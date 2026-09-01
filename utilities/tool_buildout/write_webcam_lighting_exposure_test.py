#!/usr/bin/env python3
"""Writes src/content/webcam-lighting-exposure-test.json."""
import json
import os

BASE = os.path.dirname(os.path.abspath(__file__))
CONTENT_DIR = os.path.normpath(os.path.join(BASE, "..", "..", "src", "content"))

CAMERA_ICON = '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M23 7l-7 5 7 5V7z"/><rect x="1" y="5" width="15" height="14" rx="2" ry="2"/></svg>'
SUN_ICON = '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="5"/><path d="M12 1v2M12 21v2M4.22 4.22l1.42 1.42M18.36 18.36l1.42 1.42M1 12h2M21 12h2M4.22 19.78l1.42-1.42M18.36 5.64l1.42-1.42" stroke-linecap="round"/></svg>'
ADVICE_ICON = '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M12 18h.01M12 6a4 4 0 0 0-4 4c0 1.5 1 2 1.5 3s.5 1.5.5 2" stroke-linecap="round"/></svg>'
DOT_ICON = '<svg viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="9"/></svg>'
PLACEHOLDER_ICON = '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5"><path d="M23 7l-7 5 7 5V7z"/><rect x="1" y="5" width="15" height="14" rx="2" ry="2"/></svg>'

FIELDS_HTML = f'''<div class="tool-panel primary">
  <div class="panel-header">
    <span class="panel-icon">{CAMERA_ICON}</span>
    <div><h2>Lighting &amp; Exposure Test</h2><p class="panel-sub">Sit where you normally would for a call and let the reading settle for a couple of seconds</p></div>
  </div>
  <div class="media-preview" id="cameraPreviewWrap">
    <video id="cameraVideo" autoplay playsinline muted></video>
    <div class="media-preview-placeholder" id="cameraPlaceholder">
      {PLACEHOLDER_ICON}
      <span>Your camera feed will appear here</span>
    </div>
  </div>
  <canvas id="analysisCanvas" style="display:none"></canvas>
  <canvas id="histogramCanvas" style="width:100%;height:70px;margin-top:1rem;border-radius:var(--radius-sm);border:1px solid var(--border);background:var(--bg-alt)"></canvas>
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
    <span class="panel-icon">{SUN_ICON}</span>
    <div><h2>Exposure Reading</h2><p class="panel-sub">Updates a few times a second</p></div>
  </div>
  <div class="stat-grid">
    <div class="stat-tile highlight"><span class="stat-value" id="statCondition">—</span><span class="stat-label">Condition</span></div>
    <div class="stat-tile"><span class="stat-value" id="statOverall">—</span><span class="stat-label">Overall Brightness</span></div>
    <div class="stat-tile"><span class="stat-value" id="statCentre">—</span><span class="stat-label">Centre Brightness</span></div>
    <div class="stat-tile"><span class="stat-value" id="statEdge">—</span><span class="stat-label">Edge Brightness</span></div>
  </div>
  <p class="field-note">Cameras auto-adjust exposure continuously, so readings take a second or two to settle after you move or the lighting changes.</p>
</div>
<div class="tool-panel">
  <div class="panel-header">
    <span class="panel-icon">{ADVICE_ICON}</span>
    <div><h2>What To Do</h2><p class="panel-sub">Advice specific to what the camera is currently seeing</p></div>
  </div>
  <div class="diagnostic-panel" id="advicePanel">
    <div class="diagnostic-item"><span class="diag-icon">{DOT_ICON}</span><span>Start the camera to get advice tailored to your current lighting.</span></div>
  </div>
</div>'''

SCRIPT = r'''(function () {
  'use strict';

  var video = document.getElementById('cameraVideo');
  var previewWrap = document.getElementById('cameraPreviewWrap');
  var placeholder = document.getElementById('cameraPlaceholder');
  var canvas = document.getElementById('analysisCanvas');
  var histogramCanvas = document.getElementById('histogramCanvas');
  var deviceSelect = document.getElementById('deviceSelect');
  var btnStart = document.getElementById('btnStartCamera');
  var btnStop = document.getElementById('btnStopCamera');
  var diagnosticPanel = document.getElementById('diagnosticPanel');
  var advicePanel = document.getElementById('advicePanel');
  var statCondition = document.getElementById('statCondition');
  var statOverall = document.getElementById('statOverall');
  var statCentre = document.getElementById('statCentre');
  var statEdge = document.getElementById('statEdge');

  var currentStream = null;
  var starting = false;
  var analysisTimer = null;
  var recentReadings = [];
  var startedAt = 0;

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

  function setAdvice(items) {
    advicePanel.innerHTML = items.map(function (it) {
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
    if (analysisTimer) { clearInterval(analysisTimer); analysisTimer = null; }
    if (currentStream) {
      currentStream.getTracks().forEach(function (t) { t.stop(); });
      currentStream = null;
    }
    video.srcObject = null;
    previewWrap.classList.remove('is-active');
    placeholder.style.display = 'flex';
    btnStop.disabled = true;
    recentReadings = [];
    statCondition.textContent = '—';
    statOverall.textContent = '—';
    statCentre.textContent = '—';
    statEdge.textContent = '—';
    var hctx = histogramCanvas.getContext('2d');
    hctx.clearRect(0, 0, histogramCanvas.width, histogramCanvas.height);
    setAdvice([{ sev: '', html: 'Start the camera to get advice tailored to your current lighting.' }]);
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

  function drawHistogram(bins) {
    var w = histogramCanvas.clientWidth || 300;
    var h = histogramCanvas.clientHeight || 70;
    histogramCanvas.width = w;
    histogramCanvas.height = h;
    var ctx = histogramCanvas.getContext('2d');
    ctx.clearRect(0, 0, w, h);
    var maxCount = Math.max.apply(null, bins);
    if (!maxCount) return;
    var barW = w / bins.length;
    for (var i = 0; i < bins.length; i++) {
      var barH = (bins[i] / maxCount) * (h - 4);
      ctx.fillStyle = '#7c5cff';
      ctx.fillRect(i * barW, h - barH, Math.max(1, barW - 1), barH);
    }
  }

  function classify(overall, centre, edge) {
    // Backlight signature: a bright surround with a comparatively dark
    // centre subject -- this comparison is what makes backlight detection
    // work at all, a raw histogram alone can't distinguish it from "dim room".
    var backlit = (edge - centre) > 18 && centre < 45;
    if (backlit) {
      return {
        key: 'backlit', label: 'Backlit', sev: 'warn',
        advice: [
          { sev: 'warn', html: '<strong>You look backlit.</strong> The background behind you is noticeably brighter than your face.' },
          { sev: '', html: 'Turn to face a window or light source instead of having it behind you, or add a light in front of you (even a lamp or a phone screen helps).' },
          { sev: '', html: 'If you can, dim or close blinds on the window that’s currently behind you.' },
        ],
      };
    }
    if (overall < 25) {
      return {
        key: 'underexposed', label: 'Underexposed', sev: 'warn',
        advice: [
          { sev: 'warn', html: '<strong>The frame is quite dark.</strong> Your camera is having to work hard, which usually adds visible noise.' },
          { sev: '', html: 'Add a light source in front of you — face a window, turn on a desk lamp, or increase your room lighting.' },
          { sev: '', html: 'Avoid sitting with your back to the only light source in the room.' },
        ],
      };
    }
    if (overall > 82) {
      return {
        key: 'overexposed', label: 'Overexposed', sev: 'warn',
        advice: [
          { sev: 'warn', html: '<strong>The frame is very bright</strong> — detail may be washed out.' },
          { sev: '', html: 'Move away from direct light hitting the camera lens, or reduce nearby light sources pointed straight at you.' },
          { sev: '', html: 'If a window is directly behind the camera, try angling the camera slightly away from it.' },
        ],
      };
    }
    return {
      key: 'good', label: 'Good Exposure', sev: 'ok',
      advice: [
        { sev: 'ok', html: '<strong>This looks like good, even lighting.</strong> No major exposure issues detected.' },
        { sev: '', html: 'This is a good baseline to remember for future calls — similar seating and lighting should look this good again.' },
      ],
    };
  }

  // Downsample heavily before sampling pixels -- 120px on the long edge is
  // plenty for a brightness/histogram estimate and keeps the throttled
  // interval cheap.
  function measureExposure() {
    if (!currentStream || !video.videoWidth) return;
    var w = video.videoWidth, h = video.videoHeight;
    var scale = Math.min(1, 120 / Math.max(w, h));
    var sw = Math.max(8, Math.round(w * scale));
    var sh = Math.max(8, Math.round(h * scale));
    canvas.width = sw;
    canvas.height = sh;
    var ctx = canvas.getContext('2d');
    ctx.drawImage(video, 0, 0, sw, sh);

    var data;
    try {
      data = ctx.getImageData(0, 0, sw, sh).data;
    } catch (e) {
      return;
    }

    var bins = new Array(16).fill(0);
    var overallSum = 0, overallCount = 0;
    var centreSum = 0, centreCount = 0;
    var edgeSum = 0, edgeCount = 0;
    var cx0 = sw * 0.3, cx1 = sw * 0.7, cy0 = sh * 0.3, cy1 = sh * 0.7;

    for (var y = 0; y < sh; y++) {
      for (var x = 0; x < sw; x++) {
        var idx = (y * sw + x) * 4;
        var lum = (data[idx] * 0.299 + data[idx + 1] * 0.587 + data[idx + 2] * 0.114) / 255;
        overallSum += lum; overallCount++;
        bins[Math.min(15, Math.floor(lum * 16))]++;
        var inCentre = x >= cx0 && x < cx1 && y >= cy0 && y < cy1;
        if (inCentre) { centreSum += lum; centreCount++; }
        else { edgeSum += lum; edgeCount++; }
      }
    }
    if (!overallCount) return;

    var overall = Math.round((overallSum / overallCount) * 100);
    var centre = centreCount ? Math.round((centreSum / centreCount) * 100) : overall;
    var edge = edgeCount ? Math.round((edgeSum / edgeCount) * 100) : overall;

    drawHistogram(bins);

    recentReadings.push({ overall: overall, centre: centre, edge: edge });
    if (recentReadings.length > 6) recentReadings.shift();

    statOverall.textContent = overall + '%';
    statCentre.textContent = centre + '%';
    statEdge.textContent = edge + '%';

    // Let readings settle for ~1.5s (a handful of samples) before showing a
    // classification -- cameras auto-adjust exposure continuously, so an
    // instant read right after starting is often still ramping.
    if (Date.now() - startedAt < 1500 || recentReadings.length < 4) {
      statCondition.textContent = 'Reading…';
      return;
    }

    var avgOverall = Math.round(recentReadings.reduce(function (s, r) { return s + r.overall; }, 0) / recentReadings.length);
    var avgCentre = Math.round(recentReadings.reduce(function (s, r) { return s + r.centre; }, 0) / recentReadings.length);
    var avgEdge = Math.round(recentReadings.reduce(function (s, r) { return s + r.edge; }, 0) / recentReadings.length);

    var result = classify(avgOverall, avgCentre, avgEdge);
    statCondition.textContent = result.label;
    setAdvice(result.advice);
  }

  function startStream(deviceId) {
    if (starting) return;
    starting = true;
    stopStream();
    startedAt = Date.now();
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
        startedAt = Date.now();
        setDiagnostic([{ sev: 'ok', html: '<strong>Camera is live.</strong> Sit where you normally would for a call and give it a couple of seconds to settle.' }]);
        analysisTimer = setInterval(measureExposure, 300);
        return navigator.mediaDevices.enumerateDevices().then(function (devices) {
          populateDeviceSelect(devices, settings.deviceId);
        });
      })
      .catch(function (err) { setDiagnostic([describeError(err)]); stopStream(); })
      .finally(function () { starting = false; btnStart.disabled = false; });
  }

  btnStart.addEventListener('click', function () { startStream(deviceSelect.value); });
  btnStop.addEventListener('click', function () {
    stopStream();
    setDiagnostic([{ sev: '', html: 'Camera stopped.' }]);
  });
  deviceSelect.addEventListener('change', function () { if (currentStream) startStream(deviceSelect.value); });

  window.addEventListener('pagehide', stopStream);
  document.addEventListener('visibilitychange', function () {
    if (document.visibilityState === 'hidden') stopStream();
  });

  if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) {
    setDiagnostic([{ sev: 'error', html: '<strong>Your browser doesn’t support camera access.</strong>' }]);
    btnStart.disabled = true;
  }
})();'''

CONTENT_HTML = '''<p>This tool analyses your camera's live feed for the single most common reason people look bad on video calls: lighting. It classifies what it sees as underexposed, overexposed, well-lit, or backlit, and gives advice specific to whichever condition it detects.</p>
<h2>How the reading works</h2>
<p>A few times a second, a frame is drawn to a small hidden canvas and sampled for brightness. Three numbers come out of that: overall brightness across the whole frame, the brightness of just the centre region (where a person's face usually sits), and the brightness of the outer edge region. The live bar chart above the controls is a histogram of how those sampled pixels are distributed from dark to bright.</p>
<h2>Why centre-versus-edge is what actually detects backlighting</h2>
<p>A raw overall-brightness number can't tell the difference between "the room is dim" and "there's a bright window behind you" — both can average out to a similar overall reading. Comparing the centre of the frame against its edges is what makes the distinction: when the edges are noticeably brighter than the centre, and the centre itself is on the darker side, that's the classic signature of backlighting — a bright background silhouetting a darker subject in front of it.</p>
<h2>Why the reading takes a second or two to settle</h2>
<p>Cameras continuously auto-adjust their own exposure in response to what's in frame, so a reading taken the instant you move or the lighting changes is often still catching up. This tool waits for a short settling period and averages several recent samples before showing a classification, rather than reacting to every single frame.</p>'''

FAQ = [
    {"question": "What does “backlit” mean and why is it bad?", "answer": "Backlit means there's more light behind you than in front of you, often from a window or a bright doorway. Cameras expose for the overall scene, which makes a bright background look correct while your face, lit from behind, turns dark and hard to make out."},
    {"question": "Why does my reading say “Reading…” for a couple of seconds after I start the camera?", "answer": "Cameras auto-adjust exposure continuously, so a reading taken the instant the stream starts is often still settling. This tool waits briefly and averages several samples before showing a classification, to avoid flickering between readings."},
    {"question": "Is my video sent anywhere for this analysis?", "answer": "No. Every frame is analysed in memory in your own browser using canvas pixel sampling, and nothing is ever uploaded or recorded."},
    {"question": "I fixed my lighting but the condition still says the same thing — why?", "answer": "Move or wait a couple of seconds after changing your lighting; the reading only updates using the last few samples, so it can lag slightly behind a lighting change until enough new samples come in."},
]

TOOL = {
    "slug": "webcam-lighting-exposure-test",
    "meta_title": "Webcam Lighting & Exposure Test — Fix Backlighting Online | WebcamTest",
    "meta_description": "Check your webcam lighting live in your browser. Detects underexposed, overexposed and backlit conditions from your camera feed and gives specific advice to fix each one.",
    "h1": "Lighting and Exposure Test",
    "subtitle": "Live brightness analysis that detects underexposure, overexposure and backlighting, with advice for each.",
    "card": {
        "layout": "raw",
        "fields_html": FIELDS_HTML,
    },
    "script": SCRIPT,
    "content_html": CONTENT_HTML,
    "faq": FAQ,
}

if __name__ == "__main__":
    out_path = os.path.join(CONTENT_DIR, "webcam-lighting-exposure-test.json")
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(TOOL, f, indent=2, ensure_ascii=False)
    print("Wrote", out_path)
