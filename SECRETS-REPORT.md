# 🔐 Secrets-/Token-Alters-Wache
**Stand:** 2026-09-07

## Gesamt-Ampel: **AMBER**

| Secret | Status |
|---|---|
| `GROQ_API_KEY` | OK (6d) |
| `GEMINI_API_KEY` | OK (6d) |
| `PINTEREST_ACCESS_TOKEN` | UNBEKANNT |
| `MASTODON_ACCESS_TOKEN` | OK (3d) |
| `PINTEREST_TOKEN_KEY` | NICHT GENUTZT (via PINTEREST_ACCESS_TOKEN) |

## Befunde

| Ebene | Code | Meldung |
|---|---|---|
| AMBER | untracked | `PINTEREST_ACCESS_TOKEN` – Pinterest Access-Token: kein Erfolgs-Log (ausstehend, bitte --record-success einbinden) |

## Empfehlungen

1. **Pinterest:** Access-Token (30 Tage) automatisch via `pinterest_auth.py` erneuern; der Eintrag `last_success` beweist, dass der Refresh läuft.
2. **Workflows:** Nach jedem erfolgreichen Secret-Gebrauch `python3 scripts/secrets_age_guard.py --record-success <VAR>` in den Workflow einhängen (siehe Premium-Governance).
3. **Rote Befunde sofort prüfen:** Geheimes fehlt / zu alt = Kanal pinnt/toott/generiert silent nicht mehr.

_Automatisch erzeugt von `scripts/secrets_age_guard.py` am 2026-09-07._
