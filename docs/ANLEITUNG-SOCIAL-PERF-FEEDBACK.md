# 📈 ANLEITUNG: Social-Perf-Feedback (der Rückkanal)

> **Kurzfassung:** Der Social-Autopilot (`docs/ANLEITUNG-SOCIAL-AUTOPILOT.md`)
> plante bisher rein nach Regeln – ohne zu wissen, was tatsächlich funktioniert
> hat. Dieser Baustein schließt den Kreis: Er liest echtes Engagement je Kanal,
> bewertet Winkel und Themenwelten, und der Planer gewichtet seine Auswahl
> danach – ein kleiner, deterministischer Multi-Armed-Bandit, kein echter
> Zufall, 0 € Kosten.
>
> **Dein Aufwand: keiner.** Der Workflow läuft täglich um 04:10 UTC, bevor der
> Autopilot den Tagesplan baut. Ohne Daten (Kanal im Standby oder frisch aktiv)
> verhält sich alles neutral – reine Exploration, exakt wie vorher.

---

## 1 · Was hier automatisch passiert

| Schritt | Datei | Was passiert |
|---|---|---|
| 1 Lesen | `data/social/state.yaml` | Erfolgreiche Posts der letzten 60 Tage je Kanal/Winkel/Artikel |
| 2 Messen | `scripts/social_perf_feedback.py --fetch` | Aktuelle Kennzahlen nachladen (Mastodon: Favoriten/Reblogs/Antworten, öffentlich, **kein Token nötig**) → `data/social/engagement_cache.json` |
| 3 Bewerten | – | Score je Winkel und je Themenwelt, mit Bayes'scher Glättung gegen den Kanal-Durchschnitt (ein Ausreißer kippt nichts) |
| 4 Schreiben | `data/social/performance.yaml` | Winkel-Gewichte + Cooldown-Faktor je Themenwelt – **das liest `social_planner.py` beim nächsten Plan-Lauf automatisch** |
| 5 Berichten | `SOCIAL-PERF-REPORT.md` | Cockpit: Top-/Flop-Winkel, Top-/Flop-Themenwelt je Kanal |

**Workflow:** `.github/workflows/social-perf-feedback.yml` – täglich 04:10 UTC
(vor dem ersten Autopilot-Slot um 05:20 UTC), zusätzlich manuell startbar.

---

## 2 · Was die Engine aus den Daten macht

1. **Winkel-Bandit (80/20).** Der Planer wählt für einen Artikel/Kanal den
   bisherigen Sieger-Winkel in **80 % der Fälle**, probiert in **20 %** bewusst
   einen anderen. So lernt die Engine weiter dazu, statt sich festzufahren,
   wenn sich Geschmack oder Algorithmus ändern. Die Auswahl bleibt
   **deterministisch** (Hash-Seed, kein `random`) – der Plan ist reproduzierbar.
2. **Cooldown nach Erfolg.** Themenwelten mit überdurchschnittlichem Score
   dürfen bis zu **40 % früher** wieder dran sein (Evergreen-Recycling); Flops
   bis zu **40 % später**. Ein Sicherheits-Minimum von 14 Tagen verhindert,
   dass das die Spam-Bremse (`recycle_cooldown_days`) aushebelt.
3. **Mindeststichprobe.** Unter drei gemessenen Posts bleibt ein Winkel/eine
   Themenwelt bei Gewicht `1.0` (neutral) – ein einzelner Zufallstreffer darf
   die Planung nicht verbiegen.
4. **Ohne Daten = Exploration.** Kanäle ohne Historie (Standby oder frisch
   aktiv) bekommen keine Vorab-Meinung aufgezwungen.

---

## 3 · Warum die Signal-Gewichtung so ist, wie sie ist

| Signal | Gewicht | Warum |
|---|---|---|
| Reblog/Share | 1,8 | Verteilt den Post außerhalb des eigenen Publikums – das eigentliche Ziel von organischem Social |
| Antwort/Kommentar | 1,3 | Echte Interaktion, aber selten |
| Favorit/Like | 1,0 | Häufigstes, aber schwächstes Signal |

Reine Reichweite (Impressionen) fließt bewusst **nicht** ein – dafür fehlt bei
den meisten Fediverse-/Social-APIs eine verlässliche, kostenlose Quelle. Score
`1.0` heißt immer „Kanal-Durchschnitt"; das ist relativ, nicht absolut, und
bleibt damit auch bei kleinen Reichweiten aussagekräftig.

---

## 4 · Neue Kanäle anschließen

Sobald ein weiterer Kanal (Bluesky, LinkedIn, …) Zugangsdaten bekommt und
sendet, reicht **ein** Eintrag in `METRIC_FETCHERS` in
`scripts/social_perf_feedback.py` – der Rest der Maschine (Scoring,
Gewichtung, Report, Planer-Integration) ist bereits kanal-generisch:

```python
METRIC_FETCHERS["bluesky"] = fetch_bluesky  # neue Funktion ergänzen
```

Bis dahin taucht der Kanal im Report einfach als „noch keine Daten" auf –
kein Fehler, kein Hindernis für den laufenden Betrieb.

---

## 5 · Lauf von Hand

```bash
python3 scripts/social_perf_feedback.py               # aus dem Cache, kein Netz
python3 scripts/social_perf_feedback.py --fetch        # + frische Kennzahlen
python3 scripts/social_perf_feedback.py --dry-run       # nur anzeigen, nichts schreiben
python3 scripts/social_perf_feedback.py --selftest      # eingefrorene Testfälle
```

Tests: `python3 -m unittest scripts.tests.test_social_perf_feedback`

---

## 6 · Ehrlicher Ausgangsbefund (03.10.2026)

Der erste echte Lauf zeigt zugleich die nächste Baustelle: Das Mastodon-Konto
hat **0 Follower**, entsprechend liegen alle gemessenen Reaktionen bislang bei
Null. Das ist kein Fehler des Rückkanals, sondern Rohdaten – die Lernschleife
greift automatisch, sobald echtes Engagement entsteht (Reichweite aufbauen:
in Mastodon-Verzeichnissen/Hashtag-Communities sichtbar werden, Fediverse-
Accounts gezielt folgen/interagieren). Bis dahin verhält sich der Planer
korrekt neutral, statt auf Zufallsrauschen zu überfitten.
