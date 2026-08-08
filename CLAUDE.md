# CLAUDE.md — Shashi Pallava daily social pipeline

Read this before touching anything in this repo. It exists because the same
three things kept going wrong: the creatives came out in the old card style,
the backgrounds were not real photographs, and the day did not auto-post.

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
style. It was rebuilt that day to 27 files, 22 of them theme-neutral, all
public-domain natural photography — see `assets/backgrounds/SOURCES.md` for
provenance and the rules for adding more. Keep the neutral majority: it is what
guarantees a photo is always available.

### 1.3 The day must actually post — verify, never assume

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
  11:41 IST retry pass is for.

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

**Everyday, two-step review flow**
1. `generate-review.yml` — cron `37 2 * * *` (08:07 IST). Renders and uploads
   to Google Drive `Pending`. Posts nothing. Commits rotation state.
2. `publish-approved.yml` — cron 10:08 / 11:09 / 11:41 IST. 10:08 posts only
   `Approved`. 11:09 is the **cutoff**: it posts `Approved` *plus* whatever is
   still in `Pending`, so approving is optional and **deleting from Pending is
   how you say no**. 11:41 is the retry pass. Posted files move to `Posted`,
   which is what prevents double-posting.

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
  brightness behind it.
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
