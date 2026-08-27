"""Command line runner for the daily job.

Used by Windows Task Scheduler. Generation is always safe to run; publishing
requires --confirm so a mis-scheduled task can never post by accident.

    python daily_run.py generate --count 1
    python daily_run.py publish --confirm
    python daily_run.py auto --count 1 --confirm
    python daily_run.py status

The cloud uses the Drive review flow instead - generate into 'Pending', post
only what a human moved into 'Approved':

    python daily_run.py review --count 1
    python daily_run.py publish-approved --confirm
    python daily_run.py drive-check
"""

from __future__ import annotations

import argparse
import json
import shutil
import sys
import tempfile
import traceback
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from shashi_social import brand, content, drive, meta_api, pipeline, state  # noqa: E402

LOG_FILE = brand.STATE_DIR / "daily_run.log"


def posted_today(day: str) -> bool:
    """Has anything for `day` already gone live successfully?

    The cloud run regenerates the batch from scratch every time (output/ is not
    in the repo), so a re-run of the workflow would pick fresh quotes, land on
    different filenames and sail straight past the per-image duplicate check.
    This is the coarser guard that makes a second run of the same day a no-op.
    """
    return any(record.get("date") == day and record.get("ok")
               for record in state.load()["posts"])


def log(message: str) -> None:
    stamp = datetime.now(timezone.utc).isoformat(timespec="seconds")
    line = f"[{stamp}] {message}"
    print(line, flush=True)
    brand.STATE_DIR.mkdir(parents=True, exist_ok=True)
    with open(LOG_FILE, "a", encoding="utf-8") as handle:
        handle.write(line + "\n")


def cmd_generate(args: argparse.Namespace) -> int:
    day = args.date or pipeline.today()
    try:
        batch = pipeline.generate_day(
            count=args.count, day=day, canvas=args.canvas,
            theme=args.theme, overwrite=args.overwrite,
        )
    except FileExistsError:
        log(f"Batch for {day} already exists - skipping generation.")
        return 0

    log(f"Generated {batch['count']} creatives for {day} "
        f"in {pipeline.batch_dir(day)}")
    for item in batch["items"]:
        log(f"  #{item['index']} [{item['layout']}] {item['headline'][:60]}")
    return 0


def cmd_publish(args: argparse.Namespace) -> int:
    day = args.date or pipeline.today()
    platforms = tuple(p.strip() for p in args.platforms.split(",") if p.strip())

    summary = pipeline.publish_day(
        day, platforms=platforms, dry_run=not args.confirm,
        force=args.force, stop_on_error=not args.keep_going,
    )

    if not args.confirm:
        log(f"DRY RUN for {day}: {len(summary['results'])} creatives ready. "
            f"Re-run with --confirm to publish.")
        return 0

    log(f"Publish {day}: posted={summary['posted']} "
        f"failed={summary['failed']} skipped={summary['skipped']}")
    for result in summary["results"]:
        for platform, outcome in result["platforms"].items():
            if outcome.get("ok"):
                ident = outcome.get("post_id") or outcome.get("media_id")
                log(f"  #{result['index']} {platform}: OK {ident}")
            elif outcome.get("skipped"):
                log(f"  #{result['index']} {platform}: skipped "
                    f"({outcome.get('reason')})")
            else:
                log(f"  #{result['index']} {platform}: FAILED "
                    f"{outcome.get('error')}")
    return 1 if summary["failed"] else 0


def cmd_auto(args: argparse.Namespace) -> int:
    day = args.date or pipeline.today()
    if args.skip_if_posted and posted_today(day):
        log(f"Already published for {day} - nothing to do.")
        return 0
    rc = cmd_generate(args)
    if rc != 0:
        return rc
    return cmd_publish(args)


# --------------------------------------------------------------------------
# Drive review flow: generate -> Pending -> (you approve) -> Posted
# --------------------------------------------------------------------------

def cmd_review(args: argparse.Namespace) -> int:
    """Render the day's creatives and park them in Drive for approval."""
    day = args.date or pipeline.today()
    review = drive.Review()
    review.probe()          # an unreachable remote lists as "empty" - catch it here
    review.ensure_folders()

    try:
        batch = pipeline.generate_day(
            count=args.count, day=day, canvas=args.canvas,
            theme=args.theme, overwrite=args.overwrite,
        )
    except FileExistsError:
        log(f"Batch for {day} already exists - uploading it as it stands.")
        batch = pipeline.load_batch(day)

    uploaded = 0
    for item in batch["items"]:
        name = drive.review_filename(day, item["index"], item["content_id"])
        sidecar = Path(item["image_path"]).with_suffix(".caption.json")
        drive.write_sidecar(sidecar, item, day)
        try:
            review.upload(Path(item["image_path"]), drive.PENDING, name)
            review.upload(sidecar, drive.PENDING, drive.sidecar_name(name))
        except drive.DriveError as exc:
            log(f"  #{item['index']} upload FAILED: {exc}")
            continue
        uploaded += 1
        log(f"  #{item['index']} -> Pending/{name}")

    log(f"Uploaded {uploaded}/{batch['count']} creatives for {day} to Drive "
        f"'{drive.PENDING}'. Move the ones you want live into "
        f"'{drive.APPROVED}'.")
    return 0 if uploaded else 1


def _post_one(client: meta_api.GraphClient, image: Path, caption_fb: str,
              caption_ig: str, platforms: tuple[str, ...]) -> dict[str, dict]:
    outcomes: dict[str, dict] = {}
    for platform in platforms:
        try:
            if platform == "facebook":
                response = client.post_facebook_photo(image, caption_fb,
                                                      published=True)
                outcomes[platform] = {"ok": True,
                                      "post_id": response.get("post_id"),
                                      "photo_id": response.get("id")}
            else:
                response = client.post_instagram_photo(caption_ig,
                                                       image_path=image)
                outcomes[platform] = {"ok": True,
                                      "media_id": response.get("media_id")}
        except (meta_api.MetaAPIError, meta_api.ConfigError) as exc:
            outcomes[platform] = {"ok": False, "error": str(exc)}
    return outcomes


def cmd_publish_approved(args: argparse.Namespace) -> int:
    """Post everything sitting in Drive 'Approved', then move it to 'Posted'."""
    platforms = tuple(p.strip() for p in args.platforms.split(",") if p.strip())
    review = drive.Review()
    review.probe()          # an unreachable remote lists as "empty" - catch it here
    review.ensure_folders()

    queue = [(name, drive.APPROVED) for name in review.list_files(drive.APPROVED)]
    if args.include_pending:
        queue += [(name, drive.PENDING) for name in review.list_files(drive.PENDING)]

    if not queue:
        where = "Approved+Pending" if args.include_pending else "Approved"
        log(f"Nothing to post - {where} is empty.")
        return 0

    if not args.confirm:
        log(f"DRY RUN: {len(queue)} creative(s) ready to post: "
            f"{', '.join(f'{n} [{f}]' for n, f in queue)}. "
            f"Re-run with --confirm to publish.")
        return 0

    client = meta_api.GraphClient()
    work = Path(tempfile.mkdtemp(prefix="shashi-approved-"))
    posted = failed = 0

    try:
        for name, folder in queue:
            log(f"--- {name} (from {folder})")
            image = work / name
            if not review.download(folder, name, image):
                log("  download failed - left in place for the next run.")
                failed += 1
                continue

            # The caption usually stays in Pending even after you drag the image
            # into Approved, so look there too before giving up.
            cap_name = drive.sidecar_name(name)
            cap_local = work / cap_name
            cap_folder = None
            for candidate in (folder, drive.PENDING, drive.APPROVED):
                if review.download(candidate, cap_name, cap_local):
                    cap_folder = candidate
                    break
            if cap_folder is None:
                log("  no caption file found - skipping (a caption is the post).")
                failed += 1
                continue

            sidecar = drive.read_sidecar(cap_local)
            outcomes = _post_one(client, image, sidecar["caption_facebook"],
                                 sidecar["caption_instagram"], platforms)

            any_ok = False
            for platform, outcome in outcomes.items():
                if outcome.get("ok"):
                    any_ok = True
                    ident = outcome.get("post_id") or outcome.get("media_id")
                    log(f"  {platform}: OK {ident}")
                else:
                    log(f"  {platform}: FAILED {outcome.get('error')}")
                state.record_post({
                    "platform": platform,
                    "date": sidecar.get("date"),
                    "index": sidecar.get("index"),
                    "image_path": name,
                    "content_id": sidecar.get("content_id"),
                    **outcome,
                })

            if any_ok:
                review.move(folder, drive.POSTED, name)
                review.move(cap_folder, drive.POSTED, cap_name)
                log("  -> moved to Posted.")
                posted += 1
            else:
                log(f"  nothing posted - left in {folder} to retry.")
                failed += 1
    finally:
        shutil.rmtree(work, ignore_errors=True)

    log(f"Publish approved: posted={posted} failed={failed}")
    return 1 if failed else 0


def cmd_drive_check(args: argparse.Namespace) -> int:
    print(json.dumps(drive.Review().check(), indent=2))
    return 0


def cmd_status(args: argparse.Namespace) -> int:
    status = {
        "today": pipeline.today(),
        "batches": pipeline.list_batches()[-10:],
        "content_bank": content.bank_stats(),
        "meta": meta_api.config_status(),
        "backgrounds": len(list((brand.BACKGROUND_DIR).glob("*")))
                       if brand.BACKGROUND_DIR.is_dir() else 0,
    }
    print(json.dumps(status, indent=2))
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = parser.add_subparsers(dest="command", required=True)

    def add_common(p: argparse.ArgumentParser) -> None:
        p.add_argument("--date", default="", help="YYYY-MM-DD (default: today)")

    gen = sub.add_parser("generate", help="Render the day's creatives")
    add_common(gen)
    gen.add_argument("--count", type=int, default=1)
    gen.add_argument("--canvas", default="portrait",
                     choices=sorted(brand.CANVAS))
    gen.add_argument("--theme", default=None)
    gen.add_argument("--overwrite", action="store_true")
    gen.set_defaults(func=cmd_generate)

    pub = sub.add_parser("publish", help="Publish an existing batch")
    add_common(pub)
    pub.add_argument("--platforms", default="facebook,instagram")
    pub.add_argument("--confirm", action="store_true",
                     help="Actually post. Without this it is a dry run.")
    pub.add_argument("--force", action="store_true",
                     help="Re-post creatives already published")
    pub.add_argument("--keep-going", action="store_true",
                     help="Continue after a failure instead of stopping")
    pub.set_defaults(func=cmd_publish)

    auto = sub.add_parser("auto", help="Generate then publish in one run")
    add_common(auto)
    auto.add_argument("--count", type=int, default=1)
    auto.add_argument("--canvas", default="portrait", choices=sorted(brand.CANVAS))
    auto.add_argument("--theme", default=None)
    auto.add_argument("--overwrite", action="store_true")
    auto.add_argument("--platforms", default="facebook,instagram")
    auto.add_argument("--confirm", action="store_true")
    auto.add_argument("--force", action="store_true")
    auto.add_argument("--keep-going", action="store_true")
    auto.add_argument("--skip-if-posted", action="store_true",
                      help="Do nothing if this day already published (safe re-runs)")
    auto.set_defaults(func=cmd_auto)

    rev = sub.add_parser("review",
                         help="Render the day and upload it to Drive 'Pending'")
    add_common(rev)
    rev.add_argument("--count", type=int, default=1)
    rev.add_argument("--canvas", default="portrait", choices=sorted(brand.CANVAS))
    rev.add_argument("--theme", default=None)
    rev.add_argument("--overwrite", action="store_true")
    rev.set_defaults(func=cmd_review)

    app = sub.add_parser("publish-approved",
                         help="Post what you moved into Drive 'Approved'")
    app.add_argument("--platforms", default="facebook,instagram")
    app.add_argument("--confirm", action="store_true",
                     help="Actually post. Without this it is a dry run.")
    app.add_argument("--include-pending", action="store_true",
                     help="Also post anything still awaiting approval (cutoff run)")
    app.set_defaults(func=cmd_publish_approved)

    chk = sub.add_parser("drive-check",
                         help="Show the Drive remote and what is in each folder")
    chk.set_defaults(func=cmd_drive_check)

    st = sub.add_parser("status", help="Show configuration and rotation state")
    st.set_defaults(func=cmd_status)

    return parser


def main() -> int:
    args = build_parser().parse_args()
    try:
        return args.func(args)
    except (meta_api.ConfigError, drive.DriveError, FileNotFoundError) as exc:
        # Expected, actionable problems - no stack trace needed.
        log(f"NOT READY: {exc}")
        return 3
    except Exception as exc:  # noqa: BLE001 - scheduled task must log, not vanish
        log(f"ERROR: {exc}")
        log(traceback.format_exc())
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
