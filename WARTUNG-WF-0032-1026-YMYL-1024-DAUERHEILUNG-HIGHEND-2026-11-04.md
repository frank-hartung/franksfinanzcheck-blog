# Wartung · Technik + Redaktion · Vorgang WF-0032 (#1026) und YMYL-Belegkette (#1024) — Highend-Dauerheilung, 04.11.2026

**Auftrag:** `fix(wartung): Web-Vitals-Messung (#1026) und YMYL-Belegkettenspiegel (#1024) dauerhaft heilen — #1052 · Bitte dauerhaft auf Highend-Level einer Profi-Agentur beheben.`
**Datum:** 04.11.2026 · **Branch:** `arena/910a362f-franksfinanzcheck-blog` · **Basis:** `038b04f` (`main`)
**Betroffene Vorgänge:** WF-0032 / [#1026](https://github.com/frank-hartung/franksfinanzcheck-blog/issues/1026) · YMYL-Prüfqueue / [#1024](https://github.com/frank-hartung/franksfinanzcheck-blog/issues/1024) · Sammelvorgang [#1052](https://github.com/frank-hartung/franksfinanzcheck-blog/pull/1052)
**Rote Läufe:** `41456548199` (Web-Vitals) · `41454120377` (Redaktionelle YMYL-Prüfung)

---

## 1. Kurzfassung

Beide Vorfälle haben dieselbe Gestalt: **Die Logik war richtig, der Rahmen war falsch.** Es waren keine Sachfehler in der Messung und keine toten Quellen – es waren Ordnungsfehler, die einen Programmierfehler wie ein Messergebnis aussehen ließen.

1. **#1026 (Web-Vitals):** `scripts/lighthouse_live.mjs` importierte `lighthouse` und `playwright-core` **am Modulkopf**. Der Wochenlauf prüfte das Skript aber **vor `npm ci`** – Node bricht einen Import mit fehlendem Paket ab, *bevor* eine Zeile Prüflogik läuft (`ERR_MODULE_NOT_FOUND`). Eine unverbindliche Labordiagnose nahm damit die verbindliche Feldmessung mit ins Rot, und die Fehlermeldung sprach von einem kaputten Selbsttest, der nie Gelegenheit hatte, etwas zu prüfen.
2. **#1024 (YMYL):** `sicherer_abruf()` liefert ein **3-Tupel** `(status, kopf, roh)`. `abruf_gii_spiegel_http()` entpackte es als 2-Tupel (`ValueError: too many values to unpack`), und ein `except Exception:` verkaufte diesen **Programmierfehler** als „Quelle unklar“. Alle vier Bundesrechts-Zitate standen dauerhaft als unprüfbar in der Queue, `--require-complete` blockierte das Schließen des Tickets – und die Meldung behauptete, das Netz sei schuld.

Dazu kamen fünf kleinere, aber wirksame Mängel, die im Rahmen der Ursachenkette mitgeheilt sind (Feldmessung ohne Retry, Schlüssel potenziell in Fehlertexten, `--json` mit Fortschritt auf `stdout`, `continue-on-error` über gate-relevanten Schritten, Spiegel-Schlüssel als stilles Wissen im Code).

Die Heilung ist überall **Struktur, nicht Disziplin**: Ein Import, der nicht existieren *darf*, wird von einem Regressionstest verboten; ein Netzfehler ist eine abgeschlossene Liste; ein Exit-Code, der gebraucht wird, wird erfasst statt verschluckt. **101 automatisierte Prüfungen** halten das fest: 26 Node-Fälle, 75 Python-Fälle (26 Belegketten · 29 Feldmessung · 20 Strukturverträge) und drei Selbsttests mit 18 · 22 · 44 Einzelproben – Details in §5.

---

## 2. Forensischer Ist-Befund

### 2.1 #1026 — der rote Lauf `41456548199`

- Workflow `Web-Vitals-Feldmessung (wöchentlich)`, Job `Felddaten (CrUX) + Labor (Lighthouse)`, gerissener Schritt: **„Selbsttests der Messungen (ohne Netz)“**.
- Reproduktion im nackten Checkout (`node_modules` fehlt):

  ```text
  $ node --test scripts/tests/lighthouse_live.test.mjs
  Error [ERR_MODULE_NOT_FOUND]: Cannot find package 'lighthouse'
      imported from scripts/lighthouse_live.mjs
  ```

- Der Schritt stand **vor** `npm ci`. Damit war der Selbsttest nicht „rot wegen eines Fehlers“, sondern **gar nicht gelaufen** – die Meldung diagnostizierte das falsche Ding.
- Zweiter Befund derselben Kette: `continue-on-error: true` über den Mess-Schritten, mit `set -uo pipefail` und `echo "exit=$?"` – der Exit-Code des `set`-Aufrufs, nicht der Messung. Unter `bash -e` kam der Zweig nie an. Ein leeres `$GITHUB_OUTPUT` fiel im Urteil in den `*`-Zweig und meldete „fail-closed“ – richtig im Ergebnis, falsch im Weg dorthin (es hätte auch ein `0` verschlucken können).
- Dritter Befund: `node scripts/lighthouse_live.mjs --json` schrieb Fortschrittszeilen (`✅ /cockpit/ {...}`) **und** das JSON auf `stdout`. Jeder Aufrufer wäre am ersten `JSON.parse` gescheitert, ohne den Grund zu sehen.

### 2.2 #1024 — der rote Lauf `41454120377`

- Workflow `Redaktionelle YMYL-Prüfung`, Job `belegketten`, Bericht: `4× UNKLAR`, alle auf `gesetze-im-internet.de` (`vvg_2008/__40.html`, `vvg_2008/__96.html`, `bgb/__502.html`, `got_2022/`), jeweils „nicht erreichbar (URLError)“.
- Widerspruch: dieselben vier Zitate sind über den täglichen Spiegel `Gesetze-fuer-KI/bundesrecht` nachweislich vorhanden (live geprüft am 04.11.2026: `vv/vvg_2008.md` 246 KB, `bg/bgb.md` 1,76 MB, `go/got_2022.md`; alle mit `quelle:`-Kopf auf `gesetze-im-internet.de`).
- Ursache: Der Ausweichweg **konnte nicht greifen**. Die Funktion entpackte den 3-Tupel-Vertrag von `net_safety.sicherer_abruf()` als 2-Tupel. Der `ValueError` wurde von `except Exception:` gefangen und als „unklar“ ausgegeben – der Ausweichweg meldete also den Fehler, den er verhindern sollte.
- Warum es niemandem auffiel: `belegketten_wache.py` stand **nicht** in `GUARDS` (`scripts/governance_contract.py`, Regel C6). Ihr Selbsttest lief in keinem Gate.

---

## 3. Ursachenkette (fünf Schichten, nicht eine)

| # | Schicht | Fehler | Warum es niemand sah |
|---|---|---|---|
| 1 | **Reihenfolge** | Selbsttest vor `npm ci`, aber mit Fremdimporten | Der Schritt hieß „ohne Netz“ – Paketbedarf stand nirgends |
| 2 | **Fehlerklasse** | `except Exception:` im Abrufpfad | Ein Programmierfehler sieht wie ein Netzbefund aus |
| 3 | **Vertrag** | 3-Tupel als 2-Tupel entpackt | Die Signatur war korrekt dokumentiert – nur nicht benutzt |
| 4 | **Sichtbarkeit** | Exit-Code über `continue-on-error` verloren | Der Lauf war rot, aber die Ursache stand im falschen Schritt |
| 5 | **Governance** | Belegketten-Wache nicht in `GUARDS` | Ein Selbsttest ohne Lauf ist Prosa |

Jede Schicht einzeln hätte den Vorfall verhindert. Genau deshalb ist die Heilung nicht „den einen Fehler beheben“, sondern jede Schicht einzeln schließen – und die Schließung prüfbar machen.

---

## 4. Dauerheilung

### 4.1 #1026 — `scripts/lighthouse_live.mjs`

- **Modulkopf nur noch Node-Bordmittel** (`node:fs`, `node:net`, `node:path`, `node:url`). Importieren ist damit immer möglich – auch in einem nackten Checkout.
- **`ladeLaufzeit()`** lädt `lighthouse`, `playwright-core` und `e2e/browser.mjs` erst beim echten Lauf; Fehler werden zu `LaufzeitFehler` mit Klartext und Abhilfe (`npm ci --ignore-scripts && npm run browser:setup`). Die Ladefunktion ist injizierbar, damit der Fehlerweg ohne Paketinstallation prüfbar ist.
- **`--selftest`** (neu) prüft die gesamte Bewertungslogik offline: Schwellen, Messwert-Leser, Alias `dom-size`, alle drei Aggregationsmethoden, gerissene und gehaltene Grenzen, `NICHT_GEMESSEN`, CLI-Validierung, Berichtsform, Laufzeitfehler-Klasse und den Messweg – 27 Prüfungen, ohne Netz, ohne Browser, ohne `node_modules`.
- **`--json` schreibt ausschließlich JSON auf `stdout`**; Fortschritt und Warnungen gehen immer nach `stderr`.
- **`messeUrl()`** nimmt eine injizierbare Messfunktion; `erzeugeMesser()`, `messOptionen()`, `anzeigepfad()` sind benannte, prüfbare Einheiten statt Inline-Code.
- **CLI-Härtung**: fehlender Wert nach `--url`/`--basis`/`--laeufe`, Nicht-Zahl, unsinnige Basis-URL und unbekannte Argumente ergeben Klartext + Exit 2 – kein stiller Lauf mit falschen Zielen.

### 4.2 #1026 — `scripts/cwv_feld_wache.py`

- **Transienten-Retry**: 408/425/429/5xx und reine Netzabbrüche werden bis zu dreimal wiederholt, `Retry-After` bis 30 s respektiert, danach exponentielles Backoff. Ein 404 wird **nicht** wiederholt (er wiederholt sich nicht – er kostet nur Zeit).
- **`schwaerze()`**: eine Stelle, durch die jeder Text läuft, der das Haus verlässt (Bericht, JSON, `stderr`). Der Schlüssel reist als `&key=…` und taucht in keinem Artefakt auf – auch nicht in fremden Ausnahmetexten.
- **Störungen werden benannt**: Pfad, Fehlerklasse und geschwärzter Grund. Eine leere Störungsliste ist eine Aussage, kein Zufall.
- Hausregel C2 bleibt unangetastet: fehlendes CrUX ist `STOERUNG`, niemals `GUT`.

### 4.3 #1024 — `scripts/belegketten_wache.py`

- **`NETZ_AUSNAHMEN`** als abgeschlossene Liste (`URLError`, `HTTPError`, `HTTPException`, `TimeoutError`, `ConnectionError`, `SSLError`, `OSError`). Nur sie darf „unklar“ erzeugen. `ValueError`, `TypeError`, `AttributeError`, `KeyError` schlagen mit Exit 2 durch – **der Vorfall kann sich nicht wiederholen, ohne dass der Lauf hart abbricht.**
- **3-Tupel-Vertrag an genau einer Stelle** (`_spiegel_abruf`), benannt und kommentiert. Der Selbsttest prüft ihn gegen eine Attrappe mit dem *echten* Rückgabevertrag.
- **Zweistufiger Abruf**: `raw.githubusercontent.com` zuerst (ein Versuch), `api.github.com` mit `Accept: application/vnd.github.raw` als Rückfall – dieser Weg liefert auch `bg/bgb.md` (1,7 MB) vollständig und nimmt den Token für das Kontingent an. Ein 403/429 auf dem Rohweg ist ein **Kontingent**-Signal, ein 404 eine endgültige Auskunft (kein Rückfall, keine Wiederholung).
- **`GH_TOKEN` geht ausschließlich an `api.github.com`** – ein Bearer-Token auf dem Rohweg wäre ein Geheimnis auf einem Weg, der es nicht braucht.
- **Ablageordnung als Funktion** (`_gii_shard`): `vvg_2008` → `vv/`, `bgb` → `bg/`, `got_2022` → `go/`, `estg` → `es/`, Ziffernkennungen → `0-9`. Vorher stand dieselbe Regel als stilles Wissen im Code.
- **`--probe-bundesrecht`** (neu): Live-Nachweis des Messwegs für die vier echten Zitate aus #1024. Kein Gate (braucht Netz), aber ein Betriebssignal.
- **`belegketten()`** fängt nur noch Datei-/Formatfehler auf (`OSError`, `ValueError`, `YAMLError`, `KeyError`, `TypeError`) – ein Defekt in `load_article` ist ein Werkzeugfehler, kein Datenbefund.

### 4.4 Workflows

**`.github/workflows/web-vitals-woche.yml`**

- `actions/setup-node` **vor jedem** Node-Aufruf.
- Selbsttest-Schritt **vor** `npm ci`, mit beiden Werkzeugen und einem ausdrücklichen Beweis der Paketfreiheit (`[ -d node_modules ]` → Warnung, wenn doch vorhanden).
- Kein `continue-on-error` über gate-relevanten Schritten. `rc=0; … || rc=$?` → `$GITHUB_OUTPUT`, Schritt bleibt grün (Diagnose), das **Urteil am Ende** entscheidet.
- `feld-bericht.md`/`feld-fehler.txt`/`labor-bericht.md`/`labor-fehler.txt` in der Lauf-Zusammenfassung **und** im Artefakt.
- Der Jobname `Felddaten (CrUX) + Labor (Lighthouse)` bleibt unverändert – `alert_resolve_gate.py` schließt Meldungen nur, wenn der *genannte* Job im auflösenden Lauf grün ist. Ein umbenannter Job wäre ein Dauer-Alarm.

**`.github/workflows/redaktionelle-ymyl-pruefung.yml`**

- Eigener Selbsttest-Schritt **vor** der Messung.
- `GH_TOKEN` für das Spiegel-Kontingent; `persist-credentials: false` in beiden Jobs.
- Exit-Code-Erfassung statt `continue-on-error`.
- **Neuer Gate-Schritt „Werkzeug-Integrität der Belegketten-Wache“**: `0|1` = Urteil, alles andere = Werkzeugfehler → hartes Rot mit Heilweg im Klartext.
- **Neuer Schritt „Bundesrechts-Spiegel live prüfen“** (`--probe-bundesrecht`, `continue-on-error: true`, `always()`): der Messweg wird bewiesen, nicht geglaubt.
- **Ticket-Regel unterscheidet drei Zustände**: grün / Quellenbefund / Werkzeugfehler. Fehlt der Exit-Code (Job davor abgebrochen), gilt nichts als grün – fail-closed.

### 4.5 Governance

- `belegketten_wache.py` steht jetzt in `GUARDS` (`scripts/governance_contract.py`), Regel **C6**: Ihr Selbsttest läuft im vertraglichen Minimum. Ein Gate, das niemand verlangt, führt irgendwann niemand aus.
- `package.json`: `test:webvitals` fährt jetzt auch `--selftest`; neu ist `test:ymyl`.
- Runbooks: `docs/ANLEITUNG-WEB-VITALS.md` (Abschnitt „Wenn die Feldmessung selbst rot ist“ + „Warum `--selftest` vor `npm ci` läuft“) und `docs/ANLEITUNG-REDAKTIONELLE-YMYL-PRUEFUNG.md` (Abschnitt „Exit 1 oder Exit 2“).

---

## 5. Verifikation

Alle Angaben auf diesem Stand, offline, in einem Checkout **ohne** `node_modules`:

| Prüfung | Befehl | Ergebnis |
|---|---|---|
| Laborwerkzeug, 26 Fälle | `node --test scripts/tests/lighthouse_live.test.mjs` | ✅ 26/26 |
| Laborwerkzeug, Selbsttest | `node scripts/lighthouse_live.mjs --selftest` | ✅ 18 Prüfungen (gezählt) |
| Feldmessung, Selbsttest | `python3 scripts/cwv_feld_wache.py --selftest` | ✅ grün |
| Feldmessung, 29 Fälle | `python3 -m unittest scripts.tests.test_cwv_feld_wache` | ✅ 29/29 (21 alte + 8 neue) |
| Belegketten, Selbsttest | `python3 scripts/belegketten_wache.py --selftest` | ✅ bestanden |
| Belegketten, 26 Fälle | `python3 -m unittest scripts.tests.test_belegketten_wache` | ✅ 26/26 (15 alte + 11 neue) |
| **Strukturvertrag beider Vorfälle** | `python3 -m unittest scripts.tests.test_wartung_kette_1024_1026` | ✅ 20/20 |
| URL-Wache (Alert #83) | `python3 scripts/url_substring_guard.py` | ✅ 1308 Dateien, 0 Funde |
| Klartext-Wache (Alert #77/78) | `python3 scripts/clear_text_logging_guard.py` | ✅ 717 Dateien, 0 Hauscode-Funde |
| ReDoS-Wache (Alert #87) | `python3 scripts/redos_guard.py` | ✅ 717 Dateien, 0 Funde |
| Skript-Syntax | `python3 scripts/skript_syntax_wache.py --check` | ✅ 633 Dateien |
| Governance-Vertrag | `python3 scripts/governance_contract.py --quick` | ✅ 45 Regeln |
| Workflow-Vertrag | `python3 scripts/workflow_vertrag_wache.py --gate` | ✅ 98 Workflows |
| Trigger-Wache | `python3 scripts/trigger_wache.py --check` | ✅ 98 Workflows, 0 Befunde |
| Integritäts-Siegel | `python3 scripts/integrity_guard.py --gate` | ✅ 55 Kerndateien |
| Artefakt-Wächter | `python3 scripts/artefakt_waechter.py` | ✅ 564 Artefakte |
| Report-Hygiene | `python3 scripts/report_hygiene.py --check` | ✅ Root sortenrein |
| Skill-Vertrag | `python3 scripts/skills_vertrag.py` | ✅ 90 Skills, K1–K8 |

### 5.1 Der Selbsttest fängt den *Ursprungsfehler*, nicht nur seinen Schatten

Drei Proben bewegen sich bewusst auf dem Originalpfad:

1. `test_sicherer_abruf_3_tupel_wird_korrekt_entpackt` setzt eine Attrappe in `net_safety.sicherer_abruf`, die **wirklich** `(status, kopf, roh)` zurückgibt. Ein Rückfall auf das 2-Tupel-Entpacken macht diesen Test rot – nicht einen entfernten Verwandten.
2. `test_programmierfehler_ist_kein_quellenbefund` wirft genau den `ValueError("too many values to unpack (expected 2)")` aus dem Vorfall und verlangt, dass er **durchschlägt** – im Direktabruf *und* im Spiegelweg.
3. `test_lighthouse_live_hat_keinen_fremdimport_am_modulkopf` liest den Modulkopf und verbietet jedes `import … from 'lighthouse'`/`'playwright-core'`/`'../e2e/browser.mjs'`. Der Node-Test `Der Modulkopf verkauft keine Laufzeitpakete als Voraussetzung` prüft zusätzlich, dass **nur** `node:`- und relative Importe dort stehen.

### 5.2 Was bewusst **nicht** geprüft wird (und warum)

- **Kein Netz im Selbsttest.** CrUX, PSI, `gesetze-im-internet.de` und `api.github.com` sind im Selbsttest tabu – ein Selbsttest, der am Netz hängt, ist bei Netzausfall blind genau dann, wenn er gebraucht wird. Die Netzgrenze steht als ausdrücklicher Test (`test_selbsttest_beruehrt_das_netz_nicht`, `tripwire` auf `urlopen`).
- **Die Live-Probe ist kein Gate.** `--probe-bundesrecht` braucht Netz und ist damit nicht reproduzierbar. Sie läuft im Workflow mit `continue-on-error: true` und schreibt ihren Befund in die Zusammenfassung. Ein dauerhaft roter Probebefund ist ein Betriebssignal – kein Quellen-Urteil.
- **Die Lageräume der Runner bleiben ungeprüft.** Dass `www.gesetze-im-internet.de` GitHub-Runner abweist, ist am 30.10.2026 belegt und der Grund für den Spiegel; hier wird nicht erneut versucht, das Gegenteil zu beweisen.

---

## 6. Was ausdrücklich **nicht** geändert wurde

- **Keine Schwelle gesenkt.** `lighthouse/assertions.json` bleibt erzeugte Wahrheit aus `data/design/regelwerk.yaml`.
- **Kein Scheingrün.** Fehlende CrUX-Daten bleiben `STOERUNG`; ein `UNGEPRÜFT` wird nirgends zu `GUT`.
- **Keine Unterdrückung.** Kein `# codeql[...]`, kein Dismiss, keine Whitelist – die drei betroffenen Wachen heilen im Code.
- **Keine neue Abhängigkeit.** Alles läuft mit Bordmitteln (Node) und dem vorhandenen `net_safety`/`url_host`-Bestand.
- **Keine stille Verhaltensänderung am Alarm.** Der Jobname bleibt, die `alert-key`-Identität bleibt, die Ticket-Regel bleibt fail-closed.

---

## 7. Restrisiko und Schließpfad

| Restrisiko | Wirkung | Schließpfad |
|---|---|---|
| Der Spiegel `Gesetze-fuer-KI/bundesrecht` ändert seine Ablageordnung | Zitate bleiben `unklar` (fail-closed, **kein** Fehlalarm „tot“) | `--probe-bundesrecht` wird rot → `_gii_shard` in einer Stelle korrigieren |
| `api.github.com` drosselt trotz Token | Zitate bleiben `unklar` | Kontingent prüfen; die Wache wiederholt bewusst **nicht** (429 ist transient, aber ein Retry verbraucht mehr) |
| CrUX kennt eine Seite nicht (zu wenig Traffic) | `UNGEPRÜFT`, Lauf bleibt grün | korrekt und gewollt; neue Seite mit Traffic abwarten |
| Ein künftiger statischer Import in `lighthouse_live.mjs` | `npm run test:webvitals` und der CI-Strukturvertrag werden rot | Import in `ladeLaufzeit()` verschieben |
| Ein künftiges `except Exception` im Abrufpfad | `test_wartung_kette_1024_1026` wird rot (AST-Prüfung) | `NETZ_AUSNAHMEN` verwenden |

**Schließen der Tickets:** #1026 schließt der nächste grüne Lauf von `web-vitals-woche.yml` auf `main`, #1024 der nächste grüne Lauf von `redaktionelle-ymyl-pruefung.yml` – beide mit echtem Live-Job-Beweis, nicht durch diesen PR. Der Sammelvorgang #1052 schließt mit dem Merge.

---

## 8. Geänderte Dateien

| Datei | Art |
|---|---|
| `scripts/lighthouse_live.mjs` | Dauerheilung (#1026): Laufzeitimport, `--selftest`, `stdout`/`stderr`-Trennung, CLI-Härtung |
| `scripts/cwv_feld_wache.py` | Härtung: Retry, Schwärzung, benannte Störungen |
| `scripts/belegketten_wache.py` | Dauerheilung (#1024): 3-Tupel-Vertrag, `NETZ_AUSNAHMEN`, zweistufiger Spiegel, `--probe-bundesrecht` |
| `.github/workflows/web-vitals-woche.yml` | Struktur: Setup-Node, Selbsttest vor `npm ci`, rc-Erfassung |
| `.github/workflows/redaktionelle-ymyl-pruefung.yml` | Struktur: Selbsttest, Werkzeug-Gate, Live-Probe, dreistufige Ticket-Regel |
| `scripts/governance_contract.py` | `belegketten_wache.py` in `GUARDS` (C6) |
| `package.json` | `test:webvitals` erweitert, `test:ymyl` neu |
| `scripts/tests/lighthouse_live.test.mjs` | 26 Node-Tests |
| `scripts/tests/test_cwv_feld_wache.py` | +8 Fälle (29 gesamt) |
| `scripts/tests/test_belegketten_wache.py` | +11 Fälle (26 gesamt) |
| `scripts/tests/test_wartung_kette_1024_1026.py` | **neu**: 20 Strukturverträge beider Vorfälle |
| `docs/ANLEITUNG-WEB-VITALS.md` | Runbook: Fehlerbilder, `--selftest`-Begründung |
| `docs/ANLEITUNG-REDAKTIONELLE-YMYL-PRUEFUNG.md` | Runbook: Exit 1 vs. Exit 2, Messweg |
