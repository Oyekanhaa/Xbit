# Betu tu jitna thumbnail private use krwga ..mere nazar me aa gya to public ho jayeg.
# Dev :- Kanha





import os
import re
import colorsys
import aiohttp
import aiofiles
from PIL import Image, ImageDraw, ImageFont, ImageFilter

from py_yt import VideosSearch
from config import YOUTUBE_IMG_URL
from AnonXMusic import app

# ══════════════════════════════════════════════════════════════
#  CACHE
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
        if v > 0.95 and s < 0.2: continue
        score = s * v
        if score > best_score:
            best_score = score
            best_color = (r, g, b)
    if best_color is None:
        return (180,180,180),(220,220,220),(100,100,100)
    r, g, b = best_color
    h, s, v = colorsys.rgb_to_hsv(r, g, b)
    base  = tuple(int(x*255) for x in colorsys.hsv_to_rgb(h, min(s*1.1,1.0), min(v,1.0)))
    light = tuple(int(x*255) for x in colorsys.hsv_to_rgb(h, max(s*0.5,0.15), min(v*1.4,1.0)))
    dark  = tuple(int(x*255) for x in colorsys.hsv_to_rgb(h, min(s*1.3,1.0), v*0.4))
    return base, light, dark


def _trim(draw, text: str, font, max_w: int) -> str:
    try:
        if draw.textlength(text, font=font) <= max_w:
            return text
        while len(text) > 1 and draw.textlength(text+"...", font=font) > max_w:
            text = text[:-1]
        return text + "..."
    except Exception:
        return text[:28] + "..."


def _clean_views_public(raw: str) -> str:
    if not raw or raw.strip().upper() == "N/A":
        return "N/A"
    cleaned = re.sub(r"\s*views?\s*", "", raw, flags=re.IGNORECASE).strip()
    cleaned = re.sub(r"([KMBT])\1+", r"\1", cleaned, flags=re.IGNORECASE)
    return f"{cleaned} views" if cleaned else "N/A"


def _make_thumb(raw_path, title, channel, duration_text, views_text, cache_path):

    try:
        art_orig = Image.open(raw_path).convert("RGB")
    except Exception:
        art_orig = Image.new("RGB", (400,400), (30,20,15))

    # ── 1. BACKGROUND ──────────────────────────────────────────
    # Blurred art + heavily darkened warm-black
    bg_blur  = art_orig.resize((W,H), Image.LANCZOS).filter(ImageFilter.GaussianBlur(50))
    dark_base = Image.new("RGB", (W,H), (8,5,3))
    bg = Image.blend(bg_blur, dark_base, alpha=0.72).convert("RGBA")

    # Vignette
    vig = Image.new("RGBA", (W,H), (0,0,0,0))
    vd  = ImageDraw.Draw(vig)
    for i in range(0, 220, 3):
        a = int(210 * (1 - i/220)**2.0)
        vd.rectangle([i, i, W-i, H-i], outline=(0,0,0,a), width=3)
    bg.alpha_composite(vig)

    # ── 2. PALETTE ─────────────────────────────────────────────
    c_base, c_light, c_dark = _extract_palette(art_orig)

    # ── 3. CARD GEOMETRY ───────────────────────────────────────
    # Card slightly smaller, centered vertically with breathing room
    CARD_L, CARD_T = 112, 135
    CARD_W, CARD_H = 400, 450      # slightly smaller, more breathing room
    CARD_R = CARD_L + CARD_W       # 520
    CARD_B = CARD_T + CARD_H       # 590
    CARD_RAD = 22

    # Dark plate: 18px padding around card
    PAD    = 18
    PL, PT = CARD_L - PAD, CARD_T - PAD
    PR, PB = CARD_R + PAD, CARD_B + PAD
    PRAD   = CARD_RAD + 12

    # ── LAYER 1: Far drop shadow (large, soft, offset) ────────
    shad1 = Image.new("RGBA", (W,H), (0,0,0,0))
    ImageDraw.Draw(shad1).rounded_rectangle(
        [PL+14, PT+20, PR+14, PB+20],
        radius=PRAD+6, fill=(0,0,0,160))
    bg.alpha_composite(shad1.filter(ImageFilter.GaussianBlur(32)))

    # ── LAYER 2: Close shadow (tighter, darker) ───────────────
    shad2 = Image.new("RGBA", (W,H), (0,0,0,0))
    ImageDraw.Draw(shad2).rounded_rectangle(
        [PL+4, PT+6, PR+4, PB+6],
        radius=PRAD+2, fill=(0,0,0,210))
    bg.alpha_composite(shad2.filter(ImageFilter.GaussianBlur(12)))

    # ── LAYER 3: Strong color glow directly around card ───────
    glow = Image.new("RGBA", (W,H), (0,0,0,0))
    gd   = ImageDraw.Draw(glow)
    for spread, alpha in [(40,25),(28,50),(18,80),(10,110),(4,140)]:
        gd.rounded_rectangle(
            [CARD_L-spread, CARD_T-spread,
             CARD_R+spread, CARD_B+spread],
            radius=CARD_RAD+spread, fill=(*c_base, alpha))
    bg.alpha_composite(glow.filter(ImageFilter.GaussianBlur(14)))

    # Dark plate
    plate_img = Image.new("RGBA", (W,H), (0,0,0,0))
    ImageDraw.Draw(plate_img).rounded_rectangle(
        [PL, PT, PR, PB], radius=PRAD, fill=(12,8,5,238))
    bg.alpha_composite(plate_img)

    # Album art
    art  = art_orig.resize((CARD_W,CARD_H), Image.LANCZOS).convert("RGBA")
    mask = Image.new("L", (CARD_W,CARD_H), 0)
    ImageDraw.Draw(mask).rounded_rectangle(
        [0, 0, CARD_W-1, CARD_H-1], radius=CARD_RAD, fill=255)
    art.putalpha(mask)
    bg.paste(art, (CARD_L, CARD_T), art)

    # White border around art
    bord = Image.new("RGBA", (W,H), (0,0,0,0))
    ImageDraw.Draw(bord).rounded_rectangle(
        [CARD_L-3, CARD_T-3, CARD_R+3, CARD_B+3],
        radius=CARD_RAD+3, outline=(255,255,255,235), width=3)
    bg.alpha_composite(bord)

    draw = ImageDraw.Draw(bg)

    # ── 4. RIGHT PANEL ─────────────────────────────────────────
    RX, RX_END = 612, 1242
    MAX_TW = RX_END - RX

    f_title = _font(FONT_BOLD,   60)
    f_sub   = _font(FONT_NORMAL, 37)
    f_time  = _font(FONT_BOLD,   31)

    # Title — vertically ~center of canvas
    TITLE_Y = 242
    draw.text((RX, TITLE_Y), _trim(draw, title, f_title, MAX_TW),
              font=f_title, fill=(255,255,255,255))

    # Artist
    ARTIST_Y = TITLE_Y + 84
    draw.text((RX, ARTIST_Y),
              _trim(draw, f"Artist: {channel}", f_sub, MAX_TW),
              font=f_sub, fill=(185,185,185,215))

    # Views
    VIEWS_Y = ARTIST_Y + 50
    draw.text((RX, VIEWS_Y),
              _trim(draw, f"Views: {views_text}", f_sub, MAX_TW),
              font=f_sub, fill=(185,185,185,215))

    # ── 5. PROGRESS BAR ────────────────────────────────────────
    BAR_Y  = VIEWS_Y + 104
    BAR_X1 = RX
    BAR_X2 = RX_END
    BAR_H  = 6

    # Grey track
    draw.rounded_rectangle(
        [BAR_X1, BAR_Y, BAR_X2, BAR_Y+BAR_H],
        radius=BAR_H//2, fill=(90,90,90,200))

    # Fill ~47%
    filled_x = BAR_X1 + int((BAR_X2-BAR_X1) * (80/169))

    # White fill
    draw.rounded_rectangle(
        [BAR_X1, BAR_Y, filled_x, BAR_Y+BAR_H],
        radius=BAR_H//2, fill=(235,235,235,255))

    # Knob
    KX, KY, KR = filled_x, BAR_Y+BAR_H//2, 10
    draw.ellipse([KX-KR+2, KY-KR+2, KX+KR+2, KY+KR+2], fill=(0,0,0,70))
    draw.ellipse([KX-KR,   KY-KR,   KX+KR,   KY+KR  ], fill=(255,255,255,255))

    # ── 6. TIME LABELS ─────────────────────────────────────────
    TIME_Y = BAR_Y + BAR_H + 16
    draw.text((BAR_X1, TIME_Y), "01:20", font=f_time, fill=(185,185,185,215))

    dur_str = duration_text if duration_text else "0:00"
    try:
        dur_w = int(draw.textlength(dur_str, font=f_time))
    except Exception:
        dur_w = 65
    draw.text((BAR_X2-dur_w, TIME_Y), dur_str, font=f_time, fill=(185,185,185,215))

    # ── 7. SAVE ────────────────────────────────────────────────
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
        results    = VideosSearch(f"https://www.youtube.com/watch?v={videoid}", limit=1)
        search     = await results.next()
        data       = search.get("result", [])[0]
        title      = re.sub(r"[\x00-\x1f\x7f]", "", data.get("title","Unknown")).strip()
        thumb_url  = data.get("thumbnails",[{}])[-1].get("url", YOUTUBE_IMG_URL).split("?")[0]
        duration   = data.get("duration") or "0:00"
        channel    = data.get("channel",{}).get("name","YouTube")
        views_raw  = data.get("viewCount",{}).get("short","N/A")
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
    except Exception:
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
    except Exception:
        result = YOUTUBE_IMG_URL

    try:
        os.remove(raw_path)
    except Exception:
        pass

    return result
