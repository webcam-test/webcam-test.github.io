#!/usr/bin/env python3
"""Writes src/content/microphone-test-online.json."""
import json
import os

BASE = os.path.dirname(os.path.abspath(__file__))
CONTENT_DIR = os.path.normpath(os.path.join(BASE, "..", "..", "src", "content"))

MIC_ICON = '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M12 1a3 3 0 0 0-3 3v8a3 3 0 0 0 6 0V4a3 3 0 0 0-3-3z"/><path d="M19 10v2a7 7 0 0 1-14 0v-2M12 19v3M8 22h8" stroke-linecap="round"/></svg>'
INFO_ICON = '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="10"/><path d="M12 16v-4M12 8h.01" stroke-linecap="round"/></svg>'
DOT_ICON = '<svg viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="9"/></svg>'

FIELDS_HTML = f'''<div class="tool-panel primary">
  <div class="panel-header">
    <span class="panel-icon">{MIC_ICON}</span>
    <div><h2>Live Input Meter</h2><p class="panel-sub">Speak, clap, or play music near your microphone to see it respond</p></div>
  </div>
  <canvas class="waveform-canvas" id="waveformCanvas"></canvas>
  <div style="margin-top:1rem">
    <div class="level-meter"><div class="level-meter-fill" id="levelFill"></div><div class="level-meter-peak" id="levelPeak" style="left:0%"></div></div>
    <div class="level-meter-scale"><span>−60 dB</span><span>−40 dB</span><span>−20 dB</span><span>0 dB</span></div>
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
    <span class="panel-icon">{INFO_ICON}</span>
    <div><h2>Microphone Info</h2><p class="panel-sub">Reported once the microphone is live</p></div>
  </div>
  <div class="stat-grid">
    <div class="stat-tile"><span class="stat-value" id="statPeakDb">—</span><span class="stat-label">Peak Level</span></div>
    <div class="stat-tile"><span class="stat-value" id="statSampleRate">—</span><span class="stat-label">Sample Rate</span></div>
    <div class="stat-tile"><span class="stat-value" id="statChannels">—</span><span class="stat-label">Channels</span></div>
    <div class="stat-tile"><span class="stat-value" id="statDeviceName" style="font-size:.75rem;word-break:break-word">—</span><span class="stat-label">Device</span></div>
  </div>
  <p class="field-note">Nothing you say is recorded or uploaded — the meter reads live audio levels only, in your browser.</p>
</div>'''

SCRIPT = r'''(function () {
  'use strict';

  var canvas = document.getElementById('waveformCanvas');
  var canvasCtx = canvas.getContext('2d');
  var levelFill = document.getElementById('levelFill');
  var levelPeak = document.getElementById('levelPeak');
  var deviceSelect = document.getElementById('deviceSelect');
  var btnStart = document.getElementById('btnStartMic');
  var btnStop = document.getElementById('btnStopMic');
  var diagnosticPanel = document.getElementById('diagnosticPanel');
  var statPeakDb = document.getElementById('statPeakDb');
  var statSampleRate = document.getElementById('statSampleRate');
  var statChannels = document.getElementById('statChannels');
  var statDeviceName = document.getElementById('statDeviceName');

  var currentStream = null;
  var audioCtx = null;
  var analyser = null;
  var rafId = null;
  var starting = false;
  var peakDb = -60;
  var peakHoldUntil = 0;
  var peakDisplayPct = 0;

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

  function dbToPct(db) {
    // Map -60dB..0dB onto 0%..100% for the level meter / scale.
    var pct = ((db + 60) / 60) * 100;
    return Math.max(0, Math.min(100, pct));
  }

  function drawFrame() {
    rafId = requestAnimationFrame(drawFrame);
    if (!analyser) return;

    var bufferLength = analyser.fftSize;
    var dataArray = new Uint8Array(bufferLength);
    analyser.getByteTimeDomainData(dataArray);

    // Waveform
    var w = canvas.width, h = canvas.height;
    canvasCtx.clearRect(0, 0, w, h);
    canvasCtx.lineWidth = Math.max(1, w / 400);
    canvasCtx.strokeStyle = '#7c5cff';
    canvasCtx.beginPath();
    var sliceWidth = w / bufferLength;
    var x = 0;
    for (var i = 0; i < bufferLength; i++) {
      var v = dataArray[i] / 128.0;
      var y = (v * h) / 2;
      if (i === 0) canvasCtx.moveTo(x, y); else canvasCtx.lineTo(x, y);
      x += sliceWidth;
    }
    canvasCtx.stroke();

    // RMS -> dBFS, floored at -60dB (silence) rather than -Infinity
    var sumSquares = 0;
    for (var j = 0; j < bufferLength; j++) {
      var norm = (dataArray[j] - 128) / 128;
      sumSquares += norm * norm;
    }
    var rms = Math.sqrt(sumSquares / bufferLength);
    var db = rms > 0 ? 20 * Math.log10(rms) : -60;
    db = Math.max(-60, db);

    var pct = dbToPct(db);
    levelFill.style.width = pct + '%';

    // Hold the peak for ~1.2s so brief transients (claps, plosives) stay
    // visible instead of flickering past at 60fps, then let it decay back
    // down rather than staying stuck forever after a single loud moment.
    var now = performance.now();
    if (db > peakDb) {
      peakDb = db;
      peakHoldUntil = now + 1200;
    } else if (now > peakHoldUntil) {
      peakDb = Math.max(db, peakDb - 0.6, -60);
    }
    peakDisplayPct = dbToPct(peakDb);
    levelPeak.style.left = peakDisplayPct + '%';
    statPeakDb.textContent = Math.round(peakDb) + ' dB';
  }

  // Same overall shape as every camera tool's stopStream() elsewhere on
  // this site (see webcam-test-online / this project's CLAUDE.md) — audio
  // teardown additionally closes the AudioContext, which a camera-only
  // tool never needs to do.
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
    levelFill.style.width = '0%';
    levelPeak.style.left = '0%';
    canvasCtx.clearRect(0, 0, canvas.width, canvas.height);
    btnStop.disabled = true;
    statPeakDb.textContent = '—';
    statSampleRate.textContent = '—';
    statChannels.textContent = '—';
    statDeviceName.textContent = '—';
    peakDb = -60;
    peakHoldUntil = 0;
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

  function startStream(deviceId) {
    if (starting) return;
    starting = true;
    stopStream();
    setDiagnostic([{ sev: '', html: 'Requesting microphone access…' }]);
    btnStart.disabled = true;

    var audioConstraint = deviceId ? { deviceId: { exact: deviceId } } : true;
    navigator.mediaDevices.getUserMedia({ audio: audioConstraint, video: false })
      .then(function (stream) {
        currentStream = stream;
        audioCtx = new (window.AudioContext || window.webkitAudioContext)();
        // AudioContext starts suspended under autoplay policy in some
        // browsers -- resume() here runs inside the click handler chain
        // (a real user gesture), which is what makes resume() reliable.
        return audioCtx.resume().catch(function () {}).then(function () { return stream; });
      })
      .then(function (stream) {
        var source = audioCtx.createMediaStreamSource(stream);
        analyser = audioCtx.createAnalyser();
        analyser.fftSize = 2048;
        analyser.smoothingTimeConstant = 0.4;
        source.connect(analyser);
        // Deliberately NOT connected to audioCtx.destination -- this is a
        // level meter, not a monitor. Routing a live mic to speakers
        // without an explicit opt-in creates a feedback loop; the
        // dedicated echo-test tool handles that case with its own
        // explicit safety gating.

        var track = stream.getAudioTracks()[0];
        var settings = track.getSettings ? track.getSettings() : {};
        statSampleRate.textContent = audioCtx.sampleRate ? (audioCtx.sampleRate + ' Hz') : 'Not reported';
        statChannels.textContent = settings.channelCount || 'Not reported';
        statDeviceName.textContent = track.label || 'Microphone';

        resizeCanvas();
        drawFrame();

        btnStop.disabled = false;
        setDiagnostic([{ sev: 'ok', html: '<strong>Microphone is live.</strong> Speak or make noise to see the meter respond. Nothing is recorded or uploaded.' }]);

        return navigator.mediaDevices.enumerateDevices().then(function (devices) {
          populateDeviceSelect(devices, settings.deviceId);
        });
      })
      .catch(function (err) { setDiagnostic([describeError(err)]); })
      .finally(function () { starting = false; btnStart.disabled = false; });
  }

  btnStart.addEventListener('click', function () { startStream(deviceSelect.value); });
  btnStop.addEventListener('click', function () {
    stopStream();
    setDiagnostic([{ sev: '', html: 'Microphone stopped. Click <strong>Start Microphone</strong> to test again.' }]);
  });
  deviceSelect.addEventListener('change', function () {
    if (currentStream) startStream(deviceSelect.value);
  });
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

CONTENT_HTML = '''<p>The Microphone Test is the audio half of the same pre-call check the Webcam Test covers for video: grant access, watch a live level meter and waveform respond to your voice, switch between connected microphones, and read the sample rate and channel count your browser negotiated — all without recording a single sample.</p>
<h2>How to read the level meter</h2>
<p>The meter is scaled in dBFS (decibels relative to full scale) from −60&nbsp;dB (effectively silent) to 0&nbsp;dB (the loudest a digital signal can represent before clipping). Speaking at a normal conversational volume close to most microphones should land somewhere in the middle of the scale; if your peak level never leaves the far left even while talking directly into the microphone, that's a sign your input gain is set too low. A short marker line holds briefly at your loudest recent moment so short sounds — claps, plosive consonants — don't flash past unseen at 60 frames a second.</p>
<h2>Why this matters more than it seems</h2>
<p>Input that's too quiet forces call software to apply aggressive digital gain, which amplifies background noise along with your voice. Input that's consistently pinned near 0&nbsp;dB is clipping — a form of distortion that can't be fixed after the fact. Both are common, both are easy to miss without a visual meter, and both are usually fixable by adjusting your microphone's input gain in your operating system's sound settings.</p>
<h2>What this test deliberately doesn't do</h2>
<p>This page never plays your microphone's input back through your speakers — doing that without an explicit safety gate creates a feedback loop that can produce a loud, unpleasant squeal on any device with speakers near the microphone. If you want to hear exactly what your microphone sounds like to other people, use a dedicated record-and-playback tool instead, which handles that safely with headphone confirmation built in.</p>'''

FAQ = [
    {"question": "Is my voice recorded or uploaded during this test?", "answer": "No. Audio is analyzed live using the Web Audio API directly in your browser to drive the level meter and waveform. Nothing is recorded, saved, or transmitted anywhere."},
    {"question": "Why doesn't the meter move at all when I talk?", "answer": "Check that the correct microphone is selected in the device dropdown, that your operating system hasn't muted or set that device's input volume to zero, and that no other application is currently holding the microphone exclusively."},
    {"question": "What sample rate should I expect to see?", "answer": "Most built-in and USB microphones report 44,100 Hz or 48,000 Hz, both of which are more than sufficient for voice calls. A much lower reported rate usually just reflects your operating system's current audio device configuration, not a fault with the hardware."},
    {"question": "Why does the meter still move slightly when it's quiet?", "answer": "Microphones pick up genuine ambient noise — room hum, air handling, electrical interference — so a small amount of movement near the low end of the scale with no one speaking is normal, not a malfunction."},
]

TOOL = {
    "slug": "microphone-test-online",
    "meta_title": "Microphone Test — Check Your Mic Online Free | WebcamTest",
    "meta_description": "Test your microphone online for free. See a live level meter and waveform, switch between connected microphones, and check sample rate and channel count. Nothing is recorded.",
    "h1": "Microphone Test",
    "subtitle": "Check that your microphone works with a live level meter and waveform — nothing is recorded or uploaded.",
    "card": {
        "layout": "raw",
        "fields_html": FIELDS_HTML,
    },
    "script": SCRIPT,
    "content_html": CONTENT_HTML,
    "faq": FAQ,
}

if __name__ == "__main__":
    out_path = os.path.join(CONTENT_DIR, "microphone-test-online.json")
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(TOOL, f, indent=2, ensure_ascii=False)
    print("Wrote", out_path)
