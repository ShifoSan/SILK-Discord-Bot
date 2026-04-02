import discord
from discord import app_commands
from discord.ext import commands
import os
import asyncio
from . import database
from . import image_gen
from .bot_config.main_menu import ConfigPasswordModal

class LeaderboardPaginationView(discord.ui.View):
    def __init__(self, guild_id: int, sort_by_vc: bool):
        super().__init__(timeout=120)
        self.guild_id = guild_id
        self.sort_by_vc = sort_by_vc
        self.current_page = 0
        self.limit = 10

    async def generate_embed(self, guild: discord.Guild) -> discord.Embed:
        users = await database.get_top_users(self.guild_id, self.limit, self.current_page * self.limit, self.sort_by_vc)

        embed = discord.Embed(
            title=f"{guild.name} Leaderboard",
            description=f"Sorting by **{'Voice XP' if self.sort_by_vc else 'Total XP'}**",
            color=discord.Color.blue()
        )
        if guild.icon:
            embed.set_thumbnail(url=guild.icon.url)

        if not users:
            embed.add_field(name="No Data", value="Nobody is on the leaderboard yet!")
            return embed

        desc = ""
        for i, u in enumerate(users):
            rank = (self.current_page * self.limit) + i + 1
            member = guild.get_member(u["user_id"])
            name = member.display_name if member else f"Unknown User ({u['user_id']})"
            xp = u.get("vc_xp", 0) if self.sort_by_vc else u.get("xp", 0)
            level = u.get("level", 0)
            desc += f"**#{rank}** | {name} - Lvl {level} | {xp} XP\n"

        embed.description += "\n\n" + desc
        embed.set_footer(text=f"Page {self.current_page + 1}")
        return embed

    @discord.ui.button(emoji="⬅️", style=discord.ButtonStyle.secondary)
    async def prev_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        if self.current_page > 0:
            self.current_page -= 1
            embed = await self.generate_embed(interaction.guild)
            await interaction.response.edit_message(embed=embed, view=self)
        else:
            await interaction.response.defer()

    @discord.ui.button(emoji="➡️", style=discord.ButtonStyle.secondary)
    async def next_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        users_count = await database.users_collection.count_documents({"guild_id": self.guild_id, "in_server": True})
        if (self.current_page + 1) * self.limit < users_count:
            self.current_page += 1
            embed = await self.generate_embed(interaction.guild)
            await interaction.response.edit_message(embed=embed, view=self)
        else:
            await interaction.response.defer()

class LevelSystemCommands(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="rank", description="Displays your rank or another user's rank.")
    async def rank(self, interaction: discord.Interaction, user: discord.Member = None):
        await interaction.response.defer(thinking=True)

        target = user or interaction.user
        if target.bot:
            await interaction.followup.send("Bots do not have ranks.")
            return

        user_data = await database.get_user_data(interaction.guild_id, target.id)
        rank_pos = await database.get_user_rank(interaction.guild_id, target.id, sort_by_vc=False)

        level = user_data["level"]
        current_xp = user_data["xp"]
        next_level_xp = 5 * (level**2) + 50 * level + 100

        # Safely download the avatar bytes asynchronously to prevent blocking/lag
        avatar_asset = target.avatar if target.avatar else target.default_avatar
        avatar_bytes = await avatar_asset.read()

        # Run image generation in thread to avoid blocking using asyncio
        image_bytes = await asyncio.to_thread(
            image_gen.generate_rank_card,
            target.display_name,
            avatar_bytes,
            level,
            current_xp,
            next_level_xp,
            rank_pos
        )

        file = discord.File(fp=image_bytes, filename="rank.png")
        await interaction.followup.send(file=file)

    @app_commands.command(name="leaderboard", description="Displays the server leaderboard.")
    async def leaderboard(self, interaction: discord.Interaction, page: int = 1, voice_lb: bool = False):
        await interaction.response.defer(thinking=True)
        
        # Convert user's 1-based page input to our 0-based index
        page_index = max(0, page - 1)
        
        view = LeaderboardPaginationView(interaction.guild_id, voice_lb)
        view.current_page = page_index
        
        embed = await view.generate_embed(interaction.guild)
        await interaction.followup.send(embed=embed, view=view)

async def setup(bot):
    await bot.add_cog(LevelSystemCommands(bot))
    
