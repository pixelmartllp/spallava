# WEBSITE.md — shashipallava.com

Read this before touching the website. It is a **separate project from this
repo** — this repo is only the daily social pipeline (see `CLAUDE.md`). Nothing
about the site lives in the code here, so none of it is derivable from the
source or the git history. Built 01–03 Sep 2026.

Owner: **Sanjeev** (@axisuv), for the **Shashi Pallava** life & relationship
coaching brand. He writes in Hinglish; reply in the language he used, and
report what actually happened rather than what was intended.

---

## 1. Where it lives

| | |
|---|---|
| URL | https://shashipallava.com/ |
| Host | Hostinger (hPanel), LiteSpeed, PHP 8.3 |
| CMS | WordPress, theme **Twenty Twenty-Five** (block theme) |
| Editing | WordPress **REST API**, application password for `pixelmartllp@gmail.com` (administrator) |

The password is **not** written down here or anywhere in this repo. Ask him for
it, and never commit it. He can revoke it at any time under
**Users → Profile → Application Passwords**.

### Working on this from any machine

Everything needed is in `website/`, so a fresh clone is enough:

```
website/page.html        the live homepage source - edit this, not wp-admin
website/tools/push.py    validate it, then publish it
website/tools/shot.js    screenshot at a real 390px phone viewport
website/tools/sticky.js  check the header sticks on phone and desktop
```

Set the credentials once, either as environment variables or as a gitignored
`website/.wp-auth.json` holding `{"user": ..., "app": ...}`:

```bash
export WP_USER=pixelmartllp@gmail.com
export WP_APP='xxxx xxxx xxxx xxxx xxxx xxxx'
```

Then the loop is:

```bash
python website/tools/push.py             # validates only - always run this first
python website/tools/push.py --confirm   # publishes to page 4
cd website/tools && npm install          # once, for the screenshot tools
node shot.js https://shashipallava.com/ out.png 390
```

`push.py` refuses to publish if it finds any of the four failures in §4 - a
stray `&` in the script, a blank line, `overflow-x:hidden`, or reveal hiding
that is not gated behind `.sp.js`. Each guard was tested against a
deliberately broken copy, so they are real, not decorative.

The screenshot tools find Chrome themselves (override with `CHROME_PATH`) and
send a normal browser user agent, which Hostinger requires. Point them
elsewhere with `SITE_URL`.

**`website/page.html` is the only version-controlled copy of the site.** The
live page has no other backup beyond WordPress revisions, so keep the two in
step: pull the file, edit it, push it.

Theme activation is **not** possible over the REST API — he had to click that
himself. Same for anything in the Customizer.

## 2. How the homepage is actually built

This is the part that surprises people, so read it before editing.

- The entire design is **raw HTML plus an inline `<style>` and `<script>`,
  living inside the content of page id 4** ("Home"). It is not built from
  blocks, and there is no page builder.
- A **custom template `twentytwentyfive//front-page`** was created containing
  nothing but `<!-- wp:post-content /-->`. That is why no theme header or
  footer appears and the design owns the whole page. If theme chrome ever comes
  back, that template is what to check.
- The content is wrapped in `<!-- wp:html --> … <!-- /wp:html -->`. This is
  load-bearing — see §4.

To change anything, `POST` the full new content to
`/wp-json/wp/v2/pages/4`. There is no partial update; send the whole thing.

## 3. Design

Dark `#0A0A0B` with gold `#FBBD23` — deliberately the palette of
**karizmaticu.com**, which the owner chose as the reference and asked to be
matched and beaten. Type is **Archivo** throughout (his call: "bold and simple",
one family only). Mobile is the base; desktop is added in a single
`@media (min-width:900px)` block at the end. He was explicit that **mobile
matters more than desktop**.

Page order: hero → stats → three shifts → about → programs → how it works →
FAQ → success stories (hidden) → community → footer.

Phones also get a **bottom tab bar** and a **right-hand slide-in menu**;
both are hidden on desktop.

**Logos.** The header uses the lotus **mark only** (`sp-logo-mark.png`); the
full logo with the "REVIVE, RISE & RELIVE" tagline (`sp-logo-full.png`) goes in
the footer at 104px. The tagline is unreadable at header size, which is the
whole reason there are two files. Both were keyed to transparency from a
flat-black original — the raw file would show as a lighter square on the page.

## 4. Three traps this page has already fallen into

Every one of these shipped broken at least once. They are not hypothetical.

**WordPress escapes `&` inside post content.** `a && b` became
`a &#038;&#038; b`, which is a JavaScript syntax error, which killed the whole
inline script. Because the reveal animation hid every section by default, the
result was a **blank page with only the header and footer** — exactly what the
owner reported. The script is now written with **no `&`, `|`, `<` or `>`
anywhere**: nested `if`s instead of `&&`, `else if` instead of `||`,
`p !== 1` instead of `p < 1`. Keep it that way.

Two defences were added so this can never blank the page again: `.sp.js` gates
the hiding (a synchronous arming script proves JS is alive, and un-arms itself
after 2s if the main script never runs), and a `setTimeout` reveals everything
after 2.2s regardless.

**Always validate the *delivered* JavaScript, not your local file:**

```bash
curl -sS "https://shashipallava.com/" -o live.html
# extract the inline script, then:
node --check delivered.js
```

Counting braces is not enough — that check passed while the file was broken.

**`wpautop` injects `<p>` and `<br>` into `<style>` and `<script>`.** At one
point the CSS had 16 stray `<p>` tags in it. Fixed by wrapping the content in
`<!-- wp:html -->` and stripping every blank line before posting. If you ever
see layout or script weirdness, grep the live HTML for `<p>` inside `<style>`.

**`overflow-x:hidden` breaks `position:sticky`.** It turns the element into a
scroll container, so a sticky child sticks to *that* box instead of the page and
the header scrolls away. Use **`overflow-x:clip`**, which stops the overflow
without creating a scroll container.

## 5. Look before you report

Do not judge layout by reading CSS. Screenshot it:

```bash
cd website/tools && node shot.js "https://shashipallava.com/" out.png 390
```

`shot.js` drives **puppeteer-core** against the installed Chrome at a true 390px
iPhone viewport and prints element widths and offsets alongside the screenshot.
`sticky.js` checks the header sticks on both phone and desktop.

Headless Chrome's own `--window-size` flag is **ignored** for the layout
viewport (it stays at 485px), which made early screenshots look broken when the
site was fine. That wasted several rounds — use puppeteer.

**Hostinger blocks automated requests.** Without a normal browser user agent
you get `403 Checking your browser` or an instant `408`. Set a real UA on every
curl and puppeteer call, and do not hammer the site — a burst of requests got
this machine temporarily blocked while the site was working fine for the owner.

## 6. Content rules

**Only his own facts go on the site.** He asked twice for things that were
declined, and the reasons still hold:

- **No invented testimonials.** Fake client reviews under made-up names mislead
  the people who read them before paying, and India's consumer-protection rules
  cover exactly this. The **Success Stories section is fully built but carries
  the `hidden` attribute** — remove it the moment three real client lines
  arrive. A ready-to-send WhatsApp message for collecting them is in the
  session history.
- **No invented certifications.** Only what he supplied: *Life Coaching
  Certified — Alison*. The other two badges are descriptive, taken from his own
  bio text: *4+ years practice*, *NLP-based approach*.
- **Do not copy karizmaticu.com's words or numbers.** Matching their structure
  and palette is what he asked for; lifting their copy is not.

Voice: mostly English with occasional Hinglish where it lands — his instruction
was "English and Hinglish mix, zyadatar English". The strongest line on the
page is his own: *"Main sabke liye kar rahi hoon — but mere liye kaun?"*

**`FAQ.txt` in the repo root is the authority on what the programs actually
are.** He wrote it himself and confirmed it on 05 Sep 2026 over an earlier
description that contradicted it. When anything on the page disagrees with that
file, the file wins — and the page needs fixing, not the file.

See `MEMORY.md` → `shashi-brand-facts` for the numbers and contacts.

### What is being sold

- **Live Webinar** — free, online, open to everyone. The way in.
- **Revive, Rise & Relive** — ₹999, a **6-month** transformation program.
  100% online: a private WhatsApp community, interactive live webinars,
  practical challenges and missions on **Mentie Go**, and **one** personal 1:1
  session with Shashi. For women aged 18 to 55.

This replaced an earlier "Revive Your Life, 3 months, weekly 1:1" description.
Both were live on the same page for a while, a few hundred pixels apart —
the Programs card said one thing and the FAQ said another. If you change one,
walk the whole page: the section lede and the third How It Works step named the
program too.

## 7. Blog

Six posts, drawn from the **real quote bank** in `content_bank.json` (90 unused
entries remain). Each is a quote plus three short paragraphs in her voice and a
WhatsApp call to action. `/blog/` is the posts page.

## 8. Sharing

There were **no Open Graph tags at all**, which is why WhatsApp showed no
preview. **Slim SEO** is installed and active for that single purpose — it is
tiny and configuration-free, unlike Yoast or Rank Math. Page 4 has an explicit
excerpt and a featured image (`shashi-pallava-share.jpg`, 1200×630), because
the auto-generated description otherwise scraped the page's own CSS.

WhatsApp caches previews hard. To retest, add a query string
(`shashipallava.com/?1`) or use a fresh chat.

## 9. Still open

The ₹999 price used to look like a typo and is not one. It read wrong only
while the page described twelve weekly 1:1 sessions; for a six-month group
program it is an ordinary number. Settled — do not raise it again.

- **City is unknown** — the footer says only "India".
- **Testimonials** — see §6. The section is built and hidden; three real
  client lines are all it needs.
- The daily creatives still carry only "Life & Relationship Coach"
  (`BRAND_TAGLINE` in `shashi_social/brand.py`), while the site now says
  "Life & Relationship Coach | Mindset Mentor". He has been told; do not change
  it silently.
