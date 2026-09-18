#!/usr/bin/env python3
"""
Orchestrates: run /seo-optimize for every tool in keywords.txt (via the
open-source-on-page-seo-optimizer repo's own scripts/batch_run.py), then
merge every successful result into src/content/<slug>.json via
merge_seo_output.py.

This is intentionally a thin wrapper — batch_run.py's own docstring says
merging its output into your own site's content pipeline "belongs in your
own project's repo", so this repo owns the merge step while the
seo-optimizer repo keeps owning the actual scrape/write/audit loop. Do not
duplicate that logic here — shell out to it instead.

Usage:
    # regenerate keywords.txt if src/content/ changed since the last run
    python3 utilities/seo_batch/build_keywords_list.py

    # sanity-check on one tool first
    python3 utilities/seo_batch/run_batch.py \
        --seo-optimizer-dir /path/to/open-source-on-page-seo-optimizer \
        --dangerously-skip-permissions --limit 1

    # then the rest
    python3 utilities/seo_batch/run_batch.py \
        --seo-optimizer-dir /path/to/open-source-on-page-seo-optimizer \
        --dangerously-skip-permissions

Costs real Claude Code usage per tool — one full /seo-optimize skill run
each (scrape + write + audit). See open-source-on-page-seo-optimizer's own
scripts/batch_run.py docstring for why --dangerously-skip-permissions is
required for a real (non-dry-run) headless batch, and for --timeout/--model/
--allowed-tools if you need those — this wrapper only passes through the
handful of flags below; anything else, call batch_run.py directly and then
this script with --merge-only.
"""
import argparse
import json
import os
import subprocess
import sys

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
KEYWORDS_PATH = os.path.join(REPO_ROOT, "utilities", "seo_batch", "keywords.txt")
MERGE_SCRIPT = os.path.join(REPO_ROOT, "utilities", "seo_batch", "merge_seo_output.py")


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--seo-optimizer-dir", required=True, help="path to the open-source-on-page-seo-optimizer repo")
    parser.add_argument("--dry-run", action="store_true", help="passed through to batch_run.py; also skips the merge step")
    parser.add_argument("--limit", type=int, default=None, help="passed through to batch_run.py")
    parser.add_argument("--force", action="store_true", help="passed through to batch_run.py (re-run keywords already ok/audit_fail)")
    parser.add_argument("--dangerously-skip-permissions", action="store_true", help="passed through to batch_run.py (required for a real, non-dry-run batch)")
    parser.add_argument("--merge-only", action="store_true", help="skip batch_run.py entirely, just merge whatever output/ + run_log.json already has")
    args = parser.parse_args()

    batch_run_py = os.path.join(args.seo_optimizer_dir, "scripts", "batch_run.py")
    if not os.path.exists(batch_run_py):
        sys.exit("error: %s not found — is --seo-optimizer-dir correct?" % batch_run_py)

    # Prefer that repo's own venv (its README has you `python3 -m venv
    # bots_venv`) over whatever interpreter is running this wrapper —
    # batch_run.py needs `requests` etc. installed there, not here.
    venv_python = os.path.join(args.seo_optimizer_dir, "bots_venv", "bin", "python3")
    python_bin = venv_python if os.path.exists(venv_python) else sys.executable

    if not args.merge_only:
        cmd = [python_bin, batch_run_py, KEYWORDS_PATH]
        if args.dry_run:
            cmd.append("--dry-run")
        if args.limit is not None:
            cmd += ["--limit", str(args.limit)]
        if args.force:
            cmd.append("--force")
        if args.dangerously_skip_permissions:
            cmd.append("--dangerously-skip-permissions")
        print("+ %s" % " ".join(cmd))
        result = subprocess.run(cmd)
        if result.returncode != 0:
            sys.exit("batch_run.py exited %d — not merging" % result.returncode)

    if args.dry_run:
        return

    run_log_path = os.path.join(args.seo_optimizer_dir, "output", "_batch", "run_log.json")
    if not os.path.exists(run_log_path):
        sys.exit("error: %s not found" % run_log_path)
    with open(run_log_path) as f:
        run_log = json.load(f)

    merged, skipped = [], []
    for slug, entry in sorted(run_log.items()):
        if entry.get("status") != "ok":
            skipped.append((slug, entry.get("status")))
            continue
        seo_output_dir = os.path.join(args.seo_optimizer_dir, "output", slug)
        content_path = os.path.join(REPO_ROOT, "src", "content", "%s.json" % slug)
        if not os.path.exists(content_path):
            skipped.append((slug, "no matching src/content/%s.json" % slug))
            continue
        subprocess.run([sys.executable, MERGE_SCRIPT, slug, "--seo-output", seo_output_dir], check=True)
        merged.append(slug)

    print("\nMerged %d tool(s): %s" % (len(merged), ", ".join(merged) or "(none)"))
    if skipped:
        print("Skipped %d: %s" % (len(skipped), skipped))
    if merged:
        print(
            "\nNow run: python3 src/build_data.py && python3 src/generate.py && "
            "python3 utilities/silo_linking/generate_silo_rotation.py"
        )


if __name__ == "__main__":
    main()
