# GSC-Datenintegrität – Highend-Dauerheilung (24.10.2026)

**Vorgang:** Blockade des Pull-Requests #853 (Dauerheilung zu #822)
**Befund:** Drei Search-Console-Artefakte in `main` waren seit dem 21.10.2026
kein gültiges JSON mehr – zusammengesetzt aus mehreren Läufen. Das
`Integritäts-Siegel` stand dadurch für **jeden** Pull-Request des Repos auf Rot.
**Heilung:** belegbare Wiederherstellung des letzten vollständigen Laufs,
`merge=binary` für die drei Dateien, eine Wache über *Bedeutung* statt nur
Syntax (G1–G4), verdrahtet in zwei Gates und die Regressionstests.

---

## 1. Befund

Der Lauf zu #853 (`Integritäts-Siegel`, Run 40115286500, Job 120935193209) war
nach 23 Sekunden rot. Mehr war über die API nicht zu bekommen:

```
Integritäts-Siegel   fail   23s
Annotation: .github:30  failure  Process completed with exit code 1.
gh run view --log-failed --job=120935193209
  → failed to get run log … results-receiver.actions.githubusercontent.com … EOF
```

Statt zu raten, wurde der Job **lokal Schritt für Schritt nachgefahren** – in
derselben Reihenfolge wie in `.github/workflows/integrity-lock.yml`:

| Schritt | lokal | Ergebnis |
|---|---|---|
| `integrity_guard.py --gate` | ✅ | 50 Kerndateien == signierter Stand (`HEAD 5e720fc`) |
| `integrity_guard.py --selftest` | ✅ | 9 Fälle grün |
| `actions_version_guard.py --selftest/--gate` | ✅ | keine Drift |
| `artefakt_waechter.py --selftest` | ✅ | – |
| **`artefakt_waechter.py`** | **🛑** | **3 Funde (A1-JSON-SYNTAX)** |
| `pflichtcheck_guard.py` | ✅ Exit 0 | dokumentierter Dauerzustand (C15/C18) |

```
🛑 ARTEFAKT-WÄCHTER: 3 Fund(e) in 480 Artefakten.
   [A1-JSON-SYNTAX] data/gsc/meta.json                 Zeile 8
   [A1-JSON-SYNTAX] data/gsc/top_seiten_28t.json       Zeile 22
   [A1-JSON-SYNTAX] data/gsc/top_suchbegriffe_28t.json Zeile 88
```

Damit war die Ursache belegt: **nicht** das Siegel, **nicht** die Actions –
drei Datenartefakte der Search Console.

### 1.1 Wie die Dateien aussahen

`data/gsc/meta.json` (gekürzt, echt):

```json
{
  "stand": "2026-10-24T09:31:07Z",
  "zeitraum": { "von": "2026-07-24", "bis": "2026-10-21"
  "stand": "2026-10-23T10:01:50Z",
  "stand": "2026-10-22T10:09:09Z",
  "stand": "2026-10-21T10:06:23Z",
  "stand": "2026-10-20T10:01:45Z",
  …
```

Vier `stand`-Schlüssel in einem Objekt, die schließende Klammer von `zeitraum`
fehlt, kein Trennkomma. In `top_seiten_28t.json` klebten im Eintrag
`impressum` drei Fragmente ohne Komma; in `top_suchbegriffe_28t.json` trug der
Eintrag `kostenloses girokonto bremen` zweimal `clicks`, `impressions` und
`ctr` – die Kennzahlen des **nächsten** Laufs.

Das ist keine zufällige Beschädigung: Es ist der Fußabdruck eines **Text-Merges**
auf einem Artefakt, das immer als Ganzes geschrieben wird.

## 2. Ursache

`gsc_import.py` schreibt jede Datei vollständig neu
(`Path.write_text(json.dumps(...))`, siehe `lauf()` / `_schreibe_meta()`).
Zwei gültige Läufe können so niemals zu einer Datei verschmelzen. Die
Verschmelzung ist beim **Zusammenführen der Bot-Branches** entstanden:

| Commit | Zeit (UTC) | Was |
|---|---|---|
| `4a527d2e` | 20.10. | letzter Lauf, in dem **alle drei** Dateien gültig waren (PR #825) |
| `d0f9db91` | 24.10. 13:38 | **erste kaputte Fassung in `main`** (PR #828, Lauf vom 21.10.) |
| `6200a097` | 13:39 | PR #830 – kaputtes `meta.json`, neue Top-Listen |
| `1c7208d7` | 13:44 | PR #837 – dito |
| `ed7b8b2a` | 13:47 | PR #843 – dito (Endstand bis zur Heilung) |

PR #828 enthält drei Commits: den Bot-Lauf `00c92090` und **zwei manuelle
`Merge branch 'main' into automation/gsc-tagesdaten-20261021`** (`0d920b6b`,
`cb74eba3`). Genau dort wurden die Blöcke ineinandergeschoben. Der Diff ist
bezeichnend – er *fügt ein*, statt zu ersetzen:

```diff
 {
+  "stand": "2026-10-21T10:06:23Z",
+  "quelle": "…",
+  "zeitraum": {
+    "von": "2026-07-21",
+    "bis": "2026-10-18"
   "stand": "2026-10-20T10:01:45Z",
```

### 2.1 Warum es niemand vor dem Merge gesehen hat

Vier Lücken, jede für sich harmlos, zusammen eine Blockade:

1. **Kein Merge-Schutz an den Dateien.** `.gitattributes` verhinderte den
   Text-Zusammenschnitt für das Siegel (#346), die Reserve-Snapshots (#634) und
   die Quelltext-Wachen (#783) – für `data/gsc/*.json` gab es keine Regel.
   Ein Text-Merge hat auf einer Messung keine Zeile, die zu beiden Läufen gehört.
2. **Der schreibende Lauf prüfte nicht, was er schreibt.** `gsc-import.yml`
   las `meta.json` danach nur für einen Statuswert
   (`… || echo unbekannt`) – ein Parse-Fehler wurde zu „unbekannt“.
3. **Die Tests liefen für Daten-PRs nicht.** `regression` – der einzige Job mit
   der vollen Suite – hat `data/gsc/**` nicht in seiner Pfadliste. Der PR, der
   den Schaden brachte, hat keinen Test ausgelöst.
4. **Der Fund war da, hielt aber nichts auf.** Der Artefakt-Wächter im
   `Integritäts-Siegel` meldete den Defekt sofort (A1, hart) – der Check ist
   aber kein verlangter Status-Check (dokumentierter Dauerzustand,
   `pflichtcheck_guard.py`, Runbook `docs/PFLICHT-CHECK-RUNBOOK.md`). Rot
   gemergt wurde trotzdem.

Zwischen 13:38 und 17:15 UTC sind 23 Integritäts-Läufe gelaufen, 21 davon rot.

## 3. Heilung: der letzte vollständige Lauf

Repariert wurde **nicht** durch Rekonstruktion. Ein zusammengesetztes
Messartefakt lässt sich nicht zurückrechnen, ohne Zahlen zu erfinden – die
Repo-Regel aus #653 gilt hier genauso. Wiederhergestellt wurde der letzte
Commit, in dem **alle drei Kopfdaten gemeinsam** gültig sind:

```bash
python3 scripts/gsc_artefakte_guard.py --heal --rev 4a527d2e
🔧 Gesamtstand 4a527d2e7209: meta.json + beide Top-Listen werden gemeinsam gesetzt
✅ data/gsc/ ist nach der Heilung grün.
```

| Datei | Stand danach |
|---|---|
| `meta.json` | `stand 2026-10-20T10:01:45Z`, Fenster 2026-07-20 … 2026-10-17, `status: ok`, 28 Tage |
| `top_seiten_28t.json` | 23 Seiten aus diesem Lauf |
| `top_suchbegriffe_28t.json` | 4 Suchbegriffe aus diesem Lauf |
| `tagesdaten.jsonl` | **unverändert** – 32 Tage bis 2026-10-21 (append-only, je Tag eine eigene Messung) |

Bewusst *nicht* „pro Datei das Neueste“: Der Einzel-Heilpfad hätte für
`top_suchbegriffe_28t.json` den Lauf vom 22.10. gefunden und für `meta.json` den
vom 20.10. – drei Dateien aus drei Läufen ergeben wieder eine Chimäre, nur eine,
die die Syntaxprüfung besteht. Deshalb `--rev`: **ein Lauf = eine Messung.**

## 4. Was die Zahlen der Läufe 21.–24.10. betrifft (ehrliche Grenze)

Sie sind **verloren**. Die Verkettung hat die Zuordnung von Zeilen zu Läufen
zerstört; die Fragmente lassen sich zwar lesen, aber nicht mehr sicher einem
Fenster zuordnen. Es wurde nichts gemittelt, nichts ergänzt, nichts geschätzt.
Der nächste reguläre Import (`.github/workflows/gsc-import.yml`, täglicher Lauf
mit `GSC_SERVICE_ACCOUNT_JSON`) schreibt alle drei Dateien ohnehin vollständig
neu aus der API. Bis dahin steht in `meta.json` sichtbar der 20.10. – ein
lesbarer, ehrlicher Stand statt einer Chimäre.

## 5. Dauerheilung: vier Schichten

### 5.1 Struktur – `merge=binary`

```
data/gsc/meta.json merge=binary
data/gsc/top_seiten_28t.json merge=binary
data/gsc/top_suchbegriffe_28t.json merge=binary
```

Der Text-Zusammenschnitt ist damit **technisch unmöglich**; bei parallelen
Änderungen bleibt eine vollständige Fassung übrig, der Konflikt wird bewusst
gelöst. Der Tagesledger bleibt bewusst bei `*.jsonl merge=union` – Tage sind
unabhängige Messungen, ihre Vereinigung ist korrekt.

### 5.2 Bedeutung – `scripts/gsc_artefakte_guard.py`

| Prüfung | Frage |
|---|---|
| **G1** | Kopf vollständig und plausibel (Pflichtfelder, `stand` ISO-UTC, `von <= bis`, `status` bekannt, Kennzahlen bei `status: ok`) |
| **G2** | Top-Listen: genau die Schlüssel des Erzeugers, Wertebereiche, **jeder Eintrag nur einmal** |
| **G3** | Ledger: Zeilenschema, Datum **streng aufsteigend, ohne Doppel** |
| **G4** | Kopf gegen Zahlen: `zeitraum.bis` nicht hinter dem letzten Tag, `tage_gesamt` nicht über den gemessenen Tagen |

G2–G4 sind der eigentliche Gewinn: Zwei **gültige** Top-Listen hintereinander
ergeben weiterhin gültiges JSON – nur mit doppelten Suchbegriffen und Zahlen
aus zwei Fenstern. Genau diese Klasse hätte der Artefakt-Wächter (A1/A2) nie
gesehen, wenn der Merge zufällig „glatt“ gelaufen wäre.

Die Wache ist **fail-closed** und kennt einen deklarierten Zustand: Hat ein Repo
gar keinen Search-Console-Zugang, schreibt `gsc_import.py` nur `meta.json` mit
`status: nicht_konfiguriert` – das ist kein Fund (die Datei sagt selbst, warum).
Sobald gemessen wurde (`status: ok`), sind fehlende Dateien ein Fund.

### 5.3 Herkunft – Heilung nur mit Beleg

```bash
python3 scripts/gsc_artefakte_guard.py --heal                 # je Datei: jüngster gültiger Git-Stand
python3 scripts/gsc_artefakte_guard.py --heal --rev <sha>     # Gesamtstand aus EINEM Lauf
```

Regeln im Code:

* kein belegbarer Stand → **keine** Heilung (Exit 1, Datei unberührt),
* Ledger wird **nie** zurückgerollt,
* Gesamtstand ist **ganz oder gar nicht** (kein Teilstück),
* nach dem Schreiben wird die Datei **erneut** geprüft; schlägt das fehl, wird
  der alte Inhalt zurückgeschrieben.

### 5.4 Verdrahtung

| Ort | Änderung |
|---|---|
| `.github/workflows/integrity-lock.yml` | neuer Schritt „Search-Console-Artefakte (gültig, eindeutig, zueinander passend)“ direkt hinter dem Artefakt-Wächter – **jeder PR** |
| `.github/workflows/gsc-import.yml` | neuer Schritt „Leistungsdaten prüfen, bevor sie als PR gehen“ **vor** Commit und PR-Eröffnung – kein kaputtes Artefakt verlässt den Schreiber |
| `.github/workflows/publication-reliability-tests.yml` | `data/gsc/**` in der Pfadliste – Daten-PRs lösen die Suite aus |
| `scripts/tests/test_gsc_artefakte.py` | 26 Regressionstests: Bestand, jede Defektklasse, Heilung, Verweigerung, Ledger-Schutz |
| `scripts/governance_contract.py` (`GUARDS`/C6) | Selbsttest der Wache läuft im vertraglichen Minimum |

## 6. Belege

| Befehl | Ergebnis |
|---|---|
| `gsc_artefakte_guard.py --check` (vorher) | 🛑 3 Funde (G1, G2, G2) |
| `gsc_artefakte_guard.py --heal --rev 4a527d2e` | 🔧 Gesamtstand gesetzt, ✅ grün |
| `gsc_artefakte_guard.py --check` (nachher) | ✅ vier Dateien gültig, eindeutig, passend |
| `gsc_artefakte_guard.py --selftest` | ✅ 20/20 Fälle |
| `artefakt_waechter.py` | ✅ 480 Artefakte strukturell heil (vorher: 3 Funde) |
| `python3 -m unittest discover -s scripts/tests -p "test_gsc_artefakte.py"` | ✅ 26 Tests |
| `governance_contract.py --quick` | ✅ 41 Regeln |
| `yaml.safe_load` auf die drei geänderten Workflows | ✅ gültig |

## 7. Dateien

| Datei | Art |
|---|---|
| `data/gsc/meta.json`, `top_seiten_28t.json`, `top_suchbegriffe_28t.json` | repariert (Gesamtstand `4a527d2e`) |
| `scripts/gsc_artefakte_guard.py` | neu – Wache + Heilung + Selbsttest |
| `scripts/tests/test_gsc_artefakte.py` | neu – 26 Regressionstests |
| `.gitattributes` | `merge=binary` für die drei Kopfdaten |
| `.github/workflows/integrity-lock.yml` | Wache im PR-Gate |
| `.github/workflows/gsc-import.yml` | Wache vor Commit/PR |
| `.github/workflows/publication-reliability-tests.yml` | `data/gsc/**` löst die Suite aus |
| `scripts/governance_contract.py` | Wache im vertraglichen Minimum (C6) |
| `docs/ANLEITUNG-GSC-API-ZUGRIFF.md` | Runbook „Wenn ein Artefakt kaputt ist“ |
| `CLAUDE.md` | Regel „Ein Messartefakt ist eine ganze Messung, kein Text“ |

`data/gsc/tagesdaten.jsonl` und `data/audit/` wurden **nicht** angefasst.

## 8. Rest-Risiken

1. **Die Zahlen vom 21.–24.10. sind weg.** Nicht rekonstruierbar (Abschnitt 4).
   Der nächste API-Lauf ersetzt sie; bis dahin ist der Stand sichtbar vom 20.10.
2. **Ein grüner Check hält weiterhin keinen Merge auf.** Der dokumentierte
   Dauerzustand (kein verlangter Status-Check, C18) ist unverändert; diese
   Heilung ändert ihn nicht und kann es ohne Admin-Rechte nicht. Sie sorgt
   dafür, dass der Check überhaupt wieder eine Aussage trifft.
3. **Die Wache prüft Plausibilität, nicht Wahrheit.** Ob die Zahlen von Google
   stimmen, kann nur Google sagen; geprüft wird, dass der Bestand in sich
   stimmig und eindeutig ist.
4. **Ohne Zugang bleibt der Bestand alt.** Fehlt `GSC_SERVICE_ACCOUNT_JSON`,
   schreibt der Import nur den Kopf (`status: nicht_konfiguriert`) – die Wache
   meldet das nicht als Defekt, aber die Daten veralten. Das ist Absicht: ein
   deklarierter Zustand ist besser als ein Dauer-Rot.
5. **`merge=binary` entscheidet nicht, *welcher* Stand richtig ist.** Es erzwingt
   nur EINE Fassung. Die richtige wählt der Mensch bzw. `--heal --rev` nach
   Beleg – und genau deshalb gibt es den zweiten Schritt.

---

*Dieser Bericht ist der Nachweis zum Blockade-Befund von #853; er wird mit dem
Pull-Request geschlossen. Die Ursache des eigentlichen Vorgangs #822 steht in
`PINTEREST-822-DAUERHEILUNG-PREMIUM-2026-10-24.md`.*
