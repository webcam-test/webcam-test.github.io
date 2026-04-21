#!/usr/bin/env python3
"""
Monthly silo link rotation for webcam-test.github.io.

Full rotation each month:
  - Pillar rotates which hub it links to (deterministic shuffle, pick index 0).
  - Each hub's "down" link rotates to whichever supporter is first in that
    silo's shuffled chain for the month.
  - Supporter prev/next/bridge links update to match the shuffled order.

HTML files are patched in-place using comment markers:
  <!-- SILO_START:slot_a -->sentence with link<!-- SILO_END:slot_a -->

Run via GitHub Actions on the 1st of each month, or manually:
  python3 utilities/silo_linking/generate_silo_rotation.py
  python3 utilities/silo_linking/generate_silo_rotation.py --dry-run
  python3 utilities/silo_linking/generate_silo_rotation.py --date=2026-05
"""

import datetime
import hashlib
import html as html_lib
import os
import random
import re
import sys

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# ---------------------------------------------------------------------------
# Silo structure
# ---------------------------------------------------------------------------

HUBS = ["webcam-recorder.html", "fps-checker.html", "show-webcam.html"]

HUB_ANCHORS = {
    "webcam-recorder.html": "webcam recorder",
    "fps-checker.html":     "webcam fps checker",
    "show-webcam.html":     "webcam viewer",
}
HUB_URLS = {
    "webcam-recorder.html": "/webcam-recorder",
    "fps-checker.html":     "/fps-checker",
    "show-webcam.html":     "/show-webcam",
}

# Supporter pages in each silo. "anchor" = keyword used when linking TO this page.
SILO_SUPPORTERS = {
    "webcam-recorder.html": [        # Silo A — 5 pages
        {"file": "take-photo.html",        "anchor": "webcam photo",           "url": "/take-photo"},
        {"file": "mirror.html",            "anchor": "webcam mirror",          "url": "/mirror"},
        {"file": "webcam-effects.html",    "anchor": "webcam effects online",  "url": "/webcam-effects"},
        {"file": "webcam-gif.html",        "anchor": "webcam gif maker",       "url": "/webcam-gif"},
        {"file": "webcam-timelapse.html",  "anchor": "webcam timelapse online","url": "/webcam-timelapse"},
    ],
    "fps-checker.html": [            # Silo B — 5 pages
        {"file": "resolution-tester.html",      "anchor": "webcam resolution test", "url": "/resolution-tester"},
        {"file": "webcam-quality-test.html",    "anchor": "webcam quality test",    "url": "/webcam-quality-test"},
        {"file": "webcam-zoom-test.html",       "anchor": "webcam zoom test",       "url": "/webcam-zoom-test"},
        {"file": "webcam-brightness-test.html", "anchor": "webcam brightness test", "url": "/webcam-brightness-test"},
        {"file": "webcam-color-test.html",      "anchor": "webcam color test",      "url": "/webcam-color-test"},
    ],
    "show-webcam.html": [            # Silo C — 3 pages
        {"file": "camera-comparison.html",   "anchor": "webcam comparison tool", "url": "/camera-comparison"},
        {"file": "webcam-lighting-test.html","anchor": "webcam lighting test",   "url": "/webcam-lighting-test"},
        {"file": "webcam-grid-overlay.html", "anchor": "webcam grid overlay",    "url": "/webcam-grid-overlay"},
    ],
}

# ---------------------------------------------------------------------------
# Injection targets: physical HTML location for each slot (first run only).
# (heading_tag, heading_text_fragment) — None = first <p> after <h1>.
# ---------------------------------------------------------------------------

INJECTION_TARGETS = {
    "index.html": {
        "slot_a": ("h1", None),
    },
    # --- Hubs (4 slots each) ---
    "webcam-recorder.html": {
        "slot_a": ("h1", None),
        "slot_b": ("h2", "What the Webcam Recorder Captures"),
        "slot_c": ("h2", "Webcam Recording Quality"),
        "slot_d": ("h2", "Who Uses an Online Webcam Recorder"),
    },
    "fps-checker.html": {
        "slot_a": ("h1", None),
        "slot_b": ("h2", "What Does FPS Mean for Your Webcam"),
        "slot_c": ("h2", "Why Your Webcam FPS Matters"),
        "slot_d": ("h2", "How to Improve Your Webcam FPS"),
    },
    "show-webcam.html": {
        "slot_a": ("h1", None),
        "slot_b": ("h2", "How to Use the Webcam Viewer"),
        "slot_c": ("h2", "Why Check Your Webcam Specifications"),
        "slot_d": ("h2", "What Your Webcam Details Actually Tell You"),
    },
    # --- Silo A supporters (3 slots each) ---
    "take-photo.html": {
        "slot_a": ("h1", None),
        "slot_b": ("h2", "How to Take a Webcam Photo Online"),
        "slot_c": ("h2", "What Can You Use a Webcam Photo For"),
    },
    "mirror.html": {
        "slot_a": ("h1", None),
        "slot_b": ("h2", "How to Use the Webcam Mirror Online"),
        "slot_c": ("h2", "Mirror View vs. Natural View"),
    },
    "webcam-effects.html": {
        "slot_a": ("h1", None),
        "slot_b": ("h2", "Creative Filters and Effects for Your Camera"),
        "slot_c": ("h2", "How Live Camera Filters Work in a Browser"),
    },
    "webcam-gif.html": {
        "slot_a": ("h1", None),
        "slot_b": ("h2", "Tips for Making Better Webcam GIFs"),
        "slot_c": ("h2", "What to Use Webcam GIFs For"),
    },
    "webcam-timelapse.html": {
        "slot_a": ("h1", None),
        "slot_b": ("h2", "Capture Interval"),
        "slot_c": ("h2", "What to Capture — Webcam Timelapse Subject Ideas"),
    },
    # --- Silo B supporters (3 slots each) ---
    "resolution-tester.html": {
        "slot_a": ("h1", None),
        "slot_b": ("h2", "What Is Webcam Resolution"),
        "slot_c": ("h2", "What Webcam Resolution Do You Actually Need"),
    },
    "webcam-quality-test.html": {
        "slot_a": ("h1", None),
        "slot_b": ("h2", "What the Quality Metrics Measure"),
        "slot_c": ("h2", "Troubleshooting a Low Webcam Quality Score"),
    },
    "webcam-zoom-test.html": {
        "slot_a": ("h1", None),
        "slot_b": ("h2", "Understanding Digital Zoom Quality"),
        "slot_c": ("h2", "Practical Use Cases for Webcam Digital Zoom"),
    },
    "webcam-brightness-test.html": {
        "slot_a": ("h1", None),
        "slot_b": ("h2", "What Does Webcam Brightness Mean"),
        "slot_c": ("h2", "Why Webcam Brightness Matters"),
    },
    "webcam-color-test.html": {
        "slot_a": ("h1", None),
        "slot_b": ("h2", "Understanding Colour Casts and White Balance"),
        "slot_c": ("h2", "How Lighting Affects Your Webcam"),
    },
    # --- Silo C supporters (3 slots each) ---
    "camera-comparison.html": {
        "slot_a": ("h1", None),
        "slot_b": ("h2", "What Can You Compare with Two Webcams"),
        "slot_c": ("h2", "When to Use the Webcam Comparison Tool"),
    },
    "webcam-lighting-test.html": {
        "slot_a": ("h1", None),
        "slot_b": ("h2", "What the Lighting Metrics Measure"),
        "slot_c": ("h2", "Natural vs. Artificial Light"),
    },
    "webcam-grid-overlay.html": {
        "slot_a": ("h1", None),
        "slot_b": ("h2", "The Three Overlays"),
        "slot_c": ("h2", "Who Uses a Webcam Grid Overlay"),
    },
}

# ---------------------------------------------------------------------------
# Sentence templates — 6 per anchor keyword, {link} replaced at render time.
# ---------------------------------------------------------------------------

# Long-tail anchor variants used for the hub → pillar (slot_a) link.
# Rotated monthly per hub page so each hub uses a different variant.
HUB_UP_ANCHORS = [
    "webcam test",
    "online webcam test",
    "free webcam test",
    "test my webcam",
    "webcam check online",
    "test your webcam online",
]


def pick_hub_up_anchor(hub_file: str, today: datetime.date) -> str:
    key = f"{today.year}-{today.month}-{hub_file}-slot_a"
    idx = int(hashlib.md5(key.encode()).hexdigest(), 16) % len(HUB_UP_ANCHORS)
    return HUB_UP_ANCHORS[idx]


SENTENCES = {
    # --- Hub up anchors (hub → pillar) ---
    "webcam test": [
        "Run a {link} first to confirm your camera is working before diving in.",
        "A quick {link} confirms your camera is active and accessible in your browser.",
        "The {link} checks resolution, frame rate, and device access in one step.",
        "Before any recording or call, a {link} rules out camera permission issues instantly.",
        "Use the {link} to verify your camera feed is live and your device is recognised.",
        "The free {link} runs entirely in your browser — no download or account needed.",
    ],
    "online webcam test": [
        "Run an {link} to confirm your camera works before your next call or recording.",
        "An {link} checks your camera feed, resolution, and frame rate in seconds.",
        "Use an {link} to diagnose why your camera isn't showing up in video apps.",
        "An {link} confirms your device is accessible and your browser permission is granted.",
        "The free {link} measures live camera output with no software to install.",
        "Before a streaming session, an {link} ensures your setup is working correctly.",
    ],
    "free webcam test": [
        "Run a {link} in your browser to confirm your camera is ready before you start.",
        "The {link} checks your live feed, resolution, and FPS with nothing to install.",
        "A {link} catches camera access problems before they interrupt a meeting or call.",
        "Use the {link} to verify your camera's output and browser permission status instantly.",
        "The {link} works with any browser-accessible camera and runs entirely locally.",
        "Before any recording session, a {link} confirms your camera is delivering clean video.",
    ],
    "test my webcam": [
        "To {link} quickly, the tool runs in your browser and shows results in seconds.",
        "Use this page to {link} — it displays your live feed, resolution, and device name.",
        "The fastest way to {link} is to open this tool and check the live camera output.",
        "You can {link} without any downloads — it uses your browser's WebRTC API directly.",
        "To {link} before a call, click Allow and watch the live preview load instantly.",
        "This tool lets you {link} and get immediate feedback on frame rate and video quality.",
    ],
    "webcam check online": [
        "Do a {link} before your next video call to confirm your camera is ready.",
        "The {link} shows your live feed and confirms your camera permission is granted.",
        "A {link} catches device conflicts and driver issues before they affect a meeting.",
        "Use the {link} to verify your camera output and identify the active device.",
        "The free {link} runs in your browser with no software or account required.",
        "Before any recording, a {link} confirms your camera is detected and streaming correctly.",
    ],
    "test your webcam online": [
        "You can {link} in seconds — the tool shows your live feed and camera specs instantly.",
        "The easiest way to {link} is to open the page, click Allow, and read the results.",
        "Use this tool to {link} and confirm your resolution, FPS, and device name are correct.",
        "To {link} before a meeting, the browser-based tool needs no installation or sign-up.",
        "The free option to {link} runs entirely locally — your video never leaves your device.",
        "Before streaming or recording, {link} to rule out camera access or permission issues.",
    ],
    # --- Hub anchors (supporter → hub, and pillar → hub) ---
    "webcam recorder": [
        "Use the {link} to capture and download video directly from your camera in one click.",
        "The {link} records your webcam feed as a WebM file with no upload required.",
        "For full-length video capture, the {link} saves directly to your device after recording.",
        "The free {link} works in any modern browser and requires no account or installation.",
        "Try the {link} to record a test clip and check your video quality before an important call.",
        "The {link} captures both video and audio simultaneously and downloads automatically when you stop.",
    ],
    "webcam fps checker": [
        "Use the {link} to measure your camera's exact frame rate at any resolution.",
        "The {link} shows your live frames-per-second count and how it varies under load.",
        "Run the {link} to find out whether your camera hits 30fps or drops below it.",
        "The free {link} measures actual FPS delivered to the browser — not the rated spec.",
        "Before a streaming session, the {link} confirms your camera is delivering smooth frame output.",
        "The {link} lets you compare FPS at different resolutions to find the best balance.",
    ],
    "webcam viewer": [
        "Open the {link} to see your camera's full technical specs in one detailed panel.",
        "The {link} displays resolution, frame rate, device name, and autofocus mode live.",
        "Use the {link} to check your camera's facing direction, aspect ratio, and device ID.",
        "The free {link} reads your live camera stream and surfaces hardware capability data instantly.",
        "For a complete camera spec readout, the {link} is faster than any system settings menu.",
        "The {link} confirms your device name and supported resolutions directly from the browser API.",
    ],
    # --- Silo A supporter anchors ---
    "webcam photo": [
        "Use the {link} tool to capture a still image from your camera and download it in PNG.",
        "The {link} captures a high-resolution still from your live camera feed in one click.",
        "For a quick snapshot without any software, the {link} saves directly to your device.",
        "The free {link} works on any camera-equipped device in Chrome, Firefox, or Safari.",
        "Take a {link} to check framing, lighting, and focus before your next video call.",
        "The {link} lets you preview and download a full-resolution picture from your webcam instantly.",
    ],
    "webcam mirror": [
        "Use the {link} to see your live camera feed mirrored in real time, just like a physical mirror.",
        "The {link} shows your real-time reflection in a browser tab with no software needed.",
        "Check your appearance and framing with the {link} before going live or joining a call.",
        "The free {link} works on front and rear cameras and lets you apply basic visual filters.",
        "For a quick appearance check, the {link} runs entirely in your browser with no delay.",
        "The {link} is the fastest way to see how you look on camera before a recording session.",
    ],
    "webcam effects online": [
        "Apply grayscale, sepia, or blur to your live feed with the {link} tool.",
        "The {link} lets you preview camera filters in real time before any call or recording.",
        "Use {link} to see how your camera looks with different visual effects applied live.",
        "The free {link} processes filters locally — your video is never uploaded anywhere.",
        "Try {link} to find the filter that works best under your current lighting conditions.",
        "The {link} runs canvas-based filters on your live feed at your camera's native frame rate.",
    ],
    "webcam gif maker": [
        "Capture a short looping animation with the {link} and download it instantly.",
        "The {link} records a 1–5 second clip from your camera and encodes it as an animated GIF.",
        "Use the {link} to create a reaction GIF or animated avatar from your live camera feed.",
        "The free {link} runs entirely in your browser — no upload, no account, no watermark.",
        "For a quick looping clip, the {link} encodes and downloads your GIF in seconds.",
        "The {link} is the fastest way to turn a webcam moment into a shareable animated GIF.",
    ],
    "webcam timelapse online": [
        "Create a timelapse from your live camera with the {link} tool — set an interval and record.",
        "The {link} captures frames at regular intervals and lets you preview the sequence before downloading.",
        "Use the {link} to document a slow process — plant growth, weather changes, or workspace setup.",
        "The free {link} runs entirely in your browser and saves your frames as a ZIP download.",
        "For time-based camera projects, the {link} automates frame capture at any interval you choose.",
        "The {link} builds a timelapse from your webcam feed with no software or upload required.",
    ],
    # --- Silo B supporter anchors ---
    "webcam resolution test": [
        "Run a {link} to find out the maximum pixel dimensions your camera can deliver.",
        "The {link} checks every resolution from 480p to 4K and shows which your camera supports.",
        "Use the {link} to confirm whether your webcam can reach 1080p or is capped at 720p.",
        "The free {link} iterates through all standard resolutions and reports which ones succeed.",
        "Before a recording session, a {link} confirms your camera is streaming at full quality.",
        "The {link} shows your supported resolutions with aspect ratios and pixel dimensions for each.",
    ],
    "webcam quality test": [
        "Run the {link} to get a scored breakdown of sharpness, brightness, noise, and contrast.",
        "The {link} analyses your live feed and returns an overall image quality score instantly.",
        "Use the {link} to find out whether poor lighting or lens quality is limiting your video.",
        "The free {link} measures pixel-level metrics from your camera without any upload.",
        "The {link} gives you specific improvement tips based on your camera's actual performance data.",
        "Before a recording session, the {link} confirms your image quality meets your requirements.",
    ],
    "webcam zoom test": [
        "Use the {link} to preview digital zoom levels from 1× to 5× on your live camera feed.",
        "The {link} shows exactly how image quality degrades as you increase digital zoom.",
        "Run the {link} to find the highest zoom level that still delivers acceptable sharpness.",
        "The free {link} applies canvas-based zoom to your live feed with no quality data uploaded.",
        "The {link} helps you decide which zoom level is usable for your streaming or recording setup.",
        "Use the {link} to compare native resolution detail against the cropped zoom output side by side.",
    ],
    "webcam brightness test": [
        "Run the {link} to measure your camera's brightness score and see if your setup is well-lit.",
        "The {link} reads pixel luminance from your live feed and rates your lighting as dark, good, or overexposed.",
        "Use the {link} to check whether your current lighting is optimised for video calls or recording.",
        "The free {link} shows a live brightness histogram and gives specific lighting improvement tips.",
        "Before a call or stream, the {link} confirms your exposure is in the optimal range.",
        "The {link} measures brightness in real time so you can adjust your lighting and see instant feedback.",
    ],
    "webcam color test": [
        "Use the {link} to check your camera's colour balance and detect white balance issues.",
        "The {link} samples your live feed and measures red, green, and blue channel levels in real time.",
        "Run the {link} to find out whether your camera has a warm, cool, or neutral colour cast.",
        "The free {link} analyses colour accuracy from your live camera feed without any upload.",
        "The {link} shows RGB channel readings that reveal colour temperature issues in your current lighting.",
        "Use the {link} to compare colour output before and after changing your lighting or camera settings.",
    ],
    # --- Silo C supporter anchors ---
    "webcam comparison tool": [
        "Use the {link} to view two cameras side by side and compare video quality directly.",
        "The {link} streams two cameras simultaneously so you can compare resolution, colour, and exposure.",
        "Run the {link} to find out whether your built-in or external webcam delivers better quality.",
        "The free {link} works with any two browser-accessible cameras and processes all streams locally.",
        "For a side-by-side camera evaluation, the {link} is the fastest way to see real differences.",
        "The {link} lets you compare frame rate, colour accuracy, and low-light performance between two cameras.",
    ],
    "webcam lighting test": [
        "Run the {link} to measure your lighting quality and get a scored assessment of your setup.",
        "The {link} analyses brightness uniformity and exposure from your live camera feed.",
        "Use the {link} to find out whether your current lighting is rated Excellent, Good, or Poor.",
        "The free {link} gives specific tips for improving your lighting based on live camera measurements.",
        "Before a recording session, the {link} confirms your lighting conditions are optimised for video.",
        "The {link} detects uneven lighting, underexposure, and overexposure from your camera feed instantly.",
    ],
    "webcam grid overlay": [
        "Use the {link} to add a rule-of-thirds grid, crosshair, or face guide to your live camera feed.",
        "The {link} renders framing overlays directly on your live webcam feed in your browser.",
        "Toggle the {link} on to check your camera position, eye level, and subject framing before recording.",
        "The free {link} lets you switch between grid, crosshair, and face guide overlays independently.",
        "For better video composition, the {link} shows exactly where to position yourself in the frame.",
        "The {link} is the fastest way to apply rule-of-thirds framing to your webcam without any software.",
    ],
}

# ---------------------------------------------------------------------------
# Rotation helpers
# ---------------------------------------------------------------------------

def monthly_shuffle(items: list, seed_key: str, today: datetime.date) -> list:
    seed = int(hashlib.md5(f"{today.year}-{today.month}-{seed_key}".encode()).hexdigest(), 16)
    items = list(items)
    random.Random(seed).shuffle(items)
    return items


def pick_sentence(source_file: str, anchor: str, today: datetime.date) -> str:
    key = f"{today.year}-{today.month}-{source_file}-{anchor}"
    idx = int(hashlib.md5(key.encode()).hexdigest(), 16) % 6
    return SENTENCES[anchor][idx]


def generate_silo_links(today: datetime.date) -> dict:
    """Return SILO_LINKS dict for the given month via deterministic shuffle.

    Hub slot convention:
      slot_a = up to pillar (long-tail webcam test variant — rotates monthly per hub)
      slot_b = LEFT hub neighbour (None/empty if this hub is first in shuffled order)
      slot_c = RIGHT hub neighbour (None/empty if this hub is last in shuffled order)
      slot_d = DOWN to first supporter in this hub's shuffled chain (rotates monthly)
    """

    shuffled_hubs = monthly_shuffle(HUBS, "pillar", today)
    pillar_hub    = shuffled_hubs[0]

    silo_supporters = {
        hub: monthly_shuffle(SILO_SUPPORTERS[hub], f"silo_{i}", today)
        for i, hub in enumerate(HUBS)
    }

    links: dict = {}

    # --- Pillar: 1 outgoing link to whichever hub is first this month ---
    links["index.html"] = [
        {"slot": "slot_a", "anchor": HUB_ANCHORS[pillar_hub], "url": HUB_URLS[pillar_hub]},
    ]

    # --- Hub pages: slot_b=left, slot_c=right, slot_d=down ---
    for pos, hub_file in enumerate(shuffled_hubs):
        is_first_hub = (pos == 0)
        is_last_hub  = (pos == len(shuffled_hubs) - 1)
        supporters   = silo_supporters[hub_file]
        left_hub     = shuffled_hubs[pos - 1] if not is_first_hub else None
        right_hub    = shuffled_hubs[pos + 1] if not is_last_hub  else None

        links[hub_file] = [
            {"slot": "slot_a", "anchor": pick_hub_up_anchor(hub_file, today), "url": "/"},
            {"slot": "slot_b",
             "anchor": HUB_ANCHORS[left_hub]  if left_hub  else None,
             "url":    HUB_URLS[left_hub]     if left_hub  else None},
            {"slot": "slot_c",
             "anchor": HUB_ANCHORS[right_hub] if right_hub else None,
             "url":    HUB_URLS[right_hub]    if right_hub else None},
            {"slot": "slot_d",
             "anchor": supporters[0]["anchor"], "url": supporters[0]["url"]},
        ]

    # Pull per-silo shuffled lists for use in the supporter section below
    silo_a = silo_supporters["webcam-recorder.html"]
    silo_b = silo_supporters["fps-checker.html"]
    silo_c = silo_supporters["show-webcam.html"]

    # --- Supporter pages ---
    silos = [
        ("webcam-recorder.html", silo_a, 0),  # Silo A
        ("fps-checker.html",     silo_b, 1),  # Silo B
        ("show-webcam.html",     silo_c, 2),  # Silo C
    ]

    for hub_file, supporters, silo_idx in silos:
        n          = len(supporters)
        hub_anchor = HUB_ANCHORS[hub_file]
        hub_url    = HUB_URLS[hub_file]

        for i, page in enumerate(supporters):
            is_first = (i == 0)
            is_last  = (i == n - 1)

            slot_a_def = {"slot": "slot_a", "anchor": hub_anchor, "url": hub_url}

            if is_first:
                next_page  = supporters[1]
                slot_b_def = {"slot": "slot_b",
                              "anchor": next_page["anchor"], "url": next_page["url"]}

                if silo_idx == 0:
                    # Silo A first — no backward bridge (A is the first silo)
                    slot_c_def = {"slot": "slot_c", "anchor": None, "url": None}
                else:
                    # Backward bridge: link to last of the previous silo
                    prev_silo  = [silo_a, silo_b][silo_idx - 1]
                    last_prev  = prev_silo[-1]
                    slot_c_def = {"slot": "slot_c",
                                  "anchor": last_prev["anchor"], "url": last_prev["url"]}

            elif is_last:
                prev_page  = supporters[i - 1]
                slot_b_def = {"slot": "slot_b",
                              "anchor": prev_page["anchor"], "url": prev_page["url"]}

                if silo_idx == 2:
                    # Silo C last — no forward bridge (C is the last silo)
                    slot_c_def = {"slot": "slot_c", "anchor": None, "url": None}
                else:
                    # Forward bridge: link to first of the next silo
                    next_silo  = [silo_b, silo_c][silo_idx]
                    first_next = next_silo[0]
                    slot_c_def = {"slot": "slot_c",
                                  "anchor": first_next["anchor"], "url": first_next["url"]}

            else:
                # Middle of chain
                prev_page  = supporters[i - 1]
                next_page  = supporters[i + 1]
                slot_b_def = {"slot": "slot_b",
                              "anchor": prev_page["anchor"], "url": prev_page["url"]}
                slot_c_def = {"slot": "slot_c",
                              "anchor": next_page["anchor"], "url": next_page["url"]}

            links[page["file"]] = [slot_a_def, slot_b_def, slot_c_def]

    return links

# ---------------------------------------------------------------------------
# Core HTML helpers
# ---------------------------------------------------------------------------

def _strip_tags(s: str) -> str:
    return html_lib.unescape(re.sub(r"<[^>]+>", "", s)).strip()


def make_sentence_html(template: str, url: str, anchor: str) -> str:
    link = f'<a href="{url}">{anchor}</a>'
    return template.replace("{link}", link)


def update_markers(html: str, slot: str, sentence_html: str) -> str:
    start   = f"<!-- SILO_START:{slot} -->"
    end     = f"<!-- SILO_END:{slot} -->"
    pattern = re.compile(re.escape(start) + r".*?" + re.escape(end), re.S)
    return pattern.sub(start + sentence_html + end, html)


def find_paragraph_end(html: str, heading_tag: str, heading_text: str | None) -> int | None:
    """Return position just before </p> to inject into, based on the given heading."""
    if heading_text is None:
        m = re.search(r"</h1>", html)
        if not m:
            return None
        search_from = m.end()
    else:
        for m in re.finditer(
            r"<" + heading_tag + r"[^>]*>(.*?)</" + heading_tag + r">",
            html, re.S
        ):
            if heading_text in _strip_tags(m.group(1)):
                search_from = m.end()
                break
        else:
            return None

    p_end = re.search(r"</p>", html[search_from:])
    if not p_end:
        return None
    return search_from + p_end.start()


def insert_markers(html: str, slot: str, sentence_html: str,
                   heading_tag: str, heading_text: str | None) -> str:
    pos = find_paragraph_end(html, heading_tag, heading_text)
    if pos is None:
        return html
    start     = f"<!-- SILO_START:{slot} -->"
    end       = f"<!-- SILO_END:{slot} -->"
    injection = f" {start}{sentence_html}{end}"
    return html[:pos] + injection + html[pos:]

# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def run(today: datetime.date, dry_run: bool = False) -> None:
    silo_links = generate_silo_links(today)
    errors: list[str] = []

    for page_file, link_defs in silo_links.items():
        filepath = os.path.join(REPO_ROOT, page_file)
        if not os.path.exists(filepath):
            errors.append(f"MISSING FILE: {page_file}")
            continue

        html     = open(filepath, encoding="utf-8").read()
        original = html

        for link_def in link_defs:
            slot   = link_def["slot"]
            anchor = link_def["anchor"]
            url    = link_def["url"]

            marker_start = f"<!-- SILO_START:{slot} -->"

            if anchor is None:
                # Empty slot — clear any existing content, or insert empty markers
                if marker_start in html:
                    html = update_markers(html, slot, "")
                else:
                    tag, text = INJECTION_TARGETS[page_file][slot]
                    html = insert_markers(html, slot, "", tag, text)
            else:
                sentence_html = make_sentence_html(
                    pick_sentence(page_file, anchor, today), url, anchor
                )
                if marker_start in html:
                    html = update_markers(html, slot, sentence_html)
                else:
                    tag, text = INJECTION_TARGETS[page_file][slot]
                    new_html  = insert_markers(html, slot, sentence_html, tag, text)
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

    if errors:
        print("\nErrors:", file=sys.stderr)
        for e in errors:
            print(f"  {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    dry_run = "--dry-run" in sys.argv

    today = datetime.date.today()
    for arg in sys.argv[1:]:
        if arg.startswith("--date=") or (arg == "--date" and sys.argv.index(arg) + 1 < len(sys.argv)):
            raw = arg.split("=", 1)[1] if "=" in arg else sys.argv[sys.argv.index(arg) + 1]
            try:
                year, month = map(int, raw.split("-"))
                today = datetime.date(year, month, 1)
            except ValueError:
                print(f"Invalid --date value {raw!r}. Expected YYYY-MM.", file=sys.stderr)
                sys.exit(1)

    print(f"Silo rotation — {today.year}-{today.month:02d}"
          + (" [DRY RUN]" if dry_run else ""))
    run(today, dry_run=dry_run)
    print("Done.")
