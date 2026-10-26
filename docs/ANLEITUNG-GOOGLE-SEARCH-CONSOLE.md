# Google Search Console für franksfinanzcheck.de

Aktualisiert: 26.10.2026 (Abschnitt 9 – Abdeckungsbericht). Frühere Fassungen:
github.io-Anleitung (ersetzt 20.09.2026), Abschnitt „ohne API" (ersetzt
11.10.2026 durch [ANLEITUNG-GSC-API-ZUGRIFF.md](ANLEITUNG-GSC-API-ZUGRIFF.md)).

Dieses Runbook trennt zwei Dinge, die leicht verwechselt werden:

| | Wer entscheidet | Was das Repo tut |
|---|---|---|
| **Verifizierung** | Google + ein Mensch mit dem berechtigten Konto | Besitznachweis bereitlegen und dauerhaft bewachen |
| **Indexierung** | Google | jede indexierbare Seite anbieten und aktiv anfragen |

Beides ist eingerichtet und maschinell abgesichert. Was ein Agent nicht kann:
sich in dein Google-Konto anmelden. Die drei Handgriffe in Abschnitt 1 sind
deshalb ausdrücklich menschliche Arbeit – sie sind einmalig und dauern zusammen
keine zehn Minuten.

---

## 1. Property verifizieren (einmalig, menschlich)

[Google Search Console](https://search.google.com/search-console) öffnen und
mit dem berechtigten Google-Konto anmelden.

**Empfehlung: Domain-Property.** Sie fasst `http`/`https`, `www` und alle
Subdomains zusammen – bei einer Site mit `abos.franksfinanzcheck.de`
(Newsletter-Capture) ist das die robustere Wahl, und sie ist die Voraussetzung
dafür, dass die URL Inspection API für jede URL der Domain funktioniert.

1. **Property hinzufügen** → links **Domain** → `franksfinanzcheck.de`.
2. Google zeigt einen TXT-Wert der Form `google-site-verification=…`.
3. In Cloudflare (DNS-Anbieter der Domain, siehe
   [DNS-CLOUDFLARE-GITHUB-PAGES.md](DNS-CLOUDFLARE-GITHUB-PAGES.md)):
   **DNS → Datensätze → Hinzufügen** · Typ `TXT` · Name `@` · Inhalt der Wert
   aus Schritt 2 · speichern.
4. In der Search Console **Bestätigen**. DNS kann wenige Minuten brauchen;
   „Überprüfung fehlgeschlagen" ist in dieser Phase normal – erneut versuchen.

**Zweiter Weg, bereits fertig ausgeliefert:** die URL-Präfix-Property
`https://franksfinanzcheck.de/` über die HTML-Datei. Sie liegt unverändert im
Repo (`static/google8f0cd9537348f066.html`) und wird mit jedem Build
ausgeliefert. Die Wache V1 prüft bei jedem Deploy, dass sie im Build ankommt
**und dass ihr Inhalt zum Dateinamen passt** – ein Token, der nicht zum Namen
gehört, verifiziert nichts und fällt sonst erst Wochen später auf.

Keine neue Property anlegen, wenn eine passende bereits existiert. Niemals
Passwörter, OAuth-Tokens oder private Schlüssel in Chat oder Git ablegen.

## 2. Sitemap einreichen (einmalig, menschlich)

Search Console → **Sitemaps** → `https://franksfinanzcheck.de/sitemap.xml`
eintragen. Erwarteter Status: **Erfolgreich**.

Die Sitemap wird seit dem 01.10.2026 **abgeleitet**, nicht aufgezählt
(`layouts/sitemap.xml` + `_partials/sitemap_kandidaten.html`): Jede Seite des
Content-Baums, die `index, follow` trägt, steht automatisch darin. Eine neue
Seite muss nirgends nachgetragen werden. Enthalten sind Originalseiten – keine
Tag-/Kategorie-Archive (die Taxonomien sind seit 29.09.2026 abgeschaltet),
keine Pager-Seiten, keine Verifikationsdateien.

Google garantiert weder die Indexierung jeder URL noch eine feste Frist. Was
das Repo tut, ist jede Seite **anzubieten** und aktiv **anzufragen** –
Abschnitt 3.

## 3. Indexierung aktiv anfragen (automatisch, seit 12.10.2026)

Bis zu diesem Datum kannte das Projekt drei Wege in den Index: Sitemap
(Entdeckung), robots.txt (Erlaubnis) und Warten (Zufall). Die vierte Stufe
fehlte – die **aktive Anfrage**, in der Search-Console-Oberfläche der Knopf
„Indexierung beantragen".

Zuständig ist `scripts/gsc_indexierung.py` über die **URL Inspection API**. Sie
läuft täglich in `.github/workflows/gsc-import.yml` und holt die Seiten aus
derselben Quelle wie alle anderen Einreichungswege: der Sitemap.

```bash
python3 scripts/gsc_indexierung.py --live --plan     # was wäre heute fällig?
python3 scripts/gsc_indexierung.py --live --dry-run  # Zugang+Berechtigung prüfen, nichts senden
python3 scripts/gsc_indexierung.py --live            # anfragen
python3 scripts/gsc_indexierung.py --url https://franksfinanzcheck.de/posts/x/
```

**Voraussetzung:** das Dienstkonto braucht in der Search Console die
Berechtigung **„Vollständig" (Owner)**. „Eingeschränkt" reicht für den
Lese-Import, nicht für eine Anfrage – Google antwortet dann mit 403. Das Skript
prüft die Stufe vor der ersten Anfrage und sagt, was fehlt.

**Grenzen, die das Skript respektiert statt sie zu umgehen:**

- 200 Anfragen je Property und Tag. Das Skript führt ein Kontingent-Gedächtnis
  (`data/gsc_indexierung_state.json`) und hält 5 Anfragen Sicherheitsabstand.
- Wiedervorlage statt Dauerfeuer: eine bereits indexierte Seite wird nach
  28 Tagen erneut angefragt, eine noch nicht indexierte nach 7 – oder sofort,
  wenn sich ihr `lastmod` geändert hat. Unveränderte URLs täglich
  einzureichen ist genau das, wovor Google in den Richtlinien warnt.
- Die URL Inspection API ist **nicht** die „Google Indexing API". Diese gilt
  ausschließlich für `JobPosting`- und `BroadcastEvent`-Seiten; sie für einen
  Ratgeber-Blog zu benutzen wäre ein Richtlinienverstoß.

**Abdeckungszustände lesen.** Die Antwort der API nennt `coverageState`. Das
ist der eigentliche Nutzen – sie erklärt, *warum* eine Seite nicht im Index ist:

| Zustand | Bedeutung | Reaktion |
|---|---|---|
| `Submitted and indexed` | drin | keine |
| `Crawled - currently not indexed` | gesehen, für zu schwach befunden | Inhalt, interne Verlinkung, Duplikat prüfen |
| `Discovered - currently not indexed` | bekannt, aber nicht gecrawlt | Crawl-Budget: interne Links, Sitemap-Priorität |
| `Duplicate without user-selected canonical` | Google wählt ein anderes Canonical | V6-Befund der Wache ansehen |
| `Excluded by robots.txt` | gesperrt | V2/V3-Befund der Wache ansehen |

## 4. Wache: Verifikation und Indexierbarkeit (V1–V13)

`scripts/gsc_verifikations_guard.py` prüft die **Zugangsschicht** zur Search
Console. `index_hygiene_gate.py` misst die Menge der Crawl-Fläche,
`schema_seo_gate.py` die Auszeichnung der einzelnen Seite – beide prüfen nicht,
ob Google die Site überhaupt verifizieren kann und ob Sitemap und gebaute
Wahrheit zusammenpassen.

Läuft **hart im Deploy** (vor der Auslieferung) und **täglich live** im
GSC-Tageslauf:

```bash
hugo --minify --destination public
python3 scripts/gsc_verifikations_guard.py             # V1–V12 gegen public/
python3 scripts/gsc_verifikations_guard.py --nur-live  # V13 gegen die Live-Site
```

| Regel | Prüfung |
|---|---|
| V1 | Besitznachweis liegt im Build **und** sein Inhalt passt zum Dateinamen |
| V2 | robots.txt sperrt Googlebot nicht aus (`Google-Extended` darf zu bleiben) |
| V3 | Sitemap-Hinweis in robots.txt: absolut, eigener Host, Datei vorhanden |
| V4 | Sitemap-Protokoll: gültiges XML, ≤ 50.000 URLs, ≤ 50 MiB, keine Duplikate, kein fremder Host, keine Query, Kind-Reihenfolge, Bild-Tag nach `priority` |
| V5 | Jede Sitemap-URL hat eine gebaute Datei mit `index`; jede indexierbare Seite steht in der Sitemap |
| V6 | Canonical ist selbstreferenziell |
| V7 | Keine Verifikationsdatei, keine `/go/`-Weiterleitung, kein Pager in der Sitemap |
| V8 | Startseite trägt WebSite- und Organization-JSON-LD (E-E-A-T) |
| V9 | Jede noindex-Seite hat einen erklärten Grund |
| V10 | Ein in `hugo.toml` gesetzter Meta-Token kommt auch im Build an |
| V11/V12 | Hinweise: fehlendes `lastmod`, fehlender Bild-Eintrag, Waisen |
| V13 | **live**: Verifikationsdatei, robots.txt und Sitemap sind erreichbar, inhaltsgleich zum Build und ohne Weiterleitung; Stichprobe der wichtigsten URLs auf 200, `index` und korrektes Canonical |

V9 ist die Regel mit der höchsten Trefferquote in der Praxis: „Gefunden –
derzeit nicht indexiert" in der Search Console ist fast immer eine Seite, die
irgendwo ein `noindex` trägt, das niemand mehr kennt. Als Grund zählt ein
`robotsNoIndex: true` im Frontmatter, ein Pager, die 404-Seite, eine
`/go/`-Weiterleitung – oder eine Funktionsfläche aus `static/` (Veröffentlichungs-
kalender, Pinterest-Autorisierung), die ihr `noindex` selbst trägt und kein
Inhalt ist.

**Kein `--fix`.** Jeder Fund ist eine Entscheidung über Zugang, Index oder
Architektur. Die trifft die Redaktion, nicht eine Wache.

## 5. Eine Quelle für alle Einreichungswege

`scripts/indexierbare_seiten.py` beantwortet die Frage „welche Seiten sollen
in den Index?" **einmal** – aus der Sitemap. Daraus lesen:

- `scripts/gsc_indexierung.py` (Google, URL Inspection API)
- `scripts/submit_indexnow.py` (Bing, Yandex, Naver, Seznam – Google nimmt an
  IndexNow nicht teil)

Der Befund, der zu dieser Umstellung führte: Am 12.10.2026 standen 74
indexierbare URLs in der Sitemap, aber nur 54 in der IndexNow-Meldeliste. 20
Seiten waren nie an eine Suchmaschine gemeldet worden – darunter die acht
Werkzeug-Rechner, das Fixkosten-Cockpit, die Studien-Seite, `/ueber/`,
`/transparenz/`, `/impressum/` und `/datenschutz/`. Die Ursache war eine
handgeschriebene Namensliste im Skript: dieselbe Fehlerklasse, die
`layouts/sitemap.xml` am 01.10.2026 schon einmal erledigt hatte. Eine Liste,
die bei jedem Wachstum bricht, ist kein Premium-Zustand.

```bash
python3 scripts/indexierbare_seiten.py           # Bestand aus public/sitemap.xml
python3 scripts/indexierbare_seiten.py --live    # Bestand der ausgelieferten Sitemap
python3 scripts/submit_indexnow.py --dry-run     # IndexNow-Vorschau, schreibt nichts
```

**Vertrag des Probelaufs.** `--dry-run` schreibt bei beiden Werkzeugen nichts –
weder eine ausgelieferte Datei noch einen Zustand. Bei
`gsc_indexierung.py` kehrt der Lauf vor der ersten Anfrage zurück
(`status: dry_run`, geprüft im Selbsttest), bei `submit_indexnow.py` bleiben
`static/llms.txt` und `.indexnow_submitted.json` unangetastet (geprüft durch
drei Tests in `scripts/tests/test_gsc_indexierung_kette.py`, darunter eine
Gegenprobe: ohne `--dry-run` muss geschrieben werden). Ein Probelauf, der den
Arbeitsbaum ändert, ist keiner – er kann einen Deploy auslösen, obwohl niemand
etwas eingereicht hat. Nachweis: Abschnitt 10 des Berichts vom 12.10.2026.

## 6. Leistungsdaten im Repo

`scripts/gsc_import.py` holt täglich aggregierte Klicks, Impressionen, CTR und
Positionen (nur lesend, keine Personenbezüge) nach `data/gsc/`. Der tägliche
Lauf öffnet dafür einen PR; gemergt wird nach deiner Prüfung. Einrichtung und
Fehlersuche: [ANLEITUNG-GSC-API-ZUGRIFF.md](ANLEITUNG-GSC-API-ZUGRIFF.md).

Auswertung im SEO-Cockpit: `npm run seo:audit` und `npm run seo:serve`
([ANLEITUNG-SEO-COCKPIT.md](ANLEITUNG-SEO-COCKPIT.md)). Der manuelle Notweg
über CSV-Export bleibt Abschnitt 8.

**Redaktionelle Reihenfolge bei der Auswertung:** Seiten mit ausreichend
Impressionen und Position 4–20 zuerst. Suchintention prüfen, konkrete
Fakten/Quellen aktualisieren, intern passend verlinken – und erst danach Titles
überarbeiten. Eine niedrige CTR kann an Suchintention, SERP-Features oder
Position liegen, nicht pauschal an „schlechten Titeln".

## 7. Was täglich automatisch läuft

`.github/workflows/gsc-import.yml`, 05:17 UTC (≈ 07:17 Berlin):

1. Selbsttests der sechs beteiligten Wachen (fail-closed, offline)
2. V13 **live** gegen die ausgelieferte Site – was Google sieht, nicht was ein
   lokaler Build behauptet
3. Leistungsdaten holen (`gsc_import.py`)
4. Build für die Gegenprobe + Abdeckung rechnen (`gsc_abdeckung.py --audit --gate`)
5. Maßnahmenplan: Vertrag (`--vertrag`), Anfrage-Wellen (`--prioritaet`),
   Verlinkungsauftrag (`--verlinkung`), Triage (`--triage`, nur wenn
   Detail-Listen vorliegen), Wochenkennzahl und Abnahme (`--kpi`, `--abnahme`,
   `--altlasten`) – jeder Schritt endet mit einer Warnung, nie mit Abbruch
6. Indexierung anfragen (`gsc_indexierung.py --live`), in der Reihenfolge der
   Welle 1 aus `prioritaet.json` (max. 40 statt stumpf 200 nach `lastmod`)
7. IndexNow-Ping (`submit_indexnow.py --live --kein-llms`)
8. Artefakte als Download (`gsc-abdeckung`), Zustand direkt auf main sichern,
   Leistungsdaten als PR

Ohne Secrets endet der Lauf mit Status `nicht_konfiguriert` und bleibt **grün** –
ein noch nicht eingerichtetes Dienstkonto ist ein Zustand, kein Defekt.
Verschwiegen wird er nicht: Er steht in der Lauf-Zusammenfassung.

## 8. Manueller Notweg (CSV, ohne API)

**Leistung → Suchergebnisse → Exportieren → CSV**. ZIP entpacken und Datei im
lokalen Cockpit importieren: `npm run seo:audit` · `npm run seo:serve`.
Benötigt keine API, kein Google-Cloud-Projekt, keine Zugangsdaten. Es wird
nichts hochgeladen.

## 9. Abdeckungsbericht (Seiten-Indexierung)

Das ist der Bericht, den eine Agentur zuerst aufschlägt: **warum ist eine URL
nicht im Index?** Er heißt in der Oberfläche „Indexierung → Seiten" und hat
einen Nachteil, den keine Automatisierung wegzaubert: **Google stellt für ihn
keine API bereit.** Es gibt ihn nur als CSV-Export. Bis zum 26.10.2026 lagen
seine Zahlen deshalb als Bildschirmfoto vor – und niemand konnte sie gegen den
eigenen Bestand rechnen.

### 9.1 Exportieren (Mensch, 2 Minuten)

Search Console → **Indexierung → Seiten** → oben rechts **Exportieren**. Es
entstehen vier Dateien:

| Datei | Inhalt | Wird gebraucht für |
|---|---|---|
| Übersicht | Grund, Quelle, Validierung, Seiten | die Rangliste der Ursachen |
| Diagramm | Datum, nicht indexiert, indexiert, Impressionen | Verlauf und Sprünge |
| Metadaten | Property, Sitemap | Zuordnung des Exports |
| Detail je Grund (z. B. „Nicht gefunden (404).csv") | die betroffenen URLs | jede echte Ursachenanalyse |

Die Detail-Listen sind der entscheidende Teil. Ohne sie kennt man die Summe,
aber nicht eine einzige URL – und jede Zuordnung wäre geraten.

### 9.2 Einlesen und gegenrechnen (Automat)

```bash
python3 scripts/gsc_abdeckung.py --import ~/Downloads/search-console
python3 scripts/gsc_abdeckung.py --audit            # gegen den Repo-Bestand
python3 scripts/gsc_abdeckung.py --audit --gate     # Tor für den Tageslauf
python3 scripts/gsc_abdeckung.py --vorschlaege details/"Nicht gefunden (404).csv"
```

Das Modul prüft den Export **vor** dem Schreiben: Summieren sich die Gründe
nicht auf den Tageswert im Diagramm, stammen Übersicht und Diagramm aus
verschiedenen Momenten, und der Import wird abgelehnt (`E8`). Dieselbe Lehre
wie am 21.10.2026, als drei GSC-Artefakte durch einen Text-Merge unlesbar
wurden.

### 9.3 Gegenprobe: die Zahl neben der Zahl

Jede Meldung bekommt eine Erwartung aus dem Repo – nicht aus einer gepflegten
Liste:

| Meldung | Erwartung kommt aus | Am 19.10.2026 |
|---|---|---|
| „Durch noindex ausgeschlossen" | `robotsNoIndex: true` in `content/` | 5 gemeldet, 5 erwartet |
| „Durch robots.txt blockiert" | Ordner in `static/go/` | 18 gemeldet, 20 Gateways |
| „Seite mit Weiterleitung" | Einträge in `data/weiterleitungen.yaml` | 1 gemeldet, 115 möglich |
| „Nicht gefunden (404)" | Taxonomie-URLs + `data/url_entfallen.yaml` | 223 gemeldet, 30 erklärbar |
| „Gefunden / gecrawlt, nicht indexiert" | Sitemap-Bestand (Obergrenze) | 69 + 4 bei 99 Seiten |

Steigt eine Zahl über ihre Erwartung, ist das ein **harter** Widerspruch: eine
noindex-Seite, die niemand eingetragen hat (`W2`), eine robots-Sperre auf einer
Inhaltsseite (`W3`) oder ein Grund, den das Modul nicht kennt (`W6`, heißt:
Google hat etwas geändert). Bleibt sie darunter, steht das ausdrücklich als
„plausibel" da – nicht als „in Ordnung".

### 9.4 Was der Bericht vom 19.10.2026 zeigt

- 437 bekannte URLs, davon 117 im Index (26,8 %), 320 nicht.
- Der Build enthält **258 URLs**, davon **99 indexierbar**. Auf jede
  indexierbare Seite kommt also 1,6 Seiten, die nicht in den Index sollen
  (Weiterleitungen, Gateways, Pager, noindex-Funnel).
- 320 Nicht-Index-Einträge bei 258 gebauten URLs heißt: **Es sind mehr
  Einträge als Seiten.** Über die Hälfte der Einträge betrifft URLs, die es
  nicht mehr gibt. Genau das ist der 404-Block.
- 117 indexierte URLs bei 99 indexierbaren Seiten: mindestens 18 Einträge im
  Index gehören nicht zur Sitemap (Altlasten). Die Quote ist deshalb zu hoch,
  nicht zu niedrig.
- Am 17.10.2026 springt „nicht indexiert" von 261 auf 320 und „indexiert" von
  138 auf 117. Ein Sprung dieser Größe hat eine Ursache (Deploy,
  Sitemap-Änderung, Aufräumaktion) und gehört ins Änderungsprotokoll.

### 9.5 Artefakte und Grenzen

| Pfad | Bedeutung |
|---|---|
| `data/gsc/abdeckung/export/<datum>/` | der eingelesene Export, unverändert (Beweis) |
| `data/gsc/abdeckung/<datum>.json` | Momentaufnahme, ein Lauf = eine Messung |
| `data/gsc/abdeckung/aktuell.json` | dieselbe Momentaufnahme unter festem Pfad |
| `data/gsc/abdeckung/verlauf.jsonl` | eine Zeile je Momentaufnahme (append-only) |
| `data/gsc/abdeckung/befund.json` / `.md` | Ergebnis der Gegenrechnung |

Grenzen, die das Modul nicht überschreitet: Es erfindet keine URL, es schreibt
nie in `data/weiterleitungen.yaml` oder `data/url_entfallen.yaml` (Weiterleitungen
sind eine Entscheidung über Suchabsicht, Regeln A–E), und es ruft keine
Suchmaschine auf. Der Befund ist offline reproduzierbar – in einem Jahr genauso.

Das Alter des Befunds steht in jeder Ausgabe. Ist der Export älter als 14 Tage,
meldet der Befund das als `W8`; älter als 21 Tage wird daraus die P1-Maßnahme
`M10`. Ein Bildschirmfoto von vor drei Wochen ist keine Messung.

## 10. Maßnahmenplan in Betrieb (M1–M9)

Der Bericht `GSC-ABDECKUNG-HIGHEND-2026-10-26.md` listet neun Maßnahmen. Sie
sind hier keine Vorsätze, sondern Befehle und Workflow-Schritte. Jede Zeile
sagt, wer sie auslöst und wo das Ergebnis liegt.

| Maßnahme | Auslöser | Befehl / Ort | Ergebnis |
|---|---|---|---|
| M1 404er triagieren | Mensch (Export) + Tageslauf | `npm run gsc:triage` (liest `data/gsc/abdeckung/details/`) | `triage.json`, `triage.md` |
| M2 Anfrage-Priorität | Tageslauf | `--prioritaet` → Welle 1 geht an `gsc_indexierung.py --url …` | `prioritaet.json` |
| M2 interne Verlinkung | Mensch, je Lauf begrenzt | `npm run gsc:verlinkung` (Vorschau), `npm run gsc:verlinken` (schreibt) | `verlinkungsauftrag.json`, `data/verlinkung_history.jsonl` |
| M3 Redaktions-Queue | Tageslauf nach Triage | `redaktions_queue.md`, `--entscheiden` | nur Seiten mit Frist und Vorschlag; Entscheidung im Register |
| M4 Altlasten benennen | Tageslauf | `npm run gsc:altlasten` | Zahl + URLs mit belegter Nachfrage |
| M5 noindex-Vertrag | Tor (hart) | `--vertrag`, Regel V1/V2 | `vertrag.json`, Gate ROT bei Leck |
| M6 robots-Sperre | Tor (hart) | `--vertrag`, Regel V3/V4 | dito |
| M7 Sprung erklären | Mensch | `npm run gsc:ursachen` | `ursachen.json`, Beleg aus `git log` |
| M8 Detail-Listen | Mensch (Export) + Tageslauf | `stand.txt` in `details/`, Regel W9 | Warnung im Lauf, „1 von 6 Listen“ im Plan |
| M9 Wochen-Kennzahl | Tageslauf | `npm run gsc:kpi`, `npm run gsc:abnahme` | KPI-Tabelle, Abnahmestatus |

### 10.1 Detail-Listen ablegen (der einzige menschliche Schritt)

In der Search Console: **Indexierung → Seiten → Grund anklicken → Exportieren**,
je Grund eine CSV. Die Dateien nach `data/gsc/abdeckung/details/` legen und das
Exportdatum in `data/gsc/abdeckung/details/stand.txt` schreiben (`2026-10-26`).
Danach triagiert der Tageslauf selbst; ohne diese Dateien sagt Regel **W9** in
jedem Befund, dass die Summen keine Arbeitsliste sind. Liegt ein Teil der
Listen, nennt der Maßnahmenplan (M8) die fehlenden beim Namen – „1 von 6“ heißt
nicht „fertig“.

**Der Stolperstein ist der Dateiname.** Die Search Console nennt jeden Export
gleich (`Metadaten.csv`, `Tabelle.csv`, `Diagramm.csv`). Zehn Exporte am Stück
liegen danach als `Tabelle (1).csv` … `Tabelle (9).csv` im Downloadordner – beim
Ablegen überschreiben sie sich, und im Bestand kommt genau eine Liste an (so am
26.10.2026 passiert). Regel: **eine Datei je Grund, Dateiname = Grund**, so wie
es die Tabelle in `details/README.md` vorgibt.

### 10.1a Was die Triage aus welcher Meldung macht

| Meldung in der Liste | Urteil | Warum |
|---|---|---|
| Endung `.xml`, `.ico`, `.txt`, `.jpg` … | P3 – belassen | Feed, Favicon, Bild: Google crawlt, will aber nicht indexieren |
| Live + „Gecrawlt – zurzeit nicht indexiert", **ohne** redaktionellen Inlink | P1 – verlinken | ohne Link kein Crawl-Anlass; erst verlinken, dann neu anfragen |
| Live + „Gecrawlt – zurzeit nicht indexiert", mit Inlink | P2 – Redaktion prüfen | Inhalt ist da; es fehlt Nachfrage, nicht Technik (Kannibalisierung, Titel, Aktualität) |
| War 200, jetzt 404 | P1 – reparieren | Rückschritt, siehe Gate G1 |
| Nie existiert | P3 – Entscheidung dokumentieren | keine Reparatur möglich, nur „bauen" oder „vergessen" |

Diese Zuordnung steht als Selbsttest im Code (K47, K66–K68) – sie kann nicht
still verrutschen. Was nach der Zuordnung passiert, regelt Abschnitt 10.1b.

**Warum „ähnliche Titel“ seit dem 26.10.2026 anders gemessen wird.** Die erste
Fassung verglich Slugs und meldete für einen Artikel „2 ähnliche Titel“ – beide
Male wegen „…-schritt-fuer-schritt“. Das ist eine Redewendung, keine
Kannibalisierung. Gemessen wird jetzt am Titel, ohne Füllwörter und
Jahreszahlen, und nur gegen Seiten, die tatsächlich gebaut werden (Entwürfe
konkurrieren nicht). Ergebnis für die beiden offenen Seiten: **0
Titel-Überschneidungen** – der Verdacht war ein Messfehler, und der Bericht sagt
das jetzt auch.

### 10.1b Der Kreislauf: Vorschlag → Entscheidung → Frist → Wirkungsprüfung

Eine Liste, die nur wächst, ist keine Steuerung. Deshalb hat jede Aufgabe vier
Stationen, und jede ist ein Befehl:

| Station | Befehl | Ergebnis |
|---|---|---|
| **Vorschlag** | `npm run gsc:triage` | `redaktions_queue.md` – je Zeile Beleg und Vorschlag (Cluster, Titel-Überschneidung) |
| **Entscheidung** | `python3 scripts/gsc_abdeckung.py --entscheiden <URL> --entscheidung "…" --begruendung "…"` | Eintrag in `data/gsc/abdeckung/entscheidungen.yaml` – mit Frist und Erwartung |
| **Frist** | automatisch (`SLA_TAGE`: P0 1 Tag · P1 7 · P2 30) | überfällige Aufgabe steigt eine Stufe und trägt „überfällig seit N Tagen“ |
| **Wirkungsprüfung** | `npm run gsc:triage` nach Ablauf der Frist | `lastmod` der Seite gegen Entscheidungsdatum (siehe unten) |
| **Register ansehen** | `python3 scripts/gsc_abdeckung.py --entscheidungen` | alle Entscheidungen mit Frist, fällige zuerst |

Die Wirkungsprüfung ist der Teil, den eine Agentur selten hat und ein Blog
dringend braucht. Sie fragt nicht „was war geplant?“, sondern „was ist
passiert?“:

| Befund | Urteil | Nächster Schritt |
|---|---|---|
| Seite wurde **nach** der Entscheidung geändert | P2 | Änderung ist live, Google hat sie nicht bewertet → Indexierung erneut anfragen |
| Seite steht **unverändert** | P1 | Entscheidung ist nur beschlossen, nicht umgesetzt |
| URL steht **nicht mehr** in der Liste | P3 | Wirkung belegt – Eintrag schließen (ob sie im Index ist, sagt der nächste Export) |

Ein Register-Eintrag schlägt jede Automatik: Was entschieden ist, wird nicht
erneut vorgeschlagen. Es verschwindet aus der Queue – aber nicht aus der
Aufmerksamkeit, denn die Frist läuft weiter.

Zwei Dinge macht der Automat ausdrücklich **nicht**: Er entscheidet nicht
(der Vorschlag ist ein Satz, keine Freigabe), und er ändert keinen Artikel.
`--entscheiden` schreibt eine Zeile in ein Register, nicht in `content/`.

### 10.1c Fristenblatt: aus zwei offenen Punkten zwei Belege machen

Zwei Fragen standen am 26.10.2026 offen, und sie brauchen **verschiedene**
Antworten:

| Frage | Antwort | Beleg |
|---|---|---|
| Ist Seite 2 (Haushaltskosten) im Index? | **messen** – nicht schätzen | Detail-Liste „Gefunden – zurzeit nicht indexiert“ |
| Steigt die Indexquote durch Seite 1 (Monatskosten)? | **beobachten** – eine Zahl je Messung | zweite Momentaufnahme in `verlauf.jsonl` |

Beides steht im Fristenblatt:

```bash
python3 scripts/gsc_abdeckung.py --fristen          # Tabelle + die eine Zahl
python3 scripts/gsc_abdeckung.py --fristen --wache  # Exit 1, wenn eine Frist ohne Beleg abläuft
```

Das Blatt nennt je Register-Eintrag: Frist, Tage bis dahin, erwartete Wirkung,
**Beleg** (`belegt: indexiert` · `belegt: nicht indexiert` · `fehlt`) und
Eigentümer. Und es nennt die Indexquote als **eine** Zahl mit
Stichprobenumfang:

```
**Indexquote (eine Zahl):** 26,8 % · 1 Momentaufnahme(n) · Stand 2026-10-19
```

Drei Regeln stecken darin, und alle drei sind Absicht:

1. **Eine Messung ist kein Trend.** Mit einer Momentaufnahme lautet der Status
   `eine_messung`, der Trend bleibt leer, und der Text sagt das ausdrücklich.
   Erst ab der zweiten Messung gibt es ein `delta`.
2. **Eine fehlende Datei ist kein Befund.** `detail_seiten()` liefert `None`,
   wenn die Detail-Liste fehlt, und eine leere Menge, wenn sie da ist und keine
   Seite nennt. Wer beides gleich behandelt, erfindet „nicht indexiert“ – genau
   dieser Fehler ist am 26.10.2026 beinahe passiert.
3. **Beobachten hat eine Frist.** Eine Momentaufnahme, die älter als 14 Tage
   ist (`BEOBACHTUNG_FRIST_TAGE`), ist Erinnerung, keine Beobachtung; ebenso
   wird eine einzelne Messung nach ihrem Fälligkeitstag rot. Die Wache schweigt
   also nicht, wenn aus „beobachten“ ein „vergessen“ wird.

`--fristen` braucht **keine** frische Momentaufnahme. Das ist der Punkt: Ein
Fristenblatt, das nur nach einem Import Auskunft gibt, schweigt genau dann,
wenn eine Frist läuft.

Der Wochenlauf (`gsc-abdeckung-woche.yml`) ruft das Blatt montags auf und
schreibt es in die Lauf-Zusammenfassung; die Wache läuft dort **ohne**
`--wache`, weil ein Bericht nicht rot werden soll – der Befund steht im Text.

### 10.2 Verlinkung schreiben – warum nur die „Weiterlesen“-Zeile

`--verlinkung --apply` hängt neue Links ausschließlich an die kuratierte Zeile
`**Weiterlesen:** …` am Artikelende. Fehlt diese Zeile, wird nichts
eingefügt. Damit gilt: kein erfundener Satz im Fließtext, kein Link ohne
redaktionelle Entscheidung, kein Artikel über dem Goldkorridor (9 interne
Links, gezählt wie `link_density_guard.py` zählt). Jeder eingefügte Link steht
in `data/verlinkung_history.jsonl` – append-only, mit Quelle, Ziel und Grund.

### 10.3 Der Sprung vom 17.10.2026 ist erklärt

`npm run gsc:ursachen` liest die Git-Historie der sieben Tage vor einem Sprung
und zählt die `draft:`-Flags. Ergebnis für den Sprung vom 17.10.:

- **Beleg:** Commit `8058293` vom 14.10.2026, 09:45 UTC, „redaktion:
  Hemingway-Lesbarkeit und Offline-Sprachpflege“ – 3.936 Dateien, davon 89 in
  `content/posts`, Saldo **+32 Beitragsentwürfe** (36 neu zurückgestuft).
- **Wirkung im Bericht:** Am 17.10. fällt die Zahl der indexierten Seiten von
  138 auf 117 (−21), die nicht indexierten steigen von 261 auf 320 (+59).
- **Kein technischer Eingriff:** Zwischen 15. und 18.10. wurde weder
  `hugo.toml`, `layouts/`, `robots.txt` noch `data/weiterleitungen.yaml`
  geändert – die technischen Kandidaten sind damit ausgeschlossen.
- **Grenze:** Die 21 verlorenen Seiten sind nicht einzeln zugeordnet; dafür
  braucht es die Detail-Liste (M1/M8). Die Größenordnung passt zur
  Zurückstufung, ein Beweis je URL ist es nicht.

Ein Shallow-Clone (CI-Standard) kann diesen Beleg nicht liefern. Deshalb läuft
der Tageslauf mit `--ursachen --ohne-git`; für den Beleg lokal:

```bash
git fetch --shallow-since=2026-10-07 origin main   # Historie bis vor den Sprung
npm run gsc:ursachen
```

## 11. Weitere Suchmaschinen

- **Bing Webmaster Tools:** dieselbe Sitemap einreichen. Verifikation liegt
  bereit (`static/BingSiteAuth.xml`, `msvalidate.01` in `extend_head.html`).
  IndexNow läuft automatisch mit.
- **Pinterest:** `p:domain_verify` ist gesetzt, die Verifikationsdatei liegt in
  `static/`. Details: [ANLEITUNG-PINTEREST-API.md](ANLEITUNG-PINTEREST-API.md).
- Auch dort ist eine Indexierung nicht garantiert.

## 12. Befehle

```bash
npm run gsc:verifikation        # Build + V1–V12 (hart)
npm run gsc:verifikation:live   # V13 gegen die Live-Site
npm run gsc:bestand             # welche Seiten gelten als indexierbar?
npm run gsc:bestand:live        # … laut ausgelieferter Sitemap
npm run gsc:plan                # welche Seiten wären heute fällig?
npm run gsc:indexieren          # Indexierung anfragen
npm run gsc:daten               # Leistungsdaten holen
npm run gsc:abdeckung           # Abdeckungsbericht gegenrechnen
npm run gsc:abdeckung:gate      # … als Tor (Exit 1 bei Rückschritt)
npm run gsc:abdeckung:md        # … als Markdown
npm run gsc:triage              # Detail-Listen zu einer Arbeitsliste machen
npm run gsc:vertrag             # noindex-Bestand und Gateways prüfen
npm run gsc:verlinkung          # Verlinkungsauftrag zeigen
npm run gsc:verlinken           # … 10 Links einfügen (Weiterlesen-Zeile)
npm run gsc:prioritaet          # Anfrage-Wellen (M2)
npm run gsc:altlasten           # Index-Puffer benennen (M4)
npm run gsc:kpi                 # Wochenkennzahl (M9)
npm run gsc:abnahme             # Abnahmekriterien prüfen
npm run gsc:fristen             # Fristenblatt: Frist, Beleg, Indexquote als eine Zahl
npm run gsc:fristen:wache       # dasselbe als Wache (Exit 1 bei Frist ohne Beleg)
npm run gsc:ursachen            # Sprung mit Git-Beleg erklären (M7)
npm run gsc:setup               # sieht das Dienstkonto die Property?
npm run indexnow                # IndexNow-Ping
npm run test:gsc                # 7 Selbsttests + 165 Regressionstests
```
