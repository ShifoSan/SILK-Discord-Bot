import discord
from discord import app_commands
from discord.ext import commands
from cogs.help_commands import (
    ai_fun, youtube, creative, utility, fun_text,
    moderation, architect, ai_chat, creator
)

class Help(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    # --- Individual Help Commands ---

    @app_commands.command(name="quick-ai", description="Guide: AI Fun Tools")
    async def quick_ai(self, interaction: discord.Interaction):
        await interaction.response.send_message(embed=ai_fun.get_embed())

    @app_commands.command(name="yt-explain", description="Guide: YouTube Integration")
    async def yt_explain(self, interaction: discord.Interaction):
        await interaction.response.send_message(embed=youtube.get_embed())

    @app_commands.command(name="vision-help", description="Guide: Creative & Vision Tools")
    async def vision_help(self, interaction: discord.Interaction):
        await interaction.response.send_message(embed=creative.get_embed())

    @app_commands.command(name="utility-help", description="Guide: Utility Belt")
    async def utility_help(self, interaction: discord.Interaction):
        await interaction.response.send_message(embed=utility.get_embed())

    @app_commands.command(name="text-help", description="Guide: Text Playground")
    async def text_help(self, interaction: discord.Interaction):
        await interaction.response.send_message(embed=fun_text.get_embed())

    @app_commands.command(name="staff-mod-help", description="Guide: Moderation Tools")
    async def staff_mod_help(self, interaction: discord.Interaction):
        await interaction.response.send_message(embed=moderation.get_embed())

    @app_commands.command(name="server-build-help", description="Guide: Architect Tools")
    async def server_build_help(self, interaction: discord.Interaction):
        await interaction.response.send_message(embed=architect.get_embed())

    @app_commands.command(name="ai-chat-help", description="Guide: S.I.L.K. Chat Interface")
    async def ai_chat_help(self, interaction: discord.Interaction):
        await interaction.response.send_message(embed=ai_chat.get_embed())

    @app_commands.command(name="shifo-info", description="Creator Profile: ShifoSan")
    async def shifo_info(self, interaction: discord.Interaction):
        await interaction.response.send_message(embed=creator.get_embed())

    # --- The Master Help Command ---

    @app_commands.command(name="help", description="The S.I.L.K. Master Manual")
    async def help_master(self, interaction: discord.Interaction):
        await interaction.response.defer(thinking=True)

        # Logical Grouping for cleaner delivery and to avoid size limits
        group1 = [
            creator.get_embed(),
            ai_fun.get_embed(),
            ai_chat.get_embed()
        ]

        group2 = [
            youtube.get_embed(),
            creative.get_embed(),
            fun_text.get_embed()
        ]

        group3 = [
            utility.get_embed(),
            moderation.get_embed(),
            architect.get_embed()
        ]

        # Send sequentially
        await interaction.followup.send(embeds=group1)
        await interaction.followup.send(embeds=group2)
        await interaction.followup.send(embeds=group3)


async def setup(bot):
    await bot.add_cog(Help(bot))
