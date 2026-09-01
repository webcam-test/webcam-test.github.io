#!/usr/bin/env python3
"""Writes src/content/webcam-camera-information-report.json."""
import json
import os

BASE = os.path.dirname(os.path.abspath(__file__))
CONTENT_DIR = os.path.normpath(os.path.join(BASE, "..", "..", "src", "content"))

CAMERA_ICON = '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M23 7l-7 5 7 5V7z"/><rect x="1" y="5" width="15" height="14" rx="2" ry="2"/></svg>'
TABLE_ICON = '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect x="3" y="3" width="18" height="18" rx="2"/><path d="M3 9h18M3 15h18M9 3v18"/></svg>'
DOWNLOAD_ICON = '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4M7 10l5 5 5-5M12 15V3" stroke-linecap="round" stroke-linejoin="round"/></svg>'
DOT_ICON = '<svg viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="9"/></svg>'
PLACEHOLDER_ICON = '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5"><path d="M23 7l-7 5 7 5V7z"/><rect x="1" y="5" width="15" height="14" rx="2" ry="2"/></svg>'

FIELDS_HTML = f'''<div class="tool-panel primary">
  <div class="panel-header">
    <span class="panel-icon">{CAMERA_ICON}</span>
    <div><h2>Camera Preview</h2><p class="panel-sub">Start your camera, then capture a frame to fill in the image metrics below</p></div>
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
    <button type="button" class="btn-primary" id="btnStartCamera">Start Camera</button>
    <button type="button" class="btn-secondary" id="btnStopCamera" disabled>Stop Camera</button>
    <button type="button" class="btn-secondary" id="btnCaptureFrame" disabled>Analyse a Frame</button>
    <select class="device-select" id="deviceSelect" aria-label="Select camera" disabled>
      <option value="">Default camera</option>
    </select>
  </div>
  <div class="diagnostic-panel" id="diagnosticPanel" style="margin-top:1rem">
    <div class="diagnostic-item" id="diagDefault"><span class="diag-icon">{DOT_ICON}</span><span>Click <strong>Start Camera</strong>, then <strong>Analyse a Frame</strong> to fill in the image metrics section below.</span></div>
  </div>
</div>
<div class="tool-panel span-2">
  <div class="panel-header">
    <span class="panel-icon">{TABLE_ICON}</span>
    <div><h2>Full Camera Report</h2><p class="panel-sub">Hardware settings from getSettings()/getCapabilities(), plus image metrics from a captured frame</p></div>
  </div>
  <div class="info-section-label">Hardware</div>
  <div class="info-table" id="hardwareTable">
    <div class="info-row"><span class="info-label">Device Name</span><span class="info-value" id="infoDeviceName">—</span></div>
    <div class="info-row"><span class="info-label">Resolution</span><span class="info-value" id="infoResolution">—</span></div>
    <div class="info-row"><span class="info-label">Megapixels</span><span class="info-value" id="infoMegapixels">—</span></div>
    <div class="info-row"><span class="info-label">Aspect Ratio</span><span class="info-value" id="infoAspectRatio">—</span></div>
    <div class="info-row"><span class="info-label">Frame Rate</span><span class="info-value" id="infoFrameRate">—</span></div>
    <div class="info-row"><span class="info-label">Facing Mode</span><span class="info-value" id="infoFacingMode">—</span></div>
    <div class="info-row"><span class="info-label">Focus Mode</span><span class="info-value" id="infoFocusMode">—</span></div>
    <div class="info-row"><span class="info-label">Resolution Range (min–max)</span><span class="info-value" id="infoResolutionRange">—</span></div>
    <div class="info-row"><span class="info-label">Frame Rate Range (min–max)</span><span class="info-value" id="infoFrameRateRange">—</span></div>
    <div class="info-row"><span class="info-label">Device ID</span><span class="info-value" id="infoDeviceId" style="font-size:.72rem;word-break:break-all">—</span></div>
  </div>
  <div class="info-section-label">Image Metrics <span style="font-weight:400;text-transform:none;letter-spacing:0">(from the last captured frame)</span></div>
  <div class="info-table" id="imageTable">
    <div class="info-row"><span class="info-label">Average Brightness</span><span class="info-value" id="infoBrightness">—</span></div>
    <div class="info-row"><span class="info-label">Average Saturation</span><span class="info-value" id="infoSaturation">—</span></div>
    <div class="info-row"><span class="info-label">Average Hue</span><span class="info-value" id="infoHue">—</span></div>
    <div class="info-row"><span class="info-label">Average RGB</span><span class="info-value" id="infoRgb">—</span></div>
    <div class="info-row"><span class="info-label">Distinct Colours Sampled</span><span class="info-value" id="infoColourCount">—</span></div>
  </div>
  <div class="tool-actions" style="margin-top:1rem">
    <button type="button" class="btn-secondary btn-icon-text" id="btnCopyReport">{DOWNLOAD_ICON} Copy as Text</button>
    <button type="button" class="btn-secondary btn-icon-text" id="btnDownloadReport">{DOWNLOAD_ICON} Download as JSON</button>
  </div>
  <p class="field-note">Useful for pasting into a support ticket or bug report. Nothing here is sent anywhere automatically.</p>
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
  var btnCapture = document.getElementById('btnCaptureFrame');
  var btnCopy = document.getElementById('btnCopyReport');
  var btnDownload = document.getElementById('btnDownloadReport');
  var diagnosticPanel = document.getElementById('diagnosticPanel');

  var ids = ['DeviceName', 'Resolution', 'Megapixels', 'AspectRatio', 'FrameRate', 'FacingMode', 'FocusMode', 'ResolutionRange', 'FrameRateRange', 'DeviceId', 'Brightness', 'Saturation', 'Hue', 'Rgb', 'ColourCount'];
  var fields = {};
  ids.forEach(function (id) { fields[id] = document.getElementById('info' + id); });

  var currentStream = null;
  var starting = false;
  var lastReport = null;

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

  function setField(id, value, unsupported) {
    var el = fields[id];
    if (!el) return;
    el.textContent = value;
    el.classList.toggle('unsupported', !!unsupported);
  }

  function gcd(a, b) { return b === 0 ? a : gcd(b, a % b); }

  function resetHardwareFields() {
    ids.slice(0, 10).forEach(function (id) { setField(id, '—'); });
  }
  function resetImageFields() {
    ids.slice(10).forEach(function (id) { setField(id, '—'); });
  }

  // Same stopStream()/enumerate/error pattern as webcam-test-online's own
  // script (see this project's CLAUDE.md — every camera tool copies this
  // teardown block rather than importing a shared file).
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
    resetHardwareFields();
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

  function fillHardwareReport(track) {
    var settings = track.getSettings ? track.getSettings() : {};
    var caps = track.getCapabilities ? (function () { try { return track.getCapabilities(); } catch (e) { return null; } })() : null;

    setField('DeviceName', track.label || 'Camera');
    if (settings.width && settings.height) {
      setField('Resolution', settings.width + '×' + settings.height);
      var mp = (settings.width * settings.height / 1e6).toFixed(2) + ' MP';
      setField('Megapixels', mp);
      var g = gcd(settings.width, settings.height) || 1;
      setField('AspectRatio', (settings.width / g) + ':' + (settings.height / g));
    } else {
      setField('Resolution', 'Not reported', true);
      setField('Megapixels', 'Not reported', true);
      setField('AspectRatio', 'Not reported', true);
    }
    setField('FrameRate', settings.frameRate ? (Math.round(settings.frameRate * 10) / 10 + ' fps') : 'Not reported', !settings.frameRate);
    setField('FacingMode', settings.facingMode || 'Not reported', !settings.facingMode);

    if (caps) {
      setField('FocusMode', (caps.focusMode && caps.focusMode.length) ? caps.focusMode.join(', ') : 'Not reported', !(caps.focusMode && caps.focusMode.length));
      if (caps.width && caps.height) {
        setField('ResolutionRange', caps.width.min + '×' + caps.height.min + ' – ' + caps.width.max + '×' + caps.height.max);
      } else {
        setField('ResolutionRange', 'Not reported', true);
      }
      if (caps.frameRate) {
        setField('FrameRateRange', (Math.round(caps.frameRate.min * 10) / 10) + ' – ' + (Math.round(caps.frameRate.max * 10) / 10) + ' fps');
      } else {
        setField('FrameRateRange', 'Not reported', true);
      }
    } else {
      // Firefox doesn't implement getCapabilities() at all -- degrade
      // gracefully rather than treating this as a failure (per this
      // project's spec: "design for partial data").
      setField('FocusMode', 'Unsupported in this browser', true);
      setField('ResolutionRange', 'Unsupported in this browser', true);
      setField('FrameRateRange', 'Unsupported in this browser', true);
    }
    setField('DeviceId', settings.deviceId || 'Not reported', !settings.deviceId);
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
        fillHardwareReport(track);
        btnStop.disabled = false;
        btnCapture.disabled = false;
        setDiagnostic([{ sev: 'ok', html: '<strong>Camera is live.</strong> Click <strong>Analyse a Frame</strong> to fill in the image metrics below.' }]);
        var settings = track.getSettings ? track.getSettings() : {};
        return navigator.mediaDevices.enumerateDevices().then(function (devices) {
          populateDeviceSelect(devices, settings.deviceId);
        });
      })
      .catch(function (err) { setDiagnostic([describeError(err)]); })
      .finally(function () { starting = false; btnStart.disabled = false; });
  }

  function analyseFrame() {
    if (!currentStream) return;
    var track = currentStream.getVideoTracks()[0];
    var settings = track.getSettings ? track.getSettings() : {};
    var w = settings.width || video.videoWidth;
    var h = settings.height || video.videoHeight;
    if (!w || !h) return;

    // Downsample before analysing -- a full 4K frame's pixel loop would be
    // slow and the extra resolution adds nothing to an average-colour /
    // brightness estimate. 160px on the long edge is plenty.
    var scale = Math.min(1, 160 / Math.max(w, h));
    var sw = Math.max(1, Math.round(w * scale));
    var sh = Math.max(1, Math.round(h * scale));
    canvas.width = sw;
    canvas.height = sh;
    var ctx = canvas.getContext('2d');
    ctx.drawImage(video, 0, 0, sw, sh);

    try {
      var data = ctx.getImageData(0, 0, sw, sh).data;
      var rSum = 0, gSum = 0, bSum = 0, count = 0;
      var seen = new Set();
      var hueSum = 0, satSum = 0, briSum = 0;
      for (var i = 0; i < data.length; i += 4) {
        var r = data[i], g = data[i + 1], b = data[i + 2];
        rSum += r; gSum += g; bSum += b; count++;
        seen.add((r >> 4) + ',' + (g >> 4) + ',' + (b >> 4));
        var max = Math.max(r, g, b), min = Math.min(r, g, b);
        var l = (max + min) / 2 / 255;
        briSum += l;
        var s = max === min ? 0 : (l > 0.5 ? (max - min) / (2 - max / 255 - min / 255) / 255 : (max - min) / (max + min));
        satSum += s;
        var hh = 0;
        if (max !== min) {
          var d = max - min;
          if (max === r) hh = ((g - b) / d + (g < b ? 6 : 0));
          else if (max === g) hh = (b - r) / d + 2;
          else hh = (r - g) / d + 4;
          hh *= 60;
        }
        hueSum += hh;
      }
      var avgR = Math.round(rSum / count), avgG = Math.round(gSum / count), avgB = Math.round(bSum / count);
      setField('Brightness', Math.round((briSum / count) * 100) + '%');
      setField('Saturation', Math.round((satSum / count) * 100) + '%');
      setField('Hue', Math.round(hueSum / count) + '°');
      setField('Rgb', 'rgb(' + avgR + ', ' + avgG + ', ' + avgB + ')');
      setField('ColourCount', seen.size.toLocaleString() + ' (of ' + count.toLocaleString() + ' px sampled)');
      setDiagnostic([{ sev: 'ok', html: '<strong>Frame analysed.</strong> Image metrics below are from this single captured frame — recapture any time for a fresh reading.' }]);
    } catch (e) {
      setDiagnostic([{ sev: 'warn', html: 'Could not read pixel data from this frame: ' + escapeHtml(e.message || 'unknown error') + '.' }]);
    }
  }

  function buildReportObject() {
    var report = {};
    ids.forEach(function (id) { report[id] = fields[id].textContent; });
    return report;
  }

  function reportAsText(report) {
    var labels = {
      DeviceName: 'Device Name', Resolution: 'Resolution', Megapixels: 'Megapixels', AspectRatio: 'Aspect Ratio',
      FrameRate: 'Frame Rate', FacingMode: 'Facing Mode', FocusMode: 'Focus Mode', ResolutionRange: 'Resolution Range',
      FrameRateRange: 'Frame Rate Range', DeviceId: 'Device ID', Brightness: 'Average Brightness',
      Saturation: 'Average Saturation', Hue: 'Average Hue', Rgb: 'Average RGB', ColourCount: 'Distinct Colours Sampled',
    };
    return 'WebcamTest Camera Information Report\n' + ids.map(function (id) { return labels[id] + ': ' + report[id]; }).join('\n');
  }

  btnStart.addEventListener('click', function () { startStream(deviceSelect.value); });
  btnStop.addEventListener('click', function () {
    stopStream();
    setDiagnostic([{ sev: '', html: 'Camera stopped.' }]);
  });
  btnCapture.addEventListener('click', analyseFrame);
  deviceSelect.addEventListener('change', function () { if (currentStream) startStream(deviceSelect.value); });

  btnCopy.addEventListener('click', function () {
    var text = reportAsText(buildReportObject());
    (navigator.clipboard ? navigator.clipboard.writeText(text) : Promise.reject())
      .then(function () {
        var original = btnCopy.textContent;
        btnCopy.textContent = 'Copied!';
        setTimeout(function () { btnCopy.innerHTML = btnCopy.dataset.original || original; }, 1500);
      })
      .catch(function () {});
  });
  btnCopy.dataset.original = btnCopy.innerHTML;

  btnDownload.addEventListener('click', function () {
    var report = buildReportObject();
    var blob = new Blob([JSON.stringify(report, null, 2)], { type: 'application/json' });
    var url = URL.createObjectURL(blob);
    var a = document.createElement('a');
    a.href = url;
    a.download = 'camera-information-report.json';
    document.body.appendChild(a);
    a.click();
    a.remove();
    setTimeout(function () { URL.revokeObjectURL(url); }, 1000);
  });

  window.addEventListener('pagehide', stopStream);
  document.addEventListener('visibilitychange', function () {
    if (document.visibilityState === 'hidden') stopStream();
  });

  if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) {
    setDiagnostic([{ sev: 'error', html: '<strong>Your browser doesn’t support camera access.</strong>' }]);
    btnStart.disabled = true;
  }
})();'''

CONTENT_HTML = '''<p>The Camera Information Report is the single reference page every other camera tool on this site links back to: one consolidated table combining everything your browser can detect about your camera's hardware with a set of image-quality metrics computed from a frame you capture yourself.</p>
<h2>Where each number comes from</h2>
<p>The hardware section comes from two browser APIs read off your active camera track: <code>getSettings()</code>, which reports what was actually negotiated for the current stream, and <code>getCapabilities()</code>, which reports the camera's full supported range where the browser exposes it. The image metrics section — average brightness, saturation, hue, RGB and a rough distinct-colour count — is computed by drawing a single captured frame to a canvas and sampling its pixel data directly in your browser.</p>
<h2>Why some rows say "Unsupported in this browser"</h2>
<p>Firefox does not implement <code>getCapabilities()</code> at all, so focus mode, resolution range and frame-rate range will always show as unsupported there — this is a Firefox limitation, not a fault with your camera or this page. Chrome, Edge and other Chromium-based browsers generally report the fullest set of capabilities. Rather than treating a missing field as an error, this report is designed to degrade gracefully and show exactly which fields it couldn't read.</p>
<h2>Using this for a support ticket</h2>
<p>Both the <strong>Copy as Text</strong> and <strong>Download as JSON</strong> buttons capture a snapshot of everything currently shown in the report — useful if you need to describe your exact camera setup to a support team, a hardware reviewer, or a forum thread. Nothing is transmitted automatically; the copy/download only happens when you click the button.</p>'''

FAQ = [
    {"question": "Why do I need to capture a frame to see the image metrics?", "answer": "Brightness, saturation, hue and colour count are all measured from actual pixel data, which requires a still frame to analyse. The hardware section above it (resolution, frame rate, device name) is available as soon as the camera starts, without capturing anything."},
    {"question": "Is the captured frame saved or uploaded anywhere?", "answer": "No. The frame is drawn to an in-memory canvas element, analysed, and then discarded — it is never saved to disk or sent anywhere. Only the numeric report you choose to copy or download leaves the page, and only onto your own device."},
    {"question": "Why does Firefox show fewer fields than Chrome?", "answer": "Firefox doesn't implement the getCapabilities() browser API this report uses for focus mode and the resolution/frame-rate range fields. Every other field works the same across browsers."},
    {"question": "Can I use this to check a camera before buying a used laptop or webcam?", "answer": "Yes — the Download as JSON button gives you a portable snapshot you can compare against another device, or attach to a message when asking a seller questions."},
]

TOOL = {
    "slug": "webcam-camera-information-report",
    "meta_title": "Camera Information Report — Full Webcam Specs Online | WebcamTest",
    "meta_description": "See everything your browser can detect about your webcam in one report: resolution, megapixels, aspect ratio, frame rate, focus mode, and image metrics from a captured frame. Copy or download the results.",
    "h1": "Camera Information Report",
    "subtitle": "One consolidated report of everything detectable about your camera — hardware settings plus image metrics from a captured frame.",
    "card": {
        "layout": "raw",
        "fields_html": FIELDS_HTML,
    },
    "script": SCRIPT,
    "content_html": CONTENT_HTML,
    "faq": FAQ,
}

if __name__ == "__main__":
    out_path = os.path.join(CONTENT_DIR, "webcam-camera-information-report.json")
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(TOOL, f, indent=2, ensure_ascii=False)
    print("Wrote", out_path)
