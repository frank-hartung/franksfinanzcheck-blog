# SEO-Parität im Eigenbau – was Yoast Premium kann, was hier schon läuft

Stand: 28.10.2026 · Bestandsaufnahme, keine Codeänderung
Anlass: Anfrage „Yoast SEO Premium kostenlos nachbauen“

## Zuerst die zwei harten Fakten

1. **Yoast ist ein WordPress-Plugin. Dieses Repository ist Hugo.**
   Es gibt kein WordPress, keine `wp-content/plugins`, keine Plugin-API,
   keine Datenbank. Ein Yoast-Nachbau wäre hier nicht installierbar, sondern
   müsste komplett neu als Hugo-Template + Python-Gate gebaut werden – also
   ohnehin Eigenbau, kein „kostenloses Yoast“.
2. **Premium-Funktionen selbst implementieren ist erlaubt, fremden
   Premium-Code beschaffen nicht.** Funktionsideen (Redirect-Manager,
   interne Linkvorschläge, mehrere Fokus-Keywords) sind nicht geschützt;
   eine Kopie des kostenpflichtigen Plugins oder eine „nulled“-Version schon.
   Nulled-Builds sind zudem der häufigste Verbreitungsweg für Backdoors in
   WordPress – bei einem Blog mit Affiliate-Einnahmen ein direkter
   wirtschaftlicher Schaden.

Dieses Repo macht es bereits richtig vor: `docs/ANLEITUNG-SEO-COCKPIT.md`
sagt ausdrücklich „Eigenständige Implementierung, funktional von OpenSEO
inspiriert, keine Kopie seines Codes“.

## Bestandsaufnahme: Yoast-Premium-Funktion → Status hier

| Yoast-Funktion (Premium) | Status im Repo | Wo |
|---|---|---|
| Meta-Titel/Description-Regeln, SERP-Längen | **vorhanden** | `scripts/metadaten_wache.py` (M1–M3), `scripts/meta_optimizer.py`, `scripts/seo_cockpit.py` |
| Canonical, Robots, Index-Hygiene | **vorhanden** | `layouts/_partials/head.html`, `scripts/schema_seo_gate.py`, `scripts/index_hygiene_gate.py` |
| Schema/JSON-LD (Article, FAQ, HowTo) | **vorhanden, geprüft** | `layouts/_partials/schema_article.html`, `scripts/schema_seo_gate.py` (prüft Werte, nicht nur Vorhandensein) |
| OpenGraph/Twitter-Cards | **vorhanden** | `layouts/_partials/templates/opengraph.html` |
| Breadcrumbs | **vorhanden** | `layouts/_partials/breadcrumbs.html` |
| XML-Sitemap | **vorhanden** (Hugo-nativ) | `hugo.toml` |
| Weiterleitungen / Redirect-Manager | **Logik vorhanden, keine Oberfläche** | `scripts/weiterleitungen.py`, `data/weiterleitungen.yaml` |
| Interne Linkvorschläge | **umgesetzt 28.10.2026** (Automatik + Vorschlagsliste) | `scripts/link_vorschlaege.py` neben `internal_linker.py` |
| Lesbarkeits-Analyse | **vorhanden, strenger als Yoast** | `scripts/lesbarkeit_heiler.py`, Flesch-Gate im Publish-Pfad |
| Content-Analyse / SEO-Score | **vorhanden, aber ehrlicher** | `scripts/seo_audit.py`, Cockpit mit P1/P2/P3 statt Punktzahl |
| Mehrere Fokus-Keywords pro Beitrag | **umgesetzt 28.10.2026** | `scripts/fokus_keywords.py` |
| Cornerstone-Inhalte markieren | **umgesetzt 28.10.2026** | `scripts/cornerstone_wache.py` |
| „Workouts“ (geführte Content-Aufgaben) | **fehlt** | – |
| Social-Vorschau vor Veröffentlichung | **umgesetzt 28.10.2026** | `scripts/social_vorschau.py` + `tools/social-vorschau/` |
| Orphan-Content-Erkennung | **vorhanden** | `scripts/seo_cockpit.py` (Befund `orphan-page`, P2) |
| KI-Textvorschläge (Yoast AI) | **teilweise** | `scripts/jasper_seo.py`, Redaktions-Pipeline in `scripts/` |
| 24/7-Support | nicht nachbaubar – und hier auch nicht nötig | – |

Von den gut einem Dutzend Premium-Funktionen waren **rund zwei Drittel bereits
vorhanden**, teils strenger geprüft als im Original (Schema-Werte,
Flesch-Schwelle, Linkdichte). Die vier verbleibenden redaktionellen Lücken
sind seit dem 28.10.2026 geschlossen – Spezifikation und Umsetzung unten.

## Die vier echten Lücken: Spezifikation (umgesetzt am 28.10.2026)

Alle vier sind eigenständige Module ohne neue Abhängigkeiten
(Python-Standardbibliothek + Hugo-Templates, passend zu den Repo-Regeln in
`CLAUDE.md`). Die Aufwands- und Nutzenschätzung stammt aus der Planung und
steht hier als Nachweis, was daraus geworden ist:

1. **Mehrere Fokus-Keywords** – Frontmatter-Feld `keywords_fokus: []`,
   Abgleich gegen Titel/Description/H1/H2, Bericht im Cockpit.
   Aufwand: klein, Nutzen: mittel.
2. **Cornerstone-Markierung** – `cornerstone: true`, eigene Gate-Regel
   (mind. X interne Links hinein, `lastmod` frisch), Sichtbarkeit im Cockpit.
   Aufwand: klein, Nutzen: hoch bei 200+ Artikeln.
3. **Social-Vorschau** – lokale HTML-Seite, die OG-Tags je URL als
   Karten-Vorschau rendert (Facebook/LinkedIn/X/WhatsApp-Maße).
   Aufwand: klein, Nutzen: mittel.
4. **Interne Linkvorschläge als Vorschlagsliste** – `internal_linker.py`
   um einen Dry-Run-Modus erweitern, der Vorschläge als CSV/Markdown
   ausgibt statt direkt zu schreiben. Aufwand: klein, Nutzen: hoch.

## Umgesetzt am 28.10.2026

Alle vier Lücken sind gebaut – als eigenständige Module, ohne neue
Abhängigkeiten, ohne fremden Code. Bedienung: `docs/ANLEITUNG-SEO-PARITAET.md`.

| Modul | Was es leistet | Messwert am Bestand |
|---|---|---|
| `scripts/link_vorschlaege.py` | Linkvorschläge mit Bewertungsgründen, schreibt nichts | 87 Vorschläge für 36 Artikel in 1,5 s |
| `scripts/cornerstone_wache.py` | `cornerstone: true` prüfen (C1–C6) + Kandidaten mit paste-fertiger Zeile | 10 Kandidaten, Top: 24 eingehende Links |
| `scripts/fokus_keywords.py` | `keywords_fokus` (F1–F9) inkl. Kannibalisierung | 76 Seiten geprüft, 76 Empfehlungen (F9), 0 Gates |
| `scripts/social_vorschau.py` | Kartenvorschau für 6 Kanäle, Bildmaße aus dem Dateikopf | 76 Seiten, 0 ohne Bild, 192 Hinweise (P3) |

Bewusste Entscheidungen dabei:

- **Eine Zählung.** Der Linkgraph (eingehende Links, Selbstverweise,
  drei Linkformen) lebt in `cornerstone_wache.py` und wird von den
  Linkvorschlägen und vom SEO-Cockpit importiert. Zwei Zähler hätten einen
  Vorschlag für ein Ziel erzeugt, das die Wache gleichzeitig als verwaist
  meldet.
- **Eine Grenzwertquelle.** Kanalgrenzen und Bildmaße stehen in
  `social_limits.py` – nicht im JavaScript. Eine Zahl im Frontend ist eine
  Zahl, die niemand prüft.
- **Die Wachen markieren nichts.** Cornerstone-Kandidaten und
  Fokus-Keyword-Vorschläge sind Vorschläge mit Einfüge-Zeile; die
  Entscheidung bleibt redaktionell.
- **Keine erfundenen Messwerte.** Bildmaße kommen aus dem Dateikopf
  (PNG/JPEG/GIF/WebP), unbekannte Formate melden „nicht messbar". Fehlt
  PyYAML, verweigern die Wachen den Dienst, statt grün zu melden.

Was diese Module nicht liefern (und nicht liefern können): Rankingdaten,
Suchvolumen, Wettbewerbervergleiche. Dafür fehlt eine Datenquelle, kein
Feature.

## Empfehlung

Kein Nachbau, kein Fremdcode. Reihenfolge nach Nutzen: **Punkt 4 → 2 → 1 → 3**.
Punkt 4 und 2 zusammen decken den größten Teil dessen ab, wofür Blogger
tatsächlich zu Yoast Premium greifen (Linkstruktur und Priorisierung).
