#!/usr/bin/env python3
"""Writes src/content/webcam-timelapse-maker-online.json -- ports the old
legacy-bootstrap-site/webcam-timelapse.html onto the new pipeline. The old
page offered a ZIP download that only worked if a JSZip global happened to be
loaded (it never was, so it fell back to downloading 20 loose files and an
alert()); this version writes a real store-only ZIP in-page (CRC32 + local
headers, no library) so every frame downloads in one file. Frames are kept as
JPEG blobs rather than base64 data URLs to cut memory use."""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import _legacy_port as L

OUT = os.path.join(L.REPO, "src", "content", "webcam-timelapse-maker-online.json")

CAMERA_ICON = '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M23 7l-7 5 7 5V7z"/><rect x="1" y="5" width="15" height="14" rx="2" ry="2"/></svg>'
CLOCK_ICON = '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="9"/><path d="M12 7v5l3 2" stroke-linecap="round" stroke-linejoin="round"/></svg>'
WARN_ICON = '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M12 9v4M12 17h.01M10.29 3.86 1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z" stroke-linecap="round" stroke-linejoin="round"/></svg>'
DOT_ICON = '<svg viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="9"/></svg>'

FIELDS_HTML = f'''<div class="tool-panel primary">
  <div class="panel-header">
    <span class="panel-icon" aria-hidden="true">{CAMERA_ICON}</span>
    <div><h2>Live Camera Preview</h2><p class="panel-sub">Save one frame every few seconds, then download the sequence</p></div>
  </div>
  <div class="media-preview" id="cameraPreviewWrap">
    <video id="cameraVideo" autoplay playsinline muted></video>
    <div class="media-preview-placeholder" id="cameraPlaceholder">
      {CAMERA_ICON}
      <span>Your camera feed will appear here</span>
    </div>
    <div class="capture-flash" id="captureFlash"></div>
  </div>
  <div class="media-controls">
    <button type="button" class="btn-primary" id="btnStartCamera">Start Camera</button>
    <button type="button" class="btn-secondary" id="btnStopCamera" disabled>Stop Camera</button>
    <select class="device-select" id="deviceSelect" aria-label="Select camera" disabled>
      <option value="">Default camera</option>
    </select>
  </div>
  <div class="tool-actions">
    <button type="button" class="btn-primary" id="btnRun" disabled>Start Timelapse</button>
    <select class="device-select" id="selectInterval" aria-label="Capture interval" style="max-width:190px" disabled>
      <option value="1000">Every 1 second</option>
      <option value="2000">Every 2 seconds</option>
      <option value="5000" selected>Every 5 seconds</option>
      <option value="10000">Every 10 seconds</option>
      <option value="30000">Every 30 seconds</option>
    </select>
  </div>
</div>
<div class="tool-panel">
  <div class="panel-header">
    <span class="panel-icon" aria-hidden="true">{CLOCK_ICON}</span>
    <div><h2>Timelapse Report</h2><p class="panel-sub">Frames saved this session, held in your browser only</p></div>
  </div>
  <div class="stat-grid">
    <div class="stat-tile"><span class="stat-value" id="statFrames">0</span><span class="stat-label">Frames</span></div>
    <div class="stat-tile"><span class="stat-value" id="statElapsed">0s</span><span class="stat-label">Elapsed</span></div>
    <div class="stat-tile"><span class="stat-value" id="statPlayback">0s</span><span class="stat-label">Playback at 10 fps</span></div>
    <div class="stat-tile"><span class="stat-value" id="statMemory">0 MB</span><span class="stat-label">Memory Used</span></div>
  </div>
  <div class="thumb-strip" id="thumbStrip" aria-label="Captured frames"></div>
  <div class="tool-actions" style="margin-top:1rem;margin-bottom:0">
    <button type="button" class="btn-primary" id="btnDownload" disabled>Download Frames (ZIP)</button>
    <button type="button" class="btn-secondary" id="btnClear" disabled>Clear Frames</button>
  </div>
</div>
<div class="tool-panel">
  <div class="panel-header">
    <span class="panel-icon" aria-hidden="true">{WARN_ICON}</span>
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
  var flashEl = document.getElementById('captureFlash');
  var deviceSelect = document.getElementById('deviceSelect');
  var btnStart = document.getElementById('btnStartCamera');
  var btnStop = document.getElementById('btnStopCamera');
  var btnRun = document.getElementById('btnRun');
  var selectInterval = document.getElementById('selectInterval');
  var btnDownload = document.getElementById('btnDownload');
  var btnClear = document.getElementById('btnClear');
  var thumbStrip = document.getElementById('thumbStrip');
  var diagnosticPanel = document.getElementById('diagnosticPanel');
  var statFrames = document.getElementById('statFrames');
  var statElapsed = document.getElementById('statElapsed');
  var statPlayback = document.getElementById('statPlayback');
  var statMemory = document.getElementById('statMemory');

  var PLAYBACK_FPS = 10;
  var MAX_FRAMES = 1000; // hard cap so a forgotten tab can't eat all RAM
  var canvas = document.createElement('canvas');
  canvas.width = 640;
  canvas.height = 480;
  var ctx = canvas.getContext('2d');

  var currentStream = null;
  var currentDeviceId = '';
  var starting = false;
  var running = false;
  var frames = []; // {blob, url}
  var totalBytes = 0;
  var captureTick = null;
  var elapsedTick = null;
  var elapsedSeconds = 0;

__COMMON__

  function formatBytes(n) {
    if (n < 1024 * 1024) return (n / 1024).toFixed(0) + ' KB';
    return (n / (1024 * 1024)).toFixed(1) + ' MB';
  }

  function formatElapsed(s) {
    return s < 60 ? s + 's' : Math.floor(s / 60) + 'm ' + (s % 60) + 's';
  }

  function updateStats() {
    statFrames.textContent = String(frames.length);
    statElapsed.textContent = formatElapsed(elapsedSeconds);
    statPlayback.textContent = (frames.length / PLAYBACK_FPS).toFixed(1) + 's';
    statMemory.textContent = formatBytes(totalBytes);
    btnDownload.disabled = !frames.length;
    btnClear.disabled = !frames.length || running;
  }

  function clearFrames() {
    frames.forEach(function (f) { URL.revokeObjectURL(f.url); });
    frames = [];
    totalBytes = 0;
    elapsedSeconds = 0;
    thumbStrip.innerHTML = '';
    updateStats();
  }

  function stopTimelapse() {
    running = false;
    if (captureTick) { clearInterval(captureTick); captureTick = null; }
    if (elapsedTick) { clearInterval(elapsedTick); elapsedTick = null; }
    btnRun.textContent = 'Start Timelapse';
    selectInterval.disabled = !currentStream;
    updateStats();
  }

  // Every camera page on this site copies this stopStream()/enumerate/error
  // pattern from webcam-test-online.json (see this project's own CLAUDE.md).
  function stopStream() {
    stopTimelapse();
    if (currentStream) {
      currentStream.getTracks().forEach(function (t) { t.stop(); });
      currentStream = null;
    }
    video.srcObject = null;
    previewWrap.classList.remove('is-active');
    placeholder.style.display = 'flex';
    btnStop.disabled = true;
    btnRun.disabled = true;
    selectInterval.disabled = true;
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
        btnRun.disabled = false;
        selectInterval.disabled = false;
        setDiagnostic([{ sev: 'ok', html: '<strong>Camera is live.</strong> Choose an interval and click <strong>Start Timelapse</strong>.' }]);
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

  function captureFrame() {
    if (!video.videoWidth) return;
    ctx.drawImage(video, 0, 0, canvas.width, canvas.height);
    canvas.toBlob(function (blob) {
      if (!blob) return;
      var url = URL.createObjectURL(blob);
      frames.push({ blob: blob, url: url });
      totalBytes += blob.size;
      var img = document.createElement('img');
      img.src = url;
      img.alt = 'Frame ' + frames.length;
      img.width = 40;
      img.height = 30;
      thumbStrip.appendChild(img);
      thumbStrip.scrollLeft = thumbStrip.scrollWidth;
      flashEl.classList.add('flash');
      requestAnimationFrame(function () { flashEl.classList.remove('flash'); });
      updateStats();
      if (frames.length >= MAX_FRAMES) {
        stopTimelapse();
        setDiagnostic([{ sev: 'warn', html: 'Stopped at <strong>' + MAX_FRAMES + ' frames</strong> to protect your browser\\u2019s memory. Download the frames, clear them, and start a new run if you need more.' }]);
      }
    }, 'image/jpeg', 0.8);
  }

  function startTimelapse() {
    if (running || !currentStream) return;
    var intervalMs = parseInt(selectInterval.value, 10);
    clearFrames();
    running = true;
    btnRun.textContent = 'Stop Timelapse';
    selectInterval.disabled = true;
    btnClear.disabled = true;
    setDiagnostic([{ sev: 'ok', html: '<strong>Timelapse running.</strong> One frame every ' + (intervalMs / 1000) + ' second' + (intervalMs === 1000 ? '' : 's') + '. Keep this tab open.' }]);
    captureFrame();
    captureTick = setInterval(captureFrame, intervalMs);
    elapsedTick = setInterval(function () {
      elapsedSeconds++;
      statElapsed.textContent = formatElapsed(elapsedSeconds);
    }, 1000);
  }

  // --- Minimal store-only ZIP writer (no compression -- JPEGs are already
  // compressed). Local file header + central directory + end record. ---
  var crcTable = null;
  function crc32(bytes) {
    if (!crcTable) {
      crcTable = new Uint32Array(256);
      for (var n = 0; n < 256; n++) {
        var c = n;
        for (var k = 0; k < 8; k++) c = (c & 1) ? (0xEDB88320 ^ (c >>> 1)) : (c >>> 1);
        crcTable[n] = c >>> 0;
      }
    }
    var crc = 0xFFFFFFFF;
    for (var i = 0; i < bytes.length; i++) crc = crcTable[(crc ^ bytes[i]) & 0xFF] ^ (crc >>> 8);
    return (crc ^ 0xFFFFFFFF) >>> 0;
  }

  function buildZip(files) { // files: [{name, bytes}]
    var parts = [], central = [], offset = 0, enc = new TextEncoder();
    files.forEach(function (f) {
      var name = enc.encode(f.name);
      var crc = crc32(f.bytes);
      var local = new DataView(new ArrayBuffer(30));
      local.setUint32(0, 0x04034b50, true);
      local.setUint16(4, 20, true);
      local.setUint16(6, 0x0800, true); // UTF-8 names
      local.setUint16(8, 0, true);      // stored
      local.setUint32(14, crc, true);
      local.setUint32(18, f.bytes.length, true);
      local.setUint32(22, f.bytes.length, true);
      local.setUint16(26, name.length, true);
      parts.push(local.buffer, name, f.bytes);
      var cd = new DataView(new ArrayBuffer(46));
      cd.setUint32(0, 0x02014b50, true);
      cd.setUint16(4, 20, true);
      cd.setUint16(6, 20, true);
      cd.setUint16(8, 0x0800, true);
      cd.setUint32(16, crc, true);
      cd.setUint32(20, f.bytes.length, true);
      cd.setUint32(24, f.bytes.length, true);
      cd.setUint16(28, name.length, true);
      cd.setUint32(42, offset, true);
      central.push(cd.buffer, name);
      offset += 30 + name.length + f.bytes.length;
    });
    var cdSize = 0;
    central.forEach(function (b) { cdSize += b.byteLength !== undefined ? b.byteLength : b.length; });
    var end = new DataView(new ArrayBuffer(22));
    end.setUint32(0, 0x06054b50, true);
    end.setUint16(8, files.length, true);
    end.setUint16(10, files.length, true);
    end.setUint32(12, cdSize, true);
    end.setUint32(16, offset, true);
    return new Blob(parts.concat(central, [end.buffer]), { type: 'application/zip' });
  }

  function downloadFrames() {
    if (!frames.length) return;
    btnDownload.disabled = true;
    Promise.all(frames.map(function (f) { return f.blob.arrayBuffer(); })).then(function (buffers) {
      var files = buffers.map(function (buf, i) {
        return { name: 'frame_' + String(i + 1).padStart(4, '0') + '.jpg', bytes: new Uint8Array(buf) };
      });
      var url = URL.createObjectURL(buildZip(files));
      var a = document.createElement('a');
      a.href = url;
      a.download = 'timelapse-frames.zip';
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      setTimeout(function () { URL.revokeObjectURL(url); }, 4000);
      setDiagnostic([{ sev: 'ok', html: '<strong>Downloaded ' + files.length + ' frames.</strong> Import the JPEG sequence into any video editor to assemble the finished timelapse.' }]);
    }).catch(function () {
      setDiagnostic([{ sev: 'error', html: '<strong>Could not build the ZIP.</strong> Try clearing frames and capturing a shorter run.' }]);
    }).finally(function () {
      btnDownload.disabled = !frames.length;
    });
  }

  btnStart.addEventListener('click', function () { startStream(deviceSelect.value); });
  btnStop.addEventListener('click', function () {
    stopStream();
    setDiagnostic([{ sev: '', html: 'Camera stopped. Your captured frames are still available to download.' }]);
  });
  btnRun.addEventListener('click', function () {
    if (running) {
      stopTimelapse();
      setDiagnostic([{ sev: 'ok', html: '<strong>' + frames.length + ' frames captured.</strong> Download them as a ZIP or start again.' }]);
    } else {
      startTimelapse();
    }
  });
  btnDownload.addEventListener('click', downloadFrames);
  btnClear.addEventListener('click', clearFrames);
  deviceSelect.addEventListener('change', function () {
    if (currentStream && !running) startStream(deviceSelect.value);
  });

  // Guaranteed teardown: release the camera and every frame object URL the
  // moment the visitor leaves this page. Hiding the tab does NOT stop a
  // running timelapse (browsers throttle timers in background tabs, but a
  // long capture is exactly the use case); it only stops if idle.
  window.addEventListener('pagehide', function () {
    stopStream();
    clearFrames();
  });
  document.addEventListener('visibilitychange', function () {
    if (document.visibilityState === 'hidden' && !running) stopStream();
  });

  if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) {
    setDiagnostic([{ sev: 'error', html: '<strong>Your browser doesn\\u2019t support camera access.</strong> Try the latest version of Chrome, Firefox, Edge, or Safari.' }]);
    btnStart.disabled = true;
  }
})();'''.replace("__COMMON__", L.common_camera_js())

CONTENT_HTML = L.port_content("webcam-timelapse", replacements=[
    ("Click start timelapse", "Start the timelapse"),
    ("Select how often the tool should capture a frame", "Click <strong>Start Camera</strong>, then select how often the tool should capture a frame"),
    ("Allow camera access when prompted. The live feed appears and the tool starts capturing frames automatically at your chosen interval. A brief red flash on the video border confirms each frame has been saved.",
     "Click <strong>Start Timelapse</strong>. The tool starts saving frames automatically at your chosen interval, and a brief white flash over the video confirms each frame has been saved."),
    ("Click <strong>Stop Timelapse</strong> when done. All captured frames download as a ZIP file.",
     "Click <strong>Stop Timelapse</strong> when done, then <strong>Download Frames (ZIP)</strong> to save every frame in one file."),
    ("Capture interval choosing the right setting", "Capture interval and choosing the right setting"),
    ("What to capture webcam timelapse subject ideas", "What to capture and webcam timelapse subject ideas"),
])
FAQ = L.port_faq("webcam-timelapse", replacements=[
    ("What is the red flash I see on the video?", "What is the flash I see on the video?"),
    ("The brief red border flash on the video element", "The brief white flash over the video"),
])

TOOL = {
    "slug": "webcam-timelapse-maker-online",
    "meta_description": "Make a timelapse from your webcam online. Pick an interval, capture frames automatically and download them as a ZIP — free, no upload, no software.",
    "h1": "Webcam Timelapse Maker",
    "subtitle": "Set a capture interval and let your camera save a frame every few seconds — a <strong>webcam timelapse</strong> you can download as an image sequence.",
    "card": {"layout": "raw", "fields_html": FIELDS_HTML},
    "script": SCRIPT,
    "content_html": CONTENT_HTML,
    "faq": FAQ,
}

if __name__ == "__main__":
    L.write_json(OUT, TOOL)
