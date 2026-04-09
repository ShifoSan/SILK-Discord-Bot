import io
from PIL import Image, ImageDraw, ImageFont

# ==========================================
# --- MEMORY CACHING (SPEED OPTIMIZATION) ---
# ==========================================

# 1. Cache the banner into RAM on startup
try:
    BASE_BANNER = Image.open("banner.png").convert("RGBA")
except FileNotFoundError:
    BASE_BANNER = Image.new("RGBA", (1800, 600), (30, 33, 36, 255))

# 2. Dictionary to cache fonts in RAM
FONTS = {}

def get_cached_font(size, bold=False):
    font_name = "Roboto-Bold.ttf" if bold else "Roboto.ttf"
    key = f"{font_name}_{size}"
    
    # If we haven't loaded this font size yet, read from disk and cache it
    if key not in FONTS:
        try:
            FONTS[key] = ImageFont.truetype(font_name, size)
        except IOError:
            FONTS[key] = ImageFont.load_default()
            
    return FONTS[key]

# ==========================================

def get_circular_avatar(avatar_bytes: bytes, size: int) -> Image.Image:
    try:
        avatar = Image.open(io.BytesIO(avatar_bytes)).convert("RGBA")
    except Exception:
        avatar = Image.new("RGBA", (size, size), (100, 100, 100, 255))

    avatar = avatar.resize((size, size), Image.Resampling.LANCZOS)

    mask = Image.new("L", (size, size), 0)
    draw = ImageDraw.Draw(mask)
    draw.ellipse((0, 0, size, size), fill=255)

    circular_avatar = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    circular_avatar.paste(avatar, (0, 0), mask=mask)
    return circular_avatar

def generate_rank_card(user_name: str, avatar_bytes: bytes, level: int, current_xp: int, next_level_xp: int, rank: int) -> io.BytesIO:
    # Use a copy of the CACHED banner from RAM instead of reading the disk
    background = BASE_BANNER.copy()
    draw = ImageDraw.Draw(background)

    # Avatar
    avatar_size = 401
    avatar_x, avatar_y = 73, 63
    avatar = get_circular_avatar(avatar_bytes, avatar_size)
    background.paste(avatar, (avatar_x, avatar_y), avatar)

    # Use CACHED fonts from RAM
    font_name = get_cached_font(80, bold=True)
    font_stats = get_cached_font(50, bold=False)
    font_level = get_cached_font(100, bold=True)
    font_rank = get_cached_font(60, bold=True)

    # Progress Bar Background
    bar_x, bar_y = 53, 510
    bar_width, bar_height = 1702, 35
    draw.rounded_rectangle(
        [(bar_x, bar_y), (bar_x + bar_width, bar_y + bar_height)],
        radius=17, fill=(50, 50, 50, 255)
    )

    # Calculate XP math
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
    text_x_start = 520
    draw.text((text_x_start, 100), user_name, font=font_name, fill=(255, 255, 255, 255))
    draw.text((text_x_start, 220), f"Rank: #{rank}", font=font_rank, fill=(200, 200, 200, 255))

    # Level Text (Right Aligned)
    level_text = f"Level {level}"
    try:
        level_bbox = draw.textbbox((0, 0), level_text, font=font_level)
        level_width = level_bbox[2] - level_bbox[0]
    except AttributeError:
        level_width = font_level.getsize(level_text)[0]
    draw.text((1700 - level_width, 100), level_text, font=font_level, fill=(114, 137, 218, 255))

    # XP Text (Right Aligned)
    xp_text = f"{current_xp} / {next_level_xp} XP"
    try:
        xp_bbox = draw.textbbox((0, 0), xp_text, font=font_stats)
        xp_width = xp_bbox[2] - xp_bbox[0]
    except AttributeError:
        xp_width = font_stats.getsize(xp_text)[0]
    draw.text((1700 - xp_width, 440), xp_text, font=font_stats, fill=(200, 200, 200, 255))

    # Save to buffer
    final_buffer = io.BytesIO()
    background.save(final_buffer, format="PNG")
    final_buffer.seek(0)
    return final_buffer
    
