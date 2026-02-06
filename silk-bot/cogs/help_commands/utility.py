import discord

def get_embed() -> discord.Embed:
    embed = discord.Embed(
        title="🛠️ Utility Belt",
        description="Essential tools and random number generators.",
        color=discord.Color.from_str("#FFFFFF")
    )

    embed.add_field(
        name="**/ping**",
        value="Checks the bot's latency.",
        inline=True
    )
    embed.add_field(
        name="**/uptime**",
        value="Shows how long S.I.L.K. has been online.",
        inline=True
    )
    embed.add_field(
        name="**/serverinfo**",
        value="Displays detailed server information.",
        inline=True
    )
    embed.add_field(
        name="**/userinfo** `[member]`",
        value="Displays information about a user.",
        inline=True
    )
    embed.add_field(
        name="**/avatar** `[member]`",
        value="Shows the full-size avatar of a user.",
        inline=True
    )
    embed.add_field(
        name="**/roll**",
        value="Rolls a 6-sided die.",
        inline=True
    )
    embed.add_field(
        name="**/flip**",
        value="Flips a coin (Heads or Tails).",
        inline=True
    )
    embed.add_field(
        name="**/choose** `[choice1]` `[choice2]`",
        value="Randomly picks between two options.",
        inline=True
    )
    embed.add_field(
        name="**/calc** `[expression]`",
        value="Solves a basic math expression (e.g., `5 + 5`).",
        inline=True
    )
    embed.add_field(
        name="**/poll** `[question]` `[option_a]` `[option_b]`",
        value="Creates a simple reaction poll.",
        inline=True
    )
    embed.add_field(
        name="**/qr** `[url]`",
        value="Generates a QR code for the provided URL.",
        inline=True
    )

    return embed
