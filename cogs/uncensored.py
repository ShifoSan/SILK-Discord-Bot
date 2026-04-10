import discord
from discord import app_commands
from discord.ext import commands
import os
import io
import requests


class Uncensored(commands.Cog):
    """Dedicated cog for uncensored image generation.
    Uses the same proven FLUX.1-schnell router endpoint as your /imagine command
    (highly permissive with explicit/NSFW prompts).
    """

    def __init__(self, bot):
        self.bot = bot
        
        # Load token exactly like creative.py
        self.hf_token = os.getenv("HUGGINGFACE_TOKEN")

        # Same working router URL your /imagine already uses
        self.HF_API_URL = "https://router.huggingface.co/hf-inference/models/black-forest-labs/FLUX.1-schnell"

    @app_commands.command(
        name="uncensored",
        description="Generate uncensored images using FLUX (NSFW / explicit content allowed)"
    )
    @app_commands.describe(
        prompt="Your detailed prompt (be as explicit as you want — no restrictions)"
    )
    async def uncensored_imagine(self, interaction: discord.Interaction, prompt: str):
        """Slash command: /uncensored <prompt>"""
        
        # CRITICAL Defer Protocol for HeavenCloud
        await interaction.response.defer(thinking=True)

        if not self.hf_token:
            await interaction.followup.send("❌ Hugging Face Token is not configured.")
            return

        headers = {"Authorization": f"Bearer {self.hf_token}"}
        payload = {"inputs": prompt}   # Exact same minimal payload as your /imagine

        try:
            response = requests.post(self.HF_API_URL, headers=headers, json=payload)
            
            if response.status_code == 200:
                image_bytes = response.content
                fp = io.BytesIO(image_bytes)
                file = discord.File(fp, filename="uncensored_flux.png")
                
                embed = discord.Embed(
                    title="🖼️ Uncensored FLUX Image",
                    description=f"**Prompt:** {prompt[:1900]}..." if len(prompt) > 1900 else f"**Prompt:** {prompt}",
                    color=0xFF00FF
                )
                embed.set_footer(text="black-forest-labs/FLUX.1-schnell • Fully permissive")
                await interaction.followup.send(embed=embed, file=file)
            
            elif response.status_code == 503:
                await interaction.followup.send(
                    "⏳ The model is currently loading (Cold Start). Please try again in 30 seconds."
                )
            
            elif 400 <= response.status_code < 500:
                try:
                    error_json = response.json()
                    error_msg = error_json.get("error", response.text)
                except ValueError:
                    error_msg = response.text
                await interaction.followup.send(f"❌ API Error: {error_msg}")
            
            else:
                await interaction.followup.send(
                    f"❌ An unexpected error occurred. Status Code: {response.status_code}"
                )

        except Exception as e:
            await interaction.followup.send(f"❌ An error occurred: {e}")


async def setup(bot):
    await bot.add_cog(Uncensored(bot))
