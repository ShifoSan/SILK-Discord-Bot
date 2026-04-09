import os
import motor.motor_asyncio
import certifi
from datetime import datetime

MONGO_URI = os.getenv("MONGO_URI")
if MONGO_URI:
    # Added the tlsCAFile parameter to force updated certificates
    client = motor.motor_asyncio.AsyncIOMotorClient(MONGO_URI, tlsCAFile=certifi.where())
    db = client.silk_level_system
else:
    # Dummy DB for testing without URI
    client = motor.motor_asyncio.AsyncIOMotorClient("mongodb://localhost:27017/")
    db = client.silk_level_system

users_collection = db.users
configs_collection = db.guild_configs

# DEFAULT CONFIGURATION
DEFAULT_CONFIG = {
    "text_min_xp": 15,
    "text_max_xp": 25,
    "text_cooldown": 60,
    "reaction_cooldown": 60,
    "vc_cooldown": 60,
    "vc_xp_per_minute": 5,
    "vc_xp_enabled": True,
    "spam_channels_blacklist": [],
    "spam_min_length": 5,
    "role_rewards": {}, # "level_number": "role_id"
    "level_up_channel": None, # ID of channel to route messages to
    "level_up_thread_id": None, # ID of thread to route messages to
}

async def get_guild_config(guild_id: int) -> dict:
    config = await configs_collection.find_one({"guild_id": guild_id})
    if not config:
        config = DEFAULT_CONFIG.copy()
        config["guild_id"] = guild_id
        await configs_collection.insert_one(config)
    return config

async def update_guild_config(guild_id: int, updates: dict):
    await configs_collection.update_one(
        {"guild_id": guild_id},
        {"$set": updates},
        upsert=True
    )

async def get_user_data(guild_id: int, user_id: int) -> dict:
    user = await users_collection.find_one({"guild_id": guild_id, "user_id": user_id})
    if not user:
        user = {
            "guild_id": guild_id,
            "user_id": user_id,
            "xp": 0,
            "level": 0,
            "vc_xp": 0,
            "in_server": True,
            "last_text_xp": None,
            "last_reaction_xp": None,
            "last_vc_join": None
        }
        await users_collection.insert_one(user)
    return user

async def save_user_data(guild_id: int, user_id: int, updates: dict):
    await users_collection.update_one(
        {"guild_id": guild_id, "user_id": user_id},
        {"$set": updates},
        upsert=True
    )

async def get_top_users(guild_id: int, limit: int = 10, skip: int = 0, sort_by_vc: bool = False):
    sort_field = "vc_xp" if sort_by_vc else "xp"
    cursor = users_collection.find({"guild_id": guild_id, "in_server": True}).sort(sort_field, -1).skip(skip).limit(limit)
    return await cursor.to_list(length=limit)

async def get_user_rank(guild_id: int, user_id: int, sort_by_vc: bool = False) -> int:
    sort_field = "vc_xp" if sort_by_vc else "xp"
    user = await get_user_data(guild_id, user_id)
    score = user.get(sort_field, 0)

    count = await users_collection.count_documents({
        "guild_id": guild_id,
        "in_server": True,
        sort_field: {"$gt": score}
    })
    return count + 1
    
