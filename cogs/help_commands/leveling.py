import discord

def get_embed() -> discord.Embed:
    embed = discord.Embed(
        title="📈 Leveling System",
        description="Earn XP and level up by being active in the server!",
        color=discord.Color.from_str("#FFD700")
    )

    embed.add_field(
        name="How to earn XP",
        value="You can earn XP naturally by chatting in text channels, adding reactions to messages, and hanging out in Voice Channels. Keep being active to level up faster!",
        inline=False
    )

    embed.add_field(
        name="**/rank** `[user]`",
        value="Generates a custom, real-time image card showing your current level, rank, and XP progress. You can also view another user's rank.",
        inline=False
    )

    embed.add_field(
        name="**/leaderboard**",
        value="Shows the top users in the server. It also has a toggle to view the voice activity leaderboard instead of text XP.",
        inline=False
    )

    embed.add_field(
        name="Fun Features",
        value="Leveling up can trigger personalized AI congratulation messages (if configured by admins). Your data is safely retained even if you temporarily leave the server, so you never lose your progress!",
        inline=False
    )

    return embed
