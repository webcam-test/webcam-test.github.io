#!/usr/bin/env python3
"""Writes src/content/webcam-live-filter-preview.json."""
import json
import os

BASE = os.path.dirname(os.path.abspath(__file__))
CONTENT_DIR = os.path.normpath(os.path.join(BASE, "..", "..", "src", "content"))

CAMERA_ICON = '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M23 7l-7 5 7 5V7z"/><rect x="1" y="5" width="15" height="14" rx="2" ry="2"/></svg>'
SLIDER_ICON = '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M4 21v-7M4 10V3M12 21v-9M12 8V3M20 21v-5M20 12V3M1 14h6M9 8h6M17 16h6" stroke-linecap="round"/></svg>'
INFO_ICON = '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="10"/><path d="M12 16v-4M12 8h.01" stroke-linecap="round"/></svg>'
DOWNLOAD_ICON = '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4M7 10l5 5 5-5M12 15V3" stroke-linecap="round" stroke-linejoin="round"/></svg>'
DOT_ICON = '<svg viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="9"/></svg>'
PLACEHOLDER_ICON = '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5"><path d="M23 7l-7 5 7 5V7z"/><rect x="1" y="5" width="15" height="14" rx="2" ry="2"/></svg>'

FIELDS_HTML = f'''<div class="tool-panel primary">
  <div class="panel-header">
    <span class="panel-icon">{CAMERA_ICON}</span>
    <div><h2>Live Filter Preview</h2><p class="panel-sub">Preview-only — nothing here changes your actual camera or transmitted feed</p></div>
  </div>
  <div class="dual-preview">
    <div class="media-preview" id="beforeWrap">
      <span class="preview-label">Before</span>
      <video id="beforeVideo" autoplay playsinline muted></video>
      <div class="media-preview-placeholder" id="cameraPlaceholder">
        {PLACEHOLDER_ICON}
        <span>Your camera feed will appear here</span>
      </div>
    </div>
    <div class="media-preview" id="afterWrap">
      <span class="preview-label">After</span>
      <video id="afterVideo" autoplay playsinline muted></video>
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
  <div class="diagnostic-panel" id="diagnosticPanel" style="margin-top:1rem">
    <div class="diagnostic-item" id="diagDefault"><span class="diag-icon">{DOT_ICON}</span><span>Click <strong>Start Camera</strong> and allow access when your browser asks.</span></div>
  </div>
</div>
<div class="tool-panel">
  <div class="panel-header">
    <span class="panel-icon">{SLIDER_ICON}</span>
    <div><h2>Adjustments</h2></div>
  </div>
  <div class="tool-field slider-field">
    <label for="brightnessSlider">Brightness</label>
    <div class="slider-row">
      <input type="range" id="brightnessSlider" min="50" max="150" value="100">
      <span class="slider-value" id="brightnessValue">100%</span>
    </div>
  </div>
  <div class="tool-field slider-field">
    <label for="contrastSlider">Contrast</label>
    <div class="slider-row">
      <input type="range" id="contrastSlider" min="50" max="150" value="100">
      <span class="slider-value" id="contrastValue">100%</span>
    </div>
  </div>
  <div class="tool-field slider-field">
    <label for="saturationSlider">Saturation</label>
    <div class="slider-row">
      <input type="range" id="saturationSlider" min="0" max="200" value="100">
      <span class="slider-value" id="saturationValue">100%</span>
    </div>
  </div>
  <div class="tool-field slider-field" style="margin-bottom:0">
    <label for="blurSlider">Blur</label>
    <div class="slider-row">
      <input type="range" id="blurSlider" min="0" max="10" value="0" step="0.5">
      <span class="slider-value" id="blurValue">0px</span>
    </div>
  </div>
  <button type="button" class="btn-secondary" id="btnReset" style="width:100%;margin-top:1rem">Reset to Defaults</button>
</div>
<div class="tool-panel">
  <div class="panel-header">
    <span class="panel-icon">{INFO_ICON}</span>
    <div><h2>Preview Only</h2></div>
  </div>
  <p class="field-note" style="margin-top:0">These adjustments are applied only to this page's preview — they do <strong>not</strong> change your camera driver settings or what's actually transmitted in a call. Use this to find settings you like, then replicate brightness/contrast in your camera app or OS camera settings, and colour/saturation adjustments in your call software's video settings if it offers them.</p>
  <button type="button" class="btn-secondary btn-icon-text" id="btnDownload" disabled style="width:100%">{DOWNLOAD_ICON} Download Filtered Photo</button>
</div>'''

SCRIPT = r'''(function () {
  'use strict';

  var beforeVideo = document.getElementById('beforeVideo');
  var afterVideo = document.getElementById('afterVideo');
  var beforeWrap = document.getElementById('beforeWrap');
  var afterWrap = document.getElementById('afterWrap');
  var placeholder = document.getElementById('cameraPlaceholder');
  var canvas = document.getElementById('captureCanvas');
  var deviceSelect = document.getElementById('deviceSelect');
  var btnStart = document.getElementById('btnStartCamera');
  var btnStop = document.getElementById('btnStopCamera');
  var btnReset = document.getElementById('btnReset');
  var btnDownload = document.getElementById('btnDownload');
  var diagnosticPanel = document.getElementById('diagnosticPanel');

  var brightnessSlider = document.getElementById('brightnessSlider');
  var contrastSlider = document.getElementById('contrastSlider');
  var saturationSlider = document.getElementById('saturationSlider');
  var blurSlider = document.getElementById('blurSlider');
  var brightnessValue = document.getElementById('brightnessValue');
  var contrastValue = document.getElementById('contrastValue');
  var saturationValue = document.getElementById('saturationValue');
  var blurValue = document.getElementById('blurValue');

  var currentStream = null;
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

  // CSS filter functions are GPU-composited and cost nothing -- there's no
  // reason to touch canvas for the live preview itself, per this tool's own
  // spec note. Canvas only comes in for the one-off download capture below.
  function currentFilterString() {
    return 'brightness(' + brightnessSlider.value + '%) ' +
      'contrast(' + contrastSlider.value + '%) ' +
      'saturate(' + saturationSlider.value + '%) ' +
      'blur(' + blurSlider.value + 'px)';
  }

  function applyFilter() {
    afterVideo.style.filter = currentFilterString();
    brightnessValue.textContent = brightnessSlider.value + '%';
    contrastValue.textContent = contrastSlider.value + '%';
    saturationValue.textContent = saturationSlider.value + '%';
    blurValue.textContent = blurSlider.value + 'px';
  }

  // Same stopStream()/describeError()/populateDeviceSelect() pattern as
  // webcam-test-online's own script (see this project's CLAUDE.md -- every
  // camera tool copies this teardown block rather than importing a shared file).
  function stopStream() {
    if (currentStream) {
      currentStream.getTracks().forEach(function (t) { t.stop(); });
      currentStream = null;
    }
    beforeVideo.srcObject = null;
    afterVideo.srcObject = null;
    beforeWrap.classList.remove('is-active');
    afterWrap.classList.remove('is-active');
    placeholder.style.display = 'flex';
    btnStop.disabled = true;
    btnDownload.disabled = true;
  }

  function describeError(err) {
    switch (err && err.name) {
      case 'NotAllowedError':
      case 'PermissionDeniedError':
        return { sev: 'error', html: '<strong>Camera access was blocked.</strong> Allow access from your browser’s address-bar icon or site settings, then try again.' };
      case 'NotFoundError':
      case 'DevicesNotFoundError':
        return { sev: 'error', html: '<strong>No camera was detected.</strong> Connect a webcam and reload this page.' };
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

  // Single MediaStream feeding both video elements -- opening two camera
  // streams would fail on most devices, same pattern as
  // webcam-mirror-vs-natural-view-test's own script.
  function startStream(deviceId) {
    if (starting) return;
    starting = true;
    stopStream();
    setDiagnostic([{ sev: '', html: 'Requesting camera access…' }]);
    btnStart.disabled = true;

    navigator.mediaDevices.getUserMedia({ video: deviceId ? { deviceId: { exact: deviceId } } : true, audio: false })
      .then(function (stream) {
        currentStream = stream;
        beforeVideo.srcObject = stream;
        afterVideo.srcObject = stream;
        placeholder.style.display = 'none';
        beforeWrap.classList.add('is-active');
        afterWrap.classList.add('is-active');
        applyFilter();
        return Promise.all([beforeVideo.play().catch(function () {}), afterVideo.play().catch(function () {})]).then(function () { return stream; });
      })
      .then(function (stream) {
        var track = stream.getVideoTracks()[0];
        var settings = track.getSettings ? track.getSettings() : {};
        btnStop.disabled = false;
        btnDownload.disabled = false;
        setDiagnostic([{ sev: 'ok', html: '<strong>Camera is live.</strong> Adjust the sliders and compare the before/after preview.' }]);
        return navigator.mediaDevices.enumerateDevices().then(function (devices) {
          populateDeviceSelect(devices, settings.deviceId);
        });
      })
      .catch(function (err) { setDiagnostic([describeError(err)]); stopStream(); })
      .finally(function () { starting = false; btnStart.disabled = false; });
  }

  function downloadFilteredPhoto() {
    if (!currentStream || !afterVideo.videoWidth) return;
    canvas.width = afterVideo.videoWidth;
    canvas.height = afterVideo.videoHeight;
    var ctx2d = canvas.getContext('2d');
    // Canvas 2D's own filter property accepts the same CSS filter function
    // syntax, so the exact on-screen adjustment gets baked into the capture.
    ctx2d.filter = currentFilterString();
    ctx2d.drawImage(afterVideo, 0, 0, canvas.width, canvas.height);
    var url = canvas.toDataURL('image/jpeg', 0.92);
    var a = document.createElement('a');
    a.href = url;
    a.download = 'filtered-webcam-photo.jpg';
    document.body.appendChild(a);
    a.click();
    a.remove();
  }

  [brightnessSlider, contrastSlider, saturationSlider, blurSlider].forEach(function (slider) {
    slider.addEventListener('input', applyFilter);
  });

  btnReset.addEventListener('click', function () {
    brightnessSlider.value = 100;
    contrastSlider.value = 100;
    saturationSlider.value = 100;
    blurSlider.value = 0;
    applyFilter();
  });

  btnStart.addEventListener('click', function () { startStream(deviceSelect.value); });
  btnStop.addEventListener('click', function () {
    stopStream();
    setDiagnostic([{ sev: '', html: 'Camera stopped.' }]);
  });
  deviceSelect.addEventListener('change', function () { if (currentStream) startStream(deviceSelect.value); });
  btnDownload.addEventListener('click', downloadFilteredPhoto);

  window.addEventListener('pagehide', stopStream);
  document.addEventListener('visibilitychange', function () {
    if (document.visibilityState === 'hidden') stopStream();
  });

  applyFilter();

  if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) {
    setDiagnostic([{ sev: 'error', html: '<strong>Your browser doesn’t support camera access.</strong>' }]);
    btnStart.disabled = true;
  }
})();'''

CONTENT_HTML = '''<p>This tool lets you preview brightness, contrast, saturation and blur adjustments on your live camera feed side by side with the unedited original, so you can judge what actually looks better before changing anything in your real camera settings or call software.</p>
<h2>This is a preview, not a real correction</h2>
<p>Nothing here touches your camera driver, your operating system's camera settings, or the actual video stream your call software would transmit — these adjustments exist only in this browser tab, applied to what you see on screen. If you find a combination you like, the useful next step is replicating it: brightness and contrast usually live in your camera app or OS camera settings, while saturation and other colour adjustments are sometimes available in your call software's own video settings, if it offers them at all.</p>
<h2>Why this uses CSS filters instead of processing each frame</h2>
<p>Brightness, contrast, saturation and blur are all applied using the browser's built-in CSS filter functions, which run on the GPU essentially for free — there's no per-frame image processing happening in JavaScript, which keeps the preview smooth even on modest hardware. The trade-off is that these are display-only effects, which is exactly why they can't affect your transmitted stream.</p>
<h2>Downloading a filtered still</h2>
<p>The Download Filtered Photo button captures a single frame with your current adjustments baked in as an actual image file, unlike the live preview — useful for judging a specific look, or for sharing an example of a setting combination you found.</p>'''

FAQ = [
    {"question": "Will these settings apply to my actual video calls?", "answer": "No. These adjustments are a browser-only preview on this page and have no effect on your camera driver or on what any call software transmits. Use this to find a look you like, then adjust the equivalent settings in your camera app or call software directly."},
    {"question": "Why is there a separate \"before\" and \"after\" preview?", "answer": "Comparing side by side is far more reliable than judging a single filtered image against memory of what it looked like before — small brightness or saturation changes are easy to misjudge without a direct reference next to them."},
    {"question": "Can I download a photo with these filters applied?", "answer": "Yes — the Download Filtered Photo button captures a single frame with your exact current adjustments baked into the image file, so you can save or share a specific look rather than only viewing it live."},
    {"question": "Does adjusting blur or saturation cost more CPU than a plain preview?", "answer": "No — all four adjustments use the browser's built-in CSS filter functions, which are handled by the GPU rather than processed frame-by-frame in JavaScript, so the preview stays smooth regardless of which sliders you move."},
]

TOOL = {
    "slug": "webcam-live-filter-preview",
    "meta_title": "Webcam Live Filter Preview — Brightness, Contrast & Colour | WebcamTest",
    "meta_description": "Preview brightness, contrast, saturation and blur adjustments on your live webcam feed with a before/after split view. Preview-only — download a filtered still photo.",
    "h1": "Live Filter Preview",
    "subtitle": "Adjust brightness, contrast, saturation and blur on your live feed and compare before/after — preview only, download a filtered still.",
    "card": {
        "layout": "raw",
        "fields_html": FIELDS_HTML,
    },
    "script": SCRIPT,
    "content_html": CONTENT_HTML,
    "faq": FAQ,
}

if __name__ == "__main__":
    out_path = os.path.join(CONTENT_DIR, "webcam-live-filter-preview.json")
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(TOOL, f, indent=2, ensure_ascii=False)
    print("Wrote", out_path)
