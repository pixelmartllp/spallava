"""Creative renderer.

Composites a background, the quote typography, brand ornaments and the logo
into a finished post image. Four layouts keep the daily batch varied while
staying recognisably the same brand.
"""

from __future__ import annotations

import math
import random
from pathlib import Path
from typing import Any, Iterable

from PIL import Image, ImageDraw, ImageFilter, ImageFont

from . import assets, brand

LAYOUTS = ("paper_quote", "quote_left", "arch_card", "center_overlay", "soft_band")

# Layouts that assume a photograph fills the frame. On a plain paper
# background they leave an obviously empty half, so they are only chosen when
# a real background photo is available.
PHOTO_LAYOUTS = ("quote_left", "center_overlay", "soft_band")
PAPER_LAYOUTS = ("paper_quote", "arch_card")

_font_cache: dict[tuple[str, int], ImageFont.FreeTypeFont] = {}


# --------------------------------------------------------------------------
# Typography helpers
# --------------------------------------------------------------------------

def get_font(role: str, size: int) -> ImageFont.FreeTypeFont:
    key = (role, size)
    if key not in _font_cache:
        _font_cache[key] = ImageFont.truetype(brand.font_path(role), size)
    return _font_cache[key]


def smart_quotes(text: str) -> str:
    """Straight quotes read as cheap on a serif headline - curl them."""
    out: list[str] = []
    for i, ch in enumerate(text):
        if ch == "'":
            prev = text[i - 1] if i else ""
            out.append("’" if prev.isalnum() else "‘")
        elif ch == '"':
            prev = text[i - 1] if i else ""
            out.append("”" if prev.isalnum() or prev in ".,!?" else "“")
        else:
            out.append(ch)
    return "".join(out)


def wrap_text(text: str, font: ImageFont.FreeTypeFont, max_width: float) -> list[str]:
    """Greedy word wrap that also honours explicit newlines in the source."""
    lines: list[str] = []
    for paragraph in text.split("\n"):
        words = paragraph.split()
        if not words:
            lines.append("")
            continue
        current = words[0]
        for word in words[1:]:
            candidate = f"{current} {word}"
            if font.getlength(candidate) <= max_width:
                current = candidate
            else:
                lines.append(current)
                current = word
        lines.append(current)
    return lines


def fit_text(text: str, role: str, max_width: float, max_height: float,
             max_size: int, min_size: int = 20,
             line_spacing: float = 1.14) -> tuple[ImageFont.FreeTypeFont, list[str]]:
    """Largest font size at which the wrapped text still fits the box."""
    best: tuple[ImageFont.FreeTypeFont, list[str]] | None = None
    low, high = min_size, max_size

    while low <= high:
        mid = (low + high) // 2
        font = get_font(role, mid)
        lines = wrap_text(text, font, max_width)
        widest = max((font.getlength(line) for line in lines), default=0)
        height = len(lines) * mid * line_spacing

        if widest <= max_width and height <= max_height:
            best = (font, lines)
            low = mid + 1
        else:
            high = mid - 1

    if best is None:
        font = get_font(role, min_size)
        best = (font, wrap_text(text, font, max_width))
    return best


def draw_lines(draw: ImageDraw.ImageDraw, lines: Iterable[str],
               font: ImageFont.FreeTypeFont, x: float, y: float,
               fill: tuple, line_spacing: float = 1.14,
               align: str = "left", box_width: float = 0.0) -> float:
    """Draw wrapped lines and return the y coordinate just past the block."""
    step = font.size * line_spacing
    for line in lines:
        if line:
            if align == "center":
                draw.text((x + box_width / 2, y), line, font=font, fill=fill, anchor="ma")
            elif align == "right":
                draw.text((x + box_width, y), line, font=font, fill=fill, anchor="ra")
            else:
                draw.text((x, y), line, font=font, fill=fill)
        y += step
    return y


def draw_tracked(draw: ImageDraw.ImageDraw, text: str,
                 font: ImageFont.FreeTypeFont, x: float, y: float,
                 fill: tuple, tracking: float = 0.0,
                 centre_on: float | None = None) -> float:
    """Letter-spaced text - used for the small brand strap lines."""
    total = sum(font.getlength(ch) + tracking for ch in text) - tracking
    start = x if centre_on is None else centre_on - total / 2
    for ch in text:
        draw.text((start, y), ch, font=font, fill=fill)
        start += font.getlength(ch) + tracking
    return total


# --------------------------------------------------------------------------
# Ornaments
# --------------------------------------------------------------------------

def _leaf(length: int, colour: tuple, angle: float) -> Image.Image:
    """A single pointed leaf, drawn at 4x then rotated and downsampled.

    A plain ellipse reads as a chevron at this size, so the outline tapers to
    a point at both ends instead.
    """
    scale = 4
    pad = max(2, length) * scale
    canvas = Image.new("RGBA", (pad * 2, pad * 2), (0, 0, 0, 0))
    draw = ImageDraw.Draw(canvas)
    cx, cy = pad, pad
    half = length * scale * 0.5
    thick = length * scale * 0.26

    upper, lower = [], []
    steps = 24
    for i in range(steps + 1):
        t = -1 + 2 * i / steps
        offset = thick * (1 - t * t) ** 0.75
        upper.append((cx + t * half, cy - offset))
        lower.append((cx + t * half, cy + offset))
    draw.polygon(upper + list(reversed(lower)), fill=colour)

    canvas = canvas.rotate(angle, resample=Image.BICUBIC)
    return canvas.resize((pad * 2 // scale, pad * 2 // scale), Image.LANCZOS)


def draw_flourish(base: Image.Image, cx: float, cy: float, width: float,
                  colour: tuple = brand.GOLD,
                  dot_colour: tuple = brand.ROSE) -> None:
    """The leafy sprig ornament used above headlines."""
    layer = Image.new("RGBA", base.size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(layer)
    half = width / 2
    stroke = max(1, int(width / 110))

    for side in (-1, 1):
        # gently curved stem
        x0, x1 = cx + side * width * 0.06, cx + side * half
        draw.arc((min(x0, x1), cy - width * 0.10, max(x0, x1), cy + width * 0.10),
                 start=180 if side < 0 else 0,
                 end=360 if side < 0 else 180,
                 fill=colour + (255,), width=stroke)
        for i in range(3):
            t = 0.22 + i * 0.24
            lx = cx + side * (width * 0.08 + half * t)
            ly = cy - width * 0.045 - i * width * 0.006
            leaf_len = int(width * (0.115 - i * 0.018))
            if leaf_len < 3:
                continue
            leaf = _leaf(leaf_len, colour + (235,), 34 * -side)
            layer.alpha_composite(leaf, (int(lx - leaf.width / 2),
                                         int(ly - leaf.height / 2)))
            leaf_dn = _leaf(leaf_len, colour + (200,), -22 * -side)
            layer.alpha_composite(leaf_dn, (int(lx - leaf_dn.width / 2),
                                            int(ly + width * 0.055 - leaf_dn.height / 2)))

    r = max(2, width * 0.018)
    draw.ellipse((cx - r, cy - r, cx + r, cy + r), fill=dot_colour + (255,))
    base.alpha_composite(layer)


def draw_heart(base: Image.Image, cx: float, cy: float, size: float,
               colour: tuple = brand.GOLD, outline_only: bool = True) -> None:
    """Small parametric heart - the accent mark between divider rules."""
    layer = Image.new("RGBA", base.size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(layer)
    points = []
    for i in range(73):
        t = i * (2 * math.pi / 72)
        x = 16 * math.sin(t) ** 3
        y = (13 * math.cos(t) - 5 * math.cos(2 * t)
             - 2 * math.cos(3 * t) - math.cos(4 * t))
        points.append((cx + x * size / 32, cy - y * size / 32))
    if outline_only:
        draw.line(points, fill=colour + (255,), width=max(1, int(size / 14)), joint="curve")
    else:
        draw.polygon(points, fill=colour + (255,))
    base.alpha_composite(layer)


def draw_divider(base: Image.Image, cx: float, cy: float, width: float,
                 colour: tuple = brand.GOLD, with_heart: bool = True) -> None:
    """Two thin rules with a heart between them."""
    layer = Image.new("RGBA", base.size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(layer)
    gap = width * 0.10 if with_heart else 0
    stroke = max(1, int(width / 220))
    draw.line((cx - width / 2, cy, cx - gap, cy), fill=colour + (210,), width=stroke)
    draw.line((cx + gap, cy, cx + width / 2, cy), fill=colour + (210,), width=stroke)
    base.alpha_composite(layer)
    if with_heart:
        draw_heart(base, cx, cy, width * 0.12, colour)


def draw_swash(base: Image.Image, x: float, y: float, width: float,
               colour: tuple = brand.GOLD) -> None:
    """The hand-drawn looking gold underline beneath an accent line."""
    layer = Image.new("RGBA", base.size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(layer)
    stroke = max(2, int(width / 150))
    draw.arc((x, y - width * 0.10, x + width, y + width * 0.10),
             start=200, end=340, fill=colour + (255,), width=stroke)
    draw.arc((x + width * 0.16, y - width * 0.05, x + width * 0.98, y + width * 0.13),
             start=205, end=330, fill=colour + (170,), width=max(1, stroke - 1))
    base.alpha_composite(layer)


# --------------------------------------------------------------------------
# Panels and scrims
# --------------------------------------------------------------------------

def rounded_card(size: tuple[int, int], radius: int, fill: tuple,
                 arch: bool = False) -> Image.Image:
    """A cream/white panel. `arch` makes the top a full semicircle."""
    card = Image.new("RGBA", size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(card)
    width, height = size
    if arch:
        top_r = width // 2
        draw.pieslice((0, 0, width, width), 180, 360, fill=fill + (255,))
        # Square top corners on the body, or they notch into the semicircle.
        draw.rounded_rectangle((0, top_r, width, height), radius=radius,
                               fill=fill + (255,),
                               corners=(False, False, True, True))
    else:
        draw.rounded_rectangle((0, 0, width, height), radius=radius,
                               fill=fill + (255,))
    return card


def paste_with_shadow(base: Image.Image, card: Image.Image, xy: tuple[int, int],
                      blur: int = 22, opacity: int = 55,
                      offset: tuple[int, int] = (0, 10)) -> None:
    shadow = Image.new("RGBA", base.size, (0, 0, 0, 0))
    silhouette = Image.new("RGBA", card.size, (60, 40, 32, opacity))
    silhouette.putalpha(card.split()[3].point(lambda v: int(v * opacity / 255)))
    shadow.alpha_composite(silhouette, (xy[0] + offset[0], xy[1] + offset[1]))
    base.alpha_composite(shadow.filter(ImageFilter.GaussianBlur(blur)))
    base.alpha_composite(card, xy)


def horizontal_scrim(size: tuple[int, int], colour: tuple,
                     strength: float = 0.92, extent: float = 0.72,
                     from_left: bool = True) -> Image.Image:
    """Fade a flat colour in from one edge so text stays readable on a photo."""
    width, height = size
    ramp = Image.new("L", (256, 1))
    draw = ImageDraw.Draw(ramp)
    for i in range(256):
        t = i / 255
        if t < extent:
            local = t / extent
            value = int(255 * strength * (1 - local) ** 1.6)
        else:
            value = 0
        draw.point((i, 0), fill=value)
    if not from_left:
        ramp = ramp.transpose(Image.FLIP_LEFT_RIGHT)
    mask = ramp.resize((width, height), Image.BICUBIC)
    layer = Image.new("RGBA", size, colour + (0,))
    layer.putalpha(mask)
    return layer


def vertical_scrim(size: tuple[int, int], colour: tuple,
                   strength: float = 0.75, extent: float = 0.55,
                   from_top: bool = False) -> Image.Image:
    width, height = size
    ramp = Image.new("L", (1, 256))
    draw = ImageDraw.Draw(ramp)
    for i in range(256):
        t = i / 255 if from_top else 1 - i / 255
        if t < extent:
            local = t / extent
            value = int(255 * strength * (1 - local) ** 1.5)
        else:
            value = 0
        draw.point((0, i), fill=value)
    mask = ramp.resize((width, height), Image.BICUBIC)
    layer = Image.new("RGBA", size, colour + (0,))
    layer.putalpha(mask)
    return layer


# --------------------------------------------------------------------------
# Branding block
# --------------------------------------------------------------------------

def region_brightness(base: Image.Image, box: tuple[int, int, int, int]) -> float:
    """Mean luminance (0-255) of a region, used to pick logo/text colour."""
    left, top, right, bottom = box
    left = max(0, min(base.width - 1, int(left)))
    right = max(left + 1, min(base.width, int(right)))
    top = max(0, min(base.height - 1, int(top)))
    bottom = max(top + 1, min(base.height, int(bottom)))
    crop = base.convert("RGB").crop((left, top, right, bottom))
    crop = crop.resize((24, 24), Image.BILINEAR).convert("L")
    pixels = list(crop.getdata())
    return sum(pixels) / len(pixels)


def draw_brand_footer(base: Image.Image, centre_x: float,
                      top_y: float, bottom_y: float,
                      with_name: bool = False,
                      max_logo_width: float = 0.0) -> None:
    """Logo plus strapline, fitted inside the band [top_y, bottom_y].

    The logo is placed bare - no white card. Whether the full-colour mark or
    the cream monochrome one is used is decided from the actual brightness of
    the pixels behind it, so it reads correctly on paper stock and on a dark
    photograph alike.
    """
    width = base.width
    region_h = max(1.0, bottom_y - top_y)

    strap_size = max(13, int(width / 38))
    strap_font = get_font("body", strap_size)
    strap_block = strap_size * 1.9
    gap = region_h * 0.10

    logo_box_h = max(10.0, region_h - strap_block - gap)
    logo_box_w = max_logo_width or width * 0.34

    probe = assets.load_logo_fit(int(logo_box_w), int(logo_box_h))
    x = int(centre_x - probe.width / 2)
    y = int(top_y + (logo_box_h - probe.height) / 2)

    dark = region_brightness(base, (x, y, x + probe.width,
                                    int(bottom_y))) < 140
    if dark:
        logo = assets.load_logo_mono(int(logo_box_w), int(logo_box_h), brand.CREAM)
        text_colour = brand.CREAM
    else:
        logo = probe
        text_colour = brand.BROWN_SOFT

    base.alpha_composite(logo, (x, y))

    text = (f"{brand.BRAND_NAME}   |   {brand.BRAND_TAGLINE}"
            if with_name else brand.BRAND_TAGLINE)
    draw = ImageDraw.Draw(base)
    draw_tracked(draw, text, strap_font, 0, y + logo.height + gap,
                 text_colour + (255,), tracking=strap_size * 0.15,
                 centre_on=centre_x)


def draw_frame(base: Image.Image, colour: tuple = brand.GOLD,
               inset_ratio: float = 0.050, opacity: int = 150) -> None:
    """A thin double keyline just inside the canvas edge.

    Costs almost nothing and does more for a 'printed, considered' feel than
    any amount of background detail.
    """
    width, height = base.size
    layer = Image.new("RGBA", base.size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(layer)
    stroke = max(1, int(width / 700))

    outer = int(width * inset_ratio)
    inner = outer + int(width * 0.011)
    draw.rectangle((outer, outer, width - outer, height - outer),
                   outline=colour + (opacity,), width=stroke)
    draw.rectangle((inner, inner, width - inner, height - inner),
                   outline=colour + (int(opacity * 0.45),), width=stroke)
    base.alpha_composite(layer)


# --------------------------------------------------------------------------
# Layouts
# --------------------------------------------------------------------------

def _layout_paper_quote(canvas: Image.Image, entry: dict[str, Any],
                        rng: random.Random, has_photo: bool) -> None:
    """Centred quote on textured stock, inside a gold keyline.

    This is the layout for days with no background photo - it reads as a
    printed card rather than as a photo layout missing its photo.
    """
    width, height = canvas.size
    if has_photo:
        canvas.alpha_composite(Image.new("RGBA", (width, height),
                                         brand.CREAM_LIGHT + (232,)))
    draw_frame(canvas)

    draw = ImageDraw.Draw(canvas)
    text_w = width * 0.74
    left = (width - text_w) / 2
    content_top = height * 0.150
    footer_top = height * 0.755

    headline = smart_quotes(entry["headline"])
    accent = smart_quotes(entry["accent"]) if entry.get("accent") else None

    hfont, hlines = fit_text(headline, "display", text_w,
                             height * (0.28 if accent else 0.40),
                             max_size=int(width * 0.082),
                             min_size=int(width * 0.034))
    afont = alines = None
    if accent:
        afont, alines = fit_text(accent, "display", text_w, height * 0.20,
                                 max_size=int(width * 0.055),
                                 min_size=int(width * 0.026))

    flourish_w = width * 0.24
    flourish_h = flourish_w * 0.16
    gap_flourish = height * 0.046
    gap_divider = height * 0.032
    swash_h = height * 0.034

    block = flourish_h + gap_flourish + len(hlines) * hfont.size * 1.18
    if alines:
        block += gap_divider * 2 + len(alines) * afont.size * 1.20 + swash_h

    y = content_top + max(0.0, (footer_top - content_top - block) / 2)

    draw_flourish(canvas, width / 2, y + flourish_h / 2, flourish_w)
    y += flourish_h + gap_flourish

    y = draw_lines(draw, hlines, hfont, left, y, brand.BROWN + (255,),
                   line_spacing=1.18, align="center", box_width=text_w)

    if alines:
        y += gap_divider
        draw_divider(canvas, width / 2, y, width * 0.22)
        y += gap_divider
        y = draw_lines(draw, alines, afont, left, y, brand.ROSE + (255,),
                       line_spacing=1.20, align="center", box_width=text_w)
        draw_swash(canvas, width / 2 - width * 0.16, y + height * 0.010,
                   width * 0.32)

    draw_brand_footer(canvas, width / 2, footer_top + height * 0.020,
                      height * 0.945, max_logo_width=width * 0.30)


def _layout_quote_left(canvas: Image.Image, entry: dict[str, Any],
                       rng: random.Random, has_photo: bool) -> None:
    width, height = canvas.size
    canvas.alpha_composite(horizontal_scrim((width, height), brand.CREAM_LIGHT,
                                            strength=0.95, extent=0.80))
    # Keep the footer zone light so the full-colour logo reads on any photo.
    canvas.alpha_composite(vertical_scrim((width, height), brand.CREAM_LIGHT,
                                          strength=0.90, extent=0.28))
    draw_frame(canvas)

    margin = int(width * 0.115)
    text_width = width * 0.60
    content_top = height * 0.140
    footer_top = height * 0.750
    draw = ImageDraw.Draw(canvas)

    headline = smart_quotes(entry["headline"])
    accent = smart_quotes(entry["accent"]) if entry.get("accent") else None

    hfont, hlines = fit_text(headline, "display", text_width,
                             height * (0.30 if accent else 0.44),
                             max_size=int(width * 0.086),
                             min_size=int(width * 0.036))
    afont = alines = None
    if accent:
        afont, alines = fit_text(accent, "display", text_width, height * 0.22,
                                 max_size=int(width * 0.070),
                                 min_size=int(width * 0.030))

    # Measure the whole stack first, then centre it in the free zone. Fixed
    # offsets are what left the big empty gap above the logo.
    flourish_w = width * 0.22
    flourish_h = flourish_w * 0.16
    gap_flourish = height * 0.040
    gap_divider = height * 0.032
    swash_h = height * 0.034

    block = flourish_h + gap_flourish + len(hlines) * hfont.size * 1.16
    if alines:
        block += gap_divider * 2 + len(alines) * afont.size * 1.16 + swash_h

    zone = footer_top - content_top
    y = content_top + max(0.0, (zone - block) / 2)

    draw_flourish(canvas, margin + flourish_w / 2, y + flourish_h / 2, flourish_w)
    y += flourish_h + gap_flourish

    y = draw_lines(draw, hlines, hfont, margin, y, brand.BROWN + (255,),
                   line_spacing=1.16)

    if alines:
        y += gap_divider
        draw_divider(canvas, margin + text_width * 0.20, y, width * 0.20)
        y += gap_divider
        y = draw_lines(draw, alines, afont, margin, y, brand.ROSE + (255,),
                       line_spacing=1.16)
        draw_swash(canvas, margin, y + height * 0.010, width * 0.32)

    draw_brand_footer(canvas, width / 2, footer_top + height * 0.025,
                      height * 0.945, max_logo_width=width * 0.30)


def _layout_arch_card(canvas: Image.Image, entry: dict[str, Any],
                      rng: random.Random, has_photo: bool) -> None:
    width, height = canvas.size
    if has_photo:
        canvas.alpha_composite(vertical_scrim((width, height), brand.BROWN,
                                              strength=0.22, extent=0.30))

    # Off to one side when a photo fills the rest of the frame; centred on
    # plain stock, where an offset card just looks lopsided.
    card_w = int(width * (0.62 if has_photo else 0.74))
    card_h = int(height * 0.68)
    card_x = int(width * 0.075) if has_photo else (width - card_w) // 2
    card_y = int(height * 0.055)
    card = rounded_card((card_w, card_h), radius=int(width * 0.03),
                        fill=brand.CREAM_LIGHT, arch=True)

    # thin gold keyline just inside the card edge - the arc and the two
    # verticals must meet at the same y or the join shows as a step
    edge = ImageDraw.Draw(card)
    inset = int(width * 0.018)
    keyline = max(1, int(width / 480))
    shoulder = inset + (card_w - inset * 2) / 2
    edge.arc((inset, inset, card_w - inset, card_w - inset), 180, 360,
             fill=brand.GOLD + (170,), width=keyline)
    edge.line((inset, shoulder, inset, card_h - inset),
              fill=brand.GOLD + (170,), width=keyline)
    edge.line((card_w - inset, shoulder, card_w - inset, card_h - inset),
              fill=brand.GOLD + (170,), width=keyline)
    edge.line((inset, card_h - inset, card_w - inset, card_h - inset),
              fill=brand.GOLD + (170,), width=keyline)

    paste_with_shadow(canvas, card, (card_x, card_y), blur=28, opacity=70)

    draw = ImageDraw.Draw(canvas)
    inner_x = card_x + int(card_w * 0.11)
    inner_w = card_w - int(card_w * 0.22)
    align = "left" if has_photo else "center"

    # The usable zone starts below the arch curve and ends inside the base.
    zone_top = card_y + card_w * 0.40
    zone_bottom = card_y + card_h - card_h * 0.08

    bullets = [smart_quotes(b) for b in (entry.get("bullets") or [])]
    accent = smart_quotes(entry["accent"]) if entry.get("accent") else None

    font, lines = fit_text(smart_quotes(entry["headline"]), "display", inner_w,
                           card_h * (0.28 if (bullets or accent) else 0.50),
                           max_size=int(width * 0.070),
                           min_size=int(width * 0.030))

    flourish_w = card_w * 0.32
    flourish_h = flourish_w * 0.16
    gap_flourish = height * 0.038
    gap_divider = height * 0.026

    block = flourish_h + gap_flourish + len(lines) * font.size * 1.18

    bfont = None
    bullet_step = 0.0
    if bullets:
        # Shrink the list until the whole block fits between zone_top and
        # zone_bottom. At the nominal size a four-item list runs past the base
        # of the arch and the last bullet gets sliced off by the card edge -
        # the vertical centring below clamps at zone_top and cannot save it.
        gap_bullets = height * 0.030
        room = zone_bottom - zone_top - block - gap_bullets
        size = int(width * 0.042)
        floor_size = int(width * 0.026)
        while size > floor_size and len(bullets) * size * 1.85 > room:
            size -= 1
        bfont = get_font("display", size)
        bullet_step = bfont.size * 1.85
        block += gap_bullets + len(bullets) * bullet_step
    elif accent:
        afont, alines = fit_text(accent, "display", inner_w, card_h * 0.24,
                                 max_size=int(width * 0.046),
                                 min_size=int(width * 0.023))
        block += gap_divider * 2 + len(alines) * afont.size * 1.20

    y = zone_top + max(0.0, (zone_bottom - zone_top - block) / 2)

    draw_flourish(canvas, card_x + card_w / 2, y + flourish_h / 2, flourish_w)
    y += flourish_h + gap_flourish

    y = draw_lines(draw, lines, font, inner_x, y, brand.BROWN + (255,),
                   line_spacing=1.18, align=align, box_width=inner_w)

    if bullets:
        y += height * 0.030
        # Bullets read best left-aligned as a group, but that group is
        # centred as a whole so it sits under a centred headline.
        widest = max(bfont.getlength(b) for b in bullets)
        dot_r = max(3, bfont.size * 0.14)
        list_x = (inner_x if align == "left"
                  else card_x + (card_w - (widest + dot_r * 5)) / 2)
        for item in bullets:
            draw.ellipse((list_x, y + bfont.size * 0.46 - dot_r,
                          list_x + dot_r * 2, y + bfont.size * 0.46 + dot_r),
                         fill=brand.ROSE + (255,))
            draw.text((list_x + dot_r * 5, y), item, font=bfont,
                      fill=brand.BROWN + (255,))
            y += bullet_step
    elif accent:
        y += gap_divider
        draw_divider(canvas, card_x + card_w / 2, y, card_w * 0.32)
        y += gap_divider
        draw_lines(draw, alines, afont, inner_x, y, brand.ROSE + (255,),
                   line_spacing=1.20, align=align, box_width=inner_w)

    band_h = int(height * 0.20)
    band_top = height - band_h
    band = Image.new("RGBA", (width, band_h), brand.CREAM_LIGHT + (255,))
    canvas.alpha_composite(band, (0, band_top))
    draw_brand_footer(canvas, width / 2,
                      band_top + band_h * 0.12, height - band_h * 0.10,
                      with_name=True, max_logo_width=width * 0.28)


def _layout_center_overlay(canvas: Image.Image, entry: dict[str, Any],
                           rng: random.Random, has_photo: bool) -> None:
    width, height = canvas.size
    canvas.alpha_composite(Image.new("RGBA", (width, height), brand.INK + (95,)))
    canvas.alpha_composite(vertical_scrim((width, height), brand.INK,
                                          strength=0.55, extent=0.40))
    canvas.alpha_composite(vertical_scrim((width, height), brand.INK,
                                          strength=0.40, extent=0.30, from_top=True))

    draw_frame(canvas, colour=brand.CREAM, inset_ratio=0.048, opacity=105)

    draw = ImageDraw.Draw(canvas)
    text_w = width * 0.76
    left = (width - text_w) / 2
    content_top = height * 0.150
    footer_top = height * 0.740

    accent = smart_quotes(entry["accent"]) if entry.get("accent") else None
    font, lines = fit_text(smart_quotes(entry["headline"]), "display", text_w,
                           height * (0.26 if accent else 0.38),
                           max_size=int(width * 0.085), min_size=int(width * 0.034))
    afont = alines = None
    if accent:
        afont, alines = fit_text(accent, "display", text_w, height * 0.20,
                                 max_size=int(width * 0.052),
                                 min_size=int(width * 0.026))

    flourish_w = width * 0.24
    flourish_h = flourish_w * 0.16
    gap_flourish = height * 0.046
    gap_divider = height * 0.032

    block = flourish_h + gap_flourish + len(lines) * font.size * 1.18
    if alines:
        block += gap_divider * 2 + len(alines) * afont.size * 1.20

    y = content_top + max(0.0, (footer_top - content_top - block) / 2)

    draw_flourish(canvas, width / 2, y + flourish_h / 2, flourish_w,
                  colour=brand.GOLD_LIGHT, dot_colour=brand.ROSE_LIGHT)
    y += flourish_h + gap_flourish

    y = draw_lines(draw, lines, font, left, y, brand.WHITE + (255,),
                   line_spacing=1.18, align="center", box_width=text_w)

    if alines:
        y += gap_divider
        draw_divider(canvas, width / 2, y, width * 0.22, colour=brand.GOLD_LIGHT)
        y += gap_divider
        draw_lines(draw, alines, afont, left, y, brand.ROSE_PALE + (255,),
                   line_spacing=1.20, align="center", box_width=text_w)

    draw_brand_footer(canvas, width / 2, footer_top + height * 0.020,
                      height * 0.940, max_logo_width=width * 0.30)


def _layout_soft_band(canvas: Image.Image, entry: dict[str, Any],
                      rng: random.Random, has_photo: bool) -> None:
    width, height = canvas.size
    band_top = int(height * 0.46)
    band_h = height - band_top

    # Tint the photo half so the cream band still reads as a separate plane
    # even when the background itself is pale.
    canvas.alpha_composite(vertical_scrim((width, height), brand.BROWN,
                                          strength=0.28, extent=0.62,
                                          from_top=True))

    # soft torn edge: a blurred mask so the cream rises into the photo
    band = Image.new("RGBA", (width, band_h), brand.CREAM_LIGHT + (255,))
    mask = Image.new("L", (width, band_h), 255)
    mdraw = ImageDraw.Draw(mask)
    wave = int(height * 0.055)
    points = [(0, wave * 2)]
    steps = 7
    for i in range(steps + 1):
        x = width * i / steps
        points.append((x, wave * (1.0 + 0.85 * math.sin(i * 1.7 + rng.random() * 3))))
    points += [(width, wave * 2), (width, 0), (0, 0)]
    mdraw.polygon(points, fill=0)
    band.putalpha(mask.filter(ImageFilter.GaussianBlur(2)))
    canvas.alpha_composite(band, (0, band_top))

    draw = ImageDraw.Draw(canvas)
    text_w = width * 0.78
    left = (width - text_w) / 2
    content_top = band_top + band_h * 0.16
    footer_top = height * 0.800

    accent = smart_quotes(entry["accent"]) if entry.get("accent") else None
    font, lines = fit_text(smart_quotes(entry["headline"]), "display", text_w,
                           band_h * (0.26 if accent else 0.38),
                           max_size=int(width * 0.072), min_size=int(width * 0.030))
    afont = alines = None
    if accent:
        afont, alines = fit_text(accent, "display", text_w, band_h * 0.18,
                                 max_size=int(width * 0.044),
                                 min_size=int(width * 0.022))

    flourish_w = width * 0.20
    flourish_h = flourish_w * 0.16
    gap_flourish = height * 0.032
    gap_accent = height * 0.020

    block = flourish_h + gap_flourish + len(lines) * font.size * 1.16
    if alines:
        block += gap_accent + len(alines) * afont.size * 1.18

    y = content_top + max(0.0, (footer_top - content_top - block) / 2)

    draw_flourish(canvas, width / 2, y + flourish_h / 2, flourish_w)
    y += flourish_h + gap_flourish

    y = draw_lines(draw, lines, font, left, y, brand.BROWN + (255,),
                   line_spacing=1.16, align="center", box_width=text_w)

    if alines:
        y += gap_accent
        draw_lines(draw, alines, afont, left, y, brand.ROSE + (255,),
                   line_spacing=1.18, align="center", box_width=text_w)

    draw_brand_footer(canvas, width / 2, footer_top + height * 0.010,
                      height * 0.962, with_name=True,
                      max_logo_width=width * 0.26)


_LAYOUT_FUNCS = {
    "paper_quote": _layout_paper_quote,
    "quote_left": _layout_quote_left,
    "arch_card": _layout_arch_card,
    "center_overlay": _layout_center_overlay,
    "soft_band": _layout_soft_band,
}


def choose_layout(entry: dict[str, Any], rng: random.Random,
                  has_photo: bool) -> str:
    """Pick a layout that suits the background we actually got."""
    if entry.get("bullets"):
        return "arch_card"
    if not has_photo:
        return rng.choice(["paper_quote", "paper_quote", "arch_card"])
    return rng.choice(["quote_left", "center_overlay", "soft_band", "quote_left"])


# --------------------------------------------------------------------------
# Entry point
# --------------------------------------------------------------------------

def render(entry: dict[str, Any], out_path: Path,
           canvas_name: str = brand.DEFAULT_CANVAS,
           layout: str | None = None, seed: str | None = None,
           exclude_backgrounds: set[str] | None = None) -> dict[str, Any]:
    """Render one creative to `out_path` and return its metadata."""
    size = brand.CANVAS.get(canvas_name)
    if size is None:
        raise ValueError(f"Unknown canvas {canvas_name!r}. "
                         f"Choose from {sorted(brand.CANVAS)}")

    seed = seed or entry["id"]
    rng = random.Random(seed)

    background, source = assets.get_background(size, seed, exclude_backgrounds,
                                               theme=entry.get("theme"))
    canvas = background.convert("RGBA")
    has_photo = source != "generated"

    layout = layout or choose_layout(entry, rng, has_photo)
    if layout not in _LAYOUT_FUNCS:
        raise ValueError(f"Unknown layout {layout!r}. "
                         f"Choose from {sorted(_LAYOUT_FUNCS)}")
    _LAYOUT_FUNCS[layout](canvas, entry, rng, has_photo)

    out_path.parent.mkdir(parents=True, exist_ok=True)
    final = canvas.convert("RGB")
    if out_path.suffix.lower() in (".jpg", ".jpeg"):
        final.save(out_path, quality=92, subsampling=0, optimize=True)
    else:
        final.save(out_path)

    return {
        "content_id": entry["id"],
        "theme": entry.get("theme", "general"),
        "headline": entry["headline"],
        "accent": entry.get("accent"),
        "bullets": entry.get("bullets"),
        "layout": layout,
        "canvas": canvas_name,
        "size": list(size),
        "background": source,
        "image_path": str(out_path),
    }
