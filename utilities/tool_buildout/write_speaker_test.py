#!/usr/bin/env python3
"""Writes src/content/speaker-test-online.json."""
import json
import os

BASE = os.path.dirname(os.path.abspath(__file__))
CONTENT_DIR = os.path.normpath(os.path.join(BASE, "..", "..", "src", "content"))

SPEAKER_ICON = '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M11 5 6 9H2v6h4l5 4V5z"/><path d="M15.5 8.5a5 5 0 0 1 0 7M19 5a10 10 0 0 1 0 14" stroke-linecap="round"/></svg>'
WARN_ICON = '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M12 9v4M12 17h.01M10.29 3.86 1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z" stroke-linecap="round" stroke-linejoin="round"/></svg>'
DOT_ICON = '<svg viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="9"/></svg>'

FIELDS_HTML = f'''<div class="tool-panel primary">
  <div class="panel-header">
    <span class="panel-icon">{SPEAKER_ICON}</span>
    <div><h2>Test Tones</h2><p class="panel-sub">Confirms audio output is working across the frequency range</p></div>
  </div>
  <div class="media-controls">
    <button type="button" class="btn-primary" id="btnLow">Low (200 Hz)</button>
    <button type="button" class="btn-primary" id="btnMid">Mid (1000 Hz)</button>
    <button type="button" class="btn-primary" id="btnHigh">High (4000 Hz)</button>
    <button type="button" class="btn-secondary" id="btnStop" disabled>Stop</button>
  </div>
  <div class="tool-field slider-field" style="margin-top:1.25rem">
    <label for="volumeSlider">Volume</label>
    <div class="slider-row">
      <input type="range" id="volumeSlider" min="0" max="100" value="35">
      <span class="slider-value" id="volumeValue">35%</span>
    </div>
  </div>
  <div class="media-controls" id="outputSelectRow" style="display:none">
    <select class="device-select" id="outputSelect" aria-label="Select output device"></select>
  </div>
  <div class="diagnostic-panel" id="diagnosticPanel" style="margin-top:1rem">
    <div class="diagnostic-item" id="diagDefault"><span class="diag-icon">{DOT_ICON}</span><span>Start at a low volume, then click a tone button. Nothing plays until you choose one.</span></div>
  </div>
</div>
<div class="tool-panel">
  <div class="panel-header">
    <span class="panel-icon">{WARN_ICON}</span>
    <div><h2>Before You Start</h2></div>
  </div>
  <div class="trust-badges" style="flex-direction:column;align-items:flex-start;gap:.6rem">
    <span class="trust-badge">Volume starts conservative by default</span>
    <span class="trust-badge">Tones ramp in and out — no clicks or pops</span>
    <span class="trust-badge">Nothing plays until you tap a button</span>
  </div>
  <p class="field-note" style="margin-top:1rem">Output device selection (the dropdown above) only appears in browsers that support choosing an output device — mainly Chrome and Edge.</p>
</div>'''

SCRIPT = r'''(function () {
  'use strict';

  var btnLow = document.getElementById('btnLow');
  var btnMid = document.getElementById('btnMid');
  var btnHigh = document.getElementById('btnHigh');
  var btnStop = document.getElementById('btnStop');
  var volumeSlider = document.getElementById('volumeSlider');
  var volumeValue = document.getElementById('volumeValue');
  var outputSelectRow = document.getElementById('outputSelectRow');
  var outputSelect = document.getElementById('outputSelect');
  var diagnosticPanel = document.getElementById('diagnosticPanel');

  var MAX_GAIN = 0.4; // conservative ceiling -- see this site's safety notes for playback tools
  var RAMP_SECONDS = 0.02; // ramp every tone in/out to avoid audible clicks

  var audioCtx = null;
  var oscillator = null;
  var gainNode = null;
  var activeBtn = null;

  function setDiagnostic(items) {
    diagnosticPanel.innerHTML = items.map(function (it) {
      var sevClass = it.sev ? ' sev-' + it.sev : '';
      return '<div class="diagnostic-item' + sevClass + '"><span class="diag-icon">' +
        '<svg viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="9"/></svg>' +
        '</span><span>' + it.html + '</span></div>';
    }).join('');
  }

  function ensureContext() {
    if (!audioCtx) {
      audioCtx = new (window.AudioContext || window.webkitAudioContext)();
    }
    // AudioContext starts suspended under autoplay policy -- this always
    // runs from inside a click handler (a real user gesture), so resume()
    // is reliable here.
    return audioCtx.resume().catch(function () {});
  }

  function currentGainTarget() {
    return (parseFloat(volumeSlider.value) / 100) * MAX_GAIN;
  }

  function stopTone() {
    if (oscillator && gainNode && audioCtx) {
      var now = audioCtx.currentTime;
      gainNode.gain.cancelScheduledValues(now);
      gainNode.gain.setValueAtTime(gainNode.gain.value, now);
      gainNode.gain.linearRampToValueAtTime(0, now + RAMP_SECONDS);
      var osc = oscillator;
      setTimeout(function () {
        try { osc.stop(); osc.disconnect(); } catch (e) {}
      }, RAMP_SECONDS * 1000 + 20);
    }
    oscillator = null;
    gainNode = null;
    if (activeBtn) { activeBtn.classList.remove('active'); activeBtn = null; }
    btnStop.disabled = true;
  }

  function playTone(freq, btn) {
    ensureContext().then(function () {
      stopTone();
      oscillator = audioCtx.createOscillator();
      gainNode = audioCtx.createGain();
      oscillator.type = 'sine';
      oscillator.frequency.value = freq;
      gainNode.gain.value = 0;
      oscillator.connect(gainNode);
      gainNode.connect(audioCtx.destination);
      oscillator.start();
      var now = audioCtx.currentTime;
      gainNode.gain.linearRampToValueAtTime(currentGainTarget(), now + RAMP_SECONDS);

      activeBtn = btn;
      btn.classList.add('active');
      btnStop.disabled = false;
      setDiagnostic([{ sev: 'ok', html: '<strong>Playing ' + freq + ' Hz.</strong> If you hear nothing, check your system volume and that the correct output device is selected in your OS sound settings.' }]);
    });
  }

  btnLow.addEventListener('click', function () { playTone(200, btnLow); });
  btnMid.addEventListener('click', function () { playTone(1000, btnMid); });
  btnHigh.addEventListener('click', function () { playTone(4000, btnHigh); });
  btnStop.addEventListener('click', function () {
    stopTone();
    setDiagnostic([{ sev: '', html: 'Stopped.' }]);
  });

  volumeSlider.addEventListener('input', function () {
    volumeValue.textContent = volumeSlider.value + '%';
    if (gainNode && audioCtx) {
      var now = audioCtx.currentTime;
      gainNode.gain.cancelScheduledValues(now);
      gainNode.gain.setValueAtTime(gainNode.gain.value, now);
      gainNode.gain.linearRampToValueAtTime(currentGainTarget(), now + 0.05);
    }
  });

  // setSinkId on AudioContext is a newer, Chromium-leaning API -- feature-
  // detect rather than assume, and hide the picker entirely when it isn't
  // available instead of shipping a dead dropdown.
  function initOutputDevices() {
    var testCtx = window.AudioContext || window.webkitAudioContext;
    var supportsSinkId = testCtx && 'setSinkId' in testCtx.prototype;
    if (!supportsSinkId || !navigator.mediaDevices || !navigator.mediaDevices.enumerateDevices) return;

    navigator.mediaDevices.enumerateDevices().then(function (devices) {
      var outputs = devices.filter(function (d) { return d.kind === 'audiooutput'; });
      if (!outputs.length) return;
      outputSelectRow.style.display = 'flex';
      outputSelect.innerHTML = outputs.map(function (d, i) {
        return '<option value="' + d.deviceId + '">' + (d.label || ('Output ' + (i + 1))) + '</option>';
      }).join('');
      outputSelect.addEventListener('change', function () {
        ensureContext().then(function () {
          audioCtx.setSinkId(outputSelect.value).catch(function () {
            setDiagnostic([{ sev: 'warn', html: 'Could not switch output device — your browser rejected the request.' }]);
          });
        });
      });
    }).catch(function () {});
  }

  window.addEventListener('pagehide', function () { stopTone(); if (audioCtx) audioCtx.close().catch(function () {}); });
  document.addEventListener('visibilitychange', function () {
    if (document.visibilityState === 'hidden') stopTone();
  });

  initOutputDevices();

  if (!(window.AudioContext || window.webkitAudioContext)) {
    setDiagnostic([{ sev: 'error', html: '<strong>Your browser doesn’t support Web Audio.</strong> Try the latest version of Chrome, Firefox, Edge, or Safari.' }]);
    btnLow.disabled = true;
    btnMid.disabled = true;
    btnHigh.disabled = true;
  }
})();'''

CONTENT_HTML = '''<p>The Speaker Test confirms your computer's audio output is actually working — and reaching the device you expect — before you rely on it for a call or for watching something. Three test tones across the low, mid, and high end of the audible range let you check that your speakers or headphones reproduce sound evenly rather than just "making noise."</p>
<h2>Why three separate tones</h2>
<p>A single tone only tells you that <em>something</em> is producing sound. Testing low (200&nbsp;Hz), mid (1,000&nbsp;Hz), and high (4,000&nbsp;Hz) frequencies separately reveals problems a single tone would hide — a blown tweeter that can't reproduce the high tone, a small laptop speaker that can barely register the low tone, or a general drop in output level that a full-range test signal like music might mask.</p>
<h2>How the tones are generated</h2>
<p>Each tone is a pure sine wave generated directly in your browser using the Web Audio API's oscillator node — nothing is streamed or downloaded. Every tone ramps its volume in and out over a few milliseconds rather than starting and stopping abruptly, which avoids the audible click or pop a sudden on/off transition would otherwise produce.</p>
<h2>Choosing an output device</h2>
<p>Where your browser supports it (mainly Chrome and Edge), a device picker lets you send the test tone to a specific output — useful for confirming a Bluetooth headset, a USB DAC, or a secondary monitor's speakers is actually the device receiving audio, rather than assuming based on your operating system's default.</p>
<h2>If you hear nothing</h2>
<p>Check, in order: your system volume isn't muted, the correct output device is selected in your operating system's sound settings (not just in this page's own picker, which only controls where the browser sends audio, not your OS-level default), and — for Bluetooth devices — that the device is actually connected and not sitting in a paired-but-idle state.</p>'''

FAQ = [
    {"question": "Is it safe to play these tones at full volume?", "answer": "The volume slider is capped at a conservative maximum specifically so this test can't drive your speakers or headphones dangerously loud, but you should still start at a low system volume and increase gradually, especially with headphones or in-ear devices."},
    {"question": "Why is there no output device picker on my browser?", "answer": "Selecting an audio output device from a webpage is a newer capability that is currently mainly supported in Chrome and Edge. Firefox and Safari don't expose it, so the picker is hidden entirely rather than shown as a non-functional control."},
    {"question": "I can hear the mid and low tones but not the high one — is my hearing going?", "answer": "Try this on a different pair of speakers or headphones first. Small laptop speakers and cheap headphones frequently can't reproduce 4,000 Hz cleanly at all, which is a hardware limitation, not necessarily a hearing issue — if you want to check your actual hearing range, use a dedicated hearing test instead."},
    {"question": "Why does the tone fade in and out instead of starting instantly?", "answer": "A tone that starts or stops instantly produces an audible click or pop caused by the sudden jump in the audio waveform. Ramping the volume over a few milliseconds avoids that artifact — you're hearing a cleaner tone as a direct result."},
]

TOOL = {
    "slug": "speaker-test-online",
    "meta_title": "Speaker Test — Check Your Audio Output Online Free | WebcamTest",
    "meta_description": "Test your speakers or headphones online for free with low, mid, and high frequency test tones. Choose your output device, adjust volume safely, and confirm your audio actually works.",
    "h1": "Speaker Test",
    "subtitle": "Play test tones across the low, mid, and high end of the audible range to confirm your speakers or headphones actually work.",
    "card": {
        "layout": "raw",
        "fields_html": FIELDS_HTML,
    },
    "script": SCRIPT,
    "content_html": CONTENT_HTML,
    "faq": FAQ,
}

if __name__ == "__main__":
    out_path = os.path.join(CONTENT_DIR, "speaker-test-online.json")
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(TOOL, f, indent=2, ensure_ascii=False)
    print("Wrote", out_path)
