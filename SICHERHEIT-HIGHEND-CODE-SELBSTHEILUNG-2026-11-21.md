# Sicherheits-Wache · Highend · Code-Selbstheilung (#709)

**Stand:** 21.11.2026 · **Umfang:** Vollständige High-End-Aufwertung der Sicherheits-Wache (CodeQL-Gate, URL-, Klartext-, ReDoS-Guards, Abhängigkeiten, Live-Messung) **plus** automatische Selbstheilung für #709-Finding-Klassen.
**Status:** Architektur + Implementierung + Tests lokal geprüft. Kein Deploy auf `main`, kein PR angelegt. Live-Jobs und historische rotes-ReDoS-/GSC-Runs sind **nicht** vollständig belegt (siehe §4).

## 1. Belegte Feststellungen (vor Umsetzung)

### Zwei nicht geprüfte rote Läufe der ReDoS-Wache

Zwei PR-Läufe der CodeQL-Wache (run 44905110696, run 44914358334, beide auf Branch `arena/c7596817`) scheiterten identisch im 6. Schritt `Sicherheitsvertrag zu Alert Nr. 87` (`python3 -m unittest scripts.tests.test_redos_security -v` + `python3 -m unittest scripts.tests.test_gsc_abdeckung`); Schritt 7 (`gsc_abdeckung.py --selftest`) wurde übersprungen. Lokal war `test_redos_security` grün (15/15) — die wohl einzige rote Komponente war die GSC-Inhaltsinventarin-Kontrakte `BestandOhneInseln` (2 Seiten ohne redaktionellen Inlink). Diese Einsicht war bestätigt und durch die GSC-Selbstheilung `--verlinkung --heilen` geschlossen: 4 Links in 2 Zielposts (10-07 Smart-Home → 11-01 Geräte; 11-10 Fenster-Abdichten → 11-01 Geräte; 11-01 Geräte → 11-18 Gas; 11-05 Waschmaschine → 11-18 Gas), `--wache` meldet `0` ohne Inlink und `--heilen` (idempotent) schreibt keine weiteren Paare, ohne Rest `Bestand ohne Inlink: 0`.

### Abhängigkeiten-Selbstheilung (#79) als Referenz

Der bewährte Vertragsmuster (5 Schichten: Vertrag, Eichprobe, Heilung, Belegkette, Verdrahtung) existiert für #79 (`abhaengigkeits_selbstheilung.py` + `abhaengigkeits-selbstheilung.yml`). **#709 hatte dieses Muster nicht** — der #709-Heal (CODE-SCANNING-SUCHRADAR-HEILUNG-PREMIUM-2026-10-12.md) erfolgte von Hand, ohne nachweislich schreibende Automatik, ohne Vertrag, ohne Belegkette, ohne `--wache`. Eine gleichartige Klasse hätte sich jeder Tageslauf als dieselbe Handarbeit wieder einstellen können.

### Live sicherheits-wache (run 44918967667)

Lauf mit `sicherheits-wache.yml` (fail-closed Live-Messung) — Deps/Quellseite grün, **Live-Messung fehlgeschlagen (step 6/7)**; Job-Logs derzeit nicht abfragbar (EOF-/Transportfehler). Nicht ursächlich analysierbar — separate Aufgabe, nicht hier gelöst.

## 2. Dauerhafte Korrekturen (Highend, 5 Schichten)

### 1 · Schutz-Vertrag (`data/code_schutz_vertrag.json`)

Eine Quelle der Wahrheit für Regel (`py/incomplete-url-substring-sanitization`), Detektor (`scripts/url_substring_guard.py`), Helper (`scripts/url_host.py`/`ist_host_oder_subdomain`), maximal heilbare Dateien (40), Ausnahmeliste (Detektor selbst — der Detektor heilen sich nicht), Branche `automation/code-selbstheilung-*`, Belegkette `data/code_schutz_belege.jsonl`. Verwaiste Schlüssel werden abgelehnt; doppelte JSON-Schlüssel sind nicht belegbar.

### 2 · Eichprobe (`--selftest`)

Vor jedem Urteil und vor jedem Schreibzugriff wird Vorfall #709 im Speicher nachgebaut — historische, echte #709-Fundstellen (6 Fundstellen über 4 Dateien: `serp_anbieter.py`, `serp_html.py`, `suchradar.py`, `test_suchradar.py`). Detektion (6/6), Heilung (6/6 transformieren → 0 py-Fundstellen), Belegkette-Sabotage erkannt, blinder Detektor erkannt (Exit 3, kein Urteil, kein Schreiben).

### 3 · Heilung (AST-genau, host-exakt)

`--heilen` sucht nur heilbare Python-Fundstellen — `Compare` mit konstanter URL-Literal links (`in`/`not in`) und `Call` startswith/endswith mit konstanter URL-Literal. AST-spektraler Transform — ersetzt nur innerhalb der reellen Fundstellen, nicht ganze Zeilen, nicht JS/HTML. Host-exakt statt Teilzeichenkette: `ist_host_oder_subdomain(url, 'duckduckgo.com')` statt `'duckduckgo.com' in url`. Import-Erzeugung als `from url_host import ist_host_oder_subdomain  # noqa: E402  (Host-exakte URL-Wahrheit)`. **Unheilbarer Code (unbekannte Rechtsquelle, überlappende Knoten, JS/HTML-Fundstellen, Ausnahmen) → fail-closed: nichts geschrieben, nichts annehmen.** Rollback bei jedem Rollback-Fehler atomar.

### 4 · Belegkette (`data/code_schutz_belege.jsonl`)

Verkettete SHA-256-Belegkette ab `GENESIS`, parallel zu `data/abhaengigkeits_schutz_belege.jsonl` und `data/produktions_schutz_belege.jsonl`. Zeilenkontrakte: `seq` aufeinanderfolgend, `prev_sha256` bruchlos, `sha256` inhaltlich prüfbar, keine doppelten Schlüssel. `merge=binary` in `.gitattributes` — die Belegkette ist eine verifizierte Mess-/Nachweisdatei. Idempotent: Ein sauberer Bestand (`SICHER`) schreibt **keine Uhrzeit ins Repo**.

### 5 · Verdrahtung (`--wache`)

Prüft: Pflichtdateien (Heiler, Tests, Vertrag, Belegkette, `.gitattributes`, Workflow, Sicherheits-Wache, Alert-Wache), Vertrag-Stil (Vertrag-Boden), Belegkette (prüfbar), GitAttributes (`merge=binary`), Heil-Workflow (Name, `--selftest`, `--wache`, `--heilen`, `git_sync.sh`, `gh pr create`, **`gh pr merge` ist verboten** — H-02), Sicherheits-Wache (Selbsttest + Verdrahtungs-Wache als Gate), Alert-Wacht-Liste (`Code-Selbstheilung · Heilungs-PR` als Überwachtungscode).

### Workflow (`.github/workflows/code-selbstheilung.yml`)

Modell: FÜNF SCHICHTEN — Vertragsprüfung (offline), `--selftest` (Eichprobe), `--wache` (Verdrahtung), Vertragstests (offline), Bestand auditieren + heilen (`--heilen` neutral), geprüfter PR (`automation/code-selbstheilung-*`, `git_sync.sh` + `gh pr create`, `--base main`, kein merge), Endurteil mit Belegkette (`SICHER`/`GEHEILT`/`TEILGEHEILT`/`OFFEN`/`MESSGERAET`/`NICHT_BELEGBAR`). Häufung täglich 06:38 UTC (nach Abhängigkeiten-Selbstheilung 06:18), `workflow_run` nach Sicherheits-Wache-Failure.

### Verdrahtung in die Sicherheits-Wache (`.github/workflows/sicherheits-wache.yml`)

Neue Pfad-Liste: `scripts/code_selbstheilung.py`, `scripts/tests/test_code_selbstheilung.py`, `scripts/url_substring_guard.py`, `scripts/url_host.py`, `data/code_schutz_vertrag.json`, `data/code_schutz_belege.jsonl`, `.github/workflows/code-selbstheilung.yml`. Selbsttest- und `--wache`-Schritte im `abhaengigkeiten`-Job. Vertragstests im `Vertragstests der Wache`-Schritt — `test_code_selbstheilung` gesamt. Damit bricht jede Änderung am Code-Heiler, an seinen Tests, am Vertrag, an der Belegkette, an der Verdrahtung oder an der URL-Substring-Wache — jede Push/PR-Änderung löst den Sicherheits-Wache-Lauf aus.

### Alert-Wacht-Liste (`.github/workflows/alert-on-failure.yml`)

`Code-Selbstheilung · Heilungs-PR` als Überwachungscode — ein Heilungs-Lauf darf bei Eichprobenbruch (Exit 3) oder Rollback (Exit 2) niemals stumm scheitern.

## 3. Verifikation (lokal 21.11.2026)

| Prüfung | Ergebnis |
|---|---|
| `python3 scripts/code_selbstheilung.py --selftest` | ✅ 5 Schichten: `detektion:6, heilung:6, nachmessung:0, blind_sabotager_wird_erkannt, belegkette_sabotage_erkannt` |
| `python3 scripts/code_selbstheilung.py --wache` | ✅ Vertrag + Belegkette + Workflow + Sicherheits-Gate + Alerting sauber |
| `python3 scripts/code_selbstheilung.py --pruefen --json` | ✅ `SICHER` (Befund-ID `sauber`, 0 befunde) |
| `python3 -m unittest scripts.tests.test_code_selbstheilung` | ✅ **22 Tests OK** (Vertrag 6, Eichprobe 2, Transform 4, Belegkette 3, Vollheilung 2, Verdrahtung 2, CLI 2) |
| `python3 -m unittest scripts.tests.test_workflow_yaml scripts.tests.test_code_selbstheilung scripts.tests.test_url_substring_security` | ✅ **51 Tests OK (skipped=7)** |
| `python3 -m unittest scripts.tests.test_abhaengigkeits_wache scripts.tests.test_abhaengigkeits_selbstheilung scripts.tests.test_code_selbstheilung` | ✅ **91 Tests OK** |
| `python3 -m unittest scripts.tests.test_blog_header_gate scripts.tests.test_sicherheits_nachweis scripts.tests.test_alert_scoping scripts.tests.test_alert_resolve_gate scripts.tests.test_cloudflare_edge_freigabe scripts.tests.test_live_selbstheilung` | ✅ **172 Tests OK (skipped=1)** |
| `python3 -m unittest scripts.tests.test_worker_betrieb_wache scripts.tests.test_worker_deploy_vorbereiten scripts.tests.test_worker_ressourcen scripts.tests.test_worker_zugang scripts.tests.test_worker_environment_guard scripts.tests.test_worker_environment_einrichten scripts.tests.test_worker_freigabe_wache` | ✅ **204 Tests OK** |
| `python3 scripts/url_substring_guard.py --json` | ✅ **0 Funde, 0 Fehler, 1411 Datei-Prüfungen** (URL-substring-Wache grün; vorher 1409) |
| `python3 scripts/gsc_abdeckung.py --verlinkung --wache` | ✅ **0 Seiten ohne Inlink** |
| `python3 scripts/gsc_abdeckung.py --verlinkung --heilen` | ✅ **Idempotent: 0 Paare, 0 eingefügt, exit 0** |
| `python3 scripts/redos_guard.py --selftest` | ✅ 4 ReDoS-Regeln bestätigt |
| `python3 -m unittest scripts.tests.test_redos_security` | ✅ 15/15 grün |
| `python3 -m unittest scripts.tests.test_gsc_abdeckung` | ✅ **104 Tests grün** |

## 4. Was noch offen ist und wie weiter

1. **ReDoS-/GSC-CI-Läufe (Runs 44905110696, 44914358334)** — Step 6 (`Sicherheitsvertrag zu Alert Nr. 87`, `test_redos_security` + `test_gsc_abdeckung`) fiel im PR-Lauf nachweislich aus — wahrscheinlich, weil die GSC-Invarianten (2 Seiten ohne Inlink) den Testblock blockierten. Lokal jetzt geschlossen: `test_gsc_abdeckung` 104/104, `test_redos_security` 15/15. Die historischen roten Läufe sind **nicht** reproduziert bis zum aktuellen Stand; der nächste CodeQL-Lauf (oder der nächste Tageslauf 03:30 UTC) bestätigt den Heilungsschritt. **Nicht als bewiesen** angenommen.
2. **Live sicherheits-wache (run 44918967667)** — Deps/Quellseite grün, **Live-Messung (`F-01` Header / Worker-Stand) gescheitert**; Job-Logs nicht abfragbar (EOF-/Transportfehler). Wiederholung nach Transport-Stabilisierung, danach Bestätigung über GitHub-UI/API und eventuell `--live`-Nachweis. **Nicht behoben** — nur lokal verstanden.
3. **Heilung für #709-Klasse** — Live-Heilung ist ein **PR** (H-02), nicht ein Direkt-Merge auf `main`. Endziel: Der Heil-Workflow (`code-selbstheilung.yml`) läuft täglich 06:38 UTC, systemseitig H-02, der Mensch merget den erzeugten PR. Die 4 content-Files (10-07 smart-home, 11-01 Geräte, 11-05 Waschmaschine, 11-10 Fenster-Abdichten) mit dem GSC-Heiler sind **in der Arbeits-Branch** — kein Push, keine Merge, kein PR. Sie sind dieselbe Art von Wartung wie `abhaengigkeits-selbstheilung.yml`, aber für Inhalts-Links. Falls gewollt: Sie werden einzeln in einem Heilungs-PR für den Inhalt geliefert.
4. **Belegkette ist leer** — `data/code_schutz_belege.jsonl` enthält keine einzige Zeile (sauberes Messergebnis). Erst ein echter Nachweis-Lauf eines offenen Befunds erzeugt den ersten Beleg.

## 5. Risiken & Grenzen

- **Transform-Abstraktion:** Der Heiler transformiert nur reine Python-Fundstellen (Compare mit konstanter URL-Literal-Links + `startswith`/`endswith` mit konstanter URL-Literal-Argument). JS/HTML-Substrings und reine AST-unbekannte Formen bleiben sichtbar als „verbleibende Funde" und erzeugen **keinen** auto-PR. Eigentlich ist das im Highend-Sinn korrekt — Risiken ausschließlich sichern, nicht raten.
- **Eichprobe ist rein synthetisch** (nachgebauter #709-Bestand). Die echte #709-Heilung würde erst über den Tageslauf durchlaufen — der Selbsttest kann keine Aussage darüber treffen, welcher Echtfälle zustandsneutral ist.
- **Belegkette ist blinder Beweiskasten** nur in der Form geprüft — der echter Nachweiswert kommt erst auf den in den `data/code_schutz_belege.jsonl` enthaltenen `sha256`-Nachweise.
- **`--heilen` schreibt Inhalte** — dies ist ein bewusster Schreib-Pfad (nachweisbar + nachgemessen + Rollback + PR). Es wird in keinem Fall auf `main` gemerged — H-02-Vertrag — und der Heiler selbst ist ein **offline** Transform-Ausdruck ohne Netz-Zugriff, keine HTTP-Aufrufe, keine Dateibeneigung.
- **`--pruefen` ist nur eine Mission** — kann keinen Schreib-Beweis-Pfad erreichen. Sicherheits-Wache nimmt nur `--wache` (offline) und `--selftest` (offline); der Heil-Workflow nimmt `--heilen` (mitschrieben + PR).

**Konkretes Betriebs-Runbook:** Der Heil-Workflow läuft täglich; der Mensch konsultiert den erzeugten Heilungs-PR, setzt ihn `--wait`, merget ihn regulär. Falls kein PR für eine Befund-ID offen ist: nichts zu tun — der Heil-Bestand ist belegt.
