# Vorgang WF-7B6B · #654 – Dauerheilung (Manifest-Wache)

**Datum:** 08.10.2026
**Meldung:** #654 „🔧 Wartung · Lesbarkeit & Gestaltung · Vorgang WF-7B6B“ (Alert-Key `WF-7B6B`, Bereich *Lesbarkeit & Gestaltung*, Workflow *E2E-Tests (Playwright)*)
**Auslöser:** Scheduled-Lauf **37772974053** auf `main` (Commit `2aae8c35`, 11:52:39Z). Der Schritt „Abhängigkeiten installieren“ war nach **einer Sekunde** rot.

---

## Kurzfassung

- **Ursache:** `package.json` war ungültiges JSON. Ein Merge (#647) hatte einen Abhängigkeitsblock mit fehlendem Komma, doppeltem Schlüssel `pagefind` und doppeltem `lighthouse` auf `main` gebracht. `npm ci` bricht bei dieser Datei sofort ab.
- **Schaden:** E2E auf `main` rot (11:52). Alle drei Produktions-Deploys zwischen 10:41 und 12:50 UTC rot, jeweils im Schritt „Suchindex bauen (Pagefind)“, der ebenfalls `npm ci` ausführt. In diesem Fenster wurde nichts neu veröffentlicht.
- **Sofortheilung:** #651 (`e185a970`, 12:50:28Z). Deploy **37779771230** grün. `package.json` auf `main` ist seit diesem Commit gültig.
- **Dauerheilung (dieser Vorgang):** Eine Manifest-Wache prüft Manifest und Lockfile vor jedem `npm ci` (sieben Workflows, fail-closed). Sie nennt Datei, Zeile und Ursache und zeigt den Befund als Annotation an der Zeile. Die Alarm-Meldung nennt bei Install-Fehlern die Manifest-Diagnose statt des API-Key-Rats. Dazu kommen Selbsttest, Regressionstests, Runbook und ein Vertragseintrag (C6).

---

## 1. Zeitleiste (UTC, 08.10.2026)

| Zeit | Ereignis | Beleg |
|---|---|---|
| 09:31 | Merge #644 (`654bda42`): `package.json` gültig | Commit-Historie |
| 10:18 und 10:40 | PR-Läufe von #647 (Zweig `arena/cbc764a7`) rot im Schritt „Abhängigkeiten installieren“, je 1 s | Runs 37762588236, 37765057066 |
| 10:41:03 | Letzter roter PR-Lauf endet | Run 37765057066 |
| 10:41:17 | Squash-Merge #647 → `dcc31385` auf `main`. `package.json` ist ungültig | Commit-Historie |
| 10:41:20 | Deploy (push) auf `dcc31385` startet, rot | Run 37765112717 |
| 11:26:41 | Dieser Deploy rot im Schritt „Suchindex bauen (Pagefind)“, 1 s | Run 37765112717 |
| 11:52:39 | E2E (schedule) auf `main` rot im Schritt „Abhängigkeiten installieren“, 1 s | Run 37772974053 |
| 11:53:09 | Meldung #654 angelegt. Der Ratschlag nennt API-Key, GitHub-Ausfall, Transient | Issue #654 |
| 11:55:36 | Deploy (dispatch, `2f06e9e3`) rot im Schritt „Suchindex bauen“ | Run 37770425803 |
| 12:42:53 | Deploy (dispatch, `a979120f`) rot im Schritt „Suchindex bauen“ | Run 37775586729 |
| 12:50:28 | Reparatur #651 (`e185a970`). Deploy grün | Run 37779771230 |

Letzter erfolgreicher Deploy vor dem Fenster: 10:32 (`dcfad083`, Run 37764106417). Der Deploy-Catchup stößt nur `deploy.yml` an und veröffentlicht selbst nichts.

Die Deploy-Fehler von 09:12 bis 10:00 (Schritt „Build (für Publish-Gate + Publish)“) sind eine andere Klasse, dokumentiert in `WF-54C4-643-DAUERHEILUNG-PREMIUM-2026-10-08.md`.

---

## 2. Ursache

Die defekte Stelle im roten `main`-Stand (`2aae8c35`, Zeilen 179–183):

```json
  "dependencies": {
    "pagefind": "1.5.2"
    "lighthouse": "13.5.0",
    "pagefind": "^1.5.2"
  }
```

Drei Fehler in einem Block:

1. **Fehlendes Komma** nach `"pagefind": "1.5.2"`. Der Parser meldet `Zeile 181, Spalte 5` (Node: „line 181 column 5“).
2. **Doppelter Schlüssel** `pagefind`. JSON erlaubt das, npm übernimmt aber still den letzten Wert.
3. **`lighthouse` steht zusätzlich** in `dependencies`, obwohl es schon in `devDependencies` steht.

Die PR-Läufe des Branches zeigten dasselbe Muster schon vor dem Merge. Der Merge kam 14 Sekunden nach dem letzten roten Lauf, weil E2E kein Pflicht-Check ist (siehe Abschnitt 6).

---

## 3. Warum die Meldung nicht half

Die Meldung nannte den roten Schritt korrekt. Sie deutete ihn aber als API-Key-, GitHub- oder Transient-Problem. Ein Install-Schritt braucht keinen API-Key. Ein Fehler in einer Sekunde ist ein Konfigurationsfehler, kein Netzwerkproblem. Das Runbook passte für diese Klasse nicht. Es ist jetzt korrigiert (Abschnitt 4).

---

## 4. Heilung: was geändert wurde

| Datei | Änderung |
|---|---|
| `scripts/manifest_guard.py` (neu) | Manifest-Wache. Prüfungen K1, J1, J2, F1, D1, L1–L4, P1. Selbsttest mit 19 Proben (Sabotage und Gegenproben). Modi `--ref`, `--json`, GitHub-Annotationen |
| `scripts/tests/test_manifest_guard.py` (neu) | 16 Regressionstests: Selbsttest, Vorfall als echter Git-Commit, Repo-Dauerbeweis, Widerstandsfälle, Verdrahtung aller `npm ci`-Jobs, Eintragungen |
| `.github/workflows/deploy.yml` | Schritt „Manifest-Schutz“ direkt nach dem Merge-Marker-Schutz, vor allen Gates und dem Build |
| `.github/workflows/e2e.yml` | Schritt „Manifest-Wache“ direkt nach dem Checkout. Pfadfilter um Wache und Test erweitert |
| `design-varianten.yml`, `lesehilfen-gate.yml`, `robustheit.yml`, `themenwelten-gate.yml`, `werkbank.yml` | Schritt „Manifest-Wache“ vor jedem `npm ci` |
| `.github/workflows/alert-on-failure.yml` | Bei Install- und Manifest-Schritten: Manifest-Diagnose statt API-Key-Rat. Die übrigen Ratschläge bleiben unverändert |
| `scripts/tests/sim/alert_scoping_sim.mjs`, `scripts/tests/test_alert_scoping.py` | Drei neue Szenarien (#654-Reproduktion, Deploy, Gegenprobe ohne Install-Bezug). Simulation jetzt 22 Szenarien |
| `scripts/governance_contract.py` | `manifest_guard.py` in `GUARDS`. Der Selbsttest ist damit Vertragsminimum (C6) |
| `package.json` | Skripte `manifest:check` und `test:manifest` |
| `CLAUDE.md` | Befehle in der Pipeline und Abschnitt „Das Manifest ist der Bau-Eingang“ |
| `docs/ANLEITUNG-MANIFEST-WACHE.md` (neu) | Runbook: Prüfungen, Bedienung, Orte, Reaktion auf den Alarm, Grenzen, Erweiterung |
| `WF-7B6B-654-DAUERHEILUNG-PREMIUM-2026-10-08.md` (neu) | dieser Bericht |

**Entscheidungen im Detail:**

- **Eine Quelle für alle Manifeste.** Die Wache findet alle `package.json` und `package-lock.json` im Repo: Wurzel, `tools/ff-voice-browser`, `tools/ff-voice-qa`. Für `newsletter-worker` gibt es eine eng begrenzte, begründete Ausnahme. Das Manifest hat kein Lockfile und wird in keinem Workflow per `npm ci` installiert.
- **Kalibriert an npm, nicht an Vermutungen.** Dieselbe Abhängigkeit in `dependencies` und `devDependencies` ist nur eine Warnung (D1), denn `npm ci` läuft damit durch. Ein doppelter Schlüssel ist ein Fehler (J2), denn npm übernimmt still den letzten Wert. Belegt: `is-number` wird mit doppeltem Schlüssel als `6.0.0` installiert.
- **Die Grenze ist benannt.** Versions-Ranges wie `^30.1.2` prüft die Wache nicht. Das entscheidet `npm ci`. Die Wache sagt nur vorher, woran es liegt.
- **Fail-closed im Produktionspfad.** Der Deploy-Schritt steht vor allen Gates und vor dem Build. Er ändert am Inhalt nichts, er stoppt nur früher und sagt, warum.
- **Der Ausweichweg in `robustheit.yml`** (`npm ci || npm install`) könnte ein defektes Lockfile still reparieren. Die Wache läuft davor, deshalb kann dieser Weg bei einem Manifest-Fehler nicht mehr greifen. Für Registry-Hänger bleibt er bewusst bestehen.

---

## 5. Beweis

| Prüfung | Ergebnis |
|---|---|
| `python3 scripts/manifest_guard.py --selftest` | ✅ 19 Proben (Sabotage und Gegenprobe) gefangen |
| `--ref 2aae8c35…` (roter `main`-Stand) | ❌ J1 `package.json` Zeile 181, Spalte 5. Derselbe Ort wie beim Parser |
| `--ref dcc31385…` (Merge #647) | ❌ J1 `package.json` Zeile 181, Spalte 5 |
| `--ref 654bda42…`, `--ref e185a970…`, `--ref f28ab9ae…` | ✅ grün |
| `python3 scripts/manifest_guard.py` (Arbeitsbaum) | ✅ grün, 0 Warnungen, 7 Dateien geprüft |
| `npm ci --ignore-scripts` mit aktuellem `package.json` und Lock (isolierte Kopie) | ✅ Exit 0, 156 Pakete |
| `python3 -m unittest scripts.tests.test_manifest_guard` | ✅ 16 von 16 |
| `python3 -m unittest discover -s scripts/tests` (vollständig, im Repo) | ✅ siehe Abschnitt 5a |
| `node scripts/tests/sim/alert_scoping_sim.mjs` (Alarm-Skript aus der YAML) | ✅ 22 von 22 |
| `python3 scripts/governance_contract.py` (voll, inkl. C6-Selbsttests) | ✅ alle 30 Regeln |
| `python3 scripts/automation_premium_audit.py --strict` | ✅ Exit 0 |
| `python3 scripts/alert_issue_identity.py --selftest` | ✅ 9 Fallgruppen |
| YAML aller 83 Workflows | ✅ parsen |
| `node --check` auf dem Alarm-Skript | ✅ |

**Nicht lokal bewiesen:** Hugo-Build und Playwright. Die Sandbox hat kein Hugo, und die Job-Logs von GitHub sind von hier nicht abrufbar. Den vollständigen Beweis liefert der CI-Lauf des Pull Requests.

### 5b. Pull-Request-CI (#659)

Auf Schritt-Ebene geprüft, nicht nur auf Job-Ebene:

| Job (Lauf) | Ergebnis | Manifest-Wache im Lauf |
|---|---|---|
| Playwright-Suite (Desktop + Mobile) (37800692228) | ✅ 5m10s | „Manifest-Wache“ ✅, danach „Abhängigkeiten installieren“ ✅, Chromium ✅ |
| robustheit (37800692138) | ✅ | ✅ vor dem Install |
| navigation / Themenwelten (37800692124) | ✅ | ✅ vor dem Browser-Install |
| lesehilfen (37800580418) | ✅ | ✅ vor den Install-Schritten |
| gate, regression, CodeQL (JS, Python), Klartext-Wache, Integritäts-Siegel, Regelwerk & Produktionswache | ✅ | – |

Nicht im PR-Lauf: `deploy` (nur Push auf `main`), `werkbank` in `design-varianten` und `werkbank.yml` (nur Zeitplan und manueller Start). Ihre Wache-Schritte sind über Verdrahtungstests und die YAML-Prüfung abgesichert. Die Ausführung folgt beim nächsten Lauf nach dem Merge. Sie laufen dasselbe Skript mit demselben Aufruf wie die vier grünen Jobs oben.

### 5a. Vollständiger Unit-Test-Lauf

Im Repo, mit Git-Historie, ohne Netz, vor dem Commit:

- **Erster Lauf:** 2338 Tests. Der einzige Fehlschlag war mein eigener Test (ein falscher Bezeichner `installFehler` statt `installFailed`). Er ist korrigiert.
- **Abschlusslauf:** `Ran 2338 tests` · `OK (skipped=11)` · Exit 0. Die 11 Überspringungen gab es schon im Ausgangsstand und sind umgebungsbedingt.
- **Arbeitsbaum danach:** Nur die beabsichtigten Dateien geändert. Kein Test hat `data/audit/` beschrieben (C27).

---

## 6. Offene Punkte (nicht Teil dieses Vorgangs)

1. **Kein Pflicht-Check auf `main`.** Der Merge von #647 war möglich, obwohl der E2E-Lauf des Branches rot war. Die drei aktiven Rulesets auf `main` (*Integritäts-Lock (PR-Gate)*, *Premium-Schutz für main*, *main – Unveränderlichkeit (ohne Bypass)*) enthalten nur Löschschutz, Schutz vor Force-Push und lineare Historie. Keines verlangt einen Status-Check (Abfrage der Rulesets-API, Stand 08.10.2026). Der klassische Branch-Schutz war mit dem Arbeitstoken nicht lesbar (HTTP 403). Die Änderung ist eine Admin-Entscheidung (Governance-Regel C15). Empfehlung: „Playwright-Suite (Desktop + Mobile)“ und „Manifest-Wache“ als Pflicht-Checks für `main` hinterlegen.
2. **Lesehilfen-Gate auf `main` rot** (Run 37795103195, 14:45Z, Commit `742decd9`), Schritt „Funktionstest Vorlesen + Kurzfassung (echte DOM)“. Kein Install-Schritt ist betroffen, also andere Ursache als #654. Auf dem PR-Stand ist der Lauf grün (37800580418). Die Ursache auf `main` ist damit nicht geklärt: Es kann ein Flake oder ein Zustand des Commits `742decd9` sein. Beobachten, und bei erneutem Rot einen eigenen Vorgang anlegen (Bereich *Lesbarkeit & Gestaltung*, WF-7935).
3. **Abschluss:** Der Pull Request trägt `Closes #654`. Dann schreibt `vorgangs-abschluss.yml` den Vermerk. Der Alarm schließt sich ohnehin, sobald E2E auf `main` wieder grün läuft.

---

## 7. Grenzen dieser Analyse

- Die Job-Logs der Actions-Läufe sind aus der Sandbox nicht abrufbar, weil der Blob-Speicher nicht erreichbar ist. Die Ursache ist deshalb aus den Commit-Inhalten, den Zeitstempeln (Schritte in einer Sekunde) und dem lokalen Nachbau belegt, nicht aus dem Log selbst.
- Der Branch `gh-pages` enthält nur den jeweils letzten Stand. Der Livegang ist deshalb aus den Deploy-Läufen abgeleitet, nicht aus der Pages-Historie.
