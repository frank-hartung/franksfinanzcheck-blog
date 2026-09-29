# 🔑 Runbuch: Social-Kanäle scharf schalten

**Zweck:** Jeden der zehn Kanäle des Social-Autopiloten in Betrieb nehmen –
mit Klickpfad, exaktem Secret-Namen und einem **Verifikations-Lauf, der nichts
veröffentlicht**. Gesamtaufwand für alle Kanäle: **rund 90 Minuten, einmalig, 0 €.**

> **Ausgangslage (29.09.2026):** Adapter, Planer, Gate und Zeitsteuerung sind fertig
> und laufen. Es fehlen ausschließlich die Zugangsdaten – deshalb sendet aktuell nur
> Mastodon. Es ist **keine Code-Änderung nötig**: Sobald ein Secret hinterlegt ist,
> erkennt der Autopilot den Kanal beim nächsten Lauf von selbst.

---

## 0. Die drei Regeln

1. **Secrets** (geheim) unter *Settings → Secrets and variables → **Actions** → Secrets*.
   **Variables** (nicht geheim: IDs, Instanz-URLs) im Reiter daneben unter *Variables*.
   Das ist kein Detail – eine ID als Secret zu hinterlegen funktioniert zwar, macht sie
   aber in Logs unlesbar („***"), was jede Fehlersuche blockiert.
2. **Namen exakt übernehmen.** Sie stehen in `data/social/channels.yaml` und sind
   Vertrag zwischen Workflow und Adapter. Ein Tippfehler = stiller Standby.
3. **Nach jedem Kanal verifizieren** (Abschnitt 1). Nie „hinterlegen und hoffen".

---

## 1. Der Verifikations-Lauf

**Auf GitHub (Normalfall):**
*Actions → „Social-Preflight (Zugangs-Verifikation)" → Run workflow*
→ optional einen Kanal eintragen (z. B. `bluesky`) → **Run**.
Das Ergebnis steht unten im Lauf als Tabelle („Job summary").

**Lokal (wenn du die Zugangsdaten gerade in der Hand hast):**

```bash
BLUESKY_IDENTIFIER=franksfinanzcheck.de \
BLUESKY_APP_PASSWORD=xxxx-xxxx-xxxx-xxxx \
python3 scripts/social_preflight.py --kanal bluesky
```

**Lesart der Ampel:**

| | Bedeutung | Was du tust |
|---|---|---|
| ✅ `ok` | Zugang verifiziert, Konto wird angezeigt | nichts – der Kanal ist scharf |
| ⚪ `standby` | Secret fehlt | eintragen (dieses Runbuch) |
| ❌ `befund` | Zugangsdaten da, API weist sie ab | Hinweis im Bericht befolgen |
| ❓ `offen` | Netz-/Anbieterstörung | später wiederholen, **Token nicht wegwerfen** |

Der Lauf ist **rein lesend**: er ruft je Kanal nur „Wer bin ich?" auf
(`verify_credentials`, `users/me`, `getMe` …). Er postet nichts, ändert nichts
und committet nichts.

**Erst wenn ✅ steht, ist der Kanal produktiv.** Dann greifen automatisch die in
`channels.yaml` hinterlegte Kadenz, das Zeichenlimit, die Hashtag-Regel und das Gate.

---

## 2. Die Kanäle – in dieser Reihenfolge

Sortiert nach Aufwand pro Nutzen. Du kannst nach jedem Schritt aufhören; jeder
Kanal steht für sich.

---

### ① Bluesky — 5 Minuten, keine Freigabe nötig ⭐ hier anfangen

**Warum zuerst:** kein Review-Prozess, kein Ablaufdatum, sofort produktiv.

1. bsky.app → *Einstellungen → Datenschutz und Sicherheit → **App-Passwörter*** → *App-Passwort hinzufügen*.
2. Namen vergeben (z. B. `Autopilot`), Passwort **sofort kopieren** (wird nur einmal gezeigt).

| Art | Name | Wert |
|---|---|---|
| Secret | `BLUESKY_IDENTIFIER` | dein voller Handle, z. B. `franksfinanzcheck.de` |
| Secret | `BLUESKY_APP_PASSWORD` | das App-Passwort, Format `xxxx-xxxx-xxxx-xxxx` |
| Variable | `BLUESKY_PDS` | *leer lassen* (Standard `https://bsky.social`) |

> ⚠️ **Nie das Kontopasswort** eintragen. Ein App-Passwort lässt sich einzeln
> widerrufen, ohne dass du dich überall neu anmeldest.

**Verifizieren:** `--kanal bluesky` → erwartet ✅ mit `als @deinhandle`.

---

### ② Telegram — 10 Minuten, keine Freigabe nötig

**Warum:** dein eigener Verteiler. Keine Plattform kann ihn drosseln, keine
Reichweite hängt von einem Algorithmus ab.

1. In Telegram **Kanal anlegen** (öffentlich, z. B. `@franksfinanzcheck`).
2. **@BotFather** anschreiben → `/newbot` → Name + Benutzername → Token kopieren
   (Format `123456789:AAH…`).
3. Kanal → *Verwalten → Administratoren → Administrator hinzufügen* → deinen Bot
   suchen → Recht **„Nachrichten posten"** aktivieren.

| Art | Name | Wert |
|---|---|---|
| Secret | `TELEGRAM_BOT_TOKEN` | der BotFather-Token |
| Variable | `TELEGRAM_CHAT_ID` | `@franksfinanzcheck` (öffentlich) oder `-100…` (privat) |

> **Private Kanäle:** numerische ID ermitteln – im Kanal irgendetwas posten, dann
> `https://api.telegram.org/bot<TOKEN>/getUpdates` im Browser öffnen und `chat.id` ablesen.

**Verifizieren:** `--kanal telegram` → prüft Bot **und** ob er den Kanal erreicht.
Der typische Fehler („Kanal nicht erreichbar") heißt immer: Bot ist noch kein Admin.

---

### ③ Mastodon — bereits aktiv ✅

Läuft seit August (37 Posts in `data/social/state.yaml`). Nur zur Vollständigkeit:

| Art | Name | Wert |
|---|---|---|
| Secret | `MASTODON_ACCESS_TOKEN` | Einstellungen → Entwicklung → Neue Anwendung |
| Variable | `MASTODON_INSTANCE` | `https://mastodon.social` (falls abweichend) |

Scopes: `write:statuses`, `write:media`. Der Token **läuft nicht ab**.

---

### ④ LinkedIn — 20 Minuten ⭐ beste Zielgruppe für Finanzthemen

1. developer.linkedin.com → *Create app* (braucht eine LinkedIn-**Unternehmensseite**
   als Träger – reine Formalie, du postest trotzdem als Person).
2. Reiter **Products** → anfordern: **„Share on LinkedIn"** und
   **„Sign In with LinkedIn using OpenID Connect"** (Freigabe meist binnen Minuten).
3. Reiter **Auth** → *OAuth 2.0 tools → Create token* → Scopes `openid`, `profile`,
   `w_member_social` → Token kopieren.

| Art | Name | Wert |
|---|---|---|
| Secret | `LINKEDIN_ACCESS_TOKEN` | der erzeugte Token |
| Variable | `LINKEDIN_PERSON_URN` | `urn:li:person:XXXXXXXX` |
| Variable | `LINKEDIN_ORG_URN` | nur wenn als **Seite** gepostet werden soll |

> **Personen-URN herausfinden:** Trag erst nur den Token ein und starte den Preflight.
> Der Bericht meldet dann `Token gültig, aber kein Absender gesetzt` **und nennt dir
> den fertigen URN** aus der API-Antwort. Den kopierst du in die Variable.

> ⏰ **Ablaufdatum:** ~60 Tage. Der Montags-Preflight meldet es rechtzeitig als ❌.
> Trag dir zusätzlich eine Quartals-Erinnerung ein.

**Besonderheit:** Der Autopilot setzt den Link in den **ersten Kommentar**
(`link_position: first_comment`) – das ist bei LinkedIn der Reichweiten-Standard.

---

### ⑤+⑥+⑦ Facebook, Instagram, Threads — 30 Minuten, **eine** Meta-App für alle drei

**Voraussetzungen:** eine Facebook-**Seite**; für Instagram ein **Business-** oder
**Creator-Konto**, das mit dieser Seite verknüpft ist.

1. developers.facebook.com → *Meine Apps → App erstellen* → Typ **„Business"**.
2. Produkte hinzufügen: **Facebook Login**, **Instagram Graph API**, **Threads API**.
3. **Graph-API-Explorer** öffnen, deine App wählen, Berechtigungen anhaken:
   `pages_show_list`, `pages_read_engagement`, `pages_manage_posts`,
   `instagram_basic`, `instagram_content_publish`,
   `threads_basic`, `threads_content_publish`.
4. *Generate Access Token* → einloggen → Seite auswählen.
5. **Token haltbar machen** (sonst 1–2 Stunden gültig):
   *Access Token Tool → Debug → „Extend Access Token"* (→ ~60 Tage), dann
   `GET /me/accounts` im Explorer aufrufen. Der dort zurückgegebene **Seiten-Token
   läuft nicht ab** – diesen nimmst du.

**IDs ermitteln** (alles im Graph-API-Explorer):

```
GET /me/accounts                                  → Seiten-ID  (FACEBOOK_PAGE_ID)
GET /<page-id>?fields=instagram_business_account  → IG-Konto-ID (INSTAGRAM_ACCOUNT_ID)
GET /me?fields=id  (auf graph.threads.net)        → Threads-ID  (THREADS_USER_ID)
```

| Art | Name | Wert |
|---|---|---|
| Secret | `FACEBOOK_PAGE_TOKEN` | nicht ablaufender **Seiten**-Token |
| Variable | `FACEBOOK_PAGE_ID` | numerische Seiten-ID |
| Secret | `INSTAGRAM_ACCESS_TOKEN` | derselbe Seiten-Token funktioniert |
| Variable | `INSTAGRAM_ACCOUNT_ID` | IG-Business-Konto-ID |
| Secret | `THREADS_ACCESS_TOKEN` | eigener Threads-Long-Lived-Token |
| Variable | `THREADS_USER_ID` | Threads-Nutzer-ID |

> **Instagram braucht zwingend ein Bild** (`media.required: true`, Format 4:5).
> Das liefert `social_images.py` automatisch aus dem Artikel-Cover. Captions haben
> bei Instagram keine klickbaren Links – der Autopilot setzt deshalb „Link in der Bio".

**Verifizieren:** je Kanal einzeln (`--kanal facebook`, `--kanal instagram`,
`--kanal threads`). Meldet der Preflight bei Threads eine abweichende ID, nennt er
dir die richtige zum Eintragen.

---

### ⑧ X (Twitter) — 15 Minuten

1. developer.x.com → *Sign up* (Free-Tier genügt: ~500 Posts/Monat, unsere
   Obergrenze liegt bei 2/Tag) → Projekt + App anlegen.
2. **Zwingend zuerst:** *App settings → User authentication settings → Set up* →
   **App permissions: „Read and write"** → Type: *Web App/Automated App* →
   Callback/Website eintragen (`https://franksfinanzcheck.de/` genügt) → speichern.
3. *Keys and tokens* → **Consumer Keys** kopieren → **Access Token and Secret**
   **neu erzeugen** (nach dem Umstellen auf „Read and write"!).

| Art | Name | Wert |
|---|---|---|
| Secret | `X_API_KEY` | API Key (Consumer Key) |
| Secret | `X_API_SECRET` | API Key Secret |
| Secret | `X_ACCESS_TOKEN` | Access Token |
| Secret | `X_ACCESS_SECRET` | Access Token Secret |

> ⚠️ **Der Klassiker:** Access-Token, die *vor* dem Umschalten auf „Read and write"
> erzeugt wurden, behalten für immer Nur-Lese-Rechte. Der Preflight liefert dann
> ein ✅ auf `users/me`, aber das Posten scheitert später mit 403.
> **Deshalb: Berechtigung zuerst, Token danach.**

---

### ⑨ Pinterest — Sonderweg über den Token-Broker

Pinterest läuft schon (RSS-Auto-publish + `pinterest_engine.py`). Der Autopilot
übernimmt hier nur **Refresh-Pins** für Artikel ab 45 Tagen Alter.

| Art | Name | Wert |
|---|---|---|
| Secret | `PINTEREST_TOKEN_KEY` / `PINTEREST_APP_ID` / `PINTEREST_APP_SECRET` | siehe `docs/ANLEITUNG-PINTEREST-API.md` |
| Variable | `PINTEREST_BOARD_ID` | optional – sonst wird das Board je Themenwelt aufgelöst |

Der Token erneuert sich selbst (`scripts/pinterest_token.py`). Der Preflight prüft
Konto **und** Board.

---

### ⑩ Reddit — **bewusst zuletzt, Empfehlung: vorerst aus**

Technisch fertig konfiguriert (`launch_delay_hours: 72`, max. 1 Beitrag/Tag, Ziel ist
standardmäßig das eigene Profil `u/<name>`). Trotzdem:

> **Agentur-Rat:** Reddit bestraft automatisierte Selbstpromotion härter als jede
> andere Plattform – bis zum Shadowban der Domain. Setz in `data/social/channels.yaml`
> `enabled: false`, bis du zwei, drei Subreddits **manuell** erschlossen hast und ihre
> Regeln kennst.

| Art | Name | Wert |
|---|---|---|
| Secret | `REDDIT_CLIENT_ID` / `REDDIT_CLIENT_SECRET` | reddit.com/prefs/apps → Typ **script** |
| Secret | `REDDIT_USERNAME` / `REDDIT_PASSWORD` | Konto-Login |
| Variable | `REDDIT_SUBREDDIT` | leer = eigenes Profil (sicher) |

> Bei aktivierter **Zwei-Faktor-Anmeldung funktioniert der Passwort-Fluss nicht**.

---

## 3. Abnahme nach dem Einrichten

```bash
# 1) Alle Zugänge prüfen (postet nichts)
#    → auf GitHub: Actions → „Social-Preflight" → Run workflow
python3 scripts/social_preflight.py

# 2) Trockenlauf: zeigt die fertigen Texte je Kanal, sendet nichts
python3 scripts/social_studio.py --run --dry-run

# 3) Erster echter Beitrag, streng begrenzt auf EINEN
python3 scripts/social_studio.py --run --channel bluesky --limit 1
```

Danach übernimmt der Zeitplan (`social-autopilot.yml`, alle 2 Stunden).
Deine Kontrollpunkte: `SOCIAL-AUTOPILOT-STATUS.md` nach dem Lauf und der
Montags-Preflight in der Job-Zusammenfassung.

---

## 4. Wenn etwas klemmt

| Befund | Ursache | Handgriff |
|---|---|---|
| Kanal bleibt ⚪ trotz Eintrag | Secret unter *Dependabot* oder *Codespaces* statt *Actions* abgelegt; oder Tippfehler | Reiter **Actions** prüfen, Namen gegen `channels.yaml` abgleichen |
| ❌ `HTTP 401` | Token abgelaufen oder widerrufen | neu erzeugen, Secret überschreiben |
| ❌ `HTTP 403` | Scopes fehlen (X: „Read only") | Berechtigung ändern, **dann Token neu erzeugen** |
| ❌ `HTTP 404` | falsche Seiten-/Konto-/Board-/Chat-ID | ID neu ermitteln (Abschnitt ⑤–⑦) |
| ❓ `offen` | Netz- oder Anbieterstörung | später wiederholen – **Token ist vermutlich in Ordnung** |
| ✅, aber es kommt nichts an | Kadenz-Slot noch nicht erreicht, Tagesobergrenze (12) erreicht, oder Gate hat blockiert | `SOCIAL-AUTOPILOT-STATUS.md` lesen |

**Token widerrufen** (falls ein Secret je abhandenkommt): immer **zuerst** beim
Anbieter widerrufen, danach das Secret in GitHub ersetzen. Ein gelöschtes Secret
allein macht ein geleaktes Token nicht ungültig.

---

## 5. Was sich dadurch ändert

| | vorher | nachher |
|---|---|---|
| Sendende Kanäle | 1 (Mastodon) | bis zu 9 |
| Beiträge/Tag | ~2 | bis 12 (`max_posts_per_day_total`) |
| Manueller Aufwand | unverändert **0** | unverändert **0** |
| Laufende Kosten | 0 € | 0 € |

Jeder Kanal bekommt seine eigene Fassung – Zeichenbudget, Tonalität, Hashtag-Zahl,
Link-Position und Bildformat stehen je Kanal in `data/social/channels.yaml`.
Duplikat-Schutz, Evergreen-Sperrfrist und das Recht-/Link-Gate gelten unverändert.

---

*Zugehörig: `scripts/social_preflight.py` · `.github/workflows/social-preflight.yml` ·
`data/social/channels.yaml` · `docs/ANLEITUNG-SOCIAL-AUTOPILOT.md` ·
`AUTOMATISIERUNGS-FAHRPLAN-2026-09-29.md`*
