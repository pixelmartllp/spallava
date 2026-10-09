#!/usr/bin/env python
"""Publish the Instagram-linked blog posts in website/blog/posts.json.

    python website/tools/blog_sync.py            # dry run: list what it would do
    python website/tools/blog_sync.py --confirm  # upload creatives, write posts

Each entry names an Instagram post by media id. Its creative is uploaded once,
full size, as ``ig-<id>-full.jpg`` and becomes the post's featured image.
Entries with ``wp_id`` only attach that creative to an existing post; the
others create or update a whole post (matched by slug), dated to the moment
it went up on Instagram. Safe to re-run: nothing is uploaded or created twice.

Credentials as for insta_sync.py (Meta) and push.py (WordPress).
"""

from __future__ import annotations

import argparse
import html
import io
import json
import pathlib
import sys
import urllib.error
import urllib.parse
import urllib.request

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from insta_sync import WP, meta_creds  # noqa: E402

POSTS = pathlib.Path(__file__).resolve().parent.parent / "blog" / "posts.json"


def ig_media(media_id: str) -> dict:
    token, _, ver = meta_creds()
    q = urllib.parse.urlencode({"fields": "media_url,permalink,timestamp,caption",
                                "access_token": token})
    with urllib.request.urlopen(f"https://graph.facebook.com/{ver}/{media_id}?{q}",
                                timeout=60) as r:
        return {**json.loads(r.read()), "id": media_id}


def creative(wp: WP, m: dict, alt: str) -> int:
    """Media id of the full-size creative, uploading it the first time."""
    slug = f"ig-{m['id']}-full"
    found = wp.call(f"/wp-json/wp/v2/media?slug={slug}&_fields=id")
    if found:
        return found[0]["id"]
    with urllib.request.urlopen(m["media_url"], timeout=60) as r:
        raw = r.read()
    from PIL import Image
    im = Image.open(io.BytesIO(raw)).convert("RGB")
    im.thumbnail((1080, 1350))
    buf = io.BytesIO()
    im.save(buf, "JPEG", quality=86, optimize=True, progressive=True)
    made = wp.call("/wp-json/wp/v2/media", data=buf.getvalue(), method="POST",
                   headers={"Content-Type": "image/jpeg",
                            "Content-Disposition": f'attachment; filename="{slug}.jpg"'})
    wp.call(f"/wp-json/wp/v2/media/{made['id']}", method="POST",
            data=json.dumps({"alt_text": alt[:200], "slug": slug}).encode(),
            headers={"Content-Type": "application/json"})
    return made["id"]


def body(e: dict, permalink: str) -> str:
    def para(inner: str) -> str:
        return f"<!-- wp:paragraph -->\n<p>{inner}</p>\n<!-- /wp:paragraph -->"
    parts = [para(f"<strong>{html.escape(e['lead'])}</strong>")]
    parts += [para(html.escape(p)) for p in e["paras"]]
    parts.append(para(f'Ye thought pehle <a href="{html.escape(permalink)}">Instagram par</a> '
                      f"share hua tha."))
    return "\n".join(parts)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--confirm", action="store_true")
    args = ap.parse_args()

    entries = json.loads(POSTS.read_text(encoding="utf-8"))["posts"]
    for e in entries:
        what = f"post {e['wp_id']} gets creative" if "wp_id" in e else f"new post /{e['slug']}/"
        print(f"  {what}  <- ig {e['ig']}")
    if not args.confirm:
        print("  dry run - re-run with --confirm to publish")
        return 0

    wp = WP()
    json_h = {"Content-Type": "application/json"}
    try:
        for e in entries:
            m = ig_media(e["ig"])
            first = (m.get("caption") or "").strip().splitlines()
            alt = e.get("title") or (first[0] if first else "Shashi Pallava")
            mid = creative(wp, m, alt)
            if "wp_id" in e:
                wp.call(f"/wp-json/wp/v2/posts/{e['wp_id']}", method="POST", headers=json_h,
                        data=json.dumps({"featured_media": mid}).encode())
                print(f"  post {e['wp_id']}: featured image {mid}")
                continue
            payload = {"title": e["title"], "slug": e["slug"], "status": "publish",
                       "content": body(e, m["permalink"]), "excerpt": e["lead"],
                       "featured_media": mid, "date_gmt": m["timestamp"][:19],
                       "comment_status": "closed", "ping_status": "closed"}
            found = wp.call(f"/wp-json/wp/v2/posts?slug={e['slug']}&status=publish,draft&_fields=id")
            path = f"/wp-json/wp/v2/posts/{found[0]['id']}" if found else "/wp-json/wp/v2/posts"
            out = wp.call(path, method="POST", headers=json_h, data=json.dumps(payload).encode())
            print(f"  {'updated' if found else 'created'} {out['link']}")
    except urllib.error.HTTPError as exc:
        print("  FAILED:", exc.code, exc.read()[:300].decode("utf-8", "replace"))
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
