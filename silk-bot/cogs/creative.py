import discord
from discord import app_commands
from discord.ext import commands
import os
import io
import requests
from gtts import gTTS
from newsapi import NewsApiClient

class Creative(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        
        # Load API keys
        self.news_api_key = os.getenv("NEWS_API_KEY")
        self.hf_token = os.getenv("HUGGINGFACE_TOKEN")
        
        # Initialize NewsAPI Client
        if self.news_api_key:
            self.newsapi = NewsApiClient(api_key=self.news_api_key)
        else:
            self.newsapi = None
            print("Warning: NEWS_API_KEY not found in environment variables.")

        # Hugging Face Constants
        self.HF_API_URL = "https://router.huggingface.co/hf-inference/models/stabilityai/stable-diffusion-xl-base-1.0"

    # --- Tech News Command ---
    @app_commands.command(name="tech_news", description="Get the top 3 technology headlines")
    async def tech_news(self, interaction: discord.Interaction):
        await interaction.response.defer(thinking=True)

        if not self.newsapi:
            await interaction.followup.send("❌ NewsAPI is not configured.")
            return

        try:
            top_headlines = self.newsapi.get_top_headlines(category='technology', language='en', page_size=3)
            
            if top_headlines['status'] != 'ok':
                await interaction.followup.send("❌ Failed to fetch news.")
                return

            articles = top_headlines.get('articles', [])
            if not articles:
                await interaction.followup.send("ℹ️ No tech news found at the moment.")
                return

            embed = discord.Embed(title="📰 Top Tech News", color=discord.Color.blue())
            
            for article in articles:
                title = article.get('title', 'No Title')
                description = article.get('description', 'No description available.')
                url = article.get('url', '')
                
                value_text = f"{description}\n[Read more]({url})"
                embed.add_field(name=title, value=value_text, inline=False)

            embed.set_footer(text="Powered by NewsAPI")
            await interaction.followup.send(embed=embed)

        except Exception as e:
            await interaction.followup.send(f"❌ An error occurred while fetching news: {e}")

    # --- Imagine Command (Image Generation) ---
    @app_commands.command(name="imagine", description="Generate an image from a prompt using AI")
    @app_commands.describe(prompt="The description of the image you want to generate")
    async def imagine(self, interaction: discord.Interaction, prompt: str):
        await interaction.response.defer(thinking=True)

        if not self.hf_token:
            await interaction.followup.send("❌ Hugging Face Token is not configured.")
            return

        headers = {"Authorization": f"Bearer {self.hf_token}"}
        payload = {"inputs": prompt}

        try:
            response = requests.post(self.HF_API_URL, headers=headers, json=payload)
            
            if response.status_code == 200:
                image_bytes = response.content
                fp = io.BytesIO(image_bytes)
                file = discord.File(fp, filename="image.png")
                await interaction.followup.send(f"🎨 **Prompt:** {prompt}", file=file)
            
            elif response.status_code == 503:
                await interaction.followup.send("⏳ The model is currently loading (Cold Start). Please try again in 30 seconds.")
            
            elif 400 <= response.status_code < 500:
                try:
                    error_json = response.json()
                    error_msg = error_json.get("error", response.text)
                except ValueError:
                    error_msg = response.text
                await interaction.followup.send(f"❌ API Error: {error_msg}")
            
            else:
                await interaction.followup.send(f"❌ An unexpected error occurred. Status Code: {response.status_code}")

        except Exception as e:
             await interaction.followup.send(f"❌ An error occurred: {e}")

    # --- Voice Command (TTS) ---
    @app_commands.command(name="voice", description="Convert text to speech")
    @app_commands.describe(text="The text to convert to speech (max 200 chars)")
    async def voice(self, interaction: discord.Interaction, text: str):
        await interaction.response.defer(thinking=True)

        if len(text) > 200:
            await interaction.followup.send("❌ Text is too long. Please limit to 200 characters.")
            return

        try:
            tts = gTTS(text=text, lang='en', slow=False)
            fp = io.BytesIO()
            tts.write_to_fp(fp)
            fp.seek(0)
            
            file = discord.File(fp, filename="voice.mp3")
            await interaction.followup.send(f"🗣️ **Said:** {text}", file=file)
            
        except Exception as e:
            await interaction.followup.send(f"❌ An error occurred while generating speech: {e}")

async def setup(bot):
    await bot.add_cog(Creative(bot))
