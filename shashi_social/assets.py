"""Asset handling: logo preparation and background sourcing.

The logo ships as an RGB PNG on a white plate, so we key the white out once
and cache a transparent version. Backgrounds come from assets/backgrounds/ when
the user has dropped photos in there; otherwise we synthesise on-brand abstract
backgrounds so the pipeline always produces something usable.
"""

from __future__ import annotations

import hashlib
import math
import random
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter

from . import brand

PHOTO_SUFFIXES = {".jpg", ".jpeg", ".png", ".webp", ".bmp"}

# White-plate keying ramp. Pixels brighter than WHITE_CUT become fully
# transparent, darker than INK_CUT stay fully opaque, and the band between the
# two ramps smoothly so antialiased script strokes keep their soft edges.
WHITE_CUT = 252
INK_CUT = 232


# --------------------------------------------------------------------------
# Logo
# --------------------------------------------------------------------------

def prepare_logo(force: bool = False) -> Path:
    """Key the white plate out of the logo and cache the transparent result."""
    src = brand.LOGO_SOURCE
    dst = brand.LOGO_TRANSPARENT

    if not src.is_file():
        raise FileNotFoundError(
            f"Logo not found at {src}. Copy the brand logo there first."
        )

    if dst.is_file() and not force and dst.stat().st_mtime >= src.stat().st_mtime:
        return dst

    img = Image.open(src).convert("RGBA")
    pixels = img.load()
    width, height = img.size
    span = WHITE_CUT - INK_CUT

    for y in range(height):
        for x in range(width):
            r, g, b, a = pixels[x, y]
            if a == 0:
                continue
            # Use the brightest channel: coloured ink on white always has at
            # least one channel pulled well below 255.
            brightest = max(r, g, b)
            if brightest >= WHITE_CUT:
                alpha = 0
            elif brightest <= INK_CUT:
                alpha = 255
            else:
                alpha = int(round(255 * (WHITE_CUT - brightest) / span))
            pixels[x, y] = (r, g, b, min(a, alpha))

    bbox = img.getbbox()
    if bbox:
        img = img.crop(bbox)

    dst.parent.mkdir(parents=True, exist_ok=True)
    img.save(dst)
    return dst


def load_logo(target_width: int, transparent: bool = True) -> Image.Image:
    """Return the logo as RGBA, scaled to `target_width`."""
    path = prepare_logo() if transparent else brand.LOGO_SOURCE
    img = Image.open(path).convert("RGBA")
    ratio = target_width / img.width
    size = (target_width, max(1, int(round(img.height * ratio))))
    return img.resize(size, Image.LANCZOS)


def load_logo_fit(max_width: int, max_height: int,
                  transparent: bool = True) -> Image.Image:
    """Scale the logo to fit inside a box without distorting or overflowing."""
    path = prepare_logo() if transparent else brand.LOGO_SOURCE
    img = Image.open(path).convert("RGBA")
    scale = min(max_width / img.width, max_height / img.height)
    size = (max(1, int(round(img.width * scale))),
            max(1, int(round(img.height * scale))))
    return img.resize(size, Image.LANCZOS)


def load_logo_mono(max_width: int, max_height: int,
                   colour: tuple) -> Image.Image:
    """A single-colour version of the logo, using its alpha as the stencil.

    The full-colour mark disappears on a dark photo; a cream monochrome
    version is the standard way brands solve that, and it reads as deliberate
    rather than as a fallback.
    """
    logo = load_logo_fit(max_width, max_height)
    mono = Image.new("RGBA", logo.size, colour + (0,))
    mono.putalpha(logo.split()[3])
    return mono


# --------------------------------------------------------------------------
# Backgrounds
# --------------------------------------------------------------------------

def list_backgrounds() -> list[Path]:
    """Every usable photo in the background pool, sorted for stable ordering."""
    if not brand.BACKGROUND_DIR.is_dir():
        return []
    return sorted(
        p for p in brand.BACKGROUND_DIR.iterdir()
        if p.is_file() and p.suffix.lower() in PHOTO_SUFFIXES
    )


def cover_crop(img: Image.Image, size: tuple[int, int]) -> Image.Image:
    """Scale-to-fill then centre-crop, so the photo always fills the canvas."""
    target_w, target_h = size
    scale = max(target_w / img.width, target_h / img.height)
    resized = img.resize(
        (max(target_w, int(math.ceil(img.width * scale))),
         max(target_h, int(math.ceil(img.height * scale)))),
        Image.LANCZOS,
    )
    left = (resized.width - target_w) // 2
    top = (resized.height - target_h) // 2
    return resized.crop((left, top, left + target_w, top + target_h))


def _seeded_rng(seed: str) -> random.Random:
    digest = hashlib.sha256(seed.encode("utf-8")).hexdigest()
    return random.Random(int(digest[:16], 16))


def _linear_gradient(size: tuple[int, int], top: tuple, bottom: tuple) -> Image.Image:
    """Vertical gradient, built small and scaled up for speed."""
    width, height = size
    strip = Image.new("RGB", (1, 256))
    draw = ImageDraw.Draw(strip)
    for i in range(256):
        t = i / 255
        draw.point(
            (0, i),
            fill=tuple(int(round(top[c] + (bottom[c] - top[c]) * t)) for c in range(3)),
        )
    return strip.resize((width, height), Image.BICUBIC)


def _radial_glow(size: tuple[int, int], centre: tuple[float, float],
                 radius: float, colour: tuple, strength: float) -> Image.Image:
    """A soft circular light, returned as an RGBA layer to paste over a base."""
    width, height = size
    small = (max(2, width // 8), max(2, height // 8))
    mask = Image.new("L", small, 0)
    draw = ImageDraw.Draw(mask)
    cx, cy = centre[0] * small[0], centre[1] * small[1]
    r = radius * max(small)
    steps = 24
    for i in range(steps, 0, -1):
        t = i / steps
        value = int(round(255 * strength * (1 - t) ** 2))
        rr = r * t
        draw.ellipse((cx - rr, cy - rr, cx + rr, cy + rr), fill=value)
    mask = mask.filter(ImageFilter.GaussianBlur(small[0] / 12))
    mask = mask.resize(size, Image.BICUBIC)

    layer = Image.new("RGBA", size, colour + (0,))
    layer.putalpha(mask)
    return layer


def _grain(size: tuple[int, int], sigma: float = 5.0, opacity: int = 16) -> Image.Image:
    """Fine film grain so flat gradients do not band on a phone screen."""
    noise = Image.effect_noise(size, sigma).convert("L")
    layer = Image.new("RGBA", size, (255, 255, 255, 0))
    layer.putalpha(noise.point(lambda v: int(abs(v - 128) / 128 * opacity)))
    return layer


def _paper_fibre(size: tuple[int, int], opacity: int = 10) -> Image.Image:
    """Coarse, slightly stretched noise that reads as woven paper stock."""
    small = (max(2, size[0] // 3), max(2, size[1] // 3))
    noise = Image.effect_noise(small, 24).convert("L")
    noise = noise.filter(ImageFilter.GaussianBlur(0.6))
    noise = noise.resize(size, Image.BICUBIC)
    layer = Image.new("RGBA", size, brand.BROWN + (0,))
    layer.putalpha(noise.point(lambda v: int(abs(v - 128) / 128 * opacity)))
    return layer


def _vignette(size: tuple[int, int], strength: float = 0.30,
              colour: tuple = brand.BROWN) -> Image.Image:
    """Darken the edges slightly - the cheapest way to add depth."""
    width, height = size
    small = (max(4, width // 6), max(4, height // 6))
    mask = Image.new("L", small, 255)
    draw = ImageDraw.Draw(mask)
    steps = 30
    for i in range(steps):
        t = i / steps
        inset_x = small[0] * 0.5 * t
        inset_y = small[1] * 0.5 * t
        draw.ellipse((inset_x - small[0] * 0.16, inset_y - small[1] * 0.16,
                      small[0] - inset_x + small[0] * 0.16,
                      small[1] - inset_y + small[1] * 0.16),
                     fill=int(255 * (1 - t)))
    mask = mask.filter(ImageFilter.GaussianBlur(small[0] / 8))
    mask = mask.resize(size, Image.BICUBIC)
    layer = Image.new("RGBA", size, colour + (0,))
    layer.putalpha(mask.point(lambda v: int((255 - v) * strength)))
    return layer


def procedural_background(size: tuple[int, int], seed: str) -> Image.Image:
    """An on-brand textured backdrop for when no photo is available.

    These deliberately read as fine printed paper rather than as a blurred
    photograph - a soft out-of-focus wash looks like a failed photo, whereas
    a tinted, grained stock looks like an intentional editorial choice.
    """
    rng = _seeded_rng(seed)
    variant = rng.randrange(4)

    if variant == 0:  # ivory stock, warm light from above
        base = _linear_gradient(size, brand.CREAM_LIGHT, brand.CREAM_DEEP).convert("RGBA")
        base.alpha_composite(_radial_glow(size, (0.5, 0.18), 1.25,
                                          (255, 250, 240), 0.55))

    elif variant == 1:  # blush wash rising from the lower corner
        base = _linear_gradient(size, brand.CREAM_LIGHT, (240, 224, 219)).convert("RGBA")
        base.alpha_composite(_radial_glow(size, (0.18, 0.92), 1.15,
                                          brand.ROSE_PALE, 0.40))
        base.alpha_composite(_radial_glow(size, (0.80, 0.12), 1.10,
                                          (255, 246, 232), 0.50))

    elif variant == 2:  # a single faint gold ring, echoing the logo mark
        base = _linear_gradient(size, brand.CREAM_LIGHT, brand.CREAM).convert("RGBA")
        rings = Image.new("RGBA", size, (0, 0, 0, 0))
        draw = ImageDraw.Draw(rings)
        cx = rng.uniform(0.62, 0.86) * size[0]
        cy = rng.uniform(0.14, 0.30) * size[1]
        for i in range(2):
            r = (0.46 + i * 0.10) * size[0]
            draw.ellipse((cx - r, cy - r, cx + r, cy + r), outline=brand.GOLD + (46,),
                         width=max(2, size[0] // 380))
        base.alpha_composite(rings.filter(ImageFilter.GaussianBlur(1.0)))

    else:  # warm sand, light pooling in the centre
        base = _linear_gradient(size, (252, 247, 239), (236, 224, 210)).convert("RGBA")
        base.alpha_composite(_radial_glow(size, (0.5, 0.40), 1.30,
                                          (255, 252, 245), 0.60))

    # Texture and depth. This is what separates "flat gradient" from "paper".
    base.alpha_composite(_paper_fibre(size, opacity=11))
    base.alpha_composite(_grain(size, sigma=4.0, opacity=13))
    base.alpha_composite(_vignette(size, strength=0.26))
    return base.convert("RGB")


def get_background(size: tuple[int, int], seed: str,
                   exclude: set[str] | None = None) -> tuple[Image.Image, str]:
    """Pick a background photo from the pool, else synthesise one.

    Returns the image plus a short source label for logging.
    """
    exclude = exclude or set()
    pool = [p for p in list_backgrounds() if p.name not in exclude]

    if pool:
        rng = _seeded_rng(seed)
        chosen = pool[rng.randrange(len(pool))]
        try:
            img = Image.open(chosen).convert("RGB")
            return cover_crop(img, size), chosen.name
        except OSError:
            pass  # unreadable file - fall through to a generated background

    return procedural_background(size, seed), "generated"
