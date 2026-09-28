# Content-Reserve #28 / Issue #436 – dauerhafte Premium-Reparatur

**Vorfall:** Workflow „Content-Reserve (täglicher Vorrat)“, Run
[`36407111494`](https://github.com/frank-hartung/franksfinanzcheck-blog/actions/runs/36407111494),
28.09.2026 · **43:15 Minuten · rot · 1/6 READY**. Der harte End-Gate
„Stock shortage must not look successful“ hat korrekt ausgelöst. Die Messlatte
bleibt bei 6; kein Publish-Gate wurde abgeschaltet oder abgesenkt.

## 1. Beweislage aus dem Lauf

Das vom Lauf selbst nach `main` geschriebene Zertifikat und Themen-Gedächtnis
zeigen vier voneinander unabhängige Ursachen:

1. **Produktionsverlust vor der Werkbank:** 15 Themen erhielten je
   drei Antworten, die überwiegend nur am Längen-Floor scheiterten. Die
   gelieferten Texte hatten 629–1.245 Wörter. Beispiele: DSL 690, Kleidung
   876/866, Glasfaser 784, Hauskauf 685/751, Tierversicherung 732,
   Krankenzusatz 1.245 Wörter. Obwohl die folgende Reserve-Stufe bereits einen
   dateibezirkelten Längenheiler besitzt, verwarf das Geburts-Gate jeden Text
   vorher vollständig. Drei Themen gelangen zufällig; der Pool konnte das Ziel
   deshalb auch nach drei Konvergenz-Runden nicht erreichen.
2. **Ungedeckelte Wörterbuch-Lücken:** Der Camping-Kandidat erhielt wegen 27
   `unknown`-Befunden (Hunspell-Lücken mit Konfidenz 0) einen Rechtschreibwert
   von 0,46. Das drückte den Gesamtwert auf **0,826 < 0,85**, obwohl echte
   Tipp-, Phrasen- und Großschreibfehler separat klassifiziert werden.
3. **Unheilbarer IW3-Fund:** Der ETF-Kandidat versprach in einem In-Text-Satz
   einen Broker-Vergleich, verlinkte aber das Einzelangebot der C24 Bank:
   `[/go/tagesgeld/ der C24 Bank](/go/tagesgeld/)`. Das Intent-Gate urteilte
   fachlich richtig. Weil In-Text-Prosa grundsätzlich `owner=human` ist, konnte
   die automatisierte Reserve den selbst erzeugten Werbesatz aber niemals
   schließen.
4. **Impliziter Gemini-Ausgabevertrag:** Der Gemini-Pfad setzte weder
   `maxOutputTokens` noch Temperatur und las nur den ersten Antwort-Part.
   Zahlreiche Themenversuche endeten als „leere Antwort (GEMINI)“.

Die drei gespeicherten Kandidaten waren daher nur zu **1/6** reif:

| Kandidat | Befund im Lauf | Reparaturwirkung |
|---|---|---|
| Büroausstattung | READY, Score 0,864 | bleibt READY |
| Camping | Score 0,826; spelling 0,46 | konservativer Replay: **0,894** |
| ETF-Sparplan | IW3 Einzelangebot statt Vergleich | Werbesatz sicher entkommerzialisiert; Intent danach 0 Funde |

## 2. Dauerhafte Reparatur

### 2.1 Werkbank statt Wegwerfproduktion

`scripts/engine_generate.py` trennt jetzt strikt zwischen Geburt und
Veröffentlichung:

- Nur die **Reserve** darf einen substanziellen Rohtext ab 550 Wörtern und vier
  H2 in die nachfolgende Werkbank geben.
- Zulässig sind ausschließlich die belegten Heilerklassen **Länge** und
  **Keyword-Platzierung**. Fehlendes FAQ, Pflichtmodul, Struktur oder
  KI-Floskeln bleiben bereits an der Geburt hart.
- Live-Generierung nutzt die Ausnahme nicht.
- `reserve_readiness.py` zertifiziert nach der Werkbank weiterhin gegen die
  unveränderten echten Publish-Gates. Eine Vorstufe ist niemals READY.

Damit werden die im Vorfall weggeworfenen 629–1.245-Wörter-Texte vom bereits
vorhandenen `check_length.py`/`extend_articles.py` veredelt, statt bis zu 48
weitere Vollgenerierungen zu bezahlen.

### 2.2 Ehrliche Rechtschreibmetrik für neue Fachgebiete

`scripts/quality_score.py` behandelt die Klassen jetzt gemäß ihrer
Beweiskraft:

- echte `typo`-/`phrase`-/`noun_case`-Funde: weiterhin **−0,10 je Fund,
  ungekappt**;
- `unknown`: −0,02 je **verschiedenem** Wörterbuch-Eintrag, höchstens −0,20
  pro Artikel;
- Wiederholungen desselben Fachbegriffs zählen nur einmal.

Das ist keine Gate-Absenkung: `unknown` ist laut Spellcheck ausdrücklich ein
Wörterbuch-Loch ohne belastbaren Korrekturvorschlag. Echte Fehler bleiben hart.
Der konservative Replay mit allen 27 Funden als verschieden hebt Camping von
0,826 auf **0,894** und damit ehrlich über 0,85.

### 2.3 IW3 mit enger Besitzgrenze

`scripts/affiliate_intent_guard.py` erhält einen bewusst engen Schließpfad:

- nur bei `draft: true` + `reserve: true` + `ai_generated: true`;
- nur für human-owned IW3 in normaler In-Text-Prosa;
- keine KI-Umschreibung und keine erfundene Ersatzbehauptung;
- der vollständige unehrliche Werbesatz wird entfernt, Nachbarsätze und
  kanonische CTAs bleiben erhalten;
- Tabellen, Listen, Überschriften, Zitate, Live- und Menschen-Content bleiben
  weiter fail-closed bei `owner=human`.

Der reale ETF-Satz wurde im Regressionstest bytegetreu nachgebaut: Danach
bleiben zwei ehrliche C24-CTAs, der täuschende Prosa-Link ist weg und ein
zweiter Wächterlauf ist idempotent grün.

### 2.4 Provider-Vertrag und Workflow-Hygiene

- Gemini: 8.192 Output-Tokens, Temperatur 0,8, alle Text-Parts werden
  zusammengesetzt; fehlende Candidates bleiben ein ehrlicher Infra-Fund.
- Der versehentlich doppelte Promptblock wurde entfernt.
- `actions/checkout` wurde wegen der Node-20-Warnung des Vorfalls von v4 auf
  v5 gehoben.

## 3. Verifikation

| Prüfung | Ergebnis |
|---|---|
| Vollständige `unittest discover`-Regression | **1.080 Tests grün** |
| `test_quality_score_spelling` + komplette `test_reserve_pipeline` | **82 Tests grün** |
| Neue #436-Verträge | Reserve-Vorstufe, Live-Isolation, IW3-KI-Heilung, Menschen-Schutz, Unknown-Cap/Einmalzählung grün |
| Engine-/Intent-/Heiler-/Konvergenz-/Themen-/End-Gate-Selbsttests | grün |
| `selftest_runner.py` | **113 Wachen · 226 Zukunftsuhr-Proben · grün** |
| `py_compile` der geänderten Python-Dateien | grün |
| `git diff --check` | grün |
| Camping-Score-Replay | 0,826 → **0,894** bei unverändertem Publish-Floor 0,85 |
| Reales ETF-IW3-Fixture | 1 blockierender Fund → **0**, idempotent; Menschen-Fixture bleibt rot/unverändert |

## 4. Bewusste Grenzen

- Kein Secret wurde gelesen oder verändert.
- Kein bestehender Kandidat wurde von Hand als READY gestempelt.
- Das Zertifikat bleibt ein maschineller Nachweis und wird erst im echten Lauf
  neu geschrieben.
- Der End-Gate bleibt rot, solange weniger als sechs Kandidaten alle Gates
  tatsächlich bestehen.

Damit ist nicht das rote Signal kosmetisch beseitigt, sondern der Durchsatz
vor der Werkbank, die fachgebietsneutrale Bewertung und der letzte unheilbare
Maschinen-Fund sind strukturell geschlossen.
