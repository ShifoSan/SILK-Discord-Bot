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
    app.custom_commands = app.db.custom_commands

    app.level_db = app.db_client.silk_level_system
    app.level_configs = app.level_db.guild_configs

@app.after_serving
async def close_db():
    if app.db_client:
        app.db_client.close()

def is_authorized(guild_id):
    """
    Check if the user is authenticated and authorized for a specific guild.
    Returns (True, None) if authorized, (False, error_response) otherwise.
    """
    if not session.get("user_id"):
        return False, (jsonify({"error": "Unauthorized"}), 401)

    authorized_guilds = session.get("authorized_guilds", [])
    # guild_id from URL is int, g['id'] from Discord API is string
    if not any(g.get("id") == str(guild_id) for g in authorized_guilds):
        return False, (jsonify({"error": "Forbidden"}), 403)

    return True, None

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
    authorized, response = is_authorized(guild_id)
    if not authorized:
        return response

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
    authorized, response = is_authorized(guild_id)
    if not authorized:
        return response

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



@app.route("/api/level_configs/<int:guild_id>", methods=["GET"])
async def get_level_config(guild_id):
    authorized, response = is_authorized(guild_id)
    if not authorized:
        return response

    if getattr(app, "level_configs", None) is None:
        return jsonify({"error": "Database not connected"}), 500

    config = await app.level_configs.find_one({"guild_id": guild_id}, {"_id": 0})
    if config:
        # Remove _id
        config.pop("_id", None)
        return jsonify(config), 200
    else:
        # Default config
        default = {
            "text_min_xp": 15,
            "text_max_xp": 25,
            "text_cooldown": 60,
            "vc_xp_per_minute": 5,
            "vc_xp_enabled": True
        }
        return jsonify(default), 200

@app.route("/api/level_configs/<int:guild_id>", methods=["POST"])
async def update_level_config(guild_id):
    authorized, response = is_authorized(guild_id)
    if not authorized:
        return response

    if getattr(app, "level_configs", None) is None:
        return jsonify({"error": "Database not connected"}), 500

    data = await request.get_json()
    if not data:
        return jsonify({"error": "Invalid JSON payload"}), 400

    update_data = {}

    if "text_min_xp" in data:
        update_data["text_min_xp"] = data["text_min_xp"]
    if "text_max_xp" in data:
        update_data["text_max_xp"] = data["text_max_xp"]
    if "text_cooldown" in data:
        update_data["text_cooldown"] = data["text_cooldown"]
    if "vc_xp_per_minute" in data:
        update_data["vc_xp_per_minute"] = data["vc_xp_per_minute"]
    if "vc_xp_enabled" in data:
        update_data["vc_xp_enabled"] = data["vc_xp_enabled"]

    if update_data:
        await app.level_configs.update_one(
            {"guild_id": guild_id},
            {"$set": update_data},
            upsert=True
        )

    return jsonify({"message": "Leveling configuration updated successfully", "updated": update_data}), 200


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

        # Fetch user guilds
        async with http_session.get("https://discord.com/api/users/@me/guilds", headers=user_headers) as resp:
            if resp.status != 200:
                return jsonify({"error": "Failed to fetch user guilds"}), 500
            user_guilds = await resp.json()

    # Check permissions
    # Fetch bot's connected guilds from db
    stats = await app.bot_live_stats.find_one({"_id": "current_stats"})
    bot_connected_guilds = []
    if stats and "discord" in stats:
        bot_connected_guilds = stats["discord"].get("connected_server_ids", [])

    is_authorized = False
    authorized_guilds = []
    for g in user_guilds:
        # Check if bot is in this guild and user has Admin (0x8) or Manage Server (0x20)
        perms = int(g.get("permissions", 0))
        if int(g["id"]) in bot_connected_guilds and (perms & 0x8 or perms & 0x20):
            is_authorized = True
            authorized_guilds.append({"id": g["id"], "name": g["name"]})

    if not is_authorized:
        return jsonify({"error": "Unauthorized. You must have Server Admin or Manage Server permissions in a server where S.I.L.K. is present."}), 403

    # Store user in session
    session["user_id"] = user_data.get("id")
    session["username"] = user_data.get("username")
    session["authorized_guilds"] = authorized_guilds

    return redirect("/dashboard")

@app.route("/api/user_guilds", methods=["GET"])
async def get_user_guilds():
    if not session.get("user_id"):
        return jsonify({"error": "Unauthorized"}), 401
    return jsonify(session.get("authorized_guilds", [])), 200

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
        return jsonify({"error": "Prompt contains explicit or inappropriate material and cannot be saved."}), 400

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



@app.route("/api/custom_commands/<int:guild_id>", methods=["GET"])
async def get_custom_commands(guild_id):
    if not session.get("user_id"):
        return jsonify({"error": "Unauthorized"}), 401

    if getattr(app, "custom_commands", None) is None:
        return jsonify({"error": "Database not connected"}), 500

    commands = []
    async for cmd in app.custom_commands.find({"guild_id": guild_id}, {"_id": 0}):
        commands.append(cmd)

    return jsonify(commands), 200

@app.route("/api/custom_commands/<int:guild_id>", methods=["POST"])
async def upsert_custom_command(guild_id):
    if not session.get("user_id"):
        return jsonify({"error": "Unauthorized"}), 401

    if getattr(app, "custom_commands", None) is None:
        return jsonify({"error": "Database not connected"}), 500

    data = await request.get_json()
    if not data or "trigger" not in data or "response" not in data:
        return jsonify({"error": "Missing 'trigger' or 'response'"}), 400

    reply_directly = data.get("reply_directly", False)

    await app.custom_commands.update_one(
        {"guild_id": guild_id, "trigger": data["trigger"]},
        {"$set": {
            "guild_id": guild_id,
            "trigger": data["trigger"],
            "response": data["response"],
            "reply_directly": reply_directly
        }},
        upsert=True
    )
    return jsonify({"message": "Custom command saved successfully"}), 200

@app.route("/api/custom_commands/<int:guild_id>", methods=["DELETE"])
async def delete_custom_command(guild_id):
    if not session.get("user_id"):
        return jsonify({"error": "Unauthorized"}), 401

    if getattr(app, "custom_commands", None) is None:
        return jsonify({"error": "Database not connected"}), 500

    data = await request.get_json()
    if not data or "trigger" not in data:
        return jsonify({"error": "Missing 'trigger'"}), 400

    await app.custom_commands.delete_one({"guild_id": guild_id, "trigger": data["trigger"]})
    return jsonify({"message": "Custom command deleted successfully"}), 200


@app.route("/dashboard")
async def dashboard():
    return redirect("/dashboard/overview")

@app.route("/dashboard/overview")
async def dashboard_overview():
    user_id = session.get("user_id")
    username = session.get("username")

    if user_id and username:
        return await render_template("overview.html", username=username, active_page="overview")
    else:
        return jsonify({"error": "Unauthorized. Please visit /login."}), 401

@app.route("/dashboard/modules")
async def dashboard_modules():
    user_id = session.get("user_id")
    username = session.get("username")

    if user_id and username:
        return await render_template("modules.html", username=username, active_page="modules")
    else:
        return jsonify({"error": "Unauthorized. Please visit /login."}), 401

@app.route("/dashboard/settings")
async def dashboard_settings():
    user_id = session.get("user_id")
    username = session.get("username")

    if user_id and username:
        return await render_template("settings.html", username=username, active_page="settings")
    else:
        return jsonify({"error": "Unauthorized. Please visit /login."}), 401

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=2160)
