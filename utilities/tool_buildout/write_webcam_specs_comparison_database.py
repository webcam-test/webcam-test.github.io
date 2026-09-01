#!/usr/bin/env python3
"""Writes src/content/webcam-specs-comparison-database.json."""
import json
import os

BASE = os.path.dirname(os.path.abspath(__file__))
CONTENT_DIR = os.path.normpath(os.path.join(BASE, "..", "..", "src", "content"))

TABLE_ICON = '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect x="3" y="3" width="18" height="18" rx="2"/><path d="M3 9h18M3 15h18M9 3v18"/></svg>'
LINK_ICON = '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M10 13a5 5 0 0 0 7.54.54l3-3a5 5 0 0 0-7.07-7.07l-1.72 1.71"/><path d="M14 11a5 5 0 0 0-7.54-.54l-3 3a5 5 0 0 0 7.07 7.07l1.71-1.71"/></svg>'

FIELDS_HTML = f'''<div class="tool-panel span-3">
  <div class="panel-header">
    <span class="panel-icon">{TABLE_ICON}</span>
    <div><h2>Webcam Specs by Category</h2><p class="panel-sub">Typical specs across common webcam and camera tiers — filter and sort, then check your own camera against them</p></div>
  </div>
  <p class="field-note" style="margin-top:0"><strong>Last reviewed: 2026.</strong> These are typical, representative specs for each category — not claims about a specific model — since exact specs vary between manufacturers and revisions. Always check the actual product listing for a confirmed spec before buying.</p>
  <div class="media-controls" style="margin-bottom:1rem">
    <select class="device-select" id="useCaseFilter" aria-label="Filter by use case">
      <option value="all">All use cases</option>
      <option value="calls">Video calls</option>
      <option value="streaming">Streaming</option>
      <option value="content">Content creation</option>
    </select>
  </div>
  <div class="data-table-scroll">
    <div class="data-table" id="specsTable">
      <div class="data-table-head" id="specsTableHead"></div>
      <div id="specsRows"></div>
    </div>
  </div>
</div>
<div class="tool-panel span-2">
  <div class="panel-header">
    <span class="panel-icon">{LINK_ICON}</span>
    <div><h2>Verify These Specs on Your Own Camera</h2></div>
  </div>
  <div class="info-table">
    <div class="info-row"><span class="info-label">Resolution</span><span class="info-value" style="text-align:right;font-family:inherit;font-weight:600"><a href="/webcam-maximum-resolution-detector">Maximum Resolution Detector</a></span></div>
    <div class="info-row"><span class="info-label">Frame rate</span><span class="info-value" style="text-align:right;font-family:inherit;font-weight:600"><a href="/webcam-fps-frame-rate-checker">FPS and Frame Rate Checker</a></span></div>
    <div class="info-row"><span class="info-label">Focus type</span><span class="info-value" style="text-align:right;font-family:inherit;font-weight:600"><a href="/webcam-autofocus-test">Autofocus Test</a></span></div>
    <div class="info-row"><span class="info-label">Microphone</span><span class="info-value" style="text-align:right;font-family:inherit;font-weight:600"><a href="/microphone-test-online">Microphone Test</a></span></div>
  </div>
</div>
<div class="tool-panel">
  <div class="panel-header">
    <span class="panel-icon"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="10"/><path d="M12 16v-4M12 8h.01" stroke-linecap="round"/></svg></span>
    <div><h2>Reading This Table</h2></div>
  </div>
  <p class="field-note" style="margin-top:0">Field of view (FOV) and focus type affect real-world usability more than raw resolution for most video calls — a narrower FOV with good autofocus often looks better than a wide-angle fixed-focus camera at the same resolution.</p>
</div>'''

SCRIPT = r'''(function () {
  'use strict';

  var useCaseFilter = document.getElementById('useCaseFilter');
  var specsTableHead = document.getElementById('specsTableHead');
  var specsRows = document.getElementById('specsRows');

  var COLUMNS = ['Category', 'Resolution', 'Frame Rate', 'Field of View', 'Focus', 'Microphone'];
  var GRID = '1.3fr .8fr .7fr .8fr .9fr .9fr';

  var TIERS = [
    { name: 'Built-in Laptop Camera (Budget/Older)', resolution: '480p–720p', fps: '24–30 fps', fov: '~60–70°', focus: 'Fixed', mic: 'Mono, often noisy', useCases: ['calls'] },
    { name: 'Built-in Laptop Camera (Modern)', resolution: '1080p', fps: '30–60 fps', fov: '~75–90°', focus: 'Fixed or autofocus', mic: 'Stereo/array', useCases: ['calls'] },
    { name: 'Budget USB Webcam', resolution: '720p–1080p', fps: '30 fps', fov: '~60–70°', focus: 'Fixed', mic: 'Mono', useCases: ['calls'] },
    { name: 'Mid-Range USB Webcam', resolution: '1080p', fps: '30–60 fps', fov: '~70–80°', focus: 'Autofocus', mic: 'Stereo', useCases: ['calls', 'streaming'] },
    { name: 'Premium 4K USB Webcam', resolution: '4K (also 1080p mode)', fps: '30–60 fps', fov: '~65–90°, often adjustable', focus: 'Autofocus', mic: 'Stereo/array, noise-reduced', useCases: ['calls', 'streaming', 'content'] },
    { name: 'Streaming-Focused Webcam', resolution: '1080p', fps: 'up to 60 fps', fov: '~80–103°, often adjustable', focus: 'Fixed or autofocus', mic: 'Often none (external mic expected)', useCases: ['streaming', 'content'] },
    { name: 'Flagship Phone Rear Camera', resolution: '4K–8K photo, 1080p–4K video', fps: '30–60 fps (up to 120+ slow-mo)', fov: 'Wide, multi-lens', focus: 'Autofocus (PDAF/laser)', mic: 'Stereo', useCases: ['streaming', 'content'] },
    { name: 'Modern Phone Front Camera', resolution: '1080p–4K', fps: '30–60 fps', fov: '~75–90°', focus: 'Fixed or autofocus', mic: 'Mono/stereo', useCases: ['calls', 'content'] },
  ];

  var sortKey = 'name';
  var sortDir = 1;

  function escapeHtml(s) {
    var d = document.createElement('div');
    d.textContent = String(s);
    return d.innerHTML;
  }

  function renderHead() {
    specsTableHead.style.gridTemplateColumns = GRID;
    specsTableHead.innerHTML = COLUMNS.map(function (c, i) {
      var key = ['name', 'resolution', 'fps', 'fov', 'focus', 'mic'][i];
      return '<button type="button" data-sort="' + key + '">' + escapeHtml(c) + '</button>';
    }).join('');
    Array.prototype.forEach.call(specsTableHead.querySelectorAll('[data-sort]'), function (btn) {
      btn.addEventListener('click', function () {
        var key = btn.getAttribute('data-sort');
        if (sortKey === key) sortDir = -sortDir; else { sortKey = key; sortDir = 1; }
        render();
      });
    });
  }

  function render() {
    var filter = useCaseFilter.value;
    var rows = TIERS.filter(function (t) { return filter === 'all' || t.useCases.indexOf(filter) !== -1; });
    rows.sort(function (a, b) { return a[sortKey].localeCompare(b[sortKey]) * sortDir; });
    specsRows.innerHTML = rows.map(function (t) {
      return '<div class="data-row" style="grid-template-columns:' + GRID + '">' +
        '<span class="data-name">' + escapeHtml(t.name) + '</span>' +
        '<span>' + escapeHtml(t.resolution) + '</span>' +
        '<span>' + escapeHtml(t.fps) + '</span>' +
        '<span>' + escapeHtml(t.fov) + '</span>' +
        '<span>' + escapeHtml(t.focus) + '</span>' +
        '<span>' + escapeHtml(t.mic) + '</span></div>';
    }).join('');
  }

  useCaseFilter.addEventListener('change', render);
  renderHead();
  render();
})();'''

CONTENT_HTML = '''<p>Webcam specs are usually presented as a wall of numbers with no context for what they actually mean day to day. This table compares typical specs across common camera categories — from budget laptop cameras to flagship phone cameras — and links each spec straight to the tool on this site that verifies it on your own device.</p>
<h2>Why this uses categories, not specific product models</h2>
<p>Individual product specs change between revisions, get updated by manufacturers without notice, and vary between marketing claims and real-world measured performance. Rather than risk stating an outdated or inaccurate number for a specific named product, this table groups cameras into representative categories with typical specs for each — useful for understanding what tier of camera you're comparing against, while pointing you to the actual product listing for a confirmed exact spec before you buy.</p>
<h2>What actually matters beyond the resolution number</h2>
<p>Resolution gets most of the marketing attention, but field of view and focus type usually affect how you actually look on a call more than raw pixel count. A camera with a narrower field of view and real autofocus can look noticeably better than a wider-angle fixed-focus camera at the same resolution, since a narrower FOV avoids the "far away and distorted" look of an ultra-wide lens used up close, and autofocus keeps you sharp as you naturally shift position.</p>
<h2>Checking where your own camera fits</h2>
<p>The links in the panel alongside this table go straight to this site's own tools for each spec — run the Maximum Resolution Detector, FPS Checker, Autofocus Test and Microphone Test against your actual camera to see exactly where it lands compared to the categories above.</p>'''

FAQ = [
    {"question": "Why doesn't this table name specific webcam models?", "answer": "Specific product specs change between revisions and vary between marketing claims and real-world performance, so a specific claimed number can go stale or turn out inaccurate. This table groups cameras into representative categories with typical specs instead, and points you to the actual product listing to confirm an exact spec before buying."},
    {"question": "Is a higher resolution always better?", "answer": "Not necessarily for video calls — field of view and focus type usually matter more for how you actually look. A camera with a well-chosen field of view and real autofocus at 1080p can look better than a wider, fixed-focus camera at 4K."},
    {"question": "How do I check which category my own camera falls into?", "answer": "Use the linked tools alongside this table — the Maximum Resolution Detector, FPS Checker, Autofocus Test and Microphone Test all report real measured values from your own camera, which you can then compare against the typical ranges in the table."},
    {"question": "How often is this table updated?", "answer": "The last-reviewed date is shown above the table. Camera categories and their typical specs shift gradually as hardware improves, so check back periodically rather than treating this as a one-time snapshot."},
]

TOOL = {
    "slug": "webcam-specs-comparison-database",
    "meta_title": "Webcam Specs Comparison — Resolution, FPS, FOV & Focus | WebcamTest",
    "meta_description": "Compare typical webcam specs across common categories — resolution, frame rate, field of view, focus type and microphone — then verify your own camera against them.",
    "h1": "Webcam Specs Comparison",
    "subtitle": "Typical specs across common webcam and camera categories, filterable by use case, with links to verify your own camera against each spec.",
    "card": {
        "layout": "raw",
        "fields_html": FIELDS_HTML,
    },
    "script": SCRIPT,
    "content_html": CONTENT_HTML,
    "faq": FAQ,
}

if __name__ == "__main__":
    out_path = os.path.join(CONTENT_DIR, "webcam-specs-comparison-database.json")
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(TOOL, f, indent=2, ensure_ascii=False)
    print("Wrote", out_path)
