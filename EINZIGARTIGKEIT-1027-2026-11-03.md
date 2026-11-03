# Einzigartigkeit #1027: Bestandsüberlappungen – Ursache, Behebung, Dauerhebel

Stand 3. November 2026. Der Vorgang aus dem Tagesaudit
(„Einzigartigkeits-Audit: Bestandsüberlappungen gefunden", #1027, eröffnet am
2. November 2026) ist behoben: **der Bestand ist sauber, und die Ursache, die
ihn erzeugt hat, ist abgestellt.**

Es ging ausdrücklich nicht darum, den Audit zu beruhigen. Ein grüner Audit auf
unverändertem Text wäre Kosmetik gewesen: Am 3. November hätte derselbe Fehler
beim nächsten Deploy wiederkehren können. Dieser Bericht legt deshalb offen,
**wie** die Dublette entstanden ist, **was** am Bestand geändert wurde und
**woher** künftige Doppelten kommen, bevor sie live gehen.

---

## 1. Der Befund

Das Audit misst geteilte Sieben-Wort-Phrasen zwischen je zwei Artikeln; ab
fünf Phrasen gilt ein Paar als kritische Dopplung (`check_uniqueness.KRITISCH_AB
= 5`, Toleranz für Standardformulierungen: eine Phrase). Live-Artikel, die
noch nicht ausgeliefert werden (Entwurf, Zukunfts-Post, abgelaufen), werden
getrennt geführt.

Stand des Ausgangsbefunds (Reproduktion auf `HEAD` `b29c009`, 3.11.2026):

```text
Ergebnis: Pin-Konflikte: 0 | Interne Überlappungen: 31 | Kritisch (live↔live): 2
          | Nicht-Live-Paare: 4 | Same-Day-Twins: 0 (geheilt: 0)
⚠️ KRITISCHE DUPLIKATE GEFUNDEN – Bitte Artikel überarbeiten, bevor veröffentlicht wird.
```

Die sechs betroffenen Paare (Kurzform der Slugs):

| Paar | Status vorher | Geteilte 7-Wort-Phrasen |
|---|---|---:|
| `2026-08-10-sicher-heizen-…` ↔ `2026-08-12-preisgarantie-gas-…` | live ↔ live | **5** |
| `2026-08-10-sicher-heizen-…` ↔ `2026-08-24-preisgarantie-gas-…` | live ↔ live | **16** |
| `2026-08-26-dns-server-wechseln-…` ↔ `2026-10-16-dns-server-aendern-…` | live ↔ Entwurf | **5** |
| `2026-10-12-haushaltskosten-reduzieren-…` ↔ `2026-10-28-dsl-und-internet-flat-…` | live ↔ Entwurf | **5** |
| `2026-10-19-urlaubskasse-clever-aufbessern` ↔ `2026-11-02-last-minute-urlaubsangebote-…` | Entwurf ↔ Entwurf | **7** |
| `2026-10-23-stromanbieter-wechseln-…` ↔ `2026-10-26-gastarife-vergleichen-…` | Entwurf ↔ Entwurf | **34** |

---

## 2. Ursache – drei Ebenen, nicht eine

### 2.1 Inhalt: derselbe Absatz in drei Artikeln

Der Commit `69f08c40` (#1017, 2. November 2026) hat in die drei live
Gas-Artikeln vom 10., 12. und 24. August denselben BNetzA-Absatz zur
Preisänderung und zum Anbieterwechsel eingefügt – wörtlich gleich. Daraus
wurden die 5 und die 16 geteilten Phrasen. Die Sätze waren sachlich richtig;
falsch war, dass drei Ratgeber denselben Absatz in derselben Formulierung
tragen. Ein Leser, der zwei davon öffnet, hält den zweiten für eine Kopie.

### 2.2 Messlücke: das Publish-Gate sieht nur Kandidaten

Das Publish-Gate (U1/U2) misst **Kandidaten** – Texte, die ein Lauf *gerade*
live schalten würde. Eine redaktionelle Änderung an einem **bereits
ausgelieferten** Artikel ist kein Kandidat. Sie lief deshalb an jeder
Einzigartigkeitsmessung vorbei, obwohl dieselbe Änderung am 2. November
zwei Tage vor dem Deploy live ging. Das Audit schlug am 3. November Alarm; die
Meldung kam einen Tag nach dem Deploy, weil der Deploy der schnellere Weg
war. Das ist die eigentliche Lücke: **Es gab eine Messung, aber nicht dort,
wo der Fehler entstand.**

### 2.3 Vertragslücke: der Publikations-Vertrag kannte keine Einzigartigkeit

Der Publikations-Vertrag (`scripts/publikations_vertrag.py`) prüft vor dem
Schreiben einer Änderung die Lesbarkeit (V1), das Textverständnis (V2) und
die Messbarkeit (V3). Eine Regel zur Einzigartigkeit fehlte – die einzige
Eigenschaft, die das Publish-Gate an Kandidaten prüft, war an einer
*geplanten* Änderung nicht prüfbar. Ein Schreiber konnte denselben Absatz in
den zweiten Artikel übernehmen, ohne dass irgendetwas ihn stoppte.

---

## 3. Behebung im Bestand

Die betroffenen Passagen wurden eigenständig formuliert – nicht gekürzt und
nicht mit Floskeln geflickt. Fakten, Quellen, Zahlen und Fristen blieben
unverändert; die Artikel bleiben Aussagen über dasselbe Thema, sie sagen es
aber mit eigener Stimme. Betroffen waren vier live geschaltete und vier
Entwurfs-Artikel:

| Artikel | Art | Eingriff |
|---|---|---|
| `2026-08-10-sicher-heizen-…` | live | Preisänderungs- und Ersatzversorgungsabsätze neu formuliert (Ausnahmen zur separierten Klausel und zur Umsatzsteuer jetzt eigener Wortlaut) |
| `2026-08-12-preisgarantie-gas-…` | live | derselbe Absatzpaar eigenständig; zusätzlich 18 weitere Formulierungen entzerrt (z. B. „Bestandteile“ → „Teile“, „Unterlagen“ → „Papiere“) |
| `2026-08-24-preisgarantie-gas-…` | live | derselbe Absatzpaar eigenständig; Sätze zum Wechselprozess neu gegliedert |
| `2026-08-14-gasrechnung-senken-…` | live | Pin-Text an die Plan-Quelle angeglichen (siehe Abschnitt 6) |
| `2026-10-16-dns-server-aendern-…` | Entwurf | DNS-Adressen in der Anbietertabelle als „(primär), (sekundär)“ gekennzeichnet – die Ziffernfolgen waren der eigentliche Dublettenträger |
| `2026-10-26-gastarife-vergleichen-…` | Entwurf | sieben Passagen eigenständig (Prüfvermerk, Preisänderung, Modellrechnung, Grundpreis, Angebotssicherung, Checkliste, Bonusabsatz) |
| `2026-10-28-dsl-und-internet-flat-…` | Entwurf | Frist-Erinnerung eigenständig formuliert |
| `2026-11-02-last-minute-urlaubsangebote-…` | Entwurf | Abschnittstitel und Tabellenkopf der Fehlertabelle eigenständig |

**Ergebnis der Nachmessung (3. November 2026, alle sechs Befundpaare):**

| Paar | vorher | nachher |
|---|---:|---:|
| `08-10` ↔ `08-12` (live ↔ live) | 5 | **0** |
| `08-10` ↔ `08-24` (live ↔ live) | 16 | **0** |
| `08-12` ↔ `08-24` (live ↔ live) | 1 | **0** |
| `08-26` ↔ `10-16` (live ↔ Entwurf) | 5 | **0** |
| `10-12` ↔ `10-28` (live ↔ Entwurf) | 5 | **0** |
| `10-19` ↔ `11-02` (Entwurf ↔ Entwurf) | 7 | **0** |
| `10-23` ↔ `10-26` (Entwurf ↔ Entwurf) | 34 | **1** |

Die verbleibende Phrase („hast du dann ein sonderrecht zur kuendigung“) ist
eine Frageformulierung und liegt mit einer Phrase unter der Schwelle – sie
wird von der Messung als „Standard-Formulierung“ toleriert und nicht als
Dublette geführt.

**Audit nach der Behebung:**

```text
Ergebnis: Pin-Konflikte: 0 | Interne Überlappungen: 23 | Kritisch (live↔live): 0
          | Nicht-Live-Paare: 0 | Same-Day-Twins: 0 (geheilt: 0)
✅ Audit bestanden – alle Artikel sind einzigartig.
```

---

## 4. Behebung an der Quelle: V4 im Publikations-Vertrag

Der Bestand ist jetzt sauber. Damit das so bleibt, misst der
Publikations-Vertrag seit heute **jede geplante Änderung** auf ihre
Einzigartigkeit – vor dem Schreiben, unabhängig davon, ob der Artikel live ist
oder nicht.

**V4 Einzigartigkeit** (`scripts/publikations_vertrag.py`, Fall V4):

| Aspekt | Entscheidung | Begründung |
|---|---|---|
| Messung | `check_uniqueness.aenderung_befunde` – dieselbe Funktion, dieselbe Größe (`clean_body` + 7-Gramme + `KRITISCH_AB`) wie das Tagesaudit | Zwei Messregeln wären zwei Wahrheiten. Der Vertrag darf nicht großzügiger messen als das Audit, das er ablösen soll. |
| Gegenseite | **jeder** andere Artikel im Bestand, live **und** Entwurf | Ein Entwurf kann morgen live gehen. Eine Dublette, die erst im Publish-Gate auffällt, ist eine Dublette zu spät. |
| Schwelle | importiert (`check_uniqueness.KRITISCH_AB`), nicht kopiert | Vertrag und Audit müssen dieselbe Grenze kennen. Eine eigene Zahl im Vertrag wäre die zweite Wahrheit (Lehre aus #585). |
| Altlasten | **nicht** dem Schreiber angelastet | Ein Befund entsteht nur, wenn die geplante Fassung eine Überlappung *erzeugt* (bisher unter der Schwelle) oder eine bestehende *verstärkt*. Wer eine Dublette abbaut, wird nicht bestraft. |
| Rechtsprosa | keine Ausnahmeliste | Die Formulierung muss sich unterscheiden, nicht die Messung. Eine Sonderregel für Behörden-Sprache würde genau die Textstellen ausnehmen, die das Problem verursacht haben. |
| Messfehler | fail-closed | „Nicht gemessen“ ist nie „freigegeben“ (V3 gilt auch für V4). |

**Was V4 nicht ist:** kein Auto-Heiler. Eine fremde Rechtspassage umzuschreiben
ist eine redaktionelle Aufgabe; die Maschine meldet, der Mensch schreibt. Die
Ausnahme für `uniqueness_failures` im Reserve-Heiler bleibt deshalb bewusst
bestehen – eine Dublette wird nicht stillschweigend umgebaut.

**Wirksamkeitsnachweis:** Die neue Funktion hat fünf Sabotage-Proben in sich
(`check_uniqueness._aenderung_selftest`), der Vertrag hat drei eigene
(`publikations_vertrag.selftest`), und die Governance pinnt beides fest
(C22). Wer V4 abschaltet, bekommt Bescheid – im Selbsttest, im Vertrag und in
der Governance-Prüfung.

---

## 5. Dauerhebel (Tests, Vertrag, Governance)

| Hebel | Ort | Was er verhindert |
|---|---|---|
| Bestands-Regression | `scripts/tests/test_einzigartigkeit_1027.py` | Dass eines der sechs Befundpaare wieder kritisch wird (Prüfung je Paar plus Gesamtsweep über alle 74 live ausgelieferten Artikel) |
| V4-Messung | `scripts/check_uniqueness.py` (`_aenderung_selftest`) | Eine V4-Messung, die Fremdpassage übersieht, eigene Texte trifft, Altlasten bestraft oder Entwürfe außer Acht lässt |
| Vertragsfall | `scripts/publikations_vertrag.py` (`selftest`) | Ein Vertrag ohne V4-Fall, mit eigener Schwelle oder ohne fail-closed-Verhalten |
| Governance-Pinn | `scripts/governance_contract.py` (C22 + Sabotage-Proben f–h) | Dass jemand V4, die geteilte Messung oder die SSOT-Schwelle stillschweigend entfernt |
| Selbsttest-Kette | `scripts/selftest_runner.py`, `scripts/selftest_clock.py` | Dass die neue Prüfung an einem anderen Kalendertag oder in der CI-Uhrprobe anders urteilt (nachgewiesen: identisches Ergebnis bei +97 Tagen) |

**Neue Testdatei:** `scripts/tests/test_einzigartigkeit_1027.py` (19 Tests)
deckt Bestand, V4-Messung, Vertragsfall und Governance-Pinn ab.

---

## 6. Nebenbefund: Pin-Texte („beste Zeit“)

Beim Nachmessen fiel auf, dass zwei Pin-Texte („Der Spätsommer ist die beste
Zeit …“) dem Regressionsvertrag `test_faktenfrische_996` widersprachen. Der
Text stand in `data/pinterest_plan.yaml` (der Quelle) und in den Artikeln
`08-14` und `08-24` (der Spiegelung). Beide Seiten wurden auf eine
aussagenstärkere, prüfbare Formulierung umgestellt und über
`scripts/pinterest_pin_text_sync.py` synchron gehalten. Der Vorgang ist kein
Teil der Uniqueness-Messung, gehört aber zum selben Lauf: Eine Quelle, die
an zwei Stellen auseinanderläuft, ist der Nährboden der nächsten Dublette.

---

## 7. Was bewusst *nicht* getan wurde

- **Kein Abschalten oder Aufweichen der Messung.** Schwelle, Phrasenlänge und
  Toleranz sind unverändert; es gibt keine Positivliste, keine Ausnahme für
  Behördensprache und keinen Sonderweg für Entwürfe.
- **Kein stilles Umschreiben fremder Passagen durch eine Maschine.** Der
  Vertrag meldet und blockiert die geplante Änderung; geschrieben wird von
  Hand.
- **Keine Freigabe-Fälschung.** Die redaktionelle Prüfung der vier
  Entwurfs-Artikel bleibt `status: ausstehend`; `aenderungsgrund` und
  `lastmod` wurden ehrlich fortgeschrieben, der Prüfstatus nicht angetastet.
- **Kein manuelles Schließen des Vorgangs.** #1027 wird vom Produktionslauf
  (`scripts/uniqueness_issue_sync.py`) nach einem sauberen Lauf geschlossen –
  nicht von Hand, damit der Beleg stimmt.
- **Keine zweite Schwelle im Vertrag.** Der Vertrag misst mit derselben
  Konstante wie das Audit; das ist in C22 ausdrücklich gepinnt.

---

## 8. Messwerte im Überblick

| Kennzahl | vorher (03.11., `HEAD`) | nachher (03.11., Arbeitsstand) |
|---|---:|---:|
| Kritische Paare live ↔ live | 2 | **0** |
| Kritische Paare mit Entwurf | 4 | **0** |
| Interne Überlappungen gesamt | 31 | 23 (alle unter der Schwelle) |
| Pin-Konflikte | 0 | 0 |
| Same-Day-Zwillinge | 0 | 0 |
| Live-Artikel unter Flesch 60 | 2 (08-12: 57,8 / 08-24: 56,9) | **0** (08-12: 60,4 / 08-24: 60,3) |
| Ø Flesch im Live-Bestand | 65,4 | 65,5 |

Die beiden Live-Artikel unter der Lesbarkeitsschwelle sind dieselben, die die
Dopplung trugen: Wer die Dublette auflöst, muss den Text zwangsläufig
umformulieren – und eine Umformulierung kann die Lesbarkeit verschlechtern.
Deshalb wurden die betroffenen Absätze beim Umschreiben auf Flesch ≥ 60
gebracht (Publish-Schwelle `readability_check.NEW_FLESCH_MIN = 60`), ohne
Fakten oder Quellen zu verlieren. Der Live-Bestand liegt damit zum ersten Mal
ohne einen Artikel unter der Schwelle.

---

## 9. Bekannte Vorschäden (nicht von dieser Änderung verursacht)

Die volle Testsuite (`python3 -m unittest discover -s scripts/tests`) meldet
im Arbeitsstand **7 Fehlschläge und 4 Fehler**. Alle elf sind auf `HEAD`
`b29c009` genauso vorhanden – im getrennten Worktree gegen den unveränderten
Stand nachgemessen, identische Fehlerliste:

| Fehler | Ursache |
|---|---|
| `test_integrity_guard.RepoSealTests` (5) | `data/integrity_lock.json` ist in `HEAD` **kein gültiges JSON** (`Expecting ',' delimiter: line 289`) – das Siegel ist zerstört, fünf kritische Knoten sind „neu ohne Signatur“ |
| `test_fremdmessung_sperre`, `test_skills_vertrag` (3) | folgen derselben unlesbaren Siegelquelle |
| `test_lcp_image_optimizer` (1) | eingechecktes Manifest deckt sich nicht mit der Quelle (unabhängig von #1027) |
| `test_versicherungs_cluster_verlinkung` (1) | ein Pillar verlinkt einen Entwurf (unabhängig von #1027) |
| `test_wachen_vertrag` (1) | `redaktions_standard.py` meldet eine fehlende PyYAML-Umgebung mit einem `TypeError` statt mit Exit 2 (Vorsprung aus #1001) |

**Folge:** Der Integritäts-CI-Job bleibt rot, bis das Siegel bewusst neu
gesetzt wird. Das wurde hier **nicht** angefasst: `integrity_guard.py
--repair-lock`, `--set-current` oder `--heal` verändern Nachweise und
Historie und brauchen eine ausdrückliche Freigabe. Der Vorgang gehört in eine
eigene Meldung, nicht in die Uniqueness-Heilung.

---

## 10. Reproduktion

```bash
python3 -m venv .venv
.venv/bin/pip install --require-hashes -r requirements-ci.txt
.venv/bin/pip install --require-hashes -r requirements-hugo.txt

.venv/bin/python scripts/check_uniqueness.py            # Bestand: muss „Audit bestanden“ sagen
.venv/bin/python scripts/publikations_vertrag.py --selftest   # V1–V4 inkl. V4-Proben
.venv/bin/python scripts/check_uniqueness.py --selftest        # V4-Sabotage-Proben
.venv/bin/python scripts/governance_contract.py --selftest    # C22 mit V4-Pinn
.venv/bin/python -m unittest discover -s scripts/tests        # 5064 Tests (11 Vorschäden, s. o.)
.venv/bin/hugo --minify --destination public --cleanDestinationDir
```

Der Vorgang #1027 wird nach dem nächsten sauberen Produktionslauf vom
Produktionsautomaten geschlossen und kommentiert.
