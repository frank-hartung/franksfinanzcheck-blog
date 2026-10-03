# ✿ Poppy-Werkbank – Anleitung (kostenloser Poppy.ai-Nachbau)

**Stand:** 03.10.2026 · **Zweck:** Quellen (YouTube, Podcast, Artikel, PDF,
Notizen) automatisch einsammeln, als Insight-Karten auf einem Board sammeln
und in Franks Stimme zu Blog-Entwürfen plus Newsletter-, Mastodon- und
Pinterest-Texten verwerten – **komplett kostenlos, ohne Poppy.ai-API**,
self-hosted im eigenen Repo.

---

## 1. Die Idee in fünf Sätzen

Poppy.ai kostet ~30 $/Monat und lebt davon, Quellen auf einem Board zu
sammeln und in der eigenen Marken-Stimme zu verwerten. Genau das kann die
eigene Infrastruktur schon: Gratis-Keys (Groq/Gemini) sind vorhanden,
die Marken-Stimme liegt als `data/brand_brain.yaml` +
`data/schreibstil.yaml` vor, und die Veröffentlichungskette
(cadence_guard, Gates) ist etabliert. Die Poppy-Werkbank verbindet das zu
einem Nachbau ohne Fremd-API und ohne Abo: Einsammeln → Board → Verwerten.
Wie immer gilt: **Die Maschine schreibt Entwürfe, der Mensch veröffentlicht.**

## 2. Bausteine

| Baustein | Ort | Aufgabe |
|---|---|---|
| Kernbibliothek | `scripts/poppy_lib.py` | Quelltyp-Erkennung, YouTube-Transkripte, Feed-/Artikel-/PDF-Extraktion, Karten-Board, Gratis-Whisper (opt-in), LLM-Kette |
| Einsammeln | `scripts/poppy_ingest.py` | Quelle → Karte mit Insights (KI, sonst Heuristik) |
| Verwerten | `scripts/poppy_repurpose.py` | Karte → Blog-Entwurf (draft) + Newsletter/Mastodon/Pinterest |
| Board | `scripts/poppy_board.py` + `tools/poppy-board/` | lokales Dashboard (`.cache/poppy-board/`, offline, dunkel/hell) |
| Watchlist | `data/poppy/quellen.yaml` | beobachtete Kanäle/Feeds + Einstellungen |
| Karten | `data/poppy/cards/*.json` | der Board-Zustand (versioniert, Dedupe über Quell-URL) |
| Workflow | `.github/workflows/poppy-werkbank.yml` | Di + Sa 05:23 MESZ automatisch + manueller Start |
| Tests | `scripts/tests/test_poppy_werkbank.py` | 17 Unit-Tests (offline, deterministisch) |

## 3. Benutzung (lokal)

```bash
# 1) Quelle einsammeln (mehrfach möglich)
python3 scripts/poppy_ingest.py --quelle "https://youtu.be/VIDEO_ID"
python3 scripts/poppy_ingest.py --quelle "https://finanztip.de/feed/"
python3 scripts/poppy_ingest.py --quelle "Notiz: Grundversorger-Angebot prüfen"

# 2) Watchlist abrufen (data/poppy/quellen.yaml)
python3 scripts/poppy_ingest.py --watchlist

# 3) Karten verwerten (max. 2/Lauf, siehe quellen.yaml)
python3 scripts/poppy_repurpose.py --auto
python3 scripts/poppy_repurpose.py --karte 2026-10-03-stromtarife-wechseln-video

# 4) Board ansehen
python3 scripts/poppy_board.py && npm run poppy:serve
# → http://127.0.0.1:4178  (Spalten „Neu“/„Verwertet“, Copy-Buttons)
```

Kurzformen über `package.json`: `npm run poppy:watchlist`,
`npm run poppy:verwerten`, `npm run poppy:board`, `npm run poppy:serve`.

**Podcast-Audio transkribieren** (Gratis-Whisper auf Groq, max. 25 MB pro
Episode): in `data/poppy/quellen.yaml` `audio_transkription: true` setzen
oder einmalig `--transkribieren` mitgeben. Standard ist **aus** – Shownotes
reichen meist, und das Gratis-Kontingent bleibt für Artikel +
Content-Engine.

## 4. Benutzung (GitHub, automatisch)

- **Scheduler:** Di + Sa 05:23 MESZ – Watchlist abrufen, neue Karten
  verwerten, committen (Rolle „poppy“). Der Slot ist bewusst von
  KI-Redaktion (06:53 MESZ) und Content-Engine (08:10 MESZ) entzerrt.
- **Manuell:** Actions → „Poppy-Werkbank“ → *Run workflow*:
  - `aktion=watchlist` – Watchlist + Verwerten (wie Scheduler)
  - `aktion=quellen` – eigene Quellen ins Feld `quellen` (eine pro Zeile:
    YouTube-/Feed-/Artikel-/PDF-URL **oder** freie Notiz)
  - `aktion=nur_verwerten` – nur wartende Karten verwerten
  - `aktion=komplett` – beides
- **Keys:** es gelten die vorhandenen Secrets `GROQ_API_KEY` /
  `GEMINI_API_KEY` (Kosten-Regel: nur Gratis-Zugänge, wie KI-Redaktion).

## 5. Veröffentlichen – der einzige Weg

Poppy-Entwürfe tragen `draft: true` und `ki_redaktion: "poppy"` im
Frontmatter und sind damit **bewusst Teil der KI-Redaktions-Kette**:

```bash
python3 scripts/ki_redaktion.py --status          # alle Entwürfe sehen
python3 scripts/ki_redaktion.py --promote <slug>  # Freigabe → Re-Queue
```

`cadence_guard` veröffentlicht dann am nächsten Publikationstag (Mo/Mi/Fr,
2–3 Artikel/Tag). Offline-Gerüste (ohne Keys entstanden) enthalten
`TODO(KI-REDAKTION…)`-Marker und sind dadurch **nicht** promotefähig –
erst fertigstellen, dann freigeben.

## 6. Qualität & Kosten

- **Anti-Halluzination:** Faktenanker kommen ausschließlich aus der
  Quellkarte (Transkript/Shownotes/Artikel/PDF/Notiz) plus gekennzeichnete
  Faustregeln. Zahlen aus der Quelle werden als solche benannt
  („laut <Quelle> …“).
- **Stimme:** Brand Brain + Schreibstil fließen über `agc_context` in
  jeden Schreib-Auftrag (wie Content-Engine und KI-Redaktion).
- **Gates:** Tags laufen durch das kanonische Register
  (`ki_shared.build_frontmatter`), der Workflow fährt nach dem Schreiben
  das Taxonomie-Gate wie die KI-Redaktion. Die Content-Engine hebelt zu
  kurze Entwürfe beim nächsten Lauf nach (length_policy).
- **Kosten: 0 €** – Groq (gpt-oss-120b, Whisper groß-turbo) und Gemini
  im Gratis-Tier, Transkripte key-los, Extraktion lokal
  (trafilatura/pypdf/feedparser/youtube-transcript-api).
- **Fallbacks:** Ohne Keys und ohne optionale Bibliotheken läuft die
  Pipeline im Offline-/Heuristik-Modus weiter – kein Lauf geht verloren.

## 7. Watchlist pflegen

`data/poppy/quellen.yaml`: Quelle ergänzen, `aktiv: true`, fertig.
YouTube-@Handle-URLs werden zur Channel-ID aufgelöst (robuster in CI:
direkt `https://www.youtube.com/feeds/videos.xml?channel_id=UC…`
eintragen). `max_neu` begrenzt neue Karten pro Quelle und Lauf;
Duplikate (gleiche Quell-URL) überspringt die Werkbank automatisch.

## 8. Selbsttest & Pflege

```bash
npm run test:poppy      # Selbsttests + 17 Unit-Tests (fail-closed, Exit 2)
```

Bei Protokoll-Änderungen an den Karten (Schema in `poppy_lib.neue_karte`)
die Tests in `scripts/tests/test_poppy_werkbank.py` miterweitern – sie
frieren die Kernversprechen ein: Dedupe, Pillar fail-closed, draft-only,
Promote-Sperre für Gerüste, Social-Zeichengrenzen.
