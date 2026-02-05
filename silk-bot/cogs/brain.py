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
        self.model_id = "gemma-3-27b-it"

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

        try:
            response = self.client.models.generate_content(
                model=self.model_id,
                contents=prompt,
                config=types.GenerateContentConfig(
                    system_instruction=self.persona,
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
            return "I tried to think too hard and short-circuited. Try again later. 🔌"

    @app_commands.command(name="idea", description="Generate a random coding or content idea.")
    async def idea(self, interaction: discord.Interaction):
        await interaction.response.defer(thinking=True)
        prompt = "Generate a unique, random coding project idea or YouTube video concept."
        response_text = await self.get_response(prompt)

        embed = discord.Embed(title="💡 Lightbulb Moment!", description=response_text, color=discord.Color.yellow())
        await interaction.followup.send(embed=embed)

    @app_commands.command(name="roast", description="Roast a user. brutally.")
    async def roast(self, interaction: discord.Interaction, user: discord.Member):
        await interaction.response.defer(thinking=True)
        prompt = f"Write a creative, funny, lighthearted but sharp roast targeting a user named {user.display_name}. Make it specific if you can guess, but mostly generic funny insults."
        response_text = await self.get_response(prompt)

        embed = discord.Embed(title=f"🔥 Roast of {user.display_name}", description=response_text, color=discord.Color.red())
        await interaction.followup.send(embed=embed)

    @app_commands.command(name="whois", description="Get a character card for a fictional character.")
    async def whois(self, interaction: discord.Interaction, character: str):
        await interaction.response.defer(thinking=True)
        prompt = f"Generate a 'Character Card' for {character}. Include Name, Origin, Powers, and Weakness. Format it clearly."
        response_text = await self.get_response(prompt)

        embed = discord.Embed(title=f"❓ Who is {character}?", description=response_text, color=discord.Color.blue())
        await interaction.followup.send(embed=embed)

    @app_commands.command(name="summary", description="Summarize text into 3 bullet points.")
    async def summary(self, interaction: discord.Interaction, text: str):
        await interaction.response.defer(thinking=True)
        prompt = f"Summarize the following text into exactly 3 bullet points:\n\n{text}"
        response_text = await self.get_response(prompt)

        embed = discord.Embed(title="📝 TL;DR", description=response_text, color=discord.Color.green())
        await interaction.followup.send(embed=embed)

    @app_commands.command(name="define", description="Get the formal definition of a word.")
    async def define(self, interaction: discord.Interaction, word: str):
        await interaction.response.defer(thinking=True)
        prompt = f"Provide the formal definition of the word '{word}'."
        response_text = await self.get_response(prompt)

        embed = discord.Embed(title=f"📖 Definition: {word}", description=response_text, color=discord.Color.blurple())
        await interaction.followup.send(embed=embed)

    @app_commands.command(name="slang", description="Get the street definition of a word.")
    async def slang(self, interaction: discord.Interaction, word: str):
        await interaction.response.defer(thinking=True)
        prompt = f"Provide the 'street' definition (Urban Dictionary style) of '{word}' and include a usage example."
        response_text = await self.get_response(prompt)

        embed = discord.Embed(title=f"🛹 Slang: {word}", description=response_text, color=discord.Color.purple())
        await interaction.followup.send(embed=embed)

    @app_commands.command(name="translate", description="Translate text into a target language.")
    async def translate(self, interaction: discord.Interaction, language: str, text: str):
        await interaction.response.defer(thinking=True)
        prompt = f"Translate the following text into {language}:\n\n{text}"
        response_text = await self.get_response(prompt)

        embed = discord.Embed(title=f"🌐 Translate to {language}", description=response_text, color=discord.Color.teal())
        await interaction.followup.send(embed=embed)

    @app_commands.command(name="ship", description="Check compatibility between two users.")
    async def ship(self, interaction: discord.Interaction, user1: discord.Member, user2: discord.Member):
        await interaction.response.defer(thinking=True)
        prompt = f"Generate a random 'Compatibility Score' (0-100%) and a short, funny love story describing the future of {user1.display_name} and {user2.display_name}. Base it purely on their names and vibes."
        response_text = await self.get_response(prompt)

        embed = discord.Embed(title=f"❤️ Shipping: {user1.display_name} x {user2.display_name}", description=response_text, color=discord.Color.magenta())
        await interaction.followup.send(embed=embed)

async def setup(bot):
    await bot.add_cog(Brain(bot))
