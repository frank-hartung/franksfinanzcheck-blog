# Code-Scanning-Alert #80 – dauerhafte Heilung (2026-10-05)

**Alert:** #80 · `py/clear-text-logging-sensitive-data` („Clear-text logging of sensitive information", security-severity 7.5, precision high) · **Ausgangslage:** 1 offener Alert, obwohl die Heilung vom 04.10.2026 mit „0 offene Funde" abgeschlossen hatte · **Ergebnis:** die auslösenden Datenflüsse existieren nicht mehr – **ohne eine einzige Unterdrückung**, dafür mit einer neuen, vom GitHub-Upload unabhängigen Wache (`scripts/clear_text_logging_guard.py`), die dieselben zwei CodeQL-Regeln lokal und fail-closed nachbildet.

> **Wahrheitsort.** Dieses Dokument löst `CODE-SCANNING-HEILUNG-PREMIUM-2026-10-04.md` für alles ab, was die beiden Klartext-Regeln betrifft. Der ältere Bericht bleibt gültig für Methodik, JS-Funde und die Pipeline-Architektur. Was hier steht, gilt bis ein neuer datierter Abschnitt es ablöst.

---

## 1 · Was passiert war – und warum „0 Funde" trotzdem stimmte

Der Lauf der Sicherheitswache auf `main` meldet seit dem 04.10.2026 zuverlässig:

```
sarif-results/python.sarif: 6 → 0 Funde (6 per Code-Kommentar unterdrückt)
CodeQL-Bilanz (python): 0 Funde – 0 sicherheitsrelevant, 0 Qualitäts-Hinweise.
```

Gleichzeitig stand in der Security-Tab ein offener Alert #80. Beides war richtig – und genau das ist der Fehler im System:

1. **Die erweiterte Konfiguration kommt gar nicht an.** Der Upload-Schritt quittiert mit
   `##[error]Code Scanning could not process the submitted SARIF file: CodeQL analyses from advanced configurations cannot be processed when the default setup is enabled` (`CODEQL_ACTION_JOB_STATUS: JOB_STATUS_CONFIGURATION_ERROR`). Der Schritt läuft mit `continue-on-error: true` – der Lauf bleibt grün.
2. **Das Default-Setup analysiert unabhängig weiter** und erzeugt die Alerts, die in der Tab sichtbar sind.
3. **Das Default-Setup kennt unsere Ausnahmen nicht.** Es ignoriert `paths-ignore` aus `.github/codeql/codeql-config.yml` **und** jeden `# codeql[regel-id]`-Kommentar. Die sechs Funde, die unsere Pipeline als „per Code-Kommentar unterdrückt" wegfiltert, bleiben dort offene Alerts: 3 × `py/clear-text-logging-sensitive-data`, 1 × `py/clear-text-storage-sensitive-data`, 2 × `*/incomplete-url-substring-sanitization`.

**Konsequenz, die dieses Dokument durchsetzt:** Solange beide Engines laufen, ist eine Unterdrückung per Kommentar **keine Heilung, sondern eine unsichtbar gewordene Fundstelle**. Für die beiden Klartext-Regeln ist sie ab sofort verboten (durchgesetzt durch Test und CI-Job, siehe § 5).

---

## 2 · Reproduktion ohne Zugriff auf den Alert

Die REST-Endpunkte für Code-Scanning-Alerts antworten diesem Betriebstoken mit `403`; die CodeQL-CLI lässt sich in der Arbeitsumgebung nicht beziehen. Reproduziert wurde deshalb über drei unabhängige Wege, die zum selben Ergebnis führen:

| Weg | Beleg |
|---|---|
| Job-Logs der Wache auf `main` | Filterschritt nennt exakt `6 → 0 Funde`; Push-Läufe auf `main` sind **Voll**analysen (nachgewiesen an reinen Workflow-Commits, die dieselben 6 melden) |
| Whitelist der unterdrückbaren Regeln | genau 4 Regel-IDs ⇒ die 6 Funde sind eindeutig auf 3 + 1 + 2 aufteilbar |
| Lokale Nachbildung der Query | `scripts/clear_text_logging_guard.py` findet dieselben 4 Python-Stellen (±1 Zeile Versatz durch Mehrzeilen-Aufrufe) |

**Die Fundstellen (Stand vor der Heilung):**

| Datei:Zeile | Regel | Quelle (nach CodeQL-Heuristik) | Senke |
|---|---|---|---|
| `scripts/governance_contract.py:1968` | logging | Aufruf von `c9_secret_leak()` | `print(f"  ❌ {line}")` |
| `scripts/governance_contract.py:1973` | logging | dieselbe Liste | `print(f"::error::{line}")` |
| `scripts/governance_contract.py:1988` | storage | dieselbe Liste | `f.write(render_md(checks))` |
| `scripts/social_preflight.py:655` | logging | `kanal.get("secrets")` / `eintrag["secrets"]` | `print(json.dumps(safe_bericht, …))` |

---

## 3 · Die fachliche Ursache: CodeQL klassifiziert **Namen**, nicht Werte

Gelesen wurden die Query-Quellen selbst (`CleartextLogging.ql`, `CleartextLoggingCustomizations.qll`, `SensitiveDataSources.qll`, `SensitiveDataHeuristics.qll`). Entscheidend:

- **Quelle** ist jede `SensitiveDataSource` außer den Klassifikationen `id` und `certificate`: eine Zuweisung an einen sensibel benannten Namen, ein Attribut-/Index-/`.get()`-Zugriff mit sensibel benanntem Schlüssel, ein sensibel benannter Parameter **und der Rückgabewert einer sensibel benannten Funktion**.
- **Senke** ist jedes Argument von `print()`, jedes `logging.*`-Argument und `sys.stdout/stderr.write`.
- Die Heuristik ist rein lexikalisch: `secret`, `pass(word|code|phrase)`, `oauth`, `api.?key`, `auth…key` treffen; `token` und `key` allein treffen nicht; alles, was `hash`, `path`, `url`, `file`, `random`, `crypt` enthält, ist ausgenommen.

Damit war der Befund **inhaltlich falsch und formal völlig richtig**: Die gedruckten Daten waren schon immer harmlos (Regel-Labels, Dateinamen, Variablen**namen**) – aber sie kamen aus Bezeichnern, die Geheimnis **behaupteten**:

- `c9_secret_leak()` liefert `("C9", "<Datei>: Groq-API-Key im Klartext – …")`. Kein Treffer-Text, kein Wert. Der Name sagte etwas anderes.
- Das Kanal-Playbook führte unter `secrets:` die **Namen** der benötigten Umgebungsvariablen (`MASTODON_ACCESS_TOKEN`), nie deren Werte.

Ein Name, der lügt, ist ein Dokumentationsfehler – und für jede namensbasierte Analyse ein Dauer-Fehlalarm. Deshalb ist die Heilung keine Kosmetik: **Die Bezeichner sagen jetzt, was sie tragen.**

---

## 4 · Die Heilung – Namensvertrag statt Ausnahme

### 4.1 Governance-Vertrag (`scripts/governance_contract.py`)

| vorher | nachher | Grund |
|---|---|---|
| `def c9_secret_leak(texts)` | `def c9_klartext_leck(texts)` | Die Funktion **findet** Klartext-Funde, sie **liefert** keine Geheimnisse. Docstring hält fest: nur `label`, nie der Treffer. |
| `SECRET_PATTERNS = LEAK_CHECK_PATTERNS` | entfernt | Toter Alias mit geheimnis-behauptendem Namen. |
| `c5_record_provenance(…, secrets_text)` | `(…, wachen_quelltext)` | Der Parameter trägt den **Quelltext** von `secrets_age_guard.py`, aus dem Variablennamen gelesen werden. |
| lokale Variable `secrets` | `wachen_quelltext` | dito |
| 3 × `# codeql[…]` | **entfernt** | Der Fluss existiert nicht mehr; die Kommentare hätten das Default-Setup ohnehin nie erreicht. |

### 4.2 Social-Playbook und alle Verbraucher

`secrets:` → **`pflicht_env:`** in `data/social/channels.yaml` (10 Kanäle) und in jedem Konsumenten:

`scripts/social_preflight.py` (intern `pflicht_env` / `fehlende_env`), `scripts/cockpit.py`, `scripts/schaltwerk_actions.py`, `scripts/schaltwerk_triggers.py`, `scripts/social_channels/__init__.py`, Tests `test_clear_text_logging_security.py` und `test_cockpit.py`.

**Die JSON-Oberfläche bleibt unverändert** (`required_env_names` / `missing_env_names`) – sie ist Vertrag für Cockpit und Schaltwerk. Neu ist, dass die Übersetzung über eine benannte Tabelle `JSON_FELDNAMEN` läuft und der Bericht **schon intern** ehrlich heißt; die Sanitisierung ist damit kein Pflaster mehr, sondern eine reine Namens-Normalisierung.

### 4.3 Secrets-Wache (`scripts/secrets_age_guard.py`)

`oauth_empfaenger_findings()` → **`rueckleitung_findings()`**, ebenso `OAUTH_SEITE/_ZWILLING/_MARKEN` → `RUECKLEITUNG_*`. Die Funktion prüft eine statische HTML-Landeseite (`static/pinterest-oauth.html`) auf Tauglichkeit – sie sieht nie einen Token. Unter dem alten Namen war jede Ausgabe ihrer Befunde ein Klartext-Leck „per Definition".

### 4.4 Was bewusst **nicht** umbenannt wurde

`cockpit.bucket_secrets()`, `secrets_age_guard.verify_secret()`, `pinterest_token`s `app_secret`-Feld und `data/secrets_state.json` behalten ihre Namen. Sie beschreiben ihren Inhalt korrekt (Zugangs-Ampel, Live-Probe eines Secrets, tatsächliches App-Secret) – und CodeQL meldet sie nicht, weil die Flüsse dort über **unbekannte Schlüssel** laufen bzw. nur entschärfte Werte in die Ausgabe gelangen (§ 5.2). Umbenennen „zur Beruhigung einer Wache" wäre Lärm in sicherheitsrelevanter Mechanik gewesen; der ehrliche Name hat Vorrang vor dem bequemen.

---

## 5 · Die Klartext-Wache – Kontrolle, die nicht vom Upload abhängt

`scripts/clear_text_logging_guard.py` (neu) bildet `py/clear-text-logging-sensitive-data` und `py/clear-text-storage-sensitive-data` lokal nach: Sie liest alle 369 per `git ls-files '*.py'` verwalteten Python-Dateien in rund 9 Sekunden, ohne Netz, ohne CodeQL-CLI, ohne GitHub.

### 5.1 Doktrin

1. **Unterdrückung ist keine Heilung.** Eine Zeile mit `# codeql[py/clear-text-…]` gilt der Wache als eigenständiger Befund – genau so, wie das Default-Setup sie sieht.
2. **Fail-closed.** Exit 1 bei Befund, Exit 2 bei nicht analysierbarem Code.
3. **Eigenprüfung.** `--selftest` fährt 7 Positivproben, 5 Gegenproben und 19 Namensproben; darunter exakte Nachbauten der beiden #80-Muster und der geheilten Gegenstücke. Eine Wache ohne Gegenprobe ist Schein-Sicherheit.

### 5.2 Warum sie so genau ist wie CodeQL – und nicht lauter

Die erste, grobe Fassung meldete 38 Stellen; 34 davon waren Fehlalarme. Ursache war eine feldblinde Taint-Verfolgung. Die eingesetzte Fassung bildet deshalb **Inhalts-Semantik** nach, wie CodeQLs Dataflow sie kennt:

- Taint wird je **Schlüssel** geführt (`{"app_secret": …}`), `"*"` steht für „das ganze Objekt".
- Lesen mit **konstantem** Schlüssel (`d["k"]`, `.get("k")`, `t[0]`) liefert nur dessen Taint.
- Lesen mit **unbekanntem** Schlüssel (`d[var]`, `.items()`, `.values()`) liefert **nichts** – CodeQL verfolgt diesen Weg ebenfalls nicht. Genau das erklärt, warum `buckets["Secrets & Zugänge"] = bucket_secrets(…)` plus späteres `buckets[name]` kein Befund ist.
- Wer über eine heiße Sammlung **iteriert**, hält Heißes in der Hand (`for code, msg in checks:` – der reale #80-Pfad).
- Tupel-Entpackung, `return a, b`, Dict-/Listen-Literale, `IfExp`, `json.dumps`, `str()` und `dict()`/`copy.deepcopy()` sind gliedweise bzw. inhaltserhaltend modelliert; Hash-/Fingerabdruck-Funktionen entschärfen.

Kalibriert wurde gegen die **tatsächlichen** 6 Funde des Default-Setups: Das Modell reproduziert sie und erzeugt darüber hinaus keinen einzigen Fehlalarm im Repository.

### 5.3 Verankerung

- **CI:** neuer, von CodeQL unabhängiger Job `klartext-wache` in `.github/workflows/codeql.yml` (Selbsttest → Repo-Lauf → Regressionstest). Er braucht weder SARIF-Upload noch Default-Setup und blockiert Pull Requests hart.
- **Test:** `scripts/tests/test_clear_text_logging_security.py`, Klasse `KlartextWacheContract` – Selbsttest grün, **null** Befunde im ganzen Repo, **null** `# codeql[…]`-Unterdrückungen der beiden Regeln, und der Namensvertrag (`c9_klartext_leck`, `rueckleitung_findings`, `pflicht_env`) ist festgenagelt.
- **Pipeline:** Die beiden Klartext-Regeln sind aus der Whitelist der unterdrückbaren Regeln in `codeql.yml` **entfernt**. Ein zukünftiger Kommentar würde den Fund also nicht mehr aus dem SARIF filtern – er erschiene wieder im Gate.

---

## 6 · Verifikation (alles lokal reproduzierbar)

| Prüfung | Ergebnis |
|---|---|
| `python3 scripts/clear_text_logging_guard.py --selftest` | ✅ 7 Positivproben, 5 Gegenproben, 19 Namensproben |
| `python3 scripts/clear_text_logging_guard.py` | ✅ 369 Dateien, **0 Fundstellen**, 0 Unterdrückungen |
| `python3 -m unittest discover -s scripts/tests` | ✅ 1763 Tests (23 übersprungen) |
| `python3 scripts/selftest_runner.py` | ✅ 155 Wachen, 310 Uhr-Proben |
| `python3 scripts/governance_contract.py --selftest` / `--quick` | ✅ C1–C18 grün / Vertrag erfüllt |
| `python3 scripts/social_preflight.py --selftest` + `--offline --json` | ✅ 11 Kanäle; JSON-Oberfläche unverändert |
| `python3 scripts/secrets_age_guard.py --selftest`, `cockpit.py --selftest`, `schaltwerk.py --selftest` | ✅ |

---

## 7 · Einmalige Handlung für den Betreiber (wichtig)

Die Code-Ursache ist geheilt; die **Doppel-Analyse** bleibt bis zu einem Klick bestehen:

> Repo → **Settings → Code security and analysis → Code scanning (CodeQL) → Default setup → Disable**

Erst danach kann die erweiterte Wache ihr SARIF hochladen, und erst danach gelten `paths-ignore` sowie dokumentierte Ausnahmen überhaupt. Bis dahin ist der Job `klartext-wache` die maßgebliche Kontrolle für die beiden Klartext-Regeln – er funktioniert unabhängig davon, welche Engine gerade meldet.

Ein bereits geschlossener Alert #80 bleibt geschlossen, sobald der nächste Lauf des Default-Setups die Fundstellen nicht mehr sieht; es ist **kein** „Dismiss" nötig und keines wurde vorgenommen.

---

## 8 · Runbook für künftige Klartext-Funde

1. **Lokal reproduzieren:** `python3 scripts/clear_text_logging_guard.py` – sie nennt Datei, Zeile, Quelle und Senke.
2. **Heilen, in dieser Reihenfolge:**
   - **Name ehrlich machen** (`pflicht_env` statt `secrets`, `…_leck` statt `…_secret_…`), wenn der Wert harmlos ist;
   - **Wert entschärfen** (`hash16()`, Fingerabdruck, Status-String `vorhanden`/`FEHLT`, Positiv-Whitelist sicherer Felder), wenn der Wert echt ist;
   - **Ausgabe weglassen**, wenn beides nicht trägt.
3. **Niemals unterdrücken.** Für diese beiden Regeln ist `# codeql[…]` durch Test und CI gesperrt – das Default-Setup würde den Kommentar ohnehin nicht lesen.
4. **Regression sichern:** neues Muster als Positiv- **und** Gegenprobe in `POSITIV`/`NEGATIV` der Wache ergänzen.
5. **Dokumentieren:** datierter Abschnitt hier, Kurzfassung in `SECURITY.md`.
