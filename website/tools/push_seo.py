#!/usr/bin/env python
"""Publish the site-wide snippets kept in website/seo/:

    sp-seo.php   -> "SP SEO"   entity schema and /llms.txt
    sp-lang.php  -> "SP Lang"  the English / Hindi switch on every page

    python website/tools/push_seo.py            # dry run: php -l only
    python website/tools/push_seo.py --confirm  # create or update both snippets
"""

from __future__ import annotations

import argparse
import pathlib
import subprocess
import sys
import urllib.error

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from push_game import WP  # noqa: E402

SEO = pathlib.Path(__file__).resolve().parent.parent / "seo"
SNIPPETS = [
    ("sp-seo.php", "SP SEO", "Entity schema and /llms.txt."),
    ("sp-lang.php", "SP Lang", "English / Hindi switch on every page."),
]


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--confirm", action="store_true")
    args = ap.parse_args()
    for src, _, _ in SNIPPETS:
        lint = subprocess.run(["php", "-l", str(SEO / src)], capture_output=True, text=True)
        print(" ", (lint.stdout + lint.stderr).strip())
        if lint.returncode:
            return 1
    if not args.confirm:
        print("  dry run - re-run with --confirm to publish")
        return 0
    wp = WP()
    existing = wp.call("/wp-json/code-snippets/v1/snippets")
    for src, name, desc in SNIPPETS:
        code = (SEO / src).read_text(encoding="utf-8").lstrip()
        code = code[5:].lstrip("\n") if code.startswith("<?php") else code
        try:
            found = [s for s in existing if s["name"] == name and not s.get("trashed")]
            body = {"name": name, "code": code, "scope": "global", "active": True,
                    "desc": desc + f" Source: website/seo/{src} - edit there, not here."}
            # POST for updates too: Hostinger answers PUT with a bare 403
            path = f"/wp-json/code-snippets/v1/snippets/{found[0]['id']}" if found else "/wp-json/code-snippets/v1/snippets"
            out = wp.call(path, body)
        except urllib.error.HTTPError as exc:
            print(f"  {name} FAILED:", exc.code, exc.read()[:400].decode("utf-8", "replace"))
            return 1
        if out.get("code_error"):
            print(f"  {name} SNIPPET ERROR:", out["code_error"])
            return 1
        print(f"  {name}: snippet {out['id']} active={out['active']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
