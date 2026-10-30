# ANLEITUNG: Release-Scorecard – die Produktionswahrheit

> **Auftrag (03.10.2026, Audit-Befund 10 „Der Produktionsprozess ist sehr
> komplex“):** „Ich würde daraus eine einzige sichtbare Release-Scorecard
> machen … Bitte dauerhaft auf Highend-Level einer Profi-Agentur beheben.“

Die Scorecard ist der **eine Wahrheitsort** über den Veröffentlichungsprozess.
Pro Artikel, eine Zeile, acht Dimensionen:

| Dimension | Zielwert | Gemessen durch |
|---|---|---|
| Technik | bestanden | Länge, SEO-Audit, Titel R5, Keywords, Lesbarkeit, Textverständnis, Render-Beweis |
| Quellen | bestanden | Belegkette (E12) bzw. Quellen-Vorhandensein |
| Faktenalter | bestanden | faktenfrische-Intervalle, Stand-Kennzeichnung (E16), Prüfdatum (E09) |
| Affiliate-Integrität | bestanden | AI1–AI4 + Render-Beweis, IW0–IW9, O1–O7, A1–A8 |
| Redundanz | bestanden | Duplikat-Wache D1–D6 + Phrasen-Einzigartigkeit U1–U2 (seit #714) |
| YMYL-Risiko | geprüft | Risikoklassifikation + Prüfprotokoll |
| menschliche Freigabe | vorhanden | redaktionelle Prüfung mit Siegel (nur Risikoklasse hoch) |
| nächste Überprüfung | Datum | Review-Termin bzw. faktencheck + Intervall |

---

## Die sechs Fragen der Produktionswahrheit

### 1. Welche Checks blockieren Veröffentlichung?

**Alle Checks mit `wirkung: blockiert` in `data/release_scorecard.yaml`.**
Das ist keine Behauptung, sondern maschinell durchgesetzt:

- Regel **C19** (`scripts/governance_contract.py`) prüft bei jedem Lauf, dass
  jede **harte Gate-Familie des Publish-Gates** dort als blockierend
  deklariert ist. Wer eine blockierende Prüfung zur Warnung herabstußt oder
  aus der SSOT löscht, bricht den Build.
- Der **Deploy** läuft die Scorecard hart über die heutigen Live-Kandidaten
  (`deploy.yml` → „Release-Scorecard (Produktionswahrheit versiegeln,
  fail-closed)“): Exit 1 stoppt die Auslieferung.
- Das **Publish-Gate** verwirft/verparkt Kandidaten mit harten Funden – auch
  Redundanz D1–D6 über `publish_gate.duplicate_failures` und – seit #714
  (12.10.2026) – Phrasen-Einzigartigkeit U1–U2 über
  `publish_gate.uniqueness_failures` (derselbe Collector wie das tägliche
  Einzigartigkeits-Audit, `check_uniqueness.kandidaten_befunde`). Die
  Scorecard liest exakt diese Collectoren; eine eigene Duplikat- oder
  Einzigartigkeits-Schleife ist ausdrücklich verboten.

### 2. Welche Checks liefern nur Warnungen?

**Alle Checks mit `wirkung: warnung`** – aktuell:

- `T1w-zeichenlaenge-optimum`: Länge außerhalb des Optimums (12.000–18.000),
  aber über dem Floor. Der Befund nennt die Richtung:
  `unter-optimum` (< 12.000) oder `ueber-optimum` (> 18.000, bis zur harten
  Grenze 22.000)
- `Q2-quellen-vorhanden`: Artikel ohne Belegkette (Risikoklasse standard/
  erhöht – für „hoch“ ist Q1 hart)

Warnungen stehen im Report und im Ticket-Body, stoppen aber weder Deploy noch
Veröffentlichung. Sie werden nie „weggeklammert“.

### 3. Wer entscheidet bei fachlichen Konflikten?

Die Eskalationsmatrix steht deklariert in `data/release_scorecard.yaml` unter
`eskalation`:

| Konflikt | Entscheidung |
|---|---|
| **Technisch** (Gate rot bei anderem grün, Werkzeugfehler) | Der Gate-Vertrag entscheidet: fail-closed. Besitz: `auto`. Weg: Selbsttest der Wache → Issue im Kanal der Wache → `bot_watchdog --route` |
| **Fachlich** (Quellenlage, Bewertung, Formulierung) | **Herausgeber Frank Hartung** entscheidet als Chefredaktion. Weg: Befund mit `owner=human` (C14) → Entscheidung im `aenderungsgrund` dokumentieren → bei Risikoklasse hoch neu versiegeln. **Die Maschine entscheidet fachlich nie.** |
| **Messung** (Scorecard ≠ Publish-Gate) | Konstruktiv unmöglich (gleiche Collector-Funktionen) – eine Abweichung ist immer ein Defekt: Deploy stoppt, P1-Vorfall |

Jeder Check trägt außerdem `entscheidung: auto|human` – das ist der Besitz
im Alarm-Routing-Sinn (C14).

### 4. Was passiert bei falschen Positivmeldungen?

Zwei Richtungen, beide abgedeckt:

**Scheingrün (Gate meldet „bestanden“, obwohl mangelhaft):**

1. **Keine zweite Messregel:** Die Scorecard misst über *dieselben*
   Collector-Funktionen wie das Publish-Gate (`publish_gate.check_length_failures`
   … `textverstaendnis_failures`, `duplicate_failures`,
   `editorial_review_gate.evaluate_path`, `faktenfrische.faelligkeit`). Andere Ampeln für dieselbe
   Messung sind ausgeschlossen; eine Abweichung ist per Definition ein
   Defekt in einer der beiden Ketten (P1, Deploy stoppt).
2. **Fail-closed:** Kann ein Beweis nicht geführt werden (kein `public/`,
   toter Build, Detektor veraltet), lautet das Ergebnis **„nicht beweisbar“**
   – niemals „bestanden“ (Exit 2, Werkzeugfehler).
3. **C19:** Eine harte Gate-Familie kann nicht unbemerkt aus der
   Produktionswahrheit verschwinden.
4. **Vollständige Matrix:** Ein Check, der für einen Artikel hätte laufen
   müssen, aber kein Ergebnis lieferte, zeigt „nicht beweisbar“ – eine leere
   Messung ist nie grün (eingefroren im Selbsttest ST6).

**Falscher Alarm (Check blockiert zu Unrecht):**

- Nie durch Schwächung des Gates. Stattdessen: **befristete Ausnahme** in
  `data/release_scorecard.yaml` unter `ausnahmen` mit Pflichtfeldern
  `slug`, `check`, `begruendung` (≥ 15 Zeichen), `gueltig_bis` (ISO-Datum),
  `entschieden_von`.
- Eine Ausnahme stuft den Fund auf **warnung** zurück – nie auf grün – und
  wird im Report mit Ablaufdatum und Unterschrift sichtbar.
- **Abgelaufene Ausnahmen wirken nicht** und werden gemeldet (stille
  Verlängerung gibt es nicht).
- **Nicht ausnehmbar:** `M2-siegel-bindung` und `T7-render-beweis` – Siegel
  und Build-Beweis gelten ausnahmslos, sonst wäre die Antwort auf Frage 6
  eine Ausnahme von der Wahrheit.

### 5. Wie wird ein Artikel fachlich freigegeben?

**Risikoklasse „hoch“** (Baufinanzierung, Altersvorsorge, Kredite,
Versicherungen – automatisch klassifiziert, Herabstufung verboten):

1. Belegkette im Frontmatter: `quellen` (≥ 2, davon eine Rang 1/2, HTTPS,
   kein Affiliate-Partner als Beleg)
2. `gepruefte_aussagen`: Kernaussagen mit exakten Textankern → Prüfergebnis →
   Quellen-IDs
3. `gepruefte_zahlen`: Zahlen mit Fundstelle, Prüfergebnis,
   Konsistenzprüfung, Rechenweg
4. `redaktionelle_pruefung`: Prüfer (Name, Rolle, Typ `fachpruefer` oder
   `redaktion-mit-externer-belegkette`), `pruefdatum`, `aenderungsgrund`,
   `naechste_pruefung`
5. `status: "freigegeben"` setzen
6. Versiegeln: `python3 scripts/editorial_review_gate.py --seal --file <pfad>`
   (setzt `inhalt_sha256`, schreibt die Audit-Historie)
7. Jede spätere Änderung an Text, Protokoll oder Quellen **bricht das Siegel**
   (E17) → neu prüfen und neu versiegeln.

**Risikoklasse „standard“/„erhöht“:** Zwei Bahnen (Issue #521) – die harte
Gate-Kette **ist** die dokumentierte Freigabe (AUTO-Bahn). Stellt sich ein
Artikel nachträglich als YMYL-hoch heraus, greift das fail-closed
`editorial_review_gate` sofort. Die Scorecard zeigt hier ehrlich
„nicht erforderlich“ statt einer erfundenen menschlichen Freigabe.

### 6. Wie ist nachgewiesen, dass die veröffentlichte Version geprüft wurde?

**Das Release-Siegel** (nicht zu verwechseln mit dem YMYL-Freigabe-Hash):

- Beim **Deploy** versiegelt die Scorecard jeden Live-Artikel:
  **SHA-256 über die exakte Quelldatei** + alle acht Dimensionen + Urteil +
  Zeitstempel + **Deploy-Commit**.
- Ablage: `data/release_scorecard_state.json` (aktueller Siegel-Zustand),
  `data/release_scorecard_history.jsonl` (append-only Verlauf, ein Eintrag
  je Lauf mit freigabe-reif/warnung/blockiert und Kandidaten),
  `data/audit/` (Audit-Event je Lauf).
- **Drift-Erkennung:** Ändert sich eine Artikel-Datei nach der Versiegelung,
  zeigt der nächste Lauf `siegel_drift: "geändert – neu geprüft"` – der
  Artikel wurde mit dem neuen Stand neu gemessen und neu versiegelt. Was
  niemals passieren kann: eine geänderte Version, die noch das alte Siegel
  trägt (der Hash stimmt dann schlicht nicht).
- Nachweis einsehen:
  `python3 scripts/release_scorecard.py --slug <slug>` zeigt Siegel-Hash,
  Dimensionen und Drift-Status.

---

## Betrieb

```bash
npm run release:scorecard        # Live-Bestand messen + Report + Siegel (Berichtsmodus)
npm run release:bestand          # dito, aber Bestands-Rot = Exit 1 (Tageswache)
npm run release:artikel -- <slug>  # Einzelnachweis für einen Artikel
python3 scripts/release_scorecard.py --kandidaten   # Deploy-Modus (hart)
python3 scripts/release_scorecard.py --json         # maschinenlesbar
npm run test:release             # Selbsttest + 41 Unit-Tests
```

**Exit-Code-Vertrag:** `0` = freigabe-reif · `1` = blockierende Funde im
Scope · `2` = Werkzeugfehler (fail-closed).

### Symptom oder Ursache? Die Deckungszeile (#912, 29.10.2026)

Zwischen dem 20. und dem 28.10.2026 war der Bestand siebenmal rot (12 von 20 Läufen), immer mit
derselben Zeile: **Faktenalter blockiert**. Das Ticket #912 ließ sich nicht
schließen, weil es nur das Symptom nannte. Die Ursache war eine Rechnung, die
niemand angestellt hatte: Der Bestand braucht 2,58 Faktenprüfungen je Tag, der
Bestands-Takt lieferte 0,86 – **33 % Deckung**. Jede Woche wurden zwölf Seiten
mehr überfällig als geprüft.

Der Report nennt seitdem vor den blockierenden Funden einen eigenen Abschnitt
**„Faktenfrische-Deckung“**, und `data/release_scorecard_state.json` trägt die
Zahlen unter `kapazitaet` (das Ticket liest sie von dort – eine Rechnung, zwei
Leser). Er steht **nur**, wenn es Faktenalter-Funde gibt oder die Messung
scheitert.

| Spalte | Bedeutung |
|---|---|
| Bedarf | Σ 1/Intervall über den Bestand (aus `faktenfrische.faelligkeit`) |
| Angebot | Budget je Lauf × Läufe je Tag (aus dem echten cron) |
| Deckung | Angebot ÷ Bedarf – unter 100 % wächst der Rückstand zwangsläufig |
| Rückstand abgebaut | Tage bis zum leeren Rückstand (Frist: `planung.nachhol_frist_tage`) |
| Nächste Frist | Die Seite, die als nächste rot würde – die Zahl für die Planung |

Was daraus folgt, ohne nachzudenken:

- **Deckung < 100 %** → das ist keine Inhaltskrise, sondern eine Kadenz-Frage
  (`data/agent_reach/faktenfrische.yaml`, Governance C45). Nicht die Intervalle
  senken – die Lieferung erhöhen.
- **Deckung ≥ 100 %, trotzdem rot** → F1 (Alter), F4 (offener Fachbefund)
  und die übrigen Checks getrennt lesen. Ausreichende Kapazität beweist
  weder eine erfolgreiche Prüfung noch eine inhaltliche Freigabe.
- **`nicht beweisbar`** → Bedarf oder Laufplan waren nicht lesbar. Das ist ein
  Werkzeugfehler (Exit 2), kein Freibrief.

**Nachzug 30.10.2026 (#912):** Die Deckung wird über 120 echte Kalendertage
simuliert, nicht aus einem Wochenmittel abgeleitet. Gearbeitet wird nur an
cron-Tagen mit ganzzahligem Tagesbudget; Folgefrist ist Prüftag + Intervall.
Bericht und Automatik verwenden bei Auto-Skalierung dasselbe empfohlene
Budget. Zusätzlich blockiert **F4-fachbefund** jeden offenen Fachbefund ohne
menschliche, fassungsgebundene Entscheidung. Ein neues `faktencheck` allein
schließt diesen Befund nicht. Schließpfad:
`docs/ANLEITUNG-FAKTENFRISCHE.md`, Abschnitt „Befund redaktionell schließen“.

**Takt:**

| Takt | Wo | Wirkung |
|---|---|---|
| Jeder Deploy | `deploy.yml`, nach allen Content-Gates, vor der Auslieferung | hart: Exit ≠ 0 stoppt die Veröffentlichung; versiegelt den Bestand |
| Täglich 07:07 MESZ | `release-scorecard.yml` | Bericht + Siegel + Historie; bei Rot genau ein Ticket (C4/C12/C14), bei Grün Schließen |

**Wichtig für Agenten:**

- Die Scorecard **heilt nie** (Beweislauf, C15). Sie setzt
  `publish_gate.DRY_RUN = True`, damit auch die Intent-Wache im Scorecard-Lauf
  nichts schreibt.
- Neue Checks gehören **immer** zuerst in `data/release_scorecard.yaml`
  (deklarative Wahrheit), sonst meldet C19 rot. Ein Fund einer nicht
  deklarierten Prüfung blockiert laut, statt still zu verschwinden.
- Ein neuer `E`-Code in `editorial_review_gate.py` braucht ein Mapping in
  `release_scorecard.ERG_CODE_ZU_CHECK` – unbekannte Codes sind Fehler, nie
  Still (eingefroren im Selbsttest ST5).

### Bestands-Reparatur (wenn die Tageswache rot meldet)

Die Wache meldet; die **Redaktion** heilt (Vorgang #732, 13.10.2026). Fester
Weg für blockierende Bestandsbefunde – nie durch Ausnahme oder Schwächung:

1. **Befund klären:** `python3 scripts/release_scorecard.py --slug <slug>`
   nennt Check, Detail und Siegel-Drift. Für Roh-Messwerte:
   `readability_check.py --file …`, `textverstaendnis_guard.py --json`.
2. **Deterministische Heiler zuerst probieren** (alle fail-closed, schreiben
   nur beweisbar besseren Text):
   `r5_absatz_splitter.py --apply --file …` (Absätze > 4 Sätze),
   `politur_heiler.py` (R14–R16, adjacentes R15),
   `lesbarkeit_heiler.py --file … --auch-live --keine-ki` (Flesch-Klasse;
   Stufe A + Tor T1–T4). Scheitert das Tor, bleibt die Datei byte-identisch –
   dann ist Handarbeit angesagt (R15 nicht-adjacent, Flesch unter
   Silben-Hebeln, fachliche Umformulierung).
   `abbildungen_ableiten.py` (Merkkarte/Gliederung samt artikelgenauer
   Bildzeile; `--check` beweist Einbindung, Artikelgenauigkeit und
   Eindeutigkeit). Bildzeilen sind Metadaten: Sie tragen den Titel, aber
   keine Beträge – Zahlen gehören in den Text, wo der YMYL-Prüfpfad sie
   sieht (sonst wandern ungeprüfte Werte in `fachpruefung_register.yaml`).
3. **Redaktionelle Regeln beim Handarbeiten:** Zahlen-Multiset, Linkziele,
   Tabellen, Überschriften unverändert; Absätze ≤ 4 Sätze; Passiv meiden;
   Flesch-Amstad ≥ 60 (besser ≥ 62); eine Idee pro Absatz. Für
   Längen-Nachführung (T1w) eignen sich FAQ-Antworten im Artikelstil –
   einzigartig formulieren (R15/U1 prüfen!). Quellen (Q2) nur aus der
   etablierten Korpus-Belegkette nachpflegen, nie erfinden.

   **T1w in Richtung `ueber-optimum` ist kein Kürzungsauftrag.** Ein Beitrag
   über 18.000 Zeichen wird nur gekürzt, wenn der Flesch-Wert dabei ≥ 60
   bleibt – sonst tauscht die Kürzung einen Hinweis gegen einen echten
   Befund. Beim Bestandsdurchgang vom 24.10.2026 (#824) lagen genau zwei
   Beiträge über dem Optimum; beide wurden redaktionell verdichtet, ohne den
   Flesch-Wert zu senken:

   | Beitrag | Zeichen | Flesch |
   |---|---|---|
   | `2026-09-07-frugalismus-tipps-so-vermeidest-du-teure-alltagsfehler` | 18.331 → 17.854 | 62,1 → 61,9 |
   | `2026-09-30-last-minute-urlaub-so-schnappst-du-dir-das-sommer-schnaepp` | 18.849 → 17.949 | 60,6 → 61,0 |

   Gestrichen wurden ausschließlich Doppelungen: im Last-Minute-Beitrag ein
   zweiter Absatz zur Flexibilität (der Abschnitt darunter sagt dasselbe),
   eine Füllzeile nach der Checkliste und zwei aufeinanderfolgende
   Zusammenfassungen; im Frugalismus-Beitrag ein Absatz, der den „großen
   Hebel“ ein zweites Mal erklärte, und die Erklärung der Plan-Reihenfolge,
   die die Tabelle darüber selbst trägt. Zahlen, Quellen, Links und
   Überschriften blieben unverändert.
4. **Nachweis führen, dann versiegeln:** Gate-Collectoren im Trockenlauf über
   die geänderten Slugs (T4/T5/T6/RD1/RD2 + `editorial_review_gate`), dann
   `python3 scripts/release_scorecard.py` (misst neu, aktualisiert Report,
   Siegel `data/release_scorecard_state.json`, Historie, Audit).
   `--live --streng` muss Exit 0 liefern.
5. **Nie tun:** `ausnahmen` in der SSOT ohne Ablaufdatum/Unterschrift,
   Schwellen absenken, zweite Messregel einführen, Scorecard-Artefakte von
   Hand editieren.

## Zusammenhang mit den anderen Scorecards

| Instrument | Frage | Takt |
|---|---|---|
| **Release-Scorecard** (diese) | Ist JEDER Artikel veröffentlichungsfähig – und die veröffentlichte Version geprüft? | Deploy + täglich |
| `editorial_scorecard.py` | Wie gesund ist das BLATT (Kadenz, CWV, Umsatz, Decay)? | wöchentlich |
| `PRODUKTIONS-STATUS.md` | Liefert die Content-Engine ihr Tagesziel? | je Engine-Lauf |

Die Release-Scorecard ersetzt keines davon – sie ist die einzige
**artikelgenaue** Freigabe-Wahrheit.
