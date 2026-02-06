import discord

def get_embed() -> discord.Embed:
    embed = discord.Embed(
        title="🎨 Vision & Voice",
        description="Creative tools for generating media and fetching news.",
        color=discord.Color.from_str("#2B2D31")
    )

    embed.add_field(
        name="**/tech_news**",
        value="Fetches the top 3 AI/Tech headlines.",
        inline=False
    )
    embed.add_field(
        name="**/imagine** `[prompt]`",
        value="Generates an AI image based on your description (Stable Diffusion XL).",
        inline=False
    )
    embed.add_field(
        name="**/voice** `[text]`",
        value="Converts your text into a spoken MP3 file.",
        inline=False
    )

    return embed
