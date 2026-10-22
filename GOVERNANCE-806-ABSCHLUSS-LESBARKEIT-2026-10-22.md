# Governance-Report #806 – Abschlussprüfung Lesbarkeit

**Prüfdatum:** 22.10.2026
**Ergebnis:** GREEN – der im Issue verbliebene redaktionelle Befund ist im geprüften Repository-Stand nicht mehr vorhanden.

## Befund und Gegenprüfung

Issue #806 führte zwei Entwürfe mit Messwerten vom 19.10.2026 unter der Publish-Schwelle 60:

| Entwurf | Im Issue vom 19.10. | Gegenprüfung am 22.10. | Urteil |
|---|---:|---:|---|
| `2026-10-19-urlaubskasse-clever-aufbessern/index.md` | 54,2 | **82,0** | über Publish-Schwelle |
| `2026-10-16-dns-server-aendern-fuer-schnelleres-internet/index.md` | 54,9 | **72,4** | über Publish-Schwelle |

Die Befunde im Issue waren damit veraltet. Die beiden Artikel wurden nicht allein für einen Score kosmetisch umgeschrieben: Die aktuelle Fassung wurde erneut mit derselben Lesbarkeits-Wache gemessen.

## Prüfung des Bestands und der Schutzmechanismen

- `python3 scripts/readability_check.py --gate-bestand --report /tmp/lesbarkeit.md` → **GREEN**; 64 Live-Artikel, Ø Flesch 65,2, kein Live-Artikel unter Floor 55; 30 Entwürfe, **0** unter der Publish-Schwelle 60.
- `python3 scripts/readability_check.py --selftest` → **grün** (R6-Schwellen, Shortcode-Stripping und Trennung von Live-Bestand und Entwürfen).
- `python3 scripts/textverstaendnis_guard.py --selftest` → **grün** (R2–R17).
- `python3 -m venv .venv && .venv/bin/pip install PyYAML==6.0.3 && .venv/bin/python scripts/governance_contract.py --quick` → **alle 38 Governance-Regeln erfüllt**.

Die dauerhafte Absicherung besteht aus der zentralen Publish-Schwelle in `scripts/readability_check.py`, dem Lesbarkeits-Gate für neue Artikel und der wöchentlichen Premium-Governance-Messung. Das Bestands-Gate weist unterschwellige Entwürfe namentlich aus, ohne sie fälschlich als Live-Regression zu behandeln; das Publish-Gate verhindert, dass ein Entwurf unter der Schwelle veröffentlicht wird.

## Ausführungsgrenze

Ein manueller Dispatch des Premium-Governance-Workflows auf den Session-Branch wurde versucht, aber von GitHub mit HTTP 403 („Resource not accessible by integration“) abgewiesen. Der Abschluss beruht deshalb auf den lokalen, reproduzierbaren Messungen und Selbsttests oben – nicht auf einem behaupteten erfolgreichen CI-Workflow-Lauf.

**Schlussfolgerung:** Der einzige handlungsbedürftige Befund aus Issue #806 ist im geprüften Stand behoben; die übrigen im Issue aufgeführten Datenlagen waren als Hinweise ohne Handlungsbedarf klassifiziert.
