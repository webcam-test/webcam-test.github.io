#!/usr/bin/env python3
"""Writes src/content/webcam-resolution-standards-reference.json."""
import json
import os

BASE = os.path.dirname(os.path.abspath(__file__))
CONTENT_DIR = os.path.normpath(os.path.join(BASE, "..", "..", "src", "content"))

TABLE_ICON = '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect x="3" y="3" width="18" height="18" rx="2"/><path d="M3 9h18M3 15h18M9 3v18"/></svg>'
DOT_ICON = '<svg viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="9"/></svg>'

FIELDS_HTML = f'''<div class="tool-panel span-3">
  <div class="panel-header">
    <span class="panel-icon">{TABLE_ICON}</span>
    <div><h2>Webcam Resolution Standards</h2><p class="panel-sub">Every common video resolution from QQVGA to 8K, sortable and searchable — click a column heading to sort</p></div>
  </div>
  <div class="media-controls" style="margin-bottom:1rem">
    <input type="text" class="device-select" id="searchInput" placeholder="Search by name (e.g. “HD”, “4K”)…" style="cursor:text;background-image:none;padding-right:.9rem" />
    <button type="button" class="btn-primary" id="btnDetectMax">Highlight My Camera's Maximum</button>
  </div>
  <div class="diagnostic-panel" id="diagnosticPanel" style="margin-bottom:1rem;display:none">
    <div class="diagnostic-item" id="diagDefault"><span class="diag-icon">{DOT_ICON}</span><span></span></div>
  </div>
  <div class="data-table-scroll">
    <div class="data-table" id="dataTable">
      <div class="data-table-head">
        <button type="button" data-sort="name">Standard</button>
        <button type="button" data-sort="area">Dimensions</button>
        <button type="button" data-sort="mp">Megapixels</button>
        <button type="button" data-sort="aspect">Aspect</button>
        <button type="button" data-sort="use">Typical Use</button>
      </div>
      <div id="dataRows"></div>
    </div>
  </div>
</div>'''

SCRIPT = r'''(function () {
  'use strict';

  var searchInput = document.getElementById('searchInput');
  var btnDetectMax = document.getElementById('btnDetectMax');
  var diagnosticPanel = document.getElementById('diagnosticPanel');
  var dataRows = document.getElementById('dataRows');

  // Same 18-entry standards list as webcam-maximum-resolution-detector.json,
  // kept in the same order/values deliberately so the ladder there and the
  // reference here never diverge, per this tool's own spec note.
  var STANDARDS = [
    { name: '8K UHD', w: 7680, h: 4320, use: 'Cinema and flagship broadcast production; no consumer webcam reaches this.' },
    { name: '5K', w: 5120, h: 2880, use: 'High-end professional monitors and studio cameras.' },
    { name: 'DCI 4K', w: 4096, h: 2160, use: 'Digital cinema projection standard (slightly wider than consumer 4K).' },
    { name: '4K UHD', w: 3840, h: 2160, use: 'Flagship webcams and modern TVs/monitors; common ceiling for premium streaming setups.' },
    { name: 'QHD+', w: 2560, h: 1600, use: 'High-DPI laptop displays; occasionally used by high-end integrated cameras.' },
    { name: 'QHD', w: 2560, h: 1440, use: 'Also called 1440p; a common upper tier for mid-range webcams.' },
    { name: 'Full HD+', w: 1920, h: 1200, use: '16:10 variant of 1080p, seen on some laptop displays and cameras.' },
    { name: 'Full HD', w: 1920, h: 1080, use: 'The de facto standard for webcams and video calls today — 1080p.' },
    { name: 'HD+', w: 1600, h: 900, use: 'A step below 1080p, common on older or budget laptop webcams.' },
    { name: 'HD', w: 1280, h: 720, use: '720p — the long-standing baseline "HD" resolution for video calls.' },
    { name: 'XGA', w: 1024, h: 768, use: 'A legacy 4:3 computer display standard, still used by some older webcams.' },
    { name: 'WSVGA', w: 1024, h: 600, use: 'Older small-laptop displays and low-cost integrated cameras.' },
    { name: 'SVGA', w: 800, h: 600, use: 'An early-2000s webcam and monitor standard.' },
    { name: 'VGA', w: 640, h: 480, use: 'The original webcam resolution — still the fallback on many low-end or older devices.' },
    { name: 'CIF', w: 352, h: 288, use: 'Common Intermediate Format — an old video-conferencing standard.' },
    { name: 'QVGA', w: 320, h: 240, use: 'Quarter-VGA; used on very old or low-power devices.' },
    { name: 'QCIF', w: 176, h: 144, use: 'Quarter-CIF; found on legacy mobile video calling.' },
    { name: 'QQVGA', w: 160, h: 120, use: 'The smallest common standard — early feature-phone camera previews.' },
  ];

  function gcd(a, b) { return b === 0 ? a : gcd(b, a % b); }
  STANDARDS.forEach(function (s) {
    s.area = s.w * s.h;
    s.mp = s.area / 1e6;
    var g = gcd(s.w, s.h) || 1;
    s.aspect = (s.w / g) + ':' + (s.h / g);
  });

  var sortKey = 'area';
  var sortDir = -1; // descending by default (8K first)
  var highlightArea = null;

  function escapeHtml(s) {
    var d = document.createElement('div');
    d.textContent = String(s);
    return d.innerHTML;
  }

  function setDiagnostic(html) {
    if (!html) { diagnosticPanel.style.display = 'none'; return; }
    diagnosticPanel.style.display = 'flex';
    diagnosticPanel.querySelector('span:last-child').innerHTML = html;
  }

  function render() {
    var query = searchInput.value.trim().toLowerCase();
    var rows = STANDARDS.filter(function (s) { return s.name.toLowerCase().indexOf(query) !== -1; });
    rows.sort(function (a, b) {
      var av = a[sortKey], bv = b[sortKey];
      if (typeof av === 'string') return av.localeCompare(bv) * sortDir;
      return (av - bv) * sortDir;
    });
    dataRows.innerHTML = rows.map(function (s) {
      var isHighlight = highlightArea !== null && s.area === highlightArea;
      return '<div class="data-row' + (isHighlight ? ' highlight' : '') + '" data-area="' + s.area + '">' +
        '<span class="data-name">' + escapeHtml(s.name) + '</span>' +
        '<span class="data-dims">' + s.w + '×' + s.h + '</span>' +
        '<span class="data-mp">' + s.mp.toFixed(2) + ' MP</span>' +
        '<span class="data-aspect">' + s.aspect + '</span>' +
        '<span>' + escapeHtml(s.use) + '</span></div>';
    }).join('');
  }

  document.querySelectorAll('.data-table-head [data-sort]').forEach(function (btn) {
    btn.addEventListener('click', function () {
      var key = btn.getAttribute('data-sort');
      if (sortKey === key) sortDir = -sortDir;
      else { sortKey = key; sortDir = key === 'name' || key === 'use' ? 1 : -1; }
      render();
    });
  });
  searchInput.addEventListener('input', render);

  // Runs the same descending-probe technique as
  // webcam-maximum-resolution-detector.json -- stop at the first standard
  // the browser can actually negotiate -- but headlessly (no live preview)
  // since this page's job is to highlight a row in the table, not show video.
  function detectMax() {
    if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) {
      setDiagnostic('<strong>Your browser doesn’t support camera access.</strong>');
      return;
    }
    btnDetectMax.disabled = true;
    setDiagnostic('Probing your camera — this briefly restarts it several times…');

    var sorted = STANDARDS.slice().sort(function (a, b) { return b.area - a.area; });
    var i = 0;
    var stream = null;

    function stopCurrent() {
      if (stream) { stream.getTracks().forEach(function (t) { t.stop(); }); stream = null; }
    }

    function next() {
      if (i >= sorted.length) return finish(null);
      var entry = sorted[i];
      stopCurrent();
      navigator.mediaDevices.getUserMedia({ video: { width: { ideal: entry.w }, height: { ideal: entry.h } }, audio: false })
        .then(function (s) {
          stream = s;
          var track = s.getVideoTracks()[0];
          var settings = track.getSettings ? track.getSettings() : {};
          var actualArea = (settings.width || 0) * (settings.height || 0);
          if (actualArea >= entry.area * 0.95) return finish(entry);
          i++;
          next();
        })
        .catch(function (err) {
          if (err && (err.name === 'OverconstrainedError' || err.name === 'ConstraintNotSatisfiedError')) {
            i++;
            next();
            return;
          }
          finish(null, err);
        });
    }

    function finish(found, err) {
      stopCurrent();
      btnDetectMax.disabled = false;
      if (!found) {
        if (err) {
          var msg = err.name === 'NotAllowedError' ? 'Camera access was blocked — allow access and try again.'
            : err.name === 'NotFoundError' ? 'No camera was detected on this device.'
            : err.name === 'NotReadableError' ? 'Your camera is already in use by another app or tab.'
            : 'Something went wrong probing your camera.';
          setDiagnostic('<strong>' + msg + '</strong>');
        } else {
          setDiagnostic('Could not match your camera to a standard resolution.');
        }
        highlightArea = null;
        render();
        return;
      }
      highlightArea = found.area;
      setDiagnostic('<strong>Your camera\'s maximum negotiated resolution is ' + found.w + '×' + found.h + ' (' + found.name + ')</strong> — highlighted in the table below.');
      render();
      var rowEl = dataRows.querySelector('[data-area="' + found.area + '"]');
      if (rowEl) rowEl.scrollIntoView({ behavior: 'smooth', block: 'center' });
    }

    next();
  }

  btnDetectMax.addEventListener('click', detectMax);

  window.addEventListener('pagehide', function () {});

  render();
})();'''

CONTENT_HTML = '''<p>Resolution numbers only mean something in context. This table lists every common video resolution standard from the earliest feature-phone cameras up to 8K, with the pixel dimensions, megapixel count, aspect ratio and typical use for each — the exact lookup table this site's own <a href="/webcam-maximum-resolution-detector">Maximum Resolution Detector</a> and <a href="/webcam-camera-information-report">Camera Information Report</a> use internally.</p>
<h2>Why so many standards exist</h2>
<p>Video resolution standards accumulated over roughly three decades of cameras, monitors and video-calling software, each generation targeting whatever hardware was current at the time. Some names refer to the same resolution family (QHD and QHD+ share a height but differ in width), while others (Full HD vs Full HD+) reflect a small aspect-ratio difference rather than a meaningfully different pixel count.</p>
<h2>Finding your own camera's place in the table</h2>
<p>Click <strong>Highlight My Camera's Maximum</strong> to run a quick live probe against your own camera — it briefly requests a few candidate resolutions in descending order and highlights the highest one your browser could actually negotiate. This is the same technique the Maximum Resolution Detector uses, just condensed into a single button here.</p>
<h2>Sorting and searching</h2>
<p>Click any column heading to sort the table by that column — click again to reverse the order. The search box filters by standard name, useful for quickly finding a specific one (try "HD" or "4K").</p>'''

FAQ = [
    {"question": "Why does my camera's maximum not match its advertised megapixel spec?", "answer": "Browsers negotiate resolution through a constrained API that commonly caps out around 1080p or 4K regardless of a camera's physical sensor resolution — the sensor itself, and the manufacturer's own capture software, may be capable of more than any browser can request."},
    {"question": "What's the difference between Full HD and Full HD+?", "answer": "Full HD (1920×1080) uses a 16:9 aspect ratio; Full HD+ (1920×1200) uses 16:10, giving slightly more vertical pixels at the same width. They're not otherwise different generations of the same standard."},
    {"question": "Does this table share data with the Maximum Resolution Detector?", "answer": "Yes — both tools are built from the exact same 18-entry standards list, so a resolution reachable on one will always show up consistently on the other."},
    {"question": "Is my camera probed automatically when I load this page?", "answer": "No — nothing runs until you click \"Highlight My Camera's Maximum\" yourself. The table itself is static reference data that loads with no camera access at all."},
]

TOOL = {
    "slug": "webcam-resolution-standards-reference",
    "meta_title": "Webcam Resolution Standards Reference — QQVGA to 8K | WebcamTest",
    "meta_description": "A sortable, searchable reference table of every common webcam and video resolution standard from QQVGA to 8K, with pixel dimensions, megapixels, aspect ratio and typical use.",
    "h1": "Webcam Resolution Standards Reference",
    "subtitle": "Every common video resolution from QQVGA to 8K in one sortable, searchable table — with your own camera's maximum highlighted on request.",
    "card": {
        "layout": "raw",
        "fields_html": FIELDS_HTML,
    },
    "script": SCRIPT,
    "content_html": CONTENT_HTML,
    "faq": FAQ,
}

if __name__ == "__main__":
    out_path = os.path.join(CONTENT_DIR, "webcam-resolution-standards-reference.json")
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(TOOL, f, indent=2, ensure_ascii=False)
    print("Wrote", out_path)
