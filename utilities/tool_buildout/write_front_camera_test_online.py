#!/usr/bin/env python3
"""Writes src/content/front-camera-test-online.json. Throwaway authoring
script, same pattern as write_webcam_test_online.py — see this project's
CLAUDE.md 'Authoring a new tool's content file'. Sibling of
write_rear_camera_test_online.py — same facingMode-acquisition shape,
mirrored constraint/labels/cross-link."""
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
    <div><h2>Front Camera Preview</h2><p class="panel-sub">Requests your selfie camera specifically, not whichever camera is default</p></div>
  </div>
  <div class="media-preview" id="cameraPreviewWrap">
    <video id="cameraVideo" autoplay playsinline muted></video>
    <div class="media-preview-placeholder" id="cameraPlaceholder">
      {PLACEHOLDER_ICON}
      <span>Your front camera feed will appear here</span>
    </div>
  </div>
  <div class="media-controls">
    <button type="button" class="btn-primary" id="btnStartCamera">Start Front Camera</button>
    <button type="button" class="btn-secondary" id="btnStopCamera" disabled>Stop Camera</button>
    <button type="button" class="btn-secondary" id="btnMirrorToggle" aria-pressed="true">Mirror (on by default)</button>
    <button type="button" class="btn-secondary" id="btnCapture" disabled>Capture Photo</button>
  </div>
</div>
<div class="tool-panel">
  <div class="panel-header">
    <span class="panel-icon">{INFO_ICON}</span>
    <div><h2>Front Camera Info</h2><p class="panel-sub">Reported once the camera is live</p></div>
  </div>
  <div class="stat-grid">
    <div class="stat-tile"><span class="stat-value" id="statResolution">—</span><span class="stat-label">Resolution</span></div>
    <div class="stat-tile"><span class="stat-value" id="statFps">—</span><span class="stat-label">Frame Rate</span></div>
    <div class="stat-tile"><span class="stat-value" id="statFacing">—</span><span class="stat-label">Facing Reported</span></div>
    <div class="stat-tile"><span class="stat-value" id="statDeviceName" style="font-size:.75rem;word-break:break-word">—</span><span class="stat-label">Device</span></div>
  </div>
  <p class="field-note">Front camera resolution is very often a fraction of the rear camera's — see the <a href="/rear-camera-test-online">Rear Camera Test</a> to compare directly.</p>
</div>
<div class="tool-panel">
  <div class="panel-header">
    <span class="panel-icon">{WARN_ICON}</span>
    <div><h2>Status</h2><p class="panel-sub">What to do if the front camera won't start</p></div>
  </div>
  <div class="diagnostic-panel" id="diagnosticPanel">
    <div class="diagnostic-item"><span class="diag-icon">{DOT_ICON}</span><span>Click <strong>Start Front Camera</strong> and allow access when your browser asks.</span></div>
  </div>
</div>'''

SCRIPT = '''(function () {
  'use strict';

  var video = document.getElementById('cameraVideo');
  var previewWrap = document.getElementById('cameraPreviewWrap');
  var placeholder = document.getElementById('cameraPlaceholder');
  var btnStart = document.getElementById('btnStartCamera');
  var btnStop = document.getElementById('btnStopCamera');
  var btnMirror = document.getElementById('btnMirrorToggle');
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

  // Front cameras are mirrored in the preview by long-standing convention
  // (so moving your hand right looks right, like a real mirror) but NOT in
  // the captured file, which matches what the camera actually saw -- this
  // trips people up constantly, so the mirror toggle starts ON here and
  // capture always saves the true, unmirrored frame regardless of the
  // toggle. See this tool's own content for the full explanation.
  previewWrap.classList.add('is-mirrored');

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
        return { sev: 'error', html: '<strong>No matching camera was found.</strong> This device may not have a front-facing camera, or the browser can\\u2019t reach it.' };
      case 'NotReadableError':
      case 'TrackStartError':
        return { sev: 'error', html: '<strong>Your camera is already in use.</strong> Another app or browser tab is probably holding it \\u2014 close video-calling apps or other camera tabs and try again.' };
      case 'OverconstrainedError':
      case 'ConstraintNotSatisfiedError':
        return { sev: 'error', html: '<strong>No front-facing camera could be matched.</strong> Some laptops and desktops only report one generic camera; try the plain <a href="/">Webcam Test</a> instead.' };
      case 'SecurityError':
        return { sev: 'error', html: '<strong>Camera access requires a secure connection.</strong> Make sure this page is loaded over HTTPS.' };
      case 'AbortError':
        return { sev: 'warn', html: 'The camera request was interrupted. Click <strong>Start Front Camera</strong> to try again.' };
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
    setDiagnostic([{ sev: '', html: 'Requesting front camera access\\u2026' }]);
    btnStart.disabled = true;

    // ideal (not exact) so a device with only one camera still gets a
    // stream instead of hard-failing -- same facingMode convention every
    // camera tool on this site uses.
    navigator.mediaDevices.getUserMedia({ video: { facingMode: { ideal: 'user' } }, audio: false })
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
        setDiagnostic([{ sev: 'ok', html: '<strong>Front camera is live.</strong> Nothing is uploaded \\u2014 this feed stays in your browser tab.' }]);
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
    // Always draws the real, unmirrored frame -- the mirror toggle only
    // applies a CSS transform to the live <video> preview, it never
    // touches the actual pixel data being drawn here.
    ctx.drawImage(video, 0, 0, w, h);
    canvas.toBlob(function (blob) {
      if (!blob) return;
      if (lastPhotoUrl) URL.revokeObjectURL(lastPhotoUrl);
      lastPhotoUrl = URL.createObjectURL(blob);
      var a = document.createElement('a');
      a.href = lastPhotoUrl;
      a.download = 'front-camera-photo.png';
      document.body.appendChild(a);
      a.click();
      a.remove();
    }, 'image/png');
  }

  btnStart.addEventListener('click', startStream);
  btnStop.addEventListener('click', function () {
    stopStream();
    setDiagnostic([{ sev: '', html: 'Camera stopped. Click <strong>Start Front Camera</strong> to test again.' }]);
  });
  btnMirror.addEventListener('click', function () {
    var mirrored = previewWrap.classList.toggle('is-mirrored');
    btnMirror.setAttribute('aria-pressed', mirrored ? 'true' : 'false');
    btnMirror.textContent = mirrored ? 'Mirror (on by default)' : 'Show Natural View';
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

CONTENT_HTML = '''<p>WebcamTest's front camera test is scoped specifically to your selfie camera, requesting it directly with the <code>facingMode: "user"</code> constraint rather than whatever camera your browser happens to pick by default. It reports the front camera's real resolution and frame rate, which are usually well below the rear camera's — a difference that surprises a lot of people the first time they check.</p>
<h2>Why the mirror toggle matters here</h2>
<p>Front cameras are mirrored in the live preview by long-standing convention — move your hand right, and it appears to move right on screen, exactly like looking in a real mirror. This tool starts with that mirroring on, matching what you'd see on a video call. Critically, mirroring is a <em>display-only</em> effect: the <strong>Capture Photo</strong> button always saves the true, unmirrored frame the camera actually captured, regardless of what the mirror toggle currently shows. Toggle it off any time to see your camera's natural, unmirrored view.</p>
<h2>Why front camera resolution is often disappointing</h2>
<p>Phone manufacturers invest far more in the rear camera system than the front one, and laptop webcams are frequently a low-resolution afterthought entirely. It's normal for the front camera's real, browser-reachable resolution to be a fraction of the rear camera's — see the <a href="/rear-camera-test-online">Rear Camera Test</a> to check the same device's rear lens and compare the two directly.</p>
<h2>What "ideal, not exact" means for this request</h2>
<p>This page asks for the front camera using an <em>ideal</em> constraint rather than an exact one. On a phone with both cameras, that reliably selects the front lens. On a laptop or desktop with only one camera, the same request still succeeds — your browser just uses the camera it has rather than failing outright, since there's nothing else to fall back to.</p>
<h2>Switching between front and rear</h2>
<p>If you want to flip between front and rear on the same page instead of two separate tools, the <a href="/mobile-camera-test-online">Mobile Camera Test</a> combines both with a single switch button, plus a running table of every distinct lens your phone reports.</p>'''

FAQ = [
    {"question": "Why is my captured photo not mirrored, even though the preview was?", "answer": "Mirroring only affects the live preview display, applied with a CSS transform after the video is already captured by the camera. The Capture Photo button always saves the true frame the camera actually recorded, which matches what other people would see of you on a real call."},
    {"question": "Why does this show a rear camera's resolution instead?", "answer": "This page requests the front camera with an \"ideal\" (not \"exact\") facingMode constraint, so a device that genuinely has no separate front-facing camera will still return whatever single camera it does have rather than failing. If your device does have a front camera and this still shows the wrong one, some Android devices label their cameras inconsistently at the driver level — this is a device/browser limitation, not something this page controls."},
    {"question": "Is my camera feed uploaded anywhere?", "answer": "No. The video stream is processed entirely inside your browser using JavaScript running on this page. It's never sent to WebcamTest's servers or any third party."},
    {"question": "Why is my front camera's frame rate lower than my rear camera's?", "answer": "Front cameras are typically lower-priority hardware with a smaller sensor and simpler autofocus system, which often means a lower maximum frame rate as well as lower resolution. This is a hardware limitation, not something this page affects."},
]

TOOL = {
    "slug": "front-camera-test-online",
    "meta_title": "Front Camera Test — Check Your Selfie Camera Online | WebcamTest",
    "meta_description": "Test your front-facing (selfie) camera online for free. See its real resolution and frame rate, capture a photo, and compare it against your rear camera.",
    "h1": "Front Camera Test",
    "subtitle": "Check your selfie camera specifically — its real resolution, frame rate, and how it compares to your rear camera.",
    "card": {
        "layout": "raw",
        "fields_html": FIELDS_HTML,
    },
    "script": SCRIPT,
    "content_html": CONTENT_HTML,
    "faq": FAQ,
}

if __name__ == "__main__":
    out_path = os.path.join(CONTENT_DIR, "front-camera-test-online.json")
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(TOOL, f, indent=2, ensure_ascii=False)
    print("Wrote", out_path)
