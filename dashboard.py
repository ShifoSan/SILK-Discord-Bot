import os
import secrets
from quart import Quart, request, jsonify, session, redirect, render_template
from dotenv import load_dotenv
import motor.motor_asyncio
import certifi
import urllib.request
import urllib.parse
import aiohttp
from better_profanity import profanity
print("MY RAW SERVER IP IS:", urllib.request.urlopen('https://api.ipify.org').read().decode('utf8'))


# Load environment variables
load_dotenv()

app = Quart(__name__)

# Configure Secret Key
app.secret_key = os.getenv("QUART_SECRET_KEY") or secrets.token_hex(24)

# Database Setup
MONGO_URI = os.getenv("MONGO_URI")
if not MONGO_URI:
    print("Warning: MONGO_URI not found in .env file.")

# Discord OAuth2 Setup
DISCORD_CLIENT_ID = os.getenv("DISCORD_CLIENT_ID")
DISCORD_CLIENT_SECRET = os.getenv("DISCORD_CLIENT_SECRET")
DISCORD_REDIRECT_URI = os.getenv("DISCORD_REDIRECT_URI")


@app.before_serving
async def setup_db():
    if MONGO_URI:
        app.db_client = motor.motor_asyncio.AsyncIOMotorClient(MONGO_URI, tlsCAFile=certifi.where())
    else:
        app.db_client = motor.motor_asyncio.AsyncIOMotorClient("mongodb://localhost:27017/")
    app.db = app.db_client.silk_bot
    app.chat_configs = app.db.chat_configs
    app.bot_statuses = app.db.bot_statuses
    app.personalities = app.db.personalities
    app.bot_live_stats = app.db.bot_live_stats

@app.after_serving
async def close_db():
    if app.db_client:
        app.db_client.close()

# --- API Routes ---

@app.route("/api/live_stats", methods=["GET"])
async def get_live_stats():
    if getattr(app, "bot_live_stats", None) is None:
        return jsonify({"error": "Database not connected"}), 500

    stats = await app.bot_live_stats.find_one({"_id": "current_stats"})
    if stats:
        # Remove _id for JSON serialization
        stats.pop("_id", None)
        return jsonify(stats), 200
    else:
        return jsonify({"error": "No stats available yet"}), 404

@app.route("/api/chat_configs/<int:guild_id>", methods=["GET"])
async def get_chat_config(guild_id):
    if app.chat_configs is None:
        return jsonify({"error": "Database not connected"}), 500

    config = await app.chat_configs.find_one({"channel_id": guild_id}, {"_id": 0})
    if config:
        return jsonify(config), 200
    else:
        # Return default if not found
        return jsonify({"channel_id": guild_id, "enabled": False, "language": "English"}), 200

@app.route("/api/chat_configs/<int:guild_id>", methods=["POST"])
async def update_chat_config(guild_id):
    if app.chat_configs is None:
        return jsonify({"error": "Database not connected"}), 500

    data = await request.get_json()
    if not data:
        return jsonify({"error": "Invalid or missing JSON payload"}), 400

    # Validation
    enabled = data.get("enabled")
    language = data.get("language")

    if enabled is not None and not isinstance(enabled, bool):
        return jsonify({"error": "Field 'enabled' must be a boolean"}), 400

    if language is not None and language not in ["English", "Hindi"]:
        return jsonify({"error": "Field 'language' must be either 'English' or 'Hindi'"}), 400

    # If both missing
    if enabled is None and language is None:
        return jsonify({"error": "No valid fields provided for update"}), 400

    update_data = {}
    if enabled is not None:
        update_data["enabled"] = enabled
    if language is not None:
        update_data["language"] = language

    # Note: In the bot, channel_id represents the configuration context (sometimes guild_id or channel_id).
    # Using guild_id as channel_id here based on the requirement and bot implementation structure.
    await app.chat_configs.update_one(
        {"channel_id": guild_id},
        {"$set": update_data},
        upsert=True
    )

    return jsonify({"message": "Configuration updated successfully", "updated": update_data}), 200


# --- OAuth Routes ---

@app.route("/login")
async def login():
    params = {
        "client_id": DISCORD_CLIENT_ID,
        "redirect_uri": DISCORD_REDIRECT_URI,
        "response_type": "code",
        "scope": "identify guilds"
    }
    auth_url = f"https://discord.com/api/oauth2/authorize?{urllib.parse.urlencode(params)}"
    return redirect(auth_url)

@app.route("/callback")
async def callback():
    code = request.args.get("code")
    if not code:
        return jsonify({"error": "Failed to authenticate with Discord"}), 500

    data = {
        "client_id": DISCORD_CLIENT_ID,
        "client_secret": DISCORD_CLIENT_SECRET,
        "grant_type": "authorization_code",
        "code": code,
        "redirect_uri": DISCORD_REDIRECT_URI
    }

    headers = {
        "Content-Type": "application/x-www-form-urlencoded"
    }

    async with aiohttp.ClientSession() as http_session:
        # Exchange code for token
        async with http_session.post("https://discord.com/api/oauth2/token", data=data, headers=headers) as resp:
            if resp.status != 200:
                return jsonify({"error": "Failed to authenticate with Discord"}), 500
            token_data = await resp.json()
            access_token = token_data.get("access_token")

        if not access_token:
            return jsonify({"error": "Failed to authenticate with Discord"}), 500

        # Fetch user profile
        user_headers = {
            "Authorization": f"Bearer {access_token}"
        }
        async with http_session.get("https://discord.com/api/users/@me", headers=user_headers) as resp:
            if resp.status != 200:
                return jsonify({"error": "Failed to authenticate with Discord"}), 500
            user_data = await resp.json()

    # Store user in session
    session["user_id"] = user_data.get("id")
    session["username"] = user_data.get("username")
    session["access_token"] = access_token

    return redirect("/dashboard")

@app.route("/api/statuses", methods=["GET"])
async def get_statuses():
    if app.bot_statuses is None:
        return jsonify({"error": "Database not connected"}), 500
    statuses = []
    async for status in app.bot_statuses.find({}, {"_id": 0}):
        statuses.append(status)
    return jsonify(statuses), 200

@app.route("/api/statuses", methods=["POST"])
async def upsert_status():
    if not session.get("user_id"):
        return jsonify({"error": "Unauthorized"}), 401

    if app.bot_statuses is None:
        return jsonify({"error": "Database not connected"}), 500
    data = await request.get_json()
    if not data or "text" not in data or "type" not in data:
        return jsonify({"error": "Missing 'text' or 'type'"}), 400
    active = data.get("active", True)
    await app.bot_statuses.update_one(
        {"text": data["text"]},
        {"$set": {"type": data["type"], "text": data["text"], "active": active}},
        upsert=True
    )
    return jsonify({"message": "Status saved successfully"}), 200

@app.route("/api/statuses", methods=["DELETE"])
async def delete_status():
    if not session.get("user_id"):
        return jsonify({"error": "Unauthorized"}), 401

    if app.bot_statuses is None:
        return jsonify({"error": "Database not connected"}), 500
    data = await request.get_json()
    if not data or "text" not in data:
        return jsonify({"error": "Missing 'text'"}), 400
    await app.bot_statuses.delete_one({"text": data["text"]})
    return jsonify({"message": "Status deleted successfully"}), 200

@app.route("/api/personalities", methods=["GET"])
async def get_personalities():
    if app.personalities is None:
        return jsonify({"error": "Database not connected"}), 500
    personalities = []
    async for personality in app.personalities.find({}, {"_id": 0}):
        personalities.append(personality)
    return jsonify(personalities), 200

@app.route("/api/personalities", methods=["POST"])
async def upsert_personality():
    if not session.get("user_id"):
        return jsonify({"error": "Unauthorized"}), 401

    if app.personalities is None:
        return jsonify({"error": "Database not connected"}), 500
    data = await request.get_json()
    if not data or "name" not in data or "prompt" not in data:
        return jsonify({"error": "Missing 'name' or 'prompt'"}), 400

    if profanity.contains_profanity(data["prompt"]):
        return jsonify({"error": "Profanity or inappropriate content detected"}), 400

    await app.personalities.update_one(
        {"name": data["name"]},
        {"$set": {"name": data["name"], "prompt": data["prompt"]}},
        upsert=True
    )
    return jsonify({"message": "Personality saved successfully"}), 200

@app.route("/api/personalities", methods=["DELETE"])
async def delete_personality():
    if not session.get("user_id"):
        return jsonify({"error": "Unauthorized"}), 401

    if app.personalities is None:
        return jsonify({"error": "Database not connected"}), 500
    data = await request.get_json()
    if not data or "name" not in data:
        return jsonify({"error": "Missing 'name'"}), 400
    await app.personalities.delete_one({"name": data["name"]})
    return jsonify({"message": "Personality deleted successfully"}), 200



@app.route("/api/user_guilds", methods=["GET"])
async def get_user_guilds():
    access_token = session.get("access_token")
    if not access_token:
        return jsonify({"error": "Unauthorized"}), 401

    if getattr(app, "bot_live_stats", None) is None:
        return jsonify({"error": "Database not connected"}), 500

    # Fetch bot stats to get connected guilds
    stats = await app.bot_live_stats.find_one({"_id": "current_stats"})
    if not stats or "discord" not in stats or "connected_server_ids" not in stats["discord"]:
        bot_guild_ids = []
    else:
        bot_guild_ids = stats["discord"]["connected_server_ids"]

    # Fetch user guilds from Discord API
    headers = {
        "Authorization": f"Bearer {access_token}"
    }

    async with aiohttp.ClientSession() as http_session:
        async with http_session.get("https://discord.com/api/users/@me/guilds", headers=headers) as resp:
            if resp.status != 200:
                return jsonify({"error": "Failed to fetch user guilds"}), 500
            user_guilds_data = await resp.json()

    # Filter guilds where user has Admin or Manage Server and bot is present
    # Permissions in Discord API: Admin = 0x8, Manage Server = 0x20
    # Bitwise AND to check permissions
    ADMIN_PERMISSION = 0x8
    MANAGE_SERVER_PERMISSION = 0x20

    valid_guilds = []
    valid_guild_ids = []
    for guild in user_guilds_data:
        permissions = int(guild.get("permissions", 0))
        is_admin = (permissions & ADMIN_PERMISSION) == ADMIN_PERMISSION
        is_manage_server = (permissions & MANAGE_SERVER_PERMISSION) == MANAGE_SERVER_PERMISSION

        if (is_admin or is_manage_server) and str(guild["id"]) in bot_guild_ids:
            valid_guilds.append({
                "id": guild["id"],
                "name": guild["name"],
                "icon": guild.get("icon")
            })
            valid_guild_ids.append(str(guild["id"]))

    # Cache valid guild ids in session for fast authorization checks
    session["valid_guild_ids"] = valid_guild_ids

    return jsonify(valid_guilds), 200

@app.route("/api/level_configs/<int:guild_id>", methods=["GET"])
async def get_level_config(guild_id):
    if not session.get("user_id"):
        return jsonify({"error": "Unauthorized"}), 401

    if str(guild_id) not in session.get("valid_guild_ids", []):
        return jsonify({"error": "Forbidden: You do not have permission to view configs for this guild."}), 403

    if not hasattr(app, "level_guild_configs"):
        if getattr(app, "db_client", None):
            level_db = app.db_client.silk_level_system
            app.level_guild_configs = level_db.guild_configs
        else:
            return jsonify({"error": "Database not connected"}), 500

    config = await app.level_guild_configs.find_one({"guild_id": guild_id}, {"_id": 0})
    if config:
        return jsonify(config), 200
    else:
        # Default config from database.py
        default_config = {
            "guild_id": guild_id,
            "text_cooldown": 60,
            "text_min_xp": 15,
            "text_max_xp": 25,
            "vc_cooldown": 60,
            "vc_xp_per_minute": 5,
            "vc_xp_enabled": True,
            "spam_channels_blacklist": [],
            "spam_min_length": 5,
            "role_rewards": {},
            "level_up_channel": None,
            "level_up_thread_id": None,
        }
        return jsonify(default_config), 200

@app.route("/api/level_configs/<int:guild_id>", methods=["POST"])
async def update_level_config(guild_id):
    if not session.get("user_id"):
        return jsonify({"error": "Unauthorized"}), 401

    if str(guild_id) not in session.get("valid_guild_ids", []):
        return jsonify({"error": "Forbidden: You do not have permission to modify configs for this guild."}), 403

    if not hasattr(app, "level_guild_configs"):
        if getattr(app, "db_client", None):
            level_db = app.db_client.silk_level_system
            app.level_guild_configs = level_db.guild_configs
        else:
            return jsonify({"error": "Database not connected"}), 500

    data = await request.get_json()
    if not data:
        return jsonify({"error": "Invalid or missing JSON payload"}), 400

    # Fields to update
    updates = {}
    if "text_cooldown" in data:
        updates["text_cooldown"] = int(data["text_cooldown"])
    if "text_min_xp" in data:
        updates["text_min_xp"] = int(data["text_min_xp"])
    if "text_max_xp" in data:
        updates["text_max_xp"] = int(data["text_max_xp"])
    if "vc_xp_enabled" in data:
        updates["vc_xp_enabled"] = bool(data["vc_xp_enabled"])
    if "vc_xp_per_minute" in data:
        updates["vc_xp_per_minute"] = int(data["vc_xp_per_minute"])

    if "role_rewards" in data:
        # Parse comma-separated string to dict
        rewards_str = data["role_rewards"].strip()
        rewards_dict = {}
        if rewards_str:
            pairs = rewards_str.split(',')
            for pair in pairs:
                try:
                    level, role_id = pair.split(':')
                    rewards_dict[str(level.strip())] = str(role_id.strip())
                except ValueError:
                    pass # Ignore invalid format
        updates["role_rewards"] = rewards_dict

    if "spam_channels_blacklist" in data:
        # Parse comma-separated string to list
        blacklist_str = data["spam_channels_blacklist"].strip()
        if blacklist_str:
            updates["spam_channels_blacklist"] = [int(cid.strip()) for cid in blacklist_str.split(',') if cid.strip().isdigit()]
        else:
            updates["spam_channels_blacklist"] = []

    if updates:
        await app.level_guild_configs.update_one(
            {"guild_id": guild_id},
            {"$set": updates},
            upsert=True
        )

    return jsonify({"message": "Level config updated successfully", "updated": updates}), 200

@app.route("/dashboard")
async def dashboard():
    user_id = session.get("user_id")
    username = session.get("username")
    access_token = session.get("access_token")

    if not user_id or not username or not access_token:
        return jsonify({"error": "Unauthorized. Please visit /login."}), 401

    if getattr(app, "bot_live_stats", None) is None:
        return jsonify({"error": "Database not connected"}), 500

    stats = await app.bot_live_stats.find_one({"_id": "current_stats"})
    if not stats or "discord" not in stats or "connected_server_ids" not in stats["discord"]:
        bot_guild_ids = []
    else:
        bot_guild_ids = stats["discord"]["connected_server_ids"]

    headers = {
        "Authorization": f"Bearer {access_token}"
    }

    async with aiohttp.ClientSession() as http_session:
        async with http_session.get("https://discord.com/api/users/@me/guilds", headers=headers) as resp:
            if resp.status != 200:
                return jsonify({"error": "Failed to fetch user guilds"}), 500
            user_guilds_data = await resp.json()

    ADMIN_PERMISSION = 0x8
    MANAGE_SERVER_PERMISSION = 0x20

    has_access = False
    for guild in user_guilds_data:
        permissions = int(guild.get("permissions", 0))
        is_admin = (permissions & ADMIN_PERMISSION) == ADMIN_PERMISSION
        is_manage_server = (permissions & MANAGE_SERVER_PERMISSION) == MANAGE_SERVER_PERMISSION

        if (is_admin or is_manage_server) and str(guild["id"]) in bot_guild_ids:
            has_access = True
            break

    if not has_access:
        return jsonify({"error": "Unauthorized. You must have Server Admin or Manage Server permissions in a server where S.I.L.K. is present."}), 403

    return await render_template("index.html", username=username)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=2160)
