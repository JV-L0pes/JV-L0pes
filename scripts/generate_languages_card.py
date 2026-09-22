"""Generate assets/top-languages-card.svg from the profile owner's repositories.

Uses the GitHub GraphQL API (stdlib only). Private repositories are included
when the token can see them, so the card reflects the real work split.

Token resolution order: GITHUB_TOKEN, GH_TOKEN, SUMMARY_GITHUB_TOKEN, then
`gh auth token` for local runs.
"""

from __future__ import annotations

import datetime as dt
import html
import json
import os
import shutil
import subprocess
import sys
import urllib.error
import urllib.request
from pathlib import Path

LOGIN = "JV-L0pes"
OUTPUT = Path(__file__).resolve().parent.parent / "assets" / "top-languages-card.svg"
API = "https://api.github.com/graphql"
TOP_N = 5

FALLBACK_COLORS = {
    "TypeScript": "#3178C6",
    "JavaScript": "#F1E05A",
    "Python": "#3572A5",
    "HTML": "#E34F26",
    "CSS": "#663399",
    "Java": "#B07219",
    "C#": "#178600",
    "PHP": "#4F5D95",
    "Ruby": "#701516",
    "Go": "#00ADD8",
    "Rust": "#DEA584",
    "Kotlin": "#A97BFF",
    "Dart": "#00B4AB",
    "C++": "#F34B7D",
    "C": "#555555",
    "Shell": "#89E051",
    "Vue": "#41B883",
    "Svelte": "#FF3E00",
    "Jupyter Notebook": "#DA5B0B",
    "R": "#198CE7",
    "Dockerfile": "#384D54",
    "HCL": "#844FBA",
    "PLpgSQL": "#336790",
    "MDX": "#FCB32C",
    "Prisma": "#0C344B",
}

QUERY = """
query($login: String!, $cursor: String) {
  user(login: $login) {
    repositories(
      first: 100
      after: $cursor
      ownerAffiliations: [OWNER]
      isFork: false
      orderBy: {field: PUSHED_AT, direction: DESC}
    ) {
      pageInfo { hasNextPage endCursor }
      nodes {
        languages(first: 25, orderBy: {field: SIZE, direction: DESC}) {
          edges { size node { name color } }
        }
      }
    }
  }
}
"""


def resolve_token() -> str | None:
    for key in ("GITHUB_TOKEN", "GH_TOKEN", "SUMMARY_GITHUB_TOKEN"):
        value = os.environ.get(key)
        if value:
            return value
    if shutil.which("gh"):
        result = subprocess.run(["gh", "auth", "token"], capture_output=True, text=True)
        if result.returncode == 0:
            return result.stdout.strip()
    return None


def request(token: str, cursor: str | None) -> dict:
    payload = json.dumps({"query": QUERY, "variables": {"login": LOGIN, "cursor": cursor}}).encode()
    req = urllib.request.Request(
        API,
        data=payload,
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
            "User-Agent": f"{LOGIN}-profile-readme",
        },
    )
    with urllib.request.urlopen(req, timeout=30) as response:
        body = json.load(response)
    if "errors" in body:
        raise RuntimeError(body["errors"])
    return body["data"]["user"]["repositories"]


def collect_languages(token: str) -> dict[str, int]:
    totals: dict[str, int] = {}
    cursor = None
    while True:
        page = request(token, cursor)
        for repo in page["nodes"]:
            for edge in repo["languages"]["edges"]:
                name = edge["node"]["name"]
                totals[name] = totals.get(name, 0) + edge["size"]
        if not page["pageInfo"]["hasNextPage"]:
            break
        cursor = page["pageInfo"]["endCursor"]
    return totals


def slug(name: str) -> str:
    return "".join(ch.lower() if ch.isalnum() else "-" for ch in name).strip("-")


def build_svg(rows: list[dict], total_bytes: int, updated: str) -> str:
    row_svg = []
    for index, row in enumerate(rows):
        baseline = 94 + index * 33
        width = max(round(row["share"] * 200), 6)
        begin = 0.25 + index * 0.12
        row_svg.append(
            f"""    <g>
      <circle cx="40" cy="{baseline - 5}" r="4.5" fill="{row['color']}" />
      <text class="lang" x="58" y="{baseline}">{html.escape(row['name'])}</text>
      <rect x="200" y="{baseline - 8}" width="200" height="6" rx="3" fill="#16223A" />
      <rect x="200" y="{baseline - 8}" width="{width}" height="6" rx="3" fill="{row['color']}">
        <animate attributeName="width" from="0" to="{width}" dur="0.9s" begin="{begin:.2f}s" fill="freeze" calcMode="spline" keySplines="0.32 0.72 0 1" keyTimes="0;1" />
      </rect>
      <text class="pct" x="444" y="{baseline}" text-anchor="end">{row['pct']}%</text>
    </g>"""
        )

    return f"""<svg width="480" height="276" viewBox="0 0 480 276" fill="none" xmlns="http://www.w3.org/2000/svg" role="img" aria-labelledby="title desc">
  <title id="title">Top languages card</title>
  <desc id="desc">Share of code by language across all owned repositories, updated {updated}.</desc>
  <defs>
    <linearGradient id="tl-core" x1="60" y1="18" x2="430" y2="258" gradientUnits="userSpaceOnUse">
      <stop stop-color="#0B1424" />
      <stop offset="0.55" stop-color="#0A111E" />
      <stop offset="1" stop-color="#0E1B31" />
    </linearGradient>
    <style>
      .kicker {{
        font: 600 12px 'JetBrains Mono', 'Cascadia Code', 'SFMono-Regular', Consolas, monospace;
        fill: #F4B400;
        letter-spacing: 0.24em;
      }}
      .lang {{
        font: 600 13.5px 'JetBrains Mono', 'Cascadia Code', 'SFMono-Regular', Consolas, monospace;
        fill: #E2E8F0;
      }}
      .pct {{
        font: 700 12.5px 'JetBrains Mono', 'Cascadia Code', 'SFMono-Regular', Consolas, monospace;
        fill: #F5F8FC;
      }}
      .note {{
        font: 500 10.5px 'JetBrains Mono', 'Cascadia Code', 'SFMono-Regular', Consolas, monospace;
        fill: #6E7E97;
        letter-spacing: 0.04em;
      }}
    </style>
  </defs>

  <rect x="8" y="8" width="464" height="260" rx="24" fill="#060A12" stroke="#1B2740" />
  <rect x="18" y="18" width="444" height="240" rx="18" fill="url(#tl-core)" />
  <rect x="18" y="18" width="444" height="240" rx="18" stroke="#FFFFFF" stroke-opacity="0.05" />

  <text class="kicker" x="40" y="46">TOP LANGUAGES</text>
  <rect x="40" y="58" width="400" height="1" fill="#1B2740" />
  <rect x="40" y="58" width="120" height="1" fill="#F4B400" fill-opacity="0.55" />

{chr(10).join(row_svg)}

  <rect x="40" y="240" width="400" height="1" fill="#1B2740" />
  <text class="note" x="40" y="258">updated {updated} · by bytes</text>
  <text class="note" x="440" y="258" text-anchor="end">top 5 of all owned repos</text>
</svg>
"""


def main() -> int:
    token = resolve_token()
    if not token:
        print("No GitHub token available.", file=sys.stderr)
        return 1

    totals = collect_languages(token)
    if not totals:
        print("No language data returned.", file=sys.stderr)
        return 1

    total_bytes = sum(totals.values())
    ordered = sorted(totals.items(), key=lambda item: (-item[1], item[0]))[:TOP_N]
    rows = [
        {
            "name": name,
            "color": FALLBACK_COLORS.get(name, "#6E7681"),
            "share": size / total_bytes,
            "pct": round(size / total_bytes * 100),
        }
        for name, size in ordered
    ]

    updated = dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%d")
    svg = build_svg(rows, total_bytes, updated)

    if OUTPUT.exists() and OUTPUT.read_text(encoding="utf-8") == svg:
        print("Card unchanged.")
        return 0

    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(svg, encoding="utf-8", newline="\n")
    print(f"Wrote {OUTPUT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
