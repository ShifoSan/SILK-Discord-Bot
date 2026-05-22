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

        # Initialize MongoDB natively targeting the exact Version 2 manual route
        self.mongo_uri = os.getenv("MONGO_URI")
        if self.mongo_uri:
            self.db_client = AsyncIOMotorClient(self.mongo_uri, tlsCAFile=certifi.where())
            self.collection = self.db_client["silk_bot"]["aotr_knowledge"]
        else:
            self.db_client = None
            self.collection = None
            print("Warning: MONGO_URI not found. TradeCompare module will fail.")

        # Custom Emojis inherited from your aotr_value.py settings
        self.emperor_key = "<:EmperorKey:1505387099518537918>"
        self.scroll = "<:Scroll:1505387447218077699>"
        self.vizard_mask = "<:VizardMask:1505387338363043880>"

    def extract_quantity_and_name(self, raw_input: str) -> tuple[int, str]:
        """
        Extracts multiplier quantities at the start of item strings.
        Example: "2 colossal shard" -> (2, "colossal shard")
        Example: "Fritz" -> (1, "Fritz")
        """
        clean_input = raw_input.strip()
        # Matches patterns like "2 x colossal shard", "2x colossal shard", or "2 colossal shard"
        match = re.match(r"^(\d+)\s*x?\s+(.+)$", clean_input, re.IGNORECASE)
        if match:
            quantity = int(match.group(1))
            item_name = match.group(2).strip()
            return quantity, item_name
        return 1, clean_input

    def parse_raw_currency(self, item_name: str) -> int | None:
        """
        Optimized local shortcut matching: Map 'Key' or 'Keys' directly to Emperor Keys.
        Bypasses the database cluster entirely to save network processing latency.
        """
        clean_name = item_name.strip().lower()
        match = re.match(r"^(\d+)\s*keys?$", clean_name)
        if match:
            return int(match.group(1))
        return None

    def parse_tax_value(self, tax_val) -> int:
        """
        Robust text parser that handles raw integers, strings, and short-scale 
        thousands multipliers like '50k' or '58k', turning them into proper numbers.
        """
        if not tax_val or str(tax_val).lower() in ["unknown", "none", "0", "undefined"]:
            return 0
            
        clean_tax = str(tax_val).replace(",", "").strip().lower()
        
        # Look for numbers optionally followed by 'k'
        match = re.search(r"(\d+)\s*(k)?", clean_tax)
        if match:
            base_val = int(match.group(1))
            is_k_scaled = match.group(2) is not None
            return base_val * 1000 if is_k_scaled else base_val
            
        return 0

    async def fetch_item_data(self, raw_item_query: str) -> dict:
        """
        Extracts stack multipliers, employs the Version 2 RAG architecture with widened 
        boundaries, matches misspelled names, and applies the stack multiplication factor.
        """
        # Extract item multiplier count if provided
        quantity, item_query = self.extract_quantity_and_name(raw_item_query)

        # Shortcut calculation evaluation check for raw currency injections
        direct_keys = self.parse_raw_currency(item_query)
        if direct_keys is not None:
            # Multiplied directly by quantity count
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
            # Vector Search Pipeline - Widened boundaries to catch typos (V2 Setup)
            embedding_response = await self.client.aio.models.embed_content(
                model="gemini-embedding-2",
                contents=item_query
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

            # Explicitly instruct the AI to isolate Tax (Gems) and Tax (Gold)
            system_prompt = (
                "You are a strict data extraction tool. You will receive a user's search query (which may contain typos) "
                "and a set of database texts.\n\n"
                "Task 1: Identify which item from the database text best matches the user's query regardless of typos.\n"
                "Task 2: Extract the data for THAT specific item into a JSON object with EXACTLY these keys:\n"
                "name, keys, scrolls, vizard, gems_tax, gold_tax.\n\n"
                "Tax Extraction Rules:\n"
                "- Look inside the database text for 'Tax (Gems):' and extract its value into 'gems_tax' (e.g., if text says 'Tax (Gems): 💎50k', extract '50k').\n"
                "- Look inside the database text for 'Tax (Gold):' and extract its value into 'gold_tax' (e.g., if text says 'Tax (Gold): 🪙58k', extract '58k').\n"
                "- If either text field is completely absent or not specified for the matched item, set its respective JSON value to '0'.\n\n"
                "General Rules:\n"
                "- Numerical value fields (keys, scrolls, vizard) should represent raw single-item metrics, or fallback to 'Undefined'.\n"
                "- If the item is completely missing, output EXACTLY this JSON: {\"error\": \"not_found\"}\n"
                "- Output ONLY raw, valid JSON. Do not include markdown formatting code blocks."
            )

            response = await self.client.aio.models.generate_content(
                model='gemini-3.1-flash-lite-preview',
                contents=f"User's Query: {item_query}\n\nDatabase Text:\n{chunks}",
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

            # Single item base stats parsing
            base_keys = clean_int(data.get("keys", 0))
            raw_scrolls = data.get("scrolls")
            raw_vizard = data.get("vizard")
            
            base_scrolls = clean_int(raw_scrolls) if raw_scrolls and str(raw_scrolls).lower() != "undefined" else (base_keys / 3)
            base_vizard = clean_int(raw_vizard) if raw_vizard and str(raw_vizard).lower() != "undefined" else (base_keys / 900)

            base_gems_tax = self.parse_tax_value(data.get("gems_tax", 0))
            base_gold_tax = self.parse_tax_value(data.get("gold_tax", 0))

            # Apply Stack Multipliers safely across all elements
            final_name = data.get("name", item_query)
            display_name = f"{final_name} x{quantity}" if quantity > 1 else final_name

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
        # The Defer Protocol protects against interaction timeout drops (3-second limit)
        await interaction.response.defer(thinking=True)

        giving_list = [item.strip() for item in giving.split("+") if item.strip()]
        getting_list = [item.strip() for item in getting.split("+") if item.strip()]

        if not giving_list or not getting_list:
            await interaction.followup.send("⚠️ Invalid formatting. Please provide items for both fields split by `+`.")
            return

        # Parallel Execution: Runs lookups concurrently to protect the Discord Gateway loop
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

        # Ratio Logic
        if total_giving_keys == 0:
            ratio = 5.0 if total_getting_keys > 0 else 1.0
        else:
            ratio = total_getting_keys / total_giving_keys

        # Determine visual traits based on pricing margins
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

        # UI Formatting
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

        embed.set_footer(text="The official AoTR values | Last updated - 17/05/2026.")
        await interaction.followup.send(embed=embed)

async def setup(bot):
    await bot.add_cog(TradeCompare(bot))
