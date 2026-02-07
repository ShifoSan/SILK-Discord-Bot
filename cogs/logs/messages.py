import discord
from datetime import datetime, timezone

def log_message_edit(before, after):
    if before.author.bot:
        return None

    if before.content == after.content:
        return None

    embed = discord.Embed(
        title="Message Edited",
        description=f"**Author:** {before.author.mention} (`{before.author.name}`)\n**Channel:** {before.channel.mention}",
        color=0xf1c40f,
        timestamp=datetime.now(timezone.utc)
    )

    # Truncate if too long (Discord limit is 1024 for field value)
    before_content = before.content if len(before.content) < 1000 else before.content[:1000] + "..."
    after_content = after.content if len(after.content) < 1000 else after.content[:1000] + "..."

    if not before_content: before_content = "(No Content / Attachment)"
    if not after_content: after_content = "(No Content / Attachment)"

    embed.add_field(name="Before", value=before_content, inline=False)
    embed.add_field(name="After", value=after_content, inline=False)

    embed.add_field(name="Executed by", value=f"{before.author.mention} (`{before.author.id}`)", inline=False)
    embed.add_field(name="Time", value=f"<t:{int(datetime.now(timezone.utc).timestamp())}:R>", inline=False)
    embed.set_footer(text=f"ID: {before.id}")
    return embed

def log_message_delete(message):
    if message.author.bot:
        return None

    embed = discord.Embed(
        title="Message Deleted",
        description=f"**Author:** {message.author.mention} (`{message.author.name}`)\n**Channel:** {message.channel.mention}",
        color=0xe74c3c,
        timestamp=datetime.now(timezone.utc)
    )

    content = message.content if len(message.content) < 1000 else message.content[:1000] + "..."
    if not content: content = "(No Content / Attachment)"

    embed.add_field(name="Content", value=content, inline=False)

    # "Executed by" usually implies the author in this context unless verified otherwise via audit logs.
    # Since audit logs are not strictly required for message deletions in the spec, we default to the author.
    embed.add_field(name="Executed by", value=f"{message.author.mention} (`{message.author.id}`)", inline=False)

    embed.add_field(name="Time", value=f"<t:{int(datetime.now(timezone.utc).timestamp())}:R>", inline=False)
    embed.set_footer(text=f"ID: {message.id}")
    return embed
