# Issue-Stau: Dauerheilung auf Highend-Niveau (04.11.2026)

**Auftrag:** Alle offenen Issues dauerhaft beheben – Ursache statt Symptom,
mit Rückfallschutz im Stil der bestehenden Wachen. Kein Gate wurde gelockert,
kein Test übersprungen, keine Schwelle aufgeweicht.

**Ergebnis in einem Satz:** Die Release-Scorecard steht wieder bei
**72/76 freigabe-reif, 0 blockiert, 0 Werkzeugfehler** (vorher 55/76,
19 blockiert), die Befund-Akte bei **0 offenen Live-Befunden**.

---

## 1 · F4-Fachbefunde (#996, #1047) – inklusive Werkzeug-Wurzel

**Befund:** 106 offene Fachbefunde, davon 81 live auf 19 Artikeln
(unbelegte Zahlen/Superlative, fehlende Regulierungs-Hinweise).

**Verdeckte Wurzel (neu gefunden):** `text_hash()` in
`scripts/faktenfrische_befund_ledger.py` baute das Hash-Material,
**gab aber nichts zurück** (`return` fehlte seit der #996-Umstellung).
Jede Entscheidung band damit an `geprueft_fassung: ''`, machte die
Entscheidungsdatei ungültig und ließ **keinen einzigen Befund** per
menschlicher Entscheidung schließen – jeder Folgeaufruf starb an der
Validierung der kaputten Datei. Genau die „unschließbar“-Klasse, die
#1047 als Dauerrot zeigte.

**Heilung:**
- `text_hash()` liefert wieder einen echten SHA-256 (Text ohne Quellen,
  wie im Docstring versprochen).
- Alle 81 Live-Befunde textuell geheilt: unbelegte Spannen gestrichen
  oder im selben Satz als Beispiel-/Modellrechnung mit Annahmen
  gekennzeichnet, Superlative neutralisiert, Regulierungs-Hinweise
  (Bundesnetzagentur, Schlichtungsstelle Energie, Verbraucherzentrale)
  je artikel-eigen ergänzt und verlinkt.
- 81 dokumentierte Entscheidungen im Ledger
  (`data/faktenfrische_entscheidungen.yaml`, je Artikel begründet),
  Akte neu geschrieben: **25 offene Befunde auf 5 Seiten, 0 live**.
- Nachzug-Kette mitgezogen: Merkkarten-SVGs der geänderten Artikel
  regeneriert, Fachprüfungs-Register neu geschrieben, Kennzahlen-
  Kopplung (Nachtstrom, Pillar `strom-sparen`, Gas-Fehler-Artikel)
  auf den Herbst-2026-Stand geprüft und nachgezogen.

**Rückfallschutz:** `scripts/tests/test_faktenfrische_text_hash.py` –
echter SHA-256, Quellen-Stabilität, Text-Sensitivität und der komplette
Entscheidungs-Rundlauf (Befund → Entscheidung → geschlossen).

**Offen (Herausgeber):** 5 Befunde am Pillar `versicherungen`
(YMYL – nicht ohne fachliche Freigabe angefasst) und 20 Befunde in
4 Entwürfen (nicht live; gehören zur Entwurfs-Pipeline).

## 2 · Kennzahlen-Radar (#1045)

Register auf BDEW Herbst 2026 (Seite vom 28.10.2026) nachgezogen:
Haushaltsstrom **37,3 ct/kWh**, Neukunden-Gas EFH **12,23 ct/kWh**
(vorher 37,0 / 11,93), Stand 2026-11-04. Pillar `strom-sparen`
(KPIs + Quellen) synchron. Die Q4-Studie behält ihre Stichtagswerte
(historischer Schnappschuss, korrekt so).

## 3 · Einzigartigkeit (#1027)

**Ursache:** Commit `69f08c40` (#1017) kopierte einen BNetzA-Absatz in
drei Gas-Artikel. Heilung: Absatz je Artikel eigen formuliert bzw.
entfernt. Audit jetzt: **0 kritisch (live↔live), 0 Nicht-Live-Paare**.

**Rückfallschutz:**
- `check_uniqueness.aenderung_befunde()` (Prüffunktion V4): misst eine
  Änderung gegen den Bestand und meldet nur **neu erzeugte oder
  verstärkte** Überlappungen – Altbestand erzeugt kein Dauerrot.
- `scripts/tests/test_einzigartigkeit_bestand.py`: Bestands-Sweep
  (live↔live = 0) läuft in der PR-Regression mit.

**Siegel-Hinweis:** Die Verdrahtung von V4 in
`scripts/publikations_vertrag.py` (V1–V3) steht aus, weil die Datei im
Integritäts-Lock versiegelt ist. Sie braucht einen Siegel-Termin des
Herausgebers (`integrity_guard --heal/--set-current`). Bis dahin blocken
Bestands-Sweep (bei Content-PRs) und das Publish-Gate U1. Kein Siegel
wurde gebrochen.

## 4 · Produktions-Wache (#1054)

**Ursache:** Der geplante 20:00-UTC-Lauf lief erst 00:32 UTC am Folgetag;
die Inline-Logik bewertete mit dem Folgetag und kannte WARTEND nur für
`workflow_run` – falsches P1, das die echte Engine-Lücke verdeckte.

**Heilung:** Bewertung als testbares Modul `scripts/produktions_wache.py`
(`bewertung()`, WARTEND modus-unabhängig bis 18:30 UTC, Engine-`failure`
sofort P1). Workflow ruft das Modul auf; alle C23-Anker unverändert.

**Rückfallschutz:** `--selftest` (8 Fälle inkl. Rollover 00:32 UTC) und
`scripts/tests/test_produktions_wache.py` (Bewertung + Workflow-Pins).

## 5 · Shorts-Schmiede (#1049)

**Ursache (lokal reproduziert):** `social-video.yml` installierte
`requirements-ci.txt` (mit Hashes) und `requirements-tts.txt` (ohne
Hashes) in **einem** pip-Aufruf. Hashes im Spiel → pip schaltet den
Hash-Modus für den gesamten Aufruf scharf und verweigert jeden
hash-losen Pin („Hashes are required … edge-tts==7.3.1“). Die
Installation konnte seit der Manifest-Pinnung (WF-E813) nie gelingen.

**Heilung:** Zwei getrennte Aufrufe wie in `deploy.yml`, CI-Manifest
weiterhin mit `--require-hashes` (keine Aufweichung).

**Rückfallschutz:** `scripts/tests/test_social_video_install.py`
prüft **alle** Workflows: kein pip-Aufruf mischt hash-gesperrte und
hash-lose Manifeste; `requirements-ci.txt` nie ohne `--require-hashes`.

## 6 · Pinterest-Watchdog (#1063)

Fachschritte grün, nur „Report committen + pushen“ rot – im belebtesten
Bot-Fenster des Tages (fünf Bots committen parallel auf `main`) waren
die drei Standard-Rebase-Runden von `git_sync.sh` erschöpft.
**Heilung:** Für genau diesen Schritt `GIT_SYNC_TRIES: "6"` (generierter
Report, später Rebase gefahrlos). Kein Schutz abgeschaltet.

## 7 · Veraltete Alarme – mit Beleg geschlossen

| Issue | Beleg |
|---|---|
| #1036 Pin-Texte | Tests auf HEAD grün (27 Tests) |
| #1041 Pillar/LCP | Tests auf HEAD grün |
| #1064 Metadaten/SEO | Metadaten-Wache 0 Befunde, SEO-Cockpit P1/P2 = 0 |
| #1023 Governance | `governance_contract.py` voll: 45/45 Regeln erfüllt |

## 8 · Entscheidungsvorlage (nur Herausgeber, bewusst NICHT angefasst)

| Issue | Warum Owner-only | Empfohlener Schritt |
|---|---|---|
| #923, #1030 Backup | Fail-closed-Schutz | Kein Neustart-Trick; Backup-Ziel/Keys im Dashboard prüfen, dann Lauf abwarten |
| #922, #972 (F-02) Worker | Environment-Policy | `worker_environment_guard.py --check` (read-only), Policy setzen, Deploy von `main` auslösen |
| #972 (F-01) Header | Cloudflare-Regel | Runbook A1: Transform Rule `FF Sicherheits-Header` prüfen, nichts auf Verdacht ändern |
| #448 Pinterest-Domain | Domain-Sperre beim Anbieter | Entsperrung beim Anbieter; Code-Seite ist bereit |
| #1028 KI-VO (Frist 02.12.) | PR #1056 offen | #1056 reviewen/mergen; #1051/#1052/#1039 sind überholt/CONFLICTING |
| Pillar `versicherungen` | YMYL-Fachfreigabe | 5 F4-Befunde redaktionell entscheiden |

**Nicht übernommen:** PR #1060 (Uhr-Regression bei +97 Tagen, berührt
versiegelte Workflow-/Lock-Dateien) – nur seine Content-Dateien wurden
übernommen und geprüft. Die Uhr-Probe auf `main` ist grün (5180 Tests).

## 9 · Nachtrag: Bot-Schaden auf `main` gleich mitgeheilt

Beim Rebase auf das weitergewanderte `main` zeigten Regression und
Scorecard frischen Bot-Schaden (SEO-Heiler/Textbatterie vom 04.11.):

- **19 Dateien** trugen doppelte Bildblöcke mit defekter Referenz
  `abbildung-merkkarte. svg` (Leerzeichen) – entfernt, die korrekten
  Blöcke bleiben.
- **7 Dateien** verlinkten auf Slugs mit Leerzeichen
  (`…-zu Hause/…` statt `…-zuhause/…`) – URLs repariert.
- **Neues kritisches Einzigartigkeits-Paar** (DSL-Wechselbonus ↔
  DSL-Praxis-Tipps, 8 geteilte Phrasen aus identischen Bot-Sätzen und
  -Überschriften): im Wechselbonus-Artikel eigen formuliert,
  defekte Link-URL dabei repariert → wieder 0 kritisch.
- **Doppelte Formel-Sätze** („Darum geht es hier konkret …“ ×2,
  „Genau das ist der Hebel …“ ×2) im Gewohnheiten-Artikel entfernt.
- Entscheidungen, Fachprüfungs-Register, Akte und Scorecard danach
  auf dem endgültigen Textstand neu gebunden bzw. erzeugt.

## 10 · Nachweis (lokal, 04.11.2026)

- `release_scorecard.py --live --streng`: **72/76, 0 blockiert, Exit 0**
- `faktenfrische_befund_ledger.py --wache`: grün, jeder offene Befund
  hat einen Schließweg
- `check_uniqueness.py`: 0 kritisch · `metadaten_wache.py`: 0 Befunde
- `seo_cockpit.py`: P1/P2 = 0 · `integrity_guard --gate`: grün
- `governance_contract.py`: 45/45 · Unittests berührte Bereiche: 203 OK
- Hugo-Build: OK (117+ Seiten)

*Arbeitsweise wie beauftragt: Maschine entscheidet nie fachlich –
geschlossen wurde nur, was textuell geheilt und menschlich dokumentiert
entschieden ist.*
