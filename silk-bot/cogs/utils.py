import discord
from discord import app_commands
from discord.ext import commands
import datetime
import random
import asyncio
import qrcode
import io
import re

class Utils(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.start_time = datetime.datetime.now()

    # --- Status & Info Commands ---

    @app_commands.command(name="ping", description="Check the bot's latency")
    async def ping(self, interaction: discord.Interaction):
        latency = round(self.bot.latency * 1000)
        await interaction.response.send_message(f"Pong! 🏓 ({latency} ms)")

    @app_commands.command(name="uptime", description="Check how long the bot has been online")
    async def uptime(self, interaction: discord.Interaction):
        now = datetime.datetime.now()
        delta = now - self.start_time

        days = delta.days
        hours, remainder = divmod(delta.seconds, 3600)
        minutes, seconds = divmod(remainder, 60)

        parts = []
        if days > 0: parts.append(f"{days} days")
        if hours > 0: parts.append(f"{hours} hours")
        if minutes > 0: parts.append(f"{minutes} minutes")
        if seconds > 0: parts.append(f"{seconds} seconds")

        time_str = ", ".join(parts) if parts else "0 seconds"
        await interaction.response.send_message(f"Online for: {time_str}")

    @app_commands.command(name="serverinfo", description="Display detailed server information")
    async def serverinfo(self, interaction: discord.Interaction):
        guild = interaction.guild
        embed = discord.Embed(title=f"Server Info: {guild.name}", color=discord.Color.teal())

        if guild.icon:
            embed.set_thumbnail(url=guild.icon.url)

        embed.add_field(name="Server ID", value=guild.id, inline=True)
        embed.add_field(name="Owner", value=guild.owner.mention, inline=True)
        embed.add_field(name="Member Count", value=guild.member_count, inline=True)
        embed.add_field(name="Created On", value=guild.created_at.strftime("%Y-%m-%d %H:%M:%S"), inline=False)

        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="userinfo", description="Display user information")
    @app_commands.describe(member="The member to get info for (defaults to you)")
    async def userinfo(self, interaction: discord.Interaction, member: discord.Member = None):
        member = member or interaction.user

        embed = discord.Embed(title=f"User Info: {member.display_name}", color=discord.Color.teal())
        embed.set_thumbnail(url=member.display_avatar.url)

        embed.add_field(name="Joined Server", value=member.joined_at.strftime("%Y-%m-%d %H:%M:%S") if member.joined_at else "Unknown", inline=True)
        embed.add_field(name="Account Created", value=member.created_at.strftime("%Y-%m-%d %H:%M:%S"), inline=True)
        embed.add_field(name="Top Role", value=member.top_role.mention, inline=False)

        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="avatar", description="Get a user's avatar")
    @app_commands.describe(member="The member to get avatar for (defaults to you)")
    async def avatar(self, interaction: discord.Interaction, member: discord.Member = None):
        member = member or interaction.user

        embed = discord.Embed(title=f"{member.display_name}'s Avatar", color=discord.Color.teal())
        embed.set_image(url=member.display_avatar.url)

        await interaction.response.send_message(embed=embed)

    # --- Fun Tools (RNG) ---

    @app_commands.command(name="roll", description="Roll a 6-sided die")
    async def roll(self, interaction: discord.Interaction):
        result = random.randint(1, 6)
        await interaction.response.send_message(f"🎲 You rolled a {result}!")

    @app_commands.command(name="flip", description="Flip a coin")
    async def flip(self, interaction: discord.Interaction):
        result = random.choice(["Heads", "Tails"])
        await interaction.response.send_message(f"🪙 It's {result}!")

    @app_commands.command(name="choose", description="Randomly choose between two options")
    async def choose(self, interaction: discord.Interaction, choice1: str, choice2: str):
        result = random.choice([choice1, choice2])
        await interaction.response.send_message(f"I choose: **{result}**")

    # --- Utility Tools ---

    @app_commands.command(name="calc", description="Solve a basic math expression")
    @app_commands.describe(expression="The math expression to solve (e.g., 5 + 5)")
    async def calc(self, interaction: discord.Interaction, expression: str):
        # Allow numbers, operators, parens, decimal points, and spaces
        allowed_pattern = r"^[0-9+\-*/().\s]+$"

        if not re.match(allowed_pattern, expression):
            await interaction.response.send_message("❌ Invalid characters in expression. Only numbers and basic operators are allowed.", ephemeral=True)
            return

        try:
            # Safe to eval because we checked against the allowed pattern
            # Using a restricted scope just in case
            result = eval(expression, {"__builtins__": None}, {})
            await interaction.response.send_message(f"🧮 Result: `{expression}` = **{result}**")
        except Exception as e:
            await interaction.response.send_message(f"❌ Error calculating: {str(e)}", ephemeral=True)

    @app_commands.command(name="poll", description="Create a simple poll with two options")
    async def poll(self, interaction: discord.Interaction, question: str, option_a: str, option_b: str):
        embed = discord.Embed(title="📊 Poll", description=question, color=discord.Color.teal())
        embed.add_field(name="Option A 🇦", value=option_a, inline=False)
        embed.add_field(name="Option B 🇧", value=option_b, inline=False)
        embed.set_footer(text=f"Poll started by {interaction.user.display_name}")

        await interaction.response.send_message(embed=embed)
        message = await interaction.original_response()

        await message.add_reaction("🇦")
        await message.add_reaction("🇧")

    @app_commands.command(name="qr", description="Generate a QR code for a URL")
    async def qr(self, interaction: discord.Interaction, url: str):
        # Defer the response as QR generation might take a moment (though usually fast)
        await interaction.response.defer(thinking=True)

        qr_img = qrcode.make(url)
        buffer = io.BytesIO()
        qr_img.save(buffer, "PNG")
        buffer.seek(0)

        file = discord.File(buffer, filename="qrcode.png")
        await interaction.followup.send(file=file)

    @app_commands.command(name="dm", description="Send a direct message to a user (Admin only)")
    @app_commands.checks.has_permissions(administrator=True)
    async def dm(self, interaction: discord.Interaction, member: discord.Member, message: str):
        try:
            await member.send(message)
            await interaction.response.send_message(f"✅ Sent DM to {member.mention}", ephemeral=True)
        except discord.Forbidden:
            await interaction.response.send_message(f"❌ Could not DM {member.mention}. They might have DMs disabled.", ephemeral=True)
        except Exception as e:
             await interaction.response.send_message(f"❌ Failed to send DM: {e}", ephemeral=True)

    @dm.error
    async def dm_error(self, interaction: discord.Interaction, error: app_commands.AppCommandError):
        if isinstance(error, app_commands.MissingPermissions):
            await interaction.response.send_message("❌ You do not have permission to use this command.", ephemeral=True)

async def setup(bot):
    await bot.add_cog(Utils(bot))
