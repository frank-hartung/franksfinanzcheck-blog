# ANLEITUNG: Skills und der geteilte Leitfaden

Stand: 01.11.2026 · Verantwortlich: `scripts/skills_vertrag.py` (K1–K10) und
`scripts/skills_portfolio.py` (P1–P7) ·
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
CLAUDE.md                      ← Kern: 242 Zeilen, 18 KB, Nummer ist Vertrag
.claude/skills/
  ff-pruefen/     SKILL.md + references/*.md   ← Details wörtlich aus dem Kern
  ff-lektorat/    SKILL.md + 4 references + evals.md  ← eigene deutsche Ausgabe
  ff-ausliefern/  …
  ff-produzieren/ …
  ff-marke-text/  …
  ff-oberflaeche/ …
  ff-ki-automation/ …
  <fremd>/        SKILL.md + LICENSE.txt       ← aus skills-lock.json, npx skills update
skills-lock.json               ← nur Fremdquellen
data/skill_lizenzen.json       ← Herkunft und Lizenz je Skill
data/skill_portfolio.yaml      ← welches Skill dient welchem Thema (oder ist ausgeschlossen)
data/skill_ergaenzungen.json   ← umgezogene/verlorene Zusatzdateien (K10)
```

## Die sieben Skills und ihre Grenze

| Skill | Zuständig für | Nicht zuständig für |
|---|---|---|
| `ff-pruefen` | Prüfkatalog, Selbsttest-Bau, Wachen-Vertrag, Artefakt-Ganzheit, Manifest, Report-Erzeuger | Reihenfolge im Deploy, Textqualität |
| `ff-ausliefern` | CI, Hugo-Bau-Action, Blustradius, Siegel-Reihenfolge, Alarm-Routing, Scorecard, Backup, Merge | Produktionsregeln der Engine, Gate-Bau |
| `ff-produzieren` | zwei Bahnen, Faktenfrische, Reserve, Slots, Einzigartigkeit, Schreibvertrag | Sprache, Snippet-Grenzen |
| `ff-marke-text` | README-Markenfläche, Abschlussvermerk, ZEIT-Latte, Metadaten/SERP, Tags, Offenlegung, Pins | Layout/CSS |
| `ff-oberflaeche` | Design-Disziplin, Laufzeit-Robustheit, Werkzeuge, `_headers` | Wer wann produziert |
| `ff-ki-automation` | KI-Transportweg, Werkbank, Recherche, Suchradar, Schaltwerk, Kostensperre | Bewertung der Ergebnisse |
| `ff-lektorat` | deutsches Lektorat vor Auslieferung: Seven Sweeps, KI-Tells, YMYL-Panel, Engine-Kette, finale Checkliste | neue Texte schreiben, Layout/CSS |

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

**Achtung, `--skill '*'`.** Ein Aufruf mit allen Skills schreibt **jeden** Ordner
neu – auch die, die schon liegen. Am 01.11.2026 hat genau das die deutsche
`copy-editing`-Ausgabe gelöscht (`SKILL_DE.md`, `evals-de.json`, vier
`references/*-de.md`), und der Vertrag blieb grün.

**Die Lehre ist nicht „retten", sondern „verlassen".** Eine repo-eigene Datei
in einem Fremd-Ordner ist eine Löschung auf Zeit; sie gehört in ein
`ff-*`-Skill, das niemand überschreibt. Genau so ist der Fall geschlossen: die
deutsche Ausgabe ist jetzt `ff-lektorat` (SKILL.md + vier references +
`evals/evals.md`), und `data/skill_ergaenzungen.json` führt den Umzug mit
Herkunft, Ziel und Datum. K10 prüft seither drei Zustände: angekommen (still),
zurückgefallen (Warnung), verloren (Befund).

Für den Notfall bleibt der Blick nach dem Update (Wiederherstellung ist ein
Rettungsgriff, kein Betriebsmodell):

```bash
npx -y skills@1.7.4 add <owner>/<repo> --skill '*' -a claude-code -y
git status --short .claude/skills        # was hat der CLI ersetzt?
git checkout HEAD -- .claude/skills/<ordner>   # nur zur Rettung, dann umziehen
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

## Welche Themen bedient der Blog? (`data/skill_portfolio.yaml`)

Die Frage entsteht bei jedem neuen Fremd-Skill: Es kostet Dauerlast in jeder
Session, auch wenn es nie gelesen wird. Das Portfolio beantwortet sie an einer
Stelle, und `scripts/skills_portfolio.py` hält die Antwort ehrlich.

```
Themen (12)      sechs Inhaltswelten + sechs Kanäle, jede mit Belegpfad
produktion       Skill → Thema + Rolle + Kanal   (29 Skills, ≈ 5.400 Tokens)
ausgeschlossen   Skill → Grund + Entscheidung + Frist   (31 Skills)
```

Die Unterscheidung `art: inhalt | kanal` ist die eigentliche Antwort:

* **inhalt** – die sechs Themenwelten aus `data/themenwelten.json`. Sie werden
  von der Content-Engine mit Artikeln bedient (105 Artikel tragen `pillar:`),
  **nicht** von einem Marketing-Skill. Ein fehlendes Skill ist hier normal;
  ein Thema ohne Artikel ist ein Befund (P7).
* **kanal** – Suche/KI, Text, Werkzeuge, Verbreitung, Messung, Wettbewerb.
  Hier **muss** ein Skill hängen, sonst wird die Achse behauptet (P4).

Ein Kanal ist nur dann ein Kanal, wenn ein Pfad ihn belegt (`kanaele`:
`newsletter-worker`, `scripts/pinterest_ziele.py`, `content/presse` …). Ein
Skill für Discord, Events oder Influencer fällt damit durch – nicht weil es
schlecht ist, sondern weil es hier nichts bedient.

```bash
python3 scripts/skills_portfolio.py             # P1–P7 prüfen
python3 scripts/skills_portfolio.py --selftest  # 15 Sabotage-Fälle + Gegenproben
npm run skills:portfolio                        # dasselbe im Hausstil
```

| Klasse | Prüft | Fund heißt |
|---|---|---|
| P1 | Jedes installierte Fremd-Skill ist einem Thema zugeordnet oder ausgeschlossen | Dauerlast ohne Entscheidung |
| P2 | Jedes Thema und jeder Kanal hat einen existierenden Belegpfad | Das Thema wird behauptet, nicht bedient |
| P3 | Summe der Beschreibungen aller Themen-Skills ≤ `budget_kb` | Der Themenbetrieb wächst ohne Entscheidung |
| P4 | Kanal-Thema hat ein Skill; jedes Skill hat `rolle` und belegte `kanaele` | Achse ohne Fahrer oder Kanal, den es nicht gibt |
| P5 | Ausschluss trägt Grund, Entscheidung, Frist; abgelaufene Frist warnt | Stille Abschaffung |
| P6 | Kein Skill gleichzeitig in `produktion` und `ausgeschlossen` | Eine Entscheidung, zwei Antworten |
| P7 | Jedes Inhaltsthema hat Artikel (`pillar:` im Frontmatter) | Leere Kachel auf der Startseite |

P5 ist **immer nur eine Warnung**. Eine Frist soll erinnern, nicht das Gate
schließen – dieselbe Linie wie K6 und K8.

## Der Nachweis

```bash
python3 scripts/skills_vertrag.py            # K1–K8, Exit 0/1/2
python3 scripts/skills_vertrag.py --md       # für die Lauf-Summary
python3 scripts/skills_vertrag.py --selftest # 16 Sabotage-Fälle + Gegenproben
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
| K8 | Siegelstand: tragen `KRITISCH`/`FEST` und `data/integrity_lock.json` Wache und Lizenz-Register? | Der Regelkern ist austauschbar, ohne dass es laut wird |
| K9 | Summe aller `description` ≤ 56 KB (≈ 14.000 Tokens) | Die Bibliothek wächst still in jede Session hinein |
| K10 | Zusatzdatei in fremdem Ordner (Warnung) und jeder Stand aus `data/skill_ergaenzungen.json` am Ziel | Ein `npx skills update` löscht repo-eigene Dateien ohne Meldung |

K8 ist **immer eine Warnung, nie ein Befund**. Zeichnen ist ein Betreiberakt,
und ein Gate, das eine ungezeichnete Datei hart rot macht, bestraft die falsche
Seite: Am 19.09.2026 (Issue #316) stoppte ein HARD STOP die Content-Engine im
ersten Schritt, weil sechs geheilte Skripte nicht neu gezeichnet waren.

## Im Gate seit 01.11.2026

Der Vertrag läuft nicht nur über `GUARDS` (C6, Reihenfolge der Selbsttests),
sondern als eigener Schritt im Qualitäts-Gate `.github/workflows/link-check.yml`
– Prüfung, Selbsttest und Regressionstests, auf jedem Push, jeder PR und im
nächtlichen Lauf. Der Trigger brauchte keine Änderung (er gilt ohnehin ohne
`paths:`-Filter); ein gefundener Fehlschlag wird vom vorhandenen Schritt
„Gate-Fehlschlag melden“ mit dem gefallenen Schritt Namen gegeben.

## Fremd-Skill aufnehmen, aktualisieren, entfernen

Nie von Hand. Der Skills-CLI ist die einzige Schreibe für `skills-lock.json`,
denn dessen `computedHash` ist **nicht** die SHA-256 von `SKILL.md` – ein von
Hand gesetzter Hash sieht gültig aus und ist es nie (an `frontend-design` und
`webapp-testing` nachgeprüft, 01.11.2026).

```bash
npx -y skills@1.7.4 add <owner>/<repo> --skill <name> -a claude-code -y
npx -y skills@1.7.4 update
npx -y skills@1.7.4 check
npx -y skills@1.7.4 remove <name> -y
```

Ohne `-y` bleibt der CLI an einer Ja/Nein-Frage stehen und tut nichts – im
Automatenlauf heißt das: keine Wirkung, aber ein grüner Schritt. Reihenfolge
bei einer Aufnahme ist immer dieselbe:

1. **CLI laufen lassen** (Ordner + Lock entstehen zusammen).
2. **Lizenztext prüfen** – liegt `LICENSE.txt` im Ordner? Apache-2.0 braucht
   zusätzlich die NOTICE.
3. **`data/skill_lizenzen.json` nachziehen** (`quelle` + `lizenz`; ohne Eintrag
   meldet K6 bei jedem Lauf einen Befund).
4. **Kern-Router und zuständigen Skill verlinken** – ein Skill, den der Kern
   nicht nennt, wird nie geladen (K3).
5. `python3 scripts/skills_vertrag.py` und `npm run trigger:check` laufen lassen.

Entfernen heißt umgekehrt: CLI, dann Register-Eintrag und Quellen-Bezug
(`standen`) nachziehen, dann die Verweise im Kern und im Skill ersetzen. Am
1.11.2026 so gemacht bei `web-design-guidelines`:

> Das Upstream-Repo (vercel-labs/agent-skills) führte **keine** Lizenz, das
> Register trug die Ausnahme mit Frist **31.12.2026**. Verlängert wurde nicht –
> die Frist war der Punkt. Der Skill ist entfernt, die Regel-Substanz liegt
> hausgemacht in `ff-oberflaeche/references/web-richtlinien.md` (24 Punkte, jeder
> mit Gate-Beweis oder benannter Fundstelle), und der Fall steht im Register
> unter `erledigte_faelle`. Der Fall war damit nicht „zugeklappt“, sondern
> gelöst: 18 Fremd-Skills, 18 Lizenztexte.

## Neu im Bestand: `skill-creator` (anthropics/skills, Apache-2.0)

Aufgenommen am 01.11.2026 für das Handwerk am Regelwerk: ein Skill entwerfen,
seine `description` auf Trefferquote optimieren, Evaluationsläufe bauen. Die
Anlage liegt im selben Haus wie `frontend-design` und `webapp-testing`, bringt
ihre `LICENSE.txt` mit und ist die zweite Fremd-Anlage, deren Werkzeuge nichts
an der Website ändern (10 Python-Helfer, drei Agenten-Dokumente, Auswertung in
der Wegwerf-Kopie). Vor der Aufnahme geprüft: Syntaxwache, REDOS-Wache,
Wachen-Vertrag und Fremdmessung-Sperre blieben grün, K6 meldete sofort den
fehlenden Register-Eintrag – so soll es sein.

## Abgelehnt und begründet: `xlsx` (anthropics/skills)

Nicht aufgenommen, und zwar aus zwei Gründen, die beide nachprüfbar sind
(nachgemessen am 01.11.2026 über die GitHub-contents-API):

1. **Die Lizenz verbietet den Vorgang.** `skills/xlsx/LICENSE.txt` (1.467 Bytes)
   ist keine freie Lizenz, sondern „© 2025 Anthropic, PBC. All rights reserved"
   mit ausdrücklichen Einschränkungen: die Materialien dürfen nicht aus dem
   Dienst extrahiert oder außerhalb davon aufbewahrt, nicht vervielfältigt,
   nicht bearbeitet und nicht weitergegeben werden. Ein Vendor-Ordner in einem
   Git-Repository ist genau das. Dieselbe Datei liegt bei `pdf` und `docx`.
   Das Hauszeichen „anthropics/skills" sagt nichts über den Ordner – deshalb
   prüft K6 ab sofort je Eintrag: `MIT` und `Apache-2.0` sind nachprüfbare
   Freigaben, alles andere braucht Grund, Entscheidung und Frist (und trotzdem
   den Volltext im Ordner, wenn es einen gibt).
2. **Es gibt nichts, was der Skill hier täte.** `skills/xlsx` bringt 63 Dateien
   und 1.102.893 Bytes mit (`SKILL.md` 99 Zeilen / 8.598 Bytes,
   `scripts/recalc.py` 10.670 Bytes, dazu ein `scripts/office`-Baum). Im Repo
   liegt keine Tabellenkalkulation und kein Lese- oder Schreibwerkzeug dafür –
   am 31.08.2026 sind `docs/Pinterest-Blog-Verlinkungsplan.xlsx` und
   `docs/Pinterest-Wachstums-Workbook.pdf` daraus entfernt worden mit der
   Begründung „gehören in Notion/Drive, nicht ins Git-Repo (verlangsamen Clone)"
   (`docs/CLEANUP-REPORT-2026-08-31.md`). Eine 1,1-MB-Anlage für eine Aufgabe,
   die das Haus abgeschafft hat, ist keine Reserve.

**Wiedervorlage nur bei zwei Bedingungen:** es entsteht ein Tabellenformat, das
wirklich im Repo liegen muss, **und** die Nutzung ist schriftlich mit dem
Rechteinhaber geklärt. Dann läuft das Aufnahmeprotokoll von oben, der
Register-Eintrag trägt den wirklichen Lizenzwortlaut – nicht beschönigt auf ein
Kürzel – plus Ausnahme mit Grund, Entscheidung und Frist, und K6 meldet, solange
die Frist läuft. Eine Frist ohne Entscheidung ist hier kein
Aufschub, sondern der Bericht, dass niemand entschieden hat.

## Aufgenommen am 01.11.2026: `emil-design-eng` (emilkowalski/skills, MIT)

Auftrag war der Befehl `npx skills add emilkowalski/skill`. Das Repo heißt
inzwischen `emilkowalski/skills` (GitHub leitet weiter, `/skill` → `/skills`),
es trägt 16 Skills und liegt unter MIT (1.070-Byte-`LICENSE`, Copyright 2026
Emil Kowalski).

**Nicht alle 16.** Von den 16 deckt genau einer einen bereits gebauten Teil
dieser Website ab: Bewegung und Interaktions-Feedback. Die übrigen 15 sind für
dieses Repo entweder gegenstandslos oder schädlich:

| Skill(s) | Warum nicht |
|---|---|
| `animate-expo`, `write-swift`, `mobile-native` | React Native / Expo, Swift, iOS – das Repo ist Hugo + Papier-CSS, kein App-Build |
| `ask-sonner` | Sonner ist eine React-Toast-Bibliothek; im Repo gibt es kein React |
| `break-ui`, `prototype`, `pick-ui-library` | Werkbänke für App-Komponenten; UI-Änderungen laufen hier über Variante + Messung + Freigabe (`docs/ANLEITUNG-DESIGN-VARIANTEN.md`), nicht über einen Prototyp |
| `animate`, `improve-animations`, `review-animations`, `find-animation-opportunities`, `animation-performance`, `animation-vocabulary`, `apple-design` | Motion-Werkstatt; die Entscheidungen, die hier zählen (CSS-Transition, `prefers-reduced-motion`, CLS, Dark Mode), stehen in `ff-oberflaeche` + `emil-design-eng`. Acht weitere Beschreibungen im Dauer-Kontext wären Last ohne neue Regel |

**Befehl, wie er lief** (Version gepinnt wie im Runbook oben, `-y` gegen die
Ja/Nein-Frage):

```bash
npx -y skills@1.7.4 add emilkowalski/skill --skill emil-design-eng -a claude-code -y
```

Ergebnis: `.claude/skills/emil-design-eng/SKILL.md` (27.123 Bytes) **und** der
Lock-Eintrag entstanden zusammen; `computedHash` kommt vom CLI, nicht von Hand.
Danach nach Protokoll: `LICENSE.txt` aus der Upstream-Root unverändert kopiert
(MIT, kein `NOTICE` nötig), Register-Eintrag `quelle` + `lizenz: MIT` in
`data/skill_lizenzen.json`, Quelle in `standen`, und die Router-Zeile in
`CLAUDE.md` (UI-Tabelle) plus die Fünf-Nennung in
`ff-oberflaeche/SKILL.md`. `python3 scripts/skills_vertrag.py` meldet seither
25 Skills, 0 Befunde – vor dem Register-Eintrag meldete K6 genau einen.

**Was der Skill hier tut:** Easing- und Timing-Entscheidungen für Übergänge,
Hover/Fokus-Rückmeldung, Druck-Feedback, `prefers-reduced-motion` als Pflicht
statt Höflichkeit, Detailpolitur an Komponenten. Er ändert keine Regel dieser
Website – `PRODUCT.md`, `DESIGN.md`, `README.md`-Markenfläche und die
24-Punkte-Richtlinie in `ff-oberflaeche/references/web-richtlinien.md` bleiben
die Wahrheitsorte; der Skill liefert das Handwerk, das Urteil bleibt hausgemacht.
