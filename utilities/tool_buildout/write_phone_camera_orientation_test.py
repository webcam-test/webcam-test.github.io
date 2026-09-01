#!/usr/bin/env python3
"""Writes src/content/phone-camera-orientation-test.json."""
import json
import os

BASE = os.path.dirname(os.path.abspath(__file__))
CONTENT_DIR = os.path.normpath(os.path.join(BASE, "..", "..", "src", "content"))

CAMERA_ICON = '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M23 7l-7 5 7 5V7z"/><rect x="1" y="5" width="15" height="14" rx="2" ry="2"/></svg>'
ROTATE_ICON = '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M21 12a9 9 0 1 1-3-6.7" stroke-linecap="round"/><path d="M21 3v6h-6" stroke-linecap="round" stroke-linejoin="round"/></svg>'
LIST_ICON = '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M9 6h11M9 12h11M9 18h11M4 6h.01M4 12h.01M4 18h.01" stroke-linecap="round"/></svg>'
DOT_ICON = '<svg viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="9"/></svg>'
PLACEHOLDER_ICON = '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5"><path d="M23 7l-7 5 7 5V7z"/><rect x="1" y="5" width="15" height="14" rx="2" ry="2"/></svg>'

FIELDS_HTML = f'''<div class="tool-panel primary">
  <div class="panel-header">
    <span class="panel-icon">{CAMERA_ICON}</span>
    <div><h2>Camera Orientation Test</h2><p class="panel-sub">Rotate your phone between captures to compare how dimensions change</p></div>
  </div>
  <div class="media-preview" id="cameraPreviewWrap">
    <video id="cameraVideo" autoplay playsinline muted></video>
    <div class="media-preview-placeholder" id="cameraPlaceholder">
      {PLACEHOLDER_ICON}
      <span>Your camera feed will appear here</span>
    </div>
  </div>
  <canvas id="captureCanvas" style="display:none"></canvas>
  <div class="media-controls" style="margin-top:1rem">
    <button type="button" class="btn-primary" id="btnStartCamera">Start Camera</button>
    <button type="button" class="btn-secondary" id="btnStopCamera" disabled>Stop Camera</button>
    <select class="device-select" id="deviceSelect" aria-label="Select camera" disabled>
      <option value="">Default camera</option>
    </select>
  </div>
  <div class="tool-actions" style="margin-top:.5rem">
    <button type="button" class="btn-secondary" id="btnCapture" disabled>Capture This Orientation</button>
  </div>
  <div class="diagnostic-panel" id="diagnosticPanel" style="margin-top:1rem">
    <div class="diagnostic-item" id="diagDefault"><span class="diag-icon">{DOT_ICON}</span><span>Click <strong>Start Camera</strong> and allow access when your browser asks.</span></div>
  </div>
</div>
<div class="tool-panel">
  <div class="panel-header">
    <span class="panel-icon">{ROTATE_ICON}</span>
    <div><h2>Live Readout</h2><p class="panel-sub">Updates as you rotate</p></div>
  </div>
  <div class="stat-grid">
    <div class="stat-tile highlight"><span class="stat-value" id="statOrientation">—</span><span class="stat-label">Screen Orientation</span></div>
    <div class="stat-tile"><span class="stat-value" id="statWidth">—</span><span class="stat-label">Stream Width</span></div>
    <div class="stat-tile"><span class="stat-value" id="statHeight">—</span><span class="stat-label">Stream Height</span></div>
  </div>
  <p class="field-note">Whether these swap when you rotate depends entirely on your phone and browser — both behaviours are normal, which is exactly what this test demonstrates.</p>
</div>
<div class="tool-panel">
  <div class="panel-header">
    <span class="panel-icon">{LIST_ICON}</span>
    <div><h2>Captured Comparisons</h2></div>
  </div>
  <div class="capture-list" id="captureList">
    <p class="capture-empty" id="captureEmpty">Rotate your phone and capture in each orientation to compare — nothing is uploaded.</p>
  </div>
</div>'''

SCRIPT = r'''(function () {
  'use strict';

  var video = document.getElementById('cameraVideo');
  var previewWrap = document.getElementById('cameraPreviewWrap');
  var placeholder = document.getElementById('cameraPlaceholder');
  var canvas = document.getElementById('captureCanvas');
  var deviceSelect = document.getElementById('deviceSelect');
  var btnStart = document.getElementById('btnStartCamera');
  var btnStop = document.getElementById('btnStopCamera');
  var btnCapture = document.getElementById('btnCapture');
  var diagnosticPanel = document.getElementById('diagnosticPanel');
  var statOrientation = document.getElementById('statOrientation');
  var statWidth = document.getElementById('statWidth');
  var statHeight = document.getElementById('statHeight');
  var captureList = document.getElementById('captureList');
  var captureEmpty = document.getElementById('captureEmpty');

  var currentStream = null;
  var starting = false;
  var captures = [];
  var captureIdCounter = 0;

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

  function currentOrientationLabel() {
    if (screen.orientation && screen.orientation.type) return screen.orientation.type;
    if (typeof window.orientation === 'number') {
      return Math.abs(window.orientation) === 90 ? 'landscape (legacy API)' : 'portrait (legacy API)';
    }
    return window.innerWidth > window.innerHeight ? 'landscape (inferred)' : 'portrait (inferred)';
  }

  function updateLiveReadout() {
    statOrientation.textContent = currentOrientationLabel();
    if (currentStream) {
      var track = currentStream.getVideoTracks()[0];
      var settings = track.getSettings ? track.getSettings() : {};
      statWidth.textContent = settings.width ? String(settings.width) : (video.videoWidth || '—');
      statHeight.textContent = settings.height ? String(settings.height) : (video.videoHeight || '—');
    }
  }

  function renderCaptureList() {
    if (!captures.length) {
      captureList.innerHTML = '';
      captureList.appendChild(captureEmpty);
      return;
    }
    captureList.innerHTML = captures.map(function (cap) {
      return '<div class="capture-row"><span class="capture-row-meta">' + escapeHtml(cap.orientation) + ' — ' + cap.width + '×' + cap.height + '</span>' +
        '<span class="capture-row-actions"><a href="' + cap.url + '" download="orientation-test-' + cap.id + '.jpg">Download</a></span></div>';
    }).join('');
  }

  function captureCurrentOrientation() {
    if (!currentStream || !video.videoWidth) return;
    canvas.width = video.videoWidth;
    canvas.height = video.videoHeight;
    canvas.getContext('2d').drawImage(video, 0, 0);
    var url = canvas.toDataURL('image/jpeg', 0.9);
    captureIdCounter++;
    captures.unshift({ id: captureIdCounter, orientation: currentOrientationLabel(), width: video.videoWidth, height: video.videoHeight, url: url });
    if (captures.length > 6) captures.pop();
    renderCaptureList();
  }

  // Same stopStream()/describeError()/populateDeviceSelect() pattern as
  // webcam-test-online's own script (see this project's CLAUDE.md -- every
  // camera tool copies this teardown block rather than importing a shared file).
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
    statWidth.textContent = '—';
    statHeight.textContent = '—';
  }

  function describeError(err) {
    switch (err && err.name) {
      case 'NotAllowedError':
      case 'PermissionDeniedError':
        return { sev: 'error', html: '<strong>Camera access was blocked.</strong> Allow access from your browser’s address-bar icon or site settings, then try again.' };
      case 'NotFoundError':
      case 'DevicesNotFoundError':
        return { sev: 'error', html: '<strong>No camera was detected.</strong> Connect a camera and reload this page.' };
      case 'NotReadableError':
      case 'TrackStartError':
        return { sev: 'error', html: '<strong>Your camera is already in use</strong> by another app or browser tab.' };
      case 'OverconstrainedError':
        return { sev: 'error', html: '<strong>This camera doesn’t support the requested settings.</strong> Try another camera from the list.' };
      case 'SecurityError':
        return { sev: 'error', html: '<strong>Camera access requires HTTPS.</strong>' };
      default:
        return { sev: 'error', html: '<strong>Something went wrong starting the camera.</strong> ' + escapeHtml((err && err.message) || 'Unknown error') + '.' };
    }
  }

  function populateDeviceSelect(devices, currentDeviceId) {
    var cams = devices.filter(function (d) { return d.kind === 'videoinput'; });
    deviceSelect.innerHTML = '';
    cams.forEach(function (d, i) {
      var opt = document.createElement('option');
      opt.value = d.deviceId;
      opt.textContent = d.label || ('Camera ' + (i + 1));
      if (d.deviceId === currentDeviceId) opt.selected = true;
      deviceSelect.appendChild(opt);
    });
    deviceSelect.disabled = cams.length === 0;
  }

  function startStream(deviceId) {
    if (starting) return;
    starting = true;
    stopStream();
    setDiagnostic([{ sev: '', html: 'Requesting camera access…' }]);
    btnStart.disabled = true;

    navigator.mediaDevices.getUserMedia({ video: deviceId ? { deviceId: { exact: deviceId } } : true, audio: false })
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
        btnStop.disabled = false;
        btnCapture.disabled = false;
        setDiagnostic([{ sev: 'ok', html: '<strong>Camera is live.</strong> Rotate your phone and click Capture to compare dimensions across orientations.' }]);
        updateLiveReadout();
        return navigator.mediaDevices.enumerateDevices().then(function (devices) {
          populateDeviceSelect(devices, settings.deviceId);
        });
      })
      .catch(function (err) { setDiagnostic([describeError(err)]); stopStream(); })
      .finally(function () { starting = false; btnStart.disabled = false; });
  }

  btnStart.addEventListener('click', function () { startStream(deviceSelect.value); });
  btnStop.addEventListener('click', function () {
    stopStream();
    setDiagnostic([{ sev: '', html: 'Camera stopped.' }]);
  });
  deviceSelect.addEventListener('change', function () { if (currentStream) startStream(deviceSelect.value); });
  btnCapture.addEventListener('click', captureCurrentOrientation);

  // Listen on screen.orientation change (with a legacy-API/inferred
  // fallback for browsers that don't support it) so the readout tracks
  // rotation live, per this tool's own spec note.
  if (screen.orientation && screen.orientation.addEventListener) {
    screen.orientation.addEventListener('change', updateLiveReadout);
  } else {
    window.addEventListener('orientationchange', updateLiveReadout);
  }
  window.addEventListener('resize', updateLiveReadout);

  window.addEventListener('pagehide', stopStream);
  document.addEventListener('visibilitychange', function () {
    if (document.visibilityState === 'hidden') stopStream();
  });

  updateLiveReadout();
  renderCaptureList();

  if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) {
    setDiagnostic([{ sev: 'error', html: '<strong>Your browser doesn’t support camera access.</strong>' }]);
    btnStart.disabled = true;
  }
})();'''

CONTENT_HTML = '''<p>Ever had a photo taken in portrait arrive sideways, or a video call feed rotate unexpectedly when you turn your phone? This tool shows exactly what your browser reports about stream dimensions and screen orientation as you rotate, so you can see the actual behaviour rather than guessing at it.</p>
<h2>Why stream dimensions don't always swap on rotation</h2>
<p>Some phones and browsers report a camera stream's width and height swapping when you rotate between portrait and landscape; others keep reporting the same dimensions regardless of physical orientation and instead rely on a rotation flag applied elsewhere. Both behaviours are normal and both happen in real-world use — this tool is built to show you which one your specific device and browser combination does, not to declare one of them correct.</p>
<h2>Why a captured photo can display differently across apps</h2>
<p>A captured still image can carry an EXIF orientation flag — metadata describing how the image should be rotated for correct display — separately from the actual pixel dimensions stored in the file. Different apps and viewers handle this flag inconsistently: some rotate the image automatically before displaying it, others show it exactly as stored, ignoring the flag entirely. This is the most common reason a portrait photo looks correctly oriented in one app and sideways in another, even though it's the exact same file.</p>
<h2>Using the comparison captures</h2>
<p>Capture a photo in portrait, rotate your phone, and capture again in landscape — the live readout and your saved captures let you compare the actual reported dimensions side by side, rather than relying on memory or assumption.</p>'''

FAQ = [
    {"question": "Why does my stream width and height stay the same even when I rotate my phone?", "answer": "This is normal on many phone/browser combinations — some report the same stream dimensions regardless of physical rotation and apply orientation separately, rather than swapping width and height. It doesn't indicate anything wrong with your device."},
    {"question": "Why did a photo I took in portrait show up sideways somewhere else?", "answer": "The image file likely carries an EXIF orientation flag that some apps respect and others ignore. The actual pixel data may be stored \"sideways\" with a flag saying to rotate it for display — an app that ignores that flag will show it as stored, which looks rotated."},
    {"question": "Does this tool fix the rotation issue?", "answer": "No — it's a diagnostic tool that shows you exactly what your browser reports, so you understand why the behaviour you're seeing happens. It doesn't modify or correct anything."},
    {"question": "Are my captured comparison photos uploaded anywhere?", "answer": "No. Captures are held only in this browser tab's memory for comparison and are lost when you leave the page unless you explicitly click Download on one."},
]

TOOL = {
    "slug": "phone-camera-orientation-test",
    "meta_title": "Phone Camera Orientation Test — Portrait vs Landscape | WebcamTest",
    "meta_description": "See how your phone camera's stream dimensions and screen orientation change between portrait and landscape. Understand why photos sometimes arrive rotated.",
    "h1": "Camera Orientation Test",
    "subtitle": "Shows how captured dimensions change between portrait and landscape, and explains why photos sometimes arrive rotated.",
    "card": {
        "layout": "raw",
        "fields_html": FIELDS_HTML,
    },
    "script": SCRIPT,
    "content_html": CONTENT_HTML,
    "faq": FAQ,
}

if __name__ == "__main__":
    out_path = os.path.join(CONTENT_DIR, "phone-camera-orientation-test.json")
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(TOOL, f, indent=2, ensure_ascii=False)
    print("Wrote", out_path)
