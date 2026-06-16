import discord
from discord.ext import commands

class DashboardButton(discord.ui.Button):
    async def callback(self, interaction: discord.Interaction):
        view: "StarboardConfigView" = self.view
        
        # Security: Block non-admins from pressing dashboard buttons
        if not interaction.user.guild_permissions.administrator:
            return await interaction.response.send_message("❌ This setup panel belongs to administrators.", ephemeral=True)
            
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
            custom_id="select_channel",
            row=2
        )

    async def callback(self, interaction: discord.Interaction):
        view: "StarboardConfigView" = self.view
        
        if not interaction.user.guild_permissions.administrator:
            return await interaction.response.send_message("❌ This setup panel belongs to administrators.", ephemeral=True)
            
        # Extract the selected channel ID natively
        view.channel_id = self.values[0].id
        
        await view.save_to_db()
        view.update_components()
        await interaction.response.edit_message(view=view)

class StarboardConfigView(discord.ui.View):
    def __init__(self, cog, guild_id: int, config: dict):
        super().__init__(timeout=300)
        self.cog = cog
        self.guild_id = guild_id
        
        # Load local state parameters from the MongoDB config sub-document
        sb_data = config.get("starboard", {})
        self.is_enabled = sb_data.get("is_enabled", False)
        self.channel_id = sb_data.get("channel_id", None)
        self.trigger_emoji = sb_data.get("trigger_emoji", "any")
        
        self.update_components()

    def update_components(self):
        """Re-builds and updates the internal dashboard component tree layout."""
        self.clear_items()
        
        # 1. Root Presentation Container Card (Components V2)
        accent_color = discord.Color.from_rgb(255, 215, 0) if self.is_enabled else discord.Color.from_rgb(100, 100, 100)
        container = discord.ui.Container(title="⭐ S.I.L.K. Starboard System", color=accent_color)
        
        # 2. Content Status Matrix Display
        status_str = "🟢 Enabled" if self.is_enabled else "🔴 Disabled"
        channel_str = f"<#{self.channel_id}>" if self.channel_id else "❌ Not Set (Bot will ignore reactions)"
        rule_str = "⭐ Stars Only" if self.trigger_emoji == "⭐" else "🌍 Any Emoji (4+ Count)"
        
        dashboard_text = (
            f"### Live Configuration Status\n"
            f"* **System Power:** {status_str}\n"
            f"* **Target Output Channel:** {channel_str}\n"
            f"* **Reaction Trigger Filter:** {rule_str}\n\n"
            f"> Use the interface buttons below to update your starboard environment parameters instantly."
        )
        
        container.add_item(discord.ui.TextDisplay(body=dashboard_text))
        self.add_item(container)
        
        # 3. Interactive Options Action Rows
        toggle_label = "Disable System" if self.is_enabled else "Enable System"
        toggle_style = discord.ButtonStyle.danger if self.is_enabled else discord.ButtonStyle.success
        self.add_item(DashboardButton(label=toggle_label, style=toggle_style, custom_id="toggle_power", row=1))
        
        emoji_label = "Set to 'Any Emoji'" if self.trigger_emoji == "⭐" else "Set to '⭐ Only'"
        self.add_item(DashboardButton(label=emoji_label, style=discord.ButtonStyle.primary, custom_id="toggle_emoji", row=1))
        
        self.add_item(DashboardChannelSelect())

    async def save_to_db(self):
        """Pushes the current localized layout view state back out to MongoDB Atlas."""
        payload = {
            "starboard.is_enabled": self.is_enabled,
            "starboard.channel_id": self.channel_id,
            "starboard.trigger_emoji": self.trigger_emoji
        }
        await self.cog.db.chat_configs.update_one(
            {"guild_id": self.guild_id},
            {"$set": payload},
            upsert=True
        )

class Starboard(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        # Access your global centralized production collection index instance
        self.db = bot.db 

    @commands.command(name="sb")
    async def starboard_dashboard(self, ctx: commands.Context):
        # Mandatory Requirement: Check Admin Permissions manually
        if not ctx.author.guild_permissions.administrator:
            return  # Ignore cleanly with zero feedback trace vectors

        # Fetch or initialize server configuration records
        config = await self.db.chat_configs.find_one({"guild_id": ctx.guild.id})
        if not config:
            config = {"guild_id": ctx.guild.id, "starboard": {"is_enabled": False, "channel_id": None, "trigger_emoji": "any", "posted_messages": []}}
            await self.db.chat_configs.insert_one(config)

        view = StarboardConfigView(self, ctx.guild.id, config)
        await ctx.send(view=view)

    @commands.Cog.listener()
    async def on_raw_reaction_add(self, payload: discord.RawReactionActionEvent):
        """Global listener that bypasses cache to detect starboard thresholds."""
        
        # 0. Ignore bot reactions instantly to save computing cycles
        if payload.member and payload.member.bot:
            return

        # 1. Fetch Configuration & Quick Kill Switch
        config = await self.db.chat_configs.find_one({"guild_id": payload.guild_id})
        if not config:
            return

        sb_data = config.get("starboard", {})
        
        # If disabled or no channel is set, silently ignore the event
        if not sb_data.get("is_enabled", False):
            return
            
        target_channel_id = sb_data.get("channel_id")
        if not target_channel_id:
            return

        # 2. Check the Emoji Filter Ruleset
        trigger_rule = sb_data.get("trigger_emoji", "any")
        if trigger_rule == "⭐" and str(payload.emoji) != "⭐":
            return

        # 3. Fetch Message & Verify Reaction Count
        try:
            channel = await self.bot.fetch_channel(payload.channel_id)
            message = await channel.fetch_message(payload.message_id)
        except discord.NotFound:
            return  # The message was deleted before we could fetch it

        # Verify the specific reaction count crosses the 4+ threshold
        hit_threshold = False
        for reaction in message.reactions:
            if trigger_rule == "any" or str(reaction.emoji) == "⭐":
                if reaction.count >= 4:
                    hit_threshold = True
                    break
        
        if not hit_threshold:
            return

        # 4. Anti-Duplication Race Condition Lock (MongoDB Atomic Update)
        update_result = await self.db.chat_configs.update_one(
            {
                "guild_id": payload.guild_id,
                "starboard.posted_messages": {"$ne": message.id}
            },
            {
                "$push": {
                    "starboard.posted_messages": {
                        "$each": [message.id],
                        "$slice": -150  
                    }
                }
            }
        )

        # If modified_count is 0, the message ID was already in the array. Abort.
        if update_result.modified_count == 0:
            return

        # 5. Build and Dispatch the Component V2 Layout
        target_channel = self.bot.get_channel(target_channel_id) or await self.bot.fetch_channel(target_channel_id)
        
        class StarboardPostView(discord.ui.View):
            def __init__(self):
                super().__init__(timeout=None)
                
                # Fetch the user's current avatar (with a safe fallback if they don't have one)
                user_avatar = message.author.display_avatar.url if message.author.display_avatar else None

                # The primary backing card (Including the avatar header)
                container = discord.ui.Container(
                    title=f"⭐ Highlight | {message.author.display_name}", 
                    color=discord.Color.from_rgb(255, 215, 0),
                    icon_url=user_avatar
                )
                
                # Protect against the 4000 character Discord API crash limit
                safe_content = message.content
                if len(safe_content) > 3900:
                    safe_content = safe_content[:3900] + "... [Read More]"
                
                body_text = safe_content if safe_content else "*[Media Highlight]*"
                
                # Check for attachments to inject gracefully
                if message.attachments:
                    primary_image = message.attachments[0].url
                    body_text += f"\n\n![Attachment]({primary_image})"
                
                container.add_item(discord.ui.TextDisplay(body=body_text))
                self.add_item(container)
                
                # Action Row jump button
                self.add_item(discord.ui.Button(
                    style=discord.ButtonStyle.link, 
                    url=message.jump_url, 
                    label="Jump to Original Message"
                ))

        await target_channel.send(view=StarboardPostView())


async def setup(bot):
    await bot.add_cog(Starboard(bot))
