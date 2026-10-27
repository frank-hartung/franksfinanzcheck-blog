# Wartung · Betriebspflege · Vorgang WF-E813 (#815) — Highend-Dauerheilung, Stufe 4 (27.10.2026)

**Auftrag:** `Wartung · Betriebspflege · Vorgang WF-E813 #815 Bitte dauerhaft auf Highend-Level einer Profi-Agentur beheben.`
**Datum:** 27.10.2026 · **Branch:** `arena/8d94fcc1-franksfinanzcheck-blog` · **Basis:** `9b4a771` (`main`, nach Merge #915)
**Vorgänger:** `WARTUNG-BETRIEBSPFLEGE-WF-E813-815-HIGHEND-2026-10-24.md` (PR #852, Stufe 1) · PR #862 (25.10., Stufe 2: Bindungs-Resolver + Live-Abschluss-Härtung) · `WARTUNG-BETRIEBSPFLEGE-WF-E813-815-HIGHEND-2026-10-26.md` (Stufe 3: Lagebild-Nachführung, stille Kanäle)

---

## 1. Forensischer Ist-Befund

### 1.1 Der Vorgang selbst: unverändert offen — und das ist ehrlich

Der jüngste gemessene Lauf ist `40499567144` (Sicherheits-Wache, 27.10.2026, Event `schedule`).
Job **„Quellseite“** grün (11 s), Job **„Abhängigkeiten“** grün (1 min 7 s), Job
**„Live-Messung“** rot nach 9 s:

- **F-01 BEFUND (10 Annotationen):** Auf `https://franksfinanzcheck.de/` und `/methodik/` fehlen
  live alle fünf Pflicht-Kopfzeilen (CSP, Referrer-Policy, X-Frame-Options,
  X-Content-Type-Options, HSTS). Die Wache klassifiziert korrekt „gemessen, und etwas fehlt“ —
  nicht „nicht messbar“.
- **Worker STOERUNG (3 Annotationen):** `bau` fehlt in `/healthz`, das authentifizierte
  Betriebsbild ist unvollständig (`budget`, `turnstile`, `schluesselrollen`, `exporte`). Das ist
  der belegte Beweis, dass der Worker-Deploy `ff-newsletter-2026-10-24` **nie** live ging.
- **Live-Nachweis:** `header: BEFUND, worker: STOERUNG – kein vollständiger Live-Nachweis.`

Beides sind **Inhaber-Aufgaben** (Runbook A1 und D2): Ohne Cloudflare-Zonen-Token bzw. ohne
`CF_WORKERS_DEPLOY_TOKEN` im Environment `cloudflare-produktion` ist in dieser Umgebung keine
wirkende Änderung möglich — produktive Zugänge existieren hier nicht, und ein „grüner“ Behelf
wäre eine Fälschung des Nachweises. **Der Vorgang bleibt deshalb offen.** Diese Stufe behauptet
kein Grün; sie beseitigt zwei Betriebsfehler, die das Grün verhindern würden, wenn die
Einrichtung steht.

### 1.2 Neubefund A — ein grüner Job mit drei roten Annotationen

Beim Nachmessen fiel am Job **„Abhängigkeiten (Pins offline · Audit online)“** etwas auf, das
nicht im Meldungstext stand: Der Job war **`success`** — und trug trotzdem **drei
`failure`-Annotationen** (Checks-API von Lauf `40499567144`):

```
pyyaml ist als Bereich genannt (Untergrenze 6.0) …   abhaengigkeiten.yml: requirements-x.txt#1
Kein GITHUB_TOKEN/GH_TOKEN gesetzt – …               .github#53
x@1.0.0 (npm, high) – Fix: kein Fix veröffentlicht – Test   .github#52
```

Es gibt weder eine `requirements-x.txt` noch ein Paket `x@1.0.0` im Repository. Die Zeilen waren
die **Ausgabe der Vertragstests**: `test_abhaengigkeits_wache.py` ruft `wache.main(["--check", …])`
auf einem absichtlich vergifteten Testbaum auf, und `main()` druckte seine Befunde als
GitHub-Workflow-Kommando. Der Runner parst jede Zeile, die mit `::` beginnt — aus
Testausgaben wurden Betriebsannotationen.

**Warum das zu WF-E813 gehört und nicht Kosmetik ist:** Die gesamte Kette aus A1, D1 und D2 lebt
davon, dass ein rotes Kreuz etwas bedeutet. Ein grüner Job, der wie ein roter aussieht, trainiert
genau die Betriebsblindheit, die den stillen Worker-Deploy (#829B) und das stille CodeQL-Gate
(26.10.2026) erst möglich gemacht hat. Gemessen am Bestand: **13 Workflow-Kommandos** in einem
einzigen Testlauf der Python-Suite, davon **3** im Job der Sicherheits-Wache.

### 1.3 Neubefund B — Wachen, die bei einer Änderung nicht anspringen

Die Dauerheilung von WF-E813 besteht aus Wachen (Header, Worker, Abhängigkeiten, Edge-Freigabe,
Deploy-Vorbereitung). Ob eine Wache läuft, entscheidet allein der handgepflegte
`paths`-Filter ihres Workflows — und zwar zweimal (`push` und `pull_request`). Eine erste
Messung mit der neuen Trigger-Wache ergab **36 Befunde in neun Workflows**:

| Workflow | W1 (Aufruf ohne Trigger) | W3 (Filter unsymmetrisch) |
|---|---|---|
| `lesehilfen-gate.yml` | 6 | 14 |
| `robustheit.yml` | 4 | – |
| `design-varianten.yml` | 3 | – |
| `backup-frischwache.yml` | 2 | – |
| `brand-surface-guard.yml` | 2 | – |
| `themenwelten-gate.yml` | 2 | – |
| `e2e.yml` | 1 | – |
| `sicherheits-wache.yml` | – | 1 |
| `worker-deploy.yml` | 1 | – |
| **Summe** | **21** | **15** |

Betroffene Prüfer (elf Dateien): `manifest_guard.py` (in fünf Gates benutzt, in vier Filtern
nicht genannt), `alert_issue_identity.py`, `audio_coverage_check.py`, `ff_voice_parity_check.py`,
`ff_voice_toolbar_check.py`, `selftest_clock.py`, `backup_einrichtung.py`, `kv_backup.py`,
`tabellen_lesbarkeit_guard.py`, `agent_reach_gate.py`, `tests/test_design_varianten.py`.
Dazu im Lesehilfen-Gate zwei völlig unterschiedliche Fassungen derselben Absicht (sechs
Einzeldateien unter `layouts/…` bei `push`, ein `layouts/**` bei `pull_request`) — eine Änderung
an der Einbindung der Lesehilfen prüfte je nach Weg etwas anderes.

Keine dieser Lücken war „kaputt“. Alle waren unsichtbar — dieselbe Bauweise wie 1.2 und wie die
stillen Kanäle der Stufe 3.

---

## 2. Dauerhafte technische Heilung

### H-A — Ein Meldeweg für Workflow-Kommandos: `scripts/github_kommando.py`

**Zwei Fehler, eine Ursache.** `::error file=…,line=…,title=…::Text` ist kein Log-Text, sondern
eine Schnittstelle zum Runner. Wird sie an mehreren Stellen von Hand gebaut, entstehen zwei
Fehlerklassen, und beide waren im Bestand:

1. **Falsche Kommandos.** Jeder Aufruf aus einem Testlauf färbte den Lauf, in dem der Test lief.
2. **Erzeugbare Kommandos.** `_annotation()` in `abhaengigkeits_wache.py` setzte Dateinamen und
   Text unmaskiert ein. Ein Zeilenumbruch (Dateiname aus dem Baum, Requirement-Zeile aus einer
   Datei) beginnt ein **zweites** Kommando; ein `,` bricht aus der Eigenschaftsliste aus
   (`file=a,line=999,title=…`). Die Werte stammen aus Inhalten, die ein Pull Request
   beeinflussen kann.

Der neue Melder ist die einzige Stelle, an der Kommandos entstehen:

- **Kodierung nach GitHub-Vorschrift:** `%`, CR, LF in der Nutzlast; zusätzlich `:` und `,` in
  den Eigenschaften (`file=`, `title=`). Ein Befund bleibt damit **eine** Zeile und **eine**
  Eigenschaftsliste.
- **Teststille:** Unter `unittest`/`pytest` wird nie gesendet — auch mitten in Actions. Ein Test
  prüft Verhalten; er gestaltet nicht den Lauf, in dem er läuft.
- **Notausgang in beide Richtungen:** `GITHUB_KOMMANDOS=an` erzwingt das Senden (Gegenprobe),
  `GITHUB_KOMMANDOS=aus` erzwingt die Stille. Beides schlägt jede Automatik.
- **Lokal lesbar statt stumm:** ohne Runner erscheint dieselbe Information als Klartextzeile
  (`[error] Wache A1: requirements-x.txt:1: …`) — ein lokaler Lauf ist nicht schlechter lesbar
  als ein CI-Lauf.
- **Selbstdiagnose:** `npm run kommando:probe` zeigt, ob der aktuelle Prozess senden würde, und
  ein kodiertes Beispiel — ohne selbst ein Kommando zu senden.

Umgestellt: `abhaengigkeits_wache.py` (Befunde, Audit-Störung, Schwachstellen-Treffer),
`werkzeugbefund.py` (Befund + Notfallmeldung), `watchdog_recovery.py` (17 Meldestellen),
`sicherheits_nachweis.py` (Annotationen der Live-Auswertung, Schnittstelle unverändert).

**Messbare Wirkung:** Der vollständige Python-Testlauf erzeugte vorher **13** Workflow-Kommandos,
jetzt **0**. Die Sicherheits-Wache zeigt auf einem grünen Job keine roten Annotationen mehr.

### H-B — Eine Wache für die Wachen: `scripts/trigger_wache.py`

Die neue Trigger-Wache hält drei Zusagen (W1 Referenz, W2 Waise, W3 Symmetrie) und ist bewusst
abhängigkeitsfrei: Sie läuft im Skript-Syntax-Lauf, der keine Pakete installiert. Dass ihr
Ausschnitt-Parser nicht anders liest als ein vollständiger YAML-Parser, beweist ein Test gegen
PyYAML — **für jeden der 93 Workflows**, nicht nur für ein Beispiel (Ereignismenge, `paths`,
`paths-ignore`).

Eigener Befund beim Bau (in der Wache dokumentiert): Die erste Fassung nutzte `fnmatch`, und
dort trifft `*` **auch** den Schrägstrich. Damit hätte `scripts/*.py` den Pfad
`scripts/tests/foo.py` „gedeckt“ — die Wache wäre selbst die stille Wache gewesen, gegen die sie
antritt. `gedeckt()` übersetzt jetzt GitHubs Glob-Regeln (`*` = eine Ebene, `**` = über Ebenen,
`**/` = null oder mehr Verzeichnisse).

**Geheilt wurden alle 36 Befunde**, jeweils in beiden Listen:

- `backup-frischwache.yml`: `backup_einrichtung.py`, `kv_backup.py`
- `brand-surface-guard.yml`: `alert_issue_identity.py` (die Markenfläche liest die Vorgangs-Identität)
- `design-varianten.yml`: `agent_reach_gate.py`, `manifest_guard.py`, `tests/test_design_varianten.py`
- `e2e.yml`: `tabellen_lesbarkeit_guard.py`
- `lesehilfen-gate.yml`: **beide Listen vereinheitlicht** (ein `layouts/**` statt sechs
  Einzeldateien; `audio_coverage_check.py`, `manifest_guard.py`, `ff_voice_parity_check.py`,
  `ff_voice_toolbar_check.py` ergänzt)
- `robustheit.yml`: `manifest_guard.py`, `selftest_clock.py`
- `sicherheits-wache.yml`: `n8n_bridge.py` (Symmetrie), **neu** `github_kommando.py` und
  `tests/test_github_kommando.py` — der Kanal, der WF-E813 führt, prüft seinen eigenen Melder
- `themenwelten-gate.yml`: `manifest_guard.py`
- `worker-deploy.yml`: `manifest_guard.py` (läuft dort vor jedem `npm ci`)

Die Wache selbst läuft im Workflow **Skript-Syntax** (`--selftest` **vor** `--check`, wie es die
Hausregel verlangt), und dessen Trigger nennt jetzt `.github/workflows/**.yml`: Eine Änderung an
einem Trigger löst damit den Lauf aus, der Trigger prüft.

### H-C — Die neue Wache darf kein stiller Kanal sein

Gegenprobe an der eigenen Arbeit: Die Trigger-Wache läuft im Workflow **Skript-Syntax
(liegender Stand)** — und genau dieser Workflow stand **nicht** auf der Wacht-Liste des
zentralen Fehler-Alertings. Eine dort gefundene Regression wäre also still geblieben, also
exakt die Klasse, die diese Stufe behebt. Deshalb:

- **Wacht-Liste:** `Skript-Syntax (liegender Stand)` ist jetzt beobachtet (**63 → 64**
  Einträge, Duplikate = 0). Der Lauf ist der einzige Ort, an dem der liegende Stand
  kompiliert **und** die Trigger-Vollständigkeit geprüft wird — er verdient eine Stimme.
- **Identität:** `WF-CA1D · Betriebspflege · Skript-Syntax (liegender Stand)`, deterministisch
  abgeleitet (`alert_issue_identity.py --selftest`: 64 Workflows, 64 eindeutige Codes, Titel
  markenfrei). Der Bereich lautet „Betriebspflege" statt „Technik", weil der Lauf die
  Betriebspflege des Repos prüft.
- **Eigene Triage-Klasse `skript-syntax`:** Der Rat nennt die konkreten Befehle
  (`skript_syntax_wache.py --check`, `npm run trigger:check`, `skript_syntax_heiler.py --fix
  --commit`), die Pfad-Ergänzung in **beiden** Listen und die Grenze der Prüfung (Runbook F2) —
  kein „API-Key abgelaufen", kein Neustart. Klassenvertrag unangetastet: jede Klasse genau ein
  Rat, Rückfallklasse bleibt `allgemein`.
- **Verhalten belegt:** drei neue Szenarien der Simulation (Syntaxfehler, Trigger-Befund,
  Gegenprobe „Rat gilt nur für den eigenen Kanal") — **61 Szenarien grün** (vorher 58).

---

## 3. Verifikation (lokale Prüfungen vom 27.10.2026)

| Prüfung | Ergebnis |
|---|---|
| `python3 scripts/trigger_wache.py --selftest` | ✅ Parser, W1, W2, W3, Fließform-Sperre |
| `npm run trigger:check` | ✅ **93 Workflows, 0 Befunde** (vorher 36 in neun Workflows) |
| `npm run test:trigger` | ✅ **17 Tests** (ohne PyYAML 1 übersprungen), inkl. **PyYAML-Gegenprobe über alle 93 Workflows** und Dauervertrag „Bestand ohne Befund“ |
| `npm run test:kommando` | ✅ **22 Tests**: Fluchtschutz (Umbruch, `%`, `,`/`:` in Eigenschaften), Teststille, Notausgang, Selbstdiagnose |
| Vollständiger Python-Testlauf (`unittest discover -s scripts/tests`, mit `requirements-ci`) | ✅ **OK (28 übersprungen)** – und **0 Workflow-Kommandos** (vorher 13) |
| `npm run test:sicherheit` | ✅ Exit 0 (Header-, Inhalts-, Worker-, n8n-, Abhängigkeits-Wache + 33 Vertragstests), **0 Kommandos** |
| `python3 scripts/wachen_vertrag.py --json` | ✅ 343 Skripte, 0 Funde (keine halben Fassungen) |
| `python3 scripts/skript_syntax_wache.py --check` | ✅ 555 Dateien kompilieren |
| YAML aller 93 Workflows | ✅ mit PyYAML 6.0.3 geparst (`jobs` vorhanden, keine Strukturbrüche) |
| `scripts/trigger_wache.py` vs. PyYAML | ✅ **0 Abweichungen** in Ereignismengen, `paths` und `paths-ignore` über den gesamten Bestand |
| `python3 scripts/alert_issue_identity.py --selftest` | ✅ 10 Fallgruppen, **64 Workflows, 64 eindeutige Codes** |
| `test_alert_scoping` / `test_alerting_heartbeat` / `test_alert_router` (+ `test_alert_resolve_gate`, 19) | ✅ **72 + 16 + 29 Tests grün**, Verhaltens-Simulation **61 Szenarien** (drei neu: Syntax-, Trigger-Befund, Kanal-Gegenprobe) |
| `alert-on-failure.yml` (PyYAML 6.0.3) | ✅ 64 Wacht-Einträge, keine Duplikate, neue Klasse im Klassenvertrag |

---

## 4. Bewusste Grenzen (Ehrlichkeits- und Sicherheits-Doktrin)

- **Kein künstliches Grün, kein manuelles Schließen von #815.** F-01 (Cloudflare-Proxy + Regel)
  und der Worker-Deploy (Environment-Zugänge) bleiben Inhaber-Aufgaben nach Runbook A1/D2. In
  dieser Umgebung existieren keine produktiven Cloudflare-Zugänge; ein Eingriff auf Verdacht wäre
  gegen die Doktrin des Runbooks („bei STOERUNG nichts an Cloudflare auf Verdacht ändern“).
- **Kein Umbau aller 38 Melder.** Umgestellt sind die Stellen, die im Testlauf tatsächlich
  Kommandos erzeugten — belegt durch die Messung (13 → 0), nicht durch Vermutung. Weitere
  Skripte geben `::`-Zeilen aus, ihre Tests fangen die Ausgabe aber ab; sie brechen nichts und
  werden erst umgestellt, wenn ein Melder sie braucht.
- **Die Trigger-Wache urteilt nicht über Sinn.** Sie sagt „was der Lauf anfasst, löst ihn aus“,
  nicht „dieses Gate prüft das Richtige“. Ob ein Rat zutrifft, entscheidet weiter die
  Klassifikation der Wache selbst. Die Filter wurden **erweitert**, nie verengt; das Lesehilfen-
  Gate prüft damit auf dem Push-Weg mehr Dateien als vorher.
- **Was „grün“ hier heißt.** Der vollständige Testlauf wurde mit den Pins aus
  `requirements-ci` gefahren (wie in CI) und ist grün. Ohne PyYAML – in einer nackten
  Python-Installation nicht vorhanden – brechen die Suiten ab, die Workflows oder Register
  lesen; diese Zahl sagt etwas über die Umgebung, nicht über den Code. Beides wird hier
  getrennt genannt, statt die Umgebung als Befund zu verkaufen.
- **Kein Umbau fremder Testbühnen.** Die Bühne in `test_blustradius_register` fährt echte
  `run`-Blöcke aus `deploy.yml` mit Attrappen. Sie trägt jetzt dieselben Dateien wie das
  Repository (`github_kommando.py`) und sagt ausdrücklich `GITHUB_KOMMANDOS=aus`: Eine
  Simulation darf nicht den Lauf einfärben, in dem sie läuft.

---

## 5. Inhaber-Checkliste (unverändert gültig — erst sie schließt #815)

1. **Cloudflare Edge A1 + Datenschutz B7 (F-01):**
   ```bash
   CLOUDFLARE_API_TOKEN="<Zonen-Token mit DNS:Edit, Settings:Edit, Transform Rules:Edit>" \
     npm run edge:freigabe:apply
   npm run edge:b7
   git add content/datenschutz/index.md && git commit -m "docs(datenschutz): Cloudflare-Proxy B7 nach Freigabe aktiviert" && git push origin main
   ```
2. **Worker-Zugänge (D2):** Environment `cloudflare-produktion` um `CF_WORKERS_DEPLOY_TOKEN`
   (Workers Scripts: Read + Deploy) und `CLOUDFLARE_ACCOUNT_ID` ergänzen;
   `NEWSLETTER_WORKER_EXPORT_KEY`/`NEWSLETTER_WORKER_WRITE_KEY` mit den Worker-Secrets abgleichen.
3. **Deploy ausführen:** `gh workflow run worker-deploy.yml --ref main -f worker=newsletter-worker`.
   Nachweis: `/healthz` liefert `bau == ff-newsletter-2026-10-24`.
4. **Live-Abnahme:** `gh workflow run sicherheits-wache.yml --ref main` — nur ein vollständiger
   grüner Live-Nachweis (F-01 OK, Worker-Bild vollständig, kein B7-Blocker) schließt #815
   automatisch über `alert_resolve_gate.py`.

**Nach dieser Stufe gilt zusätzlich:** Sobald die Einrichtung steht, kann kein falsches
Annotation-Kommando und kein nicht ausgelöster Filter mehr dazwischenfunken. Sollte dennoch
etwas rot bleiben, nennt der Lauf den Schritt und die Klasse — nicht ein Artefakt aus einem
Testbaum.
