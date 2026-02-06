import discord
from discord.ext import commands
from discord import app_commands
import os
import time
import asyncio
import io
import re
from gtts import gTTS
from collections import deque
from google import genai
from google.genai import types
from cogs.personalities import standard, edgy, helpful

CREATOR_ID = 871066849205448724

class Chat(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.active_channels = set()
        self.voice_active_channels = set()
        self.reply_history = deque()
        self.MAX_RPM = 30
        self.current_persona = standard.config

        api_key = os.getenv("GEMINI_API_KEY")
        if api_key:
            self.client = genai.Client(api_key=api_key)
        else:
            print("Warning: GEMINI_API_KEY not found. Chat module will not function.")
            self.client = None

    def generate_audio(self, text: str) -> io.BytesIO:
        """
        Generates an MP3 audio file from the provided text using gTTS.
        Cleanups text (removes URLs/Code) and truncates to 500 chars.
        """
        # 1. Clean Text
        # Remove Code Blocks
        clean_text = re.sub(r'```.*?```', '', text, flags=re.DOTALL)
        # Remove Inline Code
        clean_text = re.sub(r'`.*?`', '', clean_text)
        # Remove URLs
        clean_text = re.sub(r'http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\\(\\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+', '', clean_text)

        # Collapse whitespace
        clean_text = re.sub(r'\s+', ' ', clean_text).strip()

        # 2. Smart Truncation
        if len(clean_text) > 500:
            truncated = clean_text[:500]
            # Try to cut at the last sentence end
            last_sentence_end = max(truncated.rfind('.'), truncated.rfind('!'), truncated.rfind('?'))
            if last_sentence_end != -1:
                clean_text = truncated[:last_sentence_end+1]
            else:
                clean_text = truncated

        # If text became empty after cleaning, use a fallback
        if not clean_text:
            clean_text = "Here is the response."

        # 3. Generate Audio
        fp = io.BytesIO()
        try:
            tts = gTTS(text=clean_text, lang='en', tld='com')
            tts.write_to_fp(fp)
            fp.seek(0)
            return fp
        except Exception as e:
            print(f"Error in generate_audio: {e}")
            raise e

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

    @app_commands.command(name="voice_mode", description="Enable/Disable AI Voice responses in this channel.")
    @app_commands.describe(state="True to enable, False to disable")
    @app_commands.checks.has_permissions(manage_messages=True)
    async def voice_mode(self, interaction: discord.Interaction, state: bool):
        if state:
            self.voice_active_channels.add(interaction.channel_id)
            await interaction.response.send_message("🎙️ Voice Mode ENABLED. I will now speak my responses.", ephemeral=True)
        else:
            if interaction.channel_id in self.voice_active_channels:
                self.voice_active_channels.remove(interaction.channel_id)
            await interaction.response.send_message("Cx Voice Mode DISABLED.", ephemeral=True)

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

    @app_commands.command(name="ask-silk", description="Ask S.I.L.K. a question directly (Server-wide).")
    @app_commands.describe(question="The question to ask S.I.L.K.")
    async def ask_silk(self, interaction: discord.Interaction, question: str):
        # Defer immediately
        await interaction.response.defer(thinking=True)

        # Rate Limit Check
        if not self.can_reply():
            await interaction.followup.send("⏳ Global rate limit reached. Please wait a moment.", ephemeral=True)
            return

        # Prompt Assembly
        system_prompt = self.current_persona['system_instruction']

        # Format user string for security protocol
        user_display = f"{interaction.user.display_name}"
        if interaction.user.id == CREATOR_ID:
            user_input = f"[User - {user_display} (CREATOR_VERIFIED)]: {question}"
        else:
            user_input = f"[User - {user_display}]: {question}"

        full_prompt = (
            f"{system_prompt}\n"
            f"Context:\n"
            f"{user_input}"
        )

        # Generation
        if self.client:
            try:
                response = await asyncio.to_thread(
                    self.client.models.generate_content,
                    model='gemma-3-27b-it',
                    contents=full_prompt,
                    config=types.GenerateContentConfig(safety_settings=self.current_persona['safety_settings'])
                )

                if response.text:
                    # Voice Mode Check
                    if interaction.channel_id in self.voice_active_channels:
                        try:
                            audio_file = await asyncio.to_thread(self.generate_audio, response.text)
                            await interaction.followup.send(content=response.text, file=discord.File(audio_file, filename="silk_voice.mp3"))
                        except Exception as e:
                            print(f"Error generating audio: {e}")
                            await interaction.followup.send(response.text)
                    else:
                        await interaction.followup.send(response.text)
                else:
                    await interaction.followup.send("I cannot reply to this question due to safety filters or an API error.")
                    print("Error: Empty response from Gemini API in ask-silk.")
            except Exception as e:
                await interaction.followup.send("An error occurred while processing your request.")
                print(f"Error in ask-silk: {e}")
        else:
            await interaction.followup.send("AI module is currently unavailable.")
            print("Error: Gemini Client not initialized.")

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        # 1. Triggers & Filters

        # Strictly ignore ALL bots (including self) as triggers
        if message.author.bot:
            return

        # Trigger Logic
        is_auto_chat = message.channel.id in self.active_channels
        is_mentioned = self.bot.user in message.mentions
        is_reply = (message.reference is not None and
                    isinstance(message.reference.resolved, discord.Message) and
                    message.reference.resolved.author == self.bot.user)

        # If NONE of these are true, then ignore the message
        if not (is_auto_chat or is_mentioned or is_reply):
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
                    content = msg.content

                    if msg.author == self.bot.user:
                        # Self (S.I.L.K.)
                        formatted_history.append(f"[Model - S.I.L.K.]: {content}")
                    elif msg.author.bot:
                        # Other Bots -> Skip
                        continue
                    else:
                        # User
                        if msg.author.id == CREATOR_ID:
                            formatted_history.append(f"[User - {msg.author.display_name} (CREATOR_VERIFIED)]: {content}")
                        else:
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
                    response = await asyncio.to_thread(
                        self.client.models.generate_content,
                        model='gemma-3-27b-it',
                        contents=full_prompt,
                        config=types.GenerateContentConfig(safety_settings=self.current_persona['safety_settings'])
                    )

                    if response.text:
                        await asyncio.sleep(1.5)
                        # Voice Mode Check
                        if message.channel.id in self.voice_active_channels:
                            try:
                                audio_file = await asyncio.to_thread(self.generate_audio, response.text)
                                await message.reply(content=response.text, file=discord.File(audio_file, filename="silk_voice.mp3"))
                            except Exception as e:
                                print(f"Error generating audio: {e}")
                                await message.reply(response.text)
                        else:
                            await message.reply(response.text)
                    else:
                        await message.reply("I cannot reply to this conversation due to safety filters or an API error.")
                        print("Error: Empty response from Gemini API.")
                else:
                    print("Error: Gemini Client not initialized.")

        except Exception as e:
            # Print errors to console only (do not spam chat)
            print(f"Error in chat module: {e}")

async def setup(bot):
    await bot.add_cog(Chat(bot))
