# 🔐 Secrets-/Token-Alters-Wache
**Stand:** 2026-09-01

## Gesamt-Ampel: **RED**

| Secret | Status |
|---|---|
| `GROQ_API_KEY` | UNBEKANNT |
| `GEMINI_API_KEY` | UNBEKANNT |
| `PINTEREST_ACCESS_TOKEN` | UNBEKANNT |
| `MASTODON_ACCESS_TOKEN` | UNBEKANNT |
| `PINTEREST_TOKEN_KEY` | FEHLT |

## Befunde

| Ebene | Code | Meldung |
|---|---|---|
| AMBER | untracked | `GROQ_API_KEY` – Groq KI-Key: kein Erfolgs-Log (ausstehend, bitte --record-success einbinden) |
| AMBER | untracked | `GEMINI_API_KEY` – Gemini KI-Key: kein Erfolgs-Log (ausstehend, bitte --record-success einbinden) |
| AMBER | untracked | `PINTEREST_ACCESS_TOKEN` – Pinterest Access-Token: kein Erfolgs-Log (ausstehend, bitte --record-success einbinden) |
| AMBER | untracked | `MASTODON_ACCESS_TOKEN` – Mastodon Access-Token: kein Erfolgs-Log (ausstehend, bitte --record-success einbinden) |
| RED | missing | `PINTEREST_TOKEN_KEY` – Pinterest Verschlüsselungs-Key (`PINTEREST_TOKEN_KEY`) fehlt im Env |

## Empfehlungen

1. **Pinterest:** Access-Token (30 Tage) automatisch via `pinterest_auth.py` erneuern; der Eintrag `last_success` beweist, dass der Refresh läuft.
2. **Workflows:** Nach jedem erfolgreichen Secret-Gebrauch `python3 scripts/secrets_age_guard.py --record-success <VAR>` in den Workflow einhängen (siehe Premium-Governance).
3. **Rote Befunde sofort prüfen:** Geheimes fehlt / zu alt = Kanal pinnt/toott/generiert silent nicht mehr.

_Automatisch erzeugt von `scripts/secrets_age_guard.py` am 2026-09-01._
