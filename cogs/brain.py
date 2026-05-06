import discord
from discord import app_commands
from discord.ext import commands
import os
from google import genai
from google.genai import types

class Brain(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.api_key = os.getenv("GEMINI_API_KEY")
        self.model_id = "gemma-4-31b-it"

        if self.api_key:
            self.client = genai.Client(api_key=self.api_key)
        else:
            self.client = None
            print("Warning: GEMINI_API_KEY not found. Brain module will fail.")

        self.persona = (
            "You are S.I.L.K., a witty, helpful, and slightly chaotic AI assistant living in a Discord server. "
            "Keep answers concise (under 2000 chars). Be cool."
        )

    async def get_response(self, prompt: str) -> str:
        if not self.client:
            return "My brain is missing (API Key not found)!"

        # Manual system prompting: Prepend persona to user prompt
        full_prompt = f"System: {self.persona}\nUser: {prompt}"

        try:
            response = self.client.models.generate_content(
                model=self.model_id,
                contents=full_prompt,
                config=types.GenerateContentConfig(
                    temperature=0.8
                )
            )
            if response.text:
                return response.text
            return "I have no words... literally."
        except Exception as e:
            error_str = str(e).lower()
            if "blocked" in error_str or "safety" in error_str:
                return "My safety filters blocked that response. Try asking nicely! 🤖"
            print(f"GenAI Error: {e}")
            # Debug Mode: Return actual error to Discord
            return f"⚠️ API Error: {e}"

    @app_commands.command(name="roast", description="Roast a user. brutally.")
    async def roast(self, interaction: discord.Interaction, user: discord.Member):
        await interaction.response.defer(thinking=True)
        prompt = f"Write a creative, funny, lighthearted but sharp roast targeting a user named {user.display_name}. Make it specific if you can guess, but mostly generic funny insults."
        response_text = await self.get_response(prompt)

        embed = discord.Embed(title=f"🔥 Roast of {user.display_name}", description=response_text, color=discord.Color.red())
        await interaction.followup.send(embed=embed)

    @app_commands.command(name="translate", description="Translate text into a target language.")
    async def translate(self, interaction: discord.Interaction, language: str, text: str):
        await interaction.response.defer(thinking=True)
        prompt = f"Translate the following text into {language}:\n\n{text}"
        response_text = await self.get_response(prompt)

        embed = discord.Embed(title=f"🌐 Translate to {language}", description=response_text, color=discord.Color.teal())
        await interaction.followup.send(embed=embed)

async def setup(bot):
    await bot.add_cog(Brain(bot))
