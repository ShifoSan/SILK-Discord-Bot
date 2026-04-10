import discord
from discord import app_commands
from discord.ext import commands
import os
import io
import requests


class Uncensored(commands.Cog):
    """Dedicated cog for uncensored FLUX image generation.
    Uses enhanceaiteam/Flux-uncensored (LoRA-based) via standard HF Inference API.
    """

    def __init__(self, bot):
        self.bot = bot
        
        # Load API key exactly like creative.py
        self.hf_token = os.getenv("HUGGINGFACE_TOKEN")

        # Standard HF Inference API (works for community/LoRA models)
        self.model_id = "enhanceaiteam/Flux-uncensored"
        self.HF_API_URL = f"https://api-inference.huggingface.co/models/{self.model_id}"

    @app_commands.command(
        name="uncensored",
        description="Generate fully uncensored images using FLUX (NSFW / explicit allowed)"
    )
    @app_commands.describe(
        prompt="Your detailed prompt (no restrictions — be as explicit as you want)"
    )
    async def uncensored_imagine(self, interaction: discord.Interaction, prompt: str):
        """Slash command: /uncensored <prompt>"""
        
        # CRITICAL Defer Protocol for HeavenCloud free tier
        await interaction.response.defer(thinking=True)

        if not self.hf_token:
            await interaction.followup.send("❌ Hugging Face Token is not configured.")
            return

        headers = {"Authorization": f"Bearer {self.hf_token}"}
        payload = {"inputs": prompt}   # Same minimal payload as your /imagine command

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
                embed.set_footer(text="enhanceaiteam/Flux-uncensored • Fully uncensored")
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
