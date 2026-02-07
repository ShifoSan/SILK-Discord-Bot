import discord
from datetime import datetime, timezone

def log_voice_event(member, before, after):
    embed = None

    # Join
    if before.channel is None and after.channel is not None:
        embed = discord.Embed(
            title="Voice Channel Join",
            description=f"**User:** {member.mention} (`{member.name}`)\n**Channel:** {after.channel.mention} (`{after.channel.name}`)",
            color=0x2ecc71,
            timestamp=datetime.now(timezone.utc)
        )
        embed.add_field(name="Executed by", value=f"{member.mention} (`{member.id}`)", inline=False)

    # Leave
    elif before.channel is not None and after.channel is None:
        embed = discord.Embed(
            title="Voice Channel Leave",
            description=f"**User:** {member.mention} (`{member.name}`)\n**Channel:** {before.channel.mention} (`{before.channel.name}`)",
            color=0xe74c3c,
            timestamp=datetime.now(timezone.utc)
        )
        embed.add_field(name="Executed by", value=f"{member.mention} (`{member.id}`)", inline=False)

    # Move
    elif before.channel is not None and after.channel is not None and before.channel != after.channel:
        embed = discord.Embed(
            title="Voice Channel Move",
            description=f"**User:** {member.mention} (`{member.name}`)",
            color=0xf1c40f,
            timestamp=datetime.now(timezone.utc)
        )
        embed.add_field(name="From", value=f"{before.channel.mention} (`{before.channel.name}`)", inline=False)
        embed.add_field(name="To", value=f"{after.channel.mention} (`{after.channel.name}`)", inline=False)
        embed.add_field(name="Executed by", value=f"{member.mention} (`{member.id}`)", inline=False)

    if embed:
        embed.add_field(name="Time", value=f"<t:{int(datetime.now(timezone.utc).timestamp())}:R>", inline=False)
        embed.set_footer(text=f"ID: {member.id}")
        return embed

    return None
