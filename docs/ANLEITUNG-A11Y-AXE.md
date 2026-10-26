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
| Artikel | der neueste Beitrag (`newestArticlePath`), damit die Masse des Bestands abgedeckt ist |
| Prüfwerkzeug | `axe-core` aus `devDependencies`, exakt gepinnt – **kein CDN, kein Netzaufruf im Test** |

Eine neue Werkzeugseite ist damit ohne Pflege im Gate. Die Spec prüft das
selbst: Weniger als neun gebaute Werkzeugseiten gelten als Befund.

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

## Zwei Befunde hinter dem Siegel (Stand 26.10.2026)

Beide Dateien stehen in `data/integrity_lock.json`. Eine Änderung daran
braucht die **Neu-Signatur des Inhabers**; ein Agent darf sie nicht nebenbei
erteilen. Bis dahin sind die zwei Knoten als Ausnahme registriert (Ablauf
2026-12-31). Die Patches sind fertig – sie müssen nur von befugter Hand
eingespielt und signiert werden.

### 1. `layouts/_partials/header.html` – Marken-Link

Sichtbar ist „Unabhängige Fixkosten-Redaktion", im `aria-label` fehlt dieser
Text (WCAG 2.5.3). Der Name soll aus dem Inhalt kommen:

```diff
-            <a href="{{ "" | absLangURL }}" accesskey="h" title="{{ $label_text }} (Alt + H)"
-               class="ff-brand" aria-label="FranksFinanzcheck – zur Startseite">
+            <a href="{{ "" | absLangURL }}" accesskey="h" title="{{ $label_text }} (Alt + H)"
+               class="ff-brand">
```

Das Logo bleibt `aria-hidden="true"` – der Name kommt dann aus dem
Descriptor-Text, und der ist sichtbar. `accesskey` und `title` bleiben
unberührt.

### 2. `layouts/_partials/extend_post_content.html` – Weiterlese-Karten

Der Override „Weiterlesen: <Titel>" verschweigt Datum, Kategorie und Anriss,
die sichtbar daneben stehen:

```diff
-    <a href="{{ .Permalink }}"
-       aria-label="Weiterlesen: {{ .Title | plainify }}"
-       class="ff-related-card">
+    <a href="{{ .Permalink }}" class="ff-related-card">
```

Danach ist der Name die Summe der sichtbaren Kindtexte (Kategorie, Datum,
Titel, Anriss). Genau das verlangt 2.5.3 – und es ist die robustere Variante:
Sie kann nicht wieder auseinanderlaufen, wenn sich eine Zeile im Card-Layout
ändert.

### Nach dem Einspielen

1. `data/integrity_lock.json` neu signieren (Inhaber, nicht Agent).
2. Beide Einträge aus `data/a11y/axe_ausnahmen.json` **löschen**.
3. `npm run test:a11y:browser` – muss ohne Ausnahme grün sein. Bleibt ein
   Befund, ist der Patch unvollständig, nicht die Ausnahme zu verlängern.

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
