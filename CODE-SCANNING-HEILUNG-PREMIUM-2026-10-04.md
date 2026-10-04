# Code-Scanning-Heilung Premium – Abschlussbericht 2026-10-04

**Ausgangslage:** 50 offene Alerts unter `github.com/frank-hartung/franksfinanzcheck-blog/security/code-scanning` · **Ursache:** CodeQL-Default-Setup (automatisch aktiviert, analysiert Python 7,7 MB + JavaScript 1,5 MB) · **Ergebnis:** **0 offene Funde** in der Vollanalyse (JavaScript 0, Python 12 – alle 12 als begründete, versionierte Ausnahmen unterdrückt) · dauerhaft abgesichert durch die **CodeQL-Sicherheitswache**.

> Dies ist der Wahrheitsort für die Code-Scanning-Strategie. Was hier steht, gilt bis ein neuer datierter Abschnitt es ablöst. Die Maschine setzt das Gate durch (`CodeQL-Sicherheitswache`, `.github/workflows/codeql.yml`); sie entscheidet fachlich nie.

## 1 · Vorgehen – reproduzieren, klassifizieren, heilen, verifizieren

Das Default-Setup läuft unsichtbar auf `main`. Für die Heilung wurde der Bestand **exakt reproduziert**: Ein Diagnose-Workflow auf dem Arbeitsbranch lief CodeQL mit derselben Standard-Suite und dokumentierte jede SARIF-Fundstelle als PR-Kommentar (PR #569). Erster Befund: **49 Fundstellen (13 JS + 36 PY)** – deckungsgleich mit der Security-Tab (Differenz: Laufzeit-Versatz). Jede Runde: Fix → push → Vollanalyse → Fund-für-Fund-Bewertung, bis **null offene Funden** übrig blieben.

**Methodik-Details, die den Unterschied machen:**

- Es wurde **nicht geraten**, sondern die CodeQL-Query-Quellen gelesen (z. B. `IncompleteMultiCharacterSanitization.qll`, `PathInjectionQuery.qll`, `Stdlib.qll`), um zu verstehen, welche Härtungs-Idiome der Scanner tatsächlich anerkennt – und welche nur *aussehen* wie Härtung.
- **Kein Alert wurde weggeklickt.** Jede Fundstelle wurde einzeln gelesen und bekam genau eine von zwei Behandlungen: echter Fix oder begründete, versionierte Ausnahme (Abschnitt 2).

## 2 · Behandlungsbilanz – jede Fundstelle, eine Entscheidung

### A) Echte Fixes im Code (37 Fundstellen)

| Regel | Funde | Fundort | Fix |
|---|---|---|---|
| `js/xss` | 1 | `static/pinterest-oauth.html` | URL-Werte (`code`, `error_description`) fließen nur noch als `createTextNode`-Knoten in die DOM-Helfer – nie als Strings |
| `js/xss-through-dom` | 3 | `ff-nl-praef.js`, `ff-voice.js` (×2) | URL-Wächter `sichererLink()`/`istSichereUrl()`: Schema-Prüfung via `new URL()` – nur `https:`/`http:` landet in `href`/`src` |
| `js/path-injection` | 4 | `e2e/server.mjs` | Pfad-Gefängnis: `path.resolve` + Vergleich **mit Verzeichnis-Trenner**; malformed decode → 400 |
| `js/incomplete-url-substring-sanitization` | 1 | `e2e/helpers.mjs` | Exakter Origin-Vergleich (`new URL().origin`) statt `startsWith`-Präfix |
| `js/incomplete-multi-character-sanitization` | 2 | `hugo_shortcodes.mjs`, `ff_voice_qa_lib.mjs` | **Tags werden durch Leerzeichen ERSETZT statt gelöscht.** Query-Analyse: Ein Lösch-Replace kann aus `<scr<script>ipt>` erneut `<script` zusammensetzen; mit Trennzeichen konstruktiv unmöglich. (Die erste Runde – reines Erweitern der Regex – war unzureichend; die Query meldet jeden Lösch-Replace, der `<`+Wortzeichen matcht.) |
| `js/double-escaping` | 2 | `hugo_shortcodes.mjs`, `ff-voice.js` | Entitäten in EINEM Durchlauf, `&amp;` per Lookahead ausgenommen und zuletzt dekodiert |
| `py/incomplete-url-substring-sanitization` | 10 | `newsletter_zustellbarkeit.py` (8+2 Tests), `quality_score.py` | Host-exakter Wächter `ist_resend_api()` (Schema + Host via `urlsplit`) |
| `py/clear-text-logging-sensitive-data` | 1 | `pinterest_auth.py` | **Echter Datenfluss-Bruch:** Die Scope-Ausgabe wird ausschließlich aus der `SCOPES`-Konstante konstruiert – die API-Antwort steuert nur die *Auswahl* (Membership-Test), fließt aber nicht in die Ausgabe. Selbst eine manipulierte Antwort könnte nichts anderes als die bekannten Scope-Namen ausgeben. |
| `py/path-injection` | 3 | `n8n_bridge.py` | Audio-Pfade nur durch `whisper_engine.pruefe_audio_pfad()` (Kanon + erlaubte Wurzeln). Draft-Slug: **doppelte Mauer** – (1) Gesamtmuster-Whitelist `re.fullmatch(r"[A-Za-z0-9_-]{1,80}")`, (2) kanonisches Pfad-Gefängnis `os.path.realpath` + `startswith(wurzel + os.sep)` mit **Abweisung** (nicht stiller Fallback). Beide Idiome aus der `PathInjection`-Query abgeleitet: `re.sub`/`re.fullmatch.group()` werden als Sanitizer *nicht* anerkannt, das realpath+startswith-Gefängnis ist das kanonische Muster. Integrationstest: Angriffs-Payload wird abgewiesen, Normalfall unbeeinflusst. |
| `py/redos` | 3 | `affiliate_integrity_gate.py`, `seo_audit.py`, `fix_spaces.py` | Linearisierte, semantisch äquivalente Muster – jede Änderung auf dem gesamten Content-Korpus verifiziert (0 Differenzen; ein dokumentierter Grenzfall) |
| `py/polynomial-redos` | 1 | `whisper_engine.py` | Possessives `\s++` |
| `py/bad-tag-filter` | 1 | `layout_audit.py` | `</script[^>]*>` – End-Tags mit beliebigem Inhalt vor `>` werden erkannt (echter Phantom-Link-Bug) |
| `py/insecure-protocol` | 1 | `watchdog_check4_tls.py` | Explizites `ctx.minimum_version = TLSv1_2` |
| `py/overly-large-range` | 3 | `emoji_guard.py`, `brand_guard.py`, `social_gate.py` | Emoji-Klassen kanonisiert (disjunkt, durchgehende Blöcke); Semantik per Test nachgewiesen (inkl. Regional-Indikatoren/Flaggen) |

### B) Begründete Inline-Ausnahmen (12 Fundstellen)

Wo CodeQLs Taint-Heuristik anschlägt, aber nachweislich **kein Secret-Wert** fließt: Die Ausgaben der Secrets-Wache (`secrets_age_guard.py` ×4) nennen Variablen-**Namen** („GROQ_API_KEY“), Labels und Tagesdaten – niemals Werte. Dasselbe gilt für `editorial_scorecard.py` (×2), `governance_contract.py` (×3, inkl. Markdown-Report und C10-Quelltextsuche), `social_preflight.py` (×1: Setup-Checkliste mit Variablen-Namen) und die Selftest-Assertionen `affiliate_marketer.py` / `governance_contract.py` (×2: Negativ-Assertion „Host kommt nirgends vor“ – Substring-Prüfung ist hier der *Zweck*).

Jede Ausnahme trägt einen `# codeql[regel-id]`-Kommentar **mit Begründung direkt über der Fundstelle** – versioniert, begutachtbar, und weg, sobald die Stelle refaktoriert wird.

**Warum Ausnahmen überhaupt funktionieren:** Die Analyse selbst wertet Inline-Suppressions **nicht** aus, und GitHubs Upload ignoriert SARIF-Suppressions (empirisch belegt: Testdatei mit 5 Kommentar-Varianten, keine wirkte). Der dokumentierte Weg (vgl. `kpdyer/libffx#54`) ist die Zusatz-Query **`AlertSuppression.ql`**: Sie *markiert* unterdrückte Ergebnisse im SARIF, und die Wache entfernt sie **vor** dem Upload – aber nur für Regeln aus einer festen Whitelist (Abschnitt 3).

## 3 · Die dauerhafte Pipeline: CodeQL-Sicherheitswache

`.github/workflows/codeql.yml` – ersetzt das Default-Setup vollständig:

- **Trigger:** push auf `main` (Vollanalyse + SARIF-Upload in die Security-Tab), pull_request auf `main` (Analyse + hartes Gate), montags 03:30 UTC (Freshness: neue Queries finden alten Code), manuell per Dispatch.
- **Analyse:** Standard-Query-Suite je Sprache (identisch zum Default-Setup, Vergleichbarkeit bleibt) + `AlertSuppression.ql` über die Konfigurationsdatei (`.github/codeql/codeql-config.yml`, mit Sprach-Keys). **Wichtig:** Der `packs`-*Input* der init-Action würde die Konfiguration überschreiben und die Default-Suite stillschweigend wegfallen lassen (empirisch belegt: 0 Funde trotz 14 realer) – deshalb gehört der Pack in die Config-Datei.
- **Filter vor Upload & Gate:** Unterdrückte Funde werden aus der SARIF entfernt – aber **nur** für die vier whitelisted Regeln `py/clear-text-logging-sensitive-data`, `py/clear-text-storage-sensitive-data`, `py/incomplete-url-substring-sanitization`, `js/incomplete-url-substring-sanitization`. Ein nacktes `# noqa`/`# lgtm` unterdrückt bei CodeQL *jede* Regel auf seiner Zeile – die Whitelist ist die zweite Instanz dagegen.
- **Sicherheits-Gate:** Findings mit `security-severity` (gelesen aus `tool.driver.rules` **und** `tool.extensions[].rules` – die Output-SARIF liefert die Metadaten teils nur in Extensions – vereinigt mit einer dokumentierten Regel-Liste als Fallback) lassen den Lauf fehlschlagen und blockieren damit den Pull Request. Reine Qualitäts-Fundstellen blockieren nicht – ihre dauerhafte Behebung liegt im Code (Beweis: 0 offene).
- **Bilanz-Kommentar:** Jeder PR-Lauf kommentiert Zahlen, verbleibende Funde und die unterdrückten Ausnahmen mit Begründung – die Gate-Entscheidung ist ohne Log-Download nachvollziehbar.
- **Betriebsmodus:** Auf PRs kein Upload (Security-Tab bleibt unberührt), auf `main` Upload via `upload-sarif` (nach dem Filter!) mit derselben Kategorie wie das Default-Setup (`/language:…`) – die Alert-Historie bleibt konsistent.

**Zum Verständnis PR-Analyse:** CodeQL analysiert Pull Requests **diff-informed** – es meldet nur Funde, deren Ort im PR-Diff liegt (auch konfiguriert über `observeDiffInformedIncrementalMode`). Das ist gewollt: Das PR-Gate bewertet *neue* Befunde des PR; die Vollanalyse läuft auf `main`. Deshalb zeigt die Wache auf einem PR fewer Funde als die Branch-Vollanalyse – kein Defekt, sondern das dokumentierte Verhalten.

**Ignorierte Pfade** (`.github/codeql/codeql-config.yml`, jede Ausnahme begründet): minifizierte Vendor-Bibliotheken (`**/*.min.js/.css`), vendored Skill-Tooling (`.claude/skills/impeccable/scripts/**`), `node_modules/**`. Eigener Produktionscode bleibt vollständig analysiert.

## 4 · Umstellung – einmalig nach dem Merge

1. PR #569 mergen.
2. **Einmalig das Default-Setup deaktivieren** (sonst analysieren zwei Engines parallel und die Alert-Liste verdoppelt sich): Repo → Settings → Code security and analysis → Code scanning (CodeQL) → **Default setup → Disable**.
3. Die Wache übernimmt ab dem nächsten push auf `main` (oder manuellem Dispatch) mit Vollanalyse + Upload. Bestehende Default-Setup-Alerts werden durch den Upload derselben Kategorie abgelöst; nicht mehr gemeldete Alerts schließen sich automatisch.

## 5 · Runbook für künftige Funde

- **Neuer Security-Fund auf main:** Wache schlägt rot (Gate) bzw. Alert erscheint in der Security-Tab → Code lesen, Query-Logik prüfen (dieses Dokument, Abschnitt 1), echt fixen. Nur wenn nachweislich kein reales Risiko: `# codeql[regel-id] Begründung` direkt über der Fundstelle **und** Regel in die Filter-Whitelist der Wache aufnehmen – beides ist eine begutachtete Code-Änderung.
- **Qualitäts-Fund (z. B. py/redos):** beheben, wo sinnvoll (Korpus-Verifikation nicht vergessen); das Gate blockiert bewusst nicht darauf.
- **Gate-Zahlen prüfen:** Bilanz-Kommentar am PR; SARIF-Diagnose-Notice im Lauf (`X Funde, Y unterdrückt, Z Regeln`); Diagnose-Artefakt `sarif-diagnose-<sprache>` (7 Tage Retention).
- **Niemals:** Alerts in der UI wegklicken, ohne die Ursache im Code oder in der Query-Logik verstanden zu haben.
