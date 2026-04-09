import discord
from discord.ext import commands, tasks
import psutil
import time
import os
import motor.motor_asyncio
import certifi
import aiohttp

class Heartbeat(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.start_time = time.time()

        # Database connection
        MONGO_URI = os.getenv("MONGO_URI")
        if MONGO_URI:
            self.db_client = motor.motor_asyncio.AsyncIOMotorClient(MONGO_URI, tlsCAFile=certifi.where())
        else:
            self.db_client = motor.motor_asyncio.AsyncIOMotorClient("mongodb://localhost:27017/")

        self.db = self.db_client.silk_bot
        self.bot_live_stats = self.db.bot_live_stats

        # Leveling DB for user count
        self.level_db = self.db_client.silk_level_system
        self.level_users = self.level_db.users

        self.hf_url = "https://router.huggingface.co/hf-inference/models/black-forest-labs/FLUX.1-schnell"

        self.heartbeat_loop.start()

    def cog_unload(self):
        self.heartbeat_loop.cancel()

    @tasks.loop(seconds=60.0)
    async def heartbeat_loop(self):
        try:
            # 1. Hardware Metrics
            ram_usage_mb = psutil.virtual_memory().used / (1024 * 1024)
            cpu_usage_percent = psutil.cpu_percent()

            # 2. Discord Metrics
            ping_ms = round(self.bot.latency * 1000)
            uptime_seconds = int(time.time() - self.start_time)
            total_server_count = len(self.bot.guilds)
            total_member_count = sum(g.member_count for g in self.bot.guilds if g.member_count)
            connected_server_names = [g.name for g in self.bot.guilds]

            # 3. AI/API Metrics
            chat_cog = self.bot.get_cog('Chat')
            if chat_cog:
                ai_chat_counter = chat_cog.chat_counter
                active_voice_channels = len(chat_cog.voice_active_channels)
                active_global_persona = chat_cog.current_persona_name
                gemini_status = "Connected" if chat_cog.client else "Disconnected"
            else:
                ai_chat_counter = 0
                active_voice_channels = 0
                active_global_persona = "Unknown"
                gemini_status = "Unknown"

            # HuggingFace API check
            try:
                async with aiohttp.ClientSession() as session:
                    async with session.get(self.hf_url, timeout=5) as hf_res:
                        # It might return 401 Unauthorized or 405 Method Not Allowed, but that means it's alive.
                        hf_status = "Connected" if hf_res.status != 0 else "Disconnected"
            except:
                hf_status = "Disconnected"

            # 4. Database Metrics
            start_ping = time.time()
            await self.db_client.admin.command('ping')
            db_latency_ms = round((time.time() - start_ping) * 1000)

            total_leveling_users = await self.level_users.count_documents({})

            # Payload
            payload = {
                "hardware": {
                    "ram_usage_mb": round(ram_usage_mb, 2),
                    "cpu_usage_percent": round(cpu_usage_percent, 2)
                },
                "discord": {
                    "ping_ms": ping_ms,
                    "uptime_seconds": uptime_seconds,
                    "total_server_count": total_server_count,
                    "total_member_count": total_member_count,
                    "connected_server_names": connected_server_names
                },
                "ai_api": {
                    "ai_chat_counter": ai_chat_counter,
                    "active_voice_channels": active_voice_channels,
                    "api_connection_status": {
                        "gemini": gemini_status,
                        "huggingface": hf_status
                    }
                },
                "database": {
                    "latency_ms": db_latency_ms,
                    "total_leveling_users": total_leveling_users,
                    "active_global_persona": active_global_persona
                },
                "timestamp": time.time()
            }

            # Update MongoDB with upsert
            await self.bot_live_stats.update_one(
                {"_id": "current_stats"},
                {"$set": payload},
                upsert=True
            )

        except Exception as e:
            print(f"Error in heartbeat loop: {e}")

    @heartbeat_loop.before_loop
    async def before_heartbeat_loop(self):
        await self.bot.wait_until_ready()

async def setup(bot):
    await bot.add_cog(Heartbeat(bot))
