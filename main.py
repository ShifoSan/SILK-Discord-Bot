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

            # Load level_system extensions manually since they are in subdirectories
            level_system_extensions = [
                'cogs.level_system.core',
                'cogs.level_system.commands',
                'cogs.level_system.bot_config.main_menu'
            ]
            for ext in level_system_extensions:
                try:
                    await self.load_extension(ext)
                    print(f"Loaded extension: {ext}")
                except Exception as e:
                    print(f"Failed to load extension {ext}: {e}")
                    
        # NOTE: Auto-syncing has been removed to prevent Discord Cloudflare 1015 IP Bans.
        print("Setup hook complete. Ready to connect to Discord.")

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
    
