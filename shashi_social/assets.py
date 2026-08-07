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


# --------------------------------------------------------------------------
# Natural motifs
#
# Everything here is drawn well out of focus and at low opacity. The point is
# a backdrop that feels like light and living things - dawn, leaves, still
# water - rather than a flat swatch, while still leaving the quote the most
# contrasted thing on the canvas. Anything sharp enough to name would compete
# with the words.
# --------------------------------------------------------------------------

def _mask_layer(size: tuple[int, int], mask: Image.Image,
                colour: tuple) -> Image.Image:
    layer = Image.new("RGBA", size, colour + (0,))
    layer.putalpha(mask)
    return layer


def _light_shafts(size: tuple[int, int], rng: random.Random,
                  colour: tuple = (255, 247, 231),
                  strength: float = 0.60) -> Image.Image:
    """Soft beams raking down the frame, as if through a window."""
    width, height = size
    small = (max(8, width // 5), max(8, height // 5))
    mask = Image.new("L", small, 0)
    draw = ImageDraw.Draw(mask)

    origin_x = rng.uniform(-0.25, 0.55) * small[0]
    origin_y = -small[1] * 0.35
    for _ in range(rng.randint(3, 5)):
        spread = rng.uniform(0.08, 0.20) * small[0]
        drift = rng.uniform(0.25, 1.15) * small[0]
        value = int(255 * strength * rng.uniform(0.45, 1.0))
        draw.polygon(
            [(origin_x, origin_y),
             (origin_x + spread, origin_y),
             (origin_x + drift + spread * 3.2, small[1]),
             (origin_x + drift, small[1])],
            fill=value,
        )
        origin_x += spread * rng.uniform(1.6, 3.0)

    mask = mask.filter(ImageFilter.GaussianBlur(small[0] / 9))
    return _mask_layer(size, mask.resize(size, Image.BICUBIC), colour)


def _bokeh(size: tuple[int, int], rng: random.Random,
           colour: tuple = (255, 249, 236), count: int = 14) -> Image.Image:
    """Defocused points of light - the signature of a real lens."""
    width, height = size
    small = (max(8, width // 4), max(8, height // 4))
    mask = Image.new("L", small, 0)
    draw = ImageDraw.Draw(mask)

    for _ in range(count):
        r = rng.uniform(0.03, 0.11) * small[0]
        cx = rng.uniform(-0.05, 1.05) * small[0]
        cy = rng.uniform(-0.05, 1.05) * small[1]
        draw.ellipse((cx - r, cy - r, cx + r, cy + r),
                     fill=rng.randint(46, 108))

    mask = mask.filter(ImageFilter.GaussianBlur(small[0] / 26))
    return _mask_layer(size, mask.resize(size, Image.BICUBIC), colour)


def _leaf_sprite(length: int, width: int, value: int) -> Image.Image:
    """One blade-shaped leaf, drawn as a grayscale stencil."""
    leaf = Image.new("L", (max(2, width), max(2, length)), 0)
    ImageDraw.Draw(leaf).ellipse((0, 0, width - 1, length - 1), fill=value)
    return leaf


def _botanical(size: tuple[int, int], rng: random.Random,
               colour: tuple = brand.BROWN_MUTED,
               opacity: int = 92) -> Image.Image:
    """Out-of-focus sprigs leaning in from an edge, like a plant by a window.

    Anchored to the left and right edges rather than the corners: the arch and
    paper layouts both park a solid card over the middle of the canvas, so a
    motif in the centre is simply never seen. The side margins are the strip
    that is actually on screen.
    """
    width, height = size
    # Half resolution, not a third: the leaves have to survive the blur as
    # leaves. Any softer and the sprig reads as a smudge on the lens.
    small = (max(16, width // 2), max(16, height // 2))
    mask = Image.new("L", small, 0)
    draw = ImageDraw.Draw(mask)

    # (x, y, which way it leans) - both flanks, biased to the upper half where
    # the arch narrows and leaves the most room.
    anchors = [(0.0, 0.30, 1), (0.0, 0.72, 1), (1.0, 0.26, -1), (1.0, 0.66, -1)]
    for ax, ay, direction in rng.sample(anchors, rng.randint(2, 3)):
        base_x, base_y = ax * small[0], ay * small[1]
        for _ in range(rng.randint(2, 3)):
            stem_len = rng.uniform(0.26, 0.44) * small[1]
            tip_x = base_x + stem_len * rng.uniform(0.30, 0.62) * direction
            tip_y = base_y - stem_len * rng.uniform(0.55, 1.0)
            draw.line((base_x, base_y, tip_x, tip_y),
                      fill=opacity, width=max(2, small[0] // 260))

            leaves = rng.randint(6, 9)
            for i in range(1, leaves + 1):
                t = i / (leaves + 1)
                lx = base_x + (tip_x - base_x) * t
                ly = base_y + (tip_y - base_y) * t
                length = int(rng.uniform(0.045, 0.075) * small[1] * (1.15 - t * 0.45))
                leaf = _leaf_sprite(length, int(length * 0.40), opacity + 34)
                angle = rng.uniform(25, 70) * (1 if i % 2 else -1) * direction
                leaf = leaf.rotate(angle, expand=True, resample=Image.BICUBIC)
                mask.paste(leaf, (int(lx - leaf.width / 2),
                                  int(ly - leaf.height / 2)), leaf)

    mask = mask.filter(ImageFilter.GaussianBlur(small[0] / 260))
    return _mask_layer(size, mask.resize(size, Image.BICUBIC), colour)


def _petals(size: tuple[int, int], rng: random.Random,
            colour: tuple = brand.ROSE_LIGHT, count: int = 11) -> Image.Image:
    """Petals caught mid-drift - motion, and a thing being let go of."""
    width, height = size
    small = (max(16, width // 3), max(16, height // 3))
    mask = Image.new("L", small, 0)

    for _ in range(count):
        length = int(rng.uniform(0.035, 0.075) * small[1])
        petal = _leaf_sprite(length, int(length * 0.55), rng.randint(58, 118))
        petal = petal.rotate(rng.uniform(0, 360), expand=True,
                             resample=Image.BICUBIC)
        x = int(rng.uniform(-0.05, 1.0) * small[0])
        y = int(rng.uniform(-0.05, 1.0) * small[1])
        mask.paste(petal, (x, y), petal)

    mask = mask.filter(ImageFilter.GaussianBlur(small[0] / 150))
    return _mask_layer(size, mask.resize(size, Image.BICUBIC), colour)


def _mist_bands(size: tuple[int, int], rng: random.Random,
                colour: tuple = (255, 252, 246),
                count: int = 4) -> Image.Image:
    """Horizontal haze, the way early light layers over a horizon."""
    width, height = size
    small = (max(8, width // 5), max(8, height // 5))
    mask = Image.new("L", small, 0)
    draw = ImageDraw.Draw(mask)

    for _ in range(count):
        cy = rng.uniform(0.15, 0.9) * small[1]
        thickness = rng.uniform(0.04, 0.12) * small[1]
        draw.ellipse((-small[0] * 0.3, cy - thickness,
                      small[0] * 1.3, cy + thickness),
                     fill=rng.randint(58, 122))

    mask = mask.filter(ImageFilter.GaussianBlur(small[1] / 14))
    return _mask_layer(size, mask.resize(size, Image.BICUBIC), colour)


def _ripples(size: tuple[int, int], rng: random.Random,
             colour: tuple = (255, 253, 248)) -> Image.Image:
    """Rings spreading on still water - stillness, but not emptiness."""
    width, height = size
    small = (max(8, width // 4), max(8, height // 4))
    mask = Image.new("L", small, 0)
    draw = ImageDraw.Draw(mask)

    cx = rng.uniform(0.3, 0.7) * small[0]
    cy = rng.uniform(0.55, 0.95) * small[1]
    for i in range(7):
        r = (0.10 + i * 0.11) * small[0]
        draw.ellipse((cx - r, cy - r * 0.34, cx + r, cy + r * 0.34),
                     outline=max(30, 150 - i * 16),
                     width=max(1, small[0] // 110))

    mask = mask.filter(ImageFilter.GaussianBlur(small[0] / 55))
    return _mask_layer(size, mask.resize(size, Image.BICUBIC), colour)


# --------------------------------------------------------------------------
# Scenes
#
# One per theme in the content bank, so the backdrop is saying the same thing
# as the words on top of it: dawn light behind a morning quote, new growth
# behind a growth quote, still water behind an anxiety one.
# --------------------------------------------------------------------------

def _scene_dawn(size: tuple[int, int], rng: random.Random) -> Image.Image:
    """morning - first light coming over the frame."""
    base = _linear_gradient(size, (255, 248, 236), (240, 222, 205)).convert("RGBA")
    base.alpha_composite(_radial_glow(size, (rng.uniform(0.35, 0.65), 0.10),
                                      1.35, (255, 243, 218), 0.70))
    base.alpha_composite(_light_shafts(size, rng, (255, 246, 226), 0.38))
    return base


def _scene_growth(size: tuple[int, int], rng: random.Random) -> Image.Image:
    """growth - leaves reaching in, warm light behind them."""
    base = _linear_gradient(size, (252, 249, 240), (235, 231, 216)).convert("RGBA")
    base.alpha_composite(_radial_glow(size, (0.66, 0.24), 1.20,
                                      (255, 250, 232), 0.52))
    base.alpha_composite(_botanical(size, rng, brand.BROWN_MUTED, opacity=32))
    return base


def _scene_haze(size: tuple[int, int], rng: random.Random) -> Image.Image:
    """healing - soft dawn haze, nothing sharp."""
    base = _linear_gradient(size, (253, 247, 241), (238, 226, 220)).convert("RGBA")
    base.alpha_composite(_mist_bands(size, rng, (255, 250, 244), count=5))
    base.alpha_composite(_radial_glow(size, (0.5, 0.30), 1.25,
                                      (255, 248, 238), 0.50))
    return base


def _scene_radiance(size: tuple[int, int], rng: random.Random) -> Image.Image:
    """self_worth - a warm source of light, centred and unapologetic."""
    base = _linear_gradient(size, (254, 249, 238), (242, 228, 206)).convert("RGBA")
    base.alpha_composite(_radial_glow(size, (0.5, 0.38), 1.40,
                                      (255, 247, 226), 0.72))
    base.alpha_composite(_bokeh(size, rng, (255, 246, 226), count=12))
    return base


def _scene_horizon(size: tuple[int, int], rng: random.Random) -> Image.Image:
    """boundaries - one calm, level line. Structure, held gently."""
    base = _linear_gradient(size, (252, 248, 242), (233, 226, 216)).convert("RGBA")
    base.alpha_composite(_mist_bands(size, rng, (255, 253, 249), count=2))
    base.alpha_composite(_radial_glow(size, (0.5, 0.16), 1.15,
                                      (255, 251, 242), 0.45))
    return base


def _scene_warmth(size: tuple[int, int], rng: random.Random) -> Image.Image:
    """relationships - two lights overlapping, neither one dimmed."""
    base = _linear_gradient(size, (254, 248, 244), (240, 224, 220)).convert("RGBA")
    base.alpha_composite(_radial_glow(size, (0.30, 0.30), 1.05,
                                      (255, 240, 232), 0.52))
    base.alpha_composite(_radial_glow(size, (0.72, 0.46), 1.05,
                                      brand.ROSE_PALE, 0.42))
    base.alpha_composite(_bokeh(size, rng, (255, 244, 238), count=10))
    return base


def _scene_drift(size: tuple[int, int], rng: random.Random) -> Image.Image:
    """letting_go - petals on the way down, light fading behind them."""
    base = _linear_gradient(size, (253, 248, 244), (237, 227, 224)).convert("RGBA")
    base.alpha_composite(_radial_glow(size, (0.62, 0.18), 1.20,
                                      (255, 248, 238), 0.48))
    base.alpha_composite(_petals(size, rng, brand.ROSE_LIGHT, count=12))
    return base


def _scene_still_water(size: tuple[int, int], rng: random.Random) -> Image.Image:
    """anxiety - the calmest thing we can put behind a racing mind."""
    base = _linear_gradient(size, (252, 250, 246), (232, 232, 226)).convert("RGBA")
    base.alpha_composite(_mist_bands(size, rng, (255, 254, 250), count=3))
    base.alpha_composite(_ripples(size, rng, (255, 253, 248)))
    return base


THEME_SCENES = {
    "morning": _scene_dawn,
    "growth": _scene_growth,
    "healing": _scene_haze,
    "self_worth": _scene_radiance,
    "boundaries": _scene_horizon,
    "relationships": _scene_warmth,
    "letting_go": _scene_drift,
    "anxiety": _scene_still_water,
}

# Used when an entry has a theme we have no scene for. Deliberately the calm,
# say-nothing ones - a mismatched motif is worse than a neutral wash.
_FALLBACK_SCENES = (_scene_haze, _scene_radiance, _scene_horizon, _scene_dawn)


def procedural_background(size: tuple[int, int], seed: str,
                          theme: str | None = None) -> Image.Image:
    """An on-brand backdrop, matched to what the quote is about.

    Real photography would be better still - drop files into
    assets/backgrounds/ and these are skipped entirely - but a themed,
    grained scene reads as a deliberate editorial choice, which a flat
    swatch never does.
    """
    rng = _seeded_rng(seed)
    scene = THEME_SCENES.get(theme or "")
    if scene is None:
        scene = _FALLBACK_SCENES[rng.randrange(len(_FALLBACK_SCENES))]

    base = scene(size, rng)

    # Texture and depth. Light here: the motifs already carry the image, and
    # heavy fibre would drag it back towards looking like printed paper.
    base.alpha_composite(_paper_fibre(size, opacity=7))
    base.alpha_composite(_grain(size, sigma=4.0, opacity=11))
    base.alpha_composite(_vignette(size, strength=0.24))
    return base.convert("RGB")


def photo_theme(path: Path) -> str | None:
    """Which theme a background photo is reserved for, from its filename.

    `relationships-01.jpg` is only ever used behind a relationships quote.
    Anything else - `beach.jpg`, a photo the user simply dropped in - carries
    no theme and is fair game for any of them.
    """
    prefix = path.stem.rsplit("-", 1)[0].strip().lower()
    return prefix if prefix in THEME_SCENES else None


def get_background(size: tuple[int, int], seed: str,
                   exclude: set[str] | None = None,
                   theme: str | None = None,
                   allow_photo: bool = True) -> tuple[Image.Image, str]:
    """Pick a background photo from the pool, else synthesise one.

    Returns the image plus a short source label for logging.
    """
    exclude = exclude or set()
    pool = [] if not allow_photo else [
        p for p in list_backgrounds() if p.name not in exclude]

    # A photo of a couple at sunset behind an anxiety quote reads as a mistake,
    # so a theme with no photo of its own gets its generated scene instead of
    # borrowing someone else's.
    pool = [p for p in pool if photo_theme(p) in (None, theme)]

    if pool:
        rng = _seeded_rng(seed)
        chosen = pool[rng.randrange(len(pool))]
        try:
            img = Image.open(chosen).convert("RGB")
            return cover_crop(img, size), chosen.name
        except OSError:
            pass  # unreadable file - fall through to a generated background

    return procedural_background(size, seed, theme), "generated"

