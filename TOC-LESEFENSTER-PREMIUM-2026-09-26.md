# „Im Artikel“-Navigation überdeckt nichts mehr – Lesefenster auf Premium-Level (26.09.2026)

**Auslöser:** Frank, zum Artikel
`/posts/2026-09-20-gasrechnung-senken-spaetsommer-check-spart-hunderte-euro/` –
*„Sämtliche Blog-Artikel werden durch das Inhaltsverzeichnis IM ARTIKEL
verdeckt bzw. Newsletter abonnieren wird nicht richtig angezeigt.“*

Beide Meldungen haben **eine gemeinsame Wurzel** – und betrafen nicht nur
diesen einen Artikel, sondern **jede Blog-Artikelseite ab 1280 px
Fensterbreite**.

---

## Befund (reproduziert, nicht vermutet)

Gemessen am echten Build (Hugo 0.164.0, Playwright/Chromium, Viewport
1440 × 900 – bei 1280, 1310, 1366, 1536, 1920 und 2560 px identisch):

| Größe | Wert |
|---|---|
| Textspalte (`.main`, zentriert) | 768 px (x 336–1104) |
| Newsletter-Kopf (`.ff-nl-top`) | **1024 px** (x 208–1232) – 128 px breiter als die Spalte |
| Schwebende „Im Artikel“-Box (`.ff-mini-toc`, fixed, z 50) | 216 px, x 1128–1344 – 24 px rechts **der Textspalte** |
| Überlappung Box ∩ Kopf | **104 px horizontal × 88 px vertikal** |

Der Kopf-Streifen ragt mit 128 px in den Seitenrand hinein – genau dorthin,
wo die schwebende Navigation sitzt. Folgen auf **jedem Desktop ≥ 1280 px**:

1. Die halbtransparente, blurrende Box (86 % Deckkraft) lag auf dem
   rechten Ende des Kopf-Streifens.
2. Der gelbe **„Newsletter abonnieren“-Knopf** (x 968–1204) war zu
   **76 px (rund ein Drittel)** verdeckt – inklusive des Pfeil-Symbols
   (x 1166–1186, vollständig hinter der Box). Der Knopf schien
   „abgehackt“: Textende und Pfeil verschwanden hinter einem
   Milchglas-Kasten. → *„Newsletter abonnieren wird nicht richtig
   angezeigt“*.
3. Da jeder Blog-Artikel denselben Kopf trägt, wirkte es, als würden
   **sämtliche Artikel** von der „IM ARTIKEL“-Navigation verdeckt. →
   *„Sämtliche Blog-Artikel werden durch das Inhaltsverzeichnis IM
   ARTIKEL verdeckt“*.

Der Artikeltext selbst war von der Geometrie her nie betroffen (Spalte
768 px endet vor der Box) – die Vorgänger-Reparatur
(`TOC-IM-ARTIKEL-PREMIUM-2026-09-26.md`) hatte die Box korrekt an der
Textspalte verankert. Neu war der Konflikt mit dem **Vollbreiten-Kopf
über** dem Artikel. Ein zweiter, latenter Konflikt gleicher Klasse lauerte
am Seitenende (Vollbreiten-Blöcke im Fuß) und auf kurzen Viewports
(Consent-Banner unten).

## Reparatur – das Lesefenster-Prinzip

**Leitgedanke (Profi-Standard bei schwebenden Kapitel-Navigationen):**
Die Navigation gehört zur **Lesephase**, nicht zur Landung. Sie darf nur
sichtbar sein, wenn ihr Kasten nachweislich über **leerem Rand** schwebt.

**`static/premium/ff-premium.js` → `createMiniToc()` / `setupMiniTocSpy()`**

1. **Ruhzustand ab Geburt:** Die Box startet mit `ff-mini-toc--idle`
   (unsichtbar, nicht klickbar). Ohne JavaScript existiert sie gar nicht –
   kein no-JS-Sonderfall, kein Flash.
2. **Einblenden erst im Artikelkörper:** sobald die Oberkante von
   `.post-content` die obere Zonenkante passiert (24 px Polster).
   Newsletter-Kopf, Titel, Cover und Kurzfassung bleiben immer frei.
3. **Zurückziehen vor dem Seitenfuß:** sobald der erste Fuß-Block
   (`footer.footer`, Fuß-Newsletter-Streifen, Pinterest-Block,
   Consent-Hülle) die Zone von unten erreicht (24 px Polster).
4. **Consent-Banner-Ausweiche:** steht das Banner sichtbar in der Zone
   (kurze Fenster), bleibt die Navigation zurückgezogen.
5. **Kein Layout-Thrashing:** Geometrie wird nur in der Messphase gelesen
   (`measure()`/`measureWindow()` bei resize, load, `document.fonts.ready`);
   im Scroll-Frame (rAF-gebündelt) reine Arithmetik. Die Position der Box
   liest das Skript aus dem Stylesheet (`top` + `offsetHeight`,
   transform-sicher), statt sie zu vermuten.
6. Die interne Selbstnachführung (`keepVisible`) läuft nur im sichtbaren
   Zustand; Anker-Sprünge (auch per Deep-Link `#abschnitt` beim Laden)
   erkennen die Lesephase sofort.

**`assets/css/extended/z-premium-blog.css` → Block „Im Artikel“**

- `.ff-mini-toc--idle`: `opacity: 0`, `visibility: hidden` (nimmt die
  Links auch aus der Tab-Reihenfolge), `pointer-events: none`,
  dezentes `translateY(-10px)`.
- Einblenden als Flächen-Übergang nach DESIGN.md §6: **0,3 s,
  cubic-bezier(.2,.7,.2,1)**; Zurückziehen als Micro-Übergang:
  **0,16 s ease-out**; `visibility` ohne bzw. mit passender Verzögerung,
  damit weder ein toter Fokus-Ring noch ein hartes Wegblinken entsteht.
- `@media (prefers-reduced-motion: reduce)`: Übergänge aus (Haus-Standard
  `zzz-agency-polish.css` §8 bleibt unangetastet).
- Druck bleibt ausblendet; Mobil (< 1280 px) bleibt wie zuvor
  `display: none`.

**Bewusst KEINE Variante (Ausnahme von der Varianten-Regel):** Es handelt
sich um eine **Defektreparatur**, keinen Layout-Umbau – Geometrie,
Farben und Typografie der Navigation sind unverändert; neu ist nur das
Sichtbarkeits-Timing plus Ruhzustand. Die Geometrie-Konstante
(24 px neben der 768-px-Spalte) stammt aus der freigegebenen
Vorgänger-Reparatur.

## Verifikation

| Prüfung | Ergebnis |
|---|---|
| Eigener Breitensweep 1280/1310/1366/1440/1536/1920/2560 × (900/768) am gemeldeten Artikel | Kopf: Box im Ruhzustand, Knopf an allen Punkten klickbar · Lesephase: sichtbar, **0 überdeckte Elemente** · Fuß: zurückgezogen, 0 überdeckte Elemente |
| Clip-bewusster Voll-Sweep über **alle 41 Posts + 7 Pillar-Seiten** (1440 × 900; Scroll-Positionen Kopf/Lesephase/Fuß) | **alle 48 Seiten sauber** – inklusive der Energiediebe-Seite mit 1129-px-Tabelle in der Scroll-Hülle (visuell beschnitten, kein Konflikt) |
| Mobil 390 × 844 | Navigation `display: none` (wie bisher), Kopf-Streifen sauber |
| Kurzes Fenster 1280 × 600 mit Consent-Banner | Banner 526 > Box-Unterkante 503 → keine Kollision; bei noch kürzeren Fenstern weicht die Box aus |
| `npm run test:e2e` (Playwright, Desktop + Mobil) | **64/64 grün** – inkl. 4 neuer Regressionstests (s. u.) |
| `node scripts/ff_heading_glyph_guard_test.mjs` | 43/43 grün |
| `node scripts/ff_voice_functional_test.mjs` | 252/252 grün |
| `python3 scripts/layout_audit.py` | keine neuen Befunde (nur die bekannten hreflang-/DOM-Frühwarnungen) |
| `python3 -m unittest discover -s scripts/tests` | unverändert zum Ursprungszustand (854 Tests: dieselben 5 Failures/11 Errors wie vor der Änderung – Umwelt-/Bestandsbefunde, hier nicht berührt) |

**Neue Dauer-Wache in `e2e/article.spec.mjs`** (läuft in CI bei jedem PR
auf main mit):

1. *„Schwebende Artikel-Navigation überdeckt keinen Inhalt –
   Newsletter-Kopf frei“* bei **1280, 1440 und 1920 px**: prüft
   Ruhzustand im Kopf (inkl. Klick-Treffer auf dem früher verdeckten
   Knopfrand), clip-bewusste Null-Überdeckung in der Lesephase, freien
   Fuß und sofortige Sichtbarkeit nach Anker-Sprung.
2. *„bei reduzierter Bewegung ohne Übergang“*: `prefers-reduced-motion`
   wird respektiert.
3. Der Bestandstest zu langen Abschnittstiteln scrollt jetzt erst in die
   Lesephase – er testet damit das echte Nutzerverhalten.

Damit ist die Klasse „schwebende Navigation überdeckt Inhalt“ **per
Vertrag abgesichert**: Jede künftige Änderung, die die Box wieder über
fremde Blöcke legt, lässt die CI rot laufen.

## Hinweis für die Redaktion (kein Handlungsbedarf)

Der Newsletter-Kopf bleibt bewusst 1024 px breit – auf der Startseite
(dort gibt es keine schwebende Navigation) führt die Breite zu keinem
Konflikt, und die Reparatur soll das freigegebene Erscheinungsbild nicht
anfassen. Sollte der Kopf je auf 768 px (Spaltenbreite) gezogen werden,
wäre das ein eigener Design-Entscheid über die Varianten-Werkbank.
