# Code-Scanning-Alert #78 – „Clear-text logging of sensitive information“ · Dauerheilung auf Agentur-Niveau, 05.10.2026

**Ausgangslage:** Alert #78 (`py/clear-text-logging-sensitive-data` / `py/clear-text-storage-sensitive-data`) erschien am 05.10.2026 mit **6 Fundstellen** in 3 produktiven Skripten – sechs Tage nach der Heilungsrunde vom 04.10. (`CODE-SCANNING-HEILUNG-PREMIUM-2026-10-04.md`, PR #569/#570, events #77) · **Besonderheit:** Das CodeQL-Gate der Wache meldete auf mehreren Pull Requests „0 Funde – grün“, während dieselben Commits auf `main` rot gingen. Der Alert war also nicht nur offen – er war **unsichtbar im Prozess, der ihn hätte blockieren sollen**. · **Ergebnis:** Alle 6 Fundstellen konstruktiv auf Code-Ebene geheilt (**keine Unterdrückung, kein Dismiss** – die 4 Inline-Unterdrückungen aus dem zwischenzeitlich gemergten PR #579 sind zurückgebaut), die zwei Blindheits-Ursachen des Gates behoben, und ein Dauervertrag mit drei Beinen (Namensebene, Werteebene, Unterdrückungsverbot) stellt die Wiederkehr ab: **`scripts/tests/test_zugangs_namensvertrag.py`, 21 Tests.**

> Dieser Bericht ist der Wahrheitsort für den Sonderfall #78; die Gesamtstrategie bleibt in `CODE-SCANNING-HEILUNG-PREMIUM-2026-10-04.md` (dortiger Nachtrag verweist hierher). Was hier steht, gilt bis ein neuer datierter Abschnitt es ablöst.

---

## 1 · Warum der Alert offen blieb, obwohl das Gate grün war

Der Fall hatte **drei** voneinander unabhängige Ursachen. Alle drei mussten behoben werden – jede allein hätte den Alert wiederkommen lassen.

### Ursache A – das Gate prüfte nur den Diff („Diff-Blindheit“)

Seit `codeql-action` v3.28 analysiert die Action bei `pull_request` standardmäßig **nur die im Diff berührten Zeilen** („diff-informed queries“; die Cleartext-Queries tragen dafür das Flag `observeDiffInformedIncrementalMode`). Beweis aus dem Echtbetrieb dieses Repositories:

| Lauf | Ereignis | Ergebnis |
|---|---|---|
| PR #575/#576 (Dependabot-Gruppe) | `pull_request` | Gate **grün** („0 Funde“) |
| `main` nach Merge von #576 (Lauf `37285773894`) | `push` | **FEHLER** – 6 Sicherheits-Fundstellen |
| `main` nach Merge von #577 (Lauf `37285972985`) | `push` | **FEHLER** – dieselben 6 Fundstellen |

Derselbe Commit, zwei Urteile. Das Gate war keine Wache, sondern eine Diff-Vorschau: Solange ein PR die betroffene Datei nicht selbst anfasst, sieht er die Fundstelle nicht.

**Fix:** `CODEQL_ACTION_DIFF_INFORMED_QUERIES: false` als Job-`env` in `.github/workflows/codeql.yml` (mit Begründung im Kommentar). Damit läuft in **jedem** Ereignis die Vollanalyse des gesamten Bestands. Ein PR ist nur grün, wenn das Repository als Ganzes sauber ist – das ist die Zusage, die dieses Gate gibt.

### Ursache B – der SARIF-Upload der Wache scheiterte still

Die Security-Tab zeigt bislang die Alerts des **GitHub-Default-Setups** (erkennbar an den parallelen „CodeQL“-Läufen auf `main`), nicht die der Advanced-Wache: Deren SARIF-Upload wird mit *„CodeQL analyses from advanced configurations cannot be processed when the default setup is enabled“* abgelehnt. Der Upload stand auf `continue-on-error` – er durfte die Analyse nicht verschlucken, scheiterte aber **unsichtbar**. (Abfrage des Default-Setup-Status per API: 403 – für Token dieses Repository-Kontexts nicht lesbar.)

**Fix (technisch):** Neuer Schritt **„Upload-Ergebnis sichtbar machen (Default-Setup-Konflikt)“** schreibt bei abgelehntem Upload eine Job-Summary mit Klick-Anleitung plus `::warning`-Annotation. Zusätzlich gibt das Gate jetzt **jede einzelne Fundstelle als Datei-Annotation** aus (`::error file=…,line=…,title=…`) – sichtbar an der Codezeile im PR-Diff, im Lauf-Kopf und maschinenlesbar über die Checks-API. Vorher standen die Fundstellen nur im Lauf-Log, das praktisch nur als ZIP-Download erreichbar ist – genau deshalb blieb Alert #78 über mehrere „grüne“ PRs hinweg unbemerkt.

**Fix (organisatorisch) – einmalige Handlung des Betreibers, nur per Klick möglich:**

> **Repo → Settings → Code security and analysis → Code scanning (CodeQL) → Default setup → _Disable_.**
>
> Danach übernimmt die Wache (`.github/workflows/codeql.yml`) die Security-Tab, und die dort gezeigten Alert-Nummern stammen aus der Konfiguration, die auch das Gate fährt. Bis dahin ist das **Gate des jeweiligen Laufs** maßgeblich – es prüft denselben Bestand (seit Ursache A: vollständig) und schlägt bei jeder Security-Fundstelle fehl.

### Ursache C – die erste „Behebung“ unterdrückte statt zu heilen

Der zwischenzeitlich gemergte **PR #579** hat denselben Alert an 4 der 6 Stellen über Inline-Unterdrückungen geschlossen (`# codeql[py/clear-text-logging-sensitive-data]` ×3 in `governance_contract.py`, ×1 in `social_preflight.py`). Das lässt den Alert verschwinden, ohne die Ursache zu berühren: Der Datenfluss bleibt, der irreführende Name bleibt, und beim nächsten Umbau in der Nähe kommt der Fund zurück – unter neuer Nummer. (Die Scorecard-Hälfte von #579 – `zugangsalter_*` – war dagegen eine echte Heilung und bleibt unverändert.)

**Fix:** Alle 4 Unterdrückungen sind **entfernt**; an ihrer Stelle steht jeweils die Heilung der Quelle plus ein Kommentar, der erklärt, warum keine Unterdrückung mehr nötig ist. Zusüglich sind die beiden Clear-Text-Regeln aus der **Unterdrückungs-Whitelist der Wache gestrichen** (`ERLAUBT` im Filter-Schritt): Eine künftige Unterdrückung bliebe in der SARIF sichtbar und ließe das Gate rot werden – der Rückbau kann nicht still rückgängig gemacht werden. Drittes Bein: der Unterdrückungsverbot-Test (Abschnitt 4).

---

## 2 · Die 6 Fundstellen – Befund, Ursache, Heilung

Fundbild der Vollanalysen auf `main` (Läufe `37285773894` / `37285972985`, Oktober 2026). JavaScript: 0 Funde.

| # | Fundort | Regel | Quelle des Fundes (Taint-Ursprung) | Heilung |
|---|---|---|---|---|
| 1 | `scripts/social_preflight.py:651` | logging | `ch.get("secrets")` (415/574), `eintrag["secrets"]`/`["fehlende_secrets"]` (432) → `bericht` → `print(json.dumps(...))` | Felder `pflicht_env` / `fehlende_env`; JSON-Oberfläche über `JSON_FELDNAMEN` |
| 2 | `scripts/governance_contract.py:1964` | logging | Funktionsname `c9_secret_leak(...)` → `checks` → `print(...)` | Funktion heißt `c9_leak_wache` |
| 3 | `scripts/governance_contract.py:1966` | logging | dito (`::error::`-Zweig) | dito |
| 4 | `scripts/governance_contract.py:1977` | storage | lokale Variable `secrets` (1368) → `checks` → `f.write(render_md(checks))` | Variable `wachen_quelltext` (Quelltext der Wache = Namen-Registry) |
| 5 | `scripts/editorial_scorecard.py:588` | storage | `d.get("secrets_age_red")`/`"secret_red"`/`"secret_amber"` → `row` → `f.write(json.dumps(row))` (6 Pfade) | Kennzahlen `zugangsalter_*` (bereits via PR #579 auf `main` – übernommen) |
| 6 | `scripts/editorial_scorecard.py:956` | logging | `_score()` liest `d.get("secrets_age_red")` (623) → Score → `failures`-Text → `print("   -", f)` | dito |

### Was CodeQL hier wirklich prüft

Gelesen wurde nicht die Alert-Beschreibung, sondern die Query-Quelle – `SensitiveDataHeuristics.qll` aus `github/codeql` (am 05.10.2026 am Original verifiziert):

```
maybeSecret   = (?is).*((?<!is|is_)secret|(?<!un|un_|is|is_)trusted(?!_iter)|confidential).*
maybePassword = (?is).*(pass(wd|word|code|.?phrase)(?!.*question)|(auth(entication|ori[sz]ation)?).?key
                 |oauth|api.?(key|tok)|([_-]|\b)mfa([_-]|\b)).*
notSensitive  = (?is).*([^\w$.-]|redact|censor|obfuscate|hash|md5|sha|random|(?<!unen)crypt|(?<!un)encode
                 |certain|concert|secretar|wildcard|coauthor|account(ant|ab|ing|ed)|(?<!pro)file|path|([_-]|\b)url).*
```

Vier Konsequenzen, die den Fall vollständig erklären:

1. **Sensibel ist der NAME, nicht der Wert.** Es genügt, dass eine Variable, ein Parameter, ein Dict-Schlüssel (`dict.get("<Literal>")`) oder – als `SensitiveFunctionCall` – ein **Funktionsname** in die Muster fällt. Fund #2/#3 entstand allein daraus, dass eine Prüffunktion `c9_secret_leak` hieß; ihre Rückgabe waren reine Befund-Texte.
2. **Die Default-Konfiguration kennt keine Sanitizer/Barrieren** für diese Queries. Deshalb hat die (korrekt arbeitende) Funktion `_sanitize_report_for_json()` den Fund #1 nicht beseitigen können: Sie filtert inhaltlich richtig, unterbricht aber den Taint-Fluss aus Sicht der Query nicht. Namensheilung statt Filter-Kosmetik ist damit zwingend.
3. **Entschärfend wirkt `notSensitiveRegexp`** – u. a. Namen mit `hash`, `path`, `url`, `crypt` oder mit Sonderzeichen außerhalb von `[\w$.-]` (Anzeige-Texte wie „Secrets & Zugänge“). Und jeder Name, der schlicht nicht in die Muster fällt: `pflicht_env`, `zugang_*`, `nachweis_*`, `wachen_quelltext` matchen nicht.
4. **`regexpMatch` verlangt den vollen Match** (Java-Semantik) – im Nachbau des Dauervertrags entsprechend `fullmatch()`.

### Die Heilung: ein Namensvertrag – semantisch korrekt, kein Ausweichen

Entscheidend: Die Umbenennung ist **kein Trick gegen den Scanner**, sondern die sachlich richtige Beschreibung. Die betroffenen Strukturen transportierten **nie Geheimnisse**, sondern (a) die **Namen** benötigter Umgebungsvariablen und (b) **Ampel-/Nachweis-Metadaten**. Der alte Name `secrets` behauptete das Gegenteil – irreführend für Menschen („hier liegt ein Secret“ – irgendwann füllt jemand eines hinein) und ein Fehlsignal für die Analyse. **Der Scanner hatte in der Sache recht.**

**Der Vertrag (ab 05.10.2026 verbindlich, dokumentiert in `SECURITY.md` und im Kopf von `data/social/channels.yaml`):**

| Bedeutung | Feldname intern | Feldname in der JSON-Oberfläche |
|---|---|---|
| Namen benötigter Umgebungsvariablen | `pflicht_env` | `required_env_names` |
| davon fehlende | `fehlende_env` | `missing_env_names` |
| Namen benötigter Actions-*Variables* | `vars` | `required_var_names` |
| davon fehlende | `fehlende_vars` | `missing_var_names` |
| Ampel-/Nachweis-Metadaten (Scorecard) | `zugangsalter_*` | `zugangsalter_*` |
| Zugangs-Nachweis-Zustand (Cockpit) | `zugang_state` | – (nur Anzeige) |

**Verbotene Namensbestandteile** in berichtsnahen Strukturen: `secret`, `trusted`, `confidential`, `pass*`, `oauth`, `api_key` / `api_tok`, `mfa` – exakt die Menge der CodeQL-Heuristik.

| Datei | Änderung |
|---|---|
| `data/social/channels.yaml` | SSOT: `secrets:` → **`pflicht_env:`** für alle 10 Kanäle + Namensvertrag im Kopfkommentar |
| `scripts/social_channels/__init__.py` | Feldname **einmal** zentral: `ENV_FELD = "pflicht_env"`; neue Funktion `pflicht_env_namen(channel)` mit **Fail-loud** – ein Kanal, der noch `secrets:` trägt, wirft `ValueError` (mit Migrationstext) statt still als „braucht keine Zugangsdaten“ zu gelten; `missing_env()` nutzt sie und bleibt signaturstabil |
| `scripts/social_preflight.py` | interne Felder `pflicht_env`/`fehlende_env` (auch im virtuellen YouTube-Kanal und im Selbsttest); Mapping-Dict `JSON_FELDNAMEN` hält die **stabile, nun vollständig selbsterklärende JSON-Oberfläche**; Unterdrückung entfernt |
| `scripts/governance_contract.py` | `c9_secret_leak` → **`c9_leak_wache`** (Definition + 3 Aufrufe inkl. Selbsttest), Parameter/lokale Variable `secrets`/`secrets_text` → `wachen_quelltext` (c5 + run_all), toter Alias `SECRET_PATTERNS` entfernt, 3 Unterdrückungen entfernt |
| `scripts/editorial_scorecard.py` | `zugangsalter_*` (aus PR #579, unverändert übernommen – echte Heilung) |
| `scripts/cockpit.py` | **vorsorglich mitgeheilt** (nicht unter den 6 Funden, aber dieselbe latente Quelle): Funktion `bucket_secrets` → **`bucket_zugaenge`** (Funktionsnamen matchen die Heuristik und sind mit zukünftigen Queries eine reale `SensitiveFunctionCall`-Quelle), `SECRETS_PATH` → `ZUGANG_STATE_PATH`, Parameter/Lokale `secrets_state` → `zugang_state`, `bucket_social` liest `pflicht_env` |
| `scripts/schaltwerk_actions.py` | `kanal_zustand()` führt `pflicht_env` (zentral über `sch.pflicht_env_namen`) |
| `scripts/schaltwerk_triggers.py` | Standby-Ereignis führt `pflicht_env` im `daten`-Block (Verbraucher in `data/automationen.yaml` nutzen nur `kanal`/`kanal_label`/`grund`/`jetzt` – geprüft, kein Template bricht) |

**Zwei Namen wurden bewusst _nicht_ geändert** (jeweils geprüft und begründet):

- **`data/secrets_state.json`** behält seinen **Dateinamen**. Dateinamen sind durch `notSensitiveRegexp` (`path`) ohnehin entschärft, und ein Rename würde einen Datenbestand brechen, ohne Sicherheitsgewinn. Die Datei enthält ausschließlich `entries{<ENV_NAME>: {Ampel/Nachweis}}` und `version` – keine Werte. Nur die lesende Variable in `cockpit.py` heißt jetzt wahrheitsgemäß `ZUGANG_STATE_PATH`.
- **Der Governance-Step-Key `steps["secrets"]`** bleibt. Er ist ein **externer Vertrag** zwischen `governance_contract.py` (`MEASURE_STEPS`), `governance_gate.py` (`STEPS`-Registry, `--emit secrets`), den Workflows und `data/governance_status.json`. CodeQL meldet ihn nicht (die Container-Kette dict→tuple→list sprengt das Access-Path-Limit der Analyse – empirisch über mehrere Vollläufe bestätigt, auch nach dieser Änderung). Ihn umzubenennen hätte mehrere Workflows und ein Datenformat gebrochen, ohne einen Fund zu schließen. Der Dauervertrag beweist stattdessen, dass dieser Schlüssel **nie in eine Ausgabe** durchsickert (Cockpit-Status-JSON wird mit realistischer `steps.secrets`-Eingabe geprüft).

**Nicht genutzter Ausweg:** `sensitiveLookupStringConst` verlangt lokalen Datenfluss vom String-Literal zum Lookup. Ein Umweg über eine Modulkonstante würde die Heuristik technisch aushebeln, ohne irgendetwas zu verbessern – das wäre ein Dodge und wurde verworfen. Wie am 04.10. gilt: **kein Alert wird weggeklickt.**

---

## 3 · Systemische Härtung – das Gate sieht wieder den ganzen Bestand

`.github/workflows/codeql.yml`:

1. **`CODEQL_ACTION_DIFF_INFORMED_QUERIES: false`** (Job-`env`) – Vollanalyse in jedem Ereignis (Ursache A).
2. **Upload-Ergebnis sichtbar machen** – Job-Summary + `::warning` bei blockiertem SARIF-Upload, mit Klick-Weg zum Deaktivieren des Default-Setups (Ursache B).
3. **Jede Fundstelle als Datei-Annotation** (`::error file=…,line=…,title=CodeQL <regel>`) – Fundstellen stehen ab sofort an der Codezeile im PR-Diff und in der Checks-API, nicht nur im Log-ZIP.
4. **Clear-Text-Regeln aus der Unterdrückungs-Whitelist gestrichen** – Unterdrückungen dieser Klasse blockieren künftig das Gate selbst (Ursache C, zweites Bein).

`.github/workflows/publication-reliability-tests.yml`: Der `paths`-Filter wird um **`data/social/**`** erweitert – sonst könnte das Kanal-Playbook allein geändert werden, ohne dass der Namensvertrag läuft (das Feld `pflicht_env:` könnte unbemerkt wieder `secrets:` heißen).

---

## 4 · Der Dauerschutz: `scripts/tests/test_zugangs_namensvertrag.py` (21 Tests)

Eine Umbenennung hält nur, wenn eine Maschine sie bewacht. Der Vertrag steht auf **drei Beinen** – ein Rückfall müsste alle drei gleichzeitig überlisten:

**Bein 1 – Namensebene (gegen den Alert):**

- `codeql_klassifikation(name)` baut `SensitiveDataHeuristics` **1:1 nach** – mit den Original-Regexen (am Query-Quelltext verifiziert), Java-Semantik (`fullmatch`) und den in Python unzulässigen variablen Lookbehinds als Kette (`(?<!is|is_)` → `(?<!is)(?<!is_)`).
- `HeuristikIstScharf` ist die **Gegenprobe**: Der Nachbau muss genau die Namen erkennen, die Alert #78 ausgelöst haben (`secrets`, `fehlende_secrets`, `secrets_age_red`, `c9_secret_leak`, `bucket_secrets`, `X_API_KEY` …) und die neuen durchlassen (`pflicht_env`, `zugang_*`, `c9_leak_wache`, `bucket_zugaenge`, `wachen_quelltext` …). Wird der Nachbau stumpf, fällt dieser Test – nicht erst der eigentliche Vertrag.
- `NamensvertragSSOT` prüft die Kanal-Konfiguration: kein Kanal trägt noch `secrets:`, jeder aktive Kanal nennt seine `pflicht_env`-Namen, und in den Listen stehen nur Variablennamen (`^[A-Z][A-Z0-9_]{2,63}$`) – **ein versehentlich eingetragener Wert fällt auf, weil er nicht wie ein Name aussieht**. Ein Kanal mit altem Feldnamen muss **laut** fehlschlagen.
- `NamensvertragBerichte` läuft **rekursiv über jeden Mapping-Schlüssel** der tatsächlich erzeugten Strukturen: Preflight-Eintrag, Preflight-JSON-Oberfläche, Schaltwerk-Kanalzustand, Schaltwerk-Standby-Ereignis, Scorecard-`collect()` samt Historienzeile, Cockpit-Status-JSON. Ein neu eingeführter Schlüssel `oauth_state` oder `api_token_alter` fällt sofort auf – auch in einer Datei, an die beim Schreiben niemand denkt. Das Cockpit-Beispiel bekommt die realistische Eingabe **mit** dem externen `steps["secrets"]`-Vertrag und beweist, dass dieser Schlüssel nie in der Ausgabe landet.

**Bein 2 – Werteebene (gegen das eigentliche Risiko, namensunabhängig):**

`WertDichtheit` belegt **alle** Zugangsvariablen – dynamisch aus der SSOT `channels.yaml` (`pflicht_env` + `vars` je Kanal) plus die Dienst-Keys (Groq/Gemini/Pinterest/Resend/Umami/Awin/GitHub) – mit dem Marker `GIFTWERT-DARF-NIE-AUSGEGEBEN-WERDEN-7F3A91` und lässt dann die **echten Berichtsgeneratoren** laufen. Der Marker darf nirgends auftauchen: Preflight (JSON, Konsole, Markdown-Bericht), Cockpit (Markdown + Status-JSON), Scorecard (Report + Historienzeile), Governance-Vertragsbericht (`render_md` + Konsolenausgabe, inkl. Gegenprobe, dass C9 ein künstliches Leck erkennt, ohne den Fund zu zitieren). `test_gift_test_wuerde_ein_echtes_leck_bemerken` ist die Gegenprobe auch hier. Dieses Bein greift unabhängig von jedem Namen – auch wenn CodeQL seine Heuristik ändert oder ein Wert künftig unter einem harmlos klingenden Schlüssel ausgegeben würde.

**Bein 3 – Unterdrückungsverbot (organisatorisch):**

`Unterdrueckungsverbot` durchsucht den gesamten Python-Bestand (Scripts, Tests, Adapter, Tools, e2e, newsletter-worker, n8n) nach `# codeql[py/clear-text-logging-sensitive-data]` / `# codeql[py/clear-text-storage-sensitive-data]` und schlägt bei jedem Fund an. Zusammen mit der gestrichenen Gate-Whitelist (Abschnitt 3) ist ein Rückfall zur Unterdrückungs-„Heilung“ doppelt blockiert.

**Bewusst _nicht_ gebaut:** Ein repo-weites Namensregister oder ein lokaler Taint-Emulator als Gate. Messung: repo-weit ~150 legitime `secret*`-Namens-Vorkommen in ~45 Dateien (`secrets_age_guard.py`, `pinterest_token.py`, …) – ein solches Gate wäre dauerrot und binnen Wochen abgeschaltet worden. Der Schutz greift gezielt dort, wo Berichte entstehen – plus dem namensunabhängigen Gift-Test und dem Unterdrückungsverbot.

---

## 5 · Verifikation

| Prüfung | Ergebnis |
|---|---|
| `python3 -m unittest discover -s scripts/tests` | **1779 Tests, OK** (23 skipped) – vor dieser Runde 1758; +21 aus dem Namensvertrag |
| `python3 scripts/governance_contract.py --selftest` | ✅ C1–C18 (inkl. `c9_leak_wache`-Umbenennung in der Selbstprüfung) |
| `python3 scripts/cockpit.py --selftest` | ✅ (inkl. `bucket_zugaenge`) |
| `python3 scripts/social_preflight.py --selftest` | ✅ 11 Kanäle, Standby-Regel und Offline-Lauf sauber |
| `python3 scripts/schaltwerk.py --selftest` | ✅ 11 Regeln, 14 Trigger, 12 Aktionen |
| `python3 scripts/editorial_scorecard.py --selftest` | ✅ |
| `python3 scripts/governance_gate.py --selftest` · `secrets_age_guard` · `social_gate` | ✅ |
| `python3 scripts/social_preflight.py --offline --json` | ✅ Oberfläche: `required_env_names` / `missing_env_names` / `required_var_names` / `missing_var_names` – Aussage unverändert |
| Restsuche `# codeql[py/clear-text-…]` im Bestand | **0** (vorher 4) |
| Restsuche `"secrets"` in scripts/ | nur noch der dokumentierte Governance-Step-Key, die Migrationserkennung `ENV_FELD_ALT` und Negativ-Assertionen im Test |
| **CodeQL-Vollanalyse auf dem Pull Request** (Lauf `37292715857`, Diff-informed **abgeschaltet** – der ganze Bestand wurde analysiert) | **grün.** Python: **0 Funde – 0 sicherheitsrelevant, 0 Qualitäts-Hinweise.** JavaScript: 0 Funde. Unterdrückt: ausschließlich die 2 seit 04.10.2026 begründeten `py/incomplete-url-substring-sanitization`-Negativ-Assertionen (`affiliate_marketer.py`, `governance_contract.py`). **Von den 6 Clear-Text-Fundstellen ist keine mehr da – und keine davon ist unterdrückt.** |

**Rückwärtskompatibilität:** `data/scorecard_history.jsonl` enthält Alt-Zeilen mit `secret_amber`/`secret_red`. Gelesen wird daraus nur `score` – die Historie bleibt gültig und wird nicht umgeschrieben. Die JSON-Oberfläche von `social_preflight --json` ist für die ENV-Felder seit 04.10. stabil (`required_env_names`/`missing_env_names`); die Variablen-Felder heißen jetzt einheitlich englisch-selbsterklärend (`required_var_names`/`missing_var_names`) – Verbraucher im Repository und in n8n: keine (geprüft; der einzige Abnehmer ist der Sicherheitsvertrag selbst). Die Signatur von `sch.missing_env()` ist unverändert (`social_calendar` u. a. laufen weiter).

---

## 6 · Runbook für künftige Funde

- **Neuer Bericht/ neues Feld:** Heißt es `secret`, `pass*`, `oauth`, `api_key`, `api_tok`, `mfa`, `trusted` oder `confidential`? Dann entweder wahrheitsgemäß umbenennen (`pflicht_env`, `zugang_*`, `nachweis_*`) – oder es gehört dort nicht hin. `test_zugangs_namensvertrag.py` sagt es sofort.
- **Neuer Kanal:** `pflicht_env:` in `data/social/channels.yaml` eintragen (nur Variablennamen), Secret unter *Settings → Secrets and variables → **Actions*** hinterlegen, Preflight laufen lassen. Details: `docs/RUNBUCH-SOCIAL-SECRETS.md`.
- **Kanal zeigt „braucht keine Zugangsdaten“, obwohl er welche braucht:** Das alte Feld `secrets:` ist noch drin – `pflicht_env_namen()` wirft laut. Feld umbenennen, fertig.
- **Gate meldet eine Fundstelle:** Die Annotation steht an der Codezeile im PR-Diff. Query-Quelle lesen, Datenfluss verstehen, konstruktiv heilen. Nicht unterdrücken – für die Clear-Text-Regeln blockiert das Gate die Unterdrückung ohnehin.
- **Security-Tab zeigt fremde Alert-Nummern:** Default-Setup noch aktiv → Abschnitt 1, Ursache B (einmaliges Deaktivieren per Klick).

---

## 7 · Hinweis für den Merge

Diese Arbeit liegt als eigener Pull Request vor (Branch `arena/01a10b5a-franksfinanzcheck-blog`). Der parallel entstandene, inhaltlich verwandte **PR #578** (Session `arena/01a10b34`) adressiert dieselben 6 Fundstellen mit derselben Kernidee (Namensvertrag); dieser hier geht darüber hinaus um: Umbenennung auch der Funktion `bucket_secrets` → `bucket_zugaenge` (latente `SensitiveFunctionCall`-Quelle, die mit zukünftigen Queries zurückkommen könnte), **Streichung der beiden Clear-Text-Regeln aus der Unterdrückungs-Whitelist des Gates** (Unterdrückungen blockieren künftig den Lauf) und das **Unterdrückungsverbot** als drittes Test-Bein. Sollte #578 zuerst gemergt werden, sind die Konflikte rein mechanisch (gleiche Dateien, gleiche Richtung); Auflösungsregel: **der Namensvertrag gewinnt**, danach `python3 -m unittest discover -s scripts/tests` laufen lassen – die Suite erkennt jeden Rückfall.
