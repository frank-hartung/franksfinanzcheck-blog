# Bot-Watchdog #864 · Dauerheilung: Die Wache blendete sich an ihrem eigenen Befund

- **Stand:** 25.10.2026 · **Issue:** [#864](https://github.com/frank-hartung/franksfinanzcheck-blog/issues/864)
- **Roter Lauf:** [`40209952539`](https://github.com/frank-hartung/franksfinanzcheck-blog/actions/runs/40209952539) (25.10.2026, 16:04:44 UTC, Kopf `a4c99c16`) · Job `watchdog`, Schritt „Selftest (Wache muss sehen können)", Exit 2
- **Befund im Ticket:** P1 · Skript-Syntaxfehler · `Sorry: IndentationError: unexpected indent (redaktions_standard.py, line 424)`

## 1. Kurzbefund

Der gemeldete Syntaxfehler war **echt** – und er war bereits behoben, als
das Ticket gelesen wurde. Was blieb, war die Ursache dahinter: Ein
einziger fremder Syntaxfehler nahm dem Watchdog-Lauf die Stimme. Der
Schritt „Selftest (Wache muss sehen können)" starb, und damit standen
**alle** folgenden Schritte als `skipped` im Lauf – Nachmessung,
Reserve-Heilung, Routing-Zustand, Deploy-Catchup. Ein Melder, der beim
ersten Befund die Augen schließt, ist kein Melder.

Der Befund entstand nicht beim Schreiben, sondern beim **Zusammenführen**:
Der Squash-Merge von PR [#869](https://github.com/frank-hartung/franksfinanzcheck-blog/pull/869)
(`77f9bef9`) traf eine zwischenzeitlich gewanderte `main`; Kopf und Rumpf
derselben Funktion kamen aus zwei Fassungen. In
`scripts/redaktions_standard.py` blieben ein doppelter `if`-Block und zwei
verwaiste Fortsetzungszeilen stehen.

Vier Commits gingen danach unbemerkt über diesen Stand – und **keine Stelle
im Repo kompilierte den liegenden Stand**:

| Prüfung | Sieht … | Fazit für #864 |
|---|---|---|
| PR-Prüfung (`regression`) | den PR-Stand, nicht das Merge-Ergebnis | traf den Fehler nicht |
| Unit-Tests | die Module, die sie importieren | erst nach dem Merge betroffen |
| Hugo-Build | HTML, kein Python | blind für diese Klasse |
| `bot_preflight.py` | alle Skripte | läuft nur in der Content-Engine |
| Bot-Watchdog (Check 2) | den Fehler **korrekt** | aber der Selbsttest tötete den Lauf davor |

Belegt ist der Ablauf an der Geschichte selbst: `77f9bef9` (PR #869)
hinterlässt `redaktions_standard.py` mit `IndentationError` in Zeile 424;
die Fassung kompiliert erst wieder in `bfab36e1` (PR #872, „Squash-
Fusionsschaden von #869 heilen") und `d8c3ec94`. Der rote Watchdog-Lauf
`40209952539` lief auf `a4c99c16` – mitten in diesem Fenster.

**Nachgestellt, nicht behauptet:** Auf dem Stand von `a4c99c16` endet
`python3 scripts/bot_watchdog.py --selftest` mit **Exit 2** und der Zeile
`check_syntax meldet Fehler im eigenen Repo: Sorry: IndentationError …
(redaktions_standard.py, line 424)` – genau die Ausgabe aus dem Ticket.

## 2. Dauerhafte Korrektur (vier Schichten)

### 2.1 Prävention – der liegende Stand wird kompiliert

- **Neu: `scripts/skript_syntax_wache.py`** – die eine Quelle der Wahrheit
  für „Python im Repo ist gültig". Sie liest alle Skripte, wie sie im
  Arbeitsbaum liegen, und kompiliert sie im Speicher (kein `__pycache__`,
  keine Ausführung, kein Netz). Der Befund nennt **Datei, Zeile, Fehlerart
  und Quellzeile** statt „Sorry: … (line 424)". 523 Dateien in unter einer
  Sekunde.
- **Neu: `.github/workflows/skript-syntax.yml`** – Push auf `main`, jede PR,
  auf Zuruf; fail-closed, ohne Abhängigkeiten außer Python. Genau die
  Prüfung, die am 25.10. fehlte.
- **`scripts/git_sync.sh` hat eine Notbremse (#864)** – der gemeinsame
  Schreibweg aller Bot-Workflows committet und pusht kein Skript, das nicht
  kompiliert. Geprüft werden **nur die `.py`-Dateien dieses Commits** (vor
  dem Commit: gestagete Dateien; bei `--push-only`: der Unterschied zu
  `origin/$BRANCH`). Ein Altbefund auf `main` blockiert damit keinen Lauf –
  er heilt sich, statt die Automatisierung anzuhalten.

### 2.2 Sichtbarkeit – Befund ≠ Werkzeugfehler

- `bot_watchdog.py` prüft in seinem Selbsttest jetzt **den Detektor**, nicht
  den Prüfling: Erkennt er einen absichtlich kaputten Text mit der richtigen
  Zeile? Schweigt er bei gutem Code? Der Repo-Stand wird dort **nicht mehr
  bewertet** – er ist Sache von Check 2.
- Der Workflow-Schritt „Selftest (Wache muss sehen können)" prüft zuerst den
  **Messkern** (`bot_watchdog.py` + `alert_router.py`); ohne ihn ist keine
  Aussage möglich, dann bricht der Lauf sofort ab. Jeder weitere Selbsttest
  läuft **einzeln und fehlertolerant**; Fehler erscheinen als `::error::` im
  Log.
- Der rote Lauf entsteht in einem **eigenen Bilanz-Schritt nach dem
  Alarm-Routing** (`if: always()`). Ein Werkzeugfehler bleibt also sichtbar
  (C2: eine ausgefallene Messung ist kein Grün) – aber erst, nachdem
  gemessen, geheilt und gemeldet wurde.

### 2.3 Heilung – der Befund `auto` hat jetzt einen Heiler

- **Neu: `scripts/skript_syntax_heiler.py`** – stellt die **jüngste Fassung
  derselben Datei** her, die nachweislich kompiliert. Nichts anderes: keine
  andere Datei, kein Raten, kein Fremdbereich (`scripts/**` und nur `.py`).
- Jede Heilung steht mit **beiden** Commit-Kennungen (verworfen /
  wiederhergestellt) in `data/skript_syntax_heilungen.jsonl` (append-only,
  versioniert). Die verworfene Absicht ist damit nachweisbar, nicht weg.
- Sicherungen, jede im Selbsttest gegen ein echtes Wegwerf-Repository
  geprüft: kein Heilweg ohne kompilierenden Vorgänger · kein Überschreiben
  lokaler Änderungen · **Wiederholungsbremse** (zwei Heilungen derselben
  Datei in 24 h, danach bleibt der Befund offen – dann ist ein Schreiber
  defekt, und ein Heiler, der im Kreis heilt, verdeckt das nur) · höchstens
  fünf Dateien je Lauf · atomar (`os.replace`) und mit Nachprüfung.
- Der nächste Schritt im Ticket nennt jetzt den Heiler statt einer
  Arbeitsanweisung an einen Menschen.
- **Takt:** Der Heilschritt läuft in beiden Takten. Das ist eine eng
  begrenzte Ausnahme von „der Ausfall-Takt ist read-only" (#676): Check 2
  gehört zur Ausfall-Klasse, also muss der Takt den Befund auch heilen
  dürfen – sonst misst er stündlich etwas, das er per Konstruktion nicht
  anfassen darf. Begrenzt wird sie durch den Heiler selbst.

### 2.4 Verdrahtung und Gedächtnis

- Beide neuen Skripte stehen im **vertraglichen Minimum** (`GUARDS`, C6) –
  ihr Selbsttest läuft mit `governance_contract.py --quick`, also auf jedem
  Push und jeder PR. Eine Wache, die niemand verlangt, führt irgendwann
  niemand aus.
- `CLAUDE.md` trägt die Dauerregel („Skript-Syntax: der liegende Stand muss
  kompilieren") samt Befehlen und der Lehre „Selbsttest ≠ Repo-Stand".
- Regressionstests:
  `test_skript_syntax_wache.py` (Detektor, Zeile, Quellzeile, kein
  `__pycache__`, Selbsttest bewertet nicht den Repo-Stand),
  `test_skript_syntax_heiler.py` (Vorgängerwahl, dry-run, Ledger,
  Idempotenz, Wiederholungsbremse, kein Vorgänger, Heilbereich),
  `test_bot_watchdog_syntax_sicht.py` (der Kernfall: fremder Syntaxfehler
  kippt den Selbsttest nicht; blinder Detektor kippt ihn; Befund nennt
  Datei, Zeile und Heilweg; Verdrahtung von Workflow, Push-Lauf und
  Notbremse).

## 3. Verifikation

Vorher am echten Stand nachgestellt, nachher am selben Stand geprüft:

| Probe | Vorher (`a4c99c16`) | Nachher |
|---|---|---|
| `bot_watchdog.py --selftest` bei kaputtem Fremdskript | **Exit 2** – Lauf stirbt vor der Messung | **Exit 0** – Lauf misst weiter |
| `check_syntax()` | `Sorry: IndentationError … (line 424)` | `scripts/redaktions_standard.py:424: IndentationError: unexpected indent` (plus Herkunfts-Commit) |
| `--emit-env` | Schritt `skipped` | `CHECK2=FAIL` + P1-Befund mit Heilweg |
| Heilung am historischen Blob (`77f9bef9`) | es gab keinen Heiler | Datei wiederhergestellt, Ledger-Zeile geschrieben, `--check` grün |

Läufe und Prüfungen nach der Änderung:

- `python3 -m unittest discover -s scripts/tests`: **3782 Tests grün**,
  28 übersprungen, 0 Fehler.
- `python3 scripts/governance_contract.py --quick`: **42 Regeln** erfüllt
  (C6 mit beiden neuen Skripten).
- `python3 scripts/wachen_vertrag.py`: **331 Skripte, 0 Funde**.
- `python3 scripts/automation_premium_audit.py --strict`: 90 Workflows,
  0 ohne Commit-SHA, 0 ohne Timeout, 0 ohne explizite Permissions.
- `python3 scripts/integrity_guard.py --check`: Kern unverändert – die
  geänderten Dateien stehen nicht im Siegel (keine Signatur nötig).
- `skript_syntax_wache.py --selftest` / `skript_syntax_heiler.py --selftest`:
  grün (Detektor- und Heilungsproben inklusive Sabotagefällen).
- `git_sync.sh`-Notbremse in einem Wegwerf-Repository live geprobt:
  kaputtes gestagetes Skript → **kein Commit, kein Push** (Exit 1, Index
  geleert, Arbeitsbaum unverändert); gutes Skript → Commit und Push grün;
  `--push-only` mit kaputtem Skript im Commit → **kein Push**.
- `git diff --check`: grün.

Ein Hugo-Produktionsbuild war lokal nicht ausführbar (Hugo-Binary fehlt in
der Sandbox); die Änderungen berühren weder Templates noch Inhalte, und der
Workflow-YAML-Vertrag (`test_workflow_yaml.py`, inkl. Actions-Pinning und
Step-Schlüssel) ist Teil der grünen Suite.

## 4. Was diese Heilung nicht tut

- **Keine Schwellen gelockert.** Die Wache prüft strenger als vorher (alle
  Skripte, Datei und Zeile, fail-closed im Push-Lauf).
- **Kein stiller Rollback.** Der Heiler fasst ausschließlich `scripts/**/*.py`
  an, nur mit belegtem Vorgänger, und protokolliert beide Fassungen. Bei
  Wiederholung heilt er **nicht** weiter, sondern lässt den Befund stehen.
- **Keine erfundene Zustimmung.** Der Befund bleibt ein P1 mit Ticket und
  Schließpfad; er verschwindet erst, wenn die Messung ihn nicht mehr sieht.

## 5. Pull-Request

`Closes #864`. Der Abschlussvermerk an der Meldung entsteht über
`.github/workflows/vorgangs-abschluss.yml`; das Automations-Ticket schließt
sich zusätzlich selbst, sobald der nächste Watchdog-Lauf `CHECK2=OK` misst.

*Hintergrund: `scripts/skript_syntax_wache.py`,
`scripts/skript_syntax_heiler.py`, `.github/workflows/skript-syntax.yml`,
`scripts/git_sync.sh` (Notbremse), `scripts/bot_watchdog.py` (Selbsttest und
Check 2), `.github/workflows/bot-watchdog.yml` (Selbsttest, Heilung,
Bilanz), `scripts/governance_contract.py` (GUARDS), `CLAUDE.md`.*
