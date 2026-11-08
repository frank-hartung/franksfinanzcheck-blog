# #1098 – Runde 2: Fachbefunde geheilt, Fassungsbindung dauerhaft repariert

**Stand:** 07.11.2026 · **Herausgeber:** Frank Hartung · **Branch:** `arena/9e00ce3a-franksfinanzcheck-blog`

## Ausgangslage nach dem Merge von #1125

Der erste Dispatch der Release-Scorecard auf `main`
([Lauf 42384831745](https://github.com/frank-hartung/franksfinanzcheck-blog/actions/runs/42384831745))
lief vollständig durch – Heiler, Beweisbasis, Nachmessung, Ticket, Artefakte –
und meldete ehrlich **rot**:

| Kennzahl | Wert |
|---|---|
| Siegel | `d1e1c4a`, 07.11.2026 15:11:47 UTC |
| Werkzeugfehler | keine (`tool_fehler: {}`) |
| blockiert | 3 Live-Seiten, 12 Fachbefunde |
| Ursache | ausschließlich `F4-fachbefund` → `entscheidung: human` |

Die Maschine hat also genau das getan, was sie soll: Sie hat die Beweisbasis
gebaut, geheilt was heilbar ist, und den Rest einem Menschen vorgelegt.

## Befund 1: Zehn neue Fachbefunde – inhaltlich behoben

Zwei Artikel trugen Aussagen ohne Beleg. Sie sind nicht wegformuliert, sondern
belegt oder präzisiert worden:

**Energiediebe stoppen** (5 Befunde)

* Messdauer: unbelegte „24 Stunden“ → **sieben Tage messen, auf ein Jahr
  hochrechnen**, an jeder Nennstelle inline auf die Verbraucherzentrale
  verlinkt (Kurzantwort, Schnellstart, Tipps, Messdauer, Messwoche, Fazit, FAQ).
* Ausleihe: Aussage auf die belegten **VZ-Beratungsstellen** verengt,
  regionale Unterschiede benannt, unbelegter Bibliotheks-Hinweis gestrichen.
* Strompreis: 0,37 €/kWh jetzt mit **BDEW-Haushaltsdurchschnitt Oktober 2026
  (37,3 ct/kWh, Stand 28.10.2026)** verlinkt und als Durchschnitt gekennzeichnet.
* Amortisation: 650 €, 310/140 kWh durchgehend als **frei gewählte
  Modellannahmen** gekennzeichnet, mit Verweis auf eigene Messung und EU-Label.
* Regulatorischer Rahmen: neuer Absatz zu **Messstellenbetreiber und
  Befundprüfung** mit Beleg der Bundesnetzagentur.

**Warmwasser sparen** (5 Befunde)

* „Zweitgrößter Kostenposten“ war nicht belegbar → **rund 16 Prozent des
  Haushalts-Energieverbrauchs** (co2online, Grafik Stand 10/2025), auch in
  `description`, `pin_description` und FAQ.
* Eigener Abrechnungsblock: aus „üblicherweise“ wurde **§ 9 HeizkostenV**
  (Aufteilung, Wärmezähler, Verteilung nach §§ 7/8) im amtlichen Wortlaut.
* Legionellen: **55 °C im Leitungssystem, 60 °C am Speicherausgang bei über
  400 l bzw. über 3 l Leitungsinhalt, Prüfung alle drei Monate** – VZ-Ratgeber
  vom 21.07.2026 mit Bezug zur Trinkwasserverordnung.
* VZ-Fundstellen zeigen jetzt auf die Seiten, die die Aussage tragen
  (17755, 30096 kanonisch, 17752); der unpassende Verweis 13892 ist entfernt.
* 0,30 €/kWh ist als **frei gewählte Rechenannahme** gekennzeichnet, dem
  BDEW-Durchschnitt gegenübergestellt, mit Hinweis auf Gas-/Wärmepreis.

Einzelnachweis nach der Änderung: `technik ✅ · quellen ✅ · affiliate ✅ ·
redundanz ✅` – offen war allein der F4-Befund, der auf die Freigabe wartete.

## Befund 2: Der Textpflege-Bot öffnete entschiedene Befunde

`d1e1c4a` hatte an der 50-30-20-Regel **nur** die abgeleitete Zeile
`*Abbildung: Gliederung …*` neu geschrieben. Dadurch änderte sich der
Text-Hash, die Fassungsbindung lief aus, zwei entschiedene Befunde waren
wieder offen. Der geprüfte Inhalt war wortgleich.

**Dauerhafte Reparatur statt Regel-Lockerung:**

* `kerntext()` nimmt abgeleitete Bildblöcke (`abbildung-merkkarte.svg`,
  `abbildung-ablauf.svg` samt direkt folgender Unterschrift) aus dem
  Fassungs-Hash. Sie tragen nichts, was nicht schon in Titel, Kurzantwort
  oder Body steht – jede echte Aussageänderung öffnet weiter.
* Eine handgeschriebene `*Abbildung: …*`-Zeile bleibt Teil der Aussage.
* Alt-Entscheidungen bleiben gültig: `text_hash_volltext` ist eine
  **strengere** Bindung (bytegenauer Text) und trägt weiter.
* `--fassung-normalisierung [--apply]` übersetzt sie einmalig auf den
  Kern-Hash – nur bei **Bytegleichheit** zum Bestand, als reine
  Hash-Übersetzung unter `fassung_normalisierungen`, nie als Entscheidung.
  Ein erfundenes Ziel schließt nichts, Formfehler sind Werkzeugfehler.
* Regressionen: Bot-Nachzug öffnet nicht, echte Änderung öffnet,
  Normalisierung ist idempotent, erfundenes Ziel wirkungslos, beschädigte
  Einträge fail-closed (Selbsttest + 4 Unit-Tests).

Angewendet auf den Bestand: **121 Hash-Übersetzungen**, alle beweisbar.

## Befund 3: Deploy auf `main` war rot – verursacht von Runde 1

Beim Nachmessen fiel auf, dass der Deploy-Lauf
[42383988949](https://github.com/frank-hartung/franksfinanzcheck-blog/actions/runs/42383988949)
auf `462d748` am Schritt **„Faktenfrische Gas – Rückfallschutz“** scheiterte;
die Pages-Auslieferung wurde übersprungen. Ursache war ein Fehler aus
Runde 1, nicht aus dem Bestand:

* Sechs Artikel waren per Hand mit `faktencheck: 2026-11-07` gestempelt,
  obwohl ihr echter Lauf laut Dossier am 01./03./06.11. stattfand. Ein
  handgesetzter Maschinenstempel täuscht eine Prüfung vor – der
  Rückfallschutz stoppt zu Recht das Deploy.
  **Reparatur:** Stempel auf den Dossierlauf zurückgesetzt, `lastmod`
  bleibt ehrlich auf 2026-11-07.
* Die Anker des Registers `996-N12` beschrieben einen älteren Wortlaut.
  Die Aussage steht belegt im Text („mindestens einen Monat vorher
  informieren“, „Für die Grundversorgung gelten strengere Regeln nach
  § 5 StromGVV/GasGVV“). **Reparatur:** Anker auf den belegten Wortlaut
  synchronisiert, Untersagungen unverändert.

Damit läuft der Rückfallschutz wieder grün (17/17), ohne dass eine Regel
aufgeweicht wurde.

## Freigabe und Entscheidungen

Frank Hartung hat die zwölf konkreten Fassungen in dieser Session explizit
bestätigt (Entscheidungsvorlage:
`F4-ENTSCHEIDUNGSVORLAGE-1098-RUNDE2-2026-11-07.md`) und die dauerhafte
Reparatur der Fassungsbindung im selben Zug beauftragt.

Geschrieben wurden **12 Entscheidungen** – zehn Erstentscheidungen auf den
geheilten Texten, zwei Folgeentscheidungen auf der heutigen Fassung der
50-30-20-Regel mit Vorgänger-Referenz. Jede trägt Prüfer, Datum, Begründung
und Beleg-URL.

Danach: `BEFUND-AKTE.md` neu erzeugt → **11 offene Befunde auf 3 Seiten,
0 davon live**, keiner über Frist, jeder entscheidbar.

## Was offen bleibt

Die elf restlichen Befunde liegen auf **nicht live** geschalteten Seiten
(zwei Entwürfe und die Ratgeberseite `strom-sparen`). Sie bleiben offen, bis
ihre Aussagen geprüft und entschieden sind – die Maschine schließt sie nicht.
