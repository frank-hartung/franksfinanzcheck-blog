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

## Selbst prüfen

```bash
python3 scripts/pflichtcheck_guard.py --selftest          # 9 Fälle, kein Netz, schreibt nie
python3 scripts/governance_contract.py --selftest         # C1–C18 mit Kunstbefunden
python3 -m unittest scripts/tests/test_pflichtcheck.py -v  # Vertrag am echten Workflow + Mutationen
python3 scripts/pflichtcheck_guard.py --rules-file r.json # Urteil über eine gespeicherte Antwort
```
