import asyncio
import os
import motor.motor_asyncio
from dotenv import load_dotenv

load_dotenv()

async def main():
    MONGO_URI = os.getenv("MONGO_URI")
    if MONGO_URI:
        client = motor.motor_asyncio.AsyncIOMotorClient(MONGO_URI)
    else:
        client = motor.motor_asyncio.AsyncIOMotorClient("mongodb://localhost:27017/")

    db = client.silk_bot
    stats_col = db.bot_live_stats

    payload = {
        "hardware": {
            "ram_usage_mb": 1024.5,
            "cpu_usage_percent": 15.2
        },
        "discord": {
            "ping_ms": 45,
            "uptime_seconds": 3600 * 24 + 3600 * 2 + 15 * 60,
            "total_server_count": 10,
            "total_member_count": 500,
            "connected_server_names": ["Test Server 1", "S.I.L.K HQ"]
        },
        "ai_api": {
            "ai_chat_counter": 42,
            "active_voice_channels": 2,
            "api_connection_status": {
                "gemini": "Connected",
                "huggingface": "Connected"
            }
        },
        "database": {
            "latency_ms": 12,
            "total_leveling_users": 150,
            "active_global_persona": "Standard"
        },
        "timestamp": 1234567890
    }

    await stats_col.update_one(
        {"_id": "current_stats"},
        {"$set": payload},
        upsert=True
    )
    print("Stats seeded!")
    client.close()

if __name__ == "__main__":
    asyncio.run(main())
