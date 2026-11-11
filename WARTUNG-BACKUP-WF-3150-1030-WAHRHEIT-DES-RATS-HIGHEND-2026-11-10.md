# Wartung · Sicherung · WF-3150 #1030 — die Wahrheit des Rats (10.11.2026)

**Auftrag:** `Wartung · Sicherung · Vorgang WF-3150 #1030 Bitte dauerhaft auf
Highend-Level einer Profi-Agentur beheben.`
**Branch:** `arena/a0880767-franksfinanzcheck-blog` · **Basis:** `90aa12b`
(`main`, 10.11.2026) · **Bearbeiter:** Arena Agent
**Vorgänger:** `WARTUNG-BACKUP-WF-3150-1030-SELBSTHEILUNG-HIGHEND-2026-11-07.md`

---

## 1 · Das Ergebnis in fünf Sätzen

Die Sicherung läuft weiterhin **nicht** — das ist und bleibt ein
Einrichtungsbefund des Inhabers (E1–E8), und ein Grün an dieser Stelle wäre
ein Betrug am eigenen RPO. Geheilt ist die **zweite** Hälfte: Die Wache hat
seit dem 07.11. gehandelt, aber sie hat **falsch geraten**. Am 09.11. trug ein
einziger Lauf zwei rote Schritte mit zwei verschiedenen Ratschlägen für eine
Ursache — und der zweite Rat war nachweislich falsch. Seit diesem Stand sagt
der Schritt, der es weiß, dem Schritt, der es braucht, was los ist; wer keine
Auskunft hat, antwortet **„nicht entscheidbar“** statt zu raten. Dazu fällt
ein zweiter, stiller Defekt: Der Heilungslauf konnte sich **selbst abwürgen**,
genau in den 15 Minuten, in denen er auf die angestoßene Sicherung wartet.

| Kennzahl | vorher | jetzt | Beleg |
|---|---|---|---|
| Ratschläge für eine Ursache | **zwei**, einer falsch | **einer** (die Ursache trägt ihn) | `offene_einrichtung` in `GITHUB_OUTPUT` |
| Antwort ohne Auskunft der Einrichtungsprüfung | geraten (Exit 0 oder 4) | **Exit 2, rot** | `betreibe_urteil(setup_geprueft=…)` |
| Abbruch mitten in der Heilung | jeder neue Push-Lauf | **nur Push-Läufe**, nie Tageslauf/„Run workflow“ | `cancel-in-progress: ${{ github.event_name == 'push' }}` |
| Selbstheilung als Vertrag geprüft | 21 Fallgruppen | **22** | `backup_selbstheilung.py --selftest` |
| Einrichtungsprüfung als Vertrag geprüft | 18 Fallgruppen | **19** | `backup_einrichtung.py --selftest` |
| Regressionstests der Kette | 98 | **114** (+16) | `test_backup_einrichtung`, `test_backup_selbstheilung` |

---

## 2 · Live-Befund (10.11.2026, gegen die echte GitHub-API)

| Prüfung | Ergebnis |
|---|---|
| Frischwache-Läufe | **16 rote** von 33 (8 `schedule`, 6 `push`, 2 `none`), jüngster `42715328453`, 09.11. 22:49 UTC, Dauer 15 s |
| Fehlgeschlagene Schritte dort | „Voraussetzungen prüfen“ **und** „Leerlauf prüfen“ — beide im selben Lauf |
| Offsite-Läufe | **11 geplante Läufe in Folge `failure`** (30.10.–10.11.), jüngster `42800942000`, 10.11. 10:39 UTC |
| Fehlgeschlagener Schritt dort | „Voraussetzungen prüfen“ (E1, E2, E3, E5, E6) — jeweils nach 8–9 Sekunden |
| Job „backup“ (Repo-Bundle) | **grün** — mit den Annotationen „Kein dauerhaftes Offsite-Ziel“, „Kein BACKUP_PASSPHRASE“ |
| Offene Einrichtung (Lauf-Annotationen) | **E1** `BACKUP_REPO`, **E2** `BACKUP_REPO_TOKEN`, **E3** `BACKUP_PASSPHRASE`, **E5** `CF_KV_BACKUP_TOKEN`, **E6** `KV_NAMESPACE_ID_ABO` |
| E4 `CLOUDFLARE_ACCOUNT_ID` | vorhanden (kein Fehlalarm) |
| E8 Environment `backup` | `protection_rules: []`, `deployment_branch_policy: null` → jeder Branch darf es nutzen |
| Ziel-Repo `frank-hartung/franksfinanzcheck-backup` | **HTTP 404** — existiert nicht |
| Agenten-Token: `PUT /environments/backup` | **403** `Resource not accessible by integration` (verlangt `administration: write`) |
| Agenten-Token: Secret-/Variablenlisten | **403** — nichts geprüft, nichts geraten, nichts gesetzt |

**Einordnung:** Kein Codefehler verhindert die Sicherung. Aber der **Rat**, den
der Betreiber liest, war falsch — und ein falscher Rat kostet genau die Zeit,
die der eine wirksame Schritt braucht. Dieselbe Klasse, die dieses Repo am
26.10.2026 bei der Sicherheits-Wache geheilt hat (WF-E813: „Ein Rat, der nie
zutreffen kann, ist keine Diagnose“).

---

## 3 · Die drei Defekte — reproduziert, nicht behauptet

### N-01 · Zwei Rote Stellen, zwei Ratschläge, eine Ursache

**Beleg (echte Annotationsliste, Lauf 42715328453):**

1. `failure` — „Die Offsite-Sicherung ist nicht eingerichtet (E1–E8 offen) …“
   (Schritt **„Voraussetzungen prüfen“**) — *richtig*.
2. `failure` — „Ein Lauf ist grün, gesichert wurde aber nichts (kein
   dauerhaftes Ziel bzw. keine Passphrase) …“ (Schritt **„Leerlauf prüfen“**)
   — *falsch*: Es war **kein** Lauf grün. Die Meldung setzt daraus ihren Text
   „Fehlgeschlagene Schritte (direkt aus dem Lauf)“ zusammen.

**Ursache im Code, exakt benannt:** `betreibe_urteil(…, einrichtung_offen=…)`
existiert seit dem 07.11. und hat einen klaren Kommentar, warum der Parameter
nötig ist. Der Workflow hat ihn **nie gefüllt**. Der Schritt las deshalb nur
die Job-Ebene und fand den jüngsten *grünen* `backup`-Job von Ende Oktober
(ohne Ziel, ohne Passphrase) — und meldete daraus einen Leerlauf, den es im
aktuellen Lauf gar nicht gab.

**Heilung — die Ursache reist mit:**

```
„Voraussetzungen prüfen“  →  GITHUB_OUTPUT: offene_einrichtung=E1 E2 E3 E5 E6
                                   │
„Leerlauf prüfen“  ────────────────┘  OFFENE_EINRICHTUNG=${{ steps.setup.outputs.offene_einrichtung }}
   ├─ Wert nicht leer  →  Hinweis „Ursache trägt der Schritt davor“, KEIN zweiter Rat
   ├─ Wert leer        →  echter Leerlauf-Befund (Exit 4) bleibt unverändert scharf
   └─ gar keine Auskunft → Exit 2, rot („weiß nicht“ ist kein Grün)
```

Die Ausgabe entsteht **auch bei Rot** — der Prüfer schreibt sie immer, und der
Workflow liest sie unabhängig vom Exit-Code. Genau der Fall, der zählt.

**Selbsttest S22 (neu, 6 Prüfungen):** `None` ≠ `[]` ≠ Liste; Trennzeichen
`,`/`;`/Leerzeichen; `E9` ist „unlesbar“ (kein Einrichtungspunkt); ohne
Auskunft wird die API **gar nicht** befragt; Gegenprobe, dass der echte
Leerlauf (Exit 4) und der Vorrang der Einrichtung (Exit 3) erhalten bleiben.

### N-02 · Der Heilungslauf konnte sich selbst abwürgen

**Befund:** `concurrency: cancel-in-progress: true` galt für **jeden** Lauf
dieses Workflows. Seit dem 07.11. ist der Lauf keine Messung mehr: Er stößt
`backup-offsite.yml` an und wartet bis zu **15 Minuten** (`WARTEZEIT_S = 900`)
auf das Ergebnis. Trifft in dieser Zeit ein weiterer Lauf derselben Gruppe ein
— und der `push`-Trigger feuert bei **jeder** Änderung an einem der sieben
Prüfer-Pfade —, wird der laufende Lauf abgebrochen, und zwar genau an der
Stelle, an der die Wache heilt. Abgebrochen wird nur der **Zeuge**; der
angestoßene Sicherungslauf läuft weiter (`backup-offsite.yml`:
`cancel-in-progress: false`). Ergebnis: Die Sicherung entsteht, der Nachweis
fehlt — und der nächste Lauf meldet wieder „kein frisches Release“.

**Heilung:** `cancel-in-progress: ${{ github.event_name == 'push' }}`.
Der **tägliche** Lauf und ein **manueller „Run workflow“** (eine Entscheidung
eines Menschen) laufen immer zu Ende; nur der Code-Probe-Push darf sich selbst
verdrängen. Vertraglich festgehalten in
`FrischwacheVertrag.test_kein_abbruch_mitten_im_heilungskreis`.

### N-03 · „Weiß nicht“ war ein Grün

**Befund:** Der Leerlauf-Schritt hatte für „die Einrichtungsprüfung lief nicht“
keine Antwort. Er lief dann in die Job-Messung und konnte mit Exit **0 (grün)**
oder **4 (Leerlauf-Rat)** enden — beides eine Behauptung über eine Lage, die er
nicht kannte. Dieselbe Klasse wie seinerzeit die Messung mit `2>&1`
(WARTUNG-BERICHT 07.11., N-03): *ein unlesbares Ergebnis ist kein Erfolg.*

**Heilung:** Drei Antworten statt zwei (`einrichtung_offen_aus_umgebung`):
`[]` = geprüft/nichts offen · `[E…]` = Ursache bekannt · `None` = weiß nicht
→ **Exit 2** mit dem Satz, warum. Lokal von Hand gibt es diese Auskunft nicht;
dafür sagt der Aufruf es ausdrücklich: `--ohne-setup`.

---

## 4 · Live-Proben, nicht nur Unit-Tests

Die geänderten Bash-Blöcke wurden **aus dem YAML extrahiert und ausgeführt** —
ein Test, der nur den Text prüft, hätte den `grep`/`GITHUB_OUTPUT`-Fehler
nicht gefunden:

```text
Einrichtungsschritt, Attrappe mit Exit 1 und offene_einrichtung=E1 E2 E3 E5 E6
  → ::error::… (E1–E8 offen: E1 E2 E3 E5 E6) …   Exit 1 ✔

Leerlauf-Schritt, OFFENE_EINRICHTUNG="E1 E2 E3 E5 E6", Prüfer-Exit 4
  → ::notice … „kein zweiter Rat“                  Exit 0 ✔   (vorher: Exit 1, falscher Rat)
Leerlauf-Schritt, OFFENE_EINRICHTUNG="",             Prüfer-Exit 4
  → ::error title=Backup-Leerlauf::…               Exit 1 ✔   (echter Befund bleibt)
Leerlauf-Schritt, OFFENE_EINRICHTUNG="",             Prüfer-Exit 0
  → (kein Befund)                                  Exit 0 ✔
Leerlauf-Schritt, OFFENE_EINRICHTUNG="",             Prüfer-Exit 2
  → ::error::… nicht entscheiden …                 Exit 1 ✔
```

**Gegen die echte API** (`gh` als Inhaber, Quell-Repo real):

```text
backup_selbstheilung.py --leerlauf   (Ursache bekannt, wie im Workflow)
  Ursache zuerst: Die Einrichtung ist offen (E1, E2, E3, E5, E6) …
  ⚠️ [leerlauf] Job „backup“ ist grün, gesichert wurde aber nichts (…)   ← der ALTE Befund, benannt
  Einrichtung offen (E1, E2, E3, E5, E6) – das ist der Inhaber-Weg …      Exit 3 (Vorrang)

backup_selbstheilung.py --leerlauf   (ohne Auskunft — der Zustand bis heute)
  Die Einrichtungsprüfung dieses Laufs hat ihr Ergebnis nicht hinterlassen …
                                                                          Exit 2 (vorher: 4)
```

---

## 5 · Nachweise (lokal gefahren, alle grün)

```text
python3 scripts/backup_einrichtung.py --selftest        → ✅ 19 Fallgruppen (inkl. F19)
python3 scripts/backup_selbstheilung.py --selftest      → ✅ 22 Fallgruppen (inkl. S22)
python3 scripts/backup_selbstheilung.py --vertrag       → ✅ Vertrag eingehalten
python3 scripts/backup_freshness_guard.py --selftest    → ✅ 15 Fallgruppen
python3 -m unittest scripts.tests.test_backup_einrichtung \
                     scripts.tests.test_backup_selbstheilung \
                     scripts.tests.test_alert_scoping    → Ran 146 tests … OK
python3 scripts/selftest_clock.py --trap  … --offset 97 → ✅ (keine Zeitbombe)
python3 scripts/selftest_clock.py --trap-modul … --offset 97 → ✅
python3 scripts/skript_syntax_wache.py --check           → ✅ 689 Dateien
python3 scripts/workflow_js_wache.py --check             → ✅ alle github-script-Blöcke
python3 scripts/workflow_vertrag_wache.py --gate         → ✅ 102 Workflows, V1–V7
python3 scripts/governance_contract.py --quick            → ✅ 47 Regeln
python3 scripts/automation_premium_audit.py --strict      → ✅ Pins, Timeouts, Permissions, Concurrency
```

---

## 6 · Was diese Sitzung NICHT heilt (und nicht heilen darf)

Die fünf offenen Punkte sind Zugangsdaten und Ziel-Entscheidungen des
Inhabers. Belegt am 10.11.2026: Der Agenten-Token erhält auf
`PUT /environments/backup` **403 `Resource not accessible by integration`**
(verlangt `administration: write`), Secret- und Variablenlisten sind ebenfalls
403. Es wurde **nichts** gesetzt, nichts geraten, nichts abgeschaltet.

| Punkt | Was fehlt | Wo es erledigt wird |
|---|---|---|
| E8 | Environment `backup` ohne Branch-Regel | Settings → Environments → `backup` → „Selected branches“ = `main`, keine Required Reviewer |
| E1 | Variable `BACKUP_REPO` | privates Ziel-Repo anlegen, Namen als Repository-Variable |
| E3 | Secret `BACKUP_PASSPHRASE` | Environment `backup`, 32+ Zeichen, **vorher** in den Passwort-Manager |
| E2 | Secret `BACKUP_REPO_TOKEN` | fine-grained PAT, **nur** das Ziel-Repo, Contents: Read and write |
| E5 | Secret `CF_KV_BACKUP_TOKEN` | Cloudflare-Token, nur „Workers KV Storage: Read“ |
| E6 | Variable `KV_NAMESPACE_ID_ABO` | 32-Hex-ID des Namespace `ABO` |

Werkzeug: `npm run backup:einrichten` (interaktiv, verdeckte Eingabe) bzw.
`npm run backup:status` (nur prüfen) — **Stand heute lokal geprüft:** 3 offen,
4 nicht bestätigt (fehlendes Leserecht), nichts als „eingerichtet“ behauptet.
Anleitung: `docs/ANLEITUNG-OFFSITE-BACKUP.md`, Abschnitt „Kurz: Was ist zu tun?“.

**Warum #1030 offen bleibt:** Es ist die Wahrheit über den Betrieb. Ein Issue,
das geschlossen wird, weil der Code hübscher geworden ist, wäre derselbe
Schein wie ein grüner Lauf ohne Sicherung. Der Vorgang schließt sich von
selbst, sobald die Kette grün ist — durch den Resolve-Gate-Pfad des Alertings
(Job-Beweis), nicht durch einen Handgriff.

---

## 6b · Drei Merge-Blocker, die nicht aus diesem Auftrag stammen

Der Pull Request #1171 war nach der Backup-Heilung **noch rot** – nicht wegen
der Sicherung, sondern wegen drei Wachen, die auf `main` schon rot standen
(nachgeprüft in einem eigenen Worktree auf `origin/main`, gleiche Fehlbilder):

| Wache | Befund | Ursache | Heilung |
|---|---|---|---|
| `blustradius_register --selftest` | „Schritt 30 ‚GSC-Leistungsdaten – Artefaktprüfung (fail-closed)‘ steht in keinem Register“ | `deploy.yml` bekam den Schritt am 10.11. mit **#1162**, das Register `data/blustradius-deploy.yml` keinen Eintrag (C38: jeder Schritt des Auslieferungswegs erklärt seinen Blustradius) | Eintrag **`infra`** – geprüft wird nicht Inhalt, sondern das Messartefakt (G1–G4) |
| `reserve_finisher --selftest` | „Gate-Regel ohne Heiler: `kurzantwort_failures`“ | **#1110** machte die Kurzantwort zu einer ablehnenden Gate-Regel, ohne Deckungseintrag. Der Finisher verweigert seitdem **vor** jeder Arbeit die Kette – der Reserve-Lauf kann nichts veredeln | **begründete Ausnahme**, kein Heiler: Ein Heiler im Veredelungslauf müsste die Kurzantwort *erfinden*. Die zwei echten Schreiber sind benannt (`pflichtfeld_verlust_wache --fix` aus HEAD, `generate_kurzantworten.py` mit YMYL-Sperre) |
| `selftest_runner` (Hinweis) | „`ki_provenienz.py` erwähnt `--selftest` … ein Aufruf startet die Standard-Aktion“ | Die Datei ist eine **Bibliothek**: ihr `__main__`-Zweig endet mit `raise SystemExit`. Die behauptete Folge gibt es nicht | `verweigert_direktaufruf()` misst die Folge, statt sie zu behaupten („Folge: keine“); Gegenprobe im Runner-Selbsttest in beide Richtungen |

**Warum das dazugehört:** Ein Gate, das wegen eines fehlenden Registereintrags
*jeden* Pull Request blockiert, ist derselbe Schaden wie ein falscher Rat – es
lenkt vom echten Befund ab. Und ein Hinweis, der eine Gefahr behauptet, die es
nicht gibt, kostet beim nächsten echten Fall die Aufmerksamkeit.

Zusätzlich war der Arbeitsbaum mit **kaputten Merge-Artefakten** belastet
(`data/gsc/abdeckung/befund.json` und `prioritaet.json`: ein Gabelrest mitten
im Objekt, danach alle Felder ein zweites Mal – `json.loads` scheiterte in
Zeile 651 bzw. 101, `test_gsc_abdeckung` ebenso). Geheilt mit den **Erzeugern**
(`gsc_abdeckung.py --schreiben` / `--prioritaet`), nicht per Editor; die
A2-Dubletten über `artefakt_waechter.py --heal`. Der Datenstand bleibt dabei
sichtbar: Der Export ist vom 19.10. und damit 22 Tage alt – er glänzt nicht.

**Gesamtlauf danach:** `selftest_runner` **283 Wachen, 566 Uhr-Proben, kein
Befund** (mit vollständiger Prüfgrundlage aus `requirements-ci.txt`; ohne
PyYAML/Pillow schlagen Wachen bewusst fail-closed fehl – das ist #1001, kein
Wachen-Defekt). `governance_contract --quick` ✅ 47 Regeln.

---

## 7 · Geänderte Dateien

| Datei | Änderung |
|---|---|
| `scripts/backup_einrichtung.py` | offene Kennungen als Schritt-Ausgabe (`offene_einrichtung`), Funktion `offene_kennungen`; Selbsttest **F19** (auch bei Rot geschrieben, Reihenfolge E1–E6, keine Werte) |
| `scripts/backup_selbstheilung.py` | `einrichtung_offen_aus_umgebung` (drei Antworten), `betreibe_urteil(setup_geprueft=…)` → Exit 2 statt Raten, `--ohne-setup`, Selbsttest **S22** |
| `.github/workflows/backup-frischwache.yml` | Schritt `id: setup` gibt den Befund weiter; Leerlauf-Schritt liest ihn (Ursache vor Messung); `cancel-in-progress` nur für Push |
| `scripts/tests/test_backup_einrichtung.py` | `test_einrichtungsbefund_geht_an_den_leerlauf_schritt`, `test_kein_abbruch_mitten_im_heilungskreis` |
| `scripts/tests/test_backup_selbstheilung.py` | `AuskunftsVertrag` (3 Tests in beide Richtungen) |
| `docs/ANLEITUNG-OFFSITE-BACKUP.md` | Abschnitt „Eine Ursache, ein Rat – und kein Abbruch mitten in der Heilung“; Fallzahlen nachgezogen |
| `data/blustradius-deploy.yml` | Registereintrag `infra` für „GSC-Leistungsdaten – Artefaktprüfung (fail-closed)“ (C38, Befund aus #1162) |
| `scripts/reserve_healer_coverage.py` | begründete Ausnahme `kurzantwort_failures` (Befund aus #1110) – kein Heiler, weil die Kurzantwort Inhalt ist |
| `scripts/selftest_runner.py` | `verweigert_direktaufruf()`: der Hinweis zu einer Bibliothek behauptet keine Standard-Aktion mehr; Selbsttest mit Gegenprobe |
| `data/gsc/abdeckung/befund.json`, `befund.md`, `prioritaet.json`, `ursachen.json`, `verlinkungsheilung.json` | Merge-Artefakte mit den Erzeugern geheilt (A1/A2) |

---

## 7b · Ein fremder Blocker, der offen bleibt (und offen bleiben muss)

Der Merge mit `main` (Stand `b56e915`, 11.11.) ist konfliktfrei – aber der
Regressionslauf bleibt rot, und zwar **nicht** an dieser Arbeit. `main` selbst
ist seit Stunden rot, mit demselben Bild wie mein Zweig:

| Prüfung | Ergebnis |
|---|---|
| `scripts/tests/test_faktenfrische_1072.py` auf **`origin/main`** (eigener Worktree) | **9 Failures** — 5 Befunde × (Anker + Beleg) |
| derselbe Test auf meiner Branch (gemergt) | identisch 9 Failures, **gleiche** Befund-IDs |
| Artikel-Datei | bytegleich mit `main` (`sha256 d2e6413d…`) |
| Register `data/faktenfrische_befunde_1072.yaml` | bytegleich mit `main` |

**Ursache, belegt am Commit-Baum:** `dcbd416` („fix(content): Quellenkette
Waschmaschinen-Artikel (WF-7B6B #1148)“, PR **#1163**) hat den Artikel
`2026-11-05-waschmaschine-beladen-weniger-kosten-bei-jedem-waschgang`
**neu geschrieben** — Quellen ersetzt, Kurzantwort gekürzt, Abschnitte
gestrichen. Das #1072-Register und die 47 Entscheidungen wurden **nicht**
mitgezogen. Damit gilt:

- die fünf Anker („kann die Lager der Maschine beschädigen“, „je nach Gerät
  und Häufigkeit“, „kann die Fixkosten senken“, „Modellbeispiel“,
  „im Modelljahr rund 5 €“, „Beispielwerte“) stehen **nicht mehr** im Text;
- die Beleg-URL der fünf Befunde (Bundesnetzagentur-Startseite) steht
  **nicht** in den neuen Artikelquellen — sie stand dort auch vorher nie,
  sie war der Beleg der *Redaktionsprüfung*, nicht eine Artikelquelle.

**Warum ich das nicht selbst „repariere“:** Ein neuer Anker und eine neue
Beleg-URL wären eine **menschliche Fachfreigabe** (YMYL) — genau der Vorgang,
den dieses Repo mit #1072/#1127 installiert hat und den `C15` („Beweisen ist
nicht Heilen“) verbietet. Ein Agent, der die Prüffassung fortschreibt, weil
sie nicht mehr passt, hebt die Prüfung auf. Ich habe deshalb **nichts** an
`faktenfrische_befunde_1072.yaml`, `faktenfrische_entscheidungen.yaml` oder
dem Artikel geändert.

**Was der Befund zusätzlich zeigt (Werkzeug-Lücke, nicht repariert):**
`test_faktenfrische_1072` läuft **in keinem Pull-Request-Gate**
(`bestand-regression-wache.yml` und `deploy.yml` rufen nur die
996er-Datei). Aufgefallen ist der Schaden erst in der vollen
`unittest discover`-Suite des `regression`-Jobs — nach dem Merge von #1163.
Ein Test, der erst nach dem Merge läuft, hält keinen Merge auf.

**Was zu tun ist (Inhaber/Redaktion):** Die fünf Befunde am **heutigen**
Text neu entscheiden (`python3 scripts/faktenfrische_befund_ledger.py
--entscheiden <id> --von … --begruendung …`) oder das Register auf die
#1163-Fassung umbinden — die Werkzeuge dafür liegen bereit
(`faktenfrische_befund_akte.py`, `--struktur-pruefen`). Der Ledger selbst
meldet für diesen Artikel korrekt `ueberholt`.

---

## 7c · Der zweite fremde Blocker: zwei Seiten ohne Belegkette

`Playwright-Suite` scheiterte im Schritt „Metadaten-Wache – Quelle“. Gemessen
auf **`origin/main`** (eigener Worktree, gleiches Werkzeug):

```
[M4] content/posts/2026-11-01-flugverspaetung-entschaedigung-…: Keine Quelle im Frontmatter (quellen)
[M4] content/posts/2026-11-10-wlan-frust-loesen-…:           Keine Quelle im Frontmatter (quellen)
```

Beides sind die beiden Seiten, die ich im Schritt davor über den
**Verlinkungsauftrag** angeschlossen habe — der Schritt hat den Befund
**aufgedeckt, nicht erzeugt**: Beide Dateien tragen `quellen:` schon auf
`main` nicht (`grep -c '^quellen:'` → **0/0**).

**Warum ich keine Quellen erfinde:** `metadaten_wache.py` führt M4 in der
Liste „Nicht heilbar bleibt gemeldet: M1, M4, M5, M6 …“. Der Grund steht im
Kopf der Wache und in der Akte zu #1110: Eine Quelle ist eine Recherche- und
Freigabeentscheidung (YMYL). Ein Agent, der eine plausible URL einsetzt,
erzeugt einen Beleg, der nichts belegt — die teuerste Art von Grün.

**Was passiert ist, dass es nicht wieder still bleibt:** Der Befund steht hier,
im PR und im Ledger. Die Redaktion trägt die Quellen nach
(`belegketten_wache.py --strict` prüft danach, ob die Zitate noch die
zitierten sind).

---

## 8 · Restrisiken, bewusst benannt

| Risiko | Wirkung | Gegenmaßnahme |
|---|---|---|
| Ein künftiger Schritt gibt eine falsch formatierte Ausgabe weiter | Leerlauf-Prüfung endet mit Exit 2 | fail-closed, nicht fail-open; F19 prüft das Format an der Quelle |
| Ein Push-Lauf verdrängt einen Tageslauf | nur möglich, wenn der Tageslauf **noch nicht** läuft (Gruppen-Regel von GitHub) | der Verdrängte ist dann ein Wartender ohne einen einzigen Schritt — kein Nachweis geht verloren |
| Einrichtungsprüfung wird künftig umbenannt | Ausgabe fehlt → Exit 2 | Test hält den Schrittnamen und die `id` fest |
| Owner erledigt E1–E8 | Sicherung läuft, Wache wird grün, Issue schließt sich | unverändert: kein Handbefehl nötig (Selbstheilung vom 07.11.) |

— *Ende der Akte. Nichts an dieser Änderung schaltet einen Schutz ab; nichts
davon behauptet eine Sicherung, die nicht existiert. Geheilt ist der Rat.*
