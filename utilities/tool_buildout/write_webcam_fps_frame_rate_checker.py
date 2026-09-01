#!/usr/bin/env python3
"""Writes src/content/webcam-fps-frame-rate-checker.json. Throwaway authoring
script, same pattern as write_webcam_test_online.py — see this project's
CLAUDE.md 'Authoring a new tool's content file'."""
import json
import os

BASE = os.path.dirname(os.path.abspath(__file__))
CONTENT_DIR = os.path.normpath(os.path.join(BASE, "..", "..", "src", "content"))

CAMERA_ICON = '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M23 7l-7 5 7 5V7z"/><rect x="1" y="5" width="15" height="14" rx="2" ry="2"/></svg>'
PULSE_ICON = '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M22 12h-4l-3 9L9 3l-3 9H2" stroke-linecap="round" stroke-linejoin="round"/></svg>'
WARN_ICON = '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M12 9v4M12 17h.01M10.29 3.86 1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z" stroke-linecap="round" stroke-linejoin="round"/></svg>'
DOT_ICON = '<svg viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="9"/></svg>'
PLACEHOLDER_ICON = '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5"><path d="M23 7l-7 5 7 5V7z"/><rect x="1" y="5" width="15" height="14" rx="2" ry="2"/></svg>'

FIELDS_HTML = f'''<div class="tool-panel primary">
  <div class="panel-header">
    <span class="panel-icon">{CAMERA_ICON}</span>
    <div><h2>Live Camera Preview</h2><p class="panel-sub">Grant camera access, then measure the frames it actually delivers</p></div>
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
    <select class="device-select" id="deviceSelect" aria-label="Select camera" disabled>
      <option value="">Default camera</option>
    </select>
  </div>
  <div class="tool-actions">
    <button type="button" class="btn-secondary" id="btnMeasure" disabled>Measure Now (3s)</button>
    <button type="button" class="btn-secondary" id="btnMeasureLong" disabled>Sustained Run (15s)</button>
  </div>
</div>
<div class="tool-panel">
  <div class="panel-header">
    <span class="panel-icon">{PULSE_ICON}</span>
    <div><h2>Frame Rate Report</h2><p class="panel-sub">Measured directly, not read from a claimed setting</p></div>
  </div>
  <div class="stat-grid">
    <div class="stat-tile"><span class="stat-value" id="statRequested">—</span><span class="stat-label">Requested FPS</span></div>
    <div class="stat-tile"><span class="stat-value" id="statMeasured">—</span><span class="stat-label">Measured FPS</span></div>
    <div class="stat-tile"><span class="stat-value" id="statVariance" style="font-size:.95rem">—</span><span class="stat-label">Frame Rate Range</span></div>
    <div class="stat-tile"><span class="stat-value" id="statMethod" style="font-size:.72rem;word-break:break-word">—</span><span class="stat-label">Method Used</span></div>
  </div>
  <p class="field-note">Requested FPS comes from <code>getSettings()</code> — what your browser negotiated with the camera, not what it delivers frame-by-frame. Measured FPS counts real delivered frames over the run.</p>
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
  var btnMeasure = document.getElementById('btnMeasure');
  var btnMeasureLong = document.getElementById('btnMeasureLong');
  var diagnosticPanel = document.getElementById('diagnosticPanel');
  var statRequested = document.getElementById('statRequested');
  var statMeasured = document.getElementById('statMeasured');
  var statVariance = document.getElementById('statVariance');
  var statMethod = document.getElementById('statMethod');

  var currentStream = null;
  var currentDeviceId = '';
  var starting = false;
  var measuring = false;
  var rvfcId = null;
  var rafId = null;

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

  function resetStats() {
    statRequested.textContent = '\\u2014';
    statMeasured.textContent = '\\u2014';
    statVariance.textContent = '\\u2014';
    statMethod.textContent = '\\u2014';
  }

  function stopMeasuring() {
    measuring = false;
    if (rvfcId !== null && video.cancelVideoFrameCallback) {
      video.cancelVideoFrameCallback(rvfcId);
      rvfcId = null;
    }
    if (rafId !== null) {
      cancelAnimationFrame(rafId);
      rafId = null;
    }
    btnMeasure.disabled = !currentStream;
    btnMeasureLong.disabled = !currentStream;
  }

  // Every camera page on this site copies this stopStream()/enumerate/error
  // pattern from webcam-test-online.json (see this project's own CLAUDE.md
  // — "no shared JS runtime file" is deliberate). This tool additionally
  // cancels any in-flight frame-rate measurement loop before releasing the
  // stream, so a still-running rVFC/rAF callback never fires against a dead
  // video element.
  function stopStream() {
    stopMeasuring();
    if (currentStream) {
      currentStream.getTracks().forEach(function (t) { t.stop(); });
      currentStream = null;
    }
    video.srcObject = null;
    previewWrap.classList.remove('is-active');
    placeholder.style.display = 'flex';
    btnStop.disabled = true;
    btnMeasure.disabled = true;
    btnMeasureLong.disabled = true;
    resetStats();
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
        statRequested.textContent = settings.frameRate ? (Math.round(settings.frameRate * 10) / 10 + ' fps') : 'Not reported';
        btnStop.disabled = false;
        btnMeasure.disabled = false;
        btnMeasureLong.disabled = false;
        setDiagnostic([{ sev: 'ok', html: '<strong>Camera is live.</strong> Click <strong>Measure Now</strong> to count the frames it actually delivers.' }]);
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

  // requestVideoFrameCallback fires once per decoded video frame -- the
  // correct way to count frames actually delivered by the camera, distinct
  // from the negotiated rate getSettings() reports. Firefox doesn't
  // implement it, so this falls back to counting frames drawn to a
  // throwaway canvas on a plain requestAnimationFrame loop instead, per
  // this tool's own spec.
  function measureFPS(durationMs) {
    if (measuring || !currentStream) return;
    measuring = true;
    btnMeasure.disabled = true;
    btnMeasureLong.disabled = true;
    setDiagnostic([{ sev: '', html: 'Measuring for ' + (durationMs / 1000) + ' seconds \\u2014 hold still and keep this tab visible\\u2026' }]);

    var frameCount = 0;
    var deltas = [];
    var lastTime = null;
    var startTime = null;
    var supportsRVFC = typeof video.requestVideoFrameCallback === 'function';
    statMethod.textContent = supportsRVFC ? 'requestVideoFrameCallback' : 'canvas frame counter';

    function finish() {
      measuring = false;
      var elapsedS = (performance.now() - startTime) / 1000;
      var avg = elapsedS > 0 ? frameCount / elapsedS : 0;
      statMeasured.textContent = avg.toFixed(1) + ' fps';

      if (deltas.length > 2) {
        var instFps = deltas.map(function (d) { return d > 0 ? 1000 / d : 0; });
        var minFps = Math.min.apply(null, instFps);
        var maxFps = Math.max.apply(null, instFps);
        statVariance.textContent = minFps.toFixed(1) + '\\u2013' + maxFps.toFixed(1) + ' fps';
      } else {
        statVariance.textContent = 'Not enough samples';
      }

      var requestedNum = parseFloat(statRequested.textContent);
      var gapNote = '';
      if (!isNaN(requestedNum) && avg < requestedNum * 0.85) {
        gapNote = ' This is noticeably below the requested rate \\u2014 low light is the most common cause, since cameras often drop frame rate to compensate.';
      }
      setDiagnostic([{ sev: 'ok', html: '<strong>Measured ' + avg.toFixed(1) + ' fps</strong> over ' + elapsedS.toFixed(1) + ' seconds.' + gapNote }]);
      btnMeasure.disabled = !currentStream;
      btnMeasureLong.disabled = !currentStream;
    }

    if (supportsRVFC) {
      var rvfcTick = function (now) {
        if (!measuring) return;
        if (startTime === null) startTime = performance.now();
        if (lastTime !== null) deltas.push(now - lastTime);
        lastTime = now;
        frameCount++;
        if (performance.now() - startTime >= durationMs) { finish(); return; }
        rvfcId = video.requestVideoFrameCallback(rvfcTick);
      };
      rvfcId = video.requestVideoFrameCallback(rvfcTick);
    } else {
      var canvas = document.createElement('canvas');
      var ctx = canvas.getContext('2d');
      canvas.width = 32;
      canvas.height = 18;
      var rafTick = function (now) {
        if (!measuring) return;
        if (startTime === null) startTime = performance.now();
        if (lastTime !== null) deltas.push(now - lastTime);
        lastTime = now;
        try { ctx.drawImage(video, 0, 0, canvas.width, canvas.height); } catch (e) {}
        frameCount++;
        if (performance.now() - startTime >= durationMs) { finish(); return; }
        rafId = requestAnimationFrame(rafTick);
      };
      rafId = requestAnimationFrame(rafTick);
    }
  }

  btnStart.addEventListener('click', function () { startStream(deviceSelect.value); });
  btnStop.addEventListener('click', function () {
    stopStream();
    setDiagnostic([{ sev: '', html: 'Camera stopped. Click <strong>Start Camera</strong> to test again.' }]);
  });
  btnMeasure.addEventListener('click', function () { measureFPS(3000); });
  btnMeasureLong.addEventListener('click', function () { measureFPS(15000); });
  deviceSelect.addEventListener('change', function () {
    if (currentStream) startStream(deviceSelect.value);
  });

  // Guaranteed teardown: release the camera (and cancel any in-flight
  // measurement loop, via stopStream() -> stopMeasuring()) the moment the
  // visitor leaves this page, even if they never clicked Stop.
  window.addEventListener('pagehide', stopStream);
  document.addEventListener('visibilitychange', function () {
    if (document.visibilityState === 'hidden') stopStream();
  });

  if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) {
    setDiagnostic([{ sev: 'error', html: '<strong>Your browser doesn\\u2019t support camera access.</strong> Try the latest version of Chrome, Firefox, Edge, or Safari.' }]);
    btnStart.disabled = true;
  }
})();'''

CONTENT_HTML = '''<p>WebcamTest's FPS and frame rate checker measures the frame rate your camera is actually delivering, separately from the rate your browser <em>claims</em> to have negotiated. Those two numbers are often different, and the gap is the usual cause of choppy, stuttery video calls that a simple "camera works" test never catches.</p>
<h2>Why the requested rate isn't the real rate</h2>
<p><code>getSettings().frameRate</code> reports what your browser and camera driver agreed to when the stream was negotiated — it is a request, not a promise. The camera can still deliver fewer frames per second than that in practice, most commonly because of low light: many webcams automatically slow down their frame rate to gather more light per frame when the room is dim, trading smoothness for a brighter (less noisy) image. This page's <strong>Requested FPS</strong> tile shows the negotiated number; the <strong>Measured FPS</strong> tile shows what actually arrived.</p>
<h2>How the measurement works</h2>
<p>Clicking <strong>Measure Now</strong> counts real delivered video frames over a fixed window using <code>requestVideoFrameCallback</code>, the browser API built specifically for this — it fires once per decoded frame, not once per display refresh. Firefox doesn't implement that API yet, so this page falls back to counting frames drawn to a small offscreen canvas on a standard animation loop instead, which is noted in the <strong>Method Used</strong> field so you know which measurement approach produced your result.</p>
<h2>Quick measurement vs. sustained run</h2>
<p>The default <strong>Measure Now</strong> button runs a 3-second sample, enough for a quick sanity check. <strong>Sustained Run</strong> measures for 15 seconds instead, which is long enough to catch a specific failure mode a short sample misses entirely: thermal throttling, where a camera (especially on phones and cheap USB webcams) starts strong and then drops frame rate a few seconds in as it heats up. If your quick measurement looks fine but calls still feel choppy after a few minutes, run the sustained test.</p>
<h2>Reading the frame rate range</h2>
<p>The <strong>Frame Rate Range</strong> field shows the spread between your camera's fastest and slowest instantaneous frame interval during the run, not just the average. A tight range means a steady, consistent feed; a wide range — especially one with a very low minimum — means the camera is stuttering even if the average looks acceptable, which is exactly the kind of unevenness a single averaged number would otherwise hide.</p>
<h2>Troubleshooting a camera that won't start</h2>
<p>The status panel explains exactly what went wrong using your browser's own error type. See the <a href="/">Webcam Test</a> for the same acquisition flow with a fuller explanation of each error, and the <a href="/webcam-maximum-resolution-detector">Maximum Resolution Detector</a> if you're trying to find the highest resolution your browser can reach rather than the frame rate at your current one.</p>'''

FAQ = [
    {"question": "Why is my measured FPS lower than the requested FPS?", "answer": "This is normal and common, especially in low light. Cameras frequently reduce frame rate automatically to brighten each frame when there isn't much light available, trading smoothness for image quality. Try measuring again in a brighter room to see the effect directly."},
    {"question": "What does 'Method Used' mean, and does it change my result?", "answer": "It shows whether your browser measured frames with requestVideoFrameCallback (fires once per decoded video frame — the most accurate method) or the canvas-drawing fallback used in Firefox, which doesn't support that API yet. Both approaches give a real, useful measurement; the fallback is simply a slightly less direct way of counting the same thing."},
    {"question": "What's the difference between Measure Now and Sustained Run?", "answer": "Measure Now samples for 3 seconds, enough for a quick check. Sustained Run measures for 15 seconds, long enough to catch thermal throttling — some cameras deliver a strong frame rate for the first few seconds and then drop as they heat up, which a short sample won't reveal."},
    {"question": "Is any of my video uploaded during this test?", "answer": "No. Frame counting happens entirely inside your browser tab — nothing is recorded, saved, or sent anywhere. The Firefox fallback draws frames to a small offscreen canvas purely to count them; that canvas is never displayed, saved, or read back as an image."},
    {"question": "Why does my frame rate range look so wide?", "answer": "A wide range between the fastest and slowest frame interval usually means the camera is stuttering rather than delivering frames at a steady pace, even if the average frame rate looks fine. Common causes include a busy USB bus (other high-bandwidth devices sharing the same hub), a struggling autofocus or auto-exposure adjustment, or the low-light frame-rate reduction described above."},
]

TOOL = {
    "slug": "webcam-fps-frame-rate-checker",
    "meta_title": "FPS & Frame Rate Checker — Measure Your Real Camera FPS | WebcamTest",
    "meta_description": "Measure the frame rate your webcam actually delivers, not just what it claims. Free online FPS checker with a sustained run to catch thermal throttling.",
    "h1": "FPS & Frame Rate Checker",
    "subtitle": "Measure the frame rate your camera actually delivers — not just the rate it claims to support.",
    "card": {
        "layout": "raw",
        "fields_html": FIELDS_HTML,
    },
    "script": SCRIPT,
    "content_html": CONTENT_HTML,
    "faq": FAQ,
}

if __name__ == "__main__":
    out_path = os.path.join(CONTENT_DIR, "webcam-fps-frame-rate-checker.json")
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(TOOL, f, indent=2, ensure_ascii=False)
    print("Wrote", out_path)
