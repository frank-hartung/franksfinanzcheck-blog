# 🚦 COCKPIT – franksfinanzcheck.de

**Stand:** 2026-11-01 23:29 UTC · generiert von `scripts/cockpit.py`

> Eine Seite statt 70+ Status-Dateien. Jeder Bereich bekommt eine Ampel und einen Satz Begründung. Wer tiefer graben will, findet die Quelle unter jedem Bereich – diese Datei archiviert nichts, sie verweist nur.

## 🔴 Gesamtbild: ROT

| Bereich | Ampel | Kurzbefund |
|---|---|---|
| Content-Pipeline | 🟡 | 1 Prüfpunkt(e) auffällig (lesbarkeit) · Artikel-Reserve knapp: 5/6 bereit – Nachschub nötig |
| SEO & Technik | 🟡 | 1 Prüfpunkt(e) auffällig (cwv) |
| Affiliate & Umsatz | 🟢 | in Ordnung (2 Kennzahl(en) noch ohne Datenlage) |
| Secrets & Zugänge | 🔴 | 1 Zugang/Zugänge abgelehnt: PINTEREST_ACCESS_TOKEN – Re-Auth nötig |
| Social-Automation | 🟢 | 1/10 Kanäle live (Mastodon) |
| Newsletter | 🔴 | noch kein echter Listenversand protokolliert (nur Tests/Bestätigungen) |

---

## Details

### Content-Pipeline — 🟡 GELB
- 1 Prüfpunkt(e) auffällig (lesbarkeit) · Artikel-Reserve knapp: 5/6 bereit – Nachschub nötig
- lesbarkeit: 2026-10-26-gastarife-vergleichen-vor-dem-herbst/index.md (Entwurf) – Flesch 51.5 < Publish-Schwelle 60
- Artikel-Reserve knapp: 5/6 bereit – Nachschub nötig

Quellen: `data/governance_status.json`, `data/reserve-readiness.json`, `PRODUKTIONS-STATUS.md`

### SEO & Technik — 🟡 GELB
- 1 Prüfpunkt(e) auffällig (cwv)
- cwv: 10 <img>-Elemente ohne width/height/style (CLS-Risiko)
- Search Console (2026-10-19): 117 von 437 bekannten URLs im Index (26.8 %), 320 nicht indexiert, 193 davon ohne Erklärung im Bestand

Quellen: `data/governance_status.json`, `data/gsc/abdeckung/befund.json`

### Affiliate & Umsatz — 🟢 GRÜN
- in Ordnung (2 Kennzahl(en) noch ohne Datenlage)

Quellen: `data/governance_status.json`, `AFFILIATE-INTEGRITY-REPORT.md`, `AFFILIATE-INTENT-REPORT.md`

### Secrets & Zugänge — 🔴 ROT
- 1 Zugang/Zugänge abgelehnt: PINTEREST_ACCESS_TOKEN – Re-Auth nötig
- geprüft & lebendig: GEMINI_API_KEY, GROQ_API_KEY, MASTODON_ACCESS_TOKEN
- abgelehnt (Re-Auth nötig): PINTEREST_ACCESS_TOKEN

Quellen: `data/governance_status.json`, `data/secrets_state.json`, `docs/PINTEREST-TOKEN-RUNBOOK.md`

### Social-Automation — 🟢 GRÜN
- 1/10 Kanäle live (Mastodon)
- 9 im Standby ohne Zugangsdaten (Bluesky, LinkedIn, X (Twitter), Threads, Facebook (Seite), Instagram, Pinterest, Telegram (Kanal), Reddit) – docs/RUNBUCH-SOCIAL-SECRETS.md
- letzter erfolgreicher Post vor 1.5 Tag(en)

Quellen: `data/social/state.yaml`, `data/social/channels.yaml`, `SOCIAL-PERF-REPORT.md`, `docs/RUNBUCH-SOCIAL-SECRETS.md`

### Newsletter — 🔴 ROT
- noch kein echter Listenversand protokolliert (nur Tests/Bestätigungen)
- 5 Artikel in der Warteschlange, ältester 8 Tag(e) alt

Quellen: `data/newsletter_journal.jsonl`, `data/newsletter_state.json`, `data/newsletter_kadenz.json`

---

_Automatisch erzeugt von `scripts/cockpit.py` – reine Aggregation bestehender Wachen, keine neuen Messdaten, kein Netzzugriff. Maschinenlesbar: `data/cockpit_status.json`. Siehe auch `docs/ANLEITUNG-COCKPIT.md`._
