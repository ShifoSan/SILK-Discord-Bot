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
   * cogs/personalities/: Directory for personality configuration modules (Standard, Edgy, Helpful).
   * cogs/help_commands/: Directory for individual help embed modules (Phase 9).
   * cogs/logs/: Directory for logging logic modules (Phase 11).
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
8. Moderation Module (Phase 6)
 * File: cogs/moderation.py
 * Role: Standard server management and discipline tools.
 * Commands:
   * /kick [user] [reason]: Removes a user from the server.
   * /ban [user] [reason]: Bans a user permanently.
   * /unban [user_id]: Unbans a user by ID.
   * /purge [amount]: Bulk deletes messages in the current channel.
   * /slowmode [seconds]: Sets the channel slowmode delay.
 * Logic: Enforces hierarchy checks (cannot punish users with roles higher than the bot).
9. Architect Module (Phase 7)
 * File: cogs/architect.py
 * Role: "Natural Language to Infrastructure" engine using AI.
 * Dependencies: google-genai (New SDK).
 * Model: gemma-3-27b-it (Uses text parsing).
 * Safety Protocol:
   * Strict 1.0 second delay between every creation/deletion action.
   * Restricted to Administrators only.
 * Commands:
   * /architect [instruction]: Creation Mode (No Deletes).
   * /demolish [instruction]: Destruction Mode (No Creates).
10. Chat Module (Phase 8)
 * File: cogs/chat.py
 * Sub-Modules: cogs/personalities/ (standard.py, edgy.py, helpful.py)
 * Role: Advanced, context-aware automatic chat handler with hot-swappable personalities and global reach.
 * Dependencies: google-genai (New SDK), collections.deque, asyncio, gTTS, io, re.
 * Model: gemma-3-27b-it (High quota).
 * Commands:
   * /chat_toggle [state]: Enable/Disable auto-chat in the current channel.
   * /voice_mode [state]: Enable/Disable Hybrid Voice responses in the current channel.
   * /persona [name]: Switch between "Standard", "Edgy", or "Helpful" modes (Admin/Manage Messages only).
   * /ask-silk [question]: Direct, server-wide command to ask S.I.L.K. a question using the current persona.
 * Key Features:
   * Global Reach Triggers: Responds server-wide (even outside active channels) if the bot is Mentioned (@S.I.L.K.) or Replied to.
   * Hybrid Voice Engine: When enabled via `/voice_mode`, responses include both Text and an attached MP3 audio file.
     * Performance: Uses `io.BytesIO` for in-memory file handling (no disk writes).
     * Async: Audio generation is threaded (`asyncio.to_thread`) to prevent blocking.
     * Sanitization: Strips URLs and Code Blocks from the audio stream to ensure listening quality.
     * Limits: Truncates audio input to 500 characters to prevent massive file uploads.
   * Persona Consistency: All triggers (Auto-chat, Mentions, Replies, /ask-silk) strictly use the currently active personality.
   * Personality Engine: Dynamically loads System Instructions and Safety Settings from `cogs/personalities/`.
   * Asynchronous Core: Uses `asyncio.to_thread` for API calls to eliminate bot lag and freezing during generation.
   * Creator Protocol (Security): Hardcoded User ID verification identifies the Creator. Supports "Manual Override" to bypass personality/refusal constraints.
   * Smart Scrollback: Fetches last 20 messages for Auto-Chat, Mentions, and Replies to maintain context.
   * Full Context: No character truncation limit on input text messages (leverages 1M token window).
   * Rate Limiting: 30 RPM (deque bucket) plus a 1.5s artificial delay per message for anti-spam safety.
   * Error Handling: Detects safety blockages and informs the user instead of failing silently.
11. Help Module (Phase 9)
 * File: cogs/help.py
 * Sub-Modules: cogs/help_commands/ (ai_fun.py, youtube.py, creative.py, utility.py, fun_text.py, moderation.py, architect.py, ai_chat.py, creator.py)
 * Role: Comprehensive, modular help system providing visual manuals for all bot functions.
 * Commands:
   * /quick-ai: Displays help for AI Fun tools (Brain Module).
   * /yt-explain: Displays help for YouTube tools (Shifo Module).
   * /vision-help: Displays help for Creative/Vision tools.
   * /utility-help: Displays help for Utility tools.
   * /text-help: Displays help for Text Fun tools.
   * /staff-mod-help: Displays help for Moderation tools.
   * /server-build-help: Displays help for Architect tools.
   * /ai-chat-help: Displays help for the AI Chat system and Personalities.
   * /shifo-info: Displays the Creator's profile and social links.
   * /help: Master command that retrieves and sends ALL help embeds listed above.
12. Presence Module (Phase 10)
 * File: cogs/presence.py
 * Role: Handles the bot's status, activity loops, and "Rich Presence" logic.
 * Dependencies: discord.ext.tasks, itertools.
 * Key Features:
   * Rotating Status: Cycles through Assassin-themed activities (Watching, Playing, Listening) every 20 seconds.
   * Dynamic Watching: Updates the "Watching [X] users" status in real-time based on total guild members.
   * Startup Safety: Uses wait_until_ready() to prevent race conditions during boot.
   * Non-Blocking: Runs on an asynchronous loop separate from the main thread.
13. Logging Module (Phase 11)
 * File: cogs/logger.py
 * Sub-Modules: cogs/logs/ (channels.py, roles.py, members.py, messages.py, voice.py)
 * Role: Comprehensive, event-driven server surveillance and audit logging system.
 * Dependencies: log_config.json (Runtime persistence).
 * Commands:
   * /setup_logs: Master Admin command. Auto-creates "『LOGS』" category and 6 specific channels (#📊-channel-logs, etc.).
     * Idempotent Logic: Checks for existing channels/categories before creation to prevent duplicates after restarts.
 * Key Features:
   * Visual Coding: Distinct color-coded Embeds for Creates (Green), Deletes (Red), and Updates (Yellow).
   * Audit Intelligence: Automatically fetches `guild.audit_logs` to identify *who* performed an action (e.g., who deleted a channel) instead of just reporting the event.
   * Granular Tracking:
     * Messages: Logs Edits (Before/After text) and Deletes.
     * Members: Logs Nickname changes (checks Audit Log for perpetrator).
     * Voice: Logs Joins, Leaves, and Moves.
     * Infrastructure: Logs Channel/Role creation, deletion, and permission updates.
   * Security: Log channels are automatically set to private (`view_channel=False` for @everyone).
   * Performance: Event-driven architecture ensures zero CPU usage when idle.
## 🔮 Future Roadmap (Context for Expansion)
Currently Empty. S.I.L.K. is functionally complete.
