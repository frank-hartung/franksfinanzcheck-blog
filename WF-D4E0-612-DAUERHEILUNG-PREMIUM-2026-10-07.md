# Content-Reserve · Vorgang WF-D4E0 (#612) — Dauerheilung auf Premium-Niveau

**Datum:** 07.10.2026 · **Issue:** #612 („🔧 Wartung · Inhaltsqualität · Vorgang WF-D4E0", Label `auto-report`)
**Workflow:** `.github/workflows/content-reserve.yml` — Step „Stock shortage must not look successful" (harter End-Gate), Lauf `37450734141` (06.10.2026, Commit `140859bc`)
**Reparatur:** dieser PR („Closes #612") · **Vorgänger:** #609 (Lesbarkeits-Heiler + Wirkungs-Deckung), #594 (Blocker-Klassen), #585 (Lesbarkeits-Gate), #482 (Politur-Ruinen als harte Regeln), #610 (Beleg je Tag)

## Kurzfassung

Der rote End-Gate war **korrekt**: „Stock shortage must not look successful" heißt,
dass ein zu kleiner Vorrat nicht wie Erfolg aussehen darf – und der Vorrat stand
bei **Ziel 6 / bereit 2**. Die Ursache lag nicht in der Zertifizierung (die hat
korrekt abgelehnt), sondern in **vier blinden Stellen der Kette**:

1. **Eine ganze Familie harter Publish-Regeln hatte keinen Schreiber.** R11
   (Jahreszahl-Split), R13 (Datums-Punkt) und R14 (Marker-Ruine) entscheiden seit
   #482 über die Veröffentlichung – aber keine Reserve- oder Live-Kette konnte sie
   heilen. Der Kandidat `2026-10-07-wie-smart-home-…` **scheiterte einzig an einem
   „SATZ: “-Präfix vor einer vollständig intakten Tabellenzeile** (Zertifikat:
   Qualität 0,95, alle übrigen Tore grün), blieb liegen und die Quarantäne nahm ihn
   als `reserve_blocked` aus dem Spiel.
2. **Die Geburt maß die Regel nicht, über die die Zertifizierung entscheidet.**
   `profi_quality_ok` prüfte Länge, Module, Keywords, Struktur – aber nicht die
   Lesbarkeit, obwohl Flesch ≥ 60 seit #585 ein **hartes** Publish-Kriterium ist.
   Sieben Kandidaten wurden mit Flesch 53,1–59,9 geboren und fielen später
   geschlossen durch die Zertifizierung – sie banden Heiler-/KI-Zeit statt Vorrat
   zu sein.
3. **Der Retry war blind.** `try_generate` sammelte die Ablehnungsgründe, gab sie
   aber nie an den nächsten Versuch weiter: dreimal derselbe Fehler mit dreimal
   derselben Wahrscheinlichkeit.
4. **Der Trend-Beweis war strukturell blind.** `reserve_gate` schrieb die
   Chronik-Zeile **nach** dem einzigen Commit-Schritt des Laufs. Jeder rote Lauf
   verlor sie wieder – der letzte CI-Eintrag in `data/reserve-history.jsonl`
   stammte vom 02.10.2026, alle späteren Zeilen waren lokale Reparaturläufe.

**Kein Gate wurde abgesenkt.** Der End-Gate zählt weiterhin `ready` aus dem
Zertifikat gegen das Ziel und verlangt ein Zertifikat < 36 h; die Zertifizierung
prüft unverändert mit denselben harten Regeln; der neue Heiler schreibt
ausschließlich, was er beweisen kann (Tor T1–T4), sonst nichts.

## Befund

### Was der End-Gate gemeldet hat (Zitat, gekürzt)

> **Entwürfe, Zertifikate und Reporte sichern (auch bei Engpass)** … danach:
> **Step „Stock shortage must not look successful"** → `python3 scripts/reserve_gate.py`
> → Exit 1. Der Lauf endete nach 46 Minuten rot, obwohl alle Stufen technisch liefen.

Lauf-Historie vor der Reparatur (letzte 6 Läufe): **fünf rot, einer grün**
(letzter grüner Lauf: `23110bc5`, 05.10.2026, 10:41:57 UTC).

### Das Zertifikat (`data/reserve-readiness.json`, 07.10.2026 13:20:00 UTC)

| Kandidat | Befund |
|---|---|
| `2026-10-05-bueroausstattung-…` | ✅ 0,958 |
| `2026-10-07-handyvertrag-kuendigen-…` | ✅ 0,966 |
| 7 × Lesbarkeit | Flesch 57,9 / 59,4 / 59,9 / 58,8 / 55,8 / 53,1 / 52,3 (Schwelle 60) |
| `2026-10-07-etf-sparplan-…` | 0,839 (structure 0,70) |
| `2026-10-07-heizoel-preise-2026-…` | Zeichenlänge (check_length.py) |
| `2026-10-07-wie-smart-home-…` | **R14-MARKER-RUINE** „SATZ: “ — Qualität 0,95, Lesbarkeit 0,95 |

**Ziel 6 / bereit 2 / Pool 12.** Der Vorrat ist der Puffer, aus dem ein
verpasster Slot aufgefangen wird – mit zwei bereiten Kandidaten war der End-Gate
rechnerisch rot, egal wie gut die Nacht technisch lief.

### Der reale Ruinen-Fall (07.10.2026)

```
SATZ: | Thread | 2,4 GHz | 10–20 m (Mesh) | 0,05–0,2 W | 40–80 € |
```

– ein Tablettenschaden aus einem Politur-Lauf: Das Präfix „SATZ: “ stand vor
einer vollständig intakten Tabellenzeile. Kein Werkzeug der Kette durfte es
entfernen; die Zertifizierung läuft fail-closed; die Quarantäne-Akte führte den
Kandidaten ab 10:42 UTC als `reserve_blocked` (Signatur `…r14-marker-ruine…`).

**Lehre:** Ein Blocker ohne Heiler ist ein unerreichbares Ziel (#349, #594) –
und ein Geburts-Gate, das die Publish-Schwelle nicht misst, erzeugt sie Nacht
für Nacht neu.

## Die Dauerheilung (sechs Teile, alle im PR)

1. **Der fehlende Heiler existiert** — `scripts/politur_ruine_heiler.py` (neu,
   564 Zeilen): heilt R11/R13/R14 ausschließlich nach der Muster-SSOT
   `sprachkern.POLITUR_RUINEN`, hält **Tor T1–T4** ein (keine heilbare Ruine
   bleibt; keine neue Ruine; kein neuer harter `publish_gate`-Fund;
   Frontmatter/Links/Shortcodes/Überschriften stabil; Wortzahl ≥ 97 % − belegter
   Verlust) und ist **idempotent**. R12-ZAHL-RUINE und R16-PROMPT-ECHO werden
   nur gemeldet – Raten wäre eine Fälschung.
2. **Der Heiler läuft in beiden Ketten** — `reserve_finisher.HEALER_CHAIN`
   (Reserve, letzter Textschritt) und `content-engine-v2.yml` (Live-Artikel des
   Tages), jeweils fail-closed mit Log-Restlücke.
3. **Die Geburt misst die Publish-Regel** — `generate_drafts.lesbarkeits_befund`
   prüft neue Rohtexte gegen die **importierte** SSOT-Schwelle
   `readability_check.NEW_FLESCH_MIN` (keine zweite Zahl, #585); das
   Geburts-Gate `profi_quality_ok` führt den Befund als Ablehnungsgrund. Was die
   Zertifizierung nachweislich ablehnt, entsteht gar nicht erst.
4. **Der Retry hat ein Gedächtnis** — `generate_article_text(…, hinweise=…)`
   baut aus den Befunden des Vorversuchs einen **KORREKTUR-AUFTRAG** in den
   Prompt; `try_generate` und die zweite Qualitätsschleife reichen ihn weiter.
   Statt blind zu würfeln, wird der konkrete Fehler gezielt abgestellt.
5. **Der Trend-Beweis überlebt den roten Lauf** — `reserve_gate.py --chronik`
   schreibt die Chronik-Zeile **vor** dem Sicherungs-Commit und ist **je Lauf
   idempotent** (der End-Gate schreibt nichts doppelt). Damit steht die Evidenz
   jeder Nacht im Buch – auch der roten.
6. **Deckung, Klassen und Governance halten es fest** —
   `reserve_healer_coverage.WIRKUNGS_PROBEN` verlangt für den neuen Heiler eine
   grüne `--wirkungsprobe`; `reserve_blocker_klassen.GATE_BEFUNDE` klassifiziert
   die drei heilbaren Ruinen als `heilbar` **mit** ihrem Heiler (die nicht
   rekonstruierbaren Geschwister bleiben bewusst „unbekannt"/fail-closed); die
   neue **Governance-Regel C29** („Der Schreiber prüft, was über ihn
   entscheidet") prüft die vier blinden Stellen am echten Baum **und** mit
   Sabotagen im Selbsttest; der Heiler steht unter Integritäts-Siegel
   (FEST-Liste, Akte „NEU UNTER SIEGEL").

## Beweise (07.10.2026, offline – ohne Netz, ohne KI-Key)

* **Heiler:** `--selftest` ✅ · `--wirkungsprobe` ✅ „3 → 0 heilbare Ruinen,
  Tor T1–T4 erfüllt, zweiter Lauf ohne Änderung".
* **Realfall:** `--file …/2026-10-07-wie-smart-home-… --fix` heilt **exakt eine
  Zeile** (`SATZ: | Thread | …` → `| Thread | …`, Links/Struktur unberührt);
  Re-Zertifizierung: **`ready: true`**, Score 0,89 (lokale Messung; CI-Wert war
  0,95), `Publish-Gate: 0/1 Artikel am Gate scheitern`; zweiter Lauf
  „Ruinen 0 → 0 [nichts-zu-tun]".
* **Unit-Tests:** `125 Tests in scripts/tests/test_reserve_pipeline.py` grün,
  davon **14 neue** (Ruinen-Heilung je Klasse, fail-closed-Fälle, Idempotenz,
  Realfall smart-home, Geburtsmessung gegen die SSOT, Retry-Gedächtnis,
  Chronik-Idempotenz + Workflow-Reihenfolge, Klassen-Deckung).
* **Suiten:** `selftest_runner.py` → **167 Wachen, 334 Uhr-Proben, alles grün**;
  `reserve_gate --selftest` ✅; `reserve_healer_coverage --selftest` ✅;
  `reserve_blocker_klassen --selftest` ✅.
* **Governance:** `governance_contract.py --selftest` ✅ (C1–C29 mit
  Kunstbefunden; jede Sabotage wird erkannt) · Vollprüfung ✅ („alle 28 Regeln
  prüfen in beide Richtungen").
* **Build:** Hugo 0.164.0 (extended) — 78 Seiten, 1.324 statische Dateien, grün.
* **Integrität:** Neusignatur mit `--set-current` (zweiter Commit dieser PR):
  Akte „NEU UNTER SIEGEL" für `scripts/politur_ruine_heiler.py`, Historie-Zeile
  in `data/integrity_history.jsonl`.

## Nach dem Zusammenführen mit `main`

Während dieser Reparatur sind zehn Commits auf `main` gelandet (u. a. **#624**
mit einer eigenen Governance-Regel „C28 – Die Klasse geht dem Kanal vor" für die
Auslieferungs-SLO, #611). Der Stand wurde zusammengeführt, **die neue Regel
dieser Reparatur heißt darum C29** – doppelte Regelnummern wären in Logs und
Greps zwei Wahrheiten. Die Zusammenführung ist grün nachgeprüft: Tests, Suiten,
Governance-Selbsttest (C1–C29) und Integritäts-Gate (47 Kerndateien).



## Grenzen – ehrlich benannt

* Die sieben Lesbarkeits-Blocker **heute** löst dieser PR nicht per
  Deterministik – das kann die Klasse beweisbar nicht (Ø Silben/Wort 1,85–1,96;
  Nahtstellen fast null). Der Weg ist: Das Geburts-Gate erzeugt keine neuen mehr,
  der Retry bekommt den konkreten Befund als Auftrag, und Stufe B des
  Lesbarkeits-Heilers (workflow-seitige KI-Keys) trägt die bestehenden über die
  Schwelle. Ein Gate wurde dafür nicht gesenkt.
* Der lokale Re-Zertifikatswert (0,89) läuft in einer Sandbox ohne Hunspell
  (Rechtschreib-Teil 0,5 statt CI-Niveau); die **CI-Zertifizierung bleibt die
  Wahrheit**.
* R12/R16 bleiben redaktionelle Fälle per Vertrag – der Heiler meldet sie,
  statt zu raten.
* Die volle Abnahme zeigt der **nächste Nachtlauf** von
  `content-reserve.yml` (Chronik-Zeile mit echter `GITHUB_RUN_ID`, Zertifikat,
  End-Gate).

## Beobachtung (Abnahme)

1. Nächster Lauf `content-reserve.yml`: End-Gate grün **oder** eine
   Chronik-Zeile mit dem echten `GITHUB_RUN_ID`, die die Messung der Nacht
   festhält.
2. Nächster Lauf `content-engine-v2.yml`: Log-Zeile des Politur-Ruinen-Heilers;
   keine neue „SATZ: “-Ruine im Bestand.
3. `data/reserve-readiness.json`: `2026-10-07-wie-smart-home-…` ist nach der
   Heilung **ready** (oder wird vom Lauf neu/zurecht bewertet).

## Regressionen

Alle 14 neuen Tests sind dauerhafte Verträge. Zusätzlich hält die
Governance-Regel C29 (inkl. Selbsttest mit Sabotagen) fest, dass die vier
blinden Stellen nicht wiederkommen können. Die Integritäts-Akte zeichnet den
Heiler als Schwellen-Wache unter Siegel nach.

---

*„Stock shortage must not look successful" — der Satz bleibt stehen. Der
Unterschied ist, dass die Nacht jetzt etwas dagegen tut.*
