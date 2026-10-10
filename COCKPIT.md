# 🚦 COCKPIT – franksfinanzcheck.de

**Stand:** 2026-10-09 23:58 UTC · generiert von `scripts/cockpit.py`

> Eine Seite statt 70+ Status-Dateien. Jeder Bereich bekommt eine Ampel und einen Satz Begründung. Wer tiefer graben will, findet die Quelle unter jedem Bereich – diese Datei archiviert nichts, sie verweist nur.

## 🔴 Gesamtbild: ROT

| Bereich | Ampel | Kurzbefund |
|---|---|---|
| Content-Pipeline | 🔴 | 1 Prüfpunkt(e) auffällig (lesbarkeit) |
| SEO & Technik | 🔴 | 1 Prüfpunkt(e) auffällig (live-policy) |
| Affiliate & Umsatz | 🟢 | in Ordnung (3 Kennzahl(en) noch ohne Datenlage) |
| Secrets & Zugänge | 🔴 | 1 Zugang/Zugänge abgelehnt: PINTEREST_ACCESS_TOKEN – Re-Auth nötig |
| Social-Automation | 🟢 | 1/10 Kanäle live (Mastodon) |
| Newsletter | 🔴 | noch kein echter Listenversand protokolliert (nur Tests/Bestätigungen) |

---

## Details

### Content-Pipeline — 🔴 ROT
- 1 Prüfpunkt(e) auffällig (lesbarkeit)
- lesbarkeit: 2026-09-30-last-minute-urlaub-so-schnappst-du-dir-das-sommer-schnaepp/index.md – Flesch 47.4 < Floor 55; 2026-10-02-weihnachten-budget-planen-ohne-schulden-durch-die-fei…
- Artikel-Reserve 6/6 bereit

Quellen: `data/governance_status.json`, `data/reserve-readiness.json`, `PRODUKTIONS-STATUS.md`

### SEO & Technik — 🔴 ROT
- 1 Prüfpunkt(e) auffällig (live-policy)
- live-policy: L2: 2 Money-URL(s) fehlen live in der Sitemap, z. B. https://franksfinanzcheck.de/posts/2026-10-05-budget-app-2026-so-beherrschst-du-deine-ausgaben-ohne-auf/ – Deploy/Ca…

Quellen: `data/governance_status.json`

### Affiliate & Umsatz — 🟢 GRÜN
- in Ordnung (3 Kennzahl(en) noch ohne Datenlage)

Quellen: `data/governance_status.json`, `AFFILIATE-INTEGRITY-REPORT.md`, `AFFILIATE-INTENT-REPORT.md`

### Secrets & Zugänge — 🔴 ROT
- 1 Zugang/Zugänge abgelehnt: PINTEREST_ACCESS_TOKEN – Re-Auth nötig
- geprüft & lebendig: GEMINI_API_KEY, GROQ_API_KEY, MASTODON_ACCESS_TOKEN
- abgelehnt (Re-Auth nötig): PINTEREST_ACCESS_TOKEN

Quellen: `data/governance_status.json`, `data/secrets_state.json`, `docs/PINTEREST-TOKEN-RUNBOOK.md`

### Social-Automation — 🟢 GRÜN
- 1/10 Kanäle live (Mastodon)
- 9 im Standby ohne Zugangsdaten (Bluesky, LinkedIn, X (Twitter), Threads, Facebook (Seite), Instagram, Pinterest, Telegram (Kanal), Reddit) – docs/RUNBUCH-SOCIAL-SECRETS.md
- letzter erfolgreicher Post vor 0.5 Tag(en)
- 3 Fehlversuch(e) in den letzten 14 Tagen

Quellen: `data/social/state.yaml`, `data/social/channels.yaml`, `SOCIAL-PERF-REPORT.md`, `docs/RUNBUCH-SOCIAL-SECRETS.md`

### Newsletter — 🔴 ROT
- noch kein echter Listenversand protokolliert (nur Tests/Bestätigungen)
- 5 Artikel in der Warteschlange, ältester 58 Tag(e) alt

Quellen: `data/newsletter_journal.jsonl`, `data/newsletter_state.json`, `data/newsletter_kadenz.json`

---

_Automatisch erzeugt von `scripts/cockpit.py` – reine Aggregation bestehender Wachen, keine neuen Messdaten, kein Netzzugriff. Maschinenlesbar: `data/cockpit_status.json`. Siehe auch `docs/ANLEITUNG-COCKPIT.md`._
