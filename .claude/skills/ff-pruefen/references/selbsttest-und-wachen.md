# Selbsttest- und Wachen-Vertrag

> Wörtlich aus `CLAUDE.md` übernommen am 01.11.2026 (Skill-Umbau). Kein Satz wurde umformuliert, gekürzt oder erfunden; die Überschriften sind eine Ebene tiefer gehängt. Änderungen hier sind Änderungen am Regelwerk – sie brauchen denselben Nachweis wie vorher: Selbsttest der betroffenen Wache, dann Commit.

### Ein `--selftest` muss das Modul prüfen, dessen Namen er trägt

`scripts/hemingway_check.py` warb mit `--selftest`, reichte die Flagge aber nur
an `readability_check` weiter — und ersetzte in dessen grüner Zeile den
Modulnamen. Das Häkchen lautete `✅ hemingway_check --selftest OK`, geprüft war
davon keine Zeile. Der zugehörige Test bestätigte genau diese gefälschte
Zeichenkette (behoben 03.10.2026).

**Regel für Adapter-Module:** Der Selbsttest prüft die eigenen Versprechen
(Durchreichen, Exit-Codes, Umbenennung, JSON-Unversehrtheit) **und** ruft den
Selbsttest der Engine zusätzlich auf. Er darf die Flagge nie bloß weiterreichen.

**Gegenregel zum Weiterreichen:** Hat die Engine gar kein `--selftest`, startet
ein Aufruf mit der Flagge ihre Standard-Aktion — bei `publish_gate.py` wäre das
der scharfe Lauf, der am 18.09.2026 beinahe einen Live-Artikel auf `draft`
herabstufte. `selftest_runner.GEFAHREN` führt solche Module mit Begründung.

### Eine Wache ist ganz oder gar nicht (DAUERVORGABE, seit WF-6F7F/#783, 16.10.2026)

Am 15.10.2026 hat ein Rebase in PR #776 die Redaktions-Wache halbiert. Die
Commit-Nachricht nennt es selbst: „Faustregel-Konflikte zugunsten der
themenspezifischen Varianten aufgelöst". In `scripts/redaktions_standard.py`
blieben Kopf und 14 eingefrorene Selbsttest-Fälle aus der neueren Fassung
(#766, `FAUSTREGEL_POOL` + Bestandsmessung), der RS3-Rumpf kam aus der
älteren. Die Datei war syntaktisch gültig und in sich widersprüchlich:
`main()` rief fünf Funktionen, die es nicht mehr gab, der Selbsttest las drei
Konstanten, die es nicht mehr gab. Der Selbsttest schlug an (Meldung #783),
das Qualitäts-Gate war ab 15.10. 18:19 rot, der Regressionstest ebenfalls –
und der Heilpfad der Wache war für jeden echten Lauf ein `NameError`: eine
tote Wache, die aussah, als wäre sie da.

- **Niemals zusammensetzen – auch Quelltext nicht.** Die Regel aus
  „Maschinen-Artefakte niemals mergen" (#346) gilt für die Wachen selbst:
  Bei einem Konflikt wird EINE Fassung gewählt
  (`git checkout <rev> -- <pfad>`), nie Kopf von hier, Rumpf von dort.
  `.gitattributes` setzt dafür `merge=binary` auf alle signierten
  `scripts/*.py` (Liste = Signaturliste aus `data/integrity_lock.json`) –
  ein stiller Text-Zusammenschnitt ist damit technisch nicht mehr möglich.
- **Beweis vor dem Commit.** Nach jeder Konflikt-Auflösung läuft der
  Selbsttest der betroffenen Wache: `python3 scripts/<wache>.py --selftest`.
  Rot heißt: Die Fassung stimmt in sich nicht – dann wird nicht committet.
- **Die Wache dafür:** `scripts/wachen_vertrag.py` (W1–W4) liest den Quelltext
  ALLER Skripte, ohne einen davon auszuführen, und meldet: **W1**
  Konfliktmarker (Paar-Regel: ein Docstring-`=======` ist keiner), **W2**
  halbe Aufrufe (`foo(...)` ohne Definition in derselben Datei), **W3** halbe
  Konstanten (GROSSBUCHSTABEN-Name ohne Definition), **W4** Ausnahmen, die
  unbekannt, unbegründet, undatiert oder abgelaufen sind.
  Bedienung: `python3 scripts/wachen_vertrag.py` · `npm run test:wachen` ·
  Report `WACHEN-VERTRAG-REPORT.md` (gitignoriert) · Hintergrund:
  `WF-6F7F-783-DAUERHEILUNG-PREMIUM-2026-10-16.md`.
- **Ausnahmen sind sichtbar und altern.** Dynamische Namensräume
  (`globals()`/`setattr`) gehören nach `data/wachen_vertrag_ausnahmen.yaml` –
  mit `grund` und `seit: JJJJ-MM-TT`. Eine Ausnahme, die keinen Befund mehr
  deckt, wird selbst zum Befund. Einen Konfliktmarker deckt keine Ausnahme.
- **Vertrag statt Vertrauen.** `wachen_vertrag.py` UND
  `redaktions_standard.py` stehen im vertraglichen Minimum (`GUARDS`, C6);
  der Lauf hängt als **C39** im Governance-Vertrag und läuft mit dem
  Qualitäts-Gate (`governance_contract.py --quick`). Regression:
  `scripts/tests/test_wachen_vertrag.py`, `npm run test:redaktion`.
  Die #766-Dauerheilung (`FAUSTREGEL_POOL`, Wähler, Bestandsmessung, keine
  zweite RS3-Implementierung) bleibt unangetastet.

### Skript-Syntax: der liegende Stand muss kompilieren (DAUERVORGABE, seit #864, 25.10.2026)

Am 25.10.2026 stand `scripts/redaktions_standard.py` mit einem
IndentationError auf `main` – entstanden beim **Squash-Merge** von PR #869 auf
eine zwischenzeitlich gewanderte `main` (Kopf und Rumpf derselben Funktion aus
zwei Fassungen). Vier weitere Commits gingen unbemerkt darüber: Die PR-Prüfung
sieht den PR-Stand, die Unit-Tests die importierten Module, der Hugo-Build kein
Python, `bot_preflight.py` nur die Content-Engine. Und der Bot-Watchdog, der
den Fehler sah, **starb an seinem eigenen Selbsttest** – alle Heil- und
Meldestufen des Laufs standen auf `skipped` (Meldung #864).

- **Eine Quelle der Wahrheit:** `scripts/skript_syntax_wache.py` kompiliert
  alle Skripte im Arbeitsbaum (Datei, Zeile, Art, Quellzeile), ohne etwas
  auszuführen und ohne `__pycache__` zu schreiben. Bot-Watchdog (Check 2),
  Push-/PR-Lauf und Heiler fragen sie – niemand formuliert die Regel neu.
- **Prävention:** `.github/workflows/skript-syntax.yml` prüft bei jedem Push
  auf `main` und bei jeder PR. Der gemeinsame Schreibweg
  (`scripts/git_sync.sh`) hat eine **Notbremse**: Kein Commit/Push, dessen
  eigene `.py`-Dateien nicht kompilieren (geprüft werden nur die Dateien
  DIESES Commits – ein Altbefund blockiert keine Automatisierung).
- **Heilung:** `scripts/skript_syntax_heiler.py` stellt die jüngste Fassung
  derselben Datei her, die nachweislich kompiliert. Jede Heilung steht mit
  beiden Commit-Kennungen in `data/skript_syntax_heilungen.jsonl`. Ohne
  heilbaren Vorgänger oder nach zwei Heilungen derselben Datei in 24 h heilt
  er **nicht** – dann ist ein Schreiber defekt und der Befund bleibt offen.
- **Selbsttest ≠ Repo-Stand.** Der Selbsttest einer Wache prüft den DETEKTOR
  (erkennt er Fehler, schweigt er bei gutem Code), nie den Prüfling. Ein
  Selbsttest, der am kaputten Fremdskript scheitert, schaltet den Melder
  genau dann ab, wenn er gebraucht wird. Im Workflow gilt deshalb:
  Messkern (Watchdog + Router) muss laufen – jeder weitere Selbsttest läuft
  einzeln, fehlertolerant, und der rote Lauf entsteht erst in der Bilanz
  NACH Messung, Heilung und Meldung.
- Regression: `scripts/tests/test_skript_syntax_wache.py`,
  `scripts/tests/test_skript_syntax_heiler.py`,
  `scripts/tests/test_bot_watchdog_syntax_sicht.py` · Hintergrund:
  `BOT-WATCHDOG-864-DAUERHEILUNG-PREMIUM-2026-10-25.md`.

### Ein Selbsttest urteilt über den Code, nicht über das Modell (KI-Probe, seit #138, 08.10.2026)

Engine-Lauf **#138** (Run `37694986440`, 07.10.2026 22:15 UTC) starb in Phase
0.5 mit Exit 2 – vor Phase 1, ohne Artikel, ohne Endabnahme. Kein Code war
kaputt: `requeue_quality_holds.py --selftest` rief den Lesbarkeits-Heiler mit
`ki=True` **ohne Attrappe** auf. Lokal und im PR-CI fehlen Schlüssel → grün. In
Phase 0.5 stehen seit WACHE-609 echte GROQ/GEMINI-Schlüssel → das Live-Modell
schrieb den „schlechten“ Fixture-Text gut um (Flesch 2.9 → 86) und der Test
urteilte „Hold unter der Schwelle wird freigegeben“. #136/#137 waren am selben
Tag grün, weil das Modell zufällig schlechter antwortete. Ein Münzwurf im
kritischen Pfad.

- **Regel:** Jeder Selbsttest führt seinen KI-Weg über die vorhandene Attrappe
  (`lesbarkeit_heiler.KI_CALL`, `satz_heiler.KI_CALL`, Modul-`chat` austauschen,
  Netz-Trigger über `schaltwerk_triggers.NETZ_TRIGGER`) und erreicht **nie**
  den echten Transport. „Offline, da kein Key im Selbsttest“ ist eine Annahme,
  keine Garantie – Schritte bekommen Schlüssel nachträglich (genau so entstand
  #138). Muster: `requeue_quality_holds._KiAttrappe` (zählt Aufrufe, stellt
  zurück, prüft stumm / Vertragsbruch / gelungen / gar nicht gefragt).
- **Leitplanke (empirisch):** `scripts/selftest_ki.py --trap-workflows` fährt in
  `publication-reliability-tests.yml` JEDEN Selbsttest, den ein Workflow
  aufruft, mit Attrappen-Schlüsseln (SSOT `data/ki_transportweg.yaml`) und
  gesperrtem Netz (Loopback frei). Jeder Netzversuch wird mit Datei und Zeile
  protokolliert – auch wenn der Aufrufer die Ausnahme schluckt. Stand
  08.10.2026: 98/98 grün.
- **Diagnose:** Phase 0.5 nennt per ERR-Falle den exakten Befehl als
  Annotation; die Engine-Endkontrolle kennt die Klasse **FRÜHABBRUCH** (ein
  Pflichtschritt vor der Endabnahme ist gestorben) statt „Endabnahme ohne
  Exit-Code“.
- Bedienung: `python3 scripts/selftest_ki.py --selftest` ·
  `python3 scripts/selftest_ki.py --trap scripts/<skript>.py` ·
  `python3 scripts/selftest_ki.py --liste` (🔑 = läuft heute schon mit Schlüssel) ·
  `python3 -m unittest scripts.tests.test_selftest_ki`.
  Vorgangsbericht: `CONTENT-ENGINE-138-DAUERHEILUNG-PREMIUM-2026-10-08.md`.

### Beweisen ist nicht Fabrizieren (Beweis-Ledger-Isolation, C27, seit 07.10.2026)

`data/audit/*.jsonl` ist kein Logfile, sondern ein **versioniertes
Beweis-Ledger**: `history_guard.py` bewacht es als append-only (Regel H6), und
jede Zeile behauptet einen echten Betriebsvorgang. Am 07.10.2026 – beim Siegeln
der Auslieferungs-Heilung #610 – fiel auf, dass **drei Unit-Tests echte Zeilen
hineinschrieben**. Die teuerste stand seit dem 03.10.2026 im Buch:

```json
{"module": "publish_gate", "action": "gate",
 "input": {"candidates": ["2026-09-07-r5-live"]},
 "output": {"gated": ["2026-09-07-r5-live"], "demoted": ["2026-09-07-r5-live"]}}
```

Ein am Gate verworfener Live-Artikel, den es nie gab – `2026-09-07-r5-live` ist
eine Test-Fixture. Vier weitere Zeilen bescheinigten `GROQ_API_KEY` einen Erfolg
`via content-engine-v2`, obwohl in CI ausschließlich `pinterest-ai.yml` und
`pinterest-token.yml` `--record-success` aufrufen, und nur für
`PINTEREST_TOKEN_KEY`. Genau die „fremde Erfolgsmeldung", die `secrets_age_guard`
selbst als `declared_foreign` abwertet, stand damit als Beweis im Buch.

- **Die Lehre ist die Schwester von C15:** Dort darf ein Beweislauf nicht
  heilen, was er prüft. Hier darf er nicht behaupten, was nie geschah. Beides
  sind Fälle, in denen die Messung ihre eigene Grundlage verändert.
- **Warum drei Stellen nicht reichen:** `run_gate()` → `publish_gate` →
  **Subprozess** `affiliate_profi_check.py --json`. Ein `mock.patch.object` im
  Testprozess erreicht das Kind nicht. Deshalb liegt der Vertrag in der
  **Umgebung**, die sich in jedes Kind erbt:
  `FFC_AUDIT_DIR` (Ziel umlenken) und `FFC_AUDIT_DISABLE` (harter No-Op).
- **Eine Zeile fehlt nicht, sie liegt woanders:** Die Sandbox schaltet das
  Protokollieren nicht ab. `beweis_ledger_unangetastet()` liefert den Pfad, und
  die Tests lesen die umgelenkte Zeile ausdrücklich zurück – sonst ginge eine
  zu grobe Stummschaltung als Heilung durch (Schein-Sicherheit).
- **Die dritte Leckstelle war latent:** `pg.main()` schreibt den gate-Entscheid
  nur, wenn ein Kandidat scheitert. Greift die R5-Heilung, bleibt `gated` leer.
  Der Pfad ist damit zufallsabhängig – und gerade deshalb nicht durch
  „passiert bei mir nicht" widerlegt. Die committete Zeile vom 03.10.2026 ist
  der Beweis, dass er feuert.
- **Gebrauch in Tests:**
  ```python
  from repo_isolation import beweis_ledger_unangetastet

  with beweis_ledger_unangetastet("bestand_gate"):
      findings, errors = bg.run_gate()
  ```
  Der Block bricht mit AssertionError ab, sobald im echten `data/audit/` eine
  Zeile entsteht, wächst oder verschwindet – der Beweis läuft **nach** dem
  Block, also auch dann, wenn die Prüfung selbst wirft. Das ältere Muster
  `patch.object(audit_log, "log_event")` bleibt gültig.
- **Empirisch statt statisch:** `publication-reliability-tests.yml` prüft nach
  dem Suite-Lauf `git status --porcelain -- data/audit` und wird rot, wenn auch
  nur eine Zeile entsteht – auch nach einem fehlgeschlagenen Testlauf
  (`if: !cancelled()`). Eine statische Regel allein würde nur bekannte Muster
  finden; die Leitplanke findet jeden künftigen.
- **Vertrag:** Regel **C27** in `governance_contract.py` friert Engpass,
  Sandbox, Regressionstest und Leitplanke ein; sabotierte Fassungen werden im
  Kontrakt-Selbsttest rot. Die Wache in
  `test_audit_ledger_isolation.py` meldet zusätzlich jeden Test, der einen
  bekannten Einstieg (`bestand_gate.run_gate`, `secrets_age_guard
  ._record_success`, `publish_gate.main`, `audit_log.log_event`) ohne Sandbox
  aufruft – mit Datei und Zeile.
- Bedienung: `python3 scripts/audit_log.py --selftest` ·
  `python3 scripts/repo_isolation.py --selftest` ·
  `python3 -m unittest scripts.tests.test_audit_ledger_isolation`.
  Vorgangsbericht: `BEWEIS-LEDGER-ISOLATION-C27-DAUERHEILUNG-PREMIUM-2026-10-07.md`.
