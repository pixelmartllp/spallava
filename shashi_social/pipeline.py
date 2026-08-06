"""Daily batch pipeline: generate a day's creatives, then publish them.

A batch lives in output/<YYYY-MM-DD>/ alongside a batch.json manifest that
carries the captions and per-platform publish status. Generation and
publishing are deliberately separate steps so a human can review the images
before anything reaches a live Page.
"""

from __future__ import annotations

import json
from datetime import date as date_cls
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from PIL import Image as PILImage

from . import brand, content, meta_api, renderer, state

MANIFEST_NAME = "batch.json"
PLATFORMS = ("facebook", "instagram")

# Instagram rejects oversized files; keep well under the 8 MB limit.
MAX_UPLOAD_BYTES = 7 * 1024 * 1024


def today() -> str:
    return date_cls.today().isoformat()


_today = today  # internal alias kept for readability inside this module


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def batch_dir(day: str) -> Path:
    return brand.OUTPUT_DIR / day


def manifest_path(day: str) -> Path:
    return batch_dir(day) / MANIFEST_NAME


def load_batch(day: str) -> dict[str, Any]:
    path = manifest_path(day)
    if not path.is_file():
        raise FileNotFoundError(
            f"No batch for {day}. Run generate_daily_creatives first."
        )
    return json.loads(path.read_text(encoding="utf-8"))


def save_batch(batch: dict[str, Any]) -> None:
    path = manifest_path(batch["date"])
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(batch, indent=2, ensure_ascii=False),
                    encoding="utf-8")


def list_batches() -> list[str]:
    if not brand.OUTPUT_DIR.is_dir():
        return []
    return sorted(d.name for d in brand.OUTPUT_DIR.iterdir()
                  if d.is_dir() and (d / MANIFEST_NAME).is_file())


# --------------------------------------------------------------------------
# Generation
# --------------------------------------------------------------------------

def generate_day(count: int = 5, day: str | None = None,
                 canvas: str = brand.DEFAULT_CANVAS,
                 theme: str | None = None,
                 layout: str | None = None,
                 overwrite: bool = False) -> dict[str, Any]:
    """Render `count` creatives for `day` and write the manifest."""
    brand.ensure_dirs()
    day = day or _today()

    if manifest_path(day).is_file() and not overwrite:
        raise FileExistsError(
            f"A batch already exists for {day}. Pass overwrite=true to replace "
            f"it, or use regenerate_creative to redo a single image."
        )

    if count < 1 or count > 20:
        raise ValueError("count must be between 1 and 20")

    entries = content.select(count, theme=theme, seed=day)
    recent_bg = state.recent_backgrounds()

    out_dir = batch_dir(day)
    out_dir.mkdir(parents=True, exist_ok=True)

    items: list[dict[str, Any]] = []
    used_backgrounds: list[str] = []

    for index, entry in enumerate(entries, start=1):
        slug = entry["id"]
        out_path = out_dir / f"{index:02d}-{slug}.jpg"
        meta = renderer.render(
            entry, out_path, canvas_name=canvas, layout=layout,
            seed=f"{day}-{slug}",
            exclude_backgrounds=recent_bg | set(used_backgrounds),
        )
        if meta["background"] != "generated":
            used_backgrounds.append(meta["background"])

        meta["index"] = index
        meta["caption_instagram"] = content.build_caption(
            entry, platform="instagram", seed=f"{day}-{slug}")
        meta["caption_facebook"] = content.build_caption(
            entry, platform="facebook", seed=f"{day}-{slug}")
        meta["status"] = {p: None for p in PLATFORMS}
        items.append(meta)

    state.mark_content_used([e["id"] for e in entries])
    if used_backgrounds:
        state.mark_background_used(used_backgrounds)

    batch = {
        "date": day,
        "created_at": _now(),
        "canvas": canvas,
        "theme": theme,
        "count": len(items),
        "items": items,
    }
    save_batch(batch)
    return batch


def regenerate_item(day: str, index: int, layout: str | None = None,
                    seed_suffix: str = "v2") -> dict[str, Any]:
    """Re-render a single creative, e.g. to try a different layout."""
    batch = load_batch(day)
    item = _find_item(batch, index)

    bank = content.load_bank()
    entry = next((e for e in bank["entries"] if e["id"] == item["content_id"]), None)
    if entry is None:
        raise ValueError(
            f"Content id {item['content_id']} is no longer in the bank."
        )

    out_path = Path(item["image_path"])
    meta = renderer.render(
        entry, out_path, canvas_name=batch.get("canvas", brand.DEFAULT_CANVAS),
        layout=layout, seed=f"{day}-{entry['id']}-{seed_suffix}",
        exclude_backgrounds=state.recent_backgrounds(),
    )
    meta.update({
        "index": index,
        "caption_instagram": item["caption_instagram"],
        "caption_facebook": item["caption_facebook"],
        "status": item["status"],
    })
    batch["items"][batch["items"].index(item)] = meta
    save_batch(batch)
    return meta


def find_item(batch: dict[str, Any], index: int) -> dict[str, Any]:
    for item in batch["items"]:
        if item["index"] == index:
            return item
    valid = [i["index"] for i in batch["items"]]
    raise ValueError(f"No creative #{index} in this batch. Valid: {valid}")


_find_item = find_item


# --------------------------------------------------------------------------
# Publishing
# --------------------------------------------------------------------------

def _prepare_upload(image_path: Path) -> Path:
    """Guarantee a JPEG that is small enough for the Graph API."""
    image_path = Path(image_path)
    if not image_path.is_file():
        raise FileNotFoundError(f"Creative missing on disk: {image_path}")

    needs_convert = image_path.suffix.lower() not in (".jpg", ".jpeg")
    too_big = image_path.stat().st_size > MAX_UPLOAD_BYTES
    if not needs_convert and not too_big:
        return image_path

    upload = image_path.with_name(image_path.stem + "-upload.jpg")
    img = PILImage.open(image_path).convert("RGB")
    quality = 92
    while True:
        img.save(upload, format="JPEG", quality=quality, optimize=True)
        if upload.stat().st_size <= MAX_UPLOAD_BYTES or quality <= 60:
            break
        quality -= 8
    return upload


def publish_item(day: str, index: int, platforms: tuple[str, ...] = PLATFORMS,
                 dry_run: bool = True, force: bool = False) -> dict[str, Any]:
    """Publish one creative. `dry_run` reports what would happen and stops."""
    batch = load_batch(day)
    item = _find_item(batch, index)

    unknown = [p for p in platforms if p not in PLATFORMS]
    if unknown:
        raise ValueError(f"Unknown platform(s): {unknown}. Use {list(PLATFORMS)}")

    image_path = Path(item["image_path"])
    results: dict[str, Any] = {"date": day, "index": index,
                               "image_path": str(image_path),
                               "dry_run": dry_run, "platforms": {}}

    if dry_run:
        for platform in platforms:
            prior = state.already_posted(str(image_path), platform)
            results["platforms"][platform] = {
                "would_post": True,
                "already_posted": bool(prior),
                "caption_preview": item[f"caption_{platform}"][:220],
            }
        return results

    client = meta_api.GraphClient()
    upload_path = _prepare_upload(image_path)

    for platform in platforms:
        prior = state.already_posted(str(image_path), platform)
        if prior and not force:
            results["platforms"][platform] = {
                "ok": False, "skipped": True,
                "reason": "Already published. Pass force=true to post again.",
                "previous": prior,
            }
            continue

        try:
            if platform == "facebook":
                response = client.post_facebook_photo(
                    upload_path, item["caption_facebook"], published=True)
                record = {"ok": True, "post_id": response.get("post_id"),
                          "photo_id": response.get("id")}
            else:
                response = client.post_instagram_photo(
                    item["caption_instagram"], image_path=upload_path)
                record = {"ok": True, "media_id": response.get("media_id")}
        except (meta_api.MetaAPIError, meta_api.ConfigError) as exc:
            record = {"ok": False, "error": str(exc)}

        results["platforms"][platform] = record
        item["status"][platform] = {
            **{k: v for k, v in record.items() if k != "previous"},
            "at": _now(),
        }
        state.record_post({
            "platform": platform,
            "date": day,
            "index": index,
            "image_path": str(image_path),
            "content_id": item["content_id"],
            **record,
        })

    if upload_path != image_path:
        upload_path.unlink(missing_ok=True)

    save_batch(batch)
    return results


def publish_day(day: str | None = None,
                platforms: tuple[str, ...] = PLATFORMS,
                dry_run: bool = True, force: bool = False,
                stop_on_error: bool = True) -> dict[str, Any]:
    """Publish every creative in a batch, in order."""
    day = day or _today()
    batch = load_batch(day)

    summary: dict[str, Any] = {"date": day, "dry_run": dry_run,
                               "results": [], "posted": 0, "failed": 0,
                               "skipped": 0}

    for item in batch["items"]:
        result = publish_item(day, item["index"], platforms=platforms,
                              dry_run=dry_run, force=force)
        summary["results"].append(result)

        if dry_run:
            continue

        failed = False
        for outcome in result["platforms"].values():
            if outcome.get("skipped"):
                summary["skipped"] += 1
            elif outcome.get("ok"):
                summary["posted"] += 1
            else:
                summary["failed"] += 1
                failed = True

        if failed and stop_on_error:
            summary["stopped_early"] = True
            summary["stopped_at_index"] = item["index"]
            break

    return summary
