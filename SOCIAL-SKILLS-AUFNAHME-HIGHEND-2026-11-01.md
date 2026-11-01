# Social-Skills: 17 Fremd-Skills aufgenommen, Router-Pflicht für alle (Highend, 01.11.2026)

> Status: aufgenommen, geheilt, vertraglich grün. Wahrheitsort für den Betrieb ist
> `docs/ANLEITUNG-SKILLS.md`; die Router stehen in
> `.claude/skills/ff-marke-text/SKILL.md` („Fremd-Skills: Social-Pack und
> Marketing-Pack“), `.claude/skills/ff-oberflaeche/SKILL.md` und
> `.claude/skills/ff-pruefen/SKILL.md`. Diese Datei hält Auftrag, Messung,
> Entscheidungen und Preis fest.

## Auftrag

```
npx skills add charlie947/social-media-skills
```

Ausgeführt am 01.11.2026 mit der im Runbook gepinnten Fassung
(`npx -y skills@1.7.4 add charlie947/social-media-skills -a claude-code -y`),
weil der Lock-Hash nur vom CLI geschrieben werden darf. Ergebnis: **17 Skills
kopiert**, `skills-lock.json` von 19 auf **36** Einträge gewachsen.

## Ausgangslage und Stand (gemessen, nicht geschätzt)

| Befund | vor der Aufnahme | nach der Aufnahme |
|---|---|---|
| Skill-Ordner unter `.claude/skills/` | 25 (19 fremd + 6 `ff-*`) | **42** (36 fremd + 6 `ff-*`) |
| Einträge in `skills-lock.json` | 19 | **36** |
| Einträge in `data/skill_lizenzen.json` | 18 | **36** (jeder fremde Skill genau einmal) |
| Fremd-Skills mit `LICENSE`-Text im Ordner | 18 von 19 | **36 von 36** |
| Fremd-Skills ohne Router | 13 (unsichtbar: K3 prüfte nur `ff-*`) | **0** |
| `python3 scripts/skills_vertrag.py` | 1 Befund (`animate`, K6) | **0 Befunde**, 2 Warnungen (K8, Betreiberakt) |
| Kern `CLAUDE.md` | 239 Zeilen / 17,4 KB | 240 Zeilen / 17,6 KB (Budget 420 / 32 KB) |
| `ff-marke-text/SKILL.md` | 85 Zeilen | 155 Zeilen (Budget 200) |

Die Quelle: `charlie947/social-media-skills`, MIT (Copyright (c) 2026 Charlie
Hills), 17 Skills, ~166 KB, letzter Upstream-Push 18.10.2026, nicht archiviert.
Eine reine Anlage aus `SKILL.md`-Dateien – **keine** `.py`-, `.js`- oder
Shell-Dateien, also kein ausführbarer Fremdcode im Baum (Redos-Wache und
Abhängigkeits-Wache damit nicht berührt, nachgesehen statt angenommen).

## Was nach dem CLI nötig war (das Aufnahmeprotokoll aus dem Runbook)

1. **Lizenztext je Ordner.** Der CLI kopiert nur den Skill; K6 verlangt den
   Volltext neben dem `SKILL.md`. 17 × `LICENSE.txt` aus der Upstream-Root
   unverändert übernommen. MIT verlangt die Copyright-Zeile in jeder Kopie –
   „MIT“ als Kürzel im Register erfüllt das nicht.
2. **Register.** 17 Einträge (`quelle` + `lizenz: MIT`) in
   `data/skill_lizenzen.json`, dazu die Quelle unter `standen` und eine `notiz`,
   die die Nutzungsgrenze festhält. Ohne Eintrag meldet K6 bei jedem Lauf einen
   Befund – das war direkt nach dem CLI der Fall (18 Befunde).
3. **Router.** Ein installierter Skill, den kein Text nennt, wird nicht geladen.
   Die Router-Tabelle steht dort, wo der Auftrag entsteht – in `ff-marke-text`
   („Was draußen als Text steht“), nicht als 17 Zeilen im Kern (K1). Im Kern
   wurde nur die eine Zeile des Skill-Routers ergänzt
   („Social-Texte (LinkedIn-Pack)“), kein Abschnitt, keine zweite Zahl.
4. **Die Klasse heilen, nicht den Einzelfall.** Siehe nächster Abschnitt – der
   Aufnahme-Lauf hat gezeigt, dass 13 Fremd-Skills in *keinem* Router standen.

## Die Klasse statt des Einzelfalls: K3 gilt jetzt für jeden Skill

Beim Nachtragen der Router-Zeilen fiel der eigentliche Befund auf: **K3 prüfte
nur `ff-*`**. Für vendored Skills gab es keine Router-Pflicht – sie bezahlten
ihre Beschreibung bei jedem Start und wurden nie ausgewählt. Nachgemessen:

* mit der alten, groben Prüfung (Name irgendwo als Zeichenkette): **10** Skills
  ohne Router;
* mit der neuen, genauen Prüfung (Name in Rückstrichen, wie das Repo ihn überall
  schreibt): **13** – `analytics`, `schema` und `cro` kamen vorher durch, weil
  das Wort zufällig in einer Prosa-Zeile stand. Ein Router, der „Analytics“ im
  Satz sagt, routet keinen Skill.

Geheilt wurde beides: die Wache und der Bestand.

| Ort | Was jetzt dort steht |
|---|---|
| `scripts/skills_vertrag.py` (K3) | Router-Pflicht für **jeden** installierten Skill: eigener Skill → Kern; vendored → Kern **oder** ein `ff-*`-Einstieg, jeweils in Rückstrichen. `references/` zählt nicht (was erst nach dem Nachlesen sichtbar wird, ist kein Router). |
| `ff-marke-text` | Marketing-Pack: `site-architecture`, `seo-audit`, `schema`, `programmatic-seo`, `ai-seo`, `competitor-profiling`, `competitors`, `content-strategy`, `copywriting`, `copy-editing` – jede Zeile mit der Grenze, die im Haus gilt. |
| `ff-oberflaeche` | `animate` (Bewegung) und `cro` (Conversion) im UI-Router. |
| `ff-pruefen` | `analytics` als **außer Betrieb**: der Skill beschreibt Tracking-Einbau, den die Fremdmessung-Sperre verbietet. |

Beweis statt Behauptung: `--selftest` hat jetzt **19** eingefrorene Fälle
(neu: fremder Skill ohne Router, mit Gegenprobe „im `ff-*`-Einstieg genannt →
still“), `scripts/tests/test_skills_vertrag.py` **36** Tests (drei neue: Befund,
Gegenprobe über `ff-*`, und der Prosa-Fall „Name ohne Rückstriche ist kein
Router“). Der Lizenz-Fixture trägt seinen Router jetzt selbst, damit K6-Fälle
weiter K6 messen und nicht versehentlich K3.

## Nebenbefund, den K6 sofort gefunden hat: `animate`

`emilkowalski/skills` lag seit dem Design-Rollout installiert im Repo – **ohne
`LICENSE.txt` und ohne Registereintrag**. Das war kein Schaden dieser Aufnahme,
sondern der erste Lauf der Wache am eigenen Bestand: Am 01.11.2026 stand in der
Umbau-Doku „18 Fremd-Skills, 18 Lizenztexte“, installiert waren 19. Der
MIT-Text (Copyright (c) 2026 Emil Kowalski) ist nachgezogen, der Registereintrag
ergänzt, `standen` um die Quelle erweitert. Der Satz von damals stimmt seit
heute; die damalige Datei bleibt als Historie unverändert stehen.

## Drei Grenzen, die im Router stehen und keine Auslegung sind

1. **Der Kanal-Vertrag gewinnt.** `data/social/channels.yaml` ist die SSOT:
   LinkedIn ist dort `enabled: true`, 2.900 Zeichen hart / 1.800 weich,
   3–5 Hashtags in camelCase am Ende, **kein** Emoji, Link im ersten Kommentar,
   Du-Form, erste Zeile ≤ 12 Wörter. Der Pack kennt nur LinkedIn und hängt
   Hashtags gern in den Textkörper – englische Vorlage, deutscher Hausbrauch.
2. **Keine Fremdwege, keine neuen Secrets (D20/T1).** `post-scorer` (Apify),
   `reels-scripting` (Apify + `GOOGLE_AI_API_KEY`) und `niche-research`
   (Live-Browser) beschreiben Werkzeuge, die dieses Repo nicht hat und laut
   Dauervorgabe nicht bekommt. Genutzt wird der redaktionelle Teil – Checklisten,
   Musterfragen, Strukturen; fehlt der Zugang, endet der Skill dort, statt eine
   Messung zu erfinden. `analytics-dashboard` verlangt genau das Dateiformat,
   das dieses Haus am 31.08.2026 aus dem Repo entfernt hat (`.xlsx`): nutzbar
   nur als Wegwerf-Auswertung außerhalb von Git.
3. **Keine Zahlen aus Fremdtext.** Reichweiten- und CTR-Sätze der Skills sind
   keine Belege dieses Blogs (D15), und die Fremdmessung-Sperre gilt unverändert.

## Der Preis (ehrlich gerechnet)

Skill-Beschreibungen werden **bei jedem Start** geladen, nicht erst bei Bedarf.
Gemessen über die `description`-Felder aller installierten Skills:

| Gruppe | Skills | Zeichen | ≈ Tokens |
|---|---|---|---|
| neu aufgenommen (Social-Pack) | 17 | 8.656 | **~2.164** |
| fremd, vorher schon da | 19 | 12.752 | ~3.188 |
| repo-eigen (`ff-*`) | 6 | 3.913 | ~978 |
| **Summe** | **42** | **25.321** | **~6.330** |

Dazu 36 Dateien / 169.682 Bytes im Baum für den neuen Pack (Vendor-Text,
versioniert wie alle bisherigen Fremd-Skills). Rund 2.200 Tokens Dauerlast sind
kein Nebensatz: Die Umbau-Entscheidung vom 01.11.2026 hat einen zweiten Schwung
Fremd-Skills mit **~1.500** Tokens Dauerlast *abgelehnt*. Diese Aufnahme
überschreitet diese Linie – bewusst und auf Auftrag, weil sie nicht Gate-Wissen
dupliziert, sondern Handwerk für einen Kanal liefert, der tatsächlich sendet
(LinkedIn, Priorität 3). Genau deshalb ist die Router-Pflicht jetzt scharf: Was
Dauerlast kostet, muss wenigstens auffindbar sein. Wer die Last senken will,
entfernt Skills; das Kürzen von Beschreibungen hält nicht, weil
`npx skills update` sie überschreibt.

## Verifikation (alles am 01.11.2026 gelaufen)

| Prüfung | Ergebnis |
|---|---|
| `python3 scripts/skills_vertrag.py` | 0 Befunde, 2 Warnungen (K8: Wache und Register ungezeichnet – Betreiberakt, siehe unten) |
| `python3 scripts/skills_vertrag.py --selftest` | 19 Fälle grün (17 vorher + Router-Fall mit Gegenprobe) |
| `npm run test:skills` | 36 Tests OK (1 Skip: Umzugs-Auszug `.cache/CLAUDE.md.orig` liegt nicht mehr vor) |
| `python3 scripts/skript_syntax_wache.py` | 623 Dateien grün |
| `python3 scripts/fremdmessung_sperre.py` | keine Spur, grün (auch nach der `analytics`-Sperrnotiz) |
| `python3 scripts/trigger_wache.py --check` | 98 Workflows, 0 Befunde |
| `python3 scripts/governance_contract.py --quick` | **43 Regeln grün** – im ersten Anlauf scheiterte der Lauf an fehlendem PyYAML; nach Installation der gepinnten Fassung (`pyyaml==6.0.3` aus `requirements-ci.in`) läuft er durch |
| `python3 -m unittest discover -s scripts/tests` | 4.975 Tests; nach den zwei Test-Heilungen und dem Register bleiben **1** Fehlschlag: der Siegel-Drift aus `1491ec7` (Betreiberakt, siehe oben) |
| `npm run build:vertrag` / Hugo-Bau | nicht angetastet: diese Änderung berührt kein Template, keinen Workflow, keine Pipeline-Stufe |

## Offener Betreiberakt (K8) – Besitzer und Schließpfad

Die zwei K8-Warnungen sind kein Befund und blockieren nichts, aber sie brauchen
einen Besitzer (D12): **Inhaber**, nicht Agent – `data/integrity_lock.json` steht
auf der Liste der sicherheitsrelevanten Dateien, die nur mit ausdrücklichem
Auftrag geändert werden. Der Schluss ist ein Zug, wenn der Stand grün ist:

```bash
python3 scripts/skills_vertrag.py            # muss 0 Befunde zeigen (heute: 0)
python3 scripts/integrity_guard.py --add=scripts/skills_vertrag.py
python3 scripts/integrity_guard.py --add=data/skill_lizenzen.json
python3 scripts/integrity_guard.py           # Gegenprobe: Siegel trägt beide
```

Bis dahin gilt: Wer die Wache oder das Register austauscht, tauscht eine
Entscheidung aus, ohne dass es laut wird – das ist der Grund, warum K8 die
beiden Dateien überhaupt aufführt.

## Befund aus dem Vorbestand: `main` ist am Siegel rot (nicht aus diesem PR)

Das PR-Gate „Integritäts-Siegel“ meldet rot – **vor** dieser Arbeit und ohne
Zusammenhang mit ihr. Der Guard nennt die Abweichung selbst:

```
🟠 Festrelevante Abweichungen: scripts/redaktions_standard.py
| Datei | Klasse | Arbeitsbaum | Herkunft | Urteil |
| scripts/redaktions_standard.py | fest | = HEAD | zuletzt: 1491ec7 (2026-11-01, #1003) | VERSIEGELBAR |
```

Belege, dass es nicht dieser Branch ist:

* `scripts/redaktions_standard.py` ist im Siegel (`data/integrity_lock.json`),
  wurde zuletzt in **`1491ec7`** angefasst – dem Commit, auf dem dieser Branch
  aufsetzt;
* `git diff 1491ec7..HEAD -- scripts/redaktions_standard.py` ist leer;
* `scripts/skills_vertrag.py` und `data/skill_lizenzen.json` stehen **nicht**
  im Siegel (genau das meldet K8) – dieser Branch kann das Siegel also gar
  nicht brechen.

Der Schluss ist ein Betreiberakt, weil `data/integrity_lock.json` auf der Liste
der sicherheitsrelevanten Dateien steht: `python3 scripts/integrity_guard.py
--heal` signiert ausschließlich belegten, committeten Drift der Klasse FEST –
hier genau der Fall; `--set-current` bleibt die menschliche Entscheidung für
kritische Knoten. Ein Agent, der das Siegel stillschweigend nachzieht, hebt
genau den Schutz auf, den der Guard verspricht.

## Nebenbefund: `main` war vor diesem PR viermal rot – zwei Klassen geheilt

Der PR-Regressionslauf (`publication-reliability-tests.yml`,
`python3 -m unittest discover -s scripts/tests`, 4.975 Tests) war **vor** diesem
Branch rot. Vier Fehlschläge, alle mit Herkunft außerhalb dieses Auftrags:

| Test | Ursache | Behandlung |
|---|---|---|
| `test_backup_einrichtung.AnleitungVertrag.test_leitfaden_und_npm_skript` | suchte `scripts/backup_einrichtung.py` **nur** in `CLAUDE.md`; der Name liegt seit dem Umbau vom 01.11.2026 in `ff-ausliefern/references/bestand-backup-merge.md` | **geheilt**: der Test liest den Leitfaden, wie er seit dem Umbau existiert – Kern **plus** `ff-*`-Skills (dieselbe Regel, die K3 auf der Skill-Seite durchsetzt) |
| `test_robustheits_gate.VerdrahtungTests.test_dokumentation_ist_verlinkt` | dito für `robustheits_gate.py` (liegt in `ff-oberflaeche`) | **geheilt**, gleicher Helfer |
| `test_inhalts_register.FachpruefungRegisterTests.test_register_ist_aktuell` | `data/fachpruefung_register.yaml` war veraltet (Artikel wurden umformuliert, Register nicht neu erzeugt) | **geheilt** über den Erzeuger, nicht von Hand: `python3 scripts/fachpruefung_register.py` – 6 Zeilen, ausschließlich abgeleitete Zitate (D7) |
| `test_integrity_guard.RepoSealTests.test_ausgelieferter_baum_passt_zum_siegel` | Siegel-Drift aus `1491ec7` (`scripts/redaktions_standard.py`) | **nicht angefasst**: Betreiberakt, siehe Abschnitt oben |

Die ersten beiden sind derselbe Fehlertyp wie der Kern dieses PRs: Ein Prüfer
zeigt auf den alten Ablageort, nachdem das Regelwerk umgezogen ist. Ein Test,
der „Regel verschwunden“ meldet, obwohl sie nur in einem Skill liegt, ist die
Test-Variante von „Skill ohne Router“ – er wird rot, ohne dass etwas fehlt.

## Offene Entscheidung des Inhabers

Der Pack ist vollständig aufgenommen; niemand muss etwas tun. Wenn die 2.200
Tokens Dauerlast nicht gewollt sind, ist die Verkleinerung ein CLI-Lauf, kein
Handgriff am Lock – Kandidaten in dieser Reihenfolge (externer Dienst oder
Format ohne Auftrag in diesem Repo). Nach jedem Entfernen: Registerzeile und
Router-Zeile löschen, `npm run skills:check` fahren (K4, K6 und jetzt auch K3
melden jede Waise).

```bash
npx -y skills@1.7.4 remove reels-scripting -y      # Apify + Gemini, keine Quelle im Haus
npx -y skills@1.7.4 remove analytics-dashboard -y  # .xlsx-Export, im Repo unerwünscht
npx -y skills@1.7.4 remove gemini-carousel -y      # Karussell über externen Bildweg
npx -y skills@1.7.4 remove gemini-infographic -y   # dito
npx -y skills@1.7.4 remove youtube-thumbnail -y    # Format ohne Kanal im Repo
npx -y skills@1.7.4 remove niche-research -y       # Live-Browser, T1-Sperre
```
