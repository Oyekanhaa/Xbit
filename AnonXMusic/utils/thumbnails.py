import os
import re
import colorsys
import aiohttp
import aiofiles
from PIL import Image, ImageDraw, ImageFont, ImageFilter

from py_yt import VideosSearch
from config import YOUTUBE_IMG_URL

# ══════════════════════════════════════════════════════════════
#  CACHE & CONFIG
# ══════════════════════════════════════════════════════════════
CACHE_DIR = "cache"
os.makedirs(CACHE_DIR, exist_ok=True)

W, H = 1280, 720

FONT_BOLD   = "AnonXMusic/assets/font2.ttf"
FONT_NORMAL = "AnonXMusic/assets/font.ttf"

def _font(path: str, size: int) -> ImageFont.FreeTypeFont:
    try:
        return ImageFont.truetype(path, size)
    except Exception:
        return ImageFont.load_default()

def _extract_palette(img: Image.Image):
    small  = img.convert("RGB").resize((80, 45), Image.LANCZOS)
    pixels = list(small.getdata())
    best_color, best_score = None, -1
    for px in pixels[::2]:
        r, g, b = px[0]/255.0, px[1]/255.0, px[2]/255.0
        h, s, v = colorsys.rgb_to_hsv(r, g, b)
        if v < 0.25 or s < 0.35: continue
        score = s * v
        if score > best_score:
            best_score = score
            best_color = (r, g, b)
    if best_color is None:
        return (180, 180, 180)
    return tuple(int(x*255) for x in best_color)

def _trim(draw, text: str, font, max_w: int) -> str:
    try:
        if draw.textlength(text, font=font) <= max_w:
            return text
        while len(text) > 1 and draw.textlength(text+"...", font=font) > max_w:
            text = text[:-1]
        return text + "..."
    except:
        return text[:25] + "..."

def _clean_views_public(raw: str) -> str:
    if not raw or raw.strip().upper() == "N/A":
        return "N/A"
    cleaned = re.sub(r"\s*views?\s*", "", raw, flags=re.IGNORECASE).strip()
    return f"{cleaned} views" if cleaned else "N/A"

# ══════════════════════════════════════════════════════════════
#  CORE IMAGE GENERATOR (UPGRADED)
# ══════════════════════════════════════════════════════════════
def _make_thumb(raw_path, title, channel, duration_text, views_text, cache_path):
    try:
        art_orig = Image.open(raw_path).convert("RGB")
    except:
        art_orig = Image.new("RGB", (400, 400), (30, 20, 15))

    # 1. BACKGROUND (Blurred Glassmorphism)
    bg = art_orig.resize((W, H), Image.LANCZOS).filter(ImageFilter.GaussianBlur(55))
    dark_overlay = Image.new("RGBA", (W, H), (15, 12, 10, 205))
    bg = bg.convert("RGBA")
    bg.alpha_composite(dark_overlay)

    # 2. IMAGE CARD SPECS (Matching Screenshot)
    IMG_W, IMG_H = 430, 430
    IMG_X, IMG_Y = 90, 145
    RAD = 48  # High quality rounded corners

    # Neon/Glow Effect
    c_base = _extract_palette(art_orig)
    glow = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    ImageDraw.Draw(glow).rounded_rectangle(
        [IMG_X-12, IMG_Y-12, IMG_X+IMG_W+12, IMG_Y+IMG_H+12], 
        radius=RAD+5, fill=(*c_base, 50)
    )
    bg.alpha_composite(glow.filter(ImageFilter.GaussianBlur(15)))

    # Main Thumbnail Paste
    art = art_orig.resize((IMG_W, IMG_H), Image.LANCZOS).convert("RGBA")
    mask = Image.new("L", (IMG_W, IMG_H), 0)
    ImageDraw.Draw(mask).rounded_rectangle([0, 0, IMG_W, IMG_H], radius=RAD, fill=255)
    art.putalpha(mask)
    bg.paste(art, (IMG_X, IMG_Y), art)

    # White Glossy Border
    draw = ImageDraw.Draw(bg)
    draw.rounded_rectangle([IMG_X, IMG_Y, IMG_X+IMG_W, IMG_Y+IMG_H], radius=RAD, outline=(255, 255, 255, 190), width=4)

    # 3. TEXT SECTION (Right Panel Alignment)
    TEXT_X = 630
    MAX_TW = W - TEXT_X - 60

    f_title = _font(FONT_BOLD, 78)    # Big Bold Title
    f_info  = _font(FONT_NORMAL, 42)  # Artist/Views
    f_time  = _font(FONT_BOLD, 33)    # Duration

    # Render Text
    draw.text((TEXT_X, 210), _trim(draw, title, f_title, MAX_TW), font=f_title, fill=(255, 255, 255))
    draw.text((TEXT_X, 315), f"Artist: {channel}", font=f_info, fill=(195, 195, 195))
    draw.text((TEXT_X, 375), f"Views: {views_text}", font=f_info, fill=(195, 195, 195))

    # 4. PROGRESS BAR UI
    BAR_Y = 495
    BAR_W = W - TEXT_X - 110
    BAR_X1, BAR_X2 = TEXT_X, TEXT_X + BAR_W
    
    # Empty Track
    draw.rounded_rectangle([BAR_X1, BAR_Y, BAR_X2, BAR_Y+7], radius=4, fill=(85, 85, 85, 180))
    
    # Progress Fill (Approx 45%)
    fill_w = int(BAR_W * 0.45)
    draw.rounded_rectangle([BAR_X1, BAR_Y, BAR_X1 + fill_w, BAR_Y+7], radius=4, fill=(255, 255, 255))
    
    # Slider Knob (White Circle)
    knob_x = BAR_X1 + fill_w
    draw.ellipse([knob_x-10, BAR_Y-6, knob_x+10, BAR_Y+13], fill=(255, 255, 255))

    # Time Stamps
    draw.text((BAR_X1, BAR_Y+25), "01:20", font=f_time, fill=(185, 185, 185))
    
    dur_str = str(duration_text)
    try:
        tw = int(draw.textlength(dur_str, font=f_time))
    except:
        tw = 80
    draw.text((BAR_X2 - tw, BAR_Y+25), dur_str, font=f_time, fill=(185, 185, 185))

    # Save PNG
    bg.convert("RGB").save(cache_path, "PNG")
    return cache_path

# ══════════════════════════════════════════════════════════════
#  PUBLIC API FOR BOT
# ══════════════════════════════════════════════════════════════
async def get_thumb(videoid: str, user_id=None) -> str:
    cache_path = os.path.join(CACHE_DIR, f"{videoid}.png")
    if os.path.exists(cache_path):
        return cache_path

    try:
        results    = VideosSearch(f"https://www.youtube.com/watch?v={videoid}", limit=1)
        search     = await results.next()
        data       = search.get("result", [])[0]
        title      = re.sub(r"[\x00-\x1f\x7f]", "", data.get("title", "Unknown")).strip()
        thumb_url  = data.get("thumbnails", [{}])[-1].get("url", YOUTUBE_IMG_URL).split("?")[0]
        duration   = data.get("duration") or "0:00"
        channel    = data.get("channel", {}).get("name", "YouTube")
        views_raw  = data.get("viewCount", {}).get("short", "N/A")
        views_text = _clean_views_public(views_raw)
    except Exception:
        return YOUTUBE_IMG_URL

    raw_path = os.path.join(CACHE_DIR, f"raw_{videoid}.jpg")
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(thumb_url) as resp:
                if resp.status == 200:
                    async with aiofiles.open(raw_path, "wb") as f:
                        await f.write(await resp.read())
                else:
                    return YOUTUBE_IMG_URL
    except:
        return YOUTUBE_IMG_URL

    try:
        result = _make_thumb(
            raw_path      = raw_path,
            title         = title,
            channel       = channel,
            duration_text = duration,
            views_text    = views_text,
            cache_path    = cache_path,
        )
    except:
        result = YOUTUBE_IMG_URL

    if os.path.exists(raw_path):
        os.remove(raw_path)

    return result
