import discord
from discord import app_commands
from discord.ext import commands

class Moderation(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    async def check_hierarchy(self, interaction: discord.Interaction, target: discord.Member) -> bool:
        """
        Helper to check role hierarchy.
        Returns True if:
          - The command invoker's top role is higher than the target's.
          - The bot's top role is higher than the target's.
        Otherwise, sends an error embed and returns False.
        """
        # Check 1: User vs Target
        user_ok = interaction.user.top_role > target.top_role

        # Check 2: Bot vs Target
        bot_ok = interaction.guild.me.top_role > target.top_role

        if user_ok and bot_ok:
            return True

        # If failure, send error
        embed = discord.Embed(
            description="⛔ You cannot punish this user (Role Hierarchy).",
            color=discord.Color.red()
        )
        # We use response.send_message. If the command was deferred, this would fail,
        # but kick/ban are not deferred in our implementation.
        # If we add defer later, we'd need to check interaction.response.is_done().
        if interaction.response.is_done():
             await interaction.followup.send(embed=embed, ephemeral=True)
        else:
             await interaction.response.send_message(embed=embed, ephemeral=True)

        return False

    @app_commands.command(name="kick", description="Kick a user from the server")
    @app_commands.checks.has_permissions(kick_members=True)
    @app_commands.describe(user="The user to kick", reason="The reason for the kick")
    async def kick(self, interaction: discord.Interaction, user: discord.Member, reason: str = None):
        if not await self.check_hierarchy(interaction, user):
            return

        try:
            await user.kick(reason=reason)

            embed = discord.Embed(
                title="👢 User Kicked",
                description=f"{user.mention} has been kicked.",
                color=discord.Color.red()
            )
            if reason:
                embed.add_field(name="Reason", value=reason)

            await interaction.response.send_message(embed=embed)

        except discord.Forbidden:
            await interaction.response.send_message("❌ I do not have permission to kick this user.", ephemeral=True)
        except discord.HTTPException as e:
            await interaction.response.send_message(f"❌ An error occurred: {e}", ephemeral=True)

    @app_commands.command(name="ban", description="Ban a user from the server")
    @app_commands.checks.has_permissions(ban_members=True)
    @app_commands.describe(user="The user to ban", reason="The reason for the ban")
    async def ban(self, interaction: discord.Interaction, user: discord.Member, reason: str = None):
        if not await self.check_hierarchy(interaction, user):
            return

        try:
            await user.ban(reason=reason)

            embed = discord.Embed(
                title="🔨 User Banned",
                description=f"{user.mention} has been banned.",
                color=discord.Color.red()
            )
            if reason:
                embed.add_field(name="Reason", value=reason)

            await interaction.response.send_message(embed=embed)

        except discord.Forbidden:
            await interaction.response.send_message("❌ I do not have permission to ban this user.", ephemeral=True)
        except discord.HTTPException as e:
            await interaction.response.send_message(f"❌ An error occurred: {e}", ephemeral=True)

    @app_commands.command(name="unban", description="Unban a user by their ID")
    @app_commands.checks.has_permissions(ban_members=True)
    @app_commands.describe(user_id="The ID of the user to unban")
    async def unban(self, interaction: discord.Interaction, user_id: str):
        try:
            try:
                user_int = int(user_id)
            except ValueError:
                await interaction.response.send_message("❌ Invalid User ID format.", ephemeral=True)
                return

            user_obj = discord.Object(id=user_int)

            # Attempt to fetch user details for a nicer message
            user_name = user_id
            try:
                fetched_user = await self.bot.fetch_user(user_int)
                user_name = f"{fetched_user.name} ({fetched_user.id})"
            except:
                pass

            await interaction.guild.unban(user_obj)

            embed = discord.Embed(
                title="✅ User Unbanned",
                description=f"**{user_name}** has been unbanned.",
                color=discord.Color.green()
            )
            await interaction.response.send_message(embed=embed)

        except discord.Forbidden:
            await interaction.response.send_message("❌ I do not have permission to unban users.", ephemeral=True)
        except discord.HTTPException as e:
            await interaction.response.send_message(f"❌ An error occurred (User might not be banned): {e}", ephemeral=True)

    @app_commands.command(name="purge", description="Delete a number of messages with optional filters")
    @app_commands.checks.has_permissions(manage_messages=True)
    @app_commands.describe(
        amount="Number of messages to delete",
        user="Filter by a specific user",
        role="Filter by a specific role",
        only_users="Only delete messages from non-bot users",
        only_bots="Only delete messages from bots",
        has_link="Only delete messages containing a link"
    )
    async def purge(
        self,
        interaction: discord.Interaction,
        amount: int,
        user: discord.Member = None,
        role: discord.Role = None,
        only_users: bool = False,
        only_bots: bool = False,
        has_link: bool = False
    ):
        if only_users and only_bots:
            await interaction.response.send_message("❌ You cannot select both `only_users` and `only_bots`.", ephemeral=True)
            return

        if user and only_bots and not user.bot:
            await interaction.response.send_message("❌ You selected `only_bots` but provided a user who is not a bot.", ephemeral=True)
            return

        if user and only_users and user.bot:
            await interaction.response.send_message("❌ You selected `only_users` but provided a bot user.", ephemeral=True)
            return

        # Defer Protocol: Purging takes time
        await interaction.response.defer(thinking=True, ephemeral=True)

        def check(m: discord.Message):
            # 1. User check
            if user and m.author.id != user.id:
                return False

            # 2. Role check
            if role:
                # If author is not a member (e.g. webhook), they won't have roles
                if not isinstance(m.author, discord.Member) or role not in m.author.roles:
                    return False

            # 3. Only users check
            if only_users and m.author.bot:
                return False

            # 4. Only bots check
            if only_bots and not m.author.bot:
                return False

            # 5. Has link check
            if has_link and "http" not in m.content.lower():
                return False

            return True

        try:
            deleted = await interaction.channel.purge(limit=amount, check=check)

            embed = discord.Embed(
                description=f"✅ Purged {len(deleted)} messages.",
                color=discord.Color.green()
            )
            await interaction.followup.send(embed=embed)

        except discord.Forbidden:
            await interaction.followup.send("❌ I do not have permission to manage messages.")
        except discord.HTTPException as e:
            await interaction.followup.send(f"❌ An error occurred: {e}")

    @app_commands.command(name="slowmode", description="Set the slowmode delay for this channel")
    @app_commands.checks.has_permissions(manage_channels=True)
    @app_commands.describe(seconds="Seconds of delay (0 to disable)")
    async def slowmode(self, interaction: discord.Interaction, seconds: int):
        try:
            await interaction.channel.edit(slowmode_delay=seconds)
            await interaction.response.send_message(f"⏱️ Slowmode set to {seconds} seconds.")
        except discord.Forbidden:
            await interaction.response.send_message("❌ I do not have permission to manage channels.", ephemeral=True)
        except discord.HTTPException as e:
            await interaction.response.send_message(f"❌ An error occurred: {e}", ephemeral=True)

async def setup(bot):
    await bot.add_cog(Moderation(bot))
