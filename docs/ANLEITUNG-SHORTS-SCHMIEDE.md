# 🎬 Anleitung: Shorts-Schmiede (Video & Reels)

> Premium-Integration vom 29.09.2026 · Regie: `data/social/video.yaml`
> Maschine: `scripts/social_video.py` · Workflow: `.github/workflows/social-video.yml`

**Was sie tut:** Aus einem Artikel entsteht ohne manuellen Schnitt ein
vertikales Kurzvideo (9:16, 1080×1920, 24–52 Sekunden) mit Sprecherstimme,
eingebrannten Untertiteln und Pflichthinweis – und geht als YouTube Short online.

**Kosten: 0 €.** Bild = vorhandenes Cover, Stimme = die Vorlese-Kette des Blogs
(edge-tts/Piper), Schnitt = ffmpeg, Text = Artikel + optionale Gratis-KI.

---

## 1. Warum das Video so aussieht, wie es aussieht

Jede Festlegung in `video.yaml` hat einen Grund, keinen Geschmack:

| Entscheidung | Begründung |
|---|---|
| 9:16, 1080×1920 | Das einzige Format, das auf YouTube, Instagram, TikTok und Facebook ohne Beschnitt läuft |
| 24–52 Sekunden | Lang genug für einen echten Gedanken, kurz genug für die Wiedergabe-Rate (Shorts kappt bei 60 s hart) |
| **Untertitel eingebrannt** | Rund 80 % der Wiedergaben laufen ohne Ton. Ein Finanzvideo ohne Untertitel ist ein stummes Video |
| Erste Sekunde = Zahl oder Frage | Branding am Anfang kostet Reichweite. Der Blogname steht in der Fußzeile, nicht im Hook |
| Stärkste Zahl in der Mitte | Dort sitzt die Aufmerksamkeitsdelle |
| Keine Musik | Musikrechte sind je Plattform verschieden – und bei Geldthemen wirkt eine ruhige Stimme seriöser |
| Fortschrittsbalken | Zeigt „gleich vorbei" und hält die Wiedergabe-Rate |
| Ken-Burns statt Standbild | Ein bewegtes Bild wird nicht als Diaschau weggewischt |

---

## 2. Der Aufbau jedes Videos

```
[1] HOOK    4s   Zahl oder Frage – nie „Hallo", nie der Blogname
[2] PUNKT  10s   ein Gedanke, belegt aus dem Artikel
[3] PUNKT  10s   die stärkste Zahl
[4] PUNKT  10s   der praktische Handgriff
[5] ABBINDER 5s  Verweis auf den vollständigen Ratgeber
```

Dauerhaft im Bild: der Pflichthinweis **„Allgemeine Information, keine Anlage-
oder Rechtsberatung."** und die Marken-Fußzeile. Beides ist nicht abschaltbar –
das Gate verweigert sonst die Produktion.

Der Text kommt **ausschließlich aus dem Artikel** (Kurzantwort, „Das Wichtigste
in Kürze", FAQ, Zahlen). Die Gratis-KI darf ihn nur umformulieren, nichts
hinzufügen: Erfindet sie eine Zahl, gilt automatisch wieder die Vorlage.

---

## 3. Das Gate – wann kein Video entsteht

| Prüfung | Blockiert bei |
|---|---|
| Zahlen-Pflicht | kein belastbarer Zahlenwert im Video (bei Geldthemen Pflicht) |
| Zahlen-Beleg | eine Zahl, die nicht im Artikel steht |
| Verbotene Formulierungen | „garantiert", „Geheimtipp", „die Banken hassen", „vergiss nicht zu abonnieren" |
| Untertitel-Pflicht | eine Szene ohne Untertitel |
| Hinweis-Pflicht | fehlender Rechtshinweis |
| Cover | kein Motiv |
| Dauer | unter 24 s oder über 52 s |

Fail-closed: Lieber kein Video als ein Video mit erfundener Zahl.

---

## 4. YouTube einrichten (einmalig, ~20 Minuten, 0 €)

1. **console.cloud.google.com** → Projekt anlegen → *APIs & Dienste* →
   **YouTube Data API v3** aktivieren.
2. *OAuth-Zustimmungsbildschirm* → extern → App-Namen eintragen →
   Scope `https://www.googleapis.com/auth/youtube.upload` hinzufügen →
   dein Google-Konto als Testnutzer eintragen → **danach „In Produktion" setzen**
   (im Testmodus verfällt der Refresh-Token nach 7 Tagen).
3. *Anmeldedaten* → **OAuth-Client-ID** → Typ **Desktop-App** → Client-ID und
   Secret notieren.
4. Refresh-Token einmalig holen (lokal, dauert eine Minute):

```bash
python3 - <<'EOF'
import urllib.parse, urllib.request, json
CID    = "DEINE_CLIENT_ID"
SECRET = "DEIN_CLIENT_SECRET"
q = urllib.parse.urlencode({
    "client_id": CID, "redirect_uri": "urn:ietf:wg:oauth:2.0:oob",
    "response_type": "code", "access_type": "offline", "prompt": "consent",
    "scope": "https://www.googleapis.com/auth/youtube.upload "
             "https://www.googleapis.com/auth/youtube.force-ssl"})
print("1) Öffne:\n   https://accounts.google.com/o/oauth2/v2/auth?" + q)
code = input("2) Code hier einfügen: ").strip()
d = urllib.parse.urlencode({"code": code, "client_id": CID, "client_secret": SECRET,
                            "redirect_uri": "urn:ietf:wg:oauth:2.0:oob",
                            "grant_type": "authorization_code"}).encode()
r = json.load(urllib.request.urlopen("https://oauth2.googleapis.com/token", d))
print("\nYOUTUBE_REFRESH_TOKEN =", r.get("refresh_token"))
EOF
```

5. In GitHub hinterlegen (*Settings → Secrets and variables → Actions*):

| Art | Name |
|---|---|
| Secret | `YOUTUBE_CLIENT_ID` |
| Secret | `YOUTUBE_CLIENT_SECRET` |
| Secret | `YOUTUBE_REFRESH_TOKEN` |
| Variable | `YOUTUBE_CHANNEL_ID` (optional, der Preflight nennt sie dir) |

6. **Verifizieren:** *Actions → „Social-Preflight" → Run workflow → `youtube`* →
   erwartet ✅ mit deinem Kanalnamen.

> **Kontingent:** Die YouTube Data API gibt 10.000 Einheiten pro Tag gratis.
> Ein Upload kostet ~1.600 – also bis zu 6 Videos täglich. Bei zwei Videos pro
> Woche ist das nie ein Thema.

**Instagram Reels** läuft über denselben Zugang wie Instagram-Bildposts, braucht
aber eine **öffentlich erreichbare URL** der MP4-Datei. Solange die Videos als
Lauf-Artefakt liegen, ist dieser Weg vorbereitet, aber nicht scharf.

---

## 5. Bedienung

**Auf GitHub:** *Actions → „Shorts-Schmiede" → Run workflow* →
`modus`: `plan` · `drehbuch` · `bauen` · `bauen-und-senden`.
Der Zeitplan läuft **Di + Sa 07:20 MESZ** und produziert je ein Video.

**Lokal:**

```bash
python3 scripts/social_video.py --plan                 # was wäre dran?
python3 scripts/social_video.py --drehbuch --slug SLUG # nur die Texte
python3 scripts/social_video.py --bauen --limit 1
python3 scripts/social_video.py --bauen --slug SLUG --ohne-ton   # schnell testen
python3 scripts/social_video.py --pruefe-umgebung
python3 scripts/social_video.py --selftest
```

> ⚠️ **ffmpeg muss `drawtext` können.** Die pip-Variante `imageio-ffmpeg` wird
> ohne libfreetype gebaut und kann keine Untertitel. Richtig ist
> `apt-get install -y ffmpeg`. `--pruefe-umgebung` sagt dir das in Klartext,
> statt dich mit „Filter not found" allein zu lassen.

Fertige Dateien liegen in `.cache/social-video/<slug>.mp4` (+ `.json` mit Titel,
Beschreibung und Hashtags). **Videos werden nicht versioniert** (`.gitignore: *.mp4`) –
der Workflow hängt sie 14 Tage als Artefakt an den Lauf, falls du sie von Hand
auf TikTok oder LinkedIn hochladen willst.

---

## 6. Feineinstellung

| Was | Wo in `video.yaml` |
|---|---|
| Farben, Schrift, Zoomfahrt | `marke:` |
| Szenenzahl, Länge, Regieanweisung | `szenen:` |
| Untertitelgröße, Zeilenbreite, Randabstand | `untertitel:` |
| Pflichthinweis und Fußzeile | `pflicht:` |
| Stimme (news/natural/narrator) und Tempo | `stimme:` |
| Produktionsmenge, Neu-Fenster, Wiedervorlage | `meta:` |
| Zielkanäle und Hashtags | `kanaele:` |

Nach jeder Änderung: `python3 scripts/social_video.py --selftest`.

---

## 7. Wenn etwas klemmt

| Befund | Ursache | Handgriff |
|---|---|---|
| „ffmpeg kann kein drawtext" | pip-Build ohne libfreetype | `apt-get install -y ffmpeg` |
| „keine belastbare Zahl im Video" | Artikel nennt keine Zahl | Artikel ergänzen – oder bewusst kein Video daraus |
| „Zahl steht nicht im Artikel" | KI-Politur hat erfunden | passiert automatisch: Vorlage greift; sonst `VIDEO_LLM_MODE=off` |
| „zu kurz" | Kurzantwort und Takeaways zu knapp | Artikel hat zu wenig Substanz für ein Video |
| „Cover-Bild nicht gefunden" | Cover fehlt im Front-Matter | Cover ergänzen |
| Upload „Standby" | YouTube-Secrets fehlen | Abschnitt 4 |
| Stimme fehlt, Video stumm | edge-tts im Runner nicht erreichbar | Cockpit weist `engine: stumm` aus; Lauf wiederholen |

---

## 8. Was das bringt

Zwei Videos pro Woche, vollautomatisch, aus Artikeln, die ohnehin entstehen.
YouTube Shorts ist dabei der wertvollste Kanal: Anders als ein Feed-Post bleibt
ein Short **dauerhaft suchbar** und zieht Monate später noch Zuschauer auf den Blog.

Dein Aufwand: **null.** Kontrolle: das Cockpit `SOCIAL-VIDEO-STATUS.md` und die
Job-Zusammenfassung.

---

*Zugehörig: `scripts/social_video.py` · `data/social/video.yaml` ·
`.github/workflows/social-video.yml` · `docs/RUNBUCH-SOCIAL-SECRETS.md`*
