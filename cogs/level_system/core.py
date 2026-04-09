import discord
from discord.ext import commands
from datetime import datetime, timezone
import random
import traceback
import asyncio
from . import database
from . import ai_responses

class LevelSystemCore(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    async def cog_load(self):
        # On load, scan for users currently in VC and start tracking them
        now = datetime.now(timezone.utc)
        for guild in self.bot.guilds:
            config = await database.get_guild_config(guild.id)
            if not config.get("vc_xp_enabled", True):
                continue
            for vc in guild.voice_channels:
                for member in vc.members:
                    if member.bot: continue
                    await database.save_user_data(guild.id, member.id, {"last_vc_join": now})

    def calculate_level_from_xp(self, xp: int) -> int:
        level = 0
        total_required = 0
        while True:
            xp_required = 5 * (level**2) + 50 * level + 100
            total_required += xp_required
            if xp >= total_required:
                level += 1
            else:
                break
        return level

    async def handle_level_up(self, message: discord.Message, user_data: dict, config: dict):
        current_xp = user_data["xp"]
        current_level = user_data["level"]

        # Calculate new level
        new_level = self.calculate_level_from_xp(current_xp)

        if new_level > current_level:
            # Save new level
            await database.save_user_data(message.guild.id, message.author.id, {"level": new_level})

            # Send message
            target_channel = message.channel
            if config.get("level_up_channel"):
                ch = message.guild.get_channel(config["level_up_channel"])
                if ch:
                    target_channel = ch

            if config.get("level_up_thread_id"):
                thread = message.guild.get_thread(config["level_up_thread_id"])
                if thread:
                    target_channel = thread

            ai_msg = await asyncio.to_thread(
                ai_responses.generate_level_up_message,
                message.author.display_name,
                new_level
            )

            # Rank Card Generation
            try:
                rank_pos = await database.get_user_rank(message.guild.id, message.author.id, sort_by_vc=False)
                total_xp_for_next_level = 0
                for l in range(new_level + 1):
                    total_xp_for_next_level += 5 * (l**2) + 50 * l + 100
                next_level_xp = total_xp_for_next_level

                avatar_asset = message.author.avatar if message.author.avatar else message.author.default_avatar
                avatar_bytes = await avatar_asset.read()

                from . import image_gen
                image_bytes = await asyncio.to_thread(
                    image_gen.generate_rank_card,
                    message.author.display_name,
                    avatar_bytes,
                    new_level,
                    current_xp,
                    next_level_xp,
                    rank_pos
                )
            except Exception as e:
                print(f"Failed to generate rank card for level up: {e}")
                image_bytes = None

            try:
                if image_bytes:
                    await target_channel.send(
                        content=f"{message.author.mention} {ai_msg}",
                        # Updated to WEBP extension
                        file=discord.File(fp=image_bytes, filename='levelup.webp')
                    )
                else:
                    await target_channel.send(f"{message.author.mention} {ai_msg}")
            except discord.Forbidden:
                pass

            # Role Rewards
            roles_to_add = []
            roles_to_remove = []
            role_rewards = config.get("role_rewards", {})

            # Find the highest earned role
            highest_earned_role_id = None
            for level_str, role_id in sorted(role_rewards.items(), key=lambda x: int(x[0])):
                level_req = int(level_str)
                if new_level >= level_req:
                    highest_earned_role_id = role_id

            if highest_earned_role_id:
                # Remove lower tier roles and add highest
                for level_str, role_id in role_rewards.items():
                    if role_id == highest_earned_role_id:
                        role = message.guild.get_role(int(role_id))
                        if role and role not in message.author.roles:
                            roles_to_add.append(role)
                    else:
                        role = message.guild.get_role(int(role_id))
                        if role and role in message.author.roles:
                            roles_to_remove.append(role)

                try:
                    if roles_to_remove:
                        await message.author.remove_roles(*roles_to_remove, reason=f"Level up to {new_level}")
                    if roles_to_add:
                        await message.author.add_roles(*roles_to_add, reason=f"Level up to {new_level}")
                except discord.Forbidden:
                    print(f"Missing permissions to manage roles in guild {message.guild.id}")

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        if message.author.bot or not message.guild: return

        config = await database.get_guild_config(message.guild.id)

        # Check spam filters
        if message.channel.id in config.get("spam_channels_blacklist", []): return
        if len(message.content) < config.get("spam_min_length", 5): return

        user_data = await database.get_user_data(message.guild.id, message.author.id)

        # Check cooldown
        now = datetime.now(timezone.utc)
        last_xp_time = user_data.get("last_text_xp")
        if last_xp_time:
            # Ensure it's timezone-aware for comparison
            if last_xp_time.tzinfo is None:
                last_xp_time = last_xp_time.replace(tzinfo=timezone.utc)
            delta = (now - last_xp_time).total_seconds()
            if delta < config.get("text_cooldown", 60):
                return

        # Grant XP
        min_xp = config.get("text_min_xp", 15)
        max_xp = config.get("text_max_xp", 25)
        # Ensure max_xp >= min_xp
        if max_xp < min_xp:
            max_xp = min_xp
        xp_gain = random.randint(min_xp, max_xp)
        new_xp = user_data["xp"] + xp_gain

        await database.save_user_data(message.guild.id, message.author.id, {
            "xp": new_xp,
            "last_text_xp": now,
            "in_server": True # Ensure they are marked active
        })

        user_data["xp"] = new_xp
        await self.handle_level_up(message, user_data, config)

    @commands.Cog.listener()
    async def on_raw_reaction_add(self, payload: discord.RawReactionActionEvent):
        if payload.member and payload.member.bot: return
        if not payload.guild_id: return

        try:
            channel = self.bot.get_channel(payload.channel_id)
            if not channel: return
            message = await channel.fetch_message(payload.message_id)
            if message.author.bot: return # No farming XP off bots
        except Exception:
            return

        config = await database.get_guild_config(payload.guild_id)
        user_data = await database.get_user_data(payload.guild_id, payload.user_id)

        now = datetime.now(timezone.utc)
        last_rxn_time = user_data.get("last_reaction_xp")
        if last_rxn_time:
            if last_rxn_time.tzinfo is None:
                last_rxn_time = last_rxn_time.replace(tzinfo=timezone.utc)
            delta = (now - last_rxn_time).total_seconds()
            if delta < config.get("reaction_cooldown", 60):
                return

        # Grant Reaction XP
        xp_gain = random.randint(5, 10)
        new_xp = user_data["xp"] + xp_gain

        await database.save_user_data(payload.guild_id, payload.user_id, {
            "xp": new_xp,
            "last_reaction_xp": now
        })

        # Minimal mockup of message for handle_level_up
        mock_message = type('obj', (object,), {
            'guild': channel.guild,
            'channel': channel,
            'author': payload.member
        })
        user_data["xp"] = new_xp
        await self.handle_level_up(mock_message, user_data, config)

    @commands.Cog.listener()
    async def on_voice_state_update(self, member: discord.Member, before: discord.VoiceState, after: discord.VoiceState):
        if member.bot: return

        config = await database.get_guild_config(member.guild.id)
        if not config.get("vc_xp_enabled", True): return

        now = datetime.now(timezone.utc)

        # Joined VC
        if not before.channel and after.channel:
            await database.save_user_data(member.guild.id, member.id, {"last_vc_join": now})

        # Left VC
        elif before.channel and not after.channel:
            user_data = await database.get_user_data(member.guild.id, member.id)
            join_time = user_data.get("last_vc_join")

            if join_time:
                if join_time.tzinfo is None:
                    join_time = join_time.replace(tzinfo=timezone.utc)
                delta_minutes = (now - join_time).total_seconds() / 60.0
                xp_per_min = config.get("vc_xp_per_minute", 5)
                gained_vc_xp = int(delta_minutes * xp_per_min)

                if gained_vc_xp > 0:
                    new_vc_xp = user_data.get("vc_xp", 0) + gained_vc_xp
                    # Add VC xp to main XP too, or keep separate? Let's keep separate for VC leaderboard,
                    # but also add to main XP so VC counts towards total level.
                    new_total_xp = user_data.get("xp", 0) + gained_vc_xp

                    await database.save_user_data(member.guild.id, member.id, {
                        "vc_xp": new_vc_xp,
                        "xp": new_total_xp,
                        "last_vc_join": None
                    })

                    user_data["xp"] = new_total_xp
                    # Construct mock message to handle level up via VC
                    if getattr(member.guild, 'system_channel', None):
                        mock_message = type('obj', (object,), {
                            'guild': member.guild,
                            'channel': member.guild.system_channel or next((c for c in member.guild.text_channels if c.permissions_for(member.guild.me).send_messages), None),
                            'author': member
                        })
                        if mock_message.channel:
                            await self.handle_level_up(mock_message, user_data, config)

    @commands.Cog.listener()
    async def on_member_remove(self, member: discord.Member):
        if member.bot: return
        await database.save_user_data(member.guild.id, member.id, {"in_server": False})

    @commands.Cog.listener()
    async def on_member_join(self, member: discord.Member):
        if member.bot: return
        # Check if they exist
        user = await database.users_collection.find_one({"guild_id": member.guild.id, "user_id": member.id})
        if user:
            await database.save_user_data(member.guild.id, member.id, {"in_server": True})

async def setup(bot):
    await bot.add_cog(LevelSystemCore(bot))
    
