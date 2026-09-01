#!/usr/bin/env python3
"""Writes src/content/webcam-rule-of-thirds-composition-grid.json."""
import json
import os

BASE = os.path.dirname(os.path.abspath(__file__))
CONTENT_DIR = os.path.normpath(os.path.join(BASE, "..", "..", "src", "content"))

CAMERA_ICON = '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M23 7l-7 5 7 5V7z"/><rect x="1" y="5" width="15" height="14" rx="2" ry="2"/></svg>'
GRID_ICON = '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect x="3" y="3" width="18" height="18" rx="2"/><path d="M3 9h18M3 15h18M9 3v18M15 3v18"/></svg>'
INFO_ICON = '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="10"/><path d="M12 16v-4M12 8h.01" stroke-linecap="round"/></svg>'
DOT_ICON = '<svg viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="9"/></svg>'
PLACEHOLDER_ICON = '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5"><path d="M23 7l-7 5 7 5V7z"/><rect x="1" y="5" width="15" height="14" rx="2" ry="2"/></svg>'

FIELDS_HTML = f'''<div class="tool-panel primary">
  <div class="panel-header">
    <span class="panel-icon">{CAMERA_ICON}</span>
    <div><h2>Composition Grid</h2><p class="panel-sub">Framing guides overlaid on your live feed — position yourself using the grid below</p></div>
  </div>
  <div class="media-preview" id="cameraPreviewWrap">
    <video id="cameraVideo" autoplay playsinline muted></video>
    <canvas id="overlayCanvas"></canvas>
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
  <div class="diagnostic-panel" id="diagnosticPanel" style="margin-top:1rem">
    <div class="diagnostic-item" id="diagDefault"><span class="diag-icon">{DOT_ICON}</span><span>Click <strong>Start Camera</strong> and allow access when your browser asks.</span></div>
  </div>
</div>
<div class="tool-panel">
  <div class="panel-header">
    <span class="panel-icon">{GRID_ICON}</span>
    <div><h2>Guides</h2><p class="panel-sub">Toggle each on or off</p></div>
  </div>
  <div class="tool-actions">
    <button type="button" class="btn-secondary" id="btnToggleThirds" aria-pressed="true">Rule of Thirds</button>
    <button type="button" class="btn-secondary" id="btnToggleCentre" aria-pressed="false">Centre Lines</button>
    <button type="button" class="btn-secondary" id="btnToggleEyeLevel" aria-pressed="true">Eye Level</button>
    <button type="button" class="btn-secondary" id="btnToggleHeadroom" aria-pressed="true">Headroom Band</button>
    <button type="button" class="btn-secondary" id="btnToggleSafeArea" aria-pressed="false">Safe Area</button>
  </div>
</div>
<div class="tool-panel">
  <div class="panel-header">
    <span class="panel-icon">{INFO_ICON}</span>
    <div><h2>Framing Tips</h2></div>
  </div>
  <p class="field-note" style="margin-top:0"><strong>Eye level:</strong> aim to have your eyes sit on or near the upper third line, not the exact centre — this is the single biggest framing improvement most people can make.</p>
  <p class="field-note"><strong>Headroom:</strong> leave a small, even gap above your head rather than a large empty band — too much headroom pushes your face down and out of the frame's visual centre.</p>
  <p class="field-note" style="margin-bottom:0"><strong>Safe area:</strong> keep your face and shoulders within the inner rectangle so nothing important gets cropped on displays that don't show the full frame edge-to-edge.</p>
</div>'''

SCRIPT = r'''(function () {
  'use strict';

  var video = document.getElementById('cameraVideo');
  var previewWrap = document.getElementById('cameraPreviewWrap');
  var placeholder = document.getElementById('cameraPlaceholder');
  var canvas = document.getElementById('overlayCanvas');
  var ctx = canvas.getContext('2d');
  var deviceSelect = document.getElementById('deviceSelect');
  var btnStart = document.getElementById('btnStartCamera');
  var btnStop = document.getElementById('btnStopCamera');
  var diagnosticPanel = document.getElementById('diagnosticPanel');

  var toggles = {
    thirds: document.getElementById('btnToggleThirds'),
    centre: document.getElementById('btnToggleCentre'),
    eyeLevel: document.getElementById('btnToggleEyeLevel'),
    headroom: document.getElementById('btnToggleHeadroom'),
    safeArea: document.getElementById('btnToggleSafeArea'),
  };
  var guideState = { thirds: true, centre: false, eyeLevel: true, headroom: true, safeArea: false };

  var currentStream = null;
  var starting = false;
  var resizeObserver = null;

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

  // The video element uses object-fit:contain, so its rendered content box
  // is almost never the same as the element's own box -- a camera with a
  // different aspect ratio than the 16:9 container letterboxes or
  // pillarboxes. Guides drawn against the element box (ignoring this) sit
  // in the wrong place, per this tool's own spec note.
  function computeContentBox() {
    var elW = video.clientWidth, elH = video.clientHeight;
    var vw = video.videoWidth, vh = video.videoHeight;
    if (!vw || !vh || !elW || !elH) return { x: 0, y: 0, w: elW, h: elH };
    var elRatio = elW / elH, vRatio = vw / vh;
    var w, h;
    if (vRatio > elRatio) {
      w = elW;
      h = elW / vRatio;
    } else {
      h = elH;
      w = elH * vRatio;
    }
    return { x: (elW - w) / 2, y: (elH - h) / 2, w: w, h: h };
  }

  function drawGuides() {
    var dpr = window.devicePixelRatio || 1;
    var elW = video.clientWidth, elH = video.clientHeight;
    canvas.width = Math.max(1, Math.round(elW * dpr));
    canvas.height = Math.max(1, Math.round(elH * dpr));
    ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
    ctx.clearRect(0, 0, elW, elH);
    if (!currentStream) return;

    var box = computeContentBox();
    ctx.strokeStyle = 'rgba(255,255,255,.7)';
    ctx.lineWidth = 1;

    if (guideState.thirds) {
      [1 / 3, 2 / 3].forEach(function (f) {
        ctx.beginPath();
        ctx.moveTo(box.x + box.w * f, box.y);
        ctx.lineTo(box.x + box.w * f, box.y + box.h);
        ctx.stroke();
        ctx.beginPath();
        ctx.moveTo(box.x, box.y + box.h * f);
        ctx.lineTo(box.x + box.w, box.y + box.h * f);
        ctx.stroke();
      });
    }

    if (guideState.centre) {
      ctx.save();
      ctx.strokeStyle = 'rgba(124,92,255,.85)';
      ctx.beginPath();
      ctx.moveTo(box.x + box.w / 2, box.y);
      ctx.lineTo(box.x + box.w / 2, box.y + box.h);
      ctx.moveTo(box.x, box.y + box.h / 2);
      ctx.lineTo(box.x + box.w, box.y + box.h / 2);
      ctx.stroke();
      ctx.restore();
    }

    if (guideState.eyeLevel) {
      ctx.save();
      ctx.strokeStyle = 'rgba(52,211,153,.9)';
      ctx.lineWidth = 2;
      ctx.setLineDash([6, 4]);
      var eyeY = box.y + box.h * (1 / 3);
      ctx.beginPath();
      ctx.moveTo(box.x, eyeY);
      ctx.lineTo(box.x + box.w, eyeY);
      ctx.stroke();
      ctx.setLineDash([]);
      ctx.fillStyle = 'rgba(52,211,153,.9)';
      ctx.font = '11px sans-serif';
      ctx.fillText('Eye level', box.x + 6, eyeY - 6);
      ctx.restore();
    }

    if (guideState.headroom) {
      ctx.save();
      ctx.fillStyle = 'rgba(251,191,36,.18)';
      var bandH = box.h * 0.08;
      ctx.fillRect(box.x, box.y, box.w, bandH);
      ctx.strokeStyle = 'rgba(251,191,36,.8)';
      ctx.beginPath();
      ctx.moveTo(box.x, box.y + bandH);
      ctx.lineTo(box.x + box.w, box.y + bandH);
      ctx.stroke();
      ctx.restore();
    }

    if (guideState.safeArea) {
      ctx.save();
      ctx.strokeStyle = 'rgba(255,255,255,.9)';
      ctx.setLineDash([4, 4]);
      var inset = 0.08;
      ctx.strokeRect(box.x + box.w * inset, box.y + box.h * inset, box.w * (1 - inset * 2), box.h * (1 - inset * 2));
      ctx.setLineDash([]);
      ctx.restore();
    }
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
    ctx.clearRect(0, 0, canvas.width, canvas.height);
  }

  function describeError(err) {
    switch (err && err.name) {
      case 'NotAllowedError':
      case 'PermissionDeniedError':
        return { sev: 'error', html: '<strong>Camera access was blocked.</strong> Allow access from your browser’s address-bar icon or site settings, then try again.' };
      case 'NotFoundError':
      case 'DevicesNotFoundError':
        return { sev: 'error', html: '<strong>No camera was detected.</strong> Connect a webcam and reload this page.' };
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

  function startStream(deviceId) {
    if (starting) return;
    starting = true;
    stopStream();
    setDiagnostic([{ sev: '', html: 'Requesting camera access…' }]);
    btnStart.disabled = true;

    navigator.mediaDevices.getUserMedia({ video: deviceId ? { deviceId: { exact: deviceId } } : true, audio: false })
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
        btnStop.disabled = false;
        setDiagnostic([{ sev: 'ok', html: '<strong>Camera is live.</strong> Use the guides to position yourself, then toggle any you don’t need.' }]);
        drawGuides();
        return navigator.mediaDevices.enumerateDevices().then(function (devices) {
          populateDeviceSelect(devices, settings.deviceId);
        });
      })
      .catch(function (err) { setDiagnostic([describeError(err)]); stopStream(); })
      .finally(function () { starting = false; btnStart.disabled = false; });
  }

  function bindToggle(key, btn) {
    btn.addEventListener('click', function () {
      guideState[key] = !guideState[key];
      btn.setAttribute('aria-pressed', String(guideState[key]));
      drawGuides();
    });
  }
  Object.keys(toggles).forEach(function (key) { bindToggle(key, toggles[key]); });

  btnStart.addEventListener('click', function () { startStream(deviceSelect.value); });
  btnStop.addEventListener('click', function () {
    stopStream();
    setDiagnostic([{ sev: '', html: 'Camera stopped.' }]);
  });
  deviceSelect.addEventListener('change', function () { if (currentStream) startStream(deviceSelect.value); });

  // Recompute on resize (viewport changes, panel reflow) rather than once
  // at start -- the overlay must track the video element's rendered box,
  // not the stream's native resolution, per this tool's own spec note.
  if (window.ResizeObserver) {
    resizeObserver = new ResizeObserver(function () { drawGuides(); });
    resizeObserver.observe(previewWrap);
  } else {
    window.addEventListener('resize', drawGuides);
  }

  window.addEventListener('pagehide', stopStream);
  document.addEventListener('visibilitychange', function () {
    if (document.visibilityState === 'hidden') stopStream();
  });

  if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) {
    setDiagnostic([{ sev: 'error', html: '<strong>Your browser doesn’t support camera access.</strong>' }]);
    btnStart.disabled = true;
  }
})();'''

CONTENT_HTML = '''<p>Good framing on a video call comes down to a handful of simple positioning rules that are hard to judge just by glancing at your own preview. This tool overlays the same guides photographers and video editors use directly on your live camera feed.</p>
<h2>The guides, explained</h2>
<p><strong>Rule of thirds</strong> divides the frame into a 3×3 grid — placing your eyes or face near one of the intersection points generally looks more balanced than dead centre. <strong>Centre lines</strong> mark the exact horizontal and vertical middle, useful for checking you're not accidentally off to one side. <strong>Eye level</strong> highlights the recommended line for where your eyes should sit — roughly the upper third of the frame, not the vertical centre. <strong>Headroom band</strong> shows how much empty space sits above your head; too much pushes your face down and out of the visually important area. <strong>Safe area</strong> marks an inner rectangle so nothing important gets cropped on displays or apps that don't show the full frame edge-to-edge.</p>
<h2>Why the guides track your camera's exact shape</h2>
<p>Every guide is drawn against the actual visible content of your video, not just the preview box — since your camera's aspect ratio can differ from the frame around it, the video is displayed with letterboxing or pillarboxing rather than stretched. The guides account for that automatically and stay correctly positioned regardless of your camera's native resolution.</p>'''

FAQ = [
    {"question": "Does this change what other people see on my call?", "answer": "No — the guides are an overlay shown only to you on this page, purely to help you position yourself before or during a call. They have no effect on your actual camera feed or what gets transmitted anywhere else."},
    {"question": "What's the ideal amount of headroom?", "answer": "A small, even gap above your head — enough that the top of your head isn't touching the frame edge, but not so much that your face gets pushed down toward the centre or below it. The highlighted headroom band gives you a reasonable target."},
    {"question": "Why isn't the grid aligned with my video on first load?", "answer": "The overlay needs to know your camera's actual resolution to compute where the visible video content sits, which is only known once the stream starts. It redraws correctly the moment your camera goes live, and again automatically if you resize the window."},
    {"question": "Can I use this while on an actual video call?", "answer": "You'd need this open in a separate tab or window from your call software, since only one app can use the camera at a time. Use it beforehand to find a good position, then switch to your call — most desks and chairs don't move much between the two."},
]

TOOL = {
    "slug": "webcam-rule-of-thirds-composition-grid",
    "meta_title": "Webcam Composition Grid — Rule of Thirds Framing Guide | WebcamTest",
    "meta_description": "Overlay rule-of-thirds, centre lines, eye level, headroom and safe-area guides on your live webcam feed to frame yourself correctly for calls and recordings.",
    "h1": "Composition Grid",
    "subtitle": "Framing guides overlaid on your live camera feed — rule of thirds, centre lines, eye level, headroom and safe area.",
    "card": {
        "layout": "raw",
        "fields_html": FIELDS_HTML,
    },
    "script": SCRIPT,
    "content_html": CONTENT_HTML,
    "faq": FAQ,
}

if __name__ == "__main__":
    out_path = os.path.join(CONTENT_DIR, "webcam-rule-of-thirds-composition-grid.json")
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(TOOL, f, indent=2, ensure_ascii=False)
    print("Wrote", out_path)
