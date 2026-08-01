#!/usr/bin/env python3
"""
Export a JSON content database for all WebcamTest pages.

For each page, isolates the top-level <section> elements inside <main>
and drops the ones that are UI chrome rather than article content:
  - <section class="hero">                    (H1 + intro paragraph)
  - any section containing <video>/<canvas>    (the interactive tool
                                                 itself, plus any live
                                                 results/spec panel and
                                                 sidebar testimonials
                                                 that live alongside it)
  - the section embedding <comentario-comments> (the Comments widget)

What's left is walked and split into a flat, ordered list of
{level, heading, content} blocks, one per H2-H6 heading (this includes
FAQ accordion headers - `<h3 class="accordion-header">` wrapping a
`<button class="accordion-button">` - since the accordion body text
that follows becomes that heading's content automatically). Content
is plain text (tags stripped, entities decoded); paragraphs, list
items, definition-list pairs, and table rows are each flattened to
one line.

Run:
  python3 utilities/content_export/export_content_db.py
Output:
  utilities/content_export/content-db.json
"""

import html as html_lib
import json
import os
import re
from html.parser import HTMLParser

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# (filename, url slug) - excludes 404.html (error page, no real content)
# and googlecb346f17d96186ee.html (empty verification file, must not be touched).
PAGES = [
    ("index.html", "/"),
    ("about.html", "/about"),
    ("contact.html", "/contact"),
    ("sitemap.html", "/sitemap"),
    ("show-webcam.html", "/show-webcam"),
    ("take-photo.html", "/take-photo"),
    ("mirror.html", "/mirror"),
    ("fps-checker.html", "/fps-checker"),
    ("resolution-tester.html", "/resolution-tester"),
    ("camera-comparison.html", "/camera-comparison"),
    ("webcam-recorder.html", "/webcam-recorder"),
    ("webcam-effects.html", "/webcam-effects"),
    ("webcam-gif.html", "/webcam-gif"),
    ("webcam-timelapse.html", "/webcam-timelapse"),
    ("webcam-quality-test.html", "/webcam-quality-test"),
    ("webcam-zoom-test.html", "/webcam-zoom-test"),
    ("webcam-brightness-test.html", "/webcam-brightness-test"),
    ("webcam-color-test.html", "/webcam-color-test"),
    ("webcam-lighting-test.html", "/webcam-lighting-test"),
    ("webcam-grid-overlay.html", "/webcam-grid-overlay"),
]

HEADING_TAGS = {"h2", "h3", "h4", "h5", "h6"}
BLOCK_TAGS = {"p", "li", "dt", "dd", "tr", "td", "th", "div", "aside", "blockquote", "figcaption"}
SKIP_TAGS = {"script", "style"}
SKIP_CLASSES = {"testimonial", "review-form"}  # defensive: chrome if it ever appears outside the tool section

WS_RE = re.compile(r"\s+")
SECTION_RE = re.compile(r"<(/?)section\b", re.I)
MAIN_OPEN_RE = re.compile(r"<main\b[^>]*>", re.I)
MAIN_CLOSE_RE = re.compile(r"</main>", re.I)


def extract_main(raw):
    m = MAIN_OPEN_RE.search(raw)
    if not m:
        return ""
    end = MAIN_CLOSE_RE.search(raw, m.end())
    return raw[m.end(): end.start()] if end else raw[m.end():]


def split_top_level_sections(main_html):
    """Yield each top-level <section>...</section> chunk (tag-depth aware)."""
    depth = 0
    start = None
    for m in SECTION_RE.finditer(main_html):
        closing = bool(m.group(1))
        if not closing:
            if depth == 0:
                start = m.start()
            depth += 1
        else:
            depth -= 1
            if depth == 0 and start is not None:
                # extend to the actual closing tag's end
                close_end = main_html.index(">", m.end()) + 1
                yield main_html[start:close_end]
                start = None


def keep_section(section_html):
    if re.search(r'<section\s+class="hero"', section_html, re.I):
        return False
    if "<video" in section_html.lower() or "<canvas" in section_html.lower():
        return False
    if "<comentario-comments" in section_html.lower():
        return False
    return True


class ContentExtractor(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.sections = []
        self.current = None
        self.heading_active = False
        self.heading_buf = []
        self.stack = []          # list of {"tag": tag, "buf": [str]}
        self.row_cells = []
        self.pending_term = None
        self.skip_tag_depth = 0
        self.skip_regions = []   # stack of div-depths for SKIP_CLASSES
        self.div_depth = 0

    # ---------------------------------------------------------------
    def handle_starttag(self, tag, attrs):
        attrs_d = dict(attrs)

        if tag == "div":
            self.div_depth += 1
            classes = attrs_d.get("class", "").split()
            if not self.skip_regions and any(c in SKIP_CLASSES for c in classes):
                self.skip_regions.append(self.div_depth)

        if self.skip_regions:
            return

        if tag in SKIP_TAGS:
            self.skip_tag_depth += 1
            return
        if self.skip_tag_depth:
            return

        if tag in HEADING_TAGS:
            self.current = {"level": tag, "heading": "", "content": ""}
            self.sections.append(self.current)
            self.heading_active, self.heading_buf = True, []
        elif tag in BLOCK_TAGS:
            self.stack.append({"tag": tag, "buf": []})

    def handle_endtag(self, tag):
        if tag == "div":
            if self.skip_regions and self.div_depth == self.skip_regions[-1]:
                self.skip_regions.pop()
            self.div_depth = max(0, self.div_depth - 1)
            if self.skip_regions:
                return

        if self.skip_regions:
            return

        if tag in SKIP_TAGS:
            self.skip_tag_depth = max(0, self.skip_tag_depth - 1)
            return
        if self.skip_tag_depth:
            return

        if tag in HEADING_TAGS:
            self.current["heading"] = self._collapse(self.heading_buf)
            self.heading_active, self.heading_buf = False, []
            return

        if tag in BLOCK_TAGS:
            if not self.stack or self.stack[-1]["tag"] != tag:
                return  # mismatched/unbalanced - bail defensively
            frame = self.stack.pop()
            text = self._collapse(frame["buf"])
            if tag == "dt":
                self.pending_term = text
            elif tag == "dd":
                if self.pending_term:
                    self._append(f"{self.pending_term}: {text}")
                    self.pending_term = None
                else:
                    self._append(text)
            elif tag == "li":
                if text:
                    self._append(f"- {text}")
            elif tag in ("td", "th"):
                self.row_cells.append(text)
            elif tag == "tr":
                if self.row_cells:
                    self._append(" | ".join(self.row_cells))
                self.row_cells = []
            else:  # p, div, aside, blockquote, figcaption
                if text:
                    self._append(text)

    def handle_data(self, data):
        if self.heading_active:
            self.heading_buf.append(data)
        elif self.stack:
            self.stack[-1]["buf"].append(data)

    def handle_comment(self, data):
        pass  # ignore SILO_START/SILO_END markers etc.

    # ---------------------------------------------------------------
    def _collapse(self, parts):
        text = html_lib.unescape("".join(parts))
        return WS_RE.sub(" ", text).strip()

    def _append(self, line):
        if self.current is None:
            return  # content before the first heading - shouldn't occur post-filtering
        self.current["content"] = (self.current["content"] + "\n" + line) if self.current["content"] else line


def extract_page(path):
    with open(path, encoding="utf-8") as f:
        raw = f.read()
    main_html = extract_main(raw)
    kept = "".join(s for s in split_top_level_sections(main_html) if keep_section(s))

    parser = ContentExtractor()
    parser.feed(kept)
    parser.close()
    return [s for s in parser.sections if s["heading"] or s["content"]]


def main():
    db = {}
    for filename, slug in PAGES:
        path = os.path.join(REPO_ROOT, filename)
        if not os.path.exists(path):
            print(f"  ! missing {filename}, skipping")
            continue
        sections = extract_page(path)
        db[slug] = {"file": filename, "sections": sections}
        print(f"  {filename}: {len(sections)} sections")

    out_path = os.path.join(REPO_ROOT, "utilities", "content_export", "content-db.json")
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(db, f, ensure_ascii=False, indent=2)
        f.write("\n")
    print(f"\nWrote {out_path}")


if __name__ == "__main__":
    main()
