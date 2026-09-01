#!/usr/bin/env python3
"""Writes src/content/webcam-side-by-side-comparison.json. Throwaway
authoring script, same pattern as write_webcam_test_online.py — see this
project's CLAUDE.md 'Authoring a new tool's content file'.

Unlike webcam-mirror-vs-natural-view-test.json (one stream, two <video>
elements), this tool genuinely opens TWO independent getUserMedia streams
for two different physical cameras -- which the spec's own JS-
considerations column flags as failing on most phones (only one active
camera at a time). This build detects that failure and falls back to a
sequential "capture one, then the other" stills-comparison mode instead of
a live dual-stream, per the spec's own explicit fallback guidance."""
import json
import os

BASE = os.path.dirname(os.path.abspath(__file__))
CONTENT_DIR = os.path.normpath(os.path.join(BASE, "..", "..", "src", "content"))

CAMERA_ICON = '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M23 7l-7 5 7 5V7z"/><rect x="1" y="5" width="15" height="14" rx="2" ry="2"/></svg>'
WARN_ICON = '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M12 9v4M12 17h.01M10.29 3.86 1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z" stroke-linecap="round" stroke-linejoin="round"/></svg>'
DOT_ICON = '<svg viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="9"/></svg>'
PLACEHOLDER_ICON = '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5"><path d="M23 7l-7 5 7 5V7z"/><rect x="1" y="5" width="15" height="14" rx="2" ry="2"/></svg>'

FIELDS_HTML = f'''<div class="tool-panel span-3">
  <div class="panel-header">
    <span class="panel-icon">{CAMERA_ICON}</span>
    <div><h2>Side-by-Side Camera Comparison</h2><p class="panel-sub">Compare a laptop camera against an external webcam, or any two connected cameras, directly</p></div>
  </div>
  <div class="media-controls">
    <select class="device-select" id="deviceSelectA" aria-label="Select Camera A" disabled><option value="">Camera A</option></select>
    <select class="device-select" id="deviceSelectB" aria-label="Select Camera B" disabled><option value="">Camera B</option></select>
    <button type="button" class="btn-primary" id="btnStart">Start Comparison</button>
    <button type="button" class="btn-secondary" id="btnStop" disabled>Stop</button>
    <button type="button" class="btn-secondary" id="btnSwap" disabled>Swap A ↔ B</button>
    <button type="button" class="btn-secondary" id="btnLayout" disabled>Vertical Split</button>
    <button type="button" class="btn-secondary" id="btnDownload" disabled>Download Comparison</button>
  </div>
  <div class="dual-preview" id="dualPreview" style="margin-top:1rem">
    <div class="media-preview" id="wrapA">
      <span class="preview-label" id="labelA">Camera A</span>
      <video id="videoA" autoplay playsinline muted></video>
      <img id="stillA" style="display:none;width:100%;height:100%;object-fit:contain" alt="Camera A capture">
      <div class="media-preview-placeholder" id="placeholderA">
        {PLACEHOLDER_ICON}
        <span>Camera A will appear here</span>
      </div>
    </div>
    <div class="media-preview" id="wrapB">
      <span class="preview-label" id="labelB">Camera B</span>
      <video id="videoB" autoplay playsinline muted></video>
      <img id="stillB" style="display:none;width:100%;height:100%;object-fit:contain" alt="Camera B capture">
      <div class="media-preview-placeholder" id="placeholderB">
        {PLACEHOLDER_ICON}
        <span>Camera B will appear here</span>
      </div>
    </div>
  </div>
  <div class="media-controls" id="captureControls" style="display:none;margin-top:1rem">
    <button type="button" class="btn-secondary" id="btnCaptureA">Capture Camera A</button>
    <button type="button" class="btn-secondary" id="btnCaptureB">Capture Camera B</button>
  </div>
  <div class="diagnostic-panel" id="diagnosticPanel" style="margin-top:1rem">
    <div class="diagnostic-item"><span class="diag-icon">{DOT_ICON}</span><span>Pick two cameras above (or leave on Default) and click <strong>Start Comparison</strong>.</span></div>
  </div>
</div>'''

SCRIPT = '''(function () {
  'use strict';

  var deviceSelectA = document.getElementById('deviceSelectA');
  var deviceSelectB = document.getElementById('deviceSelectB');
  var btnStart = document.getElementById('btnStart');
  var btnStop = document.getElementById('btnStop');
  var btnSwap = document.getElementById('btnSwap');
  var btnLayout = document.getElementById('btnLayout');
  var btnDownload = document.getElementById('btnDownload');
  var dualPreview = document.getElementById('dualPreview');
  var videoA = document.getElementById('videoA');
  var videoB = document.getElementById('videoB');
  var stillA = document.getElementById('stillA');
  var stillB = document.getElementById('stillB');
  var wrapA = document.getElementById('wrapA');
  var wrapB = document.getElementById('wrapB');
  var placeholderA = document.getElementById('placeholderA');
  var placeholderB = document.getElementById('placeholderB');
  var captureControls = document.getElementById('captureControls');
  var btnCaptureA = document.getElementById('btnCaptureA');
  var btnCaptureB = document.getElementById('btnCaptureB');
  var diagnosticPanel = document.getElementById('diagnosticPanel');

  var streamA = null, streamB = null;
  var starting = false;
  var captureMode = false; // true once a simultaneous second stream has failed
  var canvas = document.createElement('canvas');
  var ctx = canvas.getContext('2d');
  var stillAUrl = null, stillBUrl = null;

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

  function describeError(err) {
    switch (err && err.name) {
      case 'NotAllowedError':
      case 'PermissionDeniedError':
        return { sev: 'error', html: '<strong>Camera access was blocked.</strong> Allow access from your browser\\u2019s address-bar icon or site settings, then try again.' };
      case 'NotFoundError':
      case 'DevicesNotFoundError':
        return { sev: 'error', html: '<strong>That camera couldn\\u2019t be found.</strong> Make sure it\\u2019s connected, then reload this page.' };
      case 'NotReadableError':
      case 'TrackStartError':
        return { sev: 'error', html: '<strong>That camera is already in use.</strong>' };
      default:
        return { sev: 'error', html: '<strong>Something went wrong.</strong> ' + escapeHtml((err && err.message) || 'Unknown error') + '.' };
    }
  }

  // Moderate resolution on both requests -- running two live streams
  // roughly doubles bandwidth and CPU cost, per this tool's own spec.
  function requestCamera(deviceId) {
    var constraint = { width: { ideal: 640 }, height: { ideal: 480 } };
    if (deviceId) constraint.deviceId = { exact: deviceId };
    return navigator.mediaDevices.getUserMedia({ video: constraint, audio: false });
  }

  function stopStreamVar(name) {
    var s = name === 'A' ? streamA : streamB;
    if (s) {
      s.getTracks().forEach(function (t) { t.stop(); });
      if (name === 'A') streamA = null; else streamB = null;
    }
  }

  function resetPanel(which) {
    var video = which === 'A' ? videoA : videoB;
    var still = which === 'A' ? stillA : stillB;
    var wrap = which === 'A' ? wrapA : wrapB;
    var placeholder = which === 'A' ? placeholderA : placeholderB;
    video.srcObject = null;
    video.style.display = '';
    still.style.display = 'none';
    wrap.classList.remove('is-active');
    placeholder.style.display = 'flex';
  }

  function stopAll() {
    stopStreamVar('A');
    stopStreamVar('B');
    resetPanel('A');
    resetPanel('B');
    captureMode = false;
    captureControls.style.display = 'none';
    btnStop.disabled = true;
    btnSwap.disabled = true;
    btnLayout.disabled = true;
    btnDownload.disabled = true;
  }

  function populateSelects(devices) {
    var cams = devices.filter(function (d) { return d.kind === 'videoinput'; });
    [deviceSelectA, deviceSelectB].forEach(function (sel, idx) {
      var keep = sel.value;
      sel.innerHTML = '';
      if (!cams.length) {
        var opt = document.createElement('option');
        opt.value = '';
        opt.textContent = 'No cameras found';
        sel.appendChild(opt);
        sel.disabled = true;
        return;
      }
      cams.forEach(function (d, i) {
        var o = document.createElement('option');
        o.value = d.deviceId;
        o.textContent = d.label || ('Camera ' + (i + 1));
        sel.appendChild(o);
      });
      // Default A/B to two different cameras where more than one exists.
      if (keep && cams.some(function (d) { return d.deviceId === keep; })) {
        sel.value = keep;
      } else if (cams.length > 1) {
        sel.selectedIndex = idx === 1 ? 1 : 0;
      }
      sel.disabled = false;
    });
  }

  function refreshDeviceLists() {
    if (!navigator.mediaDevices || !navigator.mediaDevices.enumerateDevices) return Promise.resolve();
    return navigator.mediaDevices.enumerateDevices().then(populateSelects).catch(function () {});
  }

  function startLivePanel(which, deviceId) {
    var video = which === 'A' ? videoA : videoB;
    var wrap = which === 'A' ? wrapA : wrapB;
    var placeholder = which === 'A' ? placeholderA : placeholderB;
    return requestCamera(deviceId).then(function (stream) {
      if (which === 'A') streamA = stream; else streamB = stream;
      video.srcObject = stream;
      placeholder.style.display = 'none';
      wrap.classList.add('is-active');
      return video.play().catch(function () {});
    });
  }

  function enterCaptureMode() {
    captureMode = true;
    stopStreamVar('A');
    stopStreamVar('B');
    resetPanel('A');
    resetPanel('B');
    captureControls.style.display = 'flex';
    setDiagnostic([{ sev: 'warn', html: '<strong>This device can only use one camera at a time,</strong> so live simultaneous comparison isn\\u2019t possible here. Capture each camera separately below instead \\u2014 they\\u2019ll display side by side for comparison.' }]);
    btnStop.disabled = false;
    btnDownload.disabled = false;
  }

  function captureStill(which) {
    var deviceId = (which === 'A' ? deviceSelectA : deviceSelectB).value;
    var video = which === 'A' ? videoA : videoB;
    var still = which === 'A' ? stillA : stillB;
    var wrap = which === 'A' ? wrapA : wrapB;
    var placeholder = which === 'A' ? placeholderA : placeholderB;

    setDiagnostic([{ sev: '', html: 'Requesting Camera ' + which + '\\u2026' }]);
    return requestCamera(deviceId)
      .then(function (stream) {
        video.srcObject = stream;
        return video.play().catch(function () {}).then(function () {
          return new Promise(function (resolve) { setTimeout(resolve, 250); }); // let auto-exposure settle briefly
        }).then(function () {
          var w = video.videoWidth || 640, h = video.videoHeight || 480;
          canvas.width = w;
          canvas.height = h;
          ctx.drawImage(video, 0, 0, w, h);
          stream.getTracks().forEach(function (t) { t.stop(); });
          video.srcObject = null;
          return new Promise(function (resolve) {
            canvas.toBlob(function (blob) { resolve(blob); }, 'image/png');
          });
        });
      })
      .then(function (blob) {
        var url = URL.createObjectURL(blob);
        if (which === 'A') { if (stillAUrl) URL.revokeObjectURL(stillAUrl); stillAUrl = url; }
        else { if (stillBUrl) URL.revokeObjectURL(stillBUrl); stillBUrl = url; }
        still.src = url;
        still.style.display = 'block';
        video.style.display = 'none';
        placeholder.style.display = 'none';
        wrap.classList.add('is-active');
        setDiagnostic([{ sev: 'ok', html: '<strong>Camera ' + which + ' captured.</strong> Capture the other camera to compare, or download the comparison.' }]);
      })
      .catch(function (err) {
        setDiagnostic([describeError(err)]);
      });
  }

  function startComparison() {
    if (starting) return;
    starting = true;
    stopAll();
    setDiagnostic([{ sev: '', html: 'Requesting Camera A\\u2026' }]);
    btnStart.disabled = true;

    startLivePanel('A', deviceSelectA.value)
      .then(function () {
        setDiagnostic([{ sev: '', html: 'Camera A is live. Requesting Camera B\\u2026' }]);
        return startLivePanel('B', deviceSelectB.value);
      })
      .then(function () {
        setDiagnostic([{ sev: 'ok', html: '<strong>Both cameras are live.</strong> Use Swap to switch sides, or Download Comparison to save a combined image.' }]);
        btnStop.disabled = false;
        btnSwap.disabled = false;
        btnLayout.disabled = false;
        btnDownload.disabled = false;
      })
      .catch(function (err) {
        // A conflict on the SECOND request (device already locked by the
        // first) is the expected "only one active camera" case this
        // tool's spec explicitly calls out -- fall back to captures
        // rather than just showing an error.
        if (err && (err.name === 'NotReadableError' || err.name === 'TrackStartError' || err.name === 'OverconstrainedError')) {
          enterCaptureMode();
        } else {
          setDiagnostic([describeError(err)]);
          stopAll();
        }
      })
      .finally(function () {
        starting = false;
        btnStart.disabled = false;
      });
  }

  function swap() {
    var a = deviceSelectA.value, b = deviceSelectB.value;
    deviceSelectA.value = b;
    deviceSelectB.value = a;
    if (captureMode) {
      // Just swap the two already-captured stills and their labels.
      var tmpSrc = stillA.src; stillA.src = stillB.src; stillB.src = tmpSrc;
      var tmpDisplayA = stillA.style.display, tmpDisplayB = stillB.style.display;
      stillA.style.display = tmpDisplayB; stillB.style.display = tmpDisplayA;
    } else if (streamA && streamB) {
      startComparison();
    }
  }

  function toggleLayout() {
    var stacked = dualPreview.classList.toggle('stacked');
    btnLayout.textContent = stacked ? 'Horizontal Split' : 'Vertical Split';
  }

  function downloadComparison() {
    var stacked = dualPreview.classList.contains('stacked');
    var srcA = captureMode ? stillA : videoA;
    var srcB = captureMode ? stillB : videoB;
    var wA = srcA.videoWidth || srcA.naturalWidth || 640;
    var hA = srcA.videoHeight || srcA.naturalHeight || 480;
    var wB = srcB.videoWidth || srcB.naturalWidth || 640;
    var hB = srcB.videoHeight || srcB.naturalHeight || 480;
    var outCanvas = document.createElement('canvas');
    var outCtx = outCanvas.getContext('2d');
    if (stacked) {
      outCanvas.width = Math.max(wA, wB);
      outCanvas.height = hA + hB;
      outCtx.drawImage(srcA, 0, 0, wA, hA);
      outCtx.drawImage(srcB, 0, hA, wB, hB);
    } else {
      outCanvas.width = wA + wB;
      outCanvas.height = Math.max(hA, hB);
      outCtx.drawImage(srcA, 0, 0, wA, hA);
      outCtx.drawImage(srcB, wA, 0, wB, hB);
    }
    outCanvas.toBlob(function (blob) {
      if (!blob) return;
      var url = URL.createObjectURL(blob);
      var a = document.createElement('a');
      a.href = url;
      a.download = 'camera-comparison.png';
      document.body.appendChild(a);
      a.click();
      a.remove();
      setTimeout(function () { URL.revokeObjectURL(url); }, 1000);
    }, 'image/png');
  }

  btnStart.addEventListener('click', startComparison);
  btnStop.addEventListener('click', function () {
    stopAll();
    setDiagnostic([{ sev: '', html: 'Stopped. Click <strong>Start Comparison</strong> to try again.' }]);
  });
  btnSwap.addEventListener('click', swap);
  btnLayout.addEventListener('click', toggleLayout);
  btnDownload.addEventListener('click', downloadComparison);
  btnCaptureA.addEventListener('click', function () { captureStill('A'); });
  btnCaptureB.addEventListener('click', function () { captureStill('B'); });

  window.addEventListener('pagehide', function () {
    stopAll();
    if (stillAUrl) { URL.revokeObjectURL(stillAUrl); stillAUrl = null; }
    if (stillBUrl) { URL.revokeObjectURL(stillBUrl); stillBUrl = null; }
  });
  document.addEventListener('visibilitychange', function () {
    if (document.visibilityState === 'hidden') stopAll();
  });

  refreshDeviceLists();

  if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) {
    setDiagnostic([{ sev: 'error', html: '<strong>Your browser doesn\\u2019t support camera access.</strong> Try the latest version of Chrome, Firefox, Edge, or Safari.' }]);
    btnStart.disabled = true;
  }
})();'''

CONTENT_HTML = '''<p>WebcamTest's side-by-side camera comparison shows two cameras at once — a laptop's built-in webcam next to an external USB camera, or any two connected cameras — so you can directly judge which one to use for a call instead of switching back and forth between two separate tests.</p>
<h2>Why this only works with two truly separate cameras on desktop</h2>
<p>This tool opens two independent camera streams simultaneously, which works well on a desktop or laptop with two distinct physical cameras (a built-in webcam plus an external one, for example). On most phones, the hardware only permits one active camera stream at a time — trying to open a second one while the first is running fails, since the camera is exclusively locked to whichever request got there first.</p>
<h2>What happens when simultaneous comparison isn't possible</h2>
<p>This page detects that failure automatically and switches to a capture-and-compare mode instead: click <strong>Capture Camera A</strong>, then <strong>Capture Camera B</strong>, and each button briefly opens just that one camera, takes a still, and releases it before the next capture — so only one camera is ever active at a time, working around the hardware limitation while still giving you a genuine side-by-side comparison, just of two still images instead of two live feeds.</p>
<h2>Swap, layout, and download</h2>
<p><strong>Swap</strong> exchanges which camera appears on which side, useful for checking whether one position or the other looks better in your typical video call layout. <strong>Vertical Split / Horizontal Split</strong> toggles between a side-by-side and a stacked layout. <strong>Download Comparison</strong> saves both feeds (or both captured stills) combined into a single PNG image, matching whichever split layout is currently showing.</p>
<h2>Nothing is uploaded</h2>
<p>Both camera feeds — live or captured — are processed and combined entirely inside your browser tab. Nothing is ever sent to WebcamTest's servers or any third party.</p>'''

FAQ = [
    {"question": "Why did it switch to \"capture\" mode instead of showing both cameras live?", "answer": "This happens automatically when your device can't run two camera streams at once — most phones only support one active camera at a time. The page detects that specific failure and falls back to capturing one still image per camera in sequence instead, which works around the limitation while still giving you a real comparison."},
    {"question": "Can I compare my phone's front and rear cameras this way?", "answer": "Yes, but expect capture mode rather than a live simultaneous view on most phones — the underlying hardware limitation (one active camera at a time) applies to front/rear pairs just as much as to two separate external cameras."},
    {"question": "Why is the resolution capped at a moderate size?", "answer": "Running two live camera streams roughly doubles the bandwidth and processing cost compared to a single stream, so both requests ask for a moderate 640x480 resolution by default rather than each camera's maximum, to keep the comparison responsive."},
    {"question": "Is either camera feed uploaded anywhere?", "answer": "No. Both feeds (or captured stills) are processed and combined into the downloadable comparison image entirely inside your browser tab. Nothing is sent to WebcamTest's servers or any third party."},
]

TOOL = {
    "slug": "webcam-side-by-side-comparison",
    "meta_title": "Side-by-Side Camera Comparison — Compare Two Webcams Live | WebcamTest",
    "meta_description": "Compare two cameras at once, side by side — a laptop webcam vs. an external one, or any two connected cameras. Swap, split layout, and download the comparison. Free.",
    "h1": "Side-by-Side Camera Comparison",
    "subtitle": "Compare two cameras directly, side by side — swap sides, toggle the split, and download the combined image.",
    "card": {
        "layout": "raw",
        "fields_html": FIELDS_HTML,
    },
    "script": SCRIPT,
    "content_html": CONTENT_HTML,
    "faq": FAQ,
}

if __name__ == "__main__":
    out_path = os.path.join(CONTENT_DIR, "webcam-side-by-side-comparison.json")
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(TOOL, f, indent=2, ensure_ascii=False)
    print("Wrote", out_path)
