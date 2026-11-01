# Copy-Editing Checkliste (Deutsch) – FranksFinanzcheck Highend

> **Hausgemacht, nicht übernommen** – deutschsprachige Ausgabe des Hauses,
> bis 01.11.2026 im Fremd-Ordner `copy-editing` (dort `references/checkliste-de.md`), seither hier.
> Kein Upstream-Text: wer sie ändert, ändert Hausregeln.

Gilt zusammen mit den Seven Sweeps (SKILL.md) als finaler QA-Durchgang vor jeder Auslieferung.

## Vor dem Start

- [ ] Ziel des Textes geklärt (Awareness, Conversion, Retention)
- [ ] Zielgruppe bekannt
- [ ] Gewünschte Leser-Handlung definiert
- [ ] Einmal komplett gelesen, ohne zu editieren

## Sweep 1 – Klarheit

- [ ] Jeder Satz sofort verständlich
- [ ] Kein Fachjargon ohne Erklärung (ETF, Dispo, Schufa, Girocard …)
- [ ] Pronomen haben eindeutige Bezugswörter
- [ ] Kein Satz versucht, zu viel auf einmal zu sagen
- [ ] Ein Hauptgedanke pro Abschnitt („Rule of One“)
- [ ] Text spricht den Leser direkt an („du“)

## Sweep 2 – Stimme & Ton

- [ ] Einheitlicher Förmlichkeitsgrad durchgehend
- [ ] Markenpersönlichkeit konsistent
- [ ] Keine jähen Stimmungswechsel
- [ ] Laut gelesen: klingt stimmig

## Sweep 3 – „So What?“

- [ ] Jedes Feature hat einen Nutzen-Brücke („was bedeutet das für mich?“)
- [ ] Jede Behauptung beantwortet „Warum sollte mir das etwas bedeuten?“
- [ ] Keine impressiven, aber leeren Aussagen

## Sweep 4 – „Beweis es!“ (YMYL-Belegpflicht)

- [ ] Jede Behauptung ist belegt (Quelle, Rechenbeispiel, Annahmen)
- [ ] Social Proof konkret und benannt (keine anonymen „Tausende Kunden“)
- [ ] Zahlen und Statistiken mit Quelle
- [ ] Keine unbewerteten Superlative („beste“, „führend“ ohne Beleg)
- [ ] Finanz-YMYL: Risikohinweise und Affiliate-Offenlegung vorhanden

## Sweep 5 – Spezifität

- [ ] Vage Wörter durch konkrete ersetzt (spare Zeit → spare 4 Std./Woche)
- [ ] Zahlen und Zeiträume enthalten
- [ ] Generische Aussagen spezifiziert
- [ ] Füll-Inhalte entfernt
- [ ] Keine gerundeten, „erfühlt“ wirkenden Zahlen

## Sweep 6 – Emotion

- [ ] Text löst ein Gefühl aus, nicht nur Information
- [ ] Schmerzpunkte spürbar (Altersarmut, Dispo, Versicherungslücke)
- [ ] Wünsche als erreichbar präsentiert
- [ ] Emotion dient der Botschaft, keine Manipulation

## Sweep 7 – Zero Risk

- [ ] Einwände nahe der CTA adressiert („Ist das sicher?“, „Was kostet das?“)
- [ ] Trust-Signale vorhanden
- [ ] Nächste Schritte kristallklar
- [ ] Risikoumkehr genannt (Geld-zurück, jederzeit kündbar, keine Kreditkarte)

## AI-Tell-Check (Deutsch)

- [ ] Kein „Nicht X, sondern Y“ / „Nicht wegen X. Wegen Y.“
- [ ] Keine Verneinungs-Liste („Kein Termin, keine Unterlagen, kein Warten“)
- [ ] Keine Sätze, die nach dem Hauptanspruch noch Komma-Nebensätze anhäufen
- [ ] Keine selbstbeantworteten Fragen („Das Ergebnis? 3x schneller.“)
- [ ] Keine Doppelpunkt-Offenbarungen („Das Beste daran: Es lernt.“)
- [ ] Keine Stock-Opening („In der heutigen schnelllebigen Welt“, „Ob Sie … oder …“, „Hier ist das Ding“)
- [ ] Keine Em-Dashes in Headlines, Subheads, CTAs; max. 1–2 pro Seite im Fließtext
- [ ] Max. ein Fragment und eine Dreier-Liste pro Abschnitt
- [ ] Jedes vage Adjektiv durch den Fakt ersetzt, für den es stand

## Final-Checks

- [ ] Keine Tipp- oder Grammatikfehler
- [ ] Einheitliche Formatierung
- [ ] Links funktionieren (falls zutreffend)
- [ ] Kernbotschaft durch alle Edits erhalten
- [ ] Menschliche Endredaktion hat freigegeben (`scripts/endredaktion.py`)

## Automatisierte Gates (Exit 0 erforderlich)

- [ ] `scripts/grammar_check.py` (LT1–LT4) – keine offenen Funde
- [ ] `scripts/hardcases_guard.py` (H1–H9) – keine offenen Funde
- [ ] `scripts/zeit_rechtschreibung.py` (ZEIT-Niveau) – keine kritischen Funde
- [ ] `scripts/sprachglatt.py` (DW1–DW9) – keine kritischen Glätt-Funde
- [ ] `scripts/lektor_guard.py` (L1–L12) – keine kritischen Lektorat-Funde
- [ ] `scripts/readability_check.py` – Flesch-Amstad ≥ 60, Ø Satz ≤ 16 Wörter
