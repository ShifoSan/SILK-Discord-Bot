import discord
from discord.ext import commands, tasks
import random

class Presence(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

        # Reuse the centralized MongoDB client managed by SilkBot.
        self.db_client = bot.mongo_client
        if self.db_client:
            self.bot_statuses = self.db_client.silk_bot.bot_statuses
        else:
            self.bot_statuses = None
            print("Warning: MONGO_URI not found. Presence module will fail.")

    @tasks.loop(seconds=20)
    async def status_loop(self):
        if self.bot_statuses is None:
            return

        try:
            # Fetch active statuses from the database
            active_statuses = []
            async for status in self.bot_statuses.find({"active": True}):
                active_statuses.append(status)

            if not active_statuses:
                return

            # Randomly pick one
            selected_status = random.choice(active_statuses)

            # Map string type to discord.ActivityType
            type_str = selected_status.get("type", "playing").lower()
            activity_type = getattr(discord.ActivityType, type_str, discord.ActivityType.playing)

            name_template = selected_status.get("text", "")

            # Handle dynamic formatting (Member Count)
            if "{member_count}" in name_template:
                total_members = sum(g.member_count for g in self.bot.guilds)
                name = name_template.format(member_count=total_members)
            else:
                name = name_template

            # Apply the presence
            await self.bot.change_presence(activity=discord.Activity(type=activity_type, name=name))

        except Exception as e:
            print(f"Error in status loop: {e}")

    @status_loop.before_loop
    async def before_status_loop(self):
        # Crucial: Wait for bot to be ready before starting loop logic
        await self.bot.wait_until_ready()

    @commands.Cog.listener()
    async def on_ready(self):
        # Start the loop if it's not already running
        if not self.status_loop.is_running():
            self.status_loop.start()

async def setup(bot):
    await bot.add_cog(Presence(bot))
