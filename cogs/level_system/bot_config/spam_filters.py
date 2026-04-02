import discord
from .. import database

class SpamLengthModal(discord.ui.Modal, title="Spam Filter Length"):
    length_input = discord.ui.TextInput(
        label="Minimum Message Length",
        style=discord.TextStyle.short,
        placeholder="e.g. 5",
        required=True
    )

    def __init__(self, guild, config):
        super().__init__()
        self.guild = guild
        self.config = config

    async def on_submit(self, interaction: discord.Interaction):
        try:
            length = int(self.length_input.value)
            if length < 0:
                raise ValueError
        except ValueError:
            await interaction.response.send_message("❌ Please enter a valid non-negative integer.", ephemeral=True)
            return

        self.config["spam_min_length"] = length
        await database.update_guild_config(self.guild.id, {"spam_min_length": length})
        await interaction.response.send_message(f"✅ Minimum message length for XP set to **{length} characters**.", ephemeral=True)

class SpamFiltersView(discord.ui.View):
    def __init__(self, bot, guild, config, parent_view):
        super().__init__(timeout=600)
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

    @discord.ui.button(label="Set Min Message Length", style=discord.ButtonStyle.primary, row=1)
    async def btn_set_length(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(SpamLengthModal(self.guild, self.config))

    @discord.ui.button(label="Back to Main Menu", style=discord.ButtonStyle.secondary, row=2)
    async def btn_back(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.edit_message(content="🔓 Welcome to the S.I.L.K. Level System Dashboard.", view=self.parent_view)
