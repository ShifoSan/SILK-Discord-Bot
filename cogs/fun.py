import discord
from discord import app_commands
from discord.ext import commands

class Fun(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="say", description="Repeats what you say")
    async def say(self, interaction: discord.Interaction, text: str):
        # Send an ephemeral response to the user so the command invocation is hidden
        await interaction.response.send_message("Message sent!", ephemeral=True)
        # Send the actual text directly to the channel
        await interaction.channel.send(text)

async def setup(bot):
    await bot.add_cog(Fun(bot))
