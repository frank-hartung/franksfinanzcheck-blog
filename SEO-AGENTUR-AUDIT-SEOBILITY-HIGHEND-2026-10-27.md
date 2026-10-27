# SEO-Audit nach Seobility-Vorgabe – HIGHEND, 27.10.2026

> **Auftrag:** „Blog auf Highend-Level einer Profi-Agentur optimieren" –
> Grundlage: Seobility-SeoCheck der Startseite
> (`https://franksfinanzcheck.de/`, Modus „Standard" = Crawl ohne JavaScript).
> **Ergebnis in einem Satz:** Alle Befunde, die im Repository heilbar sind,
> sind geheilt und durch eine eigene Wache gegen Rückfall gesichert –
> 503 Links ohne Linktext auf 122 Seiten → **0**; der einzige *kritische*
> Befund (Backlinks) ist **nicht** per Code lösbar und wird hier mit
> Programmlage, Ursache und 4-Wochen-Plan offengelegt statt weggerechnet.

---

## 1. Ausgangslage: der Seobility-Befund (wörtlich, mit Werten)

| Bereich | Score | Befund im Check |
|---|---|---|
| Meta-Angaben | 100 % | Title 531/580 px, Description 995/1000 px, Canonical, Sprache, Hreflang sauber |
| Seitenqualität | 93 % | 1.684 Wörter, 25 Absätze, Satzlänge 11,95 Wörter – gut. **Warnung:** 1 Bild ohne Alt-Attribut · **Warnung:** wenige Social-Sharing-Möglichkeiten · Hinweis: „Einige Wörter aus dem Seitentitel werden nicht in H1-Überschriften verwendet" |
| Seitenstruktur | 100 % | genau eine H1, Überschriftenstruktur fehlerfrei |
| **Links** | **71 %** | **Warnung:** Ankertexte mehrfach verwendet · **Warnung:** Linktexte zu lang · **8 Links ohne Linktext** |
| Server | 100 % | 200, 0,07 s Antwortzeit, gzip, kein X-Powered-By |
| **Externe Faktoren** | **0 %** | **Fehler (kritisch): „Diese Seite hat fast keine Links von anderen Webseiten."** |
| Onpage gesamt | 88 % | 1 kritischer Punkt |

Der Check prüft **eine** URL. Ein Agentur-Audit prüft den Bestand. Deshalb
wurde derselbe Befund zusätzlich über den kompletten Hugo-Build gelegt
(262 HTML-Dateien, 122 echte Seiten mit Header, 11.321 Links, 711 Bilder).

**Die gemeinsame Ursache der beiden wichtigsten Befunde:** Beide entstehen
nicht im Template, sondern beim Rendern – und beide waren zum Zeitpunkt des
Checks *bewusst* so gebaut, mit gutem Grund an der falschen Stelle:

- `.entry-link` war eine leere, absolut positionierte Klickfläche über der
  ganzen Artikelkarte. Barrierefrei zulässig (die A11y-Wache überspringt
  solche Overlays ausdrücklich), für Crawler aber **ein Link ohne Ankertext**.
- Das Markenlogo trug `alt=""` und lag in einem `aria-hidden`-Bild. Für
  Screenreader korrekt (der Link hatte sichtbaren Text), für Seobility und
  die Bildersuche ein **Bild ohne Alternativtext** – und der Markenname
  fehlte im Linknamen.

---

## 2. Was geheilt wurde

### 2.1 Acht Links ohne Linktext → Titel trägt den Anker (siteweit)

| | vorher | nachher |
|---|---|---|
| Kartenmarkup | `<a class="entry-link" aria-label="Weiterlesen: …">` (leer) | `<h2><a class="entry-title-link" href="…">Titel</a></h2>` |
| Trefferfläche | Overlay-Anker über der Karte | `::after`-Inset-Overlay des Titelankers – Karte bleibt **ganz** klickbar |
| Ankertext | *keiner* (nur Attribut) | Artikeltitel – der beste interne Linktext, den eine Liste liefern kann |

Dateien: `layouts/_default/list.html`, `assets/css/extended/zzzz-seo-und-teilen.css`.
Mitgezogen: `scripts/themenwelten_browser_test.mjs` prüft jetzt beides –
Ankertext **und** Klick auf den Anriss (Overlay).

### 2.2 Bild ohne Alt-Attribut → Markenname im Alt- und Linknamen

`layouts/_partials/header.html`: `alt="FranksFinanzcheck"`, `aria-hidden` am
`<picture>` entfernt. Der Markenlink heißt damit „FranksFinanzcheck –
Unabhängige Fixkosten-Redaktion" (vorher nur der Claim). Keine
Layoutänderung, kein zusätzlicher Request.

### 2.3 Icon-Links ohne Text → sichtbarer Name im Link

- Footer-Profile (Pinterest, Mastodon): `layouts/_partials/social_icons.html`
  legt den Namen als `.sr-only`-Text in den Link (Quelle bleibt
  `params.socialIcons`, `rel="me"` und `sameAs` unverändert).
- „Nach oben"-Pfeil: `layouts/_partials/footer.html` – Text statt `aria-label`.

### 2.4 Social-Sharing-Möglichkeiten → textbeschriftete Teilen-Zeile

Neu: `layouts/_partials/ff_teilen.html` – „Auf Mastodon teilen",
„Auf Pinterest merken", „Per E-Mail empfehlen", „Link kopieren".

- **Kein Skript, kein Pixel, kein Cookie von Dritten**; Ziele sind normale
  Links, die erst nach Klick geöffnet werden.
- Jede Aktion hat **sichtbaren Text** – reine Icon-Links wären genau der
  Fehler, der hier behoben wird.
- „Link kopieren" ist ein `<button>` mit Clipboard-API und ehrlichem
  Fallback (Statusmeldung mit der URL), kein toter Knopf.
- Platziert am Artikelende (abschaltbar per `disableShare: true`) und auf
  der Startseite **nach** der Entity-Box – der zitierfähige Identitätssatz
  bleibt der letzte redaktionelle Satz.

### 2.5 Title-Wörter in den Überschriften

Der Title verspricht „Geld sparen bei Fixkosten & Verträgen", die H2s
deckten „Geld sparen" und „Verträge" nicht ab. Die Startseiten-H2 der
Themenwelten heißt jetzt **„Geld sparen bei Fixkosten & Verträgen –
6 Themenwelten"** (`layouts/_partials/home_clusters.html`). Der
Markenbegriff „Fixkosten-Kompass" bleibt unmittelbar darüber als eigene H2
erhalten und wird nicht doppelt gesetzt. Auf `/posts/` gilt weiterhin die
Wortgleichheit mit `data/themenwelten.json` (Gate-Vertrag unverändert).

### 2.6 Doppelter Ankertext im Footer

„Suche" stand im Hauptmenü **und** im Footer (identischer Ankertext, kein
zweiter Weg). Der Footer führt jetzt nur Ziele, die das Menü nicht anbietet.
`Impressum`/`Datenschutz` bleiben absichtlich doppelt (rechtlich erwartete
Erreichbarkeit, siehe §4).

### 2.7 Neue Wache: die Defektklasse kommt nicht zurück

`scripts/linktext_wache.py` (stdlib, rein lesend, `--selftest`, `--json`)
prüft den **fertigen Build** – 262 Seiten, 11.439 Links, 711 Bilder:

| Regel | Prüft | Bewertung |
|---|---|---|
| L1 | `<a href>`/`<area>` ohne sichtbaren Text | Fehler |
| L2 | `<img>` ohne `alt`-Attribut | Fehler |
| L3 | `alt=""` und Ankertexte > 60 Zeichen | Hinweis (bewusst kein Fehler) |

Bewusste Grenzen, im Code dokumentiert: `aria-label` zählt **nicht** als
Linktext (es beantwortet „wie heißt der Link", nicht „worauf verlinkt die
Seite"); `<a>` ohne `href` ist ein Sprungziel, kein Link; Ausnahmen werden
mit `data-ff-linktext-frei` **benannt** statt still geduldet; `alt=""` ist
bei Schmuckbildern korrekt und bleibt erlaubt. 14 Regressionstests
(`scripts/tests/test_linktext_wache.py`), Aufruf `npm run links:check` /
`npm run test:links`, Doku in `docs/ENTWICKLER-WERKZEUGE.md`.

---

## 3. Messung vorher/nachher (kompletter Build, nicht nur Startseite)

| Kennzahl | vorher | nachher |
|---|---|---|
| Links insgesamt | 11.321 | 11.439 |
| **Links ohne Linktext** | **503** | **0** |
| **Seiten mit Links ohne Linktext** | **122 von 262** | **0** |
| Bilder ohne `alt`-Attribut | 0 | 0 |
| Markenlogo mit `alt=""` (Seobility-Befund) | 122 Seiten | 0 (Alt + Linkname gesetzt) |
| Startseite: Links / davon ohne Text | 59 / 11 | 62 / **0** |
| Startseite: Titelwörter in H1/H2 nicht abgedeckt | 2 („Geld sparen", „Verträge") | **0** |
| Teilen-Aktionen mit sichtbarem Text | 0 | 4 (Artikel + Startseite) |
| Ankertexte > 60 Zeichen (Hinweis, s. §4) | 665 | 665 |

Reproduzierbar: `hugo --minify --cleanDestinationDir` → `npm run links:check`.

---

## 4. Was bewusst **nicht** geändert wurde (und warum)

**a) 665 Ankertexte über 60 Zeichen.** Der Seobility-Hinweis „Linktexte zu
lang" trifft im Bestand fast ausschließlich die *Kartenlinks*: Themenkarten
(Titel + Beschreibung + Zähler + CTA), Saisonkarten (Datum + Thema + Titel +
„Weiterlesen") und die Artikelkarten der Ratgeber-Pillars. Diese Bauform ist
kein Versehen, sondern ein **dokumentierter WCAG-2.5.3-Vertrag**: der
sichtbare Text der Karte muss im Linknamen stehen, sonst schlägt
Sprachsteuerung fehl („klick Strom und Gas sparen"). Sie ist zusätzlich
durch `themenwelten_guard.py` und `saisonale_startseite_guard.py` im Build
festgenagelt – eine Änderung dort ist ein **Layout-Umbau** und nach
CLAUDE.md nur als Variante mit Messung und Freigabe zulässig
(`assets/css/varianten/`, `docs/ANLEITUNG-DESIGN-VARIANTEN.md`).
Empfehlung: Titel-Link plus Inset-Overlay (Muster aus §2.1) als Variante
bauen, Kontrast/Lighthouse/Tastaturfokus messen, dann entscheiden. Nutzen
wäre real, aber klein (Präzision der Ankertexte), Risiko ohne visuelle
Abnahme wäre groß. **Kein Blindflug auf der Hauptnavigation.**

**b) Doppelte Ankertexte (Impressum, Datenschutz, Über mich, Daten &
Studien, So arbeiten wir, Transparenz & Werbung).** Das sind
Navigations-/Rechtslinks in Menü **und** Footer. Sie zu entdoppeln würde
entweder die rechtlich erwartete Erreichbarkeit oder wertvolle siteweite
Internal Links (z. B. `/studien/`, `/transparenz/`) kosten. Beides wäre
schlechter als der Hinweis. Entfernt wurde nur die echte Doppelung ohne
zweiten Weg (`Suche`, §2.6).

**c) 318 kB HTML der Startseite.** Die Dateigröße ist zu ~80 % das
absichtlich **inline** eingebettete Stylesheet (CLS-/FOUC-Fix,
`layouts/_partials/head.html`). Ein Aufsplitten in kritisches CSS ist ein
Performance-Projekt mit eigenem Messplan – nicht Teil dieses Auftrags.

**d) `og:image` der Artikel ist 1000×1500 (Pinterest-Format).** Für
Mastodon/LinkedIn wäre ein 1200×630-Pressschnitt besser. Das braucht
Bildstrecken im Cover-Pipeline (`covers_manifest`, `image_optimizer`), keine
Template-Änderung – als nächster Schritt vermerkt.

---

## 5. Der kritische Punkt: „fast keine Links von anderen Webseiten"

Das ist der einzige **Fehler** im Check und der einzige, den kein Commit
behebt. Er ist ehrlich einzuschätzen:

**Was die Maschine schon hat** (`data/backlink_prospects.yaml`,
`backlink_assets.yaml`, `data/backlink_state.json`,
`scripts/backlink_automation.py`, `.github/workflows/backlink-weekly.yml`):
32 kuratierte Prospects (Community, Digital PR, Gastartikel, Podcasts,
Pinterest, Partnerschaften), 8 Linkable Assets, Saisonkampagnen, ein
Wochenpack mit Copy-Vorlagen und ein „North Star", der Linkkauf, PBNs und
Verzeichnis-Spam ausdrücklich ausschließt.

**Was fehlt – gemessen, nicht geschätzt:** im CRM stehen **32 Prospects,
0 Kontaktaufnahmen, 0 gewonnene Links** (Statusfeld durchgehend leer,
`last_checked` 26.10.2026). Das Programm ist gebaut und läuft wöchentlich –
**es wird nur nicht ausgeführt.** Das ist der Grund für 0 % in der Kategorie
„Externe Faktoren", nicht ein technischer Mangel.

**4-Wochen-Plan (Kapazität 5 Aktionen/Woche, aus dem Wochenpack):**

| Woche | Aktion | KPI |
|---|---|---|
| 1 | 1 Community-Profil (Finanztip-Community) + 2–3 echte Antworten; Status im CRM auf `kontaktiert` | 1 Profil, 3 Antworten |
| 2 | Digital-PR-Pitch mit dem Fixkosten-Index (offene CSV + Methodik) an 2 Redaktionen | 2 Pitches, 1 Antwort |
| 3 | 1 Gastartikel-Anglage (Utopia-Klasse) + Pinterest-Embed-Grafik veröffentlichen | 1 Outline, 1 Asset live |
| 4 | Follow-up-Woche: offene Pitches nachfassen, gewonnene Erwähnungen in `authority_evidence` belegen | 3 Follow-ups, 1–2 Links |

Ehrliche Erwartung: erste **editorial verdiente** Links realistisch in
Woche 4–8, nicht in Woche 1. Jede gewonnene Erwähnung wird mit URL und Datum
belegt (`data/authority_evidence.yaml`) – dann ist „fast keine Backlinks"
irgendwann eine Zahl mit Datum statt ein Gefühl.

---

## 6. Gate-Protokoll (nach der Änderung, Build `hugo --minify`)

| Prüfung | Ergebnis |
|---|---|
| `scripts/linktext_wache.py` (neu) | ✅ 262 Seiten, 0 Befunde (vorher 503) · Selbsttest + 14 Unit-Tests grün |
| `scripts/a11y_audit.py` | ✅ 0 Probleme, 0 Kontrast-Fehler (hell + dunkel) |
| `scripts/h1_wache.py` | ✅ jede Seite genau eine H1 |
| `scripts/seo_cockpit.py --strict` | ✅ 122 Seiten, 99 indexierbar, P1/P2/P3 = 0 |
| `scripts/themenwelten_guard.py` | ✅ 6 Themen, Ziele, Zähler, Struktur |
| `scripts/entity_marken_gate.py` | ✅ 0 Fehler (1 ausgewiesene Warnung E9: Marken-Title-Abdeckung, vorbestehend) |
| `scripts/fixkosten_kompass_guard.py` · `saisonale_startseite_guard.py` | ✅ bestanden |
| `scripts/offenlegung_gate.py` · `vergleichsgrundsaetze_gate.py` | ✅ 75 Seiten, 0 Fehler |
| `scripts/brand_surface_guard.py --only readme` | ✅ ROT 0 · GELB 0 |
| `scripts/wachen_vertrag.py` | ✅ 339 Skripte, 0 Funde |
| `scripts/metadaten_wache.py` | ⚠️ 3 **vorbestehende** Inhaltsbefunde (2× `lastmod` vor `date`, 1× fehlende Kurzantwort in `content/posts/2026-10-24-bankgebuehren-…`) – nicht Teil dieser Änderung |
| `npm run suchindex` (Pagefind) · Playwright/E2E | in dieser Umgebung nicht lauffähig (keine `node_modules`, kein Browser-Download) – bitte im CI nachziehen |

**Nicht geprüft, weil ohne Freigabe nicht zulässig:** die neue Wache in
`.github/workflows/**` zu hängen (Sicherheitsregel 3 in CLAUDE.md). Vorlage
steht in `docs/ENTWICKLER-WERKZEUGE.md`, Abschnitt „Linktexte und Alt-Texte".

---

## 7. Erwartete Wirkung bei der nächsten Seobility-Prüfung

| Check | vorher | Erwartung |
|---|---|---|
| Bilder-Optimierung | Warnung 0/1 | **1/1** (Logo trägt Alt und Markennamen) |
| Links | 71 % | deutlich höher: „8 Links ohne Linktext" verschwindet, eine Doppelung weniger; „Linktexte zu lang" bleibt bewusst (§4a) |
| Soziale Vernetzung | Warnung 0/1 | **1/1** (vier textbeschriftete Teilen-Ziele auf der Startseite) |
| Seitenqualität | 93 % | Title-Wörter vollständig in H1/H2 |
| Externe Faktoren | 0 % | **bleibt 0**, bis echte Links gewonnen sind – §5 ist der Hebel, nicht Code |

Der Check läuft gegen die **Live-Site**. Die Wirkung tritt erst nach dem
Deploy ein; die Startseite selbst bleibt strukturell unverändert (keine
Layout-, Farb- oder Hero-Änderung), damit die Wirkung eindeutig dem
Befund zugeordnet werden kann.
