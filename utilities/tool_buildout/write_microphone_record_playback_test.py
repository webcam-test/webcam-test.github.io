#!/usr/bin/env python3
"""Writes src/content/microphone-record-playback-test.json. Throwaway
authoring script, same pattern as write_webcam_test_online.py — see this
project's CLAUDE.md 'Authoring a new tool's content file'. Reuses
webcam-video-recorder-online.json's MediaRecorder/isTypeSupported pattern
(audio-only mime candidates here), and microphone-input-level-meter.json's
raw-audio constraint (autoGainControl/echoCancellation/noiseSuppression
off) — but as two separate, directly comparable recording slots per the
spec's own explicit "processing on vs. off" comparison-mode ask, rather
than a single toggle."""
import json
import os

BASE = os.path.dirname(os.path.abspath(__file__))
CONTENT_DIR = os.path.normpath(os.path.join(BASE, "..", "..", "src", "content"))

MIC_ICON = '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M12 1a3 3 0 0 0-3 3v8a3 3 0 0 0 6 0V4a3 3 0 0 0-3-3z"/><path d="M19 10v2a7 7 0 0 1-14 0v-2M12 19v3M8 22h8" stroke-linecap="round"/></svg>'
FILM_ICON = '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect x="2" y="3" width="20" height="18" rx="2" ry="2"/><path d="M7 3v18M17 3v18M2 8h5M2 16h5M17 8h5M17 16h5" stroke-linecap="round"/></svg>'
WARN_ICON = '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M12 9v4M12 17h.01M10.29 3.86 1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z" stroke-linecap="round" stroke-linejoin="round"/></svg>'
DOT_ICON = '<svg viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="9"/></svg>'

FIELDS_HTML = f'''<div class="tool-panel primary">
  <div class="panel-header">
    <span class="panel-icon">{MIC_ICON}</span>
    <div><h2>Record a Sample</h2><p class="panel-sub">Record the same few seconds with processing on, then off, and compare</p></div>
  </div>
  <div class="tool-warning" style="margin:0 0 1rem">Use headphones before playing recordings back — playing them through speakers next to an open microphone can cause feedback.</div>
  <div class="media-controls">
    <button type="button" class="btn-secondary" id="btnStartMic">Start Microphone</button>
    <button type="button" class="btn-secondary" id="btnStopMic" disabled>Stop Microphone</button>
    <select class="device-select" id="deviceSelect" aria-label="Select microphone" disabled>
      <option value="">Default microphone</option>
    </select>
  </div>
  <div class="tool-actions">
    <button type="button" class="btn-primary" id="btnRecordProcessed" disabled>Record (Processed)</button>
    <button type="button" class="btn-secondary" id="btnRecordRaw" disabled>Record (Raw)</button>
    <select class="device-select" id="selectDurationCap" aria-label="Recording duration cap" style="max-width:150px" disabled>
      <option value="5" selected>5 second cap</option>
      <option value="10">10 second cap</option>
    </select>
    <span id="recordTimer" style="font-family:var(--font-mono);font-size:.85rem;color:var(--text-secondary)"></span>
  </div>
</div>
<div class="tool-panel">
  <div class="panel-header">
    <span class="panel-icon">{FILM_ICON}</span>
    <div><h2>Compare</h2><p class="panel-sub">Processed applies your browser's default echo cancellation, noise suppression and auto gain; Raw disables all three</p></div>
  </div>
  <p class="field-note" style="margin-top:0">Processed (default)</p>
  <p class="capture-empty" id="processedEmpty">Not recorded yet.</p>
  <audio id="processedPlayback" controls style="display:none;width:100%;margin-bottom:.5rem"></audio>
  <p class="capture-row-meta" id="processedMeta" style="display:none;margin-bottom:1rem"></p>
  <p class="field-note">Raw (unprocessed)</p>
  <p class="capture-empty" id="rawEmpty">Not recorded yet.</p>
  <audio id="rawPlayback" controls style="display:none;width:100%;margin-bottom:.5rem"></audio>
  <p class="capture-row-meta" id="rawMeta" style="display:none"></p>
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
  var btnRecordProcessed = document.getElementById('btnRecordProcessed');
  var btnRecordRaw = document.getElementById('btnRecordRaw');
  var selectDurationCap = document.getElementById('selectDurationCap');
  var recordTimer = document.getElementById('recordTimer');
  var diagnosticPanel = document.getElementById('diagnosticPanel');

  var slots = {
    processed: {
      playback: document.getElementById('processedPlayback'),
      empty: document.getElementById('processedEmpty'),
      meta: document.getElementById('processedMeta'),
      url: null,
    },
    raw: {
      playback: document.getElementById('rawPlayback'),
      empty: document.getElementById('rawEmpty'),
      meta: document.getElementById('rawMeta'),
      url: null,
    },
  };

  var currentStream = null;
  var currentDeviceId = '';
  var starting = false;
  var mediaRecorder = null;
  var recordedChunks = [];
  var recordStartTime = 0;
  var recordTickInterval = null;
  var recordCapTimeout = null;

  // Feature-detected with isTypeSupported rather than assumed -- codec
  // support diverges between Chrome/Edge/Firefox and Safari, same as
  // webcam-video-recorder-online.json's video mime candidate list.
  var MIME_CANDIDATES = ['audio/webm;codecs=opus', 'audio/webm', 'audio/mp4', 'audio/ogg;codecs=opus'];

  function pickMimeType() {
    if (typeof MediaRecorder === 'undefined' || !MediaRecorder.isTypeSupported) return '';
    for (var i = 0; i < MIME_CANDIDATES.length; i++) {
      if (MediaRecorder.isTypeSupported(MIME_CANDIDATES[i])) return MIME_CANDIDATES[i];
    }
    return '';
  }

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

  function formatBytes(n) {
    if (n < 1024) return n + ' B';
    if (n < 1024 * 1024) return (n / 1024).toFixed(1) + ' KB';
    return (n / (1024 * 1024)).toFixed(2) + ' MB';
  }

  function formatSeconds(s) {
    var m = Math.floor(s / 60), rem = Math.floor(s % 60);
    return m + ':' + (rem < 10 ? '0' : '') + rem;
  }

  function clearRecordTimers() {
    if (recordTickInterval) { clearInterval(recordTickInterval); recordTickInterval = null; }
    if (recordCapTimeout) { clearTimeout(recordCapTimeout); recordCapTimeout = null; }
    recordTimer.textContent = '';
  }

  function setRecordButtonsDisabled(disabled) {
    btnRecordProcessed.disabled = disabled || !currentStream;
    btnRecordRaw.disabled = disabled || !currentStream;
  }

  function stopRecordingIfActive() {
    clearRecordTimers();
    if (mediaRecorder && mediaRecorder.state !== 'inactive') mediaRecorder.stop();
  }

  // Every camera/mic page on this site copies this stopStream()/error
  // pattern from webcam-test-online.json (see this project's own
  // CLAUDE.md). This tool additionally stops any in-progress recording
  // first, so the recorder never fires against tracks already released.
  function stopStream() {
    stopRecordingIfActive();
    if (currentStream) {
      currentStream.getTracks().forEach(function (t) { t.stop(); });
      currentStream = null;
    }
    btnStop.disabled = true;
    setRecordButtonsDisabled(true);
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

  function startStream(deviceId) {
    if (starting) return;
    starting = true;
    stopStream();
    setDiagnostic([{ sev: '', html: 'Requesting microphone access\\u2026' }]);
    btnStart.disabled = true;

    var audioConstraint = deviceId ? { deviceId: { exact: deviceId } } : true;
    navigator.mediaDevices.getUserMedia({ audio: audioConstraint, video: false })
      .then(function (stream) {
        currentStream = stream;
        var track = stream.getAudioTracks()[0];
        var settings = track.getSettings ? track.getSettings() : {};
        currentDeviceId = settings.deviceId || deviceId || '';
        btnStop.disabled = false;
        setRecordButtonsDisabled(!pickMimeType());
        if (!pickMimeType()) {
          setDiagnostic([{ sev: 'warn', html: '<strong>Microphone is live,</strong> but this browser doesn\\u2019t support recording (MediaRecorder).' }]);
        } else {
          setDiagnostic([{ sev: 'ok', html: '<strong>Microphone is live.</strong> Record a Processed clip, then a Raw one, and compare.' }]);
        }
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

  function setSlotResult(slotName, blob, mimeType, durationS) {
    var slot = slots[slotName];
    if (slot.url) URL.revokeObjectURL(slot.url);
    slot.url = URL.createObjectURL(blob);
    slot.playback.src = slot.url;
    slot.playback.style.display = 'block';
    slot.empty.style.display = 'none';
    slot.meta.style.display = 'block';
    slot.meta.textContent = formatSeconds(durationS) + ' \\u2014 ' + formatBytes(blob.size) + ' \\u2014 ' + mimeType;
  }

  // Records a fresh, short getUserMedia stream with the given processing
  // constraint rather than reusing the always-on preview stream -- this
  // way the Raw recording genuinely has autoGainControl/echoCancellation/
  // noiseSuppression off at the track level, not just muted in the UI.
  function recordSlot(slotName, rawAudio) {
    if (mediaRecorder && mediaRecorder.state === 'recording') return;
    var mimeType = pickMimeType();
    if (!mimeType) return;
    setRecordButtonsDisabled(true);

    var audioConstraint = {
      autoGainControl: !rawAudio,
      echoCancellation: !rawAudio,
      noiseSuppression: !rawAudio,
    };
    if (currentDeviceId) audioConstraint.deviceId = { exact: currentDeviceId };

    navigator.mediaDevices.getUserMedia({ audio: audioConstraint, video: false })
      .then(function (recordStream) {
        recordedChunks = [];
        mediaRecorder = new MediaRecorder(recordStream, { mimeType: mimeType });
        var capSeconds = parseInt(selectDurationCap.value, 10) || 5;
        recordStartTime = Date.now();

        mediaRecorder.addEventListener('dataavailable', function (e) {
          if (e.data && e.data.size > 0) recordedChunks.push(e.data);
        });
        mediaRecorder.addEventListener('stop', function () {
          clearRecordTimers();
          // This recording's own dedicated stream is always released here
          // -- it's separate from currentStream (the always-on preview),
          // which stopStream() governs independently.
          recordStream.getTracks().forEach(function (t) { t.stop(); });
          var elapsedS = (Date.now() - recordStartTime) / 1000;
          if (recordedChunks.length) {
            var blob = new Blob(recordedChunks, { type: mimeType });
            setSlotResult(slotName, blob, mimeType, elapsedS);
            setDiagnostic([{ sev: 'ok', html: '<strong>' + (rawAudio ? 'Raw' : 'Processed') + ' recording saved.</strong> Record the other one to compare, or play both back with headphones.' }]);
          }
          recordedChunks = [];
          setRecordButtonsDisabled(false);
        });

        mediaRecorder.start();
        setDiagnostic([{ sev: '', html: '<span class="recording-dot"></span> Recording (' + (rawAudio ? 'raw' : 'processed') + ')\\u2026' }]);
        recordTickInterval = setInterval(function () {
          var elapsed = (Date.now() - recordStartTime) / 1000;
          recordTimer.textContent = formatSeconds(elapsed) + ' / ' + formatSeconds(capSeconds);
        }, 250);
        recordCapTimeout = setTimeout(function () {
          if (mediaRecorder && mediaRecorder.state === 'recording') mediaRecorder.stop();
        }, capSeconds * 1000);
      })
      .catch(function (err) {
        setDiagnostic([describeError(err)]);
        setRecordButtonsDisabled(false);
      });
  }

  btnStart.addEventListener('click', function () { startStream(deviceSelect.value); });
  btnStop.addEventListener('click', function () {
    stopStream();
    setDiagnostic([{ sev: '', html: 'Microphone stopped. Click <strong>Start Microphone</strong> to test again.' }]);
  });
  btnRecordProcessed.addEventListener('click', function () { recordSlot('processed', false); });
  btnRecordRaw.addEventListener('click', function () { recordSlot('raw', true); });
  deviceSelect.addEventListener('change', function () {
    if (currentStream) startStream(deviceSelect.value);
  });

  // Guaranteed teardown: release the microphone, stop any in-progress
  // recording, and revoke both recordings' object URLs the moment the
  // visitor leaves this page.
  window.addEventListener('pagehide', function () {
    stopStream();
    Object.keys(slots).forEach(function (name) {
      if (slots[name].url) { URL.revokeObjectURL(slots[name].url); slots[name].url = null; }
    });
  });
  document.addEventListener('visibilitychange', function () {
    if (document.visibilityState === 'hidden') stopStream();
  });

  if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) {
    setDiagnostic([{ sev: 'error', html: '<strong>Your browser doesn\\u2019t support microphone access.</strong> Try the latest version of Chrome, Firefox, Edge, or Safari.' }]);
    btnStart.disabled = true;
  } else if (typeof MediaRecorder === 'undefined') {
    setDiagnostic([{ sev: 'warn', html: 'Your browser supports microphone access but not recording (MediaRecorder). This tool needs recording to work.' }]);
  }
})();'''

CONTENT_HTML = '''<p>WebcamTest's microphone record and playback tool records a short sample and plays it back, so you hear exactly what other people on a call actually hear — something a level meter alone can never reveal. A meter can confirm your microphone is picking up sound, but tone, room echo, background hiss, and handling noise are only obvious once you actually listen back.</p>
<h2>Why there are two separate recordings</h2>
<p>Browsers apply audio processing to your microphone by default — echo cancellation, noise suppression, and automatic gain control — and the effect can be dramatic. This page lets you record the same few seconds twice: once <strong>Processed</strong>, with your browser's default processing active, and once <strong>Raw</strong>, with all three explicitly disabled at the microphone level. Playing both back one after another makes the difference immediate rather than theoretical.</p>
<h2>What to listen for</h2>
<p>The Processed recording is usually cleaner-sounding in a quiet room — less background hiss, steadier volume. The Raw recording usually sounds more natural and "present," at the cost of picking up more room noise and any inconsistency in your speaking volume. Neither is objectively better; which one call software should use depends on your environment and microphone. If your voice sounds noticeably thin, distant, or artifacted in the Processed recording, your browser's default processing may be working against a genuinely decent microphone.</p>
<h2>Use headphones for playback</h2>
<p>Play these recordings back through headphones rather than speakers sitting near an open microphone — otherwise the microphone can pick the played-back audio straight back up, creating an audible feedback loop or an unwanted echo in your next recording attempt.</p>
<h2>Nothing is uploaded</h2>
<p>Both recordings exist only in this browser tab's memory as local object URLs, generated with the standard MediaRecorder API. Neither is ever sent to WebcamTest's servers or any third party. Recording a new clip in the same slot replaces the previous one and releases its memory.</p>'''

FAQ = [
    {"question": "Why do I need two recordings instead of one?", "answer": "Browsers apply audio processing (echo cancellation, noise suppression, automatic gain control) by default, and its effect on how you sound can be significant. Recording the same moment both Processed (default) and Raw (all three disabled) lets you hear that difference directly instead of guessing."},
    {"question": "Which one should I actually use for calls?", "answer": "Neither is objectively better — it depends on your microphone and environment. Processed audio tends to sound cleaner in noisy or echo-prone rooms; Raw audio tends to sound more natural with a good microphone in a quiet, well-treated space. Listen to both and judge for your own setup."},
    {"question": "Why do you warn about headphones?", "answer": "Playing a recording back through speakers that sit near an open, live microphone can cause the microphone to pick the played-back audio straight back up — creating audible feedback or contaminating your next recording with an echo of the previous one. Headphones avoid this entirely."},
    {"question": "Is either recording uploaded anywhere?", "answer": "No. Both recordings are created and stored entirely in your browser tab's memory using the standard MediaRecorder API and local object URLs. Neither is ever sent to WebcamTest's servers or any third party."},
    {"question": "Can I keep both recordings and record again later?", "answer": "Recording again in either slot (Processed or Raw) replaces that slot's previous clip and releases its memory — download anything you want to keep before re-recording that slot."},
]

TOOL = {
    "slug": "microphone-record-playback-test",
    "meta_title": "Microphone Record & Playback Test — Hear How You Sound | WebcamTest",
    "meta_description": "Record a short sample from your microphone and play it back, with a side-by-side comparison of processed vs. raw (unprocessed) audio. Free, nothing uploaded.",
    "h1": "Microphone Record & Playback Test",
    "subtitle": "Record a short sample and hear exactly how you sound — with a direct comparison of processed vs. raw audio.",
    "card": {
        "layout": "raw",
        "fields_html": FIELDS_HTML,
    },
    "script": SCRIPT,
    "content_html": CONTENT_HTML,
    "faq": FAQ,
}

if __name__ == "__main__":
    out_path = os.path.join(CONTENT_DIR, "microphone-record-playback-test.json")
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(TOOL, f, indent=2, ensure_ascii=False)
    print("Wrote", out_path)
