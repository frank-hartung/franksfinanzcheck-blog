# Web Vitals: Labor, Feld und die ausgelieferte Seite

**Ziel:** Core Web Vitals dort messen, wo sie zählen – bei echten Besuchern –
und die Laborwerte der **ausgelieferten** Seite danebenlegen, statt sie mit
einem Varianten-Build zu verwechseln.

## Warum es diese Messung gibt (26.10.2026)

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

## Die Woche

Workflow: `.github/workflows/web-vitals-woche.yml` – montags 05:47 UTC
(≈ 07:47 Berlin), nach dem GSC-Lauf, plus manuell auslösbar. Der Lauf ist
read-only: Berichte gehen als Artefakt und in die Lauf-Zusammenfassung, nicht
in den Bestand. Ein Wochenlauf, der Commits erzeugt, wäre selbst eine
Änderungsquelle am Messgegenstand.

```
Felddaten  →  Befund  ⇒ Lauf rot (Exit 1)        – echte Besucher betroffen
           →  Störung ⇒ Lauf rot (Exit 2)        – ungeprüft ist nicht sauber
Labor      →  Befund  ⇒ Warnung im Lauf, Bericht – Diagnose, kein Blocker
```

Diese Trennung ist der Kern: Ein Laborlauf über CDN und Mobilfunk-Drosselung
ist kein Freibrief und kein Deploy-Blocker. Verbindlich für die Wirklichkeit
sind die Felddaten – sie sind der einzige Alarm, der hier zählt.

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
nur dort, wo echte Besucher messbar sind. Eine Liste mit 60 URLs wäre eine
Wunschliste, keine Messung. Aktuell: Startseite, Werkzeuge-Hub, Cockpit,
Fixkosten-Scanner, 24-Monats-Effektivpreis.

**Schlüssel:** `PSI_API_KEY` (optional, als GitHub-Secret). Ohne Schlüssel
antwortet die API gedrosselt, der Lauf bleibt möglich. Der Schlüssel wird nie
ausgegeben, nie geloggt, nie in eine Datei geschrieben.

### Wie bewertet wird

Die Bewertung kommt **aus der API** (`category`: `FAST` / `AVERAGE` / `SLOW` →
`GUT` / `VERBESSERUNGSWUERDIG` / `SCHLECHT`). Damit gibt es keine zweite,
erfundene Schwelle im Repo – 2,5 s / 200 ms / 0,1 sind Googles Definition, und
Google liefert das Urteil gleich mit.

- Das **schlechteste** Einzelurteil bestimmt das Seitenurteil. Eine Seite mit
  gutem LCP und schlechtem INP ist nicht „gut".
- **Keine Felddaten = UNGEPRÜFT**, niemals GRÜN. Eine neue Seite mit zu wenig
  Traffic wird nicht als gesund geführt.
- **Keine einzige geprüfte Seite = STÖRUNG** (Exit 2). Dann stimmt etwas an der
  Messung nicht (Domain, API, Quote) – nicht an der Seite.
- Der Schlüssel fehlt in der Ausgabe, auch im JSON.

Exit: `0` kein Feldbefund · `1` Befund (mindestens eine Seite `SCHLECHT`) ·
`2` Störung (Netz, API, kein Ziel messbar).

## Laborwerte der ausgelieferten Seite

```bash
node scripts/lighthouse_live.mjs                      # Ziele aus data/cwv/feld_ziele.json
node scripts/lighthouse_live.mjs --url https://franksfinanzcheck.de/werkzeuge/
node scripts/lighthouse_live.mjs --laeufe 3 --schreiben
node scripts/lighthouse_live.mjs --json               # Maschinenausgabe
node scripts/lighthouse_live.mjs --streng             # Befund ⇒ Exit 1 (nur wenn bewusst gewollt)
```

- Schwellen: **eine Wahrheit** aus `lighthouse/assertions.json`, erzeugt aus
  `data/design/regelwerk.yaml`. Keine zweite Zahl.
- Gerät: Mobile-Emulation (390 × 844, gedrosselt) – dieselbe Sicht wie die
  Mehrheit der Leser.
- Browser: derselbe Resolver wie die E2E-Suite (`e2e/browser.mjs`), also das
  gepinnte Chromium – kein zweiter Browserweg.
- Aggregation: je Schwelle `median` / `pessimistic`, wie in der Assertion
  hinterlegt; über mehrere Läufe wird genau diese Methode angewandt.
- Ausgabe: `data/cwv/labor/befund.json` + `.md` (`--schreiben`), Exit `0`
  gemessen · `1` Befund (nur mit `--streng`) · `2` nicht messbar.

Ein Sonderfall ist im Skript festgehalten: Lighthouse 13 hat `dom-size` als
`dom-size-insight` ausgeliefert. Der Alias steht an **einer** Stelle
(`AUDIT_ALIAS`) – nicht in der Schwelle, nicht im Bericht.

## Wenn ein Befund kommt

1. **Felddaten `SCHLECHT`** – zuerst das Labor derselben URL ansehen
   (`lighthouse_live.mjs --url …`). Es nennt die gerissene Grenze; typische
   Ursachen in diesem Blog: zu großes LCP-Bild, render-blockierendes CSS,
   nachgeladenes JavaScript im Erstkontakt.
2. **Nur Labor rot** – prüfen, ob der Varianten-Build dasselbe zeigt
   (`design-varianten.yml`). Ist nur Produktion betroffen, liegt es an
   Auslieferung/CDN (Cache-Header, Bildgrößen, Cloudflare-Optimierungen).
3. **Störung (Exit 2)** – Messung reparieren, nicht die Seite. Ein
   `UNGEPRÜFT` ist kein Blankoscheck.
4. Nach der Heilung: Felddaten hinken bis zu **28 Tage** hinterher. Ein grüner
   Wert am nächsten Tag beweist nichts; der Verlauf (`verlauf.jsonl`) zeigt
   den Trend.

## Grenzen

- CrUX kennt nur Seiten mit genügend Traffic im 28-Tage-Fenster. Kleine
  Werkzeugseiten bleiben `UNGEPRÜFT` – korrekt, nicht ärgerlich.
- Eine Feldmessung ist ein Blick von außen, kein Freibrief: Sie sagt „so war
  es", nicht „so ist es jetzt".
- Der Lauf ersetzt weder `design-varianten.yml` (Labor-Gate vor dem Deploy)
  noch `cwv_guard.py` (Byte-Budgets). Drei Messungen, drei Fragen.
