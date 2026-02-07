import discord

def get_embed() -> discord.Embed:
    embed = discord.Embed(
        title="📝 The S.I.L.K. Journey",
        description="From a simple script to a 79-command 'Cyberpunk Assassin' AI, S.I.L.K. represents the relentless pursuit of perfection. Through sleepless nights and endless debugging, this modular architecture was forged to deliver an unparalleled Discord experience. With features ranging from 'God Mode' logging to advanced AI chat, S.I.L.K. stands as a testament to what's possible when you refuse to quit.",
        color=discord.Color.from_str("#2B2D31")
    )

    embed.add_field(
        name="Support the Dev",
        value="• **YouTube**: [ShifoSan Labs](https://youtube.com/@shifosanlabs?si=8N2_qArGeFeSmjOU)\n• **X (Twitter)**: [ShifoSan](https://x.com/ShifoSan)\n• **Roblox**: ShifoSan\n• **Discord Server**: [Join Here](https://discord.gg/uvuBxdHZ3u)",
        inline=False
    )

    embed.set_footer(text="Give up? Never!")
    return embed
