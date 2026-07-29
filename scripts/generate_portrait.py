#!/usr/bin/env python3
"""Generate the animated ASCII portrait SVG.

Requirements:
    pip install pillow numpy opencv-python-headless rembg onnxruntime

Usage:
    python scripts/generate_portrait.py [photo.jpg]

Input:  photo.jpg (or first argument) in the repository root.
Output: ascii.svg in the repository root.

Pipeline:
  1. rembg removes background → white fill
  2. bilateral filter smooths skin while keeping edges
  3. CLAHE local contrast (clip 3.0, tile 8×8)
  4. darkening curve  v → (v/255)^1.7 * 255
  5. map brightness to 13-char ramp  " .`:-=+*cs#%@"
  6. each row wrapped in <clipPath> with SMIL animate (width 0→full)
  7. block cursor rides the wipe edge
  8. rows stagger top-to-bottom at 0.09 s intervals, fill="freeze"
  9. JetBrains Mono ramp subset inlined as base64 @font-face
"""
import base64
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FONT_DIR = os.path.join(ROOT, "scripts", "fonts")

# ── ramp ──────────────────────────────────────────────────────────────────────
RAMP = " .`:-=+*cs#%@"   # 13 characters, dark → light  (space = blank/bg)
COLS = 90                 # column count; below ~88 faces muddy
CHAR_W = 7.74             # px advance for font-size 12.9  (0.600 em × 12.9)
FONT_SIZE = 12.9
LINE_H = CHAR_W * 2.0    # monospace chars are ~2× taller than wide

INK_LIGHT = "#424a53"     # default ink for light-mode GitHub
INK_DARK = "#c9d1d9"      # switched via media query / prefers-color-scheme

# displayed width of the portrait block
DISPLAY_W = 460


def load_font_b64(filename):
    path = os.path.join(FONT_DIR, filename)
    if not os.path.exists(path):
        sys.exit(
            f"Font subset not found: {path}\n"
            "Run: python scripts/subset_fonts.py"
        )
    with open(path, "rb") as f:
        return base64.b64encode(f.read()).decode("ascii")


def font_face(b64):
    return (
        f"@font-face{{font-family:JBMono;font-style:normal;"
        f"font-weight:400;font-display:block;"
        f"src:url(data:font/woff2;base64,{b64}) format('woff2')}}"
    )


def process_image(photo_path):
    import numpy as np
    import cv2
    from PIL import Image
    from rembg import remove

    # 1. remove background
    with open(photo_path, "rb") as f:
        raw = f.read()
    no_bg = remove(raw)

    img = Image.open(__import__("io").BytesIO(no_bg)).convert("RGBA")

    # paste onto white
    bg = Image.new("RGBA", img.size, (255, 255, 255, 255))
    bg.paste(img, mask=img)
    img = bg.convert("L")  # grayscale

    # 2. resize to COLS wide
    h, w = img.size[1], img.size[0]
    rows = int(COLS * (h / w) * 0.48)
    img = img.resize((COLS, rows), Image.LANCZOS)

    arr = np.array(img, dtype=np.float32)

    # 3. bilateral filter
    arr8 = arr.astype(np.uint8)
    arr8 = cv2.bilateralFilter(arr8, d=9, sigmaColor=75, sigmaSpace=75)

    # 4. CLAHE local contrast
    clahe = cv2.createCLAHE(clipLimit=3.0, tileGridSize=(8, 8))
    arr8 = clahe.apply(arr8)

    # 5. darkening curve
    arr_f = arr8.astype(np.float32) / 255.0
    arr_f = np.power(arr_f, 1.7)
    arr8 = (arr_f * 255).astype(np.uint8)

    # 6. map to ramp (invert: high brightness → early ramp chars → blank)
    n = len(RAMP) - 1
    indices = ((255 - arr8.astype(np.int32)) * n // 255).clip(0, n)
    char_grid = [[RAMP[i] for i in row] for row in indices]

    return char_grid


def escape(s):
    return (s
            .replace("&", "&amp;")
            .replace("<", "&lt;")
            .replace(">", "&gt;")
            .replace('"', "&quot;"))


def build_svg(char_grid):
    rows = len(char_grid)
    cols = len(char_grid[0]) if rows else COLS

    svg_w = CHAR_W * cols
    svg_h = LINE_H * rows

    b64 = load_font_b64("jbmono-ramp.woff2")
    style_css = (
        f"{font_face(b64)}"
        f"text{{font-family:JBMono,ui-monospace,'Liberation Mono',monospace;"
        f"font-size:{FONT_SIZE}px;fill:{INK_LIGHT}}}"
        f"@media(prefers-color-scheme:dark){{text{{fill:{INK_DARK}}}}}"
    )

    lines = []
    lines.append(
        f'<svg xmlns="http://www.w3.org/2000/svg" '
        f'width="{DISPLAY_W}" '
        f'viewBox="0 0 {svg_w:.2f} {svg_h:.2f}" '
        f'role="img" aria-label="ASCII portrait of Deven Wagh">'
    )
    lines.append(f"<style>{style_css}</style>")
    lines.append("<defs>")

    # one clipPath per row
    for i in range(rows):
        clip_id = f"r{i}"
        delay = f"{i * 0.09:.2f}s"
        y_top = i * LINE_H
        lines.append(
            f'<clipPath id="{clip_id}">'
            f'<rect x="0" y="{y_top:.2f}" width="0" height="{LINE_H:.2f}">'
            f'<animate attributeName="width" from="0" to="{svg_w:.2f}" '
            f'dur="0.7s" begin="{delay}" fill="freeze"/>'
            f'</rect>'
            f'</clipPath>'
        )

    lines.append("</defs>")

    # cursor block definition — rides the right edge of each row
    CUR_W = CHAR_W
    CUR_H = LINE_H * 0.85
    lines.append("<defs>")
    for i in range(rows):
        cur_id = f"cur{i}"
        delay = f"{i * 0.09:.2f}s"
        end_delay = f"{i * 0.09 + 0.7:.2f}s"
        y_top = i * LINE_H + (LINE_H - CUR_H) / 2
        lines.append(
            f'<g id="{cur_id}">'
            f'<rect x="0" y="{y_top:.2f}" width="{CUR_W:.2f}" height="{CUR_H:.2f}" '
            f'fill="{INK_LIGHT}" opacity="0">'
            f'<animate attributeName="opacity" values="0;1;0" '
            f'dur="0.7s" begin="{delay}" fill="freeze"/>'
            f'<set attributeName="opacity" to="0" begin="{end_delay}" fill="freeze"/>'
            f'</rect>'
            f'</g>'
        )
    lines.append("</defs>")

    # text rows
    for i, row in enumerate(char_grid):
        text = escape("".join(row))
        y = (i + 1) * LINE_H - (LINE_H - FONT_SIZE) * 0.3
        lines.append(
            f'<text clip-path="url(#r{i})" '
            f'x="0" y="{y:.2f}" '
            f'xml:space="preserve">{text}</text>'
        )
        # cursor overlay
        lines.append(
            f'<use href="#cur{i}"/>'
        )

    lines.append("</svg>")
    return "\n".join(lines)


def main():
    # find photo — accepts any of these filenames in the repo root
    if len(sys.argv) > 1:
        photo = sys.argv[1]
    else:
        candidates = (
            "photo.jpg", "photo.jpeg", "photo.png",
            "image.jpg", "image.jpeg", "image.png",
            "portrait.jpg", "portrait.jpeg", "portrait.png",
            "me.jpg", "me.jpeg", "me.png",
        )
        for name in candidates:
            candidate = os.path.join(ROOT, name)
            if os.path.exists(candidate):
                photo = candidate
                break
        else:
            sys.exit(
                "No photo found. Add image.png (or photo.jpg / me.jpg) to the "
                "repository root, then run:\n"
                "  python scripts/generate_portrait.py"
            )

    print(f"Processing {photo} …")
    char_grid = process_image(photo)
    rows = len(char_grid)
    cols = len(char_grid[0]) if rows else 0
    print(f"  Grid: {cols} cols × {rows} rows")

    svg = build_svg(char_grid)

    out = os.path.join(ROOT, "ascii.svg")
    with open(out, "w", encoding="utf-8") as f:
        f.write(svg)

    size_kb = os.path.getsize(out) / 1024
    print(f"  Written → ascii.svg ({size_kb:.0f} KB)")
    print(f"  Animation: {rows * 0.09:.1f} s to complete typing")


if __name__ == "__main__":
    main()
