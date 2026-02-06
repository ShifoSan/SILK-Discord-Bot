import discord

def get_embed() -> discord.Embed:
    embed = discord.Embed(
        title="🏗️ Server Architect",
        description="AI-powered infrastructure management.",
        color=discord.Color.from_str("#E74C3C")
    )

    embed.add_field(
        name="**/architect** `[instruction]`",
        value="Creates channels and categories based on your natural language instruction.",
        inline=False
    )
    embed.add_field(
        name="**/demolish** `[instruction]`",
        value="Destroys channels and categories based on your instruction.",
        inline=False
    )

    embed.set_footer(text="⚠️ Admin Only. Use with caution.")
    return embed
