#!/usr/bin/env python3
"""Writes src/content/microphone-echo-test.json."""
import json
import os

BASE = os.path.dirname(os.path.abspath(__file__))
CONTENT_DIR = os.path.normpath(os.path.join(BASE, "..", "..", "src", "content"))

MIC_ICON = '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M12 1a3 3 0 0 0-3 3v8a3 3 0 0 0 6 0V4a3 3 0 0 0-3-3z"/><path d="M19 10v2a7 7 0 0 1-14 0v-2M12 19v3M8 22h8" stroke-linecap="round"/></svg>'
WARN_ICON = '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M12 9v4M12 17h.01M10.3 3.9L1.8 18a2 2 0 0 0 1.7 3h17a2 2 0 0 0 1.7-3L13.7 3.9a2 2 0 0 0-3.4 0z" stroke-linecap="round" stroke-linejoin="round"/></svg>'
INFO_ICON = '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="10"/><path d="M12 16v-4M12 8h.01" stroke-linecap="round"/></svg>'
DOT_ICON = '<svg viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="9"/></svg>'

FIELDS_HTML = f'''<div class="tool-panel primary">
  <div class="panel-header">
    <span class="panel-icon">{MIC_ICON}</span>
    <div><h2>Microphone Echo Test</h2><p class="panel-sub">Hear your own voice delayed, the way call participants would</p></div>
  </div>
  <div class="diagnostic-item sev-error" id="headphoneWarning" style="margin-bottom:1.25rem"><span class="diag-icon">{WARN_ICON}</span><span><strong>Headphones required.</strong> This routes your microphone to your speakers with a short delay. Without headphones, your speakers will feed straight back into your microphone and produce a loud, unpleasant squeal. Do not enable this through open speakers.</span></div>
  <div id="preEnableGate">
    <button type="button" class="btn-primary" id="btnConfirmHeadphones" style="width:100%">I'm Wearing Headphones — Enable</button>
  </div>
  <div id="controlsArea" style="display:none">
    <div class="media-controls">
      <select class="device-select" id="deviceSelect" aria-label="Select microphone" disabled>
        <option value="">Default microphone</option>
      </select>
    </div>
    <div class="tool-field slider-field" style="margin-top:1rem">
      <label for="delaySlider">Echo Delay</label>
      <div class="slider-row">
        <input type="range" id="delaySlider" min="100" max="500" value="250" step="10">
        <span class="slider-value" id="delayValue">250 ms</span>
      </div>
    </div>
    <button type="button" class="btn-primary" id="btnKillSwitch" style="width:100%;margin-top:1rem;font-size:1.1rem;padding:1.1rem;background:linear-gradient(135deg,#f87171,#dc2626)">STOP / MUTE NOW</button>
  </div>
  <div class="diagnostic-panel" id="diagnosticPanel" style="margin-top:1rem">
    <div class="diagnostic-item" id="diagDefault"><span class="diag-icon">{DOT_ICON}</span><span>Confirm you're wearing headphones above to begin.</span></div>
  </div>
</div>
<div class="tool-panel">
  <div class="panel-header">
    <span class="panel-icon">{INFO_ICON}</span>
    <div><h2>What This Reveals</h2></div>
  </div>
  <p class="field-note" style="margin-top:0">Hearing your own voice delayed is exactly what call participants experience — it makes room echo, a hollow/distant mic sound, or background noise far more obvious than listening to yourself normally, since we're used to hearing our own voice through bone conduction, not delayed through a speaker.</p>
</div>
<div class="tool-panel">
  <div class="panel-header">
    <span class="panel-icon"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z" stroke-linecap="round" stroke-linejoin="round"/></svg></span>
    <div><h2>Reducing Echo</h2></div>
  </div>
  <p class="field-note" style="margin-top:0">Soft furnishings (curtains, rugs, a couch) absorb reflections that hard-walled rooms bounce around. Moving your microphone closer to your mouth reduces how much room reflection it picks up relative to your direct voice, and pointing it away from bare walls or windows helps too.</p>
</div>'''

SCRIPT = r'''(function () {
  'use strict';

  var preEnableGate = document.getElementById('preEnableGate');
  var controlsArea = document.getElementById('controlsArea');
  var btnConfirmHeadphones = document.getElementById('btnConfirmHeadphones');
  var btnKillSwitch = document.getElementById('btnKillSwitch');
  var deviceSelect = document.getElementById('deviceSelect');
  var delaySlider = document.getElementById('delaySlider');
  var delayValue = document.getElementById('delayValue');
  var diagnosticPanel = document.getElementById('diagnosticPanel');

  var MAX_GAIN = 0.35; // capped -- see this tool's own safety note
  var RAMP_SECONDS = 0.6; // ramps in gradually rather than snapping to full volume

  var currentStream = null;
  var audioCtx = null;
  var sourceNode = null;
  var delayNode = null;
  var gainNode = null;
  var starting = false;

  function escapeHtml(s) {
    var d = document.createElement('div');
    d.textContent = String(s);
    return d.innerHTML;
  }

  function setDiagnostic(sev, html) {
    diagnosticPanel.innerHTML = '<div class="diagnostic-item' + (sev ? ' sev-' + sev : '') + '"><span class="diag-icon">' +
      '<svg viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="9"/></svg>' +
      '</span><span>' + html + '</span></div>';
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

  // SAFETY: this deliberately creates a feedback path (mic -> delay ->
  // speakers). Gated behind an explicit headphone confirmation, gain is
  // capped well below full scale, and it ramps in over half a second
  // rather than snapping on -- all per this tool's own spec note. The
  // kill switch (killAll) is the one control that must always work
  // instantly, with no ramp.
  function startMic(deviceId) {
    if (starting) return;
    starting = true;
    setDiagnostic('', 'Requesting microphone access…');

    navigator.mediaDevices.getUserMedia({ audio: { deviceId: deviceId ? { exact: deviceId } : undefined } })
      .then(function (stream) {
        currentStream = stream;
        audioCtx = new (window.AudioContext || window.webkitAudioContext)();
        sourceNode = audioCtx.createMediaStreamSource(stream);
        delayNode = audioCtx.createDelay(1.0);
        delayNode.delayTime.value = parseFloat(delaySlider.value) / 1000;
        gainNode = audioCtx.createGain();
        gainNode.gain.value = 0;
        sourceNode.connect(delayNode);
        delayNode.connect(gainNode);
        gainNode.connect(audioCtx.destination);

        var now = audioCtx.currentTime;
        gainNode.gain.linearRampToValueAtTime(MAX_GAIN, now + RAMP_SECONDS);

        var track = stream.getAudioTracks()[0];
        var settings = track.getSettings ? track.getSettings() : {};
        setDiagnostic('ok', '<strong>Echo is live.</strong> Speak normally and listen through your headphones. Use the kill switch below the instant you need to stop.');
        return navigator.mediaDevices.enumerateDevices().then(function (devices) {
          populateDeviceSelect(devices, settings.deviceId);
        });
      })
      .catch(function (err) {
        setDiagnostic(describeError(err).sev, describeError(err).html);
        killAll();
      })
      .finally(function () { starting = false; });
  }

  // Always instant, never ramped -- this is the one control that must work
  // immediately under any circumstance, per this tool's own safety note.
  function killAll() {
    if (gainNode && audioCtx) {
      gainNode.gain.cancelScheduledValues(audioCtx.currentTime);
      gainNode.gain.setValueAtTime(0, audioCtx.currentTime);
    }
    if (currentStream) {
      currentStream.getTracks().forEach(function (t) { t.stop(); });
      currentStream = null;
    }
    if (audioCtx) {
      audioCtx.close().catch(function () {});
      audioCtx = null;
    }
    sourceNode = null;
    delayNode = null;
    gainNode = null;
    preEnableGate.style.display = '';
    controlsArea.style.display = 'none';
    setDiagnostic('', 'Stopped. Confirm you\'re wearing headphones to start again.');
  }

  btnConfirmHeadphones.addEventListener('click', function () {
    preEnableGate.style.display = 'none';
    controlsArea.style.display = '';
    startMic(deviceSelect.value);
  });

  btnKillSwitch.addEventListener('click', killAll);

  deviceSelect.addEventListener('change', function () {
    if (audioCtx) {
      killAll();
      preEnableGate.style.display = 'none';
      controlsArea.style.display = '';
      startMic(deviceSelect.value);
    }
  });

  delaySlider.addEventListener('input', function () {
    var ms = parseFloat(delaySlider.value);
    delayValue.textContent = ms + ' ms';
    if (delayNode) delayNode.delayTime.value = ms / 1000;
  });

  window.addEventListener('pagehide', killAll);
  document.addEventListener('visibilitychange', function () {
    if (document.visibilityState === 'hidden') killAll();
  });

  if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) {
    setDiagnostic('error', '<strong>Your browser doesn’t support microphone access.</strong>');
    btnConfirmHeadphones.disabled = true;
  }
})();'''

CONTENT_HTML = '''<p>This tool routes your own microphone to your speakers with a short delay, so you hear your voice roughly the way call participants actually hear it — revealing room echo and microphone positioning problems that are nearly impossible to notice by just listening to yourself normally.</p>
<h2>Why headphones are mandatory, not optional</h2>
<p>Your microphone and speakers being active at the same time is normally something call software works hard to prevent, because a microphone that can hear its own output creates a feedback loop — the classic loud squeal you've probably heard at a live event with a microphone held too close to a speaker. This tool deliberately creates exactly that loop for a moment, delayed, so you can hear yourself as others do. Without headphones, your own speakers' output goes straight back into your microphone, and the delay does nothing to prevent the squeal that causes — it can happen almost instantly and at an uncomfortable volume. Always run this test with headphones on.</p>
<h2>Why your voice sounds so different this way</h2>
<p>You normally hear your own voice through a mix of vibration through your skull bones and the sound reaching your ears through the air — which is why a recording of your own voice always sounds strange the first time you hear it. Hearing yourself purely through a speaker, delayed, strips out the bone-conduction part entirely and adds whatever your room and microphone actually contribute, which is a much closer approximation of what call participants hear.</p>
<h2>Using it to spot problems</h2>
<p>A hollow, distant or echoey quality reveals your microphone is picking up too much room reflection relative to your direct voice — try moving the microphone closer to your mouth, or reducing hard reflective surfaces nearby. Adjust the delay slider if the default timing makes it hard to notice details; a slightly longer delay can make subtle qualities easier to pick out.</p>'''

FAQ = [
    {"question": "Can I use this without headphones if I turn my speaker volume down low?", "answer": "Don't. Even at low volume, a microphone positioned near an active speaker can create feedback, and the exact threshold varies unpredictably by device and positioning. Headphones remove the possibility entirely rather than just reducing the risk, which is why this test requires them."},
    {"question": "What do I do if I hear a squeal starting?", "answer": "Click the large STOP / MUTE NOW button immediately — it cuts the audio instantly with no ramp, unlike the gradual ramp-in used when starting. If for any reason the page becomes unresponsive, closing the browser tab or muting your system volume also stops it immediately."},
    {"question": "Why does the echo ramp in gradually instead of starting immediately?", "answer": "A sudden burst of audio, especially with a live microphone-to-speaker path, is jarring and briefly harder to react to safely. Ramping the volume in over about half a second gives you a moment to react if anything sounds wrong before it reaches full level."},
    {"question": "Is my voice recorded or uploaded during this test?", "answer": "No. Your microphone audio is routed directly to your own speaker output through your browser's audio processing and is never recorded, saved, or sent anywhere."},
]

TOOL = {
    "slug": "microphone-echo-test",
    "meta_title": "Microphone Echo Test — Hear Yourself Like Others Do | WebcamTest",
    "meta_description": "Hear your own microphone delayed through your speakers, the way call participants hear you. Reveals room echo and mic positioning issues. Headphones required.",
    "h1": "Microphone Echo Test",
    "subtitle": "Routes your microphone to your speakers with a short delay so you hear yourself as call participants do — headphones required.",
    "card": {
        "layout": "raw",
        "fields_html": FIELDS_HTML,
    },
    "script": SCRIPT,
    "content_html": CONTENT_HTML,
    "faq": FAQ,
}

if __name__ == "__main__":
    out_path = os.path.join(CONTENT_DIR, "microphone-echo-test.json")
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(TOOL, f, indent=2, ensure_ascii=False)
    print("Wrote", out_path)
