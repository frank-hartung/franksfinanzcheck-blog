# 🔐 Secrets-/Token-Alters-Wache
**Stand:** 2026-09-12 · **Modus:** Nachweis-Log (deklariert)

## Gesamt-Ampel: **RED**

| Secret | Status | Nachweis |
|---|---|---|
| `GROQ_API_KEY` | FEHLT | – |
| `GEMINI_API_KEY` | FEHLT | – |
| `PINTEREST_ACCESS_TOKEN` | FEHLT | – |
| `MASTODON_ACCESS_TOKEN` | FEHLT | – |
| `PINTEREST_TOKEN_KEY` | NICHT EINGERICHTET | – |
| `PINTEREST_REFRESH_TOKEN` | NICHT EINGERICHTET | – |
| `UMAMI_API_TOKEN` | NICHT EINGERICHTET | – |

## Befunde

| Ebene | Code | Meldung |
|---|---|---|
| RED | missing | `GROQ_API_KEY` – Groq KI-Key (`GROQ_API_KEY`) fehlt im Env – der Kanal kann nicht arbeiten |
| RED | missing | `GEMINI_API_KEY` – Gemini KI-Key (`GEMINI_API_KEY`) fehlt im Env – der Kanal kann nicht arbeiten |
| RED | missing | `PINTEREST_ACCESS_TOKEN` – Pinterest Access-Token (`PINTEREST_ACCESS_TOKEN`) fehlt im Env – der Kanal kann nicht arbeiten |
| RED | missing | `MASTODON_ACCESS_TOKEN` – Mastodon Access-Token (`MASTODON_ACCESS_TOKEN`) fehlt im Env – der Kanal kann nicht arbeiten |

<details><summary>ℹ️ Hinweise (kein Handlungsbedarf)</summary>

- `PINTEREST_TOKEN_KEY` – Pinterest Verschlüsselungs-Key fehlt – optionaler Kanal, kein Betrieb, kein Befund (einrichten: GitHub-Secret `PINTEREST_TOKEN_KEY`)
- `PINTEREST_REFRESH_TOKEN` – Pinterest Refresh-Token (Auto-Erneuerung) fehlt – optionaler Kanal, kein Betrieb, kein Befund (einrichten: GitHub-Secret `PINTEREST_REFRESH_TOKEN`)
- `UMAMI_API_TOKEN` – Umami Analytics-API-Token fehlt – optionaler Kanal, kein Betrieb, kein Befund (einrichten: GitHub-Secret `UMAMI_API_TOKEN`)

</details>

## Empfehlungen

1. Keine Maßnahmen – Wache läuft wöchentlich mit Live-Probe (siehe `premium-governance.yml`).

_Automatisch erzeugt von `scripts/secrets_age_guard.py` am 2026-09-12._
