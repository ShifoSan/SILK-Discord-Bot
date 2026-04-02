import discord
from .. import database

class RoleRewardsView(discord.ui.View):
    def __init__(self, bot, guild, config, parent_view):
        super().__init__(timeout=300)
        self.bot = bot
        self.guild = guild
        self.config = config
        self.parent_view = parent_view
        self.selected_level = None

    @discord.ui.select(placeholder="Select Level to map...", options=[
        discord.SelectOption(label=f"Level {i}", value=str(i)) for i in [5, 10, 15, 20, 25, 30, 40, 50, 75, 100]
    ], row=0)
    async def select_level(self, interaction: discord.Interaction, select: discord.ui.Select):
        self.selected_level = select.values[0]
        await interaction.response.send_message(f"Selected Level {self.selected_level}. Now select a role below.", ephemeral=True)

    @discord.ui.select(cls=discord.ui.RoleSelect, placeholder="Select Role to award...", row=1)
    async def select_role(self, interaction: discord.Interaction, select: discord.ui.RoleSelect):
        if not self.selected_level:
            await interaction.response.send_message("Please select a level first from the dropdown above.", ephemeral=True)
            return

        role = select.values[0]

        # Prevent selecting roles higher than the bot
        bot_member = self.guild.get_member(self.bot.user.id)
        if role.position >= bot_member.top_role.position:
            await interaction.response.send_message("❌ I cannot assign that role because it is higher or equal to my own top role.", ephemeral=True)
            return

        self.config["role_rewards"][self.selected_level] = role.id
        await database.update_guild_config(self.guild.id, {"role_rewards": self.config["role_rewards"]})

        await interaction.response.send_message(f"✅ Mapped Level {self.selected_level} to {role.mention}.", ephemeral=True)

    @discord.ui.button(label="Back to Main Menu", style=discord.ButtonStyle.secondary, row=2)
    async def btn_back(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.edit_message(content="🔓 Welcome to the S.I.L.K. Level System Dashboard.", view=self.parent_view)
