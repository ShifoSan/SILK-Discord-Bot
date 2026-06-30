import discord
from discord.ext import commands
import re
import asyncio

# --- UI COMPONENTS V2 DASHBOARD FACTORY ---
def build_dashboard_view(handler, guild_id: int) -> discord.ui.LayoutView:
    """
    Constructs the Settings Dashboard.
    Components V2 items (Container, TextDisplay) only work inside a
    discord.ui.LayoutView -- a plain discord.ui.View rejects them outright.
    LayoutView also doesn't auto-wrap loose buttons/selects into ActionRows
    the way View does, so each interactive item needs its own explicit
    discord.ui.ActionRow.
    """
    view = discord.ui.LayoutView(timeout=300)

    # 1. Base Container & Text Block
    container = discord.ui.Container(accent_color=discord.Color(0x3498DB))

    # Safely fetch current locks, defaulting to an empty set if none exist
    current_locks = handler.locked_channels.get(guild_id, set())

    # Build responsive status text
    if current_locks:
        ch_mentions = ", ".join(f"<#{ch_id}>" for ch_id in current_locks)
        status_text = f"🔒 **Currently Locked To:**
{ch_mentions}"
    else:
        status_text = "🔓 **Currently Unlocked:**
Prefix commands are allowed in ALL channels."

    container.add_item(discord.ui.TextDisplay(
        "### ⚙️ S.I.L.K. Prefix Configuration
"
        "Select up to 25 channels below where the `?` prefix should be active.

"
        f"{status_text}"
    ))
    view.add_item(container)

    # 2. Native Dropdown Component (Interactive)
    select_kwargs = {}
    if current_locks:
        # Pre-select currently-locked channels so reopening the dashboard
        # doesn't wipe them out the moment you only pick a channel to add.
        select_kwargs["default_values"] = [discord.Object(id=ch_id) for ch_id in current_locks]

    select = discord.ui.ChannelSelect(
        channel_types=[discord.ChannelType.text],
        placeholder="Select allowed command channels...",
        min_values=1,
        max_values=25,
        **select_kwargs,
    )

    async def select_callback(interaction: discord.Interaction):
        if not interaction.user.guild_permissions.manage_guild:
            return await interaction.response.send_message("❌ Unauthorized: You need Manage Server permissions.", ephemeral=True)
        selected_ids = {channel.id for channel in select.values}
        await handler.update_guild_locks(guild_id, selected_ids)
        new_view = build_dashboard_view(handler, guild_id)
        await interaction.response.edit_message(view=new_view)

    select.callback = select_callback
    view.add_item(discord.ui.ActionRow(select))

    # 3. Reset / Unlock Button (Interactive)
    reset_btn = discord.ui.Button(
        label="Allow in All Channels",
        style=discord.ButtonStyle.danger
    )

    async def reset_callback(interaction: discord.Interaction):
        if not interaction.user.guild_permissions.manage_guild:
            return await interaction.response.send_message("❌ Unauthorized: You need Manage Server permissions.", ephemeral=True)
        await handler.clear_guild_locks(guild_id)
        new_view = build_dashboard_view(handler, guild_id)
        await interaction.response.edit_message(view=new_view)

    reset_btn.callback = reset_callback
    view.add_item(discord.ui.ActionRow(reset_btn))

    return view



# --- CORE COG ROUTING & CACHE ---
class PrefixHandler(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        # Pre-compile regex once on startup to save CPU cycles per message
        self.trade_split_pattern = re.compile(r'\s+for\s+', re.IGNORECASE)
        
        # Connect to centralized MongoDB
        self.db_client = bot.mongo_client
        if self.db_client:
            self.config_collection = self.db_client["silk_bot"]["guild_configs"]
        else:
            self.config_collection = None
            print("Warning: MONGO_URI missing. Prefix channel configurations will NOT persist after bot reboots.")
            
        # RAM Cache: O(1) Time Complexity dictionary -> {guild_id: set(channel_id, channel_id)}
        self.locked_channels = {}

    async def cog_load(self):
        """Loads DB configs directly into RAM. Allows 0ms latency on message checks."""
        if self.config_collection is not None:
            try:
                cursor = self.config_collection.find({})
                async for doc in cursor:
                    # Convert the array stored in DB back to a python set()
                    self.locked_channels[doc["guild_id"]] = set(doc.get("allowed_channels", []))
            except Exception as e:
                print(f"Error loading prefix channel configs from MongoDB: {e}")

    # --- DATABASE SYNCHRONIZATION HELPERS ---
    async def update_guild_locks(self, guild_id: int, channel_ids: set):
        """Updates local memory and pushes changes to MongoDB."""
        self.locked_channels[guild_id] = channel_ids
        if self.config_collection is not None:
            try:
                await self.config_collection.update_one(
                    {"guild_id": guild_id},
                    {"$set": {"allowed_channels": list(channel_ids)}},  # Store as a list in Mongo
                    upsert=True
                )
            except Exception as e:
                print(f"Failed to update MongoDB with new locks: {e}")

    async def clear_guild_locks(self, guild_id: int):
        """Wipes the lock from local memory and deletes the config from MongoDB."""
        self.locked_channels.pop(guild_id, None)
        if self.config_collection is not None:
            try:
                await self.config_collection.delete_one({"guild_id": guild_id})
            except Exception as e:
                print(f"Failed to delete lock config from MongoDB: {e}")

    # --- MAIN LISTENER ---
    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        # 1. Foundational Gatekeeping: Ignore bots, DMs, and non-prefix messages
        if message.author.bot or not message.guild or not message.content.startswith('?'):
            return

        raw_content = message.content[1:].strip()
        if not raw_content:
            return

        # 2. Settings Dashboard Hook (?aotr)
        if raw_content.lower() == "aotr":
            if not message.author.guild_permissions.manage_guild:
                return await message.channel.send("❌ You require `Manage Server` permissions to configure this module.")
            
            dashboard = build_dashboard_view(self, message.guild.id)
            return await message.channel.send(view=dashboard)

        # 3. Channel Lock Check (Crucial execution point)
        # We query RAM (self.locked_channels) instead of the DB, taking roughly ~0.00001 seconds.
        guild_locks = self.locked_channels.get(message.guild.id)
        if guild_locks and message.channel.id not in guild_locks:
            return  # The bot silently ignores the message if triggered in a disabled channel.

        # 4. Filter Syntax Anomalies (e.g. typing just "???" or "? ")
        if len(raw_content) < 2 or raw_content.startswith('?'):
            return

        # 5. Dynamic Modular Routing
        trade_match = self.trade_split_pattern.split(raw_content)

        if len(trade_match) > 1:
            # Route to Trade Compare Module
            trade_cog = self.bot.get_cog("TradeCompare")
            if trade_cog:
                giving_items = trade_match[0].strip()
                getting_items = trade_match[1].strip()
                
                if giving_items and getting_items:
                    # Fire async task concurrently
                    asyncio.create_task(
                        trade_cog.execute_trade_compare(
                            destination=message.channel,
                            user=message.author,
                            giving=giving_items,
                            getting=getting_items
                        )
                    )
        else:
            # Route to Value Lookup Module
            value_cog = self.bot.get_cog("AoTRValue")
            if value_cog:
                # Fire async task concurrently
                asyncio.create_task(
                    value_cog.execute_value_lookup(
                        destination=message.channel,
                        user=message.author,
                        guild=message.guild,
                        item=raw_content
                    )
                )

async def setup(bot):
    await bot.add_cog(PrefixHandler(bot))
