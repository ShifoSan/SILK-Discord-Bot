import discord
from discord import app_commands
from discord.ext import commands
import re
import asyncio
import difflib


class TradeCompare(commands.Cog):
    COMPONENT_TEXT_LIMIT = 3900
    MAX_BREAKDOWN_LINES = 20

    def __init__(self, bot):
        self.bot = bot

        # Reuse the centralized MongoDB client managed by SilkBot.
        self.db_client = bot.mongo_client
        if self.db_client:
            self.collection = self.db_client["silk_bot"]["value_list"]
        else:
            self.collection = None
            print("Warning: MONGO_URI not found. TradeCompare module will fail.")

        # Custom Emojis configuration
        self.emperor_key = "<:EmperorKey:1505387099518537918>"
        self.scroll = "<:Scroll:1505387447218077699>"
        self.vizard_mask = "<:VizardMask:1505387338363043880>"

    # --- Structural Parsing Helpers ---
    def extract_quantity_and_name(self, raw_input: str) -> tuple[int, str]:
        """Extracts multiplier quantities at the start of item strings."""
        clean_input = raw_input.strip()
        match = re.match(r"^(\d+)\s*x?\s+(.+)$", clean_input, re.IGNORECASE)
        if match:
            quantity = int(match.group(1))
            item_name = match.group(2).strip()
            return quantity, item_name
        return 1, clean_input

    def parse_raw_currency(self, item_name: str) -> int | None:
        """Maps 'Key' or 'Keys' inputs straight to raw integers to save DB lookups."""
        clean_name = item_name.strip().lower()
        match = re.match(r"^(\d+)\s*keys?$", clean_name)
        if match:
            return int(match.group(1))
        return None

    def get_numeric_value(self, field, level_key=None):
        """Safely extracts integers or floats out of static values or nested dictionaries."""
        if field is None:
            return 0
        if isinstance(field, dict):
            if level_key and level_key in field:
                return field[level_key] or 0
            return field.get("Min", 0)  # Graceful fallback for range models (Artifact Taxes)
        return field

    def sanitize_display_text(self, value) -> str:
        """Escapes user/database text before rendering it in Discord markdown."""
        safe_value = discord.utils.escape_markdown(str(value))
        return discord.utils.escape_mentions(safe_value)

    def truncate_component_text(self, text: str, limit: int = COMPONENT_TEXT_LIMIT) -> str:
        """Keeps TextDisplay payloads safely under Discord component text limits."""
        if len(text) <= limit:
            return text

        suffix = "\n…output compacted to fit Discord's Components V2 limits."
        return text[: limit - len(suffix)].rstrip() + suffix

    def format_breakdown_lines(self, lines: list[str]) -> str:
        """Compacts long trade breakdowns visually without changing calculated totals."""
        if len(lines) <= self.MAX_BREAKDOWN_LINES:
            return "\n".join(lines)

        visible_lines = lines[: self.MAX_BREAKDOWN_LINES]
        hidden_count = len(lines) - self.MAX_BREAKDOWN_LINES
        visible_lines.append(f"…and {hidden_count} more item(s) included in the totals.")
        return "\n".join(visible_lines)

    def add_text_block(self, container: discord.ui.Container, content: str) -> None:
        """Adds a guarded TextDisplay block to a Components V2 container."""
        container.add_item(discord.ui.TextDisplay(self.truncate_component_text(content)))

    def build_trade_compare_view(
        self,
        user,
        giving_breakdown: list[str],
        getting_breakdown: list[str],
        total_giving_keys,
        total_giving_scrolls,
        total_giving_vizard,
        total_giving_gems_tax,
        total_giving_gold_tax,
        total_getting_keys,
        total_getting_scrolls,
        total_getting_vizard,
        total_getting_gems_tax,
        total_getting_gold_tax,
        verdict: str,
        accent_color: int,
        margin_keys,
        margin_scrolls,
        margin_vizard,
        sign: str,
        unmatched_items: list[str],
    ) -> discord.ui.LayoutView:
        """Builds the successful trade analytics dashboard using Discord Components V2."""
        view = discord.ui.LayoutView(timeout=None)
        container = discord.ui.Container(accent_color=discord.Color(accent_color))

        self.add_text_block(
            container,
            f"### ⚖️ S.I.L.K. — Trade Analytics Engine\n"
            f"Requested by **{self.sanitize_display_text(user.display_name)}**",
        )
        container.add_item(discord.ui.Separator())

        self.add_text_block(
            container,
            "### 📤 SIDE A (WHAT YOU ARE GIVING)\n"
            f"{self.format_breakdown_lines(giving_breakdown)}\n\n"
            f"**Total Outbound Value:**\n"
            f"📊 {self.emperor_key} `{total_giving_keys:,} Keys` | "
            f"{self.scroll} `{total_giving_scrolls:,.1f} Scrolls` | "
            f"{self.vizard_mask} `{total_giving_vizard:,.2f} Viz`\n"
            f"💼 **Your Required Trade Tax:** 💎 `{total_giving_gems_tax:,} Gems` | "
            f"🪙 `{total_giving_gold_tax:,} Gold`",
        )
        container.add_item(discord.ui.Separator())

        self.add_text_block(
            container,
            "### 📥 SIDE B (WHAT YOU ARE RECEIVING)\n"
            f"{self.format_breakdown_lines(getting_breakdown)}\n\n"
            f"**Total Inbound Value:**\n"
            f"📊 {self.emperor_key} `{total_getting_keys:,} Keys` | "
            f"{self.scroll} `{total_getting_scrolls:,.2f} Scrolls` | "
            f"{self.vizard_mask} `{total_getting_vizard:,.2f} Viz`\n"
            f"💼 **Their Required Trade Tax:** 💎 `{total_getting_gems_tax:,} Gems` | "
            f"🪙 `{total_getting_gold_tax:,} Gold`",
        )
        container.add_item(discord.ui.Separator())

        transaction_content = (
            "### 📊 TRANSACTION BREAKDOWN\n"
            "```ansi\n"
            f"{verdict}\n"
            f"📈 NET MARGIN: {sign}{margin_keys:,} Keys "
            f"({sign}{margin_scrolls:,.1f} Scrolls / {sign}{margin_vizard:,.2f} Viz)\n"
            "```"
        )

        if unmatched_items:
            compacted_items = self.format_breakdown_lines(unmatched_items)
            transaction_content += (
                "\n\n### ⚠️ Typo Warning / Items Not Found\n"
                "The following inputs could not be cleanly identified and calculated as `0 Keys`:\n"
                f"{compacted_items}"
            )

        self.add_text_block(container, transaction_content)
        container.add_item(discord.ui.Separator())
        self.add_text_block(container, "**Trade margins calculated mechanically | Zero AI footprint.**")

        view.add_item(container)
        return view

    # --- Mechanical Core Search Engine ---
    async def fetch_item_data(self, raw_item_query: str) -> dict:
        """Runs the free Atlas Search Fuzzy Filter and direct tie-breaker local routing."""
        quantity, item_query = self.extract_quantity_and_name(raw_item_query)

        # Immediate exit path for raw currency strings
        direct_keys = self.parse_raw_currency(item_query)
        if direct_keys is not None:
            total_keys = direct_keys * quantity
            return {
                "display_name": f"Raw Currency ({total_keys:,} Keys)",
                "keys": total_keys,
                "scrolls": total_keys / 3,
                "vizard": total_keys / 900,
                "gems_tax": 0,
                "gold_tax": 0,
                "error": None,
            }

        if self.collection is None:
            return {
                "display_name": raw_item_query,
                "keys": 0,
                "scrolls": 0,
                "vizard": 0,
                "gems_tax": 0,
                "gold_tax": 0,
                "error": "config_missing",
            }

        try:
            # Step 1: Detect Tier Level requirements from player string context
            query_lower = item_query.lower()
            is_lvl10 = any(x in query_lower for x in ["10", "max", "lvl10", "lvl 10", "level 10", "level10"])
            level_key = "Lvl_10" if is_lvl10 else "Lvl_0"

            # Step 2: Clear level labels from search term to maximize index text matching accuracy
            search_query = re.sub(r"\b(lvl|level|lv)\s*(0|10)\b", "", item_query, flags=re.IGNORECASE)
            search_query = re.sub(r"\b(max)\b", "", search_query, flags=re.IGNORECASE)
            search_query = re.sub(r"\s+", " ", search_query).strip()
            if not search_query:
                search_query = item_query

            # Step 3: Run Atlas Search Fuzzy Match Query Filter
            pipeline = [
                {
                    "$search": {
                        "index": "default",
                        "text": {
                            "query": search_query,
                            "path": "Item",
                            "fuzzy": {
                                "maxEdits": 2,
                                "prefixLength": 1,
                            },
                        },
                    }
                },
                {"$limit": 5},
            ]

            cursor = self.collection.aggregate(pipeline)
            search_results = await cursor.to_list(length=5)

            if not search_results:
                return {
                    "display_name": raw_item_query,
                    "keys": 0,
                    "scrolls": 0,
                    "vizard": 0,
                    "gems_tax": 0,
                    "gold_tax": 0,
                    "error": "not_found",
                }

            # Step 4: Python String Tie-Breaker Match over candidates
            candidate_names = [doc["Item"] for doc in search_results]
            best_matches = difflib.get_close_matches(search_query, candidate_names, n=1, cutoff=0.0)
            best_match_name = best_matches[0]

            data = next(doc for doc in search_results if doc["Item"] == best_match_name)

            # Step 5: Tunnelling and parsing properties programmatically
            final_name = data.get("Item", "Unknown Item")
            is_perk = data.get("Category") == "Perks"
            level_label = f" ({level_key.replace('_', ' ')})" if is_perk else ""

            base_keys = self.get_numeric_value(data.get("Value_Key"), level_key if is_perk else None)
            base_scrolls = self.get_numeric_value(data.get("Value_Scroll"), level_key if is_perk else None)
            base_vizard = self.get_numeric_value(data.get("Value_Viz"), level_key if is_perk else None)
            base_gold_tax = self.get_numeric_value(data.get("Tax_Gold"), level_key if is_perk else None)
            base_gems_tax = self.get_numeric_value(data.get("Tax_Gem"), level_key if is_perk else None)

            # Format item display tags
            item_display_decor = f"{final_name}{level_label}"
            display_name = f"{item_display_decor} x{quantity}" if quantity > 1 else item_display_decor

            return {
                "display_name": display_name,
                "keys": base_keys * quantity,
                "scrolls": base_scrolls * quantity,
                "vizard": base_vizard * quantity,
                "gems_tax": base_gems_tax * quantity,
                "gold_tax": base_gold_tax * quantity,
                "error": None,
            }

        except Exception:
            return {
                "display_name": raw_item_query,
                "keys": 0,
                "scrolls": 0,
                "vizard": 0,
                "gems_tax": 0,
                "gold_tax": 0,
                "error": "failed_to_parse",
            }

    @app_commands.command(name="trade-compare", description="Calculate if a trade is a Win or a Loss based on item values.")
    @app_commands.describe(
        giving="The items you are giving up (separate items using '+')",
        getting="The items you are receiving (separate items using '+')",
    )
    async def trade_compare(self, interaction: discord.Interaction, giving: str, getting: str):
        try:
            await interaction.response.defer(thinking=True)
            # Route processing variables smoothly to the decoupled core
            await self.execute_trade_compare(interaction.followup, interaction.user, giving, getting)
        except Exception as e:
            await interaction.followup.send(f"An error occurred during transaction preparation: {str(e)}")

    async def execute_trade_compare(self, destination, user, giving: str, getting: str):
        """Isolated operational core processing both prefix listeners and slash commands."""
        try:
            giving_list = [item.strip() for item in giving.split("+") if item.strip()]
            getting_list = [item.strip() for item in getting.split("+") if item.strip()]

            if not giving_list or not getting_list:
                await destination.send("⚠️ Invalid formatting. Please provide items for both fields split by `+`.")
                return

            # Fire async batch routines concurrently across the value matrix
            giving_tasks = [self.fetch_item_data(item) for item in giving_list]
            getting_tasks = [self.fetch_item_data(item) for item in getting_list]

            giving_results = await asyncio.gather(*giving_tasks)
            getting_results = await asyncio.gather(*getting_tasks)

            total_giving_keys, total_giving_scrolls, total_giving_vizard = 0, 0, 0
            total_giving_gems_tax, total_giving_gold_tax = 0, 0

            total_getting_keys, total_getting_scrolls, total_getting_vizard = 0, 0, 0
            total_getting_gems_tax, total_getting_gold_tax = 0, 0

            giving_breakdown, getting_breakdown, unmatched_items = [], [], []

            # Accumulate metrics for Giving parameters
            for res in giving_results:
                display_name = self.sanitize_display_text(res["display_name"])
                if res["error"] == "not_found":
                    unmatched_items.append(f"`{display_name}` (Giving Side)")
                total_giving_keys += res["keys"]
                total_giving_scrolls += res["scrolls"]
                total_giving_vizard += res["vizard"]
                total_giving_gems_tax += res["gems_tax"]
                total_giving_gold_tax += res["gold_tax"]

                val_display = f"{res['keys']:,}" if res["keys"] > 0 else "N/A / O/C"
                giving_breakdown.append(f"• {display_name} — {self.emperor_key} **{val_display}** Keys")

            # Accumulate metrics for Getting parameters
            for res in getting_results:
                display_name = self.sanitize_display_text(res["display_name"])
                if res["error"] == "not_found":
                    unmatched_items.append(f"`{display_name}` (Getting Side)")
                total_getting_keys += res["keys"]
                total_getting_scrolls += res["scrolls"]
                total_getting_vizard += res["vizard"]
                total_getting_gems_tax += res["gems_tax"]
                total_getting_gold_tax += res["gold_tax"]

                val_display = f"{res['keys']:,}" if res["keys"] > 0 else "N/A / O/C"
                getting_breakdown.append(f"• {display_name} — {self.emperor_key} **{val_display}** Keys")

            # Calculate Win/Loss Verdict Ratios safely
            if total_giving_keys == 0:
                ratio = 5.0 if total_getting_keys > 0 else 1.0
            else:
                ratio = total_getting_keys / total_giving_keys

            if ratio >= 1.50:
                verdict = "🚀 VERDICT: MASSIVE WIN (HUGE W)"
                embed_color = 0x00FF00
            elif 1.10 <= ratio < 1.50:
                verdict = "✅ VERDICT: PROFIT (SLIGHT W)"
                embed_color = 0x2ECC71
            elif 0.90 < ratio < 1.10:
                verdict = "🤝 VERDICT: FAIR TRADE"
                embed_color = 0x3498DB
            elif 0.60 <= ratio <= 0.90:
                verdict = "⚠️ VERDICT: LOSS (SLIGHT L)"
                embed_color = 0xE67E22
            else:
                verdict = "🛑 VERDICT: SEVERE DEFICIT (MASSIVE L)"
                embed_color = 0xE74C3C

            margin_keys = total_getting_keys - total_giving_keys
            margin_scrolls = total_getting_scrolls - total_giving_scrolls
            margin_vizard = total_getting_vizard - total_giving_vizard
            sign = "+" if margin_keys >= 0 else ""

            # Build output presentation dashboard using Discord Components V2.
            view = self.build_trade_compare_view(
                user,
                giving_breakdown,
                getting_breakdown,
                total_giving_keys,
                total_giving_scrolls,
                total_giving_vizard,
                total_giving_gems_tax,
                total_giving_gold_tax,
                total_getting_keys,
                total_getting_scrolls,
                total_getting_vizard,
                total_getting_gems_tax,
                total_getting_gold_tax,
                verdict,
                embed_color,
                margin_keys,
                margin_scrolls,
                margin_vizard,
                sign,
                unmatched_items,
            )
            await destination.send(view=view, allowed_mentions=discord.AllowedMentions.none())

        except Exception as e:
            await destination.send(f"An error occurred during trade comparison processing: {str(e)}")


async def setup(bot):
    await bot.add_cog(TradeCompare(bot))
