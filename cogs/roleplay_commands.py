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
            "cuddle": {"target": "{user} snuggles up close to {target}."},
            "pat": {"target": "{user} pats {target} on the head. Good job!"},
            "poke": {"target": "{user} pokes {target}. Hey! Listen!"},
            "lick": {"target": "{user} licks {target}... wait, why?"},
            "bite": {"target": "{user} bites {target}! Nom!"},
            "handhold": {"target": "{user} holds {target}'s hand. How lewd!"},
            "glomp": {"target": "{user} tackles {target} with a massive hug!"},

            # Action (Target Mandatory)
            "slap": {"target": "{user} slaps {target} across the face!"},
            "kill": {"target": "{user} ends {target}. Press F to pay respects."},
            "kick": {"target": "{user} kicks {target} into the stratosphere!"},
            "bonk": {"target": "{user} bonked {target} on the head! Go to horny jail!"},
            "yeet": {"target": "{user} grabs {target} and YEETS them away!"},
            "highfive": {"target": "{user} high-fives {target}! Up top!"},
            "wave": {"target": "{user} waves at {target}. Hello!"},

            # Special (Target Mandatory)
            "bully": {"target": "{user} is bullying {target}. That's just mean."},
            "smug": {"target": "{user} gives {target} a smug look."},

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

    # --- Affection Commands (Target Required) ---
    @app_commands.command(name="hug", description="Give someone a big hug!")
    async def hug(self, interaction: discord.Interaction, user: discord.Member):
        await self._perform_roleplay(interaction, "hug", user)

    @app_commands.command(name="kiss", description="Give someone a kiss!")
    async def kiss(self, interaction: discord.Interaction, user: discord.Member):
        await self._perform_roleplay(interaction, "kiss", user)

    @app_commands.command(name="cuddle", description="Cuddle with someone!")
    async def cuddle(self, interaction: discord.Interaction, user: discord.Member):
        await self._perform_roleplay(interaction, "cuddle", user)

    @app_commands.command(name="pat", description="Pat someone on the head!")
    async def pat(self, interaction: discord.Interaction, user: discord.Member):
        await self._perform_roleplay(interaction, "pat", user)

    @app_commands.command(name="poke", description="Poke someone!")
    async def poke(self, interaction: discord.Interaction, user: discord.Member):
        await self._perform_roleplay(interaction, "poke", user)

    @app_commands.command(name="lick", description="Lick someone!")
    async def lick(self, interaction: discord.Interaction, user: discord.Member):
        await self._perform_roleplay(interaction, "lick", user)

    @app_commands.command(name="bite", description="Bite someone!")
    async def bite(self, interaction: discord.Interaction, user: discord.Member):
        await self._perform_roleplay(interaction, "bite", user)

    @app_commands.command(name="handhold", description="Hold someone's hand!")
    async def handhold(self, interaction: discord.Interaction, user: discord.Member):
        await self._perform_roleplay(interaction, "handhold", user)

    @app_commands.command(name="glomp", description="Tackle hug someone!")
    async def glomp(self, interaction: discord.Interaction, user: discord.Member):
        await self._perform_roleplay(interaction, "glomp", user)

    # --- Action Commands (Target Required) ---
    @app_commands.command(name="slap", description="Slap someone!")
    async def slap(self, interaction: discord.Interaction, user: discord.Member):
        await self._perform_roleplay(interaction, "slap", user)

    @app_commands.command(name="kill", description="End someone.")
    async def kill(self, interaction: discord.Interaction, user: discord.Member):
        await self._perform_roleplay(interaction, "kill", user)

    @app_commands.command(name="kick", description="Kick someone!")
    async def kick(self, interaction: discord.Interaction, user: discord.Member):
        await self._perform_roleplay(interaction, "kick", user)

    @app_commands.command(name="bonk", description="Bonk someone to horny jail!")
    async def bonk(self, interaction: discord.Interaction, user: discord.Member):
        await self._perform_roleplay(interaction, "bonk", user)

    @app_commands.command(name="yeet", description="Yeet someone away!")
    async def yeet(self, interaction: discord.Interaction, user: discord.Member):
        await self._perform_roleplay(interaction, "yeet", user)

    @app_commands.command(name="highfive", description="High-five someone!")
    async def highfive(self, interaction: discord.Interaction, user: discord.Member):
        await self._perform_roleplay(interaction, "highfive", user)

    @app_commands.command(name="wave", description="Wave at someone!")
    async def wave(self, interaction: discord.Interaction, user: discord.Member):
        await self._perform_roleplay(interaction, "wave", user)

    # --- Special Commands (Target Required) ---
    @app_commands.command(name="bully", description="Bully someone!")
    async def bully(self, interaction: discord.Interaction, user: discord.Member):
        await self._perform_roleplay(interaction, "bully", user)

    @app_commands.command(name="smug", description="Give someone a smug look!")
    async def smug(self, interaction: discord.Interaction, user: discord.Member):
        await self._perform_roleplay(interaction, "smug", user)

    # --- Emotion/Hybrid Commands (Target Optional) ---
    @app_commands.command(name="nom", description="Eat something or someone!")
    async def nom(self, interaction: discord.Interaction, user: discord.Member = None):
        await self._perform_roleplay(interaction, "nom", user)

    @app_commands.command(name="smile", description="Smile at someone or just smile!")
    async def smile(self, interaction: discord.Interaction, user: discord.Member = None):
        await self._perform_roleplay(interaction, "smile", user)

    @app_commands.command(name="blush", description="Blush at someone or just blush!")
    async def blush(self, interaction: discord.Interaction, user: discord.Member = None):
        await self._perform_roleplay(interaction, "blush", user)

    @app_commands.command(name="wink", description="Wink at someone or just wink!")
    async def wink(self, interaction: discord.Interaction, user: discord.Member = None):
        await self._perform_roleplay(interaction, "wink", user)

    @app_commands.command(name="dance", description="Dance with someone or just dance!")
    async def dance(self, interaction: discord.Interaction, user: discord.Member = None):
        await self._perform_roleplay(interaction, "dance", user)

    @app_commands.command(name="cringe", description="Cringe at someone or something!")
    async def cringe(self, interaction: discord.Interaction, user: discord.Member = None):
        await self._perform_roleplay(interaction, "cringe", user)

    @app_commands.command(name="cry", description="Cry about it!")
    async def cry(self, interaction: discord.Interaction, user: discord.Member = None):
        await self._perform_roleplay(interaction, "cry", user)

    @app_commands.command(name="happy", description="Be happy!")
    async def happy(self, interaction: discord.Interaction, user: discord.Member = None):
        await self._perform_roleplay(interaction, "happy", user)

async def setup(bot):
    await bot.add_cog(RoleplayCommands(bot))
