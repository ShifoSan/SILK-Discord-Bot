import discord
from discord import app_commands
from discord.ext import commands
from .. import database

class DashboardView(discord.ui.View):
    def __init__(self, bot: discord.Client, guild: discord.Guild, config: dict):
        super().__init__(timeout=300)
        self.bot = bot
        self.guild = guild
        self.config = config

    @discord.ui.button(label="Role Rewards", style=discord.ButtonStyle.primary, row=0)
    async def btn_roles(self, interaction: discord.Interaction, button: discord.ui.Button):
        from .role_rewards import RoleRewardsView
        await interaction.response.edit_message(content="Select a level and role to map.", view=RoleRewardsView(self.bot, self.guild, self.config, self), embed=None)

    @discord.ui.button(label="XP Management", style=discord.ButtonStyle.primary, row=0)
    async def btn_xp(self, interaction: discord.Interaction, button: discord.ui.Button):
        from .xp_management import XPManagementView
        await interaction.response.edit_message(content="Manage user XP and levels.", view=XPManagementView(self.bot, self.guild, self.config, self), embed=None)

    @discord.ui.button(label="VC Settings", style=discord.ButtonStyle.primary, row=0)
    async def btn_vc(self, interaction: discord.Interaction, button: discord.ui.Button):
        from .vc_settings import VCSettingsView
        await interaction.response.edit_message(content="Configure Voice Channel XP.", view=VCSettingsView(self.bot, self.guild, self.config, self), embed=None)

    @discord.ui.button(label="Spam Filters", style=discord.ButtonStyle.primary, row=1)
    async def btn_spam(self, interaction: discord.Interaction, button: discord.ui.Button):
        from .spam_filters import SpamFiltersView
        await interaction.response.edit_message(content="Configure Spam Filters and Blacklists.", view=SpamFiltersView(self.bot, self.guild, self.config, self), embed=None)

    @discord.ui.button(label="Cooldown Settings", style=discord.ButtonStyle.primary, row=1)
    async def btn_cooldowns(self, interaction: discord.Interaction, button: discord.ui.Button):
        from .cooldown_settings import CooldownSettingsView
        await interaction.response.edit_message(content="Configure XP Cooldowns.", view=CooldownSettingsView(self.bot, self.guild, self.config, self), embed=None)


class ConfigPasswordModal(discord.ui.Modal, title="Admin Authentication"):
    password = discord.ui.TextInput(
        label="Enter CONFIG_PASS",
        style=discord.TextStyle.short,
        placeholder="Master Dashboard Password",
        required=True
    )

    def __init__(self, bot: discord.Client):
        super().__init__()
        self.bot = bot

    async def on_submit(self, interaction: discord.Interaction):
        import os
        correct_pass = os.getenv("CONFIG_PASS", "admin")
        if self.password.value != correct_pass:
            await interaction.response.send_message("❌ Incorrect password.", ephemeral=True)
            return

        config = await database.get_guild_config(interaction.guild_id)
        view = DashboardView(self.bot, interaction.guild, config)
        await interaction.response.send_message("🔓 Welcome to the S.I.L.K. Level System Dashboard.", view=view, ephemeral=True)

class BotConfigCommand(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="bot_config", description="Configure S.I.L.K. modules.")
    async def run_bot_config(self, interaction: discord.Interaction, show_stats: bool = False):
        if show_stats:
            await interaction.response.defer(thinking=True)
            config = await database.get_guild_config(interaction.guild_id)

            embed = discord.Embed(title="Level System Configuration", color=discord.Color.green())
            embed.add_field(name="Text Cooldown", value=f"{config.get('text_cooldown')}s")
            embed.add_field(name="Reaction Cooldown", value=f"{config.get('reaction_cooldown')}s")
            embed.add_field(name="VC XP Enabled", value=str(config.get('vc_xp_enabled')))
            embed.add_field(name="VC XP Rate", value=f"{config.get('vc_xp_per_minute')} XP/min")
            embed.add_field(name="Spam Min Length", value=str(config.get('spam_min_length')))

            bl_len = len(config.get('spam_channels_blacklist', []))
            embed.add_field(name="Blacklisted Channels", value=str(bl_len))

            rw_len = len(config.get('role_rewards', {}))
            embed.add_field(name="Role Rewards", value=str(rw_len))

            await interaction.followup.send(embed=embed)
        else:
            if not interaction.user.guild_permissions.administrator:
                await interaction.response.send_message("❌ You need Administrator permissions to access the configuration dashboard.", ephemeral=True)
                return
            await interaction.response.send_modal(ConfigPasswordModal(self.bot))

async def setup(bot):
    await bot.add_cog(BotConfigCommand(bot))
