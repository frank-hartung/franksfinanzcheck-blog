# 🚦 COCKPIT – Rollout 03.10.2026

> Anleitung: `docs/ANLEITUNG-COCKPIT.md` · Die Seite selbst: `COCKPIT.md`

## Auftrag

Fortsetzung des Audits „Social-Media-Automatisierung auf Highend-Level“
(`AUTOMATISIERUNGS-FAHRPLAN-2026-09-29.md`). Nach dem Rückkanal
(`scripts/social_perf_feedback.py`, siehe
`SOCIAL-PERF-FEEDBACK-PREMIUM-2026-10-03.md`) folgte Punkt 2:

> „Als Nächstes das Cockpit“ – über 70 `*-STATUS.md`/`*-REPORT.md`-Dateien im
> Projekt-Root machen es unmöglich, morgens in 10 Sekunden zu sehen, ob
> irgendwo etwas brennt.

## Was gebaut wurde

| Baustein | Datei | Zweck |
|---|---|---|
| Aggregator | `scripts/cockpit.py` | Liest 7 bestehende Zustandsdateien, fasst sie zu 6 Ampel-Bereichen zusammen |
| Ausgabe (Mensch) | `COCKPIT.md` | Eine Seite: Gesamtbild + Tabelle + Details + Quellenverweise |
| Ausgabe (Maschine) | `data/cockpit_status.json` | Für Telegram-Alarm und andere Wachen, die mitlesen wollen |
| Takt | `.github/workflows/cockpit.yml` | täglich 20:10 UTC (nach den Tages-Erzeugern), manuell startbar |
| Alarm | dieselbe Workflow-Datei, Schritt „Telegram-Alarm“ | nur bei Gesamtbild Rot, fail-safe ohne Secrets |
| Doku | `docs/ANLEITUNG-COCKPIT.md` | Bedienung, Ampel-Bedeutung, Erweiterung um neue Bereiche |
| Tests | `scripts/tests/test_cockpit.py` | 35 Unit-Tests je Bereich + Aggregation + Rendering |

## Design-Entscheidung: nur spiegeln, nie neu messen

Das Cockpit erzeugt **keine** neuen Messdaten und ruft **kein** Netz auf. Es
liest ausschließlich bereits von anderen Wachen geschriebene Zustandsdateien:

- `data/governance_status.json` (Content/SEO/Build/Affiliate/Secrets –
  geschrieben von `governance_contract.py`/`governance_gate.py`/
  `deploy_drift_guard.py`)
- `data/reserve-readiness.json` (Artikel-Vorrat, `bot_watchdog.py`)
- `data/secrets_state.json` (Live-Check je Zugang)
- `data/social/channels.yaml` + `data/social/state.yaml` (Kanal-Konfiguration
  + Post-Historie)
- `data/newsletter_journal.jsonl` + `data/newsletter_state.json`
  (echte Versand-Ereignisse + Warteschlange)

Das vermeidet zwei Fehler: (1) Prüflogik doppelt zu pflegen (Drift-Risiko,
wenn Cockpit und Original-Wache unterschiedlich urteilen), (2) neue
Netzzugriffe/Kosten für eine reine Übersichtsseite.

## Leitplanken (geprüft, nicht nur behauptet)

- **Standby ≠ Fehler, auch im Cockpit.** Ein Social-Kanal ohne Token ist
  ⚪ Standby, kein 🔴 Rot – getestet in
  `test_keine_kanaele_konfiguriert_ist_grau_nicht_rot` und
  `test_info_only_bleibt_gruen`.
- **Fail-safe bei fehlenden/kaputten Quelldateien.** `_load_json`/`_load_yaml`/
  `_load_jsonl` liefern bei Fehlern ein leeres `{}`/`[]` zurück statt
  abzustürzen – das Cockpit zeigt dann ⚪ „keine Daten“ statt eines
  Tracebacks. Getestet in `test_fehlende_governance_bricht_nicht`.
- **Gesamtbild = schlechteste Einzelampel, Grau zählt nicht als schlecht.**
  Getestet in `test_alles_grau_ist_gesamt_grau` und
  `test_gesamtbild_ist_schlechteste_einzelampel`.
- **„Echter“ Newsletter-Versand ≠ Testmail/Bestätigung.** Der Newsletter-
  Bereich filtert `test-*`/`selftest`/`bestaetigung-*`/`abmelde-*` explizit
  heraus, damit ein Testlauf keinen grünen Schein erzeugt – getestet in
  `test_testmails_zaehlen_nicht_als_echter_versand`.
- **Alarm nur bei Rot, fail-safe ohne Telegram-Secrets.** Übernimmt das
  bereits produktive Muster aus `.github/workflows/produktions-wache.yml`
  (`if: env.LEVEL == 'rot'`, Abbruch mit Exit 0, wenn Token/Chat-ID fehlen).

## Verifikation

```
python3 scripts/cockpit.py --selftest                 ✅ 19 eingefrorene Fälle
python3 -m unittest scripts.tests.test_cockpit -v       ✅ 35 Tests, 0 Fehler
python3 -m unittest discover -s scripts/tests           ✅ 1432 Tests, 0 Fehler (22 übersprungen, unverändert)
python3 scripts/cockpit.py                              ✅ realer Lauf, COCKPIT.md + data/cockpit_status.json geschrieben
python3 -c "import yaml; yaml.safe_load(open('.github/workflows/cockpit.yml'))"  ✅ gültiges YAML
```

## Ehrlicher Befund aus dem ersten echten Lauf (03.10.2026)

Das Cockpit zeigt den Blog so, wie er wirklich dasteht:

| Bereich | Ampel | Kurzbefund |
|---|---|---|
| Content-Pipeline | 🔴 | 3 Artikel unter Lesbarkeits-Schwelle (Flesch), Artikel-Reserve 6/6 voll |
| SEO & Technik | 🟢 | Kernwerte in Ordnung, Umami-Daten noch nicht importiert (Standby) |
| Affiliate & Umsatz | 🟡 | Klick-Kette an `/go/strom/` und `/go/dsl/` ohne vollständiges Tracking |
| Secrets & Zugänge | 🔴 | Pinterest-Token abgelehnt, Re-Auth nötig |
| Social-Automation | 🟢 | 1/10 Kanäle live (Mastodon), 9 im geplanten Standby |
| Newsletter | 🟡 | noch kein echter Listenversand protokolliert, 5 Artikel warten (bis 6 Tage) |

→ **Gesamtbild 🔴 Rot** – nicht wegen eines einzelnen Totalausfalls, sondern
weil zwei unabhängige Bereiche (Lesbarkeit, Pinterest-Token) echten
Handlungsbedarf haben. Genau das ist der Zweck: Statt in 70 Dateien zu
suchen, steht die Prioritätenliste jetzt in einer.

## Nicht gemacht (bewusste Scope-Grenze)

- Kein Ersatz der Einzel-Reports – sie bleiben Archiv/Beweiskette, das
  Cockpit ist der Index.
- Keine automatische Reparatur – das Cockpit zeigt nur an, ändert nichts.
- Kein neuer Alarmkanal – nutzt den bestehenden Telegram-Weg.
