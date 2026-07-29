#!/usr/bin/env python3
"""Draw the profile README's stat graphics from the GitHub GraphQL API.

No third-party services and no dependencies beyond the standard library.

Outputs (all sharing the portrait's visual language):
  stats.svg   hero total + weekly sparkline (column chart)
  streak.svg  current streak + longest streak with date ranges
  langs.svg   top 5 languages by bytes + top 5 by repo count
  year.svg    365 days as one character per day from the portrait ramp

Every SVG:
  * transparent background (works on any GitHub theme)
  * grey ink with dark-mode media query
  * JetBrains Mono, inlined as base64 @font-face
  * left-to-right clipPath reveal with fill="freeze" (no looping)

Env vars:
  GITHUB_TOKEN  required
  GH_LOGIN      user to summarise (default: DEVENWAGH)
  OUT_DIR       where to write SVGs (default: repository root)
"""
import base64
import functools
import json
import os
import sys
import urllib.request
from datetime import date, datetime, timedelta, timezone

API = "https://api.github.com/graphql"

# Pinned to whole UTC days for determinism: two runs minutes apart must
# produce byte-identical output, otherwise nightly diffs commit noise.
# privacy: PUBLIC only — a personal token sees private repos, the workflow
# token doesn't, so without this the language totals disagree.
QUERY = """
query($login: String!, $from: DateTime!, $to: DateTime!) {
  user(login: $login) {
    contributionsCollection(from: $from, to: $to) {
      contributionCalendar {
        totalContributions
        weeks { contributionDays { contributionCount date weekday } }
      }
    }
    repositories(first: 100, ownerAffiliations: OWNER, isFork: false,
                 privacy: PUBLIC) {
      nodes {
        languages(first: 12, orderBy: {field: SIZE, direction: DESC}) {
          edges { size node { name } }
        }
      }
    }
  }
}
"""

# Visual tokens — same ink as the portrait so the page reads as one material.
LIGHT = dict(data="#6e7681", emph="#424a53", dim="#8c959f",
             rule="#d8dee4", surface="#ffffff")
DARK  = dict(data="#c9d1d9", emph="#f0f6fc", dim="#8b949e",
             rule="#30363d", surface="#0d1117")

MONO = ("JBMono,ui-monospace,SFMono-Regular,Menlo,Consolas,"
        "'Liberation Mono',monospace")

ROOT     = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FONT_DIR = os.path.join(ROOT, "scripts", "fonts")
OUT_DIR  = os.environ.get("OUT_DIR", ROOT)

WIDTH  = 620    # every graphic shares one column width
LEFT   = 34     # left inset matching the portrait block
REVEAL = 1.30   # seconds; matches the portrait's typing cadence

RAMP = [" ", ":", "+", "#", "@"]      # 5-step ramp for the year grid
MON  = ["jan", "feb", "mar", "apr", "may", "jun",
        "jul", "aug", "sep", "oct", "nov", "dec"]


# ── font helpers ──────────────────────────────────────────────────────────────

@functools.lru_cache(maxsize=None)
def _font_b64(filename):
    path = os.path.join(FONT_DIR, filename)
    if not os.path.exists(path):
        sys.exit(
            f"Font not found: {path}\n"
            "Run: python scripts/subset_fonts.py"
        )
    with open(path, "rb") as f:
        return base64.b64encode(f.read()).decode("ascii")


def _face(filename, weight):
    b64 = _font_b64(filename)
    return (
        f"@font-face{{font-family:JBMono;font-style:normal;"
        f"font-weight:{weight};font-display:block;"
        f"src:url(data:font/woff2;base64,{b64}) format('woff2')}}"
    )


def font_text():
    """Regular + semibold for the data graphics."""
    return _face("jbmono-400.woff2", 400) + _face("jbmono-600.woff2", 600)


def font_head():
    """Only the letters the section headings use."""
    return _face("jbmono-head.woff2", 600)


# ── data fetching ─────────────────────────────────────────────────────────────

def _window():
    today = datetime.now(timezone.utc).date()
    start = today - timedelta(days=364)
    return (f"{start.isoformat()}T00:00:00Z",
            f"{today.isoformat()}T23:59:59Z")


def fetch(login, token):
    since, until = _window()
    body = json.dumps({
        "query": QUERY,
        "variables": {"login": login, "from": since, "to": until}
    }).encode()
    req = urllib.request.Request(
        API, data=body,
        headers={
            "Authorization": f"bearer {token}",
            "Content-Type": "application/json",
            "User-Agent": f"{login}-profile-stats",
        })
    with urllib.request.urlopen(req, timeout=30) as r:
        payload = json.load(r)
    if "errors" in payload:
        raise SystemExit(f"GraphQL errors: {payload['errors']}")
    user = (payload.get("data") or {}).get("user")
    if not user:
        raise SystemExit(f"No such user: {login}")
    return user


def _pretty(iso):
    d = date.fromisoformat(iso)
    return f"{MON[d.month - 1]} {d.day}"


def streaks(days):
    """Current and longest runs of days with ≥1 contribution.

    A zero on the final day (today) doesn't break the current streak —
    the day isn't over yet.
    """
    best = dict(length=0, start=None, end=None)
    run, run_start = 0, None
    for d in days:
        if d["contributionCount"] > 0:
            run += 1
            run_start = run_start or d["date"]
            if run > best["length"]:
                best = dict(length=run, start=run_start, end=d["date"])
        else:
            run, run_start = 0, None

    cur = dict(length=0, start=None, end=None)
    tail = days[:-1] if days and days[-1]["contributionCount"] == 0 else days
    for d in reversed(tail):
        if d["contributionCount"] == 0:
            break
        cur["length"] += 1
        cur["start"] = d["date"]
        cur["end"] = cur["end"] or d["date"]
    return cur, best


def languages(repos):
    by_size, by_repo = {}, {}
    for node in repos:
        edges = (node.get("languages") or {}).get("edges") or []
        for e in edges:
            name = e["node"]["name"]
            by_size[name] = by_size.get(name, 0) + e["size"]
        if edges:
            top = edges[0]["node"]["name"]
            by_repo[top] = by_repo.get(top, 0) + 1

    def rank(d):
        return sorted(d.items(), key=lambda kv: (-kv[1], kv[0]))[:5]

    return rank(by_size), rank(by_repo)


def summarise(user):
    cal   = user["contributionsCollection"]["contributionCalendar"]
    weeks = [w["contributionDays"] for w in cal["weeks"]]
    days  = [d for w in weeks for d in w]
    weekly = [sum(d["contributionCount"] for d in w) for w in weeks]
    cur, best  = streaks(days)
    by_size, by_repo = languages(user["repositories"]["nodes"])
    return dict(
        total=cal["totalContributions"],
        weeks=weekly,
        days=days,
        cur_streak=cur,
        best_streak=best,
        by_size=by_size,
        by_repo=by_repo,
    )


# ── SVG primitives ────────────────────────────────────────────────────────────

def _reveal_clip(svg_w, height, delay, clip_id):
    """One clipPath that wipes left-to-right."""
    return (
        f'<clipPath id="{clip_id}">'
        f'<rect width="0" height="{height}">'
        f'<animate attributeName="width" from="0" to="{svg_w}" '
        f'dur="{REVEAL}s" begin="{delay}s" fill="freeze"/>'
        f'</rect>'
        f'</clipPath>'
    )


def _svg_wrap(content, width, height, style):
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" '
        f'width="{width}" height="{height}" '
        f'viewBox="0 0 {width} {height}" '
        f'role="img">'
        f'<style>{style}</style>'
        f'{content}'
        f'</svg>'
    )


def _base_style(extra=""):
    L, D = LIGHT, DARK
    return (
        font_text() +
        f"text{{font-family:{MONO};font-size:12px;fill:{L['data']}}}"
        f".emph{{fill:{L['emph']};font-weight:600}}"
        f".dim{{fill:{L['dim']}}}"
        f"line{{stroke:{L['rule']}}}"
        f"rect.bar{{fill:{L['data']}}}"
        f"@media(prefers-color-scheme:dark){{"
        f"text{{fill:{D['data']}}}"
        f".emph{{fill:{D['emph']}}}"
        f".dim{{fill:{D['dim']}}}"
        f"line{{stroke:{D['rule']}}}"
        f"rect.bar{{fill:{D['data']}}}"
        f"}}"
        + extra
    )


# ── stats.svg ─────────────────────────────────────────────────────────────────

def build_stats(total, weekly):
    """Hero total + weekly contribution sparkline (column chart)."""
    H = 110
    # sparkline area
    SP_X = LEFT
    SP_Y = 54
    SP_W = WIDTH - LEFT - 20
    SP_H = 36

    max_w = max(weekly) if weekly else 1
    bar_w = SP_W / max(len(weekly), 1)

    bars = []
    for i, v in enumerate(weekly):
        bh = int((v / max_w) * SP_H) if max_w else 0
        x = SP_X + i * bar_w + bar_w * 0.1
        y = SP_Y + SP_H - bh
        bars.append(
            f'<rect class="bar" x="{x:.1f}" y="{y:.0f}" '
            f'width="{bar_w*0.8:.1f}" height="{bh:.0f}"/>'
        )

    label_y = SP_Y + SP_H + 14
    content = (
        f'<defs>{_reveal_clip(WIDTH, H, 0, "c0")}</defs>'
        f'<g clip-path="url(#c0)">'
        f'<text x="{LEFT}" y="22" class="emph" '
        f'style="font-size:28px">{total}</text>'
        f'<text x="{LEFT + 80}" y="22" '
        f'style="font-size:12px"> contributions in the last year</text>'
        f'{"".join(bars)}'
        f'<text x="{LEFT}" y="{label_y}" class="dim" '
        f'style="font-size:10px">weekly activity</text>'
        f'</g>'
    )
    return _svg_wrap(content, WIDTH, H, _base_style())


# ── streak.svg ────────────────────────────────────────────────────────────────

def build_streak(cur, best):
    """Current streak + longest streak, with date ranges."""
    H = 80
    MID = WIDTH // 2

    def streak_block(x, label, length, start, end, clip_id, delay):
        date_txt = (
            f"{_pretty(start)} – {_pretty(end)}"
            if start and end else "—"
        )
        return (
            f'<defs>{_reveal_clip(MID - 10, H, delay, clip_id)}</defs>'
            f'<g clip-path="url(#{clip_id})" transform="translate({x},0)">'
            f'<text x="0" y="14" class="dim" style="font-size:10px">{label}</text>'
            f'<text x="0" y="50" class="emph" style="font-size:36px">'
            f'{length}</text>'
            f'<text x="0" y="66" class="dim" style="font-size:10px">{date_txt}</text>'
            f'</g>'
        )

    content = (
        streak_block(LEFT, "current streak", cur["length"],
                     cur["start"], cur["end"], "c0", 0) +
        streak_block(MID, "longest streak", best["length"],
                     best["start"], best["end"], "c1", 0.3) +
        f'<line x1="{MID - 10}" y1="10" x2="{MID - 10}" y2="{H - 10}" '
        f'stroke-width="1" stroke-dasharray="2,2"/>'
    )
    return _svg_wrap(content, WIDTH, H, _base_style())


# ── langs.svg ─────────────────────────────────────────────────────────────────

def build_langs(by_size, by_repo):
    """Top 5 by bytes (left) + top 5 by repo count (right)."""
    H = 130
    MID = WIDTH // 2
    BAR_H = 6
    ROW_H = 20
    BAR_W = (MID - LEFT - 30)

    def col(items, x, title, unit_fn, clip_id, delay):
        if not items:
            return (
                f'<defs>{_reveal_clip(MID, H, delay, clip_id)}</defs>'
                f'<g clip-path="url(#{clip_id})" transform="translate({x},0)">'
                f'<text x="0" y="14" class="dim" style="font-size:10px">{title}</text>'
                f'</g>'
            )
        top_val = items[0][1]
        rows = []
        for i, (name, val) in enumerate(items):
            y = 28 + i * ROW_H
            bw = int((val / top_val) * BAR_W) if top_val else 0
            rows.append(
                f'<text x="0" y="{y}" style="font-size:10px">{name}</text>'
                f'<text x="{BAR_W + 5}" y="{y}" class="dim" '
                f'style="font-size:9px;text-anchor:end">{unit_fn(val)}</text>'
                f'<rect class="bar" x="0" y="{y + 3}" '
                f'width="{bw}" height="{BAR_H}" rx="2"/>'
            )
        return (
            f'<defs>{_reveal_clip(MID, H, delay, clip_id)}</defs>'
            f'<g clip-path="url(#{clip_id})" transform="translate({x},0)">'
            f'<text x="0" y="14" class="dim" style="font-size:10px">{title}</text>'
            + "".join(rows) +
            f'</g>'
        )

    def fmt_bytes(b):
        if b >= 1_000_000:
            return f"{b/1_000_000:.1f}M"
        if b >= 1_000:
            return f"{b/1_000:.0f}K"
        return str(b)

    content = (
        col(by_size, LEFT, "by bytes", fmt_bytes, "c0", 0) +
        col(by_repo, MID, "by repo count", lambda v: str(v), "c1", 0.3) +
        f'<line x1="{MID - 10}" y1="8" x2="{MID - 10}" y2="{H - 8}" '
        f'stroke-width="1" stroke-dasharray="2,2"/>'
    )
    return _svg_wrap(content, WIDTH, H, _base_style())


# ── year.svg ──────────────────────────────────────────────────────────────────

def build_year(days):
    """365 days, one ramp character per day, in a 7-row grid."""
    CELL_W = 9.6
    CELL_H = 14.0
    GUTTER_LEFT = 26  # room for weekday labels
    LABEL_Y_OFF = 10  # month label row height

    # align to Monday-first weeks
    # days are already ordered oldest→newest from GraphQL
    cols = (len(days) + 6) // 7
    H = int(LABEL_Y_OFF + 7 * CELL_H + 10)
    W = int(GUTTER_LEFT + cols * CELL_W + 20)

    # max contributions for ramp mapping
    max_c = max((d["contributionCount"] for d in days), default=1) or 1

    def char_for(count):
        idx = int((count / max_c) * (len(RAMP) - 1))
        return RAMP[min(idx, len(RAMP) - 1)]

    cells = []
    month_labels = {}

    for flat_i, d in enumerate(days):
        col_i = flat_i // 7
        row_i = flat_i % 7
        x = GUTTER_LEFT + col_i * CELL_W
        y = LABEL_Y_OFF + row_i * CELL_H + CELL_H * 0.85
        c = char_for(d["contributionCount"])
        cells.append(
            f'<text x="{x:.1f}" y="{y:.1f}" '
            f'style="font-size:{CELL_H * 0.75:.1f}px">{c}</text>'
        )
        # first day of each month → label
        if d["date"][8:10] == "01":
            iso_m = int(d["date"][5:7])
            month_labels[col_i] = MON[iso_m - 1]

    # weekday labels
    WD = ["M", "", "W", "", "F", "", "S"]
    wday_labels = []
    for r, lbl in enumerate(WD):
        if lbl:
            y = LABEL_Y_OFF + r * CELL_H + CELL_H * 0.85
            wday_labels.append(
                f'<text x="{GUTTER_LEFT - 4}" y="{y:.1f}" '
                f'class="dim" style="font-size:9px;text-anchor:end">{lbl}</text>'
            )

    mlabels = []
    for col_i, lbl in sorted(month_labels.items()):
        x = GUTTER_LEFT + col_i * CELL_W
        mlabels.append(
            f'<text x="{x:.1f}" y="{LABEL_Y_OFF - 2}" '
            f'class="dim" style="font-size:9px">{lbl}</text>'
        )

    content = (
        f'<defs>{_reveal_clip(W, H, 0, "c0")}</defs>'
        f'<g clip-path="url(#c0)">'
        + "".join(wday_labels)
        + "".join(mlabels)
        + "".join(cells)
        + f'</g>'
    )
    return _svg_wrap(content, W, H, _base_style())


# ── main ──────────────────────────────────────────────────────────────────────

def write(filename, svg):
    path = os.path.join(OUT_DIR, filename)
    with open(path, "w", encoding="utf-8") as f:
        f.write(svg)
    print(f"  {filename:20s}  {os.path.getsize(path) // 1024} KB")


def main():
    token = os.environ.get("GITHUB_TOKEN")
    if not token:
        sys.exit("GITHUB_TOKEN env var is required.")
    login = os.environ.get("GH_LOGIN", "DEVENWAGH")

    print(f"Fetching data for {login} …")
    user = fetch(login, token)
    data = summarise(user)

    print(f"  total={data['total']}  weeks={len(data['weeks'])}  "
          f"days={len(data['days'])}")
    print(f"  cur_streak={data['cur_streak']['length']}  "
          f"best_streak={data['best_streak']['length']}")

    print("\nWriting SVGs:")
    write("stats.svg",  build_stats(data["total"], data["weeks"]))
    write("streak.svg", build_streak(data["cur_streak"], data["best_streak"]))
    write("langs.svg",  build_langs(data["by_size"], data["by_repo"]))
    write("year.svg",   build_year(data["days"]))

    print("\nDone.")


if __name__ == "__main__":
    main()
