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

**Page structure**: Each HTML file is a standalone page (no routing framework). Pages are self-contained with inline styles and inline JS. Bootstrap 5.3.0-alpha1 + Bootstrap Icons 1.11.1 loaded from CDN. The pages are:
- `index.html` — homepage/landing
- `show-webcam.html` — detailed camera info
- `take-photo.html` — photo capture
- `mirror.html` — webcam mirror/stream viewer
- `fps-checker.html` — frame rate testing
- `resolution-tester.html` — resolution testing
- `about.html` — about page
- `contact.html` — contact page
- `404.html` — error page (copied via CopyPlugin)

**Adding a new page**: (1) create the HTML file, (2) add a `{ from: 'page.html', to: 'page.html' }` entry in `webpack.config.prod.js` CopyPlugin patterns, (3) update `sitemap.xml`.

**External dependencies (CDN only)**:
- Bootstrap 5.3.0-alpha1 + Bootstrap Icons 1.11.1
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
| Webcam Framing Guide | `webcam-framing-guide.html` | webcam framing guide | Rule-of-thirds overlay on live feed |
| Webcam Color Test | `webcam-color-test.html` | webcam color test | Color accuracy analysis from canvas |
| Webcam Timelapse | `webcam-timelapse.html` | webcam timelapse online | Capture frames at intervals → download video |
| Webcam Brightness Test | `webcam-brightness-test.html` | webcam brightness test | Measure and adjust brightness/contrast |

Rotate webcam (170/mo) is not recommended — HIGH competition.

---

## Internal Linking Strategy — Advanced Silo

**Status: Planned — not yet implemented. Implementation begins once `webcam-recorder.html` (Hub A) is built.**

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
| **A — Webcam Recorder** | `webcam-recorder.html` | "webcam recorder" | 14,800 | **To build — highest priority** |
| **B — FPS Checker** | `fps-checker.html` | "webcam fps checker" | 40 | Existing |
| **C — Show My Webcam** | `show-webcam.html` | "webcam viewer" | 2,400 | Existing |

> Hub A (`webcam-recorder.html`) must be built before the rotation script can run. Hubs B and C already exist.

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
| 3 | Webcam Effects | `webcam-effects.html` | "webcam effects online" | 1,600 | To build |
| 4 | Webcam GIF Maker | `webcam-gif.html` | "webcam gif maker" | 20 | To build |
| 5 | Webcam Timelapse | `webcam-timelapse.html` | "webcam timelapse online" | <10 | To build |

---

##### Silo B — Performance & Technical Testing (hub: `fps-checker.html`)

*Hub keyword: "webcam fps checker"*

| # | Page | File | Primary Keyword | Vol/mo | Status |
|---|------|------|----------------|--------|--------|
| 1 | Resolution Tester | `resolution-tester.html` | "webcam resolution test" | 110 | Existing |
| 2 | Webcam Quality Test | `webcam-quality-test.html` | "webcam quality test" | 50 | To build |
| 3 | Webcam Zoom Test | `webcam-zoom-test.html` | "webcam zoom test" | 10 | To build |
| 4 | Webcam Brightness Test | `webcam-brightness-test.html` | "webcam brightness test" | <10 | To build |
| 5 | Webcam Color Test | `webcam-color-test.html` | "webcam color test" | <10 | To build |

---

##### Silo C — Device Info & Scanning (hub: `show-webcam.html`)

*Hub keyword: "webcam viewer"*

| # | Page | File | Primary Keyword | Vol/mo | Status |
|---|------|------|----------------|--------|--------|
| 1 | Barcode Scanner | `barcode-scanner.html` | "barcode scanner webcam" | 1,000 | To build |
| 2 | QR Code Scanner | `qr-scanner.html` | "qr code scanner webcam" | 170 | To build |
| 3 | Camera Comparison | `camera-comparison.html` | "webcam comparison tool" | <10 | To build |
| 4 | Webcam Lighting Test | `webcam-lighting-test.html` | "webcam lighting test" | <10 | To build |
| 5 | Webcam Framing Guide | `webcam-framing-guide.html` | "webcam framing guide" | <10 | To build |

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

Build in this order to maximise SEO value and unlock the rotation system progressively.

| Priority | Page | File | Reason |
|----------|------|------|--------|
| 1 | Webcam Recorder | `webcam-recorder.html` | Hub A — 14,800/mo, unlocks entire Silo A rotation |
| 2 | Webcam Effects | `webcam-effects.html` | Silo A — 1,600/mo, high relative volume |
| 3 | Barcode Scanner | `barcode-scanner.html` | Silo C — 1,000/mo, first high-volume Silo C page |
| 4 | QR Code Scanner | `qr-scanner.html` | Silo C — 170/mo, pairs naturally with barcode scanner |
| 5 | Webcam Quality Test | `webcam-quality-test.html` | Silo B — 50/mo |
| 6 | Webcam GIF Maker | `webcam-gif.html` | Silo A — 20/mo, completes creative cluster |
| 7 | Webcam Zoom Test | `webcam-zoom-test.html` | Silo B — 10/mo |
| 8 | Webcam Timelapse | `webcam-timelapse.html` | Silo A — topical depth |
| 9 | Webcam Brightness Test | `webcam-brightness-test.html` | Silo B — topical depth |
| 10 | Webcam Color Test | `webcam-color-test.html` | Silo B — topical depth |
| 11 | Camera Comparison | `camera-comparison.html` | Silo C — topical depth |
| 12 | Webcam Lighting Test | `webcam-lighting-test.html` | Silo C — topical depth |
| 13 | Webcam Framing Guide | `webcam-framing-guide.html` | Silo C — topical depth |

---

### Monthly Rotation System — Implementation Plan

Mirrors the system built for mic-tests.github.io. To be implemented once `webcam-recorder.html` is built.

#### Script

**Planned file:** `utilities/silo_linking/generate_silo_rotation.py`

Same architecture as mic-tests.github.io:
- Deterministic shuffles via `random.Random(MD5-seed)`
- Hub order shuffles monthly → pillar link + hub left/right neighbours rotate
- Supporter order shuffles per silo → prev/next chain + bridge endpoints rotate
- Hub `slot_a` anchor rotates among 6 long-tail "webcam test" variants per hub per month
- 6 sentence templates per anchor keyword (90 total)
- HTML comment markers injected into body content paragraphs

```bash
python3 utilities/silo_linking/generate_silo_rotation.py            # apply
python3 utilities/silo_linking/generate_silo_rotation.py --dry-run  # preview
python3 utilities/silo_linking/generate_silo_rotation.py --date=2026-06  # test specific month
```

#### GitHub Actions Workflow

**Planned file:** `.github/workflows/silo-rotation.yml`

```yaml
on:
  schedule:
    - cron: '0 16 1-3 * *'   # midnight SGT, days 1–3 of each month
  workflow_dispatch:
    inputs:
      date:
        description: 'Override month (YYYY-MM). Leave empty for today.'
        required: false
        default: ''
```

Uses built-in `GITHUB_TOKEN` — no PAT required. Days 2 and 3 are retry safety nets; once committed, subsequent runs detect no diff and exit cleanly.

#### HTML Comment Markers

Each silo link injected as:
```html
<!-- SILO_START:slot_a -->sentence with <a href="/url">anchor</a><!-- SILO_END:slot_a -->
```

Inserted after the first `</p>` following a designated heading. Injection target headings to be determined per page once all pages are built.

#### Rotation Algorithm (same as mic-tests.github.io)

1. **Hub slot_a anchor** — each hub independently picks 1 of 6 long-tail pillar variants per month via `MD5(year-month-hub_file-slot_a) % 6`
2. **Hub order shuffle** — `random.Random(MD5(year-month-pillar)).shuffle(HUBS)` → determines pillar link + hub left/right neighbours
3. **Supporter shuffle per silo** — `random.Random(MD5(year-month-silo_N)).shuffle(supporters)` → determines hub down-link + supporter chain order + bridge endpoints
4. **Sentence selection** — `MD5(year-month-source_file-anchor) % 6` → picks 1 of 6 sentence templates

All shuffles are deterministic — same month always produces same output.

---

## W3 HTML Validator — Pending

All pages should be validated using live URLs via the Nu HTML Checker:
`https://validator.w3.org/nu/?doc=https://webcam-test.github.io/<page-path>`

Example:
- `https://validator.w3.org/nu/?doc=https://webcam-test.github.io/`

No pages have been validated yet. After each deploy, re-run the validator on changed pages to catch any new issues.
