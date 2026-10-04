# Mastodon-Sendeausfall #549 – Dauerreparatur auf Agentur-Niveau

**Datum:** 04.10.2026

**Incident:** GitHub Issue #549 – „Kanal Mastodon sendet seit 48 h nicht“

**Betroffen:** Social-Autopilot, Schaltwerk, Mastodon

## Kurzbefund

Der Mastodon-Token war nicht die Ursache. Der letzte Social-Autopilot-Lauf war
grün und die Live-Prüfung des Mastodon-Secrets erfolgreich. Trotzdem hatte der
Kanal **0 geplante Beiträge**.

Der Ausfall entstand aus zwei unabhängigen Konstruktionsfehlern:

1. Der Autopilot entschied über Neuplanung anhand einer **globalen** Menge. Im
   Plan standen 83 Beiträge anderer, überwiegend nicht eingerichteter Kanäle;
   Mastodon selbst hatte keinen einzigen offenen Slot. `83 >= 12` verhinderte
   deshalb jede Neuplanung. Neue, bereits veröffentlichte Artikel vom 27.09. bis
   02.10. kamen für Mastodon nie in den seit 26.09. erzeugten Plan.
2. Das Schaltwerk sollte den Plan nachts erneuern, konnte seinen State und Plan
   aber nicht dauerhaft sichern. Ein einziges fehlendes optionales Log ließ
   `git add` die komplette Pfadliste ablehnen. `|| true` maskierte anschließend
   Commit- und Push-Fehler; der Workflow erschien grün. Für
   `data/schaltwerk_state.json` existierte dadurch kein einziger Commit.

## Dauerreparatur

### 1. Kanalgerechter Rolling-Plan

`scripts/social_studio.py` rollt den 14-Tage-Plan jetzt **bei jedem Lauf**.
`build_plan()` bewahrt bestehende Slots, ergänzt aber neue Artikel und fehlende
Kanäle deterministisch. Die globale Tageskapazität wird zuerst an Kanäle mit
gültigen Zugangsdaten vergeben; Standby-Kanäle werden danach einsortiert. Ein
nicht zustellbarer Rückstau kann Mastodon damit nicht mehr aushungern.

### 2. Nachholfrist ohne Slot-Verlust

`scripts/social_planner.py` verwendet für Neuplanung und Versand dieselbe
48-Stunden-Frist. Ein durch GitHub Actions verspäteter, aber noch zustellbarer
Slot wird beim Rollen nicht mehr nach 60 Minuten gelöscht, bevor er versendet
werden kann. Ältere Slots verfallen weiterhin kontrolliert.

### 3. Wirklich persistentes Schaltwerk

`.github/workflows/schaltwerk.yml`:

- stagiert nur vorhandene oder bereits getrackte Pfade;
- sichert State, Log und Social-Plan auch dann, wenn optionale Dateien fehlen;
- behandelt Commit/Push als Teil des Erfolgsvertrags;
- maskiert Persistenzfehler nicht mehr mit `|| true`.

### 4. Self-Healing vor Eskalation

Die Regel `stiller-kanal` rollt vor dem Incident-Issue automatisch den Plan,
zieht genau einen Zukunftsslot des betroffenen Kanals auf „jetzt“ vor und
versucht die sofortige Zustellung. Tageslimit, globales Limit und
Mindestabstand bleiben hart. Ein API-Fehler unterdrückt die anschließende
Eskalation nicht; das Issue bleibt als sichtbarer Nachweis bestehen.

### 5. Robuste Zeitsteuerung

Kritische Tagesregeln können mit `nachholen: true` beim ersten Lauf nach dem
Slot nachgeholt werden. Die Nachtplanung nutzt diesen Vertrag. Zusätzlich trägt
`schaltwerk.berlin_now()` jetzt einen echten MEZ/MESZ-Offset statt einer
verschobenen Uhr mit fälschlichem `+00:00`.

## Regressionsschutz

Die Tests beweisen insbesondere:

- ein globaler Fremdkanal-Rückstau verhindert das Rollen nicht mehr;
- ein zwei Stunden verspäteter Slot überlebt die Neuplanung;
- kritische Zeitpläne werden nach GitHub-Verzug genau einmal nachgeholt;
- die 48-h-Wache versucht zuerst genau eine kontrollierte Sofortzustellung und
  eskaliert auch bei einem API-Fehler danach;
- der Workflow nutzt keine blind gestagte Pfadliste und maskiert den Push nicht;
- Schaltwerk liest die echten, verschachtelten Versandzähler des Autopiloten.

**Prüfnachweis:** 81 fokussierte Social-/Schaltwerk-Tests grün; vollständige
Repository-Suite 1.648 Tests grün (9 übersprungen); Social-Studio-,
Schaltwerk- und Kalender-Selbsttests grün; scharfer Offline-Recovery-Dry-Run
liefert genau einen Mastodon-Beitrag. Der globale Selbsttest-Runner meldet
unabhängig von dieser Änderung einen bestehenden C15-Seiteneffekt in
`scripts/awin_fetch.py --selftest` (erzeugt ein Audit-Log); die erzeugte
Prüfdatei wurde nicht übernommen.

## Betriebsergebnis

Nach dem Rollout wird ein gezielter Workflow-Lauf auf Mastodon ausgeführt. Der
Live-Nachweis (Status-URL, Workflow-Run und aktualisierter State) wird im Pull
Request und in Issue #549 dokumentiert.
