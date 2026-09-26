# Vorfall #393 – „Bot-Watchdog: Automatisierung braucht Eingriff“

**Datum:** 26.09.2026 · **Ticket:** #393 (Label `bot-watchdog`, geöffnet 13:18 UTC)
**Befund im Ticket:** `P2 · Content-Reserve niedrig (Maschine) – Nur 3 Reserve-Artikel (<4)`
**Status:** behoben · **Folgevorfall zu:** [#387](INCIDENT-2026-09-26-content-reserve-387.md)

---

## 1. Warum dieses Ticket immer wiederkam

Das Ticket war kein Einzelbefund, sondern ein **Dauerzustand mit Ansage**. Es
meldete sich nach jeder Veröffentlichung neu, weil zwei unabhängige Fehler
zusammenwirkten – und der zweite den ersten unsichtbar machte.

| # | Fehler | Wirkung |
|---|--------|---------|
| 1 | **Die Messlatte gehörte dem Gemessenen** – Ziel aus dem Zertifikat statt aus der Produktionslinie | Abgesenktes Ziel hielt sich selbst fest; Engpass sah grün aus |
| 2 | **Null Puffer** – Alarmschwelle (4) war identisch mit dem Zielbestand (4) | Die Linie füllte exakt bis zur Alarmgrenze; die nächste Veröffentlichung löste sofort wieder Alarm aus |

Dieselbe Zahl – „wie viele Kandidaten soll der Vorrat haben?“ – stand an
**drei** Orten, die nichts voneinander wussten:

| Ort | Quelle | Wert am 26.09. |
|---|---|---|
| `.github/workflows/content-reserve.yml` | `vars.RESERVE_TARGET \|\| '6'` | Produktionsziel |
| `data/reserve-readiness.json` | Feld `target`, **vom Lauf selbst geschrieben** | 4 |
| `scripts/bot_watchdog.py` | `minimum = 4`, hart codiert | 4 |

Das ist exakt die Fehlerklasse, die schon #387 erzeugt hat und dort benannt
wurde: **„ein Zustand, der nur in einer Datei steht, aber niemandem gehört.“**

---

## 2. Fehler 1 im Detail: die Ratsche

`reserve_gate.evaluate()` las das Ziel aus dem Zertifikat – also aus genau dem
Artefakt, über das es urteilen sollte:

```python
target = int(data.get("target", os.environ.get("RESERVE_TARGET", "6")))
```

`reserve_converge.cert_state()` tat dasselbe **und reichte den Wert nach unten
weiter**:

```python
state["target"] = int(data.get("target", goal))          # aus dem Zertifikat
...
env = {..., "RESERVE_TARGET": str(vorher["target"])}      # an die Kindprozesse
```

`reserve_readiness.py` schrieb ihn von dort zurück ins Zertifikat. Damit war
der Kreis geschlossen:

```
Zertifikat (target: 4) → Konvergenz liest 4 → brauche = 4 − 4 = 0
   → kein Nachschub → Zertifikat wird erneut mit target: 4 gestempelt
```

**Eine einmal abgesenkte Latte konnte sich nie wieder erholen.** Das
Produktionsziel aus dem Workflow wurde nach dem ersten Durchlauf nie wieder
gelesen; eine Erhöhung von `vars.RESERVE_TARGET` wäre wirkungslos geblieben,
bis jemand zufällig das Zertifikat löscht.

### Nachweis aus der Historie

Das Ziel stand **16 Tage lang stabil auf 6** und kippte genau einmal:

```
18923203  09-26 18:41  content: unabhängige Redaktionsreserve auffüllen | target=4 ready=4 pool=4
3c85a311  09-26 18:31  Fix content reserve janitor cleanup (#404)       | target=6 ready=1 pool=1
f0e6ae0d  09-26 16:57  fix(reserve): Pool auf 6/6 schließen (#387)      | target=6 ready=6 pool=6
…
78bec8cc  09-10 08:28  content: unabhängige Redaktionsreserve auffüllen | target=6 ready=2 pool=None
```

Der Zustand vor der Reparatur, reproduziert auf dem Ist-Stand:

```
$ RESERVE_TARGET=6 python3 scripts/reserve_gate.py
✅ Reserve-Pool gate-fertig: 4/4 Kandidaten zertifiziert.
EXIT=0            ← Ziel 6, Pool 4, und der harte End-Gate ist grün
```

Der Gate, dessen Grundregel „**Stock shortage must not look successful**“
heißt, bestätigte einen Engpass als Vollbestand.

---

## 3. Fehler 2 im Detail: null Puffer

Der Watchdog meldet, wenn der Vorrat unter seine Schwelle fällt. Diese
Schwelle war die Zahl **4** – hart im Code. Der Zielbestand war ebenfalls
**4**. Damit galt:

```
Linie füllt auf  4  ──→  Alarmschwelle  4
1 Artikel geht live  ──→  3 < 4  ──→  Ticket #393
Nacht füllt auf  4   ──→  Alarmschwelle  4
1 Artikel geht live  ──→  3 < 4  ──→  Ticket #393
```

Ein Regelkreis ohne Hysterese schwingt. **Das Ticket war kein Symptom eines
kaputten Vorrats, sondern ein Konstruktionsfehler der Alarmierung.** Genau
deshalb half jedes Auffüllen nur bis zur nächsten Veröffentlichung.

---

## 4. Was jetzt anders ist

### 4.1 Ein Besitzer für die Zahlen (`scripts/reserve_economy.py`, neu)

Eine Quelle, zwei abgeleitete Zahlen, eine **erzwungene Invariante**:

```
ZIEL          := RESERVE_TARGET (Default 6, geklemmt auf 2…60)
PUFFER        := RESERVE_PUFFER (Default 2 ≈ ein Publikationstag)
ALARMSCHWELLE := min(max(1, ZIEL − PUFFER), ZIEL − 1)

Invariante:   1 ≤ ALARMSCHWELLE < ZIEL        (strukturell, nicht per Konvention)
```

Beim dokumentierten Ziel 6 ergibt das Alarmschwelle **4** – exakt der Wert, der
vorher hart im Watchdog stand. **Die Alarm-Semantik bleibt unverändert; neu ist
nur, dass die Zahl einen Besitzer hat und mitwandert.** Bei Ziel 4 ergibt sie
2, der Puffer ist also auch dann wieder da.

Kaputte Konfiguration senkt das Ziel nie still: `RESERVE_TARGET=vier`,
`=1` oder `=10000` werden auf den erlaubten Bereich geklemmt **und melden sich**.

### 4.2 Das Zertifikat ist Zeuge, nicht Gesetzgeber

| Stelle | vorher | jetzt |
|---|---|---|
| `reserve_gate.evaluate()` | Ziel aus dem Zertifikat | Ziel aus `reserve_economy.ziel()` |
| `reserve_converge.cert_state()` | Ziel aus dem Zertifikat, nach unten weitergereicht | Ziel aus dem SSOT; Zertifikatsziel nur noch als `zertifikat_ziel` (Beweismittel) |
| `reserve_readiness.target()` | eigene Env-Lesung | delegiert an den SSOT |
| `bot_watchdog.check_content_reserve()` | `minimum = 4` | `reserve_economy.alarmschwelle()` |

Das Feld `target` im Zertifikat bleibt erhalten – als **Protokoll** („gegen
diese Latte wurde gemessen“). Weicht es vom Produktionsziel ab, ist das ein
eigener, benannter Befund (`MESSLATTE`) im Gate, im Watchdog und in der
Lauf-Zusammenfassung – statt Schweigen.

### 4.3 Der Engpass sieht wieder wie ein Engpass aus

```
$ python3 scripts/reserve_gate.py
🛑 RESERVE-ENGPAß: nur 4/6 Kandidaten gate-fertig.
   ✅ 2026-09-26-2026-stromkosten-senken-einfach-stromanbieter-wechseln | Score 0.978
   ✅ 2026-09-26-wlan-verstaerker-vs-mesh-wlan-was-brauchst-du-wirklich | Score 0.956
   ✅ 2026-09-26-20-wege-zu-weniger-kosten-stromrechnung-zu-hoch        | Score 0.892
   ✅ 2026-09-26-photovoltaik-2026-wann-rechnet-sich-die-sonne-wirklich | Score 0.928

   URSACHEN DIESES ENGPASSES:
   • MESSLATTE: Das Zertifikat wurde gegen Ziel 4 gemessen, die Produktions-
     linie verlangt 6. Ein Zertifikat setzt seine eigene Latte nicht – der
     nächste Lauf von `scripts/reserve_readiness.py` stempelt sie auf 6 um.
EXIT=1
```

Auch der **grüne** Lauf sagt jetzt, gegen welche Latte er grün ist – ein
„✅ 4/4“ war vorher nicht von einem echten Vollbestand zu unterscheiden.

### 4.4 Der Watchdog nennt beide Zahlen

```
vorher:  Reserve ausreichend (4/4 gate-fertige Artikel, 4 Reserve-Entwürfe)
jetzt:   Reserve ausreichend (4 gate-fertige Artikel (Ziel 6, Alarm unter 4),
         4 Reserve-Entwürfe; MESSLATTE: …)
```

Der Nenner war vorher die Alarmschwelle und las sich wie ein Zielbestand.

---

## 5. Nachweis

| Prüfung | Ergebnis |
|---|---|
| `python3 -m unittest discover -s scripts/tests` | **961 Tests, OK** (22 übersprungen; vorher 952) |
| `scripts/selftest_runner.py` | **105 Wachen**, 210 Uhr-Proben, alle grün (vorher 103) |
| `governance_contract.py --selftest` | C1–C18 grün, `reserve_economy.py` im Minimum (GUARDS) |
| `reserve_economy.py --selftest` | Invariante über **alle** Ziel/Puffer-Paare, Klemmung laut, Drift erkannt |
| **Mutationsprobe** | die 3 Kernverträge gegen die **alte** Logik: **3 von 3 rot** |

Die Mutationsprobe ist der eigentliche Beweis: Sie baut die alte
`evaluate()`/`cert_state()`-Fassung nach und lässt die neuen Verträge darauf
los. Ergebnis – die alte Logik meldet wieder
`✅ Reserve-Pool gate-fertig: 4/4 Kandidaten zertifiziert`, und alle drei
Verträge fallen um. Ein Vertrag, der gegen den Fehler nicht rot wird, bewacht
ihn nicht.

### Neue Verträge (`scripts/tests/test_reserve_pipeline.py`, +9)

*Messlatten-Besitz:* Zertifikat setzt sein Ziel nicht selbst · Engpass sieht
nicht erfolgreich aus · Ratsche ist tot (Konvergenz liest das Produktionsziel)
· Readiness stempelt das Produktionsziel · Drift wird gemeldet statt
verschwiegen.
*Puffer-Invariante:* Alarmschwelle liegt **immer** echt unter dem Ziel (über
alle Ziel/Puffer-Paare) · dokumentiertes Ziel 6 behält die alte Alarmsemantik
(4) · Watchdog nutzt die abgeleitete Schwelle (kein `minimum = 4` mehr im
Quelltext) · kaputte Konfiguration senkt das Ziel nicht still.

---

## 6. Wirkung auf den Betrieb

* **Content-Reserve** (`content-reserve.yml`, täglich 03:25 UTC) arbeitet
  wieder auf das echte Produktionsziel hin, statt bei `brauche = 0`
  stehenzubleiben.
* **Bot-Watchdog** (`bot-watchdog.yml`, täglich 08:30 UTC) meldet erst, wenn
  der Vorrat den Puffer aufgebraucht hat – nicht mehr nach jeder einzelnen
  Veröffentlichung. **Ticket #393 hat damit wieder einen Schließpfad.**
* Der Befund bleibt in seinem Kanal (`bot-watchdog`, Besitzer `auto`) – am
  Alarm-Routing aus #272 ändert sich nichts.

Verhalten bei beiden möglichen Zielwerten:

| `vars.RESERVE_TARGET` | Ziel | Alarm ab | Puffer |
|---|---|---|---|
| nicht gesetzt (Default) | 6 | unter 4 | 2 Artikel |
| `4` | 4 | unter 2 | 2 Artikel |

In **beiden** Fällen gilt Alarmschwelle < Ziel – das Flattern ist unabhängig
vom eingestellten Wert beendet.

---

## 7. Was ein Mensch noch entscheiden kann (optional)

1. **Puffertiefe.** `vars.RESERVE_TARGET` ist eine Actions-Variable und nur
   mit Admin-Rechten les-/schreibbar (Agenten-Token: HTTP 403). Steht sie auf
   `4`, ist der Vorrat knapp über einem Publikationstag (Mo/Mi/Fr, 2–3
   Artikel). **Für rund zwei Ausfalltage: Variable auf `6` setzen oder
   löschen** (Default ist 6) – Code, Alarmschwelle und Doku ziehen automatisch
   mit, es ist keine weitere Änderung nötig.
2. Unverändert aus #387 offen: die **5 Rückläufer** und die **Themen-Klumpen**
   in `data/topics.yaml`.

> Das Zertifikat `data/reserve-readiness.json` trägt bewusst weiterhin
> `target: 4` – es ist das ehrliche Protokoll des Laufs vom 26.09., 18:41 UTC.
> Der nächste nächtliche Lauf stempelt es auf das dann gültige Produktionsziel
> um; gelesen wird es als Vorgabe nicht mehr.
