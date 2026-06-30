import discord
from discord.ext import commands
import re
import asyncio

# --- UI COMPONENTS V2 DASHBOARD FACTORY ---
def build_dashboard_view(handler, guild_id: int) -> discord.ui.LayoutView:
    """Dynamically constructs the Components V2 Dashboard for channel configuration."""
    view = discord.ui.LayoutView(timeout=300)
    container = discord.ui.Container(accent_color=discord.Color(0x3498DB))

    # Safely fetch current locks, defaulting to an empty set
    current_locks = handler.locked_channels.get(guild_id, set())

    # Build responsive status text
    if current_locks:
        ch_mentions = ", ".join(f"<#{ch_id}>" for ch_id in current_locks)
        status_text = f"🔒 **Currently Locked To:**\n{ch_mentions}"
    else:
        status_text = "🔓 **Currently Unlocked:**\nPrefix commands are allowed in ALL channels."

    # Construct the Components V2 visual block
    container.add_item(discord.ui.TextDisplay(
        "### ⚙️ S.I.L.K. Prefix Configuration\n"
        "Select up to 25 channels below where the `?` prefix should be active.\n\n"
        f"{status_text}"
    ))
    view.add_item(container)

    # 1. Native Dropdown Component (Multi-Select capability)
    select = discord.ui.ChannelSelect(
        channel_types=[discord.ChannelType.text],
        placeholder="Select allowed command channels...",
        min_values=1,
        max_values=25
    )

    async def select_callback(interaction: discord.Interaction):
        # Security: Prevent unauthorized users from clicking an old menu
        if not interaction.user.guild_permissions.manage_guild:
            return await interaction.response.send_message("❌ Unauthorized.", ephemeral=True)
        
        # Convert selected channels into an O(1) set
        selected_ids = {channel.id for channel in select.values}
        await handler.update_guild_locks(guild_id, selected_ids)
        
        # Re-render the LayoutView with the new state
        new_view = build_dashboard_view(handler, guild_id)
        await interaction.response.edit_message(view=new_view)

    select.callback = select_callback
    view.add_item(select)

    # 2. Reset / Unlock Button Component
    reset_btn = discord.ui.Button(
        label="Allow in All Channels", 
        style=discord.ButtonStyle.danger
    )

    async def reset_callback(interaction: discord.Interaction):
        if not interaction.user.guild_permissions.manage_guild:
            return await interaction.response.send_message("❌ Unauthorized.", ephemeral=True)
            
        await handler.clear_guild_locks(guild_id)
        
        new_view = build_dashboard_view(handler, guild_id)
        await interaction.response.edit_message(view=new_view)

    reset_btn.callback = reset_callback
    view.add_item(reset_btn)

    return view


# --- MECHANICAL CORE ---
class PrefixHandler(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.trade_split_pattern = re.compile(r'\s+for\s+', re.IGNORECASE)
        
        # Centralized MongoDB connection
        self.db_client = bot.mongo_client
        if self.db_client:
            self.config_collection = self.db_client["silk_bot"]["guild_configs"]
        else:
            self.config_collection = None
            print("Warning: MONGO_URI missing. PrefixHandler channel locks will not persist across restarts.")
            
        # High-Speed In-Memory Cache: Dict[guild_id: int, set[channel_id: int]]
        self.locked_channels = {}

    async def cog_load(self):
        """Pre-loads configurations into RAM to guarantee zero database latency on messages."""
        if self.config_collection is not None:
            try:
                cursor = self.config_collection.find({})
                async for doc in cursor:
                    # Convert stored lists back into O(1) lookup sets
                    self.locked_channels[doc["guild_id"]] = set(doc.get("allowed_channels", []))
            except Exception as e:
                print(f"Failed to load prefix channel configurations: {e}")

    # --- DATABASE SYNCHRONIZATION WRAPPERS ---
    async def update_guild_locks(self, guild_id: int, channel_ids: set):
        self.locked_channels[guild_id] = channel_ids
        if self.config_collection is not None:
            try:
                await self.config_collection.update_one(
                    {"guild_id": guild_id},
                    {"$set": {"allowed_channels": list(channel_ids)}},
                    upsert=True
                )
            except Exception as e:
                print(f"Failed to save prefix locks to DB: {e}")

    async def clear_guild_locks(self, guild_id: int):
        self.locked_channels.pop(guild_id, None)
        if self.config_collection is not None:
            try:
                await self.config_collection.delete_one({"guild_id": guild_id})
            except Exception as e:
                print(f"Failed to clear prefix locks from DB: {e}")

    # --- PREFIX LISTENER ---
    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        # Base safety gatekeeping
        if message.author.bot or not message.guild or not message.content.startswith('?'):
            return

        raw_content = message.content[1:].strip()
        if not raw_content:
            return

        # 1. Dashboard Trigger Hook (?aotr)
        if raw_content.lower() == "aotr":
            if not message.author.guild_permissions.manage_guild:
                # Silently fail or send ephemeral via bot? We will send standard warning.
                return await message.channel.send("❌ You require `Manage Server` permissions to configure this module.")
            
            # Dispatch Components V2 dashboard
            view = build_dashboard_view(self, message.guild.id)
            return await message.channel.send(view=view)

        # 2. Channel Gatekeeper Logic (O(1) Memory Check)
        guild_locks = self.locked_channels.get(message.guild.id)
        if guild_locks and message.channel.id not in guild_locks:
            return  # Silently drop the query if triggered outside designated zones

        # 3. Anomaly Filter
        if len(raw_content) < 2 or raw_content.startswith('?'):
            return

        # 4. Standard Cog Routing Logic
        trade_match = self.trade_split_pattern.split(raw_content)

        if len(trade_match) > 1:
            trade_cog = self.bot.get_cog("TradeCompare")
            if trade_cog:
                giving_items = trade_match[0].strip()
                getting_items = trade_match[1].strip()
                
                if giving_items and getting_items:
                    asyncio.create_task(
                        trade_cog.execute_trade_compare(
                            destination=message.channel,
                            user=message.author,
                            giving=giving_items,
                            getting=getting_items
                        )
                    )
        else:
            value_cog = self.bot.get_cog("AoTRValue")
            if value_cog:
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
