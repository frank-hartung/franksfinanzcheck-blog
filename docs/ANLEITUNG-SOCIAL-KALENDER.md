# 🗓️ Veröffentlichungskalender je Social-Media-Kanal

**Auftrag (Frank, 29.09.2026):** „Ich benötige Veröffentlichungskalender für
jeden einzelnen Social-Media-Kanal.“ – dauerhaft, auf Premium-Niveau einer
Profi-Agentur.

Dieses Modul macht die vollautomatische Redaktion des Social-Autopiloten
**sichtbar**: Für jeden Kanal gibt es einen eigenen, laufend aktualisierten
Veröffentlichungskalender – als lesbare Markdown-Datei **und** als abonnierbare
`.ics`-Datei für dein Handy, Google-, Apple- oder Outlook-Kalender.

Du musst nichts pflegen. Die Kalender werden nach jedem Autopilot-Lauf
automatisch neu geschrieben.

---

## Was liegt wo?

Alle Kalender liegen versioniert unter **`data/social/kalender/`**:

| Datei | Inhalt |
|---|---|
| `UEBERSICHT.md` | Alle Kanäle auf einen Blick + gemeinsame 14-Tage-Timeline |
| `<kanal>.md` | Lesbarer Kalender eines Kanals (kommende & vergangene Beiträge) |
| `<kanal>.ics` | Derselbe Kalender zum **Abonnieren** |
| `video.md` / `video.ics` | Produktionsrhythmus für Reels & Shorts |
| `README.md` | Kurzüberblick |

`<kanal>` ist jeweils: `mastodon`, `bluesky`, `linkedin`, `x`, `threads`,
`facebook`, `instagram`, `pinterest`, `telegram`, `reddit`.

Jeder Kalender trägt oben die **verbindlichen Kanal-Kriterien** aus dem Playbook
(`data/social/channels.yaml`): Zeichenbudget, Hashtag-Regel, Emoji-Grenze,
Link-Position, Bildpflicht, Sendetage/-zeiten und Frequenz. So ist immer
sichtbar, nach welchen Regeln der Autopilot für diesen Kanal veröffentlicht.

---

## Woher die Termine kommen

Die Kalender erfinden nichts. Sie sind eine **lesbare Ansicht** des
versionierten Redaktionsplans:

```
data/social/channels.yaml   → Regeln je Kanal (Kriterien, Sendezeiten)
data/social/schedule.yaml   → der 14-Tage-Plan (vom Autopilot erzeugt)
data/social/state.yaml      → was bereits gesendet wurde
        │
        ▼
scripts/social_calendar.py  → data/social/kalender/*.md + *.ics
```

Der Plan selbst wird vom **Social-Autopilot** (`scripts/social_studio.py`) alle
2 Stunden fortgeschrieben; die Shorts-Schmiede (`scripts/social_video.py`)
liefert den Video-Rhythmus.

---

## Legende

| Symbol | Bedeutung |
|---|---|
| ⏳ | geplant (kommt noch) |
| ✅ | veröffentlicht |
| ⚪ | Standby – der Kanal wartet nur noch auf seine Zugangsdaten (Secret) |
| 🚫 | zurückgestellt (Autopilot hat blockiert, z. B. Artikel nicht mehr im Bestand) |

---

## Einen Kanal-Kalender im Handy abonnieren

Die Feeds liegen live unter einer stabilen HTTPS-Adresse (nach dem nächsten
Deploy von `main`):

- **Abo-Seite mit Ein-Klick-Buttons:** `https://franksfinanzcheck.de/kalender/`
- **Einzelfeed:** `https://franksfinanzcheck.de/kalender/<kanal>.ics`
- **Ein-Klick-Abo (Apple/Outlook):** `webcal://franksfinanzcheck.de/kalender/<kanal>.ics`

So abonnierst du (das Abo aktualisiert sich dann von selbst):

- **iPhone / Mac / Outlook:** auf der Abo-Seite „Abonnieren“ tippen – die
  `webcal://`-Adresse öffnet direkt die Kalender-App.
- **Google Kalender:** „Google Kalender“-Button (oder manuell: Andere Kalender →
  *Per URL* → die `https://…/<kanal>.ics`-Adresse einfügen).

> Hinweis: Die Live-Adresse funktioniert, sobald der Branch nach `main`
> gemergt und die Seite deployt wurde (GitHub Pages, Custom Domain). Bis dahin
> lassen sich die `.ics`-Dateien aus `data/social/kalender/` auch direkt in die
> Kalender-App importieren (Einmal-Schnappschuss).

---

## Selbst neu erzeugen

```bash
# alle Kalender neu schreiben
npm run social:kalender
# oder direkt:
python3 scripts/social_calendar.py --build

# nur einen Kanal:
python3 scripts/social_calendar.py --build --channel mastodon

# Fail-closed-Selbsttest (läuft auch im Workflow, bevor etwas geschrieben wird):
npm run test:social:kalender
```

---

## Automatik

- **`social-autopilot.yml`** (alle 2 h): baut nach jedem Lauf die Kalender neu
  und committet `data/social/kalender/` mit.
- **`social-video.yml`** (Di + Sa): aktualisiert `video.md` / `video.ics`.

Damit bleiben die Kalender **dauerhaft** aktuell, ohne einen manuellen Handgriff.

---

## Verwandt

- `docs/ANLEITUNG-SOCIAL-AUTOPILOT.md` – die Redaktions-Maschine dahinter
- `docs/RUNBUCH-SOCIAL-SECRETS.md` – wie ein Kanal aus Standby (⚪) aktiv (🟢) wird
- `docs/ANLEITUNG-SHORTS-SCHMIEDE.md` – Reels & Shorts
