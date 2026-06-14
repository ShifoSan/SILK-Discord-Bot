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

            # Process Rate Changes for Component Board Coloring
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

            # --- Components V2 Construction ---
            # Containers act as the structural card shell replacing traditional embeds
            container = discord.ui.Container(accent_color=discord.Color(embed_color))
            
            # Title component holding rich markdown headings
            header_content = f"### 🔮 S.I.L.K. — Asset Valuation Profile\n## **{name}**"
            container.add_item(discord.ui.TextDisplay(content=header_content))
            
            # Draw spacing separator lines to keep components uncluttered
            container.add_item(discord.ui.Separator(spacing=discord.ui.Spacing.medium))
            
            # Core market trend statistics row group
            market_section = discord.ui.Section()
            market_section.add_item(discord.ui.TextDisplay(
                content=f"### 📈 MARKET PROFILE\n"
                        f"• **Rarity Tier:** `{rarity}`\n"
                        f"• **Public Demand:** `{demand}/10`\n"
                        f"• **Market Rate:** {rate_text}"
            ))
            container.add_item(market_section)

            # --- Render Pricing Structures Mechanically ---
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

                container.add_item(discord.ui.Separator(spacing=discord.ui.Spacing.small))
                
                # Stack level profiles as partitioned visual blocks
                lvl0_section = discord.ui.Section()
                lvl0_section.add_item(discord.ui.TextDisplay(
                    content=f"### 🟢 LEVEL 0 VALUATION\n"
                            f"• {self.emperor_key} **Keys:** `{k0} Keys`\n"
                            f"• {self.scroll} **Scrolls:** `{s0}`\n"
                            f"• {self.vizard_mask} **Masks:** `{v0}`\n"
                            f"• 🪙 **Gold Tax:** `{gold0} Gold`"
                ))
                container.add_item(lvl0_section)

                container.add_item(discord.ui.Separator(spacing=discord.ui.Spacing.small))

                lvl10_section = discord.ui.Section()
                lvl10_section.add_item(discord.ui.TextDisplay(
                    content=f"### 🔥 LEVEL 10 (MAX) VALUATION\n"
                            f"• {self.emperor_key} **Keys:** `{k10} Keys`\n"
                            f"• {self.scroll} **Scrolls:** `{s10}`\n"
                            f"• {self.vizard_mask} **Masks:** `{v10}`\n"
                            f"• 🪙 **Gold Tax:** `{gold10} Gold`"
                ))
                container.add_item(lvl10_section)
            else:
                # Standard singular trade item mapping
                keys = self.format_val(data.get("Value_Key"))
                scrolls = self.format_val(data.get("Value_Scroll"), is_float=True)
                vizard = self.format_val(data.get("Value_Viz"), is_float=True)

                container.add_item(discord.ui.Separator(spacing=discord.ui.Spacing.small))

                base_section = discord.ui.Section()
                base_section.add_item(discord.ui.TextDisplay(
                    content=f"### 💰 BASE MARKET VALUATION\n"
                            f"• {self.emperor_key} **Emperor Keys:** `{keys} Keys`\n"
                            f"• {self.scroll} **Prestige Scrolls:** `{scrolls}`\n"
                            f"• {self.vizard_mask} **Vizard Masks:** `{vizard}`"
                ))
                container.add_item(base_section)
                
                # Check properties to cleanly display only the applicable tax fields
                tax_val_str = ""
                if data.get("Tax_Gem") is not None:
                    tax_val_str += f"• 💎 **Gems Cost:** `{self.format_val(data.get('Tax_Gem'))} Gems`\n"
                if data.get("Tax_Gold") is not None:
                    tax_val_str += f"• 🪙 **Gold Cost:** `{self.format_val(data.get('Tax_Gold'))} Gold`\n"
                    
                if not tax_val_str:
                    tax_val_str = "• 🆓 **Cost:** `None / 0`"
                    
                container.add_item(discord.ui.Separator(spacing=discord.ui.Spacing.small))

                tax_section = discord.ui.Section()
                tax_section.add_item(discord.ui.TextDisplay(
                    content=f"### ⚖️ REQUIRED TRANSACTION TAX\n"
                            f"{tax_val_str.strip()}"
                ))
                container.add_item(tax_section)

            # Footer representation element appended at the base of the container layout
            container.add_item(discord.ui.Separator(spacing=discord.ui.Spacing.medium))
            container.add_item(discord.ui.TextDisplay(content="*The official AoTR values | Mechanically Verified*"))

            # Bind layout tree structures to a master LayoutView component collector
            view = discord.ui.LayoutView()
            view.add_item(container)

            # Dispatch transaction response via layout engine view context maps
            await interaction.followup.send(view=view)

        except discord.NotFound:
            pass 
        except Exception as e:
            await interaction.followup.send(f"An error occurred during mechanical lookup: {str(e)}")

async def setup(bot):
    await bot.add_cog(AoTRValue(bot))
