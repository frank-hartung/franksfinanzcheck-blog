# Barrierefreiheit #623/#630 – Stufe 2: verifiziert und nachgehärtet

**Datum:** 08.10.2026
**Auftrag:** Die Dauerheilung aus **#623/#630** (`6a567c2`, Follow-up-Härtung
`e5ebb63` = #639) vollständig verifizieren, jeden offenen Rand schließen und
das Ergebnis mit einem Pull Request belegen – nicht „formal erledigt“,
sondern nachgemessen.
**Ergebnis:** Drei Ränder waren offen; **einer davon deckte einen echten
Live-Befund**. Alle drei sind geheilt, alles ist mit dem echten Hugo-Build,
dem vollständigen A11y-Audit und der kompletten Browser-Suite belegt.

## Der Befund, der zählte: die Ausnahme deckte vier Seiten ohne H1

`scripts/h1_wache.py` nahm Blätterseiten pauschal aus
(`page/N/index.html` → „Blätter-Redirect ohne Inhalt“). Diese Begründung
stammte aus der Zeit, in der `[pagination] aliases` Hugo für jede Blätterseite
eine Redirect-Seite schreiben ließ. Seit dem 29.09.2026 gilt
`[pagination] disableAliases = true` (bewacht von `index_hygiene_gate.py`, H2) –
**es gibt diese Redirects nicht mehr**. `/page/2/` … `/page/5/` und
`/posts/page/2/` … `/posts/page/5/` sind echte, verlinkte Seiten geworden.

Der geroutengenaue Beweislauf (`/tmp/h1_beweis.py`, 40 veröffentlichte
Beiträge, `pagerSize = 8` → 5 Blätterseiten je Liste) machte es sichtbar:

| Lauf | Zustand | Ergebnis |
|---|---|---|
| **A** | alter Zustand **+** alte Pauschalausnahme | grün – die Ausnahme verdeckte den Befund |
| **B** | alter Zustand **+** scharfe Registry | **4 Befunde**: `page/2` … `page/5` „trägt GAR KEINE H1“ |
| **C** | geheilt **+** scharfe Registry | grün |

Eine Ausnahme, die einen Befund deckt, ist ein Versteck. Sie ist entfernt;
die Startseiten-Blätter tragen ihre H1 jetzt wie die Beitragsblätter.

## Die beiden stillen Ränder

**1. Die Quellprüfung kannte nur eine von drei Markdown-Wahrheiten.**
S1 suchte `# …` am Zeilenanfang. Was Goldmark sonst noch als `<h1>` rendert,
war ein blinder Kanal:

| Form | vorher | jetzt |
|---|---|---|
| ATX `# Titel` (Spalte 0) | erkannt | erkannt |
| ATX mit bis zu drei führenden Leerzeichen (`   # Titel`) | **übersehen** | erkannt |
| Setext (`Titel` + `=====`) | **übersehen** | erkannt |
| rohes `<h1 …>` im Markdown (`unsafe = true` in `hugo.toml`) | **übersehen** | erkannt (`markdown_roh_html_h1`) |

Code-Zäune, eingerückter Code (4 Leerzeichen) und Inline-Code-Spans bleiben
ausdrücklich Text – dort ist die Raute keine Überschrift.

**2. Geprüft wurden vier Dateien statt des Inventars – und `heading:` galt
nicht überall.** S2 kannte nur den gemeinsamen Baustein, die beiden
Einzel-Wrapper, `layouts/_default/list.html` und den 404. Eine **neue**
H1-Quelle irgendwo im Layout-Baum wäre unbemerkt geblieben – genau die
Klasse Fehler, aus der #623 entstand. Zusätzlich ignorierten
`layouts/pillar/single.html` und `layouts/werkzeuge/single.html` das
`heading:`-Frontmatter: Eine Redakteurin hätte dort eine Schirmzeile
gesetzt und die Abschnittsliste hätte etwas anderes gezeigt als die
Einzelansicht. Jetzt gilt:

- **`H1_QUELLEN`** ist das vollständige, begründete Inventar aller Dateien,
  die im Layout-Baum ein `<h1>` rendern dürfen (9 Dateien, 10 H1-Stellen).
- **`SEITENARTEN`** hält die Seitenarten dagegen – beide Sichten müssen
  zusammenpassen; eine unregistrierte H1-Quelle **oder** eine Seitenart
  ohne Quelle ist ein Befund (**fail-closed**).
- **`PARITAET_TEMPLATES`** erzwingt, dass Einzelansichten mit eigener
  Vorlage (`pillar/`, `werkzeuge/`) `heading:` genauso ehren wie der
  gemeinsame Baustein.
- **`H1-BLÄTTERKOPF`**: Der Startseiten-Blätterkopf ist an einen Marker in
  `layouts/_default/list.html` gebunden; fehlt er, meldet die Wache.

**3. Die letzte Instanz war unvollständig verdrahtet.** Die Blätterseiten
standen in keinem Browser-Test, und der **Pull Request** maß die gebaute
Wahrheit gar nicht – die Wache lief nur im Deploy. Beides ist geschlossen:
`e2e/seo-a11y.spec.mjs` prüft jetzt auch `/page/2/` und `/posts/page/2/`,
und `e2e.yml` fährt direkt nach dem Hugo-Build
`python3 scripts/h1_wache.py --public public`.

## Nachweis (alle Zahlen am 08.10.2026 gemessen, mit echtem Build)

Der Hugo-Build war in der Arbeitsumgebung bisher nicht möglich (Release-Assets
nicht erreichbar). Gelöst über die **zweite Quelle der repo-eigenen
`install-hugo`-Action**: das PyPI-Paket `hugo`
(`hugo-python-distributions`, „extended + withdeploy“), Wheel
`hugo-0.164.0-…manylinux_2_24_x86_64….whl`. Damit lief exakt die
CI-Version:

| Prüfung | Ergebnis |
|---|---|
| `hugo --minify --cleanDestinationDir --destination public` | **Exit 0** – Hugo v0.164.0 `+extended+withdeploy`: 80 Seiten, 8 Paginator-Seiten, 1491 Static-Dateien, **0 Aliase**, 1,7 s |
| `python3 scripts/h1_wache.py --source-only` | **grün** (content/ + archetypes/) |
| `python3 scripts/h1_wache.py --public public` | **grün** – 105 geprüfte HTML-Dateien, 4 begründete Ausnahmen |
| Unabhängige Gegenprobe (fremder HTML-Parser über alle 109 Dateien) | **106× genau eine H1 · 0× mehr als eine H1 · 3 ohne H1** – und zwar exakt die drei Verifikationsdateien von Google/Pinterest |
| Blätterseiten im gebauten HTML | `/page/2/` … `/page/5/` und `/posts/page/2/` … `/posts/page/5/` je **genau eine H1** „Weitere Ratgeber“; `/page/1/` **existiert nicht** (`disableAliases`) |
| Die drei #623-Seiten | `/presse/`, `/studien/`, `/studien/fixkosten-index-2026-q4/` je **genau eine gefüllte H1** (Texte wie am 07.10. geheilt) |
| `python3 scripts/a11y_audit.py` | **85 Seiten vollständig geprüft, 0 Probleme, 0 Kontrast-Fehler** (vorher 75 – die 8 Blätterseiten sind keine Ausnahme mehr) |
| `python3 scripts/h1_wache.py --selftest` | **31 Sabotageproben grün** (S1-Formen, Inventar, Seitenarten, Parität, Blätterkopf, fail-closed) |
| `python3 -m unittest scripts.tests.test_h1_wache scripts.tests.test_a11y_audit` | **Ran 46 tests, OK** |
| `python3 scripts/governance_contract.py` | **„alle 30 Regeln prüfen in beide Richtungen“** |
| `python3 scripts/governance_contract.py --selftest` | **✅ C1–C32** mit Kunstbefunden |
| C30-Sabotagebeweise (neu) | **6/6**: Setext, rohes `<h1>`, Inventar, Blätterkopf, zurückgekehrte `page/N`-Ausnahme, aus `e2e.yml` entfernte Build-Prüfung – jede Sabotage trifft genau ihren Zweig |
| C30-Wirkprobe am echten Baum | `h1_wache.py` real sabotiert → `--selftest` **Exit 2** mit C30-Befund, danach byte-identisch wiederhergestellt und wieder grün |
| `npx playwright test` (komplette Suite, Desktop + iPhone 14) | **108/108 grün** in 4,3 min – mit dem von der Suite selbst vorgesehenen Fallback-Chromium (`@sparticuz/chromium`) |
| `npx playwright test e2e/seo-a11y.spec.mjs` | **5/5 grün**, darunter die neuen Fälle `/page/2/` und `/posts/page/2/` |
| Suchindex (E2E-Global-Setup) | 109 HTML → 70 indexierbar, 70 im Index, 39 bewusst ausgeschlossen ✅ |
| Nachbar-Gates über denselben Build | `index_hygiene_gate`, `fixkosten_kompass_guard` (Quelle+Build), `werkzeuge_gate` (Quelle+Build), `robustheits_gate` (Quelle+Build, `--strict`) – **alle grün** |

**Der C30-Vertrag wächst mit der Heilung mit.** Er prüft jetzt zusätzlich die
Markdown-Wahrheit (`SETEXT_UNTERSTRICH`, `markdown_roh_html_h1`), das
Inventar (`H1_QUELLEN`, `SEITENARTEN`), den Blätterkopf-Marker
(`H1_BLAETTERKOPF`), dass die Ausnahmen-Registry **keine** Blätterseite mehr
decken darf, die Parität der Einzel-Templates (`heading:`), die
Build-Prüfung im Pull Request (`e2e.yml`) und – als Verhaltensprobe, weil
Textsuche hier unzuverlässig wäre – dass `ausnahme_grund('page/2/…')` leer
ist, während die begründeten Ausnahmen (Google-/Pinterest-Verifikation,
Pinterest-Client-Redirect) weiter greifen.

## Was bewusst nicht getan wurde

- **Keine Prüfung abgesenkt.** Kein Schwellenwert gesenkt, keine Ausnahme
  ohne Begründung, kein `continue-on-error`. Die drei
  Google-/Pinterest-Verifikationsdateien bleiben ausgenommen – sie sind
  keine Seiten, ihre Inhalte verlangt der jeweilige Anbieter exakt; die
  Begründung steht im Register und wird geprüft.
- **Keine automatische Heilung.** `--fix` bleibt vertraglich ausgeschlossen
  (C30): Eine H1 automatisch zu löschen vernichtet einen redaktionellen
  Satz.
- **Kein Inhalt angetastet.** Geändert wurden Layout, Wachen, Tests,
  Vertrag und Doku – kein Artikeltext, kein Titel, keine Beschreibung.
- **Der `page/N/`-Hinweis bleibt im Befund.** Wird die
  `disableAliases = true`-Zeile in `hugo.toml` je entfernt, nennt die Wache
  beim Befund auf `page/1/` den Grund und die zuständige Config-Wache –
  statt eine neue Pauschalausnahme zu erfinden.

## Siegel und Doku

`layouts/pillar/single.html` steht unter dem Integritäts-Siegel (Klasse
FEST). Die Änderung wurde im selben Pull Request neu signiert – der Weg, den
das Gate selbst nennt: `python3 scripts/integrity_guard.py --set-current`,
Herkunft in `data/integrity_lock.json`, Lock und Änderung im selben PR.

Nachgezogen: `docs/GOVERNANCE-KONTRAKT.md` (C30 neu gerendert),
`docs/ENTWICKLER-WERKZEUGE.md` (Abschnitt „Was seit Stufe 2 geprüft wird“),
`CLAUDE.md` (Regressionstests 33 → 46).

## Geänderte Dateien

| Datei | Änderung |
|---|---|
| `scripts/h1_wache.py` | S1: ATX 0–3 Lz., Setext, rohes `<h1>`; Ausnahmen ohne `page/N`; S2: `H1_QUELLEN`/`SEITENARTEN`/`PARITAET_TEMPLATES`/Blätterkopf-Marker; Texte |
| `layouts/_default/list.html` | Blätterkopf-Zweig für die Startseite ab Seite 2 (`H1-BLÄTTERKOPF`) |
| `layouts/pillar/single.html`, `layouts/werkzeuge/single.html` | H1 ehrt `heading:` (Parität zum Baustein) |
| `scripts/a11y_audit.py` | Docstring/Scan-Set: Blätterseiten sind keine Ausnahme |
| `scripts/tests/test_h1_wache.py`, `scripts/tests/test_a11y_audit.py` | 46 Tests (S1-Formen, Inventar↔Baum, Seitenarten, Parität, Blätterkopf, Blätterseiten) |
| `scripts/governance_contract.py` | C30 Stufe 2 + sechs neue Sabotageproben + Langtext/Kurzname |
| `.github/workflows/e2e.yml` | Schritt „H1-Wache – gebaute Seiten“ direkt nach dem Build |
| `e2e/seo-a11y.spec.mjs` | `/page/2/` und `/posts/page/2/` im „genau eine H1“-Loop |
| `docs/GOVERNANCE-KONTRAKT.md`, `docs/ENTWICKLER-WERKZEUGE.md`, `CLAUDE.md` | Doku nachgezogen |
| `data/integrity_lock.json` | Neusignatur (Herkunft in der Akte) |

_Der Beweislauf A/B/C liegt als Wegwerf-Skript in `/tmp/h1_beweis.py`; seine
Kernzahl ist oben festgehalten, damit er nicht mit dem Container verschwindet._
