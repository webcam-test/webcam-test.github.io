#!/usr/bin/env python3
"""Writes src/content/webcam-photo-capture-online.json. Throwaway authoring
script, same pattern as write_webcam_test_online.py — see this project's
CLAUDE.md 'Authoring a new tool's content file'."""
import json
import os

BASE = os.path.dirname(os.path.abspath(__file__))
CONTENT_DIR = os.path.normpath(os.path.join(BASE, "..", "..", "src", "content"))

CAMERA_ICON = '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M23 7l-7 5 7 5V7z"/><rect x="1" y="5" width="15" height="14" rx="2" ry="2"/></svg>'
IMAGE_ICON = '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect x="3" y="3" width="18" height="18" rx="2" ry="2"/><circle cx="8.5" cy="8.5" r="1.5"/><path d="m21 15-5-5L5 21" stroke-linecap="round" stroke-linejoin="round"/></svg>'
WARN_ICON = '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M12 9v4M12 17h.01M10.29 3.86 1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z" stroke-linecap="round" stroke-linejoin="round"/></svg>'
DOT_ICON = '<svg viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="9"/></svg>'
PLACEHOLDER_ICON = '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5"><path d="M23 7l-7 5 7 5V7z"/><rect x="1" y="5" width="15" height="14" rx="2" ry="2"/></svg>'

FIELDS_HTML = f'''<div class="tool-panel primary">
  <div class="panel-header">
    <span class="panel-icon">{CAMERA_ICON}</span>
    <div><h2>Live Camera Preview</h2><p class="panel-sub">Grant camera access, then capture a still to download</p></div>
  </div>
  <div class="media-preview" id="cameraPreviewWrap">
    <video id="cameraVideo" autoplay playsinline muted></video>
    <div class="media-preview-placeholder" id="cameraPlaceholder">
      {PLACEHOLDER_ICON}
      <span>Your camera feed will appear here</span>
    </div>
    <div class="capture-countdown" id="captureCountdown"></div>
    <div class="capture-flash" id="captureFlash"></div>
  </div>
  <div class="media-controls">
    <button type="button" class="btn-primary" id="btnStartCamera">Start Camera</button>
    <button type="button" class="btn-secondary" id="btnStopCamera" disabled>Stop Camera</button>
    <button type="button" class="btn-secondary" id="btnMirrorToggle" aria-pressed="false" disabled>Mirror</button>
    <select class="device-select" id="deviceSelect" aria-label="Select camera" disabled>
      <option value="">Default camera</option>
    </select>
  </div>
  <div class="tool-actions">
    <button type="button" class="btn-primary" id="btnCapture" disabled>Capture Photo</button>
    <select class="device-select" id="selectCountdown" aria-label="Countdown timer" style="max-width:160px" disabled>
      <option value="0">No countdown</option>
      <option value="3">3 second countdown</option>
      <option value="5">5 second countdown</option>
    </select>
    <label style="display:flex;align-items:center;gap:.4rem;font-size:.85rem;color:var(--text-secondary)">
      <input type="checkbox" id="checkBurst" disabled> Burst (3 shots)
    </label>
  </div>
</div>
<div class="tool-panel">
  <div class="panel-header">
    <span class="panel-icon">{IMAGE_ICON}</span>
    <div><h2>Capture Report</h2><p class="panel-sub">PNG vs. JPEG size for your most recent shot</p></div>
  </div>
  <div class="stat-grid">
    <div class="stat-tile"><span class="stat-value" id="statResolution">—</span><span class="stat-label">Resolution</span></div>
    <div class="stat-tile"><span class="stat-value" id="statPngSize">—</span><span class="stat-label">PNG Size</span></div>
    <div class="stat-tile"><span class="stat-value" id="statJpegSize">—</span><span class="stat-label">JPEG Size</span></div>
    <div class="stat-tile"><span class="stat-value" id="statShotCount">0</span><span class="stat-label">Shots This Session</span></div>
  </div>
  <div class="capture-list" id="captureList">
    <p class="capture-empty" id="captureEmpty">Captured photos will appear here, newest first — nothing is uploaded.</p>
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
  var btnCapture = document.getElementById('btnCapture');
  var selectCountdown = document.getElementById('selectCountdown');
  var checkBurst = document.getElementById('checkBurst');
  var countdownEl = document.getElementById('captureCountdown');
  var flashEl = document.getElementById('captureFlash');
  var diagnosticPanel = document.getElementById('diagnosticPanel');
  var statResolution = document.getElementById('statResolution');
  var statPngSize = document.getElementById('statPngSize');
  var statJpegSize = document.getElementById('statJpegSize');
  var statShotCount = document.getElementById('statShotCount');
  var captureList = document.getElementById('captureList');
  var captureEmpty = document.getElementById('captureEmpty');

  var currentStream = null;
  var currentDeviceId = '';
  var starting = false;
  var capturing = false;
  var shotCount = 0;
  var captures = []; // {id, pngUrl, jpegUrl}
  var MAX_CAPTURES = 6;
  var canvas = document.createElement('canvas');
  var ctx = canvas.getContext('2d');

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

  function formatBytes(n) {
    if (n < 1024) return n + ' B';
    if (n < 1024 * 1024) return (n / 1024).toFixed(1) + ' KB';
    return (n / (1024 * 1024)).toFixed(2) + ' MB';
  }

  function revokeCapture(cap) {
    URL.revokeObjectURL(cap.pngUrl);
    URL.revokeObjectURL(cap.jpegUrl);
  }

  function renderCaptureList() {
    if (!captures.length) {
      captureList.innerHTML = '';
      captureList.appendChild(captureEmpty);
      return;
    }
    captureList.innerHTML = captures.map(function (cap) {
      return '<div class="capture-row"><span class="capture-row-meta">' + cap.width + '\\u00d7' + cap.height + ' \\u2014 ' + cap.time + '</span>' +
        '<span class="capture-row-actions"><a href="' + cap.pngUrl + '" download="webcam-photo-' + cap.id + '.png">Download PNG</a>' +
        '<a href="' + cap.jpegUrl + '" download="webcam-photo-' + cap.id + '.jpg">Download JPEG</a></span></div>';
    }).join('');
  }

  // Every camera page on this site copies this stopStream()/enumerate/error
  // pattern from webcam-test-online.json (see this project's own CLAUDE.md).
  // This tool additionally revokes every outstanding capture object URL on
  // teardown, so leaving the page never leaks blob memory.
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
    btnCapture.disabled = true;
    selectCountdown.disabled = true;
    checkBurst.disabled = true;
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
        btnCapture.disabled = false;
        selectCountdown.disabled = false;
        checkBurst.disabled = false;
        setDiagnostic([{ sev: 'ok', html: '<strong>Camera is live.</strong> Click <strong>Capture Photo</strong> to take a still.' }]);
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

  // Draws at video.videoWidth/videoHeight (the stream's real dimensions),
  // never the displayed element size, or a downscaled image gets captured
  // instead of the camera's native resolution -- per this tool's own spec.
  function grabFrame() {
    var w = video.videoWidth, h = video.videoHeight;
    if (!w || !h) return Promise.reject(new Error('Video has no dimensions yet'));
    canvas.width = w;
    canvas.height = h;
    ctx.drawImage(video, 0, 0, w, h);
    var toBlobP = function (type, quality) {
      return new Promise(function (resolve) {
        canvas.toBlob(function (blob) { resolve(blob); }, type, quality);
      });
    };
    return Promise.all([toBlobP('image/png'), toBlobP('image/jpeg', 0.92)]).then(function (blobs) {
      return { width: w, height: h, png: blobs[0], jpeg: blobs[1] };
    });
  }

  function flash() {
    flashEl.classList.add('flash');
    requestAnimationFrame(function () {
      flashEl.classList.remove('flash');
    });
  }

  function addCapture(result) {
    shotCount++;
    var now = new Date();
    var cap = {
      id: now.getTime(),
      time: now.toLocaleTimeString(),
      width: result.width,
      height: result.height,
      pngUrl: URL.createObjectURL(result.png),
      jpegUrl: URL.createObjectURL(result.jpeg),
    };
    captures.unshift(cap);
    while (captures.length > MAX_CAPTURES) {
      revokeCapture(captures.pop());
    }
    statResolution.textContent = result.width + '\\u00d7' + result.height;
    statPngSize.textContent = formatBytes(result.png.size);
    statJpegSize.textContent = formatBytes(result.jpeg.size);
    statShotCount.textContent = String(shotCount);
    renderCaptureList();
    flash();
  }

  function doCapture() {
    return grabFrame().then(addCapture).catch(function () {
      setDiagnostic([{ sev: 'error', html: '<strong>Could not capture a frame.</strong> Make sure the camera is live and try again.' }]);
    });
  }

  function runCountdown(seconds) {
    return new Promise(function (resolve) {
      if (!seconds) { resolve(); return; }
      var remaining = seconds;
      countdownEl.textContent = String(remaining);
      countdownEl.classList.add('show');
      var tick = setInterval(function () {
        remaining--;
        if (remaining <= 0) {
          clearInterval(tick);
          countdownEl.classList.remove('show');
          resolve();
          return;
        }
        countdownEl.textContent = String(remaining);
      }, 1000);
    });
  }

  function delay(ms) {
    return new Promise(function (resolve) { setTimeout(resolve, ms); });
  }

  function capturePhoto() {
    if (capturing || !currentStream) return;
    capturing = true;
    btnCapture.disabled = true;
    var seconds = parseInt(selectCountdown.value, 10) || 0;
    var burst = checkBurst.checked;

    runCountdown(seconds)
      .then(function () { return doCapture(); })
      .then(function () {
        if (!burst) return;
        return delay(700).then(doCapture).then(function () {
          return delay(700).then(doCapture);
        });
      })
      .finally(function () {
        capturing = false;
        btnCapture.disabled = !currentStream;
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
  btnCapture.addEventListener('click', capturePhoto);
  deviceSelect.addEventListener('change', function () {
    if (currentStream) startStream(deviceSelect.value);
  });

  // Guaranteed teardown: release the camera and every outstanding capture
  // URL the moment the visitor leaves this page, even if they never
  // clicked Stop.
  window.addEventListener('pagehide', function () {
    stopStream();
    captures.forEach(revokeCapture);
    captures = [];
  });
  document.addEventListener('visibilitychange', function () {
    if (document.visibilityState === 'hidden') stopStream();
  });

  if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) {
    setDiagnostic([{ sev: 'error', html: '<strong>Your browser doesn\\u2019t support camera access.</strong> Try the latest version of Chrome, Firefox, Edge, or Safari.' }]);
    btnStart.disabled = true;
  }
})();'''

CONTENT_HTML = '''<p>WebcamTest's photo capture tool takes a still image from your camera and offers it for download, in both PNG and JPEG, so you can see and compare the size difference between the two directly. It's also the mechanism the <a href="/webcam-camera-information-report">Camera Information Report</a> uses to fill in its own image-quality metrics — this page is that same capture step, exposed on its own.</p>
<h2>How the capture works</h2>
<p>Clicking <strong>Capture Photo</strong> draws the current video frame onto a canvas at your camera's real, native stream dimensions — never a scaled-down version of what you see on screen — then exports that canvas as both a PNG and a JPEG file using the browser's own <code>canvas.toBlob</code> API. Nothing is uploaded at any point: both files are generated and offered for download entirely inside your browser tab.</p>
<h2>Why PNG and JPEG both, and why the sizes differ</h2>
<p>PNG is lossless — every pixel is preserved exactly, which typically makes the file noticeably larger. JPEG uses lossy compression tuned for photographic images, usually producing a much smaller file with a difference that's rarely visible to the eye at normal viewing sizes. Seeing both sizes side by side, generated from the exact same captured frame, makes that trade-off concrete rather than theoretical.</p>
<h2>Countdown timer and burst mode</h2>
<p>Set a 3 or 5 second countdown before capturing if you need time to get in frame yourself. Turn on <strong>Burst</strong> to take three photos roughly a second apart from a single click — useful for catching a better expression or moment without repeatedly clicking Capture. Every shot from a burst appears in the list below, newest first, each with its own PNG and JPEG download links.</p>
<h2>What happens to captured photos</h2>
<p>Captured photos live only in this browser tab's memory as local object URLs — never sent anywhere. The list keeps your most recent six captures; older ones are dropped automatically (and their memory released) as new ones come in, and everything is released the moment you leave the page or click Stop Camera.</p>'''

FAQ = [
    {"question": "Is my captured photo uploaded anywhere?", "answer": "No. The photo is drawn to a canvas and exported to PNG/JPEG entirely inside your browser tab using JavaScript. It's never sent to WebcamTest's servers or any third party — the download links point to local, in-memory object URLs."},
    {"question": "Why is the PNG file so much bigger than the JPEG?", "answer": "PNG is a lossless format — it preserves every pixel exactly, which produces a larger file. JPEG uses lossy compression designed for photographic content, typically shrinking the file substantially with little visible difference. Both are generated from the identical captured frame, so the size gap you see is purely the compression trade-off."},
    {"question": "Why does my captured photo look lower resolution than expected?", "answer": "This tool captures at your camera's actual negotiated stream resolution, not an upscaled or idealized size. If you want to check the highest resolution your browser can reach with this camera first, try the Maximum Resolution Detector, then capture from there."},
    {"question": "What does burst mode actually do?", "answer": "One click on Capture Photo with Burst enabled takes three separate photos roughly 700 milliseconds apart, each added to the capture list with its own download links. It's meant for catching a better moment — a natural expression, a steadier hand — without clicking Capture three separate times."},
    {"question": "Why did only my older captures disappear?", "answer": "The capture list keeps your six most recent photos to avoid holding unlimited images in memory. Once you exceed that, the oldest capture is dropped and its memory released automatically — download anything you want to keep before it scrolls off the list."},
]

TOOL = {
    "slug": "webcam-photo-capture-online",
    "meta_title": "Webcam Photo Capture — Take & Download a Snapshot | WebcamTest",
    "meta_description": "Capture a photo from your webcam and download it as PNG or JPEG, with a live file-size comparison. Countdown timer and burst mode included. Nothing uploaded.",
    "h1": "Webcam Photo Capture",
    "subtitle": "Take a still photo from your camera and download it as PNG or JPEG — see the size difference for yourself.",
    "card": {
        "layout": "raw",
        "fields_html": FIELDS_HTML,
    },
    "script": SCRIPT,
    "content_html": CONTENT_HTML,
    "faq": FAQ,
}

if __name__ == "__main__":
    out_path = os.path.join(CONTENT_DIR, "webcam-photo-capture-online.json")
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(TOOL, f, indent=2, ensure_ascii=False)
    print("Wrote", out_path)
