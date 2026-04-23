# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Commands

```bash
npm start        # Start dev server (auto-opens browser, live reload)
npm run build    # Build for production to ./dist/
```

There are no tests configured (`npm test` will error).

## Architecture

Static webcam testing utility hosted on GitHub Pages. No backend, no runtime dependencies — all functionality uses native browser WebRTC APIs.

**Build pipeline**: Webpack bundles `./js/app.js` (intentionally empty — all page logic lives as inline `<script>` in each HTML file) → `./dist/`. Production build uses HtmlWebpackPlugin for `index.html` and CopyPlugin for static assets. **Important**: non-index HTML pages are NOT automatically copied — each must be explicitly added to the `CopyPlugin` patterns in `webpack.config.prod.js`.

**Page structure**: Each HTML file is a standalone page (no routing framework). Pages are self-contained with inline styles and inline JS. Bootstrap 5.3.3 + Bootstrap Icons 1.11.1 loaded from CDN. The pages are:
- `index.html` — homepage/landing
- `show-webcam.html` — detailed camera info
- `take-photo.html` — photo capture
- `mirror.html` — webcam mirror/stream viewer
- `fps-checker.html` — frame rate testing
- `resolution-tester.html` — resolution testing
- `webcam-recorder.html` — record webcam video (Hub A)
- `webcam-effects.html` — live camera filters
- `webcam-gif.html` — animated GIF maker
- `webcam-timelapse.html` — timelapse capture
- `webcam-quality-test.html` — image quality analysis
- `webcam-zoom-test.html` — digital zoom test
- `webcam-brightness-test.html` — brightness/exposure test
- `webcam-color-test.html` — colour accuracy test
- `camera-comparison.html` — side-by-side camera comparison
- `webcam-lighting-test.html` — lighting conditions test
- `webcam-grid-overlay.html` — rule-of-thirds grid, crosshair and face guide overlay
- `about.html` — about page
- `contact.html` — contact page
- `404.html` — error page (copied via CopyPlugin)

**Adding a new page**: (1) create the HTML file, (2) add a `{ from: 'page.html', to: 'page.html' }` entry in `webpack.config.prod.js` CopyPlugin patterns, (3) update `sitemap.xml`.

**External dependencies (CDN only)**:
- Bootstrap 5.3.3 + Bootstrap Icons 1.11.1
- Google AdSense (`ca-pub-5426315045205785`) — present on all feature pages

**Webpack configs**: `webpack.common.js` (shared), `webpack.config.dev.js` (dev server), `webpack.config.prod.js` (production).

**Editor conventions**: 2-space indents, LF line endings, UTF-8 (enforced by `.editorconfig`).

## Keyword Research (Google Ads — 2026-03-26)

Data source: Google Ads `GenerateKeywordHistoricalMetrics` API, global (no geo filter), English.

### Existing Pages — Primary + Secondary Keywords

| Page | File | Primary Keyword | Vol/mo | Secondary Keywords (also target on same page) | Vol/mo |
|------|------|-----------------|--------|-----------------------------------------------|--------|
| Webcam Test (Home) | `index.html` | webcam test | 368,000 | camera test | 246,000 |
| | | | | online camera | 90,500 |
| | | | | webcam online | 40,500 |
| | | | | camera test online | 14,800 |
| | | | | webcam test online | 14,800 |
| | | | | test my webcam | 14,800 |
| | | | | camera checker | 14,800 |
| | | | | webcam checker | 12,100 |
| | | | | test my camera | 8,100 |
| | | | | camera check online | 2,400 |
| Webcam Mirror | `mirror.html` | webcam mirror | 6,600 | camera mirror | 4,400 |
| | | | | camera mirror online | 2,400 |
| | | | | webcam mirror online | 880 |
| Take Webcam Photo | `take-photo.html` | webcam photo | 8,100 | take photo webcam | 260 |
| | | | | webcam snapshot | 110 |
| | | | | camera snapshot online | 10 |
| Show My Webcam | `show-webcam.html` | webcam viewer | 2,400 | show my webcam | 260 |
| | | | | webcam viewer online | 210 |
| | | | | webcam details | 30 |
| | | | | what webcam do i have | 20 |
| | | | | webcam diagnostic | 10 |
| Webcam Resolution Tester | `resolution-tester.html` | webcam resolution test | 110 | camera resolution test | 40 |
| Webcam FPS Checker | `fps-checker.html` | webcam fps checker | 40 | webcam fps test | 20 |
| | | | | camera fps test | 20 |

### New Tool Ideas

Potential new pages using the same `getUserMedia` + Canvas browser APIs. All LOW competition.

| Tool | Primary Keyword | Vol/mo | Secondary Keywords | Vol/mo | Implementation |
|------|-----------------|--------|--------------------|--------|----------------|
| **Webcam Recorder** | webcam recorder | 14,800 | webcam video recorder | 2,900 | MediaRecorder API — record + download WebM/MP4 |
| | | | webcam recorder online | 390 | |
| **Webcam Effects/Filters** | webcam effects online | 1,600 | webcam filters online | 480 | Canvas + CSS filters (grayscale, sepia, blur, contrast) on live feed |
| | | | blur webcam background | 50 | |
| **Barcode Scanner** | barcode scanner webcam | 1,000 | — | — | Camera feed + JS barcode library (QuaggaJS / ZXing) |
| **QR Code Scanner** | qr code scanner webcam | 170 | — | — | Camera feed + JS QR library (jsQR) |
| **Webcam Quality Test** | webcam quality test | 50 | — | — | Analyze sharpness, noise, color accuracy from canvas pixels |
| **Webcam GIF Maker** | webcam gif maker | 20 | — | — | Capture frames → gif.js to encode animated GIF |
| **Webcam Zoom Test** | webcam zoom test | 10 | — | — | Test digital zoom on live feed |

### Low Volume — Still Worth Building (topical authority)

These have <10/mo volume individually but strengthen the site's topical coverage for "webcam" as a whole. Each page deepens the silo it belongs to and passes topical authority up to its hub.

| Tool | File | Keyword | Implementation |
|------|------|---------|----------------|
| Camera Comparison | `camera-comparison.html` | webcam comparison tool | Side-by-side split view of two cameras |
| Webcam Lighting Test | `webcam-lighting-test.html` | webcam lighting test | Analyse brightness/exposure from canvas |
| Webcam Grid Overlay | `webcam-grid-overlay.html` | webcam grid overlay | Rule-of-thirds grid, crosshair and face guide on live feed |
| Webcam Color Test | `webcam-color-test.html` | webcam color test | Color accuracy analysis from canvas |
| Webcam Timelapse | `webcam-timelapse.html` | webcam timelapse online | Capture frames at intervals → download video |
| Webcam Brightness Test | `webcam-brightness-test.html` | webcam brightness test | Measure and adjust brightness/contrast |

Rotate webcam (170/mo)

---

## Internal Linking Strategy — Advanced Silo

**Status: LIVE as of 2026-04-21.** Script, GitHub Actions workflow, and HTML markers all deployed. First rotation applied for April 2026. Subsequent rotations run automatically on days 1–3 of each month.

Three-level authority silo matching the same architecture used in mic-tests.github.io. Body content links only — nav, footer, and sidebar links are navigational and do not count toward silo structure.

---

### Silo Structure

#### Pillar Page

`index.html` — **"webcam test"** (368,000/mo)

- 1 outgoing body link per month → rotates between the 3 hubs monthly
- All 3 hubs always link **up** to the pillar; anchor rotates monthly among 6 long-tail variants
- The pillar never links directly to supporting pages

**Pillar anchor variants** (used by hub slot_a links pointing up):
`"webcam test"`, `"online webcam test"`, `"free webcam test"`, `"test my webcam"`, `"webcam check online"`, `"test your webcam online"`

---

#### Sub-Silo Hubs (3 hubs)

Each hub has **4 body content slots**:

| Slot | Role | Rotates? |
|------|------|----------|
| `slot_a` | Up to pillar — anchor from 6 long-tail variants | Yes (anchor + sentence) |
| `slot_b` | Left hub neighbour — empty when first in monthly order | Yes |
| `slot_c` | Right hub neighbour — empty when last in monthly order | Yes |
| `slot_d` | Down to first page in this hub's shuffled supporter chain | Yes |

| Hub | File | Primary Keyword | Vol/mo | Status |
|-----|------|----------------|--------|--------|
| **A — Webcam Recorder** | `webcam-recorder.html` | "webcam recorder" | 14,800 | Built — silo markers live |
| **B — FPS Checker** | `fps-checker.html` | "webcam fps checker" | 40 | Built — silo markers live |
| **C — Show My Webcam** | `show-webcam.html` | "webcam viewer" | 2,400 | Built — silo markers live |

---

#### Supporting Pages

Each supporting page has **3 body content slots**:

| Slot | Role | Rotates? |
|------|------|----------|
| `slot_a` | Up to this page's hub — anchor = hub's primary keyword | No (anchor fixed; sentence variant rotates) |
| `slot_b` | prev / next / bridge — depends on position in chain | Yes |
| `slot_c` | next / bridge / empty — depends on position in chain | Yes |

**slot_b / slot_c content by position:**

| Position | slot_b | slot_c |
|----------|--------|--------|
| First in Silo A | next in chain | **empty** (Silo A has no backward bridge) |
| First in Silo B or C | next in chain | backward bridge → last of previous silo |
| Middle | prev in chain | next in chain |
| Last in Silo A or B | prev in chain | forward bridge → first of next silo |
| Last in Silo C | prev in chain | **empty** (Silo C has no forward bridge) |

---

##### Silo A — Capture & Creative Tools (hub: `webcam-recorder.html`)

*Hub keyword: "webcam recorder"*

| # | Page | File | Primary Keyword | Vol/mo | Status |
|---|------|------|----------------|--------|--------|
| 1 | Take Webcam Photo | `take-photo.html` | "webcam photo" | 8,100 | Existing |
| 2 | Webcam Mirror | `mirror.html` | "webcam mirror" | 6,600 | Existing |
| 3 | Webcam Effects | `webcam-effects.html` | "webcam effects online" | 1,600 | Built |
| 4 | Webcam GIF Maker | `webcam-gif.html` | "webcam gif maker" | 20 | Built |
| 5 | Webcam Timelapse | `webcam-timelapse.html` | "webcam timelapse online" | <10 | Built |

---

##### Silo B — Performance & Technical Testing (hub: `fps-checker.html`)

*Hub keyword: "webcam fps checker"*

| # | Page | File | Primary Keyword | Vol/mo | Status |
|---|------|------|----------------|--------|--------|
| 1 | Resolution Tester | `resolution-tester.html` | "webcam resolution test" | 110 | Existing |
| 2 | Webcam Quality Test | `webcam-quality-test.html` | "webcam quality test" | 50 | Built |
| 3 | Webcam Zoom Test | `webcam-zoom-test.html` | "webcam zoom test" | 10 | Built |
| 4 | Webcam Brightness Test | `webcam-brightness-test.html` | "webcam brightness test" | <10 | Built |
| 5 | Webcam Color Test | `webcam-color-test.html` | "webcam color test" | <10 | Built |

---

##### Silo C — Device Info & Scanning (hub: `show-webcam.html`)

*Hub keyword: "webcam viewer"*

| # | Page | File | Primary Keyword | Vol/mo | Status |
|---|------|------|----------------|--------|--------|
| 1 | Camera Comparison | `camera-comparison.html` | "webcam comparison tool" | <10 | Built |
| 2 | Webcam Lighting Test | `webcam-lighting-test.html` | "webcam lighting test" | <10 | Built |
| 3 | Webcam Grid Overlay | `webcam-grid-overlay.html` | "webcam grid overlay" | <10 | Built |

---

#### Bridges Between Silos

Bidirectional. Bridge targets change monthly as the supporter shuffle changes which pages land in first/last positions.

| Bridge | Direction | Notes |
|--------|-----------|-------|
| Silo A ↔ Silo B | last of shuffled A ↔ first of shuffled B | anchor = target page's primary keyword |
| Silo B ↔ Silo C | last of shuffled B ↔ first of shuffled C | anchor = target page's primary keyword |
| Silo C → (none) | last of shuffled C has no forward bridge | Silo C is the final silo |

---

### Page Build Priority Order

All pages are built and silo markers are live. Content writing is next.

| Page | File | Status |
|------|------|--------|
| Webcam Recorder (Hub A) | `webcam-recorder.html` | Built — silo live — content pending |
| Webcam Effects | `webcam-effects.html` | Built — silo live — content pending |
| Webcam GIF Maker | `webcam-gif.html` | Built — silo live — content pending |
| Webcam Timelapse | `webcam-timelapse.html` | Built — silo live — content pending |
| Webcam Quality Test | `webcam-quality-test.html` | Built — silo live — content pending |
| Webcam Zoom Test | `webcam-zoom-test.html` | Built — silo live — content pending |
| Webcam Brightness Test | `webcam-brightness-test.html` | Built — silo live — content pending |
| Webcam Color Test | `webcam-color-test.html` | Built — silo live — content pending |
| Camera Comparison | `camera-comparison.html` | Built — silo live — content pending |
| Webcam Lighting Test | `webcam-lighting-test.html` | Built — silo live — content pending |
| Webcam Grid Overlay | `webcam-grid-overlay.html` | Built — silo live — content pending |

---

### Monthly Rotation System — LIVE

Implemented 2026-04-21. Mirrors the system built for mic-tests.github.io.

#### Script

**File:** `utilities/silo_linking/generate_silo_rotation.py`

```bash
python3 utilities/silo_linking/generate_silo_rotation.py            # apply current month
python3 utilities/silo_linking/generate_silo_rotation.py --dry-run  # preview without writing
python3 utilities/silo_linking/generate_silo_rotation.py --date=2026-06  # apply specific month
```

- Deterministic shuffles via `random.Random(MD5-seed)` — same month always produces same output
- Hub order shuffles monthly → pillar link + hub left/right neighbours rotate
- Supporter order shuffles per silo → prev/next chain + bridge endpoints rotate
- Hub `slot_a` anchor rotates among 6 long-tail "webcam test" variants per hub per month
- 6 sentence templates per anchor keyword (132 sentences total across 22 anchor keywords)
- Script detects first-run (no markers) vs. subsequent runs (update existing markers)

#### GitHub Actions Workflow

**File:** `.github/workflows/silo-rotation.yml`

- Cron: `0 16 1-3 * *` — midnight SGT on days 1, 2, and 3 of each month
- Days 2 and 3 are retry safety nets; idempotent — no diff = no commit
- `workflow_dispatch` with optional `date` input (YYYY-MM) for manual override
- Uses built-in `GITHUB_TOKEN` — no PAT required
- View runs: GitHub → Actions → "Monthly Silo Link Rotation"

#### HTML Comment Markers

Each silo link injected as:
```html
<!-- SILO_START:slot_a -->sentence with <a href="/url">anchor</a><!-- SILO_END:slot_a -->
```

Empty slots (e.g. no left/right hub neighbour) render as `<!-- SILO_START:slot_b --><!-- SILO_END:slot_b -->`.

Inserted after the first `</p>` following the designated heading. All internal links use clean URLs (no `.html`).

#### Injection Target Headings (per page)

The script uses `(heading_tag, heading_text_fragment)` to locate injection points. `None` = first `<p>` after `<h1>`.

| Page | slot_a | slot_b | slot_c | slot_d |
|------|--------|--------|--------|--------|
| `index.html` | after h1 | — | — | — |
| `webcam-recorder.html` | after h1 | "What the Webcam Recorder Captures" | "Webcam Recording Quality" | "Who Uses an Online Webcam Recorder" |
| `fps-checker.html` | after h1 | "What Does FPS Mean for Your Webcam" | "Why Your Webcam FPS Matters" | "How to Improve Your Webcam FPS" |
| `show-webcam.html` | after h1 | "How to Use the Webcam Viewer" | "Why Check Your Webcam Specifications" | "What Your Webcam Details Actually Tell You" |
| `take-photo.html` | after h1 | "How to Take a Webcam Photo Online" | "What Can You Use a Webcam Photo For" | — |
| `mirror.html` | after h1 | "How to Use the Webcam Mirror Online" | "Mirror View vs. Natural View" | — |
| `webcam-effects.html` | after h1 | "Creative Filters and Effects for Your Camera" | "How Live Camera Filters Work in a Browser" | — |
| `webcam-gif.html` | after h1 | "Tips for Making Better Webcam GIFs" | "What to Use Webcam GIFs For" | — |
| `webcam-timelapse.html` | after h1 | "Capture Interval" | "What to Capture — Webcam Timelapse Subject Ideas" | — |
| `resolution-tester.html` | after h1 | "What Is Webcam Resolution" | "What Webcam Resolution Do You Actually Need" | — |
| `webcam-quality-test.html` | after h1 | "What the Quality Metrics Measure" | "Troubleshooting a Low Webcam Quality Score" | — |
| `webcam-zoom-test.html` | after h1 | "Understanding Digital Zoom Quality" | "Practical Use Cases for Webcam Digital Zoom" | — |
| `webcam-brightness-test.html` | after h1 | "What Does Webcam Brightness Mean" | "Why Webcam Brightness Matters" | — |
| `webcam-color-test.html` | after h1 | "Understanding Colour Casts and White Balance" | "How Lighting Affects Your Webcam" | — |
| `camera-comparison.html` | after h1 | "What Can You Compare with Two Webcams" | "When to Use the Webcam Comparison Tool" | — |
| `webcam-lighting-test.html` | after h1 | "What the Lighting Metrics Measure" | "Natural vs. Artificial Light" | — |
| `webcam-grid-overlay.html` | after h1 | "The Three Overlays" | "Who Uses a Webcam Grid Overlay" | — |

#### Rotation Algorithm

1. **Hub slot_a anchor** — each hub independently picks 1 of 6 long-tail pillar variants per month via `MD5(year-month-hub_file-slot_a) % 6`
2. **Hub order shuffle** — `random.Random(MD5(year-month-pillar)).shuffle(HUBS)` → determines pillar link + hub left/right neighbours
3. **Supporter shuffle per silo** — `random.Random(MD5(year-month-silo_N)).shuffle(supporters)` → determines hub down-link + supporter chain order + bridge endpoints
4. **Sentence selection** — `MD5(year-month-source_file-anchor) % 6` → picks 1 of 6 sentence templates

#### Pillar Anchor Variants (hub slot_a pointing up to index.html)

`"webcam test"`, `"online webcam test"`, `"free webcam test"`, `"test my webcam"`, `"webcam check online"`, `"test your webcam online"`

---

## W3 HTML Validator — Pending

All pages should be validated using live URLs via the Nu HTML Checker:
`https://validator.w3.org/nu/?doc=https://webcam-test.github.io/<page-path>`

Example:
- `https://validator.w3.org/nu/?doc=https://webcam-test.github.io/`

No pages have been validated yet. After each deploy, re-run the validator on changed pages to catch any new issues.
