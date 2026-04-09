import os
import secrets
from quart import Quart, request, jsonify, session, redirect, render_template
from dotenv import load_dotenv
import motor.motor_asyncio
import certifi
import urllib.request
import urllib.parse
import aiohttp
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

@app.after_serving
async def close_db():
    if app.db_client:
        app.db_client.close()

# --- API Routes ---

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



@app.route("/dashboard")
async def dashboard():
    user_id = session.get("user_id")
    username = session.get("username")

    if user_id and username:
        return await render_template("index.html", username=username)
    else:
        return jsonify({"error": "Unauthorized. Please visit /login."}), 401

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=2160)
