import discord
from .. import database

class VCSettingsView(discord.ui.View):
    def __init__(self, bot, guild, config, parent_view):
        super().__init__(timeout=300)
        self.bot = bot
        self.guild = guild
        self.config = config
        self.parent_view = parent_view

    @discord.ui.button(label="Toggle VC XP", style=discord.ButtonStyle.primary, row=0)
    async def btn_toggle_vc(self, interaction: discord.Interaction, button: discord.ui.Button):
        current = self.config.get("vc_xp_enabled", True)
        self.config["vc_xp_enabled"] = not current
        await database.update_guild_config(self.guild.id, {"vc_xp_enabled": self.config["vc_xp_enabled"]})
        status = "Enabled" if self.config["vc_xp_enabled"] else "Disabled"
        await interaction.response.send_message(f"✅ VC XP is now **{status}**.", ephemeral=True)

    @discord.ui.select(placeholder="Set XP per Minute...", options=[
        discord.SelectOption(label="1 XP / min", value="1"),
        discord.SelectOption(label="5 XP / min", value="5"),
        discord.SelectOption(label="10 XP / min", value="10"),
        discord.SelectOption(label="20 XP / min", value="20"),
    ], row=1)
    async def select_rate(self, interaction: discord.Interaction, select: discord.ui.Select):
        rate = int(select.values[0])
        self.config["vc_xp_per_minute"] = rate
        await database.update_guild_config(self.guild.id, {"vc_xp_per_minute": rate})
        await interaction.response.send_message(f"✅ VC XP Rate set to **{rate} XP / minute**.", ephemeral=True)

    @discord.ui.button(label="Back to Main Menu", style=discord.ButtonStyle.secondary, row=2)
    async def btn_back(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.edit_message(content="🔓 Welcome to the S.I.L.K. Level System Dashboard.", view=self.parent_view)
