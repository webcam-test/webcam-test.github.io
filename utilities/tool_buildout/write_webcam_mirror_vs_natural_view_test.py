#!/usr/bin/env python3
"""Writes src/content/webcam-mirror-vs-natural-view-test.json. Throwaway
authoring script, same pattern as write_webcam_test_online.py — see this
project's CLAUDE.md 'Authoring a new tool's content file'.

Single tool-panel (span-3, full width) rather than the usual primary+side
shape — a side-by-side dual video comparison needs the width, and there's
no natural small side panel here, so a second panel isn't forced just to
fill the grid. Critically: ONE MediaStream feeds BOTH <video> elements
(one CSS-mirrored, one not) -- opening two separate getUserMedia calls
would fail on most devices, since a camera is exclusively locked to one
active request, per this tool's own spec."""
import json
import os

BASE = os.path.dirname(os.path.abspath(__file__))
CONTENT_DIR = os.path.normpath(os.path.join(BASE, "..", "..", "src", "content"))

CAMERA_ICON = '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M23 7l-7 5 7 5V7z"/><rect x="1" y="5" width="15" height="14" rx="2" ry="2"/></svg>'
WARN_ICON = '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M12 9v4M12 17h.01M10.29 3.86 1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z" stroke-linecap="round" stroke-linejoin="round"/></svg>'
DOT_ICON = '<svg viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="9"/></svg>'
PLACEHOLDER_ICON = '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5"><path d="M23 7l-7 5 7 5V7z"/><rect x="1" y="5" width="15" height="14" rx="2" ry="2"/></svg>'

FIELDS_HTML = f'''<div class="tool-panel span-3">
  <div class="panel-header">
    <span class="panel-icon">{CAMERA_ICON}</span>
    <div><h2>Mirrored vs. Natural View</h2><p class="panel-sub">Hold up a book, phone, or anything with text on it — the difference becomes unmistakable</p></div>
  </div>
  <div class="dual-preview">
    <div class="media-preview is-mirrored" id="mirroredWrap">
      <span class="preview-label">Mirrored — what you see of yourself</span>
      <video id="mirroredVideo" autoplay playsinline muted></video>
      <div class="media-preview-placeholder" id="placeholderMirrored">
        {PLACEHOLDER_ICON}
        <span>Your camera feed will appear here</span>
      </div>
    </div>
    <div class="media-preview" id="naturalWrap">
      <span class="preview-label">Natural — what call participants see</span>
      <video id="naturalVideo" autoplay playsinline muted></video>
      <div class="media-preview-placeholder" id="placeholderNatural">
        {PLACEHOLDER_ICON}
        <span>Your camera feed will appear here</span>
      </div>
    </div>
  </div>
  <div class="media-controls" style="margin-top:1rem">
    <button type="button" class="btn-primary" id="btnStartCamera">Start Camera</button>
    <button type="button" class="btn-secondary" id="btnStopCamera" disabled>Stop Camera</button>
    <select class="device-select" id="deviceSelect" aria-label="Select camera" disabled>
      <option value="">Default camera</option>
    </select>
  </div>
  <div class="diagnostic-panel" id="diagnosticPanel" style="margin-top:1rem">
    <div class="diagnostic-item"><span class="diag-icon">{DOT_ICON}</span><span>Click <strong>Start Camera</strong> and allow access when your browser asks.</span></div>
  </div>
</div>'''

SCRIPT = '''(function () {
  'use strict';

  var mirroredVideo = document.getElementById('mirroredVideo');
  var naturalVideo = document.getElementById('naturalVideo');
  var mirroredWrap = document.getElementById('mirroredWrap');
  var naturalWrap = document.getElementById('naturalWrap');
  var placeholderMirrored = document.getElementById('placeholderMirrored');
  var placeholderNatural = document.getElementById('placeholderNatural');
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

  // Every camera page on this site copies this stopStream()/error pattern
  // from webcam-test-online.json (see this project's own CLAUDE.md). This
  // tool has no device dropdown-triggered restart complexity beyond the
  // usual, but note it assigns the SAME stream to two <video> elements --
  // stopping the one shared stream releases both at once.
  function stopStream() {
    if (currentStream) {
      currentStream.getTracks().forEach(function (t) { t.stop(); });
      currentStream = null;
    }
    mirroredVideo.srcObject = null;
    naturalVideo.srcObject = null;
    mirroredWrap.classList.remove('is-active');
    naturalWrap.classList.remove('is-active');
    placeholderMirrored.style.display = 'flex';
    placeholderNatural.style.display = 'flex';
    btnStop.disabled = true;
  }

  function describeError(err) {
    switch (err && err.name) {
      case 'NotAllowedError':
      case 'PermissionDeniedError':
        return { sev: 'error', html: '<strong>Camera access was blocked.</strong> Click the camera icon in your address bar (or your browser\\u2019s site settings) and allow access, then try again.' };
      case 'NotFoundError':
      case 'DevicesNotFoundError':
        return { sev: 'error', html: '<strong>No camera was detected.</strong> Make sure a webcam is connected, then reload this page.' };
      case 'NotReadableError':
      case 'TrackStartError':
        return { sev: 'error', html: '<strong>Your camera is already in use.</strong> Another app or browser tab is probably holding it \\u2014 close video-calling apps or other camera tabs and try again.' };
      case 'OverconstrainedError':
      case 'ConstraintNotSatisfiedError':
        return { sev: 'error', html: '<strong>This camera doesn\\u2019t support the requested settings.</strong> Try a different camera from the list above.' };
      case 'SecurityError':
        return { sev: 'error', html: '<strong>Camera access requires a secure connection.</strong> Make sure this page is loaded over HTTPS.' };
      case 'AbortError':
        return { sev: 'warn', html: 'The camera request was interrupted. Click <strong>Start Camera</strong> to try again.' };
      default:
        return { sev: 'error', html: '<strong>Something went wrong starting the camera.</strong> ' + escapeHtml((err && err.message) || 'Unknown error') + '.' };
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
        // One shared MediaStream feeds both <video> elements -- opening a
        // second independent getUserMedia call for the same physical
        // camera fails on most devices, since it's exclusively locked to
        // the first request. The mirror effect is a pure CSS transform
        // applied to mirroredWrap only; naturalWrap plays the identical
        // stream untouched.
        mirroredVideo.srcObject = stream;
        naturalVideo.srcObject = stream;
        placeholderMirrored.style.display = 'none';
        placeholderNatural.style.display = 'none';
        mirroredWrap.classList.add('is-active');
        naturalWrap.classList.add('is-active');
        return Promise.all([
          mirroredVideo.play().catch(function () {}),
          naturalVideo.play().catch(function () {}),
        ]).then(function () { return stream; });
      })
      .then(function (stream) {
        var track = stream.getVideoTracks()[0];
        var settings = track.getSettings ? track.getSettings() : {};
        currentDeviceId = settings.deviceId || deviceId || '';
        btnStop.disabled = false;
        setDiagnostic([{ sev: 'ok', html: '<strong>Camera is live.</strong> The left panel shows what you see of yourself; the right panel shows what call participants actually see.' }]);
        return refreshDeviceList();
      })
      .catch(function (err) {
        setDiagnostic([describeError(err)]);
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
    setDiagnostic([{ sev: 'error', html: '<strong>Your browser doesn\\u2019t support camera access.</strong> Try the latest version of Chrome, Firefox, Edge, or Safari.' }]);
    btnStart.disabled = true;
  }
})();'''

CONTENT_HTML = '''<p>WebcamTest's mirror vs. natural view test shows your camera feed both ways at once, side by side, so the difference between how you see yourself and how everyone else sees you stops being an abstract idea. Hold up anything with text on it — a book, a phone screen, your laptop's own logo — and the reversal becomes unmistakable in the mirrored panel while the natural panel stays perfectly readable.</p>
<h2>Why your preview is mirrored but the real feed isn't</h2>
<p>Mirroring your own camera preview is a decades-old convention carried over from actual mirrors — it's how you're used to seeing your own reflection, so it feels natural and lets you check your appearance intuitively (is my hair straight, is something in the way) without having to mentally flip left and right. But it's a <em>display-only</em> effect: this page applies it with a simple CSS transform to the video element itself, after the camera has already captured the frame. The actual video data your browser would transmit in a real call is never flipped — that's the natural panel on the right.</p>
<h2>What Zoom, Teams and Meet actually show</h2>
<p>Every mainstream video-calling app follows the same convention this test demonstrates: your own self-preview tile is mirrored (for your comfort), while the exact same feed sent to every other participant is the natural, unmirrored view. If you're wearing a T-shirt with text, or sitting in front of a whiteboard with writing on it, what you see of yourself on your own screen is reversed — but what everyone else in the meeting sees is correct and readable. This is worth knowing before you assume a shirt logo or background sign will look wrong to others just because it looks wrong to you.</p>
<h2>Why one shared stream, not two separate ones</h2>
<p>This page requests your camera only once and plays that single stream into both video panels simultaneously — requesting the camera a second time for the same physical device fails on most hardware, since a camera can typically only be actively used by one request at a time. The mirrored panel is simply the identical live video, flipped visually with CSS; no extra camera access, processing, or bandwidth is involved in showing both views at once.</p>
<h2>A quick way to prove it to yourself</h2>
<p>Hold a page of a book, a printed label, or your phone's lock screen up to the camera. In the mirrored (left) panel, any text will read backwards — exactly like looking at it in a bathroom mirror. In the natural (right) panel, the same text reads correctly. That's the whole difference, made concrete instead of theoretical.</p>'''

FAQ = [
    {"question": "Does the mirror toggle affect what I actually send in a video call?", "answer": "No. Mirroring here — and in every video-calling app — is a local, display-only convenience applied after the camera has already captured the frame. It never changes the actual video data transmitted to other participants, which always matches the natural (unmirrored) view."},
    {"question": "Why does my shirt logo or background text look backwards to me but fine to everyone else?", "answer": "You're seeing your own mirrored self-preview, which flips left and right the same way a real mirror does. Everyone else in the call sees the natural, unmirrored feed, where any text reads correctly. This test's right-hand panel shows you exactly what they see."},
    {"question": "Why does this only open my camera once instead of twice?", "answer": "A single MediaStream can feed as many <video> elements as needed at once. Opening a second, independent request for the same physical camera would fail on most devices, since a camera is typically locked to one active request at a time — this page avoids that entirely by reusing one stream for both panels."},
    {"question": "Is my camera feed uploaded anywhere?", "answer": "No. Both video panels play the same locally-processed stream directly in your browser tab. Nothing is recorded, saved, or sent to WebcamTest's servers or any third party."},
]

TOOL = {
    "slug": "webcam-mirror-vs-natural-view-test",
    "meta_title": "Mirror vs. Natural View Test — See Both Sides at Once | WebcamTest",
    "meta_description": "See your mirrored self-view and the natural, unmirrored view call participants actually see — side by side, from one camera stream. Free, nothing uploaded.",
    "h1": "Mirror vs. Natural View Test",
    "subtitle": "See exactly what you see of yourself next to exactly what call participants actually see — side by side, from a single camera stream.",
    "card": {
        "layout": "raw",
        "fields_html": FIELDS_HTML,
    },
    "script": SCRIPT,
    "content_html": CONTENT_HTML,
    "faq": FAQ,
}

if __name__ == "__main__":
    out_path = os.path.join(CONTENT_DIR, "webcam-mirror-vs-natural-view-test.json")
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(TOOL, f, indent=2, ensure_ascii=False)
    print("Wrote", out_path)
