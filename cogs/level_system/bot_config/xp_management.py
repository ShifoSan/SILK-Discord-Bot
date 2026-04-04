import discord
from .. import database

class XPModal(discord.ui.Modal):
    def __init__(self, action: str, guild, user, title="Manage XP"):
        super().__init__(title=title)
        self.action = action
        self.guild = guild
        self.user = user

        self.input_val = discord.ui.TextInput(
            label="Enter Amount",
            style=discord.TextStyle.short,
            placeholder="e.g. 500",
            required=True
        )
        self.add_item(self.input_val)

    async def on_submit(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        try:
            val = int(self.input_val.value)
            if val < 0:
                raise ValueError
        except ValueError:
            await interaction.followup.send("❌ Please enter a valid positive integer.", ephemeral=True)
            return

        user_data = await database.get_user_data(self.guild.id, self.user.id)

        if self.action == "add_xp":
            new_xp = user_data.get("xp", 0) + val
            await database.save_user_data(self.guild.id, self.user.id, {"xp": new_xp})
            msg = f"✅ Added {val} XP to {self.user.mention}."
        elif self.action == "rem_xp":
            new_xp = max(0, user_data.get("xp", 0) - val)
            await database.save_user_data(self.guild.id, self.user.id, {"xp": new_xp})
            msg = f"✅ Removed {val} XP from {self.user.mention}."
        elif self.action == "set_xp":
            await database.save_user_data(self.guild.id, self.user.id, {"xp": val})
            msg = f"✅ Set {self.user.mention}'s total XP to {val}."
        elif self.action == "set_level":
            xp_required = 0
            for l in range(val):
                xp_required += 5 * (l**2) + 50 * l + 100
            await database.save_user_data(self.guild.id, self.user.id, {"xp": xp_required})
            msg = f"✅ Set {self.user.mention} to Level {val} (XP: {xp_required})."

        await interaction.followup.send(msg, ephemeral=True)


class XPManagementView(discord.ui.View):
    def __init__(self, bot, guild, config, parent_view):
        super().__init__(timeout=600)
        self.bot = bot
        self.guild = guild
        self.config = config
        self.parent_view = parent_view
        self.selected_user = None

    @discord.ui.select(cls=discord.ui.UserSelect, placeholder="Select User...", row=0)
    async def select_user(self, interaction: discord.Interaction, select: discord.ui.UserSelect):
        self.selected_user = select.values[0]
        await interaction.response.send_message(f"Selected {self.selected_user.mention}. Use buttons below to modify their data.", ephemeral=True)

    @discord.ui.button(label="Add XP", style=discord.ButtonStyle.success, row=1)
    async def btn_add_xp(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not self.selected_user:
            await interaction.response.send_message("Please select a user first.", ephemeral=True)
            return
        await interaction.response.send_modal(XPModal("add_xp", self.guild, self.selected_user, title="Add XP"))

    @discord.ui.button(label="Remove XP", style=discord.ButtonStyle.danger, row=1)
    async def btn_rem_xp(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not self.selected_user:
            await interaction.response.send_message("Please select a user first.", ephemeral=True)
            return
        await interaction.response.send_modal(XPModal("rem_xp", self.guild, self.selected_user, title="Remove XP"))

    @discord.ui.button(label="Set Total XP", style=discord.ButtonStyle.primary, row=1)
    async def btn_set_xp(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not self.selected_user:
            await interaction.response.send_message("Please select a user first.", ephemeral=True)
            return
        await interaction.response.send_modal(XPModal("set_xp", self.guild, self.selected_user, title="Set Total XP"))

    @discord.ui.button(label="Set Custom Level", style=discord.ButtonStyle.primary, row=1)
    async def btn_set_level(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not self.selected_user:
            await interaction.response.send_message("Please select a user first.", ephemeral=True)
            return
        await interaction.response.send_modal(XPModal("set_level", self.guild, self.selected_user, title="Set Custom Level"))

    @discord.ui.button(label="Reset User Data", style=discord.ButtonStyle.danger, row=2)
    async def btn_reset(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not self.selected_user:
            await interaction.response.send_message("Please select a user first.", ephemeral=True)
            return

        # FIXED: Defer immediately to stop Discord from timing out during the DB call
        await interaction.response.defer(ephemeral=True)
        await database.save_user_data(self.guild.id, self.selected_user.id, {"xp": 0, "level": 0, "vc_xp": 0})
        await interaction.followup.send(f"✅ Reset data for {self.selected_user.mention}.", ephemeral=True)

    @discord.ui.button(label="Back to Main Menu", style=discord.ButtonStyle.secondary, row=2)
    async def btn_back(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.edit_message(content="🔓 Welcome to the S.I.L.K. Level System Dashboard.", view=self.parent_view)

