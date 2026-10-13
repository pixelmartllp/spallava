#!/usr/bin/env python
"""Generate the Brain Game question bank: 10 levels (Grade 1 to 10), 60 each.

    python website/game/bank_gen.py          # writes website/game/bank.json

Every question is built by a generator that knows the answer, then checked:
four distinct options, exactly one equal to the answer. Visual questions are
small inline SVGs. The bank is deterministic (fixed seed), so a rebuild gives
the same ids - which matters, because players' progress is stored by id.

Difficulty grows with the level: bigger numbers, two-step patterns, more
shapes, combined attributes. Points per correct answer and the unlock rule
live in sp-game.php, not here.
"""

from __future__ import annotations

import json
import math
import pathlib
import random
import string

OUT = pathlib.Path(__file__).resolve().parent / "bank.json"
PER_LEVEL = 60
R = random.Random(20261013)

# ------------------------------------------------------------------ helpers

def opts_num(ans: int, spread: int, extra: list[int] | None = None) -> list:
    pool = set(extra or [])
    pool.discard(ans)
    while len(pool) < 3:
        d = R.randint(1, max(2, spread))
        pool.add(ans + R.choice([-1, 1]) * d)
    pool.discard(ans)
    picks = R.sample(sorted(pool), 3)
    return picks + [ans]


def finish(q: dict, options: list, answer) -> dict:
    options = [str(o) for o in options]
    answer = str(answer)
    assert len(set(options)) == 4, (q, options)
    assert options.count(answer) == 1, (q, options, answer)
    R.shuffle(options)
    q["o"] = options
    q["a"] = options.index(answer)
    return q


# ------------------------------------------------------------------ text: number series

def g_series_arith(d):
    start = R.randint(1, 5 * d)
    step = R.randint(max(1, d // 2), 2 + d * 2) * R.choice([1, 1, 1, -1] if d > 3 else [1])
    n = [start + i * step for i in range(5)]
    ans = n[4]
    return finish({"k": "series", "q": f"What comes next?  {n[0]}, {n[1]}, {n[2]}, {n[3]}, ?",
                   "e": f"Each number changes by {step:+d}. {n[3]} {'+' if step > 0 else '-'} {abs(step)} = {ans}."},
                  opts_num(ans, max(3, abs(step))), ans)


def g_series_geo(d):
    mul = R.choice([2, 3] if d < 6 else [2, 3, 4, 5])
    start = R.randint(1, 3 if d < 6 else 6)
    n = [start * mul ** i for i in range(5)]
    ans = n[4]
    return finish({"k": "series", "q": f"What comes next?  {n[0]}, {n[1]}, {n[2]}, {n[3]}, ?",
                   "e": f"Each number is multiplied by {mul}. {n[3]} × {mul} = {ans}."},
                  opts_num(ans, ans // 4, [n[3] + (n[3] - n[2]), n[3] * (mul + 1)]), ans)


def g_series_two_step(d):
    a, b = R.randint(2, 4 + d), R.randint(1, 3 + d)
    x = R.randint(1, 10)
    n = [x]
    for i in range(5):
        n.append(n[-1] + (a if i % 2 == 0 else -b))
    ans = n[5]
    return finish({"k": "series", "q": f"What comes next?  {', '.join(map(str, n[:5]))}, ?",
                   "e": f"The pattern alternates: +{a}, -{b}. {n[4]} + {a} = {ans}."},
                  opts_num(ans, a + b, [n[4] - b]), ans)


def g_series_diff(d):
    start, inc = R.randint(1, 10), R.randint(1, 3)
    n, gap = [start], R.randint(1, 4)
    for _ in range(5):
        n.append(n[-1] + gap)
        gap += inc
    ans = n[5]
    gaps = [n[i + 1] - n[i] for i in range(4)]
    return finish({"k": "series", "q": f"What comes next?  {', '.join(map(str, n[:5]))}, ?",
                   "e": f"The gaps grow by {inc}: {', '.join(map(str, gaps))}, then {n[5] - n[4]}. So {n[4]} + {n[5] - n[4]} = {ans}."},
                  opts_num(ans, inc + 3, [n[4] + gaps[-1]]), ans)


SPECIAL = [
    ("squares", lambda i: (i + 1) ** 2, "They are square numbers: 1×1, 2×2, 3×3…"),
    ("cubes", lambda i: (i + 1) ** 3, "They are cube numbers: 1×1×1, 2×2×2…"),
    ("primes", lambda i: [2, 3, 5, 7, 11, 13, 17, 19, 23, 29, 31][i], "They are prime numbers - divisible only by 1 and themselves."),
    ("fib", lambda i: [1, 1, 2, 3, 5, 8, 13, 21, 34, 55][i], "Each number is the sum of the two before it."),
    ("tri", lambda i: (i + 1) * (i + 2) // 2, "Triangular numbers: add 2, then 3, then 4…"),
    ("sq1", lambda i: (i + 1) ** 2 + 1, "Square numbers plus one: 1×1+1, 2×2+1…"),
]


def g_series_special(d):
    name, f, why = R.choice(SPECIAL[:3] if d < 8 else SPECIAL)
    off = R.randint(0, 2) if name not in ("fib",) else R.randint(0, 3)
    n = [f(off + i) for i in range(6)]
    ans = n[5]
    return finish({"k": "series", "q": f"What comes next?  {', '.join(map(str, n[:5]))}, ?",
                   "e": f"{why} Next is {ans}."},
                  opts_num(ans, max(3, ans // 6), [n[4] + (n[4] - n[3])]), ans)


def g_letters(d):
    skip = R.randint(1, min(5, 1 + d // 2))
    start = R.randint(0, 25 - skip * 4)
    back = d > 6 and R.random() < 0.4
    idx = [start + i * skip for i in range(5)]
    if back:
        idx = [25 - i for i in idx]
    L = [string.ascii_uppercase[i] for i in idx]
    ans = L[4]
    pool = {string.ascii_uppercase[max(0, min(25, idx[4] + k))] for k in (-2, -1, 1, 2, skip + 1)}
    pool.discard(ans)
    while len(pool) != 3 and len(pool) < 3:
        pool.add(R.choice([c for c in string.ascii_uppercase if c != ans]))
    opts = R.sample(sorted(pool), 3) + [ans]
    return finish({"k": "letters", "q": f"Which letter comes next?  {L[0]}, {L[1]}, {L[2]}, {L[3]}, ?",
                   "e": f"Each step {'goes back' if back else 'moves forward'} {skip} letter{'s' if skip > 1 else ''} in the alphabet, so next is {ans}."},
                  opts, ans)


# ------------------------------------------------------------------ text: words

CATS = {
    "fruits": ["apple", "mango", "banana", "grapes", "litchi", "papaya", "guava"],
    "animals": ["lion", "tiger", "elephant", "horse", "rabbit", "deer", "monkey"],
    "colours": ["red", "blue", "green", "yellow", "purple", "pink", "white"],
    "vegetables": ["potato", "onion", "carrot", "spinach", "cabbage", "brinjal", "peas"],
    "birds": ["parrot", "sparrow", "peacock", "crow", "pigeon", "eagle", "owl"],
    "body parts": ["nose", "ear", "knee", "elbow", "shoulder", "ankle", "wrist"],
    "planets": ["Mars", "Venus", "Jupiter", "Saturn", "Mercury", "Neptune"],
    "instruments": ["sitar", "tabla", "guitar", "flute", "violin", "harmonium"],
    "feelings": ["joy", "anger", "fear", "sadness", "surprise", "calm"],
    "shapes": ["circle", "square", "triangle", "rectangle", "hexagon", "oval"],
}
CATS_HARD = {
    "synonyms of happy": ["glad", "cheerful", "joyful", "content", "delighted"],
    "words for brave": ["bold", "fearless", "daring", "courageous", "valiant"],
    "words for small": ["tiny", "little", "petite", "minute", "compact"],
    "metals": ["iron", "copper", "gold", "silver", "zinc", "aluminium"],
    "gases": ["oxygen", "nitrogen", "hydrogen", "helium", "carbon dioxide"],
    "units of length": ["metre", "inch", "mile", "yard", "kilometre"],
}


def g_odd_word(d):
    cats = dict(CATS)
    if d > 5:
        cats.update(CATS_HARD)
    main, other = R.sample(sorted(cats), 2)
    three = R.sample(cats[main], 3)
    odd = R.choice(cats[other])
    return finish({"k": "odd", "q": "Which one does NOT belong with the others?",
                   "e": f"{', '.join(three)} are all {main}. {odd} is from {other}."},
                  three + [odd], odd)


ANALOGIES = [
    (1, "hot", "cold", "up", "down", ["over", "high", "sky"]),
    (1, "cat", "kitten", "dog", "puppy", ["bone", "bark", "cub"]),
    (1, "day", "night", "black", "white", ["dark", "grey", "moon"]),
    (2, "bird", "fly", "fish", "swim", ["water", "fins", "sea"]),
    (2, "hand", "glove", "foot", "sock", ["toe", "leg", "walk"]),
    (2, "cow", "milk", "bee", "honey", ["sting", "flower", "hive"]),
    (3, "pen", "write", "knife", "cut", ["sharp", "kitchen", "steel"]),
    (3, "eye", "see", "ear", "hear", ["sound", "head", "ring"]),
    (3, "doctor", "hospital", "teacher", "school", ["book", "student", "lesson"]),
    (4, "tree", "forest", "star", "galaxy", ["sky", "night", "sun"]),
    (4, "chapter", "book", "verse", "poem", ["line", "word", "song"]),
    (4, "thirsty", "drink", "tired", "rest", ["sleepy", "bed", "yawn"]),
    (5, "seed", "plant", "egg", "bird", ["shell", "nest", "yolk"]),
    (5, "painter", "brush", "writer", "pen", ["book", "story", "paper"]),
    (5, "ice", "water", "water", "steam", ["cloud", "rain", "cold"]),
    (6, "finger", "hand", "toe", "foot", ["nail", "leg", "shoe"]),
    (6, "kilometre", "distance", "kilogram", "weight", ["metre", "heavy", "scale"]),
    (6, "calm", "storm", "hope", "despair", ["wish", "joy", "trust"]),
    (7, "brave", "coward", "generous", "selfish", ["kind", "rich", "giving"]),
    (7, "architect", "building", "composer", "symphony", ["piano", "concert", "music"]),
    (7, "drought", "rain", "famine", "food", ["hunger", "crop", "dry"]),
    (8, "patience", "virtue", "greed", "vice", ["money", "desire", "sin"]),
    (8, "fragile", "break", "flexible", "bend", ["soft", "strong", "rubber"]),
    (8, "map", "territory", "menu", "meal", ["restaurant", "list", "waiter"]),
    (9, "ephemeral", "brief", "eternal", "endless", ["old", "rare", "slow"]),
    (9, "candid", "frank", "aloof", "distant", ["shy", "rude", "quiet"]),
    (9, "symptom", "illness", "smoke", "fire", ["ash", "cloud", "air"]),
    (10, "benevolent", "kind", "malevolent", "spiteful", ["weak", "absent", "gentle"]),
    (10, "prologue", "epilogue", "dawn", "dusk", ["noon", "sunrise", "light"]),
    (10, "empathy", "understanding", "apathy", "indifference", ["anger", "sympathy", "sadness"]),
]


def g_analogy(d):
    pool = [a for a in ANALOGIES if abs(a[0] - d) <= 1] or ANALOGIES
    _, a, b, c, ans, wrong = R.choice(pool)
    return finish({"k": "analogy", "q": f"{a.capitalize()} is to {b} as {c} is to ?",
                   "e": f"The link between {a} and {b} is the same as between {c} and {ans}."},
                  wrong + [ans], ans)


NAMES = ["Asha", "Ravi", "Meera", "Kabir", "Neha", "Arjun", "Pooja", "Sahil", "Riya", "Dev"]


def g_word_problem(d):
    n = R.choice(NAMES)
    if d <= 2:
        a, b = R.randint(2, 9 + d * 3), R.randint(1, 8)
        ans = a + b
        q = f"{n} has {a} sweets and gets {b} more. How many sweets now?"
        e = f"{a} + {b} = {ans}."
    elif d <= 4:
        a, b = R.randint(3, 9), R.randint(2, 6 + d)
        ans = a * b
        q = f"{n} buys {b} packets with {a} pencils each. How many pencils in all?"
        e = f"{b} × {a} = {ans}."
    elif d <= 6:
        price, pct = R.choice([200, 400, 500, 800, 1000, 1200]), R.choice([10, 20, 25, 50])
        ans = price - price * pct // 100
        q = f"A ₹{price} dress has a {pct}% discount. What is the new price (₹)?"
        e = f"{pct}% of {price} is {price * pct // 100}. {price} - {price * pct // 100} = {ans}."
    elif d <= 8:
        speed, hrs = R.choice([30, 40, 45, 60, 80]), R.choice([2, 3, 4, 5])
        ans = speed * hrs
        q = f"A train runs at {speed} km per hour for {hrs} hours. How far does it go (km)?"
        e = f"Distance = speed × time = {speed} × {hrs} = {ans} km."
    else:
        a, b = R.randint(2, 5), R.randint(2, 5)
        while a == b:
            b = R.randint(2, 5)
        total = (a + b) * R.randint(5, 20)
        ans = total * a // (a + b)
        q = f"₹{total} is shared between {n} and a friend in the ratio {a}:{b}. How much does {n} get (₹)?"
        e = f"Total parts = {a + b}. One part = {total // (a + b)}. {n} gets {a} parts = {ans}."
    return finish({"k": "maths", "q": q, "e": e}, opts_num(ans, max(3, ans // 5)), ans)


def g_code(d):
    shift = R.randint(1, 1 + d // 3)
    words = ["CAT", "DOG", "SUN", "PEN", "BOOK", "TREE", "STAR", "MOON", "CALM", "HOPE", "GROW", "KIND"]
    w1, w2 = R.sample(words, 2)
    enc = lambda w, s=shift: "".join(chr((ord(c) - 65 + s) % 26 + 65) for c in w)
    ans = enc(w2)
    wrong = {enc(w2, shift + 1), enc(w2, shift - 1) if shift > 1 else enc(w2, shift + 2), ans[::-1], enc(w2[::-1])}
    wrong.discard(ans)
    return finish({"k": "code", "q": f"If {w1} is written as {enc(w1)}, how is {w2} written?",
                   "e": f"Every letter moves {shift} place{'s' if shift > 1 else ''} forward: {w2} → {ans}."},
                  R.sample(sorted(wrong), 3) + [ans], ans)


def g_order(d):
    people = R.sample(NAMES, 3 if d < 6 else 4)
    trait, more, most_w, least_w = R.choice([("taller", "taller", "tallest", "shortest"),
                                             ("older", "older", "oldest", "youngest"),
                                             ("faster", "faster", "fastest", "slowest")])
    facts = [f"{people[i]} is {more} than {people[i + 1]}" for i in range(len(people) - 1)]
    R.shuffle(facts)
    ask_most = R.random() < 0.5
    ans = people[0] if ask_most else people[-1]
    word = most_w if ask_most else least_w
    return finish({"k": "logic", "q": ". ".join(facts) + f". Who is the {word}?",
                   "e": f"Putting them in order: {' > '.join(people)}. So {ans} is the {word}."},
                  R.sample([p for p in people if p != ans], 3) + [ans] if len(people) == 4 else
                  [p for p in people if p != ans] + [R.choice([x for x in NAMES if x not in people]), ans], ans)


def g_odd_number(d):
    kind = R.choice(["even", "mult3", "mult5"] + (["square", "prime"] if d > 5 else []))
    if kind == "even":
        good = R.sample(range(2, 20 + d * 10, 2), 3)
        odd = R.choice(range(3, 20 + d * 10, 2))
        why = "are even numbers"
    elif kind == "mult3":
        good = [3 * k for k in R.sample(range(2, 10 + d * 3), 3)]
        odd = R.choice([x for x in range(10, 40 + d * 9) if x % 3])
        why = "are multiples of 3"
    elif kind == "mult5":
        good = [5 * k for k in R.sample(range(2, 10 + d * 3), 3)]
        odd = R.choice([x for x in range(11, 50 + d * 10) if x % 5])
        why = "are multiples of 5"
    elif kind == "square":
        good = [k * k for k in R.sample(range(3, 13), 3)]
        odd = R.choice([x for x in range(10, 150) if int(math.isqrt(x)) ** 2 != x])
        why = "are perfect squares"
    else:
        primes = [11, 13, 17, 19, 23, 29, 31, 37, 41, 43, 47]
        good = R.sample(primes, 3)
        odd = R.choice([15, 21, 25, 27, 33, 35, 39, 45, 49, 51])
        why = "are prime numbers"
    return finish({"k": "odd", "q": "Which number is the odd one out?",
                   "e": f"{', '.join(map(str, good))} {why}; {odd} is not."},
                  good + [odd], odd)


DAYS = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]


def g_calendar(d):
    if d < 9 or R.random() < 0.5:
        start = R.randrange(7)
        k = R.randint(3, 10 + d * 4)
        ans = DAYS[(start + k) % 7]
        return finish({"k": "calendar", "q": f"If today is {DAYS[start]}, what day will it be after {k} days?",
                       "e": f"Days repeat every 7. {k} ÷ 7 leaves {k % 7}, so count {k % 7} days on from {DAYS[start]}: {ans}."},
                      R.sample([x for x in DAYS if x != ans], 3) + [ans], ans)
    h, m = R.choice([(3, 0), (6, 0), (9, 0), (2, 0), (4, 0), (5, 0), (3, 30), (6, 30)])
    angle = abs(30 * h + 0.5 * m - 6 * m)
    angle = int(min(angle, 360 - angle))
    return finish({"k": "clock", "q": f"What is the smaller angle between the clock hands at {h}:{m:02d}?",
                   "e": f"The hour hand moves 30° per hour and 0.5° per minute; the minute hand 6° per minute. The gap is {angle}°."},
                  opts_num(angle, 30, [angle + 15, abs(angle - 15) or 45]), f"{angle}")


# ------------------------------------------------------------------ visual (SVG)

COLS = [("#E4572E", "red"), ("#2E86AB", "blue"), ("#F2B705", "yellow"), ("#3BA55C", "green"), ("#8E5572", "purple")]
SHAPES = ["circle", "square", "triangle", "diamond", "star", "hexagon"]


def shape(kind, cx, cy, r, fill, rot=0):
    if kind == "circle":
        return f'<circle cx="{cx}" cy="{cy}" r="{r}" fill="{fill}"/>'
    if kind == "square":
        pts = [(-r, -r), (r, -r), (r, r), (-r, r)]
    elif kind == "triangle":
        pts = [(0, -r), (r * 0.95, r * 0.75), (-r * 0.95, r * 0.75)]
    elif kind == "diamond":
        pts = [(0, -r), (r * 0.8, 0), (0, r), (-r * 0.8, 0)]
    elif kind == "hexagon":
        pts = [(r * math.cos(math.radians(60 * i)), r * math.sin(math.radians(60 * i))) for i in range(6)]
    elif kind == "star":
        pts = []
        for i in range(10):
            rr = r if i % 2 == 0 else r * 0.45
            a = math.radians(-90 + 36 * i)
            pts.append((rr * math.cos(a), rr * math.sin(a)))
    elif kind == "arrow":
        pts = [(0, -r), (r * 0.7, -r * 0.1), (r * 0.25, -r * 0.1), (r * 0.25, r), (-r * 0.25, r), (-r * 0.25, -r * 0.1), (-r * 0.7, -r * 0.1)]
    else:
        raise ValueError(kind)
    a = math.radians(rot)
    p = " ".join(f"{cx + x * math.cos(a) - y * math.sin(a):.1f},{cy + x * math.sin(a) + y * math.cos(a):.1f}" for x, y in pts)
    return f'<polygon points="{p}" fill="{fill}"/>'


def tile(inner: str, size=100) -> str:
    return (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {size} {size}">'
            f'<rect width="{size}" height="{size}" rx="10" fill="#fff" stroke="#d9d2c3"/>{inner}</svg>')


def strip(tiles: list[str]) -> str:
    """several tiles side by side plus a question-mark tile"""
    n = len(tiles) + 1
    body = ""
    for i, t in enumerate(tiles):
        body += f'<g transform="translate({i * 110},0)">{t}</g>'
    body += (f'<g transform="translate({(n - 1) * 110},0)"><rect width="100" height="100" rx="10" fill="#fff" '
             f'stroke="#d9d2c3" stroke-dasharray="6 5"/><text x="50" y="66" font-size="48" font-family="Arial" '
             f'font-weight="700" text-anchor="middle" fill="#9a8f7a">?</text></g>')
    return f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {n * 110 - 10} 100">{body}</svg>'


def raw(inner: str) -> str:
    return f'<rect width="100" height="100" rx="10" fill="#fff" stroke="#d9d2c3"/>{inner}'


def dots(n, fill="#2E86AB", kind="circle"):
    pos = [(50, 50)] if n == 1 else []
    if n > 1:
        cols = math.ceil(math.sqrt(n))
        rows = math.ceil(n / cols)
        gap = 70 / max(cols, rows)
        k = 0
        for r_ in range(rows):
            for c in range(cols):
                if k == n:
                    break
                pos.append((15 + gap / 2 + c * gap + (70 - cols * gap) / 2 + 0, 15 + gap / 2 + r_ * gap + (70 - rows * gap) / 2))
                k += 1
    rr = min(12, 70 / max(2, math.ceil(math.sqrt(n))) / 2 - 2)
    return "".join(shape(kind, x, y, rr, fill) for x, y in pos)


def v_rotation(d):
    step = R.choice([45, 90] if d < 5 else [45, 90, 135])
    # arrows only: a triangle looks the same every 120 degrees, so a 135-degree
    # turn reads as 15 and the puzzle stops being fair
    kind = "arrow"
    col = R.choice(COLS)[0]
    start = R.choice([0, 45, 90])
    seq = [start + i * step for i in range(4)]
    ans_rot = start + 4 * step
    mk = lambda rot: tile(shape(kind, 50, 50, 34, col, rot))
    opts = {ans_rot % 360: mk(ans_rot)}
    for wrong in (ans_rot - step, ans_rot + step, ans_rot + 180, ans_rot + 90, ans_rot - 45):
        if len(opts) == 4:
            break
        if wrong % 360 not in opts and (kind != "triangle" or (wrong % 120) != (ans_rot % 120)):
            opts[wrong % 360] = mk(wrong)
    ans = mk(ans_rot)
    return finish({"k": "visual", "q": "Which picture comes next in the pattern?",
                   "svg": strip([raw(shape(kind, 50, 50, 34, col, r)) for r in seq]),
                   "e": f"The shape turns {step}° clockwise every step."},
                  list(opts.values()), ans)


def v_count_seq(d):
    start = R.randint(1, 2)
    step = 1 if d < 4 else R.choice([1, 2])
    col = R.choice(COLS)[0]
    kind = R.choice(["circle", "square", "star"]) if d > 2 else "circle"
    seq = [start + i * step for i in range(4)]
    ans_n = start + 4 * step
    mk = lambda n: tile(dots(n, col, kind))
    wrong = [ans_n - 1, ans_n + 1, ans_n + step + 1, ans_n - 2]
    wrong = [w for w in dict.fromkeys(wrong) if w > 0 and w != ans_n][:3]
    return finish({"k": "visual", "q": "Which box comes next?",
                   "svg": strip([raw(dots(n, col, kind)) for n in seq]),
                   "e": f"Each box has {step} more shape{'s' if step > 1 else ''} than the one before, so next has {ans_n}."},
                  [mk(w) for w in wrong] + [mk(ans_n)], mk(ans_n))


def v_odd_shape(d):
    kind = R.choice(SHAPES[:4] if d < 5 else SHAPES)
    col, name = R.choice(COLS)
    how = R.choice(["shape", "colour"] if d < 6 else ["shape", "colour", "rotation", "size"])
    rot = R.choice([0, 15, 30]) if kind in ("triangle", "star") else 0
    base = tile(shape(kind, 50, 50, 32, col, rot))
    if how == "shape":
        other = R.choice([s for s in SHAPES if s != kind])
        odd = tile(shape(other, 50, 50, 32, col, rot))
        why = f"three are {kind}s; one is a {other}"
    elif how == "colour":
        oc, oname = R.choice([c for c in COLS if c[0] != col])
        odd = tile(shape(kind, 50, 50, 32, oc, rot))
        why = f"three are {name}; one is {oname}"
    elif how == "rotation":
        kind = R.choice(["triangle", "arrow"])
        base = tile(shape(kind, 50, 50, 32, col, 0))
        odd = tile(shape(kind, 50, 50, 32, col, 180))
        why = "one is turned upside down"
    else:
        odd = tile(shape(kind, 50, 50, 20, col, rot))
        why = "one is smaller than the others"
    # the three matching options must be distinct strings, so vary nothing visible but
    # an invisible comment - options are compared by index on the server anyway
    # options must be distinct strings; every one gets a random marker, the odd
    # one included, so the markup gives nothing away
    marks = R.sample(range(1000, 9999), 4)
    same = [base.replace("</svg>", f"<!--{m}--></svg>") for m in marks[:3]]
    odd = odd.replace("</svg>", f"<!--{marks[3]}--></svg>")
    return finish({"k": "visual", "q": "Which picture is different from the others?",
                   "e": f"Look closely: {why}."}, same + [odd], odd)


def v_count(d):
    target = R.choice(["triangle", "circle", "square", "star"])
    n = R.randint(2, 4 + d)
    distract = R.randint(2, 2 + d)
    # a square and a diamond are the same shape turned - never count one beside the other
    others = [s for s in ["triangle", "circle", "square", "star", "diamond"] if s != target and not (target == "square" and s == "diamond")]
    items = [target] * n + [R.choice(others) for _ in range(distract)]
    R.shuffle(items)
    placed, body = [], ""
    for it in items:
        for _ in range(200):
            x, y = R.uniform(14, 186), R.uniform(14, 106)
            if all((x - a) ** 2 + (y - b) ** 2 > 22 ** 2 for a, b in placed):
                break
        placed.append((x, y))
        body += shape(it, x, y, 9, R.choice(COLS)[0], R.choice([0, 0, 20]) if it in ("triangle", "star") else 0)
    svg = (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 200 120"><rect width="200" height="120" rx="10" '
           f'fill="#fff" stroke="#d9d2c3"/>{body}</svg>')
    return finish({"k": "visual", "q": f"How many {target}s are in the picture?", "svg": svg,
                   "e": f"There are {n} {target}s; the other shapes are there to distract you."},
                  opts_num(n, 2, [n + 1, n - 1, len(items)]), n)


def v_matrix(d):
    """3x3 grid: each row has the same shape, counts go 1,2,3 across (or colours cycle)."""
    shapes3 = R.sample(SHAPES[:4], 3)
    cols3 = R.sample(COLS, 3)
    mode = "count" if d < 7 else R.choice(["count", "colour"])
    cells = []
    for r_ in range(3):
        for c in range(3):
            if mode == "count":
                cells.append(dots(c + 1, cols3[r_][0], shapes3[r_]))
            else:
                cells.append(shape(shapes3[r_], 50, 50, 28, cols3[(r_ + c) % 3][0]))
    ans_inner = cells[8]
    grid = ""
    for i, cell in enumerate(cells):
        x, y = (i % 3) * 105, (i // 3) * 105
        if i == 8:
            grid += (f'<g transform="translate({x},{y})"><rect width="100" height="100" rx="10" fill="#fff" '
                     f'stroke="#d9d2c3" stroke-dasharray="6 5"/><text x="50" y="66" font-size="48" font-family="Arial" '
                     f'font-weight="700" text-anchor="middle" fill="#9a8f7a">?</text></g>')
        else:
            grid += f'<g transform="translate({x},{y})">{raw(cell)}</g>'
    svg = f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 310 310">{grid}</svg>'
    if mode == "count":
        wrong = [tile(dots(2, cols3[2][0], shapes3[2])), tile(dots(3, cols3[1][0], shapes3[1])),
                 tile(dots(3, cols3[2][0], shapes3[0]))]
        why = "Each row keeps one shape and colour, and the count goes 1, 2, 3."
    else:
        wrong = [tile(shape(shapes3[2], 50, 50, 28, cols3[(2 + k) % 3][0])) for k in (0, 1)] + \
                [tile(shape(shapes3[1], 50, 50, 28, cols3[(2 + 2) % 3][0]))]
        why = "Each row keeps one shape, and the colours shift one place along every row."
    return finish({"k": "visual", "q": "Which picture completes the grid?", "svg": svg, "e": why},
                  wrong + [tile(ans_inner)], tile(ans_inner))


# ------------------------------------------------------------------ assemble

GENS = [  # (generator, lowest level, highest level, weight)
    (g_series_arith, 1, 10, 3), (g_series_geo, 3, 10, 2), (g_series_two_step, 4, 10, 2),
    (g_series_diff, 6, 10, 2), (g_series_special, 5, 10, 2), (g_letters, 2, 10, 2),
    (g_odd_word, 1, 10, 2), (g_analogy, 1, 10, 3), (g_word_problem, 1, 10, 3),
    (g_code, 4, 10, 2), (g_order, 3, 10, 2), (g_odd_number, 3, 10, 2), (g_calendar, 6, 10, 2),
    (v_rotation, 1, 10, 2), (v_count_seq, 1, 8, 2), (v_odd_shape, 1, 10, 3), (v_count, 1, 10, 2),
    (v_matrix, 3, 10, 2),
]


def build() -> dict:
    bank = {}
    seen = set()
    for level in range(1, 11):
        pool = []
        for g, lo, hi, w in GENS:
            if lo <= level <= hi:
                pool += [g] * w
        made = 0
        tries = 0
        while made < PER_LEVEL:
            tries += 1
            assert tries < 5000, f"level {level} stuck at {made}"
            g = R.choice(pool)
            q = g(level)
            key = q["q"] + q.get("svg", "") + "|".join(sorted(q["o"]))
            if key in seen:
                continue
            seen.add(key)
            made += 1
            qid = f"L{level:02d}Q{made:03d}"
            q["l"] = level
            q["t"] = "visual" if ("svg" in q or q["o"][0].startswith("<svg")) else "text"
            bank[qid] = q
    return bank


MIND = pathlib.Path(__file__).resolve().parent / "mindset.json"


def add_mindset(bank: dict) -> None:
    """The Mindset Challenge: hand-written scenarios from her own posts,
    captions, chapters and FAQ. Track 'mind', ids M<level>Q<n>."""
    count = {}
    for item in json.loads(MIND.read_text(encoding="utf-8")):
        lvl = item["l"]
        count[lvl] = count.get(lvl, 0) + 1
        ans = item["o"][item["a"]]
        q = finish({"k": "mindset", "q": item["q"], "e": item["e"]}, list(item["o"]), ans)
        q.update({"l": lvl, "t": "text", "tr": "mind"})
        bank[f"M{lvl:02d}Q{count[lvl]:03d}"] = q


def main() -> None:
    bank = build()
    for q in bank.values():
        q["tr"] = "iq"
    add_mindset(bank)
    for qid, q in bank.items():
        assert len(q["o"]) == 4 and 0 <= q["a"] < 4, qid
    OUT.write_text(json.dumps(bank, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    kinds = {}
    for q in bank.values():
        kinds[q["k"]] = kinds.get(q["k"], 0) + 1
    vis = sum(1 for q in bank.values() if q["t"] == "visual")
    print(f"{len(bank)} questions, {vis} visual, {OUT.stat().st_size // 1024} KB")
    print("  by kind:", dict(sorted(kinds.items())))


if __name__ == "__main__":
    main()
