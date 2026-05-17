import discord
from discord import app_commands
from discord.ext import commands
import os
import json
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

    @app_commands.command(name="value", description="Look up the official AoTR value for an item.")
    @app_commands.describe(item="The exact or partial name of the item to lookup")
    async def value(self, interaction: discord.Interaction, item: str):
        # 1. Critical Defer Protocol
        await interaction.response.defer()

        if self.client is None or self.collection is None:
            return await interaction.followup.send("System configuration missing (API Key or MongoDB URI).")

        try:
            # 2. Vector Search - Widened the net to catch typos better
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
                        "numCandidates": 50, # Widen search scope
                        "limit": 5           # Grab top 5 instead of 2
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

            # We now explicitly pass the user's `item` query to the AI so it knows what to look for
            response = await self.client.aio.models.generate_content(
                model='gemini-3.1-flash-lite-preview',
                contents=f"User's Query: {item}\n\nDatabase Text:\n{chunks}",
                config=types.GenerateContentConfig(
                    response_mime_type="application/json",
                    system_instruction=system_prompt,
                    temperature=0.1 # Lower temperature makes the AI more rigid and analytical
                )
            )

            # 4. JSON Parsing
            try:
                data = json.loads(response.text)
                
                if isinstance(data, list):
                    data = data[0] if len(data) > 0 else {}
                    
            except json.JSONDecodeError:
                return await interaction.followup.send("⚠️ The AI failed to format the data properly. Please try again.")

            # Bail out cleanly if the AI couldn't find a match in the chunks
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

            embed.set_footer(text="The official AoTR values | Last updated - 17/05/2026.")

            await interaction.followup.send(embed=embed)

        except discord.NotFound:
            pass 
        except Exception as e:
            await interaction.followup.send(f"An error occurred: {str(e)}")

async def setup(bot):
    await bot.add_cog(AoTRValue(bot))
            
