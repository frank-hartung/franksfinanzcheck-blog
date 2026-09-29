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

Die `.ics`-Dateien lassen sich direkt in jede Kalender-App laden. Zwei Wege:

**A) Einmal-Import (Schnappschuss):** `<kanal>.ics` herunterladen und in deiner
Kalender-App öffnen.

**B) Dauer-Abo (empfohlen):** Wenn die Kalender öffentlich erreichbar sind
(z. B. über die Roh-URL im GitHub-Repo oder gespiegelt unter
`franksfinanzcheck.de`), abonnierst du die URL – dann aktualisiert sich der
Kalender von selbst:

- **Google Kalender:** Andere Kalender → *Per URL* → `.ics`-Adresse einfügen.
- **Apple Kalender (iPhone/Mac):** Kalender → *Kalenderabo hinzufügen*.
- **Outlook:** Kalender hinzufügen → *Aus dem Internet abonnieren*.

> Tipp: Für ein echtes Live-Abo muss die `.ics`-Datei unter einer stabilen
> HTTPS-URL liegen. Der GitHub-Raw-Link des jeweiligen Branch funktioniert
> sofort; für eine hübsche Adresse kann der Feed später unter
> `franksfinanzcheck.de/kalender/<kanal>.ics` gespiegelt werden.

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
