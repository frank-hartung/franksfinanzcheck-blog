# Copy-Editing Highend – FranksFinanzcheck (Profi-Agentur-Level)

> **Zustand:** aktiv · Rollout: Highend · Gilt für: alle Blogartikel (de-DE, YMYL)
> **Quelle:** `.claude/skills/ff-lektorat/SKILL.md` + `scripts/copy_editing_gate.py` + `.github/workflows/sprach-qualitaet-pipeline.yml`
> **Stand:** 31.10.2026 – Schalter-Vertrag und reiner Beweispfad (Abschnitt 10)

## 1. Ziel

Jeder Blogartikel soll sprachlich auf dem Niveau einer professionellen Finanzredaktion sein (mind. ZEIT-Niveau):

- Perfekte Rechtschreibung, Grammatik, Zeichensetzung
- Saubere Sätze, Absätze, Abstände im Layout (CSS/Design, nicht Textbearbeitung)
- Menschlicher, verständlicher Ton – keine KI-Muster
- YMYL-konform: jede finanzielle Behauptung belegt, Risikohinweise und Affiliate-Offenlegung vorhanden

## 2. Das Highend-Modell (Seven Sweeps + Automatisierung)

### 2.1 Die Seven Sweeps (menschlicher Lektoratsdurchgang)

Jeder Artikel durchläuft sieben Lektorats-Pässe (siehe `ff-lektorat/SKILL.md`):

| Sweep | Fokus | Kernfrage |
|---|---|---|
| 1 | Klarheit | Versteht der Leser sofort, was gesagt wird? |
| 2 | Stimme & Ton | Klingt der Text durchgängig nach einer Marke? |
| 3 | „So What?“ | Beantwortet jede Aussage „Warum sollte mir das etwas bedeuten?“ |
| 4 | „Beweis es!“ | Ist jede Behauptung belegt? (YMYL-kritisch) |
| 5 | Spezifität | Ist der Text konkret genug, um überzeugend zu sein? |
| 6 | Emotion | Fühlt der Leser etwas – oder konsumiert er nur Information? |
| 7 | Zero Risk | Gibt es noch Gründe, nicht zu handeln? |

Nach jedem Sweep wird zurückgeschleift, ob frühere Pässe nicht beschädigt wurden.

### 2.2 AI-Tell-Check (verpflichtend vor jeder Lieferung)

Entfernen typischer KI-Muster (Kontrast-Offenbarungen, Verneinungs-Listen, Stock-Openings, Em-Dash-Inflation etc.). Siehe `references/ai-tells-de.md`.

### 2.3 YMYL-Expert-Panel (Finanzartikel)

Für hochrelevante Finanzartikel (Versicherungen, Kredite, Anlagen, Steuern): 3–5 Personas bewerten 1–10 mit konkreter Kritik. Alle ≥ 7, Durchschnitt ≥ 8. Siehe `references/ymyl-panel-de.md`.

## 3. Die automatisierte Engine-Kette (SSOT)

Die folgenden bereits installierten Offline-Engines werden von `scripts/copy_editing_gate.py` in fester Reihenfolge orchestriert:

| Schritt | Engine | Was | Auto-Fix? |
|---|---|---|---|
| 1 | `grammar_check.py` | LT1–LT4 (Partikel, Kollokationen, Kontext, Fehlschreibung) | Ja (harte Allowlist) |
| 2 | `hardcases_guard.py` | H1–H9 (einzigste, dasselbe, darauf hin, Pleonasmen, ß/ss) | Ja (deterministisch) |
| 3 | `zeit_rechtschreibung.py` | ZEIT-Niveau (LanguageTool-kompatibel, Premium/offline) | Ja (harte Allowlist) |
| 4 | `sprachglatt.py` | DW1–DW9 (Glättung) + V1 (Vorschläge) | Ja (DW), nein (V1) |
| 5 | `lektor_guard.py` | L1–L12 (Verlags-Lektorat: Duplikate, Füllphrasen, Personenkonsistenz, …) | Teilweise |
| 6 | `readability_check.py` | Flesch-Amstad, Satzlänge, Schachtelsätze, Absätze, Passiv | nein (Hinweis nur) |

**Sicherheitsverträge (gelten für alle):**
- Schutzzonen (Code, Links inkl. Ankertext, Shortcodes, URLs, HTML) werden längentreu maskiert, nie verändert.
- Titel/Frontmatter-Anker/Shortcodes/URLs nie schreiben.
- Jeder Schreibvorgang läuft über `sprachkern.write_verified` + Selbsttest vor jedem Lauf.
- Selbsttest rot (Exit 2) = Abbruch, keine Datei wird angefasst.
- **Ein Beweislauf schreibt nichts (C15).** `--selftest` prüft ausschließlich die
  eingefrorenen Fälle – kein Report, keine History, kein Artikel. Der Gate misst
  das zusätzlich selbst: Vor und nach der Selbsttest-Phase nimmt er einen
  Fingerabdruck des Arbeitsbaums; jede Abweichung ist Exit 2.

### 3.1 Schalter-Vertrag (welche Engine was versteht)

Der Gate baut die Argumente **pro Engine** aus `ENGINE_FAEHIGKEITEN`. Ein
Schalter, den eine Engine nicht auswertet, läuft nicht mehr als Placebo mit –
bis zum 31.10.2026 bekam jede Engine denselben Satz, und `--file` /
`--include-drafts` waren bei `hardcases`, `lektor` und `readability` stille
Platzhalter (die Engine prüfte weiter den ganzen Bestand).

| Engine | `--file` | `--json` | `--fix` | `--strict` | `--include-drafts` | `--new-only` |
|---|---|---|---|---|---|---|
| `grammar_check` | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| `hardcases_guard` | ✅ | – | ✅ | – | immer | ✅ |
| `zeit_rechtschreibung` | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| `sprachglatt` | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| `lektor_guard` | ✅ | – | ✅ | – | immer | ✅ |
| `readability_check` | ✅ | ✅ | – (liest nur) | – | immer | ✅ |

„immer“ = die Engine filtert Entwürfe nicht heraus, prüft sie also ohnehin.

Regeln des Vertrags:

- `--file` bei einer Engine ohne Einzeldatei-Modus → **Abbruch (Exit 2)** statt
  stillem Wechsel auf den ganzen Bestand.
- Die Tabelle ist gegen den Quelltext geprüft (`_faehigkeiten_pruefen`). Beide
  Drift-Richtungen sind rot: Engine kann mehr als die Tabelle sagt, oder die
  Tabelle verspricht, was die Engine ignoriert.
- Neue Engine oder neuer Schalter: Tabelle **und** die betroffene Engine
  ändern; `python3 scripts/copy_editing_gate.py --selftest` beweist danach,
  dass beides zusammenpasst.

## 4. Schwellen (Highend-Profi-Agentur)

| Kennzahl | Schwelle neu | Schwelle Bestand |
|---|---|---|
| Flesch-Amstad | ≥ 60 | Ø ≥ 62, Floor ≥ 55 |
| Ø Satzlänge | ≤ 16 Wörter | ≤ 16 Wörter |
| Lange Wörter (>12 Buchst.) | < 15 % | < 15 % |
| Schachtelsätze (>25 Wörter) | < 10 % | < 10 % |
| Absätze > 4 Sätze | 0 | 0 |
| Offene kritische Funde (LT1–LT4, H1–H9, ZEIT) | 0 | 0 |

## 5. Nutzung

### 5.1 Einzelner Artikel (manuell, nicht zerstörend)

```bash
# Voller Highend-Lauf, nur melden (Empfohlen vor Veröffentlichung)
python3 scripts/copy_editing_gate.py --file content/posts/<artikel>/index.md --report COPY-EDITING-REPORT.md

# Mit Auto-Fix (nur harte Allowlist, sicher)
python3 scripts/copy_editing_gate.py --file content/posts/<artikel>/index.md --fix --strict

# Selbsttest aller Engines (Sabotage-Schutz)
python3 scripts/copy_editing_gate.py --selftest
```

### 5.2 Gesamter Bestand (Wache)

```bash
python3 scripts/copy_editing_gate.py --strict
```

### 5.3 Nur neue Artikel von heute (Publish-Gate)

```bash
python3 scripts/copy_editing_gate.py --new-only --strict
```

## 6. GitHub Actions (automatisiert)

Die `.github/workflows/sprach-qualitaet-pipeline.yml` läuft täglich 04:30 UTC und führt das komplette Gate durch:

- **report** (Default): prüft, meldet, schreibt Reports + Artefakte
- **fix**: heilt eindeutige Fälle (harte Allowlist, verifiziert)
- **strict**: wie report, aber Exit 1 bei offenen Funden → Workflow rot + automatische Issue-Eröffnung

Reports landen als Workflow-Artefakte (30 Tage Aufbewahrung). History-Files werden versioniert und dedupliziert.

## 7. Menschliche Endredaktion (freigabepflichtig)

Nach dem automatischen Durchlauf entscheidet die menschliche Endredaktion über:

- Grauzonen und V1/L1–L12-Vorschläge (nie blinder Auto-Fix)
- AI-Tell-Check (menschliche Bewertung)
- YMYL-Belege und Risikohinweise
- Finale Freigabe via `scripts/endredaktion.py`

**Kein Artikel wird ohne menschliche Endredaktion veröffentlicht.**

## 8. Dateien im Überblick

| Pfad | Zweck |
|---|---|
| `.claude/skills/ff-lektorat/SKILL.md` | Deutsche Skill-Definition (Seven Sweeps, AI-Tells, YMYL-Panel) |
| `.claude/skills/ff-lektorat/references/checkliste.md` | Finale QA-Checkliste |
| `.claude/skills/ff-lektorat/references/ai-tells.md` | KI-Muster erkennen und entfernen |
| `.claude/skills/ff-lektorat/references/ymyl-panel.md` | Multi-Persona-Review für Finanzartikel |
| `.claude/skills/ff-lektorat/references/werkzeugkette.md` | Engine-Orchestrierung und Schwellen |
| `.claude/skills/ff-lektorat/evals/evals.md` | Eingefrorene Testfälle (Regression) |
| `scripts/copy_editing_gate.py` | Hochorchestrierung aller Engines |
| `.github/workflows/sprach-qualitaet-pipeline.yml` | Automatisierte tägliche Pipeline |
| `docs/ANLEITUNG-SPRACH-QUALITAET-PIPELINE.md` | Workflow-Dokumentation (dieses Dokument ergänzt) |
| `scripts/tests/test_copy_editing_gate_schnittstelle.py` | Beweis: Schalter-Vertrag + reiner Beweislauf |
| `scripts/tests/test_workflow_push_rechte.py` | Beweis: Push-Rechte, Exit-Erfassung, Label-Reihenfolge |

## 9. Regressionstest

Vor Änderungen an den Engines:

```bash
python3 scripts/copy_editing_gate.py --selftest
# Alle 6 Engines müssen grün sein (Exit 0) – und der Arbeitsbaum danach
# unverändert (git status bleibt leer).
```

Die Suite dazu:

```bash
python3 -m unittest scripts.tests.test_copy_editing_gate_schnittstelle -v
python3 -m unittest scripts.tests.test_workflow_push_rechte -v
```

## 10. Reparatur 31.10.2026 – warum diese Seite so streng ist

Nach dem Merge von #977 lief das PR-Gate rot, obwohl alle Engines grün waren.
Der Grund war eine einzige Zeile in `lektor_guard.py`: Es kannte keinen reinen
Beweispfad. `--selftest` prüfte die 17 Fälle – und begann danach den vollen
Bestandslauf, der eine Zeile an `data/lektor_history.jsonl` anhängte. Der
Beweis war damit selbst der Vorgang, den die Vertragsregel C15 verbietet
(„Beweisen ist nicht Heilen“).

Zwei Konsequenzen, die dauerhaft gelten:

1. **Reiner Beweispfad ist Pflicht.** Jede Engine, die schreiben kann, muss
   `--selftest` als Trockenlauf führen (nur prüfen, Exit-Code, keine Datei).
   `lektor_guard.py` dokumentiert das im Kopf; `copy_editing_gate.py` prüft es
   zur Laufzeit über den Arbeitsbaum-Fingerabdruck.
2. **Kein Schalter ohne Wirkung.** Der Gate reicht nur weiter, was die Engine
   auswertet (Abschnitt 3.1). Der stille Rückfall auf den ganzen Bestand ist
   ein Scope-Bruch, kein Komfortverlust.

Die zweite Hälfte des Befunds lag im Workflow: `git push || true` bei
`permissions: contents: read` konnte nie funktionieren, und der Fehler war
unsichtbar. Details und Beweise in
`docs/ANLEITUNG-SPRACH-QUALITAET-PIPELINE.md`, Abschnitt 11.
