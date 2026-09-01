# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

**WebcamTest** is a static website served from `webcam-test.github.io` (no custom domain — see
"Domain" below). It provides 44 browser-based camera and audio testing tools (webcam test,
microphone test, resolution/FPS checkers, phone-camera tools, hearing test, etc.) using
`getUserMedia`/`MediaRecorder`/Web Audio APIs.

As of 2026-09-01 the site runs on a **JSON-driven build pipeline** (`src/` → `public/`), replacing
the old hand-authored site (Bootstrap 5.3.3 + Webpack, 19 tool/info pages). The old site is
preserved read-only in `legacy-bootstrap-site/`; it is **not** served and should not be edited.

This migration follows the same path `mic-tests.github.io` took to become `mictest.dev` — same
JSON pipeline shape, same "archive the old site, add a GitHub Actions Pages-deploy workflow"
approach. The pipeline itself was originally built and verified as
`individual_websites/webcamtest/` inside a separate monorepo
(`coffee_can_checker_tools_project`), then copied into this repo as a one-time migration. **This
repo is now the source of truth** — future edits (new tools, content changes, template changes)
happen here, not back-ported from that monorepo.

## Domain

Unlike `mic-tests.github.io` → `mictest.dev`, this site is **not** moving to a custom domain — it
stays at `webcam-test.github.io`. `DOMAIN` in `src/build_data.py` is the real, final domain, not a
placeholder; canonical URLs, JSON-LD, `robots.txt`, and `sitemap.xml` all use it as-is. There is no
`CNAME` file and none should be added.

## Deployment

This is a static site with a Python + Node build step (see "Build toolchain" below).

**Build order matters.** Run all three, in this order, whenever `src/content/*.json` changes:

```bash
python3 src/build_data.py                                   # (re)writes src/data/{tools,pages,site}.json from src/content/
python3 src/generate.py                                      # renders src/template*.html + src/data/*.json -> public/ (minified)
python3 utilities/silo_linking/generate_silo_rotation.py     # patches this month's silo links into public/*.html (last step)
```

`generate_silo_rotation.py` must run **after** `generate.py`, not before — it patches the
already-rendered `public/*.html` files in place via comment markers, and never touches
`src/content/`. Running `generate.py` again without re-running the rotation script afterward will
silently wipe the current month's rotation.

Then commit the changes under `public/` (and `src/data/*.json` if `build_data.py` changed them) and
push to `main`. Committing `public/` is still good practice — it's what
`cd public && python3 -m http.server` serves for local preview (see Local Development below) — but
as of the deploy workflow below, it's no longer what's actually live: the production site never
depends on whatever happens to be committed there.

**GitHub Pages deploy — `.github/workflows/deploy.yml`.** On every push to `main` that touches
`src/**`, `utilities/silo_linking/**`, or the workflow file itself (or via manual
`workflow_dispatch`), the workflow runs the exact three-step build order above from scratch on a
clean runner, then publishes the freshly generated `public/` via `actions/deploy-pages`. Because it
always rebuilds from `src/content/` itself rather than trusting the committed `public/` snapshot, a
human forgetting a build-order step locally can no longer leave the *live* site stale.

**⚠️ One-time manual step required, not done yet:** the workflow only takes effect once Pages'
source is switched to "GitHub Actions" in the repo's Settings → Pages — this can't be done via the
API/CLI available in this environment and must be flipped by a repo admin in the GitHub UI. Until
that switch is flipped, check the actual GitHub Pages source setting before assuming what's serving
the production site.

**⚠️ Untested end-to-end in CI.** Unlike `mic-tests.github.io`'s own `deploy.yml` (pure Python, no
extra toolchain), this site's `generate.py` also needs Node + a real Chrome (see "Build toolchain"
below) — `deploy.yml` installs both via `actions/setup-node` and `browser-actions/setup-chrome`, but
the very first run in Actions hasn't been observed yet. Check the Actions tab after the first push
that touches `src/**`.

### Build toolchain

`src/generate.py` minifies HTML/CSS and extracts per-page critical CSS via `critical` (which drives
a real headless Chrome) — the same toolchain as `passwordhive`/`hexcalculator`'s own `generate.py`
in the `coffee_can_checker_tools_project` monorepo (`html-minifier-terser@7.2.0`,
`clean-css-cli@5.6.3`, `tailwindcss@3.4.19` + `@tailwindcss/typography@0.5.20`, `critical@8.0.0`).
Requires Node/`npx`/`npm` on `PATH` and a local Chrome/Chromium install (or
`PUPPETEER_EXECUTABLE_PATH` pointed at one). `python3 src/generate.py --no-minify` skips all of this
for fast local iteration — never commit/deploy that output; it ships an empty critical-CSS block and
an empty `typography.min.css` placeholder (see `coffee_can_checker_tools_project`'s own webcamtest
CLAUDE.md for what shipping that unminified build to production actually breaks).

`getUserMedia`/`AudioContext` both work over plain `http://localhost` — browsers treat localhost as
a secure context — so local testing needs no HTTPS setup. Production (GitHub Pages) is HTTPS by
default.

## Local Development

Serve locally with any HTTP server, pointed at `public/` — not the repo root:

```bash
cd public
python3 -m http.server 8811
```

Extensionless routes (`/microphone-test-online` etc.) only resolve automatically under GitHub
Pages, not under a plain local file server — append `.html` when testing locally (e.g.
`http://localhost:8811/microphone-test-online.html`).

There are no linters or test suites configured.

## Architecture

### JSON-Driven Build Pipeline

Single source of truth per tool, modeled on the `passwordhive`/`hexcalculator` pattern:

- **`src/content/<slug>.json`** — one tool page's *entire* content: `meta_description`, `h1`/
  `subtitle`, the tool card's own interactive markup (`card.fields_html` — every tool uses the
  "raw" card layout, i.e. this field is the tool's entire card grid, not a typed sub-layout),
  `content_html`, `faq`, and that tool's own fully self-contained JS (the `script` field — no
  shared runtime file; every tool's script duplicates whatever device-acquisition/teardown logic
  it needs).
- **`src/content/pages/`** — none currently; the 5 info pages (about/contact/privacy/terms/sitemap)
  are driven by `src/data/pages.json`, itself built from constants in `build_data.py`, not
  individual JSON files.
- **`src/template.html`** — shared template for the 44 tool pages.
- **`src/template-page.html`** — shared template for the 5 info pages.
- **`src/template-404.html`** — the 404 page template.
- **`src/static/`** — binary/opaque assets that can't be derived from `site.json`: currently just
  `googlecb346f17d96186ee.html`, the Google Search Console verification file carried over from the
  old site — **do not modify its contents**, it proves domain ownership. Copied verbatim into
  `public/` by `generate.py` on every build.
- **`src/build_data.py`** — assembles `src/data/{tools,pages,site}.json` from `src/content/`.
  Site-wide constants (`SITE_NAME`, `DOMAIN`, `HOME_SLUG`, `CONTACT_EMAIL`, `OWNER_NAME`, ...) live
  at the top of this file.
- **`src/generate.py`** — renders `src/data/*.json` + the three templates into `public/*.html`,
  plus generates `public/robots.txt`, `public/sitemap.xml`, and `public/ads.txt` (all derived from
  `site.json`/`ADSENSE_CLIENT`, never hand-edited).
- **`public/`** — generated output, committed. Never hand-edit anything here — edit
  `src/content/<slug>.json` (or the template/generator) and rerun the build.

### Card layout: "raw" only

Every tool uses the "raw" card layout — `card["fields_html"]` in that tool's own
`content/<slug>.json` is its **entire** card grid (hero panel + supporting panels). Almost every
tool has a genuinely distinct interactive shape (live video + overlay grid, split-view comparison,
spectrum analyzer, resolution-probe ladder), so there is exactly one Python-side render branch
(`render_tool_card_body()`) to maintain regardless of tool count.

### No shared JS runtime file (deliberate)

Every tool's `script` field is a complete, self-contained IIFE that duplicates whatever it needs
(device acquisition/enumeration/teardown, canvas analysis, tone generation, FFT). A future fix to
teardown/error-mapping logic has to be reapplied in every tool's own `script` field that copied it —
`webcam-test-online.json` is the reference implementation every other camera tool's script copies
its acquisition/enumeration/teardown/error-mapping pattern from; `microphone-test-online.json` or
`speaker-test-online.json` are the equivalent reference for audio tools.

## AdSense

Real ad units carried over from the old `legacy-bootstrap-site/` (client `ca-pub-5426315045205785`,
already an approved, live-serving account for this exact domain — not a fresh unapproved account
like `mictest.dev`'s, so ads are **enabled**, not disabled-pending-approval). Placement logic is
ported from `passwordhive`'s own `render_adsense_*()` functions
(`coffee_can_checker_tools_project/individual_websites/passwordhive/src/generate.py`):

- **Loader** (`render_adsense_loader()`) — in `<head>`, preconnected to
  `pagead2.googlesyndication.com`.
- **Header** (`render_adsense_header()`, slot `6562139351`) — responsive leaderboard between the
  hero and the tool card: 728×90 at ≥768px, 300×100 below that, resized via inline JS.
- **Body** (`render_adsense_body()`, slot `6837554954`) — spliced before a tool's first `<h2>`,
  full-width responsive (`data-ad-format="auto"`), matching how this real unit is already
  configured.
- **Footer** (`render_adsense_footer()`, slot `5068825756`) — fixed 300×250, unconditionally after
  the FAQ section (even on a tool with no `content_html`).

Only 3 real ad units exist for this property (unlike passwordhive's 4) — there's no "body2" slot.
Ads render only on tool pages (via `render_page()`), never on the 5 info pages or 404 (matching
passwordhive's own behavior). `ads.txt` is generated from `ADSENSE_CLIENT` in `generate.py`, not
hand-maintained — it will never drift from the loader/ad-unit markup.

## Silo Linking

`utilities/silo_linking/generate_silo_rotation.py` — a **fully self-contained script**, same
no-shared-core-module shape as `mic-tests.github.io`'s own script (this repo does not import a
shared engine from the `coffee_can_checker_tools_project` monorepo, since it's no longer part of
that monorepo's build).

Two independent pillar clusters — Camera and Audio — covering all 44 tools:

- **Camera** — pillar `webcam-test-online` (`index.html`), 5 sub-silos: `webcam-live-filter-preview`,
  `use-phone-as-webcam-guide`, `webcam-video-recorder-online`, `front-camera-test-online`,
  `webcam-mirror-vs-natural-view-test`.
- **Audio** — pillar `microphone-test-online`, 3 sub-silos: `speaker-test-online`,
  `online-hearing-frequency-test`, `microphone-record-playback-test`.

Per cluster: pillar → 1 rotating link down to a sub-silo; sub-silos → up/left/right/down links;
supporting pages → up to their sub-silo + prev/next in a chain that bridges linearly across the
cluster's supporting groups (no wraparound).

**Anchor text rotates too, not just the sentence.** `ANCHOR_VARIANTS` gives each of the 44 tools 4
hand-picked phrases — the primary keyword itself, a free/online long-tail variation, a secondary/
related phrasing, and a contextual/LSI term grounded in what that specific tool actually measures —
mirroring `passwordhive`'s own `ANCHOR_VARIANTS` pattern (in that project's
`coffee_can_checker_tools_project` monorepo). Unlike passwordhive's mechanical suffix-detection
generator (its keyword vocabulary — "X generator"/"X checker"/"X calculator" — is regular enough
for a formula), camera/audio keywords are too irregular for one blind template (several are
already question-form, e.g. "is my camera on", "what camera do i have" — "free is my camera on"
reads as broken English), so these are hand-picked per tool instead. The variant is chosen per
`(source page, slot)`, same as passwordhive, so the same target page can get a different variant
depending on which page happens to link to it that month — deterministic per month, still varies
across different linking pages. The surrounding sentence (2 families — `live_test`/`guide`) rotates
separately, keyed by family rather than by the literal anchor string (since the anchor itself now
varies) via the same MD5-seeded deterministic shuffle (same month always produces the same output).

Injection targets are computed **per tool**, not hardcoded — every tool-panel header inside the
card is itself an `<h2>` (e.g. "Live Camera Preview"), so a flat h2-index would land inside the tool
card on any page whose card has ≥1 panel heading. The script reads each tool's own
`content/<slug>.json` at load time to count its card's `<h2>`s and computes `heading_index` offsets
from that, so `slot_b`/`slot_c`/`slot_d` always land in the article prose, never inside the card.

Run standalone from the repo root:
```bash
python3 utilities/silo_linking/generate_silo_rotation.py
python3 utilities/silo_linking/generate_silo_rotation.py --dry-run
python3 utilities/silo_linking/generate_silo_rotation.py --date=2026-09
```

**GitHub Actions Workflow — `.github/workflows/silo-rotation.yml`.** Cron `0 16 1-3 * *` (midnight
SGT on the 1st–3rd of each month), plus `workflow_dispatch` with an optional `date` override.
Commits and pushes `public/*.html` directly if the rotation changed anything. Note: this workflow's
own push only touches `public/**`, which is **not** in `deploy.yml`'s trigger paths — so a rotation
commit updates the *committed* `public/` (useful for local preview/history) but doesn't by itself
trigger a live redeploy. `deploy.yml` recomputes the current month's rotation itself as its own last
build step whenever *it* runs, so the live site catches up automatically on the next `src/**` change
or manual `workflow_dispatch` — same accepted behavior as `mic-tests.github.io`'s identical setup.

## Content Authoring

`camera-and-audio-test-tools-specification.xlsx` — the original 44-tool spec (Purpose/How To
Build/JavaScript Considerations/API Browser Risk columns per tool) this site was planned from.
Read it before writing a new tool.

`utilities/tool_buildout/write_<slug>.py` — one throwaway authoring script per built tool: builds
that tool's `src/content/<slug>.json` dict in plain Python (HTML/JS as ordinary triple-quoted
strings) and `json.dump()`s it out. Author new tools this way, not by hand-writing JSON —
hand-escaping multi-line HTML/JS inside a JSON string is exactly the kind of mechanical work that
introduces silent syntax errors. Keep the script after running it so the tool's content stays easy
to revise without re-deriving the HTML/JS from scratch. `progress.json` tracks each tool's build
status; `ui_layout_audit.json` is a one-time layout audit snapshot.

These both predate this repo — recovered from `coffee_can_checker_tools_project`'s git history
(commit `d4d8fef`) after that monorepo's own cleanup commit removed its now-superseded webcamtest
copy; they hadn't made the first copy-over into this repo. `utilities/google_ads_keyword_research/`
— the script + real output spreadsheet the 44 tools' primary keywords (used as both silo-link
anchor text and `/sitemap` link text — see "Silo Linking" above) come from — was recovered the same
way.

## Legacy Site

`legacy-bootstrap-site/` — a frozen, read-only snapshot of the pre-migration hand-authored site: the
original 19 tool/info pages, `css/`, `js/`, `img/`, and the old root-level `ads.txt`/`robots.txt`/
`sitemap.xml`/`site.webmanifest`/`favicon.ico`/`icon.png`/`icon.svg`, plus the old Webpack tooling
(`webpack.*.js`, `package.json`). Kept for reference/history only — it is not linked from the build,
not served, and should not be edited.

## Known Gaps

- **GitHub Pages source not yet switched to "GitHub Actions"** — see Deployment above. The live
  site will keep serving whatever it served before this migration until a repo admin flips that
  setting.
- **`deploy.yml`'s Node/Chrome setup is unverified in CI** — see "Build toolchain" above.
- **`site.webmanifest` was archived, not re-added** — the old one was mostly empty placeholder
  fields (`short_name`/`name` both `""`); this pipeline has no PWA manifest support. Low priority to
  restore unless there's an actual PWA/install-prompt need.

## W3 HTML Validator — Pending

All pages should be validated using live URLs via the Nu HTML Checker, once GitHub Pages is
actually serving the new pipeline's output:
`https://validator.w3.org/nu/?doc=https://webcam-test.github.io/<page-path>`

No pages have been validated yet.
