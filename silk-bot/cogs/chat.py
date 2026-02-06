import discord
from discord.ext import commands
from discord import app_commands
import os
import time
from collections import deque
from google import genai
from google.genai import types
from cogs.personalities import standard, edgy, helpful

class Chat(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.active_channels = set()
        self.reply_history = deque()
        self.MAX_RPM = 30
        self.current_persona = standard.config

        api_key = os.getenv("GEMINI_API_KEY")
        if api_key:
            self.client = genai.Client(api_key=api_key)
        else:
            print("Warning: GEMINI_API_KEY not found. Chat module will not function.")
            self.client = None

    def can_reply(self) -> bool:
        """
        Rate limiter engine: Enforces MAX_RPM using a sliding window.
        """
        now = time.time()

        # Remove timestamps older than 60 seconds
        while self.reply_history and self.reply_history[0] < now - 60:
            self.reply_history.popleft()

        # Check if we are within the limit
        if len(self.reply_history) < self.MAX_RPM:
            self.reply_history.append(now)
            return True
        return False

    @app_commands.command(name="chat_toggle", description="Enable or disable auto-chat in this channel.")
    @app_commands.describe(state="True to enable, False to disable")
    async def chat_toggle(self, interaction: discord.Interaction, state: bool):
        if state:
            self.active_channels.add(interaction.channel_id)
            await interaction.response.send_message("✅ Auto-Chat Enabled for this channel.", ephemeral=True)
        else:
            if interaction.channel_id in self.active_channels:
                self.active_channels.remove(interaction.channel_id)
            await interaction.response.send_message("❌ Auto-Chat Disabled for this channel.", ephemeral=True)

    @app_commands.command(name="persona", description="Switch S.I.L.K.'s personality.")
    @app_commands.describe(name="The personality to switch to")
    @app_commands.choices(name=[
        app_commands.Choice(name="Standard", value="Standard"),
        app_commands.Choice(name="Edgy", value="Edgy"),
        app_commands.Choice(name="Helpful", value="Helpful")
    ])
    @app_commands.checks.has_permissions(manage_messages=True)
    async def persona(self, interaction: discord.Interaction, name: app_commands.Choice[str]):
        choice = name.value
        if choice == "Standard":
            self.current_persona = standard.config
        elif choice == "Edgy":
            self.current_persona = edgy.config
        elif choice == "Helpful":
            self.current_persona = helpful.config

        await interaction.response.send_message(f"🔄 Persona switched to {choice}.")

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        # 1. Triggers & Filters

        # Strictly ignore ALL bots (including self) as triggers
        if message.author.bot:
            return

        # Must be in an active channel
        if message.channel.id not in self.active_channels:
            return

        # Ignore commands (start with /) - although on_message catches raw messages,
        # app_commands are usually handled separately, but standard text commands or
        # chat inputs starting with / should be ignored for chat generation.
        if message.content.startswith('/'):
            return

        # 2. Rate Limit Check
        if not self.can_reply():
            # Silently return if rate limit exceeded
            return

        # 3. The "Smart Context" Logic
        try:
            async with message.channel.typing():
                # Fetch last 20 messages
                # history() returns an async iterator, usually newest first.
                # We need to reverse it to get chronological order (Oldest -> Newest).
                history_messages = [msg async for msg in message.channel.history(limit=20)]
                history_messages.reverse()

                formatted_history = []

                for msg in history_messages:
                    # Truncate content > 1000 chars
                    content = msg.content
                    if len(content) > 1000:
                        content = content[:1000] + "...(truncated)"

                    if msg.author == self.bot.user:
                        # Self (S.I.L.K.)
                        formatted_history.append(f"[Model - S.I.L.K.]: {content}")
                    elif msg.author.bot:
                        # Other Bots -> Skip
                        continue
                    else:
                        # User
                        formatted_history.append(f"[User - {msg.author.display_name}]: {content}")

                formatted_history_string = "\n".join(formatted_history)

                # Prompt Assembly
                system_prompt = self.current_persona['system_instruction']

                full_prompt = (
                    f"{system_prompt}\n"
                    f"Context:\n"
                    f"{formatted_history_string}"
                )

                # 4. Generation
                if self.client:
                    response = self.client.models.generate_content(
                        model='gemma-3-27b-it',
                        contents=full_prompt,
                        config=types.GenerateContentConfig(safety_settings=self.current_persona['safety_settings'])
                    )

                    if response.text:
                        await message.reply(response.text)
                    else:
                        print("Error: Empty response from Gemini API.")
                else:
                    print("Error: Gemini Client not initialized.")

        except Exception as e:
            # Print errors to console only (do not spam chat)
            print(f"Error in chat module: {e}")

async def setup(bot):
    await bot.add_cog(Chat(bot))
