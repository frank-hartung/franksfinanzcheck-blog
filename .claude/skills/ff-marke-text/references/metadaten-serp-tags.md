# Metadaten, Snippet-Grenzen und das Tag-Register

> Wörtlich aus `CLAUDE.md` übernommen am 01.11.2026 (Skill-Umbau). Kein Satz wurde umformuliert, gekürzt oder erfunden; die Überschriften sind eine Ebene tiefer gehängt. Änderungen hier sind Änderungen am Regelwerk – sie brauchen denselben Nachweis wie vorher: Selbsttest der betroffenen Wache, dann Commit.

### Metadaten und Cover-Wahrheit (seit 14.10.2026, Nachschärfung #743)

- **Ein Cover ist nur wahr, wenn es aus seinem Titel neu rendert.** Der Generator
  erneuerte früher nur bei Design-Drift; eine Titeländerung aktualisierte das
  Manifest, nicht das Bild. `check_covers` meldete deshalb „Stale: 0“, obwohl
  63 von 96 JPGs nicht mehr ihrem Titel entsprachen. Heute ist Titel-Drift ein
  Neu-Render-Auslöser, und `covers:render-check` vergleicht jedes Bild pixelgenau.
- **Zahlen statt Behauptungen gilt auch auf Covers.** Eine Spar-Pille (aus
  `savings:` oder Description) braucht ihre Zahl MIT Einheit im Fließtext
  (`metadaten_wache.py`, M6). „Schritt 5“ belegt kein „5 € im Monat“.
- **`lastmod` ist die letzte inhaltliche Änderung**, nie vor `date`. Pillar-Titel
  ≤ 60 Zeichen, Descriptions 100–160 Zeichen (M1/M2/M3).
- **Reparatur eines Cover-Befunds nur über die Pipeline:**
  `python3 scripts/generate_covers.py --slug <slug>` bzw.
  `--pillars --slug pillar-<silo>`. Nie das JPG von Hand bearbeiten.

### Ein Snippet ist 155 Zeichen und 985 Pixel (DAUERVORGABE, seit 27.10.2026)

Am 27.10.2026 legte ein fremder Crawl (Screaming Frog) einen Befundbericht
über **eine** Seite vor: fehlende Sicherheits-Header, Meta-Description über
155 Zeichen, dieselbe Description über 985 Pixel, ein interner Link ohne
Ankertext, „mehrere H2". Vier davon waren keine Fehlmessung des Werkzeugs,
sondern ein **zu großzügiger eigener Maßstab**:

- `metadaten_wache` erlaubte 160 Zeichen, `seo_cockpit` 165 – der Markt
  kürzt bei 155. Zwei Grenzen im Haus, keine davon die des Marktes.
- Ankertext prüfte niemand. Die Karten-Links der Listenansicht waren leer
  (`<a class="entry-link" aria-label="…"></a>`): für Screenreader benannt,
  für Crawler ein Link ohne Text.
- „Mehrere H2" ist **kein** Befund (HTML erlaubt beliebig viele) – vier
  Seiten sprangen aber in der Rangfolge (h1→h3, h2→h4). Das ist einer.

Regeln:

- **Eine Zahl, zwei Messstellen.** Grenzen und Breitenmaß stehen in
  `scripts/serp_limits.py` (100/155 Zeichen, 985 px in Arial 14 px,
  Advance-Breiten der Helvetica-Kernmetrik – Arial ist metrisch identisch).
  `metadaten_wache` (Quelle) und `seo_cockpit` (gebautes HTML) **importieren**
  sie; eine zweite Grenze im Code ist ein Befund
  (`scripts/tests/test_serp_limits.py`, Klasse `Bindung`).
- **Breite ist nicht Zeichenzahl.** 135 Zeichen aus breiten Wörtern laufen
  über 985 px, 155 schmale nicht. Wer nur zählt, meldet Grün für ein
  abgeschnittenes Snippet. Zeichen ohne Metrik (Emoji, CJK) werden **nicht**
  geschätzt: `breite_px()` gibt `None` und die Wache meldet „nicht prüfbar".
- **Ein Link braucht Text, nicht nur `aria-label`.** Icon-Links und
  Karten-Links tragen eine `sr-only`-Spanne im Link selbst; `aria-label`
  bleibt für Screenreader, ersetzt aber keinen Ankertext.
- **Rangfolge statt H2-Zählung.** `seo_cockpit` prüft Sprünge (h2→h4), nicht
  die Anzahl der H2. Wer eine Rangstufe überspringt, ändert die Markdown-Ebene
  (`####` → `###`), nicht das Aussehen.
- **Verdrahtung:** `e2e.yml` (jeder PR) fährt `seo_cockpit --fail-on
  description-length,description-breite,heading-order`, die
  `linktext_wache` (Linktexte und Alt-Texte) und `metadaten_wache`;
  `npm run serp:check` ist der lokale Zwilling. Bewusst **kein**
  Deploy-Blocker: ein zu langes Snippet darf die Auslieferung der Live-Site
  nicht anhalten (C34), es darf aber nicht unbemerkt nach `main`.
- **Ein Befund, eine Wache.** Ankertext (`link-no-anchor`) steht im Cockpit
  weiter im Bericht, sperrt aber nicht: derselbe Befund kam am 27.10.2026
  auch über Seobility und hat mit `scripts/linktext_wache.py` eine breitere
  Wache mit eigenen Ausnahmen (`data-ff-linktext-frei`, `<a>` ohne `href`)
  und Selbsttest bekommen. Zwei Wachen für einen Befund laufen auseinander.
- **Auch die Schreiber importieren die SSOT** (seit 29.10.2026, #925): Wer
  Descriptions **baut**, hält sich an dieselbe Datei. `keyword_optimizer`
  (Keyword-Gate im Deploy-Pfad), `meta_optimizer` und `quality_score`
  importieren `serp_limits`; ihre alten eigenen Grenzen (70–160 Zeichen,
  165 im Cockpit-Rat) sind gelöscht. Der #925-Befund entstand genau dort: Der
  Schreiber setzte ein Schlüsselwort vor eine bereits 142 Zeichen lange
  Description – 153 Zeichen, aber **1011 px**, also zu breit. Der Zähler im
  Schreiber war grün, das Fenster des Marktes war abgeschnitten.
- **Geheilt wird an der Quelle, nicht im Bericht** (seit 29.10.2026, #925):
  `metadaten_wache.py --fix` kürzt ein zu breites Snippet deterministisch an
  der Wortgrenze (`serp_limits.auf_snippet_kuerzen`, Satzende behalten,
  idempotent) und richtet `lastmod` an `date` aus. Der Deploy-Pfad fährt
  deshalb Keyword-Gate → Metadaten-Selbsttest → `metadaten_wache --fix` und
  **veröffentlicht das Geheilte**. Rot werden darf die Wache weiter (C34):
  Sperren wäre ein Deploy-Blocker, also bleibt sie laut – im Log und als
  Annotation – statt still.

Vertrag: Berichte `SERP-SPIEGEL-SCREAMING-FROG-HIGHEND-2026-10-27.md` und
`WF-7B6B-925-DAUERHEILUNG-PREMIUM-2026-10-29.md` ·
Selbsttests `metadaten_wache --selftest` (13 Proben) und
`seo_cockpit`/`serp_limits` (`npm run test:serp`).

### Tags kommen aus dem Register, nie aus Keywords (Wache seit 29.09.2026)

Die Search Console meldete 237 nicht indexierte Seiten. Ursache war nicht der
Content, sondern die Taxonomie-Automatik: beide Generatoren setzten
`tags = keywords[:4]`. Keywords sind long-tail und pro Artikel einmalig – jeder
Artikel prägte damit **vier neue Tags = acht nutzlose URLs** (Archiv +
`/page/1/`-Alias). Nach 63 Artikeln: 217 Roh-Tags, 147 Archive, 193 davon mit
genau einem Artikel, insgesamt 347 nicht indexierbare URLs auf 58 echte Seiten.

**Eine Quelle:** `data/seo/tag_register.yaml` – 25 kanonische Tags, jeder einem
Pillar zugeordnet, mit vollständiger Synonymliste. `tag_governance.tags_fuer()`
ist die **einzige** erlaubte Tag-Quelle für neuen Content. Die Grenze ist
fail-closed und wird an jeder Writer-Ausgabe erneut geprüft: `engine_generate.py`,
`generate_drafts.py`, `ki_shared.py` (Claude/News) und
`pinterest_seo_healer.py`. Ein Tag wird **nie erfunden**: greift nichts,
decidiert die Redaktion über einen Registereintrag – oder der Begriff bleibt
ein Keyword. Keywords gehören ins `keywords`-Feld, wo sie Schema und
Related-Matching speisen, **ohne je eine URL zu bauen**. Ein fehlendes Register
bricht den Writer ab; es gibt keinen Legacy-Fallback auf `keywords[:4]`.

**Zwei Wachen, zwei Ebenen:**
`python3 scripts/tag_governance.py` (T1–T8, **mit** `--apply`) prüft das
Frontmatter: unbekannte Tags, Synonyme statt kanonischer Namen, Thin-Archive
(< 2 Artikel), Tag-Menge, Sonderzeichen (U+202F/U+00A0 erzeugen kaputte Slugs),
Kategorie, tote Registerzeilen.
`python3 scripts/index_hygiene_gate.py` (H1–H8, **ohne** `--fix`) misst die
**Crawl-Fläche des Builds** gegen ein Budget: Sitemap-Deckung,
`/page/1/`-Aliase, Tag-Budget (0), Kategorie-Archive, Verhältnis
indexierbar : nicht indexierbar (max. 1,0 : 1), kaputte Slugs, Waisenseiten,
`noindex` in der Sitemap. Das Deploy-Gate ist hart: Ein Verstoß stoppt den
Publish, statt nur eine Warnung zu schreiben.

**Merke:** `schema_seo_gate.py` S6 war die ganze Zeit grün – es fragt „trägt
dieses Archiv ein noindex?“, nicht „darf es dieses Archiv geben?“. Eine Seite
kann einzeln korrekt und in der Menge trotzdem ein Defekt sein. Deshalb misst
`index_hygiene_gate.py` Anzahlen, nicht Attribute.

**Keine Taxonomie-Archive mehr (Entscheidung 29.09.2026, Frank).** Der
`[taxonomies]`-Block in `hugo.toml` ist **leer** – es gibt weder `/tags/` noch
`/categories/`. Die Tag-Leiste im Artikel-Footer war echte, sichtbare
Navigation, zeigte aber auf `noindex`-Archive: 42 Artikel verschenkten je 2–4
interne Links an Seiten, die nie ranken können. Ersetzt durch
`layouts/_partials/themenwelt_chips.html` – gleiche Position, gleiche Optik
(bewusst dieselben `.post-tags`-Klassen, kein neues CSS), aber Ziele sind die
sechs **indexierbaren** Pillar-Ratgeber. Aus Crawl-Last wurde Linkkraft auf die
Money-Pages.

**Drei Themen-Bausteine, keine Dopplung:** `pillar_box.html` = ein CTA in den
eigenen Ratgeber (nach dem Text) · `themenwelten.html` = Karten-Raster auf
Startseite und `/posts/` · `themenwelt_chips.html` = Quer-Navigation am
Artikelende. Alle drei fail-closed gegen fehlende Ratgeber.

**Nicht anfassen:** `[pagination] disableAliases = true` und der leere
`[taxonomies]`-Block – beide sind dokumentierte Index-Hygiene-Entscheidungen,
keine Altlast. Wer Archive zurückholt, muss `max_tag_archive` in
`index_hygiene_gate.py` mit anheben (steht dort kommentiert). Bericht:
`INDEX-HYGIENE-PREMIUM-2026-09-29.md`.
