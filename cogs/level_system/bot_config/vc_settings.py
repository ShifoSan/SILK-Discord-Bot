import discord
from .. import database

class VCRateModal(discord.ui.Modal, title="VC XP Rate"):
    rate_input = discord.ui.TextInput(
        label="XP per Minute",
        style=discord.TextStyle.short,
        placeholder="e.g. 5",
        required=True
    )

    def __init__(self, guild, config):
        super().__init__()
        self.guild = guild
        self.config = config

    async def on_submit(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        try:
            rate = int(self.rate_input.value)
            if rate < 0:
                raise ValueError
        except ValueError:
            await interaction.followup.send("❌ Please enter a valid non-negative integer.", ephemeral=True)
            return

        self.config["vc_xp_per_minute"] = rate
        await database.update_guild_config(self.guild.id, {"vc_xp_per_minute": rate})
        await interaction.followup.send(f"✅ VC XP Rate set to **{rate} XP / minute**.", ephemeral=True)

class VCSettingsView(discord.ui.View):
    def __init__(self, bot, guild, config, parent_view):
        super().__init__(timeout=600)
        self.bot = bot
        self.guild = guild
        self.config = config
        self.parent_view = parent_view

    @discord.ui.button(label="Toggle VC XP", style=discord.ButtonStyle.primary, row=0)
    async def btn_toggle_vc(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.defer(ephemeral=True)
        current = self.config.get("vc_xp_enabled", True)
        self.config["vc_xp_enabled"] = not current
        await database.update_guild_config(self.guild.id, {"vc_xp_enabled": self.config["vc_xp_enabled"]})
        status = "Enabled" if self.config["vc_xp_enabled"] else "Disabled"
        await interaction.followup.send(f"✅ VC XP is now **{status}**.", ephemeral=True)

    @discord.ui.button(label="Set XP per Minute", style=discord.ButtonStyle.secondary, row=1)
    async def btn_set_rate(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(VCRateModal(self.guild, self.config))

    @discord.ui.button(label="Back to Main Menu", style=discord.ButtonStyle.secondary, row=2)
    async def btn_back(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.edit_message(content="🔓 Welcome to the S.I.L.K. Level System Dashboard.", view=self.parent_view)
