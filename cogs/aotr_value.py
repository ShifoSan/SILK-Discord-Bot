import discord
from discord import app_commands
from discord.ext import commands
import os
import json
import re
import certifi
from motor.motor_asyncio import AsyncIOMotorClient
from google import genai
from google.genai import types

class AoTRValue(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

        # Initialize Google GenAI
        self.api_key = os.getenv("GEMINI_API_KEY")
        if self.api_key:
            self.client = genai.Client(api_key=self.api_key)
        else:
            self.client = None
            print("Warning: GEMINI_API_KEY not found. AoTRValue module will fail.")

        # Initialize MongoDB Targeting your exact manual database route
        self.mongo_uri = os.getenv("MONGO_URI")
        if self.mongo_uri:
            self.db_client = AsyncIOMotorClient(self.mongo_uri, tlsCAFile=certifi.where())
            self.collection = self.db_client["silk_bot"]["aotr_knowledge"]
        else:
            self.db_client = None
            self.collection = None
            print("Warning: MONGO_URI not found. AoTRValue module will fail.")

        # Emojis configuration
        self.emperor_key = "<:EmperorKey:1505387099518537918>"
        self.scroll = "<:Scroll:1505387447218077699>"
        self.vizard_mask = "<:VizardMask:1505387338363043880>"

    def parse_tax_value(self, tax_val) -> int:
        """
        Robust text parser that handles integers, strings, and short-scale 
        thousands multipliers like '50k' or '2.5k', turning them into proper numbers.
        """
        if not tax_val or str(tax_val).lower() in ["unknown", "none", "0", "undefined"]:
            return 0
            
        clean_tax = str(tax_val).replace(",", "").strip().lower()
        
        # Matches digits optionally followed by 'k'
        match = re.search(r"(\d+(\.\d+)?)\s*(k)?", clean_tax)
        if match:
            base_val = float(match.group(1))
            is_k_scaled = match.group(3) is not None
            return int(base_val * 1000) if is_k_scaled else int(base_val)
            
        return 0

    @app_commands.command(name="value", description="Look up the official AoTR value and statistics for an item.")
    @app_commands.describe(item="The exact or partial name of the item to lookup")
    async def value(self, interaction: discord.Interaction, item: str):
        # 1. Critical Defer Protocol protects loop threads from timing out
        await interaction.response.defer()

        if self.client is None or self.collection is None:
            return await interaction.followup.send("System configuration missing (API Key or MongoDB URI).")

        try:
            # 2. Vector Search Pipeline with expanded boundaries
            embedding_response = await self.client.aio.models.embed_content(
                model="gemini-embedding-2",
                contents=item
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
                return await interaction.followup.send(f"❌ No asset logs found matching `{item}` inside the cluster.")

            chunks = "\n\n".join([doc.get("content", "") for doc in results])

            # 3. Data Extraction - Split prompt architecture pulling dual tax variables
            system_prompt = (
                "You are a strict data extraction tool. You will receive a user's search query and database text chunks.\n\n"
                "Task 1: Identify which item from the database text best matches the user's query regardless of spelling mistakes.\n"
                "Task 2: Extract data fields into a JSON object with EXACTLY these keys:\n"
                "name, rarity, demand, rate, keys, scrolls, vizard, gems_tax, gold_tax.\n\n"
                "Extraction Instructions:\n"
                "- Numerical fields (keys, scrolls, vizard) should hold clean base numbers if tracking exists, or 'Undefined' if absent.\n"
                "- Map 'Tax (Gems):' content verbatim to the 'gems_tax' key (e.g. '50k'). Set to '0' if missing.\n"
                "- Map 'Tax (Gold):' content verbatim to the 'gold_tax' key (e.g. '58k'). Set to '0' if missing.\n"
                "- If the item does not exist inside the text context, return EXACTLY: {\"error\": \"not_found\"}\n"
                "- Return ONLY raw, valid JSON text blocks."
            )

            response = await self.client.aio.models.generate_content(
                model='gemini-3.1-flash-lite-preview',
                contents=f"User's Query: {item}\n\nDatabase Text:\n{chunks}",
                config=types.GenerateContentConfig(
                    response_mime_type="application/json",
                    system_instruction=system_prompt,
                    temperature=0.1 
                )
            )

            # 4. JSON Validation & Guard Clauses
            try:
                data = json.loads(response.text)
                if isinstance(data, list) and len(data) > 0:
                    data = data[0]
            except json.JSONDecodeError:
                return await interaction.followup.send("⚠️ The AI failed to parse structural data cleanly. Please try again.")

            if data.get("error") == "not_found":
                return await interaction.followup.send(f"❌ I searched the active index, but couldn't resolve any assets matching `{item}`.")

            # Upgraded float parser helper to ensure decimals like 0.3 or 0.17 are preserved perfectly
            def clean_float(val) -> float | None:
                if val is None or str(val).lower() in ["undefined", "unknown", "none", "null"]:
                    return None
                try:
                    if isinstance(val, (int, float)):
                        return float(val)
                    # Extract single numbers including their decimal dots safely
                    cleaned_str = str(val).replace(",", "").strip()
                    match = re.search(r"(\d+(\.\d+)?)", cleaned_str)
                    return float(match.group(1)) if match else None
                except ValueError:
                    return None

            name = data.get("name", "Unknown Item")
            rarity = data.get("rarity", "Unknown")
            demand = data.get("demand", "Unknown")
            rate = data.get("rate", "Unknown")

            # 5. Core Mathematical Fallback System Execution
            parsed_keys = clean_float(data.get("keys"))
            keys_total = int(parsed_keys) if parsed_keys is not None else 0

            parsed_scrolls = clean_float(data.get("scrolls"))
            parsed_vizard = clean_float(data.get("vizard"))

            # Format scrolls display: strip clean integers if possible, else format to 1 decimal place
            if parsed_scrolls is not None:
                scrolls_display = f"{int(parsed_scrolls):,}" if parsed_scrolls.is_integer() else f"{parsed_scrolls:,.1f}"
            else:
                scrolls_display = f"{keys_total / 3:,.1f} *(Calculated)*"

            # Format vizard display: strip clean integers if possible, else format to 2 decimal places
            if parsed_vizard is not None:
                vizard_display = f"{int(parsed_vizard):,}" if parsed_vizard.is_integer() else f"{parsed_vizard:,.2f}"
            else:
                vizard_display = f"{keys_total / 900:,.2f} *(Calculated)*"

            # Parse split multi-currency trade tax points
            gems_tax = self.parse_tax_value(data.get("gems_tax", 0))
            gold_tax = self.parse_tax_value(data.get("gold_tax", 0))

            # Dynamically handle embed color palette shifts matching market rate trajectories
            rate_lower = str(rate).lower()
            if "rise" in rate_lower or "rising" in rate_lower or "hyped" in rate_lower:
                embed_color = 0x2ECC71  # Green
                rate_text = f"**{rate}** 📈"
            elif "drop" in rate_lower or "dropping" in rate_lower or "low" in rate_lower:
                embed_color = 0x7F8C8D  # Muted Gray
                rate_text = f"**{rate}** 📉"
            else:
                embed_color = 0xFF4500  # Default Orange
                rate_text = f"**{rate}** 🤝"

            # 6. Premium Embed Construction Space
            embed = discord.Embed(title=f"🔮 S.I.L.K. — Asset Valuation Profile", color=embed_color)
            embed.description = f"### **{name}**"
            
            avatar_url = interaction.user.display_avatar.url if interaction.user.display_avatar else None
            embed.set_author(name=interaction.user.display_name, icon_url=avatar_url)

            if interaction.guild and interaction.guild.icon:
                embed.set_thumbnail(url=interaction.guild.icon.url)

            embed.add_field(
                name="📈 MARKET PROFILE",
                value=f"• **Rarity Tier:** `{rarity}`\n• **Public Demand:** `{demand}/10`\n• **Market Rate:** {rate_text}",
                inline=False
            )

            embed.add_field(
                name="💰 BASE MARKET VALUATION",
                value=f"• {self.emperor_key} **Emperor Keys:** `{keys_total:,} Keys`\n• {self.scroll} **Prestige Scrolls:** `{scrolls_display}`\n• {self.vizard_mask} **Vizard Masks:** `{vizard_display}`",
                inline=False
            )

            embed.add_field(
                name="⚖️ REQUIRED TRANSACTION TAX",
                value=f"• 💎 **Gems Cost:** `{gems_tax:,} Gems`\n• 🪙 **Gold Cost:** `{gold_tax:,} Gold`",
                inline=False
            )

            embed.set_footer(text="The official AoTR values | Last updated - 24/05/2026.")
            await interaction.followup.send(embed=embed)

        except discord.NotFound:
            pass 
        except Exception as e:
            await interaction.followup.send(f"An error occurred: {str(e)}")

async def setup(bot):
    await bot.add_cog(AoTRValue(bot))
