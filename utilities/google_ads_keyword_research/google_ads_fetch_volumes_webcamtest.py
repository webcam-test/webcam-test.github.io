"""
google_ads_fetch_volumes_webcamtest.py
--------------------------------------
Fetches Google Ads keyword historical metrics for each tool page on the
webcam_test_project (WebcamTest site).

Usage:
    python google_ads_fetch_volumes_webcamtest.py --customer-id 8450761335
    python google_ads_fetch_volumes_webcamtest.py --customer-id 8450761335 --geo 2840
    python google_ads_fetch_volumes_webcamtest.py --dry-run
"""

import os
import sys
import time
import argparse
import logging
from datetime import datetime
from pathlib import Path

import openpyxl

SCRIPT_DIR = Path(__file__).parent
YAML_PATH = SCRIPT_DIR / "google-ads.yaml"
OUTPUT_DIR = SCRIPT_DIR / "output"

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger(__name__)

RETRY_LIMIT = 3
RETRY_DELAY = 5

GEO_TARGETS = {
    "2840": "United States",
    "2356": "India",
    "2036": "Australia",
    "2826": "United Kingdom",
    "2124": "Canada",
}

LANGUAGE_EN = "languageConstants/1000"

# ── WebcamTest pages — one primary keyword per tool page ─────────────────────
# All 44 built tools (see camera-and-audio-test-tools-specification.xlsx
# "Tool Specification" sheet for name/slug/cluster; individual_websites/
# webcamtest/utilities/tool_buildout/progress.json confirms all 44 are
# verified/live). `keyword` is a hand-picked natural search phrase per tool,
# not a literal lowercasing of the tool name.
WEBCAMTEST_PAGES = [
    # A. Camera Core
    {"name": "Webcam Test",                     "cluster": "A. Camera Core",     "slug": "webcam-test-online",                        "keyword": "webcam test"},
    {"name": "Maximum Resolution Detector",      "cluster": "A. Camera Core",     "slug": "webcam-maximum-resolution-detector",        "keyword": "webcam max resolution"},
    {"name": "FPS and Frame Rate Checker",       "cluster": "A. Camera Core",     "slug": "webcam-fps-frame-rate-checker",             "keyword": "webcam fps test"},
    {"name": "Fullscreen Camera Viewer",         "cluster": "A. Camera Core",     "slug": "webcam-fullscreen-viewer",                  "keyword": "webcam fullscreen"},
    {"name": "Mirror vs Natural View Test",      "cluster": "A. Camera Core",     "slug": "webcam-mirror-vs-natural-view-test",        "keyword": "webcam mirror test"},
    {"name": "Photo Capture",                    "cluster": "A. Camera Core",     "slug": "webcam-photo-capture-online",               "keyword": "webcam photo capture"},
    {"name": "Video Recorder",                   "cluster": "A. Camera Core",     "slug": "webcam-video-recorder-online",              "keyword": "webcam video recorder"},
    {"name": "Camera Information Report",        "cluster": "A. Camera Core",     "slug": "webcam-camera-information-report",          "keyword": "what camera do i have"},
    {"name": "Side-by-Side Camera Comparison",   "cluster": "A. Camera Core",     "slug": "webcam-side-by-side-comparison",            "keyword": "webcam comparison"},
    {"name": "Composition Grid",                 "cluster": "A. Camera Core",     "slug": "webcam-rule-of-thirds-composition-grid",    "keyword": "rule of thirds grid"},
    {"name": "Live Filter Preview",               "cluster": "A. Camera Core",     "slug": "webcam-live-filter-preview",                "keyword": "webcam filters"},
    {"name": "Sharpness and Focus Test",         "cluster": "A. Camera Core",     "slug": "webcam-sharpness-focus-test",               "keyword": "webcam focus test"},
    {"name": "Lighting and Exposure Test",       "cluster": "A. Camera Core",     "slug": "webcam-lighting-exposure-test",             "keyword": "webcam lighting test"},
    {"name": "Low-Light Noise Test",              "cluster": "A. Camera Core",     "slug": "webcam-low-light-noise-test",               "keyword": "webcam low light test"},
    {"name": "Colour Accuracy Test",              "cluster": "A. Camera Core",     "slug": "webcam-color-accuracy-test",                "keyword": "webcam color test"},
    {"name": "Autofocus Test",                    "cluster": "A. Camera Core",     "slug": "webcam-autofocus-test",                     "keyword": "webcam autofocus test"},
    {"name": "Camera Latency Test",               "cluster": "A. Camera Core",     "slug": "webcam-latency-delay-test",                 "keyword": "webcam latency test"},
    {"name": "Camera In-Use Privacy Check",       "cluster": "A. Camera Core",     "slug": "is-my-camera-being-used-check",             "keyword": "is my camera on"},
    # B. Camera Mobile
    {"name": "Mobile Camera Test",                "cluster": "B. Camera Mobile",   "slug": "mobile-camera-test-online",                 "keyword": "mobile camera test"},
    {"name": "Front Camera Test",                 "cluster": "B. Camera Mobile",   "slug": "front-camera-test-online",                  "keyword": "front camera test"},
    {"name": "Rear Camera Test",                  "cluster": "B. Camera Mobile",   "slug": "rear-camera-test-online",                   "keyword": "rear camera test"},
    {"name": "Phone Camera Resolution Checker",   "cluster": "B. Camera Mobile",   "slug": "phone-camera-resolution-checker",           "keyword": "phone camera resolution"},
    {"name": "Flash and Torch Test",               "cluster": "B. Camera Mobile",   "slug": "phone-camera-flash-torch-test",             "keyword": "phone flashlight test"},
    {"name": "Camera Zoom Test",                   "cluster": "B. Camera Mobile",   "slug": "phone-camera-zoom-test",                    "keyword": "phone camera zoom test"},
    {"name": "Camera Orientation Test",            "cluster": "B. Camera Mobile",   "slug": "phone-camera-orientation-test",             "keyword": "phone camera orientation test"},
    {"name": "Used Phone Camera Inspection",       "cluster": "B. Camera Mobile",   "slug": "used-phone-camera-inspection-checklist",    "keyword": "check used phone camera"},
    # C. Camera Reference
    {"name": "Webcam Resolution Standards Reference", "cluster": "C. Camera Reference", "slug": "webcam-resolution-standards-reference",     "keyword": "webcam resolution chart"},
    {"name": "Webcam Specs Comparison",           "cluster": "C. Camera Reference", "slug": "webcam-specs-comparison-database",          "keyword": "webcam specs comparison"},
    {"name": "Camera Test vs Webcam Test Explained", "cluster": "C. Camera Reference", "slug": "camera-test-vs-webcam-test-explained",      "keyword": "camera test vs webcam test"},
    {"name": "Webcam Troubleshooting Guide",       "cluster": "C. Camera Reference", "slug": "webcam-not-working-troubleshooting-guide",  "keyword": "webcam not working"},
    {"name": "Camera Permissions Guide",           "cluster": "C. Camera Reference", "slug": "camera-permissions-guide-windows-mac-android-ios", "keyword": "camera permissions"},
    {"name": "Use Your Phone as a Webcam",         "cluster": "C. Camera Reference", "slug": "use-phone-as-webcam-guide",                 "keyword": "use phone as webcam"},
    # D. Audio
    {"name": "Microphone Test",                    "cluster": "D. Audio",           "slug": "microphone-test-online",                    "keyword": "microphone test"},
    {"name": "Microphone Level Meter",             "cluster": "D. Audio",           "slug": "microphone-input-level-meter",              "keyword": "mic level meter"},
    {"name": "Microphone Record and Playback",     "cluster": "D. Audio",           "slug": "microphone-record-playback-test",           "keyword": "microphone record test"},
    {"name": "Microphone Quality and Spectrum",    "cluster": "D. Audio",           "slug": "microphone-quality-spectrum-analyzer",      "keyword": "microphone spectrum analyzer"},
    {"name": "Speaker Test",                       "cluster": "D. Audio",           "slug": "speaker-test-online",                       "keyword": "speaker test"},
    {"name": "Left and Right Stereo Test",         "cluster": "D. Audio",           "slug": "left-right-stereo-channel-test",            "keyword": "stereo left right test"},
    {"name": "Speaker Polarity and Phase Test",    "cluster": "D. Audio",           "slug": "speaker-polarity-phase-test",               "keyword": "speaker polarity test"},
    {"name": "Frequency Sweep Test",               "cluster": "D. Audio",           "slug": "audio-frequency-sweep-20hz-20khz",          "keyword": "frequency sweep test"},
    {"name": "Subwoofer and Bass Test",            "cluster": "D. Audio",           "slug": "subwoofer-bass-test-online",                "keyword": "subwoofer test"},
    {"name": "Audio Latency Test",                 "cluster": "D. Audio",           "slug": "audio-latency-delay-test",                  "keyword": "audio latency test"},
    {"name": "Online Hearing Test",                "cluster": "D. Audio",           "slug": "online-hearing-frequency-test",             "keyword": "hearing test online"},
    {"name": "Microphone Echo Test",               "cluster": "D. Audio",           "slug": "microphone-echo-test",                      "keyword": "mic echo test"},
]


def competition_label(value) -> str:
    mapping = {0: "UNSPECIFIED", 1: "UNKNOWN", 2: "LOW", 3: "MEDIUM", 4: "HIGH"}
    try:
        return mapping.get(int(value), str(value))
    except Exception:
        return str(value)


def fetch_metrics_batch(client, customer_id, keywords, geo_target_id):
    kp_idea_service = client.get_service("KeywordPlanIdeaService")
    request = client.get_type("GenerateKeywordHistoricalMetricsRequest")

    request.customer_id = customer_id
    request.language = LANGUAGE_EN
    if geo_target_id:
        request.geo_target_constants.append(
            client.get_service("GeoTargetConstantService")
            .geo_target_constant_path(geo_target_id)
        )
    request.keyword_plan_network = (
        client.enums.KeywordPlanNetworkEnum.GOOGLE_SEARCH
    )
    request.keywords.extend(keywords)

    response = kp_idea_service.generate_keyword_historical_metrics(request=request)

    results = {}
    for result in response.results:
        kw = result.text.lower()
        m = result.keyword_metrics
        results[kw] = {
            "avg_monthly_searches": m.avg_monthly_searches,
            "competition":          competition_label(m.competition),
            "competition_index":    m.competition_index,
            "low_top_of_page_bid":  round(m.low_top_of_page_bid_micros / 1_000_000, 2)
                                    if m.low_top_of_page_bid_micros else None,
            "high_top_of_page_bid": round(m.high_top_of_page_bid_micros / 1_000_000, 2)
                                    if m.high_top_of_page_bid_micros else None,
        }
    return results


def fetch_all_metrics(client, customer_id, pages, geo_target_id):
    keywords_list = [p["keyword"] for p in pages]
    log.info(f"Fetching metrics for {len(keywords_list)} keywords…")

    for attempt in range(1, RETRY_LIMIT + 1):
        try:
            metrics_map = fetch_metrics_batch(client, customer_id, keywords_list, geo_target_id)
            break
        except Exception as e:
            if attempt < RETRY_LIMIT:
                log.warning(f"  Attempt {attempt} failed: {e} — retrying in {RETRY_DELAY}s…")
                time.sleep(RETRY_DELAY)
            else:
                log.error(f"  Failed after {RETRY_LIMIT} attempts: {e}")
                metrics_map = {}

    all_results = []
    for page in pages:
        m = metrics_map.get(page["keyword"].lower(), {})
        all_results.append({
            **page,
            "avg_monthly_searches": m.get("avg_monthly_searches"),
            "competition":          m.get("competition"),
            "competition_index":    m.get("competition_index"),
            "low_top_of_page_bid":  m.get("low_top_of_page_bid"),
            "high_top_of_page_bid": m.get("high_top_of_page_bid"),
        })
    return all_results


XLSX_FIELDS = [
    "name", "cluster", "slug", "keyword",
    "avg_monthly_searches", "competition", "competition_index",
    "low_top_of_page_bid", "high_top_of_page_bid",
]


def save_xlsx(rows, path):
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "WebcamTest Search Volumes"
    ws.append(XLSX_FIELDS)
    for row in rows:
        ws.append([row.get(f) for f in XLSX_FIELDS])
    wb.save(path)
    log.info(f"Saved {len(rows)} rows → {path}")


def print_summary(rows):
    has_data = [r for r in rows if r.get("avg_monthly_searches") is not None]
    sorted_rows = sorted(has_data, key=lambda x: x["avg_monthly_searches"], reverse=True)

    print("\n" + "=" * 80)
    print("  WEBCAMTEST PAGES — SEARCH VOLUMES")
    print("=" * 80)
    print(f"  {'Page':<30} {'Keyword':<35} {'Volume':>8}  {'KD'}")
    print("-" * 80)
    for r in sorted_rows:
        print(f"  {r['name'][:30]:<30} {r['keyword'][:35]:<35} {r['avg_monthly_searches']:>8,}  {r['competition']}")
    print("=" * 80)

    no_data = [r for r in rows if r.get("avg_monthly_searches") is None]
    if no_data:
        print(f"\n  {len(no_data)} keywords returned no volume data (<10 searches/month)")
        for r in no_data:
            print(f"    - {r['keyword']}")
    print()


def parse_args():
    p = argparse.ArgumentParser(description="Fetch Google Ads search volumes for WebcamTest pages")
    p.add_argument("--customer-id", default=None,
                   help="Google Ads customer ID (digits only). "
                        "Can also be set via GOOGLE_ADS_CUSTOMER_ID env var.")
    p.add_argument("--geo", default=None,
                   help="Geo target ID (e.g. 2840=US, 2356=India). Omit for global.")
    p.add_argument("--dry-run", action="store_true",
                   help="Print keywords only, skip API call")
    p.add_argument("--yaml", default=str(YAML_PATH),
                   help="Path to google-ads.yaml credentials file")
    return p.parse_args()


def main():
    args = parse_args()

    customer_id = (
        args.customer_id
        or os.environ.get("GOOGLE_ADS_CUSTOMER_ID", "")
    ).replace("-", "").strip()

    pages = WEBCAMTEST_PAGES
    log.info(f"WebcamTest project: {len(pages)} keywords across {len(pages)} pages")

    if args.dry_run:
        print(f"\nDRY RUN — {len(pages)} keywords to be fetched:\n")
        for p in pages:
            print(f"  [{p['name']:<30}]  {p['keyword']}")
        return

    if not customer_id:
        log.error(
            "No customer ID provided. Pass --customer-id XXXXXXXXXX "
            "or set GOOGLE_ADS_CUSTOMER_ID environment variable."
        )
        sys.exit(1)

    try:
        from google.ads.googleads.client import GoogleAdsClient
    except ImportError:
        log.error("google-ads not installed. Run: pip install google-ads openpyxl")
        sys.exit(1)

    log.info(f"Connecting to Google Ads API (customer: {customer_id}, geo: {GEO_TARGETS.get(args.geo, args.geo) if args.geo else 'Global'})…")
    client = GoogleAdsClient.load_from_storage(args.yaml)

    start = time.time()
    results = fetch_all_metrics(client, customer_id, pages, args.geo)
    elapsed = time.time() - start
    log.info(f"Completed in {elapsed:.1f}s")

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    geo_label = GEO_TARGETS.get(args.geo, args.geo).lower().replace(" ", "_") if args.geo else "global"
    out_path = OUTPUT_DIR / f"webcamtest_search_volumes_{geo_label}_{timestamp}.xlsx"
    save_xlsx(results, out_path)
    print_summary(results)


if __name__ == "__main__":
    main()
