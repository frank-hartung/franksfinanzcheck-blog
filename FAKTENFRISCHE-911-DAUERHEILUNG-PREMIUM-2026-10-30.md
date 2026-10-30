# Faktenfrische #911 – zehn fachliche Befunde dauerhaft behoben

Stand: 30. Oktober 2026. Auftrag: „Bitte dauerhaft auf Highend-Level einer
Profi-Agentur beheben.“ Lokale Umsetzung auf dem Arbeitsbranch
`arena/761af003-franksfinanzcheck-blog`; Freigabe über Pull Request
(„Closes #911“). Keine Veröffentlichung, keine redaktionelle Freigabe und
kein Prüfsiegel vorgenommen – beide Artikel bleiben `draft: true`.

## Ausgangslage

Issue #911 meldete zehn offene fachliche Befunde aus dem Faktenfrische-Lauf
vom 27.10.2026, 10:01 UTC. Beide betroffenen Seiten standen zur
**Erstrecherche** an; die Maschine hatte vertragsgemäß nur `faktencheck`
und `quellen` gesetzt – den Text berührt sie nie. Der erste Textversuch aus
PR #938 (29.10.2026) verbesserte einzelne Formulierungen, hinterließ aber
weder eine Schließakte noch eine Regression. Zusätzlich blieben zwei
Präzisionsfehler stehen: „nicht jeden Preis“ statt „keine staatliche
Genehmigung“ und die 24-Stunden-Regel, die pauschal auf Gas übertragen
wurde. Diese Heilung schließt die Befunde, misst die Gates und sichert die
Entscheidungen gegen Rückfall ab.

| Seite | Befunde | GEO-Reife vorher | GEO-Reife jetzt |
|---|---|---|---|
| Stromanbieter wechseln (23.10.) | 5 | 83 % (5/6) | **100 % (6/6)** |
| Gastarife vergleichen (26.10.) | 5 | 83 % (5/6) | **100 % (6/6)** |

Gemessen mit der Maschinenlogik selbst (`geo_reife()` aus
`scripts/faktenfrische.py`, unveränderter Prüfcode). Die 50 % aus dem
Issue waren der Stand vor dem automatischen Frontmatter-Eintrag; nach dem
Lauf standen beide bei 5/6. Offen war die Kurzantwort-Box im Frontmatter –
jetzt redaktionell erfüllt.

## Befund für Befund

### Stromanbieter wechseln (B1–B5)

1. **luecke – „große Lücken zwischen den Tarifen“ ohne Quelle.** Die
   unbelegte Marktbehauptung ist ersatzlos gestrichen. An ihrer Stelle steht
   die amtlich belegte **Angebotsvielfalt**: Verbraucher können den Anbieter
   nach Preis, Service und Energiemix wählen (Q1, Bundesnetzagentur). Der
   Text sagt ausdrücklich, dass damit kein pauschales Sparversprechen
   verbunden ist. Die Ersparnis wird an Verbrauch, alten Tarif und Angebot
   gebunden.
2. **luecke – Bonus senkt den Preis im ersten Jahr „stark“.** Die
   Marktwirkung ist gestrichen; der Bonus ist jetzt eine **eigene
   Rechengröße**. Der Artikel verlangt, Bedingungen und Auszahlungstermin zu
   prüfen und den Tarif zusätzlich ohne Bonus zu rechnen. Die Tabelle
   markiert den Bonus als „senkt den Preis nur bei erfüllten Bedingungen“,
   nicht als Rabattzusage.
3. **praezision – Verbrauchsschwelle 3.000/2.000 kWh.** Die Faustregel ist
   entfernt. Stattdessen erklärt der Text die Mechanik: Der Grundpreis fällt
   unabhängig vom Verbrauch an, bei kleinen Haushalten wiegt er schwerer,
   bei großen der Arbeitspreis. Gerechnet wird immer mit dem eigenen
   Jahresverbrauch. Eine Verbrauchsgrenze ist keine Tarifregel.
4. **praezision – Wechsel „kostet keinen Cent“, keine „Abschiedsgebühr“.**
   Die Aussage ist auf **Haushaltskunden** begrenzt und mit der Norm belegt:
   § 20 StromGVV und § 20a Absatz 3 EnWG; die Bundesnetzagentur bestätigt
   die Kostenfreiheit ausdrücklich (Q1). Der Text ergänzt, dass die Aussage
   für andere Kundengruppen nicht automatisch gilt. Die technische
   24-Stunden-Regel und die vertragliche Kündigungsfrist sind getrennt.
5. **praezision – CHECK24 listet „fast alle Firmen und Tarife“.** Das
   Vollständigkeitsversprechen ist gestrichen. Portale zeigen eine Auswahl;
   Anbieter, Filter und Sortierung unterscheiden sich. Der Text verweist auf
   die Vertragsunterlagen beim Anbieter und auf Laufzeit, Frist, Garantie
   und Zahlungsweise (Q1).

### Gastarife vergleichen (B6–B10)

6. **luecke – Regulierungsrahmen fehlte.** Neuer Abschnitt **„Was die
   Behörde reguliert – und was nicht“**: Die Bundesnetzagentur beaufsichtigt
   den Gasmarkt und setzt die Wechselregeln, genehmigt aber keine
   Endkundenpreise. Ergänzt sind die Monatsfrist bei Preisänderungen, das
   Sonderrecht, Beschwerde/Schlichtung, die kostenfreie Kündigung und der
   Wechsel für Haushaltskunden sowie die **zwei Wochen** Kündigungsfrist in
   der Grundversorgung (Q1/Q2).
7. **luecke – Preisgarantie „typischerweise sechs Monate“.** Die erfundene
   Standarddauer ist gestrichen. Der Text sagt: Es gibt **keine einheitliche
   Standarddauer**; maßgeblich ist der Vertrag. Vier Prüffragen klären
   Umfang, Beginn, Ausnahmen und den Preis nach dem Ende. Die Preisbindungs-
   klausel kann eine Erhöhung ausschließen (Q1) – muss aber nicht jeden
   Preisbestandteil umfassen.
8. **luecke – Thermostat spart „bis zu 10 Prozent“.** Die 10-Prozent-Angabe
   ist gestrichen. Belegt ist jetzt der Richtwert der Verbraucherzentrale:
   **ein Grad weniger Raumtemperatur senkt den Verbrauch um etwa sechs
   Prozent** (Q3). Dazu stehen die Thermostatstufen (Stufe 3 ≈ 20 °C, Stufe
   2 ≈ 16 °C), die empfohlenen Raumtemperaturen und die Warnung, nicht
   dauerhaft unter 16 °C zu heizen (Feuchte/Schimmel).
9. **luecke – „2 °C = 6 % = 720 kWh“ ohne Quelle.** Die Rechnung ist jetzt
   ein gekennzeichnetes Modell: 12.000 kWh × 6 % = **720 kWh**; bei
   angenommenen 0,08 €/kWh sind das **57,60 €**. Der Text sagt ausdrücklich,
   dass die Rechnung nur gilt, wenn der gesamte Verbrauch auf die Heizung
   entfällt, und dass **zwei Grad nicht automatisch zwölf Prozent** bedeuten.
   Der Richtwert darf nicht beliebig vervielfacht werden.
10. **praezision – CHECK24 zeigt „alle wichtigen Konditionen“.** Das
    Versprechen ist gestrichen. Der Text beschreibt das Portal als Auswahl,
    nicht als Gesamtmarkt, und verlangt den Abgleich mit den Bedingungen
    beim Anbieter sowie den Vergleich der vollständigen Kosten.

### Zwei zusätzliche Präzisionsfehler aus dem Vorgängertext

- **„Die Bundesnetzagentur genehmigt nicht jeden Strom- oder Gaspreis“**
  suggerierte eine Teilgenehmigung. Richtig ist: Es gibt **keine staatliche
  Genehmigung** der Preise; Anbieter kalkulieren selbst (Q1). Beide Artikel
  sind entsprechend korrigiert.
- **24-Stunden-Regel pauschal für Gas.** Die Bundesnetzagentur beschleunigt
  den **technischen Stromlieferantenwechsel** ab 6. Juni 2025 auf 24
  Stunden an Werktagen. Für Gas gilt diese Aussage nicht. Der Gastext sagt
  jetzt ausdrücklich „Beim Strom …“, ergänzt „Eine 24-Stunden-Frist wie beim
  Strom nennt diese Seite für Gas nicht“ und hält für Gas die regulären
  Fristen des Wechselprozesses fest. Eine eigene Regression sichert die
  Abgrenzung ab.

### Bei der Schlussprüfung am 30.10.2026 zusätzlich präzisiert

- **Verbraucherberatung als Behördenverweis.** Der Stromtext ließ die
  Behörde auf „Tarifrechner, Verbraucherberatung und direkte Angebote“
  verweisen. Die abgerufene Seite nennt Tarifrechner und Vergleichsportale,
  die Hinweise des Bundeskartellamts und direkte Angebote der Anbieter, aber
  keine Verbraucherberatungsstelle. Der Satz ist auf die belegten Elemente
  umgestellt; der B5-Anker „vor dem Abschluss die Unterlagen zu prüfen“
  bleibt erhalten.
- **Umsatzsteuer-Ausnahme.** Die Aussage zum fehlenden Sonderkündigungsrecht
  gilt nach Q1 ausdrücklich bei einer Erhöhung **und** bei einer Senkung der
  Umsatzsteuer. Der Gastext nennt jetzt beide Richtungen.

## Zusätzlich behoben (Premium-Umfeld der Befunde)

- **Sprache und Ton:** durchgängige Du-Anrede; die Mischung aus „du“ und
  „Sie“ („Dann dürfen Sie meist sofort kündigen“) ist beseitigt. Vage
  Behördenprosa („Die Agentur vom Staat“) ist durch „die Bundesnetzagentur“
  bzw. „die Behörde“ ersetzt. Keine Template-Intro-Formel.
- **Struktur:** Absätze auf in der Regel höchstens vier Sätze gekürzt; die
  acht harten Absatzverstöße des Stromtextes sind weg. Überschriften und
  Tabellen tragen die Prüfschritte, statt Fließtext zu wiederholen.
- **GEO:** `kurzantwort` im Frontmatter ergänzt und die doppelte manuelle
  Kurzantwort-Box aus dem Body entfernt. Beide Artikel erreichen 6/6
  Kriterien (Kurzantwort, FAQ, Quellen, Zahlen, Tabelle, Faktencheck).
- **Interne Verlinkung:** von 0 auf **3** Links je Artikel (Strom ↔ Gas,
  Ökostrom, Haushaltsgeräte, Energieeffizienz, Gaspreisgarantie). Alle Ziele
  existieren; die Anker passen zum Ziel.
- **Modellrechnungen:** beide Rechenbeispiele sind als frei gewählte
  Annahmen gekennzeichnet und werden von der Regression Zelle für Zelle
  nachgerechnet. Die Zahlen sind keine Marktpreise.
- **Transparenz:** sichtbare Zeile „Fachlich überarbeitet am 30.10.2026“,
  `lastmod: 2026-10-30`, `redaktionelle_pruefung.aenderungsgrund` mit
  Issue-Bezug. Der Maschinen-Stempel `faktencheck: 2026-10-29` bleibt
  unangetastet; er wird nicht hochdatiert. Beide Artikel bleiben Entwürfe.

### Messwerte vorher/nachher

| Seite | Kennzahl | vorher (PR #938) | jetzt |
|---|---|---:|---:|
| Strom | Lesbarkeits-Score | 95 | **100** |
| Strom | Flesch (Ziel ≥ 60) | 77,9 | **61,7** |
| Strom | Body-Zeichen (Korridor 10.000–22.000) | 9.989 | **12.395** |
| Strom | harte Textverständnis-Regeln | 8 | **0** |
| Strom | interne Links (Minimum 2) | 0 | **3** |
| Gas | Lesbarkeits-Score | 65 | **100** |
| Gas | Flesch (Ziel ≥ 60) | 39,8 | **60,5** |
| Gas | Body-Zeichen | 11.969 | **12.503** |
| Gas | harte Textverständnis-Regeln | 0 | **0** |
| Gas | interne Links | 0 | **3** |
| beide | GEO-Reife | 83 % | **100 %** |

Der Stromtext hat jetzt längere, präzisere Sätze als der staccatoartige
Vorgänger; er bleibt über der 60er-Schwelle. Der Gastext liegt mit 60,5
knapp darüber und damit ebenfalls über der Gate-Grenze, aber unter dem
internen 62er-Ziel. Beide Werte sind ehrlich gemessen, nicht geglättet.
Entscheidend ist die Gate-Parität: Der Vorgänger scheiterte an acht harten
Absatzregeln und an fehlenden internen Links, obwohl der Score 95 zeigte.

## Dauerhafte Absicherung

### 1. Schließakte: `data/faktenfrische_befunde_911.yaml`

Zehn Einträge mit Befund, Entscheidung, Status `behoben`, Belegtyp,
Beleg-URL, Bedeutungsankern, verbotenen Behauptungen und Restrisiko. Der
Vertrag ist maschinenprüfbar:

- `beleg_url` ist entweder `null` (nur bei `belegtyp: streichung` zulässig)
  oder eine URL aus der Allowlist in `data/agent_reach/faktenfrische.yaml`.
- Diese URL muss zusätzlich wörtlich in `quellen` des jeweiligen Artikels
  stehen. Damit kann kein Beleg außerhalb der Redaktionsquellen entstehen.
- Die Anker sind Bedeutungs-Invarianten, keine Zitate. Entfernt jemand den
  Satz, der die Entscheidung trägt, wird die Regression rot.
- Die Datei ist menschlich kuratiert; `faktenfrische.py` schreibt sie nie.

### 2. Regression: `scripts/tests/test_faktenfrische_911.py` (20 Tests)

- **B1–B10 verneinungstolerant:** Jede Fehlbehauptung darf behauptend nie
  zurück; Leserfragen, Dämpfungen und ausdrücklich verworfene Beispiele
  bleiben erlaubt. Beispiel: „Angaben wie ‚typisch sechs Monate‘ helfen dir
  nicht“ ist zulässig, „Eine Preisgarantie dauert typischerweise sechs
  Monate“ nicht.
- **Arithmetik wird nachgerechnet, nicht abgetippt:** Strom 3.200 × 0,32 =
  1.024, 3.200 × 0,28 = 896, 12 × 10 = 120, 12 × 8 = 96, 1.024 + 120 =
  1.144, 896 + 96 = 992, 1.144 − 992 = 152. Gas 12.000 × 0,08 = 960,
  960 + 120 = 1.080, 12.000 × 0,06 = 720, 720 × 0,08 = 57,60.
- **Kennzeichnungspflicht:** Modelltabellen ohne „frei gewählt“ im
  Prosasatz davor machen rot.
- **24-Stunden-Regel:** eigene Prüfung, dass sie im Gasttext ausdrücklich
  auf Strom begrenzt ist.
- **Metadaten-Korridor:** `lastmod` ≥ 30.10.2026, `faktencheck` ≥ 27.10.,
  `kurzantwort`, description 70–165 Zeichen, GEO 6/6, Entwurfsstatus,
  sichtbare Überarbeitungszeile.
- **Gate-Parität:** Score ≥ 75, Flesch ≥ 60, Zeichenkorridor 10.000–
  22.000, keine harten Textregeln, interne Links ≥ 2.
- **Anrede und Register:** kein formelles „Sie/Ihre“ im Du-Artikel; das
  Register deckt alle zehn Befunde mit Beleg und Anker ab; die Queue führt
  die beiden Slugs nicht als offen.
- **Prüfauftrag:** Die neuen #911-Klassen stehen im SYSTEM_PROMPT.

**Sabotage-Probe (dokumentiert):** Mit drei testweise wieder eingefügten
Fehlern (Portal-Vollständigkeit, Garantie-Standarddauer, falsche
Ersparnis-Zelle) und der dadurch ausgelösten Flesch-Grenze wurden
**6 Tests rot**. Nach Rücknahme: 20/20 grün. Die Regression schützt also
die Bedeutung, nicht nur die Schreibweise.

### 3. Prüfanweisung: SYSTEM_PROMPT in `scripts/faktenfrische.py`

Neue Regel 10 mit den Befund-Klassen aus #911: (a) Vollständigkeits- und
Vergleichsversprechen von Portalen, (b) Verbrauchsschwellen als Tarifregel,
(c) „kostenlos/keine Gebühr“ nur mit Norm und Zielgruppe, (d) Sparprozente
aus Heizverhalten nur mit Quelle und als Richtwert (keine Scheingenauigkeit
„2 °C = 6 %“), (e) Aufsicht ist keine Preisgenehmigung, (f) Behördenfristen
mit Zielgruppe, Stichtag und Abgrenzung technischer Prozess/Vertrag. Die
Regeln aus #823 bleiben unverändert erhalten.

### 4. Betriebsdokumentation und Aufruf

`scripts/FAKTENFRISCHE.md` erklärt jetzt Register und Regression als
Schließpfad. `package.json` enthält den gezielten Aufruf
`npm run test:faktenfrische:911`. Die Publication-Reliability-CI entdeckt
das Modul ohnehin über `unittest discover`.

## Nachweise

- `python3 -m unittest discover -s scripts/tests -p 'test_faktenfrische_*.py'`:
  **93 Tests, OK** (1 Skip: fehlendes Alt-Dossier aus #823).
- Zusätzlich `test_faktenfrische_763`, `_823`, `_robustheit`, `_kapazitaet`,
  `test_publish_gate_faktenfrische`: **98 Tests, OK** (1 Skip).
- `python3 scripts/faktenfrische.py --selftest`: **23/23 grün**.
- `textverstaendnis_guard.py --selftest`, `readability_check.py --selftest`,
  `link_density_guard.py --selftest`: grün.
- `git diff --check`: sauber.
- Artikel über den echten Faktenfrische-Parser eingelesen: **6/6
  GEO-Kriterien, 100 %** je Artikel; Gates siehe Tabelle oben.

## Grenzen und Freigabe

- **Kein Hugo-Build und kein Browsernachweis.** Hugo ist in dieser
  Arbeitsumgebung nicht installiert; der Binär-Download scheitert an der
  Netzsperre. Markdown, Frontmatter, relative Links und Gates wurden
  geprüft, nicht das gerenderte HTML.
- **Dossiers nicht neu gebunden.** Die automatisch erzeugten Dossiers
  unter `data/research/artikel/` stammen aus dem Lauf vom 27.10.2026 und
  tragen noch die alten Titel und den GEO-Stand 3/6. Sie sind
  Maschinenartefakte und wurden hier nicht von Hand überschrieben; ein
  neuer `faktenfrische.py`-Lauf mit Dossier-Schreibung bleibt dafür
  erforderlich. Die Belegkette der Artikel hängt nicht daran: Quellen,
  Register und Regression sind unabhängig davon vollständig.
- **Kein vollständiger Repository-Testlauf.** Ausgeführt wurden die
  Faktenfrische-, Publish-Gate- und Guard-Tests sowie die Selbsttests der
  beteiligten Wächter. Die komplette Suite und E2E-Tests liefen nicht.
- **Keine neue Live-Marktprobe.** Die Quellen wurden am 30.10.2026
  ausschließlich lesend abgerufen (Bundesnetzagentur, Verbraucherzentrale);
  es wurden keine Marktzahlen ohne Fundstelle ergänzt. Ein Seiteninhalt kann
  sich nach dem Abruf ändern.
- **Kein Prüfsiegel.** Beide Artikel bleiben `draft: true`, die
  redaktionelle Prüfung bleibt `ausstehend`. Der `faktencheck`-Stempel
  bleibt beim echten Maschinenlauf (29.10.2026); `lastmod` dokumentiert nur
  den Texteingriff. Eine menschliche Freigabe und ein neuer Faktenfrische-
  Lauf bleiben erforderlich.
- **Die Regression ist Rückfall-Schutz, kein Wahrheitsbeweis.** Sie kann
  nicht erkennen, ob eine neue, anders formulierte Marktbehauptung falsch
  ist. Dafür bleiben Recherche, Fachprüfung und Redaktion zuständig.
- **Restrisiken je Befund** stehen im Register: Garantieklauseln sind
  individuell, der Sechs-Prozent-Wert ist ein Richtwert, und Portale können
  einzelne Konditionen zeigen, aber keine Vollständigkeit zusichern.

## Geänderte Dateien

- `content/posts/2026-10-23-stromanbieter-wechseln-und-bis-zu-300-euro-sparen/index.md`
- `content/posts/2026-10-26-gastarife-vergleichen-vor-dem-herbst/index.md`
- `data/faktenfrische_befunde_911.yaml` (neu)
- `scripts/tests/test_faktenfrische_911.py` (neu)
- `scripts/faktenfrische.py` (Prüfanweisung Regel 10)
- `scripts/FAKTENFRISCHE.md` (Betriebsdokumentation)
- `package.json` (npm-Aufruf `test:faktenfrische:911`)
