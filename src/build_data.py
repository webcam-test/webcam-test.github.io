#!/usr/bin/env python3
"""Authors data/site.json + data/tools.json + data/pages.json for
webcamtest.io's tool pages. Run this, then `python3 src/generate.py`, to
(re)build public/. See this project's CLAUDE.md for the full pipeline.

Modeled on passwordhive's own build_data.py (individual_websites/passwordhive/
src/build_data.py): every tool is a single file, content/<slug>.json carries
the *entire* page (meta_description, h1/subtitle, card, script, content_html,
faq — see src/content/README.md for the field contract). There is no
meta_title field: generate.py renders <title> from h1 directly, so every
page's title tag matches its H1 exactly, with no "| WebcamTest" suffix. This
function just loads and lightly post-processes those files (nav_name/
footer_anchor lookup, slug order) via load_tool() — no per-tool Python
builder function, same as passwordhive.

Planned scope is 44 tools total, from camera-and-audio-test-tools-specification.xlsx
in this directory's own root (its "Tool Specification"/"Build Phases" sheets).
TOOL_SLUGS below lists only the tools actually built so far — see
utilities/tool_buildout/progress.json for the full 44-tool roadmap and status.
"""
import html
import json
import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, "data")
CONTENT_DIR = os.path.join(BASE_DIR, "content")

SITE_NAME = "WebcamTest"
# This repo IS webcam-test.github.io — no custom domain move (unlike
# mic-tests.github.io -> mictest.dev), so this is the real, final domain,
# not a placeholder. Ports content from the old hand-authored site now
# archived in legacy-bootstrap-site/ — see this project's own CLAUDE.md.
DOMAIN = "webcam-test.github.io"
HOME_SLUG = "webcam-test-online"
CONTACT_EMAIL = "vinithablog@gmail.com"
OWNER_NAME = "Vinitha"
OWNER_LOCATION = "Palakkad, Kerala, India"
OWNER_BEHANCE_URL = "https://www.behance.net/vinithapu"

# Phase 1 (see the spec's "Build Phases" sheet): the 6 foundation pages that
# establish camera acquisition/enumeration/teardown and the audio-context
# pattern every later tool's own script copies from. Phases 2-5 (38 more
# tools) are tracked, not yet built — see utilities/tool_buildout/progress.json.
TOOL_SLUGS = [
    "webcam-test-online",
    "webcam-camera-information-report",
    "webcam-maximum-resolution-detector",
    "mobile-camera-test-online",
    "microphone-test-online",
    "speaker-test-online",
    "webcam-fps-frame-rate-checker",
    "webcam-fullscreen-viewer",
    "webcam-photo-capture-online",
    "webcam-video-recorder-online",
    "front-camera-test-online",
    "rear-camera-test-online",
    "phone-camera-resolution-checker",
    "microphone-input-level-meter",
    "microphone-record-playback-test",
    "left-right-stereo-channel-test",
    "webcam-not-working-troubleshooting-guide",
    "camera-permissions-guide-windows-mac-android-ios",
    "webcam-mirror-vs-natural-view-test",
    "webcam-side-by-side-comparison",
    "webcam-sharpness-focus-test",
    "webcam-lighting-exposure-test",
    "is-my-camera-being-used-check",
    "used-phone-camera-inspection-checklist",
    "phone-camera-flash-torch-test",
    "webcam-resolution-standards-reference",
    "microphone-quality-spectrum-analyzer",
    "audio-frequency-sweep-20hz-20khz",
    "online-hearing-frequency-test",
    "webcam-rule-of-thirds-composition-grid",
    "webcam-live-filter-preview",
    "webcam-low-light-noise-test",
    "webcam-color-accuracy-test",
    "webcam-autofocus-test",
    "phone-camera-zoom-test",
    "phone-camera-orientation-test",
    "camera-test-vs-webcam-test-explained",
    "webcam-specs-comparison-database",
    "use-phone-as-webcam-guide",
    "speaker-polarity-phase-test",
    "subwoofer-bass-test-online",
    "audio-latency-delay-test",
    "microphone-echo-test",
    "webcam-latency-delay-test",
]

# Short, stable nav/footer names for ALL 44 planned tools (from the spec's
# "Tool Name" column) — kept separate from each tool's own `h1` (which is
# SEO/hero copy and can run long), same convention as passwordhive's
# NAV_NAMES. Entries for not-yet-built tools are pre-added so they resolve
# the moment each slug is wired into TOOL_SLUGS/CATEGORY_GROUPS.
NAV_NAMES = {
    # A. Camera Core
    "webcam-test-online": "Webcam Test",
    "webcam-maximum-resolution-detector": "Max Resolution Detector",
    "webcam-fps-frame-rate-checker": "FPS & Frame Rate Checker",
    "webcam-fullscreen-viewer": "Fullscreen Camera Viewer",
    "webcam-mirror-vs-natural-view-test": "Mirror vs Natural View",
    "webcam-photo-capture-online": "Photo Capture",
    "webcam-video-recorder-online": "Video Recorder",
    "webcam-camera-information-report": "Camera Information Report",
    "webcam-side-by-side-comparison": "Side-by-Side Comparison",
    "webcam-rule-of-thirds-composition-grid": "Composition Grid",
    "webcam-live-filter-preview": "Live Filter Preview",
    "webcam-sharpness-focus-test": "Sharpness & Focus Test",
    "webcam-lighting-exposure-test": "Lighting & Exposure Test",
    "webcam-low-light-noise-test": "Low-Light Noise Test",
    "webcam-color-accuracy-test": "Colour Accuracy Test",
    "webcam-autofocus-test": "Autofocus Test",
    "webcam-latency-delay-test": "Camera Latency Test",
    "is-my-camera-being-used-check": "Is My Camera Being Used?",
    # B. Camera Mobile
    "mobile-camera-test-online": "Mobile Camera Test",
    "front-camera-test-online": "Mobile Front Camera Test",
    "rear-camera-test-online": "Mobile Rear Camera Test",
    "phone-camera-resolution-checker": "Mobile Phone Camera Resolution Checker",
    "phone-camera-flash-torch-test": "Mobile Flash & Torch Test",
    "phone-camera-zoom-test": "Mobile Camera Zoom Test",
    "phone-camera-orientation-test": "Mobile Camera Orientation Test",
    "used-phone-camera-inspection-checklist": "Used Mobile Phone Camera Inspection",
    # C. Camera Reference
    "webcam-resolution-standards-reference": "Resolution Standards Reference",
    "webcam-specs-comparison-database": "Webcam Specs Comparison",
    "camera-test-vs-webcam-test-explained": "Camera Test vs Webcam Test",
    "webcam-not-working-troubleshooting-guide": "Webcam Troubleshooting Guide",
    "camera-permissions-guide-windows-mac-android-ios": "Camera Permissions Guide",
    "use-phone-as-webcam-guide": "Use Your Phone as a Webcam",
    # D. Audio
    "microphone-test-online": "Microphone Test",
    "microphone-input-level-meter": "Microphone Level Meter",
    "microphone-record-playback-test": "Microphone Record & Playback",
    "microphone-quality-spectrum-analyzer": "Microphone Quality & Spectrum",
    "speaker-test-online": "Speaker Test",
    "left-right-stereo-channel-test": "Left & Right Stereo Test",
    "speaker-polarity-phase-test": "Speaker Polarity & Phase Test",
    "audio-frequency-sweep-20hz-20khz": "Frequency Sweep Test",
    "subwoofer-bass-test-online": "Subwoofer & Bass Test",
    "audio-latency-delay-test": "Audio Latency Test",
    "online-hearing-frequency-test": "Online Hearing Test",
    "microphone-echo-test": "Microphone Echo Test",
}

# Long-tail anchor text for the footer mega-menu only — kept separate from
# NAV_NAMES (used by the header dropdowns/mobile "More" menu, which need
# short, scannable labels). Every tool's footer link on every page currently
# reuses the exact same short NAV_NAMES string, which is fine for UX but
# wastes the SEO value of a footer sitewide link: a descriptive, keyword-
# varied phrase per tool gives search engines more distinct signal about
# what each linked page is actually about than 44 near-identical two-word
# labels repeated on every page. These are natural phrases (verb + subject),
# not keyword-stuffed, one per built tool — see render_footer_mega() in
# generate.py for where this is consumed.
FOOTER_ANCHORS = {
    "webcam-test-online": "Test your webcam online free",
    "webcam-camera-information-report": "View your full camera information report",
    "webcam-maximum-resolution-detector": "Detect your webcam's maximum resolution",
    "mobile-camera-test-online": "Test your mobile phone camera online",
    "microphone-test-online": "Test your microphone online free",
    "speaker-test-online": "Test your speakers online free",
    "webcam-fps-frame-rate-checker": "Check your webcam's real frame rate",
    "webcam-fullscreen-viewer": "View your webcam in fullscreen",
    "webcam-photo-capture-online": "Take a photo with your webcam",
    "webcam-video-recorder-online": "Record webcam video with audio",
    "front-camera-test-online": "Test your mobile phone's front camera",
    "rear-camera-test-online": "Test your mobile phone's rear camera",
    "phone-camera-resolution-checker": "Check your mobile phone camera's true resolution",
    "microphone-input-level-meter": "Set your microphone input gain correctly",
    "microphone-record-playback-test": "Record and play back your microphone",
    "left-right-stereo-channel-test": "Test your left and right speaker channels",
    "webcam-not-working-troubleshooting-guide": "Fix a webcam that's not working",
    "camera-permissions-guide-windows-mac-android-ios": "Allow camera and microphone permissions guide",
    "webcam-mirror-vs-natural-view-test": "Compare mirrored vs natural camera view",
    "webcam-side-by-side-comparison": "Compare two webcams side by side",
    "webcam-sharpness-focus-test": "Test your webcam's sharpness and focus",
    "webcam-lighting-exposure-test": "Check your webcam's lighting and exposure",
    "is-my-camera-being-used-check": "Check if your camera is in use",
    "used-phone-camera-inspection-checklist": "Inspect a used mobile phone's camera before buying",
    "phone-camera-flash-torch-test": "Test your mobile phone's flash and torch",
    "webcam-resolution-standards-reference": "Browse the video resolution standards table",
    "microphone-quality-spectrum-analyzer": "Analyze your microphone's frequency spectrum",
    "audio-frequency-sweep-20hz-20khz": "Run a 20 Hz to 20 kHz frequency sweep",
    "online-hearing-frequency-test": "Test the highest frequency you can hear",
    "webcam-rule-of-thirds-composition-grid": "Overlay a rule of thirds grid",
    "webcam-live-filter-preview": "Preview live webcam filters and adjustments",
    "webcam-low-light-noise-test": "Test your webcam's low-light noise",
    "webcam-color-accuracy-test": "Test your webcam's colour accuracy",
    "webcam-autofocus-test": "Test if your camera has autofocus",
    "phone-camera-zoom-test": "Test your mobile phone camera's zoom range",
    "phone-camera-orientation-test": "Test mobile camera orientation in portrait and landscape",
    "camera-test-vs-webcam-test-explained": "Camera test vs webcam test explained",
    "webcam-specs-comparison-database": "Compare webcam specs by category",
    "use-phone-as-webcam-guide": "Use your phone as a webcam",
    "speaker-polarity-phase-test": "Test speaker polarity and phase wiring",
    "subwoofer-bass-test-online": "Test your subwoofer and bass response",
    "audio-latency-delay-test": "Measure your audio latency delay",
    "microphone-echo-test": "Test microphone echo with headphones",
    "webcam-latency-delay-test": "Measure your webcam's latency delay",
}

# Nav strip / footer mega-menu / homepage tool-grid categories, one per spec
# cluster. Built tools are listed in "slugs" (resolved against by_slug, real
# pages); everything else is listed in "tools" as a static {slug, name} pair
# — that link 404s until its content/<slug>.json is written and its slug
# moves into "slugs", same accepted convention passwordhive uses during its
# own multi-session buildout (see that project's CLAUDE.md).
CATEGORY_GROUPS = [
    {
        "key": "camera-core",
        "label": "Camera Core",
        "short_label": "Camera",
        "cluster": "camera-core",
        "tagline": "Test your webcam's resolution, frame rate, focus, exposure and colour accuracy.",
        "slugs": ["webcam-test-online", "webcam-camera-information-report", "webcam-maximum-resolution-detector", "webcam-fps-frame-rate-checker", "webcam-fullscreen-viewer", "webcam-photo-capture-online", "webcam-video-recorder-online", "webcam-mirror-vs-natural-view-test", "webcam-side-by-side-comparison", "webcam-sharpness-focus-test", "webcam-lighting-exposure-test", "is-my-camera-being-used-check", "webcam-rule-of-thirds-composition-grid", "webcam-live-filter-preview", "webcam-low-light-noise-test", "webcam-color-accuracy-test", "webcam-autofocus-test", "webcam-latency-delay-test"],
        "tools": [],
    },
    {
        "key": "camera-mobile",
        "label": "Camera Mobile",
        "short_label": "Mobile",
        "cluster": "camera-mobile",
        "tagline": "Front/rear lens tests, resolution checks and a used-phone camera inspection built mobile-first.",
        "slugs": ["mobile-camera-test-online", "front-camera-test-online", "rear-camera-test-online", "phone-camera-resolution-checker", "used-phone-camera-inspection-checklist", "phone-camera-flash-torch-test", "phone-camera-zoom-test", "phone-camera-orientation-test"],
        "tools": [],
    },
    {
        "key": "camera-reference",
        "label": "Camera Reference",
        "short_label": "Guides",
        "cluster": "camera-reference",
        "tagline": "Resolution standards, spec comparisons, troubleshooting and permissions guides.",
        "slugs": ["webcam-not-working-troubleshooting-guide", "camera-permissions-guide-windows-mac-android-ios", "webcam-resolution-standards-reference", "camera-test-vs-webcam-test-explained", "webcam-specs-comparison-database", "use-phone-as-webcam-guide"],
        "tools": [],
    },
    {
        "key": "audio",
        "label": "Audio",
        "short_label": "Audio",
        "cluster": "audio",
        "tagline": "Microphone, speaker, stereo, latency and hearing tests, all running locally in your browser.",
        "slugs": ["microphone-test-online", "speaker-test-online", "microphone-input-level-meter", "microphone-record-playback-test", "left-right-stereo-channel-test", "microphone-quality-spectrum-analyzer", "audio-frequency-sweep-20hz-20khz", "online-hearing-frequency-test", "speaker-polarity-phase-test", "subwoofer-bass-test-online", "audio-latency-delay-test", "microphone-echo-test"],
        "tools": [],
    },
]


def load_tool(slug):
    with open(os.path.join(CONTENT_DIR, "%s.json" % slug), encoding="utf-8") as f:
        tool = json.load(f)
    tool["nav_name"] = NAV_NAMES[slug]
    tool["footer_anchor"] = FOOTER_ANCHORS[slug]
    return tool


def cluster_for_slug(slug):
    for group in CATEGORY_GROUPS:
        if slug in group.get("slugs", []):
            return group["cluster"]
    return "camera-core"


def build_tools():
    tools = [load_tool(slug) for slug in TOOL_SLUGS]
    for t in tools:
        t["cluster"] = cluster_for_slug(t["slug"])
    return tools


def build_site(tools):
    return {
        "site_name": SITE_NAME,
        "domain": DOMAIN,
        "home_slug": HOME_SLUG,
        "contact_email": CONTACT_EMAIL,
        "footer_tagline": "Free camera and audio testing tools that run entirely in your browser. Nothing you record or capture is ever uploaded.",
        "nav_groups": CATEGORY_GROUPS,
        "company_links": [
            {"label": "About", "href": "/about"},
            {"label": "Contact", "href": "/contact"},
            {"label": "Sitemap", "href": "/sitemap"},
            {"label": "Privacy Policy", "href": "/privacy-policy"},
            {"label": "Terms of Service", "href": "/terms"},
        ],
    }


# ---------------------------------------------------------------------------
# Info pages — freshly authored (no prior site to port content from, unlike
# passwordhive's verbatim-copy situation). Same typed heading+paragraphs
# (+list) shape render_info_content() in generate.py expects.
# ---------------------------------------------------------------------------

def build_sitemap_sections(tools):
    """Builds /sitemap's sections straight from CATEGORY_GROUPS/TOOL_SLUGS
    rather than hand-authoring it, so it can never drift out of sync as
    tools are added — same reasoning as passwordhive's own build_sitemap_sections()."""
    by_slug = {t["slug"]: t for t in tools}
    sections = []
    for group in CATEGORY_GROUPS:
        items = []
        for slug in group.get("slugs", []):
            url = "/" if slug == HOME_SLUG else "/%s" % slug
            items.append('<a href="%s">%s</a>' % (url, html.escape(by_slug[slug]["nav_name"])))
        for t in group.get("tools", []):
            items.append(html.escape(t["name"]) + " (coming soon)")
        sections.append({"heading": group["label"], "paragraphs": [group["tagline"]], "list": items})
    return sections


def build_pages(tools):
    sitemap_sections = build_sitemap_sections(tools)
    pages = [
        {
            "slug": "about",
            "meta_description": "WebcamTest is a free collection of browser-based camera and microphone testing tools. Nothing you record is ever uploaded — it all runs locally on your device.",
            "h1": "About WebcamTest",
            "subtitle": "Camera and audio diagnostics that never leave your browser.",
            "sections": [
                {
                    "heading": "Hi, I'm %s!" % OWNER_NAME,
                    "paragraphs": [
                        "I'm a designer and developer from %s. I studied Textile &amp; Apparel Design and later transitioned into digital design and web development — a path that gave me a unique eye for both aesthetics and usability." % OWNER_LOCATION,
                        "I build free online tools that solve everyday problems I've personally faced. WebcamTest started with a familiar frustration — joining a call and not knowing whether the problem was my camera, my microphone, or the app itself, with no quick way to check.",
                    ],
                },
                {
                    "heading": "What WebcamTest does",
                    "paragraphs": [
                        "WebcamTest is a growing collection of free tools for testing webcams, phone cameras, microphones and speakers directly in your browser. Every tool uses the standard <code>getUserMedia</code>/Web Audio browser APIs to talk to your hardware — there is no app to install, no account to create, and no upload step.",
                        "The site is split into four groups: camera tools for laptops and external webcams, a mobile-first set of camera tools built specifically for phones (not a desktop tool that happens to load on one), a reference section explaining what the numbers mean and how to fix common problems, and an audio half covering microphones and speakers.",
                    ],
                },
                {
                    "heading": "Why nothing is uploaded",
                    "paragraphs": [
                        "Every camera frame, audio sample and captured photo or recording is processed with JavaScript running in your own browser tab. None of it is ever sent to a server. When you close a tool's page or click its Stop control, the underlying camera and microphone tracks are released — this matters most on a privacy-positioned tool like this one, where leaving a camera indicator light on after you've left the page would be the single worst thing the site could do.",
                    ],
                },
                {
                    "heading": "What we're honest about",
                    "paragraphs": [
                        "Some of these tests have real limits that are worth stating plainly rather than glossing over: a browser can only reach the resolution the operating system's camera driver exposes to it, which is usually far below a phone's advertised megapixel count; some browsers (notably Safari on iOS) don't expose capabilities like torch or zoom to web pages at all; and a few measurements — audio latency, hearing thresholds — depend heavily on your own hardware and can only ever be reported as an estimate, never an exact number. Each tool says so directly in its own results rather than in a footnote.",
                    ],
                },
                {
                    "heading": "Contact Information",
                    "paragraphs": [
                        "<a href=\"mailto:%s\">%s</a>" % (CONTACT_EMAIL, CONTACT_EMAIL),
                        OWNER_LOCATION,
                    ],
                },
                {
                    "heading": "Connect With Me",
                    "paragraphs": [
                        "<a href=\"%s\" target=\"_blank\" rel=\"noopener\">Behance Portfolio</a>" % OWNER_BEHANCE_URL,
                        "<a href=\"mailto:%s\">Send an Email</a>" % CONTACT_EMAIL,
                    ],
                },
            ],
        },
        {
            "slug": "contact",
            "meta_description": "Get in touch with the WebcamTest team.",
            "h1": "Contact",
            "subtitle": "Questions, bug reports and tool requests are all welcome.",
            "sections": [
                {
                    "heading": "Say Hello!",
                    "paragraphs": [
                        "Got a question, spotted an error, or just want to share something? I'd genuinely love to hear from you — drop me a message and I'll get back to you as soon as I can.",
                    ],
                },
                {
                    "heading": "Ways You Can Help",
                    "paragraphs": [
                        "Every suggestion makes this better for everyone. Even a quick note saying something is wrong is incredibly helpful!",
                    ],
                    "list": [
                        "Report a tool that's not detecting your camera or microphone correctly",
                        "Share which browser or device gave you a confusing or wrong result",
                        "Suggest a new camera or audio test you'd find useful",
                        "Recommend features that would make these tools more useful",
                    ],
                },
                {
                    "heading": "Contact Information",
                    "paragraphs": [
                        "<a href=\"mailto:%s\">%s</a>" % (CONTACT_EMAIL, CONTACT_EMAIL),
                        OWNER_LOCATION,
                    ],
                },
                {
                    "heading": "Connect With Me",
                    "paragraphs": [
                        "<a href=\"%s\" target=\"_blank\" rel=\"noopener\">Behance Portfolio</a>" % OWNER_BEHANCE_URL,
                        "<a href=\"mailto:%s\">Send an Email</a>" % CONTACT_EMAIL,
                    ],
                },
            ],
        },
        {
            "slug": "sitemap",
            "meta_description": "Every WebcamTest tool and page, organized by category, in one place.",
            "h1": "Sitemap",
            "subtitle": "Every tool on WebcamTest, grouped the same way the nav menu groups them.",
            "sections": sitemap_sections,
        },
        {
            "slug": "privacy-policy",
            "meta_description": "WebcamTest's privacy policy: what data we collect (very little), and why our tools never see the camera footage, photos, or audio you test with.",
            "h1": "Privacy Policy",
            "subtitle": "What we collect, what we don't, and why.",
            "sections": [
                {
                    "heading": "Your camera and microphone data",
                    "paragraphs": [
                        "Every tool on this site accesses your camera and/or microphone using your browser's own permission prompt. Once granted, video frames and audio samples are processed entirely inside your browser tab using JavaScript — none of it is transmitted to WebcamTest or to any third party. Photos you capture and clips you record stay in your browser's memory until you download them or navigate away; they are never uploaded.",
                    ],
                },
                {
                    "heading": "Analytics",
                    "paragraphs": [
                        "This site does not currently run any analytics or advertising scripts. If that changes, this page will be updated to say exactly what is collected and why.",
                    ],
                },
                {
                    "heading": "Changes to this policy",
                    "paragraphs": [
                        "If this policy changes, the update will be reflected on this page with a new effective date.",
                    ],
                },
            ],
        },
        {
            "slug": "terms",
            "meta_description": "Terms of service for using WebcamTest's free camera and audio testing tools.",
            "h1": "Terms of Service",
            "subtitle": "The short version: these tools are free, provided as-is, and not a substitute for professional diagnosis.",
            "sections": [
                {
                    "heading": "Use of this site",
                    "paragraphs": [
                        "WebcamTest's tools are provided free of charge, as-is, with no warranty of any kind. Hardware measurements (resolution, frame rate, latency, hearing thresholds, and similar) are estimates produced by browser APIs and should not be treated as certified or medical-grade results — the hearing test in particular is explicitly not a medical hearing test.",
                    ],
                },
                {
                    "heading": "No liability",
                    "paragraphs": [
                        "WebcamTest is not liable for decisions made based on these tools' results, including purchasing or diagnostic decisions. Audio playback tools include volume warnings where relevant hardware damage or hearing damage is a real risk (sustained high-level low frequencies, high-level frequency sweeps) — read them before raising your volume.",
                    ],
                },
            ],
        },
    ]
    return pages


def main():
    os.makedirs(DATA_DIR, exist_ok=True)
    tools = build_tools()
    site = build_site(tools)
    pages = build_pages(tools)
    with open(os.path.join(DATA_DIR, "site.json"), "w", encoding="utf-8") as f:
        json.dump(site, f, indent=2)
    with open(os.path.join(DATA_DIR, "tools.json"), "w", encoding="utf-8") as f:
        json.dump(tools, f, indent=2)
    with open(os.path.join(DATA_DIR, "pages.json"), "w", encoding="utf-8") as f:
        json.dump(pages, f, indent=2)
    print("Wrote site.json (%d nav groups), tools.json (%d tools), pages.json (%d pages)" % (
        len(CATEGORY_GROUPS), len(tools), len(pages)
    ))


if __name__ == "__main__":
    main()
