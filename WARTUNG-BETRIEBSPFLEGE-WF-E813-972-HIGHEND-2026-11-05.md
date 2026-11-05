# Wartung · Betriebspflege · Vorgang WF-E813 (#972) — Highend, 05.11.2026

**Auftrag:** `Wartung · Betriebspflege · Vorgang WF-E813 #972 Bitte dauerhaft auf Highend-Level einer Profi-Agentur beheben.`
**Datum:** 05.11.2026 · **Branch:** `arena/fb50d4fe-franksfinanzcheck-blog` · **Basis:** `86c59a4e` (`main` bei Eröffnung; `origin/main` inzwischen `53a4bc6`, fünf Commits ohne Überschneidung mit den hier geänderten Dateien)
**Vorgänger:** `WARTUNG-BETRIEBSPFLEGE-WF-E813-972-HIGHEND-2026-11-03.md` · `ISSUE-STAU-DAUERHEILUNG-HIGHEND-2026-11-04.md` (§8: #972 bewusst als Herausgeber-Aufgabe stehen gelassen)

---

## 1. Kurzfassung

**#972 bleibt offen.** Der heutige Tageslauf
[42044923993](https://github.com/frank-hartung/franksfinanzcheck-blog/actions/runs/42044923993)
(14:25:48 UTC, `schedule`, `main` @ `4c700fb0`) ist rot, weil **zwei
unabhängige Live-Prüfungen** unverändert anschlagen: auf `/` und `/methodik/`
fehlen je fünf Pflicht-Header (F-01, zehn Einzelfunde), und das
authentifizierte Betriebsbild des Workers ist unvollständig
(`budget`, `turnstile`, `schluesselrollen`, `exporte`); `/healthz` liefert
keinen `bau`-Stempel. Beides sind **Inhaber-Aufgaben in Cloudflare bzw. in den
GitHub-Environment-Einstellungen**, keine Code-Regression. Die Sandbox
erreicht die Live-Domains nicht; ein Agent darf hier weder Schutzregeln noch
Secrets noch den Abschluss simulieren.

Der **neue, dauerhaft behebbare Repo-Befund** liegt eine Schicht davor: Der
tägliche Alarm war *nicht mehr selbst erklärend*. Der F-01-Auswerte-Schritt
sendete zehn Fehler-Annotationen und verlor damit die elfte Zeile – genau die
mit der Proxy-Diagnose und dem nächsten Schritt, auf die die Meldung #972
ausdrücklich verweist („Die Header-Annotation nennt die Diagnose"). In drei
Live-Läufen fehlte zusätzlich die Runner-Zeile dieses Schritts. Ein Rat, der
auf eine unsichtbare Nachricht zeigt, erzeugt Alarm-Müdigkeit statt Betrieb.
Das ist heute zentral, testfest und ohne jede Lockerung eines Gates geheilt.

| Ebene | Stand 05.11.2026 | Wer kann es ändern |
|---|---|---|
| F-01 · Transform Rule `FF Sicherheits-Header` | BEFUND, zehn fehlende Kopfzeilen, Proxy-Messung aktiv | Inhaber mit `CLOUDFLARE_API_TOKEN` (A1) |
| Worker · Environment `cloudflare-produktion` | 3 Ziele nicht erreicht; Deploy fail-closed gesperrt seit 25.10.2026 | Inhaber im GitHub-Dashboard (A1b/A4) |
| Worker · `/healthz` ohne `bau` | veralteter Deploy vor `ff-newsletter-2026-10-24` | folgt aus dem Deploy nach Schritt 3 (D2) |
| **Meldekette des Live-Jobs** | **Diagnose wurde still gekappt** | **Repository — heute geheilt** |

---

## 2. Der heutige Ist-Befund (belegt, nicht nacherzählt)

### 2.1 Der Lauf und seine Annotationen

`GET /repos/…/actions/runs/42044923993/jobs` und die Checks-API desselben
Laufs, 05.11.2026:

- **Quellseite (offline, mit Selbsttests):** ✅ success — alle vier
  Offline-Wachen grün.
- **Abhängigkeiten (Pins offline · Audit online):** ✅ success.
- **Live-Messung (täglich und auf Zuruf):** ❌ failure. Rot sind Schritt 4
  („Sicherheits-Header auswerten"), Schritt 6 („Worker-Zustand auswerten")
  und Schritt 7 („Live-Nachweis abschließen"). Die beiden täglichen
  Drift-Wachen (Schritte 8 und 9) sind grün mit Warnungen.
- **19 Annotationen** insgesamt, davon zehn `F-01 BEFUND` (je fünf Header auf
  `/` und `/methodik/`), drei `Worker STOERUNG`, eine `Live-Nachweis:
  header: BEFUND, worker: STOERUNG`, zwei Warnungen zum Environment, eine
  Notiz zu wartenden Freigaben und **zwei** Runner-Zeilen
  „Process completed with exit code 1.".

Der Check-Run enthält **keine** F-01-Zeile mit „Diagnose" oder
„`FF Sicherheits-Header`". Der Quelltext sendete sie (`naechster_schritt` ist
für `BEFUND` nie leer), die Meldung #972 zitiert sie – sichtbar war sie nicht.

### 2.2 Die Grenze, die den Rat geschluckt hat

GitHub zeigt höchstens **zehn Annotationen je Ebene und Schritt** (50 je Job)
und behält die ersten zehn; alles danach verfällt ohne Hinweis. Der
F-01-Schritt sendete:

```text
 1–10  F-01 BEFUND: <zehn fehlende Kopfzeilen>
   11  F-01 BEFUND: <Proxy-Diagnose / nächster Schritt>   ← verworfen
   12  Process completed with exit code 1.                ← verworfen
```

Die zweite Zeile ist in den Läufen `41470449168`, `41844410291` und
`42044923993` gleichermaßen belegt: Drei Schritte endeten dort mit Exit 1,
aber nur **zwei** Runner-Zeilen waren vorhanden. Der Schritt mit zehn eigenen
Fehlerzeilen hatte keine. Die Runner-Annotation zählt also in dasselbe Budget.
Wer zehn eigene Zeilen sendet, nimmt dem Runner die letzte – und wer die
Diagnose *hinter* die Befunde stellt, verliert zuerst die Diagnose.

### 2.3 Environment und Rechte (nur lesend geprüft)

`GET /repos/…/environments/cloudflare-produktion`, 05.11.2026:

```json
{"can_admins_bypass": true, "created_at": "2026-10-25T13:20:15Z",
 "deployment_branch_policy": null, "protection_rules": [],
 "updated_at": "2026-10-25T13:20:15Z"}
```

`created_at == updated_at`: Seit der automatischen Anlage ist nichts
konfiguriert worden. Lokal, read-only, mit dem vorhandenen GitHub-Zugang:

| Prüfung | Exit | Aussage |
|---|---|---|
| `python3 scripts/worker_environment_einrichten.py --pruefen` | 1 | Required Reviewer fehlt · Admin-Bypass aktiv/nicht belegbar · keine Branch-Policy |
| `python3 scripts/worker_environment_guard.py --check` | 1 | Deploy bleibt vor jedem Zugriff auf Cloudflare-Secrets fail-closed gesperrt |
| `--selftest` beider Wachen | 0 | Die Wachen selbst sind intakt |

Der Admin-Bypass ist weiterhin ein reiner Dashboard-Schalter; die GitHub-API
nimmt das Feld nicht an (im Vorgang vom 02./03.11.2026 mit HTTP 403 belegt).
Heute wurde **kein** Schreibversuch unternommen, keine Schutzregel verändert
und kein Secret gelesen oder geschrieben.

### 2.4 Was dieser Bericht ausdrücklich nicht behauptet

Die grünen Push-/PR-Läufe der Sicherheits-Wache sind kein Abschluss: Der
Live-Job läuft nur bei `schedule` und `workflow_dispatch`. Der heutige rote
Lauf ist die maßgebliche Messung. Ebenso wenig ist ein grüner Offline-Test,
ein grüner Deploy-*Plan* oder ein teilweise gemessenes Ziel ein Nachweis.
`sicherheits_nachweis.py --live` verlangt weiterhin beide vollständigen
Messungen und `abschluss_pruefen()` zusätzlich den erfolgreichen Live-Job mit
allen fünf Schritten. Keine dieser Regeln wurde angefasst.

---

## 3. Dauerhafte Heilung (H-A bis H-D)

### H-A · Ein Meldeplan statt vieler stiller Kappen

`scripts/github_kommando.py` kennt jetzt die Plattformgrenze als Konstante
(`ANNOTATIONEN_PRO_SCHRITT = 10`, `ANNOTATIONEN_PRO_JOB = 50`) und stellt mit
`annotationsplan()` einen **rein rechnenden** Plan bereit:

- `kopf` = Pflichtzeilen (Diagnose, nächster Schritt) stehen vorn und
  überleben immer;
- Einzelbefunde folgen, begrenzt auf das Restbudget;
- entfällt etwas, benennt eine Sammelzeile mit `{anzahl}` den Verlust;
- **ohne** Sammelzeile darf nichts entfallen (`ValueError`) — stilles
  Verwerfen ist genau der Fehler, der behoben wird;
- Reserve wird nur belegt, wenn sie gebraucht wird: zehn Befunde ohne
  Pflichtzeilen bleiben vollständig sichtbar;
- `MELDE_BUDGET_ROT = 9` reserviert für rot endende Schritte die zehnte Zeile
  für die Runner-Annotation.

Der Melder sendet nichts selbst; `annotation()` bleibt der einzige Weg nach
draußen, mit unverändertem Flucht- und Teststille-Schutz.

### H-B · Die Diagnose ist eine Aussage der Messung, nicht nur Prosa

`scripts/blog_header_gate.py` schreibt bei `BEFUND` ein neues Feld
`diagnose` mit der belegten Proxy-Lage aus `_proxy_satz()` in das JSON, das
der Auswerte-Schritt liest. Bisher stand sie **nur** im Markdown-Bericht. Für
`OK`, `TEILWEISE` und `STOERUNG` wird keine Diagnose erfunden.
`pruefe_messung()` prüft das Feld, falls vorhanden; ältere Artefakte ohne das
Feld bleiben lesbar (kein Bruch des Messvertrags).

### H-C · Der Live-Auswerte-Schritt sendet in der richtigen Reihenfolge

`scripts/sicherheits_nachweis.py` baut mit `annotationszeilen()` die
Sendeliste: **Diagnose → nächster Schritt → Einzelbefunde → Sammelzeile**.
Die vollständige Befundliste bleibt unverändert in der Lauf-Zusammenfassung
und im Artefakt `sicherheits-live-nachweis`; gekappt wird die Fassade, nie
der Nachweis. Der `--selftest` dieses Moduls prüft die Zehn-Zeilen-Grenze
jetzt selbst (D6), statt nur den Abschlussvertrag.

Zusätzlich nennt `scripts/worker_betrieb_wache.py` in **beiden**
Deploy-Diagnosen die Vorbedingung `cloudflare-produktion` (Required Reviewer,
exakt `main`, Admin-Bypass aus) mit dem read-only Prüfer
`worker_environment_guard.py --check` bzw. `npm run worker:environment`. Der
Rat „Zuerst deployen" war ohne diesen Schritt unvollständig: Der Deploy
bricht vor Wrangler fail-closed ab. Die Wache **misst** die Policy nicht und
behauptet das auch nicht – sie nennt die Bedingung. Die reine
Zugangs-Diagnose (falscher Leseschlüssel bei aktuellem Build) bleibt frei
davon, damit kein falscher Verdacht entsteht.

### H-D · Dieselbe Grenze an der zweiten Fundstelle

`scripts/layout_annotations.py` sendete zehn Funde **plus** einen
„+N weitere"-Hinweis – elf Zeilen, von denen ausgerechnet der Hinweis
verfiel. Es nutzt jetzt denselben `annotationsplan()` (zehn Zeilen: dieser
Schritt endet auch mit Fehlerbefunden auf Exit 0 und bekommt keine
Runner-Zeile). Damit gilt die Plattformgrenze an **einer** Stelle im
Repository, nicht in mehreren Köpfen.

### Vertragstests (Rückfallschutz)

| Test | Nagelt fest |
|---|---|
| `test_github_kommando.py::AnnotationsBudgetTest` | 0–40 Befunde, Pflichtzeilen zuerst, gezählter Verlust, `ValueError` bei fehlender/leerer Sammelzeile, falschem Platzhalter, zu großem Budget und voller Pflichtliste; Runner-Reserve |
| `test_sicherheits_nachweis.py::AnnotationsVertrag972` | Nachbau von Lauf `42044923993`: zehn F-01-Funde, Prüfung der **gesendeten** `::error::`-Zeilen, alle Funde weiter in der Summary, ungültige Diagnose = WACHE-FEHLER, grüne Messung ohne Diagnose |
| `test_blog_header_gate.py::ProxyDiagnose` | `diagnose` im JSON = Diagnose im Bericht; OK/STOERUNG erfinden keine |
| `test_worker_betrieb_wache.py` | Beide Deploy-Diagnosen nennen die Environment-Vorbedingung; Zugangs-Diagnose nicht; Dreiklang mit Runbook und Alarm-Rat |
| `test_alert_scoping.py` | Der Rat #972 darf nur auf eine Annotation zeigen, die der Meldeplan auch erzeugt; JSON-Diagnose → Plan → `--auswerten header` bleiben verdrahtet |
| `test_layout_annotations.py` | 13 Fehler → 9 sichtbare + „+4 weitere"; genau 10 Fehler → kein Hinweis; Frühwarnungen analog |

`docs/SICHERHEIT-BETRIEB-RUNBOOK.md`, neuer Abschnitt **F5**, hält den
Messbefund, die Plattformgrenze, die drei Heilungsteile und die Grenzen fest;
A1b Schritt 5 verweist darauf.

---

## 4. Verifikation

| Prüfung | Ergebnis |
|---|---|
| `npm run test:sicherheit` | ✅ Exit 0 · zwei Unittest-Blöcke 334 + 43 Tests, alle Wachen-Selbsttests grün |
| Offline-Testblock der Sicherheits-Wache (14 Module) | ✅ **379 Tests**, 1 Skip |
| Fokussierter Block der geänderten Module (6 Module) | ✅ **193 Tests**, 1 Skip |
| `python3 -m unittest scripts.tests.test_alert_scoping.VerhaltensSimulation -v` | ✅ Verhaltens-Simulation des Alarm-Routings grün |
| `python3 scripts/selftest_runner.py --python <CI-venv>` (gepinnte `requirements-ci.txt`) | ✅ **267 Wachen, 534 Uhr-Proben** (+97 d, +1461 d), 0 Befunde, kein Schreiben in den Arbeitsbaum |
| `python3 scripts/governance_contract.py --quick` | ✅ 45/45 Regeln in beide Richtungen |
| `python3 scripts/trigger_wache.py --check` | ✅ 99 Workflows, 0 Befunde |
| `python3 scripts/skript_syntax_wache.py` | ✅ 647 Dateien kompilieren |
| `python3 scripts/workflow_js_wache.py --check` | ✅ alle `github-script`-Blöcke kompilieren |
| `python3 scripts/skills_vertrag.py` | ✅ 90 Skills, 0 Befunde, 0 Warnungen |
| `python3 scripts/integrity_guard.py --gate` | ✅ 55 versiegelte Dateien, kein Drift |
| `npm run test:trigger` · `npm run workflow:js` · `npm run deps:check` | ✅ Exit 0 |
| `blog_header_gate.py --offline` · `cloudflare_edge_freigabe.py --selftest` · `worker_betrieb_wache.py --offline` · `sicherheits_nachweis.py --selftest` | ✅ Repo-Stand grün |
| Environment read-only (live) | ❌ Exit 1 — erwarteter, unveränderter Inhaber-Befund; beide Wachen-Selbsttests ✅ |

**Lokaler Vorher/Nachher-Nachbau** (heutiger Lauf als Attrappe: eine Antwort
mit `cf-ray`, aber ohne Sicherheits-Header; kein Netz, keine Secrets):

```text
Klasse: BEFUND · Exit 1 · Einzelbefunde: 10
ALT  gesendet: 11 Fehlerzeilen · davon bei GitHub sichtbar: 10
ALT  Diagnose in sichtbaren Zeilen: False
ALT  nächster Schritt sichtbar:     False
NEU  gesendet:  9 Fehlerzeilen · davon bei GitHub sichtbar:  9 (+ 1 Runner-Zeile)
NEU  Diagnose in sichtbaren Zeilen: True
NEU  nächster Schritt sichtbar:     True
NEU  Verlust benannt:              True
NEU  alle 10 Befunde in der Summary: True
```

Die gepinnten CI-Abhängigkeiten wurden ausschließlich in eine temporäre
virtuelle Umgebung **außerhalb des Repositories** installiert, um die
Selbsttests vollständig fahren zu können. Am Manifest, an Pins oder an
`.gitignore` wurde nichts geändert.

---

## 5. Schritte für die verantwortliche Person (unverändert, jetzt lesbar)

1. **Änderungen prüfen und auf `main` übernehmen.** Danach CI-Ergebnisse
   insbesondere Sicherheits-Wache (Offline-Job) und Qualitäts-Gate
   kontrollieren. `origin/main` ist gegenüber der Branch-Basis fünf Commits
   weiter (`53a4bc6`); die hier geänderten Dateien überschneiden sich nicht.
2. **Environment absichern** —
   [Settings → Environments → `cloudflare-produktion`](https://github.com/frank-hartung/franksfinanzcheck-blog/settings/environments):
   Required Reviewer `Frank Hartung`, *Deployment branches and tags* →
   `Selected` → ausschließlich `main`, *Allow administrators to bypass
   configured protection rules* → **aus**. Reviewer und Branch-Regel
   alternativ mit einem Token, das `Environments: read/write` darf:
   `python3 scripts/worker_environment_einrichten.py --anwenden --reviewer frank-hartung`.
   Den Bypass-Schalter stellt nur das Dashboard. Danach muss
   `npm run worker:environment` Exit 0 liefern.
3. **Zugang hinterlegen** (`CF_WORKERS_DEPLOY_TOKEN`,
   `CLOUDFLARE_ACCOUNT_ID`) und „Deploy-Zugang prüfen" auf `main` starten.
   Anschließend „Cloudflare-Worker deployen" für `newsletter-worker` von
   `main` ausführen und die verlangte Freigabe erteilen. `/healthz` muss
   `bau: ff-newsletter-2026-10-24` ausweisen; bei abweichendem Zustand dem
   Runbook folgen, nicht Secrets oder Schutzfunktionen auf Verdacht ändern.
4. **Edge-Regel anwenden:** `npm run edge:freigabe` (Exit 0), nach Prüfung
   des Ist-Zustands `npm run edge:freigabe:apply`, danach `npm run edge:b7`
   bzw. `npm run edge:b7:apply` und den geänderten Datenschutztext prüfen und
   committen. Bei Teilfehlern erneut messen statt blind zu wiederholen.
5. **Live-Nachweis:** `gh workflow run sicherheits-wache.yml --ref main`.
   Nur ein **vollständiger erfolgreicher Live-Job** mit beiden Messungen
   schließt #972 — nicht diese Akte, nicht ein grüner PR-Lauf und nicht ein
   grüner Offline-Test. Details und Rechte:
   `docs/SICHERHEIT-BETRIEB-RUNBOOK.md` (A1, A1b, A3/A4, D2, F5).

Keine Zugangsdaten in Issues, Logs oder Chat veröffentlichen.

---

## 6. Grenzen und Abgrenzung

- **Kein Live-Eingriff.** Kein Header gesetzt, keine Cloudflare-Regel
  angewandt, kein Worker deployt, kein Environment beschrieben, kein Secret
  gelesen oder geschrieben, kein Bypass-Schalter angefasst. Ein „grüner"
  Behelf wäre eine Fälschung des Nachweises.
- **#972 wurde nicht geschlossen und nicht kommentiert.** Der Abschluss
  gehört dem Workflow (D2); die automatische Meldung wurde heute um 14:27 UTC
  mit dem jüngsten Lauf nachgeführt und bleibt offen.
- **Kein Gate gelockert.** Fail-closed-Verträge, Auto-Close, die Trennung von
  BEFUND/STOERUNG/TEILWEISE, die Signatur-Regeln und die Proxy-Diagnose
  selbst sind unverändert. Geändert wurde nur, **was von einer Messung
  sichtbar wird** – und dass ein Verlust benannt statt verschwiegen wird.
- **Der Abschluss braucht einen Menschen.** Jeder Deploy nach Schritt 2 hält
  an der Freigabe; genau das ist die gewollte Wirkung des Schutzes.
- **Nicht in diesem Auftrag:** Der heutige rote Lauf
  `42032756148` („Release-Scorecard") und die roten PR-Prüfungen des
  GSC-Tageslaufs wurden zur Kenntnis genommen, aber bewusst nicht angefasst.
  Sie haben eigene Zustandskanäle; ein Eingriff hier hätte den
  Betriebspflege-Vorgang verwässert.
- **Reichweite der Heilung:** Sie betrifft die *Lesbarkeit* des täglichen
  Alarms und die zweite Fundstelle im Layout-Audit. Andere Melder, die
  künftig mehr als zehn Zeilen senden, müssen `annotationsplan()` nutzen;
  die Konstante und die Vertragstests machen das auffindbar, erzwingen es
  aber nicht für beliebigen neuen Code. Diese Grenze ist benannt statt durch
  eine globale, schwer prüfbare Drosselung aller Ausgaben überdeckt.
