import discord

def get_embed() -> discord.Embed:
    embed = discord.Embed(
        title="💬 S.I.L.K. Chat Interface",
        description="Interact with S.I.L.K. naturally in enabled channels.",
        color=discord.Color.from_str("#2B2D31")
    )

    embed.add_field(
        name="**/chat_toggle** `[state]`",
        value="Enable (`True`) or Disable (`False`) auto-chat in the current channel.",
        inline=False
    )
    embed.add_field(
        name="**/persona** `[name]`",
        value="Switch S.I.L.K.'s personality (e.g., Standard, Edgy, Helpful).",
        inline=False
    )

    embed.add_field(
        name="Features",
        value="• **Context Aware**: Remembers the last 20 messages.\n• **Dynamic**: Personality changes affect safety filters and tone.\n• **Smart**: Uses Gemini 1.5 Pro (via Gemma 3 27b IT model).",
        inline=False
    )

    return embed
