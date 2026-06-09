import discord
from discord.ext import commands
import re

class EmbedBuilder(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.valid_fields = {
            "title", "description", "footer", "footer text", 
            "author name", "thumbnail link", "embed color", "channel"
        }

    def parse_embed_content(self, raw_text: str) -> dict:
        """Parses raw text dynamically extracting content between # <field> blocks."""
        matches = list(re.finditer(r"^\s*#\s+([A-Za-z0-9_ ]+)\s*$", raw_text, re.IGNORECASE | re.MULTILINE))
        
        parsed_data = {}
        if not matches:
            return parsed_data

        for i, match in enumerate(matches):
            field_name = match.group(1).lower().strip()
            
            if field_name == "footer text":
                field_name = "footer"

            if field_name in self.valid_fields:
                start_index = match.end()
                end_index = matches[i + 1].start() if i + 1 < len(matches) else len(raw_text)
                field_content = raw_text[start_index:end_index].strip()
                parsed_data[field_name] = field_content

        return parsed_data

    @commands.command(name="embed")
    async def embed(self, ctx):
        """Creates a customized embed based on markdown block inputs."""
        raw_message = ctx.message.content

        # Safely slice off the command prefix trigger
        if raw_message.lower().startswith("!embed"):
            raw_message = raw_message[6:]

        data = self.parse_embed_content(raw_message)

        # Fallbacks & Defaults
        title = data.get("title", "Standard Dynamic Embed Layout")
        description = data.get("description")

        # Resolve Color
        embed_color = discord.Color.blue()
        color_str = data.get("embed color")
        if color_str:
            try:
                cleaned_color = color_str.replace("#", "").strip()
                embed_color = discord.Color(int(cleaned_color, 16))
            except ValueError:
                pass

        # Build Embed
        embed = discord.Embed(
            title=title,
            description=description if description else None,
            color=embed_color
        )

        if "author name" in data:
            embed.set_author(name=data["author name"])

        if "thumbnail link" in data:
            embed.set_thumbnail(url=data["thumbnail link"])

        if "footer" in data:
            embed.set_footer(text=data["footer"])

        # Target Channel Routing
        target_channel = ctx.channel
        channel_str = data.get("channel")
        if channel_str:
            clean_channel_str = channel_str.replace("|", "").replace("<#", "").replace(">", "").strip()
            try:
                found_channel = self.bot.get_channel(int(clean_channel_str))
                if found_channel:
                    target_channel = found_channel
            except ValueError:
                pass

        try:
            await target_channel.send(embed=embed)
            if target_channel != ctx.channel:
                await ctx.send(f"✅ Embed has been dispatched successfully to {target_channel.mention}!")
        except discord.Forbidden:
            await ctx.send("❌ I do not have permission to send embeds or view that destination channel.")

    @commands.command(name="embed_format")
    async def embed_format(self, ctx):
        """Displays manual formatting parameters for the !embed operation."""
        format_guide = (
            "💡 **S.I.L.K. Embed Builder Manual**\n"
            "To build a customized embed card, write your configuration layout on individual lines directly following `!embed`. "
            "Fields are fully case-insensitive and can be ordered entirely at random!\n\n"
            "⚠️ **Rule:** Every parameter must begin exactly with `# <Field Name>` (the space after the `#` is strictly required).\n\n"
            "📋 **Copy & Paste Blueprint Template:**\n"
            "```text\n"
            "!embed\n"
            "# Title\n"
            "Your Awesome Title Here\n\n"
            "# Description\n"
            "This is the core content message. You can write paragraphs here!\n\n"
            "# Embed Color\n"
            "0xFF0000\n\n"
            "# Author Name\n"
            "S.I.L.K. Bot Engine\n\n"
            "# Thumbnail Link\n"
            "[https://example.com/image.png](https://example.com/image.png)\n\n"
            "# Footer Text\n"
            "End notes display here\n\n"
            "# Channel\n"
            "|<#1454151185132028218>|\n"
            "```\n"
            "*Note: If an alternate channel parameter is omitted or configured incorrectly, the card drops right into the current channel automatically.*"
        )
        await ctx.send(format_guide)

async def setup(bot):
    await bot.add_cog(EmbedBuilder(bot))
