import discord
import os
import asyncio
from discord.ext import commands
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

class SilkBot(commands.Bot):
    def __init__(self):
        super().__init__(
            command_prefix="!", # This is what allows the !sync command to work
            intents=discord.Intents.all(),
            help_command=None
        )

    async def setup_hook(self):
        # Load extensions
        cogs_folder = './cogs'
        if os.path.exists(cogs_folder):
            # 1. UNTOUCHED: Standard top-level file loader
            for filename in os.listdir(cogs_folder):
                if filename.endswith('.py'):
                    try:
                        await self.load_extension(f'cogs.{filename[:-3]}')
                        print(f"Loaded extension: {filename}")
                    except Exception as e:
                        print(f"Failed to load extension {filename}: {e}")

            # 2 & 3. REPLACED LEVEL SYSTEM: Dynamic Subdirectory Folder Loader
            for item in os.listdir(cogs_folder):
                item_path = os.path.join(cogs_folder, item)
                if os.path.isdir(item_path):
                    
                    # 4. NON-HARDCODED IGNORE RULE:
                    # Skips any folder containing a '.ignore' file or starting with an underscore '_'
                    if os.path.exists(os.path.join(item_path, '.ignore')) or item.startswith('_'):
                        continue
                    
                    # Recursively traverse permitted folders
                    for root, dirs, files in os.walk(item_path):
                        # Filter nested directories dynamically in-place
                        dirs[:] = [d for d in dirs if not os.path.exists(os.path.join(root, d, '.ignore')) and not d.startswith('_')]
                        
                        for filename in files:
                            if filename.endswith('.py') and filename != '__init__.py':
                                rel_path = os.path.relpath(os.path.join(root, filename), start='.')
                                module_path = rel_path[:-3].replace(os.sep, '.')
                                try:
                                    await self.load_extension(module_path)
                                    print(f"Loaded extension: {module_path}")
                                except Exception as e:
                                    print(f"Failed to load extension {module_path}: {e}")
                    
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
    
    # --- MANUAL SYNC COMMAND ---
    # Type !sync in any server to update slash commands across ALL servers with a safe cooldown.
    @bot.command(name="sync")
    @commands.is_owner()
    async def sync_commands(ctx):
        await ctx.send(f"🔄 Starting sync across all {len(bot.guilds)} servers. This will take a moment...")
        success_count = 0
        
        for guild in bot.guilds:
            try:
                bot.tree.copy_global_to(guild=guild)
                await bot.tree.sync(guild=guild)
                success_count += 1
                await asyncio.sleep(5)  # 5-second cooldown to prevent API bans
            except Exception as e:
                print(f"Failed to sync to {guild.name}: {e}")
        
        await ctx.send(f"✅ Sync complete! Successfully synced commands to {success_count}/{len(bot.guilds)} servers.")

    bot.run(token)

if __name__ == "__main__":
    main()
