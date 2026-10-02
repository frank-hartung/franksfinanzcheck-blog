# Werkzeuge Premium – Rollout-Report (02.10.2026)

**Auftrag (Frank):** „Befund 5: Rechner sind noch kein echter
Wettbewerbsvorteil. Heute gibt es nur Shortcodes im Artikel
(`rechner.html`, `tarifvergleich.html`, `einspartabelle.html`). Gebraucht wird
eine **eigenständige, vertrauenswürdige Tool-Erfahrung** – kein Rechner im
Artikel. Dauerhaft auf Highend-Level einer Profi-Agentur beheben."

## Befund vor dem Eingriff

* Rechnen war nur **Beiwerk eines Textes**: drei Shortcodes, eingebettet in
  Artikel, ohne eigene Seite, ohne eigenen Einstieg, ohne Platz in der
  Navigation. Wer rechnen wollte, musste zuerst einen Artikel finden.
* Keine der drei Komponenten hatte Export, lokalen Speicher, offengelegte
  Formel oder eine Quelle direkt an der Zahl.
* Es gab **keine überprüfbare Zusage**, dass sich ein Rechner vollständig
  ohne Affiliate-Klick nutzen lässt. Das Versprechen stand nirgends, also
  konnte es auch nirgends halten.
* Vorhandene Substanz, auf der aufgebaut wurde: das Fixkosten-Cockpit
  (`/cockpit/`) als Präzedenzfall für eine Produktseite mit lokalem Speicher,
  der 4K-Prüfpfad (`data/fixkosten_kompass.yaml`) als thematische Ordnung und
  der Kompass-Guard als Vorlage für einen Produktvertrag.

## Entscheidung: acht Werkzeuge mit einem Versprechen, nicht acht Rechner

Leitprinzip ist **Nutzbarkeit ohne Gegenleistung**. Ein Rechner, der ohne
Klick auf einen Partnerlink funktioniert, ohne Konto, ohne Datenabfluss und
mit offengelegter Formel, ist kein Marketinginstrument mehr, sondern ein
Werkzeug. Deshalb steht wörtlich auf dem Hub und auf jeder einzelnen Seite:

> **Du kannst das Tool vollständig nutzen, ohne einen Affiliate-Link anzuklicken.**

Damit dieser Satz nicht beim nächsten Umbau still verschwindet, ist er keine
Textzeile, sondern eine Gate-Regel (W1) mit Sabotage-Tests.

### 1. Produkt (`/werkzeuge/`)

Hub plus acht eigenständige Seiten, über die Hauptnavigation erreichbar:

| Werkzeug | Beantwortet | Besonderheit |
|---|---|---|
| Fixkosten-Scanner | Was kosten alle Fixkosten im Jahr? | Sparkorridor je Kategorie, Ampel |
| 24-Monats-Effektivpreis | Was kostet der Tarif wirklich? | Bonus, Einmalkosten, Normalpreis nach Aktion |
| Abschlag & Nachzahlung | Passt der Abschlag für Strom/Gas? | Ampel −10 %/+15 %, Grundpreis getrennt |
| Selbstbehalt-Rechner | Lohnt der höhere Selbstbehalt? | Beitragsersparnis gegen Schadenrisiko |
| Notgroschen-Rechner | Wie groß, und wann voll? | Lage-abhängige Monate, Monatsiteration |
| Kündigungsfristen-Kalender | Wann ist der letzte Tag? | **ICS-Export** mit drei Terminen (−42/−14/0) |
| Tarifwechsel-Entscheidungsbaum | Wechseln, verhandeln oder bleiben? | fünf nachvollziehbare Regeln, Aufwandsgrenze 60 €/Jahr |
| Haushaltsbudget | Wohin geht das Geld? | 50-30-20 über Bucket-Zuordnung, lokaler Speicher |

Jede Seite zeigt ohne einen einzigen Klick: Formel, Annahmen und Quellen mit
Herausgeber und Stand. Nichts davon steckt in einem zugeklappten `<details>`.

### 2. Datenschutz als Bauweise, nicht als Hinweis

* Kein Konto, keine personenbezogenen Daten, kein Netzaufruf: Der Rechenkern
  kennt weder `fetch` noch `XMLHttpRequest`, das Formular hat kein `action`.
  Der Browser-Test belegt es, indem er **jede** XHR/Fetch-Anfrage mitschreibt
  und auf eine leere Liste prüft.
* Lokaler Speicher nur nach Opt-in (`ff_werkzeug_<id>_v1`), „Zurücksetzen"
  löscht ihn wieder – beides im E2E-Test festgenagelt.
* Exporte entstehen im Browser: **CSV** (BOM, Semikolon, CRLF – Excel-tauglich),
  **PDF** (eigener PDF-1.4-Writer, Helvetica, WinAnsi, kein externes Paket) und
  **ICS** (ganztägige Termine, Erinnerung `TRIGGER:-PT9H`). Jede Datei enthält
  Eingaben, Ergebnis, Formel, Quellen und das Versprechen; sie ist ohne die
  Website vollständig lesbar.

### 3. Eine Wahrheit: `data/werkzeuge.yaml`

Felder, Formeln, Annahmen, Quellen, Exportformate und der Vertrauenssatz
stehen genau einmal. Templates, Rechenkern, Export, Schema (`SoftwareApplication`,
`FAQPage`, `BreadcrumbList`) und Gate lesen dieselbe Datei. Quellen sind
amtlich und wurden vor dem Commit einzeln abgerufen, nicht erinnert:
TKG § 56, StromGVV/GasGVV § 13, VVG § 11, BGB §§ 130/309/312k, EnWG § 41,
Bundesnetzagentur (TK und Energie), BaFin, Bundesbank, Destatis,
Verbraucherzentrale.

### 4. Die Wache: `scripts/werkzeuge_gate.py`

Sieben Regeln, zweimal im Deploy – als Quellvertrag **vor** dem Build und als
Produkt-Gate **nach** dem Build gegen `public/`:

| Regel | Was sie schützt |
|---|---|
| **W1 Versprechen** | Der Satz steht wörtlich auf Hub und jeder Seite – im Markup und im Schema |
| **W2 Vollständig** | Zu jedem SSOT-Eintrag genau eine Seite und umgekehrt; der Hub verlinkt alle acht |
| **W3 Werbefrei** | Kein `/go/`, kein `rel="sponsored"`, keine Partner-Domain unter `/werkzeuge/` |
| **W4 Verdrahtung** | Frontmatter-ID = Ordner-Slug = gerendertes `data-werkzeug` |
| **W5 Nachvollziehbar** | Formel, Annahmen und Quellen mit Stand werden tatsächlich gerendert |
| **W6 Lokal** | Kein `action`, kein Netzpfad im Rechenkern, kein externes Asset |
| **W7 Offen** | Methodik sichtbar, nicht in `<details>`, nicht hinter einem Klick |

Das Gate **repariert nie selbst**. Ein Defekt stoppt den Deploy, statt das
Versprechen still abzuschwächen.

## Was neu im Repository liegt

| Datei | Zeilen | Zweck |
|---|---|---|
| `data/werkzeuge.yaml` | 743 | SSOT aller acht Werkzeuge |
| `static/premium/ff-werkzeuge.js` | 1568 | Rechenkern, Speicher, CSV/PDF/ICS – ohne Abhängigkeit |
| `assets/css/extended/zz-werkzeuge.css` | 1003 | Optik hell und dunkel, Druckansicht |
| `layouts/_partials/ff_werkzeug.html` | 204 | Markup eines Werkzeugs (DOM-Vertrag) |
| `layouts/werkzeuge/single.html` / `list.html` | 155 / 70 | Werkzeugseite mit Schema / Hub |
| `layouts/shortcodes/werkzeug.html` | – | Einbindung im Artikel |
| `layouts/_partials/werkzeuge_data.html` | – | SSOT-Zugriff mit Validierung |
| `content/werkzeuge/**` | 9 Dateien | Hub-Text und acht Werkzeugseiten |
| `scripts/werkzeuge_gate.py` | 615 | Produktvertrag W1–W7 |
| `scripts/tests/test_werkzeuge_gate.py` | 203 | 18 Unit-Tests inklusive Sabotage-Proben |
| `tools/werkzeuge.test.mjs` | 810 | 55 Rechenkern-Tests (jsdom) |
| `e2e/werkzeuge.spec.mjs` | 209 | 9 Browser-Tests des Produktversprechens |

## Verifikation (02.10.2026, lokal)

| Prüfung | Ergebnis |
|---|---|
| `python3 scripts/werkzeuge_gate.py --selftest --source-only` | exit 0 |
| `python3 scripts/werkzeuge_gate.py --public public` | exit 0 |
| `python3 -m unittest scripts.tests.test_werkzeuge_gate` | 18/18 |
| `node --test tools/werkzeuge.test.mjs` | 55/55 |
| `npx playwright test` (voller Lauf, Desktop + Mobile) | **97/97** |
| `layout_audit`, `index_hygiene_gate`, `offenlegung_gate`, `casing_guard`, `emoji_guard`, `fixkosten_kompass_guard` | je exit 0 |
| `schema_seo_gate` | 2 harte Funde – **unverändert** zur Messlatte vor dem Umbau (beide `/pillar/frugalismus/`, nicht Teil dieses Auftrags) |
| Alle 16 Quell-URLs | einzeln abgerufen, inhaltlich passend; BaFin-Link auf die heute gültige Adresse gesetzt |

Zwei Befunde kamen erst durch den Mobil-Test ans Licht und wurden behoben:
Quellen-Links waren 39 px hoch (jetzt 44 px Zielfläche) und die Opt-in-Checkbox
20 px (jetzt 24 px nach WCAG 2.5.8, gleiche Schwelle wie im Cockpit).

## Was bewusst nicht gemacht wurde

* **Keine Artikel-Shortcodes entfernt.** `rechner.html`, `tarifvergleich.html`
  und `einspartabelle.html` bleiben, wo sie im Lesefluss Sinn ergeben. Die
  Werkzeuge ersetzen sie nicht, sie geben dem Rechnen ein eigenes Zuhause.
* **Keine Partnerlinks auf den Werkzeugseiten** – auch nicht „dezent unten".
  Das wäre genau die Abschwächung, die W3 verhindert.
* **Keine erfundenen Defaults.** Jede Vorbelegung (Strompreis, Gaspreis,
  Grundpreis, Laufzeit) stammt aus den bereits gepflegten Datensätzen und
  trägt ihre Quelle.

## Nächste Schritte (Vorschlag, nicht Teil dieses Rollouts)

1. Werkzeuge aus den passenden Ratgebern heraus verlinken (Kontextbrücke statt
   Insellösung) und die Hub-Nutzung über Umami beobachten.
2. Druckansicht der Werkzeugseiten gegen echtes Papier prüfen.
3. Prüfrhythmus für die Quellen-Stände in `data/kennzahlen_register.yaml`
   aufnehmen, damit „Stand" nicht altert.
