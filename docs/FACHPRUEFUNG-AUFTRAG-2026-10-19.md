# Fachprüfungs-Auftrag: Konto, Karten und Zinsen (Entscheidung E-05)

Stand: 19.10.2026 · Auftraggeber: Frank Hartung · Status: **Auftrag vorbereitet, Prüfer offen**

Dieser Auftrag ist die Grundlage, um die Fachprüfung der 17 Ratgeber mit Finanzaussagen durchzuführen. Er liefert die Prüfkriterien, die Reihenfolge und das Protokoll. Er nennt **keinen Prüfer**. Eine Prüfung gilt erst als erfolgt, wenn ein benannter Prüfer sie schriftlich bestätigt hat. Solange das nicht geschehen ist, darf im Register kein Befund als „geprüft“ stehen.

## 1. Auftragsgegenstand

Die Beiträge stehen im Register `data/fachpruefung_register.yaml` (Anzahl und Status werden durch `scripts/fachpruefung_register.py --check` geprüft). Die Reihenfolge ist: zuerst die 6 Beiträge zu Konto, Karten und Zinsen, danach die übrigen.

| Nr. | Beitrag (Slug) | Priorität | Status |
|---|---|---|---|
| 1 | `2026-08-12-geld-abheben-im-ausland-gebuehren-vermeiden` | Konto/Karten/Zinsen (zuerst) | ausstehend |
| 2 | `2026-08-17-abos-und-vertraege-stiller-posten-haushaltsplan` | weitere Themen | ausstehend |
| 3 | `2026-08-17-kostenloses-girokonto-so-findest-du-ein-konto-ohne-gebuehren` | Konto/Karten/Zinsen (zuerst) | ausstehend |
| 4 | `2026-08-21-haushaltsbuch-fuehren-app-excel-oder-papier` | weitere Themen | ausstehend |
| 5 | `2026-08-26-tagesgeld-zinsen-2026-die-besten-zinssaetze-im-vergleich` | Konto/Karten/Zinsen (zuerst) | ausstehend |
| 6 | `2026-08-26-warmwasser-sparen-rechnung-hinter-dem-hahn` | weitere Themen | ausstehend |
| 7 | `2026-08-28-lastschrift-und-dauerauftrag-abbuchungen-pruefen` | Konto/Karten/Zinsen (zuerst) | ausstehend |
| 8 | `2026-08-31-nachtstrom-tarife-wann-sich-ein-doppeltarifzaehler-noch-lohnt` | weitere Themen | ausstehend |
| 9 | `2026-08-31-stoerung-beim-internetanbieter-so-sicherst-du-deine-rechte` | weitere Themen | ausstehend |
| 10 | `2026-09-03-kreditkarte-vergleichen-kostenlos-sicher-bezahlen` | Konto/Karten/Zinsen (zuerst) | ausstehend |
| 11 | `2026-09-04-umzug-mit-internet-anschluss-und-rufnummer-mitnehmen` | weitere Themen | ausstehend |
| 12 | `2026-09-21-grundversorgung-strom-und-gas-was-sie-leistet` | weitere Themen | ausstehend |
| 13 | `2026-09-23-einlagensicherung-wie-viel-guthaben-geschuetzt-ist` | Konto/Karten/Zinsen (zuerst) | ausstehend |
| 14 | `2026-09-28-zaehlerstand-ablesen-und-melden-schaetzwerte-vermeiden` | weitere Themen | ausstehend |
| 15 | `2026-10-05-bueroausstattung-steuerlich-clever-absetzen-so-vermeidest` | weitere Themen | ausstehend |
| 16 | `2026-10-07-dsl-anbieter-wechseln-warum-treue-dich-bares-geld-kostet` | weitere Themen | ausstehend |
| 17 | `2026-10-07-handyvertrag-kuendigen-raus-aus-der-kostenfalle-verlaengerung` | weitere Themen | ausstehend |

## 2. Qualifikation des Prüfers (Mindestanforderung)

- Nachweisbare Fachausbildung oder Berufserfahrung im Bereich Privatkundengeschäft von Banken, Kreditkarten oder Geldanlage (z. B. Bankkauffrau/Bankkaufmann, Finanzberater:in mit Sachkundeprüfung).
- Keine Verbindung zu einem Anbieter, dessen Produkt im Beitrag verglichen oder empfohlen wird. Das schließt Provisionsvereinbarungen mit Anbietern aus dem Beitrag aus.
- Der Prüfer nennt Name, Qualifikation und Datum schriftlich. Wer nur einen Stempel oder ein Logo liefert, erfüllt den Auftrag nicht.

## 3. Prüfkriterien je Beitrag

1. **Konditionen und Zahlen** sind mit dem Stand des Prüftags belegt (Gebühren, Zinssätze, Limits, Schwellen). Abweichungen werden mit Fundstelle notiert.
2. **Rechtslage** stimmt: Einlagensicherung, Verbraucherrechte, Fristen, Kündigungsrechte. Bei Neuregelungen wird der Stichtag genannt.
3. **Keine irreführende Verkürzung:** Gebührenfreiheit hat Bedingungen (z. B. Mindesteingang), und die Bedingungen stehen im Beitrag.
4. **Empfehlungen sind begründet.** Jede Handlungsempfehlung ist an eine Rechnung oder an eine Quelle gebunden.
5. **Affiliate-Kennzeichnung** ist vorhanden, wo ein Partnerlink steht, und sie steht vor dem Link.
6. **Quellen** sind erreichbar und stammen aus Primär- oder anerkannten Sekundärquellen.

## 4. Protokoll (Vorlage je Beitrag)

```
Beitrag:       <slug>
Prüfer:        <Name, Qualifikation>
Prüfdatum:     <TT.MM.JJJJ>
Ergebnis:      freigegeben | Korrektur nötig | nicht freigegeben
Befunde:       <Stelle im Text> – <Abweichung> – <Quelle mit Stand>
Korrektur:     <Änderung im Repo> (Commit-Hinweis)
```

Ein Protokoll ohne Fundstelle ist ungültig. Korrekturen werden in `data/beweise/korrekturen.yaml` festgehalten.

## 5. Abnahme (wann der Auftrag als erledigt gilt)

- Für alle Konto-/Karten-Beiträge liegt ein unterschriebenes Protokoll vor.
- Im Register stehen Prüfer, Datum und Ergebnis. `scripts/fachpruefung_register.py --check` ist grün.
- Die Korrekturen sind umgesetzt, und die Live-Gates (`editorial_review_gate.py --published --strict`) sind grün.

## 6. Was dieser Auftrag nicht leistet

- Keine Anlage- oder Steuerberatung im Sinne des Gesetzes. Die Beiträge sind Ratgeber, keine individuelle Empfehlung.
- Keine Bewertung der Redaktion durch den Prüfer. Der Prüfer prüft Fakten und Rechtslage.
