import discord

def get_embed() -> discord.Embed:
    embed = discord.Embed(
        title="🧠 Quick AI Suite",
        description="Powered by the latest LLMs, these tools allow you to generate ideas, roasts, and more.",
        color=discord.Color.from_str("#2B2D31")
    )

    embed.add_field(
        name="**/roast** `[user]`",
        value="Roasts the specified user. Brutally.",
        inline=False
    )
    embed.add_field(
        name="**/translate** `[language]` `[text]`",
        value="Translates the text into the target language.",
        inline=False
    )

    return embed
