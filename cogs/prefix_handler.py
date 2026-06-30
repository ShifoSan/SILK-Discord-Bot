import discord
from discord.ext import commands
import re
import asyncio

class ConfigModal(discord.ui.Modal, title="Configure Allowed Channels"):
    channel_ids = discord.ui.TextInput(
        label="Channel IDs (comma separated)",
        style=discord.TextStyle.paragraph,
        placeholder="e.g. 123456789012345678,987654321098765432",
        required=False,
        max_length=1000
    )

    def __init__(self, bot):
        super().__init__()
        self.bot = bot
        self.db_client = bot.mongo_client
        if self.db_client is not None:
            self.config_collection = self.db_client["silk_bot"]["server_configs"]
        else:
            self.config_collection = None

    async def on_submit(self, interaction: discord.Interaction):
        # FIXED: PyMongo collections must be explicitly checked against None
        if self.config_collection is None:
            return await interaction.response.send_message("❌ Database connection missing. Cannot save configuration.", ephemeral=True)
        
        raw_ids = self.channel_ids.value.strip()
        if raw_ids:
            # Extract digits and split by comma, cleaning up any accidental spaces
            id_list = [c_id.strip() for c_id in raw_ids.split(",") if c_id.strip().isdigit()]
        else:
            id_list = []

        # Save to the database
        await self.config_collection.update_one(
            {"guild_id": interaction.guild.id},
            {"$set": {"allowed_channels": id_list}},
            upsert=True
        )

        # Sync the high-speed local cache
        prefix_cog = self.bot.get_cog("PrefixHandler")
        if prefix_cog:
            prefix_cog.channel_cache[interaction.guild.id] = id_list

        if id_list:
            allowed_mentions = ", ".join(f"<#{c_id}>" for c_id in id_list)
            await interaction.response.send_message(f"✅ Prefix commands are now locked to:\n{allowed_mentions}", ephemeral=True)
        else:
            await interaction.response.send_message("✅ Restrictions removed. Prefix commands can now be used in all channels.", ephemeral=True)


class ConfigView(discord.ui.View):
    def __init__(self, bot):
        super().__init__(timeout=None)
        self.bot = bot

    @discord.ui.button(label="Configure Channels", style=discord.ButtonStyle.primary, custom_id="config_channels_btn")
    async def config_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        # Admin / Manager Gatekeeping
        if not interaction.user.guild_permissions.manage_guild:
            return await interaction.response.send_message("❌ You need `Manage Server` permissions to use this.", ephemeral=True)
        
        modal = ConfigModal(self.bot)
        
        # Pre-fill the modal with their current configuration for better UX
        prefix_cog = self.bot.get_cog("PrefixHandler")
        if prefix_cog and interaction.guild.id in prefix_cog.channel_cache:
            current_ids = prefix_cog.channel_cache[interaction.guild.id]
            if current_ids:
                modal.channel_ids.default = ",".join(current_ids)

        await interaction.response.send_modal(modal)


class PrefixHandler(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        # Compile the regex pattern once on startup for maximum execution speed
        self.trade_split_pattern = re.compile(r'\s+for\s+', re.IGNORECASE)
        
        self.db_client = bot.mongo_client
        if self.db_client is not None:
            self.config_collection = self.db_client["silk_bot"]["server_configs"]
        else:
            self.config_collection = None
            
        # In-memory dictionary mapped to handle Guild Configs at maximum speeds
        self.channel_cache = {}

    async def get_allowed_channels(self, guild_id: int):
        # Fetch directly from cache first
        if guild_id in self.channel_cache:
            return self.channel_cache[guild_id]
            
        # Fallback to database lookup if server configuration hasn't been cached yet
        # FIXED: PyMongo collections must be explicitly checked against None
        if self.config_collection is not None:
            doc = await self.config_collection.find_one({"guild_id": guild_id})
            if doc and "allowed_channels" in doc:
                self.channel_cache[guild_id] = doc["allowed_channels"]
                return doc["allowed_channels"]
                
        # Register an empty list in cache to prevent repeated database queries for the same server
        self.channel_cache[guild_id] = []
        return []

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        # 1. Gatekeeping: Quick exits to minimize CPU impact on busy servers
        if message.author.bot or not message.content.startswith('?'):
            return

        # Clean the input query string
        raw_content = message.content[1:].strip()
        if not raw_content:
            return

        # 2. Safety Guard: Ignore common conversational text anomalies 
        if len(raw_content) < 2 or raw_content.startswith('?'):
            return

        # 3. Intercept ?aotr configuration command anywhere
        if raw_content.lower() == "aotr":
            if message.guild and message.author.guild_permissions.manage_guild:
                # Dynamically fetch what channels are currently allowed to display in the embed
                allowed_channels = await self.get_allowed_channels(message.guild.id)
                
                if allowed_channels:
                    mentions = ", ".join(f"<#{c_id}>" for c_id in allowed_channels)
                    status_text = f"**Currently Allowed Channels:**\n{mentions}"
                else:
                    status_text = "**Currently Allowed Channels:**\n✅ All channels are allowed (No restrictions)"

                embed = discord.Embed(
                    title="⚙️ S.I.L.K. Prefix Configuration",
                    description=(
                        "You can restrict `?` prefix commands to specific channels.\n\n"
                        "Click the button below to open the setup modal. "
                        "Enter the allowed **Channel IDs** separated by commas (no spaces needed).\n"
                        "*Leave the box completely empty to allow commands everywhere.*\n\n"
                        f"{status_text}"
                    ),
                    color=0x3498DB
                )
                view = ConfigView(self.bot)
                await message.channel.send(embed=embed, view=view)
            return

        # 4. Enforce Channel Restrictions
        if message.guild:
            allowed_channels = await self.get_allowed_channels(message.guild.id)
            # If the allowed list isn't empty and the current channel ID isn't in it, ignore the message
            if allowed_channels and str(message.channel.id) not in allowed_channels:
                return

        # 5. Dynamic Cog Routing Matrix
        trade_match = self.trade_split_pattern.split(raw_content)

        if len(trade_match) > 1:
            # Handle Trade Compare Syntax
            trade_cog = self.bot.get_cog("TradeCompare")
            if trade_cog:
                giving_items = trade_match[0].strip()
                getting_items = trade_match[1].strip()
                
                # Check for empty split parameters (e.g. "? item for ")
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
            # Handle Single Item Value Lookup
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
