# 🚦 ANLEITUNG: COCKPIT (eine Ampel-Seite statt 70+ Status-Dateien)

> **Kurzfassung:** Jede neue Automation im Blog hat sich bisher eine eigene
> `*-STATUS.md`/`*-REPORT.md` gegönnt – über 70 Dateien im Projekt-Root.
> Richtig und wichtig für Nachvollziehbarkeit, aber niemand liest morgens
> 70 Dateien, um eine Frage zu beantworten: **„Brennt irgendwo was?“**
> `COCKPIT.md` beantwortet genau diese Frage: sechs Bereiche, je eine Ampel,
> ein Satz Begründung, ein Link zur Tiefe, wenn's brennt.
>
> **Dein Aufwand: eine Gewohnheit.** Morgens (oder abends) eine Datei öffnen:
> `COCKPIT.md` im Repo-Root. Rot → nachsehen. Gelb → auf dem Schirm behalten.
> Grün/Grau → weiterarbeiten. Der Workflow läuft täglich automatisch und
> aktualisiert die Datei; bei **Gesamtbild Rot** bekommst du zusätzlich einen
> Telegram-Hinweis (wenn `TELEGRAM_BOT_TOKEN`/`TELEGRAM_CHAT_ID` gesetzt sind –
> sonst einfach kein Alarm, kein Fehler).

---

## 1 · Was hier passiert

`scripts/cockpit.py` **misst nichts neu** und **ruft kein Netz auf**. Es liest
ausschließlich Dateien, die andere Wachen im Repo bereits schreiben, und
fasst sie zu sechs Bereichen zusammen:

| Bereich | Liest aus | Worum geht's |
|---|---|---|
| **Content-Pipeline** | `data/governance_status.json` (Lesbarkeit/Decay/Scorecard/Automation), `data/reserve-readiness.json` | Ist der Artikel-Vorrat gesund, Texte lesbar, Automation fehlerfrei? |
| **SEO & Technik** | `data/governance_status.json` (CWV/Build/Live-Policy/Umami) | Lädt die Seite schnell, baut sie fehlerfrei, ist die Live-Policy sauber? |
| **Affiliate & Umsatz** | `data/governance_status.json` (Click-Chain/Revenue-Funnel/Awin/Clicks/Pinperf) | Ist die Klick-Kette lückenlos messbar, ist die Umsatz-Pipeline intakt? |
| **Secrets & Zugänge** | `data/governance_status.json` (Secrets), `data/secrets_state.json` | Welche API-Zugänge sind live geprüft, welche abgelehnt/tot? |
| **Social-Automation** | `data/social/state.yaml`, `data/social/channels.yaml`, `data/secrets_state.json` | Wie viele der 10 Kanäle sind live vs. Standby vs. tot, wann der letzte erfolgreiche Post? |
| **Newsletter** | `data/newsletter_journal.jsonl`, `data/newsletter_state.json` | Ist zuletzt echt (nicht nur Test) versendet worden, wie groß ist der Rückstand? |

**Ampel-Bedeutung (überall gleich):**

- 🔴 **Rot** – etwas blockiert Umsatz/Sichtbarkeit/Vertrauen, Handeln sinnvoll.
- 🟡 **Gelb** – Rückstand oder ein Einzeldefekt, aber nicht akut.
- 🟢 **Grün** – im Rahmen der Erwartung.
- ⚪ **Grau** – (noch) keine Daten oder bewusster Standby (z. B. ein Social-Kanal
  ohne Token läuft laut `data/social/channels.yaml` planmäßig im Standby –
  das ist **kein Fehler**, siehe `docs/RUNBUCH-SOCIAL-SECRETS.md`).

Das **Gesamtbild** oben in `COCKPIT.md` ist die schlechteste Einzelampel
(Grau zählt dabei nicht als „schlecht“ – ein Blog ohne Umami-Daten ist nicht
kaputt, er hat nur noch keine Daten).

**Workflow:** `.github/workflows/cockpit.yml` – täglich 20:10 UTC (nachdem die
wichtigsten Tages-Erzeuger schon gelaufen sind), zusätzlich manuell startbar
über „Run workflow“ in den GitHub Actions.

---

## 2 · Was NICHT im Cockpit steht (bewusst)

- **Keine neuen Messungen.** Jede Zahl kommt aus einer bestehenden Wache.
  Ist eine Quelldatei veraltet, ist auch das Cockpit veraltet – das Cockpit
  repariert keine kaputte Messung, es zeigt sie nur.
- **Kein Ersatz für die Einzel-Reports.** `SOCIAL-PERF-REPORT.md`,
  `AFFILIATE-INTEGRITY-REPORT.md`, `PRODUKTIONS-STATUS.md` & Co. bleiben
  bestehen – das sind die Archive/Beweisketten. Jeder Cockpit-Bereich verlinkt
  unten auf seine Quellen, damit du bei Rot/Gelb direkt weiterklicken kannst,
  statt zu raten.
- **Keine Fein-Granularität.** Dutzende Einzelprüfungen aus
  `data/governance_status.json` (z. B. 16 einzelne „steps“) werden zu sechs
  Bereichen zusammengefasst. Wer die Einzelheit braucht, öffnet die
  Quelldatei – das Cockpit ist der Index, nicht das Archiv.

---

## 3 · Ehrlicher Befund (Stand 03.10.2026, erster Lauf)

Das Cockpit zeigt den Blog so, wie er wirklich dasteht – auch unbequem:

- 🔴 **Content-Pipeline:** 3 Artikel unter der Lesbarkeits-Schwelle (Flesch).
- 🟢 **SEO & Technik:** Kernwerte in Ordnung, Umami-Daten noch nicht importiert.
- 🟡 **Affiliate & Umsatz:** Klick-Kette an zwei Zielseiten (`/go/strom/`,
  `/go/dsl/`) ohne vollständiges Tracking-Attribut.
- 🔴 **Secrets & Zugänge:** Pinterest-Token abgelehnt, Re-Auth nötig
  (`docs/PINTEREST-TOKEN-RUNBOOK.md`).
- 🟢 **Social-Automation:** 1 von 10 Kanälen live (Mastodon), 9 im Standby
  ohne Zugangsdaten – siehe `docs/RUNBUCH-SOCIAL-SECRETS.md`.
- 🟡 **Newsletter:** noch kein echter Listenversand protokolliert (nur Tests),
  5 Artikel warten, der älteste seit 6 Tagen.

→ **Gesamtbild: 🔴 Rot.** Das ist kein Grund zur Panik, sondern genau der
Zweck des Cockpits: Statt in 70 Dateien zu suchen, weißt du in 10 Sekunden,
womit du anfängst (hier: Lesbarkeit der drei Artikel + Pinterest-Re-Auth).

---

## 4 · Selbst nachsehen / testen

```bash
python3 scripts/cockpit.py --selftest   # eingefrorene Regressionsfälle
python3 scripts/cockpit.py              # schreibt COCKPIT.md + data/cockpit_status.json
python3 scripts/cockpit.py --print      # zusätzlich auf stdout
python3 -m unittest scripts.tests.test_cockpit -v
```

`data/cockpit_status.json` ist die maschinenlesbare Fassung (für den
Telegram-Alarm und für andere Wachen, die mitlesen wollen – z. B. könnte
`scripts/bot_watchdog.py` künftig das Gesamtbild statt einzelner Dateien
abfragen).

---

## 5 · Wenn ein Bereich dauerhaft falsch liegt

Das Cockpit bildet nur ab, was seine Quellen sagen. Wirkt eine Ampel falsch:

1. Erst die **Quelldatei** prüfen (steht unter „Quellen“ in `COCKPIT.md`),
   nicht `scripts/cockpit.py` – meist liegt es an der Quelle, nicht am Index.
2. Schwellenwerte (z. B. „Rot ab > 5 Tagen ohne echten Newsletter-Versand“,
   „Rot ab > 120 h ohne erfolgreichen Social-Post“) stehen direkt in den
   `bucket_*`-Funktionen in `scripts/cockpit.py` – bewusst einfach gehalten
   und mit Kommentaren versehen, damit sie sich leicht anpassen lassen.
3. Neue Bereiche (z. B. „Video/Shorts“, sobald `scripts/social_video.py`
   productive Daten schreibt) werden als weitere `bucket_*`-Funktion ergänzt
   und in `BUCKET_ORDER` eingetragen – das Muster ist bewusst repetitiv
   gehalten, damit das einfach bleibt.
