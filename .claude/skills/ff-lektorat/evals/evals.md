# Lektorat-Evals (Deutsch)

> Stand 01.11.2026: Diese Datei hieß `evals-de.json`, enthielt aber nie JSON,
> sondern Markdown. Sie liegt jetzt im eigenen Haus (`ff-lektorat`) und trägt die
> Endung, die zu ihrem Inhalt passt. Maschinenlesbare Fälle würden als JSON
> danebenliegen, nicht als Anhang.

Eingefrorene Testfälle für den Copy-Editing-Prozess. Jeder Fall muss vor einem Change an den Engines grün sein.

## E1: Grammatik LT1–LT4 (offline)

| Eingang | Erwarteter Ausgang | Regel |
|---|---|---|
| „Du sparst seid drei Jahren Geld.“ | „Du sparst seit drei Jahren Geld.“ | LT3 seid/seit |
| „im gegensatz dazu kostet es mehr.“ | „im Gegensatz dazu kostet es mehr.“ | LT2 Kollokation |
| „ansonten funktioniert es nicht.“ | „ansonsten funktioniert es nicht.“ | LT4 Fehlschreibung |
| „Das ist das Werkzeug, wo mit du sparst.“ | „Das ist das Werkzeug, womit du sparst.“ | LT1 Partikel |
| „Ihr seid bereit.“ | unverändert (Negativ-Falle) | LT3 Verb-Schutz |
| "`vorallem` bleibt im Code unangetastet." | unverändert | Schutzzonen |

## E2: Sprachglatt DW1–DW9

| Eingang | Erwarteter Ausgang | Regel |
|---|---|---|
| „Er ist der Meinung, dass es klappt.“ | „Er meint, dass es klappt.“ | DW1 |
| „Du bist in der Lage, Geld zu sparen.“ | „Du kannst Geld sparen.“ | DW2 |
| „Wir müssen eine Entscheidung treffen.“ | „Wir müssen entscheiden.“ | DW6 |
| „in Betracht ziehen“ | „erwägen“ | DW5 |
| „Das kommt nicht in Betracht.“ | unverändert (Negativ-Falle) | DW5 Schutz |

## E3: Hardcases H1–H9

| Eingang | Erwarteter Ausgang | Regel |
|---|---|---|
| „Das ist die einzigste Option.“ | „Das ist die einzige Option.“ | H1 |
| „das selbe Problem“ | „dasselbe Problem“ | H2 |
| „darauf hin kündige ich.“ | „daraufhin kündige ich.“ | H3 |
| „weisser Schimmel“ | „Schimmel“ | H6 Pleonasmus |
| „große Straße“ (mit ß) | unverändert (Norm-ß) | H9 ß/ss Schutz |

## E4: Lektorat L1–L12

| Eingang | Erwarteter Ausgang | Regel |
|---|---|---|
| „der der Antragsteller“ | „der Antragsteller“ | L1 Wortduplikat |
| „Es ist zu beachten, dass …“ | „Wichtig: …“ | L2 Füllphrase |
| „Sie/Ihnen/Ihre“ (Einzelner) | „du/dein“ (Hausduktus) | L3 Personenkonsistenz |
| „!!!“ | „!“ | L4 Ausrufezeichen |
| „3 Tipps“ → „drei Tipps“ | (Zahlenschreibweise 2–12) | L10 |

## E5: AI-Tells (deutsch)

| Eingang | Erwarteter Ausgang | Muster |
|---|---|---|
| „Nicht X, sondern Y.“ | „Y. Grund: …“ | A1 Kontrast-Offenbarung |
| „Kein Termin, keine Unterlagen, kein Warten.“ | „Sie legen direkt los – ohne Termin und Papierkram.“ | A2 Verneinungs-Liste |
| „In der heutigen schnelllebigen Welt …“ | (konkreter Einstieg mit Problem/Fakt) | A6 Stock-Opening |

## E6: Lesbarkeit

| Eingang | Erwartet | Schwelle |
|---|---|---|
| Artikel mit Ø 22 Wörtern/Satz | Report: Satzlänge zu hoch | Ø ≤ 16 |
| Flesch-Amstad 44,3 | Report: unter Ziel | ≥ 60 (neu), ≥ 62 (Bestand) |
