# KURZFASSUNG: „§“ dauerhaft entfernt — Kurzfassung, Klartext & Vorlesen (Issue #248)

**Stand: 10.09.2026 · FranksFinanzcheck Lesehilfen · Fertigstellung auf Premium-Level**

Auftrag (Frank, Issue #248): *„‚§‘ in Kurzfassung, Klartext und Vorlesen
dauerhaft entfernt — bitte dauerhaft auf Premium-Level reparieren und
optimieren.“*

Ergebnis: **Der „§“ ist an der Wurzel entfernt (kein Textknoten mehr im
DOM), die drei betroffenen Oberflächen sind blogweit verifiziert (34
Artikel) und fünf Wälle + drei Wachen machen die Reparatur dauerhaft —
inklusive Beweis, dass sogar eine künftige, feindliche „§“-Injektion
wirkungslos bleibt.**

Dieser Report dokumentiert den **Endzustand** aus Grund-Reparatur
(PR #250, gemergt) und der Härtung aus diesem PR (Issue #248).

---

## 1 · Der Befund (10.09.2026)

Im gesamten Blog zeigte die **Kurzfassung** an **jeder Gliederung** ein
**„§“** — z. B. im Artikel
[Tagesgeld-Zinsen 2026](https://franksfinanzcheck.de/posts/2026-08-26-tagesgeld-zinsen-2026-die-besten-zinssaetze-im-vergleich/).
Betroffen waren alle drei Lese-Oberflächen:

| Oberfläche | Auswirkung |
|---|---|
| **Kurzfassung → „In diesem Artikel“** | jeder Eintrag endete auf „§“ |
| **Klartext-Kopie („Kurzfassung kopieren“)** | das „§“ landete in Franks Zwischenablage |
| **Vorlesen** | die Engine normalisiert „§“ → „Paragraph“: der Sprecher sagte „… Paragraph“ |

**Ursache (Wurzel):** Der Abschnitts-Link-Kopierer von
`ff-premium.js` (`addHeadingCopyButtons`) injizierte das Glyph „§“ als
**rohen Button-Text** in jede `h2`/`h3` mit ID. Alle Textextraktoren von
`ff-voice.js` (`readableText`) lasen ihn als Artikeltext — **UI-Schmuck
stand im Inhaltselement und war als Inhalt markiert.**

## 2 · Die Reparatur — fünf Wälle

| Wand | Datei | Was jetzt gilt |
|---|---|---|
| **1 · Quelle** | `static/premium/ff-premium.js` | **Symbol statt Glyphe:** reines Inline-SVG (Link-Symbol, Häkchen als Bestätigung) — **kein „§“-Textknoten mehr im DOM**. `data-ff-skip-read` markiert den Knopf für Lesemaschinen; `.ff-heading-text` + `aria-labelledby` sorgen dafür, dass nur der redaktionelle Text die Überschrift beschriftet (Screenreader, SEO). |
| **2 · Browser-Engine** | `static/premium/ff-voice.js` | `readableText()` entfernt vor **jeder** Extraktion `<button>`, Eingaben, `svg`, `[hidden]`, `[aria-hidden]`, `[data-ff-skip-read]`, `.anchor`, `.ff-mini-toc` (Sperrliste `READ_SKIP_SELECTOR`). `headingTextOf()` liefert saubere Überschriften-Texte für Gliederung, Tabellen-Titel und Fortschrittsanzeige. |
| **3 · Tonspur (Server)** | `scripts/ff_voice_audio.py` | Gleiche Sperrliste serverseitig plus Ankerschnitt am Überschriften-Ende — MP3-Tonspur und Browserstimme bleiben **wortgleich** (Parität 384/384). |
| **4 · Sicherheitsnetz** | `static/premium/ff-summary-safety.js` | Kürzt angehängte Ankerreste („§“, „#“) an Verzeichnis-Einträgen im Dialog — **in diesem PR gehärtet** (siehe § 3). |
| **5 · Gestaltung** | `assets/css/extended/z-premium-blog.css` | Icon zentriert, auf Touch-Geräten dezent sichtbar, im Ausdruck ausgeblendet — und **neu**: `user-select: none` (siehe § 4). |

**Inhaltsschutz:** Ein redaktionelles „§“ mitten im Text
(„Rechte aus **§ 8 EinSiG**“) bleibt in Kernaussagen, Klartext und
Tonspur unangetastet — entfernt wird nur UI-Schmuck, nie Inhalt.
Die Studio-Tonspur war nie betroffen (der Server rendert aus Markdown);
keine Audio-Regenerierung nötig.

## 3 · Härtung in diesem PR: Schwachstelle im Sicherheitsnetz geschlossen

Die neue „§“-Wache (§ 5) **fand eine echte Lücke in Wand 4**: Bestand der
letzte Textknoten eines Verzeichnis-Eintrags **nur** aus dem Ankerrest
(z. B. „Fazit “ + „§“ als zwei Knoten), blieb das „§“ stehen — die
Kürzung verlangte einen nicht-leeren Rest.

**Repariert:** `trimAnchorTrail()` entfernt reine Ankerrest-Knoten
komplett und zieht den vorangehenden Knoten in bis zu drei Durchläufen
nach. Ein „§“ mitten im Text („§ 8 EinSiG“) bleibt weiter unangetastet —
die Funktion greift nur, wenn ein Knoten **am Ende** auf „§“/„#“ endet.

## 4 · Premium-Optimierung

* **Kopieren mit Rückmeldung:** Link-Symbol → Häkchen, `aria-label`
  wechselt auf „Link kopiert“ (barrierefrei, 1,5 s).
* **Saubere manuelle Auswahl (neu):** `user-select: none` auf dem Knopf —
  wer eine Überschrift markiert und kopiert, bekommt kein Icon und kein
  Artefakt in die Zwischenablage.
* **Barrierefrei:** echter `<button type="button">`, per Tastatur
  erreichbar, sichtbarer Fokus; die Überschrift behält ihren
  redaktionellen Namen (`aria-labelledby`).
* **Mobil:** auf Touch-Geräten bleibt der Knopf dezent sichtbar.
* **Druck:** im Ausdruck unsichtbar.
* **Privacy:** kein Tracking, kein Netzwerkaufruf, alles First-Party.

## 5 · Neue „§“-Wache: `scripts/ff_heading_glyph_guard_test.mjs` (40 Gates)

Eine eigenständige Suite, die die **echten Produktions-Dateien**
(`ff-voice.js` + `ff-premium.js` + `ff-summary-safety.js`) gegen eine
**echte DOM** (jsdom) lädt — sieben Gruppen:

| Gruppe | Prüft |
|---|---|
| 1 · Injektion | Knopf an jeder Überschrift; **SVG statt Text**, kein Textzeichen im Knopf, `data-ff-skip-read`, `type`/`aria-label`, `aria-labelledby` → `.ff-heading-text` |
| 2 · Kurzfassung | Dialog, Gliederung und Klartext-Kopie ohne „§“; **Label-Vertrag: Gliederung ≡ sichtbarem Überschriftentext** |
| 3 · Vorlesen | kein TTS-Block mit „§“; H2-Blöcke enden sauber mit Punkt |
| 4 · Inhaltsschutz | „§ 8 EinSiG“ bleibt in Kernaussagen, Klartext und Absatz-Blöcken; Gliederung trotzdem §-frei |
| 5 · Mini-TOC | keine „§“/„#“-Labels, Label-Vertrag |
| 6 · **Feind-Injektion** | simuliert eine **künftige** Erweiterung, die „§“ als Knopf UND als Textknoten in die Überschrift schreibt — Klartext, Vorlesen und Dialog bleiben §-frei (Beweis für Wand 2); zusätzlich kürzt das Sicherheitsnetz einen direkt an den Dialog-Link gehängten „§“ (Beweis für Wand 4) |
| 7 · Ganzer Blog | **alle 34 echten Artikel**: Dialog, Klartext, Button-Markup, Label-Vertrag |

## 6 · Dauerschutz — drei Wachen, CI-verriegelt

1. **`scripts/ff_heading_glyph_guard_test.mjs`** (neu, 40 Gates) — läuft
   im **Lesehilfen-Gate** (Push/PR auf Lesehilfen-Dateien + Content sowie
   **täglich 08:20 MESZ**). Bricht sie, blockiert der Deploy.
2. **`scripts/heading_anchor_guard.py`** (32 → **36 Prüfungen**) — prüft
   Quelle, Engine, Theme, **gebaute Seiten in `public/`** (läuft im
   Deploy **nach** dem Hugo-Build, ein Fund stoppt den Deploy) und jetzt
   zusätzlich die Verdrahtung der „§“-Wache und die Härtung des
   Sicherheitsnetzes.
3. **Gruppe 13 des Funktionstests** (29 Prüfungen) — lädt das echte
   `ff-premium.js` gegen die echte DOM und prüft Knöpfe, Verzeichnis,
   Tabellen-Titel, Klartext, Vorlesen und Überschriften-Namen.

## 7 · Verifikation (alle Suiten grün)

| Prüfung | Ergebnis |
|---|---|
| `node scripts/ff_heading_glyph_guard_test.mjs` (neu) | **40/40** |
| `python3 scripts/heading_anchor_guard.py --selftest` (neu) | **4/4** |
| `python3 scripts/heading_anchor_guard.py` (erweitert) | **36/36** |
| Simulierter Hugo-Bau: alle 34 Artikel · 94 Überschriften mit Theme-Ankern | **0 Befunde** |
| `node scripts/ff_voice_functional_test.mjs` (inkl. Gruppe 13) | **247/247** |
| `node scripts/ff_voice_repair_test.mjs` | **56/56** |
| `node scripts/ff_voice_tts_hardening_test.mjs` | **57/57** |
| `node scripts/ff_voice_voice_test.js` (Stimmen-Regie) | **69/69** |
| `python3 scripts/ff_voice_parity_check.py` (Tonspur ≡ Browserstimme) | **384/384** |
| `python3 scripts/ff_voice_toolbar_check.py` | **118/118** |
| `python3 scripts/ff_voice_backends.py --selftest` | **83/83** |
| `python3 scripts/ff_voice_audio.py --selftest` | **114/114** |
| Bestandslauf über alle echten Artikel | **34 Artikel** — keine Gliederung mit „§“, Label-Vertrag hält überall |
| Schutz vor Übereifer | „Rechte aus **§ 8 EinSiG**“ bleibt in Überschrift, Verzeichnis und Vorlesen erhalten |

## 8 · Beifund (mitrepariert): Bau-Prüfung der Anker-Wache blockierte jeden Deploy

**Der Befund:** Nach dem Merge lief der Deploy zweimal rot (13:09 und
13:44) — bereits ab dem Grund-Fix-Merge `5d90d91` (PR #250), also
**unabhängig von dieser Härtung**. Schritt 22 „Anker-Wache“ scheiterte.

**Die Ursache:** Die **Bau-Prüfung** (Schicht 4, `public/`) kannte keine
Ausnahme für verstecktes Markup. Aber **jede gebaute Seite** trägt in
**jeder Überschrift** den legitimen Theme-Anker
(`<a hidden class="anchor" aria-hidden="true" href="#…">#</a>` aus
`anchored_headings.html`) — versteckt, exakt wie es Schicht 3 dieser
Wache selbst vorgibt. Das Muster `INNER_ANCHOR_RE` flaggte ihn als
„Ankersymbol in `<a>`/`<button>`“ → der erste Artikel genügte zum
Deploy-Stopp. Warum es niemand vorher sah: Die Bau-Prüfung lief zum
ersten Mal im echten Deploy — lokal gibt es kein `public/` (kein Hugo),
und das Lesehilfen-Gate baut nicht. Ein Klassiker: die neue Wache war
selbst ungeprüft.

**Die Reparatur:**
1. **Sichtbarkeits-Kontext:** `INNER_ANCHOR_RE` erfasst jetzt die
   Attribute der Kandidaten — `hidden`/`aria-hidden`/Klasse `anchor`
   werden ausgenommen (legitimer Theme-Anker), ein **sichtbares**
   „§“/„#“ in `<a>`/`<button>` bleibt ein Befund.
2. **Ehrlicher sichtbarer Text:** Der Enden-Check entfernt versteckte
   Knoten **vor** der Auswertung — sonst würde ein legitimes
   „Rechte aus § 8 EinSiG“ + versteckter „#“-Anker fälschlich als
   „endet auf Ankersymbol“ gelten.
3. **`--selftest` (neu):** baut ein synthetisches `public/` mit dem
   echten Theme-Markup und prüft die Bau-Logik in vier Fällen
   (sauber · Original-Bug-Knopf · Text-Ende „§“ · sichtbares Anker-„#“).
   Der Selbsttest läuft im **Lesehilfen-Gate** und im **Deploy vor der
   Wache** — die Bau-Prüfung kann nie wieder zum ersten Mal im Deploy
   laufen.

**Verifikation:** Selbsttest 4/4 · Simulation des echten Hugo-Baus über
alle 34 Artikel (94 Überschriften mit Theme-Ankern): **0 Befunde** ·
Minify-Variante (Attribute ohne Anführungszeichen): 0 Befunde, Original-
Bug weiterhin erkannt · Wache 36/36.

## 9 · Geänderte Dateien (dieser PR)

| Datei | Änderung |
|---|---|
| `scripts/ff_heading_glyph_guard_test.mjs` | **neu** — „§“-Wache, 40 Gates (echte DOM, echte Produktions-Dateien, Feind-Injektion, alle 34 Artikel) |
| `static/premium/ff-summary-safety.js` | Härtung: reine Ankerrest-Knoten fallen komplett weg, Nachzieh-Durchläufe |
| `assets/css/extended/z-premium-blog.css` | `user-select: none` für den Abschnitts-Knopf |
| `.github/workflows/lesehilfen-gate.yml` | neuer Schritt „§“-Wache + Auslöser-Pfade + Anker-Wachen-Selbsttest |
| `.github/workflows/deploy.yml` | Anker-Wachen-Selbsttest vor der echten Wache |
| `scripts/heading_anchor_guard.py` | 4 neue Prüfungen („§“-Wache vorhanden/verdrahtet, Sicherheitsnetz-Härtung) · **Bau-Prüfung repariert** (Hidden-Ausnahme, sichtbarer Text) · `--selftest` (4 Fälle) |
| `README.md` | Wächter-Liste ergänzt, Gate-Zahlen auf den aktuellen Stand gebracht |
| `KURZFASSUNG-ABSCHNITTSZEICHEN-REPARATUR-2026-09-10.md` | **neu** — dieser Report |

Grund-Reparatur (Wände 1–3, Gruppe 13, statische Wache, Deploy-Einbindung):
`KURZFASSUNG-PARAGRAPH-REPARATUR-2026-09-10.md` (PR #250, gemergt).
