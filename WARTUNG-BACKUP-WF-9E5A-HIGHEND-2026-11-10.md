# Wartung · Sicherung · WF-9E5A #923 — Highend-Dauerheilung (10.11.2026)

**Auftrag:** `Wartung · Sicherung · Vorgang WF-9E5A #923 — dauerhaft auf Highend-Level einer Profi-Agentur beheben, mit automatischer Selbstheilung.`
**Branch:** `arena/16a61312-franksfinanzcheck-blog` · **Basis:** `90aa12b` (`main`, 10.11.2026)
**Bearbeiter:** Arena Agent · **Vorgänger:** `WARTUNG-BACKUP-WF-9E5A-HIGHEND-2026-11-07.md`

---

## 0. Die eine Lehre dieses Tages

Am 07.11. habe ich an der falschen **Höhe** gemessen. Heute habe ich viermal an
der richtigen Höhe gemessen — und dabei viermal gefunden, dass zwei Werkzeuge
**dieselbe Lage verschieden beurteilen**:

| # | Werkzeug A sagt | Werkzeug B sagt | Wahrheit |
|---|---|---|---|
| A | „E1 fehlt" | E1 ist **vorhanden**, nur nicht lesbar | Es fehlt nichts. Die Leserechte fehlen. |
| B | `leerlauf` (Exit 4) | `scheinbeweis` (Exit 1) | Eine Quelle war blind. |
| C | „Inhaber-Schritt" (Exit 3) | **grüner Job** | Der Wächter kannte den Code nicht und schwieg. |
| D | „du musst nichts mehr anstoßen" | Messung `skipped`, Heilung `skipped` | Die Zusage war **falsch**. |

Das Muster ist dasselbe wie am 07.11., nur eine Ebene höher: **Nicht die
Messung war falsch, sondern die Zahl der Messungen.** Ein Zustand, den nur ein
Auge sieht, ist kein Zustand — er ist eine Meinung. Wo zwei Werkzeuge dieselbe
Sache beurteilen, müssen sie **dieselbe Wahrheit** sehen, und der Unterschied
zwischen „fehlt" und „nicht prüfbar" muss ein eigener Zustand sein, nicht ein
Sonderfall des ersten.

Drei der vier Fehler waren dabei **grün**: Der Job war grün (C), der Test war
grün (A/B unbewacht), der Rat war überzeugend formuliert (D). Ein Fehler, der
grün ist, wird nicht gefunden — er wird gefunden, wenn man die Gegenprobe
baut. Das ist der Grund, warum unten zu jedem Fix eine Sabotage steht.

---

## 1. Live-Befund (10.11.2026, echte GitHub-API)

| Prüfung | Ergebnis |
|---|---|
| Offsite-Lauf `42800942000` (jüngster) | Job `KV-/D1-Backup` **failure** in Schritt 4 („Voraussetzungen prüfen") |
| Frischwache-Lauf `42715328453` (jüngster) | `Voraussetzungen prüfen` **failure** → `Frische messen` **skipped** → `Selbstheilung` **skipped** → `Urteil` **skipped** |
| Einrichtungsprüfung (live, dieser Branch) | E1, E2, E3, E4, E5, E6, E8 **nicht prüfbar** – Recht `administration` fehlt dem Agenten |
| Schreib-Endpunkte (Variable/Secret/Environment) | `403 Resource not accessible by integration` – nichts erfunden, nichts gesetzt |
| Ziel-Repository `frank-hartung/franksfinanzcheck-backup` | **404** – existiert nicht |

**Die Inhaber-Einrichtung (E1–E8) bleibt der einzige funktionale Blocker.**
Das ist unverändert seit dem 22.10. und wird hier nicht als Fortschritt
verbucht. Was sich geändert hat, ist die **Ehrlichkeit der Anzeige**: Alle vier
Defekte dieses Tages betrafen Stellen, an denen die Anzeige etwas anderes sagte
als die Lage.

---

## 2. Die vier Heilungen

### A · Der Wizard meldete „fehlt", wo „nicht lesbar" stand

**Befund.** `backup_einrichten_wizard.sh` las Variablen mit
`gh variable get`. Diesen Unterbefehl gibt es in **gh 2.23.0** nicht. Folge:
Die Antwort war immer leer, und E1/E6 wurden als **„fehlt"** gemeldet —
obwohl sie gesetzt sein können und nur das Leserecht fehlt. Ein Inhaber, der
diesem Rat folgt, legt eine Variable neu an, die längst existiert.

**Beleg (echt, gh-Attrappe):** Vorher `❌ E1 Repository-Variable BACKUP_REPO fehlt`,
nachher `❓ E1 BACKUP_REPO – Variable nicht lesbar (Variable-API gesperrt) – Anwesenheit NICHT bestätigt`.

**Heilung.** `variable_lesen` liefert jetzt **drei** Zustände statt zwei:

| Rückgabe | Bedeutung | Erkennung |
|---|---|---|
| `0` | Wert gelesen | JSON mit `value` |
| `1` | **fehlt** | `"status": *"404"` in der Antwort |
| `2` | **nicht prüfbar** | alles andere (403, Netz, leer) |

Nur `1` erzeugt „fehlt". `2` erzeugt ausdrücklich „NICHT bestätigt" — und der
Abschluss „Alle Pflichtpunkte sind eingerichtet" ist nur bei `0`/`1` erreichbar.
Der Aufruf läuft über `gh api "repos/$QUELLE/actions/variables/…"`, also über
einen Endpunkt, den gh 2.23.0 wirklich kennt.

---

### B · Die Selbstheilung maß eine Höhe, urteilte über zwei

**Befund.** `betreibe_urteil` las **nur** die Läufe von `backup-offsite.yml`.
Der Zustand der Frischwache — der Wache, die den Rat ausgibt — blieb blind.
Reproduziert mit einer Quelle je Workflow: Offsite meldete `['leerlauf']`
(Exit 4), die Frischwache `['scheinbeweis']` (Exit 1). Zwei Wächter, zwei
Urteile über denselben Tag.

**Heilung.** `URTEIL_QUELLEN = ("backup-offsite.yml", "backup-frischwache.yml")`.
`betreibe_urteil` misst **beide** Höhen und gibt die benutzten Quellen als
`quellen` zurück; `--workflow ""` heißt jetzt „beide", ein explizit genannter
Workflow bleibt die bewusste Einäugigkeit (Selbsttest S22d hält genau diesen
Unterschied fest). Die Job-Zusammenfassung nennt die Messhöhe in einer Zeile
„Gemessen: …" — damit ist am Ausgabetext ablesbar, worauf das Urteil steht.

---

### C · Exit 3 fiel in `exit 0` — der Schritt war grün, während das Skript rot war

**Befund.** `backup_selbstheilung.py` kennt seit dem 07.11. den Code **3**
(„Einrichtung offen, Inhaber-Schritt"). Der Workflow prüfte `1`, `2`, `4` —
und fiel für alles andere in `exit 0`. **Exit 3 wurde damit grün.** Der eine
Code, der sagt „hier ist nichts zu heilen, das musst du tun", war der einzige,
der nicht ankam. Ein Wächter, der nur die Codes kennt, die er erwartet, ist bei
allem anderen blind — und „alles andere" ist genau das Neue.

**Heilung.** `case "$RC" in` mit **jedem** Code als eigener Antwort, `0` als
einziger Ausgang nach grün, `*)` als Rot. Der Vorrang ist jetzt explizit:
**3 vor 4 vor 1.** Die Einrichtungsprüfung hinterlegt ihren Befund als
**Ausgabe** (`id: einrichtung`, `offen=E1,E2`); der Leerlauf-Schritt bekommt ihn
über `EINRICHTUNG_OFFEN` **übergeben statt geraten**. Ist die Prüfung selbst
nicht lesbar, bleibt es beim allgemeinen Rat — kein Vorrang, den niemand
gemessen hat. Der Alert kennt dafür die eigene Klasse `backup-einrichtung` mit
eigenem Titel `Backup-Einrichtung offen`.

---

### D · Der Rat versprach eine Automatik, die im beschriebenen Zustand nicht läuft

**Befund.** Der Einrichtungs-Rat sagte in Nummer 3:

> „Danach **musst du nichts mehr anstoßen** (seit 07.11.2026): Der nächste Lauf
> der ‚Backup-Frischwache' sieht, dass noch keine Sicherung existiert, stößt
> ‚Offsite-Backup' selbst an und misst erneut."

Das ist im Zustand **dieses** Rats nachweislich falsch. Solange
„Voraussetzungen prüfen" rot ist, überspringt GitHub mit `success()` den
Schritt „Frische messen" — und damit auch „Selbstheilung" und „Urteil". Belegt
am jüngsten Lauf `42715328453`: failure → skipped → skipped → skipped. Die
Selbstheilung kam nie zum Zug; der einzige wirksame Weg war der **Handbefehl**,
den der Rat als Fußnote führte.

Das ist die teuerste Sorte Fehler: kein Absturz, keine rote Stelle — ein
überzeugend formulierter Satz, der die eine wirksame Handlung zur Nebensache
macht und den Inhaber warten lässt.

**Heilung.** Nummer 3 benennt die Lage:

> „**Die Selbstheilung kommt hier NICHT zum Zug** – … Solange dieser Schritt rot
> ist, wird die Messung und damit der Selbstheilungsschritt übersprungen
> (GitHubs `success()`). Der einzige wirksame Weg ist der Handbefehl, sobald
> E1–E8 stehen: Actions → ‚Offsite-Backup' → ‚Run workflow'. Erst danach greift
> die Automatik wieder … Der erste grüne Lauf schließt diese Meldung
> automatisch."

Der Satz „schließt diese Meldung automatisch" bleibt — er ist **wahr** (das
Alerting schließt bei grünem `main`-Lauf) und wird von einem eigenen Szenario
geprüft. Falsch war nur die Behauptung, es gehe von selbst.

**Der eigentliche Fix ist der Wächter.** Diese Zusage war **unbewacht** — kein
Test hätte sie je gefunden (Grep über `scripts/tests/` und die Workflows: kein
Treffer). Das Szenario `#761-Nachführung` fordert jetzt
`'kommt hier NICHT zum Zug'` und `'Run workflow'` **und** verbietet
`'musst du nichts mehr anstoßen'` sowie `'stößt „Offsite-Backup“ selbst an'`.
Damit ist die Rückkehr der Falschzusage ein roter Test, nicht eine Stilfrage.

---

## 3. Regressionsschutz — beide Richtungen, mit Sabotageproben

| Sabotage | Ergebnis |
|---|---|
| `variable_lesen` zurück auf `gh variable get` | ❌ 2 Fehlschläge („404 muss als 'fehlt' gelesen werden", kein `gh variable get` im Code) |
| 403 wieder als „fehlt" behandeln | ❌ 1 Fehlschlag („nicht prüfbar" statt „fehlt") |
| `betreibe_urteil` wieder einäugig | ❌ S22a/b/c, 3 Abweichungen, Exit 0 statt 1 |
| Workflow: `3) exit 0` | ❌ Workflow-Vertrag FAILED |
| Falschzusage „musst du nichts mehr anstoßen" zurück | ❌ Simulation: 4 Gründe, u. a. verbotene Nadel im Body |
| **Gegenrichtung:** neue Formulierung entfernt | ❌ erwartete Nadel fehlt |

**Zwei Sabotagen liefen zuerst ins Leere** — bei der ersten Fassung der
D-Formulierung fehlte der Link `actions/workflows/backup-frischwache.yml`, den
ein bestehendes Szenario verlangt; die Simulation wurde rot, obwohl der Text
inhaltlich richtig war. Ein grüner Sabotage-Lauf ist kein Beweis, sondern ein
Verdacht — hier war es ein berechtigter Einwand des Bestandstests, und die
Formulierung wurde so geändert, dass sie den Link **wahr** enthält („Erst
danach greift die Automatik wieder"). Beide Richtungen sind jetzt belegt.

---

## 4. Abnahme (alle Befehle in diesem Stand ausgeführt)

| Prüfung | Ergebnis |
|---|---|
| `unittest` `test_backup_einrichtung` + `test_backup_selbstheilung` + `test_alert_scoping` | ✅ **143 Tests, 0 Fehlschläge** |
| davon `test_backup_einrichtung.py` | ✅ **111 Tests** (davon **2** neue: `WizardVariablenVertrag`) |
| davon `test_alert_scoping.py` | ✅ **32 Tests**, Simulation **80 Szenarien** |
| `backup_selbstheilung.py --selftest` | ✅ **22 Fallgruppen** |
| `backup_einrichtung.py --selftest` | ✅ **18 Fallgruppen** |
| `backup_selbstheilung.py --vertrag` | ✅ |
| `backup-frischwache.yml` | ✅ YAML lesbar, **9 Schritte**, `id: einrichtung`, `EINRICHTUNG_OFFEN` verdrahtet, `case 0/1/2/3/4/*` |
| `alert-on-failure.yml` | ✅ YAML lesbar, Runbook-Klasse `backup-einrichtung` unverändert erreichbar |
| `bash -n backup_einrichten_wizard.sh` | ✅ |
| `ast.parse` beider Python-Dateien | ✅ |
| `trigger_wache.py --check` | ✅ **102 Workflows, 0 Befunde** |
| `trigger_wache.py --selftest` | ✅ (Parser, W1–W3, Fließform-Sperre) |
| `skript_syntax_wache.py` | ✅ **689 Dateien** |
| `wachen_vertrag.py` | ✅ **395 Skripte, 0 Funde** |

**Geänderte Dateien (7):**

```
.github/workflows/alert-on-failure.yml    |  13 ++-
.github/workflows/backup-frischwache.yml  |  69 ++++++---
scripts/backup_einrichten_wizard.sh       |  92 ++++++++---
scripts/backup_einrichtung.py             |  34 +++-
scripts/backup_selbstheilung.py           | 169 ++++++++++++++++--
scripts/tests/sim/alert_scoping_sim.mjs   |  12 ++-
scripts/tests/test_backup_einrichtung.py  | 101 +++++++++++++-
```

**Zwei Bestandstests wurden bewusst auf die strengere Form gezogen**
(nicht „Absicht geändert", sondern die Festschreibung der alten Textform):
der Einrichtungs-Regex von `--pruefen` auf `--pruefen(?: --ausgabe \S+)?` und
der Leerlauf-Block von `if [ "$RC" = … ]` auf `case`-Zweige mit je einer
eigenen Antwort pro Exit-Code. Beide prüfen jetzt **mehr** als vorher.

---

## 5. Was der Inhaber tun muss (unverändert)

```bash
npm run backup:einrichten     # E8 zuerst, dann E1–E7; Geheimnisse verdeckt
npm run backup:status         # Stand prüfen, ohne etwas zu ändern
npm run backup:heilung        # was das System selbst reparieren darf
```

Danach Actions → „Offsite-Backup" → „Run workflow" (`main`), dann
`npm run backup:probe`.

**Abnahmekriterien für #923:** (1) grüner `KV-/D1-Backup`-Job auf `main`,
(2) privates Entwurfs-Release `kv-backup-*` mit Größen-/Draft-Nachweis,
(3) bestandener Restore-Drill, (4) grüne Frischwache (beide Wachen sehen
dieselbe Wahrheit), (5) kein grüner `backup`-Job ohne dauerhaftes Offsite-Ziel.

**Diese fünf Punkte kann nur der Inhaber abschließen.** Kein Punkt dieses
Berichts behauptet, dass Sicherung funktioniert — nur, dass die Anzeige jetzt
nicht mehr lügt, wenn sie es nicht tut.

---

## 6. Bewusste Grenzen

* **Der Agent kann E1–E8 nicht lesen und nicht setzen** (`403`, Environment-Schutz
  erfordert `administration`). Das ist Absicht und bleibt so.
* **Der Wizard-Test prüft die Attrappe, nicht die echte API** — geprüft ist das
  Verhalten bei 404/403, nicht das Live-Recht.
* **Der Vorrang 3 > 4 ist eine Vereinbarung, keine Messung im Zweifel**: Wenn
  die Einrichtungsprüfung selbst scheitert, wird bewusst **kein** Vorrang
  behauptet.
* **`casing_guard.py` meldet 5 Fundstellen** in
  `content/posts/2026-11-04-guenstigen-mietwagen-fuer-den-urlaub-buchen/index.md`.
  Altbestand aus `90aa12b`, nicht Teil dieses Vorgangs, nicht angefasst.

---

## 7. Offen für den nächsten Lauf

1. **Vorgang #1107 (Frist 20.11.2026)** — eigenständig, **nicht** Teil dieses PR.
   PR #1172 („eingefrorene Gegenprobe ist laut") ist rot und **nicht auf `main`**:
   `projektions_modus` = 0 auf `main`, 8 im PR-Zweig; Bericht
   `KADENZ-HORIZONT-1107-DAUERHEILUNG-HIGHEND-2026-11-10.md` existiert nur im
   PR-Zweig. Die heutige Messung ist grün (126 Seiten, 0 fällig/0 überfällig,
   Deckung 162 %, Weg frei bis 2027-03-10) — die Heilung, auf die sie sich
   beruft, liegt aber nicht auf `main`. Bleibt offen bis PR #1172 grün und
   gemerged ist.
2. **E1–E8 beim Inhaber** — der funktionale Blocker, unverändert.
3. **Exit-Codes des Wizards** (`rc=1` bei `--check`, `rc=4` bei Leerlauf) sind
   jetzt korrekt als „nicht prüfbar" bzw. „Einrichtung offen" klassifiziert;
   ein automatisierter Lauf im CI ist weiterhin nicht verdrahtet.

---

## 8. Nachtrag 10.11.2026, 19:20 UTC — was während dieser Arbeit passierte

Drei Dinge haben sich geändert, **während** dieser Vorgang lief. Sie stehen
hier, weil sie den Vorgang berühren, nicht weil sie zu ihm gehören.

### 8.1 `main` war für jeden Pull-Request gesperrt — vier kaputte Artefakte

Beim Abarbeiten der CI-Checks fiel auf: `Integritäts-Siegel` und `ReDoS-Wache`
waren auf **jedem** Pull-Request rot — auch auf PR #1161, der mit dieser Arbeit
nichts zu tun hat. Ursache war nicht der Code, sondern `main` selbst:

| Datei | Befund |
|---|---|
| `data/gsc/abdeckung/befund.json` | Zeile 651: fehlendes Komma, ein kompletter Datensatz in einen anderen gespleißt |
| `data/gsc/abdeckung/prioritaet.json` | Zeile 101: dasselbe Muster |
| `data/gsc/abdeckung/ursachen.json` | doppelter Schlüssel `erzeugt` |
| `data/gsc/abdeckung/verlinkungsheilung.json` | doppelte Schlüssel `stand`/`status` |

Die letzten beiden sind **gültiges** JSON — `json.load` nimmt still den letzten
Wert. Genau deshalb hat sie niemand gesehen; der Artefakt-Wächter prüft seit
#653 auch auf doppelte Schlüssel (A2).

**Heilung:** mit dem Erzeuger neu geschrieben (`gsc_abdeckung.py --schreiben`
bzw. `--prioritaet`), nicht von Hand kommentiert. Seine Schreibfunktion ist
atomar (`tmp` + `replace`) und benutzt `json.dumps` — sie kann keine
Syntaxfehler erzeugen. Einen gespleißten Datensatz von Hand zu rekonstruieren
wäre geraten, nicht belegt.

Nach der Heilung: **627 Artefakte strukturell heil**, `Integritäts-Siegel` und
`ReDoS-Wache` **grün**.

### 8.2 `gate` ist rot — und der Grund hat einen Namen

`gate` scheitert an drei Selbsttests (`reserve_finisher`, `governance_contract`,
`blustradius_register`). Die Ursache ist **nicht der Code**:

```
🛑 Wirkungsprobe: Vertrag verletzt: YMYL: Schreibprüfung nicht auswertbar
   (ParseError: PyYAML fehlt: python3 -m pip install pyyaml) – fail-closed
```

Der Schritt „Python-Abhängigkeiten (für Governance-Skripte)" in
`link-check.yml` endet mit `2>/dev/null || true`. Ein gescheiterter
`pip install` wird damit **verschluckt**; die Selbsttests laufen ohne `pyyaml`
und fail-closen.

Belegt durch Gegenprobe in beiden Richtungen:

| Umgebung | `reserve_finisher` | `governance_contract` | `blustradius_register` |
|---|---|---|---|
| `/usr/bin/python3` **ohne** pyyaml (= CI) | rc=2 | rc=1 | rc=2 |
| `/usr/bin/python3` **mit** pyyaml 6.0.3 | rc=0 | rc=0 | rc=0 |
| `/tmp/venv` (mit pyyaml) | rc=0 | rc=0 | rc=0 |
| Uhr +97 und +1461 Tage, mit pyyaml | rc=0 | rc=0 | rc=0 |

`pyyaml==6.0.3` steht in `requirements-ci.txt` (Zeile 827) — die Abhängigkeit
ist also **deklariert**; sie kommt nur nicht an. Das ist ein eigener Vorgang
(CI-Härtung: `|| true` gehört vor den Verbraucher, nicht über den Fehler) und
**nicht Teil dieses PR**.

### 8.3 #1107 wurde geschlossen — vom Herausgeber

Um 18:33 UTC, während dieser Vorgang lief, hat **der Herausgeber** #1107 mit
Schließakte geschlossen (`completed`, „keine Korridor-Änderung"), und PR #1172
wurde um 18:36 gemergt. Der Agent hat weder geschlossen noch gemergt; die
Entscheidung liegt laut `CLAUDE.md` D2 beim Herausgeber. Der Punkt „#1107
bleibt offen" in Abschnitt 7 ist damit **überholt** — er bleibt als Protokoll
stehen, weil er den Stand zur Zeit der Abfassung beschreibt.
