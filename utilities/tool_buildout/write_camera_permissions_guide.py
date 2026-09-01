#!/usr/bin/env python3
"""Writes src/content/camera-permissions-guide-windows-mac-android-ios.json.
Throwaway authoring script, same pattern as write_webcam_test_online.py —
see this project's CLAUDE.md 'Authoring a new tool's content file'.

Structurally different from every camera/mic tool built so far: no live
getUserMedia call anywhere on this page at all. The "card" is a tabbed
OS -> browser reference interface (a legitimate distinct interactive shape
per this site's own "raw card layout" rationale), with the visitor's own
platform/browser preselected via UA sniffing but always overridable, per
the spec's own explicit guidance. Instructions are kept text-based (no
screenshots) and the page is dated, since permission UI changes between
browser versions -- also per the spec's own explicit caution."""
import json
import os

BASE = os.path.dirname(os.path.abspath(__file__))
CONTENT_DIR = os.path.normpath(os.path.join(BASE, "..", "..", "src", "content"))

SHIELD_ICON = '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z" stroke-linecap="round" stroke-linejoin="round"/></svg>'

# One entry per (platform, browser). "allow" and "reset" are each a list of
# plain-text steps -- no screenshots, per this tool's own spec.
GUIDE_DATA = {
    "windows": {
        "label": "Windows",
        "browsers": {
            "chrome": {
                "label": "Chrome / Edge",
                "allow": [
                    "Click the camera icon (or the lock/info icon) at the left of the address bar.",
                    "Find “Camera” and “Microphone” in the list and set each to Allow.",
                    "Reload the page.",
                ],
                "reset": [
                    "Click the lock/info icon in the address bar, then “Site settings.”",
                    "Set Camera and Microphone back to “Ask (default)” or “Allow.”",
                    "Reload the page and try again — the prompt should reappear if you chose Ask.",
                ],
            },
            "firefox": {
                "label": "Firefox",
                "allow": [
                    "Click the lock icon in the address bar.",
                    "Find the camera/microphone permission entry and choose Allow.",
                    "Reload the page.",
                ],
                "reset": [
                    "Click the lock icon in the address bar, then the arrow next to the blocked camera/microphone entry.",
                    "Choose “Remove Permission” or set it to Allow directly.",
                    "Reload the page — you should see the permission prompt again.",
                ],
            },
        },
    },
    "mac": {
        "label": "macOS",
        "browsers": {
            "chrome": {
                "label": "Chrome",
                "allow": [
                    "Click the camera icon in the address bar and choose “Always allow.”",
                    "Separately, make sure macOS itself allows it: System Settings → Privacy & Security → Camera (and Microphone), and enable Chrome in both lists.",
                    "Reload the page.",
                ],
                "reset": [
                    "Click the lock/info icon in the address bar, then “Site settings.”",
                    "Set Camera and Microphone back to “Ask (default)” or “Allow.”",
                    "Reload the page and try again.",
                ],
            },
            "firefox": {
                "label": "Firefox",
                "allow": [
                    "Click the lock icon in the address bar and allow the camera/microphone permission.",
                    "Also check System Settings → Privacy & Security → Camera (and Microphone) and make sure Firefox is enabled there too — macOS blocks access at the OS level independently of what Firefox allows.",
                    "Reload the page.",
                ],
                "reset": [
                    "Click the lock icon, then the arrow next to the blocked permission entry, and remove or change it.",
                    "Reload the page — the prompt should reappear.",
                ],
            },
            "safari": {
                "label": "Safari",
                "allow": [
                    "Safari → Settings → Websites → Camera (and separately Microphone).",
                    "Find this site in the list and set it to Allow.",
                    "Also check System Settings → Privacy & Security → Camera/Microphone and make sure Safari is enabled there.",
                    "Reload the page.",
                ],
                "reset": [
                    "Safari → Settings → Websites → Camera, find this site, and change it from Deny to Allow (or to Ask).",
                    "Do the same on the Microphone tab if audio is also blocked.",
                    "Reload the page.",
                ],
            },
        },
    },
    "android": {
        "label": "Android",
        "browsers": {
            "chrome": {
                "label": "Chrome",
                "allow": [
                    "Tap the lock/info icon at the left of the address bar.",
                    "Tap Permissions, then set Camera and Microphone to Allow.",
                    "Reload the page.",
                ],
                "reset": [
                    "Tap the lock/info icon in the address bar, then Permissions, and change Camera/Microphone from Blocked to Allow (or Ask).",
                    "If that section doesn't appear, go to Android Settings → Apps → Chrome → Permissions → Camera/Microphone and allow it at the app level, then reload the page.",
                ],
            },
            "firefox": {
                "label": "Firefox",
                "allow": [
                    "Tap the lock icon in the address bar and allow the camera/microphone permission when prompted.",
                    "Also check Android Settings → Apps → Firefox → Permissions → Camera/Microphone and make sure both are allowed there.",
                    "Reload the page.",
                ],
                "reset": [
                    "Android Settings → Apps → Firefox → Permissions → Camera (and Microphone), and set each to Allow.",
                    "Reload the page and try again.",
                ],
            },
        },
    },
    "ios": {
        "label": "iOS / iPadOS",
        "browsers": {
            "safari": {
                "label": "Safari",
                "allow": [
                    "Settings app → Safari → Camera (and separately Microphone), and set to Allow.",
                    "Alternatively, on the page itself: tap “AA” in the address bar → Website Settings, and set Camera/Microphone to Allow there.",
                    "Reload the page.",
                ],
                "reset": [
                    "Settings app → Safari → Camera, and change it from Deny to Allow (or Ask).",
                    "Do the same under Microphone if audio is blocked too.",
                    "Reload the page.",
                ],
            },
            "chrome": {
                "label": "Chrome",
                "allow": [
                    "iOS Chrome uses Apple's underlying WebKit engine, so camera/microphone permission is actually controlled by the Settings app, not inside Chrome itself: Settings app → Chrome → Camera (and Microphone), set to Allow.",
                    "Reload the page in Chrome.",
                ],
                "reset": [
                    "Settings app → Chrome → Camera (and Microphone), and change from off to on.",
                    "Reload the page.",
                ],
            },
        },
    },
}

PLATFORM_ORDER = ["windows", "mac", "android", "ios"]

FIELDS_HTML = f'''<div class="tool-panel span-3">
  <div class="panel-header">
    <span class="panel-icon">{SHIELD_ICON}</span>
    <div><h2>Find Your Platform</h2><p class="panel-sub">We've preselected your device below — switch it if this isn't the one you need</p></div>
  </div>
  <div class="media-controls" id="platformTabs" role="tablist" aria-label="Operating system"></div>
  <div class="media-controls" id="browserTabs" role="tablist" aria-label="Browser" style="margin-top:.6rem"></div>
  <div id="guideContent" style="margin-top:1.25rem"></div>
</div>'''

SCRIPT_DATA_JSON = json.dumps(
    {p: {"label": GUIDE_DATA[p]["label"], "browsers": GUIDE_DATA[p]["browsers"]} for p in PLATFORM_ORDER},
    ensure_ascii=False,
)

SCRIPT = '''(function () {
  'use strict';

  var GUIDE = ''' + SCRIPT_DATA_JSON + ''';
  var PLATFORM_ORDER = ''' + json.dumps(PLATFORM_ORDER) + ''';

  var platformTabs = document.getElementById('platformTabs');
  var browserTabs = document.getElementById('browserTabs');
  var guideContent = document.getElementById('guideContent');

  var currentPlatform = null;
  var currentBrowser = null;

  function escapeHtml(s) {
    var d = document.createElement('div');
    d.textContent = String(s);
    return d.innerHTML;
  }

  // Preselects the visitor's own platform/browser via simple UA sniffing,
  // per this tool's own spec -- always overridable via the tabs, never
  // the only way to reach a given combination.
  function detectPlatform() {
    var ua = navigator.userAgent || '';
    if (/iPhone|iPad|iPod/.test(ua)) return 'ios';
    if (/Android/.test(ua)) return 'android';
    if (/Macintosh|Mac OS X/.test(ua)) return 'mac';
    return 'windows';
  }

  function detectBrowser(platformKey) {
    var ua = navigator.userAgent || '';
    var browsers = GUIDE[platformKey].browsers;
    var guess;
    if (/Firefox/.test(ua)) guess = 'firefox';
    else if (/Safari/.test(ua) && !/Chrome|Chromium|CriOS/.test(ua)) guess = 'safari';
    else guess = 'chrome'; // covers Chrome, Edge (Edg/), and CriOS (Chrome on iOS)
    return browsers[guess] ? guess : Object.keys(browsers)[0];
  }

  function renderPlatformTabs() {
    platformTabs.innerHTML = PLATFORM_ORDER.map(function (key) {
      var active = key === currentPlatform;
      return '<button type="button" class="btn-secondary' + (active ? ' active' : '') + '" data-platform="' + key + '" aria-pressed="' + active + '">' + escapeHtml(GUIDE[key].label) + '</button>';
    }).join('');
    Array.prototype.forEach.call(platformTabs.querySelectorAll('button'), function (btn) {
      btn.addEventListener('click', function () { selectPlatform(btn.getAttribute('data-platform')); });
    });
  }

  function renderBrowserTabs() {
    var browsers = GUIDE[currentPlatform].browsers;
    browserTabs.innerHTML = Object.keys(browsers).map(function (key) {
      var active = key === currentBrowser;
      return '<button type="button" class="btn-secondary' + (active ? ' active' : '') + '" data-browser="' + key + '" aria-pressed="' + active + '">' + escapeHtml(browsers[key].label) + '</button>';
    }).join('');
    Array.prototype.forEach.call(browserTabs.querySelectorAll('button'), function (btn) {
      btn.addEventListener('click', function () { selectBrowser(btn.getAttribute('data-browser')); });
    });
  }

  function renderContent() {
    var entry = GUIDE[currentPlatform].browsers[currentBrowser];
    function stepList(steps) {
      return '<ol>' + steps.map(function (s) { return '<li>' + escapeHtml(s).replace(/&quot;/g, '"') + '</li>'; }).join('') + '</ol>';
    }
    var labelStyle = 'font-weight:700;color:var(--text);margin:0 0 .5rem';
    guideContent.innerHTML =
      '<p style="' + labelStyle + '">Allow camera &amp; microphone access</p>' + stepList(entry.allow) +
      '<p style="' + labelStyle + ';margin-top:1.25rem">Reset a previously blocked permission</p>' + stepList(entry.reset);
  }

  function selectPlatform(key) {
    if (!GUIDE[key]) return;
    currentPlatform = key;
    currentBrowser = detectBrowser(key);
    renderPlatformTabs();
    renderBrowserTabs();
    renderContent();
  }

  function selectBrowser(key) {
    if (!GUIDE[currentPlatform].browsers[key]) return;
    currentBrowser = key;
    renderBrowserTabs();
    renderContent();
  }

  selectPlatform(detectPlatform());
})();'''

CONTENT_HTML = '''<p>Blocked camera or microphone access is the single most common reason a browser-based test like the ones on this site fails to start — every camera and microphone tool here would ideally link back to this page the moment that happens. The tabs above are preselected to your own device and browser, detected automatically, but you can switch either one if you need instructions for a different combination.</p>
<h2>Why there are two separate permission layers</h2>
<p>Most operating systems have their own camera and microphone privacy toggle, entirely separate from whatever your browser itself allows. Even after you click Allow in the browser's own permission prompt, the OS-level toggle can still silently block every browser at once — this is why the steps above check both layers where it's relevant, rather than just the browser-level setting alone.</p>
<h2>The hardest case: a permission you already denied</h2>
<p>Once you dismiss a browser's permission prompt with "Block" (or accidentally click the wrong option), most browsers stop asking automatically on that site — you have to reset it manually, which is genuinely the least discoverable part of this whole process for most people. The "Reset a previously blocked permission" steps above exist specifically for this case, separate from the simpler "first time asking" steps.</p>
<h2>Still blocked after following these steps?</h2>
<p>Reload the page after changing any permission setting — most browsers only re-check camera and microphone permissions on a fresh page load, not the instant you change the setting. If it's still blocked after reloading, work through the <a href="/webcam-not-working-troubleshooting-guide">Webcam Troubleshooting Guide</a>, which runs a live test and points you to whichever of six causes actually matches your specific error.</p>
<h2>A note on accuracy</h2>
<p>Permission settings menus move around between browser versions faster than almost anything else in a browser's interface. This page was last verified accurate in 2026 — if a specific menu item described above doesn't match what you see, the general idea (a per-site permission list, usually reachable from an icon in the address bar, plus a matching operating-system privacy setting) still applies; look for the closest equivalent in your current version.</p>'''

FAQ = [
    {"question": "Why do I need to change a setting in two different places?", "answer": "Your browser and your operating system each maintain their own, independent camera/microphone permission — allowing access in the browser doesn't override an operating-system-level block, and vice versa. Both need to allow it for a website to actually access your camera or microphone."},
    {"question": "I don't see this site listed in my permission settings at all — what do I do?", "answer": "Some browsers and operating systems only add a site or app to their permission list the first time it actually requests access. Try running a live camera test once (the Webcam Troubleshooting Guide has one embedded), then check the settings again — the entry usually appears after that first request."},
    {"question": "I allowed the permission but it's still blocked — why?", "answer": "Reload the page after changing any permission setting. Most browsers only re-check camera and microphone permissions when a page freshly loads, not the instant you change a setting elsewhere."},
    {"question": "The instructions don't match what I see in my browser — has this page not been updated?", "answer": "Permission menus move around between browser versions. This page was last verified accurate in 2026; if a specific menu label has changed, look for the closest equivalent — usually a per-site permission list reachable from an icon in the address bar, alongside a matching operating-system-level privacy setting."},
]

TOOL = {
    "slug": "camera-permissions-guide-windows-mac-android-ios",
    "meta_title": "Camera & Microphone Permissions Guide — Windows, Mac, Android, iOS | WebcamTest",
    "meta_description": "Step-by-step instructions for allowing (or resetting a blocked) camera and microphone permission on Windows, macOS, Android, and iOS, across every major browser.",
    "h1": "Camera & Microphone Permissions Guide",
    "subtitle": "Step-by-step instructions for allowing camera and microphone access — or resetting a permission you already blocked.",
    "card": {
        "layout": "raw",
        "fields_html": FIELDS_HTML,
    },
    "script": SCRIPT,
    "content_html": CONTENT_HTML,
    "faq": FAQ,
}

if __name__ == "__main__":
    out_path = os.path.join(CONTENT_DIR, "camera-permissions-guide-windows-mac-android-ios.json")
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(TOOL, f, indent=2, ensure_ascii=False)
    print("Wrote", out_path)
