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

These have <10/mo volume individually but strengthen the site's topical coverage for "webcam" as a whole.

| Tool | Keyword | Implementation |
|------|---------|----------------|
| Camera Comparison | webcam comparison tool | Side-by-side split view of two cameras |
| Webcam Lighting Test | webcam lighting test | Analyze brightness/exposure from canvas |
| Webcam Framing Guide | webcam framing guide | Rule-of-thirds overlay on live feed |
| Webcam Color Test | webcam color test | Color accuracy analysis from canvas |
| Webcam Timelapse | webcam timelapse online | Capture frames at intervals → download video |
| Webcam Brightness Test | webcam brightness test | Measure and adjust brightness/contrast |

Rotate webcam (170/mo) is not recommended — HIGH competition.
