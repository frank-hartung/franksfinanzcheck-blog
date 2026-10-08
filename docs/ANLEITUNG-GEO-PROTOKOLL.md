# Anleitung: GEO-Protokoll (KI-Sichtbarkeit, manuell)

Stand: 08.10.2026 · Skript: `scripts/geo_protokoll.py` · Tests: `scripts/tests/test_geo_protokoll.py`
Daten: `data/geo/protokoll-JJJJ-MM.csv` (versioniert, ohne personenbezogene Angaben)

## Wozu

Die Frage: Taucht franksfinanzcheck.de in KI-Antworten auf, und wird die Seite als Quelle
angezeigt? Das Protokoll misst das einmal im Monat mit denselben zehn Fragen und
denselben drei Oberflächen. So sieht man, ob sich etwas bewegt.

Das Protokoll ist eine **Stichprobe**, kein Ranking. Antworten schwanken von Abfrage
zu Abfrage. Gewertet wird die Entwicklung über Monate, nicht ein einzelner Wert.

## Bewusst manuell

- Ein Mensch fragt die Oberflächen ab und trägt die Antworten ein.
- Das Skript fragt keine Chat-Oberfläche und keinen Dienst per API ab.
  Das wäre gegen die Nutzungsbedingungen mancher Dienste und unzuverlässig.
- **Perplexity ist nicht dabei.** Das ist eine bewusste Entscheidung (CLAUDE.md,
  Abschnitt Werkbank). Die eigene Antwortmaschine ersetzt diese Rolle.
- Die Tabelle wird nicht mit KI-Hilfe befüllt. Sonst misst das Protokoll nur das Modell.

## Die zehn Fragen (fest)

Die Fragen stehen im Skript (`FRAGEN`) und in jeder Datei. Sie werden nicht
geändert, sonst sind Monate nicht mehr vergleichbar. Eine neue Frage ist eine
neue Reihe (Entscheidung mit Datum in der Doku dokumentieren).

| ID | Frage | Säule |
|---|---|---|
| F01 | Welches Girokonto ist ohne Grundgebühr sinnvoll? | Konto & Karten |
| F02 | Wie finde ich eine gute Kreditkarte ohne Jahresgebühr? | Konto & Karten |
| F03 | Wie rechne ich den Effektivpreis eines DSL-Wechselbonus richtig aus? | Internet & DSL |
| F04 | Wie spare ich beim Internetvertrag, ohne den Tarif zu verschlechtern? | Internet & DSL |
| F05 | Wie erkenne ich einen guten Stromtarif ohne Lockangebote? | Strom sparen |
| F06 | Was bringt ein Anbieterwechsel beim Strom in der Praxis? | Strom sparen |
| F07 | Wie erstelle ich ein Haushaltsbudget, das ich auch durchhalte? | Frugalismus |
| F08 | Brauche ich eine Haftpflichtversicherung, und worauf achte ich beim Tarif? | Versicherungen |
| F09 | Wie spare ich beim Mietwagen, ohne Versicherungsfallen zu übersehen? | Mietwagen |
| F10 | Lohnt sich ein Tagesgeldkonto, und wie prüfe ich den Zins richtig? | Konto & Karten |

## Die drei Oberflächen

| Engine | Was gemeint ist |
|---|---|
| `chatgpt-free` | ChatGPT im kostenlosen Zugang (ohne Abo). Anmeldung im Feld `notiz` vermerken. |
| `gemini-free` | Gemini im kostenlosen Zugang (ohne Abo). Anmeldung im Feld `notiz` vermerken. |
| `google-ki-uebersicht` | Die KI-Übersicht in der Google-Suche (Deutschland). |

Bitte je Abfrage: gleicher Tag für alle drei, möglichst ohne persönlichen Verlauf
(privates Fenster), Ort Deutschland, Frage wörtlich aus der Liste.

## Eintrag je Zeile

| Feld | Regel |
|---|---|
| `datum` | Tag der Abfrage, `JJJJ-MM-TT`, im Monat der Datei |
| `genannt` | `ja`, wenn Marke oder Domain im Antworttext steht (auch in einer Liste). Sonst `nein`. |
| `position` | Nur bei `genannt=ja`: Rang der Nennung unter den genannten Quellen oder Anbietern (1 = zuerst). |
| `zitiert` | `ja`, wenn die Domain als Quelle, Link oder Zitat angezeigt wird. Sonst `nein`. |
| `quelle_url` | Nur bei `zitiert=ja`: die angezeigte URL, `https://` und auf franksfinanzcheck.de. |
| `notiz` | Frei, höchstens 200 Zeichen, keine E-Mail-Adressen, keine Kontodaten |

`genannt=nein` heißt immer auch `zitiert=nein`. Lücken fallen so auf.
Enthält ein Feld ein Komma, das Feld in Anführungszeichen setzen.

Screenshots bitte außerhalb des Repos ablegen. Sie können Kontoinformationen zeigen.

## Ablauf je Monat

```bash
python3 scripts/geo_protokoll.py --neu 2026-11     # Datei anlegen (nie überschreiben)
# … Zeilen von Hand ausfüllen …
python3 scripts/geo_protokoll.py --pruefen          # Fehler und offene Zeilen
python3 scripts/geo_protokoll.py --auswerten        # Quoten je Engine (Markdown)
```

- `--pruefen` ohne Fehler, aber mit offenen Zeilen ist in Ordnung. Auswertung
  zählt nur erfasste Zeilen. Die Zahl „erfasst“ in der Tabelle sagt, wie vollständig die Stichprobe ist.
- `--auswerten` läuft nur auf geprüften Dateien. Bei Fehlern wird die Auswertung verweigert.

## Auswertung lesen

Die Tabelle nennt je Engine:

- **erfasst**: wie viele der zehn Fragen beantwortet sind (von 10),
- **genannt**: Anteil der Antworten mit Nennung der Domain,
- **zitiert**: Anteil der Antworten, in denen die Domain als Quelle angezeigt wird,
- **Ø Position**: Rang der Nennung, wenn genannt.

Eine Zahl von einem Monat ist keine Aussage. Erst der Verlauf über drei bis sechs
Monate zeigt eine Richtung. Ein Ausschlag nach oben nach einer Änderung an einem
Artikel ist ein Hinweis, kein Beleg.

## Grenzen

- Die Antworten sind Momentaufnahmen. Personalisierung, Standort und Modellwechsel
  verändern sie.
- Die Stichprobe ist klein (zehn Fragen je Monat). Abweichungen von wenigen Prozentpunkten sind Rauschen.
- Die Liste der Fragen deckt die Säulen des Blogs ab, aber nicht alle Themen.
- Kein Werbeversprechen: die Zahl misst Sichtbarkeit, nicht Umsatz.
