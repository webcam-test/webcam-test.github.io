"""Shared helpers for the write_*.py scripts that port a tool from the frozen
legacy-bootstrap-site/ into the JSON pipeline (webcam GIF maker, timelapse,
zoom test). Pulls the article prose + FAQ out of the legacy page, strips the
Bootstrap markup/classes and the old monthly silo-rotation sentences (the new
silo script re-injects its own), re-points old URLs to the new slugs, and
sentence-cases headings to match the rest of the site. The card markup and
the tool script are NOT ported mechanically -- those are rewritten by each
write_*.py on top of the new pipeline's panel/teardown conventions."""
import html
import os
import re
from html.parser import HTMLParser

REPO = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))
LEGACY_DIR = os.path.join(REPO, "legacy-bootstrap-site")

URL_MAP = {
    "/take-photo": "/webcam-photo-capture-online",
    "/webcam-effects": "/webcam-live-filter-preview",
    "/webcam-recorder": "/webcam-video-recorder-online",
    "/mirror": "/webcam-mirror-vs-natural-view-test",
    "/fps-checker": "/webcam-fps-frame-rate-checker",
    "/resolution-tester": "/webcam-maximum-resolution-detector",
    "/webcam-color-test": "/webcam-color-accuracy-test",
    "/webcam-quality-test": "/webcam-sharpness-focus-test",
    "/show-webcam": "/webcam-camera-information-report",
}

ACRONYMS = {"GIF", "GIFs", "FPS", "RAM", "MP4", "PTZ", "JPEG", "JPG", "DIY", "USB", "HD", "CPU", "UI", "ZIP", "PNG", "FAQ", "4K", "1080p", "WebM", "LED"}

ALLOWED = {"h2", "h3", "p", "ul", "ol", "li", "strong", "em", "code", "a", "br"}


def sentence_case(text):
    text = text.replace('"', "").replace("vs.", "vs")
    text = re.sub(r"(\d)\s*[–-]\s*(\d)", r"\1 to \2", text)
    text = re.sub(r"\s*[—–]\s*", " ", text).strip()
    words = text.split()
    out = []
    for i, w in enumerate(words):
        core = re.sub(r"^[^\w]+|[^\w]+$", "", w)
        if core in ACRONYMS or re.search(r"\d", core):
            out.append(w)
        elif i == 0:
            out.append(w[0].upper() + w[1:].lower() if len(w) > 1 else w.upper())
        else:
            out.append(w.lower())
    return " ".join(out)


class _Cleaner(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=False)
        self.out = []
        self.depth_block = 0  # inside h2/h3/p/li

    def handle_starttag(self, tag, attrs):
        if tag not in ALLOWED:
            return
        if tag in ("h2", "h3", "p", "li"):
            self.depth_block += 1
        if tag == "a":
            href = dict(attrs).get("href", "")
            href = URL_MAP.get(href, href)
            self.out.append('<a href="%s">' % href)
        elif tag == "br":
            self.out.append("<br>")
        else:
            self.out.append("<%s>" % tag)

    def handle_endtag(self, tag):
        if tag not in ALLOWED or tag == "br":
            return
        if tag in ("h2", "h3", "p", "li"):
            self.depth_block -= 1
        self.out.append("</%s>" % tag)
        if tag in ("h2", "h3", "p", "ul", "ol", "li"):
            self.out.append("\n")

    def handle_data(self, data):
        if self.depth_block > 0:
            self.out.append(data)

    def handle_entityref(self, name):
        if self.depth_block > 0:
            self.out.append("&%s;" % name)

    def handle_charref(self, name):
        if self.depth_block > 0:
            self.out.append("&#%s;" % name)


def _read(name):
    with open(os.path.join(LEGACY_DIR, name + ".html"), encoding="utf-8") as f:
        h = f.read()
    # Old monthly silo-rotation sentences + comment markers: the new silo
    # script injects its own, so none of the old ones are carried over.
    h = re.sub(r"<!-- SILO_START:(\w+) -->.*?<!-- SILO_END:\1 -->", "", h, flags=re.S)
    return h


def port_content(name, replacements=()):
    h = _read(name)
    start = h.index("<!-- Content Sections -->")
    end = h.index("<!-- FAQ Section -->")
    region = re.sub(r"<script.*?</script>|<ins.*?</ins>|<!--.*?-->", "", h[start:end], flags=re.S)
    c = _Cleaner()
    c.feed(region)
    body = "".join(c.out)
    body = re.sub(r"<h([23])>(.*?)</h\1>", lambda m: "<h%s>%s</h%s>" % (m.group(1), sentence_case(html.unescape(m.group(2))).replace("&", "&amp;"), m.group(1)), body, flags=re.S)
    body = re.sub(r"[ \t]+\n", "\n", body)
    body = re.sub(r"\n{2,}", "\n", body).strip()
    for old, new in replacements:
        if old not in body:
            raise SystemExit("replacement target not found in %s: %r" % (name, old))
        body = body.replace(old, new)
    return body


def port_faq(name, replacements=()):
    h = _read(name)
    items = re.findall(
        r'<button class="accordion-button[^>]*>\s*(.*?)\s*</button>.*?<div class="accordion-body[^>]*>\s*(.*?)\s*</div>',
        h, flags=re.S)
    faq = []
    for q, a in items:
        q = html.unescape(re.sub(r"<[^>]+>", "", q)).strip()
        a = html.unescape(re.sub(r"<[^>]+>", "", a))
        a = re.sub(r"\s+", " ", a).strip()
        for old, new in replacements:
            a = a.replace(old, new)
            q = q.replace(old, new)
        faq.append({"question": q, "answer": a})
    return faq


def common_camera_js():
    """Acquisition / enumeration / teardown / error-mapping block shared by all
    three ported tools -- copied from webcam-photo-capture-online (itself a copy
    of webcam-test-online, the reference implementation; see CLAUDE.md)."""
    return r'''  function escapeHtml(s) {
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
        return { sev: 'error', html: '<strong>Camera access was blocked.</strong> Click the camera icon in your address bar (or your browser’s site settings) and allow access, then try again.' };
      case 'NotFoundError':
      case 'DevicesNotFoundError':
        return { sev: 'error', html: '<strong>No camera was detected.</strong> Make sure a webcam is connected, then reload this page.' };
      case 'NotReadableError':
      case 'TrackStartError':
        return { sev: 'error', html: '<strong>Your camera is already in use.</strong> Another app or browser tab is probably holding it — close video-calling apps or other camera tabs and try again.' };
      case 'OverconstrainedError':
      case 'ConstraintNotSatisfiedError':
        return { sev: 'error', html: '<strong>This camera doesn’t support the requested settings.</strong> Try a different camera from the list above.' };
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
  }'''


def write_json(path, tool):
    import json
    with open(path, "w", encoding="utf-8") as f:
        json.dump(tool, f, indent=2, ensure_ascii=False)
    print("Wrote", path)
