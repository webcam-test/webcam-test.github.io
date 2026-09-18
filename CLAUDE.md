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

## SEO Batch Pipeline (title/meta description/H1/content/infographics)

As of 2026-09-18, `title`/`meta_description`/`h1`/`content_html` and infographic SVGs are no
longer hand-written per tool — they're generated by the `open-source-on-page-seo-optimizer` repo's
`/seo-optimize` skill (competitor-SERP-driven `title_zone`/`snippet_zone` scoring for the metadata,
Phase 3b for the SVG infographics) and merged in here. That repo is a separate clone/checkout, not
vendored into this one — treat it as an external dependency, same as its own docs recommend.

Three scripts under `utilities/seo_batch/`, meant to run in this order:

1. **`build_keywords_list.py`** — (re)writes `utilities/seo_batch/keywords.txt` (the
   `batch_run.py`-format `Tool Name | search query | output-slug` list), deriving each tool's
   primary keyword from `utilities/silo_linking/generate_silo_rotation.py`'s own `CLUSTERS`/anchor
   data rather than a second hand-maintained list. Re-run this whenever a tool is added/renamed.
   **Only covers the 38 actual interactive-tool pages** — it skips any `site.json` nav_group whose
   `short_label` is "Guides" (currently the 6-page "Camera Reference" group:
   `webcam-not-working-troubleshooting-guide`, `camera-permissions-guide-windows-mac-android-ios`,
   `webcam-resolution-standards-reference`, `camera-test-vs-webcam-test-explained`,
   `webcam-specs-comparison-database`, `use-phone-as-webcam-guide`). Those stay hand-authored —
   see the 2026-09-18 entry below for why.
2. **`run_batch.py --seo-optimizer-dir <path> --dangerously-skip-permissions [--limit N]`** — thin
   wrapper: shells out to that repo's own `scripts/batch_run.py` (using its `bots_venv` if present)
   against `keywords.txt`, then merges every `status: ok` slug's `output/<slug>/` into this repo via
   `merge_seo_output.py`. This is the actual "generate content for the site" step — it runs the
   seo-optimize tool once per tool page and writes the results here. Costs one full Claude Code
   skill session per tool; sanity-check with `--dry-run` or `--limit 1` before running all 44.
   `--merge-only` skips straight to the merge step if `batch_run.py` was already run manually.
3. **`merge_seo_output.py <slug> --seo-output <output/<slug> path>`** — the actual merge, callable
   standalone too. Overwrites `h1`/`meta_description`/`content_html` in
   `src/content/<slug>.json` from that run's `meta.json`/`content.html`, rewrites `content_html`'s
   relative `images/<file>` src attributes to `/images/<slug>/<file>`, and copies the Phase 3b SVGs
   into `src/content_images/<slug>/`. Never touches `slug`, `subtitle`, `card`, `script`, or `faq` —
   those stay hand-authored. `meta.json`'s `title` is only sanity-checked against `h1` (this site
   still has no separate `<title>` tag — see `generate.py`'s docstring), never written anywhere.

`src/content_images/<slug>/*.svg` is a new sibling to `src/content/<slug>.json`, one directory per
tool that has infographics. `generate.py`'s `main()` copies each tool's directory verbatim into
`public/images/<slug>/` on every build (added alongside the existing fonts/favicon/static copy
steps) — SVGs need no minification, so there's no toolchain dependency for this step.

**SVG metadata is deliberately split across the two repos, the same way `passwordhive`/
`power_plug_sockets_project` embed XMP/EXIF into their own images, adapted for SVG (plain XML, no
`piexif` needed) instead of raster:** the seo-optimizer's Phase 3b writes `<title>`/`<desc>`/a
`<metadata>` RDF block with *content-only* fields (`dc:title`/`dc:description`/`dc:subject`) into
every SVG it generates — that pipeline has no concept of "the site" (its output might be explored
standalone, merged here, or seed a site that doesn't exist yet), so it never writes
creator/rights/source/license fields itself. `merge_seo_output.py`'s `stamp_svg_site_metadata()` is
where those site-specific fields (`dc:creator`="WebcamTest", `dc:rights`=copyright line,
`dc:source`=the page's real URL, `xmpRights:WebStatement`=`/terms`) get added, since merging into
*this* repo is the one place that does know there's a real site to attribute the image to. It
handles both shapes: a Phase-3b SVG that already has a `<metadata>` block (site fields get injected
into it) and an older SVG that doesn't (a full block gets built from `infographics.json`'s
`alt`/`caption`, matched by filename).

After merging, rebuild as usual (see Deployment above): `build_data.py` → `generate.py` →
`generate_silo_rotation.py`.

**Validated end-to-end against one tool (`webcam-test-online`) on 2026-09-18** — home page's
`h1`/`meta_description`/`content_html`/3 infographic SVGs were merged from a real
`open-source-on-page-seo-optimizer` output run and rebuilt successfully. Since extended to
`audio-frequency-sweep-20hz-20khz`, `audio-latency-delay-test`, and `front-camera-test-online`
(also 2026-09-18) — real cost per tool observed at $3.15-$4.03.

**Known failure mode found the same day: generated content can mismatch the actual tool.** Two
tools got reverted after review — `is-my-camera-being-used-check` (real tool is a one-click
camera-in-use privacy check; generated content described the flagship live-preview webcam test
instead, down to "review video quality and frame rate" steps that don't exist on this page) and
`camera-test-vs-webcam-test-explained` (real page is a short terminology-explainer that routes to
the right tool; generated content was a full generic webcam-test article, functionally a duplicate
of `webcam-test-online`'s own h1/content). Root cause: for a keyword with no distinct competitor
content niche of its own, `/seo-optimize` writes whatever's actually ranking (generic webcam-test
content) rather than respecting this specific page's real, narrower purpose — it has no visibility
into that purpose, only the keyword. Both were `git checkout`-reverted (uncommitted at the time) and
marked `status: audit_fail` in the seo-optimizer's own `output/_batch/run_log.json` with a reason
noting this is a manual-review finding, not something `audit.py` itself catches — this keeps
`run_batch.py` from silently re-merging the bad content on a future run and keeps `batch_run.py`
from retrying them by default (needs `--retry-failed` or a manual `--force` re-run, ideally with a
more specific `--search-query`).

**Fix applied**: `build_keywords_list.py` now excludes the "Guides" nav_group (6 pages, all
guide/reference/comparison content, not a "run a test" tool — see that script's docstring) from
`keywords.txt` entirely, since every mismatch found so far was that shape of page.
`is-my-camera-being-used-check` is a genuine interactive tool by nav classification, not a guide, so
it stays in `keywords.txt` — its `audit_fail` marker just prevents an unreviewed auto-retry.

**Review process for every future merge, before rebuilding**: compare the tool's existing
hand-authored `subtitle` (ground truth for what it actually does) against the new `h1` and
`content_html` headings. A generated page that reads like a live-preview webcam test when the real
tool is something narrower/different is the exact shape of bug to look for.

**Also verify Silo Linking after any batch content merge — `generate_silo_rotation.py`'s injection
targets are positional, not topic-matched.** `INJECTION_TARGETS` (see that script) recomputes each
tool's real `<h2>` count from the current `content_html` fresh on every run and
`slot_b`/`slot_c`/`slot_d` target the 1st/2nd/3rd real content `<h2>` by position — it's already
defensively coded (`_find_paragraph_end()` returns `None`/skips rather than crashing or overshooting
into the shared `<footer>` when a target heading doesn't exist, per a past bug of exactly that shape
that's already fixed), so a batch-regenerated tool with a different heading structure won't corrupt
anything. But two non-crashing failure modes are real and won't print an error:
1. **Silent link loss** — if a regenerated tool's `content_html` has fewer real `<h2>`s than before,
   it can silently stop receiving one or more incoming cross-links.
2. **Contextual drift** — a link that still lands may now sit under a completely different-themed
   heading than before regeneration (position N is still "there" but is a different topic), reading
   as a non-sequitur even though nothing is technically broken.

After `generate_silo_rotation.py` runs following any batch merge, spot-check the pages whose content
changed: confirm each still has its expected `<!-- SILO_START:slot_x -->` markers in `public/*.html`,
and read the sentence each one landed in to confirm it still makes sense in context.

**Not yet run for the remaining ~34 tool pages** — left for further batch runs.

**Home page (`webcam-test-online`) deliberately held back at its pre-batch, hand-authored version —
not the seo-optimize-generated one.** Timeline:
- **2026-09-15** (`ab45058`) — the home page was already ranking, a few search-term variants were
  found missing, and they were blended into the existing hand-authored copy directly (no full
  rewrite). That's the version currently live.
- **2026-09-18** — the full batch run above regenerated every tool's content via `/seo-optimize`,
  including the home page, and it was merged + tuned like the others (see the validation note
  earlier in this section).
- **Also 2026-09-18, same day** — the home page was reverted back to the `ab45058` version
  (`git show ab45058:src/content/webcam-test-online.json`, plus removing the infographic SVGs that
  version never had) and rebuilt. Reasoning: this specific page already ranks, and a full content
  swap on an already-ranking page is a materially different risk than doing the same on a page with
  no ranking history to lose — worth a deliberate decision, not something to fold into the same
  batch as everything else. The seo-optimize-generated home page content still exists (it's what
  Phase 3c/Phase 4 produced during the 2026-09-18 batch run, described earlier in this section) and
  can be regenerated again the same way if/when there's a decision to make it live — this note is
  the record of *why* it isn't live now, not a statement that the new version is bad.
- **Every other tool page** (the ~31 merged ones) did *not* have this ranking history to protect, so
  they went live with the fresh seo-optimize content directly — this hold-back is specific to the
  home page, not a general policy.

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

**Push access verified working 2026-09-18** — a stale `~/.git-credentials` entry (unrelated to this
repo, left over from cloning a different project) was causing push authentication failures earlier
the same day. Fixed by clearing that file and re-authenticating with a fresh GitHub token entered
directly at git's credential prompt (never pasted into a chat session — treat any token that does
get pasted into one as compromised and revoke it immediately). This line itself is the verification
commit/push for that fix.

## W3 HTML Validator — Pending

All pages should be validated using live URLs via the Nu HTML Checker, once GitHub Pages is
actually serving the new pipeline's output:
`https://validator.w3.org/nu/?doc=https://webcam-test.github.io/<page-path>`

No pages have been validated yet.
