# 🔑 Anleitung: Pinterest-API einrichten (einmalig, ~10 Minuten)

Damit der Blog **montags automatisch** neue Artikel bei Pinterest nachpinnen kann,
brauchst du einen Pinterest-API-Zugang. Das ist **kostenlos** – die Schritte sind:

> ⚠️ **WICHTIG (Stand 2026): Token-Lebensdauer!** Pinterest-Access-Tokens laufen nach
> **30 Tagen** ab. Dieses System erneuert sie deshalb **automatisch bei jedem Lauf**
> (Continuous Refresh, `scripts/pinterest_auth.py`). Die Tokens liegen AES-256-
> verschlüsselt in `data/pinterest_tokens.enc`; der Schlüssel ist das Secret
> `PINTEREST_TOKEN_KEY`. Einmalig bei der Ersteinrichtung erzeugen (Schritt 2a).

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

**Scopes (Premium 25.08.2026):** Unter „Requested scopes" mindestens ankreuzen:
`boards:read`, `boards:write`, `pins:read`, `pins:write` – plus `profile:read`,
damit der **Profil-Audit** (Name/Bio/Website des Live-Profils) laufen kann.

### 1c. Wichtig: Freigabe abwarten! ⏳
Pinterest prüft jede App **manuell** – die Freigabe („Trial access") kann **mehrere Tage dauern** [1](https://docs.mixpost.app/services/social/pinterest/). Du bekommst eine **E-Mail**, sobald deine App freigeschaltet ist. Erst danach kannst du den Token erzeugen (Schritt 2).

> Tipp: Du kannst den GitHub-Teil (Push des Workflows) schon jetzt machen – nur das Pinnen startet, sobald die App freigegeben ist.

## Schritt 2: OAuth-Token erzeugen (3 Minuten) – mit Auto-Refresh

### 2a. Verschlüsselungs-Schlüssel vorbereiten (1 Minute, einmalig)
1. Erzeuge eine zufällige Zeichenkette (mind. 32 Zeichen, z. B. mit einem Passwort-Generator)
2. GitHub → Repo → **Settings → Secrets and variables → Actions → New repository secret**
3. Name: **`PINTEREST_TOKEN_KEY`** → Wert: deine Zufallszeichenkette
   (Dieser Schlüssel entsperrt die Token-Datei. Ohne ihn ist die Datei wertlos.)

### 2b. Redirect-URI in der App hinterlegen
Pinterest-Dashboard → **My apps → deine App →** Redirect URI:
**`https://franksfinanzcheck.de/pinterest-oauth`** eintragen und speichern.
(Die Seite muss nicht existieren – der Browser landet nach dem Erlauben auf
einer 404-Seite, der Code steht trotzdem in der Adresszeile.)

### 2c. Autorisierung durchführen (mit Assistenz oder lokal)
```bash
# 1. URL erzeugen und im Browser öffnen (mit Pinterest eingeloggt):
PINTEREST_APP_ID=<deine-app-id> python3 scripts/pinterest_auth.py --auth-url

# 2. Nach „Erlauben" den ?code=... aus der Adresszeile kopieren und austauschen:
PINTEREST_APP_ID=<id> PINTEREST_APP_SECRET=<secret> \
PINTEREST_TOKEN_KEY=<schluessel> \
python3 scripts/pinterest_auth.py --exchange <CODE>

# 3. Verschlüsselte Tokens ins Repo (sicher, auch bei öffentlichem Repo):
git add data/pinterest_tokens.enc && git commit -m "chore: Pinterest-Tokens (verschlüsselt)" && git push

# 4. Jederzeit prüfbar:
PINTEREST_TOKEN_KEY=<schluessel> python3 scripts/pinterest_auth.py --status
```

> ℹ️ **Ab jetzt vollautomatisch:** Jeder Bot-Lauf ruft den Refresh-Endpunkt auf,
> bekommt frische Tokens (Access 30 Tage, Refresh-Token wird neu ausgestellt) und
> committet die erneuerte `data/pinterest_tokens.enc`. Solange der Workflow nicht
> länger als 60 Tage pausiert, ist nie wieder Handarbeit nötig.
> Das klassische Secret `PINTEREST_ACCESS_TOKEN` bleibt als Fallback weiter nutzbar.

## Schritt 3: Boards – werden automatisch gemanagt (Premium 25.08.2026)

Die Engine nutzt **kein einzelnes Board** mehr, sondern das 6-Board-System aus
`data/pinterest_boards.yaml` (Premium-Board-Architektur, s.
PINTEREST-PREMIUM-STRATEGIE.md § 3). Jeder Pin wird auf das Board seiner
Pinwand/Pillar geroutet:

| Pillar des Artikels | Board |
|---|---|
| `frugalismus` | Geld sparen im Alltag \| Frugalismus-Tipps |
| `konto-karten` | Budget & Haushaltskasse: clever planen |
| `strom-sparen` | Strom & Gas sparen \| Tarife clever wechseln |
| `internet-dsl` | Internet & DSL \| WLAN-Tipps & Tarife |
| `mietwagen` | Günstig reisen \| Reisebudget & Mietwagen |
| `versicherungen` | Versicherungen clever wechseln & sparen |

Board-IDs werden live per API aufgelöst und gecacht
(`data/pinterest_boards_cache.json`, TTL 14 Tage); **fehlende Boards werden
automatisch angelegt** (Scope `boards:write`, Beschreibung aus der
Konfiguration). `PINTEREST_BOARD_ID` ist nur noch optionales Fallback-Board.
Zum Prüfen:

```bash
PINTEREST_ACCESS_TOKEN=pina_DEIN_TOKEN python3 scripts/pinterest_engine.py --list-boards
# zeigt alle Live-Boards; SOLL-Boards aus der Konfiguration sind mit [SOLL] markiert
```

> Automatische Board-Anlage deaktivieren: Variable `PINTEREST_CREATE_BOARDS=0`.

## Schritt 4: Im GitHub-Repo hinterlegen (2 Minuten)

**Token als Secret (empfohlen: OAuth mit Auto-Refresh, s. Schritt 2):**
1. GitHub → Repo → **Settings → Secrets and variables → Actions**
2. **New repository secret** → `PINTEREST_TOKEN_KEY` (Schlüssel aus Schritt 2a)
3. `data/pinterest_tokens.enc` committen (AES-256-verschlüsselt – sicher, auch im öffentlichen Repo)

**Alternativ (Klassik):** Secret `PINTEREST_ACCESS_TOKEN` = dein `pina_...`-Token
(läuft nach 30 Tagen ab, kein Auto-Refresh).

**Optionale Variablen:** `PINTEREST_BOARD_ID` (Fallback-Board),
`PINTEREST_CREATE_BOARDS` (Default `1`), `PINTEREST_ROTATE_DAYS` (Default `60`).

---

## Danach läuft alles automatisch

| Wann | Was passiert |
|---|---|
| **Jeder Pin-Lauf** (Workflow „Pinterest-AI", manuell startbar) | 1) Link-Healer + Pin-Text-Sync (Premium-Guards) · 2) alle `pinned: false`-Artikel werden als Pins auf das richtige Board gepinnt · 3) **Profil-Audit**: Live-Profil vs. Premium-Soll → `PINTEREST-PROFILE-REPORT.md` |
| **Täglich 06:30 MESZ** (Workflow „Pinterest-Watchdog") | Alle Pinterest-Signale gecheckt (robots, Domain-Verify, Pin-Button, Rich-Pin-Meta, …) + **LIVE-Link-Guard**: jede Pin-Zielseite muss 200 liefern, auf der eigenen Domain bleiben und Rich-Pin-Meta tragen → `PINTEREST-LINK-GUARD-REPORT.md` |
| Danach | Ge-pinnte Artikel werden `pinned: true` markiert – jeder Artikel wird nur **einmal** gepinnt; Refresh-Kandidaten (> 60 Tage) werden in der Queue geführt |

**Manuell testen:** GitHub → Actions → „Pinterest-AI" → Run workflow
**Stoppen:** Workflow deaktivieren (Kill-Switch)

---

## Häufige Fragen

**Kostet die API etwas?**
Nein. Die Pinterest API v5 ist kostenlos. Für dein Pensum (2–15 Pins/Woche) sind die Limits völlig ausreichend.

**Welches Board wird benutzt?**
Automatisch das Board zur Pinwand/Pillar des Artikels (6-Board-System aus
`data/pinterest_boards.yaml`, s. Schritt 3). Board-Namen/Beschreibungen dort
ändern → gilt ab dem nächsten Lauf. `PINTEREST_BOARD_ID` ist nur Fallback.

**Was, wenn ein Pin fehlschlägt?**
Das Skript meldet den Fehler im Workflow-Log und macht mit dem nächsten Artikel weiter. Der Artikel bleibt `pinned: false` und wird beim nächsten Lauf erneut versucht.

**Kann ich den Token später widerrufen?**
Ja – unter developers.pinterest.com → My apps → deine App → Token widerrufen/löschen. Dann pausiert das Nachpinnen (Workflow meldet den Fehler).

**Warum montags 17:30 Uhr?**
Die Wochenend-Artikel (4 Stück) sind fertig, und die Pins gehen 1–2 Stunden vor dem abendlichen Pinterest-Nutzungs-Peak (19–22 Uhr) in die Verteilung – so bekommen sie maximales Potenzial. Außerdem kollidiert es nicht mit deinen Pin-Zeiten (08:00 / 19:30).
