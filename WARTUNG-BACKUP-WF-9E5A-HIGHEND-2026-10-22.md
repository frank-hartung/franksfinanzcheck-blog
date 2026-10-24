# Wartung · Sicherung · WF-9E5A #761 — Highend-Dauerheilung (22.10.2026)

**Auftrag:** `Wartung · Sicherung · Vorgang WF-9E5A #761 Bitte dauerhaft auf Highend-Level einer Profi-Agentur beheben.`
**Datum:** 22.10.2026 · **Branch:** `arena/8212c2d8-franksfinanzcheck-blog` · **Basis:** `fcc774a` (main)
**Bearbeiter:** Arena Agent (Profi-Agentur-Niveau)

---

## 1. Ausgangslage (Audit 22.10.2026)

Der Kernfix aus `WF-9E5A-761-DAUERHEILUNG-PREMIUM-2026-10-15.md` war **vollständig im Repo vorhanden und grün**:

| Baustein | Status 22.10. |
|---|---|
| `scripts/backup_einrichtung.py` (E1–E8, Fristen, reihenfolge_hinweis) | ✅ 17 Fallgruppen, `npm run test:backup` grün |
| `scripts/kv_backup.py` (KV/D1, --remote-Hinweis) | ✅ Selbsttest grün |
| `scripts/restore_drill.sh` (Entwürfe, 0700, Hugo-Beweis) | ✅ funktional |
| `.github/workflows/backup-offsite.yml` (env backup, fristen, Entwurf+Größe, Teil-Cleanup) | ✅ korrekt |
| `.github/workflows/alert-on-failure.yml` (3 Backup-Klassen + Nachführung) | ✅ korrekt |
| `docs/ANLEITUNG-OFFSITE-BACKUP.md` (7 Schritte, vorbelegte Links) | ✅ korrekt |
| `CLAUDE.md`, `docs/INFRASTRUKTUR.md`, `package.json` | ✅ korrekt |

**Dennoch keine Highend-Abnahme ohne Lückenanalyse.** Eine Profi-Agentur prüft nicht nur „ist der Fix da?“, sondern:

> *„Überlebt der Fix den nächsten Token-Tausch, den nächsten Scheduler-Hänger und den nächsten Junior-PR – ohne stillen Datenverlust?“*

### Gefundene operative Lücken (Profi-Sicht)

| # | Lücke | Risiko | Schwere |
|---|---|---|---|
| L-01 | **Keine operationelle Frische-Prüfung.** E1–E8 sagen „kann sichern“, nicht „hat jüngst gesichert“. Ein ausgesetzter Cron (Scheduler-Hänger, Branch-Regel falsch) bliebe bis zur Ablauf-Warnung (14–30 Tage) unbemerkt. | Stiller Backup-Ausfall, RPO-Verletzung | **Hoch** |
| L-02 | **403-Fehlerbilder unpräzise.** GitHub 403 (Rate-Limit vs. fehlende Rechte vs. IP-Restriktion) fiel in „unerwartete Antwort“ – Inhaber hätte raten müssen. | Fehlleitung bei der Einrichtung, Zeitverlust | Mittel |
| L-03 | **KV-Abdeckung dokumentarisch unvollständig.** Code sichert *alle* KV-Präfixe (`budget:`, `takt:`, `feedback:` …), Doku nannte nur die drei Pflicht-Präfixe. Auditoren/DSGVO-Nachweis würden Diskrepanz bemängeln. | Compliance-Diskrepanz | Mittel |
| L-04 | **SLA/RPO/RTO nirgends verbindlich beziffert.** Ohne Zahlen keine Abnahme, kein Monitoring-Soll, keine Eskalationsschwelle. | Operative Unschärfe | Mittel |
| L-05 | **Kein Kurzbefehl für Frische + Probe.** Inhaber müsste sich `restore_drill.sh`-Syntax merken; CI hätte keine Ein-Zeilen-Prüfung. | Reibung, geringerer Drill-Rhythmus | Niedrig |
| L-06 | **KI-Transport-Ausnahme fehlte für neuen Frische-Check.** Nächster `ki_transportweg`-Lauf hätte neue Datei als „unerlaubten API-Aufruf“ gemeldet. | Falscher Alarm, Vertrauensverlust | Niedrig |

Alle Lücken sind **ergänzend** – kein bestehender Vertrag wurde gebrochen.

---

## 2. Dauerhafte Korrektur (Highend-Ergänzung)

### 2.1 Konfigurationsprüfung präzisiert — L-02

**Datei:** `scripts/backup_einrichtung.py` · **Punkt:** E2 (Schreibzugang)

```python
# Vorher: 403 → „unerwartete Antwort HTTP 403“ (generisch)
# Nachher: 403 → Zweig
#   · „rate limit“ in Meldung → „GitHub-Rate-Limit erreicht“ + Warte-Hinweis
#   · sonst             → „Zugriff verweigert“ + „Only select repositories“-Hinweis
```

*Wirkung:* Inhaber bekommt den exakten nächsten Schritt statt „Token und Ziel prüfen“. Tests bleiben grün (kein bestehender Fall bricht).

### 2.2 Operationelle Frische-Wache — L-01, L-04, L-05, L-06

**Neue Datei:** `scripts/backup_freshness_guard.py` (Highend-Komplement zu E1–E8)

| Eigenschaft | Wert |
|---|---|
| **Was** | Liest neueste `backup-*` + `kv-backup-*` Releases im privaten Backup-Repo (Entwürfe eingeschlossen, wie `restore_drill.sh`) |
| **Grenzen** | 52 h rot (täglicher Lauf + GitHub-Verspätung belegt 07.–15.10.: 09:53–12:03 MESZ), 36 h gelb (Frühwarnung) |
| **Quellen** | Nur `api.github.com/repos/{repo}/releases?per_page=100` – kein Modell, reine Verwaltungs-API |
| **Exit** | 0 = frisch (ok/gelb), 1 = überfällig/unprüfbar (fehler), 2 = Aufruffehler |
| **Ausgabe** | Konsole (menschlich) + `--json` (CI) |
| **Selbsttest** | 12 Fallgruppen offline: frisch/gelb/rot, Grenzen 52/53 h, 401/404/Netz, Eingaben, Datum, Entwürfe, mehrere Releases, leeres Repo |
| **Kurzbefehle** | `npm run backup:frische` · `npm run backup:check` |

**Warum 52 h?** Täglich 03:00 UTC + belegte Scheduler-Verspätung bis 12:03 MESZ = 33 h für einen verpassten Tag noch grün, ab 52 h definitiv rot – exakt ein verpasster Lauf + Puffer.

**Integration:**

| Ort | Änderung |
|---|---|
| `package.json` | `test:backup` erweitert um Frische-Selbsttest; neu `backup:frische`, `backup:probe`, `backup:check` |
| `scripts/ki_transportweg.py` | `backup_freshness_guard.py` zur T6-Ausnahmeliste (GitHub-Releases, kein Modell) mit Vertrags-Hinweis |
| `docs/ANLEITUNG-OFFSITE-BACKUP.md` | Abschnitt „Betriebszusagen (SLA)“ + Frische-Anleitung unter „Was gesichert wird“ |
| `docs/INFRASTRUKTUR.md` | Backup-Zeile + Punkt 5 mit SLA/RPO/RTO und Frische-Wache |
| `CLAUDE.md` | Abschnitt „Ein Backup ohne Zugang …“ um Frische-Wache + RPO/RTO ergänzt |
| `scripts/kv_backup.py` | Kopfkommentar: alle Präfixe genannt, „alle KV-Schlüssel, kein Präfix-Filter“ |

*Wirkung:* Operative Lücke geschlossen – Konfiguration (E1–E8) + Ablauf (Fristen) + Frische (täglicher Nachweis) sind nun drei unabhängige Säulen.

### 2.3 Dokumentation auf Abnahme-Niveau — L-03, L-04

**`docs/ANLEITUNG-OFFSITE-BACKUP.md` Abschnitt „Betriebszusagen (Profi-Niveau: SLA · RPO · RTO · Abdeckung)“:**

| Tabelle | Inhalt |
|---|---|
| **SLA** | RPO 24 h / 52 h Toleranz, RTO < 60 Min., Aufbewahrung 14/35, Verschlüsselung AES-256/PBKDF2 200k+600k, E1–E8 + Fristen + 17 Fallgruppen, Fristwarnung 30/14 Tage |
| **KV-Abdeckung** | Vollständig: `abo:`/`token:`/`nachweis:` (DSGVO Art. 7 Abs. 1) + `budget:`/`exportlog:`/`takt:`/`feedback:`+`fbtag:` (Betrieb) + D1 optional |
| **Nicht gesichert** | Explizit: Issues/PRs, Secrets/Variablen, Cloudflare-Zone, `gh-pages`, Worker-Logs – jeweils mit Mitigation |
| **Frische-Check** | Ein-Zeilen-Befehle lokal/CI, Ergänzung zu E1–E8 erklärt |

*Wirkung:* Auditor (DSGVO, ISO) und neuer Mitarbeiter sehen auf einen Blick: was, wie lange, wie schnell zurück, was fehlt bewusst – Abnahme-fähig.

### 2.4 Kopfkommentar präzisiert — L-03

`scripts/kv_backup.py`: „Zusätzlich alle Betriebspräfixe (…) mitgesichert – nicht personenbezogen, aber betriebskritisch“ + „alle KV-Schlüssel, kein Präfix-Filter“.

---

## 3. Was *nicht* getan wurde (bewusste Grenzen – Highend heißt auch Nein sagen)

| Nicht getan | Begründung |
|---|---|
| Kein neuer Schedule-Workflow `backup-freshness.yml` | Ein täglicher Cron, der nur „ist das Backup frisch?“ fragt, duplizierte das Alerting von `backup-offsite.yml` und erzeugte bei jedem GitHub-Scheduler-Hänger einen Fehlalarm. Highend: Frische-Wache als *Werkzeug*, nicht als zweiter Cron – aufrufbar manuell, in CI, oder im bestehenden Watchdog. Inhaber entscheidet Laufzeit. |
| Kein `continue-on-error` oder E8 als Pflicht-Fehler | Fail-closed bleibt – E8 ist Hinweis, nicht Blocker. Würde E8 blockieren, stünde die Sicherung 30 Tage auf Rot wegen 10-Minuten-Aufgabe (Reihenfolge-Hinweis löst das besser). |
| Keine Verlängerung Aufbewahrung 14→90 Tage | 14/35 sind begründet (14 = 2 Wochen Repo, 35 = 5 Wochen KV). Länger kostet stillen Storage und verschiebt DSGVO-Löschpflichten. Änderung nur mit Frank-Entscheidung. |
| Kein Auto-Fix für fehlende Secrets | Secrets sind Inhabersache – Agenten dürfen sie nicht setzen (Audit-Prinzip). |
| Keine Duplikation der KV-Sicherung in D1-Gate | KV ist alleinige DSGVO-Quelle; D1 ist optionaler Zähler. Trennung bewusst. |

---

## 4. Verifikation

### 4.1 Automatisierte Tests (alle grün 22.10.2026)

| Befehl | Ergebnis |
|---|---|
| `python3 scripts/kv_backup.py --selftest` | ✅ Export, Paginierung, D1, Probe, Bulk, fail-closed |
| `python3 scripts/backup_einrichtung.py --selftest` | ✅ 17 Fallgruppen (inkl. 403-Rate-Limit-Zweig, F17 Reihenfolge) |
| `python3 scripts/backup_freshness_guard.py --selftest` | ✅ 12 Fallgruppen (frisch/gelb/rot, Grenzen, 401/404/Netz, Entwürfe) |
| `npm run test:backup` | ✅ 26 Unittests `test_backup_einrichtung` + 3 Selbsttests |
| `python3 scripts/ki_transportweg.py --selftest` | ✅ inkl. neuer Ausnahme (19 Tests) |
| `python3 -m unittest test_ki_transportweg` | ✅ 36 Tests |
| `python3 scripts/manifest_guard.py` | ✅ 0 Befunde |
| `python3 scripts/manifest_guard.py --selftest` | ✅ 19 Proben |
| `bash -n scripts/restore_drill.sh` | ✅ Syntax ok |
| `py_compile` aller geänderten Skripte | ✅ |
| YAML `backup-offsite.yml` | ✅ `yaml.safe_load` grün |

### 4.2 Fachliche Prüfung

| Punkt | Befund |
|---|---|
| Fail-closed unverletzt | E1–E6 offen → Exit 1, `alert-on-failure.yml` meldet `backup-einrichtung` statt GROQ/GEMINI |
| Fristwarnung nach Sicherung | Letzter Schritt `Fristwarnung` nur bei `success()`, Meldung „Sicherung gelaufen – jetzt erneuern“ |
| Teil-Release-Cleanup | `backup` und `kv-backup` entfernen Teil-Releases bei unvollständigem Upload (`aufraeumen`, `gh release delete --cleanup-tag`) |
| Environment-Schutz | `environment: backup` in beiden Jobs, E8-Warnung + „Zuerst E8“-Hinweis bei offenem Pflichtpunkt |
| --remote-Pflicht | `kv_backup.py` Kopf + `ANLEITUNG` Ernstfall + `test_backup_einrichtung.RueckspielenVertrag` (≥2 Treffer) |
| Secret-Leckage | F12 vergiftete Werte nirgends in Konsole/Annotation/Summary/Env |
| Marktfläche | Kein öffentliches Backup-Release möglich (vor Upload privat-Prüfung, `brand_surface_guard` Gate) |

### 4.3 Manuelle Probe (Highend-Niveau)

```bash
npm run test:backup        # 26 Tests + 3 Selbsttests grün
npm run backup:check       # alle drei Selbsttests grün
python3 scripts/backup_freshness_guard.py --help   # Hilfe ok
bash scripts/restore_drill.sh --help               # Hilfe ok
# Live (braucht echten Token) – dokumentiert, nicht in Sandbox ausführbar:
# python3 scripts/backup_einrichtung.py --pruefen   # E1–E8 live
# python3 scripts/backup_freshness_guard.py --repo frank-hartung/franksfinanzcheck-backup  # Frische live
# bash scripts/restore_drill.sh --repo frank-hartung/franksfinanzcheck-backup  # Wiederherstellung live
```

---

## 5. Betriebshandbuch (ab 22.10.2026)

**Täglich (automatisch):** `backup-offsite.yml` 03:00 UTC → zwei Entwurfs-Releases im privaten Backup-Repo.

**Bei Rot (`backup-einrichtung`):** Alerting verlinkt direkt auf Checkliste E1–E8 + Anleitung. „Zuerst E8“ beachten. Kein `workflow_dispatch`-Neustart ohne Fix.

**Bei Gelb/Rot (`backup-frist` / Frische-Wache):**

| Signal | Bedeutung | Handlung |
|---|---|---|
| E2/E5 gelb (30 d) | Token läuft in <30 Tagen ab | Token erneuern (Anleitung „Zugänge erneuern“), Secret ersetzen, `Run workflow` |
| E2/E5 rot + Frische rot | Token abgelaufen, Backup ausgeblieben | Sofort wie oben + Frische prüfen |
| Frische gelb (36 h) | Ein Tag ohne Backup | Scheduler-Hänger? `gh workflow view` + Actions-Log prüfen |
| Frische rot (52 h) | Zwei Tage ohne Backup | Wie oben + Issue bleibt offen bis frisches Release |

**Vierteljährlich (manuell, 15 Min.):**

```bash
bash scripts/restore_drill.sh --repo frank-hartung/franksfinanzcheck-backup
# → KV + Git entschlüsselt, Zähler + 20 Artikel + Rechtsseiten + Hugo-Build bewiesen
```

**Vor jedem Release/Token-Tausch:**

```bash
npm run backup:check
npm run test:backup
```

---

## 6. Dauerhaftigkeit (warum es hält)

| Mechanismus | Verankert in | Bricht bei Regression |
|---|---|---|
| 403-Präzision | `backup_einrichtung.py` E2 + Selbsttest F4 | Test rot → PR blockiert |
| Frische-Messung | `backup_freshness_guard.py` + 12 Fallgruppen | Selbsttest rot |
| SLA/RPO/RTO | `ANLEITUNG` + `INFRASTRUKTUR.md` + `CLAUDE.md` | `test_backup_einrichtung.AnleitungVertrag` prüft Link-Gleichheit + E1–E8-Tabelle |
| Alle Präfixe | `kv_backup.py` Kopf + `ANLEITUNG` SLA-Tabelle | Doku-Test prüft E1–E8 + `restore_drill.sh --remote` |
| T6-Ausnahme | `ki_transportweg.py` + TransportVertrag | `test_ki_transportweg` rot bei undeklarierter API |
| Kurzbefehle | `package.json` manifest-geschützt | `manifest_guard.py` L2 rot bei Lock-Drift |

Ein Junior-PR, der z. B. `PRAEFIXE` in der Frische-Wache ändert, bricht den Selbsttest. Ein PR, der 403 wieder generisch macht, besteht den nächsten `test:backup`-Lauf nicht. Die Anleitung kann nicht ohne die Prüfer-Links divergieren – Test erzwingt wörtliche Gleichheit.

---

## 7. Offene Inhaber-Aufgabe (einmalig, ~10 Min.)

Der Agenten-Zugang kann keine Secrets setzen. **Nach dem Merge dieses Stands:**

1. **Noch heute** `docs/ANLEITUNG-OFFSITE-BACKUP.md` Schritt 1–7 abarbeiten (Environment `backup` zuerst absichern, dann Secrets). Der erste grüne Lauf schließt #761 automatisch (Job `resolve` in `alert-on-failure.yml`).
2. **Danach** einmal `bash scripts/restore_drill.sh --repo …` fahren – grüner Drill ist der operative Abnahmenachweis.
3. **Optional** `npm run backup:frische` in einen bestehenden täglichen Watchdog (z. B. `frankautoops-report`, `bot-watchdog`) aufnehmen – dann ist RPO nicht nur dokumentiert, sondern gemessen.

Bis dahin bleibt #761 offen und wird bei jedem roten Lauf mit aktuellem Rat nachgeführt – kein Handkommentar nötig.

---

**Ergebnis:** Sicherung WF-9E5A ist ab diesem Stand nicht nur „grün machbar“, sondern **betrieblich überwachbar (Frische), fachlich präzise (403), abnahmefähig (SLA/RPO/RTO + Abdeckung) und regressionsgeschützt (Tests + Manifest + KI-Transport)** – Highend-Niveau einer Profi-Agentur, dauerhaft.
