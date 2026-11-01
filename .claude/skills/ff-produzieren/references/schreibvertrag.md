# Schreibvertrag: messen vor dem Schreiben

> Wörtlich aus `CLAUDE.md` übernommen am 01.11.2026 (Skill-Umbau). Kein Satz wurde umformuliert, gekürzt oder erfunden; die Überschriften sind eine Ebene tiefer gehängt. Änderungen hier sind Änderungen am Regelwerk – sie brauchen denselben Nachweis wie vorher: Selbsttest der betroffenen Wache, dann Commit.

### Wer schreibt, misst vor dem Schreiben (DAUERVORGABE, seit #806, 24.10.2026)

Der Governance-Report #806 vom 19.10.2026 nannte zwei Entwürfe unter der
Publish-Schwelle 60 (Flesch **54,2** und **54,9**) – beide aus der Rolle
„Claude“. Die Lehre aus #612 und #712 („Wer schreibt, muss messen, was über
ihn entscheidet“) war nur **einer** Rolle gegeben worden: `news_writer.py`
bekam 2026 die Sicherung `lesbarkeit_sichern()`, die Hauptproduzenten der
langen Premium-Artikel (`claude_writer.py`) und die Werkbank-Recycling-Bahn
(`poppy_repurpose.py`) schrieben ungemessen. Der Ausschuss entstand also im
Generator und wurde Wochen später von drei Wachen eingesammelt – #712 (12.10.)
und #806 (19.10.) sind dieselbe Klasse in zwei Wochen.

- **Jede Schreiberbahn misst VOR dem Schreiben.** Eine Bahn, die den Aufruf
  umgeht, produziert den Befund und wird von C41 als Befund gemeldet.
- **Eine Hausgarantie für alle Bahnen:** `scripts/lesbarkeit_schreiber.py`
  misst über die SSOT (`readability_check.NEW_FLESCH_MIN` – importiert, keine
  zweite Zahl), heilt deterministisch über die Stufe A des **versiegelten**
  `lesbarkeit_heiler.py` (als Bibliothek, nicht als Zweitzritt) und prüft das
  Ergebnis am Tor T1–T4 (`verifiziere`). Reicht die Stufe nicht, meldet der
  Schreiber **ehrlich**: „deterministische Stufe reicht nicht, redaktionelle
  Nachsorge nötig“ – mit dem Aufrufhinweis (`lesbarkeit_heiler.py --entwuerfe`).
  Der CTA-/Disclaimer-Tail bleibt außerhalb von Messung und Heilung.
- **Ein Aufruf, drei Bahnen:** `news_writer.py`, `claude_writer.py` und
  `poppy_repurpose.py` rufen `sichern()` jeweils **vor** `write_post` und
  geben den Status in die eigene Ausgabe (Log/Kurier-Report) durch.
- **Ein neuer Schreiber ruft die Garantie.** Sonst ist der nächste Ausschuss
  schon programmiert – und fällt dann wieder wochenlang durch die Wache, bis
  jemand ihn von Hand heilt.
- **Vertrag statt Vertrauen (C41):** `scripts/governance_contract.py` prüft
  Modul, SSOT-Bindung, echten Tor-Aufruf, die drei Bahnen samt Aufruf vor
  `write_post`, den Regressionstest und den Modul-Selbsttest; fünf
  Sabotage-Proben (a–e) beweisen die Wirkung. Regression:
  `scripts/tests/test_lesbarkeit_schreiber.py` (9 Tests) und
  `scripts/tests/test_news_writer_lesbarkeit.py` (6 Tests) –
  `npm run test:lesbarkeit`.

### Ein doppelter Schlüssel ist eine Bau-Falle (FM-Grenzen, F7/C32, seit #643, 08.10.2026)

Am 08.10.2026 starb der Produktions-Deploy (Run `37755044113`, Push 09:12 UTC)
im Bauschritt an **fünf Reserve-Artikeln**, die aus einem Merge je zwei
`tags:`-Zeilen trugen. go-yaml bricht bei einem wiederholten Mapping-Schlüssel
**hart** ab (`mapping key "tags" already defined at [7:1]`), PyYAML liest
dieselbe Datei still weiter (der letzte Wert gewinnt) – FM-Grenze, Taxonomie
und **alle** Gate-Reporte waren grün, der Deploy starb erst dort, wo niemand
mehr heilen kann. Zwei Dinge waren daran lehrreich:

- **Der Parser-Kurzschluss war die Blindstelle.** Solange „der Block parst“ als
  „sauber“ galt, konnte ein doppelter Schlüssel nie auffallen: PyYAML
  akzeptiert ihn. Die Wache (`scripts/fm_boundary_guard.py`) scannt deshalb
  **zeilenweise** die Mapping-Ebenen (Regel **F7**) – Erkennung **vor** dem
  Parser-Kurzschluss, Sequenzlisten (`quellen: - id: …`) und Block-Skalare sind
  eigene Container bzw. Inhalt und bleiben ruhig.
- **Heilung muss verlustfrei sein und belegt werden.** Listen werden vereinigt
  (kein Element geht verloren), alles andere folgt der YAML-Leseregel: der
  letzte Wert gilt, das frühere Vorkommen fällt weg – **jede** Änderung steht
  im `FM-GRENZEN-REPORT.md`. `--fix` heilt F7 **vor** dem Build (deploy.yml,
  selbstheilend wie F6), `--check` bleibt fail-closed (PR-Kette), `--staged`
  prüft die **Blobs aus dem Index** statt des Arbeitsbaums, `--wirkungsprobe`
  beweist die Klasse am Fixture (Erkennen, verlustfreies Heilen, Fixpunkt).
- **Ein Schreiber darf die Falle nicht unsichtbar machen.** Wer nur das ERSTE
  Vorkommen ersetzt (`count=1`), lässt die zweite Zeile stehen: Sieht geheilt
  aus, stirbt weiter. Die Schlussregel `post_utils.doppel_freies_feld` gilt
  darum für jeden FM-Schreiber (keyword_optimizer, tag_governance,
  pinterest_pin_text_sync) – nach dem Schreiben existiert der Schlüssel genau
  einmal.
- **Vertrag:** Regel **C32** in `governance_contract.py` (Haus-Nummern C24/C31
  gehören anderen Verträgen) friert Wache, Reihenfolge (Heilen VOR dem Build),
  PR-Pfad, Schreiber-Regel und die lebende Wirkung ein – fünf Kunstbefunde
  werden im Kontrakt-Selbsttest rot, der echte Baum bleibt still.

Bedienung: `python3 scripts/fm_boundary_guard.py --selftest` · `--check` ·
`--fix` · `--staged` · `--wirkungsprobe`. Tests:
`python3 -m unittest scripts.tests.test_fm_boundaries`.
Vorgangsbericht: `WF-54C4-643-DAUERHEILUNG-PREMIUM-2026-10-08.md`.

### Politur-Ruinen: Wache R11–R15 (seit 30.09.2026, Issue #482)

Vier echte Textdefekte aus automatisierten Politur-Läufen waren live
gegangen („Du bist der 0 am deutschen Strommarkt“, „es ist der 2 Januar“,
„Nutze 20 26 gezielt Mindestbestellwerte“, „SATZ: | **CHECK24-Vergleich** |
– | | | | |“) — plus das Mietwagen-Doppel-Intro. Keine Wache maß sie,
`sprachkern.write_verified` prüfte nur Struktur (Links, Shortcodes,
Überschriften, Wortzahl), nie den Ergebnis-Text.

- **Eine Muster-SSOT:** `sprachkern.POLITUR_RUINEN` (R11 Jahreszahl-Split,
  R12 Zahl-Ruine, R13 Datum-ohne-Punkt, R14 Marker-Ruine).
  `write_verified` **verweigert jede Schrift, die eine NEUE Ruine
  einführt** (bestehende blockieren die Heilung nicht) — gilt damit für
  Sprachglatt, Grammatik-Check und ZEIT-Rechtschreibung automatisch.
- **Eine Wache:** `textverstaendnis_guard.py` R11–R14 (via SSOT) +
  **R15-PHRASEN-DOPPEL** (identische ≥-10-Wort-Sequenz im Fließtext eines
  Artikels; fingert Doppel-Intros, die duplikat_guard D1/D2 verpassen).
  Tägliches Audit (`blog-health-daily.yml`), Selbsttest mit den
  eingefrorenen echten Schadensfällen.
- **Publish-Gate blockt die Maschinen-Ruinen-Familie komplett:**
  R8-NESTED-LINK, R9, R10 und R11–R15 sind hart in
  `publish_gate.textverstaendnis_failures()` — genau diese Klasse ist
  früher live gegangen.
- R15 läuft bewusst **nur auf Artikel-Fließtext** (nicht auf Rechtsseiten:
  Impressum-Adressen wiederholen sich legitim) und nicht auf
  Überschriften/Listen/Tabellen/CTA-Boxen.
- **R16-PROMPT-ECHO / R16-PROMPT-ECHO-META** (seit 02.10.2026, Issue #521):
  Prompt-Marker (`TITLE:`, `DESCRIPTION:`, `KEYWORDS:` …) im Fließtext bzw.
  im Frontmatter. Realfall: `parse_article` erkannte den Prompt-Kopf nur
  positionsgebunden; eine Leerzeile zwischen den Markern genügte, und
  „TITLE: …“ stand in `description`, `pin_description` **und** im Artikel.
  R16-META ist die **erste Regel dieses Guards, die ins Frontmatter sieht** –
  `split_body()` schneidet es sonst ab, und genau dort geht der Text als
  Google-Snippet und Pin nach außen.
- **Die beiden harten Regelsätze müssen deckungsgleich bleiben**
  (`textverstaendnis_guard.hard_rules` ↔ `publish_gate.textverstaendnis_failures`).
  Am 02.10.2026 behauptete der Report-Kopf „harte Regeln R11–R15“, während
  die Liste des Guards sie gar nicht enthielt – eine Wache, die eine
  Blockade nur versprach. `test_prompt_echo.py` vergleicht beide Sätze jetzt
  dauerhaft.
- Runbook + Zahlen: `LESBARKEIT-ENTWUERFE-PREMIUM-2026-09-30.md`,
  `CONTENT-ENGINE-KAPAZITAET-PREMIUM-2026-10-02.md`.
