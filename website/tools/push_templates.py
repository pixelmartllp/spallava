#!/usr/bin/env python
"""Push the blog's page templates - /blog/ and every single post.

    python website/tools/push_templates.py            # dry run: validate only
    python website/tools/push_templates.py --confirm  # publish both templates

Twenty Twenty-Five's own blog templates are a white page with the theme's
demo footer (Events, Shop, Patterns, Themes) and "Written by <admin email>"
on every post. These replace them with the homepage's dark-and-gold chrome.

Each template is assembled from website/templates/:

    head.html + <name>.body.html + foot.html

``home`` is the posts index (/blog/ is set as the posts page), ``single`` is
one post. Saving over a theme template stores an override in the database;
wp-admin -> Appearance -> Editor -> Templates -> "Reset" brings the theme's
back if this ever needs undoing.

--confirm also closes comments on every post and for new ones. Nobody
moderates them, and an open comment form on a small WordPress site fills with
spam within weeks.
"""

from __future__ import annotations

import argparse
import base64
import json
import pathlib
import re
import sys
import urllib.error
import urllib.request

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from push import SITE, UA, credentials  # noqa: E402

TPL = pathlib.Path(__file__).resolve().parent.parent / "templates"
THEME = "twentytwentyfive"
NAMES = {"home": "Blog Home", "single": "Single Posts", "archive": "All Archives"}


def assemble(name: str) -> str:
    head = (TPL / "head.html").read_text(encoding="utf-8").strip()
    body = (TPL / f"{name}.body.html").read_text(encoding="utf-8").strip()
    foot = (TPL / "foot.html").read_text(encoding="utf-8").strip()
    out = (f"<!-- wp:html -->\n{head}\n<!-- /wp:html -->\n{body}\n"
           f"<!-- wp:html -->\n{foot}\n<!-- /wp:html -->")
    return "\n".join(line for line in out.splitlines() if line.strip())


def check(html: str) -> list[str]:
    problems = []
    for js in re.findall(r"<script>(.*?)</script>", html, re.S):
        for ch in ("&", "|", "<", ">"):
            if ch in js:
                problems.append(f"script contains {ch!r} - WordPress may escape it")
                break
    if html.count("<!-- wp:html -->") != html.count("<!-- /wp:html -->"):
        problems.append("unbalanced wp:html blocks")
    if "overflow-x:hidden" in html:
        problems.append("overflow-x:hidden breaks the sticky header - use clip")
    return problems


def call(auth: str, path: str, payload: dict) -> dict:
    req = urllib.request.Request(
        SITE + path, data=json.dumps(payload).encode("utf-8"), method="POST",
        headers={"Content-Type": "application/json", "Authorization": auth,
                 "User-Agent": UA})
    with urllib.request.urlopen(req, timeout=90) as r:
        return json.loads(r.read())


def get(auth: str, path: str):
    req = urllib.request.Request(SITE + path,
                                 headers={"Authorization": auth, "User-Agent": UA})
    with urllib.request.urlopen(req, timeout=90) as r:
        return json.loads(r.read())


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--confirm", action="store_true")
    args = ap.parse_args()

    built = {n: assemble(n) for n in NAMES}
    bad = False
    for n, html in built.items():
        for p in check(html):
            print(f"  PROBLEM in {n}: {p}")
            bad = True
        print(f"  {n}: {len(html.encode()) // 1024} KB")
    if bad:
        return 1
    if not args.confirm:
        print("  dry run - re-run with --confirm to publish")
        return 0

    user, app = credentials()
    auth = "Basic " + base64.b64encode(f"{user}:{app}".encode()).decode()
    try:
        for n, html in built.items():
            out = call(auth, f"/wp-json/wp/v2/templates/{THEME}//{n}",
                       {"content": html, "title": NAMES[n]})
            print(f"  template {out.get('id')} saved ({out.get('source')})")
        call(auth, "/wp-json/wp/v2/settings",
             {"default_comment_status": "closed", "default_ping_status": "closed"})
        for p in get(auth, "/wp-json/wp/v2/posts?per_page=100&_fields=id,comment_status"):
            if p["comment_status"] != "closed":
                call(auth, f"/wp-json/wp/v2/posts/{p['id']}",
                     {"comment_status": "closed", "ping_status": "closed"})
        print("  comments closed")
    except urllib.error.HTTPError as exc:
        print("  FAILED:", exc.code, exc.read()[:300].decode("utf-8", "replace"))
        return 1
    print("  now look at it: node website/tools/shot.js https://shashipallava.com/blog/")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
