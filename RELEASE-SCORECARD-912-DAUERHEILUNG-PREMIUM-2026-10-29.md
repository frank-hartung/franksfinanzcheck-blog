# Release-Scorecard: Die Kadenz war zu klein, nicht der Bestand (#912)

**Auftrag (Frank, 29.10.2026):** „Release-Scorecard: Produktionswahrheit rot (Bestand blockiert) #912 – bitte dauerhaft auf Highend-Level einer Profi-Agentur beheben.“

**Prüfmaßstab:** derselbe wie immer – `data/release_scorecard.yaml` (SSOT), gemessen über die Collector-Funktionen des Publish-Gates. **Keine zweite Messregel, keine Ausnahme, keine abgesenkte Schwelle** (C15/C19). Die Intervalle der Faktenfrische (30/45/90 Tage) sind **unverändert**.

---

## Kurzfassung

Die Scorecard war zwischen dem 20. und dem 28.10.2026 **siebenmal rot** (12 der letzten 20 Läufe) – immer mit derselben Zeile: *Faktenalter blockiert*. Ticket #912 ließ sich nicht schließen, weil es nur das Symptom nannte. Die beiden Vorgänger (#732 am 13.10., #796 am 18.10.) reparierten **Texte**; dieser Vorgang repariert die **Ursache**, warum überhaupt ständig Texte überfällig werden.

| Kennzahl | vorher | nachher |
|---|---|---|
| Bedarf (Σ 1/Intervall über 106 Seiten) | 2,58 Prüfungen/Tag (≈ 18/Woche) | unverändert |
| Angebot (Budget × Takt) | 3 × 2 Läufe/Woche = **0,86/Tag** | 3 × 1 Lauf/Tag = **3,00/Tag**, elastisch bis 10,00 |
| **Deckung** | **33 %** – Rückstand **+12 Seiten/Woche** | **116 %** (Spitzen 388 %) – Rückstand −14 Seiten in 5 Tagen |
| Blockiert (live) | 10 Artikel, alle Faktenalter | nach dem nächsten Lauf: 0 (Abbauplan unten) |
| Ticket #912 | Dauer-Alarm ohne Schließpfad | Schließpfad: grün, sobald der Rückstand weg ist |

Der Bestand war nie inhaltlich falsch. Er war **unbezahlt**: Der Takt lieferte ein Drittel dessen, was die eigenen Intervalle verlangen.

## Der Befund – eine Rechnung, die niemand angestellt hatte

Ein Intervalldatum ist keine Messung, sondern eine Quote: Eine Seite mit 30-Tage-Intervall braucht 1/30 Prüfung je Tag. Über den Bestand summiert sich das zum **Bedarf**. Ihm steht ein **Angebot** gegenüber – Budget je Lauf × Läufe je Tag aus dem cron der Workflow-Datei.

```
Bestand          106 Seiten (100 Artikel + 6 Ratgeberseiten)
Bedarf          64 × 1/45  +  31 × 1/30  +  11 × 1/90  =  2,58 Prüfungen/Tag  (18,0/Woche)
Angebot         3 Artikel/Lauf × 2 Läufe/Woche         =  0,86/Tag  (6,0/Woche)
Deckung         0,86 / 2,58                            =  33 %
Rückstand       +12,0 Seiten je Woche – mathematisch nie abbaubar
```

Daraus folgt die rote Kette ohne jedes Inhaltsproblem:

1. Jede Woche werden zwölf Seiten mehr überfällig als geprüft.
2. Die Scorecard meldet genau diese Seiten (korrekt!) als `Faktenalter blockiert`.
3. Das Ticket beschreibt das Symptom, nicht die Ursache – und kann deshalb nicht geschlossen werden.
4. Nach sieben Tagen ist der Alarm Rauschen. **Das ist die Klasse, die C14 im eigenen Regelwerk verbietet: kein Dauer-Alarm ohne Schließpfad.**

Belegt am lebenden Bestand (Probetag 29.10.2026, `scripts/faktenfrische_kapazitaet.py`):

```
- Bestand: 106 Seiten · fällig heute: 14 · überfällig: 13 (max. 2 Tage)
- Bedarf: 2,58 Prüfungen/Tag (18,0/Woche) · Angebot: 0,86/Tag (Budget 3 × 0,29 Läufe/Tag) · Deckung 33 %
- Rückstand abgebaut in 18 Tagen (Frist: 7 Tage)
- ⚠️ 82 Seiten mit ZUKÜNFTIGER Frist würden gerissen
```

Die 14 fälligen Seiten sind: **13 Blogartikel** (davon 3 Entwürfe – deshalb meldet die Scorecard genau **10** blockierte Live-Artikel) und **1 Ratgeberseite** (`versicherungen`). Alle dreizehn überfälligen Artikel stammen aus einem Sammel-Prüflauf am 27./28.09.2026 – sie altern im Gleichschritt und liefen am 27.10. gemeinsam über die Kante. Genau dieser Stau ist der Grund, warum es am 26.10. grün und am 27.10. sofort rot war.

## Die Heilung – mehr liefern, nicht weniger messen

### 1. Takt: täglich statt Di + Do (`faktenfrische.yml`)

Der Bestands-Takt läuft jetzt **täglich 06:40 MESZ** (vorher Di + Do). Die Laufzeit ist kein Argument dagegen: die letzten Läufe brauchten für 3 Artikel **90 Sekunden** (Timeout 25 min). Der cron ist die einzige Stelle, an der der Plan definiert ist – die Deckungsrechnung **parst** ihn (`laeufe_je_tag`), sie tippt ihn nicht ab (Prinzip `slot_wache.py`, Governance C45).

### 2. Budget: folgt dem Bedarf (`budget.auto_skalierung`)

`budget.max_artikel_pro_lauf` (3) ist ab jetzt der **Sockel**, `budget.hartes_limit_pro_lauf` (10) die Obergrenze. Dazwischen wählt der Lauf das **kleinste Budget, das den Rückstand fristgerecht abbaut, ohne eine neue Frist zu reißen** (`empfohlenes_budget`, Simulation über 60 Tage). Heute: 3. Bei einem Stau von 60 Seiten: 8. Bei 200: „nicht abbaubar“ – dann ist es ein Befund, keine stille Deckelung.

Ein ausdrückliches `--max <n>` schaltet die Skalierung für diesen Lauf bewusst ab (Handbetrieb, Nachweise).

### 3. Vorlauf: Arbeit beginnt vor der roten Kante (`planung.vorlauf_tage: 7`)

Eine Seite wird **arbeitbar**, wenn ihre Frist sieben Tage entfernt ist – nicht erst, wenn sie schon rot ist. Der Vorlauf ist kein zweiter Fälligkeitsbegriff: `fällig` bleibt exakt `faktenfrische.faelligkeit` (und damit die Publish-Gate-Regel); der Vorlauf entscheidet nur, **wann gearbeitet** wird. Wer erst am Stichtag anfängt, arbeitet an einer roten Scorecard.

### 4. Reihenfolge: EDF statt Klassenrang

Die alte Auswahl sortierte nach Prioritätsklasse (saisonal/YMYL vor standard). Bei dauerhaftem Rückstand **verhungerten** die Standard-Seiten (90 Tage) unbegrenzt hinter den saisonalen (30 Tage), obwohl sie längst überfällig waren: Die Klasse war stärker als die Frist. Jetzt gilt **earliest deadline first** (Erstrecherche bleibt vorn) – die Reihenfolge, die nachweislich die wenigsten Fristen reißt. Als Regressionstest: `test_frueheste_frist_zuerst` (eine 200 Tage alte Standard-Seite kommt vor einer gerade fälligen saisonalen).

### 5. Eine Regel, zwei Leser (C19)

`faktenfrische.faelligkeit` liefert seit heute `frist` und `restlaufzeit`. Die Scorecard **liest** sie, statt „faktencheck + Intervall“ in `naechste_pruefung()` ein zweites Mal zu rechnen. Der Selbsttest ST8 friert beide Richtungen ein (`test_frist_gewinnt_gegen_abweichendes_intervall`).

### 6. Die Ursache steht im Ticket, im Report und im Siegel

- **Report:** neuer Abschnitt „Faktenfrische-Deckung“ vor den blockierenden Funden (`RELEASE-SCORECARD.md`).
- **Siegel:** `data/release_scorecard_state.json → kapazitaet`.
- **Ticket:** `release-scorecard.yml` liest die Zahlen aus dem Siegel (eine Rechnung, zwei Leser) und schreibt „Warum? Deckung der Faktenfrische“ mit Bedarf, Angebot, Deckung, Abbau-Tagen und dem Satz, wer entscheidet.

### 7. Der Bau wird rot, bevor der Bestand rot wird (Governance C45)

Die neue Regel C45 prüft **statisch**: `max_artikel_pro_lauf (Sockel) × Läufe/Tag ≥ Bedarf × min_deckung_prozent (110 %)`. Das harte Limit ist bewusst **nicht** die Prüfgröße: Eine Kadenz, die nur im Dauer-Spitzenbetrieb aufgeht, ist ein Dauer-Stau. Rückbauprobe gemacht – cron zurück auf Di+Do, C45 meldet „0,86/Tag gegen 2,84/Tag nötig“. Wächst der Bestand über die Kapazität, ist das ab jetzt ein **Bau-Befund mit Zahl** – und nicht Wochen später ein Rätsel-Ticket. Zusätzlich verlangt C45 Wache, SSOT-Blöcke, Fahrer im Workflow, `--wache` als Exit-Pfad, die Ursache in der Scorecard und einen Test.

### 8. Der Schließpfad (C14)

Der letzte Schritt des Workflows ist `faktenfrische_kapazitaet.py --wache`: Exit 1, wenn der Rückstand **nicht** binnen `planung.nachhol_frist_tage` (7) abbaubar ist. Der Job ist damit rot, solange die Maschine nicht nachkommt – und grün, sobald der Plan konvergiert. Kein Dauerzustand, kein stiller Ausfall.

## Abbauplan (berechnet, nicht geschätzt)

| Tag | fällig zu Beginn | Kapazität | erledigt | Rückstand danach |
|---|---|---|---|---|
| 30.10. | 14 | 3 | 3 | 11 |
| 31.10. | 11 | 3 | 3 | 8 |
| 01.11. | 8 | 3 | 3 | 5 |
| 02.11. | 5 | 3 | 3 | 2 |
| 03.11. | 2 | 3 | 2 | **0** |

(Simulation vom 29.10.2026, `abbau_tage = 5`, Frist 7. Steigt der Stau, hebt `auto_skalierung` das Budget bis 10 – deshalb ist der Plan auch bei einem Sammel-Prüfdatum stabil.)

Ab dem 03.11. ist der Bestand grün, **wenn** die Recherche je Seite gelingt. Gelingt sie nicht (Kanäle tot), bleibt das Datum absichtlich stehen – **kein Fake-Frischecheck**. Dann greift Exit 3 (`keine einzige Quelle erreichbar`) und der Lauf meldet es, statt grün zu lügen.

## Was ausdrücklich NICHT passiert ist

- **Keine Intervall-Lockerung.** `saison_tage 30 / ymyl_tage 45 / standard_tage 90` sind unverändert. Weniger messen wäre keine Heilung.
- **Keine Ausnahme, kein Wegklammern.** `data/release_scorecard.yaml` (Ausnahmen, Schwellen, Wirkungen) ist unangetastet.
- **Keine Heilung durch die Scorecard.** Sie bleibt ein Beweislauf (C15) und schreibt nur ihre eigenen Artefakte.
- **Kein erfundenes Prüfdatum.** Die 14 fälligen Seiten bleiben fällig, bis eine echte Recherche sie prüft.

## Belege (identische Umgebung, reproduzierbar)

```
python3 scripts/faktenfrische.py --selftest                 → ✅ 23/23 Fälle
python3 scripts/faktenfrische_kapazitaet.py --selftest      → ✅ 36/36 Fälle
python3 scripts/faktenfrische_kapazitaet.py                 → Deckung 116 %, Rückstand in 5 Tagen
python3 scripts/faktenfrische_kapazitaet.py --wache         → Exit 0 (Schließpfad offen)
python3 scripts/release_scorecard.py --selftest             → ✅ bestanden
python3 -m unittest scripts.tests.test_release_scorecard    → 44 Tests OK
python3 -m unittest scripts.tests.test_faktenfrische_kapazitaet → 33 Tests OK
python3 scripts/governance_contract.py --quick              → ✅ alle Regeln, C45 inklusive
```

**Offen im Rahmen dieses Vorgangs:** Der Live-Nachweis über `release_scorecard.py --live --streng` braucht den Hugo-Build (Beweisbasis `public/`); er läuft im Tages-Takt `release-scorecard.yml` und schließt #912, sobald der Abbauplan durch ist. Dieser Vorgang liefert die Mechanik und den Plan – nicht ein gefälschtes Grün.

## Bedienung

```bash
npm run faktenfrische:deckung                 # Bedarf, Angebot, Abbauplan
python3 scripts/faktenfrische_kapazitaet.py --wache   # Exit 1, wenn nicht abbaubar
python3 scripts/faktenfrische_kapazitaet.py --json    # maschinenlesbar
npm run test:faktenfrische                    # Selbsttests + 33 Unit-Tests
```

Runbook: `docs/ANLEITUNG-FAKTENFRISCHE.md` (Abschnitt „Deckung“) ·
`docs/ANLEITUNG-RELEASE-SCORECARD.md` (Abschnitt „Symptom oder Ursache?“) ·
Governance: `C45` in `scripts/governance_contract.py`.
