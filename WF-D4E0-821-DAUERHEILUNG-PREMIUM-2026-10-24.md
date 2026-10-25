# 🏛️ WF-D4E0 (#821) – Forensische Kausalanalyse & Dauerheilung auf Agentur-Niveau

**Vorgang:** `WF-D4E0` · Issue **#821** (`🔧 Wartung · Inhaltsqualität · Vorgang WF-D4E0`)
**Workflow:** `.github/workflows/content-reserve.yml` (`Content-Reserve (täglicher Vorrat)`)
**Referenzlauf:** `39926598560` (Job `120324410263`, `23.10.2026`) sowie Folgeläufe bis `40095647943` (`24.10.2026`)
**Datum der Dauerheilung:** `2026-10-24` · **Highend-Finalisierung & Neu-Zertifizierung:** `2026-10-25` (Nachführung von PR #855 auf den aktuellen `main`-Stand, Abschnitt 5)
**Ergebnis nach Heilung:** Reserve-Pool **6/6 zertifiziert READY** (`reserve_gate.py` Exit `0`), Themen-Kapazität **25 frei disponierbare AUTO-Themen** (46 gesamt über alle Bahnen, `engine_capacity.py` Exit `0`), Governance-Vertrag **40/40 Regeln grün**, **341 Unit-Tests grün**.
**Endstand nach der Finalisierung (25.10.2026):** Reserve-Pool **6/6 zertifiziert READY** (frisches Zertifikat `2026-10-25T13:46:01Z`, Scores `0.974`–`0.992`), Themen-Kapazität **25 frei disponierbare AUTO-Themen**, Governance-Vertrag **41/41 Regeln grün**, **3.671 Unit-Tests grün** (Vollsuite, Uhr-Probe bei +97 Tagen, 312 davon Reserve-Suite), Integritäts-Siegel neu signiert (50 Kerndateien, Herkunft `b5138a1b`).

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

## 5. Highend-Finalisierung 25.10.2026 – Übernahme von PR #855 auf den aktuellen `main`-Stand

PR **#855** trug beide roten Pflicht-Checks ins Gesicht: `Integritäts-Siegel` (FAIL) und `regression` (FAIL). Diese Durchführung (Branch `arena/1e64c915-franksfinanzcheck-blog`) übernimmt den Heilungs-Commit `c7696d51` auf den aktuellen `main`-Tip `b5138a1b` (47 Commits jünger als der PR-Basis) und macht beide Checks dauerhaft grün.

### 5.1 Diagnose der beiden roten Checks von #855

| Check | Ursache (forensisch) | Dauerhafte Behebung |
|---|---|---|
| `Integritäts-Siegel` | Zwei gesperrte Kerndateien (`scripts/affiliate_marketer.py`, `scripts/redaktions_standard.py`) waren geändert, aber `data/integrity_lock.json` nicht mit-signiert (Exit 3, „VERSIEGELBAR", Warnung des Gates). | `python3 scripts/integrity_guard.py --set-current` – **50 Kerndateien** gegen SHA-256 neu versiegelt, Herkunft `b5138a1b` im Lock, **im SELBEN Commit** (Vertrag aus `docs/PFLICHT-CHECK-RUNBOOK.md`). |
| `regression` | Der PR-Basis war veraltet: `test_faktenfrische_763.py` erwartete den Kadenz-Slug `2026-10-14-…` (Inhalt längst umbenannt), `test_newsletter_digest.WorkerListeTest` kannte den getrennten `NEWSLETTER_WORKER_WRITE_KEY`-Vertrag noch nicht, und `test_integrity_guard` scheiterte am offenen Lock. | Port auf den `main`-Tip (die Fixes aus #823/#846/#859 sind dort enthalten); alle drei Funde entfallen, Siegel-Test grün nach dem Commit. |

### 5.2 Konfliktlösungen beim Port (5 Konflikte, einzeln begründet)

| Datei | Lösung |
|---|---|
| `content/posts/2026-10-25-strategisch-sparen-…/index.md` | Die redaktionellen Textkorrekturen des PR übernommen („Eine volle Urlaubskasse beginnt…", klebrige Satzartefakte „als du es Entscheidend sind…", Fußnoten-Splice „Reisepreisentwicklung 2 Unsere…"), die Kadenz-Datierung `10-25` von `main` beibehalten, duplizierter `Schnell-Tipp`-Mid-CTA (A5-Dublette zu `Spar‑Tipp zwischendurch`) entfernt. |
| `data/covers_manifest.json` | `heizperiode`-Eintrag von `main` behalten (deckt sich mit dem aktuellen Titel), vier `2026-10-24-…`-Einträge der PR-Seite vereint, `saison-update`-Eintrag auf den `HEAD`-Stand zurückgesetzt – sonst wäre der Cover-Check mit `1 STALE` rot gewesen. |
| `data/reserve-custody.json` | Geheilter PR-Stand plus Slug-Nachführung `2026-10-24-strategisch…` → `2026-10-25-strategisch…`. Endstand: **6 im Pool · 0 ohne Fahne · 0 Rückläufer · 0 ausgemustert**. |
| `data/reserve-quarantine.json` | PR-Stand `{}` – der präzisiere RS5-Detektor meldet keinen Fund mehr, die Neu-Zertifizierung hat keinen Eintrag neu erzeugt. |
| `data/reserve-readiness.json` | Der PR-Stand galt nur als Ausgangspunkt: **komplett neu zertifiziert** (5.3), alle sechs `sha256`-Fingerabdrücke messen die finalen Bytes. |

### 5.3 Vollständige Neu-Zertifizierung an der ECHTEN Messkette

Statt Zertifikate umzuschreiben, wurde die Produktions-Messkette lokal exakt rekonstruiert: **Hugo Extended `0.164.0`** (PyPI-Distribution, dieselbe Version wie `install-hugo`), **Hunspell `1.7.2`** (aus den offiziellen Quellen `github.com/hunspell/hunspell` gebaut) und das **de_DE-Frami-Wörterbuch** (LibreOffice dictionaries). `reserve_recert.gate_verfuegbar()` meldet `True` („Gate-Werkzeug vollständig"), die Kontrollprobe erkennt exakt `Fheler`.

Damit lief `python3 scripts/reserve_readiness.py` vollständig durch – pro Kandidat `quality_score` + `publish_gate --strict` + Hugo-Render-Beweis: **6/6 READY**, Zertifikat `2026-10-25T13:46:01Z`, Spelling-Anteile `0.94`–`1.00`, keine Quarantäne-Wiederaufnahme.

Zusätzlich gegenüber #855 bereinigt:
- `image:`-Frontmatter von `bankgebuehren-senken` und `energieeffizienz-im-haushalt` von den alten `2026-10-06-…`-Coverpfaden auf die neu gerenderten `2026-10-24-…`-Cover umgestellt (der PR hatte zwei von vier Cover-Pfaden offengelassen).
- Sechs echte `affiliate_profi_check`-Auditzeilen des Zertifizierungslaufs in `data/audit/2026-10-25.jsonl` angehängt (append-only, C27-konform – die Tests danach schreiben nichts).

### 5.4 Verifikation (Endstand, 25.10.2026, Exit 0 wo nicht anders vermerkt)

| Prüfung | Befehl | Ergebnis |
|---|---|---|
| Reserve-End-Gate | `scripts/reserve_gate.py` | ✅ `6/6 Kandidaten zertifiziert`, Zertifikat `0.0 h` alt |
| Reserve-Snapshot (#634) | `scripts/reserve_artifacts.py --check` | ✅ `vollständig: eindeutiges JSON, echte READY-Bytes und Redaktionsvertrag` |
| Engine-Kapazität | `scripts/engine_capacity.py` | ✅ `25 frei disponierbare AUTO-Themen – Tagesziel 2 ist gedeckt` |
| Governance-Vertrag | `scripts/governance_contract.py` | ✅ `alle 41 Regeln erfüllt` (in beide Richtungen) |
| Wirkungsproben & Vorratsschutz | `scripts/reserve_healer_coverage.py --selftest` / `--vorratsschutz` | ✅ grün (inkl. `check_length.py` + `redaktions_standard.py`) |
| RS5-Selbsttest & Wirkungsprobe | `scripts/redaktions_standard.py --selftest` / `--wirkungsprobe` | ✅ `48 eingefrorene Fälle` · `RS5 2 → 0, Fixpunkt bestätigt` |
| Längen-Wirkungsprobe | `scripts/check_length.py --wirkungsprobe` | ✅ `142W/979Z (zu-kurz) → 1922W/12964Z (ok), Fixpunkt bestätigt` |
| Cover-Check | `scripts/check_covers.py` | ✅ `101 Covers · 0 Probleme · 0 stale · 0 brand · 0 text` |
| Integritäts-Siegel | `scripts/integrity_guard.py --gate` / `--selftest` | ✅ `50 Kerndateien entsprechen exakt dem signierten Stand (HEAD b5138a1b)` |
| Actions-Versionen & Artefakte | `actions_version_guard --gate` · `artefakt_waechter` · `gsc_artefakte_guard --check` | ✅ grün · `481 Artefakte strukturell heil` · grün |
| Workflow- & Frontmatter-Audits | `automation_premium_audit --strict` · `fm_boundary_guard --check` | ✅ grün |
| Unit-Test-Vollsuite | `unittest discover -s scripts/tests` | ✅ `3671 Tests` – vor dem Commit genau 1 erwarteter Fund (`test_ausgeliefertes_siegel_ist_committet` exaktiert den Siegel-Commit), danach grün |
| Uhr-Probe (+97 Tage) | `selftest_clock.py --trap-discover scripts/tests --offset 97` | ✅ `3671 Tests` – derselbe einzig erwarteter Vorab-Fund, keine Zeitbombe |
| KI-/Netz-Probe | `selftest_ki.py --selftest` / `--trap-workflows` | ✅ grün (kein Selbsttest am Modell oder Netz) |
| Ledger-Isolation (C27) | `audit_log.py --selftest` · `repo_isolation.py --selftest` | ✅ grün, `data/audit/` nach den Tests unverändert |
| Reserve-Suiten & RS-Vertrag | `test_reserve_*.py` · `test_redaktions_standard.py` + `test_zahlen_prompt_vertrag.py` | ✅ `312 Tests OK` · `29 Tests OK` |
