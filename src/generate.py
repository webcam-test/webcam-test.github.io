#!/usr/bin/env python3
"""Renders template.html/template-page.html/template-404.html x data/*.json
into public/, minifying everything by default. Modeled directly on
passwordhive's generate.py (individual_websites/passwordhive/src/generate.py)
— same minification/critical-CSS pipeline, same tool choices/pinned
versions. Run `python3 src/build_data.py` first to (re)generate
data/site.json, data/tools.json, data/pages.json.

    python3 src/generate.py             # full build, minified
    python3 src/generate.py --no-minify # fast iteration, unminified output

Every tool is one file — content/<slug>.json carries meta_description
(there's no separate meta_title — the <title> tag is the tool's own h1,
verbatim, no "| WebcamTest" suffix, so title and H1 always match exactly),
h1/subtitle, the card config, script (the tool's own
fully self-contained JS — no shared runtime file, see this project's
CLAUDE.md and src/content/README.md), content_html, and faq. Every tool
uses the "raw" card layout: card["fields_html"] is the tool's ENTIRE card
grid, authored directly in its own JSON file — unlike passwordhive, which
has several distinct card layouts (generator/analyzer/hash-multi/...),
almost every tool on this site has a genuinely different interactive shape
(live video, split-view comparison, spectrum analyzer, resolution-probe
ladder), so there is exactly one Python-side render branch to maintain
regardless of tool count.

Unlike passwordhive, there is no typed what_/how_/article_sections
fallback and no AdSense — this site has no legacy site to port ad slots
from. If a tool has no content_html, render_main_sections() renders
nothing below the tool card for it — an honestly empty section, never
synthesized filler.

Per-tool infographic SVGs (synthesized by the open-source-on-page-seo-
optimizer pipeline's Phase 3b and pulled in via
utilities/seo_batch/merge_seo_output.py) live at
content_images/<slug>/*.svg and get copied verbatim into
public/images/<slug>/ by main() below — content_html then references
them as /images/<slug>/<file>.svg.
"""
import html
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile

import schema

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, "data")
OUTPUT_DIR = os.path.join(BASE_DIR, "..", "public")

HTML_MINIFIER_PKG = "html-minifier-terser@7.2.0"
CLEAN_CSS_PKG = "clean-css-cli@5.6.3"
TAILWIND_PKG = "tailwindcss@3.4.19"
TAILWIND_TYPOGRAPHY_PKG = "@tailwindcss/typography@0.5.20"
CRITICAL_PKG = "critical@8.0.0"

# Per-cluster icons for the homepage tool grid / footer — see
# render_cluster_icon() below. Kept to 4 fixed icons (one per spec cluster)
# rather than one bespoke icon per tool, to avoid a 44-icon authoring burden
# for a site whose differentiation is in the tools themselves, not iconography.
CLUSTER_ICONS = {
    "camera-core": '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M23 7l-7 5 7 5V7z"/><rect x="1" y="5" width="15" height="14" rx="2" ry="2"/></svg>',
    "camera-mobile": '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect x="6" y="2" width="12" height="20" rx="2" ry="2"/><path d="M11 18h2" stroke-linecap="round"/></svg>',
    "camera-reference": '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M4 19.5A2.5 2.5 0 0 1 6.5 17H20"/><path d="M6.5 2H20v20H6.5A2.5 2.5 0 0 1 4 19.5v-15A2.5 2.5 0 0 1 6.5 2z"/></svg>',
    "audio": '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M12 1a3 3 0 0 0-3 3v8a3 3 0 0 0 6 0V4a3 3 0 0 0-3-3z"/><path d="M19 10v2a7 7 0 0 1-14 0v-2M12 19v3M8 22h8" stroke-linecap="round"/></svg>',
}

CHECK_SVG = '<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="3"><path d="M20 6 9 17l-5-5"/></svg>'
CHEVRON_SVG = '<svg viewBox="0 0 24 24" width="14" height="14" fill="none" stroke="currentColor" stroke-width="2"><path d="M6 9l6 6 6-6"/></svg>'
CAMERA_LOGO_SVG = '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M23 7l-7 5 7 5V7z"/><rect x="1" y="5" width="15" height="14" rx="2" ry="2"/></svg>'
CLOSE_SVG = '<svg viewBox="0 0 24 24" width="20" height="20" fill="none" stroke="currentColor" stroke-width="2"><path d="M18 6 6 18M6 6l12 12" stroke-linecap="round"/></svg>'
HAMBURGER_SVG = '<svg viewBox="0 0 24 24" width="22" height="22" fill="none" stroke="currentColor" stroke-width="2"><path d="M3 6h18M3 12h18M3 18h18" stroke-linecap="round"/></svg>'

# Same ca-pub client + real ad-unit slots webcam-test.github.io's live site
# already uses (header, an "auto" in-content unit, a fixed rectangle) — see
# that repo's own index.html and this project's CLAUDE.md "AdSense" note.
# Ported as-is, not regenerated as new units. Placement logic (loader in
# <head>, header between hero and tool card, one in-content unit spliced
# before the first <h2>, one at the very end) is passwordhive's
# render_adsense_*() pattern; the one difference is 3 slots instead of
# passwordhive's 4 — there's no 4th real unit for a "body2" position, and
# the in-content unit uses the real site's own "auto"/full-width-responsive
# format rather than passwordhive's fixed 300x250.
ADSENSE_CLIENT = "ca-pub-5426315045205785"
ADSENSE_SLOTS = {
    "header": "6562139351",
    "body": "6837554954",
    "footer": "5068825756",
}


GA_MEASUREMENT_ID = "G-VBX83N9QR8"


def render_ga_snippet():
    """Google tag (gtag.js) — on every page, unlike AdSense (tool pages
    only): analytics should track all traffic, ads only make sense where a
    unit is actually placed."""
    return (
        "<!-- Google tag (gtag.js) -->"
        '<script src="https://www.googletagmanager.com/gtag/js?id=%s" async></script>'
        "<script>"
        "window.dataLayer = window.dataLayer || [];"
        "function gtag(){dataLayer.push(arguments);}"
        "gtag('js', new Date());"
        "gtag('config', '%s');"
        "</script>"
        % (GA_MEASUREMENT_ID, GA_MEASUREMENT_ID)
    )


def render_adsense_loader():
    return (
        '<script src="https://pagead2.googlesyndication.com/pagead/js/adsbygoogle.js?client=%s" '
        'async crossorigin="anonymous"></script>'
        % ADSENSE_CLIENT
    )


def render_adsense_header():
    """Responsive leaderboard slot — same sizing logic as passwordhive's
    render_adsense_header(): 728x90 at >=768px, 300x100 below that, resized
    via inline JS since the unit isn't configured with data-ad-format="auto"."""
    return (
        '<aside class="ad-slot ad-slot-header" aria-label="Advertisement (top)"><ins class="adsbygoogle" id="adsense-header" '
        'data-ad-client="%s" data-ad-slot="%s"></ins>'
        "<script>(function(){"
        'var ins=document.getElementById("adsense-header");'
        'if(window.innerWidth>=768){ins.style.display="inline-block";ins.style.width="728px";ins.style.height="90px";}'
        'else{ins.style.display="inline-block";ins.style.width="300px";ins.style.height="100px";}'
        "(adsbygoogle=window.adsbygoogle||[]).push({});"
        "})();</script></aside>"
        % (ADSENSE_CLIENT, ADSENSE_SLOTS["header"])
    )


def render_adsense_body():
    """In-content unit, spliced before a tool's first <h2> — same position
    as passwordhive's "body1" slot. Full-width responsive, matching how this
    real ad unit is already configured on the live site (not a fixed
    300x250 like passwordhive's body units)."""
    return (
        '<aside class="ad-slot" aria-label="Advertisement (in-article)"><ins class="adsbygoogle ad-auto" '
        'data-ad-client="%s" data-ad-slot="%s" data-ad-format="auto" data-full-width-responsive="true"></ins>'
        '<script>(adsbygoogle=window.adsbygoogle||[]).push({});</script></aside>'
        % (ADSENSE_CLIENT, ADSENSE_SLOTS["body"])
    )


def render_adsense_footer():
    """Fixed 300x250 unit at the very end (after FAQ, if any) — same
    unconditional placement as passwordhive's "footer" slot, present even on
    a tool with no content_html."""
    return (
        '<aside class="ad-slot" aria-label="Advertisement (end of article)"><ins class="adsbygoogle ad-rectangle" '
        'data-ad-client="%s" data-ad-slot="%s"></ins>'
        '<script>(adsbygoogle=window.adsbygoogle||[]).push({});</script></aside>'
        % (ADSENSE_CLIENT, ADSENSE_SLOTS["footer"])
    )


# ---------------------------------------------------------------------------
# Tool-card rendering — every tool uses the "raw" layout (see module
# docstring): card["fields_html"] is the entire card grid, verbatim.
# ---------------------------------------------------------------------------

def render_tool_card_body(tool):
    card = tool.get("card", {})
    layout = card.get("layout", "raw")
    if layout != "raw":
        raise ValueError("Unknown card layout: %r on tool %r (only 'raw' is implemented on this site)" % (layout, tool.get("slug")))
    return card.get("fields_html", "")


# ---------------------------------------------------------------------------
# Main sections (content_html split at each <h2>, plus FAQ) — same mechanism
# as passwordhive/hexcalculator's raw-HTML-override path.
# ---------------------------------------------------------------------------

H2_SPLIT_RE = re.compile(r"(?=<h2\b)", re.IGNORECASE)


def split_content_by_h2(content_html):
    """Split a raw content_html blob at every <h2> boundary, keeping any lead
    content before the first <h2> prepended to that first section (same fix
    passwordhive's own split_content_by_h2() applies over hexcalculator's
    original version, which drops it)."""
    parts = [p for p in H2_SPLIT_RE.split(content_html) if p.strip()]
    if parts and not re.match(r"^\s*<h2\b", parts[0], re.IGNORECASE):
        lead = parts.pop(0)
        if parts:
            parts[0] = lead + parts[0]
        else:
            parts = [lead]
    return parts


def render_comments_section(alt):
    """Comentario embedded comment widget (https://comentario.app) — a
    self-hosted third-party comment system the legacy site carried on 17 of
    its tool pages (never on the 5 info pages), loaded from the same
    still-live comments.tickspike.com instance. Applied to all 44 tool
    pages in this pipeline. Placed after the footer ad, mirroring the
    legacy site's Ad -> Comments -> </main> order (see
    legacy-bootstrap-site/index.html)."""
    return (
        '<section class="block%s" id="comments" aria-labelledby="comments-heading"><div class="block-inner"><div class="content-card"><div class="article">'
        '<h2 id="comments-heading">Comments &amp; Feedback</h2>'
        '<script src="https://comments.tickspike.com/comentario.js" defer></script>'
        '<comentario-comments theme="light"></comentario-comments>'
        "</div></div></div></section>"
    ) % (" alt" if alt else "")


def render_faq_section(tool, alt):
    if not tool.get("faq"):
        return None
    items = "".join(
        '<div class="faq-item"><dt>%s</dt><dd>%s</dd></div>' % (html.escape(f["question"]), f["answer"])
        for f in tool["faq"]
    )
    return (
        '<section class="block%s" id="faq" aria-labelledby="faq-heading"><div class="block-inner"><div class="content-card faq-card">'
        '<h2 id="faq-heading">Frequently Asked Questions</h2><dl class="faq-list">%s</dl></div></div></section>'
    ) % (" alt" if alt else "", items)


# ---------------------------------------------------------------------------
# Author box / last-updated line — ported from MouseTester's generate.py.
# The same person is content author and fact checker; the dates shown are
# the same ones the page's JSON-LD carries (schema.Schema.dates()).
# ---------------------------------------------------------------------------

SCHEMA = [None]  # the build's schema.Schema, set in main()


def author_box(site, page_id, published, modified, alt=False):
    a = site["author"]
    href = "/%s" % a["slug"]
    link = '<a href="%s">%s</a>' % (href, html.escape(a["name"]))
    return (
        '<section class="block{alt}" id="about-the-author" aria-labelledby="about-the-author-heading" data-section="author-box">'
        '<div class="block-inner"><div class="content-card author-box">'
        '<h2 id="about-the-author-heading">About the author</h2>'
        '<div class="author-box-body">'
        '<span class="author-avatar" aria-hidden="true">{ini}</span>'
        '<div class="author-box-text">'
        '<p class="author-name">{link}</p>'
        '<p class="author-title">{title}</p>'
        '<p class="author-bio">{bio}</p>'
        '<ul class="author-roles">'
        '<li><span class="author-role-label">{crole}:</span> {link}</li>'
        '<li><span class="author-role-label">{rrole}:</span> {link}. {rnote}</li>'
        '<li><span class="author-role-label">Published</span> <time datetime="{pub}">{pubd}</time> '
        '<span class="author-role-label" aria-hidden="true">&middot;</span> '
        '<span class="author-role-label">Updated</span> <time datetime="{mod}">{modd}</time></li>'
        '</ul>'
        '<p class="author-links"><a href="{li}" rel="me noopener" target="_blank">{name} on LinkedIn</a>'
        ' &middot; <a href="{be}" rel="me noopener" target="_blank">{name} on Behance</a>'
        ' &middot; <a href="{href}">Full profile</a></p>'
        '</div></div></div></div></section>'
    ).format(alt=" alt" if alt else "", p=page_id, ini=html.escape(a["initials"]), link=link,
             title=html.escape(a["job_title"]), bio=html.escape(a["bio"]),
             crole=html.escape(a["content_role"]), rrole=html.escape(a["review_role"]), rnote=html.escape(a["review_note"]),
             pub=published, pubd=schema.long_date(published), mod=modified, modd=schema.long_date(modified),
             li=html.escape(a["linkedin"]), be=html.escape(a["behance"]), name=html.escape(a["name"]), href=href)


def updated_line(page_id, modified):
    """Visible 'Last updated' for pages whose schema carries a dateModified but that have no author box."""
    return ('<p id="%s-last-updated" class="last-updated" data-section="last-updated">'
            'Last updated <time datetime="%s">%s</time></p>' % (page_id, modified, schema.long_date(modified)))


def json_ld_graph(nodes):
    """One <script> holding a linked @graph (see schema.py); it lives in <head>."""
    return '<script type="application/ld+json">%s</script>' % json.dumps(
        {"@context": "https://schema.org", "@graph": nodes}, ensure_ascii=False).replace("</", "<\\/")


# ---------------------------------------------------------------------------
# Section anchors + "On this page" list. Every article section gets an id
# built from its own visible <h2> text (no separate keyword names), so a
# section can be deep-linked (/slug#how-to-test-your-microphone), labelled for
# assistive tech (aria-labelledby) and offered by Google as a "Jump to" link.
# The list adds no <h2> or <p>, so the silo script's positional targets are
# unchanged.
# ---------------------------------------------------------------------------

H2_TAG_RE = re.compile(r"<h2\b([^>]*)>(.*?)</h2>", re.IGNORECASE | re.DOTALL)
ID_ATTR_RE = re.compile(r'\bid="([^"]+)"')
RESERVED_SECTION_IDS = {"faq", "comments", "about-the-author", "tool", "main-content", "page-title", "on-this-page"}


def section_slug(heading_html, taken):
    text = html.unescape(re.sub(r"<[^>]+>", "", heading_html)).lower().replace("&", " and ")
    text = text.replace("'", "").replace("\u2019", "")
    slug = re.sub(r"[^a-z0-9]+", "-", text).strip("-")
    if len(slug) > 60:
        slug = slug[:60].rsplit("-", 1)[0]
    slug = slug or "section"
    base, n = slug, 2
    while slug in taken:
        slug, n = "%s-%d" % (base, n), n + 1
    taken.add(slug)
    return slug


def render_toc(entries):
    """entries: [(id, heading_html)]. Rendered only when there are 3+ sections."""
    if len(entries) < 3:
        return ""
    items = "".join('<li><a href="#%s">%s</a></li>' % (sid, re.sub(r"<[^>]+>", "", text).strip())
                    for sid, text in entries)
    return ('<nav class="toc" aria-labelledby="on-this-page"><div class="toc-title" id="on-this-page">On this page</div>'
            '<ol class="toc-list">%s</ol></nav>' % items)


def render_main_sections(tool, site):
    """Renders everything below the tool card from tool["content_html"]
    (split into alternating .content-card sections) plus a FAQ section. No
    content fallback: a tool with no content_html renders no content
    sections, never synthesized filler — the footer ad below is not
    "filler content", it's a monetization placement independent of content,
    and passwordhive's own render_main_sections() shows it unconditionally
    for the same reason.

    Carries the "body"/"footer" AdSense slots (see ADSENSE_SLOTS), same
    placement logic as passwordhive: body is spliced before the first
    tool's <h2> (in the same section, not a section of its own — splitting
    chunks[0] apart at its own <h2> with H2_SPLIT_RE, splicing the ad in
    between, then rendering the whole thing as one section like any other
    chunk), footer sits unconditionally at the very end, after FAQ. The
    Comentario comments widget (see render_comments_section()) renders
    unconditionally after that, matching the legacy site's own
    Ad -> Comments order."""
    parts = []
    section_count = 0
    if tool.get("content_html"):
        chunks = split_content_by_h2(tool["content_html"])
        # Ids already used on the page (tool card, fixed sections) must not be reused.
        taken = set(RESERVED_SECTION_IDS) | set(ID_ATTR_RE.findall(tool.get("card", {}).get("fields_html", "")))
        section_ids, toc_entries = [], []
        for i, chunk in enumerate(chunks):
            m = H2_TAG_RE.search(chunk)
            sid = None
            if m:
                existing = ID_ATTR_RE.search(m.group(1))
                sid = existing.group(1) if existing else section_slug(m.group(2), taken)
                if not existing:
                    chunk = chunk[:m.start()] + '<h2 id="%s-heading"%s>%s</h2>' % (sid, m.group(1), m.group(2)) + chunk[m.end():]
                toc_entries.append((sid, m.group(2)))
            chunks[i] = chunk
            section_ids.append(sid)
        if tool.get("faq"):
            toc_entries.append(("faq", "Frequently Asked Questions"))
        toc = render_toc(toc_entries)
        for i, chunk in enumerate(chunks):
            if i == 0:
                lead_and_rest = H2_SPLIT_RE.split(chunk, maxsplit=1)
                if len(lead_and_rest) == 2:
                    lead, rest = lead_and_rest
                    chunk = lead + toc + render_adsense_body() + rest
                else:
                    chunk = chunk + toc + render_adsense_body()
            cls = "block alt" if section_count % 2 == 1 else "block"
            # The section itself carries the name (id = slug of its own <h2>); the
            # heading is <slug>-heading and labels it.
            labelled = (' id="%s" aria-labelledby="%s-heading"' % (section_ids[i], section_ids[i])) if section_ids[i] else ""
            parts.append(
                '<section class="%s"%s><div class="block-inner"><div class="content-card"><div class="article">%s</div></div></div></section>'
                % (cls, labelled, chunk)
            )
            section_count += 1
    faq_section = render_faq_section(tool, alt=(section_count % 2 == 1))
    if faq_section:
        parts.append(faq_section)
        section_count += 1
    published, modified = SCHEMA[0].dates("src/content/%s.json" % tool["slug"], tool)
    parts.append(author_box(site, tool["slug"], published, modified, alt=(section_count % 2 == 1)))
    section_count += 1
    parts.append(render_adsense_footer())
    parts.append(render_comments_section(alt=(section_count % 2 == 1)))
    return "\n".join(parts)


def render_info_content(page):
    out = ""
    for sec in page.get("sections", []):
        out += "<h2>%s</h2>" % html.escape(sec["heading"])
        for p in sec.get("paragraphs", []):
            out += "<p>%s</p>" % p
        if sec.get("list"):
            out += "<ul>" + "".join("<li>%s</li>" % li for li in sec["list"]) + "</ul>"
    return out


# ---------------------------------------------------------------------------
# Nav (header dropdowns + mobile "More" menu) and footer — same Priority+
# pattern as passwordhive's own render_category_dropdowns()/render_more_menu().
# ---------------------------------------------------------------------------

def tool_url(tool, site):
    if tool["slug"] == site["home_slug"]:
        return "/"
    return "/%s" % tool["slug"]


def group_links(group, site, by_slug, text_field="nav_name"):
    links = []
    if "slugs" in group:
        links.extend((tool_url(by_slug[slug], site), by_slug[slug].get(text_field, by_slug[slug]["nav_name"])) for slug in group["slugs"])
    if "tools" in group:
        links.extend(
            ("/" if t["slug"] == site["home_slug"] else "/%s" % t["slug"], t["name"])
            for t in group["tools"]
        )
    return links


def render_category_dropdowns(site, by_slug):
    items = ['<div class="cat-menu-item"><a href="/" class="cat-menu-btn">Home</a></div>']
    for group in site["nav_groups"]:
        panel_id = "catmenu-%s" % group["key"]
        icon = CLUSTER_ICONS.get(group["key"], CLUSTER_ICONS["camera-core"])
        links = "".join(
            '<a href="%s">%s</a>' % (url, html.escape(name))
            for url, name in group_links(group, site, by_slug)
        )
        items.append(
            '<div class="cat-menu-item" data-cat-key="%s">'
            '<button type="button" class="cat-menu-btn" aria-expanded="false" aria-controls="%s">%s%s</button>'
            '<div class="tools-menu cat-menu" id="%s" data-cluster="%s">'
            '<div class="menu-panel-header"><span class="menu-panel-icon">%s</span>'
            '<div><strong>%s</strong><p>%s</p></div></div>'
            '<div class="menu-panel-links">%s</div>'
            '</div>'
            '</div>' % (
                group["key"], panel_id, html.escape(group["short_label"]), CHEVRON_SVG, panel_id, group["key"],
                icon, html.escape(group["label"]), html.escape(group["tagline"]), links,
            )
        )
    return "".join(items)


def render_more_menu(site, by_slug):
    sections = []
    for group in site["nav_groups"]:
        icon = CLUSTER_ICONS.get(group["key"], CLUSTER_ICONS["camera-core"])
        links = "".join(
            '<a href="%s">%s</a>' % (url, html.escape(name))
            for url, name in group_links(group, site, by_slug)
        )
        sections.append(
            '<div class="more-menu-section" data-cat-key="%s">'
            '<div class="more-menu-heading"><span class="more-menu-icon">%s</span>%s</div>%s'
            '</div>' % (group["key"], icon, html.escape(group["label"]), links)
        )
    return (
        '<div class="cat-menu-item" id="moreMenuItem">'
        '<button type="button" class="cat-menu-btn" id="moreMenuBtn" aria-expanded="false" aria-controls="moreMenuPanel">More%s</button>'
        '<div class="tools-menu more-menu" id="moreMenuPanel">%s</div>'
        '</div>' % (CHEVRON_SVG, "".join(sections))
    )


# ---------------------------------------------------------------------------
# Mobile nav drawer — a full-height slide-in panel used only below the
# .top-nav's mobile breakpoint (see styles.css), replacing the desktop
# priority+/"More" pattern above with a single hamburger trigger. Every
# group is rendered as its own accordion section (icon + label + tagline),
# always all present (no priority-collapse math needed at this width).
# ---------------------------------------------------------------------------

def render_mobile_drawer(site, by_slug):
    sections = []
    for group in site["nav_groups"]:
        panel_id = "drawer-%s" % group["key"]
        icon = CLUSTER_ICONS.get(group["key"], CLUSTER_ICONS["camera-core"])
        links = "".join(
            '<a href="%s">%s</a>' % (url, html.escape(name))
            for url, name in group_links(group, site, by_slug)
        )
        sections.append(
            '<div class="drawer-section" data-cluster="%s">'
            '<button type="button" class="drawer-section-btn" aria-expanded="false" aria-controls="%s">'
            '<span class="drawer-section-icon">%s</span>'
            '<span class="drawer-section-label"><strong>%s</strong><small>%s</small></span>'
            '%s</button>'
            '<div class="drawer-section-links" id="%s"><div class="drawer-section-links-inner">%s</div></div>'
            '</div>' % (
                group["key"], panel_id, icon, html.escape(group["label"]), html.escape(group["tagline"]),
                CHEVRON_SVG, panel_id, links,
            )
        )
    return (
        '<div class="nav-drawer-backdrop" id="navDrawerBackdrop" hidden></div>'
        '<div class="nav-drawer" id="navDrawer" role="dialog" aria-modal="true" aria-label="Site navigation" hidden>'
        '<div class="nav-drawer-header">'
        '<a href="/" class="logo"><span class="logo-icon" aria-hidden="true">%s</span><span>%s</span></a>'
        '<button type="button" class="nav-drawer-close" id="navDrawerClose" aria-label="Close menu">%s</button>'
        '</div>'
        '<div class="nav-drawer-body">'
        '<a href="/" class="drawer-home-link">Home</a>'
        '%s'
        '</div>'
        '</div>' % (CAMERA_LOGO_SVG, html.escape(site["site_name"]), CLOSE_SVG, "".join(sections))
    )


def render_footer_mega(site, by_slug):
    rows = []
    for group in site["nav_groups"]:
        pairs = group_links(group, site, by_slug, text_field="footer_anchor")
        links = "".join('<a href="%s">%s</a>' % (url, html.escape(name)) for url, name in pairs)
        rows.append(
            '<div class="footer-mega-row"><div class="footer-mega-label">%s <span class="footer-mega-count">(%d)</span></div><div class="footer-mega-links">%s</div></div>'
            % (html.escape(group["label"]), len(pairs), links)
        )
    return "\n".join(rows)


def render_footer_company(site):
    return "".join('<a href="%s">%s</a>' % (l["href"], html.escape(l["label"])) for l in site["company_links"])


def breadcrumb_trail_for_tool(tool, site):
    if tool["slug"] == site["home_slug"]:
        return []
    return [("Home", "/"), (tool["nav_name"], None)]


def render_breadcrumbs(trail):
    if not trail:
        return ""
    items = []
    for label, url in trail:
        if url:
            items.append('<li><a href="%s">%s</a></li>' % (url, html.escape(label)))
        else:
            items.append('<li aria-current="page">%s</li>' % html.escape(label))
    return '<nav class="breadcrumbs" aria-label="Breadcrumb"><ol>%s</ol></nav>' % "".join(items)


# ---------------------------------------------------------------------------
# JSON-LD
# ---------------------------------------------------------------------------

# One linked @graph per page from schema.py (WebSite, Person, WebPage,
# BreadcrumbList, WebApplication, HowTo, Article, FAQPage) — replaces the
# separate WebApplication/WebSite/FAQPage/BreadcrumbList blocks this site
# used to emit.


# ---------------------------------------------------------------------------
# Page renderers
# ---------------------------------------------------------------------------

def apply_tokens(template, tokens):
    out = template
    for k, v in tokens.items():
        out = out.replace("{{%s}}" % k, v)
    return out


KATEX_VERSION = "0.16.11"
KATEX_BASE = "https://cdnjs.cloudflare.com/ajax/libs/KaTeX/%s" % KATEX_VERSION
MATH_MARKERS = ("$$", "\\(", "\\[")


def needs_math(tool):
    """True if this tool's article/FAQ contains a LaTeX delimiter ($$...$$ or
    \\(...\\)). Only those pages load KaTeX; every other page stays script-free."""
    text = tool.get("content_html", "") + "".join(q.get("answer", "") for q in tool.get("faq", []))
    return any(m in text for m in MATH_MARKERS)


def render_katex_head(tool):
    if not needs_math(tool):
        return ""
    return '<link rel="stylesheet" href="%s/katex.min.css" crossorigin="anonymous">' % KATEX_BASE


def render_katex_scripts(tool):
    if not needs_math(tool):
        return ""
    return (
        '<script src="%(b)s/katex.min.js" defer crossorigin="anonymous"></script>'
        '<script src="%(b)s/contrib/auto-render.min.js" defer crossorigin="anonymous"></script>'
        '<script>document.addEventListener("DOMContentLoaded",function(){var go=function(){'
        'if(!window.renderMathInElement)return setTimeout(go,50);'
        'renderMathInElement(document.querySelector("main")||document.body,{delimiters:['
        '{left:"$$",right:"$$",display:true},{left:"\\\\[",right:"\\\\]",display:true},'
        '{left:"\\\\(",right:"\\\\)",display:false}],throwOnError:false})};go()});</script>'
    ) % {"b": KATEX_BASE}


def add_table_captions(fragment):
    """Give every caption-less <table> a visually hidden <caption> taken from
    the nearest preceding <h2>/<h3>, so assistive tech announces what the
    table is without changing the visible layout."""
    out, pos = [], 0
    for m in re.finditer(r"<table\b[^>]*>(?!\s*<caption)", fragment):
        heads = re.findall(r"<h[23][^>]*>(.*?)</h[23]>", fragment[:m.start()], flags=re.S)
        out.append(fragment[pos:m.end()])
        pos = m.end()
        if heads:
            text = re.sub(r"<[^>]+>", "", heads[-1]).strip()
            out.append('<caption class="sr-only">%s</caption>' % text)
    out.append(fragment[pos:])
    return "".join(out)


def add_th_scope(fragment):
    """Give every bare <th> a scope: "row" when its <tr> also holds <td>s
    (a row header), otherwise "col" (a column header)."""
    def per_row(m):
        row = m.group(0)
        scope = "row" if "<td" in row else "col"
        return re.sub(r"<th>", '<th scope="%s">' % scope, row)
    return re.sub(r"<tr>.*?</tr>", per_row, fragment, flags=re.S)


def render_page(tool, site, by_slug, tools, template, critical_css=""):
    canonical = "https://%s%s" % (site["domain"], tool_url(tool, site))
    trail = breadcrumb_trail_for_tool(tool, site)
    card = tool.get("card", {})
    extra_scripts = "".join('<script src="%s" defer></script>' % url for url in card.get("extra_scripts", []))
    extra_scripts += render_katex_scripts(tool)
    tool_warning = ""
    if card.get("tool_warning"):
        tool_warning = '<div class="tool-warning">%s</div>' % card["tool_warning"]
    data_attrs = "".join(' data-%s="%s"' % (k, html.escape(str(v))) for k, v in card.get("data_attrs", {}).items())
    code_snippet = ""
    if tool.get("code_snippet"):
        code_snippet = '<div class="code-snippet"><span class="code-label">%s</span><pre>%s</pre></div>' % (
            html.escape(tool.get("code_snippet_label", "Example")), html.escape(tool["code_snippet"])
        )

    tokens = {
        "META_DESCRIPTION": html.escape(tool["meta_description"]),
        "SITE_NAME": site["site_name"],
        "CANONICAL_URL": canonical,
        "META_TITLE": html.escape(tool["h1"]),
        "JSON_LD": json_ld_graph(SCHEMA[0].tool(
            tool, canonical, [(l, u) for l, u in trail] or [("Home", "/")],
            *SCHEMA[0].dates("src/content/%s.json" % tool["slug"], tool))),
        "AUTHOR_NAME": html.escape(site["author"]["name"]),
        "CRITICAL_CSS": critical_css,
        "GA_SNIPPET": render_ga_snippet(),
        "ADSENSE_LOADER": render_adsense_loader(),
        "KATEX_HEAD": render_katex_head(tool),
        "ADSENSE_HEADER": render_adsense_header(),
        "CATEGORY_DROPDOWNS": render_category_dropdowns(site, by_slug),
        "MORE_MENU": render_more_menu(site, by_slug),
        "MOBILE_DRAWER": render_mobile_drawer(site, by_slug),
        "HAMBURGER_ICON": HAMBURGER_SVG,
        "BREADCRUMBS": render_breadcrumbs(trail),
        "H1": html.escape(tool["h1"]),
        "SUBTITLE": tool["subtitle"],
        "CLUSTER": tool.get("cluster", "camera-core"),
        "TOOL_MODE": card.get("mode", ""),
        "TOOL_LAYOUT": card.get("layout", "raw"),
        "TOOL_DATA_ATTRS": data_attrs,
        "TOOL_CARD_BODY": add_th_scope(add_table_captions(render_tool_card_body(tool))),
        "TOOL_WARNING": tool_warning,
        "TOOL_EXTRA_SCRIPTS": extra_scripts,
        "TOOL_SCRIPT": tool.get("script", ""),
        "CODE_SNIPPET": code_snippet,
        "MAIN_SECTIONS": add_th_scope(add_table_captions(render_main_sections(tool, site))),
        "FOOTER_TAGLINE": site["footer_tagline"],
        "FOOTER_MEGA": render_footer_mega(site, by_slug),
        "FOOTER_COMPANY": render_footer_company(site),
        "YEAR": "2026",
    }
    return apply_tokens(template, tokens)


def render_info_page(page, site, by_slug, template, critical_css=""):
    canonical = "https://%s/%s" % (site["domain"], page["slug"])
    trail = [("Home", "/"), (page["h1"], None)]
    published, modified = SCHEMA[0].dates("src/build_data.py", page)
    sitemap_items = None
    if page["slug"] == "sitemap":
        sitemap_items = [(t["nav_name"], tool_url(t, site)) for g in site["nav_groups"]
                         for t in (by_slug[x] for x in g.get("slugs", []))]
    if page["slug"] == "about":
        tail = author_box(site, page["slug"], published, modified)
    else:
        tail = '<section class="block"><div class="article">%s</div></section>' % updated_line(page["slug"], modified)
    tokens = {
        "META_DESCRIPTION": html.escape(page["meta_description"]),
        "SITE_NAME": site["site_name"],
        "CANONICAL_URL": canonical,
        "META_TITLE": html.escape(page["h1"]),
        "CRITICAL_CSS": critical_css,
        "GA_SNIPPET": render_ga_snippet(),
        "CATEGORY_DROPDOWNS": render_category_dropdowns(site, by_slug),
        "MORE_MENU": render_more_menu(site, by_slug),
        "MOBILE_DRAWER": render_mobile_drawer(site, by_slug),
        "HAMBURGER_ICON": HAMBURGER_SVG,
        "JSON_LD": json_ld_graph(SCHEMA[0].info(page, canonical, trail, published, modified, sitemap_items)),
        "AUTHOR_NAME": html.escape(site["author"]["name"]),
        "BREADCRUMBS": render_breadcrumbs(trail),
        "H1": html.escape(page["h1"]),
        "SUBTITLE": page.get("subtitle", ""),
        "PAGE_CONTENT": add_th_scope(add_table_captions(render_info_content(page))),
        "PAGE_TAIL": tail,
        "FOOTER_TAGLINE": site["footer_tagline"],
        "FOOTER_MEGA": render_footer_mega(site, by_slug),
        "FOOTER_COMPANY": render_footer_company(site),
        "YEAR": "2026",
    }
    return apply_tokens(template, tokens)


def render_404_page(site, by_slug, template_404, critical_css=""):
    url = "https://%s/404" % site["domain"]
    tokens = {
        "JSON_LD": json_ld_graph(SCHEMA[0].plain(url, [("Home", "/"), ("Page not found", None)], "Page not found",
                                                 "The page you asked for doesn't exist or has moved.")),
        "AUTHOR_NAME": html.escape(site["author"]["name"]),
        "SITE_NAME": site["site_name"],
        "CRITICAL_CSS": critical_css,
        "GA_SNIPPET": render_ga_snippet(),
        "CATEGORY_DROPDOWNS": render_category_dropdowns(site, by_slug),
        "MORE_MENU": render_more_menu(site, by_slug),
        "MOBILE_DRAWER": render_mobile_drawer(site, by_slug),
        "HAMBURGER_ICON": HAMBURGER_SVG,
        "FOOTER_TAGLINE": site["footer_tagline"],
        "FOOTER_MEGA": render_footer_mega(site, by_slug),
        "FOOTER_COMPANY": render_footer_company(site),
        "YEAR": "2026",
    }
    return apply_tokens(template_404, tokens)


# ---------------------------------------------------------------------------
# Minification / build-tool helpers (pinned versions via npx, same as
# passwordhive/hexcalculator — see hexcalculator's CLAUDE.md "Minification"
# section for the rationale behind each tool choice)
# ---------------------------------------------------------------------------

def run_npx(args, cwd=None, env=None):
    cmd = ["npx", "--yes"] + args
    result = subprocess.run(cmd, cwd=cwd, env=env, capture_output=True, text=True)
    if result.returncode != 0:
        raise RuntimeError("Command failed: %s\nSTDOUT:\n%s\nSTDERR:\n%s" % (" ".join(cmd), result.stdout, result.stderr))
    return result


def minify_css_file(src, dst):
    run_npx([CLEAN_CSS_PKG, "-o", dst, src])


def minify_html_dir(src_dir, dst_dir):
    run_npx([
        HTML_MINIFIER_PKG,
        "--input-dir", src_dir,
        "--output-dir", dst_dir,
        "--file-ext", "html",
        "--collapse-whitespace",
        "--collapse-boolean-attributes",
        "--remove-comments",
        "--minify-css", "true",
        "--minify-js", "true",
        "--case-sensitive",
    ])


def build_typography_css(out_css, out_css_min):
    typo_dir = os.path.join(BASE_DIR, "typography")
    with tempfile.TemporaryDirectory() as tmp:
        subprocess.run(
            ["npm", "install", "--no-save", "--prefix", tmp, TAILWIND_PKG, TAILWIND_TYPOGRAPHY_PKG],
            check=True, capture_output=True, text=True,
        )
        env = dict(os.environ)
        env["NODE_PATH"] = os.path.join(tmp, "node_modules")
        binary = os.path.join(tmp, "node_modules", ".bin", "tailwindcss")
        subprocess.run(
            [binary, "-c", "tailwind.config.js", "-i", "input.css", "-o", out_css],
            check=True, capture_output=True, text=True, env=env, cwd=typo_dir,
        )
    minify_css_file(out_css, out_css_min)


def find_chrome_executable():
    if os.environ.get("PUPPETEER_EXECUTABLE_PATH"):
        return os.environ["PUPPETEER_EXECUTABLE_PATH"]
    candidates = [
        "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
        "/usr/bin/google-chrome",
        "/usr/bin/google-chrome-stable",
        "/usr/bin/chromium-browser",
        "/usr/bin/chromium",
        "C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe",
    ]
    for c in candidates:
        if os.path.exists(c):
            return c
    return None


CRITICAL_EXTRACT_SCRIPT = r'''
import { generate as criticalGenerate } from "critical";
import fs from "fs";
const [,, url, outFile] = process.argv;
const dimensions = [
  { width: 390, height: 844 },
  { width: 768, height: 1024 },
  { width: 1440, height: 900 },
];
try {
  const { css } = await criticalGenerate({
    inline: false,
    base: process.env.CRITICAL_BASE,
    src: url,
    dimensions,
    penthouse: {
      puppeteer: { executablePath: process.env.PUPPETEER_EXECUTABLE_PATH },
    },
  });
  fs.writeFileSync(outFile, css);
} catch (err) {
  console.error(err);
  process.exit(1);
}
'''

CRITICAL_TOOL_SOURCES = ["webcam-test-online", "microphone-test-online"]
CRITICAL_PAGE_SOURCES = ["about"]


def build_critical_css(by_slug, site, tools, template, template_page, styles_min_path, typography_min_path):
    chrome = find_chrome_executable()
    if not chrome:
        raise RuntimeError(
            "No Chrome/Chromium found for critical-CSS extraction. Set PUPPETEER_EXECUTABLE_PATH "
            "or install Google Chrome, or run with --no-minify to skip this step."
        )
    with tempfile.TemporaryDirectory() as tmp:
        shutil.copy(styles_min_path, os.path.join(tmp, "styles.min.css"))
        shutil.copy(typography_min_path, os.path.join(tmp, "typography.min.css"))
        for slug in CRITICAL_TOOL_SOURCES:
            tool = by_slug[slug]
            html_out = render_page(tool, site, by_slug, tools, template, critical_css="")
            with open(os.path.join(tmp, "%s.html" % slug), "w") as f:
                f.write(html_out)
        for slug in CRITICAL_PAGE_SOURCES:
            page = next(p for p in site["_pages"] if p["slug"] == slug)
            html_out = render_info_page(page, site, by_slug, template_page, critical_css="")
            with open(os.path.join(tmp, "%s.html" % slug), "w") as f:
                f.write(html_out)

        with tempfile.TemporaryDirectory() as npm_tmp:
            # puppeteer@25.13.0 was published to npm without its matching
            # puppeteer-core@25.13.0 (2026-10-08), so an unpinned install of
            # critical fails with ETARGET. Pin both to the last good release
            # via overrides; drop this once upstream publishes a fixed version.
            name, _, version = CRITICAL_PKG.rpartition("@")
            with open(os.path.join(npm_tmp, "package.json"), "w") as f:
                json.dump({
                    "private": True,
                    "dependencies": {name: version},
                    "overrides": {"puppeteer": "25.12.0", "puppeteer-core": "25.12.0"},
                }, f)
            subprocess.run(
                ["npm", "install", "--no-save", "--prefix", npm_tmp],
                check=True, capture_output=True, text=True,
            )
            script_path = os.path.join(npm_tmp, "extract.mjs")
            with open(script_path, "w") as f:
                f.write(CRITICAL_EXTRACT_SCRIPT)

            env = dict(os.environ)
            env["PUPPETEER_EXECUTABLE_PATH"] = chrome
            env["CRITICAL_BASE"] = tmp

            def extract(slug):
                out_file = os.path.join(tmp, "%s.critical.css" % slug)
                result = subprocess.run(
                    ["node", script_path, "%s.html" % slug, out_file],
                    capture_output=True, text=True, env=env, cwd=tmp,
                )
                if result.returncode != 0:
                    raise RuntimeError(
                        "critical CSS extraction failed for %s:\nSTDOUT:\n%s\nSTDERR:\n%s"
                        % (slug, result.stdout, result.stderr)
                    )
                with open(out_file) as f:
                    return f.read()

            tool_css_parts = [extract(slug) for slug in CRITICAL_TOOL_SOURCES]
            page_css_parts = [extract(slug) for slug in CRITICAL_PAGE_SOURCES]
    return "\n".join(tool_css_parts), "\n".join(page_css_parts)


# ---------------------------------------------------------------------------
# Site infra files
# ---------------------------------------------------------------------------

def write_robots_and_sitemap(site, tools, pages, out_dir):
    domain = site["domain"]
    with open(os.path.join(out_dir, "robots.txt"), "w") as f:
        f.write("User-agent: *\nAllow: /\n\nSitemap: https://%s/sitemap.xml\n" % domain)

    urls = ["/"] + ["/%s" % t["slug"] for t in tools if t["slug"] != site["home_slug"]] + ["/%s" % p["slug"] for p in pages]
    entries = "".join(
        "<url><loc>https://%s%s</loc></url>" % (domain, u) for u in urls
    )
    with open(os.path.join(out_dir, "sitemap.xml"), "w") as f:
        f.write('<?xml version="1.0" encoding="UTF-8"?><urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">%s</urlset>' % entries)

    # Same authorized-seller declaration as the old legacy-bootstrap-site/
    # ads.txt this replaces — just re-derived from ADSENSE_CLIENT so it
    # can't drift from the loader/ad-unit markup above.
    with open(os.path.join(out_dir, "ads.txt"), "w") as f:
        f.write("google.com, %s, DIRECT, f08c47fec0942fa0\n" % ADSENSE_CLIENT.replace("ca-", ""))


def write_redirect_stubs(site, tools, pages, out_dir):
    """One tiny meta-refresh + canonical page per old legacy-site URL in
    src/redirects.json. GitHub Pages can't send a real 301, so this is the
    standard fallback (Google treats a 0s meta refresh + canonical as
    permanent). Stubs are deliberately left out of sitemap.xml."""
    with open(os.path.join(BASE_DIR, "redirects.json")) as f:
        redirects = {k: v for k, v in json.load(f).items() if not k.startswith("_")}
    valid = {t["slug"] for t in tools} | {p["slug"] for p in pages}
    for old, new in redirects.items():
        if new and new not in valid:
            raise SystemExit("redirects.json: %r -> unknown page %r" % (old, new))
        if old in valid:
            raise SystemExit("redirects.json: %r collides with a real page" % old)
        if new and new != site["home_slug"]:
            target = "https://%s/%s" % (site["domain"], new)
        else:
            target = "https://%s/" % site["domain"]
        with open(os.path.join(out_dir, "%s.html" % old), "w") as f:
            f.write(
                '<!DOCTYPE html><html lang="en"><head><meta charset="utf-8">'
                '<meta name="viewport" content="width=device-width,initial-scale=1">'
                '<title>Page moved</title>'
                '<link rel="canonical" href="%(t)s">'
                '<meta http-equiv="refresh" content="0; url=%(t)s">'
                '<script>location.replace("%(t)s")</script></head>'
                '<body><p>This page has moved to <a href="%(t)s">%(t)s</a>.</p></body></html>\n'
                % {"t": target}
            )
    return len(redirects)


# ---------------------------------------------------------------------------
# main
# ---------------------------------------------------------------------------

def main():
    do_minify = "--no-minify" not in sys.argv

    with open(os.path.join(DATA_DIR, "site.json")) as f:
        site = json.load(f)
    with open(os.path.join(DATA_DIR, "tools.json")) as f:
        tools = json.load(f)
    with open(os.path.join(DATA_DIR, "pages.json")) as f:
        pages = json.load(f)

    by_slug = {t["slug"]: t for t in tools}
    SCHEMA[0] = schema.Schema(site, site["author"], schema.load_git_dates(os.path.dirname(BASE_DIR)))
    site["_pages"] = pages  # only used internally by build_critical_css()

    with open(os.path.join(BASE_DIR, "template.html")) as f:
        template = f.read()
    with open(os.path.join(BASE_DIR, "template-page.html")) as f:
        template_page = f.read()
    with open(os.path.join(BASE_DIR, "template-404.html")) as f:
        template_404 = f.read()
    with open(os.path.join(BASE_DIR, "styles.css")) as f:
        styles_src = f.read()

    if os.path.exists(OUTPUT_DIR):
        for name in os.listdir(OUTPUT_DIR):
            if name == "fonts":
                continue
            path = os.path.join(OUTPUT_DIR, name)
            if os.path.isdir(path):
                shutil.rmtree(path)
            else:
                os.remove(path)
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    os.makedirs(os.path.join(OUTPUT_DIR, "fonts"), exist_ok=True)
    for fname in ("dm-sans-variable.woff2", "jetbrains-mono-variable.woff2"):
        shutil.copy(os.path.join(BASE_DIR, "fonts", fname), os.path.join(OUTPUT_DIR, "fonts", fname))
    favicon_path = os.path.join(BASE_DIR, "favicon.ico")
    if os.path.exists(favicon_path):
        shutil.copy(favicon_path, os.path.join(OUTPUT_DIR, "favicon.ico"))
    # Shared nav/footer JS (see src/nav.js) — identical behaviour across all
    # three templates, so it's one static file instead of being duplicated
    # verbatim in every page's inline <script>.
    shutil.copy(os.path.join(BASE_DIR, "nav.js"), os.path.join(OUTPUT_DIR, "nav.js"))
    # Binary/opaque assets that can't be derived from site.json — currently
    # just the Google Search Console verification file carried over from the
    # old site (do not modify its contents; it proves domain ownership).
    static_dir = os.path.join(BASE_DIR, "static")
    if os.path.isdir(static_dir):
        for fname in os.listdir(static_dir):
            shutil.copy(os.path.join(static_dir, fname), os.path.join(OUTPUT_DIR, fname))

    # Per-tool infographic SVGs synthesized by the seo-optimize pipeline
    # (open-source-on-page-seo-optimizer Phase 3b) — one subdirectory per
    # tool at content_images/<slug>/, referenced from that tool's
    # content_html via /images/<slug>/<file>.svg. Copied verbatim (SVGs
    # need no minification) so the merge script and this generator agree
    # on where images live without either one hand-coding a fixed list.
    content_images_dir = os.path.join(BASE_DIR, "content_images")
    if os.path.isdir(content_images_dir):
        for slug in os.listdir(content_images_dir):
            slug_src_dir = os.path.join(content_images_dir, slug)
            if not os.path.isdir(slug_src_dir):
                continue
            slug_dest_dir = os.path.join(OUTPUT_DIR, "images", slug)
            os.makedirs(slug_dest_dir, exist_ok=True)
            for fname in os.listdir(slug_src_dir):
                shutil.copy(os.path.join(slug_src_dir, fname), os.path.join(slug_dest_dir, fname))

    tool_critical_css = ""
    page_critical_css = ""

    if do_minify:
        styles_min_path = os.path.join(OUTPUT_DIR, "styles.min.css")
        typography_css_path = os.path.join(OUTPUT_DIR, "typography.css")
        typography_min_path = os.path.join(OUTPUT_DIR, "typography.min.css")

        with tempfile.NamedTemporaryFile("w", suffix=".css", delete=False) as f:
            f.write(styles_src)
            styles_tmp_path = f.name
        minify_css_file(styles_tmp_path, styles_min_path)
        os.remove(styles_tmp_path)

        build_typography_css(typography_css_path, typography_min_path)
        os.remove(typography_css_path)

        tool_critical_css, page_critical_css = build_critical_css(
            by_slug, site, tools, template, template_page, styles_min_path, typography_min_path
        )

        render_dir = tempfile.mkdtemp(prefix="webcamtest_render_")
    else:
        render_dir = OUTPUT_DIR
        with open(os.path.join(OUTPUT_DIR, "styles.min.css"), "w") as f:
            f.write(styles_src)
        with open(os.path.join(OUTPUT_DIR, "typography.min.css"), "w") as f:
            f.write("")

    for tool in tools:
        out_html = render_page(tool, site, by_slug, tools, template, critical_css=tool_critical_css)
        filename = "index.html" if tool["slug"] == site["home_slug"] else "%s.html" % tool["slug"]
        with open(os.path.join(render_dir, filename), "w") as f:
            f.write(out_html)

    for page in pages:
        out_html = render_info_page(page, site, by_slug, template_page, critical_css=page_critical_css)
        with open(os.path.join(render_dir, "%s.html" % page["slug"]), "w") as f:
            f.write(out_html)

    out_html = render_404_page(site, by_slug, template_404, critical_css=page_critical_css)
    with open(os.path.join(render_dir, "404.html"), "w") as f:
        f.write(out_html)

    n_redirects = write_redirect_stubs(site, tools, pages, render_dir)

    write_robots_and_sitemap(site, tools, pages, render_dir if not do_minify else OUTPUT_DIR)
    if do_minify:
        write_robots_and_sitemap(site, tools, pages, render_dir)

    if do_minify:
        minify_html_dir(render_dir, OUTPUT_DIR)
        shutil.rmtree(render_dir)

    print("Built %d tool pages + %d info pages + %d redirect stubs into %s (%s)" % (
        len(tools), len(pages), n_redirects, OUTPUT_DIR, "minified" if do_minify else "unminified"
    ))


if __name__ == "__main__":
    main()
