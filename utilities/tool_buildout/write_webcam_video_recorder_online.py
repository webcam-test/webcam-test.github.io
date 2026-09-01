#!/usr/bin/env python3
"""Writes src/content/webcam-video-recorder-online.json. Throwaway authoring
script, same pattern as write_webcam_test_online.py — see this project's
CLAUDE.md 'Authoring a new tool's content file'.

Scope note: the spec's own "How To Build" column mentions offering "a
resolution and format selector where the browser supports multiple
codecs" as an optional extra. This build reports the negotiated format
(via MediaRecorder.isTypeSupported preference-list selection) as a
read-only stat after each recording rather than exposing a pre-recording
codec picker — the picker is a marginal nicety this build skips to keep
scope tight, same spirit as mobile-camera-test-online's own documented
phase-1 scope reduction (see this project's CLAUDE.md)."""
import json
import os

BASE = os.path.dirname(os.path.abspath(__file__))
CONTENT_DIR = os.path.normpath(os.path.join(BASE, "..", "..", "src", "content"))

CAMERA_ICON = '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M23 7l-7 5 7 5V7z"/><rect x="1" y="5" width="15" height="14" rx="2" ry="2"/></svg>'
FILM_ICON = '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect x="2" y="3" width="20" height="18" rx="2" ry="2"/><path d="M7 3v18M17 3v18M2 8h5M2 16h5M17 8h5M17 16h5" stroke-linecap="round"/></svg>'
WARN_ICON = '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M12 9v4M12 17h.01M10.29 3.86 1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z" stroke-linecap="round" stroke-linejoin="round"/></svg>'
DOT_ICON = '<svg viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="9"/></svg>'
PLACEHOLDER_ICON = '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5"><path d="M23 7l-7 5 7 5V7z"/><rect x="1" y="5" width="15" height="14" rx="2" ry="2"/></svg>'

FIELDS_HTML = f'''<div class="tool-panel primary">
  <div class="panel-header">
    <span class="panel-icon">{CAMERA_ICON}</span>
    <div><h2>Live Camera Preview</h2><p class="panel-sub">Grant camera and microphone access, then record a short clip</p></div>
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
    <select class="device-select" id="micSelect" aria-label="Select microphone" disabled>
      <option value="">Default microphone</option>
    </select>
  </div>
  <div class="tool-actions">
    <button type="button" class="btn-primary" id="btnRecord" disabled>Start Recording</button>
    <select class="device-select" id="selectDurationCap" aria-label="Recording duration cap" style="max-width:170px" disabled>
      <option value="10">10 second cap</option>
      <option value="20" selected>20 second cap</option>
      <option value="30">30 second cap</option>
    </select>
    <span id="recordTimer" style="font-family:var(--font-mono);font-size:.85rem;color:var(--text-secondary)"></span>
  </div>
</div>
<div class="tool-panel">
  <div class="panel-header">
    <span class="panel-icon">{FILM_ICON}</span>
    <div><h2>Recording</h2><p class="panel-sub">Review and download your last clip</p></div>
  </div>
  <p class="capture-empty" id="recordingEmpty">Record a clip to review it here — nothing is uploaded.</p>
  <video id="recordingPlayback" controls style="display:none;width:100%;border-radius:var(--radius-md);background:#000;margin-bottom:.75rem"></video>
  <div class="stat-grid" id="recordingStats" style="display:none">
    <div class="stat-tile"><span class="stat-value" id="statDuration">—</span><span class="stat-label">Duration</span></div>
    <div class="stat-tile"><span class="stat-value" id="statFileSize">—</span><span class="stat-label">File Size</span></div>
    <div class="stat-tile"><span class="stat-value" id="statFormat" style="font-size:.78rem;word-break:break-word">—</span><span class="stat-label">Format Used</span></div>
    <div class="stat-tile"><a href="#" class="btn-secondary btn-icon-text" id="btnDownloadRecording" download="webcam-recording.webm" style="text-decoration:none;font-size:.82rem">Download</a></div>
  </div>
</div>
<div class="tool-panel">
  <div class="panel-header">
    <span class="panel-icon">{WARN_ICON}</span>
    <div><h2>Status</h2><p class="panel-sub">What to do if the camera or microphone won't start</p></div>
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
  var micSelect = document.getElementById('micSelect');
  var btnStart = document.getElementById('btnStartCamera');
  var btnStop = document.getElementById('btnStopCamera');
  var btnRecord = document.getElementById('btnRecord');
  var selectDurationCap = document.getElementById('selectDurationCap');
  var recordTimer = document.getElementById('recordTimer');
  var diagnosticPanel = document.getElementById('diagnosticPanel');
  var recordingEmpty = document.getElementById('recordingEmpty');
  var recordingPlayback = document.getElementById('recordingPlayback');
  var recordingStats = document.getElementById('recordingStats');
  var statDuration = document.getElementById('statDuration');
  var statFileSize = document.getElementById('statFileSize');
  var statFormat = document.getElementById('statFormat');
  var btnDownloadRecording = document.getElementById('btnDownloadRecording');

  var currentStream = null;
  var currentDeviceId = '';
  var currentMicId = '';
  var starting = false;
  var mediaRecorder = null;
  var recordedChunks = [];
  var recordingUrl = null;
  var recordStartTime = 0;
  var recordTickInterval = null;
  var recordCapTimeout = null;

  // Preference order: VP9 compresses best, VP8 is the broadest fallback,
  // plain webm/mp4 last. Feature-detected with isTypeSupported rather than
  // assumed -- codec support diverges sharply between Chrome/Edge/Firefox
  // and Safari, per this tool's own spec.
  var MIME_CANDIDATES = [
    'video/webm;codecs=vp9,opus',
    'video/webm;codecs=vp8,opus',
    'video/webm',
    'video/mp4',
  ];

  function pickMimeType() {
    if (typeof MediaRecorder === 'undefined' || !MediaRecorder.isTypeSupported) return '';
    for (var i = 0; i < MIME_CANDIDATES.length; i++) {
      if (MediaRecorder.isTypeSupported(MIME_CANDIDATES[i])) return MIME_CANDIDATES[i];
    }
    return '';
  }

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

  function formatSeconds(s) {
    var m = Math.floor(s / 60), rem = Math.floor(s % 60);
    return m + ':' + (rem < 10 ? '0' : '') + rem;
  }

  function clearRecordTimers() {
    if (recordTickInterval) { clearInterval(recordTickInterval); recordTickInterval = null; }
    if (recordCapTimeout) { clearTimeout(recordCapTimeout); recordCapTimeout = null; }
    recordTimer.textContent = '';
  }

  // Stops the in-progress MediaRecorder (if any) WITHOUT touching
  // currentStream -- called both from the normal stop-recording path and
  // from stopStream()'s teardown, so a recorder is never left running
  // against tracks that are about to be (or already were) stopped.
  function stopRecordingIfActive() {
    clearRecordTimers();
    if (mediaRecorder && mediaRecorder.state !== 'inactive') {
      mediaRecorder.stop();
    }
  }

  // Every camera page on this site copies this stopStream()/enumerate/error
  // pattern from webcam-test-online.json (see this project's own CLAUDE.md).
  // This tool additionally stops any in-progress recording first, so the
  // recorder never fires a dataavailable/stop event against tracks that
  // have already been released.
  function stopStream() {
    stopRecordingIfActive();
    if (currentStream) {
      currentStream.getTracks().forEach(function (t) { t.stop(); });
      currentStream = null;
    }
    video.srcObject = null;
    previewWrap.classList.remove('is-active');
    placeholder.style.display = 'flex';
    btnStop.disabled = true;
    btnRecord.disabled = true;
    selectDurationCap.disabled = true;
    btnRecord.textContent = 'Start Recording';
    btnRecord.classList.remove('active');
  }

  function describeError(err) {
    switch (err && err.name) {
      case 'NotAllowedError':
      case 'PermissionDeniedError':
        return { sev: 'error', html: '<strong>Camera or microphone access was blocked.</strong> Click the camera icon in your address bar (or your browser\\u2019s site settings) and allow both, then try again.' };
      case 'NotFoundError':
      case 'DevicesNotFoundError':
        return { sev: 'error', html: '<strong>No camera or microphone was detected.</strong> Make sure both are connected, then reload this page.' };
      case 'NotReadableError':
      case 'TrackStartError':
        return { sev: 'error', html: '<strong>Your camera or microphone is already in use.</strong> Another app or browser tab is probably holding it \\u2014 close video-calling apps or other camera tabs and try again.' };
      case 'OverconstrainedError':
      case 'ConstraintNotSatisfiedError':
        return { sev: 'error', html: '<strong>This device doesn\\u2019t support the requested settings.</strong> Try a different camera or microphone from the lists above.' };
      case 'SecurityError':
        return { sev: 'error', html: '<strong>Camera and microphone access require a secure connection.</strong> Make sure this page is loaded over HTTPS.' };
      case 'AbortError':
        return { sev: 'warn', html: 'The request was interrupted. Click <strong>Start Camera</strong> to try again.' };
      default:
        return { sev: 'error', html: '<strong>Something went wrong starting the camera or microphone.</strong> ' + escapeHtml((err && err.message) || 'Unknown error') + '.' };
    }
  }

  function populateSelect(select, devices, kind, currentId, emptyLabel, labelPrefix) {
    var list = devices.filter(function (d) { return d.kind === kind; });
    select.innerHTML = '';
    if (!list.length) {
      var opt = document.createElement('option');
      opt.value = '';
      opt.textContent = emptyLabel;
      select.appendChild(opt);
      select.disabled = true;
      return;
    }
    list.forEach(function (d, i) {
      var opt = document.createElement('option');
      opt.value = d.deviceId;
      opt.textContent = d.label || (labelPrefix + ' ' + (i + 1));
      if (d.deviceId === currentId) opt.selected = true;
      select.appendChild(opt);
    });
    select.disabled = false;
  }

  function refreshDeviceLists() {
    if (!navigator.mediaDevices || !navigator.mediaDevices.enumerateDevices) return Promise.resolve();
    return navigator.mediaDevices.enumerateDevices().then(function (devices) {
      populateSelect(deviceSelect, devices, 'videoinput', currentDeviceId, 'No cameras found', 'Camera');
      populateSelect(micSelect, devices, 'audioinput', currentMicId, 'No microphones found', 'Microphone');
    }).catch(function () {});
  }

  function startStream(deviceId, micId) {
    if (starting) return;
    starting = true;
    stopStream();
    setDiagnostic([{ sev: '', html: 'Requesting camera and microphone access\\u2026' }]);
    btnStart.disabled = true;

    var videoConstraint = deviceId ? { deviceId: { exact: deviceId } } : true;
    var audioConstraint = micId ? { deviceId: { exact: micId } } : true;
    navigator.mediaDevices.getUserMedia({ video: videoConstraint, audio: audioConstraint })
      .then(function (stream) {
        currentStream = stream;
        video.srcObject = stream;
        placeholder.style.display = 'none';
        previewWrap.classList.add('is-active');
        return video.play().catch(function () {}).then(function () { return stream; });
      })
      .then(function (stream) {
        var vTrack = stream.getVideoTracks()[0];
        var aTrack = stream.getAudioTracks()[0];
        var vSettings = vTrack && vTrack.getSettings ? vTrack.getSettings() : {};
        currentDeviceId = vSettings.deviceId || deviceId || '';
        var aSettings = aTrack && aTrack.getSettings ? aTrack.getSettings() : {};
        currentMicId = aSettings.deviceId || micId || '';
        btnStop.disabled = false;
        btnRecord.disabled = !pickMimeType();
        selectDurationCap.disabled = false;
        if (!pickMimeType()) {
          setDiagnostic([{ sev: 'warn', html: '<strong>Camera and microphone are live,</strong> but this browser doesn\\u2019t support video recording (MediaRecorder). You can still use this as a live preview.' }]);
        } else {
          setDiagnostic([{ sev: 'ok', html: '<strong>Camera and microphone are live.</strong> Click <strong>Start Recording</strong> to record a clip.' }]);
        }
        return refreshDeviceLists();
      })
      .catch(function (err) {
        setDiagnostic([describeError(err)]);
      })
      .finally(function () {
        starting = false;
        btnStart.disabled = false;
      });
  }

  function setRecordedResult(blob, mimeType, durationS) {
    if (recordingUrl) URL.revokeObjectURL(recordingUrl);
    recordingUrl = URL.createObjectURL(blob);
    recordingPlayback.src = recordingUrl;
    recordingPlayback.style.display = 'block';
    recordingEmpty.style.display = 'none';
    recordingStats.style.display = '';
    statDuration.textContent = formatSeconds(durationS);
    statFileSize.textContent = formatBytes(blob.size);
    statFormat.textContent = mimeType || 'Unknown';
    var ext = mimeType.indexOf('mp4') !== -1 ? 'mp4' : 'webm';
    btnDownloadRecording.href = recordingUrl;
    btnDownloadRecording.setAttribute('download', 'webcam-recording.' + ext);
  }

  function startRecording() {
    if (!currentStream) return;
    var mimeType = pickMimeType();
    if (!mimeType) return;
    recordedChunks = [];
    try {
      mediaRecorder = new MediaRecorder(currentStream, { mimeType: mimeType });
    } catch (e) {
      setDiagnostic([{ sev: 'error', html: '<strong>Could not start recording.</strong> Your browser reported: ' + escapeHtml(e.message || 'unknown error') + '.' }]);
      return;
    }
    var capSeconds = parseInt(selectDurationCap.value, 10) || 20;
    recordStartTime = Date.now();

    mediaRecorder.addEventListener('dataavailable', function (e) {
      if (e.data && e.data.size > 0) recordedChunks.push(e.data);
    });
    mediaRecorder.addEventListener('stop', function () {
      clearRecordTimers();
      btnRecord.textContent = 'Start Recording';
      btnRecord.classList.remove('active');
      var elapsedS = (Date.now() - recordStartTime) / 1000;
      if (recordedChunks.length) {
        var blob = new Blob(recordedChunks, { type: mimeType });
        setRecordedResult(blob, mimeType, elapsedS);
        setDiagnostic([{ sev: 'ok', html: '<strong>Recording saved.</strong> Review it on the right, or download it.' }]);
      }
      recordedChunks = [];
    });

    mediaRecorder.start();
    btnRecord.textContent = 'Stop Recording';
    btnRecord.classList.add('active');
    setDiagnostic([{ sev: '', html: '<span class="recording-dot"></span> Recording\\u2026' }]);

    recordTickInterval = setInterval(function () {
      var elapsed = (Date.now() - recordStartTime) / 1000;
      recordTimer.textContent = formatSeconds(elapsed) + ' / ' + formatSeconds(capSeconds);
    }, 250);
    // Duration cap: MediaRecorder has no built-in max-length option, so a
    // plain timeout stops it once the cap elapses -- also the main defence
    // against unbounded memory growth on a long recording, per this tool's
    // own spec.
    recordCapTimeout = setTimeout(function () {
      if (mediaRecorder && mediaRecorder.state === 'recording') mediaRecorder.stop();
    }, capSeconds * 1000);
  }

  btnStart.addEventListener('click', function () { startStream(deviceSelect.value, micSelect.value); });
  btnStop.addEventListener('click', function () {
    stopStream();
    setDiagnostic([{ sev: '', html: 'Camera stopped. Click <strong>Start Camera</strong> to test again.' }]);
  });
  btnRecord.addEventListener('click', function () {
    if (mediaRecorder && mediaRecorder.state === 'recording') {
      mediaRecorder.stop();
    } else {
      startRecording();
    }
  });
  deviceSelect.addEventListener('change', function () {
    if (currentStream) startStream(deviceSelect.value, micSelect.value);
  });
  micSelect.addEventListener('change', function () {
    if (currentStream) startStream(deviceSelect.value, micSelect.value);
  });

  // Guaranteed teardown: stop any in-progress recording and release the
  // camera/microphone the moment the visitor leaves this page, and revoke
  // the recorded blob's object URL so it isn't held in memory forever.
  window.addEventListener('pagehide', function () {
    stopStream();
    if (recordingUrl) { URL.revokeObjectURL(recordingUrl); recordingUrl = null; }
  });
  document.addEventListener('visibilitychange', function () {
    if (document.visibilityState === 'hidden') stopStream();
  });

  if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) {
    setDiagnostic([{ sev: 'error', html: '<strong>Your browser doesn\\u2019t support camera access.</strong> Try the latest version of Chrome, Firefox, Edge, or Safari.' }]);
    btnStart.disabled = true;
  } else if (typeof MediaRecorder === 'undefined') {
    setDiagnostic([{ sev: 'warn', html: 'Your browser supports camera access but not video recording (MediaRecorder). You can still preview your camera, but recording won\\u2019t be available.' }]);
  }
})();'''

CONTENT_HTML = '''<p>WebcamTest's video recorder captures a short clip with audio and plays it back for review, right in your browser. It's the practical pre-call check: rather than just confirming your camera turns on, this shows and lets you hear how you actually come across on a real call.</p>
<h2>How recording works</h2>
<p>Once your camera and microphone are live, clicking <strong>Start Recording</strong> begins capturing both using the standard <code>MediaRecorder</code> API — no plugins, nothing installed. Recording stops automatically once it reaches your chosen duration cap, or you can stop it early yourself. The finished clip appears immediately in the panel on the right with playback controls and a download link.</p>
<h2>Why there's a duration cap</h2>
<p>Longer recordings hold more data in memory while they're being captured, which is why this tool caps recordings at 10, 20, or 30 seconds rather than allowing unlimited length. That's plenty of time to say a sentence or two and check how you sound and look — this is a quick sanity check, not a full recording studio.</p>
<h2>Codec and format</h2>
<p>Browsers differ sharply in which video codecs they can record with. This page automatically picks the best format your specific browser supports — VP9 where available, falling back through VP8, plain WebM, and finally MP4 for browsers (mainly Safari) that don't support the WebM container at all. Whichever format was actually used is shown in the <strong>Format Used</strong> field after each recording, so you know exactly what you're downloading.</p>
<h2>Nothing is uploaded</h2>
<p>The entire recording — capture, storage, playback — happens locally in your browser tab using an in-memory object URL. It's never sent to WebcamTest's servers or any third party. Recording again replaces the previous clip and releases its memory; downloading it first if you want to keep it is worth doing before you record another one.</p>
<h2>If recording won't start</h2>
<p>Make sure you've allowed both camera and microphone access — this tool needs both, unlike the plain <a href="/">Webcam Test</a>, which only needs the camera. If your browser doesn't support <code>MediaRecorder</code> at all (rare, on very old browsers), you can still use the live preview, but recording won't be available.</p>'''

FAQ = [
    {"question": "Is my recorded video uploaded anywhere?", "answer": "No. Recording, storage, and playback all happen locally in your browser tab using the standard MediaRecorder API and an in-memory object URL. Nothing is ever sent to WebcamTest's servers or any third party."},
    {"question": "Why is my recording capped at a set number of seconds?", "answer": "Longer recordings use progressively more memory while they're being captured. Capping the length at 10, 20, or 30 seconds keeps this a quick sanity check rather than risking a slow or crashed tab on a long clip — plenty of time to check how you look and sound."},
    {"question": "What video format does it download as?", "answer": "This page automatically picks the best format your browser supports for recording — usually WebM with VP9 or VP8 video, or MP4 on Safari. Whichever one was actually used is shown in the Format Used field after each recording finishes."},
    {"question": "Why does it need microphone access, not just the camera?", "answer": "This tool records combined audio and video, since the point is checking how you actually sound and look together on a call — not just confirming the camera works. If you only want a silent snapshot, use the dedicated Photo Capture tool instead."},
    {"question": "Can I keep more than one recording at a time?", "answer": "No, recording again replaces the previous clip and releases its memory. Download anything you want to keep before starting a new recording."},
]

TOOL = {
    "slug": "webcam-video-recorder-online",
    "meta_title": "Webcam Video Recorder — Record & Download a Test Clip | WebcamTest",
    "meta_description": "Record a short video clip with your webcam and microphone, then play it back or download it. Free, works in your browser, nothing uploaded.",
    "h1": "Webcam Video Recorder",
    "subtitle": "Record a short clip with audio and play it back — the real pre-call check for how you look and sound.",
    "card": {
        "layout": "raw",
        "fields_html": FIELDS_HTML,
    },
    "script": SCRIPT,
    "content_html": CONTENT_HTML,
    "faq": FAQ,
}

if __name__ == "__main__":
    out_path = os.path.join(CONTENT_DIR, "webcam-video-recorder-online.json")
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(TOOL, f, indent=2, ensure_ascii=False)
    print("Wrote", out_path)
