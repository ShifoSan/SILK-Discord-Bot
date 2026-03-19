import discord
from discord.ext import commands
import os
import asyncio
import json
import re
from google import genai
from google.genai import types

class TaskConfirmView(discord.ui.View):
    def __init__(self, task_cog, original_message: discord.Message):
        super().__init__(timeout=60.0)
        self.task_cog = task_cog
        self.original_message = original_message
        self.author_id = original_message.author.id

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user.id != self.author_id:
            await interaction.response.send_message("❌ This is not your task to confirm or cancel.", ephemeral=True)
            return False
        return True

    async def on_timeout(self):
        try:
            # We need to fetch the message to edit it
            if self.original_message.id in self.task_cog.pending_tasks:
                confirm_message = self.task_cog.pending_tasks[self.original_message.id]["confirm_message"]
                await confirm_message.edit(content="⏳ Request timed out!", view=None)
                del self.task_cog.pending_tasks[self.original_message.id]
        except discord.NotFound:
            pass
        except Exception as e:
            print(f"Error in TaskConfirmView on_timeout: {e}")

    @discord.ui.button(label="✅ Confirm", style=discord.ButtonStyle.green)
    async def confirm_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.edit_message(content="⏳ Working on it...", view=None)
        self.stop()
        if self.original_message.id in self.task_cog.pending_tasks:
            confirm_message = self.task_cog.pending_tasks[self.original_message.id]["confirm_message"]
            # Start the execution engine in the background
            asyncio.create_task(self.task_cog.execute_task(self.original_message, confirm_message))
            del self.task_cog.pending_tasks[self.original_message.id]

    @discord.ui.button(label="❌ Cancel", style=discord.ButtonStyle.red)
    async def cancel_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.edit_message(content="❌ Task cancelled.", view=None)
        self.stop()
        if self.original_message.id in self.task_cog.pending_tasks:
            del self.task_cog.pending_tasks[self.original_message.id]


class TaskAgent(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.pending_tasks = {} # original_message.id -> {"confirm_message": message}

        api_key = os.getenv("GEMINI_API_KEY")
        if api_key:
            self.client = genai.Client(api_key=api_key)
        else:
            print("Warning: GEMINI_API_KEY not found. TaskAgent will not function.")
            self.client = None

    async def analyze_and_intercept(self, message: discord.Message) -> bool:
        if not self.client:
            return False

        system_prompt = (
            "Analyze the user's message. If the user is explicitly instructing you to perform an action, "
            "create something structured (like an embed, a poll, or a script), or complete a specific assignment (like homework), "
            "output exactly 'TASK'. If the user is just having a casual conversation, asking a general knowledge question, "
            "or greeting you, output exactly 'CHAT'."
        )

        try:
            response = await asyncio.to_thread(
                self.client.models.generate_content,
                model='gemma-3-27b-it',
                contents=f"{system_prompt}\n\nUser message: {message.content}",
                # Gemma-3 doesn't support system_instruction parameter properly, must prepend.
                config=types.GenerateContentConfig(temperature=0.0)
            )

            if response.text and "TASK" in response.text.upper():
                # It's a task. Send confirmation UI.
                view = TaskConfirmView(self, message)
                confirm_message = await message.reply(
                    f"Hey {message.author.mention}! Just wanna confirm if you want me to execute this task...",
                    view=view
                )
                self.pending_tasks[message.id] = {"confirm_message": confirm_message}
                return True

        except Exception as e:
            print(f"Error in Intent Analyzer: {e}")

        return False

    def extract_json_from_markdown(self, text: str) -> str:
        # Match ```json ... ``` or ``` ... ```
        match = re.search(r"```(?:json)?\s*(.*?)\s*```", text, re.DOTALL | re.IGNORECASE)
        if match:
            return match.group(1).strip()
        return text.strip()

    async def execute_task(self, original_message: discord.Message, confirm_message: discord.Message):
        if not self.client:
            await confirm_message.edit(content="❌ API Key missing. Cannot execute task.")
            return

        system_prompt = (
            "You are a helpful AI assistant. Complete the user's task. "
            "If the user asks for a poll or an embed, you MUST output raw JSON representing a Discord embed. "
            "Do not include any other text if outputting JSON. Make sure the JSON is valid."
            "\n\nExample Embed JSON:\n"
            "```json\n"
            "{\n"
            "  \"title\": \"Example Title\",\n"
            "  \"description\": \"Example Description\",\n"
            "  \"color\": 16711680\n"
            "}\n"
            "```"
        )

        try:
            response = await asyncio.to_thread(
                self.client.models.generate_content,
                model='gemma-3-27b-it',
                contents=f"{system_prompt}\n\nUser Task: {original_message.content}"
            )

            if not response.text:
                await confirm_message.edit(content="❌ AI returned an empty response.")
                return

            output_text = response.text

            # Try to parse as JSON first (embed)
            json_str = self.extract_json_from_markdown(output_text)

            # Check if it even looks like JSON to avoid parsing casual text
            if json_str.startswith("{") and json_str.endswith("}"):
                try:
                    embed_dict = json.loads(json_str)
                    embed = discord.Embed.from_dict(embed_dict)
                    await original_message.reply(embed=embed)
                    await confirm_message.edit(content="✅ Done!")
                    return
                except json.JSONDecodeError:
                    # Fallback to sending raw text if JSON parsing fails but it looked like JSON
                    await original_message.reply(f"Failed to parse embed JSON. Raw output:\n{output_text}")
                    await confirm_message.edit(content="✅ Done! (Failed to parse embed JSON)")
                    return
                except Exception as e:
                     # e.g., discord.Embed error
                    await original_message.reply(f"Error creating embed: {e}\nRaw output:\n{output_text}")
                    await confirm_message.edit(content=f"✅ Done! (Error creating embed: {e})")
                    return

            # If not JSON, just send text
            # Ensure text is not empty and fits in 2000 chars
            if len(output_text) > 2000:
                output_text = output_text[:1996] + "..."

            await original_message.reply(output_text)
            await confirm_message.edit(content="✅ Done!")

        except Exception as e:
            await confirm_message.edit(content=f"❌ Task Execution Error: `{e}`")

async def setup(bot):
    await bot.add_cog(TaskAgent(bot))
