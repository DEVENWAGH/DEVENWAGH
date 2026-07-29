#!/usr/bin/env python3
"""One-time font subsetter for the profile's SVGs.

Run once locally after cloning. Requires:
    pip install fonttools brotli

Downloads JetBrains Mono Regular + SemiBold from GitHub releases and
produces four tiny woff2 subsets in scripts/fonts/:

  jbmono-ramp.woff2   13 ASCII ramp characters           ~1.3 KB
  jbmono-head.woff2   letters used in section headings   ~1.4 KB
  jbmono-400.woff2    basic latin, regular weight         ~4.5 KB
  jbmono-600.woff2    basic latin, semibold weight        ~4.5 KB
"""
import os
import sys
import urllib.request
import tempfile
import subprocess

FONTS_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "fonts")
VERSION = "2.304"
BASE_URL = (
    f"https://github.com/JetBrains/JetBrainsMono/releases/download/"
    f"v{VERSION}/"
)

URLS = {
    "JetBrainsMono-Regular.ttf": f"{BASE_URL}JetBrainsMono-{VERSION}.zip",
    "JetBrainsMono-SemiBold.ttf": f"{BASE_URL}JetBrainsMono-{VERSION}.zip",
}

# The 13-character ramp used by the ASCII portrait
RAMP_CHARS = " .`:-=+*cs#%@"

# Letters appearing in section headings (lower-case only):
#   about  stack  stats  streak  langs  year  projects  contact
HEAD_CHARS = set("aboutstckrelngyp")
HEAD_TEXT = "".join(sorted(HEAD_CHARS))

# Basic latin: printable ASCII range
LATIN = "".join(chr(i) for i in range(0x20, 0x7F))


def check_deps():
    try:
        import fontTools  # noqa: F401
    except ImportError:
        sys.exit(
            "fonttools not found. Run: pip install fonttools brotli"
        )
    try:
        import brotli  # noqa: F401
    except ImportError:
        sys.exit("brotli not found. Run: pip install brotli")


def download_font(url, dest_path):
    """Download a single TTF from a direct URL (not a zip)."""
    print(f"  Downloading {os.path.basename(dest_path)} …")
    req = urllib.request.Request(url, headers={"User-Agent": "DEVENWAGH-profile-setup"})
    with urllib.request.urlopen(req, timeout=60) as r, open(dest_path, "wb") as f:
        f.write(r.read())


def subset(ttf_path, out_path, text, weight):
    """Call pyftsubset to create a woff2 subset."""
    from fontTools.subset import main as pyftsubset_main  # type: ignore

    args = [
        ttf_path,
        f"--text={text}",
        "--flavor=woff2",
        "--layout-features=",
        "--no-hinting",
        f"--output-file={out_path}",
    ]
    print(f"  Subsetting → {os.path.basename(out_path)} ({weight}) …")
    pyftsubset_main(args)


def main():
    check_deps()
    os.makedirs(FONTS_DIR, exist_ok=True)

    # Direct TTF URLs for JetBrains Mono from the releases page
    regular_url = (
        f"https://github.com/JetBrains/JetBrainsMono/raw/v{VERSION}/"
        f"fonts/ttf/JetBrainsMono-Regular.ttf"
    )
    semibold_url = (
        f"https://github.com/JetBrains/JetBrainsMono/raw/v{VERSION}/"
        f"fonts/ttf/JetBrainsMono-SemiBold.ttf"
    )

    with tempfile.TemporaryDirectory() as tmp:
        reg_ttf = os.path.join(tmp, "JetBrainsMono-Regular.ttf")
        sem_ttf = os.path.join(tmp, "JetBrainsMono-SemiBold.ttf")

        download_font(regular_url, reg_ttf)
        download_font(semibold_url, sem_ttf)

        subset(reg_ttf,
               os.path.join(FONTS_DIR, "jbmono-ramp.woff2"),
               RAMP_CHARS, 400)

        subset(sem_ttf,
               os.path.join(FONTS_DIR, "jbmono-head.woff2"),
               HEAD_TEXT, 600)

        subset(reg_ttf,
               os.path.join(FONTS_DIR, "jbmono-400.woff2"),
               LATIN, 400)

        subset(sem_ttf,
               os.path.join(FONTS_DIR, "jbmono-600.woff2"),
               LATIN, 600)

    sizes = {}
    for fn in ["jbmono-ramp.woff2", "jbmono-head.woff2",
               "jbmono-400.woff2", "jbmono-600.woff2"]:
        p = os.path.join(FONTS_DIR, fn)
        sizes[fn] = os.path.getsize(p) / 1024

    print("\nFont subsets written to scripts/fonts/:")
    for fn, kb in sizes.items():
        print(f"  {fn:30s}  {kb:.1f} KB")
    total = sum(sizes.values())
    print(f"  {'TOTAL':30s}  {total:.1f} KB")


if __name__ == "__main__":
    main()
