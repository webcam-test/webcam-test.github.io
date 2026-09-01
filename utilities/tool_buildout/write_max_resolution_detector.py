#!/usr/bin/env python3
"""Writes src/content/webcam-maximum-resolution-detector.json."""
import json
import os

BASE = os.path.dirname(os.path.abspath(__file__))
CONTENT_DIR = os.path.normpath(os.path.join(BASE, "..", "..", "src", "content"))

CAMERA_ICON = '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M23 7l-7 5 7 5V7z"/><rect x="1" y="5" width="15" height="14" rx="2" ry="2"/></svg>'
LADDER_ICON = '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M4 20V10M10 20V4M16 20v-7M22 20v-3" stroke-linecap="round"/></svg>'
DOT_ICON = '<svg viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="9"/></svg>'
PLACEHOLDER_ICON = '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5"><path d="M23 7l-7 5 7 5V7z"/><rect x="1" y="5" width="15" height="14" rx="2" ry="2"/></svg>'

FIELDS_HTML = f'''<div class="tool-panel primary">
  <div class="panel-header">
    <span class="panel-icon">{CAMERA_ICON}</span>
    <div><h2>Resolution Probe</h2><p class="panel-sub">Finds the highest resolution your browser can actually negotiate with this camera</p></div>
  </div>
  <div class="media-preview" id="cameraPreviewWrap">
    <video id="cameraVideo" autoplay playsinline muted></video>
    <div class="media-preview-placeholder" id="cameraPlaceholder">
      {PLACEHOLDER_ICON}
      <span>Your camera feed will appear here</span>
    </div>
  </div>
  <div class="media-controls">
    <button type="button" class="btn-primary" id="btnDetect">Detect Maximum Resolution</button>
    <button type="button" class="btn-secondary" id="btnStopCamera" disabled>Stop Camera</button>
    <select class="device-select" id="deviceSelect" aria-label="Select camera" disabled>
      <option value="">Default camera</option>
    </select>
  </div>
  <div class="probe-progress" id="probeProgressWrap" style="display:none;margin-top:1rem">
    <div class="probe-progress-fill" id="probeProgressFill"></div>
  </div>
  <div class="diagnostic-panel" id="diagnosticPanel" style="margin-top:1rem">
    <div class="diagnostic-item" id="diagDefault"><span class="diag-icon">{DOT_ICON}</span><span>Click <strong>Detect Maximum Resolution</strong> to begin. This briefly requests several resolutions in a row — your video may flicker while it works.</span></div>
  </div>
</div>
<div class="tool-panel">
  <div class="panel-header"><div><h2>Your Result</h2><p class="panel-sub">The highest resolution reached</p></div></div>
  <div class="stat-grid">
    <div class="stat-tile highlight"><span class="stat-value" id="statPeakResolution">—</span><span class="stat-label">Resolution</span></div>
    <div class="stat-tile"><span class="stat-value" id="statPeakMegapixels">—</span><span class="stat-label">Megapixels</span></div>
    <div class="stat-tile"><span class="stat-value" id="statPeakAspect">—</span><span class="stat-label">Aspect Ratio</span></div>
    <div class="stat-tile"><span class="stat-value" id="statPeakStandard" style="font-size:.85rem">—</span><span class="stat-label">Closest Standard</span></div>
  </div>
  <p class="field-note">This is the browser-reachable maximum, not necessarily your camera's true sensor resolution — see below.</p>
</div>
<div class="tool-panel span-3">
  <div class="panel-header">
    <span class="panel-icon">{LADDER_ICON}</span>
    <div><h2>Resolution Standards Ladder</h2><p class="panel-sub">Every standard video mode from 8K down to QQVGA, and whether your browser could reach it</p></div>
  </div>
  <div class="ladder-list" id="ladderList"></div>
</div>'''

SCRIPT = r'''(function () {
  'use strict';

  var video = document.getElementById('cameraVideo');
  var previewWrap = document.getElementById('cameraPreviewWrap');
  var placeholder = document.getElementById('cameraPlaceholder');
  var deviceSelect = document.getElementById('deviceSelect');
  var btnDetect = document.getElementById('btnDetect');
  var btnStop = document.getElementById('btnStopCamera');
  var diagnosticPanel = document.getElementById('diagnosticPanel');
  var progressWrap = document.getElementById('probeProgressWrap');
  var progressFill = document.getElementById('probeProgressFill');
  var ladderList = document.getElementById('ladderList');
  var statResolution = document.getElementById('statPeakResolution');
  var statMegapixels = document.getElementById('statPeakMegapixels');
  var statAspect = document.getElementById('statPeakAspect');
  var statStandard = document.getElementById('statPeakStandard');

  // Standard video resolutions, 8K down to QQVGA, sorted by pixel area
  // descending. Kept as the single source the ladder display and the probe
  // loop both read from, so they can never disagree with each other.
  var STANDARDS = [
    ['8K UHD', 7680, 4320], ['5K', 5120, 2880], ['DCI 4K', 4096, 2160], ['4K UHD', 3840, 2160],
    ['QHD+', 2560, 1600], ['QHD', 2560, 1440], ['Full HD+', 1920, 1200], ['Full HD', 1920, 1080],
    ['HD+', 1600, 900], ['HD', 1280, 720], ['XGA', 1024, 768], ['WSVGA', 1024, 600],
    ['SVGA', 800, 600], ['VGA', 640, 480], ['CIF', 352, 288], ['QVGA', 320, 240],
    ['QCIF', 176, 144], ['QQVGA', 160, 120],
  ].sort(function (a, b) { return (b[1] * b[2]) - (a[1] * a[2]); });

  var currentStream = null;
  var running = false;

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

  function gcd(a, b) { return b === 0 ? a : gcd(b, a % b); }

  function renderLadder(peakArea, activeName) {
    ladderList.innerHTML = STANDARDS.map(function (s) {
      var name = s[0], w = s[1], h = s[2];
      var area = w * h;
      var cls = 'ladder-item';
      if (peakArea !== null) {
        if (area <= peakArea) cls += ' supported';
        if (name === activeName) cls += ' best';
      }
      var status = peakArea === null ? '' : (area <= peakArea ? (name === activeName ? 'Best match' : 'Reachable') : 'Not reached');
      return '<div class="' + cls + '"><span class="ladder-name">' + escapeHtml(name) + '</span>' +
        '<span class="ladder-dims">' + w + '×' + h + '</span><span>' + status + '</span></div>';
    }).join('');
  }

  // Same stopStream() shape every camera tool on this site copies (see
  // webcam-test-online's own script and this project's CLAUDE.md).
  function stopStream() {
    if (currentStream) {
      currentStream.getTracks().forEach(function (t) { t.stop(); });
      currentStream = null;
    }
    video.srcObject = null;
    previewWrap.classList.remove('is-active');
    placeholder.style.display = 'flex';
    btnStop.disabled = true;
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
      case 'SecurityError':
        return { sev: 'error', html: '<strong>Camera access requires HTTPS.</strong>' };
      default:
        return { sev: 'error', html: '<strong>Something went wrong probing the camera.</strong> ' + escapeHtml((err && err.message) || 'Unknown error') + '.' };
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

  function requestResolution(deviceId, w, h) {
    var videoConstraint = { width: { ideal: w }, height: { ideal: h } };
    if (deviceId) videoConstraint.deviceId = { exact: deviceId };
    return navigator.mediaDevices.getUserMedia({ video: videoConstraint, audio: false });
  }

  function runProbe(deviceId) {
    if (running) return;
    running = true;
    btnDetect.disabled = true;
    progressWrap.style.display = 'block';
    progressFill.style.width = '0%';
    renderLadder(null, null);
    setDiagnostic([{ sev: '', html: 'Probing resolutions — this briefly restarts the camera several times…' }]);

    var i = 0;
    var found = null; // { area, width, height }

    function next() {
      if (i >= STANDARDS.length) return finish();
      var entry = STANDARDS[i];
      progressFill.style.width = Math.round((i / STANDARDS.length) * 100) + '%';

      // Fully release the previous probe stream before requesting the
      // next -- a still-active stream leaves the camera locked at the
      // earlier resolution on many browsers/drivers.
      if (currentStream) {
        currentStream.getTracks().forEach(function (t) { t.stop(); });
        currentStream = null;
      }

      requestResolution(deviceId, entry[1], entry[2])
        .then(function (stream) {
          currentStream = stream;
          video.srcObject = stream;
          placeholder.style.display = 'none';
          previewWrap.classList.add('is-active');
          var track = stream.getVideoTracks()[0];
          var settings = track.getSettings ? track.getSettings() : {};
          var actualW = settings.width || 0, actualH = settings.height || 0;
          var actualArea = actualW * actualH;
          var wantArea = entry[1] * entry[2];

          if (!found && actualArea >= wantArea * 0.95) {
            // First (largest) standard mode this browser could actually
            // reach -- "stop at the first match" per this tool's spec.
            // Use the browser's own reported dimensions (actual), which
            // may exceed the named standard slightly.
            found = { area: actualArea, width: actualW, height: actualH, name: entry[0] };
            btnStop.disabled = false;
            return finish();
          }
          i++;
          next();
        })
        .catch(function (err) {
          // OverconstrainedError at the very top of the ladder is
          // expected on most cameras (nobody has an 8K webcam) -- treat
          // it as "not reached" and keep descending rather than aborting
          // the whole probe.
          if (err && (err.name === 'OverconstrainedError' || err.name === 'ConstraintNotSatisfiedError')) {
            i++;
            next();
            return;
          }
          running = false;
          btnDetect.disabled = false;
          progressWrap.style.display = 'none';
          setDiagnostic([describeError(err)]);
        });
    }

    function finish() {
      running = false;
      btnDetect.disabled = false;
      progressFill.style.width = '100%';
      setTimeout(function () { progressWrap.style.display = 'none'; }, 400);

      if (!found) {
        setDiagnostic([{ sev: 'error', html: 'Could not negotiate any standard resolution with this camera.' }]);
        return;
      }

      var g = gcd(found.width, found.height) || 1;
      statResolution.textContent = found.width + '×' + found.height;
      statMegapixels.textContent = (found.width * found.height / 1e6).toFixed(2) + ' MP';
      statAspect.textContent = (found.width / g) + ':' + (found.height / g);
      statStandard.textContent = found.name;
      renderLadder(found.area, found.name);
      setDiagnostic([{ sev: 'ok', html: '<strong>' + found.width + '×' + found.height + '</strong> is the highest resolution your browser could negotiate with this camera. Your camera’s native sensor resolution — and what its own manufacturer app can reach — may be higher; browsers commonly cap out around 1080p or 4K regardless of the physical sensor.' }]);

      navigator.mediaDevices.enumerateDevices().then(function (devices) {
        var settings = currentStream ? currentStream.getVideoTracks()[0].getSettings() : {};
        populateDeviceSelect(devices, settings.deviceId);
      }).catch(function () {});
    }

    next();
  }

  btnDetect.addEventListener('click', function () { runProbe(deviceSelect.value); });
  btnStop.addEventListener('click', function () {
    stopStream();
    setDiagnostic([{ sev: '', html: 'Camera stopped.' }]);
  });
  deviceSelect.addEventListener('change', function () {
    // Switching devices mid-result just clears the stale result rather
    // than auto-re-probing, since the probe is an intentionally heavier
    // action (several getUserMedia calls in a row).
    stopStream();
    statResolution.textContent = statMegapixels.textContent = statAspect.textContent = statStandard.textContent = '—';
    renderLadder(null, null);
    setDiagnostic([{ sev: '', html: 'Click <strong>Detect Maximum Resolution</strong> to probe this camera.' }]);
  });

  window.addEventListener('pagehide', stopStream);
  document.addEventListener('visibilitychange', function () {
    if (document.visibilityState === 'hidden') stopStream();
  });

  renderLadder(null, null);

  if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) {
    setDiagnostic([{ sev: 'error', html: '<strong>Your browser doesn’t support camera access.</strong>' }]);
    btnDetect.disabled = true;
  }
})();'''

CONTENT_HTML = '''<p>Most webcam tools only report whatever resolution your camera happened to start at. The Maximum Resolution Detector does something different: it works down a ladder of standard video resolutions from 8K to QQVGA, requesting each one and reading back what your browser actually negotiated, to find the real ceiling — not just the default.</p>
<h2>How the probe works</h2>
<p>Starting from the largest standard resolution, this tool requests <code>getUserMedia</code> with that resolution set as an <em>ideal</em> constraint, then reads <code>getSettings()</code> on the resulting stream to see what was actually granted. <code>getSettings()</code> reports what was negotiated, not necessarily the camera's true maximum, so probing is the only reliable way to find it — a single request at a high "ideal" value will silently get clamped down to whatever the browser and driver decide is best, which is exactly the behavior this tool works around by testing multiple values and comparing results.</p>
<p>Each probe stops the previous stream before starting the next one — a still-active stream can leave a camera locked at its earlier resolution on some browsers and drivers, which would otherwise produce a false result.</p>
<h2>Why your result is probably lower than your camera's advertised specs</h2>
<p>The browser API this tool (and every other browser-based camera tool) relies on typically tops out around 1080p or 4K, even on cameras whose manufacturer app or native OS camera interface can reach far higher. This is a limitation of what browsers expose through <code>getUserMedia</code>, not a fault with your camera or this tool — if your result looks lower than what the box says, that's expected, not a bug.</p>
<h2>Reading the ladder</h2>
<p>The resolution standards ladder below the result shows every named video mode this tool tests against, from QQVGA (160×120) up to 8K UHD (7680×4320). Every mode at or below your detected maximum is marked reachable; your best match is highlighted. A dedicated resolution standards reference page (with more detail on what each mode is typically used for) is planned for a future update to this site.</p>'''

FAQ = [
    {"question": "Why does my camera flicker while this test runs?", "answer": "Each probe step briefly stops and restarts the camera at a different resolution, which is what causes the flicker. This is expected — the camera returns to normal as soon as the probe finishes."},
    {"question": "Why is my result lower than my webcam's advertised resolution?", "answer": "Browsers access cameras through a constrained API that typically caps out around 1080p or 4K, well below what many cameras can do through their own manufacturer software. This is a browser limitation, not something this tool — or any browser-based tool — can work around."},
    {"question": "What does \"Reachable\" versus \"Not reached\" mean in the ladder?", "answer": "Reachable means your browser could negotiate at least that many pixels with your camera during the probe. Not reached means the browser couldn't get that high, even though your camera was asked for it."},
    {"question": "Does this test try every single resolution on the ladder?", "answer": "No — it stops as soon as it finds the highest one your browser can reach, then infers that every smaller standard mode is also reachable, rather than re-testing all eighteen individually. This keeps the test quick and avoids restarting your camera more times than necessary."},
]

TOOL = {
    "slug": "webcam-maximum-resolution-detector",
    "meta_title": "Webcam Maximum Resolution Detector — Test Your Real Max | WebcamTest",
    "meta_description": "Find the highest resolution your browser can actually negotiate with your webcam. Probes every standard video mode from 8K down to QQVGA and shows the full ladder of what's reachable.",
    "h1": "Maximum Resolution Detector",
    "subtitle": "Find the highest resolution your browser can actually negotiate with your camera — not just whatever it started at.",
    "card": {
        "layout": "raw",
        "fields_html": FIELDS_HTML,
    },
    "script": SCRIPT,
    "content_html": CONTENT_HTML,
    "faq": FAQ,
}

if __name__ == "__main__":
    out_path = os.path.join(CONTENT_DIR, "webcam-maximum-resolution-detector.json")
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(TOOL, f, indent=2, ensure_ascii=False)
    print("Wrote", out_path)
