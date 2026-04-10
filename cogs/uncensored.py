import discord
from discord import app_commands
from discord.ext import commands
import requests
import io
import asyncio  # For any potential sleeps if needed (though not required here)


class Uncensored(commands.Cog):
    """Dedicated cog for fully uncensored FLUX image generation.
    
    Uses the enhanceaiteam/Flux-uncensored LoRA (based on FLUX.1-dev).
    Fully respects your bot's free-tier constraints and Defer Protocol.
    """

    def __init__(self, bot):
        self.bot = bot
        # Model is hosted on Hugging Face and accessible via the same router you already use in creative.py
        self.model_id = "enhanceaiteam/Flux-uncensored"
        self.api_url = f"https://router.huggingface.co/models/{self.model_id}"

    @app_commands.command(
        name="uncensored",
        description="Generate fully uncensored images using FLUX (NSFW / explicit content allowed)"
    )
    @app_commands.describe(
        prompt="Your detailed prompt (no restrictions — be as explicit as you want)"
    )
    async def uncensored_imagine(self, interaction: discord.Interaction, prompt: str):
        """Slash command: /uncensored <prompt>"""
        
        # CRITICAL: Defer immediately (HeavenCloud free tier + slow HF cold starts)
        await interaction.response.defer(thinking=True)

        try:
            headers = {
                "Authorization": f"Bearer {self.bot.HUGGINGFACE_TOKEN}",
                "Content-Type": "application/json"
            }

            # Payload matches your existing FLUX.1-schnell style in creative.py
            # This LoRA is based on FLUX.1-dev, so we use reasonable defaults for quality/speed
            payload = {
                "inputs": prompt,
                "parameters": {
                    "width": 1024,
                    "height": 1024,
                    "num_inference_steps": 20,      # Good balance for dev-based LoRA
                    "guidance_scale": 3.5,          # Typical for FLUX uncensored
                    "max_sequence_length": 512
                }
            }

            response = requests.post(
                self.api_url,
                headers=headers,
                json=payload,
                timeout=120  # Generous timeout for free-tier inference
            )

            # Handle common HF errors gracefully (same as your existing /imagine)
            if response.status_code == 503:
                await interaction.followup.send(
                    "⚠️ Hugging Face is experiencing a cold start or high load.\n"
                    "Please try the command again in 5–10 seconds."
                )
                return

            if response.status_code != 200:
                error_text = response.text[:500] if response.text else "Unknown error"
                await interaction.followup.send(
                    f"❌ API Error ({response.status_code}):\n```{error_text}```"
                )
                return

            # The router returns raw image bytes (PNG) for FLUX models
            image_bytes = response.content

            # Convert to Discord file using in-memory buffer (exactly like your creative.py)
            with io.BytesIO(image_bytes) as buf:
                buf.seek(0)
                file = discord.File(buf, filename="uncensored_flux.png")

                # Nice embed (consistent with your bot's style)
                embed = discord.Embed(
                    title="🖼️ Uncensored FLUX Image",
                    description=f"**Prompt:** {prompt[:1900]}..." if len(prompt) > 1900 else f"**Prompt:** {prompt}",
                    color=0xFF00FF  # Magenta/purple to stand out as "uncensored"
                )
                embed.set_footer(text="enhanceaiteam/Flux-uncensored • Fully uncensored LoRA")

                await interaction.followup.send(embed=embed, file=file)

        except requests.exceptions.Timeout:
            await interaction.followup.send("❌ Request timed out. Hugging Face might be slow right now — try again.")
        except Exception as e:
            error_msg = str(e)[:500]
            await interaction.followup.send(f"❌ Unexpected error: {error_msg}")

    # Optional: You can add more parameters later (negative prompt, seed, etc.) if you want


async def setup(bot):
    """Required for automatic cog loading (your main.py iterates cogs/)."""
    await bot.add_cog(Uncensored(bot))
