import discord
from datetime import datetime, timezone

async def get_executor(guild, target_id):
    async for entry in guild.audit_logs(limit=5, action=discord.AuditLogAction.member_update):
        if entry.target.id == target_id:
            return entry.user
    return None

async def log_member_update(before, after):
    if before.nick == after.nick:
        return None

    executor = await get_executor(after.guild, after.id)

    embed = discord.Embed(
        title="Member Updated",
        description=f"**Member:** {after.mention} (`{after.name}`)",
        color=0xf1c40f,
        timestamp=datetime.now(timezone.utc)
    )

    embed.add_field(name="Changes", value=f"**Nickname:** `{before.nick}` -> `{after.nick}`", inline=False)

    if executor:
        embed.add_field(name="Executed by", value=f"{executor.mention} (`{executor.id}`)", inline=False)
    else:
        embed.add_field(name="Executed by", value="Unknown", inline=False)

    embed.add_field(name="Time", value=f"<t:{int(datetime.now(timezone.utc).timestamp())}:R>", inline=False)
    embed.set_footer(text=f"ID: {after.id}")
    return embed
