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
    Costs \~$0.022 per image (new accounts get free starting credits).
    """

    def __init__(self, bot):
        self.bot = bot
        self.replicate_token = os.getenv("REPLICATE_API_TOKEN")
        if not self.replicate_token:
            print("⚠️ WARNING: REPLICATE_API_TOKEN not found in .env")

        # CORRECT full model + version (this is what was causing the 422 error)
        self.model_version = "aisha-ai-official/flux.1dev-uncensored-msfluxnsfw-v3:b477d8fc3a62e591c6224e10020538c4a9c340fb1f494891aff60019ffd5bc48"

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
            await interaction.followup.send("❌ Replicate API token is not configured in .env")
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
            # Create prediction
            create_resp = requests.post(
                "https://api.replicate.com/v1/predictions",
                headers=headers,
                json=payload,
                timeout=30
            )

            if create_resp.status_code != 201:
                await interaction.followup.send(f"❌ API Error: {create_resp.text[:400]}")
                return

            prediction = create_resp.json()
            prediction_id = prediction["id"]

            # Poll until ready
            for _ in range(60):  # \~90 seconds max
                poll_resp = requests.get(
                    f"https://api.replicate.com/v1/predictions/{prediction_id}",
                    headers=headers,
                    timeout=30
                )
                data = poll_resp.json()

                if data.get("status") == "succeeded":
                    image_url = data["output"][0]
                    break
                elif data.get("status") in ["failed", "canceled"]:
                    await interaction.followup.send("❌ Generation failed on Replicate.")
                    return

                await asyncio.sleep(1.5)

            else:
                await interaction.followup.send("❌ Timeout — model is slow right now, try again.")
                return

            # Download image
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
