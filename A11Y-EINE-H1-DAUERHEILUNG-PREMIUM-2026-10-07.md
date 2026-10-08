# Barrierefreiheit #623 – Dauerheilung: Eine Seite, eine H1

**Datum:** 07.10.2026
**Auslöser:** Meldung **#623** „♿ A11y-Audit: Barrierefreiheits-Probleme
gefunden“ (wöchentlicher SEO-Workflow, 15:30 UTC):

```
Barrierefreiheits-Audit: 20 Seiten geprüft
…
⚠️ (1) presse/index.html
     • 2 h1 (erwartet: 1)
⚠️ (1) studien/index.html
     • 2 h1 (erwartet: 1)
Ergebnis: 2 Probleme, 0 Kontrast-Fehler
```

Zwei Seiten mit zwei H1. Das ist der sichtbare Teil. Der eigentliche Schaden
lag eine Schicht tiefer – und er betraf **drei** Seiten, nicht zwei.

## Befund

**1. Die Ursache: die H1 stand zweimal da – Titel *und* Fließtext.**
Jedes Layout dieses Blogs setzt die Seiten-H1 aus dem Titel. Die drei
betroffenen Markdown-Dokumente lieferten zusätzlich eine eigene
`# …`-Zeile im Fließtext. Ergebnis: zwei Hauptüberschriften pro Seite. Für
Screenreader, Inhaltsverzeichnisse und KI-Antworten kippt damit die
Gliederung (WCAG 1.3.1 „Info und Beziehungen“, 2.4.6 „Überschriften und
Beschriftungen“) – genau die Leser, die sich nicht beschweren können.

| Seite | H1 aus dem Layout | zweite H1 aus dem Fließtext |
|---|---|---|
| `/presse/` | „Presse & Expertise“ | „Presse, Interviews und fachliche Zusammenarbeit“ |
| `/studien/` | „Daten & Studien“ | „Daten, die man prüfen und zitieren kann“ |
| `/studien/fixkosten-index-2026-q4/` | „Fixkosten-Index Deutschland: Energie-Baseline Q4 2026“ | „Energie kostet im Modell 2.356,60 Euro pro Jahr“ |

**2. Die dritte Seite war unsichtbar – die Stichprobe hat sie verdeckt.**
`scripts/a11y_audit.py` prüfte **20 von 107** gebauten Seiten und sortierte
dabei „wichtige Seiten zuerst“ (`files.sort(...)` + `files[:20]`). Die
Studienseite stand im selben Build und fiel durch das Raster. Ein Audit, das
ein Fünftel sieht, ist kein Audit, sondern ein Würfel: Die Reparatur hätte
die Meldung geschlossen, und beim nächsten wöchentlichen Lauf wäre die
dritte Doppel-H1 als „neuer“ Befund wieder aufgelaufen – mitten in der
Nacht, ohne Zusammenhang.

**3. Dahinter lag ein toter Zweig: die Einzelansicht existierte zweimal.**
Bis zur Dauerheilung lag der Artikel-Baustein in **zwei** Dateien:
`layouts/_default/single.html` und `layouts/single.html`. Beide waren bis
auf zwei Kommentare zeichengleich und wurden von Hand „deckungsgleich“
gepflegt. Der Vermerk im Quelltext lautete:

> 26.09.2026: Block aus `_default/single.html` hierher synchronisiert –
> `layouts/single.html` gewinnt die Template-Auflösung, der aktualisierte
> Zweig lief sonst ins Leere.

**Das Gegenteil ist der Fall.** Ein Baustein-Marker im gebauten HTML
(`data-tpl="…"` in `<article class="post-single">`) bewies es: `/presse/`
und `/ueber/` trugen `data-tpl="DEFAULTSINGLE"`. Hugo löst
`_default/single.html` also **vor** `layouts/single.html` auf. Die Kopie in
`layouts/single.html` war der tote Zweig – und in genau diesem Zweig hätte
eine Heilung der H1-Regel gestanden, wenn man sie dort repariert hätte. Der
Vermerk war überdies falsch: Er behauptete die Auflösung, die er
fürchtete. Behauptungen über die Maschine gehören bewiesen, nicht
geglaubt.

## Dauerhafte Reparatur

1. **Eine H1, ein Besitzer** (`layouts/_partials/artikel_einzeln.html`,
   neu): Der Artikel-Baustein liegt jetzt genau **einmal** im Repository.
   `layouts/_default/single.html` und `layouts/single.html` sind je vier
   Zeilen und binden ihn ein. Damit kann kein Zweig mehr ins Leere laufen,
   weil es keinen zweiten Zweig gibt.
2. **Schirmzeile statt zweiter H1** (`heading:` im Frontmatter): Der
   Baustein rendert `{{ .Params.heading | default .Title | safeHTML }}`,
   die Abschnittsliste `{{ .Params.heading | default .Title | plainify }}`.
   Eine Redaktion, die eine eigene Zeile über dem Artikel will, setzt sie
   als `heading:` – die H1 übernimmt den Text, Titel, Breadcrumb und
   SEO-Zeile bleiben unangetastet. Genau so wurden `/presse/` und
   `/studien/` geheilt: Der sichtbare Wortlaut blieb erhalten, nur die
   zweite H1 verschwand. Auf der Studienseite wurde die Schirmzeile
   (`2.356,60 Euro pro Jahr`) in den Lead-Absatz übernommen – kein Satz,
   keine Zahl ging verloren.
3. **H1-Wache** (`scripts/h1_wache.py`, Regeln S1–S3):
   - **S1 Quelle:** Kein Markdown-Dokument unter `content/` **oder
     `archetypes/`** trägt eine `# …`-Zeile im Fließtext. Frontmatter,
     Code-Zäune und `#hashtag` werden erkannt und übersprungen; der Befund
     nennt Datei, Zeile, Text **und** den Handgriff. Archetypen stehen
     mit in der Pflicht: Eine H1 in einer Vorlage vererbt sich an jeden
     neuen Artikel.
   - **S2 Layout:** Der Baustein rendert genau eine H1 und ehrt
     `.Params.heading`; beide Einzel-Templates binden ihn ein und rendern
     selbst keine H1; die Abschnittsliste ehrt `heading:` ebenfalls. Damit
     ist der tote Zweig von Befund 3 vertraglich verboten.
   - **S3 Build:** Jede gebaute Seite trägt genau eine **nicht-leere** H1.
     Ausnahmen sind dokumentiert und begründet (Verifikationsdateien von
     Google/Pinterest, Blätter-Redirects, der Client-Redirect der
     Pinterest-Autorisierung) – eine Ausnahme ohne Grund ist eine Lücke mit
     Etikett, und der Selbsttest beweist das: Ohne die Begründung fällt die
     Seite wieder auf.
   **Die Wache heilt nicht selbst.** Eine H1 automatisch zu löschen
   vernichtete einen redaktionellen Satz; `--fix` ist vertraglich
   ausgeschlossen (C30). Sie meldet, die Redaktion entscheidet.
4. **Audit ohne Blindstelle** (`scripts/a11y_audit.py`): Der Lauf prüft
   jetzt **alle** gebauten Seiten statt einer Stichprobe von 20 – von 107
   HTML-Dateien bleiben 75 prüfbar, 32 sind begründet ausgenommen
   (20 Affiliate-Redirects, 8 Blätter-Redirects, 3 Verifikationsdateien,
   1 Client-Redirect). Bei einer falschen H1-Anzahl nennt der Bericht die
   Überschriften **textlich**, damit das automatische Issue ohne
   Nachfrage erklärt, was zu tun ist. Die Ausnahmenliste kommt aus der
   H1-Wache – eine Wahrheit, keine zweite Quelle.
5. **Vertrag C30** (`scripts/governance_contract.py`): „Eine Seite hat
   genau eine H1“. Er prüft Registrierung **und** Auswertung der drei
   Wachen-Pfade (eine erwähnte Flagge ist Papier), den einen Baustein mit
   `heading:`, die Verdrahtung beider Einzel-Templates, das stichprobenfreie
   Audit, beide Deploy-Schritte, `h1:check` in `package.json` und die
   Existenz der Regressionstests – plus eine **Wirkungsprobe**:
   `h1_wache.py --selftest` muss im Vertragslauf grün sein. Sechs
   Kunstbefunde beweisen, dass der Vertrag Sabotage sieht (Wache ohne
   Build-Prüfung, zurückgekehrte Stichprobe, aus `deploy.yml` entfernte
   Wache, selbst heilende Wache).
6. **Verdrahtung:** `deploy.yml` ruft die Wache **vor** dem Build
   (`--source-only`, billig, ohne Hugo) und **nach** dem Build
   (`--public public`, alle Seiten). Beide Schritte sind hart und schreiben
   eine Step-Summary. `npm run h1:check` / `npm run a11y:check` /
   `npm run test:h1` für die Arbeit am Schreibtisch, ein Browser-Test in
   `e2e/seo-a11y.spec.mjs` (genau eine gefüllte H1 auf Startseite,
   Ratgeber, Presse, Studien und Studienseite) als letzte Instanz.
   `selftest_runner.py` entdeckt die Wache automatisch; ihr Selbsttest
   steht im vertraglichen Minimum (C6).

**Was der Umbau sichtbar gemacht hat.** Die Zusammenlegung ist byte-identisch
am Output belegt (s. u.), aber sie verschiebt Code – und damit fielen vier
Prüfstellen auf, die die alte Doppeldatei voraussetzten. Sie wurden auf die
neue Lage umgestellt, **nicht** abgeschaltet:

| Prüfstelle | Alte Annahme | Neue Lage |
|---|---|---|
| `scripts/ff_voice_toolbar_check.py` (Lesehilfen-Wache, hart) | „Lesehilfen hängen in `single.html` und `_default/single.html`“ | prüft den Baustein + `pillar/single.html` (117/119 → **118/118 grün**) |
| `scripts/tests/test_offenlegung_gate.py` | Kennzeichnung in beiden Einzel-Templates | prüft den Baustein; Aussage „Kennzeichnung vor dem Inhalt“ bleibt |
| `scripts/tests/test_markenobjekt.py` | Kostenprofil in `single.html` | prüft den Baustein |
| `.github/workflows/lesehilfen-gate.yml` | Pfadfilter auf beide Einzel-Templates | zusätzlich `layouts/_partials/artikel_einzeln.html` – sonst hätte eine Änderung an der Einbindung das Gate nie wieder ausgelöst |

Das ist kein Kollateralschaden, sondern der Beweis, dass die Wachen ziehen:
Sie haben eine Verschiebung gemeldet, bevor sie in Produktion ging.

## Was bewusst nicht getan wurde

- **Kein Titel wurde angetastet.** Kein SEO-Titel, keine Beschreibung, kein
  Breadcrumb-Label hat sich geändert; `heading:` ergänzt die Schirmzeile,
  es ersetzt den Titel nicht.
- **Kein Anker ging verloren.** Die entfernten H1-Zeilen trugen zwar
  automatische IDs (`#presse-interviews-und-fachliche-zusammenarbeit`,
  `#daten-die-man-pruefen-und-zitieren-kann`,
  `#energie-kostet-im-modell-235660-euro-pro-jahr`) – eine Repo-Suche
  ergab: keine interne oder externe Stelle verlinkt sie.
- **Keine Prüfung wurde abgesenkt.** Kein Schwellenwert, keine Ausnahme
  ohne Begründung, kein `continue-on-error`.
- **Keine automatische Heilung.** Siehe oben: Content-Verlust durch eine
  Wache ist schlimmer als ein roter Lauf.

## Nachweis

| Prüfung | Ergebnis |
|---|---|
| `python3 scripts/h1_wache.py --selftest` | **17 Sabotageproben grün** (Quelle, Layout, Build, Ausnahmen, fail-closed) |
| `python3 scripts/h1_wache.py --source-only --public public` | **grün** – 106 Markdown-Dateien, 0 Doppel-H1, 75 gebaute Seiten geprüft |
| `python3 scripts/a11y_audit.py` | **grün** – 75 Seiten vollständig geprüft, **0 Probleme, 0 Kontrast-Fehler** (vorher: 2 gemeldet, 3 vorhanden) |
| `python3 -m unittest scripts.tests.test_h1_wache` | **Ran 20 tests, OK** |
| `python3 -m unittest discover -s scripts/tests` | **Ran 2045 tests, OK** (20 übersprungen) – keine Regression im Bestand |
| `python3 scripts/selftest_runner.py --ohne-uhr-probe` | **168 Wachen gelaufen, jeder Selbsttest grün** |
| `python3 scripts/ff_voice_toolbar_check.py` | **118/118 bestanden** (Lesehilfen-Wache) |
| `python3 scripts/offenlegung_gate.py` | **O1–O7 erfüllt** · 47 Seiten geprüft |
| `python3 scripts/governance_contract.py --selftest` | **✅ C1–C30** mit Kunstbefunden |
| `python3 scripts/governance_contract.py` | **🔒 alle 29 Regeln erfüllt** |
| Baustein-Zusammenlegung | 1425 gebaute Dateien verglichen: **byte-identisch**, außer genau den zwei gewollten H1-Texten (`presse/`, `studien/`) |
| Template-Auflösung | Baustein-Marker belegt `data-tpl="DEFAULTSINGLE"` auf `/presse/` und `/ueber/` |
| Sabotage-Gegenprobe | `# Sabotage-Probe` in `content/presse/index.md` → Exit 1 mit Datei, Zeile 41 und Handgriff; zurückgenommen → Exit 0 |

**Die drei Seiten heute:**

| Seite | eine H1 |
|---|---|
| `/presse/` | „Presse, Interviews und fachliche Zusammenarbeit“ |
| `/studien/` | „Daten, die man prüfen und zitieren kann“ |
| `/studien/fixkosten-index-2026-q4/` | „Fixkosten-Index Deutschland: Energie-Baseline Q4 2026“ |

---

## Nachhärtung des Audits (08.10.2026)

Die Dauerheilung aus #623/#630 war bereits im Bestand. Bei der erneuten
Premium-Abnahme fiel jedoch eine Implementierungslücke zwischen Anspruch und
Code auf: `a11y_audit.py` enthielt trotz des dokumentierten Single-Source-
Anspruchs noch eine eigene Ersatzliste, übersprang HTML-Dateien zusätzlich
über nicht dokumentierte Asset-/Substring-Filter und meldete einen fehlenden
`public/`-Build mit Exit 0. Außerdem verwendeten Build-Wache und A11y-Audit
unterschiedliche Regex-Pfade für die H1-Erkennung. Das konnte eine grüne
Meldung ohne vollständige Prüfung erzeugen.

**Nachgehärtet:**

- `h1_wache.py` und `a11y_audit.py` verwenden jetzt denselben
  HTML-aware Parser aus der Python-Standardbibliothek. HTML in Kommentaren,
  Skriptstrings oder inertem `<template>` wird nicht als Seiten-H1 gezählt;
  `&amp;` bleibt sichtbarer Text, während NBSP-, numerische und reine
  Zero-Width-Zeichen keine gefüllte H1 vortäuschen.
- Die Ausnahmen sind routenscharf und ausschließlich in `h1_wache.py`
  registriert. Das A11y-Audit hat keine Ersatzliste, keine pauschalen
  `assets`-/Substring-Skips und prüft wieder alle nicht ausgenommenen HTML-
  Dateien – auch wenn sie in einem Ordner `assets/` liegen.
- Fehlende Wache, fehlender Build oder null prüfbare HTML-Seiten sind jetzt
  **Exit 2 / `ok: false`**, nicht „übersprungen und grün“. Eine einzelne
  leere oder unsichtbare H1 wird im Voll-Audit ebenfalls ausdrücklich
  gemeldet.
- Vertrag C30 prüft den gemeinsamen Parser, das eine Ausnahmenregister,
  fail-closed-Verhalten, die Regressionstests sowie deren Verdrahtung in
  Deploy, npm und E2E-Pfadfilter. Der alte, falsche Template-Kommentar zur
  angeblich gewinnenden `layouts/single.html`-Auflösung ist bereinigt.

**Nachweis der Nachhärtung:** `hugo --minify --destination public
--cleanDestinationDir` erfolgreich (78 Hugo-Seiten, 107 HTML-Dateien);
`h1_wache.py --source-only` und `--public public` grün; A11y-Audit über alle
75 prüfbaren Seiten **0 Probleme, 0 Kontrast-Fehler**; H1-/A11y-Regressionen
**33/33 grün**; `governance_contract.py --selftest` **C1–C30 grün**.

Sabotage-Gegenprobe: ohne `public/` sowie ohne H1-Wache liefert das Audit
jeweils Exit 2 und `ok: false`; in `assets/`, in einer `BingSiteAuth.html`
oder in einer Unterseite namens `google-example.html` versteckte HTML-Seiten
fallen nicht mehr aus dem Vollscan.
