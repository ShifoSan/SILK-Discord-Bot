import discord
import logging
import asyncio
from discord.ext import commands
from typing import Optional, Dict, Any
from datetime import datetime, timedelta
from collections import OrderedDict

logger = logging.getLogger(__name__)

# ──────────────────────────────────────────────
#  Constants & Utilities
# ──────────────────────────────────────────────

class StarboardConstants:
    """Centralized configuration constants for the Starboard system."""
    DEFAULT_EMOJI = "⭐"
    TRIGGER_ANY = "any"
    REACTION_THRESHOLD = 4
    MAX_POSTED_HISTORY = 150
    MAX_CONTENT_LENGTH = 3900
    CONTENT_TRUNCATION_SUFFIX = "... [Read More]"
    ACCENT_GOLD = (255, 215, 0)
    ACCENT_GRAY = (100, 100, 100)
    DASHBOARD_TIMEOUT = 300  # seconds
    MONGO_TIMEOUT_MS = 5000  # 5 second timeout for DB operations
    CACHE_TTL_SECONDS = 300  # 5 minute TTL for guild config cache
    EMBED_ACCENT_COLOR = discord.Color.from_rgb(255, 215, 0)


class BoundedSet:
    """A memory-efficient set with a maximum capacity to prevent memory leaks."""
    def __init__(self, maxsize: int):
        self.maxsize = maxsize
        self._cache = OrderedDict()

    def add(self, item: int):
        self._cache[item] = None
        if len(self._cache) > self.maxsize:
            self._cache.popitem(last=False)

    def __contains__(self, item: int) -> bool:
        return item in self._cache

    def discard(self, item: int):
        self._cache.pop(item, None)

    def clear(self):
        self._cache.clear()


def sanitize_mentions(message: discord.Message) -> str:
    """
    Sanitizes message content to prevent any pings in starboard reposts.
    """
    content = message.clean_content or ""
    content = content.replace("@everyone", "@\u200beveryone")
    content = content.replace("@here", "@\u200bhere")
    content = content.replace("@EVERYONE", "@\u200bEVERYONE")
    content = content.replace("@HERE", "@\u200bHERE")
    content = content.replace("@Everyone", "@\u200bEveryone")
    content = content.replace("@Here", "@\u200bHere")

    import re
    content = re.sub(r'@everyone', '@\u200beveryone', content, flags=re.IGNORECASE)
    content = re.sub(r'@here', '@\u200bhere', content, flags=re.IGNORECASE)

    return content


def truncate_content(content: str, max_length: int = StarboardConstants.MAX_CONTENT_LENGTH) -> str:
    """Safely truncates content to Discord's limits with suffix."""
    if len(content) <= max_length:
        return content
    return content[:max_length] + StarboardConstants.CONTENT_TRUNCATION_SUFFIX


# ──────────────────────────────────────────────
#  Dashboard UI Components
# ──────────────────────────────────────────────

class StarboardSettingsModal(discord.ui.Modal):
    def __init__(self, view: "StarboardConfigView"):
        super().__init__(title="Starboard Advanced Settings")
        self.config_view = view
        
        self.allowed_channels_input = discord.ui.TextInput(
            label="Allowed Channel IDs",
            placeholder="Comma-separated IDs (Leave blank for all)",
            style=discord.TextStyle.paragraph,
            required=False,
            default=",".join(map(str, view.allowed_channels)) if view.allowed_channels else ""
        )
        self.add_item(self.allowed_channels_input)
        
        self.threshold_input = discord.ui.TextInput(
            label="Reaction Threshold",
            placeholder="e.g. 4",
            style=discord.TextStyle.short,
            required=True,
            default=str(view.reaction_threshold)
        )
        self.add_item(self.threshold_input)

    async def on_submit(self, interaction: discord.Interaction):
        # Process threshold
        try:
            threshold = int(self.threshold_input.value.strip())
            if threshold < 1:
                threshold = 1
            self.config_view.reaction_threshold = threshold
        except ValueError:
            pass # Keep old threshold if input is invalid

        # Process locked channels
        raw_channels = self.allowed_channels_input.value.strip()
        new_channels = []
        if raw_channels:
            # Replaces newlines to catch accidental enter presses
            for part in raw_channels.replace("\n", ",").split(","):
                part = part.strip()
                if part.isdigit():
                    new_channels.append(int(part))
        
        self.config_view.allowed_channels = new_channels

        await self.config_view.save_to_db()
        self.config_view.update_components()
        await interaction.response.edit_message(view=self.config_view)


class DashboardSettingsButton(discord.ui.Button):
    def __init__(self):
        super().__init__(
            label="Advanced Settings",
            style=discord.ButtonStyle.secondary,
            custom_id="open_settings",
            emoji="⚙️"
        )

    async def callback(self, interaction: discord.Interaction):
        if not interaction.user or not interaction.user.guild_permissions.administrator:
            return await interaction.response.send_message(
                "\u274c This setup panel is restricted to administrators.", ephemeral=True
            )

        modal = StarboardSettingsModal(self.view)
        await interaction.response.send_modal(modal)


class DashboardButton(discord.ui.Button):
    async def callback(self, interaction: discord.Interaction):
        view: "StarboardConfigView" = self.view

        if not interaction.user or not interaction.user.guild_permissions.administrator:
            return await interaction.response.send_message(
                "\u274c This setup panel is restricted to administrators.", ephemeral=True
            )

        if self.custom_id == "toggle_power":
            view.is_enabled = not view.is_enabled
        elif self.custom_id == "toggle_emoji":
            view.trigger_emoji = (
                StarboardConstants.TRIGGER_ANY
                if view.trigger_emoji == StarboardConstants.DEFAULT_EMOJI
                else StarboardConstants.DEFAULT_EMOJI
            )

        await view.save_to_db()
        view.update_components()
        await interaction.response.edit_message(view=view)


class DashboardChannelSelect(discord.ui.ChannelSelect):
    def __init__(self):
        super().__init__(
            placeholder="Select Starboard Target Channel...",
            channel_types=[discord.ChannelType.text],
            custom_id="select_channel"
        )

    async def callback(self, interaction: discord.Interaction):
        view: "StarboardConfigView" = self.view

        if not interaction.user or not interaction.user.guild_permissions.administrator:
            return await interaction.response.send_message(
                "\u274c This setup panel is restricted to administrators.", ephemeral=True
            )

        view.channel_id = self.values[0].id

        await view.save_to_db()
        view.update_components()
        await interaction.response.edit_message(view=view)


class StarboardConfigView(discord.ui.LayoutView):
    """Persistent dashboard for configuring the starboard system."""

    def __init__(self, cog: "Starboard", guild_id: int, config: dict):
        super().__init__(timeout=StarboardConstants.DASHBOARD_TIMEOUT)
        self.cog = cog
        self.guild_id = guild_id

        sb_data = config.get("starboard", {})
        self.is_enabled = sb_data.get("is_enabled", False)
        self.channel_id = sb_data.get("channel_id", None)
        self.trigger_emoji = sb_data.get("trigger_emoji", StarboardConstants.TRIGGER_ANY)
        
        self.reaction_threshold = sb_data.get("reaction_threshold", StarboardConstants.REACTION_THRESHOLD)
        self.allowed_channels = sb_data.get("allowed_channels", [])

        self.update_components()

    def update_components(self):
        """Re-builds the internal dashboard component tree."""
        self.clear_items()

        accent_color = (
            discord.Color.from_rgb(*StarboardConstants.ACCENT_GOLD)
            if self.is_enabled
            else discord.Color.from_rgb(*StarboardConstants.ACCENT_GRAY)
        )
        container = discord.ui.Container(accent_color=accent_color)

        status_str  = "\ud83d\udfe2 Enabled" if self.is_enabled else "\ud83d\udd34 Disabled"
        channel_str = f"<#{self.channel_id}>" if self.channel_id else "\u274c Not Set (Bot will ignore reactions)"
        rule_str    = (
            "\u2b50 Stars Only"
            if self.trigger_emoji == StarboardConstants.DEFAULT_EMOJI
            else "\ud83c\udf0e Any Emoji"
        )

        # Build allowed channels str safely to avoid breaking discord text lengths
        if self.allowed_channels:
            channels_str = ", ".join(f"<#{c}>" for c in self.allowed_channels)
            if len(channels_str) > 500:
                channels_str = channels_str[:495] + "..."
        else:
            channels_str = "All Channels"

        dashboard_text = (
            f"## \u2b50 S.I.L.K. Starboard System\n\n"
            f"### Live Configuration Status\n"
            f"* **System Power:** {status_str}\n"
            f"* **Target Output Channel:** {channel_str}\n"
            f"* **Reaction Trigger Filter:** {rule_str}\n"
            f"* **Reaction Threshold:** {self.reaction_threshold} Reactions\n"
            f"* **Allowed Channels:** {channels_str}\n\n"
            f"> Use the interface below to update your starboard settings."
        )

        container.add_item(discord.ui.TextDisplay(content=dashboard_text))
        self.add_item(container)

        # Buttons must reside within an ActionRow
        row_buttons = discord.ui.ActionRow()

        toggle_label = "Disable System" if self.is_enabled else "Enable System"
        toggle_style = discord.ButtonStyle.danger if self.is_enabled else discord.ButtonStyle.success
        row_buttons.add_item(DashboardButton(
            label=toggle_label,
            style=toggle_style,
            custom_id="toggle_power"
        ))

        emoji_label = (
            "Set to 'Any Emoji'"
            if self.trigger_emoji == StarboardConstants.DEFAULT_EMOJI
            else "Set to '\u2b50 Only'"
        )
        row_buttons.add_item(DashboardButton(
            label=emoji_label,
            style=discord.ButtonStyle.primary,
            custom_id="toggle_emoji"
        ))
        
        row_buttons.add_item(DashboardSettingsButton())
        
        self.add_item(row_buttons)

        # Dropdown selectors must also reside within an ActionRow
        row_select = discord.ui.ActionRow()
        row_select.add_item(DashboardChannelSelect())
        self.add_item(row_select)

    async def save_to_db(self):
        """Pushes the current view state back to MongoDB Atlas with timeout."""
        payload = {
            "starboard.is_enabled":    self.is_enabled,
            "starboard.channel_id":    self.channel_id,
            "starboard.trigger_emoji": self.trigger_emoji,
            "starboard.reaction_threshold": self.reaction_threshold,
            "starboard.allowed_channels": self.allowed_channels,
        }
        try:
            await self.cog.collection.update_one(
                {"guild_id": self.guild_id},
                {"$set": payload},
                upsert=True
            )
            # FIX: Forcefully invalidate the cog cache immediately to sync configurations
            self.cog._invalidate_cache(self.guild_id)
        except Exception as e:
            logger.error(f"Failed to save starboard config for guild {self.guild_id}: {e}")
            raise


# ──────────────────────────────────────────────
#  Starboard Highlight Post
# ──────────────────────────────────────────────

class StarboardPostView(discord.ui.LayoutView):
    """Persistent, non-interactive view for a starboard highlight card."""

    def __init__(self, message: discord.Message):
        super().__init__(timeout=None)

        user_avatar = message.author.display_avatar.url if message.author.display_avatar else None

        container = discord.ui.Container(accent_color=StarboardConstants.EMBED_ACCENT_COLOR)

        # SECURITY FIX: Sanitize ALL mentions to prevent pings
        safe_content = sanitize_mentions(message)
        safe_content = truncate_content(safe_content)

        body_text = safe_content if safe_content else "*[Media Highlight]*"

        # Handle attachments — include first image if present
        if message.attachments:
            first_attachment = message.attachments[0]
            if first_attachment.content_type and first_attachment.content_type.startswith("image/"):
                body_text += f"\n\n![Attachment]({first_attachment.url})"
            else:
                body_text += f"\n\n\ud83d\udcc4 [Attachment: {first_attachment.filename}]({first_attachment.url})"

        header_text = f"### \u2b50 Highlight | {message.author.display_name}\n\n"
        full_text = header_text + body_text

        if user_avatar:
            section = discord.ui.Section(
                discord.ui.TextDisplay(content=full_text),
                accessory=discord.ui.Thumbnail(user_avatar)
            )
            container.add_item(section)
        else:
            container.add_item(discord.ui.TextDisplay(content=full_text))

        self.add_item(container)

        # Link button inside an ActionRow
        row_link = discord.ui.ActionRow()
        row_link.add_item(discord.ui.Button(
            style=discord.ButtonStyle.link,
            url=message.jump_url,
            label="Jump to Original Message"
        ))
        self.add_item(row_link)


# ──────────────────────────────────────────────
#  Cog
# ──────────────────────────────────────────────

class Starboard(commands.Cog):
    """Starboard system: highlights popular messages via reactions."""

    def __init__(self, bot: commands.Bot):
        self.bot = bot
        # Reuse the centralized MongoDB client managed by SilkBot.
        self.db_client = getattr(bot, "mongo_client", None)
        if self.db_client:
            self.collection = self.db_client["silk_db"]["chat_configs"]
        else:
            self.collection = None
            logger.warning("MONGO_URI not found. Starboard module is non-functional.")

        # In-memory caches for efficiency
        # Maps guild_id -> (config_dict, expiry_timestamp)
        self._config_cache: Dict[int, tuple[dict, float]] = {}
        
        # Set of message IDs already posted (avoids DB + API calls) bounded to prevent memory leaks
        self._posted_cache = BoundedSet(5000)
        
        # Set of message IDs currently being processed (prevents race conditions)
        self._in_flight: set[int] = set()

    # ── Cache Management ───────────────────────

    def _get_cached_config(self, guild_id: int) -> Optional[dict]:
        """Returns cached config if still valid, else None."""
        entry = self._config_cache.get(guild_id)
        if entry is None:
            return None
        config, expiry = entry
        if datetime.utcnow().timestamp() > expiry:
            del self._config_cache[guild_id]
            return None
        return config

    def _set_cached_config(self, guild_id: int, config: dict):
        """Stores config in cache with TTL."""
        expiry = datetime.utcnow().timestamp() + StarboardConstants.CACHE_TTL_SECONDS
        self._config_cache[guild_id] = (config, expiry)

    def _invalidate_cache(self, guild_id: int):
        """Removes a guild's config from cache."""
        self._config_cache.pop(guild_id, None)

    # ── Dashboard Command ──────────────────────

    @commands.command(name="sb")
    async def starboard_dashboard(self, ctx: commands.Context):
        """Display the starboard configuration dashboard."""
        if not ctx.author.guild_permissions.administrator:
            return

        if self.collection is None:
            return await ctx.send("\u274c Database connection not available.")

        try:
            config = await self.collection.find_one(
                {"guild_id": ctx.guild.id}
            )
        except Exception as e:
            logger.error(f"DB error fetching config for guild {ctx.guild.id}: {e}")
            return await ctx.send("\u274c Database error. Please try again later.")

        if not config:
            config = {
                "guild_id": ctx.guild.id,
                "starboard": {
                    "is_enabled":     False,
                    "channel_id":     None,
                    "trigger_emoji":  StarboardConstants.TRIGGER_ANY,
                    "posted_messages": [],
                    "reaction_threshold": StarboardConstants.REACTION_THRESHOLD,
                    "allowed_channels": []
                }
            }
            try:
                await self.collection.insert_one(config)
            except Exception as e:
                logger.error(f"DB error creating config for guild {ctx.guild.id}: {e}")
                return await ctx.send("\u274c Failed to initialize configuration.")

        # Invalidate cache since we may have changed config
        self._invalidate_cache(ctx.guild.id)
        self._set_cached_config(ctx.guild.id, config)

        view = StarboardConfigView(self, ctx.guild.id, config)
        await ctx.send(view=view)

    # ── Reaction Listener ──────────────────────

    @commands.Cog.listener()
    async def on_raw_reaction_add(self, payload: discord.RawReactionActionEvent):
        """Bypasses cache to detect starboard reaction thresholds globally."""

        # Guard against DM reactions — payload.guild_id is None in DMs
        if not payload.guild_id:
            return

        # SECURITY: Ignore ALL bot reactions (handles uncached members too)
        if payload.user_id == self.bot.user.id:
            return
        # Fallback for other bots when member data is cached
        if payload.member and payload.member.bot:
            return

        if self.collection is None:
            return

        # EFFICIENCY: Check in-memory caches before touching DB or API
        if payload.message_id in self._posted_cache:
            return
        if payload.message_id in self._in_flight:
            return

        # Try cache first, then fall back to DB
        config = self._get_cached_config(payload.guild_id)
        if config is None:
            try:
                config = await self.collection.find_one(
                    {"guild_id": payload.guild_id}
                )
            except Exception as e:
                logger.error(f"DB error fetching config for guild {payload.guild_id}: {e}")
                return
            if config:
                self._set_cached_config(payload.guild_id, config)

        if not config:
            return

        sb_data = config.get("starboard", {})

        if not sb_data.get("is_enabled", False):
            return

        target_channel_id = sb_data.get("channel_id")
        if not target_channel_id:
            return

        # Prevent self-starring — reactions inside the starboard channel are ignored
        if payload.channel_id == target_channel_id:
            return

        # NEW CHECK: Process locked allowed channels filter
        allowed_channels = sb_data.get("allowed_channels", [])
        if allowed_channels and payload.channel_id not in allowed_channels:
            return

        # Check emoji filter
        trigger_rule = sb_data.get("trigger_emoji", StarboardConstants.TRIGGER_ANY)
        if trigger_rule == StarboardConstants.DEFAULT_EMOJI and str(payload.emoji) != StarboardConstants.DEFAULT_EMOJI:
            return

        # Mark as in-flight to prevent concurrent processing of the same message
        self._in_flight.add(payload.message_id)

        try:
            # Fetch channel and message from Discord API
            try:
                channel = await self.bot.fetch_channel(payload.channel_id)
                message = await channel.fetch_message(payload.message_id)
            except (discord.NotFound, discord.Forbidden, discord.HTTPException) as e:
                logger.debug(f"Failed to fetch message {payload.message_id}: {e}")
                return

            reaction_threshold = sb_data.get("reaction_threshold", StarboardConstants.REACTION_THRESHOLD)

            # Verify the reaction count crosses the configuration threshold
            hit_threshold = any(
                reaction.count >= reaction_threshold
                for reaction in message.reactions
                if trigger_rule == StarboardConstants.TRIGGER_ANY or str(reaction.emoji) == StarboardConstants.DEFAULT_EMOJI
            )

            if not hit_threshold:
                return

            # Anti-duplication atomic lock via DB
            try:
                update_result = await self.collection.update_one(
                    {
                        "guild_id": payload.guild_id,
                        "starboard.posted_messages": {"$ne": message.id}
                    },
                    {
                        "$push": {
                            "starboard.posted_messages": {
                                "$each":  [message.id],
                                "$slice": -StarboardConstants.MAX_POSTED_HISTORY
                            }
                        }
                    }
                )
            except Exception as e:
                logger.error(f"DB error during atomic update for message {message.id}: {e}")
                return

            # modified_count == 0 means already tracked — abort to prevent duplicates
            if update_result.modified_count == 0:
                self._posted_cache.add(message.id)
                return

            # SECURITY FIX: Send with allowed_mentions=none to prevent ANY pings
            try:
                target_channel = self.bot.get_channel(target_channel_id) or await self.bot.fetch_channel(target_channel_id)
                await target_channel.send(
                    view=StarboardPostView(message),
                    allowed_mentions=discord.AllowedMentions.none()
                )
                self._posted_cache.add(message.id)
                logger.info(f"Starboarded message {message.id} from guild {payload.guild_id}")
            except (discord.NotFound, discord.Forbidden, discord.HTTPException) as e:
                logger.warning(f"Failed to send starboard post for message {message.id}: {e}")
                # Remove from posted_messages so it can be retried later
                try:
                    await self.collection.update_one(
                        {"guild_id": payload.guild_id},
                        {"$pull": {"starboard.posted_messages": message.id}}
                    )
                except Exception as db_err:
                    logger.error(f"Failed to rollback posted_messages for {message.id}: {db_err}")
                return

        finally:
            self._in_flight.discard(payload.message_id)

    # ── Cleanup ────────────────────────────────

    def cog_unload(self):
        """Clean up caches when cog is unloaded."""
        self._config_cache.clear()
        self._posted_cache.clear()
        self._in_flight.clear()


async def setup(bot: commands.Bot):
    await bot.add_cog(Starboard(bot))
