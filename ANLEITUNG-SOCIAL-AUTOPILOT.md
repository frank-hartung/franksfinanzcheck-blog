# 🛰️ ANLEITUNG: Social-Autopilot (Premium)

> **Kurzfassung:** Der Blog veröffentlicht ab jetzt **vollautomatisch** auf allen
> angebundenen Social-Kanälen – mit **eigener Fassung je Kanal**, geplant über
> 14 Tage, geprüft von einem harten Gate. **Du musst nichts mehr tun:**
> keine Themensuche, keine Textarbeit, kein Terminieren, kein Klick.
>
> **Dein einziger Auftrag (einmalig):** Die Zugangsdaten der Kanäle hinterlegen,
> die du bespielen willst. Alles andere erledigt der Autopilot – jeden Tag,
> alle zwei Stunden, rund um die Uhr.

---

## 1 · Was der Autopilot jeden Lauf tut

| Stufe | Baustein | Was passiert |
|---|---|---|
| 1 | **Planen** `social_planner.py` | 14-Tage-Plan: jeder neue Artikel läuft als **Launch-Welle** über alle Kanäle (gestaffelt nach deren Optimalzeiten); danach übernimmt das **Evergreen-Recycling** – derselbe Artikel auf demselben Kanal erst nach 60–120 Tagen Sperrfrist, und dann mit einem **anderen inhaltlichen Winkel** |
| 2 | **Texten** `social_copywriter.py` | Aus dem Artikel werden Material-Bausteine gezogen (Kurzantwort = Hook, „Das Wichtigste in Kürze", Euro-/Prozent-Zahlen, FAQ-Frage, Pillar). Daraus entsteht pro Kanal eine **eigene Fassung** – mit dem Zeichenbudget, der Hashtag-Zahl, der Tonalität und der Link-Logik dieses Netzes |
| 3 | **Prüfen** `social_gate.py` | 10 harte Regeln, **fail-closed**: Länge, Link-Hygiene (niemals ein Affiliate-`/go/`-Link), unzulässige Versprechen, Hashtags, Emoji-Budget, Sprache, Spam-Muster, **Duplikat-Schutz**, **Fakten-Treue** (keine erfundene Zahl), Bildpflicht |
| 4 | **Bild** `social_images.py` | Kanäle mit Format-Zwang (Instagram 4:5) bekommen eine eigene Bildvariante. Ist die URL noch nicht live, wartet der Beitrag einen Lauf – statt mit einer 404 leerzulaufen |
| 5 | **Senden & Berichten** | Versand über den Kanal-Adapter, bis zu 3 Versuche, danach kontrollierter Abbruch mit Vermerk. Ergebnis: **Cockpit** in der Job-Zusammenfassung + `SOCIAL-AUTOPILOT-STATUS.md` |

**Betriebsregeln, die du kennen solltest**

* Fehlt ein Token, läuft der Kanal im **Standby** – sichtbar im Cockpit, **ohne Fehler und ohne Alarm**.
* Ein gescheitertes Senden wird **nicht sofort verworfen** (3 Versuche), ein blockierter Text bekommt **automatisch einen anderen Winkel**.
* Nur ein echter **Vollausfall** (≥ 3 Fehler, kein Erfolg) erzeugt ein rotes Workflow-Ergebnis und damit die bestehende Alarmierung.

**Workflow:** `.github/workflows/social-autopilot.yml` – alle 2 Stunden von 05:20 bis 19:20 UTC. Der Planer rechnet in **Berliner Zeit**, damit die Taktung im Sommer (MESZ) wie im Winter (MEZ) stimmt, ohne dass ein Cron angepasst werden muss.

---

## 2 · Schnellstart (3 Schritte, ~5 Minuten je Kanal)

1. **Kanal wählen** (Tabelle unten) und dort ein Konto anlegen bzw. bereitstellen.
2. **Zugangsdaten hinterlegen:** Repo → *Settings → Secrets and variables → Actions*
   → *New repository secret* (Tokens) bzw. *Variables* (IDs, Handles, Instanz-URLs).
3. **Nichts weiter.** Beim nächsten Lauf erkennt der Autopilot den Kanal von selbst.
   Kontrolle: Actions → *Social-Autopilot* → letzter Lauf → **Job-Zusammenfassung** (dort steht das komplette Cockpit).

> 💡 **Reihenfolge-Empfehlung der Agentur:** Mastodon → Bluesky → Telegram → LinkedIn → Pinterest → Facebook/Threads/Instagram → X → Reddit.
> Die ersten drei sind kostenlos, in Minuten eingerichtet und laufen **ohne Token-Ablauf**.

---

## 3 · Kanäle und ihre Kriterien (das Playbook)

Alle Werte stehen in **`data/social/channels.yaml`** – der Single Source of Truth.
Änderst du dort eine Zahl, gilt sie ab dem nächsten Lauf.

| Kanal | Zeichen | Hashtags | Emojis | Bild | Link | Taktung | Token läuft ab |
|---|---:|---:|---:|---|---|---|---|
| **Mastodon** | 500 | 2–4 | 2 | optional, Alt-Text | am Ende | 2/Tag | **nie** |
| **Bluesky** | 300 | 1–2 | 1 | optional, Alt-Text | am Ende | 2/Tag | nie (App-Passwort) |
| **LinkedIn** | 2.900 (optimal ≤ 1.800) | 3–5 | 0 | optional | **erster Kommentar** | 1/Tag, Mo–Fr | ~60 Tage |
| **X (Twitter)** | 280 | 1–2 | 1 | optional | am Ende (zählt nur 23 Zeichen!) | 3/Tag | abhängig vom Tarif |
| **Threads** | 500 | 1–2 | 1 | optional | am Ende | 2/Tag | ~60 Tage (Long-Lived) |
| **Facebook (Seite)** | 1.200 (optimal ≤ 480) | 1–3 | 1 | optional | am Ende | 2/Tag | Seitentoken (lange) |
| **Instagram** | 2.200 | 5–12 | 3 | **Pflicht, 4:5** | **keiner** („Link in der Bio") | 1/Tag | ~60 Tage |
| **Pinterest** | 500 (Titel ≤ 100) | 2–5 | 0 | **Pflicht, 2:3** | am Ende | 1/Tag | 30 Tage – **Broker erneuert automatisch** |
| **Telegram (Kanal)** | 4.096 (optimal ≤ 700) | 1–3 | 2 | optional | am Ende | 2/Tag | nie (Bot-Token) |
| **Reddit** | 40.000 (Titel ≤ 300) | 0 | **0** | – | im Text | **1/Tag** | bei Passwortwechsel |

**Globale Leitplanken:** maximal **12 Beiträge pro Tag über alle Kanäle**, maximal **2 Kanäle pro Artikel und Tag**, auf demselben Kanal nie zweimal hintereinander derselbe Pillar.

---

## 4 · Einrichtung je Kanal

### 🦣 Mastodon *(empfohlen: kostenlos, Token läuft nie ab)*

1. Konto auf einer Instanz (z. B. [mastodon.social](https://mastodon.social)).
2. *Einstellungen → Entwicklung → Neue Anwendung* → Scopes **`write:statuses`** und **`write:media`**.
3. Zugriffstoken kopieren → Secret **`MASTODON_ACCESS_TOKEN`**.
4. Optional Variable **`MASTODON_INSTANCE`** (Default `https://mastodon.social`).

### 🦋 Bluesky *(kostenlos, 300 Zeichen)*

1. Konto anlegen, dann *Einstellungen → App-Passwörter → App-Passwort erstellen*.
   ⚠️ **Nicht** das Account-Passwort verwenden.
2. Secret **`BLUESKY_IDENTIFIER`** = dein Handle (z. B. `franksfinanzcheck.de`),
   Secret **`BLUESKY_APP_PASSWORD`** = das erzeugte App-Passwort.
3. Optional Variable **`BLUESKY_PDS`** (Default `https://bsky.social`).
   Links und Hashtags werden als *Facets* übertragen – also echt klickbar.

### 💼 LinkedIn *(Reichweite im Business-Umfeld)*

1. [LinkedIn Developer Portal](https://developer.linkedin.com/) → App anlegen, Produkt **„Share on LinkedIn"** hinzufügen.
2. [OAuth-Token-Generator](https://www.linkedin.com/developers/tools/oauth/token-generator) → Scope **`w_member_social`** → Secret **`LINKEDIN_ACCESS_TOKEN`**.
3. Personen-URN: `https://api.linkedin.com/v2/userinfo` mit dem Token aufrufen → Feld `sub`
   → Variable **`LINKEDIN_PERSON_URN`** = `urn:li:person:<sub>`. Für eine Unternehmensseite stattdessen
   **`LINKEDIN_ORG_URN`** = `urn:li:organization:<id>`.
4. **Wichtig:** LinkedIn-Tokens laufen nach ~60 Tagen ab – die Secrets-Wache meldet die Erneuerung rechtzeitig.
   Der Autopilot setzt den Link automatisch in den **ersten Kommentar** (Reichweiten-Standard).

### 🐦 X (Twitter) *(kostenpflichtige API; ohne Secrets einfach Standby)*

1. [Developer Portal](https://developer.x.com/) → App mit **Read and Write**-Rechten.
2. Vier Werte als Secrets: **`X_API_KEY`**, **`X_API_SECRET`**, **`X_ACCESS_TOKEN`**, **`X_ACCESS_SECRET`**.
3. Besonderheit: X zählt jeden Link mit **23 Zeichen** – das nutzt der Autopilot aus und
   rechnet dein Budget korrekt (ein 140-Zeichen-Link kostet nur 23).

### 🧵 Threads

1. Meta-App anlegen, Threads-Konto verknüpfen, Long-Lived-Token erzeugen → Secret **`THREADS_ACCESS_TOKEN`**.
2. Eigene User-ID (`https://graph.threads.net/v1.0/me?fields=id`) → Variable **`THREADS_USER_ID`**.

### 👥 Facebook (Seite)

1. Facebook-**Seite** anlegen (Beiträge gehen immer über eine Seite, nie über ein Privatprofil).
2. Meta-App → Graph API Explorer → Seitentoken mit `pages_manage_posts`, `pages_read_engagement`
   → Secret **`FACEBOOK_PAGE_TOKEN`**, Variable **`FACEBOOK_PAGE_ID`**.

### 📸 Instagram

1. Instagram-Konto als **Business- oder Creator-Konto** (und mit einer Facebook-Seite verbunden).
2. Meta-App mit `instagram_basic`, `instagram_content_publish` → Secret **`INSTAGRAM_ACCESS_TOKEN`**,
   Variable **`INSTAGRAM_ACCOUNT_ID`** (IG-User-ID, über die Graph-API ermittelbar).
3. Der Autopilot rendert automatisch eine **4:5-Variante** (1080 × 1350) des Covers – das
   2:3-Cover des Blogs würde Instagram sonst ablehnen.

### 📌 Pinterest *(Refresh-Pins; Erst-Pins bleiben bei `pinterest_engine.py`)*

* Der Token-Broker (`scripts/pinterest_token.py`) erneuert den Zugang **selbstständig**; die
  Secrets **`PINTEREST_TOKEN_KEY`**, **`PINTEREST_APP_ID`**, **`PINTEREST_APP_SECRET`** müssen nur einmal gesetzt sein.
* Variable **`PINTEREST_BOARD_ID`** = Standard-Board. Ohne sie wird das Board aus
  `data/pinterest_boards.yaml` passend zum Pillar des Artikels aufgelöst.
* **Arbeitsteilung:** *neue* Artikel pinnt weiterhin `pinterest-ai.yml` (hart erprobte
  Anti-Spam-Taktung). Der Autopilot übernimmt die **Refresh-Pins** ab 45 Tagen Alter – neu
  getextet, neu gewinkelt. Kein Kanal bekommt dadurch zwei Pins desselben Artikels am selben Tag.

### ✈️ Telegram (Kanal)

1. [@BotFather](https://t.me/BotFather) → `/newbot` → Token → Secret **`TELEGRAM_BOT_TOKEN`**.
2. Bot als **Administrator** in deinen Kanal einladen.
3. Variable **`TELEGRAM_CHAT_ID`**: `@deinkanal` oder die numerische ID (z. B. `-100…`).
   Telegram-Abonnenten bekommen neue Artikel **zuerst** (Verzögerung 0 Stunden).

### 🤝 Reddit *(nur mit Augenmaß)*

1. [Reddit Apps](https://www.reddit.com/prefs/apps) → *create another app* → Typ **script**.
2. Secrets **`REDDIT_CLIENT_ID`**, **`REDDIT_CLIENT_SECRET`**, **`REDDIT_USERNAME`**, **`REDDIT_PASSWORD`**.
3. Variable **`REDDIT_SUBREDDIT`** – **leer lassen**, dann postet der Autopilot auf dein
   **eigenes Profil** (`u/<user>`). Das ist der sichere Weg: keine Community-Regel gegen
   Eigenwerbung verletzt. Ein Subreddit nur setzen, wenn dessen Regeln das ausdrücklich erlauben.
4. Sperrschutz: maximal **ein** Reddit-Beitrag pro Tag, frühestens **72 Stunden** nach
   Erscheinen des Artikels, ohne Hashtags und ohne Emojis – Community-Ton statt Marketington.

---

## 5 · Wie die Texte entstehen (Content-Erstellung ohne dich)

### Material (aus dem Artikel, nie erfunden)

* **Kurzantwort** → der Hook (bester Satz des Artikels)
* **„Das Wichtigste in Kürze"** → die Aufzählungspunkte (fehlt der Block, übernehmen die Folgesätze)
* **Euro-/Prozent-Zahlen** → das Kapital dieses Blogs („240 € im Jahr")
* **FAQ-Frage** → der Frage-Winkel
* **Pillar** → Themenwelt, Mythen-Bibliothek und Abschlussfrage

### Winkel (Rotation – damit sich kein Beitrag wiederholt)

| Winkel | Aufbau | Besonders stark auf |
|---|---|---|
| `nutzen` | Titel + Nutzen-Satz + Link | alle |
| `zahl` | Zahl zuerst, dann der Beleg | X, Mastodon, LinkedIn |
| `takeaway` | 3 Punkte, die zählen | Mastodon, Telegram, Instagram |
| `frage` | Frage + Antwort | Facebook, Bluesky, LinkedIn |
| `mythos` | „Mythos: … / Fakt: …" (Myth aus kuratierter Pillar-Bibliothek) | Mastodon,Threads, Instagram |
| `zitat` | Kernaussage in Anführungszeichen | LinkedIn, Bluesky |
| `vergleich` | „A oder B? Die Antwort hängt an einer Zahl." | LinkedIn, Facebook |
| `thread` | 4–5 Teile: Aufhänger → Punkte → Link | Mastodon, X, Bluesky |
| `karussell` | Bildstrecke mit 4–6 Slides | Instagram |

### KI-Politur (Hybrid)

Mit vorhandenem Gratis-Key (**`GROQ_API_KEY`** oder **`GEMINI_API_KEY`**, wie im Rest des Blogs)
wird die fertige Vorlage kanalgerecht geschliffen. **Der Entwurf bleibt immer die Rückfallebene:**
Ohne Key, bei Timeout oder wenn die KI gegen eine Kanalregel verstößt (zu lang, Link fehlt,
Hashtags verloren, **erfundene Zahl**), gilt automatisch die deterministische Vorlage.
Steuerung über die Variable **`SOCIAL_COPY_MODE`**: `auto` (Default) · `llm` · `off`.

---

## 6 · Das Qualitäts-Gate (10 Regeln, fail-closed)

| Nr | Prüfung | Beispiel für eine Ablehnung |
|---|---|---|
| L1 | Zeichenlänge in **Plattform-Zählung** | 512 Zeichen auf Mastodon |
| L2 | Link-Pflicht & -Hygiene | ein `/go/`-Affiliate-Link oder ein Link-Shortener |
| L3 | Recht & Versprechen | „garantiert", „risikofrei", gesperrte Phrasen |
| L4 | Hashtags (Anzahl, Länge, Schreibweise) | 10 Hashtags auf X |
| L5 | Emoji-Budget des Kanals | 4 Emojis auf Mastodon (erlaubt: 2) |
| L6 | Sprache | ein englischer Text |
| L7 | Shouting / Spam | „SUPER!!!", Link-Sammlungen |
| L8 | **Duplikat-Schutz** | ≥ 72 % Textähnlichkeit zu einem früheren Posting |
| L9 | **Fakten-Treue** | eine Zahl, die nicht im Artikel steht |
| L10 | Bildpflicht | Instagram ohne Bild |

Fällt ein Beitrag durch, probiert der Autopilot **automatisch einen anderen Winkel** (bis zu 3).
Bleibt er blockiert, steht der Grund im Cockpit – und der Beitrag wird **nicht** gesendet.

---

## 7 · Steuern, Testen, Eingreifen

```bash
# Probelauf: zeigt alle Beiträge, sendet nichts
python3 scripts/social_studio.py --run --dry-run

# Wie sieht der Lauf morgen früh aus? (Zeitpunkt simulieren, ohne Netz)
python3 scripts/social_studio.py --run --dry-run --now "2026-09-13T07:45:00+02:00"

# Nur ein Kanal / nur eine Menge
python3 scripts/social_studio.py --run --channel mastodon --limit 2

# Plan erneuern (sendet nichts) · Cockpit schreiben · Gesundheitsprüfung
python3 scripts/social_studio.py --plan
python3 scripts/social_studio.py --status
python3 scripts/social_studio.py --selftest

# Kanalstände, Kanalkriterien und der 14-Tage-Plan
python3 scripts/social_studio.py --status
cat data/social/schedule.yaml
```

**Im Betrieb (GitHub):**

| Wunsch | Weg |
|---|---|
| Autopilot **stoppen** | Actions → *Social-Autopilot* → **Disable workflow** |
| **Einmalig** starten | Actions → *Social-Autopilot* → *Run workflow* (Modus `run`, `plan`, `dry-run`, `status`) |
| Nur einen Kanal schicken | *Run workflow* → Feld **kanal** (z. B. `mastodon`) |
| **Taktung** ändern | `data/social/channels.yaml` → je Kanal `cadence:` (Tage, Zeiten, `max_per_day`) |
| **Globales Limit** | `meta.max_posts_per_day_total` (Default 12) |
| **Sperrfrist** ändern | je Kanal `cadence.recycle_cooldown_days` (Default 75) |
| Kanal **abschalten** | `enabled: false` (oder einfach das Secret löschen) |
| KI **abschalten** | Variable `SOCIAL_COPY_MODE = off` |

---

## 8 · Abgrenzung zu den bestehenden Automaten

| Automat | Aufgabe | Verhältnis zum Autopiloten |
|---|---|---|
| `pinterest-ai.yml` | **Erst-Pins** neuer Artikel | bleibt – der Autopilot pinnt nur *Refresh-Pins* (ab 45 Tage) |
| `mastodon-seo.yml` | heilt **bestehende** Toots (Alt-Text, Keywords, Kanonik) | bleibt – ergänzt den Autopiloten |
| `social-ai.yml` | alter Mastodon-/LinkedIn-Poster | **Zeitplan entfernt** (Doppelpost-Gefahr); nur noch manueller Notlauf |
| `newsletter-daily.yml` | E-Mail-Digest | bleibt unberührt |
| Content-Engine v2 | schreibt und veröffentlicht Artikel | bleibt unberührt – der Autopilot bewirbt nur, was live ist |

**Kein Konflikt:** Der Autopilot verlinkt ausschließlich **kanonische Artikel-URLs mit UTM-Marke**
(`/posts/<slug>/?utm_source=<kanal>…`). Affiliate-Links (`/go/…`) verlassen den Blog nur über die
Artikelseiten selbst – das Gate verbietet sie in Social-Texten hart.

---

## 9 · Häufige Fragen

**Muss ich noch etwas freigeben?** Nein. Planung, Text, Bild, Prüfung und Versand laufen
automatisch. Du kannst jederzeit eingreifen (Workflow deaktivieren, `enabled: false`,
`SOCIAL_COPY_MODE=off`), musst es aber nicht.

**Was passiert, wenn ein Kanal nicht eingerichtet ist?** Er bleibt im Standby. Der Lauf ist
trotzdem grün – ein fehlendes Token ist ein **Konfigurationsstand**, kein Fehler.

**Kommen Beiträge doppelt raus?** Nein. Der Stand (`data/social/state.yaml`) ist versioniert und
merkt sich jeden Post je Kanal und Artikel; zusätzlich prüft das Gate die Textähnlichkeit
(L8) und der Planer verhindert Doppelplanungen.

**Wie viele Beiträge am Tag?** Standard: bis zu **12 über alle Kanäle**, je Kanal 1–3 – gestreut
über dessen Optimalzeiten (07:30–21:00 Berliner Zeit).

**Was kostet mich das?** Nichts. Alle Kanäle laufen über kostenlose Entwicklerzugänge; die
optionale Textpolitur nutzt ausschließlich die vorhandenen Gratis-Keys (Groq/Gemini).

**Ein Kanal meldet „fehlgeschlagen" – was jetzt?** Der Beitrag wird bis zu dreimal erneut
versucht. Danach steht der Grund (API-Fehlertext) im Cockpit unter *Blockaden & Fehler*.
Meist ist ein abgelaufener Token die Ursache (LinkedIn/Threads/Instagram: ~60 Tage).

**Kann ich einen Kanal testen, ohne dass etwas rausgeht?** Ja:
`python3 scripts/social_studio.py --run --dry-run --channel <kanal>`.

---

*Stand: 12.09.2026 · Bausteine: `scripts/social_studio.py` (Orchestrierung),
`scripts/social_planner.py`, `scripts/social_copywriter.py`, `scripts/social_gate.py`,
`scripts/social_images.py`, `scripts/social_channels/` (10 Adapter) ·
Playbook: `data/social/channels.yaml` · Cockpit: `SOCIAL-AUTOPILOT-STATUS.md`*
