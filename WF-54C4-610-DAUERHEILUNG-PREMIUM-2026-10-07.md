# Öffentliche Auslieferung WF-54C4 · #610 – Dauerheilung

**Datum:** 07.10.2026
**Auslöser:** Der Kanal „P1: Öffentliche Artikel-Auslieferung unter Mindestziel“
(Issue **#610**, Marker `<!-- publication-delivery-slo -->`) meldete für den
**05.10.2026**:

    Source LIVE: 1/2 · Öffentlich geliefert: 1/2
    Beleg: {"day": "2026-10-05", "mode": "public", "minimum": 2,
            "source": ["2026-10-02-preiswert-surfen-…"],
            "delivered": ["2026-10-02-preiswert-surfen-…"],
            "errors": [], "ok": false}
    UTC 2026-10-06T14:15:07Z

Der Tag selbst ist vorbei und wird nicht nachdatiert (Betriebsvertrag). Die
Reparatur gilt den zwei Lücken, die den Fehltag **unsichtbar** gemacht und den
**Vorrat verbraucht** hätten.

## Befund

**Die Nacht des 05.10.2026, belegt aus dem Baum**
(`data/audit/2026-10-05.jsonl`, `data/content_fingerprints.jsonl`,
`data/reserve-intake.json`, `data/reserve-custody.json`):

| Zeit (UTC) | Ereignis |
|---|---|
| 21:27/21:59 | Der am 05.10. übernommene Reserve-Kandidat `2026-09-10-energie-update-…` steht als Tageskandidat in der Scorecard (`live` 39, `freigabe_reif` 32, `blockiert` **0**). |
| 21:51:31 | Fingerabdruck der Fassung A: 1557 Wörter. |
| 22:16:17 | Fingerabdruck der Fassung B: 1554 Wörter. |
| 22:20 | „Redaktions-Standard neu“ (WF-6F7F) schreibt den Text KI-geheilt um – Flesch 44,3 und R7-Intro-Formel; das ist die Ursache, die #607 adressiert. |
| 22:41:03 | `publish_gate`: `gated: [energie-update]`, `demoted: [energie-update]` – der Tag steht bei **1/2**, und der einzige Nachschub ist wieder Entwurf. |
| Nacht | Sichtung/Janitor lesen `reserve_published` + `draft: true` als **Rückläufer** („der Inhalt lebt live weiter, der Entwurf ist die Kopie“) und löschen den Text. Er war **nie öffentlich**. |

Für den 06.10.2026 (Ruhetag) existierte danach kein Material mehr, das den
nächsten Publikationstag hätte tragen können; der Vorrat stand am 07.10. bei
*Ziel 6, bereit 2* (`data/reserve-readiness.json`).

**Befund 1 – der Beweis gehörte niemandem.**
`scripts/publication_check.py` schrieb seinen Beleg bei jedem Lauf in dieselbe
Datei `tmp/publication-receipt.json` (CI-Artefakt, lokal überschrieben), und
`scripts/publication_incident.py` schloss das offene Issue bei jedem grünen
Lauf – ohne zu prüfen, welchem Tag der Beleg gehört. Die Auslieferungs-SLO
misst aber immer den **jüngsten** Publikationstag: Das Ticket über den
05.10.2026 wäre am 07.10. mit dem Beleg des 07.10. geschlossen worden. Der
Fehltag wäre nie verbucht worden, und der Beweis wäre mit der Datei
verschwunden. Ein grüner Fremdtag darf keinen roten Tag abräumen.

**Befund 2 – „Rückläufer“ war eine Behauptung.**
Die Signatur `reserve_published` + `draft: true` entsteht schon durch eine
späte Gate-Zurückstufung (`publish_gate` → `park_state.hold`). Sichtung und
Janitor behandelten sie als **Beweis**, dass der Inhalt öffentlich weiterlebt,
und löschten sofort. Wer nicht beweisen kann, dass ein Text veröffentlicht
wurde, darf ihn nicht als Kopie vernichten – der Verlust trifft nicht nur den
einen Tag, sondern den Vorrat der folgenden.

Drittens konnte die Endabnahme aufhören, obwohl Material da war: Es gab genau
einen (doppelten) Nachfüll-Durchgang. Stufte der eigene Abschluss-Lauf den
frischen Nachschub erneut zurück, endete der Tag wie am 05.10.: 1/2.

## Dauerhafte Reparatur

1. **Tagesgebundener Beleg** (`scripts/publication_check.py`,
   `beleg_schreiben()`): zusätzlich zur Lauf-Datei entsteht
   `tmp/publication-receipt-<tag>.json` und eine versionierte Zeile in
   `data/publication-delivery-history.jsonl` (`ts`, `day`, `mode`, `minimum`,
   `maximum`, `source`, `delivered`, `ok`, `errors`). Der Workflow
   `publication-delivery.yml` lädt jetzt `tmp/publication-receipt*.json` hoch.
   Die Historie ist append-only und ohne Netz schreibbar; ein Fehler dort ist
   ein Hinweis, kein Gate (der Beleg des Tages bleibt der harte Nachweis).
2. **Tagesgebundener Abschluss** (`scripts/publication_incident.py`,
   `abschluss_entscheidung()`): Geschlossen wird nur mit einem Beleg
   **desselben** Tages. Ist der gemessene Tag weitergezogen, wird der Fehltag
   als **Quittung** verbucht – mit Tag, Zahlen und dem ausdrücklichen Vermerk
   „verbucht, nicht behoben“ plus Verweis auf die verbotene Nachdatierung.
   Ohne Tag oder ohne Zahlen bleibt das Issue offen (fail-closed). Der
   Issue-Body führt den gemessenen Tag sichtbar (`- **Gemessener Tag:** …`);
   der rote Pfad aktualisiert ihn bei jedem Lauf, damit die Akte ihren Tag
   mitführt. Alt-Issues (wie #610) liefern den Tag aus dem eingefrorenen
   Beleg-JSON im Body.
3. **Nachweis-Pflicht beim Rückläufer** (`scripts/reserve_pool.py`,
   `scripts/reserve_custody.py`, `scripts/reserve_janitor.py`):
   `live_zwilling()` sucht den LIVE-Artikel mit demselben Thema (gleicher
   Slug-Rumpf **oder** gleicher normalisierter Titel). Ohne Zwilling ist der
   Entwurf kein Rückläufer, sondern **nicht ausgelieferter Nachschub**:
   die Sichtung führt ihn als `ruecklaeufer_ohne_nachweis`, der Janitor löscht
   ihn nicht (Klasse `ohne-nachweis`, Berichtsfeld `wiederhergestellt`) und
   `zurueck_in_den_pool()` holt ihn zurück in den Vorrat – mit Zeile in
   `data/reserve-history.jsonl`. Mit belegtem Zwilling bleibt es bei der
   Sichtung, jetzt mit dem Zwilling im Löschgrund.
4. **Konvergente Nachfüllung** (`scripts/publication_release.py`,
   `refill_until_min()`, `sichere_verworfene_nachschuebe()`): begrenzte Runden
   (Standard 3) statt eines Durchgangs. Jede Runde räumt verworfenen Nachschub
   zurück in den Vorrat und greift den nächsten Kandidaten; eine Rettung zählt
   als Fortschritt. Abbrüche: Mindestziel erreicht, kein Fortschritt (dann
   ausdrücklich „ehrliches Defizit“), Runden erschöpft, Off-Day (eine Runde,
   die nichts tun darf, wird gar nicht erst gestartet). Verworfen wird nur mit
   byte-identischer Wiederherstellung (Erbe von #287).
5. **Governance C26 („Ein Beleg gehört seinem Tag“, #610)** in
   `scripts/governance_contract.py`: prüft Tagesbeleg + Historie, den
   tagesgebundenen Schließpfad (Schließen ausschließlich über
   `schliessen|quittung`), die Konvergenz, die Nachweis-Pflicht beim Rückläufer
   und das Tages-Artefakt im Workflow – mit **fünf Kunstbefunden** im
   Kontrakt-Selbsttest (tagesblinder Schließpfad, fehlender Tagesbeleg,
   entfernte Nachweis-Pflicht, entfernter Rückweg im Janitor, fehlendes
   Artefakt). `publication_incident.py` steht zusätzlich in `GUARDS`; sein
   Selbsttest läuft im vertraglichen Minimum und in den Uhr-Proben
   (+97/+1461 Tage) des `selftest_runner.py`.

Kein Qualitätsgate wurde abgesenkt, kein Mindestwert gesenkt, kein
Veröffentlichungsdatum nachgetragen.

## Nachweis

- `python3 scripts/publication_incident.py --selftest` → **grün** (3 Probetage
  mit Uhr-Zwang: Schließen nur mit Beleg desselben Tages, fremder Tag wird
  quittiert, ohne Tag/Zahlen offen, Alt-Body aus #610 trägt seinen Tag).
  `selftest_clock.py --trap … --offset 97` und `--offset 1461` → grün.
- `python3 -m unittest scripts.tests.test_publication_reliability` →
  **Ran 50 tests, OK** (20 neue Regressionstests:
  `NachschubOhneNachweisTests`, `KonvergenzTests`, `BelegJeTagTests`).
- `python3 -m unittest discover -s scripts/tests` → **Ran 1978 tests,
  OK (skipped=23)**.
- `python3 scripts/reserve_pool.py --selftest`,
  `reserve_custody.py --selftest`, `reserve_janitor.py --selftest`,
  `publication_release.py --selftest`, `reserve_intake.py --selftest` → grün.
- `python3 scripts/governance_contract.py --selftest` → **bestanden (C1–C26
  mit Kunstbefunden)**; `--quick` und der volle Lauf → „alle 25 Regeln prüfen
  in beide Richtungen“.
- `python3 scripts/selftest_runner.py` → siehe Laufprotokoll; der neue Melder
  wird entdeckt (quotierte Kennung) und läuft in Basis + Uhr-Proben; der
  Arbeitsbaum bleibt unverändert (C15: ein Prüf-Aufruf heilt nicht).
- Pull Request **#620** (Branch `arena/b0de38e3-franksfinanzcheck-blog`):
  Qualitäts-Gate (Build + interne Links), Publication reliability regression
  tests, Integritäts-Lock (PR-Gate), CodeQL (python/javascript) und
  Klartext-Wache → **alle grün**.
- Erster echter Beleg der neuen Historie (07.10.2026, source):
  `{"ts": "2026-10-07T12:41:07Z", "day": "2026-10-07", "mode": "source",
  "source": 2, "delivered": 2, "ok": true}` –
  `data/publication-delivery-history.jsonl`.

**Ergebnis:** Der Fehltag vom 05.10.2026 bleibt ehrlich verbucht. Ab jetzt gilt:
Ein grüner Fremdtag kann ihn nicht mehr stillschweigend schließen, ein
zurückgestufter Nachschub wird nicht mehr als „Kopie“ vernichtet, und die
Endabnahme füllt konvergent nach, solange Material im Vorrat liegt – oder sie
meldet das Defizit ausdrücklich als ehrliches.
