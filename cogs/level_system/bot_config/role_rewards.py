import discord
from .. import database

class MapRoleModal(discord.ui.Modal, title="Map Role Reward"):
    level_input = discord.ui.TextInput(
        label="Enter Level",
        style=discord.TextStyle.short,
        placeholder="e.g. 15",
        required=True
    )

    def __init__(self, bot, guild, config):
        super().__init__()
        self.bot = bot
        self.guild = guild
        self.config = config

    async def on_submit(self, interaction: discord.Interaction):
        try:
            level = int(self.level_input.value)
            if level <= 0:
                raise ValueError
        except ValueError:
            await interaction.response.send_message("❌ Please enter a valid positive integer for the level.", ephemeral=True)
            return

        view = RoleSelectView(self.bot, self.guild, self.config, level)
        await interaction.response.send_message(f"Selected Level {level}. Please select the role to map to it.", view=view, ephemeral=True)

class RoleSelectView(discord.ui.View):
    def __init__(self, bot, guild, config, level):
        super().__init__(timeout=600)
        self.bot = bot
        self.guild = guild
        self.config = config
        self.level = level

    @discord.ui.select(cls=discord.ui.RoleSelect, placeholder="Select Role to award...", row=0)
    async def select_role(self, interaction: discord.Interaction, select: discord.ui.RoleSelect):
        await interaction.response.defer(ephemeral=True)
        role = select.values[0]

        bot_member = self.guild.get_member(self.bot.user.id)
        if role.position >= bot_member.top_role.position:
            await interaction.followup.send("❌ I cannot assign that role because it is higher or equal to my own top role.", ephemeral=True)
            return

        self.config["role_rewards"][str(self.level)] = role.id
        await database.update_guild_config(self.guild.id, {"role_rewards": self.config["role_rewards"]})

        await interaction.followup.send(f"✅ Mapped Level {self.level} to {role.mention}.", ephemeral=True)

class RemoveRoleModal(discord.ui.Modal, title="Remove Role Reward"):
    level_input = discord.ui.TextInput(
        label="Enter Level to Remove",
        style=discord.TextStyle.short,
        placeholder="e.g. 15",
        required=True
    )

    def __init__(self, guild, config):
        super().__init__()
        self.guild = guild
        self.config = config

    async def on_submit(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        level_str = self.level_input.value.strip()

        if level_str in self.config.get("role_rewards", {}):
            del self.config["role_rewards"][level_str]
            await database.update_guild_config(self.guild.id, {"role_rewards": self.config["role_rewards"]})
            await interaction.followup.send(f"✅ Removed role reward for Level {level_str}.", ephemeral=True)
        else:
            await interaction.followup.send(f"❌ No role reward found for Level {level_str}.", ephemeral=True)


class RoleRewardsView(discord.ui.View):
    def __init__(self, bot, guild, config, parent_view):
        super().__init__(timeout=600)
        self.bot = bot
        self.guild = guild
        self.config = config
        self.parent_view = parent_view

    @discord.ui.button(label="Add Role Reward", style=discord.ButtonStyle.success, row=0)
    async def btn_add_reward(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(MapRoleModal(self.bot, self.guild, self.config))

    @discord.ui.button(label="Remove Role Reward", style=discord.ButtonStyle.danger, row=0)
    async def btn_remove_reward(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(RemoveRoleModal(self.guild, self.config))

    @discord.ui.button(label="Back to Main Menu", style=discord.ButtonStyle.secondary, row=1)
    async def btn_back(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.edit_message(content="🔓 Welcome to the S.I.L.K. Level System Dashboard.", view=self.parent_view)
