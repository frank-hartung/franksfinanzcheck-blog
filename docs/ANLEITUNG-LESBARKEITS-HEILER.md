# ANLEITUNG – Lesbarkeits-Heiler (Flesch ≥ 60)

**Stand:** 2026-10-07 · **Werkzeug:** `scripts/lesbarkeit_heiler.py` · **Auslöser:** WACHE-609

## Warum es dieses Werkzeug gibt

Die Produktions-Wache meldete am 06.10.2026 für den letzten Publikationstag
„Content-Engine liefert nicht" (P2): **1/2** Artikel. Die zweite Hälfte des
Befunds stand im selben Body: `data/reserve-readiness.json` meldete
*Ziel 6, bereit 2* – **sieben Kandidaten allein am harten Lesbarkeits-Gate**
(`readability_check.NEW_FLESCH_MIN` = 60,0, verankert durch #585), ein
achter am Textverständnis. Für diese Klasse gab es **keinen Heiler, der die
Schwelle erreicht**: Die Deckungs-Wache führte die Regel als „gedeckt",
weil `profi_polish.py` in der Kette stand – *ein Name, keine Wirkung*.

**Die Quote ist das Symptom; der trockene Vorrat ist die Krankheit.**

## Zwei Stufen, ein Tor

| Stufe | Was passiert | Kosten |
|---|---|---|
| **A – deterministisch** | Schachtelsätze (> 18 Wörter) an sicheren Nahtstellen zerlegen („, und/aber/denn/doch/sondern", „;"), Füllphrasen kürzen (`KURZ_LEXIKON`), Absätze > 4 Sätze über die R5-SSOT splitten. Abkürzungen („z. B.") werden vorher maskiert. | 0 €, offline |
| **B – KI** | Gemini (`gemini-3-flash-preview`), sonst Groq. Der Auftrag nennt das **IST** (Flesch, Ø Satzlänge, Ø Wortlänge) und den echten Hebel: Flesch = 180 − Ø Satzlänge − 58,5 · **Silben je Wort**. Lange Komposita werden durch Alltagswörter ersetzt, bevor Sätze geschnitten werden. Höchstens zwei Versuche. | 1 API-Call |

**Das Tor T1–T4 entscheidet – nicht der Schreiber.** Eine Änderung wird nur
geschrieben, wenn *alle* Sätze bewiesen sind:

* **T1** Flesch ≥ importierte Schwelle `readability_check.NEW_FLESCH_MIN`
  **und** besser als vorher.
* **T2** kein neuer harter Fund aus `publish_gate.HARTE_REGELN`
  (Textverständnis-Wächter, gemessen mit dem echten Prüfer).
* **T3** `publikations_vertrag.pruefe` (V1–V3, WF-54C4/#607) meldet nichts.
* **T4** Links, `/go/`-Anker, Überschriften, Shortcodes, Tabellenzeilen,
  Zahlen-Multiset und Frontmatter byte-identisch; Länge ≥ 90 %.

Scheitert eine Zeile, bleibt die Datei **byte-identisch** liegen – der Befund
(Restlücke) geht in den Report. „Nicht gemessen" ist niemals „geschrieben".

## Nutzung

```bash
# Trockenlauf (Standard schreibt nichts)
python3 scripts/lesbarkeit_heiler.py --file content/posts/<slug>/index.md

# Entwürfe/Kandidaten heilen (nur drafts; Live-Bestand ist tabu)
python3 scripts/lesbarkeit_heiler.py --blocked --fix      # laut readiness-Zertifikat
python3 scripts/lesbarkeit_heiler.py --holds   --fix      # Gate-Holds der Klasse
python3 scripts/lesbarkeit_heiler.py --new-only --fix     # Artikel des Tages (Live-Engine)
python3 scripts/lesbarkeit_heiler.py --blocked --keine-ki --json   # nur Stufe A

# Der Maschinenvertrag (verlangt der Governance-Vertrag C25)
python3 scripts/lesbarkeit_heiler.py --wirkungsprobe       # Exit 0 = Fixture < 60 → ≥ 60
python3 scripts/lesbarkeit_heiler.py --selftest            # Sabotage- UND Wirkungsprobe
```

**Exit:** 0 = alles über der Schwelle (oder nichts zu tun) · 1 = mindestens
ein Kandidat blieb darunter (fail-closed) · 2 = Selbsttest/Werkzeugfehler.

## Verdrahtung

| Ort | Rolle |
|---|---|
| `reserve_finisher.HEALER_CHAIN` | letzter **Textschritt** der Veredelung (nach allen KI-Umschreibern, vor Linker/URL-Hygiene/Intent) |
| `reserve_healer_coverage.WIRKUNGS_PROBEN` | Wirkungsnachweis statt Namensliste (`wirkungsdeckung()`, `volldeckung()`) |
| `reserve_blocker_klassen.GATE_BEFUNDE` | „lesbarkeit" → Klassen-Heiler |
| `requeue_quality_holds.py` | Lesbarkeits-Holds werden nur mit **belegtem** Effekt rearmt |
| `content-engine-v2.yml` | Phase 0.5 + Phase 2 (Keys ergänzt): Artikel des Tages + Holds |
| `governance_contract` **C25** | „Deckung heißt Wirkung": Struktur **und** grüne Wirkungsprobe |
| `integrity_guard.FEST` | unter Siegel – wer hier heilt, heilt gegen das Tor |

## Grenzen (bewusst)

* **Nur Entwürfe.** Ausnahme ist ausschließlich `--new-only` (Artikel des
  heutigen Datums, den die Auslieferung noch nicht verankert hat). Der
  Live-Bestand gehört der Deploy-/Kadenz-Kette.
* **Stufe A ist ein Hebel, kein Wundermittel.** Bei Texten, deren Flesch an
  den Silben je Wort hängt (Ø Satzlänge bereits < 15 Wörter), ist Stufe B
  erforderlich – genau deshalb ist sie verdrahtet.
* **Die Schwelle wird nie kopiert.** Sie kommt immer aus
  `readability_check` (Lehre #585); C25 prüft das.
