# Wartung · Lesbarkeit & Gestaltung · WF-6F7F · #783 – Dauerhafte Heilung

**Datum:** 16.10.2026

**Auslöser:** [Lauf `38893209063`](https://github.com/frank-hartung/franksfinanzcheck-blog/actions/runs/38893209063)
des Workflows „Redaktions-Standard neu (Capital/WiWo/ZEIT)" (Event `workflow_run`,
`main`, 16.10. 13:21 UTC). Der Job **„wache"** schlug im Schritt
**„Selbsttest + Heilung + Gate (neue Artikel)"** fehl –
[Issue #783](https://github.com/frank-hartung/franksfinanzcheck-blog/issues/783).
Dieselbe Ursache meldete später auch das Qualitäts-Gate auf `main`
(`Governance-Selbsttests`): Lauf `38923247993`, [Issue #787](https://github.com/frank-hartung/franksfinanzcheck-blog/issues/787).

**Urteil:** Kein API-Key, kein GitHub-Ausfall, kein transienter Fehler – der im
Alarm hinterlegte Rat („Secrets erneuern", „Lauf neu starten") hätte hier nichts
geändert. Die Redaktions-Wache war **halb**: In `scripts/redaktions_standard.py`
stand der Kopf (inklusive der 14 eingefrorenen Selbsttest-Fälle) aus der neueren
Fassung #766 (Faustregel-POOL + Bestandsmessung), der RS3-Rumpf aus der älteren.
Der Selbsttest schlug deshalb an (Exit 2 = Sabotage-Schutz greift, es wird
nichts geschrieben) – und der Heilpfad der Wache war für jeden echten Lauf ein
`NameError`. Der Befund war **richtig**; falsch war der Zustand der Wache selbst.

## 1. Befund (belegt)

| Beleg | Quelle |
|---|---|
| `--selftest` = Exit 2, **14 Fälle** rot, u. a. `Faustregel-ohne-freien-Satz-schreibt-nichts: Exception name 'faustregel_saetze' is not defined` | Meldungstext in #783 und #787 |
| Qualitäts-Gate rot **ab dem Merge-Augenblick** 15.10. 18:19:02, einziger roter Schritt „Governance-Selbsttests (alle Wachen – entdeckt, uhrfest, schreibfrei)" | Läufe `38784603892` (Job `gate`), `38918175417`, `38858059982` |
| Regression-Job rot: „Code-Regression – Suite und Selbsttests", „Uhr-Probe", „KI-Probe" | Lauf `38784546132` (Job `116593051902`) |
| PR #776 wurde **bei rotem `gate`, rotem `regression` und rotem `Integritäts-Siegel`** zusammengeführt (15.10. 18:18:59) | `gh pr checks 776` |
| Der Vorgang ist **genau** diese Klasse: 33 Namen ohne Definition in derselben Datei – 21 Aufrufe und 12 Konstanten (`FAUSTREGEL_POOL`, `FAUSTREGEL_LEGACY`, `FAUSTREGEL_VORRAT_WARNUNG`, `_bestand_texte()`, `_kontext_aktualisieren()`, `_messung()`, `ersetze_generische_faustregel()`, `faustregel_kontext()`, `faustregel_saetze()`, `faustregel_vorrat()`, `waehle_faustregel()`) | `scripts/wachen_vertrag.py` gegen die `main`-Fassung vor #784: **33 Funde** (W2 21, W3 12) |

**Blastradius:** Vom 15.10. 18:19 bis zur Heilung war jeder Lauf des
Qualitäts-Gates rot, jeder Lauf der Redaktions-Wache rot, und der Heilpfad
(RS1–RS8, Entwurf-statt-Publikation) war nicht benutzbar: Ein echter Lauf wäre
an der ersten halben Zeile gestorben.

**Stand am Ende dieses Vorgangs:** `main` ist geheilt (Fassung aus #784,
Fremdheilung der Affiliate-Wache durch #789, Faktenfrische durch #793), die
Suite läuft vollständig grün, und dieser Zweig schließt die Lücke darüber –
damit die Klasse „halb zusammengesetzt" nicht wiederkommt.

## 2. Ursache

Die Commit-Nachricht des Merge-Commits `1e40a664` (PR #776) nennt die Auflösung
wörtlich:

> „Rebased onto origin/main; **Faustregel-Konflikte zugunsten der
> themenspezifischen Varianten aufgelöst** (gleiches Ziel wie #775, aber
> passende Regel pro Artikel)"

Auf dem Branch lag noch die Fassung **vor** #766. Beim Rebase entstand in der
RS3-Region ein Konflikt, der nicht durch **Wahl einer Fassung**, sondern durch
**Zusammensetzen** gelöst wurde. Übrig blieb eine Datei, die syntaktisch gültig
ist, deren Selbsttest aber auf Namen zeigt, die in ihr nicht mehr existieren –
und deren `main()` dieselben Namen aufruft.

Das war kein Redaktionsfehler: **diese Klasse hatte keine Wache.** Bestehende
Prüfungen setzen voraus, dass eine Datei funktioniert (Selbsttest) oder dass ein
Artefakt lesbar ist. Für `data/`-Artefakte und das Integritäts-Siegel existiert
seit #346/#634 die Regel „niemals beide Seiten zusammensetzen" – technisch
erzwungen durch `.gitattributes merge=binary`. Für den **Quelltext der Wachen**
gab es diese Regel nur als Prosa.

## 3. Was geheilt wurde – und was dauerhaft bleibt

### 3.1 Der Bestand ist geheilt

`scripts/redaktions_standard.py` liegt auf `main` in einer **vollständigen**
Fassung (PR #784, `f7517a5`; 2030 Zeilen, sha256 `ae0d3ecc…`). Nachgelesen und
geprüft:

* die #766-Substanz ist vorhanden und **in Benutzung** – `faustregel_saetze`,
  `faustregel_kontext`, `_bestand_texte`, `_messung`, `_kontext_aktualisieren`,
  `waehle_faustregel`, `_faustregel_kandidaten`, `FAUSTREGEL_POOL`,
  `FAUSTREGEL_LEGACY`, `FAUSTREGEL_VORRAT_WARNUNG`;
* **fail-closed ist erhalten**: `waehle_faustregel()` prüft Belegung, laufenden
  Lauf und die 7-Gramm-Kollisionsschwelle des Audits und gibt ohne freien Satz
  `(None, Grund)` zurück – „der Aufrufer schreibt dann nichts";
* `--selbsttest`: **44/44 grün**, `scripts/tests/test_redaktions_standard.py`:
  **21 Tests grün**.

Dieser Zweig hat die Fassung **nicht** durch eine zweite ersetzt. Im Verlauf der
Arbeit existierten zwischenzeitlich zwei Reparaturen derselben Datei (die reine
#766-Revision mit 1771 Zeilen und die Fassung aus #784). Nach der Lehre dieses
Vorgangs gewinnt **eine** Fassung – die gemergte. Ein „Merge“ zweier Reparaturen
wäre erneut genau die Komposition, die den Vorfall ausgelöst hat.

### 3.2 Dauerhaft: die fehlende Wache (`scripts/wachen_vertrag.py`)

| Klasse | Prüft | Beispiel |
|---|---|---|
| **W1-KONFLIKT-MARKER** | Konfliktmarker **paarweise** (`<<<<<<<` mit `=======` und `>>>>>>>`) | halb aufgelöste Merge-Reste |
| **W2-HALBER-AUFRUF** | Aufgerufener Name ist in derselben Datei **nirgends** gebunden (Definition, Import, Parameter, Zuweisung, `with as`, `except as`, Walrus, `global`/`nonlocal`) | `faustregel_kontext()` in der halben Wache |
| **W3-HALBE-KONSTANTE** | Geladene `GROSSBUCHSTABEN`-Konstante ist nirgends gebunden | `FAUSTREGEL_POOL` |
| **W4-AUSNAHME** | Ausnahmen brauchen Datei, Grund, Datum – und laufen ab | `data/wachen_vertrag_ausnahmen.yaml` |
| **W9-SYNTAX / W9-LESEFEHLER** | Der Prüfling kompiliert bzw. ist lesbar | die zweite Bruchstelle (Abschnitt 3.3) |

Der Prüfling wird **nie ausgeführt und nie importiert** – eine Wache, die ihren
Prüfling startet, ist ein Angriff auf sich selbst. Eigenschaften der Umsetzung:

* **Vorwärts-Beweis statt Beschreibung:** gegen die `main`-Fassung vor #784
  meldet die Wache **33 Funde** und benennt alle 11 Namen;
* **keine Fehlalarme:** auf dem gesamten Bestand (313 Skripte) **0 Funde**;
  Docstrings, Parameter, `with`/`except`-Bindungen und Walrus werden als
  Bindungen erkannt (eigene Testfälle in beide Richtungen);
* **gedeckte Ausnahmen statt stiller Weißliste:** eine Ausnahme verdeckt
  ausschließlich W2/W3 – nie W1, nie W9;
* **kein Selbstausschluss:** die Konfliktmarker-Vorlage der Wache wird
  zusammengesetzt (`"<" * 7`), nicht zitiert;
* **`--selftest` (16 eingefrorene Fälle)**, `--json`, `--md`, Report
  `WACHEN-VERTRAG-REPORT.md`.

### 3.3 Dauerhaft: der Vertrag und die Regel

| Baustein | Änderung |
|---|---|
| `scripts/governance_contract.py` | **C39** „Eine Wache ist ganz oder gar nicht" – Klassen, Selbsttest, GUARDS, Regressionstest, Gate-Verdrahtung **und LIVE**: der Vertrag ruft dieselbe Funktion wie die Wache (`befunde()`), damit keine zweite Messregel entsteht. Vier Sabotage-/Negativproben im Kontrakt-Selbsttest. |
| `GUARDS` (72) | `wachen_vertrag.py` **und `redaktions_standard.py`**. Die Wache, die über Entwurf-statt-Publikation entscheidet, stand bis heute nicht im vertraglichen Minimum – ihr Selbsttest lief nur über die Entdeckung des Runners. |
| `.gitattributes` | `merge=binary` für **alle signierten `scripts/*.py`** (Liste = Signaturliste aus `data/integrity_lock.json`) – dieselbe Regel wie für das Siegel (#346) und die Reserve-Snapshots (#634), mit derselben Begründung im Kommentar: Zusammenschneiden ist **technisch unmöglich**, eine Fassung muss gewählt werden. |
| `scripts/tests/test_wachen_vertrag.py` | 23 Tests: der Vorfall als Miniatur, die Gegenprobe (ganze Wache bleibt still), Marker-Paar-Regel, Namens-Vertrag, Ausnahme-Lebenszyklus, Bestand, Verdrahtung + `Vorfall766BleibtGeheilt` (prüft die #766-API **und** führt den Selbsttest der Redaktions-Wache aus). |
| `scripts/integrity_guard.py` | `wachen_vertrag.py` steht jetzt in **FEST** – also in derselben Quelle, aus der der Lock gebaut wird (nicht nur in der Akte, siehe 3.4). |
| `package.json` | `npm run test:wachen`, `npm run test:redaktion`. |
| `CLAUDE.md` | DAUERVORGABE „Eine Wache ist ganz oder gar nicht": niemals zusammensetzen (auch Quelltext), Beweis vor dem Commit, W1–W4, Ausnahmen mit Grund und Datum, C39. |

### 3.4 Nebenbefunde, die der neue Wächter sofort gefunden hat

Beim Rebase auf `main` meldete `wachen_vertrag.py` **W9-SYNTAX** für
`scripts/affiliate_integrity_gate.py`: die Datei war **nicht kompilierbar**.
Ursache: derselbe Vorgang, eine Ebene tiefer. Der Merge von #784 hat zwei
Reparaturen derselben Stelle zusammengesetzt:

```
    if not gateway_anchors and not (exempt and not exempt_error):   ← #784
    #     braucht entweder einen Beleg-fähigen CTA …                ← #785 (Kommentar)
    if not gateway_anchors and not exempt:                          ← #785
        result["problems"].append("Kein einziger Affiliate-Link …")
```

Der erste `if` hatte damit **keinen Rumpf** (`IndentationError`, Zeile 1014);
an der Notiz-Stelle standen zwei Textfassungen übereinander (Zeile 951). Folge:
Die Affiliate-Wache und ihr Drift-Wächter (`bestand_gate.py`) waren auf `main`
**tot** – der Melder der täglichen Affiliate-Prüfung konnte nicht einmal
importiert werden.

Geheilt wurde die Stelle inzwischen **fremd** (PR #789, `3cb1f52`, Vorgang
WF-53E2/#780 – „Ausnahme-Vertrag mit einem Auswerter"): die Datei kompiliert
wieder, und `affiliate_integrity_gate.py --selftest` sowie
`bestand_gate.py --selftest` sind grün. Dieser Zweig fasst die Datei deshalb
**nicht mehr an**: sie ist byte-gleich mit `main`, und der `--drift-audit`
bestätigt „kein Drift – 49 Kerndateien entsprechen dem signierten Stand". Eine
zwischenzeitliche Reparatur dieses Zweigs (die Fassung von #784, byte-identisch
mit deren PR-Kopf) ist damit gegenstandslos und wurde beim Rebase
zurückgenommen – **eine** Fassung gewinnt, auch hier.

Der Befund bleibt trotzdem wertvoll: er beweist, dass die neue Wache den Fall
**vor** dem Merge sieht. Gegen die `main`-Fassung **vor** #789 meldet sie
`W9-SYNTAX` – nicht nach einem roten Lauf, sondern aus dem Quelltext.

**Zweiter Nebenbefund – ein Werkzeug, das eine Signatur verspricht, die es
nicht hält:** `integrity_guard.py --add <pfad>` meldete für die neue Wache
„🔒 in den Lock aufgenommen (neu signiert, 50 Dateien)". Die nächste Signatur
(`--heal`) nahm den Eintrag wieder **heraus** – 49 Dateien, die neue Wache nicht
mehr unter Siegel, und die Ausgabe nannte die Datei trotzdem in der Liste der
Gezeichneten. Ursache: `signieren()` baut die Datei-Map **aus `KRITISCH|FEST`**;
ein Pfad, der nur per `--add` in die Map kommt, hat keine Quelle und fällt beim
nächsten Zeichnen still weg. Behebung an beiden Enden:

* `scripts/wachen_vertrag.py` steht jetzt in **`FEST`** (mit Begründung im Code)
  – die Wache ist damit dauerhaft unter Siegel, nicht nur bis zur nächsten
  Signatur;
* `--add` ist **fail-closed**: ein Pfad ohne `FEST`/`KRITISCH`-Eintrag wird
  abgelehnt (Exit 2, nichts geschrieben) mit dem Weg dorthin im Klartext.
  Zwei neue Testfälle in `test_wachen_vertrag.py` halten beides fest
  (FEST-Verankerung und das laute Nein).

Der Fund gehört in dieselbe Klasse wie der Vorfall: Ein Prüfwerkzeug, das
„erledigt" meldet, ohne dass es erledigt ist, ist teurer als eines, das Nein
sagt.

### 3.5 Bewusst nicht getan

* **Kein `continue-on-error`, kein Überspringen.** Der rote Selbsttest war richtig.
* **Keine Ausnahme für die eigene Datei** und keine stille Weißliste.
* **Keine Aufweichung des Selbsttests.** Kein Fall entfernt, keine Erwartung gelockert.
* **Kein Handkommentar an #783.** Vorgangsabschluss läuft über die Vorlagen des Repos.
* **Keine zweite Reparatur einer fremden Datei.** Als die Fremdheilung (#789)
  gemergt war, wurde die eigene, gleichgerichtete Reparatur beim Rebase
  zurückgenommen, statt zwei Fassungen nebeneinander zu stellen.
* **Kein zweiter Wächter neben dem ersten.** Es bleibt bei **einer** Messregel je Klasse.

## 4. Verifikation

| Prüfung | Ergebnis |
|---|---|
| `scripts/redaktions_standard.py --selftest` | **44/44 grün** (Fassung aus #784) |
| `python3 -m unittest scripts.tests.test_redaktions_standard` | **21 Tests grün** |
| `scripts/affiliate_integrity_gate.py --selftest` / `bestand_gate.py --selftest` | **grün** (nach der Fremdheilung #789; `main` war zwischenzeitlich nicht einmal importierbar) |
| `python3 scripts/wachen_vertrag.py` | 313 Skripte, **0 Funde** |
| `python3 scripts/wachen_vertrag.py --selftest` | **16/16** eingefrorene Fälle grün |
| Vorwärts-Beweis A: gegen die `main`-Fassung von `redaktions_standard.py` (vor #784) | **33 Funde** (W2 21 / W3 12) über 11 Namen |
| Vorwärts-Beweis B: gegen die `main`-Fassung von `affiliate_integrity_gate.py` (vor #789) | **1 Fund** (W9-SYNTAX: „Datei ist kein gültiges Python") |
| `python3 -m unittest scripts.tests.test_wachen_vertrag` | **25 Tests grün** (inkl. FEST-Verankerung und `--add`-Nein) |
| `test_affiliate_exemption` + `test_wachen_vertrag` | **43 Tests grün** |
| `python3 scripts/governance_contract.py --selftest` | grün, „**C1–C39** mit Kunstbefunden" |
| `python3 scripts/governance_contract.py --quick` | grün, „alle 37 Regeln prüfen in beide Richtungen" |
| `python3 scripts/selftest_runner.py` (voll, mit Uhr-Proben) | **209 Wachen / 418 Uhr-Proben / 203,7 s – alles grün** |
| `python3 scripts/selftest_ki.py --trap-workflows` | **123** Selbsttests ohne Modell und ohne Netz, grün |
| `python3 -m unittest discover -s scripts/tests` | **`Ran 3334 tests … OK (skipped=12)` – Suite vollständig grün** (gegenüber dem Stand vor #793: +22 Tests aus den Fremdheilungen) |
| `python3 scripts/selftest_clock.py --trap-discover scripts/tests --offset 97` | **Exit 0**, dieselben 3334 Tests unter einer um 97 Tage vorgestellten Uhr grün – keine Datumsabhängigkeit |
| `python3 scripts/integrity_guard.py --drift-audit` / `--gate` | **kein Drift**, 50 Kerndateien = signierter Stand – die neue Wache ist über **`FEST`** verankert, nicht per `--add`-Nachtrag |
| `--add` auf einen Pfad ohne `FEST`/`KRITISCH`-Eintrag | **Exit 2**, Weg im Klartext, Lock unverändert |

## 5. Abgrenzung & Koordination

1. **#787** (Gate-Rot auf `main`, Lauf `38923247993`) nennt exakt denselben
   Befund wie #783 – dieselbe Ursache, zweiter Melder. Er schließt sich mit dem
   ersten grünen Gate-Lauf auf `main` von selbst.
2. **PR #788** („Repair affiliate gate merge conflict after #784") zielte auf
   dieselbe Stelle wie Abschnitt 3.4 und ist mit dem Merge von **#789**
   gegenstandslos geworden – die Fremdheilung hat gewonnen. Dieser Zweig fasst
   die Datei nicht mehr an: **eine** Fassung, keine zweite daneben.
3. **PR #789** („fix(affiliate): Ausnahme-Vertrag mit einem Auswerter", WF-53E2/#780)
   hat die zerbrochene Affiliate-Wache geheilt (Abschnitt 3.4) – dieser Zweig
   nimmt dessen Fassung und stellt keine zweite daneben.
4. **`test_faktenfrische_763` war zwischenzeitlich rot – und ist geheilt.**
   Beim ersten Rebase aufgefallen und auf einem reinen `origin/main`
   nachgestellt: der Artikel
   `content/posts/2026-10-14-heizperiode-vorbereiten-im-spaetsommer` schrieb
   „39,42 **Euro**" (`:80`) und führte die Sicherungssätze aus #775 nicht mehr;
   die automatische Redaktionspflege (`15273e0`, `b78bba2`, `2aa5ae5`) hatte
   ihn nach der Heilung umgeschrieben. Die Suite stand auf
   `Ran 3312 tests … FAILED (failures=2)` – **ohne** und **mit** der um 97 Tage
   vorgestellten Uhr identisch, also keine Datumsfrage, sondern Inhalt. Geheilt
   hat das die Fremdheilung **#793** (WF-D4E0, `8afd16e`): Artikel und
   Erwartung stimmen wieder überein, `test_faktenfrische_763` ist **grün**, die
   Suite läuft mit `Ran 3334 tests … OK` durch. **PR #790** („fix(faktenfrische):
   #763 dauerhaft heilen") zielte auf denselben Befund und ist damit wie #788
   ein zweiter Weg zu einer schon geheilten Stelle – eine Fassung genügt; die
   Entscheidung darüber liegt beim Inhaber (Abschnitt 6).
5. **Alarm-Rat:** Der Rat für diesen Vorfall nennt „API-Key erneuern" und „Lauf
   neu starten" (`alert-on-failure.yml`). Bei einer halben Wache hilft beides
   nicht; ein eigener Rat „Selbsttest der Wache rot" gehört zur Klasse der
   Nachführungen aus WF-9E5A (#761).

## 6. Was nur der Inhaber tun kann

1. **Merge-Schutz:** Die drei roten Checks (`gate`, `regression`,
   `Integritäts-Siegel`) haben den Merge von #776 nicht aufgehalten (belegt).
   Benannt als Pflicht-Check ist nur `Integritäts-Siegel`. Runbook:
   `docs/PFLICHT-CHECK-RUNBOOK.md`.
2. **Merge-Reihenfolge:** die Kompositions-Reste auf `main` (Abschnitt 3.4)
   sind durch die Fremdheilung #789 weg – dieser Zweig beschränkt sich darauf,
   sie nicht erneut entstehen zu lassen (W1/W9 + `merge=binary` für die
   signierten Skripte). Läuft zeitgleich ein eigener Reparaturversuch derselben
   Stelle, gilt hinterher **eine** Fassung.
3. **#763** und die verwaisten Reparatur-PRs **#788** (Affiliate) und **#790**
   (Faktenfrische) gehören einem anderen Vorgang: #763 ist durch #793 geheilt,
   die beiden PRs zielen auf bereits geheilte Stellen. Ob sie geschlossen oder
   zusammengeführt werden, ist eine Inhaber-Entscheidung – die vorliegende
   Änderung schließt sie ausdrücklich **nicht**.

## 7. Anleitung (Kurzform)

Wer eine Wache nach einem Konflikt zusammenführt:

```bash
git checkout <rev> -- scripts/<wache>.py     # EINE Fassung, nie Komposition
python3 scripts/<wache>.py --selftest         # Beweis VOR dem Commit
python3 scripts/wachen_vertrag.py             # W1–W4/W9: halbe Wachen, Ausnahmen, Syntax
npm run test:wachen                           # Wache + Regressionstest
```

*Hintergrund: `scripts/wachen_vertrag.py`, `scripts/tests/test_wachen_vertrag.py`,
`CLAUDE.md` („Eine Wache ist ganz oder gar nicht"), `governance_contract.py` (C39).*
