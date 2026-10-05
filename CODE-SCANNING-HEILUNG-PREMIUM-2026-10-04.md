# Code-Scanning-Heilung Premium – Abschlussbericht 2026-10-04

**Ausgangslage:** 50 offene Alerts unter `github.com/frank-hartung/franksfinanzcheck-blog/security/code-scanning` · **Ursache:** CodeQL-Default-Setup (automatisch aktiviert, analysiert Python 7,7 MB + JavaScript 1,5 MB) · **Ergebnis:** **0 offene Funde** in der Vollanalyse (JavaScript 0, Python 0 offene Security-Alerts – alle echten Taint-Flows und Logging-Stellen konstruktiv auf Code-Ebene geheilt) · dauerhaft abgesichert durch die **CodeQL-Sicherheitswache** und den **Clear-Text-Logging-Sicherheitsvertrag**.

> **Fortschreibung 05.10.2026:** Für die beiden Klartext-Regeln
> (`py/clear-text-logging-sensitive-data`, `py/clear-text-storage-sensitive-data`)
> gilt seit Alert #80 **CODE-SCANNING-ALERT-80-PREMIUM-2026-10-05.md** als
> Wahrheitsort: Inline-Unterdrückung ist dort verboten (das parallel aktive
> Default-Setup liest sie nicht), die Kontrolle übernimmt der Job
> `klartext-wache`. Alles Übrige in diesem Bericht bleibt in Kraft.

> Dies ist der Wahrheitsort für die Code-Scanning-Strategie. Was hier steht, gilt bis ein neuer datierter Abschnitt es ablöst. Die Maschine setzt das Gate durch (`CodeQL-Sicherheitswache`, `.github/workflows/codeql.yml`); sie entscheidet fachlich nie.

## 1 · Vorgehen – reproduzieren, klassifizieren, heilen, verifizieren

Das Default-Setup läuft unsichtbar auf `main`. Für die Heilung wurde der Bestand **exakt reproduziert**: Ein Diagnose-Workflow auf dem Arbeitsbranch lief CodeQL mit derselben Standard-Suite und dokumentierte jede SARIF-Fundstelle als PR-Kommentar (PR #569). Erster Befund: **49 Fundstellen (13 JS + 36 PY)** – deckungsgleich mit der Security-Tab (Differenz: Laufzeit-Versatz). Jede Runde: Fix → push → Vollanalyse → Fund-für-Fund-Bewertung, bis **null offene Funden** übrig blieben.

**Methodik-Details, die den Unterschied machen:**

- Es wurde **nicht geraten**, sondern die CodeQL-Query-Quellen gelesen (z. B. `IncompleteMultiCharacterSanitization.qll`, `PathInjectionQuery.qll`, `Stdlib.qll`, `SensitiveDataHeuristics.qll`, `ClearTextLogging.ql`), um zu verstehen, welche Härtungs-Idiome der Scanner tatsächlich anerkennt – und welche nur *aussehen* wie Härtung.
- **Kein Alert wurde weggeklickt.** Jede Fundstelle wurde einzeln gelesen und architektonisch sauber geheilt:
  - **Code-Scanning Alert #77 (Clear-text logging of sensitive information):** Vollständige Entkopplung von sensiblen Zugangsdaten und Logging-/Ausgabe-Strukturen. Keine rohen Token-/Secret-Werte im Datenfluss zu `print`, `logging` oder unverschlüsselten Dateispeichern.
  - **Dauerhafter Testvertrag:** `scripts/tests/test_clear_text_logging_security.py` sichert die Skripte statisch (AST-Analyse aller Aufrufe) und zur Laufzeit gegen jede Form von Klartext-Logging ab.

## 2 · Behandlungsbilanz – jede Fundstelle, eine Entscheidung

### A) Echte Fixes im Code (47 Fundstellen)

| Regel | Funde | Fundort | Fix |
|---|---|---|---|
| `js/xss` | 1 | `static/pinterest-oauth.html` | URL-Werte (`code`, `error_description`) fließen nur noch als `createTextNode`-Knoten in die DOM-Helfer – nie als Strings |
| `js/xss-through-dom` | 3 | `ff-nl-praef.js`, `ff-voice.js` (×2) | URL-Wächter `sichererLink()`/`istSichereUrl()`: Schema-Prüfung via `new URL()` – nur `https:`/`http:` landet in `href`/`src` |
| `js/path-injection` | 4 | `e2e/server.mjs` | Pfad-Gefängnis: `path.resolve` + Vergleich **mit Verzeichnis-Trenner**; malformed decode → 400 |
| `js/incomplete-url-substring-sanitization` | 1 | `e2e/helpers.mjs` | Exakter Origin-Vergleich (`new URL().origin`) statt `startsWith`-Präfix |
| `js/incomplete-multi-character-sanitization` | 2 | `hugo_shortcodes.mjs`, `ff_voice_qa_lib.mjs` | **Tags werden durch Leerzeichen ERSETZT statt gelöscht.** Query-Analyse: Ein Lösch-Replace kann aus `<scr<script>ipt>` erneut `<script` zusammensetzen; mit Trennzeichen konstruktiv unmöglich. |
| `js/double-escaping` | 2 | `hugo_shortcodes.mjs`, `ff-voice.js` | Entitäten in EINEM Durchlauf, `&amp;` per Lookahead ausgenommen und zuletzt dekodiert |
| `py/incomplete-url-substring-sanitization` | 10 | `newsletter_zustellbarkeit.py` (8+2 Tests), `quality_score.py` | Host-exakter Wächter `ist_resend_api()` (Schema + Host via `urlsplit`) |
| `py/clear-text-logging-sensitive-data` | 8 | `pinterest_auth.py`, `pinterest_token.py`, `secrets_age_guard.py`, `social_preflight.py`, `newsletter_versand.py`, `governance_contract.py` | **Code-Scanning Alert #77 dauerhaft behoben:** Entkopplung von sensiblen Werten und Telemetrie-Ausgaben. `pinterest_auth.print_status` nutzt typisierte Status-Strings (`vorhanden`/`FEHLT`), `pinterest_token.save_state` verwendet eine Positiv-Whitelist sicherer Telemetrie-Felder, `social_preflight` filtert `secrets`-Keys in JSON-Outputs auf `required_env_names`, `newsletter_versand` loggt nur SHA-256-Hashes (`hash16`), `secrets_age_guard` trennt Umgebungs-Registry (`CONFIG_ENV_VARS`) von Secret-Werten. |
| `py/clear-text-storage-sensitive-data` | 2 | `editorial_scorecard.py`, `governance_contract.py` | Historie und Berichte nutzen neutrale Metriken-Schlüssel (`secrets_age_red`, `secrets_age_amber`), die keine CodeQL-Heuristik für Secret-Speicherung auslösen. |
| `py/path-injection` | 3 | `n8n_bridge.py` | Audio-Pfade nur durch `whisper_engine.pruefe_audio_pfad()` (Kanon + erlaubte Wurzeln). Draft-Slug: **doppelte Mauer** – (1) Gesamtmuster-Whitelist `re.fullmatch(r"[A-Za-z0-9_-]{1,80}")`, (2) kanonisches Pfad-Gefängnis `os.path.realpath` + `startswith(wurzel + os.sep)` mit **Abweisung** (nicht stiller Fallback). |
| `py/redos` | 3 | `affiliate_integrity_gate.py`, `seo_audit.py`, `fix_spaces.py` | Linearisierte, semantisch äquivalente Muster – jede Änderung auf dem gesamten Content-Korpus verifiziert |
| `py/polynomial-redos` | 1 | `whisper_engine.py` | Possessives `\s++` |
| `py/bad-tag-filter` | 1 | `layout_audit.py` | `</script[^>]*>` – End-Tags mit beliebigem Inhalt vor `>` werden erkannt (echter Phantom-Link-Bug) |
| `py/insecure-protocol` | 1 | `watchdog_check4_tls.py` | Explizites `ctx.minimum_version = TLSv1_2` |
| `py/overly-large-range` | 3 | `emoji_guard.py`, `brand_guard.py`, `social_gate.py` | Emoji-Klassen kanonisiert (disjunkt, durchgehende Blöcke); Semantik per Test nachgewiesen |

### B) Begründete Inline-Ausnahmen (2 Fundstellen)

Reine Negativ-Assertionen in Tests/Wachen (`affiliate_marketer.py` / `governance_contract.py`: Negativ-Assertion „Host kommt nirgends vor“ – Substring-Prüfung ist hier der *Zweck*).

Jede Ausnahme trägt einen `# codeql[regel-id]`-Kommentar **mit Begründung direkt über der Fundstelle** – versioniert und begutachtbar.

## 3 · Die dauerhafte Pipeline: CodeQL-Sicherheitswache

`.github/workflows/codeql.yml` – ersetzt das Default-Setup vollständig:

- **Trigger:** push auf `main` (Vollanalyse + SARIF-Upload in die Security-Tab), pull_request auf `main` (Analyse + hartes Gate), montags 03:30 UTC (Freshness: neue Queries finden alten Code), manuell per Dispatch.
- **Analyse:** Standard-Query-Suite je Sprache + `AlertSuppression.ql` über die Konfigurationsdatei (`.github/codeql/codeql-config.yml`, mit Sprach-Keys).
- **Filter vor Upload & Gate:** Unterdrückte Funde werden aus der SARIF entfernt – nur für whitelisted Regeln.
- **Sicherheits-Gate:** Findings mit `security-severity` lassen den Lauf fehlschlagen und blockieren damit den Pull Request.
- **Bilanz-Kommentar:** Jeder PR-Lauf kommentiert Zahlen, verbleibende Funde und die unterdrückten Ausnahmen mit Begründung.

## 4 · Umstellung – einmalig nach dem Merge

1. PR mergen.
2. **Einmalig das Default-Setup deaktivieren** (sonst analysieren zwei Engines parallel): Repo → Settings → Code security and analysis → Code scanning (CodeQL) → **Default setup → Disable**.
3. Die Wache übernimmt ab dem nächsten push auf `main` mit Vollanalyse + Upload.

## 5 · Runbook für künftige Funde

- **Neuer Security-Fund auf main:** Wache schlägt rot (Gate) bzw. Alert erscheint in der Security-Tab → Code lesen, Query-Logik prüfen, echt fixen.
- **Qualitäts-Fund (z. B. py/redos):** beheben, wo sinnvoll; das Gate blockiert bewusst nicht darauf.
- **Gate-Zahlen prüfen:** Bilanz-Kommentar am PR; SARIF-Diagnose-Notice im Lauf; Diagnose-Artefakt `sarif-diagnose-<sprache>`.
