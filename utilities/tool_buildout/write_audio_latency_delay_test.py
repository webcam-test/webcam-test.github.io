#!/usr/bin/env python3
"""Writes src/content/audio-latency-delay-test.json."""
import json
import os

BASE = os.path.dirname(os.path.abspath(__file__))
CONTENT_DIR = os.path.normpath(os.path.join(BASE, "..", "..", "src", "content"))

SPEAKER_ICON = '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M11 5L6 9H2v6h4l5 4V5z"/><path d="M15.5 8.5a5 5 0 0 1 0 7" stroke-linecap="round"/></svg>'
GAUGE_ICON = '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M12 20a8 8 0 1 0-8-8" stroke-linecap="round"/><path d="M12 12l4-4" stroke-linecap="round"/><path d="M2 12h2M12 2v2M20 12h2"/></svg>'
INFO_ICON = '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="10"/><path d="M12 16v-4M12 8h.01" stroke-linecap="round"/></svg>'
DOT_ICON = '<svg viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="9"/></svg>'

FIELDS_HTML = f'''<div class="tool-panel primary">
  <div class="panel-header">
    <span class="panel-icon">{SPEAKER_ICON}</span>
    <div><h2>Audio Latency Test</h2><p class="panel-sub">Click "I Heard It" the instant you hear each tone — 8 trials, averaged</p></div>
  </div>
  <div style="text-align:center;padding:1.5rem 0">
    <div id="trialReadout" style="font-family:var(--font-mono);font-weight:700;font-size:1.3rem;color:var(--text-secondary)">Trial 0 of 8</div>
    <div class="level-meter" style="max-width:420px;margin:1rem auto 0">
      <div class="level-meter-fill" id="trialProgressFill" style="width:0%"></div>
    </div>
  </div>
  <div class="tool-actions" style="justify-content:center">
    <button type="button" class="btn-primary" id="btnStartTest">Start Test</button>
    <button type="button" class="btn-secondary" id="btnHeardIt" disabled>I Heard It!</button>
  </div>
  <div class="diagnostic-panel" id="diagnosticPanel" style="margin-top:1rem">
    <div class="diagnostic-item" id="diagDefault"><span class="diag-icon">{DOT_ICON}</span><span>Click <strong>Start Test</strong>, then tap <strong>I Heard It!</strong> the instant each tone plays. Tones play at random intervals so you can't anticipate them.</span></div>
  </div>
</div>
<div class="tool-panel">
  <div class="panel-header">
    <span class="panel-icon">{GAUGE_ICON}</span>
    <div><h2>Result</h2></div>
  </div>
  <div class="stat-grid">
    <div class="stat-tile highlight"><span class="stat-value" id="statEstimate">—</span><span class="stat-label">Estimated Latency Range</span></div>
    <div class="stat-tile"><span class="stat-value" id="statHardware">—</span><span class="stat-label">Hardware-Reported (base+output)</span></div>
  </div>
  <p class="field-note">This is a range, not a precise figure — see why alongside this.</p>
</div>
<div class="tool-panel">
  <div class="panel-header">
    <span class="panel-icon">{INFO_ICON}</span>
    <div><h2>What This Actually Measures</h2></div>
  </div>
  <p class="field-note" style="margin-top:0">Every click you make measures <strong>your reaction time plus audio latency combined</strong> — a browser can't separate the two. This test subtracts a typical average human auditory reaction time (~190 ms) from your average, and reports the result as a range to reflect that real uncertainty, rather than a falsely precise single number.</p>
  <p class="field-note" style="margin-bottom:0">Where your browser reports it, <code>AudioContext.baseLatency</code> and <code>outputLatency</code> give a partial, hardware-only figure alongside your reaction-based estimate — useful context, though it doesn't capture your full output device chain (e.g. Bluetooth's own added delay).</p>
</div>'''

SCRIPT = r'''(function () {
  'use strict';

  var btnStartTest = document.getElementById('btnStartTest');
  var btnHeardIt = document.getElementById('btnHeardIt');
  var trialReadout = document.getElementById('trialReadout');
  var trialProgressFill = document.getElementById('trialProgressFill');
  var diagnosticPanel = document.getElementById('diagnosticPanel');
  var statEstimate = document.getElementById('statEstimate');
  var statHardware = document.getElementById('statHardware');

  var TRIAL_COUNT = 8;
  var MAX_GAIN = 0.4;
  var AVG_HUMAN_REACTION_MS = 190; // typical average human auditory reaction time, subtracted from the raw measurement

  var audioCtx = null;
  var running = false;
  var trialIndex = 0;
  var results = [];
  var toneStartTime = null;
  var waitingForTone = false;
  var toneTimeoutId = null;

  function setDiagnostic(sev, html) {
    diagnosticPanel.innerHTML = '<div class="diagnostic-item' + (sev ? ' sev-' + sev : '') + '"><span class="diag-icon">' +
      '<svg viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="9"/></svg>' +
      '</span><span>' + html + '</span></div>';
  }

  function ensureContext() {
    if (!audioCtx) audioCtx = new (window.AudioContext || window.webkitAudioContext)();
    return audioCtx.resume().catch(function () {});
  }

  function reportHardwareLatency() {
    if (!audioCtx) return;
    var parts = [];
    if (typeof audioCtx.baseLatency === 'number') parts.push('base ' + Math.round(audioCtx.baseLatency * 1000) + ' ms');
    if (typeof audioCtx.outputLatency === 'number') parts.push('output ' + Math.round(audioCtx.outputLatency * 1000) + ' ms');
    statHardware.textContent = parts.length ? parts.join(', ') : 'Not reported';
  }

  function playTone() {
    ensureContext().then(function () {
      reportHardwareLatency();
      var osc = audioCtx.createOscillator();
      var gain = audioCtx.createGain();
      osc.type = 'sine';
      osc.frequency.value = 880;
      gain.gain.value = 0;
      osc.connect(gain);
      gain.connect(audioCtx.destination);
      osc.start();
      var now = audioCtx.currentTime;
      gain.gain.linearRampToValueAtTime(MAX_GAIN, now + 0.01);
      gain.gain.setValueAtTime(MAX_GAIN, now + 0.15);
      gain.gain.linearRampToValueAtTime(0, now + 0.18);
      setTimeout(function () { try { osc.stop(); osc.disconnect(); gain.disconnect(); } catch (e) {} }, 250);

      toneStartTime = performance.now();
      waitingForTone = true;
      btnHeardIt.disabled = false;
      // A trial with no click within 1.5s is treated as missed and discarded
      // rather than left hanging indefinitely.
      toneTimeoutId = setTimeout(function () {
        if (waitingForTone) {
          waitingForTone = false;
          btnHeardIt.disabled = true;
          nextTrial();
        }
      }, 1500);
    });
  }

  function scheduleTrial() {
    trialIndex++;
    trialReadout.textContent = 'Trial ' + trialIndex + ' of ' + TRIAL_COUNT;
    trialProgressFill.style.width = Math.round(((trialIndex - 1) / TRIAL_COUNT) * 100) + '%';
    setDiagnostic('', 'Get ready…');
    // Random 1-3s wait before each tone so the visitor can't anticipate the
    // exact timing, per this tool's own spec note.
    var wait = 1000 + Math.random() * 2000;
    setTimeout(function () {
      if (running) playTone();
    }, wait);
  }

  function nextTrial() {
    if (trialIndex >= TRIAL_COUNT) {
      finishTest();
    } else {
      scheduleTrial();
    }
  }

  function finishTest() {
    running = false;
    trialProgressFill.style.width = '100%';
    btnStartTest.disabled = false;
    btnStartTest.textContent = 'Run Test Again';
    btnHeardIt.disabled = true;

    if (results.length < 3) {
      setDiagnostic('warn', '<strong>Not enough valid trials to estimate.</strong> Try again and click as soon as you hear each tone.');
      statEstimate.textContent = 'Inconclusive';
      return;
    }

    // Discard outliers (implausibly fast/slow) before averaging, per this
    // tool's own spec note ("discard outliers, report a range").
    var sorted = results.slice().sort(function (a, b) { return a - b; });
    var filtered = sorted.filter(function (v) { return v > 80 && v < 1200; });
    var mean = filtered.reduce(function (a, b) { return a + b; }, 0) / filtered.length;
    var estimate = Math.max(0, Math.round(mean - AVG_HUMAN_REACTION_MS));
    var spread = Math.round((filtered[filtered.length - 1] - filtered[0]) / 2) || 15;
    var low = Math.max(0, estimate - spread);
    var high = estimate + spread;

    statEstimate.textContent = low + '–' + high + ' ms';
    setDiagnostic('ok', '<strong>Estimated audio latency: ' + low + '–' + high + ' ms.</strong> This range already accounts for typical human reaction time (~190 ms), subtracted from your raw average of ' + Math.round(mean) + ' ms across ' + filtered.length + ' valid trials.');
  }

  function startTest() {
    if (running) return;
    running = true;
    trialIndex = 0;
    results = [];
    btnStartTest.disabled = true;
    btnStartTest.textContent = 'Testing…';
    trialProgressFill.style.width = '0%';
    scheduleTrial();
  }

  btnStartTest.addEventListener('click', startTest);
  btnHeardIt.addEventListener('click', function () {
    if (!waitingForTone) return;
    waitingForTone = false;
    if (toneTimeoutId) clearTimeout(toneTimeoutId);
    var reaction = performance.now() - toneStartTime;
    results.push(reaction);
    btnHeardIt.disabled = true;
    nextTrial();
  });

  window.addEventListener('pagehide', function () {
    running = false;
    if (audioCtx) { audioCtx.close().catch(function () {}); audioCtx = null; }
  });
  document.addEventListener('visibilitychange', function () {
    if (document.visibilityState === 'hidden') running = false;
  });

  if (!(window.AudioContext || window.webkitAudioContext)) {
    setDiagnostic('error', '<strong>Your browser doesn’t support the Web Audio API.</strong>');
    btnStartTest.disabled = true;
  }
})();'''

CONTENT_HTML = '''<p>Audio latency — the delay between something being scheduled to play and it actually reaching your ears — is the usual cause of lip-sync problems on Bluetooth headphones and video calls. This tool gives you a rough, honestly-framed estimate of it.</p>
<h2>Why this can only ever be an estimate</h2>
<p>Measuring audio latency accurately requires either specialised hardware or precise timestamp access a browser simply doesn't have. What this test can measure is how quickly you personally click after hearing a tone — but that number is <em>your reaction time plus the actual audio latency added together</em>, and a web page has no way to cleanly separate the two. This test handles that honestly by subtracting a typical average human auditory reaction time (around 190 milliseconds, a commonly cited figure from reaction-time research) from your measured average, and reporting the result as a range rather than a single falsely precise number.</p>
<h2>Why the tones play at random intervals</h2>
<p>If tones played on a predictable schedule, you'd naturally start anticipating them and clicking based on rhythm rather than genuinely reacting to the sound — which would measure your sense of timing, not audio latency. Random 1-3 second gaps between tones prevent that.</p>
<h2>The hardware-reported figure alongside your estimate</h2>
<p>Where your browser supports it, <code>AudioContext.baseLatency</code> and <code>outputLatency</code> report a partial, hardware-level latency figure directly — useful context to compare against your reaction-based estimate, though it only covers part of the full chain and won't include extra delay added by something like a Bluetooth connection.</p>'''

FAQ = [
    {"question": "Why is the result a range instead of one number?", "answer": "Because a browser can't separate your personal reaction time from actual audio latency — every click measures both combined. Reporting a range is more honest than presenting a single number with false precision."},
    {"question": "Why does the test discard some of my trials?", "answer": "A reaction faster than about 80ms is implausibly quick for a genuine reaction and likely an anticipatory click, while one much slower than a second suggests a moment of lost attention rather than the tone's actual latency. Discarding those outliers gives a more representative estimate from the remaining trials."},
    {"question": "Can this test measure my Bluetooth headphones' specific added delay?", "answer": "Indirectly — your reaction-based estimate includes whatever delay your full output chain adds, Bluetooth included. The separate AudioContext.baseLatency/outputLatency figures are hardware-reported and don't capture Bluetooth's own added delay, which is why both numbers are shown side by side rather than treated as interchangeable."},
    {"question": "Why do I need to click quickly instead of the test measuring something automatically?", "answer": "There's no way for a web page to detect \"a human heard this sound\" other than asking for a response — an automatic measurement would only capture the software/hardware latency up to when audio is handed off, not the actual delay you experience as a listener, which is a different (and for lip-sync purposes, more relevant) thing to know."},
]

TOOL = {
    "slug": "audio-latency-delay-test",
    "meta_title": "Audio Latency Test — Estimate Bluetooth/Speaker Delay | WebcamTest",
    "meta_description": "Estimate your audio latency — the usual cause of lip-sync problems on Bluetooth headphones and calls. A reaction-based test reporting an honest range, not a false precise number.",
    "h1": "Audio Latency Test",
    "subtitle": "Estimates audio delay from a reaction-time test, reported as an honest range — the usual cause of lip-sync problems on Bluetooth and video calls.",
    "card": {
        "layout": "raw",
        "fields_html": FIELDS_HTML,
    },
    "script": SCRIPT,
    "content_html": CONTENT_HTML,
    "faq": FAQ,
}

if __name__ == "__main__":
    out_path = os.path.join(CONTENT_DIR, "audio-latency-delay-test.json")
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(TOOL, f, indent=2, ensure_ascii=False)
    print("Wrote", out_path)
