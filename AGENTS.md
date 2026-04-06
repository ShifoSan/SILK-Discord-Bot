# S.I.L.K. Bot - Codebase Context & Architecture

## Project Overview
S.I.L.K. is a modular Discord bot written in Python using discord.py. It is currently hosted on KataBump to bypass shared-IP Cloudflare bans from Discord. The codebase is strictly modular, using "Cogs" (extensions) to separate functionality into distinct domains.

## Root Configuration
* `requirements.txt`: Contains the list of Python dependencies required to run the bot (Flask removed).
* `.env`: (Ignored by Git) Environment variables such as `DISCORD_TOKEN`, `GEMINI_API_KEY`, `HUGGINGFACE_TOKEN`, `MONGO_URI`, and `CONFIG_PASS`.

## 🏗️ Architectural Standards
 * Framework: discord.py (latest version) using app_commands (Slash Commands).
 * Hosting: KataBump (Temporary Environment).
   * Constraint: Background sleeping or restarts handled by KataBump's free tier. 
 * Command Syncing:
   * Strategy: Auto-syncing on boot is strictly disabled to prevent 1015 IP bans. 
   * Execution: Command registration is handled manually by the bot owner using the `!sync` command, which slowly pushes updates to all servers to respect rate limits.
 * File Structure:
   * main.py: Entry point. Loads env vars, iterates cogs/ to load extensions, and handles the Discord connection.
   * cogs/: Directory for all bot modules. New features MUST be added here as separate files.
   * cogs/personalities/: Directory for personality configuration modules (Standard, Edgy, Helpful).
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
     * `imagine`: Uses Hugging Face router for Stable Diffusion XL. Returns images as byte streams (`io.BytesIO`) directly in embeds. Warns users on 503 Cold Starts.
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
     * `cogs/personalities/standard.py`: Standard personality system prompt and safety config.
     * `cogs/personalities/edgy.py`: Edgy personality system prompt and safety config.
     * `cogs/personalities/helpful.py`: Helpful personality system prompt and safety config.
   * Core Logic & Features:
     * Uses `asyncio.to_thread` for GenAI and gTTS calls to avoid blocking the event loop.
     * Voice mode converts responses to an MP3 stream using `io.BytesIO` while filtering URLs/code blocks and limiting to 500 chars.
     * Maintains a 30 RPM sliding window rate limit using a deque.
     * Retrieves conversational history (last 20 messages) and reformats it with `[Model - S.I.L.K.]` and `[User - Name]`.
     * Identifies Creator explicitly using the `(CREATOR_VERIFIED)` tag for security overrides.
     * Stores persistent auto-chat configurations (enabled state and language) in a MongoDB `chat_configs` collection.
     * Multi-Language Routing: If 'Hindi' is selected, automatically shifts to `gemini-3.1-flash-lite-preview` using a dedicated Hinglish casual persona prompt. English defaults to `gemma-3-27b-it`.
   * Commands:
     * `/chat_toggle [state] [language]`: Enable/Disable auto-chat in the current channel and optionally set the language (English/Hindi).
     * `/voice_mode [state]`: Enable/Disable Hybrid Voice responses in the current channel.
     * `/persona [name]`: Switch between Standard, Edgy, or Helpful.
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
   * Core Logic & Features: Uses a `tasks.loop` running every 20 seconds cycling through standard statuses. Supports dynamic `{member_count}` interpolation aggregating users across all connected guilds. Uses `before_loop` to `wait_until_ready()`.
   * Commands: None.
   * Dependencies/Configs: `discord.ext.tasks`, `itertools`.

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
     * Enforces the "Helpful" personality for all AI outputs and maintains a separate 20-message `deque` history limit for each user.
   * Commands:
     * `/dm-list`: Displays ephemeral embed listing Approved, Pending, and Blocked users (Creator Only).
   * Dependencies/Configs: Requires `dm_config.json` for persistence and `google-genai`.

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
     * `cogs/level_system/core.py`: Main cog loading the configurations and handling `on_message`, `on_raw_reaction_add`, `on_voice_state_update`, and join/leave logic.
     * `cogs/level_system/database.py`: Asynchronous MongoDB connector for saving/retrieving user progress and server configs. (Uses `certifi` to force updated SSL certs on server hosts).
     * `cogs/level_system/commands.py`: Houses the user-facing slash commands (`/rank`, `/leaderboard`, `/bot_config`). Passes avatar bytes to prevent blocking. 
     * `cogs/level_system/image_gen.py`: Pillow-based generator drawing dynamic rank cards using `banner.png`. (Handles raw bytes instead of synchronous URL requests).
     * `cogs/level_system/ai_responses.py`: Isolated GenAI connector generating personalized level-up messages via `gemma-3-27b-it`.
     * `cogs/level_system/bot_config/`: Sub-directory containing interactive configuration UI components (`main_menu.py`, `role_rewards.py`, `xp_management.py`, `vc_settings.py`, `spam_filters.py`, `cooldown_settings.py`). 
   * Core Logic & Features:
     * Dynamic math using a quadratic curve `5*(level^2) + 50*level + 100` for leveling. Tracks exact true level dynamically based on total XP.
     * Soft data retention tracking `in_server` status to preserve leaving users' progress without cluttering leaderboards.
     * Dynamic Configuration UI: Utilizes `discord.ui.Button` triggers launching `discord.ui.Modal` with text inputs to allow for arbitrary integer configurations (custom XP values, custom cooldowns, mapped role rewards, deletion of role rewards). Views use an extended 10-minute timeout. UI components strictly manage row widths to avoid Discord limits.
     * Dedicated AI Channel & Thread Routing: Administrators can designate a specific `level_up_channel` via a Channel Select menu and explicitly set a `level_up_thread_id`. S.I.L.K. will generate a public thread inside the channel to centralize automated messages to keep main chats uncluttered.
     * Level-Up Payloads: S.I.L.K. uses a strict prompt to generate exactly ONE AI hype message, and dynamically attaches the Pillow-generated rank card into the same message payload.
     * Administrative dashboard requiring a `CONFIG_PASS` to lock out unauthorized users. Stats embeds are strictly ephemeral.
     * Performance Optimization: Uses `asyncio.to_thread` for PIL image generation, `await asset.read()` for avatars, and strict Defer Protocols (`await interaction.response.defer()`) *before* executing heavy DB tasks to completely prevent `10062` timeout errors.
   * Commands:
     * `/rank [user]`: Generates a real-time Pillow image displaying the target's stats.
     * `/leaderboard [page] [voice-lb]`: Paginated view of the top server users calculated dynamically.
     * `/bot_config [show-stats]`: Dashboard trigger (ephemeral modal) or ephemeral text-based stats display.
   * Dependencies/Configs: `motor`, `Pillow`, `google-genai`, `certifi`. Requires `MONGO_URI` and `CONFIG_PASS` in `.env`. Database defaults defined in `database.py`.

## 🔮 Future Roadmap (Context for Expansion)
Currently Empty. S.I.L.K. is functionally complete.
