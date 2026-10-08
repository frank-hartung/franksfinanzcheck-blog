# Content-Reserve WF-D4E0 · #653 – Dauerheilung

**Datum:** 08.10.2026
**Auslöser:** Der Content-Reserve-Lauf **37765762299** (Schedule, Push
`dcc31385`, 08.10.2026 10:47:11Z) wurde im Schritt **„Stock shortage must not
look successful“** rot; das Fehler-Alerting meldete das als Issue **#653**
(`auto-report`, Alert-Key `WF-D4E0`, Bereich *Inhaltsqualität*).

**Es war der sechste rote Lauf in Folge.** Die Läufe 42–47
(`37347512536` … `37765762299`, 05.10. 17:19 Uhr bis 08.10. 10:47 Uhr) endeten
alle im selben Schritt; Lauf 41 (`37298226945`, 05.10. 10:41 Uhr) war der
letzte grüne. Sechs Nächte, dieselbe Meldung:

    🛑 RESERVE-ENGPAß: nur 0/6 Kandidaten gate-fertig.

Und in keiner dieser Nächte war der Vorrat leer.

---

## Befund

### 1. Die Meldung war wahr, die Diagnose erfunden

Der harte End-Gate liest `data/reserve-readiness.json`. Bei `dcc31385` war
diese Datei **kein gültiges JSON mehr**:

    Expecting property name enclosed in double quotes: line 28 column 5

`reserve_gate.evaluate()` fängt Parse-Fehler – zu Recht, denn eine nicht
ausgeführte Messung darf kein Grün sein (C2) – und zählt daraus **0** bereite
Kandidaten. Aus dieser `0` leitete `report()` anschließend eine vollständige
Ursachenliste ab:

    URSACHEN DIESES ENGPASSES:
    • PRODUKTION: 6 Kandidat(en) fehlen im Pool, obwohl freie Themen
      bereitstehen (nächstes: „Die besten Apps für das Sparen von Geld“).
      Ursache liegt bei der KI-Generierung (API-Schlüssel, Profi-Gate) …

Der Pool war voll. Die Ursachenliste war eine Erfindung aus dem Fehlen einer
Messung. Genau sie hat die Reparatur sechs Nächte in die falsche Richtung
geschickt: nach API-Schlüsseln, Themenvorrat und Produktion gesucht – während
die Ursache ein halbes Artefakt war, das niemand las.

**Das ist der eigentliche Schaden:** nicht ein roter Lauf, sondern ein roter
Lauf mit einer falschen Wegbeschreibung.

### 2. Drei Artefakte, eine Ursache, null Wachen

| Artefakt | Zustand bei `dcc31385` |
|---|---|
| `data/reserve-readiness.json` | zwei Zertifikatsstände verschmolzen – **kein gültiges JSON** (line 28) |
| `data/reserve-quarantine.json` | Block in einen nicht geschlossenen Eintrag geklebt – **kein gültiges JSON** (`Expecting ',' delimiter: line 199`) |
| `data/reserve-custody.json` | sechs Einträge mit doppeltem Schlüssel `zuletzt_im_pool` |

Alle drei sind keine Quelltexte, sondern **versionierte Maschinen-Artefakte**
in `data/**` – genau dort, wo Zertifikat, Quarantäne-Gedächtnis und
Bestands-Gedächtnis liegen. `history_guard.py` deckt ausschließlich
`data/*_history.jsonl` ab, `bot_watchdog.py` prüft Python-Syntax. Für die
strukturierte Wahrheit in `data/**/*.json` gab es **keine Wache**.

Ursprung ist dieselbe Klasse wie in #346 („Maschinen-Artefakte niemals
mergen“): Ein Auto-Commit/Merge hat zwei Stände desselben Artefakts
verschmolzen. Die Lehre von #346 galt bislang nur für das Siegel
(`data/integrity_lock.json`, `merge=binary`). Für den Rest des `data/`-Baums
galt sie nicht.

### 3. Die Kette half nicht – sie verhinderte die Heilung

Der Workflow `content-reserve.yml` hat eine Ketten-Lücke, die den Defekt
**dauerhaft** machte:

* **Stufe 1** (Produktion), **Stufe 2** (Veredelung) und **Stufe 3**
  (Zertifizierung) trugen als einzige Schritte des Laufs **kein**
  `if: !cancelled()`. Fiel ein Schritt davor aus – an diesem Tag der
  Wachen-Selbsttest –, wurden genau diese drei übersprungen.
* **Stufe 3 schreibt das Zertifikat.** Ohne sie blieb das kaputte Artefakt
  liegen, und der End-Gate las es erneut. Die Stufe, die den Fund geheilt
  hätte, war die Stufe, die übersprungen wurde.
* Alle folgenden Schritte (Janitor, Konvergenz, Triage, Chronik, End-Gate)
  liefen weiter. Der Lauf arbeitete über 40 Minuten und meldete am Ende einen
  Vorrats-Engpass, den es nicht gab.

### 4. Darunter lag ein zweiter, echter Defekt derselben Klasse

Als das Zertifikat wieder lesbar war (Quarantäne aus Git, Zertifikat neu
erzeugt), zeigte die erste ehrliche Messung **3/6** – nicht 0/6. Drei
`2026-10-07`-Kandidaten waren tatsächlich blockiert:

    Struktur: doppelte H2-Überschrift(en): was zeigt eine modellrechnung,
    welche ausrüstung brauchst du wirklich, welche kosten gehören in ein
    campingbudget

Bisect über die Historie zeigt den Eintritt: Bis einschließlich `24b8cc5a`
waren die drei Entwürfe sauber (9/9/10 H2, **0** doppelte). Ab dem Merge
`11e65ea7` („fix: certify reserve drafts with editorial gate (#634)“) trugen
sie 15/16/11 H2 mit 6/7/1 Duplikaten. `git diff 24b8cc5a HEAD` auf den
Artikelkörpern ist eine **reine Addition, null Löschungen**: derselbe
Merge-Artefakt-Typ, nur im Content statt in `data/`.

Beide Defekte teilen eine Ursache: **Ein Merge ist kein Schreiber.**

---

## Reparatur

### 1. Bestand geheilt

* **Artefakte.** `data/reserve-quarantine.json` aus dem letzten nachweislich
  gültigen Stand (`7d5fcae3`) zurückgeholt, `data/reserve-custody.json` von
  den sechs doppelten Schlüsseln befreit, `data/reserve-readiness.json` vom
  Erzeuger selbst neu schreiben lassen (`reserve_readiness.py`), nicht von
  Hand.
* **Inhalte.** Die drei `2026-10-07`-Entwürfe auf den Artikelkörper von
  `24b8cc5a` zurückgesetzt, das Frontmatter von **heute** behalten und den
  `**Transparenz:**`-Absatz genau einmal wieder eingesetzt. Ergebnis:
  camping 15→9 H2, dsl 16→9, urlaub 11→10 – **je 0 Doppelte**;
  `git diff --stat content/posts/` = **60 Löschungen, 0 Einfügungen**.

  Warum Körper-Rollback statt „zweiten Block löschen“: Sieben Absätze der
  Duplikat-Blöcke (camping 3, dsl 1, urlaub 3) waren **nicht** wortgleich mit
  ihrer ersten Fassung – ein mechanischer Schnitt hätte redaktionellen Inhalt
  vernichtet. Der Rollback ist der verlustfreie Schnitt.

Messung danach:

    ✅ Reserve-Pool vollständig gate-fertig (6/6).

| Kandidat | Score | Flesch |
|---|---|---|
| `2026-10-07-7-gewohnheiten-fuer-finanzielle-freiheit` | 0.90 | 61.5 |
| `2026-10-07-handyvertrag-kuendigen-raus-aus-der-kostenfalle-verlaengerung` | 0.89 | 61.7 |
| `2026-10-07-wie-smart-home-geraete-deine-stromrechnung-wirklich-druecken` | 0.90 | 62.5 |
| `2026-10-07-campingurlaub-2026-clever-sparen-ohne-komfortverlust` | 0.90 | 66.1 |
| `2026-10-07-dsl-anbieter-wechseln-warum-treue-dich-bares-geld-kostet` | 0.89 | 63.3 |
| `2026-10-07-urlaub-sparen-7-clevere-wege-deine-kasse-zu-fuellen` | 0.90 | 61.1 |

(Lokal mit `spelling 0.5`, weil `hunspell` in dieser Umgebung fehlt – die
lokale Messung ist damit **strenger** als die von CI, nicht milder.)

### 2. Neue Wache: `scripts/artefakt_waechter.py`

Korpusweite Prüfung aller versionierten Maschinen-Artefakte, sechs Klassen:

| Klasse | Was geprüft wird |
|---|---|
| **A1** | `data/**/*.json` – JSON-Syntax |
| **A2** | `data/**/*.json` – doppelte Objektschlüssel |
| **A3** | `data/**/*.jsonl` – jede Zeile ein JSON-Objekt |
| **A4** | Konfliktmarker (`<<<<<<<`, `=======`, `>>>>>>>`, `|||||||`) |
| **A5** | `data/**/*.yaml\|yml` – Syntaxfehler und doppelte Schlüssel |
| **A6** | `content/**/index.md` – Frontmatter-Syntax und doppelte Schlüssel |

Alle sechs sind **hart**. Laufzeit über den echten Bestand: **1,8 s für 386
Artefakte**, keine Fehlalarme.

**Heilung ausschließlich beweisbar, sonst keine.** `--heal` repariert nur A2:
*letzter Eintrag gewinnt* – exakt das, was `json.loads()` beim Lesen ohnehin
tut; die Wache macht die stille Annahme sichtbar und schreibt sie fest. Vorher
und nachher gilt `json.loads(neu) == json.loads(alt)` – die Aussage ändert sich
für **keinen** Leser. A1/A3/A4/A5/A6 bleiben unangetastet: Ein nicht mehr
parsfähiges Artefakt zu rekonstruieren hieße, Inhalt zu erfinden. Die Wache
nennt stattdessen den Erzeugerbefehl und den letzten nachweislich gültigen
Stand im Git (gelesen, nie geschrieben).

Zwei Nachbesserungen, die erst die Regressionstests zutage brachten:

* **Idempotenz ist beweisbar.** Die Heilung meldete „bereits sauber“ als
  Erfolg; ein zweiter Lauf war damit nicht vom ersten zu unterscheiden. Sie
  meldet jetzt *nicht geändert* (`False`), wenn sie kein Byte geschrieben hat.
* **Einzug wie gelesen.** Der Einzug war hart auf 2 gesetzt; eine vierfach
  eingerückte Datei wäre auf eine Zeile eingedampft worden – aussagengleich,
  aber ein Diff-Schock, und ein solcher Diff wird beim nächsten Merge wieder
  zu Konfliktmaterial. Der Einzug wird jetzt aus dem Bestand gelesen.

### 3. Die Kette: messen läuft immer, heilen vor urteilen

`content-reserve.yml`:

* **Stufe 3 (Zertifizierung) läuft ab jetzt IMMER** (`if: !cancelled()`, ohne
  Koppelung an den Wachen-Selbsttest). Sie *misst*; sie entscheidet nichts.
  Auch bei rotem Wachen-Selbsttest wird zertifiziert, damit der End-Gate eine
  aktuelle Zahl hat – er bleibt trotzdem rot, nur mit der ehrlichen Klasse
  `WACHEN` statt der erfundenen Vorrats-Lüge.
* **Stufe 1/2 bleiben am Sabotageschutz hängen** (`steps.wachen.conclusion !=
  'failure'`). Neu ist nur, dass die Bedingung **ausgesprochen** ist, statt als
  stille Nebenwirkung von GitHub Actions zu wirken. Wer Inhalt schreibt, darf
  es nicht mit einer Wache tun, die ihren eigenen Beweis nicht besteht.
* **Der Artefakt-Wächter steht NACH der Zertifizierung**, nicht davor. Ein am
  Lauf-Anfang roter Wächter würde die Stufe abschalten, die seinen eigenen Fund
  heilt – genau der Fehler der übersprungenen Stufen 1–3. Reihenfolge:
  **heilen, dann urteilen.**

### 4. Der End-Gate unterscheidet Messung von Urteil

`reserve_gate.py` nennt jetzt die **Ursachenklasse** statt nur die Zahl
(`zertifikat_lage()`, `ketten_lage()`):

| Klasse | Bedeutung |
|---|---|
| `ok` | gemessen, Ziel erfüllt |
| `engpass` | gemessen, zu wenig Vorrat – der echte Fall |
| `artefakt` | Zertifikat fehlt oder ist unlesbar – **nicht gemessen** |
| `kette` | messende Stufe übersprungen – Messung nie erzeugt |
| `wachen` | Wachen-Selbsttest rot (Sabotageschutz) |

Und – die eigentliche Reparatur – **der Bericht leitet aus einer
fehlgeschlagenen Messung keine Ursachen mehr ab**:

    🛑 RESERVE-MESSUNG FEHLGESCHLAGEN – KEIN Vorrats-Urteil möglich.
       Ursachenklasse: artefakt
       Das Zertifikat ist STRUKTURELL KAPUTT (…). Typische Ursache: ein Merge
       hat zwei Stände desselben Maschinen-Artefakts verschmolzen …
       Die Zahl darunter (0/6) ist KEIN Bestand, sondern das Fehlen einer
       Messung. Wer sie als Engpass liest, reparaturiert nachts die falsche
       Baustelle.

       ⛔ Keine Engpass-Diagnose: sie würde Ursachen aus einer Zahl herleiten,
          die dieser Lauf nicht gemessen hat.

C2 bleibt unangetastet: Exit **1**. Ohne Messung ist nicht „Vorrat da“, sondern
„nicht gemessen“ – und genau das steht jetzt im Lauf. Die Chronik-Zeile trägt
die Klasse mit (`data/reserve-history.jsonl`), damit ein Trend künftig zwischen
Engpass und Messausfall unterscheiden kann.

### 5. Der Schreiber prüft, was er geschrieben hat

`reserve_readiness.py` schrieb das Zertifikat mit einem nackten
`write_text` – unterbrechbar, ohne Gegenprobe. Jetzt: `schreibe_zertifikat()`

* **atomar** (temporäre Datei im selben Verzeichnis, dann `os.replace`) – ein
  Zertifikat ist danach entweder alt oder neu, **nie halb**;
* **selbstgeprüft** – der geschriebene Stand wird zurückgelesen und gegen den
  Bericht abgeglichen (parsebar, Objekt, Kandidatenliste, gleiche `ready`-Zahl,
  **keine doppelten Schlüssel**). Schlägt die Prüfung fehl, bleibt die alte
  Datei unangetastet und der Lauf stirbt laut – kein stilles „Zertifikat
  geschrieben“.

### 6. Vertrag C33

`governance_contract.py` friert die Klasse ein:

Wache vorhanden · alle sechs Klassen erkannt · `--selftest` **und**
`--wirkungsprobe` **und** `--heal` registriert und ausgewertet · fail-closed
(keine Rekonstruktion) · im vertraglichen Minimum (`GUARDS`, C6) · am PR-Pfad
(`integrity-lock.yml`) **und** im Reserve-Lauf (`content-reserve.yml`) ·
dort **nach** der heilenden Stufe · End-Gate mit Ursachenklassen · Schreiber
atomar mit Gegenprobe · unter Siegel · mit Regressionstest.

Fünf Kunstbefunde werden im Kontrakt-Selbsttest rot (fehlende Klasse, PR-Pfad
ohne Wache, am Wachen-Selbsttest hängende Zertifizierung, End-Gate ohne
Ursachenklassen, nicht atomarer Schreiber); der echte Baum bleibt still.

Haus-Nummern: C24 ist die C24 Bank, C31 der Robustheits-Vertrag
(`robustheits_gate.py`) — **C33** ist darum die nächste freie Nummer.

### 7. Siegel und Regressionen

* `scripts/artefakt_waechter.py` und die geänderten Wachen stehen unter dem
  Integritäts-Siegel (`integrity_guard.FEST`).
* **`scripts/tests/test_artefakt_waechter.py` – 33 Fälle**: alle sechs Klassen
  erkannt, Negativproben (gleicher Schlüssel auf verschiedenen Ebenen, in
  Listeneinträgen), Heilung aussagengleich + idempotent + einzugtreu,
  Rekonstruktion verweigert, C15 (Prüfen schreibt nicht), CLI-Exit-Codes,
  Verdrahtung in GUARDS/Siegel/beide Workflows, Reihenfolge im Reserve-Lauf,
  Ursachenklassen des End-Gates, keine erfundene Engpass-Diagnose.

---

## Nachweis

* `python3 scripts/artefakt_waechter.py` → **Exit 0**: „✅ ARTEFAKT-WÄCHTER:
  386 Artefakte strukturell heil (JSON, JSONL, YAML, Frontmatter – parsebar,
  keine doppelten Schlüssel, keine Konfliktmarker).“ — Laufzeit 1,8 s.
* `--selftest` → **Exit 0**; `--wirkungsprobe` → **Exit 0** (A2-Sabotage
  erkannt, beweisbar geheilt, danach grün und idempotent).
* Gegenprobe auf dem **echten** Kaputt-Stand: die Wache findet genau die zwei
  vorhergesagten Funde (`data/reserve-quarantine.json`,
  `data/reserve-readiness.json`) und keinen dritten.
* `python3 scripts/reserve_readiness.py` → **Exit 0**, „✅ Reserve-Pool
  vollständig gate-fertig (6/6).“ (vor der Reparatur: Zertifikat unlesbar →
  „0/6“; nach reiner Artefakt-Heilung: 3/6; nach Inhalts-Reparatur: 6/6).
* `python3 scripts/reserve_gate.py` → **Exit 0**, „✅ Reserve-Pool gate-fertig:
  6/6 Kandidaten zertifiziert. Zertifikat 0.0 h alt (Grenze 36 h).“
* `python3 scripts/reserve_gate.py --cert <sabotiert>` → **Exit 1** mit
  Klasse `artefakt` und **ohne** Engpass-Diagnose; `RESERVE_STUFE3_STATUS=skipped
  python3 scripts/reserve_gate.py` → **Exit 1** mit Klasse `kette`.
* `python3 scripts/reserve_gate.py --selftest` → **Exit 0** (7 Fälle).
* `python3 scripts/governance_contract.py` → **Exit 0**, „alle 31 Regeln prüfen
  in beide Richtungen“; `--selftest` → **Exit 0 (C1–C33)**.
* `python3 scripts/selftest_runner.py` → **177 Wachen grün, 354 Uhr-Proben**
  (vorher 176 – die neue Wache läuft im vertraglichen Minimum mit).
* `python3 scripts/integrity_guard.py --gate` → **Exit 0**.
* `python3 scripts/automation_premium_audit.py --strict` → **Exit 0**.
* `python3 -m unittest discover -s scripts/tests -p test_artefakt_waechter.py`
  → **Ran 33, OK**; die Gesamtsuite (`discover -s scripts/tests`) → **Ran
  2356, OK (skipped=2)** – kein neuer roter Test.
* `hugo --minify --cleanDestinationDir` (Extended v0.164.0) → **rc=0, 80
  Seiten**.
* Ketten-Evidenz aus der API: Läufe `37347512536`, `37450734141`,
  `37486868704`, `37607427999`, `37645894042`, `37765762299` – je
  `conclusion: failure`, je im Schritt „Stock shortage must not look
  successful“; der letzte grüne Lauf davor ist `37298226945`.
* Pull Request mit `Closes #653`. Der Abschluss-Vermerk am Issue setzt
  `vorgangs-abschluss.yml` (Hausregel: nie von Hand).

---

## Was offen bleibt (benannt, nicht versteckt)

**Neun `2026-10-08`-Kandidaten sind weiterhin blockiert** – sie sind nicht nötig
für den Zielbestand 6, aber sie sind die Tiefe des Vorrats. Ihr Blocker ist
eine andere Klasse und **kein** Artefakt-Defekt, sondern eine redaktionelle
Regel (RS5 „Zahlenbehauptung ohne Satzbeleg oder klare Modellannahme“):

| Kandidat | Befund |
|---|---|
| `stromkosten-senken-clevere-haushaltsgeraete-im-ueberblick` | RS5: 55 |
| `haushaltskosten-reduzieren-so-gewinnst-du-die-kontrolle` | RS5: 30 |
| `dein-weg-zu-geringeren-monatskosten-schritt-fuer-schritt` | RS5: 28 + RS2 + RS3 |
| `waermepumpe-vs-gasheizung-2026-so-entscheidest-du-richtig` | RS5: 28 |
| `energiekosten-senken-smarte-helfer-fuer-den-haushalt` | RS5: 23 |
| `kleine-energiespar-tricks-die-deine-kosten-sofort-senken` | RS5: 23 |
| `balkonkraftwerk-foerderung-so-holst-du-dir-geld-zurueck` | RS5: 19 |
| `energieausweis-was-das-dokument-fuer-deine-fixkosten` | RS5: 19 |
| `vpn-zuhause-schutzschild-oder-unnoetige-fixkosten-falle` | RS5: 8 |

Das ist eine **Inhalts**-Baustelle für den Finisher, kein Gate-Defekt: Diese
Kandidaten sollen belegt werden, nicht freigeschaltet. Sie bleiben sichtbar und
werden von dieser Reparatur ausdrücklich **nicht** „grün geredet“.

---

**Ergebnis:** Ein Artefakt-Defekt kann nicht mehr als leerer Vorrat aussehen.
Die Artefakte werden korpusweit gegengelesen (386 in 1,8 s), der Schreiber
prüft was er schreibt, die messende Stufe läuft immer, der End-Gate nennt die
Klasse statt einer Zahl – und erfindet aus einer fehlgeschlagenen Messung keine
Ursachen mehr. Der Bestand ist geheilt und mit einem frischen, maschinell
erzeugten Zertifikat belegt: **6/6**. Keine Prüfung wurde abgeschwächt, keine
Latte gesenkt, nichts rückdatiert.
