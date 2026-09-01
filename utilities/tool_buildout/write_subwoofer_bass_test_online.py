#!/usr/bin/env python3
"""Writes src/content/subwoofer-bass-test-online.json."""
import json
import os

BASE = os.path.dirname(os.path.abspath(__file__))
CONTENT_DIR = os.path.normpath(os.path.join(BASE, "..", "..", "src", "content"))

SPEAKER_ICON = '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M11 5L6 9H2v6h4l5 4V5z"/><path d="M15.5 8.5a5 5 0 0 1 0 7" stroke-linecap="round"/></svg>'
WARN_ICON = '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M12 9v4M12 17h.01M10.3 3.9L1.8 18a2 2 0 0 0 1.7 3h17a2 2 0 0 0 1.7-3L13.7 3.9a2 2 0 0 0-3.4 0z" stroke-linecap="round" stroke-linejoin="round"/></svg>'
LIST_ICON = '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M9 6h11M9 12h11M9 18h11M4 6h.01M4 12h.01M4 18h.01" stroke-linecap="round"/></svg>'
DOT_ICON = '<svg viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="9"/></svg>'

FIELDS_HTML = f'''<div class="tool-panel primary">
  <div class="panel-header">
    <span class="panel-icon">{SPEAKER_ICON}</span>
    <div><h2>Subwoofer and Bass Test</h2><p class="panel-sub">Start quiet — sustained low frequencies at high volume can damage small speakers</p></div>
  </div>
  <div class="diagnostic-item sev-warn" style="margin-bottom:1.25rem"><span class="diag-icon">{WARN_ICON}</span><span><strong>Turn your volume down before starting.</strong> Small speakers and laptop speakers in particular can be damaged by sustained low-frequency tones at high volume — start quiet and raise gradually only if needed.</span></div>
  <div id="freqReadout" style="text-align:center;font-family:var(--font-mono);font-weight:700;font-size:1.8rem;color:var(--accent-light);padding:.5rem 0">—</div>
  <div class="tool-actions" style="justify-content:center;flex-wrap:wrap">
    <button type="button" class="btn-secondary freq-btn" data-freq="20">20 Hz</button>
    <button type="button" class="btn-secondary freq-btn" data-freq="25">25 Hz</button>
    <button type="button" class="btn-secondary freq-btn" data-freq="31.5">31.5 Hz</button>
    <button type="button" class="btn-secondary freq-btn" data-freq="40">40 Hz</button>
    <button type="button" class="btn-secondary freq-btn" data-freq="50">50 Hz</button>
    <button type="button" class="btn-secondary freq-btn" data-freq="63">63 Hz</button>
    <button type="button" class="btn-secondary freq-btn" data-freq="80">80 Hz</button>
    <button type="button" class="btn-secondary freq-btn" data-freq="100">100 Hz</button>
    <button type="button" class="btn-secondary freq-btn" data-freq="125">125 Hz</button>
    <button type="button" class="btn-secondary freq-btn" data-freq="150">150 Hz</button>
    <button type="button" class="btn-secondary" id="btnStop" disabled>Stop</button>
  </div>
  <div class="tool-field slider-field" style="margin-top:1rem">
    <label for="volumeSlider">Volume</label>
    <div class="slider-row">
      <input type="range" id="volumeSlider" min="0" max="100" value="25">
      <span class="slider-value" id="volumeValue">25%</span>
    </div>
  </div>
  <div class="diagnostic-panel" id="diagnosticPanel" style="margin-top:1rem">
    <div class="diagnostic-item" id="diagDefault"><span class="diag-icon">{DOT_ICON}</span><span>Click a frequency to play it, starting at low volume.</span></div>
  </div>
</div>
<div class="tool-panel">
  <div class="panel-header">
    <span class="panel-icon"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M4 14a1 1 0 0 1-.78-1.63l9.9-10.2a.5.5 0 0 1 .86.46l-1.92 6.02A1 1 0 0 0 13 10h7a1 1 0 0 1 .78 1.63l-9.9 10.2a.5.5 0 0 1-.86-.46l1.92-6.02A1 1 0 0 0 11 14H4z"/></svg></span>
    <div><h2>Low-Range Sweep</h2><p class="panel-sub">20–150 Hz continuous sweep</p></div>
  </div>
  <div class="tool-actions">
    <button type="button" class="btn-secondary" id="btnSweep">Start Sweep (10s)</button>
  </div>
  <p class="field-note">A continuous sweep can reveal a rattle or dropout at a specific frequency that discrete steps might skip past.</p>
</div>
<div class="tool-panel">
  <div class="panel-header">
    <span class="panel-icon">{LIST_ICON}</span>
    <div><h2>Identifying Rattles and Silence</h2></div>
  </div>
  <p class="field-note" style="margin-top:0"><strong>Buzzing or rattling:</strong> usually a loose panel, screw, or nearby object vibrating in sympathy — not necessarily the speaker itself. Check what's near the speaker before assuming it's faulty.</p>
  <p class="field-note" style="margin-bottom:0"><strong>Hearing nothing below ~60 Hz:</strong> very common and usually not a fault — many speakers, especially small or laptop speakers, simply can't reproduce frequencies that low at all. Silence there is a hardware limitation, not evidence something's broken.</p>
</div>'''

SCRIPT = r'''(function () {
  'use strict';

  var freqReadout = document.getElementById('freqReadout');
  var btnStop = document.getElementById('btnStop');
  var btnSweep = document.getElementById('btnSweep');
  var volumeSlider = document.getElementById('volumeSlider');
  var volumeValue = document.getElementById('volumeValue');
  var diagnosticPanel = document.getElementById('diagnosticPanel');
  var freqButtons = Array.prototype.slice.call(document.querySelectorAll('.freq-btn'));

  var MAX_GAIN = 0.3; // conservative ceiling -- see this site's safety notes; low frequencies at high level risk driver damage
  var RAMP_SECONDS = 0.05;
  var MIN_SWEEP = 20, MAX_SWEEP = 150;
  var SWEEP_DURATION = 10;

  var audioCtx = null;
  var oscillator = null;
  var gainNode = null;
  var activeBtn = null;
  var sweeping = false;
  var sweepIntervalId = null;
  var sweepElapsed = 0;
  var sweepLastTick = 0;

  function setDiagnostic(sev, html) {
    diagnosticPanel.innerHTML = '<div class="diagnostic-item' + (sev ? ' sev-' + sev : '') + '"><span class="diag-icon">' +
      '<svg viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="9"/></svg>' +
      '</span><span>' + html + '</span></div>';
  }

  function formatFreq(hz) {
    return (hz % 1 === 0 ? hz : hz.toFixed(1)) + ' Hz';
  }

  function ensureContext() {
    if (!audioCtx) {
      audioCtx = new (window.AudioContext || window.webkitAudioContext)();
      oscillator = audioCtx.createOscillator();
      gainNode = audioCtx.createGain();
      oscillator.type = 'sine';
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

  function rampGainTo(target) {
    if (!gainNode || !audioCtx) return;
    var now = audioCtx.currentTime;
    gainNode.gain.cancelScheduledValues(now);
    gainNode.gain.setValueAtTime(gainNode.gain.value, now);
    gainNode.gain.linearRampToValueAtTime(target, now + RAMP_SECONDS);
  }

  function stopSweep() {
    if (sweepIntervalId) { clearInterval(sweepIntervalId); sweepIntervalId = null; }
    sweeping = false;
    btnSweep.textContent = 'Start Sweep (10s)';
  }

  function stopAll() {
    stopSweep();
    rampGainTo(0);
    if (activeBtn) { activeBtn.classList.remove('active'); activeBtn.setAttribute('aria-pressed', 'false'); activeBtn = null; }
    btnStop.disabled = true;
    freqReadout.textContent = '—';
  }

  function playFrequency(freq, btn) {
    stopSweep();
    ensureContext().then(function () {
      oscillator.frequency.setValueAtTime(freq, audioCtx.currentTime);
      rampGainTo(currentGainTarget());
      if (activeBtn) { activeBtn.classList.remove('active'); activeBtn.setAttribute('aria-pressed', 'false'); }
      activeBtn = btn;
      if (btn) { btn.classList.add('active'); btn.setAttribute('aria-pressed', 'true'); }
      btnStop.disabled = false;
      freqReadout.textContent = formatFreq(freq);
      setDiagnostic('ok', '<strong>Playing ' + formatFreq(freq) + '.</strong> If you hear nothing and your speaker is small, that\'s likely a hardware limitation, not a fault -- see the guide alongside this.');
    });
  }

  // Timer-driven (not requestAnimationFrame) since this updates the
  // oscillator's actual frequency -- an audible side effect -- not just a
  // rendering readout, per the rAF-vs-timer distinction established
  // elsewhere in this project.
  function startSweep() {
    if (sweeping) { stopAll(); setDiagnostic('', 'Stopped.'); return; }
    ensureContext().then(function () {
      if (activeBtn) { activeBtn.classList.remove('active'); activeBtn.setAttribute('aria-pressed', 'false'); activeBtn = null; }
      sweeping = true;
      sweepElapsed = 0;
      sweepLastTick = 0;
      btnSweep.textContent = 'Stop Sweep';
      btnStop.disabled = false;
      rampGainTo(currentGainTarget());
      setDiagnostic('ok', '<strong>Sweeping 20–150 Hz…</strong> Listen for any point where a rattle appears or the sound drops out.');
      sweepIntervalId = setInterval(tickSweep, 40);
    });
  }

  function tickSweep() {
    var now = performance.now();
    if (!sweepLastTick) sweepLastTick = now;
    var dt = (now - sweepLastTick) / 1000;
    sweepLastTick = now;
    sweepElapsed += dt;
    if (sweepElapsed >= SWEEP_DURATION) {
      stopAll();
      setDiagnostic('ok', '<strong>Sweep finished.</strong> Note the frequency shown if you heard a rattle or dropout.');
      return;
    }
    var frac = sweepElapsed / SWEEP_DURATION;
    var freq = MIN_SWEEP * Math.pow(MAX_SWEEP / MIN_SWEEP, frac);
    oscillator.frequency.setValueAtTime(freq, audioCtx.currentTime);
    freqReadout.textContent = formatFreq(freq);
  }

  freqButtons.forEach(function (btn) {
    btn.setAttribute('aria-pressed', 'false');
    btn.addEventListener('click', function () {
      playFrequency(parseFloat(btn.getAttribute('data-freq')), btn);
    });
  });

  btnStop.addEventListener('click', function () {
    stopAll();
    setDiagnostic('', 'Stopped.');
  });
  btnSweep.addEventListener('click', startSweep);

  volumeSlider.addEventListener('input', function () {
    volumeValue.textContent = volumeSlider.value + '%';
    if ((activeBtn || sweeping) && audioCtx) rampGainTo(currentGainTarget());
  });

  window.addEventListener('pagehide', function () {
    stopSweep();
    if (audioCtx) { audioCtx.close().catch(function () {}); audioCtx = null; }
  });
  document.addEventListener('visibilitychange', function () {
    if (document.visibilityState === 'hidden') stopAll();
  });

  if (!(window.AudioContext || window.webkitAudioContext)) {
    setDiagnostic('error', '<strong>Your browser doesn’t support the Web Audio API.</strong>');
    freqButtons.forEach(function (b) { b.disabled = true; });
    btnSweep.disabled = true;
  }
})();'''

CONTENT_HTML = '''<p>Bass response is the hardest thing to judge from a spec sheet and the easiest to actually hear a problem with — this tool plays discrete low frequencies from 20 to 150 Hz, plus a continuous sweep across that range, so you can check extension, evenness, and rattles directly.</p>
<h2>Start quiet — this matters more here than for most audio tests</h2>
<p>Sustained low-frequency tones at high volume are one of the more common ways speaker drivers get damaged, particularly small drivers being asked to move air at 20-30 Hz — a range they were never designed to reproduce cleanly at volume. Start at a low level and only raise it gradually if you need to, and stop immediately if you hear distortion or a driver straining.</p>
<h2>Why silence at low frequencies usually isn't a fault</h2>
<p>Most speakers — especially laptop speakers, small Bluetooth speakers, and budget desktop speakers — simply can't physically reproduce frequencies much below 60 Hz at all, regardless of volume. If the low end of this test produces nothing audible, that's very likely your speaker's genuine physical limit, not a sign something's broken. A dedicated subwoofer or a larger tower speaker is generally what's required to feel real output down at 20-30 Hz.</p>
<h2>Finding a rattle</h2>
<p>A buzz or rattle at a specific frequency is often not the speaker driver itself but something nearby resonating in sympathy — a loose desk item, a picture frame, a cabinet panel. Before concluding a speaker is faulty, check what else is in the room that might be vibrating at that same frequency; moving the offending object is a far more common fix than anything wrong with the speaker.</p>'''

FAQ = [
    {"question": "Why can't I hear anything at 20 or 25 Hz?", "answer": "Most speakers, including the vast majority of laptop and small desktop speakers, physically can't reproduce frequencies that low at any volume — it's a hardware limitation of the driver size, not a fault. A subwoofer or larger tower speaker is typically needed to feel genuine output that low."},
    {"question": "Is it safe to turn the volume up if I can't hear the low frequencies?", "answer": "No — turning up the volume to try to hear frequencies your speaker genuinely can't reproduce risks damaging the driver without ever producing the sound you're listening for. Accept the silence as a hardware limit rather than pushing volume higher."},
    {"question": "I hear a rattle — is my speaker broken?", "answer": "Not necessarily. A rattle is very often something else in the room resonating in sympathy with that frequency — a loose object, a cabinet panel, a picture frame — rather than the speaker driver itself. Check nearby objects before assuming the speaker is at fault."},
    {"question": "What's the difference between the discrete frequency buttons and the sweep?", "answer": "The discrete buttons let you test specific, standard frequencies one at a time and compare their relative loudness. The continuous sweep moves smoothly through the whole 20-150 Hz range, which can reveal a narrow-band rattle or dropout that the discrete steps might skip right past."},
]

TOOL = {
    "slug": "subwoofer-bass-test-online",
    "meta_title": "Subwoofer & Bass Test — 20Hz to 150Hz Online | WebcamTest",
    "meta_description": "Test your subwoofer or speaker's bass extension with discrete low frequencies from 20 to 150 Hz, plus a continuous sweep. Includes a rattle-identification guide.",
    "h1": "Subwoofer and Bass Test",
    "subtitle": "Play discrete low frequencies from 20-150 Hz and a continuous sweep to check bass extension and identify rattles.",
    "card": {
        "layout": "raw",
        "fields_html": FIELDS_HTML,
    },
    "script": SCRIPT,
    "content_html": CONTENT_HTML,
    "faq": FAQ,
}

if __name__ == "__main__":
    out_path = os.path.join(CONTENT_DIR, "subwoofer-bass-test-online.json")
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(TOOL, f, indent=2, ensure_ascii=False)
    print("Wrote", out_path)
