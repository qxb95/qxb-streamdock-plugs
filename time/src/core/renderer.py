# src/core/renderer.py
import datetime
import math
import os
from PIL import Image, ImageDraw, ImageFont

_BG_CACHE = None
_BG_IMAGE = None
_FONT_CACHE = None


def _load_background(size: int):
    global _BG_IMAGE
    if _BG_IMAGE is not None and _BG_IMAGE.size == (size, size):
        return _BG_IMAGE

    possible_paths = [
        os.path.join(os.path.dirname(__file__), "..", "..", "background.png"),
        "background.png",
        os.path.join("debug_output", "background.png"),
    ]
    for path in possible_paths:
        if os.path.exists(path):
            try:
                img = Image.open(path).convert("RGB")
                img = img.resize((size, size), Image.Resampling.LANCZOS)
                _BG_IMAGE = img
                return img
            except Exception:
                pass
    return None


def _get_font(size: int):
    global _FONT_CACHE
    if _FONT_CACHE is not None:
        return _FONT_CACHE
    try:
        font = ImageFont.truetype("arial.ttf", int(size * 0.12))
    except:
        try:
            font = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", int(size * 0.12))
        except:
            font = ImageFont.load_default()
    _FONT_CACHE = font
    return font


def render_clock(canvas_size: int = 500, dial_size: int = 400) -> Image.Image:
    global _BG_CACHE

    now = datetime.datetime.now()
    hour = now.hour % 12
    minute = now.minute
    second = now.second

    center = canvas_size // 2
    radius = dial_size // 2 - 8
    cache_key = (canvas_size, dial_size)

    if _BG_CACHE is not None and getattr(_BG_CACHE, '_cache_key', None) != cache_key:
        _BG_CACHE = None

    if _BG_CACHE is None:
        bg_img = _load_background(canvas_size)
        if bg_img is not None:
            bg = bg_img.copy()
        else:
            bg = Image.new("RGB", (canvas_size, canvas_size), color=(10, 10, 20))
            bg_draw = ImageDraw.Draw(bg)
            max_radius = canvas_size // 2
            for r in range(max_radius, 0, -5):
                ratio = r / max_radius
                red = int(10 + 30 * (1 - ratio))
                green = int(10 + 60 * (1 - ratio))
                blue = int(25 + 105 * (1 - ratio))
                bg_draw.ellipse(
                    (center - r, center - r, center + r, center + r),
                    fill=(red, green, blue),
                    outline=None
                )

        bg_draw = ImageDraw.Draw(bg)

        # 外圈发光
        for r in range(radius, radius - 6, -2):
            color = (180, 180, 220) if (radius - r) % 4 == 0 else (100, 100, 150)
            bg_draw.ellipse(
                (center - r, center - r, center + r, center + r),
                outline=color,
                width=2
            )

        # 刻度
        for i in range(60):
            angle = math.radians(i * 6 - 90)
            is_main = (i % 5 == 0)
            length = int(radius * 0.12) if is_main else int(radius * 0.07)
            width = 3 if is_main else 1
            outer_x = center + (radius - 3) * math.cos(angle)
            outer_y = center + (radius - 3) * math.sin(angle)
            inner_x = center + (radius - 3 - length) * math.cos(angle)
            inner_y = center + (radius - 3 - length) * math.sin(angle)
            if is_main:
                bg_draw.line((outer_x, outer_y, inner_x, inner_y), fill=(255, 255, 255), width=width)
                glow_x = center + (radius - 1) * math.cos(angle)
                glow_y = center + (radius - 1) * math.sin(angle)
                bg_draw.line((outer_x, outer_y, glow_x, glow_y), fill=(200, 200, 255), width=4)
            else:
                bg_draw.line((outer_x, outer_y, inner_x, inner_y), fill=(180, 180, 200), width=width)

        _BG_CACHE = bg
        _BG_CACHE._cache_key = cache_key

    img = _BG_CACHE.copy()
    draw = ImageDraw.Draw(img)

    # 指针
    hour_angle = math.radians((hour + minute / 60) * 30 - 90)
    min_angle = math.radians(minute * 6 - 90)
    sec_angle = math.radians(second * 6 - 90)

    hour_len = radius * 0.45
    min_len = radius * 0.65
    sec_len = radius * 0.75

    # 时针
    hour_x = center + hour_len * math.cos(hour_angle)
    hour_y = center + hour_len * math.sin(hour_angle)
    draw.line((center, center, hour_x, hour_y), fill=(200, 160, 60), width=10)
    draw.line((center - 1, center - 1, hour_x - 1, hour_y - 1), fill=(255, 215, 100), width=5)

    # 分针
    min_x = center + min_len * math.cos(min_angle)
    min_y = center + min_len * math.sin(min_angle)
    draw.line((center, center, min_x, min_y), fill=(180, 180, 210), width=6)
    draw.line((center - 1, center - 1, min_x - 1, min_y - 1), fill=(230, 230, 255), width=3)

    # 秒针
    sec_x = center + sec_len * math.cos(sec_angle)
    sec_y = center + sec_len * math.sin(sec_angle)
    tail_len = int(radius * 0.1)
    tail_x = center - tail_len * math.cos(sec_angle)
    tail_y = center - tail_len * math.sin(sec_angle)
    draw.line((tail_x, tail_y, sec_x, sec_y), fill=(255, 60, 60), width=4)
    draw.ellipse((sec_x - 4, sec_y - 4, sec_x + 4, sec_y + 4), fill=(255, 120, 120))

    # 中心装饰
    draw.ellipse((center - 12, center - 12, center + 12, center + 12), outline=(200, 200, 220), width=2)
    for r in range(10, 0, -2):
        color_val = int(200 - (10 - r) * 20)
        draw.ellipse((center - r, center - r, center + r, center + r), fill=(color_val, color_val, 255))
    draw.ellipse((center - 3, center - 6, center + 2, center - 2), fill=(255, 255, 255), width=0)

    return img