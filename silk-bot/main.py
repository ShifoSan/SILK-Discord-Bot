import discord
import os
from discord.ext import commands
from dotenv import load_dotenv
import keep_alive

# Load environment variables
load_dotenv()

# Start the Keep-Alive server
keep_alive.run()

class SilkBot(commands.Bot):
    def __init__(self):
        super().__init__(
            command_prefix="!", # Required but not used for slash commands
            intents=discord.Intents.all(),
            help_command=None
        )

    async def setup_hook(self):
        # Load extensions
        cogs_folder = './cogs'
        if os.path.exists(cogs_folder):
            for filename in os.listdir(cogs_folder):
                if filename.endswith('.py'):
                    try:
                        await self.load_extension(f'cogs.{filename[:-3]}')
                        print(f"Loaded extension: {filename}")
                    except Exception as e:
                        print(f"Failed to load extension {filename}: {e}")

        # Sync commands to specific Guild
        guild_id = os.getenv("GUILD_ID")
        if guild_id:
            try:
                guild_obj = discord.Object(id=guild_id)
                self.tree.copy_global_to(guild=guild_obj)
                await self.tree.sync(guild=guild_obj)
                print(f"Synced commands to Guild ID: {guild_id}")
            except Exception as e:
                 print(f"Failed to sync commands: {e}")
        else:
            print("Warning: GUILD_ID not found in environment variables. Commands not synced.")

    async def on_ready(self):
        print(f'Logged in as {self.user} (ID: {self.user.id})')
        print('------')

def main():
    token = os.getenv("DISCORD_TOKEN")
    if not token:
        print("Error: DISCORD_TOKEN not found in environment variables.")
        return

    bot = SilkBot()
    bot.run(token)

if __name__ == "__main__":
    main()
