import discord

def get_embed() -> discord.Embed:
    embed = discord.Embed(
        title="📺 YouTube Integration",
        description="Stay connected with ShifoLabs and promote other channels.",
        color=discord.Color.from_str("#2B2D31")
    )

    embed.add_field(
        name="**/stats**",
        value="Displays live subscriber count, total views, and video count for ShifoLabs.",
        inline=False
    )
    embed.add_field(
        name="**/latest**",
        value="Fetches and links the most recent video uploaded by ShifoLabs.",
        inline=False
    )
    embed.add_field(
        name="**/shoutout** `[channel_handle]`",
        value="Generates a promo card with stats for any YouTube channel.",
        inline=False
    )

    return embed
