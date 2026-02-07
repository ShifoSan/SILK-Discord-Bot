import discord
from datetime import datetime, timezone

async def get_executor(guild, action, target_id):
    async for entry in guild.audit_logs(limit=5, action=action):
        if entry.target.id == target_id:
            return entry.user
    return None

async def log_channel_create(channel):
    executor = await get_executor(channel.guild, discord.AuditLogAction.channel_create, channel.id)

    embed = discord.Embed(
        title="Channel Created",
        description=f"**Channel:** {channel.mention} (`{channel.name}`)\n**Type:** {str(channel.type).capitalize()}",
        color=0x2ecc71,
        timestamp=datetime.now(timezone.utc)
    )
    if executor:
        embed.add_field(name="Executed by", value=f"{executor.mention} (`{executor.id}`)", inline=False)
    else:
        embed.add_field(name="Executed by", value="Unknown", inline=False)

    embed.add_field(name="Time", value=f"<t:{int(datetime.now(timezone.utc).timestamp())}:R>", inline=False)
    embed.set_footer(text=f"ID: {channel.id}")
    return embed

async def log_channel_delete(channel):
    # For deletion, the channel is gone, but we can check the audit log for the channel ID or name if needed.
    # But usually audit log retains the ID in target.
    executor = await get_executor(channel.guild, discord.AuditLogAction.channel_delete, channel.id)

    embed = discord.Embed(
        title="Channel Deleted",
        description=f"**Channel:** `{channel.name}`\n**Type:** {str(channel.type).capitalize()}",
        color=0xe74c3c,
        timestamp=datetime.now(timezone.utc)
    )
    if executor:
        embed.add_field(name="Executed by", value=f"{executor.mention} (`{executor.id}`)", inline=False)
    else:
        embed.add_field(name="Executed by", value="Unknown", inline=False)

    embed.add_field(name="Time", value=f"<t:{int(datetime.now(timezone.utc).timestamp())}:R>", inline=False)
    embed.set_footer(text=f"ID: {channel.id}")
    return embed

async def log_channel_update(before, after):
    executor = await get_executor(after.guild, discord.AuditLogAction.channel_update, after.id)

    embed = discord.Embed(
        title="Channel Updated",
        description=f"**Channel:** {after.mention} (`{after.name}`)",
        color=0xf1c40f,
        timestamp=datetime.now(timezone.utc)
    )

    changes = []
    if before.name != after.name:
        changes.append(f"**Name:** `{before.name}` -> `{after.name}`")
    if before.category != after.category:
        before_cat = before.category.name if before.category else "None"
        after_cat = after.category.name if after.category else "None"
        changes.append(f"**Category:** `{before_cat}` -> `{after_cat}`")

    if changes:
        embed.add_field(name="Changes", value="\n".join(changes), inline=False)
    else:
        embed.description += "\n(Unknown or internal update)"

    if executor:
        embed.add_field(name="Executed by", value=f"{executor.mention} (`{executor.id}`)", inline=False)
    else:
        embed.add_field(name="Executed by", value="Unknown", inline=False)

    embed.add_field(name="Time", value=f"<t:{int(datetime.now(timezone.utc).timestamp())}:R>", inline=False)
    embed.set_footer(text=f"ID: {after.id}")
    return embed
