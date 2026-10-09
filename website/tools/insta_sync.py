#!/usr/bin/env python
"""Copy the latest Instagram posts into the homepage's Instagram grid.

    python website/tools/insta_sync.py                  # dry run: list what it would do
    python website/tools/insta_sync.py --preview f.html # also write the feed markup to a file
    python website/tools/insta_sync.py --confirm        # upload images, update the page

The homepage reads a plain WordPress page, slug ``insta-feed``, whose content
is nothing but links around images. This script rewrites that page.

Why it copies the images instead of linking Instagram's: the ``media_url``
the Graph API hands back is a signed CDN address that stops working within
days, so a grid built on it goes blank on its own. Each image is uploaded to
the site's media library once, as ``ig-<media id>.jpg``, and reused after that.

Why it runs here and not in the browser: reading the feed needs the Meta
access token, and anything the page's script can read, every visitor can.
The token never leaves this machine (or the GitHub runner).

This only *reads* Instagram. It has nothing to do with the posting
automation, which is switched off - see CLAUDE.md section 8.

Meta credentials: META_ACCESS_TOKEN and META_IG_USER_ID from the environment,
else the gitignored config.json at the repo root. WordPress credentials: as
for push.py.
"""

from __future__ import annotations

import argparse
import base64
import html
import io
import json
import os
import pathlib
import sys
import urllib.error
import urllib.parse
import urllib.request

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from push import SITE, UA, credentials  # noqa: E402

REPO = pathlib.Path(__file__).resolve().parents[2]
SLUG = "insta-feed"
COUNT = 9
SIZE = 640  # px on the long edge; tiles show at ~130px, 2x on phones


def meta_creds() -> tuple[str, str, str]:
    # Taken as a pair, never mixed: this machine's environment carries a
    # META_IG_USER_ID for an unrelated account, and pairing it with the
    # config.json token gets "Object ... does not exist".
    token = os.environ.get("META_ACCESS_TOKEN")
    ig = os.environ.get("META_IG_USER_ID")
    ver = os.environ.get("META_API_VERSION")
    conf = REPO / "config.json"
    if not (token and ig) and conf.is_file():
        c = json.loads(conf.read_text(encoding="utf-8"))
        token, ig, ver = c.get("access_token"), c.get("ig_user_id"), c.get("api_version")
    if not (token and ig):
        sys.exit("No Meta credentials: set META_ACCESS_TOKEN and META_IG_USER_ID.")
    return token, ig, ver or "v25.0"


def latest_media() -> list[dict]:
    token, ig, ver = meta_creds()
    q = urllib.parse.urlencode({
        "fields": "id,caption,media_type,media_url,thumbnail_url,permalink,timestamp",
        "limit": COUNT, "access_token": token})
    try:
        with urllib.request.urlopen(f"https://graph.facebook.com/{ver}/{ig}/media?{q}",
                                    timeout=60) as r:
            data = json.loads(r.read())
    except urllib.error.HTTPError as exc:
        sys.exit(f"Instagram read failed: {exc.code} {exc.read()[:300].decode('utf-8', 'replace')}")
    out = []
    for m in data.get("data", []):
        src = m.get("thumbnail_url") if m.get("media_type") == "VIDEO" else m.get("media_url")
        if src:
            out.append({**m, "src": src})
    return out


def alt_text(m: dict) -> str:
    first = (m.get("caption") or "").strip().splitlines()
    return (first[0] if first else "Instagram post")[:120]


class WP:
    def __init__(self) -> None:
        user, app = credentials()
        self.auth = "Basic " + base64.b64encode(f"{user}:{app}".encode()).decode()

    def call(self, path: str, data: bytes | None = None, headers: dict | None = None,
             method: str = "GET"):
        h = {"User-Agent": UA, "Authorization": self.auth, **(headers or {})}
        req = urllib.request.Request(SITE + path, data=data, headers=h, method=method)
        with urllib.request.urlopen(req, timeout=90) as r:
            return json.loads(r.read())

    def hosted(self, m: dict) -> str:
        """URL of this post's image on the site, uploading it the first time."""
        slug = f"ig-{m['id']}"
        found = self.call(f"/wp-json/wp/v2/media?slug={slug}&_fields=source_url")
        if found:
            return found[0]["source_url"]
        with urllib.request.urlopen(m["src"], timeout=60) as r:
            raw = r.read()
        from PIL import Image
        im = Image.open(io.BytesIO(raw)).convert("RGB")
        im.thumbnail((SIZE, SIZE))
        buf = io.BytesIO()
        im.save(buf, "JPEG", quality=84, optimize=True, progressive=True)
        made = self.call("/wp-json/wp/v2/media", data=buf.getvalue(), method="POST",
                         headers={"Content-Type": "image/jpeg",
                                  "Content-Disposition": f'attachment; filename="{slug}.jpg"'})
        self.call(f"/wp-json/wp/v2/media/{made['id']}", method="POST",
                  data=json.dumps({"alt_text": alt_text(m), "slug": slug}).encode(),
                  headers={"Content-Type": "application/json"})
        return made["source_url"]

    def write_page(self, content: str) -> str:
        existing = self.call(f"/wp-json/wp/v2/pages?slug={SLUG}&status=publish,draft&_fields=id")
        body = json.dumps({"title": "Instagram Feed", "slug": SLUG, "status": "publish",
                           "content": content}).encode()
        path = f"/wp-json/wp/v2/pages/{existing[0]['id']}" if existing else "/wp-json/wp/v2/pages"
        out = self.call(path, data=body, method="POST",
                        headers={"Content-Type": "application/json"})
        return out["link"]


def feed_markup(items: list[tuple[dict, str]]) -> str:
    # wp:html, and no blank lines, so wpautop leaves it alone
    lines = [f'<a href="{html.escape(m["permalink"])}"><img src="{html.escape(src)}" '
             f'alt="{html.escape(alt_text(m))}"></a>' for m, src in items]
    return "<!-- wp:html -->\n" + "\n".join(lines) + "\n<!-- /wp:html -->"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--confirm", action="store_true", help="upload and update the page")
    ap.add_argument("--preview", help="write the feed markup (Instagram's own URLs) here")
    args = ap.parse_args()

    media = latest_media()
    if not media:
        print("  Instagram returned no posts - leaving the grid as it is")
        return 0
    for m in media:
        print(f"  {m['timestamp'][:10]}  {m['media_type']:<14} {m['permalink']}")

    if args.preview:
        pathlib.Path(args.preview).write_text(feed_markup([(m, m["src"]) for m in media]),
                                              encoding="utf-8")
        print("  preview written to", args.preview)
    if not args.confirm:
        print("  dry run - re-run with --confirm to update the site")
        return 0

    wp = WP()
    try:
        items = [(m, wp.hosted(m)) for m in media]
        link = wp.write_page(feed_markup(items))
    except urllib.error.HTTPError as exc:
        print("  FAILED:", exc.code, exc.read()[:300].decode("utf-8", "replace"))
        return 1
    print(f"  {len(items)} posts on {link}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
