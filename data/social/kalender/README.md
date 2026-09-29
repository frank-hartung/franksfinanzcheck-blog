# Social-Media-Veröffentlichungskalender

Dieser Ordner enthält für **jeden Social-Media-Kanal** einen eigenen, automatisch aktualisierten Veröffentlichungskalender.

- **`UEBERSICHT.md`** – alle Kanäle auf einen Blick + gemeinsame 14-Tage-Timeline.
- **`<kanal>.md`** – lesbarer Kalender eines Kanals (kommende & vergangene Beiträge, inkl. der verbindlichen Kanal-Kriterien).
- **`<kanal>.ics`** – denselben Kalender **abonnieren**: Link/Datei in Google Kalender, Apple Kalender oder Outlook hinzufügen, dann erscheinen alle geplanten Posts automatisch in deinem Kalender.
- **`video.md` / `video.ics`** – Produktionsrhythmus für Reels & Shorts.

## Woher die Termine kommen

Die Kalender werden **nicht von Hand gepflegt**. Sie werden aus dem versionierten Redaktionsplan `data/social/schedule.yaml` erzeugt, den der Social-Autopilot (`scripts/social_studio.py`) alle 2 Stunden fortschreibt. Nach jedem Lauf werden diese Kalender neu geschrieben – du musst dich um nichts kümmern.

## Selbst neu erzeugen

```bash
python3 scripts/social_calendar.py --build
```
