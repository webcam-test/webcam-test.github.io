#!/usr/bin/env python3
"""Writes src/content/use-phone-as-webcam-guide.json."""
import json
import os

BASE = os.path.dirname(os.path.abspath(__file__))
CONTENT_DIR = os.path.normpath(os.path.join(BASE, "..", "..", "src", "content"))

PHONE_ICON = '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect x="6" y="2" width="12" height="20" rx="2"/><path d="M11 18h2" stroke-linecap="round"/></svg>'
LINK_ICON = '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M10 13a5 5 0 0 0 7.54.54l3-3a5 5 0 0 0-7.07-7.07l-1.72 1.71"/><path d="M14 11a5 5 0 0 0-7.54-.54l-3 3a5 5 0 0 0 7.07 7.07l1.71-1.71"/></svg>'

FIELDS_HTML = f'''<div class="tool-panel span-3">
  <div class="panel-header">
    <span class="panel-icon">{PHONE_ICON}</span>
    <div><h2>Which Method for Your Devices</h2><p class="panel-sub">Find your phone + computer combination below</p></div>
  </div>
  <div class="info-table">
    <div class="info-row"><span class="info-label" style="max-width:45%">iPhone + Mac</span><span class="info-value" style="text-align:right;font-family:inherit;font-weight:400">Continuity Camera — built into macOS 13+ and iOS 16+, no app needed. Your iPhone appears automatically as a camera option in any app.</span></div>
    <div class="info-row"><span class="info-label" style="max-width:45%">Android + Windows or Mac</span><span class="info-value" style="text-align:right;font-family:inherit;font-weight:400">A third-party app (Camo, DroidCam, Iriun and similar) installed on both the phone and computer, usually connecting over USB or Wi-Fi.</span></div>
    <div class="info-row"><span class="info-label" style="max-width:45%">iPhone + Windows</span><span class="info-value" style="text-align:right;font-family:inherit;font-weight:400">A third-party app is required since there's no built-in bridge — the same category of app as the Android + Windows row, with an iOS companion app.</span></div>
    <div class="info-row"><span class="info-label" style="max-width:45%">Any phone, wired for lowest latency</span><span class="info-value" style="text-align:right;font-family:inherit;font-weight:400">Prefer a USB connection over Wi-Fi where the app supports it — noticeably lower latency and no dependence on network conditions.</span></div>
  </div>
</div>
<div class="tool-panel span-2">
  <div class="panel-header">
    <span class="panel-icon">{LINK_ICON}</span>
    <div><h2>Verify the Upgrade Yourself</h2></div>
  </div>
  <p class="field-note" style="margin-top:0">Don't just take it on faith that your phone's camera is better — measure both and compare directly:</p>
  <div class="info-table">
    <div class="info-row"><span class="info-label">1. Test your laptop's built-in camera</span><span class="info-value" style="text-align:right;font-family:inherit;font-weight:600"><a href="/webcam-maximum-resolution-detector">Maximum Resolution Detector</a></span></div>
    <div class="info-row"><span class="info-label">2. Test your phone's camera</span><span class="info-value" style="text-align:right;font-family:inherit;font-weight:600"><a href="/mobile-camera-test-online">Mobile Camera Test</a></span></div>
    <div class="info-row"><span class="info-label">3. Once connected as a webcam</span><span class="info-value" style="text-align:right;font-family:inherit;font-weight:600"><a href="/webcam-test-online">Webcam Test</a></span></div>
  </div>
</div>
<div class="tool-panel">
  <div class="panel-header">
    <span class="panel-icon"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="10"/><path d="M12 16v-4M12 8h.01" stroke-linecap="round"/></svg></span>
    <div><h2>Why Bother</h2></div>
  </div>
  <p class="field-note" style="margin-top:0">Most laptop webcams are a low-priority afterthought in a laptop's design, while phone cameras get significant engineering investment every generation — for most people, even a phone that's a few years old outperforms their laptop's built-in camera.</p>
</div>'''

SCRIPT = '''(function () { 'use strict'; })();'''

CONTENT_HTML = '''<p>Your phone's camera is very likely better than your laptop's built-in webcam — often dramatically so — and setting it up as your computer's camera for calls is easier than most people expect.</p>
<h2>Why the upgrade is usually so noticeable</h2>
<p>Laptop manufacturers treat the built-in webcam as a minor afterthought squeezed into a thin bezel, with little year-over-year investment. Phone cameras, by contrast, are a flagship feature that manufacturers compete hard on every single generation. The result is that even a phone that's a few years old typically has a larger sensor, better low-light performance, and real autofocus compared to most laptop webcams — including many expensive laptops.</p>
<h2>Built-in options versus third-party apps</h2>
<p>Apple's Continuity Camera is the smoothest path if you have both an iPhone and a Mac — it requires no app installation at all and your iPhone simply appears as a camera choice in any video app once it's near your Mac and signed into the same Apple ID. Every other combination — Android to Windows or Mac, or iPhone to Windows — currently requires a third-party app installed on both devices, typically connecting over USB or Wi-Fi.</p>
<h2>Wired versus wireless connections</h2>
<p>Where a third-party app supports both, a USB connection is worth preferring over Wi-Fi: it's noticeably lower latency, doesn't compete with your network for bandwidth, and keeps your phone charged during long calls instead of draining its battery.</p>
<h2>Confirming the upgrade is real, not assumed</h2>
<p>Rather than taking it on faith, use this site's own Maximum Resolution Detector and other camera tools on both your laptop's built-in camera and your phone's camera, then compare the actual measured results side by side — and again once your phone is connected as your computer's camera, to confirm the setup is delivering what you expect.</p>'''

FAQ = [
    {"question": "Do I need to buy anything to use my phone as a webcam?", "answer": "Not necessarily. If you have an iPhone and a Mac, Continuity Camera is completely free and built into the OS. For every other combination, most third-party apps have a free tier that's enough for basic video calls, though some reserve higher resolutions or extra features for a paid version."},
    {"question": "Will using my phone as a webcam drain its battery quickly?", "answer": "Yes, particularly over a wireless connection, since the screen and camera stay active continuously. Using a USB cable instead of Wi-Fi solves this — it charges the phone while it's being used, in addition to being lower-latency."},
    {"question": "Is my phone's camera really better than my laptop's, or is that just marketing?", "answer": "For the large majority of laptops, yes — you can verify this yourself rather than taking it on faith, using this site's Maximum Resolution Detector and other camera tools on both devices to compare actual measured results."},
    {"question": "Does this work for every video calling app?", "answer": "Once your phone is set up as a camera source (through Continuity Camera or a third-party app), it appears as a regular camera device to your computer, so it works with any app that lets you choose a camera — the setup is a one-time step per app, not something repeated every call."},
]

TOOL = {
    "slug": "use-phone-as-webcam-guide",
    "meta_title": "Use Your Phone as a Webcam — Setup Guide for Every OS | WebcamTest",
    "meta_description": "How to use your phone's camera as your computer's webcam, for every phone and computer combination. Built-in options, third-party apps, and how to verify the upgrade yourself.",
    "h1": "Use Your Phone as a Webcam",
    "subtitle": "Your phone's camera usually beats your laptop's built-in webcam — here's how to set it up for every device combination.",
    "card": {
        "layout": "raw",
        "fields_html": FIELDS_HTML,
    },
    "script": SCRIPT,
    "content_html": CONTENT_HTML,
    "faq": FAQ,
}

if __name__ == "__main__":
    out_path = os.path.join(CONTENT_DIR, "use-phone-as-webcam-guide.json")
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(TOOL, f, indent=2, ensure_ascii=False)
    print("Wrote", out_path)
