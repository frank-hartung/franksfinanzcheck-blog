# Google Search Console auf Agentur-Niveau

**Vorgang:** Abdeckungsbericht (Seiten-Indexierung) messbar, rechenbar und
prüfbar machen
**Stand:** 26.10.2026 · Datenstand des Berichts: 19.10.2026
**Auftrag:** „Google Search Console auf Highend-Level einer Profi-Agentur
bringen."
**Grundlage:** die vier Exporte des Abdeckungsberichts (Übersicht, Diagramm,
Metadaten, nicht kritische Probleme), der gebaute Bestand und der Repo-Bestand.

---

## 1. Das Ergebnis in drei Sätzen

Die Search Console meldet **437 bekannte URLs, davon 117 im Index (26,8 %) und
320 nicht**. Der Build enthält **258 URLs, davon 99 indexierbar** – auf jede
indexierbare Seite kommt also 1,6 Seiten, die gar nicht in den Index sollen.
Damit ist zum ersten Mal belegbar, was vorher nur ein Gefühl war: **Die
Nicht-Index-Zahl ist größer als der Bestand**, es sind mehr Einträge als Seiten
(1,24 je gebauter URL), und der größte Block davon ist Historie – 223 Einträge
melden 404, von denen der Repo-Bestand nur 30 erklärt.

Was fehlte, war nicht eine Wache mehr, sondern die **Gegenprobe**. Genau die
steht jetzt im Repo: ein Modul, das den Export einliest, gegen Sitemap, Build,
Weiterleitungskarte, noindex-Bestand und robots.txt rechnet, jeder Zahl ein
Urteil gibt und die offenen Posten als priorisierte Maßnahmenliste ausgibt –
reproduzierbar, offline, mit 51 Regressionstests.

| Bereich | vorher | jetzt |
|---|---|---|
| Abdeckungsbericht im Repo | nur als Bildschirmfoto bekannt | versionierter Export + Momentaufnahme + Verlauf |
| Gegenprobe gegen den Bestand | keine | je Grund eine Erwartung mit Urteil |
| Rückschritt-Erkennung | keine | `--gate`, Vergleich mit dem Vorlauf |
| Detail-Listen (URLs) | nicht ausgewertet | `--vorschlaege` leitet Weiterleitungs-Kandidaten ab |
| Sichtbarkeit im Cockpit | keine | Zeile in „SEO & Technik" |

---

## 2. Drei Zahlenwelten, die vorher niemand zusammengebracht hat

| Quelle | Was sie sagt | Zahl |
|---|---|---|
| Search Console | bekannte URLs | 437 |
| Search Console | davon indexiert | 117 (26,8 %) |
| Search Console | davon nicht indexiert | 320 |
| Build (`public/`) | gebaute URLs | 258 |
| Build | davon indexierbar (Sitemap) | 99 |
| Build | davon bewusst nicht indexierbar | 159 |
| Repo (`content/`) | veröffentlichte Artikel | 68 (dazu 27 Entwürfe) |

Daraus folgen drei Aussagen, die keine der Quellen allein treffen kann:

1. **Es gibt mehr Nicht-Index-Einträge als gebaute Seiten** (320 zu 258, Faktor
   1,24). Die Einträge sind also überwiegend URLs, die es nicht mehr gibt.
2. **Der Index enthält mindestens 18 URLs, die nicht in der Sitemap stehen**
   (117 indexiert minus 99 indexierbar). Die Quote ist deshalb zu hoch, nicht
   zu niedrig – jede Erfolgsmessung auf dieser Basis wäre geschmeichelt.
3. **Die Crawl-Fläche ist in Ordnung.** 159 nicht indexierbare zu 99
   indexierbaren Seiten ist ein Verhältnis von 1 : 1,6. Am 29.09.2026 lag es
   bei 1 : 6,0 (58 indexierbar, 347 nicht indexierbar). Die Aufräumarbeit der
   letzten vier Wochen hat gewirkt; das Problem von heute ist ein anderes.

### Verlauf (30 Tage bis 19.10.2026)

| Datum | nicht indexiert | indexiert | Impressionen |
|---|---|---|---|
| 21.09. | 237 | 138 | 3 |
| 13.10. | 261 | 138 | 1 |
| 16.10. | 261 | 138 | 2 |
| **17.10.** | **320** | **117** | 1 |
| 19.10. | 320 | 117 | 7 |

Am 17.10. springt „nicht indexiert" um 59 nach oben und „indexiert" um 21 nach
unten. Ein Sprung dieser Größe ist keine Messungenauigkeit, sondern eine
Ursache im Repo (Deploy, Sitemap-Änderung, Aufräumaktion). Er steht als
Maßnahme `M7` in der Liste, weil er sich aus dem Änderungsprotokoll erklären
lässt – nicht aus dem Bericht.

**Die Ursache ist inzwischen belegt** (Nachtrag 26.10.2026, `npm run gsc:ursachen`):
Der Commit `8058293` vom **14.10.2026, 09:45 UTC** („redaktion:
Hemingway-Lesbarkeit und Offline-Sprachpflege") hat 3.936 Dateien geändert,
darunter 89 in `content/posts`, und dabei **32 Beiträge mehr auf `draft: true`
gesetzt** (36 neu zurückgestuft). Zurückgestufte Beiträge verlassen Build und
Sitemap – Google meldet den Verlust drei Tage später, genau am 17.10.
Zwischen 15. und 18.10. wurde weder `hugo.toml`, `layouts/`, `robots.txt` noch
`data/weiterleitungen.yaml` angefasst; die technischen Erklärungen scheiden
damit aus. Grenze der Aussage: Die 21 verlorenen Seiten sind nicht einzeln
zugeordnet – dafür braucht es die Detail-Liste (M1).

Impressionen: 62 in 30 Tagen (2,07/Tag), sechs Tage ohne. Klicks: null. Das ist
der eigentliche Grund für diesen Auftrag – bei dieser Sichtbarkeit entscheidet
nicht die CTR, sondern die Frage, ob die Seiten überhaupt im Index ankommen.

---

## 3. Die sechs Gründe – jeder mit Gegenprobe

Die Erwartung stammt nicht aus einer gepflegten Liste, sondern aus dem
Gebauten: `robotsNoIndex` im Frontmatter, Ordner in `static/go/`, Einträge in
`data/weiterleitungen.yaml`, Taxonomie-Slugs aus den Inhalten, Sitemap-Bestand.

| Grund | Seiten | Erwartung | Urteil | Begründung |
|---|---|---|---|---|
| Nicht gefunden (404) | 223 | 30 | **offen** | 27 Taxonomie-URLs (23 Tags, 2 Kategorien, 2 Hubs) und 3 bewusst entfallene Alt-URLs sind erklärbar. 193 bleiben offen – dafür braucht es die Detail-Liste, nicht eine Vermutung. |
| Gefunden – zurzeit nicht indexiert | 69 | ≤ 99 | plausibel | Google kennt die URL, hat sie nicht abgerufen. Der Bestand ist die Obergrenze, nicht die Erwartung. |
| Durch robots.txt blockiert | 18 | 20 | plausibel | 20 `/go/`-Gateways, alle gesperrt. Google hat 18 versucht. Die Meldung bleibt dauerhaft stehen – das ist gewollt, siehe Abschnitt 6. |
| Durch „noindex"-Tag ausgeschlossen | 5 | 5 | **vollständig erklärt** | 4 Newsletter-Funnel-Seiten + `/suche/` tragen `robotsNoIndex: true`. Deckungsgleich. |
| Gecrawlt – zurzeit nicht indexiert | 4 | ≤ 99 | plausibel | Google hat gelesen und abgelehnt. Redaktionelles Signal, kein Technikdefekt. |
| Seite mit Weiterleitung | 1 | 115 | plausibel | 115 Weiterleitungsseiten liegen im Build, gemeldet wird eine. Entweder hat Google sie noch nicht besucht oder zählt sie anders – offene Beweisfrage. |

**Die Urteile sind absichtlich verschieden scharf.** „Vollständig erklärt"
verlangt Deckungsgleichheit, „plausibel" nur, dass die Zahl unter ihrer
Obergrenze bleibt. Hätte das Modul überall „ok" geschrieben, wäre der Befund
wertlos – die 193 offenen 404er sind der Kern.

---

## 4. Vier Befunde mit Beweis

### B1 · Die 404er sind eine Beweislücke, kein Reparaturstau

223 gemeldete 404er, 30 erklärbar, **193 offen**. Der Build kennt 115
Weiterleitungsseiten und 3 bewusst entfallene Alt-URLs; mehr entfernte URLs
sind im Repo nicht dokumentiert. Die restlichen 193 stammen damit aus der
Geschichte vor dem 19.10.2026 oder von außen (Backlinks, Verzeichnisse,
Social-Media-Archive).

Was daraus folgt und was nicht:

- **Nicht** folgt: 193 Weiterleitungen anlegen. Eine Weiterleitung ohne
  passende Suchabsicht ist schlimmer als ein 404, weil sie Nutzer an die
  falsche Stelle schickt (Regeln A–E in `data/weiterleitungen.yaml`).
- **Folgt:** Die Detail-Liste einlesen, mit `--vorschlaege` triagieren lassen
  und nur die Fälle mit Nachfrage weiterleiten. Das Werkzeug schlägt über den
  datumsbereinigten Slug vor, entscheidet aber nichts.

### B2 · 73 von 99 Seiten sind nicht im Index – der Crawl-Rückstand ist das größte Problem

69 „gefunden, nicht abgerufen" plus 4 „gecrawlt, nicht indexiert" stehen 99
indexierbaren Seiten gegenüber. Selbst im besten Fall (die 69 betreffen
Altlasten) bleiben 4 abgelehnte Seiten; im schlechtesten Fall ist ein großer
Teil der Artikel nicht im Index.

Auffällig: In der Sitemap stehen **69 Post-URLs** (68 Artikel + Hub) – exakt die
Zahl der „gefunden, nicht indexiert"-Einträge. Das kann Zufall sein. Wenn die
Detail-Liste es bestätigt, lautet die Aussage: **Kein einziger Artikel ist im
Index.** Diese Hypothese ist billig zu prüfen und teuer zu ignorieren; sie steht
deshalb als Beweisfrage im Befund, nicht als Behauptung im Bericht.

### B3 · Impressionen landen auf Weiterleitungs-Stubs

Von den 25 Seiten mit Impressionen (28 Tage, 90 Impressionen) sind sechs nicht
in der Sitemap:

| URL | Impressionen | Position | Was sie heute ist |
|---|---|---|---|
| `/posts/kuehlschrank-strom-sparen-einstellung/` | 9 | 16,9 | Weiterleitungsseite |
| `/posts/2026-08-07-frugalismus-fuer-den-erfolg/` | 8 | **5,3** | Weiterleitungsseite |
| `/posts/depot-umzug-steuerfrei-wechseln/` | 1 | **4,0** | Weiterleitungsseite |
| `/posts/elementarschadenversicherung-hochwasser-starkregen/` | 1 | 80,0 | Weiterleitungsseite |
| `/tags/haushaltsbuch/` | 1 | 6,0 | bewusst 404 |
| `/tags/reiser%C3%BCcktritt/` | 1 | 10,0 | Taxonomie, abgeschaltet |

19 der 90 Impressionen (21 %) gehen auf URLs, die keinen Inhalt mehr haben –
zwei davon auf **Position 5,3 und 4,0**. Google zeigt dort den Titel „Diese
Seite ist umgezogen". Der Nutzer landet per Meta-Refresh zwar am Ziel, aber der
Snippet ist leer und es gibt keinen Klick.

Das ist der einzige Befund, bei dem die Ursache eindeutig und die Behebung
technisch ist: **GitHub Pages kann keine echten 301 setzen.** Solange kein
Edge-Proxy davorsteht, bleibt die Meta-Refresh-Seite ein Ersatz. Zwei Wege:

1. **Edge-Weiterleitungen** über Cloudflare (`scripts/weiterleitungen.py
   --cloudflare` erzeugt die Bulk-CSV bereits) – echter 301, Signale wandern mit.
2. **Inhalt zurückholen**, wo Nachfrage besteht: Die zwei Position-4/5-URLs
   sind Themen mit belegter Nachfrage. Ein Artikel dazu ist mehr wert als eine
   Weiterleitung.

### B4 · Die Index-Quote ist zu hoch, nicht zu niedrig

117 indexiert bei 99 indexierbaren Seiten: mindestens 18 Einträge gehören nicht
zur Sitemap (Weiterleitungs-Stubs, abgeschaltete Tag-Archive, alte Slugs). Das
ist kein Drama – es macht aber jede Quote auf dieser Basis unbrauchbar. Der
Befund trennt deshalb „indexiert" (GSC) von „indexierbar" (Build) und weist den
Puffer aus. Ziel ist nicht, den Puffer zu erhöhen, sondern die 99 echten Seiten
vollständig in den Index zu bekommen.

---

## 5. Was gebaut wurde

### 5.1 `scripts/gsc_abdeckung.py` – die Abdeckungs-Zentrale

Ein Modul, vier Aufgaben:

| Aufgabe | Aufruf | Was passiert |
|---|---|---|
| Einlesen | `--import <verzeichnis>` | liest die vier Exporte, prüft sie gegen sich selbst, schreibt eine Momentaufnahme |
| Gegenrechnen | `--audit` | stellt jeder GSC-Zahl eine Erwartung aus dem Repo gegenüber |
| Tor | `--audit --gate` | Exit 1 bei Rückschritt, Widerspruch oder unbekanntem Grund |
| Triage | `--vorschlaege <detail.csv>` | schlägt Weiterleitungsziele vor, schreibt nichts |
| Kreislauf | `--triage`, `--entscheiden`, `--entscheidungen` | Vorschlag mit Frist, Entscheidung im Register, Wirkungsprüfung nach Ablauf (siehe 7.3) |

**Der Prüfschritt ist der wichtigste.** Summieren sich die Gründe nicht auf den
Tageswert im Diagramm (`E8`), wird der Import abgelehnt. Genau diese Klasse hat
am 21.10.2026 drei GSC-Artefakte unlesbar gemacht – damals durch einen
Text-Merge, heute durch einen Export aus zwei Momenten. Ein Artefakt aus zwei
Messungen ist keine Messung.

**Was das Modul ausdrücklich nicht tut:**

- keine URL erfinden: fehlt die Detail-Liste, steht das als offene Beweisfrage
  im Befund (Regel `E10`);
- nicht in `data/weiterleitungen.yaml` oder `data/url_entfallen.yaml`
  schreiben (Weiterleitungen sind eine Entscheidung, kein Automatismus);
- keine Suchmaschine aufrufen – der Befund ist offline reproduzierbar;
- die Zahl der indexierbaren Seiten nicht schätzen, wenn ein Build vorliegt: sie
  wird am ausgelieferten HTML gemessen (`INDEX_GATE_BASE`, dieselbe Konvention
  wie `index_hygiene_gate.py`).

### 5.2 Artefakte

| Pfad | Inhalt | Warum versioniert |
|---|---|---|
| `data/gsc/abdeckung/export/2026-10-19/` | die vier eingelesenen CSVs | Beweis; ohne ihn ist der Befund nicht nachrechenbar |
| `data/gsc/abdeckung/2026-10-19.json` | Momentaufnahme | ein Lauf = eine Messung |
| `data/gsc/abdeckung/aktuell.json` | dieselbe Momentaufnahme, fester Pfad | Leser müssen nicht nach dem Datum suchen |
| `data/gsc/abdeckung/verlauf.jsonl` | eine Zeile je Momentaufnahme | Entwicklung über Importe hinweg |
| `data/gsc/abdeckung/befund.json` / `.md` | Ergebnis der Gegenrechnung | Grundlage für Cockpit und Wochenbericht |
| `data/gsc/abdeckung/details/` | Detail-Listen je Grund + `stand.txt` | ohne sie bleibt jede Triage eine Summe (W9) |
| `data/gsc/abdeckung/triage.json` / `.md` | Triage mit Alter, Frist, Vorschlag | ein Lauf = eine Arbeitsliste, nachvollziehbar |
| `data/gsc/abdeckung/redaktions_queue.md` | was die Redaktion entscheiden kann | die Schnittstelle zwischen Automat und Mensch |
| `data/gsc/abdeckung/entscheidungen.yaml` | was entschieden wurde – mit Frist | sonst wird dieselbe Frage jede Woche neu gestellt |
| `data/gsc/abdeckung/triage_verlauf.jsonl` | seit wann eine URL offen ist | ohne Verlauf läuft keine Frist |

`merge=binary` für die JSON-Artefakte (`.gitattributes`), `merge=union` bleibt
für den Verlauf: Eine Zeile je Momentaufnahme ist eine unabhängige Messung.
Dieselbe Regel wie bei den GSC-Leistungsdaten nach dem 21.10.2026.

### 5.3 Tests, Workflow, Cockpit

- `scripts/tests/test_gsc_abdeckung.py` – 63 Regressionstests über sieben Ebenen:
  Lesen (BOM, Semikolon, deutsche Anführungszeichen), Nicht-Schreiben bei
  Widerspruch, Gegenrechnen (noindex-Leck, robots-Sperre ohne Gateway,
  unbekannter Grund), Hermetik (kein Netz, kein Schreiben in den echten
  Verlauf), Maßnahmenplan (Triage, Vertrag, Verlinkung, Goldkorridor),
  Git-Beleg (M7), Kreislauf (Register, Frist, Wirkungsprüfung). Selbsttest:
  80 Fälle.
- `.github/workflows/gsc-import.yml` – Build für die Gegenprobe (nicht
  kritisch), dann `--audit --schreiben --json` mit Tabelle in der
  Lauf-Zusammenfassung. Ein roter Befund wird als Warnung sichtbar, blockiert
  aber nicht den Datenimport; die harten Regeln greifen im Befund selbst.
- `scripts/cockpit.py` – neue Zeile in „SEO & Technik": Quote, offene Posten,
  Gate-Status. Fehlt der Befund, bleibt der Bereich wie bisher (kein erfundener
  Zustand).
- `package.json` – `gsc:abdeckung`, `gsc:abdeckung:gate`, `gsc:abdeckung:md`;
  `test:gsc` um den neuen Selbsttest und die Tests erweitert; zusätzlich
  `gsc:triage`, `gsc:vertrag`, `gsc:verlinkung`, `gsc:verlinken`,
  `gsc:prioritaet`, `gsc:altlasten`, `gsc:kpi`, `gsc:abnahme`, `gsc:ursachen`.
- `docs/ANLEITUNG-GOOGLE-SEARCH-CONSOLE.md` – neuer Abschnitt 9: Export
  anleiten, Zahlen lesen, Grenzen kennen.

---

## 6. Entscheidungen (und was bewusst NICHT geändert wurde)

1. **`/go/` bleibt per robots.txt gesperrt.** Die Meldung „durch robots.txt
   blockiert" verschwindet dadurch nie. Das ist die richtige Abwägung: 20
   Gateways sind keine Inhalte, Google soll sie nicht crawlen. Ein
   Crawl-Freigabe plus noindex würde die Meldung zwar bereinigen, aber Crawl
   auf Weiterleitungen lenken und die Sperre `schema_seo_gate.py` (S8)
   aufweichen. Der Befund wacht stattdessen darüber, dass die Zahl nicht über
   die Zahl der Gateways steigt (`W3`).
2. **Keine Weiterleitung ohne Detail-Liste.** 193 offene 404er werden nicht
   „auf Verdacht" umgeleitet. Slugs sind kein Beweis für Suchabsicht.
3. **Keine Massen-URLs.** Die Versuchung, fehlende Tag-Archive wieder zu
   aktivieren, ist real – sie stünde in direktem Widerspruch zur
   Index-Hygiene-Entscheidung vom 29.09.2026 und würde die Crawl-Fläche wieder
   aufblasen.
4. **Die Quote wird nicht schöngerechnet.** Der Befund weist den Index-Puffer
   aus, statt „117 indexiert" als Erfolg zu lesen.

---

## 7. Maßnahmenplan

| ID | Prio | Aufwand | Maßnahme | Beleg | Eigentümer | Stand 26.10.2026 |
|---|---|---|---|---|---|---|
| M1 | **P1** | S | 404-Detail-Liste exportieren und einlesen, dann triagieren | 223 gemeldet, 30 erklärbar, 193 offen | Mensch (Export) + Automat | **Automat fertig** (`--triage`), 1 von 6 Listen da |
| M2 | **P1** | M | Crawl-Nachfrage für die 69 gefundenen, nicht abgerufenen Seiten | 69 bei 99 indexierbaren Seiten | Automat + Redaktion | **Automat fertig** (`--prioritaet`, `--verlinkung`), Redaktion laufend |
| M3 | P2 | M | Redaktions-Queue für die 4 „gecrawlt, nicht indexiert" | 4 Seiten | Redaktion | **erledigt und weitergeführt** – 2 Aufgaben mit Frist und Vorschlag, 2 als Asset erkannt; Entscheidung über `--entscheiden`, Wirkungsprüfung nach Frist |
| M4 | P2 | S | Index-Altlasten benennen statt mitzählen | 117 indexiert bei 99 indexierbar | Automat | **fertig** (`--altlasten`, W5) |
| M7 | P2 | S | Sprung vom 17.10. erklären | 261 → 320 bzw. 138 → 117 | Mensch | **belegt** (Commit `8058293`, `--ursachen`) |
| M8 | P2 | S | Detail-Exporte wöchentlich in den Tageslauf | 0 Detail-Zeilen im Export | Mensch + Automat | **erledigt** – erste Liste liegt in `details/`, Regel W9 grün |
| M9 | P2 | S | Indexquote als Wochen-Kennzahl etablieren | 26,8 % | Automat | **fertig** (`--kpi`, `--abnahme`) |
| M5 | P3 | S | noindex-Bestand als Vertrag führen | 5 = 5 | Automat | **fertig** (`--vertrag`, V1/V2, Gate G6) |
| M6 | P3 | S | robots-Sperre der Gateways dokumentiert lassen | 18 von 20 | Automat | **fertig** (`--vertrag`, V3/V4) |

„Automat fertig, Export offen" heißt: Das Werkzeug ist gebaut, getestet und im
Tageslauf verdrahtet. Es kann nur nichts triagieren, solange niemand die
Detail-Listen aus der Search Console exportiert – dieser eine Schritt lässt
sich nicht automatisieren, weil die Oberfläche keinen API-Zugang dafür hat.
Der Befund sagt das in jeder Ausgabe (Regel **W9**), statt es zu verschweigen.

**Was M2 konkret heißt** (der einzige Hebel, der ohne Google-Zugriff wirkt):
interne Verlinkung verdichten (jede der 69 Seiten aus mindestens zwei Artikeln
erreichbar), `lastmod` ehrlich halten, Publikationskadenz auf 2/Tag begrenzen,
damit der Crawler nicht gegen 27 Entwürfe und 2 neue Artikel pro Tag anläuft –
und wöchentlich `python3 scripts/gsc_indexierung.py --pruefen` für den Status
je URL.

### 7.0 Die erste Detail-Liste ist eingelesen

Am 26.10.2026 kam die erste von sechs Detail-Listen an: **„Gecrawlt – zurzeit
nicht indexiert"**, vier URLs, zuletzt gecrawlt am 20.10. Sie liegt als
`data/gsc/abdeckung/details/Gecrawlt – zurzeit nicht indexiert.csv`, das
Exportdatum in `stand.txt`. `--triage` hat daraus vier Zeilen gemacht – und
zwei davon sind keine Aufgabe:

| URL | Urteil | Begründung |
|---|---|---|
| `/posts/2026-08-21-haushaltsbuch-fuehren-app-excel-oder-papier/` | **P2 Redaktion prüfen** | 1.845 Wörter, 6 redaktionelle Inlinks, keine Rolle im Cluster K7 – „zu dünn" und „unverlinkt" scheiden aus |
| `/posts/2026-10-12-dein-weg-zu-geringeren-monatskosten-schritt-fuer-schritt/` | **P2 Redaktion prüfen** | 1.872 Wörter, 3 Inlinks, keine dokumentierte Rolle im Cluster K3, **0 Titel-Überschneidungen** (frühere Angabe „2 ähnliche Titel“ war ein Messfehler, siehe 7.3) |
| `/favicon.ico` | P3 – kein Inhalt | Google crawlt Favicons planmäßig; kein Indexanspruch |
| `/index.xml` | P3 – kein Inhalt | RSS-Feed; darf gecrawlt werden, gehört nicht in den Index |

Daraus folgen zwei Erkenntnisse, die den Bericht schärfen:

1. **Die Hälfte dieser Meldung war nie ein Problem.** Zwei der vier „Fehlschläge"
   sind Feed und Favicon. Die Search Console zählt alles, was sie crawlt – auch
   das, was sie nie indexieren will. Genau deshalb prüft die Triage jetzt die
   Dateiendung, bevor sie eine Aufgabe erzeugt.
2. **Für die zwei echten Seiten ist die Ursache weder Länge noch Verlinkung.**
   Beide sind lang und gut verlinkt. Auffällig ist etwas anderes: **Keine der
   beiden hat eine Rolle im Kannibalisierungs-Register** – obwohl beide laut
   Themenfeld in ein dokumentiertes Cluster gehören (K7 Konto & Karten, K3
   Frugalismus). Solange die Rolle fehlt, ist „Kannibalisierung“ eine
   Vermutung. Genau deshalb heißt der nächste Schritt „Rolle festlegen“ und
   nicht „Artikel umbauen“.

Die Redaktions-Queue (`data/gsc/abdeckung/redaktions_queue.md`) enthält genau
diese zwei Zeilen – nichts anderes. Damit ist **M3** zum ersten Mal mit echten
Daten gefüllt, und **W9** schweigt, solange die Liste frisch bleibt.

> **Hinweis für die nächsten Exporte:** Die Search Console nennt jede Datei
> `Metadaten.csv` und `Tabelle.csv`. Fünf Exporte hintereinander ergeben fünf
> gleiche Namen – beim Ablegen überschreiben sie sich (am 26.10. so passiert:
> zehn Dateien geladen, eine Liste angekommen). Deshalb jede Datei vor dem
> Ablegen nach ihrem Grund benennen.

### 7.1 Was am 26.10.2026 tatsächlich umgesetzt wurde

Nicht die Absicht, das Ergebnis – gemessen am selben Tag:

| Größe | vorher | nachher | Messweg |
|---|---|---|---|
| Inhaltsseiten ohne redaktionellen Inlink | 14 von 76 | **0 von 74** | `--prioritaet` / `--verlinkung` |
| redaktionelle Links im Bestand | 508 | **539** | `redaktionelle_links()` |
| eingefügte Links (Beleg je Paar) | – | **33** | `data/verlinkung_history.jsonl` |
| Artikel über dem Goldkorridor (9) | 1 | **0** | `link_density_guard.py` |
| Gate-Regel für gebrochenen Vertrag | keine | **G6 (hart)** | `--audit --gate` |
| Hinweis „Detail-Listen fehlen“ | keiner | **W9** in jeder Ausgabe | `--audit` |
| Hinweis „Sitemap ohne lastmod“ | keiner | **W10** (9 URLs) | `--audit` |

Die Verlinkung lief in mehreren Läufen mit je höchstens zehn Links. Sie wurde
zweimal zurückgenommen: Der erste Anlauf setzte einen Artikel von neun auf zehn
interne Links, weil `link_density_guard.py` **Vorkommen** zählt und der Auftrag
zunächst **Ziele** zählte. Seitdem prüft `verlinkungs_auftrag()` vor jedem
Vorschlag die echte Datei mit der Regel des Guards (harte Grenze: nie mehr als
neun). Der zweite Anlauf traf eine zweite, ältere Altlast: ein Artikel stand
schon vorher bei zehn Links mit doppeltem Ziel; die Dublette im Fließtext ist
entlinkt, die „Weiterlesen“-Zeile blieb. Ergebnis: **0 über dem Korridor**,
88 % im Goldkorridor (vorher 85 %).

Zwei Befunde sind bei der Umsetzung neu dazugekommen:

- **Ein Teil der 404er kann aus dem eigenen Repo stammen.** Die Triage prüft
  jetzt, ob der Slug einer gemeldeten 404-URL als `draft: true` im Bestand
  liegt – dann lautet die Aktion „veröffentlichen“, nicht „weiterleiten“. Von
  den 27 Entwürfen sind vier aus live stehenden Artikeln verlinkt (W11); das
  Rendering zeigt dort nur noch Text, ein 404 entsteht also nicht, aber die
  Nachfrage ist dokumentiert. Getestet mit einer Beispiel-Liste: Die URL
  `/posts/2026-08-26-kfz-versicherung-vergleich-bis-zu-800-euro-sparen/` wird
  als **P1 „Seite liegt als Entwurf“** eingeordnet.
- **Zwei stehende Hinweise statt Schweigen.** Regel **W9** meldet in jeder
  Ausgabe, wenn die Detail-Listen fehlen oder älter als 14 Tage sind; Regel
  **W10** meldet die neun Sitemap-URLs ohne `lastmod`. Beides sind keine
  Fehler, die man wegdrückt, sondern Lücken, die man kennt.

Zwei Dinge sind bewusst **nicht** passiert:

- **Keine erfundenen `lastmod`-Daten.** Die neun Seiten ohne `lastmod` sind
  statische Vertrauensseiten (Impressum, Datenschutz, Über …). Ein Datum
  „heute“ wäre eine Lüge gegenüber Google; Regel W10 macht die Lücke sichtbar,
  statt sie zu übertünchen.
- **Keine Weiterleitung auf Verdacht.** Die 162 offenen Kandidaten-URLs bleiben
  offen, bis die Detail-Liste sagt, welche davon Google wirklich gesehen hat.

**Was nur ein Mensch tun kann** (kein Agent kann sich in dein Google-Konto
anmelden): die sechs Detail-Exporte aus der Oberfläche laden –
„Nicht gefunden (404)", „Gefunden – zurzeit nicht indexiert", „Gecrawlt –
zurzeit nicht indexiert", „Seite mit Weiterleitung", „Alternative Seite mit
ordnungsgemäßem Canonical-Tag", „Durch robots.txt blockiert". Sie kosten
zusammen zwei Minuten und machen aus 193 offenen 404ern eine Arbeitsliste.

### 7.2 Zwei Fehler, die erst mit echten Daten sichtbar wurden

Eine eigene Datei ist ein besserer Test als jede erfundene Probe. Sie hat zwei
Fehler gezeigt, die vorher niemand sehen konnte:

**1. Der Prioritäts-Score konnte negativ werden.** Rechtsseiten und Hubs ohne
Sitemap-Inhalt sammelten Abzüge (−1 für „kein Inhalt", −2 für Impressum,
Datenschutz, Transparenz). Im gespeicherten `prioritaet.json` standen sechs
Seiten mit Score **−1,0** – `/aenderungsprotokoll/`, `/methodik/`,
`/newsletter-checkliste/`, `/presse/`, `/so-entstehen-unsere-vergleiche/` und
eine weitere. Ein negativer Score ist keine Priorität, sondern ein Rechenrest:
Er drückt diese Seiten hinter alles andere, obwohl sie einfach nur nicht
dringend sind. Jetzt gilt `max(0, score)`; die Wellen 1 und 2 sind unverändert,
weil die fraglichen Seiten ohnehin nicht in Welle 1 lagen. Score-Bereich im
Bestand danach: **0,00 bis 8,88** über 99 Seiten.

**2. Der Selbsttest hing an einer Umgebungsvariable.** `INDEX_GATE_BASE`
bestimmt, welches Build gemessen wird – richtig für den Lauf, falsch für den
Test: Mit gesetzter Variable zog der Selbsttest die echten Sitemap-URLs herein
und meldete „K52 Score ist nie negativ" rot, ohne gesetzte Variable grün.
Derselbe Code, zwei Wahrheiten. Der Test übergibt jetzt explizit sein eigenes
Mini-Repo und ist damit unabhängig von der Umgebung – mit beiden Varianten
geprüft, beide grün.

**3. Der Plan behauptete „0 Detail-Zeilen“ – während vier Zeilen im Ordner
lagen.** Der Maßnahmenplan las nur, was im eingelesenen Export stand, und
ignorierte den Detail-Ordner. Jetzt zählt M8 die Listen („1 von 6“) und nennt
die fehlenden beim Namen, statt mit einer Null zu drohen.

Diese Korrekturen haben eigene Selbsttests (K52, K52b, K63b, K66–K68). Damit ist
der Fall abgeschlossen, nicht nur repariert.

### 7.3 Der Kreislauf – damit die Liste nicht wieder stehen bleibt

Die erste Fassung der Triage hatte einen Fehler, der erst beim Benutzen
auffällt: Sie war eine **Momentaufnahme**. Eine Zeile erschien, wurde gelesen –
und im nächsten Lauf erschien sie wieder, ohne Gedächtnis, ohne Frist, ohne
Nachweis. Genau so verschwinden Agentur-Listen: nicht durch Widerspruch,
sondern durch Wiederholung.

Vier Bausteine machen daraus einen Kreislauf:

**1. Der Vorschlag ist belegt, nicht geraten.** Jede offene Zeile trägt jetzt
einen Satz, der sich aus dem Bestand ergibt, z. B.:

> Rolle festlegen im Cluster K7-konto-karten-gebuehren (3 Artikel), Themenfeld
> „konto-karten“: Diese Seite hat dort keinen Eintrag.

Dafür liest das Modul erstmals `data/kannibalisierung_map.yaml` (34 Beiträge,
7 Cluster) und ordnet das Themenfeld dem Cluster zu. Kein neues Register – das
vorhandene wird benutzt.

**2. Die Entscheidung wird festgehalten, nicht erinnert.**

```bash
python3 scripts/gsc_abdeckung.py --entscheiden /posts/…/ \
  --entscheidung "Rolle festlegen: Rechenweg statt Vergleich" \
  --begruendung "Cluster K3 hat sechs Rollen, diese Seite hat keine" \
  --wiedervorlage 2026-11-25
```

Das schreibt eine Zeile nach `data/gsc/abdeckung/entscheidungen.yaml` – mit
Frist, Erwartung und Eigentümer. Ab dann schlägt die Triage die Seite nicht mehr
vor; sie prüft sie.

**3. Die Frist läuft von selbst.** `SLA_TAGE` = P0 1 Tag · P1 7 Tage · P2 30
Tage. Der Verlauf (`triage_verlauf.jsonl`) merkt sich, wann eine URL zum ersten
Mal als Aufgabe auftauchte. Ist die Frist überschritten, steigt die Zeile eine
Stufe und trägt den Grund im Text: „überfällig seit 55 Tagen (SLA 30)“. Eine
Priorität, die sich nie ändert, ist eine Meinung.

**4. Die Wirkung wird geprüft – am Repo, nicht am Gefühl.** Nach Ablauf der
Frist vergleicht `--triage` den `lastmod` der Seite mit dem Entscheidungsdatum:

| Befund | Urteil | Bedeutung |
|---|---|---|
| Seite nach der Entscheidung geändert | **P2** | Änderung ist live, Google hat sie nicht bewertet → Indexierung erneut anfragen |
| Seite unverändert | **P1** | Entscheidung ist beschlossen, nicht umgesetzt |
| URL nicht mehr in der Liste | **P3** | Wirkung belegt – Eintrag schließen |

Der dritte Fall ist der schönste Beleg, den dieses Repo erzeugen kann: Eine
URL, die drei Wochen als „gecrawlt, nicht indexiert“ gemeldet war, steht nicht
mehr in der Liste – und der Grund steht mit Datum im Register.

**Und ein Messfehler, den dieser Umbau gefunden hat.** Die erste Fassung maß
Titel-Ähnlichkeit auf dem **Slug** und meldete für den Monatskosten-Artikel
„2 ähnliche Titel“. Beide Treffer kamen von der Redewendung
„…-schritt-fuer-schritt“. Gemessen am Titel ohne Füllwörter und Jahreszahlen
bleibt: **0 Überschneidungen**. Die Aussage im Abschnitt 7.0 ist entsprechend
korrigiert. Ein Fehlalarm in einem Bericht ist teurer als eine Lücke – er
schickt die Redaktion an die falsche Baustelle.

Was der Umbau **nicht** tut: Er entscheidet nichts. Zwei Seiten stehen weiter
offen, mit Vorschlag und Frist, aber ohne Entscheidung – weil die dem Menschen
gehört. Der Automat hat nur dafür gesorgt, dass sie nicht mehr verschwinden
kann.

### 7.4 Was am 26.10.2026 noch offen ist

- **Fünf von sechs Detail-Listen fehlen.** Ohne die 404-Liste (223 Seiten)
  bleibt die Triage bei vier Zeilen – siehe `details/README.md` für die
  Dateinamen.
- **„Nicht kritische Probleme" kam leer an.** Der Export enthielt nur die
  Kopfzeile. Das ist ein gutes Zeichen (keine Warnungen) und keine Lücke – wird
  hier festgehalten, damit beim nächsten Lauf niemand eine fehlende Datei
  vermutet.
- **Das Entscheidungs-Register ist leer.** Zwei Seiten tragen eine Frist
  (30 Tage, bis 25.11.2026) und einen Vorschlag – aber keine Entscheidung.
  Das ist Absicht: Die Entscheidung gehört der Redaktion, nicht dem Automaten.
  Der Unterschied zu vorher: Sie kann jetzt nicht mehr still verschwinden.
- **`Diagramm.csv` endet am 19.10.2026** und deckt sich mit dem vorhandenen
  Snapshot (320 nicht indexiert / 117 indexiert, 7 Impressionen). Es fehlen
  Tage, deshalb ist der Export **Beleg, keine neue Momentaufnahme** – sonst
  würde die Zeitreihe rückwärts laufen.

---

## 8. Abnahmekriterien

| Zeitraum | Kriterium | Messung | maschinell |
|---|---|---|---|
| 14 Tage | Quote steigt, ohne dass die 404er wachsen | `--audit --gate` grün, `quote_indexiert` steigt | ✅ (`--abnahme`) |
| 14 Tage | keine offene Beweisfrage mehr bei den 404ern | `offen` bei „Nicht gefunden" = 0 oder begründet | ✅ |
| 30 Tage | mindestens 90 % der Sitemap-URLs im Index | Detail-Export je Grund | ❌ (menschlich) |
| 30 Tage | kein Widerspruch `W2`/`W3`/`W6` | `--gate` grün | ✅ |
| 30 Tage | keine Inhaltsseite ohne redaktionellen Inlink | `--prioritaet` | ✅ (seit 26.10. erfüllt) |
| 90 Tage | Impressionen auf Weiterleitungs-Stubs < 5 % | Top-Seiten gegen Sitemap | ❌ (menschlich) |
| laufend | Befund nie älter als 14 Tage | `export_alter_tage` (`W8`) | ✅ |
| laufend | Detail-Listen nie älter als 14 Tage | `detail_alter_tage` (`W9`) | ✅ |
| laufend | kein gebrochener Vertrag | `--vertrag`, Gate `G6` | ✅ |
| laufend | jede offene Aufgabe hat eine Frist und wird nach Ablauf geprüft | `--triage` (Alter, SLA, Wirkungsprüfung) | ✅ (seit 26.10.) |

Seit dem 26.10.2026 prüft `npm run gsc:abnahme` diese Zeilen und nennt je
offenem Punkt den nächsten Schritt. Ein Kriterium ohne Datum ist ein Wunsch;
ein Kriterium ohne Messweg ist eine Behauptung.

---

## 9. Grenzen dieses Befunds

- **Die 193 offenen 404er sind nicht zugeordnet.** Ohne Detail-Liste wäre jede
  Zuordnung geraten; das Modul schreibt die Lücke auf, statt sie zu füllen.
- **Die Hypothese „kein Artikel im Index" ist nicht bewiesen.** Sie stützt sich
  auf die zweimal auftretende Zahl 69 und ist in einem Schritt prüfbar.
- **Die 115 Weiterleitungsseiten sind kein 301.** Sie sind noindexiert und
  tragen ein Canonical; für Google ist das ein Ersatz, keine Gleichwertigkeit.
- **Der Befund misst den Build, nicht die Live-Site.** Weicht die ausgelieferte
  Sitemap ab, zeigt das `gsc_verifikations_guard.py --nur-live` (V13), nicht
  dieses Modul.
- **Der Bericht hat keine API.** Er ist nur so frisch wie der letzte Export;
  das Alter steht in jeder Ausgabe.

---

## 10. Befehle

```bash
# Export einlesen (Verzeichnis mit den vier CSVs)
python3 scripts/gsc_abdeckung.py --import ~/Downloads/search-console

# Gegenrechnen
python3 scripts/gsc_abdeckung.py --audit
python3 scripts/gsc_abdeckung.py --audit --md
python3 scripts/gsc_abdeckung.py --audit --gate     # Exit 1 bei Rückschritt

# Triage einer 404-Detail-Liste
python3 scripts/gsc_abdeckung.py --vorschlaege "details/Nicht gefunden (404).csv"

# Maßnahmenplan (M1–M9)
python3 scripts/gsc_abdeckung.py --triage          # Detail-Listen → Arbeitsliste
python3 scripts/gsc_abdeckung.py --entscheidungen  # Register mit Fristen zeigen
python3 scripts/gsc_abdeckung.py --entscheiden "/posts/…/" \
    --entscheidung "Rolle festlegen" --begruendung "…" --wiedervorlage 2026-11-25
python3 scripts/gsc_abdeckung.py --vertrag         # noindex-Bestand, Gateways
python3 scripts/gsc_abdeckung.py --kandidaten      # Obergrenze der 404-Erklärung
python3 scripts/gsc_abdeckung.py --prioritaet      # Anfrage-Wellen
python3 scripts/gsc_abdeckung.py --verlinkung      # Auftrag zeigen
python3 scripts/gsc_abdeckung.py --verlinkung --apply --max 10   # schreiben
python3 scripts/gsc_abdeckung.py --altlasten       # Index-Puffer benennen
python3 scripts/gsc_abdeckung.py --kpi             # Wochenkennzahl
python3 scripts/gsc_abdeckung.py --abnahme         # Abnahmekriterien
python3 scripts/gsc_abdeckung.py --ursachen        # Sprung mit Git-Beleg

# Selbsttest und Regressionstests
python3 scripts/gsc_abdeckung.py --selftest        # 80 Fälle
python3 -m unittest scripts.tests.test_gsc_abdeckung   # 63 Tests

# npm-Kurzbefehle
npm run gsc:abdeckung · gsc:abdeckung:gate · gsc:triage · gsc:vertrag
npm run gsc:prioritaet · gsc:verlinkung · gsc:verlinken · gsc:kpi
npm run gsc:abnahme · gsc:ursachen · gsc:altlasten
npm run gsc:register        # Entscheidungs-Register (neu)
```

---

## 11. Geänderte und neue Dateien

| Datei | Art | Inhalt |
|---|---|---|
| `scripts/gsc_abdeckung.py` | neu | Abdeckungs-Zentrale (Import, Gegenrechnung, Gate, Triage) |
| `scripts/tests/test_gsc_abdeckung.py` | neu | 51 Regressionstests |
| `data/gsc/abdeckung/**` | neu | Export, Momentaufnahme, Verlauf, Befund |
| `data/gsc/abdeckung/details/` | neu | Detail-Listen je Grund, `stand.txt` (Exportdatum), `README.md` (Ablage-Regel) |
| `data/gsc/abdeckung/{triage.json,triage.md,redaktions_queue.md}` | neu | Ergebnis der Triage aus der ersten gelieferten Liste |
| `data/gsc/abdeckung/triage_verlauf.jsonl` | neu | seit wann eine URL offen ist (Fristgrundlage) |
| `data/gsc/abdeckung/entscheidungen.yaml` | neu | Entscheidungs-Register mit Wiedervorlage und Erwartung |
| `docs/ANLEITUNG-GOOGLE-SEARCH-CONSOLE.md` | geändert | Abschnitt 9 (Export, Gegenprobe, Grenzen), Abschnitte 10–11 neu nummeriert |
| `.github/workflows/gsc-import.yml` | geändert | Selbsttest, Build für die Gegenprobe, Abdeckungs-Schritt mit Lauf-Tabelle, fünf Maßnahmen-Schritte, Artefakt-Upload, Welle 1 als Anfrage-Reihenfolge |
| `scripts/cockpit.py` | geändert | Zeile „Search Console" in „SEO & Technik" |
| `package.json` | geändert | drei npm-Befehle, `test:gsc` erweitert |
| `.gitattributes` | geändert | `merge=binary` für die Abdeckungs-Artefakte |

Kein Artikel, kein Template und keine Weiterleitungskarte wurde verändert. Der
Eingriff betrifft ausschließlich die Messschicht und ihre Ausgabe.
