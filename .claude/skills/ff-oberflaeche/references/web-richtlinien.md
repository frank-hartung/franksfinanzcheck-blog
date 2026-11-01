# Web-Richtlinie: UI-Code vor dem Melden durchgehen

**Hausgemacht, nicht übernommen** – Ersatz für die Fremd-Liste `web-design-guidelines`
(bis 2026-11-01:
`web-design-guidelines`, entfernt, weil die Herkunft ungeklärt war – siehe
`data/skill_lizenzen.json`, Feld `erledigte_faelle`). Alles hier ist an diesem
Repository geprüft: jeder Punkt ist entweder durch ein Gate beweisbar oder wird
an einer benannten Stelle von Hand angesehen. Eine Regel, die niemand nachprüfen
kann, gilt hier als unerfüllt.

## Prüfweise

Ein Review nennt pro Punkt **erfüllt**, **betrifft nicht** (mit Grund) oder
**Blocker** (mit Heilung). „Sieht gut aus" ist kein Befund. Wer einen Punkt
überspringt, hat ihn nicht bestanden – stillschweigend als erfüllt gelten ist
genau die Art Fehler, die hier sechs Wochen lang unsichtbar bleibt.

## A – Struktur und Semantik

1. Genau ein `<h1>`; Überschriften in Stufen ohne Sprung (`h1 → h3` ist ein Fehler, kein Stil).
2. Bedienung ist ein `<button>`, Navigation ist ein `<a href>`. Ein `<div>` mit `onclick` ist
   mit der Tastatur nicht erreichbar und dem Leser nicht als Ziel zu erkennen.
3. Landmarks (`header`/`nav`/`main`/`footer`) einmal je Rolle; kein zweites `<main>`.
4. Formular: jedes Feld mit echtem `<label for>`, `type`/`inputmode`/`autocomplete` passend zum
   Wert (E-Mail, Zahl, Postleitzahl). Pflichtfeld = `required` **und** im Text sichtbar.
5. Tabelle hat `<caption>` oder eine benachbarte Überschrift, Kopfspalten mit `scope`.

## B – Wahrnehmbarkeit

6. Kontrast gemessen, nicht geschätzt: 4,5:1 Fließtext, 3:1 große Schrift und reine
   Bedienflächen – im hellen und im dunklen Theme. Zahlen liefert `node e2e/design-metrics.mjs`.
7. Farbe trägt nie allein: „rot = Fehler" braucht Icon und Wort, sonst ist die Meldung für
   farbfehlsichtige Leser leer.
8. Text auf 200 % vergrößerbar ohne Verlust von Inhalt oder Funktion; keine feste Höhe an
   textgefüllten Kästen.
9. `:focus-visible` sichtbar auf jedem interaktiven Element. `outline: none` ohne Ersatz ist
   ein Blocker – wer den Ring abstellt, schließt die Tastaturbenutzung aus.
10. Dunkles Theme ist keine Nachtragsschicht: jeder neue Token-Wert bekommt seinen
    `:root[data-theme="dark"]`-Partner (Kernregel 3).

## C – Bewegung, Zeit, Stabilität

11. `@media (prefers-reduced-motion: reduce)` schaltet jede Animation, jedes Auto-Scrollen und
    jeden Parallax-Effekt aus – auch die in `static/premium/*.js`.
12. Keine Änderung, die Layout verschiebt, ohne dass Raum reserviert ist: Bilder mit `width`/
    `height` oder `aspect-ratio`, Werbeflächen und Nachladeschichten mit fester Höhe. CLS ist
    hier ein Befund, kein Rauschen.
13. Kein Zeitlimit ohne Ausweg, keine automatisch startende Bewegung über fünf Sekunden.

## D – Zeiger und Tastatur

14. Zielgröße mindestens 24 × 24 px, bei berührbaren Oberflächen 44 px, mit Abstand gegen
    Fehltreffer.
15. Keine Funktion, die nur bei `:hover` erscheint. Was der Finger nicht sieht, existiert nicht.
16. Overlay/Dialog: Fokus liegt beim Öffnen innen, `Escape` schließt, beim Schließen kehrt der
    Fokus zum Auslöser zurück.
17. Jeder Rechner und jedes Werkzeug ist mit Tastatur allein vollständig bedienbar
    (`npm run werkzeuge:check`, `npm run test:toc`).

## E – Text im Interface

18. `alt` leer bei Dekoration, aussagekräftig bei Inhalt; „Bild" und Dateinamen sind kein Alt-Text.
19. Fehlertexte nennen den Ausweg („Postleitzahl fehlt – 5 Ziffern, oben im Feld"), nie den
    Zustand allein („Ungültige Eingabe").
20. Statusmeldungen an Blinden-Leseräte nur über `role="status"`/`aria-live`, und nur je
    Ereignis – das Fangnetz-Prinzip aus `references/robustheit.md` gilt auch hier.
21. „Hier klicken" verboten: Linktext trägt das Ziel, weil die Leseräte-Liste sonst aus
    30 Zeilen „Hier klicken" besteht.

## F – Kopfbereich und Ressourcen

22. Kein neues `<head>`-Kind (58 sind die Lighthouse-Grenze, Kernregel 8).
23. Schrift selbst gehostet mit `font-display: swap`; geladen wird, was gebraucht wird – kein
    Preload auf einer Schrift, die nur eine Unterseite nutzt.
24. Kein Fremd-Skript, das den Leser vermisst. Auswertung ist Sache der eigenen Zählung; die
    Sperre prüft das (`scripts/fremdmessung_sperre.py`), und sie gilt auch für Proben,
    Testseiten und Skill-Texte.

## Anschluss an die Gates

| Gruppe | Beweis |
|---|---|
| A, B, E | `npm run a11y:check` · `npm run test:a11y:browser` (axe-core im gerenderten DOM) |
| B (Kontrast), C (Stabilität) | `node e2e/design-metrics.mjs` · `npm run lighthouse:live` |
| D (Werkzeuge) | `npm run werkzeuge:check` · `npm run test:toc` |
| F (Kopf, Caching) | `npm run header:check` |
| Layout-Umbau je Variante | `npm run design:quality` |

Was kein Gate abdeckt (Punkt 3, 8, 13, 15, 16, 18, 19, 21), wird im Review mit Datei und
Zeile benannt. Ein Befund ohne Fundstelle ist eine Vermutung.
