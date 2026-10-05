# Actions-Versionsdrift – dauerhaft geheilt (Premium, 05.10.2026)

**Auslöser:** Dependabot-PR **#571** „chore(deps): bump actions/setup-python from 5 to 7".

## Befund

Der PR berührte **eine** Datei (`.github/workflows/n8n-schaltwerk-bridge.yml`),
weil alle anderen Workflows längst auf `v7` standen – von Hand nachgezogen,
nachdem frühere Dependabot-Majors liegen blieben (`dependabot-automerge.yml`
mergt Majors bewusst nicht automatisch). Der Bestand war dadurch ein
Flickenteppich:

| Action | Bestand vorher | Fundstellen |
|---|---|---|
| `actions/setup-python` | `v7` (35×) **neben** `v6` (1×) | 36 |
| `actions/checkout` | `v5` (18×) **neben** `v4` (58×) | 76 + 1 SHA-Pin |
| `actions/setup-node` | `v5` (1×) **neben** `v4` (4×) | 5 |
| `actions/upload-artifact` | `v7` (15×) **neben** `v4` (2×) | 17 |

Solche Drift ist unsichtbar, bis eine abgekündigte Runner-Node-Laufzeit einen
einzelnen Nacht-Job tötet – typischerweise den, der am seltensten läuft.

## Heilung (drei Ebenen statt einer Zeile)

1. **Bestand vereinheitlicht** – 65 Referenzen in 58 Workflows auf den Kanon
   gehoben (`setup-python@v7`, `checkout@v5`, `setup-node@v5`,
   `upload-artifact@v7`). Die beiden bewussten **SHA-Pins**
   (`alerting-heartbeat.yml`, `alert-on-failure.yml`) und die lokalen
   Composite-Actions blieben unangetastet.
2. **Neue Wache `scripts/actions_version_guard.py`** – Report, `--fix`,
   `--dry-run`, `--json`, `--gate`, `--selftest` (Familienstandard).
   Regeln: **A1** eine Referenz je Action (Kanon = höchste im Repo vorhandene
   Major, damit EIN angenommener Dependabot-PR den Rest nachzieht),
   **A2** keine beweglichen Ziele (`@main`/`@master`/ohne Ref),
   **A3** 40-stellige SHA-Pins sind Absicht und tabu,
   **A4** lokale/Docker-Actions frei, **A5** Ausnahmen nur dokumentiert
   (`KANON_FIX`). Der Fix ist rein textuell – kein YAML-Round-Trip,
   also keine Umformatierung, keine verlorenen Kommentare.
3. **Dauerhaft verdrahtet**
   - `integrity-lock.yml` (läuft bei **jedem** Pull Request, auch bei jedem
     Dependabot-PR): Selbsttest + `--gate`. Teil-Bumps werden rot, bevor sie
     im `main` landen.
   - `scripts/tests/test_actions_version_guard.py` – 12 Vertragstests,
     inklusive „der Bestand ist drift-frei" und „das Gate hängt wirklich im
     PR-Workflow". Läuft über `unittest discover` in
     `publication-reliability-tests.yml`.
   - `.github/dependabot.yml`: Action-Updates werden **gruppiert**
     (`groups.github-actions`). Ein PR pro Woche statt Häppchen – damit
     entsteht die Teil-Merge-Drift gar nicht erst.

## Betrieb

```bash
python3 scripts/actions_version_guard.py            # Report
python3 scripts/actions_version_guard.py --gate     # CI-Urteil (Exit 1)
python3 scripts/actions_version_guard.py --fix      # vereinheitlichen
python3 scripts/actions_version_guard.py --selftest # Sabotage-Schutz
```

**Stand nach der Heilung:** `✅ Keine Drift – jede Action wird überall mit
derselben Version benutzt.` (13 Actions im Kanon, 0 Fundstellen).

## Zu PR #571

Der Inhalt von #571 ist hier vollständig enthalten (und darüber hinaus).
Der Dependabot-PR kann nach dem Merge dieses Zweigs geschlossen werden –
er wird beim nächsten Lauf ohnehin als erledigt erkannt.
