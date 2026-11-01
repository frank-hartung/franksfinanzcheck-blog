# Social-Skills: 17 Fremd-Skills aufgenommen, Bibliothek am K9-Budget (Highend, 01.11.2026)

> Status: aufgenommen, vertraglich grün, in `main` eingemerged und aufgelöst.
> Wahrheitsort für den Betrieb ist `docs/ANLEITUNG-SKILLS.md`; die Router stehen
> in `.claude/skills/ff-marke-text/SKILL.md` („Fremd-Skills: Social-Pack und
> Marketing-Pack“), `.claude/skills/ff-oberflaeche/SKILL.md` und
> `.claude/skills/ff-pruefen/SKILL.md`. Diese Datei hält Auftrag, Messung,
> Entscheidungen, Preis und den Merge fest.

## Auftrag

```
npx skills add charlie947/social-media-skills
```

Ausgeführt am 01.11.2026 mit der im Runbook gepinnten Fassung
(`npx -y skills@1.7.4 add charlie947/social-media-skills -a claude-code -y`),
weil der Lock-Hash nur vom CLI geschrieben werden darf. Ergebnis: **17 Skills
kopiert**, `skills-lock.json` um 17 Einträge gewachsen.

## Stand (gemessen, nicht geschätzt)

| Befund | Wert am Ende |
|---|---|
| Skill-Ordner unter `.claude/skills/` | **81** (74 vendored + 7 `ff-*`) |
| Einträge in `skills-lock.json` | **74** (57 aus `main` + 17 Social) |
| Einträge in `data/skill_lizenzen.json` | **74** – jeder vendore Skill genau einmal |
| Vendore Skills mit `LICENSE`-Text im Ordner | **74 von 74** |
| `python3 scripts/skills_vertrag.py` | **0 Befunde**, 1 Warnung (K8: Register ungezeichnet, siehe unten) |
| K9-Beschreibungs-Budget | **55,5 von 56 KB** (~14.200 Tokens Vorlast) – die Bibliothek ist am Limit |
| Kern `CLAUDE.md` | 240 Zeilen / 17,6 KB (Budget 420 / 32 KB) |
| `ff-marke-text/SKILL.md` | 156 Zeilen (Budget 200) |

Die Quelle: `charlie947/social-media-skills`, MIT (Copyright (c) 2026 Charlie
Hills), 17 Skills, ~166 KB, letzter Upstream-Push 18.10.2026, nicht archiviert.
Eine reine Anlage aus `SKILL.md`-Dateien – **keine** `.py`-, `.js`- oder
Shell-Dateien, also kein ausführbarer Fremdcode im Baum (Redos-Wache und
Abhängigkeits-Wache damit nicht berührt, nachgesehen statt angenommen).

## Was nach dem CLI nötig war (das Aufnahmeprotokoll aus dem Runbook)

1. **Lizenztext je Ordner.** Der CLI kopiert nur den Skill; K6 verlangt den
   Volltext neben dem `SKILL.md`. 17 × `LICENSE.txt` aus der Upstream-Root
   unverändert übernommen. MIT verlangt die Copyright-Zeile in jeder Kopie –
   „MIT“ als Kürzel im Register erfüllt das nicht. (Der zweite CLI-Lauf nach dem
   Merge hat die Texte erneut entfernt und wurde erneut nachgezogen – genau
   deshalb steht der Schritt im Runbook und nicht im Gedächtnis.)
2. **Register.** 17 Einträge (`quelle` + `lizenz: MIT`) in
   `data/skill_lizenzen.json`, dazu die Quelle unter `standen` und eine `notiz`,
   die die Nutzungsgrenze festhält. Ohne Eintrag meldet K6 bei jedem Lauf einen
   Befund – direkt nach dem CLI waren es 18.
3. **Router.** Ein installierter Skill, den kein Text nennt, wird nicht geladen.
   Die Router-Tabellen stehen dort, wo der Auftrag entsteht – in `ff-marke-text`
   (Social-Pack **und** Marketing-Pack mit je einer Haus-Grenze), in
   `ff-oberflaeche` (`animate`, `cro`) und `ff-pruefen` (`analytics` als *außer
   Betrieb*). Im Kern wurde nur die eine Zeile des Skill-Routers ergänzt; 17
   Zeilen im Kern wären Dauerlast (K1).

## Die Entscheidung, die der Merge erzwungen hat: keine K3-Erweiterung

Zwischenzeitlich hatte dieser Branch K3 auf **jeden** installierten Skill
ausgeweitet (eigener Skill im Kern, vendored im Kern oder `ff-*`-Einstieg, Name
in Rückstrichen; 19 Selbsttest-Fälle, 36 Unit-Tests). Diese Erweiterung ist
**zurückgenommen** – nicht weil sie falsch war, sondern weil `main` für dasselbe
Problem inzwischen eine andere, hausweite Antwort hat:

* `main` hat die Bibliothek am 01.11.2026 auf 57 vendore Skills ausgebaut
  (`cbc43ad6`, #1004) und dafür **K9** (Summe aller Beschreibungen ≤ 56 KB) und
  **K10** (Herkunft repo-eigener Zusatzdateien) eingeführt.
* K3 in der Fassung dieses Branch hätte für diese 57 Skills **57 Router-Zeilen**
  verlangt. Das ist Arbeit an `main`s Bibliotheksplan, nicht an diesem Auftrag –
  und zwei Regime für dieselbe Frage wären eine zweite Wahrheit.
* Die **Router-Tabellen bleiben**: sie benennen rund 20 der neuen Skills mit
  ihrer Haus-Grenze und sind damit der praktische Teil der Idee, ohne eine
  Wache zu verbiegen.

Der Merge ist damit ehrlich: `scripts/skills_vertrag.py` und seine Tests stehen
wieder auf `main`s Fassung (23 Selbsttest-Fälle), die Inhalte dieses Auftrags
(17 Skills, Lizenzen, Register, Router, Dokumentation) sind übernommen.

## Nebenbefund: `animate` – Lücke doppelt geschlossen

`emilkowalski/skills` lag seit dem Design-Rollout installiert im Repo, ohne
`LICENSE.txt` und ohne Registereintrag; K6 hat das gemeldet. Text und Eintrag
sind nachgezogen, `standen` ergänzt. `main` hat dieselbe Lücke am 01.11.2026
parallel geschlossen – die Notiz im Register sagt das jetzt neutral, statt einen
alleinigen Nachtrag zu behaupten.

## Drei Grenzen, die im Router stehen und keine Auslegung sind

1. **Der Kanal-Vertrag gewinnt.** `data/social/channels.yaml` ist die SSOT:
   LinkedIn ist dort `enabled: true`, 2.900 Zeichen hart / 1.800 weich,
   3–5 Hashtags in camelCase am Ende, **kein** Emoji, Link im ersten Kommentar,
   Du-Form, erste Zeile ≤ 12 Wörter. Der Pack kennt nur LinkedIn und hängt
   Hashtags gern in den Textkörper – englische Vorlage, deutscher Hausbrauch.
2. **Keine Fremdwege, keine neuen Secrets (D20/T1).** `post-scorer` (Apify),
   `reels-scripting` (Apify + `GOOGLE_AI_API_KEY`) und `niche-research`
   (Live-Browser) beschreiben Werkzeuge, die dieses Repo nicht hat und laut
   Dauervorgabe nicht bekommt. Genutzt wird der redaktionelle Teil; fehlt der
   Zugang, endet der Skill dort, statt eine Messung zu erfinden.
   `analytics-dashboard` verlangt genau das Dateiformat, das dieses Haus am
   31.08.2026 aus dem Repo entfernt hat (`.xlsx`).
3. **Keine Zahlen aus Fremdtext.** Reichweiten- und CTR-Sätze der Skills sind
   keine Belege dieses Blogs (D15), und die Fremdmessung-Sperre gilt unverändert.

## Der Preis (ehrlich gerechnet)

Skill-Beschreibungen werden **bei jedem Start** geladen, nicht erst bei Bedarf.
Die 17 neuen beschreiben 8.656 Zeichen (~2.164 Tokens). Damit steht die gesamte
Bibliothek bei **56.855 Zeichen = 55,5 KB von 56 KB** (K9) – rund 14.200 Tokens
Vorlast in jeder Session, unabhängig vom Auftrag.

**Das ist der eigentliche Befund dieses Auftrags:** Der nächste Schwung
Fremd-Skills passt nicht mehr ohne Entscheidung. Die Optionen stehen im Runbook:
Beschreibungen kürzen (nur bei repo-eigenen Skills möglich – `npx skills update`
überschreibt Fremdtext), Skills entfernen (CLI), oder die Grenze bewusst
anheben (Entscheidung des Inhabers, nicht eines Agenten).

## Verifikation

| Prüfung | Ergebnis |
|---|---|
| `python3 scripts/skills_vertrag.py` | 0 Befunde, 1 Warnung (K8: Register ungezeichnet – Betreiberakt, siehe unten) |
| `python3 scripts/skills_vertrag.py --selftest` | 23 Fälle grün (`main`s Fassung) |
| `python3 scripts/skript_syntax_wache.py` | 624 Dateien grün (nach Heilung eines kaputten Auto-Merges in `skills_vertrag.py`) |
| `python3 scripts/integrity_guard.py` | Siegel trägt den Kern wieder (nach `--heal`, siehe unten) |
| `python3 -c "fachpruefung_register --check"` | Register aktuell |
| PR-Gate (GitHub) | Qualitäts-Gate, CodeQL, ReDoS/Klartext/URL-Wachen, YMYL, Syntax, Robustheit, Beweis, Entity, Raster, Lesehilfen grün |

## Offener Betreiberakt (K8)

`main` hat am 01.11.2026 (`cbc43ad6`) **`scripts/skills_vertrag.py` und
`data/skill_lizenzen.json` ins Siegel genommen**. Damit ist jede
Register-Änderung – also jede Skill-Aufnahme – eine Siegel-Änderung. Der
vorgesehene Schluss ist ein Zug, nachdem der Stand committet und grün ist:

```bash
python3 scripts/skills_vertrag.py                 # 0 Befunde
python3 scripts/integrity_guard.py --heal         # signiert belegten Drift der Klasse FEST
python3 scripts/integrity_guard.py                # Gegenprobe: „entspricht exakt dem signierten Zustand“
```

Ein Agent, der das Siegel ohne diesen Nachweis nachzieht, hebt den Schutz auf,
den K8 verspricht – deshalb steht es hier und im Runbook, nicht im Kopf.

## Offene Entscheidung des Inhabers

Der Pack ist vollständig aufgenommen; niemand muss etwas tun. Wenn die 2.164
Tokens nicht gewollt sind, ist die Verkleinerung ein CLI-Lauf – Kandidaten mit
externem Dienst oder Format ohne Auftrag in diesem Repo. Nach jedem Entfernen:
Registerzeile und Router-Zeile löschen, `npm run skills:check` fahren.

```bash
npx -y skills@1.7.4 remove reels-scripting -y      # Apify + Gemini, keine Quelle im Haus
npx -y skills@1.7.4 remove analytics-dashboard -y  # .xlsx-Export, im Repo unerwünscht
npx -y skills@1.7.4 remove gemini-carousel -y      # Karussell über externen Bildweg
npx -y skills@1.7.4 remove gemini-infographic -y   # dito
npx -y skills@1.7.4 remove youtube-thumbnail -y    # Format ohne Kanal im Repo
npx -y skills@1.7.4 remove niche-research -y      # Live-Browser, T1-Sperre
```
