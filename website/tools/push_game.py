#!/usr/bin/env python
"""Publish Play & Grow: the server snippet, the question bank, the game script.

    python website/tools/push_game.py            # dry run: validate everything
    python website/tools/push_game.py --confirm  # publish

What goes where:
  website/game/sp-game.php  -> a Code Snippets snippet named "SP Game backend"
                               (accounts, wallet, answers, missions, redeem, admin)
  website/game/bank.json    -> option sp_g_bank   (rebuild: python website/game/bank_gen.py)
  website/game/game.js/.css -> options sp_g_js / sp_g_css, printed in every page footer
  website/game/missions.txt -> the "Missions" page, ONLY if it does not exist yet -
                               after that she edits it in wp-admin and this never
                               overwrites her month.

The snippet is checked with `php -l` before it is sent; Code Snippets also
refuses code that fails to parse, and reports it in code_error.
"""

from __future__ import annotations

import argparse
import base64
import html
import json
import pathlib
import subprocess
import sys
import urllib.error
import urllib.request

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from push import SITE, UA, credentials  # noqa: E402

GAME = pathlib.Path(__file__).resolve().parent.parent / "game"
SNIPPET = "SP Game backend"


def validate() -> list[str]:
    problems = []
    lint = subprocess.run(["php", "-l", str(GAME / "sp-game.php")], capture_output=True, text=True)
    if lint.returncode:
        problems.append("php -l: " + (lint.stdout + lint.stderr).strip())
    chk = subprocess.run(["node", "--check", str(GAME / "game.js")], capture_output=True, text=True)
    if chk.returncode:
        problems.append("node --check: " + chk.stderr.strip()[:400])
    for name in ("game.js", "game.css"):
        if "</script" in (GAME / name).read_text(encoding="utf-8").lower():
            problems.append(f"{name} contains a closing script tag - it is printed inside one")
    bank = json.loads((GAME / "bank.json").read_text(encoding="utf-8"))
    for qid, q in bank.items():
        if len(q.get("o", [])) != 4 or not 0 <= q.get("a", -1) < 4 or not 1 <= q.get("l", 0) <= 10:
            problems.append(f"bank entry {qid} is malformed")
            break
    print(f"  bank: {len(bank)} questions")
    return problems


class WP:
    def __init__(self):
        u, a = credentials()
        self.auth = "Basic " + base64.b64encode(f"{u}:{a}".encode()).decode()

    def call(self, path, data=None, method=None):
        req = urllib.request.Request(SITE + path, data=json.dumps(data).encode() if data is not None else None,
                                     method=method or ("POST" if data is not None else "GET"),
                                     headers={"Authorization": self.auth, "User-Agent": UA,
                                              "Content-Type": "application/json"})
        with urllib.request.urlopen(req, timeout=180) as r:
            return json.loads(r.read())


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--confirm", action="store_true")
    args = ap.parse_args()
    problems = validate()
    for p in problems:
        print("  PROBLEM:", p)
    if problems:
        return 1
    if not args.confirm:
        print("  checks passed - dry run, re-run with --confirm to publish")
        return 0

    wp = WP()
    try:
        plugins = {p["plugin"]: p["status"] for p in wp.call("/wp-json/wp/v2/plugins")}
        if plugins.get("code-snippets/code-snippets") != "active":
            wp.call("/wp-json/wp/v2/plugins", {"slug": "code-snippets", "status": "active"})
            print("  Code Snippets installed")

        code = (GAME / "sp-game.php").read_text(encoding="utf-8").lstrip()
        if code.startswith("<?php"):
            code = code[5:].lstrip("\n")
        found = [s for s in wp.call("/wp-json/code-snippets/v1/snippets") if s["name"] == SNIPPET and not s.get("trashed")]
        body = {"name": SNIPPET, "code": code, "scope": "global", "active": True,
                "desc": "Play & Grow: accounts, wallet, Brain Game, missions, redeem. Source: website/game/sp-game.php - edit there, not here."}
        if found:
            # POST, not PUT: Hostinger answers PUT with a bare 403
            out = wp.call(f"/wp-json/code-snippets/v1/snippets/{found[0]['id']}", body)
        else:
            out = wp.call("/wp-json/code-snippets/v1/snippets", body)
        if out.get("code_error"):
            print("  SNIPPET ERROR:", out["code_error"])
            return 1
        print(f"  snippet {out['id']} active={out['active']}")

        bank = json.loads((GAME / "bank.json").read_text(encoding="utf-8"))
        saved = wp.call("/wp-json/sp/v1/admin/assets", {
            "bank": bank,
            "js": (GAME / "game.js").read_text(encoding="utf-8"),
            "css": (GAME / "game.css").read_text(encoding="utf-8")})
        print("  assets:", saved.get("saved"))

        if not wp.call("/wp-json/wp/v2/pages?slug=missions&status=publish,draft,private&_fields=id"):
            lines = (GAME / "missions.txt").read_text(encoding="utf-8").strip().splitlines()
            content = "".join(f"<!-- wp:paragraph --><p>{html.escape(l)}</p><!-- /wp:paragraph -->" for l in lines)
            page = wp.call("/wp-json/wp/v2/pages", {"title": "Missions", "slug": "missions", "status": "publish",
                                                    "content": content, "meta": {"slim_seo": {"noindex": "1"}}})
            print("  missions page created:", page["id"])
        else:
            print("  missions page exists - left as she wrote it")
        me = wp.call("/wp-json/sp/v1/me")
        print("  /sp/v1/me answers; bank size per level:", me["progress"]["size"])
    except urllib.error.HTTPError as exc:
        print("  FAILED:", exc.code, exc.read()[:500].decode("utf-8", "replace"))
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
