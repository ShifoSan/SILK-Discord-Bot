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

    def parse_tax_string(self, tax_str: str) -> tuple[int, int]:
        """
        Robust text parser that safely extracts and evaluates currency counts from unstructured fields.
        Accurately translates abbreviations like '50k' into full numeric configurations (50000).
        """
        if not tax_str or tax_str.lower() in ["unknown", "none", "0"]:
            return 0, 0
            
        clean_tax = tax_str.replace(",", "").lower()
        gems = 0
        gold = 0
        
        # Pattern captures numbers followed optionally by a 'k' scaling factor before the tag name
        gems_match = re.search(r"(\d+)\s*(k)?\s*gem", clean_tax)
        if gems_match:
            base_val = int(gems_match.group(1))
            is_k_scaled = gems_match.group(2) is not None
            gems = base_val * 1000 if is_k_scaled else base_val
            
        gold_match = re.search(r"(\d+)\s*(k)?\s*gold", clean_tax)
        if gold_match:
            base_val = int(gold_match.group(1))
            is_k_scaled = gold_match.group(2) is not None
            gold = base_val * 1000 if is_k_scaled else base_val
            
        return gems, gold

    async def fetch_item_data(self, item_query: str) -> dict:
        """
        Employs the Version 2 RAG architecture with widened Atlas boundaries
        and analytical constraints to match misspelled items.
        """
        # Shortcut calculation evaluation check
        direct_keys = self.parse_raw_currency(item_query)
        if direct_keys is not None:
            return {
                "name": f"Raw Currency ({direct_keys:,} Keys)",
                "keys": direct_keys,
                "scrolls": direct_keys / 3,
                "vizard": direct_keys / 900,
                "gems_tax": 0,
                "gold_tax": 0,
                "error": None
            }

        if self.client is None or self.collection is None:
            return {"name": item_query, "keys": 0, "scrolls": 0, "vizard": 0, "gems_tax": 0, "gold_tax": 0, "error": "config_missing"}

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
                return {"name": item_query, "keys": 0, "scrolls": 0, "vizard": 0, "gems_tax": 0, "gold_tax": 0, "error": "not_found"}

            chunks = "\n\n".join([doc.get("content", "") for doc in results])

            # Data Extraction Prompt Strategy
            system_prompt = (
                "You are a strict data extraction tool. You will receive a user's search query (which may contain typos) "
                "and a set of database texts.\n\n"
                "Task 1: Identify which item from the database text best matches the user's query regardless of typos.\n"
                "Task 2: Extract the data for THAT specific item into a JSON object with EXACTLY these keys: "
                "name, keys, scrolls, vizard, tax.\n\n"
                "Rules:\n"
                "- Numerical fields should represent raw numbers if listed, or fallback safely to 'Undefined'.\n"
                "- Preserve the exact literal value of the tax string exactly as written in the content (e.g., '💎50k' or '🪙58k').\n"
                "- If the item is completely missing, output EXACTLY this JSON: {\"error\": \"not_found\"}\n"
                "- Output ONLY raw, valid JSON. No markdown formatting tags."
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
                return {"name": item_query, "keys": 0, "scrolls": 0, "vizard": 0, "gems_tax": 0, "gold_tax": 0, "error": "not_found"}

            def clean_int(val) -> int:
                if isinstance(val, (int, float)):
                    return int(val)
                digits = re.findall(r"\d+", str(val).replace(",", ""))
                return int(digits[0]) if digits else 0

            raw_keys = clean_int(data.get("keys", 0))
            raw_scrolls = data.get("scrolls")
            raw_vizard = data.get("vizard")
            
            final_scrolls = clean_int(raw_scrolls) if raw_scrolls and str(raw_scrolls).lower() != "undefined" else (raw_keys / 3)
            final_vizard = clean_int(raw_vizard) if raw_vizard and str(raw_vizard).lower() != "undefined" else (raw_keys / 900)

            gems_tax, gold_tax = self.parse_tax_string(str(data.get("tax", "0")))

            return {
                "name": data.get("name", item_query),
                "keys": raw_keys,
                "scrolls": final_scrolls,
                "vizard": final_vizard,
                "gems_tax": gems_tax,
                "gold_tax": gold_tax,
                "error": None
            }

        except Exception:
            return {"name": item_query, "keys": 0, "scrolls": 0, "vizard": 0, "gems_tax": 0, "gold_tax": 0, "error": "failed_to_parse"}

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
                unmatched_items.append(f"`{res['name']}` (Giving Side)")
            total_giving_keys += res["keys"]
            total_giving_scrolls += res["scrolls"]
            total_giving_vizard += res["vizard"]
            total_giving_gems_tax += res["gems_tax"]
            total_giving_gold_tax += res["gold_tax"]
            giving_breakdown.append(f"• {res['name']} — {self.emperor_key} **{res['keys']:,}** Keys")

        for res in getting_results:
            if res["error"] == "not_found":
                unmatched_items.append(f"`{res['name']}` (Getting Side)")
            total_getting_keys += res["keys"]
            total_getting_scrolls += res["scrolls"]
            total_getting_vizard += res["vizard"]
            total_getting_gems_tax += res["gems_tax"]
            total_getting_gold_tax += res["gold_tax"]
            getting_breakdown.append(f"• {res['name']} — {self.emperor_key} **{res['keys']:,}** Keys")

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
