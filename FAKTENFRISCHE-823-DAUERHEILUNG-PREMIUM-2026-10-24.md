# Faktenfrische #823 – 7 fachliche Befunde dauerhaft behoben

Stand: 24. Oktober 2026. Auftrag: „Bitte dauerhaft auf Highend-Level einer
Profi-Agentur beheben.“ Lokale Umsetzung auf dem Arbeitsbranch
`arena/653c2eae-franksfinanzcheck-blog`; Freigabe über Pull Request
(„Closes #823“). Keine Veröffentlichung, keine redaktionelle Freigabe und
kein Prüfsiegel vorgenommen – beide Artikel bleiben `draft: true`.

## Ausgangslage

Issue #823 meldete 7 offene fachliche Befunde aus dem Faktenfrische-Lauf vom
20.10.2026, 09:37 UTC. Beide betroffenen Seiten standen zur **Erstrecherche**
an; die Maschine hatte vertragsgemäß nur `faktencheck` und `quellen` gesetzt –
den Text berührt sie nie (KI-Redaktions-Statut). Die Textarbeit ist genau
diese hier. Der dritte Lauf des Tages („Urlaubskasse clever aufbessern“) hatte
0 Befunde und bleibt unberührt.

| Seite | Befunde | GEO-Reife beim Lauf | GEO-Reife jetzt |
|---|---|---|---|
| Herbst-Check: Strom, Versicherung, Konto und Internet (15.10.) | 4 | 33 % (2/6) | **100 % (6/6)** |
| DNS-Server ändern für schnelleres Internet (16.10.) | 3 | 33 % (2/6) | **100 % (6/6)** |

Gemessen mit der Maschinenlogik selbst (`geo_reife()` aus
`scripts/faktenfrische.py`, unveränderter Prüfcode). Die 33 % des Laufs waren
der Stand VOR dem automatischen Frontmatter-Eintrag; nach dem Lauf standen
beide bei 4/6 – offen waren Kurzantwort-Box sowie je ein Kriterium
(Tabelle bzw. konkrete Euro-Zahlen). Beides ist jetzt redaktionell erfüllt.

## Befund für Befund: was geändert wurde

### Herbst-Check: Strom, Versicherung, Konto und Internet (B1–B4)

1. **veraltet – „Preise für Neukunden stark nach unten“.** Die unbelegte
   Trendbehauptung ist ersetzt durch die amtliche Einordnung: Die
   Verbraucherpreise für Energie sind laut Statistischem Bundesamt zuletzt um
   **14,9 % gestiegen** (Q1, destatis). Ein „Preisrutsch für Neukunden“ wird
   ausdrücklich als nicht ableitbar benannt; der Abstand zum eigenen Tarif ist
   Einzelfall und gehört in den konkreten Vergleich. Dieselbe Zahl steht jetzt
   auch in der Kurzantwort-Box.
2. **luecke – 420-€-Stromersparnis ohne Beleg.** Das Rechenbeispiel ist jetzt
   eine **gekennzeichnete Modellrechnung**: „Die Werte in dieser Tabelle sind
   frei gewählte Annahmen. Sie sind keine Marktdaten, sondern zeigen nur den
   Rechenweg.“ Die Rechnung steht als extrahierbare Tabelle (3.500 kWh ×
   0,42 = 1.470 €; × 0,30 = 1.050 €; Differenz 420 €) und wird von der neuen
   Regression Zelle für Zelle nachgerechnet. Dazu die belegfreie, aber
   arithmetiche Faustregel: 1 Cent Preisabstand = 35 €/Jahr bei 3.500 kWh –
   mit dem ausdrücklichen Verweis, dass reale Abstände nur der Angebotsvergleich
   mit den eigenen Verbrauchsdaten zeigt.
3. **luecke – 9,90-€-Kontogebühr / >1.300-€-Ersparnis ohne Quelle.** Ebenso
   zur gekennzeichneten Modellrechnung umgebaut (9,90 × 12 = 118,80 €;
   + 15 € Karte = 133,80 €/Jahr; × 10 = **1.338 €** – die alte
   „mehr als 1.300 €“-Prosa ist durch den exakt nachgerechneten Tabellenwert
   ersetzt). Echte Gebühren verweist der Text jetzt auf das **Preisverzeichnis
   der Bank**; „kostenlos“-Konten bleiben an Bedingungen (Mindest-Geldeingang,
   Kartengebühren) geknüpft.
4. **luecke – „nach 24 Monaten massiv teurer“ ohne Quelle.** Die
   Marktpauschale („Die Vertragslaufzeit ist meist 24 Monate, danach kann der
   Preis massiv steigen“) ist ersetzt durch **Vertragsmechanik statt
   Marktbehauptung**: Was der Anschluss nach der ersten Laufzeit kostet,
   regelt der eigene Vertrag; manche Tarife verteuern sich nach der Aktion,
   andere laufen gleich weiter. Prüfauftrag: Laufzeitende + Folgedatum.
   Dieselbe Fassung steht in der dritten Faustregel. Nebensatz: „zu Fragen“ →
   „zu fragen“ (Grammatik).

### DNS-Server ändern für schnelleres Internet (B5–B7)

5. **luecke – Bundesnetzagentur-Rahmen fehlte.** Neuer Abschnitt **„Aufsicht
   und Regeln: die Bundesnetzagentur“**: Telekommunikation steht unter der
   Aufsicht der Behörde (Q1); Privatnutzer dürfen den DNS-Server frei wählen
   und brauchen keine Erlaubnis; für Unternehmen, die
   Telekommunikationsdienste anbieten, gelten regulatorische Pflichten
   (Unternehmenspflichten, Breitbandversorgung) – wer einen eigenen DNS-Dienst
   für andere betreiben will, prüft die Vorgaben vorher.
6. **praezision – „spürbar schneller“ ohne Hardware-Grenzen.** Das
   Turbo-Versprechen der Einleitung („läuft dein Netz spürbar schneller“) ist
   ersetzt durch die Mechanismus-Trennung: Neuer Abschnitt **„Was DNS
   leistet – und was nicht“** – DNS beschleunigt nur die Namensauflösung,
   nicht den Datenfluss; Tarif, Leitung, Router und WLAN setzen die
   Obergrenze. Als Beleganker steht der heise-Test der neuen Fritzbox mit
   Wi-Fi 7 (Q2) im Text: Hardware-Kompromisse entscheiden sich im Gerät,
   nicht im DNS-Eintrag. FAQ 1 ist auf die eigene Rechnung zurückgebunden
   („Sekunden bis Minuten pro Monat, nicht pro Minute“ – vorher widersprach
   die FAQ den Rechenbeispielen des Artikels), Gaming/Streaming-Passagen
   sind auf den Verbindungsaufbau präzisiert, „neues Tempo“ im
   Router-Abschnitt auf „den eingestellten DNS-Server“.
7. **praezision – „Cloudflare oft die beste Wahl für hohes Tempo“ ohne
   Daten.** Das Pauschal-Ranking ist ersatzlos gestrichen (ebenso „meist die
   schwächste Lösung“ für ISP-DNS und „extrem fix“ im 4K-Check). Neu:
   „Eine allgemeingültige Rangliste gibt es nicht“ + **Mess-Empfehlung**
   (nslookup, namebench, eigene Werte dokumentieren). Die Tabellenzelle
   „schnell, datenschutzorientiert“ ist auf „großes weltweites Netz, wirbt
   mit Datenschutz“ umgestellt; die 24-Stunden-Löschzusage steht jetzt als
   Anbieter-Angabe („Cloudflare **gibt an** …“). Die 20/50-ms-Schwellen sind
   als Faustregel-Orientierung gerahmt, nicht als Standard.

## Zusätzlich behoben (Premium-Umfeld der Befunde)

- **Beide Artikel:** `kurzantwort` im Frontmatter ergänzt (Kurzantwort-Box,
  GEO/AI-Overviews) und `lastmod: 2026-10-24` gesetzt – echte inhaltliche
  Überarbeitung, keine Frische-Inflation; `faktencheck: 2026-10-20` bleibt
  unangetastet (den Stamp setzt nur ein echter Recherchelauf).
  `redaktionelle_pruefung.aenderungsgrund` dokumentiert die Korrektur zu #823;
  Status bleibt `ausstehend` (kein Siegel).
- **Herbst-Check:** Die description trug ein Maschinen-Klebe
  („Vertrags-Check im Herbst: Strom: Im Herbst …“) – ersetzt durch einen
  sauberen Satz im SEO-Korridor (155 Zeichen, ein Doppelpunkt). Stand-Zeile
  ehrlich auf 24.10.2026. Intro-Absatz mit 7 Sätzen geteilt (R5-ABSATZ-HART).
  FAQ „die meisten Anbieter passen ihre Preise in diesem Rhythmus an“ →
  „Preise, Tarife und Fristen ändern sich laufend“.
- **DNS-Artikel:** Sechs R5-ABSATZ-HART-Absätze (bis zu 11 Sätze) geteilt,
  Template-Intro „In diesem Ratgeber“ entfernt (R7-INTRO-FORMEL),
  CHECK24-Satz im Fazit entwirrt (DNS-Server vergleicht man nicht auf einem
  Tarifportal – der Affiliate-CTA bleibt unverändert), **interne Verlinkung
  von 0 auf 2** gehoben (WLAN-verbessern + DSL-Vergleich; der Entwurf war
  link-unterversorgt, MIN_LINKS=2), Premium-FAQ „sehr sicher/schützen besser“
  auf Technik + Restrisiko (Anbieter sieht die Anfragen) präzisiert,
  Rechenbeispiele als „frei gewählte Annahmen, keine Messwerte“ gekennzeichnet
  und um die Cache-Einordnung ergänzt (realer Gewinn meist kleiner),
  macOS-Weg mit Versions-Vorbehalt, „0 Euro“/„2 bis 5 Euro“ als konkrete
  Zahlen (GEO-Zitierfähigkeit) mit Prüf-Hinweis.
- **Prüfanweisung geschärft (`scripts/faktenfrische.py`, SYSTEM_PROMPT
  Regel 9):** Die fünf Befund-Klassen aus #823 sind jetzt ausdrücklicher
  Prüfungsauftrag der KI-Fachprüfung – (a) Preis-Trends/Markt-Pauschalen ohne
  Fundstelle, (b) Zahlen in Marktfakten-Positur ohne Beleg ODER
  Modell-Kennzeichnung, (c) fehlender Regulierungsrahmen, den Fundstellen
  nahelegen, (d) Leistungsversprechen ohne Mechanismus/Systemgrenzen
  („Namensauflösung ist nicht Bandbreite“), (e) Anbieter-Rankings ohne
  messbare Daten. `--selftest`: 23/23 grün, Anti-Halluzinations-Vertrag
  (ST3), URL-Allowlist und Schreibgrenzen unverändert.

## Dauerhafte Absicherung

### 1. Neue Regression: `scripts/tests/test_faktenfrische_823.py` (13 Tests)

Bedeutungs-Invarianten statt Exaktzeichenketten (Lehre aus #763):

- **B1–B7 verneinungstolerant:** Die sieben Fehlbehauptungen dürfen
  behauptend nie zurück – Leserfragen, Dämpfungen („kann“, „oft“) und
  Verneinungen bleiben erlaubt. Positive Anker müssen stehen: 14,9 % mit
  destatis-Zuordnung, „frei gewählt“/„keine Marktdaten“, Preisverzeichnis,
  Vertragsbedingungen, Bundesnetzagentur-Aufsicht im Fließtext (Überschrift
  allein zählt nicht), Aufsichts-Leugnung ist verboten, Namensauflösung ≠
  Bandbreite + heise-Anker, „beste Wahl“/„schwächste Lösung“ nie wieder,
  Mess-Empfehlung als Ranking-Ersatz.
- **Arithmetik wird nachgerechnet, nicht abgetippt:** Beide Modelltabellen
  des Herbst-Checks werden Zelle für Zelle ausgewertet (deutsche
  Zahlenschreibweise, ×/−/+-Operatoren, Tausenderpunkte) – 3.500 × 0,42 =
  1.470, 1.470 − 1.050 = 420, 9,90 × 12 = 118,80, +15 = 133,80, ×10 = 1.338,
  Cent-Faustregel 3.500 × 0,01 = 35. Die ms-Modelle des DNS-Artikels müssen
  untereinander stimmen (120×2×50 = 12.000 ms = 12 s; 2.000×10 = 20.000;
  ×50 = 1.000.000 ms = 1.000 s ≈ 17 min).
- **Kennzeichnungs-Pflicht mit Abstandsprüfung:** Modellzahlen ohne
  „frei gewählt“ im Prosa-Absatz VOR der Tabelle machen rot – ein „im Modell“
  in der Zeilenbeschriftung allein reicht nicht (Sabotage-Lehre S3).
- **Metadaten-Korridor:** lastmod ≥ 24.10.2026, faktencheck ≥ 20.10.2026
  (kein Zurückdatieren; Obergrenze bewusst offen – echte Folgeläufe dürfen
  stempeln), description 70–165 ohne Doppel-Doppelpunkt, sichtbare
  Stand-Zeile, GEO-Reife 6/6 je Artikel.
- **Dossier-Bindung (Anti-Halluzinations-Parität für Handarbeit):** Jede URL
  im Frontmatter muss wörtlich im Recherche-Dossier des 20.10.-Laufs stehen;
  das heise-Quellendatum muss zum Dossier-Datum passen.
- **Gate-Parität:** Score ≥ 75, Flesch ≥ 60, Zeichenkorridor 10.000–22.000,
  harte Textverständnis-Regeln (R2–R17 inkl. R16) und interne Links ≥ 2 –
  genau die Gates, an denen ein geheilter Entwurf sonst im Hold verrottet.
- **Queue-Hygiene:** `faktenfrische_queue.json` darf die zwei Slugs nicht als
  offen führen – slug-kern-basiert, überlebt Umbenennungen.
- **Systemprompt-Vertrag:** Regel 9 muss die #823-Befundklassen enthalten.

**Sabotage-Nachweis statt Vertrauenssache:** 17 wiederinjizierte
Fehlvarianten (alle 7 Befunde als Text-Rückfall, Kennzeichnungs-Entzug bei
beiden Modellrechnungen, gedrehte/verzehnfachte Ergebniswerte,
Cent-Faustregel ×10, Aufsicht-Leugnung, Aufsicht-Abschnitt gelöscht,
Mechanismus-Abschnitt gelöscht, Turbo-Umkehr, Ranking-Rückfall, nacktes
„schnell“ in der Tabellenzelle, kurzantwort entfernt, lastmod
zurückdatiert) – **16/17 gefangen**; die eine Ausnahme (S11: Entfernen EINES
von mehreren redundanten Grenz-Sätzen) lässt die Heilung sachlich intact und
ist kein Rückfall. Zwei Erstentwurfs-Lücken (S3 Kennzeichnung nur über
Tabellenbeschriftung, S6 Aufsicht nur noch in Überschrift/Restsatz) sind
nachgeschärft und jetzt dicht.

### 2. `scripts/tests/test_faktenfrische_763.py` geheilt (Suite war rot)

Das #763-Modul war am 24.10. **auf main rot** (10 Fehler): Die Kadenz hatte
den Reiseartikel zur Veröffentlichung umdatiert
(`2026-10-14-…` → `2026-10-24-…`) – ein Test, der am Datumspräfix klebt,
bricht bei jeder harmlosen Umbenennung (genau die #763-Lehre). Heilung:

- `resolve()`: Slug-Auflösung über den Namens-Kern, exakter Treffer gewinnt;
- Summenformel-Toleranz gegen schmale Leerzeichen (U+202F/U+00A0) der
  Euro-Heiler – Bedeutung vor Schreibweise;
- Haus-CTA-Ausnahme: „Spar-Tipp zwischendurch“-Blockzitate sind ein von der
  `affiliate_integrity_gate` (AI1–AI5, `CTA_MARKERS`) bewachtes Hausmuster –
  die Prosa-Offenlegungspflicht gilt weiter für jeden anderen /go/-Absatz,
  und der Global-Check (Transparenz vor dem ersten /go/-Link) bleibt scharf.

Ergebnis: 16/16 grün, ohne dass eine Sach-Invariante aufgegeben wurde.

### 3. `scripts/tests/test_newsletter_digest.py` an F-08 angepasst

Zweiter Rot-Fund auf main (seit der Sicherheits-Härtung WF-E813 #815):
`worker_liste()` verlangt jetzt einen **getrennten Schreibschlüssel**
(fail-closed, F-08) – die alten Tests kannten nur den Leseweg und liefen in
den Abbruch; dadurch waren `unittest discover` UND die Uhr-Probe in **jedem**
aktuellen PR rot (ein roter Stamm schützt nichts). Die Tests prüfen den
Vertrag jetzt, wie er gilt: Export nur mit Schreibschlüssel
(`mit_token=1`, Schlüssel-Assert), plus neue Rückfall-Probe: Schreibschlüssel
fehlt / ist leer / ist identisch mit dem Leseschlüssel / Leseschlüssel fehlt →
`RuntimeError`, und der Export darf gar nicht erst aufgerufen werden.
27/27 grün.

## Nachweise (lokal, 24.10.2026)

- `.venv/bin/python -m unittest discover -s scripts/tests`: **3.587 Tests, OK**
  (27 skips – Live-Bestand-Abhängige; vorher auf main: 2 Fehler).
- `scripts/selftest_clock.py --trap-discover scripts/tests --offset 97`:
  **grün** („bleibt unter einer um 97 Tage vorgestellten Uhr grün“) –
  Zeitbomben-Schutz: alle neuen Tests arbeiten mit festen Daten, nie mit der
  Wanduhr.
- Zielmodule: `test_faktenfrische_823` **13/13**, `test_faktenfrische_763`
  **16/16**, `test_publish_gate_faktenfrische` **5/5**,
  `test_newsletter_digest` **27/27**.
- `scripts/faktenfrische.py --selftest`: **23/23 grün** (inkl. ST3
  Anti-Halluzination).
- `geo_reife()` je Artikel: **6/6 (100 %)** für beide Seiten (beim Lauf
  33 %); gemessen gegen unveränderten Prüfcode, `--offline` je Artikel:
  GEO-Reife 100 %.
- Lesbarkeit/Gates je Entwurf: Herbst-Check **Score 95, Flesch 60,8**
  (vorher 95/60,0 – Marge verbreitert), DNS **Score 95, Flesch 68,9**;
  Zeichenkorridor 13.225 bzw. 14.708 (10.000–22.000); harte
  Textverständnis-Regeln: **0 Funde** (vorher: 1× bzw. 6× R5-ABSATZ-HART,
  1× R7-INTRO-FORMEL, interim 1× R15-PHRASEN-DOPPEL – alle geheilt);
  interne Links 2 bzw. 2 (DNS vorher 0 = unterversorgt).
- `fm_boundary_guard.py --check`: **131 Dateien sauber** (neue
  Frontmatter-Felder YAML-konform, kein Doppelschlüssel).
- Engine-/Kadenz-Selbsttests: `engine_generate`, `reserve_pool`,
  `cadence_guard`, `fm_boundary_guard`, `social_studio` – **alle grün**.
- Bestandsprüfungen: `zeit_rechtschreibung.py --offline` **66 Artikel,
  0 Funde**; `seo_audit.py` **66 Artikel, 0 Probleme**;
  `editorial_review_gate.py --published --strict` **0 blockiert**
  (Live-Bestand unberührt – beide Seiten sind Entwürfe).
- `check_uniqueness.py`: Ergebnis **identisch zu main** (208/190/1, nicht
  blockierend laut content-engine-V2); die Redaktion hat **keine** neue
  Überlappung eingeführt (Diff der Nicht-Live-Paare: leer). Das bekannte
  Paar DNS-Entwurf ↔ DNS-Live-Artikel (08/26) besteht seit der Erstanlage –
  es sind die IP-Adress-Zeilen der Anbieter-Tabelle (faktisch zwingend
  identisch) plus Standard-Formulierungen; die Zusammenführungs-Entscheidung
  gehört in den Publish-Pfad der Kadenz, nicht in #823.
- Sabotage-Suite: **16/17** echte Rückfall-Varianten gefangen (Details oben);
  Artikel nach jeder Probe byte-identisch wiederhergestellt (Diff gegen
  Backup: leer).
- Maschineneigene Lauf-Dateien (`data/faktenfrische_queue.json`, Historie,
  Reports) nach Offline-Probeläufen **zurückgesetzt** – sie gehören dem
  nächsten echten CI-Lauf mit Netz (Bestand: Di + Do).
- `git diff --check`: sauber.

## Ehrliche Grenzen

- **Keine neue Live-Recherche:** destatis.de, bundesnetzagentur.de und
  heise.de sind in dieser Arbeitsumgebung nicht abrufbar. Alle Sachaussagen
  stammen aus dem dokumentierten Befunden/Dossier des 20.10.-Laufs oder sind
  als frei gewählte Modellannahmen gekennzeichnet. Keine neue URL erfunden,
  keine Affiliate-Quelle belegfähig gemacht; die Dossier-Bindung ist jetzt
  sogar testbewehrt.
- **Kein Hugo-Build lokal** (Hugo nicht installiert): YAML-/Markdown-Vertrag
  ist über `fm_boundary_guard`, den Faktenfrische-Parser und die
  Regressionstests geprüft; den echten Produktionsbuild fährt die CI
  (`publication-reliability-tests.yml`, Hugo 0.164.0).
- **Kein Prüfsiegel, keine Freigabe:** Der Herbst-Check trägt weiterhin
  `risikoklasse: hoch` mit `status: ausstehend`; die reguläre redaktionelle
  Prüfung (YMYL) bleibt erforderlich. Die Heilung der Befunde ist keine
  vorgetäuschte Veröffentlichungsreife.
- **Zahlendreher-Schutz ist kein Wahrheitsbeweis:** Die Regression prüft
  Rechnung, Kennzeichnung und Abwesenheit der gemeldeten Fehlbehauptungen –
  ob z. B. 14,9 % auch morgen noch den destatis-Daten entspricht, wacht der
  nächste Fälligkeitslauf (saisonal: 30 Tage → ~19.11.2026; Standard: 90 Tage
  → ~18.01.2027) mit frischer Recherche.

## Dauerhaftigkeit

Die Korrekturen sind im Text verankert, nicht als Overlays: falsche
Kernsätze ersetzt (nicht annotiert), Modellrechnungen in extrahierbare
Tabellen mit Kennzeichnung überführt, Mechanismus-Grenzen als eigener
Abschnitt, Regulierungsrahmen als eigener Abschnitt mit Beleganker. Wer
künftig eine der sieben Fehlbehauptungen zurückschreibt, eine Modellzahl
verdreht, die Kennzeichnung entfernt oder einen Entwurf unter die Gates
drückt, bekommt Rot in `unittest discover` – in jedem PR, an jedem Kalendertag
(Uhr-Probe). Und dieselben Befund-Klassen, die #823 gemeldet hat, prüft die
KI-Fachprüfung seit Regel 9 aktiv mit – beim nächsten Artikel, nicht erst
beim nächsten Bestand.
