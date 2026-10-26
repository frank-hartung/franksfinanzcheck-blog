# Wartung · Betriebspflege · Vorgang WF-E813 (#815) — Highend-Dauerheilung, Stufe 3 (26.10.2026)

**Auftrag:** `Wartung · Betriebspflege · Vorgang WF-E813 #815 Bitte dauerhaft auf Highend-Level einer Profi-Agentur beheben.`
**Datum:** 26.10.2026 · **Branch:** `arena/1036cd51-franksfinanzcheck-blog` · **Basis:** `64da797` (`main`, nach Merge #905/#908)
**Vorgänger:** `WARTUNG-BETRIEBSPFLEGE-WF-E813-815-HIGHEND-2026-10-24.md` (PR #852, Stufe 1) · PR #862 (25.10., Stufe 2: Bindungs-Resolver + Live-Abschluss-Härtung)

---

## 1. Forensischer Ist-Befund (belegt an den Live-Läufen bis 26.10.2026, 19:30 UTC)

Die Stufen 1 und 2 haben die Werkzeug- und Beweiskette Code-seitig dauerhaft geheilt (Schema-Vertrag
`"wartet"`, Build-Stempel-Diagnose, SSL-Downgrade-Sperre, Bindungs-Resolver, Fail-closed-Deploys,
Job-Beweis beim Auto-Close). Der frische End-to-End-Audit-Lauf dieses Tages zeigt: **der Code ist
gesund (196 Sicherheits-Unit-Tests, 9 Selbsttests, 93 Worker-Tests lokal grün)** — aber drei
Betriebslücken halten den Vorgang offen bzw. waren neu entstanden:

### 1.1 Warum #815 weiterhin offen ist (Run `40323874320`, 26.10.2026, 12:36 UTC, `schedule`)

1. **Säule 1 — `F-01 BEFUND` (10 Einzel-Annotationen):** Auf `https://franksfinanzcheck.de/` und
   `/methodik/` fehlen live weiterhin alle fünf Pflicht-Kopfzeilen, weil die Cloudflare-Zone noch
   nicht auf `Proxied` + Transform-Regel `FF Sicherheits-Header` gestellt ist (**Inhaber-Aufgabe,
   Runbook A1** — ohne Zonen-Zugang aus der Sandbox unbelegbar).
2. **Säule 2 — `Worker STOERUNG` (3 Einzel-Annotationen):** Die Diagnose der Stufe 1 arbeitet
   exakt: `bau` fehlt in `/healthz` → live antwortet noch der Worker-Stand **vor**
   `ff-newsletter-2026-10-24`; das authentifizierte Betriebsbild ist unvollständig
   (budget, turnstile, schluesselrollen, exporte fehlen). Das ist der **bewiesene Beweis, dass der
   Worker-Deploy nie lief** — kein Ratebefund mehr (**Inhaber-Aufgabe, Runbook D2**).

### 1.2 Neubefund A — „Cloudflare-Worker deployen“ stand seit 25.10. still rot

Der Deploy-Workflow (der HEILUNGSschritt von Säule 2!) ist seit 25.10.2026, 13:20 UTC (Run
`40197128082`, PR #862-Push) und erneut am 26.10.2026, 10:32 UTC (Run `40308260271`,
Dependency-Bump) **rot — ohne eine einzige Meldung**:

- Der Workflow war **nicht in der Wacht-Liste** des zentralen Fehler-Alertings und hatte **keine
  Identität** in `alert_issue_identity.py`.
- Die Rots sind korrektes **Fail-closed**: `„CF_WORKERS_DEPLOY_TOKEN fehlt im Environment
  cloudflare-produktion; die bestehende Worker-Bindung kann nicht gelesen werden.“` Genau dieser
  Zugang fehlt also dem Inhaber-Betrieb — und niemand wurde darauf hingewiesen.
- Handlungsrelevanz: Die Sicherheits-Wache rät in #815 zurecht, den Deploy zu starten — aber der
  Deploy scheitert an fehlenden Zugängen, und genau das blieb stumm.

### 1.3 Neubefund B — CodeQL-Sicherheitswache war still rot (echte Fundstellen, inzwischen geheilt)

- Run `40377542122` (26.10.2026, 18:25 UTC, Push des Merges #905): **Sicherheits-Gate rot** mit
  **2 echten Fundstellen** in der neuen `e2e/a11y-axe.spec.mjs`:
  `js/incomplete-sanitization` (Zeile 238: `datum.replace(/\./g, '\\.')` entwertete Backslashes —
  ein Titel mit `\` konnte das Muster verbiegen) und `js/regex/missing-regexp-anchor`
  (Zeile 285: `/^https?:\/\/|\.md$/` — Anker galten nur für ihren Alternations-Zweig,
  „misleading operator precedence“; jeder `.md`-String passierte ungeprüft).
- **Belegt stumm:** CodeQL war ebenfalls nicht in der Wacht-Liste — kein Issue, kein Signal.
- **Heilungsnachweis:** PR #908 (`ba8dfc95`, 18:33 UTC, „fix(ci): Manifest-Wache und CodeQL nach
  PR #905“) hat beide Fundstellen im Code geheilt (`textMuster()` baut jetzt metazeichenfreie
  Muster, der Beleg-Test nutzt zwei vollständig verankerte Einzelmuster). Der Push-Lauf um 18:54
  UTC ist **grün** — die Heilung ist damit am echten Scanner belegt. Dieser Bericht ändert an
  diesen Dateien bewusst **nichts** (kein zweiter Eingriff in grünen Code), verdrahtet aber die
  Alarmierung, damit das nächste Mal ein Signal statt eines Zufalls entsteht.

### 1.4 Neubefund C — Lagebild-Verfall: #815 zeigte tagelang den falschen Lauf

Das zentrale Alerting **lief** beim roten Lauf von 12:36 korrekt (Alarm-Job 12:37:31 UTC,
`success`), entschied aber nach der #761-Doktrin „gleiche Klasse → keine Umschrift" und fasste
#815 nicht an. Folge:

- Der Body zeigte **Run `39945360551` vom 23.10.**, obwohl Run `40323874320` vom 26.10. der
  jüngste rote Lauf war.
- Der Fußsatz `„Mit dem jüngsten Lauf nachgeführt – Rat und Lauf oben sind aktuell.“` war zur
  **Unwahrheit** geworden.
- Verdeckt aber real: Auch der maschinenlesbare `<!-- alert-jobs: [...] -->`-Marker (die
  Grundlage des Auflösungs-Beweises, #809) alterte mit jedem gleichklassigen Lauf.

---

## 2. Dauerhafte technische Heilung (Stufe 3, dieser Tag)

### H-A — Lagebild-Nachführung Stufe 2 (`.github/workflows/alert-on-failure.yml`)

- **Gleicher Rat, neuer Lauf → Body wird erneuert:** Trägt eine offene Meldung bereits die
  Runbook-Klasse des aktuellen Laufs, bleibt der **Rat** stehen — aber **Zeit, Run-Link, rote
  Schritte und der `alert-jobs`-Marker** werden mit dem jüngsten roten Lauf neu geschrieben.
- **Reihen-/Doppelt-Schutz:** Die Umschrift geschieht nur, wenn der im Body aufgezeichnete Lauf
  (`(?:actions/)?runs/(\d+)`) **älter** als der aktuelle ist. Verspätete Zustellungen oder Re-Runs
  älterer Läufe überschreiben ein jüngeres Lagebild nicht.
- **Unverändert sicher:** Ohne Job-Lage (`!jobsKnown`) wird nie umgeschrieben; das Nachführen
  bleibt fail-open (API-Fehler → Meldung bleibt offen, kein Absturz, kein Duplikat); Body-Edits
  benachrichtigen niemanden.
- Damit ist der Fußsatz „Mit dem jüngsten Lauf nachgeführt“ wieder eine **einlösbare Zusage** —
  für alle Kanäle, nicht nur die Sicherheits-Wache.

### H-B — Zwei stille Produktionskanäle bekommen Stimme und Identität

1. **Wacht-Liste erweitert:** `Cloudflare-Worker deployen` und `CodeQL-Sicherheitswache` sind
   jetzt beobachtet (63 Einträge, dedupe-fest, `alerting_heartbeat`-Vertrag unangetastet).
2. **Identität** (`alert_issue_identity.py`, deterministisch): `WF-829B · Veröffentlichung ·
   Cloudflare-Worker deployen` und `WF-D6D2 · Betriebspflege · CodeQL-Sicherheitswache` —
   Selbsttest: 63 Workflows, 63 eindeutige Codes, Titel markenfrei.
3. **Eigene Triage-Klassen statt Schlüssel-Raten:**
   - `worker-deploy-zugang` (Schritt „Produktive Ressource auflösen“ rot): Fail-closed-Einordnung,
     Environment `cloudflare-produktion` (`CF_WORKERS_DEPLOY_TOKEN`, `CLOUDFLARE_ACCOUNT_ID`),
     Verbot der manuellen ID-Kopiererei, „grüner Plan ist kein Deploy“.
   - `worker-deploy` (übrige Deploy-Rots): Log zuerst, „grüner Plan ist kein Deploy“,
     `bau`-Stempel-Nachweis, STOERUNG = kein Eingriff auf Verdacht.
   - Rote `Worker-Tests` teilen bewusst die bestehende Klasse `selbsttest` (Code-Regression,
     kein Betriebsausfall) — Erkennung über `selbsttestFailed || workerTestsFailed`, damit jeder
     Klassenname genau einen Rat behält (Strukturvertrag „keine Doppelklassen“ bleibt grün).
   - `codeql-fund` (Sicherheits-Gate rot): Fundstelle im Code heilen statt wegdrücken, mit
     Verweis auf die Heildoktrin `CODE-SCANNING-HEILUNG-PREMIUM-2026-10-04.md`.
   - `codeql` (Analyse-/Upload-Störung): Infrastruktur-Einordnung, Statusseite, Neustart —
     ausdrücklich **kein** Code-Befund.
4. **Auflösungsseite symmetrisch:** Beide Kanäle schließen über den bestehenden Marker-/Job-Beweis
  -Pfad automatisch mit ihrem ersten grünen `main`-Lauf; keine Sonderlogik nötig.

### H-C — Verifikation der fremden Heilung (PR #908) dokumentiert

Die beiden CodeQL-Fundstellen sind im Bestand durch #908 geheilt und am Scanner gegenbewiesen
(18:54-Run grün). Dieser Branch lässt `e2e/a11y-axe.spec.mjs` unangetastet — Ehrlichkeits-Doktrin:
keine Kosmetik in bereits grünem Code, aber ein Signal-Kanal für die Wiederholung.

---

## 3. Verifikation (lokale Prüfungen vom 26.10.2026)

| Prüfung | Ergebnis |
|---|---|
| Verhaltens-Simulation `alert_scoping_sim.mjs` | ✅ **57 Szenarien grün**, darunter 6 neue: Lagebild-Erneuerung bei gleichem Rat + älterem Lauf, Reihenfolgeschutz (älteres Ereignis überschreibt nicht), Idempotenz bei gleichem Lauf, Worker-Deploy (Zugang / Tests / Deploy), CodeQL (Gate / Analyse-Störung), Nachführung des neuen Zugang-Rats |
| `python3 -m unittest scripts.tests.test_alert_scoping` (mit PyYAML 6.0.3) | ✅ **26/26 Tests**, inkl. Klassen-Eindeutigkeit, Rat-Wahl-Vollständigkeit, Dedupe-Reihenfolge (Job-Lage → gleiche Klasse → nachführen), Wacht-Listen-Vertrag, YAML-1.1-Falle |
| `python3 scripts/alert_issue_identity.py --selftest` | ✅ **10 Fallgruppen, 63 Workflows, 63 eindeutige Codes**, Titel markenfrei |
| `python3 scripts/alert_resolve_gate.py --selftest` + `test_alert_resolve_gate` | ✅ 11 Fälle + Suite grün (Auto-Close-Vertrag unverletzt) |
| `python3 scripts/alerting_heartbeat.py --selftest`, `test_alert_router`, `test_alerting_heartbeat` | ✅ grün (Herzschlag-SSOT und Router unverletzt) |
| `npm run test:sicherheit` | ✅ 9 Selbsttests + 196 Sicherheits-Unit-Tests + 33 Abhängigkeits-Tests + 4 Offline-Wachen, **Exit 0** |
| `cd newsletter-worker && node --test` | ✅ **93/93** (Build-Stempel-Vertrag unverändert) |
| Workflow-YAML | ✅ `alert-on-failure.yml` mit PyYAML 6.0.3 geparst: 63 Wacheinträge, keine Duplikate, beide neuen Kanäle verdrahtet |
| `node --check e2e/a11y-axe.spec.mjs` | ✅ Syntax OK (Stand #908, CodeQL-gegenbewiesen grün) |

---

## 4. Bewusste Grenzen (Ehrlichkeits- & Sicherheits-Doktrin)

- **Kein künstliches Grün, kein manuelles Schließen von #815:** F-01 (Cloudflare-Proxy/Regel) und
  der Worker-Deploy (Environment-Zugänge) sind **Inhaber-Aufgaben** (Runbook A1/D2). In der
  Sandbox existieren weder produktive Cloudflare-Tokens noch Environment-Secrets. Der Auto-Close
  (`sicherheits_nachweis.py --abschluss` + `alert_resolve_gate.py`) schließt #815 beim ersten
  vollständigen grünen Live-Lauf vollautomatisch; ein grüner Offline-/Push-Lauf genügt weiterhin
  nicht — und wird jetzt zusätzlich nicht mehr als „jüngster Lauf“ angezeigt, weil das Lagebild
  sich selbst nachführt.
- **Die Rots von „Cloudflare-Worker deployen“ bleiben solange ehrlich rot,** bis die Zugänge im
  Environment `cloudflare-produktion` hinterlegt sind. Ab dem Merge dieser Stufe erzeugt der erste
  weitere Fail-closed-Abbruch eine Meldung (WF-829B) mit dem exakten Einrichtungsweg statt
  Funkstille — und schließt sich nach dem echten Deploy selbst.
- **Keine weiteren Wacht-Listen-Erweiterungen ohne eigenen Rat:** Weitere unüberwachte Workflows
  (z. B. GSC-Tageslauf, Release-Scorecard, Suchradar) sind derzeit grün. Jede Aufnahme verdient
  eine eigene, zutreffende Triage — ein generischer „API-Key abgelaufen“-Rat wäre genau die
  Fehlklasse, die dieses Alerting seit #632/#654/#780/#809 abgebaut hat. Empfehlung für eine
 Folgesession: Vollabdeckungs-Audit Kanal für Kanal mit eigenem Runbook.

---

## 5. Inhaber-Checkliste (echter Live-Abschluss von #815 — unverändert gültig, jetzt bewiesensicher)

1. **Cloudflare Edge A1 + Datenschutz B7 (F-01):**
   ```bash
   CLOUDFLARE_API_TOKEN="<Zonen-Token mit DNS:Edit, Settings:Edit, Transform Rules:Edit>" \
     npm run edge:freigabe:apply
   npm run edge:b7
   git add content/datenschutz/index.md && git commit -m "docs(datenschutz): Cloudflare-Proxy B7 nach Freigabe aktiviert" && git push origin main
   ```
   Apply-Reihenfolge: Read-Preflight → Header-Regel → SSL → DNS-Proxy → erneute Messung; ein
   bestehendes `Full (strict)` wird nie herabgestuft.
2. **Worker-Zugänge (D2):** Environment `cloudflare-produktion` um `CF_WORKERS_DEPLOY_TOKEN`
   (Workers Scripts: Read + Deploy) und `CLOUDFLARE_ACCOUNT_ID` ergänzen;
   `NEWSLETTER_WORKER_EXPORT_KEY`/`NEWSLETTER_WORKER_WRITE_KEY` mit den Worker-Secrets abgleichen.
   Keine IDs manuell kopieren — der Resolver liest die bestehenden Bindungen (`ABO`/KV,
   `DB`/D1) selbst.
3. **Deploy ausführen:** `gh workflow run worker-deploy.yml --ref main -f worker=newsletter-worker`
   (Environment-Freigabe erteilen). Der Lauf muss den Post-Deploy-Nachweis zeigen:
   `/healthz` liefert `bau == ff-newsletter-2026-10-24`. Bleibt der Deploy dennoch rot, meldet
   sich jetzt der Kanal WF-829B mit dem konkreten Einrichtungsweg.
4. **Live-Abnahme:** `gh workflow run sicherheits-wache.yml --ref main` — nur ein vollständiger
   grüner Live-Nachweis (F-01 OK, Worker-Bild vollständig OK, kein B7-Abschlussblocker) schließt
   #815 automatisch. Ab diesem Merge zeigt die Meldung außerdem garantiert den **jüngsten** roten
   Lauf, solange sie offen ist.
