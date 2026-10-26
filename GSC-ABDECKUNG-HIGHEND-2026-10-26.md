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
reproduzierbar, offline, mit 33 Regressionstests.

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

`merge=binary` für die JSON-Artefakte (`.gitattributes`), `merge=union` bleibt
für den Verlauf: Eine Zeile je Momentaufnahme ist eine unabhängige Messung.
Dieselbe Regel wie bei den GSC-Leistungsdaten nach dem 21.10.2026.

### 5.3 Tests, Workflow, Cockpit

- `scripts/tests/test_gsc_abdeckung.py` – 33 Regressionstests über vier Ebenen:
  Lesen (BOM, Semikolon, deutsche Anführungszeichen), Nicht-Schreiben bei
  Widerspruch, Gegenrechnen (noindex-Leck, robots-Sperre ohne Gateway,
  unbekannter Grund), Hermetik (kein Netz, kein Schreiben in den echten
  Verlauf). Selbsttest: 40 Fälle.
- `.github/workflows/gsc-import.yml` – Build für die Gegenprobe (nicht
  kritisch), dann `--audit --schreiben --json` mit Tabelle in der
  Lauf-Zusammenfassung. Ein roter Befund wird als Warnung sichtbar, blockiert
  aber nicht den Datenimport; die harten Regeln greifen im Befund selbst.
- `scripts/cockpit.py` – neue Zeile in „SEO & Technik": Quote, offene Posten,
  Gate-Status. Fehlt der Befund, bleibt der Bereich wie bisher (kein erfundener
  Zustand).
- `package.json` – `gsc:abdeckung`, `gsc:abdeckung:gate`, `gsc:abdeckung:md`;
  `test:gsc` um den neuen Selbsttest und die 30 Tests erweitert.
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

| ID | Prio | Aufwand | Maßnahme | Beleg | Eigentümer |
|---|---|---|---|---|---|
| M1 | **P1** | S | 404-Detail-Liste exportieren und einlesen, dann triagieren | 223 gemeldet, 30 erklärbar, 193 offen | Mensch (Export) + Automat |
| M2 | **P1** | M | Crawl-Nachfrage für die 69 gefundenen, nicht abgerufenen Seiten | 69 bei 99 indexierbaren Seiten | Automat + Redaktion |
| M3 | P2 | M | Redaktions-Queue für die 4 „gecrawlt, nicht indexiert" | 4 Seiten | Redaktion |
| M4 | P2 | S | Index-Altlasten benennen statt mitzählen | 117 indexiert bei 99 indexierbar | Automat |
| M7 | P2 | S | Sprung vom 17.10. erklären | 261 → 320 bzw. 138 → 117 | Mensch |
| M8 | P2 | S | Detail-Exporte wöchentlich in den Tageslauf | 0 Detail-Zeilen im Export | Mensch + Automat |
| M9 | P2 | S | Indexquote als Wochen-Kennzahl etablieren | 26,8 % | Automat |
| M5 | P3 | S | noindex-Bestand als Vertrag führen | 5 = 5 | Automat |
| M6 | P3 | S | robots-Sperre der Gateways dokumentiert lassen | 18 von 20 | Automat |

**Was M2 konkret heißt** (der einzige Hebel, der ohne Google-Zugriff wirkt):
interne Verlinkung verdichten (jede der 69 Seiten aus mindestens zwei Artikeln
erreichbar), `lastmod` ehrlich halten, Publikationskadenz auf 2/Tag begrenzen,
damit der Crawler nicht gegen 27 Entwürfe und 2 neue Artikel pro Tag anläuft –
und wöchentlich `python3 scripts/gsc_indexierung.py --pruefen` für den Status
je URL.

**Was nur ein Mensch tun kann** (kein Agent kann sich in dein Google-Konto
anmelden): die sechs Detail-Exporte aus der Oberfläche laden –
„Nicht gefunden (404)", „Gefunden – zurzeit nicht indexiert", „Gecrawlt –
zurzeit nicht indexiert", „Seite mit Weiterleitung", „Alternative Seite mit
ordnungsgemäßem Canonical-Tag", „Durch robots.txt blockiert". Sie kosten
zusammen zwei Minuten und machen aus 193 offenen 404ern eine Arbeitsliste.

---

## 8. Abnahmekriterien

| Zeitraum | Kriterium | Messung |
|---|---|---|
| 14 Tage | Quote steigt, ohne dass die 404er wachsen | `--audit --gate` grün, `quote_indexiert` steigt |
| 14 Tage | keine offene Beweisfrage mehr bei den 404ern | `offen` bei „Nicht gefunden" = 0 oder begründet |
| 30 Tage | mindestens 90 % der Sitemap-URLs im Index | Detail-Export je Grund |
| 30 Tage | kein Widerspruch `W2`/`W3`/`W6` | `--gate` grün |
| 90 Tage | Impressionen auf Weiterleitungs-Stubs < 5 % | Top-Seiten gegen Sitemap |
| laufend | Befund nie älter als 14 Tage | `export_alter_tage` im Befund (`W8`) |

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

# Selbsttest und Regressionstests
python3 scripts/gsc_abdeckung.py --selftest
python3 -m unittest scripts.tests.test_gsc_abdeckung

# npm-Kurzbefehle
npm run gsc:abdeckung · npm run gsc:abdeckung:gate · npm run gsc:abdeckung:md
```

---

## 11. Geänderte und neue Dateien

| Datei | Art | Inhalt |
|---|---|---|
| `scripts/gsc_abdeckung.py` | neu | Abdeckungs-Zentrale (Import, Gegenrechnung, Gate, Triage) |
| `scripts/tests/test_gsc_abdeckung.py` | neu | 33 Regressionstests |
| `data/gsc/abdeckung/**` | neu | Export, Momentaufnahme, Verlauf, Befund |
| `docs/ANLEITUNG-GOOGLE-SEARCH-CONSOLE.md` | geändert | Abschnitt 9 (Export, Gegenprobe, Grenzen), Abschnitte 10–11 neu nummeriert |
| `.github/workflows/gsc-import.yml` | geändert | Selbsttest, Build für die Gegenprobe, Abdeckungs-Schritt mit Lauf-Tabelle |
| `scripts/cockpit.py` | geändert | Zeile „Search Console" in „SEO & Technik" |
| `package.json` | geändert | drei npm-Befehle, `test:gsc` erweitert |
| `.gitattributes` | geändert | `merge=binary` für die Abdeckungs-Artefakte |

Kein Artikel, kein Template und keine Weiterleitungskarte wurde verändert. Der
Eingriff betrifft ausschließlich die Messschicht und ihre Ausgabe.
