import os
import re
import aiohttp
import aiofiles
from PIL import Image, ImageDraw, ImageFont, ImageFilter

from ytSearch import VideosSearch
from config import YOUTUBE_IMG_URL

# ══════════════════════════════════════════════════════════════
#  CACHE & CONFIG
# ══════════════════════════════════════════════════════════════
CACHE_DIR = "cache"
os.makedirs(CACHE_DIR, exist_ok=True)

SCALE_FACTOR = 2.0
BASE_W, BASE_H = 1280, 720
W, H = int(BASE_W * SCALE_FACTOR), int(BASE_H * SCALE_FACTOR)

FONT_BOLD   = "AnonXMusic/assets/font2.ttf"
FONT_NORMAL = "AnonXMusic/assets/font.ttf"

def s(value):
    return int(value * SCALE_FACTOR)

def _font(path: str, size: int) -> ImageFont.FreeTypeFont:
    try:
        return ImageFont.truetype(path, s(size))
    except Exception:
        return ImageFont.load_default()

def _trim(draw, text: str, font, max_w: int) -> str:
    try:
        if draw.textlength(text, font=font) <= max_w:
            return text
        while len(text) > 1 and draw.textlength(text + "...", font=font) > max_w:
            text = text[:-1]
        return text + "..."
    except:
        return text[:25] + "..."


def _draw_rainbow_border(draw, x1, y1, x2, y2, radius, thickness):
    """
    Card ke around rainbow/holographic gradient border draw karta hai
    Exactly jaise reference image mein blue→cyan→green→yellow lining thi
    """
    import math
    # Rainbow color stops (blue → cyan → green → yellow → back)
    stops = [
        (0.00,  (80,  120, 255)),   # blue
        (0.20,  (60,  220, 255)),   # cyan
        (0.45,  (100, 255, 120)),   # green
        (0.70,  (200, 255,  60)),   # yellow-green
        (0.85,  (255, 220,  80)),   # yellow
        (1.00,  (80,  120, 255)),   # back to blue
    ]

    def lerp_color(t):
        for i in range(len(stops) - 1):
            t0, c0 = stops[i]
            t1, c1 = stops[i + 1]
            if t0 <= t <= t1:
                f = (t - t0) / (t1 - t0)
                return tuple(int(c0[j] + (c1[j] - c0[j]) * f) for j in range(3))
        return stops[-1][1]

    # Perimeter ke saath segments draw karo
    cx, cy = (x1 + x2) / 2, (y1 + y2) / 2
    w, h = x2 - x1, y2 - y1
    total_steps = 360

    for i in range(total_steps):
        t = i / total_steps
        angle = 2 * math.pi * t

        # Rounded rect boundary point calculate karo
        cos_a, sin_a = math.cos(angle), math.sin(angle)
        # Scale to ellipse then clamp to rounded rect
        ex = cx + (w / 2) * cos_a
        ey = cy + (h / 2) * sin_a

        color = lerp_color(t) + (255,)

        for th in range(thickness):
            nx = cx + ((w / 2) - th) * cos_a
            ny = cy + ((h / 2) - th) * sin_a
            draw.ellipse([nx - 2, ny - 2, nx + 2, ny + 2], fill=color)


# ══════════════════════════════════════════════════════════════
#  CORE IMAGE GENERATOR
# ══════════════════════════════════════════════════════════════
def _make_thumb(raw_path, title, channel, duration_text, views_text, cache_path):
    try:
        art_orig = Image.open(raw_path).convert("RGB")
    except:
        art_orig = Image.new("RGB", (400, 400), (20, 20, 20))

    # ── 1. BLURRED BACKGROUND ─────────────────────────────────
    # Full image stretch + heavy blur — exactly like reference screenshot
    bg = art_orig.resize((W, H), Image.LANCZOS)
    
    # Step 1: Strong gaussian blur (jaise iOS music player bg hota hai)
    bg = bg.filter(ImageFilter.GaussianBlur(radius=s(40)))
    
    # Step 2: Ek aur pass — aur smoothen karo
    bg = bg.filter(ImageFilter.GaussianBlur(radius=s(20)))
    
    bg = bg.convert("RGBA")
    
    # Step 3: Dark semi-transparent overlay — colors thodi dikh rahe ho but dim
    dark_overlay = Image.new("RGBA", (W, H), (0, 0, 0, 175))
    bg.alpha_composite(dark_overlay)

    # ── 2. IMAGE CARD SPECS ───────────────────────────────────
    IMG_W, IMG_H = s(465), s(465)
    IMG_X, IMG_Y = s(85), s(130)
    RAD = s(55)

    # ── 3. WHITE SOFT SHADOW + RAINBOW BORDER ────────────────

    # --- WHITE GLOW SHADOW (card ke peeche, pure white, soft) ---
    shadow_layer = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    white_glow_steps = [
        (s(55), 12),
        (s(40), 22),
        (s(28), 38),
        (s(18), 58),
        (s(10), 80),
        (s(5),  105),
        (s(2),  130),
    ]
    for expand, alpha in white_glow_steps:
        ImageDraw.Draw(shadow_layer).rounded_rectangle(
            [
                IMG_X - expand,
                IMG_Y - expand,
                IMG_X + IMG_W + expand,
                IMG_Y + IMG_H + expand,
            ],
            radius=RAD + expand,
            fill=(255, 255, 255, alpha),
        )
    shadow_layer = shadow_layer.filter(ImageFilter.GaussianBlur(radius=s(22)))
    bg.alpha_composite(shadow_layer)

    # ── 4. MAIN CARD ──────────────────────────────────────────
    art = art_orig.resize((IMG_W, IMG_H), Image.LANCZOS).convert("RGBA")
    mask = Image.new("L", (IMG_W, IMG_H), 0)
    ImageDraw.Draw(mask).rounded_rectangle([0, 0, IMG_W, IMG_H], radius=RAD, fill=255)
    art.putalpha(mask)
    bg.paste(art, (IMG_X, IMG_Y), art)

    # Rainbow holographic border — exactly jaise reference image mein tha
    draw = ImageDraw.Draw(bg)
    # Pehle ek thin white inner border
    draw.rounded_rectangle(
        [IMG_X + s(3), IMG_Y + s(3), IMG_X + IMG_W - s(3), IMG_Y + IMG_H - s(3)],
        radius=RAD - s(3),
        outline=(255, 255, 255, 80),
        width=s(2),
    )
    # Rainbow lining layer
    rainbow_layer = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    _draw_rainbow_border(
        ImageDraw.Draw(rainbow_layer),
        IMG_X, IMG_Y, IMG_X + IMG_W, IMG_Y + IMG_H,
        RAD, s(6)
    )
    rainbow_layer = rainbow_layer.filter(ImageFilter.GaussianBlur(radius=s(2)))
    bg.alpha_composite(rainbow_layer)
    draw = ImageDraw.Draw(bg)  # redraw after composite

    # ── 5. TEXT SECTION ───────────────────────────────────────
    TEXT_X = s(630)
    MAX_TW = W - TEXT_X - s(70)

    f_title = _font(FONT_BOLD, 85)
    f_info  = _font(FONT_NORMAL, 45)
    f_time  = _font(FONT_NORMAL, 38)
    f_water = _font(FONT_NORMAL, 30)

    draw.text((TEXT_X, s(200)), _trim(draw, title, f_title, MAX_TW), font=f_title, fill=(255, 255, 255))
    draw.text((TEXT_X, s(315)), f"Artist: {channel}", font=f_info, fill=(220, 220, 220))
    draw.text((TEXT_X, s(380)), f"Views: {views_text}", font=f_info, fill=(220, 220, 220))

    # ── 6. PROGRESS BAR ───────────────────────────────────────
    BAR_Y = s(510)
    BAR_W = W - TEXT_X - s(125)
    BAR_X1, BAR_X2 = TEXT_X, TEXT_X + BAR_W

    draw.rounded_rectangle([BAR_X1, BAR_Y, BAR_X2, BAR_Y + s(9)], radius=s(5), fill=(80, 80, 80, 180))

    fill_w = int(BAR_W * 0.45)
    draw.rounded_rectangle([BAR_X1, BAR_Y, BAR_X1 + fill_w, BAR_Y + s(9)], radius=s(5), fill=(255, 255, 255))

    knob_x = BAR_X1 + fill_w
    draw.ellipse(
        [knob_x - s(13), BAR_Y + s(4.5) - s(13), knob_x + s(13), BAR_Y + s(4.5) + s(13)],
        fill=(255, 255, 255)
    )

    draw.text((BAR_X1, BAR_Y + s(35)), "01:20", font=f_time, fill=(200, 200, 200))
    try:
        tw = int(draw.textlength(str(duration_text), font=f_time))
    except:
        tw = s(90)
    draw.text((BAR_X2 - tw, BAR_Y + s(35)), str(duration_text), font=f_time, fill=(200, 200, 200))

    # ── 7. WATERMARK ──────────────────────────────────────────
    water_text = "Dev :- Kanha"
    try:
        ww = int(draw.textlength(water_text, font=f_water))
    except:
        ww = s(120)
    draw.text((W - ww - s(50), H - s(60)), water_text, font=f_water, fill=(255, 255, 255, 140))

    # Final Save
    bg.convert("RGB").save(cache_path, "PNG")
    return cache_path


# ══════════════════════════════════════════════════════════════
#  PUBLIC API
# ══════════════════════════════════════════════════════════════
async def get_thumb(videoid: str, user_id=None) -> str:
    cache_path = os.path.join(CACHE_DIR, f"{videoid}.png")
    if os.path.exists(cache_path):
        return cache_path

    try:
        results   = VideosSearch(f"https://www.youtube.com/watch?v={videoid}", limit=1)
        search    = await results.next()
        data      = search.get("result", [])[0]

        title     = re.sub(r"[\x00-\x1f\x7f]", "", data.get("title", "Unknown")).strip()
        thumb_url = data.get("thumbnails", [{}])[-1].get("url", YOUTUBE_IMG_URL).split("?")[0]
        duration  = data.get("duration") or "0:00"
        channel   = data.get("channel", {}).get("name", "YouTube")

        views_raw  = data.get("viewCount", {}).get("text", "N/A")
        views_text = re.sub(r"\s*views?\s*", "", views_raw, flags=re.IGNORECASE).strip()
        views_text = f"{views_text} views" if views_text and views_text.upper() != "N/A" else "N/A"

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
        result = _make_thumb(raw_path, title, channel, duration, views_text, cache_path)
    except:
        result = YOUTUBE_IMG_URL

    if os.path.exists(raw_path):
        os.remove(raw_path)
    return result
