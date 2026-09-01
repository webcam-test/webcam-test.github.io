#!/usr/bin/env python3
"""Writes src/content/phone-camera-resolution-checker.json. Throwaway
authoring script, same pattern as write_webcam_test_online.py — see this
project's CLAUDE.md 'Authoring a new tool's content file'. Combines
webcam-maximum-resolution-detector.json's descending-ladder probe (same
STANDARDS list, same requestResolution()/area-threshold-match logic) with
mobile-camera-test-online.json's multi-lens enumeration, run once per
enumerated camera rather than once for the default camera."""
import json
import os

BASE = os.path.dirname(os.path.abspath(__file__))
CONTENT_DIR = os.path.normpath(os.path.join(BASE, "..", "..", "src", "content"))

CAMERA_ICON = '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M23 7l-7 5 7 5V7z"/><rect x="1" y="5" width="15" height="14" rx="2" ry="2"/></svg>'
TABLE_ICON = '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M3 3h18v18H3z"/><path d="M3 9h18M3 15h18M9 3v18M15 3v18"/></svg>'
WARN_ICON = '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M12 9v4M12 17h.01M10.29 3.86 1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z" stroke-linecap="round" stroke-linejoin="round"/></svg>'
DOT_ICON = '<svg viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="9"/></svg>'
PLACEHOLDER_ICON = '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5"><path d="M23 7l-7 5 7 5V7z"/><rect x="1" y="5" width="15" height="14" rx="2" ry="2"/></svg>'

FIELDS_HTML = f'''<div class="tool-panel primary">
  <div class="panel-header">
    <span class="panel-icon">{CAMERA_ICON}</span>
    <div><h2>Lens Probe</h2><p class="panel-sub">Finds the highest resolution each of your cameras can reach, one at a time</p></div>
  </div>
  <div class="media-preview" id="cameraPreviewWrap">
    <video id="cameraVideo" autoplay playsinline muted></video>
    <div class="media-preview-placeholder" id="cameraPlaceholder">
      {PLACEHOLDER_ICON}
      <span>Each camera's preview appears here while it's being probed</span>
    </div>
  </div>
  <div class="probe-progress" id="progressWrap" style="display:none;margin-top:1rem">
    <div class="probe-progress-fill" id="progressFill"></div>
  </div>
  <div class="media-controls">
    <button type="button" class="btn-primary" id="btnProbeAll">Probe All Cameras</button>
  </div>
</div>
<div class="tool-panel">
  <div class="panel-header">
    <span class="panel-icon">{TABLE_ICON}</span>
    <div><h2>Lens Comparison</h2><p class="panel-sub">Every camera probed this session, largest reachable resolution first</p></div>
  </div>
  <div class="capture-list" id="lensList">
    <p class="capture-empty" id="lensEmpty">Click Probe All Cameras to begin — on iPhone this checks about 2 lenses; on Android it may be several, and can take a little while.</p>
  </div>
</div>
<div class="tool-panel">
  <div class="panel-header">
    <span class="panel-icon">{WARN_ICON}</span>
    <div><h2>Status</h2><p class="panel-sub">What to do if probing won't start</p></div>
  </div>
  <div class="diagnostic-panel" id="diagnosticPanel">
    <div class="diagnostic-item"><span class="diag-icon">{DOT_ICON}</span><span>Click <strong>Probe All Cameras</strong> and allow access when your browser asks.</span></div>
  </div>
</div>'''

SCRIPT = '''(function () {
  'use strict';

  var video = document.getElementById('cameraVideo');
  var previewWrap = document.getElementById('cameraPreviewWrap');
  var placeholder = document.getElementById('cameraPlaceholder');
  var btnProbeAll = document.getElementById('btnProbeAll');
  var progressWrap = document.getElementById('progressWrap');
  var progressFill = document.getElementById('progressFill');
  var diagnosticPanel = document.getElementById('diagnosticPanel');
  var lensList = document.getElementById('lensList');
  var lensEmpty = document.getElementById('lensEmpty');

  var currentStream = null;
  var running = false;

  // Same 18-entry ladder, in the same descending-area order, as
  // webcam-maximum-resolution-detector.json -- kept identical so results
  // from the two tools are directly comparable.
  var STANDARDS = [
    ['8K UHD', 7680, 4320], ['5K', 5120, 2880], ['DCI 4K', 4096, 2160], ['4K UHD', 3840, 2160],
    ['QHD+', 2560, 1600], ['QHD', 2560, 1440], ['Full HD+', 1920, 1200], ['Full HD', 1920, 1080],
    ['HD+', 1600, 900], ['HD', 1280, 720], ['XGA', 1024, 768], ['WSVGA', 1024, 600],
    ['SVGA', 800, 600], ['VGA', 640, 480], ['CIF', 352, 288], ['QVGA', 320, 240],
    ['QCIF', 176, 144], ['QQVGA', 160, 120],
  ].sort(function (a, b) { return (b[1] * b[2]) - (a[1] * a[2]); });

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

  function describeError(err) {
    switch (err && err.name) {
      case 'NotAllowedError':
      case 'PermissionDeniedError':
        return { sev: 'error', html: '<strong>Camera access was blocked.</strong> Click the camera icon in your address bar (or your browser\\u2019s site settings) and allow access, then try again.' };
      case 'NotFoundError':
      case 'DevicesNotFoundError':
        return { sev: 'error', html: '<strong>No camera was detected.</strong> Make sure a camera is connected, then reload this page.' };
      case 'NotReadableError':
      case 'TrackStartError':
        return { sev: 'error', html: '<strong>Your camera is already in use.</strong> Another app or browser tab is probably holding it \\u2014 close video-calling apps or other camera tabs and try again.' };
      case 'SecurityError':
        return { sev: 'error', html: '<strong>Camera access requires a secure connection.</strong> Make sure this page is loaded over HTTPS.' };
      default:
        return { sev: 'error', html: '<strong>Something went wrong.</strong> ' + escapeHtml((err && err.message) || 'Unknown error') + '.' };
    }
  }

  function releaseStream() {
    if (currentStream) {
      currentStream.getTracks().forEach(function (t) { t.stop(); });
      currentStream = null;
    }
    video.srcObject = null;
    previewWrap.classList.remove('is-active');
    placeholder.style.display = 'flex';
  }

  function requestResolution(deviceId, w, h) {
    var videoConstraint = { width: { ideal: w }, height: { ideal: h } };
    if (deviceId) videoConstraint.deviceId = { exact: deviceId };
    return navigator.mediaDevices.getUserMedia({ video: videoConstraint, audio: false });
  }

  function renderLensRow(label, result) {
    var row = document.createElement('div');
    row.className = 'capture-row';
    if (!result) {
      row.innerHTML = '<span class="capture-row-meta"><strong>' + escapeHtml(label) + '</strong> \\u2014 could not negotiate any standard resolution</span>';
    } else {
      var g = gcd(result.width, result.height) || 1;
      var mp = (result.width * result.height / 1e6).toFixed(2);
      row.innerHTML = '<span class="capture-row-meta"><strong>' + escapeHtml(label) + '</strong> \\u2014 ' +
        result.width + '\\u00d7' + result.height + ' (' + mp + ' MP, ' + (result.width / g) + ':' + (result.height / g) +
        ', closest standard ' + escapeHtml(result.name) + ')</span>';
    }
    lensList.appendChild(row);
  }

  // Probes one camera's descending resolution ladder, stopping at the
  // first (largest) standard it can actually reach -- identical logic to
  // webcam-maximum-resolution-detector.json's runProbe(), just scoped to a
  // single deviceId and returning the result instead of rendering it
  // directly, so the caller can probe every enumerated camera in turn.
  function probeOneLens(deviceId) {
    return new Promise(function (resolve) {
      var i = 0;
      function next() {
        if (i >= STANDARDS.length) { resolve(null); return; }
        var entry = STANDARDS[i];
        requestResolution(deviceId, entry[1], entry[2])
          .then(function (stream) {
            // Fully release the previous probe stream before requesting
            // the next -- a still-active stream leaves the camera locked
            // at the earlier resolution on many browsers/drivers.
            releaseStream();
            currentStream = stream;
            video.srcObject = stream;
            placeholder.style.display = 'none';
            previewWrap.classList.add('is-active');
            var track = stream.getVideoTracks()[0];
            var settings = track.getSettings ? track.getSettings() : {};
            var actualW = settings.width || 0, actualH = settings.height || 0;
            var actualArea = actualW * actualH;
            var wantArea = entry[1] * entry[2];
            if (actualArea >= wantArea * 0.95) {
              resolve({ area: actualArea, width: actualW, height: actualH, name: entry[0] });
              return;
            }
            i++;
            next();
          })
          .catch(function () {
            i++;
            next();
          });
      }
      next();
    });
  }

  function probeAllCameras() {
    if (running) return;
    running = true;
    btnProbeAll.disabled = true;
    lensList.innerHTML = '';
    progressWrap.style.display = 'block';
    progressFill.style.width = '0%';
    setDiagnostic([{ sev: '', html: 'Requesting camera access\\u2026' }]);

    // enumerateDevices() only returns real labels once permission has been
    // granted at least once -- this throwaway getUserMedia call exists
    // purely to unlock labels, then is released immediately.
    navigator.mediaDevices.getUserMedia({ video: true, audio: false })
      .then(function (stream) {
        stream.getTracks().forEach(function (t) { t.stop(); });
        return navigator.mediaDevices.enumerateDevices();
      })
      .then(function (devices) {
        var cams = devices.filter(function (d) { return d.kind === 'videoinput'; });
        if (!cams.length) {
          setDiagnostic([{ sev: 'error', html: '<strong>No cameras were found.</strong>' }]);
          return Promise.resolve();
        }
        setDiagnostic([{ sev: '', html: 'Probing ' + cams.length + ' camera(s) \\u2014 this briefly restarts each one several times\\u2026' }]);
        var results = [];
        var chain = Promise.resolve();
        cams.forEach(function (d, idx) {
          chain = chain.then(function () {
            progressFill.style.width = Math.round((idx / cams.length) * 100) + '%';
            var label = d.label || ('Camera ' + (idx + 1));
            return probeOneLens(d.deviceId).then(function (result) {
              renderLensRow(label, result);
              results.push(result);
            });
          });
        });
        return chain.then(function () {
          progressFill.style.width = '100%';
          var found = results.filter(Boolean).length;
          setDiagnostic([{ sev: 'ok', html: '<strong>Done.</strong> Probed ' + cams.length + ' camera(s), got a result for ' + found + '.' }]);
        });
      })
      .catch(function (err) {
        setDiagnostic([describeError(err)]);
      })
      .finally(function () {
        releaseStream();
        running = false;
        btnProbeAll.disabled = false;
        setTimeout(function () { progressWrap.style.display = 'none'; }, 400);
        if (!lensList.children.length) lensList.appendChild(lensEmpty);
      });
  }

  btnProbeAll.addEventListener('click', probeAllCameras);

  // Guaranteed teardown: release whichever camera is mid-probe the moment
  // the visitor leaves this page.
  window.addEventListener('pagehide', releaseStream);
  document.addEventListener('visibilitychange', function () {
    if (document.visibilityState === 'hidden') releaseStream();
  });

  if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) {
    setDiagnostic([{ sev: 'error', html: '<strong>Your browser doesn\\u2019t support camera access.</strong> Try the latest version of Chrome, Firefox, Edge, or Safari.' }]);
    btnProbeAll.disabled = true;
  }
})();'''

CONTENT_HTML = '''<p>WebcamTest's phone camera resolution checker probes every camera your browser can see — not just the default one — and reports the highest standard resolution each can actually reach. It's the mobile counterpart to the desktop-focused <a href="/webcam-maximum-resolution-detector">Maximum Resolution Detector</a>, run once per lens instead of once for a single camera.</p>
<h2>How the probe works</h2>
<p>Clicking <strong>Probe All Cameras</strong> first lists every camera your browser can access, then runs the same descending-resolution-ladder check against each one in turn: starting from 8K and working down through 18 standard video modes, requesting each resolution and checking what the browser actually delivered, stopping the moment a lens successfully reaches one. Each camera's stream is fully released before the next probe begins — running two probes against the same camera at once is what causes cameras to lock at the wrong resolution on many browsers and drivers.</p>
<h2>Why this takes a little while</h2>
<p>Each lens can be probed several times before it turns up a match, and every probe briefly restarts that camera. On an iPhone, which typically exposes only its front and rear camera as two distinct entries, this finishes quickly. On Android phones with three or four rear lenses (main, ultra-wide, telephoto, macro), it can take noticeably longer — the progress bar reflects which lens is currently being checked, not each individual probe within that lens, so it's normal for it to pause for a moment on a single lens.</p>
<h2>Reading the comparison list</h2>
<p>Each row shows one camera's label (whatever your browser and OS report — not always a friendly name), its highest reachable resolution, megapixel count, aspect ratio, and the closest named video standard. As with every other resolution tool on this site, these numbers reflect what the <strong>browser</strong> can reach, not your phone's advertised sensor megapixel count — see the <a href="/rear-camera-test-online">Rear Camera Test</a> for a full explanation of why those two numbers are so different.</p>
<h2>Some lenses can't be reached at all</h2>
<p>Not every camera a phone has is necessarily reachable through the standard web camera API — some ultra-wide or macro lenses on certain Android devices simply don't appear as a separate, selectable camera to browsers. If your phone has more physical lenses than this page lists, that's a browser/OS limitation, not a bug in this page.</p>'''

FAQ = [
    {"question": "Why does this take longer than the regular Maximum Resolution Detector?", "answer": "This page repeats that same probe once per camera your browser can see, rather than once for a single default camera. A phone with several rear lenses (main, ultra-wide, telephoto) takes proportionally longer since each one is probed in full before moving to the next."},
    {"question": "Why don't all my phone's lenses show up?", "answer": "Not every physical camera a phone has is necessarily exposed as a separate, selectable device through the standard web camera API. Some ultra-wide or macro lenses on certain Android devices aren't independently reachable by browsers at all — this is a platform limitation, not something this page can work around."},
    {"question": "Is any of this uploaded anywhere?", "answer": "No. Every probe happens entirely inside your browser tab using JavaScript. Nothing about your camera feed or the results is ever sent to WebcamTest's servers or any third party."},
    {"question": "Why does one of my cameras show \"could not negotiate any standard resolution\"?", "answer": "This means that specific camera didn't successfully reach any of the 18 standard resolutions this page checks, which can happen with some low-quality or unusual lenses. Try the plain Webcam Test on that same camera to see what resolution it reports under normal, non-probing conditions."},
]

TOOL = {
    "slug": "phone-camera-resolution-checker",
    "meta_title": "Phone Camera Resolution Checker — Compare All Your Lenses | WebcamTest",
    "meta_description": "Find the highest resolution each of your phone's cameras can reach in the browser, compared side by side. Free, works on iPhone and Android, nothing uploaded.",
    "h1": "Phone Camera Resolution Checker",
    "subtitle": "Probe every camera your phone has and compare the highest resolution each one can actually reach.",
    "card": {
        "layout": "raw",
        "fields_html": FIELDS_HTML,
    },
    "script": SCRIPT,
    "content_html": CONTENT_HTML,
    "faq": FAQ,
}

if __name__ == "__main__":
    out_path = os.path.join(CONTENT_DIR, "phone-camera-resolution-checker.json")
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(TOOL, f, indent=2, ensure_ascii=False)
    print("Wrote", out_path)
