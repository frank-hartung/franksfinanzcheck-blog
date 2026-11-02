---
name: ff-pruefen
description: "Benutzen, bevor in diesem Repo etwas GELTEN soll: Commit, Merge, Umbau einer Wache/Gate, neuer oder geänderter --selftest, Verdacht auf einen Befund, kaputtes data/*.json, package.json-Lauffehler, Report mit 'Datenlage offen'. Dieser Skill enthält den vollständigen Prüfkatalog (welches npm run test:* zu welcher Änderung), die Selbsttest-Disziplin, den Wachen-Vertrag, die Artefakt-Regeln und die Manifest-Wache. Auslöser auch bei: 'prüf das', 'welcher Test?', 'der Selbsttest läuft nicht', 'das Gate ist rot', 'Artefakt kaputt'. Nicht für Reihenfolge im Deploy (ff-ausliefern) und nicht für Textqualität (ff-marke-text)."
metadata:
  version: 1.0.0
  besitz: repo-eigen – kein Eintrag in skills-lock.json, nie von `npx skills update` anfassen
  quelltext: CLAUDE.md-Kernregeln, wörtliche Details in references/
---

# Prüfen, bevor etwas gilt

Dieser Skill trägt, was der Kern nur anreißen kann: **welcher Test zu welcher
Änderung gehört** und **welche Vertragsregeln einen grünen Lauf vor Scheingrün
schützen**. Die Details in `references/` sind wörtlich aus `CLAUDE.md`
übernommen – dort stehen Befund, Zahlen und Vorgeschichte.

## Wann dieser Skill zählt

- Du willst committen, mergen oder einen Stand „fertig“ nennen.
- Du änderst, löschst oder schreibst eine **Wache** (`scripts/*_guard.py`,
  `*_gate.py`, `*wache*.py`) oder ihren `--selftest`.
- Ein Report, ein Issue oder eine Annotation meldet einen Befund, und du willst
  wissen, welcher Test die Klasse wirklich deckt.
- Eine `data/*.json`, `package.json` oder ein Lockfile verhält sich falsch.
- Ein Schritt schreibt einen Report, den niemand mehr erzeugen kann.

## Die harten Kernregeln

1. **Ein `--selftest` prüft das Modul, dessen Namen er trägt** – nie die Engine,
   deren Flagge er nur durchreicht. Hat die Engine keinen Selbsttest, darf der
   Aufruf mit `--selftest` nicht ihre scharfe Standardaktion starten
   (`selftest_runner.GEFAHREN`).
2. **Eine Wache ist ganz oder gar nicht.** Bei einem Merge-Konflikt wird EINE
   Fassung gewählt (`git checkout <rev> -- <pfad>`), nie Kopf von hier und Rumpf
   von dort. Nach jeder Auflösung: `python3 scripts/<wache>.py --selftest`.
   Rot heißt: es wird nicht committet.
3. **Ein Selbsttest urteilt über Code, nicht über das Modell.** Jeder KI-Weg
   läuft über die vorhandene Attrappe; „offline, weil kein Key im Selbsttest“
   ist eine Annahme, keine Garantie. Leitplanke:
   `python3 scripts/selftest_ki.py --trap-workflows`.
4. **Ein Messartefakt ist eine ganze Messung, kein Text.** Maschinen-Artefakte
   werden nie textuell gemergt (`merge=binary`), nicht rekonstruiert und nie
   zurückgerollt; gegengelesen wird mit
   `python3 scripts/artefakt_waechter.py` (A1–A6).
5. **Vor jedem `npm ci`/`npm install` steht die Manifest-Wache**
   (`npm run manifest:check`); sie ersetzt keine Versionsentscheidung.
6. **Kein Report-Schritt ohne lebenden Erzeuger.** Ein Schritt, dessen Skript es
   nicht mehr gibt, meldet für immer „Datenlage offen“.
7. **Fremdmessung ist tabu** – die Sperre und ihr Grund stehen im
   `CLAUDE.md`-Kern (DAUERVORGABE), die Mechanik der Klassen F1–F5 hier:
   `references/selbsttest-und-wachen.md`.

## Katalog

| Deine Frage | Antwort im Detail |
|---|---|
| Welcher Test läuft zu meiner Änderung? | `references/pruefkatalog.md` (vollständiger Katalog inkl. E2E-Architektur und Browser-Pflicht) |
| Wie muss ein `--selftest` gebaut sein, was verbietet der Wachen-Vertrag, warum kompiliert der liegende Stand? | `references/selbsttest-und-wachen.md` (inkl. Beweis-Ledger-Isolation C27) |
| Artefakt kaputt, Merge-Dopplung, `npm ci`-Absturz, JSON mit zwei Läufen? | `references/artefakte-und-manifest.md` (inkl. C33, #853, #654) |
| Warum steht im Report „Datenlage offen“? | `references/report-erzeuger.md` (C42, generierte Zone) |

## Kommando-Notausgang

```bash
python3 scripts/skills_vertrag.py            # dieser Skill-Vertrag (K1–K8)
python3 -m unittest discover -s scripts/tests -p "test_skills_vertrag.py"
python3 scripts/skript_syntax_wache.py       # liegt der Stand kompilierfähig?
python3 scripts/wachen_vertrag.py            # halbe Aufrufe, halbe Konstanten
npm run manifest:check                       # Manifest + Lockfile
```

## Fremd-Skill außer Betrieb: `analytics`

Der Skill `analytics` (coreyhaines31/marketingskills) beschreibt Tracking-Einbau –
Ereignisse, UTM, Tag-Manager, Auswertung. Dieses Repo hat **keine**
Besucher-Messung und bekommt keine nachgerüstet (Fremdmessung-Sperre, C40,
`scripts/fremdmessung_sperre.py`). Gelesen wird er, um zu erkennen, was hier
gesperrt ist – nie, um es umzusetzen. Wer ihn anwendet, baut die Anbindung
wieder ein, die am 19.10.2026 restlos entfernt wurde (#806).

## Nicht zuständig für

- **Reihenfolge und Blockaden im Deploy** → `ff-ausliefern`
- **Produktionsregel der Content-Engine** (Themen, Reserve, Fakten) → `ff-produzieren`
- **Sprache, Metadaten, Kennzeichnung** → `ff-marke-text`
