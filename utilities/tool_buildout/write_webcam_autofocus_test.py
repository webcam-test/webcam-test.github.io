#!/usr/bin/env python3
"""Writes src/content/webcam-autofocus-test.json."""
import json
import os

BASE = os.path.dirname(os.path.abspath(__file__))
CONTENT_DIR = os.path.normpath(os.path.join(BASE, "..", "..", "src", "content"))

CAMERA_ICON = '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M23 7l-7 5 7 5V7z"/><rect x="1" y="5" width="15" height="14" rx="2" ry="2"/></svg>'
GAUGE_ICON = '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M12 20a8 8 0 1 0-8-8" stroke-linecap="round"/><path d="M12 12l4-4" stroke-linecap="round"/><path d="M2 12h2M12 2v2M20 12h2"/></svg>'
INFO_ICON = '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="10"/><path d="M12 16v-4M12 8h.01" stroke-linecap="round"/></svg>'
DOT_ICON = '<svg viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="9"/></svg>'
PLACEHOLDER_ICON = '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5"><path d="M23 7l-7 5 7 5V7z"/><rect x="1" y="5" width="15" height="14" rx="2" ry="2"/></svg>'

FIELDS_HTML = f'''<div class="tool-panel primary">
  <div class="panel-header">
    <span class="panel-icon">{CAMERA_ICON}</span>
    <div><h2>Autofocus Test</h2><p class="panel-sub">Point at something detailed, then run the guided test while moving an object toward the lens</p></div>
  </div>
  <div class="media-preview" id="cameraPreviewWrap">
    <video id="cameraVideo" autoplay playsinline muted></video>
    <div class="media-preview-placeholder" id="cameraPlaceholder">
      {PLACEHOLDER_ICON}
      <span>Your camera feed will appear here</span>
    </div>
  </div>
  <canvas id="analysisCanvas" style="display:none"></canvas>
  <canvas id="curveCanvas" style="width:100%;height:90px;margin-top:1rem;border-radius:var(--radius-sm);border:1px solid var(--border);background:var(--bg-alt)"></canvas>
  <div style="margin-top:.75rem">
    <div class="level-meter-label"><span>Live Sharpness</span><strong id="sharpnessLabel">—</strong></div>
    <div class="level-meter"><div class="level-meter-fill" id="sharpnessFill"></div></div>
  </div>
  <div class="media-controls" style="margin-top:1rem">
    <button type="button" class="btn-primary" id="btnStartCamera">Start Camera</button>
    <button type="button" class="btn-secondary" id="btnStopCamera" disabled>Stop Camera</button>
    <select class="device-select" id="deviceSelect" aria-label="Select camera" disabled>
      <option value="">Default camera</option>
    </select>
  </div>
  <div class="tool-actions" style="margin-top:.5rem">
    <button type="button" class="btn-secondary" id="btnRunTest" disabled>Run Guided Focus Test (8s)</button>
  </div>
  <div class="diagnostic-panel" id="diagnosticPanel" style="margin-top:1rem">
    <div class="diagnostic-item" id="diagDefault"><span class="diag-icon">{DOT_ICON}</span><span>Click <strong>Start Camera</strong> and allow access when your browser asks.</span></div>
  </div>
</div>
<div class="tool-panel">
  <div class="panel-header">
    <span class="panel-icon">{GAUGE_ICON}</span>
    <div><h2>Result</h2></div>
  </div>
  <div class="stat-grid">
    <div class="stat-tile highlight"><span class="stat-value" id="statVerdict">—</span><span class="stat-label">Verdict</span></div>
    <div class="stat-tile"><span class="stat-value" id="statFocusMode">—</span><span class="stat-label">Reported Focus Mode</span></div>
  </div>
  <p class="field-note">Browser-reported focus mode is Chromium-leaning and often absent (always missing in Firefox) — the guided test below is the reliable method regardless of browser.</p>
</div>
<div class="tool-panel">
  <div class="panel-header">
    <span class="panel-icon">{INFO_ICON}</span>
    <div><h2>How to Run the Test</h2></div>
  </div>
  <p class="field-note" style="margin-top:0">1. Point the camera at something with fine detail — text or a patterned object.</p>
  <p class="field-note">2. Click <strong>Run Guided Focus Test</strong>, then a couple of seconds in, move a second object (a hand, a book) much closer to the lens and hold it there.</p>
  <p class="field-note" style="margin-bottom:0">3. If your camera has autofocus, the sharpness curve will dip as it loses focus, then climb back up as it reacquires — that recovery is timed. A flat curve the whole time usually means fixed focus.</p>
</div>'''

SCRIPT = r'''(function () {
  'use strict';

  var video = document.getElementById('cameraVideo');
  var previewWrap = document.getElementById('cameraPreviewWrap');
  var placeholder = document.getElementById('cameraPlaceholder');
  var canvas = document.getElementById('analysisCanvas');
  var curveCanvas = document.getElementById('curveCanvas');
  var deviceSelect = document.getElementById('deviceSelect');
  var btnStart = document.getElementById('btnStartCamera');
  var btnStop = document.getElementById('btnStopCamera');
  var btnRunTest = document.getElementById('btnRunTest');
  var diagnosticPanel = document.getElementById('diagnosticPanel');
  var sharpnessFill = document.getElementById('sharpnessFill');
  var sharpnessLabel = document.getElementById('sharpnessLabel');
  var statVerdict = document.getElementById('statVerdict');
  var statFocusMode = document.getElementById('statFocusMode');

  var currentStream = null;
  var starting = false;
  var liveTimer = null;
  var testing = false;

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

  // Same variance-of-Laplacian sharpness scorer as
  // webcam-sharpness-focus-test.json -- reused rather than reimplemented,
  // per this tool's own spec note, including the same tuned /70 scaling
  // divisor confirmed against real hardware on that tool.
  function measureSharpness() {
    if (!currentStream || !video.videoWidth) return null;
    var w = video.videoWidth, h = video.videoHeight;
    var scale = Math.min(1, 140 / Math.max(w, h));
    var sw = Math.max(8, Math.round(w * scale));
    var sh = Math.max(8, Math.round(h * scale));
    canvas.width = sw;
    canvas.height = sh;
    var ctx = canvas.getContext('2d');
    ctx.drawImage(video, 0, 0, sw, sh);

    var data;
    try {
      data = ctx.getImageData(0, 0, sw, sh).data;
    } catch (e) {
      return null;
    }

    var gray = new Float32Array(sw * sh);
    for (var i = 0, p = 0; i < data.length; i += 4, p++) {
      gray[p] = data[i] * 0.299 + data[i + 1] * 0.587 + data[i + 2] * 0.114;
    }

    var lapSum = 0, lapSumSq = 0, count = 0;
    for (var y = 1; y < sh - 1; y++) {
      for (var x = 1; x < sw - 1; x++) {
        var idx = y * sw + x;
        var lap = 4 * gray[idx] - gray[idx - 1] - gray[idx + 1] - gray[idx - sw] - gray[idx + sw];
        lapSum += lap;
        lapSumSq += lap * lap;
        count++;
      }
    }
    if (!count) return null;
    var mean = lapSum / count;
    var variance = (lapSumSq / count) - (mean * mean);
    return Math.max(0, Math.min(100, Math.round(variance / 70)));
  }

  function updateLiveMeter() {
    var score = measureSharpness();
    if (score === null) return;
    sharpnessFill.style.width = score + '%';
    sharpnessLabel.textContent = String(score);
    return score;
  }

  function drawCurve(samples) {
    var w = curveCanvas.clientWidth || 300;
    var h = curveCanvas.clientHeight || 90;
    curveCanvas.width = w;
    curveCanvas.height = h;
    var ctx = curveCanvas.getContext('2d');
    ctx.clearRect(0, 0, w, h);
    if (samples.length < 2) return;
    ctx.strokeStyle = '#7c5cff';
    ctx.lineWidth = 2;
    ctx.beginPath();
    samples.forEach(function (s, i) {
      var x = (i / (samples.length - 1)) * w;
      var y = h - (s / 100) * h;
      if (i === 0) ctx.moveTo(x, y); else ctx.lineTo(x, y);
    });
    ctx.stroke();
  }

  // Timer-driven (not requestAnimationFrame) -- this is background
  // sampling/analysis, not rendering, per the rAF-vs-timer distinction
  // documented elsewhere in this project.
  function runGuidedTest() {
    if (!currentStream || testing) return;
    testing = true;
    btnRunTest.disabled = true;
    setDiagnostic([{ sev: '', html: 'Recording… point at detail, then partway through move an object much closer to the lens and hold it.' }]);
    var samples = [];
    var sampleId = setInterval(function () {
      var score = updateLiveMeter();
      if (score !== null) samples.push(score);
      drawCurve(samples);
    }, 150);

    setTimeout(function () {
      clearInterval(sampleId);
      testing = false;
      btnRunTest.disabled = false;
      analyseCurve(samples);
    }, 8000);
  }

  // Fixed-focus cameras produce a flat curve -- that flatness is itself the
  // result, per this tool's own spec note. A real autofocus recovery shows
  // as a dip (losing focus on the closer object) followed by a climb back
  // up (reacquiring), which this looks for directly in the sample series.
  function analyseCurve(samples) {
    if (samples.length < 8) {
      statVerdict.textContent = 'Inconclusive';
      setDiagnostic([{ sev: 'warn', html: 'Not enough samples captured -- try the test again.' }]);
      return;
    }
    var minIdx = 0;
    for (var i = 1; i < samples.length; i++) {
      if (samples[i] < samples[minIdx]) minIdx = i;
    }
    var preMin = Math.max.apply(null, samples.slice(0, Math.max(1, minIdx)));
    var postMax = Math.max.apply(null, samples.slice(minIdx));
    var dip = preMin - samples[minIdx];
    var recovery = postMax - samples[minIdx];
    var THRESHOLD = 12;

    if (dip > THRESHOLD && recovery > THRESHOLD && minIdx > 0 && minIdx < samples.length - 1) {
      var recoverIdx = minIdx;
      for (var j = minIdx; j < samples.length; j++) {
        if (samples[j] >= samples[minIdx] + recovery * 0.85) { recoverIdx = j; break; }
      }
      var seconds = ((recoverIdx - minIdx) * 0.15).toFixed(1);
      statVerdict.textContent = 'Autofocus (~' + seconds + 's)';
      setDiagnostic([{ sev: 'ok', html: '<strong>Autofocus detected.</strong> The camera lost and regained sharpness during the test, recovering in roughly ' + seconds + ' seconds.' }]);
    } else {
      statVerdict.textContent = 'Fixed Focus / Flat';
      setDiagnostic([{ sev: '', html: 'The sharpness curve stayed roughly flat -- this usually means fixed focus, or that no distance change was detected during the test. If you didn’t move an object closer during recording, try again.' }]);
    }
  }

  // Same stopStream()/describeError()/populateDeviceSelect() pattern as
  // webcam-test-online's own script (see this project's CLAUDE.md -- every
  // camera tool copies this teardown block rather than importing a shared file).
  function stopStream() {
    if (liveTimer) { clearInterval(liveTimer); liveTimer = null; }
    testing = false;
    if (currentStream) {
      currentStream.getTracks().forEach(function (t) { t.stop(); });
      currentStream = null;
    }
    video.srcObject = null;
    previewWrap.classList.remove('is-active');
    placeholder.style.display = 'flex';
    btnStop.disabled = true;
    btnRunTest.disabled = true;
    sharpnessFill.style.width = '0%';
    sharpnessLabel.textContent = '—';
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
        var caps = track.getCapabilities ? (function () { try { return track.getCapabilities(); } catch (e) { return null; } })() : null;
        btnStop.disabled = false;
        btnRunTest.disabled = false;
        statFocusMode.textContent = (caps && caps.focusMode && caps.focusMode.length) ? caps.focusMode.join(', ') : 'Not reported';
        setDiagnostic([{ sev: 'ok', html: '<strong>Camera is live.</strong> Point at something detailed, then click Run Guided Focus Test.' }]);
        liveTimer = setInterval(updateLiveMeter, 250);
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
  btnRunTest.addEventListener('click', runGuidedTest);

  window.addEventListener('pagehide', stopStream);
  document.addEventListener('visibilitychange', function () {
    if (document.visibilityState === 'hidden') stopStream();
  });

  if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) {
    setDiagnostic([{ sev: 'error', html: '<strong>Your browser doesn’t support camera access.</strong>' }]);
    btnStart.disabled = true;
  }
})();'''

CONTENT_HTML = '''<p>Many cheap webcams have fixed focus and simply don't advertise it — the only reliable way to find out is to watch how sharpness responds when the distance to your subject actually changes. This tool runs that test directly.</p>
<h2>Why the guided test is the primary method, not the capability check</h2>
<p>Browsers can sometimes report a camera's focus mode directly through <code>getCapabilities()</code>, but this API is inconsistently implemented — it leans heavily toward Chromium-based browsers and is entirely absent in Firefox. Rather than rely on that alone, this tool's main method is a guided sharpness-curve test: it reuses the same edge-detection sharpness scorer as the Sharpness and Focus Test tool, records it continuously while you deliberately change the distance to your subject, and looks for the signature of a real autofocus event — a dip in sharpness followed by a climb back up as the camera reacquires.</p>
<h2>What a flat curve means</h2>
<p>If the sharpness score stays roughly flat throughout the test even after you've moved an object toward the lens, that's a meaningful result in itself: it points to fixed focus, where the lens simply can't refocus regardless of distance. It can also mean the distance change wasn't large or fast enough for the camera to register — if you're unsure, try the test again with a bigger, more deliberate movement.</p>
<h2>Reading the recovery time</h2>
<p>When a genuine dip-then-recovery pattern is detected, the reported time is roughly how long the camera took to reacquire sharp focus after the distance change, not how long the whole test ran. A fast recovery time generally means a more responsive autofocus system.</p>'''

FAQ = [
    {"question": "Why does the test need me to move an object during it?", "answer": "Autofocus only shows itself when the subject distance actually changes — a static scene gives a fixed-focus camera and an autofocus camera an identical result. Moving an object closer partway through the recording is what creates a detectable dip-and-recovery signature if autofocus is present."},
    {"question": "My result says \"Fixed Focus / Flat\" but I'm sure my camera has autofocus — what happened?", "answer": "The distance change may not have been large or fast enough, or wasn't well-lit or detailed enough for the sharpness scorer to register clearly. Try again with a bigger, quicker movement and make sure both distances have visible texture or detail in frame."},
    {"question": "Why does Firefox show \"Not reported\" for focus mode?", "answer": "Firefox doesn't implement the getCapabilities() browser API this field reads from at all. It's a Firefox limitation, not a fault with your camera — the guided test below it works the same regardless of browser."},
    {"question": "Is any video recorded or uploaded during the test?", "answer": "No. Every frame is analysed in memory in your browser for its sharpness score only, and discarded immediately — nothing is saved or transmitted."},
]

TOOL = {
    "slug": "webcam-autofocus-test",
    "meta_title": "Webcam Autofocus Test — Does Your Camera Actually Focus? | WebcamTest",
    "meta_description": "Test whether your webcam has real autofocus or fixed focus. A guided sharpness-curve test measures how quickly your camera refocuses when subject distance changes.",
    "h1": "Autofocus Test",
    "subtitle": "Find out whether your camera has autofocus or fixed focus, and how quickly it refocuses when distance changes.",
    "card": {
        "layout": "raw",
        "fields_html": FIELDS_HTML,
    },
    "script": SCRIPT,
    "content_html": CONTENT_HTML,
    "faq": FAQ,
}

if __name__ == "__main__":
    out_path = os.path.join(CONTENT_DIR, "webcam-autofocus-test.json")
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(TOOL, f, indent=2, ensure_ascii=False)
    print("Wrote", out_path)
