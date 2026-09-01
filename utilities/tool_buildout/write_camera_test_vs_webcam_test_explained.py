#!/usr/bin/env python3
"""Writes src/content/camera-test-vs-webcam-test-explained.json."""
import json
import os

BASE = os.path.dirname(os.path.abspath(__file__))
CONTENT_DIR = os.path.normpath(os.path.join(BASE, "..", "..", "src", "content"))

COMPASS_ICON = '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="10"/><path d="M16.24 7.76l-2.12 6.36-6.36 2.12 2.12-6.36 6.36-2.12z"/></svg>'

FIELDS_HTML = f'''<div class="tool-panel span-3">
  <div class="panel-header">
    <span class="panel-icon">{COMPASS_ICON}</span>
    <div><h2>Find the Right Tool</h2><p class="panel-sub">"Camera test" and "webcam test" usually mean the same thing — pick what you're actually checking below</p></div>
  </div>
  <p class="field-note" style="margin-top:0">Both phrases almost always describe the same basic need: confirming a camera works and previewing its live feed. "Webcam" traditionally implied a separate USB device plugged into a desktop, while "camera" is more often used for a laptop's built-in camera or a phone — but in practice the two terms are used interchangeably, and every tool on this site works the same regardless of which type of camera you have.</p>
  <div class="info-table">
    <div class="info-row"><span class="info-label" style="max-width:60%">Just want to confirm your camera works and see a live preview?</span><span class="info-value" style="text-align:right;font-family:inherit;font-weight:600"><a href="/webcam-test-online">Webcam Test</a></span></div>
    <div class="info-row"><span class="info-label" style="max-width:60%">Need exact hardware specs — resolution, frame rate, device name?</span><span class="info-value" style="text-align:right;font-family:inherit;font-weight:600"><a href="/webcam-camera-information-report">Camera Information Report</a></span></div>
    <div class="info-row"><span class="info-label" style="max-width:60%">Checking image quality — sharpness, lighting or colour?</span><span class="info-value" style="text-align:right;font-family:inherit;font-weight:600"><a href="/webcam-sharpness-focus-test">Sharpness and Focus Test</a></span></div>
    <div class="info-row"><span class="info-label" style="max-width:60%">Testing a phone's camera, front or rear?</span><span class="info-value" style="text-align:right;font-family:inherit;font-weight:600"><a href="/mobile-camera-test-online">Mobile Camera Test</a></span></div>
    <div class="info-row"><span class="info-label" style="max-width:60%">Inspecting a used phone's camera before buying it?</span><span class="info-value" style="text-align:right;font-family:inherit;font-weight:600"><a href="/used-phone-camera-inspection-checklist">Used Phone Camera Inspection</a></span></div>
    <div class="info-row"><span class="info-label" style="max-width:60%">Worried another app might be using your camera?</span><span class="info-value" style="text-align:right;font-family:inherit;font-weight:600"><a href="/is-my-camera-being-used-check">Camera In-Use Privacy Check</a></span></div>
    <div class="info-row"><span class="info-label" style="max-width:60%">Camera not showing up, or not working at all?</span><span class="info-value" style="text-align:right;font-family:inherit;font-weight:600"><a href="/webcam-not-working-troubleshooting-guide">Troubleshooting Guide</a></span></div>
    <div class="info-row"><span class="info-label" style="max-width:60%">Need to grant camera permission in your browser?</span><span class="info-value" style="text-align:right;font-family:inherit;font-weight:600"><a href="/camera-permissions-guide-windows-mac-android-ios">Permissions Guide</a></span></div>
  </div>
</div>'''

SCRIPT = '''(function () { 'use strict'; })();'''

CONTENT_HTML = '''<p>If you searched for "camera test" and ended up wondering whether that's different from a "webcam test," you're not alone — it's a common enough point of confusion that it's worth addressing directly.</p>
<h2>Where the distinction actually comes from</h2>
<p>Historically, "webcam" referred specifically to a separate USB camera device plugged into a desktop computer, distinct from a laptop's built-in camera or a phone's camera. That distinction has mostly faded in everyday language — people now say "webcam test" and "camera test" to mean the same thing regardless of what kind of camera they actually have, and search engines treat the two queries as close synonyms rather than genuinely different requests.</p>
<h2>Does it matter which term you use on this site?</h2>
<p>No — every tool here works identically whether you're testing a built-in laptop camera, an external USB webcam, or a phone's camera. The naming across this site follows common search phrasing rather than the older technical distinction, since that's how people actually look for these tools today.</p>
<h2>What actually matters: what you're checking</h2>
<p>The more useful question isn't "camera test" versus "webcam test" — it's what specifically you want to verify. The table above routes by that instead, since "does my camera work," "how sharp is the image," and "is my camera being watched by something else" are genuinely different checks that call for different tools, regardless of what you call the camera itself.</p>'''

FAQ = [
    {"question": "Is a \"webcam\" different from a \"camera\" for the purposes of these tools?", "answer": "Not functionally — every tool on this site works the same way whether you're testing a built-in laptop camera, an external USB webcam, or a phone's camera. The terms are used interchangeably throughout."},
    {"question": "Why do some competing sites have a dedicated page explaining this difference?", "answer": "Because enough people search for both phrases with some uncertainty about whether they mean the same thing that it's worth addressing directly rather than leaving visitors guessing — which is exactly the purpose of this page."},
    {"question": "Which tool should I start with if I'm not sure what I need?", "answer": "The Webcam Test (this site's home page) is the right starting point for almost everyone — it confirms your camera works and shows a live preview with basic resolution and frame rate info, and links out to more specific tools from there."},
]

TOOL = {
    "slug": "camera-test-vs-webcam-test-explained",
    "meta_title": "Camera Test vs Webcam Test: What's the Difference? | WebcamTest",
    "meta_description": "\"Camera test\" and \"webcam test\" usually mean the same thing. This guide explains the distinction and routes you to the right tool for what you're actually checking.",
    "h1": "Camera Test vs Webcam Test Explained",
    "subtitle": "These two phrases almost always mean the same thing — here's the real distinction, and which tool to use for what you're actually checking.",
    "card": {
        "layout": "raw",
        "fields_html": FIELDS_HTML,
    },
    "script": SCRIPT,
    "content_html": CONTENT_HTML,
    "faq": FAQ,
}

if __name__ == "__main__":
    out_path = os.path.join(CONTENT_DIR, "camera-test-vs-webcam-test-explained.json")
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(TOOL, f, indent=2, ensure_ascii=False)
    print("Wrote", out_path)
