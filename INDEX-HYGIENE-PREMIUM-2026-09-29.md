# 237 nicht indexierte Seiten in der Search Console – Ursache gefunden und behoben (29.09.2026)

**Auslöser (Frank):** „Meine Google Search Console zeigt für den Blog 237 nicht
indexierte Seiten an. Bitte auf Premium-Level einer Profi-Agentur beheben.“

**Kurzfassung:** Kein einziger Artikel war schuld. Die Site hat schlicht **sechsmal
mehr URLs gebaut, als sie Inhalte hat** – 347 nicht indexierbare URLs auf 58 echte
Seiten. Zwei Automatiken haben das erzeugt, beide unbemerkt, beide wachsend mit
jedem neuen Artikel. Die Crawl-Fläche ist jetzt um **89 % reduziert** (347 → 38),
die Ursachen sind an der Quelle geschlossen und durch zwei neue Wachen mit
24 Selbsttests gegen Rückfall gesichert.

> **Korrekturhinweis zu einer früheren Fassung dieses Berichts:** Abschnitt 8
> behauptete zunächst, die Tag-Archive seien „von keiner Artikelseite verlinkt".
> Das war **falsch** – 42 Artikel rendern eine sichtbare Tag-Leiste. Der Fehler
> und seine Ursache sind in Abschnitt 8 dokumentiert; die daraus folgende
> Entscheidung ist dort ebenfalls festgehalten und umgesetzt.

---

## 1 · Befund – am gebauten HTML gemessen, nicht geschätzt

Grundlage ist der Hugo-Build des Repo-Stands (`cbfb618`), also exakt das, was
Produktion ausliefert. Jede `.html`-Datei wurde klassifiziert nach
`<meta name="robots">` und Meta-Refresh:

| Kategorie | URLs | Was Google daraus macht |
|---|---:|---|
| **Indexierbar** | **58** | die eigentliche Site |
| `/page/1/`-Alias-Weiterleitungen | 154 | „Seite mit Weiterleitung“ |
| Tag-Archive (`noindex`) | 147 | „Durch ‚noindex‘-Tag ausgeschlossen“ |
| `/go/`-Affiliate-Weiterleitungen | 20 | „Durch robots.txt blockiert“ (**gewollt**) |
| Pager-Seiten (`/page/2..6/`) | 14 | „Durch ‚noindex‘-Tag ausgeschlossen“ |
| Kategorie-Archive | 4 | „Durch ‚noindex‘-Tag ausgeschlossen“ |
| Newsletter-Funnel, OAuth, 404 | 8 | „Durch ‚noindex‘-Tag ausgeschlossen“ |
| **Summe nicht indexierbar** | **347** | Verhältnis **1 : 5,98** |

Die 237 der Search Console sind die Teilmenge davon, die Google bis heute
tatsächlich entdeckt hat. Die Größenordnung passt exakt.

### Warum keine bestehende Wache das gesehen hat

Der Blog hat 24 intakte Wachen. `schema_seo_gate.py` prüft mit Regel **S6** sogar
ausdrücklich die „Hygiene der dünnen Seiten“ – und war die ganze Zeit **grün**.
Zu Recht: S6 fragt *„trägt dieses Archiv ein noindex?“*, und das tat jedes
einzelne der 147 Archive korrekt.

> Niemand fragte: **„Darf es diese 147 Archive überhaupt geben?“**

Jede Seite war einzeln richtig ausgezeichnet. Der Defekt lag in der **Menge** –
eine Dimension, die keine Wache gemessen hat. Genau diese Lücke schließt die neue
Wache `index_hygiene_gate.py`.

---

## 2 · Ursache 1 – Tags wurden aus SEO-Keywords erzeugt (die URL-Leckage)

In `scripts/engine_generate.py` stand:

```python
kw_yaml  = "[" + ", ".join(f'"{k}"' for k in kws[:8]) + "]"
tag_yaml = "[" + ", ".join(f'"{k}"' for k in kws[:4]) + "]"   # ← die Ursache
```

Dieselbe Zeile in `scripts/generate_drafts.py` (`normalize_tags(keywords[:4])`).

Die ersten vier **SEO-Keywords** eines Artikels wurden direkt zu **Tags**. Keywords
sind aber per Definition long-tail und pro Artikel einmalig – genau das ist ihr
Zweck. Jeder neue Artikel prägte damit bis zu vier **brandneue** Tags, und jeder
neue Tag kostet **zwei** URLs (Archiv + `/page/1/`-Alias).

**Das war kein einmaliger Fehler, sondern ein Leck mit konstanter Rate:
~8 nutzlose URLs pro Artikel.** Nach 63 Artikeln:

* **217 Roh-Tags** → 147 Archive (Hugo führt Slug-Kollisionen wie
  `Mesh WLAN` / `Mesh-WLAN` zusammen)
* **193 Tags mit genau EINEM Artikel** (89 %)
* nur 24 Tags mit mehr als einem Artikel

Wie kaputt die Tags inhaltlich waren, zeigt ein Blick in die Liste:

* **Ganze Artikeltitel als Tag:** `5 einfache Frugalismus-Tricks für den Alltag`,
  `Stromspeicher kaufen 2026 – Lohnt sich die Investition`,
  `Konto & Karten-Update: was sich jetzt für dich ändert`
* **Abgeschnittene Satzfragmente:** `Finanzieller`, `Wirklich`,
  `Grundversorgung Strom Kosten senken –`
* **Dubletten in vier Schreibweisen:** `Kfz-Versicherung`, `Kfz Versicherung Vergleich`,
  `Kfz Versicherung wechseln`, `Kfz Haftpflicht`
* **Unsichtbares Sonderzeichen:** `Interrail\u202f+\u202fBahncard` enthielt zweimal
  U+202F (schmales geschütztes Leerzeichen aus der Typografie-Sicherung) und
  erzeugte damit eine prozent-kodierte Kaputt-URL.

### Behebung: ein kuratiertes Register statt Keyword-Abfall

Neu: **`data/seo/tag_register.yaml`** – 25 kanonische Tags, jeder einem der sechs
Pillars zugeordnet, mit vollständiger Synonymliste. Alle 217 Roh-Tags sind dort
abgebildet; kein einziger blieb ungemappt.

| Pillar | Tags |
|---|---|
| strom-sparen | Heizkosten senken (10) · Stromkosten senken (7) · Gastarif wechseln (6) · Gasrechnung prüfen (5) |
| frugalismus | Geld sparen im Alltag (9) · Budget planen (7) · Frugalismus (7) · Haushaltsbuch führen (6) · Notgroschen (4) |
| versicherungen | Gesundheit und Vorsorge (5) · Versicherungen vergleichen (5) · Kfz-Versicherung (4) · Hausratversicherung (3) · Haftpflichtversicherung (2) · Wohngebäudeversicherung (2) |
| internet-dsl | DSL-Vergleich (5) · Internet und Mobilfunk (5) · WLAN verbessern (4) · DNS und Netzsicherheit (2) |
| konto-karten | Girokonto (4) · Altersvorsorge (3) · Kreditkarte und Kredit (3) · Tagesgeld und Zinsen (3) |
| mietwagen | Mietwagen und Wohnmobil (3) · Reisekosten sparen (3) |

**Jeder Tag hat mindestens 2 Artikel** – kein Thin-Archiv mehr.

`scripts/tag_governance.py --apply` hat das Frontmatter von **62 Artikeln**
normalisiert (Synonym → kanonischer Name, Unicode-Bereinigung, Dedupe, Kappung
auf 4 Tags). Die **Keywords blieben unverändert**: sie gehören ins
`keywords`-Feld, wo sie Schema und Related-Matching speisen, **ohne je eine URL
zu bauen**.

**Quelle geschlossen:** beide Generatoren rufen jetzt `tags_fuer()` auf und
bekommen ausschließlich Register-Tags. Passt kein Keyword und kein Titelwort,
greift das Pillar-Auffangnetz – **ein Tag wird nie mehr erfunden.**

---

## 3 · Ursache 2 – 154 Weiterleitungen, die niemand angefordert hat

Hugo legt für **jede** paginierte Liste zusätzlich eine Seite `…/page/1/` an, die
per Meta-Refresh auf die Liste selbst weiterleitet. Bei 147 Tag-Archiven,
4 Kategorien und 3 Sektionen waren das **154 reine Weiterleitungs-URLs**.

Der eigentliche Skandal: **`/page/1/` ist nirgends verlinkt.** Der Paginator zeigt
für Seite 1 immer auf die Basis-URL. Diese 154 URLs existierten ausschließlich für
den Crawler – und wurden von ihm brav als „Seite mit Weiterleitung“ gemeldet.

**Behebung** (`hugo.toml`):

```toml
[pagination]
pagerSize = 8
disableAliases = true   # ← 154 URLs weg, keine einzige Funktion verloren
```

Die echten Pager (`/page/2/` … `/page/6/`) bleiben unverändert erhalten.

---

## 4 · Drei weitere Funde, die dabei aufgefallen sind

**a) Kategorie-Taxonomie ohne Zweck (8 URLs).** `categories` kannte nur zwei Werte
(„Ratgeber“ 61×, „News“ 5×) und war **nirgends verlinkt**. Die drei Stellen, die
das Feld lesen (`schema_article.html` → `articleSection`, die Related-Karten und
die Voice-Toolbar), nutzen ausschließlich `.Params.categories` als **Wert**, nie
die Archiv-URL. Die Taxonomie ist jetzt in `hugo.toml` abgeschaltet – das
Frontmatter-Feld bleibt voll lesbar, nur die 8 Archivseiten entfallen.
Verifiziert: `"articleSection":["Ratgeber"]` steht unverändert im Schema.
Nebenbei korrigiert: zwei Artikel trugen die Streukategorien „Energie“ bzw.
„Versicherung“.

**b) `/transparenz/` fehlte in der Sitemap.** Die Seite ist indexierbar und aus dem
Footer verlinkt, stand aber in keiner Sitemap – für Google also nur über interne
Links auffindbar („Gefunden – zurzeit nicht indexiert“). Als Vertrauensseite
(E-E-A-T) gehört sie zu den Money-Pages und ist jetzt in `layouts/sitemap.xml`
aufgenommen. Sitemap: 55 → 56 Einträge.

**c) Kaputter Tag-Slug.** Der zunächst gewählte Name „Internet- und Handytarif“
hätte `/tags/internet--und-handytarif/` erzeugt (doppelter Bindestrich). Die neue
Wache hat das im ersten Lauf selbst gefunden – Name jetzt „Internet und Mobilfunk“.

Ausdrücklich **nicht** angefasst: die **20 `/go/`-Weiterleitungen**. Sie sind
gewollt, per `robots.txt` gesperrt und tragen bereits
`rel="sponsored nofollow noopener"` – korrektes Affiliate-Handwerk, das in der GSC
zu Recht als „blockiert“ erscheint.

---

## 5 · Ergebnis

```
                         VORHER          NACHHER        Δ
  HTML-URLs gesamt          405              96        −309
  Indexierbare Seiten        58              58         unverändert
  Nicht indexierbar         347              38        −309  (−89 %)
  Verhältnis             1 : 5,98        0,66 : 1
  ──────────────────────────────────────────────────────────────
  Tag-Archive               147               0        −147
  /page/1/-Aliase           154               0        −154
  Kategorie-Archive           4               0          −4
  Pager-Seiten               14              10          −4
  Roh-Tags (Vokabular)      217              25        −192
  Tags mit 1 Artikel        193               0        −193
  Sitemap-Einträge           55              56          +1
  ──────────────────────────────────────────────────────────────
  Verbleibend (alles gewollt): 20 /go/ · 10 Pager · 7 Funnel/OAuth · 1 404
```

Alle bestehenden Wachen bleiben grün:
`schema_seo_gate.py` (0 harte Funde, 0 Hinweise) · `seo_cockpit.py --strict`
(P1 0, P2 0) · `casing_guard.py` (unverändert 7/44, vorbestehend).

---

## 6 · Absicherung gegen Rückfall

| Wache | Regeln | Selbsttests | Läuft |
|---|---|---|---|
| `scripts/tag_governance.py` | T1–T8 | 14 | Deploy (vor Build, selbstheilend) + wöchentlich |
| `scripts/index_hygiene_gate.py` | H1–H8 | 10 | Deploy (nach Build) + wöchentlich |

**`tag_governance.py`** – T1 Register-Integrität · T2 unbekannter Tag ·
T3 Synonym statt kanonisch · T4 Thin-Archiv (< 2 Artikel) · T5 Tag-Menge ·
T6 Form/Sonderzeichen · T7 Kategorie · T8 tote Registerzeile.
`--apply` heilt selbst; unbekannte Tags werden **nicht geraten**, sondern
gemeldet – die Entscheidung „Registereintrag oder Keyword“ bleibt redaktionell.

**`index_hygiene_gate.py`** – misst die **Crawl-Fläche** des fertigen Builds:
H1 Sitemap-Deckung · H2 `/page/1/`-Aliase · H3 Tag-Archive (jetzt: 0 erlaubt) ·
H4 Kategorie-Archive · H5 Verhältnis (max. 1,0 : 1) · H6 kaputte Slugs ·
H7 Waisenseiten · H8 `noindex` in der Sitemap.
Bewusst **ohne** `--fix`: jeder Fund ist eine Architekturentscheidung.

Ein Detail, das die Wache selbst fast wertlos gemacht hätte: Produktion baut mit
`hugo --minify`, und der Minifier entfernt die Anführungszeichen um
Attributwerte (`href=/posts/…` statt `href="/posts/…"`). Die erste Fassung der
Link-Erkennung verlangte Anführungszeichen und meldete daraufhin im
minifizierten Build 26 Artikel als „Waisenseite“ – reine Falschalarme. Beides
ist behoben und durch einen eigenen Selbsttest (minifiziertes HTML) abgesichert.

Neue npm-Skripte:

```bash
npm run tags              # Bestand der Taxonomie
npm run tags:check        # Wache
npm run tags:fix          # Frontmatter normalisieren
npm run index:hygiene     # Build + Crawl-Fläche messen
npm run test:index:hygiene   # 24 Selbsttests
```

---

## 7 · Was in der Search Console jetzt passiert (ehrliche Erwartung)

Die Zahl **fällt nicht sofort** – und sie kann kurzfristig sogar erst die Kategorie
wechseln. Das ist normal und kein Rückschritt:

1. **Tag 1–3:** Neuer Build live, Sitemap mit 56 Einträgen. Die 309 entfernten URLs
   liefern jetzt 404 statt `noindex`/Redirect.
2. **Woche 1–3:** Google crawlt die alten URLs nach und bucht sie von „Durch
   ‚noindex‘ ausgeschlossen“ bzw. „Seite mit Weiterleitung“ nach **„Nicht gefunden
   (404)“** um. Die Gesamtzahl bleibt zunächst ähnlich. **Das ist der gewünschte
   Zwischenschritt.**
3. **Woche 3–10:** 404er verschwinden dauerhaft aus dem Bericht. `noindex`-Seiten
   werden dagegen unbegrenzt weiter gecrawlt und gemeldet – deshalb ist 404 hier
   klar die bessere Endstation als eine Weiterleitung.
4. **Dauerhaft:** Der Bericht pendelt sich bei rund **38** nicht indexierten URLs
   ein – davon 20 gewollte `/go/`-Weiterleitungen, 10 Pager, 7 Newsletter-/
   OAuth-Seiten und die 404. Alles davon ist Absicht.

Eine Weiterleitung der alten Tag-URLs auf die neuen wurde **bewusst verworfen**:
die alten Archive waren `noindex`, standen in keiner Sitemap und hatten keine
externen Links – es gibt keine Linkkraft zu erhalten, und 301-Ketten würden den
Bericht nur dauerhaft mit „Seite mit Weiterleitung“ füllen.

**Nichts zu tun in der GSC.** Kein Entfernungsantrag, keine manuelle
Neuindexierung nötig. Sinnvoll ist nur: nach dem Deploy die **Sitemap einmal neu
einreichen** und in 4 Wochen erneut draufschauen.

---

## 8 · Die Tag-Archive – mein Analysefehler und die Entscheidung

### 8.1 Was ich zuerst berichtet habe – und warum es falsch war

Die erste Fassung dieses Berichts behauptete:

> „Die Tag-Archive sind von keiner Artikel-, Pillar- oder Startseite verlinkt.
> Sie sind eine geschlossene Insel."

**Das war falsch.** Nachgemessen am Build:

* **42 Artikel** rendern im Footer eine **sichtbare, gestylte Tag-Leiste**
  (`<ul class="post-tags">` in `layouts/single.html` und
  `layouts/_default/single.html`; Styling über PaperMod `post-single.css` und
  `assets/css/extended/zzz-agency-polish.css`).
* Die Archive waren also **echte, benutzbare Navigation** – keine Insel.

Ursache meines Fehlers – zwei Effekte gleichzeitig:

```
gesucht:       href="/tags/                            (relativ + Anführungszeichen)
ausgeliefert:  href=https://franksfinanzcheck.de/tags/ (absolut + minifiziert)
```

Hugo schreibt hier absolute Permalinks, und der geprüfte Build war mit
`--minify` erzeugt (der Minifier entfernt die Anführungszeichen). Der Suchbegriff
konnte damit nicht treffen. Bitter: Es ist **derselbe Minifier-Fallstrick**, den
ich in `index_hygiene_gate.py` (H7) korrekt behandelt und eigens durch einen
Selbsttest abgesichert habe – in der manuellen Analyse daneben bin ich ihm
trotzdem aufgesessen. Konsequenz für die Zukunft: Aussagen über interne
Verlinkung nur noch über `interne_ziele()` der Wache, nie über einen Ad-hoc-Grep.

Nicht betroffen: der gesamte Rest des Berichts. Befund, beide Ursachen und alle
Kennzahlen stammen aus der Klassifikation je Datei über `robots`-Meta und
Meta-Refresh – nicht aus diesem Grep.

### 8.2 Die Entscheidung (Frank, 29.09.2026): vollständig entfernen, Navigation ersetzen

Auf der korrigierten Grundlage lautete die Frage nicht mehr „totes Gewicht
wegräumen?", sondern: **Wohin sollen diese 2–4 internen Links pro Artikel
zeigen?** Denn das war der eigentliche Missstand – die Leiste war nützlich, ihre
**Ziele** waren es nicht: jeder Klickpfad endete auf einem `noindex`-Archiv, das
per Definition nie ranken kann.

Entschieden und umgesetzt wurde daher:

* Die Taxonomien `tags` **und** `categories` sind in `hugo.toml` abgeschaltet –
  es entsteht keine `/tags/`- und keine `/categories/`-URL mehr (**−27 URLs**).
* Die Tag-Leiste ist durch **`layouts/_partials/themenwelt_chips.html`** ersetzt:
  dieselbe Position am Artikelende, **dieselbe Optik** (bewusst dieselben
  `.post-tags`-Klassen → kein neues CSS, keine Design-Drift), aber die Chips
  zeigen auf die **sechs indexierbaren Pillar-Ratgeber**. Die eigene Themenwelt
  steht vorn und ist als „· dein Thema" ausgezeichnet, die übrigen fünf sind der
  seitliche Absprung.
* Das `tags`-Feld im Frontmatter **bleibt** – es speist weiter Hugos
  Related-Matching (Gewicht 80) und den Keyword-Rückfall im Article-Schema.
  Beides verifiziert: Verwandten-Karten und `"keywords": …` stehen unverändert
  im gebauten HTML.

**Der eigentliche Gewinn ist nicht die URL-Ersparnis, sondern die Umleitung der
Linkkraft:** Vorher verschenkten 42 Artikel je 2–4 interne Links an `noindex`-
Seiten. Jetzt fließen von **jedem** Artikel sechs Links auf genau die sechs
Seiten, die ranken sollen. Aus einer Crawl-Last wurde ein Ranking-Signal für die
Money-Pages.

**Abgrenzung zu den Nachbarbausteinen** (bewusst keine Dopplung):

| Baustein | Wo | Funktion |
|---|---|---|
| `pillar_box.html` | nach dem Artikeltext | **ein** prominenter CTA in den **eigenen** Ratgeber |
| `themenwelten.html` | Startseite, `/posts/` | volles Karten-Raster aller sechs Themen |
| `themenwelt_chips.html` | Artikelende (neu) | kompakte **Quer**-Navigation über alle sechs, eigenes Thema zuerst |

Der Baustein ist **fail-closed** wie `themenwelten.html`: fehlt ein Ratgeber oder
ist er unveröffentlicht, bricht der Build ab, statt still eine leere Leiste zu
bauen. Die Klick-Messung (`cta_click`, Platzierung `artikel-themenwelten`) ist
angeschlossen, damit der Absprung „Artikelende → Ratgeber" im Umsatztrichter
sichtbar bleibt.

**Rückbau**, falls die Archive je wieder gewollt sind: `tag = "tags"` im
`[taxonomies]`-Block eintragen, `max_tag_archive` in `index_hygiene_gate.py`
anheben – beides ist an Ort und Stelle kommentiert.

## 9 · Geänderte Dateien

**Neu**
* `data/seo/tag_register.yaml` – 25 kanonische Tags, 217 Synonyme, Politik
* `scripts/tag_governance.py` – Wache T1–T8, `--apply`, 14 Selbsttests
* `scripts/index_hygiene_gate.py` – Wache H1–H8, 10 Selbsttests
* `layouts/_partials/themenwelt_chips.html` – Themen-Navigation am Artikelende

**Geändert**
* `hugo.toml` – `disableAliases`, `[taxonomies]` leer (keine Taxonomie mehr)
* `layouts/single.html`, `layouts/_default/single.html`,
  `layouts/pillar/single.html` – Tag-Leiste → Themenwelt-Chips
* `layouts/sitemap.xml` – `/transparenz/` ergänzt
* `scripts/engine_generate.py` – Tags aus dem Register statt aus Keywords
* `scripts/generate_drafts.py` – dito (`_register_tags()`)
* `.github/workflows/deploy.yml` – beide Wachen in der Kette
* `.github/workflows/seo-weekly.yml` – Crawl-Fläche im Wochenbericht
* `package.json` – 5 neue Skripte
* 62 Artikel in `content/posts/` – Frontmatter kanonisiert
