import discord
from .. import database

class CooldownModal(discord.ui.Modal):
    def __init__(self, action: str, guild, config, title="Set Cooldown"):
        super().__init__(title=title)
        self.action = action
        self.guild = guild
        self.config = config

        self.cd_input = discord.ui.TextInput(
            label="Cooldown in Seconds",
            style=discord.TextStyle.short,
            placeholder="e.g. 60",
            required=True
        )
        self.add_item(self.cd_input)

    async def on_submit(self, interaction: discord.Interaction):
        try:
            cd = int(self.cd_input.value)
            if cd < 0:
                raise ValueError
        except ValueError:
            await interaction.response.send_message("❌ Please enter a valid non-negative integer.", ephemeral=True)
            return

        if self.action == "text":
            self.config["text_cooldown"] = cd
            await database.update_guild_config(self.guild.id, {"text_cooldown": cd})
            msg = f"✅ Text Cooldown set to **{cd} seconds**."
        elif self.action == "reaction":
            self.config["reaction_cooldown"] = cd
            await database.update_guild_config(self.guild.id, {"reaction_cooldown": cd})
            msg = f"✅ Reaction Cooldown set to **{cd} seconds**."
        elif self.action == "vc":
            self.config["vc_cooldown"] = cd
            await database.update_guild_config(self.guild.id, {"vc_cooldown": cd})
            msg = f"✅ VC Cooldown set to **{cd} seconds**."

        await interaction.response.send_message(msg, ephemeral=True)

class CooldownSettingsView(discord.ui.View):
    def __init__(self, bot, guild, config, parent_view):
        super().__init__(timeout=600)
        self.bot = bot
        self.guild = guild
        self.config = config
        self.parent_view = parent_view

    @discord.ui.button(label="Set Text Cooldown", style=discord.ButtonStyle.primary, row=0)
    async def btn_text_cd(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(CooldownModal("text", self.guild, self.config, title="Text Cooldown"))

    @discord.ui.button(label="Set Reaction Cooldown", style=discord.ButtonStyle.primary, row=0)
    async def btn_reaction_cd(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(CooldownModal("reaction", self.guild, self.config, title="Reaction Cooldown"))

    @discord.ui.button(label="Set VC Cooldown", style=discord.ButtonStyle.primary, row=0)
    async def btn_vc_cd(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(CooldownModal("vc", self.guild, self.config, title="VC Cooldown"))

    @discord.ui.button(label="Back to Main Menu", style=discord.ButtonStyle.secondary, row=1)
    async def btn_back(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.edit_message(content="🔓 Welcome to the S.I.L.K. Level System Dashboard.", view=self.parent_view)
