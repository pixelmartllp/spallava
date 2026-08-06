# Shashi Pallava — Cloud (GitHub Actions + Google Drive review)

Same shape as the AxisUV marketing automation, and everything lives under the
**pixelmartllp@gmail.com** account — both the Google Drive review folder and the
GitHub repo.

The PC no longer needs to be on. Each day, in the cloud:

| Time (IST) | What happens |
|---|---|
| **11:00** | 5 creatives are rendered and posted straight to the Facebook Page + Instagram |
| **12:00** | Retry pass — reposts nothing, only picks up anything the 11:00 run failed to post |

**No review step**, as asked. The 12:00 slot exists because the Graph API
returns a transient `code 1: please reduce the amount of data` often enough to
lose a post most days; `state/state.json` remembers what already went out, so
the retry can never post the same creative twice.

**Only steps 3, 4 and 5 below are required for this.** Steps 1 and 2 (Google
Drive) are only needed if you later want the optional review flow — see
[Optional: the review flow](#optional-the-review-flow) at the bottom.

---

## 1. Make the review folder in Drive *(optional — review flow only)*

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

## 2. Give rclone access to that Drive *(optional — review flow only)*

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
   New repository secret**, and add these **three**:

   | Secret name | Value |
   |---|---|
   | `META_PAGE_ID` | `page_id` from `D:\Shi\config.json` |
   | `META_IG_USER_ID` | `ig_user_id` from `config.json` |
   | `META_ACCESS_TOKEN` | `access_token` from `config.json` (never expires) |

   The token never expires, so this is a one-time job.

   Doing the optional review flow as well? Add two more:
   `DRIVE_REVIEW_FOLDER_ID` (the folder ID from step 1) and `RCLONE_CONF` —
   for the latter, open `C:\Users\user\AppData\Roaming\rclone\rclone.conf` in
   Notepad and copy **only the `[shashi]` section** (that line and everything
   under it, up to the next `[` heading). Don't paste the AxisUV remotes —
   this repo has no business holding them.

## 4. Test it

Repo → **Actions** tab → **Shashi Daily - Generate and post** → **Run
workflow**.

1. Tick **"Generate only"** first: it renders the 5 creatives and posts
   nothing. Download the **creatives** artifact from the run summary to see
   them.
2. Happy? Run it again with the tick **off** — that one posts for real.

Green tick = published. Check facebook.com/shashipallava and the Instagram
account.

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
  Change the `count` default in `.github/workflows/daily.yml`.
- **`state/state.json` is committed by every run.** It is the only memory of
  which quotes have been used and what has been posted — it is what stops
  repeats, and what makes the 12:00 retry safe. Don't delete it.
- **Backgrounds match the quote.** Each theme has its own scene — dawn light
  for `morning`, leaf shadows for `growth`, still water for `anxiety`, drifting
  petals for `letting_go`. Drop real photos into `assets/backgrounds/` and they
  are used instead.
- Re-running the 11:00 job on a day that already published does nothing
  (`--skip-if-posted`). The 12:00 job is different — it only ever fills gaps.
- GitHub's scheduled times drift by a few (sometimes many) minutes — normal.
- The rendered images are kept as a run **artifact** for 14 days, not in the
  repo.

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

- **`ConfigError: Missing Meta credentials`** — one of the three `META_*`
  secrets is missing or misspelled.
- **`GraphError (code 1): Please reduce the amount of data...`** — a Facebook
  flake, not your setup. The 12:00 retry run exists for exactly this; if it
  still shows up there, run the workflow by hand.
- **Meta permission errors** — check the token locally:

  ```powershell
  cd D:\Shi
  .\.venv\Scripts\python.exe -c "from shashi_social import meta_api; print(meta_api.GraphClient().verify())"
  ```
- **`DriveError: ...`** — review flow only: the `RCLONE_CONF` secret is missing
  the `[shashi]` block, `DRIVE_REVIEW_FOLDER_ID` is wrong, or the Drive access
  was revoked.

---

## Optional: the review flow

If you ever want to look at the creatives before they go out, two extra
workflows are already in the repo, set to **manual only**:

- **Shashi - Generate for review** → renders the day into Drive `Pending`
- **Shashi - Publish approved** → posts what you moved into `Approved`, then
  moves it to `Posted`

They need steps 1 and 2 above (the Drive folder and the `shashi` rclone
remote) plus the two extra secrets. To make them the everyday job, give them
`schedule:` blocks and **remove the schedule from `daily.yml`** — otherwise
the day gets posted twice.
