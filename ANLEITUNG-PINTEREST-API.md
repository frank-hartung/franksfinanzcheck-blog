# 🔑 Anleitung: Pinterest-API einrichten (einmalig, ~10 Minuten)

Damit der Blog **montags automatisch** neue Artikel bei Pinterest nachpinnen kann,
brauchst du einen Pinterest-API-Zugang. Das ist **kostenlos** – die Schritte sind:

---

## Schritt 1: Developer-App erstellen (10 Minuten)

### 1a. Voraussetzungen (einmalig)
- **Pinterest Business-Konto** (hast du bereits – für die Website-Verifizierung) ✅
- **E-Mail-Adresse bestätigt** (in deinem Pinterest-Konto)
- **Developer Terms akzeptieren:** Beim ersten Besuch von https://developers.pinterest.com/ wirst du aufgefordert, die Nutzungsbedingungen zu bestätigen

### 1b. „Connect app"-Formular ausfüllen

Gehe auf **https://developers.pinterest.com/** → **„My apps"** → **„Connect app"** (bzw. „Create app") und fülle DIESE Felder aus:

| Feld | Was du einträgst |
|---|---|
| **App name** | `FranksFinanzcheck Blog` |
| **Company name** | `FranksFinanzcheck` (oder dein Name `Frank Hartung` – als Privatperson beides ok) |
| **Website** | `https://frank-hartung.github.io/franksfinanzcheck-blog` |
| **App purpose** (Freitext) | `The purpose of this app is to allow us to add images and videos, called "pins", to Pinterest accounts, get data about connected accounts, and post analytics.` |
| **Developer purpose** (Auswahl) | `I am developing an app for my organization/personal use` |
| **Use cases** (Mehrfachauswahl) | ☑️ **Pin creation & scheduling** · ☑️ **Reporting** |
| **Audience** (Mehrfachauswahl) | ☑️ **Pinners** · ☑️ **Creators** |

Dann **„Submit"** klicken.

### 1c. Wichtig: Freigabe abwarten! ⏳
Pinterest prüft jede App **manuell** – die Freigabe („Trial access") kann **mehrere Tage dauern** [1](https://docs.mixpost.app/services/social/pinterest/). Du bekommst eine **E-Mail**, sobald deine App freigeschaltet ist. Erst danach kannst du den Token erzeugen (Schritt 2).

> Tipp: Du kannst den GitHub-Teil (Push des Workflows) schon jetzt machen – nur das Pinnen startet, sobald die App freigegeben ist.

## Schritt 2: OAuth-Token erzeugen (3 Minuten)

1. Gehe auf **https://developers.pinterest.com/tools/access-token/**
2. Wähle deine App aus dem Dropdown
3. Hake **alle Scopes** an, insbesondere:
   - ☑️ **`boards:read`**
   - ☑️ **`pins:read`**
   - ☑️ **`pins:write`** (das Wichtigste – erlaubt das Erstellen von Pins)
4. Klicke **„Generate token"** / **„Authorize"**
5. Pinterest fragt: **„Erlaube der App, auf dein Konto zuzugreifen?"** → **„Erlauben"**
6. **Kopiere den Token** – er beginnt mit `pina_...`

> ⚠️ Der Token ist ein **Geheimnis** – er erlaubt das Pinnen in deinem Namen.
> Schicke ihn mir hier im Chat NUR zum Einrichten (danach löschen/neu erzeugen).

## Schritt 3: Board-ID ermitteln (1 Minute)

Sobald du den Token hast, sag mir Bescheid – ich führe dann aus:

```bash
PINTEREST_ACCESS_TOKEN=pina_DEIN_TOKEN python3 scripts/generate_pins.py --list-boards
```

Das zeigt alle deine Boards mit ihren IDs, z. B.:
```
1234567890123456789  ←  Geld sparen & Frugalismus
9876543210987654321  ←  Haushaltskasse & Budgetplanung
```

## Schritt 4: Im GitHub-Repo hinterlegen (2 Minuten)

**Token als Secret:**
1. GitHub → Repo → **Settings → Secrets and variables → Actions**
2. **New repository secret** → Name: `PINTEREST_ACCESS_TOKEN` → Wert: dein Token

**Board-ID als Variable:**
1. Tab **„Variables"** → **New repository variable**
2. Name: `PINTEREST_BOARD_ID` → Wert: die Board-ID (z. B. für „Geld sparen & Frugalismus")

---

## Danach läuft alles automatisch

| Wann | Was passiert |
|---|---|
| **Montag 17:30 Uhr (DE)** | Der Workflow „Wöchentliches Nach-Pinnen" findet alle Artikel mit `pinned: false` und erstellt für jeden einen Pin (Cover-Bild + Beschreibung + Artikel-URL) |
| Danach | Die Artikel werden als „gepinnt" markiert (`pinned: true`) – jeder Artikel wird nur **einmal** gepinnt |

**Manuell testen:** GitHub → Actions → „Wöchentliches Nach-Pinnen" → Run workflow
**Stoppen:** Workflow deaktivieren (Kill-Switch)

---

## Häufige Fragen

**Kostet die API etwas?**
Nein. Die Pinterest API v5 ist kostenlos. Für dein Pensum (2–15 Pins/Woche) sind die Limits völlig ausreichend.

**Welches Board wird benutzt?**
Das Board, dessen ID du als `PINTEREST_BOARD_ID` hinterlegst. Du kannst später auch mehrere Boards nacheinander nutzen (Variable ändern) – oder das Skript erweitern, damit es pro Thema das passende Board wählt.

**Was, wenn ein Pin fehlschlägt?**
Das Skript meldet den Fehler im Workflow-Log und macht mit dem nächsten Artikel weiter. Der Artikel bleibt `pinned: false` und wird beim nächsten Lauf erneut versucht.

**Kann ich den Token später widerrufen?**
Ja – unter developers.pinterest.com → My apps → deine App → Token widerrufen/löschen. Dann pausiert das Nachpinnen (Workflow meldet den Fehler).

**Warum montags 17:30 Uhr?**
Die Wochenend-Artikel (4 Stück) sind fertig, und die Pins gehen 1–2 Stunden vor dem abendlichen Pinterest-Nutzungs-Peak (19–22 Uhr) in die Verteilung – so bekommen sie maximales Potenzial. Außerdem kollidiert es nicht mit deinen Pin-Zeiten (08:00 / 19:30).
