import discord

def get_embed() -> discord.Embed:
    embed = discord.Embed(
        title="👑 Creator: ShifoSan",
        description="The mastermind behind S.I.L.K.",
        color=discord.Color.from_str("#E74C3C")
    )

    embed.add_field(
        name="YouTube",
        value="[ShifoSan Labs](https://www.youtube.com/@ShifoSan)",
        inline=True
    )
    embed.add_field(
        name="X (Twitter)",
        value="[@ShifoSan](https://twitter.com/ShifoSan)",
        inline=True
    )
    embed.add_field(
        name="Roblox",
        value="[ShifoSan](https://www.roblox.com/users/ShifoSan/profile)",
        inline=True
    )
    embed.add_field(
        name="Discord Server",
        value="[Join Here](https://discord.gg/uvuBxdHZ3u)",
        inline=False
    )

    embed.set_footer(text="Built by ShifoSan.")
    return embed
