# Kadenz-Horizont #1107 – die dritte Messart (10.11.2026)

**Auftrag:** „Frist: Kadenz-Horizont – projiziert 26.11./31.12.2026 rot, auch
am Limit (Frist 20.11.2026) #1107 – bitte dauerhaft auf Highend-Niveau einer
Profi-Agentur beheben.“
**Ausgangslage:** #1117 ist als `8349d8d` gemergt; die Projektion rechnet seit
dem 07.11.2026 die Trajektorie ab heute. Der Befund von #1107 ist damit
widerlegt – **nachrechenbar**, nicht behauptet.
**Stand:** 10.11.2026, Branch `arena/ee0d10ff-franksfinanzcheck-blog`,
aufgebaut auf `main` (`90aa12b`).

---

## 1 · Das Ergebnis in vier Sätzen

Die Korrektur aus #1117 ist richtig, aber sie kannte nur **zwei** Messarten:
`trajektorie: true` (Weg ab heute) und `trajektorie: false`. Der zweite Zustand
trug im Klartext den Satz „Stichtag selbst (Nachweis, keine Projektion in die
Zukunft)“ – und das ist für einen **Zukunftstag, der mit dem Prüfstand seines
eigenen Tages gemessen wurde**, nachweislich falsch: Es *ist* eine Projektion,
und sie *ist* eingefroren. Genau dieser Satz hat aus dem Fehlbild ein Ticket
mit Frist gemacht. Seit heute entscheidet **eine** Funktion
(`projektions_modus`) zwischen `weg`, `nachweis` und `eingefroren`; der dritte
Zustand ist laut (⚠️ im Klartext, `eingefroren: true` im JSON, `--wache` →
Exit 2, Deckungs-Ticket → „beweislos“) und nur noch über den ausdrücklichen
Schalter `--gegenprobe` erreichbar. Damit lässt sich #1107 **reproduzieren**,
ohne es zu behaupten – und keine Oberfläche kann eine Momentaufnahme mehr als
Betriebsnachweis ausgeben.

---

## 2 · Der Rest, den #1117 stehen ließ

| Ebene | vorher (07.11.2026) | Befund |
|---|---|---|
| `messe()` | `projektion.trajektorie: false` | Heute und „eingefrorene Zukunft“ sehen **identisch** aus |
| Klartext | „Stichtag selbst (Nachweis, keine Projektion in die Zukunft)“ | Falsch für jeden Zukunftstag – er ist eine Prognose, und eingefroren ist er auch |
| CLI | kein Weg zur Gegenprobe | Das Fehlbild ließ sich nicht mehr *vorführen*, nur behaupten |
| `--wache` | prüfte `puenktlich`/`spitze` | Eine eingefrorene Messung hätte die Wache füttern können |
| Deckungs-Ticket | kannte grün/rot/beweislos | Eine eingefrorene Messung galt als Nachweis → hätte schließen können |
| C45 | Marker für die drei Bausteine | Die Unterscheidung selbst war **löschbar**, ohne dass der Bau rot wurde |

Die Lehre ist dieselbe wie am 07.11.: Nicht die Zahl war falsch, sondern
**welche Art Zahl sie ist** stand nirgends. Ein Gate, das eine Gegenprobe wie
einen Betriebszustand behandelt, ist genau der Dauer-Alarm, den C14 verbietet.

---

## 3 · Nachrechnung am 10.11.2026 (126 Seiten, Sockel 5 / Limit 18)

Beides mit demselben Bestand, demselben Budget-Korridor und derselben
Simulation – nur die Messart unterscheidet sich:

| Stichtag | Weg des Bots (`modus: weg`) | Eingefroren (`modus: eingefroren`) |
|---|---|---|
| 2026-11-26 | **0 überfällig** · 0 gerissene Termine · Weg frei bis 2027-03-26 · `puenktlich: true` | 25 überfällig (max. 13 Tage) · **13 gerissene Termine** · „auch mit Limit 18 nicht fristgerecht abbaubar“ |
| 2026-12-31 | **0 überfällig** · 0 gerissene Termine · Weg frei bis 2027-04-30 · `puenktlich: true` | 114 überfällig (max. 48 Tage) · 2 gerissene Termine · `empfehlung_erreicht: false` |

Die rechte Spalte ist die Klasse, aus der #1107 entstand (am 06.11.2026 mit
115 Seiten: 30 und 104 überfällig). Sie beschreibt **keinen Zustand, den der
Bot erreicht** – sie beschreibt, was wäre, wenn er ab heute aufhörte. Die
linke Spalte ist der Betrieb; an beiden Tagen reißt nichts.

**Tageslauf heute:** 126 Seiten · Bedarf 3,08 Prüfungen/Tag (21,5/Woche) ·
Budget 5 × 1,00 Läufe/Tag · Deckung **162,5 %** · Weg frei bis **2027-03-10** ·
59 Bündeltage im Horizont ohne Befund · `--wache` **Exit 0**.

Reproduzierbar in zwei Befehlen (Beweispaar für das Ticket):

```bash
python3 scripts/faktenfrische_kapazitaet.py --stichtag 2026-11-26 --json
#   → "modus": "weg", 0 überfällig, kadenz_horizont.weg_frei: true
python3 scripts/faktenfrische_kapazitaet.py --stichtag 2026-11-26 --gegenprobe --json
#   → "modus": "eingefroren", "eingefroren": true, "warnung": "...", 25 überfällig
```

---

## 4 · Was jetzt anders ist

### 4.1 Eine Entscheidung, drei Zustände

```python
def projektions_modus(stichtag, basis, heute=None) -> str:
    """→ 'weg' | 'nachweis' | 'eingefroren' – die eine Stelle (C19)."""
```

- `basis < stichtag` → **weg** (Zukunft ab heute, Betriebsnachweis).
- `basis == stichtag` und Stichtag heute/gestern → **nachweis**.
- `basis == stichtag` und Stichtag in der Zukunft → **eingefroren**.
- Ausgangspunkt **nach** dem Stichtag → `ValueError` (fail-closed, wie `plan`).

Jede Messung trägt `projektion.modus`, `eingefroren`, `warnung` und `regel`.
`trajektorie` bleibt als Rückwärtskompatibilität erhalten, ist aber nicht mehr
die Aussage, auf die sich eine Oberfläche stützen darf.

### 4.2 Eingefroren ist laut, nicht still

- **Klartext:** Die ⚠️-Zeile „Eingefrorene Gegenprobe – kein
  Betriebsnachweis“ steht **vor** allen Zahlen, die sie erzeugt; die
  Horizont-Zeile heißt dann „Weg des Bots (im eingefrorenen Stand)“. Nach dem
  Bericht folgt dieselbe Warnung als Schlusszeile.
- **JSON:** `eingefroren: true` + `warnung` – maschinell prüfbar.
- **Ticket:** `gegenprobe_befund()` setzt den Rahmen; `bewertung()` liefert
  `beweislos` statt `grün`. Eine Gegenprobe schließt **nichts** und erzeugt
  keinen Auftrag.
- **Wache:** `--wache --gegenprobe` endet mit **Exit 2** („eine Wache auf
  einer Gegenprobe wäre ein Scheinnachweis“). Zusätzlich prüft `main()` den
  Modus, bevor irgendetwas gemessen wird.

### 4.3 Die Gegenprobe ist ein Werkzeug, kein Betriebsmodus

`--gegenprobe` verlangt `--stichtag` **in der Zukunft**; heute und gestern
sind ein echter Nachweis und werden abgewiesen. Wer das Fehlbild von #1107
zeigen will, kann es zeigen – wer eine Entscheidung braucht, bekommt sie nur
noch aus dem Weg.

### 4.4 Governance hält die Unterscheidung

C45 verlangt zusätzlich die Marker `projektions_modus`, `eingefroren` und
`--gegenprobe`. Wer die dritte Messart löscht, macht den **Bau** rot, nicht
erst das Ticket – dieselbe Mechanik wie bei `bestand_trajektorie` (#1117).

---

## 5 · Automatische Selbstheilung

| Kreis | Wie er sich selbst schließt |
|---|---|
| **Täglicher Lauf** | `--wache` und `--json` messen ohne Zutun den Weg ab heute (`modus: weg`); ein Zukunftstag kann nicht mehr versehentlich eingefroren werden. |
| **Deckungs-Ticket** | Bewertet eine eingefrorene Messung als `beweislos` – es kann daraus weder schließen noch einen Auftrag ableiten; der grüne Lauf schließt es weiter selbst. |
| **Governance C45** | Drei Pflichtmarker; Löschen ist ein Bau-Fehler. |
| **Tests / Selbsttest** | ST15 (Modus, Warnung, Rahmen vor den Zahlen) und `MessartDreiZustaendeTest`, `EingefroreneGegenprobeTest` – inklusive CLI-Wache (Exit 2). |

Bewusst **nicht** automatisiert: Takt, Sockel, Limit und Intervalle. Sie
stehen in `data/agent_reach/faktenfrische.yaml` und gehören dem Herausgeber.
Die Schließung von #1107 ist ebenfalls eine menschliche Entscheidung – der
Befund, aus dem die Frist entstand, ist widerlegt und nachrechenbar.

---

## 6 · Was geändert wurde

| Datei | Änderung |
|---|---|
| `scripts/faktenfrische_kapazitaet.py` | `projektions_modus`, `projektions_regel`, drei Messarten in `messe()`; ⚠️-Rahmen im Klartext; `--gegenprobe` (nur Zukunftstag, nie mit `--wache`); ST15 |
| `scripts/faktenfrische_deckung_ticket.py` | `gegenprobe_befund()`, `bewertung()` → `beweislos` bei eingefrorener Messung; ehrliche `projektion_zeile()` (drei Zustände); D8 |
| `scripts/governance_contract.py` | C45-Marker `projektions_modus`, `eingefroren`, `--gegenprobe` + Begründung |
| `scripts/tests/test_faktenfrische_kapazitaet.py` | `MessartDreiZustaendeTest` (6 Tests) |
| `scripts/tests/test_faktenfrische_deckung_ticket.py` | `EingefroreneGegenprobeTest` (4 Tests) |
| `docs/ANLEITUNG-FAKTENFRISCHE.md` | Nachzug 10.11.2026 (drei Zustände, Tabelle, Beweispaar) |
| `KADENZ-HORIZONT-1107-DAUERHEILUNG-HIGHEND-2026-11-10.md` | dieser Bericht |

**Unverändert:** `data/agent_reach/faktenfrische.yaml` (Sockel 5, Vorlauf 14,
Limit 18, Nachholfrist 7, Horizont 120, Mindestdeckung 110 %), Intervalle,
Workflow-Takt, Scorecard-Schwellen. Dieser Branch misst anders, nicht mehr
oder weniger.

---

## 7 · Verifikation

| Prüfung | Ergebnis |
|---|---|
| `faktenfrische_kapazitaet.py --selftest` | ✅ **68** Fälle (vorher 57, +11 für die dritte Messart) |
| `faktenfrische_deckung_ticket.py --selftest` | ✅ **45** Fälle (vorher 36) |
| `unittest scripts.tests.test_faktenfrische_kapazitaet` | ✅ **80** Tests |
| `unittest scripts.tests.test_faktenfrische_deckung_ticket` | ✅ **18** Tests |
| Faktenfrische-Suiten (Kapazität, Ticket, Robustheit, Messhöhe, Akte, Ledger) | ✅ **156** Tests |
| `--wache` (heute) | ✅ Exit 0 · 126 Seiten · Deckung 162,5 % · Weg frei bis 2027-03-10 |
| `--stichtag 2026-11-26` / `2026-12-31` | ✅ Exit 0 · `modus: weg` · 0 überfällig · 0 gerissene Termine |
| `--gegenprobe` dieselben Tage | ✅ Exit 0 · `modus: eingefroren` · 25/114 überfällig – das Fehlbild bleibt reproduzierbar |
| `--wache --gegenprobe` | ✅ Exit 2 (Scheinnachweis abgewiesen) |
| `--gegenprobe` ohne Zukunftstag / ohne `--stichtag` | ✅ Exit 2 |
| `governance_contract.py --quick` | ✅ erfüllt (47 Regeln) |
| `skript_syntax_wache.py` | ✅ 689 Dateien |
| `wachen_vertrag.py` | ✅ 395 Skripte, 0 Funde |
| `integrity_guard.py --gate` | ✅ 55 Kerndateien (HEAD `90aa12b`) |
| Volle Suite (`discover -s scripts/tests -t scripts/tests`) | 5716 Tests · 19 Befunde **außerhalb** des Änderungsbereichs |

**Zu den 19 Befunden der vollen Suite (ehrlich statt grün gerechnet):** Kein
Faktenfrische-Test ist rot. Die Befunde liegen in Bereichen, die dieser Branch
nicht berührt, und sind im Sandkasten reproduzierbar, z. B.
`data/gsc/meta.json` (ungültiges JSON im Bestand, `gsc_artefakte_guard`
verlangt `--heal`), `pagefind`-Pin im Test (1.5.2) gegen die soeben gemergte
Dependabot-Anhebung (1.6.0) und der Hugo-Pin-Abgleich. Sie sind **vor** dieser
Änderung vorhanden und werden hier nicht mitgeheilt, weil sie eigene
Entscheidungen (Artefakt-Reparatur, Pin-Vertrag) tragen.

---

## 8 · Nicht getan – bewusst

- **Keine Korridor-Änderung.** Sockel 5 / Limit 18 sind der gemergte Stand;
  dieser Branch entscheidet nichts nach.
- **Kein Workflow-Umbau.** Die Messart reist in `--json` und `--wache` mit;
  der bestehende Schritt und das bestehende Ticket lesen sie.
- **Kein Schließen von #1107.** Die Schließung liegt beim Herausgeber; der
  Befund, aus dem die Frist entstand, ist nachrechenbar widerlegt (Abschnitt
  3), und seit heute ist auch die Verwechslung, die ihn erzeugte, nicht mehr
  still möglich.
- **Keine Zusage zur Ausfalltoleranz.** Gemessen und benannt, nicht zugesagt
  (`AusfallToleranzTest`, SSOT-Kommentar 10.11.2026).
