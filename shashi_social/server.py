"""MCP server for the Shashi Pallava daily social pipeline.

Exposes the whole workflow as tools: check setup, generate the day's
creatives, preview them, then publish to Facebook and Instagram.

Publishing is guarded. Every posting tool defaults to a dry run and will not
touch the live Page unless it is called with confirm=True.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from mcp.server.fastmcp import FastMCP
from mcp.server.fastmcp.utilities.types import Image as MCPImage

from . import assets, brand, content, meta_api, pipeline, renderer, state

mcp = FastMCP(
    "shashi-social",
    instructions=(
        "Daily creative generation and publishing for the Shashi Pallava "
        "life & relationship coaching brand (facebook.com/shashipallava).\n\n"
        "Normal flow: check_setup -> generate_daily_creatives -> "
        "preview_creative for each -> publish_batch(confirm=True).\n\n"
        "Publishing tools are dry-run by default. Never pass confirm=True "
        "unless the user has explicitly approved posting to the live Page."
    ),
)


def _ok(**payload: Any) -> str:
    return json.dumps({"ok": True, **payload}, indent=2, ensure_ascii=False,
                      default=str)


def _err(message: str, **payload: Any) -> str:
    return json.dumps({"ok": False, "error": message, **payload}, indent=2,
                      ensure_ascii=False, default=str)


# --------------------------------------------------------------------------
# Setup and diagnostics
# --------------------------------------------------------------------------

@mcp.tool()
def check_setup() -> str:
    """Health check: fonts, logo, background pool, content bank, Meta config.

    Run this first. It reports exactly what still needs configuring.
    """
    brand.ensure_dirs()
    report: dict[str, Any] = {"project_root": str(brand.ROOT)}
    todo: list[str] = []

    try:
        logo = assets.prepare_logo()
        report["logo"] = {"source": str(brand.LOGO_SOURCE),
                          "transparent_cache": str(logo), "ready": True}
    except FileNotFoundError as exc:
        report["logo"] = {"ready": False, "error": str(exc)}
        todo.append(f"Copy the brand logo to {brand.LOGO_SOURCE}")

    backgrounds = assets.list_backgrounds()
    report["backgrounds"] = {
        "folder": str(brand.BACKGROUND_DIR),
        "count": len(backgrounds),
        "files": [p.name for p in backgrounds[:20]],
    }
    if not backgrounds:
        todo.append(
            f"Optional: drop clean photos (no text) into {brand.BACKGROUND_DIR}. "
            f"Until then, on-brand abstract backgrounds are generated instead."
        )

    report["fonts"] = brand.font_report()
    if "Playfair" not in json.dumps(report["fonts"]):
        todo.append(
            f"Optional: drop PlayfairDisplay-SemiBold.ttf into {brand.FONT_DIR} "
            f"for a closer match to the sample creatives."
        )

    try:
        report["content_bank"] = content.bank_stats()
        if report["content_bank"]["remaining"] < 10:
            todo.append("Content bank is nearly used up - add more entries "
                        "with add_content_entry.")
    except content.ContentBankError as exc:
        report["content_bank"] = {"error": str(exc)}
        todo.append("Fix content_bank.json")

    meta_status = meta_api.config_status()
    report["meta"] = meta_status
    if not meta_status["ready_for_facebook"]:
        todo.append(f"Add page_id and access_token to {meta_api.CONFIG_FILE} "
                    f"(see SETUP.md).")
    if not meta_status["ready_for_instagram"]:
        todo.append("Add ig_user_id for Instagram posting "
                    "(run discover_meta_accounts once credentials work).")

    report["batches"] = pipeline.list_batches()[-10:]
    report["next_steps"] = todo or ["Everything is configured. "
                                    "Run generate_daily_creatives."]
    return _ok(**report)


@mcp.tool()
def discover_meta_accounts() -> str:
    """List Facebook Pages this token manages, with their Instagram IDs.

    Use this to find the page_id and ig_user_id values for config.json.
    """
    try:
        return _ok(**meta_api.GraphClient().discover())
    except (meta_api.MetaAPIError, meta_api.ConfigError) as exc:
        return _err(str(exc))


@mcp.tool()
def verify_meta_credentials() -> str:
    """Check the access token, Page access and Instagram link are all working."""
    try:
        return _ok(**meta_api.GraphClient().verify())
    except (meta_api.MetaAPIError, meta_api.ConfigError) as exc:
        return _err(str(exc))


# --------------------------------------------------------------------------
# Content bank
# --------------------------------------------------------------------------

@mcp.tool()
def content_bank_status() -> str:
    """How many quotes are left before the rotation repeats."""
    try:
        return _ok(**content.bank_stats())
    except content.ContentBankError as exc:
        return _err(str(exc))


@mcp.tool()
def add_content_entry(headline: str, theme: str, caption: str,
                      accent: str = "", bullets: str = "",
                      entry_id: str = "") -> str:
    """Add a new post idea to the content bank.

    Args:
        headline: The main line on the creative.
        theme: One of self_worth, relationships, healing, boundaries,
            growth, morning, anxiety, letting_go.
        caption: The post caption (without hashtags - those are added).
        accent: Optional second line, rendered in rose.
        bullets: Optional pipe-separated list, e.g. "clarity|consistency".
            Providing bullets switches the creative to the arch-card layout.
        entry_id: Optional explicit id; auto-generated when omitted.
    """
    try:
        bank = content.load_bank()
    except content.ContentBankError as exc:
        return _err(str(exc))

    existing = {e["id"] for e in bank["entries"]}
    if not entry_id:
        n = len(bank["entries"]) + 1
        while f"q{n:03d}" in existing:
            n += 1
        entry_id = f"q{n:03d}"
    if entry_id in existing:
        return _err(f"Content id {entry_id} already exists.")

    entry: dict[str, Any] = {"id": entry_id, "theme": theme,
                             "headline": headline, "caption": caption}
    if accent:
        entry["accent"] = accent
    if bullets:
        entry["bullets"] = [b.strip() for b in bullets.split("|") if b.strip()]

    bank["entries"].append(entry)
    content.BANK_FILE.write_text(
        json.dumps(bank, indent=2, ensure_ascii=False), encoding="utf-8")
    return _ok(added=entry, total_entries=len(bank["entries"]))


# --------------------------------------------------------------------------
# Generation
# --------------------------------------------------------------------------

@mcp.tool()
def generate_daily_creatives(count: int = 5, date: str = "",
                             theme: str = "", canvas: str = "portrait",
                             layout: str = "", overwrite: bool = False) -> str:
    """Generate the day's creatives with the logo applied. Does not publish.

    Args:
        count: How many creatives to make (default 5).
        date: YYYY-MM-DD. Defaults to today.
        theme: Restrict to one theme. Empty means a mixed batch.
        canvas: portrait (1080x1350), square, or story.
        layout: Force one layout for the whole batch. Empty means auto.
        overwrite: Replace an existing batch for that date.
    """
    try:
        batch = pipeline.generate_day(
            count=count, day=date or None, canvas=canvas,
            theme=theme or None, layout=layout or None, overwrite=overwrite,
        )
    except (FileExistsError, ValueError, content.ContentBankError,
            FileNotFoundError) as exc:
        return _err(str(exc))

    return _ok(
        date=batch["date"],
        folder=str(pipeline.batch_dir(batch["date"])),
        count=batch["count"],
        items=[{
            "index": i["index"],
            "content_id": i["content_id"],
            "theme": i["theme"],
            "headline": i["headline"],
            "accent": i.get("accent"),
            "layout": i["layout"],
            "background": i["background"],
            "image_path": i["image_path"],
        } for i in batch["items"]],
        next_step=("Preview each with preview_creative, then publish with "
                   "publish_batch(date, confirm=True)."),
    )


@mcp.tool()
def list_batch(date: str = "") -> str:
    """Show a day's creatives with their captions and publish status."""
    day = date or pipeline.today()
    try:
        batch = pipeline.load_batch(day)
    except FileNotFoundError as exc:
        return _err(str(exc), available_batches=pipeline.list_batches()[-10:])
    return _ok(**batch)


@mcp.tool()
def list_batches() -> str:
    """List every generated batch by date."""
    return _ok(batches=pipeline.list_batches())


@mcp.tool()
def preview_creative(date: str = "", index: int = 1) -> Any:
    """Return a rendered creative as an image so it can be reviewed.

    Annotated as Any because it returns either an image or a JSON error
    string, and a union of the two has no pydantic schema.
    """
    day = date or pipeline.today()
    try:
        batch = pipeline.load_batch(day)
        item = pipeline.find_item(batch, index)
    except (FileNotFoundError, ValueError) as exc:
        return _err(str(exc))

    path = Path(item["image_path"])
    if not path.is_file():
        return _err(f"Image missing on disk: {path}")
    return MCPImage(path=path)


@mcp.tool()
def regenerate_creative(date: str = "", index: int = 1,
                        layout: str = "") -> str:
    """Re-render one creative, optionally forcing a different layout.

    Layouts: paper_quote, arch_card (both work without a background photo),
    quote_left, center_overlay, soft_band (these assume a photo fills the
    frame and are only auto-selected when the background pool has one).
    """
    day = date or pipeline.today()
    try:
        meta = pipeline.regenerate_item(day, index, layout=layout or None)
    except (FileNotFoundError, ValueError) as exc:
        return _err(str(exc))
    return _ok(regenerated=meta, available_layouts=list(renderer.LAYOUTS))


@mcp.tool()
def edit_caption(date: str = "", index: int = 1, platform: str = "both",
                 caption: str = "") -> str:
    """Replace the caption for a creative before publishing.

    Args:
        platform: facebook, instagram, or both.
    """
    day = date or pipeline.today()
    if not caption.strip():
        return _err("caption cannot be empty")
    if platform not in ("facebook", "instagram", "both"):
        return _err("platform must be facebook, instagram or both")

    try:
        batch = pipeline.load_batch(day)
        item = pipeline.find_item(batch, index)
    except (FileNotFoundError, ValueError) as exc:
        return _err(str(exc))

    targets = ("facebook", "instagram") if platform == "both" else (platform,)
    for target in targets:
        item[f"caption_{target}"] = caption
    pipeline.save_batch(batch)
    return _ok(index=index, updated=list(targets),
               caption_facebook=item["caption_facebook"],
               caption_instagram=item["caption_instagram"])


# --------------------------------------------------------------------------
# Publishing
# --------------------------------------------------------------------------

def _platform_tuple(platforms: str) -> tuple[str, ...]:
    if platforms in ("", "both", "all"):
        return pipeline.PLATFORMS
    return tuple(p.strip() for p in platforms.split(",") if p.strip())


@mcp.tool()
def publish_creative(date: str = "", index: int = 1, platforms: str = "both",
                     confirm: bool = False, force: bool = False) -> str:
    """Publish ONE creative to Facebook and/or Instagram.

    Args:
        platforms: "both", "facebook", "instagram", or a comma-separated list.
        confirm: Must be True to actually post. False returns a dry-run plan.
        force: Post again even if this image was already published.

    This posts publicly to a live business Page. Only pass confirm=True when
    the user has explicitly approved this specific action.
    """
    day = date or pipeline.today()
    try:
        result = pipeline.publish_item(
            day, index, platforms=_platform_tuple(platforms),
            dry_run=not confirm, force=force,
        )
    except (FileNotFoundError, ValueError, meta_api.ConfigError) as exc:
        return _err(str(exc))

    if not confirm:
        result["note"] = ("Dry run - nothing was posted. Call again with "
                          "confirm=true to publish.")
    return _ok(**result)


@mcp.tool()
def publish_batch(date: str = "", platforms: str = "both",
                  confirm: bool = False, force: bool = False,
                  stop_on_error: bool = True) -> str:
    """Publish an ENTIRE day's batch to Facebook and/or Instagram.

    Args:
        platforms: "both", "facebook", "instagram", or a comma-separated list.
        confirm: Must be True to actually post. False returns a dry-run plan.
        force: Re-post creatives that were already published.
        stop_on_error: Halt the run after the first failure.

    This posts publicly to a live business Page. Only pass confirm=True when
    the user has explicitly approved publishing this batch.
    """
    day = date or pipeline.today()
    try:
        summary = pipeline.publish_day(
            day, platforms=_platform_tuple(platforms),
            dry_run=not confirm, force=force, stop_on_error=stop_on_error,
        )
    except (FileNotFoundError, ValueError, meta_api.ConfigError) as exc:
        return _err(str(exc))

    if not confirm:
        summary["note"] = ("Dry run - nothing was posted. Call again with "
                           "confirm=true to publish all of them.")
    return _ok(**summary)


@mcp.tool()
def publish_history(limit: int = 20) -> str:
    """Recent publish attempts recorded by this pipeline."""
    return _ok(posts=state.post_history(limit))


@mcp.tool()
def page_recent_posts(limit: int = 10) -> str:
    """Fetch what is actually live on the Facebook Page right now."""
    try:
        return _ok(**meta_api.GraphClient().recent_posts(limit))
    except (meta_api.MetaAPIError, meta_api.ConfigError) as exc:
        return _err(str(exc))


def main() -> None:
    mcp.run()


if __name__ == "__main__":
    main()

