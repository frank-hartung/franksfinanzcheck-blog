# Produktions-Wache · Content-Engine · Vorgang WACHE-609 (#609) — Dauerheilung auf Premium-Niveau

**Datum:** 07.10.2026 · **Issue:** #609 („Produktions-Wache: Content-Engine liefert nicht (P2)", Label `produktions-wache`)
**Workflow:** `.github/workflows/produktions-wache.yml` (Meldung vom 06.10.2026 01:15 UTC, Lauf `37398240858`)
**Reparatur-Vorschlag:** PR #619 („Closes #609") · **Vorgänger:** #585 (Lesbarkeits-Gate), #601 (Tagesdefizit 05.10.), #590 (Synchronverlust), #594 (Blocker-Klassen), #608 (Zustandskanal)

## Kurzfassung

#609 war **kein Engine-Ausfall und kein Key-Problem**. Der Befund hat zwei
Hälften – und die erste („am 05.10. nur 1/2") war die Folge der zweiten:

> Der Reserve-Vorrat stand bei **Ziel 6 / bereit 2**. **Sieben Kandidaten waren
> allein am harten Lesbarkeits-Gate geparkt** (Flesch 53,1–59,9; Schwelle
> `readability_check.NEW_FLESCH_MIN` = 60,0 seit #585), ein achter am
> Textverständnis. Die Heiler-Deckung führte die Regel trotzdem als „gedeckt",
> weil `profi_polish.py` in der Kette stand. **Ein Name in der Kette ist eine
> Behauptung – die Wirkung fehlte.**

Der Vorrat ist der Puffer, aus dem ein verpasster Slot (#601) oder ein
Synchronverlust (#590) aufgefüllt wird. Mit 2/6 bereiten Kandidaten und sieben
strukturell unerreichbaren Texten gab es für den 05.10. keinen Puffer – der Tag
endete 1/2, die Wache öffnete #609.

Die Dauerheilung schließt die Lücke **an der Wurzel**: Der fehlende Heiler der
Klasse existiert jetzt, seine Wirkung ist Maschinenvertrag, er läuft in
Reserve- und Live-Kette, seine Holds werden rearmt – und eine
Governance-Regel hält es fest.

## Befund

### Was die Wache gemeldet hat (Zitat, gekürzt)

> **Stufe:** P2 · **Befund:** Am letzten Publikationstag (2026-10-05) nur 1/2
> Artikel – unter Mindestziel. – Bestand: 2 von Gates gehalten (ältester
> 1 Tage: publish-gate: Lesbarkeits-Gate nicht bestanden: Flesch 44.4
> (Mindestwert 60) – ein Artikel unter dieser Schwelle zieht den
> Bestands-Durchschnitt nach unten (#585); Textverständn…)

Der Rest des Bodys: Heute 2026-10-06 (Dienstag, Ruhetag) · LIVE gesamt 38 ·
förderfähig in der Re-Queue 0 · von Gates gehalten 2 · Mindestziel 2/Tag.
`PRODUKTIONS-STATUS.md` stand um 06.10. 23:43 UTC weiter auf **P2**.

### Die zweite Hälfte: der Vorrat (`data/reserve-readiness.json`, 07.10. 11:11:50 UTC)

| Kennzahl | Wert |
|---|---|
| Ziel | **6** |
| bereit | **2** |
| Pool | 12 |

Nicht bereit – und warum:

| # | Kandidat (Slug, gekürzt) | Blocker |
|---|---|---|
| 1 | `2026-10-07-dein-weg-zu-geringeren-monatskosten…` | Lesbarkeits-Gate: Flesch 57,9 (Mindestwert 60) |
| 2 | `2026-10-07-dsl-anbieter-wechseln…` | Lesbarkeits-Gate: Flesch 59,4 |
| 3 | `2026-10-07-haushaltskosten-reduzieren…` | Lesbarkeits-Gate: Flesch 59,9 |
| 4 | `2026-10-07-stromkosten-senken…` | Lesbarkeit: Score 70/100 (Flesch 52), 2 Absätze zu lang |
| 5 | `2026-10-07-urlaub-sparen…` | Lesbarkeits-Gate: Flesch 58,8 |
| 6 | `2026-10-07-vpn-zuhause…` | Lesbarkeits-Gate: Flesch 55,8 |
| 7 | `2026-10-07-waermepumpe-vs-gasheizung…` | Lesbarkeits-Gate: Flesch 53,1 |
| 8 | `2026-10-07-etf-sparplan-starten…` | quality-score 0,839 < 0,85 (structure 0,70) |
| 9 | `2026-10-07-heizoel-preise-2026…` | Zeichenlänge (`check_length.py`) |
| 10 | `2026-10-07-wie-smart-home-geraete…` | Textverständnis: R14-MARKER-RUINE („SATZ:") |

**Sieben von zehn Blockern sind dieselbe Klasse** – und diese Klasse hatte
keinen Heiler, der die Schwelle erreicht (Deckungstabelle: `readability_failures`
→ `profi_polish.py`; am Gate heilt das Polish nachweislich nicht auf ≥ 60).

### Warum die Schwelle dort hängt (Messung, nicht Vermutung)

Flesch (deutsch) = 180 − ØSatzlänge − 58,5 · ØSilben/Wort. Gemessen an den
sieben Kandidaten (Wörter, Ø Satz, Ø Silbe/Wort):

| Kandidat | Flesch | Ø Satz (Wörter) | Ø Silbe/Wort | Wörter |
|---|---|---|---|---|
| dein-weg | 57,9 | 13,6 | 1,854 | 1146 |
| dsl | 59,4 | 9,1 | 1,906 | 1098 |
| haushaltskosten | 59,9 | 9,1 | 1,899 | 1439 |
| stromkosten | 52,3 | 13,0 | 1,962 | 1632 |
| urlaub | 58,8 | 11,3 | 1,879 | 721 |
| vpn | 55,8 | 9,9 | 1,953 | 1404 |
| waermepumpe | 53,1 | 12,8 | 1,948 | 936 |

Der Hebel steht eindeutig in der **dritten Spalte** (Silben je Wort), nicht in
der Satzlänge: `dsl` hat mit Ø 9,1 Wörtern bereits kurze Sätze und liegt
trotzdem unter 60. Deshalb ist der neue Heiler auf die Silbenebene gebaut –
deterministische Satzschnitte allein sind nachweislich zu schwach (Gewinne
≤ +0,4, siehe Grenzen).

### Warum daraus 1/2 wurde

Die Engine erzeugt die Artikel des Tages selbst; die Reserve ist der Puffer für
verpasste Slots und Verluste. Am 05.10.2026 kam der zurückgestufte/gehaltene
Bestand hinzu (2 gehaltene Posts, ältester Grund: genau dieses Lesbarkeits-Gate,
Flesch 44,4). Ergebnis: **1/2 LIVE** – und der nächste Publikationstag musste
aus einem Vorrat von 2/6 bedienen. Genau die Lage, die #609 beschreibt.

## Die Dauerheilung (sechs Teile, alle im PR)

1. **`scripts/lesbarkeit_heiler.py` (neu, 1037 Zeilen)** – der fehlende Heiler
   der Klasse.
   * **Stufe A (deterministisch, offline):** Schachtelsätze (> 18 Wörter) an
     sicheren Nahtstellen zerlegen („, und/aber/denn/doch/sondern", „;"),
     Füllphrasen kürzen (`KURZ_LEXIKON`), Absätze > 4 Sätze über die
     bestehende R5-SSOT splitten. Abkürzungen werden maskiert, Links,
     Shortcodes und Code-Spans sind Schnitt-Sperrzonen.
   * **Stufe B (KI, gezielt):** Gemini → Groq; der Auftrag nennt IST-Lage
     (Flesch, Ø Satzlänge, Ø Wortlänge) und den echten Hebel: lange Komposita
     durch Alltagswörter ersetzen, bevor Sätze geschnitten werden. Maximal
     zwei Versuche.
   * **Tor T1–T4 (fail-closed):** geschrieben wird nur, was (T1) Flesch ≥
     **importierte** Schwelle `readability_check.NEW_FLESCH_MIN` **und** besser
     als vorher erreicht, (T2) keinen neuen harten Fund aus
     `publish_gate.HARTE_REGELN` erzeugt, (T3) `publikations_vertrag.pruefe`
     (V1–V3, #607) hält und (T4) Links/`/go/`-Anker/Überschriften/Shortcodes/
     Tabellen/Zahlen-Multiset/Frontmatter byte-identisch bewahrt (Länge ≥ 90 %).
     Scheitert eine Zeile, bleibt die Datei **byte-identisch** liegen.
   * **Scope:** nur Entwürfe (`draft: true`); Ausnahme ausschließlich
     `--new-only` (Artikel des heutigen Datums). Der Live-Bestand gehört der
     Deploy-/Kadenz-Kette.
2. **Wirkungsnachweis statt Namensliste** – `reserve_healer_coverage.py`:
   `WIRKUNGS_PROBEN` + `wirkungsdeckung()` + `volldeckung()`. Regeln mit
   Zahlen-Versprechen (`PROBEN_PFLICHT`: `readability_failures`) brauchen
   mindestens einen Heiler mit **grüner Wirkungsprobe**
   (`--wirkungsprobe`, Exit 0, ohne Netz, ohne Kontingent). Wirkungs-Lücken
   wandern in `luecken` – jeder bestehende Aufrufer bleibt ohne Änderung
   fail-closed.
3. **Verdrahtung: Reserve-Kette** – `reserve_finisher.HEALER_CHAIN` fährt den
   Heiler als **letzten Textschritt** (nach allen KI-Umschreibern, vor
   Linker/URL-Hygiene/Intent), datei-bezirkelt (`--fix`, Scope `file`). Der
   Finisher-Selbsttest verlangt Kette **und** Wirkungsprobe.
4. **Verdrahtung: Live-Engine + Holds** – `content-engine-v2.yml`:
   * Phase 0.5 (Hold-Requeue) bekommt `GROQ_API_KEY`/`GEMINI_API_KEY`, damit
     Lesbarkeits-Holds schon in der Frühphase geheilt und rearmt werden;
   * Phase 3 heilt die Artikel des Tages (`--new-only --fix`, fail-closed,
     `|| echo` nur als Log-Hinweis).
   `requeue_quality_holds.py` kennt die Lesbarkeits-Klasse (Wort-Erkennung
   „Lesbarkeits-Gate"/„Lesbarkeits-Score") und hebt einen Hold **nur** auf,
   wenn die Schwelle im Ergebnis steht; `reserve_blocker_klassen.py` nennt den
   Klassen-Heiler (zusammen mit `profi_polish.py` als zweitem Hebel).
5. **Governance-Regel C25 („Deckung heißt Wirkung")** – Code C25, weil „C24"
   im Haus die C24 Bank bezeichnet (Logs/Greps wären sonst nicht
   unterscheidbar). Der Kontrakt prüft Struktur **und** Wirkung: Tabellen,
   Kettenglied, importierte Schwelle (keine zweite Zahl), `--wirkungsprobe`
   **jetzt grün**; der Selbsttest fängt drei Sabotagen (Proben entfernt,
   Schwelle kopiert, Heiler aus der Kette). `docs/GOVERNANCE-KONTRAKT.md` neu
   erzeugt (Stand 07.10., mit C20–C25). Ergänzend: Dokumentation in
   `docs/ANLEITUNG-LESBARKEITS-HEILER.md`, `docs/QUALITAETS-REGELWERK.md`
   (zwei Zeilen), Nachtrag in `docs/publication-reliability.md`.
6. **Unter Siegel** – `integrity_guard.FEST` führt den Heiler wie
   `publikations_vertrag.py` (Schwellen-Wache). Signatur `--set-current` über
   **46 Dateien** (vorher 45), Akte: „NEU UNTER SIEGEL", Klasse `fest`,
   HEAD `edfb7ce`, 2026-10-07T11:46:43Z.

## Beweise (07.10.2026, alle offline – ohne Netz, ohne Key)

| Kommando | Urteil |
|---|---|
| `python3 scripts/lesbarkeit_heiler.py --selftest` | ✅ „Wirkungsprobe grün (51.3 → 72.3), Tor T1–T4 weist Sabotage ab, Stufe B nimmt mit Attrappe an und verwirft, Nahtstellen und Abkürzungen halten." |
| `python3 scripts/lesbarkeit_heiler.py --wirkungsprobe` | ✅ Exit 0: „Stufe A: Flesch 51.3 → 72.3 (≥ 60), Verträge T1–T4 erfüllt" |
| `python3 scripts/lesbarkeit_heiler.py --blocked --keine-ki` | 7 Kandidaten einzeln geprüft – **alle fail-closed** („Text bleibt unangetastet"), nichts geschrieben |
| `python3 scripts/reserve_healer_coverage.py` | **0 Lücken**, 10 gedeckt, 2 begründete Ausnahmen + 🧪 „`lesbarkeit_heiler.py` → ✅ Wirkungsprobe: Stufe A: Flesch 51.3 → 72.3 (≥ 60), Verträge T1–T4 erfüllt" |
| `python3 scripts/reserve_healer_coverage.py --selftest` | ✅ inkl. Wirkungs-Deckung („Regel ohne Probe, rote Probe, fehlendes Skript") |
| `python3 scripts/reserve_finisher.py --selftest` | ✅ inkl. Heiler-Deckung Gate↔Kette |
| `python3 scripts/requeue_quality_holds.py --selftest` | ✅ (Erkennung, Schwellen – inkl. Lesbarkeits-Hold-Fälle #609) |
| `python3 scripts/reserve_blocker_klassen.py --selftest` | ✅ (heilbar/unheilbar/Mischfall/Präfix-Deckung) |
| `python3 scripts/slot_wache.py --selftest` | ✅ 33 Fälle (u. a. Vorfall 05.10. nachgestellt) |
| `python3 scripts/engine_issue.py --selftest` | ✅ (Ruhetag, Reopen, Verbuchen) |
| `python3 -m unittest discover -s scripts/tests` | **Ran 1958 tests – OK (skipped=23)**, Exit 0 (inkl. 29 neuer Tests in `test_lesbarkeit_heiler.py`) |
| `python3 scripts/governance_contract.py` | ✅ „erfüllt – alle 24 Regeln prüfen in beide Richtungen" (C1–C25; C24 bewusst ausgelassen) |
| `python3 scripts/governance_contract.py --selftest` | ✅ „C1–C25 mit Kunstbefunden: Fehler erkannt, gutes Setup bleibt still" |
| `python3 scripts/integrity_guard.py --gate` | ✅ „46 Kerndateien entsprechen exakt dem signierten Stand (HEAD `edfb7ce`)" |

Lage (gemessen mit `cadence_guard`): **07.10. = 2/2 LIVE**, 05.10. = 1/2
(verbucht, nicht nachholbar – Inhalte werden nie nachdatiert), 06.10. = Ruhetag.
Die Produktions-Wache hat die letzten 8 Läufe (bis 06.10. 23:43 UTC) ohne
Fehler beendet.

## Grenzen – ehrlich benannt

* **Der Sandbox fehlt ein KI-Key.** Stufe A allein hebt **keinen** der sieben
  Kandidaten über 60 (Gewinne ≤ +0,4; z. B. dein-weg 57,9 → 58,2). Genau
  deshalb ist Stufe B gebaut und in beiden Workflows verdrahtet, die die
  Secrets (GROQ/GEMINI) besitzen. Der **erste echte Heilungsnachweis** kommt
  aus dem nächsten Reserve-Lauf – der Report wird dann um sein Zertifikat
  ergänzt.
* **Kein Text wird unter der Schwelle geschrieben.** Ein „Versuch" rearmt
  nichts und veröffentlicht nichts – auch nicht „knapp darunter". Das ist
  gewollt und wird vom Tor T1–T4 und von C25 erzwungen.
* **Der 05.10. bleibt 1/2.** Ein vergangener Fehltag wird nicht nachgetragen
  (Hausregel); die Wache schließt, sobald ihre **eigene Messung** wieder OK
  sieht.

## Beobachtung (Abnahme)

1. Nächster Reserve-Lauf: `data/reserve-readiness.json` muss sich von 2/6 nach
   oben bewegen (die sieben Kandidaten durchlaufen den Heiler; Reste bleiben
   ehrlich rot).
2. Nächster Publikationstag: 2/2 LIVE; `--wirkungsprobe` im
   Governance-Lauf bleibt grün.
3. Wenn ein Kandidat trotz Heiler unter 60 bleibt, steht das als Restlücke im
   Log – dann ist es ein Inhaltsproblem, kein Werkzeugproblem, und der Weg ist
   redaktionell (nicht: Schwelle senken).

## Regressionen

`scripts/tests/test_lesbarkeit_heiler.py` (neu, 29 Tests): Wirkungsprobe und
SSOT, CLI-Maschinenvertrag, Tor T1–T4 (entfernter Link, veränderte Zahl,
fremdes Frontmatter, neuer harter Fund, zu starke Kürzung, Wirkungslosigkeit,
Idempotenz, Abkürzungen), Stufe B mit Attrappe (annehmen/verwerfen, Link-
Verlust, unter der Schwelle, ohne KI nichts schreiben), Scope (Nicht-Entwurf,
Trockenlauf), Kandidaten, Verdrahtung (Kette, Deckung, Governance, Workflow),
Report. Dazu die erweiterten Selbsttests von Deckungs-Wache, Finisher,
Hold-Requeue und Governance-Kontrakt (C1–C25).
