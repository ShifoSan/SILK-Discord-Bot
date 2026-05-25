import discord
from discord import app_commands
from discord.ext import commands
import os
import json
import re
import asyncio
import certifi
from motor.motor_asyncio import AsyncIOMotorClient
from google import genai
from google.genai import types

class TradeCompare(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        
        # Initialize Google GenAI
        self.api_key = os.getenv("GEMINI_API_KEY")
        if self.api_key:
            self.client = genai.Client(api_key=self.api_key)
        else:
            self.client = None
            print("Warning: GEMINI_API_KEY not found. TradeCompare module will fail.")

        # Initialize MongoDB natively targeting the manual database route
        self.mongo_uri = os.getenv("MONGO_URI")
        if self.mongo_uri:
            self.db_client = AsyncIOMotorClient(self.mongo_uri, tlsCAFile=certifi.where())
            self.collection = self.db_client["silk_bot"]["aotr_knowledge"]
        else:
            self.db_client = None
            self.collection = None
            print("Warning: MONGO_URI not found. TradeCompare module will fail.")

        # Custom Emojis configuration
        self.emperor_key = "<:EmperorKey:1505387099518537918>"
        self.scroll = "<:Scroll:1505387447218077699>"
        self.vizard_mask = "<:VizardMask:1505387338363043880>"

    def extract_quantity_and_name(self, raw_input: str) -> tuple[int, str]:
        """
        Extracts multiplier quantities at the start of item strings.
        Example: "2 x Lvl 10 Kengo" -> (2, "Lvl 10 Kengo")
        """
        clean_input = raw_input.strip()
        match = re.match(r"^(\d+)\s*x?\s+(.+)$", clean_input, re.IGNORECASE)
        if match:
            quantity = int(match.group(1))
            item_name = match.group(2).strip()
            return quantity, item_name
        return 1, clean_input

    def parse_raw_currency(self, item_name: str) -> int | None:
        """
        Maps 'Key' or 'Keys' directly to Emperor Keys to save API latency.
        """
        clean_name = item_name.strip().lower()
        match = re.match(r"^(\d+)\s*keys?$", clean_name)
        if match:
            return int(match.group(1))
        return None

    def parse_tax_value(self, tax_val) -> int:
        """
        Turns short-scale thousands multipliers like '480k' or '140k' into integers.
        """
        if not tax_val or str(tax_val).lower() in ["unknown", "none", "0", "undefined"]:
            return 0
            
        clean_tax = str(tax_val).replace(",", "").strip().lower()
        match = re.search(r"(\d+(\.\d+)?)\s*(k)?", clean_tax)
        if match:
            base_val = float(match.group(1))
            is_k_scaled = match.group(3) is not None
            return int(base_val * 1000) if is_k_scaled else int(base_val)
            
        return 0

    async def fetch_item_data(self, raw_item_query: str) -> dict:
        """
        Optimizes strings, runs structural dual extraction via Gemini, 
        and maps level stats using deterministic Python rules.
        """
        quantity, item_query = self.extract_quantity_and_name(raw_item_query)

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
                "error": None
            }

        if self.client is None or self.collection is None:
            return {"display_name": raw_item_query, "keys": 0, "scrolls": 0, "vizard": 0, "gems_tax": 0, "gold_tax": 0, "error": "config_missing"}

        try:
            # Rule 1: Deterministic Level Target Detection via Python
            query_lower = item_query.lower()
            is_lvl10 = any(x in query_lower for x in ["10", "max", "lvl10", "lvl 10", "level 10", "level10"])

            # Rule 2: Clean level clutter out to optimize Vector Index matching accuracy
            search_query = re.sub(r"\b(lvl|level|lv)\s*(0|10)\b", "", item_query, flags=re.IGNORECASE)
            search_query = re.sub(r"\b(max)\b", "", search_query, flags=re.IGNORECASE)
            search_query = re.sub(r"\s+", " ", search_query).strip()
            if not search_query:  # Fallback if query was only numerical level text
                search_query = item_query

            # Vector Search Pipeline
            embedding_response = await self.client.aio.models.embed_content(
                model="gemini-embedding-2",
                contents=search_query
            )
            vector = embedding_response.embeddings[0].values

            pipeline = [
                {
                    "$vectorSearch": {
                        "index": "vector_index",
                        "path": "embedding",
                        "queryVector": vector,
                        "numCandidates": 50,
                        "limit": 5
                    }
                },
                {
                    "$project": {
                        "content": 1,
                        "_id": 0
                    }
                }
            ]

            cursor = self.collection.aggregate(pipeline)
            results = await cursor.to_list(length=5)

            if not results:
                return {"display_name": raw_item_query, "keys": 0, "scrolls": 0, "vizard": 0, "gems_tax": 0, "gold_tax": 0, "error": "not_found"}

            chunks = "\n\n".join([doc.get("content", "") for doc in results])

            # Rule 3: Enforce strict dual schema extraction layout instructions
            system_prompt = (
                "You are a strict data extraction tool. You will receive an item search query and database texts.\n\n"
                "Task 1: Identify which item from the database text best matches the query regardless of typos.\n"
                "Task 2: Extract data fields into a JSON object with EXACTLY these keys:\n"
                "name, is_perk, lvl0, lvl10.\n\n"
                "Extraction Instructions:\n"
                "- 'is_perk' must be true if the database text explicitly contains separate level stats (e.g. 'Lvl 0:' or 'Level 0 Value:'), otherwise false.\n"
                "- 'lvl0' and 'lvl10' are child objects each containing: keys, scrolls, vizard, gems_tax, gold_tax.\n"
                "- For standard single items without tiers, extract metrics into 'lvl0' and set 'lvl10' to null.\n"
                "- Pull base integers for value metrics or return 'Undefined'. Pass tax variables verbatim (e.g. '480k') or '0' if missing.\n"
                "- If the item does not exist inside the text context, return EXACTLY: {\"error\": \"not_found\"}\n"
                "- Return ONLY raw, valid JSON text blocks."
            )

            response = await self.client.aio.models.generate_content(
                model='gemini-3.1-flash-lite-preview',
                contents=f"Query: {search_query}\n\nDatabase Text:\n{chunks}",
                config=types.GenerateContentConfig(
                    response_mime_type="application/json",
                    system_instruction=system_prompt,
                    temperature=0.1
                )
            )

            data = json.loads(response.text)
            if isinstance(data, list) and len(data) > 0:
                data = data[0]

            if data.get("error") == "not_found":
                return {"display_name": raw_item_query, "keys": 0, "scrolls": 0, "vizard": 0, "gems_tax": 0, "gold_tax": 0, "error": "not_found"}

            def clean_int(val) -> int:
                if isinstance(val, (int, float)):
                    return int(val)
                digits = re.findall(r"\d+", str(val).replace(",", ""))
                return int(digits[0]) if digits else 0

            is_perk = data.get("is_perk", False)

            # Rule 4: Route data deterministically based on Python's level detection check
            if is_perk and is_lvl10 and data.get("lvl10"):
                stats = data["lvl10"]
                level_label = " (Lvl 10)"
            else:
                stats = data.get("lvl0", {})
                level_label = " (Lvl 0)" if is_perk else ""

            base_keys = clean_int(stats.get("keys", 0))
            raw_scrolls = stats.get("scrolls")
            raw_vizard = stats.get("vizard")
            
            base_scrolls = clean_int(raw_scrolls) if raw_scrolls and str(raw_scrolls).lower() != "undefined" else (base_keys / 3)
            base_vizard = clean_int(raw_vizard) if raw_vizard and str(raw_vizard).lower() != "undefined" else (base_keys / 900)

            base_gems_tax = self.parse_tax_value(stats.get("gems_tax", 0))
            base_gold_tax = self.parse_tax_value(stats.get("gold_tax", 0))

            final_name = data.get("name", search_query)
            item_display_decor = f"{final_name}{level_label}"
            display_name = f"{item_display_decor} x{quantity}" if quantity > 1 else item_display_decor

            return {
                "display_name": display_name,
                "keys": base_keys * quantity,
                "scrolls": base_scrolls * quantity,
                "vizard": base_vizard * quantity,
                "gems_tax": base_gems_tax * quantity,
                "gold_tax": base_gold_tax * quantity,
                "error": None
            }

        except Exception:
            return {"display_name": raw_item_query, "keys": 0, "scrolls": 0, "vizard": 0, "gems_tax": 0, "gold_tax": 0, "error": "failed_to_parse"}

    @app_commands.command(name="trade-compare", description="Calculate if a trade is a Win or a Loss based on item values.")
    @app_commands.describe(
        giving="The items you are giving up (separate items using '+')",
        getting="The items you are receiving (separate items using '+')"
    )
    async def trade_compare(self, interaction: discord.Interaction, giving: str, getting: str):
        await interaction.response.defer(thinking=True)

        giving_list = [item.strip() for item in giving.split("+") if item.strip()]
        getting_list = [item.strip() for item in getting.split("+") if item.strip()]

        if not giving_list or not getting_list:
            await interaction.followup.send("⚠️ Invalid formatting. Please provide items for both fields split by `+`.")
            return

        giving_tasks = [self.fetch_item_data(item) for item in giving_list]
        getting_tasks = [self.fetch_item_data(item) for item in getting_list]

        giving_results = await asyncio.gather(*giving_tasks)
        getting_results = await asyncio.gather(*getting_tasks)

        total_giving_keys, total_giving_scrolls, total_giving_vizard = 0, 0, 0
        total_giving_gems_tax, total_giving_gold_tax = 0, 0

        total_getting_keys, total_getting_scrolls, total_getting_vizard = 0, 0, 0
        total_getting_gems_tax, total_getting_gold_tax = 0, 0

        giving_breakdown, getting_breakdown, unmatched_items = [], [], []

        for res in giving_results:
            if res["error"] == "not_found":
                unmatched_items.append(f"`{res['display_name']}` (Giving Side)")
            total_giving_keys += res["keys"]
            total_giving_scrolls += res["scrolls"]
            total_giving_vizard += res["vizard"]
            total_giving_gems_tax += res["gems_tax"]
            total_giving_gold_tax += res["gold_tax"]
            giving_breakdown.append(f"• {res['display_name']} — {self.emperor_key} **{res['keys']:,}** Keys")

        for res in getting_results:
            if res["error"] == "not_found":
                unmatched_items.append(f"`{res['display_name']}` (Getting Side)")
            total_getting_keys += res["keys"]
            total_getting_scrolls += res["scrolls"]
            total_getting_vizard += res["vizard"]
            total_getting_gems_tax += res["gems_tax"]
            total_getting_gold_tax += res["gold_tax"]
            getting_breakdown.append(f"• {res['display_name']} — {self.emperor_key} **{res['keys']:,}** Keys")

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

        embed = discord.Embed(title="⚖️ S.I.L.K. — Trade Analytics Engine", color=embed_color)
        avatar_url = interaction.user.display_avatar.url if interaction.user.display_avatar else None
        embed.set_author(name=interaction.user.display_name, icon_url=avatar_url)

        embed.add_field(
            name="📤 SIDE A (WHAT YOU ARE GIVING)",
            value="\n".join(giving_breakdown) + 
                  f"\n\n**Total Outbound Value:**\n📊 {self.emperor_key} `{total_giving_keys:,} Keys` | {self.scroll} `{total_giving_scrolls:,.2f} Scrolls` | {self.vizard_mask} `{total_giving_vizard:,.2f} Viz`" +
                  f"\n💼 **Your Required Trade Tax:** 💎 `{total_giving_gems_tax:,} Gems` | 🪙 `{total_giving_gold_tax:,} Gold`",
            inline=False
        )

        embed.add_field(
            name="📥 SIDE B (WHAT YOU ARE RECEIVING)",
            value="\n".join(getting_breakdown) + 
                  f"\n\n**Total Inbound Value:**\n📊 {self.emperor_key} `{total_getting_keys:,} Keys` | {self.scroll} `{total_getting_scrolls:,.2f} Scrolls` | {self.vizard_mask} `{total_getting_vizard:,.2f} Viz`" +
                  f"\n💼 **Their Required Trade Tax:** 💎 `{total_getting_gems_tax:,} Gems` | 🪙 `{total_getting_gold_tax:,} Gold`",
            inline=False
        )

        breakdown_text = (
            f"```ansi\n"
            f"{verdict}\n"
            f"📈 NET MARGIN: {sign}{margin_keys:,} Keys ({sign}{margin_scrolls:,.1f} Scrolls / {sign}{margin_vizard:,.2f} Viz)\n"
            f"```"
        )
        embed.add_field(name="📊 TRANSACTION BREAKDOWN", value=breakdown_text, inline=False)

        if unmatched_items:
            embed.add_field(
                name="⚠️ Typo Warning / Items Not Found",
                value=f"The following inputs could not be cleanly identified and calculated as `0 Keys`:\n{', '.join(unmatched_items)}",
                inline=False
            )

        embed.set_footer(text="The official AoTR values | Data dynamically synchronized from live sheet.")
        await interaction.followup.send(embed=embed)

async def setup(bot):
    await bot.add_cog(TradeCompare(bot))
