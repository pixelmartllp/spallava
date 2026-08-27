"""Brand system for Shashi Pallava - Life & Relationship Coach.

Colours, fonts and canvas sizes are all defined here so the look stays
consistent across every creative the renderer produces.
"""

from __future__ import annotations

import os
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

ASSETS = ROOT / "assets"
FONT_DIR = ASSETS / "fonts"
BACKGROUND_DIR = ASSETS / "backgrounds"
# The commissioned pool: figures seen from behind with no readable face, in
# natural-photograph and pen/pencil-sketch styles. Kept apart from
# backgrounds/ because a sketch on cream paper needs dark type, where a
# photograph needs light - see renderer.artwork_is_light().
ARTWORK_DIR = ASSETS / "artwork"
OUTPUT_DIR = ROOT / "output"
STATE_DIR = ROOT / "state"

LOGO_SOURCE = ASSETS / "logo.png"
LOGO_TRANSPARENT = ASSETS / "logo_transparent.png"

WINDOWS_FONTS = Path(os.environ.get("SystemRoot", r"C:\Windows")) / "Fonts"


# --------------------------------------------------------------------------
# Palette - sampled from the brand logo and the approved sample creatives
# --------------------------------------------------------------------------

CREAM = (248, 242, 233)
CREAM_LIGHT = (253, 250, 245)
CREAM_DEEP = (240, 231, 218)

BROWN = (67, 48, 42)
BROWN_SOFT = (107, 82, 72)
BROWN_MUTED = (140, 118, 108)

ROSE = (194, 102, 108)
ROSE_LIGHT = (217, 143, 148)
ROSE_PALE = (238, 210, 210)

GOLD = (194, 154, 91)
GOLD_LIGHT = (219, 190, 143)

WHITE = (255, 255, 255)
INK = (32, 24, 21)


# --------------------------------------------------------------------------
# Canvas presets
# --------------------------------------------------------------------------

CANVAS = {
    "portrait": (1080, 1350),   # Instagram / Facebook feed - best reach
    "square": (1080, 1080),
    "story": (1080, 1920),
}

DEFAULT_CANVAS = "portrait"


# --------------------------------------------------------------------------
# Font resolution
#
# Drop nicer brand fonts (Playfair Display, Cormorant, Montserrat) into
# assets/fonts/ and they are picked up automatically. Otherwise we fall back
# to well-made fonts that ship with Windows.
# --------------------------------------------------------------------------

_FONT_STACKS: dict[str, list[str]] = {
    "display": [
        "PlayfairDisplay-SemiBold.ttf",
        "PlayfairDisplay-Medium.ttf",
        "PlayfairDisplay-Regular.ttf",
        "Cormorant-SemiBold.ttf",
        "CormorantGaramond-SemiBold.ttf",
        "constan.ttf",
        "georgia.ttf",
        "times.ttf",
    ],
    "display_bold": [
        "PlayfairDisplay-Bold.ttf",
        "PlayfairDisplay-SemiBold.ttf",
        "Cormorant-Bold.ttf",
        "constanb.ttf",
        "georgiab.ttf",
        "timesbd.ttf",
    ],
    "display_italic": [
        "PlayfairDisplay-Italic.ttf",
        "Cormorant-Italic.ttf",
        "constani.ttf",
        "georgiai.ttf",
        "timesi.ttf",
    ],
    "body": [
        "Montserrat-Regular.ttf",
        "Lato-Regular.ttf",
        "segoeui.ttf",
        "calibri.ttf",
        "arial.ttf",
    ],
    "body_medium": [
        "Montserrat-Medium.ttf",
        "Montserrat-SemiBold.ttf",
        "Lato-Bold.ttf",
        "segoeuib.ttf",
        "calibrib.ttf",
        "arialbd.ttf",
    ],
}


def font_path(role: str) -> str:
    """Return an absolute path to the best available font for a role."""
    candidates = _FONT_STACKS.get(role)
    if not candidates:
        raise KeyError(f"Unknown font role: {role!r}")

    for name in candidates:
        local = FONT_DIR / name
        if local.is_file():
            return str(local)

    for name in candidates:
        system = WINDOWS_FONTS / name
        if system.is_file():
            return str(system)

    # Last resort - anything at all, so rendering never hard-fails.
    for fallback in (WINDOWS_FONTS / "arial.ttf", WINDOWS_FONTS / "segoeui.ttf"):
        if fallback.is_file():
            return str(fallback)

    raise FileNotFoundError(
        f"No font found for role {role!r}. Install a font or drop a .ttf into {FONT_DIR}"
    )


def font_report() -> dict[str, str]:
    """Which concrete font file each role currently resolves to."""
    return {role: font_path(role) for role in _FONT_STACKS}


# --------------------------------------------------------------------------
# Brand copy that appears on every creative
# --------------------------------------------------------------------------

BRAND_NAME = "Shashi Pallava"
BRAND_TAGLINE = "Life & Relationship Coach"

BRAND_HANDLE = "@shashipallava"

# The same handle set the way the owner writes it, for the faint mark across
# the middle of every creative - so a screenshot that gets cropped or reshared
# still carries it. Separate from BRAND_HANDLE because that one is an actual
# @mention in captions and has to match the account exactly; this one is
# lettering. Deliberately quiet: a watermark, not a second logo.
BRAND_WATERMARK = "@ShashiPallava"
PAGE_URL = "https://www.facebook.com/shashipallava"


def ensure_dirs() -> None:
    """Create the directory layout the pipeline expects."""
    for directory in (ASSETS, FONT_DIR, BACKGROUND_DIR, ARTWORK_DIR,
                      OUTPUT_DIR, STATE_DIR):
        directory.mkdir(parents=True, exist_ok=True)
