#!/usr/bin/env python3
"""Writes src/content/microphone-input-level-meter.json. Throwaway authoring
script, same pattern as write_webcam_test_online.py — see this project's
CLAUDE.md 'Authoring a new tool's content file'.

Deliberately differentiated from the already-built microphone-test-online
(which shows a waveform + a single peak-hold-of-RMS meter): this tool shows
TRUE instantaneous peak and RMS/average as two separate meters (the spec's
own "peak and average" wording, and the only way clipping is detectable at
all -- RMS never approaches 0dBFS even while clipping), adds a visual
"recommended band" target zone on both meters, a clipping-event counter,
and a raw-audio toggle (disables autoGainControl/echoCancellation/
noiseSuppression) that microphone-test-online doesn't have."""
import json
import os

BASE = os.path.dirname(os.path.abspath(__file__))
CONTENT_DIR = os.path.normpath(os.path.join(BASE, "..", "..", "src", "content"))

MIC_ICON = '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M12 1a3 3 0 0 0-3 3v8a3 3 0 0 0 6 0V4a3 3 0 0 0-3-3z"/><path d="M19 10v2a7 7 0 0 1-14 0v-2M12 19v3M8 22h8" stroke-linecap="round"/></svg>'
INFO_ICON = '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="10"/><path d="M12 16v-4M12 8h.01" stroke-linecap="round"/></svg>'
WARN_ICON = '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M12 9v4M12 17h.01M10.29 3.86 1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z" stroke-linecap="round" stroke-linejoin="round"/></svg>'
DOT_ICON = '<svg viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="9"/></svg>'

FIELDS_HTML = f'''<div class="tool-panel primary">
  <div class="panel-header">
    <span class="panel-icon">{MIC_ICON}</span>
    <div><h2>Level Meter</h2><p class="panel-sub">Speak normally and watch both meters — aim to stay inside the shaded band</p></div>
  </div>
  <div class="level-meter-label"><span>Peak</span><strong id="peakReadout">— dB</strong></div>
  <div class="level-meter"><div class="level-meter-fill" id="peakFill"></div><div class="level-meter-band" id="peakBand"></div><div class="level-meter-peak" id="peakHoldTick" style="left:0%"></div></div>
  <div class="level-meter-scale" style="margin-bottom:1rem"><span>−60 dB</span><span>−40 dB</span><span>−20 dB</span><span>0 dB</span></div>
  <div class="level-meter-label"><span>Average (RMS)</span><strong id="rmsReadout">— dB</strong></div>
  <div class="level-meter"><div class="level-meter-fill" id="rmsFill"></div><div class="level-meter-band" id="rmsBand"></div></div>
  <div class="level-meter-scale">
    <span>−60 dB</span><span>−40 dB</span><span>−20 dB</span><span>0 dB</span>
  </div>
  <div class="media-controls" style="margin-top:1rem">
    <button type="button" class="btn-primary" id="btnStartMic">Start Microphone</button>
    <button type="button" class="btn-secondary" id="btnStopMic" disabled>Stop Microphone</button>
    <select class="device-select" id="deviceSelect" aria-label="Select microphone" disabled>
      <option value="">Default microphone</option>
    </select>
  </div>
  <label style="display:flex;align-items:center;gap:.5rem;font-size:.85rem;color:var(--text-secondary);margin-top:.75rem">
    <input type="checkbox" id="checkRawAudio"> Disable browser audio processing (auto gain, echo cancellation, noise suppression)
  </label>
</div>
<div class="tool-panel">
  <div class="panel-header">
    <span class="panel-icon">{INFO_ICON}</span>
    <div><h2>Level Report</h2><p class="panel-sub">Reported once the microphone is live</p></div>
  </div>
  <div class="stat-grid">
    <div class="stat-tile"><span class="stat-value" id="statPeak">—</span><span class="stat-label">Peak</span></div>
    <div class="stat-tile"><span class="stat-value" id="statRms">—</span><span class="stat-label">Average (RMS)</span></div>
    <div class="stat-tile"><span class="stat-value" id="statClips">0</span><span class="stat-label">Clipping Events</span></div>
    <div class="stat-tile"><span class="stat-value" style="font-size:.85rem">−18 to −6 dB</span><span class="stat-label">Recommended Band</span></div>
  </div>
  <p class="field-note">Auto gain control actively fights manual gain adjustments on your mixer or OS input slider — turn off browser audio processing above if your levels seem to "correct themselves" no matter what you change.</p>
</div>
<div class="tool-panel">
  <div class="panel-header">
    <span class="panel-icon">{WARN_ICON}</span>
    <div><h2>Status</h2><p class="panel-sub">What to do if the microphone won't start</p></div>
  </div>
  <div class="diagnostic-panel" id="diagnosticPanel">
    <div class="diagnostic-item"><span class="diag-icon">{DOT_ICON}</span><span>Click <strong>Start Microphone</strong> and allow access when your browser asks.</span></div>
  </div>
</div>'''

SCRIPT = '''(function () {
  'use strict';

  var deviceSelect = document.getElementById('deviceSelect');
  var btnStart = document.getElementById('btnStartMic');
  var btnStop = document.getElementById('btnStopMic');
  var checkRawAudio = document.getElementById('checkRawAudio');
  var diagnosticPanel = document.getElementById('diagnosticPanel');
  var peakFill = document.getElementById('peakFill');
  var peakHoldTick = document.getElementById('peakHoldTick');
  var peakBand = document.getElementById('peakBand');
  var peakReadout = document.getElementById('peakReadout');
  var rmsFill = document.getElementById('rmsFill');
  var rmsBand = document.getElementById('rmsBand');
  var rmsReadout = document.getElementById('rmsReadout');
  var statPeak = document.getElementById('statPeak');
  var statRms = document.getElementById('statRms');
  var statClips = document.getElementById('statClips');

  var currentStream = null;
  var currentDeviceId = '';
  var starting = false;
  var audioCtx = null;
  var analyser = null;
  var source = null;
  var rafId = null;
  var peakHoldDb = -60;
  var peakHoldUntil = 0;
  var clipCount = 0;
  var lastClipTime = 0;

  var MIN_DB = -60;
  // -18 to -6 dBFS is a widely used conversational-speech target band for
  // a mic level meter -- loud enough to sit well above the noise floor,
  // with headroom before clipping.
  var BAND_LOW = -18, BAND_HIGH = -6;
  // Anything within 1dB of full scale counts as clipping for this meter's
  // purposes -- true 0dBFS is vanishingly rare to land on exactly.
  var CLIP_THRESHOLD_DB = -1;

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

  function dbToPct(db) {
    var pct = ((db - MIN_DB) / (0 - MIN_DB)) * 100;
    return Math.max(0, Math.min(100, pct));
  }

  function positionBand(bandEl) {
    var left = dbToPct(BAND_LOW);
    var right = dbToPct(BAND_HIGH);
    bandEl.style.left = left + '%';
    bandEl.style.width = (right - left) + '%';
  }
  positionBand(peakBand);
  positionBand(rmsBand);

  function resetMeters() {
    peakFill.style.width = '0%';
    peakHoldTick.style.left = '0%';
    rmsFill.style.width = '0%';
    peakReadout.textContent = '\\u2014 dB';
    rmsReadout.textContent = '\\u2014 dB';
    statPeak.textContent = '\\u2014';
    statRms.textContent = '\\u2014';
    peakHoldDb = MIN_DB;
    peakHoldUntil = 0;
  }

  function stopAnalysis() {
    if (rafId) { cancelAnimationFrame(rafId); rafId = null; }
    if (source) { try { source.disconnect(); } catch (e) {} source = null; }
    if (analyser) { analyser = null; }
    if (audioCtx) { audioCtx.close().catch(function () {}); audioCtx = null; }
  }

  // Every camera/mic page on this site copies this stopStream()/error
  // pattern from webcam-test-online.json (see this project's own
  // CLAUDE.md). This tool additionally tears down the AnalyserNode/
  // AudioContext and cancels the meter's rAF loop -- never left running
  // against a closed context.
  function stopStream() {
    stopAnalysis();
    if (currentStream) {
      currentStream.getTracks().forEach(function (t) { t.stop(); });
      currentStream = null;
    }
    btnStop.disabled = true;
    resetMeters();
  }

  function describeError(err) {
    switch (err && err.name) {
      case 'NotAllowedError':
      case 'PermissionDeniedError':
        return { sev: 'error', html: '<strong>Microphone access was blocked.</strong> Click the camera icon in your address bar (or your browser\\u2019s site settings) and allow access, then try again.' };
      case 'NotFoundError':
      case 'DevicesNotFoundError':
        return { sev: 'error', html: '<strong>No microphone was detected.</strong> Make sure a microphone is connected, then reload this page.' };
      case 'NotReadableError':
      case 'TrackStartError':
        return { sev: 'error', html: '<strong>Your microphone is already in use.</strong> Another app or browser tab is probably holding it \\u2014 close video-calling apps or other audio tabs and try again.' };
      case 'OverconstrainedError':
      case 'ConstraintNotSatisfiedError':
        return { sev: 'error', html: '<strong>This microphone doesn\\u2019t support the requested settings.</strong> Try a different microphone from the list above.' };
      case 'SecurityError':
        return { sev: 'error', html: '<strong>Microphone access requires a secure connection.</strong> Make sure this page is loaded over HTTPS.' };
      case 'AbortError':
        return { sev: 'warn', html: 'The microphone request was interrupted. Click <strong>Start Microphone</strong> to try again.' };
      default:
        return { sev: 'error', html: '<strong>Something went wrong starting the microphone.</strong> ' + escapeHtml((err && err.message) || 'Unknown error') + '.' };
    }
  }

  function populateDeviceSelect(devices) {
    var mics = devices.filter(function (d) { return d.kind === 'audioinput'; });
    deviceSelect.innerHTML = '';
    if (!mics.length) {
      var opt = document.createElement('option');
      opt.value = '';
      opt.textContent = 'No microphones found';
      deviceSelect.appendChild(opt);
      deviceSelect.disabled = true;
      return;
    }
    mics.forEach(function (d, i) {
      var opt = document.createElement('option');
      opt.value = d.deviceId;
      opt.textContent = d.label || ('Microphone ' + (i + 1));
      if (d.deviceId === currentDeviceId) opt.selected = true;
      deviceSelect.appendChild(opt);
    });
    deviceSelect.disabled = false;
  }

  function refreshDeviceList() {
    if (!navigator.mediaDevices || !navigator.mediaDevices.enumerateDevices) return Promise.resolve();
    return navigator.mediaDevices.enumerateDevices().then(populateDeviceSelect).catch(function () {});
  }

  function drawFrame() {
    rafId = requestAnimationFrame(drawFrame);
    if (!analyser) return;

    var bufferLength = analyser.fftSize;
    var dataArray = new Uint8Array(bufferLength);
    analyser.getByteTimeDomainData(dataArray);

    var sumSquares = 0, peakAbs = 0;
    for (var i = 0; i < bufferLength; i++) {
      var norm = (dataArray[i] - 128) / 128;
      var abs = Math.abs(norm);
      if (abs > peakAbs) peakAbs = abs;
      sumSquares += norm * norm;
    }
    var rms = Math.sqrt(sumSquares / bufferLength);
    var rmsDb = Math.max(MIN_DB, rms > 0 ? 20 * Math.log10(rms) : MIN_DB);
    var peakDb = Math.max(MIN_DB, peakAbs > 0 ? 20 * Math.log10(peakAbs) : MIN_DB);

    rmsFill.style.width = dbToPct(rmsDb) + '%';
    rmsReadout.textContent = Math.round(rmsDb) + ' dB';
    statRms.textContent = Math.round(rmsDb) + ' dB';

    peakFill.style.width = dbToPct(peakDb) + '%';
    peakReadout.textContent = Math.round(peakDb) + ' dB';
    statPeak.textContent = Math.round(peakDb) + ' dB';

    // Hold the peak briefly so short transients (claps, plosives) stay
    // visible instead of flickering past at 60fps, then let it decay.
    var now = performance.now();
    if (peakDb > peakHoldDb) {
      peakHoldDb = peakDb;
      peakHoldUntil = now + 1200;
    } else if (now > peakHoldUntil) {
      peakHoldDb = Math.max(peakDb, peakHoldDb - 0.6, MIN_DB);
    }
    peakHoldTick.style.left = dbToPct(peakHoldDb) + '%';

    if (peakDb >= CLIP_THRESHOLD_DB && now - lastClipTime > 300) {
      clipCount++;
      statClips.textContent = String(clipCount);
      lastClipTime = now;
    }
  }

  function startStream(deviceId) {
    if (starting) return;
    starting = true;
    stopStream();
    clipCount = 0;
    statClips.textContent = '0';
    setDiagnostic([{ sev: '', html: 'Requesting microphone access\\u2026' }]);
    btnStart.disabled = true;

    var rawAudio = checkRawAudio.checked;
    var audioConstraint = {
      autoGainControl: !rawAudio,
      echoCancellation: !rawAudio,
      noiseSuppression: !rawAudio,
    };
    if (deviceId) audioConstraint.deviceId = { exact: deviceId };

    navigator.mediaDevices.getUserMedia({ audio: audioConstraint, video: false })
      .then(function (stream) {
        currentStream = stream;
        var track = stream.getAudioTracks()[0];
        var settings = track.getSettings ? track.getSettings() : {};
        currentDeviceId = settings.deviceId || deviceId || '';

        audioCtx = new (window.AudioContext || window.webkitAudioContext)();
        analyser = audioCtx.createAnalyser();
        analyser.fftSize = 1024;
        source = audioCtx.createMediaStreamSource(stream);
        // Deliberately never connected to audioCtx.destination -- routing
        // a live mic to speakers without a hard opt-in creates a feedback
        // loop (same safety rule as microphone-test-online.json).
        source.connect(analyser);

        btnStop.disabled = false;
        setDiagnostic([{ sev: 'ok', html: '<strong>Microphone is live.</strong> Speak normally and watch the two meters \\u2014 nothing is recorded or uploaded.' }]);
        drawFrame();
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
    setDiagnostic([{ sev: '', html: 'Microphone stopped. Click <strong>Start Microphone</strong> to test again.' }]);
  });
  deviceSelect.addEventListener('change', function () {
    if (currentStream) startStream(deviceSelect.value);
  });
  checkRawAudio.addEventListener('change', function () {
    if (currentStream) startStream(deviceSelect.value);
  });

  // Guaranteed teardown: release the microphone and tear down the audio
  // graph the moment the visitor leaves this page, even if they never
  // clicked Stop.
  window.addEventListener('pagehide', stopStream);
  document.addEventListener('visibilitychange', function () {
    if (document.visibilityState === 'hidden') stopStream();
  });

  if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) {
    setDiagnostic([{ sev: 'error', html: '<strong>Your browser doesn\\u2019t support microphone access.</strong> Try the latest version of Chrome, Firefox, Edge, or Safari.' }]);
    btnStart.disabled = true;
  }
})();'''

CONTENT_HTML = '''<p>WebcamTest's microphone level meter is a focused tool for setting your input gain correctly, showing peak and average (RMS) levels as two separate live meters rather than one blended number. Clipping (input that's too loud, distorting the signal) and input that's too quiet are the two most common call-audio problems, and both are easy to catch here before you're on an actual call.</p>
<h2>Why two meters instead of one</h2>
<p>The <strong>Peak</strong> meter shows the loudest instantaneous sample in each moment — the number that matters for clipping, since a signal only has to touch full scale once to distort. The <strong>Average (RMS)</strong> meter shows the sustained loudness of your voice over time, which is what "does this sound quiet or loud" actually reflects. A voice can have a healthy average level while still occasionally spiking into clipping on louder syllables — watching both at once catches that a single blended meter would hide.</p>
<h2>Reading the recommended band</h2>
<p>The shaded region on each meter, roughly −18 to −6 dBFS, is a widely used target zone for conversational speech: loud enough to sit comfortably above background noise, with enough headroom left before 0 dBFS (full scale, where clipping starts) to absorb louder moments without distorting. Aim to keep your average level inside that band, with peaks that only occasionally poke above it.</p>
<h2>What the clipping counter means</h2>
<p>Every time the peak meter touches within about 1 dB of full scale, this page counts it as a clipping event. Occasional clipping on a single loud word usually isn't a problem, but if the counter climbs steadily while you're speaking normally, your input gain is set too high — lower it in your operating system's sound settings or on your audio interface, rather than just talking more quietly, which makes background noise relatively louder instead.</p>
<h2>Why your levels might seem to "correct themselves"</h2>
<p>Most browsers apply automatic gain control by default, which continuously adjusts your microphone's sensitivity to keep levels roughly consistent — helpful for casual calls, but actively counterproductive when you're trying to manually tune your gain, since it fights your adjustments. Turn on <strong>Disable browser audio processing</strong> above to see your microphone's genuinely raw signal, unprocessed by auto gain, echo cancellation, or noise suppression.</p>'''

FAQ = [
    {"question": "Why do I have both a Peak and an Average meter?", "answer": "Peak shows the loudest instantaneous sample, which is what determines clipping. Average (RMS) shows your voice's sustained loudness over time. A voice can look fine on average while still spiking into clipping on louder syllables — watching both catches problems a single meter would hide."},
    {"question": "What does the clipping counter actually measure?", "answer": "Every time the peak meter comes within about 1 dB of full scale (0 dBFS), it counts as one clipping event. Occasional clipping on a single loud word is usually fine; steadily climbing counts during normal speech mean your input gain is set too high."},
    {"question": "Why should I disable browser audio processing?", "answer": "Automatic gain control continuously adjusts your microphone's sensitivity in the background, which actively fights manual gain changes — turning it off (along with echo cancellation and noise suppression) shows your microphone's true, unprocessed signal, which is what you want to see while you're tuning gain manually."},
    {"question": "Is my audio uploaded or recorded anywhere?", "answer": "No. Levels are computed entirely inside your browser tab from live AnalyserNode data. Nothing is recorded, saved, or sent to WebcamTest's servers or any third party. If you want to actually hear a recording of your voice played back, use the dedicated Microphone Record and Playback tool instead."},
    {"question": "My meters barely move even when I'm speaking loudly — what's wrong?", "answer": "Check that the correct microphone is selected in the device dropdown, that your operating system hasn't muted it or set its input volume to near zero, and that no other application is holding it exclusively. If those all check out, try disabling browser audio processing, since aggressive noise suppression can sometimes suppress genuine speech on certain microphones."},
]

TOOL = {
    "slug": "microphone-input-level-meter",
    "meta_title": "Microphone Level Meter — Set Your Input Gain Correctly | WebcamTest",
    "meta_description": "Free live microphone level meter showing peak and average (RMS) dBFS with a recommended target band and clipping counter. Set your input gain correctly before a call.",
    "h1": "Microphone Level Meter",
    "subtitle": "Set your input gain correctly with separate peak and average meters, a recommended target band, and a clipping counter.",
    "card": {
        "layout": "raw",
        "fields_html": FIELDS_HTML,
    },
    "script": SCRIPT,
    "content_html": CONTENT_HTML,
    "faq": FAQ,
}

if __name__ == "__main__":
    out_path = os.path.join(CONTENT_DIR, "microphone-input-level-meter.json")
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(TOOL, f, indent=2, ensure_ascii=False)
    print("Wrote", out_path)
