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
            # 2. Vector Search (gemini-embedding-2)
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
                        "numCandidates": 10,
                        "limit": 2
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
            results = await cursor.to_list(length=2)

            if not results:
                return await interaction.followup.send("No value data found for that item.")

            chunks = "\n\n".join([doc.get("content", "") for doc in results])

            # 3. Data Extraction via AI
            system_prompt = (
                "You are a strict data extraction tool. Given the provided text about item values, "
                "extract the data into a JSON object with EXACTLY these keys: "
                "name, rarity, demand, rate, keys, scrolls, vizard, tax. "
                "If a specific currency (Keys, Scrolls, or Vizard) is missing from the item's value, "
                "explicitly set its JSON value to 'Undefined'. "
                "Do NOT include markdown formatting like ```json. Output ONLY raw, valid JSON."
            )

            response = await self.client.aio.models.generate_content(
                model='gemma-4-31b-it',
                contents=chunks,
                config=types.GenerateContentConfig(
                    response_mime_type="application/json",
                    system_instruction=system_prompt
                )
            )

            # 4. JSON Parsing
            try:
                data = json.loads(response.text)
            except json.JSONDecodeError:
                return await interaction.followup.send("The AI failed to format the data properly. Please try again.")

            name = data.get("name", "Unknown Item")
            rarity = data.get("rarity", "Unknown")
            demand = data.get("demand", "Unknown")
            rate = data.get("rate", "Unknown")
            keys = data.get("keys", "Undefined")
            scrolls = data.get("scrolls", "Undefined")
            vizard = data.get("vizard", "Undefined")
            tax = data.get("tax", "Unknown")

            # 5. Embed Design
            embed = discord.Embed(title=name, color=0x2b2d31)
            embed.set_author(name="shifosan")

            if interaction.guild and interaction.guild.icon:
                embed.set_thumbnail(url=interaction.guild.icon.url)

            # Field 1
            embed.add_field(
                name="📊 Market Stats",
                value=f"**Rarity:** {rarity}\n**Demand:** {demand}/10\n**Rate:** {rate}",
                inline=True
            )

            # Field 2
            embed.add_field(
                name="💰 Current Valuation",
                value=f"{self.emperor_key} **Keys:** {keys}\n{self.scroll} **Scrolls:** {scrolls}\n{self.vizard_mask} **Vizard:** {vizard}",
                inline=True
            )

            # Field 3
            embed.add_field(
                name="⚖️ Trade Tax",
                value=str(tax),
                inline=True
            )

            embed.set_footer(text="The official AoTR values | Last updated - 17/05/2026.")

            await interaction.followup.send(embed=embed)

        except discord.NotFound:
            pass # Handle case where user deleted the thinking message
        except Exception as e:
            await interaction.followup.send(f"An error occurred: {str(e)}")

async def setup(bot):
    await bot.add_cog(AoTRValue(bot))
    
