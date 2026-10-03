# Automatisierungs-Fahrplan: Blog × Social × Gratis-KI
**Stand 29.09.2026 · Agentur-Befund für FranksFinanzcheck**

## 0. Kurzantwort

Du musst **nichts Neues bauen**. Die Maschine steht bereits: 60 GitHub-Actions-Workflows,
243 Skripte, Content-Engine v2, AGC-Autopilot, Social-Autopilot mit 10 Kanal-Adaptern,
Newsletter-Eigenbetrieb, Pinterest-Engine, SEO-/Rechtschreib-/Affiliate-Gates.

Dein Engpass ist **nicht Technik, sondern Zugangsdaten und ein fehlender Rückkanal**:

| Was | Zustand |
|---|---|
| Social-Autopilot aktiv | ✅ läuft alle 2 h |
| Kanäle mit echtem Versand | ⚠️ **nur Mastodon** (37 von 37 Posts in `data/social/state.yaml`) |
| Kanäle im Standby (Adapter fertig, Secret fehlt) | ❌ Bluesky, LinkedIn, X, Threads, Facebook, Instagram, Telegram, Reddit, Pinterest-Refresh |
| Rückkanal „Was performt?" → Redaktionsplan | ❌ fehlt (nur Pinterest hat `pinterest_perf_feedback.py`) |
| Kommentare/Antworten | ✅ **gebaut 29.09.2026** – Dialog-Autopilot (abgestufte Autonomie) |
| Video/Shorts | ✅ **gebaut 29.09.2026** – Shorts-Schmiede (9:16, ffmpeg + Gratis-TTS) |

**Hebel-Reihenfolge: erst Tokens (Tag 1, ~90 Min, 0 €), dann Feedback-Loop, dann Video.**

---

## 1. Sofort (Tag 1, ~90 Minuten, einmalig, 0 €)

Jeder Kanal braucht nur sein Secret unter *Settings → Secrets and variables → Actions*.
Der Autopilot erkennt ihn beim nächsten Lauf von selbst — keine Code-Änderung.

Reihenfolge nach Aufwand-Nutzen für Finanz-Content:

1. **Bluesky** (5 Min, kein Review) — `BLUESKY_IDENTIFIER`, `BLUESKY_APP_PASSWORD`
   → App-Passwort in den Bluesky-Einstellungen erzeugen. Größter Sofort-Effekt.
2. **Telegram** (10 Min, kein Review) — `TELEGRAM_BOT_TOKEN`, Variable `TELEGRAM_CHAT_ID`
   → Kanal anlegen, @BotFather-Bot als Admin hinzufügen. Eigener Verteiler, keine Plattformwillkür.
3. **LinkedIn** (20 Min) — `LINKEDIN_ACCESS_TOKEN` (+ `LINKEDIN_PERSON_URN`)
   → Beste Zielgruppe für Finanzthemen. Achtung: Token läuft alle ~60 Tage ab.
4. **Facebook-Seite + Instagram** (30 Min, eine Meta-App deckt beide + Threads ab)
   → `FACEBOOK_PAGE_TOKEN`/`FACEBOOK_PAGE_ID`, `INSTAGRAM_ACCESS_TOKEN`/`INSTAGRAM_ACCOUNT_ID`,
   `THREADS_ACCESS_TOKEN`/`THREADS_USER_ID`.
5. **X** (15 Min) — 4 Secrets; Free-Tier erlaubt ~500 Posts/Monat, reicht für `max_per_day: 2`.
6. **Reddit** — bewusst zuletzt/optional. `launch_delay_hours: 72` und Profil-Post sind
   korrekt konfiguriert, aber Selbstpromo ist hier ein Reputationsrisiko. Empfehlung:
   `enabled: false` lassen, bis du 2–3 Subreddits manuell erschlossen hast.

**Verifikation (gebaut am 29.09.2026):** Nach jedem Secret der Beweis-Lauf
`npm run social:preflight` bzw. *Actions → „Social-Preflight"*. Er ruft je Kanal
nur-lesend „Wer bin ich?" auf und veröffentlicht nichts.
Klickpfad je Kanal: **`docs/RUNBUCH-SOCIAL-SECRETS.md`**.

**Ergebnis:** aus 2 Posts/Tag werden bis zu 12 (`max_posts_per_day_total: 12`),
mit kanalnativen Fassungen, Gate und Duplikat-Schutz — ohne einen manuellen Handgriff mehr.

### Token-Wache nachziehen
LinkedIn/Threads/Instagram-Tokens verfallen. Prüfe, ob `secrets-wache` / `bot-watchdog.yml`
die Ablaufdaten dieser Kanäle wirklich meldet — sonst fällt ein Kanal still in den Standby
zurück und du merkst es erst Wochen später im Cockpit.

---

## 2. Kurzfristig (Woche 1–2): der fehlende Rückkanal → **erledigt 03.10.2026**

`scripts/social_perf_feedback.py` + Integration in `social_planner.py`
(`docs/ANLEITUNG-SOCIAL-PERF-FEEDBACK.md`). Genau nach dem unten skizzierten
Muster gebaut: Score je Winkel/Themenwelt, Bandit-Gewichtung (80/20),
Cooldown-Anpassung, Standby-sicher ohne Daten. Ehrlicher Befund aus dem ersten
echten Lauf: Das Mastodon-Konto hat 0 Follower, also bislang überall
Engagement = 0 – die Lernschleife greift automatisch, sobald echte Reichweite
entsteht. Ursprüngliche Planungsnotiz bleibt unten zur Nachvollziehbarkeit stehen.

Heute plant `social_planner.py` nach Regeln (Launch-Welle + Evergreen-Rotation), aber
**ohne Wissen darüber, was funktioniert hat**. Das ist die größte verbleibende Handarbeit,
weil du sonst selbst ins Cockpit schauen und nachjustieren musst.

**Vorschlag `scripts/social_perf_feedback.py`** (Muster existiert schon bei Pinterest):

- Täglich je Kanal die Metriken der letzten 30 Tage abholen
  (Mastodon `/api/v1/accounts/:id/statuses` → Boosts/Favs; Bluesky `getAuthorFeed`;
  LinkedIn `socialActions`; Telegram `views`; Umami-Referrer als kanalübergreifende Wahrheit).
- Score je **Winkel** (`angles:` — nutzen/zahl/mythos/frage/vergleich) und je **Themenwelt**.
- Schreibt `data/social/performance.yaml`; der Planer gewichtet Winkel und Sendezeiten danach
  (Multi-Armed-Bandit light: 80 % Sieger-Winkel, 20 % Exploration).
- Top-5-Evergreens bekommen kürzeren `recycle_cooldown_days`, Flops längeren.

**Zweiter Rückkanal – Content-Engine füttern:** Social-Sieger-Themen und Umami-Top-Suchbegriffe
als Priorisierungs-Signal in den AGC-Redaktionskalender geben. Dann schreibt der Blog
automatisch mehr von dem, was zieht.

---

## 3. Mittelfristig (Monat 1–2)

**a) Antwort-Assistent statt Voll-Automat (Kommentare/Mentions)** → **erledigt 29.09.2026**
(`scripts/social_dialog.py`, `data/social/dialog.yaml`, `docs/ANLEITUNG-DIALOG-AUTOPILOT.md`)
Vollautomatische Antworten sind bei Finanzthemen ein Rechtsrisiko (Beratungs-Anschein).
Richtiger Zuschnitt: Bot sammelt Mentions/Kommentare/DMs aller Kanäle, formuliert per
Groq/Gemini einen Antwortvorschlag mit Beleglink aus dem eigenen Bestand und legt ihn als
GitHub-Issue-Checkliste ab. Du tippst 3×/Woche „ok" — 5 Minuten statt 5 Kanäle durchklicken.

**b) Vertikal-Video (der einzige echte Reichweiten-Hebel, der dir noch fehlt)** → **erledigt 29.09.2026**
(`scripts/social_video.py`, `data/social/video.yaml`, `docs/ANLEITUNG-SHORTS-SCHMIEDE.md`)
Aus jedem Artikel entsteht bereits Text + Cover. Ergänzen:
`ffmpeg` (gratis) + vorhandene TTS-Pipeline (du hast schon Audio-Backfill) + Kenburns auf dem
2:3-Cover + Untertitel aus dem Skript → 30–45-s-MP4 für Instagram Reels, YouTube Shorts,
TikTok, Facebook. Rein in `social_images.py`-Nachbarschaft als `social_video.py`, Adapter
`youtube.py` (Data API v3, Gratis-Kontingent) und `tiktok.py`. Läuft in GitHub Actions, 0 €.

**c) Newsletter × Social koppeln**
Die Social-Sieger der Woche als „Meistgelesen"-Block automatisch in den Freitags-Newsletter;
umgekehrt Newsletter-Klick-Sieger in die Evergreen-Rotation.

**d) Ein Cockpit statt zwölf Reports** → **erledigt 03.10.2026**
(`scripts/cockpit.py`, `COCKPIT.md`, `.github/workflows/cockpit.yml`,
`docs/ANLEITUNG-COCKPIT.md`)
Du hast >50 Status-Markdowns im Root. Ein täglicher `COCKPIT.md` mit Ampel je Subsystem
(Content · Social · Newsletter · SEO · Affiliate · Deploy/Secrets) + Telegram-Push an dich
selbst (nur bei Rot). Alles andere liest du nur noch, wenn eine Ampel rot ist. Das senkt
deine tatsächliche Eingriffszeit stärker als jede weitere Automatisierung.

---

## 4. Kostenrahmen (Dauervorgabe „0 €" bleibt erfüllt)

| Baustein | Kosten |
|---|---|
| GitHub Actions (public repo) | 0 € |
| Groq + Gemini Free Tier (Texte, Politur, Antwortvorschläge) | 0 € |
| Mastodon/Bluesky/Telegram/Reddit APIs | 0 € |
| Meta-Graph (FB/IG/Threads), LinkedIn, X Free, Pinterest, YouTube Data API | 0 € |
| ffmpeg, Piper/Coqui-TTS, Umami self-hosted | 0 € |

Einziges Limit: API-Rate-Limits. Die bestehende Standby-/Retry-Logik fängt das bereits sauber ab.

---

## 5. Was du danach noch manuell tust

- **3×/Woche 5 Min:** Antwortvorschläge freigeben.
- **1×/Woche 15 Min:** Cockpit-Ampeln, KI-Redaktions-Entwürfe promoten (`ki_redaktion.py --promote`).
- **1×/Quartal 30 Min:** Tokens erneuern, Themenwelten/Brand-Brain nachschärfen.

Das ist realistisch das Minimum, das bleiben *sollte* — alles darunter heißt bei
Finanz-Content: unkontrollierte Haftung.

---

## 6. Nächster Schritt

Sag mir, womit ich anfangen soll:
1. ~~Secret-Setup-Runbuch je Kanal mit Klickpfad + Verifikations-Lauf~~ → **erledigt 29.09.2026**:
   `docs/RUNBUCH-SOCIAL-SECRETS.md`, `scripts/social_preflight.py`, `social-preflight.yml`,
2. ~~`scripts/social_perf_feedback.py` + Planer-Gewichtung bauen~~ → **erledigt 03.10.2026**,
3. ~~`social_video.py` + YouTube-Adapter~~ → **erledigt 29.09.2026**,
4. ~~Antwort-Assistent~~ → **erledigt 29.09.2026**,
5. ~~Cockpit-Konsolidierung (ein `COCKPIT.md` statt >50 Status-Dateien)~~ → **erledigt 03.10.2026**.
