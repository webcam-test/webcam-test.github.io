#!/usr/bin/env python3
"""
Monthly silo link rotation for webcamtest.

Standalone port — same self-contained, no-shared-core-module shape as
mic-tests.github.io's own utilities/silo_linking/generate_silo_rotation.py
(no `sites/` subfolder, no import of a shared engine module). This replaces
the version that used to live in the coffee_can_checker_tools_project
monorepo at utilities/silo_linking/sites/webcamtest.py (which imported a
shared core.py used by several other sites in that monorepo) — this site is
moving to its own standalone repo (webcam-test.github.io), so it needs its
own copy of whatever engine logic it actually uses, same as mic-tests.

Two independent pillar clusters — Camera and Audio — covering all 44 tools.
Per cluster:
  Pillar     -> 1 page        slot_a: single link down, rotated monthly
                               among its sub-silos (hoards authority via
                               exactly one outbound link)
  Sub-silos  -> up to 5 pages slot_a: up to pillar
                               slot_b/c: horizontal neighbor sub-silos
                                         (order shuffled monthly)
                               slot_d: down to its own chain's first
                                       supporting page
  Supporting -> rest          slot_a: up to its sub-silo
                               slot_b/c: prev/next in its own chain —
                                         chains bridge into each other
                                         linearly within the cluster (last
                                         chain does NOT wrap back to the
                                         first)

Anchor text is always the target page's own primary keyword, fixed (not
rotated across variants). Sentence templates (6 per family) are grouped into
exactly two families: "live_test" for the 37 tools that acquire a real
camera/mic via getUserMedia, and "guide" for the 7 reference/how-to pages
that don't touch a device.

HTML files are patched in-place using comment markers:
  <!-- SILO_START:slot_a -->sentence with link<!-- SILO_END:slot_a -->

Run this AFTER the site's own build step (build_data.py + generate.py),
never before — the build has no knowledge of the SILO_START/SILO_END
markers this script injects and will silently wipe them if run afterward.

Run standalone from the repo root:
  python3 utilities/silo_linking/generate_silo_rotation.py
  python3 utilities/silo_linking/generate_silo_rotation.py --dry-run
  python3 utilities/silo_linking/generate_silo_rotation.py --date=2026-09
"""

import datetime
import hashlib
import html as html_lib
import json
import os
import random
import re
import sys

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
PAGES_DIR = os.path.join(REPO_ROOT, "public")
CONTENT_DIR = os.path.join(REPO_ROOT, "src", "content")

# ---------------------------------------------------------------------------
# Cluster structure: 2 independent pillar/sub-silo/supporting silos
# ---------------------------------------------------------------------------

CLUSTERS = [
    {
        "id": 1,  # Camera
        "pillar": {"file": "index.html", "anchor": "webcam test", "url": "/"},
        "subsilos": [
            {"file": "webcam-live-filter-preview.html", "anchor": "webcam filters", "url": "/webcam-live-filter-preview"},
            {"file": "use-phone-as-webcam-guide.html", "anchor": "use phone as webcam", "url": "/use-phone-as-webcam-guide"},
            {"file": "webcam-video-recorder-online.html", "anchor": "webcam video recorder", "url": "/webcam-video-recorder-online"},
            {"file": "front-camera-test-online.html", "anchor": "front camera test", "url": "/front-camera-test-online"},
            {"file": "webcam-mirror-vs-natural-view-test.html", "anchor": "webcam mirror test", "url": "/webcam-mirror-vs-natural-view-test"},
        ],
        "groups": [
            [
                {"file": "webcam-rule-of-thirds-composition-grid.html", "anchor": "rule of thirds grid", "url": "/webcam-rule-of-thirds-composition-grid"},
                {"file": "webcam-autofocus-test.html", "anchor": "webcam autofocus test", "url": "/webcam-autofocus-test"},
                {"file": "webcam-sharpness-focus-test.html", "anchor": "webcam focus test", "url": "/webcam-sharpness-focus-test"},
                {"file": "webcam-lighting-exposure-test.html", "anchor": "webcam lighting test", "url": "/webcam-lighting-exposure-test"},
                {"file": "webcam-low-light-noise-test.html", "anchor": "webcam low light test", "url": "/webcam-low-light-noise-test"},
                {"file": "webcam-color-accuracy-test.html", "anchor": "webcam color test", "url": "/webcam-color-accuracy-test"},
            ],
            [
                {"file": "camera-permissions-guide-windows-mac-android-ios.html", "anchor": "camera permissions", "url": "/camera-permissions-guide-windows-mac-android-ios"},
                {"file": "webcam-not-working-troubleshooting-guide.html", "anchor": "webcam not working", "url": "/webcam-not-working-troubleshooting-guide"},
                {"file": "webcam-resolution-standards-reference.html", "anchor": "webcam resolution chart", "url": "/webcam-resolution-standards-reference"},
                {"file": "webcam-specs-comparison-database.html", "anchor": "webcam specs comparison", "url": "/webcam-specs-comparison-database"},
                {"file": "camera-test-vs-webcam-test-explained.html", "anchor": "camera test vs webcam test", "url": "/camera-test-vs-webcam-test-explained"},
            ],
            [
                {"file": "webcam-photo-capture-online.html", "anchor": "webcam photo capture", "url": "/webcam-photo-capture-online"},
            ],
            [
                {"file": "phone-camera-resolution-checker.html", "anchor": "phone camera resolution", "url": "/phone-camera-resolution-checker"},
                {"file": "mobile-camera-test-online.html", "anchor": "mobile camera test", "url": "/mobile-camera-test-online"},
                {"file": "rear-camera-test-online.html", "anchor": "rear camera test", "url": "/rear-camera-test-online"},
                {"file": "phone-camera-zoom-test.html", "anchor": "phone camera zoom test", "url": "/phone-camera-zoom-test"},
                {"file": "phone-camera-flash-torch-test.html", "anchor": "phone flashlight test", "url": "/phone-camera-flash-torch-test"},
                {"file": "phone-camera-orientation-test.html", "anchor": "phone camera orientation test", "url": "/phone-camera-orientation-test"},
                {"file": "used-phone-camera-inspection-checklist.html", "anchor": "check used phone camera", "url": "/used-phone-camera-inspection-checklist"},
            ],
            [
                {"file": "webcam-side-by-side-comparison.html", "anchor": "webcam comparison", "url": "/webcam-side-by-side-comparison"},
                {"file": "is-my-camera-being-used-check.html", "anchor": "is my camera on", "url": "/is-my-camera-being-used-check"},
                {"file": "webcam-fullscreen-viewer.html", "anchor": "webcam fullscreen", "url": "/webcam-fullscreen-viewer"},
                {"file": "webcam-camera-information-report.html", "anchor": "what camera do i have", "url": "/webcam-camera-information-report"},
                {"file": "webcam-fps-frame-rate-checker.html", "anchor": "webcam fps test", "url": "/webcam-fps-frame-rate-checker"},
                {"file": "webcam-maximum-resolution-detector.html", "anchor": "webcam max resolution", "url": "/webcam-maximum-resolution-detector"},
                {"file": "webcam-latency-delay-test.html", "anchor": "webcam latency test", "url": "/webcam-latency-delay-test"},
            ],
        ],
    },
    {
        "id": 2,  # Audio
        "pillar": {"file": "microphone-test-online.html", "anchor": "microphone test", "url": "/microphone-test-online"},
        "subsilos": [
            {"file": "speaker-test-online.html", "anchor": "speaker test", "url": "/speaker-test-online"},
            {"file": "online-hearing-frequency-test.html", "anchor": "hearing test online", "url": "/online-hearing-frequency-test"},
            {"file": "microphone-record-playback-test.html", "anchor": "microphone record test", "url": "/microphone-record-playback-test"},
        ],
        "groups": [
            [
                {"file": "left-right-stereo-channel-test.html", "anchor": "stereo left right test", "url": "/left-right-stereo-channel-test"},
                {"file": "speaker-polarity-phase-test.html", "anchor": "speaker polarity test", "url": "/speaker-polarity-phase-test"},
                {"file": "subwoofer-bass-test-online.html", "anchor": "subwoofer test", "url": "/subwoofer-bass-test-online"},
            ],
            [
                {"file": "audio-latency-delay-test.html", "anchor": "audio latency test", "url": "/audio-latency-delay-test"},
                {"file": "audio-frequency-sweep-20hz-20khz.html", "anchor": "frequency sweep test", "url": "/audio-frequency-sweep-20hz-20khz"},
            ],
            [
                {"file": "microphone-echo-test.html", "anchor": "mic echo test", "url": "/microphone-echo-test"},
                {"file": "microphone-quality-spectrum-analyzer.html", "anchor": "microphone spectrum analyzer", "url": "/microphone-quality-spectrum-analyzer"},
                {"file": "microphone-input-level-meter.html", "anchor": "mic level meter", "url": "/microphone-input-level-meter"},
            ],
        ],
    },
]

# ---------------------------------------------------------------------------
# Injection targets — positional, computed per tool rather than hardcoded.
# template.html renders {{TOOL_CARD_BODY}} BEFORE {{MAIN_SECTIONS}}
# (content_html), and every tool-panel header inside the card is itself an
# <h2> (e.g. "Live Camera Preview", "Recording") — so a flat h2-index of
# 0/1/2 would land inside the TOOL CARD on any page whose card has >=1 panel
# heading, not in the article prose. Real per-tool card <h2> counts range
# from 1 to 3 (checked across all 44 content/<slug>.json's own
# card.fields_html) — there's no fixed offset that works for every page.
#
# slot_a lands on the subtitle paragraph (<h1> immediately followed by
# <p class="subtitle">). slot_b/c/d target the 1st/2nd/3rd REAL content <h2>
# — i.e. heading_index = that tool's own card <h2> count, +0/+1/+2 —
# computed per tool below by reading its own content/<slug>.json.
# ---------------------------------------------------------------------------


def _file_to_slug(file: str) -> str:
    return "webcam-test-online" if file == "index.html" else file[:-len(".html")]


def _card_h2_count(slug: str) -> int:
    path = os.path.join(CONTENT_DIR, f"{slug}.json")
    with open(path, encoding="utf-8") as f:
        data = json.load(f)
    return data.get("card", {}).get("fields_html", "").count("<h2")


_ALL_TOOLS = []
for _cluster in CLUSTERS:
    _ALL_TOOLS.append(_cluster["pillar"])
    _ALL_TOOLS.extend(_cluster["subsilos"])
    for _group in _cluster["groups"]:
        _ALL_TOOLS.extend(_group)

INJECTION_TARGETS: dict = {}
for _t in _ALL_TOOLS:
    _n = _card_h2_count(_file_to_slug(_t["file"]))
    INJECTION_TARGETS[_t["file"]] = {
        "slot_a": ("h1", None, 0, 0),
        "slot_b": ("h2", None, 0, _n),
        "slot_c": ("h2", None, 0, _n + 1),
        "slot_d": ("h2", None, 0, _n + 2),
    }

# ---------------------------------------------------------------------------
# Anchor-text variant pools — one pool per tool's primary keyword, mirroring
# passwordhive.py's own ANCHOR_VARIANTS (individual_websites/passwordhive/
# utilities/silo_linking sibling in the coffee_can_checker_tools_project
# monorepo this pipeline was originally built in). Unlike passwordhive's
# mechanical suffix-detection generator (its keyword vocabulary — "X
# generator"/"X checker"/"X calculator" — is regular enough for a formula),
# camera/audio keywords are too irregular for one blind template ("is my
# camera on", "what camera do i have" are already question-form; "free is
# my camera on" or "is my camera on online" would read as broken English) —
# so these are hand-picked per tool instead: the primary keyword itself,
# one free/online long-tail variation, one secondary/related phrasing, and
# one contextual/LSI term pulled from what that specific tool actually
# measures or does (grounded in each tool's own content_html/faq, not
# generic filler).
ANCHOR_VARIANTS: dict = {
    # --- Camera Core ---
    "webcam test": ["webcam test", "free webcam test online", "test my webcam", "check webcam resolution and specs"],
    "what camera do i have": ["what camera do i have", "check what camera do i have", "find out what camera do i have", "webcam device information lookup"],
    "webcam max resolution": ["webcam max resolution", "webcam maximum resolution detector", "find your webcam's highest resolution", "webcam native resolution check"],
    "webcam fps test": ["webcam fps test", "webcam frame rate checker", "check webcam fps online", "webcam frames per second test"],
    "webcam fullscreen": ["webcam fullscreen", "webcam fullscreen viewer", "view webcam in fullscreen mode", "full screen camera preview"],
    "webcam photo capture": ["webcam photo capture", "take a photo with your webcam", "webcam snapshot tool", "capture webcam image online"],
    "webcam video recorder": ["webcam video recorder", "record webcam video online", "free webcam recording tool", "record video from your camera"],
    "webcam mirror test": ["webcam mirror test", "mirrored vs natural webcam view", "webcam mirror mode checker", "flip webcam image test"],
    "webcam comparison": ["webcam comparison", "side-by-side webcam comparison tool", "compare two cameras online", "webcam vs webcam test"],
    "webcam focus test": ["webcam focus test", "webcam sharpness test", "check webcam focus quality", "camera blur and sharpness checker"],
    "webcam lighting test": ["webcam lighting test", "webcam exposure test", "check webcam brightness and lighting", "camera lighting conditions checker"],
    "is my camera on": ["is my camera on", "check if my camera is being used", "camera in use detector", "is my webcam active right now"],
    "rule of thirds grid": ["rule of thirds grid", "webcam composition grid overlay", "camera framing grid tool", "rule of thirds camera overlay"],
    "webcam filters": ["webcam filters", "live webcam filter preview", "webcam effects and filters online", "apply filters to webcam feed"],
    "webcam low light test": ["webcam low light test", "webcam low light noise test", "check webcam performance in low light", "camera noise in dim lighting checker"],
    "webcam color test": ["webcam color test", "webcam colour accuracy test", "check webcam color reproduction", "camera white balance and color checker"],
    "webcam autofocus test": ["webcam autofocus test", "check webcam autofocus speed", "camera autofocus lag test", "webcam focus hunting checker"],
    "webcam latency test": ["webcam latency test", "webcam delay test", "check webcam video lag", "camera latency and delay checker"],
    # --- Camera Mobile ---
    "front camera test": ["front camera test", "test your phone's front camera", "selfie camera test online", "front facing camera checker"],
    "rear camera test": ["rear camera test", "test your phone's rear camera", "main camera test online", "back camera checker"],
    "mobile camera test": ["mobile camera test", "test your phone camera online", "smartphone camera test", "mobile device camera checker"],
    "phone camera resolution": ["phone camera resolution", "phone camera resolution checker", "check your phone's actual camera resolution", "smartphone megapixel checker"],
    "phone camera zoom test": ["phone camera zoom test", "test your phone's digital zoom", "phone camera zoom quality checker", "check phone zoom performance"],
    "phone flashlight test": ["phone flashlight test", "phone camera flash torch test", "test your phone's camera flash", "check phone torch and flash"],
    "phone camera orientation test": ["phone camera orientation test", "check phone camera rotation", "camera orientation and rotation checker", "phone camera landscape portrait test"],
    "check used phone camera": ["check used phone camera", "used phone camera inspection checklist", "inspect a secondhand phone's camera", "buying a used phone camera checklist"],
    # --- Camera Reference ---
    "use phone as webcam": ["use phone as webcam", "turn your phone into a webcam", "how to use phone as webcam guide", "phone as webcam setup guide"],
    "camera permissions": ["camera permissions", "camera permissions guide", "fix blocked camera permissions", "camera and microphone permissions guide"],
    "webcam not working": ["webcam not working", "webcam not working troubleshooting guide", "fix webcam not working issues", "camera troubleshooting guide"],
    "webcam resolution chart": ["webcam resolution chart", "webcam resolution standards reference", "video resolution comparison chart", "camera resolution standards guide"],
    "webcam specs comparison": ["webcam specs comparison", "webcam specs comparison database", "compare webcam specifications", "camera specs reference database"],
    "camera test vs webcam test": ["camera test vs webcam test", "camera test vs webcam test explained", "difference between camera test and webcam test", "camera testing terminology explained"],
    # --- Audio ---
    "microphone test": ["microphone test", "free microphone test online", "test my microphone", "check microphone input levels"],
    "speaker test": ["speaker test", "free speaker test online", "test your speakers", "check speaker output quality"],
    "hearing test online": ["hearing test online", "online hearing frequency test", "free hearing test", "check your hearing range"],
    "microphone record test": ["microphone record test", "microphone record and playback test", "record and play back your mic", "test mic recording quality"],
    "stereo left right test": ["stereo left right test", "left and right stereo channel test", "check stereo channel balance", "test left right speaker channels"],
    "speaker polarity test": ["speaker polarity test", "speaker polarity and phase test", "check speaker phase alignment", "speaker wiring polarity checker"],
    "subwoofer test": ["subwoofer test", "subwoofer bass test online", "test your subwoofer bass response", "check subwoofer low frequency output"],
    "audio latency test": ["audio latency test", "audio latency and delay test", "check your audio system latency", "measure audio round trip delay"],
    "frequency sweep test": ["frequency sweep test", "audio frequency sweep 20hz to 20khz", "test speaker frequency range", "full range frequency sweep tool"],
    "mic echo test": ["mic echo test", "microphone echo test", "check for microphone echo", "test mic feedback and echo"],
    "microphone spectrum analyzer": ["microphone spectrum analyzer", "microphone quality spectrum analyzer", "analyze microphone frequency response", "check mic spectral quality"],
    "mic level meter": ["mic level meter", "microphone input level meter", "check microphone input gain", "test mic volume levels"],
}

# ---------------------------------------------------------------------------
# Sentence templates — 2 families, 6 variants each. Keyed by family, not by
# anchor text, since the anchor text itself now rotates among
# ANCHOR_VARIANTS — a sentence template only needs to know whether the
# target is a live device test or a no-device reference guide, not which
# specific variant phrase was chosen for it this month.
# ---------------------------------------------------------------------------

_GUIDE_ANCHORS = {
    "use phone as webcam",
    "camera permissions",
    "webcam not working",
    "webcam resolution chart",
    "webcam specs comparison",
    "camera test vs webcam test",
    "check used phone camera",
}

_SENTENCE_FAMILIES = {
    "live_test": [
        "Run the {link} directly in your browser — it uses your camera or microphone live, and nothing you capture is ever uploaded.",
        "The {link} works entirely client-side, so you get an instant result without installing an app or creating an account.",
        "Use the {link} to check your hardware is actually working the way you expect, right from this page.",
        "The {link} needs a quick permission prompt the first time you run it, then gives you a live read-out in seconds.",
        "Nothing you do in the {link} ever leaves your device — the whole test runs locally in your browser tab.",
        "The {link} is free to use with no sign-up, and works on both desktop and mobile browsers.",
    ],
    "guide": [
        "The {link} walks through the exact steps in plain language, with no camera or microphone access required to read it.",
        "Check the {link} if you want the background explanation before running a live test elsewhere on this site.",
        "The {link} is kept up to date and free to read, with no account or sign-up needed.",
        "Read the {link} for a clear breakdown you can refer back to whenever the same issue comes up again.",
        "The {link} covers the common cases in one place, so you don't have to piece the answer together from forum threads.",
        "Use the {link} as a quick reference — it's written to be skimmed, not read start to finish.",
    ],
}


def _family_for(primary_kw: str) -> str:
    return "guide" if primary_kw in _GUIDE_ANCHORS else "live_test"

# ---------------------------------------------------------------------------
# Rotation helpers
# ---------------------------------------------------------------------------


def monthly_shuffle(items: list, seed_key: str, today: datetime.date) -> list:
    seed = int(hashlib.md5(f"{today.year}-M{today.month:02d}-{seed_key}".encode()).hexdigest(), 16)
    items = list(items)
    random.Random(seed).shuffle(items)
    return items


def pick_from_list(items: list, seed_key: str, today: datetime.date):
    key = f"{today.year}-M{today.month:02d}-{seed_key}"
    idx = int(hashlib.md5(key.encode()).hexdigest(), 16) % len(items)
    return items[idx]


def pick_sentence(source_file: str, family: str, today: datetime.date) -> str:
    key = f"{today.year}-M{today.month:02d}-{source_file}-{family}"
    idx = int(hashlib.md5(key.encode()).hexdigest(), 16) % 6
    return _SENTENCE_FAMILIES[family][idx]


def make_sentence_html(template: str, url: str, anchor: str) -> str:
    return template.replace("{link}", f'<a href="{url}">{anchor}</a>')


def _pick_anchor(primary_kw: str, seed_key: str, today: datetime.date) -> str:
    return pick_from_list(ANCHOR_VARIANTS[primary_kw], seed_key, today)


# ---------------------------------------------------------------------------
# Link generation
# ---------------------------------------------------------------------------


def _group_links(pages: list, subsilo: dict, seed_prefix: str, today: datetime.date,
                  prev_bridge, next_bridge) -> dict:
    shuffled = monthly_shuffle(pages, seed_prefix, today)
    page_links: dict = {}

    for pos, page in enumerate(shuffled):
        left = shuffled[pos - 1] if pos > 0 else prev_bridge
        right = shuffled[pos + 1] if pos < len(shuffled) - 1 else next_bridge
        src = page["file"]

        links = [
            {"slot": "slot_a", "family": _family_for(subsilo["anchor"]),
             "anchor": _pick_anchor(subsilo["anchor"], f"{src}_up", today), "url": subsilo["url"]},
        ]
        if left:
            links.append({"slot": "slot_b", "family": _family_for(left["anchor"]),
                           "anchor": _pick_anchor(left["anchor"], f"{src}_left", today), "url": left["url"]})
        else:
            links.append({"slot": "slot_b", "family": None, "anchor": None, "url": None})
        if right:
            links.append({"slot": "slot_c", "family": _family_for(right["anchor"]),
                           "anchor": _pick_anchor(right["anchor"], f"{src}_right", today), "url": right["url"]})
        else:
            links.append({"slot": "slot_c", "family": None, "anchor": None, "url": None})

        page_links[page["file"]] = links

    return page_links


def generate_links(today: datetime.date) -> dict:
    links: dict = {}

    for cluster in CLUSTERS:
        cid = cluster["id"]
        pillar = cluster["pillar"]
        subsilos = cluster["subsilos"]
        groups = cluster["groups"]

        # Pillar: rotate its single outbound link among its sub-silos monthly.
        chosen = pick_from_list(subsilos, f"wc_c{cid}_pillar", today) if subsilos else None
        if chosen:
            links[pillar["file"]] = [
                {"slot": "slot_a", "family": _family_for(chosen["anchor"]),
                 "anchor": _pick_anchor(chosen["anchor"], f"{pillar['file']}_down", today), "url": chosen["url"]},
            ]

        # Pre-shuffle each sub-silo's own supporting group (for slot_d + bridge wiring).
        group_shuffles = [monthly_shuffle(g, f"wc_c{cid}_group{i}", today) for i, g in enumerate(groups)]
        group_first = [gs[0] if gs else None for gs in group_shuffles]

        # Sub-silos: shuffle order monthly for horizontal-neighbor variety;
        # slot_d (down) always follows the sub-silo's own original index.
        order = monthly_shuffle(list(range(len(subsilos))), f"wc_c{cid}_subsilo_order", today)
        for pos, ss_i in enumerate(order):
            ss = subsilos[ss_i]
            left_ss = subsilos[order[pos - 1]] if pos > 0 else None
            right_ss = subsilos[order[pos + 1]] if pos < len(order) - 1 else None
            down = group_first[ss_i]
            src = ss["file"]

            page_links = [
                {"slot": "slot_a", "family": _family_for(pillar["anchor"]),
                 "anchor": _pick_anchor(pillar["anchor"], f"{src}_up", today), "url": pillar["url"]},
            ]
            if left_ss:
                page_links.append({"slot": "slot_b", "family": _family_for(left_ss["anchor"]),
                                    "anchor": _pick_anchor(left_ss["anchor"], f"{src}_left", today), "url": left_ss["url"]})
            else:
                page_links.append({"slot": "slot_b", "family": None, "anchor": None, "url": None})
            if right_ss:
                page_links.append({"slot": "slot_c", "family": _family_for(right_ss["anchor"]),
                                    "anchor": _pick_anchor(right_ss["anchor"], f"{src}_right", today), "url": right_ss["url"]})
            else:
                page_links.append({"slot": "slot_c", "family": None, "anchor": None, "url": None})
            if down:
                page_links.append({"slot": "slot_d", "family": _family_for(down["anchor"]),
                                    "anchor": _pick_anchor(down["anchor"], f"{src}_down", today), "url": down["url"]})
            links[ss["file"]] = page_links

        # Supporting groups, bridged linearly within this cluster only
        # (group 0 -> group 1 -> ... -> last group, no wraparound).
        nonempty = [i for i, g in enumerate(groups) if g]
        for pos, i in enumerate(nonempty):
            g = groups[i]
            prev_i = nonempty[pos - 1] if pos > 0 else None
            next_i = nonempty[pos + 1] if pos < len(nonempty) - 1 else None
            prev_bridge = group_shuffles[prev_i][-1] if prev_i is not None else None
            next_bridge = group_shuffles[next_i][0] if next_i is not None else None
            links.update(_group_links(g, subsilos[i], f"wc_c{cid}_group{i}", today,
                                       prev_bridge=prev_bridge, next_bridge=next_bridge))

    return links


# ---------------------------------------------------------------------------
# Core HTML helpers — the heading_index-aware variant this site needs (a
# tool page's first real content <h2> isn't always the first <h2> on the
# page, since every tool-panel header inside the card is itself an <h2> —
# see the INJECTION_TARGETS comment above).
# ---------------------------------------------------------------------------


def _strip_tags(s: str) -> str:
    return html_lib.unescape(re.sub(r"<[^>]+>", "", s)).strip()


def _update_markers(html: str, slot: str, sentence_html: str) -> str:
    start = f"<!-- SILO_START:{slot} -->"
    end = f"<!-- SILO_END:{slot} -->"
    pattern = re.compile(re.escape(start) + r".*?" + re.escape(end), re.S)
    # Replacement passed as a callable, not a string — a string replacement is
    # scanned by re for backreferences/escapes (\1, \g<name>, ...), and
    # sentence_html can legitimately contain a literal backslash.
    return pattern.sub(lambda m: start + sentence_html + end, html)


def _find_paragraph_end(html: str, heading_tag: str, heading_text, para_index: int = 0, heading_index: int = 0):
    if heading_text is None:
        pattern = re.compile(f"</{re.escape(heading_tag)}>", re.I)
        matches = list(pattern.finditer(html))
        if heading_index >= len(matches):
            return None
        search_from = matches[heading_index].end()
    else:
        search_from = None
        for m in re.finditer(
            r"<" + heading_tag + r"[^>]*>(.*?)</" + heading_tag + r">",
            html, re.S
        ):
            if heading_text in _strip_tags(m.group(1)):
                search_from = m.end()
                break
        if search_from is None:
            return None

    offset = search_from
    p_end = None
    for i in range(para_index + 1):
        p_end = re.search(r"</p>", html[offset:])
        if not p_end:
            return None
        if i < para_index:
            offset += p_end.end()

    return offset + p_end.start()


def _insert_markers(html: str, slot: str, sentence_html: str,
                     heading_tag: str, heading_text, para_index: int = 0, heading_index: int = 0) -> str:
    pos = _find_paragraph_end(html, heading_tag, heading_text, para_index, heading_index)
    if pos is None:
        return html
    start = f"<!-- SILO_START:{slot} -->"
    end = f"<!-- SILO_END:{slot} -->"
    injection = f" {start}{sentence_html}{end}"
    return html[:pos] + injection + html[pos:]


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def run(today: datetime.date, dry_run: bool = False) -> list:
    silo_links = generate_links(today)
    errors: list = []

    for page_file, link_defs in silo_links.items():
        filepath = os.path.join(PAGES_DIR, page_file)
        if not os.path.exists(filepath):
            errors.append(f"MISSING FILE: {page_file}")
            continue

        html = open(filepath, encoding="utf-8").read()
        original = html

        for link_def in link_defs:
            slot = link_def["slot"]
            anchor = link_def["anchor"]
            url = link_def["url"]

            marker_start = f"<!-- SILO_START:{slot} -->"
            target = INJECTION_TARGETS[page_file][slot]
            tag, text = target[0], target[1]
            para_idx = target[2] if len(target) > 2 else 0
            h_idx = target[3] if len(target) > 3 else 0

            if anchor is None:
                if marker_start in html:
                    html = _update_markers(html, slot, "")
                else:
                    html = _insert_markers(html, slot, "", tag, text, para_idx, h_idx)
            else:
                sentence_html = make_sentence_html(pick_sentence(page_file, link_def["family"], today), url, anchor)
                if marker_start in html:
                    html = _update_markers(html, slot, sentence_html)
                else:
                    new_html = _insert_markers(html, slot, sentence_html, tag, text, para_idx, h_idx)
                    if new_html == html:
                        errors.append(f"INJECT FAILED: {page_file}/{slot} — heading not found")
                    html = new_html

        if html != original:
            if dry_run:
                print(f"[dry-run] would update: {page_file}")
            else:
                open(filepath, "w", encoding="utf-8").write(html)
                print(f"Updated: {page_file}")
        else:
            print(f"No change: {page_file}")

    return errors


if __name__ == "__main__":
    dry_run = "--dry-run" in sys.argv

    today = datetime.date.today()
    for arg in sys.argv[1:]:
        if arg.startswith("--date="):
            raw = arg.split("=", 1)[1]
            try:
                year, month = map(int, raw.split("-"))
                today = datetime.date(year, month, 1)
            except ValueError:
                print(f"Invalid --date value {raw!r}. Expected YYYY-MM.", file=sys.stderr)
                sys.exit(1)

    print(f"Silo rotation — webcamtest — {today.year}-M{today.month:02d}" + (" [DRY RUN]" if dry_run else ""))
    errs = run(today, dry_run=dry_run)
    if errs:
        print("\nErrors:", file=sys.stderr)
        for e in errs:
            print(f"  {e}", file=sys.stderr)
        sys.exit(1)
    print("Done.")
