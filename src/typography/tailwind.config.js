// Config for the @tailwindcss/typography build — see build_typography_css() in
// ../generate.py. className: 'article' targets the site's existing `.article`
// div directly (template.html/template-page.html), so raw HTML (h2/h3/p/ul/
// ol/li/strong/code/a/blockquote/table...) dropped in there gets readable
// typography with zero classes added to the content itself. corePlugins is
// off — this build emits only the typography plugin's component CSS, not
// Tailwind's utility framework or preflight reset (this site has its own).
// Colors/fonts below are CSS var references into styles.css's tokens, so
// this build stays in sync with the site palette without duplicating hex
// values — only regenerate (rerun generate.py) if those tokens change.
module.exports = {
  // template.html no longer has `class="article"` as literal text — that div
  // is composed in Python (render_typed_main_sections/render_main_sections
  // in ../generate.py) and only ever reaches template.html via the
  // {{MAIN_SECTIONS}} token at render time. Tailwind's JIT scanner only sees
  // whatever's literally present in these files, so generate.py has to be a
  // scan target too, or this build silently stops emitting `.article` rules
  // the next time nothing else in these files happens to contain that text.
  content: ["../template.html", "../template-page.html", "../generate.py"],
  corePlugins: false,
  theme: {
    extend: {
      typography: {
        DEFAULT: {
          css: {
            maxWidth: "none",
            "--tw-prose-body": "var(--text-secondary)",
            "--tw-prose-headings": "var(--text)",
            "--tw-prose-lead": "var(--text-secondary)",
            "--tw-prose-links": "var(--accent-dark)",
            "--tw-prose-bold": "var(--text-alt)",
            "--tw-prose-counters": "var(--text-muted)",
            "--tw-prose-bullets": "var(--text-muted)",
            "--tw-prose-hr": "var(--border)",
            "--tw-prose-quotes": "var(--text-alt)",
            "--tw-prose-quote-borders": "var(--accent)",
            "--tw-prose-captions": "var(--text-muted)",
            "--tw-prose-code": "var(--accent-light)",
            "--tw-prose-pre-code": "var(--code-text)",
            "--tw-prose-pre-bg": "var(--code-bg)",
            "--tw-prose-th-borders": "var(--border)",
            "--tw-prose-td-borders": "var(--border)",
            a: { textDecoration: "underline", textUnderlineOffset: "2px", fontWeight: "500" },
            // Preflight (disabled above, corePlugins: false) is what normally supplies the
            // browser-independent `border-style: solid` default every other prose ruleset
            // assumes is already in place -- without it, blockquote's border-inline-start-width
            // and -color render with an implicit border-style of "none" and the border simply
            // doesn't paint, even though width/color are both set. Same root cause as the two
            // build-pipeline bugs documented in this project's own CLAUDE.md.
            blockquote: { borderInlineStartStyle: "solid" },
            hr: { borderTopStyle: "solid" },
            code: {
              fontFamily: "var(--font-mono)",
              backgroundColor: "var(--accent-soft)",
              padding: "0.15em 0.4em",
              borderRadius: "var(--radius-sm)",
              fontWeight: "500",
            },
            "code::before": { content: "none" },
            "code::after": { content: "none" },
          },
        },
      },
    },
  },
  plugins: [
    require("@tailwindcss/typography")({ className: "article" }),
  ],
};
