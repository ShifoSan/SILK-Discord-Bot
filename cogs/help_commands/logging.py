import discord

def get_embed() -> discord.Embed:
    embed = discord.Embed(
        title="📊 The Watcher: Logging Module",
        description="Phase 11: Comprehensive server surveillance and audit logging.",
        color=discord.Color.gold()
    )

    embed.add_field(
        name="**/setup_logs**",
        value="Master Admin command. Automatically creates the '『LOGS』' category and 6 specific channels (#📊-channel-logs, etc.).\n*Idempotent: Checks for existing channels/categories before creation to prevent duplicates.*",
        inline=False
    )

    embed.add_field(
        name="Features",
        value="• **Visual Coding**: distinct color-coded Embeds for Creates (Green), Deletes (Red), and Updates (Yellow).\n• **Audit Intelligence**: Automatically fetches `guild.audit_logs` to identify *who* performed an action.\n• **Granular Tracking**: Messages (Edits/Deletes), Members (Nicknames), Voice (Joins/Leaves/Moves), Infrastructure (Channel/Role changes).",
        inline=False
    )

    embed.add_field(
        name="Security",
        value="Log channels are automatically set to private (`view_channel=False` for @everyone).",
        inline=False
    )

    return embed
