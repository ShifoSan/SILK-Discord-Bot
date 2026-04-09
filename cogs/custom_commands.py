import discord
from discord.ext import commands
import os
import motor.motor_asyncio
from dotenv import load_dotenv

load_dotenv()
MONGO_URI = os.getenv("MONGO_URI")

class CustomCommands(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        # Connect to MongoDB
        self.db_client = motor.motor_asyncio.AsyncIOMotorClient(MONGO_URI)
        self.db = self.db_client.silk_bot
        self.custom_commands_col = self.db.custom_commands

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        # Ignore bots and direct messages
        if message.author.bot or message.guild is None:
            return

        # Query the custom_commands collection for this guild and exact trigger match
        command_config = await self.custom_commands_col.find_one({
            "guild_id": message.guild.id,
            "trigger": message.content
        })

        if command_config:
            response_text = command_config.get("response", "")
            reply_directly = command_config.get("reply_directly", False)

            if response_text:
                if reply_directly:
                    await message.reply(response_text)
                else:
                    await message.channel.send(response_text)

async def setup(bot):
    await bot.add_cog(CustomCommands(bot))
