#!/usr/bin/env python3
"""Writes src/content/microphone-quality-spectrum-analyzer.json."""
import json
import os

BASE = os.path.dirname(os.path.abspath(__file__))
CONTENT_DIR = os.path.normpath(os.path.join(BASE, "..", "..", "src", "content"))

MIC_ICON = '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M12 1a3 3 0 0 0-3 3v8a3 3 0 0 0 6 0V4a3 3 0 0 0-3-3z"/><path d="M19 10v2a7 7 0 0 1-14 0v-2M12 19v3M8 22h8" stroke-linecap="round"/></svg>'
GAUGE_ICON = '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M12 20a8 8 0 1 0-8-8" stroke-linecap="round"/><path d="M12 12l4-4" stroke-linecap="round"/><path d="M2 12h2M12 2v2M20 12h2"/></svg>'
INFO_ICON = '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="10"/><path d="M12 16v-4M12 8h.01" stroke-linecap="round"/></svg>'
DOT_ICON = '<svg viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="9"/></svg>'

FIELDS_HTML = f'''<div class="tool-panel primary">
  <div class="panel-header">
    <span class="panel-icon">{MIC_ICON}</span>
    <div><h2>Microphone Quality &amp; Spectrum</h2><p class="panel-sub">Live frequency spectrum, logarithmic axis (20 Hz – ~20 kHz)</p></div>
  </div>
  <canvas class="waveform-canvas" id="spectrumCanvas" style="height:180px"></canvas>
  <div style="display:flex;justify-content:space-between;font-size:.68rem;color:var(--text-muted);font-family:var(--font-mono);margin-top:.3rem">
    <span>20 Hz</span><span>200 Hz</span><span>2 kHz</span><span>20 kHz</span>
  </div>
  <div class="media-controls" style="margin-top:1rem">
    <button type="button" class="btn-primary" id="btnStartMic">Start Microphone</button>
    <button type="button" class="btn-secondary" id="btnStopMic" disabled>Stop Microphone</button>
    <select class="device-select" id="deviceSelect" aria-label="Select microphone" disabled>
      <option value="">Default microphone</option>
    </select>
  </div>
  <div class="diagnostic-panel" id="diagnosticPanel" style="margin-top:1rem">
    <div class="diagnostic-item" id="diagDefault"><span class="diag-icon">{DOT_ICON}</span><span>Click <strong>Start Microphone</strong> and allow access when your browser asks.</span></div>
  </div>
</div>
<div class="tool-panel">
  <div class="panel-header">
    <span class="panel-icon">{GAUGE_ICON}</span>
    <div><h2>Readings</h2></div>
  </div>
  <div class="stat-grid">
    <div class="stat-tile highlight"><span class="stat-value" id="statDominant">—</span><span class="stat-label">Dominant Frequency</span></div>
    <div class="stat-tile"><span class="stat-value" id="statNoiseFloor">—</span><span class="stat-label">Noise Floor</span></div>
    <div class="stat-tile"><span class="stat-value" id="statHum">—</span><span class="stat-label">Mains Hum</span></div>
    <div class="stat-tile"><span class="stat-value" id="statSampleRate">—</span><span class="stat-label">Sample Rate</span></div>
  </div>
  <button type="button" class="btn-secondary" id="btnMeasureFloor" disabled style="width:100%">Measure Noise Floor (2s)</button>
  <p class="field-note">Stay silent for 2 seconds while measuring — this captures your room's background noise level for comparison.</p>
</div>
<div class="tool-panel">
  <div class="panel-header">
    <span class="panel-icon">{INFO_ICON}</span>
    <div><h2>Why Processing Is Disabled</h2></div>
  </div>
  <p class="field-note" style="margin-top:0">This test deliberately requests your microphone with echo cancellation, noise suppression and automatic gain control all turned <strong>off</strong>. Those features are on by default in most calling apps, but they actively reshape the frequency spectrum — leaving them on here would measure your browser's processing, not your microphone.</p>
  <p class="field-note">Mains hum shows up as a spike at exactly 50 Hz (most of the world) or 60 Hz (North America and parts of Asia) — usually from a nearby power supply, unshielded cable, or ground loop.</p>
</div>'''

SCRIPT = r'''(function () {
  'use strict';

  var canvas = document.getElementById('spectrumCanvas');
  var canvasCtx = canvas.getContext('2d');
  var deviceSelect = document.getElementById('deviceSelect');
  var btnStart = document.getElementById('btnStartMic');
  var btnStop = document.getElementById('btnStopMic');
  var btnMeasureFloor = document.getElementById('btnMeasureFloor');
  var diagnosticPanel = document.getElementById('diagnosticPanel');
  var statDominant = document.getElementById('statDominant');
  var statNoiseFloor = document.getElementById('statNoiseFloor');
  var statHum = document.getElementById('statHum');
  var statSampleRate = document.getElementById('statSampleRate');

  var currentStream = null;
  var audioCtx = null;
  var analyser = null;
  var freqData = null;
  var peakHold = null;
  var rafId = null;
  var starting = false;
  var measuringFloor = false;
  var minFreq = 20, maxFreq = 20000;

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

  function resizeCanvas() {
    var rect = canvas.getBoundingClientRect();
    var dpr = window.devicePixelRatio || 1;
    canvas.width = Math.max(1, Math.round(rect.width * dpr));
    canvas.height = Math.max(1, Math.round(rect.height * dpr));
  }

  // Maps a pixel column to a frequency bin on a LOGARITHMIC axis -- a
  // linear axis compresses everything below 1 kHz (where most speech and
  // instrument fundamentals live) into an unreadable sliver, per this
  // tool's own spec note.
  function binForColumn(x, w, sampleRate) {
    var frac = x / w;
    var freq = minFreq * Math.pow(maxFreq / minFreq, frac);
    var bin = Math.round((freq / (sampleRate / 2)) * analyser.frequencyBinCount);
    return Math.max(0, Math.min(analyser.frequencyBinCount - 1, bin));
  }

  function drawFrame() {
    rafId = requestAnimationFrame(drawFrame);
    if (!analyser) return;
    analyser.getByteFrequencyData(freqData);

    var w = canvas.width, h = canvas.height;
    canvasCtx.clearRect(0, 0, w, h);

    var sampleRate = audioCtx.sampleRate;
    var maxVal = 0, maxBin = 0;
    for (var i = 0; i < freqData.length; i++) {
      if (freqData[i] > maxVal) { maxVal = freqData[i]; maxBin = i; }
    }

    var barCount = Math.max(1, Math.round(w / 3));
    var barWidth = w / barCount;
    for (var b = 0; b < barCount; b++) {
      var x = b * barWidth;
      var bin = binForColumn(x, w, sampleRate);
      var value = freqData[bin] / 255;
      var barH = value * h;
      canvasCtx.fillStyle = '#7c5cff';
      canvasCtx.fillRect(x, h - barH, Math.max(1, barWidth - 1), barH);

      if (!peakHold || peakHold.length !== barCount) peakHold = new Array(barCount).fill(0);
      if (value > peakHold[b]) peakHold[b] = value;
      else peakHold[b] = Math.max(0, peakHold[b] - 0.004);
      var peakY = h - peakHold[b] * h;
      canvasCtx.fillStyle = 'rgba(124,92,255,.55)';
      canvasCtx.fillRect(x, peakY, Math.max(1, barWidth - 1), 2);
    }

    if (maxVal > 10) {
      var dominantHz = Math.round((maxBin * (sampleRate / 2)) / analyser.frequencyBinCount);
      statDominant.textContent = dominantHz >= 1000 ? (dominantHz / 1000).toFixed(2) + ' kHz' : dominantHz + ' Hz';
    }

    // Mains hum: compare magnitude right at 50/60 Hz against the
    // surrounding noise floor -- a genuine hum spike stands out sharply
    // from nearby bins, unlike broadband noise.
    var hum50 = binMagnitude(50, sampleRate), hum60 = binMagnitude(60, sampleRate);
    var neighborhood = binMagnitude(150, sampleRate) + 15;
    if (hum50 > neighborhood && hum50 >= hum60) {
      statHum.textContent = '50 Hz detected';
    } else if (hum60 > neighborhood) {
      statHum.textContent = '60 Hz detected';
    } else {
      statHum.textContent = 'None detected';
    }
  }

  function binMagnitude(freq, sampleRate) {
    var bin = Math.round((freq / (sampleRate / 2)) * analyser.frequencyBinCount);
    bin = Math.max(0, Math.min(analyser.frequencyBinCount - 1, bin));
    return freqData[bin];
  }

  // Deliberately timer-driven, not requestAnimationFrame -- this is a
  // background measurement, not a rendering task, and rAF is fully
  // suspended whenever the tab isn't visible. A user briefly switching tabs
  // mid-measurement would otherwise leave this permanently stuck.
  function measureNoiseFloor() {
    if (!analyser || measuringFloor) return;
    measuringFloor = true;
    btnMeasureFloor.disabled = true;
    var samples = [];
    var intervalId = setInterval(function () {
      analyser.getByteFrequencyData(freqData);
      var sum = 0;
      for (var i = 0; i < freqData.length; i++) sum += freqData[i];
      samples.push(sum / freqData.length);
    }, 50);
    setTimeout(function () {
      clearInterval(intervalId);
      var avg = samples.reduce(function (a, b) { return a + b; }, 0) / samples.length;
      var db = avg > 0 ? Math.round(20 * Math.log10(avg / 255)) : -60;
      statNoiseFloor.textContent = db + ' dB';
      measuringFloor = false;
      btnMeasureFloor.disabled = false;
    }, 2000);
  }

  // Same overall stopStream() shape as microphone-test-online's own script
  // (see this project's CLAUDE.md) -- audio teardown additionally closes
  // the AudioContext.
  function stopStream() {
    if (rafId) { cancelAnimationFrame(rafId); rafId = null; }
    if (currentStream) {
      currentStream.getTracks().forEach(function (t) { t.stop(); });
      currentStream = null;
    }
    if (audioCtx) {
      audioCtx.close().catch(function () {});
      audioCtx = null;
    }
    analyser = null;
    peakHold = null;
    canvasCtx.clearRect(0, 0, canvas.width, canvas.height);
    btnStop.disabled = true;
    btnMeasureFloor.disabled = true;
    statDominant.textContent = '—';
    statNoiseFloor.textContent = '—';
    statHum.textContent = '—';
    statSampleRate.textContent = '—';
  }

  function describeError(err) {
    switch (err && err.name) {
      case 'NotAllowedError':
      case 'PermissionDeniedError':
        return { sev: 'error', html: '<strong>Microphone access was blocked.</strong> Allow access from your browser’s address-bar icon or site settings, then try again.' };
      case 'NotFoundError':
      case 'DevicesNotFoundError':
        return { sev: 'error', html: '<strong>No microphone was detected.</strong> Connect a microphone and reload this page.' };
      case 'NotReadableError':
      case 'TrackStartError':
        return { sev: 'error', html: '<strong>Your microphone is already in use</strong> by another app or browser tab.' };
      case 'OverconstrainedError':
        return { sev: 'error', html: '<strong>This microphone doesn’t support the requested settings.</strong> Try another microphone from the list.' };
      case 'SecurityError':
        return { sev: 'error', html: '<strong>Microphone access requires HTTPS.</strong>' };
      default:
        return { sev: 'error', html: '<strong>Something went wrong starting the microphone.</strong> ' + escapeHtml((err && err.message) || 'Unknown error') + '.' };
    }
  }

  function populateDeviceSelect(devices, currentDeviceId) {
    var mics = devices.filter(function (d) { return d.kind === 'audioinput'; });
    deviceSelect.innerHTML = '';
    mics.forEach(function (d, i) {
      var opt = document.createElement('option');
      opt.value = d.deviceId;
      opt.textContent = d.label || ('Microphone ' + (i + 1));
      if (d.deviceId === currentDeviceId) opt.selected = true;
      deviceSelect.appendChild(opt);
    });
    deviceSelect.disabled = mics.length === 0;
  }

  function startMic(deviceId) {
    if (starting) return;
    starting = true;
    stopStream();
    resizeCanvas();
    setDiagnostic([{ sev: '', html: 'Requesting microphone access…' }]);
    btnStart.disabled = true;

    // echoCancellation/noiseSuppression/autoGainControl are ON by default
    // and will actively distort the spectrum -- disabling them is the one
    // thing that makes this measurement meaningful, per this tool's own
    // spec note.
    var constraints = {
      audio: {
        deviceId: deviceId ? { exact: deviceId } : undefined,
        echoCancellation: false,
        noiseSuppression: false,
        autoGainControl: false,
      },
    };

    navigator.mediaDevices.getUserMedia(constraints)
      .then(function (stream) {
        currentStream = stream;
        audioCtx = new (window.AudioContext || window.webkitAudioContext)();
        var source = audioCtx.createMediaStreamSource(stream);
        analyser = audioCtx.createAnalyser();
        analyser.fftSize = 2048;
        analyser.smoothingTimeConstant = 0.7;
        freqData = new Uint8Array(analyser.frequencyBinCount);
        source.connect(analyser);

        var track = stream.getAudioTracks()[0];
        var settings = track.getSettings ? track.getSettings() : {};
        statSampleRate.textContent = Math.round(audioCtx.sampleRate) + ' Hz';
        btnStop.disabled = false;
        btnMeasureFloor.disabled = false;
        setDiagnostic([{ sev: 'ok', html: '<strong>Microphone is live.</strong> Make some noise to see the spectrum respond, or stay silent and measure your noise floor.' }]);
        drawFrame();

        return navigator.mediaDevices.enumerateDevices().then(function (devices) {
          populateDeviceSelect(devices, settings.deviceId);
        });
      })
      .catch(function (err) { setDiagnostic([describeError(err)]); stopStream(); })
      .finally(function () { starting = false; btnStart.disabled = false; });
  }

  btnStart.addEventListener('click', function () { startMic(deviceSelect.value); });
  btnStop.addEventListener('click', function () {
    stopStream();
    setDiagnostic([{ sev: '', html: 'Microphone stopped.' }]);
  });
  deviceSelect.addEventListener('change', function () { if (currentStream) startMic(deviceSelect.value); });
  btnMeasureFloor.addEventListener('click', measureNoiseFloor);

  window.addEventListener('resize', resizeCanvas);
  window.addEventListener('pagehide', stopStream);
  document.addEventListener('visibilitychange', function () {
    if (document.visibilityState === 'hidden') stopStream();
  });

  resizeCanvas();

  if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) {
    setDiagnostic([{ sev: 'error', html: '<strong>Your browser doesn’t support microphone access.</strong>' }]);
    btnStart.disabled = true;
  }
})();'''

CONTENT_HTML = '''<p>This tool shows what your microphone is actually picking up across the full audible spectrum — frequency response gaps, background hum, and noise you may not consciously notice while just listening.</p>
<h2>Why the frequency axis is logarithmic</h2>
<p>Human hearing itself works on a roughly logarithmic scale — the octave from 100 Hz to 200 Hz sounds like the same-sized musical jump as 5,000 Hz to 10,000 Hz, even though the second span covers far more raw frequency. A linear axis would squeeze everything below 1 kHz — where most speech and instrument fundamentals actually live — into an unreadable sliver on the left edge. This spectrum stretches that region out proportionally instead.</p>
<h2>Why processing is turned off for this test specifically</h2>
<p>Every other microphone tool on this site uses your browser's default audio processing, which is what you want for judging how you'll actually sound on a call. This test is different: it explicitly disables echo cancellation, noise suppression and automatic gain control, because all three actively reshape the frequency spectrum before you ever see it — leaving them on would show you your browser's processing chain, not your microphone's real response.</p>
<h2>Reading the spectrum</h2>
<p>The bright purple bars show the current spectrum; the lighter line above each bar is a decaying peak hold, so brief spikes stay visible for a moment instead of flickering past. The dominant frequency reading tracks whichever bin currently has the strongest energy. Mains hum detection compares the exact 50 Hz and 60 Hz bins against their surroundings — a genuine hum problem produces a sharp, narrow spike that stands out clearly from broadband background noise.</p>'''

FAQ = [
    {"question": "Why does the tool disable echo cancellation and noise suppression?", "answer": "Those processing features are on by default in almost every browser and calling app, but they actively reshape the frequency spectrum before you see it. This test turns them off specifically so the spectrum reflects your actual microphone and room, not your browser's processing."},
    {"question": "What does mains hum at 50 Hz vs 60 Hz mean?", "answer": "It usually points to nearby electrical interference — from a power supply, an unshielded cable, or a ground loop. 50 Hz is the mains frequency across most of the world; 60 Hz is used in North America and parts of Asia. Which one shows up can hint at what kind of device nearby might be the source."},
    {"question": "How do I measure my noise floor accurately?", "answer": "Click \"Measure Noise Floor\" and stay completely silent — no talking, typing, or moving anything near the microphone — for the full 2 seconds. This captures your room's background noise level as a baseline for comparison."},
    {"question": "Is any audio recorded or uploaded during this test?", "answer": "No. The microphone's audio is analysed in real time entirely in your browser and never recorded, stored, or sent anywhere."},
]

TOOL = {
    "slug": "microphone-quality-spectrum-analyzer",
    "meta_title": "Microphone Quality & Spectrum Analyzer — Live Frequency Test | WebcamTest",
    "meta_description": "See your microphone's live frequency spectrum with a logarithmic axis, peak hold, dominant frequency, noise floor measurement and mains hum detection at 50/60 Hz.",
    "h1": "Microphone Quality and Spectrum",
    "subtitle": "A live frequency spectrum of your microphone with processing disabled, so you see the real response — not your browser's.",
    "card": {
        "layout": "raw",
        "fields_html": FIELDS_HTML,
    },
    "script": SCRIPT,
    "content_html": CONTENT_HTML,
    "faq": FAQ,
}

if __name__ == "__main__":
    out_path = os.path.join(CONTENT_DIR, "microphone-quality-spectrum-analyzer.json")
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(TOOL, f, indent=2, ensure_ascii=False)
    print("Wrote", out_path)
