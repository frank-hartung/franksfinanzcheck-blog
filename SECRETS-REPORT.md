# 🔐 Secrets-/Token-Alters-Wache
**Stand:** 2026-09-07 · **Modus:** Live-Probe (--verify)

## Gesamt-Ampel: **RED**

| Secret | Status | Nachweis |
|---|---|---|
| `GROQ_API_KEY` | VERIFIZIERT (live, 2026-09-07) | API 200 |
| `GEMINI_API_KEY` | VERIFIZIERT (live, 2026-09-07) | API 200 |
| `PINTEREST_ACCESS_TOKEN` | TOT (live-Probe) | API-Lehnung |
| `MASTODON_ACCESS_TOKEN` | VERIFIZIERT (live, 2026-09-07) | API 200 |
| `PINTEREST_TOKEN_KEY` | NICHT GENUTZT (via PINTEREST_ACCESS_TOKEN) | – |
| `UMAMI_API_TOKEN` | NICHT EINGERICHTET | – |

## Befunde

| Ebene | Code | Meldung |
|---|---|---|
| RED | dead | `PINTEREST_ACCESS_TOKEN` – Pinterest Access-Token: Live-Check abgelehnt – Pinterest-Token abgelaufen/ungültig (401) |

<details><summary>ℹ️ Hinweise (kein Handlungsbedarf)</summary>

- `UMAMI_API_TOKEN` – Umami Analytics-API-Token fehlt – optionaler Kanal, kein Betrieb, kein Befund (einrichten: GitHub-Secret `UMAMI_API_TOKEN`)

</details>

## Empfehlungen

1. **Token tot (401/403):** sofort erneuern – Pinterest via `python3 scripts/pinterest_auth.py --auth-url` + `--exchange <code>`, danach `--verify` zur Gegenprobe.

_Automatisch erzeugt von `scripts/secrets_age_guard.py` am 2026-09-07._
