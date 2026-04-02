import discord
from .. import database

class XPManagementView(discord.ui.View):
    def __init__(self, bot, guild, config, parent_view):
        super().__init__(timeout=300)
        self.bot = bot
        self.guild = guild
        self.config = config
        self.parent_view = parent_view
        self.selected_user = None

    @discord.ui.select(cls=discord.ui.UserSelect, placeholder="Select User...", row=0)
    async def select_user(self, interaction: discord.Interaction, select: discord.ui.UserSelect):
        self.selected_user = select.values[0]
        await interaction.response.send_message(f"Selected {self.selected_user.mention}. Use buttons below to modify their data.", ephemeral=True)

    @discord.ui.select(placeholder="Action: Add / Remove XP / Set Level...", options=[
        discord.SelectOption(label="Add 100 XP", value="add_100"),
        discord.SelectOption(label="Add 500 XP", value="add_500"),
        discord.SelectOption(label="Remove 100 XP", value="rem_100"),
        discord.SelectOption(label="Remove 500 XP", value="rem_500"),
        discord.SelectOption(label="Set to Level 10", value="set_10"),
        discord.SelectOption(label="Set to Level 25", value="set_25"),
    ], row=1)
    async def select_action(self, interaction: discord.Interaction, select: discord.ui.Select):
        if not self.selected_user:
            await interaction.response.send_message("Please select a user first.", ephemeral=True)
            return

        action = select.values[0]
        user_data = await database.get_user_data(self.guild.id, self.selected_user.id)

        if action.startswith("add_"):
            amount = int(action.split("_")[1])
            new_xp = user_data.get("xp", 0) + amount
            await database.save_user_data(self.guild.id, self.selected_user.id, {"xp": new_xp})
            await interaction.response.send_message(f"✅ Added {amount} XP to {self.selected_user.mention}.", ephemeral=True)
        elif action.startswith("rem_"):
            amount = int(action.split("_")[1])
            new_xp = max(0, user_data.get("xp", 0) - amount)
            await database.save_user_data(self.guild.id, self.selected_user.id, {"xp": new_xp})
            await interaction.response.send_message(f"✅ Removed {amount} XP from {self.selected_user.mention}.", ephemeral=True)
        elif action.startswith("set_"):
            level = int(action.split("_")[1])
            xp_required = 5 * ((level - 1)**2) + 50 * (level - 1) + 100 if level > 1 else 0
            await database.save_user_data(self.guild.id, self.selected_user.id, {"level": level, "xp": xp_required})
            await interaction.response.send_message(f"✅ Set {self.selected_user.mention} to Level {level}.", ephemeral=True)

    @discord.ui.button(label="Reset User Data", style=discord.ButtonStyle.danger, row=2)
    async def btn_reset(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not self.selected_user:
            await interaction.response.send_message("Please select a user first.", ephemeral=True)
            return

        await database.save_user_data(self.guild.id, self.selected_user.id, {"xp": 0, "level": 0, "vc_xp": 0})
        await interaction.response.send_message(f"✅ Reset data for {self.selected_user.mention}.", ephemeral=True)

    @discord.ui.button(label="Back to Main Menu", style=discord.ButtonStyle.secondary, row=2)
    async def btn_back(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.edit_message(content="🔓 Welcome to the S.I.L.K. Level System Dashboard.", view=self.parent_view)
