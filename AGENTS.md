# S.I.L.K. Bot - Codebase Context & Architecture

## Project Overview
S.I.L.K. is a modular Discord bot written in Python using discord.py. It is currently hosted on HeavenCloud to bypass shared-IP Cloudflare bans from Discord. The codebase is strictly modular, using "Cogs" (extensions) to separate functionality into distinct domains.

## Root Configuration
* `requirements.txt`: Contains the list of Python dependencies required to run the bot.
* `.env`: (Ignored by Git) Environment variables such as `DISCORD_TOKEN`, `GEMINI_API_KEY`, `HUGGINGFACE_TOKEN`, `MONGO_URI`, `CONFIG_PASS`, `QUART_SECRET_KEY`, `DISCORD_CLIENT_ID`, `DISCORD_CLIENT_SECRET`, and `DISCORD_REDIRECT_URI`.

## 🏗️ Architectural Standards
 * Framework: discord.py (latest version) using app_commands (Slash Commands).
 * Hosting: HeavenCloud (Temporary Environment).
   * Constraint: Background sleeping or restarts handled by HeavenCloud's free tier. 
 * Command Syncing:
   * Strategy: Auto-syncing on boot is strictly disabled to prevent 1015 IP bans. 
   * Execution: Command registration is handled manually by the bot owner using the `!sync` command, which slowly pushes updates to all servers to respect rate limits.
 * File Structure:
   * launcher.py: The master entry point used by the hosting panel to concurrently launch both the bot and the web dashboard.
   * main.py: Bot entry point. Loads env vars, iterates cogs/ to load extensions, and handles the Discord connection.
   * dashboard.py: Async web server entry point (Quart).
   * templates/index.html: Frontend UI for the web dashboard built with Tailwind CSS.
   * cogs/: Directory for all bot modules. New features MUST be added here as separate files.
   * cogs/help_commands/: Directory for individual help embed modules (Phase 9).
   * cogs/logs/: Directory for logging logic modules (Phase 11).

## ⚠️ Critical Protocols
 * The Defer Protocol:
   * Free tier hosts can be slow to wake up or execute logic. Discord times out interactions after 3 seconds.
   * Rule: Any command performing logic (API calls, image generation, math, database fetches) MUST start with `await interaction.response.defer(thinking=True)` instantly to prevent `10062: Unknown interaction` errors.
   * Follow-up: Once deferred, use `await interaction.followup.send(...)` or `await interaction.message.edit(...)`.
 * Sync Throttling (Anti-Ban):
   * Discord strictly rate-limits slash command syncing. Syncing multiple servers back-to-back immediately on boot triggers a Cloudflare IP ban (Error 1015).
   * Rule: The manual `!sync` command explicitly uses an `asyncio.sleep(5.0)` delay between iterations when looping through `bot.guilds`.
 * Input Sanitization:
   * Math/Eval commands must strictly strip dangerous characters to prevent code injection.

## 🤖 Agents & Tools (Components)

1. The Core (System Orchestrator)
   * Primary Role: Initializes the bot, manages the setup_hook for extension loading, and handles the Discord connection.
   * Files Included:
     * `main.py`: Entry point. Loads env vars, connects to Discord, and provides the manual syncing tool.
   * Core Logic & Features: Automatically ignores non-py files in cogs/. Bypasses auto-syncing during `setup_hook`. Provides a safe, owner-only manual sync tool to update commands across all servers via a controlled loop.
   * Commands: `!sync` (Owner only, loops through all guilds with a 5-second cooldown).
   * Dependencies/Configs: `discord.py`, `python-dotenv`, `asyncio`.

2. Brain Module (Phase 1)
   * Primary Role: Handles AI intelligence, text generation, and creative writing.
   * Files Included:
     * `cogs/brain.py`: The main Cog containing general AI text commands.
   * Core Logic & Features: Sends prompts to the GenAI model with manual system prompting to simulate the S.I.L.K. persona. Enforces defer protocols and handles safety filters.
   * Commands: `/roast [user]`, `/translate [language] [text]`.
   * Dependencies/Configs: `google-genai` (New SDK), model `gemma-3-27b-it`. Requires `GEMINI_API_KEY`.

3. Creative Module (Phase 3)
   * Primary Role: Handles external API calls for media generation and information fetching.
   * Files Included:
     * `cogs/creative.py`: Cog integrating text-to-speech and image generation.
   * Core Logic & Features:
     * `imagine`: Uses the updated Hugging Face router endpoint (`router.huggingface.co`) for the `FLUX.1-schnell` model to avoid deprecation errors and speed up generation. Returns images as byte streams (`io.BytesIO`) directly in embeds. Warns users on 503 Cold Starts.
     * `voice`: Uses gTTS to create audio buffers in memory and uploads them as discord Files.
   * Commands: `/imagine [prompt]`, `/voice [text]`.
   * Dependencies/Configs: `requests` (Hugging Face), `gTTS`, `io`. Requires `HUGGINGFACE_TOKEN`.

4. Utilities Module (Phase 4)
   * Primary Role: Provides essential tools, server stats, and logic-based utilities.
   * Files Included:
     * `cogs/utils.py`: Cog handling bot latency, up time, random events, polls, math, and QR generation.
   * Core Logic & Features: Tracks bot uptime using a datetime marker on load. Uses `io.BytesIO` for QR code generation to avoid disk IO.
   * Commands:
     * Info: `/ping`, `/uptime`, `/serverinfo`, `/userinfo [member]`, `/avatar [member]`.
     * RNG: `/roll`, `/choose [choice1] [choice2]`.
     * Tools: `/poll [question] [option_a] [option_b]`, `/qr [url]`, `/dm [member] [message]` (Admin only).
   * Dependencies/Configs: `qrcode`, `Pillow`, `io`, `re`.

5. Fun Module (Phase 5)
   * Primary Role: Handles text manipulation and entertainment commands.
   * Files Included:
     * `cogs/fun.py`: Pure Python text processing utilities.
   * Core Logic & Features: Configured `/say` to act stealthily by sending an ephemeral "Message sent!" response to hide the interaction from the main chat feed, while dumping the raw text payload directly into the channel via `channel.send`.
   * Commands: `/say [text]`.
   * Dependencies/Configs: None.

6. Moderation Module (Phase 6)
   * Primary Role: Standard server management and discipline tools.
   * Files Included:
     * `cogs/moderation.py`: Cog encapsulating kick, ban, purge, and slowmode logic.
   * Core Logic & Features: Contains `check_hierarchy` to enforce Discord role hierarchies and prevent standard users/bot from punishing those with higher roles. Captures `discord.Forbidden` to provide clean errors. Added five new optional filters to the `/purge` command (`user`, `role`, `only_users`, `only_bots`, `has_link`). It validates these arguments (like mutually exclusive bot/user flags) and uses `channel.purge` with a targeted check function.
   * Commands:
     * `/kick [user] [reason]`
     * `/ban [user] [reason]`
     * `/unban [user_id]` (Attempts to fetch user for display, falls back to ID)
     * `/purge [amount] [user] [role] [only_users] [only_bots] [has_link]`
     * `/slowmode [seconds]`
   * Dependencies/Configs: None.

7. Architect Module (Phase 7)
   * Primary Role: "Natural Language to Infrastructure" engine using AI.
   * Files Included:
     * `cogs/architect.py`: Interprets natural language and translates it into Discord guild structure actions.
   * Core Logic & Features: Sends current guild context (roles/channels) and user instructions to the LLM to output a JSON plan for creating or deleting structure. Uses strict 1.0s `asyncio.sleep` to prevent rate limits. Demolition is explicitly isolated from creation commands.
   * Commands:
     * `/architect [instruction]`: Creation Mode (No Deletes).
     * `/demolish [instruction]`: Destruction Mode (No Creates).
   * Dependencies/Configs: `google-genai` (New SDK), `gemma-3-27b-it`.

8. Chat Module (Phase 8)
   * Primary Role: Advanced, context-aware automatic chat handler with hot-swappable personalities, multi-language support, and global reach.
   * Files Included:
     * `cogs/chat.py`: Main cog for auto-chat, mention, and reply interception.
   * Core Logic & Features:
     * Uses `asyncio.to_thread` for GenAI and gTTS calls to avoid blocking the event loop.
     * Voice mode converts responses to an MP3 stream using `io.BytesIO` while filtering URLs/code blocks and limiting to 500 chars.
     * Maintains a 30 RPM sliding window rate limit using a deque.
     * Retrieves conversational history (last 20 messages) and reformats it with `[Model - S.I.L.K.]` and `[User - Name]`.
     * Identifies Creator explicitly using the `(CREATOR_VERIFIED)` tag for security overrides.
     * Stores persistent auto-chat configurations (enabled state and language) in a MongoDB `chat_configs` collection.
     * Dynamically fetches the active system prompt from the `personalities` MongoDB collection based on the selected persona.
     * Multi-Language Routing: If 'Hindi' is selected, automatically shifts to `gemini-3.1-flash-lite-preview` using a dedicated Hinglish casual persona prompt. English defaults to `gemma-3-27b-it`.
   * Commands:
     * `/chat_toggle [state] [language]`: Enable/Disable auto-chat in the current channel and optionally set the language (English/Hindi).
     * `/voice_mode [state]`: Enable/Disable Hybrid Voice responses in the current channel.
     * `/persona [name]`: Switch between personalities (uses an autocomplete dropdown querying the database).
   * Dependencies/Configs: `google-genai` (New SDK), `gTTS`, `io`, `collections.deque`, `re`, `motor`.

9. Help Module (Phase 9)
   * Primary Role: Comprehensive, interactive dashboard system for bot documentation.
   * Files Included:
     * `cogs/help.py`: Core dashboard utilizing `discord.ui.View` for a 3-row button grid interface.
     * `cogs/help_commands/*.py`: 11 discrete files (`ai_fun.py`, `creative.py`, `utility.py`, `fun_text.py`, `moderation.py`, `architect.py`, `ai_chat.py`, `logging.py`, `roleplay.py`, `creator_note.py`, `leveling.py`). Each returns a specific `discord.Embed`.
   * Core Logic & Features: Instantiates a persistent dashboard replacing standard walls-of-text with an interactive UI. Edits the original embed when users click categorical buttons to display commands.
   * Commands:
     * `/help`: Launches the interactive dashboard.
     * `/creator-note`: A dedicated personal note/dev log from the creator.
   * Dependencies/Configs: None.

10. Presence Module (Phase 10)
   * Primary Role: Handles the bot's status, activity loops, and "Rich Presence" logic.
   * Files Included:
     * `cogs/presence.py`: Manages the dynamic rotating presence.
   * Core Logic & Features: Uses a `tasks.loop` running every 20 seconds. It fetches active statuses dynamically from the `bot_statuses` MongoDB collection and randomly selects one. Supports dynamic `{member_count}` interpolation aggregating users across all connected guilds. Uses `before_loop` to `wait_until_ready()`.
   * Commands: None.
   * Dependencies/Configs: `discord.ext.tasks`, `motor`.

11. Logging Module (Phase 11)
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

12. Roleplay Module (Phase 12)
   * Primary Role: "Anime Roleplay" engine that sends animated reaction GIFs via Embeds.
   * Files Included:
     * `cogs/roleplay_commands.py`: A unified cog for expressive interactions.
   * Core Logic & Features: Centralizes 20 different actions into one `/emote` command using `app_commands.Choice`. Utilizes the `waifu.pics` API. Uses internal dictionaries to map commands to target-required/target-optional interactions, injecting users into specific flavor text strings.
   * Commands:
     * `/emote [action] [target]`: Actions include Affection (hug, kiss), Action (slap, kill), Special (bully), Emotion (smile, blush).
   * Dependencies/Configs: `aiohttp`. External API: `https://api.waifu.pics/sfw/{category}`.

13. DM Gatekeeper Module (Phase 13)
   * Primary Role: Secure, privacy-focused handler for Direct Message interactions with a strict approval system.
   * Files Included:
     * `cogs/dm_chat.py`: Controller handling DM routing, intent processing, and interactive approvals.
   * Core Logic & Features:
     * Ignores server messages. Checks if DMs originate from Approved, Pending, or Blocked lists.
     * Automatically routes unlisted users to "Pending" and pushes an interactive DM request to the hardcoded `CREATOR_ID` allowing approval or denial.
     * Overrides safety protocols via `CREATOR_ID` matching.
     * Enforces the "Helpful" personality for all AI outputs by dynamically fetching its prompt from the MongoDB `personalities` collection, and maintains a separate 20-message `deque` history limit for each user.
   * Commands:
     * `/dm-list`: Displays ephemeral embed listing Approved, Pending, and Blocked users (Creator Only).
   * Dependencies/Configs: Requires `dm_config.json` for persistence, `google-genai`, `motor`.

14. Task Agent Module (Phase 14)
   * Primary Role: Intercepts direct mentions to analyze and execute complex tasks (e.g., creating embeds, parsing structured data) based on user instructions.
   * Files Included:
     * `cogs/task_agent.py`: Controller identifying and processing instructional messages.
   * Core Logic & Features:
     * Evaluates messages targeting the bot with an initial GenAI call to classify them as "TASK" or "CHAT". Tweaked LLM system prompts so the bot strictly triggers on explicitly stated tasks, avoiding casual chat. If a TASK, blocks default chat processing.
     * Offers an interactive UI (`TaskConfirmView`) to confirm the execution of the task. Appended the `message.content` context into the confirmation prompts and "waiting" state.
     * Secondary GenAI call produces structural output (e.g. JSON strings), falling back to raw text if parsing fails. Set the default response type to raw text instead of forcing embeds, except when explicitly asked (e.g. polls, embeds).
   * Commands: None explicitly, triggers automatically on mentions based on context.
   * Dependencies/Configs: `google-genai`.

15. Level System Module (Phase 15)
   * Primary Role: Advanced XP and leveling system tracking messages, reactions, and voice activity with a robust UI dashboard.
   * Files Included:
     * `cogs/level_system/core.py`: Main cog loading the configurations and handling `on_message`, `on_raw_reaction_add`, `on_voice_state_update`, and join/leave logic. Supports WebP image attachments for fast level-up notifications.
     * `cogs/level_system/database.py`: Asynchronous MongoDB connector for saving/retrieving user progress and server configs. (Uses `certifi` to force updated SSL certs on server hosts).
     * `cogs/level_system/commands.py`: Houses the user-facing slash commands (`/rank`, `/leaderboard`, `/bot_config`). Offloads avatar resizing to Discord's CDN to prevent blocking and gracefully catches `discord.NotFound` errors if a user deletes the thinking message.
     * `cogs/level_system/image_gen.py`: Pillow-based generator drawing dynamic rank cards. Implements RAM caching for `banner.png` and fonts to eliminate disk I/O bottlenecks. Optimizes generation using `BILINEAR` resampling and outputs as highly compressed `WebP` buffers.
     * `cogs/level_system/ai_responses.py`: Isolated GenAI connector generating personalized level-up messages via `gemma-3-27b-it`.
     * `cogs/level_system/bot_config/`: Sub-directory containing interactive configuration UI components (`main_menu.py`, `role_rewards.py`, `xp_management.py`, `vc_settings.py`, `spam_filters.py`, `cooldown_settings.py`). 
   * Core Logic & Features:
     * Dynamic math using a quadratic curve `5*(level^2) + 50*level + 100` for leveling. Tracks exact true level dynamically based on total XP.
     * Soft data retention tracking `in_server` status to preserve leaving users' progress without cluttering leaderboards.
     * Dynamic Configuration UI: Utilizes `discord.ui.Button` triggers launching `discord.ui.Modal` with text inputs to allow for arbitrary integer configurations (custom XP values, custom cooldowns, mapped role rewards, deletion of role rewards). Views use an extended 10-minute timeout. UI components strictly manage row widths to avoid Discord limits.
     * Dedicated AI Channel & Thread Routing: Administrators can designate a specific `level_up_channel` via a Channel Select menu and explicitly set a `level_up_thread_id`. S.I.L.K. will generate a public thread inside the channel to centralize automated messages to keep main chats uncluttered.
     * Level-Up Payloads: S.I.L.K. uses a strict prompt to generate exactly ONE AI hype message, and dynamically attaches the Pillow-generated rank card into the same message payload.
     * Administrative dashboard requiring a `CONFIG_PASS` to lock out unauthorized users. Stats embeds are strictly ephemeral.
     * Performance Optimization: Uses `asyncio.to_thread` for PIL image generation, Discord CDN for pre-resizing avatars, outputs to WebP format to bypass heavy PNG compression, and uses strict Defer Protocols (`await interaction.response.defer()`) *before* executing heavy DB tasks to completely prevent `10062` timeout errors.
   * Commands:
     * `/rank [user]`: Generates a real-time Pillow image displaying the target's stats.
     * `/leaderboard [page] [voice-lb]`: Paginated view of the top server users calculated dynamically.
     * `/bot_config [show-stats]`: Dashboard trigger (ephemeral modal) or ephemeral text-based stats display.
     * `GET/POST /api/level_configs/<guild_id>`: Web API routes for updating level constraints natively via dashboard.py.
   * Dependencies/Configs: `motor`, `Pillow`, `google-genai`, `certifi`. Requires `MONGO_URI` and `CONFIG_PASS` in `.env`. Database defaults defined in `database.py`.

16. Button Module (Phase 16)
   * Primary Role: Generates interactive, clickable buttons for users with customizable timeouts, styles, and ephemeral responses.
   * Files Included:
     * `cogs/button.py`: Cog containing the isolated slash command and custom UI view logic.
   * Core Logic & Features: Utilizes a custom `discord.ui.View` subclass to handle button timeouts (disabling the button when time expires). Reads optional file attachments directly into `io.BytesIO` buffers during execution to prevent Discord attachment links from expiring before a user clicks. Supports an anonymous mode by splitting the ephemeral acknowledgement from the public button payload.
   * Commands:
     * `/button [title] [text] [style] [timeout] [visibility] [anonymous] [file]`
   * Dependencies/Configs: `io`.

17. Web Dashboard Module (Phase 17)
   * Primary Role: External web interface and API routing for configuring S.I.L.K.'s database settings securely via browser using Discord OAuth2.
   * Files Included:
     * `launcher.py`: Subprocess orchestrator that concurrently boots `main.py` and `dashboard.py` and handles crash restarts.
     * `dashboard.py`: Lightweight asynchronous web server running Quart.
     * `templates/base.html`: Master Jinja2 layout containing the sidebar, top navbar, and canvas background.
     * `templates/overview.html`: Multi-page view for Live Stats and heartbeat metrics.
     * `templates/modules.html`: Multi-page view for managing Personalities, Statuses, and Auto-Chat routing.
     * `templates/settings.html`: Multi-page view for Server Settings (Leveling and Custom Commands).
     * `static/js/dashboard.js`: Extracted JavaScript handling API polling, dynamic DOM updates, and the background canvas animation.
   * Core Logic & Features: 
     * Runs completely parallel to the bot process to separate web traffic from Discord Gateway logic. 
     * Uses `motor.motor_asyncio` to connect directly to the bot's shared MongoDB.
     * Implements full Discord OAuth2 login flow using `aiohttp` to exchange codes for tokens and fetch user profiles.
     * Secures endpoints using Quart's encrypted `session` cookies based on the `QUART_SECRET_KEY`.
     * Exposes RESTful API endpoints to read/write specific server configurations (e.g., `chat_configs`), as well as global `bot_statuses` and `personalities`.
     * Restricts dashboard access strictly to users who possess 'Server Admin' or 'Manage Server' permissions in at least one shared Discord server with S.I.L.K. (verified via Heartbeat stats).
     * Integrates `better_profanity` to screen AI Personality prompts to prevent API key bans.
     * Implements a fully responsive, multi-page "Matte Obsidian Bento Box" UI with a global server selector and persistent canvas background animations.
   * Commands/Routes: 
     * `/login`: Redirects user to Discord Authorization URL.
     * `/callback`: Exchanges code for access token, fetches profile, and saves user context to session.
     * `/dashboard/overview`, `/dashboard/modules`, `/dashboard/settings`: Protected UI routes.
     * `GET/POST /api/chat_configs/<guild_id>`
     * `GET/POST/DELETE /api/statuses`
     * `GET/POST/DELETE /api/personalities`
     * `GET/POST/DELETE /api/custom_commands/<guild_id>`
     * `GET /api/live_stats`
     * `GET /api/user_guilds`
   * Dependencies/Configs: `quart`, `aiohttp`, `certifi`, `urllib.request`. Requires `.env` vars: `QUART_SECRET_KEY`, `DISCORD_CLIENT_ID`, `DISCORD_CLIENT_SECRET`, and `DISCORD_REDIRECT_URI`. Runs externally on port `2160`.

18. Heartbeat Module (Phase 18)
   * Primary Role: Background loop that continuously monitors and pushes bot statistics and hardware health.
   * Files Included:
     * `cogs/heartbeat.py`: Controller handling the data collection and pushing to MongoDB.
   * Core Logic & Features:
     * Gathers hardware usage (RAM, CPU), Discord states (Ping, Uptime, Server/Member counts), AI activity (Chats, Voice, API Statuses), and Database latency every 60 seconds.
     * Saves the payload to the `bot_live_stats` collection in MongoDB for external dashboards to query.
   * Commands: None
   * Dependencies/Configs: `psutil`, `requests`, `motor`.

19. Custom Commands Module (Phase 19)
   * Primary Role: Database-driven custom text command system managed via the web dashboard.
   * Files Included:
     * `cogs/custom_commands.py`: Cog with an `on_message` listener that checks incoming text for exact trigger matches against the MongoDB `custom_commands` collection for the guild.
   * Core Logic & Features:
     * Allows custom commands setup per-server.
     * Matches exact and case-sensitive trigger words in message content.
     * Optionally replies directly to the user's message based on the `reply_directly` flag.
   * Commands: None explicitly, triggers based on content.
   * Dependencies/Configs: `motor`.

## 🔮 Future Roadmap (Context for Expansion)
Currently Empty. S.I.L.K. is functionally complete.
