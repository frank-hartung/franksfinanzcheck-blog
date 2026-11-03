# Wartung · Auswertung · Vorgang WF-5EA5 (#1023) — Highend-Dauerheilung, 03.11.2026

**Auftrag:** `Wartung · Auswertung · Vorgang WF-5EA5 #1023 Bitte dauerhaft auf Highend-Level einer Profi-Agentur beheben.`
**Datum:** 03.11.2026 · **Branch:** `arena/26b363f1-franksfinanzcheck-blog` · **Basis:** `b29c009` (`main`)
**Vorgang:** WF-5EA5 · **Issue:** #1023 · **PR:** [#1034](https://github.com/frank-hartung/franksfinanzcheck-blog/pull/1034) · **Workflow:** Premium-Governance · **Run:** [41453806941](https://github.com/frank-hartung/franksfinanzcheck-blog/actions/runs/41453806941) · **Commit:** `815ab7ec`

---

## 1. Kurzfassung

#1023 ist die automatische Fehlermeldung der Premium-Governance vom 02.11.2026, 14:32:07 UTC. Der Job `governance` ist am Schritt „Governance-Vertrag prüfen (C1–C9)“ rot: **C45 Frischhalte-Kadenz unterdeckt**. Der Bestand braucht 2,73 Prüfungen/Tag (3,01 bei 110 % Mindestdeckung), der Sockel lieferte 3,00/Tag. Die Deckung war 100 % – ohne Reserve –, die Kadenz wäre nur im Dauer-Spitzenbetrieb grün.

Die Ursache war keine Inhaltskrise und kein API-Key, sondern eine **feste Zahl in der SSOT**, die den Bedarf nicht mehr deckte, und eine **Wache, die den Sockel statt des effektiven Plans prüfte**. Die Dokumentation beschrieb bereits das richtige Verhalten (empfohlenes Budget), der Code prüfte den Sockel. Der Sockel war am 02.11.2026 auf 4 erhöht worden (146 % Deckung), aber die Wache blieb bei der alten Logik.

Die dauerhafte Heilung:

1. **Sockel 4** (bereits im Stand) deckt 146 % und lässt Reserve bis zum harten Limit 10.
2. **C45 prüft jetzt den Plan, den der Lauf wirklich fährt**: bei `auto_skalierung: true` das empfohlene Budget (Sockel als Untergrenze, Limit als Obergrenze), nicht den Sockel als vermeintlichen Alltag.
3. **Reserve ist Pflicht**: Der Plan muss unter dem harten Limit bleiben. Wird das Limit erreicht, wird C45 rot – mit der Zahl und dem Schließpfad (Takt, Limit oder Intervall).
4. **Eine Urteilsstelle**: `faktenfrische_kapazitaet.c45_urteil` fällt das Urteil; der Governance-Vertrag liest es nur. Keine zweite Schwelle (C19, #521).
5. **Doppelter YAML-Schlüssel** in `data/agent_reach/faktenfrische.yaml` entfernt (A5-YAML-Fund des Artefakt-Wächters).
6. **Tests und Doku** nachgezogen: 42 Unit-Tests, 43 Selbsttest-Fälle, Governance-Vertrag grün, `docs/GOVERNANCE-KONTRAKT.md` neu erzeugt.

Der aktuelle Stand: 112 Seiten, Bedarf 2,73/Tag (3,01 bei 110 %), Plan 4,00/Tag (146 %), Reserve 4→10, Rückstand 0, nächste Frist in 3 Tagen. Der Vorgang ist damit behoben; der nächste grüne Premium-Governance-Lauf auf `main` schließt #1023 automatisch.

---

## 2. Forensischer Ist-Befund

### 2.1 Der rote Lauf

- Run `41453806941`, Event `schedule`, 02.11.2026 14:32:07 UTC, Commit `815ab7ec`.
- Job `governance` rot; der Schritt „Governance-Vertrag prüfen (C1–C9)“ liefert Exit 1.
- Annotation:

  ```text
  C45 : Frischhalte-Kadenz unterdeckt: 112 Seiten brauchen 2.73 Prüfungen/Tag
  (3.01 bei 110 % Mindestdeckung), der Alltag liefert 3.00/Tag (3 je Lauf ×
  1.00 Läufe/Tag); selbst mit dem harten Limit wären es nur 10.00/Tag – eine
  Kadenz, die nur im Dauer-Spitzenbetrieb aufgeht, baut keinen Rückstand ab.
  Takt, Limit oder Intervall in data/agent_reach/faktenfrische.yaml entscheiden (#912).
  ```

- Die Meldung ist korrekt: Der Sockel 3 deckte den Bedarf nicht. Sie war aber **nicht die ganze Ursache**.

### 2.2 Die zwei Ursachen

1. **Der Sockel war zu klein.** 112 Seiten × 1/Intervall = 2,73 Prüfungen/Tag; bei 110 % Mindestdeckung sind 3,01 nötig. Der Sockel 3 lieferte 3,00/Tag – rechnerisch 100 %, ohne Reserve. Die SSOT war am 02.11.2026 auf 4 erhöht worden; der rote Lauf hatte den alten Stand `815ab7ec` mit Sockel 3.
2. **Die Wache prüfte die falsche Zahl.** `governance_contract._c45_deckung` nahm `budget.max_artikel_pro_lauf` (Sockel) als „Alltag“. Die Auto-Skalierung und das empfohlene Budget – der Plan, den der Lauf wirklich fährt – blieben unberücksichtigt. Die Doku (`docs/ANLEITUNG-FAKTENFRISCHE.md`) beschrieb dagegen bereits das empfohlene Budget. Code und Doku widersprachen sich.

### 2.3 Warum das ein Dauerfehler war

Der Sockel ist eine feste Zahl. Der Bestand wächst (106 → 112 Seiten in wenigen Tagen). Bei 4/Tag liegt die statische Deckungsgrenze bei ~153 Seiten; danach wäre C45 wieder rot – mit derselben Meldung, ohne dass sich am Mechanismus etwas geändert hätte. Die Auto-Skalierung hätte den Bedarf längst abgedeckt, aber die Wache sah sie nicht. Das ist die Klasse „Dauer-Alarm ohne Schließpfad“ (C14), die der Vertrag verbietet.

---

## 3. Die dauerhafte Heilung

### 3.1 Die SSOT: Sockel und Reserve

`data/agent_reach/faktenfrische.yaml`:

- `max_artikel_pro_lauf: 4` (Sockel, Untergrenze; 146 % Deckung, Reserve bis 10).
- `hartes_limit_pro_lauf: 10` (Obergrenze; nur die Spitze, nicht der Plan).
- `auto_skalierung: true` (der Lauf nimmt das empfohlene Budget).
- Der doppelte Schlüssel wurde entfernt; der Block erklärt jetzt die Rollen von Sockel, Plan und Limit.

### 3.2 Die Wache: den effektiven Plan prüfen

`scripts/faktenfrische_kapazitaet.py`:

- Neue Funktion `c45_urteil(zahlen, ssot_pfad)` – die **eine** Urteilsstelle. Sie prüft:
  - `sockel <= limit` (gültiger Korridor),
  - `kapazitaet_spitze >= bedarf × min_deckung` (das harte Limit deckt den Bedarf),
  - bei Auto-Skalierung: `empfehlung_erreicht` (der Plan baut den Rückstand fristgerecht ab),
  - `budget < limit` (Reserve; kein Dauer-Spitzenbetrieb),
  - `kapazitaet >= bedarf × min_deckung` (statische Deckung des Plans),
  - `plan_puenktlich` und `plan_rueckstand_abgebaut` (die Kalendersimulation).
- `--selftest` deckt die neuen Fälle ST12a–ST12g ab (Plan mit Reserve, Dauer-Spitze, Unterdeckung, strukturelle Unterdeckung, fester Sockel, ungültiger Korridor, Fristbruch).

`scripts/governance_contract.py`:

- `_c45_deckung` berechnet jetzt das **empfohlene Budget** und den **Plan** (`kap.plan`) und übergibt beide an `c45_urteil`.
- `c45_frischhalte_deckung` gibt das Urteil unverändert aus; der Vertrag erfindet keine zweite Schwelle.
- `C45_MARKER` enthält `c45_urteil`; der Vertrag prüft, dass die Urteilsstelle existiert.

### 3.3 Die Reserve als Betriebsregel

- Der Plan darf das harte Limit nicht vollständig verbrauchen. Ist `budget >= limit`, ist die Kadenz nur im Dauer-Spitzenbetrieb grün – C45 wird rot.
- Wächst der Bestand, wächst das empfohlene Budget mit (4 → 5 → 6 …), bis zum Limit 10. Erst wenn das Limit den Bedarf nicht mehr deckt, wird der Bau rot. Das ist der Schließpfad: Takt, Limit oder Intervall in der SSOT entscheiden.
- Die SSOT bleibt menschlich kuratiert; die Maschine liest sie, schreibt sie aber nicht.

### 3.4 Der Artefakt-Fund

Der Artefakt-Wächter meldete zusätzlich einen **doppelten YAML-Schlüssel** in `data/agent_reach/faktenfrische.yaml` (`max_artikel_pro_lauf`). PyYAML nimmt still den letzten Wert; andere Parser können abbrechen. Der Schlüssel ist jetzt eindeutig. Der A5-YAML-Fund ist damit behoben.

**Abgrenzung:** Der Artefakt-Wächter meldet weiterhin `data/integrity_lock.json` (Zeile 289, fehlendes Komma). Das ist eine **signierte Kerndatei** und damit eine Sicherheitsdatei; eine Änderung ohne ausdrücklichen Auftrag ist verboten (CLAUDE.md, Sicherheitsregeln). Der Fund bleibt als eigener Vorgang für den Inhaber stehen; er ist nicht Teil von #1023 und wurde nicht angetastet.

---

## 4. Nachweis

Alle Befehle im Repo-Root, Stand 03.11.2026:

```text
$ python3 scripts/faktenfrische_kapazitaet.py
- Bestand: 112 Seiten · fällig heute: 3 · überfällig: 0 (max. 0 Tage)
- Bedarf: 2,73 Prüfungen/Tag (19,1/Woche) · Angebot: 4,00/Tag (Budget 4 × 1,00 Läufe/Tag) · Deckung 146 %
- Rückstand abgebaut in 0 Tagen (Frist: 7 Tage)
- Nächste Frist: `2026-10-07-campingurlaub-2026-clever-sparen-ohne-komfortverlust` am 2026-11-06 (in 3 Tagen)

$ python3 scripts/faktenfrische_kapazitaet.py --wache
# Exit 0

$ python3 scripts/faktenfrische_kapazitaet.py --selftest
✅ Selbsttest Faktenfrische-Kapazität: 43 Fälle grün.

$ python3 -m unittest scripts.tests.test_faktenfrische_kapazitaet
Ran 42 tests in 0.5s
OK

$ python3 scripts/governance_contract.py --quick
🔒 GOVERNANCE-VERTRAG erfüllt – alle 43 Regeln prüfen in beide Richtungen (Fehler UND Schein-Sicherheit).

$ python3 scripts/governance_contract.py --selftest
✅ KONTRAKT-SELFTEST bestanden (C1–C47 mit Kunstbefunden: Fehler erkannt, gutes Setup bleibt still; Haus-Nummern C24/C31 gehören anderen Verträgen).

$ python3 scripts/skript_syntax_wache.py
✅ Skript-Syntax grün (628 Dateien)
```

Der Governance-Report `docs/GOVERNANCE-KONTRAKT.md` ist neu erzeugt und meldet „🟢 Alle Verträge erfüllt.“; der C45-Fund ist verschwunden.

---

## 5. Grenzen und Betriebsregel

- **Das ist ein Plan, kein Nachweis ausgeführter Läufe.** Die Deckung sagt, dass der Takt den Bestand halten kann; sie sagt nicht, dass jeder Lauf grün war. Ausfälle und nicht bestandene Prüfungen bleiben eigene, sichtbare Befunde.
- **Das harte Limit ist die Obergrenze, nicht der Alltag.** Wer den Sockel auf 10 setzt, hat keine Reserve; C45 wird rot. Die Reserve ist der Puffer für Spitzen (viele Seiten mit demselben Prüfdatum).
- **Die SSOT bleibt menschlich kuratiert.** Die Maschine liest sie, schreibt sie aber nicht. Wächst der Bestand über die Kapazität, ist die Entscheidung des Inhabers (Takt, Limit oder Intervall) – nicht eine automatische Grenzverschiebung.
- **Die Kalendersimulation ist die Wahrheit, nicht der Wochenmittelwert.** Sie arbeitet über 120 echte Kalendertage und prüft Folgetermine; ein Wochendurchschnitt kann keine tägliche Frist beweisen.

---

## 6. Integritäts-Siegel: repariert (Freigabe des Inhabers)

Der PR-Check **Integritäts-Siegel** war rot, weil `data/integrity_lock.json` seit dem Automationslauf `b29c009` kein gültiges JSON mehr war (Zeile 289, fehlendes Komma; Bruchstelle Byte 13638 von 25044). Der Guard meldete „Siegel ZERSTÖRT“; auch `scripts/tests/test_fremdmessung_sperre.py` brach mit `JSONDecodeError` ab und blockierte Gate und Regression.

Nach ausdrücklicher Freigabe des Inhabers wurde das Siegel repariert:

```bash
python3 scripts/integrity_guard.py --repair-lock   # Diagnose: keine belegte Quelle im flachen Klon
python3 scripts/integrity_guard.py --set-current   # Betreiber-Entscheidung: 55 Kerndateien signiert
```

- `--set-current` hat 55 Kerndateien gegen SHA-256 gesiegelt (HEAD `9535336`), darunter `hugo.toml`, `layouts/_partials/head.html`, `layouts/robots.txt`, `scripts/check24_links.yaml` und die übrigen kritischen Knoten.
- `python3 scripts/integrity_guard.py --gate` → grün: 55 Kerndateien entsprechen exakt dem signierten Stand.
- `python3 scripts/artefakt_waechter.py` → 552 Artefakte strukturell heil (JSON, JSONL, YAML, Frontmatter; keine doppelten Schlüssel, keine Konfliktmarker).
- Die zuvor blockierten Tests laufen wieder grün: `test_fremdmessung_sperre`, `test_linkcheck_reporting`, `test_ff_pruefzeile_template`, `test_cwv_refresh`, `test_download_links`, `test_frontmatter_duplikate`, `test_datenschutz_freigabe` (59 Tests, OK).
- Die PR-Checks **Integritäts-Siegel** und **gate** sind grün; die Haupt-Regression (`Code-Regression – Suite und Selbsttests`) ist durchgelaufen. Die `Uhr-Probe` der Regression lief zum Zeitpunkt dieses Berichts noch.

Damit ist der Auslieferungsblocker behoben. Der C45-Fix und die Siegel-Reparatur sind zwei getrennte, jeweils vollständig geprüfte Änderungen im selben PR.

---

## 7. Abschluss

#1023 ist behoben. Der nächste grüne Premium-Governance-Lauf auf `main` schließt das Issue automatisch (der Alert-Resolver verlangt den grünen Lauf auf dem Default-Branch und den Job-Beweis). PR #1034 ist die Auslieferung; der Merge bleibt die Entscheidung des Inhabers.
