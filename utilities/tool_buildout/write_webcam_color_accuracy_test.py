#!/usr/bin/env python3
"""Writes src/content/webcam-color-accuracy-test.json."""
import json
import os

BASE = os.path.dirname(os.path.abspath(__file__))
CONTENT_DIR = os.path.normpath(os.path.join(BASE, "..", "..", "src", "content"))

CAMERA_ICON = '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M23 7l-7 5 7 5V7z"/><rect x="1" y="5" width="15" height="14" rx="2" ry="2"/></svg>'
PALETTE_ICON = '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="13.5" cy="6.5" r=".5"/><circle cx="17.5" cy="10.5" r=".5"/><circle cx="8.5" cy="7.5" r=".5"/><circle cx="6.5" cy="12.5" r=".5"/><path d="M12 2a10 10 0 1 0 0 20c1.1 0 2-.9 2-2 0-.5-.2-1-.5-1.4-.3-.4-.5-.9-.5-1.4 0-1.1.9-2 2-2h2.3c1.8 0 3.2-1.4 3.2-3.2C20.5 6.5 16.7 2 12 2z"/></svg>'
CARD_ICON = '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect x="2" y="5" width="20" height="14" rx="2"/><circle cx="8" cy="12" r="2"/><path d="M14 10h6M14 14h4"/></svg>'
DOT_ICON = '<svg viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="9"/></svg>'
PLACEHOLDER_ICON = '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5"><path d="M23 7l-7 5 7 5V7z"/><rect x="1" y="5" width="15" height="14" rx="2" ry="2"/></svg>'
DOWNLOAD_ICON = '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4M7 10l5 5 5-5M12 15V3" stroke-linecap="round" stroke-linejoin="round"/></svg>'

FIELDS_HTML = f'''<div class="tool-panel primary">
  <div class="panel-header">
    <span class="panel-icon">{CAMERA_ICON}</span>
    <div><h2>Colour Accuracy Test</h2><p class="panel-sub">Point the camera at the printable grey card (or a plain white sheet) filling the frame, then measure</p></div>
  </div>
  <div class="media-preview" id="cameraPreviewWrap">
    <video id="cameraVideo" autoplay playsinline muted></video>
    <div class="media-preview-placeholder" id="cameraPlaceholder">
      {PLACEHOLDER_ICON}
      <span>Your camera feed will appear here</span>
    </div>
  </div>
  <canvas id="analysisCanvas" style="display:none"></canvas>
  <div class="media-controls" style="margin-top:1rem">
    <button type="button" class="btn-primary" id="btnStartCamera">Start Camera</button>
    <button type="button" class="btn-secondary" id="btnStopCamera" disabled>Stop Camera</button>
    <select class="device-select" id="deviceSelect" aria-label="Select camera" disabled>
      <option value="">Default camera</option>
    </select>
  </div>
  <div class="tool-actions" style="margin-top:.5rem">
    <button type="button" class="btn-secondary" id="btnMeasure" disabled>Measure Colour Balance (3s)</button>
  </div>
  <div class="diagnostic-panel" id="diagnosticPanel" style="margin-top:1rem">
    <div class="diagnostic-item" id="diagDefault"><span class="diag-icon">{DOT_ICON}</span><span>Click <strong>Start Camera</strong> and allow access when your browser asks.</span></div>
  </div>
</div>
<div class="tool-panel">
  <div class="panel-header">
    <span class="panel-icon">{PALETTE_ICON}</span>
    <div><h2>Colour Reading</h2></div>
  </div>
  <div class="stat-grid">
    <div class="stat-tile highlight"><span class="stat-value" id="statCast">—</span><span class="stat-label">Detected Cast</span></div>
    <div class="stat-tile"><span class="stat-value" id="statRgb">—</span><span class="stat-label">Average RGB</span></div>
    <div class="stat-tile"><span class="stat-value" id="statDeviation">—</span><span class="stat-label">Max Channel Deviation</span></div>
  </div>
  <div id="swatch" style="height:48px;border-radius:var(--radius-sm);border:1px solid var(--border);margin-top:.75rem"></div>
  <p class="field-note">Without a known neutral reference, a colour reading is meaningless — that's what the grey card is for. Auto white balance keeps adjusting, so this samples over 3 seconds and averages.</p>
</div>
<div class="tool-panel">
  <div class="panel-header">
    <span class="panel-icon">{CARD_ICON}</span>
    <div><h2>Printable Grey Card</h2><p class="panel-sub">A neutral 50% grey reference — required for a meaningful reading</p></div>
  </div>
  <canvas id="cardCanvas" style="display:none"></canvas>
  <div class="media-preview" id="cardPreviewWrap" style="aspect-ratio:4/3;margin-bottom:1rem">
    <img id="cardPreviewImg" alt="Grey reference card preview" style="width:100%;height:100%;object-fit:contain" />
  </div>
  <button type="button" class="btn-secondary btn-icon-text" id="btnDownloadCard" style="width:100%">{DOWNLOAD_ICON} Download Grey Card (PNG)</button>
</div>'''

SCRIPT = r'''(function () {
  'use strict';

  var video = document.getElementById('cameraVideo');
  var previewWrap = document.getElementById('cameraPreviewWrap');
  var placeholder = document.getElementById('cameraPlaceholder');
  var canvas = document.getElementById('analysisCanvas');
  var deviceSelect = document.getElementById('deviceSelect');
  var btnStart = document.getElementById('btnStartCamera');
  var btnStop = document.getElementById('btnStopCamera');
  var btnMeasure = document.getElementById('btnMeasure');
  var diagnosticPanel = document.getElementById('diagnosticPanel');
  var statCast = document.getElementById('statCast');
  var statRgb = document.getElementById('statRgb');
  var statDeviation = document.getElementById('statDeviation');
  var swatch = document.getElementById('swatch');
  var cardCanvas = document.getElementById('cardCanvas');
  var cardPreviewImg = document.getElementById('cardPreviewImg');
  var btnDownloadCard = document.getElementById('btnDownloadCard');

  var currentStream = null;
  var starting = false;
  var measuring = false;

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
    video.srcObject = null;
    previewWrap.classList.remove('is-active');
    placeholder.style.display = 'flex';
    btnStop.disabled = true;
    btnMeasure.disabled = true;
    statCast.textContent = '—';
    statRgb.textContent = '—';
    statDeviation.textContent = '—';
    swatch.style.background = '';
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

  function sampleAverage() {
    var w = video.videoWidth, h = video.videoHeight;
    if (!w || !h) return null;
    var size = 60;
    canvas.width = size;
    canvas.height = size;
    var ctx = canvas.getContext('2d');
    var cropSize = Math.min(w, h) * 0.4;
    var sx = (w - cropSize) / 2, sy = (h - cropSize) / 2;
    // video.style.filter is never set on this page (no CSS filter applied
    // here), so the sampled pixels reflect the camera's own colour
    // rendering only -- see this tool's own spec note about disabling any
    // filter during measurement.
    ctx.drawImage(video, sx, sy, cropSize, cropSize, 0, 0, size, size);
    try {
      var data = ctx.getImageData(0, 0, size, size).data;
      var rSum = 0, gSum = 0, bSum = 0, count = 0;
      for (var i = 0; i < data.length; i += 4) {
        rSum += data[i]; gSum += data[i + 1]; bSum += data[i + 2]; count++;
      }
      return { r: rSum / count, g: gSum / count, b: bSum / count };
    } catch (e) {
      return null;
    }
  }

  function classifyCast(r, g, b) {
    var avg = (r + g + b) / 3;
    var dR = r - avg, dG = g - avg, dB = b - avg;
    var THRESHOLD = 6;
    var maxDev = Math.max(Math.abs(dR), Math.abs(dG), Math.abs(dB));
    if (maxDev < THRESHOLD) return 'Neutral';
    if (dR >= dG && dR >= dB) return dB <= dG ? 'Warm / Orange Cast' : 'Red Cast';
    if (dB >= dR && dB >= dG) return 'Cool / Blue Cast';
    return 'Green Cast (often fluorescent lighting)';
  }

  // Auto white balance keeps adjusting continuously, so a single frame is
  // unreliable -- sample over several seconds and average, per this tool's
  // own spec note. Timer-driven (background sampling, not rendering).
  function measureColor() {
    if (!currentStream || measuring) return;
    measuring = true;
    btnMeasure.disabled = true;
    setDiagnostic([{ sev: '', html: 'Sampling colour over 3 seconds…' }]);

    var samples = [];
    var intervalId = setInterval(function () {
      var s = sampleAverage();
      if (s) samples.push(s);
    }, 200);

    setTimeout(function () {
      clearInterval(intervalId);
      measuring = false;
      btnMeasure.disabled = false;
      if (samples.length < 3) {
        setDiagnostic([{ sev: 'warn', html: 'Could not get enough samples -- try again.' }]);
        return;
      }
      var r = samples.reduce(function (s, v) { return s + v.r; }, 0) / samples.length;
      var g = samples.reduce(function (s, v) { return s + v.g; }, 0) / samples.length;
      var b = samples.reduce(function (s, v) { return s + v.b; }, 0) / samples.length;
      var avg = (r + g + b) / 3;
      var maxDev = Math.max(Math.abs(r - avg), Math.abs(g - avg), Math.abs(b - avg));
      var cast = classifyCast(r, g, b);

      statRgb.textContent = 'rgb(' + Math.round(r) + ', ' + Math.round(g) + ', ' + Math.round(b) + ')';
      statDeviation.textContent = Math.round(maxDev) + ' / 255';
      statCast.textContent = cast;
      swatch.style.background = 'rgb(' + Math.round(r) + ',' + Math.round(g) + ',' + Math.round(b) + ')';
      setDiagnostic([{ sev: cast === 'Neutral' ? 'ok' : 'warn', html: '<strong>' + escapeHtml(cast) + '.</strong> Measured against your grey/white reference filling the frame. Point at a different reference or lighting to compare.' }]);
    }, 3000);
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
        btnMeasure.disabled = false;
        setDiagnostic([{ sev: 'ok', html: '<strong>Camera is live.</strong> Fill the frame with the grey card (or a plain white sheet) below, then click Measure.' }]);
        return navigator.mediaDevices.enumerateDevices().then(function (devices) {
          populateDeviceSelect(devices, settings.deviceId);
        });
      })
      .catch(function (err) { setDiagnostic([describeError(err)]); stopStream(); })
      .finally(function () { starting = false; btnStart.disabled = false; });
  }

  function drawGreyCard() {
    var w = 1200, h = 900;
    cardCanvas.width = w;
    cardCanvas.height = h;
    var ctx = cardCanvas.getContext('2d');
    ctx.fillStyle = '#808080'; // 50% neutral grey
    ctx.fillRect(0, 0, w, h);
    ctx.fillStyle = '#000000';
    ctx.font = 'bold 22px sans-serif';
    ctx.textAlign = 'center';
    ctx.fillText('WebcamTest Grey Card -- 50% Neutral Grey', w / 2, h - 24);
    cardPreviewImg.src = cardCanvas.toDataURL('image/png');
  }

  btnStart.addEventListener('click', function () { startStream(deviceSelect.value); });
  btnStop.addEventListener('click', function () {
    stopStream();
    setDiagnostic([{ sev: '', html: 'Camera stopped.' }]);
  });
  deviceSelect.addEventListener('change', function () { if (currentStream) startStream(deviceSelect.value); });
  btnMeasure.addEventListener('click', measureColor);

  btnDownloadCard.addEventListener('click', function () {
    var url = cardCanvas.toDataURL('image/png');
    var a = document.createElement('a');
    a.href = url;
    a.download = 'webcamtest-grey-card.png';
    document.body.appendChild(a);
    a.click();
    a.remove();
  });

  window.addEventListener('pagehide', stopStream);
  document.addEventListener('visibilitychange', function () {
    if (document.visibilityState === 'hidden') stopStream();
  });

  drawGreyCard();

  if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) {
    setDiagnostic([{ sev: 'error', html: '<strong>Your browser doesn’t support camera access.</strong>' }]);
    btnStart.disabled = true;
  }
})();'''

CONTENT_HTML = '''<p>Bad auto white balance and mixed lighting both show up as a colour cast — a subtle orange, blue or green tint across everything your camera captures. This tool measures that cast directly using a known neutral reference.</p>
<h2>Why a reference card is required, not optional</h2>
<p>A colour reading only means something when compared against something known to be neutral — without that, there's no way to tell whether a warm tone in the image is your camera's white balance or just a warm-coloured wall. The printable grey card (a flat, neutral 50% grey) or a plain white sheet gives the measurement something to compare against: any deviation from that known-neutral reference is a real colour cast, not scene content.</p>
<h2>Why the measurement takes 3 seconds</h2>
<p>Automatic white balance is a continuously adjusting system, not a one-time calculation — a single frame can catch it mid-adjustment and give a misleading reading. This test samples the frame repeatedly over 3 seconds and averages the result, which is far more representative of where your camera actually settles.</p>
<h2>Reading the result</h2>
<p>A "Neutral" result means your camera's white balance is close to accurate against the reference. A warm/orange or red cast usually points to incandescent lighting or a white-balance setting that hasn't adapted; a cool/blue cast often comes from shade, overcast daylight, or a camera locked to an indoor white-balance preset; a green cast is a common signature of certain fluorescent lighting.</p>'''

FAQ = [
    {"question": "Do I have to use the printable grey card, or can I use anything white?", "answer": "A plain white sheet of paper works too, as long as it fills the frame and isn't itself tinted. The printed grey card is simply a more consistent, known-neutral reference than most household white objects, which often have a slight tint of their own."},
    {"question": "Why does my reading change if I retest a minute later?", "answer": "Auto white balance continuously adjusts to lighting, and lighting itself can shift (clouds passing, a light warming up). If your surroundings haven't changed and the result differs a lot, try letting the camera settle for a few seconds before measuring again."},
    {"question": "What does \"Green Cast\" usually mean?", "answer": "It's a common signature of certain fluorescent or LED lighting, which don't emit a smooth, continuous spectrum the way daylight or incandescent bulbs do. It's a lighting characteristic more than a camera fault."},
    {"question": "Is my video uploaded for this analysis?", "answer": "No. Frames are sampled and averaged directly in your browser's memory during the 3-second measurement and then discarded — nothing is saved or transmitted."},
]

TOOL = {
    "slug": "webcam-color-accuracy-test",
    "meta_title": "Webcam Colour Accuracy Test — Detect White Balance Casts | WebcamTest",
    "meta_description": "Measure your webcam's colour balance against a printable grey card reference. Detects warm, cool and green colour casts from bad auto white balance or mixed lighting.",
    "h1": "Colour Accuracy Test",
    "subtitle": "Measures colour balance against a printable grey card reference, detecting warm, cool and green colour casts.",
    "card": {
        "layout": "raw",
        "fields_html": FIELDS_HTML,
    },
    "script": SCRIPT,
    "content_html": CONTENT_HTML,
    "faq": FAQ,
}

if __name__ == "__main__":
    out_path = os.path.join(CONTENT_DIR, "webcam-color-accuracy-test.json")
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(TOOL, f, indent=2, ensure_ascii=False)
    print("Wrote", out_path)
