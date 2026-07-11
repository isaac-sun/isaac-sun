#!/usr/bin/env python3
"""Generate themed, self-contained SVG cards for the isaac-sun profile README.

All data is pulled live from the GitHub API via `gh`, so the cards stay
accurate without depending on any external image host (China-friendly).

Run locally:  python3 scripts/gen_cards.py
In CI:        same command, authenticated with GITHUB_TOKEN.
"""
import json
import subprocess
import sys
from datetime import datetime

OWNER = "isaac-sun"
ASSETS = "assets"
# Repos that contain no meaningful code language for the breakdown.
EXCLUDE_REPOS = {"isaac-sun", "isaac-sun.github.io"}

# GitHub-ish linguist colors; unknown languages fall back to gray.
LANG_COLORS = {
    "Python": "#3572A5", "C": "#555555", "C++": "#f34b7d", "JavaScript": "#f1e05a",
    "TypeScript": "#3178c6", "HTML": "#e34c26", "CSS": "#563d7c",
    "Jupyter Notebook": "#DA5B0B", "Shell": "#89e051", "Vue": "#41b883",
    "Java": "#b07219", "Haskell": "#5e5086", "Lua": "#000080",
    "CMake": "#DA3434", "Dockerfile": "#384d54", "Makefile": "#427819",
}


def gh_api(args):
    cmd = ["gh", "api"] + args
    res = subprocess.run(cmd, capture_output=True, text=True)
    if res.returncode != 0:
        sys.exit("gh api failed: " + res.stderr.strip())
    return res.stdout


def get_contrib():
    q = ('{ user(login:"%s"){ contributionsCollection { contributionCalendar '
         '{ totalContributions weeks { contributionDays { date contributionCount } } } } } }' % OWNER)
    cal = json.loads(gh_api(["graphql", "-f", "query=" + q]))["data"]["user"][
        "contributionsCollection"]["contributionCalendar"]
    days = []
    for w in cal["weeks"]:
        for d in w["contributionDays"]:
            days.append((d["date"], d["contributionCount"]))
    return cal["totalContributions"], days


def get_stats():
    q = ('{ user(login:"%s"){ followers{totalCount} following{totalCount} '
         'repositories(first:100,ownerAffiliations:OWNER,isFork:false){totalCount '
         'nodes{name stargazers{totalCount}}} starredRepositories{totalCount} } }' % OWNER)
    u = json.loads(gh_api(["graphql", "-f", "query=" + q]))["data"]["user"]
    repos = u["repositories"]["nodes"]
    stars = sum(r["stargazers"]["totalCount"] for r in repos)
    return {
        "followers": u["followers"]["totalCount"],
        "following": u["following"]["totalCount"],
        "repos": u["repositories"]["totalCount"],
        "stars": stars,
        "starred": u["starredRepositories"]["totalCount"],
        "repo_names": [r["name"] for r in repos],
    }


def get_languages(stats):
    totals = {}
    for name in stats["repo_names"]:
        if name in EXCLUDE_REPOS:
            continue
        try:
            langs = json.loads(gh_api(["repos/%s/%s/languages" % (OWNER, name)]))
        except SystemExit:
            continue
        for k, v in langs.items():
            totals[k] = totals.get(k, 0) + v
    return totals


def esc(s):
    return (s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;"))


# ---------------------------------------------------------------------------
# Card 1: contribution activity (area/line chart, real daily counts)
# ---------------------------------------------------------------------------
def render_activity(total, days):
    counts = [c for _, c in days]
    n = len(counts)
    x0, x1 = 20, 680
    ytop, ybot = 45, 135
    plot_w = x1 - x0
    plot_h = ybot - ytop
    maxc = max(counts) if counts else 1
    ymax = max(maxc, 4)

    pts = []
    for i, c in enumerate(counts):
        x = x0 + (i / (n - 1)) * plot_w
        y = ybot - (c / ymax) * plot_h
        pts.append((round(x, 1), round(y, 1)))

    line = " ".join("L%.1f,%.1f" % (x, y) if i else "M%.1f,%.1f" % (x, y)
                    for i, (x, y) in enumerate(pts))
    area = "%s L%.1f,%.1f L%.1f,%.1f Z" % (line, x1, ybot, x0, ybot)

    # longest streak marker (peak day)
    peak_i = counts.index(maxc)
    px, py = pts[peak_i]

    start, end = days[0][0], days[-1][0]
    return f'''<svg width="700" height="150" viewBox="0 0 700 150" xmlns="http://www.w3.org/2000/svg" role="img" aria-label="Contribution activity">
  <defs>
    <linearGradient id="bg" x1="0" y1="0" x2="1" y2="1">
      <stop offset="0%" stop-color="#06101f"/>
      <stop offset="100%" stop-color="#0b1224"/>
    </linearGradient>
    <linearGradient id="neon" x1="0" y1="0" x2="1" y2="0">
      <stop offset="0%" stop-color="#22d3ee"/>
      <stop offset="100%" stop-color="#4ade80"/>
    </linearGradient>
    <linearGradient id="area" x1="0" y1="0" x2="0" y2="1">
      <stop offset="0%" stop-color="#22d3ee" stop-opacity="0.45"/>
      <stop offset="100%" stop-color="#22d3ee" stop-opacity="0"/>
    </linearGradient>
  </defs>
  <rect width="700" height="150" rx="14" fill="url(#bg)" stroke="url(#neon)" stroke-opacity="0.5" stroke-width="1.5"/>
  <text x="20" y="28" font-family="'JetBrains Mono',monospace" font-size="12" fill="#94a3b8" letter-spacing="1">sar -A :: contribution activity</text>
  <g stroke="#13233b" stroke-width="1">
    <line x1="20" y1="{ytop}" x2="680" y2="{ytop}"/>
    <line x1="20" y1="{ybot-plot_h//2}" x2="680" y2="{ybot-plot_h//2}"/>
    <line x1="20" y1="{ybot}" x2="680" y2="{ybot}"/>
  </g>
  <path d="{area}" fill="url(#area)"/>
  <path d="{line}" fill="none" stroke="#4ade80" stroke-width="2.5" stroke-linejoin="round" stroke-linecap="round"/>
  <circle cx="{px}" cy="{py}" r="3.5" fill="#a78bfa"/>
  <text x="680" y="44" text-anchor="end" font-family="'JetBrains Mono',monospace" font-size="10" fill="#64748b">peak {maxc}/day</text>
  <text x="20" y="148" font-family="'JetBrains Mono',monospace" font-size="10" fill="#64748b">{start} → {end}</text>
  <text x="680" y="148" text-anchor="end" font-family="'JetBrains Mono',monospace" font-size="10" fill="#22d3ee">{total} contributions</text>
</svg>
'''


# ---------------------------------------------------------------------------
# Card 2: stats overview
# ---------------------------------------------------------------------------
def render_stats(s):
    rows = [("Public Repos", s["repos"], "#22d3ee"),
            ("Followers", s["followers"], "#4ade80"),
            ("Following", s["following"], "#f472b6"),
            ("Stars Earned", s["stars"], "#a78bfa"),
            ("Starred", s["starred"], "#f7df1e")]
    y = 124
    body = ""
    for label, val, color in rows:
        body += f'''  <text x="20" y="{y}" font-family="'JetBrains Mono',monospace" font-size="12" fill="#94a3b8">{label}</text>
  <text x="380" y="{y}" text-anchor="end" font-family="'JetBrains Mono',monospace" font-size="15" font-weight="700" fill="{color}">{val}</text>
  <line x1="20" y1="{y+10}" x2="380" y2="{y+10}" stroke="#13233b" stroke-width="1"/>
'''
        y += 22
    return f'''<svg width="400" height="{y-14}" viewBox="0 0 400 {y-14}" xmlns="http://www.w3.org/2000/svg" role="img" aria-label="GitHub stats overview">
  <defs>
    <linearGradient id="bg" x1="0" y1="0" x2="1" y2="1">
      <stop offset="0%" stop-color="#06101f"/>
      <stop offset="100%" stop-color="#0b1224"/>
    </linearGradient>
    <linearGradient id="neon" x1="0" y1="0" x2="1" y2="0">
      <stop offset="0%" stop-color="#22d3ee"/>
      <stop offset="100%" stop-color="#4ade80"/>
    </linearGradient>
    <filter id="glow" x="-40%" y="-40%" width="180%" height="180%">
      <feGaussianBlur stdDeviation="2.5" result="b"/>
      <feMerge><feMergeNode in="b"/><feMergeNode in="SourceGraphic"/></feMerge>
    </filter>
  </defs>
  <rect width="400" height="{y-14}" rx="14" fill="url(#bg)" stroke="url(#neon)" stroke-opacity="0.5" stroke-width="1.5"/>
  <text x="20" y="28" font-family="'JetBrains Mono','Fira Code',monospace" font-size="12" fill="#94a3b8" letter-spacing="1">isaac@github :: stats</text>
  <line x1="20" y1="40" x2="380" y2="40" stroke="#1e293b" stroke-width="1"/>
  <circle cx="40" cy="76" r="20" fill="#04101c" stroke="#4ade80" stroke-opacity="0.5" stroke-width="1.5"/>
  <text x="40" y="82" text-anchor="middle" font-family="'JetBrains Mono',monospace" font-size="15" font-weight="700" fill="#4ade80" filter="url(#glow)">YS</text>
  <text x="72" y="70" font-family="'Segoe UI',system-ui,sans-serif" font-size="16" font-weight="700" fill="#e2e8f0">Yinan SUN</text>
  <text x="72" y="88" font-family="'JetBrains Mono',monospace" font-size="11" fill="#64748b">@isaac-sun · UNNC</text>
{body}</svg>
'''


# ---------------------------------------------------------------------------
# Card 3: top languages (real byte breakdown)
# ---------------------------------------------------------------------------
def render_languages(totals):
    items = sorted(totals.items(), key=lambda kv: kv[1], reverse=True)[:7]
    grand = sum(v for _, v in items) or 1
    row_h = 26
    top = 52
    h = top + len(items) * row_h + 14
    body = ""
    y = top
    for name, bytes_ in items:
        pct = bytes_ / grand * 100
        color = LANG_COLORS.get(name, "#64748b")
        w = max(6, pct / 100 * 340)
        body += f'''  <text x="20" y="{y+4}" font-family="'JetBrains Mono',monospace" font-size="12" fill="#e2e8f0">{esc(name)}</text>
  <rect x="20" y="{y+10}" width="340" height="8" rx="4" fill="#0b1626"/>
  <rect x="20" y="{y+10}" width="{w:.1f}" height="8" rx="4" fill="{color}"/>
  <text x="372" y="{y+4}" text-anchor="end" font-family="'JetBrains Mono',monospace" font-size="12" font-weight="700" fill="{color}">{pct:.1f}%</text>
'''
        y += row_h
    return f'''<svg width="400" height="{h}" viewBox="0 0 400 {h}" xmlns="http://www.w3.org/2000/svg" role="img" aria-label="Top languages">
  <defs>
    <linearGradient id="bg" x1="0" y1="0" x2="1" y2="1">
      <stop offset="0%" stop-color="#06101f"/>
      <stop offset="100%" stop-color="#0b1224"/>
    </linearGradient>
    <linearGradient id="neon" x1="0" y1="0" x2="1" y2="0">
      <stop offset="0%" stop-color="#22d3ee"/>
      <stop offset="100%" stop-color="#4ade80"/>
    </linearGradient>
  </defs>
  <rect width="400" height="{h}" rx="14" fill="url(#bg)" stroke="url(#neon)" stroke-opacity="0.5" stroke-width="1.5"/>
  <text x="20" y="28" font-family="'JetBrains Mono','Fira Code',monospace" font-size="12" fill="#94a3b8" letter-spacing="1">isaac@github :: languages</text>
  <line x1="20" y1="40" x2="380" y2="40" stroke="#1e293b" stroke-width="1"/>
{body}</svg>
'''


def main():
    print("Fetching contribution calendar...")
    total, days = get_contrib()
    print("Fetching stats...")
    stats = get_stats()
    print("Fetching language breakdown...")
    langs = get_languages(stats)

    import os
    os.makedirs(ASSETS, exist_ok=True)
    open(f"{ASSETS}/activity-graph.svg", "w").write(render_activity(total, days))
    open(f"{ASSETS}/stats-overview.svg", "w").write(render_stats(stats))
    open(f"{ASSETS}/stats-languages.svg", "w").write(render_languages(langs))
    print(f"Wrote 3 cards. total_contrib={total}, repos={stats['repos']}, "
          f"stars={stats['stars']}, langs={len(langs)}")


if __name__ == "__main__":
    main()
