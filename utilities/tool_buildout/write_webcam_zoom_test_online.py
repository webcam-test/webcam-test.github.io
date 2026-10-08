#!/usr/bin/env python3
"""Writes src/content/webcam-zoom-test-online.json -- ports the old
legacy-bootstrap-site/webcam-zoom-test.html (a canvas crop-and-upscale digital
zoom, 1x-5x) onto the new pipeline. Kept: the canvas crop/upscale zoom and the
article prose/FAQ. Added on top of the old logic: a Zoom Report (visible area,
share of sensor pixels kept, effective resolution, a quality verdict) and a
read-only check for whether the camera also exposes real hardware zoom via
MediaStreamTrack.getCapabilities(). Distinct from phone-camera-zoom-test,
which drives the *hardware* zoom control on phones."""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import _legacy_port as L

OUT = os.path.join(L.REPO, "src", "content", "webcam-zoom-test-online.json")

CAMERA_ICON = '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M23 7l-7 5 7 5V7z"/><rect x="1" y="5" width="15" height="14" rx="2" ry="2"/></svg>'
ZOOM_ICON = '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="11" cy="11" r="7"/><path d="M21 21l-4.3-4.3M11 8v6M8 11h6" stroke-linecap="round" stroke-linejoin="round"/></svg>'
WARN_ICON = '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M12 9v4M12 17h.01M10.29 3.86 1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z" stroke-linecap="round" stroke-linejoin="round"/></svg>'
DOT_ICON = '<svg viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="9"/></svg>'

FIELDS_HTML = f'''<div class="tool-panel primary">
  <div class="panel-header">
    <span class="panel-icon" aria-hidden="true">{CAMERA_ICON}</span>
    <div><h2>Live Zoom Preview</h2><p class="panel-sub">Crop into the centre of your live feed, from 1&times; to 5&times;</p></div>
  </div>
  <div class="media-preview" id="cameraPreviewWrap">
    <video id="cameraVideo" autoplay playsinline muted style="position:absolute;width:1px;height:1px;opacity:0;pointer-events:none"></video>
    <canvas id="zoomCanvas" width="640" height="360" style="display:none"></canvas>
    <div class="media-preview-placeholder" id="cameraPlaceholder">
      {CAMERA_ICON}
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
  <div class="tool-field slider-field">
    <label for="zoomSlider">Digital zoom</label>
    <div class="slider-row">
      <input type="range" id="zoomSlider" min="1" max="5" value="1" step="0.1" disabled>
      <span class="slider-value" id="zoomValue">1&times;</span>
      <button type="button" class="btn-secondary" id="btnReset" disabled>Reset 1&times;</button>
    </div>
  </div>
</div>
<div class="tool-panel">
  <div class="panel-header">
    <span class="panel-icon" aria-hidden="true">{ZOOM_ICON}</span>
    <div><h2>Zoom Report</h2><p class="panel-sub">What digital zoom does to your camera's pixels</p></div>
  </div>
  <div class="stat-grid">
    <div class="stat-tile"><span class="stat-value" id="statNative">&mdash;</span><span class="stat-label">Native Resolution</span></div>
    <div class="stat-tile"><span class="stat-value" id="statVisible">&mdash;</span><span class="stat-label">Visible Area</span></div>
    <div class="stat-tile"><span class="stat-value" id="statKept">&mdash;</span><span class="stat-label">Pixels Kept</span></div>
    <div class="stat-tile"><span class="stat-value" id="statQuality">&mdash;</span><span class="stat-label">Quality</span></div>
    <div class="stat-tile"><span class="stat-value text-value" id="statHardware">&mdash;</span><span class="stat-label">Hardware Zoom</span></div>
  </div>
  <p class="field-note" style="margin-bottom:0">Digital zoom crops the centre of the frame and stretches it, so it adds no detail. Hardware (optical) zoom is a separate camera control &mdash; most webcams don't expose one to the browser.</p>
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

  var video = document.getElementById('cameraVideo');
  var canvas = document.getElementById('zoomCanvas');
  var ctx = canvas.getContext('2d');
  var previewWrap = document.getElementById('cameraPreviewWrap');
  var placeholder = document.getElementById('cameraPlaceholder');
  var deviceSelect = document.getElementById('deviceSelect');
  var btnStart = document.getElementById('btnStartCamera');
  var btnStop = document.getElementById('btnStopCamera');
  var btnReset = document.getElementById('btnReset');
  var zoomSlider = document.getElementById('zoomSlider');
  var zoomValue = document.getElementById('zoomValue');
  var diagnosticPanel = document.getElementById('diagnosticPanel');
  var statNative = document.getElementById('statNative');
  var statVisible = document.getElementById('statVisible');
  var statKept = document.getElementById('statKept');
  var statQuality = document.getElementById('statQuality');
  var statHardware = document.getElementById('statHardware');

  var currentStream = null;
  var currentDeviceId = '';
  var starting = false;
  var rafId = null;
  var zoomLevel = 1;

__COMMON__

  function qualityLabel(z) {
    if (z <= 1.05) return 'Native';
    if (z <= 1.5) return 'Good';
    if (z <= 2) return 'Fair';
    if (z <= 3) return 'Soft';
    return 'Poor';
  }

  function updateReport() {
    var vw = video.videoWidth, vh = video.videoHeight;
    zoomValue.textContent = zoomLevel.toFixed(1).replace('.0', '') + '\\u00d7';
    if (!vw || !vh) return;
    statNative.textContent = vw + '\\u00d7' + vh;
    statVisible.textContent = Math.round(vw / zoomLevel) + '\\u00d7' + Math.round(vh / zoomLevel);
    statKept.textContent = (100 / (zoomLevel * zoomLevel)).toFixed(0) + '%';
    statQuality.textContent = qualityLabel(zoomLevel);
  }

  // The old site's zoom logic, unchanged in spirit: crop the centre
  // 1/zoom of the frame and upscale it to fill the canvas every frame.
  function drawFrame() {
    rafId = requestAnimationFrame(drawFrame);
    if (!currentStream || video.readyState < 2) return;
    var vw = video.videoWidth, vh = video.videoHeight;
    if (!vw || !vh) return;
    if (canvas.width !== vw || canvas.height !== vh) {
      canvas.width = vw;
      canvas.height = vh;
    }
    var cropW = vw / zoomLevel, cropH = vh / zoomLevel;
    ctx.drawImage(video, (vw - cropW) / 2, (vh - cropH) / 2, cropW, cropH, 0, 0, vw, vh);
  }

  function describeHardwareZoom(track) {
    var caps = track.getCapabilities ? track.getCapabilities() : {};
    if (caps && caps.zoom) {
      statHardware.textContent = caps.zoom.min + '\\u00d7\\u2013' + caps.zoom.max + '\\u00d7';
      return 'This camera also exposes <strong>hardware zoom (' + caps.zoom.min + '\\u00d7\\u2013' + caps.zoom.max + '\\u00d7)</strong> to the browser. Try the <a href="/phone-camera-zoom-test">mobile camera zoom test</a> to drive it.';
    }
    statHardware.textContent = 'Not exposed';
    return 'No hardware zoom is exposed for this camera, so the slider shows <strong>digital zoom</strong> only \\u2014 which is what most webcams offer.';
  }

  // Every camera page on this site copies this stopStream()/enumerate/error
  // pattern from webcam-test-online.json (see this project's own CLAUDE.md).
  function stopStream() {
    if (rafId) { cancelAnimationFrame(rafId); rafId = null; }
    if (currentStream) {
      currentStream.getTracks().forEach(function (t) { t.stop(); });
      currentStream = null;
    }
    video.srcObject = null;
    canvas.style.display = 'none';
    previewWrap.classList.remove('is-active');
    placeholder.style.display = 'flex';
    btnStop.disabled = true;
    btnReset.disabled = true;
    zoomSlider.disabled = true;
    zoomLevel = 1;
    zoomSlider.value = 1;
    zoomValue.innerHTML = '1&times;';
    [statNative, statVisible, statKept, statQuality, statHardware].forEach(function (el) { el.textContent = '\\u2014'; });
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
        canvas.style.display = 'block';
        btnStop.disabled = false;
        btnReset.disabled = false;
        zoomSlider.disabled = false;
        updateReport();
        rafId = requestAnimationFrame(drawFrame);
        setDiagnostic([{ sev: 'ok', html: '<strong>Camera is live.</strong> Drag the slider to zoom in.' }, { sev: '', html: describeHardwareZoom(track) }]);
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
  zoomSlider.addEventListener('input', function () {
    zoomLevel = parseFloat(zoomSlider.value);
    updateReport();
  });
  btnReset.addEventListener('click', function () {
    zoomLevel = 1;
    zoomSlider.value = 1;
    updateReport();
  });
  deviceSelect.addEventListener('change', function () {
    if (currentStream) startStream(deviceSelect.value);
  });

  // Guaranteed teardown: release the camera the moment the visitor leaves
  // this page or hides the tab, even if they never clicked Stop.
  window.addEventListener('pagehide', stopStream);
  document.addEventListener('visibilitychange', function () {
    if (document.visibilityState === 'hidden') stopStream();
  });

  if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) {
    setDiagnostic([{ sev: 'error', html: '<strong>Your browser doesn\\u2019t support camera access.</strong> Try the latest version of Chrome, Firefox, Edge, or Safari.' }]);
    btnStart.disabled = true;
  }
})();'''.replace("__COMMON__", L.common_camera_js())

CONTENT_HTML = L.port_content("webcam-zoom-test", replacements=[
    ("Click start zoom test", "Start the camera"),
    ("Your browser will request camera permission. Click <strong>Allow</strong>.", "Click <strong>Start Camera</strong>. Your browser will request camera permission &mdash; click <strong>Allow</strong>."),
    ("Use the resolution tester to confirm", "Use the <a href=\"/webcam-maximum-resolution-detector\">maximum resolution detector</a> to confirm"),
    ("Run the Webcam Quality Test to get", "Run the <a href=\"/webcam-sharpness-focus-test\">sharpness and focus test</a> to get"),
    ("Digital zoom vs optical zoom what's the difference?", "Digital zoom vs optical zoom explained"),
    ("Troubleshooting common issues with the zoom test", "Troubleshooting common zoom test issues"),
])
FAQ = L.port_faq("webcam-zoom-test")

TOOL = {
    "slug": "webcam-zoom-test-online",
    "meta_description": "Test your webcam's digital zoom online. Slide from 1x to 5x on your live feed and see how much detail each zoom level keeps — free, no upload.",
    "h1": "Webcam Zoom Test",
    "subtitle": "Move the slider to preview <strong>digital zoom</strong> from 1&times; to 5&times; on your live camera feed and see how much quality each level costs.",
    "card": {"layout": "raw", "fields_html": FIELDS_HTML},
    "script": SCRIPT,
    "content_html": CONTENT_HTML,
    "faq": FAQ,
}

if __name__ == "__main__":
    L.write_json(OUT, TOOL)
