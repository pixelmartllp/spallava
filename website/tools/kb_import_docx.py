#!/usr/bin/env python
"""Import a course-notes .docx into the assistant's knowledge base as PRIVATE chapters.

    python website/tools/kb_import_docx.py Alison_Mindfulness_Properly_Formatted.docx
    python website/tools/kb_import_docx.py Alison_Mindfulness_Properly_Formatted.docx --confirm

Built for the Alison "Mindfulness Powerhouse" course notes (Heading 1 = module,
Heading 2 = section, Heading 3 = lesson). Every lesson - and every section that
has text of its own before its first lesson - becomes one child page of
"Assistant Knowledge" (page 141), titled

    Mindfulness: M<module>.<nn> <lesson title>

so typing "Mindfulness" in admin mode lists the whole course in order, and any
search finds the lesson. Every chapter is created **private**: this is
third-party course material for Shashi's own reference and webinars, not for
visitors, and the assistant never answers visitors from private chapters.

Pages are matched by slug (mf-m1-05 ...), so a re-run updates rather than
duplicates. Modules with no text (the interim assessments) are skipped.
"""

from __future__ import annotations

import argparse
import html
import json
import pathlib
import re
import sys
import urllib.error

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from push_game import WP  # noqa: E402

KB_ROOT = 141
TOPIC = "Mindfulness"


def clean(t: str) -> str:
    t = t.replace("�", "-").replace("\t", " ")
    t = re.sub(r"\s+", " ", t).strip()
    t = re.sub(r"^(\d+\.?|[A-F]\.)\s+", "", t)       # "2.  Embracing", "A.  Resolving"
    return t.rstrip(" :.").strip()


def chapters(path: str) -> list[dict]:
    import docx
    doc = docx.Document(path)
    out, mod_no, mod_name, sec_name = [], 0, "", ""
    cur = None

    def start(title, kind):
        nonlocal cur
        cur = {"module": mod_no, "module_name": mod_name, "section": sec_name, "title": title,
               "kind": kind, "paras": []}
        out.append(cur)

    for p in doc.paragraphs:
        text, style = p.text.strip(), p.style.name
        if not text:
            continue
        if style == "Heading 1":
            m = re.match(r"Module\s*(\d+)\s*:?\s*(.*)", clean(text))
            if m:
                mod_no, mod_name = int(m.group(1)), clean(m.group(2))
            else:
                mod_no, mod_name = 99, clean(text)       # "Final Course Components"
            sec_name, cur = "", None
            if text.lower().startswith("contents"):
                mod_no = 0
            continue
        if mod_no == 0 or style in ("Title", "Subtitle"):
            continue
        if style == "Heading 2":
            sec_name = clean(text)
            start(sec_name, "section")
            continue
        if style == "Heading 3":
            start(clean(text), "lesson")
            continue
        if cur is None:
            start(mod_name or "Introduction", "section")
        cur["paras"].append(text)

    keep = [c for c in out if sum(len(x.split()) for x in c["paras"]) >= 15]
    # the notes repeat one lesson's text under an earlier heading (Module 2's
    # second "Understanding the Gap" holds "Attention, Part 1" word for word):
    # when two chapters carry identical text, keep the later heading's copy
    keep = [c for i, c in enumerate(keep) if not any(c["paras"] == d["paras"] for d in keep[i + 1:])]
    n = {}
    for c in keep:
        n[c["module"]] = n.get(c["module"], 0) + 1
        mod = "MX" if c["module"] == 99 else f"M{c['module']}"
        c["num"] = f"{mod}.{n[c['module']]:02d}"
        c["slug"] = f"mf-{mod.lower()}-{n[c['module']]:02d}"
    return keep


def content(c: dict) -> str:
    kw = ", ".join(x for x in [c["module_name"], c["section"], c["title"], "mindfulness"] if x)
    parts = [f"<!-- wp:paragraph --><p>Keywords: {html.escape(kw)}</p><!-- /wp:paragraph -->"]
    where = f"Module {c['module']}: {c['module_name']}" if c["module"] != 99 else c["module_name"]
    if c["section"] and c["section"] != c["title"]:
        where += f" · {c['section']}"
    parts.append(f"<!-- wp:paragraph --><p><em>{html.escape(where)}</em></p><!-- /wp:paragraph -->")
    for t in c["paras"]:
        parts.append(f"<!-- wp:paragraph --><p>{html.escape(t)}</p><!-- /wp:paragraph -->")
    return "\n".join(parts)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("docx")
    ap.add_argument("--confirm", action="store_true")
    args = ap.parse_args()
    chs = chapters(args.docx)
    words = sum(sum(len(x.split()) for x in c["paras"]) for c in chs)
    for c in chs:
        print(f"  {c['num']:7} {sum(len(x.split()) for x in c['paras']):5}w  {c['title'][:70]}")
    print(f"  {len(chs)} chapters, {words} words")
    if not args.confirm:
        print("  dry run - re-run with --confirm to create them as private chapters")
        return 0
    wp = WP()
    try:
        existing = {}
        page = 1
        while True:
            got = wp.call(f"/wp-json/wp/v2/pages?parent={KB_ROOT}&status=publish,private,draft"
                          f"&per_page=100&page={page}&_fields=id,slug")
            existing.update({p["slug"]: p["id"] for p in got})
            if len(got) < 100:
                break
            page += 1
        made = upd = 0
        for i, c in enumerate(chs):
            body = {"title": f"{TOPIC}: {c['num']} {c['title']}", "slug": c["slug"], "status": "private",
                    "parent": KB_ROOT, "menu_order": 1000 + i, "content": content(c),
                    "meta": {"slim_seo": {"noindex": "1"}}}
            if c["slug"] in existing:
                wp.call(f"/wp-json/wp/v2/pages/{existing[c['slug']]}", body)
                upd += 1
            else:
                wp.call("/wp-json/wp/v2/pages", body)
                made += 1
        print(f"  created {made}, updated {upd} private chapters under page {KB_ROOT}")
    except urllib.error.HTTPError as exc:
        print("  FAILED:", exc.code, exc.read()[:300].decode("utf-8", "replace"))
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
