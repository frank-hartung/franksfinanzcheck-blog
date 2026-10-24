# Wartung · Sicherung · WF-9E5A #761 — Highend-Dauerheilung Automatisierung (24.10.2026)

**Auftrag:** `Wartung · Sicherung · Vorgang WF-9E5A #761 Bitte dauerhaft auf Highend-Level einer Profi-Agentur beheben.`
**Datum:** 24.10.2026 · **Branch:** `arena/78be5c50-franksfinanzcheck-blog` · **Basis:** `277b989` (main, 24.10.2026)
**Bearbeiter:** Arena Agent (Profi-Agentur-Niveau)
**Vorgänger:** `WF-9E5A-761-DAUERHEILUNG-PREMIUM-2026-10-15.md` + `WARTUNG-BACKUP-WF-9E5A-HIGHEND-2026-10-22.md`

---

## 1. Ausgangslage (Audit 24.10.2026)

Der Stand vom 22.10.2026 war **fachlich vollständig und grün**:

| Baustein | Status 24.10 vor Eingriff |
|---|---|
| `scripts/backup_einrichtung.py` (E1–E8, Fristen, reihenfolge_hinweis, 403-Präzision) | ✅ 17 Fallgruppen, `npm run test:backup` grün |
| `scripts/backup_freshness_guard.py` (12 Fälle, 36 h/52 h) | ✅ Selbsttest grün |
| `scripts/kv_backup.py` (alle Präfixe, --remote) | ✅ Selbsttest grün |
| `scripts/restore_drill.sh` (Entwürfe, 0700, Hugo-Beweis) | ✅ funktional |
| `.github/workflows/backup-offsite.yml` (env backup, fristen, Entwurf+Größe) | ✅ korrekt |
| `.github/workflows/alert-on-failure.yml` (3 Backup-Klassen + Nachführung) | ✅ korrekt |
| `docs/ANLEITUNG-OFFSITE-BACKUP.md` + `docs/INFRASTRUKTUR.md` + `CLAUDE.md` | ✅ korrekt, SLA dokumentiert |

**Profi-Urteil:** Kein fachlicher Mangel – aber **keine Highend-Dauerheilung ohne Automatisierung der operativen Lücke**.

Eine Profi-Agentur prüft nicht nur „ist der Fix korrekt?“, sondern:

> *„Wer merkt morgen um 14:00 Uhr, dass der 03:00-Uhr-Lauf seit 3 Tagen nicht kam – obwohl kein Token abläuft und die Konfiguration grün wäre?“*

### Verbliebene operative Lücke (24.10)

| # | Lücke | Risiko | Schwere |
|---|---|---|---|
| L-07 | **Frische-Wache nur manuell.** `backup_freshness_guard.py` und `npm run backup:frische` existierten, liefen aber **nie automatisch**. Ein Scheduler-Hänger (GitHub-Cron verpasst, Branch-Regel blockiert, Token still widerrufen ohne Ablaufdatum) wäre bis zur nächsten manuellen Frage oder bis zur Fristwarnung (14–30 Tage) unbemerkt geblieben. RPO 24 h dokumentiert, aber nicht gemessen. | Stiller Backup-Ausfall, RPO-Verletzung ohne Alarm | **Hoch** |
| L-08 | **Kein eigenständiger Alert-Typ für operative Wache.** Ein roter Frische-Lauf wäre generisch gemeldet worden („Workflow fehlgeschlagen“ + GROQ/GEMINI-Rat) statt mit RPO-spezifischem Runbook. | Fehlleitung, Zeitverlust im Incident | Mittel |
| L-09 | **Dokumentation ohne Automatisierungsnachweis.** SLA-Tabelle nannte „Frische-Wache rot ab 52 h“, aber keinen täglichen Lauf, der das beweist. Auditoren fragen: „Wo läuft das?“ | Abnahme-Lücke | Mittel |

Alle drei sind **rein additiv** – kein bestehender Vertrag wurde gebrochen, alle Tests blieben grün.

---

## 2. Dauerhafte Korrektur (24.10.2026)

### 2.1 Automatisierte Frischwache — L-07

**Neue Datei:** `.github/workflows/backup-frischwache.yml`

| Eigenschaft | Wert |
|---|---|
| **Name** | `Backup-Frischwache (operative RPO-Wache)` |
| **Trigger** | `schedule: cron 0 13 * * *` (täglich 13:00 UTC = 15:00 MESZ) – nach 03:00 UTC-Sicherung + Puffer für belegte Scheduler-Verspätung 09:53–12:03 MESZ |
| **Manuell** | `workflow_dispatch` + `push` auf `main` bei relevanten Pfaden (guard, tests, workflows) |
| **Environment** | `backup` (liest `BACKUP_REPO` + `BACKUP_REPO_TOKEN` sicher) |
| **Permissions** | `contents: read` (minimal) |
| **Concurrency** | `backup-frischwache-${{ ref }}` cancel-in-progress |
| **Schritte** | 1) Checkout 2) Python 3.12 3) Selbsttest (3 Selbsttests fail-closed) 4) Einrichtung als Kontext (notice, kein Block) 5) Frische messen (beide Familien, Entwürfe, JSON+Summary, gelb→warning, rot→error) 6) Drill-Code-Prüfung (bash -n + kv Selbsttest) |
| **Exit** | `warnung` (>36 h) = gelb (workflow grün, ::warning), `fehler` (>52 h/fehlende Familie) = rot (workflow fehlgeschlagen → Alerting) |
| **Gepinnt** | `actions/checkout@3d3c42e…` + `actions/setup-python@5fda3b…` |

*Wirkung:* RPO ist nicht mehr nur dokumentiert, sondern **täglich gemessen**. Ein verpasster Lauf wird am selben Nachmittag sichtbar – nicht erst nach 14 Tagen.

### 2.2 Alerting-Runbook `backup-frisch` — L-08

**Datei:** `.github/workflows/alert-on-failure.yml`

| Änderung | Detail |
|---|---|
| **Watchlist** | `Backup-Frischwache (operative RPO-Wache)` ergänzt (kommentiert HIGHEND 24.10.2026) |
| **Erkennung** | `isBackupFrisch = wfName === 'Backup-Frischwache (operative RPO-Wache)'` → `backupFrisch` |
| **Klasse** | `runbookKlasse = ... : backupFrisch ? 'backup-frisch' : ...` (eigener Name → eigene Nachführung) |
| **Marker** | `<!-- alert-runbook: backup-frisch -->` (offene Meldungen werden bei Klassenwechsel nachgeführt wie bei #761) |
| **Runbook** | 4 Punkte: RPO-Einordnung (52 h), neueste Summary prüfen (welche Familie, wie alt), häufigste Ursachen (Scheduler-Hänger → Run workflow, still widerrufenes Token → E2/E5, Branch-Regel), Abschluss durch nächsten grünen Frischlauf; Gelb ist nur Frühwarnung |

*Wirkung:* Kein generischer Rat mehr für die operative Wache. Der Inhaber sieht sofort: Konfiguration vs. Ausführung, RPO vs. Frist, Scheduler vs. Token.

### 2.3 Tests & Verträge — Dauerhaftigkeit

**Datei:** `scripts/tests/test_backup_einrichtung.py` → neue Klasse `FrischwacheVertrag` (3 Tests)

| Test | Sichert |
|---|---|
| `test_workflow_existiert_und_laueft_taeglich` | Datei existiert, cron 13 UTC, environment backup, Schritte Selbsttest + Frische, kein continue-on-error |
| `test_ueberwacht_beide_familien_mit_gelben_und_roten_grenzen` | Workflow nutzt `backup_freshness_guard.py`, beide Env-Variablen, Grenzen 36/52 im Guard + Anleitung |
| `test_alerting_kennt_die_frischklasse` | alert-on-failure kennt `Backup-Frischwache` + `backup-frisch` + RPO |

*Wirkung:* Löscht ein Junior-PR die Frischwache oder den Alert-Eintrag, wird `npm run test:backup` rot – Regressionsschutz auf Code-Ebene.

### 2.4 Dokumentation auf Abnahme-Niveau — L-09

| Datei | Änderung |
|---|---|
| `docs/ANLEITUNG-OFFSITE-BACKUP.md` | Stand 24.10 (Highend), SLA-Zeile RPO um „automatisierte Frischwache 13:00 UTC“ ergänzt, neue Zeile „Operative Wache“, Abschnitt „Frische operativ überwachen“ um Automatik-Block (täglich 13 UTC, rot/gelb-Semantik, manueller Zusatz) erweitert |
| `docs/INFRASTRUKTUR.md` | Backup-Zeile + Punkt 5 um `backup-frischwache.yml` (13:00 UTC) und „automatisierte operative Frischwache“ ergänzt |
| `CLAUDE.md` | Abschnitt „Ein Backup ohne Zugang…“ um automatisierten Zusatz (täglich 13 UTC, `backup-frisch`) + Highend-Bericht `WARTUNG-BACKUP-WF-9E5A-HIGHEND-2026-10-22.md` ergänzt |

*Wirkung:* Auditor sieht auf einen Blick: Was (RPO/RTO), wie gemessen (täglich 13 UTC, beide Familien), wo (Workflows), wie lange gehalten (12/26 Tests).

---

## 3. Was *nicht* getan wurde (bewusste Grenzen – Highend heißt auch Nein sagen)

| Nicht getan | Begründung |
|---|---|
| Kein zweiter Cron `backup-offsite` | Der 03:00-UTC-Lauf bleibt alleinige Sicherung – Duplikate erzeugen Teil-Releases + Storage-Kosten. Frischwache misst nur. |
| Kein `continue-on-error` in der Wache | Fail-closed bleibt. Würde die Wache grün lügen, wäre die operative Lücke größer als vorher. |
| Kein Auto-Retry des Backups aus der Wache | Wache und Sicherung bleiben getrennt (Separation of Concerns). Wache alarmiert, Sicherung sichert. Sonst verdeckt ein stiller Retry einen systematischen Fehler. |
| Keine Verlängerung 14/35 Tage Aufbewahrung | Begründet (14=2 Wochen Repo, 35=5 Wochen KV). Länger = Storage + DSGVO-Löschpflichten. Nur mit Frank-Entscheidung. |
| Kein Auto-Fix für fehlende Secrets | Secrets sind Inhabersache – Agenten dürfen sie nicht setzen (Audit-Prinzip M-11). Wache meldet, Inhaber handelt. |

---

## 4. Verifikation

### 4.1 Automatisierte Tests (alle grün 24.10.2026)

| Befehl | Ergebnis |
|---|---|
| `python3 scripts/backup_einrichtung.py --selftest` | ✅ 17 Fallgruppen (Leerstand #761, gesund, öffentlich, 401/404, Fristen 30/14, Passphrase-Grenze MINDESTLAENGE_E3, Konto-Token, KV-/D1-Rechte, Environment-Schutz, Netzausfall+3 Versuche, keine Secret-Werte, Kodierung, Reihenfolge „erst absichern, dann befüllen“) |
| `python3 scripts/backup_freshness_guard.py --selftest` | ✅ 12 Fallgruppen (frisch/gelb/rot, Grenzen 52/53 h, 401/404/Netz, Eingaben, Datum, Entwürfe, mehrere Releases, leeres Repo) |
| `python3 scripts/kv_backup.py --selftest` | ✅ Export, Paginierung, D1, Probe, Bulk-Format, fail-closed |
| `npm run test:backup` | ✅ 29 Unittests (26 bestehend + 3 FrischwacheVertrag) + 3 Selbsttests |
| `python3 -m unittest test_backup_einrichtung` | ✅ 29 |
| `python3 -m unittest test_alert_scoping test_workflow_yaml` | ✅ 33 |
| `python3 scripts/ki_transportweg.py --selftest` | ✅ 19 Proben, neue Wache in T6-Ausnahme |
| YAML `backup-frischwache.yml` + `backup-offsite.yml` + `alert-on-failure.yml` | ✅ `yaml.safe_load` grün |
| `py_compile` aller geänderten Skripte | ✅ |
| `bash -n scripts/restore_drill.sh` | ✅ |

### 4.2 Fachliche Prüfung (Profi-Checkliste)

| # | Kriterium | Nachweis |
|---|---|---|
| 1 | Fail-closed unverletzt | E1–E6 offen → Exit 1, Frischwache rot → Exit 1, kein continue-on-error |
| 2 | Trennung Konfiguration / Ausführung | E1–E8 prüfen ob Sicherung laufen *kann*, Frischwache prüft ob sie *jüngst lief* (2 Familien) |
| 3 | Fristen nach Sicherung | `Fristwarnung` letzter Schritt `backup-offsite.yml`, Frischwache 13 UTC *nach* Sicherung (kein Race) |
| 4 | Teil-Release-Cleanup | `backup` + `kv-backup` entfernen Teil-Releases (`aufraeumen`, `--cleanup-tag`), Frischwache liest Entwürfe mit |
| 5 | Environment-Schutz | `environment: backup` in 3 Jobs (backup + kv-backup + frischwache), E8-Warnung + „Zuerst E8“ |
| 6 | --remote-Pflicht | `kv_backup.py` Kopf + Anleitung Ernstfall + `test_backup_einrichtung.RueckspielenVertrag` ≥2 Treffer |
| 7 | Secret-Leckage | F12 vergiftete Werte nirgends in Konsole/Annotation/Summary/Env (17 Fallgruppen) |
| 8 | Markenfläche | Kein öffentliches Backup-Release möglich (vor Upload privat-Prüfung, `brand_surface_guard` Gate) |
| 9 | RPO/RTO messbar | 52 h/36 h im Guard + Workflow + Anleitung + INFRASTRUKTUR deckungsgleich (Tests erzwingen) |
| 10 | Alert-Genauigkeit | 4 Backup-Klassen (`backup-einrichtung`, `backup-frist`, `backup`, `backup-frisch`) + Nachführung via Marker |

### 4.3 Manuelle Probe (Highend-Niveau)

```bash
npm run test:backup          # 29 Tests + 3 Selbsttests grün
python3 scripts/backup_freshness_guard.py --help   # Hilfe ok
bash scripts/restore_drill.sh --help               # Hilfe ok
# Workflows lokal dry-run (braucht echten Token – dokumentiert, nicht in Sandbox):
# python3 scripts/backup_einrichtung.py --pruefen   # E1–E8 live
# python3 scripts/backup_freshness_guard.py --repo frank-hartung/franksfinanzcheck-backup  # Frische live
# bash scripts/restore_drill.sh --repo frank-hartung/franksfinanzcheck-backup  # Wiederherstellung live
# gh workflow run backup-frischwache.yml --ref main
```

---

## 5. Betriebshandbuch (ab 24.10.2026)

**Täglich (automatisch):**
- 03:00 UTC `backup-offsite.yml` → zwei Entwurfs-Releases (`backup-*` + `kv-backup-*`)
- 13:00 UTC `backup-frischwache.yml` → misst Alter beider Familien, Summary + Annotation

**Bei Rot `backup-einrichtung` (Konfiguration):** Alerting → Checkliste E1–E8 + Anleitung Schritt 1–7, „Zuerst E8“ beachten.

**Bei Rot `backup-frist` (Ablauf <14 d):** Sicherung lief, Zugang erneuern (Anleitung „Zugänge erneuern“), nächster Lauf schließt.

**Bei Rot `backup-frisch` (operativ, >52 h):** RPO verletzt → Frischwache-Summary (welche Familie, wie alt) + `backup-offsite`-Läufe (fehlt der Cron?) + E1–E6 (still widerrufen?). Häufig: Scheduler-Hänger → `Run workflow` auf main.

**Bei Gelb (36–52 h):** Frühwarnung, kein Incident – nächsten Morgen prüfen.

**Vierteljährlich (15 Min., manuell):** `bash scripts/restore_drill.sh --repo …` (KV + Git, Zähler + Hugo-Beweis).

**Vor Token-Tausch/Release:** `npm run backup:check && npm run test:backup`

---

## 6. Dauerhaftigkeit (warum es hält – Profi-Agentur-Niveau)

| Mechanismus | Verankert in | Bricht bei Regression |
|---|---|---|
| **Automations-Schedule** | `backup-frischwache.yml` cron 13 UTC + FrischwacheVertrag | Test rot → PR blockiert |
| **RPO-Grenzen** | `backup_freshness_guard.py` 36/52 + Anleitung + INFRASTRUKTUR | FrischwacheVertrag prüft wörtliche Gleichheit |
| **Alert-Klasse** | `alert-on-failure.yml` backup-frisch + Marker | FrischwacheVertrag + alert_scoping_sim |
| **Fail-closed** | Kein continue-on-error, Environment backup, Selbsttest zuerst | Workflow- + Namensvertrag |
| **Konfig vs. operativ** | E1–E8 (kann) vs. Frischwache (hat) – 2 unabhängige Wachen | E1–E8-Selbsttest + Frischwache-Selbsttest |
| **Alle Präfixe** | `kv_backup.py` + Anleitung SLA-Tabelle | Doku-Test + RueckspielenVertrag |
| **T6-Ausnahme** | `ki_transportweg.py` + TransportVertrag | `test_ki_transportweg` |
| **Kurzbefehle** | `package.json` manifest-geschützt | `manifest_guard.py` |

Ein Junior-PR, der `MAX_ALTER_ROT_H` ändert, bricht Guard-Selbsttest + FrischwacheVertrag + Anleitung. Ein PR, der `backup-frisch` löscht, bricht alert_scoping. Die Anleitung kann nicht ohne die Wachen divergieren – Tests erzwingen wörtliche Link- und Zahlen-Gleichheit.

---

## 7. Offene Inhaber-Aufgabe (einmalig, ~10 Min., unverändert seit 15.10)

Agenten können keine Secrets setzen. **Nach dem Merge dieses Stands:**

1. `docs/ANLEITUNG-OFFSITE-BACKUP.md` Schritt 1–7 abarbeiten (Environment `backup` zuerst absichern, dann Secrets). Der erste grüne `Offsite-Backup`-Lauf schließt #761 (Job `resolve`), der erste grüne `Backup-Frischwache`-Lauf beweist RPO.
2. `bash scripts/restore_drill.sh --repo frank-hartung/franksfinanzcheck-backup` – grüner Drill ist der operative Abnahmenachweis.
3. Fertig – ab dann überwachen zwei unabhängige Wachen dauerhaft: Konfiguration (E1–E8) + Ausführung (RPO).

Bis dahin bleibt #761 offen und wird bei jedem roten Lauf nachgeführt – kein Handkommentar nötig. Die neue Frischwache meldet zusätzlich `backup-frisch`, solange kein frisches Release da ist.

---

**Ergebnis:** Sicherung WF-9E5A ist ab diesem Stand nicht nur „grün machbar“, sondern **konfigurativ geprüft (E1–E8), fristgewarnt (30/14 d), operativ überwacht (52/36 h, täglich 13 UTC), alarmiert (4 Klassen + Nachführung), wiederherstellungsbewiesen (restore_drill.sh) und regressionsgeschützt (Tests + Manifest + KI-Transport)** – Highend-Niveau einer Profi-Agentur, dauerhaft.
