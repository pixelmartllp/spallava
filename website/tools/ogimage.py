from PIL import Image, ImageDraw, ImageFont, ImageFilter
import pathlib

# paths are relative to this file, so the folder can live anywhere
HERE = pathlib.Path(__file__).resolve().parent          # website/tools
PKG = HERE.parent.parent                                # the unzipped folder
ASSETS = HERE.parent / 'assets'
ORIGINALS = PKG / 'originals'
FONTS = HERE / 'fonts'
W, H = 1200, 630
BG = (10, 10, 11)
GOLD = (251, 189, 35)
GOLD_HI = (255, 214, 102)
CREAM = (250, 250, 250)
MUTED = (162, 162, 171)

card = Image.new('RGB', (W, H), BG)

# ---- her photo, bleeding off the right edge, faded into the ground ----
photo = Image.open(ORIGINALS / 's new.png').convert('RGB')
ph_w = 520
scale = ph_w / photo.width
ph = photo.resize((ph_w, int(photo.height * scale)), Image.LANCZOS)
ph = ph.crop((0, int(ph.height * 0.02), ph_w, int(ph.height * 0.02) + H))
card.paste(ph, (W - ph_w, 0))

# feather the photo's left edge into the background
grad = Image.new('L', (W, H), 255)
gd = ImageDraw.Draw(grad)
for x in range(W - ph_w, W - ph_w + 260):
    t = (x - (W - ph_w)) / 260.0
    gd.line([(x, 0), (x, H)], fill=int(255 * t))
gd.rectangle([0, 0, W - ph_w, H], fill=0)
card = Image.composite(card, Image.new('RGB', (W, H), BG), grad)

# ---- a gold glow behind the type, same as the site's hero ----
glow = Image.new('RGB', (W, H), BG)
ImageDraw.Draw(glow).ellipse([-220, 60, 620, 640], fill=(46, 34, 8))
glow = glow.filter(ImageFilter.GaussianBlur(120))
card = Image.blend(card, Image.blend(card, glow, 0.55), 0.75)

d = ImageDraw.Draw(card)

def font(name, size):
    return ImageFont.truetype(str(FONTS / name), size)

f_name = font('Montserrat-Medium.ttf', 74)
f_role = font('Montserrat-Medium.ttf', 25)
f_line = font('Montserrat-Regular.ttf', 30)
f_tag = font('Montserrat-Medium.ttf', 22)

x = 74
# logo mark, top left
logo = Image.open(ASSETS / 'sp-logo-mark.png').convert('RGBA')
lh = 96
logo = logo.resize((int(logo.width * lh / logo.height), lh), Image.LANCZOS)
card.paste(logo, (x, 62), logo)

d.text((x, 214), 'Shashi Pallava', font=f_name, fill=CREAM)

role = 'LIFE & RELATIONSHIP COACH  ·  MINDSET MENTOR'
d.text((x, 312), role, font=f_role, fill=GOLD)

d.line([(x, 366), (x + 92, 366)], fill=GOLD, width=3)

for i, line in enumerate(['Understand yourself better.', 'Build healthier relationships.']):
    d.text((x, 398 + i * 44), line, font=f_line, fill=MUTED)

# a quiet strip for the handle, bottom left
d.text((x, 528), 'shashipallava.com', font=f_tag, fill=GOLD_HI)

card.save(ASSETS / 'shashi-pallava-share.jpg', quality=88, optimize=True, progressive=True)
print('og image', card.size, round((ASSETS / 'shashi-pallava-share.jpg').stat().st_size / 1024), 'KB')
