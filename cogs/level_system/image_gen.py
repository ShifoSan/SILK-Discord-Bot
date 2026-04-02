import io
from PIL import Image, ImageDraw, ImageFont

def load_font(size, bold=False):
    font_name = "Roboto-Bold.ttf" if bold else "Roboto.ttf"
    try:
        return ImageFont.truetype(font_name, size)
    except IOError:
        return ImageFont.load_default()

def get_circular_avatar(avatar_bytes: bytes, size: int) -> Image.Image:
    try:
        # Load from raw bytes instead of relying on slow synchronous web requests
        avatar = Image.open(io.BytesIO(avatar_bytes)).convert("RGBA")
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

def generate_rank_card(user_name: str, avatar_bytes: bytes, level: int, current_xp: int, next_level_xp: int, rank: int) -> io.BytesIO:
    try:
        background = Image.open("banner.png").convert("RGBA")
    except FileNotFoundError:
        # Fallback minimalist banner if banner.png is missing
        background = Image.new("RGBA", (1800, 600), (30, 33, 36, 255))

    draw = ImageDraw.Draw(background)

    # Avatar bounding box from user: Top-Left (73, 63) Bottom-Right (474, 467.5)
    avatar_size = 401
    avatar_x, avatar_y = 73, 63
    avatar = get_circular_avatar(avatar_bytes, avatar_size)
    background.paste(avatar, (avatar_x, avatar_y), avatar)

    # Fonts
    font_name = load_font(80, bold=True)
    font_stats = load_font(50, bold=False)
    font_level = load_font(100, bold=True)
    font_rank = load_font(60, bold=True)

    # Progress Bar Background bounding box: Top-Left (53, 510) Bottom-Right (1755, 545)
    bar_x, bar_y = 53, 510
    bar_width, bar_height = 1702, 35
    draw.rounded_rectangle(
        [(bar_x, bar_y), (bar_x + bar_width, bar_y + bar_height)],
        radius=17, fill=(50, 50, 50, 255)
    )

    # Calculate previous level XP for accurate relative progress bar
    # The true total XP required to reach `level`
    prev_level_xp = 0
    for l in range(level):
        prev_level_xp += 5 * (l**2) + 50 * l + 100

    xp_in_level = max(0, current_xp - prev_level_xp)
    xp_required_for_level = next_level_xp - prev_level_xp

    # Progress Bar Fill
    progress = max(0.0, min(1.0, xp_in_level / xp_required_for_level)) if xp_required_for_level > 0 else 0
    fill_width = int(bar_width * progress)

    if fill_width > 0:
        draw.rounded_rectangle(
            [(bar_x, bar_y), (bar_x + fill_width, bar_y + bar_height)],
            radius=17, fill=(114, 137, 218, 255)
        )

    # Text Placement
    # We want text to be placed to the right of the avatar, but still well above the progress bar.
    # Text area: X from ~520 to ~1700. Y from ~63 to ~460.
    text_x_start = 520

    # User Name (Top-left of the text area)
    draw.text((text_x_start, 100), user_name, font=font_name, fill=(255, 255, 255, 255))

    # Rank (Below User Name)
    draw.text((text_x_start, 220), f"Rank: #{rank}", font=font_rank, fill=(200, 200, 200, 255))

    # Level (Top-right of the text area)
    # Using text length to right-align
    level_text = f"Level {level}"
    try:
        level_bbox = draw.textbbox((0, 0), level_text, font=font_level)
        level_width = level_bbox[2] - level_bbox[0]
    except AttributeError:
        level_width = font_level.getsize(level_text)[0]
    draw.text((1700 - level_width, 100), level_text, font=font_level, fill=(114, 137, 218, 255))

    # XP Text (Right-aligned above the progress bar)
    xp_text = f"{current_xp} / {next_level_xp} XP"
    try:
        xp_bbox = draw.textbbox((0, 0), xp_text, font=font_stats)
        xp_width = xp_bbox[2] - xp_bbox[0]
    except AttributeError:
        xp_width = font_stats.getsize(xp_text)[0]
    draw.text((1700 - xp_width, 440), xp_text, font=font_stats, fill=(200, 200, 200, 255))

    final_buffer = io.BytesIO()
    background.save(final_buffer, format="PNG")
    final_buffer.seek(0)
    return final_buffer
            
