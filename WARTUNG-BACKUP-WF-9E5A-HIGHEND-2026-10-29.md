# Wartung · Sicherung · WF-9E5A #923 — Highend-Dauerheilung (29.10.2026)

**Auftrag:** `Wartung · Sicherung · Vorgang WF-9E5A #923 Bitte dauerhaft auf Highend-Level einer Profi-Agentur beheben.`  
**Branch:** `arena/fcade9e0-franksfinanzcheck-blog`  
**Basis:** `2e4c7ae313b1be78b9e4383fc45c0de830127610` (`main`, 29.10.2026)  
**Bearbeiter:** Arena Agent

---

## 1. Live-Befund — nicht raten, sondern nachweisen

Issue [#923](https://github.com/frank-hartung/franksfinanzcheck-blog/issues/923)
ist eine automatisch nachgeführte Meldung aus dem Lauf
[40847586847](https://github.com/frank-hartung/franksfinanzcheck-blog/actions/runs/40847586847)
(29.10.2026, 09:10 UTC). Der Lauf selbst ist nicht „kaputter Exportcode“:

- Job `backup` war grün und erzeugte nur die ausdrücklich als **Kurzzeit-Kopie
  ohne Offsite-Schutz** bezeichnete Artefaktspur.
- Job `KV-/D1-Backup (Abonnenten + Einwilligungsnachweise)` brach im
  fail-closed-Schritt `Voraussetzungen prüfen` ab.
- Export, Verschlüsselung und Ablage wurden korrekt **nicht** gestartet.

Die Check-Run-Annotationen belegen diesen Stand:

| Punkt | Live-Befund | Bedeutung |
|---|---|---|
| E1 `BACKUP_REPO` | fehlt | Kein privates Ziel-Repository konfiguriert |
| E2 `BACKUP_REPO_TOKEN` | fehlt | Kein fein eingeschränkter Schreibzugang zum Ziel |
| E3 `BACKUP_PASSPHRASE` | fehlt | Keine wiederherstellbare Verschlüsselung möglich |
| E4 `CLOUDFLARE_ACCOUNT_ID` | vorhanden | Dieser Einzelpunkt ist grün |
| E5 `CF_KV_BACKUP_TOKEN` | fehlt | KV-Lesezugriff nicht eingerichtet |
| E6 `KV_NAMESPACE_ID_ABO` | fehlt | Quelle der Abonnenten-/Einwilligungsdaten nicht bestimmt |
| E7 `D1_DATABASE_ID` | optional | Nur für den optionalen Klick-Zähler nötig |
| E8 Environment `backup` | offen | `deployment_branch_policy: null`; jeder Branch wäre zugelassen |

**Sicherheitsurteil:** Abonnenten und Einwilligungsnachweise sind bis zur
Inhaber-Einrichtung nicht offsite gesichert. Das Rot ist richtig. Ein
`Run workflow` ohne Einrichtung wäre kein Fix, sondern nur ein weiterer roter
Nachweis.

Die Schreib-Endpunkte für Actions-Secrets/-Variablen und Environment-Schutz
waren im verfügbaren GitHub-Kontext mit `403 Resource not accessible by
integration` nicht beschreibbar. Es wurden deshalb **keine** Secrets,
Variablen, Tokens, Environment-Regeln oder Issues erfunden, überschrieben oder
in Chat/Repository abgelegt. Secret-Werte sind aus GitHub grundsätzlich nicht
lesbar.

---

## 2. Dauerhafte Code-Korrektur in diesem Stand

Der Live-Befund zeigt zugleich eine E8-Sicherheitslücke: Eine offene
Environment-Policy darf nicht die einzige Barriere für ein manuelles
`workflow_dispatch` sein. Die Workflows wurden deshalb defensiv verschärft:

### 2.1 Ref-Gate vor Environment-Secrets — E8 Defense in depth

Alle Jobs, die das Environment `backup` verwenden, tragen jetzt auf
Job-Ebene eine explizite, versionierte Ref-Schranke:

```yaml
if: ${{ github.ref == 'refs/heads/main' }}
```

Das gilt für:

- `backup-offsite.yml` → `backup`
- `backup-offsite.yml` → `kv-backup`
- `backup-frischwache.yml` → `frischwache`

Damit erhält ein manueller Start auf einem Feature-Branch keinen
Environment-Secret-Kontext, selbst wenn die E8-Policy später driftet oder
versehentlich entfernt wird. Die Branch-Policy **nur `main`** bleibt trotzdem
Pflicht: Sie schützt auch gegen andere Fehlkonfigurationen und ist der
vorgelagerte Inhaber-Nachweis.

### 2.2 Kein Quell-Token als Offsite-Ersatz

Der Repo-Backup-Job verwendete bei gesetztem Ziel bisher als Fallback den
kurzlebigen `GITHUB_TOKEN` des Quell-Repositorys. Dieser Token beweist keinen
Zugriff auf das private Ziel und ist kein zulässiger Offsite-Zugang. Der
Ablagepfad verlangt jetzt explizit `BACKUP_REPO_TOKEN`, bricht ohne ihn
fail-closed ab und verwendet auch beim Aufräumen niemals den Quell-Token.

Zusätzlich wurde die Berechtigung des Repo-Jobs von `contents: write` auf
`contents: read` reduziert und `persist-credentials: false` gesetzt. Der
separat gespeicherte, fein eingeschränkte Ziel-Token wird nur an den einzelnen
`gh`-Aufruf übergeben.

### 2.3 Regressionsschutz

`WorkflowVertrag` hält jetzt fest:

- alle drei Secret-Jobs dürfen nur auf `refs/heads/main` laufen;
- der Repo-Job hat nur `contents: read`;
- ein gesetztes Ziel verlangt einen dedizierten `BACKUP_REPO_TOKEN`;
- kein Quell-`GITHUB_TOKEN` darf als Offsite-Fallback dienen.

Die Dokumentation in `docs/ANLEITUNG-OFFSITE-BACKUP.md`,
`docs/INFRASTRUKTUR.md` und `CLAUDE.md` beschreibt die zusätzliche Schranke
und nennt den aktuellen Live-Stand von #923, ohne den offenen Inhaber-Schritt
als erledigt auszugeben.

---

## 3. Abnahme — was jetzt grün ist und was der Inhaber noch tun muss

### Automatisch geprüft

| Prüfung | Ergebnis |
|---|---|
| `python3 -m unittest scripts.tests.test_backup_einrichtung` mit PyYAML | **41 Tests, 0 Fehler** |
| `python3 scripts/backup_einrichtung.py --selftest` | grün |
| `python3 scripts/backup_freshness_guard.py --selftest` | grün |
| `python3 scripts/kv_backup.py --selftest` | grün |
| `bash -n scripts/backup_einrichten_wizard.sh` | grün |
| `python3 -m py_compile` der Backup-Skripte | grün |
| YAML-Parse beider Backup-Workflows mit PyYAML | grün |
| `git diff --check` | grün |

Die nackte Sandbox hat PyYAML zunächst nicht installiert; die vollständige
41-Test-Abnahme wurde anschließend in einer isolierten temporären Python-
Umgebung mit PyYAML durchgeführt. Keine Testumgebung oder Abhängigkeit wurde
ins Repository geschrieben.

### Einmalige Inhaber-Einrichtung

Die eigentliche Sicherung kann nur mit echten, nicht zu erratenden Zugangsdaten
laufen. Der Inhaber führt am eigenen Rechner aus:

```bash
npm run backup:einrichten
```

Der Wizard erzwingt die Reihenfolge **E8 → E1–E7** und prüft E8 nach jeder
Änderung erneut. Alternativ die sieben Schritte in
`docs/ANLEITUNG-OFFSITE-BACKUP.md`:

1. Environment `backup`: Selected branches → genau `main`, keine Required reviewers.
2. Privates Repository anlegen und als `BACKUP_REPO` eintragen.
3. Zufällige Passphrase mit mindestens 32 Zeichen im Passwort-Manager sichern;
   nur als `BACKUP_PASSPHRASE` eintragen.
4. Fine-grained GitHub-Token mit Contents Read and write **nur** für das
   private Backup-Repository als `BACKUP_REPO_TOKEN` eintragen.
5. Cloudflare-Token nur mit Workers KV Storage: Read als
   `CF_KV_BACKUP_TOKEN` eintragen.
6. Die 32-stellige Namespace-ID von `ABO` als `KV_NAMESPACE_ID_ABO` eintragen.
7. Actions → `Offsite-Backup` → `Run workflow` auf `main` starten.

Danach muss ein echter grüner Lauf beide Release-Familien erzeugen und
nachprüfen. Erst anschließend folgt:

```bash
npm run backup:probe
```

**Abnahmekriterium für #923:** ein grüner `KV-/D1-Backup`-Job auf `main`, ein
privates Entwurfs-Release `kv-backup-*` mit Größen-/Draft-Nachweis und danach
ein erfolgreicher Restore-Drill. Bis dahin bleibt #923 offen; das ist der
korrekte, auditierbare Zustand.

---

## 4. Bewusste Grenzen

- Keine Secrets oder Passphrasen im Code, in Issues, im Bericht oder in Logs.
- Kein `continue-on-error`, kein Überspringen des KV-Exports und kein
  automatisches „grün“, nur um #923 zu schließen.
- Keine Nutzung des öffentlichen Quell-Repositories als Ersatz für ein
  privates Offsite-Ziel.
- Keine manuelle Issue-Umschreibung oder -Schließung: Das bestehende Alerting
  führt #923 mit dem nächsten roten Lauf nach und schließt erst mit dem
  nachgewiesenen grünen Job.
- Keine Erfindung fehlender Cloudflare-/GitHub-Werte. Ein Highend-Fix ist
  reproduzierbar und wiederherstellbar, nicht nur optisch grün.

**Ergebnis:** Die Quellcode-Seite ist gegen Ref-/Token-Fehlkonfigurationen
härter und vollständig regressionsgeschützt. Der verbleibende Live-Blocker
ist transparent auf die Inhaber-Einrichtung reduziert; ohne diese echten
Zugangsdaten wäre jede behauptete vollständige Heilung ein Schein-Backup.
