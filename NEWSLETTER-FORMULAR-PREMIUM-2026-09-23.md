# Newsletter-Formular: Veröffentlichungsmodus Dienstag/Freitag auf Agentur-Niveau

Stand: 23.09.2026. Arbeitszweig `arena/01a0cf9d-franksfinanzcheck-blog`. Es wurde
**kein** Newsletter versendet, kein Brevo-Konto angefasst und keine versiegelte
Kerndatei geändert (`python3 scripts/integrity_guard.py --drift-audit`: „Kein
Drift – 43 Kerndateien entsprechen dem signierten Stand“).

## 1. Ausgangslage

Der Auftrag: „Das Formular auf den Veröffentlichungsmodus Dienstag und Freitag auf
Premium-Level einer Profi-Agentur anpassen.“ Gemeint ist der Anmeldekasten auf
`/newsletter/` (`layouts/shortcodes/newsletter_form.html`). Gemessener Befund vor
der Änderung: Das Formular verkaufte ein Abo **ohne Kalender** – der Takt
(dienstags der Wochen-Check, freitags der Wochen-Abschluss) stand nur als
Fließtext im Lead-Satz und in der Statuszeile; zwischen „anmelden“ und dem ersten
Mail lag für den Leser nichts Greifbares. Drei Lücken:

| # | Befund | Beleg |
|---|---|---|
| 1 | **Kein sichtbarer Versandplan.** Die beiden Ausgaben (Name, Auftrag, Rhythmus) tauchten im Kasten nicht auf – der Leser sah erst im Postfach, wofür er sich eingetragen hat. | `newsletter_form.html` vor der Änderung: nur Lead, Felder, Consent, Status. |
| 2 | **Kein nächster Termin.** Weder statisch (würde über Nacht altern) noch gerechnet – die einzige Terminzusage war „am nächsten Dienstag oder Freitag“. | Statuszeile vor der Änderung. |
| 3 | **Fakten ohne Quelle im Markup.** Wochentage und Uhrzeit waren an mehreren Stellen abgetippt statt aus dem Versandvertrag gelesen – dieselbe Drift-Quelle, die am 23.09.2026 schon die Betreff-Rotation gebrochen hat (Locale-Falle). | `grep "07:05"` in `content/` und `layouts/`. |

## 2. Was jetzt im Formular steht

Der neue Baustein `layouts/_partials/newsletter_versandplan.html` sitzt **vor** dem
Feld (Inline-Formular UND Button-Weg, **nicht** im Leerzustand – ein Takt ohne
Anmeldung wäre Werbung):

* **Kicker** „Versandplan · Dienstag und Freitag“ und der Satz zur ersten Ausgabe
  mit reserviertem Platz für den Termin.
* **Zwei Kacheln**, eine je Versandtag: Badge (Di/Fr), Wochentag, Ausgabenname
  (*Wochen-Check* / *Wochen-Abschluss*), Auftrag je Tag, darunter die Zeile
  „Nächster Termin“ mit gerechnetem Datum. Am Versandtag markiert eine Kante und
  ein „heute“-Marker die Kachel – als Tatsache, nicht als Countdown.
* **Vertrauenszeile** mit vier Zusagen, alle aus der Konfiguration: Double-Opt-In,
  höchstens 2 Mails pro Kalenderwoche, Abmeldung mit einem Klick, kein
  Öffnungs-Tracking (letzte entfällt automatisch, wenn Tracking je eingeschaltet
  wird).
* **Form-Politur:** Klartext unter dem CTA („Kostenlos · 2 Mails pro Woche ·
  Abmeldung mit einem Klick“), Statuszeile mit Tagen und Uhrzeit aus dem Vertrag.

Gestaltet nach DESIGN.md: Tokens statt Hex im Markup, Radius 12/16, Schatten mit
Versatz, Dark-Mode-Varianten für jede Fläche, Fokus sichtbar, `prefers-reduced-motion`
ohne Bewegung, keine Layout-Properties animiert. Kontraste im Browser **gemessen**
(hell und dunkel ≥ 4,5:1, Playwright), nicht geschätzt.

## 3. Ein Vertrag, eine Stelle

* `scripts/newsletter_schedule.py` schreibt den Snapshot
  `data/newsletter_kadenz.json` (`--export-site`, Drift-Check `--pruefen-site`).
  Der Snapshot trägt **bewusst kein Kalenderdatum** – ein gedruckter Termin ist am
  Tag nach dem Bau falsch.
* `layouts/_partials/newsletter_studio_data.html` liefert zusätzlich `kadenz`
  (Fakten aus dem Snapshot) und `rahmen` (Redaktion aus `creative.kadenz`) –
  dieselbe Teilung wie `studio.kadenz_rahmen()` im Python.
* Den nächsten Termin rechnet `static/premium/ff-newsletter.js` in
  **Europe/Berlin** (`Intl.DateTimeFormat` mit geprüfter `timeZone`): Kacheln
  zeigen „Di, 29.09.“, die erste Ausgabe „Freitag, 25. September“. Heute zählt nur
  vor der Versanduhrzeit als Termin – „heute“ ist ein Fakt, kein Versprechen, das
  der Double-Opt-In noch kippen kann. **Ohne JavaScript bleibt der kadenzrichtige
  Satz ohne Datum stehen** – ehrlich statt falsch.

## 4. Geänderte Dateien

```
scripts/newsletter_schedule.py                (Snapshot-Export, --pruefen-site, gerechnete Winterzeit)
data/newsletter_kadenz.json                   (generierter Snapshot des Vertrags)
layouts/_partials/newsletter_studio_data.html (liefert kadenz + rahmen)
layouts/_partials/newsletter_versandplan.html (neu: der Takt vor dem Feld)
layouts/shortcodes/newsletter_form.html       (Plan eingebaut, Status/Hinweis aus Vertrag)
static/premium/ff-newsletter.js               (Terminrechnung in Europe/Berlin)
assets/css/extended/zz-newsletter.css         (Versandplan, Dark Mode, 320px)
scripts/tests/test_newsletter_schedule.py     (Snapshot == Vertrag, CLI, kein Datum)
scripts/tests/test_newsletter_site.py         (class Versandplan, Hooks aus Form+Plan)
e2e/newsletter.spec.mjs                       (Termin gerechnet, ohne JS ehrlich, Kontrast)
docs/ANLEITUNG-NEWSLETTER.md                  (Snapshot-Pfad dokumentiert)
```

## 5. Verifikation

Hugo Extended (PyPI-Quelle, v0.166.0), Chromium aus dem dokumentierten
`@sparticuz/chromium`-Fallback. Mutationstests: Wochentag bzw. Datum ins Markup
gelegt → die zugehörige Wache schlägt an; zurückgebaut → grün.

| Prüfung | Ergebnis |
|---|---|
| `hugo --gc --minify --destination public` | erfolgreich (205 Seiten) |
| `python3 -m unittest discover -s scripts/tests` (mit PyYAML) | **761 Tests grün**, 19 Skip |
| `python3 scripts/newsletter_schedule.py --pruefen-site` | Snapshot entspricht dem Vertrag |
| `npx playwright test` (volle Suite, Desktop+Mobile, hell/dunkel) | **53 Tests grün** (vorher 51, +2) |
| `python3 scripts/layout_audit.py` | ✅ OK, interne Links 0 kaputt |
| `python3 scripts/dom_audit.py --top 5` | alle Grenzen im Budget (max. 976 Elemente) |
| `python3 scripts/seo_cockpit.py --strict` | 213 Seiten, P1/P2/P3: 0 |
| `python3 scripts/newsletter_digest.py --check` | aktiv – Capture-Kette greift |
| `python3 scripts/integrity_guard.py --drift-audit` | **kein Drift**, 43 Kerndateien |
| `git diff --check` | sauber |

Gemessene Terminrechnung (Browser, 23.09.2026, Europe/Berlin): erste Ausgabe
„Freitag, 25. September“, Kacheln „Di, 29.09.“ / „Fr, 25.09.“; am Versandtag vor
07:05 zählt „heute“, danach der Folgetermin. Zehn Kalender-Fälle (Monatsende,
Jahreswechsel, Schaltjahr) im Harness grün.

## 6. Offen – Entscheidungen, die ein Mensch trifft

**Owner: human · Severity: P3 · Channel: Redaktionsfreigabe**

1. **Wortlaut der Kachel-Aufträge** ist Redaktion (`creative.kadenz.preheader_hinweis`)
   und darf sich ändern – die Wachen prüfen nur, dass je Versandtag ein Eintrag
   existiert und nichts im Markup getippt ist.
2. **„heute“-Marker:** erscheint nur am Versandtag vor dem Versand. Wer den Marker
   lieber nie sehen will, entfernt die `classList.add(...)`-Zeile in
   `static/premium/ff-newsletter.js` – die Kachelkante (`--heute`) entfällt dann mit.
3. Der Snapshot muss nach jeder Vertragsänderung neu geschrieben werden
   (`--export-site`); `--pruefen-site` und die Tests erinnern daran.
