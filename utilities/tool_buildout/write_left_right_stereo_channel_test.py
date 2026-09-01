#!/usr/bin/env python3
"""Writes src/content/left-right-stereo-channel-test.json. Throwaway
authoring script, same pattern as write_webcam_test_online.py — see this
project's CLAUDE.md 'Authoring a new tool's content file'. Reuses
speaker-test-online.json's oscillator/gain ramp-in/out pattern, MAX_GAIN
safety ceiling, and setSinkId output-device picker verbatim, inserting a
StereoPannerNode (simpler than manual ChannelSplitter routing, per the
spec's own JS-considerations column) between gain and destination."""
import json
import os

BASE = os.path.dirname(os.path.abspath(__file__))
CONTENT_DIR = os.path.normpath(os.path.join(BASE, "..", "..", "src", "content"))

SPEAKER_ICON = '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M11 5 6 9H2v6h4l5 4V5z"/><path d="M15.54 8.46a5 5 0 0 1 0 7.07" stroke-linecap="round"/></svg>'
WARN_ICON = '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M12 9v4M12 17h.01M10.29 3.86 1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z" stroke-linecap="round" stroke-linejoin="round"/></svg>'

FIELDS_HTML = f'''<div class="tool-panel primary">
  <div class="panel-header">
    <span class="panel-icon">{SPEAKER_ICON}</span>
    <div><h2>Stereo Channel Test</h2><p class="panel-sub">Confirms each speaker or headphone side works, isn't swapped, and is balanced</p></div>
  </div>
  <div class="media-controls">
    <button type="button" class="btn-primary" id="btnLeft">Left Only</button>
    <button type="button" class="btn-primary" id="btnRight">Right Only</button>
    <button type="button" class="btn-primary" id="btnBoth">Both (Center)</button>
    <button type="button" class="btn-primary" id="btnAlternate">Alternating</button>
    <button type="button" class="btn-secondary" id="btnStop" disabled>Stop</button>
  </div>
  <div class="tool-field" style="margin-top:1.25rem">
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
    <div class="diagnostic-item"><span>Start at a low volume, then click a channel button. Nothing plays until you choose one.</span></div>
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

SCRIPT = '''(function () {
  'use strict';

  var btnLeft = document.getElementById('btnLeft');
  var btnRight = document.getElementById('btnRight');
  var btnBoth = document.getElementById('btnBoth');
  var btnAlternate = document.getElementById('btnAlternate');
  var btnStop = document.getElementById('btnStop');
  var volumeSlider = document.getElementById('volumeSlider');
  var volumeValue = document.getElementById('volumeValue');
  var outputSelectRow = document.getElementById('outputSelectRow');
  var outputSelect = document.getElementById('outputSelect');
  var diagnosticPanel = document.getElementById('diagnosticPanel');

  var MAX_GAIN = 0.4; // conservative ceiling -- see this site's safety notes for playback tools
  var RAMP_SECONDS = 0.02; // ramp every tone in/out to avoid audible clicks
  var TONE_FREQ = 440; // A4 -- a mid frequency every speaker can reproduce cleanly

  var audioCtx = null;
  var oscillator = null;
  var gainNode = null;
  var panner = null;
  var activeBtn = null;
  var alternateInterval = null;
  var alternateSide = -1; // -1 = left, 1 = right

  function setDiagnostic(items) {
    diagnosticPanel.innerHTML = items.map(function (it) {
      var sevClass = it.sev ? ' sev-' + it.sev : '';
      return '<div class="diagnostic-item' + sevClass + '"><span>' + it.html + '</span></div>';
    }).join('');
  }

  function ensureContext() {
    if (!audioCtx) {
      audioCtx = new (window.AudioContext || window.webkitAudioContext)();
    }
    // AudioContext starts suspended under autoplay policy -- this always
    // runs from inside a click handler (a real user gesture), so resume()
    // is allowed to succeed immediately.
    return audioCtx.state === 'suspended' ? audioCtx.resume().then(function () { return audioCtx; }) : Promise.resolve(audioCtx);
  }

  function currentGainTarget() {
    return (parseFloat(volumeSlider.value) / 100) * MAX_GAIN;
  }

  function clearAlternate() {
    if (alternateInterval) { clearInterval(alternateInterval); alternateInterval = null; }
  }

  function stopTone() {
    clearAlternate();
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
    panner = null;
    if (activeBtn) { activeBtn.classList.remove('active'); activeBtn = null; }
    btnStop.disabled = true;
  }

  function startTone(pan, btn) {
    return ensureContext().then(function () {
      stopTone();
      oscillator = audioCtx.createOscillator();
      gainNode = audioCtx.createGain();
      panner = audioCtx.createStereoPanner();
      oscillator.type = 'sine';
      oscillator.frequency.value = TONE_FREQ;
      gainNode.gain.value = 0;
      panner.pan.value = pan;
      oscillator.connect(gainNode);
      gainNode.connect(panner);
      panner.connect(audioCtx.destination);
      oscillator.start();
      var now = audioCtx.currentTime;
      gainNode.gain.linearRampToValueAtTime(currentGainTarget(), now + RAMP_SECONDS);

      if (btn) {
        activeBtn = btn;
        btn.classList.add('active');
      }
      btnStop.disabled = false;
    });
  }

  function playSide(side, btn) {
    var label = side < 0 ? 'left' : (side > 0 ? 'right' : 'both (centered)');
    startTone(side, btn).then(function () {
      setDiagnostic([{ sev: 'ok', html: '<strong>Playing ' + label + '.</strong> If you hear it on the wrong side, your channels may be swapped in your OS or cabling — see the guidance below.' }]);
    });
  }

  function playAlternating() {
    ensureContext().then(function () {
      stopTone();
      alternateSide = -1;
      oscillator = audioCtx.createOscillator();
      gainNode = audioCtx.createGain();
      panner = audioCtx.createStereoPanner();
      oscillator.type = 'sine';
      oscillator.frequency.value = TONE_FREQ;
      gainNode.gain.value = 0;
      panner.pan.value = alternateSide;
      oscillator.connect(gainNode);
      gainNode.connect(panner);
      panner.connect(audioCtx.destination);
      oscillator.start();
      var now = audioCtx.currentTime;
      gainNode.gain.linearRampToValueAtTime(currentGainTarget(), now + RAMP_SECONDS);

      activeBtn = btnAlternate;
      btnAlternate.classList.add('active');
      btnStop.disabled = false;
      setDiagnostic([{ sev: 'ok', html: '<strong>Alternating left / right.</strong> The side should switch roughly every second and a half.' }]);

      alternateInterval = setInterval(function () {
        if (!panner) return;
        alternateSide = alternateSide < 0 ? 1 : -1;
        panner.pan.setValueAtTime(alternateSide, audioCtx.currentTime);
        setDiagnostic([{ sev: 'ok', html: '<strong>Now playing: ' + (alternateSide < 0 ? 'left' : 'right') + '.</strong>' }]);
      }, 1500);
    });
  }

  btnLeft.addEventListener('click', function () { playSide(-1, btnLeft); });
  btnRight.addEventListener('click', function () { playSide(1, btnRight); });
  btnBoth.addEventListener('click', function () { playSide(0, btnBoth); });
  btnAlternate.addEventListener('click', playAlternating);
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
  // available instead of shipping a dead dropdown. Identical to
  // speaker-test-online.json's own initOutputDevices().
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
            setDiagnostic([{ sev: 'warn', html: 'Could not switch output device \\u2014 your browser rejected the request.' }]);
          });
        });
      });
    }).catch(function () {});
  }

  window.addEventListener('pagehide', function () {
    stopTone();
    if (audioCtx) audioCtx.close().catch(function () {});
  });
  document.addEventListener('visibilitychange', function () {
    if (document.visibilityState === 'hidden') stopTone();
  });

  initOutputDevices();
})();'''

CONTENT_HTML = '''<p>WebcamTest's stereo channel test plays a tone through your left speaker, your right speaker, both together, and alternating between them, so you can confirm both sides actually work, aren't swapped, and are reasonably balanced in volume. It's one of the highest-volume searches in this whole audio category — a surprisingly common and frustrating problem to diagnose without a dedicated tool.</p>
<h2>How to use it</h2>
<p>Start with <strong>Left Only</strong> and confirm sound comes only from your left speaker or headphone side, then <strong>Right Only</strong> for the same check on the right. <strong>Both (Center)</strong> plays through both sides evenly, useful for a basic "does it work at all" check. <strong>Alternating</strong> switches between left and right roughly every second and a half without you needing to click repeatedly — useful for confirming which physical side is which while you're not looking at the screen.</p>
<h2>If left and right sound swapped</h2>
<p>If <strong>Left Only</strong> plays from what feels like your right side, the most common causes, roughly in order of likelihood: headphones or earbuds put on the wrong way round, a 3.5mm cable wired unusually, or (less commonly) an operating-system audio setting that swaps channels. This page reports exactly what it requested — if what you hear doesn't match, the mismatch is happening downstream of the browser, in your hardware or OS settings.</p>
<h2>Why Bluetooth headphones sometimes sound mono</h2>
<p>Many Bluetooth headsets automatically drop from stereo audio to a lower-bandwidth mono "voice" profile the moment their microphone is also active — for a call, a voice assistant, or sometimes just an idle connection to certain devices. If both channels sound identical and centered no matter what this page does, that's very likely your Bluetooth connection collapsing to mono, not a fault with your headphones or this test. Try a wired connection, or check whether your OS shows the headset connected in a "stereo" vs. "hands-free/headset" audio profile.</p>
<h2>Nothing is uploaded</h2>
<p>Every tone is generated locally using the Web Audio API's oscillator and stereo panner nodes — nothing is played back from a file, recorded, or sent anywhere. See the <a href="/speaker-test-online">Speaker Test</a> for a broader low/mid/high frequency check if you also want to confirm your speakers reproduce different pitches evenly, not just left-versus-right.</p>'''

FAQ = [
    {"question": "Why does Left Only seem to play from my right side?", "answer": "This usually means headphones or earbuds are on the wrong way round, or a cable is wired unusually — this page always reports exactly which side it requested, so a mismatch means the swap is happening in your hardware or OS settings, not in this test."},
    {"question": "Why do both channels sound identical even though I'm testing separately?", "answer": "This is a common symptom of a Bluetooth headset that has dropped into its mono \"voice\" profile, which many devices do automatically the moment a microphone is also active on the connection. Try a wired connection, or check your OS's Bluetooth audio profile setting."},
    {"question": "What frequency is the test tone?", "answer": "440 Hz (musical note A4) — a mid-range frequency essentially every speaker and headphone can reproduce cleanly, so a channel or balance problem isn't confused with a frequency-response limitation."},
    {"question": "Is any audio uploaded or recorded?", "answer": "No. Every tone is generated locally in your browser using the Web Audio API. Nothing is played from a file, recorded, or sent to WebcamTest's servers or any third party."},
    {"question": "Why don't I see a device selector to choose my output?", "answer": "Output device selection depends on a browser API (setSinkId) that isn't available everywhere — mainly Chrome and Edge support it. If your browser doesn't, the picker is hidden automatically rather than shown as a non-functional control; switch your default output device in your operating system's own sound settings instead."},
]

TOOL = {
    "slug": "left-right-stereo-channel-test",
    "meta_title": "Left/Right Stereo Channel Test — Check for Swapped Speakers | WebcamTest",
    "meta_description": "Test your left and right speakers or headphones independently, plus an alternating mode. Free online stereo channel test — check for swapped channels or Bluetooth mono fallback.",
    "h1": "Left/Right Stereo Channel Test",
    "subtitle": "Play each speaker independently to confirm both sides work, aren't swapped, and are balanced.",
    "card": {
        "layout": "raw",
        "fields_html": FIELDS_HTML,
    },
    "script": SCRIPT,
    "content_html": CONTENT_HTML,
    "faq": FAQ,
}

if __name__ == "__main__":
    out_path = os.path.join(CONTENT_DIR, "left-right-stereo-channel-test.json")
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(TOOL, f, indent=2, ensure_ascii=False)
    print("Wrote", out_path)
