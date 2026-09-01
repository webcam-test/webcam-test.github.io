#!/usr/bin/env python3
"""Writes src/content/webcam-test-online.json. Run once from anywhere; it
locates the content dir relative to this file. This is a throwaway authoring
script (same pattern as writing content by hand, just avoiding manual JSON
string-escaping for large HTML/JS blobs) — not part of the build pipeline."""
import json
import os

BASE = os.path.dirname(os.path.abspath(__file__))
CONTENT_DIR = os.path.normpath(os.path.join(BASE, "..", "..", "src", "content"))

CAMERA_ICON = '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M23 7l-7 5 7 5V7z"/><rect x="1" y="5" width="15" height="14" rx="2" ry="2"/></svg>'
INFO_ICON = '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="10"/><path d="M12 16v-4M12 8h.01" stroke-linecap="round"/></svg>'
WARN_ICON = '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M12 9v4M12 17h.01M10.29 3.86 1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z" stroke-linecap="round" stroke-linejoin="round"/></svg>'
DOT_ICON = '<svg viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="9"/></svg>'
PLACEHOLDER_ICON = '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5"><path d="M23 7l-7 5 7 5V7z"/><rect x="1" y="5" width="15" height="14" rx="2" ry="2"/></svg>'

FIELDS_HTML = f'''<div class="tool-panel primary">
  <div class="panel-header">
    <span class="panel-icon">{CAMERA_ICON}</span>
    <div><h2>Live Camera Preview</h2><p class="panel-sub">Grant camera access to begin — nothing is recorded or uploaded</p></div>
  </div>
  <div class="media-preview" id="cameraPreviewWrap">
    <video id="cameraVideo" autoplay playsinline muted></video>
    <div class="media-preview-placeholder" id="cameraPlaceholder">
      {PLACEHOLDER_ICON}
      <span>Your camera feed will appear here</span>
    </div>
  </div>
  <div class="media-controls">
    <button type="button" class="btn-primary" id="btnStartCamera">Start Camera</button>
    <button type="button" class="btn-secondary" id="btnStopCamera" disabled>Stop Camera</button>
    <button type="button" class="btn-secondary" id="btnMirrorToggle" aria-pressed="false" disabled>Mirror</button>
    <select class="device-select" id="deviceSelect" aria-label="Select camera" disabled>
      <option value="">Default camera</option>
    </select>
  </div>
</div>
<div class="tool-panel">
  <div class="panel-header">
    <span class="panel-icon">{INFO_ICON}</span>
    <div><h2>Camera Info</h2><p class="panel-sub">Reported once the camera is live</p></div>
  </div>
  <div class="stat-grid">
    <div class="stat-tile"><span class="stat-value" id="camStatResolution">—</span><span class="stat-label">Resolution</span></div>
    <div class="stat-tile"><span class="stat-value" id="camStatFps">—</span><span class="stat-label">Frame Rate</span></div>
    <div class="stat-tile"><span class="stat-value" id="camStatFacing">—</span><span class="stat-label">Facing</span></div>
    <div class="stat-tile"><span class="stat-value" id="camStatDeviceName" style="font-size:.75rem;word-break:break-word">—</span><span class="stat-label">Device</span></div>
  </div>
  <p class="field-note">Every value here is read directly from your browser's own camera API and stays on this page — see our <a href="/privacy-policy">privacy policy</a>.</p>
</div>
<div class="tool-panel">
  <div class="panel-header">
    <span class="panel-icon">{WARN_ICON}</span>
    <div><h2>Status</h2><p class="panel-sub">What to do if the camera won't start</p></div>
  </div>
  <div class="diagnostic-panel" id="diagnosticPanel">
    <div class="diagnostic-item" id="diagDefault"><span class="diag-icon">{DOT_ICON}</span><span>Click <strong>Start Camera</strong> and allow access when your browser asks.</span></div>
  </div>
</div>'''

SCRIPT = r'''(function () {
  'use strict';

  var video = document.getElementById('cameraVideo');
  var previewWrap = document.getElementById('cameraPreviewWrap');
  var placeholder = document.getElementById('cameraPlaceholder');
  var deviceSelect = document.getElementById('deviceSelect');
  var btnStart = document.getElementById('btnStartCamera');
  var btnStop = document.getElementById('btnStopCamera');
  var btnMirror = document.getElementById('btnMirrorToggle');
  var diagnosticPanel = document.getElementById('diagnosticPanel');
  var statResolution = document.getElementById('camStatResolution');
  var statFps = document.getElementById('camStatFps');
  var statFacing = document.getElementById('camStatFacing');
  var statDeviceName = document.getElementById('camStatDeviceName');

  var currentStream = null;
  var currentDeviceId = '';
  var starting = false;

  function escapeHtml(s) {
    var d = document.createElement('div');
    d.textContent = String(s);
    return d.innerHTML;
  }

  function setDiagnostic(items) {
    // items: [{sev: 'ok'|'warn'|'error'|'', html: '...'}]
    diagnosticPanel.innerHTML = items.map(function (it) {
      var sevClass = it.sev ? ' sev-' + it.sev : '';
      return '<div class="diagnostic-item' + sevClass + '"><span class="diag-icon">' +
        '<svg viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="9"/></svg>' +
        '</span><span>' + it.html + '</span></div>';
    }).join('');
  }

  function resetInfo() {
    statResolution.textContent = '—';
    statFps.textContent = '—';
    statFacing.textContent = '—';
    statDeviceName.textContent = '—';
  }

  // Every camera page on this site copies this stopStream()/enumerate/error
  // pattern as its starting point (see this project's own CLAUDE.md — "no
  // shared JS runtime file" is a deliberate choice, so teardown discipline
  // has to be copied verbatim into every tool's own script instead of
  // living in one shared file). Calling stop() on every track here is the
  // single highest-stakes correctness requirement on this whole site: skip
  // it and the browser's camera indicator light stays on after the visitor
  // has left the page.
  function stopStream() {
    if (currentStream) {
      currentStream.getTracks().forEach(function (t) { t.stop(); });
      currentStream = null;
    }
    video.srcObject = null;
    previewWrap.classList.remove('is-active');
    placeholder.style.display = 'flex';
    btnStop.disabled = true;
    btnMirror.disabled = true;
    resetInfo();
  }

  function describeError(err) {
    switch (err && err.name) {
      case 'NotAllowedError':
      case 'PermissionDeniedError':
        return { sev: 'error', html: '<strong>Camera access was blocked.</strong> Click the camera icon in your address bar (or your browser’s site settings) and allow access, then try again.' };
      case 'NotFoundError':
      case 'DevicesNotFoundError':
        return { sev: 'error', html: '<strong>No camera was detected.</strong> Make sure a webcam is connected, then reload this page.' };
      case 'NotReadableError':
      case 'TrackStartError':
        return { sev: 'error', html: '<strong>Your camera is already in use.</strong> Another app or browser tab is probably holding it — close video-calling apps or other camera tabs and try again.' };
      case 'OverconstrainedError':
      case 'ConstraintNotSatisfiedError':
        return { sev: 'error', html: '<strong>This camera doesn’t support the requested settings.</strong> Try a different camera from the list above.' };
      case 'SecurityError':
        return { sev: 'error', html: '<strong>Camera access requires a secure connection.</strong> Make sure this page is loaded over HTTPS.' };
      case 'AbortError':
        return { sev: 'warn', html: 'The camera request was interrupted. Click <strong>Start Camera</strong> to try again.' };
      default:
        return { sev: 'error', html: '<strong>Something went wrong starting the camera.</strong> ' + escapeHtml((err && err.message) || 'Unknown error') + '.' };
    }
  }

  function populateDeviceSelect(devices) {
    var cams = devices.filter(function (d) { return d.kind === 'videoinput'; });
    deviceSelect.innerHTML = '';
    if (!cams.length) {
      var opt = document.createElement('option');
      opt.value = '';
      opt.textContent = 'No cameras found';
      deviceSelect.appendChild(opt);
      deviceSelect.disabled = true;
      return;
    }
    cams.forEach(function (d, i) {
      var opt = document.createElement('option');
      opt.value = d.deviceId;
      opt.textContent = d.label || ('Camera ' + (i + 1));
      if (d.deviceId === currentDeviceId) opt.selected = true;
      deviceSelect.appendChild(opt);
    });
    deviceSelect.disabled = false;
  }

  function refreshDeviceList() {
    if (!navigator.mediaDevices || !navigator.mediaDevices.enumerateDevices) return Promise.resolve();
    return navigator.mediaDevices.enumerateDevices().then(populateDeviceSelect).catch(function () {});
  }

  function updateInfo(track) {
    var settings = track.getSettings ? track.getSettings() : {};
    statResolution.textContent = settings.width && settings.height ? (settings.width + '×' + settings.height) : '—';
    statFps.textContent = settings.frameRate ? (Math.round(settings.frameRate * 10) / 10 + ' fps') : '—';
    statFacing.textContent = settings.facingMode || 'Unspecified';
    statDeviceName.textContent = track.label || 'Camera';
  }

  function startStream(deviceId) {
    if (starting) return;
    starting = true;
    // Always fully release the previous stream before requesting a new
    // one — requesting a second stream while the first is still active
    // leaves the camera locked at the earlier resolution/device on many
    // browsers.
    stopStream();
    setDiagnostic([{ sev: '', html: 'Requesting camera access…' }]);
    btnStart.disabled = true;

    var videoConstraint = deviceId ? { deviceId: { exact: deviceId } } : true;
    navigator.mediaDevices.getUserMedia({ video: videoConstraint, audio: false })
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
        currentDeviceId = settings.deviceId || deviceId || '';
        updateInfo(track);
        btnStop.disabled = false;
        btnMirror.disabled = false;
        setDiagnostic([{ sev: 'ok', html: '<strong>Camera is live.</strong> Nothing is uploaded — this feed stays in your browser tab.' }]);
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

  btnStart.addEventListener('click', function () { startStream(deviceSelect.value); });
  btnStop.addEventListener('click', function () {
    stopStream();
    setDiagnostic([{ sev: '', html: 'Camera stopped. Click <strong>Start Camera</strong> to test again.' }]);
  });
  btnMirror.addEventListener('click', function () {
    var mirrored = previewWrap.classList.toggle('is-mirrored');
    btnMirror.setAttribute('aria-pressed', mirrored ? 'true' : 'false');
    btnMirror.classList.toggle('active', mirrored);
  });
  deviceSelect.addEventListener('change', function () {
    if (currentStream) startStream(deviceSelect.value);
  });

  // Guaranteed teardown: release the camera the moment the visitor leaves
  // this page, even if they never clicked Stop. pagehide covers back-
  // forward-cache navigations that 'unload' can miss.
  window.addEventListener('pagehide', stopStream);
  document.addEventListener('visibilitychange', function () {
    if (document.visibilityState === 'hidden') stopStream();
  });

  if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) {
    setDiagnostic([{ sev: 'error', html: '<strong>Your browser doesn’t support camera access.</strong> Try the latest version of Chrome, Firefox, Edge, or Safari.' }]);
    btnStart.disabled = true;
  }
})();'''

CONTENT_HTML = '''<p>WebcamTest's webcam test requests access to your camera, shows a live preview, and reports the resolution, frame rate and device name your browser actually negotiated — all without ever leaving your device. If you only run one test on this site, this is the one: every other camera tool here builds on the same acquisition and teardown logic this page uses.</p>
<h2>How this test works</h2>
<p>Click <strong>Start Camera</strong> and your browser will show its own native permission prompt — WebcamTest never sees or stores your decision, it only reads whatever your browser reports back. Once you allow access, the page requests a video stream using the standard <code>getUserMedia</code> API, plays it into the preview panel, and reads the negotiated resolution, frame rate, facing mode and device name back out of the stream using <code>getSettings()</code>.</p>
<p>If you have more than one camera connected — a laptop's built-in webcam plus an external USB camera, for example — the device dropdown lets you switch between them without granting permission twice. Device names only become visible to a webpage <em>after</em> permission has been granted, which is a browser privacy protection, not a bug in this tool.</p>
<h2>Why the camera always turns off when you leave</h2>
<p>This site is built around one non-negotiable rule: your camera's indicator light must never stay on after you've stopped using a tool. Clicking Stop, navigating to another page, or switching browser tabs all immediately release every camera track this page opened. If you ever see this site's camera indicator stay lit after you've left the page, that is a bug — please <a href="/contact">let us know</a>.</p>
<h2>Why some fields might not appear</h2>
<p>Not every browser reports every field. Firefox, for example, doesn't implement <code>getCapabilities()</code>, which some of the other tools on this site rely on for extra hardware detail — this page only uses <code>getSettings()</code>, which is far more broadly supported, so it should work consistently across Chrome, Edge, Firefox and Safari. If your camera doesn't report a frame rate or facing mode at all, that's the hardware or driver declining to expose it, not a failure of this page.</p>
<h2>Troubleshooting a camera that won't start</h2>
<p>The status panel on this page explains exactly what went wrong using your browser's own error type rather than a single generic failure message. The most common causes, in order of likelihood: the permission prompt was dismissed or previously blocked, another application (a video-calling app, another browser tab) is already holding the camera exclusively, or no camera is connected at all. Each of those needs a different fix, which is why this page reports them separately instead of one catch-all "camera error."</p>'''

FAQ = [
    {"question": "Is my camera feed uploaded anywhere?", "answer": "No. The video stream is processed entirely by your browser using JavaScript running on this page. It is never sent to WebcamTest's servers or any third party."},
    {"question": "Why does my browser ask for camera permission every time?", "answer": "Browsers only remember a permission grant for the exact origin (domain) you're visiting, and some browser/privacy-mode combinations ask again every visit by design. This is a browser behavior, not something this site controls."},
    {"question": "The page says my camera is in use, but I don't have any other apps open. What's happening?", "answer": "Check for background apps that can silently hold a camera: video-calling software running in the system tray, another browser tab with an active camera test, or an OS-level camera utility. On Windows, background apps with camera access are listed in Settings → Privacy → Camera."},
    {"question": "Why does my resolution show lower than my camera's advertised specs?", "answer": "This page reports what the browser actually negotiated with your camera driver, which is frequently lower than a camera's maximum advertised resolution. Use the Maximum Resolution Detector to probe for the true ceiling your browser can reach."},
    {"question": "Does the mirror toggle affect what other people see on a call?", "answer": "No. Mirroring here is a local preview convenience only, applied with a CSS transform after the video is already captured. It has no effect on the actual video data your browser would transmit in a call."},
]

TOOL = {
    "slug": "webcam-test-online",
    "meta_title": "Webcam Test — Check Your Camera Online Free | WebcamTest",
    "meta_description": "Test your webcam online for free. See a live preview, switch between connected cameras, and check the resolution, frame rate and device name your browser detects. Nothing is uploaded.",
    "h1": "Webcam Test",
    "subtitle": "Check that your camera works, see a live preview, and read its real resolution and frame rate — entirely in your browser.",
    "card": {
        "layout": "raw",
        "fields_html": FIELDS_HTML,
    },
    "script": SCRIPT,
    "content_html": CONTENT_HTML,
    "faq": FAQ,
}

if __name__ == "__main__":
    out_path = os.path.join(CONTENT_DIR, "webcam-test-online.json")
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(TOOL, f, indent=2, ensure_ascii=False)
    print("Wrote", out_path)
