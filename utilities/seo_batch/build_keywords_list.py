#!/usr/bin/env python3
"""
Generate utilities/seo_batch/keywords.txt (the batch_run.py-format keyword
list: "Tool Name | search query | output-slug") for all 44 tools, driven by
this repo's own data rather than a hand-maintained duplicate list.

Primary keyword per tool comes from utilities/silo_linking's own
ANCHOR_VARIANTS/CLUSTERS (the same phrase already used as that tool's silo
anchor text) since it's the closest thing this repo has to a canonical
"this tool's primary keyword" registry. Falls back to the tool's slug
(hyphens -> spaces) for any tool CLUSTERS doesn't cover (currently none —
see the assertion below).

Only covers actual interactive tool pages — nav_groups whose `short_label` is
"Guides" (currently just "Camera Reference": webcam-not-working-troubleshooting-
guide, camera-permissions-guide-windows-mac-android-ios, webcam-resolution-
standards-reference, camera-test-vs-webcam-test-explained, webcam-specs-
comparison-database, use-phone-as-webcam-guide) are skipped. These are guide/
reference/comparison content, not a "run a test" tool, and in practice the
/seo-optimize pipeline has mismatched them: with no distinct competitor content
niche of their own for their keyword, it writes generic webcam-test-tool
content instead of respecting the page's actual (non-test) purpose — see
CLAUDE.md's SEO Batch Pipeline section, 2026-09-18 entry, for two real examples
that had to be reverted. Guide pages stay hand-authored for now.

Run whenever a new tool is added to src/content/, before a fresh batch run:
    python3 utilities/seo_batch/build_keywords_list.py
"""
import json
import os
import sys

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(REPO_ROOT, "utilities", "silo_linking"))
import generate_silo_rotation as silo  # noqa: E402


def non_tool_slugs():
    """Slugs belonging to a nav_group labeled 'Guides' — reference/comparison
    content, not an interactive tool, and the current source of every
    content-mismatch case found so far. See module docstring."""
    with open(os.path.join(REPO_ROOT, "src", "data", "site.json")) as f:
        site = json.load(f)
    skip = set()
    for group in site["nav_groups"]:
        if group.get("short_label") == "Guides":
            skip.update(group["slugs"])
    return skip


def slug_to_keyword_map():
    mapping = {}
    for cluster in silo.CLUSTERS:
        pillar = cluster["pillar"]
        mapping[pillar["file"].replace(".html", "")] = pillar["anchor"]
        for entry in cluster.get("subsilos", []):
            mapping[entry["file"].replace(".html", "")] = entry["anchor"]
        for group in cluster["groups"]:
            for entry in group:
                mapping[entry["file"].replace(".html", "")] = entry["anchor"]
    return mapping


def main():
    with open(os.path.join(REPO_ROOT, "src", "data", "tools.json")) as f:
        tools = json.load(f)
    slug_to_keyword = slug_to_keyword_map()
    skip = non_tool_slugs()

    lines = []
    missing = []
    excluded = []
    for tool in sorted(tools, key=lambda t: t["slug"]):
        slug = tool["slug"]
        if slug in skip:
            excluded.append(slug)
            continue
        keyword = slug_to_keyword.get(slug)
        if keyword is None:
            missing.append(slug)
            keyword = slug.replace("-", " ")
        lines.append("%s | %s | %s" % (keyword.title(), keyword, slug))

    out_path = os.path.join(REPO_ROOT, "utilities", "seo_batch", "keywords.txt")
    with open(out_path, "w") as f:
        f.write("\n".join(lines) + "\n")

    print("Wrote %d keywords to %s (%d guide/reference page(s) excluded)" % (len(lines), out_path, len(excluded)))
    if excluded:
        print("  excluded: %s" % excluded)
    if missing:
        print("warning: %d slug(s) had no CLUSTERS anchor, fell back to slug text: %s" % (len(missing), missing))


if __name__ == "__main__":
    main()
