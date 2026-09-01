#!/usr/bin/env python3
"""Writes src/content/phone-camera-flash-torch-test.json."""
import json
import os

BASE = os.path.dirname(os.path.abspath(__file__))
CONTENT_DIR = os.path.normpath(os.path.join(BASE, "..", "..", "src", "content"))

CAMERA_ICON = '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M23 7l-7 5 7 5V7z"/><rect x="1" y="5" width="15" height="14" rx="2" ry="2"/></svg>'
BOLT_ICON = '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M13 2L3 14h7l-1 8 10-12h-7l1-8z" stroke-linecap="round" stroke-linejoin="round"/></svg>'
PHONE_ICON = '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect x="6" y="2" width="12" height="20" rx="2"/><path d="M11 18h2" stroke-linecap="round"/></svg>'
DOT_ICON = '<svg viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="9"/></svg>'
PLACEHOLDER_ICON = '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5"><path d="M23 7l-7 5 7 5V7z"/><rect x="1" y="5" width="15" height="14" rx="2" ry="2"/></svg>'

FIELDS_HTML = f'''<div class="tool-panel primary">
  <div class="panel-header">
    <span class="panel-icon">{CAMERA_ICON}</span>
    <div><h2>Flash &amp; Torch Test</h2><p class="panel-sub">Starts your rear camera, since torch is only ever exposed on a rear-facing lens</p></div>
  </div>
  <div class="media-preview" id="cameraPreviewWrap">
    <video id="cameraVideo" autoplay playsinline muted></video>
    <div class="media-preview-placeholder" id="cameraPlaceholder">
      {PLACEHOLDER_ICON}
      <span>Your camera feed will appear here</span>
    </div>
  </div>
  <div class="media-controls" style="margin-top:1rem">
    <button type="button" class="btn-primary" id="btnStartCamera">Start Camera</button>
    <button type="button" class="btn-secondary" id="btnStopCamera" disabled>Stop Camera</button>
    <select class="device-select" id="deviceSelect" aria-label="Select camera" disabled>
      <option value="">Default camera</option>
    </select>
  </div>
  <div class="tool-actions" style="margin-top:1rem">
    <button type="button" class="btn-primary" id="btnToggleTorch" disabled>Turn Torch On</button>
  </div>
  <div class="diagnostic-panel" id="diagnosticPanel" style="margin-top:1rem">
    <div class="diagnostic-item" id="diagDefault"><span class="diag-icon">{DOT_ICON}</span><span>Click <strong>Start Camera</strong> and allow access when your browser asks.</span></div>
  </div>
</div>
<div class="tool-panel">
  <div class="panel-header">
    <span class="panel-icon">{BOLT_ICON}</span>
    <div><h2>Full-Screen White Light</h2><p class="panel-sub">A screen-brightness alternative when torch control isn't available</p></div>
  </div>
  <p class="field-note" style="margin-top:0">Most phones don't let a website control the physical LED flash directly — iOS Safari never exposes it at all, and only some Android browsers do. This turns your whole screen into a bright white light instead, useful as a close-range light source or a substitute for the torch this page can't reach.</p>
  <button type="button" class="btn-secondary" id="btnWhiteScreen">Open Full-Screen White Light</button>
</div>
<div class="tool-panel">
  <div class="panel-header">
    <span class="panel-icon">{PHONE_ICON}</span>
    <div><h2>Testing the Real Flash</h2><p class="panel-sub">When browser torch control isn't supported</p></div>
  </div>
  <p class="field-note" style="margin-top:0">To test the actual LED flash hardware (not just this page's ability to control it), open your phone's native Camera app, switch to video or flashlight mode, and toggle the flash there. If it doesn't light up from the native app either, that points to an actual hardware fault rather than a browser limitation.</p>
</div>
<div class="media-preview is-pseudo-fullscreen" id="whiteScreenOverlay" style="display:none;position:fixed;inset:0;z-index:9999;background:#fff;aspect-ratio:auto;border-radius:0;align-items:center;justify-content:center">
  <button type="button" class="btn-secondary" id="btnCloseWhiteScreen" style="position:absolute;top:1.5rem;right:1.5rem;z-index:2">Close</button>
</div>'''

SCRIPT = r'''(function () {
  'use strict';

  var video = document.getElementById('cameraVideo');
  var previewWrap = document.getElementById('cameraPreviewWrap');
  var placeholder = document.getElementById('cameraPlaceholder');
  var deviceSelect = document.getElementById('deviceSelect');
  var btnStart = document.getElementById('btnStartCamera');
  var btnStop = document.getElementById('btnStopCamera');
  var btnToggleTorch = document.getElementById('btnToggleTorch');
  var diagnosticPanel = document.getElementById('diagnosticPanel');
  var btnWhiteScreen = document.getElementById('btnWhiteScreen');
  var btnCloseWhiteScreen = document.getElementById('btnCloseWhiteScreen');
  var whiteScreenOverlay = document.getElementById('whiteScreenOverlay');

  var currentStream = null;
  var starting = false;
  var torchOn = false;
  var torchSupported = false;

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

  // Same stopStream()/describeError()/populateDeviceSelect() pattern as
  // webcam-test-online's own script (see this project's CLAUDE.md -- every
  // camera tool copies this teardown block rather than importing a shared file).
  function stopStream() {
    if (currentStream) {
      currentStream.getTracks().forEach(function (t) { t.stop(); });
      currentStream = null;
    }
    video.srcObject = null;
    previewWrap.classList.remove('is-active');
    placeholder.style.display = 'flex';
    btnStop.disabled = true;
    btnToggleTorch.disabled = true;
    btnToggleTorch.textContent = 'Turn Torch On';
    torchOn = false;
    torchSupported = false;
  }

  function describeError(err) {
    switch (err && err.name) {
      case 'NotAllowedError':
      case 'PermissionDeniedError':
        return { sev: 'error', html: '<strong>Camera access was blocked.</strong> Allow access from your browser’s address-bar icon or site settings, then try again.' };
      case 'NotFoundError':
      case 'DevicesNotFoundError':
        return { sev: 'error', html: '<strong>No camera was detected.</strong> Connect a camera and reload this page.' };
      case 'NotReadableError':
      case 'TrackStartError':
        return { sev: 'error', html: '<strong>Your camera is already in use</strong> by another app or browser tab.' };
      case 'OverconstrainedError':
        return { sev: 'error', html: '<strong>This camera doesn’t support the requested settings.</strong> Try another camera from the list.' };
      case 'SecurityError':
        return { sev: 'error', html: '<strong>Camera access requires HTTPS.</strong>' };
      default:
        return { sev: 'error', html: '<strong>Something went wrong starting the camera.</strong> ' + escapeHtml((err && err.message) || 'Unknown error') + '.' };
    }
  }

  function populateDeviceSelect(devices, currentDeviceId) {
    var cams = devices.filter(function (d) { return d.kind === 'videoinput'; });
    deviceSelect.innerHTML = '';
    cams.forEach(function (d, i) {
      var opt = document.createElement('option');
      opt.value = d.deviceId;
      opt.textContent = d.label || ('Camera ' + (i + 1));
      if (d.deviceId === currentDeviceId) opt.selected = true;
      deviceSelect.appendChild(opt);
    });
    deviceSelect.disabled = cams.length === 0;
  }

  // Torch capability only ever appears while a rear-camera stream is active,
  // per this tool's own spec note -- request facingMode:environment so
  // phones default to the lens that actually has a flash next to it.
  function startStream(deviceId) {
    if (starting) return;
    starting = true;
    stopStream();
    setDiagnostic([{ sev: '', html: 'Requesting camera access…' }]);
    btnStart.disabled = true;

    var constraints = deviceId
      ? { video: { deviceId: { exact: deviceId } }, audio: false }
      : { video: { facingMode: { ideal: 'environment' } }, audio: false };

    navigator.mediaDevices.getUserMedia(constraints)
      .then(function (stream) {
        currentStream = stream;
        video.srcObject = stream;
        placeholder.style.display = 'none';
        previewWrap.classList.add('is-active');
        return video.play().catch(function () {}).then(function () { return stream; });
      })
      .then(function (stream) {
        var track = stream.getVideoTracks()[0];
        var settings = track.getSettings ? track.getSettings() : {};
        var caps = track.getCapabilities ? (function () { try { return track.getCapabilities(); } catch (e) { return null; } })() : null;
        btnStop.disabled = false;
        torchSupported = !!(caps && caps.torch);
        if (torchSupported) {
          btnToggleTorch.disabled = false;
          setDiagnostic([{ sev: 'ok', html: '<strong>Camera is live and torch control is available.</strong> Use the button above to toggle it.' }]);
        } else {
          btnToggleTorch.disabled = true;
          setDiagnostic([{ sev: 'warn', html: '<strong>Camera is live, but this browser can’t control the flash directly.</strong> This is expected on iPhone (Safari never exposes torch to web pages) and on many Android browsers too — use the full-screen white light or your native camera app instead.' }]);
        }
        return navigator.mediaDevices.enumerateDevices().then(function (devices) {
          populateDeviceSelect(devices, settings.deviceId);
        });
      })
      .catch(function (err) { setDiagnostic([describeError(err)]); stopStream(); })
      .finally(function () { starting = false; btnStart.disabled = false; });
  }

  function toggleTorch() {
    if (!currentStream || !torchSupported) return;
    var track = currentStream.getVideoTracks()[0];
    var next = !torchOn;
    track.applyConstraints({ advanced: [{ torch: next }] })
      .then(function () {
        torchOn = next;
        btnToggleTorch.textContent = torchOn ? 'Turn Torch Off' : 'Turn Torch On';
        setDiagnostic([{ sev: 'ok', html: torchOn ? '<strong>Torch on.</strong> Confirm the LED next to the rear lens is lit.' : 'Torch turned off.' }]);
      })
      .catch(function () {
        setDiagnostic([{ sev: 'error', html: '<strong>Couldn’t toggle the torch</strong> even though it was reported as supported. Try the full-screen white light instead.' }]);
      });
  }

  function openWhiteScreen() {
    whiteScreenOverlay.style.display = 'flex';
    document.addEventListener('keydown', onWhiteScreenKeydown);
  }
  function closeWhiteScreen() {
    whiteScreenOverlay.style.display = 'none';
    document.removeEventListener('keydown', onWhiteScreenKeydown);
  }
  function onWhiteScreenKeydown(e) { if (e.key === 'Escape') closeWhiteScreen(); }

  btnStart.addEventListener('click', function () { startStream(deviceSelect.value); });
  btnStop.addEventListener('click', function () {
    stopStream();
    setDiagnostic([{ sev: '', html: 'Camera stopped.' }]);
  });
  deviceSelect.addEventListener('change', function () { if (currentStream) startStream(deviceSelect.value); });
  btnToggleTorch.addEventListener('click', toggleTorch);
  btnWhiteScreen.addEventListener('click', openWhiteScreen);
  btnCloseWhiteScreen.addEventListener('click', closeWhiteScreen);

  window.addEventListener('pagehide', stopStream);
  document.addEventListener('visibilitychange', function () {
    if (document.visibilityState === 'hidden') stopStream();
  });

  if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) {
    setDiagnostic([{ sev: 'error', html: '<strong>Your browser doesn’t support camera access.</strong>' }]);
    btnStart.disabled = true;
  }
})();'''

CONTENT_HTML = '''<p>This tool tests whether your phone's rear LED flash can be controlled directly from a web page, and gives you two working alternatives for the many devices and browsers where it can't.</p>
<h2>Why torch control is so inconsistent</h2>
<p>The torch capability is part of the same camera API used everywhere else on this site, but almost no browser supports it fully. iOS Safari never exposes torch control to any website, on any iPhone, under any circumstances — this is an Apple platform restriction, not something this page (or any other) can work around. Some Android browsers support it, but only while a rear-camera stream is actively running, and only on certain phone models. If this page reports torch as unavailable, that's expected on the large majority of devices, not a fault with your phone.</p>
<h2>The full-screen white light alternative</h2>
<p>When direct torch control isn't available, turning your entire screen into a bright white rectangle is a genuinely useful substitute for close-range lighting — it's the same trick many dedicated "flashlight" apps use on devices without an LED flash at all. It won't be as bright as a real LED flash, but it's instant and works on every device.</p>
<h2>Testing the physical flash hardware directly</h2>
<p>If you specifically need to confirm the LED flash itself works — for example, checking a used phone before buying it — your phone's own native camera app is the most reliable test, since it talks to the camera hardware directly rather than through a browser's limited API. If the flash doesn't respond there either, that points to an actual hardware issue rather than a browser limitation.</p>'''

FAQ = [
    {"question": "Why doesn't this work on my iPhone?", "answer": "iOS Safari doesn't expose torch control to any website — this is a restriction Apple applies platform-wide, not a bug in this page. Use the full-screen white light option instead, or test the flash directly through your phone's native camera app."},
    {"question": "The camera is live but the torch button is disabled — is my flash broken?", "answer": "Not necessarily. Many Android browsers and most iPhones simply don't let web pages control the torch at all, even when the flash hardware itself works fine. Test the actual LED using your phone's native camera app to rule out a hardware issue."},
    {"question": "Does the full-screen white light actually make my screen brighter?", "answer": "It sets your screen content to solid white, which is as bright as your screen's current brightness setting allows — it doesn't increase your device's maximum brightness. For the most light, turn your screen brightness up manually before opening it."},
    {"question": "Why does this tool start my rear camera specifically?", "answer": "The torch/flash LED is physically attached to the rear camera on virtually every phone, and the browser only exposes torch capability while a rear-facing camera stream is active — so this tool requests the rear lens by default."},
]

TOOL = {
    "slug": "phone-camera-flash-torch-test",
    "meta_title": "Phone Flash & Torch Test — Check Your LED Flash Online | WebcamTest",
    "meta_description": "Test whether your phone's LED torch responds to browser control, with a full-screen white light alternative and native camera app instructions for devices where it doesn't.",
    "h1": "Flash and Torch Test",
    "subtitle": "Tests whether your phone's flash responds to browser control, with a full-screen white light and native camera app fallback.",
    "card": {
        "layout": "raw",
        "fields_html": FIELDS_HTML,
    },
    "script": SCRIPT,
    "content_html": CONTENT_HTML,
    "faq": FAQ,
}

if __name__ == "__main__":
    out_path = os.path.join(CONTENT_DIR, "phone-camera-flash-torch-test.json")
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(TOOL, f, indent=2, ensure_ascii=False)
    print("Wrote", out_path)
