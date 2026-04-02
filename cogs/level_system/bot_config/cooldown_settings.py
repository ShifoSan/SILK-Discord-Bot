import discord
from .. import database

class CooldownSettingsView(discord.ui.View):
    def __init__(self, bot, guild, config, parent_view):
        super().__init__(timeout=300)
        self.bot = bot
        self.guild = guild
        self.config = config
        self.parent_view = parent_view

    @discord.ui.select(placeholder="Text Cooldown...", options=[
        discord.SelectOption(label="10 seconds", value="10"),
        discord.SelectOption(label="30 seconds", value="30"),
        discord.SelectOption(label="60 seconds", value="60"),
        discord.SelectOption(label="120 seconds", value="120"),
    ], row=0)
    async def select_text(self, interaction: discord.Interaction, select: discord.ui.Select):
        cd = int(select.values[0])
        self.config["text_cooldown"] = cd
        await database.update_guild_config(self.guild.id, {"text_cooldown": cd})
        await interaction.response.send_message(f"✅ Text Cooldown set to **{cd} seconds**.", ephemeral=True)

    @discord.ui.select(placeholder="Reaction Cooldown...", options=[
        discord.SelectOption(label="10 seconds", value="10"),
        discord.SelectOption(label="30 seconds", value="30"),
        discord.SelectOption(label="60 seconds", value="60"),
        discord.SelectOption(label="120 seconds", value="120"),
    ], row=1)
    async def select_reaction(self, interaction: discord.Interaction, select: discord.ui.Select):
        cd = int(select.values[0])
        self.config["reaction_cooldown"] = cd
        await database.update_guild_config(self.guild.id, {"reaction_cooldown": cd})
        await interaction.response.send_message(f"✅ Reaction Cooldown set to **{cd} seconds**.", ephemeral=True)

    @discord.ui.select(placeholder="VC Cooldown...", options=[
        discord.SelectOption(label="10 seconds", value="10"),
        discord.SelectOption(label="30 seconds", value="30"),
        discord.SelectOption(label="60 seconds", value="60"),
        discord.SelectOption(label="120 seconds", value="120"),
    ], row=2)
    async def select_vc(self, interaction: discord.Interaction, select: discord.ui.Select):
        cd = int(select.values[0])
        self.config["vc_cooldown"] = cd
        await database.update_guild_config(self.guild.id, {"vc_cooldown": cd})
        await interaction.response.send_message(f"✅ VC Cooldown set to **{cd} seconds**.", ephemeral=True)

    @discord.ui.button(label="Back to Main Menu", style=discord.ButtonStyle.secondary, row=3)
    async def btn_back(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.edit_message(content="🔓 Welcome to the S.I.L.K. Level System Dashboard.", view=self.parent_view)
