import io
from PIL import Image, ImageDraw, ImageFont
import requests

def load_font(size, bold=False):
    font_name = "Roboto-Bold.ttf" if bold else "Roboto.ttf"
    try:
        return ImageFont.truetype(font_name, size)
    except IOError:
        return ImageFont.load_default()

def get_circular_avatar(avatar_url: str, size: int) -> Image.Image:
    try:
        response = requests.get(avatar_url, timeout=5)
        response.raise_for_status()
        avatar = Image.open(io.BytesIO(response.content)).convert("RGBA")
    except Exception:
        # Create a default solid color avatar if fetching fails
        avatar = Image.new("RGBA", (size, size), (100, 100, 100, 255))

    avatar = avatar.resize((size, size), Image.Resampling.LANCZOS)

    # Create circular mask
    mask = Image.new("L", (size, size), 0)
    draw = ImageDraw.Draw(mask)
    draw.ellipse((0, 0, size, size), fill=255)

    circular_avatar = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    circular_avatar.paste(avatar, (0, 0), mask=mask)
    return circular_avatar

def generate_rank_card(user_name: str, avatar_url: str, level: int, current_xp: int, next_level_xp: int, rank: int) -> io.BytesIO:
    try:
        background = Image.open("banner.png").convert("RGBA")
    except FileNotFoundError:
        # Fallback minimalist banner if banner.png is missing
        background = Image.new("RGBA", (800, 250), (30, 33, 36, 255))

    draw = ImageDraw.Draw(background)

    # Avatar
    avatar_size = 160
    avatar_x, avatar_y = 40, 45
    avatar = get_circular_avatar(avatar_url, avatar_size)
    background.paste(avatar, (avatar_x, avatar_y), avatar)

    # Fonts
    font_name = load_font(45, bold=True)
    font_stats = load_font(30, bold=False)
    font_level = load_font(60, bold=True)
    font_rank = load_font(30, bold=True)

    # User Name
    text_x = 230
    draw.text((text_x, 60), user_name, font=font_name, fill=(255, 255, 255, 255))

    # Rank & Level
    draw.text((text_x, 120), f"Rank: #{rank}", font=font_rank, fill=(200, 200, 200, 255))
    draw.text((600, 50), f"Level {level}", font=font_level, fill=(114, 137, 218, 255))

    # Progress Bar Background
    bar_x, bar_y = 230, 180
    bar_width, bar_height = 520, 25
    draw.rounded_rectangle(
        [(bar_x, bar_y), (bar_x + bar_width, bar_y + bar_height)],
        radius=12, fill=(50, 50, 50, 255)
    )

    # Calculate previous level XP for accurate relative progress bar
    prev_level_xp = 5 * ((level - 1)**2) + 50 * (level - 1) + 100 if level > 0 else 0
    xp_in_level = max(0, current_xp - prev_level_xp)
    xp_required_for_level = next_level_xp - prev_level_xp

    # Progress Bar Fill
    progress = max(0.0, min(1.0, xp_in_level / xp_required_for_level)) if xp_required_for_level > 0 else 0
    fill_width = int(bar_width * progress)

    if fill_width > 0:
        draw.rounded_rectangle(
            [(bar_x, bar_y), (bar_x + fill_width, bar_y + bar_height)],
            radius=12, fill=(114, 137, 218, 255)
        )

    # XP Text
    xp_text = f"{current_xp} / {next_level_xp} XP"
    draw.text((bar_x + bar_width - 150, bar_y - 35), xp_text, font=font_stats, fill=(200, 200, 200, 255))

    final_buffer = io.BytesIO()
    background.save(final_buffer, format="PNG")
    final_buffer.seek(0)
    return final_buffer
