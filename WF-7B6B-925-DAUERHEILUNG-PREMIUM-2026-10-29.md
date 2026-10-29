# Vorgang WF-7B6B · #925 – Dauerheilung (Snippet-SSOT an der Quelle)

**Datum:** 29.10.2026
**Meldung:** #925 „🔧 Wartung · Lesbarkeit & Gestaltung · Vorgang WF-7B6B“ (Alert-Key `WF-7B6B`, Bereich *Lesbarkeit & Gestaltung*, Workflow *E2E-Tests (Playwright)*)
**Auslöser:** Geplanter Lauf **40677860531** auf `main` (Commit `f56e25c7`, 28.10.2026, 11:10:18Z). Der Schritt „Snippet-Gate – Snippetfenster und Rangfolge“ war rot. Die Meldung (11:11:15Z) riet zu API-Schlüsseln, GitHub-Ausfall und Neustart.

---

## Kurzfassung

- **Ursache:** Ein *Schreiber* hat den Verstoß erzeugt, keine Wache hat ihn übersehen. Das Keyword-Gate (`keyword_optimizer.heal_description`) setzte am 27.10.2026 um 19:58:50Z das Schlüsselwort `DSL Hacks:` vor eine bereits passende Description – **153 Zeichen, aber 1011 px**. Der Schreiber rechnete gegen seine **eigene** Grenze (160 Zeichen) und war grün; das Fenster des Marktes (155 Zeichen / 985 px, SSOT `scripts/serp_limits.py`) war abgeschnitten. Zeichenzahl ist nicht Breite – genau die Lektion vom 27.10.2026, diesmal im Schreibpfad statt im Messpfad.
- **Schaden:** Der Verstoß stand **~15 h 12 min** auf `main` (27.10. 19:58 → 28.10. 11:10). Der Commit kam ohne Pull Request direkt auf `main` (Gate-Heilung des Deploy-Laufs), das Snippet-Gate läuft im PR- und Nachtpfad – die erste Messung war also der nächtliche Lauf. In diesem Fenster ausgeliefert wurde die Seite mit einer abgeschnittenen Description. Der Inhalt selbst ist seit dem 28.10. 16:14Z grün (redaktioneller Retrofit `f5fb9b956`, 140 Zeichen / 934 px); die Meldung bleibt offen, bis der nächste geplante Lauf grün läuft.
- **Sofortheilung:** `f5fb9b956` (28.10. 16:14:55Z) ersetzte die Description. Zusätzlich heilt dieser Vorgang die Klasse: die Wache kürzt an der Quelle deterministisch (`metadaten_wache.py --fix` → 134 Zeichen / 899 px).
- **Dauerheilung (dieser Vorgang):** (1) Die **Schreiber** importieren die SSOT statt eigene Grenzen zu pflegen – `keyword_optimizer`, `meta_optimizer`, `quality_score`. (2) Die Metadaten-Wache läuft **im Deploy-Pfad, direkt hinter den Schreibenden**, und heilt die Snippet-Klasse (M2/M7) plus `lastmod < date` (M3) an der Quelle – toleriert, aber laut (C34: kein Deploy-Blocker). (3) Das nächtliche Snippet-Gate bleibt das harte PR-Gate. (4) Die Alarm-Meldung erkennt die Messgates als eigene Klasse und gibt den Mess-Rat statt des API-Key-Rats. Dazu: sechs Regressionstest-Dateien, Simulationsszenarien, Blustradius-Einträge, Vertragseintrag und ein Runbook-Abschnitt in der Meldung.

---

## 1. Zeitleiste (UTC)

| Zeit | Ereignis | Beleg |
|---|---|---|
| 27.10. 19:58:50 | Commit `7a0cf57b7` (Content-Bot, „fix(gate): Kadenz-/Titel-/Cover-Heilungen vor Veröffentlichung (automatisch)“) stellt `DSL Hacks:` vor die Description von `content/posts/2026-09-27-wlan-verstaerker-vs-mesh-wlan-was-brauchst-du-wirklich/index.md`: 142 → **153 Zeichen / 1011 px**. Kein PR, direkter Push auf `main` | Commit-Diff |
| 28.10. 10:55:59 | `f56e25c7` (Scorecard/Live-Bestand versiegelt) – der Verstoß steht weiter auf `main` | Commit |
| 28.10. 11:10:18 | Geplanter E2E-Lauf 40677860531 rot im Schritt „Snippet-Gate – Snippetfenster und Rangfolge“ (Cron `0 5 * * *`, verzögert gestartet) | Run 40677860531 |
| 28.10. 11:11:15 | Meldung #925 angelegt – Klasse `allgemein`, Rat: API-Key, GitHub-Ausfall, transienter Fehler | Issue #925 |
| 28.10. 16:14:55 | `f5fb9b956` („redaktion: Bestand auf Capital/WiWo/ZEIT-Standard gehoben“) ersetzt die Description: **140 Zeichen / 934 px**, konform | Commit |
| 29.10. | Dieses Vorgang: Schreiber an die SSOT gebunden, Wache an der Quelle selbstheilend, Alarm-Rat korrigiert | dieser PR |

**Latenz Schreiben → Finden: 15 h 12 min.** Der Commit lief ohne PR, also ohne PR-Gate; gemessen wurde erst in der Nacht.

---

## 2. Ursache

Die verletzende Zeile in `7a0cf57b7`:

```diff
-description: "WLAN-Verstärker oder Mesh-WLAN? So findest du 2026 heraus, was dein Zuhause wirklich braucht – mit klaren Kosten und einer Entscheidungshilfe."   # 142 Z. / 933 px – konform
+description: "DSL Hacks: WLAN-Verstärker oder Mesh-WLAN? So findest du 2026 heraus, was dein Zuhause wirklich braucht – mit klaren Kosten und einer Entscheidungshilfe."   # 153 Z. / 1011 px
```

Gemessen mit der SSOT (`scripts/serp_limits.py`, Arial-/Helvetica-Kernmetrik 14 px):

| Text | Zeichen | Breite | Befund |
|---|---|---|---|
| vorher | 142 | 933 px | – |
| nach `7a0cf57b7` | 153 | **1011 px** | `zu-breit` |
| nach `metadaten_wache.py --fix` | 134 | 899 px | – |

Drei Baustellen, keine davon „die Wache war blind“:

1. **Der Schreiber hatte eigene Grenzen.** `keyword_optimizer` rechnete mit 160 Zeichen (und `meta_optimizer` mit 70–160). 153 < 160 = grün. Beide Zahlen sind Altlasten von **vor** der SSOT (#917, 27.10.2026). Ein Schreiber, der gegen eine eigene Grenze punktet, produziert genau dann einen Verstoß, wenn die echte Grenze enger ist – und Breite war in seiner Rechnung überhaupt nicht vorgesehen.
2. **Gemessen wurde erst spät und am gebauten HTML.** `seo_cockpit` (Snippet-Gate) liest die SSOT korrekt, läuft aber in `e2e.yml` im PR- und Nachtpfad. Ein Commit ohne PR umgeht den PR-Pfad; die nächtliche Messung kam 15 h später. Die Quelle (`metadaten_wache`) hatte zu diesem Zeitpunkt keinen Heiler – sie meldet(e) nur.
3. **Der Alarm-Rat passte nicht zur Klasse.** Ein Schritt, der Breiten **misst**, kann an einem abgelaufenen API-Schlüssel, einem GitHub-Ausfall oder einem transienten Fehler nicht rot werden. Die Meldung nannte den roten Schritt korrekt und deutete ihn falsch.

---

## 3. Warum die Meldung nicht half

Dieselbe Klasse wie #654: Der rote Schritt war korrekt benannt, das Runbook war es nicht. `Snippet-Gate – Snippetfenster und Rangfolge` ist eine Messung am gebauten HTML; ihre drei häufigsten „Ursachen“ (Schlüssel, Plattform, Neustart) können sie nicht rot machen. Die einzige Ursachenklasse, die übrig bleibt, ist ein **Messbefund am Bestand** – und der wird nicht durch Neustart kleiner. Korrigiert in Abschnitt 4.

---

## 4. Heilung: was geändert wurde

| Datei | Änderung |
|---|---|
| `scripts/serp_limits.py` | SSOT erweitert: `auf_snippet_kuerzen(text, min_zeichen=…, satzende=…)` – die EINE Stelle, an der gekürzt wird. Wortgrenze, BEIDE Grenzen, ehrliches Ende (`…` bzw. das verlangte Satzzeichen), `None` wenn kein Präfix passt |
| `scripts/metadaten_wache.py` | Neuer Modus `--fix`: `heile_snippet` (M2/M7, kürzt über die SSOT), `heile_lastmod` (M3, nur veröffentlichte, setzt `lastmod` auf das Publikationsdatum), `heile_datei` als Zeilen-Rewriter. Idempotent, meldet „Geheilt: n“ |
| `scripts/keyword_optimizer.py` | `heal_description` SSOT-gebunden: Schlüsselwort-Präfix wird nur gesetzt, wenn das Ergebnis die SSOT einhält; Addons werden gegen die Obergrenzen geprüft; Schnitt über `auf_snippet_kuerzen`; Schritt 5 behält bei Nicht-Können die alte, konforme Fassung. Selftest um #925-Proben erweitert |
| `scripts/meta_optimizer.py` | Grenzen importiert (`DESC_MIN/DESC_MAX` = SSOT), `generate_description` schneidet gegen die SSOT, `extend_description` gegen `min_zeichen=0`, `fix_meta` Schritt 0/1 SSOT-gebunden – inklusive des Satzende-Heilers am Limit (kürzen **und dann** punktieren, keine zweite Schneidestelle) |
| `scripts/quality_score.py` | Meta-Regel liest `serp_limits.passt(desc, min_zeichen=0)` (Zeichen **und** Breite). Wirkt nur auf `publish_gate`/Reserve, überspringt Entwürfe |
| `scripts/keyword_gate.py` | Berichtstexte auf SSOT-Wortlaut |
| `.github/workflows/deploy.yml` | Nach dem Keyword-Gate: **Metadaten-Selbsttest** + **Metadaten-Wache – Quelle (Snippet-SSOT, selbstheilend, C34-toleriert)**. Geheiltes geht in den Commit „Gate-Heilungen“; der Restbefund geht über `werkzeugbefund.py` an das Siegel |
| `data/blustradius-deploy.yml` | Zwei Einträge: Selbsttest als `gate-selbsttest`, Wache als `werkzeug` (darf nie blockieren, meldet an `release-seal`) |
| `.github/workflows/e2e.yml` | Kommentar korrigiert: `metadaten_wache` ist **strenger** als das Gate (jeder M1–M7-Befund rötet, nicht nur die drei Snippet-Codes) und heilt die Snippet-Klasse seit diesem Vorgang an der Quelle |
| `.github/workflows/alert-on-failure.yml` | Neue Runbook-Klasse `messgate-bestand` für die Messgates des E2E-Laufs (Snippet-Gate, Metadaten-Wache, Linktext-Wache, H1-Wache) plus vierpunktiger Rat: gemessen nicht geraten · Repro über Log/Build/Quelle · Heilung inkl. `metadaten_wache.py --fix` und Regressionstests · „kein API-Key, kein Neustart“ |
| `scripts/tests/sim/alert_scoping_sim.mjs` | Drei Szenarien (#925-Reproduktion, Metadaten-Wache, Gegenprobe: `E2E-Suite ausführen` ohne Messbezug behält das allgemeine Runbook) – Simulation jetzt 64 Szenarien |
| `scripts/tests/test_serp_limits.py` | Klasse `Kuerzen` + `Bindung` + Probe für den `satzende`-Parameter (29 Tests) |
| `scripts/tests/test_metadaten_wache.py` | Klasse `SnippetHeilungTests`: #925 geheilt, Zeilenzahl unverändert, idempotent, konform bleibt konform, zu kurz wird nicht verlängert, unmessbar in der Mitte bleibt liegen, `lastmod` geheilt, Entwürfe unberührt, `--fix` konvergiert gegen 0 |
| `scripts/tests/test_keyword_optimizer.py` (neu) | SSOT-Bindung, #925-Heilung/Idempotenz, `W`×300 bleibt liegen, Satzende ohne SSOT-Verstoß |
| `scripts/tests/test_meta_optimizer.py` (neu) | SSOT-Bindung, Generate/Extend/Audit, Satzende am Limit |
| `scripts/tests/test_quality_score_meta.py` (neu) | SSOT-Bindung der Meta-Regel, 155 grün, 160 kostet, Breite kostet, Untergrenze ist nicht dieses Scores Geschäft |
| `scripts/tests/test_alert_scoping.py` | `test_wf_7b6b_925_messgate_hat_eigenes_runbook` (Erkennung, Klasse, Rat-Inhalte) + statische Absicherung der Simulationsszenarien (28 Tests) |
| `scripts/tests/test_reserve_pipeline.py` | Fixture `DESC_OHNE_PUNKT` auf einen SSOT-konformen Text gestellt (die alte war 155 Zeichen / 996 px – selbst ein Verstoß; ihr Punkt-Anhang 156 Zeichen) |
| `CLAUDE.md` | Zwei Regeln im Abschnitt „Ein Snippet ist 155 Zeichen und 985 Pixel“: *Auch die Schreiber importieren die SSOT* und *Geheilt wird an der Quelle, nicht im Bericht* |
| `content/posts/2026-10-25-strategisch-sparen-so-kannst-du-deine-reisekasse-fuellen/index.md` | `lastmod` an `date` ausgerichtet (der eine M3-Befund des Arbeitsbaums – der lebende Belegfall für `heile_lastmod`) |
| `.github/workflows/alert-on-failure.yml`, `package.json` (Nachtrag) | Drei geerbte Defekte aus `main` geheilt: fehlendes Komma (Skript parsebar), toter Erkennungszweig, doppelter/ersetzter `test:sicherheit`-Schlüssel – siehe Abschnitt 7 |
| `WF-7B6B-925-DAUERHEILUNG-PREMIUM-2026-10-29.md` (neu) | dieser Bericht |

**Entscheidungen im Detail:**

- **Kürzen ist eine Aufgabe, nicht vier.** `auf_snippet_kuerzen` ist die einzige Stelle, die schneidet; Wache, Keyword-Schreiber, Meta-Schreiber und Satzende-Heiler rufen sie auf. Der Satzende-Heiler nimmt das Satzzeichen als Parameter derselben Funktion – kein zweiter, augenmaßlicher Schnitt im Schreiber.
- **Der Heiler verlängert nicht.** Ein zu kurzes Snippet ist eine Redaktionsentscheidung (welcher Satz gehört hinein?), keine Mechanik. `auf_snippet_kuerzen` prüft deshalb nur die **Obergrenzen**; `metadaten_wache` meldet `zu-kurz` weiter als Befund.
- **`None` ist eine erlaubte Antwort.** Wo kein Präfix das Fenster erfüllt (ein riesiges Wort, ein unmessbares Zeichen mitten im Text), lässt der Heiler den Text unverändert und meldet den Befund. Eine halb geschnittene Description wäre schlimmer als eine gemeldete.
- **Kein Deploy-Blocker (C34).** Ein zu langes Snippet darf die Live-Site nicht einfrieren. Die Wache im Deploy-Pfad läuft deshalb toleriert, meldet aber über `werkzeugbefund.py` an das Siegel – der Lauf färbt sich nach der Veröffentlichung rot. Sperrend bleiben: Keyword-Gate/Content-Gates (fachlich), Publish-Gate (Freigabe), und das Snippet-Gate im PR-Pfad.
- **Kein zweiter Grenzwert im Code.** `keyword_optimizer`, `meta_optimizer` und `quality_score` importieren `serp_limits`; ein eigene Zahl im Schreiber ist ab heute ein Testbefund (Klasse `Bindung`).
- **Die Messung bleibt am gebauten HTML.** Das Snippet-Gate misst, was der Browser bekommt – das ist die Wahrheit. Neu ist, dass die **Quelle** vor dem Bau geheilt wird, statt dass der Bericht danach rot wird.

---

## 5. Beweis

| Prüfung | Ergebnis |
|---|---|
| Reproduktion auf `f56e25c7` (Vorfall-Stand, aktuelle Skripte) | ❌ 153 Zeichen / 1011 px, Code `zu-breit` |
| `metadaten_wache.py --fix` auf diesem Stand | ✅ 134 Zeichen / 899 px, Befunde: 0 („Geheilt: 2“: Snippet + lastmod) |
| `keyword_optimizer.heal_description` mit `DSL Hacks` auf der 142-Zeichen-Fassung | ✅ 134 Zeichen / 899 px, idempotent – der Schreiber erzeugt den Verstoß nicht mehr |
| `python3 scripts/metadaten_wache.py` (Arbeitsbaum, 107 Dateien) | ✅ Befunde: 0 · `--selftest`: 13 Proben + Heiler-Proben grün |
| `python3 scripts/keyword_optimizer.py --selftest` | ✅ grün (inkl. #925-Proben) |
| `python3 scripts/meta_optimizer.py` (Audit, 100 Artikel) | ✅ 0 Artikel mit Meta-Problemen |
| `python3 scripts/quality_score.py --report` | ✅ Verteilung unverändert (95 Publish / 2 Human-Review / 3 Draft); die Meta-Regel feuert vor und nach der Bindung auf genau demselben einen Artikel |
| `python3 -m unittest scripts.tests.test_serp_limits` | ✅ 29 |
| `python3 -m unittest scripts.tests.test_metadaten_wache` | ✅ 23 (inkl. `SnippetHeilungTests`) |
| `python3 -m unittest scripts.tests.test_keyword_optimizer scripts.tests.test_meta_optimizer` | ✅ 12 |
| `python3 -m unittest scripts.tests.test_quality_score_meta` | ✅ 6 |
| `python3 -m unittest scripts.tests.test_alert_scoping` | ✅ 28 |
| `node scripts/tests/sim/alert_scoping_sim.mjs` (Alarm-Skript aus der YAML, echte Identitätsquelle) | ✅ 69 von 69 Szenarien (nach dem Merge von `main`, siehe Abschnitt 7) |
| `python3 scripts/blustradius_register.py --check` / `--selftest` | ✅ 71 Schritte erklärt · Selbsttest grün |
| `python3 scripts/governance_contract.py` | ✅ alle 42 Regeln |
| `python3 scripts/automation_premium_audit.py --strict` | ✅ Exit 0 |
| YAML aller 95 Workflows | ✅ parsen |
| `node --check` auf dem Alarm-Skript (async-umhüllt) | ✅ |
| `python3 -m unittest discover -s scripts/tests` (vollständig) | ✅ 4467 Tests · 4 Fehlschläge, **alle vier auf einem sauberen `origin/main`-Checkout gleich rot** (Inhalts-Register ×3, Versicherungs-Cluster) · 14 Überspringungen umgebungsbedingt |

**Nicht lokal bewiesen:** Hugo-Build und Playwright (die Sandbox hat kein Hugo; `public/` liegt hier nicht). Der Build-Nachweis des Snippet-Gates läuft im CI-Lauf des Pull Requests. Die Zahl 1011 px ist keine Schätzung, sondern `serp_limits.breite_px()` mit der Adobe-Kernmetrik – demselben Maß, mit dem das Gate im Lauf gemessen hat.

---

## 6. Offene Punkte (nicht Teil dieses Vorgangs)

1. **Kein Pflicht-Check auf `main`.** Der Commit `7a0cf57b7` kam ohne PR auf `main` – dieselbe Lücke wie beim Merge von #647 (#654). Die PR-Läufe des Branches wären rot gewesen. Drei Rulesets auf `main` (*Integritäts-Lock (PR-Gate)*, *Premium-Schutz für main*, *main – Unveränderlichkeit*) enthalten Löschschutz, Force-Push-Schutz und lineare Historie, aber keinen Status-Check (Abfrage der Rulesets-API, Stand 08.10.2026). Änderung ist eine Admin-Entscheidung (Governance-Regel C15). Empfehlung: „Playwright-Suite (Desktop + Mobile)“ und „Snippet-Gate – Snippetfenster und Rangfolge“ als Pflicht-Checks für `main`. Damit verkürzt sich die Latenz dieser Klasse von ~15 h auf die PR-Laufzeit.
2. **Meldung #925 bleibt offen**, bis der nächste geplante E2E-Lauf auf `main` grün ist (Cron verzögert sich; seit `f5fb9b956` ist der Inhalt konform). Der Pull Request trägt `Closes #925`; `vorgangs-abschluss.yml` schreibt den Vermerk.
3. **Die 6 roten Tests des Gesamtlaufs** sind auf dem unveränderten Stand genauso rot (Abschnitt 5). Sie gehören anderen Klassen (Faktenfrische-Zahl, Inhalts-Register, LCP-Manifest, Cluster-Verlinkung) und bekommen bei Bedarf eigene Vorgänge.

---

## 7. Nachtrag: Merge von `main` und drei geerbte Defekte (29.10.2026)

Der Zweig musste `main` vom 29.10.2026 übernehmen – und der Merge legte drei Defekte frei, die **main selbst** mitgebracht hat. Keiner gehört zum Vorgang #925, aber ohne sie wäre dieser Pull Request nicht grün (und das Fehler-Alerting wäre ausgefallen):

1. **Das Alarm-Skript war nicht einmal parsebar.** Im Rat der Klasse `worker-deploy-zugang` fehlte ein Komma zwischen zwei Ratzeilen – `node --check` über das github-script scheitert mit `SyntaxError: Unexpected string`. Ein Fehler-Alerting, dessen Skript nicht lädt, meldet nie wieder etwas (Schadensklasse #227). Behoben: Komma ergänzt, `node --check` grün.
2. **Eine Erkennung war toter Code.** `workerZugangFailed` hatte eine verwaiste Zeile hinter einem abgeschlossenen Statement; der Schritt „Produktions-Environment absichern“ wurde nicht erkannt und lief in den allgemeinen API-Key-Rat – dieselbe Klasse wie #925, ein Workflow weiter. Behoben: die drei Schrittnamen in einer Erkennung zusammengeführt. Die Simulations-Probe von main („Worker-Deploy: Environment-Policy ungeschützt“) läuft seitdem grün – sie war vorher überhaupt nicht lauffähig, weil das Skript nicht parste.
3. **`package.json` hatte `test:sicherheit` doppelt** – Klasse #654: `npm ci` bricht ab, die Manifest-Wache im Deploy- und im E2E-Lauf wird rot (der Nachtlauf vom 29.10. 11:23Z auf `main` ist genau daran gestorben). Beim Entschärfen zeigte sich die Ursache der Verdopplung: Die #922-Änderung hatte `worker_zugang` durch `worker_environment_guard` **ersetzt** statt ergänzt – npm übernahm still den letzten Wert, der Zugangs-Vertrag fiel aus der Sicherheitskette. Behoben: eine Fassung, die beide Verträge fährt; Manifest-Wache, Package-Vertrag und `test_worker_zugang` grün.

Dazu ein eigener Fund aus den Regressionstests: Die Fixture `DESC_OHNE_PUNKT` in `test_reserve_pipeline.py` enthielt einen Doppelpunkt und wird **unquittiert** ins Frontmatter geschrieben – ungültiges YAML (Klasse WF-9FD5 / #901). `automatic_write_protected` geht dann fail-closed, und der Heiler meldet „YMYL: Metadaten bleiben an die Freigabe gebunden“, statt zu heilen. Die Fixture ist jetzt colonfrei; der Test prüft wieder das, was er prüfen soll.

**Nach dem Merge:** Alarm-Simulation 69/69 Szenarien · `test_alert_scoping` 28/28 · Vollsuite 4467 Tests mit 4 Fehlschlägen, die auf einem sauberen `origin/main`-Checkout genauso rot sind (Inhalts-Register ×3, Versicherungs-Cluster) · Blustradius-Check grün · Governance-Vertrag alle 42 Regeln · Automation-Premium-Audit Exit 0 · Manifest-Wache grün.

---

---

## 8. Grenzen dieser Analyse

- Die Job-Logs des Actions-Laufs 40677860531 sind aus der Sandbox nicht abrufbar (Blob-Speicher nicht erreichbar). Belegt sind der rote Schritt und die Uhrzeit aus der Meldung #925 selbst sowie die verletzende Zeile aus dem Commit-Diff.
- Der Hugo-Build und damit der Messpfad am gebauten HTML laufen im CI, nicht hier. Local bewiesen ist der Quellpfad (Wache + Heiler) gegen denselben Commit.
- Die Pixelzahl ist ein Modell (Adobe-Kernmetrik für Helvetica/Arial 14 px) – aber **dasselbe** Modell, mit dem das Gate misst. Ein anderer Maßstab wäre ein eigener Befund, keine Rechtfertigung.
