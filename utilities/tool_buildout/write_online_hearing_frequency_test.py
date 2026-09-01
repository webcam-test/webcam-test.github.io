#!/usr/bin/env python3
"""Writes src/content/online-hearing-frequency-test.json."""
import json
import os

BASE = os.path.dirname(os.path.abspath(__file__))
CONTENT_DIR = os.path.normpath(os.path.join(BASE, "..", "..", "src", "content"))

EAR_ICON = '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M6 18c-3-3-3-9 2-13a6 6 0 0 1 8 8c-1 1-2 1-3 0a3 3 0 0 1 0-4" stroke-linecap="round"/><path d="M12 14a4 4 0 0 0 4 4c1 0 1 2-1 3-3 1-7-1-7-5" stroke-linecap="round"/></svg>'
CHART_ICON = '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect x="3" y="3" width="18" height="18" rx="2"/><path d="M3 9h18M3 15h18M9 3v18"/></svg>'
WARN_ICON = '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M12 9v4M12 17h.01M10.3 3.9L1.8 18a2 2 0 0 0 1.7 3h17a2 2 0 0 0 1.7-3L13.7 3.9a2 2 0 0 0-3.4 0z" stroke-linecap="round" stroke-linejoin="round"/></svg>'
DOT_ICON = '<svg viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="9"/></svg>'

FIELDS_HTML = f'''<div class="tool-panel span-3">
  <div class="diagnostic-item sev-warn" style="margin-bottom:1.25rem"><span class="diag-icon">{WARN_ICON}</span><span><strong>This is not a medical hearing test.</strong> It's a rough, informal estimate for fun — the result depends entirely on your speakers or headphones, which vary hugely and often can't reproduce the highest frequencies at all regardless of your actual hearing. If you have genuine concerns about your hearing, see an audiologist.</span></div>
  <div class="panel-header">
    <span class="panel-icon">{EAR_ICON}</span>
    <div><h2 id="stepTitle">Step 1 — Set Your Volume</h2><p class="panel-sub" id="stepSubtitle">Play a comfortable reference tone before the test begins</p></div>
  </div>
  <div style="text-align:center;padding:1rem 0">
    <div id="freqReadout" style="font-family:var(--font-mono);font-weight:700;font-size:2rem;color:var(--accent-light)">1 kHz</div>
  </div>
  <div class="tool-actions" style="justify-content:center" id="stepActions">
    <button type="button" class="btn-primary" id="btnPrimaryAction">Play Reference Tone</button>
    <button type="button" class="btn-secondary" id="btnCantHear" style="display:none">I Can't Hear It Anymore</button>
    <button type="button" class="btn-secondary" id="btnRestart" style="display:none">Test Again</button>
  </div>
  <div class="diagnostic-panel" id="diagnosticPanel" style="margin-top:1rem">
    <div class="diagnostic-item" id="diagDefault"><span class="diag-icon">{DOT_ICON}</span><span>Set your volume to a comfortable, moderate level, then click Play Reference Tone.</span></div>
  </div>
</div>
<div class="tool-panel span-2">
  <div class="panel-header">
    <span class="panel-icon">{CHART_ICON}</span>
    <div><h2>Typical Range by Age</h2><p class="panel-sub">A commonly cited approximation, not a diagnostic scale</p></div>
  </div>
  <div class="info-table" id="ageTable">
    <div class="info-row" data-bracket="teens"><span class="info-label">Teens</span><span class="info-value" style="text-align:left;font-weight:400;font-family:inherit">up to ~19–20 kHz</span></div>
    <div class="info-row" data-bracket="20s"><span class="info-label">20s</span><span class="info-value" style="text-align:left;font-weight:400;font-family:inherit">~17–19 kHz</span></div>
    <div class="info-row" data-bracket="30s"><span class="info-label">30s</span><span class="info-value" style="text-align:left;font-weight:400;font-family:inherit">~15–17 kHz</span></div>
    <div class="info-row" data-bracket="40s"><span class="info-label">40s</span><span class="info-value" style="text-align:left;font-weight:400;font-family:inherit">~13–15 kHz</span></div>
    <div class="info-row" data-bracket="50s"><span class="info-label">50s</span><span class="info-value" style="text-align:left;font-weight:400;font-family:inherit">~11–13 kHz</span></div>
    <div class="info-row" data-bracket="60plus"><span class="info-label">60+</span><span class="info-value" style="text-align:left;font-weight:400;font-family:inherit">~8–11 kHz</span></div>
  </div>
</div>
<div class="tool-panel">
  <div class="stat-grid">
    <div class="stat-tile highlight"><span class="stat-value" id="statResult">—</span><span class="stat-label">Your Estimated Ceiling</span></div>
  </div>
  <p class="field-note">Hearing loss at the very top of this range is extremely common with age and totally normal — it's one of the first frequency bands to go, long before it affects speech or music you'd notice day to day.</p>
</div>'''

SCRIPT = r'''(function () {
  'use strict';

  var stepTitle = document.getElementById('stepTitle');
  var stepSubtitle = document.getElementById('stepSubtitle');
  var freqReadout = document.getElementById('freqReadout');
  var btnPrimary = document.getElementById('btnPrimaryAction');
  var btnCantHear = document.getElementById('btnCantHear');
  var btnRestart = document.getElementById('btnRestart');
  var diagnosticPanel = document.getElementById('diagnosticPanel');
  var statResult = document.getElementById('statResult');
  var ageTable = document.getElementById('ageTable');

  var MAX_GAIN = 0.25; // deliberately conservative -- see this tool's own safety note (cap output level)
  var RAMP_SECONDS = 0.05;
  var REFERENCE_FREQ = 1000;

  // Ascending sequence from 8 kHz upward, per this tool's own spec.
  var TEST_FREQUENCIES = [8000, 10000, 12000, 13000, 14000, 15000, 16000, 17000, 18000, 19000, 20000];

  var audioCtx = null;
  var oscillator = null;
  var gainNode = null;
  var phase = 'reference'; // 'reference' -> 'testing' -> 'done'
  var stepIndex = -1;

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
      oscillator.frequency.value = REFERENCE_FREQ;
      gainNode.gain.value = 0;
      oscillator.connect(gainNode);
      gainNode.connect(audioCtx.destination);
      oscillator.start();
    }
    return audioCtx.resume().catch(function () {});
  }

  function rampGainTo(target) {
    if (!gainNode || !audioCtx) return;
    var now = audioCtx.currentTime;
    gainNode.gain.cancelScheduledValues(now);
    gainNode.gain.setValueAtTime(gainNode.gain.value, now);
    gainNode.gain.linearRampToValueAtTime(target, now + RAMP_SECONDS);
  }

  function formatFreq(hz) {
    return hz >= 1000 ? (hz / 1000).toFixed(hz % 1000 === 0 ? 0 : 1) + ' kHz' : hz + ' Hz';
  }

  function playReferenceTone() {
    ensureContext().then(function () {
      oscillator.frequency.setValueAtTime(REFERENCE_FREQ, audioCtx.currentTime);
      freqReadout.textContent = formatFreq(REFERENCE_FREQ);
      rampGainTo(MAX_GAIN);
      setDiagnostic('ok', '<strong>Playing a 1 kHz reference tone.</strong> Adjust your device volume to a comfortable, clearly audible level, then continue.');
      btnPrimary.textContent = 'Volume Is Set — Start Test';
      btnPrimary.onclick = beginTest;
    });
  }

  function beginTest() {
    phase = 'testing';
    stepIndex = 0;
    stepTitle.textContent = 'Step 2 — Ascending Tones';
    stepSubtitle.textContent = 'Click "I can’t hear it anymore" the moment a tone disappears';
    btnPrimary.style.display = 'none';
    btnCantHear.style.display = '';
    playCurrentStep();
  }

  function playCurrentStep() {
    var freq = TEST_FREQUENCIES[stepIndex];
    ensureContext().then(function () {
      oscillator.frequency.setValueAtTime(freq, audioCtx.currentTime);
      freqReadout.textContent = formatFreq(freq);
      rampGainTo(MAX_GAIN);
      setDiagnostic('', '<strong>Playing ' + formatFreq(freq) + '.</strong> If you can hear this, wait a moment — it advances automatically to the next tone. Click the button the instant it disappears.');
    });
  }

  function advanceOrFinish() {
    stepIndex++;
    if (stepIndex >= TEST_FREQUENCIES.length) {
      finishTest(TEST_FREQUENCIES[TEST_FREQUENCIES.length - 1], true);
    } else {
      playCurrentStep();
    }
  }

  function finishTest(highestHeard, reachedEnd) {
    phase = 'done';
    rampGainTo(0);
    var resultText = reachedEnd ? formatFreq(highestHeard) + '+ (test limit)' : formatFreq(highestHeard);
    statResult.textContent = resultText;
    freqReadout.textContent = resultText;
    stepTitle.textContent = 'Result';
    stepSubtitle.textContent = 'Remember: this is a rough, informal estimate, not a medical measurement';
    btnCantHear.style.display = 'none';
    btnRestart.style.display = '';
    setDiagnostic('ok', reachedEnd
      ? '<strong>You could hear every tone up to the top of this test (' + formatFreq(highestHeard) + ').</strong> Many playback devices roll off well before this point regardless of hearing ability, so this is a good result, not necessarily exceptional hearing.'
      : '<strong>Your estimated ceiling is around ' + formatFreq(highestHeard) + '.</strong> Remember this depends heavily on your speakers/headphones — a different device could easily give a different result.');
    highlightBracket(highestHeard);
  }

  function highlightBracket(hz) {
    var bracket = hz >= 19000 ? 'teens' : hz >= 17000 ? '20s' : hz >= 15000 ? '30s' : hz >= 13000 ? '40s' : hz >= 11000 ? '50s' : '60plus';
    Array.prototype.forEach.call(ageTable.querySelectorAll('.info-row'), function (row) {
      row.classList.toggle('highlight-row', row.getAttribute('data-bracket') === bracket);
      if (row.getAttribute('data-bracket') === bracket) {
        row.style.background = 'var(--accent-softer)';
        row.style.borderColor = 'var(--accent)';
      }
    });
  }

  function restartTest() {
    phase = 'reference';
    stepIndex = -1;
    stepTitle.textContent = 'Step 1 — Set Your Volume';
    stepSubtitle.textContent = 'Play a comfortable reference tone before the test begins';
    freqReadout.textContent = formatFreq(REFERENCE_FREQ);
    statResult.textContent = '—';
    btnPrimary.style.display = '';
    btnPrimary.textContent = 'Play Reference Tone';
    btnPrimary.onclick = playReferenceTone;
    btnCantHear.style.display = 'none';
    btnRestart.style.display = 'none';
    rampGainTo(0);
    Array.prototype.forEach.call(ageTable.querySelectorAll('.info-row'), function (row) {
      row.style.background = '';
      row.style.borderColor = '';
    });
    setDiagnostic('', 'Set your volume to a comfortable, moderate level, then click Play Reference Tone.');
  }

  btnPrimary.addEventListener('click', playReferenceTone);
  btnCantHear.addEventListener('click', function () {
    if (phase !== 'testing') return;
    var lastHeard = stepIndex > 0 ? TEST_FREQUENCIES[stepIndex - 1] : null;
    if (lastHeard === null) {
      finishTest(TEST_FREQUENCIES[0] - 1000, false);
    } else {
      finishTest(lastHeard, false);
    }
  });
  btnRestart.addEventListener('click', restartTest);

  // Each test tone auto-advances after a few seconds if the visitor doesn't
  // click "can't hear it" -- silence gives no signal either way, so
  // advancing (rather than waiting forever) keeps the test moving.
  setInterval(function () {
    if (phase === 'testing') advanceOrFinish();
  }, 4000);

  window.addEventListener('pagehide', function () {
    if (audioCtx) { audioCtx.close().catch(function () {}); audioCtx = null; }
  });
  document.addEventListener('visibilitychange', function () {
    if (document.visibilityState === 'hidden' && gainNode && audioCtx) rampGainTo(0);
  });

  if (!(window.AudioContext || window.webkitAudioContext)) {
    setDiagnostic('error', '<strong>Your browser doesn’t support the Web Audio API.</strong>');
    btnPrimary.disabled = true;
  }
})();'''

CONTENT_HTML = '''<p>This is a lighthearted, informal estimate of the highest-pitched tone you can hear — a popular "hearing age" style test, not a clinical hearing assessment. Read the honest limitations below before drawing any conclusions from your result.</p>
<h2>Why this can't be a real hearing test</h2>
<p>A genuine audiological hearing test is performed in a controlled sound booth with calibrated headphones and a trained professional interpreting the results. This tool runs through whatever speakers or headphones happen to be connected to your device right now — and playback hardware varies enormously in how high a frequency it can actually reproduce. Many consumer speakers and even some headphones roll off well before 16 kHz regardless of how good your hearing is, which means a low result here just as easily reflects your hardware's limits as your ears'.</p>
<h2>Why hearing loss at high frequencies is completely normal</h2>
<p>The ability to hear very high frequencies is one of the first things to fade with age, and it happens to almost everyone gradually over decades — long before it affects your ability to hear speech, music, or anything else you'd notice in daily life. A lower result on this test is expected as people get older and is not, by itself, a sign of a hearing problem worth worrying about.</p>
<h2>Getting the most consistent result</h2>
<p>Use headphones rather than speakers if you can — they're far more likely to reproduce high frequencies accurately and consistently. Set your volume using the reference tone step before starting, and try to test in a quiet room. If you have any genuine concerns about your hearing, this tool is not a substitute for seeing an audiologist.</p>'''

FAQ = [
    {"question": "Is this a real medical hearing test?", "answer": "No — this is an informal, for-fun estimate. It cannot diagnose hearing loss and depends entirely on the quality of your speakers or headphones, which is completely outside this test's control. See an audiologist for an actual hearing assessment."},
    {"question": "Why did I score lower than I expected?", "answer": "Most likely your playback device: many speakers and headphones can't accurately reproduce frequencies above roughly 15-16 kHz at all, regardless of how good your hearing is. Try headphones instead of speakers, and make sure your volume is set to a clearly audible level using the reference tone step."},
    {"question": "Is it safe to keep raising my volume if I can't hear the high tones?", "answer": "No — please don't. High-frequency hearing loss is extremely common and not dangerous by itself, but turning volume up excessively to try to hear very high tones risks damaging your hearing further. Accept your result at a comfortable volume rather than pushing louder."},
    {"question": "Why does the tone automatically move on after a few seconds?", "answer": "If you don't click \"I can't hear it anymore,\" the test assumes you can still hear the current tone and moves to the next, slightly higher one. This keeps the test moving at a reasonable pace rather than waiting indefinitely."},
]

TOOL = {
    "slug": "online-hearing-frequency-test",
    "meta_title": "Online Hearing Test — Estimate Your Highest Audible Frequency | WebcamTest",
    "meta_description": "A fun, informal hearing test that estimates the highest-pitched tone you can hear, with an age-comparison chart. Not a medical test — results depend on your speakers or headphones.",
    "h1": "Online Hearing Test",
    "subtitle": "An informal, for-fun test that estimates the highest frequency you can hear — not a substitute for a real hearing exam.",
    "card": {
        "layout": "raw",
        "fields_html": FIELDS_HTML,
    },
    "script": SCRIPT,
    "content_html": CONTENT_HTML,
    "faq": FAQ,
}

if __name__ == "__main__":
    out_path = os.path.join(CONTENT_DIR, "online-hearing-frequency-test.json")
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(TOOL, f, indent=2, ensure_ascii=False)
    print("Wrote", out_path)
