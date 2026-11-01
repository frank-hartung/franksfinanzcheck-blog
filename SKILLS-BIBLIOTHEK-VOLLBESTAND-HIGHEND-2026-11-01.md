# Skills-Bibliothek: Vollbestand, Rückbau der themenfernen, zwei neue Wachen (Highend, 01.11.2026)

> Status: umgesetzt, gemessen, geprüft. Enthält den Vollbestand (53) **und** den
> Rückbau um `sms`/`paywalls`/`aso` am selben Tag – beide Zahlen stehen unten,
> der Rückbau ist die gültige: **64** Skill-Ordner, davon **57** aus sechs
> Fremd-Quellen (50 `coreyhaines31/marketingskills`, 3 `anthropics/skills` und
> je 1 aus `Panniantong/Agent-Reach`, `emilkowalski/skills`,
> `Leonxlnx/taste-skill`, `pbakaus/impeccable`) und **7** repo-eigen (`ff-*`).
> Betriebsanleitung: `docs/ANLEITUNG-SKILLS.md`.
>
> **Nachtrag 01.11.2026, abends:** Die Zahlen dieses Berichts stammen aus dem
> Lauf am Vormittag (62/56/6, 11.790 Tokens). Seitdem kamen der
> Themen-Portfolio-Schnitt, das eigene `ff-lektorat` und der geerbte
> `animate`-Skill dazu – der gültige Stand steht in
> `SKILLS-PORTFOLIO-THEMEN-SIEGEL-LEKTORAT-HIGHEND-2026-11-01.md`. Die Tabelle
> unten ist auf diesen Stand nachgezogen, damit sie nicht als zweite Wahrheit
> stehen bleibt; die Erzählung des Tages ist unverändert historisch.
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
| Skill-Ordner unter `.claude/skills/` | 24 | 65 | **62** → **64** |
| davon Fremd-Skills | 18 | 59 | **56** → **57** |
| davon repo-eigen (`ff-*`) | 6 | 6 | **6** → **7** |
| Einträge in `skills-lock.json` | 18 | 59 | **56** → **57** |
| Dateien im Skill-Baum | ~250 | 687 | **667** → **671** |
| Lizenztexte in den Fremd-Ordnern | 18 | 59 | **56** → **57** |
| Summe aller `description` | 16.198 Zeichen (≈ 4.050 Tokens) | 49.142 · 48,0 KB · ≈ 12.285 Tokens | **46.272 Zeichen · 45,2 KB · ≈ 11.568 Tokens** |
| Beschreibungen über dem Limit 1.024 | 0 | 0 (längste: `social` 1.021) | **0** |
| `skills_vertrag.py` | 0 Befunde, 2 Warnungen | 0 Befunde, 3 Warnungen | **0 Befunde, 0 Warnungen** (K8 geheilt, K10 geheilt) |

Die letzte Spalte führt beide Stände: links die Zahl des Vormittagslaufs,
rechts der heute gemessene. Zur Ehrlichkeit der Herkunft: Die 62/56/6 und die
47.162 Zeichen (≈ 11.790 Tokens) stammen aus dem Vormittagslauf, dessen Baum in
diesem Branch nicht mehr existiert (die Historie wurde am selben Tag neu
aufgebaut). Sie sind hier **nicht nachrechenbar** und stehen deshalb als
Protokoll, nicht als Messwert.

Was nachrechenbar ist: heute 64 Ordner, 57 Fremd, 7 eigen, 46.272 Zeichen
(≈ 11.568 Tokens). Die Differenz von −890 Zeichen gegenüber dem Protokoll lässt
sich nicht auf einzelne Skills zurückführen – zwei Skills kamen hinzu
(`ff-lektorat` 490, `animate` 472 Zeichen), die Gegenbuchung liegt in den
Fremd-Beschreibungen, ohne dass ich sie hier pro Datei belegen könnte. Wer die
Dauerlast beurteilen will, nimmt die **11.568**; wer die Entscheidung von
damals nachlesen will, die 11.790.

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
Posten bleibt die Entscheidung für die Bibliothek selbst (~11.790 Tokens am
Vormittag, seit dem Abendlauf 11.568), und
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
`BESCHREIBUNG_KB_MAX = 56 KB` bleiben (am 01.11. vormittags 46,1 KB ≈ 11.790
Tokens, abends 45,2 KB ≈ 11.568 Tokens). Ein
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
python3 scripts/skills_vertrag.py             → 64 Skills, 0 Befunde, 0 Warnungen
python3 scripts/skills_vertrag.py --selftest  → OK (21 eingefrorene Fälle)
npm run test:skills                           → OK (37 Tests, 1 skipped)
npm run trigger:check                         → 98 Workflows, 0 Befunde
python3 scripts/skript_syntax_wache.py        → 624 Dateien, grün
```

Der Stand der drei Warnungen von damals – **beide geheilt**, jeweils an der
Ursache statt an der Meldung:

* **K8 ×2 – geheilt.** `scripts/skills_vertrag.py` und
  `data/skill_lizenzen.json` stehen seit dem Abendlauf in `FEST` und sind
  signiert (der Betreiberakt, der hier bewusst offenblieb, ist nachgeholt).
* **K10 ×1 – geheilt.** Die sechs deutschen `copy-editing`-Dateien liegen nicht
  mehr im Fremd-Ordner, sondern als eigenes `ff-lektorat` im Haus. Damit
  überlebt die Betreiberarbeit jedes `npx skills update`, und der Fremd-Ordner
  ist wieder der des Upstream – bytegleich, wie es sein soll.

## Grenzen, die dazugehören

1. **Der Preis ist dauerhaft.** 11.568 Tokens Beschreibung (Stand Abend;
   vormittags 11.790) liegen ab jetzt in jeder Session. Das ist die bewusste
   Entscheidung von heute, keine Messung, die sich von selbst erledigt; K9 hält
   sie sichtbar und begrenzt.
2. **Der Bestand ist nicht versioniert abgesichert.** K4 liest `skills-lock.json`,
   die 53 Ordner liegen als Dateien im Repo. `npx skills update` ist damit
   jederzeit in der Lage, den Baum zu verändern – der Git-Diff ist der einzige
   Zeuge, K10 der einzige Alarm.
3. **Die zwölf sind nicht mehr „unsere".** Wo früher deutsche Ergänzungen im
   `copy-editing`-Ordner lagen, liegt jetzt Upstream-Text; die deutsche Fassung
   steht daneben und ist mit jedem Update erneut zu retten.
4. **Trefferqualität ist nicht gemessen.** 64 Skills mit teils überlappenden
   Beschreibungen (`copywriting` / `copy-editing` / `ff-marke-text`) können
   falsch auslösen. Die `skill-creator`-Auswertung wäre der nächste Schritt –
   nicht Teil dieses Auftrags.
