# ANLEITUNG SUCHRADAR – Suchergebnis-Erfassung ohne API

> Rollout 12.10.2026 · Engine: `scripts/suchradar.py` · Anbieter: `scripts/serp_anbieter.py`
> Auftrag: Nachbau des Apify-Actors [`apify/google-search-scraper`](https://apify.com/apify/google-search-scraper),
> **ohne API-Anbindung**, ohne Kosten, vollautomatisch.
> Bericht: `SUCHRADAR-GOOGLE-SERP-NACHBAU-PREMIUM-2026-10-12.md`

---

## Was das Suchradar tut

Ein Suchbegriff geht hinein, eine Ergebnisseite kommt heraus: Rang, Titel,
Beschreibung, Adresse, Sonderflächen. Darüber liegen drei Schichten, die
aus einer Trefferliste eine Entscheidungsgrundlage machen:

| Schicht | Was sie beantwortet | Datei |
|---|---|---|
| **Rang-Verfolgung** | Wo steht `franksfinanzcheck.de` – und wie hat sich das bewegt? | `data/suchradar/rankings.json` |
| **Wettbewerbs-Radar** | Welche Domänen besetzen die eigene Themenwelt? | `data/suchradar/wettbewerb.json` |
| **Merkmal-Erkennung** | Wer belegt die Ergebnisseite mit Sonderflächen? | im Wettbewerbs-Radar |

Der reine Abruf ist die halbe Sache. Eine Rangzahl ohne Vergleich mit dem
Vortag ist ein Momentaufnahme-Wert, aus dem sich nichts ableiten lässt –
deshalb wird die Historie versioniert und das Delta mitgerechnet.

## Bedienung

```bash
npm run suchradar                  # Lauf: suchen → messen → Cockpit schreiben
npm run suchradar:probe            # welcher Anbieter antwortet heute?
npm run suchradar:status           # Cockpit anzeigen
npm run suchradar:json             # Maschinenausgabe
npm run suchradar:probe-lauf       # --dry-run: suchen, nichts schreiben
npm run suchradar:cache            # abgelaufenen Zwischenspeicher löschen
npm run suchradar:selftest         # Offline-Selbsttest (13 Prüfblöcke)
npm run test:suchradar             # Selbsttest + 73 Unit-Tests
```

Ad-hoc, ohne Konfiguration:

```bash
python3 scripts/suchradar.py --anfrage "Stromanbieter wechseln" --anfrage "Gaskosten senken"
python3 scripts/suchradar.py --anfrage "Fixkosten senken" --max-anfragen 1
```

### Exit-Codes

| Code | Bedeutung | Reaktion |
|---|---|---|
| 0 | mindestens ein Anbieter lieferte Treffer | keine |
| 1 | harter Fehler (Konfiguration, Schreibzugriff) | Protokoll lesen |
| 3 | **kein einziger Treffer** – alle Anbieter ausgefallen | `--probe` ausführen |

Exit 3 ist Absicht. Ein leerer Bericht, der „alles in Ordnung" meldet, ist
die teuerste Variante dieses Fehlers – dieselbe Klasse wie Meldung #514.

## Konfiguration

Alles in `data/suchradar.yaml`. Die Werte, die man tatsächlich anfasst:

| Schlüssel | Wirkung |
|---|---|
| `eigene_domaene` | Wofür die Rang-Verfolgung misst |
| `anfragen` | Vorrang-Liste, wird jeden Tag gemessen |
| `max_anfragen_pro_lauf` | Anfragen je Lauf |
| `max_abfragen_pro_tag` | **Budget-Grenze** – hart durchgesetzt |
| `zwischenspeicher_stunden` | wie lange ein Ergebnis als frisch gilt |
| `reihenfolge` | Ausweichtiefe der Anbieter |
| `searxng_instanzen` | öffentliche Metasuch-Instanzen |

`max_abfragen_pro_tag` schützt nicht vor einer Rechnung – es gibt keine.
Es schützt fremde Server vor der eigenen Automatik: eine Endlosschleife,
die Suchmaschinen mit Anfragen überschüttet, ist ein Sperrproblem.

## Automatik

`.github/workflows/suchradar.yml` läuft täglich um **07:52 MESZ**:

1. Selbsttest – fail-closed, bevor eine Anfrage rausgeht
2. Unit-Tests – Budget, Cache, Kette, Parser
3. Anbieter-Probe – wer antwortet heute?
4. Suchlauf
5. Zustand committen (Quote, Instanzen-Gesundheit, Rang-Historie)
6. Meldung bei Totalausfall, sonst nichts

Das Cockpit `SUCHRADAR-RADAR.md` wird **mit committet** – das Ergebnis
steht also im Repo und nicht nur als CI-Artefakt. Es heißt bewusst nicht
`*-STATUS.md`: Die .gitignore-Regel `/*-STATUS.md` würde es verschlucken.
Vorbild sind `KENNZAHLEN-RADAR.md` und `AUTHORITY-RADAR.md`, die genauso
erzeugt und versioniert werden.

Der Zustand unter `data/suchradar/` ist dagegen versioniert. Ohne die
Rang-Historie gibt es kein Delta zum Vortag, und ohne die Quote gibt es
keine Budget-Grenze über Läufe hinweg. Der Zwischenspeicher
(`data/suchradar/cache/`) ist ignoriert – er ist flüchtig.

## Anbieter und warum diese

| Anbieter | Schlüssel | Organisch | Rolle |
|---|---|---|---|
| `searxng` | keiner | ja | **Primärquelle.** Metasuche, bündelt u. a. den Google-Index |
| `duckduckgo` | keiner | ja | HTML-Endpunkt, eigener Index plus Bing |
| `duckduckgo_lite` | keiner | ja | schlanke Ausweichstufe derselben Quelle |
| `mojeek` | keiner | ja | unabhängiger Index – der Kontrollwert |
| `wikipedia` | keiner | nein | Wissens-Rückfall, damit ein Lauf nie leer ausgeht |
| `google_cse` | ja | ja | offizieller Google-Weg, 100 Abfragen/Tag frei |
| `brave` | ja | ja | 2.000 Abfragen/Monat frei |
| `serper` | ja | ja | bezahlt – gesperrt |
| `serpapi` | ja | ja | bezahlt – gesperrt |
| `apify` | ja | ja | **das Original** – gesperrt, für Vergleichsmessungen |

### Warum nicht einfach google.com scrapen

Der Apify-Actor tut genau das, mit einem Proxy-Pool. Dieser Nachbau tut es
nicht. Drei Gründe, in dieser Reihenfolge:

1. **Vertrag.** Automatisiertes Abfragen von google.com verstößt gegen die
   Google-Nutzungsbedingungen. Für eine Finanzmarke (YMYL) ist das keine
   theoretische Frage, sondern eine Abmahnfläche.
2. **Technik.** GitHub-Runner fahren aus Rechenzentrums-Netzbereichen.
   Google antwortet dort mit CAPTCHA oder HTTP 429. Ein Scraper, der nur
   dort funktioniert, wo er nicht beobachtet wird, ist kein Betrieb.
3. **Ergebnis.** Selbst wenn es liefe: Rechenzentrums-IP, kein
   Cookie-Verlauf, kein Standort. Die Treffer wären verzerrt – und eine
   Rangzahl, die niemand reproduzieren kann, ist keine Entscheidungsgrundlage.

Metasuche und offene Indizes sind für den maschinellen Zugriff gebaut.
Das ist der Unterschied zwischen einem Betrieb und einem Glücksspiel.

### Bezahlte Anbieter entsperren

Sie sind vollständig verdrahtet, brauchen aber **zwei** Dinge: einen
Schlüssel *und* eine Freigabe in `data/kostensperre.yaml`.

```yaml
# data/kostensperre.yaml → flaechen[serp_premium]
freigegeben: true
grund: "Vergleichsmessung gegen das Apify-Original, befristet bis …"
datum: "2026-11-01"
```

Ohne beides liefern sie eine leere Liste – auch bei gesetztem Schlüssel.
Ein vergessenes Secret kann hier kein Geld auslösen. Kontrolle:
`python3 scripts/kostensperre.py --pruefen`.

## Störungssuche

### Kein Anbieter liefert Treffer (Exit 3)

```bash
python3 scripts/suchradar.py --probe
```

Das nennt jeden Anbieter einzeln mit Status, Antwortzeit und Fehler.

| Befund | Ursache | Lösung |
|---|---|---|
| alle SearXNG-Instanzen `fehler` | Instanzen offline | Liste in `data/suchradar.yaml` gegen <https://searx.space> abgleichen |
| `duckduckgo` leer, `duckduckgo_lite` ok | HTML-Endpunkt blockt, Lite nicht | nichts – die Kette macht genau das |
| beide DuckDuckGo-Wege leer | Markup-Änderung oder Ratenlimit | Parser-Tests laufen lassen, Abstand erhöhen |
| alle `fehler` mit „robots.txt verbietet" | Regel der Quelle | Anbieter aus `reihenfolge` nehmen |
| alles ok, aber Lauf leer | Budget erschöpft | `data/suchradar/quota.json` prüfen |

### Eine SearXNG-Instanz ergänzen

In `data/suchradar.yaml` unter `searxng_instanzen` eintragen. Der Host muss
zusätzlich für das SSRF-Gatter freigegeben werden – das geschieht
automatisch über `instanzen_zulassen()`, sobald die Konfiguration gelesen
wird. Eine Instanz, die nicht in der Liste steht, wird nicht angefragt.

Voraussetzung: Die Instanz muss entweder `format=json` erlauben oder
HTML liefern. Beides wird versucht, JSON zuerst.

### Budget ist erschöpft

```bash
python3 -c "import json;print(json.load(open('data/suchradar/quota.json')))"
```

Der Zähler setzt sich zum Tageswechsel selbst zurück. Für einen sofortigen
Neustart: den Eintrag des laufenden Tages entfernen – oder
`--max-anfragen` senken.

### Parser greifen ins Leere

Suchmaschinen bauen ihr Markup laufend um. Die Parser sind gegen echte
HTML-Proben getestet:

```bash
python3 -m unittest scripts.tests.test_suchradar
ls scripts/tests/serp_proben/     # duckduckgo.html, searxng.html, mojeek.html
```

Fällt ein Test, ist die Probe veraltet: aktuelle Seite speichern,
Probe ersetzen, Selektoren in `scripts/serp_anbieter.py` anpassen.

## Leitplanken

- **Der Schlüssel ist eine Quelle, kein Ziel.** `max_abfragen_pro_tag`
  wird *vor* dem Abruf geprüft, nicht danach.
- **Instanzen-Gesundheit ist Gedächtnis.** Jede Antwort wird gemessen;
  die Reihenfolge folgt der Erfolgsquote. Ungemessene Instanzen sortieren
  sich *zwischen* bewährte und ausgefallene – nicht nach vorn, nicht nach hinten.
- **Ein Anbieter-Ausfall ist eine Umschaltung**, kein Laufabbruch. Kein
  Anbieter liefert etwas → Exit 3, nicht grünes Schweigen.
- **Interne Kennzeichen bleiben intern.** `instanz:…` und `engine:…`
  steuern die Auswertung, erscheinen aber nicht im Bericht.
- **Anzeigen zählen nicht.** `result--ad`, `result_ad` und die
  `duckduckgo.com/y.js`-Links von Lite fallen raus – sonst misst das
  Radar ein Werbebudget statt eines Rankings.
- **Kein freigegebener Host ohne Ausführer.** Selbsttest-Block 11 in
  `scripts/serp_anbieter.py` prüft, dass jeder Eintrag in
  `ERLAUBTE_HOSTS` auch angefragt wird. Ein toter Eintrag ist eine
  unwahre Aussage im Code und vergrößert die Angriffsfläche um nichts.
- **Umleitungen werden ausgepackt.** DuckDuckGo liefert `/l/?uddg=…`;
  ohne Entpacken zählte die Wettbewerbs-Auswertung nur duckduckgo.com.
- **`--dry-run` schreibt nichts.** Weder Zustand noch Cache noch Bericht.
- **Kein Treffer wird ungeprüft übernommen.** Das Radar misst; die
  Entscheidung trifft Frank. Fremde Titel sind urheberrechtlich geschützt.

## Ehrliche Grenze

Ohne Schlüssel gibt es **kein Google-Original-Ranking**. SearXNG bündelt
den Google-Index über fremde Instanzen, DuckDuckGo und Mojeek sind eigene
Indizes. Die Ränge sind Indikationen, keine Positionsgarantie.

Wo es auf die exakte Position ankommt, ist die Google Search Console die
richtige Quelle – und die ist ebenfalls kostenlos:
`docs/ANLEITUNG-GSC-API-ZUGRIFF.md`.

## Dateien

| Datei | Zweck | versioniert |
|---|---|---|
| `scripts/suchradar.py` | Engine, Auswertung, CLI, Selbsttest | ja |
| `scripts/serp_anbieter.py` | Anbieter-Adapter, HTTP, Kostensperre | ja |
| `scripts/serp_html.py` | HTML-Baum mit CSS-Teilmenge | ja |
| `data/suchradar.yaml` | Konfiguration (SSOT) | ja |
| `data/suchradar/quota.json` | Tagesbudget je Anbieter | ja |
| `data/suchradar/instanzen.json` | Gesundheitsführung der Instanzen | ja |
| `data/suchradar/rankings.json` / `.jsonl` | Rang-Stand und Historie | ja |
| `data/suchradar/wettbewerb.json` | Wettbewerbs-Radar | ja |
| `data/suchradar/verlauf.jsonl` | Lauf-Protokoll | ja |
| `data/suchradar/cache/` | Zwischenspeicher | nein |
| `SUCHRADAR-RADAR.md` | Cockpit | **ja** (erzeugt, committet) |
| `scripts/tests/serp_proben/` | HTML-Proben der Parser-Tests | ja |
| `.github/workflows/suchradar.yml` | tägliche Automatik | ja |
