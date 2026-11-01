# Laufzeit-Robustheit und die Artikel-Navigation

> Wörtlich aus `CLAUDE.md` übernommen am 01.11.2026 (Skill-Umbau). Kein Satz wurde umformuliert, gekürzt oder erfunden; die Überschriften sind eine Ebene tiefer gehängt. Änderungen hier sind Änderungen am Regelwerk – sie brauchen denselben Nachweis wie vorher: Selbsttest der betroffenen Wache, dann Commit.

### Die Seite darf nie stumm sterben (Robustheit der Laufzeit, C31, seit 07.10.2026)

**Lehre aus vier Befunden, die kein Build-Gate sehen konnte.** Dieser Blog hat
zwei Fehlerklassen. Die lauten fangen die übrigen Wachen: Der Build bricht ab,
ein Gate wird rot, der Deploy bleibt liegen. Die stillen sind teurer, weil die
Seite **baut** – der Ausfall passiert erst im Browser, bei einem Leser, auf
einem Gerät, das hier niemand hat. Am 07.10.2026 lagen vier solcher Fälle real
im Bestand:

1. `ff-rechner.js` initialisierte alle Rechner einer Seite in einer Schleife
   **ohne Fangnetz**. Ein einziger Rechner mit unerwartetem Markup warf – und
   nahm den übrigen die Verdrahtung mit: Formular sichtbar, Absenden lädt die
   Seite neu, keine Rechnung.
2. Die Newsletter-Anmeldung wartete **unbegrenzt** auf den Worker: `fetch` ohne
   Zeitlimit, Knopf `disabled`. Hing der Worker, stand „Wird übermittelt …" für
   immer; wiederholen ging nicht, abbrechen auch nicht.
3. Der Service Worker öffnete seinen Cache außerhalb jedes `try/catch`. Wirft
   das Cache-API (volle Quota, privater Modus), lehnte `respondWith` ab – ein
   Request, der ohne den SW problemlos durchgegangen wäre, kam nicht an.
4. Der Kopier-Knopf meldete „copied!" **bevor** die Zwischenablage antwortete
   und ließ ein abgelehntes Promise zurück.

**Die Regel daraus:** Ein gefangener Fehler ist erst behoben, wenn der Leser
weiß, woran er ist. Ein Knopf, der nichts tut, ist schlechter als ein Satz, der
sagt, was geht und was nicht.

**Zwei Stufen, eine Wahrheit.** Stufe 1 ist der Bootstrap im `<head>`
(`layouts/_partials/extend_head.html`, **im vorhandenen** Consent-Skript – kein
zusätzliches Head-Kind, 58 ist die Lighthouse-Grenze): Er sieht jeden Fehler,
auch den der Inline-Skripte, und stellt `FFRobust.hole()` – Fetch mit
Zeitlimit, das **nie** ablehnt. Stufe 2 ist `static/premium/ff-robust.js`
(defer, Fuß des Body): Fehlergrenzen (`insel`), Speicher-Fangnetz (`ablage`),
ehrliche Zwischenablage, Diagnose (`bericht()`). Beide sind idempotent
(`R.boot`), beide first-party, beide ohne Versand nach außen.

**Was ein Agent beim Bauen eines interaktiven Bausteins tut:**

1. Fangnetz **je Instanz**, nicht je Seite: `FFRobust.insel('name', init,
   { ziel: ergebnisFeld })` oder ein eigenes `try/catch` pro Element.
2. Im Ausfall einen Satz: `role="status"`, Marke, keine Technik.
3. Jeder Netzaufruf über `FFRobust.hole(url, { zeitlimit, versuche, quelle })`;
   der Knopf wird im Fehlerfall wieder freigegeben.
4. Web Storage nur mit Fangnetz (`FFRobust.ablage` oder `try/catch`) – die Seite
   bleibt ohne Speicher bedienbar.
5. Kein `innerHTML` aus Text, kein `document.write`, kein `eval()`.

**Zwei Vertragspunkte, die nicht verhandelbar sind.** `opaque` (Antwort aus
einem `no-cors`-Fetch) ist **kein** Fehler: Sie sagt „durchgekommen, Inhalt
nicht lesbar" – die Newsletter-Anmeldung sendet bewusst `no-cors`, und
`test_kein_erfolgsversprechen` hält fest, dass sie deshalb nie einen Erfolg
behauptet. Und: Wiederholt wird nur bei `netz`, nie bei `zeitlimit` – ein
Request, der ins Zeitlimit lief, hat den Dienst schon beschäftigt.

**Wache:** `scripts/robustheits_gate.py` (R1–R13, `--selftest` mit 14
Sabotage-Proben und 4 Gegenproben, `--public` für die gebaute Wahrheit). Sie
läuft in `robustheit.yml` (Push/PR/Nacht) und im Deploy **vor** dem Build,
fail-closed. Sie heilt nie selbst: Ein Fangnetz, das sich selbst wieder
einhängt, wäre keines.

**Ausnahmen** stehen in `data/robustheit_ausnahmen.yaml` – begründet, mit
Entscheidung und **Fälligkeit**, im Bericht genannt. Eine Ausnahme ohne
Fälligkeit ist eine stille Abschaffung. Für die Frist gilt R13, und R13 ist aus
einem echten Befund entstanden: Die CI-Uhr-Probe
(`publication-reliability-tests.yml`, ganze Suite mit +97 Tagen) fand am
07.10.2026 einen Test, der `faellig` gegen `date.today()` maß – die Suite wäre
ab dem Stichtag **jeden Tag rot** geworden, ohne Code-Änderung. Deshalb: Fristen
werden gegen das **Entscheidungsdatum aus den Daten** gemessen (Spanne ≥ 97 und
≤ 730 Tage), eine abgelaufene Frist steht im **Bericht** und als `::warning`,
nie im Exit-Code (Vorbild `fristen_check.py`), und
`selftest_clock.py --trap-modul scripts.tests.test_robustheits_gate --offset 97`
läuft im Robustheits-Lauf mit. Wer einen Test schreibt, der die Wanduhr liest,
baut eine Zeitbombe – `scripts/selftest_clock.py` erklärt die Klasse. Aktuell eine: `head.html` (KRITISCH
versiegelt, R8) – der nackte `localStorage`-Zugriff dort ist PaperMod-Erbe und
durch `disableThemeToggle = true` tot; ihn zu ändern braucht eine menschliche
Signatur.

Runbook: `docs/ANLEITUNG-ROBUSTHEIT.md` · Befund und Beweis:
`ROBUSTHEIT-PREMIUM-2026-10-07.md`

### „Im Artikel“ bleibt Premium (Wache seit 27.09.2026)

Die schwebende Artikel-Navigation ist zweimal (26.09.2026) an einem
harmlos aussehenden Refactoring zerbrochen. Deshalb ist ihr Premium-Zustand
jetzt ein **geprüfter Vertrag**, nicht eine Absicht:
`python3 scripts/mini_toc_premium_guard.py` (V1–V14: Vollständigkeit,
feste Kopfzeile, Geometrie an `--main-width`, Ruhzustand, Breakpoint,
Druck, Reduced Motion, Dark Mode, Materialtiefe, Fokus-Ring, keine
Inline-Farben, kein Line-Clamp). Der Selbsttest sabotiert die Wache selbst
und verlangt, dass sie es merkt. Läuft in `npm run test:toc`.
