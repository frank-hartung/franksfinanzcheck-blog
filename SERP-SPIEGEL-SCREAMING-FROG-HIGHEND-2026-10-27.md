# SERP-Spiegel: der Screaming-Frog-Befund, dauerhaft geheilt · 27.10.2026

**Ausgangslage:** Ein fremder Crawl (Screaming Frog SEO Spider) legte am
27.10.2026 einen Befundbericht über **eine** URL vor – ausgewiesen mit
„URLs: 1" und „% von Gesamt: 100". Es war ein Lauf über die Startseite, keine
Site-Prüfung. Sechs Meldungen standen darin:

| # | Befund des Crawls | Typ | Was wirklich dahintersteckte |
|---|---|---|---|
| 1 | Fehlender `Content-Security-Policy`-Header | Warnung | GitHub Pages kann keine Header setzen – und der Migrationsweg `static/_headers` trug sie nicht |
| 2 | `X-Content-Type-Options` fehlt | Warnung | dito |
| 3 | `Strict-Transport-Security` fehlt | Warnung | dito |
| 4 | `X-Frame-Options` fehlt | Warnung | dito |
| 5 | `Referrer-Policy` fehlt | Warnung | dito (per `<meta name=referrer>` nur teilweise ersetzt) |
| 6 | Meta-Description über 155 Zeichen / über 985 Pixel | Hinweis | **unser Maßstab war zu großzügig** (160 bzw. 165 Zeichen) |
| 7 | Interner Link ohne Ankertext | Hinweis | Karten- und Nach-oben-Links hatten nur `aria-label`, keinen Text |
| 8 | „H2: Mehrere" | Warnung | kein Befund – aber vier Seiten sprangen in der Rangfolge (h1→h3, h2→h4) |

**Ergebnis:** Sieben der acht Punkte sind geheilt, der achte ist als
Nicht-Befund belegt. Kein Punkt war ein Fehlalarm des Werkzeugs – in fünf von
acht Fällen war unsere eigene Messung zu nachsichtig, in drei Fällen fehlte
sie ganz. Alle fünf Messlücken sind jetzt an einer Stelle geschlossen und
verdrahtet.

> Dieser Bericht ist der Wahrheitsort für diese Runde. Die Regeln für künftige
> Arbeiten stehen in `CLAUDE.md` („Ein Snippet ist 155 Zeichen und 985 Pixel"
> und „Kopfzeilen stehen an einer Stelle").

---

## 1 · Warum ein Befund über *eine* Seite ein Site-Befund ist

Der Crawl sah die Startseite. Die Ursachen dahinter sind aber nicht
seitenindividuell: Header setzt der Hoster (alle Seiten), Description-Länge
erzeugt der Text (alle Seiten), Ankertext erzeugt das Listen-Template (alle
Listen). Deshalb wurde nicht die eine gemeldete URL repariert, sondern der
**ganze Build** gemessen – 122 Seiten, davon 99 indexierbar:

```bash
hugo --minify --cleanDestinationDir --environment production
python3 scripts/seo_cockpit.py --build public --fail-on \
  description-length,description-breite,link-no-anchor,heading-order
```

Vorher: **0 Befunde** (das Cockpit erlaubte 165 Zeichen und prüfte Ankertext
gar nicht). Nach der Nachschärfung am selben Build: **18 Befunde**. Genau
diese Differenz ist der Befund hinter dem Befund.

---

## 2 · Snippet: 155 Zeichen *und* 985 Pixel (Befund 6)

### 2.1 Die zwei Grenzen, die niemand zusammenführte

| Stelle | Grenze vorher | Grenze jetzt |
|---|---|---|
| `scripts/metadaten_wache.py` (Quelle) | 100–**160** Zeichen | 100–155 Zeichen **+ 985 px** |
| `scripts/seo_cockpit.py` (gebautes HTML) | 70–**165** Zeichen | 100–155 Zeichen **+ 985 px** |
| Screaming Frog / Google Desktop | **155** Zeichen, **985** px | Maßstab |

Zwei Grenzen im Haus, keine davon die des Marktes. Ein Gate, das großzügiger
misst als der Markt, meldet Grün und wird vom nächsten Fremdlauf widerlegt.

### 2.2 Eine Zahl, zwei Messstellen

Neu: **`scripts/serp_limits.py`** ist die einzige Quelle für
`DESC_MIN_ZEICHEN = 100`, `DESC_MAX_ZEICHEN = 155`, `DESC_MAX_PX = 985` und das
Breitenmaß. Beide Messstellen **importieren** sie – `test_serp_limits.py`
(Klasse `Bindung`) schlägt fehl, wenn irgendwo eine zweite Grenze im Code
auftaucht:

```python
DESC_MIN, DESC_MAX = serp_limits.DESC_MIN_ZEICHEN, serp_limits.DESC_MAX_ZEICHEN
```

Gemessen wird mit den **Advance-Breiten der Helvetica-Kernmetrik** (Adobe,
1/1000 em, 219 Zeichen) bei 14 px – der Schrift und Größe des
Google-Desktop-Snippets; Arial ist metrisch identisch mit Helvetica. Das ist
eine **Schätzung der Darstellung, keine Browsermessung** – aber eine
deterministische, ohne Netz, ohne Font-Datei, ohne Zusatzpaket. Zeichen ohne
Metrik (Emoji, CJK) werden **nicht** geschätzt: `breite_px()` gibt `None`, die
Wachen melden „nicht prüfbar" (fail-closed statt Wunschzahl).

Warum die Breite überhaupt zählt, zeigt der eigene Bestand: eine Description
mit 135 Zeichen aus breiten Wörtern ergab 1002 px – Zeichenzahl grün, Snippet
abgeschnitten:

```
„Wohngebäude und Wärmewende: Warum Wärmeverlust, Wärmepumpe und Wartung
 zusammengehören. Wer Wohnraum warm hält, spart mit Wärmedämmung."
→ 135 Zeichen · 1002 px · Grenze 985 px
```

### 2.3 Was repariert wurde

**22 Descriptions** neu geschrieben: 11 lagen über 155 Zeichen, 19 über 985 px
(einige in beiden Fenstern), eine enthielt ein Zeichen ohne Breitenmaß.

| Seite | vorher | nachher |
|---|---|---|
| `/` | 156 Z · 1002 px | 147 Z · 941 px |
| `/cockpit/` | 163 Z · 1068 px | 134 Z · 871 px |
| `/pillar/internet-dsl/` | 158 Z · 1061 px | 143 Z · 920 px |
| `/werkzeuge/` | 153 Z · 1005 px | 146 Z · 954 px |
| `/werkzeuge/abschlag-nachzahlung-rechner/` | 158 Z · 1036 px | 143 Z · 938 px |
| … 17 weitere | | |

Nebenbefund, der die Klasse zeigt: **fünf Descriptions endeten mitten im
Satz** („…ohne funktionierende.", „…für drei bis.") – Artefakte einer früheren
Kürzung. Sie sind jetzt vollständige Sätze und trotzdem kürzer.

Dazu kamen vier **Entwürfe**, die kein Crawler sieht, weil ihre URLs
weitergeleitet werden – aber sie sind veröffentlichungsreif und wären beim
nächsten Heben des Entwurfs durch dasselbe Fenster gefallen (mit „…" am Ende).
Dazu zwei `lastmod`-Werte, die vor ihrem `date` lagen, und eine fehlende
Kurzantwort (`2026-10-24-bankgebuehren-…`).

`npm run metadaten:check` ist damit auf **0 Befunden** (vorher 3, plus 6 neue
durch M7).

---

## 3 · Ankertext: ein Link braucht Text, nicht nur `aria-label` (Befund 7)

Der Listen-Template-Baustein erzeugte 137 Karten-Links dieser Form:

```html
<a class="entry-link" aria-label="Weiterlesen: <Titel>" href="…"></a>
```

Dazu 122 „Nach oben"-Links mit nur einem SVG. Für Screenreader benannt, für
Crawler **259 interne Links ohne Ankertext**. `aria-label` ist ein Name für
Hilfstechnik, kein Linktext für Suchmaschinen.

Geheilt an der Ursache – nicht im gebauten HTML:

```diff
-  <a class="entry-link" aria-label="Weiterlesen: {{ .Title | plainify }}" href="{{ .RelPermalink }}"></a>
+  <a class="entry-link" aria-label="Weiterlesen: {{ .Title | plainify }}" href="{{ .RelPermalink }}"><span class="sr-only">Weiterlesen: {{ .Title | plainify }}</span></a>
```

`sr-only` ist eine vorhandene, geprüfte Klasse (1×1 px, `clip`) – der Text ist
im Accessibility-Tree und im DOM, aber nicht sichtbar. `aria-label` bleibt,
weil es **denselben** Ausdruck verwendet: Label und Text können nicht
auseinanderlaufen. `aria-label` allein hätte nicht gereicht, ein sichtbarer
Text hätte das Kartenlayout verändert.

Die Wache dazu ist neu und misst die gerenderte Wahrheit
(`link-no-anchor`, P2): Ein interner Link ohne Text und ohne Bild-Alt ist ein
Befund – auch dann, wenn er ein `aria-label` trägt (dann mit dem Zusatz „nur
aria-label"). Der `<title>` in einem Icon-SVG zählt bewusst **nicht** als
Ankertext; er ist ein Tooltip der Grafik. Nach dem Fix: **0**.

---

## 4 · „H2: Mehrere" ist kein Befund – vier Sprünge waren einer (Befund 8)

Der Crawl sagt es selbst: mehrere `<h2>` sind zulässig, solange die
Rangfolge stimmt. Die Prüfung wurde deshalb **nicht** auf „Anzahl H2"
gebaut, sondern auf **Rangfolge** (`heading-order`, P3). Ergebnis: vier
echte Sprünge, alle geheilt:

| Seite | Befund | Ursache | Heilung |
|---|---|---|---|
| `2026-08-19-energiediebe-…` | h1→h3 | Artikel begann mit `### Dein Schnellstart` | `##` |
| `2026-09-11-guenstig-durch-den-winter-…` | h1→h3 | dito | `##` |
| `2026-10-12-kleine-energiespar-tricks-…` | h2→h4 | `#### LED-Lampen`, `#### Stand-by` | `###` |
| `2026-10-12-waermepumpe-vs-gasheizung-…` | h2→h4 | `#### Pro- und Contra-Tabelle` | `###` |

Ein Sprung ist kein Schönheitsfehler: Er zerreißt die Gliederung, die
Screenreader, „Im Artikel"-Navigation und KI-Antworten lesen. Nach dem Fix:
**0** (und `h1_wache --public` bleibt grün: genau eine H1 je Seite).

---

## 5 · Sicherheits-Header: der eine Punkt, der nicht im Repo endet (Befunde 1–5)

Hier ist Ehrlichkeit wichtiger als eine grüne Zeile.

**Live ändert sich durch dieses Repository nichts.** Die Seite liegt auf
GitHub Pages, und GitHub Pages setzt keine eigenen Antwort-Header. Der Crawl
hat also gemessen, was tatsächlich ausgeliefert wird – **der Befund ist
richtig**. Wirksam werden die Header erst über den Cloudflare-Proxy, und das
ist ein Dashboard-Schritt, kein Commit:

```bash
npm run edge:freigabe        # misst DNS-Proxy, SSL-Modus und die Regel A1
npm run edge:freigabe:apply  # stellt Regel → SSL → DNS idempotent her
npm run header:check:live    # misst die Wirkung an der echten Seite
```

Das Werkzeug dafür existierte bereits (`scripts/cloudflare_edge_freigabe.py`,
Runbook `docs/SICHERHEIT-BETRIEB-RUNBOOK.md` A1). Was fehlte, war der zweite
Auslieferungsweg:

### 5.1 Die Datei, die „Migrationsweg" hieß und nichts schützte

`static/_headers` ist die Datei, die Cloudflare Pages und Netlify lesen – sie
gilt im Haus ausdrücklich als der Weg für einen Umzug. Sie enthielt bis zum
27.10.2026 **ausschließlich Cache-Regeln**. Wer damit umgezogen wäre, hätte
HSTS, `nosniff`, Clickjacking-Schutz, `Referrer-Policy` und CSP **nicht**
mitgenommen: derselbe Befund, eine Woche später, schwerer zu finden.

Jetzt stehen die acht Kopfzeilen dort – und zwar **nicht abgetippt**, sondern
aus der Tabelle A1 in `cloudflare/edge-schutz.md` abgeleitet. `npm run
header:check` (offline, jeder PR) prüft zwei Regeln:

- **S1** Jede Kopfzeile der Vorlage steht mit **exakt** diesem Wert in
  `static/_headers` (fehlt sie oder driftet ein Wert, ist der Lauf rot).
- **S2** Kein Pfad erbt zwei verschiedene Werte derselben Kopfzeile.

S2 ist kein Formalismus. Cloudflare Pages führt **alle** passenden Regeln
zusammen und verbindet gleiche Kopfzeilen mit Komma. Die alte Datei hätte für
`/fonts/inter-variable.woff2` also `Cache-Control: public, max-age=31536000,
immutable` **und** `public, max-age=600` geschickt – zwei widersprüchliche
Anweisungen in einem Header. Deshalb setzt `static/_headers` sein
`Cache-Control` nur dort, wo keine zweite Regel denselben Pfad trifft; HTML
bleibt beim ETag des Hosters. Auf GitHub Pages ist das folgenlos (die Datei
wird ignoriert), auf einem Umzug ist es der Unterschied zwischen „Cache
stimmt" und „Cache streitet sich".

### 5.2 Was zusätzlich über `<meta>` wirkt

Unverändert: Die Meta-CSP im `<head>` trägt `base-uri`, `object-src` und
`form-action`; `frame-ancestors` und HSTS sind per `<meta>` wirkungslos und
stehen dort bewusst **nicht** (die Wache meldet sie als Scheinschutz). Die
`Referrer-Policy` ist zusätzlich als `<meta name="referrer">` gesetzt und
wirkt damit auch ohne Proxy – der Crawl prüft nur den HTTP-Header, deshalb
erscheint sie dort trotzdem als fehlend.

---

## 6 · Was jetzt dauerhaft wacht

| Wache | Prüft | Läuft |
|---|---|---|
| `serp_limits.py` (SSOT) | Grenzen + Arial-Breitenmaß, 219 Zeichen | Basis aller Prüfungen |
| `metadaten_wache.py` M2/M7 | Description 100–155 Z **und** ≤ 985 px, Quelle | `npm run metadaten:check`, PR-Gate |
| `seo_cockpit.py` `description-length`/`-breite`/`-kurz`/`-messbar` | dasselbe am **gebauten** HTML | `npm run serp:check`, PR-Gate |
| `seo_cockpit.py` `link-no-anchor` | interner Link ohne Ankertext | PR-Gate |
| `seo_cockpit.py` `heading-order` | Rangfolge-Sprünge (nicht H2-Anzahl) | PR-Gate |
| `blog_header_gate.py` S1/S2 | `static/_headers` == Vorlage A1, keine Überschneidung | `npm run header:check`, Sicherheits-Wache |
| `blog_header_gate.py` live | die acht Header an der echten Seite | `npm run header:check:live`, täglich |

**Verdrahtung:** `.github/workflows/e2e.yml` fährt bei jedem PR
`seo_cockpit --fail-on description-length,description-breite,link-no-anchor,heading-order`
und `metadaten_wache`; die Sicherheits-Wache fährt `blog_header_gate --offline`
(jetzt inklusive S1/S2) bei Änderungen an `static/**` und `cloudflare/**`.

Bewusst **kein Deploy-Blocker**: Ein zu langes Snippet darf die Auslieferung
der Live-Site nicht anhalten (Hausregel C34), es darf aber nicht unbemerkt
nach `main` wandern. Der PR ist der Ort, an dem die Grenze greift.

### Selbsttests (Sabotage, nicht Beteuerung)

- `python3 scripts/metadaten_wache.py --selftest` → **13 Proben**
  (neu: „Description zu breit bei 135 Zeichen", „Zeichen ohne Breitenmaß")
- `python3 scripts/blog_header_gate.py --selftest` → **27 Fälle**
  (neu: fehlende Kopfzeile, gedrifteter HSTS-Wert, überschneidende Cache-Regeln)
- `npm run test:serp` → `test_serp_limits.py` (18), `test_seo_cockpit.py` (30)
- `python3 -m unittest scripts.tests.test_blog_header_gate` → **47**

### Nachweis am echten Build (27.10.2026)

```
h1_wache --public public            → bestanden (jede Seite genau eine H1)
a11y_audit.py                       → 0 Probleme, 0 Kontrast-Fehler
seo_cockpit --fail-on …             → P1 0 · P2 0 · P3 0
metadaten_wache.py                  → 105 Dateien, 0 Befunde
blog_header_gate --offline          → Vorlage + _headers deckungsgleich (S1/S2)
robustheits_gate --public --strict  → bestanden
werkzeuge_gate --public public      → bestanden
index_hygiene_gate.py               → Crawl-Fläche sauber
```

---

## 7 · Offen – und zwar benannt

1. **Live-Header** (Befunde 1–5): braucht den Cloudflare-Proxy und die
   Transform Rule. Repo-seitig ist alles vorbereitet und geprüft; die
   Sicherheits-Wache misst täglich und meldet den Zustand als `BEFUND`
   (gemessen und mangelhaft) getrennt von `STOERUNG` (nicht messbar).
   Ohne Proxy ist der Befund **nicht** durch Code zu beheben – jede andere
   Darstellung wäre eine Behauptung.
2. **Social-Icon-Links im Footer** (Pinterest, Mastodon): extern, ohne
   Linktext, mit `title` – vom Crawler nicht als interner Befund geführt und
   für Screenreader benannt. Bewusst nicht angefasst; wenn sie je in die
   Sitemap-Nachbarschaft rücken, greift `link-no-anchor` nur bei internen
   Zielen und würde sie weiterhin nicht melden.
3. **Der Crawl selbst** umfasste eine URL. Die nächste Messung sollte die
   Sitemap (99 indexierbare Seiten) als Startpunkt nehmen – erst dann ist der
   Bericht ein Site-Bericht. Unsere Gegenseite (`seo_cockpit`) tut das schon.

---

## 8 · Geänderte Dateien

**Neu:** `scripts/serp_limits.py` · `scripts/tests/test_serp_limits.py` ·
dieser Bericht.

**Wachen:** `scripts/seo_cockpit.py` (Parser: Ankertexte + Rangfolge; vier
neue Regeln; `--fail-on`) · `scripts/metadaten_wache.py` (M2 155, M7 Breite,
2 Proben) · `scripts/blog_header_gate.py` (S1/S2, 4 Proben) ·
`tools/seo-cockpit/app.js` (Labels, Pixelanzeige).

**Templates:** `layouts/_default/list.html` · `layouts/_partials/footer.html`.

**Inhalt:** 22 Descriptions (18 Seiten + 4 Entwürfe), 2 `lastmod`,
1 Kurzantwort, 6 Überschriftsebenen in 4 Artikeln, ein zerbrochener
Listenpunkt (`4 im Modellfall.` → `4.`) in `2026-10-24-bankgebuehren-…`.

**Auslieferung:** `static/_headers` (acht Sicherheits-Kopfzeilen, kein
widersprüchliches `Cache-Control`).

**Verdrahtung/Doku:** `.github/workflows/e2e.yml` · `package.json`
(`serp:check`, `test:serp`, `seo:check` mit `--fail-on`) · `CLAUDE.md` (zwei
DAUERVORGABE-Abschnitte) · `cloudflare/edge-schutz.md` ·
`docs/SICHERHEIT-BETRIEB-RUNBOOK.md` (A1).
