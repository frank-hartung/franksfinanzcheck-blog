# 🍂 SAISONALE STARTSEITE – Report Herbst 2026

**Stand:** 2026-09-20 · Branch: `arena/01a0bed1-franksfinanzcheck-blog` (Basis: `main` @ `c489a24`)
**Umfang:** Saison-Badge + Hinweis im Hero **und** Saison-Fokus-Block unter den Artikel-Karten („Beides: Hero + Teaser“)
**Status:** ✅ gebaut, gemessen, getestet – alle Gates grün (Playwright 33/33, Unit 447 OK, 8 Repo-Wächter grün)

---

## 1. Ausgangslage & Auftrag

Die Startseite war saisonal blind: Willkommenstext und Teaser-Reihenfolge änderten sich nie, obwohl der Bestand
klare Jahres-Schwerpunkte hat (Heizkosten/Gas im Herbst, Konto & Karten zum Jahreswechsel, Strom im Sommer,
Mietwagen & Urlaub im Frühling). Auftrag: die Startseite bekommt ein **datengetriebenes Saison-Gerüst**, das

1. im Hero sofort sichtbar macht, welche Jahreszeit redaktionell läuft (Badge + ein Satz Kontext),
2. unter den Artikel-Karten einen **Saison-Fokus-Block** mit Ratgeber-Link, drei passend sortierten Beiträgen
   und „Franks Tipp“ setzt,
3. sich **ohne Code-Änderung** je Quartal umschaltet – gepflegt wird nur `data/saisons.yaml`,
4. dabei Marken-Stimme, Design-Tokens, Dark Mode, WCAG-Kontraste und die LCP-Ordnung der Startseite nicht verletzt.

## 2. Was gebaut wurde

| Datei | Rolle |
|---|---|
| `data/saisons.yaml` | Einzige redaktionelle Quelle: 4 Saisons × Fenster, Emoji, Badge-, Hinweis-, Head-, Tipp-Text, Ratgeber-Ziel, Keywords, `min_artikel`; je Saison 5 Farb-Rollen (hell + dunkel). |
| `layouts/_partials/saisons_data.html` | Liest die YAML über `os.ReadFile` + `transform.Unmarshal` (Format explizit `yaml`) und parsed **einmal** pro Build (`partialCached`). Bewusst **nicht** `site.Data` (Build-Killer, siehe §7). |
| `layouts/_partials/_funcs/saison-aufloesung.html` | Reines Datums-Fenster (Jahresübertrag Dezember→Februar inklusive), Oktal-Falle umschifft (`strings.TrimPrefix "0"`). |
| `layouts/_partials/_funcs/saison-kontext.html` | Validierung + Auswahl der laufenden Saison, Spiegel der Template-Sortierung (Relevanz vor Datum), Fail-closed-`errorf`s. |
| `layouts/_partials/home_season.html` | Renderer für die drei Modi `badge` / `hinweis` / `block`; Redaktionstitel der Ratgeber kommen aus `themenwelten_data.html` (kein Slug-Capitalize). |
| `layouts/_partials/home_info.html` | Drei Ankerpunkte: Badge **vor** dem Header, Hinweis **nach** dem Willkommenstext, Block **nach** dem Pinterest-CTA. |
| `assets/css/extended/zz-saisonale-startseite.css` | Alle Saison-Styles; Farben ausschließlich als Custom Properties je Saison-Klasse (`.ff-saison--herbst` …) + Dark-Varianten (`data-theme="dark"` und `auto`/`prefers-color-scheme`). Keine Inline-Farben im Template, keine neuen Fonts, keine `var()`-Fallbacks (Repo-Konvention). |
| `scripts/saisonale_startseite_guard.py` | Neues Gate: Quellen-Checks S1–S8 (Schema, Kalender-Abdeckung, Marke/Ton, WCAG, CSS/YAML-Deckung, Ratgeber-Ziele, Auswahl-Spiegel, Datenpfad) + Build-Checks B1–B7 (Markup, Reihenfolge, Messkette, Kontrast-Paarung, Dark-Pfade, LCP-Ordnung, Datenpfad im Build) + `--selftest`. |
| `scripts/tests/test_saisonale_startseite.py` | 33 Vertragstests (unittest): Fenster-/Oktal-Logik, Kalender-Lücke & -Überlappung, Schema/Ton, Farb-Parität, CSS-Drift/Dark-Pfade/LCP-Order, Auswahl-Spiegel (Relevanz > Datum, Gleichstand, Fallbacks), Bestands-Lesbarkeit (draft/index/hidden), Datenpfad, Build-Prüfung, Gesamtlauf. |
| `e2e/saisonale-startseite.spec.mjs` | 7 Browser-Tests: Hero-Kohärenz (Badge/Hinweis = aktive Saison), Block-Inhalt + Messkette + HTTP-200 aller Links, Gerüst (genau 1 `h1`, Block in `main.main`, Anker vorhanden), Kontraste hell **und** dunkel ≥ 4.5:1, mobil 390×844: LCP-Bild im Viewport, Saison-`order` ≥ 2, kein horizontaler Overflow, Tap-Ziele ≥ 44 px. Zeit-tolerant (gestern/heute/morgen) gegen Fenstergrenzen-Flakes. |
| `e2e/design-metrics.mjs` | Erweitert um 9 Saison-Kontrast-Sonden (hell + dunkel) und die Layout-Sonde `LAYOUT_BODY` (Geometrie + Flex-`order` der `main.main`-Kinder). |

**Renderter Stand am 2026-09-20 (Saison `herbst`):** Badge „🍂 Herbst-Check: Heizkosten & Wechselfenster“,
Hinweis unter dem Willkommenstext, Block „Jetzt zählt die Heizsaison“ mit Ratgeber-Link
`/pillar/strom-sparen/` („Strom & Gas sparen“) und den Karten *Gasrechnung senken* (14.08.),
*Heizkosten senken* (18.09.), *Günstig durch den Winter* (11.09.) plus „Franks Tipp“.
Alle vier Saisons finden heute ≥ 3 Keyword-Treffer im Live-Bestand – der Fallback „neueste Artikel“
musste nowhere greifen.

## 3. Design-Entscheidungen (PRODUCT.md / DESIGN.md)

- **Tokens statt neuer Farben:** Texte/Akzente laufen über bestehende Rollen (`--ff-emerald`, `--ff-text-muted`,
  `--ff-surface` …). Neu sind nur die **fünf Saison-Rollen** `akzent`, `akzent_dunkel`, `hero_text`, `linie`,
  `linie_dunkel` je Saison – hell in der YAML, dunkel gespiegelt in der CSS-Klasse; das Gate prüft die Parität
  Hex für Hex (auch den `auto`-Pfad via `prefers-color-scheme`).
- **Kontraste gemessen, nicht geschätzt** (gerendert, `e2e/design-metrics.mjs`):

  | Sonde | Hell | Dunkel | Ziel |
  |---|---|---|---|
  | Badge-Text | 5.67 | 5.67 | ≥ 4.5 ✅ |
  | Hinweis | 7.22 | 7.22 | ≥ 4.5 ✅ |
  | Eyebrow | 5.41 | 7.31 | ≥ 4.5 ✅ |
  | Karten-Titel | 8.20 | 8.33 | ≥ 4.5 ✅ |
  | Karten-CTA | 5.41 | 7.31 | ≥ 4.5 ✅ |
  | Karten-Meta | 6.39 | 6.14 | ≥ 4.5 ✅ |
  | Ratgeber-Link | 5.41 | 7.31 | ≥ 4.5 ✅ |
  | Tipp-Text | 6.39 | 6.14 | ≥ 4.5 ✅ |
  | Tipp-Label | 5.41 | 7.31 | ≥ 4.5 ✅ |

- **Kein `text-transform: capitalize`** auf Slugs (ergab „Strom-sparen“); stattdessen Redaktionstitel aus
  `data/themenwelten.json` via `themenwelten_data.html`.
- **Aufmacher-Karte vertikal mittig:** die erste Karte spannt über beide Zeilen der Seitenspalte;
  `justify-content: center` + CTA direkt unter dem Titel verhindert den Leerraum-Riss zwischen Titel und CTA
  (vorher/nachher in `shots/block--desktop-light.png` sichtbar).
- **Dark Mode** dreifach abgesichert: `:root[data-theme="dark"]`, `@media (prefers-color-scheme: dark)` für
  `data-theme="auto"` (noscript-Pfad) – und das Gate failt, sobald die zwei Dark-Pfade auseinanderlaufen.
- **Fokus & Motion:** 3 px Signalgelb auf `:focus-visible` (Repo-Standard), Hover-Transforms nur `transform`/
  `box-shadow`, `prefers-reduced-motion`-respektierend über die bestehenden Repo-Regeln.

## 4. Layout, Reihenfolge & LCP-Schutz

Der Block ist eigenes Kind von `main.main` mit `order: 5` – **hinter** Pagination (`order: 4`), **vor** den
Themen-Clustern (Tie-Break per DOM-Reihenfolge). Damit bleiben die LCP-Karten (`order: 1`) auf Mobil unverändert
an erster Stelle; ein Kind ohne explizite `order` hätte sich (0 < 1) **vor** die LCP-Karten geschoben –
diese Falle prüft das Gate hart (S8/B6: `order` ≤ 1 bzw. > 5 failt).

Gemessen (gerendert, `design-metrics.mjs`, minified Build), Basis = `main` @ `c489a24`:

| Messgröße | Basis | Neu | Bewertung |
|---|---|---|---|
| Hero-Höhe Desktop (1280×800) | 788 px | 904 px | +116 px Badge/Hinweis, tragbar |
| LCP-Karte Desktop `top` | 1071 px | 1775 px | beide **unter** der 800-px-Falte → kein LCP-Erstkontakt verschoben |
| LCP-Bild Desktop `top` | 1096 px | 1800 px | dito, `lcpBildImViewport: false` vorher wie nachher |
| LCP-Karte Mobil `top` | 105 px | 105 px | **identisch** ✅ |
| LCP-Bild Mobil `top` / im Viewport | 120 px / ja | 120 px / ja | **identisch** ✅ |
| Saison-Block `top` (Desktop / Mobil) | – | 1187 px / 6535 px | bewusst unterhalb des Erstkontakts |
| Flex-Reihenfolge Mobil | – | Karten (1) → Pinterest (3) → Hero (2) → **Saison (5)** → Footer (4) → Cluster (5) | LCP vorne ✅ |

## 5. Gewicht der Startseite

| Größe | Basis | Neu | Delta |
|---|---|---|---|
| `public/index.html` (minified) | 145,675 B | 157,632 B | +11,957 B (+8.2 %) |
| DOM-Tags Startseite | 362 | 408 | +46 (cwv-Gate: DOM_NODES_SOFT 2500, grün) |
| Inline-CSS Startseite | 97,763 B | 104,857 B | +7,094 B (ff-saison-Anteil ≈ 7.1 KB minified) |
| CSS-Quelle `zz-saisonale-startseite.css` | – | 13,059 B | einmalig, build-time inline |

Kein neues JavaScript, keine externen Assets, keine zusätzlichen Requests – der Block ist pures Markup + CSS.

## 6. Test- & Gate-Bilanz

- **Playwright:** 33/33 grün (26 bestehende + 7 neue Saison-Tests), 45 s.
- **Unit:** `python3 -m unittest discover -s scripts/tests` → 447 Tests OK (davon 33 neue), 18 skips unverändert.
- **Saison-Gate:** `--selftest`, `--source-only`, `--public public` jeweils ✅ „Keine Funde“
  (Kalender-Abdeckung 366 Tage, alle 4 Saisons, WCAG, Parität, Spiegel, Datenpfad, Build).
- **Repo-Gates grün:** `layout_audit.py` (2135 Links, 0 broken), `themenwelten_guard.py`, `brand_guard.py`,
  `integrity_guard.py`, `emoji_guard.py`, `affiliate_intent_guard.py`, `cwv_guard.py --strict-build`,
  `willkommenstext_guard.py`.
- **Negativ-Beweise** (in einer Wegwerf-Kopie `/tmp/negativ` eingespielt, jede Regression wurde gefangen):

  | Eingebaute Regression | Fänger | Befund |
  |---|---|---|
  | Sommer-Fenster aus der YAML gelöscht | Gate S2 | „Kalender-Lücke: 2028-06-01 gehört zu keiner Saison“ (Exit 1) |
  | Laufende Saison (Herbst) gelöscht | Hugo-Build | `ERROR Saisonale Startseite: kein Saison-Fenster deckt heute (2026-09-20) ab …` (Exit 1) |
  | Ratgeber `strom-sparen` auf `draft: true` | Hugo-Build **und** Gate S6 | `ERROR … Ratgeber /pillar/strom-sparen/ fehlt` + „ist draft: true – der Saison-Link würde ins Leere zeigen“ |
  | CSS-Akzent von YAML entkoppelt + `order: 0` | Gate S5/S8 | „CSS-Drift: … eine Quelle muss die andere gewinnen“ + „die Artikel-Karten mit dem LCP-Cover haben order: 1 und müssen VORNE bleiben“ |
  | Sortierung auf Datum statt Relevanz zurückgedreht | Gate B3 | Reihenfolgen-Diff gebaut vs. erwartet (exakt die beim Entwickeln gefundene Regression) |
  | `site.Data.saisons` statt `os.ReadFile` | Hugo-Build **und** Gate S8 | `failed to load data: …/2026-08-27.jsonl: unmarshal of format "" is not supported` (Exit 1) + Quellen-Fund |

- **Screenshots** (hell/dunkel, Desktop/Mobil, Hero + Block + Mobil-Viewport) liegen lokal in `shots/`
  (gitignore-befreit von Versionierung, regenerierbar über `e2e/design-shots.mjs` bzw. die Layout-Sonden);
  die Vorher-Bilder des Heroes heißen dort `*-BASIS.png`.

## 7. Erkenntnisse für Folgearbeiten (Hugo-Fallen dieses Repo)

1. **`site.Data` / `hugo.Data` ist ein Build-Killer:** `data/audit/*.jsonl` lässt Hugos Data-Loader sterben
   (`unmarshal of format "" not supported`). Daten immer über `os.ReadFile` + `transform.Unmarshal` mit
   explizitem Format laden – deshalb existiert `saisons_data.html`.
2. **`int "09"` stolpert über Oktal** – Monats-/Tag-Strings vor `int` von führenden Nullen befreien.
3. **`return` mit Wert nur top-level**, nie in `{{ if }}`/`{{ range }}` – der Kontext-Partial sammelt deshalb
   in eine einzige Map und returnt einmal am Ende.
4. **`sort`-Ketten kollabieren** (`sort (sort … "a") "b"` sortiert nur noch nach `b`) – die Karten-Reihenfolge
   nutzt einen kombinierten numerischen Schlüssel `relevanz×1e12 + zeit`.
5. **Flex-`order` ist auf der Startseite vergeben** (Karten 1, Hero 2, Pinterest 3, Footer 4, Cluster 5):
   jedes neue `main.main`-Kind braucht eine bewusste `order`, sonst rutscht es vor den LCP-Erstkontakt.
6. **Minified-HTML hat unquotierte Attribute** – Build-Validierung nur mit `html.parser.HTMLParser`,
   nicht mit Regex auf `class="…"`.

## 8. Redaktioneller Betrieb

- **Umschalten:** nichts. Die Fenster steuern alles; am 01.12. übernimmt `winter` automatisch.
- **Pflegen:** nur `data/saisons.yaml` (Texte, Keywords, `min_artikel`, Farben). Das Gate läuft lokal und in CI
  (`scripts/saisonale_startseite_guard.py`), die Browser-Verträge in `e2e/` bei jedem PR.
- **Fail-closed:** fehlendes Fenster, fehlender Ratgeber, leere Auswahl oder Kalender-Lücke brechen den Build
  mit sprechendem `errorf` ab – eine halbkaputte Startseite wird nie ausgeliefert.
- **Messkette:** Badge/Block tragen `data-ff-saison`-Attribute (Saison, Quelle, Kandidaten-Zahl), damit
  `design-metrics.mjs` und das E2E-Spec dieselbe Wahrheit lesen wie das Python-Gate.

## 9. Nebenbefunde & Follow-ups (nicht Teil dieses PRs)

- `data/cwv_manifest.json` ist am Stand von `main` **veraltet**: er zählt `.avif` nicht mit (committed 1028
  Bilder vs. real 1538 inkl. avif, 41 MB). Frische Messung: Ampel GRÜN, `--strict-build` grün. Der Refresh
  gehört in einen eigenen Gate-Commit (`python3 scripts/cwv_guard.py --strict-build`), nicht in diesen Feature-PR.
- Sommer-Saison hat die dünnste Keyword-Deckung (genau 3 Treffer) – redaktionell nachschärfen, sobald neue
  Sommer-Beiträge erscheinen; das Gate meldet Fallback-Nutzung laut, sobald `min_artikel` nicht aus Keywords reicht.
- Optionale Ausbaustufe: saisonales OG-/Pinterest-Hero-Bild je Saison (bräuchte eigene Assets + Brand-Prüfung).

---
_Erzeugt am 2026-09-20 im Zuge von Branch `arena/01a0bed1-franksfinanzcheck-blog`. Alle Zahlen aus gemessenen
Läufen: `hugo --minify` (Extended 0.164.0), `e2e/design-metrics.mjs`, `scripts/saisonale_startseite_guard.py`,
`scripts/tests/test_saisonale_startseite.py`, `npx playwright test`._
