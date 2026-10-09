#!/usr/bin/env python
"""Apply the SEO and GEO layer in website/blog/seo.json to every blog post.

    python website/tools/seo_sync.py            # dry run: print one post's block
    python website/tools/seo_sync.py --confirm  # update posts, categories, settings

Per post it sets the Slim SEO title and description (Slim SEO registers its
``slim_seo`` meta for REST, so no wp-admin trip), files the post in its
category, and appends three practical steps, two questions with direct answers
and two internal links. The questions are also emitted as FAQPage JSON-LD -
answer-first, self-contained text is what search snippets and AI answers lift.

The appended block sits between ``<!-- sp-seo:start -->`` and
``<!-- sp-seo:end -->``; a re-run replaces it rather than stacking a second.

Site-wide: renames the default "Uncategorized" category, sets the tagline to
"Life, Relationship & Mindset Coach", shows all posts on one /blog/ page, and
gives each creative an alt text that names the coach.
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
from insta_sync import WP  # noqa: E402

SEO = pathlib.Path(__file__).resolve().parent.parent / "blog" / "seo.json"
SITE = "https://shashipallava.com"
ROLE = "Life, Relationship & Mindset Coach"
BLOCK = re.compile(r"\n?<!-- sp-seo:start -->.*?<!-- sp-seo:end -->", re.S)
JSON_H = {"Content-Type": "application/json"}


def heading(text: str, level: int = 2) -> str:
    attrs = "" if level == 2 else f' {{"level":{level}}}'
    return (f"<!-- wp:heading{attrs} -->\n<h{level} class=\"wp-block-heading\">"
            f"{html.escape(text)}</h{level}>\n<!-- /wp:heading -->")


def items(lis: list[str], ordered: bool) -> str:
    tag = "ol" if ordered else "ul"
    attrs = ' {"ordered":true}' if ordered else ""
    inner = "".join(f"<!-- wp:list-item -->\n<li>{li}</li>\n<!-- /wp:list-item -->" for li in lis)
    return f"<!-- wp:list{attrs} -->\n<{tag} class=\"wp-block-list\">{inner}</{tag}>\n<!-- /wp:list -->"


def para(inner: str) -> str:
    return f"<!-- wp:paragraph -->\n<p>{inner}</p>\n<!-- /wp:paragraph -->"


def block(s: dict, titles: dict[str, str]) -> str:
    out = ["<!-- sp-seo:start -->", heading("Try this today"),
           items([html.escape(x) for x in s["steps"]], True),
           heading("Questions women often ask")]
    for q, a in s["faq"]:
        out += [heading(q, 3), para(html.escape(a))]
    out += [heading("Read next"),
            items([f'<a href="{SITE}/{slug}/">{html.escape(titles[slug])}</a>'
                   for slug in s["related"]], False)]
    faq = {"@context": "https://schema.org", "@type": "FAQPage",
           "mainEntity": [{"@type": "Question", "name": q,
                           "acceptedAnswer": {"@type": "Answer", "text": a}}
                          for q, a in s["faq"]]}
    ld = json.dumps(faq, ensure_ascii=False)
    # WordPress has escaped & inside post content before; keep it out entirely
    ld = ld.replace("&", "\\u0026").replace("<", "\\u003c")
    out += ["<!-- wp:html -->", f'<script type="application/ld+json">{ld}</script>',
            "<!-- /wp:html -->", "<!-- sp-seo:end -->"]
    return "\n".join(out)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--confirm", action="store_true")
    args = ap.parse_args()

    data = json.loads(SEO.read_text(encoding="utf-8"))
    for slug, s in data["posts"].items():
        for k, n in (("title", 65), ("desc", 160)):
            if len(s[k]) > n:
                print(f"  note: {slug} {k} is {len(s[k])} chars (aim {n})")

    wp = WP()
    posts = wp.call("/wp-json/wp/v2/posts?per_page=100&context=edit"
                    "&_fields=id,slug,title,content,featured_media")
    by_slug = {p["slug"]: p for p in posts}
    missing = [s for s in data["posts"] if s not in by_slug]
    if missing:
        sys.exit(f"posts not found on the site: {missing}")
    titles = {p["slug"]: html.unescape(p["title"]["raw"]) for p in posts}

    if not args.confirm:
        first = next(iter(data["posts"]))
        print(block(data["posts"][first], titles))
        print(f"\n  {len(data['posts'])} posts ready - dry run, re-run with --confirm")
        return 0

    try:
        cat_ids = {}
        for slug, c in data["categories"].items():
            found = wp.call(f"/wp-json/wp/v2/categories?slug={slug}")
            if not found and slug == "mindset":
                found = wp.call("/wp-json/wp/v2/categories?slug=uncategorized")
            payload = json.dumps({"name": c["name"], "slug": slug,
                                  "description": c["description"]}).encode()
            path = f"/wp-json/wp/v2/categories/{found[0]['id']}" if found else "/wp-json/wp/v2/categories"
            cat_ids[slug] = wp.call(path, data=payload, method="POST", headers=JSON_H)["id"]
        print("  categories:", cat_ids)

        for slug, s in data["posts"].items():
            p = by_slug[slug]
            content = BLOCK.sub("", p["content"]["raw"]).rstrip() + "\n" + block(s, titles)
            wp.call(f"/wp-json/wp/v2/posts/{p['id']}", method="POST", headers=JSON_H,
                    data=json.dumps({"content": content, "categories": [cat_ids[s["cat"]]],
                                     "meta": {"slim_seo": {"title": s["title"],
                                                           "description": s["desc"]}}}).encode())
            if p["featured_media"]:
                wp.call(f"/wp-json/wp/v2/media/{p['featured_media']}", method="POST",
                        headers=JSON_H, data=json.dumps({
                            "alt_text": f"{titles[slug]} - quote by Shashi Pallava, {ROLE}"}).encode())
            print(f"  {slug}: done")

        wp.call("/wp-json/wp/v2/settings", method="POST", headers=JSON_H,
                data=json.dumps({"description": ROLE, "posts_per_page": 12}).encode())
        wp.call("/wp-json/wp/v2/pages/5", method="POST", headers=JSON_H, data=json.dumps({
            "meta": {"slim_seo": {
                "title": "Blog | Shashi Pallava - Life, Relationship & Mindset Coach",
                "description": "Short reads on boundaries, relationships, healing and mindset "
                               "for women, by Shashi Pallava - Life, Relationship & Mindset "
                               "Coach. Practical steps in English and Hinglish."}}}).encode())
        print("  tagline, posts per page and the /blog/ meta set")
    except urllib.error.HTTPError as exc:
        print("  FAILED:", exc.code, exc.read()[:400].decode("utf-8", "replace"))
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
