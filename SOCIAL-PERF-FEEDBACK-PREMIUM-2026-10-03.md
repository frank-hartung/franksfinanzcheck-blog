# 📈 SOCIAL-PERF-FEEDBACK – Rückkanal-Rollout 03.10.2026

> Anleitung: `docs/ANLEITUNG-SOCIAL-PERF-FEEDBACK.md` · Cockpit: `SOCIAL-PERF-REPORT.md`

## Auftrag

> „Was fehlt meinem Blog, um die Social-Media-Automatisierung weltweit auf
> das absolute Highend-Level zu pushen und meine deutsche Konkurrenz um
> Längen voraus zu sein?“

Audit-Ergebnis vorab: Architektur (10 Kanal-Adapter, Gate, Schaltwerk,
Shorts-Schmiede) ist bereits Agentur-Niveau. Der reale Engpass war zweifach:
(1) 9 von 10 Kanälen ohne Zugangsdaten – das ist Franks Aufgabe, kein Code
(siehe `docs/RUNBUCH-SOCIAL-SECRETS.md`), (2) der Planer lernte aus echtem
Engagement **nicht** – das ist Code, und genau das wurde hier gebaut.

## Was gebaut wurde

| Baustein | Datei | Zweck |
|---|---|---|
| Engine | `scripts/social_perf_feedback.py` | Liest Sendehistorie + Kennzahlen, bewertet Winkel/Themenwelt, schreibt Gewichte |
| Planer-Hook | `scripts/social_planner.py` (`pick_angle`, `_candidates`, `_not_in_cooldown`, `build_plan`) | 80/20-Bandit für Winkel, Cooldown-Faktor je Themenwelt – **opt-in, rückwärtskompatibel** |
| Rückkanal-Daten | `data/social/performance.yaml`, `data/social/engagement_cache.json`, `data/social/performance_history.jsonl` | Gewichte, Rohdaten-Cache, Audit-Trail |
| Takt | `.github/workflows/social-perf-feedback.yml` | täglich 04:10 UTC, vor dem ersten Autopilot-Slot |
| Doku | `docs/ANLEITUNG-SOCIAL-PERF-FEEDBACK.md` | Bedienung, Signal-Gewichte, Erweiterung auf neue Kanäle |
| Tests | `scripts/tests/test_social_perf_feedback.py` | 17 Unit-Tests (Scoring, Mindeststichprobe, Cooldown-Grenzen, Rückwärtskompatibilität, Bandit-Verteilung) |

## Leitplanken (geprüft, nicht nur behauptet)

- **Rückwärtskompatibel per Konstruktion.** `pick_angle(..., angle_weights=None)`
  und `build_plan(..., performance=None)` verhalten sich ohne Rückkanal-Daten
  exakt wie vor diesem Umbau – bewiesen durch `test_pick_angle_ohne_gewichte_ist_hash_basiert`
  und `test_leerer_rueckkanal_aendert_plan_nicht_kaputt`. Alle 39 bereits
  bestehenden Autopilot-Tests laufen unverändert grün.
- **Kein echter Zufall.** Der Bandit wählt deterministisch über einen
  SHA1-Seed aus (Kanal, Artikel, Tag, Sequenz) – der Plan bleibt reproduzierbar
  (`test_determinismus` bleibt grün).
- **Mindeststichprobe gegen Overfitting.** Unter drei Posts bleibt ein
  Winkel/eine Themenwelt neutral (Gewicht 1.0), selbst bei extremen Rohwerten.
- **Sicherheits-Minimum beim Cooldown.** Auch ein extremer Faktor darf die
  Sperrfrist nie unter 14 Tage drücken (Spam-Bremse bleibt intakt).
- **Fail-safe.** Fehlende/leere Kennzahlen sind kein Fehler; der Report meldet
  „noch keine Daten“ statt abzustürzen.

## Verifikation

```
python3 scripts/social_perf_feedback.py --selftest        ✅ bestanden
python3 -m unittest scripts.tests.test_social_perf_feedback  ✅ 17 Tests, 0 Fehler
python3 -m unittest scripts.tests.test_social_autopilot       ✅ 39 Tests, 0 Fehler (unverändert)
python3 scripts/social_studio.py --selftest                 ✅ bestanden
python3 scripts/schaltwerk.py --selftest                    ✅ bestanden
python3 scripts/social_perf_feedback.py                     ✅ realer Lauf, performance.yaml + Report geschrieben
```

## Ehrlicher Befund aus dem ersten echten Lauf

Von 41 Sendungen in `data/social/state.yaml` tragen 11 eine echte
Mastodon-Status-ID (der Rest ist migrierter Altbestand ohne ID). Die Live-Abfrage
aller 11 Toots (`mastodon.social/api/v1/statuses/<id>`, 03.10.2026) zeigt:
**Favoriten, Reblogs und Antworten stehen durchweg bei 0 – das Konto hat 0 Follower.**
Das ist kein Fehler des Rückkanals, sondern der nächste ehrliche Befund des
Highend-Audits: Die Lernschleife ist jetzt da, aber sie braucht echtes Publikum,
um zu wirken. Nächster Hebel dafür bleibt unverändert `docs/RUNBUCH-SOCIAL-SECRETS.md`
(weitere Kanäle scharf schalten) plus aktives Fediverse-Wachstum für den
bestehenden Mastodon-Account (Hashtag-Communities, gezieltes Folgen/Interagieren).

## Nächste Schritte für Frank

1. `docs/RUNBUCH-SOCIAL-SECRETS.md` abarbeiten – jeder neue Kanal liefert dem
   Rückkanal sofort mehr Lernsignal.
2. Mastodon-Reichweite aktiv aufbauen (Follower, Hashtags, Verzeichnisse) –
   ohne Publikum bleibt jeder Rückkanal auf Nullwerten stehen.
3. Cockpit-Konsolidierung (`AUTOMATISIERUNGS-FAHRPLAN-2026-09-29.md`, Punkt 3d)
   bleibt der nächste offene Punkt der Highend-Roadmap.
