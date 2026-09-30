# Bestand-Gate #476 – Zerfaserung dauerhaft behoben

**Datum:** 2026-09-30
**Auslöser:** Issue #476 „📋 Bestand-Gate: bestehende Artikel brauchen Aufmerksamkeit“
**Befund des Gates:** 44 Live-Artikel geprüft · 1 weiterhin auffällig ·
`2026-09-07-frugalismus-tipps-so-vermeidest-du-teure-alltagsfehler` –
„Länge außerhalb 700-1800 Wörter“

---

## 1) Was wirklich kaputt war

Der gemeldete Artikel war **nicht zu lang, weil er zu viel zu sagen hatte**.
Er war zerfasert.

| Messung | vorher | Korridor (SSOT `length_policy.py`) |
|---|---|---|
| Zeichen Fließtext | **22.599** | Floor 10.000 · Optimum 12.000–18.000 · Deckel 22.000 |
| H2-Abschnitte | **29** | – |
| davon Mikro-Abschnitte (< 90 Wörter) | **16** | – |
| Serien-Überschriften | „Welche …“ ×13 in Folge | – |

Die letzten 15 Abschnitte des Artikels waren angehängte Mini-Rubriken aus den
Politur-Runden 25–41 (dokumentiert in `PREMIUM-BLOG-AUDIT-2026-09-25.md`):

> „Welche Reihenfolge im Alltag oft am leichtesten ist“ · „Welche zwei Geldlecks
> oft zuerst verschwinden“ · „Welche eine Frage Impulskäufe oft stoppt“ · …
> „Welche Samstagsnotiz dir das Gegensteuern leichter macht“

Jeder Abschnitt 40–70 Wörter, inhaltlich überlappend, ohne Dramaturgie. Für
Leser: ein Artikel, der nach dem Fazit-Gefühl noch 15-mal neu anfängt. Für
Google: Mikro-Struktur ohne Tiefe. Für das Gate: irgendwann der harte Deckel.

## 2) Die strukturelle Lücke (der eigentliche Fehler)

- `length_guard.py` heilt **ausschließlich nach oben** – zu kurz → KI ergänzt
  Mehrwert-Module. Für die Gegenrichtung existierte **keine Wache**.
- `check_length.py` misst Zeichen und schlägt erst am **harten Deckel** an –
  also Wochen nach Beginn der Zerfaserung, und ohne die Ursache zu benennen.
- `content_audit.py` C1 prüft „zu dünn“ auf **Artikelebene**, nie die
  Feinstruktur der Abschnitte.

Ergebnis: Jede Politur-Runde durfte einen weiteren Mini-Abschnitt anhängen.
Das Gate meldete das Symptom („zu lang“), die Ursache blieb unsichtbar – und
eine rein redaktionelle Kürzung hätte den Mechanismus in der nächsten Runde
erneut zuschlagen lassen.

## 3) Redaktionelle Reparatur des Artikels

- Die 15 angehängten Mini-Rubriken sind **zu einem Kapitel verdichtet**:
  **„Dein 7-Tage-Start: vom Vorsatz zur Routine“** – Wochen-Fahrplan als
  Tabelle (Montag bis Sonntag) plus zwei substanzielle H3
  („Zähle die Häufigkeit, nicht die Summe“, „Leitplanken halten länger als
  Verbote“). Jeder Gedanke der alten Schnipsel ist erhalten, keiner doppelt.
- **Fazit neu geschrieben.** Vorher standen dort artikelfremde Zahlen
  („Nebenkosten-Klassiker 80 bis 100 €“, „Tarifwechsel drückt 60 € auf 35 €“)
  und ein gegen den Artikel laufender Sparbetrag.
- **Zahlen konsistent gemacht:** Kurzfassung, Rechenbeispiel, Fazit und FAQ
  sagen jetzt dasselbe (1.200–3.700 € pro Jahr; FAQ 100–300 € pro Monat).
- **Redundanzen verdichtet** (Mindset-, Sparmethoden-, Motivations- und
  Trick-Abschnitte), damit der Artikel im **Optimum** landet statt knapp unter
  dem Deckel.
- **Kaputte Verweise geheilt:** „Lesetipp“ ohne Link → echter interner Link;
  generischer Anker „[finanzielle]“ → „[finanzielle Sicherheit]“.
- Meta-Description ohne Abbruch-Ellipse, `lastmod` aktualisiert.

| Messung | vorher | nachher |
|---|---|---|
| Zeichen | 22.599 (**zu-lang**) | **17.709 (ok, Optimum)** |
| Wörter | 3.197 | 2.469 |
| H2-Abschnitte | 29 | 14 |
| Mikro-Abschnitte | 16 | **0** |
| Serien-Überschriften | ja | **0** |
| Lesbarkeit | – | **100/100 · Flesch 62,7** (Ziel ≥ 62) |

`check_length.py`: **zu-lang 0 · zu-kurz 0**. Die Textwachen (casing, dash,
unit, lektor, stil, compound, repetition, math, table, link, content_audit)
melden zu diesem Artikel **keinen einzigen Fund**.

## 4) Damit es nicht wiederkommt: `scripts/struktur_guard.py`

Neue deterministische Wache (kein KI-Anteil, kein Auto-Fix – Abschnitte
zusammenführen ist redaktionelle Arbeit):

| Regel | Was sie sieht |
|---|---|
| **S1** | H2-Abschnitt mit < 90 Wörtern Fließtext (Kanon-Rubriken wie „Das Wichtigste in Kürze“, FAQ-Kopf, Quellen sind befreit) |
| **S2** | ≥ 3 aufeinanderfolgende H2, die mit demselben Wort beginnen **und alle Mikro-Abschnitte sind** – der Fingerabdruck angehängter Politur-Runden. „Trick 1–4“ mit echtem Inhalt schlägt bewusst nicht an |
| **S3** | Fließtext über dem **Optimum** (18.000) bei vorhandenen Mikro-Abschnitten – greift also, **bevor** der harte Deckel (22.000) fällt |

**Sperrklinke** (`data/struktur_baseline.json`): Je Artikel ist der heutige
Stand eingefroren. Der Wert darf **nur kleiner werden**.

- Zuwachs an Mikro-Abschnitten oder Serien → **Exit 1**, Befund im Report.
- Rückgang → Baseline rastet automatisch enger (Klinke).
- Neue Artikel dürfen höchstens 2 Mikro-Abschnitte mitbringen.

Damit ist der Mechanismus aus #476 ab sofort blockiert: Die nächste Runde, die
einem Artikel einen 50-Wörter-Abschnitt anhängt, fällt **sofort** auf – statt
Wochen später als „zu lang“.

**Beweis:** `--selftest` mit 9 eingefrorenen Fällen (Mikro-Erkennung,
Kanon-Befreiung, Serien-Signatur, Negativfälle, Tabellen-Gerüst, Klinke in
beide Richtungen, Korridor-Plausibilität). Rot = Exit 2, es wird nichts
geschrieben (fail-closed wie im ganzen Haus).

## 5) Verdrahtung

- **`scripts/blog_doctor.py`** – Wache Nr. 26 der Kette (Phase B-Semantik), direkt hinter
  `length_guard.py` (die Gegenrichtung gehört neben die Heilung nach oben).
- **`.github/workflows/seo-weekly.yml`** – eigener Schritt *vor* dem
  Bestand-Gate; Baseline und Historie wandern in den vorhandenen Commit-Schritt.
  Schlägt das Bestand-Gate an, hängt der Struktur-Report **die Ursache** an das
  Issue an.
- **`scripts/bestand_gate.py`** – die Legacy-Zeile „Länge außerhalb 700-1800
  Wörter“ ist ersetzt. Sie war schlicht falsch: Gemessen wird seit dem
  Premium-Korridor in **Zeichen**. Neu meldet der Bericht Messwert, echten
  Korridor, Heilbefehl (zu kurz) bzw. den Zerfaserungs-Befund (zu lang).

## 6) Restschuld, bewusst sichtbar gehalten

Die Wache zeigt, dass die Zerfaserung kein Einzelfall war: **57 von 62**
Artikeln tragen noch Mikro-Abschnitte, **14** zusätzlich Serien. Nichts davon
ist heute ein Gate-Verstoß, und nichts davon wird automatisch angefasst –
aber alles ist eingefroren und kann nur noch **kleiner** werden. Größte Posten
für die nächsten Politur-Runden (dann bitte verdichtend statt anhängend):

| Artikel | Mikro | Serien | Status |
|---|---|---|---|
| `2026-09-21-zahnzusatzversicherung-kosten-leistungen-vergleich` | 31 | 1 | Entwurf |
| `2026-09-17-versicherung-update-was-sich-jetzt-fuer-dich-aendert` | 30 | 1 | Entwurf |
| `2026-09-22-konto-karten-update-was-sich-jetzt-fuer-dich-aendert` | 30 | 1 | Entwurf |
| `2026-08-18-wohngebaeudeversicherung-vergleich-worauf-du-achten-musst` | 20 | 1 | live |
| `2026-09-21-tierkrankenversicherung-hund-katze-kosten` | 18 | 1 | live |

## 7) Prüfbefehle

```bash
python3 scripts/struktur_guard.py --selftest   # 9 eingefrorene Fälle
python3 scripts/struktur_guard.py              # Bestand + Sperrklinke
python3 scripts/struktur_guard.py --json
python3 scripts/check_length.py                # zu-lang 0 · zu-kurz 0
python3 scripts/readability_check.py           # Artikel 100/100 · Flesch 62,7
python3 scripts/blog_doctor.py --selftest      # Kette: 26 Wachen
```
