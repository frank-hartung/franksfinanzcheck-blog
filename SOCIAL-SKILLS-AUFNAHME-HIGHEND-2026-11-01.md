# Social-Skills: 17 Fremd-Skills aufgenommen, `animate` nachgewiesen (Highend, 01.11.2026)

> Status: aufgenommen und vertraglich grün. Wahrheitsort für den Betrieb ist
> `docs/ANLEITUNG-SKILLS.md`; der Router für den Alltag steht in
> `.claude/skills/ff-marke-text/SKILL.md` („Fremd-Skills für Social-Texte“).
> Diese Datei hält Auftrag, Messung, Entscheidungen und Preis fest.

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
| `python3 scripts/skills_vertrag.py` | 1 Befund (`animate`, K6) | **0 Befunde**, 2 Warnungen (K8, Betreiberakt) |
| Kern `CLAUDE.md` | 239 Zeilen / 17,4 KB | 240 Zeilen / 17,6 KB (Budget 420 / 32 KB) |
| `ff-marke-text/SKILL.md` | 85 Zeilen | 129 Zeilen (Budget 200) |

Die Quelle: `charlie947/social-media-skills`, MIT (Copyright (c) 2026 Charlie
Hills), 17 Skills, ~166 KB, letzter Upstream-Push 18.10.2026, kein archiviertes
Repo. Eine reine Anlage aus `SKILL.md`-Dateien – **keine** `.py`-, `.js`- oder
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
   Die Router-Tabelle steht deshalb dort, wo der Auftrag entsteht – in
   `ff-marke-text` („Was draußen als Text steht“), nicht als 17 Zeilen im Kern
   (K1). Im Kern wurde nur die eine Zeile des Skill-Routers ergänzt
   („Social-Texte (LinkedIn-Pack)“), kein Abschnitt, keine zweite Zahl.

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
(LinkedIn, Priorität 3). Wer die Last senken will, entfernt Skills; das Kürzen
von Beschreibungen hält nicht, weil `npx skills update` sie überschreibt.

## Verifikation (alles am 01.11.2026 gelaufen)

| Prüfung | Ergebnis |
|---|---|
| `python3 scripts/skills_vertrag.py` | 0 Befunde, 2 Warnungen (K8: Wache und Register ungezeichnet – Betreiberakt) |
| `python3 scripts/skills_vertrag.py --selftest` | 17 Fälle grün |
| `python3 -m unittest scripts.tests.test_skills_vertrag` | 33 Tests OK (1 Skip: Umzugs-Auszug `.cache/CLAUDE.md.orig` liegt nicht mehr vor) |
| `python3 scripts/skript_syntax_wache.py` | 623 Dateien grün |
| `python3 scripts/fremdmessung_sperre.py` | keine Spur, grün |
| `python3 scripts/trigger_wache.py --check` | 98 Workflows, 0 Befunde |
| `python3 scripts/governance_contract.py --quick` | **nicht lauffähig in dieser Umgebung**: `pinterest_ziele.py` importiert `yaml`, PyYAML fehlt (vorbestehend, unabhängig von dieser Änderung) |

## Offene Entscheidung des Inhabers

Der Pack ist vollständig aufgenommen; niemand muss etwas tun. Wenn die 2.200
Tokens Dauerlast nicht gewollt sind, ist die Verkleinerung ein CLI-Lauf, kein
Handgriff am Lock – Kandidaten in dieser Reihenfolge (externer Dienst oder
Format ohne Auftrag in diesem Repo):

```bash
npx -y skills@1.7.4 remove reels-scripting -y      # Apify + Gemini, keine Quelle im Haus
npx -y skills@1.7.4 remove analytics-dashboard -y  # .xlsx-Export, im Repo unerwünscht
npx -y skills@1.7.4 remove gemini-carousel -y      # Karussell über externen Bildweg
npx -y skills@1.7.4 remove gemini-infographic -y   # dito
npx -y skills@1.7.4 remove youtube-thumbnail -y    # Format ohne Kanal im Repo
npx -y skills@1.7.4 remove niche-research -y       # Live-Browser, T1-Sperre
```

Danach Registerzeile und Router-Zeile nachziehen, `npm run skills:check`
fahren – Entfernen ist derselbe Vorgang wie Aufnehmen, nur rückwärts.
