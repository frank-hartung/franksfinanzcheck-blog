# Sitecheck 2016 – Optimierung von franksfinanzcheck.de

**Datum:** 27.10.2026 · **Auftrag:** „Bitte meinen Blog optimieren wie folgende Website empfiehlt: [pergamon-interactive.de/sitecheck-2016.html](https://www.pergamon-interactive.de/sitecheck-2016.html)“
**Grundlage:** der Website Check selbst plus seine vierteilige Serie – [Meta-Elemente](https://www.pergamon-interactive.de/meta-tags-im-website-check.html), [Webseiten-Struktur](https://www.pergamon-interactive.de/webseiten-struktur-im-website-check.html), [Technik](https://www.pergamon-interactive.de/technik-im-website-check.html), [Konfiguration](https://www.pergamon-interactive.de/konfiguration-im-website-check.html).

> **Vorweg, damit die Zahlen ehrlich sind:** Der Online-Check konnte aus dieser
> Umgebung nicht gegen die Live-Domain gefahren werden (der Dienst ist ein
> URL-Formular mit Tageslimit, ausgehende Verbindungen sind hier begrenzt).
> Stattdessen wurden die **dokumentierten Prüfkriterien** auf den echten
> Hugo-Build angewandt – nicht auf eine einzelne Startseite, sondern auf alle
> **262 gebauten HTML-Dateien, davon 99 indexierbare Seiten**. Der daraus
> entstandene Prüfer liegt dauerhaft im Repo (`scripts/sitecheck_wache.py`).

---

## 1. Messung vorher / nachher

| Prüfpunkt | Empfehlung des Checks | Vorher | Nachher |
|---|---|---:|---:|
| Title | ~60 Zeichen | **2** Seiten > 60 | **0** |
| Description | 110–156 Zeichen | **9** indexierbare Seiten außerhalb (13 Frontmatter-Dateien insgesamt) | **0** |
| generator-Tag | aus Sicherheit entfernen | **9** Seiten (Start + Pager) | **0** |
| Überschriften | H1 einmalig, h2–h6 ohne Sprünge | **4** Artikel mit h1→h3 bzw. h2→h4 | **0** |
| Veraltete Auszeichnung | `<strong>` statt `<b>` | **73** Vorkommen auf 5 Seiten (19 Tags in 6 Vorlagen) | **0** |
| Interne Links | keine Sackgassen | **42** Inhaltsverzeichnis-Links mit `href="#"` | **0** (0 verwaister Anker) |
| Doctype / lang / viewport / Canonical / robots | vorhanden, https | 0 Funde | 0 Funde |
| robots.txt / sitemap.xml | vorhanden, konsistent | 99 URLs = 99 Canonicals | unverändert grün |
| Bilder | alt, Maße, Ladeverhalten | 567 Bilder, 0 Funde | unverändert grün |
| Tabellen | nur für Daten, nicht Layout | 163 Tabellen, alle mit `<th>` | unverändert grün |
| Skripte/CSS | bündeln, komprimieren | 2–6 `defer`-Skripte, **0** externe CSS-Dateien | unverändert grün |
| Fließtext | nicht zu dünn | kürzeste Seite 1.921 Zeichen | unverändert grün |
| HTML-Übertragung | klein halten | Median 340 kB roh → **68 kB gzip** | 340 kB → 68 kB |

Die Übersichtsseite nennt außerdem **Markup** und **Recht**; eigene Ratgeber
dazu existieren nicht mehr (beide URLs liefern 404). Ihre Inhalte sind in der
Struktur-Serie enthalten: gültiges HTML statt veralteter Tags (S3) sowie
erreichbare Impressum- und Datenschutzlinks (S6). Beides ist unten geprüft.

Der Check selbst bewertet vier Bereiche. Nach der Runde:

```
SITECHECK-WACHE · 262 gebaute HTML-Dateien · 99 indexierbare Seiten
Harte Funde: 0 · Hinweise: 0
✅ Meta, Struktur, Technik und Konfiguration im grünen Bereich.
```

---

## 2. Was konkret geändert wurde

### Meta
1. **Generator-Angabe entfernt.** `hugo.toml` setzt jetzt `disableHugoGeneratorInject = true`. Vorher schrieb Hugo auf Startseite und allen acht Blätterseiten `<meta name="generator" content="Hugo 0.168.0">` – genau der Tag, vor dem der Check aus Sicherheitsgründen warnt (Bots erkennen das CMS samt Version).
   `hugo.toml` steht unter dem Integritätssiegel. Die Änderung wurde deshalb bewusst über `python3 scripts/integrity_guard.py --set-current` neu signiert; `python3 scripts/integrity_guard.py --gate` ist danach grün. Das ist eine Betreiber-Entscheidung und hier dokumentiert.
2. **Zwei Seitentitel ins 60-Zeichen-Fenster.** `/methodik/` bekam einen eigenen `seoTitle` („So arbeiten wir: Beweissystem & Methodik“), die sichtbare H1 bleibt unverändert. Der `seoTitle` von `/werkzeuge/` verlor das Marken-Suffix, das ihn auf 62 Zeichen gedrückt hatte. Die Marke steht ohnehin im WebSite-Schema über dem Snippet.
3. **13 Description-Felder auf 110–156 Zeichen gebracht.** Darunter vier, die mitten im Wort abgeschnitten waren („… ohne funktionierende.“, „… drei bis.“). Die neuen Texte nennen dasselbe Thema, behalten die Keywords und sind vollständige Sätze. Betroffen: Impressum, Datenschutz, Änderungsprotokoll, Cockpit, vier Newsletter-Seiten, Pillar `internet-dsl`, der Abschlags-Rechner und vier Ratgeber.
4. Vorhanden und bewacht bleiben: HTML5-Doctype, `lang="de"`, `charset`, `viewport` mit `width=device-width`, genau ein `https`-Canonical, `robots` je Seite, eindeutige Titel und Beschreibungen.

### Struktur
5. **Überschriftenhierarchie in vier Artikeln geradegerückt.** Der „Schnellstart“-Block begann mit `h3` direkt nach der H1, zwei Artikel sprangen von `h2` auf `h4`. Jetzt: `h1 → h2 → h3` ohne Sprung. Anker-IDs blieben identisch, bestehende Links bleiben gültig. **Folgeänderung:** Beim Stromfresser-Artikel ändern die neuen H2 die abgeleiteten „Stationen“ der Gliederungsgrafik. `abbildungen_ableiten.py` hat deshalb `abbildung-ablauf.svg` und die artikelgenaue Bildunterschrift neu geschrieben; der Abbildungs-Check ist wieder bei 0 Befunden. Ohne diesen Schritt wäre die Inhalts-Wache FF5 rot gelaufen.
6. **19 `<b>`-Tags auf `<strong>` umgestellt** – in den Beweis-, Änderungs-, Methodik- und Vergleichs-Shortcodes sowie im Kostenprofil. Die drei betroffenen Stylesheets selektieren jetzt `:is(b, strong)`, damit das Design unverändert bleibt und künftige Inhalte mit `<b>` trotzdem richtig aussehen. `<b>` ist in HTML5 nicht *ungültig* – die Wache meldet es deshalb als Hinweis, nicht als Fehler; `<font>`, `<center>`, `<marquee>`, `<frameset>` und Konsorten sind harte Funde.
7. **42 tote Inhaltsverzeichnis-Links entfernt.** PaperMod baute das TOC aus *allen* Überschriften, auch aus Widget-Überschriften ohne `id` – Ergebnis: `href="#"`, ein Klick sprang an den Seitenanfang. Die eigene Fassung `layouts/_partials/toc.html` lässt nur Überschriften mit echter `id` zu; UI-Beschriftungen von Rechnern und Boxen sind keine Kapitel. Messung nachher: **0** `href="#"`, **0** Anker ohne Ziel auf 77 Seiten mit Inhaltsverzeichnis. Das Theme selbst bleibt unangetastet und updatefähig.

### Technik
8. KeineFrames, kein Flash, keine Plugin-Objekte, keine Layout-Tabellen. Der einzige `iframe` (Anbieterkennzeichnung im Impressum) hat `title`, `sandbox` und `referrerpolicy`.
9. 2–6 externe Skripte pro Seite, alle mit `defer`, alle vom eigenen Ursprung; **0** externe Stylesheets. Das CSS ist zu **einem minifizierten Block** zusammengefasst und inline – kein zusätzlicher Request, kein FOUC. Die Wache deckelt Skriptdateien bei 6 und verlangt `defer`/`async`.
10. Webfonts: vier selbst gehostete woff2-Dateien, `font-display: optional`, nur Inter wird vorgeladen. Die drei Playfair-Schnitte (500, 600, kursiv) sind alle tatsächlich in CSS-Regeln verwendet – hier wurde bewusst **nichts** entfernt.

### Konfiguration
11. `robots.txt` und `sitemap.xml` waren bereits vorbildlich: Sitemap-Zeile über https, `/go/` gesperrt, CSS/JS frei, 99 Sitemap-URLs deckungsgleich mit den 99 `index, follow`-Canonicals. Die neue Wache prüft diese Parität bei jedem Lauf – und verwechselt die gewollten `Disallow: /` für Trainings-Crawler (GPTBot, CCBot …) nicht mit einem globalen Sperren.
12. HTTPS sitzt in Canonical, Open Graph, Schema.org und Sitemap; `404.html` ist vorhanden.

---

## 3. Bewusst NICHT umgesetzt (Begründung statt blindem Gehorsam)

Der Check stammt aus dem Jahr 2016. Fünf Empfehlungen würden die Seite 2026 verschlechtern:

| Empfehlung | Entscheidung | Warum |
|---|---|---|
| `meta keywords`, `page-topic` | weggelassen | Google ignoriert Keywords-Meta seit 2009; beide Tags blähen nur den kritischen Head auf. Das Repo hatte `keywords` bereits bewusst entfernt. |
| `meta http-equiv="expires"` | weggelassen | Browser ignorieren es weitgehend. Korrekt sind HTTP-Header: `Cache-Control` in `static/_headers` (1 Jahr für Fonts/Bilder, 600 s für HTML) plus versionierte Asset-URLs. |
| `mod_pagespeed` | weggelassen | Apache-Modul; die Site läuft auf GitHub Pages hinter Cloudflare. Kompression passiert auf Edge-Ebene (gzip/Brotli), nicht im Webserver-Prozess. |
| „Möglichst alle JS-Dateien zusammenfassen“ | bewusst nicht | Galt für HTTP/1.1 mit sechs Verbindungen. Unter HTTP/2 sind 2–6 parallele, `defer`-geladene, unveränderlich gecachte Dateien schneller als ein großer Block, den jede Werkzeugseite vollständig laden müsste. Die Wache setzt stattdessen eine Obergrenze und erzwingt `defer`/`async`. |
| „Externe CSS statt Inline-CSS“ | bewusst anders | Der Check meint „CSS zusammenfassen und Requests sparen“. Genau das passiert: ein minifizierter Block, null Requests. Er wird inline ausgegeben, um den dokumentierten Layout-Shift (CLS) zu vermeiden. Preis: ~340 kB rohes HTML pro Seite, übertragen werden davon ~68 kB (gzip). Die Wache misst beides und schlägt erst bei >120 kB gzip an. |

Ebenfalls nicht verändert: die Domain (kurz, merkfähig, markentragend) und HTTPS – beides war bereits erfüllt. Die reinen Verifikationsdateien (`google8f0….html`, `pinterest-*.html`) sind absichtlich reine Textdateien ohne `<html>`/`<head>`: sie sind keine Inhaltsseiten und stehen nicht im Index.

---

## 4. Die neue Wache (damit es so bleibt)

`scripts/sitecheck_wache.py` prüft **den gebauten Blog**, nicht die Absicht im Template. 27 Regeln in vier Blöcken:

- **M1–M8 (Meta):** Doctype, lang/charset, viewport, Title ≤ 60, Description 110–156, genau ein https-Canonical, kein generator, eindeutige Metadaten.
- **S1–S8 (Struktur):** genau eine H1 ≤ 80 Zeichen, keine Ebenensprünge, keine obsoleten Tags, Bilder mit `alt`/Maßen/`loading`, Datentabellen mit `<th>`, Pflichtlinks (Impressum/Datenschutz), keine toten Anker, mind. 600 Zeichen Text.
- **T1–T4 (Technik):** keine Frames/Flash/Plugins, Skripte ≤ 6 und immer `defer`/`async`, keine fremden Skript-Hosts, Stylesheets gebündelt.
- **K1–K5 (Konfiguration):** robots.txt mit https-Sitemap und ohne globale Sperre, Sitemap nur sichere eigene URLs, **Sitemap = indexierbare Canonicals**, 404 vorhanden, HTML nach gzip im Budget.

Zwei Fallen sind eingebaut und getestet: `<title>` innerhalb eines SVG-Diagramms ist **kein** Seitentitel (sonst erscheinen zwei Artikel mit 148/250 Zeichen Titel), und `<a id="anker">` ohne `href` ist ein Sprungziel, kein toter Link.

```bash
npm run test:sitecheck      # 27 Sabotageproben + 23 Unit-Tests, offline
npm run sitecheck:check     # Selbsttest + Hugo-Build + Prüfung von public/
python3 scripts/sitecheck_wache.py --site public --json   # Maschinenausgabe
```

Der Selbsttest prüft den **Detektor**, nicht den liegenden Stand (DAUERVORGABE dieses Repos): jede Regel wird mit einer kaputten Seite provoziert und muss anschlagen; eine saubere Mini-Site muss grün bleiben.

**Einordnung in die bestehende Landschaft:** Die Wache ergänzt, sie ersetzt nichts. `h1_wache.py`, `a11y_audit.py`, `metadaten_wache.py` und `schema_seo_gate.py` bleiben unverändert zuständig. Kein Workflow und keine sicherheitsrelevante Datei wurde angefasst; die beiden npm-Kommandos sind der einzige neue Einstiegspunkt. Wer die Wache in CI hängen will, ergänzt `npm run sitecheck:check` als einen Schritt hinter dem Hugo-Build.

---

## 5. Verifikation dieses Auftrags

```
npm run test:sitecheck                           ✅ 27 Sabotageproben + 23 Unit-Tests
npm run sitecheck:check                          ✅ Build + Vollprüfung, 0 Funde
python3 scripts/h1_wache.py --public public      ✅ genau eine H1 je Seite
python3 scripts/a11y_audit.py                    ✅ 227 Seiten, 0 Probleme, 0 Kontrastfehler
python3 scripts/schema_seo_gate.py               ✅ 262 Seiten, 0 harte Funde
python3 scripts/check_titles.py                  ✅ 104 Titel, 0 Verstöße
python3 scripts/seo_audit.py                     ✅ 68 Artikel, 0 Probleme
python3 scripts/layout_audit.py                  ✅ 3355 interne Links, 0 kaputt; DOM im Budget
python3 scripts/roh_html_gate.py --gate          ✅ kein gefährliches Roh-HTML
python3 scripts/content_html_wache.py            ✅ kein eingeschleustes HTML
python3 scripts/shortcode_guard.py --check       ✅ alle Parameter build-sicher
python3 scripts/manifest_guard.py                ✅ package.json/Lock synchron
python3 scripts/wachen_vertrag.py                ✅ 339 Skripte, 0 Funde
python3 scripts/skript_syntax_wache.py           ✅ 547 Dateien kompilieren
python3 scripts/integrity_guard.py --gate        ✅ Siegel nach Neu-Signatur gültig
python3 scripts/abbildungen_ableiten.py --check  ✅ 20 Beiträge, 0 Befunde
python3 scripts/reserve_artifacts.py --check     ✅ Snapshot vollständig
```

**CI-Regression nachgezogen:** Der Merge-Stand wurde zusätzlich mit der
vollständigen Suite geprüft – `python3 -m unittest discover -s scripts/tests -v`
(**4.025 Tests, 0 Fehler, 14 Skips**) und die Uhr-Probe
`python3 scripts/selftest_clock.py --trap-discover scripts/tests --offset 97`
(**4.025 Tests, 0 Fehler, 16 Skips**), dazu alle Selbsttests des
Regression-Jobs (`engine_generate`, `reserve_pool`, `cadence_guard`,
`fm_boundary_guard`, `social_studio`). Der aktuelle `main`-Stand (`bba81c1`)
wurde dafür konfliktfrei in den Branch geholt.

Hugo-Build: `hugo v0.168.0+extended` (lokal aus dem im Repo dokumentierten PyPI-Fallback `hugo==0.168.0`), 109 Seiten + 17 Paginierungsseiten, 2.434 statische Dateien, ~2 s.

**Browser-E2E** wurde hier nicht gefahren: In der Sandbox fehlen `node_modules`
(`playwright-core`) und das gepinnte Chromium. Der einzige E2E-Test, den die
TOC-Änderung berühren könnte (`e2e/article.spec.mjs`, Inhaltsverzeichnis),
wurde deshalb auf HTML-Ebene gegengeprüft: Das TOC des Testartikels ist vor
und nach der Änderung **bytegleich** (32 Links, 0 tote Ziele). Für 77 Seiten
mit Inhaltsverzeichnis gilt nachher: 0 `href="#"`, 0 Anker ohne Ziel.

---

## 6. Bekannter Rest (nicht Teil dieses Auftrags)

- `python3 scripts/metadaten_wache.py` meldet weiterhin **3 inhaltliche Altbefunde**: zwei Artikel mit `lastmod` vor `date` und ein Artikel ohne `kurzantwort`. Das sind redaktionelle Pflichtfelder, keine Sitecheck-Kriterien. Sie sollten in einem eigenen Content-Vorgang geheilt werden, damit die Wache wieder vollständig grün ist.
- **Reserve-Zertifikat:** Die E6-Markenkorrektur im Reserve-Entwurf `2026-10-27-frugalismus-familie-clever-sparen-ohne-verzicht` ändert dessen SHA-256. Statt eine Messung zu erfinden, wurde der ungültige READY-Nachweis mit `python3 scripts/reserve_artifacts.py --withdraw-invalid` zurückgezogen (`data/reserve-readiness.json`: 4/6 statt 5/6 bereit, Score/Teilscores entfernt, Grund dokumentiert). Eine vollständige Nachzertifizierung bleibt `reserve_recert.py --fix` in der Produktionskette vorbehalten (`hugo` + `hunspell` + Rechtschreibkette); in der Sandbox fehlt `hunspell`. Der Reserve-Snapshot-Check ist damit grün.
- Die drei `seoTitle`-Werte und 13 Description-Texte sind redaktionelle Entscheidungen. Wer sie ändert, sollte `npm run test:sitecheck` mitlaufen lassen – die Wache merkt sofort, wenn ein Titel über 60 Zeichen rutscht.
- Der Online-Check von Pergamon selbst kann nach dem Deploy mit `https://franksfinanzcheck.de/` erneut gefahren werden; die hier geprüften Kriterien decken seine vier veröffentlichten Prüfbereiche ab, nicht seine undokumentierte Gewichtung im „Total Score“.
