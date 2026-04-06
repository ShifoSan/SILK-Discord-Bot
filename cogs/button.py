import discord
from discord import app_commands
from discord.ext import commands
import io

class ButtonView(discord.ui.View):
    def __init__(self, timeout: int, title: str, text: str, style: discord.ButtonStyle,
                 raw_file_bytes: bytes, filename: str, ephemeral_resp: bool):
        super().__init__(timeout=timeout)
        self.text = text
        self.raw_file_bytes = raw_file_bytes
        self.filename = filename
        self.ephemeral_resp = ephemeral_resp
        self.message = None # To hold the message for editing on timeout

        # Create the dynamic button
        btn = discord.ui.Button(label=title, style=style, custom_id="custom_button")
        btn.callback = self.button_callback
        self.add_item(btn)

    async def button_callback(self, interaction: discord.Interaction):
        kwargs = {
            "content": self.text,
            "ephemeral": self.ephemeral_resp
        }
        if self.raw_file_bytes:
            # Reconstruct BytesIO for every click so it can be sent multiple times
            buffer = io.BytesIO(self.raw_file_bytes)
            kwargs["file"] = discord.File(buffer, filename=self.filename)

        await interaction.response.send_message(**kwargs)

    async def on_timeout(self):
        if self.message:
            for item in self.children:
                if isinstance(item, discord.ui.Button):
                    item.disabled = True
            try:
                await self.message.edit(view=self)
            except discord.HTTPException:
                pass


class ButtonCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="button", description="Creates a custom clickable button")
    @app_commands.describe(
        title="The text displayed on the button (max 80 chars)",
        text="The text message sent when someone clicks the button",
        style="The color/style of the button",
        timeout="How long the button remains active in seconds (default 60)",
        visibility="Whether the response to clicking the button is Public or Ephemeral",
        anonymous="Send button separately without your name attached",
        file="An optional image/video/audio file sent when clicked"
    )
    @app_commands.choices(style=[
        app_commands.Choice(name="Green", value="success"),
        app_commands.Choice(name="Red", value="danger"),
        app_commands.Choice(name="Blue", value="primary"),
        app_commands.Choice(name="Grey", value="secondary"),
    ])
    @app_commands.choices(visibility=[
        app_commands.Choice(name="Public", value="public"),
        app_commands.Choice(name="Ephemeral", value="ephemeral"),
    ])
    async def button(
        self,
        interaction: discord.Interaction,
        title: str,
        text: str,
        style: app_commands.Choice[str] = None,
        timeout: int = 60,
        visibility: app_commands.Choice[str] = None,
        anonymous: bool = False,
        file: discord.Attachment = None
    ):
        if len(title) > 80:
            await interaction.response.send_message("Error: The button title cannot exceed 80 characters.", ephemeral=True)
            return

        btn_style_map = {
            "success": discord.ButtonStyle.success,
            "danger": discord.ButtonStyle.danger,
            "primary": discord.ButtonStyle.primary,
            "secondary": discord.ButtonStyle.secondary
        }

        selected_style = btn_style_map[style.value] if style else discord.ButtonStyle.success
        is_ephemeral = True
        if visibility and visibility.value == "public":
            is_ephemeral = False

        raw_bytes = None
        filename = None
        if file:
            raw_bytes = await file.read()
            filename = file.filename

        view = ButtonView(
            timeout=timeout,
            title=title,
            text=text,
            style=selected_style,
            raw_file_bytes=raw_bytes,
            filename=filename,
            ephemeral_resp=is_ephemeral
        )

        if anonymous:
            await interaction.response.send_message("Button deployed stealthily.", ephemeral=True)
            message = await interaction.channel.send(view=view)
            view.message = message
        else:
            await interaction.response.send_message(view=view)
            view.message = await interaction.original_response()

async def setup(bot):
    await bot.add_cog(ButtonCog(bot))
