# Release-Scorecard: Produktionswahrheit wieder grün (#796)

**Auftrag (Frank, 18.10.2026):** „Run failed: Release-Scorecard (Produktionswahrheit) – main (c984f17). Bitte dauerhaft auf Highend-Level einer Profi-Agentur beheben.“

**Prüfmaßstab:** exakt der Lauf der Wache – Hugo Extended 0.164.0 bauen (Beweisbasis `public/`), dann `scripts/release_scorecard.py --live --streng` über die Collector-Funktionen des Publish-Gates. **Keine Ausnahme, keine geschwächte Schwelle, keine zweite Messregel** (Vertragsregeln C15/C19; Bestandsreparatur nach Vorgang #732 und `docs/ANLEITUNG-RELEASE-SCORECARD.md`).

---

## Kurzfassung

Die Tageswache meldete beim Lauf vom 18.10. (07:07 MESZ, run 39115588269) **1 blockierten** Live-Artikel:

- `2026-08-31-stoerung-beim-internetanbieter-so-sicherst-du-deine-rechte` – **T5-lesbarkeit**: Flesch **59.5** unter der Publish-Schwelle 60 (#585) · Score 75 (Punktlandung) · 12 Passiv-Formulierungen · 1 Absatz > 4 Sätze.

Zusätzlich standen drei **Warnungen ohne Blockade** (T1w-zeichenlaenge-optimum) im Report: zwei Artikel knapp unter dem Längen-Optimum (10.977 / 10.404 Zeichen), einer 8 Zeichen darüber (18.008).

Der Bestand ist jetzt **60/60 freigabe-reif, 0 blockiert, 0 Warnungen, 0 Werkzeugfehler** – gemessen von derselben Engine, die den Lauf rot gemacht hat.

| Kennzahl | vorher (Lauf c984f17 → 39115588269) | nachher |
|---|---|---|
| Live-Artikel freigabe-reif | 57/60 | **60/60** |
| blockiert / nicht beweisbar | 1 | **0** |
| Warnungen ohne Blockade (T1w) | 3 | **0** |
| Technik-Dimension Gesamtbestand | ❌ blockiert | **✅ bestanden** |
| `release_scorecard.py --live --streng` | Exit 1 | **Exit 0** |
| `release_scorecard.py --selftest` | ✅ | ✅ |
| Unit-Tests `test_release_scorecard` | 42 OK | **42 OK** |

## Was blockiert hat – und wie geheilt wurde

### `2026-08-31-stoerung-beim-internetanbieter-so-sicherst-du-deine-rechte` (T5: Flesch 59.5)

Der Heilversuch über `lesbarkeit_heiler.py --file … --auch-live --keine-ki` (Stufe A, Deterministik) hob den Text nur auf 59.6 – das Tor T1 verwarf den Vorschlag fail-closed, die Datei blieb unangetastet. Genau der Fall „Flesch unter Silben-Hebeln“ → **Handarbeit** nach #732-Rezept (37 behutsame Umformulierungen im Fließtext, 31 + 6 Einzelschritte):

- **Flesch 59.5 → 65.8, Score 75 → 100, Passiv 12 → 0, Absatz > 4 Sätze 1 → 0.**
- Hebel = Silben je Wort, nicht Satzlänge (die war mit Ø 11 Wörtern bereits gut): lange Komposita durch Alltagswörter ersetzt („Geschwindigkeitstest“ → „Speedtest“, „Telekommunikationsdiensten … Verbraucherinformationen“ → „Internet und Telefon … Verbraucherinformationen“, „Zugangsmöglichkeit“ → „Zugang“, „Erstattungsfähigkeits-Umkreis“ entschärft, „Servicetelefonate“ → „den Anruf“), dazu zwei Absätze an Ideengrenzen geteilt.
- **Bewahrung verbrieft:** Zahlen-Multiset identisch, alle Linkziele (inkl. `/go/`, § 59 TKG, Bundesnetzagentur, Verbraucherzentrale) unverändert, kein Heading, keine Tabelle, kein Shortcode angetastet; Längen-Messung 13.301 → 12.408 Zeichen, weiter im Optimum. Bewiesen mit derselben Prüffunktion des Heiler-Tors (`lesbarkeit_heiler.bewahre`) + `readability_check --file`.

## Was nur warnte – und jetzt auch sauber ist (T1w, 3 Artikel)

Warnungen stoppen nichts; der Highend-Anspruch des Auftrags ist aber ein Bestand ohne offene Ampeln. Nach #732-Rezept: Lücken mit **einzigartig formulierten FAQ-Antworten im Stil des jeweiligen Artikels** schließen (eine Idee pro Absatz, kurze Sätze, keine erfundenen Zahlen, keine neuen Quellen behauptet), Überlänge durch Straffung von Füllwörtern.

| Artikel | vorher | nachher |
|---|---|---|
| `2026-09-30-last-minute-urlaub-…-sommer-schnaepp` | 18.008 Z. (8 über Optimum) | **17.936 Z. im Optimum** – zwei Füllsätze gestrafft („Es gibt immer …“-Dreifachwiederholung → ein Satz; „bildet aber nicht zwingend alle“ → „bildet aber nicht alle“), Flesch unverändert 61.1, Score 95 |
| `2026-10-07-urlaub-sparen-7-clevere-wege-…` | 10.977 Z. | **12.188 Z. im Optimum** – 4 neue FAQ-Antworten (Überblick Reisekasse, Zahlungsart, Kasse in der Gruppe, Kurztrips); Flesch 61.1 → 62.3, Score 100 |
| `2026-10-07-wie-smart-home-geraete-…` | 10.404 Z. | **12.157 Z. im Optimum** – 5 neue FAQ-Antworten (Messdauer, Geräte-Eignung für Automatik, Ersparnis belegen, Umzug/Mietwohnung, schaltbare Leiste); Flesch 62.5 → 62.6, Score 100 |

Alle drei bestehen nach der Änderung T1 (Länge), T4 (Keyword-Score – die FAQ-Antworten führen die Keywords des Artikels natürlich, die Dichte bleibt im Band), T5 (Lesbarkeit), T6 (Textverständnis inkl. R15) und die Redundanz-/Einzigartigkeitsscan (RD1/RD2, U1) über den **gesamten** Bestand – die neuen Passagen wurden extra einzigartig formuliert und gegen den Korpus gemessen, nicht gegen sich selbst.

## Ursachenanalyse (das „dauerhaft“)

1. **Klasse bekannt, Mechanismus greift:** Der Fund ist exakt die Lücke, die #585 dokumentiert hat – Bestand, der *vor* der Schwellenhärtung live ging und seither nur von der Tageswache gemeldet wird. Das Publish-Gate blockiert neue Artikel unter Flesch 60 hart; Entwürfe und Reserve zieht `lesbarkeit_heiler` (Stufe A/B) nach (`npm run lesbarkeit:nachsorge`). Die Lücke war nie ein Gate-Defekt, sondern offene **Redaktionsarbeit** an einem Alttext (C15: „Die Scorecard heilt nie“).
2. **Der Heiler stößt bei dieser Spielart an seine dokumentierte Grenze:** War ein Text bereits kurz im Satz, aber schwer im Wort (Ø 11 Wörter, 1,87 Silben/Wort), kann Stufe A (Satzschnitte + Füllphrasen) nur Zehntel holen; das Tor wirft den Versuch korrekt weg. Für diesen Fall ist Handarbeit vorgesehen – dieser Lauf hat sie geliefert und mit 65.8 messbar **Puffer über Schwelle** eingebaut, nicht 0.1.
3. **Keine Absenkung, keine Ausnahme:** `data/release_scorecard.yaml` (SSOT), Schwellen in `readability_check.py`, Workflows und Skripte sind **unangetastet**. Der Bestand ist echt besser, nicht weggeklammert.
4. **T1w-Drift ist normal** (Nachpflege-Eingriffe anderer Wachen ändern Zeichenzahlen); der Weg ist vorgezeichnet (#732) und wurde hier zum zweiten Mal sauber durchexerziert. Sollte die Engine künftig systematisch ans Optimum statt an den Floor zielen, ist das eine **Entscheidung der Chefredaktion** (`entscheidung: auto|human` in der SSOT), keine Reparatur im Vorbeigehen.

## Belege (identische Kommandos, identische Umgebung wie der CI-Schritt)

```
hugo --minify --destination public                 → Build OK (v0.164.0+extended)
python3 scripts/release_scorecard.py --selftest    → ✅ bestanden
python3 scripts/release_scorecard.py --live --streng → Exit 0 · 60/60 freigabe-reif, 0 blockiert, 0 Werkzeugfehler
python3 -m unittest scripts.tests.test_release_scorecard → 42 Tests OK
python3 scripts/readability_check.py --selftest    → ✅
python3 scripts/textverstaendnis_guard.py --selftest → ✅ R2–R17
python3 scripts/lesbarkeit_heiler.py --selftest    → ✅ (Tor T1–T4 weist Sabotage ab)
python3 scripts/check_length.py                    → 60 Artikel, 0 Verstöße, 0 Warnungen
```

Siegel und Historie (`data/release_scorecard_state.json`, `data/release_scorecard_history.jsonl`, `RELEASE-SCORECARD.md`) werden bewusst **nicht** aus einer Arbeitsumgebung geschrieben – sie gehören der Wache: Der nächste tägliche Lauf (07:07 MESZ) auf `main` misst neu, versiegelt und schließt Ticket #796 über den eingebauten Schließpfad (C4: Grün schließt das eine Ticket).
