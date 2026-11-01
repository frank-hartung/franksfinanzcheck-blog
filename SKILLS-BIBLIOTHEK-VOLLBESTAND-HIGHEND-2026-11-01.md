# Skills-Bibliothek: Vollbestand, Rückbau der themenfernen, zwei neue Wachen (Highend, 01.11.2026)

> Status: umgesetzt, gemessen, geprüft. Enthält den Vollbestand (53) **und** den
> Rückbau um `sms`/`paywalls`/`aso` am selben Tag – beide Zahlen stehen unten,
> der Rückbau ist die gültige: 62 Skill-Ordner, davon 50 aus
> `coreyhaines31/marketingskills` und 6 aus den übrigen Quellen. Betriebsanleitung: `docs/ANLEITUNG-SKILLS.md`.
> Vorgänger mit den Zahlen des Umbaus: `SKILLS-UMBAU-UND-LIZENZ-NACHWEIS-HIGHEND-2026-11-01.md`.

## Der Auftrag und was er ausgelöst hat

Angestoßen wurde ein `npx skills add coreyhaines31/marketingskills`. Der CLI ist
ohne TTY nicht interaktiv und hat abgebrochen; mit `--list` zeigte er **53**
Skills, von denen 12 schon im Haus lagen. Zwei Befunde standen vor der
Entscheidung:

1. **Die installierten zwölf waren veraltet.** `analytics` lag in 2.0.3, im
   Upstream in 2.2.2 – es fehlten unter anderem die Abschnitte „Compute, Don't
   Eyeball" und „Match Observation Windows", also genau die Regeln gegen
   vorgerechnete Zahlen ohne Zeilenbeleg. `ai-seo` lag in 2.7.6 gegen 2.12.0.
2. **Die Beschreibungen sind die eigentliche Rechnung.** Sie stehen in jeder
   Session im Kontext, unabhängig vom Auftrag. Alle 53 zu installieren kostet
   rund 12.000 Tokens Dauerlast – mehr als das Dreifache des heutigen Bestands.

Entschieden wurde (Betreiber, 01.11.2026): **alle 53** und **die zwölf
aktualisieren**. Damit ist die Aussage „kein zweiter Schwung Fremd-Skills" aus
`SKILLS-UMBAU-…-2026-11-01.md` bewusst revidiert – nicht stillschweigend
überholt. Der Grund ist derselbe wie damals, nur anders beantwortet: Die
Bibliothek ist Werkzeugkasten, nicht Regelwerk; die Frage ist nicht, ob sie
nützlich ist, sondern was sie dauerhaft kostet.

## Stand, gemessen statt geschätzt

| Befund | vorher | Vollbestand (53) | **gültig nach Rückbau** |
|---|---|---|---|
| Skill-Ordner unter `.claude/skills/` | 24 | 65 | **62** |
| davon Fremd-Skills | 18 | 59 | **56** |
| davon repo-eigen (`ff-*`) | 6 | 6 | **6** |
| Einträge in `skills-lock.json` | 18 | 59 | **56** |
| Dateien im Skill-Baum | ~250 | 687 | **667** |
| Lizenztexte in den Fremd-Ordnern | 18 | 59 | **56** |
| Summe aller `description` | 16.198 Zeichen (≈ 4.050 Tokens) | 49.142 · 48,0 KB · ≈ 12.285 Tokens | **47.162 Zeichen · 46,1 KB · ≈ 11.790 Tokens** |
| Beschreibungen über dem Limit 1.024 | 0 | 0 (längste: `social` 1.021) | **0** |
| `skills_vertrag.py` | 0 Befunde, 2 Warnungen | 0 Befunde, 3 Warnungen | **0 Befunde, 3 Warnungen** (K8 ×2, K10 ×1) |

## Rückbau am selben Tag: `sms`, `paywalls`, `aso`

Der Vollbestand war die Entscheidung, die der Betreiber am selben Tag korrigiert
hat – nach der Messung, nicht nach Bauchgefühl. Drei Skills haben im Blog
**keinen** Anker: `sms` (SMS/MMS/WhatsApp),
`paywalls` (In-App-Kauf- und Abo-Mauern) und `aso` (App-Store-/Play-Listings).
Der Blog ist eine statische Hugo-Seite mit Newsletter – es gibt keine App, kein
Abo hinter einer Mauer, keine Telefonnummer-Liste. Die Aufnahme hätte drei
Dauerbeschreibungen in jeden Kontext gelegt, für die kein Gate und kein Vorgang
dieses Repos sie je aufruft.

Entfernt nach dem Runbook (Schritt 4: Ordner **und** Lock **und** Registerzeile):

```
npx -y skills@1.7.4 remove sms paywalls aso -a claude-code -y
   → 3 skills entfernt, 20 Dateien aus dem Baum, 56 Lock-Einträge
data/skill_lizenzen.json   → 3 Einträge gelöscht (sonst K6-Warnung „Register
                             führt einen Skill, der nicht installiert ist")
```

Wirkung, gerechnet in Tokens: **—495 Tokens Dauerlast** (`aso` 115, `paywalls`
192, `sms` 187). Ehrlich dazu: Das ist der kleinste Teil des Preises. Der große
Posten bleibt die Entscheidung für die Bibliothek selbst (~11.790 Tokens), und
die drei waren die einzigen mit einem **sachlichen** Grund zum Gehen – alle
anderen haben mit Blog, Suche, Text oder Auslieferung zu tun. Wer weiter sparen
will, muss die Frage anders stellen (welche Themen der Blog überhaupt bedient),
nicht die drei erneut suchen.

Aufnahmeprotokoll eingehalten: `npx -y skills@1.7.4`, danach **53 mal**
`LICENSE.txt` (MIT, „Copyright (c) 2025 Corey Haines", bytegleich mit dem
Upstream-Text) und **53 Register-Einträge** (`quelle` + `lizenz: MIT`) in
`data/skill_lizenzen.json` – nach dem Rückbau 50 davon im Baum. Alle 53 `SKILL.md`
waren bytegleich mit dem Upstream –
es wurde nichts gekürzt, umgewidmet oder umgeschrieben. Auch die drei
Beschreibungen, die im Upstream über 1.024 Zeichen liegen, sind nach dem
Neu-Schreiben unter dem Limit (K2 prüft sonst sofort).

## Was das Update der zwölf wirklich geändert hat

Nur acht der zwölf hatten im Upstream einen neuen Stand; vier waren schon aktuell.

```
ai-seo                 2.7.6 → 2.12.0     competitors           2.3.0 → 2.3.0
analytics              2.0.3 → 2.2.2      cro                   2.0.3 → 2.0.3
competitor-profiling   2.1.3 → 2.1.5      schema                2.0.2 → 2.0.2
content-strategy       2.1.3 → 2.1.5      site-architecture     2.1.0 → 2.1.0
copy-editing           2.1.1 → 2.2.1
copywriting            2.1.0 → 2.3.2
programmatic-seo       2.1.0 → 2.1.1
seo-audit              2.2.0 → 2.2.2
```

Der Update-Pfad hat aber auch **verloren**, was nicht im Upstream steht: Der CLI
schreibt den ganzen Ordner neu. Mit `--skill '*'` traf das die repo-eigene
deutsche `copy-editing`-Ausgabe – `SKILL_DE.md`, `evals/evals-de.json` und vier
`references/*-de.md` (ai-tells, checkliste, werkzeugkette, ymyl-panel, seit
21.09.2026, beschrieben in `docs/ANLEITUNG-COPY-EDITING-HIGHEND.md`). Sechs
Dateien waren weg, und der Vertrag meldete **0 Befunde**. Wiederhergestellt mit
`git checkout HEAD -- .claude/skills/copy-editing/…`; die Dateien liegen
seitdem unverändert im Baum.

Das ist die Lehre des Tages: Ein Werkzeug, das einen Ordner besitzt, löscht
alles, was es nicht kennt – und eine Wache, die nur Lizenzen und `ff-*` kennt,
sieht es nicht.

## Zwei neue Prüfungen (K9, K10) statt einer Notiz

**K9 – Beschreibungs-Budget.** Die Summe aller `description`-Zeichen muss unter
`BESCHREIBUNG_KB_MAX = 56 KB` bleiben (heute 46,1 KB ≈ 11.790 Tokens). Ein
Befund ist nicht die einzelne lange Beschreibung (das ist K2), sondern die
Summe: Wer sie reißt, entscheidet über Vorladelast jeder Session, nicht über
Dateien. Die Grenze ist bewusst **heute** gesetzt und nicht großzügig – sie ist
die Zahl, an der der nächste Schwung begründet werden muss.

**K10 – Zusatzdateien im Fremd-Ordner.** Liegt in einem Fremd-Ordner eine
`SKILL_DE.md`, `evals-de.json` oder `*-de.md`, die nicht aus dem Upstream
kommt, meldet die Wache **eine Warnung je Ordner** (nicht sechs Zeilen für einen
Fall – Rauschen wird überlesen, Lehre aus #729). Warnung, kein Befund: Die Datei
ist ein Rechts- und Bestandsproblem, kein Gate-Fehler; das Gate soll nicht
kneifen, wo Betreiberarbeit nötig ist (dieselbe Linie wie K8, Issue #316).

Beide Prüfungen sind am Sabotage-Fall bewiesen und haben eine Gegenprobe –
Selbsttest jetzt **19 Fälle** (vorher 17), Unit-Tests **37** (vorher 33,
1 übersprungen). Der echte Bestand ist bei K9/K10 warnungsfrei bis auf den
bewusst gemeldeten `copy-editing`-Fall. Eingehängt in `befunde()`; das Gate
`.github/workflows/link-check.yml` ruft dieselbe Wache, es brauchte keine neue
Zeile – nur der Kommentar sagt jetzt K1–K10.

## Nachweis (alles in diesem Lauf ausgeführt)

```
python3 scripts/skills_vertrag.py             → 62 Skills, 0 Befunde, 3 Warnungen
python3 scripts/skills_vertrag.py --selftest  → OK (19 eingefrorene Fälle)
npm run test:skills                           → OK (37 Tests, 1 skipped)
npm run trigger:check                         → 98 Workflows, 0 Befunde
python3 scripts/skript_syntax_wache.py        → 623 Dateien, grün
```

Die drei Warnungen sind keine offenen Fehler, sondern der Stand:

* **K8 ×2** – `scripts/skills_vertrag.py` und `data/skill_lizenzen.json` stehen
  nicht in `FEST`/Siegel. Zeichnen ist ein Betreiberakt (und
  `integrity_guard.py --add` verlangt einen eigenen, ruhigen Lauf) – hier
  absichtlich **nicht** getan, damit keine Unterschrift unter einem Stand
  entsteht, den dieser Lauf selbst verändert hat.
* **K10 ×1** – die sechs `copy-editing`-Dateien. Dauerhaft gehört die deutsche
  Ausgabe in einen `ff-*`-Skill; solange sie im Fremd-Ordner liegt, ist die
  Warnung die Quittung dafür.

## Grenzen, die dazugehören

1. **Der Preis ist dauerhaft.** 11.790 Tokens Beschreibung liegen ab jetzt in
   jeder Session. Das ist die bewusste Entscheidung von heute, keine Messung,
   die sich von selbst erledigt; K9 hält sie sichtbar und begrenzt.
2. **Der Bestand ist nicht versioniert abgesichert.** K4 liest `skills-lock.json`,
   die 53 Ordner liegen als Dateien im Repo. `npx skills update` ist damit
   jederzeit in der Lage, den Baum zu verändern – der Git-Diff ist der einzige
   Zeuge, K10 der einzige Alarm.
3. **Die zwölf sind nicht mehr „unsere".** Wo früher deutsche Ergänzungen im
   `copy-editing`-Ordner lagen, liegt jetzt Upstream-Text; die deutsche Fassung
   steht daneben und ist mit jedem Update erneut zu retten.
4. **Trefferqualität ist nicht gemessen.** 62 Skills mit teils überlappenden
   Beschreibungen (`copywriting` / `copy-editing` / `ff-marke-text`) können
   falsch auslösen. Die `skill-creator`-Auswertung wäre der nächste Schritt –
   nicht Teil dieses Auftrags.
