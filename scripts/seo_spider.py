#!/usr/bin/env python3
"""Headless live crawl for the local SEO Spider and scheduled reports."""
from __future__ import annotations
import argparse, json, sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools" / "seo-spider"))
from crawler import crawl, csv_text, links_csv_text  # noqa: E402
from compare import compare_pages  # noqa: E402


def main():
    parser = argparse.ArgumentParser(description="Respectful same-domain technical SEO crawl (no third-party dependencies).")
    parser.add_argument("--url", default="https://franksfinanzcheck.de/", help="Public start URL (default: blog live site)")
    parser.add_argument("--max-pages", type=int, default=500, help="Page limit (1–5000; default 500)")
    parser.add_argument("--delay", type=float, default=0.5, help="Minimum seconds between page requests (default 0.5)")
    parser.add_argument("--timeout", type=int, default=12, help="Per-request timeout in seconds")
    parser.add_argument("--time-limit", type=int, default=900, help="Maximum total crawl time in seconds (default 900)")
    parser.add_argument("--depth", type=int, default=10, help="Maximum internal-link depth (default 10)")
    parser.add_argument("--sitemap", help="Optional sitemap URL; robots.txt sitemaps are detected automatically")
    parser.add_argument("--seed-file", type=Path, help="Optional newline-separated URL list to crawl")
    parser.add_argument("--follow-nofollow", action="store_true", help="Also crawl URLs linked with rel=nofollow")
    parser.add_argument("--check-external", action="store_true", help="Check up to 100 unique external links with HEAD requests (opt-in)")
    parser.add_argument("--json", dest="json_path", type=Path, help="Write the complete report to a JSON file")
    parser.add_argument("--csv", dest="csv_path", type=Path, help="Write page inventory to a CSV file")
    parser.add_argument("--links-csv", type=Path, help="Write internal and external link graph to a CSV file")
    parser.add_argument("--compare", type=Path, help="Compare this run with a previous SEO Spider JSON export")
    parser.add_argument("--diff-json", type=Path, help="Write a machine-readable comparison report")
    parser.add_argument("--fail-on-errors", action="store_true", help="Exit 1 if an HTTP/connection error is found")
    args = parser.parse_args()
    try:
        if args.diff_json and not args.compare:
            raise ValueError("--diff-json benötigt zusätzlich --compare.")
        if args.timeout < 1 or args.time_limit < 1:
            raise ValueError("Timeouts müssen mindestens eine Sekunde betragen.")
        seeds = args.seed_file.read_text(encoding="utf-8").splitlines() if args.seed_file else []
        seeds = [line.strip() for line in seeds if line.strip() and not line.lstrip().startswith("#")]
        if len(seeds) > 5000:
            raise ValueError("Seed-Liste ist auf 5.000 URLs begrenzt.")
        result = crawl(args.url, args.max_pages, args.delay, args.timeout, max_seconds=args.time_limit,
                       max_depth=args.depth, seed_urls=seeds, sitemap_url=args.sitemap, follow_nofollow=args.follow_nofollow, check_external=args.check_external)
        if args.compare:
            baseline = json.loads(args.compare.read_text(encoding="utf-8"))
            if not isinstance(baseline, dict) or not isinstance(baseline.get("pages"), list):
                raise ValueError("Vergleichsdatei enthält kein gültiges pages-Array.")
            result["comparison"] = compare_pages(result["pages"], baseline["pages"])
    except (ValueError, OSError) as exc:
        print(f"SEO Spider: {exc}", file=sys.stderr)
        return 2
    result["generated_at"] = datetime.now(timezone.utc).isoformat()
    pages = result["pages"]
    errors = [p for p in pages if p["status"] == "ERROR" or (isinstance(p["status"], int) and p["status"] >= 400)]
    findings = sum(bool(p["issues"]) for p in pages)
    print(f"SEO Spider: {len(pages)} URLs geprüft · {findings} URLs mit Befunden · {len(errors)} HTTP-/Verbindungsfehler")
    print(f"robots.txt: {'gelesen' if result['robots_checked'] else 'nicht verfügbar'} · Sitemaps: {result['sitemaps_found']} · Sitemap-URLs nicht gecrawlt: {result['sitemap_unseen_urls']}")
    print(f"Interne Links: {sum(page['outlinks'] for page in pages)} · externe Links: {sum(page['external_links'] for page in pages)} (geprüft: {result['external_checked']}, offen: {result['external_unchecked']})")
    if result.get("comparison"):
        delta = result["comparison"]["summary"]
        print(f"Vergleich: +{delta['added']} neu · -{delta['removed']} entfernt · {delta['changed']} geändert · {delta['unchanged']} unverändert")
    if result["limit_reached"]: print(f"URL-Limit ({result['max_pages']}) erreicht; weitere URLs stehen ggf. noch in der Warteschlange.")
    if result["depth_skipped"]: print(f"Klicktiefe begrenzt: {result['depth_skipped']} URLs jenseits Tiefe {result['max_depth']} ausgelassen.")
    if result["timed_out"]: print("Zeitlimit erreicht; der Crawl-Bericht ist unvollständig.")
    if result["stopped"]: print("Crawl wurde manuell gestoppt; der Bericht ist unvollständig.")
    for row in pages:
        if row["issues"]:
            print(f"{row['status']}  {row['url']}  — {row['issues']}")
    if args.json_path:
        args.json_path.parent.mkdir(parents=True, exist_ok=True)
        args.json_path.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print(f"JSON: {args.json_path}")
    if args.csv_path:
        args.csv_path.parent.mkdir(parents=True, exist_ok=True)
        args.csv_path.write_text(csv_text(pages), encoding="utf-8-sig", newline="")
        print(f"CSV: {args.csv_path}")
    if args.links_csv:
        args.links_csv.parent.mkdir(parents=True, exist_ok=True)
        args.links_csv.write_text(links_csv_text(result["links"]), encoding="utf-8-sig", newline="")
        print(f"Link-CSV: {args.links_csv}")
    if args.diff_json:
        if not result.get("comparison"):
            print("--diff-json benötigt zusätzlich --compare.", file=sys.stderr)
            return 2
        args.diff_json.parent.mkdir(parents=True, exist_ok=True)
        args.diff_json.write_text(json.dumps(result["comparison"], ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print(f"Differenzbericht: {args.diff_json}")
    return 1 if args.fail_on_errors and (errors or result["timed_out"]) else 0

if __name__ == "__main__":
    raise SystemExit(main())
