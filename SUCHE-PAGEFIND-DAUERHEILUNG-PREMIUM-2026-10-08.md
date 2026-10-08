# Suche (Pagefind) und Redaktionsressourcen – Dauerheilung #644

**Datum:** 08.10.2026 · **Branch:** `arena/1bb97ec8-franksfinanzcheck-blog` (Basis: `main` = `dcc3138`)
**Bezug:** #644 (gemergt). Dessen Umsetzung steht auf `main` über #647 und hatte mehrere Brüche.
Kein „Closes“: #644 ist bereits geschlossen; der Vorgang wird über diesen Bericht nachvollziehbar.

## Befund auf `main` (gemessen, nicht vermutet)

1. **Build und Deploy standen.** `package.json` war kein gültiges JSON (Parsefehler Zeile 181:
   fehlendes Komma im Block `dependencies`). Dazu kamen ein doppelter Schlüssel `build` und
   `pagefind` zweimal (`1.5.2` und `^1.5.2`). `npm ci` brach mit `EJSONPARSE` ab. Damit scheiterten
   der Deploy-Schritt „Suchindex bauen“ und alle Workflows mit `npm ci`.
2. **Unit-Tests:** 2285 Tests mit 15 Fehlschlägen (5 Failures, 10 Errors). Alle 15 gehen auf das kaputte
   `package.json` bzw. fehlende npm-Skripte zurück (Fehlermeldungen geprüft). Dazu die Alarme #650
   (`ki_transportweg` T8, `werkbank` B8).
3. **Sichtbarer Text auf der Suchseite:** Ein Front-Matter-Rest aus #644 stand als Fließtext auf
   `/suche/` (`title: „Ratgeber durchsuchen“ … draft: false`).
4. **Zwei Suchoberflächen:** Reste von #644 (`layouts/search/single.html` mit pagefind-ui und
   `zz-pagefind.css`, das auf jeder Seite inline ausgeliefert wurde) lagen neben #647 (`ff-suche`).
5. **Suchfeld unter dem Falz:** Das Titelbild der Suchseite schob das Suchfeld aus dem ersten
   Bildschirm (Screenshot 1280 × 900).
6. **Toter Link:** Der Ohne-JavaScript-Hinweis verlinkte `/blog/`. Die Seite gibt es nicht; der
   Blog liegt unter `/posts/`. Das Layout-Gate (`scripts/layout_audit.py`) meldete es, Exit 1.
7. **Pagefind-Verhalten:**
   - Unbekannte Begriffe lieferten Treffer: „Zyklotronbeschleuniger“ → 19, „xqzv“ → 2. Die
     markierten Stellen waren Teilstücke wie „(z.“ und „x“.
   - Anker-Zeichen „#“ standen in Auszügen („in der Praxis#“).
   - Im Ausgabeordner blieben alte Fragmente liegen: 138 Dateien für 70 Seiten.
8. **Index-Prüfung zu schwach:** `test -s` ließ einen leeren Index durch. Das Runbook nannte
   „69 Seiten“; gemessen sind 70.
9. **Widersprüche:** Runbook und Footer-Kommentar sagten „nicht im Menü“, `hugo.toml` enthielt
   den Menüpunkt aus #644.
10. **Browser-Test fehlte.** #647 nennt die echte Browser-Prüfung selbst als nicht ausgeführt.
    CLAUDE.md verlangt sie („Browser-Pflicht“, #507).
11. **Editorial-Ressourcen verwaist:** Die Standards für Alt-Texte und GEO wurden von keiner
    Anleitung verlinkt; der GEO-Dateiname war uneinheitlich geschrieben.

## Maßnahmen

- **`package.json`:** gültig, ohne Doppelschlüssel. `pagefind` ist die einzige Abhängigkeit,
  exakt `1.5.2`, unter `dependencies` (Deploy mit `--omit=dev`). Dublette `lighthouse` entfernt.
  `build` ruft `suchindex` auf. `suchindex` = `rm -rf public/pagefind` → `pagefind --force-language de
  --exclude-selectors 'a.anchor'` → Wache. Neu: `suchindex:pruefen`, `test:suche:browser`.
- **`package-lock.json`:** aus `package.json` regeneriert. Diff: 1 Einfügung, 10 Löschungen
  (`dev`-Flags von pagefind und den Plattform-Paketen).
- **`content/suche/index.md`:** Front-Matter-Rest entfernt, Titelbild entfernt, Satz über den
  Index präzisiert.
- **Entfernt:** `layouts/search/single.html`, `assets/css/extended/zz-pagefind.css`.
- **`static/premium/ff-suche.js`:** Trefferregel. Ein Treffer zählt nur, wenn eine markierte
  Fundstelle oder der Titel die ersten fünf Buchstaben eines Suchworts enthält (Umlaute und ß
  neutral). Flexion bleibt treffbar. Alle Kandidaten werden geladen, damit die Zählzeile stimmt.
- **`layouts/shortcodes/suche.html`:** `/blog/` → `/posts/`.
- **Neue Index-Wache `scripts/suchindex_check.py`** (nur Standardbibliothek). Sie vergleicht
  den Index mit den gebauten Seiten nach derselben Regel wie `baseof.html`: Body-Marker da,
  kein `ignore="all"`, kein `noindex`. Außerdem prüft sie, dass die Zahl der Fragmentdateien
  `page_count` entspricht und das Pagefind-Format noch stimmt. Fail-closed (Exit 1 bzw. 2).
  Selbsttest mit 14 Proben.
- **`e2e/suche.spec.mjs`:** 9 Browser-Tests (Index ausgeliefert, Beschriftung, Treffer mit
  internen Links, keine Anfrage an fremde Hosts, Suchbegriff in keinem Speicher, Enter ohne
  `?q=`, Ansagen für Kurzeingabe und Leertreffer, Tastaturfokus, Mobil ohne horizontalen
  Überlauf, Footer-Link, Ohne-JavaScript-Pfad mit Erreichbarkeit der drei Links).
- **Tests:** `scripts/tests/test_suche_pagefind.py` auf 26 Verträge erweitert (JSON-Gültigkeit,
  Doppelschlüssel, Lock-Konsistenz, eine Suchoberfläche, Front-Matter, Titelbild, Ausgabe leeren,
  Anker, Ohne-JS-Links, Wache). `tools/ff-suche.test.mjs` auf 13 Tests erweitert; ein
  Sicherheitstest bekam eine echte Fundstelle im Fixture, sein Prüfgegenstand bleibt gleich.
- **Doku:** `docs/ANLEITUNG-SUCHE-PAGEFIND.md` neu gefasst (Menü und Footer, Trefferregel,
  Wache, Deploy-Verhalten). Querverweise aus den Alt-Text- und GEO-Anleitungen. GEO-Standard
  umbenannt in `docs/GEO-REDAKTIONSPROTOKOLL.md` (`git mv`). Zwei Prüfbefehle in `CLAUDE.md`.
- **Footer-Kommentar** korrigiert: Suche im Footer zusätzlich zum Hauptmenü.

## Nachweise (Sandbox, 08.10.2026)

| Prüfung | Ergebnis |
|---|---|
| `npm ci --ignore-scripts` | rc 0, Lockfile konsistent |
| Deploy-Simulation: `npm ci --omit=dev --ignore-scripts` in frischem Ordner | nur `pagefind@1.5.2` (+ Linux-Binary); Index 70 Seiten; `test -s` OK; Wache OK |
| `npm run build` (Hugo 0.164.0 Extended, Chromium-Fallback wie unten) | Hugo 80 Seiten; Wache: 109 HTML · 70 indexierbar · 70 im Index · 39 bewusst ausgeschlossen |
| Sabotage am echten Build (Artikelseite in einer Kopie auf `noindex`) | Exit 1, nennt die Seite |
| `npm run test:suche` | jsdom 13/13; Wache-Selbsttest 14 Proben; Python 26 Verträge OK |
| `npx playwright test e2e/suche.spec.mjs --project=desktop` | 9/9 (letzter Lauf nach allen Korrekturen) |
| `npx playwright test` (Desktop und Mobil, vor der Korrektur des Ohne-JS-Links) | 107/107 |
| `python3 -m unittest discover -s scripts/tests` | vorher 2285 Tests, 15 Fehlschläge; nachher 2301 Tests OK, 5 übersprungen |
| CodeQL (javascript), Sicherheits-Gate auf dem PR | vor der Korrektur 1 Befund: `js/incomplete-multi-character-sanitization` in `ff-suche.js:54` (Tag-Regex beim Auszug). Behoben: Auszug bleibt Text, nur `<mark>` ist Markup. Erneuter Lauf auf dem PR ausstehend |
| CI-Job „Playwright-Suite“ auf dem PR (E2E baut mit der Hugo-Action, nicht mit `npm run build`) | vor der Korrektur rot: `public/pagefind/pagefind.js fehlt`. Behoben durch `e2e/suchindex.setup.mjs` (globales Setup baut den Index vor dem ersten Test neu). Nachbildung ohne Index: 9/9 |
| `integrity_guard.py --gate` | rc 0, 47 versiegelte Dateien unverändert |
| `fm_boundary_guard.py --check` · `h1_wache.py` · `offenlegung_gate.py` · `index_hygiene_gate.py` | grün |
| `robustheits_gate.py --public public --strict` | rc 0 |
| `ki_transportweg.py` | rc 0 (vorher rc 1 wegen T8) |
| `werkbank_gate.py --selftest` | grün (vorher B8 rot) |
| `layout_audit.py` | rc 0 (vorher rc 1: `/blog/`) |
| Screenshots 1280 px hell und dunkel, 375 px | Suchfeld oberhalb des Falzes; Dunkelmodus greift (`data-theme=dark`, Hintergrund `rgb(29, 30, 32)`) |

**Umgebung:** GitHub-Release-Assets sind in der Sandbox nicht erreichbar. Hugo kam über den
PyPI-Fallback der Repo-Action (`hugo==0.164.0`). Für die Browser-Tests lief Chromium 153
über `@sparticuz/chromium` (`cdn.playwright.dev` nicht erreichbar). `package.json` blieb dabei unverändert.

**Gemessen zur Last:** Der gesamte Pagefind-Ordner ist 1,7 MB, davon 588 KB Fragmente.

## Entscheidungen

- **Suche bleibt im Hauptmenü und im Footer.** Der Menüpunkt aus #644 bleibt; Runbook und
  Footer-Kommentar wurden angepasst. Die Sichtbarkeit im Kopf ist der Grund.
- **Trefferregel statt strikter Suche.** Anführungszeichen würden die Flexion verlieren.
- **Keine Änderung an versiegelten Dateien.** `hugo.toml`, `head.html`, `extend_footer.html`
  und `robots.txt` blieben unberührt. Das Integritäts-Gate bleibt grün.
- **Datenschutzfrage offen.** Ob die Datenschutzerklärung einen Satz zur lokalen Suche braucht,
  ist eine redaktionelle und rechtliche Frage. Sie ist nicht entschieden und keine Rechtsberatung.

## Offene Punkte (nicht in dieser Änderung)

1. **Versiegelte Dateien** (Signatur durch Frank nötig, `integrity_guard.py --set-current`):
   - `layouts/_partials/head.html` (KRITISCH): Der Kommentar nennt noch
     `layouts/search/single.html`, die Datei gibt es nicht mehr. Nur ein Kommentar.
   - `hugo.toml` (KRITISCH): Die Menüpunkte „Suche“ und „Über mich“ haben beide das Gewicht 7.
     Kosmetisch.
2. **Alt-Text-Skript (#647) umgeht den Transportweg:** `scripts/alt_text_vorschlaege.py` ruft
   Gemini direkt auf (`ENDPUNKT`), nicht über `scripts/llm_client.py`. Das verstößt gegen den
   KI-Transportweg in CLAUDE.md. Das Gate T6 erkennt es nicht, weil die Liste `RUFER` das Skript
   nicht führt. Die Umstellung braucht Bildteile im Client und einen Live-Test. Beides war hier
   nicht möglich.
3. **Live-Aufruf Gemini nicht getestet:** `generativelanguage.googleapis.com` ist aus der Sandbox
   nicht erreichbar.
4. **Mehr Treffer:** Angezeigt werden die ersten zehn Treffer, mit Zählzeile. Ein Knopf „Mehr“
   fehlt. Folgearbeit.
5. **Mobil:** Der Menüpunkt „Suche“ liegt im horizontal scrollbaren Menü weit rechts. Erreichbar
   ist er über den Footer. Eine Suchschaltfläche im Kopf wäre eine Designentscheidung.
6. **Keine weiteren Befunde aus den geprüften Gates.** Die Ergebnisse stehen in der Tabelle oben.
