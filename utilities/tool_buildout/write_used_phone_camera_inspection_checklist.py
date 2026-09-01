#!/usr/bin/env python3
"""Writes src/content/used-phone-camera-inspection-checklist.json."""
import json
import os

BASE = os.path.dirname(os.path.abspath(__file__))
CONTENT_DIR = os.path.normpath(os.path.join(BASE, "..", "..", "src", "content"))

CAMERA_ICON = '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M23 7l-7 5 7 5V7z"/><rect x="1" y="5" width="15" height="14" rx="2" ry="2"/></svg>'
CHECKLIST_ICON = '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M9 11l3 3L22 4M21 12v7a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h11" stroke-linecap="round" stroke-linejoin="round"/></svg>'
SUMMARY_ICON = '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect x="3" y="3" width="18" height="18" rx="2"/><path d="M3 9h18M3 15h18M9 3v18"/></svg>'
DOT_ICON = '<svg viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="9"/></svg>'
PLACEHOLDER_ICON = '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5"><path d="M23 7l-7 5 7 5V7z"/><rect x="1" y="5" width="15" height="14" rx="2" ry="2"/></svg>'
DOWNLOAD_ICON = '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4M7 10l5 5 5-5M12 15V3" stroke-linecap="round" stroke-linejoin="round"/></svg>'

FIELDS_HTML = f'''<div class="tool-panel primary">
  <div class="panel-header">
    <span class="panel-icon">{CAMERA_ICON}</span>
    <div><h2 id="stepTitle">Step 1 of 7 — Select the Lens</h2><p class="panel-sub" id="stepSubtitle">Choose which camera you want to inspect</p></div>
  </div>
  <div class="media-preview" id="cameraPreviewWrap">
    <video id="cameraVideo" autoplay playsinline muted></video>
    <div class="media-preview-placeholder" id="cameraPlaceholder">
      {PLACEHOLDER_ICON}
      <span>Your camera feed will appear here</span>
    </div>
  </div>
  <canvas id="analysisCanvas" style="display:none"></canvas>
  <div class="media-controls" style="margin-top:1rem">
    <button type="button" class="btn-primary" id="btnStartCamera">Start Camera</button>
    <button type="button" class="btn-secondary" id="btnStopCamera" disabled>Stop Camera</button>
    <select class="device-select" id="deviceSelect" aria-label="Select camera" disabled>
      <option value="">Default camera</option>
    </select>
  </div>
  <p class="field-note" id="stepInstructions" style="margin-top:1rem">Start the camera, then use the dropdown to pick the lens you want to inspect. Repeat this whole checklist once per lens if the phone has more than one (wide, ultra-wide, telephoto, front).</p>
  <div id="stepExtra"></div>
  <div class="tool-actions" style="margin-top:.5rem">
    <button type="button" class="btn-secondary" id="btnMarkPass" disabled>Mark Pass</button>
    <button type="button" class="btn-secondary" id="btnMarkFail" disabled>Mark Fail</button>
    <button type="button" class="btn-secondary" id="btnPrevStep" disabled>&larr; Previous</button>
    <button type="button" class="btn-primary" id="btnNextStep">Next &rarr;</button>
  </div>
  <div class="diagnostic-panel" id="diagnosticPanel" style="margin-top:1rem">
    <div class="diagnostic-item" id="diagDefault"><span class="diag-icon">{DOT_ICON}</span><span>Click <strong>Start Camera</strong> and allow access when your browser asks.</span></div>
  </div>
</div>
<div class="tool-panel">
  <div class="panel-header">
    <span class="panel-icon">{CHECKLIST_ICON}</span>
    <div><h2>Checklist</h2><p class="panel-sub">Click any step to jump to it</p></div>
  </div>
  <div class="ladder-list" id="checklistList"></div>
</div>
<div class="tool-panel">
  <div class="panel-header">
    <span class="panel-icon">{SUMMARY_ICON}</span>
    <div><h2>Summary</h2><p class="panel-sub">Updates as you complete steps</p></div>
  </div>
  <div class="stat-grid">
    <div class="stat-tile highlight"><span class="stat-value" id="statPass">0</span><span class="stat-label">Passed</span></div>
    <div class="stat-tile"><span class="stat-value" id="statFail">0</span><span class="stat-label">Failed</span></div>
    <div class="stat-tile"><span class="stat-value" id="statPending">7</span><span class="stat-label">Pending</span></div>
  </div>
  <img id="summaryPhoto" alt="Captured sample photo" style="display:none;width:100%;border-radius:var(--radius-sm);margin-bottom:1rem;border:1px solid var(--border)" />
  <div class="tool-actions">
    <button type="button" class="btn-secondary btn-icon-text" id="btnCopySummary">{DOWNLOAD_ICON} Copy as Text</button>
    <button type="button" class="btn-secondary btn-icon-text" id="btnDownloadSummary">{DOWNLOAD_ICON} Download Summary</button>
  </div>
  <p class="field-note">Useful to show a seller, or to keep for your own records before buying. Nothing here is uploaded — everything stays on this page.</p>
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
  var stepTitle = document.getElementById('stepTitle');
  var stepSubtitle = document.getElementById('stepSubtitle');
  var stepInstructions = document.getElementById('stepInstructions');
  var stepExtra = document.getElementById('stepExtra');
  var btnMarkPass = document.getElementById('btnMarkPass');
  var btnMarkFail = document.getElementById('btnMarkFail');
  var btnPrevStep = document.getElementById('btnPrevStep');
  var btnNextStep = document.getElementById('btnNextStep');
  var checklistList = document.getElementById('checklistList');
  var statPass = document.getElementById('statPass');
  var statFail = document.getElementById('statFail');
  var statPending = document.getElementById('statPending');
  var summaryPhoto = document.getElementById('summaryPhoto');
  var btnCopySummary = document.getElementById('btnCopySummary');
  var btnDownloadSummary = document.getElementById('btnDownloadSummary');

  var currentStream = null;
  var starting = false;
  var stepIndex = 0;
  var capturedPhotoUrl = null;

  var STEPS = [
    { id: 'lens', title: 'Select the Lens', subtitle: 'Choose which camera you want to inspect', instructions: 'Start the camera, then use the dropdown to pick the lens you want to inspect. Repeat this whole checklist once per lens if the phone has more than one (wide, ultra-wide, telephoto, front).' },
    { id: 'resolution', title: 'Resolution Check', subtitle: 'Compare against the seller’s claimed specs', instructions: 'The resolution reported below should roughly match what the phone’s specs claim for this lens (allowing for some aspect-ratio cropping). A much lower number than advertised is worth asking the seller about.' },
    { id: 'focus', title: 'Focus Check', subtitle: 'Confirm the lens can focus cleanly', instructions: 'Point the camera at something with fine detail — text or a patterned object — a short distance away. It should snap into focus quickly and stay sharp. Judge it by eye, then mark pass or fail.' },
    { id: 'dust', title: 'Sensor Dust Check', subtitle: 'Look for dark specks on a plain white field', instructions: 'Point the camera at a plain white surface (a wall, paper, or a blank screen) filling the whole frame. Look closely for small dark specks or blurry patches — these indicate dust or debris on the sensor.' },
    { id: 'deadpixel', title: 'Dead Pixel Check', subtitle: 'Look for stuck bright dots on a dark field', instructions: 'Point the camera at a dark, evenly-lit surface (a shadowed wall, a dark cloth) filling the whole frame. Look for small bright or coloured dots that stay in the same spot — these are dead or stuck pixels.' },
    { id: 'torch', title: 'Flash / Torch Check', subtitle: 'Only applicable to rear cameras with a flash', instructions: 'If this lens has a flash, use the button below to try turning it on. Confirm you can see the flash light up, then mark pass or fail. If your browser or this lens doesn’t support torch control, that’s common and not necessarily a fault — mark it based on whatever you can observe directly on the phone instead.' },
    { id: 'capture', title: 'Capture a Sample Photo', subtitle: 'Included in your summary for review', instructions: 'Take a normal photo in good lighting using the button below. This sample gets attached to your summary so you — or a seller — can review actual image quality.' },
  ];

  var results = {};
  STEPS.forEach(function (s) { results[s.id] = 'pending'; });

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
        return { sev: 'error', html: '<strong>No camera was detected.</strong> Connect a camera and reload this page.' };
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
        setDiagnostic([{ sev: 'ok', html: '<strong>Camera is live.</strong> Use Next to move through the checklist.' }]);
        results.lens = 'pass';
        renderChecklist();
        renderStep();
        return navigator.mediaDevices.enumerateDevices().then(function (devices) {
          populateDeviceSelect(devices, settings.deviceId);
        });
      })
      .catch(function (err) {
        setDiagnostic([describeError(err)]);
        results.lens = 'fail';
        renderChecklist();
        stopStream();
      })
      .finally(function () { starting = false; btnStart.disabled = false; });
  }

  function currentTrack() {
    return currentStream ? currentStream.getVideoTracks()[0] : null;
  }

  function renderResolutionExtra() {
    var track = currentTrack();
    var settings = track && track.getSettings ? track.getSettings() : null;
    if (settings && settings.width && settings.height) {
      var mp = (settings.width * settings.height / 1e6).toFixed(1);
      stepExtra.innerHTML = '<div class="stat-grid"><div class="stat-tile highlight"><span class="stat-value">' +
        settings.width + '×' + settings.height + '</span><span class="stat-label">Reported Resolution</span></div>' +
        '<div class="stat-tile"><span class="stat-value">' + mp + ' MP</span><span class="stat-label">Megapixels</span></div></div>';
    } else {
      stepExtra.innerHTML = '<p class="field-note">Start the camera on the previous step to read its resolution.</p>';
    }
  }

  function renderTorchExtra() {
    stepExtra.innerHTML = '<div class="tool-actions"><button type="button" class="btn-secondary" id="btnTryTorch">Try Torch</button><span class="field-note" id="torchStatus" style="margin:0"></span></div>';
    var btnTryTorch = document.getElementById('btnTryTorch');
    var torchStatus = document.getElementById('torchStatus');
    btnTryTorch.addEventListener('click', function () {
      var track = currentTrack();
      if (!track) { torchStatus.textContent = 'Start the camera first.'; return; }
      var caps = track.getCapabilities ? (function () { try { return track.getCapabilities(); } catch (e) { return null; } })() : null;
      if (!caps || !caps.torch) {
        torchStatus.textContent = 'Torch control isn’t supported by this browser/lens — judge this step by eye on the phone itself instead.';
        return;
      }
      track.applyConstraints({ advanced: [{ torch: true }] })
        .then(function () {
          torchStatus.textContent = 'Torch turned on — confirm you can see it, then turn it off below.';
          btnTryTorch.textContent = 'Turn Torch Off';
          btnTryTorch.onclick = function () {
            track.applyConstraints({ advanced: [{ torch: false }] }).catch(function () {});
            renderTorchExtra();
          };
        })
        .catch(function () { torchStatus.textContent = 'Couldn’t toggle torch on this lens.'; });
    });
  }

  function renderCaptureExtra() {
    stepExtra.innerHTML = '<div class="tool-actions"><button type="button" class="btn-secondary" id="btnTakePhoto">Take Photo</button></div>';
    document.getElementById('btnTakePhoto').addEventListener('click', function () {
      if (!video.videoWidth) return;
      canvas.width = video.videoWidth;
      canvas.height = video.videoHeight;
      canvas.getContext('2d').drawImage(video, 0, 0);
      capturedPhotoUrl = canvas.toDataURL('image/jpeg', 0.9);
      summaryPhoto.src = capturedPhotoUrl;
      summaryPhoto.style.display = 'block';
      results.capture = 'pass';
      renderChecklist();
      renderSummaryCounts();
    });
  }

  function renderStep() {
    var step = STEPS[stepIndex];
    stepTitle.textContent = 'Step ' + (stepIndex + 1) + ' of ' + STEPS.length + ' — ' + step.title;
    stepSubtitle.textContent = step.subtitle;
    stepInstructions.textContent = step.instructions;

    if (step.id === 'resolution') renderResolutionExtra();
    else if (step.id === 'torch') renderTorchExtra();
    else if (step.id === 'capture') renderCaptureExtra();
    else stepExtra.innerHTML = '';

    btnPrevStep.disabled = stepIndex === 0;
    btnNextStep.textContent = stepIndex === STEPS.length - 1 ? 'Finish' : 'Next →';
    // Lens and capture grade themselves (a successful stream / a taken
    // photo IS the pass condition); every other step -- including
    // resolution, whose reported number is informational only -- needs a
    // human to look and judge, so Mark Pass/Fail stays enabled there.
    var manual = step.id !== 'lens' && step.id !== 'capture';
    btnMarkPass.disabled = !manual;
    btnMarkFail.disabled = !manual;
  }

  function renderChecklist() {
    checklistList.innerHTML = STEPS.map(function (s, i) {
      var status = results[s.id];
      var cls = status === 'pass' ? 'supported' : (status === 'fail' ? 'failed' : '');
      if (i === stepIndex) cls += ' current';
      var badge = status === 'pass' ? 'Pass' : (status === 'fail' ? 'Fail' : 'Pending');
      return '<div class="ladder-item ' + cls + '" data-step="' + i + '" style="cursor:pointer"><span class="ladder-name">' + (i + 1) + '. ' + escapeHtml(s.title) + '</span><span class="ladder-dims">' + badge + '</span></div>';
    }).join('');
    Array.prototype.forEach.call(checklistList.querySelectorAll('[data-step]'), function (el) {
      el.addEventListener('click', function () {
        stepIndex = parseInt(el.getAttribute('data-step'), 10);
        renderStep();
        renderChecklist();
      });
    });
  }

  function renderSummaryCounts() {
    var pass = 0, fail = 0, pending = 0;
    STEPS.forEach(function (s) {
      if (results[s.id] === 'pass') pass++;
      else if (results[s.id] === 'fail') fail++;
      else pending++;
    });
    statPass.textContent = String(pass);
    statFail.textContent = String(fail);
    statPending.textContent = String(pending);
  }

  function buildSummaryText() {
    var lines = ['Used Phone Camera Inspection Summary', ''];
    STEPS.forEach(function (s, i) {
      var status = results[s.id] === 'pass' ? 'PASS' : (results[s.id] === 'fail' ? 'FAIL' : 'PENDING');
      lines.push((i + 1) + '. ' + s.title + ': ' + status);
    });
    lines.push('', capturedPhotoUrl ? 'Sample photo captured: yes' : 'Sample photo captured: no');
    return lines.join('\n');
  }

  btnStart.addEventListener('click', function () { startStream(deviceSelect.value); });
  btnStop.addEventListener('click', function () {
    stopStream();
    setDiagnostic([{ sev: '', html: 'Camera stopped.' }]);
  });
  deviceSelect.addEventListener('change', function () { if (currentStream) startStream(deviceSelect.value); });

  btnMarkPass.addEventListener('click', function () {
    results[STEPS[stepIndex].id] = 'pass';
    renderChecklist();
    renderSummaryCounts();
  });
  btnMarkFail.addEventListener('click', function () {
    results[STEPS[stepIndex].id] = 'fail';
    renderChecklist();
    renderSummaryCounts();
  });
  btnPrevStep.addEventListener('click', function () {
    if (stepIndex > 0) { stepIndex--; renderStep(); renderChecklist(); }
  });
  btnNextStep.addEventListener('click', function () {
    if (stepIndex < STEPS.length - 1) { stepIndex++; renderStep(); renderChecklist(); }
  });

  btnCopySummary.addEventListener('click', function () {
    var text = buildSummaryText();
    (navigator.clipboard ? navigator.clipboard.writeText(text) : Promise.reject())
      .then(function () {
        var original = btnCopySummary.dataset.original || btnCopySummary.innerHTML;
        btnCopySummary.dataset.original = original;
        btnCopySummary.textContent = 'Copied!';
        setTimeout(function () { btnCopySummary.innerHTML = original; }, 1500);
      })
      .catch(function () {});
  });

  btnDownloadSummary.addEventListener('click', function () {
    var blob = new Blob([buildSummaryText()], { type: 'text/plain' });
    var url = URL.createObjectURL(blob);
    var a = document.createElement('a');
    a.href = url;
    a.download = 'phone-camera-inspection-summary.txt';
    document.body.appendChild(a);
    a.click();
    a.remove();
    setTimeout(function () { URL.revokeObjectURL(url); }, 1000);
  });

  window.addEventListener('pagehide', stopStream);
  document.addEventListener('visibilitychange', function () {
    if (document.visibilityState === 'hidden') stopStream();
  });

  renderChecklist();
  renderSummaryCounts();

  if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) {
    setDiagnostic([{ sev: 'error', html: '<strong>Your browser doesn’t support camera access.</strong>' }]);
    btnStart.disabled = true;
  }
})();'''

CONTENT_HTML = '''<p>Buying a used phone means trusting that its cameras actually work as well as the listing claims. This checklist walks you through every practical check a buyer can do in a browser before handing over money, and produces a pass/fail summary you can save or show the seller.</p>
<h2>What each step checks</h2>
<p>The seven steps cover lens selection (so you can repeat the whole run per lens on multi-camera phones), a resolution reading to compare against advertised specs, a focus check, a sensor dust check against a plain white field, a dead-pixel check against a dark field, a flash/torch test where supported, and a sample photo capture you can review afterward.</p>
<h2>Why some steps need your own judgement</h2>
<p>Sensor dust, dead pixels and focus quality are all things a human eye is much better at spotting reliably than an automated check — a small dark speck on a white field or a stuck bright pixel is easy for a person to notice but easy for an algorithm to mistake for something else entirely. Rather than pretend to auto-detect these with unreliable heuristics, this tool gives you the right test conditions and instructions, and you mark pass or fail based on what you actually see.</p>
<h2>Using the summary</h2>
<p>The summary panel updates as you go and works even if you don't finish every step. Both the copy and download buttons capture a snapshot of your current results plus whether a sample photo was taken — useful for comparing notes with a seller or keeping a record before you commit to a purchase.</p>'''

FAQ = [
    {"question": "Do I need to run this once per lens?", "answer": "Yes — if the phone has multiple rear cameras (wide, ultra-wide, telephoto) plus a front camera, switch the device selector at step 1 and run through the checklist again for each lens you want to verify."},
    {"question": "Why can't the dust and dead-pixel checks just tell me pass or fail automatically?", "answer": "A human eye is far more reliable at spotting a small dark speck or a stuck bright pixel than an automated heuristic would be at this resolution, and a false pass or fail on a purchase decision is worse than no automation at all. This tool sets up the right test conditions (a plain white or dark field) and instructions, and you make the call."},
    {"question": "The torch step says it's not supported — is that a problem with the phone?", "answer": "Not necessarily. Torch control through a browser is inconsistently supported depending on the device and browser — many phones simply don't expose it to web pages at all. If that happens, judge the flash by testing it directly on the phone's own camera app instead."},
    {"question": "Is my sample photo or any check result uploaded anywhere?", "answer": "No. Everything — the live preview, the captured photo, and your pass/fail choices — stays in this browser tab's memory. Only the summary you explicitly copy or download ever leaves the page, and only onto your own device."},
]

TOOL = {
    "slug": "used-phone-camera-inspection-checklist",
    "meta_title": "Used Phone Camera Inspection Checklist — Test Before You Buy | WebcamTest",
    "meta_description": "A guided 7-step checklist to inspect a used phone's camera before buying: lens, resolution, focus, sensor dust, dead pixels, flash, and a sample photo. Get a downloadable pass/fail summary.",
    "h1": "Used Phone Camera Inspection",
    "subtitle": "A guided checklist that walks you through every camera check before buying a used phone, with a downloadable pass/fail summary.",
    "card": {
        "layout": "raw",
        "fields_html": FIELDS_HTML,
    },
    "script": SCRIPT,
    "content_html": CONTENT_HTML,
    "faq": FAQ,
}

if __name__ == "__main__":
    out_path = os.path.join(CONTENT_DIR, "used-phone-camera-inspection-checklist.json")
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(TOOL, f, indent=2, ensure_ascii=False)
    print("Wrote", out_path)
