---
name: ff-oberflaeche
description: "Benutzen bei jeder Oberfläche dieses Blogs: CSS, Farbe, Theme, Dark Mode, Kontrast, Layout, Typografie, Variante, Figma oder Relume, Templates/Shortcodes, JavaScript im Browser, Rechner-/Werkzeug-Formular, Service Worker, localStorage, Newsletter-Anmeldung, Artikel-Navigation (TOC), Lighthouse/Web Vitals, A11y, '_headers'/Caching, 'die Farbe ändert nichts', 'im Dark Mode unsichtbar', 'ein Knopf tut nichts'. Dieser Skill enthält den Design-Vertrag (PRODUCT.md/DESIGN.md, Varianten statt Basis, keine Inline-Farben, Handoff), die Laufzeit-Robustheit und die Produktzusage der Werkzeuge. Nicht für Text/Sprache (ff-marke-text) und nicht für Gate-Bau (ff-pruefen)."
metadata:
  version: 1.0.0
  besitz: repo-eigen – kein Eintrag in skills-lock.json, nie von `npx skills update` anfassen
  quelltext: CLAUDE.md-Kernregeln, wörtliche Details in references/
---

# Oberfläche: gemessen, signiert, nie stumm

Ein UI-Fehler dieses Blogs kostet nicht nur Optik, sondern Vertrauen: ein
Rechner, der nicht rechnet, ein Knopf, der nichts tut, eine Farbe, die im Dark
Mode verschwindet. Deshalb ist hier jede Oberflächenarbeit an **drei** Dinge
gebunden: Tokens aus `PRODUCT.md`/`DESIGN.md`, eine Messung, und – bei
Layout-Umbauten – eine Variante mit menschlicher Freigabe. Alles hier ist
wörtlich aus `CLAUDE.md` übernommen.

## Wann dieser Skill zählt

- Du änderst eine Farbe, einen Abstand, eine Schrift, ein Template, ein `static/premium/*.js`.
- Du baust ein neues Werkzeug, eine neue Seite oder ein interaktives Formular.
- Ein Entwurf kommt aus Figma/Relume oder aus `design/handoff/`.
- Ein Befund nennt Kontrast, CLS, Head-Kinder, DOM-Budget, `inline style` oder
  „Funktion tut nichts“.

## Die harten Kernregeln

1. **Skills zuerst:** `impeccable` (UI entwerfen/polieren/auditieren – liest
   `PRODUCT.md` + `DESIGN.md` zuerst), `web-design-guidelines` (Review gegen
   Web Interface Guidelines), `frontend-design` (neue visuelle Identität),
   `design-taste-frontend` (Anti-Slop), `webapp-testing` (Browser-Interaktion).
   Diese fünf stehen im Kern-Router, weil sie jeden UI-Auftrag angehen.
2. **`PRODUCT.md` und `DESIGN.md` lesen, bevor eine Farbe geändert wird.**
3. **Layout-Umbauten gehören in eine Variante, nicht in die Basis:**
   `assets/css/varianten/<id>.css` + Eintrag in `data/design/varianten.yaml`,
   messen, Mensch zur Freigabe. Direkt in `assets/css/extended/` schreiben heißt:
   ohne Messung und ohne Unterschrift deployen.
4. **Dark Mode mitdenken:** `defaultTheme: auto` → jede Farbe braucht eine
   `:root[data-theme="dark"]`-Variante. Kontraste messen mit
   `node e2e/design-metrics.mjs`.
5. **Keine Inline-Farben in Templates** – Klassen + CSS-Dateien
   (Vorbild: `.ff-pc-*` in `layouts/pillar/single.html`).
6. **Figma/Relume nur über den Handoff-Vertrag**, generierte Dateien nie von
   Hand ändern; ohne Figma ist `design/handoff/design-system.html` gleichwertig.
7. **Ein gefangener Fehler ist erst behoben, wenn der Leser weiß, woran er
   ist.** Fangnetz je Instanz (`FFRobust.insel`), Ausfall in einem Markensatz
   mit `role="status"`, jeder Netzaufruf über `FFRobust.hole`, Storage nur mit
   Fangnetz, kein `innerHTML` aus Text, kein `eval()`. `robustheits_gate.py`
   heilt nie selbst.
8. **Kein zusätzliches `<head>`-Kind:** der Robustheit-Bootstrap hängt im
   vorhandenen Consent-Skript (58 Head-Kinder sind die Lighthouse-Grenze).
9. **Skripte und Markup sprechen über `data-`-Hooks, nie über Klassen** – und
   die Werkzeuge halten ihre Zusage: vollständig nutzbar ohne Affiliate-Klick.

## Katalog

Die fünf Basissätze (Skills zuerst, Tokens lesen, Variante statt Basis, Dark
Mode, keine Inline-Farben, Handoff-Vertrag) stehen **wörtlich im Kern** unter
„Verhalten beim UI-/Design-Arbeiten“ – sie gelten bei jedem Auftrag und haben
deshalb keinen zweiten Text hier.

| Deine Frage | Antwort im Detail |
|---|---|
| Wie laufen Variante, Messung und Freigabe im Detail, was prüft `figma_quality_gate.py`? | `CLAUDE.md` §UI/Design + `docs/ANLEITUNG-DESIGN-VARIANTEN.md`, `docs/ANLEITUNG-FIGMA-RELUME-HANDOFF.md` |
| Wie baue ich ein Fangnetz, was verbietet R1–R13, wie altern Ausnahmen? | `references/robustheit.md` (C31, #740-Ausnahme `head.html`) |
| Was macht ein Werkzeug zum Produkt, welche Zusage ist hart, wie sitzen die `_headers`? | `references/produkte-und-header.md` (W1–W7, S1/S2) |

## Kommando-Notausgang

```bash
node e2e/design-metrics.mjs                  # Kontrast hell + dunkel, JSON
python3 scripts/robustheits_gate.py --source-only     # Laufzeit-Fangnetze ohne Hugo (< 1 s)
npm run werkzeuge:check                      # W1–W7: Quelle + Build + public/
npm run test:toc                             # „Im Artikel“-Navigation, V1–V14
npm run test:a11y:browser                    # axe-core im gerenderten DOM (WCAG AA)
python3 scripts/design_handoff.py --check    # Marken- und Exportdrift
```

## Nicht zuständig für

- **Was in den Text gehört, Kennzeichnung, Snippet-Grenzen** → `ff-marke-text`
- **Ob der Build liefert oder blockiert** → `ff-ausliefern`
- **Wie der zugehörige Test gebaut ist** → `ff-pruefen`
