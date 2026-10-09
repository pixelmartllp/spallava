# WEBSITE.md — shashipallava.com

Read this before touching the website. It is a **separate project from this
repo** — this repo is only the daily social pipeline (see `CLAUDE.md`). Nothing
about the site lives in the code here, so none of it is derivable from the
source or the git history. Built 01–03 Sep 2026; blog, Instagram grid and
SEO added 09 Oct 2026.

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
website/page.html               the live homepage source - edit this, not wp-admin
website/templates/              blog chrome: head.html + <name>.body.html + foot.html
website/blog/posts.json         blog posts tied to Instagram creatives
website/blog/seo.json           per-post SEO titles, descriptions, steps, FAQ, links
website/tools/push.py           validate page.html, then publish it to page 4
website/tools/push_templates.py publish the home / single / archive templates
website/tools/blog_sync.py      upload creatives, create or attach blog posts
website/tools/seo_sync.py       apply seo.json to every post, categories, tagline
website/tools/insta_sync.py     copy the latest 9 Instagram posts into the grid
website/tools/shot.js           screenshot at a real 390px phone viewport
website/tools/sticky.js         check the header sticks on phone and desktop
website/tools/pwa.js            check the site installs as an app
website/tools/makezip.py        rebuild the handover zip
```

Every publishing script is a **dry run unless given `--confirm`**.

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

Page order: hero → stats → three shifts → about → programs → payment (UPI) →
webinar registration → how it works → FAQ → success stories (hidden) →
**from the blog** → **Instagram grid** → community → footer.

**Light theme.** Dark is the default; `.sp.light` restates the colour tokens
and the choice is remembered per browser in `localStorage` key `sp-theme`.
The blog templates read the same key, so the choice follows the reader. The
toggle sits on the right of the app bar next to Install and the menu, a 44px
rounded square drawn **inverted against the page** (`background:var(--fg)`,
icon `var(--bg)`): white on dark, near-black on light, at the owner's request.
It carries its own `margin-left:auto` - when it relied on Install's, it ended
up glued to the logo whenever Install was hidden.

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

Twelve posts at `/blog/` (page id 5, the posts page): six from the original
quote bank and six written from the 1–9 Oct 2026 Instagram creatives. Every
post carries an Instagram creative as its featured image.

**Homepage.** A *From the Blog* section (`#blog`) and a Blog link in the menu.
The three cards in `page.html` are a static snapshot; the script swaps in the
three newest posts from `/wp-json/wp/v2/posts?_embed` - one query parameter
only, because an `&` cannot appear in that script - with each post's creative.

**Templates.** `/blog/`, every post and every category page render through
three template overrides - `home`, `single`, `archive` - assembled from
`website/templates/` and published by `push_templates.py`. Before them, Twenty
Twenty-Five showed a white page, the theme's demo footer (Events, Shop,
Patterns, Themes) and **"Written by pixelmartllp@gmail.com" on every post**.
The admin user's display name is now *Shashi Pallava* and its slug
`shashi-pallava`, because Slim SEO's schema also printed the email. The same
script closes comments; nobody moderates them. Undo any template from
Appearance → Editor → Templates → Reset.

**Posts and creatives.** `website/blog/posts.json` ties each post to an
Instagram media id. Entries with `wp_id` only attach a creative to an existing
post; the rest are whole posts - title and bold lead from the creative and its
caption (his words), three short Hinglish paragraphs, a link back to the
Instagram post, dated to when it went up there. `blog_sync.py --confirm`
uploads each creative once as `ig-<id>-full.jpg`; re-running is safe. New
posts are **written**, so they are never automatic: add the entry, show him the
words, publish only after he says yes.

## 7a. SEO and GEO

Asked for on 09 Oct 2026, keywords around **"Shashi Pallava - Life,
Relationship & Mindset Coach"**. `website/blog/seo.json` holds, per post, the
category, the Slim SEO title (65 chars at most) and description (160), three
practical steps, two question-and-answer pairs and two internal links.
`seo_sync.py --confirm` appends them between `<!-- sp-seo:start -->` and
`<!-- sp-seo:end -->` - a re-run replaces the block, never stacks a second - and
emits the Q&A as **FAQPage JSON-LD**. Answer-first, self-contained text is what
search snippets and AI answers lift.

- Slim SEO registers its `slim_seo` post meta for REST, so titles,
  descriptions and `noindex` are set directly, no wp-admin trip.
- Categories: Boundaries, Relationships, Healing & Self-Worth, Mindset (the old
  Uncategorized, renamed), each with a keyword description.
- The single template ends every post with an **author box plus Person
  JSON-LD**: role, the Alison credential, Instagram and Facebook as `sameAs`.
- Tagline: *Life, Relationship & Mindset Coach*. `/blog/` shows 12 per page.
- Creative alt texts name the coach and the role.

**A new post needs an entry in both JSON files**, then `blog_sync.py` and
`seo_sync.py`.

## 7b. Search Console

The owner installed **Site Kit by Google** on 09 Oct 2026: Search Console,
Analytics 4 (`GT-MQRT32HB`) and PageSpeed Insights are connected, and
`sitemap.xml` (Slim SEO) was submitted that day. It first showed *Couldn't
fetch*; fetched as Googlebot, the index and all three child sitemaps return
200 and valid XML, so that was Google's first-day status, not the site.

`insta-feed` (page 91) and `webinar-details` (page 76) are data pages the
homepage reads; both carry Slim SEO `noindex`, which also drops them from the
sitemap.

Site Kit's REST data routes answer the app password, but on 09 Oct they
returned `missing_required_scopes` (`webmasters`) - a permission left unticked
during setup. Until he re-grants it in Site Kit, search data cannot be read
from here.

## 7c. Instagram grid

`#insta` on the homepage shows the latest Instagram posts and stays `hidden`
until there is something to show. The browser never talks to Instagram: the
Meta token cannot go in a page every visitor can read, and the image URLs the
Graph API returns are signed and expire within days.

So `website/tools/insta_sync.py` reads the latest nine posts with the Meta
token, uploads each image once to the media library as `ig-<media id>.jpg`,
and rewrites a plain page, slug **`insta-feed`**, as links around those
images. The homepage script reads that page, exactly like `webinar-details`.

It only *reads* Instagram; it is not part of the posting automation that is
switched off (CLAUDE.md §8). `.github/workflows/insta-feed.yml` runs it daily
at 13:00 IST once the `WP_USER` and `WP_APP` secrets exist, and skips with a
notice until then. Run it by hand any time:

```bash
python website/tools/insta_sync.py            # dry run: lists the posts
python website/tools/insta_sync.py --confirm
```

Trap: this machine's environment carries a `META_IG_USER_ID` for a different
account. The script takes token and id as a pair - env only if both are set,
otherwise both from `config.json` - because mixing them fails with "Object
does not exist".

## 8. Sharing

There were **no Open Graph tags at all**, which is why WhatsApp showed no
preview. **Slim SEO** is installed and active for that single purpose — it is
tiny and configuration-free, unlike Yoast or Rank Math. Page 4 has an explicit
excerpt and a featured image (`shashi-pallava-share.jpg`, 1200×630), because
the auto-generated description otherwise scraped the page's own CSS.

WhatsApp caches previews hard. To retest, add a query string
(`shashipallava.com/?1`) or use a fresh chat.

## 9. Installable as an app (PWA)

The site installs to a phone's home screen and opens without browser chrome.
**SuperPWA** (`super-progressive-web-apps`) does the parts that live outside
page content — it prints `<link rel="manifest">` into `<head>` and serves both
files from the site root, neither of which the REST API can reach:

```
https://shashipallava.com/superpwa-manifest.json
https://shashipallava.com/superpwa-sw.js
```

Verified directly rather than assumed: manifest returns `application/json`
with a name, `display: standalone`, `scope: /`, and 192px and 512px icons; the
service worker returns `text/javascript`; the registration is inline in the
page. Those are Chrome's install requirements, and they pass.

`website/tools/pwa.js` runs the same check through a real mobile Chrome and
also confirms the worker takes control of the page. **Hostinger's bot
protection frequently hangs or blocks headless Chrome**, so that script can
stall where plain `curl` succeeds — when it does, check the manifest and the
worker with `curl` instead and read the values, which is what actually matters.

**SuperPWA's settings are not exposed over REST** — no routes, and nothing in
`/wp/v2/settings`. So the four brand fields have to be set by hand in
**wp-admin → SuperPWA → Settings**, and until they are the app uses the
plugin's placeholder logo and a pale blue `#D5E0EB`:

| Field | Value |
|---|---|
| Application Icon | `sp-icon-512.png` (media id 65) |
| Splash Screen Icon | `sp-icon-512-maskable.png` (id 66) |
| Background Colour | `#0A0A0B` |
| Theme Colour | `#0A0A0B` |

The icons were cut from the lotus mark onto the brand's near-black, with the
maskable one held inside the safe zone because launchers crop to a circle.
`site_icon` is already pointed at id 65, which is what the favicon and the iOS
`apple-touch-icon` use.

## 10. Still open

The ₹999 price used to look like a typo and is not one. It read wrong only
while the page described twelve weekly 1:1 sessions; for a six-month group
program it is an ordinary number. Settled — do not raise it again.

- **Testimonials** — see §6. The section is built and hidden; three real
  client lines are all it needs.
- **Daily Instagram grid refresh** needs the `WP_USER` and `WP_APP` GitHub
  secrets (repo → Settings → Secrets and variables → Actions). Until then run
  `insta_sync.py --confirm` by hand.
- **Rotate the application password** - the current one was pasted into a chat
  on 09 Oct 2026. Put the new one in the GitHub secret and in the local
  `website/.wp-auth.json`.
- **Site Kit permission** - see §7b.
- **A floating "×" button** overlaps text on the left of the blog pages. It
  predates the blog work and is not in any file here; most likely a plugin.
- **Older posts still close with "free demo session"** while the template's
  call to action says free webinar.
- **Role lines differ.** The site says *Life, Relationship & Mindset Coach*;
  the creatives' signature reads *Life and Mindset Coach*; the daily pipeline's
  `BRAND_TAGLINE` is *Life & Relationship Coach*. He has been told; do not
  change any of them silently.
- **SuperPWA brand fields** - see §9, still set by hand.
