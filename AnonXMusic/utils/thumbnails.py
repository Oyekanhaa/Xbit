import os
import re
import colorsys
import aiohttp
import aiofiles
from PIL import Image, ImageDraw, ImageFont, ImageFilter

from ytSearch import VideosSearch
# Note: config.YOUTUBE_IMG_URL is still used as fallback
from config import YOUTUBE_IMG_URL

# ══════════════════════════════════════════════════════════════
#  CACHE & CONFIG (SOLID CHOCOLATE + HEAVY GLOW + WATERMARK)
# ══════════════════════════════════════════════════════════════
CACHE_DIR = "cache"
os.makedirs(CACHE_DIR, exist_ok=True)

# Scaling for High Quality (QHD)
SCALE_FACTOR = 2.0 
BASE_W, BASE_H = 1280, 720
W, H = int(BASE_W * SCALE_FACTOR), int(BASE_H * SCALE_FACTOR)

# Font paths (Make sure these exist in your assets folder)
FONT_BOLD   = "AnonXMusic/assets/font2.ttf"
FONT_NORMAL = "AnonXMusic/assets/font.ttf"

def s(value):
    """Scaling helper function"""
    return int(value * SCALE_FACTOR)

def _font(path: str, size: int) -> ImageFont.FreeTypeFont:
    try:
        return ImageFont.truetype(path, s(size))
    except Exception:
        # Fallback to default if font is missing
        return ImageFont.load_default()

def _extract_palette(img: Image.Image):
    """
    Extracts the most vibrant color to use for the shadow glow.
    """
    small  = img.convert("RGB").resize((80, 45), Image.LANCZOS)
    pixels = list(small.getdata())
    best_color, best_score = None, -1
    for px in pixels[::2]:
        r, g, b = px[0]/255.0, px[1]/255.0, px[2]/255.0
        h, s_val, v = colorsys.rgb_to_hsv(r, g, b)
        # Avoid too dark or too desaturated colors
        if v < 0.25 or s_val < 0.35: continue
        score = s_val * v
        if score > best_score:
            best_score = score
            best_color = (r, g, b)
    if best_color is None:
        return (210, 105, 30) # Chocolate Orange Fallback
    return tuple(int(x*255) for x in best_color)

def _trim(draw, text: str, font, max_w: int) -> str:
    """Smart text trimming with ellipsis"""
    try:
        if draw.textlength(text, font=font) <= max_w:
            return text
        while len(text) > 1 and draw.textlength(text+"...", font=font) > max_w:
            text = text[:-1]
        return text + "..."
    except:
        return text[:25] + "..."

# ══════════════════════════════════════════════════════════════
#  CORE IMAGE GENERATOR (REFERENCE MATCHED + KANHA WATERMARK)
# ══════════════════════════════════════════════════════════════
def _make_thumb(raw_path, title, channel, duration_text, views_text, cache_path):
    try:
        art_orig = Image.open(raw_path).convert("RGB")
    except:
        # Fallback image if original fails
        art_orig = Image.new("RGB", (400, 400), (60, 30, 20))

    # 1. BACKGROUND (Solid Deep Chocolate Brown)
    # The reference image has a solid, non-blurred background.
    # Color R:60, G:30, B:20 is a deep chocolate.
    bg = Image.new("RGB", (W, H), (60, 30, 20))
    bg = bg.convert("RGBA")

    # Optional: Add the subtle red flare in the bottom left corner from the reference
    flare = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    ImageDraw.Draw(flare).ellipse([-s(100), H-s(200), s(300), H+s(100)], fill=(200, 50, 50, s(100)))
    bg.alpha_composite(flare.filter(ImageFilter.GaussianBlur(s(60))))

    # 2. IMAGE CARD SPECS
    IMG_W, IMG_H = s(465), s(465)
    IMG_X, IMG_Y = s(85), s(130)
    RAD = s(55)

    # --- THE HEAVY SHADOW/GLOW EFFECT ---
    # This creates the deep "pop" effect seen around the card.
    # Instead of an extracted color, the shadow is dark but heavy.
    shadow_color = (0, 0, 0, s(180)) # Dark and opaque
    shadow_layer = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    
    # Layer multiple rectangles to build depth
    for i in range(10, 50, 10):
        # Slightly offset shadow (2, 2) and bigger size
        offset = s(2) * (i//10)
        ImageDraw.Draw(shadow_layer).rounded_rectangle(
            [IMG_X - s(i) + offset, IMG_Y - s(i) + offset, IMG_X + IMG_W + s(i) + offset, IMG_Y + IMG_H + s(i) + offset], 
            radius=RAD + s(i), fill=shadow_color
        )
    
    # Apply heavy blur to the shadow layer
    bg.alpha_composite(shadow_layer.filter(ImageFilter.GaussianBlur(s(40)))) 

    # --- MAIN THUMBNAIL PASTE ---
    art = art_orig.resize((IMG_W, IMG_H), Image.LANCZOS).convert("RGBA")
    mask = Image.new("L", (IMG_W, IMG_H), 0)
    ImageDraw.Draw(mask).rounded_rectangle([0, 0, IMG_W, IMG_H], radius=RAD, fill=255)
    art.putalpha(mask)
    bg.paste(art, (IMG_X, IMG_Y), art)

    # White Border around the card
    draw = ImageDraw.Draw(bg)
    draw.rounded_rectangle([IMG_X, IMG_Y, IMG_X+IMG_W, IMG_Y+IMG_H], radius=RAD, outline=(255, 255, 255, 200), width=s(4))

    # 3. TEXT SECTION (Layout exactly matched)
    TEXT_X = s(630) # Adjusted based on reference
    MAX_TW = W - TEXT_X - s(70)

    # Reference used Bold for title, Regular for others
    f_title = _font(FONT_BOLD, 85)
    f_info  = _font(FONT_NORMAL, 45)
    f_time  = _font(FONT_NORMAL, 38) # Times are normal weight
    f_water = _font(FONT_NORMAL, 28) # Watermark font

    # Vertical positions matched to reference spacing
    draw.text((TEXT_X, s(200)), _trim(draw, title, f_title, MAX_TW), font=f_title, fill=(255, 255, 255))
    draw.text((TEXT_X, s(315)), f"Artist: {channel}", font=f_info, fill=(210, 210, 210))
    draw.text((TEXT_X, s(380)), f"Views: {views_text}", font=f_info, fill=(210, 210, 210))

    # 4. PROGRESS BAR (Matches reference exactly)
    BAR_Y = s(510)
    BAR_W = W - TEXT_X - s(125)
    BAR_X1, BAR_X2 = TEXT_X, TEXT_X + BAR_W

    # reference track is dark gray
    draw.rounded_rectangle([BAR_X1, BAR_Y, BAR_X2, BAR_Y+s(9)], radius=s(5), fill=(80, 80, 80, 200))

    # Reference progress is solid white, matching timestamps
    fill_w = int(BAR_W * 0.45) # Static 45% preview
    draw.rounded_rectangle([BAR_X1, BAR_Y, BAR_X1 + fill_w, BAR_Y+s(9)], radius=s(5), fill=(255, 255, 255))

    # Slider Knob (Solid White Circle)
    knob_x = BAR_X1 + fill_w
    draw.ellipse([knob_x-s(13), BAR_Y+s(4.5)-s(13), knob_x+s(13), BAR_Y+s(4.5)+s(13)], fill=(255, 255, 255))

    # Time Stamps (01:20 and 3:44 matching the reference look)
    draw.text((BAR_X1, BAR_Y+s(35)), "01:20", font=f_time, fill=(210, 210, 210))

    # The dynamic duration from the YouTube result
    dur_str = str(duration_text) # For reference match, this would be '3:44'
    try: tw = int(draw.textlength(dur_str, font=f_time))
    except: tw = s(90)
    draw.text((BAR_X2 - tw, BAR_Y+s(35)), dur_str, font=f_time, fill=(210, 210, 210))

    # 5. WATERMARK (Updated to Dev :- Kanha)
    water_text = "Dev :- Kanha"
    try: ww = int(draw.textlength(water_text, font=f_water))
    except: ww = s(120)
    # Positioned at bottom right with slight transparency
    draw.text((W - ww - s(50), H - s(60)), water_text, font=f_water, fill=(255, 255, 255, 130))

    # Final Save
    bg.convert("RGB").save(cache_path, "PNG")
    return cache_path

# ══════════════════════════════════════════════════════════════
#  PUBLIC API (UPGRADED FOR BETTER VIEW FORMATTING)
# ══════════════════════════════════════════════════════════════
async def get_thumb(videoid: str, user_id=None) -> str:
    cache_path = os.path.join(CACHE_DIR, f"{videoid}.png")
    if os.path.exists(cache_path):
        return cache_path

    try:
        results    = VideosSearch(f"https://www.youtube.com/watch?v={videoid}", limit=1)
        search     = await results.next()
        data       = search.get("result", [])[0]
        
        # Data Extraction
        title      = re.sub(r"[\x00-\x1f\x7f]", "", data.get("title", "Unknown Title")).strip()
        thumb_url  = data.get("thumbnails", [{}])[-1].get("url", YOUTUBE_IMG_URL).split("?")[0]
        duration   = data.get("duration") or "0:00"
        channel    = data.get("channel", {}).get("name", "YouTube")
        
        # Format views to match reference "82M views" look
        views_raw  = data.get("viewCount", {}).get("text", "N/A")
        views_text = re.sub(r"\s*views?\s*", "", views_raw, flags=re.IGNORECASE).strip()
        if views_text and views_text.upper() != "N/A":
            views_text = f"{views_text} views"
        else: views_text = "N/A"

    except Exception:
        return YOUTUBE_IMG_URL

    # Download original thumbnail
    raw_path = os.path.join(CACHE_DIR, f"raw_{videoid}.jpg")
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(thumb_url) as resp:
                if resp.status == 200:
                    async with aiofiles.open(raw_path, "wb") as f:
                        await f.write(await resp.read())
                else: return YOUTUBE_IMG_URL
    except: return YOUTUBE_IMG_URL

    # Generate the high-quality thumb
    try:
        result = _make_thumb(raw_path, title, channel, duration, views_text, cache_path)
    except: result = YOUTUBE_IMG_URL

    # Cleanup raw download
    if os.path.exists(raw_path): os.remove(raw_path)
    return result
