# Runbook: Pflicht-Check `Integritäts-Siegel` (Branch-Schutz für `main`)

**Stand:** 19.09.2026 · **Vertrag:** Governance-Regel **C18** (`scripts/governance_contract.py`)
· **Live-Wache:** `scripts/pflichtcheck_guard.py` (letzter Schritt in
`.github/workflows/integrity-lock.yml`) · **Anlass:** Nachtrag zu
[Vorfall 19.09.2026](INCIDENT-2026-09-19-integritaets-lock.md) / PR #317

## Worum es geht – in drei Sätzen

Das PR-Gate `Integritäts-Lock (PR-Gate)` prüft bei jedem Pull Request auf `main`,
ob der signierte Kern zum Baum passt. Einen Merge **aufhalten** kann es nur, wenn
GitHub es als **Pflicht-Check** (required status check) kennt – unter genau dem
Namen, den der Job meldet: **`Integritäts-Siegel`**. Dieser Name ist deshalb ein
Vertrag zwischen zwei Orten, die einander nicht sehen: der Workflow-Datei und dem
Ruleset des Repositories.

## Der Vertrag (was wo stehen muss)

| Ort | Eintrag | Wer prüft |
|---|---|---|
| `scripts/governance_contract.py` | `PFLICHT_CHECK_NAME = "Integritäts-Siegel"` | – (die Konstante ist die Quelle) |
| `.github/workflows/integrity-lock.yml` | `jobs.lock.name: Integritäts-Siegel`, PR-Trigger auf `main`, **kein** `paths`/`paths-ignore`, **kein** `if:` am Job, **kein** `continue-on-error` am Gate-Schritt, nur `contents: read`, letzter Schritt `pflichtcheck_guard.py` | **C18** im Qualitäts-Gate (jeder Push/PR) |
| Ruleset (Settings → Rules → Rulesets) | Enforcement **Active**, Target **Include default branch**, Required status check **`Integritäts-Siegel`** (Quelle GitHub Actions, App-ID 15368) | **Live-Wache** im Gate-Lauf jedes PR |

Warum jede Zeile: Ein umbenannter Job lässt jeden PR auf einen Check warten, der
nie berichtet („Expected“) – `main` ist eingefroren. Ein Pfadfilter tut dasselbe,
nur seltener. Ein `if:` am Job oder `continue-on-error` am Gate-Schritt macht aus
Rot ein Grün, denn ein übersprungener Pflicht-Check gilt GitHub als bestanden.
Ein Ruleset ohne Ziel-Zweig, deaktiviert oder mit altem Namen schützt nichts –
das Gate läuft dann, entscheidet aber nichts.

## Zustand prüfen (read-only, jeder darf das)

```bash
# Was verlangt main wirklich? (nur AKTIVE Rulesets, Ziel-Bedingungen aufgelöst)
gh api repos/frank-hartung/franksfinanzcheck-blog/rules/branches/main

# Dasselbe als Urteil mit Diagnose und Reparatur (Exit 0 = Vertrag erfüllt)
python3 scripts/pflichtcheck_guard.py

# Der statische Teil des Vertrags (Workflow-Datei = Konstante)
python3 scripts/governance_contract.py --quick
```

Antwortet die erste Zeile mit `[]`, verlangt `main` **nichts** – so sah es am
19.09.2026 aus: Das Ruleset „Integritäts-Lock (PR-Gate)“ (#23695872) war aktiv,
verlangte `lock` und hatte **keinen Ziel-Zweig** (`include: []`).

## Ruleset einrichten oder reparieren (Admin)

**Klickweg:** Settings → Rules → Rulesets → „Integritäts-Lock (PR-Gate)“

1. **Target branches** → Add target → **Include default branch** (`~DEFAULT_BRANCH`).
2. **Require status checks to pass** → alten Eintrag (`lock`) entfernen →
   **`Integritäts-Siegel`** hinzufügen (Quelle: GitHub Actions). Der Name erscheint
   in der Suche, sobald der Check einmal gelaufen ist (also nach dem ersten PR
   mit dem umbenannten Job).
3. Enforcement **Active** → **Save changes**.
4. Im offenen PR den Job **Re-run** → der Schritt „Pflicht-Check-Vertrag prüfen“
   wird grün und nennt die Ruleset-ID.

**API-Einzeiler (gleichwertig, Admin-Token nötig):**

```bash
gh api --method PUT repos/frank-hartung/franksfinanzcheck-blog/rulesets/23695872 --input - <<'JSON'
{
  "name": "Integritäts-Lock (PR-Gate)",
  "target": "branch",
  "enforcement": "active",
  "conditions": { "ref_name": { "include": ["~DEFAULT_BRANCH"], "exclude": [] } },
  "rules": [
    { "type": "deletion" },
    { "type": "non_fast_forward" },
    { "type": "required_status_checks",
      "parameters": {
        "strict_required_status_checks_policy": false,
        "do_not_enforce_on_create": false,
        "required_status_checks": [ { "context": "Integritäts-Siegel", "integration_id": 15368 } ]
      } }
  ]
}
JSON
```

(`strict_required_status_checks_policy: false` = PRs müssen nicht vor jedem Merge
auf den neuesten `main` gebracht werden – bei einem Ein-Personen-Repo mit
Squash-Merges bewusst so gewählt; das Siegel prüft ohnehin den Merge-Stand.)

> **Achtung, `PUT` ersetzt das Ruleset als Ganzes.** Ein Einzeiler ohne
> `bypass_actors` löscht einen vorhandenen Bypass-Akteur still – und damit die
> Reparatur aus dem Abschnitt
> [Direkte Pushes und Automation](#direkte-pushes-und-automation-vorfall-19092026)
> unten. Vor jedem `PUT`: erst `GET` (`gh api repos/frank-hartung/franksfinanzcheck-blog/rulesets/23695872`),
> dann den Zielzustand vollständig hinschreiben, danach erneut `GET` und
> `bypass_actors` prüfen.

## Umbenennen – nur in dieser Reihenfolge

Ein Pflicht-Check wird nie „mal eben“ umbenannt. Wer es tut, tut es in **einem**
Vorgang:

1. **PR:** `PFLICHT_CHECK_NAME` in `governance_contract.py` **und** `jobs.lock.name`
   in `integrity-lock.yml` gemeinsam ändern (C18 und der Selbsttest der Wache –
   Fall 9 – sind sonst rot; der PR kommt nicht durch das Qualitäts-Gate).
   Dokumentation nachziehen: README, `docs/QUALITAETS-REGELWERK.md`, dieses Runbook.
2. **Ruleset:** *Nach* dem Merge dieses PR den neuen Namen im Ruleset eintragen und
   den alten entfernen (Klickweg oder API-Einzeiler oben).
   Zwischen 1 und 2 verlangt `main` noch den alten Namen – PRs mit dem neuen
   Workflow melden ihn nicht mehr und bleiben auf „Expected“ stehen. Deshalb:
   erst mergen, sofort danach das Ruleset – oder das Ruleset **vor** dem Merge
   umstellen, wenn der PR selbst schon den neuen Namen meldet (dann ist er der
   erste, der unter dem neuen Vertrag mergebar ist).
3. **Beweis:** `gh api …/rules/branches/main` nennt den neuen Namen; der nächste
   Gate-Lauf ist grün („Vertrag erfüllt … Ruleset #…“).

## Direkte Pushes und Automation (Vorfall 19.09.2026)

### Was passiert ist

Das Ruleset #23695872 verlangte ab 10:00:03 Uhr den Pflicht-Check
`Integritäts-Siegel` auf `main` – mit `bypass_actors: null`, also ohne dass
irgendjemand vorbeikommt. Dieser Check entsteht aber ausschließlich in Pull
Requests (`integrity-lock.yml` hat die Trigger `pull_request` und
`workflow_dispatch` – und kein `push`). Ergebnis:

* **jeder direkte Push auf `main` wurde abgelehnt** – vorher elf Bot-Commits in
  90 Minuten, danach kein einziger mehr;
* Deploy #998 (Run `35437446077`) scheiterte im Schritt **„Gate-Heilungen
  committen (konvergent)"**, der Schritt **„Deploy auf gh-pages“** wurde
  übersprungen – die Website blieb ab 10:27 Uhr alt;
* der Social-Autopilot (Run `35448944197`, 14:30) starb an derselben Stelle;
* im Log stand nur `git_sync.sh: Synchronisation nach 3 Runden fehlgeschlagen
  (zuletzt: netzwerk)` – drei Runden Backoff gegen eine Regel, die sich nicht
  wegwartet, und eine Ursachenangabe, die keine war;
* diese Wache meldete zeitgleich `✅ Vertrag erfüllt`. Der Vertrag *war* erfüllt
  – um den Preis der gesamten Automation.

Betroffen war nicht ein Workflow, sondern das ganze Haus: **31 Workflows**
committen selbst auf `main` (`deploy.yml`, `content-engine-v2.yml`,
`social-autopilot.yml`, `affiliate-health.yml`, `seo-weekly.yml`, …).

### Warum ein Pflicht-Check direkte Pushes blockiert

Pflicht-Status-Checks gelten für **jeden** Schreibvorgang auf den Zweig, nicht
nur für Merges. GitHubs eigene Doku sagt es in einem Satz („Troubleshooting
rules", Abschnitt *Troubleshooting required status checks*):

> Required status checks do not take workflow, matrix, or event trigger types
> into account.

Das Ruleset weiß also nicht – und will es nicht wissen –, dass der verlangte
Check bei einem direkten Push nie entstehen *kann*. Es sieht nur: „kein
bestandener Check" → ablehnen. Ein Pflicht-Check, dessen Workflow keinen
`push:`-Trigger hat, ist für direkte Pushes damit eine Sackgasse, kein
Sicherheitsgewinn. Der vorgesehene Ausweg heißt **Bypass-Akteur**.

### Diagnose (read-only, jeder darf das)

```bash
# 1) Wer verlangt was – und wer darf vorbei? bypass_actors ist der Schlüssel.
gh api repos/frank-hartung/franksfinanzcheck-blog/rulesets/23695872 \
  --jq '{name, enforcement, bypass_actors, conditions, rules: [.rules[].type]}'

# 2) Kann der verlangte Check auf einem direkten Push überhaupt entstehen?
grep -n -A4 '^on:' .github/workflows/integrity-lock.yml      # nur pull_request → Sackgasse

# 3) Beweis am Verlauf: letzter Bot-Commit gegen Uhrzeit der Ruleset-Änderung
gh api 'repos/frank-hartung/franksfinanzcheck-blog/commits?sha=main&per_page=15' \
  --jq '.[] | "\(.commit.author.date)  \(.commit.author.name)  \(.commit.message | split("\n")[0])"'
gh api repos/frank-hartung/franksfinanzcheck-blog/rulesets/23695872 --jq '{created_at, updated_at}'

# 4) Urteil samt Bypass-Nachprüfung (zählt die betroffenen Workflows)
python3 scripts/pflichtcheck_guard.py --branch main
```

### Reparatur: zwei Rulesets statt einem (Admin)

**Geschichtet** heißt: Der unverhandelbare Teil (nichts verschwindet, nichts wird
überschrieben) bindet **alle** – auch Admins, auch Bots. Der Teil, der einen
laufenden Check verlangt, bekommt einen **Bypass für die Automation**, sonst
steht das Haus. Beide Rulesets wirken gleichzeitig auf `~DEFAULT_BRANCH`; GitHub
addiert die Regeln.

**A) Neu – „main – Unveränderlichkeit“ (Bypass-Liste leer):**

Klickweg: Settings → Rules → Rulesets → **New ruleset** → **New branch ruleset**

1. Ruleset name: `main – Unveränderlichkeit (ohne Bypass)`
2. Target branches → **Include default branch**
3. Rules: **Restrict deletions** + **Block force pushes** – sonst nichts
4. **Bypass list leer lassen** → Create

```bash
gh api --method POST repos/frank-hartung/franksfinanzcheck-blog/rulesets --input - <<'JSON'
{
  "name": "main – Unveränderlichkeit (ohne Bypass)",
  "target": "branch",
  "enforcement": "active",
  "bypass_actors": [],
  "conditions": { "ref_name": { "include": ["~DEFAULT_BRANCH"], "exclude": [] } },
  "rules": [ { "type": "deletion" }, { "type": "non_fast_forward" } ]
}
JSON
```

**B) Bestehend #23695872 – nur noch Pflicht-Check, mit Bypass für Automation:**

Klickweg: Settings → Rules → Rulesets → „Integritäts-Lock (PR-Gate)“

1. Rules: **Restrict deletions** und **Block force pushes** entfernen (steht jetzt
   in A und gilt dort für alle), **Require status checks to pass** mit
   `Integritäts-Siegel` behalten.
2. **Bypass list** → **Add bypass** → Rolle **Repository role: Write** auswählen →
   **Add Selected** → Modus **„Always allow“** (nicht „For pull requests only“:
   die Automation pusht direkt).
3. Optional, bewusst abwägen: zusätzlich **Repository role: Admin** mit
   **„For pull requests only“** – dann hat der Eigentümer einen Notausgang über
   einen PR (mit Spur im Audit-Log), darf aber weiterhin nicht direkt pushen.
   Modus „Always“ für Admin würde auch Merge-am-Siegel-vorbei erlauben.
4. **Save changes**.

```bash
# Rollen-IDs sind GitHub-intern und nicht offiziell dokumentiert. Reihenfolge:
# erst im UI klicken (die Beschriftungen sind eindeutig), dann die ID ablesen …
gh api repos/frank-hartung/franksfinanzcheck-blog/rulesets/23695872 --jq '.bypass_actors'
# … und genau diese ID im Einzeiler verwenden. Übliche Werte (Praxis, ohne
# Garantie): 1 Read · 2 Triage · 3 Write · 4 Maintain · 5 Admin.
gh api --method PUT repos/frank-hartung/franksfinanzcheck-blog/rulesets/23695872 --input - <<'JSON'
{
  "name": "Integritäts-Lock (PR-Gate)",
  "target": "branch",
  "enforcement": "active",
  "bypass_actors": [
    { "actor_id": 3, "actor_type": "RepositoryRole", "bypass_mode": "always" },
    { "actor_id": 5, "actor_type": "RepositoryRole", "bypass_mode": "pull_request" }
  ],
  "conditions": { "ref_name": { "include": ["~DEFAULT_BRANCH"], "exclude": [] } },
  "rules": [
    { "type": "required_status_checks",
      "parameters": {
        "strict_required_status_checks_policy": false,
        "do_not_enforce_on_create": false,
        "required_status_checks": [ { "context": "Integritäts-Siegel", "integration_id": 15368 } ]
      } }
  ]
}
JSON
```

Der `GITHUB_TOKEN` eines Workflows mit `permissions: contents: write` gilt als
Akteur mit der Rolle **Write** – Admin-Rechte erbt er nie, auch nicht wenn der
auslösende Mensch Admin ist. Deshalb ist „Write“ die richtige Bypass-Rolle für
die Automation und nicht „Admin“.

### Verifikation

```bash
# a) Bypass steht drin, Pflicht-Check auch, Lösch-/Force-Schutz in A:
gh api repos/frank-hartung/franksfinanzcheck-blog/rulesets \
  --jq '.[] | "\(.id)\t\(.name)\t\(.enforcement)"'
gh api repos/frank-hartung/franksfinanzcheck-blog/rulesets/23695872 --jq '.bypass_actors'
gh api repos/frank-hartung/franksfinanzcheck-blog/rules/branches/main \
  --jq '.[].type'

# b) Die Wache muss grün bleiben UND die Warnung verlieren:
python3 scripts/pflichtcheck_guard.py --branch main      # ✅ ohne ⚠️ Schein-Sicherheit

# c) Der liegengebliebene Deploy muss wieder durchlaufen:
gh run rerun 35437446077 --failed
#    Schritt „Gate-Heilungen committen“ grün → „Deploy auf gh-pages“ läuft.

# d) Härteprobe (optional): leerer Commit direkt auf main – muss durchgehen.
git commit --allow-empty -m "chore: Probe direkter Push" && git push origin main
```

### Was der Code jetzt tut (PR #321)

* **`scripts/git_sync.sh`** kennt die Fehlerklasse **`schutz`**
  (`GH006`/`GH013`/`GH014`, `protected branch`, `required status check`,
  `changes must be made through a pull request`, `update-ref failed`, …).
  Sie wird **vor** `auth` geprüft, bricht **ohne Retry-Runden** ab und nennt im
  `::error::` dieses Runbook. Transientes (Netzwerk) und Non-Fast-Forward bleiben
  retrybar – nur die Regel-Ablehnung hört auf, sich als Wackelkontakt auszugeben.
* **`scripts/pflichtcheck_guard.py`** prüft im **grünen** Fall nach (best effort,
  nur GET, ändert nie das Urteil): aktives Ruleset mit Pflicht-Check auf dem
  Ziel-Zweig **ohne** Bypass-Akteur **und** Workflows, die selbst dorthin
  committen → `::warning::` „Schein-Sicherheit“ mit betroffener Workflow-Zahl,
  Folge und Reparaturweg. Genau dieser Fall war am 19.09.2026 blind.
* Regeln-Änderungen bleiben Menschen mit Admin-Rechten vorbehalten (C15,
  `docs/INCIDENT-2026-09-19-integritaets-lock.md`): Die Wache meldet, sie
  repariert nie selbst.

## Was die Live-Wache meldet

| Urteil | Bedeutung | Exit |
|---|---|---|
| `VERLANGT` | `main` verlangt `Integritäts-Siegel` (von GitHub Actions oder quellenfrei) | 0 |
| `FEHLT` | `main` verlangt andere Checks (z. B. noch `lock`), nicht diesen – Hinweis, wenn der verlangte Name die Job-ID ist | 1 |
| `FALSCHE_QUELLE` | Name stimmt, aber das Ruleset bindet ihn an eine andere App – der Actions-Lauf erfüllt ihn nie | 1 |
| `UNGESCHUETZT` | kein aktives Ruleset verlangt irgendeinen Status-Check auf `main` – das Siegel ist Deko | 1 |
| `NICHT_PRUEFBAR` | API nicht erreichbar oder Antwort unbrauchbar – **kein Urteil**, `::warning::`, Lauf bleibt grün (der Melder darf nicht selbst zum Vorfall werden) | 0 |

Bei Rot stehen im Log und in der Step-Summary: die Diagnose je Ruleset (Name,
Zustand, Ziel-Zweige, verlangte Checks) und die Reparatur in Klicks.

Bei **Grün** kann zusätzlich eine Warnung stehen – das Urteil bleibt dann 0:

| Meldung (trotz `VERLANGT`) | Bedeutung |
|---|---|
| `⚠️ Schein-Sicherheit: … ohne Bypass-Akteur` | Der Pflicht-Check gilt auch für direkte Pushes, entsteht aber nur in Pull Requests, und niemand darf vorbei: die Automation steht. Reparatur oben, Abschnitt „Direkte Pushes und Automation“ |

## Selbst prüfen

```bash
python3 scripts/pflichtcheck_guard.py --selftest          # 13 Fälle, kein Netz, schreibt nie
python3 scripts/governance_contract.py --selftest         # C1–C18 mit Kunstbefunden
python3 -m unittest scripts/tests/test_pflichtcheck.py -v  # Vertrag am echten Workflow + Mutationen
python3 scripts/pflichtcheck_guard.py --rules-file r.json # Urteil über eine gespeicherte Antwort
```
