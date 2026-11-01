# 🏛️ WF-D4E0 (#983) – Forensische Kausalanalyse & Dauerheilung auf Agentur-Niveau

**Vorgang:** `WF-D4E0` · Issue **#983** (`🔧 Wartung · Inhaltsqualität · Vorgang WF-D4E0`)
**Workflow:** `.github/workflows/content-reserve.yml` (`Content-Reserve (täglicher Vorrat)`)
**Referenzlauf:** `41190324785` · Job `reserve` (`124505623614`) · `31.10.2026, 09:50:37Z`, `schedule`, Commit `260860de`
**Datum der Dauerheilung:** `2026-11-01` — Basis-HEAD `8048d64`
**Alarmbild:** `"Selbsttests aller Wachen (entdeckt, uhrfest, schreibfrei)" → "Stock shortage must not look successful"` — ein roter Selbsttest, der im Ticket wie ein Vorratsproblem klingt.

---

## 1. Was der Lauf wirklich gemeldet hat (Beleg, nicht Erinnerung)

Die Actions-API nennt für Run `41190324785` genau zwei rote Schritte — der zweite ist nur die Folge des ersten:

| # | Schritt | Ergebnis |
|---|---|---|
| 8 | `Selbsttests aller Wachen (entdeckt, uhrfest, schreibfrei)` | **failure** |
| 25 | `Stock shortage must not look successful` | **failure** |
| 19/21/22 | Stufe 3 / Stufe 5 / Artefakt-Wächter | success |

Der Lauf war **nicht** an einem leeren Vorrat gescheitert. Er war an einem
**Selbsttest** gescheitert — die Wache hat ihr eigenes Prüfwerkzeug geprüft und
für defekt befunden. Das Issue selbst ordnet das bereits richtig ein:
*„Code-Regression, kein Betriebsausfall. Rot ist ein Selbsttest.“*

Der Befund wurde **reproduziert**: Der Baum des Lauf-Commits `260860de` wurde
aus GitHub geladen (codeload-Tarball) und der Runner darauf gestartet —
**derselbe Befund, in einer Zeile**:

```
❌ scripts/copy_editing_gate.py --selftest schrieb in den Arbeitsbaum (C15): M data/lektor_history.jsonl
❌ Selbsttest hat in den Arbeitsbaum geschrieben (C15: ein Prüf-Aufruf heilt nicht): M data/lektor_history.jsonl
```

---

## 2. Forensische Chronologie (Git-Historie + Actions-API)

| Zeit (UTC) | Commit / Lauf | Was passiert |
|---|---|---|
| 30.10. 10:16 | Run `41039588923` (`b02cdf7c`) | Reserve-Lauf **grün** |
| 31.10. 09:49:48 | `260860de` (**#981**, „Copy-Editing Highend-Pipeline“) | `copy_editing_gate.py` entsteht; sein `--selftest` ruft die Engine-Selbsttests — darunter `lektor_guard.py --selftest`, das den **vollen Bestandslauf** startet und eine Zeile an `data/lektor_history.jsonl` hängt |
| 31.10. 09:50:37 | Run `41190324785` | **49 Sekunden nach dem Merge**: Selbsttest-Schritt rot (C15), End-Gate rot → Issue #983 |
| 31.10. 13:59:30 | `a5af34f9` (**#987**) | Heilung: `lektor_guard.py` bekommt einen reinen Beweispfad; `copy_editing_gate.py` bekommt einen Arbeitsbaum-Fingerabdruck (Status + SHA-256) um die Beweisphase |
| 01.11. | HEAD `8048d64` | `copy_editing_gate.py --selftest` und `lektor_guard.py --selftest` schreiben **nichts** mehr; der Runner ist auf dem echten Bestand **grün** |

**Die Ursache in einem Satz:** Ein neuer Orchestrator-Gate (#981) komponierte
Engine-Selbsttests, und eine dieser Engines (`lektor_guard`) hatte keinen
reinen Beweispfad — ihr `--selftest` heilte nebenbei. Damit war die
Beweisführung genau der Vorgang, den **C15** verbietet („ein Prüflauf, der
nebenbei heilt, verändert die Messgröße, die er prüfen will“).

**Ehrliche Einordnung:** Der nächtliche Runner ist das Netz, das den Befund
49 s nach dem Merge fing. Dieselbe Runner-Stufe läuft auch im PR-Gate
(`link-check.yml`, ohne Pfad-Filter). Warum #981 trotzdem rot mergen konnte,
ist eine Frage der Merge-Enforcement (Branch-Schutz), nicht des Codes — und
bewusst **nicht** Teil dieser Heilung.

---

## 3. Warum der Vorfall bereits geheilt ist — und welche KLASSE trotzdem offen war

Der **Vorfall** ist durch #987 geschlossen und in HEAD vielfach abgesichert:

* `lektor_guard.py --selftest` prüft nur die 17 Fälle, schreibt nichts (Kern ist integritätsversiegelt).
* `copy_editing_gate.py` nimmt vor/nach der Beweisphase einen Fingerabdruck und verwirft einen schreibenden Beweis (fail-closed).
* `scripts/tests/test_copy_editing_gate_schnittstelle.py` (12 Tests) hält beides fest.

Bei der Analyse blieb aber eine **Klasse** offen — und zwar an genau der
Wächter-Wache, die den #983-Befund trägt: dem Runner selbst.

### 3.1 Die Blindstelle: Statuszeile ohne Inhalt

`selftest_runner.arbeitsbaum()` las nur die **`git status`-Zeile** (`M pfad`).
Eine Datei, die ein früherer Schritt schon geändert hatte, bleibt `M pfad`,
auch wenn ein Selbsttest sie **ein weiteres Mal** beschreibt. Der Vergleich
`nachher − vorher` bleibt dann **leer** — der zweite Schreibvorgang ist
unsichtbar. Reproduziert am echten Code:

```
vorher:  {'M chronik.jsonl'}
nachher: {'M chronik.jsonl'}
DELTA:   set()        ← der Append des Selbsttests wird NICHT gesehen
```

`copy_editing_gate.py` hatte genau diese Lücke seit #987 mit einem
**Inhalts-Abdruck (Status + SHA-256)** geschlossen. Der Runner — die Wache, die
jenen Befund im Nachtlauf überhaupt erst sichtbar macht — war nie auf
denselben Stand gebracht worden. #983 war ein *sauberer* Baum (frischer
Checkout), deshalb wurde der erste Append gesehen; auf einem Baum mit
vorherigen Schreibvorgängen wäre dieselbe Klasse unbemerkt geblieben.

---

## 4. Dauerheilung: die Klasse schließen, nicht den Vorfall

### 4.1 Inhalts-Abdruck im Runner (`scripts/selftest_runner.py`)

`arbeitsbaum()` wird auf denselben Stand wie `copy_editing_gate.py` gebracht —
**keine zweite Wahrheit**, sondern dieselbe bewährte Härtung an der Stelle,
die den Befund trägt:

| Zusage | Mechanismus |
|---|---|
| **Jeder Schreibvorgang ist sichtbar** | Jede git-sichtbare Spur trägt jetzt `Status + SHA-256[:16]` des Inhalts. Ändert ein Selbsttest eine schon vorher geänderte Datei, ändert sich der Abdruck → `nachher − vorher` ist nicht mehr leer. |
| **Keine neuen Falschalarme** | Die Menge der betrachteten Pfade bleibt exakt die git-sichtbare (plus die bestehende Leer-Ordner-Spur). Es wird nichts zusätzlich inspiziert. |
| **Kostenlos im CI** | Auf einem frischen Checkout ist `git status` leer → es wird nichts gelesen. Nur ein bereits schmutziger Pfad wird gehasht (5150 Dateien: Stat-Scan 14 ms, Voll-Lesen 77 ms — im Nachtlauf gegenstandslos). |
| **Robuste Pfade** | `git status --porcelain=v1 -z`: NUL-getrennte, unquotierte Pfade (Leerzeichen/Umlaute); Umbenennung/Kopie wird samt Quellpfad korrekt gelesen. |
| **Fail-closed bleibt** | Ohne beweiskräftiges Git liefert `arbeitsbaum()` weiter `None` — die Prüfung wird gemeldet, nicht still ausgeschaltet. |

### 4.2 Sabotage-Probe im vertraglichen Minimum

Der Runner steht in `governance_contract.GUARDS` — sein `--selftest` läuft in
**jedem** Qualitäts-Gate. Die eingebaute C15-Sabotage (`schreiber.py`) schrieb
bisher nur eine **neue, unversionierte** Datei. Sie hängt jetzt zusätzlich an
eine **schon vorher geänderte, versionierte** `chronik.jsonl` an — exakt die
#983-Signatur. Eine neue Assertion verlangt, dass der Runner diesen Append
sieht. **Gegenprobe:** Mit neutralisiertem Inhalts-Abdruck fällt der
Runner-Selbsttest durch (`Exit 2`) — die Probe ist also scharf, nicht dekorativ.

### 4.3 Regressionen (`scripts/tests/test_selftest_runner_c15.py`, neu)

11 Integrationstests an einem echten Mini-Git-Baum:

* Append an **saubere** Chronik (nackter #983-Fall) → gesehen.
* Append an **schon geänderte** Chronik (die geschlossene Lücke) → gesehen.
* Gleiche Statuszeile, anderer Inhalt → anderer Abdruck (Mechanismus direkt).
* Neue unversionierte Datei, gelöschte Datei, leerer `content/`-Ordner → gesehen.
* **Reiner Leselauf** → kein Falschalarm.
* **Ohne Git** → `None` (fail-closed).
* Pfad mit Leerzeichen, Umbenennung → korrekt gelesen.
* **Bewusste Grenze:** ein ignorierter Report (`.gitignore`) liegt außerhalb von C15 — wie in `copy_editing_gate.py` seit #987. Die Grenze ist als Test festgehalten, damit eine künftige Änderung sie bewusst trifft.

---

## 5. Geänderte Dateien

| Datei | Änderung |
|---|---|
| `scripts/selftest_runner.py` | `_pfad_abdruck()` (SHA-256) neu; `arbeitsbaum()` auf Status + Inhalts-Abdruck umgestellt (`-z`); C15-Sabotage um die #983-Signatur (Append an schon geänderte Chronik) erweitert + Assertion |
| `scripts/tests/test_selftest_runner_c15.py` | **neu** — 11 Regressionen inkl. der geschlossenen Lücke, Falschalarm-Freiheit, fail-closed und der bewussten Report-Grenze |

**Bewusst nicht angefasst:** `scripts/lektor_guard.py` (integritätsversiegelter
Kern, durch #987 bereits geheilt), `scripts/copy_editing_gate.py` (durch #987
bereits gehärtet) und `data/integrity_lock.json`. Kein Kern wurde berührt.

---

## 6. Verifikation

| Prüfung | Befehl | Ergebnis |
|---|---|---|
| Vorfall reproduziert (Lauf-Baum `260860de`) | `selftest_runner.py --ohne-uhr-probe` | 🛑 **1 Fund: `copy_editing_gate … C15: M data/lektor_history.jsonl`** — exakt der Befund des Laufs |
| HEAD: Vorfall geheilt | `copy_editing_gate.py --selftest` / `lektor_guard.py --selftest` | ✅ beide schreiben nichts (Arbeitsbaum bytegleich) |
| Geschlossene Lücke (Gegenprobe) | `arbeitsbaum()` vor/nach Append an schon geänderte Datei | ✅ **vorher leerer DELTA → jetzt Fund** |
| Neue Regressionen | `python3 -m unittest scripts.tests.test_selftest_runner_c15` | ✅ **11 Tests OK** |
| Runner-Selbsttest (vertragliches Minimum) | `selftest_runner.py --selftest` | ✅ grün — und **Exit 2 ohne Inhalts-Abdruck** (Probe scharf) |
| Alle Wachen-Selbsttests (die CI-Stufe) | `python3 scripts/selftest_runner.py` | ✅ **258 Wachen · 516 Uhr-Proben · 248,6 s · 0 Befunde** |
| #987-Regressionen | `… test_copy_editing_gate_schnittstelle` | ✅ **12 Tests OK** |
| Nachbar-Suiten | `… test_pflichtcheck test_politur_heiler` | ✅ **39 + 16 Tests OK** |
| Governance-Vertrag | `governance_contract.py --quick` | ✅ **43/43 Regeln** (beide Richtungen) |
| Integritäts-Siegel | `integrity_guard.py --gate` | ✅ **50 Kerndateien**, HEAD `8048d64` (kein Kern angefasst) |

---

## 7. Was strukturell verhindert ist

* Ein Selbsttest, der in eine **schon vorher geänderte** Datei schreibt, kann
  nicht mehr unbemerkt bleiben: der Inhalts-Abdruck macht jeden Schreibvorgang
  sichtbar — die Klasse hinter #983 ist an der tragenden Wache geschlossen.
* Die **#983-Signatur selbst** (Append an eine Chronik) ist im vertraglichen
  Minimum festgehalten: fällt der Inhalts-Abdruck je wieder weg, wird der
  Runner-Selbsttest rot, bevor der Nachtlauf es tut.
* **Keine zweiten Wahrheiten:** der Runner fährt dieselbe Härtung, die
  `copy_editing_gate.py` seit #987 fährt — eine Mechanik, zwei Stellen.
* **Kein stiller Schwund:** der reine Beweispfad bleibt schreibfrei; ein
  Falschalarm auf lesende Selbsttests ist im Test ausgeschlossen.

---

## 8. Ehrliche Grenzen

* **Verifikation auf Python 3.11** (Container-Python). Die CI fährt 3.12; ein
  Standalone-3.12-Download war im Arbeits-Container nicht möglich (Release-Host
  gesperrt, Quellbau ohne SSL-/zlib-Header nicht sinnvoll). Der Befund und die
  Heilung sind aber **versionsunabhängig**: `hashlib` und `git status
  --porcelain -z` sind stabile Schnittstellen, und der C15-Befund reproduziert
  sich identisch auf 3.11. Der nächste Nachtlauf (3.12) bestätigt das Grün.
* **Merge-Enforcement ist eine eigene Frage.** Dass #981 rot mergen konnte,
  obwohl das PR-Gate denselben Runner fährt, ist Branch-Schutz, nicht Code —
  hier bewusst nicht mitrepariert.
* **Baseline-Befunde der Vollsuite** (die schon #947 als vorbestehend führte:
  Weiterleitungen/Siegel, Affiliate-Intent, LCP-Manifest, Social-Winkel,
  Inhalts-Register, Versicherungs-Pillar) sind eine andere Klasse und nicht
  Teil dieser Heilung.

---

## 9. Erwarteter Lauf nach dieser Heilung

1. **Schritt 8 (Selbsttests)** läuft auf einem Bestand, in dem der #983-Befund
   durch #987 geheilt ist — grün.
2. **Bei einem künftigen schreibenden Selbsttest** (auch in eine schon geänderte
   Datei) nennt das Ticket Datei und Regel statt „Stock shortage“ über einem
   Build-Befund; der End-Gate berichtet den Vorrat weiterhin ehrlich.
3. **Das Issue schließt sich** beim nächsten grünen Nachtlauf auf `main` selbst
   (kein manueller Eingriff nötig).
