# S.I.L.K. Bot - Codebase Context & Architecture

## Project Overview
S.I.L.K. is a modular Discord bot written in Python using discord.py. It is hosted on Render as a Web Service. The codebase is strictly modular, using "Cogs" (extensions) to separate functionality into distinct domains.

## Root Configuration
* `requirements.txt`: Contains the list of Python dependencies required to run the bot.
* `.env`: (Ignored by Git) Environment variables such as `DISCORD_TOKEN`, `GEMINI_API_KEY`, `YOUTUBE_API_KEY`, `YOUTUBE_CHANNEL_ID`, `NEWS_API_KEY`, `HUGGINGFACE_TOKEN`, and `GUILD_IDS`.

## 🏗️ Architectural Standards
 * Framework: discord.py (latest version) using app_commands (Slash Commands).
 * Hosting: Render Web Service.
   * Constraint: Requires a "Keep-Alive" mechanism to prevent sleeping.
   * Solution: keep_alive.py runs a Flask server on 0.0.0.0.
   * Port: Must use os.environ.get("PORT", 8080).
 * Command Syncing:
   * Development: Commands are strictly synced to specific test guilds (comma-separated GUILD_IDS in .env) for instant updates across multiple servers.
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
   * Primary Role: Initializes the bot, manages the setup_hook for extension loading, and handles the Discord connection.
   * Files Included:
     * `main.py`: Entry point. Loads env vars, starts Flask thread, iterates cogs/ to load extensions, and syncs commands.
   * Core Logic & Features: Automatically ignores non-py files in cogs/. Iterates through the GUILD_IDS environment variable and syncs commands immediately to multiple target servers upon login.
   * Commands: None.
   * Dependencies/Configs: `discord.py`, `python-dotenv`.

2. The Heartbeat (Uptime Agent)
   * Primary Role: Tricks Render into treating the bot as a web service.
   * Files Included:
     * `keep_alive.py`: Runs a lightweight Flask app returning "Silk is Online!". It runs on a separate daemon thread initiated by main.py.
   * Core Logic & Features: Exposes a `/` route on `0.0.0.0` bound to the port specified in `PORT` or default `8080`.
   * Commands: None.
   * Dependencies/Configs: `flask`, `threading`.

3. Brain Module (Phase 1)
   * Primary Role: Handles AI intelligence, text generation, and creative writing.
   * Files Included:
     * `cogs/brain.py`: The main Cog containing general AI text commands.
   * Core Logic & Features: Sends prompts to the GenAI model with manual system prompting to simulate the S.I.L.K. persona. Enforces defer protocols and handles safety filters.
   * Commands: `/idea`, `/roast [user]`, `/whois [character]`, `/summary [text]`, `/define [word]`, `/slang [word]`, `/translate [language] [text]`, `/ship [user1] [user2]`.
   * Dependencies/Configs: `google-genai` (New SDK), model `gemma-3-27b-it`. Requires `GEMINI_API_KEY`.

4. Shifo Module (Phase 2)
   * Primary Role: Handles YouTube Data API integration for channel stats and promotion.
   * Files Included:
     * `cogs/shifo.py`: Cog for YouTube interactions.
   * Core Logic & Features: Queries the YouTube v3 API. Retrieves statistics for a specific channel ID or searches handles. Converts numeric stats to formatted integers. Executes API requests via `run_in_executor` to avoid blocking.
   * Commands:
     * `/stats`: Displays live subscriber count, total views, and video count for ShifoLabs.
     * `/latest`: Fetches and links the most recent ShifoLabs video upload.
     * `/shoutout [channel_handle]`: Generates a "Promo Card" embed for any YouTube channel.
   * Dependencies/Configs: `google-api-python-client`. Requires `YOUTUBE_API_KEY` and `YOUTUBE_CHANNEL_ID`.

5. Creative Module (Phase 3)
   * Primary Role: Handles external API calls for media generation and information fetching.
   * Files Included:
     * `cogs/creative.py`: Cog integrating text-to-speech, image generation, and news API.
   * Core Logic & Features:
     * `tech_news`: Fetches top 3 articles.
     * `imagine`: Uses Hugging Face router for Stable Diffusion XL. Returns images as byte streams (`io.BytesIO`) directly in embeds. Warns users on 503 Cold Starts.
     * `voice`: Uses gTTS to create audio buffers in memory and uploads them as discord Files.
   * Commands: `/tech_news`, `/imagine [prompt]`, `/voice [text]`.
   * Dependencies/Configs: `requests` (Hugging Face), `gTTS`, `newsapi-python`, `io`. Requires `NEWS_API_KEY` and `HUGGINGFACE_TOKEN`.

6. Utilities Module (Phase 4)
   * Primary Role: Provides essential tools, server stats, and logic-based utilities.
   * Files Included:
     * `cogs/utils.py`: Cog handling bot latency, up time, random events, polls, math, and QR generation.
   * Core Logic & Features: Evaluates basic math expressions using strict regex sanitization. Tracks bot uptime using a datetime marker on load. Uses `io.BytesIO` for QR code generation to avoid disk IO.
   * Commands:
     * Info: `/ping`, `/uptime`, `/serverinfo`, `/userinfo [member]`, `/avatar [member]`.
     * RNG: `/roll`, `/flip`, `/choose [choice1] [choice2]`.
     * Tools: `/calc [expression]`, `/poll [question] [option_a] [option_b]`, `/qr [url]`, `/dm [member] [message]` (Admin only).
   * Dependencies/Configs: `qrcode`, `Pillow`, `io`, `re`.

7. Fun Module (Phase 5)
   * Primary Role: Handles text manipulation and entertainment commands.
   * Files Included:
     * `cogs/fun.py`: Pure Python text processing utilities.
   * Core Logic & Features: Simple string manipulation functions mapping inputs to mocked case, reversed case, or inserting emojis. [span_0](start_span)Configured `/say` to act stealthily by sending an ephemeral "Message sent!" response to hide the interaction from the main chat feed, while dumping the raw text payload directly into the channel via `channel.send`[span_0](end_span).
   * Commands: `/mock [text]`, `/reverse [text]`, `/clap [text]`, `/say [text]`.
   * Dependencies/Configs: None.

8. Moderation Module (Phase 6)
   * Primary Role: Standard server management and discipline tools.
   * Files Included:
     * `cogs/moderation.py`: Cog encapsulating kick, ban, purge, and slowmode logic.
   * Core Logic & Features: Contains `check_hierarchy` to enforce Discord role hierarchies and prevent standard users/bot from punishing those with higher roles. Captures `discord.Forbidden` to provide clean errors. [span_1](start_span)Added five new optional filters to the `/purge` command (`user`, `role`, `only_users`, `only_bots`, `has_link`)[span_1](end_span). [span_2](start_span)It validates these arguments (like mutually exclusive bot/user flags) and uses `channel.purge` with a targeted check function[span_2](end_span).
   * Commands:
     * `/kick [user] [reason]`
     * `/ban [user] [reason]`
     * `/unban [user_id]` (Attempts to fetch user for display, falls back to ID)
     * `/purge [amount] [user] [role] [only_users] [only_bots] [has_link]`
     * `/slowmode [seconds]`
   * Dependencies/Configs: None.

9. Architect Module (Phase 7)
   * Primary Role: "Natural Language to Infrastructure" engine using AI.
   * Files Included:
     * `cogs/architect.py`: Interprets natural language and translates it into Discord guild structure actions.
   * Core Logic & Features: Sends current guild context (roles/channels) and user instructions to the LLM to output a JSON plan for creating or deleting structure. Uses strict 1.0s `asyncio.sleep` to prevent rate limits. Demolition is explicitly isolated from creation commands.
   * Commands:
     * `/architect [instruction]`: Creation Mode (No Deletes).
     * `/demolish [instruction]`: Destruction Mode (No Creates).
   * Dependencies/Configs: `google-genai` (New SDK), `gemma-3-27b-it`.

10. Chat Module (Phase 8)
   * Primary Role: Advanced, context-aware automatic chat handler with hot-swappable personalities and global reach.
   * Files Included:
     * `cogs/chat.py`: Main cog for auto-chat, mention, and reply interception.
     * `cogs/personalities/standard.py`: Standard personality system prompt and safety config.
     * `cogs/personalities/edgy.py`: Edgy personality system prompt and safety config.
     * `cogs/personalities/helpful.py`: Helpful personality system prompt and safety config.
   * Core Logic & Features:
     * Uses `asyncio.to_thread` for GenAI and gTTS calls to avoid blocking the event loop.
     * Voice mode converts responses to an MP3 stream using `io.BytesIO` while filtering URLs/code blocks and limiting to 500 chars.
     * Maintains a 30 RPM sliding window rate limit using a deque.
     * Retrieves conversational history (last 20 messages) and reformats it with `[Model - S.I.L.K.]` and `[User - Name]`.
     * Identifies Creator explicitly using the `(CREATOR_VERIFIED)` tag for security overrides.
   * Commands:
     * `/chat_toggle [state]`: Enable/Disable auto-chat in the current channel.
     * `/voice_mode [state]`: Enable/Disable Hybrid Voice responses in the current channel.
     * `/persona [name]`: Switch between Standard, Edgy, or Helpful.
     * `/ask-silk [question]`: Direct, server-wide command using the active persona.
   * Dependencies/Configs: `google-genai` (New SDK), `gTTS`, `io`, `collections.deque`, `re`.

11. Help Module (Phase 9)
   * Primary Role: Comprehensive, interactive dashboard system for bot documentation.
   * Files Included:
     * `cogs/help.py`: Core dashboard utilizing `discord.ui.View` for a 3-row button grid interface.
     * `cogs/help_commands/*.py`: 11 discrete files (`ai_fun.py`, `youtube.py`, `creative.py`, `utility.py`, `fun_text.py`, `moderation.py`, `architect.py`, `ai_chat.py`, `logging.py`, `roleplay.py`, `creator_note.py`). Each returns a specific `discord.Embed`.
   * Core Logic & Features: Instantiates a persistent dashboard replacing standard walls-of-text with an interactive UI. Edits the original embed when users click categorical buttons to display commands.
   * Commands:
     * `/help`: Launches the interactive dashboard.
     * `/creator-note`: A dedicated personal note/dev log from the creator.
   * Dependencies/Configs: None.

12. Presence Module (Phase 10)
   * Primary Role: Handles the bot's status, activity loops, and "Rich Presence" logic.
   * Files Included:
     * `cogs/presence.py`: Manages the dynamic rotating presence.
   * Core Logic & Features: Uses a `tasks.loop` running every 20 seconds cycling through standard statuses. Supports dynamic `{member_count}` interpolation aggregating users across all connected guilds. Uses `before_loop` to `wait_until_ready()`.
   * Commands: None.
   * Dependencies/Configs: `discord.ext.tasks`, `itertools`.

13. Logging Module (Phase 11)
   * Primary Role: Comprehensive, event-driven server surveillance and audit logging system.
   * Files Included:
     * `cogs/logger.py`: The orchestrator handling event listeners and the `setup_logs` command.
     * `cogs/logs/channels.py`, `roles.py`, `members.py`, `messages.py`, `voice.py`: Dedicated handlers that formulate the distinct color-coded embeds for specific events (Create=Green, Delete=Red, Update=Yellow).
   * Core Logic & Features:
     * Idempotent logic for the `/setup_logs` command ensuring channels/categories are only created if missing.
     * Multi-file configuration loading/saving a distinct `log_config_{guild_id}.json` file per server.
     * Actively queries `guild.audit_logs()` internally to map an event to an executor (the user who made the change).
     * Bypasses events missing a guild context (e.g., Direct Messages).
   * Commands:
     * `/setup_logs`: Master Admin command to generate the `『LOGS』` category and channels.
   * Dependencies/Configs: Dynamically generated `log_config_{guild_id}.json` files for persistent state mapping channel IDs.

14. Roleplay Module (Phase 12)
   * Primary Role: "Anime Roleplay" engine that sends animated reaction GIFs via Embeds.
   * Files Included:
     * `cogs/roleplay_commands.py`: A unified cog for expressive interactions.
   * Core Logic & Features: Centralizes 20 different actions into one `/emote` command using `app_commands.Choice`. Utilizes the `waifu.pics` API. Uses internal dictionaries to map commands to target-required/target-optional interactions, injecting users into specific flavor text strings.
   * Commands:
     * `/emote [action] [target]`: Actions include Affection (hug, kiss), Action (slap, kill), Special (bully), Emotion (smile, blush).
   * Dependencies/Configs: `aiohttp`. External API: `https://api.waifu.pics/sfw/{category}`.

15. DM Gatekeeper Module (Phase 13)
   * Primary Role: Secure, privacy-focused handler for Direct Message interactions with a strict approval system.
   * Files Included:
     * `cogs/dm_chat.py`: Controller handling DM routing, intent processing, and interactive approvals.
   * Core Logic & Features:
     * Ignores server messages. Checks if DMs originate from Approved, Pending, or Blocked lists.
     * Automatically routes unlisted users to "Pending" and pushes an interactive DM request to the hardcoded `CREATOR_ID` allowing approval or denial.
     * Overrides safety protocols via `CREATOR_ID` matching.
     * Enforces the "Helpful" personality for all AI outputs and maintains a separate 20-message `deque` history limit for each user.
   * Commands:
     * `/dm-list`: Displays ephemeral embed listing Approved, Pending, and Blocked users (Creator Only).
   * Dependencies/Configs: Requires `dm_config.json` for persistence and `google-genai`.

16. Task Agent Module (Phase 14)
   * Primary Role: Intercepts direct mentions to analyze and execute complex tasks (e.g., creating embeds, parsing structured data) based on user instructions.
   * Files Included:
     * `cogs/task_agent.py`: Controller identifying and processing instructional messages.
   * Core Logic & Features:
     * Evaluates messages targeting the bot with an initial GenAI call to classify them as "TASK" or "CHAT". [span_3](start_span)Tweaked LLM system prompts so the bot strictly triggers on explicitly stated tasks, avoiding casual chat[span_3](end_span). If a TASK, blocks default chat processing.
     * Offers an interactive UI (`TaskConfirmView`) to confirm the execution of the task. [span_4](start_span)Appended the `message.content` context into the confirmation prompts and "waiting" state[span_4](end_span).
     * Secondary GenAI call produces structural output (e.g. JSON strings), falling back to raw text if parsing fails. [span_5](start_span)Set the default response type to raw text instead of forcing embeds, except when explicitly asked (e.g. polls, embeds)[span_5](end_span).
   * Commands: None explicitly, triggers automatically on mentions based on context.
   * Dependencies/Configs: `google-genai`.

## 🔮 Future Roadmap (Context for Expansion)
Currently Empty. S.I.L.K. is functionally complete.
