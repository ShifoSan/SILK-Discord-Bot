import discord
from discord.ext import commands, tasks
import itertools

class Presence(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        # Store statuses as a list of tuples: (ActivityType, String Template)
        self.status_templates = [
            (discord.ActivityType.watching, "for targets in #general"),
            (discord.ActivityType.playing, "with knives 🔪"),
            (discord.ActivityType.listening, "to your secrets"),
            (discord.ActivityType.watching, "over {member_count} users"), # Dynamic
            (discord.ActivityType.playing, "System: Optimal"),
            (discord.ActivityType.playing, "Human Simulator 2026"),
            (discord.ActivityType.listening, "/help for orders"),
        ]
        self.status_cycle = itertools.cycle(self.status_templates)

    @tasks.loop(seconds=20)
    async def status_loop(self):
        try:
            # Get the next status template
            activity_type, name_template = next(self.status_cycle)

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
