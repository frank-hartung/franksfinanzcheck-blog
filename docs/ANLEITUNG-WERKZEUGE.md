# Anleitung: Franks Werkzeuge (`/werkzeuge/`)

> Rollout 02.10.2026. Zweiter Produktkern neben dem Fixkosten-Cockpit.
> Diese Datei ist das Runbook: Wer ein Werkzeug anfasst, liest sie vorher.

## Wofür es die Werkzeuge gibt

Vor dem Rollout gab es Rechner nur **im** Artikel (`rechner.html`,
`tarifvergleich.html`, `einspartabelle.html`). Wer rechnen wollte, musste
erst einen Text finden. Die acht Werkzeuge drehen das um: eigene Seiten,
eigene Navigation, eigener Einstieg über `/werkzeuge/` – benutzbar, ohne
vorher etwas zu lesen und ohne einen Empfehlungslink anzuklicken.

Der bindende Satz, der auf dem Hub und auf **jeder** Werkzeugseite steht:

> **Du kannst das Tool vollständig nutzen, ohne einen Affiliate-Link anzuklicken.**

Er ist kein Marketingtext, sondern eine geprüfte Zusage (Gate-Regel W1/W3).

## Die acht Werkzeuge

| Slug (`/werkzeuge/<slug>/`) | Engine | Was es beantwortet | Speicher | Export |
|---|---|---|---|---|
| `fixkosten-scanner` | `scanner` | Was kosten alle Fixkosten im Jahr, und was ist davon prüfwürdig? | ja | CSV, PDF |
| `effektivpreis-rechner` | `effektivpreis` | Was kostet der Tarif über 24 Monate wirklich – inklusive Bonus und Einmalkosten? | ja | CSV, PDF |
| `abschlag-nachzahlung-rechner` | `energie` | Passt der Strom-/Gas-Abschlag, oder droht eine Nachzahlung? | ja | CSV, PDF |
| `selbstbehalt-rechner` | `selbstbehalt` | Lohnt der höhere Selbstbehalt gegenüber der Beitragsersparnis? | ja | CSV, PDF |
| `notgroschen-rechner` | `notgroschen` | Wie groß muss der Notgroschen sein, und wann ist er voll? | ja | CSV, PDF |
| `kuendigungsfristen-kalender` | `fristen` | Wann ist der letzte Tag für die Kündigung? | ja | **ICS**, CSV, PDF |
| `tarifwechsel-entscheidungsbaum` | `entscheidung` | Wechseln, verhandeln oder bleiben? | **nein** | CSV, PDF |
| `haushaltsbudget` | `budget` | Wie teilt sich das Einkommen auf (50-30-20), und was bleibt übrig? | ja | CSV, PDF |

## Architektur in einem Bild

```
data/werkzeuge.yaml            SSOT: Felder, Formeln, Annahmen, Quellen, Versprechen
   │
   ├─ layouts/_partials/werkzeuge_data.html   Zugriff + Validierung der SSOT
   ├─ layouts/_partials/ff_werkzeug.html      Markup eines Werkzeugs (DOM-Vertrag)
   ├─ layouts/shortcodes/werkzeug.html        {{< werkzeug "<id>" >}} für Content
   ├─ layouts/werkzeuge/single.html           Werkzeugseite + SoftwareApplication-Schema
   ├─ layouts/werkzeuge/list.html             Hub /werkzeuge/
   ├─ assets/css/extended/zz-werkzeuge.css    Optik (hell + dunkel)
   └─ static/premium/ff-werkzeuge.js          Rechenkern, Speicher, Export (netzfrei)

content/werkzeuge/<slug>/index.md             Seitentext, Frontmatter-ID, FAQ
```

**Es gibt genau eine Wahrheit:** `data/werkzeuge.yaml`. Felder, Formeln,
Annahmen und Quellen werden nirgends doppelt gepflegt – Templates, Rechenkern,
Export, Schema und Gate lesen alle dieselbe Datei.

## Der DOM-Vertrag

Rechenkern und Tests sprechen **nur über `data-`-Attribute** mit dem Markup,
nie über Klassen. Klassen gehören dem Design, `data-`-Hooks gehören der
Funktion. Wer eine Klasse umbenennt, bricht nichts; wer einen Hook entfernt,
bricht das Produkt (und das Gate sagt es).

| Hook | Bedeutung |
|---|---|
| `data-ff-werkzeug` | Wurzel; trägt `data-werkzeug`, `data-engine`, `data-versprechen`, `data-dateipraefix` |
| `data-feld` | Eingabefeld; `data-typ` ∈ `euro,zahl,prozent,datum,auswahl`, dazu `data-label`, optional `data-einheit`, `data-pflicht`, `data-bucket`, `data-korridor` |
| `data-ff-wz-reset` / `-speichern` | Zurücksetzen / Opt-in-Checkbox für den lokalen Speicher |
| `data-ff-wz-leer` / `-fehler` / `-ausgabe` | Ergebniszustände (leer, Fehlerliste, Ergebnis) |
| `data-ff-wz-kennzahlen` / `-liste` / `-zeilen` / `-hinweise` / `-termine` | Ergebnisbausteine |
| `data-ff-wz-export-format="csv\|pdf\|ics"` | Export-Knöpfe |
| `data-ff-wz-formel` / `-annahme` / `-quelle` | Methodik, immer sichtbar, nie in `<details>` |

Feld-IDs folgen `ff-wz-<werkzeug>-<feld>`. Die öffentliche Skript-API ist
`globalThis.FFWerkzeuge = { logik, hilfen, exporte, felderLesen, start }`;
jede Engine liefert `{ kennzahlen, zeilen, liste, hinweise, termine }` oder
`{ fehler: [...] }`.

## Datenschutz und Export

- **Kein Konto, keine Eingabe personenbezogener Daten, kein Netzaufruf.**
  Der Rechenkern enthält weder `fetch` noch `XMLHttpRequest`; das Formular
  hat bewusst kein `action`.
- **Speicher nur nach Opt-in:** erst das Häkchen „Eingaben auf diesem Gerät
  merken" schreibt nach `localStorage` (`ff_werkzeug_<id>_v1`).
  „Zurücksetzen" löscht den Schlüssel wieder.
- **Export entsteht im Browser:** CSV (BOM, Semikolon, CRLF – Excel-tauglich),
  PDF (eigener PDF-1.4-Writer, Helvetica, WinAnsi) und ICS (ganztägige
  Termine, Erinnerung `TRIGGER:-PT9H`). Jede Datei trägt Eingaben, Ergebnis,
  Formel, Quellen und das Versprechen – sie ist ohne die Website lesbar.

## Ein neues Werkzeug ergänzen

1. **SSOT erweitern:** Eintrag in `data/werkzeuge.yaml` (`id`, `slug`,
   `engine`, `felder[]`, `formel[]`, `annahmen[]`, `quellen[]`, `exporte[]`).
   Jede Quelle braucht `titel`, `url`, `herausgeber`, `stand`; URLs werden vor
   dem Commit geprüft, nicht geraten.
2. **Engine ergänzen** in `static/premium/ff-werkzeuge.js` unter `logik.<engine>`
   – reine Funktion `(felder, {heute}) => Ergebnis`, keine DOM-Zugriffe.
3. **Seite anlegen:** `content/werkzeuge/<slug>/index.md` mit `werkzeug: "<id>"`
   im Frontmatter und `{{< werkzeug "<id>" >}}` im Text.
4. **Tests schreiben:** Fälle in `tools/werkzeuge.test.mjs` (Rechenkern),
   bei neuem Produktverhalten zusätzlich `e2e/werkzeuge.spec.mjs`.
5. **Zahl anpassen:** `ANZAHL_WERKZEUGE` in `scripts/werkzeuge_gate.py` und die
   Erwartung im Hub-Test – das Gate kennt die Soll-Zahl bewusst.
6. **Alles laufen lassen** (siehe unten). Erst grün, dann committen.

## Prüfen

```bash
npm run werkzeuge:check     # Selbsttest + Quellvertrag + Build + Produkt-Gate
npm run test:werkzeuge      # 24 Gate-Unit-Tests + 55 Rechenkern-Tests (jsdom)
python3 scripts/werkzeuge_gate.py --source-only     # nur die Quelle, ohne Build
python3 scripts/werkzeuge_gate.py --public public   # nur der gebaute Stand
npx playwright test e2e/werkzeuge.spec.mjs          # Produktverhalten im Browser
```

Das Gate kennt acht Regeln und **repariert nie selbst**:

| Regel | Was sie schützt |
|---|---|
| **W1 Versprechen** | Der Vertrauenssatz steht wörtlich auf Hub und jeder Seite – im Markup und im Schema |
| **W2 Vollständig** | Zu jedem SSOT-Eintrag genau eine Seite und umgekehrt; der Hub verlinkt alle acht |
| **W3 Werbefrei** | Kein `/go/`, kein `rel="sponsored"`, keine Partner-Domain unter `/werkzeuge/` |
| **W4 Verdrahtung** | Shortcode eingebunden, Frontmatter-ID = Ordner-Slug = gerendertes `data-werkzeug` |
| **W5 Nachvollziehbar** | Formel, Annahmen und Quellen mit Stand werden tatsächlich gerendert |
| **W6 Lokal** | Kein `action`, kein Netzpfad im Rechenkern, kein externes Asset |
| **W7 Offen** | Methodik sichtbar auf der Seite, nicht in `<details>`, nicht hinter einem Klick |
| **W8 Verdrahtung** | Kein Werkzeug ist eine Waise: jedes muss aus seinem `pillar:` erreichbar sein; Einbettungen `{{< werkzeug id="…" >}}` außerhalb von `/werkzeuge/` nennen eine ID der SSOT und die Seite führt `lastmod` |

Im Deploy läuft W1–W8 zweimal: als Quellvertrag **vor** dem Build und als
Produkt-Gate **nach** dem Build gegen `public/` (W8 ist eine Quellenregel –
der Build prüft sie nicht erneut, weil sie nichts am Markup ändert).

## Werkzeuge in Artikeln und Pillaren einbetten

`{{< werkzeug id="…" >}}` ist für die Einbettung **außerhalb** des Silos gebaut:
der Rechenkern und das CSS werden pro Seite genau einmal geladen, die ID muss
in `data/werkzeuge.yaml` stehen (sonst stoppt W8 die Quelle und `errorf` den
Build). Zwei Grenzen bleiben, weil sie das Produktversprechen sind:

- **Kein `/go/`-Link, kein `rel="sponsored"`, keine Partner-Domain unter
  `/werkzeuge/`** (W3) – auch nicht „optional“ und nicht „nur ein CTA unten“.
- Der Verdrahtungspfad ist die **Gegenrichtung**: Werkzeug → in den kaufnahen
  Text, nicht Werbung → auf das Werkzeug. Verlinkung aus dem deklarierten
  Pillar ist Pflicht (W8), damit kein Werkzeug als unentdeckte Seite endet.

Der Grund ist gemessen, nicht gefühlt (10.10.2026): 0 Links aus `content/` auf
`/werkzeuge/`, 0 Einbettungen, 0 der 82 kaufnahen Trichter-Seiten waren
Werkzeugseiten. Acht fertige Rechner, die niemand auf dem Entscheidungsweg
traf.

## Stolpersteine

- **Überschriften in Shortcode-Containern dürfen kein `id`-Attribut tragen** –
  sonst bricht der Chunker-Vertrag in `scripts/layout_audit.py`.
- `/werkzeuge/...` ist **keine** Money-Page im Sinne von
  `scripts/schema_seo_gate.py` – dort gilt der reduzierte OG-Satz.
- Deutsche Zahlen enthalten ein geschütztes Leerzeichen vor `€` (U+00A0).
  In Tests `\s` benutzen oder `.replace(/\u00A0/g, ' ')`.
- Neue Werkzeugseiten landen **automatisch** in Sitemap und Navigation
  (`sitemap_kandidaten.html`, `[menu.main]`), neue CSS-Dateien automatisch im
  Bundle (`head.html`). Nichts davon von Hand nachpflegen.
