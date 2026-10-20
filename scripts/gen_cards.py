#!/usr/bin/env python3
"""Generate the pixel-art SVGs for the isaac-sun profile README.

Data comes from GitHub's public REST API and the public contribution
calendar, so no third-party image host is involved (China-friendly).
Every image is written twice, as <name>-dark.svg and <name>-light.svg.

Run locally:  python3 scripts/gen_cards.py
In CI:        same command (see .github/workflows/update-cards.yml).
"""
import json
import os
import re
import urllib.request
from datetime import date

from pixelfont import pixel_text as px, sprite, width

OWNER = "isaac-sun"
ASSETS = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "assets")
# Repos that contain no meaningful code language for the breakdown.
EXCLUDE_REPOS = {"isaac-sun", "isaac-sun.github.io"}
USER_AGENT = "isaac-sun-profile-card-generator"

THEMES = {  # Sweetie-16 palette
    "dark": {"bg": "#1a1c2c", "panel": "#29366f", "frame": "#f4f4f4", "text": "#f4f4f4", "muted": "#94b0c2",
             "yellow": "#ffcd75", "green": "#a7f070", "heart": "#b13e53", "shadow": "#0b0c16",
             "brick": "#566c86", "mortar": "#333c57", "star": "#f4f4f4", "seg_off": "#333c57",
             "heat": ["#333c57", "#257179", "#38b764", "#a7f070", "#ffcd75"]},
    "light": {"bg": "#f4f4f4", "panel": "#ffffff", "frame": "#1a1c2c", "text": "#1a1c2c", "muted": "#566c86",
              "yellow": "#ef7d57", "green": "#38b764", "heart": "#b13e53", "shadow": "#94b0c2",
              "brick": "#ef7d57", "mortar": "#b13e53", "star": "#94b0c2", "seg_off": "#e2e8ee",
              "heat": ["#e2e8ee", "#a7f070", "#38b764", "#257179", "#29366f"]},
}
CRISP = 'shape-rendering="crispEdges"'
SHORT_NAMES = {"Jupyter Notebook": "JUPYTER"}

HERO = [  # 16×16 player sprite
    "................",
    ".....KKKKKK.....",
    "....KHHHHHHK....",
    "...KHHHHHHHHK...",
    "...KHSSSSSSHK...",
    "...KSSKSSKSSK...",
    "...KSSSSSSSSK...",
    "....KSSRRSSK....",
    ".....KKKKKK.....",
    "...KKBBBBBBKK...",
    "..KBBBBBBBBBBK..",
    "..KBKLLLLLLKBK..",
    "..KSKLWWWWLKSK..",
    "..KKKLWWWWLKKK..",
    "....KLLLLLLK....",
    "....KKKKKKKK....",
]
HERO_PALETTE = {"K": "#0b0c16", "H": "#5d275d", "S": "#f4c9a0", "R": "#b13e53",
                "B": "#3b5dc9", "L": "#94b0c2", "W": "#73eff7"}


# ---------------------------------------------------------------------------
# Data
# ---------------------------------------------------------------------------
def fetch(url):
    request = urllib.request.Request(url, headers={
        "Accept": "application/vnd.github+json",
        "User-Agent": USER_AGENT,
        "X-GitHub-Api-Version": "2022-11-28",
    })
    with urllib.request.urlopen(request, timeout=20) as response:
        return response.read().decode("utf-8")


def get_json(path):
    return json.loads(fetch(f"https://api.github.com{path}"))


def get_contrib():
    """Return [(date, count, level)] in chronological order.

    The calendar HTML lists cells row by row (all Sundays, then all Mondays…),
    with the real count in a separate <tool-tip for="cell-id">, so both are
    joined by id and then sorted by date.
    """
    page = fetch(f"https://github.com/users/{OWNER}/contributions")
    cells = {}
    for tag in re.findall(r"<td\b[^>]*ContributionCalendar-day[^>]*>", page):
        day = re.search(r'data-date="([^"]+)"', tag)
        cid = re.search(r'\bid="([^"]+)"', tag)
        level = re.search(r'data-level="([0-4])"', tag)
        if day and cid and level:
            cells[cid.group(1)] = [day.group(1), 0, int(level.group(1))]
    for cid, label in re.findall(r'<tool-tip\b[^>]*\bfor="([^"]+)"[^>]*>([^<]*)</tool-tip>', page):
        count = re.match(r"\s*(\d[\d,]*) contribution", label)
        if cid in cells and count:
            cells[cid][1] = int(count.group(1).replace(",", ""))
    days = sorted(tuple(cell) for cell in cells.values())
    if not days:
        raise RuntimeError("GitHub returned no public contribution-calendar data")
    return days


def get_stats():
    user = get_json(f"/users/{OWNER}")
    repos = get_json(f"/users/{OWNER}/repos?per_page=100&type=owner")
    public = [r for r in repos if not r.get("fork") and not r.get("private")]
    return {
        "followers": user["followers"],
        "repos": len(public),
        "stars": sum(int(r.get("stargazers_count") or 0) for r in public),
        "repo_names": [r["name"] for r in public],
    }


def get_languages(stats):
    totals = {}
    for name in stats["repo_names"]:
        if name in EXCLUDE_REPOS:
            continue
        try:
            langs = get_json(f"/repos/{OWNER}/{name}/languages")
        except Exception as error:
            print(f"warn: unable to fetch languages for {name}: {error}")
            continue
        for language, byte_count in langs.items():
            totals[language] = totals.get(language, 0) + int(byte_count or 0)
    return totals


def best_streak(counts):
    best = run = 0
    for count in counts:
        run = run + 1 if count else 0
        best = max(best, run)
    return best


# ---------------------------------------------------------------------------
# Rendering
# ---------------------------------------------------------------------------
def svg(w, h, label, body):
    return (f'<svg width="{w}" height="{h}" viewBox="0 0 {w} {h}" xmlns="http://www.w3.org/2000/svg" '
            f'role="img" aria-label="{label}">\n{body}\n</svg>\n')


def window(x, y, w, h, t, title):
    """An RPG menu window with a title tab sitting on its top border."""
    return "\n".join([
        f'<rect x="{x}" y="{y}" width="{w}" height="{h}" fill="{t["panel"]}" stroke="{t["frame"]}" stroke-width="4" {CRISP}/>',
        f'<rect x="{x + 8}" y="{y + 8}" width="{w - 16}" height="{h - 16}" fill="none" stroke="{t["frame"]}" stroke-opacity="0.35" stroke-width="2" {CRISP}/>',
        f'<rect x="{x + 24}" y="{y - 14}" width="{width(title, 3) + 24}" height="28" fill="{t["panel"]}" stroke="{t["frame"]}" stroke-width="4" {CRISP}/>',
        px(x + 36, y - 10, title, 3, t["yellow"]),
    ])


def render_header(total, t):
    w, h = 1200, 380
    b = [f'<rect width="{w}" height="{h}" fill="{t["bg"]}"/>']
    stars = [(640, 60), (720, 150), (1130, 90), (980, 40), (600, 250), (1150, 230), (700, 320), (640, 180)]
    for i, (sx, sy) in enumerate(stars):
        b.append(f'<rect x="{sx}" y="{sy}" width="6" height="6" fill="{t["star"]}" {CRISP}>'
                 f'<animate attributeName="opacity" values="1;0.2;1" dur="{1.2 + i * 0.3:.1f}s" repeatCount="indefinite" calcMode="discrete"/></rect>')
    b += [
        f'<rect x="6" y="6" width="{w - 12}" height="{h - 12}" fill="none" stroke="{t["frame"]}" stroke-width="6" {CRISP}/>',
        f'<rect x="18" y="18" width="{w - 36}" height="{h - 36}" fill="none" stroke="{t["frame"]}" stroke-opacity="0.3" stroke-width="2" {CRISP}/>',
        px(48, 42, "PLAYER 1", 3, t["yellow"]),
        px(w - 48, 42, f"HI-SCORE {total:06d}", 3, t["text"], "end"),
        px(54, 102, "YINAN SUN", 10, t["shadow"]),
        px(48, 96, "YINAN SUN", 10, t["text"]),
        px(48, 206, "CLASS", 3, t["muted"]), px(200, 206, "FL RESEARCHER", 3, t["text"]),
        px(48, 242, "GUILD", 3, t["muted"]), px(200, 242, "UNIV. OF NOTTINGHAM", 3, t["text"]),
        px(48, 278, "HP", 3, t["muted"]), px(200, 278, "♥♥♥♥♡", 3, t["heart"]),
        f'<g>{px(48, 324, "▶ PRESS START", 3, t["green"])}'
        f'<animate attributeName="opacity" values="1;0" dur="1.1s" calcMode="discrete" repeatCount="indefinite"/></g>',
    ]
    for i in range(10):  # brick platform
        b.append(f'<rect x="{840 + i * 30}" y="300" width="30" height="40" fill="{t["brick"]}" stroke="{t["mortar"]}" stroke-width="3" {CRISP}/>')
    b.append(f'<g>{sprite(900, 108, HERO, HERO_PALETTE, 12)}'
             f'<animateTransform attributeName="transform" type="translate" values="0 0;0 -8;0 0" dur="1.2s" calcMode="discrete" repeatCount="indefinite"/></g>')
    b += [f'<rect x="1070" y="96" width="92" height="44" fill="{t["panel"]}" stroke="{t["frame"]}" stroke-width="4" {CRISP}/>',
          f'<rect x="1062" y="136" width="12" height="12" fill="{t["frame"]}" {CRISP}/>',
          px(1116, 108, "HI!", 3, t["text"], "middle")]
    return svg(w, h, "Player 1: Yinan Sun — class: FL researcher, guild: University of Nottingham", "\n".join(b))


def render_status(days, stats, langs, t):
    w, h = 1200, 600
    counts = [count for _, count, _ in days]
    total = sum(counts)
    b = [window(20, 24, 560, 300, t, "STATUS")]
    rows = [("XP", f"{total}", t["yellow"]),
            ("QUESTS", f"{stats['repos']}", t["text"]),
            ("STARS", f"★ {stats['stars']}", t["yellow"]),
            ("ALLIES", f"{stats['followers']}", t["text"]),
            ("BEST STREAK", f"{best_streak(counts)} DAYS", t["green"])]
    for i, (key, value, color) in enumerate(rows):
        y = 70 + i * 48
        b.append(px(52, y, key, 3, t["muted"]))
        b.append(px(548, y, value, 3, color, "end"))

    b.append(window(620, 24, 560, 300, t, "SKILLS"))
    grand = sum(langs.values()) or 1
    for i, (name, value) in enumerate(sorted(langs.items(), key=lambda kv: -kv[1])[:5]):
        y = 70 + i * 48
        pct = value / grand * 100
        filled = max(1, round(pct / 10))
        b.append(px(652, y, SHORT_NAMES.get(name, name), 3, t["text"]))
        for s in range(10):
            b.append(f'<rect x="{850 + s * 22}" y="{y - 2}" width="18" height="24" fill="{t["green"] if s < filled else t["seg_off"]}" {CRISP}/>')
        b.append(px(1148, y, f"{pct:.0f}%", 3, t["muted"], "end"))

    b.append(window(20, 370, 1160, 210, t, "QUEST LOG - 52 WEEKS"))
    offset = (date.fromisoformat(days[0][0]).weekday() + 1) % 7  # Sunday-first rows, like GitHub
    for index, (day, count, level) in enumerate(days):
        col, row = divmod(index + offset, 7)
        b.append(f'<rect x="{123 + col * 18}" y="{410 + row * 20}" width="16" height="16" fill="{t["heat"][level]}" {CRISP}>'
                 f'<title>{day}: {count} contribution{"" if count == 1 else "s"}</title></rect>')
    for row, label in ((1, "M"), (3, "W"), (5, "F")):
        b.append(px(86, 412 + row * 20, label, 2, t["muted"]))
    return svg(w, h, f"Player stats: {total} XP (contributions), {stats['repos']} quests, {stats['stars']} stars", "\n".join(b))


def write(name, theme, content):
    with open(os.path.join(ASSETS, f"{name}-{theme}.svg"), "w") as handle:
        handle.write(content)


def main():
    print("Fetching contribution calendar...")
    days = get_contrib()
    print("Fetching stats...")
    stats = get_stats()
    print("Fetching language breakdown...")
    langs = get_languages(stats)

    os.makedirs(ASSETS, exist_ok=True)
    total = sum(count for _, count, _ in days)
    for theme, t in THEMES.items():
        write("header", theme, render_header(total, t))
        write("status", theme, render_status(days, stats, langs, t))
    print(f"Wrote {2 * len(THEMES)} images. contributions={total}, "
          f"repos={stats['repos']}, stars={stats['stars']}, langs={len(langs)}")


if __name__ == "__main__":
    main()
