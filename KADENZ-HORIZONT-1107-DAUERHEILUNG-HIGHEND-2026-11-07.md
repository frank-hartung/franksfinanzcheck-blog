# Kadenz-Horizont #1107 – Dauerwache und Selbstheilung (07.11.2026)

**Auftrag:** „fix(faktenfrische): Projektion rechnet den Weg des Bots statt des
eingefrorenen Stands (#1107)“ – dauerhaft auf Highend-Niveau einer
Profi-Agentur, **mit automatischer Selbstheilung**.
**Ausgangslage:** #1113 ist als `560c88f` in `main` gemergt. Damit rechnet die
Projektion bereits die Trajektorie, und der Korridor steht auf Sockel **4** /
Vorlauf **14** (Entscheidung des Herausgebers). Was fehlte, war die
**Dauerwache**: `basis` war optional, eine Hand-Momentaufnahme konnte weiter
eingefroren werden, und im Ticket stand keine Projektion.
**Stand:** 07.11.2026, Branch `arena/b61c15dc-franksfinanzcheck-blog` (PR #1117),
aufgebaut auf `main` nach #1113.

---

## 1 · Das Ergebnis in vier Sätzen

Die Korrektur aus #1113 ist richtig, aber sie war **umgehbar**: Wer `basis`
wegließ, maß weiter den eingefrorenen Stand – ohne Fehler, ohne Warnung.
Jetzt entscheidet **eine** Funktion (`projektions_ausgangspunkt`), welcher Tag
der Ausgangspunkt einer Messung ist; die CLI benutzt sie, `messe()` ist ohne
Angabe von sich aus sicher, und ein Ausgangspunkt nach dem Stichtag wirft
(fail-closed). Jede Ausgabe nennt ihren Ausgangspunkt (`basis`,
`projektion`) und den Weg als **Datum** (`kadenz_horizont`: „kein Prüftermin
reißt bis 2027-03-07“). Ticket, Tageslauf, Governance (C45) und Tests tragen
die Heilung jetzt selbst – eine Momentaufnahme von Hand erreicht kein Ticket
mehr.

---

## 2 · Nachrechnung am 07.11.2026 (115 Seiten, Korridor 4/14)

| Stichtag | eingefrorener Stand (`basis=stichtag`) | Weg ab heute (`basis=heute`) |
|---|---|---|
| 2026-11-26 | **27 überfällig**, 20 gerissene Zukunfts-Fristen, `puenktlich: false` | **0 · 0 · `true`** |
| 2026-12-31 | **105 überfällig**, 2 gerissene Zukunfts-Fristen, `puenktlich: false` | **0 · 0 · `true`** |

Die eingefrorene Spalte ist die Klasse, aus der #1107 entstand (am 06.11.2026
mit dem damaligen Korridor: 30 und 104 überfällig). Sie beschreibt keinen
Zustand, den der Bot je erreicht – sie beschreibt, was wäre, wenn er ab heute
aufhörte. Der Weg ab heute ist an beiden Tagen ohne Befund.

**Tageslauf heute:** empfohlenes Budget 4 (Sockel 4, Limit 16), Deckung
141,7 %, Weg frei bis **2027-03-07**, 56 Bündeltage ohne Befund, `--wache`
Exit 0.

**Bündel-Boden (Kalender-Sweep 52 Montage, Trajektorie ab heute, Korridor
4/14):** Sockel 3 → 12 Montagen rot, Sockel 4 → **0**, Sockel 12 → 0.

**Ausfalltoleranz (7 Tage, echte Automatik, Starttage 0–20, 07.11.2026):**
Starttag 0 → 4 gerissene Fristen, Tag 1 → 1, ab Tag 2 → 0. Das ist die
gemessene Grenze der Ausfall-Reserve, keine Zusage.

---

## 3 · Was jetzt anders ist

### 3.1 Eine Regel statt eines optionalen Parameters

```python
def projektions_ausgangspunkt(stichtag, heute=None):
    """Zukunft → heute; heute/Vergangenheit → der Stichtag (Nachweis)."""
```

- `main()` benutzt ausschließlich diese Funktion; `messe()` – die Messung,
  aus der Text, JSON und Ticket entstehen – zieht sie ebenfalls, wenn kein
  `basis` übergeben wird.
- `plan()` weist einen Ausgangspunkt **nach** dem Stichtag fail-closed ab.
- Der eingefrorene Vergleich bleibt möglich (`basis=stichtag`), aber er muss
  benannt werden – und er ist die Gegenprobe in den Tests.

### 3.2 Der Weg als Datum

`kadenz_horizont` nennt aus derselben Simulation, die das Urteil fällt:

```json
{"geprueft": true, "bis": "2027-03-07", "tage": 120, "weg_frei": true,
 "erstverletzung": null, "erstverletzung_seite": null,
 "erstverletzung_frist": null, "verletzungen": 0, "seiten": 0,
 "rueckstand_verletzungen": 0}
```

Gezählt werden nur Termine mit **zukünftiger** Frist – dieselbe Menge, die
`puenktlich` urteilt. Der Alt-Rückstand bleibt beim Nachholfrist-Urteil
(`rueckstand_verletzungen` trennt beides). Wer beides vermischt, macht aus
„eine Seite ist schon überfällig“ ein „der Weg reißt heute“.

### 3.3 Jede Ausgabe nennt ihren Ausgangspunkt

`plan()`/`messe()` liefern `basis` und `projiziert`, `messe()` zusätzlich den
Block `projektion` (Stichtag, Ausgangspunkt, `trajektorie: true|false`,
Regel). Wer eine Zahl liest, sieht, ob sie den Weg oder einen Nachweis
beschreibt.

---

## 4 · Automatische Selbstheilung

| Kreis | Wie er sich selbst schließt |
|---|---|
| **Täglicher Lauf** (`faktenfrische.yml`) | `--wache` und `--json` messen mit dem Lauftag als Ausgangspunkt – ohne Handbefehl, ohne zweite Rechnung. |
| **Deckungs-Ticket** | Trägt die Projektion aus derselben Messung: „Der Weg des Bots ist bis **D** frei“ oder „reißt zuerst am **D2** (`seite`, Frist F)“. Öffnet/aktualisiert/schließt sich weiter selbst (C14). |
| **Governance C45** | Pflichtmarker `bestand_trajektorie`, `projektions_ausgangspunkt`, `kadenz_horizont` – Löschen macht den Bau rot, nicht erst den Bestand. |
| **Tests / Selbsttest** | ST14 und vier Klassen, u. a. CLI und Voreinstellung mit eingefrorener Uhr: Fehlbild rot, Weg grün, echter Engpass rot, Ausgangspunkt nach dem Stichtag wirft. |

Bewusst **nicht** automatisiert: Takt, Sockel, Limit und Intervalle. Sie
stehen in `data/agent_reach/faktenfrische.yaml` und gehören dem Herausgeber.

---

## 5 · Was geändert wurde

| Datei | Änderung |
|---|---|
| `scripts/faktenfrische_kapazitaet.py` | `projektions_ausgangspunkt`, `kadenz_horizont`, `messe`; `basis`/`projiziert` in jeder Ausgabe; CLI rechnet jeden Zukunftstag ab heute; ST14 |
| `scripts/faktenfrische_deckung_ticket.py` | Projektion + Weg des Bots im Ticket (Tabelle, Grün- und Rot-Text, „nicht gemessen“ ist kein Grün); Selbsttest D6/D7 |
| `scripts/governance_contract.py` | C45-Marker für Trajektorie, Ausgangspunkt und Horizont |
| `scripts/tests/test_faktenfrische_kapazitaet.py` | `ProjektionsAusgangspunktTest`, `KadenzHorizontTest`, `MessungSelbstheilungTest`; `AusfallToleranzTest` aus #1113 bleibt bestehen |
| `docs/ANLEITUNG-FAKTENFRISCHE.md` | Nachzug 07.11.2026 (Regel, Ausgabe, Ticket, Vertrag) und Nutzungsbeispiel für `--stichtag` |
| `scripts/tests/faktenfrische_gleis.py` | gemeinsame Regel der Befund-Akten: Arbeitsliste ist kein Befund (Abschnitt 7) |
| `scripts/tests/test_faktenfrische_{763,823,911}.py` | prüfen offene Befunde über das Ledger statt „steht nicht in der Queue“ |
| `KADENZ-HORIZONT-1107-DAUERHEILUNG-HIGHEND-2026-11-07.md` | dieser Bericht |

**Unverändert:** `data/agent_reach/faktenfrische.yaml` (Sockel 4, Vorlauf 14,
Limit 16, Nachholfrist 7, Horizont 120, Mindestdeckung 110 %), Intervalle,
Workflow-Takt, Scorecard-Schwellen. Dieser Branch misst anders, nicht mehr
oder weniger; die Korridor-Entscheidung aus #1113 bleibt unangetastet.

---

## 6 · Verifikation

| Prüfung | Ergebnis |
|---|---|
| `faktenfrische_kapazitaet.py --selftest` | ✅ **57** Fälle |
| `faktenfrische_deckung_ticket.py --selftest` | ✅ **36** Fälle |
| `python -m unittest scripts.tests.test_faktenfrische_kapazitaet` | ✅ **74** Tests |
| `python -m unittest discover -s scripts/tests` | ✅ **5474** Tests (22 skipped) |
| `selftest_clock.py --offset 97` (Uhr-Probe) | ✅ grün unter fremdem Kalender |
| Faktenfrische-/Scorecard-Suiten (Ledger, Robustheit, 996, Akte, Slug, Ticket) | ✅ **95** Tests |
| `--wache` (heute) | ✅ Exit 0 · Deckung 141,7 % · Weg frei bis 2027-03-07 |
| `--stichtag 2026-11-26` / `2026-12-31` | ✅ Exit 0 · `projektion.basis = 2026-11-07`, 0 überfällig |
| eingefrorene Gegenprobe (`basis=stichtag`) | ✅ 27 bzw. 105 überfällig – das Fehlbild bleibt reproduzierbar |
| `governance_contract.py --quick` | ✅ erfüllt (47 Regeln) |
| `skript_syntax_wache.py` | ✅ 670 Dateien |
| `wachen_vertrag.py` | ✅ 387 Skripte, 0 Funde |
| `integrity_guard.py --gate` | ✅ 55 Kerndateien |

---

## 7 · Nebenbefund 07.11.2026: drei Zeitbomben derselben Klasse

Der erste volle Suite-Lauf auf diesem Branch wurde rot – nicht wegen der
Projektion, sondern weil drei Aktentests (#763, #823, #911) **dieselbe
Verwechslung** eingebaut hatten, die #1107 ausgelöst hat: Sie prüften, ob
ihre Seiten noch in `data/faktenfrische_queue.json` stehen, und nannten das
„kein offener Befund“. Die Queue ist aber eine **Arbeitsliste**. Mit dem
Vorlauf von 14 Tagen kehren Seiten turnusmäßig zurück – „frisch geprüft vor
23 Tagen“, Frist 14.11., ohne einen einzigen offenen Befund. Am 07.11.2026
wurden zwei der drei Prüfungen rot, ohne dass ein Sachfehler zurückkam; die
dritte wäre am nächsten Fristtag gefolgt.

Geheilt wurde nicht der Testtext, sondern die Frage: `faktenfrische_gleis.py`
fragt das **Befund-Ledger** (`faktenfrische_befund_ledger.offene_befunde`) –
dieselbe Quelle, aus der Redaktion und Ticket arbeiten. Ein Eintrag in der
Arbeitsliste bleibt erlaubt, solange er keinen Befund mitschleppt. Bewusst
**kein** Wortlaut-Muster („frisch geprüft“) als Ersatz: das wäre die nächste
Zeitbombe, sobald die Seite fällig wird.

Nebenbefund im Nebenbefund: `scripts/governance_contract.py` aus #1113/#1119
war beim Zusammenführen verloren gegangen – die Pflichtfeld-Verlust-Wache
(#1110) fehlte in der Wächterliste. Der Vertrag steht jetzt wieder auf dem
Stand von `main` (47 Regeln) **plus** den drei C45-Markern.

**Verifikation dafür:** volle Suite **5474 Tests grün**, Uhr-Probe (+97 Tage)
grün, alle Selbsttests der CI-Kette grün.

---

## 8 · Nicht getan – bewusst

- **Keine Korridor-Änderung.** Sockel 4 / Vorlauf 14 sind der gemergte Stand
  aus #1113; dieser Branch entscheidet nichts nach.
- **Kein Workflow-Umbau.** Die Projektion reist in `--json` und `--wache`
  mit; der bestehende Schritt und das bestehende Ticket lesen sie. Ein
  sicherheitsrelevanter Workflow musste nicht angefasst werden.
- **Kein Schließen von #1107.** Die Schließung liegt beim Herausgeber; der
  Befund, aus dem die Frist entstand, ist nachrechenbar widerlegt.
- **Keine Ausfalltoleranz-Zusage.** Gemessen und benannt (Abschnitt 2),
  nicht zugesagt.
