#!/usr/bin/env python3
"""Writes src/content/rear-camera-test-online.json. Throwaway authoring
script, same pattern as write_webcam_test_online.py — see this project's
CLAUDE.md 'Authoring a new tool's content file'. Sibling of
write_front_camera_test_online.py — same facingMode-acquisition shape, no
mirror (rear cameras aren't conventionally mirrored), cross-linked to it."""
import json
import os

BASE = os.path.dirname(os.path.abspath(__file__))
CONTENT_DIR = os.path.normpath(os.path.join(BASE, "..", "..", "src", "content"))

CAMERA_ICON = '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M23 7l-7 5 7 5V7z"/><rect x="1" y="5" width="15" height="14" rx="2" ry="2"/></svg>'
INFO_ICON = '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="10"/><path d="M12 16v-4M12 8h.01" stroke-linecap="round"/></svg>'
WARN_ICON = '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M12 9v4M12 17h.01M10.29 3.86 1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z" stroke-linecap="round" stroke-linejoin="round"/></svg>'
DOT_ICON = '<svg viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="9"/></svg>'
PLACEHOLDER_ICON = '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5"><path d="M23 7l-7 5 7 5V7z"/><rect x="1" y="5" width="15" height="14" rx="2" ry="2"/></svg>'

FIELDS_HTML = f'''<div class="tool-panel primary">
  <div class="panel-header">
    <span class="panel-icon">{CAMERA_ICON}</span>
    <div><h2>Rear Camera Preview</h2><p class="panel-sub">Requests your main camera specifically, not whichever camera is default</p></div>
  </div>
  <div class="media-preview" id="cameraPreviewWrap">
    <video id="cameraVideo" autoplay playsinline muted></video>
    <div class="media-preview-placeholder" id="cameraPlaceholder">
      {PLACEHOLDER_ICON}
      <span>Your rear camera feed will appear here</span>
    </div>
  </div>
  <div class="media-controls">
    <button type="button" class="btn-primary" id="btnStartCamera">Start Rear Camera</button>
    <button type="button" class="btn-secondary" id="btnStopCamera" disabled>Stop Camera</button>
    <button type="button" class="btn-secondary" id="btnCapture" disabled>Capture Photo</button>
  </div>
</div>
<div class="tool-panel">
  <div class="panel-header">
    <span class="panel-icon">{INFO_ICON}</span>
    <div><h2>Rear Camera Info</h2><p class="panel-sub">Reported once the camera is live</p></div>
  </div>
  <div class="stat-grid">
    <div class="stat-tile"><span class="stat-value" id="statResolution">—</span><span class="stat-label">Resolution</span></div>
    <div class="stat-tile"><span class="stat-value" id="statFps">—</span><span class="stat-label">Frame Rate</span></div>
    <div class="stat-tile"><span class="stat-value" id="statFacing">—</span><span class="stat-label">Facing Reported</span></div>
    <div class="stat-tile"><span class="stat-value" id="statDeviceName" style="font-size:.75rem;word-break:break-word">—</span><span class="stat-label">Device</span></div>
  </div>
  <p class="field-note">This is what your <strong>browser</strong> can reach, not your phone's advertised megapixel count — see below for why those two numbers are so different.</p>
</div>
<div class="tool-panel">
  <div class="panel-header">
    <span class="panel-icon">{WARN_ICON}</span>
    <div><h2>Status</h2><p class="panel-sub">What to do if the rear camera won't start</p></div>
  </div>
  <div class="diagnostic-panel" id="diagnosticPanel">
    <div class="diagnostic-item"><span class="diag-icon">{DOT_ICON}</span><span>Click <strong>Start Rear Camera</strong> and allow access when your browser asks.</span></div>
  </div>
</div>'''

SCRIPT = '''(function () {
  'use strict';

  var video = document.getElementById('cameraVideo');
  var previewWrap = document.getElementById('cameraPreviewWrap');
  var placeholder = document.getElementById('cameraPlaceholder');
  var btnStart = document.getElementById('btnStartCamera');
  var btnStop = document.getElementById('btnStopCamera');
  var btnCapture = document.getElementById('btnCapture');
  var diagnosticPanel = document.getElementById('diagnosticPanel');
  var statResolution = document.getElementById('statResolution');
  var statFps = document.getElementById('statFps');
  var statFacing = document.getElementById('statFacing');
  var statDeviceName = document.getElementById('statDeviceName');

  var currentStream = null;
  var starting = false;
  var canvas = document.createElement('canvas');
  var ctx = canvas.getContext('2d');
  var lastPhotoUrl = null;

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

  function resetInfo() {
    statResolution.textContent = '\\u2014';
    statFps.textContent = '\\u2014';
    statFacing.textContent = '\\u2014';
    statDeviceName.textContent = '\\u2014';
  }

  // Every camera page on this site copies this stopStream()/error pattern
  // from webcam-test-online.json (see this project's own CLAUDE.md). This
  // tool has no device dropdown (facingMode selects the lens, not an
  // enumerated device list), so there's no populateDeviceSelect() here.
  function stopStream() {
    if (currentStream) {
      currentStream.getTracks().forEach(function (t) { t.stop(); });
      currentStream = null;
    }
    video.srcObject = null;
    previewWrap.classList.remove('is-active');
    placeholder.style.display = 'flex';
    btnStop.disabled = true;
    btnCapture.disabled = true;
    resetInfo();
  }

  function describeError(err) {
    switch (err && err.name) {
      case 'NotAllowedError':
      case 'PermissionDeniedError':
        return { sev: 'error', html: '<strong>Camera access was blocked.</strong> Click the camera icon in your address bar (or your browser\\u2019s site settings) and allow access, then try again.' };
      case 'NotFoundError':
      case 'DevicesNotFoundError':
        return { sev: 'error', html: '<strong>No matching camera was found.</strong> This device may not have a rear-facing camera, or the browser can\\u2019t reach it.' };
      case 'NotReadableError':
      case 'TrackStartError':
        return { sev: 'error', html: '<strong>Your camera is already in use.</strong> Another app or browser tab is probably holding it \\u2014 close video-calling apps or other camera tabs and try again.' };
      case 'OverconstrainedError':
      case 'ConstraintNotSatisfiedError':
        return { sev: 'error', html: '<strong>No rear-facing camera could be matched.</strong> Some laptops and desktops only report one generic camera; try the plain <a href="/">Webcam Test</a> instead.' };
      case 'SecurityError':
        return { sev: 'error', html: '<strong>Camera access requires a secure connection.</strong> Make sure this page is loaded over HTTPS.' };
      case 'AbortError':
        return { sev: 'warn', html: 'The camera request was interrupted. Click <strong>Start Rear Camera</strong> to try again.' };
      default:
        return { sev: 'error', html: '<strong>Something went wrong starting the camera.</strong> ' + escapeHtml((err && err.message) || 'Unknown error') + '.' };
    }
  }

  function updateInfo(track) {
    var settings = track.getSettings ? track.getSettings() : {};
    statResolution.textContent = settings.width && settings.height ? (settings.width + '\\u00d7' + settings.height) : '\\u2014';
    statFps.textContent = settings.frameRate ? (Math.round(settings.frameRate * 10) / 10 + ' fps') : '\\u2014';
    statFacing.textContent = settings.facingMode || 'Not reported';
    statDeviceName.textContent = track.label || 'Camera';
  }

  function startStream() {
    if (starting) return;
    starting = true;
    stopStream();
    setDiagnostic([{ sev: '', html: 'Requesting rear camera access\\u2026' }]);
    btnStart.disabled = true;

    // ideal (not exact) so a device with only one camera still gets a
    // stream instead of hard-failing -- same facingMode convention every
    // camera tool on this site uses.
    navigator.mediaDevices.getUserMedia({ video: { facingMode: { ideal: 'environment' } }, audio: false })
      .then(function (stream) {
        currentStream = stream;
        video.srcObject = stream;
        placeholder.style.display = 'none';
        previewWrap.classList.add('is-active');
        return video.play().catch(function () {}).then(function () { return stream; });
      })
      .then(function (stream) {
        var track = stream.getVideoTracks()[0];
        updateInfo(track);
        btnStop.disabled = false;
        btnCapture.disabled = false;
        setDiagnostic([{ sev: 'ok', html: '<strong>Rear camera is live.</strong> Nothing is uploaded \\u2014 this feed stays in your browser tab.' }]);
      })
      .catch(function (err) {
        setDiagnostic([describeError(err)]);
      })
      .finally(function () {
        starting = false;
        btnStart.disabled = false;
      });
  }

  function capturePhoto() {
    if (!currentStream) return;
    var w = video.videoWidth, h = video.videoHeight;
    if (!w || !h) return;
    canvas.width = w;
    canvas.height = h;
    ctx.drawImage(video, 0, 0, w, h);
    canvas.toBlob(function (blob) {
      if (!blob) return;
      if (lastPhotoUrl) URL.revokeObjectURL(lastPhotoUrl);
      lastPhotoUrl = URL.createObjectURL(blob);
      var a = document.createElement('a');
      a.href = lastPhotoUrl;
      a.download = 'rear-camera-photo.png';
      document.body.appendChild(a);
      a.click();
      a.remove();
    }, 'image/png');
  }

  btnStart.addEventListener('click', startStream);
  btnStop.addEventListener('click', function () {
    stopStream();
    setDiagnostic([{ sev: '', html: 'Camera stopped. Click <strong>Start Rear Camera</strong> to test again.' }]);
  });
  btnCapture.addEventListener('click', capturePhoto);

  // Guaranteed teardown: release the camera the moment the visitor leaves
  // this page, even if they never clicked Stop.
  window.addEventListener('pagehide', function () {
    stopStream();
    if (lastPhotoUrl) { URL.revokeObjectURL(lastPhotoUrl); lastPhotoUrl = null; }
  });
  document.addEventListener('visibilitychange', function () {
    if (document.visibilityState === 'hidden') stopStream();
  });

  if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) {
    setDiagnostic([{ sev: 'error', html: '<strong>Your browser doesn\\u2019t support camera access.</strong> Try the latest version of Chrome, Firefox, Edge, or Safari.' }]);
    btnStart.disabled = true;
  }
})();'''

CONTENT_HTML = '''<p>WebcamTest's rear camera test is scoped specifically to your phone's main camera, requesting it directly with the <code>facingMode: "environment"</code> constraint. Just as important as the number itself is what it means: this reports what your <strong>browser</strong> can actually reach, which is almost always dramatically lower than the megapixel figure printed on your phone's spec sheet — and that gap is worth understanding before you assume something is broken.</p>
<h2>Why the browser number is so much lower than the advertised spec</h2>
<p>A phone's native camera app can capture at its sensor's full resolution — 12, 50, even 200 megapixels on recent flagships — using manufacturer-specific processing pipelines that aren't exposed to web pages at all. The browser's camera API caps out far lower, typically around 1080p to 4K (roughly 2 to 8 megapixels), because it's a generic cross-platform interface, not a direct line to the sensor. This is the single most common point of confusion on any browser-based camera tool, so it's worth stating plainly up front: <strong>a low number here does not mean your camera is broken or underperforming</strong> — it means you're seeing what the web platform, not your phone's hardware, is capable of delivering.</p>
<h2>What this test actually measures</h2>
<p>The stats above come directly from <code>getSettings()</code> on the live video track — the same negotiated resolution, frame rate, and facing mode every other camera tool on this site reports, scoped to your rear-facing lens specifically rather than whatever camera your browser defaults to.</p>
<h2>Comparing against your front camera</h2>
<p>See the <a href="/front-camera-test-online">Front Camera Test</a> to check your selfie camera the same way and compare the two directly — rear cameras are typically significantly higher resolution, since manufacturers prioritize that lens.</p>
<h2>Multiple rear lenses</h2>
<p>Many phones have more than one rear lens (wide, ultra-wide, telephoto), but <code>facingMode: "environment"</code> can only request "a" rear-facing camera — the browser picks one, usually the primary wide lens, and doesn't currently offer a standard way to specifically request the ultra-wide or telephoto lens by name. If you want to see every distinct lens your browser can reach, one at a time, use the <a href="/mobile-camera-test-online">Mobile Camera Test</a>, which tracks each one as you switch.</p>'''

FAQ = [
    {"question": "Why does this show such a low resolution compared to my phone's camera app?", "answer": "Your phone's native camera app captures at the sensor's full resolution using manufacturer-specific processing that isn't available to web pages. Browsers cap camera access far lower, typically 1080p to 4K, because the web camera API is a generic, cross-platform interface rather than direct sensor access. A low number here reflects a browser platform limit, not a problem with your camera."},
    {"question": "Can I test my phone's ultra-wide or telephoto lens specifically?", "answer": "Not reliably. The standard facingMode: \"environment\" constraint can only ask for \"a\" rear-facing camera — the browser chooses which one, usually the primary wide lens — with no standard way to request a specific secondary lens by name. The Mobile Camera Test can surface additional lenses some phones expose as you switch cameras, but this isn't guaranteed on every device."},
    {"question": "Is my camera feed uploaded anywhere?", "answer": "No. The video stream is processed entirely inside your browser using JavaScript running on this page. It's never sent to WebcamTest's servers or any third party."},
    {"question": "Why did I get an error even though my phone definitely has a rear camera?", "answer": "Check that no other app or browser tab is currently holding the camera (a video-calling app running in the background is the most common cause), and that you allowed camera access when your browser's permission prompt appeared. If neither applies, try reloading the page — a previous camera session on the same tab occasionally needs a fresh start."},
]

TOOL = {
    "slug": "rear-camera-test-online",
    "meta_title": "Rear Camera Test — Check Your Phone's Main Camera Online | WebcamTest",
    "meta_description": "Test your phone's rear (main) camera online for free. See its real browser-reachable resolution and frame rate, and understand why it's lower than the advertised megapixel count.",
    "h1": "Rear Camera Test",
    "subtitle": "Check your phone's main camera — and understand why the browser reports far fewer megapixels than the spec sheet.",
    "card": {
        "layout": "raw",
        "fields_html": FIELDS_HTML,
    },
    "script": SCRIPT,
    "content_html": CONTENT_HTML,
    "faq": FAQ,
}

if __name__ == "__main__":
    out_path = os.path.join(CONTENT_DIR, "rear-camera-test-online.json")
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(TOOL, f, indent=2, ensure_ascii=False)
    print("Wrote", out_path)
