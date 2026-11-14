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
