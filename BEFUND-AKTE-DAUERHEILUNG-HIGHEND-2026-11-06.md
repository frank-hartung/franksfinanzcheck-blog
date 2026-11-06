# BEFUND-AKTE – Dauerheilung & automatische Selbstheilung 2026-11-06

**Stand:** 6. November 2026 (nachmittags) · **Vorgang** auf
`arena/09fe5639-franksfinanzcheck-blog` · **Bezug:** #912-Klasse (committed
Arbeitsliste ist der einzige Wahrheitsort der Redaktion für offene Fachbefunde),
#1039/#1103 (Bündel-Blindfleck, heute gemergt), #922, #1067

> Auftrag (wörtlich): „die committed BEFUND-AKTE auf main ist veraltet
> (Generator meldet 19 Befunde/8 überholt — Hinweis…). Bitte dauerhaft auf
> Highend-Level einer Profi-Agentur beheben mit automatischer
> Selbstheilung.“ Dazu die drei weiteren offenen Punkte des Vorgangs.

---

## 1. Ausgangslage – was an der Akte tatsächlich kaputt war

Die committed Arbeitsliste zeigte auf `main` **11 offene Befunde** (Stand
14:15, erzeugt beim „#1100 neu versiegeln“ in #1095). **Weniger als eine
Stunde später** editierten andere Läufe die beiden Preisgarantie-Gas-Artikel
(`f3521a127`, `9a7871cc1`, `61e061e79`-Klasse: euregate-/Redaktions-/GSC-Läufe);
Fassungs-Hashes kippten → **8 Befunde „überholt“, 2 Seiten neu offen**. Der
Tageslauf war durch, und sein Commit-Hake (`content/ data/ FAKTENFRISCHE-
REPORT.md`) greift nur auf seine eigene Pfadliste – externe Inhalts-Edits
erreichen den Akte-Commit **nie**. Ergebnis: committe Akte blieb stehen;
`test_akte_im_repo_ist_auf_dem_stand_der_queue` wurde auf **main rot** und
blieb es bis #1103 es bemerkte (Altlast in der Regression).

Live-Generator auf frischem `main`-Bestand (06.11.2026, heute):
**19 Befunde auf 6 Seiten, 5 live, 16 live-Befunde, 8 überholt, ältester
5 Tage.** #1103 hat den Standort einmalig korrigiert (Squash-Merge
`30e401576`) – die **Klasse** „Akte veraltet zwischen Inhalts-Edits“ bestand
damit weiterhin.

Daneben lagen drei offene Punkte offen (wortgleich aus dem Vorgang):
#1067 (Ersatz-PR, nach #1103 weiter offen), #922 (Cloudflare-Deploy,
fail-closed seit 27.10.), „#912 (Rückstands-Klasse)“ – wobei das zugehörige
Issue inzwischen (03.11.) **geschlossen** war, die Kadenz-Projektion hatte
daher keinen Ort mehr.

## 2. Die Heilung – fünf Teile, davon ein neuer Selbstheilungs-Lauf

**(1) Neuer Workflow `.github/workflows/befund-akte-nachziehen.yml`
(„Befundakte nachziehen“).** Er schließt die Lücke zwischen externen
Inhalts-Edits und dem Tageslauf:

- Trigger: `push` auf `main`, aber **nur** diese Pfade: `content/posts/**`,
  `data/faktenfrische_queue.json`, `data/faktenfrische_entscheidungen.yaml`,
  `scripts/faktenfrische_befund_akte.py`,
  `scripts/faktenfrische_befund_ledger.py`, sich selbst; plus
  `workflow_dispatch`.
- Erzeugt Akte und Zustand mit dem verbindlichen Generator
  (`faktenfrische_befund_akte.py --schreiben`) und committet **nur bei
  echter Änderung**: `git diff -I'^\s*"erzeugt":' --quiet` überspringt reine
  Erzeugungszeitpunkt-Differenzen (der Zeitstempel läuft bei jedem Lauf –
  sonst committe der Bot die Uhr statt des Befunds); `[skip ci]`;
  `git_sync.sh` übernimmt Fetch/Rebase/Push mit Retry; `contents: write`;
  concurrency-Gruppe gegen Doppel-Läufe.
- Der Lauf selbst berührt nur `BEFUND-AKTE.md` und
  `data/faktenfrische_befunde_state.json` → **kein Selbst-Trigger**.
- **Lokal simuliert** (frische Worktree, beide Zweige): unveränderter Baum →
  „Nur Erzeugungszeitpunkt – kein Commit“; externer Content-Edit →
  „WUERDE COMMITTEN“ (semantisch abweichend) – beides korrekt.
- Vertrags-Wache: YAML parse, `workflow_vertrag_wache.py --selftest` grün,
  `--online --gate` → **100 Workflow-Dateien vertragsgemäß**;
  Konfliktmarker-Wache sauber; `artefakt_waechter` unverändert heil.

**(2) Stand auf `main` ist heute wahr:** committed = live erzeugt = **19
Befunde / 8 überholt** (verifiziert am 06.11.2026, 15:15 UTC).

**(3) #1067 geschlossen** mit Referenz auf #1103 (squash `30e401576`, alle
Checks grün). Der ältere Ersatz-PR ist damit nicht mehr unerreichbar offen;
Git-Historie unangetastet.

**(4) #922 gemessen statt vermutet** (alles read-only, nichts geändert):
Environment `cloudflare-produktion` – **Required Reviewer fehlt**,
**Administrator-Bypass aktiv oder nicht belegbar**, **Branch-Policy
keine** (kein Zweig eingeschränkt); Zugang: **`CF_WORKERS_DEPLOY_TOKEN`
und `CLOUDFLARE_ACCOUNT_ID` nicht lesbar** (5 Befunde, FEHLT/OFFEN,
fail-closed gewollt); Selftests `worker_zugang`, `worker_ressourcen`,
`worker_environment_guard` grün. Befund + zwei Inhaber-Schritte als
Kommentar auf #922 (Settings + `worker_environment_einrichten.py --anwenden`
als API-Teil; Administrator-Bypass bleibt ein Schalter im Dashboard).
**Bewusst NICHT ausgeführt** – Produktions-Umgebungsschutz ist Inhaber-Sache.

**(5) #1107 erstellt („⏰ Frist: Kadenz-Horizont – projiziert 26.11./31.12.2026
rot, auch am Limit (Frist 20.11.2026)“)** – die Kadenz-Projektion hat wieder
einen Ort, mit Frist, drei gemessenen Optionen (A Takt enger / B Intervall /
C Korridor), ohne eine Entscheidung für den Herausgeber zu treffen. Ab der
Schwelle feuert die bestehende Selbstheilungs-Schleife (Wache → Deckungs-Ticket
mit Schließpfad; seit #1103 live) automatisch.

## 3. Ehrliche Grenzen

- Der neue Lauf heilt **die Akte-Klasse**; er entscheidet keine Befunde und
  heilt keinen Inhalt.
- Alters- und Fristfelder („ältester N Tage“, „Über der Frist“) springen mit
  dem Kalender; ein Commit ohne neue Befunde ist legitim und im Hausstil.
- Externe Content-Edits **nach** `main`-Pushes werden beim Merge erfasst;
  Feature-Branches werden nicht nachverfolgt (gewollt – main ist der
  Wahrheitsort).
- **#922 bleibt offen** und braucht den Inhaber (Cloudflare + Environment
  Settings; der Deploy sperrt absichtlich bis zur manuellen Absicherung).
- **#1107 braucht eine Frist-Entscheidung bis 20.11.2026**; bis dahin tritt
  der 26.11.-Exit-1-Horizont nicht ein. Die Kadenz-Optionen A–C wurden
  nicht „mit 2 Läufen/Tag“ vermessen – die Rechnung verweigert das absichtlich
  (kein Wochenmittel als Tagesplan). Der Herausgeber vermisst beim Setzen des
  Cron; seine Option C (Korridor) setzt einen bewusst menschlichen signierten
  Schritt in der SSOT voraus.
- Die committed Akte kann zwischen zwei Inhalts-Edits erneut steigen – das
  ist kein Defekt mehr, sondern der Arbeitsrhythmus des Bestands; der neue
  Lauf hält sie maximal bis zum nächsten Merge auf `main`.

## 4. Geänderte/neue Dateien

- `.github/workflows/befund-akte-nachziehen.yml` – **neu**: der
  Selbstheilungs-Nachziehen (push + dispatch; nur-bei-Änderung-Commit)
- `docs/ANLEITUNG-FAKTENFRISCHE.md` – Verweis auf den Nachzieh-Lauf
- dieser Bericht

## 5. Nachweise

```text
YAML-Parse befund-akte-nachziehen.yml .......... ok (jobs: nachziehen; push + dispatch)
workflow_vertrag_wache --selftest .............. ok (V1–V6)
workflow_vertrag_wache --online --gate ......... ✅ 100 Workflow-Dateien vertragsgemäß
konfliktmarker_wache --paths <neu> ............. ✅ keine Marker
Simulation unveränderter Baum .................. „Nur Erzeugungszeitpunkt – kein Commit“
Simulation externer Content-Edit ............... „WUERDE COMMITTEN“ (semantisch)
Generator (05.-06.11.): committed = live ....... 19 Befunde / 8 überholt / 6 Seiten / 5 live
```

**Vorgang:** #912-Klasse · **Bezug:** #1103 (gemergt) · #1107 (Frist 20.11.) ·
#1072 (Redaktionsakte, synchron mit Akte) · **Offen:** #922 (Inhaber)
