#!/usr/bin/env python3
"""One stable delivery incident, closed only by a day-correct public receipt.

Premium-Fix 15.09.2026 (#287): Bei Source-Defizit (LIVE unter Minimum im
Repo) stößt die Recovery zuerst die Kadenz-Endkontrolle an – die füllt über
`publication_release.refill_to_min()` Re-Queue + Reserve nach. Deploy allein
reicht nicht, wenn der Source-Stand schon unter dem Mindestziel liegt.
Bei Source ok / Public defizit (CDN-Lag) bleibt Deploy der richtige Hebel.

Premium-Fix 07.10.2026 (WF-54C4 #610) – „Ein Beleg gehört seinem Tag“:
Die Auslieferungs-SLO misst immer den JÜNGSTEN Publikationstag. Das Issue
selbst gehört aber dem Tag, an dem es entstanden ist. Vorher schloss jeder
grüne Lauf das offene Issue – auch wenn der Beleg einen ganz anderen Tag
zeigte: Das Ticket über den 05.10.2026 wäre am 07.10. mit dem Beleg des
07.10. geschlossen worden, ohne dass der Fehltag je verbucht worden wäre.
Deshalb gilt jetzt:

  * GESCHLOSSEN wird nur mit einem Beleg DESSELBEN Tages.
  * Ist der gemessene Tag weitergezogen, ist der alte Tag nicht mehr
    nachholbar (kein Backdating – Betriebsvertrag). Dann verbucht der
    Abschluss ihn als **Quittung**: Tag, Zahlen und Nicht-Nachholbarkeit
    im Klartext, Beleg zusätzlich in `data/publication-delivery-history.jsonl`.
  * Ohne Zahlen keine Quittung – dann bleibt das Issue offen (fail-closed).
  * Der Issue-Body trägt den gemessenen Tag sichtbar (`Gemessener Tag:`) und
    wird bei jedem roten Lauf aktualisiert, damit die Akte den Tag mitführt.
"""
import argparse
import datetime as dt
import json
import os
import re
import subprocess
import sys
import tempfile
from pathlib import Path

try:  # Determinismus-Garantie (scripts/selftest_clock.py)
    from selftest_clock import (MITTAG as _MITTAG,  # type: ignore
                                MODUS_VERSCHOBEN as _UHR_VERSCHOBEN,
                                uhr as _uhr)
except ImportError:  # pragma: no cover – im Repo immer vorhanden
    _MITTAG = _uhr = None  # type: ignore

MARKER = '<!-- publication-delivery-slo -->'
BODY_TAG = '- **Gemessener Tag:**'


def gh(*args):
    return subprocess.check_output(['gh', *args], text=True)


def _receipt(day: str | None = None) -> dict:
    """Tagesgenauer Beleg, sonst der generische des Laufs (Rückfall)."""
    kandidaten = []
    if day:
        kandidaten.append(Path(f'tmp/publication-receipt-{day}.json'))
    kandidaten.append(Path('tmp/publication-receipt.json'))
    for path in kandidaten:
        if not path.exists():
            continue
        try:
            daten = json.loads(path.read_text(encoding='utf-8'))
        except Exception:  # noqa: BLE001 – Belegtext bleibt roh im Issue
            continue
        if isinstance(daten, dict):
            return daten
    return {}


def _tag_wert(wert) -> str | None:
    m = re.match(r'(\d{4}-\d{2}-\d{2})', str(wert or ''))
    return m.group(1) if m else None


def tag_aus_beleg(beleg: dict) -> str | None:
    return _tag_wert((beleg or {}).get('day'))


def tag_aus_body(body: str) -> str | None:
    """Der Tag, dem dieses Issue gehört – Marker zuerst, dann der Beleg-JSON."""
    m = re.search(r'(?m)^-\s*\*\*Gemessener Tag:\*\*\s*(\d{4}-\d{2}-\d{2})',
                  body or '')
    if m:
        return m.group(1)
    m = re.search(r'"day"\s*:\s*"(\d{4}-\d{2}-\d{2})"', body or '')
    return m.group(1) if m else None


def zahlen_aus_body(body: str) -> dict | None:
    """Zahlen des verbuchten Tages aus dem eingefrorenen Beleg im Issue."""
    m = re.search(r'```json\s*(\{.*?\})\s*```', body or '', re.S)
    if m:
        try:
            daten = json.loads(m.group(1))
            return {'minimum': int(daten.get('minimum') or 2),
                    'source': len(daten.get('source') or []),
                    'delivered': len(daten.get('delivered') or [])}
        except Exception:  # noqa: BLE001 – dann greift die Zeilen-Lesart
            pass
    quelle = re.search(r'Source LIVE:\*\*\s*(\d+)/(\d+)', body or '')
    geliefert = re.search(r'Öffentlich geliefert:\*\*\s*(\d+)/(\d+)', body or '')
    if quelle and geliefert:
        return {'minimum': int(quelle.group(2)),
                'source': int(quelle.group(1)),
                'delivered': int(geliefert.group(1))}
    return None


def quittung_text(issue_day: str, zahlen: dict, beleg_tag: str | None) -> str:
    """Buchung statt Beschönigung: der Fehltag wird verbucht, nicht behoben."""
    quelle = f"{zahlen.get('source', '?')}/{zahlen.get('minimum', '?')}"
    geliefert = f"{zahlen.get('delivered', '?')}/{zahlen.get('minimum', '?')}"
    return (
        f'Quittung: Der Auslieferungstag **{issue_day}** bleibt unter dem '
        f'Mindestziel (Source LIVE {quelle}, öffentlich geliefert {geliefert}).\n\n'
        f'Dieser Abschluss belegt ausdrücklich NICHT den {issue_day}: Der '
        f'Lauf-Nachweis gilt dem {beleg_tag} und der ist grün. Der {issue_day} '
        'ist vorbei und wird nicht nachdatiert – Nachtragen ist laut '
        'Betriebsvertrag verboten (docs/publication-reliability.md). '
        'Der Fehltag ist damit **verbucht, nicht behoben**; die '
        'Ursachenheilung läuft über die Dauerreparatur (#610) und ist im '
        'Code eingefroren (Publikations-Konvergenz, Nachweis-Pflicht beim '
        'Rückläufer).\n\n'
        f'Beleg des Tages: Issue-Body (eingefrorenes JSON) und die '
        'versionierte Historie `data/publication-delivery-history.jsonl`.')


def abschluss_entscheidung(issue_day: str | None, beleg: dict, *,
                           receipt_ok: bool,
                           zahlen: dict | None = None) -> tuple[str, str]:
    """Schließen | Quittung | offen – die eine Entscheidung des Kanals.

    Rückgabe: (urteil, text). `offen` trägt eine Begründung, `schliessen`
    und `quittung` den Kommentar für GitHub.
    """
    if not receipt_ok:
        return 'offen', ''
    beleg_tag = tag_aus_beleg(beleg)
    if not beleg_tag:
        return 'offen', ('Kein tagesgenauer Beleg vorhanden – ohne Tag kein '
                         'Abschluss. Das Issue bleibt offen (fail-closed).')
    if not issue_day or beleg_tag == issue_day:
        return 'schliessen', (
            f'Öffentlicher Nachweis erfolgreich: Mindestziel am {beleg_tag} '
            'in Sitemap und Artikel-HTML bestätigt.')
    if not zahlen:
        return 'offen', (f'Der Beleg gilt dem {beleg_tag}, das Issue dem '
                         f'{issue_day} – ohne die Zahlen des Fehltags gibt es '
                         'keine Quittung. Das Issue bleibt offen.')
    return 'quittung', quittung_text(issue_day, zahlen, beleg_tag)


def _body(lage: dict, *, tag: str | None, source: int, delivered: int,
          minimum: int, tag_deficit: bool, evidence: str) -> str:
    return (f'{MARKER}\n## Auslieferungsziel nicht bestätigt\n\n'
            f'{BODY_TAG} {tag or "?"}\n'
            f'UTC: {dt.datetime.now(dt.timezone.utc).isoformat()}\n\n'
            f'- **Source LIVE:** {source}/{minimum}\n'
            f'- **Öffentlich geliefert:** {delivered}/{minimum}\n'
            f'- **Diagnose:** '
            + ('Source unter Mindestziel → Kadenz-Endkontrolle füllt nach '
               '(Re-Queue + Reserve). '
               if tag_deficit else
               'Source ok, Public defizit → Deploy/CDN-Propagation. ')
            + '\n\n'
            f'```json\n{evidence}\n```\n\n'
            'Runbook: docs/publication-reliability.md. Keine Qualitätsgates umgehen.\n'
            'Reparatur #287: Deploy füllt nach Gate-Verwurf selbst nach; '
            'Endkontrolle bleibt der Tages-Backstop.\n'
            'Reparatur #610: Nachschub ohne Gate-Bestehen kehrt in den Vorrat '
            'zurück (Konvergenz statt 1/2), und dieser Kanal schließt nur mit '
            'einem Beleg SEINES Tages – sonst per Quittung.\n')


def main():
    issues = json.loads(gh('issue', 'list', '--state', 'open', '--search',
                           'in:title "P1: Öffentliche Artikel-Auslieferung"',
                           '--json', 'number,body'))
    issue = next((i for i in issues if MARKER in i.get('body', '')), None)

    if os.environ.get('RECEIPT_OK') == 'true':
        if not issue:
            return
        body = issue.get('body', '')
        issue_day = tag_aus_body(body)
        urteil_beleg = _receipt(issue_day)
        urteil, text = abschluss_entscheidung(
            issue_day, urteil_beleg, receipt_ok=True,
            zahlen=zahlen_aus_body(body))
        if urteil in ('schliessen', 'quittung'):
            gh('issue', 'close', str(issue['number']), '--comment', text)
            print(f'{urteil}: #{issue["number"]} ({issue_day}) – '
                  f'Beleg {tag_aus_beleg(urteil_beleg)}')
        else:
            print(text or 'Issue bleibt offen.')
        return

    # Roter Lauf: Issue anlegen/aktualisieren und die Reparatur anstoßen.
    path = Path('tmp/publication-receipt.json')
    evidence = path.read_text(encoding='utf-8') if path.exists() else \
        'Nachweis konnte nicht ausgeführt werden.'
    receipt = _receipt()
    source_n = len(receipt.get('source') or [])
    delivered_n = len(receipt.get('delivered') or [])
    minimum = int(receipt.get('minimum') or 2)
    source_deficit = source_n < minimum
    tag = tag_aus_beleg(receipt)
    body = _body(receipt, tag=tag, source=source_n, delivered=delivered_n,
                 minimum=minimum, tag_deficit=source_deficit,
                 evidence=evidence)
    if issue:
        gh('issue', 'edit', str(issue['number']), '--body', body)
    else:
        gh('issue', 'create',
           '--title', 'P1: Öffentliche Artikel-Auslieferung unter Mindestziel',
           '--body', body)
    # Bounded recovery: fixed monitoring slots only; no workflow_run cycle.
    # Publication Delivery can opt into the synchronous orchestrator so its
    # final assertion does not race an asynchronously dispatched backstop.
    # Other callers retain the original fire-and-forget recovery behaviour.
    if os.environ.get('DEFER_RECOVERY') == 'true':
        print('Recovery is handed to publication_recovery.py; waiting before final receipt.')
        return
    # Source-Defizit → zuerst Endkontrolle (Quote), dann Deploy.
    # Public-only-Defizit → Deploy reicht (CDN/Build).
    now = dt.datetime.now(dt.timezone.utc)
    if source_deficit and now.weekday() in {0, 2, 4}:
        gh('workflow', 'run', 'kadenz-endkontrolle.yml', '--ref', 'main')
    gh('workflow', 'run', 'deploy.yml', '--ref', 'main')
    if (not source_deficit) and now.weekday() in {0, 2, 4}:
        # Public hinkt hinterher: Backstop noch einmal, falls Source
        # zwischenzeitlich durch parallelen Gate-Verwurf gelitten hat.
        gh('workflow', 'run', 'kadenz-endkontrolle.yml', '--ref', 'main')


# ===========================================================================
# Selbsttest (C6): Der Melder-Kanal ist selbst eine Wache
# ===========================================================================
PROBETAGE = (dt.date(2026, 10, 5),   # Montag – der Fehltag aus #610
             dt.date(2026, 10, 6),   # Dienstag – Ruhetag, Zustand bleibt rot
             dt.date(2026, 10, 7))   # Mittwoch – nächster Publikationstag

# Der eingefrorene Issue-Body aus #610 (vor dieser Änderung erzeugt: kein
# `Gemessener Tag:`-Marker, aber der Beleg-JSON trägt den Tag).
LEGACY_BODY = (MARKER + '\n## Auslieferungsziel nicht bestätigt\n\n'
               'UTC: 2026-10-06T14:15:07.340793+00:00\n\n'
               '- **Source LIVE:** 1/2\n'
               '- **Öffentlich geliefert:** 1/2\n\n'
               '```json\n{\n  "day": "2026-10-05",\n  "mode": "public",\n'
               '  "minimum": 2,\n  "source": [\n'
               '    "2026-10-02-preiswert-surfen"\n  ],\n'
               '  "delivered": [\n    "2026-10-02-preiswert-surfen"\n  ],\n'
               '  "errors": [],\n  "ok": false\n}\n```\n')


def _szenario(tag: dt.date) -> list[str]:
    fehler: list[str] = []
    body = _body({}, tag=tag.isoformat(), source=1, delivered=1, minimum=2,
                 tag_deficit=True, evidence='{}')
    if f'{BODY_TAG} {tag.isoformat()}' not in body:
        fehler.append('Der Issue-Body trägt den gemessenen Tag nicht sichtbar')
    if tag_aus_body(body) != tag.isoformat():
        fehler.append(f'Tag-Rücklese fehlgeschlagen: {tag_aus_body(body)!r}')
    if tag_aus_body(LEGACY_BODY) != '2026-10-05':
        fehler.append('Alt-Issue (#610) verliert seinen Tag')
    if zahlen_aus_body(LEGACY_BODY) != {'minimum': 2, 'source': 1,
                                        'delivered': 1}:
        fehler.append(f'Zahlen des Alt-Issues falsch: '
                      f'{zahlen_aus_body(LEGACY_BODY)}')
    if tag_aus_beleg({'day': '2026-10-05T00:00:00Z'}) != '2026-10-05':
        fehler.append('Beleg-Tag mit Zeitanteil wird nicht gelesen')
    if tag_aus_beleg({}) is not None or tag_aus_beleg(None) is not None:
        fehler.append('Leerer Beleg liefert einen Tag')

    # Die Entscheidungsmatrix – ein Kanal, drei Urteile.
    beleg_gleich = {'day': tag.isoformat()}
    beleg_fremd = {'day': (tag + dt.timedelta(days=2)).isoformat()}
    if abschluss_entscheidung(tag.isoformat(), beleg_gleich,
                              receipt_ok=True)[0] != 'schliessen':
        fehler.append('Beleg desselben Tages schließt nicht')
    if abschluss_entscheidung(None, beleg_gleich,
                              receipt_ok=True)[0] != 'schliessen':
        fehler.append('Issue ohne Tag + Beleg schließt nicht (Rückfall)')
    if abschluss_entscheidung('2026-10-05', beleg_fremd,
                              receipt_ok=True, zahlen={'minimum': 2,
                                                       'source': 1,
                                                       'delivered': 1})[0] \
            != 'quittung':
        fehler.append('Fremder Tag wird nicht quittiert')
    quittung = quittung_text('2026-10-05', {'minimum': 2, 'source': 1,
                                            'delivered': 1},
                             beleg_fremd['day'])
    for stichwort in ('2026-10-05', beleg_fremd['day'],
                      'verbucht, nicht behoben', '1/2'):
        if stichwort not in quittung:
            fehler.append(f'Quittung nennt {stichwort!r} nicht')
    if abschluss_entscheidung('2026-10-05', beleg_fremd,
                              receipt_ok=True)[0] != 'offen':
        fehler.append('Fremder Tag ohne Zahlen wird nicht offen gelassen')
    if abschluss_entscheidung('2026-10-05', {}, receipt_ok=True)[0] != 'offen':
        fehler.append('Beleg ohne Tag schließt oder quittiert')
    if abschluss_entscheidung('2026-10-05', beleg_gleich,
                              receipt_ok=False)[0] != 'offen':
        fehler.append('Roter Beleg benutzt einen Abschlusspfad')
    if abschluss_entscheidung('2026-10-05', beleg_fremd, receipt_ok=True,
                              zahlen={'minimum': 2, 'source': 0,
                                      'delivered': 0})[0] != 'quittung':
        fehler.append('Fehltag ohne Auslieferung wird nicht quittiert')

    # Tagesgenauer Beleg schlägt den generischen des Laufs.
    with tempfile.TemporaryDirectory() as tmp:
        alt = os.getcwd()
        os.chdir(tmp)
        try:
            Path('tmp').mkdir()
            Path('tmp/publication-receipt.json').write_text(
                json.dumps({'day': beleg_fremd['day']}), encoding='utf-8')
            Path(f'tmp/publication-receipt-{tag.isoformat()}.json').write_text(
                json.dumps(beleg_gleich), encoding='utf-8')
            if tag_aus_beleg(_receipt(tag.isoformat())) != tag.isoformat():
                fehler.append('Tagesbeleg hat keinen Vorrang')
            Path(f'tmp/publication-receipt-{tag.isoformat()}.json').unlink()
            if tag_aus_beleg(_receipt(tag.isoformat())) != beleg_fremd['day']:
                fehler.append('Rückfall auf den Lauf-Beleg fehlt')
            Path('tmp/publication-receipt.json').unlink()
            if _receipt(tag.isoformat()) != {}:
                fehler.append('Fehlender Beleg liefert kein leeres Ergebnis')
        finally:
            os.chdir(alt)
    return fehler


def run_selftest() -> int:
    if _uhr is None or _MITTAG is None:
        print('🛑 publication_incident-Selbsttest FEHLGESCHLAGEN:\n'
              '  - scripts/selftest_clock.py fehlt oder ist nicht '
              'importierbar –\n    ein Schließpfad ohne Uhr-Zwang ist eine '
              'Verabredung mit dem Kalender.')
        return 2
    errors: list[str] = []
    for tag in PROBETAGE:
        with _uhr(dt.datetime.combine(tag, _MITTAG, tzinfo=dt.timezone.utc),
                  _UHR_VERSCHOBEN, module=[sys.modules[__name__]]):
            errors += [f'[Testdatum {tag.isoformat()}] {e}'
                       for e in _szenario(tag)]
    if errors:
        print('🛑 publication_incident-Selbsttest FEHLGESCHLAGEN:')
        for e in errors:
            print(f'   - {e}')
        return 2
    print('✅ publication_incident-Selbsttest grün (3 Probetage, Uhr-Zwang): '
          'Schließen nur mit Beleg DESSELBEN Tages, fremder Tag wird als '
          'Quittung verbucht (nicht beschönigt), ohne Tag/Zahlen bleibt das '
          'Issue offen (fail-closed), der Alt-Body aus #610 trägt seinen Tag.')
    return 0


def _cli() -> int:
    ap = argparse.ArgumentParser(description='Auslieferungs-Incident-Kanal')
    ap.add_argument('--selftest', action='store_true')
    args = ap.parse_args()
    if args.selftest:
        return run_selftest()
    main()
    return 0


if __name__ == '__main__':
    raise SystemExit(_cli())
