# 🧮 PREMIUM-AUDIT 2026-09-11 – geschlossene Lücken + dauerhafte Wachen

**Datum:** 11.09.2026 · **Umfang:** technisches Fundament von Build, Schema-Markup,
Social-/Pin-Signalen, Indexierungs-Hygiene und CI-Gates · **Auftrag:** „wichtige und
dringende Lücken finden und dauerhaft auf Premium-Level schließen"

---

## 1. Gesamturteil vorher / nachher

Das redaktionelle System dieser Site ist außergewöhnlich gut gebaut (172 Skripte,
13+ Workflows, signierter Kern). Die kritischen Fehler lagen **nicht** im Content,
sondern in einer einzigen, sehr teuren Ecke: **dem Maschinellen, das Google,
Pinterest und KI-Antwortmaschinen über die Seite denken.** Genau diese Ecke war von
keiner Wache abgedeckt — der Build blieb grün, während das Schema seit dem
Theme-Override kaputt war.

| Bereich | Vorher | Nachher |
|---|---|---|
| Article-/FAQ-Schema (31 Live-Artikel + 6 Ratgeber) | unbrauchbar (doppelt gescapete Werte) | valid, inkl. Bildmaßen, wordCount, sameAs |
| CollectionPage/ItemList der Ratgeber-Übersicht | derselbe Defekt | valid |
| Frische-Signale (sitemap `lastmod`, `dateModified`) | Deploy-Zeitstempel bei 6 Artikeln | rotes Redaktionsdatum, erzwungen durch Wache |
| Indexierungs-Hygiene | 116 Tag-Duplikate + Pager-Kopien in der Sitemap | 42 Money-URLs, Archive `noindex, follow` |
| Pinterest auf `/pillar/*` | kein Cover, kein Pin-It-Button | 6 Covers (2:3, 14 Varianten), Pin-It im Footer |
| og:image-Maße | geraten/fehlend | real gemessen aus der Datei (Breite/Höhe/Typ) |
| LCP-Preload | Loader lud Cover, die nie gerendert wurden | exakt 1 Preload pro Seiten-Typ, 0 ungenutzte |
| KI-Antwortmaschinen | keine Politik | 7 Answer-Engines explizit erlaubt, Training weiter nein |
| PWA | Service Worker ohne Manifest | Manifest + 3 Icons, aus hugo.toml erzeugt |
| Gate-Landschaft | Schema/Social/Index = unbewacht | 2 neue Wachen + 19 Regressionstests + Issue-Melder |

---

## 2. Die Lücken im Einzelnen (Befund → Fix → dauerhafte Sicherung)

### 2.1 Doppelt escaptes JSON-LD (kritisch, seit Theme-Override aktiv)
`layouts/_partials/schema_article.html` baute das Article-Objekt per Hand und rief
`{{ .Permalink | jsonify }}` **innerhalb** eines `<script>`-Blocks auf. Hugos
kontextsensitiver Escaper behandelt die Ausgabe an dieser Stelle als JavaScript und
setzt das bereits geparste JSON noch einmal in Anführungszeichen:

```
"@id": "\"https://franksfinanzcheck.de/posts/…/\""     ← so sah es aus
"dateModified": "\"2026-09-11T00:00:00Z\""
```

Google liest damit `@id`, `url`, `mainEntityOfPage`, `image.url` und beide Daten als
buchstabierte Strings mit Quotes → **keine Rich Results, kein Reliable-Authority-Signal
auf der Seite, und Pinterest verliert die Article-Identität.** Alle 31 Live-Artikel
und 6 Ratgeber waren betroffen; die Ratgeber-Übersicht (`layouts/pillar/list.html`)
hatte denselben Baustil in ihrem CollectionPage-Block.

**Fix:** beide Blöcke auf `dict | jsonify | safeJS` umgestellt — exakt ein Escaping,
dasselbe Muster, das `extend_head.html` schon immer richtig machte. Zusätzlich
nachgezogen, was im Altbau fehlte: echte Bildmaße über `imageConfig`, `wordCount`,
`isAccessibleForFree`, `articleSection`, `inLanguage`, `sameAs` aus
`site.Params.socialIcons`, sowie `@id`-Verweise (`#article`, `#website`,
`#organization`, `#frank-hartung`), damit die Objekte im Graphen verschmelzen.

**Sicherung:** `scripts/schema_seo_gate.py` (S1–S4) plus
`scripts/tests/test_schema_seo_gate.py` — die Wache hat einen Sabotage-Fall genau für
diese Klasse (`Fall 2`), und die Quelltext-Invariante verbietet nacktes
`| jsonify` in Schema-Templates (Zitate in den Kommentarblöcken sind ausgenommen,
damit die Invariante nicht auf zitiertem Code anschlägt).

### 2.2 Erfundene Frische (zwei Effekte, ein Fehlerbild)
Sechs Live-Artikel tragen kein `lastmod` im Frontmatter. Hugo fällt dann auf
`.Lastmod` = Datei-Mtime zurück — im CI der Checkout-Zeitstempel. Ergebnis: **jeder
Deploy** (mehrmals täglich) meldete Google „heute aktualisiert" für Seiten ohne
Änderung, und `Article:dateModified` zeigte dasselbe erfundene Datum. Frische-Signale
werden dadurch wertlos, im Zweifel schädlich.

**Fix:** neues Partial `layouts/_partials/sitemap_lastmod.html` (Frontmatter-`lastmod`
→ sonst `.Date`, niemals `.Lastmod`, niemals Zukunft, auf Tag gekürzt) und
dieselbe Logik im Schema-Block. **Kein einziger Artikel hat für diesen Fix ein
datiertes Frontmatter bekommen** — erfundene Redaktionsdaten wären der schlimmere
Fehler gewesen. `scripts/set_lastmod.py --all` wurde bewusst **nicht** ausgeführt.

**Sicherung:** S7 (Sitemap) und eine neue Regel in `_check_article` (S3): weicht
`dateModified` vom Redaktionsdatum ab → harter Fund. Die Wache meldet damit auch den
Fallback-Fall „Template wieder auf `.Lastmod` gestellt".

### 2.3 Indexierungs-Hygiene: Duplikate raus, Kopien still
Die Standard-Sitemap listete 161 URLs, davon 116 Tag-Archive (je ein Artikel =
Duplikat) und die Paginierungs-Kopien — 72 % Crawlbudget für Thin-Duplikate, dazu
Keyword-Kannibalisierung zwischen Tag und Artikel.

**Fix:** eigenes `layouts/sitemap.xml` nach Money-Pages-Prinzip (42 URLs: Home,
Artikel, 6 Ratgeber, Ratgeber-Übersicht, Rechtliches/Über; Dedupe über eine
`$seen`-Liste, weil `hasKey` in Hugo 0.164 für diese Struktur nicht verfügbar ist),
`[outputs] taxonomy=["HTML"] term=["HTML"]` in `hugo.toml` (beseitigt 115 per-Tag-Feeds),
und in `layouts/_partials/head.html`: `noindex, follow` für Taxonomie-/Term-Seiten und
Paginierungs-Kopien, `noindex, nofollow` für `/404*`.

**Sicherung:** S6 (Archiv-/Pager-URL in der Sitemap oder indexable Live-Seite fehlt)
und S10 (genau ein canonical, Ziel muss im Build existieren).

### 2.4 Ratgeber-Seiten ohne Bild, ohne Pin, mit totem Preload
Die 6 `content/pillar/*/index.md` trugen kein `cover:` → keine og:image (die
wichtigsten Landingpages der Site teilten als grauer Kasten), kein Pin-It-Button in
`layouts/pillar/single.html` → auf Pinterest die schlechteste aller Loop-Formen, und
`layouts/_partials/head.html` lud über den Deterministik-Fallback ein Cover-Bild vor,
das das Pillar-Template gar nicht rendert.

**Fix:** `scripts/generate_covers.py` kann jetzt Ratgeber-Covers (eigener Pfad-Zweig
`pillar_paths()`, `ensure_pillar_covers()`, Flag `--pillars`, Gegenstück
`--posts-only`): 6 Covers im 2:3-Format, gleiche Marke, 14 Varianten
(360/480/620/720 + WebP/AVIF), `cover:`-Frontmatter inkl. `preload: false` —
selbstheilend eingesetzt **nach** einem vorhandenen `cover:`-Block, wenn dort
`preload:` fehlt. Pin-It-Schwimmer + Footer-Partials in `layouts/pillar/single.html`
(gleiche Guard-Bedingung wie im Artikel-Template). Damit ist auch der Pin-Loop der
Ratgeber geschlossen: Pin → Ratgeber → Artikel → Vergleichslink.

**Sicherung:** `check_covers.py` (prüft die Pillar-Frontmatter mit – 54 Covers · 0 Probleme), S9 (Preload muss im gerenderten Bild vorkommen — der Fund, der den toten
Preload auf Pager-Seiten sichtbar machte), `generate_covers.py --pillars` läuft
nächtlich in `blog-health-daily.yml` vor `blog_health_gate.py`.

### 2.5 Preload auf Pager-Seiten (von der eigenen Wache gefunden)
Der LCP-Fallback schlüsselte das Manifest an `.RelPermalink` — die ist auf
`/posts/page/2/` identisch mit `/posts/`. Folge: Auf allen 9 Pager-Seiten wurde das
Cover des neuesten Artikels vorgeladen, das dort nicht vorkommt (un-genutzter
Preload = Bytes + Lighthouse-Abzug).

**Fix:** `head.html` bekommt eine Preload-Bremse über `.Paginator.PageNumber > 1`
plus `term`/`taxonomy` komplett ausgenommen. Bewusst **nicht** `.Truncated` — das Flag
steht auf jedem Artikel mit >70 Wörtern (Summary-Schnitt) und hätte den legitimen
Cover-Preload aller 31 Artikel abgeschaltet; `.OutputPath`/`.PagingMetadata` existieren
in Hugo 0.164 nicht auf der Seite (verifiziert, zwei Fehlversuche).

**Sicherung:** S9 + Invariante `test_head_hat_preload_bremse_fuer_pager_und_archive`.

### 2.6 Antwortmaschinen-Politik in robots.txt
Die Site will in Antworten von ChatGPT/Perplexity/Claude/DuckDuckGo stehen (Traffic
ohne Ranking-Abhängigkeit), Training aber ablehnen. Bisher gab es keine Zeile dafür.

**Fix:** `layouts/robots.txt` dokumentiert sieben Retrieval-/Answer-Bots
(OAI-SearchBot, ChatGPT-User, PerplexityBot, Perplexity-User, DuckAssistBot,
Claude-User, meta-externalfetcher) mit `Allow: /` + `Disallow: /go/` (der Affiliate-Klickpfad gehört nicht in Antworten). Bewusst **kein** zweites `User-agent: *`-Content-Signal
daneben gestellt: die bestehende Zeile sagt bereits `search=yes, ai-train=no,
use=reference`, und mehrere `*`-Gruppen heben sich nach RFC-Logik teilweise auf.
Die Content-Signal-Zeile ist eine Absichtserklärung ohne Rechtswirkung — Cloudflare
und Google schreiben sie unabhängig vom Repo.

**Sicherung:** S8 prüft die Politik im Build (Pinterest-Gruppe vorhanden, kein
`Disallow: /` für Pin-/Answer-Bots, Content-Signal nicht auf `search=no` verbogen).

### 2.7 PWA: Service Worker ohne Manifest
`layouts/index.sw.js` registriert einen Worker inkl. Offline-Fallback — ohne Manifest
zeigt aber kein Browser je „Zum Startbildschirm hinzufügen", und iOS startet nicht
im Vollbild. Für eine Site, deren Publikum von Pinterest und Suche kommt
(Einmal-Klick-Publikum), ist der Home-Screen-Shortcut der billigste Rückholkanal.

**Fix:** `scripts/generate_pwa_icons.py` (deterministisch, offline, mit `--check` und
`--selftest`) erzeugt `static/manifest.json` aus `hugo.toml` (Name, Beschreibung,
Theme-Farbe, Shortcuts auf die vier wichtigsten Ratgeber) + `icon-192/512/maskable-512`
aus dem bestehenden Markenbildzeichen; `layouts/_partials/extend_head.html` verlinkt
es (`rel=manifest`, `application-name`, Apple-Metas). `manifest.json` statt
`.webmanifest`, weil GitHub Pages das MIME für letztere nicht setzt. Bewusst **kein**
zweites `theme-color` gesetzt — PaperMod liefert es bereits (sonst doppeltes Meta-Tag,
was die neue Wache jetzt ohnehin meldet).

**Sicherung:** S11 (Manifest vorhanden, Felder vollständig, Icons im Build ≥144 px,
Link im Kopf, keine Duplikate) + `test_pwa_artefakte_sind_im_repository` +
`generate_pwa_icons.py --selftest` als Guard.

### 2.8 Phantom-Links in zwei Wachen
`layout_audit.py` und `scripts/check_internal_links.sh` meldeten seit längerem
drei „kaputte interne Links" (`pinterest-oauth.html → im | innerhalb | wf;`). Die
Links waren perfekt; die **Parser** waren zu gierig: das quote-tolerante Muster
(sinnvoll, weil `hugo --minify` Anführungszeichen tilgt) sah auch `link.href = wf;`
in Skripten und `href=` in HTML-Kommentaren. Eine Wache, die Phantome meldet, wird
abgeschaltet — und damit ist der Schutz weg, den sie darstellen sollte.

**Fix:** beide Prüfer entfernen `<script>`, `<style>` und Kommentare vor dem Scannen
(`layout_audit.py`: `NOISE_RE`; `check_internal_links.sh`: `perl -0777`, mit Fallback
auf rohen Scan, wenn `perl` fehlt). Ergebnis: 1811 bzw. 2649 Links geprüft, 0 Defekte.

### 2.9 Zwei Content-Metadaten-Lücken (klein, aber sichtbar)
* `2026-09-09-notgroschen…` hatte kein `pinwand` → das Board-Routing
  (`scripts/pinterest_engine.py: board_name_for`) fiel auf das Pillar-Fallback
  zurück. gesetzt: `Geld sparen im Alltag | Frugalismus-Tipps` (exakt der
  Board-Name aus `data/pinterest_boards.yaml` für `pillar: frugalismus`).
* `2026-09-11-wlan-probleme…` hatte keine `kurzantwort` → die Antwort-Box zeigte nur
  die Meta-Description (Template-Fallback). Jetzt eine echte Antwort, **ausschließlich
  mit Zahlen, die im Artikel selbst stehen** (80 €, 250 €, Half-Duplex, Seamless
  Roaming) — keine erfundenen Werte.

### 2.10 og:image-Maße und -Typ
`og:image:width/-height` fehlten ganz, `og:image:type` ebenfalls. Pinterest und
Google werten fehlende Maße als Signal minderer Qualität; für das
Fallback-Site-Bild (Startseite/Rechtsseiten, neu: `params.images` →
`images/covers/brand-franksfinanzcheck.jpg`, 1000×1500, im Covers-Look der Site,
Badge „FRUGALISMUS · TARIFE · VERSICHERUNGEN") werden sie jetzt wie bei allen
Artikeln aus der Datei gemessen.

---

## 3. Was neu dauerhaft wacht

| Baustein | Zweck |
|---|---|
| `scripts/schema_seo_gate.py` | 11 Regelgruppen (S1–S11) über den gebauten `public/`: JSON-LD-Validität, Doppel-Escape-Detektor, Article-Werte/-Typen/-Daten/-URLs/-Bildexistenz, FAQ-Antwortlänge, OG+Twitter-Abdeckung inkl. Maßvergleich mit der Bilddatei, Archiv-/Pager-`noindex`, Sitemap-Vollständigkeit/-Reinheit, `lastmod` ≡ Redaktionsdatum, Robots-Politik (Pinterest + Answer-Bots + „keine Gruppe darf `/` sperren"), Preload↔gerendertes Bild, genau ein canonical mit existierendem Ziel, PWA-Manifest, doppelte Kopf-Metas. Keine `--fix`-Funktion: Diese Wache misst, sie dichtet nicht. 10 Sabotage-Fälle (`--selftest`), schreibt `SCHEMA-SEO-REPORT.md` (vom Repo ausgeschlossen, `/*-REPORT.md`) und `data/schema_seo_history.jsonl`. |
| `scripts/generate_pwa_icons.py` | Manifest + Icons aus `hugo.toml`, `--check` als Drift-Wache. |
| `.github/workflows/link-check.yml` | Neues Gate: **Push, PR und täglich** — Selbsttest-Loop auf alle Wachen umgestellt (Liste als Variable, Anzahl wird gezählt statt im Titel behauptet), `Schema-/SEO-Gate` nach dem Build als Schritt mit `id: schema`, Issue-Melder deckt jetzt beide Prüfer ab (Titel entscheidet), Schließen nur wenn **beide** grün sind, Gate-Status rot bei einem der beiden. |
| `scripts/governance_contract.py` | `GUARDS` um `schema_seo_gate.py` + `generate_pwa_icons.py` erweitert (C6 prüft Präsenz **und** Ausführung ihrer Selbsttests); Kommentar hält fest, warum die beiden drin sein müssen. |
| `.github/workflows/blog-health-daily.yml` | Heilkette ergänzt: `generate_covers.py --pillars`, `generate_pwa_icons.py --selftest` + der Erzeugungslauf vor `blog_health_gate.py` → nächtliche Selbstheilung statt manueller Nacharbeit. |
| `scripts/tests/test_schema_seo_gate.py` | 19 Tests, ohne Build und ohne Netz: Verhalten der Wache an einer Mini-Site (grüne Anlage bleibt grün; Originalbug, kaputtes JSON, erfundene Frische, falsche Bildmaße, toter Preload, doppeltes canonical, Archiv ohne `noindex`, Sitemap-Fehler, Robots-Sperre, fehlendes Manifest) + Quelltext-Invarianten der Templates. |

Lokaler Verifikationslauf (11.09.2026, Hugo 0.164.0 extended, `--minify -e production`):

```
Build                      312 Seiten, 0 Warnungen
schema_seo_gate.py         330 Seiten · 37 Money-Pages · 0 harte Funde · 0 Hinweise
schema_seo_gate --selftest 10 Fälle grün
layout_audit.py            51 Seiten · Kritisch 0 · Warnungen 0
check_internal_links.sh    2649 Links · 0 defekt
check_covers.py            54 Covers · Probleme 0 · Stale 0 · Brand 0 · Text 0
blog_health_gate.py        grün (inkl. heading_guard, description-abdeckung)
seo_audit.py               0 Probleme in 31 Artikeln
publication_check.py       ok=true (3/3 für 2026-09-11)
governance_contract.py     erfüllt — alle dreizehn Regeln
integrity_guard.py         signiert (42 Dateien), Check: 🎉 Kern identisch
unittest discover          Ran 91 tests · OK
```

---

## 4. Bewusst nicht geändert (und warum)

* **Kein Text-Rewriting** in `content/{ueber,impressum,datenschutz}` und kein
  Umformulieren der 3 kritischen 7-Wort-Überlappungen, die `check_uniqueness.py`
  meldet (vor diesem Lauf vorhanden, identisch vorher/nachher). Das ist
  redaktioneller Besitz, keine technische Lücke.
* **Keine erfundenen `lastmod`-Daten** für die 6 Artikel ohne `lastmod`
  (`set_lastmod.py --all` blieb unbenutzt). Stattdessen deterministischer Fallback
  auf `.Date` im Template — ehrlich, und die Wache erzwingt das jetzt.
* **`data/.indexnow_submitted.json` und `data/.affiliate_integrity_state.json`
  bleiben versioniert**: sie sind gewollter Zustand über Läufe hinweg (Dedupe-
  Historie), keine versehentlichen Artefakte.
* **Keine Massen-Entfernung der ~64 generierten `*-REPORT.md` im Root** und kein
  Löschen der versionierten 2,6 MB `strom-sparen-pinterest.mp4` /
  `static/audio/*.mp3`: das sind Besitzstände, die Frank betreffen — Empfehlung
  statt Eingriff (siehe § 5).
* **`layouts/pillar/single.html` zeigt weiterhin kein großes Cover-Bild**: die
  Spartabelle gehört auf Ratgeber-Seiten über die Falz, nicht ein Poster. Das Cover
  arbeitet dort als `og:image`, Pin-Medium und Preload-Ausnahme — bewusst ohne
  sichtbares `<figure>`-Element.

---

## 5. Empfehlungen an Frank (alle acht umgesetzt, siehe 5.1)

| # | Befund | Nutzen | Aufwand |
|---|---|---|---|
| 1 | `params.newsletterFormUrl` ist leer → `extend_footer.html:31` rendert seit Monaten **kein** Newsletter-Feld. Die gesamte Pinterest-/Such-Reichweite läuft über eine Audience, die man nicht besitzt. | höchster strategischer Hebel des ganzen Audits | 1 Nachmittag (Provider + Formular-URL eintragen) |
| 2 | `static/go/<slug>/index.html`: canonical zeigt auf die **Awin-Klick-URL** (sollte leer/`noindex` sein), und die Klammerzeile enthält den Tippfehler „für dich kostenlos" als `fuer`. | Sauberkeit + Vertrauen | 15 Min, Skript-Fall |
| 3 | `check_uniqueness.py`: 3 Paarüberlappungen mit je 5–6 identischen Sieben-Wort-Phrasen zwischen Live-Artikeln. | Differenzierung, Duplicate-Risiko | je 10 Min pro Artikel |
| 4 | Studio-Audio existiert für **1 von 31** Artikeln, obwohl Voice-Toolbar + `static/audio/*.mp3` gebaut sind. | Barrierefreiheit + Verweildauer | Batch-Lauf des TTS-Skripts |
| 5 | ~64 generierte `*-REPORT.md` im Root sind versioniert (Churn in jedem CI-Lauf, History-Verschleiß). | aufgeräumteres Repo | 1 Commit nach `.gitignore`-Pflege |
| 6 | 17 Drafts liegen seit Wochen im Baum (`content/posts/*/draft: true`) — Kadenz-Gate zählt sie mit. | Planbarkeit | Sichten: publizieren oder verwerfen |
| 7 | Issue #246: Pinterest-Re-Auth und die manuelle Entsperrung des Link-Domain-Spam-Blocks (seit 27.08.2026) sind offen. | Pins laufen sonst weiter ins Leere | 30 Min, Doku im Ticket |
| 8 | Cloudflare Managed Rules schreiben `robots.txt` live um — Repo und Live können abweichen, obwohl beide korrekt aussehen. | Vermeidung von Scheingrün | wöchentlicher Blick in die Search Console |

### 5.1 Umsetzung am 12.09.2026 (Auftrag: «Bitte sofort umsetzen»)

Alle acht Punkte sind abgearbeitet; wo ein externales Konto nötig bleibt, ist die
Repo-Seite fertig und der Handgriff dokumentiert. Status je Nummer der Tabelle oben.

| # | Status | Was im Repo landete | Was bei Frank bleibt |
|---|---|---|---|
| 1 | **umgesetzt, Aktivierung offen** | `content/newsletter/index.md` (Landingpage, NoIndex, nicht in Sitemap, nicht in der Home-Liste), `layouts/shortcodes/newsletter_form.html` (Provider-neutral: Inline-POST `newsletterFormAction` oder Button `newsletterFormUrl`), drei neue `params` in `hugo.toml`, `scripts/newsletter_digest.py` (Capture-Wache + Digest-Bau + Brevo-Versand mit dreifacher Verriegelung + Duplikatsschutz über `data/newsletter_state.json`), Workflow `newsletter-daily.yml` (Mo–Fr 05:05 UTC, ohne Secrets bewusst inert), `docs/NEWSLETTER-RECHTSTEXT-VORLAGE.md` | Brevo-Konto, Liste + Formular anlegen, `BREVO_API_KEY`/`BREVO_LIST_ID` als Secret, Formular-URL in `hugo.toml`, Datenschutz-Abschnitt ersetzen (Schritte: `docs/ANLEITUNG-NEWSLETTER.md`) |
| 2 | **Repo-Seite fertig** | OAuth-Empfänger-Wache in `secrets_age_guard.py`: prüft `static/pinterest-oauth.html` (Code lesen, Kopierweg, NoIndex) und den Zwilling `/pinterest-oauth/` — die Handlungsanweisung aus #246 kann nicht mehr ins Leere führen | Einmalig neu autorisieren (Issue #246, 5 Min): `pinterest-token.yml` → `show_auth_url` → Erlauben → Code in `auth_code`; danach schließt das Issue sich selbst. Zusätzlich in der Pinterest-App: Domain-Sperr-Freigabe prüfen |
| 3 | **erledigt** | Überlappungen in 3 Artikeln paraphrasiert (5 Ersetzungen, NBSP-sicher); `check_uniqueness.py` meldet wieder 0 kritische Funde und druckt jetzt die gemeinsamen Grams + Slugs im Report | nichts |
| 4 | **Befund korrigiert + Wache** | Gezählt wurde im Quell-Repo (`static/audio/` = 1 handgemachtes Paar). Die Tonspuren liegen auf `gh-pages/audio/articles/`: **18 von 31 Live-Artikeln haben eine Studio-Tonspur**, 13 nutzen die Gerätestimme. Neu: `scripts/audio_coverage_check.py` (Build-/Ref-modus, „unbekannt" ≠ „0 %"), Tagesschritt in `lesehilfen-gate.yml`, Selbsttest + `governance_contract.GUARDS` | Bei Bedarf einmalig Deploy mit `audio_backfill=true` auslösen (Input existiert in `deploy.yml`, 25 Artikel je Lauf, Budget 90 Min) |
| 5 | **Korrigiert + dauerhaft sauber** | Nach Einordnung sind **64 von 70** Root-Reports echte CI-Dashboards (von einem Workflow per Name gestaged) oder dokumentierte Referenzen — pauschales Ent-versionieren hätte Leseproben der Wachen zerstört. `scripts/report_hygiene.py` klassifiziert jetzt in vier Eimer (ci-dashboard / doku / maschinen-muell / verwaist) mit Selbsttest; 20 generierte, von niemandem gelesene Reports aus dem Index genommen, `BESTAND-GATE-PREMIUM-FIX-REPORT.md` nach `docs/` verschoben; `.gitattributes` markiert Root-Reports als `linguist-generated` (keine Diff-Sperre mehr in PRs); Heilung läuft täglich in `blog-health-daily.yml`, Wochencheck in `premium-governance.yml` | nichts |
| 6 | **umgesetzt (Triage statt Bulk-Entscheidung)** | `scripts/draft_triage.py`: jeder der 17 Entwürfe bekommt einen begründeten Zustand (REIF 6 · BLOCKIERT 11 · WARTET 0 · VERWAIST 0) samt Hindernis in der Sprache der Produktions-Gates; Stufen-Einbau in `content-reserve.yml` (Tabelle in die Lauf-Zusammenfassung, `--check-decisions` meldet reifen Verfall). **Nebenbefund mit echtem Schaden:** 8 Artikel (2 Drafts, 6 live) hatten die Frontmatter-Grenze an den ersten Absatz geklebt (`---Text`) → Hugo baute sie korrekt, die Regex-Wachen des Repos übersahen die Artikel vollständig (u. a. `check_uniqueness`, `length_guard`, `link_density_guard`). Alle Grenzen normalisiert, Regel `fm-grenze` ist jetzt Blocker in der Triage | 6 reife Entwürfe: publizieren oder begründet halten (Liste im Workflow-Log) |
| 7 | **erledigt** | `/go/`-Gateway: canonical aus dem Klammer-Template geworfen, Viewport ergänzt, `fuer`-Tippfehler in „für dich kostenlos" bereinigt, Preishinweis neutral formuliert; 19 Seiten neu erzeugt, `affiliate_link_check.py` + `affiliate_integrity_gate.py` grün. Deep-Link-Erwartung der Wache an die Produktfamilie des Pillars angepasst (Heizung/Gas im Strom-Pillar war ein Mapping-Fehler der Wache, nicht des Artikels) → Report wieder leer | nichts |
| 8 | **umgesetzt (wöchentlicher Blick, gemessen)** | `scripts/live_policy_guard.py` vergleicht live mit dem Build: `robots.txt` (jede User-agent-Gruppe, `Disallow: /` je Bot, Content-Signal), Sitemap (Money-URLs, keine `/tags/`- oder `/page/`-Duplikate), canonical/og:image/JSON-LD einer Stichprobe (erkannt wird auch doppelt escaptes JSON-LD **im CDN-Cache**), HTTP-Umleitung + Manifest-MIME. Ohne Netz: Hinweis; im CI mit `--require-live`: rot. Schritt in `premium-governance.yml`, Ledger-Code `live-policy`, Report ist Lauf-Artefakt (Root bleibt sauber), Nachweis im `governance_history.jsonl`-Event | Cloudflare-Dashboard: Managed-Rules-Set prüfen, wenn die Wache Drift meldet (Repo-Seite kann Rewrite nicht verhindern, nur anzeigen) |

**Neue Wachen in dieser Runde** (alle mit `--selftest`, alle in `governance_contract.GUARDS`
und im WACHEN-Loop von `link-check.yml`, alle per unittest regressionsgesichert):
`report_hygiene.py`, `draft_triage.py`, `live_policy_guard.py`, `audio_coverage_check.py`,
`newsletter_digest.py` — 42 neue Regressionstests, Suite jetzt 133 Tests.

**Klarstellung zu „1 von 31 Audio"** und zu den Root-Reports: beide Befunde
stammten aus Quell-Repo-Zählungen, die den Auslieferungszustand bzw. die
Verbraucher der Dateien nicht kannten. Die Korrekturen stehen hier, damit das
nächste Audit nicht dieselbe Reparatur vorschlägt, die es gerade gibt.

---

## 6. Wiederholen / erweitern

```bash
# Gate lokal (braucht einen Build im public/)
hugo --minify -e production
python3 scripts/schema_seo_gate.py            # Exit 1 = harte Funde
python3 scripts/schema_seo_gate.py --selftest # Sabotage-Schutz der Wache
python3 -m unittest discover -s scripts/tests

# Assets heilen
python3 scripts/generate_covers.py --pillars
python3 scripts/generate_pwa_icons.py
```

Neue Regel in `schema_seo_gate.py`? Regelgruppe `Sx` ergänzen, **einen
Sabotage-Fall in `_selftest()` dazu** (C6 läuft den Selbsttest bei jedem Push), und
den Fundsatz so formulieren, dass der nächste Schritt daraus schon folgt — die
Meldung „manifest.json fehlt im Build" nennt das Erzeugungskommando direkt mit.
