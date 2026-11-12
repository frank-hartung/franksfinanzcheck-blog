# Faktenfrische #1072 – zweite Runde, 12.11.2026

Dieses Dokument ist die redaktionelle Akte zur zweiten Entscheidungsrunde des
Registers `data/faktenfrische_befunde_1072.yaml`. Es ersetzt keine Fachprüfung
und kein Prüfsiegel. Es hält fest, was am 12.11.2026 am Text entschieden
wurde, worauf die Entscheidung steht und was bewusst offen bleibt.

## 1. Anlass

Der Rückfallschutz des Registers war rot, der Pages-Deploy blockiert. Zwei
Ursachen, beide nachvollziehbar:

1. **Anker-Drift.** Die Artikel vom 30.09. bis 05.11. wurden am 11.11.2026
   redaktionell überarbeitet. Dabei verschwanden neun Sätze, die im Register
   als Bedeutungsanker standen (u. a. „kann die Lager beschädigen“, „Eine
   längere Garantie ist nicht automatisch sicherer“). Die Entscheidungen
   waren damit an eine Fassung gebunden, die es nicht mehr gab.
2. **Falsch zugeordnete Belege.** Fünf Waschmaschinen-Befunde trugen die
   Startseite der Bundesnetzagentur als Beleg – eine Allowlist-Domain, aber
   ohne Bezug zum Befund und ohne Eintrag im Quellenverzeichnis des Artikels.

Dazu kamen zwei Befunde, die kein Test bisher sehen konnte, weil die Prüfung
nur den Body las: ein Fixkosten-Versprechen in `description` und
`pin_description` und eine Kurzantwort mit ungedeckten Zahlen in leeren
Zitatklammern.

## 2. Was entschieden wurde

| Paket | Inhalt | Umfang |
|---|---|---|
| A | Anker an den Text vom 12.11. gebunden, Belege korrigiert | 9 Befunde |
| B | Möglichkeitsform in `description`, `pin_description`, Body zurückgeholt; Verbots-Prüfung auf Meta-Flächen ausgedehnt | 1 Befund + Testvertrag |
| C | unquellbare Verschleiß-Folge gestrichen statt belegt | 1 Befund |
| D | #996-Anker-Nachzug (entblockt den Gas-Rückfallschutz) | 1 Register, 1 Befund |

Die Runde umfasst **14 Befunde in drei Artikeln**:

- `2026-11-02-last-minute-urlaubsangebote-sichern` (5)
- `2026-11-04-guenstigen-mietwagen-fuer-den-urlaub-buchen` (4)
- `2026-11-05-waschmaschine-beladen-weniger-kosten-bei-jedem-waschgang` (5)

Alle 14 tragen `entschieden_am: 2026-11-12` und sind über
`geprueft_fassung` (Projektion `betrieb-v3`) an den heutigen Text gebunden.
Der Ledger hält die Vorgängerfassung in `vorgaenger_geprueft_fassung`; das
Register hält die ersetzte Begründung in `entscheidung_vorgaenger`. Nichts
wird überschrieben.

## 3. Paket C – die Entscheidung und ihre Begründung

**Der Satz:** „Überladung führt zu schnellerem Verschleiß und teuren
Reparaturen“ (Befund `4284fd2d9c9005e7af8f`).

**Die Lage:** Die Aussage stützte sich allein auf FORUM WASCHEN – im Artikel
als Q4 geführt (`ikw.org`), also auf einer Domain, die **nicht** in der
Allowlist (`data/agent_reach/faktenfrische.yaml`, 16 Domains) steht. Die
Kausalaussage (Verschleiß, Reparaturkosten) war im Quellentext nicht belegt;
eine Messgröße nannte niemand. Eine allowlist-konforme Quelle für genau
diese Folge gibt es im Bestand nicht, und eine neue konnte am 12.11.2026
nicht geprüft werden (kein Netzzugang im Lauf).

**Die Entscheidung: Streichung, nicht Beleg.** Die Hausregel aus #911/#996
ist eindeutig: `beleg_url` ist entweder eine Allowlist-Url, die wörtlich im
Quellenverzeichnis steht – oder `null`, und dann lautet der Belegtyp
`streichung`. Eine Quelle zu erfinden, um den Befund zu schließen, wäre der
Fehler, den das Register verhindern soll.

**Was bleibt (und warum es bleiben darf):**

- „FORUM WASCHEN empfiehlt, die Nennbeladung des Geräts nicht zu
  überschreiten.“ – eine zugeordnete Empfehlung, keine Kausalfolge.
- „Die Nennbeladung deines Geräts steht auf dem Typenschild und in der
  Gebrauchsanleitung – sie gilt je Programm.“ – Geräteeigenschaft, keine
  externe Behauptung.
- „Wer diese Grenzen dauerhaft überschreitet, riskiert, dass die Wäsche
  nicht sauber wird und du den Waschgang wiederholen musst.“ – die
  Kostenfolge leitet der Artikel selbst her (Reibung, Reinigungswirkung,
  Wiederholung); dafür braucht es keine Fremdquelle.

**Was gestrichen wurde:** die Verschleiß- und Reparaturfolge an allen drei
Stellen (Kurzüberblick, Fehlerabschnitt, Schlussabsatz) und die Leserfrage
„Wie wirkt sich die Beladung auf den Verschleiß aus?“, die danach keine
Antwort mehr gehabt hätte.

## 4. Paket B – der Rückfall lag in den Meta-Flächen

Der Body war längst gedämpft („ein kleiner Baustein in deinem persönlichen
Fixkosten-Cockpit“), während

- `description`: „Richtiges Waschmaschine beladen **senkt** deine Fixkosten“,
- `pin_description`: derselbe Satz mit Werbekennzeichnung,
- Body, Abschnitt Vorwäsche: „senkt die Betriebskosten … nachhaltig“

weiter behaupteten. Der Verbots-Eintrag des Befunds („das richtige beladen
allein die fixkosten senkt“) griff nicht, weil das Wort „allein“ fehlte – und
`description` ohnehin nie geprüft wurde. Drei Konsequenzen:

1. Alle drei Stellen stehen wieder in der Möglichkeitsform.
2. Der Regressionstest prüft die Verbote jetzt zusätzlich auf `title`,
   `description`, `kurzantwort`, `pin_title` und `pin_description`
   (`test_verbote_gelten_auch_auf_den_meta_flaechen`) und sperrt den
   konkreten Satz musterunabhängig
   (`test_fixkosten_versprechen_bleibt_moeglichkeitsform`).
3. `test_beschreibungsaenderung_oeffnet_die_entscheidung` belegt systemisch,
   dass eine Meta-Änderung den Fassungshash öffnet – sonst wäre die
   fassungsgebundene Entscheidung blind.

Dieselbe Klasse traf zwei Nachbarartikel: Die Kurzantworten enthielten
„sparst du durchschnittlich 27 % … – Statista (2023)“ und „sparst laut
ADAC-Umfrage durchschnittlich 15 % … ()“ samt leerer Zitatklammern. Beide
Zahlen sind ohne Beleg im Text; sie sind ersetzt worden, nicht umformuliert.
Beide Artikel haben jetzt ein Quellenverzeichnis mit der Beleg-Url, die das
Register nennt – vorher stand der Beleg nur im Register.

## 5. Paket D – #996

Der Anker „Eine längere Garantie ist nicht automatisch sicherer“ war im
Rahmen der Überarbeitung ersetzt worden durch „Eine Garantie kauft dir
Planung – keine sichere Ersparnis“. Die Aussage ist unverändert, nur die
Formulierung. Der Anker ist nachgezogen (`996-N16`), das Register nennt den
Vorgang im Kopf, die Entscheidung selbst bleibt. Damit läuft der
Deploy-Schritt „Faktenfrische Gas – Rückfallschutz“ wieder grün.

## 6. Neuer Registervertrag

Bisher prüfte der Test „jeder Befund ist am heutigen Text entschieden“ über
ein Datumsfeld – eine Prüfung, die nach jeder Textänderung entweder rot
wird oder aufgeweicht werden muss. Der Vertrag ist jetzt viergeteilt:

1. **Anker sind die Invariante.** Fehlt ein Anker, ist die Fehlermeldung
   eine Arbeitsanweisung: Text nach der Entscheidung geändert → Befund neu
   entscheiden, Anker an die heutige Fassung binden.
2. **Runden sind dokumentiert.** `stand`, `lauf` und `runden` halten die
   Runden vom 05.11., 07.11., 11.11. und 12.11. fest; jeder Befund gehört
   zu genau einer dokumentierten Runde.
3. **Die jüngste Runde ist am heutigen Text gefasst.** Für jeden am
   Registerstand entschiedenen Befund muss `geprueft_fassung` exakt dem
   aktuellen Aussage-Hash entsprechen. Ältere Runden bleiben Historie und
   werden nicht rückwirkend umgeschrieben.
4. **Der Register-Hash stammt aus der Ledger-Kette.** Er muss in
   `geprueft_fassung`, `ursprungs_geprueft_fassung`,
   `vorgaenger_geprueft_fassung` oder `befund_fassung` eines Eintrags zu
   diesem Befund vorkommen – erfundene Hashes sind damit ausgeschlossen.

Zusätzlich ist die Quellenprüfung ausnahmslos: Der frühere Freibrief „wenn
der Artikel ein Quellenverzeichnis hat“ ist entfernt. Neu gilt: Beleg-Url
steht im Quellenverzeichnis – oder der Befund ist eine Streichung.

## 7. Beweise (gemessen am 12.11.2026)

| Prüfung | Ergebnis |
|---|---|
| `python3 -m unittest scripts.tests.test_faktenfrische_1072` | 12 Tests grün (vorher 14 Fehler) |
| `python3 -m unittest scripts.tests.test_faktenfrische_996` | 17 Tests grün |
| `deploy.yml` – „Faktenfrische Gas – Rückfallschutz #996“ | grün |
| `faktenfrische_befund_ledger.py --selftest` | grün |
| `faktenfrische_befund_ledger.py struktur_pruefen` | 291 Einträge, 0 Strukturfehler |
| `faktenfrische_befund_akte.py --schreiben` | 139 offene Befunde, 35 Seiten |
| Gesamt-Suite (`unittest discover -s scripts/tests`) | gleiche 14 rote Tests wie auf `main` (alle vorbestehend, keine neuen) |

## 8. Was bewusst nicht gemacht wurde

- **Keine Massen-Neuentscheidung.** Die übrigen 33 Registerbefunde bleiben
  an ihre dokumentierte Fassung gebunden. Sie sind nicht stillgelegt: Anker
  und Verbote werden bei jedem Lauf geprüft. Ein Befund, dessen Anker
  verschwindet, wird rot – wie diese Runde.
- **Kein Aufweichen der Datumsprüfung.** Statt „Stand 05.11.“ zu streichen,
  gibt es einen strengeren Vertrag (Abschnitt 6).
- **Keine erfundene Quelle für Paket C.** Siehe Abschnitt 3.
- **Keine Registrierung des Publish-Gates ohne Not.** Der Selbsttest des
  Registers läuft jetzt zusätzlich als eigener Deploy-Schritt; die
  Gesamt-Suite bleibt der zweite, breitere Riegel.

## 9. Offene Punkte (bewusst)

- Die 33 Befunde mit älterer Fassungsbindung werden erst bei der nächsten
  Textänderung neu entschieden. Das ist gewollt: Entschieden wird am Text,
  nicht am Kalender.
- `data/faktenfrische_queue.json` führt die Befunde weiter als offen. Die
  Queue ist Maschinenausgabe des Collectors; sie wird nicht von Hand
  nachgezogen.
- Die drei berührten Artikel sind weiter `draft: true` bzw. als
  Reserve-Veröffentlichung geführt. Diese Runde ändert daran nichts.
