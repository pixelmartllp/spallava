# Shashi Pallava — Cloud (GitHub Actions + Google Drive review)

Same shape as the AxisUV marketing automation, and everything lives under the
**pixelmartllp@gmail.com** account — both the Google Drive review folder and the
GitHub repo.

The PC no longer needs to be on. Each day, in the cloud:

| Time (IST) | What happens |
|---|---|
| **09:00** | 5 creatives are rendered and dropped into Drive → **Pending** |
| *anytime* | You look at them on your phone. Drag the good ones into **Approved**. **Delete** the ones you don't want. |
| **10:00** | Everything in **Approved** is posted to Facebook + Instagram, then moved to **Posted** |
| **11:00** | **Cutoff** — Approved *plus* anything still left in Pending is posted |

So approving is optional; **deleting is how you say no**. If you do nothing, the
day goes out at 11:00. Nothing is ever posted twice — posting moves the file out
of the folders the publisher reads.

---

## 1. Make the review folder in Drive

Signed in as **pixelmartllp@gmail.com**:

1. Create a folder in Google Drive called **`Shashi Review`**.
2. Open it and copy the **ID** out of the address bar — the long code after
   `/folders/`:

   ```
   https://drive.google.com/drive/folders/1AbCdEfGhIjKlMnOpQrStUvWxYz
                                          ^^^^^^^^^^^^^^^^^^^^^^^^^^ this
   ```

   Keep it handy — it becomes the `DRIVE_REVIEW_FOLDER_ID` secret in step 3.

You do **not** need to create Pending / Approved / Posted by hand — the first run
makes them.

## 2. Give rclone access to that Drive

On your PC, in PowerShell:

```powershell
rclone config
```

Answer: `n` (new remote) → name it exactly **`shashi`** → storage **`drive`** →
leave client id/secret blank → scope **`1`** (full access) → leave the rest at the
defaults → `y` to open the browser → **sign in as pixelmartllp@gmail.com and
allow** → `n` to team drive → `y` to confirm → `q` to quit.

Check it worked:

```powershell
cd D:\Shi
.\.venv\Scripts\python.exe daily_run.py drive-check
```

(For this to work locally, add the two Drive lines to `D:\Shi\config.json` —
see `config.example.json` for the exact key names.)

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
   | `DRIVE_REVIEW_FOLDER_ID` | the folder ID from step 1 |
   | `RCLONE_CONF` | the `[shashi]` block — see below |

   **RCLONE_CONF:** open `C:\Users\user\AppData\Roaming\rclone\rclone.conf` in
   Notepad and copy **only the `[shashi]` section** (the `[shashi]` line and
   every line under it, up to the next `[` heading). Don't paste the AxisUV
   remotes — this repo has no business holding them.

## 4. Test it

Repo → **Actions** tab.

1. **Shashi - Generate for review** → **Run workflow**. Green tick, then check
   Drive: `Shashi Review/Pending` should have 5 images + 5 `.json` caption files.
2. Move **one** image into **Approved** (drag the matching `.json` too, or leave
   it — the publisher looks in Pending for it either way).
3. **Shashi - Publish approved** → **Run workflow** (leave "include pending"
   unticked). Green tick = that one is live on facebook.com/shashipallava and
   Instagram, and the file has moved to `Posted`.

## 5. Turn off the PC task

Once a cloud run has posted successfully, disable the local task so the day is
not published twice:

```powershell
Disable-ScheduledTask -TaskName 'ShashiPallava-DailyCreatives'
```

(Or Task Scheduler → right-click `ShashiPallava-DailyCreatives` → **Disable**.)

---

## Things worth knowing

- **5 creatives a day**, both platforms — that is what the PC task was set to.
  Change the `--count` default in `.github/workflows/generate-review.yml`.
- **Don't want the 11:00 auto-post?** Delete the `- cron: '30 5 * * *'` line
  from `.github/workflows/publish-approved.yml`. Then only what you explicitly
  approve ever goes out.
- **`state/state.json` is committed by every run.** It is the only memory of
  which quotes have been used and what has been posted. Don't delete it.
- A creative that fails to post is **left where it is** and retried on the next
  run, so a blip doesn't lose a day.
- A creative whose `.json` caption file is missing is **skipped** — the caption
  carries the CTA and hashtags, so posting without it isn't worth it. Don't
  delete the `.json` files on their own.
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
  secret missing or misspelled.
- **`ConfigError: Missing Meta credentials`** — one of the three `META_*`
  secrets is missing.
- **Meta permission errors** — check the token locally:

  ```powershell
  cd D:\Shi
  .\.venv\Scripts\python.exe -c "from shashi_social import meta_api; print(meta_api.GraphClient().verify())"
  ```
