# Release-Scorecard #912 – der zweite Dauer-Alarm: F4 hatte keinen Schließweg

**Stand:** 03.11.2026 · **Branch:** `arena/83819bc8-franksfinanzcheck-blog` (Basis `b29c009`) ·
**Vorgang:** Issue #912 „Produktionswahrheit rot (Bestand blockiert)“ ·
**Vorgänger:** `RELEASE-SCORECARD-912-DAUERHEILUNG-PREMIUM-2026-10-29.md` (Kadenz),
`FAKTENFRISCHE-996-2026-11-02.md` (Fachbefunde)

---

## 1. Der Befund in einem Satz

Die Kadenz ist seit dem 29.10. geheilt (**0 überfällig, 146 % Deckung**) – und der
Bestand war am 02.11. trotzdem rot. Nicht das Faktenalter blockierte, sondern
**F4-fachbefund**: 42 offene Fachbefunde auf 10 live-Artikeln. Und dieser Befund
war **per Konstruktion unschließbar**: Er hing an einem Hash, den die eigene
Arbeit täglich verändert, während das Ticket behauptete, es gehe „ausschließlich
um die Faktenfrische“ und „danach schließt sich dieses Ticket selbst“.

Das ist kein Inhaltsproblem, das ist ein **fehlender Schließpfad** – und damit
genau der Dauer-Alarm, den Governance C14 verbietet.

### Die Kette, Ursache für Ursache

| Stufe | Was gemessen wurde | Warum das (allein) nicht reicht |
|---|---|---|
| 1 | 28.10.2026: 10 Artikel blockiert, alle „faktenalter“ | Symptom; die Dimension sagt nichts über den Check |
| 2 | 29.10.2026: Kadenz 33 % → täglich, Budget 4 · **C45** | heilt F1 – am 02.11. nachweislich grün (146 %) |
| 3 | 02.11.2026: weiter 10 Artikel rot | die Ursache war **F4**, nicht F1 – das Ticket sagte das Gegenteil |
| 4 | **03.11.2026:** F4 ist ein Befund ohne Entscheidungsweg | 21 von 57 Befunden an überholtem Text, 20 ohne Fassung → **mathematisch unschließbar** |

**Kernzahl vor der Heilung:** 57 offene Befunde auf 13 Seiten (42 davon auf 10
live-Artikeln); 21 mit `fassung_status = ueberholt`, 20 mit `ohne-fassung`,
0 `seite-fehlt`. Nur 4 der 13 Seiten hatten überhaupt eine entscheidbare
Textbindung (MATCH), 8 waren STALE, 3 legacy/STALE, 1 unbindbar
(`versicherungen` existiert nur im Ledger).

---

## 2. Die eigentliche Ursache: eine Entscheidung, die sich selbst löscht

Bis 02.11.2026 band **alles** an `pruef_hash`: Titel, Beschreibung, Kurzantwort,
**Quellen** und Text. Zwei Folgen:

1. **Die Maschine schreibt `quellen` selbst.** Jede legitime Quellenpflege änderte
   die „Fassung“ und entwertete eine bereits dokumentierte menschliche
   Entscheidung. Der Schließpfad wurde durch die eigene Arbeit gelöscht.
2. **Der Befund verlangt eine Textänderung – und die sperrt ihn.** Wurde der
   Text zur Heilung geändert (der Zweck des Befunds!), passte der alte Hash nicht
   mehr. Eine Entscheidung über den *neuen* Text konnte den *alten* Befund nie
   schließen.

Dazu kam der zweite Konstruktionsfehler: **ein Befund ohne Fassung** (`legacy-unbekannt`)
war überhaupt nicht entscheidbar, weil der Entscheid eine exakte Hash-Gleichheit
verlangte.

Und der dritte, der den Alarm zum Dauerläufer machte: Der Ticket-Text stand als
**Heredoc im Workflow** und behauptete bei jedem `faktenalter`-Fund „Kadenz,
kein Inhaltsbefund“. Am 02.11. war F1 grün, F4 die Ursache – das Ticket log
strukturell, jeden Tag, mit derselben Zeile.

---

## 3. Was jetzt gilt (die Heilung, nicht die Linderung)

### 3.1 Zwei Hashes, zwei Verträge – `scripts/faktenfrische_befund_ledger.py`

| Hash | Umfasst | Bindet |
|---|---|---|
| `pruef_hash` | Titel, Beschreibung, Kurzantwort, **Quellen**, Text | die KI-Antwort an die vollständige Prüffassung |
| `text_hash` | Titel, Beschreibung, Kurzantwort, Text | den Befund und die menschliche Entscheidung an die **Aussageflächen** |

- **Quellenpflege öffnet keine Entscheidung mehr.** Eine Textänderung öffnet sie
  – dann muss der Mensch die neue Aussage erneut anschauen. Genau diese Richtung
  ist gewollt.
- **Eine Entscheidung nennt beides:** `befund_fassung` (welcher Ledger-Eintrag)
  und `geprueft_fassung` (welcher Text gelesen wurde). Kein Raten, kein
  stilles Überschreiben.
- **`ohne-fassung` ist entscheidbar:** Alt-Befunde werden gegen den heutigen Text
  entschieden (`fassung_status = ohne-fassung`), statt für immer offen zu bleiben.
- **`ueberholt` ist entscheidbar:** Der Befund wird am heutigen Text entschieden
  und als solcher ausgewiesen – die Akte sagt es ausdrücklich („21 Befunde
  wurden an einem älteren Text erhoben; der Text wurde seither geändert“).
- **Die Maschine entscheidet weiterhin nie fachlich.** Sie prüft nur die Form:
  Person, Begründung (≥ 20 Zeichen), offener Befund, eindeutige ID, lesbare
  Seite – und schreibt atomar. Ohne diese Angaben schreibt sie **nichts**.

Befehl (der einzige Weg, einen Befund zu schließen):

```bash
python3 scripts/faktenfrische_befund_ledger.py --entscheiden <BEFUND-ID> \
  --von "Frank Hartung" \
  --begruendung "BDEW-Preis entfernt, 6-%-Wert an der Quelle verlinkt"
```

### 3.2 Eine Arbeitsliste, die man arbeiten kann – `scripts/faktenfrische_befund_akte.py`

`BEFUND-AKTE.md` (+ Siegel `data/faktenfrische_befunde_state.json`) wird aus
Ledger **und** Entscheidungen gebaut: je Seite ID, Typ, Alter, Fassungsstand,
Beanstandung, Beleg, Entscheidungsstatus und der fertige Befehl.

- **Frist & Eskalation** kommen aus der SSOT: `befunde.frist_tage` (14),
  `befunde.eskalation_tage` (21) in `data/agent_reach/faktenfrische.yaml`.
  Überfällige Befunde stehen oben; die Frist senkt keine Schwelle, sie bestimmt
  nur, **wer wann davon erfährt** (Herausgeber).
- `--wache` (Exit 1) prüft: jeder offene Befund hat einen dokumentierten
  Schließweg; Zählungen decken sich mit Ledger, Queue und Live-Bestand; die
  Fristen sind positive Zahlen.
- Das Siegel ist die einzige Zahlquelle für Ticket und Scorecard – **keine
  zweite Zählregel** (C19).

Aktueller Stand (live, 03.11.2026):

```
57 offene Befunde auf 13 Seiten (live: 42 auf 10 Artikeln)
ältester 4 Tage · Frist 14 Tage · über der Frist: 0
überholte Fassung: 21 · ohne Fassung: 20 · nicht entscheidbar: 0
```

### 3.3 Ein Siegel, das die Ursache nennt – `scripts/release_scorecard.py`

`durchfuehren()` schreibt jetzt zwei neue Blöcke ins Siegel:

- **`ursachen`** – je blockierendem CHECK: Dimension, Wirkung, `entscheidung`
  (`auto` / `human` / `redaktion`), `quelle`, betroffene Artikel, Anzahl.
- **`befundlage`** – offene Fachbefunde: Anzahl, Seiten, live-Befunde,
  überholte Fassungen, Fassungslose, Alter, Frist, über der Frist, je Slug.

Beides wird aus **denselben Collectoren** gezählt, die auch blockieren – die
Dimension ist nur noch die Landkarte, der Check ist die Adresse. Der Bericht
gliedert entsprechend:

1. Gesamtergebnis je Dimension
2. Live-Bestand artikelweise
3. **Was blockiert – nach Prüfung, nicht nach Dimension**
4. **Offene Fachbefunde (F4)** – Zahl, Alter, Frist, Arbeitsdatei, Befehl
5. **Faktenfrische-Deckung** – und der Satz, der vorher fehlte: „F1 ist nicht
   die Ursache: rot ist der Inhalt, nicht der Takt“ (bzw. „Zusätzlich ist F1
   blockiert“, wenn beides gilt)
6. Blockierende Funde artikelweise

### 3.4 Ein Ticket, das eine getestete Funktion ist – `scripts/scorecard_ticket.py`

Der Heredoc ist weg (`.github/workflows/release-scorecard.yml` enthält keine
Zeile Ticket-Text mehr). Der Text entsteht aus dem Siegel und wird geprüft:
Ursache je Check, Besitz, betroffene Artikel, Befundalter, Frist, Arbeitsdatei,
Schließbefehl.

| Behauptung im alten Ticket | Wahrheit am 02.11. | heute |
|---|---|---|
| „ausschließlich die Faktenfrische“ | F1 war grün (146 %) | nur zulässig, wenn F1 wirklich blockiert |
| „ein Kadenz-Befund, kein Inhaltsbefund“ | 42 Fachbefunde offen | nur zulässig, wenn keine F4-Funde zählen |
| „danach schließt sich dieses Ticket selbst“ | nichts schloss sich | Schließpfad = dokumentierte Entscheidungen |

### 3.5 Der Alarm schließt sich – `.github/workflows/faktenfrische.yml`

- Schritt „Befundakte schreiben“ (vor dem Commit), `BEFUND-AKTE.md` und das
  Siegel werden mitcommittet.
- Schritt „Befundakte-Wache“: ein Befund ohne Schließweg macht den Job rot.
- **Genau ein** Ticket „Offene Fachbefunde (F4) – Redaktionsakte“: wird
  aktualisiert, nicht dupliziert, und **geschlossen**, sobald kein Befund mehr
  offen ist (C14: Alarm nur mit Schließweg).
- Der bisherige Tagesdatum-Titel („… 03.11.“) entfällt – er hätte jede Woche
  ein neues, ewig offenes Ticket erzeugt.

### 3.6 Governance C46 – damit das nicht zurückkommt

Neue Regel in `scripts/governance_contract.py` (45 Regeln, `docs/GOVERNANCE-KONTRAKT.md`
regeneriert):

> **C46** Jeder offene Fachbefund ist entscheidbar: Befund und Entscheidung
> hängen am TEXT-Hash (ohne Quellen), die KI-Prüfung weiterhin an der
> vollständigen Prüffassung. Eine Entscheidung nennt `befund_fassung` UND
> `geprueft_fassung` … `--entscheiden` schreibt die Entscheidung,
> `BEFUND-AKTE.md` ist die Arbeitsliste mit Frist und Fassungsstand, und das
> Scorecard-Ticket ist eine getestete Funktion des Siegels: Es nennt die Kadenz
> nur, wenn F1 wirklich blockiert – nicht bei F4.

C46 prüft statisch (Marker in Ledger, Akte, SSOT, Workflows, Ticket, Scorecard,
beiden Testdateien, `GUARDS`/C6) **und** live (`faktenfrische_befund_akte.py
--wache`; unter `--quick` übersprungen). Die falsche Ursachenbehauptung ist als
verbotene Zeichenkette hinterlegt – sie darf in `scorecard_ticket.py` und im
Scorecard-Workflow nicht mehr vorkommen, auch nicht im Docstring.

**Rückbauprobe** (so ist C46 belegt, nicht nur behauptet):

| Sabotage | C46 sagt |
|---|---|
| `text_hash` aus dem Ledger entfernt | „`def text_hash(` fehlt – ohne Textbindung …“ |
| `befunde.frist_tage` aus der SSOT gelöscht | „`befunde.frist_tage` fehlt oder ist keine positive Zahl“ |
| `--entscheiden` im Ledger umbenannt | „`--entscheiden` fehlt – ohne Befehl kein Schließweg“ |
| alte Ticket-Zeile wieder eingesetzt | „verbotene Ursachenbehauptung … im Ticket-Text“ |
| Akte-Schritt aus dem Workflow entfernt | „`BEFUND-AKTE.md` wird nicht geschrieben/gecommittet“ |

---

## 4. Nachweis (was tatsächlich gelaufen ist)

| Prüfung | Ergebnis |
|---|---|
| `governance_contract.py --quick` | ✅ **erfüllt – alle 45 Regeln** |
| `governance_contract.py --selftest` | ✅ C1–C47 mit Kunstbefunden (Fehler erkannt, gutes Setup still) |
| `faktenfrische_befund_ledger.py --selftest` / `--wache` | ✅ (zwei Hashes, Quellenpflege öffnet nicht, Altbestand entscheidbar) / ✅ 57 offen, 21 überholt, 20 ohne Fassung |
| `faktenfrische_befund_akte.py --selftest` / `--wache` | ✅ / ✅ „Jeder offene Befund hat einen dokumentierten Schließweg“ |
| `release_scorecard.py --selftest` | ✅ (SSOT-Form, Scheingrün-Schutz, Exit-Vertrag, Terminrechnung) |
| `scorecard_ticket.py --selftest` | ✅ (F4 ohne Kadenz-Behauptung, ehrlicher Schließpfad) |
| `faktenfrische.py --selftest` | ✅ 29/29 |
| Unit-Tests (Ledger, Akte, Ticket, Scorecard, Kapazität, Publish-Gate) | ✅ **128 Tests OK** |
| Workflow-YAML (`faktenfrische.yml`, `release-scorecard.yml`) | ✅ `yaml.safe_load`, 14 bzw. 10 Schritte |

Neu abgesichert:

- `scripts/tests/test_faktenfrische_befund_akte.py` – Zwei-Hash-Bindung,
  überholter und fassungsloser Text entscheidbar, **keine** Entscheidung ohne
  Person/Begründung, echtes SHA-256 in `geprueft_fassung`, Akte-Inhalt, Frist,
  Live-Siegel gegen Queue.
- `scripts/tests/test_scorecard_ticket.py` – F4- vs. F1-Ursache, Eskalation,
  ehrlicher Schließpfad, kein Selbstschluss, Workflow-Verdrahtung.
- `scripts/tests/test_release_scorecard.py` (+3) – der Bericht nennt F4 als
  Ursache und **nicht** die Kadenz; F1 wird getrennt als zusätzliche Ursache
  ausgewiesen; überholte Fassungen werden erklärt.

---

## 5. Was rot bleibt – und warum das richtig ist

**42 offene Fachbefunde auf 10 live-Artikeln bleiben offen.** Kein Skript der
Welt darf sie schließen: Es sind fachliche Aussagen (Superlative ohne Beleg,
Preisangaben ohne Quelle, Werbeversprechen). Genau das ist die Grenze
„Maschine entscheidet nie fachlich“.

Was sich geändert hat: Der Weg ist **einer**, er ist **dokumentiert**, er ist
**in 14 Tagen fällig** und er ist **ein Befehl**:

1. `BEFUND-AKTE.md` öffnen (oder das Ticket „Offene Fachbefunde (F4)“).
2. Je Befund: Zahl belegen oder entfernen, Aussage präzisieren – oder fachlich
   begründet zurückweisen.
3. `--entscheiden <ID> --von "<Name>" --begruendung "<≥ 20 Zeichen>"`.
4. `faktenfrische_befund_akte.py --schreiben`, dann
   `release_scorecard.py --live --streng`.

Wenn die 42 weg sind, ist F4 grün, das Scorecard-Ticket schließt sich selbst
**weil dann nichts mehr blockiert** – nicht, weil Zeit vergangen ist.

### Zwei ehrliche Nebenbefunde

1. **`scripts/tests/test_faktenfrische_996.py` ist seit dem 02.11. rot (2 von 4
   Tests)** – nicht durch diese Arbeit, sondern bereits auf `b29c009`
   nachgewiesen (Worktree-Probe). Grund: zwei `pin_description`-Zeilen werben
   weiter mit „Der Spätsommer ist die **beste Zeit** für den Gaswechsel“
   (`2026-08-14-gasrechnung-senken-…`, `2026-08-24-preisgarantie-gas-…`), obwohl
   der 996-Rückfallschutz genau das verbietet. Das ist **redaktioneller Text**
   und ändert den Artikel-Hash (Release-Siegel) – deshalb hier nicht
   mitgeändert, sondern benannt. Der Test bleibt scharf; die Zeile wird
   redaktionell ersetzt, dann neu versiegelt – eigener Vorgang:
   **Issue #1036** (`qualitaet`).
2. **`python3 scripts/release_scorecard.py --live --streng` lief hier nicht
   vollständig**, weil im Sandbox kein `hugo` und kein `public/` existiert
   (`M2-siegel-bindung`/`T7-render-beweis` brauchen den Build). Die
   Berichtswege wurden stattdessen mit einem konstruierten Siegel end-to-end
   gerendert (Abschnitte 3.4/3.5 im Test), der Live-Lauf passiert im
   Workflow `release-scorecard.yml` um 05:07 UTC.

---

## 6. Dateien

| Datei | Änderung |
|---|---|
| `scripts/faktenfrische_befund_ledger.py` | zwei Hashes, `fassung_status`, `befunde_mit_status`, `--entscheiden`, `--wache`, `--nachlese` |
| `scripts/faktenfrische.py` | `text_sha256` in Lauf, Dossier und Ledger-Merge |
| `scripts/faktenfrische_befund_akte.py` | **neu** – Arbeitsliste + Siegel, `--schreiben`, `--wache`, `--selftest` |
| `scripts/scorecard_ticket.py` | **neu** – einzige Ticket-Textquelle |
| `scripts/release_scorecard.py` | `ursachen_ermitteln`, `befundlage_ermitteln`, Siegel + Berichtsgliederung |
| `scripts/governance_contract.py` | **C46**, `GUARDS` erweitert, `LABEL`/`RULE_TEXT` |
| `.github/workflows/faktenfrische.yml` | Akte + Akte-Wache, ein Ticket, Sammel-Rotfall |
| `.github/workflows/release-scorecard.yml` | Ticket aus Skript, ein FID-Marker |
| `data/agent_reach/faktenfrische.yaml` | `befunde.frist_tage: 14`, `befunde.eskalation_tage: 21` |
| `package.json` | `faktenfrische:akte`, `faktenfrische:befunde`, Tests erweitert |
| `docs/ANLEITUNG-FAKTENFRISCHE.md` | Schließpfad neu geschrieben (Befehl statt YAML-Handwerk) |
| `docs/ANLEITUNG-RELEASE-SCORECARD.md` | Lehre 03.11.: F1 misst den Takt, F4 den Inhalt |
| `docs/GOVERNANCE-KONTRAKT.md` | regeneriert (C45, C46) |
| `scripts/FAKTENFRISCHE.md`, `.claude/skills/ff-ausliefern/references/alarme-und-scorecard.md` | Betriebs-Anleitung nachgezogen |
| `BEFUND-AKTE.md`, `data/faktenfrische_befunde_state.json` | erzeugt (57/13/42, Frist 14) |
| `scripts/tests/test_faktenfrische_befund_akte.py`, `test_scorecard_ticket.py` | **neu** (11 + 12 Tests) |
| `scripts/tests/test_release_scorecard.py` | +3 Berichtstests |

---

## 7. Merksatz

> **F1 misst den Takt, F4 den Inhalt.** Ausreichende Kapazität ist kein
> Inhaltsbeweis, und ein Fachbefund ist kein Kadenz-Artefakt. Ein Alarm ohne
> Schließweg ist keine Warnung, sondern eine unbezahlte Rechnung – und ein
> Ticket, das die Ursache falsch nennt, verlängert sie täglich.
