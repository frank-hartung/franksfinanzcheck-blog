# Bestand, Backup und Merge-Disziplin

> Wörtlich aus `CLAUDE.md` übernommen am 01.11.2026 (Skill-Umbau). Kein Satz wurde umformuliert, gekürzt oder erfunden; die Überschriften sind eine Ebene tiefer gehängt. Änderungen hier sind Änderungen am Regelwerk – sie brauchen denselben Nachweis wie vorher: Selbsttest der betroffenen Wache, dann Commit.

### Parallele Bearbeitung: der Bestand gewinnt (seit #590, 05.10.2026)

Menschen (PR-Merges) und Automatik arbeiten am selben Bestand. Kollidiert eine
**maschinelle Heilung** mit einer **fremden, neueren Fassung** desselben
Artikels, gewinnt die fremde Fassung – und die Heilung wird nachgezogen, nicht
vergessen. Unwiederbringlich ist Text; Heilung ist reproduzierbar.

- **Schalter (Opt-in, nicht global):** `GIT_SYNC_BESTAND_POLICY=bestand-gewinnt`
  in `content-engine-v2.yml`. Ohne die Variable bleibt ein Content-Konflikt in
  `scripts/git_sync.sh` ein **harter Stopp** – kein Blind-Merge, nirgends.
- **Nachheilung:** `scripts/git_sync.sh` protokolliert jeden abgegebenen
  Artikel in `.git_sync_nachheilung.txt` (gitignored),
  `scripts/nachheilung.py --fix` heilt ihn im selben Lauf auf dem neuen Text
  (offline, deterministisch, keine Geldfläche, < 1 s).
- **Reserve bleibt Maschinensache:** Bei zwei Reserve-Entwürfen gewinnt
  weiterhin der frische Lauf (#295) – diese Regel hat Vorrang.
- **Ehrlichkeit:** Ein nicht gepushter Tagesertrag bleibt rot, aber als eigene
  Klasse (`SYNCHRONVERLUST`) mit Datei und Ursache – nie wieder „API-Key
  prüfen", während ein Rebase klemmt.
- Vor jedem Umbau am Sync-Kern: `npm run test:sync` (47 Verträge) · Hintergrund:
  `SYNCHRONVERLUST-ENGINE-590-DAUERHEILUNG-PREMIUM-2026-10-05.md`.

### Ein Backup ohne Zugang ist kein Backup (Einrichtungsprüfung, seit WF-9E5A / #761, 15.10.2026)

Am 15.10.2026 war der KV-Job von `backup-offsite.yml` (Audit M-11) ab seinem
ersten Lauf rot: Ziel, Passphrase, Cloudflare-Lesezugang und Namespace-ID waren
nie eingerichtet. Das Rot war richtig. Die Meldung riet aber zu „API-Key
(GROQ/GEMINI)“ und „neu starten“, und die Prüfung kannte nur „gesetzt?“.

- **Fail-closed bleibt.** Kein `continue-on-error`, keine Bedingung „nur wenn
  das Secret gesetzt ist“, kein Überspringen: Ohne Sicherung ist der Lauf rot.
  Die Einrichtung ist Inhaberaufgabe – Agenten können Secrets weder lesen noch
  setzen.
- **`scripts/backup_einrichtung.py --pruefen`** prüft jeden Zugang live (E1–E8):
  Ziel privat und erreichbar, Token aktiv, Namespace mit genau diesem Token
  lesbar, Environment nur für `main`. Jeder offene Punkt steht mit Abhilfe-Link
  als Annotation und in der Job-Zusammenfassung. Kein Secret-Wert erscheint in
  einer Ausgabe (Selbsttest mit vergifteten Werten).
- **Der Schrittname „Voraussetzungen prüfen“ ist Alarmschlüssel**
  (`alert-on-failure.yml`, `backupEinrichtung`): Er bekommt das
  Einrichtungs-Runbook statt des API-Key-Rats. „Fristwarnung“ meldet ablaufende
  Zugänge 14 Tage vorher – nach der Sicherung, nicht statt ihr.
- **Offene Meldungen werden nachgeführt** (`alert-on-failure.yml`, Marker
  `<!-- alert-runbook: … -->`): Ändert sich die Klasse des Rats, schreibt der
  nächste rote Lauf die offene Meldung neu (gleiche Nummer, kein Kommentar,
  keine Benachrichtigung). Eine neue Runbook-Klasse braucht deshalb einen
  eigenen Namen in `runbookKlasse`; `test_alert_scoping` erzwingt, dass Klassen
  und Ratschläge deckungsgleich bleiben. Offene Alarm-Issues nie von Hand
  umschreiben – der nächste rote Lauf erledigt das.
- **Lagebild-Verfall / stille Frischhaltung (seit 26.10.2026, WF-E813/#815,
  dieselbe Lücke wie WF-9E5A/#761):** Bleibt die Klasse gleich, vergleicht
  dasselbe Skript die per Regex aus dem Body gelesene Lauf-ID
  (`/(?:actions\/)?runs\/(\d+)/`) mit dem aktuellen Lauf. Ein jüngerer Lauf
  schreibt die Meldung über den bestehenden Nachführ-Pfad neu (Lauf-Link,
  Zeit, Commit, Job-Liste, `alert-jobs`-Marker), ohne den Rat anzutassen;
  ein gleicher oder älterer Lauf (Webhook-Redelivery, verspätete Zustellung)
  lässt den Body unangetastet – Reihenfolgeschutz. Eine offene Meldung darf
  nie auf einen alten Lauf verweisen und gleichzeitig behaupten, aktuell zu
  sein. Der Update-Block ist fail-open – lehnt die Issue-API ab, bleibt die
  Meldung unverändert offen, und es entsteht kein Duplikat. Vertrag:
  `test_alert_scoping` (Strukturvertrag + 58 Sim-Szenarien).
- **Beide Backup-Jobs laufen im Environment `backup`** – dort liegen die Secrets.
  Zusätzlich verweigern `backup-offsite.yml` und `backup-frischwache.yml` auf
  Job-Ebene jeden Ref außer `refs/heads/main`, bevor ein Job mit Environment-
  Secrets startet. Das ist Defense in depth, kein Ersatz für die Einrichtung:
  immer **erst absichern, dann befüllen** (Anleitung Schritt 1: explizit genau
  `main` vom Typ `branch`). Der Wizard schreibt die Policy über
  die unterstützte REST-Kette (Environment-`PUT`, Policy-`GET`/`DELETE`/`POST`)
  und verlangt danach einen paginierten Live-Read-back; unlesbar, `protected branches`,
  zusätzliche Branches/Tags oder fehlende Regeln bedeuten Abbruch vor dem
  ersten Secret. Eine manuelle „Erledigt?“-Bestätigung ersetzt den Nachweis
  nicht. Solange Zugänge fehlen und ein fremder Branch an das Environment
  käme, stellt der Prüfer „Zuerst E8“ über die Liste; Tests sichern Payload,
  Rückprüfung und Fail-closed-Reihenfolge.
- **KV zurückspielen nur mit `--remote`:** Wrangler 4 schreibt sonst in die
  lokale Simulation und meldet trotzdem Erfolg.
- **Wiederherstellung beweisen:** `bash scripts/restore_drill.sh --repo <privates Backup-Repo>`
  (KV + Git, entschlüsselt in einem 0700-Temp-Verzeichnis).
- **Ein Drill ohne Prüfung ist kein Drill (01.11.2026, #923).** Ein Aufruf
  ohne geprüfte Familie (`--nur-kv` und `--nur-git` zugleich) endete bisher
  mit Exit 0 und „RESTORE-DRILL BESTANDEN“ – ein Nachweis über nichts. Jetzt
  Exit 2, und der Abschluss nennt die geprüften Familien. Der enthaltene
  Branch wird ausdrücklich aus dem Bundle gewählt (sonst klont Git bei
  abweichendem HEAD still einen leeren Baum). Die Frischwache prüft das
  jeden Tag inkl. Gegenprobe; ein roter Rückweg-Nachweis meldet die Klasse
  `backup-restore` („gelaufen, aber Rückweg nicht belegt“) statt eines
  Neustart-Rats, der an einem Syntaxfehler nichts ändert.
- **Eingaben der Wachen werden geprüft, nicht nur ihre Messung:** In
  `backup_freshness_guard.py` verwarf ein Vorrang-Fehler (`a or b if … else ""`)
  jedes `--repo` ohne Positionsargument – also genau den Aufruf aus Anleitung
  und `npm run backup:frische`. Seit #923 zerlegt `repo_bestimmen()` die Quellen
  (Flag → Position → `BACKUP_REPO`/`ZIEL_REPO`), und der Selbsttest (13.
  Fallgruppe) hält die Klasse zu.
- **Frische operativ überwachen (Highend-Ergänzung 22.10.2026, automatisiert 24.10.2026):** E1–E8 prüfen die
  *Konfiguration* – ob die Sicherung laufen *kann*. Ob sie *jüngst lief*, misst
  `scripts/backup_freshness_guard.py --repo <privates Backup-Repo>` (52 h rot,
  36 h gelb, beide Release-Familien `backup-*` + `kv-backup-*`). Kurzform
  `npm run backup:frische`. **Automatisiert:** Workflow `backup-frischwache.yml`
  läuft täglich 13:00 UTC (nach 03:00 UTC-Sicherung + Scheduler-Puffer) und meldet
  über `backup-frisch` – kein Ersatz für E1–E8, sondern die operative Lücke:
  Ein Scheduler-Hänger ohne ablaufenden Token bliebe sonst bis zur nächsten
  Anleger-Frage unbemerkt. SLA: RPO 24 h / 52 h Toleranz, RTO < 60 Min.
- **Inhaber-Einrichtung ist der einzige offene Auftragsteil (#761; aktuell
  erneut nachgewiesen in #923):** Der Schnellweg führt über `npm run backup:einrichten`
  (`scripts/backup_einrichten_wizard.sh`, E8 erst live auf ausschließlich
  `main` beweisen, dann E1–E7; Geheimnisse nur verdeckt, in CI bewusst
  gesperrt); `npm run backup:status` prüft den Stand ohne Änderung. Agenten
  setzen weiterhin keine Secrets und umschreiben keine offenen Alarm-Issues
  von Hand.
- Tests: `npm run test:backup` (Frische-Wache 13 Fälle, E8 REST- und
  Fail-closed-Wizard-Verträge, Rückweg-Vertrag: Exit 2 ohne Familie,
  belegter Bestanden-Satz, falsche Passphrase rot) ·
  Alarm-Szenarien in `scripts/tests/sim/alert_scoping_sim.mjs` (58 Szenarien,
  inkl. Lagebild-Verfall und Reihenfolgeschutz) · Anleitung
  `docs/ANLEITUNG-OFFSITE-BACKUP.md` · Bericht
  `WF-9E5A-761-DAUERHEILUNG-PREMIUM-2026-10-15.md` + Highend-Berichte
  `WARTUNG-BACKUP-WF-9E5A-HIGHEND-2026-10-22.md`,
  `WARTUNG-BACKUP-WF-9E5A-HIGHEND-2026-10-24.md`,
  `WARTUNG-BACKUP-WF-9E5A-HIGHEND-2026-10-26.md` und
  `WARTUNG-BACKUP-WF-9E5A-HIGHEND-2026-10-27.md` und
  `WARTUNG-BACKUP-WF-9E5A-HIGHEND-2026-10-29.md` (Live-Befund #923,
  Ref-/Token-Defense-in-depth; Inhaber-Einrichtung bleibt offen) und
  `WARTUNG-BACKUP-WF-9E5A-HIGHEND-2026-11-01.md` (Live-Befund erneut belegt;
  Schein-Grün im Rückweg-Beweis und verworfene `--repo`-Eingabe geheilt).

### Ein Rebase ist ein neuer Stand – erst grün, dann mergen (seit WF-53E2 / #780, 16.10.2026)

PR #776 wurde am 15.10.2026 auf `main` umgesetzt (zwei Konflikte) und **22
Sekunden** nach dem Push dieses Stands gemergt – bevor ein Check des Commits
fertig war. Danach waren drei rot (Qualitäts-Gate, Regressionstests,
Integritäts-Siegel). Die Konflikte waren „zugunsten“ einer Seite aufgelöst und
überschrieben damit zwei schon gemergte Heilungen: den Ausnahme-Vertrag aus
#762 (zweite Auswertung in Gate und A8, sichtbarer Hinweis gelöscht) und den
Faustregel-Pool aus #766 (Code weg, Selbsttests und Aufrufer geblieben). Das
Qualitäts-Gate meldete es um 18:22 UTC als „Qualitätsprüfung rot“ (#777); am
16.10. folgten #778, #779, #780 und #783, die Affiliate-Wache stand fail-closed.
Am 16.10. wiederholte sich das Muster binnen Minuten: Die parallelen
Reparaturen #785 und #784 gingen 58 s bzw. 77 s auseinander rot nach `main`;
ihre Zusammenführung ließ in `affiliate_integrity_gate.py` zwei `if`-Köpfe und
zwei Hinweistexte stehen – ein **IndentationError auf `main`**, an dem jeder
Aufrufer (Wache, Publish-Gate, Bestand-Gate, CodeQL-Wachen) abstürzte.

- **Kein Merge vor dem grünen Abschluss DIESES Commits.** Nach jedem Push –
  auch Rebase und Force-Push – `gh pr checks <nr> --watch --fail-fast`
  abwarten. Rot oder ausstehend heißt: nicht mergen. Der Branch-Schutz verlangt
  die Checks hier nicht (Dauerzustand, `docs/PFLICHT-CHECK-RUNBOOK.md`); bis er
  es tut, ersetzt diese Regel ihn. Eine offene „Qualitätsprüfung rot“ ist der
  früheste Alarm – sie geht jeder weiteren Arbeit vor.
- **Konflikt zwischen zwei Heilungen = beide behalten.** Eine Auflösung
  „zugunsten“ einer Seite nimmt die andere zurück und braucht deren Vorgang.
  Danach `python3 scripts/selftest_runner.py` (alle Wachen, wenige Minuten) –
  er hätte #776 vor dem Merge gestoppt.
- **Ein Vertrag, ein Auswerter.** `affiliate_exempt` liest nur
  `scripts/affiliate_exemption.py` (`affiliate_exemption`,
  `exemption_for_article`, `exemption_for_text`). Kein eigenes
  Frontmatter-Splitten, kein Import über eine andere Wache, kein
  `except Exception` um den Vertrag – ein verschluckter Fehler wird still zu
  „keine Ausnahme“. `test_affiliate_exemption.SingleEvaluatorStructureTests`
  erzwingt das am Code; der Render-Beweis wertet nur das geladene `fm` aus.
- **Ungültige Ausnahme = Fund, nie Heilung.** A8
  (`affiliate_profi_check.py --fix`) setzt einem Artikel mit kaputter Ausnahme
  keine Werbe-CTA ein; der Render-Beweis meldet dafür genau einen Fund.
- **Ein roter Selbsttest ist Code.** Alarm-Klasse `selbsttest` in
  `alert-on-failure.yml` (maßgeblich ist der erste rote Schritt): Rat =
  `selftest_runner.py` und `git log` der Wache – kein Schlüssel-, kein
  Neustart-Rat.
- Tests: `npm run test:affiliate-links` · Szenarien #780 in
  `scripts/tests/sim/alert_scoping_sim.mjs` · Bericht
  `WF-53E2-780-DAUERHEILUNG-PREMIUM-2026-10-16.md`.
