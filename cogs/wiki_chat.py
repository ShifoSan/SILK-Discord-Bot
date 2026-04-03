import discord
from discord.ext import commands
from discord import app_commands
import os
import asyncio
import aiohttp
from google import genai
from google.genai import types

from cogs.level_system.database import get_guild_config, update_guild_config

AVAILABLE_FANDOMS = {
    "aotr": "https://official-attack-on-titans-revolution.fandom.com/api.php"
}

class WikiChat(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        api_key = os.getenv("GEMINI_API_KEY")
        if api_key:
            self.client = genai.Client(api_key=api_key)
        else:
            print("Warning: GEMINI_API_KEY not found. WikiChat module will not function.")
            self.client = None

    @app_commands.command(name="set-wiki", description="Manage Wiki Auto-Chat for a specific channel")
    @app_commands.describe(
        channel="The target channel",
        state="True to enable the wiki AI, False to disable",
        show_fandoms="If True, shows available wikis and ignores other arguments"
    )
    @app_commands.checks.has_permissions(manage_guild=True)
    async def set_wiki(self, interaction: discord.Interaction, channel: discord.TextChannel = None, state: bool = None, show_fandoms: bool = False):
        await interaction.response.defer(ephemeral=True)

        if show_fandoms:
            embed = discord.Embed(title="Available Fandom Wikis", color=discord.Color.blue())
            for name, url in AVAILABLE_FANDOMS.items():
                embed.add_field(name=name.upper(), value=url, inline=False)
            await interaction.followup.send(embed=embed)
            return

        if channel is None or state is None:
            await interaction.followup.send("❌ You must provide both `channel` and `state` unless using `show_fandoms`.", ephemeral=True)
            return

        # Conflict Resolution: Ensure standard chat is disabled
        chat_cog = self.bot.get_cog("Chat")
        if state and chat_cog and channel.id in chat_cog.active_channels:
            await interaction.followup.send(f"❌ Standard Chat is already enabled in {channel.mention}. You must disable it first using `/chat_toggle` before enabling the Wiki AI.", ephemeral=True)
            return

        config = await get_guild_config(interaction.guild_id)
        wiki_channels = config.get("wiki_channels", [])

        if state:
            if channel.id not in wiki_channels:
                wiki_channels.append(channel.id)
                await update_guild_config(interaction.guild_id, {"wiki_channels": wiki_channels})
                await interaction.followup.send(f"✅ Wiki AI has been ENABLED in {channel.mention}.")
            else:
                await interaction.followup.send(f"⚠️ Wiki AI is already enabled in {channel.mention}.")
        else:
            if channel.id in wiki_channels:
                wiki_channels.remove(channel.id)
                await update_guild_config(interaction.guild_id, {"wiki_channels": wiki_channels})
                await interaction.followup.send(f"✅ Wiki AI has been DISABLED in {channel.mention}.")
            else:
                await interaction.followup.send(f"⚠️ Wiki AI is not enabled in {channel.mention}.")

    async def fetch_wiki_text(self, query: str) -> str:
        """Helper to search Fandom and extract text."""
        api_url = AVAILABLE_FANDOMS["aotr"]
        async with aiohttp.ClientSession() as session:
            # 1. Search for the closest page
            search_params = {
                "action": "query",
                "list": "search",
                "srsearch": query,
                "format": "json"
            }
            async with session.get(api_url, params=search_params) as resp:
                search_data = await resp.json()

            if not search_data.get("query", {}).get("search"):
                return ""

            # Take the top match title
            page_title = search_data["query"]["search"][0]["title"]

            # 2. Extract plain text from the matched page
            extract_params = {
                "action": "query",
                "prop": "extracts",
                "explaintext": 1,
                "titles": page_title,
                "format": "json"
            }
            async with session.get(api_url, params=extract_params) as resp:
                extract_data = await resp.json()

            pages = extract_data.get("query", {}).get("pages", {})
            for page_id, page_info in pages.items():
                if "extract" in page_info:
                    # Return first 4000 chars to save tokens
                    return page_info["extract"][:4000]

            return ""

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        if message.author.bot or not message.guild:
            return

        if message.content.startswith('/'):
            return

        # Check if the channel is an active wiki channel
        config = await get_guild_config(message.guild.id)
        wiki_channels = config.get("wiki_channels", [])
        if message.channel.id not in wiki_channels:
            return

        if not self.client:
            return

        async with message.channel.typing():
            # 1. Extract a clean search query using the fast model
            extraction_prompt = f"""
            Extract the core subject from the following user question to be used as a wiki search query. 
            Return ONLY the 1-3 word search query and absolutely nothing else.
            User Question: "{message.content}"
            """
            
            try:
                query_response = await asyncio.to_thread(
                    self.client.models.generate_content,
                    model='gemini-3.1-flash-lite-preview',
                    contents=extraction_prompt,
                    config=types.GenerateContentConfig(safety_settings=[])
                )
                search_term = query_response.text.strip()
            except Exception as e:
                print(f"Error in WikiChat AI Extraction: {e}")
                search_term = message.content # Fallback to raw message if it fails

            # 2. Fetch wiki content using the cleaned search term
            wiki_text = await self.fetch_wiki_text(search_term)

            # 3. Compile recent history
            history_messages = [msg async for msg in message.channel.history(limit=20)]
            history_messages.reverse()

            formatted_history = []
            for msg in history_messages:
                if msg.author == self.bot.user:
                    formatted_history.append(f"[Model - S.I.L.K.]: {msg.content}")
                elif not msg.author.bot:
                    formatted_history.append(f"[User - {msg.author.display_name}]: {msg.content}")

            history_string = "\n".join(formatted_history)

            # 4. Prompt Setup
            system_prompt = (
                "You are S.I.L.K., an expert Wiki Agent. Your ONLY source of truth is the provided Fandom Wiki Extract below. "
                "You must ONLY answer the user's questions based on this exact text. Do NOT hallucinate stats, prices, or information. "
                "If the text does not contain the answer, politely say that you don't know based on the wiki."
            )

            full_prompt = (
                f"{system_prompt}\n\n"
                f"--- WIKI EXTRACT ---\n"
                f"{wiki_text if wiki_text else 'No relevant wiki page found for the query.'}\n"
                f"--------------------\n\n"
                f"--- CONVERSATION HISTORY ---\n"
                f"{history_string}"
            )

            try:
                response = await asyncio.to_thread(
                    self.client.models.generate_content,
                    model='gemma-4-31b-it',
                    contents=full_prompt,
                    config=types.GenerateContentConfig(safety_settings=[])
                )

                if response.text:
                    # Keep under Discord limit
                    reply_text = response.text[:2000]
                    await message.reply(reply_text)
            except Exception as e:
                print(f"Error in WikiChat AI Generation: {e}")

async def setup(bot):
    await bot.add_cog(WikiChat(bot))
            
