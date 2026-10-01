# Sitemap-Ableitung statt Handpflege – Premium-Reparatur (Vorgang WF-54C4, Issue #508)

**Stand:** 01.10.2026 · **Bereich:** Veröffentlichung / Index-Hygiene
**Symptom:** „Deploy auf GitHub Pages“ rot, Schritt *Index-Hygiene-Gate
(Crawl-Fläche gegen Budget)*, Commit `f6bef8d6`, zwei Läufe hintereinander.

## Befund (reproduziert, nicht vermutet)

Build und Wache lokal auf dem roten Commit nachgestellt
(`hugo --minify` + `python3 scripts/index_hygiene_gate.py`):

```
  HARTE FUNDE (1):
    [H1] /cockpit/: indexierbare Seite fehlt in der Sitemap
```

Die Seite `/cockpit/` (Produktkern „Fixkosten-Cockpit“) trug korrekt
`index, follow` – stand aber in keiner Sitemap. Die Wache stoppt den Deploy
genau dafür, zu Recht: Eine indexierbare Money-Page, die Google nur über
interne Links findet, landet im Status „Gefunden – zurzeit nicht indexiert“.

## Ursache (die eigentliche, nicht die oberflächliche)

`layouts/sitemap.xml` **zählte seinen Bestand auf**, statt ihn abzuleiten:
eine feste Liste aus sechs Pillar-Slugs, zwei Hub-Sektionen und den
Rechts-/Vertrauensseiten. Jede neue Seite war damit per Konstruktion
unsichtbar für die Sitemap, bis jemand ihren Namen ins Template nachtrug.

Dasselbe Muster schlug vorher schon zu – immer mit demselben Fund H1:

| Datum | Seite | Reaktion |
|---|---|---|
| 29.09.2026 | `/transparenz/` | Name nachgetragen |
| 01.10.2026 | `/aenderungsprotokoll/` | Name nachgetragen |
| 01.10.2026 | `/cockpit/` | **Deploy gestoppt**, Name nachgetragen |

Dreimal derselbe Defekt, dreimal dieselbe Handpflege: Das ist kein Einzelfall,
sondern ein Konstruktionsfehler. Dazu kam eine zweite Schwäche: Über die Frage
„darf diese Seite in den Index?“ entschieden **zwei** Stellen mit je eigenen
Regeln – `head.html` (robots-Meta) und `sitemap.xml` (Namensliste). Driften
sie auseinander, entstehen exakt die Funde H1 (indexierbar, nicht in der
Sitemap) und H8 (noindex, aber in der Sitemap).

## Reparatur (strukturell, dauerhaft)

1. **`layouts/_partials/sitemap_kandidaten.html` (neu)** – läuft den
   `content`-Baum rekursiv ab und liefert jeden Seitenpfad. Bewusst über das
   Dateisystem statt über `site.RegularPages`: Die sechs Pillar-Ratgeber tragen
   `build.list: never` und fehlen in allen Hugo-Page-Collections.
2. **`layouts/_partials/seo_indexierbar.html` (neu)** – **eine** Quelle für die
   Index-Entscheidung (Produktion, `robotsNoIndex`, 404, Archiv, Pager).
   `head.html` **und** `sitemap.xml` fragen ab sofort dieselbe Partial.
3. **`layouts/sitemap.xml` (neu gefasst)** – nimmt jede indexierbare Seite ohne
   `sitemap.disable` auf, gruppiert nach Seitentyp (Start / Artikel / Pillar /
   Sektion / Seite) für `priority` und `changefreq`, Bild-Sitemap unverändert
   nach `priority`. **Kein einziger Seitenname mehr im Template.**
   Feinsteuerung liegt bei der Seite selbst (`sitemap.priority`,
   `sitemap.changefreq` im Frontmatter – so hält `/cockpit/` seine 0.6).
4. **`scripts/tests/test_sitemap_ableitung.py` (neu)** – hält den Zustand fest:
   schlägt an, sobald wieder Seitennamen ins Sitemap-Template wandern, die
   Ableitung entfernt wird oder `head.html` die Indexierbarkeit wieder
   eigenständig entscheidet. Läuft in `publication-reliability-tests.yml` mit.

## Beweis

| Prüfung | Ergebnis |
|---|---|
| Sitemap-URL-Menge vorher/nachher | **identisch**, 60 URLs, kein Diff |
| `index_hygiene_gate.py` | ✓ grün, 0 harte Funde (Selbsttest 12/12) |
| `schema_seo_gate.py` | ✅ 101 Seiten, 0 harte Funde, 0 Hinweise |
| `seo_cockpit.py` / `publish_gate.py` | grün |
| robots-Meta im Build | unverändert: 60 × index, 10 × noindex/follow, 5 × noindex/nofollow |
| **Regressionstest neue Seite** | Testseite angelegt → **automatisch in der Sitemap**, H1 bleibt stumm (nur weicher H7-Hinweis „noch nicht verlinkt“) |
| `test_integrity_guard` | grün (Siegel für `head.html` im selben Commit neu gezeichnet) |

## Was ab jetzt gilt

Eine neue Seite braucht **keinen** Eingriff am Sitemap-Template mehr. Sie ist
in der Sitemap, sobald sie indexierbar ist – und draußen, sobald sie
`robotsNoIndex` oder `sitemap.disable` trägt. Der Deploy kann an dieser Stelle
nicht mehr durch Wachstum brechen.
