# Wartung · Sicherung · WF-3150 #1030 — Stand 12.11.2026

**Auftrag:** `Wartung · Sicherung · Vorgang WF-3150 #1030 Bitte dauerhaft auf
Highend-Level einer Profi-Agentur beheben.`
**Branch:** `arena/19dd3d9b-franksfinanzcheck-blog` · **Basis:** `0e7784d` (`main`)
**Vorgänger:** `WARTUNG-BACKUP-WF-3150-1030-SELBSTHEILUNG-HIGHEND-2026-11-07.md`,
PR #1171 (offen, nicht gemergt)

---

## 1 · Das Ergebnis in vier Sätzen

Die Sicherung läuft **weiterhin nicht**: Abonnenten und
Einwilligungsnachweise werden seit dem 15.10.2026 nicht gesichert, und das
kann nur der Inhaber ändern (fünf Zugänge/Ziele, rund 10 Minuten, §4).
Der Fix vom 10.11. (PR #1171) ist **nie auf `main` angekommen** – deshalb
trug der Tageslauf vom 11.11. erneut zwei rote Schritte mit zwei
Ratschlägen, einer davon falsch. Dieser Zweig bringt genau die
Sicherungs-Teile von #1171 auf den heutigen `main`-Stand – ohne dessen
fremde Daten- und Artikeländerungen – und schließt eine Lücke, die #1171
selbst noch hatte (§3). #1030 bleibt offen, bis ein Lauf mit echtem Release
grün ist; ein früheres Schließen wäre Schein.

## 2 · Live-Befund (12.11.2026, GitHub-API)

| Prüfung | Ergebnis |
|---|---|
| Frischwache | jüngster Lauf `43091924689` (11.11. 19:57 UTC) `failure`; alle 11 Läufe auf `main` seit dem 05.11. rot, Meldung offen seit 02.11. |
| Rote Schritte in diesem Lauf | „Voraussetzungen prüfen“ (richtig) **und** „Leerlauf prüfen“ (falscher Rat: „Ein Lauf ist grün, gesichert wurde aber nichts“ – es war kein Lauf grün) |
| Offsite-Backup | jüngster Lauf `43000930211` (11.11.) `failure`; die letzten 8 geplanten Läufe (04.–11.11.) rot, laut Vorgänger-Akte durchgehend seit 15.10. |
| Offene Pflichtpunkte (Annotationen des Laufs) | **E1** `BACKUP_REPO`, **E2** `BACKUP_REPO_TOKEN`, **E3** `BACKUP_PASSPHRASE`, **E5** `CF_KV_BACKUP_TOKEN`, **E6** `KV_NAMESPACE_ID_ABO`; Hinweis **E8** (Environment `backup` für jeden Branch nutzbar) |
| PR #1171 (Fix vom 10.11.) | offen; `gate`, `regression`, Playwright rot; 46 Commits hinter `main`; enthält 13 sachfremde Dateien (Artikel, GSC-Daten) |
| `main` (`0e7784d`) | enthält den Fix nicht – `backup-frischwache.yml` unverändert seit dem 07.11. |

## 3 · Was dieser Zweig ändert

**Aus #1171 übernommen (sechs Dateien, sauber auf `main` angewendet):**

1. **Eine Ursache, ein Rat.** „Voraussetzungen prüfen“ schreibt die offenen
   Kennungen als Schritt-Ausgabe (`offene_einrichtung`), auch bei Rot.
   „Leerlauf prüfen“ liest sie und vergibt bei offener Einrichtung einen
   Hinweis statt eines zweiten roten Rats.
2. **Kein Abbruch mitten in der Heilung.** `cancel-in-progress` gilt nur
   noch für Push-Läufe; Tageslauf und „Run workflow“ laufen zu Ende.

**Neu in dieser Sitzung – die Lücke in #1171:**

#1171 sagt zu: „Fehlt die Auskunft, endet die Prüfung rot (Exit 2).“ Im
Workflow war dieser Fall **nicht erreichbar**. `${{ steps.setup.outputs.offene_einrichtung }}`
ist für GitHub derselbe leere Text, ob der Schritt „nichts offen“ gemeldet
hat, übersprungen wurde oder abgestürzt ist. Die Variable war damit immer
gesetzt, der Prüfer las „geprüft, nichts offen“ – und hätte bei einem
übersprungenen Einrichtungsschritt wieder aus alten grünen Jobs geraten:
derselbe falsche Rat, nur über einen anderen Weg.

Heilung: Die Einrichtungsprüfung schreibt zusätzlich `einrichtung_geprueft=ja`.
Ohne diesen Beleg entfernt der Leerlauf-Schritt die Variable; der Prüfer
antwortet „niemand weiß es“ und endet rot.

| Lage | vorher (#1171) | jetzt |
|---|---|---|
| Einrichtung offen | Hinweis | Hinweis |
| geprüft, nichts offen | echte Leerlauf-Prüfung | echte Leerlauf-Prüfung |
| Schritt übersprungen/abgestürzt | **wie „nichts offen“ – rät aus alten Jobs** | **rot, Exit 2** |
| Kennungen ohne Beleg | Hinweis (grün) | rot |

**Bewusst nicht übernommen:** die Änderungen von #1171 an
`scripts/reserve_healer_coverage.py`, `scripts/selftest_runner.py`,
`data/blustradius-deploy.yml`, vier Artikeln und den GSC-Daten. Sie gehören
nicht zur Sicherung. Geprüft: `selftest_runner.py --selftest` und der
Standardlauf von `reserve_healer_coverage.py` sind auf dem heutigen `main`
ohne sie grün; ob #1171 sie für ein anderes Gate brauchte, zeigt der CI-Lauf
dieses Zweigs.

## 4 · Was nur der Inhaber erledigen kann

Der Agenten-Zugang darf weder Secrets noch Variablen, Repositories oder
Environment-Regeln anlegen (`403 Resource not accessible by integration`,
belegt am 07.11. und 10.11.; in dieser Sitzung nicht erneut versucht).

| Punkt | Was fehlt | Wo |
|---|---|---|
| E8 | Environment `backup` nur für `main` | Settings → Environments → `backup` → „Selected branches“ |
| E1 | privates Ziel-Repo + Variable `BACKUP_REPO` | Repository-Variable |
| E3 | Secret `BACKUP_PASSPHRASE` (32+ Zeichen, **zuerst** in den Passwort-Manager) | Environment `backup` |
| E2 | Secret `BACKUP_REPO_TOKEN` (fine-grained, nur das Ziel-Repo, Contents: Read and write) | Environment `backup` |
| E5 | Secret `CF_KV_BACKUP_TOKEN` (nur „Workers KV Storage: Read“) | Environment `backup` |
| E6 | Variable `KV_NAMESPACE_ID_ABO` | Repository-Variable |

Geführt: `npm run backup:einrichten` · nur prüfen: `npm run backup:status` ·
Anleitung mit vorbelegten Links: `docs/ANLEITUNG-OFFSITE-BACKUP.md`.
Danach ist kein Handgriff nötig: Der nächste Tageslauf stößt die Sicherung
selbst an, misst erneut und schließt #1030 beim ersten grünen Lauf.

## 5 · Nachweise (lokal, auf diesem Zweig)

```text
npm run test:backup                                   → 4 Selbsttests grün (19 / 15 / 22 Fallgruppen + KV)
python3 -m unittest test_backup_einrichtung test_backup_selbstheilung test_alert_scoping
                                                      → Ran 150 tests … OK (mit PyYAML, 0 übersprungen)
python3 scripts/skript_syntax_wache.py --check        → ✅ 697 Dateien
python3 scripts/workflow_js_wache.py --check          → ✅
python3 scripts/workflow_vertrag_wache.py --gate      → ✅
python3 scripts/governance_contract.py --quick        → ✅ 47 Regeln
selftest_clock --trap (97 / 1461 Tage)                → ✅
```

Ohne PyYAML überspringt die Suite 24 Workflow-Tests stillschweigend – auch
die neuen. Die Zahl oben stammt aus einem Lauf **mit** PyYAML 6.0.3.

**Der rote Lauf vom 11.11. nachgestellt:** Beide Schritt-Blöcke wurden aus
dem YAML gelesen und mit Bash ausgeführt, ohne Zugänge (wie im Betrieb):

```text
Voraussetzungen prüfen → Exit 1, „E1–E8 offen: E1 E2 E3 E4 E5 E6“
GITHUB_OUTPUT          → offene_einrichtung=E1 E2 E3 E4 E5 E6 / einrichtung_geprueft=ja
Leerlauf prüfen        → Exit 0, ::notice (kein zweiter Rat)
```

(E4 erscheint nur in der Nachstellung, weil lokal auch
`CLOUDFLARE_ACCOUNT_ID` fehlt; im Betrieb ist E4 vorhanden.)

Vier neue Tests führen den Leerlauf-Block ebenfalls aus: offen mit Beleg →
Hinweis; beide Felder leer → rot, ohne den Satz „Ein Lauf ist grün“;
Kennungen ohne Beleg → rot.

**Nicht belegt:** der Lauf in GitHub Actions selbst. Die Frischwache startet
nur auf `main`; der erste echte Nachweis ist der Lauf nach dem Merge. Der
Fall „geprüft, nichts offen“ ist nur mit Attrappen getestet, weil er eine
fertige Einrichtung voraussetzt.

## 6 · Was nach dem Merge zu erwarten ist

Der Lauf bleibt **rot** – mit genau einem roten Schritt („Voraussetzungen
prüfen“) und einem Rat. Grün wird er erst nach §4.

## 7 · Aufräumen

PR #1171 ist mit diesem Zweig inhaltlich abgelöst und kann geschlossen
werden. PR #1174 (#923, WF-9E5A) ändert dieselben Dateien
(`backup-frischwache.yml`, `backup_einrichtung.py`, `backup_selbstheilung.py`)
und braucht nach diesem Merge einen Abgleich.

## 8 · Geänderte Dateien

| Datei | Änderung |
|---|---|
| `.github/workflows/backup-frischwache.yml` | Schritt-Ausgabe `setup`, Leerlauf liest Ursache + Beleg, `cancel-in-progress` nur für Push |
| `scripts/backup_einrichtung.py` | Ausgabe `offene_einrichtung` + `einrichtung_geprueft`; Selbsttest F19 |
| `scripts/backup_selbstheilung.py` | drei Antworten (offen / nichts offen / unbekannt), `--ohne-setup`, Selbsttest S22 |
| `scripts/tests/test_backup_einrichtung.py` | Vertrag + vier ausgeführte Leerlauf-Fälle |
| `scripts/tests/test_backup_selbstheilung.py` | Auskunftsvertrag |
| `docs/ANLEITUNG-OFFSITE-BACKUP.md` | Abschnitt „Eine Ursache, ein Rat“ + Nachschärfung |
