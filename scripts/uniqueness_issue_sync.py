#!/usr/bin/env python3
"""Synchronisiert den einen offenen Einzigartigkeits-Befund mit GitHub Issues.

Das Einzigartigkeits-Audit selbst entscheidet ausschließlich über Inhalt und
liefert seinen Exit-Code:
  0  kein kritischer Live-Befund
  1  kritischer Live-Befund
  2  die Audit-Selbsttests sind kaputt

Dieses kleine Betriebswerkzeug macht daraus einen belastbaren Vorgang – ohne
`gh`-Abhängigkeit und ohne bei jedem täglichen Lauf ein weiteres Issue zu
öffnen:

* `--status critical` erstellt oder aktualisiert GENAU ein kanonisches Issue.
* `--status clean` kommentiert und schließt nur dieses kanonische Issue.
* Nicht-Produktionsläufe dürfen weder einen echten Befund öffnen noch einen
  Produktionsbefund schließen. Der erwartete Produktions-Ref wird deshalb
  zusätzlich zum Workflow-`if` hier geprüft.

Der Selbsttest ist komplett offline. Das Skript wird nur in GitHub Actions mit
`GITHUB_TOKEN` und `GITHUB_REPOSITORY` gegen die API ausgeführt.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any, Iterable

ISSUE_TITLE = "📋 Einzigartigkeits-Audit: Bestandsüberlappungen gefunden"
REPORT_LIMIT = 55_000  # GitHub-Issue-Body bleibt sicher unter dem API-Limit.
USER_AGENT = "franksfinanzcheck-uniqueness-issue-sync"


def is_production_ref(current_ref: str, expected_ref: str) -> bool:
    """Nur der explizit erwartete Produktionsref darf Issue-Zustand ändern."""
    return bool(expected_ref) and current_ref == expected_ref


def matching_open_issues(items: Iterable[dict[str, Any]]) -> list[dict[str, Any]]:
    """Filtert exakt benannte offene Issues und ignoriert Pull Requests."""
    return [
        item for item in items
        if not item.get("pull_request") and item.get("title") == ISSUE_TITLE
    ]


def clipped_report(text: str) -> str:
    """Bewahrt bei sehr langen Logs Anfang und Ende als redaktionellen Beleg."""
    text = text.strip()
    if len(text) <= REPORT_LIMIT:
        return text
    head = REPORT_LIMIT // 2
    tail = REPORT_LIMIT - head
    return (
        text[:head]
        + "\n\n… [Audit-Ausgabe für GitHub gekürzt; vollständiger Beleg im Workflow-Log] …\n\n"
        + text[-tail:]
    )


def run_url(env: dict[str, str]) -> str:
    """Erzeugt einen stabilen Link zum auslösenden Workflow-Lauf."""
    server = env.get("GITHUB_SERVER_URL", "https://github.com").rstrip("/")
    repo = env.get("GITHUB_REPOSITORY", "")
    run_id = env.get("GITHUB_RUN_ID", "")
    if repo and run_id:
        return f"{server}/{repo}/actions/runs/{run_id}"
    return f"{server}/{repo}" if repo else server


def critical_body(report: str, evidence_url: str) -> str:
    """Kanonischer, überschreibbarer Issue-Body für einen offenen Befund."""
    evidence = clipped_report(report) or "(Das Audit lieferte keine lesbare Ausgabe.)"
    return "\n".join([
        "## Offener Bestandsbefund",
        "",
        "Das tägliche Einzigartigkeits-Audit hat mindestens eine kritische "
        "Überlappung zwischen zwei live auslieferbaren Artikeln gefunden. "
        "Entwürfe, künftige oder abgelaufene Seiten werden separat geführt und "
        "lösen diesen Vorgang nicht aus.",
        "",
        f"**Aktueller Beleg:** [Workflow-Lauf]({evidence_url})",
        "",
        "### Aktuelle Audit-Ausgabe",
        "```text",
        evidence,
        "```",
        "",
        "---",
        "Dieser Vorgang wird beim nächsten sauberen Produktionslauf automatisch "
        "kommentiert und geschlossen. Neue kritische Läufe aktualisieren diesen "
        "einen Vorgang statt weitere Duplikate zu erzeugen.",
    ])


def resolution_comment(evidence_url: str) -> str:
    return "\n".join([
        "✅ **Audit wieder grün.**",
        "",
        "Der Produktionslauf meldet keine kritischen Überlappungen zwischen "
        "live auslieferbaren Artikeln mehr. Der Befund ist damit verifiziert "
        f"erledigt: [Workflow-Lauf]({evidence_url}).",
    ])


class GitHubIssuesApi:
    """Minimaler, bewusst enger REST-Client für genau diesen Issue-Lebenszyklus."""

    def __init__(self, token: str, repository: str, api_url: str = "https://api.github.com"):
        self.token = token
        self.repository = repository
        self.api_url = api_url.rstrip("/")

    def _request(self, method: str, path: str, payload: dict[str, Any] | None = None) -> tuple[Any, dict[str, str]]:
        data = json.dumps(payload, ensure_ascii=False).encode("utf-8") if payload is not None else None
        request = urllib.request.Request(
            self.api_url + path,
            data=data,
            method=method,
            headers={
                "Accept": "application/vnd.github+json",
                "Authorization": f"Bearer {self.token}",
                "User-Agent": USER_AGENT,
                **({"Content-Type": "application/json"} if data is not None else {}),
            },
        )
        try:
            with urllib.request.urlopen(request, timeout=30) as response:
                raw = response.read().decode("utf-8")
                parsed = json.loads(raw) if raw else None
                return parsed, dict(response.headers.items())
        except urllib.error.HTTPError as exc:
            detail = exc.read().decode("utf-8", errors="replace")
            raise RuntimeError(
                f"GitHub API {method} {path} fehlgeschlagen ({exc.code}): {detail[:500]}"
            ) from exc
        except urllib.error.URLError as exc:
            raise RuntimeError(f"GitHub API {method} {path} nicht erreichbar: {exc.reason}") from exc

    def _issues_path(self) -> str:
        return "/repos/" + urllib.parse.quote(self.repository, safe="/") + "/issues"

    def list_open(self) -> list[dict[str, Any]]:
        """Holt alle offenen Issues; 100 reichen meist, Pagination ist trotzdem echt."""
        path = self._issues_path() + "?state=open&per_page=100"
        items: list[dict[str, Any]] = []
        while path:
            page, headers = self._request("GET", path)
            items.extend(page or [])
            path = ""
            # RFC-5988 Link-Header, nur rel="next" interessiert uns.
            for part in headers.get("Link", "").split(","):
                if 'rel="next"' not in part:
                    continue
                target = part.split(";", 1)[0].strip().strip("<>")
                parsed = urllib.parse.urlparse(target)
                path = parsed.path + (f"?{parsed.query}" if parsed.query else "")
                break
        return items

    def create(self, body: str) -> dict[str, Any]:
        result, _ = self._request("POST", self._issues_path(), {
            "title": ISSUE_TITLE,
            "body": body,
        })
        return result

    def update(self, number: int, body: str) -> None:
        self._request("PATCH", f"{self._issues_path()}/{number}", {
            "title": ISSUE_TITLE,
            "body": body,
        })

    def comment(self, number: int, body: str) -> None:
        self._request("POST", f"{self._issues_path()}/{number}/comments", {"body": body})

    def close(self, number: int) -> None:
        self._request("PATCH", f"{self._issues_path()}/{number}", {
            "state": "closed",
            "state_reason": "completed",
        })


def sync(status: str, report: str, env: dict[str, str]) -> int:
    """Führt den idempotenten Lebenszyklus aus; Rückgabe ist CI-tauglich."""
    expected_ref = env.get("UNIQUE_PRODUCTION_REF", "")
    current_ref = env.get("GITHUB_REF", "")
    if not is_production_ref(current_ref, expected_ref):
        print(
            "ℹ️ Issue-Synchronisierung übersprungen: "
            f"Ref {current_ref or '(leer)'} ist nicht {expected_ref or '(nicht gesetzt)'}."
        )
        return 0

    token = env.get("GITHUB_TOKEN", "")
    repository = env.get("GITHUB_REPOSITORY", "")
    missing = [name for name, value in (("GITHUB_TOKEN", token), ("GITHUB_REPOSITORY", repository)) if not value]
    if missing:
        raise RuntimeError("Issue-Synchronisierung ohne " + ", ".join(missing) + " ist unsicher.")

    api = GitHubIssuesApi(token, repository, env.get("GITHUB_API_URL", "https://api.github.com"))
    matches = matching_open_issues(api.list_open())
    evidence_url = run_url(env)

    if status == "critical":
        body = critical_body(report, evidence_url)
        # Die REST-API liefert standardmäßig zuletzt aktualisierte Issues zuerst.
        # Der älteste Befund bleibt trotzdem kanonisch; ein jüngeres Doppel-Issue
        # darf weder die Historie noch den Owner-Weckruf verdrängen.
        ordered_matches = sorted(
            matches,
            key=lambda item: (str(item.get("created_at", "")), int(item.get("number", 0))),
        )
        if ordered_matches:
            canonical = ordered_matches[0]
            number = int(canonical["number"])
            api.update(number, body)
            print(f"ℹ️ Einzigartigkeits-Issue #{number} mit aktuellem Beleg aktualisiert.")
        else:
            created = api.create(body)
            number = int(created["number"])
            print(f"✅ Einzigartigkeits-Issue #{number} erstellt.")

        # Ein alter, versehentlich parallel geöffneter Vorgang darf keine echte
        # Störung deduplizieren. Der älteste bleibt der kanonische Vorgang.
        for duplicate in ordered_matches[1:]:
            duplicate_number = int(duplicate["number"])
            api.comment(duplicate_number, f"Duplikat von #{number}; der aktuelle Audit-Beleg liegt dort.")
            api.close(duplicate_number)
            print(f"ℹ️ Doppeltes Einzigartigkeits-Issue #{duplicate_number} geschlossen.")
        return 0

    if status == "clean":
        for issue in matches:
            number = int(issue["number"])
            api.comment(number, resolution_comment(evidence_url))
            api.close(number)
            print(f"✅ Einzigartigkeits-Issue #{number} nach grünem Audit geschlossen.")
        if not matches:
            print("✅ Kein offenes Einzigartigkeits-Issue – Audit ist bereits sauber dokumentiert.")
        return 0

    raise ValueError(f"Unbekannter Status: {status}")


def selftest() -> list[str]:
    """Offline-Regressionen für Filtering, Ref-Scope und Beleg-Format."""
    errors: list[str] = []
    issues = [
        {"number": 490, "title": ISSUE_TITLE},
        {"number": 491, "title": ISSUE_TITLE, "pull_request": {"url": "x"}},
        {"number": 492, "title": "anderes Issue"},
    ]
    matches = matching_open_issues(issues)
    if [row["number"] for row in matches] != [490]:
        errors.append("offene Issues/Pull Requests werden nicht eindeutig gefiltert")
    if not is_production_ref("refs/heads/main", "refs/heads/main"):
        errors.append("Produktions-Ref wird nicht erkannt")
    if is_production_ref("refs/heads/arena/test", "refs/heads/main"):
        errors.append("Arbeitsbranch dürfte Produktions-Issue verändern")
    oversized = "A" * (REPORT_LIMIT + 100)
    clipped = clipped_report(oversized)
    if "vollständiger Beleg" not in clipped or len(clipped) > REPORT_LIMIT + 200:
        errors.append("lange Audit-Ausgabe wird nicht nachvollziehbar begrenzt")
    body = critical_body("kritischer Fund", "https://example.test/run/1")
    if ISSUE_TITLE in body or "kritischer Fund" not in body or "Workflow-Lauf" not in body:
        errors.append("kritischer Issue-Body enthält nicht alle Pflichtbelege")
    comment = resolution_comment("https://example.test/run/2")
    if "Audit wieder grün" not in comment or "Workflow-Lauf" not in comment:
        errors.append("Schlusskommentar ist nicht prüfbar")
    return errors


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--status", choices=("critical", "clean"), help="Audit-Ergebnis synchronisieren")
    parser.add_argument("--report", type=Path, help="Audit-Log bei status=critical")
    parser.add_argument("--selftest", action="store_true", help="offline Regressionen ausführen")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv or sys.argv[1:])
    if args.selftest:
        errors = selftest()
        if errors:
            print("🛑 Issue-Sync-Selbsttest rot:\n" + "\n".join(f"  - {error}" for error in errors))
            return 2
        print("✅ Issue-Sync-Selbsttest grün (Scope, Dedupe, Beleg, Schlusskommentar).")
        return 0
    if not args.status:
        print("--status ist erforderlich (oder --selftest).", file=sys.stderr)
        return 2
    report = ""
    if args.report:
        try:
            report = args.report.read_text(encoding="utf-8")
        except OSError as exc:
            print(f"Audit-Report nicht lesbar ({args.report}): {exc}", file=sys.stderr)
            return 2
    try:
        return sync(args.status, report, dict(os.environ))
    except (OSError, RuntimeError, ValueError) as exc:
        print(f"🛑 Issue-Synchronisierung fehlgeschlagen: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
