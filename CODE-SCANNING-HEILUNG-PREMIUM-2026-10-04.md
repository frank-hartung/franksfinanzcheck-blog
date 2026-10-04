# Code-Scanning-Heilung Premium – 2026-10-04

**Ausgangslage:** 50 offene Alerts unter `github.com/frank-hartung/franksfinanzcheck-blog/security/code-scanning` · **Ursache:** CodeQL-Default-Setup (automatisch aktiviert, analysiert Python 7,7 MB + JavaScript 1,5 MB) · **Ziel:** dauerhaft null Alerts – behoben auf Code-Ebene, abgesichert durch eine eigene Pipeline mit PR-Gate.

> Dies ist der Wahrheitsort für die Code-Scanning-Strategie. Was hier steht, gilt bis ein neuer datierter Abschnitt es ablöst. Die Maschine setzt das Gate durch (`CodeQL-Sicherheitswache`, `.github/workflows/codeql.yml`); sie entscheidet fachlich nie.

## 1 · Warum die Alerts da waren – und wie sie exakt reproduziert wurden

Das Repo hat keinen CodeQL-Workflow – die Alerts stammen aus dem **Default-Setup**, das GitHub für öffentliche Repos einschaltet. Es läuft unsichtbar auf `main`, mit der Standard-Query-Suite für JavaScript und Python.

Für die Heilung wurde der Bestand **exakt reproduziert** (nicht geraten): Ein Workflow auf dem Arbeitsbranch lief CodeQL mit derselben Standard-Suite und gab die SARIF-Ergebnisse als PR-Kommentar aus (PR #569, Lauf `Arena CodeQL Reproduktion`). Ergebnis: **49 Fundstellen, 13 JavaScript + 36 Python** – deckungsgleich mit den ~50 Alerts der Security-Tab (Differenz: Laufzeit-Versatz).

## 2 · Befund-Klassifikation – jede Fundstelle, eine Entscheidung

Grundsatz: **kein Alert wird weggeklickt.** Jede Fundstelle wurde einzeln gelesen und bekam genau eine von zwei Behandlungen:

**A) Echter Fix im Code** – wo ein reales Muster steckte (28 Fundstellen):

| Regel | Funde | Fundort | Fix |
|---|---|---|---|
| `js/xss` | 1 | `static/pinterest-oauth.html` | URL-Werte (`code`, `error_description`) fließen nur noch als fertige `createTextNode`-Knoten in die DOM-Helfer – nie als Strings |
| `js/xss-through-dom` | 3 | `static/premium/ff-nl-praef.js`, `ff-voice.js` (×2) | URL-Wächter `sichererLink()`/`istSichereUrl()`: Schema-Prüfung via `new URL()` – nur `https:`/`http:` landet in `href`/`src` |
| `js/path-injection` | 4 | `e2e/server.mjs` | Pfad-Gefängnis: `path.resolve` + Vergleich **mit Verzeichnis-Trenner** (Geschwister-Verzeichnis-Trick geschlossen), malformed decode → 400 |
| `js/incomplete-url-substring-sanitization` | 1 | `e2e/helpers.mjs` | Exakter Origin-Vergleich (`new URL().origin`) statt `startsWith`-Präfix |
| `js/incomplete-multi-character-sanitization` | 2 | `scripts/hugo_shortcodes.mjs`, `ff_voice_qa_lib.mjs` | Tag-Strip entfernt auch unvollständige Tags (`<[^>]*>?`) – kein `<script`-Fragment überlebt |
| `js/double-escaping` | 2 | `scripts/hugo_shortcodes.mjs`, `static/premium/ff-voice.js` | Entitäten in EINEM Durchlauf, `&amp;` per Lookahead ausgenommen und zuletzt dekodiert – `&amp;lt;` wird nie doppelt entschlüsselt (wortgleich in `scripts/ff_voice_backends.py`) |
| `py/incomplete-url-substring-sanitization` | 11 | `newsletter_zustellbarkeit.py` (8), Tests (2), `quality_score.py` | Host-exakter Wächter `ist_resend_api()` (Schema + Host via `urlsplit`) bzw. Muster-Suche – `https://api.resend.com.böse.example` besteht nie wieder als „Resend“ |
| `py/clear-text-logging-sensitive-data` | 1 | `scripts/pinterest_auth.py` | Datenfluss-Hygiene: Scope-Ausgabe aus der API-Antwort (`resp`), nie aus dem Secret-tragenden `data`-Dictionary |
| `py/path-injection` | 3 | `scripts/n8n_bridge.py` | Webhook-Pfade laufen nur noch durch `whisper_engine.pruefe_audio_pfad()` (Kanon + erlaubte Wurzeln, `None` statt rohem Pfad); Draft-Slug über Whitelist `[^\w-]+` |
| `py/redos` | 3 | `affiliate_integrity_gate.py`, `seo_audit.py`, `fix_spaces.py` | Linearisierte, semantisch äquivalente Muster – jede Änderung empirisch auf dem gesamten Content-Korpus verifiziert (0 Differenzen; ein dokumentierter Grenzfall) |
| `py/polynomial-redos` | 1 | `whisper_engine.py` | Possessives `\s++` (semantisch identisch, da die Folgeklasse kein Leerraum ist) |
| `py/bad-tag-filter` | 1 | `layout_audit.py` | `</script\s*>` – End-Tags mit Leerraum werden erkannt (echter Phantom-Link-Bug) |
| `py/insecure-protocol` | 1 | `watchdog_check4_tls.py` | Explizites `ctx.minimum_version = TLSv1_2` – der TLS-Watchdog toleriert selbst kein TLS 1.0/1.1 mehr |
| `py/overly-large-range` | 3 | `emoji_guard.py`, `brand_guard.py`, `social_gate.py` | Emoji-Klassen kanonisiert: disjunkt, explizit escapte Grenzen (z. B. lag `1F600–1F64F` komplett in `1F300–1F6FF`); Semantik per Test nachgewiesen |

**B) Begründete Inline-Ausnahme** – wo CodeQLs Namens-Heuristik anschlägt, aber nachweislich **kein Secret-Wert** fließt (17 Fundstellen): `secrets_age_guard.py` (4×), `editorial_scorecard.py` (2×), `governance_contract.py` (3× + 1× C10-Quelltextsuche), `social_preflight.py` (1×), `affiliate_marketer.py` (1× Selftest-Assertion). Jede trägt einen `# codeql[regel-id]`-Kommentar **mit Begründung im Code** – versioniert, begutachtbar, und weg, sobald die Stelle refaktoriert wird. Beispiele: Die Ausgaben der Secrets-Wache nennen Variablen-**Namen** („GROQ_API_KEY“), Labels und Tagesdaten – niemals Werte; die C9-Meldungen des Governance-Vertrags nennen Datei und Muster-Label, nie den Inhalt.

## 3 · Die dauerhafte Pipeline (ersetzt das Default-Setup)

`.github/workflows/codeql.yml` – **CodeQL-Sicherheitswache**:

- **pull_request auf main:** Analyse + hartes Gate – jedes Finding mit Security-Severity lässt den Lauf fehlschlagen. Kein Alert erreicht mehr `main` ungeschaut.
- **push auf main:** Analyse + SARIF-Upload in die Security-Tab (identische Kategorie wie bisher – alte Alerts werden aufgelöst statt doppelt geführt).
- **montags 03:30 UTC:** Freshness-Lauf – neue CodeQL-Queries treffen alten Code, bevor ein Angreifer ihn liest.
- **Konfiguration** `.github/codeql/codeql-config.yml`: Ausschlüsse nur mit Begründung (minifizierte Vendor-Libs, vendored Skill-Tooling unter `.claude/skills/impeccable`, `node_modules`). Eigener Produktionscode bleibt vollständig analysiert.

**Einmalige Umstellung nach Merge dieses PR** (Settings-API-Änderung braucht Admin-Rechte im UI):
Repo → **Settings → Code security and analysis → Code scanning (CodeQL) → Default setup → Disable**. Danach analysiert nur noch die Wache – mit Gate, Zeitplan und dokumentierter Konfiguration statt Black-Box-Automatik.

## 4 · Verifikation – der Beweis

1. **Repo-eigene Prüfungen:** Governance-Vertrag **alle 19 Regeln erfüllt** (`governance_contract.py --quick`), Whisper-Engine-Selbsttest, Secrets-Wache, Scorecard, ff-voice-backends 109/109, affiliate-integrity & marketer, newsletter-Zustellbarkeit 70/70, fix_spaces 40/40, Voice-/TOC-Node-Tests grün.
2. **Verifikationslauf:** Die CodeQL-Sicherheitswache läuft als PR-Check auf diesem Pull Request – Bilanz muss `0 Security-Fundstellen` lauten. Der Repro-Workflow bestätigt parallel die Gesamtzahl (Ziel: 0).
3. **Äquivalenz-Beweise der Regex-Umbauten:** alte vs. neue Muster über den kompletten `content/`-Korpus + synthetische Grenzfälle (siehe Abschnitt 2).

## 5 · Runbook – wenn die Wache künftig anschlägt

1. **Lesen, nicht wegklicken:** Alert in der Security-Tab öffnen, Pfad und Datenfluss ansehen.
2. **Echter Fund → Code fixen** (Muster oben in Abschnitt 2 als Referenz). Ein Fix ohne Verständnis ist kein Fix.
3. **Werkzeug überschätzt → Inline-Ausnahme** `# codeql[regel-id]` mit Begründungssatz direkt an der Stelle – niemals „Dismiss“ ohne versionierte Spur.
4. **Neues Muster → hier dokumentieren:** neuer datierter Abschnitt, wenn eine neue Regelklasse auftaucht.
5. **Lieferanten-Code (Theme, Skill, Vendor) nie lokal patchen** – Ausschluss in `codeql-config.yml` prüfen bzw. Upstream melden.
