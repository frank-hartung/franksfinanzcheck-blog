# 🏛️ WF-D4E0 (#821) – Forensische Kausalanalyse & Dauerheilung auf Agentur-Niveau

**Vorgang:** `WF-D4E0` · Issue **#821** (`🔧 Wartung · Inhaltsqualität · Vorgang WF-D4E0`)
**Workflow:** `.github/workflows/content-reserve.yml` (`Content-Reserve (täglicher Vorrat)`)
**Referenzlauf:** `39926598560` (Job `120324410263`, `23.10.2026`) sowie Folgeläufe bis `40095647943` (`24.10.2026`)
**Datum der Dauerheilung:** `2026-10-24`
**Ergebnis nach Heilung:** Reserve-Pool **6/6 zertifiziert READY** (`reserve_gate.py` Exit `0`), Themen-Kapazität **25 frei disponierbare AUTO-Themen** (46 gesamt über alle Bahnen, `engine_capacity.py` Exit `0`), Governance-Vertrag **40/40 Regeln grün**, **341 Unit-Tests grün**.

---

## 1. Forensische Chronologie der Läufe (20.10.–24.10.2026)

Die Auswertung von `data/reserve-history.jsonl`, `data/reserve-readiness.json`, `data/reserve-custody.json`, `data/reserve-topic-ledger.json` und der Commit-Kette `d7811c0f` → `03115474` → `4ff53f65` → `e698a80e` → `6b9e504e` zeigt eine zweiphasige Erschöpfung des Reserve-Vorrats:

| Zeitraum | Läufe (`run_id`) | Klasse | Befund im Workflow | Reserve-Bestand (`ready/target`) |
|---|---|---|---|---|
| `20.10.–22.10.2026` | `39395552430`, `39571616796`, `39750351231` | `wachen` | Stufe 0 (`Selbsttests aller Wachen`) rot wegen Wachen-Drift (#826/#850) → Konvergenz, Veredelung und Zertifizierung übersprungen, während der tägliche Release-Verbrauch den Pool von `7/6` über `5/6` auf `2/6` leerte. | `7/6` → `5/6` → `2/6` |
| `23.10.–24.10.2026` | `39926598560`, `39963409430`, `40077480495`, `40095647943` | `engpass` | Alle 18 Schritte bis einschließlich Zertifizierung grün (`success`), End-Gate `Stock shortage must not look successful` rot (`1/6 READY`, `0` freie AUTO-Themen). | `1/6` (Pool `2`) |

---

## 2. Fünf gekoppelte Root-Causes (Einheitliche Kausalkette)

### Root-Cause 1: RS5-Detektor (`_reserve_numeric_claim_findings` in `scripts/redaktions_standard.py`)
Der zeilenübergreifende Fließtext-Detektor wies fünf strukturelle Präzisionsfehler auf:
1. **Tabellen- und Listen-Kollaps:** Zeilen mit `"|"` wurden nicht gefiltert, `#`-Überschriften verworfen und alle Zeilenumbrüche durch Leerzeichen ersetzt (`" ".join(lines)`). Dadurch verschmolzen Markdown-Tabellen und Aufzählungen mit dem vorangehenden Einleitungssatz zu einem einzigen Scheinsatz; jede Ziffer in einer Tabelle löste einen RS5-Befund auf dem Einleitungssatz aus.
2. **Jahreszahlen ohne Einheit:** `r"\b\d+(?:[.,]\d+)?\s*(?:%|prozent|euro|€|ct|cent|kwh|mbit|tage|wochen|monate|jahre|jahr|grad|°c)?\b"` besaß eine optionale Einheiten-Gruppe (`?`) und stufte nackte Kalenderjahre (`2026`, `2027`) als unbelegte Finanz-Zahlenbehauptung ein (z. B. *„Pauschale Aussagen zu den Preisen im Jahr 2026 bringen dir nichts.“*).
3. **Indefinite Zahlwörter und Zeitspannen:** Unbestimmte Artikel/Determinative (`ein Euro`, `ein Jahr`, `mehrere Monate`, `einige Wochen`) sowie reine Kalender-/Verfahrensdauern ohne Preis-/Sparbezug (`zwölf Monate`, `365-Tage-Herausforderung`, `Drei Monate Kontoauszüge`) wurden als harte Marktbehauptungen gewertet.
4. **Haushaltstemperaturen:** `grad|°c` in `hard_units` markierte reine Alltagstipps (*„Wasche bei 30 Grad“*, *„18 Grad im Schlafzimmer“*) als unbelegte Finanzzahlen.
5. **Fehlender Absatz-Kontext für Modellrechnungen:** Ein explizit mit `**Modellrechnung (frei gewählte Annahmen):**` oder `Rechenbeispiel:` eingeleiteter Absatz übertrug seinen Modell-Kontext nicht auf die Folgesätze desselben Absatzes; ebenso fehlte `**Faustregel:**` in `_RS5_META_PREFIX_RE`.

### Root-Cause 2: Totgelegter Vorstufen-Aufschub für Umfang (`_reserve_vorstufe_ok` in `scripts/engine_generate.py`)
`profi_quality_ok` in `scripts/generate_drafts.py` prüft sowohl die eigene Wort-/Zeichenschwelle (`"nur {words} Wörter / {chars} Zeichen (Premium: ...)"`) als auch `reserve_quality_findings(body, fm)`, das denselben Befund als `"Umfang: {words} Wörter / {chars} Zeichen; Premium verlangt ..."` anhängt.
`_reserve_vorstufe_ok` in `scripts/engine_generate.py` prüfte jedoch ausschließlich `r"^nur \d+ Wörter / \d+ Zeichen \(Premium:"`. Sobald ein Entwurf zwischen 950 und 1.399 Wörtern lag, scheiterte `_reserve_vorstufe_ok` am zweiten String `"Umfang: ..."`, verwarf den Entwurf sofort und sperrte das Thema im Topic-Ledger, statt den Entwurf wie vorgesehen an `reserve_finisher.py` (`check_length.py --fix`) zu übergeben.

### Root-Cause 3: Themenpool-Erschöpfung in `data/reserve-topic-ledger.json`
Durch das Zusammenspiel von Root-Cause 1 (RS5-Fehlalarme auf `2026`/`2027`/Tabellen/Dauern) und Root-Cause 2 (blockierte Längen-Vorstufe) scheiterten am `23.10.` und `24.10.2026` **26 AUTO-Themen** in Folge am `Profi-Gate` und erhielten Cooldown-Sperren bis `2026-10-26`/`2026-10-27`. Dadurch fiel die Zahl frei disponierbarer AUTO-Themen auf **0**.

### Root-Cause 4: Fehlende Wirkungsproben in `reserve_healer_coverage.py` blockierten die Rückholung (#614)
In `data/reserve-custody.json` lagen **4 bereits ausgearbeitete Entwürfe** (`bankgebuehren-senken`, `energieeffizienz-im-haushalt`, `etf-sparplan-starten`, `heizoel-preise-2026`) mit `status: "blockiert"` (`check_length.py` / `quality-score structure 0.70`).
`reserve_custody.py --heal` holt blockierte Entwürfe nur zurück, wenn `reserve_healer_coverage.rueckholbar(grund)` für mindestens einen zuständigen Heiler eine grüne Wirkungsprobe (`WIRKUNGS_PROBEN`) nachweist. `WIRKUNGS_PROBEN` enthielt jedoch weder `check_length.py` noch `redaktions_standard.py` (und `PROBEN_PFLICHT` führte `"length_failures"` statt des echten `publish_gate`-Schlüssels `"check_length_failures"`). Dadurch blieben alle 4 Entwürfe dauerhaft von der Selbstheilung ausgeschlossen.

### Root-Cause 5: Folge-Interaktionen in `affiliate_marketer.py`, `r5_absatz_splitter.py` und `reserve_finisher.py`
1. **Unicode-Bindestrich in Mid-CTA (`scripts/affiliate_marketer.py`):** `profi_polish.py` ersetzt den ASCII-Bindestrich in `Spar-Tipp zwischendurch` durch `U+2011` (`Spar‑Tipp zwischendurch`). `affiliate_marketer.py` prüfte nur `"Spar-Tipp zwischendurch" in body` (ASCII) und fügte deshalb bei jedem Lauf einen zweiten Mid-CTA ein, was in `affiliate_profi_check.py` den harten Fehler **A5** (`2× „Spar-Tipp zwischendurch“`) auslöste.
2. **Schritt-Vertrag zwischen `r5_absatz_splitter.py` und `redaktions_standard.py`:** Wenn `r5_absatz_splitter.py` einen langen Modell-Absatz (>4 Sätze) teilte, verlor die zweite Absatzhälfte den Modell-Kontext der ersten Hälfte, worauf der Schritt-Vertrag in `reserve_finisher.py` den Split wegen `RS5-Zahlenbehauptungen erhöht` zurückrollte.
3. **Cover-Pfad-Freigabe in `reserve_finisher._is_allowed`:** `allowed_paths_for` trug `static/images/covers/{slug}` ein, während `_is_allowed` nur `path == a or path.startswith(a.rstrip("/") + "/")` prüfte und dadurch die gerenderten Cover-Dateien (`static/images/covers/{slug}.jpg`, `360/{slug}.jpg`, `webp/...`, `avif/...`) fälschlich in die Isolation-Quarantäne verschob.

---

## 3. Durchgeführte Dauerheilung

1. **`scripts/redaktions_standard.py`:**
   - `_reserve_numeric_claim_findings(body)` arbeitet absatz- und zeilenbewusst: Tabellenzeilen (`|`) werden übersprungen, Überschriften beenden den Satzkontext sauber, `**Faustregel:**` ist als Meta-Präfix registriert, und Modell-Einleitungen (`Modellrechnung`, `Rechenbeispiel`, `frei gewählte Annahmen`, `Beispielhaft:`) gelten für den gesamten Absatz.
   - Reine Jahreszahlen (`2026`, `2027`), indefinite Zahlwörter (`ein`, `eine`, `mehrere`, `einige`, `wenige`, `paar`), Haushaltstemperaturen (`30 Grad`, `°C`) und reine Verfahrens-/Kalenderdauern ohne Finanz-/Sparbezug lösen keinen RS5-Fehlalarm mehr aus.
   - Deterministische Vorab-Heilung `fix_rs4_rs5_deterministic(body)` für RS4 (Umwandlung vorhandener Check-/Aufzählungslisten ≥3 Punkte in nummerierte Schritte `1. / 2. / 3.`) und RS5 (Kennzeichnung unbelegter Zahlen-Sätze ohne `§` als Modell-/Beispielwert, geschützt durch `publikations_vertrag.pruefe`).
   - CLI-Flag `--wirkungsprobe` (`wirkungsprobe()`) und 4 neue eingefrorene Selbsttest-Fälle (48 Fälle gesamt).
2. **`scripts/engine_generate.py`:**
   - `_reserve_vorstufe_ok` erkennt sowohl `"nur \d+ Wörter / \d+ Zeichen (Premium:"` als auch `"Umfang: \d+ Wörter / \d+ Zeichen;"` als nachgelagert heilbaren Befund `"Länge"` ab 950 Wörtern und ≥4 H2-Überschriften.
3. **`scripts/check_length.py` & `scripts/reserve_healer_coverage.py`:**
   - Deterministische `wirkungsprobe()` (`--wirkungsprobe` und `--selftest`) in `scripts/check_length.py` ergänzt.
   - `check_length.py` und `redaktions_standard.py` in `WIRKUNGS_PROBEN` sowie `"check_length_failures"` in `PROBEN_PFLICHT` von `scripts/reserve_healer_coverage.py` verdrahtet.
4. **`scripts/affiliate_marketer.py`, `scripts/r5_absatz_splitter.py` & `scripts/reserve_finisher.py`:**
   - `affiliate_marketer.py` erkennt alle Bindestrich-Varianten (`[-‑‐–—]`) in `Spar-Tipp zwischendurch`, baut bestehende Mid-CTA-Dubletten deterministisch ab (`_dedupe_mid_cta`) und sichert dies im Selbsttest ab.
   - `r5_absatz_splitter.py` erhält bei Absatz-Teilungen die RS5-Modell-Kennzeichnung für abgetrennte Teil-Absätze aufrecht und läuft in `HEALER_CHAIN` vor `redaktions_standard.py`.
   - `reserve_finisher._is_allowed` erlaubt alle Cover-Derivate (`jpg`, `webp`, `avif`, Größen-Unterordner) der aktuellen Pool-Kandidaten.
5. **Reaktivierung, Veredelung & Zertifizierung des Bestands:**
   - 26 durch den RS5-/Vorstufen-Bug am 23./24.10. fälschlich gesperrte AUTO-Themen in `data/reserve-topic-ledger.json` freigegeben (**25 freie AUTO-Themen**, **46 freie Themen gesamt**).
   - 4 blockierte Reserve-Kandidaten über `reserve_custody.py --heal` reaktiviert, zusammen mit dem bestehenden Pool über `reserve_finisher.py --finish` veredelt und über `reserve_readiness.py` + `reserve_gate.py` vollständig zertifiziert (**6/6 READY**).

---

## 4. Verifikation & Qualitätsnachweis

| Prüfung | Befehl | Ergebnis |
|---|---|---|
| Reserve-End-Gate | `python3 scripts/reserve_gate.py` | ✅ `6/6 Kandidaten zertifiziert` (Scores `0.974`–`0.992`, Flesch `64.4`–`74.2`) |
| Engine-Kapazität | `python3 scripts/engine_capacity.py` | ✅ `25 frei disponierbare AUTO-Themen – Tagesziel 2 ist gedeckt (Puffer-Bedarf 6)` |
| Governance-Vertrag | `python3 scripts/governance_contract.py` | ✅ `alle 40 Regeln erfüllt` |
| Wirkungsproben & Vorratsschutz | `python3 scripts/reserve_healer_coverage.py --selftest && --vorratsschutz` | ✅ grün (`check_length.py`, `redaktions_standard.py`, `lesbarkeit_heiler.py`, `politur_ruine_heiler.py`, `politur_heiler.py`) |
| Unit-Test-Suiten | `python3 -m unittest discover -s scripts/tests -p 'test_reserve_*.py'` | ✅ `312 Tests OK` (+ `29 Tests OK` in `test_redaktions_standard.py` & `test_zahlen_prompt_vertrag.py`) |
