import discord

def get_embed() -> discord.Embed:
    embed = discord.Embed(
        title="🎭 Anime Roleplay: Phase 12",
        description="Interactive roleplay commands powered by Waifu.pics.",
        color=discord.Color.from_str("#FFC0CB")
    )

    embed.add_field(
        name="Categories",
        value="• **Affection**: `/hug`, `/kiss`, `/cuddle`, `/pat`, `/poke`, `/lick`, `/bite`, `/handhold`, `/glomp`\n• **Action**: `/slap`, `/kill`, `/kick`, `/bonk`, `/yeet`, `/highfive`, `/wave`\n• **Emotion**: `/smile`, `/blush`, `/wink`, `/dance`, `/cringe`, `/cry`, `/happy`, `/nom`\n• **Special**: `/bully`, `/smug`",
        inline=False
    )

    embed.add_field(
        name="Command Types",
        value="• **Interactive**: Commands like `/hug` require a target user.\n• **Emotion**: Commands like `/smile` are solo-compatible but can optionally target someone.",
        inline=False
    )

    embed.add_field(
        name="Visuals",
        value="All commands use soft pink embeds with unique flavor text and animated GIFs.",
        inline=False
    )

    return embed
