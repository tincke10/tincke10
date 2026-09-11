#!/usr/bin/env python3
"""Render the profile README as a terminal session SVG, in the martinmoreira.site look.

Reads pinned repositories and the contribution calendar from the GitHub GraphQL
API and writes:
  session.svg      the terminal session (one image, JetBrains Mono embedded)
  pills/<name>.svg one small linked pill per pinned repo and per contact link
  README.md        the image plus the linked pills

Environment: GITHUB_TOKEN (or METRICS_TOKEN) with read access to the profile.
"""
from __future__ import annotations

import base64
import datetime as dt
import json
import os
import sys
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
LOGIN = "tincke10"
W = 808
BODY_PAD_X, BODY_PAD_Y = 26, 22
FONT_PX, LINE_H = 13, 23
CHAR_W = FONT_PX * 0.6  # JetBrains Mono advance width
COLS = int((W - 2 * BODY_PAD_X) // CHAR_W)  # characters per line
BAR_H = 38

BG_TOP, BG_BOTTOM, RULE = "#0d1014", "#0a0b0d", "#1f2227"
INK, INK_MUTED, INK_DIM = "#d4d4d2", "#8b8d8a", "#5a5c59"
LIME, BLUE = "#b6f569", "#6ab8ff"
LEVELS = ["#1c2025", "#2a3b17", "#4a6b22", "#7fb03a", "#b6f569"]
LEVEL_NAMES = ["NONE", "FIRST_QUARTILE", "SECOND_QUARTILE", "THIRD_QUARTILE", "FOURTH_QUARTILE"]

CONTACT = [
    ("linkedin", "https://www.linkedin.com/in/moreiramartin"),
    ("dev.to", "https://dev.to/tincke10"),
    ("martinmoreira.site", "https://martinmoreira.site"),
]
NOW_LINES = [
    "shipping AI agents and RAG pipelines that actually run in prod",
    "cloud-native backends on AWS: multi-tenant SaaS, event-driven where it pays off",
    "writing it down on dev.to when it is worth it",
]
WHOAMI = "martin · software engineer | innovation engineering · buenos aires, ar"

QUERY = """
{ user(login: "%s") {
    pinnedItems(first: 6, types: REPOSITORY) { nodes { ... on Repository { name description url } } }
    contributionsCollection { contributionCalendar { totalContributions weeks { contributionDays { contributionLevel } } } }
} }
""" % LOGIN


def esc(s: str) -> str:
    return (s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;").replace('"', "&quot;"))


def truncate(s: str | None, n: int) -> str:
    s = (s or "").strip()
    return s if len(s) <= n else s[: n - 1].rstrip() + "…"


def level_color(level: str) -> str:
    return LEVELS[LEVEL_NAMES.index(level)] if level in LEVEL_NAMES else LEVELS[0]


def repo_lines(repos: list[dict], cols: int = COLS) -> list[str]:
    names = [r["name"].lower() + "/" for r in repos]
    col = max(len(n) for n in names) + 3
    return [n.ljust(col) + truncate(r.get("description"), cols - col) for n, r in zip(names, repos)]


# ---------- SVG building blocks ----------

def _font_css(font_b64: str) -> str:
    return ("@font-face{font-family:'JBM';src:url(data:font/woff2;base64,%s) format('woff2');font-weight:400}"
            ".t{font-family:'JBM',ui-monospace,SFMono-Regular,Menlo,Consolas,monospace;font-size:%dpx;fill:%s}"
            % (font_b64, FONT_PX, INK))


def _text(y: float, parts: list[tuple[str, str]], x: float = BODY_PAD_X) -> str:
    spans = "".join(f'<tspan fill="{color}">{esc(text)}</tspan>' for text, color in parts)
    return f'<text class="t" x="{x}" y="{y:.1f}" xml:space="preserve">{spans}</text>'


def _bar(width: int, right_label: str) -> str:
    dots = "".join(f'<circle cx="{16 + 5.5 + i * 17}" cy="{BAR_H / 2}" r="5.5" fill="{c}"/>'
                   for i, c in enumerate(("#ff5f56", "#ffbd2e", "#27c93f")))
    return (f'<rect x="0.5" y="0.5" width="{width - 1}" height="{BAR_H}" fill="#ffffff" fill-opacity="0.02"/>'
            f'<line x1="0" y1="{BAR_H + 0.5}" x2="{width}" y2="{BAR_H + 0.5}" stroke="{RULE}"/>'
            f'{dots}'
            f'<text class="t" x="{16 + 3 * 17 + 8}" y="{BAR_H / 2 + 4}" font-size="11" fill="{INK_DIM}">~/martin — zsh — 92×24</text>'
            f'<text class="t" x="{width - 16}" y="{BAR_H / 2 + 4}" font-size="11" fill="{INK_DIM}" text-anchor="end">{esc(right_label)}</text>')


def _calendar(weeks: list[dict], x: float, y: float, cell: int = 10, gap: int = 3) -> tuple[str, int]:
    rects = []
    for c, week in enumerate(weeks):
        for r, day in enumerate(week["contributionDays"]):
            rects.append(f'<rect x="{x + c * (cell + gap):.0f}" y="{y + r * (cell + gap):.0f}" width="{cell}" height="{cell}" rx="2" fill="{level_color(day["contributionLevel"])}"/>')
    return "".join(rects), 7 * (cell + gap) - gap


def session_svg(data: dict, font_b64: str) -> str:
    P, C, M, D, B = LIME, INK, INK_MUTED, INK_DIM, BLUE
    rows: list[list[tuple[str, str]] | str] = []
    rows.append([("$ ", P), ("whoami", C)])
    rows.append([(WHOAMI, C)])
    rows.append([])
    rows.append([("$ ", P), ("cat now.txt", C)])
    rows += [[("# ", M), (line, C)] for line in NOW_LINES]
    rows.append([])
    rows.append([("$ ", P), ("ls ~/code", C)])
    for line in repo_lines(data["pinned"]):
        name, rest = line.split("/", 1)
        rows.append([(name + "/", B), (rest, C)])
    rows.append([])
    rows.append([("$ ", P), ("contributions --last-year", C)])
    rows.append([(f"{data['total']:,} contributions", B), ("  # updated " + data["updated"], D)])
    rows.append("calendar")
    rows.append([])
    rows.append([("$ ", P), ("open " + " ".join(u.removeprefix("https://").removeprefix("www.") for _, u in CONTACT), C)])
    rows.append("cursor")

    body = []
    y = BAR_H + BODY_PAD_Y + FONT_PX
    for row in rows:
        if row == "calendar":
            rects, h = _calendar(data["weeks"], BODY_PAD_X, y - FONT_PX + 4)
            body.append(rects)
            y += h + 8
        elif row == "cursor":
            body.append(_text(y, [("$ ", P)]))
            body.append(f'<rect x="{BODY_PAD_X + 2 * CHAR_W:.1f}" y="{y - FONT_PX + 1}" width="8" height="15" fill="{LIME}"/>')
            y += LINE_H
        else:
            if row:
                body.append(_text(y, row))
            y += LINE_H
    height = int(y - FONT_PX + BODY_PAD_Y)

    return (f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{height}" viewBox="0 0 {W} {height}">'
            f'<style>{_font_css(font_b64)}</style>'
            f'<defs><linearGradient id="bg" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="{BG_TOP}"/><stop offset="1" stop-color="{BG_BOTTOM}"/></linearGradient>'
            f'<clipPath id="r"><rect width="{W}" height="{height}" rx="10"/></clipPath></defs>'
            f'<g clip-path="url(#r)"><rect width="{W}" height="{height}" fill="url(#bg)"/>{_bar(W, "updated " + data["updated"])}{"".join(body)}</g>'
            f'<rect x="0.5" y="0.5" width="{W - 1}" height="{height - 1}" rx="10" fill="none" stroke="{RULE}"/>'
            f'</svg>')


def pill_svg(label: str, font_b64: str) -> str:
    fs, pad, icon, gap, h = 12, 14, 12, 6, 32
    text_w = len(label) * fs * 0.6
    w = int(pad + text_w + gap + icon + pad)
    ix, iy = w - pad - icon, (h - icon) / 2
    return (f'<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" viewBox="0 0 {w} {h}">'
            f'<style>{_font_css(font_b64)}</style>'
            f'<rect x="0.5" y="0.5" width="{w - 1}" height="{h - 1}" rx="16" fill="#14171b" stroke="#2c3036"/>'
            f'<text class="t" x="{pad}" y="{h / 2 + fs * 0.35:.1f}" font-size="{fs}" fill="{INK}">{esc(label)}</text>'
            f'<path d="M{ix + 2.5} {iy + 9.5} L{ix + 9.5} {iy + 2.5} M{ix + 5} {iy + 2.5} H{ix + 9.5} V{iy + 7}" fill="none" stroke="{INK_MUTED}" stroke-width="1.6"/>'
            f'</svg>')


def slug(name: str) -> str:
    return "".join(ch if ch.isalnum() or ch in "-_." else "-" for ch in name.lower())


def readme_md(pinned: list[dict]) -> str:
    links = [(r["name"].lower(), r["url"]) for r in pinned] + CONTACT
    pills = "\n".join(f'  <a href="{url}"><img src="pills/{slug(name)}.svg" alt="{esc(name)}"></a>' for name, url in links)
    return (f'<img src="session.svg" width="{W}" alt="{WHOAMI}">\n\n<p>\n{pills}\n</p>\n')


# ---------- data ----------

def fetch(token: str) -> dict:
    req = urllib.request.Request("https://api.github.com/graphql", data=json.dumps({"query": QUERY}).encode(),
                                 headers={"Authorization": f"bearer {token}", "Content-Type": "application/json",
                                          "User-Agent": "tincke10-profile"})
    with urllib.request.urlopen(req) as resp:
        payload = json.load(resp)
    if "errors" in payload:
        raise SystemExit(f"GraphQL errors: {payload['errors']}")
    user = payload["data"]["user"]
    cal = user["contributionsCollection"]["contributionCalendar"]
    return {"pinned": user["pinnedItems"]["nodes"], "total": cal["totalContributions"],
            "weeks": cal["weeks"], "updated": dt.date.today().isoformat()}


def main() -> int:
    token = os.environ.get("GITHUB_TOKEN") or os.environ.get("METRICS_TOKEN")
    if not token:
        print("GITHUB_TOKEN or METRICS_TOKEN is required", file=sys.stderr)
        return 2
    font_b64 = base64.b64encode((ROOT / "assets" / "JetBrainsMono-latin-400.woff2").read_bytes()).decode()
    data = fetch(token)
    (ROOT / "session.svg").write_text(session_svg(data, font_b64))
    pills = ROOT / "pills"
    pills.mkdir(exist_ok=True)
    for old in pills.glob("*.svg"):
        old.unlink()
    for name, _ in [(r["name"], r["url"]) for r in data["pinned"]] + CONTACT:
        (pills / f"{slug(name)}.svg").write_text(pill_svg(name.lower(), font_b64))
    (ROOT / "README.md").write_text(readme_md(data["pinned"]))
    print(f"rendered session.svg, {len(data['pinned']) + len(CONTACT)} pills, README.md ({data['total']} contributions)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
