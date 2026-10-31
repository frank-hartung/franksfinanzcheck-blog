# FIGMA-HANDOFF-UND-DESIGN-SKILLS-HIGHEND-2026-10-31

**Datum:** 31.10.2026 · **Umfang:** Figma-Handoff, Figma-Plugin, Qualitäts-Gate,
beide Design-Skills · **Status:** produktionsreif im Repository

## Kurzurteil

Der Blog hatte seit 26.09.2026 einen **korrekten, aber statischen** Figma-/Relume-
Handoff: Tokens als JSON, ein Brief, ein Inventar, ein Hash-Manifest. Das war
sauber – aber es war eine *Beschreibung* von Figma, keine Datei, die in Figma
existiert. Wer den Handoff öffnete, hielt JSON in der Hand und musste alles von
Hand nachbauen. Genau dort entsteht der Unterschied zwischen „vorhanden“ und
„Highend einer Profi-Agentur“: Ein Agentur-Handoff ist **ausführbar**.

Zusätzlich lagen die beiden Design-Skills unvollständig und mit falschen Hashes
im Repository: `impeccable` war 4.3.1 (Upstream: 4.8.0), ihm fehlten sieben
Referenzen und die halbe Live-Engine; `design-taste-frontend` war eine einzelne
Markdown-Datei ohne die 11 Referenzen, ohne Richtungsbibliothek und ohne die
Werkzeuge `lint.mjs`, `draw.mjs`, `inspect.mjs`. Beide Hash-Werte in
`skills-lock.json` stimmten nicht mit den Dateien überein.

## Was jetzt anders ist

### 1. Die Skills sind die echten Skills

| | vorher | jetzt |
|---|---|---|
| `impeccable` | 4.3.1, 56 Dateien, veraltete Engine 0.1.5 | **4.8.0**, Engine **0.1.18**, 63 Dateien, 40 Referenzen, 5 Agenten |
| `design-taste-frontend` | 1 Datei, 1206 Zeilen | **taste-skill v2**, 39 Dateien, 11 Referenzen, Bibliothek mit 20 Richtungen, `lint.mjs` / `draw.mjs` / `inspect.mjs` |
| Pinning | Hash falsch, kein Commit | Upstream-**Commit**, Version, Baumzahl, SHA-256 – geprüft vom Gate |

### 2. Der Handoff ist ausführbar geworden

**`figma/design-system-builder/`** ist ein installierbares Figma-Plugin, das die
Datei *baut*: 7 Seiten, 4 Variablen-Sammlungen (Primitives, Semantik mit
Hell/Dunkel-Aliasen, Abstand, Radius), Dev-Mode-Syntax `var(--ff-…)`,
18 Textstile (Desktop **und** Mobil), 22 Farbstile, 4 Schattenstile und
18 Komponenten-Sets mit den Achsen **Zustand × Modus**.

- **Generiert, nicht geschrieben:** `source.js` + Datenblock → `code.js`.
  Die SSOT bleibt `data/design/handoff.yaml`; ein Platzhalter ist der einzige
  Kopplungspunkt.
- **Ohne Netz:** `allowedDomains: ["none"]`. Kein `fetch`, kein `require`.
- **Idempotent, bewiesen:** Der zweite Lauf meldet **„Neu: 0“** und 143
  übersprungene Objekte. Bewiesen nicht durch Zusehen, sondern durch
  `scripts/tests/figma_plugin_sim.mjs`, das die Figma-API nachbildet.

### 3. Die SSOT beschreibt jetzt die Wirklichkeit

Vorher enthielt sie drei erfundene bzw. falsche Angaben, die das neue Gate
sofort gefunden hat:

- `.ff-newsletter-form` **existiert nicht** im CSS (echt ist `.ff-nl__form`).
- `.ff-spar-matrix-table` **existiert nicht** (echt ist `.ff-spar-matrix-*`).
- `.header` fehlte der Beleg, `.skip-link` der Dark-Zustand.

Neu dazu: vollständige **Typo-Skala mit Mobilwerten** (h1_home, h1_article, h2,
h3, lead, body, meta, label, subline), **Schatten-Skala**, **Abstands- und
Radius-Sammlungen**, Rollen für Sekundärtext, Fehler- und Erfolgsfarbe sowie
18 statt 8 Komponenten – jede mit CSS-Beleg und Rollenbindung.

### 4. Drei Prüfungen, die es vorher nicht gab

| Prüfung | Was sie fängt |
|---|---|
| `pruefe_css_vertrag` im Generator | Jede Komponente muss im echten CSS vorkommen – erfundene Klassen brechen den Build. |
| Typo-Kohäsionsregel | Überschriften dürfen per `clamp()` fließen; Fließtext, Meta und Labels nicht unter 85 % fallen. |
| `scripts/figma_quality_gate.py` | **35 Kriterien** über fünf Ebenen: SSOT, Exporte, Plugin, Skills, Doku. |

### 5. Neue Artefakte, die ein Agentur-Handoff ausmachen

- **`design/handoff/patterns.md`** – Muster statt Bauteile: Seitenrhythmus,
  Typo-Einsatz, Tiefe, und die acht Dinge, die das System niemals tut.
- **`design/handoff/ANNOTATIONEN.md`** – **gerechnete** WCAG-2.2-Kontrast-Matrix
  (24 Paarungen, Hell und Dunkel, alle ≥ 4,5:1) plus Pflichtzustände je Typ.
- **`design/handoff/spezifikation.html`** – eine Seite, die das System aushält:
  Swatches, Rollen beider Modi, Typo-Proben, Raster, Tiefe, Kontrastgrenze.
  Kein Build nötig, einfach öffnen.

## Prüfkette

```bash
npm run figma:bauen          # Exporte + Plugin neu erzeugen
npm run design:handoff:check # Drift
npm run figma:sim            # Plugin real aufbauen (Simulator), Idempotenz
npm run figma:gate           # 35 Kriterien
npm run figma:selftest       # Sabotage-Proben beider Werkzeuge
npm run skill:lint           # Tells-Scan gegen assets/ und layouts/
```

Ergebnis: **34/35 erfüllt, 0 Fehler, 1 Warnung** – die Warnung ist **P8**
(„noch keine Figma-Plugin-ID“) und verschwindet, sobald das Plugin einmal in
Figma importiert und die vergebene ID in `figma.plugin_id` eingetragen ist.
Sie ist bewusst eine Warnung: Eine ID, die es vor dem ersten Import nicht geben
kann, darf kein rotes Gate erzeugen.

67 Regressionstests (27 neu) laufen grün, darunter Sabotage-Proben, die
beweisen, dass das Gate echte Lücken fängt: manipulationsfreie Manifeste,
verfälschte Kontrastzeilen und erfundene CSS-Klassen werden erkannt.

## Was ein Mensch tun muss

Figma-Dateien und Plugin-Installationen lassen sich ohne Konto nicht anlegen –
das bleibt eine Handlung des Kontoinhabers, bewusst ohne SaaS-Token im Repo.
Der Ablauf steht vollständig in `docs/ANLEITUNG-FIGMA-RELUME-HANDOFF.md`
(Weg A = Plugin, Weg B = manuell über Tokens Studio).

## Grenzen, ehrlich benannt

1. Das Plugin ist gegen eine **nachgebildete** Figma-API geprüft, nicht gegen
   Figma selbst. Die Simulation deckt Aufbau, Zahlen und Idempotenz ab; sie
   ersetzt keinen Blick auf die gerenderte Datei.
2. Die Kontrast-Matrix prüft **Token-Paarungen**, nicht gerenderte Flächen.
   Die gerenderte Messung bleibt bei `node e2e/design-metrics.mjs`.
3. Die Skills werden gepinnt und in ihrer Integrität geprüft, aber ihr Wert
   entsteht erst im Einsatz. `skill:lint` liefert dafür den statischen Tells-Scan.
