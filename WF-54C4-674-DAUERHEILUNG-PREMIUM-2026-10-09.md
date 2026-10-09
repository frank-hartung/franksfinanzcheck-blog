# Veröffentlichung WF-54C4 · #674 – Dauerheilung

**Datum:** 09.10.2026
**Auslöser:** Der Deploy-Lauf [37931543847](https://github.com/frank-hartung/franksfinanzcheck-blog/actions/runs/37931543847) stoppte im Schritt **„Release-Scorecard (Produktionswahrheit versiegeln, fail-closed)“**. Der automatische Alert eröffnete Issue [#674](https://github.com/frank-hartung/franksfinanzcheck-blog/issues/674) im Kanal **WF-54C4 / Veröffentlichung**. Weitere Deploy-Läufe zeigten dieselbe Fehlerklasse.

## Befund

Der Scorecard-Bestand und der Publish-Pfad hatten bei Redundanz zwei verschiedene
Einstiegspunkte:

1. `publish_gate.py` prüfte Kandidaten nicht mit `duplikat_guard`.
2. `release_scorecard.py` rief die Duplikat-Wache dagegen selbst auf – also erst
   **nach** dem Publish-Gate und unmittelbar vor der Auslieferung.
3. Bei Cross-Artikel-Funden D3/D4 schrieb die alte Scorecard den Befund nur dem
   lexikografisch ersten Dateipfad zu. Welcher der beiden betroffenen Artikel
   rot erschien, hing damit von der Sortierung ab statt von der Beteiligung.

Der konkrete Befund war ein D3-X-Treffer für
`2026-10-07-7-gewohnheiten-fuer-finanzielle-freiheit`: Die abschließende
Tagesgeld-CTA war wortgleich mit der CTA im ETF-Sparplan-Artikel. Der vorherige
Fix aus #672 hatte eine andere Passage verändert; der tatsächlich gemeldete
CTA-Block blieb bestehen. So konnte das Publish-Gate grün werden, während die
Scorecard den späteren Deploy fail-closed stoppte.

Das war kein Anlass, die Redundanz-Wache zu lockern: Doppelte CTAs schwächen
Eigenständigkeit, Leserführung und die Verlässlichkeit der Produktionswahrheit.
Die Reparatur liegt deshalb am gemeinsamen Messweg und am konkreten Text.

## Dauerhafte Reparatur

### Ein gemeinsamer, schreibfreier Collector

`publish_gate.duplicate_failures(candidates)` ist nun der alleinige Adapter für
D1–D6:

- Er nutzt weiterhin `duplikat_guard` als fachlichen Detektor und verändert
  keinen Content.
- Interne Funde D1/D2/D5/D6 werden dem jeweiligen Kandidaten zugeordnet.
- Cross-Artikel-Funde D3/D4 werden **beiden** Seiten zugeordnet. Ein Kandidat
  wird damit auch dann zuverlässig blockiert, wenn er beim Sortieren der
  zweite Pfad ist.
- Ein nicht ausführbarer Detektor ist ein Werkzeugfehler. Das Publish-Gate
  stoppt dann fail-closed, ohne einen Artikel zu verwerfen oder zurückzustufen.

Das Publish-Gate ruft den Collector vor seiner Entscheidung auf. Die
Release-Scorecard ruft exakt denselben Collector für den Live-Bestand auf; ihre
eigene Duplikat-Schleife entfällt. `RD1-duplikate` ist außerdem in
`PUBLISH_GATE_HART_FAMILIEN` aufgenommen und damit durch C19 gegen ein erneutes
Auseinanderlaufen von Gate und Scorecard abgesichert.

Die Duplikat-Wache akzeptiert optional einen Repository-Root. Das macht die
Messung in isolierten Tests möglich, ohne die Produktionswache oder ihren
Standardpfad zu verändern.

### Konkreter Inhaltsbefund beseitigt

Die CTA des Gewohnheiten-Artikels bleibt ein passender, registrierter Link auf
`/go/tagesgeld/`, spricht nun aber den Artikelkontext an:

> Rücklagen flexibel parken: C24-Tagesgeld mit aktuellem Zins prüfen

Damit entfällt die wortgleiche Kopie, ohne Affiliate-Ziel, Offenlegung oder
Lesernutzen zu verändern.

## Regressionen und Nachweis

Neu: `scripts/tests/test_publish_gate_duplicates.py`.

1. Ein D3-Fund blockiert explizit den **lexikografisch zweiten** Kandidaten.
2. Duplikate ausschließlich zwischen unbeteiligten Bestandsartikeln blockieren
   keinen anderen Kandidaten.
3. Der konkrete Tagesgeld-CTA-Befund aus #674 bleibt gegen den gesamten Bestand
   frei von D1–D6-Funden.
4. Die Scorecard-Tests prüfen zusätzlich, dass sie
   `publish_gate.duplicate_failures` verwendet und keine zweite
   `duplikat_guard`-Messschleife einführt.

Lokal ausgeführt (Python 3.11, PyYAML 6.0.3, Hugo Extended 0.164.0):

| Nachweis | Ergebnis |
|---|---|
| `python3 -m unittest scripts.tests.test_publish_gate_duplicates scripts.tests.test_release_scorecard scripts.tests.test_publish_gate_faktenfrische scripts.tests.test_editorial_review_gate scripts.tests.test_publication_reliability` | **123 Tests grün** |
| `python3 scripts/duplikat_guard.py --selftest` | **7 Sabotage-/Gegenproben grün** |
| `python3 scripts/release_scorecard.py --selftest` | **grün**, einschließlich C19-Deckung und Exit-Vertrag |
| `hugo --minify --destination public --cleanDestinationDir` | **grün**, 82 Seiten |
| `python3 scripts/release_scorecard.py --kandidaten --json` | **Exit 0**, beide Tageskandidaten ohne Werkzeugfehler; Dimension `redundanz: bestanden` |
| `python3 scripts/publish_gate.py --dry-run --strict` | **Exit 0**, 0/2 Kandidaten am Gate gescheitert |

Die beiden Kandidaten tragen weiterhin bestehende, nicht blockierende
Technik-Warnungen. Sie sind weder Redundanz- noch Auslieferungsblocker und der
Scorecard-Exit bleibt deshalb 0.

## Abschluss

Der nächste echte Deploy bestätigt zusätzlich die CI-Ausführung mit dem
Repository-Token und dem Pages-Deployment. Der Codepfad, der #674 ausgelöst
hat, ist lokal vollständig reproduziert und geschützt: Eine D1–D6-Abweichung
kann nicht mehr erst in der Scorecard entstehen, nachdem das Publish-Gate grün
war.
