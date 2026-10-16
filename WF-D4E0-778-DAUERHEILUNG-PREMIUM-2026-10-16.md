# WF-D4E0: Publication-Reliability-CI – Dauerheilung PREMIUM (#778)

> **Vorgang:** `WF-D4E0` · **Run:** https://github.com/frank-hartung/franksfinanzcheck-blog/actions/runs/38873132768
> **Symptom:** Step 8/„Tests & Qualitätssicherung" der `Publication Reliability CI`
> → `FAILURE` („This step has exceeded the maximum execution time." – Folge der
> endlos laufenden Selbstdiagnosen, nicht deren Ursache)
> **Entscheidungslevel:** LESE-LEVEL · **Bericht:** 16.10.2026 · **Zweig:** `arena/6ce28a56-franksfinanzcheck-blog`

---

## 1. Symptom, wie gemeldet

* **Alert-Key `WF-D4E0`** (`auto-report`), Runbook `allgemein`, Issue **#778**, Status OPEN.
* Die Wache **Tests & Qualitätssicherung** läuft in die maximale Ausführungszeit, weil drei
  Selbstdiagnosen dauerhaft rot sind und je eine Diagnoseschleife starten
  (`redaktions_standard.py --selftest`, `affiliate_integrity_gate.py --selftest`,
  `bestand_gate.py --selftest`). Die übrigen Wachen derselben CI sind grün.
* Reproduziert auf dem Arbeitszweig (`selftest_runner.py`): **208 Wachen, 3 Ausnahmen**
  – exakt die drei im Step 8 sichtbaren.

## 2. Forensik (Untersuchung, Historie, Urteil)

### 2.1 Ursache A – die #766-Schicht des Redaktions-Standard-Schreibers war verloren

`scripts/redaktions_standard.py` enthielt zum Zeitpunkt des Laufs wieder den **#764-Stand**
(„Faustregel setzen"), obwohl #766 (15.10.2026) die Schicht „Faustregel **wählen**" gebaut hatte:

| Baustein #766 (Soll) | Fund am 16.10. (Ist) |
|---|---|
| `ersetzte_generische_faustregel` (einmalige Alt-Satz-Ersetzung) | **fehlte komplett** |
| `fix_rs2_rs3_deterministic(..., kontext, titel, nur_rs3)` | alte Signatur `(body, slug, kontext)` ohne `nur_rs3` |
| `FAUSTREGEL_POOL` (45 thematische Sätze) + `waehle_faustregel`/`faustregel_kontext`/`faustregel_vorrat` | `_THEMEN_FAUSTREGELN` (15 Sätze, #764: „setzen") |
| Selbsttest 44 Fälle (Pool 6 / Vergabe 14 / Kontext 6 / Einsetzer 8 / RS2 10) | nur 2 Kurzfälle |
| Aufruf in `main()` mit `kontext=`, `nur_rs3=NUR_FAUSTREGEL` | **NameError** `nur_rs3` bei jedem Heilungsversuch |

* **Nachweis der Verdrängung:** In `main()` steht der #766-Aufruf `fix_rs2_rs3_deterministic(..., kontext=..., titel=..., nur_rs3=...)`
  unverändert neben der verlorenen Funktion – d. h. ein **Merge/Wiedereinspielen alter Daten** hat die
  Funktionsschicht ersetzt, nicht die Aufrufschicht. Genau so meldete sich der Lauf: `name 'nur_rs3' is not defined`.
  * Der in `data/redaktions_standard_history.jsonl` vermerkte #766-Heilerlauf (33 Aktionen,
    15.10.2026 15:37 UTC) schrieb **33-mal denselben Satz** („Zinsen sind kein Geschenk …") in
    Artikel, die gar kein Thema Geldanlage haben – das ist der **#764-Massensatz**, nicht die
    #766-Vergabe. Die Datenlage zeigt damit zwei verschiedene „Wiederherstellungen" desselben Tages:
    erst die Wiederherstellung der #766-Schicht (Selbsttest 44/44 um 20:13 UTC protokolliert),
    dann einen Lauf auf dem wiedereingespielten #764-Stand (15:37 UTC).
* Der Commit-Nachweis der Ursprungsarbeit (`971b05b6`, aus #766-Kontext) war aus der Sandbox
  nicht abrufbar (nur `e662cf0` erreichbar); die **Spezifikation lag vollständig im Bericht
  `FAKTENFRISCHE-763-DAUERHEILUNG-2026-10-15.md`** (Abschnitt „Rekonstruktion der verlorenen
  Pool-Implementierung") und im Selbsttest-Vertrag. Rekonstruktion daraus: **beweissicher**.
* **Urteil A:** Verlust der #766-Implementierung durch überschreibendes Wiedereinspielen eines
  älteren Stands. Kein Entwurfsfehler, kein Laufzeitfehler – **unbemerkter Schichtverlust ohne
  Prüfe** (ein Vertrag, den niemand testete: „der Code muss die im Bericht dokumentierte
  Spezifikation noch erfüllen“).

### 2.2 Ursache B – Doppelter Ausnahmepfad im Render-Beweis des Affiliate-Gates

* Der #762-Vertrag hält die redaktionelle Ausnahme („*kein passendes Tarifangebot*“) im
  Frontmatter und verlangt, dass sie den **Mindestbestand** hebt **und** im Gate-Report als
  sichtbarer Hinweis steht (getestet: `test_affiliate_exemption.py`, Selbsttest 8b).
* Eingebaut wurde das als **ein** Pfad über `scripts/affiliate_exemption.py` (geteilter Vertrag,
  #714). Zusätzlich lag – aus der #764-Runde – ein **zweiter, dateibezirkelter** Ausnahmeweg in
  `verify_article_render`: er las die Ausnahme **ein zweites Mal von der Platte** (`article['path']`),
  setzte `exempt` auf das Ergebnis *dieses* Lesevorgangs und überschrieb damit still das
  Vertragsergebnis, sobald `article['path']` nicht im erwarteten Verhältnis stand. Genau das
  passierte in der Wache (8b → „🛑 Kein einziger Affiliate-Link, obwohl Artikel live“).
* Zusätzlich: Der Ausnahmehinweis „*(redaktionell ausgenommen: …)*“ war **nur im Report-Text**
  implementiert, nicht in `verify_article_render` – Selbsttest 8c („Hinweis vorhanden“) schlug fehl.
* **Urteil B:** Zwei Ablesewegen, zwei Wahrheiten (#714/#766-Muster) – plus ein fehlender
  Sichtbarkeitspfad. Fail-open war es nicht (der Fehler ging nach ROT), aber falsch-ROT für
  korrekt ausgenommene Artikel.

### 2.3 Ursache C – Inhaltsfolgen des Verlusts (Sichtfläche der Wache)

* **33-mal derselbe Faustregel-Satz** (15.10.2026), davon zwei **thematikfremd** im Bestand
  (u. a. ein Geldanlage-Satz in „Störung beim Internetanbieter“) – die Checks bemerken
  Einzigartigkeit erst in der Paar-Analyse, und der Satz stand mehrfach im Bestand.
* **12 Artikel ohne RS3-Faustregel** (harte Regel) – der Massensatz-Verlust hatte die
  #766-Vergabe ja gar nicht erst ausgeführt.
* **Vertragsdrift der #763-Entwürfe:** `test_faktenfrische_763` (15.10. eingefroren) fordert im
  Heizperiode-Entwurf exakte Einheiten (`39,42 €`, `13,14 €`, `105 €`, `120 €`, „bei gleichem
  Grundpreis“) und vier Safeguards. Der Text zeigte noch „Euro“-Schreibungen und „wenn der
  Grundpreis gleich bleibt“. (Der Reisekassen-Teil war intakt.)
* **Urteil C:** Wiederkehrende Inhaltsqualität als zweite Sichtfläche desselben Verlusts –
  Inhaltsschäden, keine weiteren Codefehler.

## 3. Maßnahmen (Dauerheilung, nicht Workaround)

### 3.1 Code – `scripts/redaktions_standard.py` (Ursache A)

* **#766-Schicht wiederhergestellt.** Zwei Linien trafen zusammen und wurden im Merge vereint
  (Konfliktlösung 16.10.2026): die #778-Rekonstruktion aus der Berichtsspezifikation und die
  auf `main` parallel entstandene Wiederherstellung (#777/#784, `f7517a5`). Übernommen wurde
  die `main`-Fassung – ihr Wähler misst Kandidaten direkt gegen die Audit-Schwelle
  (`check_uniqueness.KRITISCH_AB`, geteilte 7-Gramme) und ihr Testsuite ist umfangreicher;
  die #778-Arbeit ergänzt den eingefrorenen Aufrufvertrag-Test und die Inhaltssichtfläche:
  * `FAUSTREGEL_POOL` – eigenständige, themenbezogene, zahlenfreie Faustregeln; der Wähler
    (`waehle_faustregel`) vergibt nur Sätze, die **weder im Bestand stehen noch ein
    Artikelpaar über die Audit-Schwelle schieben** – die Wiederholungssperre ist damit sowohl
    Code als auch Datenlage (die 33 Sätze des 15.10.-Massensatzlaufs stehen im Bestand und
    werden nie wieder vergeben).
  * `faustregel_kontext`/`faustregel_vorrat`: Verwaltung der Belegung im laufenden Lauf
    (kein Satz zweimal), `ersetzte_generische_faustregel` ersetzt den eingefrorenen
    #764-Alt-Satz einmalig und meldet Stillstand statt Massensatz bei leerem Pool.
  * `fix_rs2_rs3_deterministic` mit **`nur_rs3`** (Faustregel-Modus berührt RS2 nie), Aufruf-
    vertrag `main()` ↔ Funktion wieder stimmig; Fail-closed-Meldung bei leerem Pool.
  * **Selbsttest 44/44** (Pool · Vergabe · Kontext · Einsetzer · RS2) einschließlich der
    #766-Kernfälle (freie Wahlen ohne Wiederholung; Massensatz-Sperre; Vergabeschutz;
    Pool selbst audit-sauber; `--selftest` überschreibt keinen Bestand).
* **Neuer Regressionstest** `HeilerAufrufVertragTest` in `test_redaktions_standard.py`:
  friert den Aufrufvertrag `fix_rs2_rs3_deterministic(..., kontext, titel, nur_rs3=True)` ein
  (RS3 wird geheilt, RS2 bleibt liegen, Vergabeschutz zählt) – genau die Fehlerklasse des
  `nur_rs3`-NameErrors.

### 3.2 Code – `scripts/affiliate_integrity_gate.py` (Ursache B)

* `verify_article_render`: **einstelliger Pfad** – die Ausnahme kommt ausschließlich aus dem
  geteilten Vertrag `affiliate_exemption.exemption_for_article` (Frontmatter aus dem
  In-Memory-Artikel); der dateibezirkelter Zweitausnahmeweg ist **entfernt**.
* Mindestbestand gilt weiter **uneingeschränkt ohne gültige Ausnahme**; „nichtleere Begründung“,
  „gilt nicht für rohe Partnerlinks“ usw. bleiben harte Fünde (Selbsttest 8a/8e–8g).
* Der Sichtbarkeitshinweis „*(redaktionell ausgenommen: …)*“ ist wieder **im Resultat**
  (`notes`), nicht nur im Reporttext (Selbsttest 8c grün).
* **Neue Regressionstests** `RenderProofSinglePathTests` in `test_affiliate_exemption.py`:
  gültige In-Memory-Ausnahme ohne lesbare Datei bleibt gültig (#778-Fehlerklasse),
  Hinweis mit Begründung ist sichtbar, ohne Ausnahme bleibt der Mindestbestand-Alarm.
* Danach: `affiliate_integrity_gate.py --selftest` und `bestand_gate.py --selftest` wieder grün
  (Bestand-Gate-Folge ohne eigenen Eingriff).

### 3.3 Inhalt (Ursache C)

* **Entwurfsvertrag #763 wiederhergestellt** (`2026-10-14-heizperiode-vorbereiten-im-spaetsommer`):
  Einheiten „39,42 € / 13,14 € / 105 € / 120 €“, „bei gleichem Grundpreis“, Safeguards
  „keine konkrete Prozentangabe“, „kein allgemeines Optimum“, „Keine Arbeiten an Brenner oder
  Gasleitungen in Eigenregie“ (die übrigen Vertragsteile waren unverändert korrekt).
  `test_faktenfrische_763` wieder **7/7 grün**.
* **Thematisch falsche Faustregel getauscht** (`2026-08-31-stoerung-beim-internetanbieter-…`):
  der Geldanlage-Satz ersetzt durch eine artikelgerechte Regel (Störungsdokumentation:
  Uhrzeit, Ticketnummer, Gesprächspartner).
* **RS3-Heilung einmalig mit dem wiederhergestellten Pool-Heiler** (`--fix --nur-faustregel`,
  mit und ohne `--include-drafts`): geheilt wurden 5 Artikel (2 live: `2026-09-04-digitaler-turbo-…`,
  `2026-09-30-last-minute-urlaub-…`; 3 Entwürfe: `2026-09-23-5-einfache-frugalismus-tricks-…`,
  beide #763-Entwürfe). **YMYL-gesiegelte Artikel blieben unangetastet** (vertragsgemäß,
  redaktionelle Entscheidung); der Entwurf `2026-10-16-dns-server-aendern-…` wurde **fail-closed
  gestoppt** (V1 Lesbarkeit: Flesch 54,6 unter Publish-Schwelle – sichtbar gemeldet, nicht
  erzwungen). Alle Schutzverträge (Links, H2, Zahlen, Flesch) liefen vor jedem Schreiben.
* `check_uniqueness.py` nach allen Änderungen: **0 kritische Paare, Audit bestanden.**

## 4. Beweiskette (Verifikation)

| Prüfung | Ergebnis |
|---|---|
| `redaktions_standard.py --selftest` | ✅ **44/44** |
| `unittest scripts.tests.test_redaktions_standard` | ✅ **22/22** (inkl. neuem Aufrufvertrag-Test) |
| `unittest scripts.tests.test_faktenfrische_763` | ✅ **7/7** |
| `affiliate_integrity_gate.py --selftest` | ✅ (inkl. 8b/8c, verschärft um Begründungsnachweis) |
| `bestand_gate.py --selftest` | ✅ |
| `unittest scripts.tests.test_affiliate_exemption` | ✅ **23/23** (Single-Path-Tests + BestandGate-Dependency) |
| `check_uniqueness.py` | ✅ 0 kritisch (live↔live) |
| `selftest_runner.py` (voll, mit Uhr-Proben) | ✅ **208 Wachen · 416 Uhr-Proben** (war: 3 Ausnahmen) |
| `unittest discover -s scripts/tests` | ✅ **3309 Tests, 0 Fehler** (nach beiden Merges mit `main` + Siegelstand) |
| FEST-Siegel (`integrity_guard.py`) | ✅ `--heal` auf committetem Drift, verkettet, Stufe 4 |

### 4.1 Merge mit `main` (16.10.2026, Konfliktlösung)

`main` hatte während der Arbeit sieben Commits aufgenommen; drei Konflikte betrafen diese
Dauerheilung. Auflösung nach Nutzen und Beweislage:

* `scripts/redaktions_standard.py`: übernommen wurde die **`main`-Fassung** (#777/#784) – die
  parallele Wiederherstellung desselben #766-Vertrags mit Audit-Messung im Wähler und
  größeren Testsuite (52 grüne Tests in der Vereinigung, Selbsttest 44/44).
* `scripts/affiliate_integrity_gate.py`: übernommen wurde die **#778-Fassung** – die
  `main`-Fassung war an dieser Stelle **syntaktisch defekt** (IndentationError,
  doppelte Notiz-Anweisung aus einem Artefakt). Die auf `main` verschärften
  Selbsttest-Erwartungen (Hinweis enthält Begründung; ungültige Ausnahme zeigt keinen
  „ausgenommen“-Hinweis) sind in die #778-Fassung portiert.
* `scripts/tests/test_affiliate_exemption.py`: **Vereinigung** beider Testklassen
  (`RenderProofSinglePathTests` + `BestandGateSelftestDependencyTests`).
* `data/integrity_lock.json`: über `integrity_guard.py --heal` nach dem Merge neu versiegelt.

Ein zweiter Merge desselben Tages brachte zusätzlich den WF-53E2-Fix des Affiliate-Gates
(`3cb1f52`, „ein Auswerter“ – identische Zielrichtung wie die #778-Fassung); übernommen wurde
die `main`-Fassung, die #778-Regressionstests (`RenderProofSinglePathTests`) laufen gegen
beide Fassungen und sperren die Fehlerklasse. Finale Batterie nach beiden Merges:
**3309 Tests, 0 Fehler**.

## 5. Abgrenzung

* **Nicht angefasst:** `bestand_gate.py` (Folgefehler, ohne eigenen Eingriff grün), Affiliate-
  Link-Kontrakte/`links.yaml`, YMYL-gesiegelte Artikel (redaktionelle Hoheit), der
  DNS-Entwurf mit Lesbarkeitsstopp (bewusst offen, siehe 3.3), alle FEST-Dateien außer den
  beiden genannten (Rest-Siegel über `integrity_guard.py --heal`).
* **Ausdrücklich keine Symptomarbeit:** keine Abschwächung von Schwellen, kein Löschen des
  Selbsttests, kein Entfernen der Fünde, kein Ausschalten des Mindestbestands.

## 6. Rückfallplan (Was tun, wenn es erneut aufschlägt?)

1. **`redaktions_standard.py --selftest` rot** → zuerst `--selftest`-Ausgabe lesen (44 Fälle
   sind einzeln benannt). Häufigste Klasse: Pool/Bestandskollision → `faustregel_vorrat`
   prüfen; Signaturen decken `test_redaktions_standard.py` ab (läuft in jeder CI).
2. **8b/8c des Affiliate-Gates rot** → `verify_article_render` hat erneut mehr als einen
   Auslespfad: `grep -n "exempt" scripts/affiliate_integrity_gate.py` muss genau die
   Vertragszeile `exemption_for_article` zeigen; die Regressionstests in
   `test_affiliate_exemption.py` (Klasse `RenderProofSinglePathTests`) benennen die Stelle.
3. **`test_faktenfrische_763` rot** → Entwurfstext weicht vom #763-Vertrag ab (15.10.2026):
   Vertrag siegt, Text wird angeglichen – nie der Test entschärft.
4. **Massensatz im Bestand** → `data/redaktions_standard_history.jsonl` (Zeitpunkt des Laufs)
   + `check_uniqueness.py`; Heiler nur noch mit Kontextaufruf laufen lassen.
5. **FEST-Drift nach Code-Commits** → `python3 scripts/integrity_guard.py --heal` im eigenen
   `chore(integrity)`-Commit; `--set-current` bleibt die menschliche Entscheidung.

## 7. Monitoring

* **Wache:** `publication-reliability.yml` → „Tests & Qualitätssicherung“ (frühestes Signal:
  Selbsttests + `unittest discover`).
* **Frühindikator:** `redaktions_standard_history.jsonl` – mehrere Einträge desselben Tages mit
  identischem Satz = Vergabe läuft nicht.
* **Zweite Sichtfläche:** `check_uniqueness.py` (Paar-Analyse) und `bestand_gate`-Report.

## 8. Nächste Schritte (redaktionell, außerhalb dieses Vorgangs)

* **6 YMYL-gesiegelte Artikel ohne Faustregel** (`2026-08-12-dein-haus-sicher-…`,
  `2026-08-17-privathaftpflicht-…`, `2026-08-18-wohngebaeudeversicherung-…`,
  `2026-09-17-versicherung-update-…`, `2026-09-21-unfallversicherung-…`,
  `2026-09-21-zahnzusatzversicherung-…`): fachliche Freigabe + `--fix --include-drafts`
  (bzw. Redaktions-Lauf) nach Freigabe des Siegels.
* **`2026-10-16-dns-server-aendern-…`:** Lesbarkeit (Flesch 54,6) redaktionell anheben,
  danach heilt der Pool-Heiler die RS3 von selbst.
* **Nachtlauf-Workflows** (`redaktions-standard-bestand.yml`) nutzen den wiederhergestellten
  Pool – künftige RS3-Heilungen laufen automatisch vergabesicher.

---

### Wiederherstellungsanker (Kurzform)

```bash
# 1) Wache im Zweifel zuerst
python3 scripts/selftest_runner.py --ohne-uhr-probe

# 2) Der Vertrag des Schreibers
python3 scripts/redaktions_standard.py --selftest          # 44/44
python3 -m unittest scripts.tests.test_redaktions_standard scripts.tests.test_faktenfrische_763

# 3) Ausnahme einstellig
python3 scripts/affiliate_integrity_gate.py --selftest
python3 -m unittest scripts.tests.test_affiliate_exemption

# 4) Volle Flotte
python3 -m unittest discover -s scripts/tests
```

**Ergebnis:** Der Vorgang `WF-D4E0` (#778) ist behoben – die Wache „Tests & Qualitätssicherung“
läuft wieder durch, weil die #766-Schicht wiederhergestellt, der doppelte Ausnahmepfad entfernt
und beides durch Regressionstests gegen Wiederverdrängung gesperrt ist.
