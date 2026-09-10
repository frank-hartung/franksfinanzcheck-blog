# KURZFASSUNG: Kein „§“ mehr im ganzen Blog (Anker-Reparatur)

**Stand: 10.09.2026 · FranksFinanzcheck Lesehilfen**

Auftrag (Frank): *„Bei Kurzfassung wird im gesamten Blog immer ein ‚§‘
angezeigt … Bitte dauerhaft auf Premium-Level reparieren und optimieren.“*

Ergebnis: **Ursache gefunden, an der Wurzel behoben, blogweit verifiziert
(34 Artikel · 729 Überschriften) und mit einer eigenen Wache dauerhaft
abgesichert.** Der Abschnitts-Link bleibt als Komfortfunktion erhalten —
jetzt in einer Form, die Verlagshäusern entspricht.

---

## 1 · Der Befund

In der **Kurzfassung** stand hinter **jedem** Eintrag von „In diesem
Artikel“ ein „§“ — im gesamten Blog, z. B. im Artikel
[Tagesgeld-Zinsen 2026](https://franksfinanzcheck.de/posts/2026-08-26-tagesgeld-zinsen-2026-die-besten-zinssaetze-im-vergleich/).

Beweis von der Live-Seite (Überschrift, wie sie im DOM stand):

```
## Was ist Tagesgeld eigentlich? [#](#was-ist-tagesgeld-eigentlich)§
```

Das „§“ war **kein Redaktionszeichen**, sondern ein Bauteil der Seite,
das in jede Überschrift hineingerendert wurde.

### Folgeschäden, die vorher niemand sah

| Baustein | Auswirkung |
|---|---|
| **Kurzfassung → „In diesem Artikel“** | jeder Eintrag endete auf „§“ (gemeldeter Fehler) |
| **Kurzfassung → Tabellen & Übersichten** | Tabellen-Titel mit angehängtem „§“ |
| **Kurzfassung → „Kurzfassung kopieren“** | das „§“ landete im Klartext in Franks Zwischenablage |
| **Vorlesen** | die Engine normalisiert „§“ → „Paragraph“: der Sprecher sagte „… Paragraph“ |
| **Mini-Verzeichnis** | dort war das „§“ notdürftig weggeputzt — ein Symptom-Pflaster |
| **Screenreader (WCAG/BITV)** | der Überschriften-Name enthielt die Knopf-Beschriftung |
| **SEO** | Überschriften sind ein Ranking-Signal; Google rendert JS und las das „§“ mit |

## 2 · Die Ursache

`static/premium/ff-premium.js` → `addHeadingCopyButtons()` setzte den
Knopf „Link zu diesem Abschnitt kopieren“ **mit einem „§“ als Textknoten**
in jede Überschrift mit ID:

```js
button.innerHTML = '§';          // ← die Ursache
heading.appendChild(button);     // ← dadurch Teil des Überschriften-Texts
```

Der Knopf ist eine gute Funktion (Abschnitts-Link teilen). Als *Text* in
der Überschrift ist er jedoch ein Fremdkörper: Jede Auswertung, die
Überschriften-Text liest, bekommt ihn mit — die eigene Kurzfassungs-Engine
(`ff-voice.js`), die Mini-Navigation, Screenreader und Suchmaschinen.

**Warum die Wachen trotzdem grün waren:** Der Funktionstest baute die
Seite ohne das Premium-Skript; der Theme-Anker „#“ ist `aria-hidden` und
wurde herausgefiltert, das „§“ kam im Test gar nicht vor. Genau diese
Lücke ist jetzt geschlossen (Gruppe 13 lädt das **echte**
`ff-premium.js`).

## 3 · Die Reparatur (fünf Schichten)

| Schicht | Datei | Was jetzt gilt |
|---|---|---|
| **1 · Quelle** | `static/premium/ff-premium.js` | **Symbol statt Glyphe:** Inline-SVG (Link-Symbol, Bestätigung als Häkchen) — kein Textknoten mehr. `data-ff-skip-read` markiert den Knopf für Lesemaschinen. Der Überschriften-Text wandert in `.ff-heading-text`; `aria-labelledby` sorgt dafür, dass nur er die Überschrift beschriftet. |
| **2 · Browser-Engine** | `static/premium/ff-voice.js` | Neue Sperrliste `READ_SKIP_SELECTOR`: Buttons, Eingaben, `svg`, `[hidden]`, `[aria-hidden]`, `[data-ff-skip-read]`, `.anchor`, `.ff-heading-copy`, `.ff-mini-toc` werden beim Textlesen entfernt. Neue Funktion `headingTextOf()` liefert Überschriften-Texte sauber — für Inhaltsverzeichnis, Tabellen-Titel und Fortschrittsanzeige. |
| **3 · Tonspur (Server)** | `scripts/ff_voice_audio.py` | Gleiche Sperrliste serverseitig (`button`, `[hidden]`, `.anchor`, `.ff-heading-copy` …) plus Ankerschnitt am Überschriften-Ende — damit MP3-Tonspur und Browserstimme **wortgleich** bleiben (Parität). |
| **4 · Sicherheitsnetz** | `static/premium/ff-summary-safety.js` | Entfernt ein *angehängtes* Ankersymbol am Ende jedes Verzeichnis-Eintrags — falls je eine andere Erweiterung wieder ein Symbol in eine Überschrift schreibt. Ein echtes „§“ im Text („Rechte aus § 8 EinSiG“) bleibt unangetastet. |
| **5 · Gestaltung** | `assets/css/extended/z-premium-blog.css` | Icon-Größe zentriert, auf Touch-Geräten dezent sichtbar (`@media (hover: none)`), im Ausdruck ausgeblendet (`@media print`). |

**Ergebnis im DOM (vorher → nachher):**

```html
<!-- vorher -->
<h2 id="was-ist-tagesgeld-eigentlich">Was ist Tagesgeld eigentlich?<button class="ff-heading-copy">§</button></h2>

<!-- nachher -->
<h2 id="was-ist-tagesgeld-eigentlich" aria-labelledby="was-ist-tagesgeld-eigentlich-label">
  <span class="ff-heading-text" id="was-ist-tagesgeld-eigentlich-label">Was ist Tagesgeld eigentlich?</span>
  <button class="ff-heading-copy" type="button" data-ff-skip-read=""
          aria-label="Link zu diesem Abschnitt kopieren"><svg …></svg></button>
</h2>
```

## 4 · Premium-Optimierung des Abschnitts-Links

* **Kopieren mit Rückmeldung:** Link-Symbol → Häkchen, `aria-label`
  wechselt auf „Link kopiert“ (barrierefrei, 1,5 s).
* **Barrierefrei:** echter `<button type="button">`, per Tastatur
  erreichbar, sichtbarer Fokus, sinnvolle Beschriftung; die Überschrift
  selbst behält ihren redaktionellen Namen.
* **Mobil:** auf Touch-Geräten (kein Hover) bleibt der Knopf dezent
  sichtbar — der Abschnitts-Link ist damit auch unterwegs teilbar
  (Pinterest, WhatsApp, E-Mail).
* **Druck:** im Ausdruck unsichtbar.
* **Privacy:** kein Tracking, kein Netzwerkaufruf, alles First-Party.

## 5 · Verifikation (alle Suiten grün)

| Prüfung | Ergebnis |
|---|---|
| `node scripts/ff_voice_functional_test.mjs` (echte DOM, **neue Gruppe 13**) | **247/247** (vorher 218/218 — 29 Prüfungen neu) |
| `python3 scripts/heading_anchor_guard.py` (neue Wache) | **32/32** |
| `python3 scripts/ff_voice_toolbar_check.py` | **118/118** |
| `node scripts/ff_voice_repair_test.mjs` | **56/56** |
| `node scripts/ff_voice_tts_hardening_test.mjs` | **57/57** |
| `node scripts/ff_voice_voice_test.js` (Stimmen-Regie) | **69/69** |
| `python3 scripts/ff_voice_parity_check.py` (Tonspur ≡ Browserstimme) | **384/384** |
| `python3 scripts/ff_voice_audio.py --selftest` | **114/114** |
| Bestandslauf über alle echten Artikel | **34 Artikel · 729 Überschriften** — kein Verzeichnis-Eintrag endet auf ein Ankersymbol, kein Knopf trägt ein Textzeichen |
| Schutz vor Übereifer | „Rechte aus **§ 8 EinSiG**“ bleibt in Überschrift, Verzeichnis und Vorlesen erhalten |
| Manuelle Sichtprüfung | `tools/heading-anchor-preview/index.html` (Vorher/Nachher, echte Skripte) |

## 6 · Wachen — dauerhaft, nicht einmalig

1. **`scripts/heading_anchor_guard.py`** (neu, 32 Prüfungen) — prüft
   Quelle (kein „§“ als Inhalt/Text), Engine (Sperrliste,
   `headingTextOf`), Theme (Anker unsichtbar), **gebaute Seiten in
   `public/`** (keine Überschrift endet auf ein Ankersymbol) und die
   Verdrahtung von Test + Gate. Ein Fund → Exit 1.
2. **`.github/workflows/deploy.yml`** — die Wache läuft **nach dem
   Hugo-Build** gegen die echten Seiten; ein Fund stoppt den Deploy.
3. **`.github/workflows/lesehilfen-gate.yml`** — neue Auslöser für
   `ff-premium.js`, `ff-summary-safety.js`, `heading_anchor_guard.py`,
   `z-premium-blog.css`; Syntaxprüfung der Premium-Skripte und die Wache
   als eigener Schritt; dazu die tägliche Wache.
4. **Gruppe 13 des Funktionstests** — lädt das **echte** `ff-premium.js`
   gegen die echte DOM, prüft Knopf, Verzeichnis, Tabellen-Titel,
   Klartext-Kopie, Vorlesen-Blöcke, Mini-Verzeichnis und den
   Überschriften-Namen — und zusätzlich jeden echten Artikel.

## 7 · Geänderte Dateien

| Datei | Änderung |
|---|---|
| `static/premium/ff-premium.js` | Abschnitts-Knopf: Symbol statt „§“, `data-ff-skip-read`, `.ff-heading-text` + `aria-labelledby`, Häkchen-Bestätigung, sauberes Mini-Verzeichnis |
| `static/premium/ff-voice.js` | `READ_SKIP_SELECTOR`, `headingTextOf()` für Verzeichnis, Tabellen-Titel und Fortschritt |
| `static/premium/ff-summary-safety.js` | Sicherheitsnetz gegen angehängte Ankersymbole im Verzeichnis |
| `scripts/ff_voice_audio.py` | Serverseitige Sperrliste + Ankerschnitt (Parität zur Browser-Engine) |
| `assets/css/extended/z-premium-blog.css` | Icon-Gestaltung, Touch-Sichtbarkeit, Druck-Ausblendung |
| `scripts/heading_anchor_guard.py` | **neu** — Wache gegen Ankersymbole |
| `scripts/ff_voice_functional_test.mjs` | **Gruppe 13** (29 neue Prüfungen, inkl. Bestandslauf) |
| `.github/workflows/deploy.yml` | Wache nach dem Build |
| `.github/workflows/lesehilfen-gate.yml` | Auslöser, Syntaxprüfung, Wache |
| `tools/heading-anchor-preview/index.html` | **neu** — Vorher/Nachher-Vorschau mit echten Skripten |

## 8 · Beifund (mitrepariert): nichtdeterministische Tagesbilanz

Beim Abschluss des Pull Requests war die Suite **„Publication reliability
regression tests“ rot**. Der Fehler ist **nicht** durch die §-Reparatur
entstanden — er tritt auf dem Basis-Commit `a081c24` genauso auf:

```
FAIL: test_engine_snapshot_uses_final_source_truth
AssertionError: '2 Entwurf' not found in
'0 Artikel live heute (0 NEU · 0 recycelt · 0 Entwurf · 1 hold) | …'
```

**Ursache:** `engine_generate.tages_bilanz()` rechnete immer mit
`datetime.date.today()`. `bot_status.engine_snapshot(posts, today, …)`
übergab zwar einen Stichtag, dieser wurde aber ignoriert — die Bilanz
kam vom *Ausführungstag*, nicht vom *Auswertungstag*. Der Test war damit
an jedem Tag außer seinem Stichtag rot.

**Reparatur:** `tages_bilanz(..., today=None)` — ohne Angabe bleibt alles
beim Alten (heute); `bot_status.engine_snapshot()` übergibt seinen
Stichtag jetzt mit. Kein Verhalten für die Produktion geändert, nur die
Auswertung deterministisch gemacht.

| Prüfung | vorher | nachher |
|---|---|---|
| `python3 -m unittest discover -s scripts/tests` | 1 Fehler | **31/31 OK** |
| `engine_generate.py --selftest` | grün | grün |
| `cadence_guard.py --selftest` | grün | grün |
| `bot_status.py` (Schreiblauf) | grün | grün |
