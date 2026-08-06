# Shashi Pallava — Cloud (GitHub Actions + Google Drive review)

Same shape as the AxisUV marketing automation, and everything lives under the
**pixelmartllp@gmail.com** account — both the Google Drive review folder and the
GitHub repo.

The PC no longer needs to be on — the local task is already disabled. Each day,
in the cloud:

| Time (IST) | What happens |
|---|---|
| **08:00** | 5 creatives are rendered and dropped into Drive → **Pending** |
| *08:00–11:00* | You look at them on your phone. Drag the good ones into **Approved**. **Delete** the ones you don't want. |
| **10:00** | Anything already in **Approved** is posted, then moved to **Posted** |
| **11:00** | **Cutoff** — Approved *plus* anything still left in Pending is posted |
| **11:30** | Retry pass — posts nothing new, only picks up what failed at 11:00 |

So approving is optional; **deleting is how you say no**. Do nothing and the
day goes out at 11:00 anyway. Approve early and it goes out at 10:00 instead.
Nothing can be posted twice — posting moves the file out of the folders the
publisher reads.

The 11:30 slot is there because the Graph API returns a transient
`code 1: please reduce the amount of data` often enough to lose a post most
days.

---

## 1. The review folder in Drive — ✅ done

`Shashi Review` exists in the pixelmartllp@gmail.com Drive, with `Pending`,
`Approved` and `Posted` inside it. Its ID is
**`1-wu2A9Lv-OpjOOxkw9f-lTcwMbzipg_L`** — that is the `DRIVE_REVIEW_FOLDER_ID`
secret in step 3.

## 2. rclone access — ✅ done

The remote is called **`shashi`** and is authorised against
pixelmartllp@gmail.com. `config.json` already carries `drive_remote` and
`drive_review_folder_id`, so this works locally:

```powershell
cd D:\Shi
.\.venv\Scripts\python.exe daily_run.py drive-check
```

If that ever returns `ok: false` with a 401 / `Invalid Credentials`, the Google
authorisation has lapsed. Re-run it and answer `y`, `y`, **`n`** (not a Shared
Drive), `y`:

```powershell
rclone config reconnect shashi:
```

Then update the `RCLONE_CONF` secret, because reconnecting writes a new token.

## 3. Put the repo on GitHub

1. **GitHub Desktop** → **File → Add local repository** → `D:\Shi` →
   **Publish repository** → tick **"Keep this code private"**, and publish it to
   the **pixelmartllp** GitHub account.

   `.gitignore` already excludes `config.json`, the rendered images and the
   virtualenv, so only code + logo + content bank get uploaded.

2. On github.com open the repo → **Settings → Secrets and variables → Actions →
   New repository secret**, and add these **five**:

   | Secret name | Value |
   |---|---|
   | `META_PAGE_ID` | `page_id` from `D:\Shi\config.json` |
   | `META_IG_USER_ID` | `ig_user_id` from `config.json` |
   | `META_ACCESS_TOKEN` | `access_token` from `config.json` (never expires) |
   | `DRIVE_REVIEW_FOLDER_ID` | `1-wu2A9Lv-OpjOOxkw9f-lTcwMbzipg_L` |
   | `RCLONE_CONF` | the `[shashi]` block — see below |

   The Meta token never expires, so that part is a one-time job.

   **RCLONE_CONF:** open `C:\Users\user\AppData\Roaming\rclone\rclone.conf` in
   Notepad and copy **only the `[shashi]` section** — that heading and the four
   lines under it (`type`, `scope`, the long `token = {...}` line, and
   `team_drive =`), stopping before the next `[` heading. Don't paste the
   AxisUV remotes; this repo has no business holding them.

## 4. Test it

Repo → **Actions** tab.

1. **Shashi - Generate for review** → **Run workflow**. Green tick, then check
   Drive: `Shashi Review/Pending` should have 5 images + 5 `.json` caption
   files.
2. Move **one** image into **Approved**. (Leave its `.json` behind if you like
   — the publisher looks in Pending for it too.)
3. **Shashi - Publish approved** → **Run workflow**, leave "include pending"
   unticked. Green tick = that one is live on facebook.com/shashipallava and
   Instagram, and the file has moved to `Posted`.

After that the schedule takes over and you do nothing.

## 5. The PC task

Already **disabled** — the cloud owns the schedule now. If you ever need it
back:

```powershell
Enable-ScheduledTask -TaskName 'ShashiPallava-DailyCreatives'
```

Don't leave it enabled alongside the cloud, or the day gets posted twice.

---

## Things worth knowing

- **5 creatives a day**, both platforms. Change the `count` default in
  `.github/workflows/generate-review.yml`.
- **`state/state.json` is committed by every run.** It is the only memory of
  which quotes have been used and what has been posted. Don't delete it.
- **Backgrounds match the quote.** Each theme has its own scene — dawn light
  for `morning`, leaf shadows for `growth`, still water for `anxiety`, drifting
  petals for `letting_go`. Drop real photos into `assets/backgrounds/` and they
  are used instead.
- A creative that fails to post is **left where it is** and picked up by the
  next run, so a blip doesn't lose a day.
- A creative whose `.json` caption file is missing is **skipped** — the caption
  carries the CTA and hashtags, so posting without it isn't worth it. Don't
  delete the `.json` files on their own.
- **Need a day out right now, no review?** Actions → **Shashi Daily - Generate
  and post** → Run workflow. It skips Drive entirely. It has no schedule, so it
  can't collide with the daily flow.
- GitHub's scheduled times drift by a few (sometimes many) minutes — normal.

## Content bank

`content_bank.json` holds 60 quotes. At 5/day the rotation **restarts
automatically** when it runs out — it won't fail, it will start repeating old
quotes. Top it up with `add_content_entry` (or by editing `content_bank.json`)
before that happens. Check what's left any time:

```powershell
.\.venv\Scripts\python.exe daily_run.py status
```

## If a run fails

Open the failed run in the **Actions** tab and read the failing step's log.
The realistic causes:

- **`DriveError: rclone ... failed`** — the `RCLONE_CONF` secret is missing the
  `[shashi]` block, or the Drive access was revoked. Re-run `rclone config` and
  update the secret.
- **`DriveError: No Drive review folder configured`** — `DRIVE_REVIEW_FOLDER_ID`
  is missing or misspelled.
- **`ConfigError: Missing Meta credentials`** — one of the three `META_*`
  secrets is missing or misspelled.
- **`GraphError (code 1): Please reduce the amount of data...`** — a Facebook
  flake, not your setup. The 11:30 run exists for exactly this; if it survives
  that too, the creative is still sitting in Drive, so just run **Publish
  approved** by hand.
- **Meta permission errors** — check the token locally:

  ```powershell
  cd D:\Shi
  .\.venv\Scripts\python.exe -c "from shashi_social import meta_api; print(meta_api.GraphClient().verify())"
  ```
