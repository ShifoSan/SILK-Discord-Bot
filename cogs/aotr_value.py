import discord
from discord import app_commands
from discord.ext import commands, tasks
import os
import json
import certifi
import aiohttp
import csv
import io
import asyncio
from motor.motor_asyncio import AsyncIOMotorClient
from google import genai
from google.genai import types

class AoTRValue(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

        # Google Sheet CSV Export Link
        self.spreadsheet_csv_url = "https://docs.google.com/spreadsheets/d/e/2PACX-1vR7naBmry1w8WlHFrtpxJ0n3XdgDj5cehW6XxTdJVDPMDivrnOefz83uuFCoYEGd028tjFQ6tcfPyBA/pub?output=csv"

        # Initialize Google GenAI
        self.api_key = os.getenv("GEMINI_API_KEY")
        if self.api_key:
            self.client = genai.Client(api_key=self.api_key)
        else:
            self.client = None
            print("Warning: GEMINI_API_KEY not found. AoTRValue module will fail.")

        # Initialize MongoDB
        self.mongo_uri = os.getenv("MONGO_URI")
        if self.mongo_uri:
            self.db_client = AsyncIOMotorClient(self.mongo_uri, tlsCAFile=certifi.where())
            self.collection = self.db_client["silk_bot"]["aotr_knowledge"]
        else:
            self.db_client = None
            self.collection = None
            print("Warning: MONGO_URI not found. AoTRValue module will fail.")

        # Emojis
        self.emperor_key = "<:EmperorKey:1505387099518537918>"
        self.scroll = "<:Scroll:1505387447218077699>"
        self.vizard_mask = "<:VizardMask:1505387338363043880>"

        # Start the background sync loop automatically
        if self.collection is not None and self.client is not None:
            self.sync_aotr_values.start()

    def cog_unload(self):
        self.sync_aotr_values.cancel()

    @tasks.loop(hours=6)
    async def sync_aotr_values(self):
        """Background task that pulls live CSV data, formats it into clean sentences, 
        and updates vector embeddings in MongoDB only if data changes."""
        print("[AoTR Sync] Starting dynamic database synchronization loop...")
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(self.spreadsheet_csv_url) as response:
                    if response.status != 200:
                        print(f"[AoTR Sync] Failed to fetch CSV from Google Sheets. Status: {response.status}")
                        return
                    csv_text = await response.text()

            # Read the CSV raw text asynchronously
            f = io.StringIO(csv_text)
            reader = csv.reader(f)

            # 1. Dynamic Header Hunting (Bulletproof against layout changes)
            headers = None
            for row_list in reader:
                # Clean the row to check for our core column names
                clean_row = [str(col).strip().lower() for col in row_list]
                
                if "item" in clean_row or "item name" in clean_row:
                    # We found the header row! Save the exact casing used in the sheet.
                    headers = [str(col).strip() for col in row_list]
                    break
            
            if not headers:
                print("[AoTR Sync] ERROR: Could not find the header row! Did the devs completely change the sheet layout or move data to a new tab?")
                return

            updated_count = 0
            skipped_count = 0

            # 2. Parse the actual data now that we mapped the headers
            for row_list in reader:
                # Zip the found headers with the current row data
                raw_row = dict(zip(headers, row_list))
                
                # Sanitize ALL keys to lowercase to prevent KeyErrors if devs add trailing spaces
                row = {k.strip().lower(): str(v).strip() for k, v in raw_row.items() if k}
                
                # Look for "item" or "item name" dynamically
                item_name = row.get("item", row.get("item name", ""))
                if not item_name:
                    continue

                category = row.get("category", "Unknown")
                rarity = row.get("rarity", "Unknown")
                demand = row.get("demand", "Unknown")
                value = row.get("value", "Unknown")
                rate_of_change = row.get("rate of change", "Stable")
                
                # Check for flexible tax column variants dynamically
                tax_str = ""
                if "tax (gems)" in row and row["tax (gems)"]:
                    tax_str = f" Tax (Gems): {row['tax (gems)']}"
                elif "tax (gold)" in row and row["tax (gold)"]:
                    tax_str = f" Tax (Gold): {row['tax (gold)']}"
                elif "tax" in row and row["tax"]:
                    tax_str = f" Tax: {row['tax']}"
                    
                if tax_str:
                    tax_str += "."

                # Reconstruct your exact custom sentenced string format perfectly
                content_sentence = f"Item: {item_name}. Category: {category}. Rarity: {rarity}. Demand: {demand}. Value: {value}. Rate Of Change: {rate_of_change}.{tax_str}"

                # Optimization Check: Query database to see if values actually changed
                existing_doc = await self.collection.find_one({"item_name": item_name})
                
                if existing_doc and existing_doc.get("content") == content_sentence:
                    skipped_count += 1
                    continue

                try:
                    # Request a fresh embedding matching your pipeline architecture
                    embedding_response = await self.client.aio.models.embed_content(
                        model="gemini-embedding-2",
                        contents=content_sentence
                    )
                    embedding = embedding_response.embeddings[0].values

                    # Overwrite or insert into MongoDB collection
                    await self.collection.update_one(
                        {"item_name": item_name},
                        {
                            "$set": {
                                "item_name": item_name,
                                "content": content_sentence,
                                "embedding": embedding
                            }
                        },
                        upsert=True
                    )
                    updated_count += 1
                    
                    # Safe artificial delay to seamlessly respect Gemini API quotas
                    await asyncio.sleep(0.5)

                except Exception as embed_error:
                    print(f"[AoTR Sync] Failed embedding sequence for {item_name}: {embed_error}")

            print(f"[AoTR Sync] Synchronization cycle finished. Updated/Inserted: {updated_count}, Unchanged/Skipped: {skipped_count}")

        except Exception as e:
            print(f"[AoTR Sync] Critical failure encountered during background loop execution: {e}")

    @sync_aotr_values.before_loop
    async def before_sync_loop(self):
        # Guarantee Discord gateway cache is populated before firing background network transactions
        await self.bot.wait_until_ready()

    @app_commands.command(name="value", description="Look up the official AoTR value for an item.")
    @app_commands.describe(item="The exact or partial name of the item to lookup")
    async def value(self, interaction: discord.Interaction, item: str):
        # 1. Critical Defer Protocol
        await interaction.response.defer()

        if self.client is None or self.collection is None:
            return await interaction.followup.send("System configuration missing (API Key or MongoDB URI).")

        try:
            # 2. Vector Search - Corrected model target parameter to fix the 404 error
            embedding_response = await self.client.aio.models.embed_content(
                model="gemini-embedding-2",
                contents=item
            )
            vector = embedding_response.embeddings[0].values

            pipeline = [
                {
                    "$vectorSearch": {
                        "index": "vector_index", # The Atlas index name belongs here
                        "path": "embedding",
                        "queryVector": vector,
                        "numCandidates": 50,     # Widen search scope to catch typos better
                        "limit": 5               # Grab top 5 chunks
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
                return await interaction.followup.send("No value data found for that item.")

            chunks = "\n\n".join([doc.get("content", "") for doc in results])

            # 3. Data Extraction - Bulletproofed Prompt
            system_prompt = (
                "You are a strict data extraction tool. You will receive a user's search query (which may contain typos) "
                "and a set of database texts.\n\n"
                "Task 1: Identify which item from the database text best matches the user's query.\n"
                "Task 2: Extract the data for THAT specific item into a JSON object with EXACTLY these keys: "
                "name, rarity, demand, rate, keys, scrolls, vizard, tax.\n\n"
                "Rules:\n"
                "- If a currency is missing, set it to 'Undefined'.\n"
                "- If the user's requested item is completely missing from the provided text, output EXACTLY this JSON: {\"error\": \"not_found\"}\n"
                "- Output ONLY raw, valid JSON. No markdown tags."
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

            # 4. JSON Parsing
            try:
                data = json.loads(response.text)
                if isinstance(data, list):
                    data = data[0] if len(data) > 0 else {}
            except json.JSONDecodeError:
                return await interaction.followup.send("⚠️ The AI failed to format the data properly. Please try again.")

            if data.get("error") == "not_found":
                return await interaction.followup.send(f"❌ I searched my database, but couldn't find any values for `{item}`. Are you sure it's spelled correctly?")

            name = data.get("name", "Unknown Item")
            rarity = data.get("rarity", "Unknown")
            demand = data.get("demand", "Unknown")
            rate = data.get("rate", "Unknown")
            keys = data.get("keys", "Undefined")
            scrolls = data.get("scrolls", "Undefined")
            vizard = data.get("vizard", "Undefined")
            tax = data.get("tax", "Unknown")

            # 5. Embed Design
            embed = discord.Embed(title=name, color=0xFF4500)
            
            avatar_url = interaction.user.display_avatar.url if interaction.user.display_avatar else None
            embed.set_author(name=interaction.user.display_name, icon_url=avatar_url)

            if interaction.guild and interaction.guild.icon:
                embed.set_thumbnail(url=interaction.guild.icon.url)

            embed.add_field(
                name="📊 Market Stats",
                value=f"**Rarity:** {rarity}\n**Demand:** {demand}/10\n**Rate:** {rate}",
                inline=True
            )

            embed.add_field(
                name="💰 Current Valuation",
                value=f"{self.emperor_key} **Keys:** {keys}\n{self.scroll} **Scrolls:** {scrolls}\n{self.vizard_mask} **Vizard:** {vizard}",
                inline=True
            )

            embed.add_field(
                name="⚖️ Trade Tax",
                value=str(tax),
                inline=True
            )

            embed.set_footer(text="The official AoTR values | Data dynamically synchronized from live sheet.")

            await interaction.followup.send(embed=embed)

        except discord.NotFound:
            pass 
        except Exception as e:
            await interaction.followup.send(f"An error occurred: {str(e)}")

async def setup(bot):
    await bot.add_cog(AoTRValue(bot))
