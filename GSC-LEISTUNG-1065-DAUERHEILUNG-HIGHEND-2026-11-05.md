# GSC-Leistungsdaten #1065 – die Auswertung, die gefehlt hat

**Vorgang:** #1065 „GSC-Leistungsdaten 2026-11-04“ · Auftrag: dauerhaft auf
Highend-Level einer Profi-Agentur beheben
**Stand:** 05.11.2026 · Suchmaschine: Google Search Console (Dienstkonto, nur lesend)
**Vorherige Wahrheit:** `data/gsc/meta.json` (Stand 05.11.2026 13:10 UTC,
`status: ok`), `data/gsc/tagesdaten.jsonl` (44 Messtage),
`top_seiten_28t.json` (35 Seiten), `top_suchbegriffe_28t.json` (53 Begriffe),
`GSC-OPTIMIERUNGSPLAN-2026-10-27.md`, `docs/ANLEITUNG-GOOGLE-SEARCH-CONSOLE.md` §6.

---

## 1 · Das Ergebnis in vier Sätzen

Die Automatik funktionierte – **die Auswertung fehlte**. Seit dem 12.10.2026
sammelt `gsc_import.py` täglich Klicks, Impressionen, CTR und Position; am
05.11.2026 lagen 44 Messtage, 35 Seiten und 53 Suchbegriffe im Repo, und **kein
einziges Skript hat sie gelesen**. Genau deshalb steht im täglichen Issue der
Abschnitt „Was zu prüfen ist“ – drei Fragen an einen Menschen, obwohl jede davon
aus denselben vier Dateien beantwortbar ist. Die redaktionelle Reihenfolge
(„Seiten mit ausreichend Impressionen und Position 4–20 zuerst“) stand seit dem
27.10.2026 als **Prosa** im Runbook, ohne Erzeuger. `scripts/gsc_leistung.py`
schließt diese Lücke: neun Regeln (L1–L9), offline, deterministisch, mit
Warteschlange – verdrahtet in den Tageslauf, das Tor, die Regressionstests und
beide Runbooks. Die erste Auswertung des echten Bestands liefert dabei einen
Befund, den vorher niemand sehen konnte: **zwei gültige Dateien desselben Laufs
widersprechen sich um 74 Impressionen.**

| Kennzahl | vorher | jetzt (05.11.2026) | Quelle |
|---|---|---|---|
| Skripte, die `data/gsc/` auswerten | 0 | **1** (`gsc_leistung.py`, L1–L9) | `scripts/gsc_leistung.py` |
| Auswertung im täglichen Lauf | – | **Schritt 6a** + Tor + Zusammenfassung | `.github/workflows/gsc-import.yml` |
| Redaktionelle Reihenfolge | Prosa im Runbook | **erzeugte Warteschlange** (P1–P3) | `data/gsc/leistung/warteschlange.json` |
| Regressionstests zur Leistung | 0 | **36** | `scripts/tests/test_gsc_leistung.py` |
| Selbsttest im vertraglichen Minimum (C6) | – | **dabei** | `scripts/governance_contract.py` |
| Frische des Imports geprüft | – | **L1** (hart ab Tag 3) | `--check` |
| Kopf gegen Ledger gerechnet | – | **L2/L9** | `--check` |
| Harte Funde im echten Bestand | unbekannt | **0** | `python3 scripts/gsc_leistung.py --check` |

---

## 2 · Befund A – die Zahlen lagen da, niemand las sie

Der Bestand am 05.11.2026, vollständig aus `data/gsc/` gelesen:

| Kennzahl | Wert | Quelle |
|---|---|---|
| Messtage | 44 (20.09. – 02.11.2026), 38 mit Impression | `tagesdaten.jsonl` |
| Impressionen (28 Tage) | **276** | `tagesdaten.jsonl` |
| Klicks (28 Tage) | **0** · CTR 0,00 % | `tagesdaten.jsonl` |
| Bester Tag | 31.10.2026 mit 33 Impressionen | `tagesdaten.jsonl` |
| Seiten mit Impression | 35 (davon 21 Inhaltsseiten) | `top_seiten_28t.json` |
| Inhaltsseiten ohne Impression | **71 von 92 (77 %)** | `content/` × `top_seiten_28t.json` |
| Suchbegriffe mit Impression | 53 | `top_suchbegriffe_28t.json` |

Zwei Tatsachen daraus sind für die Reihenfolge der Arbeit entscheidend, und keine
von beiden stand vorher irgendwo als Zahl:

1. **77 % der Inhaltsseiten hatten keine einzige Impression.** Die Reichweiten-
   Bremse ist der Index, nicht das Snippet. Ein Title auf einer Seite, die Google
   nicht kennt, ist Arbeit ohne Leser – deshalb steht die Index-Arbeit (L5) in
   der Warteschlange **oben**, nicht die CTR-Arbeit.
2. **276 Impressionen, null Klicks.** Bei Positionen von 32 bis 87 ist das kein
   CTR-Problem, sondern ein Positions-Problem. Die Auswertung sagt beides, statt
   „Titel überarbeiten“ zu empfehlen.

---

## 3 · Befund B – zwei gültige Dateien widersprechen sich (L9)

Die Kreuzprüfung hält Kopf und Listen gegeneinander. Im echten Bestand:

```
top_seiten_28t.json summiert 350 Impressionen,
der Tages-Ledger im selben Fenster 2026-10-06…2026-11-02 hat 276
```

Beide Zahlen kommen aus **demselben Lauf**, derselben Property, demselben
`dataState: final`, Sekunden auseinander. 74 Impressionen Differenz (27 %).

**Was hier geprüft ist und was nicht.** Google aggregiert je Dimension und
anonymisiert einzelne Suchbegriffe – die Summe der Query-Liste (183) liegt
deshalb sogar **unter** dem Tages-Ledger, die Summe der Seiten-Liste darüber.
Welche der beiden Seiten-Messungen recht hat, kann von hier aus niemand
entscheiden; das Repo hat keinen Netzweg zu Google. Deshalb ist L9 in **zwei
Schweregrade** geteilt:

* **hart** – rechnerisch prüfbar ohne Google: `klicks_zeitraum` gegen den Ledger,
  CTR je Eintrag gegen Klicks/Impressionen, Position außerhalb 1–100. Ein
  Widerspruch hier ist ein Defekt der Dateien, nicht der Messung.
* **Hinweis** – die Mess-Abweichung zwischen Seiten-Liste und Tages-Ledger
  jenseits von 25 %. Sie steht im Bericht mit **beiden** Zahlen, damit ein
  verschobenes Fenster oder ein alter Listenstand auffällt; sie macht den Lauf
  nicht rot, weil das Repo die Frage nicht entscheiden kann.

Der nächste Schritt dafür ist ein Mensch mit Search-Console-Zugang:
„Leistung → Seiten“ gegen „Leistung → Täglich“ im selben Fenster vergleichen.
Genau das steht als `naechster_schritt` im Befund – ein Befund, den niemand
bedienen kann, ist nur Lärm.

---

## 4 · Befund C – die eingefrorene Top-20-Auswahl driftet (L8)

`data/top20_abbildungen.yaml` ist eine Momentaufnahme vom **19.10.2026**,
ausgewählt nach genau diesen Impressionen. Der Import schreibt die Quelle
täglich neu – die Auswahl selbst steht. Heute treffen **6 von 20** Einträgen
(30 %) noch auf eine Seite mit Impressionen; die Grenze liegt bei 50 %.

Warum das kein rein kosmetischer Befund ist: `abbildungen_ableiten.py --check`
(delegiert von `ff_inhalts_wache.py`, FF5) prüft Abbildungen und Bildzeilen
**dieser** Auswahl. Driftet sie, prüft die Wache eine Auswahl, die niemand mehr
begründen kann – und der Bericht vom 30.10.2026
(`LAYOUT-UND-RESERVE-900-NACHTRAG-HIGHEND-2026-10-30.md`) beschreibt genau die
Folge: 21 FF5-Befunde, die bei **jedem fremden PR** landen, weil die
GSC-Automatik die Liste verschiebt und niemand die Abbildungen nachzieht.

**Die Heilung ist absichtlich keine Automatik.** Ein tägliches Neuwählen würde
20 Artikel jeden Tag anfassen (zwei SVGs plus Bildzeile je Beitrag) – aus einer
Messung, die sich täglich verschiebt. L8 meldet die Drift deshalb als
**Wiedervorlage** mit Beleg; erneuert wird von Hand
(`python3 scripts/abbildungen_ableiten.py` → `--check`). Die Auswahlregel
bleibt dieselbe, nur der Zeitpunkt ihrer Erneuerung wird sichtbar.

---

## 5 · Befund D – die Schlagdistanz war nur ein Satz (L4/L7)

Im Runbook stand: „Seiten mit ausreichend Impressionen und Position 4–20
zuerst.“ Kein Skript erzeugte diese Liste. Jetzt tut es das, mit Klasse und
Beleg je Seite. Aus dem echten Bestand (Auswahl):

| Prio | Seite | Beleg | Nächster Schritt |
|---|---|---|---|
| P1 | `/posts/2026-10-09-vpn-zuhause-…` | 7 Impressionen, Position 10,00, 0 Klicks | Suchintention prüfen → Fakten/Quellen → Inlink → **dann** Title |
| P1 | `/posts/2026-08-21-haushaltsbuch-fuehren-…` | 6 Impressionen, Position 7,17, 0 Klicks | dito |
| P1 | `/posts/2026-08-12-preisgarantie-gas-…` | 6 Impressionen, Position 8,67, 0 Klicks | dito |
| P1 | `/posts/2026-08-24-preisgarantie-gas-…` | 5 Impressionen, Position 9,40, 0 Klicks | dito |
| P2 | `/posts/2026-08-14-gasrechnung-senken-…` | 4 Impressionen, Position 4,50, 0 Klicks | dito |

Zwei Konstruktionsfehler sind dabei erst im echten Lauf aufgefallen und behoben:

1. **Hubs landeten in der Warteschlange.** `/posts/` und `/pillar/` sind
   Listenansichten. Ein Präfix-Vergleich (`startswith("/posts/")`) nimmt sie mit,
   und schon steht „Title der Beitrags-Übersicht optimieren“ in der Liste.
   Jetzt entscheidet die **Klasse**, nicht der Anfang des Pfads.
2. **Die Reihenfolge war invertiert.** Der erste Wurf machte die Snippet-Arbeit
   (L7) zu P1 und die Inhalts-Arbeit (L4) zu P2 – genau entgegen der
   dokumenteten Ordnung. Jetzt gilt: eine Seite, eine Aufgabe, und der
   nächste Schritt ist immer „Suchintention prüfen, Fakten/Quellen
   aktualisieren, intern verlinken – erst dann Title/Description“.

---

## 6 · Heilung: vier Schichten

### 6.1 Erzeuger – `scripts/gsc_leistung.py`

Offline, deterministisch, ohne Netz, ohne Google ein zweites Mal zu fragen.
Liest ausschließlich die vier Dateien des Imports plus `content/` (Titel,
Description, lastmod, live) und `data/top20_abbildungen.yaml`. Schreibt keinen
Text, wählt keine Top-20 neu, erfindet keine URL: was nicht in den Listen steht,
hat keine Impression – nicht „wenige“, keine.

Die Schwellen stehen **einmal** oben in der Datei (`FRISCH_TAGE`,
`MIN_IMPRESSIONEN`, `POSITION_SCHLAGDISTANZ`, `ABWEICHUNG_GRENZE`, …) – dieselbe
Konvention, die `serp_limits.py` für Metadaten erzwingt. Der Selbsttest fährt
das ganze Modul gegen einen Wegwerf-Baum (`Pfade`-Injektion statt globaler
Konstanten-Verdrehung) und damit ohne den echten Bestand.

### 6.2 Befund und Warteschlange – `data/gsc/leistung/`

```
data/gsc/leistung/befund.json         Befund (maschinenlesbar, L1–L9)
data/gsc/leistung/befund.md           derselbe Befund als Bericht
data/gsc/leistung/warteschlange.json  redaktionelle Aufgaben (P1–P3, Eigentümer: Mensch)
data/gsc/leistung/verlauf.jsonl       eine Zeile je Lauf (append-only)
```

`merge=binary` für die beiden JSON-Dateien in `.gitattributes`: Ein Lauf = eine
Messung. Der Verlauf bleibt bei `merge=union` – eine Zeile je Lauf ist eine
unabhängige Messung, ihre Vereinigung ist korrekt (dieselbe Regel wie beim
Tagesledger und beim Triage-Verlauf).

### 6.3 Verdrahtung

| Ort | Änderung |
|---|---|
| `.github/workflows/gsc-import.yml` | neuer Schritt 6a „Leistung auswerten (L1–L9) und Tor fahren“: `--selftest`, `--check` als Tor, `--schreiben --md` in die Lauf-Zusammenfassung |
| `.github/workflows/gsc-import.yml` | der tägliche PR **trägt die Auswertung** (`--issue`) – die Fragen des Issues sind beantwortet, bevor sie gestellt werden; fällt das Werkzeug aus, bleibt der alte Text (kein Report-Schritt ohne lebenden Erzeuger, D9) |
| `scripts/governance_contract.py` (`GUARDS`, C6) | `gsc_leistung.py` im vertraglichen Minimum – sein Selbsttest läuft im Governance-Gate |
| `package.json` | `gsc:leistung`, `gsc:leistung:md`, `gsc:leistung:issue`; `test:gsc` fährt Selbsttest + Regression mit |
| `.gitattributes` | `data/gsc/leistung/*.json merge=binary` |
| `docs/ANLEITUNG-GOOGLE-SEARCH-CONSOLE.md` | §6.1 (Regeln, Schweregrade, Befehle), §7 Schritt 6a, §12 Befehle |
| `docs/ANLEITUNG-GSC-API-ZUGRIFF.md` | Abschnitt „Leistungsdaten auswerten“ – warum die Mess-Abweichung nur ein Hinweis ist, warum L8 nicht automatisch neu wählt |
| `scripts/tests/test_gsc_leistung.py` | 36 Regressionstests: Erkennen **und** Schweigen je Regel, Warteschlange-Ordnung, Artefakte, echter Bestand |

### 6.4 Selbsttest und Vertrag

`python3 scripts/gsc_leistung.py --selftest` prüft **dieses** Modul (D6): jede
Regel an ihrem Fall **und** am guten Lauf, die Warteschlange-Ordnung, das
Schreiben der vier Artefakte, append-only Verlauf, und den Fehlerpfad
(fehlende/kaputte/leere Eingabe → `LeistungsFehler`, Exit 2 statt Exit 0). Kein
Netz, kein Schlüssel, kein Modell – der Läuft damit auch unter
`selftest_ki.py --trap-workflows`.

---

## 7 · Belege (alle 05.11.2026, gleicher Stand)

| Prüfung | Ergebnis |
|---|---|
| `python3 scripts/gsc_leistung.py --selftest` | ✅ bestanden (L1–L9, Warteschlange, Artefakte, Fehlerpfad) |
| `python3 -m unittest scripts.tests.test_gsc_leistung` | ✅ **36 Tests** |
| `npm run test:gsc` (8 Selbsttests + 5 Testmodule) | ✅ **221 Tests** |
| `python3 scripts/gsc_leistung.py --check` (echter Bestand) | ✅ **0 harte Funde**, 7 Hinweise |
| `python3 scripts/gsc_artefakte_guard.py --check` | ✅ grün (unverändert, vier Dateien gültig) |
| `python3 scripts/skript_syntax_wache.py` | ✅ 649 Dateien |
| `python3 scripts/wachen_vertrag.py` | ✅ 379 Skripte, 0 Funde |
| `python3 scripts/governance_contract.py --quick` | ✅ 45 Regeln (inkl. C6 für die neue Wache) |
| `yaml.safe_load` auf `gsc-import.yml` | ✅ gültig, Schritt 6a an 21. Stelle |
| `hugo`-Build | nicht berührt (keine Layout-/Inhaltsänderung) |

**Der Befund des echten Bestands** (vollständig in `data/gsc/leistung/befund.md`):
L9 (Mess-Abweichung 350 : 276), L3 (276 Impressionen, 0 Klicks), L4 (9
Inhaltsseiten in Schlagdistanz), L7 (9 Seiten auf Position ≤ 10 ohne Klick), L5
(21 von 92 Inhaltsseiten mit Impression), L6 (7 Begriffe mit Nachfrage jenseits
Position 20), L8 (Top-20-Auswahl trifft 30 %) – **sieben Hinweise, null hart**.
Genau so soll es sein: keine dieser Zahlen ist ein Defekt, alle sind Aussagen.

---

## 8 · Was bewusst offen bleibt

| Punkt | Warum hier offen | Wo es läuft |
|---|---|---|
| Die 74-Impressionen-Differenz (L9) | Nur die Search Console kann entscheiden, welche der beiden Dimensionen recht hat | Befund + `naechster_schritt`; Mensch vergleicht „Seiten“ gegen „Täglich“ |
| Top-20-Auswahl erneuern (L8) | Ein automatisches Neuwählen würde 20 Artikel täglich anfassen | Warteschlange P3; `abbildungen_ableiten.py` → `--check` |
| 71 Inhaltsseiten ohne Impression | Index-Arbeit, nicht Snippet-Arbeit | Warteschlange P1 → `gsc:abdeckung` + `gsc:triage` |
| Abdeckungs-Export ist 17 Tage alt (W8) | CSV kommt nur aus der Oberfläche | Wochenroutine `npm run gsc:abdeckung` |
| Roter Test `test_register_ist_aktuell` | Vor dieser Sitzung rot: `fachpruefung_register.yaml` ist um eine Fundstelle veraltet (Tagesgeld-Artikel). Nicht Teil dieses Vorgangs, nicht von `data/gsc/` berührt | eigener Vorgang; Heilung ist `python3 scripts/fachpruefung_register.py` |

---

## 9 · Rest-Risiken

1. **Die Auswertung liest, sie entscheidet nicht.** Ob eine Seite in
   Schlagdistanz eine bessere Überschrift braucht, weiß nur ein Mensch mit
   Suchabsicht. Das Werkzeug liefert Zahl, Regel und nächsten Schritt.
2. **L9 trennt Rechnen und Messen – die Grenze ist eine Annahme.** Dass Google
   je Dimension anders aggregiert, ist beobachtet (350 : 276), nicht dokumentiert.
   Die 25-%-Toleranz ist deshalb eine Schwelle mit Begründung, keine Wahrheit.
   Fällt sie zu eng, meldet der Lauf dauerhaft; fällt sie zu weit, sieht er nichts.
   Beides steht als Konstante an einem Ort.
3. **`--check` ist grün, solange der Import läuft.** Ein stehengebliebener Lauf
   ist hart (L1) – aber nur, wenn `meta.json` überhaupt geschrieben wird. Bleibt
   der Workflow selbst aus, meldet das der Workflow, nicht dieses Werkzeug.
4. **Die Klassenregel kennt neue Seitentypen nicht.** Was nicht in `RECHT`,
   `HUBS` oder den vier Inhaltsklassen steht, wird „sonstige“ – und bekommt
   keine Aufgabe, erscheint aber auch in keiner Liste. Ein neuer Seitentyp ist
   damit ein stiller Blindflug, bis jemand ihn einträgt.

---

*Dieser Bericht ist der Nachweis zum Vorgang #1065. Erzeuger:
`scripts/gsc_leistung.py` · Befund: `data/gsc/leistung/befund.md` · Warteschlange:
`data/gsc/leistung/warteschlange.json` · Runbook:
`docs/ANLEITUNG-GSC-API-ZUGRIFF.md`.*
