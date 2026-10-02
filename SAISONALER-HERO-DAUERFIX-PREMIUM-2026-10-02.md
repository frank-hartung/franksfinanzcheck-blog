# 🍂 Saisonaler Hero – Dauerfix auf Premium-Niveau (02.10.2026)

**Anlass:** Issue #514 „Saisonaler Hero-Refresh: Aktion nötig (2026-10-02)" ·
**Lauf:** [36999824666](https://github.com/frank-hartung/franksfinanzcheck-blog/actions/runs/36999824666)
(Step „Claude-Textprüfung – nur H1 und GEO-Lead", Exit 3) ·
**Ziel:** nicht den Tageslauf nachziehen, sondern die Ursache abstellen.

---

## 1. Befund

Die Startseite war **zu keinem Zeitpunkt beschädigt**. Der ausgelieferte
Herbst-Hero besteht SEO/GEO-Vertrag und Startseiten-Wache (`--source-only`
grün). Defekt war die Automatik darum herum:

| Ebene | Was wirklich passierte |
|---|---|
| Fälligkeit | Der kuratierte Hero wurde redaktionell überarbeitet (neuer Lead: „… ist dein Fixkosten-Cockpit für Strom, Gas, Internet, Konto und Versicherungen im Herbst …"). Der Nachweis in `data/saisonaler_hero_state.json` stand noch auf dem Stand vom 27.09. → **Fingerprint-Abweichung**. |
| Folge | `is_due()` kannte nur „fällig". Jede redaktionelle Änderung machte den Hero damit **dauerhaft fällig** – Tag für Tag, bis ein Claude-Lauf gelingt. |
| Zweitfehler | Die Claude-Kette schlug fehl (Exit 3 unmittelbar nach dem Agent-Reach-Brief → Vorbedingung, typischerweise fehlendes/abgelaufenes `PUTER_AUTH_TOKEN`). |
| Eskalation | Exit 3 = harter Job-Fehler → Issue #514. Da die Fingerprint-Abweichung bleibt, hätte sich das **jeden Tag** wiederholt. |
| Diagnose | Exit 3 stand gleichzeitig für „kein Brief", „kein Token", „kein Format", „Kandidat verworfen". Der Report wurde im Fehlerfall gar nicht geschrieben – das Artefakt des roten Laufs war leer. |

Kurz: ein **Fehlalarm-Dauerlauf** mit unbrauchbarer Diagnose, während die
Live-Seite einwandfrei war.

---

## 2. Dauerfix (vier Hebel)

### Hebel 1 – Redaktionelle Änderung einholen statt bestrafen
`due_state()` liefert jetzt einen Grundcode statt eines nackten Flags:
`aktuell · redaktion · rotation · neu · zeitstempel · force`.

Bei `redaktion` prüft das Skript den **live ausgelieferten** Hero gegen den
kompletten Vertrag (Entity-first, drei Kernkategorien, du-Form, Faktenbremse,
Längen, KI-Floskeln) **und** die Startseiten-Wache. Besteht er beides, wird er
automatisch als geprüfter Basisstand übernommen (`approved-seasonal-baseline`),
die Rotationsuhr startet neu. Es wird **nichts generiert** und **nichts als
KI-poliert ausgegeben** – nur der Nachweis holt auf. Besteht er nicht, bleibt
der Lauf hart rot: ein defekter Live-Text ist genau das, was ein Issue verdient.

### Hebel 2 – Kette mit Wiederholung und Korrekturauflage
`claude_candidate()` fragt bis zu dreimal (Backoff 0/20/45 s). Ein verworfener
Kandidat geht als **präzise Korrekturauflage** zurück in den Prompt
(„Die letzte Fassung wurde verworfen: … Behebe genau diese Punkte, ohne neue
Fakten zu erfinden."). Die Faktenbremse bleibt unverändert scharf – sie wird
nur nicht mehr nach dem ersten Stolperer zum Jobabbruch.

### Hebel 3 – Gestufte Eskalation statt Alles-oder-nichts
`escalate()` entscheidet nach dem tatsächlichen Schaden:

| Lage | Ampel | Verhalten |
|---|---|---|
| Kette ausgefallen, Basis geprüft und frisch | 🟡 gelb | Lauf grün, `::warning`, Diagnose-Report, Ausfallzähler im State – **kein** stiller Fallback, aber auch kein Fehlalarm |
| Ausfall in Serie (≥ 3 Läufe) | 🔴 rot | Issue mit vollständiger Diagnose |
| Freigegebene Fassung ≥ 35 Tage alt (21 + 14 Kulanz) | 🔴 rot | Issue |
| Live-Hero verletzt den Vertrag | 🔴 rot | sofort, ohne Kulanz |

### Hebel 4 – Diagnose, die den Namen verdient
Jeder Ausgang schreibt denselben `SAISONALER-HERO-REPORT.md`: Zustand, Ampel,
Grundcode, Exit, Alter der Fassung, **Kettennachweis** (Brief vorhanden? Token
gesetzt? Brücke vorhanden? Ausfallserie?) und das Versuchsprotokoll. Der Report
landet im Lauf-Summary, im Artefakt und – bei Rot – im Issue.

---

## 3. Workflow-Hygiene

* **Step-Summary:** Der Report steht in jedem Lauf direkt unter „Summary".
* **Commit auch im Fehlerfall:** State, Historie und Recherche werden
  `if: always()` gesichert – nur so ist die Ausfallserie überhaupt zählbar.
  `data/saisons.yaml` bleibt im Fehlerfall unverändert (atomarer Rollback).
* **Ein Vorgang je Störung:** Ein offenes Issue wird **kommentiert** statt
  dupliziert; die Diagnose hängt als aufklappbarer Block daran.
* **Selbstschließend:** Läuft die Kette wieder sauber durch (Ampel grün),
  schließt der Workflow das offene Issue mit Lauf-Referenz. Bei Gelb bleibt es
  bewusst offen – die Störung besteht ja noch.

---

## 4. Beweise

```
python3 scripts/saisonaler_hero_refresh.py --selftest        → ✅ grün
python3 -m unittest discover -s scripts/tests \
        -p "test_saisonaler_hero_refresh.py"                 → 21 Tests, OK
python3 -m unittest discover -s scripts/tests \
        -p "test_saisonale_startseite.py"                    → 36 Tests, OK
python3 -m unittest discover -s scripts/tests \
        -p "test_workflow_yaml.py"                           → 6 Tests, OK
python3 scripts/saisonale_startseite_guard.py --source-only  → ✅ Keine Funde
python3 scripts/saisonaler_hero_refresh.py --check --json    → due: false
```

Durchgespielte Eskalationsleiter (State künstlich gealtert, ohne Token):
Lauf 1 🟡 Exit 0 · Lauf 2 🟡 Exit 0 · Lauf 3 🔴 Exit 3 mit Begründung
„3 Läufe in Folge ohne erfolgreiche Claude-Politur". Danach Originalzustand
wiederhergestellt.

Neue Testklassen: `Faelligkeit` (Grundcodes), `Eskalation` (Ampelvertrag),
`ClaudeWiederholung` (Retry, Korrekturauflage, Faktenbremse),
`Ausfallzaehler` (Persistenz der Serie).

---

## 5. Was bewusst **nicht** geändert wurde

* Kein Modellwechsel, kein Anthropic-Key, kein Fallback-Modell – weiterhin
  ausschließlich `claude-sonnet-5` über die Puter-Brücke.
* Keine Lockerung der Faktenbremse: keine Zahlen, Preise, Fristen, Quellen,
  URLs oder Superlative im Hero.
* Keine Template-, CSS-, CTA- oder Layoutänderung; die freigegebene
  `v-hero-premium`-Variante bleibt review-pflichtig.
* Keine Textgenerierung ohne frischen Agent-Reach-Brief.

---

## 6. Offene Betreiberaufgabe (einmalig)

Der wahrscheinlichste Auslöser des Kettenausfalls ist ein **abgelaufenes
`PUTER_AUTH_TOKEN`** (Secret ist aus dem Lauf heraus nicht prüfbar). Bitte das
Secret einmal erneuern; der Workflow sagt ab sofort selbst, woran es liegt:
Der Kettennachweis im Report zeigt „PUTER_AUTH_TOKEN ❌ fehlt/leer" bzw. den
Brückenfehler im Klartext. Bis dahin bleibt die Startseite mit dem geprüften,
kuratierten Herbst-Hero live – ohne tägliche Fehl-Issues.
