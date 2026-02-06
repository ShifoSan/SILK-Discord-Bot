import discord

def get_embed() -> discord.Embed:
    embed = discord.Embed(
        title="🧠 Quick AI Suite",
        description="Powered by the latest LLMs, these tools allow you to generate ideas, roasts, and more.",
        color=discord.Color.from_str("#2B2D31")
    )

    embed.add_field(
        name="**/idea**",
        value="Generates a unique coding project idea or YouTube video concept.",
        inline=False
    )
    embed.add_field(
        name="**/roast** `[user]`",
        value="Roasts the specified user. Brutally.",
        inline=False
    )
    embed.add_field(
        name="**/whois** `[character]`",
        value="Generates a character card (Name, Origin, Powers, Weakness) for a fictional character.",
        inline=False
    )
    embed.add_field(
        name="**/summary** `[text]`",
        value="Summarizes the provided text into exactly 3 bullet points.",
        inline=False
    )
    embed.add_field(
        name="**/define** `[word]`",
        value="Provides the formal definition of a word.",
        inline=False
    )
    embed.add_field(
        name="**/slang** `[word]`",
        value="Provides the street definition and usage of a word.",
        inline=False
    )
    embed.add_field(
        name="**/translate** `[language]` `[text]`",
        value="Translates the text into the target language.",
        inline=False
    )
    embed.add_field(
        name="**/ship** `[user1]` `[user2]`",
        value="Checks compatibility and generates a short love story.",
        inline=False
    )

    return embed
