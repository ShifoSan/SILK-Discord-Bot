import discord
from discord import app_commands
from discord.ext import commands
import os
import io
import requests
import asyncio


class Uncensored(commands.Cog):
    """True uncensored FLUX cog using Replicate.com
    Model: aisha-ai-official/flux.1dev-uncensored-msfluxnsfw-v3 (explicitly NSFW/uncensored)
    """

    def __init__(self, bot):
        self.bot = bot
        self.replicate_token = os.getenv("REPLICATE_API_TOKEN")
        if not self.replicate_token:
            print("⚠️ WARNING: REPLICATE_API_TOKEN not found in .env")

        # This is the exact uncensored FLUX variant
        self.model_version = "aisha-ai-official/flux.1dev-uncensored-msfluxnsfw-v3:..."  # ← Replace with current version ID from https://replicate.com/aisha-ai-official/flux.1dev-uncensored-msfluxnsfw-v3 (copy the long version hash)

    @app_commands.command(
        name="uncensored",
        description="Generate truly uncensored images (NSFW / explicit fully allowed)"
    )
    @app_commands.describe(
        prompt="Your detailed prompt (no restrictions — be as explicit as you want)"
    )
    async def uncensored_imagine(self, interaction: discord.Interaction, prompt: str):
        await interaction.response.defer(thinking=True)

        if not self.replicate_token:
            await interaction.followup.send("❌ Replicate API token is not configured.")
            return

        headers = {
            "Authorization": f"Token {self.replicate_token}",
            "Content-Type": "application/json"
        }

        payload = {
            "version": self.model_version,
            "input": {
                "prompt": prompt,
                "width": 1024,
                "height": 1024,
                "num_inference_steps": 20,
                "guidance_scale": 3.5
            }
        }

        try:
            # 1. Create prediction
            create_resp = requests.post(
                "https://api.replicate.com/v1/predictions",
                headers=headers,
                json=payload,
                timeout=30
            )

            if create_resp.status_code != 201:
                await interaction.followup.send(f"❌ API Error: {create_resp.text[:300]}")
                return

            prediction = create_resp.json()
            prediction_id = prediction["id"]

            # 2. Poll until ready (Replicate is async)
            for _ in range(60):  # max \~60 seconds
                poll_resp = requests.get(
                    f"https://api.replicate.com/v1/predictions/{prediction_id}",
                    headers=headers,
                    timeout=30
                )
                data = poll_resp.json()

                if data["status"] == "succeeded":
                    image_url = data["output"][0]  # direct image URL
                    break
                elif data["status"] in ["failed", "canceled"]:
                    await interaction.followup.send("❌ Generation failed on Replicate.")
                    return

                await asyncio.sleep(1.5)  # polite polling

            else:
                await interaction.followup.send("❌ Timeout — try again.")
                return

            # 3. Download the image bytes
            img_resp = requests.get(image_url, timeout=30)
            image_bytes = img_resp.content

            with io.BytesIO(image_bytes) as buf:
                buf.seek(0)
                file = discord.File(buf, filename="uncensored_flux.png")

                embed = discord.Embed(
                    title="🖼️ Truly Uncensored FLUX Image",
                    description=f"**Prompt:** {prompt[:1900]}..." if len(prompt) > 1900 else f"**Prompt:** {prompt}",
                    color=0xFF00FF
                )
                embed.set_footer(text="Replicate • aisha-ai-official/flux.1dev-uncensored-msfluxnsfw-v3")
                await interaction.followup.send(embed=embed, file=file)

        except Exception as e:
            await interaction.followup.send(f"❌ An error occurred: {e}")


async def setup(bot):
    await bot.add_cog(Uncensored(bot))
