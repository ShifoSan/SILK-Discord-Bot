import discord
from discord import app_commands
from discord.ext import commands
import os
import certifi
import difflib
from motor.motor_asyncio import AsyncIOMotorClient

class AoTRValue(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

        # Initialize MongoDB Targeting the new mechanical normalized collection
        self.mongo_uri = os.getenv("MONGO_URI")
        if self.mongo_uri:
            self.db_client = AsyncIOMotorClient(self.mongo_uri, tlsCAFile=certifi.where())
            self.collection = self.db_client["silk_bot"]["value_list"]
        else:
            self.db_client = None
            self.collection = None
            print("Warning: MONGO_URI not found. AoTRValue module will fail.")

        # Emojis configuration
        self.emperor_key = "<:EmperorKey:1505387099518537918>"
        self.scroll = "<:Scroll:1505387447218077699>"
        self.vizard_mask = "<:VizardMask:1505387338363043880>"

    # --- Structural Formatting Helpers ---
    def format_val(self, val, is_float=False):
        """Mechanically formats database integers into clean strings."""
        if val is None:
            return "N/A / O/C"
        
        # Handle ranges (like Artifact Taxes having Min/Max keys)
        if isinstance(val, dict) and "Min" in val and "Max" in val:
            return f"{val['Min']:,} - {val['Max']:,}"
            
        # Handle fractional strings securely (like 0.3 viz)
        if is_float:
            return f"{float(val):,.3f}".rstrip('0').rstrip('.')
            
        return f"{int(val):,}"

    def get_lvl(self, data_field, level_key):
        """Safely tunnels into multi-tier perk objects."""
        if isinstance(data_field, dict):
            return data_field.get(level_key)
        return None

    @app_commands.command(name="value", description="Look up the official AoTR value and statistics for an item.")
    @app_commands.describe(item="The exact or partial name of the item to lookup")
    async def value(self, interaction: discord.Interaction, item: str):
        # Critical Defer Protocol
        await interaction.response.defer()

        if self.collection is None:
            return await interaction.followup.send("❌ System configuration missing (MongoDB URI).")

        try:
            # 1. Zero-API Atlas Search Pipeline (Fuzzy Match Filter)
            pipeline = [
                {
                    "$search": {
                        "index": "default",
                        "text": {
                            "query": item,
                            "path": "Item",
                            "fuzzy": {
                                "maxEdits": 2,
                                "prefixLength": 1
                            }
                        }
                    }
                },
                {"$limit": 5}
            ]

            cursor = self.collection.aggregate(pipeline)
            search_results = await cursor.to_list(length=5)

            if not search_results:
                return await interaction.followup.send(f"❌ I searched the active index, but couldn't resolve any assets matching `{item}`.")

            # 2. Python Tie-Breaker Logic (Levenshtein Distance over the top 5 candidates)
            candidate_names = [doc["Item"] for doc in search_results]
            best_matches = difflib.get_close_matches(item, candidate_names, n=1, cutoff=0.0)
            best_match_name = best_matches[0]
            
            # 3. Extract the Winning Database Object
            data = next(doc for doc in search_results if doc["Item"] == best_match_name)

            # --- Extract Core Properties ---
            name = data.get("Item", "Unknown Item")
            rarity = data.get("Rarity") or "Unknown"
            demand = data.get("Demand") or "N/A"
            rate = data.get("Rate Of Change") or "Unknown"
            is_perk = data.get("Category") == "Perks"

            # Process Rate Changes for Embed Coloring
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

            # --- Embed Construction ---
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

            # --- Render Fields Mechanically ---
            if is_perk:
                # Level 0 Metrics
                k0 = self.format_val(self.get_lvl(data.get("Value_Key"), "Lvl_0"))
                s0 = self.format_val(self.get_lvl(data.get("Value_Scroll"), "Lvl_0"), is_float=True)
                v0 = self.format_val(self.get_lvl(data.get("Value_Viz"), "Lvl_0"), is_float=True)
                gold0 = self.format_val(self.get_lvl(data.get("Tax_Gold"), "Lvl_0"))

                # Level 10 Metrics
                k10 = self.format_val(self.get_lvl(data.get("Value_Key"), "Lvl_10"))
                s10 = self.format_val(self.get_lvl(data.get("Value_Scroll"), "Lvl_10"), is_float=True)
                v10 = self.format_val(self.get_lvl(data.get("Value_Viz"), "Lvl_10"), is_float=True)
                gold10 = self.format_val(self.get_lvl(data.get("Tax_Gold"), "Lvl_10"))

                embed.add_field(
                    name="🟢 LEVEL 0 VALUATION",
                    value=f"• {self.emperor_key} **Keys:** `{k0} Keys`\n• {self.scroll} **Scrolls:** `{s0}`\n• {self.vizard_mask} **Masks:** `{v0}`\n• 🪙 **Gold Tax:** `{gold0} Gold`",
                    inline=True
                )
                embed.add_field(
                    name="🔥 LEVEL 10 (MAX) VALUATION",
                    value=f"• {self.emperor_key} **Keys:** `{k10} Keys`\n• {self.scroll} **Scrolls:** `{s10}`\n• {self.vizard_mask} **Masks:** `{v10}`\n• 🪙 **Gold Tax:** `{gold10} Gold`",
                    inline=True
                )
            else:
                # Single Items
                keys = self.format_val(data.get("Value_Key"))
                scrolls = self.format_val(data.get("Value_Scroll"), is_float=True)
                vizard = self.format_val(data.get("Value_Viz"), is_float=True)

                embed.add_field(
                    name="💰 BASE MARKET VALUATION",
                    value=f"• {self.emperor_key} **Emperor Keys:** `{keys} Keys`\n• {self.scroll} **Prestige Scrolls:** `{scrolls}`\n• {self.vizard_mask} **Vizard Masks:** `{vizard}`",
                    inline=False
                )
                
                # Check properties to cleanly display only the applicable tax
                tax_val_str = ""
                if data.get("Tax_Gem") is not None:
                    tax_val_str += f"• 💎 **Gems Cost:** `{self.format_val(data.get('Tax_Gem'))} Gems`\n"
                if data.get("Tax_Gold") is not None:
                    tax_val_str += f"• 🪙 **Gold Cost:** `{self.format_val(data.get('Tax_Gold'))} Gold`\n"
                    
                if not tax_val_str:
                    tax_val_str = "• 🆓 **Cost:** `None / 0`"
                    
                embed.add_field(
                    name="⚖️ REQUIRED TRANSACTION TAX",
                    value=tax_val_str.strip(),
                    inline=False
                )

            embed.set_footer(text="The official AoTR values | Mechanically Verified")
            await interaction.followup.send(embed=embed)

        except discord.NotFound:
            pass 
        except Exception as e:
            await interaction.followup.send(f"An error occurred during mechanical lookup: {str(e)}")

async def setup(bot):
    await bot.add_cog(AoTRValue(bot))
