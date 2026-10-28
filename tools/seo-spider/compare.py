"""Deterministic before/after comparisons for exported crawler reports."""
from __future__ import annotations

from crawler import normalize_url

COMPARE_FIELDS = (
    "status", "title", "description", "h1", "canonical", "robots", "indexability",
    "sitemap", "depth", "inlinks", "outlinks", "broken_internal_links", "broken_external_links",
    "images_missing_alt", "schema_errors", "content_hash",
)


def compare_pages(current_pages, baseline_pages):
    def index(pages):
        result = {}
        for page in pages:
            url = normalize_url(str(page.get("url", "")))
            if url:
                result[url] = page
        return result

    current, baseline = index(current_pages), index(baseline_pages)
    added_urls = sorted(current.keys() - baseline.keys())
    removed_urls = sorted(baseline.keys() - current.keys())
    changed, unchanged = [], 0
    for url in sorted(current.keys() & baseline.keys()):
        before, after = baseline[url], current[url]
        differences = [
            {"field": field, "before": before.get(field), "after": after.get(field)}
            for field in COMPARE_FIELDS if before.get(field) != after.get(field)
        ]
        if differences:
            changed.append({"url": url, "changes": differences})
        else:
            unchanged += 1
    return {
        "summary": {"added": len(added_urls), "removed": len(removed_urls), "changed": len(changed), "unchanged": unchanged},
        "added": added_urls,
        "removed": removed_urls,
        "changed": changed,
    }
