# 📌 Pinterest-Check #822: Eine Prüfung muss die richtige Menge messen

**Datum:** 24.10.2026 · **Bezug:** Issue #822 „Pinterest-Check: Probleme
gefunden“ (Watchdog-Läufe 20.–24.10.2026, täglich Exit 1) · **Auftrag:**
„Bitte dauerhaft auf Highend-Level einer Profi-Agentur beheben.“ · **Neuer
Vertrag:** C43 · **Vorgänger:** #729 (P8, C37 – Befund ohne Schließpfad),
#390 (Report-Provenienz), #305 (Duplikate, C17)

---

## 1. Befund

Der Pinterest-Watchdog meldete fünf Tage lang **denselben einen Posten**:

```
[P10] 2026-08-12-dein-haus-sicher-schuetzen-das-neue-vorsorge-update-2026:
      Artikel-Seite ist ein Meta-Refresh-Alias – nicht direkt pinnen
```

**Er hatte recht – und der Befund war trotzdem falsch.** Der Artikel ist seit
dem 19.10.2026 nach dem Redaktions-Standard (RS1–RS3) **geparkt**
(`draft: true`, `cadence_demoted: 2026-10-19T13:09:54Z`), und seine ehemalige
URL steht seit demselben Tag in `data/weiterleitungen.yaml`:

```yaml
- {von: "/posts/2026-08-12-dein-haus-sicher-schuetzen-das-neue-vorsorge-update-2026/",
   nach: "/pillar/versicherungen/", regel: "C",
   grund: "Redaktions-Standard (RS1–RS3) hat den ehemals live Beitrag geparkt; …"}
```

Die Meta-Refresh-Seite unter `static/posts/<slug>/index.html` ist damit **die
gewollte Auslieferung**. P10 hat sie als Defekt eines Artikels gemeldet, den
es im Build gar nicht gibt. Und weil P10 – anders als P8, P4, P4b, P7 – keinen
Heiler besaß, konnte das Issue nie zugehen: Der Workflow schließt nur bei
Exit 0. Genau die Bauart, die C37/#729 zwei Wochen vorher beschrieben hat.

## 2. Die eigentliche Schwäche: drei Stellen, ein Fehler

| Stelle | Was sie sah | Warum es dauerhaft rot blieb |
|---|---|---|
| `pinterest_check.py` P10 | ein Meta-Refresh unter `/posts/<slug>/` | **falsche Menge**: `_post_slugs()` kennt Entwürfe, P10 fragte nie, ob der Slug live ist. Ein geparkter Artikel *muss* weiterleiten |
| `pinterest_check.py` P10 | derselbe Befund, jeden Tag | **kein Schließpfad**: P10 prüfte nur. Die Selbstheilung kannte P1, P4, P4b, P7, P8 – nicht P10 |
| `pinterest_link_guard.py` L1/L2 | 6 Probleme (4 Entwürfe, 2 fehlende Ziele) | **eine Wache ohne Fahrer**: Das Skript wurde von **keinem** Workflow und keinem Orchestrator aufgerufen – `grep -r "pinterest_link_guard" .github/` war am 24.10.2026 vor der Heilung leer. Es hätte den Befund unabhängig gefunden |

Dieselbe Frage – *„ist dieses Ziel noch ein Artikel?“* – wurde im Haus
viermal anders beantwortet: `_is_draft()` im Pinterest-Check,
`live_urls()` in `weiterleitungen.py`, L1/L2 im Link-Guard, P6/P7 im
Plan-Guard. Vier Antworten, kein Ort.

## 3. Der blinde Fleck, der beim Nachmessen sichtbar wurde

Nicht der Artikel war das Pinterest-Problem, sondern **der Masterplan**.
`data/pinterest_plan.yaml` trug 46 Pins – bei **7 davon** war das Ziel keine
Artikel-Seite mehr:

| Pin | Ziel | Status am 24.10.2026 | Heilung |
|---|---|---|---|
| Tag 7 | `2026-08-18-geld-sparen-im-alltag-…` | Weiterleitung Regel **B** → `2026-09-11-5-einfache-frugalismus-tricks-…` | umgeschrieben (SSOT-Nachfolger) |
| Tag 26 | dieselbe URL | Weiterleitung Regel **B** | umgeschrieben |
| Tag 35 | `2026-08-16-gas-anbieter-wechseln-…` | Weiterleitung Regel **B** → `2026-08-12-preisgarantie-gas-…` | umgeschrieben |
| Tag 15 | `2026-08-26-kfz-versicherung-…` | **Entwurf** (geparkt) | geparkt |
| Tag 33 | `2026-08-12-dein-haus-sicher-schuetzen-…` | Weiterleitung Regel **C** (Pillar) | geparkt |
| Tag 36 | `2026-08-17-privathaftpflicht-…` | **Entwurf** | geparkt |
| Tag 37 | `2026-08-18-wohngebaeudeversicherung-…` | **Entwurf** | geparkt |

Ein Pin auf eine Meta-Refresh-Seite ist für Pinterest ein schwaches Ziel: kein
Rich-Pin-Scraping auf der Zielseite, ein Umleitungsschritt nach dem Klick, und
im schlimmsten Fall ein Ziel, das nicht hält, was der Pin-Text verspricht.
Genau davor warnt P10 seit jeher („nicht direkt pinnen“) – nur prüfte niemand
den Plan.

## 4. Die zweite Quelle: der Link-Guard reproduziert es unabhängig

`python3 scripts/pinterest_link_guard.py` (LOCAL, offline) am unveränderten
Bestand:

```
Link-Guard: 76 Ziele, 6 Probleme (Modus: LOCAL)
| L1 | 2026-08-18-geld-sparen-im-alltag-…            | Pin-Ziel gibt es nicht im Repo (404 nach Deploy!) |
| L2 | 2026-08-26-kfz-versicherung-…                  | Pin zeigt auf DRAFT-Artikel (geht nicht live)     |
| L2 | 2026-08-12-dein-haus-sicher-schuetzen-…        | Pin zeigt auf DRAFT-Artikel (geht nicht live)     |
| L1 | 2026-08-16-gas-anbieter-wechseln-…             | Pin-Ziel gibt es nicht im Repo (404 nach Deploy!) |
| L2 | 2026-08-17-privathaftpflicht-…                 | Pin zeigt auf DRAFT-Artikel (geht nicht live)     |
| L2 | 2026-08-18-wohngebaeudeversicherung-…          | Pin zeigt auf DRAFT-Artikel (geht nicht live)     |
```

Sieben Pins, sechs Ziele – deckungsgleich mit der Zielwache, ohne dass eine
von der anderen wusste. Nach der Heilung: **70 Ziele, 0 Probleme**.

## 5. Was jetzt gilt (eine Quelle, ein Schließpfad, ein Fahrer)

- **EINE QUELLE.** `scripts/pinterest_ziele.py` beantwortet *„ist dieses Ziel
  noch ein Artikel?“* – über `weiterleitungen.live_urls()`, also dieselbe
  Live-Definition wie `url_wache.py` und das fail-closed
  Weiterleitungs-Gate in `deploy.yml`. Status: `artikel`, `pillar`,
  `weiterleitung`, `geparkt`, `fehlt`, `fremd`. Keine zweite Draft-Regel.
- **P10 misst die richtige Menge.** Live-Artikel müssen Inhalt liefern;
  eine geparkte URL darf weiterleiten, wenn `data/weiterleitungen.yaml` es
  erklärt – und dann nennt der Report sie ausdrücklich als
  Betriebszustand („kein Befund“ heißt nicht „nicht gemessen“, C2).
- **P10 heilt in beide Richtungen, fail-closed.** Überdeckt eine
  Weiterleitung einen **Live**-Artikel, gewinnt der Artikel: SSOT-Eintrag
  und Alias-Seite werden entfernt (chirurgisch, vor dem Schreiben
  nachgeparst; mehrdeutige Form → nichts wird angefasst, Befund bleibt).
  Eine verwaiste Alias-Seite ohne SSOT-Eintrag wird entfernt. Handgebaute
  Alias-Seiten ohne Generator-Marker bleiben Handentscheidung.
- **P14: kein Pin auf ein geparktes Ziel.** Heilung **nur über die SSOT**:
  Regeln A/B (gleichwertiger, geprüfter Live-Nachfolger) → Ziel wird
  umgeschrieben, Pin-Text bleibt unangetastet; alles andere → Park in
  `data/pinterest_plan_parked.yaml` (kein Content-Verlust, wartet auf
  seinen eigenen Artikel); Queue-Einträge werden entfernt, nie geparkt.
  Kein Ziel wird geraten, kein Pin gelöscht.
- **Die Wache hat einen Fahrer.** `pinterest_link_guard.py` läuft künftig im
  Pinterest-Watchdog – im **selben Issue** (Label `pinterest`), damit kein
  zweiter Kanal entsteht; ihr `--selftest` steht im vertraglichen Minimum
  (C6). Der Watchdog schließt nur, wenn Heiler **und** Zielwache grün sind.
- **Nachweis.** Report-Schema 5: Der Quellfingerabdruck kennt jetzt
  `data/weiterleitungen.yaml`, `url_entfallen.yaml`, Masterplan,
  Parkbecken, Queue sowie `scripts/pinterest_ziele.py` und
  `scripts/weiterleitungen.py`. Ein Schema-4-Report bezeugt diese Prüfungen
  nicht mehr.

## 6. Belege (ausgeführt am 24.10.2026)

| Prüfung | Ergebnis |
|---|---|
| `pinterest_ziele.py --check` (vorher) | 7 offen, 0 geheilt · Exit 1 |
| `pinterest_ziele.py --fix` | 3 Retargets, 4 Parks · danach **0 offen** · Exit 0 |
| `pinterest_ziele.py --check` (nachher) | 0 offen · Exit 0 |
| `pinterest_link_guard.py` | **70 Ziele, 0 Probleme** · Exit 0 |
| `pinterest_check.py --fix` | Selbsttest grün · Exit 0 (alle gemessenen Prüfungen grün) |
| P10 gegen den echten Bestand (simulierte Auslieferung: 66 Live-Seiten + `static/`) | **0 Probleme**, 1 erklärte Weiterleitung (`dein-haus-sicher-…` → `/pillar/versicherungen/`, Regel C) |
| `governance_contract.py --selftest` | ✅ bestanden (C1–C43, vier Kunstbefunde zu C43) |
| `governance_contract.py` (voll) | 🔒 alle 41 Regeln erfüllt |
| `unittest test_pinterest_ziele test_pinterest_check` | 44 Tests, OK |
| Masterplan nachher | 42 Pins aktiv (vorher 46), 29 im Parkbecken (vorher 25) |

## 7. Dateien

- neu: `scripts/pinterest_ziele.py`, `scripts/tests/test_pinterest_ziele.py`
- geändert: `scripts/pinterest_check.py` (P10 neu, P14 neu, Report-Schema 5,
  Fingerabdruck, Selbsttest), `scripts/governance_contract.py` (C43 samt
  Sabotage-Fällen), `scripts/pinterest_link_guard.py` (`--selftest` fährt nur
  den Selbsttest), `.github/workflows/pinterest-watchdog.yml` (Zielwache als
  Schritt, Issue-Bedingungen), `scripts/tests/test_pinterest_check.py`,
  `data/pinterest_plan.yaml`, `data/pinterest_plan_parked.yaml`,
  `PINTEREST-REPORT.md`, `docs/PINTEREST-SPIELBUCH.md`,
  `docs/GOVERNANCE-KONTRAKT.md`, `CLAUDE.md`.
- **Nicht angefasst:** das Audit-Ledger (`data/audit/`). Die Belege dieses
  Berichts stammen aus Sandkasten-Läufen; ein Beweis-Ledger gehört dem Lauf,
  der ihn produzierte (C27), nicht einem nachträglichen Commit.

## 8. Rest-Risiken und ehrliche Grenzen

- **Kein Hugo im Sandkasten.** Die HTML-Prüfungen (P3/P6/P7/P10/P12) sind
  lokal **nicht** über den echten Build gemessen; der Report sagt das (C2).
  P10 wurde ersatzweise gegen eine aus `static/` abgeleitete Auslieferung
  (66 Live-Seiten + Alias-Seiten) geprüft **und** in fünf eingefrorenen
  Testfällen. Der nächste Watchdog-Lauf misst den echten Build und schließt
  #822.
- **Plan-Guard P2 ist nach der Heilung rot** („Board ‚Versicherungen clever
  wechseln & sparen‘ nur 1 Pin (<3)“). Das ist keine neue Panne, sondern die
  ehrliche Folge: Vier Pins dieses Boards hatten kein Ziel. Die Lösung ist
  Redaktion (neue **live** Versicherungsartikel), nicht ein Pin auf eine tote
  URL – ein Ziel zu erfinden wäre die Ursache, nicht die Heilung. Der
  Plan-Guard läuft in keinem Workflow; diese Lücke ist **nicht** Teil von
  #822 und wird hier nicht als geheilt behauptet.
- **Bereits gepinnte Pins.** Ein Pin, der vor dem 24.10.2026 mit einer
  Alias-URL gesendet wurde, behält sie auf Pinterest. Ein `pin_id`-Ledger
  für nachträgliche Ziel-Updates existiert im Repo nicht; der nächste
  Repin/Refresh zieht die geheilte Quelle. `data/pin_queue.yaml` ist
  derzeit leer.
- **Der Masterplan ist eine Blaupause, kein Versender.** Die Engine postet
  aus dem Live-Bestand (`draft: false`), nicht aus dem Plan. Der Plan speist
  Pin-Texte (`pinterest_pin_text_sync`), den CSV-Export und die Redaktion –
  deshalb war die Heilung dort trotzdem Pflicht, aber sie ersetzt keine
  Aussage über bereits gesendete Pins.
- **Bewusste Grenze der Automatik:** Ein *Mehrzeiler* in
  `data/weiterleitungen.yaml` oder eine handgebaute Alias-Seite wird nie
  automatisch entfernt (fail-closed, Befund für Menschen). Das ist Absicht:
  Ein Heiler, der Format raten muss, ist die nächste halbe Fassung (C39).
- **Test-Suite-Baseline:** Die volle Suite (`unittest discover`) läuft mit
  3597 Tests; die 12 Fehler (`test_faktenfrische_763` 10×,
  `test_newsletter_digest` 2×) treten im frischen Worktree des Basis-Commits
  `7b93dde` identisch auf (dort 10 bzw. 2) – sie gehören nicht zu diesem PR
  und werden hier **nicht** als geheilt behauptet. Die 44 Tests der neuen
  Ziel-Regel sind grün.

*Dieser Bericht ist der Nachweis zu #822; er wird mit dem PR geschlossen.*
