import discord

def get_embed() -> discord.Embed:
    embed = discord.Embed(
        title="🎭 Text Playground",
        description="Fun text manipulation tools.",
        color=discord.Color.from_str("#FFFFFF")
    )

    embed.add_field(
        name="**/mock** `[text]`",
        value="CoNvErTs TeXt To SpOnGeBoB cAsE.",
        inline=False
    )
    embed.add_field(
        name="**/reverse** `[text]`",
        value="txet eht sesreveR.",
        inline=False
    )
    embed.add_field(
        name="**/clap** `[text]`",
        value="Adds 👏 emojis 👏 between 👏 words.",
        inline=False
    )
    embed.add_field(
        name="**/say** `[text]`",
        value="Makes the bot repeat what you say.",
        inline=False
    )

    return embed
