# Newsletter-Versandzeit: 07:05 → 06:30 deutscher Zeit (Di/Fr)

Stand: 25.09.2026. Im Arbeitszweig `arena/01a0d6a6-franksfinanzcheck-blog`
implementiert und getestet, noch nicht veröffentlicht.

## Entscheidung

Der planmäßige Listen-Versand rückt um 35 Minuten vor:

| | Vorher | Jetzt |
|---|---|---|
| Cron (`newsletter-daily.yml`) | `5 5 * * 2,5` (05:05 UTC) | `30 4 * * 2,5` (04:30 UTC) |
| Deutsche Zeit | 07:05 MESZ / 06:05 MEZ | **06:30 MESZ / 05:30 MEZ** |
| Kadenz-Wache (`newsletter-cadence.yml`) | `11 8 * * 2,5` (08:11 UTC) | unverändert |
| Wache-Fenster „Tag bedient“ | ab 04:00 UTC | **ab 03:30 UTC** (bleibt 1 h Gnade vor dem Soll-Termin) |

Die Wochentage (Dienstag/Freitag) und das Wochenlimit (2×/Woche) bleiben
unverändert.

## Warum

Basis: Inxmail E-Mail-Marketing-Benchmark 2026 (DACH-Raum, 4 Mrd. Mails):

- Das Zeitfenster **3–6 Uhr morgens** erzielt die höchsten Öffnungsraten
  aller Zeitfenster – im B2C 42,5 %. Der Effekt: die Mail liegt beim ersten
  Mail-Check (Handy, Frühstück, Pendelweg, ca. 6:30–8:00) oben im Postfach,
  bevor die Arbeitsmailflut eintrifft. ~80 % aller Öffnungen fallen in die
  ersten 4 Stunden nach Zustellung.
- Die Uhrzeit verschiebt Öffnungsraten um bis zu 30 Punkte, der Wochentag nur
  um 5–8 → am Tag nichts drehen, an der Uhrzeit optimieren.
- Freitags ist der Posteingang nach dem Wochenende voller: wer früh drin
  ist, verliert den ersten Check nicht an die Samstagnachhol-Flut.
- Finanz-Digest + Affiliate: morgens lesen, am selben Tag klicken.

## Geänderte Stellen (eine Wahrheit, alle Fassungen)

Kern: `scripts/newsletter_schedule.py` – `SEND_UHRZEIT = dt.time(6, 30)`
(UTC- und Winterzeit sowie `uhrzeit_zeile()` werden daraus **gerechnet**,
nicht abgeschrieben). Alles Weitere liest aus diesem Vertrag:

- `.github/workflows/newsletter-daily.yml`: Cron `30 4 * * 2,5` + Kommentare
- `.github/workflows/newsletter-cadence.yml`: Fenster-Kommentar (ab 03:30 UTC)
- `scripts/newsletter_cadence.py`: `FENSTER_START_UHRZEIT = dt.time(3, 30)`,
  Befundtext „Soll: 04:30 UTC“, Selftest-Fälle 2/3/9
- `scripts/newsletter_zustellbarkeit.py`: Hinweiszeile „nächster Di/Fr-Cron
  04:30 UTC holt sie ab“
- `data/newsletter_kadenz.json`: per `--export-site` neu generiert
  (06:30 / 05:30) – fließt über `newsletter_versandplan.html` in Anmelde-
  box, Strip und Versandplan-Kacheln
- `layouts/shortcodes/newsletter_form.html`: Fallback-Uhrzeitzeile
- `static/premium/ff-newsletter.js`: Fallback `'07:05'` → `'06:30'`
  (reale Werte kommen aus dem Snapshot; Fallback bleibt Vertragstreu)
- `content/newsletter/index.md`, `content/newsletter-bestaetigung/index.md`:
  Versandversprechen 06:30 (Winter 05:30)
- `docs/ANLEITUNG-NEWSLETTER-EIGENBETRIEB.md` (Architektur-Skizze, Schritt 8,
  Betriebs-Tabelle), `docs/ANLEITUNG-NEWSLETTER-STUDIO.md` (Schritt 6)
- `scripts/tests/test_newsletter_schedule.py` (Cron-Assertion, UTC/Winter-
  Uhrzeiten, Sommer-/Winterzeit-Fall 04:30 UTC), `scripts/tests/
  test_newsletter_cadence.py` (Befund-Solltermin, Fenstergrenze 03:29/03:31)

Nicht geändert: `hugo.toml` (enthält keine Uhrzeit → Integritätssiegel
unberührt), historische Vorfallberichte mit Datum (23./24.09.),
`data/audit/*.jsonl`, `data/spam_history.jsonl`,
`docs/PREMIUM-AUDIT-2026-09-11.md` (geschichtete Aufzeichnungen),
`newsletterPromise` in `hugo.toml` (nennt nur Tage, keine Uhrzeit).

## Verifikation

| Prüfung | Ergebnis |
|---|---|
| `python3 scripts/newsletter_schedule.py --export-site` / `--pruefen-site` | Snapshot geschrieben + Drift-frei (06:30) |
| `python3 -m unittest discover -s scripts/tests -p 'test_newsletter*.py'` | grün (Details unten) |
| `python3 scripts/newsletter_cadence.py --selftest` | grün |
| `grep -rn "05:05\|07:05\|06:05"` (aktive Dateien) | nur noch in historischen Reports/Daten |

## Testplan nach Freischaltung (keine Daten, keine Meinung)

1. 4–6 Ausgaben alt (07:05) vs. neu (06:30) im Wechsel – mit Resend kein
   Split-Versand, der Wechsel genügt bei 2×/Woche.
2. Metrik: **CTR und Affiliate-Konversion pro Ausgabe**, nicht
   Öffnungsrate (Mail-Privacy-Protection verzerrt sie).
3. Abbruchkriterium: Unterschied < 1 CTR-Punkt → 06:30 behalten (Bequem-
   lichtigkeit + Top-of-Inbox-Vorteil), kein Rückbau.
