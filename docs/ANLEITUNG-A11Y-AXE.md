# Barrierefreiheit im gerenderten Zustand (axe-core)

**Ziel:** WCAG 2.1/2.2 AA dort prüfen, wo sie entstehen – im gerenderten DOM.
`scripts/a11y_audit.py` liest den gebauten Text (lang, title, genau eine H1,
alt-Attribute, Skip-Link, `focus-visible`, Marken-Kontraste); es sieht **keine**
berechnete Farbe, keinen Accessible Name und keine ARIA-Beziehung.
`e2e/a11y-axe.spec.mjs` schließt genau diese Lücke – deterministisch, im echten
Chromium, gegen den lokalen Build.

## Warum das ein Gate ist und keine Kür

Für einen deutschen Finanzratgeber ist WCAG 2.1 AA kein Geschmack: Das
Barrierefreiheitsstärkungsgesetz (BFSG) verweist für
Verbraucher-Dienstleistungen darauf. Ein Kontrast, der „fast" reicht, ist
deshalb ein Befund wie ein toter Link – nicht eine Stilfrage.

Zwei Lehren aus dem ersten Lauf (26.10.2026) stehen im Code und sollen nicht
wieder verloren gehen:

1. **Prüfe die Wirkung, nicht das Attribut.** Ein Test, der
   `aria-labelledby` auf Existenz prüft, hält einen falschen Accessible Name
   für in Ordnung. Der Test gehört auf `toHaveAccessibleName(...)`.
2. **Kein Name-Override, wo der Inhalt reicht.** Ein `aria-label`, das den
   sichtbaren Text nicht enthält, verletzt WCAG 2.5.3 (Label in Name). Die
   Heilung ist fast immer: Override entfernen, Name aus dem Inhalt.

## Ausführen

```bash
npm ci --ignore-scripts
npm run browser:setup                 # gepinntes Chromium, siehe ANLEITUNG-CHROMIUM.md
HUGO_JSDELIVR_SHA=localdev hugo --minify --destination public
npm run suchindex                     # der neueste Artikel braucht den Index
npm run test:a11y:browser             # nur die A11y-Spec (Desktop + Mobile)
npx playwright test                   # volle Suite, so läuft es in CI
```

Die Spec läuft in **beiden** Playwright-Projekten: Kontrast, Tap-Ziele und
Fokus unterscheiden sich im 390-px-Layout real. Ein Gate, das nur Desktop
sieht, prüft die Hälfte der Leser nicht.

## Was geprüft wird

| Element | Quelle |
|---|---|
| WCAG-Tags | `wcag2a`, `wcag2aa`, `wcag21a`, `wcag21aa`, `wcag22aa` |
| Feste Seiten | `/`, `/werkzeuge/`, `/cockpit/`, `/suche/`, `/presse/`, `/ueber/`, `/impressum/`, `/datenschutz/` |
| Werkzeugseiten | **automatisch** alle Verzeichnisse unter `public/werkzeuge/` mit `index.html` |
| Ratgeber-Welten | **automatisch** alle Verzeichnisse unter `public/pillar/` mit `index.html` (seit 26.10.2026) |
| Artikel | der neueste Beitrag (`newestArticlePath`), damit die Masse des Bestands abgedeckt ist |
| Prüfwerkzeug | `axe-core` aus `devDependencies`, exakt gepinnt – **kein CDN, kein Netzaufruf im Test** |

Eine neue Werkzeugseite ist damit ohne Pflege im Gate. Die Spec prüft das
selbst: Weniger als neun gebaute Werkzeugseiten gelten als Befund. Dasselbe
gilt für die Ratgeber-Welten (mindestens sechs) – sie fehlten bis zum
26.10.2026 in der festen Liste, und genau dort stand der dritte Befund
derselben Klasse (68 Karten mit `aria-label="Weiterlesen: …"`).

Jeder Lauf hängt sein Roh-Ergebnis als `axe-<pfad>.json` an den Test – auch
bei Grün. Die Prüftiefe ist ein Beleg, kein Nebenprodukt.

## Ausnahmen: node-genau, begründet, mit Ablauf

Eine Ausnahme steht in `data/a11y/axe_ausnahmen.json` und braucht **alle**
Felder:

```json
{
  "regel": "label-content-name-mismatch",
  "seite": "*",                     // Pfad oder "*"
  "ziel": ".ff-brand",              // CSS-Ziel, Substring des axe-node.target
  "seit": "2026-10-26",             // JJJJ-MM-TT
  "pruefung": "2026-12-31",         // Ablauf: danach ist die Spec rot
  "grund": "…mindestens 20 Zeichen, warum das nicht heilbar ist…",
  "beleg": "docs/ANLEITUNG-A11Y-AXE.md"
}
```

Warum so streng: Eine Ausnahme auf eine **Regel** allein deckt jede künftige
Verletzung derselben Regel mit – das ist kein Tor, das ist eine offene Wand.
Deshalb wirkt sie nur auf `regel` + `ziel` + `seite`, und sie läuft ab.
Ein Eintrag ohne Grund, ohne Datum oder mit überschrittenem Prüftermin macht
die Spec rot.

**Ist-Stand 26.10.2026: `data/a11y/axe_ausnahmen.json` ist leer (`[]`).**
Die beiden Ausnahmen hinter dem Siegel (Marken-Link, Weiterlese-Karten) sind
eingespielt, das Siegel neu signiert und die Einträge gelöscht. Der Lauf ist
ohne Ausnahme grün – in beiden Playwright-Projekten. Wie das belegt wurde und
warum der Patch allein noch nicht reichte, steht unten unter „Ausnahmen in den
Bestand überführt".

## Ausnahmen in den Bestand überführt (26.10.2026)

Zwei Befunde lagen in gesiegelten Dateien (`layouts/_partials/header.html`,
`layouts/_partials/extend_post_content.html`). Beide sind geheilt, das Siegel
ist neu signiert, die Registry ist leer. Was dabei zusätzlich auffiel, ist der
eigentliche Wert dieser Runde:

### 1. Marken-Link – der Patch allein wäre auf dem Telefon rot geworden

Der `aria-label="FranksFinanzcheck – zur Startseite"` ist entfernt; der Name
kommt aus dem sichtbaren Descriptor „Unabhängige Fixkosten-Redaktion". Das
Logo bleibt `aria-hidden="true"`, `accesskey` und `title` unberührt.

**Falle:** `assets/css/extended/zzz-agency-polish.css` blendete den Descriptor
unter 768 px mit `display: none` aus. Damit war er auch aus dem
Accessibility-Tree – der Link hätte auf jeder Mobilseite **gar keinen** Namen
gehabt (`link-name`, critical). Die Mobile-Regel versteckt den Text jetzt
visuell (1×1-px-Technik), lässt ihn aber vorlesbar. WCAG 2.5.3 verlangt den
sichtbaren Text im Namen; zusätzlicher Text ist erlaubt.

### 2. Weiterlese-Karten – Name aus dem Inhalt

Der Override „Weiterlesen: <Titel>" verschwieg Datum, Kategorie und Anriss.
Nach dem Entfernen ist der Name die Summe der sichtbaren Kindtexte. Das ist
die robustere Variante: Sie kann nicht auseinanderlaufen, wenn sich eine Zeile
im Card-Layout ändert.

### 3. Dieselbe Klasse auf den Ratgeber-Welten (68 Karten)

`layouts/pillar/single.html` baute `.ff-pc-card` mit demselben Muster
(„Weiterlesen: <Titel>", sichtbar zusätzlich Anriss und „Jetzt lesen →").
Die feste Seitenliste der Spec kannte `/pillar/*` nicht – axe sah diese Seiten
nie. Deshalb: Override entfernt **und** die Ratgeber-Welten automatisch ins
Gate geholt. Der Zähler im `themenwelten_guard.py` zählt die Karten jetzt über
die Klasse, nicht über den entfernten Override – ein Gate darf seine Zahl
nicht aus dem Fehler ziehen, den es verhindern soll.

### 4. Zwei weitere Befunde, die erst durch die neue Abdeckung sichtbar wurden

| Befund | Seite | Heilung |
|---|---|---|
| `label` (critical) an sechs Aufgabenlisten-Kästchen | `/pillar/mietwagen/` | Gemeinsames Partial `layouts/_partials/aufgabenlisten_a11y.html` (eine Wahrheit für Artikel **und** Pillar-Seiten) |
| `scrollable-region-focusable` an der Entscheidungsmatrix | drei Ratgeber-Welten | `tabindex="0"` + `aria-label` an der Tabelle (PaperMod macht jede Tabelle zum Scrollcontainer), Fokusring aus dem Marken-Token |

### 5. Die dauerhafte Wache: `scripts/a11y_audit.py` prüft 2.5.3

axe sieht nur die besuchten Seiten. Das Audit liest **jede** gebaute Seite
und vergleicht für jedes `a`/`button` mit `aria-label` den deklarierten Namen
mit dem sichtbaren Text (Normalisierung: NFKC, Whitespace, Groß/Klein).
Damit ist die Fehlerklasse nicht nur an drei Stellen weg, sondern überall
detektierbar – auch auf künftigen Seiten ohne Spec-Eintrag.

Bewusste Grenzen, damit niemand sie überdehnt: `aria-labelledby` wird nicht
aufgelöst (dafür braucht es den Accessibility-Tree), und CSS-Sichtbarkeit über
Media Queries sieht nur der Browser. Genau diese Fälle deckt die
Playwright-Wirkungsprüfung (`toHaveAccessibleName`) zusätzlich ab.

### Nach dem Einspielen (Wiederholungsvorlage)

1. `data/integrity_lock.json` neu signieren (Inhaber, nicht Agent).
2. Einträge aus `data/a11y/axe_ausnahmen.json` **löschen** – nicht verlängern.
3. `python3 scripts/a11y_audit.py` (alle Seiten, statisch) **und**
   `npm run test:a11y:browser` (Chromium, beide Projekte) müssen grün sein.
   Bleibt ein Befund, ist der Patch unvollständig.

## Geheilt am 26.10.2026 (damit es nicht zurückkommt)

| Befund | Heilung | Warum so |
|---|---|---|
| `label-content-name-mismatch` auf Saison-/Themen-Karten | `aria-labelledby`-Overrides **entfernt** (`home_season.html`, `themenwelten.html`) | Ein erweiterter Override heilte nichts: axe nimmt den Namen aus dem Override, nicht aus dem Inhalt |
| `label-content-name-mismatch` am Pin-Knopf | `aria-label="Pin It – diesen Artikel auf Pinterest pinnen"` | Sichtbarer Text („Pin It") steckt jetzt im Namen |
| `color-contrast` in der Artikel-Kostenprofil-Leiste | `#687770` → `#5A6A63` in `zzz-agency-polish.css` | gemessen: 5.07:1 auf `#f5f1e8`, 5.71:1 auf Weiß (vorher 4.18:1 / 4.71:1) |
| `label` (critical) an deaktivierten Checkboxen in Aufgabenlisten | `aria-hidden="true" tabindex="-1"` per zeilenlokalem `replaceRE` in `artikel_einzeln.html` | Goldmark rendert `- [ ]` als `<input disabled>` ohne Label; die Checkbox ist reine Grafik. Mehrzeilige Muster sind im Haus verboten (ReDoS) |
| `link-in-text-block` | Unterstreichung für `.ff-entity-punkte a` / `.ff-entity-links a` in `zz-entity.css` | Farbe allein ist kein Unterscheidungsmerkmal (1.4.1) |
| `scrollable-region-focusable` | `tabindex="0"` an der Tabellen-Hülle (`render-table.html`) | Eine scrollbare Fläche muss per Tastatur erreichbar sein |
| `color-contrast` am Saison-Tipp-Label | Herbst `#8A4F0C` (5.23:1), Winter `#7A5C00` (4.93:1) in `data/saisons.yaml` | Kontrast gegen die **gerenderte** Fläche gemessen, inklusive `color-mix`-Tint – nicht gegen die Wunschfarbe |
| `label-content-name-mismatch` am Marken-Link | `aria-label` entfernt (`header.html`); Mobile-Regel versteckt den Descriptor nur noch visuell | Der Name kommt aus dem sichtbaren Text – und existiert auch im 390-px-Layout |
| `label-content-name-mismatch` an Weiterlese-Karten | `aria-label` entfernt (`extend_post_content.html`) | Datum, Kategorie und Anriss stehen sichtbar daneben; der Name ist die Summe dieser Texte |
| `label-content-name-mismatch` an 68 Pillar-Karten | `aria-label` entfernt (`pillar/single.html`), Ratgeber-Welten ins Gate | Dieselbe Klasse wäre sonst auf ungeprüften Seiten weitergewachsen |
| `label` (critical) an Aufgabenlisten-Kästchen auf Pillar-Seiten | `aufgabenlisten_a11y.html` für Artikel und Pillar-Seiten | Eine Wahrheit statt zweier Kopien derselben Zeile |
| `scrollable-region-focusable` an Entscheidungsmatrizen | `tabindex="0"` + `aria-label` an der Tabelle, Fokusring in `zzz-agency-polish.css` | Der PaperMod-Reset macht Tabellen scrollbar – ohne Tab-Stopp ist die Fläche für Tastatur unerreichbar |

## Grenzen (ehrlich benannt)

- Automatisierbar sind rund ein Drittel der WCAG-Kriterien. Tastaturführung,
  Verständlichkeit und Fehlermeldungsqualität decken die übrigen Specs und der
  Mensch ab. Ein grüner axe-Lauf ist **kein** BFSG-Nachweis.
- Geprüft wird der lokale Build, nicht die ausgelieferte Seite. Für die
  Wirklichkeit siehe `docs/ANLEITUNG-WEB-VITALS.md`.
- axe prüft den Zustand nach dem Laden. Zustände hinter Interaktion
  (aufgeklappte Menüs, Fehlermeldungen im Formular) decken die
  verhaltensbezogenen Specs ab.

## Abbruchbedingung

Der Lauf und die Heilung enden, wenn ein Befund **nur** durch eine Änderung an
einer gesiegelten Datei oder an `aria`-Overrides heilbar wäre, die den
sichtbaren Text verfälschen. Dann gilt: Patch hier dokumentieren, Ausnahme
registrieren (mit Ablauf), Inhaber informieren – **nicht** die Regel
abschalten und nicht die Signatur umgehen.
