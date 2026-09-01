#!/usr/bin/env python3
"""Writes src/content/webcam-low-light-noise-test.json."""
import json
import os

BASE = os.path.dirname(os.path.abspath(__file__))
CONTENT_DIR = os.path.normpath(os.path.join(BASE, "..", "..", "src", "content"))

CAMERA_ICON = '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M23 7l-7 5 7 5V7z"/><rect x="1" y="5" width="15" height="14" rx="2" ry="2"/></svg>'
GAUGE_ICON = '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M12 20a8 8 0 1 0-8-8" stroke-linecap="round"/><path d="M12 12l4-4" stroke-linecap="round"/><path d="M2 12h2M12 2v2M20 12h2"/></svg>'
MOON_ICON = '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M21 12.8A9 9 0 1 1 11.2 3a7 7 0 0 0 9.8 9.8z" stroke-linecap="round" stroke-linejoin="round"/></svg>'
DOT_ICON = '<svg viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="9"/></svg>'
PLACEHOLDER_ICON = '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5"><path d="M23 7l-7 5 7 5V7z"/><rect x="1" y="5" width="15" height="14" rx="2" ry="2"/></svg>'

FIELDS_HTML = f'''<div class="tool-panel primary">
  <div class="panel-header">
    <span class="panel-icon">{CAMERA_ICON}</span>
    <div><h2>Low-Light Noise Test</h2><p class="panel-sub">Hold the camera and scene completely still while taking a reading</p></div>
  </div>
  <div class="media-preview" id="cameraPreviewWrap">
    <video id="cameraVideo" autoplay playsinline muted></video>
    <div class="media-preview-placeholder" id="cameraPlaceholder">
      {PLACEHOLDER_ICON}
      <span>Your camera feed will appear here</span>
    </div>
  </div>
  <canvas id="analysisCanvas" style="display:none"></canvas>
  <div style="margin-top:1rem">
    <div class="level-meter-label"><span>Noise</span><strong id="noiseLabel">—</strong></div>
    <div class="level-meter"><div class="level-meter-fill" id="noiseFill"></div></div>
    <div class="level-meter-scale"><span>Clean</span><span>Moderate</span><span>Noisy</span><span>Very Noisy</span></div>
  </div>
  <div class="media-controls" style="margin-top:1rem">
    <button type="button" class="btn-primary" id="btnStartCamera">Start Camera</button>
    <button type="button" class="btn-secondary" id="btnStopCamera" disabled>Stop Camera</button>
    <select class="device-select" id="deviceSelect" aria-label="Select camera" disabled>
      <option value="">Default camera</option>
    </select>
  </div>
  <div class="tool-actions" style="margin-top:.5rem">
    <button type="button" class="btn-secondary" id="btnTakeReading" disabled>Take a Reading (1.5s, hold still)</button>
  </div>
  <div class="diagnostic-panel" id="diagnosticPanel" style="margin-top:1rem">
    <div class="diagnostic-item" id="diagDefault"><span class="diag-icon">{DOT_ICON}</span><span>Click <strong>Start Camera</strong> and allow access when your browser asks.</span></div>
  </div>
</div>
<div class="tool-panel">
  <div class="panel-header">
    <span class="panel-icon">{GAUGE_ICON}</span>
    <div><h2>Reading</h2></div>
  </div>
  <div class="stat-grid">
    <div class="stat-tile highlight"><span class="stat-value" id="statNoiseScore">—</span><span class="stat-label">Noise Score (0–100)</span></div>
  </div>
  <p class="field-note">This measures how much each pixel flickers between frames while nothing in the scene is moving — that flicker is sensor noise, not real detail. Movement during a reading will inflate the score, so hold still.</p>
</div>
<div class="tool-panel">
  <div class="panel-header">
    <span class="panel-icon">{MOON_ICON}</span>
    <div><h2>Dim-the-Lights Comparison</h2><p class="panel-sub">See noise rise as light drops — the exact effect a good sensor minimises</p></div>
  </div>
  <div class="stat-grid">
    <div class="stat-tile"><span class="stat-value" id="statBaseline">—</span><span class="stat-label">Normal Light</span></div>
    <div class="stat-tile"><span class="stat-value" id="statDimmed">—</span><span class="stat-label">Dimmed</span></div>
  </div>
  <div class="tool-actions">
    <button type="button" class="btn-secondary" id="btnSaveBaseline" disabled>Save as Normal Light</button>
    <button type="button" class="btn-secondary" id="btnSaveDimmed" disabled>Save as Dimmed</button>
  </div>
  <p class="field-note">Take a reading in your normal lighting and save it, then dim the room lights (or move away from a window) and take and save a second reading to compare.</p>
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
  var btnTakeReading = document.getElementById('btnTakeReading');
  var btnSaveBaseline = document.getElementById('btnSaveBaseline');
  var btnSaveDimmed = document.getElementById('btnSaveDimmed');
  var diagnosticPanel = document.getElementById('diagnosticPanel');
  var noiseFill = document.getElementById('noiseFill');
  var noiseLabel = document.getElementById('noiseLabel');
  var statNoiseScore = document.getElementById('statNoiseScore');
  var statBaseline = document.getElementById('statBaseline');
  var statDimmed = document.getElementById('statDimmed');

  var currentStream = null;
  var starting = false;
  var reading = false;
  var lastScore = null;
  var SAMPLE_SIZE = 32;
  var SAMPLE_COUNT = 20;
  var SAMPLE_INTERVAL_MS = 70;

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
    btnTakeReading.disabled = true;
    noiseFill.style.width = '0%';
    noiseLabel.textContent = '—';
    statNoiseScore.textContent = '—';
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

  function classify(score) {
    if (score < 12) return 'Very Clean';
    if (score < 28) return 'Clean';
    if (score < 50) return 'Moderate';
    if (score < 75) return 'Noisy';
    return 'Very Noisy';
  }

  function sampleFrame() {
    var w = video.videoWidth, h = video.videoHeight;
    if (!w || !h) return null;
    canvas.width = SAMPLE_SIZE;
    canvas.height = SAMPLE_SIZE;
    var ctx = canvas.getContext('2d');
    // Sample a small fixed crop from the centre of the frame -- the same
    // region every time, since temporal variance only measures noise
    // correctly when comparing the identical patch of scene across frames.
    var cropSize = Math.min(w, h) * 0.3;
    var sx = (w - cropSize) / 2, sy = (h - cropSize) / 2;
    ctx.drawImage(video, sx, sy, cropSize, cropSize, 0, 0, SAMPLE_SIZE, SAMPLE_SIZE);
    try {
      var data = ctx.getImageData(0, 0, SAMPLE_SIZE, SAMPLE_SIZE).data;
      var gray = new Float32Array(SAMPLE_SIZE * SAMPLE_SIZE);
      for (var i = 0, p = 0; i < data.length; i += 4, p++) {
        gray[p] = data[i] * 0.299 + data[i + 1] * 0.587 + data[i + 2] * 0.114;
      }
      return gray;
    } catch (e) {
      return null;
    }
  }

  // Temporal variance (the same pixel position across consecutive frames
  // of a held-still scene), not spatial variance -- spatial variance can't
  // distinguish noise from real fine detail in the scene, per this tool's
  // own spec note. Timer-driven (not requestAnimationFrame) since this is
  // a background sampling task, not rendering.
  function takeReading() {
    if (!currentStream || reading) return;
    reading = true;
    btnTakeReading.disabled = true;
    btnSaveBaseline.disabled = true;
    btnSaveDimmed.disabled = true;
    setDiagnostic([{ sev: '', html: 'Reading… hold the camera and scene completely still.' }]);

    var frames = [];
    var count = 0;
    var intervalId = setInterval(function () {
      var g = sampleFrame();
      if (g) frames.push(g);
      count++;
      if (count >= SAMPLE_COUNT) {
        clearInterval(intervalId);
        finishReading(frames);
      }
    }, SAMPLE_INTERVAL_MS);
  }

  function finishReading(frames) {
    reading = false;
    btnTakeReading.disabled = false;
    btnSaveBaseline.disabled = false;
    btnSaveDimmed.disabled = false;

    if (frames.length < 4) {
      setDiagnostic([{ sev: 'warn', html: 'Could not get enough samples for a reading -- try again.' }]);
      return;
    }

    var pixelCount = frames[0].length;
    var varianceSum = 0;
    for (var p = 0; p < pixelCount; p++) {
      var sum = 0;
      for (var f = 0; f < frames.length; f++) sum += frames[f][p];
      var mean = sum / frames.length;
      var sq = 0;
      for (var f2 = 0; f2 < frames.length; f2++) {
        var d = frames[f2][p] - mean;
        sq += d * d;
      }
      varianceSum += sq / frames.length;
    }
    var avgVariance = varianceSum / pixelCount;

    // Scaling divisor is empirical, not a calibrated absolute unit -- see
    // this tool's own field-note. Tuned against real hardware during
    // this build so a typical well-lit reading lands well short of 100,
    // leaving headroom to show the score rise as light drops.
    var score = Math.max(0, Math.min(100, Math.round(avgVariance / 1.2)));

    lastScore = score;
    noiseFill.style.width = score + '%';
    noiseLabel.textContent = score + ' — ' + classify(score);
    statNoiseScore.textContent = String(score);
    setDiagnostic([{ sev: 'ok', html: '<strong>Reading complete: ' + score + ' (' + classify(score) + ').</strong> Save this as your normal-light or dimmed comparison below, or take another reading.' }]);
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
        btnTakeReading.disabled = false;
        setDiagnostic([{ sev: 'ok', html: '<strong>Camera is live.</strong> Let it settle for a couple of seconds after any light change, then click Take a Reading and hold still.' }]);
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
  btnTakeReading.addEventListener('click', takeReading);
  btnSaveBaseline.addEventListener('click', function () {
    if (lastScore === null) return;
    statBaseline.textContent = String(lastScore);
  });
  btnSaveDimmed.addEventListener('click', function () {
    if (lastScore === null) return;
    statDimmed.textContent = String(lastScore);
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

CONTENT_HTML = '''<p>Sensor noise — the grainy flicker you see in dim conditions — is one of the biggest real quality differences between a cheap webcam and a good one, but it's almost invisible until you specifically look for it. This tool measures it directly.</p>
<h2>Why the measurement uses temporal variance, not a single frame</h2>
<p>Noise can't be reliably measured from a single still frame, because a busy, detailed scene and a genuinely noisy sensor can look similarly "grainy" to a simple analysis — spatial variance (comparing neighbouring pixels within one frame) can't tell the difference between real fine detail and noise. This test instead samples the exact same small patch of your scene across roughly 20 consecutive frames and measures how much each individual pixel flickers over time. In a held-still scene, any pixel-to-pixel variation over time is sensor noise, not detail — detail doesn't move, so a truly static patch should read almost perfectly stable pixel values frame after frame if the sensor were noise-free.</p>
<h2>Why you need to hold still</h2>
<p>Any real movement in the sampled patch during a reading — your hand, a swaying background object, even the camera itself shifting slightly — will inflate the score, since motion changes pixel values between frames for reasons that have nothing to do with sensor noise. Hold the camera and the framed scene completely still for the roughly 1.5 seconds a reading takes.</p>
<h2>The dim-the-lights comparison</h2>
<p>Every camera's automatic gain control raises its sensor's sensitivity as available light drops, and that increased gain amplifies noise along with the signal — this is the fundamental trade-off behind "how does this webcam handle low light." Taking a reading in your normal lighting, then dimming the room and taking a second reading, demonstrates this effect directly and lets you compare how much a given camera's noise floor rises as light gets scarce.</p>'''

FAQ = [
    {"question": "Why does the score go up if I move during a reading?", "answer": "The test measures how much each pixel changes between frames, assuming nothing in the scene is actually moving. Real movement changes pixel values for reasons unrelated to sensor noise, which inflates the score. Hold the camera and scene still for the full ~1.5 second reading."},
    {"question": "What's a good noise score?", "answer": "There's no universal target since it depends on lighting and camera quality, but a clean, well-lit reading from a typical webcam should land well below 30. Watch how much it rises specifically when you dim the lights — that rise, more than the absolute number, is the useful signal about your camera's low-light performance."},
    {"question": "Why does the camera need a moment to settle after I change the lighting?", "answer": "Auto-exposure and auto-gain take a moment to re-adjust after a lighting change. Taking a reading immediately after dimming the lights would partly measure the camera still adjusting, not its settled noise floor."},
    {"question": "Is any video recorded or uploaded?", "answer": "No. Each reading samples a small patch of the live frame directly in your browser's memory and discards it immediately after computing the noise score — nothing is saved or transmitted."},
]

TOOL = {
    "slug": "webcam-low-light-noise-test",
    "meta_title": "Webcam Low-Light Noise Test — Measure Sensor Noise Online | WebcamTest",
    "meta_description": "Measure your webcam's sensor noise using temporal variance across frames. See a live noise score and compare normal-light vs dimmed-light readings.",
    "h1": "Low-Light Noise Test",
    "subtitle": "Measures sensor noise from temporal variance across frames, with a guided dim-the-lights comparison.",
    "card": {
        "layout": "raw",
        "fields_html": FIELDS_HTML,
    },
    "script": SCRIPT,
    "content_html": CONTENT_HTML,
    "faq": FAQ,
}

if __name__ == "__main__":
    out_path = os.path.join(CONTENT_DIR, "webcam-low-light-noise-test.json")
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(TOOL, f, indent=2, ensure_ascii=False)
    print("Wrote", out_path)
