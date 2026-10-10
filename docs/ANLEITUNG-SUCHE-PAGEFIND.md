# Anleitung: Site-Suche (Pagefind)

Stand: 08.10.2026 · Gilt für: `content/suche/index.md`, `layouts/shortcodes/suche.html`,
`static/premium/ff-suche.js`, `assets/css/extended/ff-suche.css`, `scripts/suchindex_check.py`,
Schritt „Suchindex bauen (Pagefind)“ in `.github/workflows/deploy.yml`.

## Was die Suche tut

Eine statische Volltextsuche über alle Inhaltsseiten. Sie läuft im Browser:
kein Suchdienst, kein Konto, kein Cookie, kein Analytics-Ereignis mit dem
Suchbegriff. Die Eingabe steht weder in der URL noch in einem Speicher; das Formular
fängt das Absenden im Skript ab (kein GET-Formular). Pagefind ist MIT-lizenziert und
wird lokal ausgeliefert (keine CDN-Assets).

- Suchseite: `/suche/` (noindex, nicht in der Sitemap, ohne Titelbild – das Suchfeld steht oben)
- Einstieg: Menüpunkt „Suche“ im Hauptmenü und Link „Suche“ im Footer jeder Seite
- Index: `/pagefind/` – entsteht erst beim Deploy aus dem fertigen `public/`-Stand
- Oberfläche: genau eine. Die Maske kommt aus `ff-suche.js`; eine zweite Suchoberfläche
  (pagefind-ui) gibt es bewusst nicht. Der Vertrag `scripts/tests/test_suche_pagefind.py` wacht darüber.

## Was indexiert wird – und was nicht

Pagefind liest nur `<main data-pagefind-body>`. `layouts/baseof.html` setzt
`data-pagefind-ignore="all"` auf den `<body>` aller Seiten, die nicht in den Index dürfen.

| Bereich | Im Index? | Grund |
|---|---|---|
| Artikel, Ratgeber, Werkzeuge, Studien, Startseite, Blog-Liste (Seite 1), Säulen | ja | Inhalt im `<main>` |
| Navigation, Footer, Header | nein | liegen außerhalb von `<main>` |
| `/suche/` | nein | `data-pagefind-ignore="all"` am `<body>` |
| 404-Seite, Newsletter-Seiten (Hauptseite, Bestätigung, Präferenzen, Abmeldung) | nein | `noindex` über `seo_indexierbar.html` |
| Blätterseiten ab Seite 2 (`/page/2/`, `/posts/page/2/` …) | nein | nur Listen-Ausschnitte |
| Hinweis-Dateien ohne `<html>` (z. B. Google-Verifizierung) | nein | kein Inhalt |

**Regel für `noindex`:** Pagefind ignoriert das robots-Meta. Deshalb entscheidet
`layouts/baseof.html` über `partial "seo_indexierbar.html"` – dieselbe Quelle wie
robots-Meta und Sitemap. Die Wache (siehe unten) prüft das am gebauten HTML nach.

**Anker-Links** (`a.anchor`, das „#“ hinter Überschriften) werden beim Indexieren
ausgeschlossen (`--exclude-selectors` in `package.json`). Sonst stünde „Praxis#“ in Auszügen.

## Trefferregel (Anzeige)

Pagefind gleicht bei unbekannten Begriffen auch Teilstücke ab – etwa das Zeichen „z“
aus „z.B.“. Ohne Gegenmaßnahme erschienen dann Treffer für erfundene Wörter.
Deshalb zählt in `ff-suche.js` ein Treffer nur, wenn eine **markierte Fundstelle oder der
Titel** den Anfang eines Suchworts enthält (die ersten fünf Buchstaben, Umlaute und ß
neutral verglichen). Flexion bleibt treffbar („Kündigungsfristen“ für „Kündigungsfrist“).
Die Regel steht in den jsdom-Tests (`tools/ff-suche.test.mjs`) und im Browser-Test
(`e2e/suche.spec.mjs`, „Zyklotronbeschleuniger“ → keine Treffer).

Seitenweise Anzeige: Es werden zuerst die ersten zehn Treffer angezeigt; die Zählzeile
nennt immer die Gesamtzahl. Der Knopf „Mehr Treffer anzeigen“ unter der Liste lädt die
nächsten zehn Treffer nach und verschwindet, sobald alle sichtbar sind. Geprüft in
`tools/ff-suche.test.mjs` (Nachladen, Neustart, kein toter Knopf) und im Browser-Test
(`e2e/suche.spec.mjs`, „Mehr Treffer“).

## Version

Pagefind ist in `package.json` **exakt** gepinnt (`"pagefind": "1.5.2"`, ohne `^`) und steht
als einzige Abhängigkeit unter `dependencies` – der Deploy installiert mit `--omit=dev`.
`package-lock.json` zieht dieselbe Version; `scripts/tests/test_suche_pagefind.py` prüft
beides. Ein Upgrade geht nur so:

1. `npm install --package-lock-only --ignore-scripts --save-exact pagefind@<neu>`
2. `npm run build` (baut Hugo und den Index und prüft ihn mit der Wache)
3. `npm run test:suche` und `npm run test:suche:browser`
4. Erst dann committen. Das Fragment-Format prüft die Wache; ändert es sich, meldet sie
   „Pagefind-Format geändert?“ und der Deploy stoppt (fail-closed).

## Lokal prüfen

```bash
npm ci --ignore-scripts                  # einmalig; installiert pagefind
npm run build                            # Hugo → public/, Suchindex, Wache
npm run suchindex:pruefen                # nur die Wache auf dem vorhandenen public/
npm run test:suche                       # jsdom + Selbsttest der Wache + Python-Verträge
npm run test:suche:browser               # echter Chromium: Treffer, Datenschutz, Tastatur, Mobil
```

Erwartet: `✅ Suchindex korrekt: N HTML-Seiten gebaut · M indexierbar · M im Index · … bewusst
ausgeschlossen.` Die Zahlen wechseln mit dem Inhalt; wichtig ist, dass „indexierbar“ und
„im Index“ gleich sind.

Die Browser-Tests brauchen Chromium. Der Browser ist als `@sparticuz/chromium`
exakt im Root-Manifest und Lockfile gepinnt; `e2e/browser.mjs` verwendet ihn, wenn
kein expliziter `CHROME_PATH`-Browser oder Playwright-Cache vorhanden ist. Nach
`npm ci` prüft `npm run browser:setup` Start und JavaScript-Ausführung. Der Ablauf
benötigt weder `cdn.playwright.dev` noch ein ungepinntes `--no-save`-Paket.

## Deploy-Verhalten

Der Schritt „Suchindex bauen (Pagefind)“ läuft nach dem letzten Hugo-Build und vor dem
gh-pages-Deploy. Er führt aus:

1. `npm ci --omit=dev --ignore-scripts` – installiert pagefind aus dem Lockfile,
2. `npm run --silent suchindex` – leert `public/pagefind/`, baut den Index und prüft ihn
   mit `scripts/suchindex_check.py`,
3. `test -s public/pagefind/pagefind.js` und `pagefind-entry.json`.

**Fail-closed:** Fehlt der Index, weicht er von den indexierbaren Seiten ab oder liegen alte
Fragmente im Ordner, stoppt der Deploy. Eine Suche ohne oder mit falschem Inhalt geht nicht live.

Rot geworden? Zuerst die Ausgabe der Wache lesen: Sie nennt die Seiten, die im Index sind,
aber nicht hinein dürfen (oder umgekehrt). Dann lokal `npm run build` laufen lassen. Ein
kaputter Lockfile-Stand zeigt sich vorher in `npm ci` und in `test_suche_pagefind`.

## Datenschutz-Hinweis

- Die Eingabe wird nicht an einen Server geschickt und nicht in der URL oder im Speicher abgelegt.
- Die Indexdateien kommen vom selben Hoster (GitHub Pages) wie alle Seiten. Dateiabrufe
  erscheinen dort wie bei jeder Seite in den Zugriffslogs.
- Die Datenschutzerklärung beschreibt die Suche unter „Website-Suche (lokale Suche)“
  (`content/datenschutz/index.md`, Abschnitt 2): Begriffe bleiben im Browser, kein
  Suchdienst, keine Suchhistorie, Indexdateien von dieser Website. Die frühere
  Offen-Frage ist damit **entschieden und erledigt** (08.10.2026); der Offen-Hinweis in
  `SUCHE-PAGEFIND-DAUERHEILUNG-PREMIUM-2026-10-08.md` ist als Tagesprotokoll überholt.
  Vertrag: `scripts/tests/test_suche_pagefind.py`, Klasse `DatenschutzVersprechen`.

## Abschalten

Menüpunkt „Suche“ in `hugo.toml` und Footer-Link in `layouts/_partials/footer.html` entfernen,
Ordner `content/suche/` löschen, Deploy-Schritt „Suchindex bauen (Pagefind)“ streichen,
`layouts/shortcodes/suche.html`, `static/premium/ff-suche.js`, `assets/css/extended/ff-suche.css`
und `scripts/suchindex_check.py` entfernen, Tests anpassen (`tools/ff-suche.test.mjs`,
`scripts/tests/test_suche_pagefind.py`, `e2e/suche.spec.mjs`).
