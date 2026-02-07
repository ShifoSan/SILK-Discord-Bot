import discord
from datetime import datetime, timezone

async def get_executor(guild, action, target_id):
    async for entry in guild.audit_logs(limit=5, action=action):
        if entry.target.id == target_id:
            return entry.user
    return None

async def log_role_create(role):
    executor = await get_executor(role.guild, discord.AuditLogAction.role_create, role.id)
    embed = discord.Embed(
        title="Role Created",
        description=f"**Role:** {role.mention} (`{role.name}`)",
        color=0x2ecc71,
        timestamp=datetime.now(timezone.utc)
    )
    if executor:
        embed.add_field(name="Executed by", value=f"{executor.mention} (`{executor.id}`)", inline=False)
    else:
        embed.add_field(name="Executed by", value="Unknown", inline=False)

    embed.add_field(name="Time", value=f"<t:{int(datetime.now(timezone.utc).timestamp())}:R>", inline=False)
    embed.set_footer(text=f"ID: {role.id}")
    return embed

async def log_role_delete(role):
    executor = await get_executor(role.guild, discord.AuditLogAction.role_delete, role.id)
    embed = discord.Embed(
        title="Role Deleted",
        description=f"**Role:** `{role.name}`",
        color=0xe74c3c,
        timestamp=datetime.now(timezone.utc)
    )
    if executor:
        embed.add_field(name="Executed by", value=f"{executor.mention} (`{executor.id}`)", inline=False)
    else:
        embed.add_field(name="Executed by", value="Unknown", inline=False)

    embed.add_field(name="Time", value=f"<t:{int(datetime.now(timezone.utc).timestamp())}:R>", inline=False)
    embed.set_footer(text=f"ID: {role.id}")
    return embed

async def log_role_update(before, after):
    executor = await get_executor(after.guild, discord.AuditLogAction.role_update, after.id)
    embed = discord.Embed(
        title="Role Updated",
        description=f"**Role:** {after.mention} (`{after.name}`)",
        color=0xf1c40f,
        timestamp=datetime.now(timezone.utc)
    )

    changes = []
    if before.name != after.name:
        changes.append(f"**Name:** `{before.name}` -> `{after.name}`")
    if before.color != after.color:
        changes.append(f"**Color:** `{before.color}` -> `{after.color}`")
    if before.permissions.value != after.permissions.value:
         changes.append(f"**Permissions:** Changed")
    if before.hoist != after.hoist:
         changes.append(f"**Hoisted:** `{before.hoist}` -> `{after.hoist}`")
    if before.mentionable != after.mentionable:
         changes.append(f"**Mentionable:** `{before.mentionable}` -> `{after.mentionable}`")

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
