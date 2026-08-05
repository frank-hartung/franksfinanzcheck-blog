# 🔑 Anleitung: Pinterest-API einrichten (einmalig, ~10 Minuten)

Damit der Blog **montags automatisch** neue Artikel bei Pinterest nachpinnen kann,
brauchst du einen Pinterest-API-Zugang. Das ist **kostenlos** – die Schritte sind:

---

## Schritt 1: Developer-App erstellen (5 Minuten)

1. Gehe auf **https://developers.pinterest.com/** und melde dich mit deinem Pinterest-Konto an
2. Klicke auf **„My apps"** (oben rechts) → **„Create app"**
3. Fülle das Formular aus:
   - **App name:** `FranksFinanzcheck Blog`
   - **App description:** `Automatisches Nachpinnen der Blog-Artikel`
   - **Website:** `https://frank-hartung.github.io/franksfinanzcheck-blog`
4. **Bestätigen** → deine App ist erstellt (App-ID wird angezeigt)

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
