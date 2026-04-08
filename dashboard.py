import os
import secrets
from quart import Quart, request, jsonify
from dotenv import load_dotenv
import motor.motor_asyncio
import certifi

# Load environment variables
load_dotenv()

app = Quart(__name__)

# Configure Secret Key
app.secret_key = os.getenv("QUART_SECRET_KEY") or secrets.token_hex(24)

# Database Setup
MONGO_URI = os.getenv("MONGO_URI")
if not MONGO_URI:
    print("Warning: MONGO_URI not found in .env file.")

@app.before_serving
async def setup_db():
    if MONGO_URI:
        app.db_client = motor.motor_asyncio.AsyncIOMotorClient(MONGO_URI, tlsCAFile=certifi.where())
        app.db = app.db_client.silk_bot
        app.chat_configs = app.db.chat_configs
    else:
        app.db_client = None
        app.chat_configs = None

@app.after_serving
async def close_db():
    if app.db_client:
        app.db_client.close()

# --- API Routes ---

@app.route("/api/chat_configs/<int:guild_id>", methods=["GET"])
async def get_chat_config(guild_id):
    if not app.chat_configs:
        return jsonify({"error": "Database not connected"}), 500

    config = await app.chat_configs.find_one({"channel_id": guild_id}, {"_id": 0})
    if config:
        return jsonify(config), 200
    else:
        # Return default if not found
        return jsonify({"channel_id": guild_id, "enabled": False, "language": "English"}), 200

@app.route("/api/chat_configs/<int:guild_id>", methods=["POST"])
async def update_chat_config(guild_id):
    if not app.chat_configs:
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


# --- OAuth Placeholder Routes ---

@app.route("/login")
async def login():
    return jsonify({"status": "Under construction", "route": "login"}), 200

@app.route("/callback")
async def callback():
    return jsonify({"status": "Under construction", "route": "callback"}), 200

@app.route("/dashboard")
async def dashboard():
    return jsonify({"status": "Under construction", "route": "dashboard"}), 200

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080)
