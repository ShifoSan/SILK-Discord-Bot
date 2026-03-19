import discord

def get_embed() -> discord.Embed:
    embed = discord.Embed(
        title="🎭 Anime Roleplay: Phase 12",
        description="All roleplay actions are now handled through a single command: `/emote [action] [target]`.\nPowered by Waifu.pics.",
        color=discord.Color.from_str("#FFC0CB")
    )

    embed.add_field(
        name="Emote Categories",
        value="• **Affection**: hug, kiss, pat, poke, lick, bite, handhold\n• **Action**: slap, kill, kick, highfive\n• **Special**: bully\n• **Emotion**: nom, smile, blush, wink, dance, cringe, cry, happy",
        inline=False
    )

    embed.add_field(
        name="Targeting",
        value="• **Interactive**: Actions like `hug` and `slap` require a target user.\n• **Emotion**: Actions like `smile` and `cry` can be used solo, but can optionally target someone.",
        inline=False
    )

    embed.add_field(
        name="Visuals",
        value="All commands use soft pink embeds with unique flavor text and animated GIFs.",
        inline=False
    )

    return embed
