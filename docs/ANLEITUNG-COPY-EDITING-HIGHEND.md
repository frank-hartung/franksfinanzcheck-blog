# Copy-Editing Highend – FranksFinanzcheck (Profi-Agentur-Level)

> **Zustand:** aktiv · Rollout: Highend · Gilt für: alle Blogartikel (de-DE, YMYL)
> **Quelle:** `.claude/skills/copy-editing/SKILL_DE.md` + `scripts/copy_edoting_gate.py` + `.github/workflows/sprach-qualitaet-pipeline.yml`

## 1. Ziel

Jeder Blogartikel soll sprachlich auf dem Niveau einer professionellen Finanzredaktion sein (mind. ZEIT-Niveau):

- Perfekte Rechtschreibung, Grammatik, Zeichensetzung
- Saubere Sätze, Absätze, Abstände im Layout (CSS/Design, nicht Textbearbeitung)
- Menschlicher, verständlicher Ton – keine KI-Muster
- YMYL-konform: jede finanzielle Behauptung belegt, Risikohinweise und Affiliate-Offenlegung vorhanden

## 2. Das Highend-Modell (Seven Sweeps + Automatisierung)

### 2.1 Die Seven Sweeps (menschlicher Lektoratsdurchgang)

Jeder Artikel durchläuft sieben Lektorats-Pässe (siehe `SKILL_DE.md`):

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
| `.claude/skills/copy-editing/SKILL_DE.md` | Deutsche Skill-Definition (Seven Sweeps, AI-Tells, YMYL-Panel) |
| `.claude/skills/copy-editing/references/checkliste-de.md` | Finale QA-Checkliste |
| `.claude/skills/copy-editing/references/ai-tells-de.md` | KI-Muster erkennen und entfernen |
| `.claude/skills/copy-editing/references/ymyl-panel-de.md` | Multi-Persona-Review für Finanzartikel |
| `.claude/skills/copy-editing/references/werkzeugkette-de.md` | Engine-Orchestrierung und Schwellen |
| `.claude/skills/copy-editing/evals/evals-de.json` | Eingefrorene Testfälle (Regression) |
| `scripts/copy_editing_gate.py` | Hochorchestrierung aller Engines |
| `.github/workflows/sprach-qualitaet-pipeline.yml` | Automatisierte tägliche Pipeline |
| `docs/ANLEITUNG-SPRACH-QUALITAET-PIPELINE.md` | Workflow-Dokumentation (dieses Dokument ergänzt) |

## 9. Regressionstest

Vor Änderungen an den Engines:

```bash
python3 scripts/copy_editing_gate.py --selftest
# Alle 6 Engines müssen grün sein (Exit 0).
```
