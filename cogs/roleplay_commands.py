import discord
from discord import app_commands
from discord.ext import commands
import aiohttp

class RoleplayCommands(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        # Flavor text mapping:
        # Keys match the command name (which usually matches the API category).
        # Values are dictionaries with "solo" (optional) and "target" (mandatory) templates.
        self.flavor_text = {
            # Affection (Target Mandatory)
            "hug": {"target": "{user} wraps their arms tightly around {target}!"},
            "kiss": {"target": "{user} leans in and gives {target} a soft kiss."},
            "pat": {"target": "{user} pats {target} on the head. Good job!"},
            "poke": {"target": "{user} pokes {target}. Hey! Listen!"},
            "lick": {"target": "{user} licks {target}... wait, why?"},
            "bite": {"target": "{user} bites {target}! Nom!"},
            "handhold": {"target": "{user} holds {target}'s hand. How lewd!"},

            # Action (Target Mandatory)
            "slap": {"target": "{user} slaps {target} across the face!"},
            "kill": {"target": "{user} ends {target}. Press F to pay respects."},
            "kick": {"target": "{user} kicks {target} into the stratosphere!"},
            "highfive": {"target": "{user} high-fives {target}! Up top!"},

            # Special (Target Mandatory)
            "bully": {"target": "{user} is bullying {target}. That's just mean."},

            # Emotion/Reaction (Target Optional)
            # API categories that support both solo and target logically
            "nom": {
                "solo": "{user} is eating something delicious.",
                "target": "{user} takes a bite out of {target}! Tasty?"
            },
            "smile": {
                "solo": "{user} is smiling happily!",
                "target": "{user} smiles sweetly at {target}."
            },
            "blush": {
                "solo": "{user}'s face turns bright red!",
                "target": "{user} blushes because of {target}."
            },
            "wink": {
                "solo": "{user} winks playfully.",
                "target": "{user} winks at {target}. ;)"
            },
            "dance": {
                "solo": "{user} starts dancing! Look at them go!",
                "target": "{user} grabs {target} for a dance!"
            },
            "cringe": {
                "solo": "{user} cringes hard.",
                "target": "{user} cringes at what {target} did."
            },
            "cry": {
                "solo": "{user} bursts into tears. Someone give them a hug!",
                "target": "{user} is crying because of {target}."
            },
            "happy": {
                "solo": "{user} is jumping with joy!",
                "target": "{user} is happy to see {target}!"
            }
        }

    async def get_gif(self, category: str) -> str:
        """Fetches a GIF URL from waifu.pics API."""
        url = f"https://api.waifu.pics/sfw/{category}"
        async with aiohttp.ClientSession() as session:
            async with session.get(url) as response:
                if response.status != 200:
                    raise Exception(f"API returned status {response.status}")
                data = await response.json()
                return data["url"]

    async def _perform_roleplay(self, interaction: discord.Interaction, category: str, target: discord.Member = None):
        """Helper to handle the logic, embedding, and error handling for all roleplay commands."""
        target_required = [
            "hug", "kiss", "pat", "poke", "lick", "bite", "handhold",
            "slap", "kill", "kick", "highfive",
            "bully"
        ]

        if category in target_required and target is None:
            await interaction.response.send_message("You need to specify a target for this emote!", ephemeral=True)
            return

        # Defer immediately as per protocol
        await interaction.response.defer(thinking=True)

        try:
            image_url = await self.get_gif(category)

            # Determine flavor text
            templates = self.flavor_text.get(category, {})
            text = ""

            if target:
                if "target" in templates:
                    text = templates["target"].format(user=interaction.user.mention, target=target.mention)
                else:
                    # Fallback if specific target text missing
                    text = f"{interaction.user.mention} interacts with {target.mention}."
            else:
                if "solo" in templates:
                    text = templates["solo"].format(user=interaction.user.mention)
                else:
                    # Fallback or if command forced a target but logic failed (shouldn't happen with correct args)
                    text = f"{interaction.user.mention} is {category}ing!"

            # Build Embed
            embed = discord.Embed(description=text, color=0xFFC0CB) # Soft Pink
            embed.set_image(url=image_url)

            await interaction.followup.send(embed=embed)

        except Exception as e:
            # Log error if needed, but return ephemeral message to user
            print(f"Roleplay API Error ({category}): {e}")
            await interaction.followup.send("❌ The GIF API is taking a nap. Try again later.", ephemeral=True)

    @app_commands.command(name="emote", description="Perform a roleplay emote!")
    @app_commands.describe(
        action="The emote action to perform",
        target="The member you want to target (required for some actions)"
    )
    @app_commands.choices(action=[
        app_commands.Choice(name="Hug", value="hug"),
        app_commands.Choice(name="Kiss", value="kiss"),
        app_commands.Choice(name="Pat", value="pat"),
        app_commands.Choice(name="Poke", value="poke"),
        app_commands.Choice(name="Lick", value="lick"),
        app_commands.Choice(name="Bite", value="bite"),
        app_commands.Choice(name="Handhold", value="handhold"),
        app_commands.Choice(name="Slap", value="slap"),
        app_commands.Choice(name="Kill", value="kill"),
        app_commands.Choice(name="Kick", value="kick"),
        app_commands.Choice(name="Highfive", value="highfive"),
        app_commands.Choice(name="Bully", value="bully"),
        app_commands.Choice(name="Nom", value="nom"),
        app_commands.Choice(name="Smile", value="smile"),
        app_commands.Choice(name="Blush", value="blush"),
        app_commands.Choice(name="Wink", value="wink"),
        app_commands.Choice(name="Dance", value="dance"),
        app_commands.Choice(name="Cringe", value="cringe"),
        app_commands.Choice(name="Cry", value="cry"),
        app_commands.Choice(name="Happy", value="happy")
    ])
    async def emote(self, interaction: discord.Interaction, action: app_commands.Choice[str], target: discord.Member = None):
        await self._perform_roleplay(interaction, action.value, target)

async def setup(bot):
    await bot.add_cog(RoleplayCommands(bot))
