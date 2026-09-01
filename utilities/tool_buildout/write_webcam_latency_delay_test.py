#!/usr/bin/env python3
"""Writes src/content/webcam-latency-delay-test.json."""
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
    <div><h2>Camera Latency Test</h2><p class="panel-sub">Works with any camera — front, rear or external. No second device or screen-pointing needed</p></div>
  </div>
  <div id="cueBox" style="width:100%;aspect-ratio:16/9;border-radius:var(--radius-md);background:var(--bg-alt);border:2px solid var(--border);display:flex;align-items:center;justify-content:center;color:var(--text-muted);font-weight:700;font-size:1.3rem;margin-bottom:1rem;transition:background-color .1s,color .1s">Get Ready…</div>
  <div class="media-preview" id="cameraPreviewWrap" style="height:140px">
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
    <button type="button" class="btn-secondary" id="btnRunTest" disabled>Run Reaction Test (6 trials)</button>
  </div>
  <div class="diagnostic-panel" id="diagnosticPanel" style="margin-top:1rem">
    <div class="diagnostic-item" id="diagDefault"><span class="diag-icon">{DOT_ICON}</span><span>Start your camera, then click Run Reaction Test. When the box turns green and says <strong>MOVE NOW</strong>, quickly wave your hand in front of the camera or cover the lens.</span></div>
  </div>
</div>
<div class="tool-panel">
  <div class="panel-header">
    <span class="panel-icon">{GAUGE_ICON}</span>
    <div><h2>Result</h2></div>
  </div>
  <div class="stat-grid">
    <div class="stat-tile highlight"><span class="stat-value" id="statEstimate">—</span><span class="stat-label">Estimated Camera Response Range</span></div>
    <div class="stat-tile"><span class="stat-value" id="statRawAvg">—</span><span class="stat-label">Raw Average (before adjustment)</span></div>
  </div>
  <p class="field-note">This is a range, not a precise figure — see why alongside this.</p>
</div>
<div class="tool-panel">
  <div class="panel-header">
    <span class="panel-icon">{INFO_ICON}</span>
    <div><h2>What This Actually Measures</h2></div>
  </div>
  <p class="field-note" style="margin-top:0">Every trial measures <strong>your visual reaction time plus the camera's actual capture-to-detection delay combined</strong> — a browser can't separate the two. This test subtracts a typical average human visual reaction time (~250 ms, slightly slower than the ~190 ms typical for reacting to sound) from your average, and reports a range rather than a falsely precise single number.</p>
  <p class="field-note" style="margin-bottom:0">Because this only needs the camera to see <em>you</em> reacting — not to be pointed at a screen — it works with a front-facing laptop webcam, a phone's front or rear camera, or an external webcam, with no special physical setup required.</p>
</div>'''

SCRIPT = r'''(function () {
  'use strict';

  var video = document.getElementById('cameraVideo');
  var previewWrap = document.getElementById('cameraPreviewWrap');
  var placeholder = document.getElementById('cameraPlaceholder');
  var canvas = document.getElementById('analysisCanvas');
  var cueBox = document.getElementById('cueBox');
  var deviceSelect = document.getElementById('deviceSelect');
  var btnStart = document.getElementById('btnStartCamera');
  var btnStop = document.getElementById('btnStopCamera');
  var btnRunTest = document.getElementById('btnRunTest');
  var diagnosticPanel = document.getElementById('diagnosticPanel');
  var statEstimate = document.getElementById('statEstimate');
  var statRawAvg = document.getElementById('statRawAvg');

  var TRIAL_COUNT = 6;
  var CHANGE_THRESHOLD = 30; // absolute brightness delta (either direction) counted as "the visitor moved"
  var TRIAL_TIMEOUT_MS = 2500;
  var AVG_VISUAL_REACTION_MS = 250; // typical average human visual reaction time, subtracted from the raw measurement

  var currentStream = null;
  var starting = false;
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
    btnRunTest.disabled = true;
    testing = false;
    cueBox.style.background = 'var(--bg-alt)';
    cueBox.style.color = 'var(--text-muted)';
    cueBox.textContent = 'Get Ready…';
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

  function sampleBrightness() {
    var w = video.videoWidth, h = video.videoHeight;
    if (!w || !h) return null;
    var size = 24;
    canvas.width = size;
    canvas.height = size;
    var ctx = canvas.getContext('2d');
    var cropSize = Math.min(w, h) * 0.6;
    var sx = (w - cropSize) / 2, sy = (h - cropSize) / 2;
    ctx.drawImage(video, sx, sy, cropSize, cropSize, 0, 0, size, size);
    try {
      var data = ctx.getImageData(0, 0, size, size).data;
      var sum = 0, count = 0;
      for (var i = 0; i < data.length; i += 4) {
        sum += data[i] * 0.299 + data[i + 1] * 0.587 + data[i + 2] * 0.114;
        count++;
      }
      return sum / count;
    } catch (e) {
      return null;
    }
  }

  // requestVideoFrameCallback fires once per decoded video frame -- the
  // most precise way to detect exactly which delivered frame first shows
  // the visitor's movement, distinct from polling on an arbitrary timer.
  // Firefox doesn't implement it, so this falls back to a fast setInterval
  // poll instead, same fallback convention as
  // webcam-fps-frame-rate-checker's own script. An independent setTimeout
  // deadline (not reliant on the poll callback itself firing) guards
  // against requestVideoFrameCallback correctly pausing on a hidden tab,
  // which would otherwise leave a trial hanging indefinitely.
  function waitForMovement(baseline, onDetect, onTimeout) {
    var supportsRVFC = typeof video.requestVideoFrameCallback === 'function';
    var fallbackIntervalId = null;
    var settled = false;

    var deadlineId = setTimeout(function () {
      if (settled) return;
      settled = true;
      if (fallbackIntervalId) clearInterval(fallbackIntervalId);
      onTimeout();
    }, TRIAL_TIMEOUT_MS);

    function check() {
      if (settled) return true;
      var b = sampleBrightness();
      if (b !== null && Math.abs(b - baseline) > CHANGE_THRESHOLD) {
        settled = true;
        clearTimeout(deadlineId);
        if (fallbackIntervalId) clearInterval(fallbackIntervalId);
        onDetect(performance.now());
        return true;
      }
      return false;
    }

    if (supportsRVFC) {
      function frameTick() {
        if (check()) return;
        video.requestVideoFrameCallback(frameTick);
      }
      video.requestVideoFrameCallback(frameTick);
    } else {
      fallbackIntervalId = setInterval(function () { check(); }, 8);
    }
  }

  function runTrial(index, results, doneCallback) {
    if (!testing) return;
    cueBox.style.background = 'var(--bg-alt)';
    cueBox.style.color = 'var(--text-muted)';
    cueBox.textContent = 'Get Ready…';
    setDiagnostic([{ sev: '', html: 'Trial ' + (index + 1) + ' of ' + TRIAL_COUNT + ' — hold still…' }]);

    // Random 1-2.5s wait before each cue so the visitor can't anticipate
    // the exact timing, same rationale as the audio latency test.
    setTimeout(function () {
      if (!testing) return;
      var baseline = sampleBrightness();
      if (baseline === null) { results.push(null); return doneCallback(); }
      var cueTime = performance.now();
      cueBox.style.background = '#22c55e';
      cueBox.style.color = '#fff';
      cueBox.textContent = 'MOVE NOW!';
      waitForMovement(
        baseline,
        function (detectTime) {
          results.push(detectTime - cueTime);
          doneCallback();
        },
        function () {
          results.push(null);
          setDiagnostic([{ sev: 'warn', html: 'Trial ' + (index + 1) + ' timed out -- make sure your camera can see you move, and react as soon as the box turns green.' }]);
          doneCallback();
        }
      );
    }, 1000 + Math.random() * 1500);
  }

  function runTest() {
    if (!currentStream || testing) return;
    testing = true;
    btnRunTest.disabled = true;
    var results = [];
    var i = 0;

    function next() {
      if (!testing) return;
      if (i >= TRIAL_COUNT) return finish(results);
      var idx = i;
      i++;
      runTrial(idx, results, next);
    }
    next();
  }

  function finish(results) {
    testing = false;
    btnRunTest.disabled = false;
    cueBox.style.background = 'var(--bg-alt)';
    cueBox.style.color = 'var(--text-muted)';
    cueBox.textContent = 'Get Ready…';

    var valid = results.filter(function (r) { return r !== null; });
    if (valid.length < 3) {
      setDiagnostic([{ sev: 'warn', html: '<strong>Not enough valid trials.</strong> Make sure your camera can clearly see you, and react the instant the box turns green.' }]);
      statEstimate.textContent = 'Inconclusive';
      statRawAvg.textContent = '—';
      return;
    }

    // Discard outliers (implausibly fast/slow) before averaging, same
    // approach as the audio latency test's own reaction-based measurement.
    var sorted = valid.slice().sort(function (a, b) { return a - b; });
    var filtered = sorted.filter(function (v) { return v > 80 && v < 2000; });
    var mean = filtered.reduce(function (a, b) { return a + b; }, 0) / filtered.length;
    var estimate = Math.max(0, Math.round(mean - AVG_VISUAL_REACTION_MS));
    var spread = Math.round((filtered[filtered.length - 1] - filtered[0]) / 2) || 20;
    var low = Math.max(0, estimate - spread);
    var high = estimate + spread;

    statRawAvg.textContent = Math.round(mean) + ' ms';
    statEstimate.textContent = low + '–' + high + ' ms';
    setDiagnostic([{ sev: 'ok', html: '<strong>Estimated camera response: ' + low + '–' + high + ' ms.</strong> This range already accounts for typical visual reaction time (~250 ms), subtracted from your raw average of ' + Math.round(mean) + ' ms across ' + filtered.length + ' valid trials.' }]);
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
        btnRunTest.disabled = false;
        setDiagnostic([{ sev: 'ok', html: '<strong>Camera is live.</strong> Click Run Reaction Test, then react the instant the box turns green.' }]);
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
  btnRunTest.addEventListener('click', runTest);

  window.addEventListener('pagehide', stopStream);
  document.addEventListener('visibilitychange', function () {
    if (document.visibilityState === 'hidden') stopStream();
  });

  if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) {
    setDiagnostic([{ sev: 'error', html: '<strong>Your browser doesn’t support camera access.</strong>' }]);
    btnStart.disabled = true;
  }
})();'''

CONTENT_HTML = '''<p>The delay between something actually happening and it appearing on screen matters more than most people realise until they've tried to react to something on a laggy video call. This tool gives you a rough, honestly-framed estimate of your camera's own response delay, using only the camera you already have.</p>
<h2>Why this doesn't need an external camera or a second device</h2>
<p>Measuring camera latency precisely would normally need a controlled external stimulus with a known exact timestamp. Rather than requiring a second device or an awkward setup where your camera has to be turned to face a screen, this test uses the same technique as a reaction-time test: it shows an on-screen cue at a precisely recorded moment, and asks you to react by waving your hand or covering the lens the instant you see it. That works with any camera pointed at you normally — a laptop's built-in webcam, a phone's front or rear camera, or an external one — with no repositioning needed.</p>
<h2>Why this can only ever be an estimate</h2>
<p>Every trial measures <em>your reaction time plus the camera's actual capture-and-detection delay, added together</em> — a browser has no way to cleanly separate the two. This test handles that honestly, the same way this site's own Audio Latency Test does: it subtracts a typical average human visual reaction time (around 250 milliseconds — slightly slower than the ~190ms typical for reacting to sound, a well-documented difference in reaction-time research) from your measured average, and reports the result as a range rather than a single falsely precise number.</p>
<h2>Why the cue appears at random intervals</h2>
<p>If the cue appeared on a predictable schedule, you'd naturally start reacting to its rhythm rather than genuinely reacting to the visual change — which would measure your sense of timing, not camera responsiveness. Random 1-2.5 second gaps before each cue prevent that.</p>'''

FAQ = [
    {"question": "Why does the test ask me to move instead of just watching my camera automatically?", "answer": "A browser can't create a known, precisely-timestamped real-world event on its own — it needs a moment it can measure exactly. Showing you a cue and having you react is the same technique used for reaction-time testing generally, adapted here to also capture your camera's own response delay."},
    {"question": "Why is the result a range instead of one number?", "answer": "Because a browser can't separate your personal reaction time from your camera's actual response delay — every trial measures both combined. Reporting a range, after subtracting a typical average reaction time, is more honest than presenting a single number with false precision."},
    {"question": "Why did some of my trials time out?", "answer": "A trial times out if no clear movement is detected within 2.5 seconds of the cue — usually because the reaction was too subtle for the camera to register clearly, or the camera couldn't see the movement well (poor lighting, movement too far from frame). Make a clear, deliberate movement close to the camera as soon as the box turns green."},
    {"question": "Does this work with a phone's front camera?", "answer": "Yes — unlike a setup that requires pointing a camera at a screen, this only needs the camera to see you react, which works with any camera facing you normally, including a phone's front camera."},
]

TOOL = {
    "slug": "webcam-latency-delay-test",
    "meta_title": "Webcam Latency Test — Estimate Camera Response Time | WebcamTest",
    "meta_description": "Estimate your camera's response delay with a quick reaction-time test — no external camera or screen-pointing needed. Works with any front, rear or external camera.",
    "h1": "Camera Latency Test",
    "subtitle": "Estimates your camera's response delay from a quick reaction-time test — works with any camera, no second device needed.",
    "card": {
        "layout": "raw",
        "fields_html": FIELDS_HTML,
    },
    "script": SCRIPT,
    "content_html": CONTENT_HTML,
    "faq": FAQ,
}

if __name__ == "__main__":
    out_path = os.path.join(CONTENT_DIR, "webcam-latency-delay-test.json")
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(TOOL, f, indent=2, ensure_ascii=False)
    print("Wrote", out_path)
