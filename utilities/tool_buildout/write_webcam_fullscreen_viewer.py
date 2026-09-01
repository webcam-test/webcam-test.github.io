#!/usr/bin/env python3
"""Writes src/content/webcam-fullscreen-viewer.json. Throwaway authoring
script, same pattern as write_webcam_test_online.py — see this project's
CLAUDE.md 'Authoring a new tool's content file'."""
import json
import os

BASE = os.path.dirname(os.path.abspath(__file__))
CONTENT_DIR = os.path.normpath(os.path.join(BASE, "..", "..", "src", "content"))

CAMERA_ICON = '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M23 7l-7 5 7 5V7z"/><rect x="1" y="5" width="15" height="14" rx="2" ry="2"/></svg>'
WARN_ICON = '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M12 9v4M12 17h.01M10.29 3.86 1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z" stroke-linecap="round" stroke-linejoin="round"/></svg>'
DOT_ICON = '<svg viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="9"/></svg>'
PLACEHOLDER_ICON = '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5"><path d="M23 7l-7 5 7 5V7z"/><rect x="1" y="5" width="15" height="14" rx="2" ry="2"/></svg>'
EXPAND_ICON = '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M8 3H5a2 2 0 0 0-2 2v3M16 3h3a2 2 0 0 1 2 2v3M21 16v3a2 2 0 0 1-2 2h-3M3 16v3a2 2 0 0 0 2 2h3" stroke-linecap="round" stroke-linejoin="round"/></svg>'

# NOT "primary" -- this tool has only 2 panels, so the hero uses span-2 (2
# cols, 1 row) and Status is a plain 1-col panel: 2+1=3 columns, tiles the
# grid exactly with no empty cells. Using "primary" (2 cols x 2 rows) here
# with only one side panel would leave a permanent empty grid cell, the same
# bug fixed on webcam-camera-information-report — see this site's CLAUDE.md
# for that story if it recurs.
FIELDS_HTML = f'''<div class="tool-panel span-2">
  <div class="panel-header">
    <span class="panel-icon">{CAMERA_ICON}</span>
    <div><h2>Live Camera Preview</h2><p class="panel-sub">Grant camera access, then go fullscreen for a clean, chrome-free view</p></div>
  </div>
  <div class="media-preview" id="cameraPreviewWrap">
    <video id="cameraVideo" autoplay playsinline muted></video>
    <div class="media-preview-placeholder" id="cameraPlaceholder">
      {PLACEHOLDER_ICON}
      <span>Your camera feed will appear here</span>
    </div>
    <div class="fullscreen-hint" id="fullscreenHint">Press Esc or tap to exit fullscreen</div>
  </div>
  <div class="media-controls">
    <button type="button" class="btn-primary" id="btnStartCamera">Start Camera</button>
    <button type="button" class="btn-secondary" id="btnStopCamera" disabled>Stop Camera</button>
    <button type="button" class="btn-secondary" id="btnMirrorToggle" aria-pressed="false" disabled>Mirror</button>
    <button type="button" class="btn-secondary btn-icon-text" id="btnFullscreen" disabled>{EXPAND_ICON}Fullscreen</button>
    <select class="device-select" id="deviceSelect" aria-label="Select camera" disabled>
      <option value="">Default camera</option>
    </select>
  </div>
</div>
<div class="tool-panel">
  <div class="panel-header">
    <span class="panel-icon">{WARN_ICON}</span>
    <div><h2>Status</h2><p class="panel-sub">What to do if the camera won't start</p></div>
  </div>
  <div class="diagnostic-panel" id="diagnosticPanel">
    <div class="diagnostic-item"><span class="diag-icon">{DOT_ICON}</span><span>Click <strong>Start Camera</strong> and allow access when your browser asks.</span></div>
  </div>
</div>'''

SCRIPT = '''(function () {
  'use strict';

  var video = document.getElementById('cameraVideo');
  var previewWrap = document.getElementById('cameraPreviewWrap');
  var placeholder = document.getElementById('cameraPlaceholder');
  var deviceSelect = document.getElementById('deviceSelect');
  var btnStart = document.getElementById('btnStartCamera');
  var btnStop = document.getElementById('btnStopCamera');
  var btnMirror = document.getElementById('btnMirrorToggle');
  var btnFullscreen = document.getElementById('btnFullscreen');
  var fullscreenHint = document.getElementById('fullscreenHint');
  var diagnosticPanel = document.getElementById('diagnosticPanel');

  var currentStream = null;
  var currentDeviceId = '';
  var starting = false;
  var wakeLock = null;
  var cursorTimer = null;
  var hintTimer = null;
  var pseudoFullscreen = false;

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

  // Every camera page on this site copies this stopStream()/enumerate/error
  // pattern from webcam-test-online.json (see this project's own CLAUDE.md).
  function stopStream() {
    if (isFullscreenActive()) exitFullscreenView();
    if (currentStream) {
      currentStream.getTracks().forEach(function (t) { t.stop(); });
      currentStream = null;
    }
    video.srcObject = null;
    previewWrap.classList.remove('is-active');
    placeholder.style.display = 'flex';
    btnStop.disabled = true;
    btnMirror.disabled = true;
    btnFullscreen.disabled = true;
  }

  function describeError(err) {
    switch (err && err.name) {
      case 'NotAllowedError':
      case 'PermissionDeniedError':
        return { sev: 'error', html: '<strong>Camera access was blocked.</strong> Click the camera icon in your address bar (or your browser\\u2019s site settings) and allow access, then try again.' };
      case 'NotFoundError':
      case 'DevicesNotFoundError':
        return { sev: 'error', html: '<strong>No camera was detected.</strong> Make sure a webcam is connected, then reload this page.' };
      case 'NotReadableError':
      case 'TrackStartError':
        return { sev: 'error', html: '<strong>Your camera is already in use.</strong> Another app or browser tab is probably holding it \\u2014 close video-calling apps or other camera tabs and try again.' };
      case 'OverconstrainedError':
      case 'ConstraintNotSatisfiedError':
        return { sev: 'error', html: '<strong>This camera doesn\\u2019t support the requested settings.</strong> Try a different camera from the list above.' };
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

  // Fullscreen entry/exit preserves the selected camera automatically --
  // the real Fullscreen API renders <video> fullscreen in place without
  // reparenting it, so its srcObject (the live stream) is never touched.
  // The pseudo-fullscreen fallback (position:fixed via CSS) is the same
  // element too, just repositioned, for the same reason.
  function isFullscreenActive() {
    return document.fullscreenElement === previewWrap || pseudoFullscreen;
  }

  function showHintBriefly() {
    fullscreenHint.classList.add('show');
    clearTimeout(hintTimer);
    hintTimer = setTimeout(function () { fullscreenHint.classList.remove('show'); }, 2500);
  }

  function resetCursorTimer() {
    previewWrap.classList.remove('is-cursor-hidden');
    clearTimeout(cursorTimer);
    cursorTimer = setTimeout(function () {
      previewWrap.classList.add('is-cursor-hidden');
    }, 3000);
  }

  function onFullscreenMouseMove() { resetCursorTimer(); }
  function onFullscreenKeydown(e) { if (e.key === 'Escape') exitFullscreenView(); }

  function requestWakeLock() {
    if (navigator.wakeLock && navigator.wakeLock.request) {
      navigator.wakeLock.request('screen').then(function (lock) { wakeLock = lock; }).catch(function () {});
    }
  }
  function releaseWakeLock() {
    if (wakeLock) {
      wakeLock.release().catch(function () {});
      wakeLock = null;
    }
  }

  function enterFullscreenView() {
    if (!currentStream || isFullscreenActive()) return;
    var request = previewWrap.requestFullscreen ? previewWrap.requestFullscreen() : null;
    if (request && request.then) {
      request.catch(function () { enterPseudoFullscreen(); });
    } else if (!document.fullscreenEnabled) {
      // iOS Safari and other browsers with no Fullscreen API at all.
      enterPseudoFullscreen();
    }
    // If the real request succeeds, the 'fullscreenchange' listener below
    // handles setup -- afterEnter() runs from there, not here, to stay in
    // sync with exits triggered by the browser's own fullscreen UI.
  }

  function enterPseudoFullscreen() {
    pseudoFullscreen = true;
    previewWrap.classList.add('is-pseudo-fullscreen');
    afterEnterFullscreen();
  }

  function afterEnterFullscreen() {
    btnFullscreen.textContent = 'Exit Fullscreen';
    previewWrap.addEventListener('mousemove', onFullscreenMouseMove);
    resetCursorTimer();
    showHintBriefly();
    requestWakeLock();
    // Real Fullscreen API is supposed to exit on Escape natively via the
    // browser's own handling, but that isn't reliably reachable from
    // page-level automation/testing input, and costs nothing to also
    // handle explicitly -- so this listener is attached for BOTH the real
    // and pseudo-fullscreen paths, not just the pseudo fallback.
    document.addEventListener('keydown', onFullscreenKeydown);
  }

  function exitFullscreenView() {
    if (document.fullscreenElement === previewWrap) {
      document.exitFullscreen();
      return; // afterExitFullscreen() runs from the fullscreenchange listener.
    }
    if (pseudoFullscreen) {
      pseudoFullscreen = false;
      previewWrap.classList.remove('is-pseudo-fullscreen');
      afterExitFullscreen();
    }
  }

  function afterExitFullscreen() {
    btnFullscreen.textContent = 'Fullscreen';
    previewWrap.removeEventListener('mousemove', onFullscreenMouseMove);
    clearTimeout(cursorTimer);
    previewWrap.classList.remove('is-cursor-hidden');
    fullscreenHint.classList.remove('show');
    releaseWakeLock();
    document.removeEventListener('keydown', onFullscreenKeydown);
  }

  document.addEventListener('fullscreenchange', function () {
    if (document.fullscreenElement === previewWrap) {
      afterEnterFullscreen();
    } else if (!pseudoFullscreen) {
      afterExitFullscreen();
    }
  });

  function startStream(deviceId) {
    if (starting) return;
    starting = true;
    stopStream();
    setDiagnostic([{ sev: '', html: 'Requesting camera access\\u2026' }]);
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
        btnStop.disabled = false;
        btnMirror.disabled = false;
        btnFullscreen.disabled = false;
        setDiagnostic([{ sev: 'ok', html: '<strong>Camera is live.</strong> Click <strong>Fullscreen</strong> for a clean, full-screen view.' }]);
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
  btnFullscreen.addEventListener('click', function () {
    if (isFullscreenActive()) { exitFullscreenView(); } else { enterFullscreenView(); }
  });
  previewWrap.addEventListener('click', function () {
    if (isFullscreenActive()) exitFullscreenView();
  });
  deviceSelect.addEventListener('change', function () {
    if (currentStream) startStream(deviceSelect.value);
  });

  // Guaranteed teardown: release the camera the moment the visitor leaves
  // this page, even if they never clicked Stop.
  window.addEventListener('pagehide', stopStream);
  document.addEventListener('visibilitychange', function () {
    if (document.visibilityState === 'hidden') stopStream();
  });

  if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) {
    setDiagnostic([{ sev: 'error', html: '<strong>Your browser doesn\\u2019t support camera access.</strong> Try the latest version of Chrome, Firefox, Edge, or Safari.' }]);
    btnStart.disabled = true;
  }
})();'''

CONTENT_HTML = '''<p>WebcamTest's fullscreen camera viewer shows your camera feed at full screen with every button and menu hidden, for checking framing at real size, inspecting image quality up close, or simply using your device as a mirror. It's a small, single-purpose tool, but it's one of the most frequently searched camera utilities on its own.</p>
<h2>What "fullscreen" actually does here</h2>
<p>Clicking <strong>Fullscreen</strong> requests the browser's real Fullscreen API on the preview panel itself — the same underlying mechanism video sites use for their player. Because the video element isn't recreated or moved in the page, your live camera stream keeps running exactly as it was; entering and leaving fullscreen never interrupts it or switches your selected camera.</p>
<h2>iPhone Safari works differently</h2>
<p>iOS Safari doesn't support the Fullscreen API the way desktop browsers and Android Chrome do. On an iPhone, this tool automatically falls back to a full-viewport view built with CSS instead — visually identical (camera feed filling the screen, all page chrome hidden), just achieved without the native browser API. You don't need to do anything differently; the fallback is automatic.</p>
<h2>Exiting fullscreen</h2>
<p>Press <kbd>Esc</kbd>, tap anywhere on the video, or click the Fullscreen button again (it becomes an Exit Fullscreen button once active). A small hint reminding you how to exit fades in briefly when you enter fullscreen, then fades out so it doesn't stay in the way.</p>
<h2>Why the cursor disappears</h2>
<p>If you stop moving the mouse for a few seconds while in fullscreen, the cursor hides itself automatically — the same convention video players use — so nothing overlaps the feed while you're just looking at it. Moving the mouse brings it straight back.</p>
<h2>Screen won't dim while you're checking framing</h2>
<p>Where your browser supports it, this page requests a screen wake lock while you're in fullscreen, so your laptop or phone display doesn't dim or lock itself mid-check. The wake lock releases automatically the moment you exit fullscreen or leave the page.</p>
<h2>Using it as a mirror</h2>
<p>The <strong>Mirror</strong> toggle flips the preview horizontally, which is what most people expect when using a webcam as a mirror to check their appearance. It's a local display-only flip — see the <a href="/">Webcam Test</a> page's own FAQ for why mirroring never affects the actual video data a real call would transmit.</p>'''

FAQ = [
    {"question": "Does entering fullscreen restart my camera or switch devices?", "answer": "No. The Fullscreen API renders the existing video element at full screen without recreating it, so your live camera stream and selected device are completely unaffected by entering or leaving fullscreen."},
    {"question": "Why doesn't fullscreen work the same way on my iPhone?", "answer": "iOS Safari doesn't implement the Fullscreen API for arbitrary page elements the way desktop browsers do. This tool detects that automatically and falls back to a full-viewport CSS view instead, which looks and behaves the same way — chrome hidden, feed filling the screen — without relying on that API."},
    {"question": "Why did my screen dim even though I was using this tool?", "answer": "The screen wake lock this page requests is only supported in some browsers, and some operating systems override it under low-battery power-saving modes regardless of what a web page requests. If your screen dims anyway, check your OS's own power settings."},
    {"question": "Is my camera feed uploaded anywhere during fullscreen viewing?", "answer": "No. Fullscreen only changes how the existing local video element is displayed on your own screen. Nothing about the video stream itself changes, and nothing is ever sent to WebcamTest's servers or any third party."},
    {"question": "The cursor disappeared and I can't find the exit button — what do I do?", "answer": "Move your mouse and it reappears immediately, or just press Esc / tap the screen to exit fullscreen without needing to see the button at all."},
]

TOOL = {
    "slug": "webcam-fullscreen-viewer",
    "meta_title": "Fullscreen Camera Viewer — Full-Screen Webcam & Mirror | WebcamTest",
    "meta_description": "View your webcam feed at full screen with no interface — check framing, inspect image quality, or use it as a mirror. Free, nothing uploaded.",
    "h1": "Fullscreen Camera Viewer",
    "subtitle": "See your camera feed at full screen with everything else hidden — for checking framing or using your device as a mirror.",
    "card": {
        "layout": "raw",
        "fields_html": FIELDS_HTML,
    },
    "script": SCRIPT,
    "content_html": CONTENT_HTML,
    "faq": FAQ,
}

if __name__ == "__main__":
    out_path = os.path.join(CONTENT_DIR, "webcam-fullscreen-viewer.json")
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(TOOL, f, indent=2, ensure_ascii=False)
    print("Wrote", out_path)
