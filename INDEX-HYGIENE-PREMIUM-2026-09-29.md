# 237 nicht indexierte Seiten in der Search Console – Ursache gefunden und behoben (29.09.2026)

**Auslöser (Frank):** „Meine Google Search Console zeigt für den Blog 237 nicht
indexierte Seiten an. Bitte auf Premium-Level einer Profi-Agentur beheben.“

**Kurzfassung:** Kein einziger Artikel war schuld. Die Site hat schlicht **sechsmal
mehr URLs gebaut, als sie Inhalte hat** – 347 nicht indexierbare URLs auf 58 echte
Seiten. Zwei Automatiken haben das erzeugt, beide unbemerkt, beide wachsend mit
jedem neuen Artikel. Die Crawl-Fläche ist jetzt um **81 % reduziert** (347 → 65),
die Ursachen sind an der Quelle geschlossen und durch zwei neue Wachen mit
23 Selbsttests gegen Rückfall gesichert.

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
  Indexierbare Seiten        58              58         unverändert
  Nicht indexierbar         347              65        −282  (−81 %)
  Verhältnis             1 : 5,98        1 : 1,12
  ──────────────────────────────────────────────────────────────
  Tag-Archive               147              26        −121
  /page/1/-Aliase           154               0        −154
  Kategorie-Archive           4               0          −4
  Roh-Tags                  217              25        −192
  Tags mit 1 Artikel        193               0        −193
  Sitemap-Einträge           55              56          +1
```

Alle bestehenden Wachen bleiben grün:
`schema_seo_gate.py` (0 harte Funde, 0 Hinweise) · `seo_cockpit.py --strict`
(P1 0, P2 0) · `casing_guard.py` (unverändert 7/44, vorbestehend).

---

## 6 · Absicherung gegen Rückfall

| Wache | Regeln | Selbsttests | Läuft |
|---|---|---|---|
| `scripts/tag_governance.py` | T1–T8 | 14 | Deploy (vor Build, selbstheilend) + wöchentlich |
| `scripts/index_hygiene_gate.py` | H1–H8 | 9 | Deploy (nach Build) + wöchentlich |

**`tag_governance.py`** – T1 Register-Integrität · T2 unbekannter Tag ·
T3 Synonym statt kanonisch · T4 Thin-Archiv (< 2 Artikel) · T5 Tag-Menge ·
T6 Form/Sonderzeichen · T7 Kategorie · T8 tote Registerzeile.
`--apply` heilt selbst; unbekannte Tags werden **nicht geraten**, sondern
gemeldet – die Entscheidung „Registereintrag oder Keyword“ bleibt redaktionell.

**`index_hygiene_gate.py`** – misst die **Crawl-Fläche** des fertigen Builds:
H1 Sitemap-Deckung · H2 `/page/1/`-Aliase · H3 Tag-Budget (max. 35) ·
H4 Kategorie-Archive · H5 Verhältnis (max. 2,0 : 1) · H6 kaputte Slugs ·
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
npm run test:index:hygiene   # 23 Selbsttests
```

---

## 7 · Was in der Search Console jetzt passiert (ehrliche Erwartung)

Die Zahl **fällt nicht sofort** – und sie kann kurzfristig sogar erst die Kategorie
wechseln. Das ist normal und kein Rückschritt:

1. **Tag 1–3:** Neuer Build live, Sitemap mit 56 Einträgen. Die 281 entfernten URLs
   liefern jetzt 404 statt `noindex`/Redirect.
2. **Woche 1–3:** Google crawlt die alten URLs nach und bucht sie von „Durch
   ‚noindex‘ ausgeschlossen“ bzw. „Seite mit Weiterleitung“ nach **„Nicht gefunden
   (404)“** um. Die Gesamtzahl bleibt zunächst ähnlich. **Das ist der gewünschte
   Zwischenschritt.**
3. **Woche 3–10:** 404er verschwinden dauerhaft aus dem Bericht. `noindex`-Seiten
   werden dagegen unbegrenzt weiter gecrawlt und gemeldet – deshalb ist 404 hier
   klar die bessere Endstation als eine Weiterleitung.
4. **Dauerhaft:** Der Bericht pendelt sich bei rund **65** nicht indexierten URLs
   ein, davon ~20 gewollte `/go/`-Weiterleitungen und ~11 Pager.

Eine Weiterleitung der alten Tag-URLs auf die neuen wurde **bewusst verworfen**:
die alten Archive waren `noindex`, standen in keiner Sitemap und hatten keine
externen Links – es gibt keine Linkkraft zu erhalten, und 301-Ketten würden den
Bericht nur dauerhaft mit „Seite mit Weiterleitung“ füllen.

**Nichts zu tun in der GSC.** Kein Entfernungsantrag, keine manuelle
Neuindexierung nötig. Sinnvoll ist nur: nach dem Deploy die **Sitemap einmal neu
einreichen** und in 4 Wochen erneut draufschauen.

---

## 8 · Offener Punkt zur Entscheidung – die 26 Tag-Archive

Bei der Analyse kam heraus, dass die Tag-Archive **von keiner einzigen
Artikel-, Pillar- oder Startseite verlinkt sind**. Die einzigen Seiten, die auf
`/tags/…` zeigen, sind die Tag-Seiten selbst (Brotkrumen). Sie sind damit eine
**geschlossene Insel**: `noindex` (bringen also nie Traffic) und unverlinkt
(bringen also auch keine interne Linkkraft).

Der Kommentar in `hugo.toml` begründete sie bisher mit „bleiben erhalten
(interne Verlinkung)“ – diese Begründung trifft im aktuellen Build **nicht zu**.

Damit gibt es zwei saubere Wege. Beide sind vertretbar, deshalb liegt die
Entscheidung bei dir:

* **A – Archive entfernen** (`[taxonomies]`-Block in `hugo.toml` leeren):
  −27 weitere URLs, Endstand 38 statt 65. Das `tags`-Feld bleibt als Metadatum
  erhalten und speist weiter Related-Matching und Schema – genau wie es jetzt
  schon bei `categories` gelöst ist. Ein Einzeiler.
* **B – Archive aktivieren:** Tag-Chips unter jedem Artikel ausspielen. Dann
  erfüllen die 26 Seiten ihren dokumentierten Zweck als interne Crawl-Pfade.
  Kleiner Eingriff ins Artikel-Layout.

Bis zur Entscheidung bleibt der Stand wie jetzt: 26 kuratierte, saubere Archive
statt 147 kaputter – der Schaden ist in jedem Fall behoben.

---

## 9 · Geänderte Dateien

**Neu**
* `data/seo/tag_register.yaml` – 25 kanonische Tags, 217 Synonyme, Politik
* `scripts/tag_governance.py` – Wache T1–T8, `--apply`, 14 Selbsttests
* `scripts/index_hygiene_gate.py` – Wache H1–H8, 8 Selbsttests

**Geändert**
* `hugo.toml` – `disableAliases`, `[taxonomies]` ohne `category`
* `layouts/sitemap.xml` – `/transparenz/` ergänzt
* `scripts/engine_generate.py` – Tags aus dem Register statt aus Keywords
* `scripts/generate_drafts.py` – dito (`_register_tags()`)
* `.github/workflows/deploy.yml` – beide Wachen in der Kette
* `.github/workflows/seo-weekly.yml` – Crawl-Fläche im Wochenbericht
* `package.json` – 5 neue Skripte
* 62 Artikel in `content/posts/` – Frontmatter kanonisiert
