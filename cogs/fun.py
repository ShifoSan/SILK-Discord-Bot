import discord
from discord import app_commands
from discord.ext import commands

class Fun(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="mock", description="Converts text to sPoNgEbOb cAsE")
    async def mock(self, interaction: discord.Interaction, text: str):
        # Start with lower to match sPoNgEbOb pattern (first letter usually lower in the meme, but standard alternate works too)
        # Using i%2 == 0 as lower, i%2 == 1 as upper: sPoNgE...
        # 's' (0) -> lower, 'P' (1) -> upper
        mocked_text = "".join([c.lower() if i % 2 == 0 else c.upper() for i, c in enumerate(text)])
        await interaction.response.send_message(mocked_text)

    @app_commands.command(name="reverse", description="Reverses the text")
    async def reverse(self, interaction: discord.Interaction, text: str):
        await interaction.response.send_message(text[::-1])

    @app_commands.command(name="clap", description="Adds 👏 emojis between words")
    async def clap(self, interaction: discord.Interaction, text: str):
        clapped_text = " 👏 ".join(text.split())
        await interaction.response.send_message(clapped_text)

    @app_commands.command(name="say", description="Repeats what you say")
    async def say(self, interaction: discord.Interaction, text: str):
        # Keep as slash command, "Used /say" will be visible.
        await interaction.response.send_message(text)

async def setup(bot):
    await bot.add_cog(Fun(bot))
