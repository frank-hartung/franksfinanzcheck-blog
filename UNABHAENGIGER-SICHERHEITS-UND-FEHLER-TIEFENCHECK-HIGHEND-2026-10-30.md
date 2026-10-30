# Unabhängiger Sicherheits-, Logik- und Infrastruktur-Tiefencheck (Highend-Agentur-Audit)

**Datum:** 30.10.2026  
**Geprüftes Repository:** `frank-hartung/franksfinanzcheck-blog` (`franksfinanzcheck.de`)  
**Basis-Commit:** `7e76809` (`main`) · **Arbeitszweig:** `arena/5a4f2599-franksfinanzcheck-blog`  
**Umfang:** ~609 Python-Module (`scripts/`, `tools/`), 88 JavaScript-/MJS-/Worker-Module (`newsletter-worker/`, `cloudflare/`, `static/premium/`, `e2e/`, `tools/`), 97 GitHub-Actions-Workflows (`.github/workflows/`), 6 Node-Lockfiles, 5 Python-Anforderungsdateien, Docker-/n8n-/Whisper-Stack (`tools/n8n/`, `n8n/`) sowie 13 Shell-Skripte.

---

## 1. Gesamturteil (Management Summary)

Das Repository besitzt bereits eine außergewöhnlich reife Sicherheits- und Governance-Architektur: lückenloses SHA-Pinning aller GitHub Actions, Hash-Pinning in `requirements-ci.txt`, **0 bekannte CVEs** über sämtliche Python- und npm-Abhängigkeiten (`pip-audit`, `npm audit`, `abhaengigkeits_wache.py`), strikte Trennung von Lese- und Schreibschlüsseln im Cloudflare-Newsletter-Worker, konstante Zeitvergleiche für Geheimnisse sowie ein kryptografisches SHA-256-Integritätssiegel über 50 Kerndateien (`data/integrity_lock.json`).

Durch die Kombination **unabhängiger Open-Source-Scanner** (**Zizmor v1.31.1**, **Bandit v1.9.4**, **Ruff**, **ESLint + `eslint-plugin-security`**, **`pip-audit`**, **`npm audit`**) mit einer **manuellen Quelltext-Tiefenprüfung** wurden dennoch **echte, produktionsrelevante Fehler und Sicherheitslücken** identifiziert, von Fehlalarmen getrennt und direkt im unversiegelten Bestand dauerhaft behoben:

1. **Kritischer Laufzeitfehler (`F823` / `UnboundLocalError`) in `scripts/engine_generate.py`:** Ein lokales `import glob, re` in Zeile 248 überschattete das globale `import re` (Zeile 36) im gesamten Funktionskörper. Sobald `pin_description` befüllt war, warf Zeile 229 deterministisch `UnboundLocalError: cannot access local variable 're'`, was in Zeile 237 still geschluckt wurde und den restlichen SEO-Preflight übersprang.
2. **SSRF-, `file://`-LFI- und Speichererschöpfungs-Lücken in Recherche-/Feed-/Playwright-Adaptern:** Externe Abrufe über `urllib.request.urlopen()` (`werkbank_adapters.py`, `schaltwerk_triggers.py`, `faktenfrische.py`, `agent_reach_research.py`, `belegketten_wache.py`) sowie die Playwright-Brücke (`tools/werkbank/render.mjs`) akzeptierten zuvor beliebige Schemata (`file://`) bzw. ungeprüfte Weiterleitungen auf Loopback-/Privat-/Cloud-Metadaten-Netze (`127.0.0.1:5678` n8n, `:8765` Whisper, `169.254.169.254`). Neu abgesichert durch **`scripts/net_safety.py`** (inkl. Cross-Zone-Redirect-Sperre) und Request-Interception in **`tools/werkbank/render.mjs`**.
3. **XML-Entity-Expansion (Billion Laughs) & XXE-Härtung:** Sechs Sitemap-/RSS-Parser nutzten ungehärtetes `xml.etree.ElementTree`. Neu abgesichert durch **`scripts/safe_xml.py`** (deterministische `pyexpat`-Vorprüfung gegen `<!ENTITY`, interne DTD-Subsets und externe System-/Public-Referenzen + 50-MiB-Größenlimit).
4. **URL-Host-Spoofing in `scripts/pinterest_plan_guard.py`:** Ad-hoc-Prüfung mittels `.lstrip("www.")` (`B005` entfernt Zeichenmenge `{w, .}`) und Teilstring-Vergleich (`EIGENE_DOMAIN not in host`) ließ Domains wie `franksfinanzcheck.de.angreifer.tld` oder `evilfranksfinanzcheck.de` passieren. Umgestellt auf die kanonische SSOT `scripts/url_host.py` + `urlsplit`.
5. **Defekter Keyword-Splitter & JS-/Browser-Fehler:** In `scripts/keyword_optimizer.py` trennte der Raw-String `r"[,\\n;]"` KI-Antworten an jedem Buchstaben **`n`** statt am Zeilenumbruch `\n`. Im SEO-Cockpit (`tools/seo-cockpit/app.js`) überschrieb ein doppelter Objektschlüssel `'description-length'` den 155-Zeichen-Regeltext. In `static/premium/ff-voice.js` blieb ein abgelehntes `navigator.clipboard.writeText()`-Promise ungehandhabt; in `scripts/ff_voice_browser_test.mjs` referenzierte der `catch`-Pfad eine nicht im Scope liegende Variable `page` und ließ Browser/Server offen.
6. **GitHub-Actions-Härtung (97 Workflows) & Container-Minimierung:** Sämtliche verbleibenden `${{ ... }}`-Ausdrücke in `run:`-Blöcken (16 Workflows) wurden vollständig in `env:` überführt (**0 Template-Injection-Stellen im gesamten Repo**). Multi-Job-Workflows (`codeql.yml`, `redaktionelle-ymyl-pruefung.yml`, `alert-on-failure.yml`) erhielten striktes Job-Level-Least-Privilege (**0 `excessive-permissions`-Befunde in Zizmor**). `tools/n8n/Dockerfile.whisper` entfernt `git` und `build-essential` nun in derselben Image-Schicht.

Alle **50 SHA-256-versiegelten Kerndateien** (`data/integrity_lock.json`) blieben unangetastet (`integrity_guard.py --gate` grün).

---

## 2. Eingesetzte unabhängige Prüfwerkzeuge

| Ebene | Werkzeug | Geprüfter Bereich | Ergebnis (Kurzfassung) |
|---|---|---|---|
| **GitHub Actions SAST** | **Zizmor v1.31.1** | Alle 97 `.github/workflows/*.yml` | `template-injection` in `run:` **0**, `excessive-permissions` **0** (nach Härtung) |
| **Python Security AST** | **Bandit v1.9.4** | ~609 Dateien in `scripts/` & `tools/` | 0 Parse-Fehler; `B314`/`B405` (XML) & `B324` (FIPS-Hash) im unversiegelten Code **0** |
| **Python Bug & Security** | **Ruff** (`F`, `B`, `S`, `PLE`, `RUF`) | Alle Python-Module & Tests | `F823`, `F821`, `F601`, `F811`, `B005`, `B020`, `B023` (Prod), `B025`, `B034`, `S314`, `PLE2515` **0** |
| **JavaScript / Workers** | **ESLint v9** + `eslint-plugin-security` | 88 JS/MJS/CJS-Dateien (`cloudflare/`, `newsletter-worker/`, `static/`, `tools/`, `scripts/`) | Doppelte Keys, unaufgelöste Scope-Referenz, unbehandeltes Clipboard-Promise & Regex-Überlappung behoben |
| **Python Supply Chain** | **`pip-audit`** (PyPI OSV) | Alle 5 `requirements*.txt` + `Dockerfile.whisper`-Pins | **0 bekannte Schwachstellen (CVEs)** |
| **Node Supply Chain** | **`npm audit`** | Alle 6 `package-lock.json` | **0 bekannte Schwachstellen (CVEs)** |
| **Shell & Haus-Wachen** | `bash -n`, `integrity_guard`, `wachen_vertrag`, `redos_guard`, `url_substring_guard`, `clear_text_logging_guard`, `n8n_schutz_wache` | Gesamtes Repository | **100 % grün** |

---

## 3. Triage: Echte Befunde vs. Fehlalarme (False Positives)

Eine professionelle Sicherheitsprüfung unterscheidet reale Risiken von generischem Scanner-Rauschen:

- **Als Fehlalarm / bewusste Architektur verworfen (nicht kaputtoptimiert):**
  - **Zizmor `artipacked` (93×) & `self-repository` (51×):** Standard-Hinweis auf `persist-credentials` bei `actions/checkout`; viele Bot-Workflows im Repo führen bewusst signierte Nachheilungs-Pushes über `scripts/git_sync.sh` aus.
  - **Zizmor `dangerous-triggers` (6× `workflow_run` / `pull_request_target`):** Bereits architektonisch sauber entschärft – z. B. checkt `vorgangs-abschluss.yml` ausdrücklich `github.event.repository.default_branch` statt PR-Code aus und übergibt PR-Nummern über `env:`; `alert-on-failure.yml` wertet ausschließlich den Default-Branch aus.
  - **Bandit `B108` in Docstrings / CLI-Hilfetexten / Offline-Selbsttests:** Zahlreiche Treffer betrafen reine Dokumentationsstrings (`--out /tmp/...`) oder `tempfile.TemporaryDirectory()`-Tests. Nur der echte Laufzeit-Schreibpfad in `scripts/fristen_check.py` (`/tmp/fristen_issue_body.md`, `/tmp/fristen_comment.md`) war real und wurde auf `tempfile.NamedTemporaryFile` umgestellt.
  - **Bandit `B310` auf festen HTTPS-API-Endpunkten** (z. B. `api.pinterest.com`, `api.github.com`, `searchconsole.googleapis.com`): Dort ist das Zielschema hart auf `https://` kodiert; gehärtet wurden gezielt alle Stellen mit variablen/externen Feed-, Such- oder Zitat-URLs.
  - **`newsletter-worker/src/index.js:922` (`let kv_ok = false`):** Rein defensive Vorbelegung vor `try/catch`; zudem Teil des versiegelten Bestands – bewusst unverändert belassen.
- **Versiegelter Bestand (`data/integrity_lock.json`, 50 Dateien):**
  - In versiegelten Dateien (`scripts/affiliate_marketer.py`, `scripts/internal_linker.py`, `scripts/plagiat_guard.py`, `scripts/stil_guard.py`) meldete Ruff lediglich kosmetische/defensive Kleinigkeiten (z. B. doppelte Stoppwörter in Sets `B033` oder `B023`-Closures, die sofort in derselben Iteration ausgewertet werden). Gemäß Governance-Regel aus `CLAUDE.md` wurden versiegelte Dateien **nicht ohne Not angetastet**.

---

## 4. Durchgeführte Reparaturen und Härtungen im Detail

### Arbeitspaket 1 — Kritische Laufzeit-, Logik- und JavaScript-Fehler
- **`scripts/engine_generate.py` (`F823` Kritisch + `B033`):**
  - *Befund:* `re` war in Zeile 36 global importiert, wurde aber in Zeile 248 innerhalb derselben Funktion durch `import glob, re` als lokale Variable markiert. Zeile 229 (`re.sub(...)` auf `pin_description`) warf dadurch vor Erreichen von Zeile 248 `UnboundLocalError`, der im umgebenden `except Exception:` (Zeile 237) verschluckt wurde.
  - *Reparatur:* `import glob` auf Modulebene gehoben, lokales `import glob, re` entfernt; doppeltes Stoppwort `"auch"` in Zeile 923 bereinigt.
- **`scripts/keyword_optimizer.py` (Defektes Keyword-Splitting + `B005` + `B023`):**
  - *Befund:* `re.split(r"[,\\n;]", raw)` interpretierte `\\n` im Raw-String als literalen Backslash **oder Buchstaben `n`**. Mehrzeilige KI-Vorschläge wie `"Nebenkosten senken\nStromtarif wechseln"` wurden an jedem `n` zerschnitten (`"Nebe"`, `"koste"`, `" se"`, ...).
  - *Reparatur:* Korrigiert auf `re.split(r"[,\n;]", raw)`, Anführungszeichen-Strip dedupliziert (`.strip("\"'„“”‚‘")`) und Schleifenvariable `_fm=fm` in `get()` gebunden.
- **`tools/seo-cockpit/app.js` & `tools/seo-cockpit/app.test.cjs` (Doppelter Schlüssel `'description-length'`):**
  - *Befund:* `'description-length': 'Beschreibung auf 155 Zeichen kürzen'` wurde in derselben Objekt-Deklaration durch `'description-length': 'Beschreibung redaktionell prüfen'` überschrieben – das konkrete 155-Zeichen-SERP-Limit ging im UI verloren.
  - *Reparatur:* Überschreibung entfernt, `RULE_LABELS` exportiert und durch Unit-Test in `app.test.cjs` abgesichert (10/10 Tests grün).
- **`static/premium/ff-voice.js` & `scripts/ff_voice_browser_test.mjs`:**
  - *Reparatur (`ff-voice.js`):* Asynchrones `navigator.clipboard.writeText()` mit `.then(ok, fallbackCopy)` abgesichert (verhindert Unhandled-Promise-Rejection und falsche Erfolgsmeldung bei verweigertem Clipboard-Recht; synchroner Test-Hook `__ff_voice_copied` bleibt erhalten); überlappendes Quantorenmuster in `labelAround()` entschärft; doppelte `var`-Deklarationen bereinigt (265/265 + 48/48 DOM-Tests grün).
  - *Reparatur (`ff_voice_browser_test.mjs`):* `activeServer`, `activeBrowser` und `activePage` auf Modulebene geführt, damit der Fehlerpfad (`main().catch(...)`) den Seitenzustand ohne `ReferenceError: page is not defined` auslesen und Browser + HTTP-Server zuverlässig schließen kann.

### Arbeitspaket 2 — Kanonische URL-Host-Prüfung statt Teilstring-/lstrip-Heuristik
- **`scripts/pinterest_plan_guard.py` (`B005` + Host-Spoofing + Import-Seiteneffekt):**
  - *Befund:* `host = ...lstrip("www.")` schnitt einzelne Zeichen `{w, .}` ab (z. B. `www.wuestenrot.de` → `uestenrot.de`) und `EIGENE_DOMAIN not in host` akzeptierte `franksfinanzcheck.de.angreifer.tld` sowie `evilfranksfinanzcheck.de`. Zudem führte ein `import pinterest_plan_guard` sofort den CLI-Hauptlauf inkl. `sys.exit()` aus.
  - *Reparatur:* Neue Funktion `pruefe_ziel_url()` auf Basis von `urllib.parse.urlsplit` + `scripts/url_host.py` (`host_von`, `ist_host_oder_subdomain`), CLI-Hauptlauf sauber in `main()` gekapselt und `_selftest()` um 4 Spoofing-Gegenproben erweitert.

### Arbeitspaket 3 — Zentraler Transportschutz gegen SSRF, `file://`-LFI & OOM
- **Neues Modul `scripts/net_safety.py` (Stdlib, 0 Fremdpakete, `--selftest` mit 21 Fällen):**
  - Erzwingt `http`/`https`, weist Steuerzeichen (`\r`, `\n`, `\x00`) ab, sperrt Link-Local-/Cloud-Metadaten (`169.254.0.0/16`, `fe80::/10`, `metadata.google.internal`), RFC1918, CGNAT (`100.64.0.0/10`), ULA (`fc00::/7`), Multicast, `0.0.0.0`/`::` sowie IPv4-gemappte IPv6-Adressen (`::ffff:127.0.0.1`), prüft jedes 3xx-Redirect-Ziel erneut (**inkl. harter Cross-Zone-Sperre extern → Loopback**, selbst wenn für direkte lokale Dienste `erlaube_loopback=True` aktiv ist) und deckelt Antworten auf `max_bytes` (Standard 4 MiB). Respektiert Monkeypatching von `urllib.request.urlopen` in bestehenden Unit-Tests (`test_werkbank.py`).
- **Verdrahtet in:** `scripts/werkbank_adapters.py` (`_hole`, `suche_duckduckgo`, `lies`, `browser_beweis`, `konnektor_ausfuehren`), `scripts/schaltwerk_triggers.py` (`trigger_rss`), `scripts/faktenfrische.py` (`sammle_rss`, `sammle_web`), `scripts/agent_reach_research.py` (`sammle_web`) und `scripts/belegketten_wache.py` (`abruf_http`).
- **Playwright-Brücke `tools/werkbank/render.mjs` (inkl. `--selftest` mit 14 Proben):**
  - Vorab-Prüfung + `context.route('**/*', ...)` blockiert Nicht-`http(s)`-Schemata, Loopback, Privatnetze, CGNAT und Cloud-Metadaten inkl. DNS-Auflösung und WHATWG-Hex-Normalisierung (`[::ffff:7f00:1]`), sodass fremdes Seiten-JS lokale Dienste (`n8n :5678`, `Whisper :8765`, `Bridge :5680`) nicht abtasten kann.

### Arbeitspaket 4 — Deterministische XML-Härtung gegen Billion Laughs & XXE
- **Neues Modul `scripts/safe_xml.py` (Stdlib `pyexpat`-Vorprüfung, `--selftest` mit 6 Fällen):**
  - Da CPythons C-Beschleuniger `_elementtree` eigene Expat-Handler setzt, prüft `safe_xml.py` jedes XML-Dokument vor dem Baumaufbau deterministisch über `xml.parsers.expat.ParserCreate()` und blockiert jegliche `<!ENTITY ...>`-Deklaration, interne DTD-Subsets sowie externe `SYSTEM`/`PUBLIC`-Referenzen bei einem Größenlimit von 50 MiB (Google-Sitemap-Protokollgrenze).
- **Verdrahtet in:** `scripts/publication_check.py`, `scripts/indexierbare_seiten.py`, `scripts/gsc_abdeckung.py` (alle 3 Parser-Stellen), `scripts/seo_cockpit.py`, `scripts/spam_guard.py` und `tools/seo-spider/crawler.py`.

### Arbeitspaket 5 — GitHub-Actions-Workflows (97 Dateien) & Docker-Härtung
- **Vollständige Eliminierung von `${{ ... }}` in `run:`-Blöcken (16 Workflows → 0 Verstöße im gesamten Repo):**
  - Gehärtet: `affiliate-health.yml`, `affiliate-integrity-daily.yml`, `brand-surface-guard.yml`, `codeql.yml`, `content-engine-v2.yml`, `deploy.yml`, `gsc-import.yml`, `link-check.yml`, `n8n-schaltwerk-bridge.yml`, `newsletter-daily.yml`, `pinterest-restart.yml`, `vorgangs-abschluss.yml`, `web-vitals-woche.yml`, `werkbank.yml`.
- **Job-Level Least Privilege (`excessive-permissions` → 0):**
  - `codeql.yml`: Top-Level `contents: read`; Schreibrechte (`security-events: write`, `pull-requests: write`) ausschließlich auf Job `analyze` (`klartext-wache`, `url-wache`, `redos-wache` laufen strikt read-only).
  - `redaktionelle-ymyl-pruefung.yml`: Top-Level `contents: read`; `issues: write` ausschließlich auf Job `belegketten`.
  - `alert-on-failure.yml`: Top-Level `contents: read`; `issues: write` + `actions: read` explizit auf Job-Ebene.
- **Container-Härtung (`tools/n8n/Dockerfile.whisper`):**
  - `git` und `build-essential` werden unmittelbar nach `pip install` in derselben `RUN`-Schicht per `apt-get purge -y --auto-remove` entfernt; im Laufzeit-Image unter `USER whisper` (UID 10001) verbleiben nur `ffmpeg` und `curl`.

### Arbeitspaket 6 — Python-Sicherheits- & Qualitäts-Hygiene (Unversiegelter Bestand)
- **Sichere Temp-Dateien (`B108`):** `scripts/fristen_check.py` nutzt `tempfile.NamedTemporaryFile(..., delete=False)` mit garantiertem `unlink(missing_ok=True)` im `finally`-Block statt fixer Pfade unter `/tmp/`.
- **FIPS-konforme nicht-kryptografische Hashes (`B324`):** `usedforsecurity=False` ergänzt in `scripts/affiliate_intent_guard.py`, `scripts/alert_router.py`, `scripts/social_dialog.py` und `scripts/social_planner.py`.
- **Weitere Code-Defekte bereinigt:**
  - `scripts/emoji_guard.py`: doppelter Dict-Schlüssel `"â€ž"` (`F601`) entfernt und unsichtbare Zero-Width-Literale explizit als `\u200b`–`\ufeff` maskiert (`PLE2515`).
  - `scripts/tests/test_faktenfrische_763.py`, `823.py`, `911.py`: doppelter Schlüssel `'‑'` (`\u2011`, `F601`) bereinigt.
  - `scripts/dom_audit.py`: `maxsplit=1` als Keyword-Argument bei `re.split` (`B034`).
  - `scripts/seo_paritaet_ci.py`: Überschreiben des Iterables `posten` durch die eigene Schleifenvariable behoben (`B020`).
  - `scripts/kennzahlen_radar.py`: doppelter `except OSError:`-Zweig entfernt (`B025`).
  - `scripts/bot_watchdog.py`: redundantes lokales `import tempfile` entfernt (`F811`).
  - **Alle 12 `B023`-Schleifen-Closures** in unversiegelten Produktionsskripten (`affiliate_link_check.py`, `bestand_gate.py`, `cwv_feld_wache.py`, `meta_optimizer.py`, `newsletter_digest.py`, `pinterest_duplicate_guard.py`, `pinterest_pin_text_sync.py`, `publish_gate.py`, `saisonaler_hero_refresh.py`, `spam_guard.py`, `spellcheck.py`, `update_articles.py`) gebunden sowie unveränderliche Klassenattribute (`frozenset`) in `h1_wache.py` und `themenwelten_guard.py` (`RUF012`) und Set-Duplikate (`B033`) in `generate_drafts.py`, `reserve_topics.py`, `spellcheck.py`, `textverstaendnis_guard.py` bereinigt.

---

## 5. Messbare Vorher-/Nachher-Bilanz (Unversiegelter Produktionsbestand & Workflows)

| Prüfkategorie / Regelklasse | Vorher | Nachher | Status |
|---|---:|---:|---|
| **Bekannte CVEs (`pip-audit` + `npm audit` + `abhaengigkeits_wache`)** | 0 | **0** | Grün bestätigt |
| **Zizmor `template-injection` (`${{ }}` in `run:` über 97 Workflows)** | 16 Workflows | **0 Workflows** | 100 % behoben |
| **Zizmor `excessive-permissions` (über 97 Workflows)** | 3 Workflows | **0 Workflows** | 100 % behoben |
| **Python `F823` (`UnboundLocalError` vor Zuweisung)** | 1 (`engine_generate.py`) | **0** | 100 % behoben |
| **Bandit/Ruff `B314`/`B405`/`S314` (ungehärtetes XML)** | 15 Stellen | **0** | 100 % behoben |
| **Bandit `B324` (`md5`/`sha1` ohne `usedforsecurity=False`)** | 4 Stellen | **0** | 100 % behoben |
| **Ruff `F601` (doppelte Dictionary-Schlüssel)** | 4 Stellen | **0** | 100 % behoben |
| **Ruff `B005` (fehlerhaftes Multi-Char-`strip`/`lstrip`)** | 3 Stellen | **0** | 100 % behoben |
| **Ruff `B020` / `B025` / `B034` / `F811` / `PLE2515`** | 7 Stellen | **0** | 100 % behoben |
| **Ruff `B023` (ungebundene Schleifen-Closures in Prod-Skripten)** | 18 Stellen | **0** | 100 % behoben |
| **SHA-256-Integritätssiegel (`data/integrity_lock.json`, 50 Dateien)** | 50/50 intakt | **50/50 intakt** | Unangetastet grün |

---

## 6. Durchgeführte Verifikationsnachweise

Alle neuen Schutzmodule, Regressionstests und bestehenden Haus-Wachen wurden ausgeführt und bestanden fehlerfrei:

- `python3 scripts/safe_xml.py --selftest` → **6/6 Fälle grün** (Sitemap, Billion-Laughs, XXE, externe DTD, Größenlimit, Datei)
- `python3 scripts/net_safety.py --selftest` → **21/21 Fälle grün** (Schema, LFI, Cloud-Metadaten, RFC1918, Loopback, Cross-Zone-Redirect)
- `node tools/werkbank/render.mjs --selftest` → **14/14 SSRF-/Schema-Proben grün** (inkl. `[::ffff:7f00:1]`)
- `python3 -m unittest scripts/tests/test_unabhaengiger_tiefencheck.py` → **11/11 Regressions- & Sabotage-Tests grün**
- `python3 scripts/pinterest_plan_guard.py --selftest` → **P6/P7/P8 inkl. Host-Spoofing-Proben grün**
- `python3 scripts/integrity_guard.py --gate` → **50/50 versiegelte Kerndateien exakt auf Stand `7e76809`**
- `python3 scripts/skript_syntax_wache.py` → **599 Dateien grün**
- `python3 scripts/wachen_vertrag.py` → **361 Skripte geprüft, 0 Funde**
- `python3 scripts/url_substring_guard.py` → **1.147 Dateien, 0 Funde**
- `python3 scripts/clear_text_logging_guard.py` → **609 Python-Dateien, 0 Funde**
- `npm run test:sicherheit` → **alle Selbsttests + 269 Unit-Tests + Offline-Wachen grün**
- `npm run test:redos` → **ReDoS-Wache (609 Dateien, 0 Funde) + 12 Selbsttests + Unit-Tests grün**
- `python3 scripts/selftest_ki.py --trap-workflows` → **sämtliche Workflow-Skript-Selbsttests grün**
- `python3 -m unittest scripts/tests/test_werkbank.py scripts/tests/test_schaltwerk.py` → **106/106 Tests grün**
- `python3 -m unittest scripts/tests/test_workflow_yaml.py scripts/tests/test_deploy_cache_isolation.py scripts/tests/test_deploy_gate_paths.py scripts/tests/test_linkcheck_reporting.py scripts/tests/test_workflow_js_wache.py scripts/tests/test_actions_version_guard.py` → **47/47 Tests grün**
- `node --test tools/seo-cockpit/app.test.cjs` (**10/10**), `node scripts/ff_voice_functional_test.mjs` (**265/265**), `node scripts/ff_heading_glyph_guard_test.mjs` (**48/48**), `newsletter-worker` (**93/93**), `cloudflare/ki-assistent` (**17/17**), `cloudflare/klick-zaehler` (**34/34**), `tools/seo-spider` (**13/13**) → **alle grün**.

---

## 7. Optionale Folgeschritte für den Betreiber

1. **GitHub Default CodeQL Setup prüfen (einmalig im GitHub-UI):** Wie im Kopf von `.github/workflows/codeql.yml` dokumentiert, sollte unter *Settings → Advanced Security → CodeQL analysis* das GitHub-Default-Setup deaktiviert sein, damit ausschließlich die eigene `CodeQL-Sicherheitswache` SARIF-Berichte hochlädt.
2. **Kosmetische Set-/Closure-Pflege in versiegelten Dateien nur bei regulärem Siegel-Update:** Falls künftig ohnehin eine geplante Änderung mit `python3 scripts/integrity_guard.py --heal` an `scripts/affiliate_marketer.py` oder `scripts/internal_linker.py` erfolgt, können dort optional die harmlosen Set-Duplikate (`B033`) mitbereinigt werden; ein eigenes Aufbrechen des Siegels dafür wäre unverhältnismäßig.
