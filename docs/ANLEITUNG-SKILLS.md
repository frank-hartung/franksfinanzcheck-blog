# ANLEITUNG: Skills und der geteilte Leitfaden

Stand: 01.11.2026 · Verantwortlich: `scripts/skills_vertrag.py` (K1–K7) ·
Vorgang und Zahlen: `SKILLS-UMBAU-UND-LIZENZ-NACHWEIS-HIGHEND-2026-11-01.md` ·
Auftrag: Regelwerk so ablegen, dass es **gewirkt** wird, nicht nur exists.

## Warum das hier liegt

Bis zum 01.11.2026 stand alles in einer Datei: `CLAUDE.md`, 2.532 Zeilen,
158 KB. Jeder Agent las das bei jedem Start – Backup-Fristen neben
Snippet-Pixeln neben Reserve-Löschrechten – und trotzdem fand niemand alles,
weil 67 Abschnitte ohne System nicht auffindbar sind. Das ist dasselbe Problem
wie ein Report-Schritt ohne Erzeuger (#806): Der Text ist da, die Wirkung fehlt.

Seitdem gilt das Prinzip der Agent-Skills: **Progressive Disclosure.** Der Kern
trägt, was *jeden* Auftrag angeht (Sicherheit, Verbote, Budget, Router). Der
Rest liegt in `.claude/skills/ff-*` und wird geladen, wenn der Auftrag ihn
braucht. Ersparnis: rund 35.000 Tokens Regelwerk pro Session, 89 % weniger
Vorladelast, bei unverändertem Regelbestand.

```
CLAUDE.md                      ← Kern: 237 Zeilen, 17 KB, Nummer ist Vertrag
.claude/skills/
  ff-pruefen/     SKILL.md + references/*.md   ← Details wörtlich aus dem Kern
  ff-ausliefern/  …
  ff-produzieren/ …
  ff-marke-text/  …
  ff-oberflaeche/ …
  ff-ki-automation/ …
  <fremd>/        SKILL.md + LICENSE.txt       ← aus skills-lock.json, npx skills update
skills-lock.json               ← nur Fremdquellen
data/skill_lizenzen.json       ← Herkunft und Lizenz je Skill
```

## Die sechs Skills und ihre Grenze

| Skill | Zuständig für | Nicht zuständig für |
|---|---|---|
| `ff-pruefen` | Prüfkatalog, Selbsttest-Bau, Wachen-Vertrag, Artefakt-Ganzheit, Manifest, Report-Erzeuger | Reihenfolge im Deploy, Textqualität |
| `ff-ausliefern` | CI, Hugo-Bau-Action, Blustradius, Siegel-Reihenfolge, Alarm-Routing, Scorecard, Backup, Merge | Produktionsregeln der Engine, Gate-Bau |
| `ff-produzieren` | zwei Bahnen, Faktenfrische, Reserve, Slots, Einzigartigkeit, Schreibvertrag | Sprache, Snippet-Grenzen |
| `ff-marke-text` | README-Markenfläche, Abschlussvermerk, ZEIT-Latte, Metadaten/SERP, Tags, Offenlegung, Pins | Layout/CSS |
| `ff-oberflaeche` | Design-Disziplin, Laufzeit-Robustheit, Werkzeuge, `_headers` | Wer wann produziert |
| `ff-ki-automation` | KI-Transportweg, Werkbank, Recherche, Suchradar, Schaltwerk, Kostensperre | Bewertung der Ergebnisse |

Die Grenze ist keine Dekoration: Wer eine Regel ablegt, entscheidet, **wer sie
in Zukunft liest**. Eine Regel im falschen Skill wird bei dem Auftrag nicht
geladen, für den sie geschrieben wurde.

## Neue Regel? Drei Fälle

1. **Ein Dauerverbot, das jeden Auftrag angeht** → ein Satz in die
   Dauervorgaben-Tabelle des Kerns **und** der volle Text in den zuständigen
   Skill. Die Tabelle führt keine Zahl und keine Flagge ein zweites Mal – eine
   zweite Grenze im Code ist genau der Fehler, den `serp_limits.py` verbietet.
2. **Eine Detail-, Vorgangs- oder Runbook-Regel** → **nur** in den Skill.
   Neue Befehle in einen Code-Zaun schreiben, weil `K5` sie gegen
   `package.json` und den Quelltext prüft; Prosa-Befehle prüfen nichts.
3. **Ein Thema ohne zuständigen Skill** → Skill gründen (Ordner + `SKILL.md`),
   ihn im Router des Kerns verlinken, ihn in `data/skill_lizenzen.json` unter
   `eigene.skills` eintragen. Drei Schritte, sonst meldet K3 oder K6.

Nie: eine Sektion in `CLAUDE.md` anhängen. K1 ist deshalb eine Sperre und
keine Höflichkeit.

## Fremd-Skill hinzufügen oder entfernen

```bash
npx skills add <owner>/<repo>          # Quelle landet in skills-lock.json
python3 scripts/skills_vertrag.py      # was fehlt noch? (K4, K6)
```

Danach ist die Arbeit nicht fertig, sondern überprüfbar:

1. **Lizenztext in den Ordner.** `LICENSE.txt` aus der Upstream-Root oder dem
   Skill-Ordner kopieren – unverändert. Bei Apache-2.0 zusätzlich `NOTICE.md`,
   wenn das Upstream eine führt (§4(d)).
2. **Eintrag in `data/skill_lizenzen.json`:** `quelle` + `lizenz`. Eine Lizenz
   „unbekannt“ nur mit `ausnahme` (`grund`, `entscheidung`, `faellig`).
   Eine Ausnahme ohne Frist ist eine stille Abschaffung; eine abgelaufene
   meldet als Warnung und blockiert die Auslieferung nicht.
3. **Router:** ein Satz, wann der Skill zu lesen ist. Ein Skill ohne Router-
   zeile wird nicht gefunden (K3).
4. **Entfernen:** Ordner *und* `skills-lock.json`-Eintrag *und* Registerzeile.
   Ein Eintrag ohne Ordner warnt, ein Ordner ohne Eintrag ist ein Befund.

`skills-lock.json` ist für Fremdquellen da. **`ff-*` stehen dort nie** – sonst
überschreibt das nächste `npx skills update` repo-eigenes Regelwerk (K4).

## Der Nachweis

```bash
python3 scripts/skills_vertrag.py            # K1–K7, Exit 0/1/2
python3 scripts/skills_vertrag.py --md       # für die Lauf-Summary
python3 scripts/skills_vertrag.py --selftest # 13 Sabotage-Fälle + Gegenproben
npm run skills:check                         # dasselbe, im Hausstil
npm run test:skills                          # Selbsttest + 31 Unit-Tests
```

| Klasse | Prüft | Fund heißt |
|---|---|---|
| K1 | Kern ≤ 420 Zeilen / ≤ 32 KB, `SKILL.md` ≤ 200 Zeilen | Der Kern sammelt wieder Details |
| K2 | `name` == Ordner, `description` 80–1024 Zeichen, kein Markup | Der Skill wird nicht ausgewählt |
| K3 | jeder `ff-*` im Router, jede Referenz verlinkt und vorhanden | Eine Regel wird nie gelesen |
| K4 | installierter Fremd-Skill im Lock, kein `ff-*` im Lock | Herkunft oder Update-Recht fehlt |
| K5 | `npm run`-Name, Pfad und Flagge in Code-Zäunen | Das Runbook befehlt einen Schritt, den es nicht gibt |
| K6 | Lizenztext, NOTICE, Ausnahme mit Grund und Frist | Fremder Code ohne Erlaubnis im Repo |
| K7 | `§N` / „Regel N“ / „Abschnitt X“ aus `scripts/` und Workflows | Ein Verweis läuft ins Leere |

Die Wache steht im vertraglichen Minimum (`GUARDS`, C6) und läuft damit mit
dem Qualitäts-Gate auf jeden Push und jede PR – ohne Workflow-Änderung.
`werkbank`- und `suchradar`-Muster: Exit 0 sauber · 1 Befund · 2 Hausfehler.

## Bekannter offener Punkt

`web-design-guidelines` (Vercel) wird genutzt, aber das Upstream-Repo führt
**keine** Lizenz. Das Register trägt die Ausnahme mit Frist **31.12.2026** und
drei Wegen: Anfrage beim Autor, eigener Haus-Leitfaden (empfohlen – die
maßgeblichen Regeln stehen längst in `DESIGN.md` und `ff-oberflaeche`), oder
entfernen. Nach der Frist meldet K6 Warnung auf Warnung; entschieden hat es
niemand. Das ist Absicht: ein unbefristeter Vermerk wäre die stille Variante
desselben Fehlers.
