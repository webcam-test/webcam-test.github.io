#!/usr/bin/env python3
"""Writes src/content/is-my-camera-being-used-check.json."""
import json
import os

BASE = os.path.dirname(os.path.abspath(__file__))
CONTENT_DIR = os.path.normpath(os.path.join(BASE, "..", "..", "src", "content"))

SHIELD_ICON = '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M12 2l8 4v6c0 5-3.5 8.5-8 10-4.5-1.5-8-5-8-10V6l8-4z"/></svg>'
INFO_ICON = '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="10"/><path d="M12 16v-4M12 8h.01" stroke-linecap="round"/></svg>'
LIGHT_ICON = '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="4"/><path d="M12 2v2M12 20v2M4.93 4.93l1.41 1.41M17.66 17.66l1.41 1.41M2 12h2M20 12h2M4.93 19.07l1.41-1.41M17.66 6.34l1.41-1.41" stroke-linecap="round"/></svg>'
DOT_ICON = '<svg viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="9"/></svg>'

FIELDS_HTML = f'''<div class="tool-panel span-3">
  <div class="panel-header">
    <span class="panel-icon">{SHIELD_ICON}</span>
    <div><h2>Camera In-Use Privacy Check</h2><p class="panel-sub">Tests whether your camera is free to use right now, or already held by another app</p></div>
  </div>
  <canvas id="hiddenCanvas" style="display:none"></canvas>
  <div class="tool-actions">
    <button type="button" class="btn-primary" id="btnRunCheck">Run Check</button>
  </div>
  <div class="diagnostic-panel" id="diagnosticPanel">
    <div class="diagnostic-item" id="diagDefault"><span class="diag-icon">{DOT_ICON}</span><span>Click <strong>Run Check</strong>. This briefly requests camera access and releases it immediately — nothing is recorded or previewed.</span></div>
  </div>
</div>
<div class="tool-panel">
  <div class="panel-header">
    <span class="panel-icon">{INFO_ICON}</span>
    <div><h2>What This Actually Tests</h2></div>
  </div>
  <p class="field-note" style="margin-top:0">Browsers don't let any website see <em>which</em> app is using your camera — only whether a new request to use it succeeds or fails. This check can't detect spyware or confirm anything is secretly recording you. What it <strong>can</strong> tell you: if the request fails with "already in use," some other running application currently has an exclusive lock on the camera — that's usually a video-call app left open in the background, not something malicious.</p>
  <p class="field-note">If you're worried about unauthorised access, the indicator light next to your camera is the most reliable signal — see the guide alongside this.</p>
</div>
<div class="tool-panel span-2">
  <div class="panel-header">
    <span class="panel-icon">{LIGHT_ICON}</span>
    <div><h2>Indicator Light &amp; Privacy Panel Guide</h2></div>
  </div>
  <div class="info-table">
    <div class="info-row"><span class="info-label">Windows</span><span class="info-value" style="text-align:left;font-family:inherit;font-weight:400">Green LED lights whenever any app uses the camera. Check Settings → Privacy &amp; Security → Camera for which apps have permission.</span></div>
    <div class="info-row"><span class="info-label">macOS</span><span class="info-value" style="text-align:left;font-family:inherit;font-weight:400">Green LED next to the camera lights whenever it's active. Check System Settings → Privacy &amp; Security → Camera.</span></div>
    <div class="info-row"><span class="info-label">Android</span><span class="info-value" style="text-align:left;font-family:inherit;font-weight:400">A green dot appears in the status bar when the camera or mic is active. Check Settings → Privacy → Permission manager → Camera.</span></div>
    <div class="info-row"><span class="info-label">iOS</span><span class="info-value" style="text-align:left;font-family:inherit;font-weight:400">A green (camera) or orange (mic) dot appears at the top of the screen. Check Settings → Privacy &amp; Security → Camera.</span></div>
  </div>
</div>'''

SCRIPT = r'''(function () {
  'use strict';

  var btnRun = document.getElementById('btnRunCheck');
  var diagnosticPanel = document.getElementById('diagnosticPanel');
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

  // Distinguish NotReadableError/NotAllowedError/NotFoundError precisely --
  // each points at a different fix, per this tool's own spec note. Never
  // imply detection of spying; only "another app currently holds it" or
  // "access is blocked" or "no camera exists at all".
  function runCheck() {
    if (running) return;
    running = true;
    btnRun.disabled = true;
    setDiagnostic([{ sev: '', html: 'Requesting camera access…' }]);

    navigator.mediaDevices.getUserMedia({ video: true, audio: false })
      .then(function (stream) {
        stream.getTracks().forEach(function (t) { t.stop(); });
        setDiagnostic([{ sev: 'ok', html: '<strong>Your camera is free.</strong> Nothing else currently holds an exclusive lock on it. If the indicator light was on a moment ago and now isn’t, whatever was using it likely just released it.' }]);
      })
      .catch(function (err) {
        switch (err && err.name) {
          case 'NotReadableError':
          case 'TrackStartError':
            setDiagnostic([{ sev: 'warn', html: '<strong>Your camera is currently in use by another application.</strong> This is the most common cause — a video-call app (Zoom, Teams, Meet) or another browser tab left open in the background. Close other apps that might be using the camera and run the check again.' }]);
            break;
          case 'NotAllowedError':
          case 'PermissionDeniedError':
            setDiagnostic([{ sev: 'error', html: '<strong>Camera access is blocked</strong> — either you denied the permission prompt, or your browser/OS has camera access turned off for this site. This is a permissions setting, not a sign the camera is in use.' }]);
            break;
          case 'NotFoundError':
          case 'DevicesNotFoundError':
            setDiagnostic([{ sev: 'error', html: '<strong>No camera was detected</strong> on this device at all, so this check can’t tell you anything about in-use status.' }]);
            break;
          case 'SecurityError':
            setDiagnostic([{ sev: 'error', html: '<strong>Camera access requires HTTPS.</strong>' }]);
            break;
          default:
            setDiagnostic([{ sev: 'error', html: '<strong>Something went wrong running the check.</strong> ' + escapeHtml((err && err.message) || 'Unknown error') + '.' }]);
        }
      })
      .finally(function () { running = false; btnRun.disabled = false; });
  }

  btnRun.addEventListener('click', runCheck);

  if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) {
    setDiagnostic([{ sev: 'error', html: '<strong>Your browser doesn’t support camera access.</strong>' }]);
    btnRun.disabled = true;
  }
})();'''

CONTENT_HTML = '''<p>This check answers one specific question: is anything else currently holding an exclusive lock on your camera? It briefly requests camera access, reads exactly why that request succeeded or failed, and releases the camera immediately — no video is ever shown or recorded.</p>
<h2>Why this can't detect spying</h2>
<p>A website's JavaScript has no way to ask the operating system "which application is using the camera right now" — that information simply isn't exposed to the browser. All a page can ever learn is whether its own request to open the camera succeeded or failed, and if it failed, which specific error the browser reported. This check is built around reading that error precisely rather than overstating what it means.</p>
<h2>What each result actually means</h2>
<p>If the check succeeds, no other app currently has the camera locked. If it fails with "already in use," the browser is telling you a different process — almost always a video-call app or another browser tab left open — currently holds it exclusively; this is not evidence of anything malicious, since legitimate everyday apps behave exactly the same way. If it fails with a permission error, that's a browser or OS setting blocking access, unrelated to whether the camera is in use. If no camera is found at all, the check can't tell you anything either way.</p>
<h2>The indicator light is still your best signal</h2>
<p>Every modern laptop, phone and external webcam has a hardware or OS-level indicator light that turns on whenever the camera is actively capturing — this is enforced closer to the hardware than any browser API and is considered the most reliable sign of genuine camera activity. See the platform guide alongside this check for where to find your device's privacy panel.</p>'''

FAQ = [
    {"question": "Can this tool tell me if spyware is using my camera?", "answer": "No — browsers don't expose which specific application is using the camera to any website's JavaScript, only whether a new access request succeeds or fails. This tool reads that result precisely, but it can't identify or detect any particular piece of software."},
    {"question": "The check says my camera is in use, but I don't have any video call open — should I be worried?", "answer": "Check for background apps and other browser tabs first — many video-call and streaming apps keep the camera reserved even minimized. If you've closed everything and it still reports in-use, check your OS's camera privacy panel (see the guide on this page) for which apps currently have camera permission."},
    {"question": "Does this tool record or store anything?", "answer": "No. It requests the camera for a fraction of a second, checks whether that succeeded, and immediately stops the stream. No video frame is ever drawn, displayed, or saved."},
    {"question": "Why does it say \"camera is free\" but my indicator light was on a second ago?", "answer": "The indicator light reflects the moment a camera is actively capturing. If another app just released the camera before you ran this check, the light will have already turned off, and this check will correctly report the camera as free."},
]

TOOL = {
    "slug": "is-my-camera-being-used-check",
    "meta_title": "Is My Camera Being Used? — Camera In-Use Privacy Check | WebcamTest",
    "meta_description": "Check whether another app currently has an exclusive lock on your webcam. Distinguishes camera-in-use, blocked-permission and no-camera-found, with a platform guide to indicator lights and privacy panels.",
    "h1": "Camera In-Use Privacy Check",
    "subtitle": "Find out whether your camera is free right now, or already held by another application — plus what your indicator light really means.",
    "card": {
        "layout": "raw",
        "fields_html": FIELDS_HTML,
    },
    "script": SCRIPT,
    "content_html": CONTENT_HTML,
    "faq": FAQ,
}

if __name__ == "__main__":
    out_path = os.path.join(CONTENT_DIR, "is-my-camera-being-used-check.json")
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(TOOL, f, indent=2, ensure_ascii=False)
    print("Wrote", out_path)
