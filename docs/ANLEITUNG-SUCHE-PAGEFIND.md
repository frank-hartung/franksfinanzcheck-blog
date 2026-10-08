# Anleitung: Site-Suche (Pagefind)

Stand: 08.10.2026 · Gilt für: `content/suche/`, `layouts/shortcodes/suche.html`,
`static/premium/ff-suche.js`, `assets/css/extended/ff-suche.css`,
Schritt „Suchindex bauen (Pagefind)“ in `.github/workflows/deploy.yml`.

## Was die Suche tut

Eine statische Volltextsuche über alle Inhaltsseiten. Sie läuft im Browser:
kein Suchdienst, kein Konto, kein Cookie, kein Analytics-Ereignis mit dem
Suchbegriff. Pagefind ist MIT-lizenziert und wird lokal ausgeliefert (keine CDN-Assets).

- Suchseite: `/suche/` (noindex, nicht in der Sitemap)
- Einstieg: Link „Suche“ im Footer jeder Seite (nicht im Menü)
- Index: `/pagefind/` – entsteht erst beim Deploy aus dem fertigen `public/`-Stand

## Was indexiert wird – und was nicht

| Bereich | Im Index? | Grund |
|---|---|---|
| Artikel, Ratgeber, Werkzeuge, Startseite, Blog-Liste (Seite 1), Säulen | ja | nur `<main data-pagefind-body>` wird gelesen |
| Navigation, Footer, Header | nein | liegen außerhalb von `<main>` |
| `/suche/` | nein | `data-pagefind-ignore="all"` auf dem `<body>` |
| 404-Seite, Newsletter-Abmeldung, -Bestätigung, -Präferenzen, Newsletter-Hauptseite | nein | `noindex` (siehe unten) |
| Blätterseiten ab Seite 2 (`/page/2/`, `/posts/page/2/` …) | nein | nur Listen-Ausschnitte, würden bei jedem Begriff treffen |
| Weiterleitungen `/go/…`, `/kalender/`, Pinterest-OAuth | nein | kein `<main>` mit `data-pagefind-body` |

**Regel für `noindex`:** Pagefind ignoriert das Robots-Meta. Deshalb entscheidet
`layouts/baseof.html` über `partial "seo_indexierbar.html"` – dieselbe Quelle wie
robots-Meta und Sitemap. Was Suchmaschinen nicht indexieren dürfen, steht auch nicht
in der Suche. Der Ausschluss ist per `data-pagefind-ignore` am `<body>` umgesetzt. Die Taxonomie-Archive sind derzeit abgeschaltet (`hugo.toml`, `[taxonomies]`); würden sie wieder gebaut, griffe dieselbe Regel.

## Version

Pagefind ist in `package.json` exakt gepinnt (`"pagefind": "1.5.2"`, ohne `^`),
der Lockfile zieht dieselbe Version. Ein Upgrade geht nur so:

1. `npm install --package-lock-only --save-exact pagefind@<neu>`
2. `npm run suchindex` gegen einen Hugo-Build laufen lassen
3. `npm run test:suche` und die Trefferprobe unten wiederholen
4. Erst dann committen.

## Lokal prüfen

```bash
npm ci                                   # einmalig; installiert pagefind
hugo --minify --destination public
npm run suchindex                        # erwartet: „Indexed 69 pages“ (Stand 08.10.2026, 83 Seiten mit Marker minus 14 ausgeschlossene)
npm run test:suche                       # JS-Vertrag (jsdom) + Python-Vertrag
```

Trefferprobe: `public/` mit einem statischen Server ausliefern und `/suche/`
öffnen. Erwartet: „Tagesgeld“ liefert Artikel und Ratgeber, keine
`/go/`-Weiterleitungen; „Impressum“ findet die Impressumsseite; `/suche/`
erscheint nie als Treffer.

## Deploy-Verhalten

Der Schritt läuft nach dem letzten Hugo-Build und vor dem gh-pages-Deploy.
Er ist **fail-closed**: fehlt `public/pagefind/pagefind.js`, stoppt der Deploy.
Eine Suche ohne Inhalt soll nicht live gehen.

Rot geworden? Zuerst `npm ci` in den Logs prüfen (Registry erreichbar?), dann
lokal `npm run suchindex` nach einem Hugo-Build. Die Ursache ist fast immer
der Registry-Zugriff, nicht der Index.

## Datenschutz-Hinweis

- Die Eingabe wird nicht an einen Server geschickt und nicht in der URL gespeichert
  (das Formular fängt das Absenden im Skript ab; es gibt kein GET-Formular).
- Die Index-Dateien werden wie alle Seitenbestandteile vom Hoster (GitHub Pages)
  ausgeliefert; Dateiabrufe erscheinen dort wie bei jeder Seite in den Zugriffslogs.
  Wer das ausschließen will, müsste die Suche abschalten.
- Technisch sendet die Suche nichts an Dritte. Die Indexdateien kommen vom selben Hoster
  wie alle Seiten. Ob die Datenschutzerklärung dafür einen Satz braucht, ist zu prüfen.
  Das ist keine Rechtsberatung.

## Abschalten

Footer-Link in `layouts/_partials/footer.html` entfernen, Ordner `content/suche/`
löschen, Deploy-Schritt „Suchindex bauen (Pagefind)“ streichen, Tests anpassen
(`tools/ff-suche.test.mjs`, `scripts/tests/test_suche_pagefind.py`).
