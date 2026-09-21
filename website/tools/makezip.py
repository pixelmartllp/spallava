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

START_HERE = """SHASHI PALLAVA WEBSITE - shashipallava.com
==========================================

Is folder me wo sab kuch hai jo kisi bhi PC par is website par kaam karne ke
liye chahiye.

KYA KYA HAI
-----------
WEBSITE.md                 Poori documentation. SABSE PEHLE YE PADHIYE.
FAQ.txt                    Aapka likha hua FAQ - programs ki sahi jaankari.
website/page.html          Site ka asli source. Homepage ka poora design isi
                           ek file me hai. Ise edit kijiye, wp-admin me nahi.
website/tools/push.py      File ko check karke site par publish karta hai.
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
    if (ROOT / "FAQ.txt").is_file():
        shutil.copy(ROOT / "FAQ.txt", STAGE / "FAQ.txt")

    (STAGE / "website").mkdir()
    shutil.copy(WEB / "page.html", STAGE / "website" / "page.html")
    shutil.copytree(WEB / "tools", STAGE / "website" / "tools", ignore=SKIP)
    shutil.copytree(WEB / "assets", STAGE / "website" / "assets", ignore=SKIP)

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
