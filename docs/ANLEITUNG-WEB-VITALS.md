# Web Vitals: Labor, Feld und die ausgelieferte Seite

**Ziel:** Core Web Vitals dort messen, wo sie zählen – bei echten Besuchern –
und die Laborwerte der **ausgelieferten** Seite danebenlegen, statt sie mit
einem Varianten-Build zu verwechseln.

## Warum es diese Messung gibt (26.10.2026 · gehärtet 03.11.2026, #1026)

Das Haus hatte drei Messungen und keine davon sah Produktion:

| Messung | Was sie sieht | Blinder Fleck |
|---|---|---|
| `scripts/cwv_guard.py` | den statischen Baum (Bytes, Bilder, JS) | kein Rendering, keine Zeit |
| `design-varianten.yml` + `lighthouserc.cjs` | Varianten-Builds unter `.cache/design-varianten/<id>/public` | Entwürfe, nicht die Website |
| `lighthouse/assertions.json` | Schwellen (eine Wahrheit für alle Labore) | ohne Verbraucher wirkungslos |

Die Seite, die ein Besucher über Cloudflare lädt, wurde von keinem Gate
gemessen. Das ist die Lücke, die zwei Werkzeuge schließen – mit klarer
Rollenverteilung:

- **Felddaten (verbindlich):** `scripts/cwv_feld_wache.py` liest den Chrome UX
  Report (CrUX) über PageSpeed Insights. Das sind echte Besucher, gemessen von
  Google.
- **Labor live (Diagnose):** `scripts/lighthouse_live.mjs` misst dieselben URLs
  mit denselben Schwellen wie das Varianten-Gate und sagt, **welche** Grenze
  reißt.

## Die Woche (`WF-0032`)

Workflow: `.github/workflows/web-vitals-woche.yml` – montags 05:47 UTC
(≈ 07:47 Berlin), nach dem GSC-Lauf, plus manuell auslösbar (`strategie`:
`mobile` oder `desktop`). Der Lauf ist read-only: Berichte gehen als Artefakt
(`web-vitals-woche`) und in die Lauf-Zusammenfassung, nicht in den Bestand. Ein
Wochenlauf, der Commits erzeugt, wäre selbst eine Änderungsquelle am
Messgegenstand.

```text
Felddaten  →  Befund (Exit 1)   ⇒ Lauf rot (web-vitals-befund)   – echte Besucher betroffen
           →  Störung (Exit 2)  ⇒ Lauf rot (web-vitals-stoerung) – ungeprüft / API gestört (C2)
Labor      →  Befund / Störung  ⇒ Warnung im Lauf, Bericht       – Diagnose, kein Blocker
```

Architektur-Garantien seit der Dauerheilung #1026
(`WARTUNG-TECHNIK-WF-0032-1026-DAUERHEILUNG-HIGHEND-2026-11-03.md`):

1. **Paketfreie Importierbarkeit:** `scripts/lighthouse_live.mjs` importiert am
   Dateikopf ausschließlich Node-Bordmittel; `lighthouse`, `playwright-core`
   und `e2e/browser.mjs` werden erst beim echten Browserlauf über
   `ladeLaufzeit()` nachgeladen. Der Workflow beweist das vor `npm ci` mit
   `test ! -d node_modules`.
2. **Entkoppelte Pfade:** Feld-Selbsttest und Feldmessung laufen **vor** dem
   Laborpfad. Ein Defekt am Diagnose-Werkzeug kann die verbindliche
   CrUX-Messung niemals überspringen.
3. **Deterministisches Exit-Capturing:** Beide Messschritte fangen Nicht-Null-
   Exits explizit über `|| rc=$?` unter `bash -eo pipefail` ab (kein
   `continue-on-error` mit stillem Abbruch vor `$GITHUB_OUTPUT`).

## Offline-Selbsttests & Vertragstests (ohne Netz, ohne `node_modules`)

```bash
npm run test:webvitals
npm run test:cwv:feld
npm run test:cwv:labor
node scripts/lighthouse_live.mjs --selftest
python3 scripts/cwv_feld_wache.py --selftest
```

`scripts/tests/test_web_vitals_workflow.py` kopiert das Lighthouse-Werkzeug in
einen nackten Temp-Ordner ohne `node_modules` und führt zusätzlich die echten
Shell-Blöcke aus `.github/workflows/web-vitals-woche.yml` unter
`bash -eo pipefail` aus.

## Felddaten messen

```bash
python3 scripts/cwv_feld_wache.py                  # Bericht auf stdout
python3 scripts/cwv_feld_wache.py --schreiben      # + data/cwv/feld/{befund.json,befund.md,verlauf.jsonl}
python3 scripts/cwv_feld_wache.py --json           # Maschinenausgabe
python3 scripts/cwv_feld_wache.py --ziel /cockpit/ --ziel /werkzeuge/
python3 scripts/cwv_feld_wache.py --strategie desktop
python3 scripts/cwv_feld_wache.py --fixture antwort.json --datum 2026-10-26
python3 scripts/cwv_feld_wache.py --selftest       # ohne Netz, ohne Schreiben
```

Ziele stehen in `data/cwv/feld_ziele.json` – bewusst kurz: Felddaten entstehen
nur dort, wo echte Besucher messbar sind. Aktuell: Startseite, Werkzeuge-Hub,
Cockpit, Fixkosten-Scanner, 24-Monats-Effektivpreis.

**Schlüssel & Rate-Limit-Schutz:** `PSI_API_KEY` (optional, als GitHub-Secret).
Ohne Schlüssel drosselt Google geteilte Runner-IPs streng (`HTTPError 429`);
`cwv_feld_wache.py` fängt transiente Antworten (`408`/`429`/`5xx`, Zeitlimit)
mit begrenztem Backoff inkl. `Retry-After` ab und taktet Live-Ziele schonend.
Der Schlüssel wird in jeder Fehlermeldung und URL geschwärzt (`[GESCHWAERZT]`)
und nie ausgegeben, geloggt oder gespeichert.

### Wie bewertet wird

Die Bewertung kommt **aus der API** (`category`: `FAST` / `AVERAGE` / `SLOW` →
`GUT` / `VERBESSERUNGSWUERDIG` / `SCHLECHT`). Damit gibt es keine zweite,
erfundene Schwelle im Repo – 2,5 s / 200 ms / 0,1 sind Googles Definition, und
Google liefert das Urteil gleich mit.

- Das **schlechteste** Einzelurteil bestimmt das Seitenurteil. Eine Seite mit
  gutem LCP und schlechtem INP ist nicht „gut".
- **Keine Felddaten = UNGEPRÜFT**, niemals GRÜN. Eine neue Seite mit zu wenig
  Traffic wird nicht als gesund geführt.
- **Keine einzige geprüfte Seite = STÖRUNG** (Exit 2, Hausregel C2). `befund.json`
  und Bericht nennen `stoerung_grund`:
  - `keine_crux_daten`: PageSpeed Insights hat für alle Ziele geantwortet, im
    28-Tage-CrUX-Fenster liegen aber noch keine Besucherdaten vor (kein
    technischer Defekt, kein Code-Eingriff nötig).
  - `teilabruf_fehlgeschlagen` / `abruf_fehlgeschlagen`: API-/Netzfehler oder
    Rate-Limit (`HTTPError 429` → Secret `PSI_API_KEY` hinterlegen).

Exit: `0` kein Feldbefund · `1` Befund (mindestens eine Seite `SCHLECHT`) ·
`2` Störung (Netz, API oder 0 Ziele mit CrUX-Daten).

## Laborwerte der ausgelieferten Seite

```bash
node scripts/lighthouse_live.mjs --selftest           # offline & ohne node_modules
node scripts/lighthouse_live.mjs                      # Ziele aus data/cwv/feld_ziele.json
node scripts/lighthouse_live.mjs --url https://franksfinanzcheck.de/werkzeuge/
node scripts/lighthouse_live.mjs --laeufe 3 --schreiben
node scripts/lighthouse_live.mjs --json               # Maschinenausgabe
node scripts/lighthouse_live.mjs --streng             # Befund ⇒ Exit 1 (nur wenn bewusst gewollt)
```

- Schwellen: **eine Wahrheit** aus `lighthouse/assertions.json`, erzeugt aus
  `data/design/regelwerk.yaml`. Leere oder fehlende Schwellen brechen hart ab
  (Scheingrün-Sperre).
- Gerät: Mobile-Emulation (390 × 844, gedrosselt) – dieselbe Sicht wie die
  Mehrheit der Leser.
- Browser: derselbe Resolver wie die E2E-Suite (`e2e/browser.mjs`), also das
  gepinnte Chromium – erst zur Messzeit dynamisch geladen.
- Aggregation: je Schwelle `median` / `pessimistic` / `optimistic`, wie in der
  Assertion hinterlegt.
- Ausgabe: `data/cwv/labor/befund.json` + `.md` (`--schreiben`), Exit `0`
  gemessen · `1` Befund (nur mit `--streng`) · `2` nicht messbar / falsche
  Argumente.

Ein Sonderfall ist im Skript festgehalten: Lighthouse 13 hat `dom-size` als
`dom-size-insight` ausgeliefert. Der Alias steht an **einer** Stelle
(`AUDIT_ALIAS`) – nicht in der Schwelle, nicht im Bericht.

## Wenn eine Meldung (`WF-0032`) kommt

Das zentrale Fehler-Alerting (`.github/workflows/alert-on-failure.yml`) trennt
drei Ursachen:

1. **Klasse `selbsttest`:** Code- oder Vertragsregression am Prüfwerkzeug.
   Lokal mit `npm run test:webvitals` nachstellen und im Code beheben.
2. **Klasse `web-vitals-befund` (Felddaten `SCHLECHT`, Exit 1):** Zuerst den
   Laborbericht derselben URL im Artefakt `web-vitals-woche` prüfen – er nennt
   die gerissene Grenze (LCP-Bild, render-blockierendes CSS, Hauptthread-JS).
   Nach der Heilung hinkt CrUX gleitend bis zu **28 Tage** hinterher.
3. **Klasse `web-vitals-stoerung` (Exit 2):** Annotation und Lauf-Zusammenfassung
   prüfen:
   - Steht dort `keine_crux_daten`, ist die API gesund, aber die Seite liegt im
     28-Tage-Fenster noch unter Googles CrUX-Besucherschwelle (C2).
   - Steht dort `HTTPError 429` / `abruf_fehlgeschlagen`, ein gültiges
     `PSI_API_KEY`-Secret in den Repository-Einstellungen hinterlegen und den
     Workflow manuell starten.

## Grenzen

- CrUX kennt nur Seiten mit genügend Traffic im 28-Tage-Fenster. Kleine
  Werkzeugseiten bleiben `UNGEPRÜFT` – korrekt, nicht ärgerlich.
- Eine Feldmessung ist ein Blick von außen, kein Freibrief: Sie sagt „so war
  es", nicht „so ist es jetzt".
- Der Lauf ersetzt weder `design-varianten.yml` (Labor-Gate vor dem Deploy)
  noch `cwv_guard.py` (Byte-Budgets). Drei Messungen, drei Fragen.
