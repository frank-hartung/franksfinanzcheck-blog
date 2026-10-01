# Beweissystem Premium – Rollout-Report (01.10.2026)

**Auftrag (Frank):** „Zu wenig originäre Beweise. Das Repository behauptet viel
(‚selbst geprüft‘, ‚praxisgetestet‘, ‚über zehn Jahre Erfahrung‘, ‚hunderte
Tarifvergleiche‘, ‚unabhängig‘), belegt aber wenig. `content/methodik/index.md`
ist ein guter Ansatz, muss aber vom Erklärtext zu einem **Beweissystem**
ausgebaut werden. Dauerhaft auf Highend-Level einer Profi-Agentur beheben.“

## Befund vor dem Eingriff

* Erfahrungs-Behauptungen in **43 von 66 Artikeln** als identischer
  Frontmatter-Boilerplate (`erfahrung: "… selbst geprüft … praxisgetestet …"`),
  ohne einen einzigen sichtbaren, originären Beleg (B6-Inventar der neuen Wache).
* Quellen nur als Artikel-Endblock („Quellen & Faktenstand“) – keine Quelle
  direkt an der Zahl.
* Keine Fallstudien, keine dokumentierten Wechsel, keine Messreihen, kein
  öffentliches Änderungsprotokoll, keine je Themenbereich nachvollziehbare
  Vergleichsmethodik (nur allgemeiner Erklärtext).
* Vorhandene Substanz, auf der aufgebaut wurde: versionierte Datensätze
  (`data/datasets/`), Kennzahlen-Register mit Prüfrhythmen
  (`data/kennzahlen_register.yaml`), Faktenfrische-Pipeline.

## Entscheidung: Beweissystem statt mehr Behauptungstext

Vier öffentliche Bausteine + eine Wache. Leitprinzip ist **Ehrlichkeit vor
Eindruck**: Was (noch) nicht belegt ist, wird nicht behauptet, sondern als
terminierter Backlog öffentlich gemacht. Es wurden bewusst **keine** Fallstudien,
Rechnungen oder Messwerte erfunden – erfundene Beweise wären das Gegenteil von
E-E-A-T und verstoßen gegen die SSOT-Regel „nichts aus dem Gedächtnis“
(`data/kennzahlen_register.yaml`).

### 1. Beweis-Register (`data/beweise/register.yaml`)

* **Verifiziert (2):** Modellrechnungen `mr-dsl-effektivpreis-24m` und
  `mr-tagesgeld-15000` – aus den bestehenden, redaktionell nachgerechneten
  Datensätzen übernommen (Formel, Annahmen, Grenzen, Quellen, Changelog).
* **Modellfall (1):** `fs-dsl-modellfall-2026` – Fallstudien-Format
  (Ausgangslage → Entscheidung → Ergebnis) auf Basis der verifizierten
  Rechnung; Rendering erzwingt den Hinweis „kein realer Einzelfall“.
* **Backlog mit Fälligkeit (3):** Standby-Messreihe (Messaufbau komplett
  definiert, fällig 30.11.2026), eigenes DSL-Wechselprotokoll mit
  Rechnungsarchiv (fällig 15.12.2026), anonymisierte Leser-Fallstudie Kfz
  (fällig 15.01.2027, nur mit Einwilligung).

### 2. Vergleichsmethodik je Themenbereich (`data/beweise/vergleichsmethodik.yaml`)

Sechs Bereiche (= Pillar-Slugs), je mit Leitfrage, Rechenweg-Formel,
K.-o.-Kriterien + Rangfolge, Datenbasis nach Belegklassen, Grenzen und
SemVer-Changelog. Bewusst Prüfregeln statt erfundener Gewichtungs-Prozente.

### 3. Öffentliches Änderungsprotokoll (`/aenderungsprotokoll/`)

Neue Seite, gespeist aus `data/beweise/korrekturen.yaml`: was, wann, warum,
welche Quelle, welche Seiten – rückwirkend mit den real dokumentierten
Ereignissen (u. a. VZ-Girokonto-Quelle 404→Nachfolgeseite am 28.09.,
BDEW-Bestätigung 37,0 ct/kWh, Tagesgeld-Datensatz v1.1.0).

### 4. Quellen direkt an der Zahl + Belegklassen A/M/E

* Shortcode `beleg`: Beleg-Chip an der Zahl (Herausgeber + Stand + Klasse),
  bevorzugt aus dem Kennzahlen-Register (`kennzahl=`) – ein Stand, überall.
* Shortcode `beweis`: bettet Register-Einträge als prüfbaren Kasten ein;
  unfertige Einträge brechen den Build.
* Belegklassen-Dreiteilung sichtbar im gesamten Auftritt: **A** amtlich,
  **M** Marktbeobachtung/Modellrechnung, **E** eigene Erfahrung/Messung.
* `experience_box.html` trägt jetzt eine feste Einordnungszeile: persönliche
  Erfahrung ist Klasse E ohne Protokoll = Einordnung, **kein** Beweis.

### Wache + CI (Dauerhaftigkeit)

`scripts/beweis_gate.py` (B1–B6, mit Sabotage-Selbsttest) und
`.github/workflows/beweis-gate.yml` bei jedem Push/PR auf Beweisdaten,
Content oder Render-Bausteine. Zusätzlich bricht schon der Hugo-Build bei
toten Beweis-/Kennzahl-Verweisen ab (errorf in den Shortcodes).

## Geänderte/neue Dateien

| Datei | Zweck |
|---|---|
| `data/beweise/schema.yaml` | Normativer Vertrag (Klassen, Typen, Status, Pflichtfelder) |
| `data/beweise/register.yaml` | Beweis-Register (SSOT) |
| `data/beweise/vergleichsmethodik.yaml` | Methodik je Bereich, versioniert (SSOT) |
| `data/beweise/korrekturen.yaml` | Öffentliches Änderungsprotokoll (SSOT) |
| `layouts/shortcodes/beleg.html` | Quelle direkt an der Zahl (A/M/E-Chip) |
| `layouts/shortcodes/beweis.html` | Einzelner Beweis im Artikel |
| `layouts/shortcodes/beweisregister.html` | Register-Übersicht + ehrlicher Backlog |
| `layouts/shortcodes/vergleichsmethodik.html` | Methodik-Karten mit Version/Changelog |
| `layouts/shortcodes/aenderungsprotokoll.html` | Protokoll-Zeitleiste |
| `assets/css/extended/zz-beweissystem.css` | Styles inkl. Dark Mode (Marken-Tokens) |
| `content/methodik/index.md` | Umbau zum Beweissystem-Hub |
| `content/aenderungsprotokoll/index.md` | Neue öffentliche Seite |
| `layouts/_partials/experience_box.html` | Einordnungszeile (E ≠ Beweis) |
| `scripts/beweis_gate.py` | Wache B1–B6 + Selbsttest |
| `.github/workflows/beweis-gate.yml` | CI-Gate |
| `docs/ANLEITUNG-BEWEISSYSTEM.md` | Runbook |
| Artikel Standby / Tagesgeld | Erste Live-Nutzung von `beleg` bzw. `beweis` |

## Beifang-Reparaturen (beim Verifizieren gefunden, Basis-Commit)

* **Startseiten-Title dupliziert:** Der Cockpit-Rollout hatte `content/_index.md`
  denselben `seoTitle` wie `/cockpit/` gegeben → SEO-Cockpit P2 (duplicate-title)
  und roter E2E-Vertrag (`seo-pagination.spec.mjs` erwartet „Geld sparen“).
  Startseite hat wieder einen eigenen Title (≤ 65 Zeichen).
* **Sitemap-Lücken:** `/cockpit/` (Basis-Commit) und das neue
  `/aenderungsprotokoll/` waren indexierbar, aber in keiner Sitemap
  (Index-Hygiene-Wache H1). Beide ergänzt in `layouts/sitemap.xml`.

## Verifikation

* `hugo --destination public` grün (0.164.0 extended); Anker geprüft
  (`#beweis-register`, `#methodik-<bereich>`, keine doppelten DOM-IDs).
* `python3 scripts/beweis_gate.py` → 0 Fehler, 43 B6-Warnungen (gewollt:
  das Inventar der Alt-Behauptungen, Abbauziel siehe unten).
* `python3 scripts/beweis_gate.py --selftest` → 6/6 Sabotage-Proben OK.
* `npx playwright test` → **83/83 grün** (Desktop + Mobile; Chromium über den
  dokumentierten `@sparticuz/chromium`-Fallback aus `e2e/browser.mjs`).
* `python3 -m unittest discover -s scripts/tests` → 1192 Tests OK.
* `scripts/layout_audit.py` (1916 interne Links, 0 kaputt),
  `scripts/index_hygiene_gate.py` (Crawl-Fläche sauber, 60 Sitemap-Einträge),
  `scripts/schema_seo_gate.py` (0 harte Funde),
  `scripts/seo_cockpit.py --strict` (P1: 0, **P2: 0**, P3: 6 – Bestand),
  `scripts/offenlegung_gate.py` (O1–O7 erfüllt),
  `scripts/zeit_rechtschreibung.py` (0 Funde) – alle grün.

## Offene Folgearbeiten (terminiert im Register)

1. B6-Inventar abbauen: Erfahrungs-Boilerplate je Artikel entweder durch
   echten Register-Beleg ersetzen oder zur Einordnung abschwächen.
2. Messreihe `ms-standby-haushalt-2026` abschließen → Datensatz + Artikel-Belege
   auf Klasse E heben (fällig 30.11.2026).
3. Wechselprotokoll `wp-internet-dsl-2026` mit erster Neuanbieter-Rechnung
   veröffentlichen (fällig 15.12.2026).
4. Leser-Fallstudie Kfz mit Einwilligung + Vier-Augen-Anonymisierung
   (fällig 15.01.2027).
