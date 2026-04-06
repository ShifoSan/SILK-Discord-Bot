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
    ()
