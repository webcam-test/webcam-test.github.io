#!/usr/bin/env python3
"""Writes src/content/mobile-camera-test-online.json."""
import json
import os

BASE = os.path.dirname(os.path.abspath(__file__))
CONTENT_DIR = os.path.normpath(os.path.join(BASE, "..", "..", "src", "content"))

MOBILE_ICON = '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect x="6" y="2" width="12" height="20" rx="2" ry="2"/><path d="M11 18h2" stroke-linecap="round"/></svg>'
TABLE_ICON = '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect x="3" y="3" width="18" height="18" rx="2"/><path d="M3 9h18M3 15h18M9 3v18"/></svg>'
DOT_ICON = '<svg viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="9"/></svg>'
PLACEHOLDER_ICON = '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5"><rect x="6" y="2" width="12" height="20" rx="2" ry="2"/><path d="M11 18h2" stroke-linecap="round"/></svg>'

FIELDS_HTML = f'''<div class="tool-panel primary">
  <div class="panel-header">
    <span class="panel-icon">{MOBILE_ICON}</span>
    <div><h2>Camera Preview</h2><p class="panel-sub">Switch between your front and rear cameras</p></div>
  </div>
  <div class="media-preview" id="cameraPreviewWrap">
    <video id="cameraVideo" autoplay playsinline muted></video>
    <div class="media-preview-placeholder" id="cameraPlaceholder">
      {PLACEHOLDER_ICON}
      <span>Your camera feed will appear here</span>
    </div>
  </div>
  <canvas id="captureCanvas" style="display:none"></canvas>
  <div class="media-controls">
    <button type="button" class="btn-primary" id="btnFront">Front Camera</button>
    <button type="button" class="btn-primary" id="btnRear">Rear Camera</button>
    <button type="button" class="btn-secondary" id="btnCapture" disabled>Capture Photo</button>
    <button type="button" class="btn-secondary" id="btnStop" disabled>Stop Camera</button>
  </div>
  <div class="media-controls" id="lensSelectRow" style="display:none">
    <select class="device-select" id="lensSelect" aria-label="Select a specific lens"></select>
  </div>
  <div class="stat-grid" style="margin-top:1rem">
    <div class="stat-tile"><span class="stat-value" id="statFacing">—</span><span class="stat-label">Active Facing</span></div>
    <div class="stat-tile"><span class="stat-value" id="statResolution">—</span><span class="stat-label">Resolution</span></div>
    <div class="stat-tile"><span class="stat-value" id="statFps">—</span><span class="stat-label">Frame Rate</span></div>
    <div class="stat-tile"><span class="stat-value" id="statOrientation">—</span><span class="stat-label">Screen Orientation</span></div>
  </div>
  <div class="diagnostic-panel" id="diagnosticPanel" style="margin-top:1rem">
    <div class="diagnostic-item" id="diagDefault"><span class="diag-icon">{DOT_ICON}</span><span>Tap <strong>Front Camera</strong> or <strong>Rear Camera</strong> to begin.</span></div>
  </div>
</div>
<div class="tool-panel span-2">
  <div class="panel-header">
    <span class="panel-icon">{TABLE_ICON}</span>
    <div><h2>Lenses Tested This Session</h2><p class="panel-sub">Every distinct camera your browser has reported so far</p></div>
  </div>
  <div class="info-table" id="lensTable">
    <div class="info-row"><span class="info-label" style="color:var(--text-muted)">No lens tested yet — switch cameras above to populate this table.</span></div>
  </div>
  <p class="field-note">iPhones running Safari report exactly one front and one rear entry, no matter how many physical lenses the phone has — this is a browser limitation, not a bug. Android/Chromium phones usually report more, though some manufacturers group several lenses into one entry.</p>
</div>'''

SCRIPT = r'''(function () {
  'use strict';

  var video = document.getElementById('cameraVideo');
  var previewWrap = document.getElementById('cameraPreviewWrap');
  var placeholder = document.getElementById('cameraPlaceholder');
  var canvas = document.getElementById('captureCanvas');
  var btnFront = document.getElementById('btnFront');
  var btnRear = document.getElementById('btnRear');
  var btnCapture = document.getElementById('btnCapture');
  var btnStop = document.getElementById('btnStop');
  var lensSelectRow = document.getElementById('lensSelectRow');
  var lensSelect = document.getElementById('lensSelect');
  var diagnosticPanel = document.getElementById('diagnosticPanel');
  var lensTable = document.getElementById('lensTable');
  var statFacing = document.getElementById('statFacing');
  var statResolution = document.getElementById('statResolution');
  var statFps = document.getElementById('statFps');
  var statOrientation = document.getElementById('statOrientation');

  var currentStream = null;
  var starting = false;
  var testedLenses = {}; // deviceId -> { label, facing, width, height, fps }

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

  function updateOrientation() {
    var o = (screen.orientation && screen.orientation.type) ||
      (window.innerHeight >= window.innerWidth ? 'portrait' : 'landscape');
    statOrientation.textContent = o;
  }

  function renderLensTable() {
    var keys = Object.keys(testedLenses);
    if (!keys.length) {
      lensTable.innerHTML = '<div class="info-row"><span class="info-label" style="color:var(--text-muted)">No lens tested yet — switch cameras above to populate this table.</span></div>';
      return;
    }
    lensTable.innerHTML = keys.map(function (id) {
      var l = testedLenses[id];
      return '<div class="info-row"><span class="info-label">' + escapeHtml(l.label) + ' (' + escapeHtml(l.facing) + ')</span>' +
        '<span class="info-value">' + (l.width ? (l.width + '×' + l.height + ' · ' + l.fps) : 'Not reported') + '</span></div>';
    }).join('');
  }

  // Same stopStream()/error-mapping shape as every other camera tool's own
  // script on this site (see webcam-test-online and this project's CLAUDE.md
  // — no shared runtime file, so this block is copied, not imported).
  function stopStream() {
    if (currentStream) {
      currentStream.getTracks().forEach(function (t) { t.stop(); });
      currentStream = null;
    }
    video.srcObject = null;
    previewWrap.classList.remove('is-active');
    placeholder.style.display = 'flex';
    btnCapture.disabled = true;
    btnStop.disabled = true;
  }

  function describeError(err) {
    switch (err && err.name) {
      case 'NotAllowedError':
      case 'PermissionDeniedError':
        return { sev: 'error', html: '<strong>Camera access was blocked.</strong> Allow access in your browser’s site settings, then try again.' };
      case 'NotFoundError':
      case 'DevicesNotFoundError':
        return { sev: 'error', html: '<strong>No matching camera was found.</strong> This phone may not have that camera, or the browser can’t reach it.' };
      case 'NotReadableError':
      case 'TrackStartError':
        return { sev: 'error', html: '<strong>Your camera is already in use</strong> by another app.' };
      case 'OverconstrainedError':
        return { sev: 'error', html: '<strong>That camera isn’t available.</strong> Try the other facing direction or a different lens.' };
      case 'SecurityError':
        return { sev: 'error', html: '<strong>Camera access requires HTTPS.</strong>' };
      default:
        return { sev: 'error', html: '<strong>Something went wrong starting the camera.</strong> ' + escapeHtml((err && err.message) || 'Unknown error') + '.' };
    }
  }

  function populateLensSelect(devices) {
    var cams = devices.filter(function (d) { return d.kind === 'videoinput'; });
    if (cams.length <= 2) {
      lensSelectRow.style.display = 'none';
      return;
    }
    lensSelectRow.style.display = 'flex';
    lensSelect.innerHTML = '<option value="">Choose a specific lens…</option>' + cams.map(function (d, i) {
      return '<option value="' + d.deviceId + '">' + escapeHtml(d.label || ('Camera ' + (i + 1))) + '</option>';
    }).join('');
  }

  function startStream(constraints, requestedFacing) {
    if (starting) return;
    starting = true;
    if (currentStream) {
      currentStream.getTracks().forEach(function (t) { t.stop(); });
      currentStream = null;
    }
    setDiagnostic([{ sev: '', html: 'Requesting camera…' }]);

    navigator.mediaDevices.getUserMedia({ video: constraints, audio: false })
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
        var facing = settings.facingMode || requestedFacing || 'unspecified';
        statFacing.textContent = facing;
        statResolution.textContent = settings.width && settings.height ? (settings.width + '×' + settings.height) : 'Not reported';
        statFps.textContent = settings.frameRate ? (Math.round(settings.frameRate * 10) / 10 + ' fps') : 'Not reported';

        var key = settings.deviceId || facing;
        testedLenses[key] = {
          label: track.label || (facing + ' camera'),
          facing: facing,
          width: settings.width || 0,
          height: settings.height || 0,
          fps: settings.frameRate ? (Math.round(settings.frameRate * 10) / 10 + ' fps') : 'Not reported',
        };
        renderLensTable();

        btnCapture.disabled = false;
        btnStop.disabled = false;
        setDiagnostic([{ sev: 'ok', html: '<strong>Camera is live.</strong> Nothing is uploaded — this stays in your browser.' }]);

        return navigator.mediaDevices.enumerateDevices().then(populateLensSelect);
      })
      .catch(function (err) { setDiagnostic([describeError(err)]); })
      .finally(function () { starting = false; });
  }

  btnFront.addEventListener('click', function () {
    startStream({ facingMode: { ideal: 'user' } }, 'user');
  });
  btnRear.addEventListener('click', function () {
    startStream({ facingMode: { ideal: 'environment' } }, 'environment');
  });
  lensSelect.addEventListener('change', function () {
    if (!lensSelect.value) return;
    startStream({ deviceId: { exact: lensSelect.value } }, null);
  });
  btnStop.addEventListener('click', function () {
    stopStream();
    setDiagnostic([{ sev: '', html: 'Camera stopped.' }]);
  });

  btnCapture.addEventListener('click', function () {
    if (!currentStream) return;
    var w = video.videoWidth, h = video.videoHeight;
    if (!w || !h) return;
    canvas.width = w;
    canvas.height = h;
    canvas.getContext('2d').drawImage(video, 0, 0, w, h);
    canvas.toBlob(function (blob) {
      if (!blob) return;
      var url = URL.createObjectURL(blob);
      var a = document.createElement('a');
      a.href = url;
      a.download = 'mobile-camera-test-photo.jpg';
      document.body.appendChild(a);
      a.click();
      a.remove();
      setTimeout(function () { URL.revokeObjectURL(url); }, 1000);
    }, 'image/jpeg', 0.92);
  });

  window.addEventListener('pagehide', stopStream);
  document.addEventListener('visibilitychange', function () {
    if (document.visibilityState === 'hidden') stopStream();
  });

  if (screen.orientation) {
    screen.orientation.addEventListener('change', updateOrientation);
  } else {
    window.addEventListener('resize', updateOrientation);
  }
  updateOrientation();

  if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) {
    setDiagnostic([{ sev: 'error', html: '<strong>Your browser doesn’t support camera access.</strong>' }]);
    btnFront.disabled = true;
    btnRear.disabled = true;
  }
})();'''

CONTENT_HTML = '''<p>Most "webcam test" tools are desktop pages that happen to load on a phone. This one is built mobile-first: switch instantly between your front and rear cameras, see resolution and frame rate reported per lens, and capture a photo — all in a portrait-friendly layout with touch-sized controls.</p>
<h2>Why phone cameras behave differently from laptop webcams</h2>
<p>A phone typically exposes at least two cameras — front (selfie) and rear (main) — through the <code>facingMode</code> constraint, requested here as <em>ideal</em> rather than <em>exact</em> so the request still succeeds on devices that don't label their cameras with a facing direction at all. Rear cameras almost always report a higher resolution and frame rate than front cameras; that gap is normal, not a fault with your device.</p>
<h2>The multi-lens gap between iPhone and Android</h2>
<p>This is the single most common point of confusion in mobile camera testing: Safari on iPhone exposes exactly one front camera and one rear camera to web pages, regardless of how many physical lenses your iPhone actually has — even a phone with a triple rear camera system reports just one combined rear entry. Android's Chromium browsers usually expose more individual lenses, though some phone manufacturers group several lenses into a single reported entry too. If your phone has three rear lenses and this page only shows one, that's a browser limitation on that platform, not a bug in this tool.</p>
<h2>Why the resolution shown is lower than your phone's advertised camera</h2>
<p>Browsers reach cameras through a constrained web API that tops out well below what a phone's native camera app can capture — commonly 1080p or 4K through the browser, versus 12, 50, or even 200 megapixels through the manufacturer's own camera app. This gap exists on every phone and every browser; it isn't specific to your device.</p>
<h2>Where your capture goes</h2>
<p>Tapping <strong>Capture Photo</strong> draws the current video frame to an in-page canvas at your camera's native resolution and saves it straight to your device as a JPEG — nothing is uploaded or stored anywhere else.</p>'''

FAQ = [
    {"question": "Why does my iPhone only show one rear camera when it has three lenses?", "answer": "Safari on iOS reports exactly one combined rear-camera entry to web pages regardless of how many physical lenses your iPhone has. This is a platform limitation in iOS Safari, not something any website can change."},
    {"question": "Why is my front camera's resolution so much lower than my rear camera's?", "answer": "This is normal on almost every phone — the front (selfie) camera sensor is physically smaller and lower-resolution than the rear camera on the vast majority of devices, so a large gap between the two is expected."},
    {"question": "Can I test more than two cameras on my Android phone?", "answer": "Yes — if your browser reports more than two camera entries, a lens picker dropdown appears below the main Front/Rear buttons, listing every individual camera your browser can see."},
    {"question": "Is my captured photo uploaded anywhere?", "answer": "No. The photo is drawn to a canvas element and saved directly to your device using your browser's own download mechanism. It never leaves your phone."},
]

TOOL = {
    "slug": "mobile-camera-test-online",
    "meta_title": "Mobile Camera Test — Test Your Phone's Front & Rear Camera | WebcamTest",
    "meta_description": "Test your phone's front and rear cameras online. See resolution and frame rate per lens, switch cameras instantly, and capture a photo — built mobile-first, free, no upload.",
    "h1": "Mobile Camera Test",
    "subtitle": "Switch between your phone's front and rear cameras and see the real resolution and frame rate each one reports.",
    "card": {
        "layout": "raw",
        "fields_html": FIELDS_HTML,
    },
    "script": SCRIPT,
    "content_html": CONTENT_HTML,
    "faq": FAQ,
}

if __name__ == "__main__":
    out_path = os.path.join(CONTENT_DIR, "mobile-camera-test-online.json")
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(TOOL, f, indent=2, ensure_ascii=False)
    print("Wrote", out_path)
