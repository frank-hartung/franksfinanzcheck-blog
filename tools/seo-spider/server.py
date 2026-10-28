#!/usr/bin/env python3
"""Local-only web UI for the FF SEO Spider. Python standard library only."""
from __future__ import annotations
import argparse, json, pathlib, threading
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlparse
from crawler import crawl, csv_text, links_csv_text

HERE = pathlib.Path(__file__).resolve().parent
PAGE_FIELDS = set(("url status title title_count title_chars description description_count description_chars description_px h1 h1_count h2_count canonical indexability robots lang viewport doctype og_title og_description og_image twitter_card hreflang_count schema_types schema_count schema_errors images images_missing_alt images_empty_alt words content_hash sitemap content_type bytes truncated depth depth_origin inlinks outlinks external_links empty_anchor_links broken_internal_links broken_external_links broken_anchor_links elapsed_ms server cache_control last_modified etag content_encoding orphan issues final_url").split())
STATE = {"running": False, "done": False, "pages": [], "links": [], "progress": 0, "limit": 0, "current": "", "error": "", "summary": {}}
LOCK = threading.Lock()
STOP = threading.Event()


def run_crawl(url, limit, delay, depth, sitemap, seed_urls, follow_nofollow, check_external):
    def progress(count, maximum, current):
        with LOCK: STATE.update(progress=count, limit=maximum, current=current)
    try:
        result = crawl(url, limit, delay, stop_event=STOP, progress=progress, max_depth=depth, sitemap_url=sitemap or None, seed_urls=seed_urls, follow_nofollow=follow_nofollow, check_external=check_external)
        pages = result["pages"]
        result["generated_at"] = datetime.now(timezone.utc).isoformat()
        counts = {
            "pages": len(pages), "errors": sum(isinstance(p["status"], int) and p["status"] >= 400 or p["status"] == "ERROR" for p in pages),
            "missing_title": sum("Missing title" in p["issues"] for p in pages),
            "missing_description": sum("Missing meta description" in p["issues"] for p in pages),
            "missing_h1": sum("Missing H1" in p["issues"] for p in pages),
            "noindex": sum("Noindex" in p["issues"] or "Nofollow directive" in p["issues"] for p in pages),
            "metadata_issues": sum(any(token in p["issues"] for token in ("Missing title", "Missing meta description", "Missing H1", "Long title", "Long meta description", "Short meta description", "Wide meta description")) for p in pages),
            "broken_links": sum(p.get("broken_internal_links", 0) for p in pages),
            "orphans": sum(p.get("orphan", False) for p in pages),
            "missing_alt": sum(p.get("images_missing_alt", 0) for p in pages),
            "duplicate_titles": sum("Duplicate title" in p["issues"] for p in pages),
            "duplicate_content": sum("Duplicate content" in p["issues"] for p in pages),
            "external_links": sum(p.get("external_links", 0) for p in pages),
            "broken_external_links": sum(p.get("broken_external_links", 0) for p in pages),
            "internal_links": sum(p.get("outlinks", 0) for p in pages),
            "indexable": sum(p.get("indexability") == "indexable" for p in pages),
        }
        page_payload = [{key: value for key, value in page.items() if key in PAGE_FIELDS} for page in pages]
        with LOCK: STATE.update(pages=page_payload, links=result["links"], summary=counts, generated_at=result["generated_at"] if "generated_at" in result else None, start_url=result["start_url"], robots_checked=result["robots_checked"], sitemaps_found=result["sitemaps_found"], sitemap_urls=len(result["sitemap_urls"]), sitemap_unseen=result["sitemap_unseen_urls"], sitemap_errors=result["sitemap_errors"], timed_out=result["timed_out"], stopped=result["stopped"], scope=result["scope"], max_depth=result["max_depth"], robots_delay=result["robots_delay"], external_checked=result["external_checked"], external_unchecked=result["external_unchecked"], check_external=check_external, limit_reached=result["limit_reached"], depth_skipped=result["depth_skipped"])
    except Exception as exc:
        with LOCK: STATE["error"] = str(exc)
    finally:
        with LOCK: STATE.update(running=False, done=True)


class Handler(BaseHTTPRequestHandler):
    server_version = "FF-SEOSpider/1.0"
    def log_message(self, fmt, *args):
        pass
    def send_bytes(self, data, content_type, status=200):
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(data)))
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("X-Frame-Options", "DENY")
        self.send_header("Referrer-Policy", "no-referrer")
        self.send_header("Content-Security-Policy", "default-src 'self'; connect-src 'self'; img-src 'self' data:; style-src 'self'; script-src 'self'; base-uri 'none'; form-action 'none'; frame-ancestors 'none'")
        self.end_headers()
        self.wfile.write(data)
    def do_GET(self):
        path = urlparse(self.path).path
        if path == "/api/state":
            with LOCK: body = json.dumps(STATE, ensure_ascii=False).encode()
            return self.send_bytes(body, "application/json; charset=utf-8")
        if path == "/api/export.json":
            with LOCK:
                body = json.dumps({"generated_at": STATE.get("generated_at"), "scope": STATE.get("scope"), "summary": STATE["summary"], "pages": STATE["pages"], "links": STATE["links"], "sitemap_errors": STATE.get("sitemap_errors", [])}, ensure_ascii=False, indent=2).encode()
            self.send_response(200); self.send_header("Content-Type", "application/json; charset=utf-8"); self.send_header("Content-Disposition", 'attachment; filename="seo-spider-report.json"'); self.send_header("Content-Length", str(len(body))); self.send_header("Cache-Control", "no-store"); self.end_headers(); return self.wfile.write(body)
        if path in ("/api/export.csv", "/api/export-links.csv"):
            with LOCK:
                text = csv_text(STATE["pages"]) if path == "/api/export.csv" else links_csv_text(STATE["links"])
            body = text.encode("utf-8-sig")
            filename = "seo-spider-pages.csv" if path == "/api/export.csv" else "seo-spider-links.csv"
            self.send_response(200); self.send_header("Content-Type", "text/csv; charset=utf-8"); self.send_header("Content-Disposition", f'attachment; filename="{filename}"'); self.send_header("Content-Length", str(len(body))); self.end_headers(); return self.wfile.write(body)
        file = "index.html" if path == "/" else path.lstrip("/")
        if file not in ("index.html", "app.js", "style.css"):
            return self.send_bytes(b"Not found", "text/plain", 404)
        data = (HERE / file).read_bytes()
        content_type = {
            "index.html": "text/html; charset=utf-8",
            "app.js": "application/javascript; charset=utf-8",
            "style.css": "text/css; charset=utf-8",
        }[file]
        self.send_bytes(data, content_type)
    def do_POST(self):
        origin = self.headers.get("Origin")
        if origin and urlparse(origin).netloc != self.headers.get("Host", ""):
            return self.send_bytes(b'{"error":"Cross-Origin-Anfrage blockiert"}', "application/json", 403)
        path = urlparse(self.path).path
        if path == "/api/stop":
            STOP.set(); return self.send_bytes(b'{"ok":true}', "application/json")
        if path != "/api/start": return self.send_bytes(b'{"error":"Not found"}', "application/json", 404)
        try:
            length = int(self.headers.get("Content-Length", "0"))
            if length > 1_000_000: raise ValueError("Anfrage zu groß (max. 1 MB).")
            data = json.loads(self.rfile.read(length))
            url = str(data.get("url", ""))[:2000]
            limit, delay, depth = int(data.get("limit", 500)), float(data.get("delay", 0.5)), int(data.get("depth", 10))
            sitemap = str(data.get("sitemap", ""))[:2000].strip()
            seed_urls = data.get("seed_urls", [])
            if not isinstance(seed_urls, list) or len(seed_urls) > 5000 or any(not isinstance(item, str) or len(item) > 2000 for item in seed_urls):
                raise ValueError("Seed-Liste ungültig oder größer als 5.000 URLs.")
            follow_nofollow = bool(data.get("follow_nofollow", False))
            check_external = bool(data.get("check_external", False))
            if not 1 <= limit <= 5000 or not 0.2 <= delay <= 10 or not 0 <= depth <= 100:
                raise ValueError("Seitenlimit (1–5000), Tiefe (0–100) oder Abstand (0,2–10 s) ungültig.")
            with LOCK:
                if STATE["running"]:
                    return self.send_bytes(json.dumps({"error": "Ein Crawl läuft bereits."}, ensure_ascii=False).encode(), "application/json; charset=utf-8", 409)
                STATE.update(running=True, done=False, pages=[], links=[], progress=0, limit=limit, current="", error="", summary={}, start_url=url)
            STOP.clear()
            threading.Thread(target=run_crawl, args=(url, limit, delay, depth, sitemap, seed_urls, follow_nofollow, check_external), daemon=True).start()
            return self.send_bytes(b'{"ok":true}', "application/json", 202)
        except (ValueError, TypeError, json.JSONDecodeError) as exc:
            return self.send_bytes(json.dumps({"error": str(exc)}, ensure_ascii=False).encode(), "application/json", 400)


def main():
    parser = argparse.ArgumentParser(description="Starte den lokalen FF SEO Spider.")
    parser.add_argument("--port", type=int, default=8765)
    args = parser.parse_args()
    server = ThreadingHTTPServer(("127.0.0.1", args.port), Handler)
    print(f"FF SEO Spider läuft lokal: http://127.0.0.1:{args.port} (Beenden mit Strg+C)")
    try: server.serve_forever()
    except KeyboardInterrupt: print("\nServer beendet.")
    finally: server.server_close()

if __name__ == "__main__": main()
