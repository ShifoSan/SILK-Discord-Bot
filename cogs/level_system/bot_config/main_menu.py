import discord
from discord import app_commands
from discord.ext import commands
from .. import database

class DashboardView(discord.ui.View):
    def __init__(self, bot: discord.Client, guild: discord.Guild, config: dict):
        super().__init__(timeout=600)
        self.bot = bot
        self.guild = guild
        self.config = config

    @discord.ui.select(cls=discord.ui.ChannelSelect, channel_types=[discord.ChannelType.text], placeholder="Select Level-Up Channel...", row=2)
    async def select_level_channel(self, interaction: discord.Interaction, select: discord.ui.ChannelSelect):
        channel = select.values[0]
        self.config["level_up_channel"] = channel.id
        await database.update_guild_config(self.guild.id, {"level_up_channel": channel.id})
        await interaction.response.send_message(f"✅ Level-up messages will now be sent to {channel.mention}.", ephemeral=True)

    # FIXED: Moved button to row=3 to avoid the 5-width limit crash
    @discord.ui.button(label="Set Thread Name", style=discord.ButtonStyle.secondary, row=3)
    async def btn_thread_name(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not self.config.get("level_up_channel"):
            await interaction.response.send_message("❌ Please select a Level-Up Channel first!", ephemeral=True)
            return

        modal = ThreadNameModal(self.bot, self.guild, self.config)
        await interaction.response.send_modal(modal)

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


class ThreadNameModal(discord.ui.Modal, title="Set Level-Up Thread"):
    thread_name = discord.ui.TextInput(
        label="Thread Name",
        style=discord.TextStyle.short,
        placeholder="e.g. Level Ups!",
        required=True
    )

    def __init__(self, bot: discord.Client, guild: discord.Guild, config: dict):
        super().__init__()
        self.bot = bot
        self.guild = guild
        self.config = config

    async def on_submit(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)

        channel_id = self.config.get("level_up_channel")
        channel = self.guild.get_channel(channel_id)
        if not channel:
            await interaction.followup.send("❌ The configured Level-Up Channel no longer exists.", ephemeral=True)
            return

        try:
            thread = await channel.create_thread(
                name=self.thread_name.value,
                type=discord.ChannelType.public_thread
            )
            self.config["level_up_thread_id"] = thread.id
            await database.update_guild_config(self.guild.id, {"level_up_thread_id": thread.id})
            await interaction.followup.send(f"✅ Level-up messages will now be sent to {thread.mention}.", ephemeral=True)
        except discord.Forbidden:
            await interaction.followup.send("❌ I do not have permission to create threads in that channel.", ephemeral=True)
        except discord.HTTPException as e:
            await interaction.followup.send(f"❌ Failed to create thread: {e}", ephemeral=True)

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
        # 1. DEFER THE INTERACTION immediately to reset the 3-second timer to 15 minutes
        await interaction.response.defer(ephemeral=True)
        
        import os
        correct_pass = os.getenv("CONFIG_PASS", "admin")
        
        if self.password.value != correct_pass:
            # 2. Use followup since we already deferred
            await interaction.followup.send("❌ Incorrect password.", ephemeral=True)
            return

        config = await database.get_guild_config(interaction.guild_id)
        view = DashboardView(self.bot, interaction.guild, config)
        
        # 3. Use followup for the successful response too
        await interaction.followup.send("🔓 Welcome to the S.I.L.K. Level System Dashboard.", view=view, ephemeral=True)


class BotConfigCommand(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="bot_config", description="Configure S.I.L.K. modules.")
    async def run_bot_config(self, interaction: discord.Interaction, show_stats: bool = False):
        if show_stats:
            await interaction.response.defer(ephemeral=True)
            config = await database.get_guild_config(interaction.guild_id)

            embed = discord.Embed(title="Level System Configuration", color=discord.Color.green())
            embed.add_field(name="Text Cooldown", value=f"{config.get('text_cooldown')}s")
            embed.add_field(name="Reaction Cooldown", value=f"{config.get('reaction_cooldown')}s")
            embed.add_field(name="VC XP Enabled", value=str(config.get('vc_xp_enabled')))
            embed.add_field(name="VC XP Rate", value=f"{config.get('vc_vc_xp_per_minute')} XP/min")
            embed.add_field(name="Spam Min Length", value=str(config.get('spam_min_length')))

            bl_len = len(config.get('spam_channels_blacklist', []))
            embed.add_field(name="Blacklisted Channels", value=str(bl_len))

            rw_len = len(config.get('role_rewards', {}))
            embed.add_field(name="Role Rewards", value=str(rw_len))

            lvl_up_chan = config.get("level_up_channel")
            embed.add_field(name="Level-Up Channel", value=f"<#{lvl_up_chan}>" if lvl_up_chan else "Not Set")

            await interaction.followup.send(embed=embed, ephemeral=True)
        else:
            if not interaction.user.guild_permissions.administrator:
                await interaction.response.send_message("❌ You need Administrator permissions to access the configuration dashboard.", ephemeral=True)
                return
            await interaction.response.send_modal(ConfigPasswordModal(self.bot))

async def setup(bot):
    await bot.add_cog(BotConfigCommand(bot))
    
