# 🗞️ Governance-Härtung — Antwort auf Report #206 (07.09.2026)

**Auftrag:** Blog dauerhaft zuverlässiger und robuster machen auf dem Niveau einer
Profi-Agentur — und den Inhalt des automatisch erzeugten „Governance-Report:
Redaktionelle & technische Handlungsfelder" (#206) als *Fehler* beseitigen, nicht
als Dokumentation wegschreiben.

**Ausgangslage:** Der Report war keine Schlagzeile über den Blog. Er war eine
Schlagzeile über die Steuerung selbst: Der wöchentliche Governance-Lauf meldete
seit Wochen dieselben „Handlungsfelder", die sich nicht aus Messwerten ergaben,
und produzierte dabei Duplikate (#145 → #206). Für einen Betrieb mit 30+
Automatisierungen ist das der teuerste Fehler, den man haben kann: **Alarm-Müdigkeit**.
Ein roter Befund, der zwischen drei Scheinalarmen liegt, wird übersehen.

Die Analyse unten ist so geschrieben, wie eine Agentur ein Post-Mortem abgibt:
Ursache → Beleg → Maßnahme → Nachweis, dass die Maßnahme wirkt und der Fehler
nicht zurückkommen kann.

---

## 1 · Ursachenanalyse (Belege aus dem Bestand)

| # | Sichtbar in #206 | Ursache im System | Beleg |
|---|---|---|---|
| U1 | „Core-Web-Vitals **AMBER** 🟡" in der Scorecard, im selben Lauf meldet `cwv_guard.py` **GREEN** | Die Scorecard war **vor** den Messschritten eingebaut und las `data/cwv_manifest.json` des Vorlaufs. Die Scorecard ist aber ein Verbraucher dieser Manifeste — sie kann nichts Älteres erfinden als „aktuell". Folge: −7 Punkte Score, eine gelbe Zeile und eine Empfehlung („Covers als AVIF/WebP …"), die ins Leere liefen. | `premium-governance.yml` v1: Schritt-Reihenfolge Scorecard (Index 4) vor Decay/CWV/Secrets (5/6/7) |
| U2 | `PINTEREST_ACCESS_TOKEN` **UNBEKANNT** → „kein Erfolgs-Log (ausstehend…)" | Der einzige Lieferant des Nachweises (`pinterest-ai.yml`, Schritt „Pinterest-Secret-Erfolg vermerken") läuft seit dem 20.08.2026 **nur noch manuell** (`workflow_dispatch`) — die Automatisierung hat Pinnen an den RSS-Auto-Publish abgegeben. Der Nachweis wurde also nie mehr geschrieben. Die Wache meldet „untracked" = AMBER, der Workflow wertete AMBER als Fehlschlag ⇒ Issue. | `pinterest-ai.yml` Trigger-Zeile, `SECRETS-REPORT.md` (v1) |
| U3 | `GROQ_API_KEY` / `GEMINI_API_KEY` „OK (6d)" | **Nachweis-Wäsche:** der Governance-Lauf vermerkte Erfolg für Keys, die er in diesem Lauf nie benutzt (er misst nur). Die Wache bestätigte sich selbst — der Status war eine Aussage über den Runner, nicht über den Key. | `premium-governance.yml` v1, Schritt „Erfolgreiche Secrets vermerken" |
| U4 | Issue #145 und #206 mit identischem Titel, eine Woche apart | Das Issue wurde an **Exit-Codes** aufgehängt (`steps.*.outcome == 'failure'`). `awin_provisions.py`/`click_attribution.py`/`pinterest_perf_feedback.py` melden „keine Daten" aber mit Exit 1 — eine Datenlage ist kein Fehler. Außerdem: immer `issues.create`, kein Dedupe, kein Schließen bei Grün. | Issue-Block v1 (actions/github-script), `return 1 if unmatched else 0` |
| U5 | „Affiliate-Klicks 0 über 0 Artikel", „Awin 0.00 €" | Die Monetarisierungs-Schleife hatte als einzige Datenquelle einen **manuellen Dashboard-Export**. Ohne Automatik steht dort für immer 0. Die Zeilen waren 🟡 markiert, als wäre das ein Content-Problem. | `data/umami_clicks.json` = `[]`, `data/pinterest_perf.yaml` `entries: []` |
| U6 | (verdeckt) CWV könnte grün melden, ohne dass gebaut wurde | `hugo --minify > /dev/null 2>&1 \|\| true` verschluckt jeden Build-Fehler. Der Wächter fand dann ein leeres/altes `public/`, keine Abweichung, Ausgabe: **GREEN**. Scheinsicherheit ist schlimmer als ein Alarm. | Build-Schritt v1 |
| U7 | (verdeckt) State-Dateien aus Parallel-Läufen | `data/secrets_state.json` wurde von vier Workflows mit `open(..., "w")` geschrieben — ohne Sperre, ohne atomaren Austausch. Ein Riss im JSON hätte die Wache mit Traceback sterben lassen (Exit ≠ 0 ⇒ wieder ein Issue). | `secrets_age_guard.py` v1 `_save_state` |
| U8 | (verdeckt, #205-Klasse) | Reports, die `.gitignore` ignoriert, wurden mit `git add` gestagt → harter Abbruch unter `set -e`. | Behoben am 07.09. in `frankautoops-report.yml`; Regel jetzt festgeschrieben (C8) |

---

## 2 · Maßnahmen

### 2.1 Einordnen: Messen → Sehen → Bewerten → Melden

Der Lauf hat jetzt vier Phasen mit klaren Verträgen dazwischen. Das ist die
eigentliche Behebung von U1/U4 — nicht das Nachziehen einzelner Zahlen.

```
0 Preflight  →  1 Messen  →  2 Sehen (Scorecard)  →  3 Bewerten (Gate)  →  4 Melden (1 Issue)
```

* `scripts/governance_gate.py` **(neu)** — der Schiedsrichter. Jeder Messschritt
  meldet `--emit <schritt> --report <datei> --exit <rc>` in ein Ledger
  (`data/governance_status.json`, Verlauf `data/governance_history.jsonl`).
  Der Gate klassifiziert gegen eine dokumentierte Policy und entscheidet
  `report` / `close` / `none`. Body-Bau inklusive: kuratierte Befundtabelle statt
  Roh-Log-Schrott. Zwei Extras für den Betrieb:
  * `--rehearse` — Trockenlauf über den Bestand, schreibt nichts, zeigt exakt die
    Entscheidung, die der Lauf treffen würde (ein Test, der die Policy beweist,
    ohne ein Issue zu riskieren).
  * `--reset` — ein Ledger gilt nur für den Lauf, der es gefüllt hat. Altlasten
    (vergessener Schritt, umbenannt, abgebrochen) können nicht mehr wöchentlich
    dasselbe Issue auslösen; verworfene Einträge bleiben als Hinweis sichtbar.
* **Issue-Policy** (Regel C4): `gh issue list --label governance` → vorhandenes
  Issue **aktualisieren** (Body nur bei verändertem Fingerabdruck, sonst Kommentar),
  sonst neu anlegen; bei meldungsfreier Lage **schließen**. Der Fingerabdruck
  (`sha256` über Schritt/Code/Anzahl) macht Melden idempotent.

### 2.2 Secrets-Wache v2 — von „vorhanden" zu „bewiesen" (U2, U3, U7)

`scripts/secrets_age_guard.py`:

* **Live-Probe `--verify`**: ein Head-call pro Kanal — Pinterest `GET /v5/users/me`,
  Mastodon `GET /api/v1/accounts/verify_credentials`, Groq `GET /v1/models`,
  Gemini `GET /v1beta/models`, Umami `GET /v1/websites`. Erfolg wird nur bei
  HTTP 200 vermerkt. Abgelaufener Token (401/403) ⇒ **rot** (`dead`) — der Alarm,
  den die Wache von Anfang an liefern sollte – statt einer Alterungsvermutung.
* **Netzwerkfehler sind keine Gesundheit**: `unreachable` ⇒ AMBER im Report, aber
  ℹ️ in der Policy. Sonst hätte ich den Dauer-Alarm nur durch einen neuen ersetzt
  (API-Gate, Wartungsfenster). Eskalation läuft über die Altersregel: bleibt der
  Nachweis aus, kippt `stale` auf **rot**.
* **Alarm-Kontinuität**: ein in einem Vorlauf abgelehnter Token bleibt rot, bis ein
  Live-Check ihn bestätigt. Ein einzelner Lauf ohne Netzwerk „heilt" den Kanal nicht.
* **Nachweis-Provenienz**: `--record-success <VAR> --proof-by <workflow>`; ein
  Nachweis aus einem Workflow, der das Secret nicht nutzt (`proof_by`-Whitelist in
  der Registrierung), wird als `foreign_proof`-Hinweis entlarvt statt als Grün.
* **Robustheit**: alle State-Schreibungen atomar (`tmp` + `os.replace`, `fsync`) und
  mit `flock` (bei fehlendem `fcntl` wird weitergearbeitet, nicht abgestürzt);
  Datumsfelder werden tolerant geparst; eine beschädigte State-Datei wird gesichert,
  neu begonnen und als Befund gemeldet — nicht als Traceback.
* **Registry erweitert**: `UMAMI_API_TOKEN` (optional) ist jetzt ein registrierter
  Kanal, damit „Kanal nicht eingerichtet" und „Kanal tot" verschiedene Meldungen sind.

`data/secrets_state.json` v2-Felder (rückwärtskompatibel gelesen):
`last_verified`, `verify` (`ok|dead|unreachable`), `verify_detail`, `proven_by`,
`quality` (`proven|declared|declared_foreign`).

### 2.3 Scorecard: eine Wahrheit mit Herkunft (U1, U4, U5)

`scripts/editorial_scorecard.py`:

* CWV-Zeile liest Manifest **und** Alter: `STALE (nd)` bzw. „nicht gemessen" bzw.
  „nur static/ (Build ausgefallen)" ⇒ ⚪, Abzug 3 statt 7, Empfehlung nennt die
  Messlücke statt einer erfundenen Performance-Diagnose.
* Secrets-Zeile wertet den Report des Wächters (Policy), nicht eine eigene
  Zweitrechnung; ein v1-Report ohne `Nachweis`-Spalte wird als Format-Altlast
  erkannt (⚪ + Hinweis) — Verbraucher dürfen nicht strenger sein als Erzeuger.
* Lampen ehrlich: Entwürfe `0 → 🟢` (war dauerhaft 🟡), Monetarisierung ohne Daten
  `⚪` (war 🟡), mit Daten nach Schwelle 🟢/🟡.
* Neu: Abschnitt **„Datenlagen (Messabdeckung)"** — Kennzahl, Quelle, Stand,
  Bewertung. Die erste Frage eines Chefredakteurs ist nicht „wie gut ist die Zahl",
  sondern „woher kommt sie und ist sie frisch".
* Neu: Trend aus `data/scorecard_history.jsonl` („Vorlauf 83 → 90 (+7)"). Ein Score
  ohne Verlauf ist eine Meinung.
* Neu: Empfehlungen für die Previously-ignorierten Signale (Lesbarkeit < 70,
  Umsatz-Pipeline) — Abzug ohne Handlungsempfehlung ist Mobbing an der Automation.

### 2.4 CWV-Wächter: „nicht gemessen" ≠ „in Ordnung" (U6)

`scripts/cwv_guard.py`: `--strict-build` (CI-Modus), `--min-html`, Befunde
`build_missing` / `build_thin`, Manifest-Feld `build_measured`, Verlauf
`data/cwv_history.jsonl` + `--trend`, atomares Manifest. Exit 1 nur noch bei
tatsächlicher Abweichung (rot/gelb), reine Hinweise (info) lassen den Lauf ruhig.

### 2.5 Umsatz-Datenpipeline statt Bauchgefühl (U5)

`scripts/umami_clicks.py` **(neu)**: holt `affiliate_click`-Events aus Umami
(Cloud `https://api.umami.is/v1` mit `x-umami-api-key`, self-hosted via
`UMAMI_API_BASE`), verarbeitet die Versionen unterschiedlichen API-Forms mit
(`eventProperties`-Liste wie flache Felder), aggregiert nach
(slug, article, pillar) und schreibt `data/umami_clicks.json` im Schema, das
`click_attribution.py` bereits konsumiert. Dazu `data/umami_clicks.meta.json`
(Stand, Quelle, Grund).

* **Website-ID aus `hugo.toml`**, nicht aus einem zweiten Secret — eine Wahrheit.
* Kein Token/keine ID ⇒ dokumentierter Skip (`status: skipped`, Grund), nie eine
  Schein-Null. Bei API-Störung bleibt der letzte Bestand stehen.
* Token-Material wird aus jeder Fehlermeldung redigiert (`_redact`).

### 2.6 Dauer der Maßnahmen (damit es nicht zurückkommt)

* `scripts/governance_contract.py` **(neu)** — neun Regeln als ausführbarer
  Vertrag, geprüft im Qualitäts-Gate (jeder Push/PR) **und** als Preflight im
  Governance-Lauf:

  | Regel | Vertrag |
  |---|---|
  | C1 Reihenfolge | Scorecard (View) nach allen Messschritten — U1 für immer zu |
  | C2 Bau-Grundlage | kein `\|\| true` am Hugo-Build; Ergebnis geht ans Gate |
  | C3 Messkette | jede Gate-Kennung wird aus einem Workflow gefüttert |
  | C4 Issue-Policy | Entscheidung nur über `--decide`; Dedupe-Pflicht; Close-Pfad Pflicht |
  | C5 Nachweis | `--record-success` nur mit `--proof-by`, nur registrierte Secrets, nie im Governance-Lauf selbst |
  | C6 Selbsttests | alle zehn Wachen haben `--selftest` und bestehen |
  | C7 Datenkonsistenz | Manifest ↔ Report ↔ Scorecard zeigen dieselbe Ampel (oder ⚪ mit Begründung) |
  | C8 Commit-Hygiene | kein `git add` auf ignorierte, unversionierte Dateien (#205) |
  | C9 Leak-Schutz | kein Token-Material in Reports/`data/*.json` |

  Der Checker prüft in **beide Richtungen**: er meldet Fehler, und er meldet
  Scheinsicherheit. Die `--selftest`-Fälle füttern ihm Kunst-Workflows (vorher/nachher),
  damit die Regeln nicht verstubbt werden.
* `pinterest-watchdog.yml`: tägliche Live-Probe des Pinterest-Tokens (der Kanal mit
  30-Tage-Verfall wird nicht mehr wöchentlich, sondern täglich bewiesen).
* `pinterest-ai.yml` / `social-ai.yml`: blindes Vermerken ersetzt durch
  `--verify-only … --quiet`; der Krypto-Key behält `--record-success` mit `--proof-by`.
* `.gitignore`: `*.lock`, `data/*.tmp-*` (Laufzeit-Nebenprodukte der Wachen).

---

## 3 · Verifikation (alles nach dem Stand dieses Commits ausgeführt)

| Prüfpunkt | Ergebnis |
|---|---|
| Selbsttests der 10 Governance-Skripte (`--selftest`) | alle ✅ (`editorial_scorecard`, `cwv_guard`, `secrets_age_guard`, `decay_radar`, `governance_gate`, `governance_contract`, `umami_clicks`, `click_attribution`, `awin_provisions`, `pinterest_perf_feedback`) |
| Syntax aller `scripts/*.py` (`py_compile`) | ✅ |
| YAML-Parsing aller 34 Workflows (`yaml.safe_load`) | ✅ |
| `governance_contract.py` auf dem **vorherigen** Stand (HEAD~ = `2db88bc`) | 🔴 **28 Verletzungen** (C1×6, C2×2, C3×8, C4×4, C5×7, C7×1) |
| `governance_contract.py` auf dem neuen Stand (inkl. C6 mit Selbsttest-Läufen) | 🟢 0 Verletzungen |
| Rehearsal über den Bestand: `governance_gate.py --rehearse` | 🟢 Ampel INFO → Aktion `close` (6 Hinweise, 0 Befunde) — der bestehende Report #206 wird beim nächsten Lauf geschlossen, kein neuer öffnet |
| Simulierter Token-Ausfall (`verify=dead` im State) | 🔴 `dead` → Gate `report`, `--fail-on red` Exit 1, Issue-Body mit Runbook — der Alarm funktioniert, wenn er echt ist |
| Vorfall „Netzwerk bei der Live-Probe zu" (4 Proben URLError) | 🟢 ℹ️-Ampel INFO, Aktion `none` — kein Alarm aus Infrastruktur-Rauschen |
| Scorecard nach der Korrektur | **90/100 GREEN** statt 83/100 AMBER, ohne dass ein Artikel angefasst wurde |

Der letzte Punkt ist die Pointe: 7 der 17 Punkte Unterschied waren Messartefakte
(CWV-Stale 7, Secrets-Format 1, Lampen-Politik), kein Qualitätsverlust des Blogs.

## 4 · Betrieb — was du tun solltest (und was nicht)

1. **Nichts** zum Reparieren der Governance. Nach dem Merge:
   `gh workflow run "Premium-Governance"` — ein Lauf, der die Reports im neuen
   Format erzeugt, #206 schließt und das Ledger füllt.
2. **Einmalig 2 Minuten für den Umsatz-Hebel:** Umami → *User Settings* → *API* →
   Key erzeugen → `gh secret set UMAMI_API_TOKEN`. Ab dem nächsten Lauf stehen in
   Scorecard und `CLICK-REPORT.md` echte Klicks je Artikel/Pillar statt „Datenlage
   offen". (Anleitung: `docs/ANLEITUNG-UMAMI-ANALYTICS.md`.)
3. **Awin** bleibt bewusst CSV: Export nach `data/awin_transactions.csv`. Die API
   wäre möglich, aber ohne dokumentierten Zugriff wäre eine Anbindung ein zweiter
   stiller Kanal, der nie Daten liefert — und stille Kanäle sind genau die Klasse
   dieses Berichts.
4. Echte redaktionelle Baustellen, jetzt ehrlich ausgewiesen (nicht mehr als
   Technik-Alarm verkleidet): **Ø Lesbarkeit 53.3** (Ziel ≥ 70; Longlist in
   `python3 scripts/readability_check.py`), **1 Entwurf** in der Warteschleife
   (`python3 scripts/publish_gate.py`).

## 5 · Grenzen dieser Härtung (fair benannt)

* Die Live-Probe beweist **Zugriff**, nicht **Nutzbringung**: ein Pinterest-Token,
  der `/users/me` beantwortet, aber keine Pins schreibt, ist weiterhin nur über
  `PIN-STATUS.md`/Watchdog-Checks sichtbar. Die Wache meldet den Kanal als gesund,
  wo sie das wirklich belegen kann, und sonst nicht.
* Die Scorecard misst Lesbarkeit am Bestand (Flesch/Amstad); sie ersetzt kein
  Lektorat und entscheidet keine Freigaben.
* `unreachable`-Hinweise sind bewusst nicht alarmierend. Wer eine harte Garantie
  will, setzt `--strict` (Umami) bzw. behandelt `verify=unreachable` im Report
  als eigenen Punkt — die Policy ist an einer Stelle definiert
  (`governance_gate.ACTIONABLE_AMBER` / `INFO_AMBER`), nicht an fünf.

---

*Dateien des Sets:* `scripts/governance_gate.py`, `scripts/governance_contract.py`,
`scripts/umami_clicks.py` (neu); `scripts/secrets_age_guard.py`,
`scripts/cwv_guard.py`, `scripts/editorial_scorecard.py` (gehärtet);
`.github/workflows/premium-governance.yml` (v2), `link-check.yml` (Gate),
`pinterest-watchdog.yml`, `pinterest-ai.yml`, `social-ai.yml` (Nachweise);
`docs/GOVERNANCE-KONTRAKT.md` (Regelwerk, vom Lauf gepflegt),
README-Abschnitt „Premium-Governance (v2)".
