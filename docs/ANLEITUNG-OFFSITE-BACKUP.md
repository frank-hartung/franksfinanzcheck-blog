# Anleitung: Offsite-Backup einrichten, prüfen, wiederherstellen

> Vorgang WF-9E5A · Meldung #923 · Stand 07.11.2026 (Selbstheilung, WF-3150 / #1030)
> Workflows `.github/workflows/backup-offsite.yml` + `backup-frischwache.yml` · Prüfer `scripts/backup_einrichtung.py` ·
> Frische-Wache `scripts/backup_freshness_guard.py` · **Selbstheilung `scripts/backup_selbstheilung.py`** ·
> Probe `scripts/restore_drill.sh` · Export `scripts/kv_backup.py` ·
> Einrichtungs-Wizard `scripts/backup_einrichten_wizard.sh`

### Integrität des Exports (12.11.2026)

Der Export bricht ab, wenn eine KV-Seite ungültig ist, ein Cursor wiederholt
wird oder ein angeforderter Wert fehlt bzw. kein Text ist. Ein fehlgeschlagener
Bulk-Abruf fällt nicht mehr auf Einzelabrufe zurück: Deren Fehlerantworten
konnten früher als gesicherter Wert erscheinen. D1-Tabellen mit Sonderzeichen
im Namen werden ebenfalls exportiert, statt still ausgelassen zu werden.
Die Gegenproben laufen im Backup-Job und mit `npm run test:backup`.

KV-Listen und Werte werden zeitlich nacheinander gelesen, nicht als atomarer
Snapshot; gleichzeitige Änderungen können zu einem Abbruch führen und müssen
durch einen weiteren Lauf erneut gesichert werden.

**Einrichtung am 12.11.2026:** Der Inhaber hat die Einrichtung abgeschlossen;
[Backup-Lauf 43216033861](https://github.com/frank-hartung/franksfinanzcheck-blog/actions/runs/43216033861)
und [Frischwache 43236761664](https://github.com/frank-hartung/franksfinanzcheck-blog/actions/runs/43236761664)
waren erfolgreich. Der KV-Export und das Git-Bundle wurden separat lokal
entschlüsselt und strukturell geprüft; ein Hugo-Build und ein tatsächlicher
Cloudflare-Rückimport wurden nicht durchgeführt. D1 war nicht eingerichtet.
Die ältere Diagnose auf dieser Seite beschreibt den damaligen Stand. Eine
unabhängige zweite Kopie außerhalb des GitHub-Kontos ist noch einzurichten.

## Kurz: Was ist zu tun?

Die nächtliche Sicherung der Abonnenten und Einwilligungsnachweise (Job
„KV-/D1-Backup“) bleibt **absichtlich rot**, falls die Zugänge unten nicht
korrekt eingerichtet sind. Das kann nur der Inhaber: An Secrets und an das Cloudflare-Konto kommen
Agenten nicht heran, und das ist auch richtig so. Aufwand: etwa 10 Minuten,
alle Links sind vorbelegt.

| # | Was | Wohin | Prüfpunkt |
|---|---|---|---|
| 1 | Environment `backup` absichern (nur `main`) – **zuerst** | Settings → Environments → `backup` | E8 |
| 2 | Privates Backup-Repository | Variable `BACKUP_REPO` (Repository) | E1 |
| 3 | Passphrase (zufällig, 32+ Zeichen) | Secret `BACKUP_PASSPHRASE` (Environment `backup`) | E3 |
| 4 | GitHub-Schreibzugang (fine-grained, 366 Tage) | Secret `BACKUP_REPO_TOKEN` (Environment `backup`) | E2 |
| 5 | Cloudflare-Lesezugang (nur KV lesen) | Secret `CF_KV_BACKUP_TOKEN` (Environment `backup`) | E5 |
| 6 | ID des KV-Namespace ABO | Variable `KV_NAMESPACE_ID_ABO` (Repository) | E6 |
| – | Cloudflare-Konto-ID | Secret `CLOUDFLARE_ACCOUNT_ID` – **schon vorhanden** | E4 |
| – | optional: D1-Datenbank (Klick-Zähler) | Variable `D1_DATABASE_ID` (Repository) – nur wenn der Klick-Zähler mitgesichert werden soll | E7 |

**Erst absichern, dann befüllen:** Schritt 1 kommt vor jedes Secret. Sonst
liegen die Zugänge, und sei es nur für Minuten, in einem Environment, das
jeder Branch nutzen darf. Die Einrichtungsprüfung im Lauf setzt denselben
Hinweis an den Anfang ihrer Liste („Zuerst E8“), solange das zutrifft.

**Komfort-Weg (seit 25.10.2026, Kurzbefehle seit 26.10.2026):** Statt der
sechs Klickstrecken führt der Wizard am eigenen Rechner interaktiv durch
dasselbe Vorgehen (erst E8, dann E1–E7; Geheimnisse werden verdeckt
abgefragt, nie geloggt; PAT-/Cloudflare-Formulare werden vorbelegt
geöffnet):

```bash
npm run backup:einrichten     # interaktiv durch E8 + E1–E7 (bash scripts/backup_einrichten_wizard.sh)
npm run backup:status         # aktuellen Stand E1–E8 prüfen, ohne etwas zu ändern (--check)
```

In CI verweigert sich der Wizard bewusst (kein Mensch, kein TTY) – die
Einrichtung bleibt eine Inhaber-Aufgabe am eigenen Rechner. Beide Wege
enden an derselben Stelle: Der erste grüne Lauf schließt die offene
WF-9E5A-Meldung automatisch.

Danach **ist kein Handbefehl mehr nötig** (seit 07.11.2026, WF-3150 / #1030):
Der nächste Lauf der Frischwache (täglich 13:00 UTC) sieht, dass noch keine
Sicherung existiert, stößt „Offsite-Backup“ selbst an und misst danach
erneut – grün wird er erst mit frischem Release (Abschnitt „Selbstheilung“).
Wer nicht bis 13:00 UTC warten will: Actions → „Offsite-Backup“ →
„Run workflow“ (Branch `main`). Die offene Meldung schließt sich beim ersten
grünen Lauf von selbst.

**Zusätzliche Laufzeit-Schranke:** Beide Backup-Jobs und die Frische-Wache
haben zusätzlich eine explizite Job-Bedingung auf
`refs/heads/main`. Ein manueller Start auf einem Feature-Branch erhält damit
keine Environment-Secrets, selbst wenn die E8-Branch-Policy versehentlich
entfernt wurde. Das ersetzt **nicht** Schritt 1: Das Environment muss
weiterhin explizit nur `main` zulassen, bevor Secrets eingetragen werden.

**Dringlichkeit:** Das Anmeldeformular ist geschaltet (`newsletterFormAction`
in `hugo.toml`), und der Worker antwortet (Newsletter-Lauf vom 13.10.2026:
0 aktive Abonnenten). Jede Anmeldung erzeugt einen Einwilligungsnachweis
(Art. 7 Abs. 1 DSGVO), der ohne diese Einrichtung **nur** in Cloudflare
liegt. Deshalb jetzt einrichten, vor den ersten Anmeldungen.

### Live-Status 07.11.2026 – WF-9E5A #923 (aktuell)

Gegen die echte GitHub-API geprüft am 07.11.2026, 10:00–11:00 UTC:

| Prüfung | Ergebnis |
|---|---|
| Offsite-Lauf `42359904795` (07.11., 09:28 UTC) | Job `KV-/D1-Backup` **failure** in „Voraussetzungen prüfen“ – gewollt, Einrichtung fehlt. Job `backup` **success** – aber siehe nächste Zeile: |
| Annotations des grünen Jobs | „Kein dauerhaftes Offsite-Ziel gesetzt“ und „Kein BACKUP_PASSPHRASE“ – der grüne Job hat **nichts gesichert** |
| Einrichtungsprüfung (live) | E1, E2, E3, E4, E5, E6 offen; E7 optional; E8 offen (`protection_rules: []`) |
| 24 Läufe 15.10.–07.11. | **alle** `failure`, Startzeiten 07:37–10:28 UTC (Soll 03:00) |
| Frischwache `42282938395` (06.11., 19:48 UTC) | **failure**; der Rückweg-Nachweis stand als `skipped` im Lauf (sechs Läufe in Folge) |
| Schreib-Endpunkte (Variablen, Secrets, Environment) | weiterhin `403 Resource not accessible by integration` – nichts erfunden, nichts gesetzt |
| Ziel-Repository `frank-hartung/franksfinanzcheck-backup` | **404** – existiert nicht |

**Drei Befunde code-seitig dauerhaft geheilt** (Einzelheiten und Belege in
`WARTUNG-BACKUP-WF-9E5A-HIGHEND-2026-11-07.md`):

1. **Der grüne Leerlauf** – ein Job meldet Erfolg, ohne etwas zu sichern.
   Jetzt eigen gemessen (`backup_selbstheilung.py`, Klasse `leerlauf`, Exit 4)
   und mit eigenem Rat im Fehler-Alerting (`backup-leerlauf`).
2. **Der übersprungene Nachweis** – der Rückweg-Nachweis stand in sechs
   Läufen als `skipped`; ein Nachweis hinter einem roten Vorgänger ist keiner.
   Er läuft jetzt mit `!cancelled()` und benennt, was ohne Einrichtung nicht
   prüfbar ist.
3. **Der fehlende Lauf** – Verspätungen von 4½ bis 7½ Stunden sind belegt.
   Die Selbstheilung holt den Lauf per Dispatch nach und **beweist** ihn über
   die Läufe-Liste (ein „angenommen“ der API zählt nicht).

Die Inhaber-Einrichtung (E1–E8) bleibt der einzige funktionale Blocker.
### Live-Status 07.11.2026 – WF-3150 / #1030 (aktuell)

Gegen die echte GitHub-API geprüft am 07.11.2026 (Vormittag UTC):

| Prüfung | Ergebnis |
|---|---|
| Frischwache `42282938395` (06.11., 20:48 UTC) | **failure** im Schritt „Voraussetzungen prüfen“ – gewollt (fail-closed), Einrichtung fehlt weiter |
| Offsite-Lauf `42359904795` (07.11., 09:31 UTC) | **failure**, derselbe Schritt – 12 Läufe in Folge (22.10.–07.11.) mit identischer Ursache |
| Environment `backup` | `protection_rules: []`, `deployment_branch_policy: null` → **E8 offen** (Annotation im Lauf) |
| Repository `frank-hartung/franksfinanzcheck-backup` | **404** – existiert nicht (E1/E2) |
| Variablen/Secrets (Agenten-Token) | `403 Resource not accessible by integration` – nichts erfunden, nichts gesetzt |
| Lauf-Annotationen der Frischwache | E1, E2, E3, E5, E6 fehlen · E4 vorhanden · E8 Hinweis · **kein** Fehlalarm über nicht gesetzte Namen |

**Die Lage ist unverändert die eines Einrichtungsbefunds, nicht eines Code-
fehlers** – und genau deshalb war die bisherige Wache zu wenig: Sie konnte
den Ausfall nur MELDEN. Seit dem 07.11.2026 heilt der Lauf den operativen
Teil selbst (nächster Abschnitt). Was der Code **nicht** kann und nicht
können soll: ein privates Repository anlegen, Secrets erzeugen oder ein
Environment absichern – das ist und bleibt eine Inhaber-Aufgabe
(`403 Resource not accessible by integration` ist die Grenze, nicht ein Bug).

Einzelheiten, Messungen und Verträge:
`WARTUNG-BACKUP-WF-3150-1030-SELBSTHEILUNG-HIGHEND-2026-11-07.md`.

### Live-Status 03.11.2026 – WF-9E5A #923 (Archiv)

Gegen die echte GitHub-API geprüft am 03.11.2026 (Vormittag UTC):

| Prüfung | Ergebnis |
|---|---|
| Offsite-Lauf `41428440948` (02.11., 10:23 UTC) | unverändert **failure** im Schritt „Voraussetzungen prüfen (fail-closed)“ – gewollt, Einrichtung fehlt |
| Erwarteter Lauf 03.11., 03:00 UTC | zum Prüfzeitpunkt **noch nicht eingetroffen** – dasselbe belegte Scheduler-Bild wie 22.10.–02.11. (Verspätungen bis ~7 h), RPO-Toleranz 52 h deckt es |
| Frischwache `41533983322` (02.11., 22:04 UTC) | **failure** mit Runbook `backup-einrichtung` – das fail-closed-Verhalten vom 02.11. greift im Live-Betrieb |
| Alarme | `#923` (Offsite) und `#1030` (Frischwache) offen, jüngster Lauf jeweils nachgeführt, Rat korrekt |
| Environment `backup` / Ziel-Repo | unverändert ohne Schutzregeln / **404** – Inhaber-Einrichtung weiterhin der Blocker |

Zwei Befunde **code-seitig dauerhaft geheilt** (Einzelheiten und Belege in
`WARTUNG-BACKUP-WF-9E5A-HIGHEND-2026-11-03.md`, Verträge in
`scripts/tests/test_backup_einrichtung.py`, Klasse `FrischwacheEinrichtungVertrag`):

1. **Die Frischwache prüfte Namen, die sie nie erhielt** (Spiegel fehlte):
   E4 meldete live „fehlt“, obwohl `CLOUDFLARE_ACCOUNT_ID` eingerichtet ist.
   Nach einer abgeschlossenen Einrichtung wären E1–E7 dort **für immer rot**
   geblieben – Dauer-Fehlalarm. Der Job erhält jetzt denselben
   Umgebungs-Spiegel wie der KV-Job (E1–E7), und E8 läuft mit dem Lauf-Token
   (`actions: read`), weil der fein eingeschränkte Ziel-Token die Regeln des
   Quell-Repos definitionsgemäß nicht lesen darf.
2. **Selbsttests erzeugten echte Fehler-Annotationen:** `kv_backup.py
   --selftest` entließ drei `::error::`/`::warning::`-Zeilen simulierter
   Ausfälle in echte Läufe (im roten UND im grünen Lauf sichtbar). Die
   Simulation fängt sie jetzt ein **und** beweist zugleich, dass die Meldungen
   im echten Lauf weiterhin ausgegeben werden.

Nach dem Abschluss der Inhaber-Einrichtung (unten, Schritte 1–8) gilt
unverändert als Abnahme: ein grüner `KV-/D1-Backup`-Job auf `main`, ein
privates Entwurfs-Release `kv-backup-*` mit Größen-/Draft-Nachweis und ein
bestandener Restore-Drill – ergänzt seit dem 03.11. um die reflexive Probe:
**die Frischwache muss danach ebenfalls grün werden** (Job „Backup-Frische
pruefen“), sonst läge ein viertes Problem vor.

### Live-Status 02.11.2026 – WF-9E5A #923 (Archiv)

Gegen die echte GitHub-API geprüft am 02.11.2026, 09:20 UTC:

| Prüfung | Ergebnis |
|---|---|
| Lauf `41295239096` (01.11., 09:56 UTC) | `backup`-Job **success**, `kv-backup` **failure** in „Voraussetzungen prüfen“ |
| Zehn Läufe 23.10.–01.11. | **alle** `failure` im selben Schritt – derselbe Zustand wie am 15.10. |
| Erwarteter Lauf 02.11., 03:00 UTC | **nicht vorhanden** (Scheduler-Aussetzer, nicht nachgeholt) |
| Frischwache `41335523844` (01.11., 18:13 UTC) | **success** – obwohl E1/E2 offen sind und keine einzige Sicherung existiert |
| Environment `backup` | `deployment_branch_policy: null`, `protection_rules: []` (E8 offen) |
| Repository `frank-hartung/franksfinanzcheck-backup` | **404** – existiert nicht |
| Variablen/Secrets (Agenten-Token) | `403 Resource not accessible by integration` |

Daraus zwei Befunde, die dieser Stand geheilt hat (Einzelheiten und Belege in
`WARTUNG-BACKUP-WF-9E5A-HIGHEND-2026-11-02.md`):

1. **Die Frischwache war grün, ohne etwas zu überwachen.** Ihr Schritt
   „Einrichtung als Kontext“ endete fest mit `exit 0`; ein fehlendes Ziel war
   nur eine `notice` im Log. Seit diesem Stand ist der Schritt rot
   („Voraussetzungen prüfen“, eigene Klasse `backup-einrichtung`).
2. **Der Export konnte einen Fehler in „leer“ verwandeln.** Eine D1-Antwort
   mit `success: false` wurde zur leeren Tabelle, ein KV-Export ohne
   Schlüssel bestand die Probe, `--wrangler-bulk` schrieb eine leere
   Rückspiel-Datei mit Exit 0. Alles drei ist jetzt fail-closed.

### Live-Status 01.11.2026 – WF-9E5A #923 (Archiv)

Der Lauf `41187477202` (31.10.2026) ist **weiterhin im Schritt
„Voraussetzungen prüfen“ rot** – und das ist richtig. Die Annotationen nennen
unverändert E1 `BACKUP_REPO`, E2 `BACKUP_REPO_TOKEN`, E3 `BACKUP_PASSPHRASE`,
E5 `CF_KV_BACKUP_TOKEN` und E6 `KV_NAMESPACE_ID_ABO` als fehlend; E8
(Environment „backup“) steht jedem Branch offen (`deployment_branch_policy:
null`, keine Branch-Policy). E4 ist vorhanden, E7 bleibt optional.

Am 01.11.2026 wurden diese fünf offenen Punkte **erneut live geprüft und
bestätigt** (GitHub-API des Repos): E1–E3/E5/E6 sind ohne Inhaber-Zugangsdaten
nicht herstellbar, und die Schreib-Endpunkte für Variablen, Secrets,
Repositories und Environment-Policies antworten dem Agenten-Token mit
`403 Resource not accessible by integration`. Es wurden **keine** Secrets,
Variablen, Repositories oder Environment-Regeln erfunden, überschrieben oder
in Chat/Repository abgelegt.

Was in diesem Stand **code-seitig** dauerhaft behoben wurde, ist die Klasse
„grün, ohne geprüft zu haben“ im Rückweg-Beweis – siehe Abschnitt
„Wiederherstellung“ (Exit 2 statt „bestanden“, eigener Alarm-Rat
`backup-restore`, automatische Gegenprobe in der Frischwache) und
`WARTUNG-BACKUP-WF-9E5A-HIGHEND-2026-11-01.md`.

### Live-Status 29.10.2026 – WF-9E5A #923 (Archiv)

Der aktuelle rote Lauf `40847586847` ist **kein Fehler im Exportcode** und
kein Fall für einen Neustart. Die fail-closed-Prüfung hat korrekt festgestellt,
dass die Inhaber-Einrichtung noch fehlt: E1 `BACKUP_REPO`, E2
`BACKUP_REPO_TOKEN`, E3 `BACKUP_PASSPHRASE`, E5 `CF_KV_BACKUP_TOKEN` und E6
`KV_NAMESPACE_ID_ABO` fehlen; E4 ist vorhanden, E7 bleibt optional. E8
(Environment nur für `main`) ist ebenfalls noch nicht nachgewiesen. Bis die
sieben Inhaber-Schritte oben erledigt sind, bleiben Abonnenten und
Einwilligungsnachweise **ungesichert**. Ein erneuter Lauf ohne Einrichtung
würde denselben sicheren Fehler erzeugen und schließt #923 nicht.

## Was gesichert wird – und wo

| Job | Inhalt | Verschlüsselung | Ziel | Aufbewahrung |
|---|---|---|---|---|
| `backup` | Git-Bundle von `main` + Arbeitskopie (öffentlicher Code) | AES-256-CBC, PBKDF2 200 000 | privates Repo, **Entwurfs**-Release `backup-…` | 14 |
| `kv-backup` | Workers KV `ABO`: `abo:`, `token:`, `nachweis:` (+ optional D1) | AES-256-CBC, PBKDF2 600 000 | privates Repo, Entwurfs-Release `kv-backup-…` | 35 (5 Wochen) |

Die Grundsätze stammen aus dem Sicherheitsaudit (M-11) und der
Marken-Oberflächen-Wache vom 20.09.2026:

- **Nie öffentlich.** Vor jedem Upload wird live geprüft, dass das Ziel privat ist.
- **Nie als Actions-Artefakt.** Bei öffentlichen Repos kann jeder angemeldete
  GitHub-Nutzer Artefakte laden.
- **Jede Verschlüsselung mit Rückweg-Probe.** Die Datei wird testweise
  entschlüsselt und bytegenau verglichen.
- **Jeder Upload wird nachgelesen.** Geprüft werden die Größe und ob das
  Release ein Entwurf ist.
- **Fehlt etwas, ist der Lauf rot.** Kein Schein-Grün.

### Betriebszusagen (Profi-Niveau: SLA · RPO · RTO · Abdeckung)

| Zusage | Wert | Beleg |
|---|---|---|
| **RPO** (max. Datenverlust) | 24 h + Scheduler-Toleranz (52 h) | Täglich 03:00 UTC; GitHub-Scheduler belegt 09:53–12:03 MESZ; **automatisierte** Frischwache `backup-frischwache.yml` (13:00 UTC) rot ab 52 h, gelb ab 36 h. Seit 07.11.2026 **heilt sie selbst**: ab 26 h stößt sie die Sicherung an (Budget 3/24 h) und misst erneut |
| **RTO** (Wiederherstellung) | < 30 Min. für KV, < 60 Min. für Repo | Probe `restore_drill.sh` in < 5 Min.; Ernstfall-Anleitung unten mit `gh release download` + `openssl` + `wrangler kv bulk put --remote` |
| **Aufbewahrung** | Repo 14, KV 35 Releases (Entwürfe) | `backup-offsite.yml` KEEP=14 / 35; älteste darüber automatische Löschung |
| **Verschlüsselung** | AES-256-CBC/PBKDF2, Bundle 200k, KV 600k | Workflow + Prüfer `backup_einrichtung.py` E3 (≥ 20 Zeichen, empfohlen 32+) |
| **Prüfung** | 8 Live-Punkte E1–E8 je Lauf, 3 Frist-Stufen, 19 Fallgruppen Selbsttest | `backup_einrichtung.py --selftest`, `test_backup_einrichtung` (47 Tests, inkl. Wizard- und Rückweg-Vertrag) |
| **Ablauf-Warnung** | 30 Tage gelb, 14 Tage rot (nach Sicherung) | `BACKUP_FRIST_TAGE` → letzter Schritt `Fristwarnung` + Alerting `backup-frist` |
| **Operative Wache** | Täglich 13:00 UTC, beide Familien `backup-*` + `kv-backup-*`, inkl. Inhalts-Nachweis (Assets) | `backup_freshness_guard.py` (15 Fälle) + `backup_selbstheilung.py` (22 Fälle, Selbstheilung mit Budget) + Workflow `backup-frischwache.yml` → Alerting `backup-frisch` |

**Was gesichert wird – vollständig:**

| KV-Präfix | Inhalt | DSGVO-Relevanz | Quelle |
|---|---|---|---|
| `abo:` | Aktive Abonnenten (Status, Zeitstempel) | Art. 7 (1) Nachweis der Einwilligung | Worker `ABO` |
| `token:` | Bestätigungs-/Abmelde-Tokens (→ abo:) | Technisch für Double-Opt-In | Worker `ABO` |
| `nachweis:` | Einwilligungsnachweis (IP, Zeit, Text-Stand) | Art. 7 (1) Nachweispflicht | Worker `ABO` |
| `budget:` | Tagesbudget Anmeldung/Feedback (TTL) | Betrieb, nicht personenbezogen | Worker `ABO` |
| `exportlog:` | Export-Protokoll (TTL 30 d) | Betrieb | Worker `ABO` |
| `takt:` | Taktgeber letzte Läufe | Betrieb | Worker `ABO` |
| `feedback:` + `fbtag:` | Artikel-Feedback je Tag | Betrieb | Worker `ABO` |
| D1 | Klick-Zähler (optional) | Betrieb | Cloudflare D1 |

> Alle KV-Schlüssel werden gesichert – nicht nur die drei Pflicht-Präfixe.
> Die Probe `kv_backup.py --pruefen` und `restore_drill.sh` beweisen die
> Wiederherstellbarkeit (Struktur, keine verwaisten Tokens, Zähler).

**Was NICHT gesichert wird (bewusst, mit Mitigation):**

| Nicht im Backup | Warum | Mitigation |
|---|---|---|
| GitHub Issues/PRs/Discussions | Nicht im Git, API-limitiert | Wöchentlich manuell exportieren oder `gh issue list` archivieren (nicht automatisiert – geringes Volumen) |
| GitHub Secrets/Variablen | GitHub gibt Secrets nie heraus | In 1Password dokumentieren (Anleitung Schritt 3–5) |
| Cloudflare-Zone (DNS, Regeln) | Nicht im KV, nicht im Repo | `docs/SICHERHEIT-BETRIEB-RUNBOOK.md` A1 dokumentiert Sollstand; `edge:freigabe` misst |
| `gh-pages` Branch | Regenerierbar (Build-Artefakt) | Quelle `main` ist gesichert; `deploy.yml` baut neu |
| Worker-Logs (> 200k Zeilen/Tag) | Flüchtig (Free 1 d) | Nicht kritisch; bei Incident vorher exportieren |

**Frische operativ überwachen (automatisiert seit 24.10.2026):**

```bash
# Lokal oder in CI (braucht Lese-Token auf Backup-Repo):
python3 scripts/backup_freshness_guard.py --repo frank-hartung/franksfinanzcheck-backup
python3 scripts/backup_freshness_guard.py --selftest   # 15 Fälle offline (inkl. Hülle ohne Inhalt)
npm run backup:frische   # Kurzform
```

- **Automatisch:** Workflow `backup-frischwache.yml` läuft täglich **13:00 UTC** (nach
  dem 03:00 UTC-Sicherungslauf + Puffer für GitHub-Scheduler-Verspätung bis 12:03 MESZ).
  Urteil `fehler` (>52 h oder fehlende Familie) → Workflow rot → Alerting `backup-frisch`
  mit RPO-Rat; `warnung` (>36 h) → gelber Hinweis in der Summary (Frühwarnung).
- **Manuell:** Zusätzlich vor Releases oder nach Token-Tausch: `npm run backup:frische`.

Die Frische-Wache ergänzt E1–E8: Sie misst, ob die Sicherung *jüngst* wirklich
lief (täglich erwartet, 52 h Toleranz). Ein grünes `backup_einrichtung` ohne
frisches Backup ist eine Konfigurations-, aber keine Betriebsgarantie – deshalb
laufen beide Wachen unabhängig.

### Selbstheilung – die Wache stößt die Sicherung selbst an (seit 07.11.2026)

Eine Wache, die nur meldet, ist eine Warteschlange. Die Frischwache schließt
den Kreis jetzt selbst:

1. **Messen** (`backup_freshness_guard.py`): beide Release-Familien, Entwürfe
   eingeschlossen. Ein Release **ohne Datei** (0 Assets) gilt nicht mehr als
   Sicherung – eine Hülle ist keine Sicherung.
2. **Entscheiden** (`backup_selbstheilung.py`, reine Funktion): Es wird nur
   angestoßen, wenn das **Tagesfenster verpasst** ist (`> 26 h`), und nur dann,
   wenn keine Sicherung läuft (kein `queued`/`in_progress`), der Mindestabstand
   von 15 Minuten zum letzten Lauf eingehalten ist, das Budget von **3
   Anstößen je 24 h** nicht erschöpft ist und die Lauf-Historie **lesbar** war.
   Ist die Historie nicht lesbar, wird **nicht** angestoßen (ein blinder
   Anstoß könnte doppelt sichern).
3. **Anstoßen**: genau ein `workflow_dispatch` von `backup-offsite.yml` auf
   `main` – der geprüfte Weg, keine zweite Sicherungslogik.
4. **Erneut messen**: Grün gibt es nur mit frischem Release. Ein angestoßener
   Lauf ist kein Nachweis; ein gescheiterter Lauf bleibt rot, mit Link.

| Grenze | Wert | Warum |
|---|---|---|
| Heilung ab | **26 h** | Täglicher Lauf 03:00 UTC, Messung 13:00 UTC: gesund ≤ 17 h (10 h + belegte Scheduler-Verspätung), ausgefallen ≥ 34 h. 26 h heilt den Ausfall **am selben Tag** statt erst bei der 52-h-Meldung |
| Meldung (gelb/rot) | **36 h / 52 h** | unverändert die SLA-Grenzen aus der Tabelle oben |
| Mindestabstand | **15 Min.** | kein zweiter Anstoß, während der letzte Lauf noch frisch ist |
| Budget | **3 Anstöße / 24 h** | kein Dauerfeuer bei einem echten Fehler; danach bleibt es Rot **mit Grund** |
| Rechte | `actions: write` (Lauf-Token) | nur für `POST …/dispatches`; GitHub kennt kein feineres Recht. Messung und Selbsttests laufen ohne |

**Lokal (ändert nichts, wenn `--probe`):**

```bash
python3 scripts/backup_selbstheilung.py --probe        # messen + entscheiden, kein Anstoß
python3 scripts/backup_selbstheilung.py --heilen       # mit Anstoß (braucht actions: write)
python3 scripts/backup_selbstheilung.py --selftest     # 22 Fallgruppen, offline
npm run backup:selbstheilung                           # Kurzform der Probe
```

**Was die Selbstheilung ausdrücklich NICHT tut:** Sie legt kein Repository an,
erzeugt keine Secrets, ändert keine Environment-Regel und schaltet keinen
Schutz ab. Fehlt die Einrichtung (E1–E8), bleibt der Lauf rot im Schritt
„Voraussetzungen prüfen“ – mit Einrichtungs-Rat, nicht mit Frische-Rat.

### Eine Ursache, ein Rat – und kein Abbruch mitten in der Heilung

Zwei Zusagen, die seit dem **10.11.2026** gelten (Vorgang WF-3150 / #1030)
und die man an einem roten Lauf nachprüfen kann:

**1. Der Leerlauf-Schritt rät nicht mehr.** Am 09.11.2026 (Lauf
`42715328453`) trug ein Lauf **zwei** rote Schritte mit **zwei**
verschiedenen Ratschlägen: „Voraussetzungen prüfen“ (richtig: E1–E8 offen)
und „Leerlauf prüfen“ (falsch: „ein Lauf ist grün, gesichert wurde nichts“ –
es war gar kein Lauf grün). Der zweite Schritt bekam den Befund des ersten
nie, obwohl der Prüfer den Parameter dafür seit dem 07.11. hatte.

Seitdem gilt: Der Schritt, der es weiß, sagt es – „Voraussetzungen prüfen“
schreibt die offenen Kennungen (`E1 … E8`) in seine Schritt-Ausgabe
`offene_einrichtung`, der Leerlauf-Schritt liest sie:

| Lage | Was der Leerlauf-Schritt tut |
|---|---|
| Einrichtung nachweislich offen | **ein Hinweis, kein zweiter Rat** – die Ursache trägt „Voraussetzungen prüfen“ |
| Einrichtung geprüft, nichts offen (`offene_einrichtung` leer) | der echte Leerlauf-Befund (Exit 4) bleibt unverändert scharf |
| gar keine Auskunft (Schritt nicht gelaufen) | **Exit 2, rot** – „weiß nicht“ ist kein Grün und kein Rat |

**Nachschärfung 12.11.2026:** Ein leerer Wert allein ist keine Auskunft –
GitHub liefert für eine Schritt-Ausgabe denselben leeren Text, wenn der
Schritt übersprungen wurde oder abgestürzt ist. Die Einrichtungsprüfung
schreibt deshalb zusätzlich `einrichtung_geprueft=ja`; fehlt dieser Beleg,
verwirft der Leerlauf-Schritt den Wert und endet rot (Exit 2). Erst damit ist
die dritte Zeile der Tabelle im Workflow tatsächlich erreichbar (Akte
`WARTUNG-BACKUP-WF-3150-1030-HIGHEND-2026-11-12.md`).

Lokal von Hand (`npm run backup:selbstheilung`) gibt es die Einrichtungslage
nicht; dort sagt der Aufruf das ausdrücklich: `--ohne-setup`.

**2. Der Heilungslauf wird nicht mehr abgewürgt.** `cancel-in-progress` galt
für *jeden* Lauf dieses Workflows. Seit die Wache selbst anstößt und bis zu
15 Minuten auf das Ergebnis wartet, brach ein nachfolgender Lauf genau diesen
Wartezustand ab – der einzige Schreiber im Kreis hat sich selbst verdrängt.
Jetzt darf nur ein `push`-Lauf (Code-Probe an einem Prüfer, ohne
Betriebsabsicht) einen anderen verdrängen; der **tägliche Lauf** und ein
**manueller „Run workflow“** laufen immer zu Ende.

## Einrichtung Schritt für Schritt

Ablage-Regel: **Secrets** ins Environment `backup` (Settings → Environments →
`backup` → „Environment secrets“), **Variablen** auf Repository-Ebene
(Settings → Secrets and variables → Actions → Variables). Beide Jobs des
Workflows laufen im Environment `backup` und sehen deshalb beides.

### Schritt 1 – Environment `backup` absichern (E8)

**Zuerst, bevor ein einziges Secret eingetragen wird.** Das Environment besteht
seit dem ersten Lauf am 15.10.2026, steht aber jedem Branch offen. Wer erst
befüllt und dann absichert, lässt die Zugänge eine Weile ungeschützt liegen.
(Fehlt es, unter „New environment“ mit dem Namen `backup` anlegen.)

Settings → Environments → `backup`: <https://github.com/frank-hartung/franksfinanzcheck-blog/settings/environments>

- **Deployment branches and tags → „Selected branches and tags“ → nur `main`.**
  Ohne diese Regel kommt jeder Branch an die Backup-Zugänge, etwa ein
  Arbeitszweig mit geänderter Workflow-Datei (Sicherheitsaudit F-07).
- **Keine „Required reviewers“.** Sonst wartet jeder nächtliche Lauf auf
  einen Klick und bricht nach 30 Tagen ab.

Der Wizard setzt die Branch-Policy über die GitHub-REST-Endpunkte für
Environment und Deployment-Branch-Policies (Environment `PUT`, Policies
`GET`/`DELETE`/`POST`). Er erhält eine vorhandene `main`-Regel oder legt sie
vor dem Entfernen weiterer Regeln an; sowohl Auflistung als auch Read-back
sind paginiert. Nur **genau eine Regel `main` vom Typ `branch`** gilt als
sicher. „Protected branches“ reicht nicht als Nachweis. Ist die API nicht
lesbar, fehlt eine Berechtigung oder bleibt eine fremde Regel übrig, bricht
der Wizard vor jedem Secret ab – eine manuelle „Erledigt?“-Bestätigung allein
reicht nicht.

Der Laufzeit-Prüfer liest diese Einstellungen bei jedem Lauf und meldet
Abweichungen als Hinweis; die Sicherung läuft trotzdem, damit ein E8-Befund
die eigentliche Sicherung nicht still überspringt. Solange Pflichtzugänge
fehlen und das Environment nicht nachweislich nur `main` zulässt, setzt er
„Zuerst E8“ an den Anfang der Prüfliste.

### Schritt 2 – Privates Backup-Repository anlegen (E1)

1. Vorbelegtes Formular öffnen – Sichtbarkeit **Private** ist gesetzt:
   <https://github.com/new?owner=frank-hartung&name=franksfinanzcheck-backup&visibility=private&description=Private+Sicherungen+%28verschl%C3%BCsselt%29>
   → „Add a README“ aktivieren (erster Commit als Grundlage für Releases)
   und „Create repository“ wählen. Eine Lizenz ist nicht nötig.
2. Repository-Variable anlegen: <https://github.com/frank-hartung/franksfinanzcheck-blog/settings/variables/actions> → „New repository
   variable“ → Name `BACKUP_REPO`, Wert `frank-hartung/franksfinanzcheck-backup`.

### Schritt 3 – Passphrase erzeugen (E3)

1. Im Passwort-Manager einen Eintrag „FranksFinanzcheck – Backup-Passphrase“
   anlegen und ein zufälliges Passwort mit **mindestens 32 Zeichen** erzeugen
   lassen. Alternativ im Terminal: `openssl rand -base64 33`.
2. **Erst speichern, dann eintragen.** Die Passphrase ist der einzige
   Schlüssel zu allen Sicherungen. Geht sie verloren, ist jede Sicherung
   wertlos. Sie gehört nie in einen Chat, ein Issue, einen Commit oder eine Mail.
3. Environment `backup` → „Add environment secret“ → Name `BACKUP_PASSPHRASE`.

Der Prüfer verlangt mindestens 20 Zeichen (E3). Die Länge selbst gibt er nie aus.

### Schritt 4 – GitHub-Schreibzugang (E2)

1. Vorbelegtes Formular öffnen:
   <https://github.com/settings/personal-access-tokens/new?name=ff-offsite-backup&description=Offsite-Backup%3A+Entwurfs-Releases+im+privaten+Backup-Repo+%28nur+dieses+Repo%29&target_name=frank-hartung&expires_in=366&contents=write>
   Vorbelegt sind Name, Beschreibung, Besitzer, **Ablauf 366 Tage** und das
   Recht **Contents: Read and write**.
2. **Repository access → „Only select repositories“ → nur
   `franksfinanzcheck-backup`.** Diese Auswahl lässt sich nicht vorbelegen und
   muss von Hand gesetzt werden. „All repositories“ wäre ein Generalschlüssel.
3. „Generate token“ klicken, den Token kopieren und im Environment `backup`
   als Secret `BACKUP_REPO_TOKEN` speichern.

Warum 366 Tage? GitHub schlägt sonst 30 Tage vor – dann stünde die Sicherung
nach einem Monat. Der Prüfer liest das Ablaufdatum bei jedem Lauf und weist ab
30 Tagen vorher darauf hin. 14 Tage vorher meldet sich das Alerting (siehe
„Zugänge erneuern“). Ein klassischer Token (`ghp_…`) funktioniert auch, sieht
aber **alle** Repositories – der Prüfer markiert ihn mit einem Hinweis.

### Schritt 5 – Cloudflare-Lesezugang (E5)

1. Vorbelegte Vorlage für einen Konto-Token öffnen:
   <https://dash.cloudflare.com/?to=/:account/api-tokens&permissionGroupKeys=%5B%7B%22key%22%3A%22workers_kv_storage%22%2C%22type%22%3A%22read%22%7D%5D&name=ff-kv-backup+%28nur+lesen%29>
   Vorbelegt sind das Recht **Workers KV Storage: Read** und der Name
   „ff-kv-backup (nur lesen)“. Nur dieses Konto auswählen und keine weiteren
   Rechte vergeben, schon gar keine Schreibrechte.
2. „Create Token“ klicken, den Token kopieren und im Environment `backup` als
   Secret `CF_KV_BACKUP_TOKEN` speichern.

Hinweise:

- Konto-Tokens (Account API Tokens) sind für Automationen gedacht und hängen
  nicht am persönlichen Login. Ein Nutzer-Token (My Profile → API Tokens) mit
  demselben Recht funktioniert ebenfalls; der Prüfer erkennt beide Arten.
- Soll der Klick-Zähler (D1) mitgesichert werden, braucht der Token
  zusätzlich **D1: Read**: <https://dash.cloudflare.com/?to=/:account/api-tokens&permissionGroupKeys=%5B%7B%22key%22%3A%22workers_kv_storage%22%2C%22type%22%3A%22read%22%7D%2C%7B%22key%22%3A%22d1%22%2C%22type%22%3A%22read%22%7D%5D&name=ff-kv-backup+%28nur+lesen%29>
- Bewusst **nicht** wiederverwenden: `CLOUDFLARE_API_TOKEN` (Workers AI) und
  `CF_WORKERS_DEPLOY_TOKEN` (Deploy, schreibend). Ein Backup braucht nur Lesen.

### Schritt 6 – ID des KV-Namespace ABO (E6)

1. Die ID im Cloudflare-Dashboard holen: Workers & Pages → Worker
   `ff-newsletter` → Settings → Bindings → KV-Namespace **ABO**.
   Alternativ: Storage & Databases → Workers KV (<https://dash.cloudflare.com/?to=/:account/workers/kv/namespaces>) oder im
   Terminal `npx wrangler kv namespace list`.
2. Als Repository-Variable `KV_NAMESPACE_ID_ABO` eintragen. Gemeint ist die
   ID (32 Hex-Zeichen), **nicht** der Name „ABO“.

Wichtig: Es muss **der Namespace sein, an den der laufende Worker sein
Binding `ABO` hat**. Sonst sichert der Job einen leeren Namespace. Zur
Kontrolle zeigt der Prüfer den Titel des Namespace an.

**Kopplung mit dem Worker-Deploy:** `worker-deploy.yml` nutzt dieselbe
Variable. Bisher überspringt er den Newsletter-Worker „mangels ID“. Sobald
sie gesetzt ist, versucht er bei der nächsten Änderung unter
`newsletter-worker/**` einen Deploy. Dafür braucht er `CF_WORKERS_DEPLOY_TOKEN`
im Environment `cloudflare-produktion` (siehe
`docs/ANLEITUNG-NEWSLETTER-EIGENBETRIEB.md`, Schritt 4). Die gemeinsame
Variable ist Absicht: So können Backup und Worker nie auf verschiedene
Namespaces zeigen – auch nicht nach dem geplanten Umzug in einen EU-Namespace.

### Schritt 7 – Lauf starten

Actions → „Offsite-Backup“ → „Run workflow“ → Branch `main`. Danach:

- In der Job-Zusammenfassung „Offsite-Backup – Einrichtungsprüfung“ sind alle
  Pflichtpunkte ✅.
- Im Backup-Repo stehen zwei Entwurfs-Releases (`backup-…` und `kv-backup-…`).
- Die offene Meldung schließt sich beim ersten grünen Lauf automatisch.

Danach einmal die Wiederherstellung proben (Abschnitt „Wiederherstellung“).

## Was der Lauf prüft (E1–E8) – und was bei Rot zu tun ist

| Punkt | Prüfung | Typischer Befund | Abhilfe |
|---|---|---|---|
| E1 | `BACKUP_REPO` gesetzt, Format `besitzer/name`, nicht das Blog-Repo | fehlt · falsches Format | Schritt 2 |
| E2 | Token gültig, Ziel erreichbar, **privat**, nicht archiviert, Ablaufdatum | 401: ungültig/abgelaufen · 404: Repo fehlt oder Token sieht es nicht · ÖFFENTLICH | Schritt 4 (bei 404: Repo im Token auswählen) |
| E3 | Passphrase mit mindestens 20 Zeichen | fehlt · zu kurz | Schritt 3 |
| E4 | Konto-ID mit 32 Hex-Zeichen | fehlt · Format | Dashboard → Workers & Pages, rechte Spalte |
| E5 | Cloudflare-Token aktiv (Nutzer- oder Konto-Token), Ablaufdatum | nicht anerkannt · abgelaufen · deaktiviert | Schritt 5 |
| E6 | Namespace-ID: Format, mit **diesem** Token lesbar | Name statt ID · 403: Recht fehlt · 404: falsches Konto | Schritt 6 bzw. Schritt 5 |
| E7 | optional: D1-Datenbank lesbar | nicht lesbar | D1: Read ergänzen oder Variable entfernen |
| E8 | Ausdrücklich ausgewählte Branch-Regel: genau `main` vom Typ `branch`; keine Pflicht-Freigabe | Hinweis (vor dem Befüllen: „Zuerst E8“); Wizard stoppt vor Secrets, wenn E8 nicht live bestätigt ist | Schritt 1 |

„GitHub-API nicht erreichbar“ oder „Cloudflare-API nicht erreichbar“ ist
meist vorübergehend: den Lauf später neu starten.

### Fehlerbilder

Diese Fehler treten in den Schritten nach der Prüfung auf:

- **„Ablage in … fehlgeschlagen“:** Der Token darf nicht schreiben. Prüfen,
  ob er „Contents: Read and write“ hat und das Backup-Repo ausgewählt ist
  (Schritt 4).
- **„unvollständig oder kein Entwurf … Teil-Release wird entfernt“:** Der
  Upload ist abgebrochen; die halbe Sicherung wurde wieder entfernt. Meist
  vorübergehend, also neu starten.
- **„Verschlüsselung nicht umkehrbar“:** ein Problem auf dem Runner. Neu
  starten; bleibt der Fehler, ein Issue mit Lauf-Link anlegen.
- **Export schlägt fehl (`kv_backup.py`):** entweder eine Störung bei
  Cloudflare (<https://www.cloudflarestatus.com>) oder der Token wurde
  zwischenzeitlich widerrufen. Der nächste Lauf prüft ihn erneut (E5).
- **Repo-Job: „nicht nachweislich privat (Antwort: UNBEKANNT, API: …)“:**
  „Not Found“ heißt, das Repo fehlt oder der Token sieht es nicht.
  „Bad credentials“ heißt, der Token ist ungültig oder abgelaufen.

## Selbstheilung – was das System selbst repariert (und was NICHT)

Seit 07.11.2026 (Vorgänge WF-9E5A / #923 und WF-3150 / #1030) enthält die
tägliche Frischwache **zwei** Schritte mit klarer Rollentrennung
(`scripts/backup_selbstheilung.py`):

| Schritt | Recht | Aufgabe |
|---|---|---|
| „Selbstheilung – fehlende Sicherung anstoßen (fail-closed)“ | Lauf-Token (`actions: write`) | **der einzige** Schritt, der anstößt (`--heilen`): messen → entscheiden → genau ein Dispatch → begrenzt warten → **erneut messen** |
| „Leerlauf prüfen – grüner Lauf ohne Sicherung (fail-closed)“ | Lauf-Token, **nur lesend** (`--leerlauf`) | misst auf **Job-Ebene** und am jüngsten Lauf **mit Schritten**, ob ein grüner Lauf tatsächlich gesichert hat |

Beide sind bewusst eng: Sie reparieren, was **beweisbar kaputt** ist und **ohne
jeden Zugang** repariert werden kann – alles andere benennen sie, statt es zu
erfinden. Zwei Heilschritte gab es bis zum 08.11.2026 versehentlich (ein
Merge-Rest aus beiden Vorgängen): Der zweite hätte im selben Lauf ein zweites
Mal anstoßen können. Jetzt gibt es genau **einen** Schreiber.

| Klasse | Was gemessen wird | Heilung |
|---|---|---|
| `scheduler` | Der nächtliche Lauf (Soll 03:00 UTC, Kulanz 4 h) fehlt – belegt sind Startzeiten von 07:37 bis 10:28 UTC | **Ja:** `workflow_dispatch` – und der Beweis ist ein **neuer Lauf** in der Läufe-Liste. Ein „angenommen“ der API (HTTP 204) zählt nicht. |
| `leerlauf` | Ein **Job** meldet Erfolg, obwohl weder `BACKUP_REPO` noch `BACKUP_PASSPHRASE` gesetzt sind – dann entsteht nur eine 7-Tage-Kurzzeitkopie im selben Konto | Nein – der Weg steht in den Schritten 2–4 |
| `scheinbeweis` | Ein Nachweis-Schritt steht als `skipped` im Lauf (GitHubs Standardbedingung `success()` schaltet ihn hinter einem roten Vorgänger ab) | Nein – das ist ein Code-Vertrag (der Rückweg-Nachweis läuft jetzt mit `!cancelled()`) |
| `einrichtung` | E1–E8 offen | **Nein** – Inhaber-Sache |

### Die Grenze: Was ausdrücklich NICHT geheilt wird

**E1–E8 werden nie automatisch „erledigt".** Ziel-Repository, Token,
Passphrase, Cloudflare-Konto, KV-Namespace und Environment-Schutz sind
Zugänge und Entscheidungen des Inhabers. Ein Agent kann sie nicht herstellen –
und ein erfundener oder stillschweigend „gesetzter" Wert wäre schlimmer als
der offene Befund, weil er eine Sicherung vortäuscht, die es nicht gibt.
Deshalb gilt unverändert: `npm run backup:einrichten` (E8 zuerst, dann
E1–E7).

Daraus folgt die ehrliche Lesart der Job-Zusammenfassung:

- **`scheduler` geheilt** heißt: Der Lauf ist nachgeholt **und** ein neuer
  Lauf ist sichtbar. Er kann inhaltlich trotzdem rot sein (Einrichtung fehlt) –
  dann ist die Ursache E1–E8, nicht der Scheduler.
- **`leerlauf` gemeldet** heißt: Der Job ist grün und **trotzdem ist nichts
  gesichert**. Gemessen wird auf JOB-Ebene, nicht am Gesamtlauf: Am 07.11. war
  der Lauf rot (KV-Job) und der sichernde Job grün – eine Messung auf
  Lauf-Ebene hätte den Befund genau an dem Tag verschluckt, an dem er zutraf. Das ist der wichtigere der beiden Zustände.
- **Exit 3** („nichts automatisch heilbar") ist kein Fehler des Systems,
  sondern die Ansage: Hier ist ein Mensch dran.
- **Exit 4** heißt: Ein Job meldet Erfolg, **gesichert wurde aber nichts**
  (Leerlauf). Das Fehler-Alerting führt dafür die eigene Klasse
  `backup-leerlauf` mit eigenem Rat – nicht „neu starten" (der nächste Lauf
  wäre genauso leer) und nicht „einrichten" (die Einrichtung kann vollständig
  sein und trotzdem nichts sichern).

Eine Heilung, die über diese Grenze hinausgeht, ist ein Fehler – der Vertrag
`SelbstheilungVertrag` in `scripts/tests/test_backup_einrichtung.py` prüft in
beide Richtungen (heilbare Klassen genau `scheduler`, keine Secret-Zugriffe,
kein `gh secret set`/`gh variable set`, Grenze in dieser Datei).

## Zugänge erneuern

Der Prüfer liest bei jedem Lauf die Ablaufdaten: bei GitHub aus der
Kopfzeile `github-authentication-token-expiration`, bei Cloudflare aus
`expires_on`.

| Resttage | Wirkung |
|---|---|
| 30 und mehr | nichts |
| unter 30 | gelber Hinweis in Prüfung und Zusammenfassung |
| unter 14 | Schritt „Fristwarnung“ wird rot und das Alerting meldet sich. **Die Sicherung des Tages ist trotzdem gelaufen.** |
| abgelaufen | Prüfung rot, keine Sicherung |

So wird erneuert:

- **GitHub-Token:** Settings → Developer settings → Fine-grained tokens →
  Token → „Regenerate token“ (Rechte und Repo-Auswahl bleiben erhalten).
  Danach den neuen Wert in `BACKUP_REPO_TOKEN` (Environment `backup`) ersetzen.
- **Cloudflare-Token:** API Tokens → Token → „Roll“. Danach den neuen Wert
  in `CF_KV_BACKUP_TOKEN` ersetzen.
- Anschließend „Run workflow“ starten; ein grüner Lauf schließt die Fristmeldung.

**Passphrase wechseln** nur mit Bedacht: Ältere Sicherungen bleiben mit der
**alten** Passphrase verschlüsselt. Deshalb beide im Passwort-Manager
behalten, mit dem Datum des Wechsels. Ist die Aufbewahrung abgelaufen
(35 Tage), wird die alte Passphrase nicht mehr gebraucht.

## Wiederherstellung

Voraussetzungen: `gh` (angemeldet mit `gh auth login`), `openssl` und
`python3`. Alle Befehle im Wurzelverzeichnis des Repos ausführen.

### Probe (nach der Einrichtung, danach vierteljährlich)

```bash
bash scripts/restore_drill.sh --repo frank-hartung/franksfinanzcheck-backup
```

Die Probe läuft so ab:

1. Sie holt die neuesten Sicherungen (Entwürfe eingeschlossen) und fragt die
   Passphrase verdeckt ab.
2. Sie entschlüsselt in ein Temp-Verzeichnis (Rechte 0700), das am Ende
   gelöscht wird.
3. Sie beweist, dass der KV-Export vollständig und konsistent ist
   (`kv_backup.py --pruefen`; im Log stehen nur Zähler).
4. Sie beweist, dass sich das Git-Bundle klonen lässt und Artikel und
   Rechtsseiten enthält.

Die Probe prüft das **Alter** der neuesten Sicherung mit denselben Grenzen wie
die Frischwache (`backup_freshness_guard.py`): über **36 h** eine Warnung, über
**52 h** Exit 1 – denn eine Sicherung, die die eigene RPO-Zusage reißt, ist
kein bestandener Rückweg (bis 01.11.2026 warnte sie erst ab 48 h und bestand
dann weiter). Mit `--nur-kv` oder `--nur-git` lässt sich die Probe eingrenzen.

**Kein Schein-Grün (01.11.2026, #923):** Ein Lauf ohne geprüfte Familie –
also `--nur-kv` **und** `--nur-git` zugleich – endet mit **Exit 2** und dem
Hinweis „Es wurde NICHTS geprüft“. Vorher meldete genau dieser Aufruf
„RESTORE-DRILL BESTANDEN“ und hätte als Wiederherstellungs-Nachweis zitiert
werden können. Der Abschlusssatz nennt jetzt ausdrücklich, *was* geprüft
wurde (`geprüft: Abonnenten (KV), Repository (Git-Bundle, …)`).

Dieselbe Prüfung läuft automatisiert: Die Frischwache
(`backup-frischwache.yml`, Schritt „Kurzprüfung Wiederherstellbarkeit“)
prüft Syntax und Selbsttest und führt die Gegenprobe aus (Drill ohne Familie
muss Exit 2 liefern). Ist dieser Schritt rot, meldet das Alerting die Klasse
`backup-restore`: „Sicherung gelaufen, Rückweg nicht belegt“ – ein Neustart
hilft dort nicht, der Code muss repariert werden.

### Ernstfall: Abonnenten zurückspielen

```bash
TAG=$(gh api "repos/frank-hartung/franksfinanzcheck-backup/releases?per_page=100" \
  --jq '[.[] | select(.tag_name | startswith("kv-backup-"))] | sort_by(.created_at) | last | .tag_name')
gh release download "$TAG" --repo frank-hartung/franksfinanzcheck-backup --pattern kv-export.json.enc
openssl enc -d -aes-256-cbc -pbkdf2 -iter 600000 -in kv-export.json.enc -out kv-export.json
python3 scripts/kv_backup.py --pruefen kv-export.json
python3 scripts/kv_backup.py --wrangler-bulk kv-export.json > bulk.json
npx wrangler kv bulk put bulk.json --namespace-id <ID-des-Ziel-Namespace> --remote
shred -u kv-export.json bulk.json 2>/dev/null || rm -f kv-export.json bulk.json
```

- `openssl` fragt die Passphrase ab.
- **`--remote` ist Pflicht.** Wrangler 4 schreibt KV-Befehle ohne diese
  Angabe in eine *lokale* Simulation und meldet trotzdem Erfolg. Dann wäre
  nichts wiederhergestellt.
- Die Klartext-Dateien enthalten E-Mail-Adressen. Nach dem Einspielen löschen
  (letzte Zeile).
- Einträge, die schon abgelaufen wären (etwa offene Bestätigungen),
  überspringt `--wrangler-bulk` automatisch.
- D1, falls mitgesichert: Die Tabellen stehen im Export unter `d1.tabellen`.

### Ernstfall: Repository wiederherstellen

```bash
TAG=$(gh api "repos/frank-hartung/franksfinanzcheck-backup/releases?per_page=100" \
  --jq '[.[] | select(.tag_name | startswith("backup-"))] | sort_by(.created_at) | last | .tag_name')
gh release download "$TAG" --repo frank-hartung/franksfinanzcheck-backup --pattern backup.bundle.enc
openssl enc -d -aes-256-cbc -pbkdf2 -iter 200000 -in backup.bundle.enc -out backup.bundle
git clone backup.bundle franksfinanzcheck-blog-wiederhergestellt
```

## Sicherheit

- Die Secrets liegen im Environment `backup` und sind nur für `main`
  erreichbar (Schritt 1).
- Der GitHub-Token sieht nur das Backup-Repo. Der Cloudflare-Token darf nur lesen.
- Der Prüfer gibt nie einen Secret-Wert aus, sondern nur Namen, Zustände und
  API-Antworten. Sein Selbsttest prüft das mit vergifteten Werten.
- **Gerät ein Token in falsche Hände:** Token sofort löschen (GitHub bzw.
  Cloudflare), neu erzeugen und das Secret ersetzen. Mit dem GitHub-Token
  allein lässt sich nur das Backup-Repo beschreiben; ohne Passphrase sind die
  Sicherungen unlesbar.

## Optional: Marken-Oberfläche

Läufe in einem Environment erscheinen auf der Startseite des Repos in der
Seitenleiste „Deployments“ – hier also `backup`. Ausblenden lässt sich das
über das Zahnrad bei „About“ → „Include in the home page“ → „Deployments“
abwählen.

## Hintergrund: Vorgang WF-9E5A / #761

Am 15.10.2026 war der KV-Job ab seinem ersten Lauf rot: Fünf von sechs
Voraussetzungen fehlten. Auch der jüngste Lauf vom 27.10.2026 (Run
`40474184391`) zeigt E1, E2, E3, E5 und E6 weiterhin als fehlend; E4 ist
vorhanden, E7 bleibt optional. E8 ist nicht auf `main` beschränkt. Dass der
Job rot ist, ist richtig – ein Grün ohne Sicherung wäre ein Schein-Grün. Die
technischen Umstände und der sichere Einrichtungsweg sind behoben; die noch
fehlenden Zugangsdaten muss der Inhaber einmalig am eigenen Konto einrichten.

- **Rat:** Die Meldung riet zu „API-Key (GROQ/GEMINI)“ und „neu starten“.
  Jetzt nennt sie die Einrichtung und verlinkt diese Anleitung. Ändert sich
  die Einordnung, führt der nächste rote Lauf eine offene Meldung nach – auch
  #761 selbst.
- **Prüfung:** Die alte Prüfung sah nur, *ob* ein Wert gesetzt ist. Jetzt
  prüft sie, ob er wirkt (E1–E8).
- **Verweis:** „siehe Umsetzungs-Runbook“ zeigte auf keine Datei. Jetzt
  verweist er hierher.
- **Fristen:** Auslaufende Tokens hätten die Sicherung eines Tages still
  beendet. Jetzt gibt es eine Fristwarnung mit 14 Tagen Vorlauf.
- **Environment:** Der Repo-Job lief ohne Environment `backup` und hätte die
  dort abgelegten Secrets nicht gesehen.
- **Rückspielen:** Ohne `--remote` hätte das Rückspielen nur lokal
  geschrieben.

Details stehen im Bericht `WF-9E5A-761-DAUERHEILUNG-PREMIUM-2026-10-15.md`.
