# Bot-Watchdog #661: Der Nachweis war krank, nicht der Vorrat

**Stand:** 08.10.2026 (Nachtrag: zweiter Gang) · **Meldung:** [#661](https://github.com/frank-hartung/franksfinanzcheck-blog/issues/661)
· **Klasse:** maschinell behebbar, Besitzer Content-Automatisierung

> **„P2 · Content-Reserve niedrig (Maschine) – Reife-Zertifikat nicht verfügbar
> (Expecting property name enclosed in double quotes: line 28 column 5
> (char 738)); 15 Reserve-Entwürfe, Nachweis fehlt“**

## Das Urteil in einem Satz

Der Vorrat war gesund – **6 von 6 Kandidaten waren zertifiziert** –, aber der
Nachtlauf brachte diesen Nachweis seit Tagen nicht mehr nach `main`, und als
das Zertifikat dort unlesbar wurde, gab es weder eine eigene Befundklasse
dafür noch eine maschinelle Heilung. Das Ticket riet deshalb, vier neue
Kandidaten zu *produzieren* – eine Heilung, die an einem defekten JSON nichts
ändern kann.

## Die Ursachen der Meldung (U1–U4)

| # | Ursache | Beleg |
|---|---|---|
| **U1** | **Falsche Diagnose, falscher nächster Schritt.** `check_content_reserve()` fing jeden Parse-Fehler ab und meldete „Content-Reserve niedrig“; `reserve_finding()` hängte darum den Produktions-Schritt an. | Issue-Body #661: „Nachweis fehlt“ + „mindestens 4 zertifizierte Kandidaten herstellen“ |
| **U2** | **Keine maschinelle Heilung.** Einen Schnappschuss neu zu ziehen dauert Sekunden. `reserve_artifacts.py --check` konnte den Schaden nur *melden*. Damit hatte ein `owner: auto`-Befund keinen Schließpfad – derselbe Konstruktionsfehler wie #272. | Kein Schreibpfad auf `data/reserve-*.json` außerhalb des Nachtlaufs |
| **U3** | **Der Nachtlauf kam nicht durch.** 10 von 12 Läufen (`content-reserve.yml`) endeten rot, jedes Mal in „Entwürfe, Zertifikate und Reporte sichern“: `git_sync.sh: Rebase-Konflikt gegen origin/main` auf `content/posts/*/index.md`. Der frisch gemessene Pool blieb lokal; `main` behielt ein altes Zertifikat. | Runs 37803509309, 37765762299, 37645894042 (08.10.), 37486868704, 37450734141 … |
| **U4** | **Selbst gebauter Schreibkonflikt.** Der Watchdog startete den 45–90-Minuten-Produktionslauf und schrieb im selben Lauf selbst ein Zertifikat nach `main` („Reserve-Zertifikat nachziehen“). Zwei Schreiber, eine Datei, eine Nacht – der spätere Rebase des Reserve-Laufs kollidierte damit per Konstruktion. | `bot-watchdog.yml`: Dispatch stand VOR Nachzertifizierung und Nachmessung |

U3 und U4 erklären gemeinsam, warum die Meldung jeden Tag wiederkam: Selbst
ein gesunder Pool kann sein Zertifikat nicht nach `main` bringen, also bleibt
dort ein alter Stand – und ein alter Stand wird irgendwann unlesbar, ohne
dass jemand es merkt.

## Dauerhafte Änderungen

### A1 · Eigene Befundklasse statt Etikettenschwindel (`scripts/bot_watchdog.py`)

* Ein defekter Schnappschuss heißt jetzt **„Reserve-Nachweis beschädigt“**
  (`id: reserve-nachweis`), nennt die betroffene Datei samt Parse-Position
  und verweist auf die Heilung. Der Produktions-Schritt steht dort nicht mehr.
* **Fehlend** bleibt bewusst ein anderer Fall als **defekt**: Fehlt das
  Zertifikat ganz, fehlt ein Messlauf – die #462-Logik greift weiter.
* `RESERVE_DIAGNOSE` wird zu Beginn jeder Messung geleert. Ein Rest aus einem
  früheren Aufruf färbte sonst den Folgebefund (in der Regression
  nachgewiesen).

### A2 · Der Heiler (`scripts/reserve_snapshot_heiler.py`, neu)

`--check` · `--fix` · `--selftest`. Wirkt auf die drei Ganz-Schnappschüsse aus
`reserve_artifacts.STATE_FILES` und heilt **fail-closed**:

* **Zertifikat** – neu aus dem Bestand: jede Zeile trägt den **echten SHA-256**
  der Datei und `ready: false` mit Grund. **Nie** wird eine Reife behauptet,
  die nicht gemessen wurde; das Ziel kommt aus `reserve_economy.ziel()`, nie
  aus der beschädigten Datei (#393). Die echte Nachmessung macht danach
  `reserve_readiness.py`.
* **Bestands-Gedächtnis** – Buchhaltung, vollständig aus den Entwürfen
  ableitbar (`reserve_custody.bestandsaufnahme()`), deterministisch, kein
  Artikel wird angefasst.
* **Quarantäne** – Beweismaterial, nicht ableitbar. Deshalb wird nichts
  rekonstruiert, sondern der Schaden **belegt**: SHA-256, Größe und
  Fingerabdruck der defekten Bytes wandern in `data/reserve-history.jsonl`
  (append-only). Dann beginnt die Zählung nachvollziehbar bei null.
* Alle Schreibvorgänge laufen über `reserve_artifacts.write_object()`
  (atomar, fsync, Rückleseprobe), danach **Gegenprobe**; bleibt etwas
  ungültig, endet der Lauf rot. Intakter Zustand = kein geschriebenes Byte.

### A3 · Der Sync-Kern kann die Reserve-Klasse entscheiden (`scripts/git_sync.sh`)

* **Diagnose:** Vor jedem harten Abbruch nennt das Log jetzt die Klasse je
  Pfad – `stufe1/stufe2/stufe3` mit `reserve-entwurf`, `veroeffentlicht`,
  `fehlt` oder `fremd`. Zehn Nächte lang stand dort nur ein Dateiname.
* **`GIT_SYNC_RESERVE_POLICY=reserve-verwaltet`** (Opt-in, ausschließlich
  `content-reserve.yml`, Default bleibt `hart`): Zwei Klassen werden
  entschieden, in denen auf `main` **nichts** verloren gehen kann –
  a) `main` kennt den Pfad nicht mehr (Janitor, Datums-Umbenennung) → der
  Entwurf des laufenden Reserve-Laufs gewinnt; b) `main` hat den Kandidaten
  **veröffentlicht** → die Live-Fassung gewinnt, der Pfad wandert ins
  Nachheil-Protokoll. Voraussetzung in beiden Fällen: die **Basis** war ein
  Reserve-Entwurf.
* **Ganz-Schnappschüsse:** Fehlt eine Konfliktseite von
  `reserve-custody/-quarantine/-topic-ledger`, gewinnt die vorhandene – defekte
  Seiten bleiben weiterhin ein harter Konflikt (#634 unangetastet).

### A4 · Die beiden Schreiber arbeiten nacheinander (`bot-watchdog.yml`)

Erst der billige Weg (Snapshot heilen → nachzertifizieren), dann **neu
messen**, und nur wenn `CHECK8` danach immer noch warnt, die
Produktionslinie anstoßen. Ein Engpass, den eine Nachzertifizierung schließt,
kostet keine Produktionsnacht mehr – und kein zweiter Schreiber steht dem
Reserve-Lauf im Weg.

### A5 · Der Nachtlauf liest erst, wenn der Nachweis lesbar ist (`content-reserve.yml`)

Neue **Stufe 0** vor dem Janitor: `reserve_snapshot_heiler.py --fix`. Janitor,
Bestands-Wächter, Produktion, Veredelung, Konvergenz und der harte End-Gate
lesen dieselben drei Dateien; war eine defekt, starb die Nacht im ersten
Schritt mit einer Meldung, die auf Content-Engpass deutete.

Zusätzlich: `npm run reserve:snapshot` / `reserve:snapshot:fix` und die
Erweiterung von `npm run test:reserve`.

## Was bewusst NICHT geändert wurde

* **Keine Schwelle, kein Ziel, keine Gate-Regel gelockert.** Die neun
  blockierten Kandidaten bleiben blockiert; die Rekonstruktion zählt sie als
  `ready: false`. Die Alarmschwelle kommt weiter aus
  `reserve_economy.alarmschwelle()`.
* **Kein Live-Artikel, kein redaktioneller Text angefasst.** Der Heiler
  schreibt ausschließlich Zustandsdateien; die Sync-Politik greift nur, wenn
  die Basis ein Reserve-Entwurf war.
* **Der tägliche Datums-Lift (`reserve_finisher.lift_to_today`) bleibt**, obwohl
  er die Konfliktfläche vergrößert (jede Nacht 6–15 Ordner-Umbenennungen).
  Er ist in die Heiler-Steuerung eingewoben; ein Eingriff gehört in einen
  eigenen Vorgang mit eigener Messung – hier wäre er eine unbelegte
  Nebenwirkung.
* **Die neun offenen RS5-/RS2-Blocker sind NICHT Teil dieses Vorgangs.** Sie
  sind redaktionelle Qualitätsfragen an KI-Rohtexten, kein Automationsdefekt;
  der Vorrat erreicht sein Ziel ohne sie (6/6).

## Nachtrag (gleicher Tag, zweiter Gang): zwei weitere Ursachen

Beim Beweisgang für diesen Vorgang fiel auf, dass die Meldung #661 noch
einen zweiten und einen dritten Boden hat. Beide gehören in denselben
Vorgang, weil beide dieselbe Verwechslung betreiben: **„nicht gemessen“
wurde als „nichts gefunden“ ausgegeben.**

### U5 · Der Messvertrag war zwischenzeitlich stillgelegt

29 Regressionstests fielen auf `main` – ausgerechnet jene, die belegen,
dass ein Zertifikat nur gilt, wenn **Bytes, Nachbar-Gedächtnisse und Alter**
stimmen. Der Rückbau unter #662 hatte vier Funktionen auf einen reinen
JSON-Blick reduziert:

| Funktion | Vertrag (aus #634/#393/#295) | Stand unter #662 | Wirkung |
|---|---|---|---|
| `reserve_gate.evaluate()` | zählt Kandidaten **gegen die Entwurfsdateien** (`artifacts.verified_rows`) | liest nur das JSON | 10 Tests rot: ohne Bestand war jede Zahl eine Behauptung |
| `max_age_hours()` | klemmt `NaN`/`inf`/`≤0` auf 36 h (C2) | keine Klemmung | 4 Tests rot: die Notbremse war per Konfiguration abschaltbar |
| `cert_age_hours()` | echtes ISO-Datum mit Zone | Teilstring-Vermutung | 4 Tests rot: zukünftige und zonenlose Stempel galten als Alter |
| `freshness()` | fehlender **oder** zukünftiger Stempel ist **kein Nachweis** | nur Warnung | 6 Tests rot: „6 von irgendwann“ zählte als Vorrat |

Im Schreiber (`reserve_readiness.py`) kam Viererlei hinzu: Er stellte nach
der Messung nicht mehr **bytegenau** wieder her (CRLF-Zeilenenden gingen
verloren – der gespeicherte SHA-256 passte zu keinem Byte auf der Platte),
er nahm den Beweis-Abdruck nicht mehr **vor** dem Gate (eine Vorheilung
während der Messung blieb unbemerkt), er suchte die Frontmatter-Grenze
wieder selbst (die Zaun-Falle F1–F7 war damit zurück: eine `---`-Zeile in
einem YAML-Wert galt als „nicht lesbar“), und er lief ohne Vorprüfung in
ein beschädigtes Gedächtnis hinein.

**Maßnahmen (alle mit Regressionstest):**

* `evaluate()` prüft wieder gegen den Bestand; `max_age_hours()` klemmt
  wieder; `cert_age_hours()` liest ISO; `freshness()` ist wieder
  fail-closed. Das CLI bietet `--posts-dir` wieder an, und der Selbsttest
  legt seinen Bestand wieder **echt** auf die Platte – er darf die
  Quellenprüfung nicht weglassen, um grün zu bleiben.
* `reserve_readiness.py` misst und stellt bytegenau wieder her, nimmt den
  Abdruck **vor** dem Gate, stoppt vor **jeder** Mutation bei beschädigtem
  Gedächtnis (Exit 2) oder fehlendem Messwerkzeug (Exit 3) und schreibt das
  Zertifikat über den **einen** versiegelten Schreiber
  `artifacts.write_object` – mit Gegenprobe auf doppelte Schlüssel nach dem
  Tausch.
* **C33** verlangt den Beweis dafür jetzt dort, wo er erbracht wird: nicht
  ein eigenes `os.replace(` im Schreiber, sondern die Abgabe an den
  versiegelten Weg (der fsync, Rückleseprobe und Doppelschlüssel-Prüfung
  in sich vereint). Zusätzlich steht `scripts/reserve_artifacts.py` wieder
  unter dem Integritäts-Siegel – sonst wäre die Abgabe nur eine
  verschobene Behauptung.

### U6 · Das Messwerkzeug fehlte im CI – und die Wache schwieg dazu

Vier Stunden war der Integritäts-Lock rot, **ohne dass ein Artefakt kaputt
war**: Der Artefakt-Wächter liest YAML und Frontmatter mit PyYAML, und
`actions/setup-python` bringt PyYAML nicht mit. Jeder andere Python-Job
dieses Repos installiert es von Hand; im Integritäts-Lock fehlte der
Schritt.

Der eigentliche Fehler saß aber im Messgerät: `_yaml_laden()` fing das
fehlende Werkzeug mit `return [], []` ab. Auf einem Rechner ohne PyYAML
meldete die Wache damit **„386 Artefakte heil“**, ohne ein einziges YAML
gelesen zu haben. Ein Hart-Gate, das bei fehlendem Messwerkzeug grün wird,
ist schlimmer als keins: Es bezeugt eine Prüfung, die nie stattfand.

**Maßnahmen:**

* **Fail-closed:** Fehlt das Werkzeug, ist das ein **Befund** („nicht
  geprüft“) statt Stille. Wer das Werkzeug hat, merkt davon nichts; wer es
  nicht hat, sieht rot und die Ursache.
* **Der eigene Scanner trägt allein:** Doppelte Schlüssel findet
  `_yaml_doppelte_schluessel()` ohne jedes Drittwerkzeug. Der Selbsttest
  prüft jetzt **beide Welten** (mit und ohne PyYAML) und verlangt in beiden
  dasselbe Urteil; drei neue Regressionstests frieren das ein.
* **Der fehlende Schritt:** `integrity-lock.yml` installiert PyYAML wie
  alle anderen Python-Jobs. Jobname (`Integritäts-Siegel`), Filter und
  Reihenfolge bleiben unangetastet (C18).
* Das geänderte Siegel (`scripts/artefakt_waechter.py` steht unter
  Integritäts-Siegel) wurde **im selben Commit neu signiert** – 49
  Kerndateien, Herkunft im Lock.

## Nachweise

| Prüfung | Ergebnis |
|---|---|
| Gesamtsuite (`python3 -m unittest discover -s scripts/tests`) | **2.462 Tests**, davon 3 Fehler – alle drei `test_ki_transportweg` (fremd, vorbestehend, s. u.), 25 Skips. **29 Fehler aus U5 sind damit weg** (vorher 32) |
| Neue Regressionen `test_reserve_snapshot_heiler.py` | **10 Tests OK** (7 Sabotageproben + Befundklasse + Idempotenz) |
| Erweiterte Regressionen `test_git_sync.py` | **44 Tests OK** (davon 5 neu: zwei heilbare Klassen, zwei Schutzproben, ein harter Stopp ohne Opt-in) |
| Reserve-, Sync- und Routing-Module im Verbund | **116 Tests OK** |
| `scripts/selftest_runner.py` | **180 Wachen** (vorher 179), 356 Uhr-Proben; einziger Fehler: `ki_transportweg.py` (fremd) |
| `reserve_snapshot_heiler.py --selftest` | grün (7 Sabotageproben, offline) |
| `reserve_snapshot_heiler.py --check` am echten Bestand | grün – **kein Byte** am Live-Zustand geschrieben |
| `reserve_artifacts.py --check` | grün |
| `reserve_gate.py` | **6/6 zertifiziert**, Zertifikat frisch |
| `bot_watchdog.py --selftest` | grün |
| `automation_premium_audit.py --strict` | Exit 0 |
| `integrity_guard.py --gate` | grün, **49 Kerndateien** unverändert (Siegel neu signiert) |
| `artefakt_waechter.py --selftest` | grün **mit und ohne** PyYAML (zwei Welten, ein Urteil) |
| `artefakt_waechter.py` am echten Bestand | grün, 386 Artefakte strukturell heil |
| `reserve_gate.py --selftest` / `--chronik` | grün (8 Fälle, `--posts-dir` wieder verdrahtet) |
| `governance_contract.py` Kontrakt-Selbsttest | grün (C33-Kunstbefund zeigt auf die neue Marke) |
| `pflichtcheck_guard.py` | Exit 0 |
| `fm_boundary_guard.py --check` | grün (109 Dateien) |
| `manifest_guard.py` | grün (1 vorbestehende Warnung) |
| Synthetische End-to-End-Proben gegen `git_sync.sh` | Fall a (auf `main` gelöscht) und Fall b (auf `main` veröffentlicht) heilen mit Opt-in, bleiben ohne Opt-in harter Stopp **mit Klassen-Diagnose** |

**Vorbestehende Fremdbefunde (nicht Teil von #661, alle nachgewiesen auf
`main` selbst):**

* **`ki_transportweg.py`, T6** – `cloudflare/ki-assistent/worker.js` spricht
  den Gemini-Endpunkt direkt an. Drei Tests und eine Wache rot. Diese Datei
  wurde hier nicht angefasst; der Befund ist unter **Issue #665** erfasst und
  färbt *jeden* offenen Pull Request rot (verifiziert: gleiche Jobs, gleiche
  Meldung, auf `main` seit 17:15 Uhr und auf drei fremden PR-Branches).
* **`robustheits_gate.py`** – Selbsttest rot (ebenfalls Issue #665).

Die zwei in diesem PR damit roten Checks (`gate`, `regression`) sind
**nicht** durch diesen Vorgang entstanden: Sie fallen an exakt derselben
Stelle (`unittest discover`, Schritt 7) auf Branches, die mit #661 nichts zu
tun haben. Kein Fund dieses Vorgangs wurde unterdrückt, um sie grün zu
bekommen.

## Betriebsabnahme

1. `Bot-Watchdog` regulär laufen lassen (Cron 08:30 UTC) oder manuell
   auslösen. Erwartung: kein Reserve-Befund mehr; meldet er doch einen, nennt
   er die Klasse und heilt sie im selben Lauf.
2. `Content-Reserve` regulär laufen lassen (Cron 03:25 UTC). Erwartung:
   Stufe 0 grün, Sicherungs-Push erfolgreich – und bei einem Konflikt steht
   im Log, **welche** Klasse es war.
3. Bleibt „Stock shortage“ rot, ist es ab jetzt ein echter Content-Engpass
   und kein Nachweis-Artefakt: Die Diagnose nennt die Kandidaten mit Grund.

## Dateien

```
scripts/reserve_gate.py                             – Messvertrag restauriert (evaluate/max_age/ISO/freshness, --posts-dir, Selbsttest-Bestand)
scripts/reserve_readiness.py                        – bytegenau, Beweis vor dem Gate, Vorprüfungen, ein versiegelter Schreiber
scripts/artefakt_waechter.py                        – fail-closed ohne YAML-Werkzeug (Siegel neu signiert)
scripts/governance_contract.py                      – C33: Beweismarke + Siegelpflicht des Schreibers
scripts/integrity_guard.py                          – scripts/reserve_artifacts.py wieder unter Siegel
scripts/tests/test_artefakt_waechter.py             – 3 neue Regressionen (zwei Welten, ein Urteil)
.github/workflows/integrity-lock.yml                – PyYAML für den Wächter (wie in allen anderen Python-Jobs)
data/integrity_lock.json, data/integrity_history.jsonl – Siegel neu signiert (49 Dateien)
scripts/reserve_snapshot_heiler.py            (neu)  – Prüfen, Heilen, Belegen
scripts/tests/test_reserve_snapshot_heiler.py (neu)  – 10 Regressionen
scripts/bot_watchdog.py                              – eigene Befundklasse #661
scripts/git_sync.sh                                  – Konflikt-Diagnose + Reserve-Politik
scripts/tests/test_git_sync.py                       – 5 neue Regressionen
.github/workflows/bot-watchdog.yml                   – Reihenfolge: heilen → messen → dispatchen
.github/workflows/content-reserve.yml                – Stufe 0 Snapshot-Heilung, Reserve-Politik
package.json                                         – reserve:snapshot, test:reserve
BOT-WATCHDOG-661-DAUERHEILUNG-PREMIUM-2026-10-08.md  – dieser Bericht
```
