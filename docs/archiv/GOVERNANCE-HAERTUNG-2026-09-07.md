# Governance-Härtung 07.09.2026 — Root-Cause „#206" und die neue Betriebsschicht

**Kontext:** Issue #206 war ein automatisch erzeugter Governance-Report der Wache
`Premium-Governance` (Montag 07:15 MESZ). Er klang nach „drei redaktionelle +
drei technische Handlungsfelder", gemessen war aber nichts davon. Das Problem
war die **Governance selbst**, und zwar strukturell: Sie hat sich mit
Vorwochenständen, Vermutungen und Roh-Exit-Codes selbst alarmiert — und genau
daraus Duplikat-Issues gebaut (#145 → #206).

Dieses Dokument ist der Handover an den Betreiber. Es erklärt pro Baustein,
was kaputt war, was jetzt anders ist und womit man es nachprüfen kann.

---

## 1. Befund: sieben Ursachen, ein Symptom

| # | Ursache (vorher) | Woran es im Report sichtbar wurde |
|---|---|---|
| U1 | **Reihenfolge.** Der Lauf berechnete die Scorecard *zuerst*, die Messungen (CWV, Decay, Secrets) *danach*. Die Scorecard las also `data/cwv_manifest.json` der Vorwoche. | „Core-Web-Vitals AMBER" in der Scorecard, während der CWV-Wächter im selben Lauf GREEN meldete; −7 Punkte Score, eine Empfehlung „Layout/JS prüfen", die ins Leere lief |
| U2 | **Vermutung statt Messung** bei Secrets. Geprüft wurde nur die *Datei* `data/secrets_state.json`; geschrieben wurde sie vom jeweiligen KI-Workflow — `pinterest-ai.yml` aber seit dem 20.08. nur noch manuell. Die Governance hat die „6 Tage alt"-Zahlen also nie aktualisiert, nur geerbt. | `PINTEREST_ACCESS_TOKEN UNBEKANNT` → dauerhaft AMBER → *jeder* Lauf meldete „Handlungsfeld" und *jeder* Lauf wollte ein neues Issue |
| U3 | **Selbstbestätigter Erfolg.** `--record-success GROQ_API_KEY`/`GEMINI_API_KEY` standen im Governance-Lauf, der diese Keys nie benutzt. | „OK (6d)" bedeutete: „dieser Workflow ist mal gelaufen", nicht „der Token funktioniert" |
| U4 | **Issue-Policy an Exit-Codes gekoppelt.** Jeder Schritt mit Exit 1 erzeugte ein Issue — und „noch keine Daten" (Awin CSV, Umami-Import, Pinterest-Analytics ohne Scope) war Exit 1. | Duplikate; Issue-Titel mit identischem Inhalt, wachsender Kommentar-Thread pro Woche |
| U5 | **Dauer-„0 Klicks"** in Scorecard und SEO-Briefing, weil die einzige Quelle ein manueller Dashboard-Export war. | „Affiliate-Klicks 0 / Awin 0,00 €" als scheinbarer Befund; Monetarisierungs-Empfehlungen ohne Datenbasis |
| U6 | **Lückenlose Grün-Malerei.** `hugo --minify … \|\| true` (Build-Fehler wurden verschluckt) und `check_inbound_links.py \|\| true` — CWV konnte ein „grün" melden, ohne dass eine Seite gebaut war. | (nicht sichtbar — das ist die gefährliche Klasse: Alarm ruht auf einer Messung, die nie stattfand) |
| U7 | **Datenriss im State.** `data/secrets_state.json` wurde von vier Workflows parallel mit `open(..., "w")` geschrieben, ohne Sperre, ohne Atomicity, und `last_success_date` akzeptierte nur ein Datumsformat. | (gelegentlich) Traceback in einem KI-Workflow → dort wieder ein „Workflow-Panne"-Issue |

## 2. Behebung

### 2.1 Einordnen: Messen → Sehen → Bewerten → Melden

Der Lauf hat jetzt vier Phasen mit klaren Verträgen dazwischen (C1–C9 aus
`scripts/governance_contract.py`). Das ist die eigentliche Behebung von U1/U4 —
nicht das Nachziehen einzelner Zahlen.

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
    können keinen Daueralarm mehr bauen. Verwaiste Einträge (> 26 h) werden
    verworfen, nicht bewertet.
  * Ein toter Schritt ist ein Befund: `--reset` + kein `--emit` während des Laufes
    ⇒ rot („Schritt hat nicht gemeldet"), statt unsichtbar „grün, aber vorgestern".

* **Issue-Policy (U4).** Ein Issue bei `red`/`amber` **mit** Befund; bei veränderten
  Befunden wird das bestehende Issue aktualisiert (Fingerabdruck über
  `(schritt, code, zahl)`), sonst nur ein Kommentar. Meldungsarme, aber nicht grüne
  Lage ⇒ ein Kommentar. **Kein Befund ⇒ Issue zu.** Exit-Grün trotz Befund
  (Zustimm-Schritte) wird ignoriert, Exit-rot ohne Befund wird zur Info
  („Datenlage offen").

* **Scorecard (U1, U5).** `scripts/editorial_scorecard.py` läuft zuletzt, liest die
  frischen Manifeste und kennzeichnet jede Zahl mit ihrer Herkunft: `(Stand 06.09,
  1d)` oder `STALE (20.08, 18d)` oder `nicht gemessen` — ⚪ statt 🟡, weil eine
  fehlende Messung keine schlechte Nachricht ist, sondern eine Lücke.
  Neue Abschnitt **„Datenlagen (Messabdeckung)"**: zeigt den Pipeline-Zustand
  (nie gelaufen / ok / Fehler / übersprungen) als ℹ️ statt als Alarm.
  Score-Logik: ⚪ zählt nicht gegen die Agentur, CWV ohne Messung auch nicht
  (stattdessen −3 „Blindflug"). Lesbarkeit und Klickstrecke haben jetzt eigene
  Empfehlungen.

* **Secrets-Wache v2 (U2, U3, U7).** `scripts/secrets_age_guard.py`:
  * `--verify` macht **echte Live-Proben** mit den echten Secrets
    (Pinterest `/v5/users/me`, Mastodon `verify_credentials`, Groq/Gemini `/models`,
    optional Umami). Erfolg zählt nur bei HTTP 200, Antwort wird length-limited
    gelesen. Ein abgelehnter Token ist **rot**, nicht mehr „UNBEKANNT".
  * **Alarm-Kontinuität:** ein gemeldeter `dead` bleibt rot, bis eine Probe ihn
    bestätigt — ein Lauf ohne Netz heilt den Alarm nicht (das wäre gefährlicher
    als kein Alarm).
  * Nachweise tragen **Herkunft** (`--proof-by pinterest-ai.yml`) und
    **Qualität** (`proven` / `declared` / `declared_foreign` / `legacy`).
    `--record-success` ohne `--proof-by` wird abgelehnt (U3).
  * Transiente API-Störung ⇒ `unreachable` = ℹ️, *kein* Issue; die Altersregel
    eskaliert erst, wenn der Nachweis wirklich ausbleibt (`stale` ⇒ rot).
  * Optionale Kanäle ohne Secret ⇒ **info** („Kanal nicht eingerichtet, bewusst"),
    keine Pflicht-Kanäle ohne Secret ⇒ rot — da ist die Wache strenger als vorher.
  * State: atomar (`tmp` + `os.replace` + `fsync`), `flock` gegen Parallelzugriff,
    tolerantes Datums-Parsing (`ISO` und `dd.mm.jjjjj`), beschädigter State wird
    gesichert und gemeldet statt mit Traceback abzurstürzen.
  * `--quiet` für fremde Workflows (Pinterest/Mastodon): verifizieren und
    vermerken, aber weder Exit-Code noch Report schreiben.

* **CWV-Wächter (U6).** `scripts/cwv_guard.py`: `--strict-build` (und
  `--min-html N`) — fehlt der `public/`-Baum oder ist er dünner als das Minimum,
  heißt der Befund `build_missing`/`build_thin` und ist **rot**, nicht grün. Das
  Manifest enthält jetzt `build_measured` (Zeitstempel der Messung), und der Lauf
  schreibt zusätzlich `data/cwv_history.jsonl` → `--trend` zeigt, ob die Seite über
  Wochen langsamer wird, statt nur den Moment zu melden. Reine Hinweise
  (`hinweis`) alarmieren nicht mehr.

* **Umsatz-Strecke (U5).** `scripts/umami_clicks.py` **(neu)** zieht die Klicks
  selbst aus Umami (`/api/v1/events/sessions` mit `referrer=/go/{slug}/`), pro
  Artikel, Pillar und Typ aggregiert, und schreibt `data/umami_clicks.json` im
  gewachsenen Schema. Es akzeptiert Cloud- *und* self-hosted-Payloads (beide
  Feldordnungen, `results`-Wrapper, alternative Property-Namen), redigiert Token
  aus jeder Fehlermeldung, und **überschreibt bestehende Daten nicht** mit einem
  API-Fehler. Website-ID kommt aus `hugo.toml` → kein zweiter Pflegeraum.
  Kein Secret ⇒ dokumentierter Skip (`reason`), *keine* erfundene „0 Klicks".
  Awin bleibt bei `data/awin_transactions.csv` (API hat keinen dokumentierten
  Programm-Zugriff; eine „Anbindung", die nicht prüfbar ist, wäre genau die
  Fehlerklasse U2/U3).

### 2.2 Die Dauerhaftigkeit: `scripts/governance_contract.py` (neu)

Einmalige Fixes veralten. Deshalb sind die Lehren als **neun Regeln im Repo**
abgelegt, die bei jedem Push/PR (Qualitäts-Gate) und als Preflight im
Governance-Lauf geprüft werden — `docs/GOVERNANCE-KONTRAKT.md` ist das
zugehörige, automatisch gepflegte Regelwerk:

| Regel | Sichert ab gegen |
|---|---|
| C1 Reihenfolge | Scorecard vor den Messungen (U1), Reports die niemals gelesen werden |
| C2 Bau-Grundlage | `\|\| true` an einem Build/Mess-Schritt; Meldung ans Gate (U6) |
| C3 Messkette | Jeder `--emit`-Name hat seinen Absender im Workflow (U2) |
| C4 Issue-Policy | `--decide` vor dem Issue-Schritt, kein `gh issue create` ohne Policy, **Dedupe-Pflicht** (U4) |
| C5 Nachweis-Provenienz | `--record-success` in der Governance, `--proof-by` Pflicht (U3) |
| C6 Selbsttests | Wache ohne `--selftest` oder mit fehlgeschlagenem Selbsttest |
| C7 Datenkonsistenz | Manifest, Report und Scorecard müssen dieselbe Ampel zeigen (U1 als Regressionsfalle) |
| C8 Commit-Hygiene | `git add` auf ignorierte/unversionierte Pfade (#205) |
| C9 Secret-Leak-Schutz | kein Secret-Material in Reports/`data/*.json` |

Beweisrichtung: `governance_contract.py --selftest` füttert dem Checker
Kunst-Workflows (vorher/nachher). Er muss den alten Stand *finden* und den neuen
*in Ruhe lassen* — Regeln, die nur bei ihrem eigenen Fehler schweigen, sind
Deko. Zusätzlich werden die Selbsttests der Wächter (C6) mit dem realen Python
des Läufers ausgeführt.

### 2.3 Workflows

* `premium-governance.yml` v2 — Preflight (10 Selbsttests + Vertrag) → Bauen →
  Messen → Sehen → Bewerten → Issue (idempotent) → Summary → Commit. Jeder
  Mess-Schritt endet beim Gate, `::error::`-Annotationen nur bei Befund.
* `link-check.yml` (Qualitäts-Gate) — führt die Governance-Selbsttests **bei
  jedem Push/PR** aus, plus Vertrag; der Hugo-Bau bleibt als Messgrundlage nötig.
* `pinterest-watchdog.yml` — die tägliche Wache prüft den Pinterest-Token jetzt
  **live** (`--verify --quiet`), nicht nur die Env-Variable; das
  „Secrets-Report"-Artifact wird mit `if: always()` gesichert, damit ein
  geblockter Alarm nicht zu einem Pip-Abbruch *und damit zu einem weiteren
  Issue* führt. Das war die Nebenursache von #206.
* `pinterest-ai.yml` / `social-ai.yml` — `--verify` vor der Veröffentlichung
  (toter Token ⇒ Abbruch mit Runbook, Netzstörung ⇒ Warnung), und Erfolg wird nur
  noch vermerkt, wenn der Post wirklich rausging (`|| true` am „erfolgreich
  gepostet"-Schritt entfernt), mit `--proof-by`.
* `.gitignore` — `*.lock` und `data/*.tmp-*`: die Wache erzeugt jetzt
  Sperr-/Temp-Dateien; `pinterest-watchdog.yml` committed mit `git add -A`, und
  eine `*.lock` im Repo warf beim Governance-Commit einen Fehler.

---

## 3. Verifikation (dieser Stand)

| Prüfpunkt | Ergebnis |
|---|---|
| `--selftest` aller 10 Wachen inkl. neuem Gate, Scorecard, Umami, Vertrag | ✅ |
| `governance_contract.py` auf **HEAD~** (alter Stand, neue Checker) | 🔴 28 Verletzungen (C1×6, C2×2, C3×8, C4×4, C5×7, C7×1) |
| `governance_contract.py` auf diesem Stand (inkl. C6-Selbsttests) | 🟢 0 Verletzungen |
| `governance_gate.py --rehearse` über den Bestand | Ampel INFO → Aktion `close` (0 Befunde, 6 Hinweise, 3 grün) |
| Simulierter Token-Ausfall (`verify=dead`) | 🔴 `dead` → Issue mit Runbook, `--fail-on red` Exit 1 |
| Netzwerk zu, Secrets „vermeintlich" da | Ampel INFO, Exit 0, **kein** Issue |
| Scorecard | **90/100 GREEN** (vorher 83/100 AMBER), Begründung je Zeile |
| YAML aller 35 Workflows, `py_compile` | ✅ |

## 4. Betrieb

* **Einmalig (2 Minuten, optional, aber der eigentliche Umsatz-Hebel):**
  `UMAMI_API_TOKEN` als Secret setzen (`gh secret set UMAMI_API_TOKEN`, Token in
  Umami unter *User Settings → API*). Ab dem nächsten Montag stehen echte Klicks
  in `data/umami_clicks.json`, im `CLICK-REPORT.md` und in der Scorecard.
  Selbst-hosted: zusätzlich `UMAMI_API_BASE`. Schritt-für-Schritt-Anleitung:
  `docs/ANLEITUNG-UMAMI-ANALYTICS.md` (Abschnitt „Automatische Klick-Übernahme").
* **Wöchentlicher Blick (30 Sekunden):** `EDITORIAL-SCORECARD.md` →
  Zeile „Datenlagen" und Score-Trend. Wenn dort alles 🟢/ℹ️ ist, ist die
  Automatisierung gesund — unabhängig davon, ob die Redaktion rot steht.
* **Wenn ein Issue aufgeht:** Der Body listet nur noch Befunde mit Zählwert
  (z. B. „Token abgelehnt", „State gerissen", „Baum nicht gebaut"). Runbook pro
  Code steht im Report (`DEAD_TOKEN`, `STATE_STALE`, `STATE_CORRUPT`).
* **Neue Wache / neuer Kanal?** Drei Dinge, sonst beißt der Vertrag:
  `--selftest` bauen, im Qualitäts-Gate auflisten, Ergebnis mit
  `governance_gate.py --emit` melden (sonst C3/C4).

## 5. Was bewusst *nicht* gemacht wurde

* **Keine erfundene Umsatz-Zahl.** Awin bleibt CSV, Pinterest-Analytics braucht
  den `analytics:read`-Scope. Ein „automatisierter" Import, der still
  herunterfällt, ist der Rückfall in U2/U5 — die Scorecard zeigt jetzt
  transparent „Datenlage offen", inklusive was dafür zu tun ist.
* **Kein Alarm bei Infrastruktur-Wetter.** Netz-API-Störungen sind Hinweise.
  Rot wird's über die Altersregel, wenn niemand in 7 Tagen mehr messen konnte.
* **Der Governance-Lauf bleibt grün, wenn er rot meldet.** Das Issue ist der
  Alarm; der Run trägt die `::error::`-Annotation und den Befund im Job-Summary.
  Ein roter Run würde vom zentralen Fehler-Alerting ein zweites Issue für
  dieselbe Lage erzeugen — genau das Doppeln, das wir abschaffen wollen.
