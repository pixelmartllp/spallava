#!/usr/bin/env python
"""Generate the Brain Game question bank: 10 levels (Grade 1 to 10), 60 each.

    python website/game/bank_gen.py          # writes website/game/bank.json

Every question is built by a generator that knows the answer, then checked:
four distinct options, exactly one equal to the answer. Visual questions are
small inline SVGs. The bank is deterministic (fixed seed), so a rebuild gives
the same ids - which matters, because players' progress is stored by id.

Each level has its own mix of question kinds, and the mix climbs steeply:

  1-2   one step: count, add and take away within 20, simple patterns,
        odd one out of everyday things
  3-4   two steps: tables, change from a note, x2/x3 series, +1 letter codes,
        simple analogies, who is tallest, time on a clock
  5-6   mixed operations, fractions and percentages, letter series with
        growing skips, 3x3 picture grids with one rule, directions,
        simple family relations, ranks in a row
  7-8   two-rule picture grids, interleaved series, ratios, speed and
        distance, clock angles, calendars, reversed codes, syllogisms,
        seating puzzles
  9-10  multi-rule series, probability, work and pipes, ages, tricky family
        relations, rotation + count grids, dice and painted cubes, five-person
        seating deductions - level 10 is meant to be hard for an adult

Wrong options are built from the mistakes people actually make (the reflex
answer, the forgotten step, the reversed ratio), not random numbers. Where an
answer can be worked out a second, independent way (brute force, a calendar,
enumerating dice), the generator attaches a check that self_check() runs
before anything is written.

Points per correct answer and the unlock rule live in sp-game.php, not here.
"""

from __future__ import annotations

import datetime
import itertools
import json
import math
import pathlib
import random
import string
from fractions import Fraction

OUT = pathlib.Path(__file__).resolve().parent / "bank.json"
PER_LEVEL = 60
R = random.Random(20261103)
AB = string.ascii_uppercase

NAMES_F = ["Asha", "Meera", "Neha", "Pooja", "Riya", "Kavya", "Isha", "Tara"]
NAMES_M = ["Ravi", "Kabir", "Arjun", "Sahil", "Dev", "Rohan", "Aman", "Vikram"]
NAMES = NAMES_F + NAMES_M
DAYS = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
MONTHS = ["January", "February", "March", "April", "May", "June", "July", "August",
          "September", "October", "November", "December"]


# ------------------------------------------------------------------ helpers

def pron(name):
    return "She" if name in NAMES_F else "He"


def nth(n):
    return f"{n}{'th' if 10 <= n % 100 <= 20 else {1: 'st', 2: 'nd', 3: 'rd'}.get(n % 10, 'th')}"


def fmt(x):
    """ints stay ints, Fractions print as a/b, halves as .5"""
    if isinstance(x, Fraction):
        if x.denominator == 1:
            return str(x.numerator)
        if x.denominator == 2 and abs(x) > 1:
            return f"{float(x):g}"
        return f"{x.numerator}/{x.denominator}"
    if isinstance(x, float) and x.is_integer():
        return str(int(x))
    return str(x)


def nopts(ans, mistakes=(), spread=None, neg=False):
    """the answer plus three wrong numbers - the listed mistakes first"""
    if spread is None:
        spread = max(3, int(abs(ans)) // 6)
    ms = []
    for m in mistakes:
        if m != ans and m not in ms and (neg or m >= 0):
            ms.append(m)
    R.shuffle(ms)
    out = ms[:3]
    while len(out) < 3:
        v = ans + R.choice([-1, 1]) * R.randint(1, max(2, spread))
        if v != ans and v not in out and (neg or v >= 0):
            out.append(v)
    return out + [ans]


def finish(q: dict, options: list, answer, check=None) -> dict:
    options = [fmt(o) for o in options]
    answer = fmt(answer)
    assert len(set(options)) == 4, (q, options)
    assert options.count(answer) == 1, (q, options, answer)
    R.shuffle(options)
    q["o"] = options
    q["a"] = options.index(answer)
    if check:
        q["_check"] = check
    return q


def wrong_from(pool, ans, n=3):
    return R.sample([p for p in dict.fromkeys(pool) if p != ans], n)


def pick(ans, cands, fill):
    """the answer plus the listed wrong ones, de-duplicated, topped up from fill"""
    out = [c for c in dict.fromkeys(cands) if c != ans][:3]
    rest = [f for f in fill if f != ans and f not in out]
    R.shuffle(rest)
    return out + rest[:3 - len(out)] + [ans]


# ------------------------------------------------------------------ levels 1-2: one step

ITEMS = ["sweets", "balloons", "marbles", "pencils", "stickers", "mangoes", "books", "flowers", "shells"]


def g_add(d):
    n, it = R.choice(NAMES), R.choice(ITEMS)
    top = 10 if d == 1 else 20
    a = R.randint(1, top - 2)
    b = R.randint(1, top - a)
    ans = a + b
    return finish({"k": "maths", "q": f"{n} has {a} {it}. {pron(n)} gets {b} more. How many {it} does {n} have now?",
                   "e": f"{a} + {b} = {ans}."}, nopts(ans, [ans - 1, ans + 1, abs(a - b), ans + 2]), ans,
                  lambda a=a, b=b: a + b)


def g_sub(d):
    n, it = R.choice(NAMES), R.choice(ITEMS)
    top = 10 if d == 1 else 20
    a = R.randint(4, top)
    b = R.randint(1, a - 1)
    ans = a - b
    return finish({"k": "maths", "q": f"{n} had {a} {it} and gave {b} to a friend. How many {it} are left?",
                   "e": f"{a} - {b} = {ans}."}, nopts(ans, [a + b, ans + 1, ans - 1, b]), ans,
                  lambda a=a, b=b: a - b)


def g_after(d):
    top = 50 if d == 1 else 199
    n = R.randint(5, top)
    if d == 1:
        before = R.random() < 0.5
        ans = n - 1 if before else n + 1
        q = f"Which number comes just {'before' if before else 'after'} {n}?"
        e = f"Counting {'back' if before else 'on'} by one from {n} gives {ans}."
    else:
        k = R.choice([2, 10])
        before = R.random() < 0.5
        ans = n - k if before else n + k
        q = f"What is {k} {'less' if before else 'more'} than {n}?"
        e = f"{n} {'-' if before else '+'} {k} = {ans}."
    return finish({"k": "number", "q": q, "e": e},
                  nopts(ans, [n, ans + 1, ans - 1, n + (1 if ans < n else -1)]), ans)


def g_biggest(d):
    big = R.random() < 0.5
    if d == 1:
        nums = R.sample(range(1, 51), 4)
    else:
        digits = R.sample(range(1, 10), 3)
        perms = ["".join(map(str, p)) for p in itertools.permutations(digits)]
        nums = [int(x) for x in R.sample(perms, 4)]
    ans = max(nums) if big else min(nums)
    return finish({"k": "number", "q": f"Which number is the {'biggest' if big else 'smallest'}?",
                   "e": f"Compare the hundreds first, then the tens: {ans} is the {'biggest' if big else 'smallest'}."
                   if d > 1 else f"{ans} is the {'biggest' if big else 'smallest'} of these numbers."},
                  nums, ans)


def series_q(terms, ans, why, mistakes, spread=None, neg=False, kind="series", check=None):
    lin = terms[-1] + (terms[-1] - terms[-2])
    return finish({"k": kind, "q": "What comes next?  " + ", ".join(map(str, terms)) + ", ?", "e": why},
                  nopts(ans, list(mistakes) + [lin], spread, neg), ans, check)


def g_series_small(d):
    if d == 1:
        step = R.choice([1, 2])
        s = R.randint(1, 10)
        back = False
    elif d == 2:
        step = R.choice([2, 3, 5, 10])
        s = R.randint(1, 20)
        back = R.random() < 0.3
    else:
        step = R.randint(3, 9)
        s = R.randint(2, 30)
        back = R.random() < 0.3
    sgn = -1 if back else 1
    if back:
        s += 5 * step + R.randint(0, 5)
    t = [s + sgn * i * step for i in range(5)]
    ans = t[4]
    return series_q(t[:4], ans, f"Each number goes {'down' if back else 'up'} by {step}: {t[3]} {'-' if back else '+'} {step} = {ans}.",
                    [ans + 1, ans - 1, t[3] + sgn * (step + 1), t[3]])


def g_series_geo(d):
    m = 2 if d == 3 else R.choice([3, 4])
    s = R.randint(1, 4 if d == 3 else 3)
    t = [s * m ** i for i in range(5)]
    ans = t[4]
    return series_q(t[:4], ans, f"Each number is multiplied by {m}: {t[3]} × {m} = {ans}.",
                    [t[3] * (m + 1), t[3] + m, ans + m, ans - t[0]])


def g_series_alt(d):
    a, b = R.randint(2, 3 + d), R.randint(1, 1 + d)
    while a == b:
        b = R.randint(1, 1 + d)
    t = [R.randint(1, 12)]
    for i in range(5):
        t.append(t[-1] + (a if i % 2 == 0 else -b))
    ans = t[5]
    return series_q(t[:5], ans, f"The steps alternate +{a}, -{b}. After {t[4]} comes +{a}: {ans}.",
                    [t[4] - b, ans + b, t[4] + a - b, ans - 1])


def g_series_diff(d):
    inc = 1 if d <= 4 else R.choice([1, 2, 3])
    gap = R.randint(1, 4)
    t = [R.randint(1, 15)]
    for _ in range(5):
        t.append(t[-1] + gap)
        gap += inc
    ans = t[5]
    gaps = [t[i + 1] - t[i] for i in range(4)]
    return series_q(t[:5], ans, f"The gaps are {', '.join(map(str, gaps))} - each {inc} more - so the next gap is {ans - t[4]}: {ans}.",
                    [t[4] + gaps[-1], ans + inc, ans - 1, ans + 1])


def g_series_special(d):
    pool = [("squares", lambda i: i * i, "They are square numbers"),
            ("triangular", lambda i: i * (i + 1) // 2, "They are triangular numbers - add 2, then 3, then 4…"),
            ("primes", lambda i: [2, 3, 5, 7, 11, 13, 17, 19, 23, 29, 31, 37, 41][i - 1], "They are the prime numbers in order")]
    if d >= 6:
        pool.append(("cubes", lambda i: i ** 3, "They are cube numbers"))
    name, f, why = R.choice(pool)
    off = R.randint(1, 4) if name != "cubes" else R.randint(1, 2)
    t = [f(off + i) for i in range(6)]
    ans = t[5]
    return series_q(t[:5], ans, f"{why}: next is {ans}.", [ans + 1, ans - 1, ans + 2, t[4] + (t[4] - t[3]) + 1])


def g_series_inter(d):
    if d == 7:
        x, p = R.randint(1, 20), R.randint(2, 6)
        y, q = R.randint(20, 60), -R.randint(2, 6)
        xs = [x + i * p for i in range(4)]
        ys = [y + i * q for i in range(4)]
        why = f"Two series take turns: {xs[0]}, {xs[1]}, {xs[2]}… goes {p:+d} and {ys[0]}, {ys[1]}, {ys[2]}… goes {q:+d}. Next is {xs[3]}."
    else:
        x, p = R.randint(2, 5), 2
        y, q = R.randint(30, 60), -R.randint(3, 7)
        xs = [x * p ** i for i in range(4)]
        ys = [y + i * q for i in range(4)]
        why = f"Two series take turns: {xs[0]}, {xs[1]}, {xs[2]}… doubles and {ys[0]}, {ys[1]}, {ys[2]}… goes {q:+d}. Next is {xs[3]}."
    t = [xs[0], ys[0], xs[1], ys[1], xs[2], ys[2]]
    ans = xs[3]
    return series_q(t, ans, why, [ys[3], ans + abs(p), ys[2] + q - 1, ans - 1], neg=True)


def g_series_altops(d):
    s, add = R.randint(2, 6), R.randint(1, 5)
    t = [s]
    for i in range(6):
        t.append(t[-1] * 2 if i % 2 == 0 else t[-1] + add)
    ans = t[6]
    return series_q(t[:6], ans, f"The rule alternates ×2, +{add}. After {t[5]} comes ×2: {ans}.",
                    [t[5] + add, t[5] * 2 + add, ans - 2, t[5] * 3])


def g_series_multi(d):
    kind = R.choice(["sq1", "prime2", "second", "nn1", "x3m"])
    if kind == "sq1":
        o = R.randint(2, 5)
        t = [(o + i) ** 2 + 1 for i in range(6)]
        why = f"Each is a square plus one: {o + 5}² + 1 = {t[5]}."
    elif kind == "prime2":
        pr = [2, 3, 5, 7, 11, 13, 17, 19, 23]
        o = R.randint(0, 3)
        t = [2 * pr[o + i] for i in range(6)]
        why = f"Each is a prime doubled: 2 × {pr[o + 5]} = {t[5]}."
    elif kind == "second":
        s, g, inc = R.randint(1, 9), R.randint(1, 4), R.choice([2, 3])
        t = [s]
        for _ in range(5):
            t.append(t[-1] + g)
            g += inc
        why = f"The gaps grow by {inc} each time (second differences are {inc}), so the next gap is {t[5] - t[4]}: {t[5]}."
    elif kind == "nn1":
        o = R.randint(1, 4)
        t = [(o + i) * (o + i + 1) for i in range(6)]
        why = f"Each is n × (n+1): {o + 5} × {o + 6} = {t[5]}."
    else:
        s, m = R.randint(2, 4), R.choice([1, 2])
        t = [s]
        for _ in range(5):
            t.append(t[-1] * 3 - m)
        why = f"Each number is ×3 then -{m}: {t[4]} × 3 - {m} = {t[5]}."
    ans = t[5]
    return series_q(t[:5], ans, why, [ans + 1, ans - 1, ans + 2, t[4] * 2], spread=max(3, ans // 10))


def g_series_hard(d):
    kind = R.choice(["cubemn", "primegap", "mulpos", "sqprime", "trib", "dbl"])
    if kind == "cubemn":
        o = R.randint(2, 4)
        t = [(o + i) ** 3 - (o + i) for i in range(6)]
        why = f"Each is n³ - n: {o + 5}³ - {o + 5} = {t[5]}."
        mis = [t[4] + 2 * (t[4] - t[3]) - (t[3] - t[2]), (o + 5) ** 3, t[5] + (o + 5)]
    elif kind == "primegap":
        s = R.randint(1, 20)
        gaps = [2, 3, 5, 7, 11]
        t = [s]
        for g in gaps:
            t.append(t[-1] + g)
        why = f"The gaps are the primes 2, 3, 5, 7, so the next gap is 11: {t[4]} + 11 = {t[5]}."
        mis = [t[4] + 9, t[4] + 10, t[4] + 13]
    elif kind == "mulpos":
        s = R.randint(1, 3)
        t = [s]
        for n in range(1, 6):
            t.append(t[-1] * n + n)
        why = f"Multiply by 1, 2, 3, 4… and add the same number: {t[4]} × 5 + 5 = {t[5]}."
        mis = [t[4] * 5, t[4] * 4 + 4, t[4] * 5 + 4]
    elif kind == "sqprime":
        pr = [2, 3, 5, 7, 11, 13, 17, 19]
        o = R.randint(0, 2)
        t = [pr[o + i] ** 2 for i in range(6)]
        why = f"They are squares of the primes {', '.join(map(str, pr[o:o + 5]))} - next is {pr[o + 5]}² = {t[5]}."
        mis = [(pr[o + 4] + 1) ** 2, (pr[o + 4] + 2) ** 2, t[4] + (t[4] - t[3])]
    elif kind == "trib":
        t = sorted(R.sample(range(1, 6), 3))
        for _ in range(3):
            t.append(t[-1] + t[-2] + t[-3])
        why = f"Each number is the sum of the three before it: {t[2]} + {t[3]} + {t[4]} = {t[5]}."
        mis = [t[4] + t[3], t[4] * 2, t[4] + t[3] + t[2] + 1]
    else:
        s, g = R.randint(1, 9), R.randint(2, 4)
        t = [s]
        for _ in range(5):
            t.append(t[-1] + g)
            g *= 2
        why = f"The gaps double each time, so the next gap is {t[5] - t[4]}: {t[5]}."
        mis = [t[4] + (t[4] - t[3]), t[4] * 2, t[5] + (t[5] - t[4]) // 2]
    ans = t[5]
    return series_q(t[:5], ans, why, mis, spread=max(3, ans // 12))


def letter_opts(ans_i, extra):
    pool = {AB[i] for i in [ans_i + k for k in (-2, -1, 1, 2)] + extra if 0 <= i <= 25}
    pool.discard(AB[ans_i])
    return R.sample(sorted(pool), 3) + [AB[ans_i]]


def g_letters(d):
    if d == 2:
        s = R.randint(0, 20)
        idx = [s + i for i in range(5)]
        why = "The letters go in alphabet order"
    elif d == 3:
        s = R.randint(0, 16)
        idx = [s + 2 * i for i in range(5)]
        why = "Each step skips one letter (+2)"
    elif d == 4:
        k = R.choice([3, -1, -2])
        s = R.randint(0, 13) if k > 0 else R.randint(10, 25)
        idx = [s + k * i for i in range(5)]
        why = f"Each step moves {abs(k)} letter{'s' if abs(k) > 1 else ''} {'forward' if k > 0 else 'back'}"
    elif d in (5, 7):
        s = R.randint(0, 9)
        idx = [s]
        for g in range(1, 5):
            idx.append(idx[-1] + g)
        why = "The jumps grow: +1, +2, +3, +4"
    else:
        s = R.randint(0, 6)
        idx = [s]
        for g in range(2, 6):
            idx.append(idx[-1] + g)
        why = "The jumps grow: +2, +3, +4, +5"
    if d == 6 and R.random() < 0.5:
        s = R.randint(0, 8)
        pairs = [AB[s + i] + AB[25 - s - i] for i in range(4)]
        ans = AB[s + 4] + AB[21 - s]
        wrong = [AB[s + 4] + AB[22 - s], AB[s + 5] + AB[21 - s], AB[21 - s] + AB[s + 4]]
        return finish({"k": "letters", "q": "What comes next?  " + ", ".join(pairs[:4]) + ", ?",
                       "e": f"The first letter moves forward, the second moves back from Z: {ans}."}, wrong + [ans], ans)
    if d == 7:
        a, b = R.randint(0, 6), 25
        seq = []
        for i in range(3):
            seq += [AB[a + 2 * i], AB[b - 2 * i]]
        ans = AB[a + 6]
        wrong = [AB[b - 6], AB[a + 5], AB[a + 7]]
        return finish({"k": "letters", "q": "Which letter comes next?  " + ", ".join(seq) + ", ?",
                       "e": f"Two series take turns: {seq[0]}, {seq[2]}, {seq[4]} go +2, and {seq[1]}, {seq[3]}, {seq[5]} go back 2. Next is {ans}."},
                      wrong + [ans], ans)
    if d == 9:
        s = R.randint(0, 3)
        idx = [s]
        for g in range(2, 6):
            idx.append(idx[-1] + g)
        terms = [f"{AB[i]}{i + 1}" for i in idx]
        ans = terms[4]
        wrong = [f"{AB[idx[4]]}{idx[4]}", f"{AB[idx[4] - 1]}{idx[4]}", f"{AB[idx[4] + 1]}{idx[4] + 2}"]
        return finish({"k": "letters", "q": "What comes next?  " + ", ".join(terms[:4]) + ", ?",
                       "e": f"Each letter jumps +2, +3, +4, +5 and the number is its place in the alphabet: {ans}."},
                      wrong + [ans], ans)
    ans_i = idx[4]
    L = [AB[i] for i in idx]
    return finish({"k": "letters", "q": f"Which letter comes next?  {', '.join(L[:4])}, ?",
                   "e": f"{why}, so next is {L[4]}."}, letter_opts(ans_i, [idx[3] + (idx[3] - idx[2])]), L[4])


CATS = {
    "fruits": ["apple", "mango", "banana", "grapes", "papaya", "guava", "orange"],
    "animals": ["lion", "tiger", "elephant", "horse", "rabbit", "deer", "monkey"],
    "colours": ["red", "blue", "green", "yellow", "purple", "pink", "white"],
    "vegetables": ["potato", "onion", "carrot", "spinach", "cabbage", "brinjal", "peas"],
    "birds": ["parrot", "sparrow", "peacock", "crow", "pigeon", "eagle", "owl"],
    "things you wear": ["shirt", "sock", "cap", "scarf", "jacket", "shoe"],
    "vehicles": ["bus", "car", "train", "bicycle", "truck", "scooter"],
    "kitchen things": ["spoon", "plate", "pan", "bowl", "cup", "ladle"],
}
CATS_HARD = {
    "words that mean happy": ["glad", "cheerful", "joyful", "content", "delighted"],
    "words that mean brave": ["bold", "fearless", "daring", "courageous", "valiant"],
    "words that mean small": ["tiny", "little", "petite", "minute", "compact"],
    "metals": ["iron", "copper", "gold", "silver", "zinc", "aluminium"],
    "gases": ["oxygen", "nitrogen", "hydrogen", "helium", "neon"],
    "units of length": ["metre", "inch", "mile", "yard", "kilometre"],
    "planets": ["Mars", "Venus", "Jupiter", "Saturn", "Mercury", "Neptune"],
}


def g_odd_word(d):
    cats = CATS if d <= 3 else CATS_HARD
    main, other = R.sample(sorted(cats), 2)
    three = R.sample(cats[main], 3)
    odd = R.choice(cats[other])
    return finish({"k": "odd", "q": f"Which one does NOT belong?  {', '.join(sorted(three + [odd]))}",
                   "e": f"{', '.join(three)} are all {main}. {odd} is not."}, three + [odd], odd)


ANALOGIES = [
    (2, "hot", "cold", "up", "down", ["over", "high", "sky"]),
    (2, "cat", "kitten", "dog", "puppy", ["bone", "bark", "cub"]),
    (2, "day", "night", "black", "white", ["dark", "grey", "moon"]),
    (2, "bird", "fly", "fish", "swim", ["water", "fins", "sea"]),
    (2, "hand", "glove", "foot", "sock", ["toe", "leg", "walk"]),
    (3, "cow", "milk", "bee", "honey", ["sting", "flower", "hive"]),
    (3, "pen", "write", "knife", "cut", ["sharp", "kitchen", "steel"]),
    (3, "eye", "see", "ear", "hear", ["sound", "head", "ring"]),
    (3, "doctor", "hospital", "teacher", "school", ["book", "student", "lesson"]),
    (3, "page", "book", "brick", "wall", ["house", "cement", "red"]),
    (4, "tree", "forest", "star", "galaxy", ["sky", "night", "sun"]),
    (4, "chapter", "book", "verse", "poem", ["line", "word", "song"]),
    (4, "thirsty", "drink", "tired", "rest", ["sleepy", "bed", "yawn"]),
    (4, "seed", "plant", "egg", "bird", ["shell", "nest", "yolk"]),
    (4, "painter", "brush", "writer", "pen", ["book", "story", "paper"]),
    (5, "ice", "water", "water", "steam", ["cloud", "rain", "cold"]),
    (5, "finger", "hand", "toe", "foot", ["nail", "leg", "shoe"]),
    (5, "kilometre", "distance", "kilogram", "weight", ["metre", "heavy", "scale"]),
    (6, "calm", "storm", "hope", "despair", ["wish", "joy", "trust"]),
    (6, "brave", "coward", "generous", "selfish", ["kind", "rich", "giving"]),
    (6, "architect", "building", "composer", "symphony", ["piano", "concert", "music"]),
    (7, "drought", "rain", "famine", "food", ["hunger", "crop", "dry"]),
    (7, "patience", "virtue", "greed", "vice", ["money", "desire", "wish"]),
    (7, "fragile", "break", "flexible", "bend", ["soft", "strong", "rubber"]),
    (7, "map", "territory", "menu", "meal", ["restaurant", "list", "waiter"]),
    (7, "symptom", "illness", "smoke", "fire", ["ash", "cloud", "air"]),
]


def g_analogy(d):
    pool = [a for a in ANALOGIES if abs(a[0] - d) <= 1]
    _, a, b, c, ans, wrong = R.choice(pool)
    return finish({"k": "analogy", "q": f"{a.capitalize()} is to {b} as {c} is to ?",
                   "e": f"The link between {a} and {b} is the same as between {c} and {ans}."}, wrong + [ans], ans)


def g_days(d):
    s = R.randrange(7)
    k, what = R.choice([(-1, "yesterday"), (2, "the day after tomorrow"), (3, "in 3 days"), (-2, "the day before yesterday")])
    ans = DAYS[(s + k) % 7]
    return finish({"k": "calendar", "q": f"Today is {DAYS[s]}. What day {'was' if k < 0 else 'will it be'} {what}?",
                   "e": f"Count {abs(k)} day{'s' if abs(k) > 1 else ''} {'back' if k < 0 else 'on'} from {DAYS[s]}: {ans}."},
                  pick(ans, [DAYS[(s - k) % 7], DAYS[(s + k + (1 if k > 0 else -1)) % 7], DAYS[s]], DAYS), ans)


# ------------------------------------------------------------------ levels 3-4: two steps

def g_mult(d):
    n = R.choice(NAMES)
    if d == 3:
        a, b = R.randint(2, 5), R.randint(3, 10)
        ans = a * b
        return finish({"k": "maths", "q": f"{n} buys {b} packets with {a} pencils in each. How many pencils in all?",
                       "e": f"{b} × {a} = {ans}."}, nopts(ans, [a + b, ans - a, ans + a, ans + 1]), ans, lambda a=a, b=b: a * b)
    k, qn = R.randint(3, 9), R.randint(3, 9)
    r = R.randint(1, k - 1)
    total = k * qn + r
    if R.random() < 0.5:
        return finish({"k": "maths", "q": f"{total} sweets are shared equally among {k} children. How many sweets are left over?",
                       "e": f"{k} × {qn} = {k * qn}, and {total} - {k * qn} = {r} left over."},
                      nopts(r, [qn, k - r, r + 1, 0]), r, lambda t=total, k=k: t % k)
    return finish({"k": "maths", "q": f"{total} sweets are shared equally among {k} children. How many does each child get?",
                   "e": f"{k} × {qn} = {k * qn}, which is the most that fits into {total}, so each gets {qn} ({r} left over)."},
                  nopts(qn, [qn + 1, r, qn - 1, k]), qn, lambda t=total, k=k: t // k)


def g_money(d):
    n = R.choice(NAMES)
    k, p = R.randint(2, 6), R.choice([4, 5, 6, 7, 8, 9, 12, 15])
    note = 50 if k * p < 50 else 100
    if k * p >= 100:
        k = 4
    ans = note - k * p
    return finish({"k": "maths", "q": f"{n} buys {k} pens at ₹{p} each and pays with a ₹{note} note. How much change does {n} get (₹)?",
                   "e": f"The pens cost {k} × {p} = ₹{k * p}. Change = {note} - {k * p} = ₹{ans}."},
                  nopts(ans, [note - p, k * p, ans + p, ans - 5]), ans, lambda n_=note, k=k, p=p: n_ - k * p)


def g_months(d):
    s = R.randrange(12)
    k = R.choice([2, 3, 4, -2, -3])
    ans = MONTHS[(s + k) % 12]
    return finish({"k": "calendar", "q": f"Which month comes {abs(k)} months {'after' if k > 0 else 'before'} {MONTHS[s]}?",
                   "e": f"Count {abs(k)} months {'on' if k > 0 else 'back'} from {MONTHS[s]}: {ans}."},
                  pick(ans, [MONTHS[(s + k + 1) % 12], MONTHS[(s + k - 1) % 12], MONTHS[(s - k) % 12]], MONTHS), ans)


def g_time(d):
    h, m = R.randint(1, 11), R.choice(range(5, 60, 5))
    k = R.choice([15, 20, 25, 30, 35, 40, 45, 50])
    while m + k < 60:
        m = R.choice(range(5, 60, 5))
    t = h * 60 + m + k
    f = lambda mins: f"{(mins // 60 - 1) % 12 + 1}:{mins % 60:02d}"
    ans = f(t)
    wrong = [f(h * 60 + (m + k) % 60), f(t + 60), f(t - 10), f(t + 10)]
    return finish({"k": "time", "q": f"A clock shows {h}:{m:02d}. What time will it show {k} minutes later?",
                   "e": f"{60 - m} minutes takes it to {h % 12 + 1}:00, then {k - (60 - m)} more: {ans}."},
                  wrong_from(wrong, ans) + [ans], ans)


def g_code_shift(d):
    shift = 1 if d == 3 else R.choice([1, 2])
    words = ["CAT", "DOG", "SUN", "PEN", "BAT", "CUP", "HAT", "BOX"] if d == 3 else \
            ["BOOK", "TREE", "STAR", "MOON", "CALM", "HOPE", "GROW", "KIND", "LAMP", "FISH", "DESK", "RAIN"]
    w1, w2 = R.sample(words, 2)
    enc = lambda w, s=shift: "".join(AB[(AB.index(c) + s) % 26] for c in w)
    ans = enc(w2)
    wrong = {enc(w2, shift + 1), enc(w2, -shift), enc(w2)[::-1], enc(w2[::-1])}
    wrong.discard(ans)
    return finish({"k": "code", "q": f"In a code, {w1} is written as {enc(w1)}. How is {w2} written?",
                   "e": f"Every letter moves {shift} place{'s' if shift > 1 else ''} forward: {w2} → {ans}."},
                  R.sample(sorted(wrong), 3) + [ans], ans)


def g_order(d):
    k = 3 if d == 3 else 4
    people = R.sample(NAMES, k)
    more, most_w, least_w = R.choice([("taller", "tallest", "shortest"), ("older", "oldest", "youngest"),
                                      ("faster", "fastest", "slowest"), ("heavier", "heaviest", "lightest")])
    facts = [f"{people[i]} is {more} than {people[i + 1]}" for i in range(k - 1)]
    R.shuffle(facts)
    ask_most = R.random() < 0.5
    ans = people[0] if ask_most else people[-1]
    word = most_w if ask_most else least_w
    others = [p for p in people if p != ans]
    if len(others) < 3:
        others.append(R.choice([x for x in NAMES if x not in people]))
    return finish({"k": "logic", "q": ". ".join(facts) + f". Who is the {word}?",
                   "e": f"In order: {' > '.join(people)}. So {ans} is the {word}."}, R.sample(others, 3) + [ans], ans)


def g_odd_number(d):
    if d == 3:
        kind = R.choice(["even", "odd"])
    elif d == 4:
        kind = R.choice(["mult3", "mult4"])
    elif d == 5:
        kind = "square"
    elif d == 6:
        kind = "prime"
    else:
        kind = R.choice(["cube", "digits9"])
    if kind in ("even", "odd"):
        par = 0 if kind == "even" else 1
        good = R.sample([x for x in range(10, 60) if x % 2 == par], 3)
        bad = R.choice([x for x in range(10, 60) if x % 2 != par])
        why = f"are {kind}"
    elif kind in ("mult3", "mult4"):
        m = 3 if kind == "mult3" else 4
        good = [m * k for k in R.sample(range(4, 14), 3)]
        bad = R.choice([x for x in range(14, 56) if x % m and x % 2 == good[0] % 2])
        why = f"are multiples of {m}"
    elif kind == "square":
        good = [k * k for k in R.sample(range(4, 13), 3)]
        bad = R.choice([k * k + R.choice([-1, 1, 2]) for k in range(5, 12)])
        why = "are perfect squares"
    elif kind == "prime":
        good = R.sample([23, 29, 31, 37, 41, 43, 47, 53, 59, 61, 67, 71, 73], 3)
        bad = R.choice([39, 49, 51, 57, 63, 69, 77, 87, 91])
        why = "are prime numbers"
    elif kind == "cube":
        good = [k ** 3 for k in R.sample(range(2, 8), 3)]
        bad = R.choice([36, 100, 144, 81, 121, 196])
        why = "are cube numbers (but not squares)"
        if bad in good:
            bad = 50
    else:
        good = R.sample([x for x in range(100, 999) if sum(map(int, str(x))) == 18 and x % 9 == 0], 3)
        bad = R.choice([x for x in range(100, 999) if sum(map(int, str(x))) == 17])
        why = "have digits that add up to 18"
    nums = good + [bad]
    return finish({"k": "odd", "q": f"Which number is the odd one out?  {', '.join(map(str, sorted(nums)))}",
                   "e": f"{', '.join(map(str, good))} {why}; {bad} is the odd one."}, nums, bad)


GRID_RULES = {
    "sum": (lambda a, b: a + b, "the sum of the first two"),
    "prod": (lambda a, b: a * b, "the first two multiplied"),
    "prod1": (lambda a, b: a * b + 1, "the first two multiplied, plus 1"),
    "dblsum": (lambda a, b: 2 * (a + b), "double the sum of the first two"),
    "sqplus": (lambda a, b: a * a + b, "the first squared, plus the second"),
    "prodplusa": (lambda a, b: a * b + a, "the first two multiplied, plus the first"),
    "prodminus": (lambda a, b: a * b - a - b, "the first two multiplied, minus both"),
    "sumsq": (lambda a, b: a * a + b * b, "the sum of the squares of the first two"),
    "sqminus": (lambda a, b: a * a - b, "the first squared, minus the second"),
    "diffsq": (lambda a, b: (a - b) ** 2, "the difference of the first two, squared"),
    "a2b": (lambda a, b: a + 2 * b, "the first plus double the second"),
}


def g_grid(d):
    target = R.choice({4: ["sum", "a2b"], 6: ["prod", "prod1", "dblsum"], 8: ["sqplus", "prodplusa", "prodminus"],
                       9: ["sumsq", "sqminus", "diffsq"]}[d])
    f, desc = GRID_RULES[target]
    for _ in range(100):
        rows = [(R.randint(2, 9), R.randint(1, 9)) for _ in range(3)]
        # every number different, or "add 12 to the first" could fit as well
        if len({a for a, _ in rows}) < 3 or len({b for _, b in rows}) < 3 or any(a == b for a, b in rows):
            continue
        others = [k for k in GRID_RULES if k != target]
        if any(all(GRID_RULES[k][0](a, b) == f(a, b) for a, b in rows[:2]) for k in others):
            continue
        a, b = rows[2]
        ans = f(a, b)
        if ans <= 0:
            continue
        mis = [GRID_RULES[k][0](a, b) for k in others]
        shown = "   ".join(f"({x}, {y}, {f(x, y)})" for x, y in rows[:2]) + f"   ({a}, {b}, ?)"
        return finish({"k": "number", "q": f"The same rule works in every group. Find the missing number:  {shown}",
                       "e": f"The third number is {desc}: for ({a}, {b}) that is {ans}."},
                      nopts(ans, mis), ans, lambda a=a, b=b, f=f: f(a, b))
    raise RuntimeError("grid")


# ------------------------------------------------------------------ levels 5-6

def g_mixed(d):
    if d == 5:
        a, b, c, e, k = R.randint(2, 20), R.randint(2, 9), R.randint(2, 9), R.randint(2, 5), R.randint(2, 9)
        dd = e * k
        expr, py = f"{a} + {b} × {c} − {dd} ÷ {e}", f"{a} + {b} * {c} - {dd} // {e}"
        ans = a + b * c - k
        lr = ((a + b) * c - dd)
        mis = [lr // e if lr % e == 0 else (a + b) * c - k, a + b * c - dd, (a + b) * c - k, ans + k]
        why = f"Multiply and divide first: {b} × {c} = {b * c} and {dd} ÷ {e} = {k}. Then {a} + {b * c} − {k} = {ans}."
    else:
        a, b, c, dd = R.randint(2, 9), R.randint(2, 9), R.randint(2, 6), R.randint(2, 6)
        expr, py = f"({a} + {b}) × {c} − {dd}²", f"({a} + {b}) * {c} - {dd} ** 2"
        ans = (a + b) * c - dd * dd
        mis = [a + b * c - dd * dd, (a + b) * c - 2 * dd, (a + b) * c + dd * dd, ((a + b) * c - dd) ** 2 if (a + b) * c - dd < 15 else ans + 10]
        why = f"Brackets first: {a} + {b} = {a + b}; then {a + b} × {c} = {(a + b) * c}; {dd}² = {dd * dd}; so {(a + b) * c} − {dd * dd} = {ans}."
    return finish({"k": "maths", "q": f"Work it out:  {expr} = ?", "e": why},
                  nopts(ans, mis, neg=ans < 0), ans, lambda py=py: eval(py))


def g_fraction(d):
    n = R.choice(NAMES)
    if d == 5:
        den = R.choice([3, 4, 5, 6, 8])
        num = R.randint(2, den - 1)
        while math.gcd(num, den) != 1:
            num = R.randint(2, den - 1)
        M = den * R.randint(3, 12)
        ans = M * num // den
        return finish({"k": "maths", "q": f"What is {num}/{den} of {M}?",
                       "e": f"{M} ÷ {den} = {M // den}, and {M // den} × {num} = {ans}."},
                      nopts(ans, [M // den, M - ans, M // num if M % num == 0 else ans + M // den, ans + 1]), ans,
                      lambda M=M, num=num, den=den: Fraction(M) * num / den)
    a, b = R.choice([(2, 3), (3, 4), (4, 5), (3, 2), (5, 4), (2, 5), (4, 3)])
    M = a * b * R.randint(4, 15) * (5 if R.random() < 0.5 else 1)
    after1 = M - M // a
    ans = after1 - after1 // b
    naive = M - M // a - M // b
    return finish({"k": "maths", "q": f"{n} had ₹{M}. {pron(n)} spent 1/{a} of it on books, then 1/{b} of what was left on lunch. How much is left (₹)?",
                   "e": f"After books: {M} − {M // a} = {after1}. Lunch: 1/{b} of {after1} = {after1 // b}. Left: {after1} − {after1 // b} = ₹{ans}."},
                  nopts(ans, [naive, after1, after1 // b, M // a]), ans,
                  lambda M=M, a=a, b=b: Fraction(M) * (1 - Fraction(1, a)) * (1 - Fraction(1, b)))


def pct_opts(ans, mis):
    return [f"{fmt(x)}%" for x in nopts(ans, mis)]


def g_percent(d):
    if d == 5:
        price, pct = R.choice([200, 400, 500, 800, 1000, 1200, 1500]), R.choice([10, 20, 25, 30, 50])
        disc = price * pct // 100
        ans = price - disc
        return finish({"k": "maths", "q": f"A ₹{price} dress has a {pct}% discount. What is the new price (₹)?",
                       "e": f"{pct}% of {price} is {disc}. {price} − {disc} = ₹{ans}."},
                      nopts(ans, [disc, price - pct, price + disc, ans + 10]), ans)
    if d == 6:
        a, p = R.choice([40, 50, 60, 80, 120, 200, 250, 400]), R.choice([10, 20, 25, 40, 50])
        b = a * (100 + p) // 100
        wrongbase = Fraction(b - a, b) * 100
        mis = [b - a, p // 2, p + 5]
        if wrongbase.denominator == 1:
            mis.append(int(wrongbase))
        return finish({"k": "maths", "q": f"The price of a book goes up from ₹{a} to ₹{b}. By what percent did it go up?",
                       "e": f"It rose by ₹{b - a}. Compare with the old price: {b - a} ÷ {a} × 100 = {p}%."},
                      pct_opts(p, mis), f"{p}%", lambda a=a, b=b: f"{fmt(Fraction(b - a, a) * 100)}%")
    if d == 7:
        c, p = R.choice([200, 400, 500, 800, 1000, 1250]), R.choice([10, 20, 25, 40, 50])
        s = c * (100 + p) // 100
        mis = [s - c, p + 5, p - 5]
        alt = Fraction(s - c, s) * 100
        if alt.denominator == 1:
            mis.append(int(alt))
        return finish({"k": "maths", "q": f"A shopkeeper buys a lamp for ₹{c} and sells it for ₹{s}. What is the profit percent?",
                       "e": f"Profit = ₹{s - c}. Profit % is on the cost price: {s - c} ÷ {c} × 100 = {p}%."},
                      pct_opts(p, mis), f"{p}%", lambda c=c, s=s: f"{fmt(Fraction(s - c, c) * 100)}%")
    if d == 8:
        if R.random() < 0.5:
            p = R.choice([10, 20, 30, 40, 50])
            x = Fraction(p * p, 100)
            first = R.choice(["rises", "falls"])
            ans = f"{fmt(x)}% decrease"
            opts = ["No change", f"{fmt(x)}% increase", ans, f"{fmt(2 * x)}% decrease"]
            return finish({"k": "maths", "q": f"A price {first} by {p}% and then {'falls' if first == 'rises' else 'rises'} by {p}%. What is the overall change?",
                           "e": f"Take ₹100: it becomes {100 + p if first == 'rises' else 100 - p}, then {fmt(Fraction(100 + p) * (100 - p) / 100)}. That is a {fmt(x)}% decrease, not 'no change'."},
                          opts, ans, lambda p=p: f"{fmt(Fraction(p * p, 100))}% decrease")
        a, b = R.choice([(20, 10), (25, 20), (50, 20), (10, 20), (20, 25), (40, 25)])
        net = Fraction(100 + a) * (100 - b) / 100 - 100
        word = "increase" if net > 0 else "decrease"
        ans = f"{fmt(abs(net))}% {word}" if net else "No change"
        naive = a - b
        opts = {ans, f"{abs(naive)}% {'increase' if naive > 0 else 'decrease'}" if naive else "No change"}
        for cand in [f"{fmt(abs(net) + 2)}% {word}", f"{fmt(abs(net))}% {'decrease' if word == 'increase' else 'increase'}", "No change", f"{a + b}% {word}"]:
            if len(opts) < 4:
                opts.add(cand)
        return finish({"k": "maths", "q": f"A salary rises by {a}% and then falls by {b}%. What is the overall change?",
                       "e": f"Take ₹100: +{a}% gives {100 + a}, then −{b}% gives {fmt(Fraction(100 + a) * (100 - b) / 100)}. That is {ans.lower()}."},
                      list(opts), ans)
    P, r = R.choice([(1000, 10), (2000, 10), (5000, 10), (1000, 20), (2500, 20), (4000, 5), (8000, 5), (10000, 10), (5000, 20)])
    ci = P * ((100 + r) ** 2 - 10000) // 10000
    si = 2 * P * r // 100
    return finish({"k": "maths", "q": f"₹{P} is invested at {r}% a year, compound interest, for 2 years. How much interest does it earn (₹)?",
                   "e": f"Year 1: {P} → {P * (100 + r) // 100}. Year 2: {r}% of that is {P * (100 + r) * r // 10000}. Interest = ₹{ci} (simple interest would be only ₹{si})."},
                  nopts(ci, [si, P + ci, P * r // 100, ci + P * r // 100]), ci,
                  lambda P=P, r=r: Fraction(P) * Fraction(100 + r, 100) ** 2 - P)


def g_area(d):
    l, w = R.randint(5, 20), R.randint(3, 12)
    if l == w:
        l += 1
    if R.random() < 0.5:
        ans = 2 * (l + w)
        return finish({"k": "maths", "q": f"A garden is {l} m long and {w} m wide. How many metres of fence go all the way round it?",
                       "e": f"Perimeter = 2 × ({l} + {w}) = {ans} m."}, nopts(ans, [l * w, l + w, 2 * l + w]), ans)
    ans = l * w
    return finish({"k": "maths", "q": f"A room is {l} m long and {w} m wide. What is its floor area in square metres?",
                   "e": f"Area = {l} × {w} = {ans} square metres."}, nopts(ans, [2 * (l + w), l + w, ans + l]), ans)


DIRS8 = ["north", "north-east", "east", "south-east", "south", "south-west", "west", "north-west"]
VEC = {"north": (0, 1), "east": (1, 0), "south": (0, -1), "west": (-1, 0)}


def dir_of(dx, dy):
    """the compass quarter, as these puzzles mean it: any mix of north and west is north-west"""
    ns = "north" if dy > 0 else "south" if dy < 0 else ""
    ew = "east" if dx > 0 else "west" if dx < 0 else ""
    return f"{ns}-{ew}" if ns and ew else ns or ew


def g_direction(d):
    n = R.choice(NAMES)
    if d == 5:
        start = R.choice(list(VEC))
        turn = R.choice(["left", "right"])
        a, b = R.randint(2, 9), R.randint(2, 9)
        i = DIRS8.index(start)
        second = DIRS8[(i + (2 if turn == "right" else -2)) % 8]
        dx = VEC[start][0] * a + VEC[second][0] * b
        dy = VEC[start][1] * a + VEC[second][1] * b
        ans = dir_of(dx, dy)
        j = DIRS8.index(ans)
        return finish({"k": "direction", "q": f"{n} walks {a} km {start}, turns {turn} and walks {b} km. In which direction is {n} now from the starting point?",
                       "e": f"Turning {turn} from {start} means walking {second}. {start.capitalize()} then {second} puts {n} to the {ans} of the start."},
                      pick(ans, [DIRS8[(j + 4) % 8], DIRS8[(j + 2) % 8], DIRS8[(j - 2) % 8]], DIRS8), ans,
                      lambda dx=dx, dy=dy: dir_of(dx, dy))
    if d == 6:
        x, y, h = R.choice([(3, 4, 5), (6, 8, 10), (5, 12, 13), (8, 6, 10), (9, 12, 15), (4, 3, 5), (12, 5, 13)])
        e = R.randint(2, 6)
        east = R.choice(["east", "west"])
        legs = [(y + e, "north"), (x, east), (e, "south")]
        path = sum(l for l, _ in legs)
        sim = [0, 0]
        for l, dname in legs:
            sim[0] += VEC[dname][0] * l
            sim[1] += VEC[dname][1] * l
        return finish({"k": "direction", "q": f"{n} walks {y + e} km north, then {x} km {east}, then {e} km south. How far is {n} from the starting point (km)?",
                       "e": f"Net: {y} km north and {x} km {east}. Distance = √({y}² + {x}²) = {h} km."},
                      nopts(h, [path, x + y, abs(y + e - x), h + 1]), h,
                      lambda s=tuple(sim): math.hypot(*s))
    start = R.choice(list(VEC))
    turns = [(R.choice([45, 90, 135]), R.choice(["clockwise", "anticlockwise"])) for _ in range(3)]
    turns[R.randrange(3)] = (R.choice([90, 135, 180]), R.choice(["clockwise", "anticlockwise"]))
    i = DIRS8.index(start)
    for deg, way in turns:
        i += (deg // 45) * (1 if way == "clockwise" else -1)
    ans = DIRS8[i % 8]
    j = DIRS8.index(ans)
    text = ", then ".join(f"{deg}° {way}" if deg != 180 else "180°" for deg, way in turns)
    return finish({"k": "direction", "q": f"{n} faces {start}. {pron(n)} turns {text}. Which way does {n} face now?",
                   "e": f"Clockwise is +, anticlockwise is −: {' '.join(('+' if w == 'clockwise' else '−') + str(g) for g, w in turns)} = {sum(g if w == 'clockwise' else -g for g, w in turns):+d}°. From {start} that ends at {ans}."},
                  pick(ans, [DIRS8[(j + 4) % 8], DIRS8[(j + 1) % 8], DIRS8[(j - 2) % 8]], DIRS8), ans)


BLOOD_SIMPLE = [  # (phrase, answer, wrong, relative's gender, speaker gender or None)
    ("my mother's brother", "Uncle", ["Cousin", "Grandfather", "Brother"], "m", None),
    ("my father's father", "Grandfather", ["Uncle", "Father", "Great-grandfather"], "m", None),
    ("my mother's sister", "Aunt", ["Mother", "Cousin", "Grandmother"], "f", None),
    ("my father's brother's son", "Cousin", ["Brother", "Nephew", "Uncle"], "m", None),
    ("my brother's daughter", "Niece", ["Daughter", "Cousin", "Sister"], "f", None),
    ("my sister's son", "Nephew", ["Son", "Cousin", "Brother"], "m", None),
    ("my son's son", "Grandson", ["Son", "Nephew", "Cousin"], "m", None),
    ("my husband's mother", "Mother-in-law", ["Mother", "Aunt", "Sister-in-law"], "f", "f"),
    ("my brother's wife", "Sister-in-law", ["Sister", "Cousin", "Aunt"], "f", None),
    ("my daughter's husband", "Son-in-law", ["Son", "Nephew", "Brother-in-law"], "m", None),
    ("my wife's brother", "Brother-in-law", ["Brother", "Cousin", "Son-in-law"], "m", "m"),
    ("my father's sister's husband", "Uncle", ["Brother-in-law", "Cousin", "Grandfather"], "m", None),
    ("my mother's father's only daughter", "Mother", ["Aunt", "Grandmother", "Sister"], "f", None),
    ("the son of my father's only son", "Son", ["Nephew", "Brother", "Cousin"], "m", "m"),
]


def g_blood(d):
    phrase, ans, wrong, g, sg = R.choice(BLOOD_SIMPLE if d == 5 else BLOOD_SIMPLE[3:])
    sp = R.choice(NAMES_F if sg == "f" else NAMES_M if sg == "m" else NAMES)
    who = "man" if g == "m" else "woman"
    pr = "He" if g == "m" else "She"
    tail = " (Only one son: who is that?)" if "only son" in phrase else ""
    return finish({"k": "relations", "q": f"Pointing to a {who}, {sp} says, \"{pr} is {phrase}.\" How is the {who} related to {sp}?",
                   "e": f"{phrase[3:].capitalize() if phrase.startswith('my ') else phrase.capitalize()} - that is {sp}'s {ans.lower()}.{tail}".replace(' (Only one son: who is that?)', f' {sp}\'s father\'s only son is {sp}.')},
                  wrong + [ans], ans)


def g_rank(d):
    n = R.choice(NAMES)
    L, Rr = R.randint(4, 20), R.randint(4, 20)
    ans = L + Rr - 1
    return finish({"k": "logic", "q": f"In a row of children, {n} is {nth(L)} from the left and {nth(Rr)} from the right. How many children are in the row?",
                   "e": f"{L} + {Rr} counts {n} twice, so {L} + {Rr} − 1 = {ans}."},
                  nopts(ans, [L + Rr, L + Rr - 2, L + Rr + 1]), ans)


def g_average(d):
    k = R.randint(4, 6)
    avg = R.randint(12, 40)
    nums = [R.randint(avg - 10, avg + 10) for _ in range(k - 1)]
    x = avg * k - sum(nums)
    if x <= 0:
        x = avg
        nums[0] = avg * k - sum(nums[1:]) - x
    shown = ", ".join(map(str, nums))
    return finish({"k": "maths", "q": f"The average of {k} numbers is {avg}. {k - 1} of them are {shown}. What is the last number?",
                "e": f"The total must be {k} × {avg} = {avg * k}. {avg * k} − {sum(nums)} = {x}."},
               nopts(x, [avg, avg * (k - 1) - sum(nums) if avg * (k - 1) > sum(nums) else x + k, x + avg // 2, x - k]), x,
               lambda avg=avg, k=k, s=sum(nums): avg * k - s)


def g_numcode(d):
    words = ["CAT", "DOG", "SUN", "BED", "CUP", "HEN", "PIN", "FAN", "TOY", "JAM", "MAP", "BUS"]
    w1, w2 = R.sample(words, 2)
    val = lambda w: sum(AB.index(c) + 1 for c in w)
    rev = lambda w: sum(26 - AB.index(c) for c in w)
    ans = val(w2)
    return finish({"k": "code", "q": f"If A = 1, B = 2 … Z = 26 and {w1} = {val(w1)}, what is {w2}?",
                   "e": f"Add the letter places: {' + '.join(str(AB.index(c) + 1) for c in w2)} = {ans}."},
                  nopts(ans, [rev(w2), ans + 1, ans - 1, ans + 2]), ans, lambda w2=w2: val(w2))


def g_cal_after(d):
    s, k = R.randrange(7), R.randint(20, 100)
    ans = DAYS[(s + k) % 7]
    return finish({"k": "calendar", "q": f"If today is {DAYS[s]}, what day will it be after {k} days?",
                   "e": f"Days repeat every 7. {k} = 7 × {k // 7} + {k % 7}, so count {k % 7} day{'s' if k % 7 != 1 else ''} on from {DAYS[s]}: {ans}."},
                  pick(ans, [DAYS[(s + k + 1) % 7], DAYS[(s + k - 1) % 7], DAYS[(s + k // 7) % 7]], DAYS), ans)


NUM_RULES = {
    "sq": (lambda n: n * n, "n × n"), "dbl1": (lambda n: 2 * n + 1, "2n + 1"), "tri": (lambda n: 3 * n, "3n"),
    "cube": (lambda n: n ** 3, "n × n × n"), "sq1": (lambda n: n * n + 1, "n² + 1"), "tri1": (lambda n: 3 * n + 1, "3n + 1"),
    "sqm1": (lambda n: n * n - 1, "n² − 1"), "nn1": (lambda n: n * (n + 1), "n × (n + 1)"), "pow2": (lambda n: 2 ** n, "2 to the power n"),
    "cubemn": (lambda n: n ** 3 - n, "n³ − n"), "sqn": (lambda n: n * n + n + 1, "n² + n + 1"),
}


def g_num_analogy(d):
    target = R.choice({5: ["sq", "dbl1", "tri"], 6: ["cube", "sq1", "tri1"], 7: ["sqm1", "nn1", "sq1"],
                       8: ["pow2", "nn1", "sqn"], 9: ["cubemn", "sqn", "pow2"]}[d])
    f, desc = NUM_RULES[target]
    for _ in range(100):
        a, b = R.sample(range(3, 10 if target != "pow2" else 9), 2)
        others = [k for k in NUM_RULES if k != target]
        if any(NUM_RULES[k][0](a) == f(a) for k in others):
            continue
        ans = f(b)
        mis = [NUM_RULES[k][0](b) for k in others]
        return finish({"k": "number", "q": f"{a} is to {f(a)} as {b} is to ?",
                       "e": f"The rule is {desc}: {a} → {f(a)}, so {b} → {ans}."}, nopts(ans, mis), ans, lambda b=b, f=f: f(b))
    raise RuntimeError("num analogy")


# ------------------------------------------------------------------ levels 7-8

def g_ratio(d):
    n = R.choice(NAMES)
    if d == 7:
        if R.random() < 0.5:
            a, b = R.sample(range(2, 8), 2)
            total = (a + b) * R.randint(5, 30)
            ans = total * a // (a + b)
            return finish({"k": "maths", "q": f"₹{total} is shared between {n} and a friend in the ratio {a}:{b}. How much does {n} get (₹)?",
                           "e": f"{a} + {b} = {a + b} parts, one part = {total // (a + b)}. {n} gets {a} parts = ₹{ans}."},
                          nopts(ans, [total * b // (a + b), total // a, total // (a + b), total - total // (a + b)]), ans,
                          lambda t=total, a=a, b=b: Fraction(t * a, a + b))
        a, b = R.sample(range(2, 9), 2)
        k = R.randint(3, 9)
        ans = b * k
        return finish({"k": "maths", "q": f"In a class the ratio of boys to girls is {a}:{b}. There are {a * k} boys. How many girls are there?",
                       "e": f"{a * k} boys = {a} parts, so one part = {k}. Girls = {b} × {k} = {ans}."},
                      nopts(ans, [a * k + b, (a + b) * k, b * a, ans + k]), ans)
    a, b = R.randint(1, 5), R.randint(2, 7)
    c, dd = R.randint(2, 7), R.randint(2, 7)
    if math.gcd(a, b) != 1 or math.gcd(c, dd) != 1 or a == b or c == dd:
        return g_ratio(d)
    red = lambda x, y: f"{x // math.gcd(x, y)}:{y // math.gcd(x, y)}"
    ans = red(a * c, b * dd)
    cands = [red(a, dd), red(a * dd, b * c), red(a + c, b + dd), red(a * c + 1, b * dd), red(b * dd, a * c)]
    wrong = [w for w in dict.fromkeys(cands) if w != ans][:3]
    while len(wrong) < 3:
        w = red(R.randint(1, 20), R.randint(1, 20))
        if w != ans and w not in wrong:
            wrong.append(w)
    return finish({"k": "maths", "q": f"A : B = {a} : {b} and B : C = {c} : {dd}. What is A : C?",
                   "e": f"Make B the same in both: A:B = {a * c}:{b * c} and B:C = {b * c}:{b * dd}. So A:C = {a * c}:{b * dd} = {ans}."},
                  wrong + [ans], ans, lambda a=a, b=b, c=c, dd=dd: red(a * c, b * dd))


def hm(mins):
    h, m = divmod(mins, 60)
    return f"{h} h {m:02d} min" if h else f"{m} min"


def g_speed(d):
    if d == 7:
        if R.random() < 0.5:
            v = R.choice([40, 48, 50, 60, 72, 80])
            mins = R.choice([90, 150, 75, 105, 135, 45, 210, 165])
            dist = v * mins // 60
            if v * mins % 60:
                return g_speed(d)
            ans = hm(mins)
            dec = Fraction(mins, 60)
            wrong = {f"{int(dec)} h {int(round((dec - int(dec)) * 100)):02d} min", hm(mins + 15), hm(mins - 15), hm(mins + 30)}
            wrong.discard(ans)
            return finish({"k": "speed", "q": f"A car covers {dist} km at {v} km per hour. How long does the journey take?",
                           "e": f"Time = {dist} ÷ {v} = {fmt(dec) if dec.denominator != 1 else int(dec)} hours = {ans}."},
                          R.sample(sorted(wrong), 3) + [ans], ans, lambda dist=dist, v=v: hm(dist * 60 // v))
        kmh, ms = R.choice([(36, 10), (54, 15), (72, 20), (90, 25), (108, 30)])
        t = R.randint(6, 20)
        L = ms * t
        return finish({"k": "speed", "q": f"A train {L} m long runs at {kmh} km per hour. How many seconds does it take to pass a pole?",
                       "e": f"{kmh} km/h = {kmh} × 5/18 = {ms} m/s. Time = {L} ÷ {ms} = {t} seconds."},
                      nopts(t, [t * 2, t + 5, round(L / kmh) if round(L / kmh) != t else t + 3]), t,
                      lambda L=L, kmh=kmh: Fraction(L) / (Fraction(kmh) * 1000 / 3600))
    if d == 8:
        if R.random() < 0.5:
            x, y = R.choice([(40, 60), (30, 60), (20, 30), (60, 90), (45, 90), (30, 70), (36, 45), (48, 80)])
            ans = 2 * x * y // (x + y)
            return finish({"k": "speed", "q": f"A bus goes from A to B at {x} km/h and comes back the same way at {y} km/h. What is its average speed for the whole trip (km/h)?",
                           "e": f"Average speed = total distance ÷ total time = 2 × {x} × {y} ÷ ({x} + {y}) = {ans} km/h - not the simple average {(x + y) // 2}."},
                          nopts(ans, [(x + y) // 2, y - x, ans + 2]), ans,
                          lambda x=x, y=y: Fraction(2) / (Fraction(1, x) + Fraction(1, y)))
        (k1, m1), (k2, m2) = R.sample([(36, 10), (54, 15), (72, 20), (90, 25)], 2)
        t = R.randint(6, 15)
        L1 = R.randint(5, 20) * 10
        L2 = (m1 + m2) * t - L1
        if L2 <= 50:
            return g_speed(d)
        return finish({"k": "speed", "q": f"Two trains, {L1} m and {L2} m long, run towards each other at {k1} km/h and {k2} km/h. How many seconds do they take to cross each other?",
                       "e": f"Speeds add when they meet: {m1} + {m2} = {m1 + m2} m/s. Distance = {L1} + {L2} = {L1 + L2} m. Time = {t} s."},
                      nopts(t, [Fraction(L1 + L2, abs(m1 - m2)) if (L1 + L2) % abs(m1 - m2) == 0 else t * 2, Fraction(L1, m1 + m2) if L1 % (m1 + m2) == 0 else t - 3, t + 4]), t,
                      lambda L=L1 + L2, s=m1 + m2: Fraction(L, s))
    b, s = R.randint(8, 20), R.randint(2, 5)
    dist = (b + s) * (b - s) * R.choice([1, 2])
    td, tu = Fraction(dist, b + s), Fraction(dist, b - s)
    if td.denominator != 1 or tu.denominator != 1:
        return g_speed(d)
    return finish({"k": "speed", "q": f"A boat goes {dist} km downstream in {td} hours and the same {dist} km upstream in {tu} hours. What is the speed of the stream (km/h)?",
                   "e": f"Downstream {b + s} km/h, upstream {b - s} km/h. Stream = ({b + s} − {b - s}) ÷ 2 = {s} km/h."},
                  nopts(s, [b, 2 * s, b + s, b - s]), s,
                  lambda dist=dist, td=td, tu=tu: (Fraction(dist) / td - Fraction(dist) / tu) / 2)


def clock_angle(h, m):
    a = abs(Fraction(30 * (h % 12)) + Fraction(m, 2) - 6 * m)
    return min(a, 360 - a)


def g_clock(d):
    if d == 7:
        h, m = R.randint(1, 12), R.choice([0, 30])
    elif d == 8:
        h, m = R.randint(1, 12), R.choice(range(5, 60, 5))
    else:
        h, m = R.randint(1, 12), R.choice([x for x in range(1, 60) if x % 5])
    ans = clock_angle(h, m)
    naive = abs(30 * (h % 12) - 6 * m)
    naive = min(naive, 360 - naive)
    mis = [naive, ans + 15, ans + Fraction(m, 2) if m else ans + 30, abs(ans - 30)]
    deg = lambda x: f"{fmt(x)}°"
    opts = [deg(x) for x in nopts(ans, mis, spread=20)]
    return finish({"k": "clock", "q": f"What is the smaller angle between the hour and minute hands at {h}:{m:02d}?",
                   "e": f"Minute hand: {m} × 6 = {6 * m}°. Hour hand: {h % 12} × 30 + {m} × ½ = {fmt(Fraction(30 * (h % 12)) + Fraction(m, 2))}°. The gap is {fmt(ans)}°."},
                  opts, deg(ans), lambda h=h, m=m: deg(sim_clock(h, m)))


def sim_clock(h, m):
    """independent: move both hands one minute at a time from 12:00"""
    hour, minute = Fraction(0), Fraction(0)
    for _ in range((h % 12) * 60 + m):
        hour += Fraction(1, 2)
        minute = (minute + 6) % 360
    a = abs(hour - minute) % 360
    return min(a, 360 - a)


def g_cal_date(d):
    a = R.randint(1, 12)
    b = R.randint(13, 30)
    s = R.randrange(7)
    if R.random() < 0.5:
        a, b = b, a
    ans = DAYS[(s + b - a) % 7]
    way = "on" if b > a else "back"
    return finish({"k": "calendar", "q": f"The {nth(a)} of a month is a {DAYS[s]}. What day of the week is the {nth(b)} of the same month?",
                   "e": f"Going {way} {abs(b - a)} days is {abs(b - a) // 7} whole weeks and {abs(b - a) % 7} more, so {ans}."},
                  pick(ans, [DAYS[(s + b - a + 1) % 7], DAYS[(s + b - a - 1) % 7], DAYS[(s - (b - a)) % 7]], DAYS), ans,
                  lambda a=a, b=b, s=s: DAYS[(s + b - a) % 7])


def g_cal_year(d):
    s = R.randrange(7)
    kind = R.choice(["mar", "dec31", "nextyear"])
    leap = R.random() < 0.5
    yr = "a leap year" if leap else "an ordinary (non-leap) year"
    if kind == "mar":
        days = 31 + (29 if leap else 28)
        ans = DAYS[(s + days) % 7]
        q = f"In {yr}, 1 January is a {DAYS[s]}. What day is 1 March?"
        e = f"January has 31 days and February {29 if leap else 28}: {days} days on, which is {days % 7} extra days - {ans}."
        wrong = [DAYS[(s + days + (-1 if leap else 1)) % 7], DAYS[(s + 2) % 7] if (s + 2) % 7 != (s + days) % 7 else DAYS[(s + 5) % 7], DAYS[s]]
    elif kind == "dec31":
        days = 365 if not leap else 366
        ans = DAYS[(s + days - 1) % 7]
        q = f"In {yr}, 1 January is a {DAYS[s]}. What day is 31 December of the same year?"
        e = f"31 December is day {days}, which is {days - 1} days after 1 January = {(days - 1) // 7} weeks and {(days - 1) % 7} day{'s' if (days - 1) % 7 != 1 else ''}: {ans}."
        wrong = [DAYS[(s + days) % 7], DAYS[(s + days + 1) % 7], DAYS[(s + days - 2) % 7]]
    else:
        days = 366 if leap else 365
        ans = DAYS[(s + days) % 7]
        q = f"1 January of {yr} is a {DAYS[s]}. What day is 1 January of the next year?"
        e = f"{days} days = 52 weeks and {days - 364} day{'s' if days - 364 > 1 else ''}, so it moves on by {days - 364}: {ans}."
        wrong = [DAYS[s], DAYS[(s + days + (1 if not leap else -1)) % 7], DAYS[(s - 1) % 7]]
    return finish({"k": "calendar", "q": q, "e": e}, pick(ans, wrong, DAYS), ans)


def g_cal_real(d):
    y = R.randint(2026, 2029)
    mo, dd = R.choice([(1, 26), (8, 15), (10, 2), (11, 14), (3, 8), (6, 21), (12, 25)])
    gap = R.randint(1, 3)
    d1 = datetime.date(y, mo, dd)
    d2 = datetime.date(y + gap, mo, dd)
    ans = DAYS[d2.weekday()]
    s = d1.weekday()
    leaps = (d2 - d1).days - 365 * gap
    return finish({"k": "calendar", "q": f"{dd} {MONTHS[mo - 1]} {y} is a {DAYS[s]}. What day of the week is {dd} {MONTHS[mo - 1]} {y + gap}?",
                   "e": f"Each ordinary year moves the day on by 1 and a year crossing 29 February by 2: {gap} + {leaps} = {gap + leaps} days on, so {ans}."},
                  pick(ans, [DAYS[(s + gap) % 7], DAYS[(s + gap + leaps + 1) % 7], DAYS[(s - gap) % 7]], DAYS), ans,
                  lambda d2=d2: DAYS[d2.weekday()])


def g_code_rev(d):
    words = ["CALM", "HOPE", "LAMP", "DESK", "FISH", "RAIN", "BOLD", "KIND", "GROW", "STAR", "MILK", "WIND"]
    w1, w2 = R.sample(words, 2)
    if d == 7:
        enc = lambda w: "".join(AB[(AB.index(c) + 1) % 26] for c in w[::-1])
        ans = enc(w2)
        wrong = ["".join(AB[(AB.index(c) + 1) % 26] for c in w2), w2[::-1], "".join(AB[(AB.index(c) - 1) % 26] for c in w2[::-1])]
        e = f"The word is written backwards and every letter moves 1 forward: {w2} → {w2[::-1]} → {ans}."
    elif d == 8:
        enc = lambda w: "".join(AB[25 - AB.index(c)] for c in w)
        ans = enc(w2)
        wrong = [ans[::-1], "".join(AB[(AB.index(c) + 1) % 26] for c in w2), "".join(AB[(25 - AB.index(c) + 1) % 26] for c in w2)]
        e = f"Each letter swaps with its mirror in the alphabet (A↔Z, B↔Y, C↔X…): {w2} → {ans}."
    else:
        enc = lambda w: "".join(AB[(AB.index(c) + i + 1) % 26] for i, c in enumerate(w))
        ans = enc(w2)
        wrong = ["".join(AB[(AB.index(c) + 1) % 26] for c in w2), "".join(AB[(AB.index(c) + 4 - i) % 26] for i, c in enumerate(w2)),
                 "".join(AB[(AB.index(c) + 2) % 26] for c in w2)]
        e = f"The 1st letter moves 1 on, the 2nd 2 on, the 3rd 3 on, the 4th 4 on: {w2} → {ans}."
    wrong = [w for w in dict.fromkeys(wrong) if w != ans]
    if len(wrong) < 3:
        return g_code_rev(d)
    return finish({"k": "code", "q": f"In a code, {w1} is written as {enc(w1)}. How is {w2} written?", "e": e}, wrong[:3] + [ans], ans,
                  lambda w2=w2, enc=enc: enc(w2))


TERMS = ["zibs", "mops", "tals", "wugs", "kels", "daxes", "fems", "plons", "gorps", "rins", "blicks", "toves"]


def syl_text(form, x, y):
    return {"all": f"All {x} are {y}.", "no": f"No {x} are {y}.", "some": f"Some {x} are {y}.", "somenot": f"Some {x} are not {y}."}[form]


def syl_true(form, x, y, regions):
    if form == "all":
        return all(r[y] for r in regions if r[x])
    if form == "no":
        return not any(r[x] and r[y] for r in regions)
    if form == "some":
        return any(r[x] and r[y] for r in regions)
    return any(r[x] and not r[y] for r in regions)


def syl_models():
    kinds = [k for k in itertools.product([0, 1], repeat=3) if any(k)]
    for mask in range(1, 2 ** len(kinds)):
        regions = [kinds[i] for i in range(len(kinds)) if mask >> i & 1]
        if all(any(r[t] for r in regions) for t in range(3)):
            yield regions


MODELS = list(syl_models())
CONCL = [("all", 0, 2), ("all", 2, 0), ("no", 0, 2), ("some", 0, 2), ("somenot", 0, 2), ("somenot", 2, 0)]


def syl_follows(prem):
    ok = [m for m in MODELS if all(syl_true(f, x, y, m) for f, x, y in prem)]
    if not ok:
        return None
    return [c for c in CONCL if all(syl_true(c[0], c[1], c[2], m) for m in ok)]


def g_syllogism(d):
    names = R.sample(TERMS, 3)
    for _ in range(200):
        prem = [(R.choice(["all", "all", "no", "some", "somenot"]),) + tuple(R.sample([0, 1], 2)),
                (R.choice(["all", "all", "no", "some"]),) + tuple(R.sample([1, 2], 2))]
        F = syl_follows(prem)
        if F is None:
            continue
        NF = [c for c in CONCL if c not in F]
        if not F and d < 8:
            continue
        if F and R.random() < 0.25 and d >= 8:
            continue
        if len(NF) < 3:
            continue
        txt = lambda c: syl_text(c[0], names[c[1]], names[c[2]])
        if F:
            ans_c = R.choice(F)
            ans = txt(ans_c)
            opts = [txt(c) for c in R.sample(NF, 3)] + [ans]
            e = f"Only \"{ans}\" is true in every situation that fits both statements; each of the others can be false."
        else:
            ans = "None of these follows for sure"
            opts = [txt(c) for c in R.sample(NF, 3)] + [ans]
            e = "Each of the three can be false while both statements are true, so none of them follows for sure."
        q = (f"Statements: {syl_text(prem[0][0], names[prem[0][1]], names[prem[0][2]])} "
             f"{syl_text(prem[1][0], names[prem[1][1]], names[prem[1][2]])} Which conclusion definitely follows?")
        return finish({"k": "logic", "q": q, "e": e}, opts, ans,
                      lambda prem=prem, opts=tuple(opts), names=tuple(names): syl_answer(prem, opts, names))
    raise RuntimeError("syllogism")


def syl_answer(prem, opts, names):
    F = syl_follows(prem)
    txts = {syl_text(c[0], names[c[1]], names[c[2]]): c for c in CONCL}
    good = [o for o in opts if o in txts and txts[o] in F]
    if not good:
        return "None of these follows for sure"
    assert len(good) == 1, good
    return good[0]


# seating ------------------------------------------------------------

def seat_holds(c, s):
    pos = {n: i for i, n in enumerate(s)}
    N = len(s)
    t = c[0]
    if t == "end":
        return pos[c[1]] in (0, N - 1)
    if t == "notend":
        return pos[c[1]] not in (0, N - 1)
    if t == "mid":
        return pos[c[1]] == N // 2
    if t == "imleft":
        return pos[c[1]] + 1 == pos[c[2]]
    if t == "left":
        return pos[c[1]] < pos[c[2]]
    if t == "notadj":
        return abs(pos[c[1]] - pos[c[2]]) > 1
    if t == "gap":
        return abs(pos[c[1]] - pos[c[2]]) - 1 == c[3]
    raise ValueError(t)


def seat_text(c):
    t = c[0]
    if t == "end":
        return f"{c[1]} sits at one of the two ends."
    if t == "notend":
        return f"{c[1]} does not sit at either end."
    if t == "mid":
        return f"{c[1]} sits exactly in the middle."
    if t == "imleft":
        return f"{c[1]} sits immediately to the left of {c[2]}."
    if t == "left":
        return f"{c[1]} sits somewhere to the left of {c[2]}."
    if t == "notadj":
        return f"{c[1]} does not sit next to {c[2]}."
    return f"Exactly {c[3]} {'person sits' if c[3] == 1 else 'people sit'} between {c[1]} and {c[2]}."


def seat_facts(s, d):
    N = len(s)
    pos = {n: i for i, n in enumerate(s)}
    out = []
    for x in s:
        out.append(("end",) + (x,) if pos[x] in (0, N - 1) else ("notend", x))
        if N % 2 and pos[x] == N // 2 and d < 10:
            out.append(("mid", x))
        for y in s:
            if x == y:
                continue
            if pos[x] + 1 == pos[y]:
                out.append(("imleft", x, y))
            if pos[x] + 1 < pos[y]:
                out.append(("left", x, y))
            if x < y and abs(pos[x] - pos[y]) > 1:
                out.append(("notadj", x, y))
                out.append(("gap", x, y, abs(pos[x] - pos[y]) - 1))
    return out


def seat_solve(names, clues):
    return [s for s in itertools.permutations(names) if all(seat_holds(c, s) for c in clues)]


def g_seating(d):
    N = 4 if d == 7 else 5
    lo, hi = {7: (3, 4), 8: (4, 5), 9: (4, 5), 10: (5, 6)}[d]
    word = {4: "Four", 5: "Five"}[N]
    for _ in range(400):
        names = R.sample(NAMES, N)
        secret = names[:]
        R.shuffle(secret)
        pool = seat_facts(secret, d)
        R.shuffle(pool)
        sols = list(itertools.permutations(names))
        chosen = []
        for c in pool:
            nxt = [s for s in sols if seat_holds(c, s)]
            if len(nxt) < len(sols):
                chosen.append(c)
                sols = nxt
            if len(sols) == 1:
                break
        if len(sols) != 1:
            continue
        for c in chosen[:]:
            rest = [x for x in chosen if x is not c]
            if len(seat_solve(names, rest)) == 1:
                chosen = rest
        if not lo <= len(chosen) <= hi:
            continue
        sol = sols[0]
        asks = [(0, "at the far left"), (N - 1, "at the far right"), (1, "second from the left"), (N - 2, "second from the right")]
        if N == 5:
            asks.append((2, "in the middle"))
        if d >= 9:
            for x in sol[:-1]:
                asks.append(("right", x))
        R.shuffle(asks)
        for a in asks:
            if a[0] == "right":
                x = a[1]
                ans = sol[sol.index(x) + 1]
                if ("imleft", x, ans) in chosen:
                    continue
                qtxt = f"Who sits immediately to the right of {x}?"
                getter = lambda s, x=x: s[s.index(x) + 1]
            else:
                i = a[0]
                ans = sol[i]
                if ("mid", ans) in chosen and i == N // 2:
                    continue
                qtxt = f"Who sits {a[1]}?"
                getter = lambda s, i=i: s[i]
            break
        else:
            continue
        intro = f"{word} friends - {', '.join(sorted(names)[:-1])} and {sorted(names)[-1]} - sit in a row (left and right as you look at them)."
        clue_txt = " ".join(seat_text(c) for c in chosen)
        opts = R.sample([x for x in names if x != ans], 3) + [ans]
        return finish({"k": "logic", "q": f"{intro} {clue_txt} {qtxt}",
                       "e": f"Only one order fits every clue: {', '.join(sol)} (left to right). So the answer is {ans}."},
                      opts, ans, lambda names=tuple(names), chosen=tuple(chosen), getter=getter: getter(seat_solve(names, chosen)[0]))
    raise RuntimeError("seating")


def g_ages(d):
    if d == 8:
        dd = R.randint(18, 32)
        s = R.randint(6, 25)
        S = 2 * s + dd
        ans = s
        return finish({"k": "ages", "q": f"A mother and her daughter are {S} years old in total. The mother is {dd} years older. How old is the daughter?",
                       "e": f"Take away the difference and share equally: ({S} − {dd}) ÷ 2 = {ans}."},
                      nopts(ans, [s + dd, S - dd, (S + dd) // 2 - 1, dd]), ans,
                      lambda S=S, dd=dd: [x for x in range(1, 100) if x + (x + dd) == S][0])
    if d == 9:
        for _ in range(200):
            k, m, n = R.randint(3, 6), R.randint(2, 4), R.choice([4, 5, 6, 8, 10, 12, 15])
            if m >= k or (n * (m - 1)) % (k - m):
                continue
            s = n * (m - 1) // (k - m)
            if not 4 <= s <= 25:
                continue
            f = k * s
            ask_f = R.random() < 0.4
            ans = f if ask_f else s
            q = f"A father is {k} times as old as his son. In {n} years he will be {m} times as old as his son. How old is the {'father' if ask_f else 'son'} now?"
            return finish({"k": "ages", "q": q, "e": f"Son = s, father = {k}s. {k}s + {n} = {m}(s + {n}) gives s = {s}, so the father is {f}."},
                          nopts(ans, [s if ask_f else f, s + n, f + n, ans + n]), ans,
                          lambda k=k, m=m, n=n, af=ask_f: [(x * k if af else x) for x in range(1, 100) if k * x + n == m * (x + n)][0])
    for _ in range(500):
        b = R.randint(8, 30)
        n = R.randint(2, 6)
        k = R.randint(2, 4)
        a = k * (b - n) + n
        ps = [(p, (a + p) // (b + p)) for p in range(1, 25) if (a + p) % (b + p) == 0 and 2 <= (a + p) // (b + p) < k]
        if not ps:
            continue
        p, m = R.choice(ps)
        q = f"{n} year{'s' if n > 1 else ''} ago, Ravi was {k} times as old as Meera. In {p} year{'s' if p > 1 else ''}, Ravi will be {m} times as old as Meera. How old is Meera now?"
        return finish({"k": "ages", "q": q, "e": f"Ravi − {n} = {k}(Meera − {n}) and Ravi + {p} = {m}(Meera + {p}). Solving: Meera = {b}, Ravi = {a}."},
                      nopts(b, [a, b - n, b + p, b + 2]), b,
                      lambda n=n, k=k, p=p, m=m: [y for y in range(1, 100) for x in range(1, 150) if x - n == k * (y - n) and x + p == m * (y + p)][0])
    raise RuntimeError("ages")


# ------------------------------------------------------------------ levels 9-10

def frac_opts(ans, mis):
    out = []
    for m in mis:
        m = Fraction(m)
        if m != ans and m not in out and 0 <= m <= 1:
            out.append(m)
    R.shuffle(out)
    out = out[:3]
    while len(out) < 3:
        m = Fraction(R.randint(1, 11), 12)
        if m != ans and m not in out:
            out.append(m)
    return out + [ans]


def g_prob(d):
    if d == 9:
        kind = R.choice(["die_gt", "die_prime", "coins", "bag", "cards"])
        if kind == "die_gt":
            k = R.randint(1, 4)
            ans = Fraction(6 - k, 6)
            q = f"A fair die is rolled once. What is the probability of getting a number greater than {k}?"
            e = f"Numbers above {k}: {6 - k} of the 6 faces, so {fmt(ans)}."
            mis, chk = [Fraction(7 - k, 6), Fraction(k, 6), Fraction(1, 6 - k)], lambda k=k: Fraction(sum(1 for f in range(1, 7) if f > k), 6)
        elif kind == "die_prime":
            ans = Fraction(1, 2)
            q = "A fair die is rolled once. What is the probability of getting a prime number?"
            e = "The primes on a die are 2, 3 and 5 (1 is not prime): 3 of 6 = 1/2."
            mis, chk = [Fraction(2, 3), Fraction(1, 3), Fraction(1, 6)], lambda: Fraction(sum(1 for f in range(1, 7) if f in (2, 3, 5)), 6)
            if R.random() < 0.5:
                ans, q = Fraction(1, 3), "A fair die is rolled once. What is the probability of getting a multiple of 3?"
                e, mis = "Multiples of 3 on a die: 3 and 6 - 2 of 6 = 1/3.", [Fraction(1, 2), Fraction(1, 6), Fraction(2, 3)]
                chk = lambda: Fraction(sum(1 for f in range(1, 7) if f % 3 == 0), 6)
        elif kind == "coins":
            which = R.choice(["at least one head", "exactly one head", "two heads", "no heads"])
            cnt = {"at least one head": lambda o: o.count("H") >= 1, "exactly one head": lambda o: o.count("H") == 1,
                   "two heads": lambda o: o.count("H") == 2, "no heads": lambda o: o.count("H") == 0}[which]
            outs = ["".join(p) for p in itertools.product("HT", repeat=2)]
            ans = Fraction(sum(1 for o in outs if cnt(o)), 4)
            q = f"Two fair coins are tossed. What is the probability of getting {which}?"
            e = f"The 4 equally likely results are HH, HT, TH, TT; {ans.numerator * 4 // ans.denominator} of them {'fits' if ans * 4 == 1 else 'fit'}: {fmt(ans)}."
            mis, chk = [Fraction(1, 3), Fraction(2, 3), 1 - ans, Fraction(1, 2)], lambda c=cnt: Fraction(sum(1 for o in itertools.product("HT", repeat=2) if c("".join(o))), 4)
        elif kind == "bag":
            r, b, g = R.randint(2, 7), R.randint(2, 7), R.randint(1, 6)
            n = r + b + g
            ans = Fraction(r, n)
            q = f"A bag has {r} red, {b} blue and {g} green balls. One ball is picked at random. What is the probability it is red?"
            e = f"{r} red out of {n} balls: {fmt(ans)}."
            mis, chk = [Fraction(r, b + g), Fraction(b, n), Fraction(1, 3), 1 - ans], lambda r=r, n=n: Fraction(r, n)
        else:
            what, ans, why = R.choice([("a king", Fraction(1, 13), "4 kings out of 52"), ("a heart", Fraction(1, 4), "13 hearts out of 52"),
                                       ("a red king", Fraction(1, 26), "2 red kings out of 52"), ("a face card (jack, queen or king)", Fraction(3, 13), "12 face cards out of 52")])
            q = f"One card is drawn from a full pack of 52 playing cards. What is the probability it is {what}?"
            e = f"{why} = {fmt(ans)}."
            mis, chk = [Fraction(1, 52), Fraction(4, 13), Fraction(1, 4), Fraction(1, 13), Fraction(1, 26), Fraction(3, 13), Fraction(1, 2)], None
        return finish({"k": "probability", "q": q, "e": e}, frac_opts(ans, mis), ans, chk)
    kind = R.choice(["sum", "norepl", "six2", "six3"])
    if kind == "sum":
        s = R.randint(4, 10)
        ways = sum(1 for a in range(1, 7) for b in range(1, 7) if a + b == s)
        unordered = len({tuple(sorted((a, b))) for a in range(1, 7) for b in range(1, 7) if a + b == s})
        ans = Fraction(ways, 36)
        q = f"Two fair dice are rolled. What is the probability that the total is {s}?"
        e = f"{ways} of the 36 equally likely pairs add to {s}: {fmt(ans)}."
        mis, chk = [Fraction(unordered, 36), Fraction(1, 11), Fraction(ways + 1, 36), Fraction(ways, 12)], lambda s=s: Fraction(sum(1 for a in range(1, 7) for b in range(1, 7) if a + b == s), 36)
    elif kind == "norepl":
        r, b = R.randint(3, 7), R.randint(2, 6)
        n = r + b
        ans = Fraction(r, n) * Fraction(r - 1, n - 1)
        q = f"A box has {r} red and {b} blue pens. Two pens are taken out without putting the first back. What is the probability both are red?"
        e = f"{r}/{n} for the first, then {r - 1}/{n - 1} for the second: {r}/{n} × {r - 1}/{n - 1} = {fmt(ans)}."
        mis = [Fraction(r, n) ** 2, Fraction(r, n), Fraction(r - 1, n - 1), Fraction(r * (r - 1), n * n)]
        chk = lambda r=r, n=n: Fraction(sum(1 for x, y in itertools.permutations(range(n), 2) if x < r and y < r), n * (n - 1))
    elif kind == "six2":
        ans = Fraction(11, 36)
        q = "A fair die is rolled twice. What is the probability of getting at least one six?"
        e = "Chance of no six = 5/6 × 5/6 = 25/36, so at least one six = 1 − 25/36 = 11/36."
        mis, chk = [Fraction(1, 3), Fraction(1, 36), Fraction(25, 36), Fraction(1, 6)], lambda: Fraction(sum(1 for o in itertools.product(range(1, 7), repeat=2) if 6 in o), 36)
    else:
        ans = Fraction(91, 216)
        q = "A fair die is rolled three times. What is the probability of getting at least one six?"
        e = "No six = (5/6)³ = 125/216, so at least one six = 1 − 125/216 = 91/216."
        mis, chk = [Fraction(1, 2), Fraction(125, 216), Fraction(1, 216), Fraction(1, 6)], lambda: Fraction(sum(1 for o in itertools.product(range(1, 7), repeat=3) if 6 in o), 216)
    return finish({"k": "probability", "q": q, "e": e}, frac_opts(ans, mis), ans, chk)


def g_work(d):
    if d == 9:
        a, b = R.choice([(10, 15), (12, 24), (6, 12), (20, 30), (18, 9), (15, 30), (24, 12), (40, 60), (30, 20), (36, 18), (21, 42), (12, 4), (15, 10)])
        ans = a * b // (a + b)
        return finish({"k": "work", "q": f"Asha can paint a wall in {a} days and Ravi in {b} days. Working together, how many days will they take?",
                       "e": f"Each day they do 1/{a} + 1/{b} = {fmt(Fraction(1, a) + Fraction(1, b))} of the wall, so together {ans} days."},
                      nopts(ans, [(a + b) // 2, a + b, abs(a - b), min(a, b) - 1]), ans,
                      lambda a=a, b=b: 1 / (Fraction(1, a) + Fraction(1, b)))
    if R.random() < 0.5:
        a, t = R.choice([(12, 8), (10, 6), (20, 12), (18, 12), (15, 10), (24, 16), (30, 20), (28, 21), (6, 4), (36, 20)])
        b = a * t // (a - t)
        return finish({"k": "work", "q": f"Kabir and Neha together finish a job in {t} days. Kabir alone takes {a} days. How many days would Neha take alone?",
                       "e": f"Neha's share per day = 1/{t} − 1/{a} = 1/{b}, so {b} days."},
                      nopts(b, [a - t, a + t, 2 * t, b + t]), b,
                      lambda a=a, t=t: 1 / (Fraction(1, t) - Fraction(1, a)))
    f, e = R.choice([(4, 6), (3, 4), (6, 9), (5, 10), (8, 12), (10, 15), (6, 10), (12, 20)])
    ans = f * e // (e - f)
    return finish({"k": "work", "q": f"A pipe fills a tank in {f} hours. A leak empties the full tank in {e} hours. With both working, how long does the empty tank take to fill (hours)?",
                   "e": f"Each hour: 1/{f} − 1/{e} = 1/{ans} of the tank, so {ans} hours."},
                  nopts(ans, [e - f, f * e // (e + f) if f * e % (e + f) == 0 else f + e, f + e, ans + f]), ans,
                  lambda f=f, e=e: 1 / (Fraction(1, f) - Fraction(1, e)))


BLOOD_HARD = [
    lambda: (lambda F, M: (f"Pointing to a man, {F} says, \"His mother is the only daughter of my mother.\" How is {F} related to the man?",
                           "Mother", ["Sister", "Aunt", "Grandmother"],
                           f"The only daughter of {F}'s mother is {F} herself - so {F} is the man's mother."))(R.choice(NAMES_F), None),
    lambda: (lambda M: (f"Pointing to a woman, {M} says, \"She is the daughter of my paternal grandfather's only son.\" How is the woman related to {M}?",
                        "Sister", ["Cousin", "Aunt", "Niece"],
                        f"The only son of {M}'s paternal grandfather is {M}'s father, so she is {M}'s sister."))(R.choice(NAMES_M)),
    lambda: (lambda a, b, c, dd: (f"{a} is the brother of {b}. {b} is the sister of {c}. {c} is the father of {dd}. How is {a} related to {dd}?",
                                  "Uncle", ["Father", "Grandfather", "Cousin"],
                                  f"{a}, {b} and {c} are siblings; {c} is {dd}'s father, so {a} is {dd}'s uncle."))(*R.sample(NAMES_M, 1), R.choice(NAMES_F), *R.sample(NAMES_M[4:], 1), R.choice(NAMES)),
    lambda: (lambda m1, m2: (f"{m1}'s father is the only son of {m2}'s father. How is {m2} related to {m1}?",
                             "Father", ["Grandfather", "Uncle", "Brother"],
                             f"The only son of {m2}'s father is {m2} himself - so {m2} is {m1}'s father."))(*R.sample(NAMES_M, 2)),
    lambda: (lambda f1, m1, f2, m2: (f"{f1} is the mother of {m1}. {m1} is the brother of {f2}. {f2} is the wife of {m2}. How is {m2} related to {f1}?",
                                     "Son-in-law", ["Son", "Nephew", "Brother-in-law"],
                                     f"{f2} is {f1}'s daughter, and {m2} is {f2}'s husband - {f1}'s son-in-law."))(*R.sample(NAMES_F, 1), *R.sample(NAMES_M[:4], 1), *R.sample(NAMES_F[4:], 1), *R.sample(NAMES_M[4:], 1)),
    lambda: (lambda M: (f"Introducing a girl, {M} says, \"She is the daughter of the only son of my father.\" How is the girl related to {M}?",
                        "Daughter", ["Niece", "Sister", "Cousin"],
                        f"The only son of {M}'s father is {M} himself, so she is his daughter."))(R.choice(NAMES_M)),
    lambda: (lambda a, b: (f"{a}'s mother is the sister of {b}'s father. How is {a} related to {b}?",
                           "Cousin", ["Brother", "Nephew", "Uncle"],
                           f"{a}'s mother is {b}'s aunt, so {a} and {b} are cousins."))(*R.sample(NAMES_M, 2)),
    lambda: (lambda a, b: (f"{b} is the only son of {a}'s father's wife. {a} is a girl. How is {b} related to {a}?",
                           "Brother", ["Cousin", "Father", "Uncle"],
                           f"{a}'s father's wife is {a}'s mother; her only son is {a}'s brother."))(R.choice(NAMES_F), R.choice(NAMES_M)),
]

CODED = [("− +", "aunt", "sister of", "father of"), ("× ÷", "uncle", "brother of", "mother of"), ("+ ×", "father", "father of", "brother of"),
         ("÷ +", "grandmother", "mother of", "father of"), ("+ +", "grandfather", "father of", "father of"), ("÷ −", "mother", "mother of", "sister of"),
         ("× +", "uncle", "brother of", "father of"), ("− ÷", "aunt", "sister of", "mother of"), ("+ ÷", "grandfather", "father of", "mother of")]
LETTERS = [("A", "B", "C"), ("J", "K", "L"), ("X", "Y", "Z"), ("D", "E", "F"), ("R", "S", "T"), ("M", "N", "O")]


def g_blood_hard(d):
    if d == 9:
        q, ans, wrong, e = R.choice(BLOOD_HARD)()
        return finish({"k": "relations", "q": q, "e": e}, wrong + [ans], ans)
    ops, rel, r1, r2 = R.choice(CODED)
    a, b, c = R.choice(LETTERS)
    o1, o2 = ops.split()
    ans = f"{a} is {c}'s {rel}"
    pool = ["aunt", "uncle", "father", "mother", "grandmother", "grandfather", "sister", "brother", "cousin"]
    wrong = [f"{a} is {c}'s {w}" for w in R.sample([p for p in pool if p != rel], 3)]
    q = (f"In a code, P + Q means P is the father of Q; P − Q means P is the sister of Q; P × Q means P is the brother of Q; "
         f"P ÷ Q means P is the mother of Q. What does {a} {o1} {b} {o2} {c} mean?")
    return finish({"k": "relations", "q": q, "e": f"{a} is the {r1} {b}, and {b} is the {r2} {c} - so {a} is {c}'s {rel}."}, wrong + [ans], ans)


def g_dice(d):
    faces = list(range(1, 7))
    R.shuffle(faces)
    x, y, c1, c2, w, z = faces
    v1, v2 = [x, c1, c2], [y, c1, c2]
    R.shuffle(v1)
    R.shuffle(v2)
    q = (f"Two views of the same die: in the first, the faces showing are {', '.join(map(str, v1))}; "
         f"in the second, the faces showing are {', '.join(map(str, v2))}. Which number is opposite {x}?")
    return finish({"k": "dice", "q": q, "e": f"{c1} and {c2} show in both views, so {x} and {y} both touch them. Two different faces touching the same pair of neighbours must be opposite: {y}."},
                  [w, z, c1, y], y, lambda x=x, v1=tuple(v1), v2=tuple(v2): dice_opposite(x, v1, v2))


def dice_opposite(x, v1, v2):
    """independent: try every way to pair 1-6 into opposite faces"""
    found = set()

    def pairings(rest):
        if not rest:
            yield []
            return
        a = rest[0]
        for b in rest[1:]:
            for p in pairings([r for r in rest if r not in (a, b)]):
                yield [(a, b)] + p

    for p in pairings(list(range(1, 7))):
        opp = {}
        for a, b in p:
            opp[a], opp[b] = b, a
        if any(opp[f] in v for v in (v1, v2) for f in v):
            continue
        found.add(opp[x])
    assert len(found) == 1, found
    return found.pop()


def g_cube(d):
    n = R.randint(3, 6) if d == 9 else R.randint(4, 7)
    kind = R.choice(["two", "one"] if d == 9 else ["one", "none", "two"])
    f = {"two": 12 * (n - 2), "one": 6 * (n - 2) ** 2, "none": (n - 2) ** 3}
    words = {"two": "exactly two painted faces", "one": "exactly one painted face", "none": "no paint at all"}
    why = {"two": f"They sit along the 12 edges, {n - 2} per edge (not the corners): 12 × {n - 2}",
           "one": f"They sit in the middle of the 6 faces, {n - 2} × {n - 2} each: 6 × {(n - 2) ** 2}",
           "none": f"They form the hidden inner cube, {n - 2} × {n - 2} × {n - 2}"}
    ans = f[kind]
    mis = [v for k, v in f.items() if k != kind] + [8, 12 * n, 6 * n * n, n ** 3 - 6 * n * n]
    return finish({"k": "cube", "q": f"A cube is painted on all six sides and then cut into {n ** 3} equal small cubes ({n} along each edge). How many small cubes have {words[kind]}?",
                   "e": f"{why[kind]} = {ans}."}, nopts(ans, mis), ans,
                  lambda n=n, kind=kind: sum(1 for p in itertools.product(range(n), repeat=3)
                                             if sum(1 for c in p if c in (0, n - 1)) == {"two": 2, "one": 1, "none": 0}[kind]))


# ------------------------------------------------------------------ visual (SVG)

COLS = [("#E4572E", "red"), ("#2E86AB", "blue"), ("#F2B705", "yellow"), ("#3BA55C", "green"), ("#8E5572", "purple")]
SHAPES = ["circle", "square", "triangle", "diamond", "star", "hexagon"]


def shape(kind, cx, cy, r, fill, rot=0):
    if kind == "circle":
        return f'<circle cx="{cx:.1f}" cy="{cy:.1f}" r="{r:.1f}" fill="{fill}"/>'
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


QBOX = ('<rect width="100" height="100" rx="10" fill="#fff" stroke="#d9d2c3" stroke-dasharray="6 5"/><text x="50" y="66" '
        'font-size="48" font-family="Arial" font-weight="700" text-anchor="middle" fill="#9a8f7a">?</text>')


def strip(tiles: list[str]) -> str:
    """several tiles side by side plus a question-mark tile"""
    n = len(tiles) + 1
    body = "".join(f'<g transform="translate({i * 110},0)">{t}</g>' for i, t in enumerate(tiles))
    body += f'<g transform="translate({(n - 1) * 110},0)">{QBOX}</g>'
    return f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {n * 110 - 10} 100">{body}</svg>'


def grid3(cells: list[str]) -> str:
    body = ""
    for i, cell in enumerate(cells):
        x, y = (i % 3) * 105, (i // 3) * 105
        body += f'<g transform="translate({x},{y})">{QBOX if i == 8 else raw(cell)}</g>'
    return f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 310 310">{body}</svg>'


def raw(inner: str) -> str:
    return f'<rect width="100" height="100" rx="10" fill="#fff" stroke="#d9d2c3"/>{inner}'


def spots(n):
    if n == 1:
        return [(50, 50)], 22
    cols = math.ceil(math.sqrt(n))
    rows = math.ceil(n / cols)
    gap = 70 / max(cols, rows)
    pos = []
    for k in range(n):
        r_, c = divmod(k, cols)
        pos.append((15 + gap / 2 + c * gap + (70 - cols * gap) / 2, 15 + gap / 2 + r_ * gap + (70 - rows * gap) / 2))
    return pos, min(12, gap / 2 - 2)


def dots(n, fill="#2E86AB", kind="circle", rot=0):
    pos, rr = spots(n)
    if n == 1:
        rr = 22
    return "".join(shape(kind, x, y, rr, fill, rot) for x, y in pos)


def mark(svgs):
    """options must be distinct strings even when two look alike; every option gets
    a random invisible marker, the answer included, so the markup gives nothing away"""
    ms = R.sample(range(1000, 9999), len(svgs))
    return [s.replace("</svg>", f"<!--{m}--></svg>") for s, m in zip(svgs, ms)]


def v_rotation(d):
    step = 90 if d <= 3 else R.choice([45, 90, 135])
    col = R.choice(COLS)[0]
    start = R.choice([0, 45, 90])
    seq = [start + i * step for i in range(4)]
    ans_rot = start + 4 * step
    mk = lambda rot: tile(shape("arrow", 50, 50, 34, col, rot))
    opts = {ans_rot % 360: mk(ans_rot)}
    for wrong in (ans_rot - step, ans_rot + step, ans_rot + 180, ans_rot + 90, ans_rot - 45):
        if len(opts) == 4:
            break
        if wrong % 360 not in opts:
            opts[wrong % 360] = mk(wrong)
    return finish({"k": "visual", "q": "Which picture comes next in the pattern?",
                   "svg": strip([raw(shape("arrow", 50, 50, 34, col, r)) for r in seq]),
                   "e": f"The arrow turns {step}° clockwise every step."}, list(opts.values()), mk(ans_rot))


def v_count_seq(d):
    start = R.randint(1, 2)
    step = 1 if d < 3 else R.choice([1, 2])
    col = R.choice(COLS)[0]
    kind = R.choice(["circle", "square", "star"]) if d > 1 else "circle"
    seq = [start + i * step for i in range(4)]
    ans_n = start + 4 * step
    mk = lambda n: tile(dots(n, col, kind))
    wrong = [w for w in dict.fromkeys([ans_n - 1, ans_n + 1, ans_n + step + 1, ans_n - 2]) if w > 0 and w != ans_n][:3]
    return finish({"k": "visual", "q": "Which box comes next?", "svg": strip([raw(dots(n, col, kind)) for n in seq]),
                   "e": f"Each box has {step} more shape{'s' if step > 1 else ''} than the one before, so next has {ans_n}."},
                  [mk(w) for w in wrong] + [mk(ans_n)], mk(ans_n))


def v_pattern(d):
    col = R.choice(COLS)[0]
    picks = R.sample(SHAPES[:5], 4)
    A, B, C, D = picks
    pat = R.choice([["AB"], ["AB"]] if d == 1 else [["ABB"], ["ABC"], ["AAB"]])[0]
    seq = [pat[i % len(pat)] for i in range(5)]
    m = {"A": A, "B": B, "C": C}
    ans_k = m[seq[4]]
    mk = lambda k: tile(shape(k, 50, 50, 30, col))
    return finish({"k": "visual", "q": "Which shape comes next?", "svg": strip([raw(shape(m[s], 50, 50, 30, col)) for s in seq[:4]]),
                   "e": f"The shapes repeat in the order {' '.join(m[c] for c in pat)}, so next is a {ans_k}."},
                  [mk(k) for k in picks if k != ans_k][:3] + [mk(ans_k)], mk(ans_k))


def v_odd_shape(d):
    kind = R.choice(SHAPES[:4] if d < 3 else SHAPES)
    col, name = R.choice(COLS)
    how = R.choice(["shape", "colour"] if d < 3 else ["shape", "colour", "rotation", "size"])
    rot = R.choice([0, 15, 30]) if kind in ("triangle", "star") else 0
    base = tile(shape(kind, 50, 50, 32, col, rot))
    if how == "shape":
        other = R.choice([s for s in SHAPES if s != kind and not {s, kind} <= {"square", "diamond"}])
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
    opts = mark([base, base, base, odd])
    return finish({"k": "visual", "q": "Which picture is different from the others?", "e": f"Look closely: {why}."}, opts, opts[3])


def v_count(d):
    target = R.choice(["triangle", "circle", "square", "star"])
    n = R.randint(2, 4 + d)
    distract = R.randint(2, 2 + d)
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
                  nopts(n, [n + 1, n - 1, len(items)], spread=2), n, lambda n=n: n)


def v_matrix(d):
    """one rule: each row keeps a shape and colour, counts go 1, 2, 3 across (L3-5),
    or each row keeps a shape while the colours shift along (L6)"""
    shapes3 = R.sample(SHAPES[:4], 3)
    cols3 = R.sample(COLS, 3)
    mode = "count" if d < 6 else "colour"
    cells = []
    for r_ in range(3):
        for c in range(3):
            cells.append(dots(c + 1, cols3[r_][0], shapes3[r_]) if mode == "count" else shape(shapes3[r_], 50, 50, 28, cols3[(r_ + c) % 3][0]))
    if mode == "count":
        wrong = [tile(dots(2, cols3[2][0], shapes3[2])), tile(dots(3, cols3[1][0], shapes3[1])), tile(dots(3, cols3[2][0], shapes3[0]))]
        why = "Each row keeps one shape and colour, and the count goes 1, 2, 3."
    else:
        wrong = [tile(shape(shapes3[2], 50, 50, 28, cols3[(2 + k) % 3][0])) for k in (0, 1)] + [tile(shape(shapes3[1], 50, 50, 28, cols3[(2 + 2) % 3][0]))]
        why = "Each row keeps one shape, and the colours shift one place along every row."
    return finish({"k": "visual", "q": "Which picture completes the grid?", "svg": grid3(cells), "e": why}, wrong + [tile(cells[8])], tile(cells[8]))


def v_matrix2(d):
    """two rules at once: the count grows across a row AND the colours shift along"""
    shapes3 = R.sample(SHAPES[:5], 3)
    cols3 = R.sample(COLS, 3)
    cell = lambda r_, c: dots(c + 1, cols3[(r_ + c) % 3][0], shapes3[r_])
    cells = [cell(r_, c) for r_ in range(3) for c in range(3)]
    ans = tile(cells[8])
    wrong = [tile(dots(3, cols3[(2 + 2 + k) % 3][0], shapes3[2])) for k in (1, 2)] + [tile(dots(2, cols3[(2 + 2) % 3][0], shapes3[2]))]
    if d == 8:
        wrong[2] = tile(dots(3, cols3[(2 + 2) % 3][0], shapes3[1]))
    return finish({"k": "visual", "q": "Which picture completes the grid?", "svg": grid3(cells),
                   "e": "Two rules: across each row the count goes 1, 2, 3, and the colours shift one place along each row and column."},
                  wrong + [ans], ans)


def v_matrix_rot(d):
    """rotation + count: count goes 1, 2, 3 across; the arrows turn as you go"""
    col = R.choice(COLS)[0]
    base = R.choice([0, 45, 90])
    if d == 9:
        rot = lambda r_, c: base + 90 * r_
        why = "Across each row the number of arrows goes 1, 2, 3; each row down, the arrows turn a further 90° clockwise."
        wr = [(3, base + 90), (3, base), (2, base + 180)]
    else:
        rot = lambda r_, c: base + 45 * (r_ + c)
        why = "The number of arrows goes 1, 2, 3 across each row, and every step right or down turns them 45° clockwise - so the last box is turned 180° from the first."
        wr = [(3, base + 135), (3, base + 225), (2, base + 180)]
    cells = [dots(c + 1, col, "arrow", rot(r_, c)) for r_ in range(3) for c in range(3)]
    ans = tile(cells[8])
    wrong = [tile(dots(n, col, "arrow", ro)) for n, ro in wr]
    return finish({"k": "visual", "q": "Which picture completes the grid?", "svg": grid3(cells), "e": why}, wrong + [ans], ans)


# ------------------------------------------------------------------ assemble

LEVELS = {  # level: [(generator, weight)]
    1: [(g_add, 3), (g_sub, 2), (g_after, 2), (g_biggest, 2), (g_series_small, 3), (g_odd_word, 3), (v_odd_shape, 3),
        (v_count, 3), (v_count_seq, 2), (v_pattern, 3)],
    2: [(g_add, 2), (g_sub, 2), (g_after, 1), (g_biggest, 2), (g_series_small, 3), (g_odd_word, 2), (g_analogy, 2), (g_letters, 2),
        (v_pattern, 2), (v_count, 2), (v_odd_shape, 2), (v_rotation, 2), (g_days, 2)],
    3: [(g_mult, 3), (g_money, 3), (g_series_small, 2), (g_series_geo, 2), (g_series_alt, 2), (g_letters, 2), (g_code_shift, 2),
        (g_analogy, 2), (g_order, 2), (g_odd_number, 2), (g_months, 2), (v_rotation, 2), (v_count_seq, 2), (v_matrix, 2), (v_odd_shape, 1)],
    4: [(g_mult, 3), (g_time, 2), (g_series_alt, 2), (g_series_geo, 2), (g_series_diff, 2), (g_code_shift, 2), (g_analogy, 2), (g_order, 2),
        (g_odd_number, 2), (g_grid, 2), (g_letters, 2), (v_rotation, 2), (v_matrix, 2), (v_odd_shape, 2), (g_odd_word, 1)],
    5: [(g_mixed, 3), (g_fraction, 3), (g_percent, 2), (g_letters, 2), (g_direction, 2), (g_blood, 3), (v_matrix, 3), (g_series_diff, 2),
        (g_series_special, 2), (g_num_analogy, 2), (g_odd_number, 2), (g_analogy, 1), (g_area, 2)],
    6: [(g_percent, 2), (g_fraction, 2), (g_average, 2), (g_rank, 2), (g_letters, 2), (g_direction, 2), (g_blood, 2), (g_cal_after, 2),
        (g_numcode, 2), (g_grid, 2), (v_matrix, 2), (g_series_special, 2), (g_num_analogy, 2), (g_mixed, 2), (v_rotation, 1)],
    7: [(v_matrix2, 3), (g_series_inter, 3), (g_ratio, 2), (g_speed, 3), (g_clock, 2), (g_cal_date, 2), (g_code_rev, 2), (g_syllogism, 3),
        (g_seating, 3), (g_percent, 2), (g_analogy, 1), (g_odd_number, 1), (g_num_analogy, 1), (g_letters, 1)],
    8: [(v_matrix2, 2), (g_series_inter, 2), (g_series_altops, 2), (g_ratio, 2), (g_speed, 3), (g_clock, 2), (g_cal_year, 2), (g_code_rev, 2),
        (g_syllogism, 3), (g_seating, 3), (g_ages, 2), (g_direction, 2), (g_percent, 2), (g_grid, 2), (g_num_analogy, 1)],
    9: [(g_series_multi, 4), (g_clock, 2), (g_prob, 4), (g_work, 3), (g_ages, 3), (g_blood_hard, 3), (v_matrix_rot, 3), (g_dice, 2),
        (g_cube, 2), (g_seating, 3), (g_syllogism, 2), (g_percent, 2), (g_letters, 2), (g_grid, 1), (g_num_analogy, 1)],
    10: [(g_series_hard, 4), (g_clock, 2), (g_prob, 4), (g_work, 3), (g_ages, 3), (g_blood_hard, 3), (v_matrix_rot, 3), (g_dice, 2),
         (g_cube, 2), (g_seating, 3), (g_syllogism, 2), (g_speed, 3), (g_cal_real, 2), (g_code_rev, 2)],
}


def qkey(q):
    """text questions must read differently; picture questions differ by figure or options"""
    if "svg" in q or q["o"][0].startswith("<svg"):
        return q["q"] + q.get("svg", "") + "|".join(sorted(q["o"]))
    return q["q"]


def build() -> dict:
    bank = {}
    for level in range(1, 11):
        pool = [g for g, w in LEVELS[level] for _ in range(w)]
        seen = set()
        made = tries = 0
        while made < PER_LEVEL:
            tries += 1
            assert tries < 20000, f"level {level} stuck at {made}"
            q = R.choice(pool)(level)
            key = qkey(q)
            if key in seen:
                continue
            seen.add(key)
            made += 1
            q["l"] = level
            q["t"] = "visual" if ("svg" in q or q["o"][0].startswith("<svg")) else "text"
            q["tr"] = "iq"
            bank[f"L{level:02d}B{made:03d}"] = q
    return bank


MIND = pathlib.Path(__file__).resolve().parent / "mindset.json"


def add_mindset(bank: dict) -> None:
    """The Mindset Challenge: hand-written scenarios from her own posts,
    captions, chapters and FAQ. Track 'mind', ids M<level>Q<n>. The option
    order already live is kept, so a rebuild of the IQ bank changes nothing here."""
    old = json.loads(OUT.read_text(encoding="utf-8")) if OUT.exists() else {}
    rm = random.Random(20261013)
    count = {}
    for item in json.loads(MIND.read_text(encoding="utf-8")):
        lvl = item["l"]
        count[lvl] = count.get(lvl, 0) + 1
        qid = f"M{lvl:02d}Q{count[lvl]:03d}"
        prev = old.get(qid)
        if prev and prev.get("q") == item["q"] and sorted(prev["o"]) == sorted(item["o"]):
            q = {"k": "mindset", "q": item["q"], "e": item["e"], "o": prev["o"], "a": prev["o"].index(item["o"][item["a"]])}
        else:
            opts = list(item["o"])
            ans = opts[item["a"]]
            rm.shuffle(opts)
            q = {"k": "mindset", "q": item["q"], "e": item["e"], "o": opts, "a": opts.index(ans)}
        q.update({"l": lvl, "t": "text", "tr": "mind"})
        bank[qid] = q


# ------------------------------------------------------------------ self-check

def self_check(bank: dict) -> list[str]:
    errs = []
    per = {}
    keys = {}
    rechecked = 0
    for qid, q in bank.items():
        lvl, tr = q["l"], q.get("tr")
        if tr not in ("iq", "mind"):
            errs.append(f"{qid}: track {tr!r}")
        per[(tr, lvl)] = per.get((tr, lvl), 0) + 1
        o = q["o"]
        if len(o) != 4 or len(set(o)) != 4:
            errs.append(f"{qid}: options {o}")
        if not (isinstance(q["a"], int) and 0 <= q["a"] < 4):
            errs.append(f"{qid}: answer index {q['a']}")
        if not q.get("e") or not q.get("q"):
            errs.append(f"{qid}: missing text")
        if tr == "iq":
            k = qkey(q)
            if k in keys.setdefault(lvl, set()):
                errs.append(f"{qid}: duplicate within level {lvl}")
            keys[lvl].add(k)
            if any(ord(ch) > 0x2fff for ch in q["q"] + q["e"]):
                errs.append(f"{qid}: odd character")
        chk = q.get("_check")
        if chk:
            got = chk()
            if isinstance(got, (int, Fraction, float)):
                got = fmt(Fraction(got).limit_denominator(1000)) if isinstance(got, float) else fmt(got)
            got = str(got)
            want = o[q["a"]]
            if got != want and got + "°" != want and f"{got}%" != want:
                errs.append(f"{qid}: recomputed {got!r} but marked {want!r} | {q['q'][:80]}")
            rechecked += 1
    for lvl in range(1, 11):
        if per.get(("iq", lvl), 0) < 60:
            errs.append(f"level {lvl}: only {per.get(('iq', lvl), 0)} questions")
    print(f"  self-check: {len(bank)} questions, {rechecked} answers recomputed independently, {len(errs)} problems")
    return errs


def main() -> None:
    bank = build()
    add_mindset(bank)
    errs = self_check(bank)
    for e in errs[:30]:
        print("  !!", e)
    assert not errs, f"{len(errs)} problems"
    for q in bank.values():
        q.pop("_check", None)
    OUT.write_text(json.dumps(bank, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    vis = sum(1 for q in bank.values() if q["t"] == "visual")
    print(f"{len(bank)} questions, {vis} visual, {OUT.stat().st_size // 1024} KB")
    for lvl in range(1, 11):
        kinds = {}
        for q in bank.values():
            if q["tr"] == "iq" and q["l"] == lvl:
                kinds[q["k"]] = kinds.get(q["k"], 0) + 1
        print(f"  L{lvl:<2}", dict(sorted(kinds.items())))


if __name__ == "__main__":
    main()
