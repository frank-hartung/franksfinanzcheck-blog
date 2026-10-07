# Publikations-Vertrag WF-54C4 · #607 – Dauerheilung

**Datum:** 07.10.2026
**Auslöser:** Der Deploy `Deploy auf GitHub Pages` (Run
`37379833880`, Commit `48e3534f`) wurde als `failure` gemeldet. Der Job
`deploy` (ID `112007817658`) starb nach 41 Sekunden im Schritt
„Release-Scorecard (Produktionswahrheit versiegeln, fail-closed)“ mit Exit 1;
alle folgenden Schritte – einschließlich „Deploy auf gh-pages“ – wurden
übersprungen.

## Befund

Die Scorecard des Laufs meldete wörtlich:

    Release-Scorecard (kandidaten): 32/39 Live-Artikel freigabe-reif,
                                    1 blockiert/unbeweisbar, 0 Werkzeugfehler.
      ❌ 2026-09-10-energie-update-was-sich-jetzt-fuer-dich-aendert (blockiert)
           T5-lesbarkeit: Flesch 44.3 (Mindestwert 60) – ein Artikel unter
           dieser Schwelle zieht den Bestands-Durchschnitt nach unten (#585)
           T6-textverstaendnis: R7-INTRO-FORMEL: „in diesem beitrag“ ×1
           (Template-Sprache – umformulieren)
    Exit 1 (blockierend im Scope).

Der Artikel war 20 Minuten vorher konform: Score 100/100, Flesch 68,7, kein
R7-Fund. Die KI-Heilung des Workflows „Redaktions-Standard neu
(Capital/WiWo/ZEIT)“ (WF-6F7F) hatte ihn mit Commit `2d8fc01` („redaktion:
neue Artikel auf Capital/WiWo/ZEIT-Standard (Wache + Gate)“, 05.10.2026
22:20:20 UTC) neu geschrieben und dabei unter die Veröffentlichungsschwelle
gedrückt; zusätzlich stand danach „In diesem Beitrag erfährst du, worauf es
jetzt ankommt.“ im Text – genau die gesperrte Intro-Formel R7.

Lokal nachgemessen (`python3 scripts/readability_check.py --file …`):

| Fassung | Score | Flesch |
|---|---|---|
| `48e3534f` (vor der Heilung) | 100 | 68,7 |
| `2d8fc01` (nach der Heilung) | 75 | 44,3 |

**Die eigentliche Lücke lag auf der Schreib-Seite.** Die Verifikation der
KI-Heilung (`_verify` in `scripts/redaktions_standard.py`) prüfte nur die
**Struktur** der Änderung: Linkziele, H2-Anzahl, Mindestlänge, Trennlinien.
Die Regeln, die über die Veröffentlichung entscheiden – Flesch-Schwelle und
harte Textverständnis-Funde – kannte sie nicht. Der folgende Deploy-Lauf
blockierte deshalb korrekt; übrig blieben ein roter Produktionsalarm, ein
abgebrochener Deploy und ein Catch-up-Lauf. Die Lehre aus #585 lautete „Eine
Wache ohne Tor ist ein Protokoll“ – hier gilt die Umkehrung: **Ein Schreiber
ohne Tor ist ein Blocker-Produzent.**

Warum der Lauf die veränderte Fassung überhaupt sah: Der Run wurde 22:02:11
UTC eingereiht, sein Job startete aber erst 22:27:01. In der Zwischenzeit zog
die Content-Kette auf `main` weiter (`802e1ee`, `b1fbf76`, `dbd1b34`,
`b418f3c`, `2d8fc01`). Der Job selbst committete um 22:27:32 UTC seine
Gate-Heilungen (`a91049e`, „fix(gate): Kadenz-/Titel-/Cover-Heilungen vor
Veröffentlichung (automatisch)“) und glich dabei über
`scripts/git_sync.sh --push-only` (Rebase auf `origin/main`) die
zwischenzeitlichen Commits in seinen Arbeitsbaum ab. Der anschließende
Rebuild und die Scorecard (22:27:42) bewerteten damit den frisch geheilt-
verstümmelten Artikel – und blockierten.

## Dauerhafte Reparatur

1. **Neuer Publikations-Vertrag** (`scripts/publikations_vertrag.py`, V1–V3).
   Gemessen wird die *geplante* Änderung – alt gegen neu –, bevor sie
   geschrieben wird:
   - **V1 Lesbarkeit:** Fällt der Flesch unter die Publish-Schwelle *und*
     verschlechtert sich der Text, wird die Änderung verworfen. Die Schwelle
     ist importiert (`readability_check.NEW_FLESCH_MIN`), keine zweite Zahl.
   - **V2 Textverständnis:** Neu eingeführte harte Verständnis-Funde
     (Regelliste importiert aus `publish_gate.HARTE_REGELN` – derselben
     Liste, mit der das Gate blockiert) verwerfen die Änderung. Geprüft wird
     die Differenz: Altlasten werden nicht dem Schreiber angelastet.
   - **V3 Messbarkeit:** Lässt sich V1 oder V2 nicht auswerten, gilt der
     Vertrag als verletzt (**fail-closed**). „Nicht gemessen“ ist niemals
     „freigegeben“. Dafür misst `readability_check.parse_article` jetzt auch
     Texte, die noch in keiner Datei stehen.

2. **Der Schreiber prüft, bevor er schreibt.**
   `redaktions_standard.heal_article_ai` ruft den Vertrag nach der
   Struktur-Prüfung und vor dem Idempotenz-Nachweis auf. Ein Verstoß
   verwirft die KI-Änderung; die Datei bleibt byte-identisch.

3. **Ein Stopp ist sichtbar, kein Betriebsgeräusch.** Verworfene Änderungen
   erscheinen im Report (`REDAKTIONS-STANDARD-REPORT.md`), in der
   versionierten Historie (`data/redaktions_standard_history.jsonl`) und – in
   GitHub Actions – als `::warning::`-Annotation. Die bisherige Stille der
   `|| echo`-Zeilen in `redaktions-standard-neu.yml` kann einen
   Vertragsstopp damit nicht mehr verstecken.

4. **Eine Regelliste, kein zweiter Maßstab.** Die harten
   Textverständnis-Regeln stehen in `publish_gate.py` als Modul-Konstante
   `HARTE_REGELN`; `textverstaendnis_failures` bindet sie, und der
   Regressionstest `test_publish_gate_bindet_die_ssot` verbietet eine
   zweite, abweichende Liste in der Funktion. Die Liste des Guards bleibt
   deckungsgleich (bestehender Gleichheits-Test).

5. **Governance friert den Weg ein** (Regel **C22** „Publikations-Vertrag
   der Schreib-Seite“): Der Vertrag steht in `GUARDS` (Selbsttest läuft in
   C6), der Schreiber muss ihn importieren und aufrufen, Schwellen müssen
   importiert sein, und der reale Vorfall bleibt als Text eingefroren
   (`scripts/tests/sim/wf54c4/vorher.md` und `nachher.md` – kein Nachbau).
   Der Vertrag selbst steht unter dem Integritäts-Siegel
   (`scripts/integrity_guard.py`, FEST).

6. **Regressionstests** (`scripts/tests/test_redaktions_standard.py`, läuft
   in `publication-reliability-tests.yml` über `unittest discover`): Der
   Flesch-Absturz aus #607 und die neu eingeführte Intro-Formel werden
   verworfen, die Datei bleibt unverändert, ein fehlender Vertrag ist
   fail-closed, eine angehobene SSOT-Schwelle greift – und die gute Heilung
   bleibt möglich (kein Totstell-Test).

Bewusst nicht geändert: Die Scorecard hat richtig gehandelt – der Text war
tatsächlich nicht veröffentlichungsfähig. Repariert wurde nicht das
melde­nde Tor, sondern der Schreiber, der die Blockade erzeugt hat.

## Nachweis

- `python3 scripts/publikations_vertrag.py --selftest` → bestanden (V1, V2,
  V3, reale Vorfallprobe).
- Die reale Vorfallprobe liefert beide Gründe wörtlich: „V1 Lesbarkeit:
  Flesch 44.3 liegt unter der Publish-Schwelle 60 und verschlechtert den
  Text (68.7 → 44.3) …“ und „V2 Textverständnis: die Änderung führt den
  harten Fund R7-INTRO-FORMEL ein …“.
- `python3 scripts/redaktions_standard.py --selftest` → 27 eingefrorene
  Fälle bestanden (inkl. neuer Vertrags-Sabotagefälle).
- `python3 scripts/readability_check.py --selftest` → bestanden.
- `python3 scripts/governance_contract.py --selftest` → bestanden (C1–C22
  mit Kunstbefunden); `--quick` und der volle Lauf → „alle 22 Regeln“
  erfüllt.
- `python3 -m unittest discover -s scripts/tests` → grün (siehe
  Lauf-Ausgabe; die neuen Tests sind Teil des Netzes).
- Die eingefrorenen Originaltexte (`scripts/tests/sim/wf54c4/`) sind die
  echten Fassungen aus `48e3534f` und `2d8fc01`, keine Nachbauten.

**Ergebnis:** Die Meldungsklasse von WF-54C4/#607 ist an der Ursache
behoben. Kein KI-Schreibvorgang des Redaktions-Standards kann mehr einen
Artikel erzeugen, den das Publish-Gate blockieren muss – und wenn der
Vertrag selbst nicht prüfbar ist, wird nicht geschrieben.
