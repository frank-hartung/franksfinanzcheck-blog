# Beweis-Ledger-Isolation · C27 – Dauerheilung

**Datum:** 07.10.2026
**Auslöser:** Nebenbefund beim Siegeln der Auslieferungs-Heilung **#610**
(PR **#620**, Merge-Commit `28fe5a2`). Beim Nachweis, dass die Suite grün ist,
fiel auf, dass ein Testlauf **echte Zeilen in `data/audit/`** hinterließ –
ein versioniertes, append-only bewachtes Beweis-Ledger.

Der Befund war als „Nebenbefund" notiert und sollte in einer späteren Sitzung
geheilt werden. Dieser Bericht ist die Heilung.

## Befund

**`data/audit/*.jsonl` ist kein Logfile.** `history_guard.py` bewacht das
Verzeichnis als append-only (Regel **H6**: „Historie geschrumpft" /
„Append-Only verletzt" sind harte Fehler), 37 Dateien sind versioniert, und
`frankautoops-report.yml` committet den Stand regelmäßig (`git add data/audit/`).
Jede Zeile ist eine Behauptung über den Betrieb.

**Drei Unit-Tests schrieben solche Behauptungen – nachweislich, im Baum:**

| # | Test | Kette bis zur Zeile | Art der Zeile |
|---|---|---|---|
| 1 | `test_affiliate_intent_guard`<br>`.test_bestand_gate_checks_intent_dimension` | `bestand_gate.run_gate()` → `publish_gate.affiliate_profi_failures()` → **Subprozess** `affiliate_profi_check.py --json` → `log_event()` | `affiliate_profi_check/check` |
| 2 | `test_clear_text_logging_security`<br>`.test_secrets_age_guard_record_success_and_list_are_clean` | `secrets_age_guard._record_success("GROQ_API_KEY")` → `log_event()` | `secrets_age_guard/record-success` |
| 3 | `test_publication_reliability`<br>`.test_publish_gate_heilt_r5_vor_der_harten_pruefung` | `pg.main()` mit `DRY_RUN=False` → `log_event(action="gate")` | `publish_gate/gate` |

Reproduziert am 07.10.2026 durch Fingerabdruck aller 2925 Dateien vor/nach
einem Suite-Lauf: **1978 Tests, OK** – und zwei neue Zeilen im versionierten
Ledger. Jeder Eintrag wurde einem Test zugeordnet, indem `log_event` ummantelt
und jeder Teststart mit Zeitstempel notiert wurde (Subprozess-Schreiber über
die Zeitachse).

**Befund 1 – die Zeilen standen bereits im Buch.**

`data/audit/2026-10-03.jsonl:136`, committet, letzte Zeile der Datei:

```json
{"ts": "2026-10-03T18:26:51Z", "module": "publish_gate", "action": "gate",
 "input": {"candidates": ["2026-09-07-r5-live"]},
 "output": {"gated": ["2026-09-07-r5-live"], "demoted": ["2026-09-07-r5-live"],
            "editorial_holds": []}, "status": "gated"}
```

`2026-09-07-r5-live` ist eine **Test-Fixture** aus
`test_publication_reliability.py`. Das Beweis-Ledger behauptete vier Tage lang
einen am Gate verworfenen und auf `draft` zurückgestuften Live-Artikel, den es
nie gab.

`data/audit/2026-10-05.jsonl`, Zeilen 2, 162, 185, 187 – **alle vier**
`record-success`-Einträge des gesamten Ledgers:

```json
{"module": "secrets_age_guard", "action": "record-success",
 "input": {"var": "GROQ_API_KEY", "proof_by": "content-engine-v2"},
 "output": {"quality": "declared"}}
```

Gegenbeweis aus den Workflows: `--record-success` wird in CI ausschließlich von
`pinterest-ai.yml` und `pinterest-token.yml` aufgerufen, und nur für
`PINTEREST_TOKEN_KEY` (`--proof-by pinterest-ai` bzw. `pinterest-token`).
`proof_by: content-engine-v2` ist wörtlich der Wert aus dem Test.
`social-autopilot.yml` hält sogar ausdrücklich fest: *„Probe und nicht
`--record-success`: eine fremde Erfolgsmeldung gilt nicht."* Genau diese fremde
Erfolgsmeldung stand als Beweis im Buch – mit `quality: declared`, also
aufgewertet statt als `declared_foreign` abgewertet.

**Befund 2 – ein Monkeypatch hätte nicht gereicht.**

Leckstelle 1 entsteht in einem **Kindprozess**. `mock.patch.object` wirkt nur
im Testprozess; `publish_gate` startet `affiliate_profi_check.py` über
`subprocess.run`. Das erklärt, warum das Haus zwar drei korrekte
Isolations-Muster kannte (`test_editorial_review_gate` und
`test_publication_release_wache` patchen `audit_log.log_event`,
`publication_release.selftest` ebenso) – und warum sie hier alle nicht griffen.

**Befund 3 – die dritte Leckstelle ist latent, nicht harmlos.**

`pg.main()` schreibt den gate-Entscheid nur, wenn `gated` nicht leer ist. Greift
die R5-Heilung, bleibt `gated` leer und es entsteht keine Zeile: Der Test lief
in drei Folgeläufen sauber. Der Schreibpfad ist damit **zufallsabhängig** – und
die committete Zeile vom 03.10.2026 ist der Beweis, dass er feuert. „Passiert
bei mir nicht" ist hier kein Widerlegung, sondern Glück.

**Befund 4 – die Wache war halb gebaut.**

Leckstelle 2 patchte `_mutate_state` (Zustandsdatei geschützt), ließ aber den
Audit-Zweig offen. Dieselbe Datei `test_affiliate_intent_guard.py` setzt an
acht anderen Stellen `aig.DRY_RUN = True` mit dem Kommentar *„Beweislauf
schreibt nichts ins Repo"* – nur `run_gate()` nicht, weil dort ein Flag im
Elternprozess ein Kind nicht erreicht. Die Absicht war vorhanden, das Werkzeug
fehlte.

## Dauerhafte Reparatur

**1. Der Engpass trägt den Vertrag** (`scripts/audit_log.py`).
Jede Zeile des Ledgers geht durch `log_event()`. Zwei Umgebungsvariablen:

- `FFC_AUDIT_DIR` – Zielverzeichnis umlenken. Die Zeilen entstehen vollständig
  und bleiben lesbar, landen aber nicht im Buch des Repos.
- `FFC_AUDIT_DISABLE` – harter No-Op, `log_event()` liefert `None`.

Beide stehen in der **Umgebung**, nicht in einer Prozess-Variable, weil sich
die Umgebung in jedes Kind erbt. Schreib- *und* Lesepfad (`load_events`,
`report`, `cleanup`) gehen durch `audit_verzeichnis()`, damit ein umgelenkter
Lauf seine eigenen Zeilen liest. `ops_report.py` las als einziger Verbraucher
direkt über `audit_log.AUDIT_DIR` und folgt jetzt derselben Auflösung.
Neu: `--selftest`, der den Vertrag in beide Richtungen beweist.

**2. Eine Sandbox statt drei Handgriffe** (`scripts/repo_isolation.py`, neu).
`ledger_sandbox()` lenkt um und liefert den Pfad; `beweis_ledger_unangetastet()`
legt zusätzlich einen SHA-256-Fingerabdruck aller 37 Ledger-Dateien an und
bricht **nach** dem Block mit AssertionError ab, sobald eine Zeile entsteht,
wächst oder verschwindet – der Beweis hält also auch, wenn die Prüfung selbst
wirft. `--selftest` vorhanden.

**3. Die drei Tests sind geheilt** und lesen die umgelenkte Zeile ausdrücklich
zurück. Ohne diese Gegenprobe wäre eine zu grobe Stummschaltung als Heilung
durchgegangen: Das Protokollieren bleibt eingeschaltet, es schreibt nur nicht
mehr ins Buch. Bei Leckstelle 3 entfiel außerdem eine doppelt aufgeführte
`patch.object(pg, 'offenlegung_failures', …)`-Zeile.

**4. Regressionstests** (`scripts/tests/test_audit_ledger_isolation.py`, neu,
15 Tests) in drei Schichten:

- **Vertrag des Engpasses** – Umlenkung und Stummschaltung im eigenen Prozess
  *und* im Subprozess, Leser folgen der Umlenkung, Selbsttests als Skript.
  Dazu die Schein-Sicherheits-Probe: Ohne Schalter **muss** `AUDIT_DIR` scharf
  sein. Eine Isolation, die das Protokollieren im Betrieb abschaltet, würde
  Beweise vernichten statt zu fabrizieren – der teurere der beiden Fehler.
- **Bekannte Leckpfade** – `affiliate_profi_check.py --json` als echter
  Kindprozess, `bestand_gate.run_gate()` Ende-zu-Ende, `_record_success()`.
  Jeweils mit Gegenprobe, dass die Zeile im Sandkasten *ankommt*.
- **Wache gegen neue Leckstellen** – meldet jeden Test, der einen bekannten
  Einstieg ohne Sandbox aufruft, mit Datei und Zeile.

Zwei Falschbefunde, die diese Wache beinahe selbst gebaut hätte, sind als
Tests eingefroren: `pg` heißt in `test_ruleset_restoration.py`
`pflichtcheck_guard` und nicht `publish_gate` (ein Alias trägt keine
Bedeutung – Importe werden pro Datei aufgelöst), und `self.run_gate()` in
`test_schema_seo_gate.py` ist eine eigene Hilfsmethode.

**5. Empirische Leitplanke im Qualitäts-Gate**
(`.github/workflows/publication-reliability-tests.yml`). Nach dem Suite-Lauf
prüft ein eigener Schritt `git status --porcelain -- data/audit` und wird rot,
wenn auch nur eine Zeile entsteht – mit `if: ${{ !cancelled() }}`, also auch
nach einem fehlgeschlagenen Testlauf, weil die Frage dann am interessantesten
ist. Zusätzlich laufen beide neuen Selbsttests als eigene Schritte. Statische
Regeln allein finden nur bekannte Muster; die Leitplanke findet jeden künftigen.

**6. Governance-Regel C27** (`scripts/governance_contract.py`),
Label **„Beweis-Ledger-Isolation"**. Friert Engpass, Sandbox, Regressionstest
und Leitplanke ein. Der Kontrakt-Selbsttest prüft fünf Kunstbefunde: Umlenkung
entfernt, Schreibpfad fest verdrahtet, Sandbox fehlt, Leitplanke fällt aus dem
Workflow – und als Schein-Sicherheits-Probe der entfernte Rückfall auf
`data/audit`, also eine als Isolation getarnte Abschaltung. `docs/
GOVERNANCE-KONTRAKT.md` ist neu erzeugt, `CLAUDE.md` trägt den Vorgang als
eigenen Abschnitt plus die beiden Selbsttests in der Test-Pipeline.

## Nachweis

```
$ python3 scripts/audit_log.py --selftest
✅ Audit-Log-Selbsttest ok: FFC_AUDIT_DIR lenkt um, FFC_AUDIT_DISABLE schaltet
   stumm, Normalfall schreibt nach data/audit.

$ python3 scripts/repo_isolation.py --selftest
✅ Repo-Isolation-Selbsttest ok: Sandbox lenkt um (auch für Kindprozesse),
   data/audit/ bleibt unberührt, Abweichungen fallen auf.

$ python3 -m unittest discover -s scripts/tests
Ran 1993 tests in …s
OK (skipped=9)                       # 1978 Bestand + 15 neu

$ git status --porcelain -- data/audit
                                     # leer – kein Test schreibt mehr ins Buch

$ python3 scripts/governance_contract.py --selftest
✅ KONTRAKT-SELFTEST bestanden (C1–C27 mit Kunstbefunden: Fehler erkannt,
   gutes Setup bleibt still).

$ python3 scripts/governance_contract.py
🔒 GOVERNANCE-VERTRAG erfüllt – alle 26 Regeln prüfen in beide Richtungen.

$ python3 scripts/automation_premium_audit.py --strict   # unverändert grün
$ python3 scripts/history_guard.py                       # H6 unverändert grün
```

Vorher/Nachher gemessen, nicht behauptet: Vor der Heilung hinterließ derselbe
Suite-Lauf zwei neue Zeilen im versionierten Ledger (dritte latent). Nach der
Heilung ist `data/audit/` Byte für Byte unverändert – geprüft über SHA-256
aller 37 Dateien.

**Ergebnis:** Der Schreibpfad ist am Engpass geschlossen, nicht an drei
Zufallsstellen. Ab jetzt gilt: Ein Testlauf schreibt Audit-Zeilen in einen
Sandkasten, und die Zeile fehlt nicht – sie liegt woanders. Wer einen neuen
Test ohne Sandbox an einen bekannten Einstieg hängt, bekommt denselben Befund
zweimal: einmal mit Datei und Zeile aus der Wache, einmal als roten Lauf aus
der Leitplanke.

**Offen, weil es eine Entscheidung des Besitzers ist:** Die fünf bereits
committeten fabrizierten Zeilen (`data/audit/2026-10-03.jsonl:136` und
`data/audit/2026-10-05.jsonl:2,162,185,187`) stehen weiterhin im Buch. Sie zu
entfernen widerspricht der append-only-Regel H6, die dieses Repo bewusst
aufgestellt hat; `history_guard.py` sagt dazu selbst: *„Bewusste Bereinigung
gehört in einen dokumentierten, eigenen Commit."* Diese Heilung lässt die
Vergangenheit deshalb unberührt und stoppt die Zukunft.
