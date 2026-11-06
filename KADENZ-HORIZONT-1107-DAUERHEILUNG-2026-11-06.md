# Kadenz-Horizont #1107 – Dauerheilung (06.11.2026)

**Auftrag:** Issue #1107 „⏰ Frist: Kadenz-Horizont – projiziert 26.11./31.12.2026 rot, auch am Limit (Frist 20.11.2026)“. Option C gewählt (Korridor anpassen: Limit anheben mit Reserve-Prüfung **oder** Sockel-Grenzen neu vermessen). Dauerhaft auf Highend-Niveau einer Profi-Agentur beheben.

**Ergebnis in einem Satz:** Die rote Projektion war ein Messfehler, kein Kapazitätsdefizit. Die Wache rechnete Zukunftstage mit dem heute eingefrorenen Prüfstand, als hätte der Bot bis dahin nichts geprüft. Korrigiert auf die Trajektorie ab heute. Der Korridor (Sockel 12, Limit 16) bleibt unverändert, weil die Messung kein höheres Limit verlangt. Eine Anhebung auf über 16 würde die Ausfallsicherheit nicht verbessern (Abschnitt 4).

---

## 1. Befund

| Stichtag | Eingefrorener Stand (alt) | Trajektorie ab heute (neu) |
|---|---|---|
| 26.11.2026, Budget 16 | 30 überfällig, 24 Fristen gerissen → **rot** | 0 überfällig, 0 gerissen → **grün** |
| 31.12.2026, Budget 16 | 104 überfällig, 2 gerissen → **rot** | 0 / 0 → **grün** |

Die Projektion unterstellte, der Bot prüfe zwischen heute und dem Stichtag nichts. Dann wurden Seiten, die er in dieser Zeit längst geprüft hätte, als überfällig gezählt.

**Warum die Trajektorie das richtige Modell ist:** Die Auswahl in `simuliere` ist dieselbe EDF-Regel wie in `scripts/faktenfrische.py` (`edf_schluessel` plus Vorlauf-Kandidaten mit `restlaufzeit <= vorlauf`). Die Simulation gibt also den Weg wieder, den der Bot tatsächlich geht.

## 2. Korrektur im Code

Dateien: `scripts/faktenfrische_kapazitaet.py`, `scripts/tests/test_faktenfrische_kapazitaet.py`.

- **`simuliere`** merkt sich den letzten Prüftag je Seite und liefert optional Tagesschnappschüsse (`beobachte`).
  - Der Schnappschuss wird **zu Beginn** des Tages genommen. Ein Schnappschuss nach der Verarbeitung hätte den Tagesplatz beim Restart doppelt gezählt. Dieser Fehler wurde beim Testen gefunden und korrigiert (ST13b).
- **`bestand_trajektorie(artikel, cfg, budget, laeufe, basis, ziele)`** ist neu: Bestand an jedem Zieltag, wie der Bot ihn ab `basis` hinterlässt. Vergangene oder heutige Ziele bleiben unverändert.
- **`plan(..., basis=)`, `empfohlenes_budget(..., basis=)`, `spitzenlast_stichtag(..., basis=)`, `spitze_zahlen(..., basis=)`** nehmen den Ausgangspunkt entgegen. Ohne `basis` ist der Stichtag selbst der Ausgangspunkt, das heutige Verhalten bleibt also gleich.
- **Spitzentag:** Der Zustand an jedem Bündeltag ist die Trajektorie. Kandidatentage kommen aus heutigem Stand und aus dem Stand am Horizontende, weil der Bot selbst neue Fristen erzeugt.
- **`main()`** übergibt `basis = heute`. Ein Ausgangspunkt nach dem Stichtag wird hart abgewiesen (fail-closed), genauso jede nicht beweisbare Laufkalenderlage.
- **Keine Gate-Lockerung:** Die Urteile (`c45_urteil`, `puenktlich`, `rueckstand_abgebaut`, Reserve-Regel) sind unverändert. Geändert wurde nur der Zustand, an dem sie gemessen werden.

## 3. Messungen (Trajektorie ab heute, 06.11.2026, 115 Seiten)

**a) Steady-State und Bündel-Boden** (Kalender-Sweep über 52 Montage, `spitzenlast_stichtag` mit `basis=heute`):

| Budget | Montage rot | Anmerkung |
|---|---|---|
| 1 | 52 / 52 | Engpass, bleibt rot |
| 2 | 52 / 52 | Engpass, bleibt rot |
| 3 | 12 / 52 | Engpass |
| **4** | **0 / 52** | **Bündel-Boden** (Bedarf 2,82/Tag, Deckung 142 %) |
| 12 (Sockel) | 0 / 52 | heute |

Zum Vergleich: Der eingefrorene Restart zeigte bei Budget 4 noch 4 / 52 rot. Diese vier Montage waren ein Messfehler.

**b) Ausfall-Probe** (ein Lauf fällt aus, Start an Tag 3, 10 oder 20):

| Ausfall | Minimales Budget ohne Fristverletzung | Verletzungen bei Limit 16 |
|---|---|---|
| 3 Tage | 4 bis 5 | 0 |
| 7 Tage | 4 bis 7 | 0 |
| 10 Tage | kein Budget bis 60 | 2 |
| 14 Tage | kein Budget bis 60 | 37 (Limit 24: 33) |

Bei 10 und mehr Tagen Ausfall ist der Vorlauf (7 Tage) der Engpass, nicht das Limit.

## 4. Entscheidung für den Herausgeber (offen)

Der Auftrag lautete Option C. Die Messung zeigt, dass **das Limit nicht der Engpass** ist:

- Im Normalbetrieb braucht das System Budget 4. Der Sockel 12 ist etwa dreifach größer.
- Ein Limit über 16 würde die Ausfallgrenze nicht verschieben (Gegenprobe: Limit 24 bei 10 Tagen Ausfall 2 Verletzungen, wie bei 16).
- Ein größeres Limit würde nur mehr Verarbeitung im Aufholmodus bedeuten. Das ist die einzige Stelle, an der es greifen würde, und es erhöht die automatischen Änderungen je Lauf.

Deshalb habe ich das Limit **nicht** angehoben. Offen sind drei Fragen, die der Herausgeber entscheidet:

1. **Sockel 12 beibehalten oder auf 4 senken?** Die Messung trägt 4 für den Normalbetrieb. 12 ist eine Reserve gegen einwöchige Ausfälle (dort braucht man 4 bis 7).
2. **Ausfalltoleranz:** Wie lange darf der Bot ausfallen, ohne dass Fristen reißen? Die Antwort hängt am **Vorlauf** (7 Tage). Ein größerer Vorlauf wäre der Hebel, nicht das Limit.
3. **Messung bestätigen:** Die Änderung betrifft die Wache und ihre Projektion. Sie gehört in ein Review, bevor sie gemergt wird.

## 5. Was geändert wurde (nur Messung und Dokumentation)

| Datei | Änderung |
|---|---|
| `scripts/faktenfrische_kapazitaet.py` | Trajektorie, `basis`-Parameter, Kopfdoku Punkt 6 |
| `scripts/tests/test_faktenfrische_kapazitaet.py` | Neue Klasse `ProjektionTrajektorieTest` (7 Tests, beide Richtungen). Sweep auf `basis=heute` umgestellt, plus Gegenprobe. |
| `data/agent_reach/faktenfrische.yaml` | **Nur Kommentar.** Die Begründung „Bündel“ für Sockel 12 ist als Messfehler widerrufen, der Wert bleibt. |
| `docs/ANLEITUNG-FAKTENFRISCHE.md` | Korrektur der Tabelle, des Rückstandsabschnitts und der Ausfallgrenze |
| `KADENZ-HORIZONT-1107-DAUERHEILUNG-2026-11-06.md` | Dieser Bericht |

**Unverändert:** Sockel (12), Limit (16), Nachholfrist (7), Vorlauf (7), Intervalle, Mindestdeckung (110 %), Workflow, Siegel-Dateien (`data/integrity_lock.json` enthält diese Dateien nicht). `faktenfrische.yaml` wurde nur im Kommentar angefasst; die Werte sind menschlich kuratiert und unberührt.

Historischer Bericht `FAKTENFRISCHE-1039-BUENDEL-DAUERHEILUNG-HIGHEND-2026-11-06.md` bleibt als Dokument unverändert. Seine Zahlen („38 von 83 am 26.11.“) sind durch diesen Bericht korrigiert.

## 6. Verifikation

| Prüfung | Ergebnis |
|---|---|
| `faktenfrische_kapazitaet.py --selftest` | 49 Fälle grün |
| `faktenfrische.py --selftest` | 29 / 29 grün |
| `faktenfrische_befund_ledger.py --selftest` | grün |
| `faktenfrische_deckung_ticket.py --selftest` | 26 Fälle grün |
| `--wache` heute / `--stichtag 2026-11-26` / `--stichtag 2026-12-31` | Exit 0 / 0 / 0 |
| `--budget 1..3 --wache` heute | Exit 1 (Gegenprobe: Wache bleibt scharf) |
| `--budget 4 --wache` heute | Exit 0 |
| `governance_contract.py --quick` | erfüllt, 46 Regeln in beide Richtungen |
| Unit-Suiten Faktenfrische (`test:faktenfrische` plus Erweiterungen) | 184 Tests OK |
| Release-Scorecard, Release-Isolation, Publish-Gate, Check-Length, Deploy-Priorität | 113 Tests OK |

**Laufzeit:** Die Kapazitätstests brauchen jetzt rund 60 s statt 11 s. Ursache ist der Montags-Sweep mit der richtigen Basis (etwa 0,8 s je Aufruf statt 0,4 s). Das ist der Preis für die korrekte Messung. Die Konsumenten laufen einmal täglich und sind nicht betroffen.

## 7. Grenzen und Risiken

- **Modellannahme:** Die Trajektorie setzt voraus, dass der Bot an den Tagen des Kalenders wirklich läuft und jede Prüfung gelingt. Ausfälle sind nur über die Ausfall-Probe abgebildet, nicht über Fehlerraten einzelner Läufe.
- **Keine Rückwärts-Validierung gegen Produktionshistorie.** Die Simulation stimmt mit dem Auswahlcode überein (Prüfung im Code), wurde aber nicht gegen tatsächliche Laufprotokolle abgeglichen. Das wäre der nächste Schritt, falls der Herausgeber ihn will.
- **Ein Befund bleibt sichtbar:** Die Meldung „Am … kämen N von M Seiten zu spät“ zählt Verletzungsereignisse, nicht unterschiedliche Seiten. N kann deshalb größer als M sein (zum Beispiel 189 von 115 bei Budget 1). Die Zahl ist als Dringlichkeit richtig, die Formulierung ist ungenau. Das ist ein Folgeposten, kein Blocker.
- **Issue #1107 bleibt offen.** Der Schließpfad läuft über den Workflow und die Entscheidung des Herausgebers (D2), nicht durch einen Kommentar von Hand.

## 8. Nicht getan (bewusst)

- Kein Commit oder Push ohne Auftrag. Die Änderungen liegen im Arbeitsbranch `arena/365a0a7d-franksfinanzcheck-blog`.
- Kein Merge. Die Änderung wartet auf das Review des Herausgebers (D11: nur mit grünem Abschluss).
- Keine Änderung an Sockel oder Limit ohne Entscheidung des Herausgebers.
- Keine Kommentare auf GitHub, bis der Herausgeber die Entscheidung getroffen hat.
