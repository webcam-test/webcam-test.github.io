#!/usr/bin/env python3
"""Writes src/content/audio-frequency-sweep-20hz-20khz.json."""
import json
import os

BASE = os.path.dirname(os.path.abspath(__file__))
CONTENT_DIR = os.path.normpath(os.path.join(BASE, "..", "..", "src", "content"))

SPEAKER_ICON = '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M11 5L6 9H2v6h4l5 4V5z"/><path d="M15.5 8.5a5 5 0 0 1 0 7" stroke-linecap="round"/></svg>'
WARN_ICON = '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M12 9v4M12 17h.01M10.3 3.9L1.8 18a2 2 0 0 0 1.7 3h17a2 2 0 0 0 1.7-3L13.7 3.9a2 2 0 0 0-3.4 0z" stroke-linecap="round" stroke-linejoin="round"/></svg>'
DOT_ICON = '<svg viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="9"/></svg>'

FIELDS_HTML = f'''<div class="tool-panel primary">
  <div class="panel-header">
    <span class="panel-icon">{SPEAKER_ICON}</span>
    <div><h2>Frequency Sweep Test</h2><p class="panel-sub">Sweeps 20 Hz to 20 kHz to reveal dropouts, rattles and resonances</p></div>
  </div>
  <div style="text-align:center;padding:1.5rem 0">
    <div id="freqReadout" style="font-family:var(--font-mono);font-weight:700;font-size:2.4rem;color:var(--accent-light)">—</div>
    <div class="level-meter" style="max-width:420px;margin:1rem auto 0">
      <div class="level-meter-fill" id="sweepProgressFill" style="width:0%"></div>
    </div>
  </div>
  <div class="tool-actions" style="justify-content:center">
    <button type="button" class="btn-primary" id="btnStartSweep">Start Sweep</button>
    <button type="button" class="btn-secondary" id="btnPauseSweep" disabled>Pause</button>
    <button type="button" class="btn-secondary" id="btnStopSweep" disabled>Stop</button>
  </div>
  <div class="diagnostic-panel" id="diagnosticPanel" style="margin-top:1rem">
    <div class="diagnostic-item sev-warn" id="diagDefault"><span class="diag-icon">{WARN_ICON}</span><span><strong>Turn your volume down before starting.</strong> A sweep played at high volume can damage tweeters and small speakers — start quiet and raise it gradually if needed.</span></div>
  </div>
</div>
<div class="tool-panel">
  <div class="panel-header">
    <span class="panel-icon"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M4 14a1 1 0 0 1-.78-1.63l9.9-10.2a.5.5 0 0 1 .86.46l-1.92 6.02A1 1 0 0 0 13 10h7a1 1 0 0 1 .78 1.63l-9.9 10.2a.5.5 0 0 1-.86-.46l1.92-6.02A1 1 0 0 0 11 14H4z"/></svg></span>
    <div><h2>Sweep Settings</h2></div>
  </div>
  <div class="tool-field slider-field">
    <label for="durationSlider">Sweep Duration</label>
    <div class="slider-row">
      <input type="range" id="durationSlider" min="5" max="30" value="15" step="1">
      <span class="slider-value" id="durationValue">15 s</span>
    </div>
  </div>
  <div class="tool-field slider-field" style="margin-bottom:0">
    <label for="volumeSlider">Volume</label>
    <div class="slider-row">
      <input type="range" id="volumeSlider" min="0" max="100" value="30">
      <span class="slider-value" id="volumeValue">30%</span>
    </div>
  </div>
</div>
<div class="tool-panel">
  <div class="panel-header">
    <span class="panel-icon"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="3"/><path d="M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 1 1-2.83 2.83l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 0 1-4 0v-.09A1.65 1.65 0 0 0 9 19.4a1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 1 1-2.83-2.83l.06-.06a1.65 1.65 0 0 0 .33-1.82 1.65 1.65 0 0 0-1.51-1H3a2 2 0 0 1 0-4h.09A1.65 1.65 0 0 0 4.6 9a1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 1 1 2.83-2.83l.06.06a1.65 1.65 0 0 0 1.82.33H9a1.65 1.65 0 0 0 1-1.51V3a2 2 0 0 1 4 0v.09a1.65 1.65 0 0 0 1 1.51 1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 1 1 2.83 2.83l-.06.06a1.65 1.65 0 0 0-.33 1.82V9a1.65 1.65 0 0 0 1.51 1H21a2 2 0 0 1 0 4h-.09a1.65 1.65 0 0 0-1.51 1z"/></svg></span>
    <div><h2>Jump to a Frequency</h2><p class="panel-sub">Report an exact frequency where you hear a problem</p></div>
  </div>
  <div class="tool-field slider-field" style="margin-bottom:0">
    <label for="manualFreqSlider">Manual Frequency</label>
    <div class="slider-row">
      <input type="range" id="manualFreqSlider" min="0" max="1000" value="500">
      <span class="slider-value" id="manualFreqValue">1000 Hz</span>
    </div>
  </div>
  <p class="field-note">Dragging this plays a steady tone at that exact frequency — pauses the sweep automatically.</p>
</div>'''

SCRIPT = r'''(function () {
  'use strict';

  var btnStart = document.getElementById('btnStartSweep');
  var btnPause = document.getElementById('btnPauseSweep');
  var btnStop = document.getElementById('btnStopSweep');
  var freqReadout = document.getElementById('freqReadout');
  var progressFill = document.getElementById('sweepProgressFill');
  var diagnosticPanel = document.getElementById('diagnosticPanel');
  var durationSlider = document.getElementById('durationSlider');
  var durationValue = document.getElementById('durationValue');
  var volumeSlider = document.getElementById('volumeSlider');
  var volumeValue = document.getElementById('volumeValue');
  var manualFreqSlider = document.getElementById('manualFreqSlider');
  var manualFreqValue = document.getElementById('manualFreqValue');

  var MAX_GAIN = 0.3; // conservative ceiling -- see this site's safety notes for playback tools; a sweep can be uncomfortable/damaging at full volume
  var MIN_FREQ = 20, MAX_FREQ = 20000;

  var audioCtx = null;
  var oscillator = null;
  var gainNode = null;
  var tickIntervalId = null;
  var sweeping = false;
  var paused = false;
  var elapsed = 0; // seconds of sweep progress
  var lastTick = 0;

  function setDiagnostic(sev, html) {
    diagnosticPanel.innerHTML = '<div class="diagnostic-item' + (sev ? ' sev-' + sev : '') + '"><span class="diag-icon">' +
      '<svg viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="9"/></svg>' +
      '</span><span>' + html + '</span></div>';
  }

  function ensureContext() {
    if (!audioCtx) {
      audioCtx = new (window.AudioContext || window.webkitAudioContext)();
      oscillator = audioCtx.createOscillator();
      gainNode = audioCtx.createGain();
      oscillator.type = 'sine';
      oscillator.frequency.value = MIN_FREQ;
      gainNode.gain.value = 0;
      oscillator.connect(gainNode);
      gainNode.connect(audioCtx.destination);
      oscillator.start();
    }
    return audioCtx.resume().catch(function () {});
  }

  function currentGainTarget() {
    return (parseFloat(volumeSlider.value) / 100) * MAX_GAIN;
  }

  function formatFreq(hz) {
    return hz >= 1000 ? (hz / 1000).toFixed(2) + ' kHz' : Math.round(hz) + ' Hz';
  }

  // Exponential ramp, not linear -- a linear sweep from 20-20000 Hz spends
  // almost its entire duration above 10 kHz and blows through the whole
  // musically/audibly relevant range in the first fraction of a second,
  // per this tool's own spec note.
  function freqAtElapsed(t, duration) {
    var frac = Math.max(0, Math.min(1, t / duration));
    return MIN_FREQ * Math.pow(MAX_FREQ / MIN_FREQ, frac);
  }

  // Timer-driven, not requestAnimationFrame -- this updates the oscillator's
  // actual frequency (an audible side effect the visitor may be listening
  // to), not just an on-screen readout, and rAF is fully suspended whenever
  // the tab isn't visible. A user briefly switching tabs mid-sweep should
  // still hear it continue and finish on schedule.
  function tick() {
    if (!sweeping || paused) return;
    var now = performance.now();
    if (!lastTick) lastTick = now;
    var dt = (now - lastTick) / 1000;
    lastTick = now;
    var duration = parseFloat(durationSlider.value);
    elapsed += dt;
    if (elapsed >= duration) {
      elapsed = duration;
      var freq = freqAtElapsed(elapsed, duration);
      oscillator.frequency.setValueAtTime(freq, audioCtx.currentTime);
      freqReadout.textContent = formatFreq(freq);
      progressFill.style.width = '100%';
      finishSweep();
      return;
    }
    var freqNow = freqAtElapsed(elapsed, duration);
    oscillator.frequency.setValueAtTime(freqNow, audioCtx.currentTime);
    freqReadout.textContent = formatFreq(freqNow);
    progressFill.style.width = Math.round((elapsed / duration) * 100) + '%';
  }

  function finishSweep() {
    sweeping = false;
    stopTickLoop();
    rampGainTo(0);
    btnStart.textContent = 'Start Sweep';
    btnPause.disabled = true;
    btnStop.disabled = true;
    setDiagnostic('ok', '<strong>Sweep finished.</strong> Note the frequency shown if you heard a dropout, rattle or resonance, and use the manual slider to zero in on it.');
  }

  function rampGainTo(target) {
    if (!gainNode || !audioCtx) return;
    var now = audioCtx.currentTime;
    gainNode.gain.cancelScheduledValues(now);
    gainNode.gain.setValueAtTime(gainNode.gain.value, now);
    gainNode.gain.linearRampToValueAtTime(target, now + 0.05);
  }

  function startTickLoop() {
    if (tickIntervalId) clearInterval(tickIntervalId);
    tickIntervalId = setInterval(tick, 30);
  }
  function stopTickLoop() {
    if (tickIntervalId) { clearInterval(tickIntervalId); tickIntervalId = null; }
  }

  function startSweep() {
    ensureContext().then(function () {
      elapsed = 0;
      lastTick = 0;
      sweeping = true;
      paused = false;
      rampGainTo(currentGainTarget());
      btnStart.textContent = 'Restart Sweep';
      btnPause.disabled = false;
      btnPause.textContent = 'Pause';
      btnStop.disabled = false;
      setDiagnostic('ok', '<strong>Sweeping…</strong> Listen for any point where the tone drops out, rattles, or seems to resonate unusually loud.');
      startTickLoop();
    });
  }

  function togglePause() {
    if (!sweeping) return;
    paused = !paused;
    btnPause.textContent = paused ? 'Resume' : 'Pause';
    if (paused) {
      rampGainTo(0);
    } else {
      lastTick = 0;
      rampGainTo(currentGainTarget());
      startTickLoop();
    }
  }

  function stopSweep() {
    sweeping = false;
    paused = false;
    stopTickLoop();
    rampGainTo(0);
    progressFill.style.width = '0%';
    freqReadout.textContent = '—';
    btnStart.textContent = 'Start Sweep';
    btnPause.disabled = true;
    btnStop.disabled = true;
    setDiagnostic('', 'Stopped.');
  }

  function playManualFrequency() {
    ensureContext().then(function () {
      sweeping = false;
      paused = false;
      btnPause.disabled = true;
      btnStop.disabled = false;
      var pct = parseFloat(manualFreqSlider.value) / 1000;
      var freq = MIN_FREQ * Math.pow(MAX_FREQ / MIN_FREQ, pct);
      oscillator.frequency.setValueAtTime(freq, audioCtx.currentTime);
      manualFreqValue.textContent = formatFreq(freq);
      freqReadout.textContent = formatFreq(freq);
      rampGainTo(currentGainTarget());
      setDiagnostic('ok', '<strong>Playing ' + formatFreq(freq) + ' steadily.</strong> Click Stop when done.');
    });
  }

  btnStart.addEventListener('click', startSweep);
  btnPause.addEventListener('click', togglePause);
  btnStop.addEventListener('click', stopSweep);

  durationSlider.addEventListener('input', function () {
    durationValue.textContent = durationSlider.value + ' s';
  });
  volumeSlider.addEventListener('input', function () {
    volumeValue.textContent = volumeSlider.value + '%';
    if (sweeping && !paused) rampGainTo(currentGainTarget());
  });
  manualFreqSlider.addEventListener('input', function () {
    var pct = parseFloat(manualFreqSlider.value) / 1000;
    var freq = MIN_FREQ * Math.pow(MAX_FREQ / MIN_FREQ, pct);
    manualFreqValue.textContent = formatFreq(freq);
  });
  manualFreqSlider.addEventListener('change', playManualFrequency);
  manualFreqSlider.dispatchEvent(new Event('input'));

  window.addEventListener('pagehide', function () {
    sweeping = false;
    stopTickLoop();
    if (audioCtx) { audioCtx.close().catch(function () {}); audioCtx = null; }
  });
  document.addEventListener('visibilitychange', function () {
    // Silence (rather than let it keep sweeping unheard) when the tab is
    // hidden -- a diagnostic tone playing on unattended, especially at the
    // high-frequency end, isn't something to leave running invisibly.
    if (document.visibilityState === 'hidden') {
      sweeping = false;
      stopTickLoop();
      if (gainNode && audioCtx) rampGainTo(0);
    }
  });

  if (!(window.AudioContext || window.webkitAudioContext)) {
    setDiagnostic('error', '<strong>Your browser doesn’t support the Web Audio API.</strong>');
    btnStart.disabled = true;
  }
})();'''

CONTENT_HTML = '''<p>This tool sweeps a single continuous tone from 20 Hz up to 20 kHz — the full range of human hearing — to reveal problems a normal listening session might never surface: a dropout at a specific frequency, a rattle from a loose speaker component, or a resonance that makes one narrow band sound unnaturally loud.</p>
<h2>Turn your volume down first</h2>
<p>A frequency sweep played at high volume can genuinely damage tweeters and small speaker drivers, especially at the high end of the range. Start quiet, confirm the sweep is audible and comfortable, and only raise the volume gradually if you need to.</p>
<h2>Why the sweep speeds up as it gets higher</h2>
<p>The sweep moves exponentially, not linearly — each octave (a doubling of frequency) takes the same amount of time, rather than each fixed number of hertz taking the same time. A linear sweep from 20 Hz to 20,000 Hz would spend the overwhelming majority of its duration above 10 kHz and blast through the entire musically relevant range in a fraction of a second; the exponential approach gives every part of the audible spectrum a fair, comparable amount of listening time.</p>
<h2>Reporting a problem frequency</h2>
<p>If you hear something odd during the sweep — a dropout, a buzz, an unusually loud resonance — note roughly where the live frequency readout was, then use the manual frequency slider afterward to dial in on that exact spot and confirm it repeatably. That's a much more useful thing to report to a manufacturer or include in a review than "somewhere in the middle."</p>'''

FAQ = [
    {"question": "Is it safe to run this at full volume?", "answer": "No — start at a low volume. A frequency sweep, especially the high-frequency end, can damage tweeters and small speaker drivers if played too loud. Raise the volume gradually only if needed."},
    {"question": "Why does the sweep seem to spend more time on low frequencies?", "answer": "The sweep moves exponentially so that each octave gets equal time, rather than linearly by raw hertz. Without this, the sweep would race through almost the entire audible range in the blink of an eye — see the explanation above."},
    {"question": "I heard a dropout but missed the exact frequency — what do I do?", "answer": "Use the manual frequency slider to play a steady tone and sweep it slowly around where you think the problem was, watching the live frequency readout until you reproduce the issue."},
    {"question": "Does this test my microphone too?", "answer": "No — this is a playback-only test of your speakers or headphones. For a microphone frequency test, see the Microphone Quality and Spectrum tool instead."},
]

TOOL = {
    "slug": "audio-frequency-sweep-20hz-20khz",
    "meta_title": "Frequency Sweep Test 20Hz–20kHz — Test Your Speakers Online | WebcamTest",
    "meta_description": "Sweep a tone from 20 Hz to 20 kHz to find dropouts, rattles and resonances in your speakers or headphones. Adjustable duration, pause control, and manual frequency selection.",
    "h1": "Frequency Sweep Test",
    "subtitle": "Sweeps 20 Hz to 20 kHz to reveal speaker or headphone dropouts, rattles and resonances — with a live frequency readout.",
    "card": {
        "layout": "raw",
        "fields_html": FIELDS_HTML,
    },
    "script": SCRIPT,
    "content_html": CONTENT_HTML,
    "faq": FAQ,
}

if __name__ == "__main__":
    out_path = os.path.join(CONTENT_DIR, "audio-frequency-sweep-20hz-20khz.json")
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(TOOL, f, indent=2, ensure_ascii=False)
    print("Wrote", out_path)
