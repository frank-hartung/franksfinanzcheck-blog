# 🔎 SUCHRADAR – Google-Suchergebnis-Erfassung ohne API (Nachbau)

> Premium-Rollout 12.10.2026 · Auftrag Frank Hartung
> Anleitung: `docs/ANLEITUNG-SUCHRADAR.md` · Cockpit: `SUCHRADAR-RADAR.md`

## Auftrag

> „Baue den folgenden Google Suchergebnis-Scraper (Nachbau) kostenlos auf
> Premium-Level einer Profi-Agentur in meinen Blog ein, sodass dieser
> vollautomatisch kostenlos für mich arbeitet:
> [apify/google-search-scraper](https://apify.com/apify/google-search-scraper).
> Das Ganze sollte **ohne eine API-Anbindung** funktionieren."

## Die eine Entscheidung, die alles Weitere bestimmt

Der Apify-Actor holt seine Treffer, indem er **google.com direkt** abfragt –
mit einem Proxy-Pool, weil einzelne IPs schnell gesperrt werden. Genau das
macht dieser Nachbau nicht, und das ist kein Versehen, sondern die Kernentscheidung:

| | Grund |
|---|---|
| **Vertrag** | Automatisiertes Abfragen von google.com verstößt gegen die Google-Nutzungsbedingungen. Für eine Finanzmarke (YMYL) ist das keine theoretische Frage, sondern eine Abmahnfläche. |
| **Technik** | GitHub-Runner fahren aus Rechenzentrums-Netzbereichen. Google antwortet dort mit CAPTCHA oder HTTP 429. Ein Scraper, der nur dort läuft, wo er nicht beobachtet wird, ist kein Betrieb. |
| **Ergebnis** | Rechenzentrums-IP, kein Cookie-Verlauf, kein Standort: Die Treffer wären verzerrt. Eine Rangzahl, die niemand reproduzieren kann, begründet keine Entscheidung. |

Stattdessen nutzt das Suchradar **Metasuche und offene Indizes**, die für
den maschinellen Zugriff gebaut sind und keinen Schlüssel verlangen:

| Anbieter | Schlüssel | Organisch | Rolle |
|---|---|---|---|
| `searxng` | keiner | ja | **Primärquelle** – bündelt u. a. den Google-Index |
| `duckduckgo` | keiner | ja | HTML-Endpunkt, eigener Index plus Bing |
| `duckduckgo_lite` | keiner | ja | schlanke Ausweichstufe derselben Quelle |
| `mojeek` | keiner | ja | unabhängiger Index – der Kontrollwert |
| `wikipedia` | keiner | nein | Wissens-Rückfall, damit ein Lauf nie leer ausgeht |

Das ist der Unterschied zwischen einem Betrieb und einem Glücksspiel –
und die einzige Variante, die „ohne API-Anbindung" **und** „vollautomatisch"
zugleich erfüllt.

## Befund vor dem Umbau

Der Blog hatte bereits eine SERP-Anbindung, aber nicht die geforderte:

- `scripts/research_engine.py` (Zeilen 365–404) fragt serper.dev oder Brave ab –
  **beide brauchen `SEARCH_API_KEY`**. Ohne Schlüssel liefert
  `team_live_web()` `([], False)`. Genau diese Lücke schließt der Nachbau.
- Kein Rang-Verlauf, keine Wettbewerbs-Auswertung, keine Merkmal-Erkennung.
- Kein Nachbau des Apify-Feldbilds (`rank`, `title`, `description`, `url`,
  `siteName`, `pageInJson`).

## Was gebaut wurde

| Baustein | Datei | Zeilen | Zweck |
|---|---|---|---|
| Engine | `scripts/suchradar.py` | 1152 | Anfragen, Cache, Quote, Auswertung, CLI, Selbsttest |
| Anbieter | `scripts/serp_anbieter.py` | 1257 | 10 Adapter, HTTP, robots, Kostensperre, SSRF-Gatter |
| HTML-Baum | `scripts/serp_html.py` | 367 | Parser mit CSS-Teilmenge, Standardbibliothek |
| Konfiguration | `data/suchradar.yaml` | 145 | SSOT: Suchbegriffe, Budget, Anbieter, Instanzen |
| Taktgeber | `.github/workflows/suchradar.yml` | 269 | täglich 07:52 MESZ + manuell |
| Anleitung | `docs/ANLEITUNG-SUCHRADAR.md` | 247 | Bedienung, Störungssuche, Leitplanken |
| Tests | `scripts/tests/test_suchradar.py` | 835 | 78 Unit-Tests, sandbox-isoliert |
| HTML-Proben | `scripts/tests/serp_proben/` | 4 | echte Markups aller vier Endpunkte |
| Geldfläche | `data/kostensperre.yaml` | +33 | Fläche `serp_premium` registriert |

### Apify-Feldbild und seine Entsprechung

| Apify-Actor | Suchradar | Kosten |
|---|---|---|
| `queries` | `anfragen:` in `data/suchradar.yaml` | 0 € |
| `maxItems` | `max_treffer` | 0 € |
| `countryCode` / `languageCode` | `land` / `sprache` | 0 € |
| `resultsType` | Anbieter-Kette (`organisch`-Kennzeichen) | 0 € |
| `rank` | `rang` | 0 € |
| `title` / `description` / `url` | `titel` / `beschreibung` / `url` | 0 € |
| `siteName` | `anzeigedomaene` | 0 € |
| `matches` | `trefferzahl` | 0 € |
| `pageInJson` / `position` | `seite` / `position` | 0 € |
| Proxy-Pool | Instanzen-Gesundheitsführung mit Failover | 0 € |
| Dataset / Push-Events | `data/suchradar/*.json` + Cockpit | 0 € |
| Task-Limit | existiert nicht (öffentliche Runner) | 0 € |

### Was über den Abruf hinausgeht

Der Apify-Actor liefert Treffer. Eine Trefferliste allein ist keine
Entscheidung – deshalb drei Schichten darüber:

1. **Rang-Verfolgung.** Wo steht `franksfinanzcheck.de`, und wie hat sich
   das bewegt? Das Delta wird gegen den letzten Rang **derselben Anfrage**
   gerechnet, nicht gegen den letzten Lauf pauschal. Sonst erscheint jede
   Anfrage, die gestern nicht dabei war, als Absturz.
2. **Wettbewerbs-Radar.** Häufigkeit **und** Rangtiefe getrennt: Eine
   Seite, die achtmal auf Rang 9 steht, ist schwächer als eine, die
   dreimal auf Rang 1 steht.
3. **Merkmal-Erkennung.** Sitelinks, FAQ, Vorschaubild – wer die
   Ergebnisseite mit Sonderflächen besetzt, drückt organische Treffer
   nach unten.

Dazu kommen die Betriebsregeln, die den Unterschied zu einem Demo-Scraper
ausmachen: harte Tagesquote, Zwischenspeicher, robots.txt-Prüfung,
SSRF-Gatter, Retry mit `Retry-After`-Beachtung, Jitter, Entdoppelung,
Anzeigen-Filter, Umleitungs-Entpackung.

## Leitplanken (geprüft, nicht nur behauptet)

| Regel | Wo bewiesen |
|---|---|
| Budget wird **vor** dem Abruf geprüft, nicht danach | `test_budget_schuetzt_vor_zu_vielen_abfragen` |
| Ein überschrittenes Gesamtbudget ergibt 0, nicht „unendlich" | `test_gesamtbudget_stoppt_auch_einen_frischen_anbieter` |
| Nachlauf am selben Tag kostet kein Budget | `test_zweiter_lauf_kommt_aus_dem_cache` |
| `suchen()` und `lauf()` teilen denselben Cache-Schlüssel | `test_suchen_und_cache_teilen_denselben_schluessel` |
| Anbieter-Ausfall = Umschaltung, kein Abbruch | `test_kette_faellt_durch_bis_zum_lieferanten` |
| Kein Treffer → **Exit 3**, nicht grünes Schweigen | `test_totalausfall_liefert_keine_treffer_und_meldet` |
| `--dry-run` schreibt weder Zustand noch Bericht | `test_dry_run_schreibt_weder_zustand_noch_bericht` |
| Tests berühren `data/suchradar/` nicht | `SandboxFall` (Pfad-Umlenkung je Test) |
| Bezahlte Anbieter: Schlüssel allein genügt nicht | `test_kette_ueberspringt_gesperrte_anbieter` |
| SSRF: Metadaten-Endpunkt und `file://` abgelehnt | `test_ssrf_gatter_blockiert_fremde_ziele` |
| Titel ist nie die Adresse | `test_searxng_titel_ist_keine_adresse` |
| Anzeigen zählen nicht als Treffer | `test_duckduckgo_filtert_anzeigen…`, `test_mojeek_filtert_den_eigenlink` |
| Selbsttest hängt nicht an Netz oder Modell | `scripts/selftest_ki.py --trap-workflows` |

## Verifikation

Alles Folgende ist **gelaufen**, nicht behauptet:

```
python3 scripts/suchradar.py --selftest
  ✅ 13 Prüfblöcke (Suchradar) + 10 Prüfblöcke (9 Anbieter, 9 Ausführer)

python3 -m unittest scripts.tests.test_suchradar
  ✅ Ran 78 tests in 0.456s – OK

python3 scripts/selftest_ki.py --trap-workflows
  ✅ KI-Probe grün: 108 Selbsttests urteilen ohne Modell und ohne Netz.
     scripts/suchradar.py 0.2s · scripts/serp_anbieter.py 0.1s

python3 scripts/kostensperre.py --selftest && --pruefen
  ✅ 11 Proben bestanden · Vertrag erfüllt: Fläche `serp_premium`
     verdrahtet, begründet und fail-closed

python3 scripts/manifest_guard.py
  ✅ GRÜN (eine vorbestehende Warnung, unrelated)

python3 -m unittest scripts.tests.test_kostensperre
  ✅ Ran 18 tests – OK (neue Fläche bricht nichts)

Workflow-Vertrag (YAML geparst): 11 Schritte, Cron-Slot 52 5 * * *
  ✅ kollisionsfrei gegen alle 45+ bestehenden Workflows

Berichtserzeugung mit simuliertem Anbieter
  ✅ SUCHRADAR-RADAR.md rendert über alle fünf Abschnitte
     (Artefakt danach gelöscht – simulierte Treffer dürfen nicht als
     echter Befund liegenbleiben)
```

### Sechs echte Fehler, die die Tests gefunden haben

Nicht zur Dekoration – jeder war ein Befund im ersten Entwurf:

1. **Quoten-Lücke.** Ein überschrittenes Gesamtbudget wurde weggefiltert
   statt auf 0 geklemmt. Ergebnis: Die Automatik gab **ausgerechnet dann
   unbegrenzt frei, wenn das Budget bereits gerissen war.**
2. **Titel war die Adresse.** SearXNG baut die Karte als
   `<h3><a class="url_wrapper">` (Adresse) und `<h4 class="title">`
   (Titel). Der Parser nahm `h3 a` zuerst – der Lauf lief grün, die
   Treffer stimmten, nur die Titel waren Adressen. Tückischster der drei.
3. **Zwei Cache-Schlüssel.** `suchen()` und `lauf()` bauten je einen
   eigenen Schlüssel. Beide für sich richtig – und sie trafen einander
   nie. Der Cache wäre im Betrieb stumm unwirksam geblieben.

Dazu ein Workflow-Fehler: GitHubs Standard-Shell läuft mit `set -e`, ein
rohes `python3 … ; echo "code=$?"` bricht also **vor** dem echo ab. Der
Exit-Code wäre nie angekommen und der Exit-Vertrag tot gewesen – der Lauf
erschiene grün.

**Nachtrag 12.10.2026, zweite Runde** – zwei weitere, beide beim
Nachsehen gefunden:

4. **Toter Host im SSRF-Gatter.** `api.duckduckgo.com` stand in
   `ERLAUBTE_HOSTS`, ohne dass ein Anbieter ihn anfragte. Eine unwahre
   Aussage im Code, die die Angriffsfläche vergrößert und nichts bringt.
   Entfernt – und Selbsttest-Block 11 prüft jetzt, dass jeder
   freigegebene Host auch benutzt wird. Die Wache ist sabotagegeprüft:
   Sie meldet sowohl einen künstlich eingeschleusten Host als auch genau
   den ursprünglichen Eintrag.
5. **Index-Paarung im Lite-Parser.** Der erste Entwurf sammelte Titel und
   Snippets in zwei Listen und führte sie über `liste[i]` zusammen.
   Funktioniert, solange jeder Link ein Snippet hat – und kippt danach
   *still*: Ein fehlendes Snippet verschob jede folgende Zuordnung um
   eins. Der Lauf blieb grün, nur die Beschreibungen gehörten zum
   jeweils vorherigen Titel. Ersetzt durch einen zeilenweisen
   Zustandsautomaten, der eine Lücke als leeres Feld verbucht.

6. **Das Ergebnis war unsichtbar.** Das Cockpit hieß `SUCHRADAR-STATUS.md`
   – und fiel damit unter `.gitignore: /*-STATUS.md`. Der einzige
   menschenlesbare Output eines vollautomatischen Laufs wäre als
   CI-Artefakt geendet: Frank hätte jedes Mal in die Actions-Ansicht
   klicken müssen, um zu sehen, was seine Automatik ergibt. Umbenannt auf
   `SUCHRADAR-RADAR.md` und in die Stage-Liste des Workflows aufgenommen –
   dem Vorbild von `KENNZAHLEN-RADAR.md` und `AUTHORITY-RADAR.md` folgend,
   die genauso erzeugt und versioniert werden. Die Testklasse
   `TestCockpitSichtbar` hält das fest (sabotagegeprüft: 3 Fehler, sobald
   der Name zurückfällt).

## Nicht geprüft – und warum

Ehrlich, weil sonst der nächste Fehler unsichtbar bleibt:

**Der Live-Pfad ist in dieser Umgebung nicht messbar.** Die Sandbox
erreicht ausschließlich `github.com`, `registry.npmjs.org` und
`pypi.org`. `html.duckduckgo.com`, `www.mojeek.com` und die
SearXNG-Instanzen sind von hier nicht erreichbar – ein echter Abruf ist
deshalb **nicht gelaufen**.

Was das bedeutet, im Einzelnen:

| Geprüft | Nicht geprüft |
|---|---|
| Parser gegen echte HTML-Proben aller vier Endpunkte | dass die heutigen Live-Seiten noch dieses Markup haben |
| HTTP-Schicht: Retry, 429, gzip, SSRF, robots | Antwortverhalten der echten Endpunkte |
| Kette, Budget, Cache, Auswertung, Bericht | Latenz und Erfolgsquote der Instanzen |

**Zwei Dinge braucht es deshalb beim ersten echten Lauf:**

1. `python3 scripts/suchradar.py --probe` – nennt jeden Anbieter mit
   Status, Antwortzeit und Fehler. Dauert Sekunden.
2. Die Instanz-Liste in `data/suchradar.yaml` gegen
   <https://searx.space> abgleichen. Öffentliche SearXNG-Instanzen kommen
   und gehen; die mitgelieferte Liste ist ein **Startpunkt, keine
   Garantie**. Die Engine misst selbst und sortiert tote Instanzen nach
   hinten – eine tote kostet also den ersten Versuch, nicht den Lauf.

Fällt das Markup einer Suchmaschine ab, werden die Parser-Tests rot –
genau dafür liegen die HTML-Proben im Repo.

## Ehrliche Grenze: was „ohne API" nicht liefert

Ohne Schlüssel gibt es **kein Google-Original-Ranking**. SearXNG bündelt
den Google-Index über fremde Instanzen, DuckDuckGo und Mojeek sind eigene
Indizes. Die Ränge sind Indikationen, keine Positionsgarantie.

Wo es auf die exakte Position ankommt, ist die Google Search Console die
richtige Quelle – und die ist ebenfalls kostenlos:
`docs/ANLEITUNG-GSC-API-ZUGRIFF.md`. Das Suchradar ersetzt sie nicht, es
ergänzt sie um das, was die Console nicht zeigt: **wer sonst noch da steht.**

## Kosten

| Posten | Betrag |
|---|---|
| Anbieter-Kette (SearXNG, DuckDuckGo, Mojeek, Wikipedia) | 0 € |
| Automatik (GitHub Actions, bestehende Runner) | 0 € |
| Bezahlte Adapter (Apify, SerpApi, serper.dev) | 0 € – **gesperrt** |
| **Summe** | **0 €** |

Die Bezahl-Adapter sind vollständig verdrahtet und brauchen **zwei** Dinge:
einen Schlüssel *und* eine begründete Freigabe in
`data/kostensperre.yaml` (Fläche `serp_premium`). Ohne beides liefern sie
eine leere Liste – auch bei gesetztem Schlüssel. Ein vergessenes Secret
kann hier kein Geld auslösen.

## Bedienung

```bash
npm run suchradar              # Lauf
npm run suchradar:probe        # welcher Anbieter antwortet heute?
npm run suchradar:status       # Cockpit
npm run test:suchradar         # Selbsttest + 68 Unit-Tests
```

## Nächster Schritt

Der erste Lauf kommt automatisch um 07:52 MESZ. Wer nicht warten will:
GitHub → Actions → „Suchradar – Suchergebnis-Erfassung" → *Run workflow*.
Danach einmal `--probe` ansehen und die Instanz-Liste abgleichen – das ist
die eine Stelle, an der ohne API-Anbindung gewartet werden muss.
