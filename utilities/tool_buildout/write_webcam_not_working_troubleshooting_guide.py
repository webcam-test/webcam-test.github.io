#!/usr/bin/env python3
"""Writes src/content/webcam-not-working-troubleshooting-guide.json.
Throwaway authoring script, same pattern as write_webcam_test_online.py —
see this project's CLAUDE.md 'Authoring a new tool's content file'.

Structurally different from every other tool built so far: the card is a
live diagnostic instrument (webcam-test-online's exact acquisition/
teardown/error pattern, unmodified) paired with a "Diagnosis" panel that
maps each real getUserMedia error to a specific numbered step further down
the page in content_html -- per the spec's own explicit differentiator
("embedding a live acquisition attempt at each step is what separates this
from the many static articles... map each browser error type to the
matching step so arriving from a failed test lands the visitor on the
right one")."""
import json
import os

BASE = os.path.dirname(os.path.abspath(__file__))
CONTENT_DIR = os.path.normpath(os.path.join(BASE, "..", "..", "src", "content"))

CAMERA_ICON = '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M23 7l-7 5 7 5V7z"/><rect x="1" y="5" width="15" height="14" rx="2" ry="2"/></svg>'
LIST_ICON = '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M9 6h11M9 12h11M9 18h11M4 6h.01M4 12h.01M4 18h.01" stroke-linecap="round" stroke-linejoin="round"/></svg>'
PLACEHOLDER_ICON = '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5"><path d="M23 7l-7 5 7 5V7z"/><rect x="1" y="5" width="15" height="14" rx="2" ry="2"/></svg>'

STEPS = [
    ("step-permission", "Browser permission is blocked"),
    ("step-in-use", "Another app is already using the camera"),
    ("step-os-privacy", "Your operating system is blocking browser camera access"),
    ("step-drivers", "Outdated or missing camera drivers"),
    ("step-connection", "A loose or disconnected camera cable"),
    ("step-hardware", "A genuine hardware failure"),
]

FIELDS_HTML = f'''<div class="tool-panel primary">
  <div class="panel-header">
    <span class="panel-icon">{CAMERA_ICON}</span>
    <div><h2>Run the Live Test</h2><p class="panel-sub">Try starting your camera here — whatever happens tells us exactly where to send you below</p></div>
  </div>
  <div class="media-preview" id="cameraPreviewWrap">
    <video id="cameraVideo" autoplay playsinline muted></video>
    <div class="media-preview-placeholder" id="cameraPlaceholder">
      {PLACEHOLDER_ICON}
      <span>Your camera feed will appear here</span>
    </div>
  </div>
  <div class="media-controls">
    <button type="button" class="btn-primary" id="btnStartCamera">Start Camera</button>
    <button type="button" class="btn-secondary" id="btnStopCamera" disabled>Stop Camera</button>
    <select class="device-select" id="deviceSelect" aria-label="Select camera" disabled>
      <option value="">Default camera</option>
    </select>
  </div>
</div>
<div class="tool-panel">
  <div class="panel-header">
    <span class="panel-icon">{LIST_ICON}</span>
    <div><h2>Diagnosis</h2><p class="panel-sub">Ordered by how common each cause actually is</p></div>
  </div>
  <div class="diagnostic-panel" id="diagnosticPanel">
    <div class="diagnostic-item"><span>Click <strong>Start Camera</strong> above and allow access when your browser asks — we'll point you to the right step based on what happens.</span></div>
  </div>
  <div class="ladder-list" style="margin-top:1rem">
''' + "".join(f'    <div class="ladder-item"><a href="#{anchor}">Step {i}: {title}</a></div>\n' for i, (anchor, title) in enumerate(STEPS, 1)) + '''  </div>
</div>'''

SCRIPT = '''(function () {
  'use strict';

  var video = document.getElementById('cameraVideo');
  var previewWrap = document.getElementById('cameraPreviewWrap');
  var placeholder = document.getElementById('cameraPlaceholder');
  var deviceSelect = document.getElementById('deviceSelect');
  var btnStart = document.getElementById('btnStartCamera');
  var btnStop = document.getElementById('btnStopCamera');
  var diagnosticPanel = document.getElementById('diagnosticPanel');

  var currentStream = null;
  var currentDeviceId = '';
  var starting = false;

  function escapeHtml(s) {
    var d = document.createElement('div');
    d.textContent = String(s);
    return d.innerHTML;
  }

  function setDiagnostic(items) {
    diagnosticPanel.innerHTML = items.map(function (it) {
      var sevClass = it.sev ? ' sev-' + it.sev : '';
      return '<div class="diagnostic-item' + sevClass + '"><span class="diag-icon">' +
        '<svg viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="9"/></svg>' +
        '</span><span>' + it.html + '</span></div>';
    }).join('');
  }

  // Every camera page on this site copies this stopStream()/enumerate/error
  // pattern from webcam-test-online.json (see this project's own CLAUDE.md).
  function stopStream() {
    if (currentStream) {
      currentStream.getTracks().forEach(function (t) { t.stop(); });
      currentStream = null;
    }
    video.srcObject = null;
    previewWrap.classList.remove('is-active');
    placeholder.style.display = 'flex';
    btnStop.disabled = true;
  }

  // Maps each real getUserMedia error to the specific step below that
  // addresses it -- this mapping is the whole point of this page existing
  // as a live tool rather than a static article, per its own spec.
  function describeError(err) {
    switch (err && err.name) {
      case 'NotAllowedError':
      case 'PermissionDeniedError':
        return { sev: 'error', anchor: 'step-permission', html: '<strong>Camera access was blocked.</strong> This is a browser permission problem — see Step 1 below.' };
      case 'NotReadableError':
      case 'TrackStartError':
        return { sev: 'error', anchor: 'step-in-use', html: '<strong>Your camera is already in use.</strong> Another app is holding it — see Step 2 below.' };
      case 'NotFoundError':
      case 'DevicesNotFoundError':
        return { sev: 'error', anchor: 'step-connection', html: '<strong>No camera was detected at all.</strong> This usually means a connection or hardware problem — see Step 5 below (and Step 6 if that doesn\\u2019t fix it).' };
      case 'OverconstrainedError':
      case 'ConstraintNotSatisfiedError':
        return { sev: 'error', anchor: 'step-drivers', html: '<strong>Your camera couldn\\u2019t satisfy the request.</strong> This can point to outdated drivers — see Step 4 below.' };
      case 'SecurityError':
        return { sev: 'error', anchor: null, html: '<strong>Camera access requires a secure connection (HTTPS).</strong> This isn\\u2019t something you can fix locally — it means the page requesting camera access isn\\u2019t loaded securely.' };
      case 'AbortError':
        return { sev: 'warn', anchor: null, html: 'The camera request was interrupted. Click <strong>Start Camera</strong> to try again.' };
      default:
        return { sev: 'error', anchor: 'step-os-privacy', html: '<strong>Something went wrong starting the camera.</strong> ' + escapeHtml((err && err.message) || 'Unknown error') + ' — start with Step 3 below if the specific steps above don\\u2019t match.' };
    }
  }

  function populateDeviceSelect(devices) {
    var cams = devices.filter(function (d) { return d.kind === 'videoinput'; });
    deviceSelect.innerHTML = '';
    if (!cams.length) {
      var opt = document.createElement('option');
      opt.value = '';
      opt.textContent = 'No cameras found';
      deviceSelect.appendChild(opt);
      deviceSelect.disabled = true;
      return;
    }
    cams.forEach(function (d, i) {
      var opt = document.createElement('option');
      opt.value = d.deviceId;
      opt.textContent = d.label || ('Camera ' + (i + 1));
      if (d.deviceId === currentDeviceId) opt.selected = true;
      deviceSelect.appendChild(opt);
    });
    deviceSelect.disabled = false;
  }

  function refreshDeviceList() {
    if (!navigator.mediaDevices || !navigator.mediaDevices.enumerateDevices) return Promise.resolve();
    return navigator.mediaDevices.enumerateDevices().then(populateDeviceSelect).catch(function () {});
  }

  function jumpToStep(anchor) {
    if (!anchor) return;
    var el = document.getElementById(anchor);
    if (!el) return;
    el.scrollIntoView({ behavior: 'smooth', block: 'start' });
    el.classList.add('is-active');
    setTimeout(function () { el.classList.remove('is-active'); }, 2500);
  }

  function startStream(deviceId) {
    if (starting) return;
    starting = true;
    stopStream();
    setDiagnostic([{ sev: '', html: 'Requesting camera access\\u2026' }]);
    btnStart.disabled = true;

    var videoConstraint = deviceId ? { deviceId: { exact: deviceId } } : true;
    navigator.mediaDevices.getUserMedia({ video: videoConstraint, audio: false })
      .then(function (stream) {
        currentStream = stream;
        video.srcObject = stream;
        placeholder.style.display = 'none';
        previewWrap.classList.add('is-active');
        return video.play().catch(function () {}).then(function () { return stream; });
      })
      .then(function (stream) {
        var track = stream.getVideoTracks()[0];
        var settings = track.getSettings ? track.getSettings() : {};
        currentDeviceId = settings.deviceId || deviceId || '';
        btnStop.disabled = false;
        setDiagnostic([{ sev: 'ok', html: '<strong>Your camera works.</strong> If you followed a link here from a different tool that failed, try that tool again now.' }]);
        return refreshDeviceList();
      })
      .catch(function (err) {
        var described = describeError(err);
        setDiagnostic([described]);
        jumpToStep(described.anchor);
      })
      .finally(function () {
        starting = false;
        btnStart.disabled = false;
      });
  }

  btnStart.addEventListener('click', function () { startStream(deviceSelect.value); });
  btnStop.addEventListener('click', function () {
    stopStream();
    setDiagnostic([{ sev: '', html: 'Camera stopped. Click <strong>Start Camera</strong> to test again.' }]);
  });
  deviceSelect.addEventListener('change', function () {
    if (currentStream) startStream(deviceSelect.value);
  });

  window.addEventListener('pagehide', stopStream);
  document.addEventListener('visibilitychange', function () {
    if (document.visibilityState === 'hidden') stopStream();
  });

  if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) {
    setDiagnostic([{ sev: 'error', html: '<strong>Your browser doesn\\u2019t support camera access at all.</strong> Try the latest version of Chrome, Firefox, Edge, or Safari — this isn\\u2019t something the steps below can fix.' }]);
    btnStart.disabled = true;
  }
})();'''

CONTENT_HTML = '''<p>If your camera won't start, the live test above will tell you which of six causes is most likely — ordered here by how common each one actually is, so you fix the likely problem first instead of guessing. Click <strong>Start Camera</strong> above; a failed attempt automatically jumps you to the specific step that addresses it.</p>

<h2 id="step-permission">Step 1: Browser permission is blocked</h2>
<p>By far the most common cause. Either you dismissed the permission prompt without allowing access, or a previous visit to this site (or a similar one) was blocked and your browser remembered that choice.</p>
<p><strong>Chrome/Edge:</strong> click the camera icon (or the lock icon) in the address bar, find Camera in the list, and set it to Allow. <strong>Firefox:</strong> click the lock icon in the address bar, then the arrow next to "Blocked" or the camera permission, and allow it. <strong>Safari:</strong> open Safari → Settings → Websites → Camera, find this site in the list, and set it to Allow. Reload the page after changing the permission, then try again.</p>
<p>If you don't see this site listed at all under any of those settings, your permission may be set at the operating-system level instead — see Step 3.</p>

<h2 id="step-in-use">Step 2: Another app is already using the camera</h2>
<p>Most cameras can only be used by one application at a time. If a video-calling app, another browser tab running a camera test, screen-recording software, or a background utility is already holding the camera, this browser tab can't also access it — you'll typically see a message like "camera already in use" or "could not start video source."</p>
<p>Close other video-calling apps entirely (not just minimize them — check your system tray or menu bar for ones still running in the background), close any other browser tabs that might have an active camera test open, and check for OS-level camera utilities that might be holding it. Then try again.</p>

<h2 id="step-os-privacy">Step 3: Your operating system is blocking browser camera access</h2>
<p>Separately from the browser's own permission prompt, your operating system has its own camera privacy toggle that can block every browser at once, regardless of what you've allowed inside the browser itself.</p>
<details><summary><strong>Windows</strong></summary><p>Settings → Privacy &amp; security → Camera. Make sure "Camera access" is on, and that your specific browser is allowed in the app list further down that same page.</p></details>
<details><summary><strong>macOS</strong></summary><p>System Settings → Privacy &amp; Security → Camera. Find your browser in the list and make sure its toggle is on. If you don't see your browser listed at all, try the live test above once — macOS often only adds an app to this list the first time it actually requests camera access.</p></details>
<details><summary><strong>Android</strong></summary><p>Settings → Apps → [your browser] → Permissions → Camera, and make sure it's allowed. On newer Android versions this may show as "Allowed only while using the app," which is fine for a browser.</p></details>
<details><summary><strong>iOS / iPadOS</strong></summary><p>Settings → [your browser app] → Camera, and make sure it's toggled on. Safari specifically uses per-website permissions instead, managed in Settings → Safari → Camera.</p></details>
<p>For the full walkthrough with more detail on resetting a previously denied permission, see the <a href="/camera-permissions-guide-windows-mac-android-ios">Camera Permissions Guide</a>.</p>

<h2 id="step-drivers">Step 4: Outdated or missing camera drivers</h2>
<p>Mostly relevant on Windows and Linux, less so on macOS, Android, or iOS, where the camera driver is tightly integrated with the OS itself. If your camera doesn't show up in your operating system's own camera app either (not just in the browser), the driver is a likely cause.</p>
<p>On Windows, open Device Manager, expand "Cameras" or "Imaging devices," right-click your camera, and choose "Update driver." If the camera doesn't appear in Device Manager at all, try a different USB port, and check the manufacturer's website for a dedicated driver if it's an external webcam.</p>

<h2 id="step-connection">Step 5: A loose or disconnected camera cable</h2>
<p>For an external USB webcam specifically: check that the cable is fully seated at both ends, try a different USB port (ideally directly on the machine rather than through an unpowered hub), and try a different USB cable if you have one available — cables fail more often than the camera hardware itself.</p>
<p>For a built-in laptop camera, this step doesn't apply — skip to Step 6 if drivers and OS permissions both check out.</p>

<h2 id="step-hardware">Step 6: A genuine hardware failure</h2>
<p>If you've worked through every step above and the camera still won't start, confirm it independently of any browser: open your operating system's own built-in camera app (Camera on Windows, Photo Booth on macOS, the default Camera app on Android/iOS) and see if it can access the camera there. If the OS-level camera app also can't see it, the problem is with the camera hardware or its connection, not with any particular browser or website — at that point, the camera itself likely needs repair or replacement.</p>'''

FAQ = [
    {"question": "Why does the live test send me to a different step than I expected?", "answer": "The test reads the exact error your browser reports and maps it to the step that specifically addresses that error type, which is usually more accurate than guessing based on symptoms alone. If that step doesn't fix it, work through the remaining steps in order — they're listed by how common each cause actually is."},
    {"question": "The live test says my camera works, but it still fails on another site — why?", "answer": "This means your camera, browser, and OS permissions are all fine in general. The other site may have a completely different, unrelated problem (a bug in its own code, a stricter security policy, or a permission it hasn't been granted specifically for that site). Try allowing camera access specifically for that other site's address."},
    {"question": "I fixed the permission but the camera still won't start — what's next?", "answer": "Reload the page after changing any permission setting — browsers frequently only re-check camera permissions on a fresh page load, not immediately after you change the setting. If it still fails after reloading, work through Steps 2 through 6 in order."},
    {"question": "Does this guide work the same way on mobile?", "answer": "The live test itself works identically on mobile browsers. The OS-specific instructions in Step 3 include separate Android and iOS sections — expand whichever matches your device."},
]

TOOL = {
    "slug": "webcam-not-working-troubleshooting-guide",
    "meta_title": "Webcam Not Working? Troubleshooting Guide With a Live Test | WebcamTest",
    "meta_description": "Camera won't start? Run a live test that points you to the exact fix — permission, another app, OS privacy settings, drivers, connection, or hardware, ordered by likelihood.",
    "h1": "Webcam Not Working? Troubleshooting Guide",
    "subtitle": "Run a live test above — it points you straight to the specific step that fixes your exact problem.",
    "card": {
        "layout": "raw",
        "fields_html": FIELDS_HTML,
    },
    "script": SCRIPT,
    "content_html": CONTENT_HTML,
    "faq": FAQ,
}

if __name__ == "__main__":
    out_path = os.path.join(CONTENT_DIR, "webcam-not-working-troubleshooting-guide.json")
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(TOOL, f, indent=2, ensure_ascii=False)
    print("Wrote", out_path)
