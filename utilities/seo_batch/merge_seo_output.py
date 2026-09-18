#!/usr/bin/env python3
"""
Merge one tool's /seo-optimize output (from the open-source-on-page-seo-
optimizer repo's output/<slug>/ directory) into this repo's
src/content/<slug>.json and src/content_images/<slug>/.

Usage:
    python3 utilities/seo_batch/merge_seo_output.py webcam-test-online \
        --seo-output /path/to/open-source-on-page-seo-optimizer/output/webcam-test

Fields it overwrites in src/content/<slug>.json (from meta.json/content.html):
    h1, meta_description, content_html

Fields it never touches (hand-authored, not produced by /seo-optimize):
    slug, subtitle, card, script, faq

This site has no separate <title> tag — generate.py renders <title> as the
tool's own h1 verbatim (see src/generate.py's module docstring) — so
meta.json's "title" is only used as a sanity check against "h1", never
written anywhere itself.

Also copies output/<slug>/images/*.svg (Phase 3b infographics) into
src/content_images/<slug>/, and rewrites content_html's relative
images/<file> src attributes to the /images/<slug>/<file> path
generate.py serves them at (see that file's copy step in main()).

Each copied SVG also gets *site*-specific metadata stamped in (dc:creator/
dc:rights/dc:source/license) — deliberately not something the seo-optimizer
skill itself writes, since that pipeline is site-agnostic and has no way to
know whether/where its output will actually get published (see SKILL.md's
Phase 3b note on this). This is the one place that does know, so it's the
right place to attribute the image to WebcamTest. If the SVG already has a
content-level <metadata> RDF block (from Phase 3b), the site fields are
added into it; if it's an older SVG without one (pre-dating that SKILL.md
change), a full block is built from infographics.json's alt/caption.

Run src/build_data.py + src/generate.py afterward to rebuild public/.
"""
import argparse
import html
import json
import os
import re
import shutil
import sys
from datetime import date

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
CONTENT_DIR = os.path.join(REPO_ROOT, "src", "content")
CONTENT_IMAGES_DIR = os.path.join(REPO_ROOT, "src", "content_images")
SITE_JSON_PATH = os.path.join(REPO_ROOT, "src", "data", "site.json")

IMG_SRC_RE = re.compile(r'src="images/([^"]+)"')
SVG_OPEN_TAG_RE = re.compile(r'(<svg\b[^>]*>)')
RDF_DESC_CLOSE_RE = re.compile(r'</rdf:Description>')
TITLE_EL_RE = re.compile(r'<title[^>]*>(.*?)</title>', re.DOTALL)
DESC_EL_RE = re.compile(r'<desc[^>]*>(.*?)</desc>', re.DOTALL)


def _site_info(slug):
    with open(SITE_JSON_PATH) as f:
        site = json.load(f)
    site_url = "https://%s" % site["domain"]
    page_url = site_url if slug == site["home_slug"] else "%s/%s" % (site_url, slug)
    license_url = "%s/terms" % site_url
    copyright_line = "© %d %s — %s" % (date.today().year, site["site_name"], site["domain"])
    return {
        "site_name": site["site_name"],
        "page_url": page_url,
        "license_url": license_url,
        "copyright_line": copyright_line,
    }


DIGITAL_SOURCE_TYPE_EL = (
    '<Iptc4xmpExt:DigitalSourceType xmlns:Iptc4xmpExt="http://iptc.org/std/Iptc4xmpExt/2008-02-29/">'
    "http://cv.iptc.org/newscodes/digitalsourcetype/trainedAlgorithmicMedia"
    "</Iptc4xmpExt:DigitalSourceType>"
)


def stamp_svg_site_metadata(svg_path, alt, caption, site):
    with open(svg_path, encoding="utf-8") as f:
        svg = f.read()

    site_fields = (
        "<dc:creator><rdf:Seq><rdf:li>%s</rdf:li></rdf:Seq></dc:creator>"
        '<dc:rights><rdf:Alt><rdf:li xml:lang="x-default">%s</rdf:li></rdf:Alt></dc:rights>'
        "<dc:source>%s</dc:source>"
        '<xmpRights:WebStatement xmlns:xmpRights="http://ns.adobe.com/xap/1.0/rights/">%s</xmpRights:WebStatement>'
        % (
            html.escape(site["site_name"]),
            html.escape(site["copyright_line"]),
            html.escape(site["page_url"]),
            html.escape(site["license_url"]),
        )
    )
    # Google's generative-AI-content guidance names this IPTC field explicitly for
    # AI-generated images — https://developers.google.com/search/docs/fundamentals/using-generative-ai-content.
    # These SVGs genuinely are LLM-synthesized (SKILL.md's Phase 3b), true regardless
    # of site, but older runs predate that SKILL.md change, so backfill it here too.
    if "DigitalSourceType" not in svg:
        site_fields = DIGITAL_SOURCE_TYPE_EL + site_fields

    if "<metadata>" in svg:
        svg, n = RDF_DESC_CLOSE_RE.subn(site_fields + "</rdf:Description>", svg, count=1)
        if n == 0:
            return  # unexpected shape (no rdf:Description to attach to) — leave the file alone
    else:
        # Reuse an existing <title>/<desc> verbatim if the SVG already has one
        # (e.g. authored with an aria-labelledby id pair rather than Phase 3b's
        # first-child convention) — inserting a second, alt/caption-derived pair
        # here would duplicate it with worse (truncated) text.
        existing_title = TITLE_EL_RE.search(svg)
        existing_desc = DESC_EL_RE.search(svg)
        dc_title = existing_title.group(1).strip() if existing_title else html.escape((alt or "")[:80])
        dc_desc = existing_desc.group(1).strip() if existing_desc else html.escape(caption or alt or "")

        new_elements = ""
        if not existing_title:
            new_elements += "<title>%s</title>" % html.escape((alt or "")[:80])
        if not existing_desc:
            new_elements += "<desc>%s</desc>" % html.escape(caption or alt or "")

        metadata_block = (
            new_elements
            + '<metadata><rdf:RDF xmlns:rdf="http://www.w3.org/1999/02/22-rdf-syntax-ns#" '
            'xmlns:dc="http://purl.org/dc/elements/1.1/"><rdf:Description rdf:about="">'
            '<dc:title><rdf:Alt><rdf:li xml:lang="x-default">%s</rdf:li></rdf:Alt></dc:title>'
            '<dc:description><rdf:Alt><rdf:li xml:lang="x-default">%s</rdf:li></rdf:Alt></dc:description>'
            "%s</rdf:Description></rdf:RDF></metadata>"
            % (dc_title, dc_desc, site_fields)
        )
        svg, n = SVG_OPEN_TAG_RE.subn(lambda m: m.group(1) + metadata_block, svg, count=1)
        if n == 0:
            return  # no <svg> open tag found — not a well-formed SVG, leave it alone

    with open(svg_path, "w", encoding="utf-8") as f:
        f.write(svg)


def merge(slug, seo_output_dir, dry_run=False):
    content_path = os.path.join(CONTENT_DIR, "%s.json" % slug)
    if not os.path.exists(content_path):
        sys.exit("error: %s does not exist — is %r a real tool slug?" % (content_path, slug))

    meta_path = os.path.join(seo_output_dir, "meta.json")
    content_html_path = os.path.join(seo_output_dir, "content.html")
    if not os.path.exists(meta_path):
        sys.exit("error: %s not found" % meta_path)
    if not os.path.exists(content_html_path):
        sys.exit("error: %s not found" % content_html_path)

    with open(content_path) as f:
        content = json.load(f)
    with open(meta_path) as f:
        meta = json.load(f)
    with open(content_html_path) as f:
        content_html = f.read()

    if meta.get("title") != meta.get("h1"):
        print(
            "warning: %s: meta.json's title != h1 (%r vs %r) — this site "
            "renders <title> as h1 verbatim, so only h1 is used"
            % (slug, meta.get("title"), meta.get("h1"))
        )

    content_html = IMG_SRC_RE.sub(lambda m: 'src="/images/%s/%s"' % (slug, m.group(1)), content_html)

    content["h1"] = meta["h1"]
    content["meta_description"] = meta["meta_description"]
    content["content_html"] = content_html

    images_src_dir = os.path.join(seo_output_dir, "images")
    n_images = 0
    if os.path.isdir(images_src_dir):
        infographics_path = os.path.join(seo_output_dir, "infographics.json")
        infographics_by_file = {}
        if os.path.exists(infographics_path):
            with open(infographics_path) as f:
                for entry in json.load(f):
                    infographics_by_file[os.path.basename(entry["file"])] = entry

        dest_dir = os.path.join(CONTENT_IMAGES_DIR, slug)
        image_files = [f for f in os.listdir(images_src_dir) if f.lower().endswith(".svg")]
        if not dry_run:
            # Clear stale files first — a re-run (e.g. after an earlier manual
            # test generation) can rename/drop images, and content_html always
            # gets fully overwritten to match the new set. Without this, an
            # old run's SVG no longer referenced by any content_html silently
            # lingers here and gets committed as dead weight.
            if os.path.isdir(dest_dir):
                shutil.rmtree(dest_dir)
            os.makedirs(dest_dir, exist_ok=True)
            site = _site_info(slug)
            for fname in image_files:
                dest_path = os.path.join(dest_dir, fname)
                shutil.copy(os.path.join(images_src_dir, fname), dest_path)
                entry = infographics_by_file.get(fname, {})
                stamp_svg_site_metadata(dest_path, entry.get("alt"), entry.get("caption"), site)
        n_images = len(image_files)

    if dry_run:
        print("[dry-run] %s: would set h1/meta_description/content_html, copy %d image(s)" % (slug, n_images))
        return

    with open(content_path, "w") as f:
        json.dump(content, f, indent=2, ensure_ascii=False)
        f.write("\n")

    print(
        "%s: merged h1/meta_description/content_html, copied %d image(s) into src/content_images/%s/"
        % (slug, n_images, slug)
    )


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("slug", help="tool slug, e.g. webcam-test-online (must match an existing src/content/<slug>.json)")
    parser.add_argument("--seo-output", required=True, help="path to the seo-optimizer repo's output/<slug> directory")
    parser.add_argument("--dry-run", action="store_true", help="report what would change without writing anything")
    args = parser.parse_args()
    merge(args.slug, args.seo_output, dry_run=args.dry_run)


if __name__ == "__main__":
    main()
