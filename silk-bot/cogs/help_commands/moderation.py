import discord

def get_embed() -> discord.Embed:
    embed = discord.Embed(
        title="⚖️ The Judge",
        description="Standard server management and discipline tools.",
        color=discord.Color.from_str("#E74C3C")
    )

    embed.add_field(
        name="**/kick** `[user]` `[reason]`",
        value="Kicks a user from the server.",
        inline=False
    )
    embed.add_field(
        name="**/ban** `[user]` `[reason]`",
        value="Permanently bans a user.",
        inline=False
    )
    embed.add_field(
        name="**/unban** `[user_id]`",
        value="Unbans a user by their ID.",
        inline=False
    )
    embed.add_field(
        name="**/purge** `[amount]`",
        value="Bulk deletes messages in the current channel.",
        inline=False
    )
    embed.add_field(
        name="**/slowmode** `[seconds]`",
        value="Sets the channel slowmode delay (0 to disable).",
        inline=False
    )

    embed.set_footer(text="⚠️ Safety: Hierarchy checks are enforced.")
    return embed
