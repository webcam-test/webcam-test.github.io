#!/usr/bin/env python3
"""Writes src/content/webcam-gif-maker-online.json -- ports the old
legacy-bootstrap-site/webcam-gif.html onto the new pipeline: article prose +
FAQ come from the legacy page (see _legacy_port.py), the card and script are
rebuilt on the new panel/teardown conventions. The legacy page loaded gifenc
from a CDN <script>; this one inlines gifenc (MIT, utilities/tool_buildout/
_gifenc.esm.js) so the tool stays fully self-contained with no third-party
script request."""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import _legacy_port as L

BASE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(L.REPO, "src", "content", "webcam-gif-maker-online.json")

with open(os.path.join(BASE, "_gifenc.esm.js"), encoding="utf-8") as f:
    GIFENC = f.read().strip()

CAMERA_ICON = '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M23 7l-7 5 7 5V7z"/><rect x="1" y="5" width="15" height="14" rx="2" ry="2"/></svg>'
IMAGE_ICON = '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect x="3" y="3" width="18" height="18" rx="2" ry="2"/><circle cx="8.5" cy="8.5" r="1.5"/><path d="m21 15-5-5L5 21" stroke-linecap="round" stroke-linejoin="round"/></svg>'
WARN_ICON = '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M12 9v4M12 17h.01M10.29 3.86 1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z" stroke-linecap="round" stroke-linejoin="round"/></svg>'
DOT_ICON = '<svg viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="9"/></svg>'

FIELDS_HTML = f'''<div class="tool-panel primary">
  <div class="panel-header">
    <span class="panel-icon" aria-hidden="true">{CAMERA_ICON}</span>
    <div><h2>Live Camera Preview</h2><p class="panel-sub">Record a short burst of frames, then turn it into a looping GIF</p></div>
  </div>
  <div class="media-preview" id="cameraPreviewWrap">
    <video id="cameraVideo" autoplay playsinline muted></video>
    <div class="media-preview-placeholder" id="cameraPlaceholder">
      {CAMERA_ICON}
      <span>Your camera feed will appear here</span>
    </div>
    <div class="capture-flash" id="recordFlash"></div>
  </div>
  <div class="media-controls">
    <button type="button" class="btn-primary" id="btnStartCamera">Start Camera</button>
    <button type="button" class="btn-secondary" id="btnStopCamera" disabled>Stop Camera</button>
    <select class="device-select" id="deviceSelect" aria-label="Select camera" disabled>
      <option value="">Default camera</option>
    </select>
  </div>
  <div class="tool-actions">
    <button type="button" class="btn-primary" id="btnCapture" disabled>Capture Frames</button>
    <select class="device-select" id="selectDuration" aria-label="GIF duration" style="max-width:160px" disabled>
      <option value="1">Duration: 1s</option>
      <option value="2" selected>Duration: 2s</option>
      <option value="3">Duration: 3s</option>
      <option value="5">Duration: 5s</option>
    </select>
    <button type="button" class="btn-secondary" id="btnCreate" disabled>Create GIF</button>
  </div>
  <div class="probe-progress" id="captureProgress" hidden><div class="probe-progress-fill" id="captureBar"></div></div>
</div>
<div class="tool-panel">
  <div class="panel-header">
    <span class="panel-icon" aria-hidden="true">{IMAGE_ICON}</span>
    <div><h2>Your GIF</h2><p class="panel-sub">Preview, check the file size, then download</p></div>
  </div>
  <div class="stat-grid">
    <div class="stat-tile"><span class="stat-value" id="statFrames">0</span><span class="stat-label">Frames</span></div>
    <div class="stat-tile"><span class="stat-value" id="statSize">320&times;240</span><span class="stat-label">Output Size</span></div>
    <div class="stat-tile"><span class="stat-value" id="statFps">10</span><span class="stat-label">Frames / Sec</span></div>
    <div class="stat-tile"><span class="stat-value" id="statFileSize">&mdash;</span><span class="stat-label">GIF File Size</span></div>
  </div>
  <div class="gif-output" id="gifOutput" hidden>
    <img id="gifPreview" alt="Your generated webcam GIF" width="320" height="240">
    <a class="btn-primary" id="gifDownload" download="webcam.gif">Download GIF</a>
  </div>
  <p class="field-note" id="gifEmpty" style="margin-bottom:0">Capture some frames, then click <strong>Create GIF</strong>. Everything is encoded in this tab &mdash; nothing is uploaded.</p>
</div>
<div class="tool-panel">
  <div class="panel-header">
    <span class="panel-icon" aria-hidden="true">{WARN_ICON}</span>
    <div><h2>Status</h2><p class="panel-sub">What to do if the camera won't start</p></div>
  </div>
  <div class="diagnostic-panel" id="diagnosticPanel">
    <div class="diagnostic-item"><span class="diag-icon">{DOT_ICON}</span><span>Click <strong>Start Camera</strong> and allow access when your browser asks.</span></div>
  </div>
</div>'''

SCRIPT = '''(function () {
  'use strict';

  /* gifenc 1.0.3 -- MIT License, Copyright (c) 2017 Matt DesLauriers.
     https://github.com/mattdesl/gifenc */
  __GIFENC__

  var video = document.getElementById('cameraVideo');
  var previewWrap = document.getElementById('cameraPreviewWrap');
  var placeholder = document.getElementById('cameraPlaceholder');
  var flashEl = document.getElementById('recordFlash');
  var deviceSelect = document.getElementById('deviceSelect');
  var btnStart = document.getElementById('btnStartCamera');
  var btnStop = document.getElementById('btnStopCamera');
  var btnCapture = document.getElementById('btnCapture');
  var btnCreate = document.getElementById('btnCreate');
  var selectDuration = document.getElementById('selectDuration');
  var captureProgress = document.getElementById('captureProgress');
  var captureBar = document.getElementById('captureBar');
  var diagnosticPanel = document.getElementById('diagnosticPanel');
  var statFrames = document.getElementById('statFrames');
  var statFileSize = document.getElementById('statFileSize');
  var gifOutput = document.getElementById('gifOutput');
  var gifPreview = document.getElementById('gifPreview');
  var gifDownload = document.getElementById('gifDownload');
  var gifEmpty = document.getElementById('gifEmpty');

  var GIF_W = 320, GIF_H = 240;
  var FRAME_RATE = 10;
  var FRAME_INTERVAL = 1000 / FRAME_RATE;
  var canvas = document.createElement('canvas');
  canvas.width = GIF_W;
  canvas.height = GIF_H;
  var ctx = canvas.getContext('2d', { willReadFrequently: true });

  var currentStream = null;
  var currentDeviceId = '';
  var starting = false;
  var capturing = false;
  var encoding = false;
  var frames = [];
  var captureTick = null;
  var gifUrl = null;

__COMMON__

  function revokeGif() {
    if (gifUrl) { URL.revokeObjectURL(gifUrl); gifUrl = null; }
  }

  function formatBytes(n) {
    if (n < 1024) return n + ' B';
    if (n < 1024 * 1024) return (n / 1024).toFixed(0) + ' KB';
    return (n / (1024 * 1024)).toFixed(2) + ' MB';
  }

  function stopCapture() {
    capturing = false;
    if (captureTick) { clearInterval(captureTick); captureTick = null; }
    captureProgress.hidden = true;
    captureBar.style.width = '0%';
  }

  // Every camera page on this site copies this stopStream()/enumerate/error
  // pattern from webcam-test-online.json (see this project's own CLAUDE.md).
  function stopStream() {
    stopCapture();
    if (currentStream) {
      currentStream.getTracks().forEach(function (t) { t.stop(); });
      currentStream = null;
    }
    video.srcObject = null;
    previewWrap.classList.remove('is-active');
    placeholder.style.display = 'flex';
    btnStop.disabled = true;
    btnCapture.disabled = true;
    selectDuration.disabled = true;
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
        btnCapture.disabled = false;
        selectDuration.disabled = false;
        setDiagnostic([{ sev: 'ok', html: '<strong>Camera is live.</strong> Pick a duration and click <strong>Capture Frames</strong>.' }]);
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

  function startCapture() {
    if (capturing || !currentStream || encoding) return;
    var duration = parseInt(selectDuration.value, 10) * 1000;
    var totalFrames = Math.floor(duration / FRAME_INTERVAL);
    frames = [];
    revokeGif();
    gifOutput.hidden = true;
    gifEmpty.hidden = false;
    statFrames.textContent = '0';
    statFileSize.textContent = '\\u2014';
    btnCreate.disabled = true;
    btnCapture.disabled = true;
    captureProgress.hidden = false;
    capturing = true;
    setDiagnostic([{ sev: '', html: 'Capturing <strong>' + selectDuration.value + ' seconds</strong> at about ' + FRAME_RATE + ' frames per second\\u2026' }]);

    captureTick = setInterval(function () {
      if (!video.videoWidth) return;
      ctx.drawImage(video, 0, 0, GIF_W, GIF_H);
      frames.push(ctx.getImageData(0, 0, GIF_W, GIF_H));
      statFrames.textContent = String(frames.length);
      captureBar.style.width = Math.min(100, Math.round(frames.length / totalFrames * 100)) + '%';
      if (frames.length >= totalFrames) {
        stopCapture();
        btnCapture.disabled = !currentStream;
        btnCreate.disabled = false;
        flashEl.classList.add('flash');
        requestAnimationFrame(function () { flashEl.classList.remove('flash'); });
        setDiagnostic([{ sev: 'ok', html: '<strong>' + frames.length + ' frames captured.</strong> Click <strong>Create GIF</strong> to encode them.' }]);
      }
    }, FRAME_INTERVAL);
  }

  function buildGif() {
    if (!frames.length || encoding) return;
    encoding = true;
    btnCreate.disabled = true;
    btnCapture.disabled = true;
    btnCreate.textContent = 'Encoding\\u2026';
    setDiagnostic([{ sev: '', html: 'Encoding the animated GIF \\u2014 this can take a moment on slower devices\\u2026' }]);

    // Deferred so the browser can paint the "Encoding..." state first.
    setTimeout(function () {
      try {
        var encoder = gifenc.GIFEncoder();
        var delay = Math.round(FRAME_INTERVAL);
        frames.forEach(function (imageData) {
          var palette = gifenc.quantize(imageData.data, 256);
          var index = gifenc.applyPalette(imageData.data, palette);
          encoder.writeFrame(index, GIF_W, GIF_H, { palette: palette, delay: delay });
        });
        encoder.finish();
        var blob = new Blob([encoder.bytes()], { type: 'image/gif' });
        revokeGif();
        gifUrl = URL.createObjectURL(blob);
        gifPreview.src = gifUrl;
        gifDownload.href = gifUrl;
        gifOutput.hidden = false;
        gifEmpty.hidden = true;
        statFileSize.textContent = formatBytes(blob.size);
        setDiagnostic([{ sev: 'ok', html: '<strong>GIF ready.</strong> Click <strong>Download GIF</strong> to save it.' }]);
      } catch (err) {
        setDiagnostic([{ sev: 'error', html: '<strong>GIF encoding failed.</strong> Capture again and retry.' }]);
      }
      encoding = false;
      btnCreate.textContent = 'Create GIF';
      btnCreate.disabled = false;
      btnCapture.disabled = !currentStream;
    }, 50);
  }

  btnStart.addEventListener('click', function () { startStream(deviceSelect.value); });
  btnStop.addEventListener('click', function () {
    stopStream();
    setDiagnostic([{ sev: '', html: 'Camera stopped. Click <strong>Start Camera</strong> to record again.' }]);
  });
  btnCapture.addEventListener('click', startCapture);
  btnCreate.addEventListener('click', buildGif);
  deviceSelect.addEventListener('change', function () {
    if (currentStream) startStream(deviceSelect.value);
  });

  // Guaranteed teardown: release the camera and the GIF object URL the
  // moment the visitor leaves this page, even if they never clicked Stop.
  window.addEventListener('pagehide', function () {
    stopStream();
    revokeGif();
  });
  document.addEventListener('visibilitychange', function () {
    if (document.visibilityState === 'hidden') stopStream();
  });

  if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) {
    setDiagnostic([{ sev: 'error', html: '<strong>Your browser doesn\\u2019t support camera access.</strong> Try the latest version of Chrome, Firefox, Edge, or Safari.' }]);
    btnStart.disabled = true;
  }
})();'''.replace("__GIFENC__", GIFENC).replace("__COMMON__", L.common_camera_js())

CONTENT_HTML = L.port_content("webcam-gif", replacements=[
    ("using the GIF.js library running in your browser", "using an open-source GIF encoder (gifenc) running in your browser"),
    ("passed directly to the GIF.js encoder", "passed directly to the gifenc encoder"),
    ("Select duration and camera", "Choose a duration and start your camera"),
    ("Choose a GIF duration from 1 to 5 seconds. 2 seconds is ideal for most reaction GIFs. Select which camera to use if you have more than one device connected.",
     "Click <strong>Start Camera</strong> and allow access, then choose a GIF duration from 1 to 5 seconds. 2 seconds is ideal for most reaction GIFs. Pick which camera to use if you have more than one connected."),
    ("Allow camera access when prompted. The live preview appears and the tool begins capturing frames at approximately 10 fps.",
     "Click <strong>Capture Frames</strong>. The tool grabs frames from the live preview at approximately 10 fps."),
    ("the <strong>Create GIF</strong> button appears.", "the <strong>Create GIF</strong> button becomes active."),
    ("Click start GIF capture", "Capture frames"),
    ("Click create GIF", "Create the GIF"),
    ("GIF file size what to expect", "GIF file size and what to expect"),
])
FAQ = L.port_faq("webcam-gif", replacements=[("GIF.js", "gifenc")])

TOOL = {
    "slug": "webcam-gif-maker-online",
    "meta_description": "Make an animated GIF from your webcam online. Capture 1 to 5 seconds of frames, create the GIF and download it — free, no upload, no software.",
    "h1": "Webcam GIF Maker",
    "subtitle": "Capture a few seconds from your camera and turn it into a looping <strong>animated GIF</strong> you can download — all processed in your browser.",
    "card": {"layout": "raw", "fields_html": FIELDS_HTML},
    "script": SCRIPT,
    "content_html": CONTENT_HTML,
    "faq": FAQ,
}

if __name__ == "__main__":
    L.write_json(OUT, TOOL)
