#!/usr/bin/env python3
"""Generate section heading SVGs.

Each heading is a lowercase monospace label followed by a hairline rule
that extends to the right edge of the column. The font subset inlined is
only the letters that appear in that specific heading — so each file is
tiny despite carrying its own font.

Headings generated:
  hd-about.svg      hd-stack.svg    hd-projects.svg
  hd-stats.svg      hd-streak.svg   hd-langs.svg
  hd-year.svg       hd-contact.svg

Run once locally after subset_fonts.py.
"""
import base64
import os
import sys

ROOT     = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FONT_DIR = os.path.join(ROOT, "scripts", "fonts")
OUT_DIR  = ROOT

WIDTH    = 620
HEIGHT   = 28
FONT_SZ  = 11
TEXT_Y   = 18
RULE_Y   = TEXT_Y - FONT_SZ * 0.35   # vertically centred on cap-height

INK_LIGHT = "#424a53"
INK_DARK  = "#f0f6fc"
RULE_LIGHT = "#d8dee4"
RULE_DARK  = "#30363d"

HEADINGS = [
    "about",
    "stack",
    "projects",
    "stats",
    "streak",
    "langs",
    "year",
    "contact",
]

# Monospace advance: 0.600 em × 11 px = 6.6 px per character
CHAR_W = 6.6


def load_font_b64():
    path = os.path.join(FONT_DIR, "jbmono-head.woff2")
    if not os.path.exists(path):
        sys.exit(
            f"Font not found: {path}\n"
            "Run: python scripts/subset_fonts.py"
        )
    with open(path, "rb") as f:
        return base64.b64encode(f.read()).decode("ascii")


def build_heading(label, font_b64):
    text_w = len(label) * CHAR_W
    gap = 10            # space between label end and rule start
    rule_x1 = text_w + gap
    rule_x2 = WIDTH - 4

    style = (
        f"@font-face{{font-family:JBMono;font-style:normal;"
        f"font-weight:600;font-display:block;"
        f"src:url(data:font/woff2;base64,{font_b64}) format('woff2')}}"
        f"text{{font-family:JBMono,ui-monospace,monospace;"
        f"font-size:{FONT_SZ}px;font-weight:600;"
        f"fill:{INK_LIGHT};letter-spacing:0.05em}}"
        f"line{{stroke:{RULE_LIGHT};stroke-width:0.5}}"
        f"@media(prefers-color-scheme:dark){{"
        f"text{{fill:{INK_DARK}}}"
        f"line{{stroke:{RULE_DARK}}}"
        f"}}"
    )

    svg = (
        f'<svg xmlns="http://www.w3.org/2000/svg" '
        f'width="{WIDTH}" height="{HEIGHT}" '
        f'viewBox="0 0 {WIDTH} {HEIGHT}" '
        f'role="img" aria-label="{label}">'
        f'<style>{style}</style>'
        f'<text x="0" y="{TEXT_Y}">{label}</text>'
        f'<line x1="{rule_x1:.1f}" y1="{RULE_Y:.1f}" '
        f'x2="{rule_x2}" y2="{RULE_Y:.1f}"/>'
        f'</svg>'
    )
    return svg


def main():
    font_b64 = load_font_b64()
    for label in HEADINGS:
        svg  = build_heading(label, font_b64)
        name = f"hd-{label}.svg"
        path = os.path.join(OUT_DIR, name)
        with open(path, "w", encoding="utf-8") as f:
            f.write(svg)
        kb = os.path.getsize(path) / 1024
        print(f"  {name:25s}  {kb:.1f} KB")

    print(f"\n{len(HEADINGS)} heading SVGs written.")


if __name__ == "__main__":
    main()
