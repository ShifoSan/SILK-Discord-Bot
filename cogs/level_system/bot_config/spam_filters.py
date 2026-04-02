import discord
from .. import database

class SpamFiltersView(discord.ui.View):
    def __init__(self, bot, guild, config, parent_view):
        super().__init__(timeout=300)
        self.bot = bot
        self.guild = guild
        self.config = config
        self.parent_view = parent_view

    @discord.ui.select(cls=discord.ui.ChannelSelect, channel_types=[discord.ChannelType.text], placeholder="Select Channel to Blacklist...", row=0)
    async def select_channel(self, interaction: discord.Interaction, select: discord.ui.ChannelSelect):
        channel = select.values[0]
        blacklist = self.config.get("spam_channels_blacklist", [])

        if channel.id in blacklist:
            blacklist.remove(channel.id)
            msg = f"✅ Removed {channel.mention} from blacklist."
        else:
            blacklist.append(channel.id)
            msg = f"✅ Added {channel.mention} to blacklist."

        self.config["spam_channels_blacklist"] = blacklist
        await database.update_guild_config(self.guild.id, {"spam_channels_blacklist": blacklist})
        await interaction.response.send_message(msg, ephemeral=True)

    @discord.ui.select(placeholder="Minimum Message Length...", options=[
        discord.SelectOption(label="1 character", value="1"),
        discord.SelectOption(label="5 characters", value="5"),
        discord.SelectOption(label="10 characters", value="10"),
        discord.SelectOption(label="20 characters", value="20"),
    ], row=1)
    async def select_length(self, interaction: discord.Interaction, select: discord.ui.Select):
        length = int(select.values[0])
        self.config["spam_min_length"] = length
        await database.update_guild_config(self.guild.id, {"spam_min_length": length})
        await interaction.response.send_message(f"✅ Minimum message length for XP set to **{length} characters**.", ephemeral=True)

    @discord.ui.button(label="Back to Main Menu", style=discord.ButtonStyle.secondary, row=2)
    async def btn_back(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.edit_message(content="🔓 Welcome to the S.I.L.K. Level System Dashboard.", view=self.parent_view)
