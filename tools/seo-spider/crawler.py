"""Respectful, dependency-free technical SEO crawler for public websites."""
from __future__ import annotations

import csv
import hashlib
import ipaddress
import json
import re
import socket
import time
import urllib.error
import urllib.parse
import urllib.request
from collections import Counter, deque
from html.parser import HTMLParser
from urllib.robotparser import RobotFileParser
from pathlib import Path
import sys

_REPO_ROOT = Path(__file__).resolve().parents[2]
if str(_REPO_ROOT / "scripts") not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT / "scripts"))
import safe_xml as ET  # noqa: E402
import serp_limits

USER_AGENT = "FF-SEO-Spider/2.0 (+https://franksfinanzcheck.de/; local SEO audit)"
MAX_BYTES = 2_000_000
MAX_SITEMAPS = 12
TRACKING_PARAMS = {"gclid", "fbclid", "msclkid", "dclid", "gbraid", "wbraid"}


class PageParser(HTMLParser):
    """Extract indexable-page signals from server HTML without executing JS."""
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.title_parts: list[str] = []
        self.meta: dict[str, list[str]] = {}
        self.canonicals: list[str] = []
        self.h1: list[list[str]] = []
        self.h2: list[list[str]] = []
        self.headings: list[int] = []
        self.links: list[dict] = []
        self.images: list[dict] = []
        self.ids: set[str] = set()
        self.hreflang: list[dict] = []
        self.schema: list[object] = []
        self.schema_errors = 0
        self.text_parts: list[str] = []
        self.in_title = False
        self.in_head = False
        self.title_count = 0
        self.current_heading: list[str] | None = None
        self.current_anchor: dict | None = None
        self.current_image: dict | None = None
        self.in_schema = False
        self.schema_parts: list[str] = []
        self.skip_text_depth = 0
        self.svg_depth = 0
        self.lang = ""
        self.has_viewport = False
        self.refresh_redirect = False
        self.doctype = False

    def handle_decl(self, decl):
        if decl.lower().startswith("doctype html"):
            self.doctype = True

    def handle_starttag(self, tag, attrs):
        a = {k.lower(): v or "" for k, v in attrs}
        if a.get("id"):
            self.ids.add(a["id"])
        if tag == "html":
            self.lang = a.get("lang", "").strip()
        if tag == "svg":
            self.svg_depth += 1
        if tag == "head":
            self.in_head = True
        if tag == "title" and self.in_head and self.svg_depth == 0:
            self.in_title = True
            self.title_count += 1
        if tag in ("script", "style", "noscript", "template"):
            self.skip_text_depth += 1
        if tag == "meta":
            name = (a.get("name") or a.get("property") or "").strip().lower()
            if name:
                self.meta.setdefault(name, []).append(a.get("content", "").strip())
            if name == "viewport":
                self.has_viewport = True
            if (a.get("http-equiv") or "").strip().lower() == "refresh":
                self.refresh_redirect = True
        if tag == "link":
            rels = set(a.get("rel", "").lower().split())
            if "canonical" in rels:
                self.canonicals.append(a.get("href", "").strip())
            if "alternate" in rels and a.get("hreflang") and a.get("href"):
                self.hreflang.append({"lang": a["hreflang"].strip(), "href": a["href"].strip()})
        if tag == "a" and a.get("href"):
            self.current_anchor = {"href": a["href"].strip(), "rel": a.get("rel", "").strip().lower(), "text": [], "image_alt": []}
        if tag == "area" and a.get("href"):
            self.links.append({"href": a["href"].strip(), "rel": a.get("rel", "").strip().lower(), "anchor": a.get("alt", "").strip()})
        if tag == "img":
            image = {"src": a.get("src", "").strip(), "alt": a.get("alt"), "width": a.get("width", ""), "height": a.get("height", "")}
            self.images.append(image)
            if self.current_anchor is not None and image.get("alt"):
                self.current_anchor["image_alt"].append(image["alt"].strip())
        if tag in ("h1", "h2", "h3", "h4", "h5", "h6"):
            level = int(tag[1])
            self.headings.append(level)
            self.current_heading = []
            (self.h1 if level == 1 else self.h2 if level == 2 else []).append(self.current_heading)
        if tag == "script" and a.get("type", "").lower() == "application/ld+json":
            self.in_schema = True
            self.schema_parts = []

    def handle_endtag(self, tag):
        if tag == "title":
            self.in_title = False
        if tag == "head":
            self.in_head = False
        if tag in ("script", "style", "noscript", "template") and self.skip_text_depth:
            self.skip_text_depth -= 1
        if tag == "a" and self.current_anchor is not None:
            anchor = self.current_anchor
            anchor_text = " ".join(" ".join(anchor["text"]).split())
            if not anchor_text and anchor["image_alt"]:
                anchor_text = " ".join(anchor["image_alt"])
            self.links.append({"href": anchor["href"], "rel": anchor["rel"], "anchor": anchor_text})
            self.current_anchor = None
        if tag in ("h1", "h2", "h3", "h4", "h5", "h6"):
            self.current_heading = None
        if tag == "svg" and self.svg_depth:
            self.svg_depth -= 1
        if tag == "script" and self.in_schema:
            try:
                self.schema.append(json.loads("".join(self.schema_parts)))
            except (ValueError, TypeError):
                self.schema_errors += 1
            self.in_schema = False

    def handle_data(self, data):
        if self.in_title:
            self.title_parts.append(data)
        if self.in_schema:
            self.schema_parts.append(data)
        if self.current_heading is not None:
            self.current_heading.append(data)
        if self.current_anchor is not None and not self.svg_depth:
            self.current_anchor["text"].append(data)
        if not self.skip_text_depth:
            self.text_parts.append(data)

    @staticmethod
    def _join(parts):
        return " ".join(" ".join(parts).split())

    @property
    def title(self):
        return self._join(self.title_parts)

    @property
    def description(self):
        return self._join(self.meta.get("description", [])[-1:])

    @property
    def robots(self):
        return ", ".join(self.meta.get("robots", []) + self.meta.get("googlebot", []))

    @property
    def visible_text(self):
        return re.sub(r"\s+", " ", " ".join(self.text_parts)).strip()

    def result(self):
        text = self.visible_text
        word_count = len(re.findall(r"\b[\w’'-]+\b", text, flags=re.UNICODE))
        schema_types = sorted(_schema_types(self.schema))
        headings = [self._join(parts) for parts in self.h1 + self.h2]
        return {
            "title": self.title,
            "title_count": self.title_count,
            "description_count": len(self.meta.get("description", [])),
            "title_chars": len(self.title),
            "description": self.description,
            "description_chars": len(self.description),
            "description_px": serp_limits.breite_px(self.description),
            "h1": [self._join(parts) for parts in self.h1 if self._join(parts)],
            "h2": [self._join(parts) for parts in self.h2 if self._join(parts)],
            "heading_levels": self.headings,
            "canonical": self.canonicals,
            "robots": self.robots,
            "lang": self.lang,
            "viewport": self.has_viewport,
            "doctype": self.doctype,
            "meta_og_title": self._join(self.meta.get("og:title", [])),
            "meta_og_description": self._join(self.meta.get("og:description", [])),
            "meta_og_image": self._join(self.meta.get("og:image", [])),
            "twitter_card": self._join(self.meta.get("twitter:card", [])),
            "hreflang": self.hreflang,
            "links": self.links,
            "images_count": len(self.images),
            "images_missing_alt": sum(1 for image in self.images if image.get("alt") is None),
            "images_empty_alt": sum(1 for image in self.images if image.get("alt") == ""),
            "images": self.images,
            "ids": self.ids,
            "words": word_count,
            "content_hash": hashlib.sha256(text.casefold().encode("utf-8")).hexdigest() if text else "",
            "schema_types": schema_types,
            "schema_errors": self.schema_errors,
            "schema_count": len(self.schema),
            "refresh_redirect": self.refresh_redirect,
        }


def _schema_types(values):
    found = set()
    for value in values:
        if isinstance(value, dict):
            types = value.get("@type", [])
            if isinstance(types, str): found.add(types)
            elif isinstance(types, list): found.update(t for t in types if isinstance(t, str))
            found.update(_schema_types(list(value.values())))
        elif isinstance(value, list):
            found.update(_schema_types(value))
    return found


def normalize_url(url):
    try:
        parts = urllib.parse.urlsplit(url)
        if parts.scheme.lower() not in ("http", "https") or not parts.hostname or parts.username or parts.password:
            return None
        host = parts.hostname.lower().rstrip(".")
        netloc = f"[{host}]" if ":" in host else host
        port = parts.port
        if port and not ((parts.scheme.lower() == "http" and port == 80) or (parts.scheme.lower() == "https" and port == 443)):
            netloc += f":{port}"
        path = urllib.parse.quote(urllib.parse.unquote(parts.path or "/"), safe="/%:@!$&'()*+,;=-._~")
        query = urllib.parse.parse_qsl(parts.query, keep_blank_values=True)
        query = [(k, v) for k, v in query if k.lower() not in TRACKING_PARAMS and not k.lower().startswith("utm_")]
        return urllib.parse.urlunsplit((parts.scheme.lower(), netloc, path, urllib.parse.urlencode(query, doseq=True), ""))
    except (ValueError, UnicodeError):
        return None


def public_host(url):
    """Only allow destinations resolving entirely to globally routable IPs."""
    host = urllib.parse.urlsplit(url).hostname
    try:
        addresses = [ipaddress.ip_address(host)]
    except ValueError:
        try:
            addresses = [ipaddress.ip_address(item[4][0]) for item in socket.getaddrinfo(host, None, type=socket.SOCK_STREAM)]
        except (OSError, ValueError):
            return False
    return bool(addresses) and all(ip.is_global for ip in addresses)


class SafeRedirect(urllib.request.HTTPRedirectHandler):
    def __init__(self, allowed_host):
        super().__init__()
        self.allowed_host = allowed_host

    def redirect_request(self, req, fp, code, msg, headers, newurl):
        normalized = normalize_url(urllib.parse.urljoin(req.full_url, newurl))
        if not normalized or urllib.parse.urlsplit(normalized).hostname != self.allowed_host or not public_host(normalized):
            raise urllib.error.URLError("Weiterleitung außerhalb der öffentlichen Ziel-Domain blockiert")
        return super().redirect_request(req, fp, code, msg, headers, normalized)


class PublicRedirect(urllib.request.HTTPRedirectHandler):
    """External-link checker may follow redirects only to public addresses."""
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        normalized = normalize_url(urllib.parse.urljoin(req.full_url, newurl))
        if not normalized or not public_host(normalized):
            raise urllib.error.URLError("Weiterleitung zu nicht öffentlicher Adresse blockiert")
        return super().redirect_request(req, fp, code, msg, headers, normalized)


def build_opener(host):
    return urllib.request.build_opener(SafeRedirect(host))


def fetch(opener, url, timeout=12):
    if not public_host(url):
        raise urllib.error.URLError("Ziel ist nicht öffentlich erreichbar oder DNS-Auflösung fehlgeschlagen")
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT, "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.5"})
    started = time.monotonic()
    try:
        response = opener.open(request, timeout=timeout)
    except urllib.error.HTTPError as exc:
        response = exc
    with response:
        body = response.read(MAX_BYTES + 1)
        truncated = len(body) > MAX_BYTES
        body = body[:MAX_BYTES]
        content_type = response.headers.get_content_type()
        charset = response.headers.get_content_charset() or "utf-8"
        try:
            text = body.decode(charset, errors="replace")
        except LookupError:
            text = body.decode("utf-8", errors="replace")
        return {
            "status": response.status,
            "final_url": response.geturl(),
            "content_type": content_type,
            "x_robots": response.headers.get("X-Robots-Tag", ""),
            "headers": {name.lower(): value for name, value in response.headers.items()},
            "body": text,
            "bytes": len(body),
            "truncated": truncated,
            "elapsed_ms": round((time.monotonic() - started) * 1000),
        }


def _parse_sitemap_document(text, base_host):
    """Return same-host locs and whether this XML document is an index."""
    try:
        root = ET.fromstring(text)
        is_index = root.tag.rsplit("}", 1)[-1].lower() == "sitemapindex"
        urls = []
        for node in root.iter():
            if node.tag.rsplit("}", 1)[-1].lower() == "loc" and node.text:
                url = normalize_url(node.text.strip())
                if url and urllib.parse.urlsplit(url).hostname == base_host:
                    urls.append(url)
        return urls, is_index
    except ET.ParseError:
        return [], False


def parse_sitemap(text, base_host):
    """Return URL locs on the target host; accepts sitemap and index XML."""
    return _parse_sitemap_document(text, base_host)[0]


def _sitemap_inventory(opener, sitemap_urls, host, timeout, max_seconds, started, delay, stop_event=None):
    pending = deque(sitemap_urls)
    visited, page_urls, sitemap_errors = set(), set(), []
    last_request = started
    while pending and len(visited) < MAX_SITEMAPS and time.monotonic() - started < max_seconds and not (stop_event and stop_event.is_set()):
        sitemap_url = normalize_url(pending.popleft())
        if not sitemap_url or sitemap_url in visited:
            continue
        if urllib.parse.urlsplit(sitemap_url).hostname != host:
            continue
        visited.add(sitemap_url)
        if last_request:
            wait = delay - (time.monotonic() - last_request)
            if wait > 0:
                if stop_event and stop_event.wait(wait):
                    break
                if not stop_event:
                    time.sleep(wait)
        last_request = time.monotonic()
        try:
            response = fetch(opener, sitemap_url, timeout)
            if response["status"] >= 400:
                sitemap_errors.append({"url": sitemap_url, "status": response["status"]})
                continue
            locs, is_index = _parse_sitemap_document(response["body"], host)
            if is_index:
                pending.extend(loc for loc in locs if len(pending) + len(visited) < MAX_SITEMAPS)
            else:
                page_urls.update(locs)
        except Exception as exc:
            sitemap_errors.append({"url": sitemap_url, "status": "ERROR", "error": " ".join(str(exc).split())[:180]})
    return page_urls, visited, sitemap_errors


def _head_check(url, timeout):
    normalized = normalize_url(url)
    host = urllib.parse.urlsplit(normalized).hostname if normalized else ""
    if not normalized or not public_host(normalized):
        return {"status": "BLOCKED", "final_url": normalized or url, "elapsed_ms": 0}
    opener = urllib.request.build_opener(PublicRedirect())
    started = time.monotonic()
    def open_method(method, extra_headers=None):
        headers = {"User-Agent": USER_AGENT, "Accept": "*/*"}
        headers.update(extra_headers or {})
        request = urllib.request.Request(normalized, method=method, headers=headers)
        try:
            return opener.open(request, timeout=timeout)
        except urllib.error.HTTPError as exc:
            return exc
    try:
        response = open_method("HEAD")
        if response.status in (405, 501):
            response.close()
            response = open_method("GET", {"Range": "bytes=0-0"})
        with response:
            return {"status": response.status, "final_url": normalize_url(response.geturl()) or normalized,
                    "elapsed_ms": round((time.monotonic()-started)*1000)}
    except Exception:
        return {"status": "ERROR", "final_url": normalized, "elapsed_ms": round((time.monotonic()-started)*1000)}


def crawl(start_url, max_pages=500, delay=0.5, timeout=12, stop_event=None, progress=None,
          max_seconds=900, max_depth=10, seed_urls=None, sitemap_url=None, follow_nofollow=False,
          check_external=False, max_external_urls=100):
    started = time.monotonic()
    start = normalize_url(start_url.strip())
    if not start:
        raise ValueError("Bitte eine gültige http://- oder https://-URL angeben.")
    host = urllib.parse.urlsplit(start).hostname.lower().rstrip(".")
    if not public_host(start):
        raise ValueError("Nur öffentliche Websites sind erlaubt; lokale/private Ziele werden blockiert.")
    max_pages = max(1, min(int(max_pages), 5000))
    max_depth = max(0, min(int(max_depth), 100))
    delay = max(0.2, min(float(delay), 10.0))
    timeout = max(1, min(float(timeout), 60.0))
    max_seconds = max(1, float(max_seconds))
    opener = build_opener(host)
    robots = RobotFileParser()
    start_parts = urllib.parse.urlsplit(start)
    robots_url = urllib.parse.urlunsplit((start_parts.scheme, start_parts.netloc, "/robots.txt", "", ""))
    robots_available, robots_delay = False, None
    declared_sitemaps = [sitemap_url] if sitemap_url else []
    try:
        rob = fetch(opener, robots_url, timeout)
        if rob["status"] < 400:
            robots.parse(rob["body"].splitlines())
            robots_available = True
            robots_delay = robots.crawl_delay(USER_AGENT)
            declared_sitemaps.extend(line.split(":", 1)[1].strip() for line in rob["body"].splitlines() if line.lower().startswith("sitemap:"))
        else:
            robots.parse([])
    except Exception:
        robots.parse([])
    sitemap_urls, sitemap_files, sitemap_errors = _sitemap_inventory(opener, declared_sitemaps, host, timeout, max_seconds, started, max(delay, float(robots_delay or 0)), stop_event=stop_event)

    seed_pool = deque()
    seed_seen = {start}
    for candidate in seed_urls or []:
        normalized = normalize_url(urllib.parse.urljoin(start, str(candidate)))
        if normalized and urllib.parse.urlsplit(normalized).hostname == host and normalized not in seed_seen:
            seed_pool.append((normalized, "URL-Liste"))
            seed_seen.add(normalized)
    for normalized in sorted(sitemap_urls):
        if normalized not in seed_seen:
            seed_pool.append((normalized, "Sitemap"))
            seed_seen.add(normalized)
    queue = deque([(start, 0, "Start-URL")])
    seen, rows, discovered_links = set(), [], {}
    depth_skipped = 0
    effective_delay = max(delay, float(robots_delay or 0))
    last_request = time.monotonic() if robots_available or sitemap_files else 0.0
    while (queue or seed_pool) and len(rows) < max_pages and time.monotonic() - started < max_seconds and not (stop_event and stop_event.is_set()):
        if not queue:
            while seed_pool and seed_pool[0][0] in seen:
                seed_pool.popleft()
            if seed_pool:
                seed_url, seed_origin = seed_pool.popleft()
                queue.append((seed_url, 0, seed_origin))
        if not queue:
            break
        url, depth, depth_origin = queue.popleft()
        if url in seen:
            continue
        seen.add(url)
        if urllib.parse.urlsplit(url).hostname != host:
            continue
        if not robots.can_fetch(USER_AGENT, url):
            rows.append(_blocked_row(url, depth, depth_origin))
            if progress: progress(len(rows), max_pages, url)
            continue
        if depth > max_depth:
            depth_skipped += 1
            continue
        if last_request:
            wait = effective_delay - (time.monotonic() - last_request)
            if wait > 0:
                if stop_event and stop_event.wait(wait):
                    break
                if not stop_event:
                    time.sleep(wait)
        last_request = time.monotonic()
        try:
            response = fetch(opener, url, timeout)
            final_url = normalize_url(response["final_url"]) or url
            parser = PageParser()
            is_html = response["content_type"] in ("text/html", "application/xhtml+xml")
            if is_html:
                parser.feed(response["body"])
                parser.close()
                data = parser.result()
            else:
                data = _empty_page_data()
            if response.get("x_robots"):
                data["robots"] = ", ".join(filter(None, (data["robots"], response["x_robots"])))
            target = final_url if urllib.parse.urlsplit(final_url).hostname == host else url
            internal, external = [], []
            for link_data in data["links"]:
                resolved = urllib.parse.urljoin(target, link_data["href"])
                dest = normalize_url(resolved)
                if not dest:
                    continue
                target_host = urllib.parse.urlsplit(dest).hostname
                fragment = urllib.parse.unquote(urllib.parse.urlsplit(resolved).fragment)
                edge = {"source": url, "target": dest, "anchor": link_data["anchor"], "rel": link_data["rel"], "fragment": fragment, "internal": target_host == host}
                if target_host == host:
                    internal.append(edge)
                    follows = follow_nofollow or "nofollow" not in link_data["rel"].split() and "nofollow" not in data["robots"].lower()
                    if follows and depth < max_depth and dest not in seen and len(rows) + len(queue) < max_pages * 3:
                        queue.append((dest, depth + 1, depth_origin))
                else:
                    external.append(edge)
            discovered_links[url] = internal + external
            issues = _page_issues(url, data, response, is_html)
            if final_url != url:
                issues.append("Redirected")
            if data["refresh_redirect"]:
                issues.append("Meta refresh redirect")
            row = {
                "url": url, "status": response["status"], "title": data["title"], "title_count": data["title_count"], "description_count": data["description_count"], "title_chars": data["title_chars"],
                "description": data["description"], "description_chars": data["description_chars"], "description_px": data["description_px"],
                "h1": " | ".join(data["h1"]), "h1_count": len(data["h1"]), "h2_count": len(data["h2"]),
                "canonical": " | ".join(urllib.parse.urljoin(target, c) for c in data["canonical"]),
                "canonical_data": [urllib.parse.urljoin(target, c) for c in data["canonical"]],
                "robots": data["robots"], "lang": data["lang"], "viewport": data["viewport"],
                "doctype": data["doctype"], "og_title": data["meta_og_title"], "og_description": data["meta_og_description"],
                "og_image": urllib.parse.urljoin(target, data["meta_og_image"]) if data["meta_og_image"] else "",
                "twitter_card": data["twitter_card"], "hreflang_count": len(data["hreflang"]), "hreflang_data": data["hreflang"],
                "schema_types": ", ".join(data["schema_types"]), "schema_count": data["schema_count"], "schema_errors": data["schema_errors"],
                "images": data["images_count"], "images_missing_alt": data["images_missing_alt"], "images_empty_alt": data["images_empty_alt"], "words": data["words"],
                "content_hash": data["content_hash"], "sitemap": url in sitemap_urls,
                "content_type": response["content_type"], "bytes": response["bytes"], "truncated": response["truncated"],
                "depth": depth, "depth_origin": depth_origin, "inlinks": 0, "outlinks": len(internal), "external_links": len(external),
                "empty_anchor_links": sum(1 for edge in internal if not edge["anchor"]),
                "broken_internal_links": 0, "broken_anchor_links": 0, "elapsed_ms": response["elapsed_ms"],
                "server": response["headers"].get("server", ""), "cache_control": response["headers"].get("cache-control", ""),
                "last_modified": response["headers"].get("last-modified", ""), "etag": response["headers"].get("etag", ""),
                "content_encoding": response["headers"].get("content-encoding", ""),
                "indexability": "error" if isinstance(response["status"], int) and response["status"] >= 400 else "noindex" if "noindex" in data["robots"].lower() else "indexable" if is_html else "non-html",
                "issues": "; ".join(issues), "final_url": final_url,
                "hreflang": data["hreflang"], "images_data": [{**image, "src": urllib.parse.urljoin(target, image["src"])} for image in data["images"]], "ids": sorted(data["ids"]),
                "internal_link_data": internal, "external_link_data": external,
            }
            rows.append(row)
        except Exception as exc:
            rows.append(_error_row(url, depth, depth_origin, exc))
        if progress: progress(len(rows), max_pages, url)

    external_urls = sorted({edge["target"] for edge_list in discovered_links.values() for edge in edge_list if edge["internal"] is False})
    external_results = {}
    if check_external:
        for target in external_urls[:max(0, min(int(max_external_urls), 200))]:
            if stop_event and stop_event.is_set() or time.monotonic() - started >= max_seconds:
                break
            if external_results:
                wait = 1.0 - (time.monotonic() - last_request)
                if wait > 0:
                    if stop_event and stop_event.wait(wait):
                        break
                    if not stop_event:
                        time.sleep(wait)
            last_request = time.monotonic()
            external_results[target] = _head_check(target, timeout)
    for edges in discovered_links.values():
        for edge in edges:
            if edge["target"] in external_results:
                edge.update(external_results[edge["target"]])
            else:
                edge["status"] = "NOT_CHECKED" if edge["internal"] is False and check_external else "EXTERNAL"
    rows_by_url = {row["url"]: row for row in rows}
    inbound = Counter()
    outbound_to_errors = Counter()
    outbound_external_errors = Counter()
    broken_fragments = Counter()
    anchors_by_url = {url: set(row.get("ids", [])) for url, row in rows_by_url.items()}
    for source, edges in discovered_links.items():
        for edge in edges:
            dest = edge["target"]
            if edge.get("internal"):
                inbound[dest] += 1
                target_row = rows_by_url.get(dest)
                if target_row and (target_row["status"] == "ERROR" or isinstance(target_row["status"], int) and target_row["status"] >= 400):
                    outbound_to_errors[source] += 1
                if target_row and edge["fragment"] and edge["fragment"] not in anchors_by_url[dest]:
                    broken_fragments[source] += 1
            elif isinstance(edge.get("status"), int) and edge["status"] >= 400:
                outbound_external_errors[source] += 1
    for row in rows:
        row["inlinks"] = inbound[row["url"]]
        row["broken_internal_links"] = outbound_to_errors[row["url"]]
        row["broken_external_links"] = outbound_external_errors[row["url"]]
        row["broken_anchor_links"] = broken_fragments[row["url"]]
        row["orphan"] = row["url"] in sitemap_urls and row["inlinks"] == 0 and row["url"] != start
        if outbound_to_errors[row["url"]]:
            _append_issue(row, f"Broken internal link ({outbound_to_errors[row['url']]})")
        if outbound_external_errors[row["url"]]:
            _append_issue(row, f"Broken external link ({outbound_external_errors[row['url']]})")
        if broken_fragments[row["url"]]:
            _append_issue(row, f"Broken anchor ({broken_fragments[row['url']]})")
        if row["orphan"]:
            _append_issue(row, "Sitemap orphan (no internal inlinks)")
        if row["empty_anchor_links"]:
            _append_issue(row, f"Empty internal link text ({row['empty_anchor_links']})")
        if row["sitemap"] and "noindex" in row["robots"].lower():
            _append_issue(row, "Noindex URL listed in sitemap")
        if sitemap_urls and not row["sitemap"] and "noindex" not in row["robots"].lower() and isinstance(row["status"], int) and 200 <= row["status"] < 300:
            _append_issue(row, "Indexable URL missing from sitemap")
        canonical_values = row.get("canonical_data", [])
        if len(canonical_values) == 1:
            canonical_host = urllib.parse.urlsplit(canonical_values[0]).hostname
            if canonical_host != host:
                _append_issue(row, "Canonical points off-host")
            canonical_row = rows_by_url.get(normalize_url(canonical_values[0]))
            if canonical_row and isinstance(canonical_row["status"], int) and canonical_row["status"] >= 400:
                _append_issue(row, "Canonical target returns HTTP error")
        hreflang_codes = [item["lang"].casefold() for item in row.get("hreflang_data", [])]
        if len(hreflang_codes) != len(set(hreflang_codes)):
            _append_issue(row, "Duplicate hreflang language")

    _mark_duplicates(rows, "title", "Duplicate title")
    _mark_duplicates(rows, "description", "Duplicate meta description")
    _mark_duplicates(rows, "canonical", "Duplicate canonical")
    _mark_duplicates(rows, "content_hash", "Duplicate content")
    for row in rows:
        canonicals = [part.strip() for part in row["canonical"].split("|") if part.strip()]
        if len(canonicals) == 1 and normalize_url(canonicals[0]) != row["url"]:
            _append_issue(row, "Canonical differs from URL")
        if row["url"] not in sitemap_urls and sitemap_urls:
            row["sitemap"] = False
    all_edges = [edge for edges in discovered_links.values() for edge in edges]
    pages_seen = {row["url"] for row in rows}
    return {
        "start_url": start, "pages": rows, "links": all_edges,
        "robots_checked": robots_available, "robots_delay": robots_delay,
        "sitemap_files": sorted(sitemap_files), "sitemap_urls": sorted(sitemap_urls),
        "sitemap_errors": sitemap_errors, "sitemaps_found": len(sitemap_files),
        "sitemap_unseen_urls": len(sitemap_urls - pages_seen),
        "external_checked": len(external_results), "external_urls_discovered": len(external_urls),
        "external_unchecked": max(0, len(external_urls) - len(external_results)),
        "stopped": bool(stop_event and stop_event.is_set()),
        "timed_out": bool((queue or seed_pool or check_external and len(external_results) < min(len(external_urls), int(max_external_urls))) and not (stop_event and stop_event.is_set()) and time.monotonic() - started >= max_seconds),
        "limit_reached": bool((queue or seed_pool) and len(rows) >= max_pages), "depth_skipped": depth_skipped,
        "max_pages": max_pages, "max_depth": max_depth,
        "scope": host,
    }


def _empty_page_data():
    return {"title": "", "title_count": 0, "description_count": 0, "title_chars": 0, "description": "", "description_chars": 0, "description_px": None, "h1": [], "h2": [],
            "heading_levels": [], "canonical": [], "robots": "", "lang": "", "viewport": False, "doctype": False,
            "meta_og_title": "", "meta_og_description": "", "meta_og_image": "", "twitter_card": "",
            "hreflang": [], "links": [], "images_count": 0, "images_missing_alt": 0, "images_empty_alt": 0, "images": [], "ids": set(),
            "words": 0, "content_hash": "", "schema_types": [], "schema_errors": 0, "schema_count": 0,
            "refresh_redirect": False}


def _blocked_row(url, depth, depth_origin="Start-URL"):
    return {"url": url, "status": "ROBOTS", "title": "", "title_count": 0, "description_count": 0, "title_chars": 0, "description": "", "description_chars": 0, "description_px": None,
            "h1": "", "h1_count": 0, "h2_count": 0, "canonical": "", "robots": "blocked by robots.txt", "lang": "", "hreflang_data": [],
            "viewport": False, "doctype": False, "og_title": "", "og_description": "", "og_image": "", "twitter_card": "",
            "hreflang_count": 0, "schema_types": "", "schema_count": 0, "schema_errors": 0, "images": 0,
            "images_missing_alt": 0, "images_empty_alt": 0, "words": 0, "content_hash": "", "sitemap": False, "content_type": "", "bytes": 0,
            "truncated": False, "depth": depth, "depth_origin": depth_origin, "inlinks": 0, "outlinks": 0, "external_links": 0, "empty_anchor_links": 0,
            "broken_internal_links": 0, "broken_external_links": 0, "broken_anchor_links": 0, "elapsed_ms": 0, "server": "", "cache_control": "",
            "last_modified": "", "etag": "", "content_encoding": "", "canonical_data": [],
            "indexability": "blocked", "issues": "Blocked by robots.txt", "final_url": url, "hreflang": [], "images_data": [], "ids": [],
            "internal_link_data": [], "external_link_data": [], "orphan": False}


def _error_row(url, depth, depth_origin, exc):
    row = _blocked_row(url, depth, depth_origin)
    row.update(status="ERROR", robots="", indexability="error", issues=" ".join(str(exc).split())[:220])
    return row


def _page_issues(url, data, response, is_html):
    issues = []
    if response["status"] >= 400:
        issues.append("HTTP error")
    if not is_html:
        return issues
    if not data["title"]: issues.append("Missing title")
    elif data["title_count"] > 1: issues.append("Multiple title elements")
    elif data["title_chars"] > 60: issues.append("Long title")
    if not data["description"]:
        issues.append("Missing meta description")
    elif data["description_count"] > 1:
        issues.append("Multiple meta descriptions")
    else:
        for code, _detail in serp_limits.befunde(data["description"]):
            if code == "zu-kurz": issues.append("Short meta description")
            elif code == "zu-lang": issues.append("Long meta description")
            elif code == "zu-breit": issues.append("Wide meta description")
            elif code == "unmessbar": issues.append("Meta description width not measurable")
    if not data["h1"]: issues.append("Missing H1")
    elif len(data["h1"]) > 1: issues.append("Multiple H1")
    if not data["canonical"]: issues.append("Missing canonical")
    elif len(data["canonical"]) > 1: issues.append("Multiple canonicals")
    if "noindex" in data["robots"].lower(): issues.append("Noindex")
    if "nofollow" in data["robots"].lower(): issues.append("Nofollow directive")
    if not data["lang"]: issues.append("Missing lang")
    if not data["viewport"]: issues.append("Missing viewport")
    if not data["doctype"]: issues.append("Missing HTML doctype")
    if data["images_missing_alt"]: issues.append(f"Images missing alt ({data['images_missing_alt']})")
    if data["schema_errors"]: issues.append("Invalid JSON-LD")
    if not data["meta_og_title"]: issues.append("Missing Open Graph title")
    if not data["meta_og_description"]: issues.append("Missing Open Graph description")
    if not data["twitter_card"]: issues.append("Missing Twitter card")
    if any(right > left + 1 for left, right in zip(data["heading_levels"], data["heading_levels"][1:])):
        issues.append("Heading order jump")
    return issues


def _append_issue(row, issue):
    existing = row.get("issues", "")
    if issue not in existing.split("; "):
        row["issues"] = "; ".join(filter(None, (existing, issue)))


def _mark_duplicates(rows, key, issue):
    groups = {}
    for row in rows:
        value = row.get(key, "")
        if value and row.get("status") != "ERROR" and row.get("status") != "ROBOTS":
            groups.setdefault(value.strip().casefold(), []).append(row)
    for group in groups.values():
        if len(group) > 1:
            for row in group:
                _append_issue(row, issue)


def csv_text(pages):
    import io
    fields = ["url", "status", "title", "title_chars", "description", "description_count", "description_chars", "description_px", "title_count", "h1", "h1_count", "h2_count",
              "canonical", "indexability", "robots", "lang", "viewport", "doctype", "og_title", "og_description", "og_image", "twitter_card",
              "hreflang_count", "schema_types", "schema_count", "schema_errors", "images", "images_missing_alt", "images_empty_alt", "words",
              "sitemap", "content_type", "bytes", "truncated", "depth", "depth_origin", "inlinks", "outlinks", "external_links",
              "empty_anchor_links", "broken_internal_links", "broken_external_links", "broken_anchor_links", "elapsed_ms", "server", "cache_control",
              "last_modified", "etag", "content_encoding", "orphan", "issues", "final_url"]
    output = io.StringIO(newline="")
    writer = csv.DictWriter(output, fieldnames=fields, extrasaction="ignore")
    writer.writeheader()
    for page in pages:
        safe_row = dict(page)
        for key, value in safe_row.items():
            if isinstance(value, str) and value.lstrip(" \t\r\n")[:1] in ("=", "+", "-", "@"):
                safe_row[key] = "'" + value
        writer.writerow(safe_row)
    return output.getvalue()


def links_csv_text(links):
    import io
    output = io.StringIO(newline="")
    fields = ("source", "target", "anchor", "rel", "fragment", "internal", "status", "final_url", "elapsed_ms")
    writer = csv.DictWriter(output, fieldnames=fields, extrasaction="ignore")
    writer.writeheader()
    for edge in links:
        safe = {key: ("'" + value if isinstance(value, str) and value.lstrip(" \t\r\n")[:1] in ("=", "+", "-", "@") else value) for key, value in edge.items()}
        writer.writerow(safe)
    return output.getvalue()
