#!/usr/bin/env python
"""Build the handover zip for shashipallava.com.

    python website/tools/makezip.py

Everything it packages now lives in the repo, so this no longer depends on a
session scratchpad — which is exactly how the previous copy of this script,
and the site's own image assets, came to be lost.
"""

from __future__ import annotations

import pathlib
import shutil
import zipfile

ROOT = pathlib.Path(__file__).resolve().parent.parent.parent   # the repo root
WEB = ROOT / "website"
OUT = ROOT / "shashipallava-website.zip"
STAGE_PARENT = ROOT / ".ziptmp"
STAGE = STAGE_PARENT / "shashipallava-website"

SKIP = shutil.ignore_patterns("__pycache__", "*.pyc", "node_modules",
                              "package-lock.json", "*.png.tmp", ".wp-auth.json")

CLAUDE_MD = """# CLAUDE.md — shashipallava.com

**Read `WEBSITE.md` in this folder, in full, before changing anything.** It is
the real documentation; this file only exists so you load it automatically.

This folder is the complete source of the live website
**https://shashipallava.com/**. It is not a git repo — it was handed over as a
zip. `website/page.html` is the only copy of the site outside WordPress itself.

Owner: **Sanjeev** (@axisuv), for the **Shashi Pallava** life and relationship
coaching brand. He writes in Hinglish; reply in the language he used, and
report what actually happened rather than what was intended.

## How to change the site

```bash
set WP_USER=pixelmartllp@gmail.com
set WP_APP=<application password - ask him, never commit it>

python website/tools/push.py             # validates only; always run first
python website/tools/push.py --confirm   # publishes to page 4
```

The whole homepage is raw HTML with an inline `<style>` and `<script>`, living
inside the content of WordPress page id 4, wrapped in `<!-- wp:html -->`. There
is no page builder.

The blog (`/blog/`, posts, category pages) is different: it renders through
three theme template overrides built from `website/templates/` and published
with `push_templates.py`. Posts and their SEO live in `website/blog/*.json`
and go out with `blog_sync.py` and `seo_sync.py`; the homepage Instagram grid
is refreshed by `insta_sync.py`. All of them are dry runs without `--confirm`.
WEBSITE.md sections 7 to 7c explain each one.

**Never publish blog words he has not read.** New posts are written content;
show him the text first.

## Four things that have actually broken this page

`push.py` refuses to publish if it finds any of them, and each guard was tested
against a deliberately broken copy. Do not work around the guards.

1. **WordPress escapes `&` inside post content.** `a && b` became
   `a &#038;&#038; b`, a syntax error that killed the whole script and left a
   blank page. The script therefore contains **no `&`, `|`, `<` or `>` at all** —
   nested `if`s instead of `&&`, `else if` instead of `||`, `p !== 1` instead of
   `p < 1`, and DOM calls instead of HTML strings. Keep it that way.
2. **`wpautop` injects `<p>` and `<br>` into `<style>` and `<script>`.** Avoided
   by the `wp:html` wrapper and by stripping every blank line before posting.
3. **`overflow-x:hidden` breaks `position:sticky`.** Use `overflow-x:clip`.
4. **Reveal animations must be gated behind `.sp.js`**, or a dead script hides
   the entire page.

Always validate the **delivered** JavaScript, not your local file: fetch the
live page, pull the inline script out, and run `node --check` on it. Counting
braces is not enough — that check passed while the file was broken.

## Look before you report

Do not judge layout by reading CSS. `website/tools/shot.js` screenshots at a
real 390px phone and prints element offsets; `sticky.js` and `pwa.js` check the
header and installability. A class collision and a broken icon size were both
found by screenshot and would not have been found any other way.

Hostinger blocks automated requests without a normal browser user agent — you
get `403 Checking your browser` or an instant `408`. Set one on every request,
and do not hammer the site.

## Content rules

Only his own facts go on the site. Two things were asked for and declined, and
the reasons still hold:

- **No invented testimonials.** The Success Stories section is built but carries
  the `hidden` attribute; it goes live when three real client lines arrive.
- **No invented certifications.** Only what he supplied.

`FAQ.txt` is his own writing and is the authority on what the programmes are.
If the page disagrees with that file, the page is what gets fixed.
"""


START_HERE = """SHASHI PALLAVA WEBSITE - shashipallava.com
==========================================

Is folder me wo sab kuch hai jo kisi bhi PC par is website par kaam karne ke
liye chahiye.

KYA KYA HAI
-----------
CLAUDE.md                  Claude ise khud padh leta hai. Chhedne ki zarurat nahi.
WEBSITE.md                 Poori documentation. SABSE PEHLE YE PADHIYE.
FAQ.txt                    Aapka likha hua FAQ - programs ki sahi jaankari.
website/page.html          Site ka asli source. Homepage ka poora design isi
                           ek file me hai. Ise edit kijiye, wp-admin me nahi.
website/tools/push.py      File ko check karke site par publish karta hai.
website/templates/         Blog, post aur category pages ka design.
website/tools/push_templates.py   Blog ka design publish karta hai.
website/blog/posts.json    Blog posts aur unke Instagram creatives.
website/blog/seo.json      Har post ka SEO - title, description, FAQ, links.
website/tools/blog_sync.py Naye posts aur creatives site par daalta hai.
website/tools/seo_sync.py  seo.json ko saare posts par lagata hai.
website/tools/insta_sync.py Homepage ka Instagram grid update karta hai.
github/insta-feed.yml      Roz Instagram grid update karne wala GitHub job.
website/tools/shot.js      Asli phone size par screenshot leta hai.
website/tools/sticky.js    Header sticky hai ya nahi, ye check karta hai.
website/tools/pwa.js       App ki tarah install ho rahi hai ya nahi, ye check.
website/tools/ogimage.py   WhatsApp share card banane wala script.
website/tools/makezip.py   Yahi zip dobara banane ke liye.
website/assets/            Jo images site par lagi hain - logo, photo, share
                           card, aur app icons.
originals/                 Aapki bheji hui asli files, bina kisi badlav ke.

CHAHIYE KYA
-----------
- Python 3 (push.py ke liye - koi extra package nahi chahiye)
- Node.js + Chrome (sirf screenshot/pwa tools ke liye, optional)

SHURU KAISE KAREIN
------------------
1. WordPress ka application password lijiye:
   wp-admin -> Users -> Profile -> Application Passwords -> naya banaiye

2. Us password ko set kijiye. Do tarike hain -

   Windows (Command Prompt):
     set WP_USER=pixelmartllp@gmail.com
     set WP_APP=xxxx xxxx xxxx xxxx xxxx xxxx

   Ya ek file bana lijiye - website/.wp-auth.json :
     {"user": "pixelmartllp@gmail.com", "app": "xxxx xxxx xxxx xxxx xxxx xxxx"}

3. Kaam ka tarika:

   python website/tools/push.py
       Sirf check karta hai, kuch publish nahi karta. HAMESHA pehle ye chalaiye.

   python website/tools/push.py --confirm
       Ab asal me site par publish karta hai.

   cd website/tools
   npm install                    (ek hi baar)
   node shot.js https://shashipallava.com/ out.png 390
       Screenshot lekar naap bhi bata deta hai.

ZAROORI BAATEIN
---------------
* website/page.html hi site ki EKMATRA backup copy hai. Live page ka koi aur
  backup nahi hai. File aur site, dono ko saath rakhiye.

* push.py chaar aisi galtiyan pakadta hai jo is site ne pehle sach me jheli
  hain, aur mile to publish karne se mana kar deta hai. Uski baat maniye -
  har guard tod kar test kiya gaya hai.

* Password kisi file me likha hua nahi hai, aur kabhi commit mat kijiye.

ABHI KYA BAAKI HAI
------------------
0. INSTAGRAM GRID ROZ UPDATE - GitHub repo -> Settings -> Secrets and
   variables -> Actions me do secrets daaliye: WP_USER aur WP_APP.
   Tab tak:  python website/tools/insta_sync.py --confirm

0b. SITE KIT - Search Console ki ek permission baaki hai. Site Kit ->
   Dashboard me "grant permissions" dabaiye, saare checkbox tick kijiye.

1. APP ICONS - site app ki tarah install to ho jaati hai, par uske icon aur
   rang abhi plugin ke default hain. WP Admin -> SuperPWA -> Settings me
   chaar cheezein set kijiye:
       Application Icon     sp-icon-512.png
       Splash Screen Icon   sp-icon-512-maskable.png
       Background Color     #0A0A0B
       Theme Color          #0A0A0B
   Dono icons Media Library me pehle se upload hain.

2. TEEN ASLI CLIENT TESTIMONIALS - Success Stories section poora bana hua hai
   par 'hidden' hai. Asli lines aate hi live ho jayega. Banaye hue reviews
   mat daaliye.

FAQ.txt hi programs ki sahi jaankari hai. Site aur us file me kabhi farq lage
to file sahi maani jayegi - page theek karna hai, file nahi.
"""


def main() -> int:
    if STAGE_PARENT.exists():
        shutil.rmtree(STAGE_PARENT)
    STAGE.mkdir(parents=True)

    shutil.copy(ROOT / "WEBSITE.md", STAGE / "WEBSITE.md")
    # Claude Code only auto-loads CLAUDE.md, so the handover needs one of its
    # own - without it a fresh session in this folder starts blind.
    (STAGE / "CLAUDE.md").write_text(CLAUDE_MD, encoding="utf-8")
    if (ROOT / "FAQ.txt").is_file():
        shutil.copy(ROOT / "FAQ.txt", STAGE / "FAQ.txt")

    (STAGE / "website").mkdir()
    shutil.copy(WEB / "page.html", STAGE / "website" / "page.html")
    shutil.copytree(WEB / "tools", STAGE / "website" / "tools", ignore=SKIP)
    shutil.copytree(WEB / "assets", STAGE / "website" / "assets", ignore=SKIP)
    shutil.copytree(WEB / "templates", STAGE / "website" / "templates", ignore=SKIP)
    shutil.copytree(WEB / "blog", STAGE / "website" / "blog", ignore=SKIP)
    wf = ROOT / ".github" / "workflows" / "insta-feed.yml"
    if wf.is_file():
        (STAGE / "github").mkdir()
        shutil.copy(wf, STAGE / "github" / "insta-feed.yml")

    # his untouched source files, which are not tracked in the repo
    originals = ROOT / "Sample"
    if originals.is_dir():
        dest = STAGE / "originals"
        dest.mkdir()
        for f in originals.iterdir():
            if f.is_file():
                shutil.copy(f, dest / f.name)

    (STAGE / "START-HERE.txt").write_text(START_HERE, encoding="utf-8")

    if OUT.exists():
        OUT.unlink()
    with zipfile.ZipFile(OUT, "w", zipfile.ZIP_DEFLATED, compresslevel=9) as z:
        for path in sorted(STAGE.rglob("*")):
            if path.is_file():
                z.write(path, path.relative_to(STAGE_PARENT))

    shutil.rmtree(STAGE_PARENT)

    with zipfile.ZipFile(OUT) as z:
        names = z.namelist()
        print(f"  {OUT.name}  {OUT.stat().st_size / 1024 / 1024:.2f} MB  "
              f"{len(names)} files  integrity "
              f"{'OK' if z.testzip() is None else 'BAD'}")
        for n in names:
            print(f"    {z.getinfo(n).file_size:>9,}  {n}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
