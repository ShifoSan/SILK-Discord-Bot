import discord
from discord.ext import commands
import re
import asyncio

class PrefixHandler(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        # Compile the regex pattern once on startup for maximum execution speed
        self.trade_split_pattern = re.compile(r'\s+for\s+', re.IGNORECASE)

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        # 1. Gatekeeping: Quick exits to minimize CPU impact on busy servers
        if message.author.bot or not message.content.startswith('?'):
            return

        # Clean the input query string
        raw_content = message.content[1:].strip()
        if not raw_content:
            return

        # 2. Safety Guard: Ignore common conversational text anomalies 
        # (e.g. typing just '???' or '? punctuation test')
        if len(raw_content) < 2 or raw_content.startswith('?'):
            return

        # 3. Dynamic Cog Routing Matrix
        trade_match = self.trade_split_pattern.split(raw_content)

        if len(trade_match) > 1:
            # Handle Trade Compare Syntax
            trade_cog = self.bot.get_cog("TradeCompare")
            if trade_cog:
                giving_items = trade_match[0].strip()
                getting_items = trade_match[1].strip()
                
                # Check for empty split parameters (e.g. "? item for ")
                if giving_items and getting_items:
                    asyncio.create_task(
                        trade_cog.execute_trade_compare(
                            destination=message.channel,
                            user=message.author,
                            giving=giving_items,
                            getting=getting_items
                        )
                    )
        else:
            # Handle Single Item Value Lookup
            value_cog = self.bot.get_cog("AoTRValue")
            if value_cog:
                asyncio.create_task(
                    value_cog.execute_value_lookup(
                        destination=message.channel,
                        user=message.author,
                        guild=message.guild,
                        item=raw_content
                    )
                )

async def setup(bot):
    await bot.add_cog(PrefixHandler(bot))
