# Figma einrichten – und der Weg ohne Figma

**Stand:** 31.10.2026 · **Gilt für:** `main` ab `22a19c6` · **Prüfkette:** 36 Kriterien, 71 Tests, 1 Simulation

Diese Anleitung führt in zwei Spuren. **Beide enden beim selben Ergebnis.**
Figma ist eine Option, keine Voraussetzung: Wer kein Figma hat oder es nicht
einrichten will, öffnet `design/handoff/design-system.html` und hat Farben,
Typografie, Abstände, Komponenten, Kontraste und Muster – vollständig, lokal,
ohne Netz, ohne Anmeldung.

> **Die kurze Antwort für Eilige:** Ohne Figma brauchst du nichts zu tun.
> Die Datei ist erzeugt und liegt im Repository. Aufmachen, prüfen, fertig.

---

## 1. Was hier eigentlich entsteht

Das Design lebt an genau einer Stelle im Repository: `data/design/handoff.yaml`
(SSOT). Alles andere ist daraus abgeleitet und trägt einen Hash:

| Datei | Wofür | Wer liest sie |
|---|---|---|
| `data/design/handoff.yaml` | Die Quelle: Farben, Rollen, Typo, Abstände, 19 Komponenten, Sitemap | Generator, Figma-Plugin, Menschen |
| `data/design/regelwerk.yaml` | Leitplanken: erlaubte Farben, Radien, A11y-Budgets | Marken-Gate |
| `design/handoff/design-system.html` | **Der Figma-freie Weg.** Ansehen und prüfen im Browser | Menschen, Kunden, Agentur |
| `design/handoff/spezifikation.html` | Druckreife Spezifikation, ebenfalls lokal | Agentur, Entwicklung |
| `design/handoff/figma-tokens.tokens.json` | Tokens-Studio-Import (Hell + Dunkel) | Figma |
| `design/handoff/component-inventory.md` | Figma-Name ↔ CSS-Klasse ↔ Zustände ↔ A11y | Entwicklung |
| `design/handoff/ANNOTATIONEN.md` | Kontrast-Matrix, gerechnet nach WCAG 2.2 | A11y, Kunde |
| `design/handoff/patterns.md` | Musterbibliothek: wann was, was nie | Entwurf |
| `design/handoff/relume-project-brief.md` | Kopierfertiger Relume-Prompt | Relume |
| `design/handoff/handoff-manifest.json` | SHA-256 je Datei – der Beweis, dass alles zur Quelle passt | Prüfkette |
| `figma/design-system-builder/` | Plugin: baut Variablen, Stile, Komponenten in **einer** Datei | Figma |

Eine Änderung ist immer derselbe Dreisatz:

```bash
# 1. Quelle ändern (data/design/handoff.yaml), 2. erzeugen, 3. prüfen
python3 scripts/design_handoff.py
python3 scripts/figma_quality_gate.py
```

`design/handoff/*` niemals von Hand bearbeiten. Es wird beim nächsten Lauf
überschrieben – und die Prüfkette meldet es vorher (P27, P29).

---

## 2. Spur A – ohne Figma (der gleichwertige Weg)

1. `design/handoff/design-system.html` im Browser öffnen (Doppelklick genügt;
   die Datei bringt ihr CSS mit und lädt nichts nach).
2. Oben rechts **Hell / Dunkel** umschalten. Beide Modi sind vollständig –
   12 semantische Rollen, dieselben in beiden Modi.
3. Abschnitte: Farben · Typografie (Desktop **und** Mobilwert) · 19 Komponenten
   mit CSS-Klasse und Zuständen · Abstände · Kontrast-Matrix.
4. `design/handoff/spezifikation.html` daneben öffnen: dieselben Werte in
   druckbarer Form, plus Komponenten-Register.

**Was du damit tun kannst, ohne Figma zu besitzen:** Marke prüfen, Abstimmung
mit Kunden, Entwicklung briefen, Kontraste belegen, Komponenten benennen,
Abstände nachschlagen. Das ist der komplette Handoff-Inhalt.

**Was du ohne Figma nicht bekommst:** einen klickbaren Prototyp. Wenn ein
Kunde den braucht, ist das eine eigene Aufgabe – kein Bestandteil dieses
Handoffs.

---

## 3. Spur B – mit Figma (optional)

### 3.1 Plugin einmalig importieren

1. Figma → Menü **Plugins → Development → Import plugin from manifest…**
2. `figma/design-system-builder/manifest.json` auswählen.
3. Fertig. Das Plugin erscheint unter **Plugins → Development**.

**Wenn der Import abbricht:** Das Manifest trägt bewusst **kein** `id`-Feld.
Ein leeres `"id": ""` ist die häufigste Ursache für einen stummen Abbruch.
Wird trotzdem eine ID verlangt, im Figma-**Desktop**-Client
„Plugins → Development → New plugin“ wählen, dort „Generate ID“ – und die ID
**nicht ins Repository schreiben**, sondern in `handoff.yaml → figma.plugin_id`
(bewusst leer lassen, sie ist maschinenlokal).

### 3.2 Design-System bauen

1. Neue Datei anlegen, Name: **FranksFinanzcheck – Design System**
   (aus `handoff.yaml → figma.dateiname`).
2. Plugin starten → **„Design-System aufbauen“**.
3. Das Plugin legt an: 7 Seiten in der dokumentierten Reihenfolge,
   4 Variablen-Sammlungen (Primitives · Semantik · Abstand · Radius),
   54 Variablen, 18 Textstile (Desktop + Mobil), 22 Farbstile, 4 Schattenstile,
   19 Komponenten-Sets mit Zustand × Modus, ein Cover mit Stand und Zahlen.

Beim **zweiten** Lauf passiert nichts Doppeltes: Das Plugin liest den Bestand
und meldet „Neu: 0 · Bereits vorhanden: 144“. Dieselbe Zusage prüft
`node scripts/tests/figma_plugin_sim.mjs` bei jedem Pull Request.

### 3.3 Fehlende Rechte – was dann zu tun ist

Das Plugin prüft **vor** dem Aufbau, was es darf, und bricht lieber ab, als
halb zu bauen. Meldung `⛔ …` im Plugin-Fenster:

| Meldung enthält | Ursache | Lösung |
|---|---|---|
| `currentpage` | Seitenwechsel nicht erlaubt | Plugin neu starten; Figma-Desktop statt Browser |
| `textreview` | Schriften/Stile nicht lesbar | Datei neu laden, Plugin erneut starten |
| `dynamic-page` | Manifest veraltet | `python3 scripts/design_handoff.py` |

Ein Abbruch hinterlässt nichts Halbes: Es wird **keine** Seite und **keine**
Variable angelegt, bevor die Rechte feststehen.

### 3.4 Tokens-Studio-Weg (Alternative zum Plugin)

Wer Tokens Studio nutzt, statt das Plugin zu bauen:
`design/handoff/figma-tokens.tokens.json` importieren. Es enthält zwei Themes
(Hell/Dunkel), Primitives und Semantik als echte Alias-Ketten. Der Unterschied
zum Plugin: Tokens Studio legt Variablen an, aber keine Komponenten.

---

## 4. Die Prüfkette (warum du dem Handoff trauen kannst)

```bash
python3 scripts/design_handoff.py --selftest        # Generator + Verträge
python3 scripts/design_handoff.py --check           # Drift gegen die Quelle
python3 scripts/figma_quality_gate.py               # 36 Kriterien
python3 scripts/figma_quality_gate.py --selftest    # Gate gegen sich selbst
node    scripts/tests/figma_plugin_sim.mjs          # Plugin ohne Figma
python3 -m unittest scripts.tests.test_figma_handoff scripts.tests.test_design_varianten
```

Das Gate prüft nicht „existiert eine Datei?“, sondern: Steht in der Datei noch
das, was die Quelle hergibt? Beispiele:

- **P14** – Jede dokumentierte CSS-Klasse muss im ausgelieferten CSS existieren.
  Ein Inventar, das Klassen erfindet, ist eine Fiktion mit Tabellenformat.
- **P24** – Jede Kontrastzeile braucht einen gerechneten Wert. Eine Tabelle
  ohne Zahlen sieht aus wie ein Nachweis und ist nur eine Behauptung.
- **P27** – SHA-256 je Artefakt. Weicht ein Hash ab, ist die Datei veraltet.
- **P33** – Das Plugin wird gegen eine nachgebaute Figma-API ausgeführt, inklusive
  Rechte-Abbruch und „zweiter Lauf legt nichts an“.
- **P36** – Die Prüfkette hängt im Workflow. Ein Gate, das nur lokal läuft,
  ist eine private Meinung.

**Ehrliche Grenzen:** Das Gate prüft Token-Paarungen und Verträge, nicht
gerenderte Pixel. Ob ein Fokusring im Browser wirklich sichtbar ist, entscheidet
`e2e/design-metrics.mjs`. Und die Plugin-Simulation bildet die Figma-API nach –
sie ersetzt keinen Blick in eine echte Datei.

---

## 5. Wenn etwas nicht stimmt

| Symptom | Ursache | Behebung |
|---|---|---|
| `--check` meldet Drift | Quelle geändert, nicht neu erzeugt | `python3 scripts/design_handoff.py` |
| Gate P14 rot | Klasse im CSS umbenannt | `code`-Feld in `handoff.yaml` korrigieren |
| Gate P6 rot | Rolle nur in einem Modus | Rolle in beiden Modi definieren |
| Gate P31 rot | `id` im Manifest | Feld entfernen; ID gehört in `handoff.yaml` |
| Gate P34/P36 rot | Anleitung oder Workflow fehlt | Datei wiederherstellen, Schritte ergänzen |
| Plugin baut doppelt | `code.js` veraltet | `python3 scripts/design_handoff.py` |
| Kontrast unter 4,5:1 | Farbe geändert | Token in `regelwerk.yaml` prüfen lassen |

Nichts davon erfordert Figma. Alles davon ist im Repository nachvollziehbar.
