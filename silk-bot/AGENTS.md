# S.I.L.K. Bot - Codebase Context & Architecture
## Project Overview
S.I.L.K. is a modular Discord bot written in Python using discord.py. It is hosted on Render as a Web Service. The codebase is strictly modular, using "Cogs" (extensions) to separate functionality into distinct domains.
## 🏗️ Architectural Standards
 * Framework: discord.py (latest version) using app_commands (Slash Commands).
 * Hosting: Render Web Service.
   * Constraint: Requires a "Keep-Alive" mechanism to prevent sleeping.
   * Solution: keep_alive.py runs a Flask server on 0.0.0.0.
   * Port: Must use os.environ.get("PORT", 8080).
 * Command Syncing:
   * Development: Commands are strictly synced to a specific test guild (GUILD_ID in .env) for instant updates.
   * Production: Global sync is currently disabled to prioritize development speed.
 * File Structure:
   * main.py: Entry point. Loads env vars, starts Flask thread, iterates cogs/ to load extensions, and syncs commands.
   * cogs/: Directory for all bot modules. New features MUST be added here as separate files.
## ⚠️ Critical Protocols (The "Render Rules")
 * The Defer Protocol:
   * Render's free tier can be slow to wake up. Discord times out interactions after 3 seconds.
   * Rule: Any command performing logic (API calls, image generation, math, database fetches) MUST start with await interaction.response.defer(thinking=True).
   * Follow-up: Once deferred, use await interaction.followup.send(...) instead of response.send_message.
 * Input Sanitization:
   * Math/Eval commands must strictly strip dangerous characters to prevent code injection.
## 🤖 Agents & Tools (Components)
1. The Core (System Orchestrator)
 * File: main.py
 * Role: Initializes the bot, manages the setup_hook for extension loading, and handles the Discord connection.
 * Key Behavior: Automatically ignores non-py files in cogs/. Syncs commands immediately to the target Guild ID upon login.
2. The Heartbeat (Uptime Agent)
 * File: keep_alive.py
 * Role: Tricks Render into treating the bot as a web service.
 * Behavior: Runs a lightweight Flask app returning "Silk is Online!". It runs on a separate daemon thread initiated by main.py.
3. Brain Module (Phase 1)
 * File: cogs/brain.py
 * Role: Handles AI intelligence, text generation, and creative writing.
 * Dependencies: google-genai (New SDK).
 * Model: gemma-3-27b-it (Selected for high daily quota).
 * Commands:
   * /idea, /roast, /whois, /summary, /define, /slang, /translate, /ship.
4. Shifo Module (Phase 2)
 * File: cogs/shifo.py
 * Role: Handles YouTube Data API integration for channel stats and promotion.
 * Dependencies: google-api-python-client.
 * Commands:
   * /stats: Displays live subscriber count, total views, and video count for ShifoLabs.
   * /latest: Fetches and links the most recent ShifoLabs video upload.
   * /shoutout [handle]: Generates a "Promo Card" embed for any YouTube channel.
5. Creative Module (Phase 3)
 * File: cogs/creative.py
 * Role: Handles external API calls for media generation and information fetching.
 * Dependencies: requests (Hugging Face), gTTS (Google Text-to-Speech), newsapi-python, io.
 * Commands:
   * /tech_news: Fetches top 3 AI/Tech headlines via NewsAPI.
   * /imagine [prompt]: Generates AI images using Stable Diffusion XL (via Hugging Face Router).
   * /voice [text]: Converts text to an MP3 file and uploads it.
6. Utilities Module (Phase 4)
 * File: cogs/utils.py
 * Role: Provides essential tools, server stats, and logic-based utilities.
 * Dependencies: qrcode, Pillow, io.
 * Commands:
   * Info: /ping (Latency), /uptime, /serverinfo, /userinfo, /avatar.
   * RNG: /roll (Dice), /flip (Coin), /choose (Pick random).
   * Tools: /calc (Safe math), /poll (Reacts with 🇦/🇧), /qr (Generates QR codes), /dm (Admin only).
7. Fun Module (Phase 5)
 * File: cogs/fun.py
 * Role: Handles text manipulation and entertainment commands.
 * Commands: /mock, /reverse, /clap, /say.
 * Convention: Pure Python string manipulation. No external APIs required.
8. Architect Module (Phase 7)
 * File: cogs/architect.py
 * Role: "Natural Language to Infrastructure" engine using AI.
 * Dependencies: google-genai (New SDK).
 * Model: gemma-3-27b-it (No native JSON mode support - uses text parsing).
 * Safety Protocol:
   * Strict 1.0 second delay between every creation/deletion action.
   * Restricted to Administrators only.
 * Commands:
   * /architect [instruction]: Creation Mode. Safely builds channels, roles, and categories. Forbidden from deleting.
   * /demolish [instruction]: Destruction Mode. Deletes specific channels/roles. Forbidden from creating.
9. Chat Module (Phase 8 - The Conversationalist)
 * File: cogs/chat.py
 * Role: Advanced, context-aware automatic chat handler.
 * Dependencies: google-genai (New SDK), collections.deque (for rate limiting).
 * Model: gemma-3-27b-it (High quota).
 * Key Features:
   * Smart Scrollback: Fetches last 20 messages.
   * Context Awareness: Formats history as [User - Name]: Msg and [Model - S.I.L.K.]: Msg so the bot remembers its own replies but ignores other bots.
   * Trigger: Responds to ALL messages in active channels (except bots/commands).
   * Rate Limiting (CRITICAL): Implements a deque bucket to enforce 30 replies per minute max.
   * Toggle: /chat_toggle [state] to enable/disable for specific channels.
## 🔮 Future Roadmap (Context for Expansion)
When generating new code, strictly adhere to these planned modules:
 * cogs/moderation.py (Phase 6 - The Judge):
   * Role: Standard server management and discipline tools.
   * Commands: /kick, /ban, /purge (clear messages), /slowmode.
   * Logic: Must enforce hierarchy checks (cannot ban users with higher roles).
   * 
