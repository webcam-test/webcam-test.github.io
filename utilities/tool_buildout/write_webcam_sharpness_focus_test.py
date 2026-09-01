#!/usr/bin/env python3
"""Writes src/content/webcam-sharpness-focus-test.json."""
import json
import os

BASE = os.path.dirname(os.path.abspath(__file__))
CONTENT_DIR = os.path.normpath(os.path.join(BASE, "..", "..", "src", "content"))

CAMERA_ICON = '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M23 7l-7 5 7 5V7z"/><rect x="1" y="5" width="15" height="14" rx="2" ry="2"/></svg>'
GAUGE_ICON = '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M12 20a8 8 0 1 0-8-8" stroke-linecap="round"/><path d="M12 12l4-4" stroke-linecap="round"/><path d="M2 12h2M12 2v2M20 12h2"/></svg>'
CHART_ICON = '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="9"/><circle cx="12" cy="12" r="4"/><path d="M12 3v3M12 18v3M3 12h3M18 12h3"/></svg>'
DOT_ICON = '<svg viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="9"/></svg>'
PLACEHOLDER_ICON = '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5"><path d="M23 7l-7 5 7 5V7z"/><rect x="1" y="5" width="15" height="14" rx="2" ry="2"/></svg>'
DOWNLOAD_ICON = '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4M7 10l5 5 5-5M12 15V3" stroke-linecap="round" stroke-linejoin="round"/></svg>'

FIELDS_HTML = f'''<div class="tool-panel primary">
  <div class="panel-header">
    <span class="panel-icon">{CAMERA_ICON}</span>
    <div><h2>Sharpness &amp; Focus Test</h2><p class="panel-sub">Point the camera at something with fine detail — text, a patterned fabric, a bookshelf — and adjust focus while watching the meter</p></div>
  </div>
  <div class="media-preview" id="cameraPreviewWrap">
    <video id="cameraVideo" autoplay playsinline muted></video>
    <div class="media-preview-placeholder" id="cameraPlaceholder">
      {PLACEHOLDER_ICON}
      <span>Your camera feed will appear here</span>
    </div>
  </div>
  <canvas id="analysisCanvas" style="display:none"></canvas>
  <div style="margin-top:1rem">
    <div class="level-meter-label"><span>Sharpness</span><strong id="sharpnessLabel">—</strong></div>
    <div class="level-meter"><div class="level-meter-fill" id="sharpnessFill"></div></div>
    <div class="level-meter-scale"><span>Blurry</span><span>Soft</span><span>Sharp</span><span>Very Sharp</span></div>
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
    <span class="panel-icon">{GAUGE_ICON}</span>
    <div><h2>Live Reading</h2><p class="panel-sub">Updates a few times a second</p></div>
  </div>
  <div class="stat-grid">
    <div class="stat-tile"><span class="stat-value" id="statScore">—</span><span class="stat-label">Score (0–100)</span></div>
    <div class="stat-tile highlight"><span class="stat-value" id="statBest">—</span><span class="stat-label">Best This Session</span></div>
  </div>
  <p class="field-note">The score is relative, not absolute — a blank wall scores low regardless of focus. Point the camera at something with visible detail and watch the score respond as you adjust focus; the response is the real test, not the raw number.</p>
</div>
<div class="tool-panel">
  <div class="panel-header">
    <span class="panel-icon">{CHART_ICON}</span>
    <div><h2>Printable Focus Chart</h2><p class="panel-sub">A generated test chart for manual focus verification</p></div>
  </div>
  <canvas id="chartCanvas" style="display:none"></canvas>
  <div class="media-preview" id="chartPreviewWrap" style="aspect-ratio:3/4;margin-bottom:1rem">
    <img id="chartPreviewImg" alt="Focus test chart preview" style="width:100%;height:100%;object-fit:contain;background:#fff;border-radius:var(--radius-sm)" />
  </div>
  <button type="button" class="btn-secondary btn-icon-text" id="btnDownloadChart">{DOWNLOAD_ICON} Download Focus Chart (PNG)</button>
  <p class="field-note">Print it or display it on a second screen, then check whether the fine spokes near the centre stay distinct at your camera's normal working distance.</p>
</div>'''

SCRIPT = r'''(function () {
  'use strict';

  var video = document.getElementById('cameraVideo');
  var previewWrap = document.getElementById('cameraPreviewWrap');
  var placeholder = document.getElementById('cameraPlaceholder');
  var canvas = document.getElementById('analysisCanvas');
  var deviceSelect = document.getElementById('deviceSelect');
  var btnStart = document.getElementById('btnStartCamera');
  var btnStop = document.getElementById('btnStopCamera');
  var diagnosticPanel = document.getElementById('diagnosticPanel');
  var sharpnessFill = document.getElementById('sharpnessFill');
  var sharpnessLabel = document.getElementById('sharpnessLabel');
  var statScore = document.getElementById('statScore');
  var statBest = document.getElementById('statBest');
  var chartCanvas = document.getElementById('chartCanvas');
  var chartPreviewImg = document.getElementById('chartPreviewImg');
  var btnDownloadChart = document.getElementById('btnDownloadChart');

  var currentStream = null;
  var starting = false;
  var analysisTimer = null;
  var bestScore = 0;

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
    if (analysisTimer) { clearInterval(analysisTimer); analysisTimer = null; }
    if (currentStream) {
      currentStream.getTracks().forEach(function (t) { t.stop(); });
      currentStream = null;
    }
    video.srcObject = null;
    previewWrap.classList.remove('is-active');
    placeholder.style.display = 'flex';
    btnStop.disabled = true;
    sharpnessFill.style.width = '0%';
    sharpnessLabel.textContent = '—';
    statScore.textContent = '—';
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

  function classify(score) {
    if (score < 15) return 'Very Blurry';
    if (score < 35) return 'Blurry';
    if (score < 55) return 'Soft';
    if (score < 78) return 'Sharp';
    return 'Very Sharp';
  }

  // Downsample heavily before the convolution or the loop won't keep up --
  // 140px on the long edge is plenty for a variance-of-Laplacian estimate.
  function measureSharpness() {
    if (!currentStream || !video.videoWidth) return;
    var w = video.videoWidth, h = video.videoHeight;
    var scale = Math.min(1, 140 / Math.max(w, h));
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

    var gray = new Float32Array(sw * sh);
    for (var i = 0, p = 0; i < data.length; i += 4, p++) {
      gray[p] = data[i] * 0.299 + data[i + 1] * 0.587 + data[i + 2] * 0.114;
    }

    var lapSum = 0, lapSumSq = 0, count = 0;
    for (var y = 1; y < sh - 1; y++) {
      for (var x = 1; x < sw - 1; x++) {
        var idx = y * sw + x;
        var lap = 4 * gray[idx] - gray[idx - 1] - gray[idx + 1] - gray[idx - sw] - gray[idx + sw];
        lapSum += lap;
        lapSumSq += lap * lap;
        count++;
      }
    }
    if (!count) return;
    var mean = lapSum / count;
    var variance = (lapSumSq / count) - (mean * mean);

    // Raw variance-of-Laplacian has no fixed ceiling -- scale and clamp to a
    // 0-100 display range. This scaling factor is empirical, not a
    // calibrated absolute unit; the live response to focus changes is what
    // matters, not the specific number (see this tool's own field-note).
    var score = Math.max(0, Math.min(100, Math.round(variance / 70)));

    sharpnessFill.style.width = score + '%';
    sharpnessLabel.textContent = score + ' — ' + classify(score);
    statScore.textContent = String(score);
    if (score > bestScore) {
      bestScore = score;
      statBest.textContent = String(bestScore);
    }
  }

  function startStream(deviceId) {
    if (starting) return;
    starting = true;
    stopStream();
    bestScore = 0;
    statBest.textContent = '—';
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
        setDiagnostic([{ sev: 'ok', html: '<strong>Camera is live.</strong> Point it at something with fine detail and adjust focus while watching the meter.' }]);
        analysisTimer = setInterval(measureSharpness, 250);
        return navigator.mediaDevices.enumerateDevices().then(function (devices) {
          populateDeviceSelect(devices, settings.deviceId);
        });
      })
      .catch(function (err) { setDiagnostic([describeError(err)]); stopStream(); })
      .finally(function () { starting = false; btnStart.disabled = false; });
  }

  // Draws a Siemens-star focus chart (alternating black/white wedges radiating
  // from the centre) plus concentric rings -- the industry-standard pattern
  // for manual focus verification, since blur shows up first as the fine
  // spokes near the centre merging into grey.
  function drawFocusChart() {
    var size = 1200;
    chartCanvas.width = size;
    chartCanvas.height = size;
    var ctx = chartCanvas.getContext('2d');
    ctx.fillStyle = '#ffffff';
    ctx.fillRect(0, 0, size, size);

    var cx = size / 2, cy = size / 2;
    var outerR = size * 0.46;
    var wedges = 36;
    for (var i = 0; i < wedges; i++) {
      ctx.beginPath();
      ctx.moveTo(cx, cy);
      var a0 = (i / wedges) * Math.PI * 2;
      var a1 = ((i + 1) / wedges) * Math.PI * 2;
      ctx.arc(cx, cy, outerR, a0, a1);
      ctx.closePath();
      ctx.fillStyle = (i % 2 === 0) ? '#000000' : '#ffffff';
      ctx.fill();
    }

    ctx.strokeStyle = '#000000';
    ctx.lineWidth = 3;
    [0.15, 0.28, 0.46].forEach(function (r) {
      ctx.beginPath();
      ctx.arc(cx, cy, size * r, 0, Math.PI * 2);
      ctx.stroke();
    });

    ctx.fillStyle = '#000000';
    ctx.font = 'bold 28px sans-serif';
    ctx.textAlign = 'center';
    ctx.fillText('WebcamTest Focus Chart', cx, size * 0.96);
    ctx.font = '18px sans-serif';
    ctx.fillText('Fine spokes near the centre should stay distinct when in focus', cx, size * 0.06);

    chartPreviewImg.src = chartCanvas.toDataURL('image/png');
  }

  btnStart.addEventListener('click', function () { startStream(deviceSelect.value); });
  btnStop.addEventListener('click', function () {
    stopStream();
    setDiagnostic([{ sev: '', html: 'Camera stopped.' }]);
  });
  deviceSelect.addEventListener('change', function () { if (currentStream) startStream(deviceSelect.value); });

  btnDownloadChart.addEventListener('click', function () {
    var url = chartCanvas.toDataURL('image/png');
    var a = document.createElement('a');
    a.href = url;
    a.download = 'webcamtest-focus-chart.png';
    document.body.appendChild(a);
    a.click();
    a.remove();
  });

  window.addEventListener('pagehide', stopStream);
  document.addEventListener('visibilitychange', function () {
    if (document.visibilityState === 'hidden') stopStream();
  });

  drawFocusChart();

  if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) {
    setDiagnostic([{ sev: 'error', html: '<strong>Your browser doesn’t support camera access.</strong>' }]);
    btnStart.disabled = true;
  }
})();'''

CONTENT_HTML = '''<p>This tool measures how sharply your camera is focused by analysing edge contrast in the live video feed, and gives you a printable focus chart for a manual sanity check alongside the live number.</p>
<h2>How the sharpness score works</h2>
<p>Every quarter-second, a frame from your camera is drawn to a small hidden canvas, converted to greyscale, and passed through an edge-detection kernel (a Laplacian filter). A sharply focused image has strong, well-defined edges, which produces a high-variance result; a blurry image has soft transitions between pixels, which produces a low-variance result. That variance is scaled to a 0-100 meter for readability.</p>
<h2>Why the number alone doesn't mean much</h2>
<p>The score is a relative measurement, not a calibrated absolute unit — it depends heavily on what's actually in frame. A blank wall or a plain ceiling has almost no edges to detect and will always score low, regardless of how well-focused your camera actually is. Point the camera at something with real detail — printed text, a patterned fabric, a bookshelf — and watch the score rise and fall as you adjust focus. That live response is the actual test; the "Best This Session" tile records the highest score you've reached so far, which is a useful target to beat back down to after moving the camera.</p>
<h2>Using the printable focus chart</h2>
<p>The focus chart panel generates a Siemens star pattern — the same style of radiating alternating-wedge chart used in optics testing — plus a few concentric rings. Download it and either print it out or display it full-size on a second screen, then check your camera's live feed against it: the fine spokes near the centre are the first thing to blur when a camera is out of focus, so how close to the centre they stay sharp is a quick visual indicator of your camera's actual resolving power.</p>'''

FAQ = [
    {"question": "Why does my score go up when I point at a bookshelf but drop near a blank wall?", "answer": "The sharpness score measures edge contrast, not focus in isolation. A blank wall has almost no edges to detect, so it scores low no matter how well-focused the camera is. Point the camera at something with real detail to get a meaningful reading."},
    {"question": "What counts as a good score?", "answer": "There's no universal good score, since it depends on scene content and camera. What matters is the relative change: turn or tap your camera's focus ring (if it has one) or nudge the lens area, and confirm the score responds — rising when focus improves, dropping when it doesn't."},
    {"question": "Is any video or image uploaded anywhere?", "answer": "No. Every frame is analysed in memory in your browser and immediately discarded. The only thing that ever leaves your device is the focus chart PNG, and only if you click the download button yourself."},
    {"question": "What is the printable focus chart for?", "answer": "It's a Siemens-star test pattern, a standard tool in optics for checking focus and resolving power. Print it or display it on another screen, point your camera at it, and see how close to the centre the alternating spokes stay distinct rather than blurring into grey."},
]

TOOL = {
    "slug": "webcam-sharpness-focus-test",
    "meta_title": "Webcam Sharpness & Focus Test — Check Camera Focus Online | WebcamTest",
    "meta_description": "Test your webcam's sharpness and focus live in your browser. See a real-time sharpness meter as you adjust focus, plus a downloadable printable focus chart.",
    "h1": "Sharpness and Focus Test",
    "subtitle": "A live sharpness meter that responds as you adjust focus, plus a printable focus chart for a manual check.",
    "card": {
        "layout": "raw",
        "fields_html": FIELDS_HTML,
    },
    "script": SCRIPT,
    "content_html": CONTENT_HTML,
    "faq": FAQ,
}

if __name__ == "__main__":
    out_path = os.path.join(CONTENT_DIR, "webcam-sharpness-focus-test.json")
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(TOOL, f, indent=2, ensure_ascii=False)
    print("Wrote", out_path)
