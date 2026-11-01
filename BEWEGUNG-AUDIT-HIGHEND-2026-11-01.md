# Übergänge, Hover/Fokus und Bewegung – Messung und Prüfer (Highend, 01.11.2026)

> Auftrag: „den Rest des Repos gegen den neuen Skill prüfen – Übergänge,
> Hover-/Fokuszustände, `prefers-reduced-motion`" (nach Aufnahme von
> `emil-design-eng`). Ergebnis: **gemessen, nicht repariert.**
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
