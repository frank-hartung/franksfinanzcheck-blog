# Governance-Report #712 · Lesbarkeits-Wache – Vollständige Dauerheilung auf Highend-Agentur-Niveau

**Datum:** 12.10.2026
**Auslöser:** Premium-Governance-Lauf vom 12.10.2026 (13:12 UTC), Issue **#712** (`governance`, Ampel **AMBER**, Fingerabdruck `a69d19423d76`); einziger „Zu beheben"-Befund: **Lesbarkeits-Wache (Bestand)** – Entwürfe unter der Publish-Schwelle 60 (`read_draft`).
**Stand vorher:** **9** Entwürfe unter der Publish-Schwelle (Flesch **38,2–56,4**), Endredaktion **1 blockiert / 8 optimiert**, Bestands-Gate AMBER. Das Issue nannte drei Namen (Report-Kürzung), der Report alle neun.
**Stand nachher:** **0** Entwürfe unter der Schwelle, Bestands-Gate **GREEN** (44 Live-Artikel, Ø Flesch **67,5**, kein Live-Artikel unter 55), Endredaktion **24 grün / 8 optimiert / 0 blockiert**.

---

## 1. Forensische Ursachenkette (warum dieselben Namen Woche für Woche wiederkamen)

1. **Die Klasse hatte keinen Adressaten.** Der Lesbarkeits-Heiler kannte drei Quellen: `--holds` (Gate-Park), `--blocked` (Reserve-Zertifikat), `--new-only` (Artikel des Tages). Entwürfe, die aus einer **anderen Rolle** stammten (`news_writer` „ChatGPT/News“, `ki_redaktion`) und einfach „zu dicht" lagen, hatten keinen Gate-Hold und damit in **keiner** Kette einen Aufrufer. Sie alterten im Vorrat, bis das Publish-Gate sie anließ.
2. **Eine Heilung ohne Wirkungsnachweis.** `endredaktion.politur_pruefen()` verifizierte Links, Überschriften, Länge und Floskeln – **nicht die Lesbarkeit**. Eine Politur-Antwort mit unverändert schlechter Flesch-Zahl galt als „sauber", wurde geschrieben, der Entwurf blieb gelb und wurde nie freigegeben (Governance-Regel C25, Lehre #609).
3. **E6 in Rot war eine Sackgasse.** `Flesch < 45` ergab „blockiert"; die Politur lief nur bei `optimieren`. Der Artikel `2026-10-08-energie-update` (Flesch 38,2) blockierte zwei Tage lang das Gate – ohne Ausweg.
4. **Der Schreiber maß nicht.** `news_writer.py` erzeugte News-Kompakt-Artikel gegen die Längen-SSOT (min 10 500 / Ziel 12 000 Zeichen) und lieferte ~7 000 – **und kannte die Publish-Schwelle überhaupt nicht**. Der Ausschuss entstand im Generator und musste von drei Wachen später eingesammelt werden (Lehre WF-D4E0/#612: Wer schreibt, muss messen, was über ihn entscheidet).
5. **Zweite Wahrheit drohte.** Der Heiler ist mit einer Wirkungsprobe zertifiziert (C25) und unter Siegel; die Nachsorge hätte ihre eigene Satz-Zerlegung bauen können – zwei Messungen, dieselbe Bauart wie der SSOT-Bruch aus #585.
6. **Kein Sweep in der Kette.** Der CI-Lauf fuhr nur `--new-only --fix` (Artikel des Tages). Für den Vorrat gab es keinen geplanten Lauf – der Befund war damit strukturell dauerhaft.

---

## 2. Vollständige Heilung des Bestands (9/9 über der Publish-Schwelle)

Alle neun Entwürfe wurden redaktionell neu gefasst: kurze Sätze (Ø 7,7–10,5 Wörter), aktive Verben statt Nominalstil, kurze Wortformen statt Komposita. Die Invarianten wurden **gegen HEAD** mit dem Tor T1–T4 des Heilers (`verifiziere`) geprüft – alle neun: **keine Gründe** (Frontmatter byte-identisch, Links und `/go/`-Anker unverändert, Überschriften/Shortcodes/Tabellenzeilen erhalten, Zahlen-Multiset identisch, Länge ≥ 90 %).

| Slug | Flesch vorher | Flesch nachher | Länge (Rohdatei) |
|---|---|---|---|
| `2026-10-08-energie-update-was-sich-jetzt-fuer-dich-aendert` | 38,2 | **63,8** | 101,2 % |
| `2026-10-06-markt-update-was-sich-jetzt-fuer-dich-aendert` | 47,1 | **65,3** | 97,3 % |
| `2026-10-07-notgroschen-aufbauen-wie-viel-reicht-wirklich` | 50,8 | **64,9** | 93,3 % |
| `2026-10-12-stromfresser-im-haushalt-entlarven` | 52,0 | **63,0** | 91,9 % |
| `2026-10-07-heizoel-preise-2026-so-findest-du-den-optimalen-kaufzeitpu` | 52,5 | **62,3** | 98,1 % |
| `2026-10-09-7-gewohnheiten-fuer-finanzielle-freiheit` | 53,1 | **62,5** | 95,3 % |
| `2026-10-06-bankgebuehren-senken-7-schritte-zum-guenstigeren-konto` | 54,4 | **64,5** | 90,6 % |
| `2026-10-07-etf-sparplan-starten-schritt-fuer-schritt-zum-monatlichen` | 56,2 | **66,6** | 95,2 % |
| `2026-10-06-energieeffizienz-im-haushalt-5-schnelle-spartricks` | 56,4 | **66,3** | 90,6 % |

Commit: `d68a9f4` – danach `readability_check.py --gate-bestand --report LESBARKEIT-REPORT.md` → **Entwürfe unter Publish-Schwelle: 0**.

---

## 3. Systemische Dauerheilung (Code, Kette, Verträge)

| Ebene | Ort | Zusage |
|---|---|---|
| **Nachweis** | `scripts/endredaktion.py` | `LESBARKEITS_SCHWELLE = readability_check.NEW_FLESCH_MIN` (importiert, keine zweite Zahl); `politur_pruefen()` misst Flesch **vorher/nachher** und den Längen-Floor – fail-closed; `politur_auftrag()` nennt **IST und ZIEL** (Lesbarkeit und Länge); `deterministische_fixes()` behandelt E6 über `lesbarkeit_heiler.stufe_a` **als Bibliothek** + Tor `verifiziere` (eine Satz-Zerlegung im Haus); `lauf()` öffnet `heilbares_rot` (E6 rot ⇒ Politur statt Sackgasse); LEKTOR_SYSTEM 4a: der stärkste Hebel ist die Silbe (Formel + Beispiele). |
| **Adressat** | `scripts/lesbarkeit_heiler.py` | Vierte Quelle `hole_entwuerfe()`/`--entwuerfe`: **alle** Entwürfe unter der importierten Schwelle, schlechteste zuerst; ein Sweep ohne Kandidaten endet mit **Exit 0** und Klartext statt argparse-Fehler (die Wochen-Nachsorge darf bei gesundem Bestand nicht rot werden). |
| **Aufrufer** | `.github/workflows/content-engine-v2.yml` | Phase 3 fährt `lesbarkeit_heiler.py --entwuerfe --fix || echo …` direkt neben `--new-only --fix` – mit denselben Gratis-Keys (Stufe B), fail-closed, im Optimierungs-Commit. |
| **Produzent** | `scripts/news_writer.py` | Regel 1a im System-Prompt; `lesbarkeit_sichern()` **vor** dem Schreiben: messen → Stufe A → Tor, sonst ehrlicher Status („redaktionelle Nachsorge nötig" inkl. Aufrufhinweis); der Tail (CTA/Disclaimer) bleibt außerhalb von Messung und Heilung; Log + Kurier-Report nennen den Status. |
| **Vertrag** | `scripts/governance_contract.py` | **C36 „Die Nachsorge beweist die Kennzahl"**: importierte Schwelle, Wirkungsmessung, `heilbares_rot`, Stufe-A-Verdrahtung, `lesbarkeit_sichern` verdrahtet, `--entwuerfe` vorhanden **und in der Kette aufgerufen**, Regressionstests vorhanden, Selbsttest der Nachsorge läuft jetzt (Exit 0). **Sieben Sabotage-Proben** beweisen die Wirkung. |
| **Tests** | `scripts/tests/` | `test_endredaktion.py::TestPoliturWirkung` (5), `test_lesbarkeit_heiler.py::NachsorgeAuswahlTests` (2), **neu** `test_news_writer_lesbarkeit.py` (6). Lauf: **22 / 31 / 6** Tests grün. |
| **Haus-Aufruf** | `package.json` | `npm run lesbarkeit:nachsorge` = `lesbarkeit_heiler.py --entwuerfe --fix`. |
| **Siegel** | `data/integrity_lock.json` | `lesbarkeit_heiler.py` ist eine gesiegelte Kerndatei (Klasse FEST): Änderung zuerst committet (`fd16147`), dann über `integrity_guard.py --heal` neu signiert; Herkunft im Lock (`art: heal`, `VERSIEGELBAR`). |

---

## 4. Beweise (alle Befehle am 12.10.2026 ausgeführt)

| Befehl | Ergebnis |
|---|---|
| `readability_check.py --gate-bestand --report LESBARKEIT-REPORT.md` | ✅ **GREEN** – 44 Live-Artikel Ø **67,5**, kein Live-Artikel unter Floor 55, **32 Entwürfe, 0 unter der Publish-Schwelle 60** |
| `endredaktion.py --nur-pruefen` | ✅ 32 geprüft – **24 grün, 8 optimiert, 0 blockiert** (vorher 23/8/**1**) |
| `lesbarkeit_heiler.verifiziere()` gegen HEAD für alle 9 Dateien | ✅ **keine Gründe** (T1–T4), Flesch 62,3–66,6 |
| `lesbarkeit_heiler.py --selftest` | ✅ Wirkungsprobe **51,3 → 72,3**, Tor T1–T4 weist Sabotage ab |
| `lesbarkeit_heiler.py --entwuerfe --keine-ki` | ✅ Exit 0 – „kein Entwurf unter der Publish-Schwelle 60 – nichts zu tun" |
| `endredaktion.py --selftest` | ✅ Sicherheitsvertrag, Urteils-Logik, Konfig-Wache, Lektor-Prompt |
| `readability_check.py --selftest` | ✅ R6-Schwellen, Shortcode-Stripping, Bestands-Urteil |
| `governance_contract.py` (Voll-Audit) | ✅ **GOVERNANCE-VERTRAG erfüllt – alle 34 Regeln** |
| `governance_contract.py --selftest` | ✅ C1–**C36** mit Kunstbefunden (7 C36-Sabotagen erkannt) |
| `python3 -m unittest …test_endredaktion …test_lesbarkeit_heiler …test_news_writer_lesbarkeit` | ✅ 22 / 31 / 6 Tests grün |
| `integrity_guard.py --drift-audit` | ✅ **Kein Drift – 49 Kerndateien entsprechen dem signierten Stand** |
| `integrity_guard.py --gate` | ✅ Integritäts-Gate grün (HEAD `e0e4bed`) |

---

## 5. Ehrliche Restlücke

- **Länge (E2):** Acht der neun Artikel liegen im Fließtext noch unter dem Floor 10 000 Zeichen (5 400–9 600 Rohzeichen) und stehen darum bei der Endredaktion auf „optimieren" statt „grün". Das ist **kein** Lesbarkeits-Befund aus #712, sondern die Längen-Klasse; sie wird von der bestehenden Kette (`length_guard --fix --ai` in der Content-Engine, deterministische Ausformulierung) geheilt und blockiert nichts.
- **KI-Pfade lokal nicht gefahren:** Ohne `GROQ_API_KEY`/`GEMINI_API_KEY` laufen Stufe B und die KI-Politur nur in CI; geprüft sind sie hier über die **Attrappen-Proben** des Heiler-Selbsttests und die neuen Wirkungsnachweis-Tests der Endredaktion.
- **Kein Endredaktions-Voll-Lauf ohne `--nur-pruefen`:** Ein Voll-Lauf hätte im Modus `automatisch` bis zu einen Entwurf freigegeben (Re-Queue → `cadence_guard`). Die Freigabe-Entscheidung gehört in die Kette, nicht in eine Prüfsitzung – die Zahlen oben stammen deshalb aus dem Prüf-Modus.

---

## 6. Was jetzt dauerhaft verhindert, dass der Befund zurückkommt

1. **Der Befund hat einen Adressaten** (`--entwuerfe`) **und einen Aufrufer in der Kette** (Content-Engine Phase 3, täglich Mo–Fr) – eine Auswahl ohne Fahrer wäre die nächste „Deckung ohne Wirkung" gewesen; C36 prüft darum auch den Aufruf.
2. **Die Nachsorge muss wirken, nicht nur laufen:** Jede Politur wird gegen die importierte Schwelle gemessen; ohne Messung, ohne Bewegung oder unter dem Floor wird nichts geschrieben (fail-closed).
3. **Die rote Lesbarkeits-Klasse ist keine Sackgasse mehr:** E6 rot wird deterministisch (Stufe A + Tor) oder per KI politiert – beides mit Nachweis.
4. **Der Schreiber kann keinen stillen Ausschuss mehr erzeugen:** Er misst vor dem Schreiben und meldet die Restlücke ehrlich.
5. **Sieben Sabotage-Proben halten den Vertrag:** Fällt eine Zusage (Wirkungsmessung, importierte Schwelle, `heilbares_rot`, `lesbarkeit_sichern`, `--entwuerfe`, Kettenaufruf, Regressionstests), wird der Vertrags-Selbsttest rot – im CI, nicht erst im nächsten Governance-Report.

**Schließt:** `Closes #712`.
