# DEVENWAGH — Self-Generating GitHub Profile

A profile README that generates itself. Animated ASCII portrait, live
contribution stats, streak, top languages, and a year-at-a-glance grid —
all from a nightly GitHub Actions workflow. Zero third-party requests.

## How it works

```
scripts/generate_portrait.py   ──►  ascii.svg      (run once locally)
scripts/generate_headings.py   ──►  hd-*.svg        (run once locally)
scripts/generate_stats.py      ──►  stats.svg       (nightly, in CI)
                                    streak.svg
                                    langs.svg
                                    year.svg
```

Everything is scheduled via `.github/workflows/refresh.yml`.
The portrait is regenerated on demand via `.github/workflows/portrait.yml`.

## First-time setup

### 1 — Clone and enter the repo

```bash
git clone https://github.com/DEVENWAGH/DEVENWAGH.git
cd DEVENWAGH
```

### 2 — Subset the fonts (once)

```bash
pip install fonttools brotli
python scripts/subset_fonts.py
```

This downloads JetBrains Mono (SIL OFL 1.1) and creates four tiny woff2
subsets in `scripts/fonts/`. Total: ~12 KB.

### 3 — Generate heading SVGs (once)

```bash
python scripts/generate_headings.py
```

### 4 — Generate stats SVGs (requires GitHub token)

```bash
export GITHUB_TOKEN=ghp_xxxxxxxxxxxxxxxxxxxx
export GH_LOGIN=DEVENWAGH
python scripts/generate_stats.py
```

### 5 — Generate the portrait (requires a photo)

Add a photo as `photo.jpg` in the repository root. Photo tips:

- **Side-lit**: window at ~45°, one side of face lit, other in shadow
- **Fill the frame**: chin to just above the hair
- **High resolution**: 1200 px+ crop — 320 px headshots fail
- **Plain background**: not black clothes against a dark wall
- **Slight angle**: gives the nose and jaw a shadow edge

Then run:

```bash
pip install pillow numpy opencv-python-headless rembg onnxruntime
python scripts/generate_portrait.py
```

The first run downloads a ~176 MB background-removal model (cached after that).

### 6 — Customise the README

Edit `README.md`:
- Update your social links
- Fill in the projects section (see the comment template)
- Update the about/stack text to describe you

### 7 — Push to GitHub

```bash
git add -A
git commit -m "chore: initial profile"
git push
```

The nightly workflow will keep stats fresh automatically.

## Triggering workflows manually

- **Stats refresh**: Actions → "refresh stats" → Run workflow
- **Portrait regen**: Actions → "regenerate portrait" → Run workflow

## File structure

```
DEVENWAGH/
├── README.md              ← the profile page
├── ascii.svg              ← portrait (generated)
├── stats.svg              ← contribution sparkline (generated nightly)
├── streak.svg             ← streak graphic (generated nightly)
├── langs.svg              ← top languages (generated nightly)
├── year.svg               ← year grid (generated nightly)
├── hd-about.svg           ← section headings (generated once)
├── hd-stack.svg
├── hd-projects.svg
├── hd-stats.svg
├── hd-streak.svg
├── hd-langs.svg
├── hd-year.svg
├── hd-contact.svg
├── scripts/
│   ├── subset_fonts.py        ← one-time font subsetter
│   ├── generate_portrait.py   ← portrait pipeline
│   ├── generate_stats.py      ← stats → SVGs
│   ├── generate_headings.py   ← heading SVGs
│   └── fonts/
│       ├── JetBrainsMono-LICENSE.txt
│       ├── jbmono-ramp.woff2   (after subset_fonts.py)
│       ├── jbmono-head.woff2
│       ├── jbmono-400.woff2
│       └── jbmono-600.woff2
└── .github/
    └── workflows/
        ├── refresh.yml    ← nightly at 05:17 UTC
        └── portrait.yml   ← manual dispatch only
```

## Gotchas

- **A full-page screenshot restarts SMIL.** Use a tall viewport instead when
  verifying — a 56-row portrait takes ~5 s to finish typing.
- **A newly created profile README is cached.** If it doesn't appear on your
  profile, edit it once through the web UI to force a refresh.
- **Don't add `photo.jpg` to git.** It's in `.gitignore`. Upload it
  as a temporary commit, run the workflow, then remove it.
- **The `portrait.yml` workflow** only runs when you manually trigger it —
  it's not in the nightly cron, so it never blocks the stats refresh.

## Credits

- Portrait pipeline approach: ASCII Portrait README Guide
- Typeface: JetBrains Mono, SIL OFL 1.1
- Reference implementation: github.com/andriidrok1
