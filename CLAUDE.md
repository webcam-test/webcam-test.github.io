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

**Build pipeline**: Webpack bundles `./js/app.js` → `./dist/`. Production build uses HtmlWebpackPlugin (template: `index.html`) and CopyPlugin to copy static assets, vendor files, and all HTML pages into `./dist/`.

**Page structure**: Each HTML file is a standalone page (no routing framework). Pages are self-contained with inline styles and Bootstrap 5.3 + Bootstrap Icons loaded from CDN. The pages are:
- `index.html` — homepage/landing
- `show-webcam.html` — detailed camera info
- `take-photo.html` — photo capture
- `mirror.html` — webcam mirror/stream viewer
- `fps-checker.html` — frame rate testing
- `resolution-tester.html` — resolution testing

**External dependencies (CDN only)**:
- Bootstrap 5.3.0-alpha1 + Bootstrap Icons 1.11.1
- Google AdSense (monetization)

**SEO assets**: `robots.txt`, `sitemap.xml` — update sitemap when adding/removing pages.

**Webpack configs**: `webpack.common.js` (shared), `webpack.config.dev.js` (dev server), `webpack.config.prod.js` (production).
