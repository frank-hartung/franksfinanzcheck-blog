# Offene Änderungsvorschläge: Bestandsaufnahme und Bereinigung – 14.11.2026

**Auftrag:** Die fünf am 14.11.2026 offenen Änderungsvorschläge (#1217, #1174, #1173, #1171, #1167) vollständig und dauerhaft klären.
**Messstand:** `main` bei `389d4c8b5` (14.11.2026, 17:16 UTC). Alle Zahlen dieses Berichts sind an diesem Stand gemessen; die Befehle stehen jeweils dabei.

## Ergebnis in vier Sätzen

1. Keiner der fünf Vorschläge lässt sich zusammenführen, ohne Heilungen zurückzudrehen, die `main` seither bekommen hat: `main` ist ihnen um 170 bis 210 Commits voraus und hat ihre Themen in #1162, #1168, #1177, #1201, #1207, #1214, #1216, #1218 und #1219 teils übernommen, teils bewusst anders entschieden.
2. Was aus den Vorschlägen noch fehlte und ohne Fachentscheidung nachziehbar war, ist in diesem Zweig nachgezogen: ein bisher unentdeckter, scharfer Defekt im Leerzeichen-Generator (`scripts/fix_spaces.py`), der Paragrafenzeichen und Linkziele zerstören konnte.
3. Was eine menschliche Entscheidung braucht, ist unten einzeln benannt – mit Befehl, Zahl und Fundstelle, nicht als Sammelhinweis.
4. Zwei rote Prüfungen auf `main` stammen nicht aus den fünf Vorschlägen, treffen aber jeden künftigen Vorschlag; sie stehen im Abschnitt „Was auf `main` rot ist“.

## Stand nach der Bereinigung

Alle fünf Vorschläge sind am 14.11.2026 ohne Zusammenführen geschlossen, jeder mit einem Vermerk, der Grund und Fundstelle nennt. Ihre Zweige bleiben erhalten; ein Vorschlag lässt sich jederzeit wieder öffnen. Offen ist allein #1220 mit der Heilung aus diesem Zweig.

## Die fünf Vorschläge im Einzelnen

| Nr. | Thema | Stand gegenüber `main` | Urteil |
|---|---|---|---|
| #1217 | Zustandsdateien reparieren (Queue, Ledger, zwei Wachen) | Alle 12 Dateien sind auf `main` jünger (#1216, #1218). | **Überholt.** Ein Zusammenführen würde Messartefakte textlich mischen (D7) und die Wiederherstellung aus #1218 zurückdrehen. |
| #1171 | Backup: eine Ursache, ein Rat | 94 bis 100 % der Codezeilen stehen auf `main`; `WARTUNG-BACKUP-WF-3150-1030-HIGHEND-2026-11-12.md` §7 nennt den Vorschlag bereits als schließbar. | **Überholt.** |
| #1174 | Backup: vier Blindstellen der Anzeige | A (Einrichtungs-Assistent), B (`URTEIL_QUELLEN`) und C (Leerlauf-Prüfung) stehen auf `main`, C in anderer Bauform (`offene_einrichtung`, `einrichtung_geprueft`). D ist ein Hinweistext, der dem heutigen Verhalten widerspricht: Nach der Einrichtung stößt der nächste Tageslauf die Sicherung selbst an (Bericht vom 12.11., §4). | **Überholt.** Offen bleibt allein, was nur der Inhaber kann (siehe unten). |
| #1167 | KI-Kennzeichnung: unbelegte Ausnahmen schließen | `main` hat sich in #1201, #1207 und #1218 für das Gegenteil entschieden: Eine ungeklärte Herkunft wird nie zur KI-Behauptung umgeschrieben, sie bleibt rot, bis ein Mensch sie klärt (`RECHT-UPDATE-REPORT.md`, Zeile 121). Die beiden technischen Korrekturen des Vorschlags (`ungeklaert_erstmals`, `requirements-hugo.txt`) stehen auf `main`. | **Durch dokumentierte Entscheidung abgelöst.** Der Kern darf nicht portiert werden – er würde neun Artikel ohne Beleg als KI-erzeugt ausweisen. |
| #1173 | F4 #1072: Fachbefunde geschlossen, Heilungsbeleg | Dreiteilig, siehe nächster Abschnitt. | **Überholt bis auf acht Entscheidungen, die ein Mensch bestätigen muss.** |

### #1173 im Detail

**Teil 1 – Leerzeichen-Generator.** Der Vorschlag schützte Markdown-Ziele vor Regel D. `main` hat das in #1177 (`3a4c2a452`) breiter gelöst: Ziele, HTML-Attribute, URLs und Dateinamen werden tokenisiert, `abbildungen_ableiten.py` und `fix_url_hygiene.py` haben den Bestand geheilt (0 zerlegte Bildziele in `content`, gemessen mit `grep`). Die neue Wache `bildziel_wache.py` des Vorschlags hätte heute keinen Bestand mehr zu heilen. Beim Nachprüfen dieser Lösung fiel der Defekt auf, den dieser Zweig behebt (nächster Abschnitt).

**Teil 2 – 140 Redaktionsentscheidungen auf 31 Seiten.** Gemessen gegen die heutige Entscheidungskette (`data/faktenfrische_entscheidungen.yaml`, 325 Einträge) und den heutigen Text (`faktenfrische_befund_ledger.fassungen_aus_bestand()`):

| Anzahl | Lage auf `main` | Folge |
|---:|---|---|
| 38 | Der Befund ist auf `main` nicht mehr offen. | Erledigt, nichts zu übertragen. |
| 94 | Der Befund ist offen, aber der im Vorschlag geprüfte Text ist nicht der heutige. | Nicht übertragbar. `docs/FAKTENFRISCHE-MERGE-VORFALL-2026-11-13.md` legt fest: Entscheidungen zu einer anderen Fassung brauchen eine Prüfung des heutigen Textes und eine belegte Folgeentscheidung. |
| 8 | Der Befund ist offen **und** der geprüfte Text ist byteweise der heutige. | Übertragbar – aber nur durch den Menschen, der sie verantwortet (D13). Liste unten. |

Die acht übertragbaren Entscheidungen (Befund-ID, Seite, Art):

| Befund-ID | Seite | Art |
|---|---|---|
| `05be346e82c80b2a8664` | `2026-10-28-dsl-und-internet-flat-guenstig-sichern` | Lücke |
| `d0a5cf7bb64eb0cd46c8` | `2026-10-28-dsl-und-internet-flat-guenstig-sichern` | Lücke |
| `ec53e181336df8dc61ac` | `2026-10-28-dsl-und-internet-flat-guenstig-sichern` | Lücke |
| `f3f9184bfca9b097f68e` | `2026-10-28-dsl-und-internet-flat-guenstig-sichern` | Lücke |
| `fb4d2260f4fa291c35ae` | `2026-10-28-dsl-und-internet-flat-guenstig-sichern` | Präzision |
| `82cc87314e0d4fcb21e9` | `2026-09-23-5-einfache-frugalismus-tricks-fuer-den-alltag` | Lücke |
| `bd5ee70c85ec7db78f26` | `2026-09-23-5-einfache-frugalismus-tricks-fuer-den-alltag` | Lücke |
| `f83f21c1f2e2012f672e` | `2026-09-23-5-einfache-frugalismus-tricks-fuer-den-alltag` | Präzision |

Begründung und Beleg jeder Entscheidung stehen unverändert im Zweig des Vorschlags (`git show refs/pull/1173/head:data/faktenfrische_entscheidungen.yaml`). Eintragen kann sie nur der Erzeuger, nie ein Texteditor:

```
python3 scripts/faktenfrische_befund_ledger.py --entscheiden <Befund-ID> \
    --von "<Name>" --begruendung "<Text>" --beleg "<URL>" --apply
python3 scripts/faktenfrische_befund_akte.py --schreiben
```

Sie sind in diesem Zweig bewusst **nicht** eingetragen: Eine Unterschrift unter eine Fachentscheidung trägt niemand für einen anderen nach.

**Teil 3 – Belegregel (`--art`, `--stelle`, `--pruefe-stellen`).** `main` hat das Ledger in #1218 neu aufgebaut und bindet Entscheidungen an die Textfassung statt an eine Fundstelle. Beide Modelle nebeneinander wären zwei Wahrheiten über denselben Befund (D4). Die Regel wird deshalb nicht portiert.

## Was dieser Zweig behebt: Paragrafenzeichen und Linkziele im Leerzeichen-Generator

**Befund.** `scripts/fix_spaces.py` läuft in `content-engine-v2.yml` und `seo-weekly.yml` über jeden Artikel. Alle Masken des Moduls benutzten das Paragrafenzeichen als Platzhalter; Regel D stellte danach mit `.replace("§", ".")`, Regel E mit `.replace("§§", ",")` zurück – also jedes „§“ der Zeile. Sobald eine der beiden Regeln auf einer Zeile griff:

| Eingang | Ergebnis vor der Heilung |
|---|---|
| `Nach § 20 EStG gilt das.Mehr dazu unten` | `Nach . 20 EStG gilt das. Mehr dazu unten` |
| `Nach §§ 305 ff. BGB gilt,dass es zählt` | `Nach , 305 ff. BGB gilt, dass es zählt` |
| `Die Datei tabelle.csv liegt bereit.Öffne sie.` | `Die Datei .Z0. liegt bereit. Öffne sie.` |
| `Das kostet 3 Euro.Mehr steht im [Rechner](/werkzeuge/rechner/).` | `Das kostet 3 Euro. Mehr steht im [Rechner.Z0..` |
| `Die Seite www.example.de hilft.Schau rein` | `Die Seite .DOM0. hilft. Schau rein` |

Auf einer Finanz- und Rechtsseite ist ein verschwundenes „§“ eine verfälschte Rechtsquelle, und keine Wache sucht danach. Der Bestand war am 14.11.2026 noch sauber (27 Dateien tragen ein „§“, keine Zeile traf beide Auslöser zugleich); der Defekt war scharf, nicht eingetreten.

**Heilung.**

- Platzhalter liegen im privaten Unicode-Bereich (U+E000 bis U+E004). Sie können im Text nicht vorkommen, und jede Maske stellt nur ihr eigenes Zeichen zurück.
- Fail-closed in beide Richtungen: Eine Zeile, die schon ein Platzhalter-Zeichen trägt, wird nicht angefasst; bleibt nach der Rückstellung eines stehen, wird die Änderung verworfen und das Original bleibt.
- Nebenfund des Kreuztests: Regel C entfernte das Leerzeichen vor Bild-Markup (`Text ![Bild](a.svg)` → `Text![Bild](a.svg)`). `![` gilt jetzt nicht mehr als Satzzeichen.

**Nachweis.**

| Prüfung | Ergebnis |
|---|---|
| `python3 scripts/fix_spaces.py --selftest` | 96 Fälle grün (48 Paare, je Regel und Idempotenz; 17 Paare neu) |
| `python3 -m unittest scripts.tests.test_fix_spaces_platzhalter` | 13 Tests grün; gegen das alte Modul 58 Fehlschläge – der Test erkennt den Defekt |
| Bestandsvergleich alt gegen neu, 162 Inhaltsdateien | Ergebnis bytegleich – die Heilung ändert keine gesunde Zeile |
| `python3 -m unittest scripts.tests.test_1098_produktionswahrheit` | grün (Schutzzonen aus #1177 unverändert) |
| `npm run test:redos` | grün |

## Was auf `main` rot ist – unabhängig von den fünf Vorschlägen

Volle Suite auf `main` (`python3 -m unittest discover -s scripts/tests`): 6070 Tests, 2 Fehlschläge, 10 übersprungen. Beide Fehlschläge sind in #1218 als bewusst offen dokumentiert:

| Prüfung | Ursache | Wer kann es schließen |
|---|---|---|
| Integritäts-Siegel (`integrity_guard.py --gate`, Exit 3; `test_ausgelieferter_baum_passt_zum_siegel`) | `scripts/generate_covers.py` wurde in #1218 geändert, das Siegel nicht neu gezeichnet. | Inhaber: `python3 scripts/integrity_guard.py --set-current`, danach `data/integrity_lock.json` im selben Commit. Die Datei ist sicherheitsrelevant und wird ohne ausdrücklichen Auftrag nicht angefasst. |
| `test_vollrueckstand_nach_97_tagen_behaelt_reserve` | Der eingefrorene Stresstest (Stichtag 09.02.2027) trifft auf den Entwurf `2026-11-13-secondhand-kleidung-…`, dessen Frist zwei Tage nach dem Stichtag liegt. Der Lauf arbeitet Überfälliges zuerst ab; bei 130 überfälligen Seiten reißt diese eine neue Frist bei jedem Limit unter 131 (gemessen für 18, 19, 20, 21, 22, 24). | Fachentscheidung zur Reihenfolge (Überfälliges zuerst oder früheste Frist zuerst) – in #1218 als offene Frage benannt. |
| KI-Provenienz-Wache (Lauf auf `main`) | 12 ungeklärte Herkunftsfälle in `data/ki_kennzeichnung.yaml`, Frist 02.12.2026. Rot ist hier die gewollte Anzeige. | Inhaber: jede der zwölf Seiten als menschlich oder KI-gestützt einordnen. |

Solange das Siegel nicht neu gezeichnet ist, zeigt **jeder** Änderungsvorschlag eine rote Siegel-Prüfung – auch dieser. Nach D11 wird er deshalb nicht zusammengeführt, bevor die Prüfungen für genau diesen Commit grün sind.

## Was nur der Inhaber erledigen kann

| Vorgang | Offener Schritt |
|---|---|
| #923 / #1030 (Backup) | Zugänge `BACKUP_REPO`, `BACKUP_REPO_TOKEN`, `BACKUP_PASSPHRASE`, `CF_KV_BACKUP_TOKEN`, `KV_NAMESPACE_ID_ABO` und die Umgebung `backup` einrichten (`scripts/backup_einrichten_wizard.sh`). Der Vorgang bleibt offen, bis ein echter Sicherungslauf grün ist. |
| #1028 (KI-Kennzeichnung) | Zwölf Herkunftsfälle bis 02.12.2026 klären. |
| #1072 (Fachbefunde) | Acht Entscheidungen aus #1173 bestätigen und eintragen (Liste oben); 94 weitere Befunde am heutigen Text neu entscheiden. `BEFUND-AKTE.md` führt 155 offene Befunde auf 39 Seiten. |
| Integritäts-Siegel | Neu zeichnen (Befehl oben). |

## Warum die Vorschläge veralten konnten

Kein Skript und kein Workflow beobachtet offene Änderungsvorschläge (`grep` nach `pulls` und `pr list` in `scripts/` und `.github/workflows/`: Treffer nur für bereits zusammengeführte Vorschläge in `vorgangs_abschluss.py`). Ein Vorschlag, dessen Thema `main` auf anderem Weg löst, bleibt deshalb unbegrenzt offen und sammelt rote Prüfungen an. Eine Wache dafür bräuchte in `bot-watchdog.yml` das Leserecht auf Änderungsvorschläge – eine Änderung an einer sicherheitsrelevanten Datei, die einen ausdrücklichen Auftrag verlangt. Sie ist deshalb hier als Vorschlag benannt und nicht eingebaut.

## Geänderte Dateien

- `scripts/fix_spaces.py` – Platzhalter, fail-closed, Regel C, 17 neue Selbsttest-Paare
- `scripts/tests/test_fix_spaces_platzhalter.py` – neu
- `PR-BESTAND-HIGHEND-2026-11-14.md` – dieser Bericht

## Nachtrag vom 14.11.2026, abends: die offenen Punkte abgearbeitet

Auftrag des Inhabers nach dem ersten Bericht: die dort als offen genannten Punkte vollständig beheben. Dieser Abschnitt ergänzt den Bericht; die Abschnitte darüber bleiben, wie sie am Nachmittag standen.

### Stand je Punkt

| Punkt | Ergebnis |
|---|---|
| Integritäts-Siegel | **Erledigt, auf `main`.** Das Siegel wurde zweimal gleichlautend neu gezeichnet: in diesem Zweig und in #1221, der zuerst zusammengeführt wurde. Beide Fassungen decken dieselben 55 Dateien mit denselben Prüfsummen. Dieser Zweig übernimmt die Fassung von `main` und ändert das Siegel nicht mehr. |
| Stresstest der Faktenfrische | **Behoben.** Ursache und Entscheidung unten. |
| Acht Entscheidungen aus #1173 | **Vier eingetragen, vier bewusst offen.** Begründung unten. |
| Wache für liegende Vorschläge | **Gebaut und angeschlossen.** Beschreibung unten. |
| #1028, zwölf Herkunftsfälle | **Bleibt beim Inhaber.** Das Werkzeug liegt bereit, Schritte unten. |
| #923 / #1030, Backup | **Bleibt beim Inhaber.** Die Zugänge kann nur er anlegen. |

### Stresstest: der Test maß nicht mehr, was sein Name sagt

Der Test „Vollrückstand nach 97 Tagen“ führte seinen Tag als festes Datum, den 09.02.2027. Eine am 13.11.2026 geprüfte Seite hat ihre nächste Frist am 11.02.2027, also zwei Tage nach diesem Datum. Am 09.02.2027 war damit nicht mehr der ganze Bestand im Rückstand: Die eine Seite wurde mitten im Abbau neu fällig und riss ihre Frist bei jedem Limit unter 44 (Messung vom 14.11.2026 mit `faktenfrische_kapazitaet.py`). Der Test war rot, obwohl sich an der Kapazität nichts geändert hatte.

Behoben ist die Ursache, nicht die Schwelle:

- Der Tag des Vollrückstands wird aus dem Bestand gerechnet: späteste Frist plus Nachholfrist (`faktenfrische_kapazitaet.vollrueckstand_stichtag`). Er wandert mit jeder Prüfung mit.
- Nachmessung am 14.11.2026 mit 132 Artikeln, davon 131 mit Frist: Tag 18.02.2027, nötiges Budget 17 je Lauf, Abbau in 7 Tagen, keine gerissene Folgefrist (`scripts/tests/test_faktenfrische_kapazitaet.py`).
- **Entscheidung, die der Inhaber zurücknehmen kann:** `hartes_limit_pro_lauf` steigt von 18 auf 19. Das folgt der Regel vom 10.11.2026 (gemessener Bedarf plus zwei Plätze Reserve); bei Limit 18 wäre nur ein Platz geblieben. Das Limit greift nur bei echtem Rückstand, der Normalbetrieb bleibt bei Sockel 5. Arbeitsreihenfolge, Prüfintervalle, Nachholfrist und Mindestdeckung sind unverändert.
- Der Test meldet künftig, wenn die Reserve aufgebraucht ist. Nach heutiger Messung ist das ab 144 Seiten mit Frist der Fall (`test_vollrueckstand_tag_folgt_dem_bestand`).

Der Vorfallbericht `docs/FAKTENFRISCHE-MERGE-VORFALL-2026-11-13.md` nannte die Änderung des Limits eine Betreiberentscheidung. Sie ist hier auf den Auftrag vom 14.11.2026 hin getroffen. Wer bei Limit 18 bleiben will, setzt die eine Zeile in `data/agent_reach/faktenfrische.yaml` zurück; der Test verlangt dann nur noch einen Reserveplatz weniger, als die Regel vorsieht, und schlägt deshalb an.

`RELEASE-SCORECARD.md` und `data/release_scorecard_state.json` nennen noch Limit 18. Beide schreibt die Scorecard beim nächsten Lauf selbst neu (D7); von Hand sind sie nicht angefasst.

### #1173: vier Entscheidungen eingetragen, vier nicht

Eingetragen am heutigen Text des DSL-Artikels (`2026-10-28-dsl-und-internet-flat-guenstig-sichern`), als Folgeentscheidung mit Verweis auf die frühere Fassung, unter „Arena-Redaktion (Auftrag: Frank Hartung), 14.11.2026“:

| Befund | Was heute im Text steht |
|---|---|
| `05be346e82c80b2a8664` Bonusspanne 50 bis 100 € | Keine Spanne mehr; der Text sagt, dass es keine gesetzliche Spanne und keine belastbare Statistik gibt. |
| `d0a5cf7bb64eb0cd46c8` Rechtsrahmen fehlt | § 56 TKG ist genannt und verlinkt. |
| `ec53e181336df8dc61ac` 24 Monate, ein Monat Frist ohne Quelle | Als gesetzlicher Rahmen nach § 56 TKG formuliert. Mit dem Normtext verglichen (Absätze 1, 3 und 4, gesetze-im-internet.de, Abruf 14.11.2026): Der Artikel gibt ihn zutreffend wieder. |
| `f3f9184bfca9b097f68e` 50-30-20 als allgemeine Regel | Ausdrücklich „ein Haushaltsmodell, keine Vorgabe aus Recht oder Statistik“. |

Diese vier Einträge hat die Arena-Sitzung geprüft, nicht der Inhaber persönlich. Das steht so im Feld `entschieden_von`. Die Akte ist ein Anfügeprotokoll: Eine abweichende Entscheidung des Inhabers kommt als weiterer Eintrag dazu. `BEFUND-AKTE.md` führt danach 151 offene Befunde auf 39 Seiten, vorher 155.

Nicht eingetragen:

- **`fb4d2260f4fa291c35ae` (Bandbreite für zwei HD-Streams).** Der Befund bemängelte eine Zahl ohne Beleg. Der Text nennt heute andere Zahlen (8 bis 12 Mbit/s je Stream), nennt sie eine Faustregel und belegt sie weiterhin nicht. Das ist eine Abschwächung, keine Heilung. Ob die Kennzeichnung als Faustregel genügt oder eine Quelle hinein muss, ist eine Fachentscheidung.
- **Die drei Befunde zum Frugalismus-Entwurf** (`82cc87314e0d4fcb21e9`, `bd5ee70c85ec7db78f26`, `f83f21c1f2e2012f672e`). Der Text, an den sie gebunden würden, enthält einen Sachfehler (nächster Abschnitt). Eine Entscheidung an einem Text, der korrigiert werden muss, verfiele mit der Korrektur wieder.

### Neuer Befund: falscher Energiewert in acht Artikeln

Beim Gegenlesen der Belege fiel auf: Acht Artikel schreiben, Energie sei **im Oktober 2026** um 14,9 % teurer gewesen als im Vorjahr. Das ist der Wert für **September 2026**. Für Oktober meldet das Statistische Bundesamt 12,2 %, vorläufig in der Pressemitteilung Nr. 382 vom 30.10.2026 und endgültig in Nr. 392 vom 11.11.2026 (beide am 14.11.2026 im Wortlaut abgerufen). Die anderen genannten Oktoberwerte stimmen: Inflationsrate 2,8 %, Nahrungsmittel 0,4 % (Nr. 392).

| Artikel | Zeilen | Stand |
|---|---|---|
| `2026-08-24-mehr-freiheit-durch-verzicht-clevere-frugalismus-tipps` | 241 | live |
| `2026-09-04-finanzielle-freiheit-erreichen-denke-dich-reich` | 161 | live |
| `2026-09-07-frugalismus-tipps-mehr-freiheit-durch-bewussten-konsum` | 158, 160 | live |
| `2026-09-07-frugalismus-tipps-so-vermeidest-du-teure-alltagsfehler` | 83, 151, 167 | live |
| `2026-09-11-5-einfache-frugalismus-tricks-fuer-den-alltag` | 87, 136, 196 | live |
| `2026-09-11-50-30-20-regel-beherrsche-dein-budget-im-jahr-2026` | 158, 189 | live |
| `2026-10-02-weihnachten-budget-planen-ohne-schulden-durch-die-feiertage` | 112 | live |
| `2026-09-23-5-einfache-frugalismus-tricks-fuer-den-alltag` | 66, 130 | Entwurf |

Der Artikel `2026-10-15-saison-update-was-sich-jetzt-fuer-dich-aendert` nennt denselben Wert richtig für September und ist nicht betroffen.

Zwei Stellen begründen mit dem Energiewert zusätzlich, warum sich ein Stromtarifwechsel lohne (`2026-09-23-…` Zeile 130, `2026-09-11-5-einfache-…` Zeile 136). Der Energiewert enthält Kraftstoffe, die im Oktober 2026 um 28,9 % über dem Vorjahr lagen; Strom allein war um 5,2 % günstiger als im Vorjahr (Tabelle in Nr. 392). Die Begründung trägt deshalb auch mit der richtigen Zahl nicht.

Dieser Zweig ändert die Artikel **nicht**. Es sind sieben veröffentlichte Seiten mit zusammen 51 an den Text gebundenen Entscheidungen, die mit jeder Textänderung neu zu treffen sind, und eine Korrektur an Finanztexten braucht die Fachfreigabe des Inhabers (D13). Vorschlag: ein eigener Vorgang, der den Wert auf 12,2 % mit Verweis auf Nr. 392 stellt, die beiden Strom-Begründungen neu fasst und die Entscheidungen am neuen Text nachzieht.

### Wache für liegende Vorschläge

`scripts/pr_bestand_wache.py` meldet jeden offenen Änderungsvorschlag, der seit 3 Tagen ohne Bewegung ist; Entwürfe und maschinell erzeugte zählen mit. Die Frist von 3 Tagen entspricht dem Stand vom 14.11.2026, an dem vier Vorschläge so lange lagen und keiner mehr zusammenführbar war.

- Die Wache liest nur Nummern und Zeitpunkte, keine Titel. Sie schließt, kommentiert und führt nichts zusammen.
- Der Bot-Watchdog führt sie im täglichen Voll-Lauf als Check 11. Liegt ein Vorschlag, entsteht ein Befund mit menschlichem Besitzer im Kanal `human-action`. Im stündlichen Ausfall-Takt wird sie übersprungen.
- Kann die Wache GitHub nicht lesen, meldet sie „nicht messbar“ (Exit 2, im Watchdog `UNKNOWN`). Das gilt auch, wenn die Leseseite von 200 Vorschlägen voll ist. Grün meldet sie nur nach einer vollständigen Messung.
- `.github/workflows/bot-watchdog.yml` bekommt dafür das Leserecht `pull-requests: read` und den Selbsttest der Wache. Die Workflow-Datei ist mit dem ausdrücklichen Auftrag vom 14.11.2026 geändert.

Grenze: Das Fach-Ticket schließt nicht von selbst. Der Befund fällt aus Messung und Bericht, sobald kein Vorschlag mehr liegt; das Ticket schließt der Mensch, der entschieden hat. So hält es der Alarm-Router bei jedem Befund mit menschlichem Besitzer.

### Rot aus `main`: drei Ursachen, zwei davon hier geheilt

Die Prüfung `regression` war am 14.11.2026 bei jedem Änderungsvorschlag rot, auch auf Ständen, die diesen Zweig nicht enthalten (Läufe 43626365365, 43628208008, 43629528335 und 43633806749; die roten Tests stehen als Anmerkungen am jeweiligen Lauf). Nach D11 darf so nichts zusammengeführt werden. Der Inhaber hat am 14.11.2026 beauftragt, die Ursachen in diesem Zweig zu beheben.

| Ursache | Stand |
|---|---|
| `scripts/pinterest_duplicate_guard.py` las die Artikel in der Reihenfolge des Dateisystems. Bei zwei Seiten mit gleichem Pin-Text behielt die zuerst gelesene den Text. War die zweite ein bytegebundener Reserve-Entwurf, wurde nur sie übersprungen und die Dublette blieb stehen. Lokal kam die Reihenfolge passend, in CI nicht: `test_normaler_entwurf_wird_weiterhin_eindeutig` war dort rot, lokal grün. | **Hier geheilt.** Die Artikel werden sortiert gelesen, und ein bytegebundener Entwurf behält seinen Text immer; die übrigen Seiten der Gruppe bekommen einen neuen. Drei neue Tests drehen die Reihenfolge des Dateisystems in beide Richtungen; mit dem alten Stand schlagen alle drei fehl (Gegenprobe am 14.11.2026). Der heutige Bestand hat keine Dublette, die Änderung schreibt also nichts um (`python3 scripts/pinterest_duplicate_guard.py`). |
| Das mit #1222 eingeführte Quellen-Gate ließ `test_publish_gate_heilt_r5_vor_der_harten_pruefung` scheitern. Der Test legt alle Gates still außer der R5-Heilung; das neue Gate fehlte in dieser Liste. | **Hier geheilt**, nur im Test (`scripts/tests/test_publication_reliability.py`). Am Gate ist nichts geändert; es hat seinen eigenen Test (`test_publish_gate_quellen.py`). |
| `.github/workflows/skript-syntax.yml` installierte PyYAML ohne feste Version (#1222); die Abhängigkeits-Wache lehnt das ab (Regel A7, zwei Tests). | **Auf `main` geheilt**, während dieser Zweig dieselbe Zeile korrigierte (`pyyaml==6.0.3`). Übernommen ist die Fassung von `main`; dieser Zweig ändert die Datei nicht. |

### Was beim Inhaber bleibt

**#1028, Frist 02.12.2026.** Zwölf Einträge unter `menschlich:` in `data/ki_kennzeichnung.yaml` tragen `ai_generated: false`, ohne dass das Repository die Herkunft belegt. Das Register verbietet jedem Skript, die Herkunft zu setzen, und `docs/KI-TRANSPARENZ-ABNAHME.md` §3 nennt die Freigabe ausdrücklich Sache des Betreibers. Ein Agent kann nicht wissen, wer die Texte geschrieben oder geprüft hat.

```
python3 scripts/freigabe_liste.py --liste            # die zwölf Einträge ansehen
python3 scripts/freigabe_liste.py --abhaken <slug>   # je Eintrag, nach eigener Prüfung
python3 scripts/freigabe_liste.py --freigabe         # Erklärung erzeugen, sobald alle zwölf abgehakt sind
```

Die Erklärung gehört in `docs/FREIGABE-VORLAGE-KI-VO-KENNZEICHNUNG-BESTAND.md`. War ein Text KI-gestützt, wird er nicht abgehakt, sondern im Register von `menschlich` nach `maschinell` umgetragen.

**#923 / #1030.** `bash scripts/backup_einrichten_wizard.sh` führt durch die fünf Zugänge und die Umgebung `backup`. Der Vorgang schließt, sobald ein echter Sicherungslauf grün ist.

**Fachbefunde (#1072).** 151 offene Befunde auf 39 Seiten (`BEFUND-AKTE.md`, Stand 14.11.2026), darunter die vier oben und die 94 aus #1173, die am heutigen Text neu zu entscheiden sind.

### Belege

| Prüfung | Ergebnis |
|---|---|
| Gesamte Testsuite vor der Übernahme von #1222 (`python3 -m unittest discover -s scripts/tests`) | 6102 Tests, 0 Fehlschläge; der eine Fehler des ersten Laufs war das fehlende Bauprodukt und ist nach `hugo` grün (`test_ki_provenienz_gate`, 32 Tests) |
| Gesamte Testsuite nach der Übernahme von #1222 | 6137 Tests, 3 Fehlschläge, alle drei aus `main` (Abschnitt „Rot aus `main`“); nach der Heilung laufen die betroffenen Module grün (`test_publication_reliability`, `test_abhaengigkeits_wache`, `test_publish_gate_quellen`, `test_workflow_aufruf_vertrag`: 160 Tests mit drei Workflow-Tests) |
| `scripts.tests.test_reserve_schreibschutz` | 17 Tests grün, auch unter einer um 97 Tage vorgestellten Uhr (`selftest_clock.py --trap-modul`) |
| Uhr-Probe für die geänderten Module (`selftest_clock.py --offset 97`) | grün: `test_faktenfrische_kapazitaet`, `test_pr_bestand_wache`, `test_bot_watchdog_meldetakt` |
| `python3 scripts/selftest_ki.py --trap-workflows` | 171 Selbsttests ohne Modell und ohne Netz grün |
| `npm run test:faktenfrische` | 183 Tests grün |
| `python3 scripts/governance_contract.py` | 47 Regeln erfüllt |
| `python3 scripts/pr_bestand_wache.py --selftest` | 21 Fälle grün |
| `scripts.tests.test_pr_bestand_wache` | 20 Tests grün |
| `scripts.tests.test_bot_watchdog_meldetakt` | 47 Tests grün |
| `python3 scripts/integrity_guard.py --gate` | grün, 55 Dateien |
| `python3 scripts/faktenfrische_befund_ledger.py --struktur-pruefen` | 329 Einträge, sauber |
| `hugo --destination public`, `npm run seo:check` | Bau grün; 142 Seiten, kein P1, kein P2 |
| `python3 scripts/skript_syntax_wache.py`, `python3 scripts/skills_vertrag.py` | grün (714 Dateien; 90 Skills, 0 Befunde) |

### Geänderte Dateien in diesem Nachtrag

- `scripts/faktenfrische_kapazitaet.py`, `scripts/tests/test_faktenfrische_kapazitaet.py`, `data/agent_reach/faktenfrische.yaml`, `docs/ANLEITUNG-FAKTENFRISCHE.md` – Stresstest
- `scripts/pr_bestand_wache.py`, `scripts/tests/test_pr_bestand_wache.py` – neu
- `scripts/bot_watchdog.py`, `scripts/tests/test_bot_watchdog_meldetakt.py`, `.github/workflows/bot-watchdog.yml` – Check 11
- `scripts/pinterest_duplicate_guard.py`, `scripts/tests/test_reserve_schreibschutz.py`, `scripts/tests/test_publication_reliability.py` – Rot aus `main` geheilt
- `data/faktenfrische_entscheidungen.yaml` – vier Einträge angefügt; `BEFUND-AKTE.md`, `data/faktenfrische_befunde_state.json` – vom Werkzeug neu geschrieben
