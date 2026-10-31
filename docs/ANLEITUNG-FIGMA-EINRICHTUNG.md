# Figma einrichten – Schritt für Schritt

**Stand:** 31.10.2026 · **Dauer:** etwa 15 Minuten · **Voraussetzung:** ein
kostenloses Figma-Konto

Diese Anleitung führt dich von null bis zur fertigen Design-Datei. Du brauchst
dafür **kein** SDK, kein Terminal-Wissen und keine Zugangsschlüssel. Alles, was
du in Figma brauchst, liegt fertig im Repository.

> **Wichtig vorab:** Die Figma-Datei ist ein **Entwurfswerkzeug**. Sie ersetzt
> nicht den Blog. Produktionswahrheit bleiben `DESIGN.md`, das Regelwerk und der
> Hugo-Bestand. Nichts, was hier entsteht, geht automatisch live.

---

## Schritt 0 – Was du am Ende hast

| | |
|---|---|
| Seiten | 00 Cover · 01 Foundations · 02 Components · 03 Patterns · 04 Desktop · 05 Mobile · 90 Archive |
| Variablen | 4 Sammlungen: Primitives, Semantik (Hell/Dunkel), Abstand, Radius |
| Stile | 18 Textstile (Desktop **und** Mobil), 22 Farb-, 4 Schattenstile |
| Komponenten | 18 Sets mit den Achsen **Zustand × Modus** |

---

## Schritt 1 – Dateien bereitlegen (2 Minuten)

Du brauchst aus dem Repository genau **einen Ordner**:

```
figma/design-system-builder/
├── manifest.json   ← diese Datei wählst du in Figma aus
├── code.js         ← wird geladen, nicht angefasst
├── ui.html         ← wird geladen, nicht angefasst
└── source.js       ← Quelle des Plugins, für Figma nicht nötig
```

**Wichtig:** Alle drei Dateien (`manifest.json`, `code.js`, `ui.html`) müssen
zusammen im selben Ordner liegen. Sie dürfen **nicht** umbenannt oder einzeln
verschoben werden — `manifest.json` verweist auf die anderen beiden.

> **Es gibt bewusst kein ZIP im Repository.** Ein gepacktes Paket müsste bei
> jeder Plugin-Änderung neu gebaut und geprüft werden — eine zweite Wahrheit
> neben den Dateien. Lade stattdessen eine der beiden Quellen:

### Weg 1 – ganzes Repository als ZIP (empfohlen)

1. Repository auf GitHub öffnen:
   `https://github.com/frank-hartung/franksfinanzcheck-blog`
2. Oben links den Branch **`arena/42a7556c-franksfinanzcheck-blog`** wählen
   (nicht `main` — dort liegt das Plugin noch nicht).
3. Grüner Knopf **Code → Download ZIP**.
4. Entpacken. Du brauchst daraus nur den Ordner
   `figma/design-system-builder/` — kopiere ihn an eine Stelle, die du
   wiederfindest.

### Weg 2 – die drei Dateien einzeln herunterladen

Öffne auf GitHub den Ordner und lade jede Datei über den **Download-Knopf**
(⤓) herunter:

```
figma/design-system-builder/manifest.json
figma/design-system-builder/code.js
figma/design-system-builder/ui.html
```

Lege alle drei in **einen gemeinsamen Ordner**. Achtung: Manche Browser
speichern `code.js` als `code.js.txt` — prüfe die Dateiendung, sonst findet
Figma `main` nicht.

### Kontrolle, bevor es weitergeht

Im Ordner müssen genau diese drei Dateien liegen — Größen zum Abgleichen:

| Datei | Größe |
|---|---|
| `manifest.json` | ca. 0,4 KB |
| `code.js` | ca. 25 KB |
| `ui.html` | ca. 4,4 KB |

Stimmen die Größen grob, ist das Paket vollständig.

---

## Schritt 2 – Figma-Datei anlegen (1 Minute)

1. Öffne [figma.com](https://www.figma.com) und melde dich an.
2. **New design file** (im Dashboard oben rechts).
3. Benenne die Datei exakt: **`FranksFinanzcheck – Design System`**

Der Name ist kein Geschmack: Er steht so in `data/design/handoff.yaml` und
verbindet Datei und SSOT. Ein Tippfehler fällt später im Qualitäts-Gate auf.

> Du kannst auch eine **leere** Datei nehmen — die Startseite „Page 1“ wird
> später zur Seite `00 Cover`. Nichts wird gelöscht.

---

## Schritt 3 – Plugin importieren (2 Minuten)

1. Klicke oben links auf das **Figma-Menü** (☰) und wähle
   **Plugins → Development → Import plugin from manifest…**
   *Bei älteren Versionen: Plugins → Development → Import plugin from manifest.*
2. Wähle die Datei **`figma/design-system-builder/manifest.json`**.
   Figma zeigt eine Zusammenfassung: „FranksFinanzcheck – Design System“.
3. Mit **Import** bestätigen.

Das Plugin erscheint jetzt dauerhaft unter **Plugins → Development**. Du musst
das nur **einmal** machen.

> **Hinweis zu „Development“:** Das ist richtig und kein Zeichen für einen
> Entwurf. Ein Plugin, das nur dir gehört, läuft immer über diesen Weg. Eine
> Veröffentlichung im Figma-Community-Store ist weder nötig noch vorgesehen.

---

## Schritt 4 – Plugin starten (1 Minute)

1. **Plugins → Development → FranksFinanzcheck – Design System**
2. Es öffnet sich ein Fenster mit dem Titel **„FranksFinanzcheck Design System“**.
3. Oben steht, was gebaut wird, darunter der Knopf
   **„Design-System aufbauen“**.

Beim allerersten Start fragt Figma nach Zugriff. Das ist normal:

| Abfrage | Warum | Antwort |
|---|---|---|
| **currentpage** (Seitenwechsel) | Das Plugin legt Seiten an und wechselt dorthin | **Allow** |
| **textreview** (Schriften und Stile) | Es legt Text-, Farb- und Schattenstile an | **Allow** |

**Beide bestätigen.** Lehnt man eines ab, bricht der Aufbau ab — das Plugin
prüft das jetzt vorher und sagt es dir, statt eine halb gefüllte Datei zu
hinterlassen.

---

## Schritt 5 – Aufbauen (30 Sekunden)

1. Knopf **„Design-System aufbauen“** drücken.
2. Kurz warten (je nach Verbindung 5–30 Sekunden).
3. Das Protokoll erscheint im Plugin-Fenster:

```
✅ Design-System aufgebaut
Neu: 143
Bereits vorhanden: 0
Hinweise: 0
```

**So liest du das:**

| Zeile | Bedeutung |
|---|---|
| `Neu: 143` | So viele Objekte wurden angelegt |
| `Bereits vorhanden: …` | Diese gab es schon — nichts wurde doppelt angelegt |
| `Hinweise: …` | Meist fehlende Marken-Schrift, ersetzt durch Inter |

Das Plugin ist **wiederholbar**: Ein zweiter Lauf meldet `Neu: 0`. Du kannst es
also jederzeit erneut starten, ohne dass die Datei zumüllt.

---

## Schritt 6 – Das Ergebnis prüfen (5 Minuten)

Arbeite die sechs Seiten von links nach rechts durch:

### 00 Cover
Titel, Ziel und Stand der Datei, die Zahlen (Sammlungen, Variablen, Stile,
Komponenten) und die Herkunft. **Prüfe:** Steht dort das heutige Datum?

### 01 Foundations
Hier liegen die Variablen. Öffne rechts die Variablen-Ansicht
(*Lokale Variablen* im Panel „Design“):

- **Primitives** — die Rohwerte, ein Modus „Wert“
- **Semantik** — zwei Modi **Hell** und **Dunkel**. Klicke eine Rolle an:
  Der Wert ist ein **Alias** (z. B. `heading → emerald`), kein Hex-Wert.
- **Abstand** und **Radius** — Zahlenwerte, die Auto-Layout binden kann

**Prüfe den Dunkelmodus:** Rechtsklick auf einen Frame → *Variable modes* →
Sammlung „Semantik“ → **Dunkel**. Die Farben müssen wechseln.

### 02 Components
18 Komponenten-Sets. Jedes hat die Eigenschaften **Zustand** und **Modus**:

- `Standard`, `Hover`, `Fokus`, `Deaktiviert`, `Fehler`, `Erfolg` …
- `Modus = Hell | Dunkel`

**Prüfe eine Variante:** Wähle `Action/Button/Primary`, stelle auf
`Zustand = Fokus` — der Fokusring muss sichtbar sein.

### 03 Patterns · 04 Desktop · 05 Mobile
Die Seiten für den Entwurf. Sie sind bewusst **leer** angelegt: Hier zeichnest
du Layouts mit den Komponenten aus `02 Components`. Der Vertrag dafür steht in
`design/handoff/patterns.md` (Seitenrhythmus, Typo-Einsatz, Tiefe).

### 90 Archive
Ablage für Verworfenes. Nichts wird gelöscht, alles wird verschoben.

---

## Schritt 7 – Plugin-ID eintragen (1 Minute, einmalig)

Damit die Datei dauerhaft eindeutig zugeordnet ist:

1. **Plugins → Development → FranksFinanzcheck → Rechtsklick → „Manage plugin“**
   (oder Figma-Menü → Plugins → Development → *Manage plugins*).
2. Dort steht die **Plugin-ID** (eine lange Zeichenkette).
3. Trage sie in `data/design/handoff.yaml` ein:

```yaml
figma:
  dateiname: "FranksFinanzcheck – Design System"
  plugin_id: "1234567890123456789"   # ← hier eintragen
```

Du brauchst das nicht selbst zu machen — sag mir einfach die ID, dann trage ich
sie ein, lasse die Exporte neu erzeugen und die Prüfkette laufen.

**Warum das zählt:** Das Qualitäts-Gate meldet bis dahin eine Warnung **P8**
(„noch keine Figma-Plugin-ID“). Nach dem Eintragen sind **35 von 35**
Kriterien erfüllt.

---

## Schritt 8 – Nichts kaputt gemacht? Kurz prüfen

Wenn du den Handoff verändert hast (Tokens, Komponenten, Typografie), läuft die
Prüfkette so:

```bash
npm run figma:bauen            # Exporte + Plugin neu erzeugen
npm run design:handoff:check   # Drift?
npm run figma:sim              # Plugin real aufbauen (Simulator)
npm run figma:gate             # 35 Kriterien
npm run figma:selftest         # Sabotage-Proben
```

Erwartetes Ergebnis:

```
✅ Figma-/Relume-Handoff ist aktuell und regelkonform.
  Lauf 2: Neu 0 · vorhanden 143
  ✅ Aufbau vollständig, zweiter Lauf legt nichts an.
34/35 Kriterien erfüllt · 0 Fehler · 1 Warnung
```

Die eine Warnung ist **P8** — sie verschwindet mit Schritt 7.

---

## Wenn etwas nicht klappt

| Symptom | Ursache | Lösung |
|---|---|---|
| „Import plugin from manifest“ fehlt | Ansicht ist kein Design-File | Datei öffnen, nicht das Dashboard |
| `manifest.json` wird nicht akzeptiert | Datei einzeln kopiert | Alle drei Dateien im selben Ordner |
| Ich finde kein ZIP im Repository | Es gibt keins (Absicht) | Branch wählen, *Code → Download ZIP*; siehe Schritt 1 |
| Figma meldet „Cannot find main“ | `code.js` heißt `code.js.txt` | Dateiendung korrigieren |
| Ordner wirkt leer / nur `source.js` | Nur die Quelldatei geladen | `manifest.json`, `code.js` und `ui.html` dazunehmen |
| „⛔ Aufbau nicht gestartet – es fehlt der Zugriff“ | Zugriff abgelehnt | Plugin schließen, neu starten, **Allow** wählen |
| Aufbau bricht mittendrin ab | Figma-Version zu alt | Figma aktualisieren (Desktop-App oder Browser) |
| „Hinweise: 1“ und Inter statt Playfair | Marken-Schrift fehlt lokal | Playfair Display installieren; Inter ist der dokumentierte Ersatz |
| Farben wechseln nicht im Dunkelmodus | Frame-Modus nicht gesetzt | Rechtsklick → *Variable modes* → Semantik → Dunkel |
| Protokoll meldet `Neu: 0` beim ersten Lauf | Datei war schon gefüllt | Kein Fehler — es wurde nichts doppelt angelegt |
| Komponenten sehen leer aus | Textstile brauchen Schriften | Schriften laden lassen, Plugin einmal neu starten |

---

## Was du bewusst **nicht** brauchst

- **Kein Tokens-Studio-Plugin.** Der Weg ist optional (Weg B in
  `ANLEITUNG-FIGMA-RELUME-HANDOFF.md`), wenn du die Tokens von Hand
  nachvollziehen willst. Für den normalen Aufbau reicht das eigene Plugin.
- **Kein Personal Access Token, keine Plugin-ID im Voraus, kein API-Key.**
  Nichts davon gehört ins Repository — und nichts davon wird gebraucht.
- **Kein Netzwerk.** Das Plugin hat `allowedDomains: ["none"]`. Es sendet
  nichts, lädt nichts nach, veröffentlicht nichts.

---

## Der ehrliche Hinweis zum Schluss

Das Plugin ist gegen eine **nachgebildete** Figma-API getestet
(`scripts/tests/figma_plugin_sim.mjs`): Aufbau, Zahlen und Wiederholbarkeit
sind belegt. Was ein Test nicht kann, ist ein Blick auf die gerenderte Datei.
Wenn dir auf einem der sechs Schritte etwas unrund vorkommt — Abstände,
Schriftgrößen, ein fehlender Zustand —, sag es mir mit der Seitenzahl. Das ist
dann ein Befund am Handoff, und der lässt sich an der SSOT beheben, nicht durch
Herumklicken in Figma.
