# Shashi Pallava — Daily Social Creatives MCP

Roz **5 branded creatives** banata hai (logo lagakar) aur **Facebook Page + Instagram**
pe post karta hai — sab kuch ek MCP server ke through, jise aap Claude se natural
language me chala sakte ho.

Page: <https://www.facebook.com/shashipallava>

---

## 1. Ye kya karta hai

```
content_bank.json  ──┐
assets/logo.png    ──┼──> renderer (Pillow) ──> output/YYYY-MM-DD/01..05.jpg
assets/backgrounds ──┘                                    │
                                                          v
                                            Meta Graph API ──> FB Page + Instagram
```

- **60 ready quotes** brand voice me, 8 themes ke saath (self worth, relationships,
  healing, boundaries, growth, morning, anxiety, letting go).
- **5 layouts**, aur selection background-aware hai:
  - Background photo **nahi** hai → `paper_quote`, `arch_card` (textured paper +
    gold keyline frame — printed card jaisa premium look)
  - Background photo **hai** → `quote_left`, `center_overlay`, `soft_band`
  - Ye isliye, kyunki photo-wale layouts plain background pe aadha frame khaali
    chhod dete hain.
- **Logo** har creative pe transparent lagta hai — koi white box nahi. Background
  ki brightness dekh kar apne aap full-colour ya cream monochrome version choose
  hota hai, taaki dark photo pe bhi saaf dikhe.
- **Rotation tracking** — ek quote dobara nahi aayega jab tak poora bank khatam na ho.
- **Captions + hashtags** auto-generate hote hain (Instagram me 18 tags, Facebook me 5).
- **Publishing guarded hai** — har publish tool default me dry-run karta hai.

---

## 2. Zaroori setup (ek baar)

### 2.1 Prerequisites — already done

| Cheez | Status |
| --- | --- |
| Python 3.14 | installed |
| Virtual env `.venv` | banaya, `mcp` + `Pillow` + `requests` installed |
| Logo | `assets/logo.png` pe copy ho gaya |
| Content bank | `content_bank.json`, 60 entries |

### 2.2 Meta side pe kya chahiye

1. **Instagram account Business/Creator hona chahiye** aur Facebook Page se linked hona
   chahiye. (Instagram app → Settings → Account type → Switch to Professional →
   phir Page se link karo.)
2. Aap dono ke **admin** ho.

### 2.3 Meta App banao

1. <https://developers.facebook.com/apps> → **Create App** → type **Business**.
2. App ban jaane ke baad **App ID** aur **App Secret** note karlo
   (Settings → Basic).

### 2.4 Access token nikalo

**Step A — user token with permissions**

<https://developers.facebook.com/tools/explorer> kholo:

- Upar apni app select karo.
- **Generate Access Token** dabao aur ye permissions add karo:

```
pages_show_list
pages_read_engagement
pages_manage_posts
instagram_basic
instagram_content_publish
business_management
```

Ye short-lived token (~1 ghanta) hai. Ise copy karlo.

> App **Development mode** me hi rahe to chalega — apne khud ke Page aur Instagram
> pe post karne ke liye App Review ki zaroorat nahi hai.

**Step B — long-lived token banao (60 din)**

Browser me ye URL kholo (apne values daalkar):

```
https://graph.facebook.com/v21.0/oauth/access_token
  ?grant_type=fb_exchange_token
  &client_id=APP_ID
  &client_secret=APP_SECRET
  &fb_exchange_token=SHORT_LIVED_TOKEN
```

**Step C — Page token nikalo (ye expire nahi hota)**

```
https://graph.facebook.com/v21.0/me/accounts?access_token=LONG_LIVED_USER_TOKEN
```

Response me apne Page ka `id` aur `access_token` milega. **Yahi wala
`access_token` use karna hai** — long-lived user token se derive hua Page token
expire nahi hota, isliye daily automation bina rukawat chalti rahegi.

**Step D — Instagram account ID**

```
https://graph.facebook.com/v21.0/PAGE_ID?fields=instagram_business_account&access_token=PAGE_TOKEN
```

Ya phir credentials bharne ke baad Claude se bolo: *"discover meta accounts"* —
`discover_meta_accounts` tool ye sab khud dhoond dega.

### 2.5 config.json bharo

```powershell
Copy-Item D:\Shi\config.example.json D:\Shi\config.json
```

Phir `config.json` edit karo:

```json
{
  "app_id": "...",
  "app_secret": "...",
  "page_id": "...",
  "ig_user_id": "...",
  "access_token": "PAGE_ACCESS_TOKEN",
  "api_version": "v21.0"
}
```

> `config.json` `.gitignore` me hai. Isme live token hai — kisi ke saath share
> mat karna.

Verify karo:

```powershell
D:\Shi\.venv\Scripts\python.exe D:\Shi\daily_run.py status
```

---

## 3. MCP server register karna

`.mcp.json` project root me already bana hua hai. Claude Code me project folder
`D:\Shi` kholo — server apne aap detect ho jayega (approve karna padega).

Manually add karna ho to:

```powershell
claude mcp add shashi-social --scope project -- D:\Shi\.venv\Scripts\python.exe -m shashi_social.server
```

Check: Claude me `/mcp` chalao, `shashi-social` connected dikhna chahiye.

---

## 4. Rozana kaise use karein (Claude se)

Bas normal baat karo:

| Aap bolo | Claude kya karega |
| --- | --- |
| "check setup" | `check_setup` — kya missing hai batayega |
| "aaj ke 5 creatives banao" | `generate_daily_creatives` |
| "creative 3 dikhao" | `preview_creative` — image dikhayega |
| "creative 2 ka layout badlo" | `regenerate_creative` |
| "creative 1 ka caption badlo" | `edit_caption` |
| "sab post kar do" | `publish_batch` — **pehle dry run dikhayega** |
| "haan confirm, post karo" | `publish_batch(confirm=True)` — live post |
| "page pe kya kya post hua" | `page_recent_posts` |

### Saare tools

**Setup:** `check_setup`, `discover_meta_accounts`, `verify_meta_credentials`
**Content:** `content_bank_status`, `add_content_entry`
**Banane ke liye:** `generate_daily_creatives`, `list_batch`, `list_batches`,
`preview_creative`, `regenerate_creative`, `edit_caption`
**Publish:** `publish_creative`, `publish_batch`, `publish_history`,
`page_recent_posts`

---

## 5. Command line se (Claude ke bina)

```powershell
$py = "D:\Shi\.venv\Scripts\python.exe"

# aaj ke 5 creatives banao
& $py D:\Shi\daily_run.py generate --count 5

# dry run — kuch post nahi hoga, sirf plan dikhega
& $py D:\Shi\daily_run.py publish

# actually post karo
& $py D:\Shi\daily_run.py publish --confirm

# ek hi command me dono
& $py D:\Shi\daily_run.py auto --count 5 --confirm

# sirf Instagram pe
& $py D:\Shi\daily_run.py publish --platforms instagram --confirm
```

Log: `state\daily_run.log`

---

## 6. Daily automatic chalane ke liye

**Safe mode (recommended)** — roz subah creatives ban jayenge, aap dekh kar khud
post karoge:

```powershell
cd D:\Shi
.\register_daily_task.ps1 -Time 08:00
```

**Fully automatic** — bina puche FB + Instagram dono pe post ho jayega:

```powershell
.\register_daily_task.ps1 -Time 09:30 -Publish
```

Test / remove:

```powershell
Start-ScheduledTask -TaskName "ShashiPallava-DailyCreatives"
.\register_daily_task.ps1 -Remove
```

> Fully automatic mode live business Page pe bina review ke post karta hai.
> Pehle kuch din safe mode chalakar output dekh lena behtar rahega.

---

## 7. Quality behtar karne ke liye

### 7.1 Background photos (sabse zyada farq padta hai)

Abhi backgrounds folder khaali hai, isliye system **procedural abstract
backgrounds** generate kar raha hai — ye theek dikhte hain, lekin real photos ke
saath creatives sample jaise premium lagenge.

`assets\backgrounds\` me aise photos daalo:

- **Bilkul plain — koi text nahi** (renderer khud text lagayega)
- Portrait ya square, kam se kam 1080x1350
- Brand palette: warm cream, blush pink, soft gold, natural light
- Achhe subjects: window light, coffee cups, linen/bedding, flowers, calm interiors,
  woman looking out of a window

Jitni zyada photos, utni variety. System recent 25 backgrounds yaad rakhta hai
taaki lagatar repeat na ho.

### 7.2 Font (sample se exact match ke liye)

Sample creatives me **Playfair Display** jaisa serif hai. Abhi Windows ka
Constantia use ho raha hai (kaafi acha hai). Exact match chahiye to
[Playfair Display](https://fonts.google.com/specimen/Playfair+Display) download
karke `assets\fonts\` me daalo:

```
PlayfairDisplay-SemiBold.ttf
PlayfairDisplay-Regular.ttf
PlayfairDisplay-Bold.ttf
```

Renderer apne aap pick kar lega. Sans ke liye `Montserrat-Regular.ttf` bhi daal
sakte ho.

### 7.3 Naya content add karna

Claude se bolo: *"add a new post: headline 'X', accent 'Y', theme boundaries,
caption '...'"*

Ya `content_bank.json` seedha edit karo:

```json
{
  "id": "q061",
  "theme": "boundaries",
  "headline": "Main line yahan.",
  "accent": "Rose colour wali doosri line.",
  "caption": "Post caption. Hashtags apne aap lag jayenge.",
  "bullets": ["optional", "list", "items"]
}
```

`bullets` daalne se creative automatically **arch card** layout me chala jayega.

---

## 8. Troubleshooting

| Error | Matlab / Fix |
| --- | --- |
| `Missing Meta credentials` | `config.json` me `page_id` / `access_token` nahi hai |
| `(code 190) Error validating access token` | Token expire ho gaya — Section 2.4 dohrao |
| `(code 200) Requires pages_manage_posts` | Token me permission missing — dobara generate karo |
| `(code 100) Unsupported post request` | `page_id` ya `ig_user_id` galat hai — `discover_meta_accounts` chalao |
| `ig_user_id is not configured` | Instagram ID missing — `discover_meta_accounts` chalao |
| `Instagram container ... ERROR` | Image aspect ratio (4:5 se 1.91:1) ya size problem — portrait canvas hi use karo |
| `A batch already exists` | Us date ka batch bana hua hai — `overwrite=true` do |
| Content khatam ho gaya | Rotation apne aap reset ho jaata hai; naye quotes add karo |

Graph API version purana lage to `config.json` me `api_version` badal do
(jaise `"v22.0"`).

---

## 9. File structure

```
D:\Shi\
├─ .mcp.json                  MCP registration (Claude Code)
├─ config.json                YOUR CREDENTIALS (gitignored)
├─ config.example.json        template
├─ content_bank.json          60 quotes + hashtag sets
├─ daily_run.py               CLI runner
├─ register_daily_task.ps1    Windows scheduler setup
├─ SETUP.md                   ye file
├─ assets\
│  ├─ logo.png                brand logo
│  ├─ backgrounds\            <- yahan photos daalo
│  └─ fonts\                  <- yahan Playfair daalo
├─ output\
│  └─ 2026-07-28\             ek din ka batch + batch.json
├─ state\
│  ├─ state.json              rotation + publish history
│  └─ daily_run.log
└─ shashi_social\
   ├─ server.py               MCP server (15 tools)
   ├─ pipeline.py             batch generate + publish
   ├─ renderer.py             layouts, typography, logo
   ├─ assets.py               logo keying, backgrounds
   ├─ content.py              content bank + captions
   ├─ meta_api.py             Graph API client
   ├─ brand.py                colours, fonts, sizes
   └─ state.py                rotation + history store
```
