#!/usr/bin/env python
"""Publish the SP SEO snippet (website/seo/sp-seo.php) - entity schema and /llms.txt.

    python website/tools/push_seo.py            # dry run: php -l only
    python website/tools/push_seo.py --confirm  # create or update the snippet
"""

from __future__ import annotations

import argparse
import pathlib
import subprocess
import sys
import urllib.error

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from push_game import WP  # noqa: E402

SRC = pathlib.Path(__file__).resolve().parent.parent / "seo" / "sp-seo.php"
NAME = "SP SEO"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--confirm", action="store_true")
    args = ap.parse_args()
    lint = subprocess.run(["php", "-l", str(SRC)], capture_output=True, text=True)
    print(" ", (lint.stdout + lint.stderr).strip())
    if lint.returncode:
        return 1
    if not args.confirm:
        print("  dry run - re-run with --confirm to publish")
        return 0
    code = SRC.read_text(encoding="utf-8").lstrip()
    code = code[5:].lstrip("\n") if code.startswith("<?php") else code
    wp = WP()
    try:
        found = [s for s in wp.call("/wp-json/code-snippets/v1/snippets") if s["name"] == NAME and not s.get("trashed")]
        body = {"name": NAME, "code": code, "scope": "global", "active": True,
                "desc": "Entity schema and /llms.txt. Source: website/seo/sp-seo.php - edit there, not here."}
        # POST for updates too: Hostinger answers PUT with a bare 403
        path = f"/wp-json/code-snippets/v1/snippets/{found[0]['id']}" if found else "/wp-json/code-snippets/v1/snippets"
        out = wp.call(path, body)
    except urllib.error.HTTPError as exc:
        print("  FAILED:", exc.code, exc.read()[:400].decode("utf-8", "replace"))
        return 1
    if out.get("code_error"):
        print("  SNIPPET ERROR:", out["code_error"])
        return 1
    print(f"  snippet {out['id']} active={out['active']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
