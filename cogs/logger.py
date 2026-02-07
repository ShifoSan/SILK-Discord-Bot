import discord
from discord.ext import commands
from discord import app_commands
import json
import os
import asyncio

# Logic Modules
from cogs.logs import channels as log_channels_module
from cogs.logs import roles as log_roles_module
from cogs.logs import members as log_members_module
from cogs.logs import messages as log_messages_module
from cogs.logs import voice as log_voice_module

class Logger(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.config_path = "log_config.json"
        self.log_channels_map = {
            "channel_logs": "📊-channel-logs",
            "role_logs": "📊-role-logs",
            "member_logs": "📊-member-logs",
            "message_edit_logs": "📊-message-edit-logs",
            "message_delete_logs": "📊-message-delete-logs",
            "vc_logs": "📊-vc-logs"
        }

    def load_config(self):
        if os.path.exists(self.config_path):
            try:
                with open(self.config_path, "r") as f:
                    return json.load(f)
            except json.JSONDecodeError:
                return {}
        return {}

    def save_config(self, config):
        with open(self.config_path, "w") as f:
            json.dump(config, f, indent=4)

    async def get_log_channel(self, guild_id, log_type):
        config = self.load_config()
        if str(guild_id) not in config:
            return None
        channel_id = config[str(guild_id)].get(log_type)
        if not channel_id:
            return None
        return self.bot.get_channel(channel_id)

    @app_commands.command(name="setup_logs", description="Sets up the logging system (Idempotent).")
    @app_commands.checks.has_permissions(administrator=True)
    async def setup_logs(self, interaction: discord.Interaction):
        await interaction.response.defer(thinking=True)
        guild = interaction.guild
        config = self.load_config()
        guild_id = str(guild.id)

        if guild_id not in config:
            config[guild_id] = {}

        # Create Category
        category_name = "『LOGS』"
        category = discord.utils.get(guild.categories, name=category_name)

        overwrites = {
            guild.default_role: discord.PermissionOverwrite(view_channel=False),
            guild.me: discord.PermissionOverwrite(view_channel=True)
        }

        if not category:
            category = await guild.create_category(category_name, overwrites=overwrites)
        else:
             await category.edit(overwrites=overwrites)

        created_channels = []

        # Create Channels
        for key, channel_name in self.log_channels_map.items():
            channel = discord.utils.get(category.channels, name=channel_name)
            if not channel:
                channel = await guild.create_text_channel(channel_name, category=category)

            config[guild_id][key] = channel.id
            created_channels.append(channel.mention)

        self.save_config(config)
        await interaction.followup.send(f"✅ Logs configured. Linked to: {', '.join(created_channels)}")

    # --- Channel Events ---
    @commands.Cog.listener()
    async def on_guild_channel_create(self, channel):
        log_channel = await self.get_log_channel(channel.guild.id, "channel_logs")
        if log_channel:
            embed = await log_channels_module.log_channel_create(channel)
            await log_channel.send(embed=embed)

    @commands.Cog.listener()
    async def on_guild_channel_delete(self, channel):
        log_channel = await self.get_log_channel(channel.guild.id, "channel_logs")
        if log_channel:
            embed = await log_channels_module.log_channel_delete(channel)
            await log_channel.send(embed=embed)

    @commands.Cog.listener()
    async def on_guild_channel_update(self, before, after):
        log_channel = await self.get_log_channel(after.guild.id, "channel_logs")
        if log_channel:
            embed = await log_channels_module.log_channel_update(before, after)
            await log_channel.send(embed=embed)

    # --- Role Events ---
    @commands.Cog.listener()
    async def on_guild_role_create(self, role):
        log_channel = await self.get_log_channel(role.guild.id, "role_logs")
        if log_channel:
            embed = await log_roles_module.log_role_create(role)
            await log_channel.send(embed=embed)

    @commands.Cog.listener()
    async def on_guild_role_delete(self, role):
        log_channel = await self.get_log_channel(role.guild.id, "role_logs")
        if log_channel:
            embed = await log_roles_module.log_role_delete(role)
            await log_channel.send(embed=embed)

    @commands.Cog.listener()
    async def on_guild_role_update(self, before, after):
        log_channel = await self.get_log_channel(after.guild.id, "role_logs")
        if log_channel:
            embed = await log_roles_module.log_role_update(before, after)
            await log_channel.send(embed=embed)

    # --- Member Events ---
    @commands.Cog.listener()
    async def on_member_update(self, before, after):
        log_channel = await self.get_log_channel(after.guild.id, "member_logs")
        if log_channel:
            embed = await log_members_module.log_member_update(before, after)
            if embed:
                await log_channel.send(embed=embed)

    # --- Message Events ---
    @commands.Cog.listener()
    async def on_message_edit(self, before, after):
        if not before.guild: return
        log_channel = await self.get_log_channel(before.guild.id, "message_edit_logs")
        if log_channel:
            embed = log_messages_module.log_message_edit(before, after)
            if embed:
                await log_channel.send(embed=embed)

    @commands.Cog.listener()
    async def on_message_delete(self, message):
        if not message.guild: return
        log_channel = await self.get_log_channel(message.guild.id, "message_delete_logs")
        if log_channel:
            embed = log_messages_module.log_message_delete(message)
            if embed:
                await log_channel.send(embed=embed)

    # --- Voice Events ---
    @commands.Cog.listener()
    async def on_voice_state_update(self, member, before, after):
        log_channel = await self.get_log_channel(member.guild.id, "vc_logs")
        if log_channel:
            embed = log_voice_module.log_voice_event(member, before, after)
            if embed:
                await log_channel.send(embed=embed)

async def setup(bot):
    await bot.add_cog(Logger(bot))
