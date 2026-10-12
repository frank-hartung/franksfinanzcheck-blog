# Content-Reserve WF-D4E0 · #710 – Dauerheilung auf Premium-Niveau

**Datum:** 12.10.2026
**Auslöser:** Der Content-Reserve-Lauf **38240822821** (Schedule, 12.10.2026 11:09 UTC) wurde im Schritt **„Stock shortage must not look successful“** rot; das Fehler-Alerting meldete das als Issue **#710** (`auto-report`, Alert-Key `WF-D4E0`, Bereich *Inhaltsqualität*).
**Stand vorher:** **5/6** gate-fertig (Ziel 6) – ein Kandidat fehlte.
**Stand nach der Reparatur:** **7/6** gate-fertig (7 Kandidaten am echten Produktions-Gate zertifiziert).

---

## Kurzfassung

Der Vorrat war nicht leer – er stand bei 5/6. Sechs der elf Pool-Kandidaten scheiterten an **einer einzigen Klasse**: RS5 (Zahlen ohne Satzbeleg oder Modell-Kennzeichnung). Die Wurzel lag nicht im Bestand, sondern **bei der Geburt**: Der Generierungs-Prompt in `generate_drafts.py` lehrte das Modell, harte Zahlen mit „ca./rund/etwa“ einzuordnen – das harte RS5-Gate wertet solche Abschwächungen ausdrücklich **nicht** als Beleg. Prompt und Gate widersprachen sich; jeder frisch erzeugte Kandidat trug die ablehnende Klasse bereits in sich.

Geheilt wurden der Bestand (zwei Kandidaten redaktionell, ohne erfundene Quellen) und die Ursache (Prompt an das Gate angeglichen, per Vertragstest verriegelt). Kein Gate wurde abgesenkt.

## Befund

| Kandidat (2026-10-12) | Blocker |
|---|---|
| dein-weg-zu-geringeren-monatskosten | RS5: 6 Sätze (Hook-Zahl, Kürze-Spanne, Faustregel-Prozent …) |
| haushaltskosten-reduzieren | RS5: 3 Sätze (Hook-Statistik „1.000 €“, Bank-Spanne, Ergebnis-Satz) |
| energieausweis | RS3 + RS4 + RS5 (16) + Flesch 59,0 |
| kleine-energiespar-tricks | RS5 (34) |
| stromkosten-senken | RS5 (43) |
| waermepumpe-vs-gasheizung | RS5 (29) + Flesch 59,6 |

Zusätzlich trugen zwei Kandidaten Titel-Artefakte aus dem Keyword-Stempel („Dein Weg zu geringeren: Monatskosten“, „Praktische Mitteln“) – auf Profi-Niveau nicht tragbar.

## Heilung des Bestands (redaktionell, ehrlich)

* **haushaltskosten-reduzieren:** Erfundene Hook-Statistik („durchschnittlicher Haushalt … 1.000 €“) ersatzlos gestrichen; Bankgebühren-Spanne als Beispielrechnung mit Bedingung gekennzeichnet; Ergebnis-Satz trägt sein Modell-Label selbst; Kurzantwort (unbelegte „bis zu 20 %“) auf das Artikel-Modell zurückgeführt; Grammatik („Praktische Mitteln“ → „Praktische Mittel“) korrigiert.
* **dein-weg-zu-geringeren-monatskosten:** Hook-Zahl als Ergebnis der Modellrechnung gekennzeichnet; Kürze-Box nennt statt erfundener Spanne (500–1.200 €) das echte Modell-Ergebnis (1.332 €); Scheinpräzision entfernt (Faustregel-Prozent, starre 24-Monats-Zahlen); Titel-/Pin-/Alt-Artefakt „geringeren: Monatskosten“ bereinigt; Kurzantwort ohne unbelegte 10-%-Forderung.
* **Zertifizierung am echten Gate:** Beide Kandidaten lokal mit Hugo 0.164 Extended + Publish-Gate STRICT über `reserve_readiness.certify_one` gemessen: je `ready: true` (Flesch 60,8 / 60,1; Score 0,898 / 0,894 bei lokal fehlendem hunspell, also strenger als CI). Das Zertifikat wurde atomar über `schreibe_zertifikat` erneuert (gleicher Zeitstempel – die übrigen neun Zeilen stammen unverändert aus der CI-Messung vom selben Tag).

## Dauerheilung (Ursache)

1. **Prompt ↔ Gate angeglichen** (`scripts/generate_drafts.py`): Punkt 5 des Redaktions-Standards verlangt jetzt im selben Satz Quellenlink **oder** ausdrückliche Beispielrechnungs-/Modell-Kennzeichnung und erklärt „ca./rund/etwa“ für gate-wertlos. Die Kürze-Box-Anweisung („Zahlen nur als Spannen“) wurde ebenfalls auf die Gate-Wahrheit gezogen. Da Entwürfe keine Links erfinden dürfen, steuert der Prompt Beträge in ausgewiesene Modellrechnungen mit Annahmen – oder lässt die Zahl weg.
2. **Vertragstest** (`scripts/tests/test_zahlen_prompt_vertrag.py`, 6 Fälle): Verriegelt Prompt-Formel und Gate-Semantik gegeneinander (Hedge fällt durch, Modell/Link bestehen). Fällt der Prompt je wieder auf die Hedge-Formel zurück, wird der Testlauf rot, bevor ein Kandidat geboren wird.

Bewusst **kein** deterministischer RS5-Auto-Heiler: Unbelegte Marktzahlen nachträglich per Skript zu „Modellrechnungen“ umzuetikettieren, würde Scheinbelege erzeugen. Die Heilung gehört an die Geburt (Prompt + Geburts-Gate mit Korrektur-Auftrag) und – für den Altbestand – in die Redaktion, nicht in einen Etikettier-Automaten.

## Nachweise (12.10.2026, lokal)

```
python3 scripts/reserve_gate.py
→ ✅ Reserve-Pool gate-fertig: 7/6 Kandidaten zertifiziert. (Exit 0)

python3 scripts/artefakt_waechter.py
→ ✅ 397 Artefakte strukturell heil

python3 -m unittest discover -s scripts/tests -p "test_reserve*.py"   → 223 OK
python3 -m unittest discover -s scripts/tests -p "test_redaktions*.py" → 8 OK
python3 -m unittest scripts.tests.test_zahlen_prompt_vertrag           → 6 OK
python3 scripts/redaktions_standard.py --selftest                      → 31 OK
```

## Grenzen (ehrlich benannt)

* Vier Kandidaten (energieausweis, kleine-energiespar-tricks, stromkosten-senken, waermepumpe) bleiben an RS5/Flesch blockiert – das ist der redaktionelle bzw. KI-Heiler-Pfad der nächsten Nächte, kein Gate wurde für sie gesenkt.
* Die lokale Messung lief ohne `hunspell` (in der Sandbox nicht installierbar): `spelling = 0.5` („unbekannt“) macht die lokalen Scores **strenger** als CI; der nächste Nachtlauf zertifiziert den Pool in CI ohnehin vollständig neu.
* Der nächste planmäßige Reserve-Lauf muss auf `main` grün durchlaufen; erst dann schließt das Alerting #710 automatisch.
