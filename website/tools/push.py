#!/usr/bin/env python
"""Push website/page.html to the shashipallava.com homepage.

    python website/tools/push.py            # dry run: validate only
    python website/tools/push.py --confirm  # actually publish

Credentials are never stored in this repo. Supply them either way:

    set WP_USER=pixelmartllp@gmail.com
    set WP_APP=xxxx xxxx xxxx xxxx xxxx xxxx

or drop a gitignored website/.wp-auth.json holding {"user": ..., "app": ...}.
Make a new application password under Users -> Profile in wp-admin; the old one
can be revoked there at any time.
"""

from __future__ import annotations

import argparse
import base64
import json
import os
import pathlib
import re
import sys
import urllib.error
import urllib.request

ROOT = pathlib.Path(__file__).resolve().parent.parent
PAGE = ROOT / "page.html"
SITE = "https://shashipallava.com"
PAGE_ID = 4

# Hostinger answers automated requests without a normal user agent with
# "403 Checking your browser" or an instant 408.
UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/140.0.0.0 Safari/537.36")


def credentials() -> tuple[str, str]:
    user, app = os.environ.get("WP_USER"), os.environ.get("WP_APP")
    if not (user and app):
        conf = ROOT / ".wp-auth.json"
        if conf.is_file():
            data = json.loads(conf.read_text(encoding="utf-8"))
            user, app = data.get("user"), data.get("app")
    if not (user and app):
        sys.exit("No credentials. Set WP_USER and WP_APP, or create "
                 "website/.wp-auth.json - see the docstring.")
    return user, app.replace(" ", "")


def check(html: str) -> list[str]:
    """Everything that has silently broken this page before."""
    problems = []

    scripts = re.findall(r"<script>(.*?)</script>", html, re.S)
    for js in scripts:
        for ch in ("&", "|", "<", ">"):
            if ch in js:
                problems.append(
                    f"script contains {ch!r} - WordPress escapes these inside "
                    f"post content and it breaks the whole file")
                break

    if "\n\n" in html:
        problems.append("blank lines present - wpautop turns them into <p> tags")

    if "overflow-x:hidden" in html:
        problems.append("overflow-x:hidden found - it breaks position:sticky, "
                        "use overflow-x:clip")

    if 'class="sp"' not in html:
        problems.append("the .sp wrapper is missing")

    if ".sp.js .rv{opacity:0" not in html:
        problems.append("reveal hiding is not gated behind .sp.js - a dead "
                        "script would blank the page")

    return problems


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--confirm", action="store_true",
                    help="actually publish; without it this only validates")
    args = ap.parse_args()

    html = PAGE.read_text(encoding="utf-8")
    problems = check(html)
    for p in problems:
        print("  PROBLEM:", p)
    if problems:
        return 1
    print(f"  checks passed ({len(html.encode()) // 1024} KB)")

    if not args.confirm:
        print("  dry run - re-run with --confirm to publish")
        return 0

    body = json.dumps({"content": "<!-- wp:html -->\n" + html + "\n<!-- /wp:html -->"})
    user, app = credentials()
    token = base64.b64encode(f"{user}:{app}".encode()).decode()
    req = urllib.request.Request(
        f"{SITE}/wp-json/wp/v2/pages/{PAGE_ID}",
        data=body.encode("utf-8"),
        headers={"Content-Type": "application/json",
                 "Authorization": "Basic " + token,
                 "User-Agent": UA},
        method="POST")
    try:
        with urllib.request.urlopen(req, timeout=90) as resp:
            out = json.loads(resp.read())
    except urllib.error.HTTPError as exc:
        print("  FAILED:", exc.code, exc.read()[:300].decode("utf-8", "replace"))
        return 1

    print("  published page", out.get("id"), "->", out.get("link"))
    print("  now verify it rendered: node website/tools/shot.js")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
