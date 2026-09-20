# Runbook: Pflicht-Check `Integritäts-Siegel` (PR-Schutz für `main`)

**Stand:** 20.09.2026 (Nachprüfung, Befund unverändert offen) · **Vertrag:** Governance-Regel **C18**
(`scripts/governance_contract.py`) · **Wache:** `scripts/pflichtcheck_guard.py`
· **Anlass:** [Integritäts-Vorfall](INCIDENT-2026-09-19-integritaets-lock.md),
PR #317 und Deploy-Ausfall #320 / PR #321.

## Aktueller Befund – Nachprüfung 20.09.2026 (read-only, ohne Admin-Recht)

Geprüft am **20.09.2026** mit dem Arena-Bot-Token. `GET /repos/…` meldet für
diesen Zugang `permissions: {"admin": false, "maintain": false, "pull": false,
"push": false, "triage": false}` – also **kein** `administration:write`.
Rulesets ändern bleibt damit Admin-Aufgabe (Governance-Regel **C15**: Regeln
ändert ein Mensch, die Wache repariert nie selbst). Der Zielzustand unten ist
vorbereitet und **nicht live angewendet**.

| Frage | Antwort (API-Beleg, 20.09.2026) |
|---|---|
| Verlangt `main` den Check `Integritäts-Siegel`? | **Nein.** `GET /rules/branches/main` liefert **vier** Einträge – je `deletion` + `non_fast_forward` aus #23710849 und #23705980. Kein `required_status_checks`, keine `pull_request`-Regel. |
| Ruleset **#23710849** „Integritäts-Lock (PR-Gate)“ | `enforcement: active`, Ziel `~DEFAULT_BRANCH` (keine Excludes), Regeln **nur** `deletion` + `non_fast_forward`. Angelegt 19.09. 22:19:24 UTC, zuletzt geändert 22:37:36 UTC. |
| Ruleset **#23705980** „main – Unveränderlichkeit (ohne Bypass)“ | `active`, ebenfalls nur Lösch-/Force-Push-Schutz – **unverändert beibehalten** (siehe Bypass-Warnung unten). |
| Ursprünglich beauftragte ID **#23695872** | weiterhin **HTTP 404** auf `GET /rulesets/23695872`. 404 allein beweist keine Löschung (auch fehlende Sichtbarkeit ist möglich). |
| Urteil der Live-Wache | `python3 scripts/pflichtcheck_guard.py --branch main` → **UNGESCHUETZT**, Exit 1: „Kein aktives Ruleset verlangt einen Status-Check auf dem Ziel-Zweig – `Integritäts-Siegel` entscheidet nichts, das Siegel ist Deko.“ |
| Harter Stopp selbst | **grün** – Schritt „Integritäts-Siegel prüfen (HARD STOP)“ lief in allen Läufen seit 19.09. 23:09 UTC erfolgreich; lokal: `integrity_guard.py --gate` → „43 Kerndateien entsprechen exakt dem signierten Stand“. |

**Zeitachse – Korrektur der Notiz „Zustand seit 19.09., ~20:42“.** Der
Meta-Schritt ist nicht seit 20:42 rot; um 20:42 starb ein anderer Schritt.
Belegt über die Jobs-API (`/actions/runs/<id>/jobs`, Schritt-Abschlüsse):

| Lauf (UTC) | Roter Schritt | Einordnung |
|---|---|---|
| 19.09. 20:42:36 · `35468218966` | **Schritt 4** `integrity_guard.py --gate` | HARD STOP (belegter Drift), Schritte 5/6 übersprungen – kein Pflicht-Check-Befund |
| 19.09. 20:44:43 · `35468323189` | keiner | **alle sechs Schritte grün** – der Branch-Schutz verlangte den Check zu diesem Zeitpunkt noch |
| 19.09. 23:09:30 · `35475323371` | **Schritt 6** `pflichtcheck_guard.py` | **erster** roter Pflicht-Check-Vertrag |
| 20.09. 14:51:11 · `35517752331` | Schritt 6 | Schritte 4 + 5 grün |
| 20.09. 15:05:20 · `35518477966` | Schritt 6 | Schritte 4 + 5 grün |

Der Pflicht-Check-Vertrag ist also seit dem Lauf **19.09. 23:09:30 UTC** rot –
zeitlich passend zum Ruleset-Wechsel 22:19/22:37 UTC (#23695872 → #23710849).
Einschränkung der Nachprüfung: Die Log-Texte der Läufe waren in der
Prüfumgebung nicht ladbar (`results-receiver.actions.githubusercontent.com`
antwortete mit `EOF`); die Einordnung stützt sich auf die Schritt-Abschlüsse,
nicht auf Log-Zitate.

**Frank muss die ID im angemeldeten Browser bestätigen.** Wenn #23695872 dort
noch existiert, genau diese reparieren; sonst das gleichnamige #23710849.
Nicht blind einen PUT auf eine alte ID senden und nicht still eine weitere
Kopie anlegen. Name allein identifiziert kein Ruleset.

## Der Zielvertrag (PR-Scoping, aber Automation bleibt schreibfähig)

| Ort | Eintrag | Prüfung |
|---|---|---|
| `scripts/governance_contract.py` | `PFLICHT_CHECK_NAME = "Integritäts-Siegel"` | Quelle des Namens |
| `.github/workflows/integrity-lock.yml` | `jobs.lock.name: Integritäts-Siegel`, `pull_request` auf `main`, keine Pfadfilter, kein Job-`if`, kein Gate-`continue-on-error`, `contents: read`, letzte Stufe `pflichtcheck_guard.py` | C18, jedes Qualitäts-Gate |
| Integritäts-Ruleset | Active, `~DEFAULT_BRANCH`, `deletion`, `non_fast_forward`, Check `Integritäts-Siegel` / App **15368**, `pull_request` mit **0 Approvals** | Live-Wache prüft Pflicht-Check und PR-Scoping |
| Bypass desselben Rulesets | **nur** `[{"actor_id":15368,"actor_type":"Integration","bypass_mode":"always"}]` | Nachprüfung: fehlender Actions-Bypass wird gewarnt |
| Governance | letzter Bot-Commit auf `main` **>24 h**, obwohl Writer-Crons liefen | ROT-Finding `automation_blocked` |

**PR-Scoping ist kein API-Schalter für „Status-Checks gelten nur in PRs“.**
Pflicht-Checks gelten auch für direkte Pushes. Die `pull_request`-Regel bindet
Menschen an einen PR; **0 Approvals** erlaubt das Ein-Personen-Repository, ohne
den Pflicht-Check abzuschalten. Nur der **Actions-Integration-Bypass `always`**
lässt die State-Commits der 31 direkt schreibenden Workflows durch.
`pull_request` als Bypass-Modus reicht für diese direkten Pushes **nicht**.

Keine `RepositoryRole: Write`-/Admin-Bypässe als Ersatz: Sie erweitern den
menschlichen Zugang und sind kein Nachweis des verlangten Actions-Bypasses.
Die frühere Rollen-Empfehlung aus PR #321 ist hiermit ersetzt.

**Wichtig:** Ein Bypass gilt für das **gesamte** Ruleset, also auch dessen
Lösch-/Force-Push-Regeln und botinitiierte PR-Merges. Ein zusätzliches aktives
Ruleset „main – Unveränderlichkeit (ohne Bypass)“ mit ausschließlich `deletion`
und `non_fast_forward` beibehalten: Dann bleiben auch Bots daran gebunden.
Nicht deaktivieren. Ein weiteres Ruleset mit PR-/Status-Pflichten ohne passenden
Actions-Bypass kann trotz korrektem Integritäts-Ruleset weiterhin blockieren.

## Dringlichkeit und eine Regel: nur in einem Zug

**Nachprüfung 20.09.2026, 15:52–15:59 UTC. Der Befund oben ist unverändert
offen – und die Reparatur ist weiterhin nicht von hier ausführbar.** Belege:

* `PUT /repos/…/rulesets/23710849` mit exakt
  [integritaets-lock-ruleset.json](integritaets-lock-ruleset.json) →
  **HTTP 403 „Resource not accessible by integration“**. `GET /repos/…` meldet
  für diesen Zugang `permissions: {"admin": false, …}` – kein
  `administration:write`. Damit ist belegt, dass die Reparatur nicht mit dem
  Arena-Bot-Token gelingt (C15: Regeln ändert ein Mensch). Der Versuch war
  idempotent: ein 403 ändert nichts, nachprüfbar über
  `GET …/rulesets/23710849` (unverändert `rules: [deletion, non_fast_forward]`,
  `updated_at: 2026-09-19T22:37:36Z`).
* **Das rote Kreuz blockiert derzeit keinen Merge.** PR **#327** wurde am
  **20.09.2026 15:43:18 UTC** gemergt, obwohl `Integritäts-Siegel` um 15:36:37
  UTC mit `conclusion: FAILURE` abgeschlossen hatte (`GET …/pulls/327`,
  `statusCheckRollup`; Merge-Commit `4b91938`). Ebenso #323–#325. Ein Pflicht-
  Check, der nicht im Branch-Schutz steht, hält GitHub nicht auf – die Anzeige
  ist Lärm, die Schutzwirkung **null**. Genau unter dieser Bedingung sind
  #316 und #320 entstanden.
* **Die Reparatur macht das Gate scharf – das ist der eigentliche Termin.**
  Nach dem PUT entscheiden zwei Dinge gleichzeitig: PRs warten auf das Siegel,
  **und** die direkt schreibenden Workflows brauchen den Bypass. Ohne Bypass
  friert `main` sofort ein (Vorfall 19.09.: elf Bot-Commits in 90 Minuten,
  dann Stille).

**Deshalb: kein Zwischenzustand, in dem der Pflicht-Check ohne Bypass live
ist.** Diese Automation schreibt im Minutentakt auf `main` – Commits vom
20.09.2026 (UTC): Content-Bot 15:43, 15:08, 10:32, 10:08 · Social-Autopilot
14:43 · Bot-Watchdog 13:09 · Willkommenstext-Bot 10:21.

* **API:** der **eine** PUT unten. Er ersetzt den gesamten Zielzustand, Check
  und Bypass landen im selben Request. Nicht erst den Check setzen und den
  Bypass „nachziehen“.
* **Klickweg:** Hier ist „einmal speichern“ **nicht** die richtige Reihenfolge –
  der Bypass kann abgelehnt werden (HTTP 422, siehe unten). Darum: **zuerst den
  Bypass allein speichern und nachsehen, ob er drinsteht**, erst danach
  Pflicht-Check und PR-Pflicht in einem zweiten Speichern. So schlägt ein
  abgelehnter Bypass fehl, solange `main` noch gar keinen Pflicht-Check hat –
  statt danach. Reihenfolge im Klickweg unten.
* Fällt der Bypass im Picker aus (Etappe 1): **STOPP**, kein Pflicht-Check. Dann
  ist es eine Grundsatzentscheidung – Abschnitt „Wenn der Bypass abgelehnt wird“.

Umgekehrt gilt: Solange der Befund offen ist, ist **nichts eingefroren**. Ein
bewusstes Aufschieben kostet keine Verfügbarkeit – es kostet die Schutzwirkung
des Siegels, bis der Pflicht-Check **mit** funktionierendem Bypass live ist.

## Reparatur für Frank – ohne Terminal

### Unterstützter GitHub-Klickweg

**Reihenfolge ist Sicherheit: erst der Bypass, dann der Pflicht-Check.** Beide
in umgekehrter Folge zu speichern erzeugt genau den Ausfall von #320. Und: Der
Bypass kann abgelehnt werden (siehe Warnung unten) – dann muss er **vor** dem
Pflicht-Check auffallen, nicht danach.

**Etappe 1 – Bypass allein probehalber speichern (entscheidender Test):**

1. [Repository → Settings → Rules → Rulesets](https://github.com/frank-hartung/franksfinanzcheck-blog/settings/rules)
   öffnen, **„Integritäts-Lock (PR-Gate)“** wählen und ID in der URL bestätigen
   (bei der letzten Abfrage: **23710849**, ursprünglicher Auftrag: **23695872**).
2. Target branches: **Include default branch** (`~DEFAULT_BRANCH`), keine
   Excludes. **Restrict deletions** und **Block force pushes** beibehalten.
3. Bypass list → **Add bypass** → im Suchfeld **GitHub Actions** suchen,
   auswählen, **Add Selected**. Modus **Always allow** beibehalten – **nicht**
   auf „For pull requests only“ umstellen, das reicht für direkte Pushes nicht.
   Keine Write-/Admin-Rolle als Ersatz.
4. Enforcement **Active** → **Save changes**.

   Jetzt ist `main` noch **nicht** strenger geschützt als vorher (es kommt nur
   ein Bypass dazu), der Test ist also risikolos. Ergebnis prüfen:
   Ruleset erneut öffnen – steht **GitHub Actions** mit **Always** in der
   Bypass-Liste?
   * **Ja** → weiter mit Etappe 2.
   * **Nein** (Eintrag fehlt, Picker bietet es nicht an, Fehlermeldung wie
     *„Actor GitHub Actions integration must be part of the ruleset source or
     owner organization“*) → **STOPP.** Etappe 2 nicht ausführen. Der
     Pflicht-Check ohne funktionierenden Bypass friert `main` ein. Weiter bei
     „Wenn der Bypass abgelehnt wird“.

**Etappe 2 – Pflicht-Check und PR-Pflicht, ein Speichern:**

5. Dasselbe Ruleset erneut öffnen. **Require status checks to pass** aktivieren
   und **`Integritäts-Siegel`** hinzufügen, Quelle **GitHub Actions**.
   „Require branches to be up to date before merging“ **aus** lassen.
   (Nachprüfung 20.09.: Es gibt keinen alten Check `lock` mehr zum Entfernen –
   `GET …/rulesets/23710849` meldet nur `deletion` und `non_fast_forward`.)
6. **Require a pull request before merging** aktivieren, **Required approvals: 0**;
   Code-Owner-/Last-Push-/Thread-Resolution-Zusatzpflichten aus lassen.
7. Bypass-Liste unverändert lassen (**GitHub Actions**, **Always**).
   Enforcement **Active** → **einmal** **Save changes**. Das separate
   Unveränderlichkeits-Ruleset #23705980 unverändert aktiv lassen.
8. Nachweis: `GET …/rules/branches/main` muss jetzt `required_status_checks`
   **und** `pull_request` zeigen, `GET …/rulesets/23710849` den Bypass. Dann im
   PR **Integritäts-Siegel → Re-run** und einen liegengebliebenen
   Writer-Workflow (z. B. Deploy oder Social-Autopilot) erneut ausführen und
   **dessen State-Commit auf `main`** prüfen. Ein grüner gh-pages-Deploy allein
   beweist den Bypass nach der Publish-Prioritäts-Änderung **nicht mehr**.

### Wenn der Bypass abgelehnt wird

**Beobachtet am 20.09.2026 von Frank im angemeldeten Browser: Der
„Add bypass“-Picker bietet „GitHub Actions“ nicht an.** Das bestätigt die
Recherche – Etappe 1 ist damit an ihrem Endpunkt, Etappe 2 darf nicht
ausgeführt werden.

Die GitHub-Doku nennt als bypass-fähig: Repository-/Org-/Enterprise-Admins,
Maintain-/Write-Rollen, seit 07.05.2026 auch **einzelne User**, Teams,
**GitHub Apps** und Dependabot. **GitHub Actions steht nicht in dieser Liste** –
`github-actions[bot]` ist eine Systemidentität, keine installierbare App, und
steht deshalb im Picker nicht zur Auswahl. Passend dazu dokumentieren mehrere
unabhängige Berichte (u. a. 14.09.2026) für genau diesen Bypass-Aktor
**HTTP 422**: *„Actor GitHub Actions integration must be part of the ruleset
source or owner organization“*; für **User-eigene** Repositories ohne
Organisation wird er als nicht setzbar beschrieben. Dieses Repository ist
user-eigen (`frank-hartung/…`).

**Ungeprüft:** Der API-Weg ist von hier nicht testbar – `PUT`/`POST` auf die
Rulesets antworten mit **403**, `GET /user` ebenfalls, also ist kein
Wegwerf-Repo möglich. Wer einen Admin-Token hat, kann die Frage mit dem **einen**
PUT unten endgültig klären: **422** bestätigt den Befund und ändert nichts,
**200** würde bedeuten, dass der Picker nur weniger kann als die API.

**Folge:** Der Zielzustand dieses Runbooks – Pflicht-Check **plus** Bypass
`Integration 15368 / always` – ist auf diesem Repository voraussichtlich **nicht
installierbar**. Der Pflicht-Check darf deshalb **nicht** scharf gestellt
werden: Ohne Bypass friert er `main` ein (Vorfall 19.09., #320). Das rote Kreuz
bleibt vorerst bestehen und blockiert weiterhin keinen Merge.

### Entscheidung danach – erst proben, dann umbauen

**Reihenfolge: erst beweisen, dass ein Bypass funktioniert, dann 32 Workflows
anfassen.** Nicht umgekehrt.

1. **Probe (billig, wenige Minuten):** Eigene GitHub App anlegen
   (Settings → Developer settings → GitHub Apps), `Contents: read and write`,
   installieren auf diesem Repository. App in die Bypass-Liste des Rulesets
   eintragen – **ohne** Pflicht-Check. Dann **ein** Test-Workflow, der sein Token
   mit `actions/create-github-app-token@v1` erzeugt und damit einen Commit auf
   `main` pusht. Erst wenn dieser Push durchgeht, ist bewiesen, dass ein
   Integration-Bypass hier überhaupt wirkt.
2. **Erst dann der Umbau.** Nachprüfung 20.09.2026: **32 Workflows** pushen
   direkt auf `main`, und zwar **alle** über `scripts/git_sync.sh --push-only` –
   kein einziger pusht roh (die beiden `git push`-Fundstellen in
   `agent-reach-research.yml` und `ki-redaktion.yml` sind Kommentare, beide
   Workflows rufen `git_sync.sh`). 32 Workflows haben `contents: write`, das
   Repository hat 48 Workflows. **Kein** einziger der 48
   Workflows nutzt heute ein App-Token (`grep` nach
   `create-github-app-token`/`APP_PRIVATE_KEY`/`app-id:` → keine Treffer).
   **Engpass ist `scripts/git_sync.sh`:** Das Skript nimmt kein Token entgegen –
   es liest `BRANCH`, `MSG`, `GIT_USER`, `GIT_MAIL`, `DRY_RUN`, `PUSH_ONLY`,
   `GIT_SYNC_*`, aber weder `GITHUB_TOKEN` noch `GH_TOKEN`; es pusht über das
   vorkonfigurierte `origin`-Remote, also mit dem eingebauten `GITHUB_TOKEN`.
   Weil es der einzige Push-Weg ist, ist Token-Unterstützung **dort** die halbe
   Arbeit; die andere Hälfte bleibt, dass jeder der 32 Workflows sein App-Token
   selbst erzeugen und übergeben muss.
3. **Erst wenn alle 32 schreiben können**, Pflicht-Check und PR-Pflicht
   scharfstellen (Etappe 2).

**Wichtig, und bisher nirgends belegt:** Ein App-Bypass gilt für die
**App-Identität**, nicht für `github-actions[bot]`. Solange ein Workflow mit
`GITHUB_TOKEN` pusht, nützt ihm der App-Bypass nichts. Genau deshalb ist die
Probe in Schritt 1 Pflicht und nicht optional.

Weitere Auswege, alle **nicht verifiziert**: **Deploy-Key** als Bypass-Aktor
(SSH- statt HTTPS-Push; von Dritten berichtet). **Organisation** als
Ruleset-Quelle – der 422-Fehlermeldung nach wäre der Actions-Aktor dort
zulässig, bedeutet aber einen Owner-Wechsel. Ein **PAT mit
`bypass-pull-request-requirements`** oder eine **Write-/Admin-Rolle** im Bypass
würde technisch wahrscheinlich genügen, widerspricht aber dem Zielvertrag oben
(„nur Integration 15368“) und erweitert den menschlichen Zugang – das ist eine
Governance-Entscheidung (C15), keine Reparatur.

Fällt die Entscheidung auf „kein Umbau“, ist das ein **dokumentierter
Dauerzustand**, kein offener Mangel: Der Pflicht-Check-Vertrag ist dann auf
diesem Repository nicht erfüllbar, und `pflichtcheck_guard.py` sollte das als
bekannt melden statt als roten Vorfall. Bis dahin bleibt er rot – korrekt, aber
lärmend.

Der `pflichtcheck_guard.py` verlangt in diesem Fall weiter `VERLANGT` und bleibt
rot. Das ist korrekt: Er soll nicht grün melden, was nicht schützt. Die
Governance-Wache `automation_blocked` fängt den umgekehrten Fall ab.

### Exakter Admin-API-Request (vollständiger Ersatz, keine Teiländerung)

**Zur angefragten „Browser-API-Konsole“:** `https://github.com/settings/api`
lieferte bei der Prüfung eine 404-Seite. Eine dort verfügbare, authentifizierte
REST-Konsole ist nicht verifiziert. Daher gibt es hier bewusst **keinen als
funktionierend ausgegebenen JavaScript-Einfügebefehl**. Ein `fetch` auf
`api.github.com` wird durch die GitHub-Browser-Anmeldung allein nicht zum
Admin-Request. Keine Tokens in Chat, Repository oder fremde Browser-Konsole kopieren.
Der oben beschriebene GitHub-Klickweg ist der terminallose Reparaturweg.

Für einen tatsächlich verfügbaren, bereits authentifizierten Admin-API-Client:
**Methode PUT**, URL nach ID-Prüfung (aktueller sichtbarer Kandidat):

```text
https://api.github.com/repos/frank-hartung/franksfinanzcheck-blog/rulesets/23710849
```

Falls Frank **#23695872** noch sehen kann, stattdessen:

```text
https://api.github.com/repos/frank-hartung/franksfinanzcheck-blog/rulesets/23695872
```

Header: `Accept: application/vnd.github+json`, `Content-Type: application/json`,
`X-GitHub-Api-Version: 2022-11-28`. Authentifizierung separat durch den Admin-Client
mit **Administration: write**, nie durch den Arena-Token. **Body exakt:**

```json
{
  "name": "Integritäts-Lock (PR-Gate)",
  "target": "branch",
  "enforcement": "active",
  "bypass_actors": [
    { "actor_id": 15368, "actor_type": "Integration", "bypass_mode": "always" }
  ],
  "conditions": {
    "ref_name": { "include": ["~DEFAULT_BRANCH"], "exclude": [] }
  },
  "rules": [
    { "type": "deletion" },
    { "type": "non_fast_forward" },
    {
      "type": "required_status_checks",
      "parameters": {
        "strict_required_status_checks_policy": false,
        "do_not_enforce_on_create": false,
        "required_status_checks": [
          { "context": "Integritäts-Siegel", "integration_id": 15368 }
        ]
      }
    },
    {
      "type": "pull_request",
      "parameters": {
        "required_approving_review_count": 0,
        "dismiss_stale_reviews_on_push": false,
        "require_code_owner_review": false,
        "require_last_push_approval": false,
        "required_review_thread_resolution": false
      }
    }
  ]
}
```

Maschinenlesbar derselbe Body: [integritaets-lock-ruleset.json](integritaets-lock-ruleset.json).
Regressionstests prüfen Identität von Runbook und Datei sowie Regeln, Bypass und PR-Vertrag.

### Optional: derselbe Zielzustand über `gh` (eigener Admin-Zugang)

Wer `gh` mit einem **eigenen** Admin-Token benutzt, sendet exakt die versionierte
Datei – kein handgetipptes JSON, keine zweite Wahrheit. Niemals mit dem
Arena-Bot-Token (kein `administration:write`) und niemals mit einem Token, der
in Chat, Issue oder fremder Konsole stand:

```bash
ID=23710849   # vorher per GET/Browser bestätigen – falls sichtbar: 23695872
R=repos/frank-hartung/franksfinanzcheck-blog/rulesets/$ID

gh api "$R" --jq '{id, name, enforcement, conditions, rules: [.rules[].type], bypass_actors}'
gh api --method PUT "$R" --input docs/integritaets-lock-ruleset.json
gh api "$R" --jq '{id, name, enforcement, conditions, rules: [.rules[].type], bypass_actors}'
python3 scripts/pflichtcheck_guard.py --branch main   # muss VERLANGT melden (Exit 0)
```

`--input` sendet die Datei unverändert; `scripts/tests/test_ruleset_restoration.py`
prüft, dass sie mit dem JSON-Block dieses Runbooks identisch bleibt. 404/403 ist
**kein** Erfolg (falsche ID oder fehlendes Recht) – dann nicht mit POST
„nachbessern“. Mit dem Arena-Bot-Token ist **403 der erwartete Ausgang**
(„Resource not accessible by integration“, belegt 20.09.2026): Der Aufruf beweist
dann nur, dass die Reparatur Admin-Sache bleibt. Er ist außerdem unschädlich –
ein 403 verändert das Ruleset nicht.

**Ein Request, ein Zustand: Check und Bypass gehören zusammen.** Der PUT trägt
`required_status_checks` **und** `bypass_actors` in einem Aufruf – im Gegensatz
zum Klickweg, der den Bypass bewusst **zuerst allein** probehalber setzt, weil
er abgelehnt werden kann. Genau das ist der Grund, die versionierte Datei zu
senden statt Teiländerungen zu tippen: Ein Zwischenzustand „Pflicht-Check live,
Bypass fehlt“ friert `main` sofort ein (Vorfall 19.09., #320). Wer die
Reparatur stückelt – Check vor Bypass –, erzeugt den Ausfall, den das Ruleset
verhindern soll.

**PUT ersetzt den Zielzustand vollständig.** Vorher GET derselben URL, Identität
und vorhandene Regeln prüfen; danach GET und den ganzen Zielzustand vergleichen,
insbesondere `bypass_actors`, `rules` und `conditions`. Bei 404/403 nicht als Erfolg
werten und nicht mit POST eine vermeintliche Reparatur vortäuschen.

`strict_required_status_checks_policy: false` ist bewusst: Ein-Personen-Repo mit
Squash-Merges; nicht vor jedem Merge manuell auf den neuesten `main` bringen.
Der Gate-Lauf prüft den Merge-Stand.

## Direkte Pushes und Automation (Vorfall 19.09.2026)

Ab 10:00:03 verlangte #23695872 das Siegel auf `main`, ohne Bypass. Der Check
entsteht nur bei PRs/manuell, nicht auf direkten Pushes. Vorher elf Bot-Commits
in 90 Minuten, danach Stille. Deploy #998 (Run `35437446077`) scheiterte bei
„Gate-Heilungen committen“, die Veröffentlichung wurde übersprungen; auch
Social-Autopilot `35448944197` scheiterte. Betroffen: 31 Workflows, nicht nur Deploy.
Die damalige Wache meldete gleichzeitig „Vertrag erfüllt“.

Heute sind drei getrennte Schutzmechanismen zuständig:

* **`git_sync.sh`** erkennt Branch-Schutz (`GH006`/`GH013`/`GH014`, PR-/Check-
  Pflicht) als `schutz`, bricht ohne sinnlose Netzwerk-Retries ab und nennt
  dieses Runbook. Außerhalb des Deploy-State-Schritts bleibt sein Fehler hart.
* **Publish-Priorität in `deploy.yml`:** Nur der fehlgeschlagene Push in
  „Gate-Heilungen committen (konvergent)“ wird abgefangen, mit **`::error::`**
  annotiert und ohne falsche Erfolgsmeldung fortgesetzt. Lokaler Commit,
  Rebuild, Integritäts-/Inhalts-Gates und gh-pages-Deploy bleiben harte Schritte.
  Kein `if: always()`/pauschales `continue-on-error`: kaputte Inhalte gehen nicht
  live. Persistenz ist nicht Veröffentlichung; beim nächsten Lauf werden die
  Heilungen erneut konvergent versucht.
* **`pflichtcheck_guard.py`:** PR-Vertrag plus exakte Actions-Bypass-Nachprüfung;
  davon getrennt **`--automation`** als Betriebssignal an das Governance-Gate.
  Regeln-Änderungen bleiben Admin-Aufgabe (C15); die Wache repariert nie selbst.

## Neue Governance-Wache: „Automation durch Branch-Schutz blockiert“

`premium-governance.yml` misst **nach dem Ledger-Reset und vor `--decide`**.
`actions: read` erlaubt die Cron-Abfrage; die Messung benutzt nur GET.

* Branch immer **`main`**, niemals PR-Head oder `gh-pages`.
* Letzter Bot-Commit: API-Bot-Identität (Autor/Committer) oder die expliziten
  `git config user.email`-Identitäten der direkt schreibenden Workflows,
  einschließlich `Content-Bot`/`Social-Autopilot`. **Committer-Zeit** in UTC,
  nicht ein möglicherweise altes Autorendatum; menschliche Commits setzen die
  Uhr nicht zurück. Keine pauschale Suche nach „bot“ im Namen.
* **ROT** bei Alter **strikt >24 h** **und** mindestens einem abgeschlossenen
  `schedule`-Lauf eines direkt schreibenden Workflows auf `main`, gestartet in
  den letzten 24 h und nach dem letzten Bot-Commit. Erfolgreiche wie
  fehlgeschlagene Crons zählen; queued/laufende, manuelle und reine Lese-Läufe
  nicht. Exakt 24 h bleibt grün.
* Code **`automation_blocked`**, Befundtabelle `RED`, Zeit/Alter und Run-ID als
  Evidenz. Governance erstellt/aktualisiert seinen gebündelten Report; mit
  `--fail-on red` wird der Lauf rot. Keine neue separate Issue-Schleife.
* Das ist ein **Blockade-Verdacht**, kein kausaler Beweis: Auch legitime No-op-
  Crons können ohne Commit enden. Push-Log auf `schutz`/GH013 und Rulesets prüfen.
* API-/Berechtigungs-/Formatfehler, fehlender Bot-Nachweis, erschöpfte Pagination
  oder alte Bot-Commits ohne relevante Cron-Evidenz → **INFO** (`probe_skipped`),
  kein falsches Rot/Grün. Pagination: maximal 10 × 100 Commits bzw. Runs;
  ein tatsächlich gefundener passender Cron genügt als positive Evidenz.
* Die Wache läuft mit Premium-Governance **wöchentlich oder manuell**.
  24 h ist die Befundschwelle, **keine Zusage eines täglichen Alarms**.

Der Report wird in `/tmp/automation-report.md` frisch erzeugt und ins Ledger
emittiert; auch bei blockiertem späterem Ledger-State-Push existieren Log,
Job-Summary und Governance-Issue bereits. Kein neuer Root-Report.

## Was die PR-Live-Wache meldet

| Urteil | Bedeutung | Exit |
|---|---|---|
| `VERLANGT` | Check verlangt; im Live-Aufruf zusätzlich PR-Pflicht mit 0 Approvals | 0 |
| `FEHLT` | Andere Checks, etwa die alte Job-ID `lock` | 1 |
| `FALSCHE_QUELLE` | Check an falsche App gebunden | 1 |
| `UNGESCHUETZT` | Kein Status-Check auf dem Ziel | 1 |
| `PR_SCOPING_FEHLT` | Check vorhanden, aber keine `pull_request`-Regel mit 0 Approvals | 1 |
| `NICHT_PRUEFBAR` | API/Antwort unbrauchbar, Warnung statt erfundenem Urteil | 0 |

Die Namensprüfung akzeptiert weiterhin quellenfreie Checks; **der Admin-Zielzustand
ist strenger** und bindet ausdrücklich App 15368. Bei `VERLANGT` prüft die Wache
zusätzlich aktive Rulesets: PR-/Status-Regeln ohne **Actions/15368/always** und
vorhandene Direkt-Pusher → `::warning::` „Schein-Sicherheit“ (Exit bleibt 0).
Fremde Rollen/Apps und `pull_request`-Bypässe unterdrücken diese Warnung nicht.
Fehlt das Feld `bypass_actors` in einer API-Antwort (eingeschränkte Sichtbarkeit),
meldet die Wache „nicht prüfbar“, nicht „kein Bypass“; nur explizites `null`/`[]`
belegt eine leere Liste. API-Ausfälle dieser Zusatzprüfung sind best effort; die Betriebswache ist
separat und wird nicht an den PR-Check gekoppelt.

## Zustand prüfen und Regression (Entwicklung, optionales Terminal)

```bash
# Read-only, nach jeder Admin-Reparatur:
gh api repos/frank-hartung/franksfinanzcheck-blog/rulesets
gh api repos/frank-hartung/franksfinanzcheck-blog/rulesets/23710849
gh api repos/frank-hartung/franksfinanzcheck-blog/rules/branches/main
python3 scripts/pflichtcheck_guard.py --branch main
python3 scripts/pflichtcheck_guard.py --automation

# Offline und ohne Schreibzugriff am Bestand:
python3 scripts/pflichtcheck_guard.py --selftest
python3 scripts/governance_gate.py --selftest
python3 scripts/governance_contract.py --selftest
python3 scripts/governance_contract.py --quick
python3 -m unittest scripts/tests/test_pflichtcheck.py scripts/tests/test_ruleset_restoration.py -v
python3 -m unittest discover -s scripts/tests -v
python3 scripts/pflichtcheck_guard.py --rules-file r.json # effektive Branch-Regeln (Liste)
```

Kein manueller Probe-Push auf `main`: **Menschen sollen jetzt gerade einen PR
benutzen**. Automations-Nachweis über einen Writer-Workflow mit wirklichem
State-Commit, nicht über einen leeren Commit unter Franks Identität.

## Umbenennen – nur zusammen mit dem Ruleset

1. Im PR `PFLICHT_CHECK_NAME` und `jobs.lock.name` gemeinsam ändern (C18),
   Runbook, Payload und Tests nachziehen. Keine Pfadfilter/Skip-Schalter einbauen.
2. Ruleset im selben abgestimmten Vorgang umstellen. Ein neuer Workflow-Name
   erfüllt den alten Pflicht-Check nie („Expected“). Entweder bisherigen PR
   noch unter altem Namen mergen und sofort Ruleset umstellen, oder Ruleset
   vorher auf den bereits im PR berichteten neuen Namen wechseln.
3. Effektive Branch-Regeln nachlesen, Gate erneut ausführen. Bypass und PR-Pflicht
   dabei unverändert vollständig erhalten. Keine Schreibrechte für den PR-Job.
