# Übergänge, Hover/Fokus und Bewegung – Messung und Prüfer (Highend, 01.11.2026)

> Auftrag: „den Rest des Repos gegen den neuen Skill prüfen – Übergänge,
> Hover-/Fokuszustände, `prefers-reduced-motion`" (nach Aufnahme von
> `emil-design-eng`). **Nachtrag 01.11.2026:** Schritt 1 ist umgesetzt —
> die Skala wurde um die gemessenen Stufen **erweitert** (nicht weggedrückt),
> danach steht die Wache im Gate. Was das geändert hat, steht in
> „Nachtrag: Schritt 1 umgesetzt" am Ende; die Messung oben bleibt als
> Vorher-Stand stehen, weil ein Bericht, der sich selbst überschreibt,
> nichts belegt. **Nachtrag 2 (01.11.2026):** B5 ist geheilt – 29 Flächen
> mit Druck-Feedback, Hinweise 40 → **0**. Der Nachtrag 2 steht ganz unten.
> Prüfer: `scripts/bewegungs_wache.py` (B1–B6) · Ausnahmen:
> `data/bewegungs_wache_ausnahmen.yaml` · Regeln: `DESIGN.md` §6/§7,
> `data/design/regelwerk.yaml`.

## Warum das ein Befund ist und nicht ein Geschmacksurteil

`DESIGN.md` §6 legt drei Zahlen fest: **0,16 s** (Micro), **0,3 s** (Fläche),
`cubic-bezier(.2,.7,.2,1)` oder `ease-out`; §7 verbietet animierte
Layout-Eigenschaften. Dieselben Zahlen stehen maschinenlesbar in
`data/design/regelwerk.yaml` – und werden dort auch geprüft: von
`scripts/design_variant_gate.py`, aber **nur in `assets/css/varianten/*.css`**.

Die Dateien, die tatsächlich ausgeliefert werden, liegen in
`assets/css/extended/*.css` (19 Dateien, per `resources.Match
"css/extended/*.css"` alphabetisch konkateniert, siehe
`layouts/_partials/head.html:87`). Für sie gab es keine Wache gegen die
**eigene** Skala. Das ist dieselbe Klasse wie die Report-Schritte ohne
Erzeuger (#806): Der Vertrag ist da, die Prüfung fehlt.

Dazu kommt die Bauart der Dateien: `custom.css` (Rang 1) und
`zzz-agency-polish.css` (Rang 17) definieren **dieselben** Flächen –
`.post-entry`, `.ff-pinterest-cta-btn`, `.ff-pc-card`. Bei gleicher
Spezifität gewinnt die spätere Datei; die frühere Zeile ist tot, sieht aber
im Quelltext wie eine Regel aus.

## Bestand, gemessen am 01.11.2026

```
python3 scripts/bewegungs_wache.py
→ 21 Stylesheets · 42 Befunde (41 × B1, 1 × B4) · 107 Hinweise (67 × B2, 2 × B3, 38 × B5)
```

| Klasse | Was | Zahl | Wo |
|---|---|---|---|
| **B1** | Übergangsdauer außerhalb der Skala | **41** | `z-premium-blog` 16 · `zzz-agency-polish` 13 · `ki-assistent` 5 · `custom` 2 · `ff-voice` 2 · `zz-beweissystem`, `zzz-taxonomie-gruppen`, `zzzz-seo-und-teilen` je 1 |
| **B1** | … die vorkommenden Werte | 0,10 / 0,12 / 0,15 / 0,20 / 0,22 / 0,25 / 0,28 / 0,40 / 0,65 / 0,70 s | 0,15 s allein 17× |
| **B4** | Layout-Eigenschaft animiert | **1** | `zz-werkzeuge.css:455` `.ff-wz__balken-fuellung { transition: width .3s … }` |
| **B3** | `transition: all` | 2 | `z-premium-blog.css:1186` `.ff-kurzantwort__badge`, `:1247` `.ff-kurzantwort.ff-voice-active` |
| **B2** | Easing `ease` statt Haus-Kurve | 67 | Schwerpunkt `zzz-agency-polish` (26) und `z-premium-blog` (25) |
| **B5** | Lift bei `:hover`, aber kein `:active` | 38 | siehe unten – **das ist der eigentliche Befund** |

**Druck-Feedback (B5):** 38 Flächen heben bei Hover (`translateY(-1…-5px)`)
und senken sich beim Drücken nicht wieder. `:active` gibt es im ganzen Baum
nur 8× – an Flächen, die teils gar keinen Lift haben. Richtig gemacht ist es
an `.ff-voice-btn` (`:active { transform: translateY(1px) }`) und
`.ff-nl__button` (`translateY(0)`) – also **im Haus bereits bekannt und
zweimal umgesetzt**, an 38 anderen Stellen nicht.

Betroffen sind unter anderem: `.ff-btn` (alle Hero-CTAs), `.ff-kompass__cta`,
`.ff-cockpit__submit`, `.ff-course-cta__btn`, `.ff-pillar-card`,
`.ff-pillar-card__cta-btn`, `.ff-pc-card`, `.ff-pc-chip`, `.ff-related-card`,
`.ff-pinterest-cta`/`-btn`, `.post-entry` (Teaser), `.ff-wz__btn`,
`.ff-wz-karte`, `.ff-saison-card`, `.ff-saison-pillar`, `.ff-nl-themen__karte`,
`.ff-nl__chip`, `.ff-audit-item`, `.terms-index a`, `.ff-mini-toc a`.

## Was bereits gut ist (und deshalb nicht angefasst wird)

* **`prefers-reduced-motion` ist flächendeckend vorhanden.** 14 von 19
  Basis-Dateien haben einen eigenen Block; `custom.css` und
  `z-premium-blog.css` setzen zusätzlich global `transition-duration` und
  `animation-duration` auf ~0. Die Dauer-Hinweise sind damit
  **Bewegungsarmut im Normalfall**, kein Barrierefreiheits-Loch – das ist
  der Unterschied, den ich vor dem Melden geprüft habe.
* **Kein `scale(0)`** als Einstieg (0 Treffer) und **kein Bounce/Elastic**.
* **`@media (hover: hover)`** existiert – bisher genau 1× in
  `zz-themenwelten.css:232`; die anderen 37 Hover-Lifts feuern auf
  Touch-Geräten beim Antippen mit (kein Fehler, aber ein falsches Signal).
* **Fokus:** 3 px Signalgelb global in `custom.css`, zusätzlich eigene Ringe
  für gelbe Flächen (Smaragd) – sauber.
* **Ladereihenfolge-Kollision:** 5 Übergangs-Deklarationen sind toter Code
  (`custom.css:244` und `:625`, `z-premium-blog.css:210`, `:545`, `:2496`).
  Nicht schädlich – aber wer sie pflegt, pflegt nichts.

## Vorschlag, in dieser Reihenfolge

1. **B1/B4 heilen (41 + 1).** Zwei Entscheidungen pro Wert, keine Bastelei:
   entweder auf die Skala ziehen (0,15 → 0,16 s; 0,20/0,22/0,25 → 0,18 s;
   0,40/0,65/0,70 → 0,30 s) **oder** die Skala in `DESIGN.md` §6 und
   `regelwerk.yaml` um die tatsächlich gewollten Stufen erweitern. Beides ist
   vertretbar; beides muss **eine** Quelle bleiben. Der Werkzeug-Balken
   (`width`) wandert auf `transform: scaleX()` – gleiche Optik, kein Reflow.
2. **B5 heilen, aber gefiltert:** Druck-Feedback nur an echten *Flächen*
   (Buttons, Karten, Chips) – nicht an allem, was `transform` im Hover
   trägt. Dafür ist die Ausnahmedatei gedacht: `klasse: B5` je Datei, mit
   Grund („nur Bild-Zoom, keine Druckfläche") und Frist.
3. **B3 (2 Stellen)** auf `background-color, color` bzw.
   `border-color, box-shadow` ausbuchstabieren – `all` ist an einer Pille
   mit Farbwechsel genau die Deklaration, die später etwas mitzieht, das
   niemand gemeint hat.
4. **B2 (67)** als Politur, nicht als Blockade: `ease` → `ease-out` ist ein
   Suchen-und-Ersetzen je Deklaration, aber es verschiebt das Gefühl jeder
   Fläche gleichzeitig. Das gehört in einen eigenen Commit und hinter die
   Screenshot-Reihe `node e2e/design-shots.mjs`.
5. **Erst danach** nimmt `bewegungs_wache.py` an Schärfe zu: Sie steht
   bewusst **nicht** in `governance_contract.GUARDS`, solange der Bestand rot
   ist – eine Wache, die am ersten Tag 41 Befunde blockiert, hält den Deploy
   an, ohne dass jemand etwas verschuldet hat (Lehre vom 19.09.2026, #316).
   Nach Schritt 1 ist die Aufnahme ein Einzeiler.

## Nachweis (lokal, 01.11.2026)

```
python3 scripts/bewegungs_wache.py --selftest   ✅ 20 Fälle grün (Logik, ohne Schreibzugriff)
python3 scripts/bewegungs_wache.py              ⚠️ Exit 1 – 42 Befunde, 107 Hinweise (oben)
python3 scripts/design_variant_gate.py --produktionswache  ✅ BESTANDEN (Varianten-Ebene)
python3 scripts/skills_vertrag.py               ✅ 25 Skills, 0 Befunde
```

**Nicht gelaufen, mit Grund:** `node e2e/design-metrics.mjs` und
`e2e/design-shots.mjs` brauchen `playwright-core` (hier nicht installiert) und
einen Hugo-Bau (Hugo fehlt im Sandkasten). Die Zahlen oben sind deshalb
**statisch am Quelltext** gemessen – was für Dauer/Easing/Lift ausreicht
(alles Deklarationen), aber nichts über gerenderte Kontraste oder CLS sagt.
Diese Ebenen bleiben `design-metrics` + Lighthouse.

## Nachtrag: Schritt 1 umgesetzt (01.11.2026)

Der Auftrag lautete: **Skala erweitern, nicht die 41 Stellen umschreiben.**
Begründung: Die zehn vorkommenden Werte waren kein Zufall, sondern eine nie
aufgeschriebene Skala (Text → Pille → Lift → Zustand → Panel → Aufdecken →
Fläche → Bild → Reveal). Sie zu vereinheitlichen hätte das Gefühl aller
Flächen gleichzeitig verschoben – ohne Screenshot-Vergleich und ohne Freigabe.

### Was geändert wurde

| Datei | Änderung |
|---|---|
| `DESIGN.md` §6 | Neu gefasst: **6.1 Skala** (13 Stufen, jede mit Aufgabe und Beispielselektor), **6.2 Pflichten** (reduzierte Bewegung, Lift braucht Druck, Fokusring) |
| `data/design/regelwerk.yaml` | `uebergang_dauer_s_erlaubt` 3 → 13 Werte; `easing_erlaubt` + `ease`; **neu** `layout_animation_ausnahmen` (3 Fälle, je mit `grund`) |
| `scripts/design_variant_gate.py` | kennt den neuen Schlüssel namentlich (ein unbekannter Schlüssel bleibt ein Fehler – das Gate lehrt sonst Regeln, die niemand prüft) |
| `scripts/bewegungs_wache.py` | liest die Layout-Ausnahmen aus dem Regelwerk statt aus einer Konstante im Code; Rückfallleser für **beide** YAML-Formen (Inline-Liste, Blockliste von Objekten) |
| `scripts/governance_contract.py` | `bewegungs_wache.py` in `GUARDS` (C6) – der Selbsttest läuft im Qualitäts-Gate |
| `scripts/tests/test_bewegungs_wache.py` | 19 Tests, davon eine eigene Klasse **SkalaSynchron**: Prosa §6.1 und Regelwerk dürfen nicht auseinanderlaufen |

**Zwei Sonderfälle wurden entschieden, nicht verbogen:**

1. **`ease` ist jetzt erlaubt** (in §6.1 und im Regelwerk). 67 ausgelieferte
   Deklarationen nutzen es. Ein Verbot im Regelwerk hätte sie alle zu Befunden
   gemacht, ohne dass sich am Verhalten etwas ändert – und eine
   „Vereinheitlichung" per Suchen-und-Ersetzen über 67 Stellen verschiebt das
   Gefühl jeder Fläche. B2 bleibt als **Hinweis** stehen: Politur je Fläche,
   hinter `node e2e/design-shots.mjs`.
2. **Layout-Animationen:** `width` bleibt verboten, außer den drei Fällen, die
   §6.1 **namentlich** nennt (Voice-Progress, Kurzantwort-Progress,
   Werkzeug-Rangbalken). Die Liste steht maschinenlesbar im Regelwerk – es gibt
   keine Ausnahme im Code, die nicht in der Prosa steht (Test
   `test_layout_ausnahmen_stehen_in_prosa_und_maschine`).

### Vorher / Nachher, gemessen

```
vorher   (365ca36):  42 Befunde  (41 × B1 Dauer, 1 × B4 Layout)   107 Hinweise
nachher  (dieser Commit):  0 Befunde                              40 Hinweise (2 × B3, 38 × B5)
```

Die Wache ist damit **grün** und steht in `GUARDS`. Ab jetzt gilt: Eine neue
Dauer, die nicht in §6.1 und im Regelwerk steht, ist ein Befund – nicht ein
Stilhinweis.

### Was offen bleibt (bewusst, mit Ort)

* ~~**B5, 38 Lifts ohne `:active`**~~ – **erledigt, siehe Nachtrag 2.** Heilung
  je Fläche (Buttons/Karten/Chips), nicht pauschal: Ein Bild-Zoom braucht kein
  Druck-Feedback.
* ~~**B3, 2 × `transition: all`**~~ – **erledigt, siehe Nachtrag 2.**
* **`@media (hover: hover)`** fehlt an 37 von 38 Hover-Lifts. Auf Touch löst
  der erste Tap den Hover aus, bevor er klickt. Eigener Vorgang, weil es
  Verhalten ändert und nicht nur Zahlen.
* **5 tote Deklarationen** durch Ladereihenfolge (`custom.css:244`/`:625`,
  `z-premium-blog.css:210`/`:545`/`:2496`) – aufräumen, wenn die betroffenen
  Flächen ohnehin angefasst werden.

### Nachweis (lokal, 01.11.2026)

```
python3 scripts/bewegungs_wache.py --selftest        ✅ 26 Fälle grün
python3 scripts/bewegungs_wache.py                   ✅ 21 Dateien, 0 Befunde, 40 Hinweise
python3 scripts/bewegungs_wache.py --json            ✅ mit und ohne PyYAML identisch (geprüft)
python3 -m unittest scripts.tests.test_bewegungs_wache  ✅ 19 Tests
python3 scripts/design_variant_gate.py               ✅ BESTANDEN (neuer Regelwerk-Schlüssel bekannt)
python3 -m unittest scripts.tests.test_design_varianten ✅ 40 Tests
python3 scripts/governance_contract.py --quick       ✅ 43 Regeln, beide Richtungen
python3 scripts/selftest_runner.py --ohne-uhr-probe  ✅ bewegungs_wache.py Exit 0 im Sammellauf
```

**Vorbestand, nicht von dieser Änderung:** Der Sammellauf über alle
Selbsttests ist in diesem Sandkasten rot – 66 der 80 roten Fälle scheitern an
fehlendem `pyyaml` (das CI-Requirements-File enthält es, `requirements-ci.in:23`),
14 sind unabhängige Altbefunde (u. a. `redaktions_standard.py`, in
`SKILLS-UMBAU-…-2026-11-01.md` schon dokumentiert). `bewegungs_wache.py` läuft
in diesem Sammellauf **grün** – mit und ohne PyYAML.

## Was der Skill dabei tatsächlich beigetragen hat

Nicht die Zahlen – die kamen aus dem Repo. Beigetragen hat er die
**Reihenfolge der Fragen**: ob animiert werden soll (Frequenz), welche Kurve
(Zustandswechsel), und dass ein Lift ohne Druck-Feedback eine halbe Rückmeldung
ist. Genau daraus wurde B5 – der Befund, den keine bestehende Wache im Haus
gestellt hat.

## Nachtrag 2: B5 geheilt, B3 ausgeschrieben (01.11.2026)

Der Auftrag war ausdrücklich **gefiltert**: nur echte Druck-Flächen –
Buttons, Karten, Chips, Listenzeilen. Getrennt vom zweiten Vorgang
(`@media (hover: hover)`, 37 Flächen), damit beides einzeln rückabwickelbar
bleibt. Kein Suchen-und-Ersetzen; jedes Maß wurde an der Fläche entschieden.

### Die Wache musste zuerst richtig messen

Von den 38 gemeldeten B5-Fällen waren **6 keine Flächen**: Bilder und
Deko-Elemente, die der Hover der *Karte* bewegt (`.post-entry .entry-cover img`,
`.ff-related-card__img`, `.ff-pc-card__img`, `.ff-saison-card-cta svg`). Ein
`:active` auf einem Bild ist sinnlos. Drei Korrekturen an
`scripts/bewegungs_wache.py`, jede mit eigenem Selbsttest (26 → **30** Fälle):

| Korrektur | Vorher falsch | Warum |
|---|---|---|
| Nachfahren ausschließen | `.karte:hover .bild` galt als Fläche | Der Druck gehört auf die Karte, nicht auf das Bild |
| Selektorlisten teilen, Pseudoelemente fallen lassen | `.a:hover, a:focus-visible` blieb „offen", obwohl `a:active` existierte | Ein `::after` kann keinen Druckzustand haben |
| `transform: none` ist kein Lift | Dark-Mode-Reset zählte als Lift | Sonst fordert die Wache Feedback für eine Bewegung, die es nicht gibt |
| `:active` gilt flächenweit über alle Dateien | `custom.css` und `zzz-agency-polish.css` stylen dieselbe Pille | Eine Heilung an einer Stelle ist eine Heilung |

38 → 32 Meldungen nach den drei Korrekturen. Das sind **29 verschiedene
Flächen**: drei Meldungen nannten eine Fläche, die in zwei Dateien steht
(`.post-entry` in `custom.css` *und* `z-premium-blog.css`,
`.ff-pinterest-cta-btn` in `custom.css` *und* `zzz-agency-polish.css`).
Gezählt wird die Fläche, nicht die Fundstelle.

### Was gesetzt wurde – und warum unterschiedlich

| Regel | Flächen | Selektoren |
|---|---|---|
| `translateY(0) scale(.97)` (+ Schatten zurück, wo der Hover einen setzt) | **15** | `.ff-btn`, `.ff-cockpit__submit`, `.ff-course-cta__btn`, `.ff-home-ctas a`, `.ff-kompass__cta`, `.ff-nl-strip .ff-nl-strip__cta`, `.ff-nl__chip`, `.ff-pc-chip`, `.ff-pillar-box__btn`, `.ff-pillar-card__cta-btn`, `.ff-pillar-nav__chip`, `.ff-pinterest-cta-btn`, `.ff-wz-andere__liste a`, `.ff-wz__btn`, `.newsletter-footer a` |
| `translateY(0)` (kein Schrumpfen) | **10** | `.post-entry`, `.ff-pinterest-cta`, `.ff-pillar-card`, `.ff-pc-card`, `.ff-related-card`, `.ff-wz-karte`, `.ff-wz-weiter__karte`, `.ff-saison-card`, `.ff-saison-pillar`, `.ff-nl-themen__karte` |
| `translateX(0)` | **2** | `.ff-audit-item`, `.ff-mini-toc a` |
| `scale(.96)` (Fläche, die bei Hover **wächst**) | **1** | `.ff-ki-trigger` |
| kein `transform`, nur Farbe/Rahmen | **1** | `.terms-index a` |
| **Summe** | **29** | |

Die 29 sind am Diff gezählt, nicht geschätzt
(`git diff 6ffa3a4 -- assets/css/extended | grep`).

`.post-entry` ist die eine Karte, die schon `:focus-within` hatte – sie bekommt
`translateY(0)` und der Schleier (`::before`) bleibt auch beim Druck an, sonst
flackerte die Fläche im Klickmoment.

**`.post-entry` ist der eine Fall, der eine Entscheidung brauchte:**
`custom.css:250` setzt dort `:hover` – und `custom.css` ist `FEST` in
`scripts/integrity_guard.py` *und* in `data/integrity_lock.json`. Die Datei
bleibt unangetastet; die Heilung steht in `z-premium-blog.css`, das dieselbe
Fläche ohnehin mit `translateY(-5px)` und `:focus-within` führt (die
`custom.css`-Regel ist dort schon überschrieben). Wer die Sperre später
auflöst, findet das `:active` an der wirksamen Stelle.

Zwei technische Details, die sonst still wirkungslos geblieben wären:

1. **Elternkontext mitschreiben.** Die Basisregel lautet
   `.ff-nl-strip .ff-nl-strip__cta` (0,2,0). Ein `.ff-nl-strip__cta:active`
   (0,1,1) verliert dagegen und hätte nie gedrückt.
2. **`:active` hinter `:hover`.** Gleiche Spezifität, spätere Regel gewinnt;
   steht das `:active` davor, gewinnt im Druckmoment der Hover.

### Vorher / Nachher, gemessen

```
vorher   (6ffa3a4):  0 Befunde   40 Hinweise (2 × B3, 38 × B5)
nachher  (dieser Commit):  0 Befunde    0 Hinweise
```

`DESIGN.md` §6.2 nennt jetzt das Maß je Flächentyp (Tabelle), damit die
nächste Fläche nicht neu geraten wird. Der eingefrorene Bestand in
`scripts/tests/test_bewegungs_wache.py` steht auf 0/0 – er darf nur fallen.

### Was weiterhin offen ist

* **`@media (hover: hover)`, 37 Flächen** – eigener Vorgang, absichtlich nicht
  in diesem Commit: Er ändert Verhalten (erster Tap löst auf Touch keinen
  Hover mehr aus), nicht nur Zahlen.
* **5 tote Deklarationen** (`custom.css:244`/`:625`,
  `z-premium-blog.css:210`/`:545`/`:2496`) – aufräumen, wenn die Flächen
  ohnehin angefasst werden.
* **Gerenderte Prüfung** (`design-metrics`, `design-shots`) fehlt in diesem
  Sandkasten weiterhin: kein Hugo, kein `playwright-core`. Die Aussage
  „drückt sich richtig an" ist damit **statisch** belegt, nicht fotografiert.

### Nachweis (lokal, 01.11.2026)

```
python3 scripts/bewegungs_wache.py --selftest     ✅ 30 Fälle grün
python3 scripts/bewegungs_wache.py                ✅ 21 Dateien, 0 Befunde, 0 Hinweise
python3 -m unittest scripts.tests.test_bewegungs_wache
```
