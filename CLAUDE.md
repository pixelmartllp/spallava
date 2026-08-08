# CLAUDE.md — Shashi Pallava daily social pipeline

Read this before touching anything in this repo. It exists because the same
things kept going wrong: the creatives came out in the old card style, the
backgrounds were not real photographs, and the day did not auto-post — and then,
once real photographs went in, the type and the logo stopped reading on them.
Every rule below is something that actually shipped wrong at least once.

The owner is **Sanjeev** (@axisuv), writing for the **Shashi Pallava** life &
relationship coaching brand — facebook.com/shashipallava and the linked
Instagram. He often writes in Hinglish; reply in the language he used. Reply
about what actually happened, not what the code intends to happen.

---

## 1. Standing instructions (do not re-litigate these)

These are decisions the owner has already made and repeated. Treat them as
requirements, not preferences.

### 1.1 Backgrounds must be real, natural, live photography — and must not show faces

Every background is a photograph of the real world: light, water, sky, leaves,
mist, sand, stone, fabric, a window, a horizon. "Live natural" means an actual
photo, not a drawn or generated scene.

**No human faces. Ever.** No identifiable person, no couple facing camera, no
portrait. A silhouette, a back-of-head at distance, or hands are acceptable
only if no face is readable. The brand's authority comes from the words and the
logo; a stock face makes it look like a stock post.

Also out: text baked into the photo, watermarks, logos of other brands,
recognisable landmarks, anything AI-obviously-generated.

The synthetic scenes in `shashi_social/assets.py` (`procedural_background`,
`THEME_SCENES`, `_scene_dawn`, `_botanical`, …) are a **fallback only**. They
are the "old way" the owner keeps rejecting. Do not treat a run that used them
as a successful run.

### 1.2 Never ship the old card look

The old look = a cream card / paper stock / arch panel with the quote printed
on it. In code that is layout `paper_quote` or `arch_card`, and it is what
`choose_layout()` falls back to whenever `has_photo` is false.

Target look = `editorial` (full-bleed photograph, quote set into its calm
region) or `center_overlay`. A batch is only acceptable when **every item in
`batch.json` has a real filename in `background`, not `"generated"`.**

Two known traps that silently produce the old look:

- **Empty photo pool for a theme.** `assets/backgrounds/<theme>-NN.jpg` is
  reserved for that theme only (`photo_theme()`); an unprefixed name like
  `calm-water.jpg` is usable by any theme. If a theme has no photo of its own
  and there are no unprefixed photos, that quote silently falls back to a
  generated scene. **Every theme in the content bank needs photo coverage.**
  Themes today: `morning`, `growth`, `healing`, `self_worth`, `boundaries`,
  `relationships`, `letting_go`, `anxiety` (185 entries total).
- **Bullet entries.** `renderer.render()` passes `allow_photo=not entry.get("bullets")`,
  so any quote with a `bullets` list is *forced* onto `arch_card` with a
  generated background. If bullet entries keep landing in the daily batch,
  that is a source of old-look creatives — raise it rather than shipping it.

Also: `state.recent_backgrounds()` excludes recently used photos. With a pool
of five, exclusion can empty the pool and drop everything back to generated.
Pool size has to comfortably exceed the exclusion window.

**History:** on 08 Aug 2026 the pool was 5 files covering only 2 themes, which
is why 4 of 5 creatives on 07 Aug and 5 of 5 on 06 Aug came out in the old
style. It was rebuilt that day to **27 photographs — 21 theme-neutral, 6 locked**
(`letting_go-01`, `relationships-01..05`), all public-domain natural
photography. See `assets/backgrounds/SOURCES.md` for provenance and the rules
for adding more. Keep the neutral majority: it is what guarantees a photo is
always available.

Sourcing that actually works, if the pool ever needs topping up: **Wikimedia
Commons**, filtered to CC0 / public-domain marks read from each file's own
`extmetadata`, pulled through the API's `iiurlwidth` render. Two other routes
were tried first and both failed on pixels, not taste — Openverse hands back a
1024px derivative from most providers whatever the original size, and StockSnap's
CDN returns 403. Commons throttles hard: keep downloads to ~4 concurrent with
backoff, or most of them 429. A good slice of the usable results are the CC0
Unsplash photographs mirrored onto Commons.

Always **look at the candidates before shipping them** — a contact sheet cropped
the way the renderer crops is the cheap way. That check is what caught a
watermark, a person in a red jacket, an Angkor Wat silhouette and a vintage
painting in this pool's own shortlist. Metadata will not tell you any of that.

### 1.3 Type has to read on the photograph — and so does the logo

Putting real pictures behind the words is what exposed both of these. Neither is
a preference; both were shipped defects the owner spotted.

**The scrim is measured, not assumed.** `_layout_editorial` now fits the type
*before* anything is painted, picks its palette from the band the words actually
occupy, and calls `seat_text()`, which deepens a feathered `band_scrim()` until
the tail that fights the ink has separated. Three things there are load-bearing:

- Judge the **band the text occupies**, not the whole upper frame. A frame can
  average pale while the strip carrying the accent line is a blown-out sun.
- Judge on a **percentile, not the mean** (`region_levels()`). A band of wheat
  averages bright while every ear in it is mid-tone; a mean-based test passes
  and the rose accent still lands on something too dark to read against.
- The **accent line fails first** — it is smaller and lower contrast than the
  headline. If you are eyeballing a creative, check the accent, not the
  headline.

Type is also fitted to the calm zone the photograph offers (`calm_extent()`), so
a frame with a high treeline gets smaller type. That is deliberate: more scrim
would bury the picture, which is the thing we went to real photography for.

**The logo is sized by the footer band's height, not its width.** The mark is
nearly square, so a short band binds on height — at the old 0.11-of-canvas band
it rendered 98px wide on a 1080 canvas and simply vanished. `editorial` and
`center_overlay` now give it a taller band (~215px). On top of that,
`load_logo_fit()` lifts the alpha by a gamma after resizing: these are hairline
strokes inside a hairline gold ring, they land on a fraction of a pixel once
shrunk, and downsampling averages them against transparency. Colour is
untouched — only how much of it lands.

Judge both **at full size**. A contact sheet squeezed to 430px makes a perfectly
good logo look faint, which will send you chasing a bug that is not there.

### 1.4 The day must actually post — verify, never assume

"Generated" is not "posted". The automation has three separate places where a
day can die silently, and it has died in all three:

- **GitHub cron drift.** `generate-review.yml` asks for 08:07 IST but GitHub
  regularly runs it 2–3 hours late. On 2026-08-08 it landed at 10:54 IST —
  after the 10:08 publish run had already found `Pending` empty and exited
  with "Nothing to post".
- **Drive auth.** The rclone token in the `RCLONE_CONF` secret expires. When it
  does, `review.probe()` raises and `daily_run.py` logs `NOT READY: … Error 401`
  and returns 3. Nothing posts, and because no post was recorded, no state
  commit appears — so the failure leaves almost no trace in the repo.
- **Graph API flakes.** The API returns a transient `code 1: please reduce the
  amount of data` often enough to lose a post most days; that is what the
  repeated cutoff passes are for.

The drift race is partly mitigated — since 08 Aug the publish side sweeps at
13:53 and 16:47 IST as well, so a generate that lands after 11:41 still goes
out the same day. The Drive-auth failure is **not** fixed and cannot be fixed
from here: it needs the owner to paste a fresh local `rclone.conf` into the
`RCLONE_CONF` GitHub secret.

So: after any change, or any time the owner asks whether the day went out,
**check the evidence**, do not read the workflow file and infer.

---

## 2. Definition of done

Before telling the owner a day is fine, confirm all three:

```bash
git fetch && git log origin/main --format='%h %ad %s' --date=iso -8
# "Update rotation state"  = generation ran
# "Update publish state"   = something actually posted (or failed) that day

.venv/Scripts/python.exe -c "import json;s=json.load(open('state/state.json',encoding='utf-8'));\
print([ (p['date'],p['platform'],p.get('ok')) for p in s['posts'] if p['date']=='YYYY-MM-DD'])"

.venv/Scripts/python.exe -c "import json;b=json.load(open('output/YYYY-MM-DD/batch.json',encoding='utf-8'));\
[print(i['index'],i['theme'],i['layout'],i['background']) for i in b['items']]"
```

Pass = a publish-state commit exists, `ok: true` rows exist for both platforms,
and every `background` is a real filename. Anything else is a failure — say so
plainly and name which of the three stages broke.

`gh` is not installed on this machine, so Actions logs are not readable from
here. If a run's outcome cannot be established from the repo, say that instead
of guessing.

---

## 3. How the pipeline actually works

```
content_bank.json ──> content.select()  ──┐
assets/backgrounds ──> assets.get_background() ──> renderer.render() ──> output/<date>/NN-<id>.jpg
                                                                          + batch.json (captions, status)
```

Two automation paths, both on `windows-latest` on purpose (the brand fonts
`constan.ttf` / `segoeui.ttf` ship with Windows; Ubuntu would silently render a
different typeface):

**Everyday, two-step review flow — one creative a day**
1. `generate-review.yml` — cron `37 2 * * *` (08:07 IST). Renders **one**
   creative (the scheduled run passes no input, so the step's own `$count`
   fallback is the real daily number) and uploads it to Google Drive `Pending`.
   Posts nothing. Commits rotation state.
2. `publish-approved.yml` — 10:08 / 11:09 / 11:41 / 13:53 / 16:47 IST. 10:08
   posts only `Approved`. **Every later run is a cutoff**: it posts `Approved`
   *plus* whatever is still in `Pending`, so approving is optional and
   **deleting from Pending before 11:09 is how you say no**. The last two exist
   because the 08:07 generate is regularly delayed by GitHub's queue — on
   08 Aug 2026 it landed at 10:54 — and a day that generates late must still go
   out. They are free on a normal day: anything published has already moved to
   `Posted`, so they find an empty queue.

Posted files move to `Posted`, which is what prevents double-posting.

**Escape hatch** — `daily.yml`, `workflow_dispatch` only. Generates and posts
straight to the Page, skipping review. Never give it a `schedule:`; with the
other two scheduled, the day would go out twice.

Local CLI (`daily_run.py`): `generate`, `publish`, `auto`, `review`,
`publish-approved`, `drive-check`, `status`. Use `.venv/Scripts/python.exe` —
bare `python` on this machine hits the Microsoft Store stub and fails.

---

## 4. Safety rules

- **Publishing is live.** `publish` / `publish-approved` / `auto` are dry-run
  unless `--confirm`. Never pass `--confirm` (or `confirm=True` on the
  `shashi-social` MCP tools) without the owner explicitly approving that
  specific post in that conversation. The Page has a real audience.
- **`config.json` holds live Meta credentials** and is gitignored. Never commit
  it, never paste its contents into a message, a PR, an artifact, or any
  external service. Same for `RCLONE_CONF`, `META_ACCESS_TOKEN`, and the other
  GitHub secrets.
- **`state/state.json` is committed on purpose** — it is the cloud run's only
  memory of what it already posted. Do not gitignore it, do not hand-edit the
  `posts` ledger to make a day look successful.
- `output/` is gitignored and regenerated every run; the cloud run has no copy
  of yesterday's images.
- Don't re-post to "test". Use `--dry-run` / the `dry_run` MCP default.

---

## 5. Brand rules

- Palette, fonts, canvas sizes and the strapline all live in
  `shashi_social/brand.py` — change them there, never inline in the renderer.
- Canvas default `portrait` 1080×1350. Logo goes on bare (no white plate); the
  renderer picks the full-colour or cream monochrome mark from the measured
  brightness behind it. See §1.3 before changing anything about its size.
- Strapline is `BRAND_TAGLINE = "Life & Relationship Coach"` — one phrase, set
  by the owner on 08 Aug 2026. Note the logo artwork already contains
  "LIFE • RELATIONSHIP • COACH", so the line under it is a deliberate repeat.
  He has been told; do not silently "fix" it.
- Voice: warm, plain, second person, no jargon, no hard sell. Captions get a
  CTA plus up to 18 hashtags on Instagram, 5 on Facebook.
- New quotes go in `content_bank.json` with a unique `id`, a `theme` from the
  list above, a `headline`, an optional `accent`, and hashtags. Prefer `accent`
  over `bullets` — see §1.2 on why bullets force the old look.

---

## 6. Working style the owner expects

- Fix the root cause, not the symptom. "Generated a nicer fallback scene" is
  not a fix for "backgrounds must be photographs".
- Report what actually happened, including what did not work. If one of the
  three stages is still broken after a change, say which one.
- Ship the whole thing. If part is blocked (e.g. Drive token expired and only
  he can re-auth), finish everything else and name the blocked part precisely,
  with what he has to do.
- He reviews on his phone, in Drive. Send him finished work, not options.

---

## 7. Where things stand (08 Aug 2026)

Facts, so a later session does not have to re-derive them:

- **Cadence: one creative a day**, live from 09 Aug. Set in
  `generate-review.yml` — and note the number that matters is the run step's own
  `$count` fallback, because the scheduled run passes no input. The dispatch
  input default is only what a manual run sees. Both are `1`.
- **Content bank**: 185 entries, 115 unused → ~115 days at one a day. The
  rotation resets itself when the bank empties, so it never hard-fails.
- **Backgrounds**: 27 photographs, 21 of them theme-neutral.
- **08 Aug posted 5 creatives × 2 platforms**, all `ok`, published manually
  after the day's scheduled windows had passed — the owner approved all five
  explicitly. 06–07 Aug also went out; 30 Jul–04 Aug are failures in the ledger.
- **Open, needs the owner**: the `RCLONE_CONF` GitHub secret. Drive works from
  this machine; the cloud's copy is the prime suspect for 08 Aug posting
  nothing on schedule (a 401 appears in the log on 06 Aug). If a day generates
  but never posts, look there first.
- Working scripts from the background-sourcing job live in the session
  scratchpad, not the repo — `fetch_commons.py` (Commons + PD filter),
  `sheet.py` (contact sheet), `install_bg.py` (resize, rename, write
  SOURCES.md). Worth rewriting rather than hunting for.
