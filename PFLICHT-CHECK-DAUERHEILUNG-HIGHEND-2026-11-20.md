# Pflicht-Check `Integritäts-Siegel` – Highend-Dauerheilung (20.11.2026)

**Stand:** 20.11.2026 · **Vorgang:** Dauerzustand (Option B, 20.09.2026) auf Highend-Level gebracht,
damit die Aktivierung als Pflicht-Check von `main` ein sauberer, separater Admin-Schritt bleibt –
und der 01.01.2027 nicht als Überraschung zuschlägt · **Vertrag:** C18
(`scripts/governance_contract.py`) · **Runbook:** `docs/PFLICHT-CHECK-RUNBOOK.md`

**Die Aktivierung selbst wurde NICHT ausgeführt.** Rulesets ändern ist Admin-Aufgabe (C15)
und laut Auftrag ausdrücklich ein separater Schritt. Nichts im Ruleset, an der Frist
(`pruefung_bis` 2026-12-31) oder an der weich gezeichneten Meldung wurde eingestellt.

---

## 1. Der Befund

Der Dauerzustand seit 19./20.09.2026 ist ehrlich dokumentiert: `main` verlangt den Check
`Integritäts-Siegel` nicht, kein Lauf dieses Hauses ändert das Ruleset (C15: Admin-Aufgabe), und das
rote Kreuz hielt nachweislich keinen Merge auf (PR #327 bei `FAILURE` gemergt, `4b91938`).
Seit dem 20.09.2026 war aber keiner der drei Träger dieser Entscheidung nachgezogen:

| # | Befund | Beleg |
|---|---|---|
| 1 | **Die Belege waren veraltet.** Sie nannten „vier Einträge“ aus zwei Rulesets. Tatsächlich stehen seit dem 30.09.2026 (Ruleset #24247857 „Premium-Schutz für main“, `required_linear_history`) **sieben Einträge aus drei Rulesets** im effektiven Branch-Schutz – ohne `required_status_checks`, ohne `pull_request`-Regel, ohne Bypass-Akteure. Eine Erklärung, deren Belege still altern, ist die zweite Wahrheit, gegen die C18 antritt. | `GET /rules/branches/main` und `GET /rulesets/*`, 20.11.2026 |
| 2 | **Der 01.01.2027 kam ohne Vorwarnung.** Die einzige Erinnerung war „noch X Tage“ im Log des PR-Gates – ein Kanal, den niemand regelmäßig liest. Ohne Nachziehen (verlängern oder aktivieren) kippt die Wache mit Sperrtag auf Exit 1 in **jedem** PR auf `main`. | `pflichtcheck_guard.py`, Stand vorher |
| 3 | **Die Aktivierung war nicht hektikfrei verifizierbar.** Der Runbook nannte Klickweg und PUT-Body, aber keine verbindliche Reihenfolge für den Nachweis danach (Zielzustand gelesen? Bypass vorhanden? `--strict` grün? Erklärung zurückgebaut? Automation schrieb wirklich?). | `docs/PFLICHT-CHECK-RUNBOOK.md`, 20.09.2026 |
| 4 | **Zwei Kohärenz-Lücken in der Governance-Kette.** Ein neuer Governance-Schritt ohne Signatur im Vertrag hätte die Deckungsgleichheit Gate↔Vertrag (C1/C3-Klasse) gebrochen; ein Schritt ohne Erzeuger-Erklärung wäre als Zeile ohne Messung (C42, #806) rot geworden. Beides wurde vorab geschlossen, nicht hinterher. | `test_revenue_measurement.TestVerdrahtung`, C42 |

Zusätzlich auffällig (und offen dokumentiert): Der für Repository-Analysen genutzte
Probing-Kontext meldet heute `permissions: {"admin": true, …}` – die Reparatur wäre
**technisch ausführbar**. Sie wurde bewusst **nicht** ausgeführt: Der Auftrag lautet,
die Aktivierung als separaten Admin-Schritt zu behandeln. Der CI-relevante Token des PR-Gates
(`github.token`, `contents: read`) hat weiterhin kein `administration:write`.

---

## 2. Die Reparatur

### 2.1 Frist-Wache (neu, dauerhaft, automatisiert)

`scripts/pflichtcheck_guard.py --frist-report PFAD` berechnet die Restlaufzeit der Frist
**offline aus dem Vertrag** (kein Netz, kein Token, keine Schreibrechte) und schreibt eine
Governance-Befundtabelle. Verdrahtet als Schritt „Pflicht-Check-Frist-Wache (Dauerzustand)“
im wöchentlichen `premium-governance.yml` (Gate-Kennung `pflichtcheck`):

| Lage | Code | Gate-Verhalten |
|---|---|---|
| Restlaufzeit > 35 Tage (heute: 41) | `dauerzustand_frist` · INFO | grün, Hinweis, **kein Issue** |
| Restlaufzeit ≤ 35 Tage (ab 26.11.2026) | `dauerzustand_frist` · AMBER | **actionable → gebündeltes Governance-Issue** (die längst fällige Menschen-Entscheidung: verlängern oder aktivieren) |
| Frist abgelaufen oder unbrauchbar (ab 01.01.2027) | `dauerzustand_frist` · RED | **rot** – Wochenlauf rot, `::error::`, Issue |
| Erklärung zurückgebaut (aktiviert oder bewusst verworfen) | `dauerzustand_weg` · INFO | grün – nichts zu messen |

Warum 35 Tage: Der Montagslauf (15.05Z) muss den Ablauf sehen, bevor er hart wird – das sind
fünf Wochentakte Vorlauf (erster AMBER-Takt: 30.11.2026, dann 07./14./21./28.12.2026).
Verlängern datiert `pruefung_bis` um – **Menschen-Entscheidung**, kein Lauf tut das.
Die Frist-Wache ändert **kein** Urteil des PR-Gates; sie erzeugt den Handlungsdruck, der fehlte,
statt den Alarm zu drehen. Selbsttest: Fallgruppe 21 (Grenzen exakt: 41/36/35/Stichtag/danach,
unbrauchbare Frist → RED, fehlende Erklärung → INFO `dauerzustand_weg`).

Gate-Seite: `governance_gate.py` kennt die Kennung `pflichtcheck` (STEPS, Label
„Pflicht-Check-Frist (Dauerzustand)“) und zählt `dauerzustand_frist` als handlungswürdiges
Amber (#206-Policy: Wartungsfälle mit Vorlauf sind handlungsbedürftig). Der Vertrag trägt die
emit-Signatur (STEP_SIGNATURES) – **Gate- und Vertrags-Seite bleiben deckungsgleich**, die
bestehende Testsuite erzwingt das. C42 führt `pflichtcheck` als dokumentierte Ausnahme
(wie `automation`): offline, kein Report-Scanner.

### 2.2 Belege nachgezogen (kein Grünwaschen)

`PFLICHT_CHECK_DAUERZUSTAND.belege` in `scripts/governance_contract.py` beschreibt jetzt den
**gemessenen** Stand vom 20.11.2026: 7 Einträge aus #23710849 / #24247857 (`required_linear_history`,
ausdrücklich kein Status-Check) / #23705980 · kein Bypass-Akteur (explizites `[]`, kein
Sichtbarkeitsartefakt) · `integrity_guard.py --gate` grün mit **55** Kerndateien ·
CI-Token ohne `administration:write`, Probing-Kontext mit `admin:true` – und warum das die
Aktivierung trotzdem nicht zu einer Repo-Aufgabe macht (C15). `festgestellt` (2026-09-19),
`dokumentiert` (2026-09-20) und `pruefung_bis` (2026-12-31) bleiben **unverändert** –
nur die Belege altern, nicht die Entscheidung.

### 2.3 Runbook: Nachprüfung + verbindliche Aktivierungs-Verifikation

`docs/PFLICHT-CHECK-RUNBOOK.md` trägt jetzt (a) die datierte **Nachprüfung 20.11.2026**
(live verifiziert, Tabelle), (b) den alten Befund als archivierten Abschnitt mit Landmarker
(**Historie**, unverändert als Beleg), (c) die neue **Frist-Wache**-Beschreibung, und (d) einen
neuen Abschnitt **„Verifikation nach der Aktivierung (Admin-Schritt, verbindlich)“**: sieben
Schritte in verbindlicher Reihenfolge – effektive Regeln lesen (genau ein
`required_status_checks` mit Kontext `Integritäts-Siegel` / App 15368), Ruleset im Ganzen
prüfen (Bypass unverändert `always` für Actions), `--strict` grün, Dauerzustand im selben PR
zurückgebaut, Automation nachweislich schreibend (Writer-Cron mit State-Commit), Frist-Wache
INFO `dauerzustand_weg`, Governance-Vertrag 47 Regeln grün. Jeder ✗-Schritt heißt:
**nicht als repariert melden**.

### 2.4 Kohärenz in der Kette

- `governance_contract.STEP_SIGNATURES` um `pflichtcheck` erweitert (C1-Position, C3-Messkette,
  Deckungsgleichheit mit dem Gate – geprüft von `test_revenue_measurement.TestVerdrahtung`).
- `governance_contract.C42_OHNE_ERZEUGER` um `pflichtcheck` erweitert (wie `automation`).
- `integrity-lock.yml`: allein ein datierter Kommentar-Nachtrag; **Trigger, Job und Schritte unverändert**.
- `QUALITAETS-REGELWERK.md`, `ff-ausliefern/references/ci-und-hugo-build.md`: datierte Hinweise auf die Frist-Wache.
- Neue Tests `scripts/tests/test_pflichtcheck_frist.py` (23 Tests: Grenze, Report-Format,
  Gate-Klassifizierung inkl. `decide_policy`, Workflow-Reihenfolge + Offline-Vertrag des
  Schritts, CLI-Verhalten unter injizierter Uhr).
- `docs/GOVERNANCE-KONTRAKT.md` regeneriert (nur Stand-Datum).

---

## 3. Was ausdrücklich NICHT getan wurde

- **Kein Ruleset angefasst.** Weder #23710849 noch #24247857 noch #23705980 wurden gelesen-only
  verifiziert und **nicht** verändert – die Aktivierung bleibt der separate Admin-Schritt.
- **`pruefung_bis` nicht verlängert** (2026-12-31 unverändert) und `festgestellt`/`dokumentiert` nicht neu datiert.
- **Kein Grünwaschen:** Der weiche Pfad bleibt exakt wie dokumentiert (🛑 bleibt lesbar,
  `::warning::`, Exit 0); `--strict` unverändert. Der harte Stopp vor dem Wächter unverändert.
- **Kein Test gelockert.** Neue Prüfungen kamen dazu; keine Assertion entspannt; kein `skip`,
  kein `xfail`, kein `continue-on-error`, kein `if:` am Job, kein Pfadfilter.
- **Kein zweiter Wahrheitsträger:** Der Frist-Wache-Text referenziert denselben Vertrag
  (`PFLICHT_CHECK_DAUERZUSTAND`), keine Kopie; Name, Runbook und Watch-Pfad unverändert.

---

## 4. Verifikation (lokal, 20./21.11.2026)

| Prüfung | Ergebnis |
|---|---|
| `python3 scripts/pflichtcheck_guard.py --branch main` (live, GET-only) | **BEKANNT**, Exit 0, 🛑 + `::warning::` |
| `python3 scripts/pflichtcheck_guard.py --selftest` | 21 Fallgruppen grün |
| `python3 scripts/pflichtcheck_guard.py --frist-report …` (heute) | **GREEN**, `dauerzustand_frist`, 41 Tage, Exit 0 |
| `governance_gate.classify("pflichtcheck", …)` je Lage | INFO→grün · AMBER→amber+actionable · RED→red+actionable (→ Issue) |
| `python3 scripts/governance_contract.py --quick` | **47 Regeln erfüllt** (vorher 47 – keine Regel geschwächt) |
| `python3 scripts/governance_contract.py --quick --md` | regeneriert (nur Stand-Datum) |
| `workflow_vertrag_wache.py --online --gate` | 103 Workflows vertragsgemäß |
| `actions_version_guard.py --gate` / `artefakt_waechter.py` | Pins einheitlich / 709 Artefakte heil |
| `scripts/selftest_runner.py` (Quality-Gate, requirements-ci.txt) | **288 Wachen grün · 576 Uhr-Proben** (+97/+1461 Tage) |
| `test_pflichtcheck` (39) + `test_pflichtcheck_frist` (23) + `test_ruleset_restoration` (29) | **91 Tests OK** |
| `test_revenue_measurement` (Gate↔Vertrag-Deckungsgleichheit, 36) | OK |
| `test_integrity_guard` (66) · `test_workflow_vertrag_wache` (12) · `test_actions_version_guard` (22) · `test_governance_messfrische` (17) | OK (117) |

### 4.1 Nachtrag 21.11.2026 – eine Zahl zurückgenommen

Die frühere Zeile „Pflicht-Check-/Governance-Testmodule (22 Module) · 377 Tests OK"
ließ sich aus dem Repository **nicht reproduzieren**: Es gibt keine Datei und keinen
Workflow, der diese 22 Module benennt, und keine Modulmenge des Repos ergibt beim
Nachzählen 377 Tests. Die Zeile war damit eine Behauptung, kein Messwert. Sie ist
durch die einzeln gemessenen Module oben ersetzt (91 + 36 + 117 = 244 Tests, alle
nachgezählt am 21.11.2026). Die Aussage „keine Assertion entspannt" bleibt davon
unberührt und ist am Diff prüfbar; die neue Frist-Wache bringt 23 eigene Tests mit.

Live-Belege (GET, 20.11.2026): `rules/branches/main` → 7 Einträge; Rulesets #23710849 /
#24247857 / #23705980 → `active`, je `bypass_actors: []` (explizit leer), `~DEFAULT_BRANCH`;
permissions des Probing-Kontexts → `admin:true`.

---

## 5. Was Frank tun muss (der separate Admin-Schritt)

1. Klickweg oder PUT wie in `docs/PFLICHT-CHECK-RUNBOOK.md` §„Reparatur für Frank"
   (`docs/integritaets-lock-ruleset.json` ist die versionierte Vorlage – Kontext
   `Integritäts-Siegel`, App **15368**, Bypass **nur** GitHub Actions `always`, PR-Regel
   **0 Approvals**). Ziel: #23710849 nach im Browser bestätigter ID (ursprünglicher Auftrag
   #23695872). 404/403 ist **kein Erfolg**.
2. Danach die **sieben** verbindlichen Verifikations-Schritte desselben Runbooks
   (§„Verifikation nach der Aktivierung"). Erst danach ist der Beschluss vollzogen.
3. Der Dauerzustand wird **im selben PR** zurückgebaut (Schritt 4 der Verifikation); die
   Frist-Wache meldet danach INFO (`dauerzustand_weg`) und entfernt sich selbst aus dem
   Handlungs-Pfad, ohne dass an `premium-governance.yml` weiter gedreht wird.
4. Alternativ, ohne Aktivierung: Frank datiert `pruefung_bis` mit Begründung neu – die
   Frist-Wache wird dann ab 35 Tagen Vorlauf wieder warnen (AMBER → Issue), danach RED.

**Rollback:** Die Code-Änderungen sind additiv. Rückbau: `--frist-report`-Schritt aus
`premium-governance.yml` (oder Schritt leeren → Gate meldet `dauerzustand_frist` nicht mehr),
`pflichtcheck` aus `STEPS`/`STEP_SIGNATURES`/`C42_OHNE_ERZEUGER`/`ACTIONABLE_AMBER`,
`test_pflichtcheck_frist.py` löschen, Frist-Wache-Blöcke in Runbook/Regelwerk als Historie
stehen lassen. Der dokumentierte Dauerzustand bleibt davon unberührt.

---

## Verifikationsmatrix nach Runbook (gemessen 21.11.2026, 11:2x UTC)

Der Admin-Schritt wurde **nicht** ausgeführt (ausdrückliche Anweisung, siehe unten).
Die sieben Runbook-Schritte sind trotzdem abgearbeitet, damit der Ist-Zustand
belegt ist und nach einer späteren Aktivierung nur noch verglichen werden muss.

| # | Runbook-Schritt | Ist-Stand | Ergebnis |
|---|---|---|---|
| 1 | `rules/branches/main` trägt genau einen `required_status_checks` mit Kontext `Integritäts-Siegel` | 7 Regel-Einträge, **kein** `required_status_checks` (`ctx` durchweg `null`) | ✗ nicht erreicht |
| 2 | Ruleset #23710849: `bypass_actors:[{15368, Integration, always}]`, 4 Regeln | `bypass_actors: []`, Regeln nur `deletion`, `non_fast_forward` | ✗ nicht erreicht |
| 3 | `pflichtcheck_guard.py --branch main --strict` → Exit 0 | **Exit 1**, `::error::`, Frist hinweisend | ✗ rot – wie erwartet |
| 4 | Dauerzustand auf `{}` zurückgebaut | `PFLICHT_CHECK_DAUERZUSTAND` noch gesetzt (Frist 31.12.2026) | ✗ erst nach Aktivierung |
| 5 | Writer-Workflow beweist Bypass | ohne Bypass nicht prüfbar | ⊘ blockiert durch 2 |
| 6 | `--frist-report` → `INFO` | **INFO**, 40 Tage Vorlauf, kein Handlungsbedarf | ✓ |
| 7 | Governance-Vertrag + Selbsttests | **47/47 Regeln grün**, Pflicht-Check-Module grün | ✓ |

**Lesart:** Schritt 3 rot ist kein Rückschritt, sondern die *korrekte* Messung des
nicht aktivierten Admin-Schritts. Die Wache ist so gebaut, dass sie den
Dauerzustand im `--strict`-Modus als Vorfall meldet — genau das tut sie. Ein
„grün" an dieser Stelle wäre der Beleg dafür, dass die Wache nicht mehr prüft.

**Warum der Admin-Schritt trotz `admin: true` des Tokens nicht ausgeführt wurde:**
Er steht im direkten Widerspruch zu einer früheren ausdrücklichen Anweisung
(„Admin-Aktivierung des Pflicht-Checks NICHT ausführen"). Technisch wäre er
möglich; die Entscheidung darüber liegt bei Frank. Nach Freigabe ist die
Reihenfolge: PUT auf #23710849 → Schritte 1, 2, 5 erneut messen → Dauerzustand
im selben PR auf `{}` → Schritte 3, 6, 7 wiederholen.

Ein CSP-Eintrag für `static.cloudflareinsights.com` (Ursache des roten
`layout-audit`) ist ebenfalls **nicht** gesetzt: Der Beacon ist im Repo-HTML
nicht vorhanden (0 Treffer über 131 Seiten), kommt also von der Edge. Das ist
eine Sicherheitsrichtlinie — die ändert man nicht als Nebenwirkung eines
Faktenfrische-PRs.
