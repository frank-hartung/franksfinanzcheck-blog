# Kadenz-Horizont #1107 – Dauerheilung (06.11.2026)

**Auftrag:** Issue #1107 „⏰ Frist: Kadenz-Horizont – projiziert 26.11./31.12.2026 rot, auch am Limit (Frist 20.11.2026)“. Option C gewählt, dauerhaft auf Highend-Niveau einer Profi-Agentur.

**Entscheidungen des Herausgebers (06.11.2026):**
1. Sockel `max_artikel_pro_lauf`: **12 → 4**.
2. Ausfalltoleranz: **7 Tage**. Der Hebel ist der **Vorlauf** (`planung.vorlauf_tage`: **7 → 14**), nicht das Limit.
3. Änderung ins Review, erst nach grünen Checks mergen.

**Ergebnis in einem Satz:** Die rote Projektion war ein Messfehler (eingefrorener Prüfstand statt der Arbeit des Bots bis zum Stichtag). Korrigiert ist die Messung. Der Sockel 4 trägt den Normalbetrieb und alle 52 Montage. Die 7-Tage-Ausfalltoleranz trägt der Vorlauf 14, gemessen mit der echten Automatik.

---

## 1. Befund

| Stichtag | Eingefrorener Stand (alt) | Trajektorie ab heute (neu) |
|---|---|---|
| 26.11.2026, Budget 16 | 30 überfällig, 24 gerissen → **rot** | 0 / 0 → **grün** |
| 31.12.2026, Budget 16 | 104 überfällig, 2 gerissen → **rot** | 0 / 0 → **grün** |

Die Projektion unterstellte, der Bot prüfe bis zum Stichtag nichts. Die Trajektorie nutzt dieselbe EDF-Auswahl wie `faktenfrische.py` (`edf_schluessel` plus Vorlauf-Kandidaten mit `restlaufzeit <= vorlauf`).

## 2. Korrektur im Code

Datei `scripts/faktenfrische_kapazitaet.py`:

- `simuliere`: letzter Prüftag je Seite, Tagesschnappschüsse zu **Tagesbeginn**. Ein Schnappschuss nach der Verarbeitung hätte den Tagesplatz beim Restart doppelt gezählt (gefunden durch ST13b).
- `bestand_trajektorie(artikel, cfg, budget, laeufe, basis, ziele)`: Bestand an jedem Zieltag, wie der Bot ihn ab `basis` hinterlässt.
- `plan`, `empfohlenes_budget`, `spitzenlast_stichtag`, `spitze_zahlen`: Parameter `basis=`. Ohne `basis` gilt das bisherige Verhalten.
- `main`: `basis = heute`. Ein Ausgangspunkt nach dem Stichtag wird abgewiesen (fail-closed).
- Keine Gate-Lockerung: Urteile und Reserve-Regel unverändert.

## 3. Messungen

### 3a) Bündel-Boden (Kalender-Sweep, 52 Montage, Trajektorie ab heute)

| Sockel | Montage rot |
|---|---|
| 1 oder 2 | 52 / 52 |
| 3 | 12 / 52 |
| **4** | **0 / 52** |
| 12 | 0 / 52 |

Der Normalbetrieb braucht 2,82 Prüfungen/Tag (Deckung 142 % bei Sockel 4, Mindest 110 %).

### 3b) Ausfalltoleranz mit der echten Automatik

Jeder Lauftag bekommt das Budget aus `empfohlenes_budget` (Sockel bis Limit). Ein 7-Tage-Ausfall, 46 Starttage (0–45). Verletzung = zwischen zwei Prüfterminen liegt mehr als das Intervall.

| Konfiguration | Starttage mit Verletzung | Max. Verletzungen je Start |
|---|---|---|
| Sockel 12, Vorlauf 7 (vor dieser Entscheidung) | 3 (Tag 0, 14, 15) | 11 |
| Sockel 4, Vorlauf 7 | 35 / 46 | 27 |
| **Sockel 4, Vorlauf 14 (gewählt)** | 3 (Tag 0, 1, 2) | 6 |
| Sockel 4, Vorlauf 21 | 3 (Tag 0, 1, 2) | 6 |

**Korrektur früherer Aussagen:** In der Vorfassung hieß es, Sockel 12 sei eine Ausfall-Reserve für eine Woche. Das stützte sich auf drei Startpunkte. Über alle Starttage hält es nicht: Sockel 12 mit Vorlauf 7 verletzt bei Tag 14 und 15. Auch die Aussage „ab zehn Tagen hält kein Budget die Fristen“ war unvollständig. Maßgeblich ist die Messung oben.

**Offene Grenzen, ehrlich benannt:**
- **Tag 0** ist mit jedem Limit inhärent: 5 Verletzungen auch bei Limit 16. Der Bestand an diesem Tag lässt sich nicht mehr vorarbeiten.
- **Tag 1 und 2** verursachen mit Sockel 4 und Vorlauf 14 die Verletzungen 4 bzw. 1. Der Vorlauf allein reicht dort nicht. Sockel 8 mit Vorlauf 14 hält Tag 1 bis 3 ohne Verletzung. Das ist die nächste Stellschraube, falls der Herausgeber sie will.
- Die Messung nimmt eine tägliche Automatik an. Fehlerraten einzelner Läufe sind nicht modelliert.

## 4. Was geändert wurde

| Datei | Änderung |
|---|---|
| `data/agent_reach/faktenfrische.yaml` | `max_artikel_pro_lauf: 12 → 4`, `vorlauf_tage: 7 → 14`, Kommentarblöcke korrigiert. Limit 16 und Nachholfrist 7 unverändert. |
| `scripts/faktenfrische_kapazitaet.py` | Trajektorie, `basis`-Parameter, Kopfdoku Punkt 6 |
| `scripts/tests/test_faktenfrische_kapazitaet.py` | `ProjektionTrajektorieTest` (7), `BuenndelWacheSweepTest` auf `basis=heute` mit gegenprobe, `AusfallToleranzTest` (2: Zusage Starttage 3/10/20 und Gegenprobe Vorlauf 7) |
| `docs/ANLEITUNG-FAKTENFRISCHE.md` | Entscheidung, Tabellen mit Automatik-Messung, Korrekturen |
| `KADENZ-HORIZONT-1107-DAUERHEILUNG-2026-11-06.md` | Dieser Bericht |

**Unverändert:** Limit 16, Nachholfrist 7, Intervalle, Mindestdeckung 110 %, Workflow, Siegel-Dateien (`data/integrity_lock.json` enthält diese Dateien nicht).

## 5. Verifikation (Stand dieses Commits)

| Prüfung | Ergebnis |
|---|---|
| `faktenfrische_kapazitaet.py --selftest` | 49 Fälle grün |
| `faktenfrische.py --selftest` | 29 / 29 grün |
| `faktenfrische_deckung_ticket.py --selftest` | 26 Fälle grün |
| `--wache` heute / 2026-11-26 / 2026-12-31 | Exit 0 / 0 / 0 |
| `--budget-empfehlung` | 4 |
| Unit-Suiten Faktenfrische plus Release-, Publish- und Deploy-Suiten | 297 Tests OK (vor dem Ausfall-Test), danach `AusfallToleranzTest` 2 / 2 grün |
| `governance_contract.py --quick` | erfüllt, 46 Regeln |
| `skript_syntax_wache.py` | 665 Dateien grün |
| `wachen_vertrag.py` | 385 Skripte, 0 Funde |
| `integrity_guard.py --gate` | 55 Kerndateien grün |

**Laufzeit:** Die Kapazitätstests brauchen rund 60 s statt 11 s (Montags-Sweep mit korrekter Basis). Der neue Ausfall-Test dauert rund 6 s.

## 6. Nicht getan

- Kein Merge ohne grüne Checks für genau diesen Commit (D11).
- Issue #1107 bleibt offen. Der Schließpfad läuft über den Workflow und die Entscheidung des Herausgebers (D2).
- Keine Änderung am Limit (16).
- Keine Kommentare auf GitHub.
