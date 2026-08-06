"""Small JSON-backed state store.

Tracks which content has been used and what has actually been published, so a
daily run never repeats a quote and never double-posts the same creative.
"""

from __future__ import annotations

import json
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from . import brand

STATE_FILE = brand.STATE_DIR / "state.json"

_DEFAULT: dict[str, Any] = {
    "used_content_ids": [],
    "used_backgrounds": [],
    "posts": [],
}


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def load() -> dict[str, Any]:
    if not STATE_FILE.is_file():
        return json.loads(json.dumps(_DEFAULT))
    try:
        data = json.loads(STATE_FILE.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return json.loads(json.dumps(_DEFAULT))
    for key, value in _DEFAULT.items():
        data.setdefault(key, json.loads(json.dumps(value)))
    return data


def save(data: dict[str, Any]) -> None:
    """Atomic write, so an interrupted run cannot corrupt the state file."""
    brand.STATE_DIR.mkdir(parents=True, exist_ok=True)
    fd, tmp_name = tempfile.mkstemp(dir=str(brand.STATE_DIR), suffix=".tmp")
    tmp = Path(tmp_name)
    try:
        with open(fd, "w", encoding="utf-8") as handle:
            json.dump(data, handle, indent=2, ensure_ascii=False)
        tmp.replace(STATE_FILE)
    except BaseException:
        tmp.unlink(missing_ok=True)
        raise


def mark_content_used(content_ids: list[str]) -> None:
    data = load()
    used = data["used_content_ids"]
    for cid in content_ids:
        if cid not in used:
            used.append(cid)
    save(data)


def reset_content_rotation() -> None:
    data = load()
    data["used_content_ids"] = []
    save(data)


def mark_background_used(names: list[str], keep_last: int = 25) -> None:
    """Remember recent backgrounds so consecutive days do not look identical."""
    data = load()
    used = [n for n in data["used_backgrounds"] if n not in names]
    used.extend(names)
    data["used_backgrounds"] = used[-keep_last:]
    save(data)


def recent_backgrounds() -> set[str]:
    return set(load()["used_backgrounds"])


def record_post(record: dict[str, Any]) -> None:
    data = load()
    record = {**record, "recorded_at": _now()}
    data["posts"].append(record)
    save(data)


def already_posted(image_path: str, platform: str) -> dict[str, Any] | None:
    """Find a successful publish of this exact image to this platform."""
    target = str(Path(image_path).resolve()).lower()
    for record in reversed(load()["posts"]):
        if record.get("platform") != platform or not record.get("ok"):
            continue
        recorded = record.get("image_path")
        if recorded and str(Path(recorded).resolve()).lower() == target:
            return record
    return None


def post_history(limit: int = 30) -> list[dict[str, Any]]:
    return load()["posts"][-limit:]
