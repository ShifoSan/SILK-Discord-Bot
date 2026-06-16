import discord
import os
from discord.ext import commands
from dotenv import load_dotenv
from motor.motor_asyncio import AsyncIOMotorClient

load_dotenv()


# ──────────────────────────────────────────────
#  Dashboard UI Components
# ──────────────────────────────────────────────

class DashboardButton(discord.ui.Button):
    async def callback(self, interaction: discord.Interaction):
        view: "StarboardConfigView" = self.view

        if not interaction.user.guild_permissions.administrator:
            return await interaction.response.send_message(
                "❌ This setup panel belongs to administrators.", ephemeral=True
            )

        if self.custom_id == "toggle_power":
            view.is_enabled = not view.is_enabled
        elif self.custom_id == "toggle_emoji":
            view.trigger_emoji = "any" if view.trigger_emoji == "⭐" else "⭐"

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

        if not interaction.user.guild_permissions.administrator:
            return await interaction.response.send_message(
                "❌ This setup panel belongs to administrators.", ephemeral=True
            )

        view.channel_id = self.values[0].id

        await view.save_to_db()
        view.update_components()
        await interaction.response.edit_message(view=view)


# FIX: Changed parent class to LayoutView
class StarboardConfigView(discord.ui.LayoutView):
    def __init__(self, cog: "Starboard", guild_id: int, config: dict):
        super().__init__(timeout=300)
        self.cog = cog
        self.guild_id = guild_id

        sb_data = config.get("starboard", {})
        self.is_enabled = sb_data.get("is_enabled", False)
        self.channel_id = sb_data.get("channel_id", None)
        self.trigger_emoji = sb_data.get("trigger_emoji", "any")

        self.update_components()

    def update_components(self):
        """Re-builds the internal dashboard component tree."""
        self.clear_items()

        accent_color = discord.Color.from_rgb(255, 215, 0) if self.is_enabled else discord.Color.from_rgb(100, 100, 100)
        container = discord.ui.Container(accent_color=accent_color)

        status_str  = "🟢 Enabled" if self.is_enabled else "🔴 Disabled"
        channel_str = f"<#{self.channel_id}>" if self.channel_id else "❌ Not Set (Bot will ignore reactions)"
        rule_str    = "⭐ Stars Only" if self.trigger_emoji == "⭐" else "🌍 Any Emoji (4+ Count)"

        dashboard_text = (
            f"## ⭐ S.I.L.K. Starboard System\n\n"
            f"### Live Configuration Status\n"
            f"* **System Power:** {status_str}\n"
            f"* **Target Output Channel:** {channel_str}\n"
            f"* **Reaction Trigger Filter:** {rule_str}\n\n"
            f"> Use the interface buttons below to update your starboard environment parameters instantly."
        )

        container.add_item(discord.ui.TextDisplay(content=dashboard_text))
        self.add_item(container)

        # FIX: Standard buttons inside a LayoutView must reside within an ActionRow
        row_buttons = discord.ui.ActionRow()
        
        toggle_label = "Disable System" if self.is_enabled else "Enable System"
        toggle_style = discord.ButtonStyle.danger if self.is_enabled else discord.ButtonStyle.success
        row_buttons.add_item(DashboardButton(label=toggle_label, style=toggle_style, custom_id="toggle_power"))

        emoji_label = "Set to 'Any Emoji'" if self.trigger_emoji == "⭐" else "Set to '⭐ Only'"
        row_buttons.add_item(DashboardButton(label=emoji_label, style=discord.ButtonStyle.primary, custom_id="toggle_emoji"))
        self.add_item(row_buttons)

        # FIX: Dropdown selectors must also reside within an ActionRow inside a LayoutView
        row_select = discord.ui.ActionRow()
        row_select.add_item(DashboardChannelSelect())
        self.add_item(row_select)

    async def save_to_db(self):
        """Pushes the current view state back to MongoDB Atlas."""
        payload = {
            "starboard.is_enabled":    self.is_enabled,
            "starboard.channel_id":    self.channel_id,
            "starboard.trigger_emoji": self.trigger_emoji,
        }
        await self.cog.collection.update_one(
            {"guild_id": self.guild_id},
            {"$set": payload},
            upsert=True
        )


# ──────────────────────────────────────────────
#  Starboard Highlight Post (top-level, not nested)
# ──────────────────────────────────────────────

# FIX: Changed parent class to LayoutView
class StarboardPostView(discord.ui.LayoutView):
    """Persistent, non-interactive view for a starboard highlight card."""

    def __init__(self, message: discord.Message):
        super().__init__(timeout=None)

        user_avatar = message.author.display_avatar.url if message.author.display_avatar else None

        container = discord.ui.Container(accent_color=discord.Color.from_rgb(255, 215, 0))

        # Guard against empty content crashing len()
        safe_content = message.content or ""
        if len(safe_content) > 3900:
            safe_content = safe_content[:3900] + "... [Read More]"

        body_text = safe_content if safe_content else "*[Media Highlight]*"

        if message.attachments:
            body_text += f"\n\n![Attachment]({message.attachments[0].url})"

        header_text = f"### ⭐ Highlight | {message.author.display_name}\n\n"
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

        # FIX: Link buttons inside a LayoutView must reside within an ActionRow
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
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        # Self-contained connection — no dependency on bot.db
        self._mongo_client = AsyncIOMotorClient(os.getenv("MONGO_URI"))
        self.collection = self._mongo_client["silk_db"]["chat_configs"]

    def cog_unload(self):
        """Close the MongoDB connection cleanly when the cog is unloaded or reloaded."""
        self._mongo_client.close()

    # ── Dashboard Command ──────────────────────

    @commands.command(name="sb")
    async def starboard_dashboard(self, ctx: commands.Context):
        if not ctx.author.guild_permissions.administrator:
            return

        config = await self.collection.find_one({"guild_id": ctx.guild.id})
        if not config:
            config = {
                "guild_id": ctx.guild.id,
                "starboard": {
                    "is_enabled":     False,
                    "channel_id":     None,
                    "trigger_emoji":  "any",
                    "posted_messages": []
                }
            }
            await self.collection.insert_one(config)

        view = StarboardConfigView(self, ctx.guild.id, config)
        await ctx.send(view=view)

    # ── Reaction Listener ──────────────────────

    @commands.Cog.listener()
    async def on_raw_reaction_add(self, payload: discord.RawReactionActionEvent):
        """Bypasses cache to detect starboard reaction thresholds globally."""

        # FIX: Guard against DM reactions — payload.guild_id is None in DMs
        if not payload.guild_id:
            return

        # Ignore bot reactions
        if payload.member and payload.member.bot:
            return

        # Fetch config & quick-kill if starboard isn't set up
        config = await self.collection.find_one({"guild_id": payload.guild_id})
        if not config:
            return

        sb_data = config.get("starboard", {})

        if not sb_data.get("is_enabled", False):
            return

        target_channel_id = sb_data.get("channel_id")
        if not target_channel_id:
            return

        # FIX: Prevent self-starring — reactions inside the starboard channel are ignored
        if payload.channel_id == target_channel_id:
            return

        # Check emoji filter
        trigger_rule = sb_data.get("trigger_emoji", "any")
        if trigger_rule == "⭐" and str(payload.emoji) != "⭐":
            return

        # FIX: Catch Forbidden and HTTPException, not just NotFound
        try:
            channel = await self.bot.fetch_channel(payload.channel_id)
            message = await channel.fetch_message(payload.message_id)
        except (discord.NotFound, discord.Forbidden, discord.HTTPException):
            return

        # Verify the reaction count crosses the 4+ threshold
        hit_threshold = any(
            reaction.count >= 4
            for reaction in message.reactions
            if trigger_rule == "any" or str(reaction.emoji) == "⭐"
        )

        if not hit_threshold:
            return

        # Anti-duplication atomic lock
        update_result = await self.collection.update_one(
            {
                "guild_id": payload.guild_id,
                "starboard.posted_messages": {"$ne": message.id}
            },
            {
                "$push": {
                    "starboard.posted_messages": {
                        "$each":  [message.id],
                        "$slice": -150
                    }
                }
            }
        )

        # modified_count == 0 means the ID was already tracked — abort to prevent duplicate posts
        if update_result.modified_count == 0:
            return

        # FIX: Wrap the final send in error handling — channel may have been deleted or perms revoked
        try:
            target_channel = self.bot.get_channel(target_channel_id) or await self.bot.fetch_channel(target_channel_id)
            await target_channel.send(view=StarboardPostView(message))
        except (discord.NotFound, discord.Forbidden, discord.HTTPException):
            return


async def setup(bot: commands.Bot):
    await bot.add_cog(Starboard(bot))
