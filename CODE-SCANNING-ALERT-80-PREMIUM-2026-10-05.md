# Code-Scanning-Alert #80 – dauerhafte Heilung auf Agentur-Niveau (05.10.2026)

**Alert:** #80 · `py/clear-text-logging-sensitive-data` · Security-Severity 7.5 · Precision `high`

**Ziel:** Ursache entfernen, keine Ausnahme und kein Dismiss; Wiederkehr lokal und in CI blockieren.

**Ergebnis:** Der letzte namensbedingte Fluss ist konstruktiv geheilt. Die neue, vom SARIF-Upload unabhängige **Klartext-Wache** prüft den gesamten Python-Bestand fail-closed.

> **Wahrheitsort.** Dieses Dokument ergänzt den Dauerheilungsbericht zu Alert #78. Der Bericht zu #78 bleibt für Vollanalyse, Namensvertrag, Wert-Dichtheit und Umstellung des GitHub-Setups maßgeblich; hier stehen der zusätzliche Befund #80 und die zweite, upload-unabhängige Kontrolllinie.

---

## 1 · Befund und Ursache

Alert #80 war offen, obwohl die Advanced-CodeQL-Wache „0 Funde“ melden konnte. Das ist kein Widerspruch:

1. Solange GitHubs **Default-Setup** aktiv ist, wird der SARIF-Upload der eigenen Advanced-Konfiguration abgelehnt (`CodeQL analyses from advanced configurations cannot be processed when the default setup is enabled`).
2. Der Upload-Schritt läuft absichtlich mit `continue-on-error`, damit ein Upload-Konflikt nicht die bereits ausgeführte Analyse verschluckt. Der aktuelle Workflow macht diesen Zustand inzwischen als Warnung und Job-Summary sichtbar.
3. Das Default-Setup analysiert unabhängig. Es übernimmt weder `paths-ignore` der Advanced-Konfiguration noch deren Inline-Unterdrückungen.
4. Deshalb ist ein `# codeql[py/clear-text-…]`-Kommentar keine Heilung. Er kann einen Fund nur in einer der beiden parallelen Sichten verbergen.

Die Alert-API ist für das Betriebstoken nicht lesbar (`403 Resource not accessible by integration`). Der Fluss wurde deshalb deterministisch lokal reproduziert:

```text
scripts/secrets_age_guard.py:1280
print("   -", f)
  ← Rückgabe der Funktion oauth_empfaenger_findings()
```

Die Funktion prüfte nur, ob eine statische HTML-Landeseite für Pinterests Autorisierungs-Rückleitung vorhanden und bedienbar ist. Ihre Rückgabe enthielt Befund-Dicts (`level`, `code`, `var`, `msg`), niemals einen Autorisierungscode oder Token. CodeQL wertet jedoch **Namen** als Quelle (`SensitiveDataHeuristics.qll`): `oauth` im Funktionsnamen machte jede spätere Ausgabe der harmlosen Rückgabe formal zu einem sensiblen Fluss.

**Fachliche Diagnose:** inhaltlich kein Geheimnisleck, aber ein falscher semantischer Vertrag. Ein Bezeichner behauptete Zugangsmaterial, obwohl er Seiten-Prüfbefunde trug.

---

## 2 · Heilung im Produktivcode – keine Ausnahme

In `scripts/secrets_age_guard.py` gilt jetzt:

| vorher | nachher | Inhalt |
|---|---|---|
| `oauth_empfaenger_findings()` | `rueckleitung_findings()` | Befunde zur statischen Rückleitungsseite |
| `OAUTH_SEITE` | `RUECKLEITUNG_SEITE` | Dateipfad |
| `OAUTH_ZWILLING` | `RUECKLEITUNG_ZWILLING` | Dateipfad der Slash-Variante |
| `OAUTH_MARKEN` | `RUECKLEITUNG_MARKEN` | erwartete HTML-Merkmale |

Alle produktiven Aufrufe, Selbsttests und Monkeypatch-Stellen wurden atomar umgestellt. Die extern sichtbaren Befund-Codes (`oauth_page_missing`, `oauth_page_incomplete`, `oauth_page_zwilling`) bleiben absichtlich stabil: Sie sind Datenwerte für Governance-Auswertungen, keine Python-Bezeichner und kein Taint-Ursprung.

Die Docstrings dokumentieren den Inhalt ausdrücklich. Es gibt:

- keinen Kompatibilitätsalias mit dem alten sensiblen Namen,
- keine `# codeql[...]`-Unterdrückung,
- kein Alert-Dismiss,
- keine Änderung der fachlichen Pinterest-Prüfung.

### Bereits durch Alert #78 geheilte Überschneidungen

Der aktuelle `main`-Stand enthielt die übrigen Teile des Namensvertrags bereits:

- `secrets:` → `pflicht_env:` im Social-Playbook und allen Verbrauchern,
- intern `fehlende_env`, extern stabil `required_env_names` / `missing_env_names`,
- `c9_secret_leak()` → `c9_leak_wache()`,
- `secrets_text` / lokale `secrets` → `wachen_quelltext`,
- Scorecard-Metriken → `zugangsalter_*`,
- keine Clear-Text-Regel in der Unterdrückungs-Whitelist.

Diese jüngere, bereits verankerte Ausgestaltung bleibt erhalten. Die Heilung von #80 ergänzt sie, statt dieselben Stellen erneut und widersprüchlich umzubenennen.

---

## 3 · Neue Klartext-Wache

`scripts/clear_text_logging_guard.py` bildet die relevanten Eigenschaften von

- `py/clear-text-logging-sensitive-data` und
- `py/clear-text-storage-sensitive-data`

lokal mit Python-AST-Analyse nach. Sie braucht weder Netzwerk noch CodeQL-CLI noch GitHub-Berechtigungen.

### 3.1 Abdeckung

- sensible Quellen aus Variablen-, Parameter-, Funktions-, Attribut- und konstanten Mapping-Schlüssel-Namen,
- `print`, `logging.*`, erkannte Logger-Instanzen sowie `stdout`/`stderr` als Ausgabesenken,
- `json.dump`, YAML-/Pickle-Dump, Datei-`write*` und `Path.write_*` als Klartext-Speichersenken,
- lokale Aufruf-, Rückgabe-, Container-, Iterations- und Tupel-Flüsse,
- schlüsselbezogenes Taint-Modell statt pauschaler Vergiftung ganzer Mappings,
- monotone Fixpunktanalyse ohne willkürliche maximale Aufruftiefe,
- versionierte **und neue, nicht ignorierte** Python-Dateien (`git ls-files --cached --others --exclude-standard`),
- wertfreie Diagnosen (Datei, Zeile, Quellenart, Senke; nie Quelltext oder Trefferwert),
- Fallback-Rekursion außerhalb eines Git-Checkouts.

### 3.2 Fail-closed

| Exit-Code | Bedeutung |
|---|---|
| `0` | vollständig analysiert, kein Befund |
| `1` | mindestens ein Klartext-Fluss oder verbotener Marker |
| `2` | Datei nicht lesbar, nicht UTF-8, syntaktisch nicht analysierbar oder Aufruffehler |

JSON- und Textmodus haben dieselbe Exit-Semantik. Ein Parsefehler kann daher nicht als gewöhnlicher Fund oder als Grün durchrutschen.

### 3.3 Unterdrückung ist selbst ein Befund

Die Wache erkennt echte Python-Kommentare tokenbasiert. Jeder Kommentar mit einer der beiden Clear-Text-Regeln wird **auch ohne Datenfluss** rot. Marker in Docstrings oder Test-Fixtures zählen dagegen nicht; ein naiver Substring-Scan würde die Wache mit ihrem eigenen Lehrstoff verwechseln.

Damit gelten dieselben Regeln lokal, im Regressionstest und in CI:

1. harmloser Inhalt, sensibel klingender Name → Name ehrlich machen;
2. echter sensibler Wert → Hash/Fingerabdruck/Status/Positiv-Whitelist oder Ausgabe entfernen;
3. nie unterdrücken.

### 3.4 Eigenprüfung

`--selftest` enthält:

- **10 Positivproben:** sensibler Lookup, sensibler Funktionsname, Zuweisung, Parameter, Logging, Storage, eigenständige Unterdrückung, Logger-Alias, Aufrufkette über mehr als acht Helfer und wertfreie Diagnose;
- **6 Gegenproben:** ehrliche Variablennamen, Hash, reine Vorhandenseinsprüfung, ausgeschlossene ID-Klasse, entschärfter Name und Marker nur im String;
- **19 Namensproben** gegen die nachgebaute CodeQL-Heuristik.

Eine stumpfe Wache fällt somit an ihrer eigenen Gegenmessung aus.

---

## 4 · Dauerhafte Verankerung

### CI

`.github/workflows/codeql.yml` besitzt den eigenständigen Job:

```text
Klartext-Wache (unabhängig vom SARIF-Upload)
  1. Eigenprüfung
  2. vollständiger Repository-Lauf
  3. Regressionstest test_clear_text_logging_security
```

Der Job hat keine Laufzeitabhängigkeit außer Python 3.12, blockiert Pull Requests hart und bleibt wirksam, wenn:

- der SARIF-Upload abgelehnt wird,
- das Default-Setup parallel läuft,
- GitHub-Alert-APIs nicht lesbar sind,
- ein CodeQL-Kommentar versucht, einen Fund auszublenden.

Die bestehende CodeQL-Vollanalyse bleibt zusätzlich aktiv (`CODEQL_ACTION_DIFF_INFORMED_QUERIES: false`). Die lokale Wache ersetzt CodeQL nicht; sie schließt gezielt dessen betriebliche Transportlücke für die beiden Clear-Text-Regeln.

### Regressionstests

- `KlartextWacheContract` in `scripts/tests/test_clear_text_logging_security.py` erzwingt Eigenprüfung, JSON-Fail-closed, Repository-Nullbefund und den #80-Namensvertrag.
- `Unterdrueckungsverbot` in `scripts/tests/test_zugangs_namensvertrag.py` erkennt echte verbotene Kommentare tokenbasiert.
- Der bestehende Wert-Dichtheitstest vergiftet alle Zugangsvariablen und beweist, dass kein Wert in Konsole, JSON, Markdown oder Historie gelangt.

---

## 5 · Verifikation

| Prüfung | Ergebnis |
|---|---|
| `python3 scripts/clear_text_logging_guard.py --selftest` | ✅ 10 Positiv-, 6 Gegen-, 19 Namensproben |
| `python3 scripts/clear_text_logging_guard.py` | ✅ 372 Python-Dateien, 0 Befunde, 0 Analysefehler |
| `python3 scripts/secrets_age_guard.py --selftest` | ✅ fachliche Rückleitungsprüfung unverändert |
| `python3 -m unittest scripts.tests.test_clear_text_logging_security -v` | ✅ Sicherheitsvertrag inklusive Repository-Lauf |
| `python3 -m unittest scripts.tests.test_zugangs_namensvertrag -v` | ✅ 21 Tests: Namens-, Werte- und Unterdrückungsvertrag |
| `python3 -m unittest discover -s scripts/tests` | ✅ 1.787 Tests, 23 übersprungen |
| `python3 scripts/selftest_runner.py` | ✅ 155 Wachen, 310 Uhr-Proben |
| `governance_contract.py --selftest` / `--quick` | ✅ Kunstbefunde erkannt; 19 Regeln erfüllt |
| Social-Preflight, Cockpit und Schaltwerk `--selftest` | ✅ fachliche Verbraucher unverändert |

Damit sind sowohl der gezielte Sicherheitsvertrag als auch alle übrigen Repository-Regressionen gegen den finalen Stand ausgeführt.

---

## 6 · Einmalige Betreiberhandlung nach dem Merge

Die Code-Ursache ist im Repository geheilt. Für eine einzige Alert-Wahrheit muss das parallele GitHub-Default-Setup trotzdem einmalig beendet werden:

1. <https://github.com/frank-hartung/franksfinanzcheck-blog/settings/security_analysis>
2. **Settings → Security and quality → Advanced Security**
3. Abschnitt **Code Security**, Zeile **CodeQL analysis**, Menü `...`
4. **Disable CodeQL** wählen – nicht „Switch to advanced“
5. Unter **Security and quality → Code scanning → Affected branches → main** die stale Default-Konfiguration löschen; die Kategorien `/language:python` und `/language:javascript` dieser Repository-Wache stehen lassen.

Danach muss der Schritt **„SARIF in Security-Tab hochladen“** grün sein und die Upload-Konfliktwarnung entfallen. Ein Dismiss von Alert #80 ist nicht erforderlich: Der nächste Lauf schließt den Alert aufgrund des entfernten Flusses. Falls die alte Default-Konfiguration nur stale ist, wird ausschließlich diese Konfiguration wie oben beschrieben entfernt.

---

## 7 · Runbook für den nächsten Klartext-Fund

1. `python3 scripts/clear_text_logging_guard.py` lokal ausführen.
2. Genannte Quelle und Senke lesen; danach die entsprechende CodeQL-Query prüfen.
3. In dieser Reihenfolge heilen:
   - falschen Bezeichner korrigieren,
   - echten Wert konstruktiv entschärfen,
   - unnötige Ausgabe entfernen.
4. Keine Unterdrückung und kein Dismiss als Ersatz für Codeänderung.
5. Das neue Muster als Positiv- **und** Gegenprobe ergänzen.
6. Klartext-Wache, gezielten Regressionstest und vollständige Tests ausführen.
7. Erst dann mergen; nach dem Push die Security-Tab und den upload-unabhängigen CI-Job kontrollieren.
