#!/usr/bin/env python3
"""Generate deterministic SVG assets for the GitHub profile README."""

from __future__ import annotations

import datetime as dt
import html
import json
import os
import urllib.request
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ASSETS = ROOT / "assets"
ASSETS.mkdir(exist_ok=True)

TOKEN = os.environ.get("GITHUB_TOKEN", "")
USERNAME = os.environ.get("GITHUB_USERNAME", "epicdventurer900")

def github_graphql(query: str, variables: dict) -> dict:
    data = json.dumps({"query": query, "variables": variables}).encode()
    request = urllib.request.Request(
        "https://api.github.com/graphql",
        data=data,
        headers={
            "Authorization": f"Bearer {TOKEN}",
            "Content-Type": "application/json",
            "User-Agent": "github-profile-generator",
        },
        method="POST",
    )
    with urllib.request.urlopen(request, timeout=30) as response:
        payload = json.load(response)
    if payload.get("errors"):
        raise RuntimeError(payload["errors"])
    return payload["data"]

QUERY = """
query($login:String!) {
  user(login:$login) {
    name
    login
    bio
    followers { totalCount }
    following { totalCount }
    repositories(
      first:100
      ownerAffiliations:OWNER
      privacy:PUBLIC
      isFork:false
    ) {
      totalCount
      nodes {
        name
        stargazerCount
        primaryLanguage { name }
        languages(first:10, orderBy:{field:SIZE, direction:DESC}) {
          edges { size node { name } }
        }
      }
    }
    contributionsCollection {
      contributionCalendar {
        totalContributions
        weeks {
          contributionDays { date contributionCount }
        }
      }
      commitContributionsByRepository(maxRepositories:100) {
        contributions(first:100) { totalCount }
      }
    }
  }
}
"""

def fetch_stats() -> dict:
    data = github_graphql(QUERY, {"login": USERNAME})["user"]
    days = []
    for week in data["contributionsCollection"]["contributionCalendar"]["weeks"]:
        days.extend(week["contributionDays"])
    days.sort(key=lambda x: x["date"])
    public_repos = data["repositories"]["totalCount"]
    stars = sum(r["stargazerCount"] for r in data["repositories"]["nodes"])
    languages = Counter()
    for repo in data["repositories"]["nodes"]:
        for edge in repo["languages"]["edges"]:
            languages[edge["node"]["name"]] += edge["size"]
    return {
        "name": data["name"] or USERNAME,
        "login": data["login"],
        "bio": data["bio"] or "",
        "followers": data["followers"]["totalCount"],
        "following": data["following"]["totalCount"],
        "repos": public_repos,
        "stars": stars,
        "total_contributions": data["contributionsCollection"]["contributionCalendar"]["totalContributions"],
        "days": days,
        "languages": languages,
    }

def esc(value) -> str:
    return html.escape(str(value), quote=True)

def svg(title: str, body: str, width: int = 900, height: int = 260) -> str:
    return f'''<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">
  <rect width="100%" height="100%" rx="18" fill="#0d1117"/>
  <text x="36" y="48" fill="#58a6ff" font-family="monospace" font-size="22" font-weight="700">{esc(title)}</text>
  {body}
</svg>
'''

def write(name: str, content: str) -> None:
    (ASSETS / name).write_text(content, encoding="utf-8")

def make_header(s):
    write("header.svg", svg(
        "PRAYUKTH SHETTY",
        '<text x="36" y="94" fill="#f0f6fc" font-family="monospace" font-size="20">&gt; FULL-STACK DEVELOPER • PYTHON • CYBERSECURITY</text>'
        '<text x="36" y="132" fill="#8b949e" font-family="monospace" font-size="17">&gt; BUILD • TEST • SECURE • DEPLOY</text>'
        '<text x="36" y="190" fill="#3fb950" font-family="monospace" font-size="16">● PROFILE SYSTEM ONLINE</text>',
        height=225,
    ))

def make_sections():
    for name, label in [
        ("section-about.svg", "ABOUT"),
        ("section-stack.svg", "TECH STACK"),
        ("section-projects.svg", "PROJECTS"),
        ("section-stats.svg", "GITHUB TELEMETRY"),
    ]:
        write(name, svg(label, '<line x1="36" y1="68" x2="864" y2="68" stroke="#30363d"/>', height=90))

def make_stats(s):
    body = (
        f'<text x="36" y="92" fill="#f0f6fc" font-family="monospace" font-size="18">Contributions</text>'
        f'<text x="36" y="122" fill="#58a6ff" font-family="monospace" font-size="26" font-weight="700">{s["total_contributions"]}</text>'
        f'<text x="250" y="92" fill="#f0f6fc" font-family="monospace" font-size="18">Public repos</text>'
        f'<text x="250" y="122" fill="#58a6ff" font-family="monospace" font-size="26" font-weight="700">{s["repos"]}</text>'
        f'<text x="450" y="92" fill="#f0f6fc" font-family="monospace" font-size="18">Stars</text>'
        f'<text x="450" y="122" fill="#58a6ff" font-family="monospace" font-size="26" font-weight="700">{s["stars"]}</text>'
        f'<text x="610" y="92" fill="#f0f6fc" font-family="monospace" font-size="18">Followers</text>'
        f'<text x="610" y="122" fill="#58a6ff" font-family="monospace" font-size="26" font-weight="700">{s["followers"]}</text>'
    )
    write("stats.svg", svg("LIVE PROFILE STATS", body, height=170))

def make_streak(s):
    days = s["days"][-84:]
    values = [d["contributionCount"] for d in days]
    max_v = max(values or [1])
    cells = []
    for i, value in enumerate(values):
        x = 20 + (i % 21) * 40
        y = 72 + (i // 21) * 28
        opacity = 0.12 if value == 0 else min(1.0, 0.25 + value / max_v * 0.75)
        cells.append(f'<rect x="{x}" y="{y}" width="22" height="18" rx="4" fill="#39d353" fill-opacity="{opacity:.2f}"/>')
    write("streak.svg", svg("LAST 12 WEEKS • CONTRIBUTION HEATMAP", "".join(cells), height=205))

def make_languages(s):
    total = sum(s["languages"].values()) or 1
    top = s["languages"].most_common(7)
    rows = []
    for i, (lang, amount) in enumerate(top):
        y = 72 + i * 29
        pct = amount / total * 100
        rows.append(
            f'<text x="36" y="{y}" fill="#f0f6fc" font-family="monospace" font-size="16">{esc(lang)}</text>'
            f'<rect x="190" y="{y-15}" width="520" height="16" rx="8" fill="#21262d"/>'
            f'<rect x="190" y="{y-15}" width="{520*pct/100:.1f}" height="16" rx="8" fill="#58a6ff"/>'
            f'<text x="730" y="{y}" fill="#8b949e" font-family="monospace" font-size="15">{pct:.1f}%</text>'
        )
    write("langs.svg", svg("TOP LANGUAGES • PUBLIC REPOSITORIES", "".join(rows), height=max(130, 95 + len(top)*29)))

def make_year(s):
    year = dt.datetime.now(dt.timezone.utc).year
    months = [0] * 12
    for d in s["days"]:
        if d["date"].startswith(str(year)):
            months[int(d["date"][5:7])-1] += d["contributionCount"]
    max_v = max(months or [1])
    bars = []
    for i, value in enumerate(months):
        x = 35 + i * 70
        h = 120 * value / max_v if max_v else 0
        bars.append(
            f'<rect x="{x}" y="{178-h:.1f}" width="38" height="{h:.1f}" rx="6" fill="#58a6ff"/>'
            f'<text x="{x+19}" y="202" text-anchor="middle" fill="#8b949e" font-family="monospace" font-size="12">{i+1:02d}</text>'
        )
    write("year.svg", svg(f"{year} ACTIVITY • UTC", "".join(bars), height=225))

def make_footer():
    write("footer.svg", svg(
        "KEEP BUILDING • KEEP LEARNING",
        '<text x="36" y="96" fill="#8b949e" font-family="monospace" font-size="16">Automated profile assets • public GitHub data • updated daily</text>',
        height=145,
    ))

def main():
    if not TOKEN:
        raise SystemExit("GITHUB_TOKEN is required.")
    stats = fetch_stats()
    make_header(stats)
    make_sections()
    make_stats(stats)
    make_streak(stats)
    make_languages(stats)
    make_year(stats)
    make_footer()
    print("Generated profile assets successfully.")

if __name__ == "__main__":
    main()
