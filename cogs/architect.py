import discord
from discord import app_commands
from discord.ext import commands
import os
import asyncio
import json
from google import genai
from google.genai import types

class Architect(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.api_key = os.getenv("GEMINI_API_KEY")
        self.model_id = "gemma-3-27b-it"

        if self.api_key:
            self.client = genai.Client(api_key=self.api_key)
        else:
            self.client = None
            print("Warning: GEMINI_API_KEY not found. Architect module will fail.")

    def get_guild_context(self, guild):
        # Fetch roles and channels with IDs for precise identification
        roles = [f"{r.name} (ID: {r.id})" for r in guild.roles]
        channels = [f"{c.name} (ID: {c.id}, Type: {c.type})" for c in guild.channels]

        role_str = ", ".join(roles)
        channel_str = ", ".join(channels)
        return f"Roles: {role_str}\nChannels: {channel_str}"

    async def get_ai_plan(self, instruction, mode, guild_context):
        if not self.client:
            return None

        schema_create = """
[
  {"action": "create_category", "name": "Category Name"},
  {"action": "create_channel", "name": "channel-name", "type": "text|voice", "category": "Category Name", "restricted_roles": ["Role Name"]},
  {"action": "create_role", "name": "Role Name", "color_hex": "#FF0000"}
]
"""
        schema_delete = """
[
  {"action": "delete_channel", "name": "channel-name", "id": "12345"},
  {"action": "delete_role", "name": "Role Name", "id": "12345"}
]
"""

        system_instruction = ""
        if mode == "CREATE":
            system_instruction = (
                "You are S.I.L.K. Architect. You are in CREATION mode. "
                "You are FORBIDDEN from deleting anything. "
                "Output a strictly valid JSON list of actions based on the user's request. "
                f"Use this schema: {schema_create}. "
                "For 'restricted_roles', strictly use the names of existing roles or roles you are creating in this plan. "
                "Do not include Markdown formatting (like ```json). Return ONLY the JSON string."
            )
        else: # DELETE
            system_instruction = (
                "You are S.I.L.K. Demolisher. You are in DESTRUCTION mode. "
                "You are FORBIDDEN from creating anything. "
                "Output a strictly valid JSON list of actions to delete specific channels or roles. "
                f"Use this schema: {schema_delete}. "
                "Prefer using IDs if available in the context. "
                "Do not include Markdown formatting (like ```json). Return ONLY the JSON string."
            )

        full_prompt = (
            f"System: {system_instruction}\n"
            f"Context (Existing Infrastructure): {guild_context}\n"
            f"User Instruction: {instruction}"
        )

        try:
            # Gemma-3-27b-it supports response_mime_type for JSON enforcement
            response = self.client.models.generate_content(
                model=self.model_id,
                contents=full_prompt,
                config=types.GenerateContentConfig(
                    temperature=0.2,
                    response_mime_type="application/json"
                )
            )

            text = response.text
            # Clean up just in case
            if text.strip().startswith("```json"):
                text = text.strip()[7:]
            if text.strip().endswith("```"):
                text = text.strip()[:-3]

            return json.loads(text.strip())

        except Exception as e:
            print(f"Architect AI Error: {e}")
            return None

    @app_commands.command(name="architect", description="Build channels and roles using AI.")
    @app_commands.checks.has_permissions(administrator=True)
    async def architect(self, interaction: discord.Interaction, instruction: str):
        await interaction.response.defer(thinking=True)

        context = self.get_guild_context(interaction.guild)
        plan = await self.get_ai_plan(instruction, "CREATE", context)

        if not plan:
            await interaction.followup.send("❌ I couldn't understand the blueprints (AI Error or Invalid JSON).")
            return

        report = []
        created_categories = {} # Name -> Category Object

        for step in plan:
            try:
                action = step.get("action")
                name = step.get("name")

                if action == "create_category":
                    cat = await interaction.guild.create_category(name)
                    created_categories[name] = cat
                    report.append(f"✅ Created Category: **{name}**")
                    await asyncio.sleep(1) # Rate limit safety

                elif action == "create_role":
                    color_hex = step.get("color_hex", "#000000")
                    try:
                        color = discord.Color.from_str(color_hex)
                    except ValueError:
                        color = discord.Color.default()

                    await interaction.guild.create_role(name=name, color=color)
                    report.append(f"✅ Created Role: **{name}**")
                    await asyncio.sleep(1)

                elif action == "create_channel":
                    ctype = step.get("type", "text")
                    cat_name = step.get("category")
                    restricted_roles = step.get("restricted_roles", [])

                    category = created_categories.get(cat_name)
                    if not category and cat_name:
                        # Try to find existing category
                        category = discord.utils.get(interaction.guild.categories, name=cat_name)

                    overwrites = {}
                    if restricted_roles:
                        # Deny everyone view_channel
                        overwrites[interaction.guild.default_role] = discord.PermissionOverwrite(view_channel=False)

                        for r_name in restricted_roles:
                            # Try finding role in guild
                            role = discord.utils.get(interaction.guild.roles, name=r_name)
                            if role:
                                overwrites[role] = discord.PermissionOverwrite(view_channel=True)

                    if ctype == "voice":
                        await interaction.guild.create_voice_channel(name, category=category, overwrites=overwrites)
                    else:
                        await interaction.guild.create_text_channel(name, category=category, overwrites=overwrites)

                    report.append(f"✅ Created Channel: **{name}**")
                    await asyncio.sleep(1)

            except Exception as e:
                report.append(f"⚠️ Failed to execute '{step.get('action', 'unknown')}': {e}")

        embed = discord.Embed(
            title="🏗️ Architecture Report",
            description="\n".join(report) if report else "No actions taken.",
            color=discord.Color.green()
        )
        await interaction.followup.send(embed=embed)

    @app_commands.command(name="demolish", description="Destroy channels and roles using AI. IRREVERSIBLE.")
    @app_commands.checks.has_permissions(administrator=True)
    async def demolish(self, interaction: discord.Interaction, instruction: str):
        await interaction.response.defer(thinking=True)

        context = self.get_guild_context(interaction.guild)
        plan = await self.get_ai_plan(instruction, "DELETE", context)

        if not plan:
            await interaction.followup.send("❌ I couldn't understand the blueprints (AI Error or Invalid JSON).")
            return

        report = []

        for step in plan:
            try:
                action = step.get("action")
                name = step.get("name")
                obj_id = step.get("id")

                target = None

                if action == "delete_channel":
                    if obj_id:
                        try:
                            target = interaction.guild.get_channel(int(obj_id))
                        except ValueError:
                            pass
                    if not target and name:
                        target = discord.utils.get(interaction.guild.channels, name=name)

                    if target:
                        await target.delete()
                        report.append(f"💥 Demolished Channel: **{target.name}**")
                    else:
                        report.append(f"⚠️ Could not find channel: {name} (ID: {obj_id})")
                    await asyncio.sleep(1)

                elif action == "delete_role":
                    if obj_id:
                        try:
                            target = interaction.guild.get_role(int(obj_id))
                        except ValueError:
                            pass
                    if not target and name:
                        target = discord.utils.get(interaction.guild.roles, name=name)

                    if target:
                        try:
                            await target.delete()
                            report.append(f"💥 Demolished Role: **{target.name}**")
                        except discord.Forbidden:
                             report.append(f"⛔ Permission Denied: Cannot delete role **{target.name}** (Hierarchy issue).")
                    else:
                        report.append(f"⚠️ Could not find role: {name} (ID: {obj_id})")
                    await asyncio.sleep(1)

            except Exception as e:
                report.append(f"⚠️ Error executing '{step.get('action', 'unknown')}': {e}")

        embed = discord.Embed(
            title="🚧 Demolition Report",
            description="\n".join(report) if report else "No actions taken.",
            color=discord.Color.red()
        )
        await interaction.followup.send(embed=embed)

async def setup(bot):
    await bot.add_cog(Architect(bot))
