# Barrierefreiheit: „Label in Name" – Siegel-Heilung und Dauerwache · 26.10.2026

**Ausgangslage:** Zwei Befunde der A11y-Spec lagen in **gesiegelten** Dateien
(`layouts/_partials/header.html`, `layouts/_partials/extend_post_content.html`)
und waren deshalb als Ausnahme mit Prüftermin 2026-12-31 registriert. Die
fertigen Patches standen in `docs/ANLEITUNG-A11Y-AXE.md`.

**Ergebnis:** Beide Patches sind eingespielt, das Siegel ist neu signiert, die
Ausnahme-Registry ist **leer** (`[]`). Der Browser-Lauf ist ohne Ausnahme grün –
**60 Tests in beiden Playwright-Projekten** (Desktop 1280 px, iPhone 14
390 px). Dabei kamen ein **dritter Befund derselben Klasse** (68 Karten auf den
Ratgeber-Welten, für die Spec unsichtbar) und **zwei weitere axe-Befunde** auf
diesen Seiten ans Licht. Alle sind geheilt, und die Fehlerklasse ist jetzt an
drei unabhängigen Stellen dauerhaft bewacht.

> Dieser Bericht ist der Wahrheitsort für diese Runde. Die Bedienungsanleitung
> der Spec steht in `docs/ANLEITUNG-A11Y-AXE.md` (dort aktualisiert).

---

## 1 · Die zwei Befunde hinter dem Siegel

### 1.1 Marken-Link (`layouts/_partials/header.html`)

Sichtbar ist „Unabhängige Fixkosten-Redaktion", im `aria-label` fehlte dieser
Text (WCAG 2.5.3, Label in Name). Der Override ist entfernt:

```diff
-            <a href="{{ "" | absLangURL }}" accesskey="h" title="{{ $label_text }} (Alt + H)"
-               class="ff-brand" aria-label="FranksFinanzcheck – zur Startseite">
+            <a href="{{ "" | absLangURL }}" accesskey="h" title="{{ $label_text }} (Alt + H)"
+               class="ff-brand">
```

Logo (`aria-hidden="true"`), `accesskey` und `title` bleiben unberührt. Der
Accessible Name ist jetzt der sichtbare Descriptor:

```
- link "Unabhängige Fixkosten-Redaktion":
  - /url: https://franksfinanzcheck.de/
```

### 1.2 Weiterlese-Karten (`layouts/_partials/extend_post_content.html`)

Der Override „Weiterlesen: <Titel>" verschwieg Datum, Kategorie und Anriss.

```diff
-    <a href="{{ .Permalink }}"
-       aria-label="Weiterlesen: {{ .Title | plainify }}"
-       class="ff-related-card">
+    <a href="{{ .Permalink }}" class="ff-related-card">
```

Der Name ist jetzt die Summe der sichtbaren Kindtexte. Das ist die robustere
Variante: Ändert sich eine Zeile im Card-Layout, kann der Name nicht mehr
auseinanderlaufen.

---

## 2 · Die Falle, die den Patch allein rot gemacht hätte

`assets/css/extended/zzz-agency-polish.css` blendete den Descriptor unter
768 px mit `display: none` aus. `display: none` nimmt Text **auch aus dem
Accessibility-Tree** – der Marken-Link hätte im 390-px-Projekt also **gar
keinen Namen** gehabt. axe meldet das als `link-name` (impact: critical) auf
jeder Mobilseite. Der Patch wäre damit „fertig" und trotzdem rot gewesen.

Die Mobile-Regel versteckt den Text jetzt visuell, nicht semantisch
(1×1-px-Technik, `position: absolute`, `clip`):

```css
@media (max-width: 768px) {
  .ff-brand-descriptor {
    position: absolute; width: 1px; height: 1px;
    padding: 0; margin: -1px;
    overflow: hidden; clip: rect(0, 0, 0, 0);
    white-space: nowrap; border: 0;
  }
}
```

Gemessen im 390-px-Layout: `display: block`, Breite `1px`, Accessible Name
vorhanden. WCAG 2.5.3 verlangt den **sichtbaren** Text im Namen; zusätzlicher,
visuell verborgener Text ist erlaubt – und der Screenreader hört weiterhin den
Namen der Redaktion.

---

## 3 · Der dritte Befund: 68 Karten, die die Spec nie sah

`layouts/pillar/single.html` baute die Karten-Grids der Ratgeber-Welten mit
exakt demselben Muster:

```html
<a href="…" aria-label="Weiterlesen: Energieeffizienz im Haushalt …" class="ff-pc-card">
  <!-- sichtbar: Titel, Anriss, „Jetzt lesen →" -->
```

Die feste Seitenliste der Spec (`/`, Werkzeuge, Cockpit, Suche, Presse, Über,
Rechtstexte, neuester Artikel) enthielt **kein** `/pillar/*`. Deshalb war der
Befund für das Gate unsichtbar – bei 68 Knoten auf fünf Seiten:

| Ratgeber-Welt | `.ff-pc-card`-Knoten |
|---|---|
| Strom & Gas | 22 |
| Frugalismus | 17 |
| Internet & DSL | 16 |
| Konto & Karten | 8 |
| Mietwagen & Reisen | 5 |
| Versicherungen | 0 (keine Karten) |

**Heilung:** Override entfernt, Name kommt aus dem Inhalt. **Und** die
Ratgeber-Welten kommen automatisch aus dem Build ins Gate – wie die
Werkzeugseiten, ohne Pflegeliste. Die Spec prüft selbst, dass mindestens sechs
gebaut wurden; fällt eine aus dem Build, ist das ein Befund und keine stille
Lücke.

**Folgewirkung, die man nicht übersehen darf:** `scripts/themenwelten_guard.py`
zählte die Artikel je Welt über `aria-label="Weiterlesen: …"` – also über genau
den Fehler, der hier geheilt wurde. Der Zähler liest jetzt die Klasse
`.ff-pc-card`. Ein Gate darf seine Zahl nicht aus dem Zustand ziehen, den es
verhindern soll.

---

## 4 · Zwei weitere Befunde, die erst die neue Abdeckung zeigte

| Befund | Seite | Ursache | Heilung |
|---|---|---|---|
| `label` (critical), 6 Knoten | `/pillar/mietwagen/` | Goldmark rendert `- [ ]` als `<input disabled type="checkbox">` ohne Label. Die Heilung existierte nur im Artikel-Layout. | Gemeinsames Partial `layouts/_partials/aufgabenlisten_a11y.html`; Artikel **und** Pillar-Seiten nutzen es. Eine Wahrheit statt zweier Kopien derselben Zeile. |
| `scrollable-region-focusable` (serious) | Strom & Gas, Frugalismus, Internet & DSL | Der PaperMod-Reset macht jede Tabelle zum Scrollcontainer (`display: block; overflow-x: auto`). Die Matrix war scrollbar, aber nicht per Tastatur erreichbar. | `tabindex="0"` + `aria-label` an der Tabelle, Fokusring aus dem Marken-Token (`--ff-yellow`) in `zzz-agency-polish.css`. |

Die Tabellen sind Roh-HTML in den Inhaltsdateien; der Markdown-Tabellen-Hook
(`render-table.html`) greift dort nicht. Die Heilung steht deshalb dort, wo das
Markup entsteht – kein nachgelagertes Skript, keine Unterdrückung.

---

## 5 · Dauerwache in drei Ebenen

| Ebene | Was sie sieht | Wo |
|---|---|---|
| **Browser (axe-core)** | gerendertes DOM, berechnete Namen, beide Viewports | `e2e/a11y-axe.spec.mjs` – feste Seiten + **alle** Werkzeuge + **alle** Ratgeber-Welten + neuester Artikel |
| **Wirkungsprüfung** | den Namen, den der Screenreader bekommt (`toHaveAccessibleName`) | 3 neue Tests: Marken-Link, Weiterlese-Karten (Titel **und** Datum), Pillar-Karten |
| **Statisch, alle Seiten** | `aria-label`, das sichtbaren Text verschweigt (WCAG 2.5.3) | `scripts/a11y_audit.py` – läuft im Deploy und wöchentlich, **222 gebaute Seiten** |

Die statische Prüfung ist bewusst kein Attribut-Test: Sie baut den sichtbaren
Text des Links aus dem HTML (inklusive verschachtelter Auszeichnung), entfernt
`aria-hidden`-Teilbäume und die hausüblichen `sr-only`-Klassen und verlangt
den Rest im deklarierten Namen. Verglichen wird normalisiert (NFKC,
Whitespace, Groß/Klein).

Bewusste Grenzen: `aria-labelledby` wird nicht aufgelöst (dafür braucht es
einen Accessibility-Tree), und CSS-Sichtbarkeit über Media Queries sieht nur
der Browser. Genau diese Fälle deckt die Playwright-Wirkungsprüfung ab – beide
Ebenen zusammen sind der Beweis, keine allein.

Die Prüfung selbst hat eine Lehre aus dem ersten Entwurf: Ein naiver Parser,
der `<picture>` für ein Void-Element hält, verliert den gesamten Kartentext und
meldet **fälschlich „0 Befunde"** – real passiert und im Test
`test_verschachtelte_auszeichnung_wird_vollstaendig_gelesen` eingefroren.

---

## 6 · Siegel

Die Änderung an gesiegelten Dateien ist keine Nebenbei-Signatur, sondern ein
belegter Vorgang: `python3 scripts/integrity_guard.py --set-current` schreibt
Datum, HEAD, Datei-Map, Hash-Kette und die Herkunft (Commits, Klasse, Urteil)
in `data/integrity_lock.json` und eine Zeile nach
`data/integrity_history.jsonl`.

Betroffene gesiegelte Dateien dieser Runde:

| Datei | Änderung |
|---|---|
| `layouts/_partials/header.html` | `aria-label` am Marken-Link entfernt |
| `layouts/_partials/extend_post_content.html` | `aria-label` an Weiterlese-Karten entfernt |
| `layouts/pillar/single.html` | `aria-label` an Pillar-Karten entfernt; Aufgabenlisten-Heilung ergänzt |

Nicht gesiegelt und deshalb ohne Signaturbedarf: CSS
(`zzz-agency-polish.css`), Inhalte (drei Ratgeber-Welten), Wachen und Spec.

---

## 7 · Verifikationsmatrix

| Prüfung | Ergebnis |
|---|---|
| `python3 scripts/integrity_guard.py --selftest` | ✅ 9 Fälle |
| `python3 scripts/integrity_guard.py` (nach Signatur) | ✅ Kern entspricht exakt dem signierten Zustand |
| `python3 scripts/integrity_guard.py --gate` | ✅ kein Drift |
| `HUGO_JSDELIVR_SHA=localdev hugo --minify --destination public` | ✅ 109 Seiten |
| `python3 scripts/a11y_audit.py` | ✅ **222 Seiten, 0 Probleme**, 0 Kontrast-Fehler |
| `npm run test:a11y:browser` | ✅ **60 Tests, beide Projekte** – ohne Ausnahme |
| `python3 -m unittest scripts.tests.test_a11y_audit` | ✅ **18 Tests** (9 neue für 2.5.3) |
| `python3 scripts/themenwelten_guard.py --selftest` | existiert nicht (der Guard hat keinen Selbsttest; Basisbefund unten) |
| `python3 scripts/themenwelten_guard.py --public public` | ⚠️ 24 Meldungen – **identisch auf `b6de502`** (Basisbefund unten) |
| `python3 scripts/tabellen_lesbarkeit_guard.py --selftest` | ✅ |
| `python3 scripts/content_html_wache.py --selftest` | ✅ |

Die Registry `data/a11y/axe_ausnahmen.json` ist `[]`; die Spec-Tests
„Ausnahmen-Registry ist begründet, datiert und läuft ab" bleiben grün, weil es
nichts zu rechtfertigen gibt.

### Basisbefund (nicht von dieser Runde)

`scripts/tests/test_themenwelten.py::HugoPublicationTests` schlägt auf dem
unveränderten `main` (`b6de502`) identisch fehl: Der Guard verlangt an den
Themen-Karten ein `aria-labelledby`, das die Vorlage nicht setzt (24 Meldungen,
u. a. „zugänglicher Linkname stimmt nicht mit dem Titel überein"). Das wurde in
einem separaten Worktree auf dem Basisstand reproduziert und **nicht** durch
eine Ausnahme maskiert. Es gehört in einen eigenen Vorgang, weil dort die
Frage „Overlay-Name vs. Inhalt" für die Themen-Karten neu entschieden werden
muss – die alte Entscheidung kollidiert mit der 2.5.3-Heilung.

---

## 8 · Grenzen (ehrlich benannt)

- Ein grüner axe-Lauf ist **kein** BFSG-Nachweis. Automatisierbar sind rund ein
  Drittel der WCAG-Kriterien.
- Geprüft wird der lokale Build, nicht die ausgelieferte Seite.
- Zustände hinter Interaktion (aufgeklappte Menüs, Formularfehler) decken die
  verhaltensbezogenen Specs und der Mensch ab – nicht dieser Lauf.
- Die fachliche Wirkung des Namens („Hört sich das für einen Menschen
  verständlich an?") kann kein Gate entscheiden. Die Prüfung erzwingt nur,
  dass der sichtbare Text im Namen steckt und kein Override ihn verschweigt.
