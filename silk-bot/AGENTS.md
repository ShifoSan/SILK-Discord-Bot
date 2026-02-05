# S.I.L.K. Bot - Codebase Context & Architecture

## Project Overview
S.I.L.K. is a modular Discord bot written in Python using `discord.py`. It is hosted on Render as a Web Service. The codebase is strictly modular, using "Cogs" (extensions) to separate functionality into distinct domains.

## 🏗️ Architectural Standards
* **Framework:** `discord.py` (latest version) using `app_commands` (Slash Commands).
* **Hosting:** Render Web Service.
    * **Constraint:** Requires a "Keep-Alive" mechanism to prevent sleeping.
    * **Solution:** `keep_alive.py` runs a Flask server on `0.0.0.0`.
    * **Port:** Must use `os.environ.get("PORT", 8080)`.
* **Command Syncing:**
    * **Development:** Commands are strictly synced to a specific test guild (`GUILD_ID` in .env) for instant updates.
    * **Production:** Global sync is currently disabled to prioritize development speed.
* **File Structure:**
    * `main.py`: Entry point. Loads env vars, starts Flask thread, iterates `cogs/` to load extensions, and syncs commands.
    * `cogs/`: Directory for all bot modules. New features MUST be added here as separate files.

## 🤖 Agents & Tools (Components)

### 1. The Core (System Orchestrator)
* **File:** `main.py`
* **Role:** Initializes the bot, manages the `setup_hook` for extension loading, and handles the Discord connection.
* **Key Behavior:** Automatically ignores non-py files in `cogs/`. Syncs commands immediately to the target Guild ID upon login.

### 2. The Heartbeat (Uptime Agent)
* **File:** `keep_alive.py`
* **Role:** Tricks Render into treating the bot as a web service.
* **Behavior:** Runs a lightweight Flask app returning "Silk is Online!". It runs on a separate daemon thread initiated by `main.py`.

### 3. Fun Module (Text Processor)
* **File:** `cogs/fun.py` (Phase 5)
* **Role:** Handles text manipulation and entertainment commands.
* **Commands:** `/mock`, `/reverse`, `/clap`, `/say`.
* **Convention:** Pure Python string manipulation. No external APIs required.

## 🔮 Future Roadmap (Context for Expansion)
When generating new code, strictly adhere to these planned modules:
* **`cogs/brain.py` (Phase 1):** Will handle Google Gemini 3 integration (AI Chat).
* **`cogs/shifo.py` (Phase 2):** Will handle YouTube Data API v3 integration.
* **`cogs/creative.py` (Phase 3):** Will handle Media generation (Hugging Face / NewsAPI).
* **`cogs/utils.py` (Phase 4):** Will handle Utilities (Ping, Math, Embeds).
* **`cogs/moderation.py` (Phase 6):** Will handle Admin tools.
* 
