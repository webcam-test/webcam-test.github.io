#!/usr/bin/env python3
"""Writes src/content/phone-camera-zoom-test.json."""
import json
import os

BASE = os.path.dirname(os.path.abspath(__file__))
CONTENT_DIR = os.path.normpath(os.path.join(BASE, "..", "..", "src", "content"))

CAMERA_ICON = '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M23 7l-7 5 7 5V7z"/><rect x="1" y="5" width="15" height="14" rx="2" ry="2"/></svg>'
ZOOM_ICON = '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="11" cy="11" r="8"/><path d="M21 21l-4.35-4.35M11 8v6M8 11h6" stroke-linecap="round"/></svg>'
INFO_ICON = '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="10"/><path d="M12 16v-4M12 8h.01" stroke-linecap="round"/></svg>'
DOT_ICON = '<svg viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="9"/></svg>'
PLACEHOLDER_ICON = '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5"><path d="M23 7l-7 5 7 5V7z"/><rect x="1" y="5" width="15" height="14" rx="2" ry="2"/></svg>'

FIELDS_HTML = f'''<div class="tool-panel primary">
  <div class="panel-header">
    <span class="panel-icon">{CAMERA_ICON}</span>
    <div><h2>Camera Zoom Test</h2><p class="panel-sub">Tests optical/digital zoom range where your browser exposes it</p></div>
  </div>
  <div class="media-preview" id="cameraPreviewWrap">
    <video id="cameraVideo" autoplay playsinline muted></video>
    <div class="media-preview-placeholder" id="cameraPlaceholder">
      {PLACEHOLDER_ICON}
      <span>Your camera feed will appear here</span>
    </div>
  </div>
  <div class="media-controls" style="margin-top:1rem">
    <button type="button" class="btn-primary" id="btnStartCamera">Start Camera</button>
    <button type="button" class="btn-secondary" id="btnStopCamera" disabled>Stop Camera</button>
    <select class="device-select" id="deviceSelect" aria-label="Select camera" disabled>
      <option value="">Default camera</option>
    </select>
  </div>
  <div class="tool-field slider-field" style="margin-top:1rem">
    <label for="zoomSlider">Zoom</label>
    <div class="slider-row">
      <input type="range" id="zoomSlider" min="0" max="1" value="0" step="0.01" disabled>
      <span class="slider-value" id="zoomValue">—</span>
    </div>
  </div>
  <div class="diagnostic-panel" id="diagnosticPanel" style="margin-top:1rem">
    <div class="diagnostic-item" id="diagDefault"><span class="diag-icon">{DOT_ICON}</span><span>Click <strong>Start Camera</strong> and allow access when your browser asks.</span></div>
  </div>
</div>
<div class="tool-panel">
  <div class="panel-header">
    <span class="panel-icon">{ZOOM_ICON}</span>
    <div><h2>Reported Range</h2></div>
  </div>
  <div class="stat-grid">
    <div class="stat-tile"><span class="stat-value" id="statMin">—</span><span class="stat-label">Minimum</span></div>
    <div class="stat-tile"><span class="stat-value" id="statMax">—</span><span class="stat-label">Maximum</span></div>
    <div class="stat-tile"><span class="stat-value" id="statStep">—</span><span class="stat-label">Step</span></div>
  </div>
  <p class="field-note">These are whatever your browser and camera driver report as the supported range — not necessarily the lens's full optical range.</p>
</div>
<div class="tool-panel">
  <div class="panel-header">
    <span class="panel-icon">{INFO_ICON}</span>
    <div><h2>Browser Support Is Limited</h2></div>
  </div>
  <p class="field-note" style="margin-top:0">Programmatic zoom control is only exposed by some browsers — mostly Chromium-based browsers on Android — and only when the camera and driver declare the capability at all. It's absent entirely on iOS Safari, and many desktop webcams don't expose it either since most don't have a motorised or stepped zoom to control.</p>
  <p class="field-note" style="margin-bottom:0">If a multi-lens phone switches to a different physical lens partway through its zoom range (common around 2x on phones with a dedicated telephoto lens), you may notice a visible jump or brief refocus in the preview at that point — that's the phone switching lenses, not a bug in this test.</p>
</div>'''

SCRIPT = r'''(function () {
  'use strict';

  var video = document.getElementById('cameraVideo');
  var previewWrap = document.getElementById('cameraPreviewWrap');
  var placeholder = document.getElementById('cameraPlaceholder');
  var deviceSelect = document.getElementById('deviceSelect');
  var btnStart = document.getElementById('btnStartCamera');
  var btnStop = document.getElementById('btnStopCamera');
  var zoomSlider = document.getElementById('zoomSlider');
  var zoomValue = document.getElementById('zoomValue');
  var diagnosticPanel = document.getElementById('diagnosticPanel');
  var statMin = document.getElementById('statMin');
  var statMax = document.getElementById('statMax');
  var statStep = document.getElementById('statStep');

  var currentStream = null;
  var starting = false;
  var currentTrack = null;

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

  // Same stopStream()/describeError()/populateDeviceSelect() pattern as
  // webcam-test-online's own script (see this project's CLAUDE.md -- every
  // camera tool copies this teardown block rather than importing a shared file).
  function stopStream() {
    if (currentStream) {
      currentStream.getTracks().forEach(function (t) { t.stop(); });
      currentStream = null;
    }
    currentTrack = null;
    video.srcObject = null;
    previewWrap.classList.remove('is-active');
    placeholder.style.display = 'flex';
    btnStop.disabled = true;
    zoomSlider.disabled = true;
    zoomValue.textContent = '—';
    statMin.textContent = '—';
    statMax.textContent = '—';
    statStep.textContent = '—';
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
        currentTrack = stream.getVideoTracks()[0];
        video.srcObject = stream;
        placeholder.style.display = 'none';
        previewWrap.classList.add('is-active');
        return video.play().catch(function () {}).then(function () { return stream; });
      })
      .then(function (stream) {
        var track = currentTrack;
        var settings = track.getSettings ? track.getSettings() : {};
        var caps = track.getCapabilities ? (function () { try { return track.getCapabilities(); } catch (e) { return null; } })() : null;
        btnStop.disabled = false;

        // Zoom capability is exposed only by some Chromium-based browsers,
        // mostly on Android, and only when the camera/driver declares it --
        // absent entirely on iOS Safari, per this tool's own spec note. Show
        // a clear unsupported state rather than a dead slider.
        if (caps && caps.zoom) {
          zoomSlider.min = caps.zoom.min;
          zoomSlider.max = caps.zoom.max;
          zoomSlider.step = caps.zoom.step || 0.1;
          zoomSlider.value = settings.zoom || caps.zoom.min;
          zoomSlider.disabled = false;
          zoomValue.textContent = String(zoomSlider.value) + 'x';
          statMin.textContent = caps.zoom.min + 'x';
          statMax.textContent = caps.zoom.max + 'x';
          statStep.textContent = String(caps.zoom.step || 'n/a');
          setDiagnostic([{ sev: 'ok', html: '<strong>Zoom control is available.</strong> Drag the slider to zoom in and out.' }]);
        } else {
          zoomSlider.disabled = true;
          setDiagnostic([{ sev: 'warn', html: '<strong>This browser or camera doesn’t expose zoom control.</strong> This is common — zoom is only available on some Chromium-based Android browsers when the camera declares the capability. It\'s absent entirely on iOS Safari and on most desktop webcams.' }]);
        }

        return navigator.mediaDevices.enumerateDevices().then(function (devices) {
          populateDeviceSelect(devices, settings.deviceId);
        });
      })
      .catch(function (err) { setDiagnostic([describeError(err)]); stopStream(); })
      .finally(function () { starting = false; btnStart.disabled = false; });
  }

  zoomSlider.addEventListener('input', function () {
    if (!currentTrack) return;
    var value = parseFloat(zoomSlider.value);
    zoomValue.textContent = value.toFixed(2) + 'x';
    currentTrack.applyConstraints({ advanced: [{ zoom: value }] }).catch(function () {});
  });

  btnStart.addEventListener('click', function () { startStream(deviceSelect.value); });
  btnStop.addEventListener('click', function () {
    stopStream();
    setDiagnostic([{ sev: '', html: 'Camera stopped.' }]);
  });
  deviceSelect.addEventListener('change', function () { if (currentStream) startStream(deviceSelect.value); });

  window.addEventListener('pagehide', stopStream);
  document.addEventListener('visibilitychange', function () {
    if (document.visibilityState === 'hidden') stopStream();
  });

  if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) {
    setDiagnostic([{ sev: 'error', html: '<strong>Your browser doesn’t support camera access.</strong>' }]);
    btnStart.disabled = true;
  }
})();'''

CONTENT_HTML = '''<p>This tool tests whether your browser can control your camera's zoom directly, and if so, reports the exact range and step size your camera and driver report supporting.</p>
<h2>Why zoom control is so rarely available</h2>
<p>Programmatic zoom is a genuinely narrow browser feature: it only works on some Chromium-based browsers, predominantly on Android, and only when the underlying camera and its driver explicitly declare a zoom capability through the browser's media API. iOS Safari doesn't expose it at all, on any iPhone, and most desktop webcams don't either — many simply don't have a motorised or digitally-stepped zoom mechanism for a browser to control in the first place. If this test reports zoom as unsupported, that's the expected outcome for the large majority of devices, not a fault with your camera.</p>
<h2>What the reported range actually means</h2>
<p>The minimum, maximum and step values shown are whatever the browser's media API reports as supported — not necessarily your phone's full advertised optical zoom range. Some phones only expose part of their zoom capability to web pages, reserving the rest for their native camera app.</p>
<h2>Lens switching on multi-camera phones</h2>
<p>Phones with a dedicated telephoto lens alongside their main camera will sometimes physically switch to that second lens partway through the zoom range — commonly somewhere around 2x. If you notice a brief refocus or a visible jump in the preview at a specific zoom level, that's very likely the lens switch happening, not an error.</p>'''

FAQ = [
    {"question": "Why is the zoom slider disabled on my phone?", "answer": "Zoom control through the browser is only available on some Chromium-based Android browsers, and only when the camera declares the capability. It's completely absent on iOS Safari and on most desktop webcams, so a disabled slider there is expected, not a bug."},
    {"question": "The reported maximum zoom seems lower than my phone's camera app allows — why?", "answer": "Some phones only expose part of their full zoom range to web pages through the browser's media API, keeping the rest reserved for their own native camera app. The range shown here is what the browser itself reports as controllable."},
    {"question": "Why did the image jump slightly at a specific zoom level?", "answer": "On phones with more than one rear lens (a main lens plus a telephoto lens, for example), the camera sometimes switches physically to the other lens at a certain zoom level — often around 2x. A brief refocus or visible jump there is that lens switch, not a fault."},
    {"question": "Does this change my phone's actual camera app zoom setting?", "answer": "No — this only controls the browser's live preview on this page. It has no effect on your phone's native camera app or its settings."},
]

TOOL = {
    "slug": "phone-camera-zoom-test",
    "meta_title": "Phone Camera Zoom Test — Check Zoom Range Online | WebcamTest",
    "meta_description": "Test your phone camera's zoom range directly in the browser. Reports minimum, maximum and step, with a clear explanation when zoom control isn't supported.",
    "h1": "Camera Zoom Test",
    "subtitle": "Tests optical/digital zoom range where your browser exposes it, reporting minimum, maximum and step.",
    "card": {
        "layout": "raw",
        "fields_html": FIELDS_HTML,
    },
    "script": SCRIPT,
    "content_html": CONTENT_HTML,
    "faq": FAQ,
}

if __name__ == "__main__":
    out_path = os.path.join(CONTENT_DIR, "phone-camera-zoom-test.json")
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(TOOL, f, indent=2, ensure_ascii=False)
    print("Wrote", out_path)
