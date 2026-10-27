# SEO-Audit nach Seobility-Vorgabe – HIGHEND, 27.10.2026

> **Auftrag:** „Blog auf Highend-Level einer Profi-Agentur optimieren" –
> Grundlage: Seobility-SeoCheck der Startseite
> (`https://franksfinanzcheck.de/`, Modus „Standard" = Crawl ohne JavaScript).
> **Ergebnis in einem Satz:** Alle Befunde, die im Repository heilbar sind,
> sind geheilt und durch eigene Wachen gegen Rückfall gesichert –
> 503 Links ohne Linktext auf 122 Seiten → **0**, 665 zu lange Ankertexte →
> **336** (keiner mehr über 80 Zeichen), Karten tragen genau einen
> Titel-Link. Der einzige *kritische* Befund (Backlinks) ist nicht per Code
> lösbar; er hat jetzt eine gemessene Kadenz (heute ROT), einen fertigen
> Einbett-Block als Angebot und einen 4-Wochen-Plan – statt einer Bitte.

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

### 2.6 Doppelter Ankertext im Footer – bewusst **nicht** gestrichen

Der erste Anlauf hat den „Suche"-Link aus dem Footer entfernt, weil Seobility
ihn als „Ankertext mehrfach verwendet" zählt. Das war falsch: `e2e/suche.spec.mjs`
hält fest, dass die Suche von **jeder** Seite erreichbar ist, und ein zweiter
Weg ist für Tastatur- und Sprachbedienung wertvoller als ein Hinweis im
Crawler-Report. Die Streichung ist zurückgenommen – der Hinweis bleibt stehen
und wird hier als solcher ausgewiesen. `Impressum`/`Datenschutz` bleiben aus
demselben Grund doppelt (rechtlich erwartete Erreichbarkeit, siehe §4.2).

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
| Links insgesamt | 11.321 | 11.565 |
| **Links ohne Linktext** | **503** | **0** |
| **Seiten mit Links ohne Linktext** | **122 von 262** | **0** |
| Bilder ohne `alt`-Attribut | 0 | 0 |
| Markenlogo mit `alt=""` (Seobility-Befund) | 122 Seiten | 0 (Alt + Linkname gesetzt) |
| Startseite: Links / davon ohne Text | 59 / 11 | 62 / **0** |
| Startseite: Titelwörter in H1/H2 nicht abgedeckt | 2 („Geld sparen", „Verträge") | **0** |
| Teilen-Aktionen mit sichtbarem Text | 0 | 4 (Artikel + Startseite) |
| **Ankertexte > 60 Zeichen** | **665** | **336** (davon 0 über 80) |
| Karten mit genau einem Titel-Link | 0 | 323 (6 Familien) |

Reproduzierbar: `hugo --minify --cleanDestinationDir` → `npm run links:check`.

---

## 4. Kartenlinks und Ankertexte: repariert, nicht entschuldigt

Die erste Fassung dieses Berichts hatte zwei Punkte als „bewusst nicht
geändert" abgelegt – 665 zu lange Ankertexte und die 0 % bei den externen
Faktoren. Beides war eine Erklärung, keine Reparatur. Beides ist jetzt
erledigt; was hier steht, ist das Ergebnis, nicht die Rechtfertigung.

### 4.1 665 zu lange Ankertexte → 336, keiner mehr über der Fehlergrenze

Der Seobility-Hinweis „Linktexte zu lang" traf fast ausschließlich die
**Kartenlinks**. Eine Karte trug bisher *einen* Link, der Titel,
Beschreibung, Zähler und CTA umschloss: semantisch korrekt, als Ankertext
unbrauchbar. Der frühere Einwand (WCAG 2.5.3 „Name enthält sichtbaren
Text") war kein Hindernis, sondern eine Beschreibung des Problems – er lässt
sich mit einem Titel-Link plus Overlay erfüllen:

| Vorher | Nachher |
|---|---|
| ein `<a>` um die ganze Karte | **genau ein** `<a class="…__title-link">`, Text = Kartentitel |
| Karten-Titel als `<h3>` ohne Link | Titel bleibt Überschrift, wird zum Link |
| CTA/„Weiterlesen" ein zweiter Link | `aria-hidden`, Trefferfläche via `::after { inset: 0 }` |
| Klick-Handler am Link | `data-klick*` am `<article>` (ein Ziel, eine Fläche) |
| Fokusring am Link | `:has(:focus-visible)` markiert die ganze Karte |

Umgesetzt in sechs Familien: Themenwelten (`.ff-topic-card`), Saison
(`.ff-saison-card`), Ratgeber-Pillar (`.ff-pc-card`), „Das könnte dich auch
interessieren" (`.ff-related-card`), Werkzeug-Raster (`.ff-wz-karte`),
Werkzeug → Ratgeber (`.ff-wz-weiter__karte`). Messung im Build: **323 Karten,
jede mit genau einem Link** (`article` je Familie, `len(a) == 1`).

Damit WCAG 2.5.3 weiterhin gilt, sind drei Dinge gleichzeitig erfüllt:
Der Linkname ist der sichtbare Kartentitel (keine `aria-label`-Kunstgriffe),
die **Trefferfläche** ist per Inset-Overlay die ganze Karte (für Maus und
Touch ändert sich nichts), und der Tastaturfokus liegt sichtbar auf der
Karte, nicht auf einem 3 cm breiten Textstück.

Die beiden Gates, die den alten DOM einfroren, sind mitgezogen – nicht
abgeschaltet: `scripts/themenwelten_guard.py` und
`scripts/saisonale_startseite_guard.py` prüfen jetzt Titel-Link,
Overlay-Ziel, `aria-hidden` der Deko-Teile und weiterhin die Inhalte
(6 Themen, Ziele, Live-Zähler, 366 Kalendertage). Dieselbe Umstellung in
`scripts/themenwelten_browser_test.mjs`, `e2e/a11y-axe.spec.mjs`,
`e2e/saisonale-startseite.spec.mjs`.

Die Wache hat dafür eine vierte Regel bekommen, statt eine Ausnahmeliste zu
wachsen:

| Regel | Prüft | Bewertung |
|---|---|---|
| **L1** | `<a href>` ohne sichtbaren Text | Fehler |
| **L2** | `<img>` ohne `alt` | Fehler |
| **L3** | `alt=""` · Ankertext > 60 Zeichen | Hinweis |
| **L4** | Ankertext eines **Kartenlinks** > 80 Zeichen | Fehler |

Die frühere Fassung von L4 maß 80 Zeichen auf *allen* Links und erzeugte 14
Fehlalarme (FAQ-Links, `aside.ff-weiterrechnen`, der externe Quellenlink) –
die Quittung dafür, eine Regel zu breit zu ziehen. L4 greift jetzt nur,
wenn die Klasse des Links oder eines Vorfahren auf `card`, `karte`, `tile`
oder `entry-title` passt und die Seite indexierbar ist. Kein Whitelisting.

Zusätzlich an der Ursache geheilt: `layouts/_partials/weiterrechnen_box.html`
hatte den Werkzeugnamen **und** die Beschreibung im Anker. Der Anker heißt
jetzt nur noch wie das Werkzeug, die Beschreibung steht in einem
Geschwister-`<span class="ff-weiterrechnen__kurz">`.

**Was von den 336 langen Ankertexten übrig bleibt – und warum das kein
Defekt ist:**

| Anzahl | Wo | Bewertung |
|---|---|---|
| 151 | redaktionelle Fließtext-Links (Werkzeugnamen, Partner-Fallback „Falls nicht automatisch: weiter zum …") | gewollt: der Satz ist der Linktext, kein Kartenmuster |
| 120 | Blättern `« Vorherige <Titel>` / `Nächste <Titel>` | Ziel wird benannt; Kürzung würde Orientierung kosten, Seobility prüft die Startseite |
| 65 | Quellenzeilen `ff-quellen__link` (Studienname/Herausgeber) | Zitat ist der Name der Quelle – Kürzen wäre Genauigkeitsverlust |

Alle drei Gruppen sind reine Hinweise (L3), keine Fehler, und keine davon
liegt über 80 Zeichen.

### 4.2 Was weiterhin bewusst unverändert bleibt

**a) Doppelte Ankertexte (Impressum, Datenschutz, Über mich, Daten &
Studien, So arbeiten wir, Transparenz & Werbung).** Das sind
Navigations-/Rechtslinks in Menü **und** Footer. Sie zu entdoppeln würde
entweder die rechtlich erwartete Erreichbarkeit oder wertvolle siteweite
Internal Links (z. B. `/studien/`, `/transparenz/`) kosten. Beides wäre
schlechter als der Hinweis. Entfernt wurde nur die echte Doppelung ohne
zweiten Weg (`Suche`, §2.6).

**b) 318 kB HTML der Startseite.** Die Dateigröße ist zu ~80 % das
absichtlich **inline** eingebettete Stylesheet (CLS-/FOUC-Fix,
`layouts/_partials/head.html`). Ein Aufsplitten in kritisches CSS ist ein
Performance-Projekt mit eigenem Messplan – nicht Teil dieses Auftrags.

**c) `og:image` der Artikel ist 1000×1500 (Pinterest-Format).** Für
Mastodon/LinkedIn wäre ein 1200×630-Pressschnitt besser. Das braucht
Bildstrecken in der Cover-Pipeline (`covers_manifest`, `image_optimizer`),
keine Template-Änderung – als nächster Schritt vermerkt.

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

### 5.1 Die eine Zahl, die den Score bewegt: Kadenz

Ein Programm, das stillsteht, sieht aus wie ein Programm, das nichts findet.
Deshalb hat `scripts/backlink_automation.py` jetzt eine Kennzahl, die
**nur** die menschliche Tätigkeit zählt – nicht die Menge der Prospects:

```bash
npm run backlink:kadenz          # Exit 1, solange ROT
npm run backlink:kadenz:json     # maschinenlesbar (letzte_kontaktaufnahme,
                                 # tage_seit_kontakt, in_7, in_28, ziel, offen,
                                 # gewonnen, gesamt, urteil, satz)
```

Ziel: **5 Aktionen pro Woche** (`KADENZ_ZIEL_WOCHE = 5`), gezählt aus den
Kontaktzeitstempeln im CRM, nicht aus einer Selbsteinschätzung. Stand heute:

```
Kadenz: 0/5 Aktionen (7 Tage) · 0 in 28 Tagen · letzter Kontakt: nie · gewonnen: 0 → ROT
```

Das steht so auch im Wochenbericht (`BACKLINK-REPORT.md`, Abschnitt
„Kadenz") und in der Konsole des Workflows. Zehn neue Selbsttest-Fälle
halten die Rechnung fest (25 Fälle, alle grün) – darunter der Fall „Status
`kontaktiert` ohne Zeitstempel zählt nicht", damit sich niemand die Zahl
schönsetzt.

Der Score bleibt trotzdem bei 0 %, bis gesendet wird. Das ist keine
technische Lücke mehr, sondern eine offene Aufgabe mit einer Zahl davor.

### 5.2 Der Hebel, der ohne Gegenleistung funktioniert: ein fertiger Einbett-Block

Ein Redakteur, der eine Grafik einbauen will, muss drei Dinge tun: Bild
finden, Quellenzeile formulieren, verlinken. Jeder dieser Schritte ist eine
Gelegenheit, den Link weglassen. Deshalb liefert die Seite den fertigen
Block – Bild und Quellenzeile, beides mit absolutem Link, ohne Skript,
ohne iframe, ohne Tracking-Parameter:

```html
<figure>
  <a href="https://franksfinanzcheck.de/studien/fixkosten-index-2026-q4/">
    <img src="https://franksfinanzcheck.de/downloads/fixkosten-index-2026-q4-pressegrafik.svg"
         width="1200" height="628" alt="Modellrechnung mit 925 Euro Stromkosten, …" loading="lazy">
  </a>
  <figcaption>Grafik: <a href="https://franksfinanzcheck.de/studien/fixkosten-index-2026-q4/">FranksFinanzcheck, Fixkosten-Index Deutschland: Energie-Baseline Q4 2026</a></figcaption>
</figure>
```

Live an zwei Stellen, wo die Zielgruppe tatsächlich landet:
`/studien/fixkosten-index-2026-q4/` (Abschnitt „Nutzung und Zitierweise")
und `/presse/` (dort mit Linkziel *Ausgabeseite*, nicht Presseseite).
Ein Klick kopiert den Code (Clipboard-API, ehrlicher Fallback: der Text
steht sichtbar und markierbar im `<pre>`).

Die Überschrift steht bewusst **vor** der `<section>`: Der Chunker-Vertrag
in `scripts/layout_audit.py` verlangt, dass jede H2 mit `id` im Artikelinhalt
ein direkter Block des Inhalts bleibt – sonst reißt die Text-Teilung den
Container auf. Derselbe Lauf hat den Link-Scanner des Audits gehärtet
(`<pre>`-Blöcke sind Text, kein Markup – sonst meldet das Code-Beispiel
selbst „kaputte interne Links“).

Abgesichert durch eine eigene Wache, weil ein fehlerhaftes Angebot
schlimmer ist als keins – ein relativer `src` zeigt beim Einbau auf die
*fremde* Domain, ein `nofollow` bittet um genau den Link, den die Seite
nicht bekommt:

| Regel | Prüft | Bewertung |
|---|---|---|
| **E1** | Block hat einen Namen (`aria-labelledby` → existierende Überschrift **außerhalb** der Section) | Fehler |
| **E2** | genau ein `<figure>`/`<img>`, `src` absolut, `width`/`height`, `alt` | Fehler |
| **E3** | Bild und Quellenzeile absolut, **gleiches** Ziel, kein `nofollow` | Fehler |
| **E4** | kein Kampagnen-Parameter (`utm_*`, `gclid`, `fbclid`, `ref`, …) | Fehler |
| **E5** | kein `<script>`, `<iframe>`, `<form>`, `<object>`, `<embed>` | Fehler |
| **E6** | Kopier-Knopf zeigt auf die `<pre>`-ID, `role="status"` vorhanden | Fehler |

`scripts/einbetten_wache.py` läuft mit `npm run links:check` und hat
9 Selbsttest-Fälle plus 12 Regressionstests. Auch hier: fail-closed – ein
**verschwundener** Block („0 Blöcke") ist rot.

Was das für die Kadenz bedeutet: Der Pitch an eine Redaktion ist ab jetzt
ein Zweizeiler mit Link auf `/presse/` statt einer Bitte um einen Gefallen.

**4-Wochen-Plan (Kapazität 5 Aktionen/Woche, aus dem Wochenpack – genau die
Zahl, die `npm run backlink:kadenz` misst):**

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
| `scripts/linktext_wache.py` | ✅ 262 Seiten, 11.443 Links, 0 Befunde (vorher 503) · L1–L4 · Selbsttest + 18 Unit-Tests grün |
| `scripts/einbetten_wache.py` (neu) | ✅ 2 Einbett-Blöcke, E1–E6 sauber · 9 Selbsttest-Fälle + 12 Unit-Tests grün |
| `scripts/themenwelten_guard.py` · `saisonale_startseite_guard.py` | ✅ auf dem neuen Karten-DOM (Titel-Link, Overlay, Deko `aria-hidden`) |
| `scripts/werkzeuge_gate.py` · `fixkosten_kompass_guard.py` | ✅ Quelle + Build |
| `scripts/layout_audit.py` · `scripts/entity_marken_gate.py` | ✅ Kritisch 0 (vorher 2 Chunker-Verstöße durch die Einbett-Überschrift) · Quelle 0 Fehler (ein „Franks Finanzcheck" in einem Artikel korrigiert) |
| `scripts/a11y_audit.py` | ✅ 0 Probleme, 0 Kontrast-Fehler (hell + dunkel) |
| `scripts/h1_wache.py` | ✅ jede Seite genau eine H1 |
| `scripts/seo_cockpit.py --strict` | ✅ 122 Seiten, 99 indexierbar, P1/P2/P3 = 0 |
| `scripts/layout_audit.py` | ✅ 0 kritische Befunde (Chunker-Vertrag grün, 1.995 Überschriften geprüft) |
| `scripts/check_internal_links.sh` | ✅ 3.988 interne Links, 0 defekt |
| `scripts/entity_marken_gate.py` | ✅ Quelle 0 Fehler (3× „Franks Finanzcheck" in einem Reserve-Entwurf auf die Markenschreibweise korrigiert) · Build: 0 Fehler, 1 ausgewiesene Warnung E9 (Marken-Title-Abdeckung, vorbestehend) |
| `scripts/integrity_guard.py` | ✅ Siegel neu signiert (50 Kerndateien, Herkunft im Lock) – die vier geänderten Layouts stehen mit ihren Commits im `data/integrity_lock.json` |
| `scripts/reserve_recert.py --check` | ⚠️ 1 erwartete Folge: Die Textkorrektur im Entwurf entwertet dessen byte-genaues Zertifikat. `--fix` braucht `hunspell` (hier nicht installierbar); der Bot-Watchdog (`.github/workflows/bot-watchdog.yml`) zieht die Nachzertifizierung beim nächsten Lauf nach. Bewusst rot statt gefälscht |
| `scripts/vergleichsgrundsaetze_gate.py` | ✅ 20 Routen, 74 Offenlegungs-Bausteine, 0 Fehler |
| `scripts/offenlegung_gate.py` | ✅ 75 Seiten, 0 Fehler |
| `scripts/brand_surface_guard.py --only readme` | ✅ ROT 0 · GELB 0 |
| `scripts/wachen_vertrag.py` | ✅ 340 Skripte, 0 Funde (inkl. der neuen Wache) |
| Unittest-Suite der berührten Wachen | ✅ 279 Tests, 5 übersprungen, 0 Fehler |
| `scripts/metadaten_wache.py` | ⚠️ 3 **vorbestehende** Inhaltsbefunde (2× `lastmod` vor `date`, 1× fehlende Kurzantwort in `content/posts/2026-10-24-bankgebuehren-…`) – nicht Teil dieser Änderung |
| `npx playwright test` (E2E, Desktop + Mobil) | ✅ **180 Tests grün** (lokal mit dem im Repo gepinnten Chromium-Bundle) |
| `node scripts/themenwelten_browser_test.mjs --public public` | ✅ 426 Prüfungen (Tastatur, Trefferfläche, Kontrast, 200 % Text, ohne JS) |
| `npm run suchindex` (Pagefind) | ✅ 262 Seiten, 99 indexierbar – im E2E-Vorlauf grün |

**Nicht geprüft, weil ohne Freigabe nicht zulässig:** die neue Wache in
`.github/workflows/**` zu hängen (Sicherheitsregel 3 in CLAUDE.md). Vorlage
stehen in `docs/ENTWICKLER-WERKZEUGE.md`, Abschnitte „Linktexte und
Alt-Texte" und „Einbett-Blöcke".

---

## 7. Erwartete Wirkung bei der nächsten Seobility-Prüfung

| Check | vorher | Erwartung |
|---|---|---|
| Bilder-Optimierung | Warnung 0/1 | **1/1** (Logo trägt Alt und Markennamen) |
| Links | 71 % | „8 Links ohne Linktext" weg, eine Doppelung weniger, „Linktexte zu lang" von 665 auf 336 und keiner mehr über 80 Zeichen (§4.1) |
| Soziale Vernetzung | Warnung 0/1 | **1/1** (vier textbeschriftete Teilen-Ziele auf der Startseite) |
| Seitenqualität | 93 % | Title-Wörter vollständig in H1/H2 |
| Externe Faktoren | 0 % | **bleibt 0**, bis gesendet wird. Die Kadenz (§5.1) macht das sichtbar (heute ROT), der Einbett-Block (§5.2) macht das Senden leichter |

Der Check läuft gegen die **Live-Site**. Die Wirkung tritt erst nach dem
Deploy ein; die Startseite selbst bleibt strukturell unverändert (keine
Layout-, Farb- oder Hero-Änderung), damit die Wirkung eindeutig dem
Befund zugeordnet werden kann.
