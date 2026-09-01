#!/usr/bin/env python3
"""Writes src/content/speaker-polarity-phase-test.json."""
import json
import os

BASE = os.path.dirname(os.path.abspath(__file__))
CONTENT_DIR = os.path.normpath(os.path.join(BASE, "..", "..", "src", "content"))

SPEAKER_ICON = '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M11 5L6 9H2v6h4l5 4V5z"/><path d="M15.5 8.5a5 5 0 0 1 0 7" stroke-linecap="round"/></svg>'
EAR_ICON = '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M6 18c-3-3-3-9 2-13a6 6 0 0 1 8 8c-1 1-2 1-3 0a3 3 0 0 1 0-4" stroke-linecap="round"/><path d="M12 14a4 4 0 0 0 4 4c1 0 1 2-1 3-3 1-7-1-7-5" stroke-linecap="round"/></svg>'
WARN_ICON = '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M12 9v4M12 17h.01M10.3 3.9L1.8 18a2 2 0 0 0 1.7 3h17a2 2 0 0 0 1.7-3L13.7 3.9a2 2 0 0 0-3.4 0z" stroke-linecap="round" stroke-linejoin="round"/></svg>'
DOT_ICON = '<svg viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="9"/></svg>'

FIELDS_HTML = f'''<div class="tool-panel primary">
  <div class="panel-header">
    <span class="panel-icon">{SPEAKER_ICON}</span>
    <div><h2>Speaker Polarity and Phase Test</h2><p class="panel-sub">Requires two real speakers — this test can't work on headphones</p></div>
  </div>
  <div class="diagnostic-item sev-warn" style="margin-bottom:1.25rem"><span class="diag-icon">{EAR_ICON}</span><span><strong>Headphones won't show anything here.</strong> Your ears are acoustically isolated by headphones, so a phase difference between channels has nothing to interact with. This test only works through actual stereo speakers positioned in a room.</span></div>
  <div class="tool-actions" style="justify-content:center">
    <button type="button" class="btn-primary" id="btnInPhase">Play In-Phase (Correct Wiring)</button>
    <button type="button" class="btn-secondary" id="btnOutPhase">Play Out-of-Phase (Reversed Wiring)</button>
    <button type="button" class="btn-secondary" id="btnStop" disabled>Stop</button>
  </div>
  <div class="tool-field slider-field" style="margin-top:1rem">
    <label for="volumeSlider">Volume</label>
    <div class="slider-row">
      <input type="range" id="volumeSlider" min="0" max="100" value="35">
      <span class="slider-value" id="volumeValue">35%</span>
    </div>
  </div>
  <div class="diagnostic-panel" id="diagnosticPanel" style="margin-top:1rem">
    <div class="diagnostic-item" id="diagDefault"><span class="diag-icon">{DOT_ICON}</span><span>Click <strong>Play In-Phase</strong> first to hear the correct baseline, then <strong>Play Out-of-Phase</strong> to compare.</span></div>
  </div>
</div>
<div class="tool-panel">
  <div class="panel-header">
    <span class="panel-icon"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="10"/><path d="M12 16v-4M12 8h.01" stroke-linecap="round"/></svg></span>
    <div><h2>What You're Listening For</h2></div>
  </div>
  <p class="field-note" style="margin-top:0"><strong>In-phase (correct):</strong> the sound feels centred between your speakers with solid, present bass — a clear, focused image.</p>
  <p class="field-note" style="margin-bottom:0"><strong>Out-of-phase (reversed):</strong> the sound feels diffuse and hard to locate, thinner overall, with noticeably weaker bass — the two speakers are partially cancelling each other out.</p>
</div>
<div class="tool-panel">
  <div class="panel-header">
    <span class="panel-icon">{WARN_ICON}</span>
    <div><h2>What Reversed Wiring Means</h2></div>
  </div>
  <p class="field-note" style="margin-top:0">If your speakers sound like the "out-of-phase" example even during normal listening, one speaker's positive and negative wire connections are likely swapped relative to the other — common after DIY speaker wiring or a loose terminal. Swapping the two wires on just one speaker (not both) usually fixes it.</p>
</div>'''

SCRIPT = r'''(function () {
  'use strict';

  var btnInPhase = document.getElementById('btnInPhase');
  var btnOutPhase = document.getElementById('btnOutPhase');
  var btnStop = document.getElementById('btnStop');
  var volumeSlider = document.getElementById('volumeSlider');
  var volumeValue = document.getElementById('volumeValue');
  var diagnosticPanel = document.getElementById('diagnosticPanel');

  var MAX_GAIN = 0.35; // conservative ceiling -- see this site's safety notes for playback tools
  var RAMP_SECONDS = 0.03;
  var TEST_FREQ = 80; // a low-mid tone where phase cancellation is easy to hear

  var audioCtx = null;
  var oscillator = null;
  var gainL = null, gainR = null;
  var panL = null, panR = null;
  var playing = false;

  function setDiagnostic(sev, html) {
    diagnosticPanel.innerHTML = '<div class="diagnostic-item' + (sev ? ' sev-' + sev : '') + '"><span class="diag-icon">' +
      '<svg viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="9"/></svg>' +
      '</span><span>' + html + '</span></div>';
  }

  function currentGainTarget() {
    return (parseFloat(volumeSlider.value) / 100) * MAX_GAIN;
  }

  // One shared oscillator split into two gain chains, each hard-panned to
  // a channel via StereoPannerNode -- a single source guarantees the two
  // channels are perfectly correlated to start with, so inverting one
  // channel's gain to -1 is a clean, genuine phase inversion rather than
  // two independently-drifting oscillators, per this tool's own spec note.
  function ensureGraph() {
    if (audioCtx) return audioCtx.resume().catch(function () {});
    audioCtx = new (window.AudioContext || window.webkitAudioContext)();
    oscillator = audioCtx.createOscillator();
    oscillator.type = 'sine';
    oscillator.frequency.value = TEST_FREQ;

    gainL = audioCtx.createGain();
    gainR = audioCtx.createGain();
    gainL.gain.value = 0;
    gainR.gain.value = 0;

    panL = audioCtx.createStereoPanner ? audioCtx.createStereoPanner() : null;
    panR = audioCtx.createStereoPanner ? audioCtx.createStereoPanner() : null;

    oscillator.connect(gainL);
    oscillator.connect(gainR);

    if (panL && panR) {
      panL.pan.value = -1;
      panR.pan.value = 1;
      gainL.connect(panL).connect(audioCtx.destination);
      gainR.connect(panR).connect(audioCtx.destination);
    } else {
      gainL.connect(audioCtx.destination);
      gainR.connect(audioCtx.destination);
    }

    oscillator.start();
    return audioCtx.resume().catch(function () {});
  }

  function rampGain(node, target) {
    var now = audioCtx.currentTime;
    node.gain.cancelScheduledValues(now);
    node.gain.setValueAtTime(node.gain.value, now);
    node.gain.linearRampToValueAtTime(target, now + RAMP_SECONDS);
  }

  function play(inPhase) {
    ensureGraph().then(function () {
      playing = true;
      var target = currentGainTarget();
      rampGain(gainL, target);
      rampGain(gainR, inPhase ? target : -target);
      btnStop.disabled = false;
      setDiagnostic('ok', inPhase
        ? '<strong>Playing in-phase.</strong> This is how correctly wired speakers should sound — centred, with solid bass.'
        : '<strong>Playing out-of-phase (simulated reversed wiring).</strong> Notice how the sound feels diffuse and the bass thins out compared to in-phase.');
    });
  }

  function stop() {
    playing = false;
    if (gainL && audioCtx) rampGain(gainL, 0);
    if (gainR && audioCtx) rampGain(gainR, 0);
    btnStop.disabled = true;
    setDiagnostic('', 'Stopped.');
  }

  btnInPhase.addEventListener('click', function () { play(true); });
  btnOutPhase.addEventListener('click', function () { play(false); });
  btnStop.addEventListener('click', stop);

  volumeSlider.addEventListener('input', function () {
    volumeValue.textContent = volumeSlider.value + '%';
    if (playing && audioCtx) {
      var target = currentGainTarget();
      // Re-apply whichever mode is currently active by checking gainR's sign
      // relative to gainL rather than tracking a separate flag.
      var outOfPhase = gainR.gain.value < 0;
      rampGain(gainL, target);
      rampGain(gainR, outOfPhase ? -target : target);
    }
  });

  window.addEventListener('pagehide', function () {
    if (audioCtx) { audioCtx.close().catch(function () {}); audioCtx = null; }
  });
  document.addEventListener('visibilitychange', function () {
    if (document.visibilityState === 'hidden' && audioCtx) { stop(); }
  });

  if (!(window.AudioContext || window.webkitAudioContext)) {
    setDiagnostic('error', '<strong>Your browser doesn’t support the Web Audio API.</strong>');
    btnInPhase.disabled = true;
    btnOutPhase.disabled = true;
  }
})();'''

CONTENT_HTML = '''<p>Reversed speaker wiring is a surprisingly common and easy-to-miss problem — it doesn't make a speaker silent or obviously broken, it just quietly weakens the bass and smears the stereo image in a way that's easy to attribute to the room or the speakers themselves rather than the wiring.</p>
<h2>What "out of phase" actually means</h2>
<p>Each speaker driver moves outward and inward to produce sound. When both speakers in a stereo pair move in the same direction at the same time for identical parts of the signal, they're "in phase" and their sound waves reinforce each other — this is correct, and how speakers are meant to be wired. If one speaker's positive and negative connections are swapped relative to the other, that speaker moves in the opposite direction for the same signal — the two speakers are now working against each other, partially cancelling the sound, especially at low frequencies where the cancellation is most audible.</p>
<h2>Why this test can't work on headphones</h2>
<p>Headphones deliver each channel directly and separately to each ear, with no shared acoustic space for the two channels' sound waves to interact in. Phase cancellation is fundamentally an effect that happens in the air, between two speakers in a room — there's nothing for it to act on with headphones, so this test will sound identical in both modes if you try it that way. That's expected, not a bug.</p>
<h2>Fixing reversed wiring</h2>
<p>If your setup sounds like the out-of-phase example even during normal use, check the wire connections at the back of each speaker and your amplifier or receiver — swap the two wires on just one speaker (not both, which would just reverse the reversal back to normal on that one speaker but leave the pair still mismatched if the other was already correct). Most speaker terminals are colour-coded or marked + and − to make correct polarity straightforward to restore.</p>'''

FAQ = [
    {"question": "Why does the test sound the same in both modes on my headphones?", "answer": "This is expected — headphone drivers deliver each channel separately and directly to each ear with no shared air space for the channels to interact in, so phase cancellation (which only happens acoustically, between two speakers in a room) has nothing to act on. Try the test through actual stereo speakers instead."},
    {"question": "How do I know if my speakers are actually wired backwards, not just sounding this way from room acoustics?", "answer": "Compare your normal listening directly against this test's out-of-phase example. If your regular listening sounds notably weaker in bass and less centred/focused than the in-phase example here, and especially if it improves after swapping one speaker's wire connections, that's a strong sign of reversed wiring rather than just room acoustics."},
    {"question": "Which speaker's wires should I swap if I find a problem?", "answer": "Swap the wire connections on just one of the two speakers, not both — swapping both would just undo each other and leave you back where you started if one was already correct. Try either speaker; whichever one you swap, the mismatch gets fixed."},
    {"question": "Is it safe to play this test at high volume?", "answer": "Start at a low, comfortable volume as with any playback test — there's no special extra risk from the phase-inversion itself beyond normal speaker volume limits, but there's no reason to test any louder than you'd normally listen anyway."},
]

TOOL = {
    "slug": "speaker-polarity-phase-test",
    "meta_title": "Speaker Polarity & Phase Test — Detect Reversed Wiring | WebcamTest",
    "meta_description": "Play in-phase and out-of-phase test tones to detect reversed speaker wiring. Requires two real speakers — explains why headphones can't show the effect.",
    "h1": "Speaker Polarity and Phase Test",
    "subtitle": "Play in-phase and out-of-phase signals to detect reversed speaker wiring — requires real stereo speakers, not headphones.",
    "card": {
        "layout": "raw",
        "fields_html": FIELDS_HTML,
    },
    "script": SCRIPT,
    "content_html": CONTENT_HTML,
    "faq": FAQ,
}

if __name__ == "__main__":
    out_path = os.path.join(CONTENT_DIR, "speaker-polarity-phase-test.json")
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(TOOL, f, indent=2, ensure_ascii=False)
    print("Wrote", out_path)
