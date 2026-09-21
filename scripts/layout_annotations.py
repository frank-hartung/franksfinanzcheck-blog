#!/usr/bin/env python3
"""layout_annotations.py – Befunde als GitHub-Annotationen (Issue #338).

WARUM:
Der Layout-Audit schreibt seinen Bericht in `LAYOUT-REPORT.md`, die Zahlen in
`.cache/layout/dom-audit.json` und das Browser-Ergebnis nach
`/tmp/browser-audit.json`. Alles drei liegt im **Log** – und Logs sieht man
erst, wenn man den Lauf öffnet, den Step sucht und kopiert. Genau so wurde
#338 zum Dauer-Issue: Der Befund stand im Bericht, aber nicht dort, wo
entschieden wird (Pull Request, Checks-Tab).

Dieses Skript bringt die Befunde an die Oberfläche:
  - je kritischem Befund eine `::error::`-Annotation (rot am Lauf/PR),
  - je Frühwarnung eine `::warning::`-Annotation (gelb, ohne roten Lauf),
  - eine `::notice::` mit den Kennzahlen des Laufs.

Es entscheidet NICHTS – Severity und Exit-Code kommen aus den Audits
(`dom_audit.py` = Lighthouse-Grenzen kritisch, Frühwarnungen weich;
`layout_browser_check.js` = nur Lighthouse-Grenzen/Fehler/Parser-Drift rot).
Hier wird nur übersetzt, was schon entschieden ist.

GitHub versteht höchstens 10 Warnungen und 10 Fehler je Step; weitere werden
verworfen. Deshalb wird hier bewusst gedeckelt und die Zahl der verschwiegenen
Befunde genannt („+N weitere") – eine Liste, die bei 10 aufhört und das nicht
sagt, ist schlimmer als keine Liste.
"""
from __future__ import annotations

import argparse
import json
import os
import sys

DEFAULT_DOM = os.path.join(".cache", "layout", "dom-audit.json")
DEFAULT_BROWSER = "/tmp/browser-audit.json"
MAX_ANNOTATIONS = 10


def escape(text: str) -> str:
    """Workflow-Command-Escaping: sonst zerlegt ein Zeilenumbruch den Befehl."""
    return (str(text).replace("%", "%25")
            .replace("\r", "%0D")
            .replace("\n", "%0A"))


def _load(path: str) -> dict:
    try:
        with open(path, encoding="utf-8") as fh:
            data = json.load(fh)
        return data if isinstance(data, dict) else {}
    except (OSError, ValueError):
        return {}


def dom_lines(dom: dict) -> tuple[list[str], list[str]]:
    """(errors, warnings) aus dem statischen DOM-Budget."""
    if not dom:
        return [], []
    errors = [
        f"{row.get('rel', '?')}: {'; '.join(row.get('critical', []))}"
        for row in dom.get("critical", []) if row.get("critical")]
    warnings = [
        f"{row.get('rel', '?')}: {'; '.join(row.get('warnings', []))}"
        for row in dom.get("warnings", []) if row.get("warnings")]
    return errors, warnings


def browser_lines(browser: dict) -> tuple[list[str], list[str]]:
    """(errors, warnings) aus dem Browser-Audit."""
    if not browser:
        return [], []
    errors, warnings = [], []
    for page in browser.get("criticalPages", []):
        errors.append(f"{page.get('url', '?')} ({page.get('viewport', '?')}): "
                      + "; ".join(page.get("issues", [])))
    for page in browser.get("warningPages", []):
        warnings.append(f"{page.get('url', '?')} ({page.get('viewport', '?')}): "
                        + "; ".join(page.get("warnings", [])))
    if browser.get("toolError"):
        errors.append("Browser-Audit: Werkzeugfehler (fail-closed)")
    return errors, warnings


def summary_notice(dom: dict, browser: dict) -> str:
    parts = []
    if dom:
        worst = dom.get("worst") or {}
        parts.append(f"Statisch: {dom.get('pages', '?')} Seiten vermessen")
        if worst:
            parts.append(
                "Maxima – Kinder {maxchildren} ({maxchildren_path}), Head "
                "{headchildren}, Tiefe {depth}, Elemente {elements}".format(**worst))
    metrics = (browser or {}).get("domMetrics") or {}
    if metrics:
        parts.append(
            "Browser-Laufzeit: max. Kinder {maxChildren} ({maxChildrenElement}), "
            "Head {maxHeadChildren}, Tiefe {maxDepth}, Elemente {maxElements}"
            .format(**metrics))
    html_metrics = (browser or {}).get("domMetricsHtmlOnly") or {}
    if html_metrics:
        parts.append(
            "HTML ohne Fremd-Skripte: max. Elemente {maxElements}, Head "
            "{maxHeadChildren}".format(**html_metrics))
    layer = (browser or {}).get("erweiterungsschicht") or {}
    if layer:
        parts.append("Erweiterungsschicht der Site (Laufzeit − HTML): "
                     f"+{layer.get('min', 0)} bis +{layer.get('max', 0)} Elemente")
    check = (browser or {}).get("parserCheck") or {}
    if check:
        parts.append(f"Parser-Gegenrechnung an {check.get('compared', 0)} Messungen, "
                     f"Drift: {len(check.get('drift', []))}")
    if not parts:
        return "Layout-Audit: keine Zahlen gefunden (kein Bau/kein Bericht?)."
    return " · ".join(parts)


def emit(level: str, message: str, out) -> None:
    print(f"::{level}::{escape(message)}", file=out)


def report(dom: dict, browser: dict, max_annotations: int = MAX_ANNOTATIONS,
           out=None) -> dict:
    """Schreibt Annotationen und gibt die Zählung für Tests/Logs zurück."""
    out = out or sys.stdout
    errors, warnings = dom_lines(dom)
    b_errors, b_warnings = browser_lines(browser)
    errors += b_errors
    warnings += b_warnings

    for message in errors[:max_annotations]:
        emit("error", "Layout-Audit: " + message, out)
    if len(errors) > max_annotations:
        emit("error", f"Layout-Audit: +{len(errors) - max_annotations} weitere "
                      "kritische Befunde (siehe LAYOUT-REPORT.md)", out)
    for message in warnings[:max_annotations]:
        emit("warning", "Layout-Audit (Frühwarnung): " + message, out)
    if len(warnings) > max_annotations:
        emit("warning", f"Layout-Audit: +{len(warnings) - max_annotations} weitere "
                        "Frühwarnungen (siehe LAYOUT-REPORT.md)", out)
    emit("notice", summary_notice(dom, browser), out)

    if errors:
        print(f"❌ {len(errors)} kritische(r) Befund(e)", file=out)
    elif warnings:
        print(f"✅ keine kritischen Befunde, {len(warnings)} Frühwarnung(en)", file=out)
    else:
        print("✅ keine Befunde", file=out)
    return {"errors": len(errors), "warnings": len(warnings)}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("--dom", default=DEFAULT_DOM,
                        help=f"JSON des statischen Audits (Standard: {DEFAULT_DOM})")
    parser.add_argument("--browser", default=DEFAULT_BROWSER,
                        help="JSON des Browser-Audits")
    parser.add_argument("--max", type=int, default=MAX_ANNOTATIONS,
                        help="Höchstzahl Annotationen je Stufe")
    parser.add_argument("--json", dest="json_out",
                        help="Zählung zusätzlich in diese Datei schreiben")
    args = parser.parse_args(argv)

    dom = _load(args.dom)
    browser = _load(args.browser)
    if not dom and not browser:
        print(f"Keine Berichte gefunden ({args.dom}, {args.browser}) – "
              "nichts zu annotieren.")
        return 0
    counts = report(dom, browser, max(1, args.max))
    if args.json_out:
        with open(args.json_out, "w", encoding="utf-8") as fh:
            json.dump(counts, fh, ensure_ascii=False, sort_keys=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
