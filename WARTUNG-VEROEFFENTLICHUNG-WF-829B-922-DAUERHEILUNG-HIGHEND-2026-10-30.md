# Wartung · Veröffentlichung · Vorgang WF-829B (#922) — Highend-Dauerheilung, 30.10.2026

**Vorgang:** WF-829B · **Issue:** [#922](https://github.com/frank-hartung/franksfinanzcheck-blog/issues/922)
**Auftrag:** dauerhaft auf Highend-Level einer Profi-Agentur beheben
**Stand der Messungen:** 30.10.2026, 11:20–11:30 UTC · alle Werte live abgefragt
**Vorbericht:** `WARTUNG-VEROEFFENTLICHUNG-WF-829B-922-DAUERHEILUNG-HIGHEND-2026-10-29.md`

---

## 1. Kurzfassung

Der Vorgang #922 bestand aus der richtigen Entscheidung („Deploy nicht ohne
nachgewiesene Freigabe“) und drei Defekten darum herum. Zwei sind mit diesem
Bericht dauerhaft geheilt, der dritte ist eine Inhaber-Aufgabe, die jetzt
*einen* Durchgang hat statt einer Ratekette:

| Nr. | Defekt | Heilung | Stand |
|---|---|---|---|
| **A** | Das Repository konnte die fehlende Produktionsfreigabe nur **melden**, nicht herstellen — und niemand sah, ob sie erneut wegdriftet | `scripts/worker_environment_einrichten.py` (setzt, was eine API annimmt) + täglicher Drift-Blick in der Sicherheits-Wache | **geheilt** (30 Tests grün, live gemessen) |
| **B** | Der Melder war selbst tot — 24 Stunden lang, unbemerkt | KANAL-PROBE: der cron-Herzschlag prüft die Lauffähigkeit des Fehler-Alertings vor jeder Zählung und meldet über einen Kanal, den er nicht selbst beobachtet | **geheilt** (19 Tests grün, Sabotage-Gegenprobe rot) |
| **C** | Die GitHub-API nimmt `can_admins_bypass` nicht an; eine Freigabe-Bedingung ist reine Oberfläche | nicht heilbar — aber **beziffert**: der Lauf nennt sie als einzigen verbleibenden Schritt | **Inhaber**, 1 Schalter, danach 1 Knopf |

**Der harte Stopp bleibt unangetastet.** Kein Schritt überspringt den
Deploy-Job, keine Matrix wird geleert, kein Befund wird zur Warnung
herabgestuft. Die einzige neue „Warnung" betrifft einen Zustand, den das
Repository **nicht herstellen kann** — dauerhaft rot wäre dort ein Alarm ohne
Schließpfad (C14), und genau das hat dieses Repository schon einmal teuer
bezahlt.

---

## 2. Forensischer Ist-Befund (live gemessen, nicht zitiert)

### 2.1 Defekt A · Die Freigabe existiert nicht — und wurde nie gesetzt

Live-Abfrage am 30.10.2026 (`GET /repos/frank-hartung/franksfinanzcheck-blog/environments/cloudflare-produktion`):

```json
{"branch":null,"bypass":true,"created":"2026-10-25T13:20:15Z",
 "name":"cloudflare-produktion","rules":[],"updated":"2026-10-25T13:20:15Z"}
```

Vier Aussagen stecken darin:

1. **Kein Required Reviewer** (`protection_rules: []`).
2. **Keine Branch-Regel** (`deployment_branch_policy: null`) — das Environment
   nimmt jeden Branch an.
3. **Admin-Bypass aktiv** (`can_admins_bypass: true`) — der Inhaber kann die
   beiden anderen Regeln jederzeit überspringen, ohne Spur.
4. **`created == updated` (25.10.2026 13:20:15 UTC)** — seit der automatischen
   Anlage durch GitHub hat niemand dieses Environment je konfiguriert. Es ist
   kein „verlorener" Schutz, es ist ein **nie eingerichteter**.

Das ist der Grund, warum die Läufe
[40855503441](https://github.com/frank-hartung/franksfinanzcheck-blog/actions/runs/40855503441)
(29.10., 10:10:58 UTC, Push `665deeb` über #935) und
[40857308513](https://github.com/frank-hartung/franksfinanzcheck-blog/actions/runs/40857308513)
(29.10., 10:24:27 UTC, Push `2b4382d` über #943) im Schritt
„Produktions-Environment absichern" stoppten — nach unter einer Sekunde, weil
dort kein Test läuft, sondern eine Messung. Seit dem 29.10.2026 10:24 UTC
wurde kein Worker-Deploy mehr ausgelöst.

### 2.2 Defekt A · Zwei Grenzen, gemessen statt vermutet

**Grenze 1 — `can_admins_bypass` ist über keine GitHub-API setzbar.**
Die veröffentlichte OpenAPI-Beschreibung führt für
`PUT /repos/{owner}/{repo}/environments/{environment_name}` genau vier Felder
auf — `wait_timer`, `prevent_self_review`, `reviewers`,
`deployment_branch_policy` — und schließt alles andere aus
(`additionalProperties: false`). Die GraphQL-Mutation `updateEnvironment`
kennt das Feld nicht, und `Environment.protectionRules` ist im Schema
ausschließlich lesbar. Für den Bypass-Schalter existiert **keine Leitung**,
unabhängig von der Stärke des Tokens.

**Grenze 2 — Schreiben ist eine Rechtefrage, keine Code-Frage.**
Ein Live-Schreibversuch mit dem Integrationstoken dieses Repositories
antwortete **HTTP 403**. Das Werkzeug meldet daraus einen *Rechtebefund*
(feingranular „Environments: read/write", klassisch `repo`; die Inventur
beweist parallel, dass dasselbe Token alle fünf Environments lesen kann).
Ohne diese Trennung wäre ein 403 als „Skript kaputt" gelesen worden — und
damit als das, was es nicht ist.

### 2.3 Defekt B · Der Melder war selbst tot — 24 Stunden lang

Der `github-script`-Block von `alert-on-failure.yml` enthielt eine doppelte
`const workerZugangFailed`-Deklaration (beim Zusammenführen zweier Fassungen
entstanden). Der Runner führt den Block als Funktion aus: **jeder** Lauf
starb. Live-Annotation des Check-Runs 124015697710 (Meldelauf 41041663678,
30.10.2026 10:33:54 UTC), wortgleich abgefragt:

```text
Unhandled error: SyntaxError: Identifier 'workerZugangFailed' has already been declared
```

Die Auswertung aller 433 Meldeläufe des 29. und 30.10.2026:

| Kennzahl | Wert |
|---|---|
| Meldeläufe 29.–30.10.2026 | **433** (187 Erfolg · 174 übersprungen · **72 Fehlschlag**) |
| Erster Fehlschlag | **29.10.2026 10:24:30 UTC** (2 s nach dem Push `2b4382d`) |
| Letzter Fehlschlag | **30.10.2026 10:33:54 UTC** (3 min vor dem Merge von PR #956) |
| Dauer des Ausfalls | **24 h 9 min** |
| Nicht-grüne Quellläufe im selben Fenster | **124** (112 rot, 12 abgebrochen) über **18 Workflows** |
| Issues, die der Melder im Fenster erzeugt hat | **0** |
| Seit dem Merge von PR #956 (`dec5e0a`, 10:36:32 UTC) | Meldeläufe wieder grün (0 Fehlschläge in den letzten 100 Läufen) |

**Die Erkennung funktionierte.** Der Lauf „Skript-Syntax (liegender Stand)"
wurde im Fenster **achtmal** rot — er sah den doppelten `const` und nannte
Zeile und Datei. **Die Eskalation war tot**: Der einzige Weg, aus einem roten
Lauf ein Issue zu machen, war genau dieses `alert-on-failure.yml`.

Das ist der eigentliche Befund dieses Tages, und er ist größer als der
Syntaxfehler:

> Ein Wächter, der über die gestörte Leitung alarmiert werden will,
> schweigt genau dann, wenn er gebraucht wird.

Erkennung ohne Eskalation ist wie ein Rauchmelder ohne Batterie: Er hat
funktioniert. Es hat nur niemand gehört.

---

## 3. Dauerhafte technische Heilung

### H-A · Einrichten statt melden: `scripts/worker_environment_einrichten.py`

Neu. Das Gegenstück zum read-only-Gate: Es **stellt her**, was eine API
annimmt, und **beziffert**, was keine annimmt.

```bash
python3 scripts/worker_environment_einrichten.py --pruefen     # Stand je Ziel
python3 scripts/worker_environment_einrichten.py --anwenden --reviewer frank-hartung
python3 scripts/worker_environment_einrichten.py --inventur    # alle Environments
python3 scripts/worker_environment_einrichten.py --selftest    # 11 Sabotagefälle, kein Netz
```

Jedes Ziel bekommt eine Klasse und **einen** nächsten Schritt:

| Klasse | Bedeutung | Weg |
|---|---|---|
| `ERFUELLT` | belegt | — |
| `MACHBAR` | fehlt, per GitHub-API setzbar | `--anwenden` |
| `OBERFLAECHE` | fehlt, **nur im Dashboard** setzbar | der Lauf nennt den Schalter |
| `ABWEICHUNG` / `UNBEKANNT` | vorhanden, aber nicht von diesem Werkzeug gesetzt | von Hand prüfen, nie überschreiben |
| `OFFEN` | nicht belegbar | **nie grün** — erst die Ursache der Unlesbarkeit |

Live-Befund vom 30.10.2026, 11:26 UTC (gekürzt):

| Ziel | Stand | Nächster Schritt |
|---|---|---|
| Required Reviewer | `MACHBAR` | `--anwenden` ergänzt den fehlenden Reviewer |
| Kein Administrator-Bypass | `OBERFLAECHE` | Dashboard: „Allow administrators to bypass…" **AUS** |
| Branch-Regel exakt `main` | `MACHBAR` | `--anwenden` setzt „Selected branches" + `main` |

Fünf unverhandelbare Grenzen, jede durch einen Test belegt:

1. **Nur Verschärfen.** Kein `DELETE`, kein Entfernen eines bestehenden
   Reviewers, `wait_timer` und `prevent_self_review` bleiben unberührt.
   Mehrere `required_reviewers`-Regeln werden **zusammengeführt**, nicht
   ersetzt — sonst verlöre ein zweiter Prüfer sein Veto durch einen Lauf.
2. **Endpunkt-Grenze.** Ausgehend nur `api.github.com`, Environment-Name
   ausschließlich `cloudflare-produktion`, daneben `/users/<login>` zur
   Reviewer-Auflösung. Weiterleitungen werden abgelehnt.
3. **Geheimnisfreiheit.** Kein Token, kein Header, kein Antworttext in
   Ausgabe oder Markdown; Ausnahmen werden nur als Typname genannt.
4. **Idempotenz.** Steht ein Ziel auf `ERFUELLT`, erfolgt **kein** Schreibzugriff.
5. **Fail-closed.** Unlesbare API-Antwort ⇒ jedes Ziel `OFFEN`, nie `ERFUELLT`
   („nicht belegbar" ist kein „in Ordnung", C33).

### H-B · Drift sichtbar machen — täglich, in der richtigen Lautstärke

`.github/workflows/sicherheits-wache.yml`, Job **Live-Messung** (täglich und
auf Zuruf), neuer Schritt „Produktions-Environment – Freigabestand und Drift"
vor dem Artefakt-Upload. Der Job hat dafür `permissions: {actions: read,
contents: read}` — Metadaten, keine Secrets.

| Exit des Werkzeugs | Wirkung |
|---|---|
| `0` | grün |
| `1` | `::warning` + `exit 0` — der Zustand ist im Repository **nicht herstellbar** |
| `2` | `::error` + `exit 1` — **nicht belegbar** |

Warum hier Warnung und nicht rot: Der harte Stopp liegt im Deploy-Pfad
(`worker_environment_guard.py`, fail-closed). Was fehlte, war der Blick
*dazwischen* — wird das Environment neu angelegt (GitHub tut das beim ersten
Verweis automatisch und ungesichert) oder ein Reviewer entfernt, merkte das
sonst erst der nächste Deploy-Versuch. Ein Dauer-Rot ohne Schließpfad ist
Anti-Muster C14; „nicht belegbar" bleibt dagegen rot, weil ungeprüft nicht
sauber ist (C34).

### H-C · Die KANAL-PROBE: wer meldet den Ausfall des Melders?

Neu in `scripts/alerting_heartbeat.py` und `.github/workflows/alerting-heartbeat.yml`.
Der Herzschlag läuft per `cron` und ist damit der **einzige** Weg, der einen
toten Melder noch melden kann — vorausgesetzt, er benutzt ihn nicht selbst.

```bash
python3 scripts/alerting_heartbeat.py --kanal      # 0 lauffähig · 1 Befund · 2 nicht prüfbar
python3 scripts/alerting_heartbeat.py --selftest   # u. a. sechs Sabotagefälle K1–K6
```

Ablauf im Workflow:

1. **Kanal-Integrität** prüft jeden `github-script`-Block von
   `alert-on-failure.yml` mit `node --check` (derselbe Prüfer, der den
   Vorfall sah: `workflow_js_wache.py`).
2. Ist der Kanal tot: **eigenes Issue** „🫀 Alerting-Kanal: das Fehler-Alerting
   selbst ist nicht lauffähig", und **die Zählung bleibt aus** — eine
   Zustellquote für eine Leiche wäre eine Zahl ohne Bedeutung.
3. Ist der Kanal grün: offene Kanal-Meldung wird geschlossen, danach läuft die
   Zählung wie bisher.

Zwei Entscheidungen, die nicht offensichtlich sind:

- **Ein eigener Issue-Titel.** Die bestehende Meldung „Zustellung verliert
  Ereignisse" würde auf API-Schlüssel und Netz raten, während die Ursache ein
  Syntaxfehler im Melder selbst ist. Zwei Titel, zwei Räte, ein Werkzeug.
- **Sechs Sabotagefälle im Selbsttest (K1–K6).** Eine Prüfung, die nicht
  nachweist, dass sie den Ausfall *erkennt*, ist eine Behauptung. Die
  Gegenprobe (die Probe behauptet grundlos „lauffähig") schlägt fehl wie
  gewollt: `exit 2` mit „K1 kaputter Meldeweg nicht erkannt".
- **Eine stillschweigend mitgeheilte Falle.** Der Schritt „Meldung schließen
  (Zustellung wieder vollständig)" hing bisher an `success()`. Bei totem
  Meldeweg bleibt die Zählung jetzt aus — der Job wäre trotzdem erfolgreich
  und hätte eine offene Zustellungs-Meldung **ungemessen geschlossen**. Das
  wäre genau das falsche Grün, das dieser Vorgang bekämpft. Der Schritt hängt
  nun an `kanal-code == '0' && steps.messung.outcome == 'success'`; ein Test
  hält das fest. Wer nicht gemessen hat, darf nicht schließen.

### H-D · Der Rat bleibt am Befund

`scripts/worker_environment_guard.py` nennt in seiner Fehlermeldung jetzt den
einen Befehl, der die Lücke schließt (`--anwenden`), und sagt gleichzeitig,
welcher Teil ein Dashboard-Schalter bleibt. Ein roter Lauf, der nur „fehlt"
schreibt, erzeugt die nächste Runde Raterei.

### H-E · Verträge und Dokumentation

| Ort | Änderung |
|---|---|
| `scripts/governance_contract.py` | `worker_environment_einrichten.py` im vertraglichen Minimum (C6): Eine Wache, die niemand verlangt, führt irgendwann niemand aus |
| `scripts/ki_transportweg.py` | dokumentierte api.github.com-Ausnahme **nur** für dieses Werkzeug, mit Endpunkt-Einschränkung und Verweis auf den ausgleichenden Test |
| `package.json` | `worker:environment`, `worker:environment:anwenden`, `worker:environment:inventur`, `test:worker:environment`; `test:sicherheit` führt Selbsttest und Vertragstests mit |
| `docs/SICHERHEIT-BETRIEB-RUNBOOK.md` | **A4** „Die Freigabe einrichten, statt sie nur zu melden" (Klassen, Befehle, die zwei gemessenen Grenzen) · **D2** Schritt 1 jetzt mit Heilungsweg statt Handgriff · **F4** „Wer meldet den Ausfall des Melders?" |

---

## 4. Verifikation

| Prüfung | Ergebnis |
|---|---|
| `python3 scripts/worker_environment_einrichten.py --selftest` | **Exit 0** — 11 Sabotagefälle (Zuordnung, `OFFEN` ist nie grün, Endpunktgrenzen, Nur-Verschärfen, Idempotenz, Rechtebefund, Geheimnisfreiheit) |
| `python3 -m unittest scripts.tests.test_worker_environment_einrichten` | **30 Tests OK** |
| `python3 -m unittest scripts.tests.test_alerting_heartbeat` | **20 Tests OK** (4 neue für die KANAL-PROBE und den Schließpfad) |
| `python3 -m unittest scripts.tests.test_worker_environment_guard` | **17 Tests OK** |
| Sabotage-Gegenprobe KANAL-PROBE | **Exit 2** — „K1 kaputter Meldeweg nicht erkannt" |
| `python3 scripts/trigger_wache.py --check` | **96 Workflows, 0 Befunde** |
| `python3 scripts/wachen_vertrag.py` | **357 Skripte, 0 Befunde** |
| `python3 scripts/skript_syntax_wache.py --check` | **591 Dateien grün** |
| `python3 scripts/governance_contract.py --quick` | **42 Regeln** prüfen in beide Richtungen |
| `python3 scripts/ki_transportweg.py --selftest` · `alert_issue_identity.py --selftest` · `actions_version_guard.py` · `clear_text_logging_guard.py` | alle grün (65 Workflows / 65 Codes, 601 Python-Dateien) |
| `python3 scripts/workflow_js_wache.py --check` | **Exit 0** — alle `github-script`-Blöcke kompilieren |
| `python3 scripts/alerting_heartbeat.py --kanal` | **Exit 0** — Kanal lauffähig |
| `npm run test:sicherheit` | **Exit 0** |
| `npm run manifest:check` | **GRÜN** |
| `python3 -m unittest discover -s scripts/tests` | **4547 Tests, 14 Fehlschläge** — dieselben 14, in derselben Reihenfolge, auf dem unberührten Stand `6d5ddd0` in einem eigenen Worktree gegengeprüft (Inhalte/SEO/Social, nicht berührt von diesem Vorgang) |

Die Gegenprobe auf dem sauberen Stand ist Teil des Berichts, weil
„4547 Tests, 14 rot" allein nichts beweist. Bewiesen ist: **kein** dieser
14 Fehlschläge stammt aus diesem Vorgang.

---

## 5. Was offen bleibt — Inhaber-Aufgabe, ein Durchgang

Der dritte Defekt ist nicht im Repository heilbar. Er hat jetzt aber eine
Reihenfolge, in der jeder Schritt den nächsten belegt:

1. **Ein Schalter im Dashboard** (30 Sekunden, nicht automatisierbar):
   Settings → Environments → **`cloudflare-produktion`** →
   *Allow administrators to bypass configured protection rules* **aus**.
   Alles andere kann das Skript selbst setzen.
2. **Dann ein Befehl** (setzt Reviewer + Branch-Regel `main`; bestehende
   Einträge bleiben stehen):
   ```bash
   export GITHUB_TOKEN=<Token mit Environments: read/write>
   python3 scripts/worker_environment_einrichten.py --anwenden --reviewer frank-hartung
   python3 scripts/worker_environment_einrichten.py --pruefen      # muss 0 melden
   ```
   Ohne Schreibrecht antwortet GitHub mit 403 — der Lauf benennt dann das
   fehlende Recht. Das ist kein Fehler des Werkzeugs.
3. **Dann ein Knopf:** Actions → **„Cloudflare-Worker deployen"** →
   *Run workflow* (`newsletter-worker`, `main`). Das Environment-Gate liest die
   Freigabe live und lässt Wrangler erst dann an die Secrets.

Erst Schritt 3 mit **zwei grünen Deploy-Jobs** schließt #922 — nachgewiesen
über `scripts/alert_resolve_gate.py`. Ein grüner Plan, ein grüner
Zugangs-Check oder ein Push ohne Deploy-Job schließt ihn ausdrücklich **nicht**;
das war die Lücke vom 24.10.2026.

Bis dahin ist der Zustand **bekannt und bewacht**, nicht unbekannt und still:
Der tägliche Lauf der Sicherheits-Wache meldet den Freigabestand als Warnung,
und der Herzschlag prüft, ob diese Meldung überhaupt ankommen kann.

---

## 6. Grenzen dieser Heilung (bewusst benannt)

- **Der Bypass-Schalter bleibt Handarbeit.** Kein Werkzeug und kein Token
  kann ihn setzen; die Belege stehen in Abschnitt 2.2. Wer etwas anderes
  behauptet, hat es nicht gemessen.
- **Die Warnstufe beim täglichen Drift-Blick ist eine Entscheidung, keine
  Erleichterung.** Sie gilt ausschließlich für einen Zustand, den das
  Repository nicht herstellen kann. Sobald `--anwenden` den Rest gesetzt hat
  und nur noch der Schalter offen ist, bleibt die Warnung bewusst stehen —
  sie ist der einzige tägliche Hinweis darauf, dass der Deploy wartet.
  „Nicht belegbar" bleibt rot.
- **Die KANAL-PROBE prüft den Melder, nicht die Leitung.** Sie beantwortet
  „kann das Fehler-Alerting laufen?", nicht „kommt die E-Mail an?". Für die
  Zustellquote bleibt der Herzschlag zuständig — er zählt nur, wenn die
  Kanal-Probe grün war.
- **Die 14 verbleibenden Testfehlschläge** liegen in Inhalten, SEO und
  Social-Winkeln. Sie sind auf dem unberührten Stand identisch und gehören
  nicht zu diesem Vorgang; sie sind hier nur aufgeführt, damit niemand sie
  später für eine Folge dieses PRs hält.
