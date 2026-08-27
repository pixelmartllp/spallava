"""Content bank access and caption assembly."""

from __future__ import annotations

import json
import random
from pathlib import Path
from typing import Any

from . import brand, state

BANK_FILE = brand.ROOT / "content_bank.json"

MAX_HASHTAGS = 18

# The bank no longer recycles used quotes, so it can genuinely run out. Shout
# with a fortnight's warning rather than on the morning it breaks - topping the
# bank up is a writing job, and the owner needs notice to do it.
LOW_BANK_WARNING = 14
CTA_LINES = [
    "Book a 1:1 session - link in bio.",
    "Follow @shashipallava for daily clarity.",
    "DM the word START to begin your 1:1 journey.",
    "Save this and come back to it when you need it.",
]


class ContentBankError(RuntimeError):
    pass


def log_low_bank(remaining: int) -> None:
    """Warn on stdout, which is where the GitHub Actions log picks it up."""
    print(f"WARNING: only {remaining} unused quotes left in the content bank. "
          f"At one creative a day that is {remaining} days. Add more to "
          f"content_bank.json before it runs dry.", flush=True)


def load_bank() -> dict[str, Any]:
    if not BANK_FILE.is_file():
        raise ContentBankError(f"Content bank missing at {BANK_FILE}")
    try:
        bank = json.loads(BANK_FILE.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ContentBankError(f"content_bank.json is not valid JSON: {exc}") from exc

    entries = bank.get("entries")
    if not isinstance(entries, list) or not entries:
        raise ContentBankError("content_bank.json has no 'entries'")

    seen: set[str] = set()
    for entry in entries:
        cid = entry.get("id")
        if not cid:
            raise ContentBankError(f"Entry without an 'id': {entry!r}")
        if cid in seen:
            raise ContentBankError(f"Duplicate content id: {cid}")
        seen.add(cid)
        if not entry.get("headline"):
            raise ContentBankError(f"Entry {cid} has no 'headline'")

    bank.setdefault("hashtag_sets", {})
    return bank


def bank_stats() -> dict[str, Any]:
    bank = load_bank()
    entries = bank["entries"]
    used = set(state.load()["used_content_ids"])
    themes: dict[str, int] = {}
    for entry in entries:
        theme = entry.get("theme", "general")
        themes[theme] = themes.get(theme, 0) + 1
    return {
        "total_entries": len(entries),
        "used": len(used & {e["id"] for e in entries}),
        "remaining": len([e for e in entries if e["id"] not in used]),
        "themes": themes,
        "days_of_content_left": len([e for e in entries if e["id"] not in used]) // 5,
    }


def select(count: int, theme: str | None = None,
           seed: str | None = None,
           allow_repeats: bool = False) -> list[dict[str, Any]]:
    """Pick `count` entries that have not been used before.

    The rotation used to reset itself once the bank ran dry, so the daily job
    could never fail - but that also meant quotes silently came round again.
    The owner's rule is that a quote never repeats, so an exhausted bank is now
    a loud failure instead: better a missing day he can fix than a repeat he
    only notices in the feed. `allow_repeats=True` is the deliberate override.
    """
    bank = load_bank()
    entries = [e for e in bank["entries"]
               if theme is None or e.get("theme") == theme]
    if not entries:
        raise ContentBankError(f"No entries for theme {theme!r}")

    used = set() if allow_repeats else set(state.load()["used_content_ids"])
    fresh = [e for e in entries if e["id"] not in used]

    if len(fresh) < count:
        raise ContentBankError(
            f"Only {len(fresh)} unused entries left"
            + (f" for theme {theme!r}" if theme else "")
            + f", need {count}. Add new quotes to content_bank.json - the "
            f"rotation no longer recycles used ones, because a repeat in the "
            f"feed is worse than a day that did not go out."
        )

    if len(fresh) <= LOW_BANK_WARNING:
        log_low_bank(len(fresh))

    rng = random.Random(seed) if seed else random.Random()
    rng.shuffle(fresh)

    chosen: list[dict[str, Any]] = []
    seen_themes: list[str] = []
    # Spread themes across the day's batch rather than posting five of a kind.
    for entry in fresh:
        if len(chosen) >= count:
            break
        entry_theme = entry.get("theme", "general")
        if entry_theme in seen_themes and len(fresh) > count * 2:
            continue
        chosen.append(entry)
        seen_themes.append(entry_theme)

    for entry in fresh:
        if len(chosen) >= count:
            break
        if entry not in chosen:
            chosen.append(entry)

    return chosen[:count]


def build_caption(entry: dict[str, Any], platform: str = "instagram",
                  include_cta: bool = True, seed: str | None = None) -> str:
    """Assemble the final caption: body, CTA, then hashtags."""
    bank = load_bank()
    sets = bank["hashtag_sets"]
    rng = random.Random(seed or entry["id"])

    body = entry.get("caption") or entry["headline"]
    parts = [body.strip()]

    if include_cta:
        parts.append(rng.choice(CTA_LINES))

    tags: list[str] = []
    for tag in sets.get("core", []):
        if tag not in tags:
            tags.append(tag)
    for tag in entry.get("hashtags", sets.get(entry.get("theme", ""), [])):
        if tag not in tags:
            tags.append(tag)

    # Top up with tags from other themes so the set is not too narrow.
    extras = [t for key, group in sets.items() if key != "core"
              for t in group if t not in tags]
    rng.shuffle(extras)
    tags.extend(extras[: max(0, MAX_HASHTAGS - len(tags))])
    tags = tags[:MAX_HASHTAGS]

    if platform == "facebook":
        # Facebook readers respond badly to hashtag walls.
        tags = tags[:5]

    parts.append(" ".join(tags))
    return "\n\n".join(p for p in parts if p)
