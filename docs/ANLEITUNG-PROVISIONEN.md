# Anleitung: Provisions-Tabelle (Monatssummen je Partner)

Stand: 08.10.2026 · Skript: `scripts/provisionen_check.py` · Tests: `scripts/tests/test_provisionen_check.py`

## Wozu

Die Tabelle hält, was die Partner (CHECK24, Tarifcheck, C24 Bank) pro Monat
abrechnen: Abschlüsse, Stornos und Provision. Sie ist die Grundlage, um Klicks aus
dem Blog mit echtem Umsatz zu vergleichen. Der Umsatztrichter in
`scripts/revenue_funnel.py` braucht Awin-Transaktionen; Awin ist laut Stand 08.10.2026
aus. Dort bleibt der Provisionsschritt deshalb „unbekannt“. Die Tabelle schließt diese
Lücke von Hand, ohne Kundendaten zu speichern.

Die Tabelle ist **intern**. Sie wird nicht veröffentlicht und nicht in den Blog
übernommen. Sie ersetzt keine Buchhaltung und keine Steuerberatung.

## Wo die Daten liegen

| Datei | Inhalt | Git |
|---|---|---|
| `data/provisionen/provisionen-vorlage.csv` | nur die Kopfzeile | versioniert |
| `data/provisionen/provisionen.csv` | die echten Monatssummen | **ausgeschlossen** (`.gitignore`) |

Das Repo ist öffentlich. Deshalb liegt die echte Datei nur lokal. Die Vorlage
kopieren, dann befüllen:

```bash
cp data/provisionen/provisionen-vorlage.csv data/provisionen/provisionen.csv
```

## Spalten (Reihenfolge fest)

| Spalte | Regel | Beispiel (erfunden) |
|---|---|---|
| `monat` | `JJJJ-MM`, nicht in der Zukunft | `2026-09` |
| `partner` | `CHECK24`, `Tarifcheck`, `C24 Bank` oder `sonstig` | `CHECK24` |
| `abschluesse` | ganze Zahl ≥ 0 | `4` |
| `stornos` | ganze Zahl ≥ 0 | `1` |
| `provision_eur` | Dezimalpunkt, höchstens 2 Stellen, ≥ 0, ohne Tausendertrennung | `126.50` |
| `abrechnung_ref` | Nummer der Partner-Abrechnung. Pflicht, sobald `provision_eur` > 0 | `CHECK24-Abr-2026-09` |
| `notiz` | frei, höchstens 200 Zeichen | `Nachberechnung Juli` |

Eine Zeile je Monat und Partner. Doppelte Kombinationen werden abgewiesen.
Enthält ein Feld ein Komma (etwa in `notiz`), das Feld in Anführungszeichen setzen: `"Nachberechnung, Juli"`.

Beispiel:

```csv
monat,partner,abschluesse,stornos,provision_eur,abrechnung_ref,notiz
2026-09,CHECK24,4,1,126.50,CHECK24-Abr-2026-09,Beispielzeile
```

## Konventionen

- **Stornos, die Provision mindern:** im Monat der Abrechnung als Nettobetrag
  eintragen. Die Provision darf nicht negativ sein. Die Zahl der Stornos steht
  in `stornos`, die Begründung in `notiz`.
- **Nachberechnungen:** wie eine normale Zeile im Monat der Abrechnung, Hinweis in `notiz`.
- **Abrechnungsnummer:** nur die Referenz aus dem Partnerportal. Niemals Namen,
  Kundennummern oder Kontodaten.
- Der Betrag wird brutto so eingetragen, wie der Partner ihn abrechnet.

## Prüfen

```bash
npm run provisionen:check            # prüft die lokale Datei und zeigt die Zusammenfassung
python3 scripts/provisionen_check.py          # nur prüfen, ohne Zusammenfassung
python3 scripts/provisionen_check.py --selftest  # Selbsttest der Prüfregeln
```

Ausgaben:

- **„Datenlage offen“** (Exit 0): die lokale Datei fehlt. Das ist kein Fehler,
  solange noch keine Abrechnung eingetragen ist.
- **Fehlerliste** (Exit 1): Zeilen mit Problemen, mit Zeilennummer. Erst korrigieren, dann committen. Nur die Vorlage gehört ins Repo.
- **Zusammenfassung** (`--summary`): Abschlüsse, Provision gesamt, Ø Provision je
  Abschluss und Monate ohne jede Zeile. Eine Lücke heißt: Abrechnung fehlt
  oder war Null. Das prüfen, nicht raten.

Die Prüfung schlägt Alarm bei E-Mail-Adressen, IBAN-ähnlichen Nummern und langen
Zahlenfolgen in `notiz` oder `abrechnung_ref`. Das ist eine Sicherung, kein
Ersatz für die eigene Sorgfalt.

## Monatliche Routine

1. Nach Eingang der Partner-Abrechnung: Zeilen für den Abrechnungsmonat ergänzen.
2. `npm run provisionen:check` ausführen, bis „gültig“ erscheint.
3. Mit `--summary` die Zahlen gegen das Partnerportal abgleichen.
4. Die Tabelle wird nicht committet. Sie bleibt lokal.

## Grenzen

- Die Tabelle erfasst nur, was eingetragen wird. Sie prüft nicht, ob die Partner
  richtig abrechnen.
- Die Prüfung ersetzt keine Steuer- oder Rechtsberatung. Vermittlerfragen
  (§ 34d GewO, Tippgeber-Grenzen) sind separat zu klären.
- Die echte Datei ist die einzige Kopie. Sicherung außerhalb des Repos einplanen.
