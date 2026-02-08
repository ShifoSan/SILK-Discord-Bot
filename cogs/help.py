import discord
from discord import app_commands
from discord.ext import commands
from cogs.help_commands import (
    ai_fun, youtube, creative, utility,
    moderation, architect, ai_chat, fun_text,
    logging, roleplay, creator_note
)

class HelpView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None) # Persistent view if needed, but ephemeral usually times out.

    # Row 1: [🧠 Brain] [📺 Shifo] [🎨 Creative] [🛠️ Utils]
    @discord.ui.button(label="Brain", style=discord.ButtonStyle.secondary, emoji="🧠", row=0)
    async def brain_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.edit_message(embed=ai_fun.get_embed(), view=self)

    @discord.ui.button(label="Shifo", style=discord.ButtonStyle.secondary, emoji="📺", row=0)
    async def shifo_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.edit_message(embed=youtube.get_embed(), view=self)

    @discord.ui.button(label="Creative", style=discord.ButtonStyle.secondary, emoji="🎨", row=0)
    async def creative_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.edit_message(embed=creative.get_embed(), view=self)

    @discord.ui.button(label="Utils", style=discord.ButtonStyle.secondary, emoji="🛠️", row=0)
    async def utils_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.edit_message(embed=utility.get_embed(), view=self)

    # Row 2: [🛡️ Mod] [🏗️ Architect] [💬 AI Chat] [🎲 Fun]
    @discord.ui.button(label="Mod", style=discord.ButtonStyle.danger, emoji="🛡️", row=1)
    async def mod_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.edit_message(embed=moderation.get_embed(), view=self)

    @discord.ui.button(label="Architect", style=discord.ButtonStyle.secondary, emoji="🏗️", row=1)
    async def architect_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.edit_message(embed=architect.get_embed(), view=self)

    @discord.ui.button(label="AI Chat", style=discord.ButtonStyle.primary, emoji="💬", row=1)
    async def ai_chat_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.edit_message(embed=ai_chat.get_embed(), view=self)

    @discord.ui.button(label="Fun", style=discord.ButtonStyle.secondary, emoji="🎲", row=1)
    async def fun_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.edit_message(embed=fun_text.get_embed(), view=self)

    # Row 3: [📊 Logs] [🎭 Roleplay] [📝 Creator]
    @discord.ui.button(label="Logs", style=discord.ButtonStyle.secondary, emoji="📊", row=2)
    async def logs_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.edit_message(embed=logging.get_embed(), view=self)

    @discord.ui.button(label="Roleplay", style=discord.ButtonStyle.secondary, emoji="🎭", row=2)
    async def roleplay_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.edit_message(embed=roleplay.get_embed(), view=self)

    @discord.ui.button(label="Creator", style=discord.ButtonStyle.success, emoji="📝", row=2)
    async def creator_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.edit_message(embed=creator_note.get_embed(), view=self)


class Help(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="help", description="The S.I.L.K. Master Manual")
    async def help_master(self, interaction: discord.Interaction):
        embed = discord.Embed(
            title="S.I.L.K. Help Dashboard",
            description="Select a module below to view its commands.\nNow supporting Secure Direct Messages (DM).",
            color=discord.Color.blurple()
        )
        embed.set_footer(text="Use the buttons to navigate categories.")

        view = HelpView()
        await interaction.response.send_message(embed=embed, view=view)

    @app_commands.command(name="creator-note", description="A personal note from the developer.")
    async def creator_note_cmd(self, interaction: discord.Interaction):
        await interaction.response.send_message(embed=creator_note.get_embed())

async def setup(bot):
    await bot.add_cog(Help(bot))
