import discord
from discord.ext import commands
from discord import app_commands
import json
import os
import asyncio
from collections import deque
from google import genai
from google.genai import types
from cogs.personalities import helpful

CREATOR_ID = 871066849205448724
DM_CONFIG_FILE = "dm_config.json"

class DMControlView(discord.ui.View):
    def __init__(self, bot, user_id):
        super().__init__(timeout=None)
        self.bot = bot
        self.user_id = user_id

    @discord.ui.button(label="Approve", style=discord.ButtonStyle.success, emoji="✅")
    async def approve_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        cog = self.bot.get_cog("DMChat")
        if cog:
            await cog.approve_user(self.user_id)
            await interaction.response.edit_message(content=f"✅ User <@{self.user_id}> has been APPROVED.", view=None, embed=None)

            # Notify the user
            try:
                user = await self.bot.fetch_user(self.user_id)
                await user.send("✅ **Access Granted.** You have been approved for DM Chat with S.I.L.K.")
            except:
                pass
        else:
            await interaction.response.send_message("Error: DMChat cog not found.", ephemeral=True)

    @discord.ui.button(label="Block", style=discord.ButtonStyle.danger, emoji="⛔")
    async def block_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        cog = self.bot.get_cog("DMChat")
        if cog:
            await cog.block_user(self.user_id)
            await interaction.response.edit_message(content=f"⛔ User <@{self.user_id}> has been BLOCKED.", view=None, embed=None)
        else:
            await interaction.response.send_message("Error: DMChat cog not found.", ephemeral=True)

class DMChat(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.dm_history = {}  # {user_id: deque(maxlen=20)}
        self.config = self.load_config()

        api_key = os.getenv("GEMINI_API_KEY")
        if api_key:
            self.client = genai.Client(api_key=api_key)
        else:
            print("Warning: GEMINI_API_KEY not found. DM Chat module will not function.")
            self.client = None

    def load_config(self):
        if os.path.exists(DM_CONFIG_FILE):
            try:
                with open(DM_CONFIG_FILE, "r") as f:
                    return json.load(f)
            except json.JSONDecodeError:
                return {'approved': [], 'pending': [], 'blocked': []}
        return {'approved': [], 'pending': [], 'blocked': []}

    def save_config(self):
        with open(DM_CONFIG_FILE, "w") as f:
            json.dump(self.config, f, indent=4)

    async def approve_user(self, user_id):
        if user_id in self.config['pending']:
            self.config['pending'].remove(user_id)
        if user_id in self.config['blocked']:
            self.config['blocked'].remove(user_id)
        if user_id not in self.config['approved']:
            self.config['approved'].append(user_id)
        self.save_config()

    async def block_user(self, user_id):
        if user_id in self.config['pending']:
            self.config['pending'].remove(user_id)
        if user_id in self.config['approved']:
            self.config['approved'].remove(user_id)
        if user_id not in self.config['blocked']:
            self.config['blocked'].append(user_id)
        self.save_config()

    def get_history(self, user_id):
        if user_id not in self.dm_history:
            self.dm_history[user_id] = deque(maxlen=20)
        return self.dm_history[user_id]

    @app_commands.command(name="dm-list", description="Manage DM Access Lists (Creator Only).")
    async def dm_list(self, interaction: discord.Interaction):
        if interaction.user.id != CREATOR_ID:
            await interaction.response.send_message("⛔ You are not authorized to use this command.", ephemeral=True)
            return

        await interaction.response.defer(ephemeral=True)

        approved_list = []
        for uid in self.config['approved']:
            user = self.bot.get_user(uid)
            approved_list.append(f"{user.mention} ({uid})" if user else f"Unknown User ({uid})")

        pending_list = [str(uid) for uid in self.config['pending']]
        blocked_list = [str(uid) for uid in self.config['blocked']]

        embed = discord.Embed(title="🔐 DM Access Control List", color=discord.Color.gold())

        embed.add_field(
            name=f"✅ Approved ({len(approved_list)})",
            value="\n".join(approved_list) if approved_list else "None",
            inline=False
        )
        embed.add_field(
            name=f"⏳ Pending ({len(pending_list)})",
            value=", ".join(pending_list) if pending_list else "None",
            inline=False
        )
        embed.add_field(
            name=f"⛔ Blocked ({len(blocked_list)})",
            value=", ".join(blocked_list) if blocked_list else "None",
            inline=False
        )

        await interaction.followup.send(embed=embed, ephemeral=True)

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        # 1. Check if DM and not bot
        if message.guild is not None or message.author == self.bot.user:
            return

        user_id = message.author.id

        # 2. Creator Override
        if user_id == CREATOR_ID:
            # Bypass checks, process immediately
            await self.process_ai_response(message)
            return

        # 3. Gatekeeper Logic
        if user_id in self.config['blocked']:
            return # Ignore completely

        if user_id in self.config['pending']:
            return # Ignore silently

        if user_id in self.config['approved']:
            await self.process_ai_response(message)
            return

        # 4. New User Logic
        # Add to pending
        if user_id not in self.config['pending']:
            self.config['pending'].append(user_id)
            self.save_config()

            # Reply to user
            await message.reply("🔒 Restricted Access. Authorization request sent. (Warning: I may forget you if I restart!)")

            # DM Creator
            creator = await self.bot.fetch_user(CREATOR_ID)
            if creator:
                embed = discord.Embed(
                    title="📩 New DM Request",
                    description=f"User: {message.author.mention} (`{user_id}`)\nMessage: {message.content}",
                    color=discord.Color.orange()
                )
                view = DMControlView(self.bot, user_id)
                await creator.send(embed=embed, view=view)

    async def process_ai_response(self, message: discord.Message):
        if not self.client:
            return

        user_id = message.author.id
        history = self.get_history(user_id)

        # Update history with user message
        user_display = message.author.display_name
        if user_id == CREATOR_ID:
            history.append(f"[User - {user_display} (CREATOR_VERIFIED)]: {message.content}")
        else:
            history.append(f"[User - {user_display}]: {message.content}")

        async with message.channel.typing():
            # Construct Prompt
            system_prompt = helpful.config['system_instruction']
            history_text = "\n".join(history)

            full_prompt = (
                f"{system_prompt}\n"
                f"Context:\n"
                f"{history_text}"
            )

            try:
                response = await asyncio.to_thread(
                    self.client.models.generate_content,
                    model='gemma-3-27b-it',
                    contents=full_prompt,
                    config=types.GenerateContentConfig(safety_settings=helpful.config['safety_settings'])
                )

                if response.text:
                    # Update history with bot response
                    history.append(f"[Model - S.I.L.K.]: {response.text}")
                    await message.reply(response.text)
                else:
                    await message.reply("I cannot reply to this message due to safety filters.")
            except Exception as e:
                print(f"Error in DM Chat generation: {e}")
                await message.reply("An error occurred while processing your request.")

async def setup(bot):
    await bot.add_cog(DMChat(bot))
