# 📐 Layout-Automatisierung – Wächter, Budgets und Reparatur (Issue #338)

**Stand:** 21.09.2026 · **Basis:** `scripts/dom_audit.py`-Vermessung des
minifizierten Produktionsbaus (`hugo --minify`) · **Anlass:** Issue
„⚠ Layout-Automatisierung: Probleme gefunden" (#338)

Diese Datei ist das Runbook zur Layout-Wache: was sie prüft, warum die Grenzen
so liegen, wie man sie ändert – und was am 21.09.2026 repariert wurde, damit
derselbe Fehlalarm nicht wiederkommt.

---

## 1. Zwei Ebenen, ein Budget

| Ebene | Werkzeug | Umfang | Läuft |
|---|---|---|---|
| **Statisch** (kein Browser, ohne Netz) | `scripts/dom_audit.py` | **jede** gebaute Seite | in `layout_audit.py` und damit in jedem Layout-AI-Lauf |
| **Browser** (Chrome headless) | `scripts/layout_browser_check.js` | Startseite + 3 neueste Artikel + die statisch schwersten Seiten, je Desktop & Mobile | im Layout-AI-Workflow (weich: fehlt Chrome, wird übersprungen) |

`layout_audit.py` prüft intern: interne Links, Cover-Varianten, Alt-Texte,
Schema/og/Meta/H1, **hreflang-Hygiene** (siehe § 3.1), DOM-Budget und
Chunker-Vertrag. Es vereint beides im Report `LAYOUT-REPORT.md` (gitignored,
Lauf-Artefakt) und legt die Maschinenzahlen unter
`.cache/layout/dom-audit.json` ab. Genau diese Datei liest der Browser-Audit:
er vergleicht seine echten Browsermesswerte mit den Parserwerten (Toleranz
2 Kinder / 2 Tiefe / 5 Elemente) und meldet **Parser-Drift** als Befund. Damit
prüft sich der Parser bei jedem Lauf selbst mit – gegen einen echten Browser.

**Budgets (eine Wahrheit: `scripts/dom_audit.py`)**

| Metrik | Frühwarnung (ausgeliefert) | Lighthouse-Grenze | Ist ausgeliefert (21.09.2026) |
|---|---|---|---|
| Kinder eines Elements | 54 | 60 | **50** (`html > head`) |
| Kinder im `<head>` | 52 | 58 | **50** |
| Tiefe | 28 | 32 | **12** |
| Elemente je Seite | 1100 | 1400 | **968** |

**Zwei Messbereiche – das war die zweite Ursache der roten Läufe:** Der
statische Audit vermisst die **ausgelieferte HTML** (jede Seite). Der Browser
sieht mehr: `static/premium/ff-premium.js` baut zur Laufzeit die
Mini-Inhaltsübersicht, Anker-Buttons und die Lese-Fortschrittsleiste, die
Lesehilfen kommen dazu – nachgemessen **968 → 1109 Elemente** auf der
schwersten Artikelseite (+141, wachsend mit der Artikel-Länge). Das ist eine
Funktion, kein Fehler. Deshalb:

* **Laufzeit-DOM** wird gegen `fruehwarnung_runtime` geprüft (Kopf/Tiefe
  unverändert 52/28, Elemente **1350**); harte Grenze bleibt overall die
  Lighthouse-Grenze 1400 – sie billigt auch Lighthouse dem Laufzeit-DOM zu.
  Ein eigener Kopf-/Tiefenwert wäre eine erfundene Zahl und steht deshalb auf
  demselben Wert wie statisch.
* **Parser-Gegenrechnung** vergleicht den Parser mit einer zweiten
  Browsermessung, bei der Fremd-Skripte durch leere Antworten **ersetzt**
  (nicht geladen) werden – nur so sieht der Browser, was der Parser sieht.
  Vorher verglich er Laufzeit gegen Parser und meldete jede legitime
  Erweiterung als „Drift" (Δ92–171) – ein Dauer-Fehlalarm der schlimmsten
  Sorte, weil er nach einem echten Parser-Fehler aussah.
  Diese Messung schützt sich selbst: Der HTTP-Cache wird abgeschaltet (sonst
  kommt das zweite Laden aus dem Speicher, es gibt keinen Request – die
  Ersetzung greift ins Leere, gemessen als „Erweiterungsschicht +0"), und die
  Zahl der ersetzten Skripte wird gegen die Zahl der ausgelieferten
  `<script src>` geprüft. Liefert eine Seite Fremd-Skripte aus und es wird
  keins ersetzt, ist das ein **harter Befund „Messinstrument unbrauchbar"** –
  eine Referenz, die nicht sagt, ob sie funktioniert hat, ist keine.
* Beide Zahlen stehen im Browser-JSON (`domMetrics`, `domMetricsHtmlOnly`,
  `erweiterungsschicht`) und in der `::notice::`-Annotation.

Frühwarnungen stehen nur im Report (Exit 0). Ein Issue und ein roter Lauf
entstehen erst an der Lighthouse-Grenze – außer man ruft mit `--strict`
(Befund auch bei Frühwarnung).

---

## 2. Wurzelursachen von #338 (alle fünf behoben)

| # | Ursache | Wirkung | Heilung |
|---|---|---|---|
| 1 | Audit-Sample: nur Startseite + 3 neueste Artikel | Die Tag-Übersicht `/tags/` mit **136 direkten Kindern** in *einer* Liste war nie im Blick | `dom_audit.py` vermisst **jede** Seite; `/tags/` ist jetzt nach Anfangsbuchstaben gruppiert (max. 21 Kinder je Liste) |
| 2 | Gemessen wurde `hugo --quiet` (unminifiziert) | Zahlen entsprachen nicht dem ausgelieferten Stand | Bau im Workflow + Vermessung jetzt `hugo --minify` wie in `deploy.yml` |
| 3 | Budget war unerreichbar („Head 59 > 58") | Dauer-Fehlalarm auf praktisch jeder Artikelseite | Head strukturell verkleinert (60 → 50) **und** Budget begründet (`52`/`58`) – die Zahl ist jetzt template-, nicht redaktionsabhängig |
| 4 | Alt-Text-Warnung kam aus dem Frontmatter | Der gemeldete Beitrag ist ein **Entwurf ohne Cover** – ein Bild ohne Bild hat keinen Alt-Text | Prüfung läuft am **gebauten Stand** (Artikel-Inhalt); Frontmatter nur für *veröffentlichte* Beiträge; Entwürfe erscheinen als Hinweiszeile, nicht als Warnung |
| 5 | Statischer Audit konnte kein Issue auslösen (`|| true`) und das Issue wurde nur *erstellt*, nie aktualisiert/geschlossen | Befunde verpufften; ein einmal geöffnetes Issue blieb für immer offen | Workflow wertet `STATIC_EXIT`/`BROWSER_EXIT` aus, wird bei Befunden rot, **aktualisiert** das Issue (Marker) und **schließt** es, sobald der Lauf grün ist |

---

## 3. Was am Bau geändert wurde

### 3.1 Head-DOM: 60 → 50 Kinder (Artikel-Seiten)

* **`article:tag` entfernt** (`layouts/_partials/templates/opengraph.html`).
  Bis zu **sechs** Meta-Tags pro Artikel, die nachweislich kein Konsument mehr
  auswertet: dieselben Begriffe stehen als `keywords` im Article-JSON-LD und
  sichtbar in der Tag-Navigation. Der größte Einzelposten am Budget.
* **Analytics + Service-Worker ans Body-Ende**
  (`layouts/_partials/deferred_scripts.html`, eingebunden von `footer.html`).
  Umami (cookieless) und die SW-Registrierung blockieren nichts und gehören
  nicht in den kritischen Pfad. Das Consent-Gate ist **unverändert**: geladen
  wird nur nach „Alle akzeptieren" (`ff_cookie_consent=all`), der
  `ffConsentChange`-Horcher bleibt.
* **`apple-mobile-web-app-status-bar-style` entfernt** – der gesetzte Wert
  `default` *ist* das Plattformverhalten, das Tag änderte nichts.
* **Doppelte hreflang-Selbstreferenz entfernt** (`extend_head.html`). Das
  versiegelte `head.html` setzt über `range .AllTranslations` bereits
  `<link rel=alternate hreflang=de …>`; `extend_head.html` setzte dieselbe
  Zeile noch einmal – auf **jeder** Seite doppelt, auf 12 Paginierungsseiten
  sogar mit zwei verschiedenen Zielen (Abschnitts-Wurzel vs. Seiten-URL).
  Zwei Werte für eine Sprache sind ein Widerspruch und werden ignoriert.
  Jetzt gilt: genau **eine** Angabe je Sprache, und sie zeigt auf das
  Canonical – gesetzt wird sie nur, wenn `head.html` sie nicht schon
  (identisch) setzt. Neue Wache: `check_hreflang()` in `layout_audit.py`
  (Doppelung = kritisch, fehlende Selbstreferenz = kritisch, Pager-Abweichung
  = Warnung).
* **Geprüft und bewusst behalten:** `og:image:type` (dokumentierte Entscheidung
  aus `docs/PREMIUM-AUDIT-2026-09-11.md` § 2.10), Maße, Alt,
  Verification-Tags, Twitter-Cards, Preloads.
* Nicht angefasst: `layouts/_partials/head.html` ist im Integritäts-Lock
  **KRITISCH-versiegelt** (menschliche Signatur nötig). Die Verkleinerung
  kommt deshalb vollständig aus freien Partials.

> **Regel für neue Metas:** Der Head ist ab jetzt eine harte Budgetgröße.
> Wer ein Tag ergänzt, nimmt ein anderes weg – oder `BUDGET.head_children` in
> `scripts/dom_audit.py` wird bewusst angehoben (und der Test
> `scripts/tests/test_dom_audit.py` mit). Der Layout-Audit zählt es sonst als
> Frühwarnung.

### 3.2 Text-Teilung (DOM-Gruppen in langen Ratgebern)

`layouts/_partials/sectioned_content.html` teilte Markdown-Inhalte nur an
`<h2>` – ein langer H2-Abschnitt blieb damit bei bis zu 58 direkten Kindern.
Jetzt wird zusätzlich an **jeder `h3`** geteilt (`<h[23] id="…">`), die Gruppen
folgen der Gliederung. Die Teilung ist eine Textoperation auf dem gerenderten
Markdown; sie greift nur bei Überschriften **mit `id`** (also nur bei
Goldmark-Überschriften, nie bei Template-/Shortcode-Überschriften). Den Vertrag
prüft der Audit nach: **Chunker-Vertrag** – H2/H3 mit `id` im Artikel-Inhalt
müssen direkt im Inhaltsblock oder in einer Gruppe liegen (sonst „Container
aufgerissen" = kritisch).

### 3.3 Tag-Übersicht: 136 → max. 21 Kinder je Liste

`layouts/taxonomy.html` (neuer Site-Override, gilt für `/tags/` **und**
`/categories/`) gruppiert die Begriffe nach Anfangsbuchstaben:

* eine `<ul class="terms-tags">` **je Buchstabe** statt einer Liste mit 136 `<li>`,
* A–Z-Sprungleiste (`.terms-index`) und echte `<h2>`-Überschriften je Gruppe
  (Struktur für Screenreader, `id="term-a"`… als Anker),
* Optik unverändert: dieselben Chips, dieselbe Hochzahl (`.terms-tags` bleibt
  der Theme-Selektor), neue Zusatzstile nur in
  `assets/css/extended/zzz-taxonomie-gruppen.css`.

### 3.4 Alt-Texte: geprüft wird, was ankommt

`check_alts()` in `scripts/layout_audit.py` prüft jedes `<img>` im
**gerenderten Artikel-Inhalt**. Ein leeres `alt` ist erlaubt, wenn das Bild
ausdrücklich dekorativ ist (`aria-hidden="true"` / `role="presentation"`,
z. B. das Logo-Lockup im Header, dessen Link den Namen trägt). Gemeldet wird
außerdem, was wie ein Alt-Text aussieht, aber keiner ist („generisch"):
Dateinamen (`cover.jpg`), Kürzel (`bild`, `foto`) und Dateistämme mit
Größen-Suffix (`hero-1200`) – `is_generic_alt()` in derselben Datei.
Zusätzlich (warnend) geprüft: veröffentlichte Beiträge mit Cover, aber ohne
`cover.alt` – Entwürfe ohne Cover werden als Hinweis gezählt.

---

## 4. Verifikation (Beleg statt Behauptung)

| Beweis | Ergebnis |
|---|---|
| Parser gegen **parse5** (`scriptingEnabled: true` = Browser mit JS), alle 371 gebauten Seiten | **0 Abweichungen** bei Elementen, Tiefe, max. Kindern, Head-Kindern |
| `python3 scripts/dom_audit.py --selftest` | 8 eingefrorene Parser-Fälle (unquotierte Attribute, impliziter `<tbody>`, `<p>`-Autoclose, `<noscript>`-Rohtext, SVG-Selbstschluss, Fremdinhalt, Kommentare/`<script>`-Inhalte, Pfadangaben) |
| Browser-Audit im CI (Puppeteer) | rechnet jeden Lauf gegen `.cache/layout/dom-audit.json` (Budget-SSOT), misst Laufzeit-DOM **und** HTML-Messung ohne Fremd-Skripte; Drift zwischen Parser und HTML-Messung = Befund |
| `node scripts/layout_browser_check.js --selftest` | 13 Verträge ohne Chrome (Budget-/Severity-Logik inkl. Laufzeitsatz) (u. a. „Laufzeit 1109 Elemente ist kein Befund", „ausgeliefert wären 1109 eine Frühwarnung", „+1 über der Lighthouse-Grenze ist rot") |
| `python3 -m unittest discover -s scripts/tests` | **549 Tests grün** (14 übersprungen: jsdom-Parität ohne `NODE_PATH`), davon 58 neue in dieser Runde (`test_dom_audit.py` 40: Parservertrag, Budget-/Exit-Logik, Chunker-Vertrag, Alt-Prüfung, hreflang-Hygiene, Template- und Browser-Verträge, optionaler jsdom-Parallelbeweis; `test_layout_annotations.py` 12: Annotationen/Deckel-Escaping/Notiz; `test_workflow_yaml.py` 6: YAML-, Step-, JS- und Skriptpfad-Wachen) |
| hreflang-Hygiene (`check_hreflang()`) | 371 Seiten je **genau eine** Angabe pro Sprache, keine Doppelung; auf 12 Paginierungsseiten zeigt das geerbte `de` auf die Abschnitts-Wurzel → **Warnung** mit Quelle (`head.html`, versiegelt) statt stiller Duldung |
| `python3 scripts/integrity_guard.py` | grün – 7 KRITISCH-versiegelte Knoten unangetastet |

**Vorher → Nachher (minifizierter Bau, 213 Seiten ohne Paginierung):**

| Kennzahl | vorher | nachher | Budget |
|---|---|---|---|
| max. Kinder eines Elements | **136** (`/tags/`, `ul.terms-tags`) | **50** (`html > head`) | 54 / 60 |
| max. Kinder im `<head>` | **60** (Artikel mit FAQ) | **50** | 52 / 58 |
| `article:tag`-Metas je Artikel | bis **6** | 0 | – |
| Seiten im Blick der Vermessung | 4 | **213** | – |
| Skripte im `<head>` | 8 | 6 | – |

---

## 5. Betrieb

```bash
# Vollständig (Statisch + DOM-Budget + Chunker-Vertrag)
python3 scripts/layout_audit.py

# Nur DOM-Budget, mit Zahlen und JSON
python3 scripts/dom_audit.py --top 15 --json .cache/layout/dom-audit.json
python3 scripts/dom_audit.py --only /tags/          # eine Seite
python3 scripts/dom_audit.py --strict               # Frühwarnung = Exit 1
python3 scripts/dom_audit.py --selftest

# Browser-Audit (lokal, wenn Chrome vorhanden ist)
LAYOUT_BASE=$PWD/public LAYOUT_PORT=8099 CHROME_PATH=/pfad/chrome \
  node scripts/layout_browser_check.js
```

**Workflow `.github/workflows/layout-ai.yml`** (Mo 07:00 UTC, manuell und
bei Pull Requests mit Layout-Pfaden):

1. `hugo --minify` (identisch zur Produktion),
2. statisches Audit → `STATIC_EXIT`, Report + Zahlen,
3. Auto-Heilung: `check_covers.py --fix`, Commit + Push (`git_sync.sh --push-only`),
4. Browser-Audit → `BROWSER_EXIT` (0 grün, 1 Befunde, **2 = übersprungen**, wenn
   kein Chrome installierbar ist – dokumentiert und gewollt, weil das statische
   Budget jede Seite abdeckt),
5. **Annotationen in den Checks** (`layout_annotations.py`): kritische Befunde
   als `::error::` (rot in der PR-/Checks-Ansicht), Frühwarnungen als
   `::warning::`, Kennzahlen als `::notice::` – gedeckelt auf 10 je Stufe, mit
   Nennung der verschwiegenen Anzahl,
6. Job-Summary mit Report und Browser-JSON,
7. Issue-Lebenszyklus über Marker `<!-- layout-ai-report -->` **oder** den
   festen Titel (Alt-Issues aus früheren Workflow-Versionen ohne Marker werden
   übernommen – sonst bleibt der alte Alarm offen *und* ein zweiter entsteht):
   **anlegen oder aktualisieren** bei Befunden, **kommentieren + schließen**
   bei grün. Ein Issue ohne Schließpfad ist ein Alarm ohne Ende – genau das
   war #338.

Im **Pull-Request-Modus** läuft derselbe Bau und derselbe Audit, aber ohne
Auto-Heilung und ohne Issue-Pflege – ein PR darf keine Commits in seinen
Branch schreiben und keine Alarm-Issues erzeugen. Befunde machen den Lauf rot
und stehen in der Job-Summary; dieser Lauf ist das Gate vor dem Merge.

**Offener Punkt (versiegelt, menschliche Entscheidung):** Auf 12
Paginierungsseiten (`/…/page/N/`, N≥2) setzt das **KRITISCH-versiegelte**
`head.html` die `de`-Selbstreferenz auf die Abschnitts-Wurzel statt auf die
Seite. Der Audit meldet das als Warnung (kein roter Lauf – sonst entstünde
wieder ein Dauer-Alarm). Behebbar ist es nur durch eine signierte Änderung an
`head.html` (`integrity_guard.py --set-current` nach menschlicher Prüfung);
alles außerhalb des Siegels ist bereits korrekt (`x-default` zeigt überall auf
das Canonical).

**Grenzen der Automatik:** Der statische Audit misst ohne Browser; gerechnet
wird mit den Regeln des HTML5-Parsers (siehe Kopf von `dom_audit.py`). Läuft
der Browser-Audit, wird diese Annahme bei jedem Lauf gegengeprüft. Läuft er
nicht, bleibt die Annahme ungeprüft – deshalb ist der Skip sichtbar
(`::warning::` + Job-Summary), nicht still.

## 6. Selbstschutz: die Automatik darf nicht still sterben

Am 21.09.2026 (beim Umbau genau dieser Dateien) stand in einem Step-Namen ein
ungeschützter Doppelpunkt:

```yaml
- name: Website bauen (identisch zur Produktion: `hugo --minify`)   # ✗ YAML-Fehler
```

Das ist gültiges Aussehen, aber kein gültiges YAML: GitHub legt die Datei
still („This run likely failed because of a workflow file issue"), der Lauf
stirbt vor dem ersten Step. Der Fehler war nur zufällig sichtbar, weil für den
Push ein Fehl-Lauf angelegt wurde – **kein Test und kein Lint im Repo hätte
ihn gefunden**.

Seitdem prüft `scripts/tests/test_workflow_yaml.py` **alle** Workflows:

1. gültiges YAML (jede Datei),
2. keine doppelten Schlüssel (PyYAML nimmt sonst still den letzten – so
   verschwindet ein Step, ohne dass es auffällt),
3. vorhandenen `on:`-Auslöser, je Job `runs-on`, Steps mit `run` oder `uses`,
   keine unbekannten Step-Schlüssel,
4. Step-Namen ohne die YAML-Falle „Doppelpunkt + Leerzeichen" (quotiert ist
   erlaubt).

4b. die JavaScript-Blöcke der `actions/github-script`-Steps syntaktisch
    gültig sind (in der Hülle, in der die Action sie ausführt). Warum:
    der Issue-Step steht auf `continue-on-error: true` – ein Syntaxfehler
    darin würde still übersprungen, und das Issue würde nie gepflegt.

Der Test läuft in `python3 -m unittest discover -s scripts/tests` mit – also
vor jedem Push, den die Pipeline ernst nimmt. Regel daraus: **jede Datei, die
einen Lauf steuert, hat einen Test, der sie parst.** Eine Wache ohne Wache ist
keine Wache.

Und ein zweiter Beschluss aus #338: Die Issue-Pflege dedupliziert über den
Marker **und** den festen Titel. Issues aus einer älteren Workflow-Version
(ohne Marker) werden damit übernommen und bei Grün geschlossen – sonst bliebe
der alte Alarm offen und der nächste Befund erzeugte einen zweiten.

## 7. Zweite Lehre: eine Prüfung, die immer Alarm schlägt, wird abgeschaltet

Der erste PR-Gate-Lauf (21.09.2026) war rot – und zwar an einer Stelle, die
niemand sehen konnte: Die Befunde standen nur im Log, der Issue-Step ist im
PR-Modus (richtig) ausgeschaltet. Zwei Fehler steckten darin:

1. **Unsichtbarkeit.** Ein Befund, den man erst nach dem Klick in den Lauf
   findet, existiert für die Entscheidung nicht. Behoben mit
   `scripts/layout_annotations.py`: kritische Befunde werden `::error::`,
   Frühwarnungen `::warning::`, dazu eine `::notice::` mit den Kennzahlen –
   direkt in der Checks-/PR-Ansicht, gedeckelt auf 10 je Stufe, mit Nennung der
   verschwiegenen Anzahl.
2. **Falsche Bezugsgröße.** Der Browser verglich sein Laufzeit-DOM mit dem
   Parser: Δ92–171 Elemente Unterschied, auf jeder Artikelseite, bei jedem
   Lauf. Das sah nach „Parser kaputt" aus, war aber die Erweiterungsschicht der
   Site (Mini-Inhaltsübersicht, Anker, Fortschrittsleiste, Lesehilfen). Zwei
   Messungen statt einer Meinung: Laufzeit gegen Laufzeit-Budget, HTML-Messung
   (Fremd-Skripte ersetzt) gegen Parser. Erst dadurch ist „Drift" wieder ein
   Signal für einen echten Parser-Fehler. Beim ersten Versuch war auch diese
   Messung noch falsch (HTTP-Cache lieferte die Skripte aus dem Speicher) – die
   Differenz war „+0" und damit sichtbar: seitdem prüft sich das Instrument
   selbst (siehe § 1) und der Fehler kann nicht mehr still auftreten.

Nebenbei fiel dabei ein echter Fehler auf: jede Seite trug die
hreflang-Selbstreferenz **doppelt** (versiegeltes `head.html` und
`extend_head.html`), auf 12 Paginierungsseiten mit widersprüchlichen Zielen.
Siehe § 3.1 und die Warnung in `check_hreflang()`.

**Regel:** Wenn eine Prüfung wiederholt Alarm schlägt, ist zuerst die
Bezugsgröße falsch – nicht die Schwelle. Schwellen anzupassen, bis es grün
ist, war die Ursache von #338; Bezugsgrößen zu trennen ist die Heilung.
