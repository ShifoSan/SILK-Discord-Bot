import discord

def get_embed() -> discord.Embed:
    embed = discord.Embed(
        title="💬 S.I.L.K. Chat Interface",
        description="Interact with S.I.L.K. naturally in enabled channels.",
        color=discord.Color.from_str("#2B2D31")
    )

    embed.add_field(
        name="**/chat_toggle** `[enable]` `[mode]` `[toxicity]`",
        value="Configure auto-chat in the current channel. Set `enable` to True/False, choose `mode` (Censored/Uncensored), and optionally set `toxicity`.",
        inline=False
    )
    embed.add_field(
        name="**/voice_mode** `[state]`",
        value="Enable (`True`) or Disable (`False`) Hybrid Audio responses. When enabled, S.I.L.K. will reply with both text and a generated voice message.",
        inline=False
    )
    embed.add_field(
        name="**/ask-silk** `[question]`",
        value="Ask S.I.L.K. a question directly from anywhere in the server. Respects the channel's active Uncensored/Censored mode.",
        inline=False
    )
    embed.add_field(
        name="**/persona** `[name]`",
        value="Switch S.I.L.K.'s personality (e.g., Standard, Edgy, Helpful).",
        inline=False
    )

    embed.add_field(
        name="📩 Direct Messages",
        value="You can also DM S.I.L.K. (Requires Approval).",
        inline=False
    )

    embed.add_field(
        name="Global Reach",
        value="Even if auto-chat is disabled, S.I.L.K. will always respond if you:\n• **Mention** the bot (@S.I.L.K.)\n• **Reply** to one of its messages.",
        inline=False
    )

    embed.add_field(
        name="Features",
        value="• **Context Aware**: Remembers the last 20 messages.\n• **Dual-Model Architecture**: Toggle between Censored (Gemma 3) and Uncensored (Dolphin Mistral) AI modes per channel.\n• **Dynamic**: Uncensored mode supports 6 distinct toxicity levels.",
        inline=False
    )

    return embed
