# Content-Reserve WF-D4E0 · #710 – Vollständige Dauerheilung auf Highend-Agentur-Niveau

**Datum:** 12.10.2026
**Auslöser:** Der Content-Reserve-Lauf **38240822821** (Schedule, 12.10.2026 11:09 UTC) wurde im Schritt **„Stock shortage must not look successful“** rot; das Fehler-Alerting meldete das als Issue **#710** (`auto-report`, Alert-Key `WF-D4E0`, Bereich *Inhaltsqualität*).
**Stand vorher:** **5/6** gate-fertig (Ziel 6, 6 von 11 Kandidaten blockiert).
**Stand nach der Komplettheilung:** **11/6** gate-fertig (**11 von 11** Pool-Kandidaten mit `hugo 0.164 Extended` + `hunspell/de_DE` + `publish_gate --strict` zertifiziert, **0 Blocker**, Quarantäne leer `{}`).

---

## 1. Forensische Ursachenkette (warum WF-D4E0 nach #687 erneut auftrat)

Die Analyse der Commits `76425b2` (Reserve-Lauf vom 12.10.2026 11:18 UTC) und `ea92f36` zeigte sieben ineinandergreifende Ursachen:

1. **Vier seit #687 (10.10.2026) ungeheilte Pool-Kandidaten** (`energieausweis`, `kleine-energiespar-tricks`, `stromkosten-senken`, `waermepumpe-vs-gasheizung`) belegten dauerhaft 4 von 12 Pool-Plätzen.
2. **Aktive Nach-Korruption durch `scripts/profi_polish.py` (Schritt 1 in `reserve_finisher.HEALER_CHAIN`):**
   - Weil `reserve_finisher.lift_to_today()` unzertifizierte Entwürfe jeden Tag auf `<heute>-<stamm>` umbenennt und `profi_polish.py` seinen Cache nach dem datierten `slug` schlüsselte, polierte `profi_polish.py` unzertifizierte Entwürfe jede Nacht neu.
   - Der Prompt in `profi_polish.py` verlangte „konkrete Zahl in der Einleitung“ sowie „ca. X–Y €“ / „in der Regel“ (Widerspruch zum harten RS5-Gate).
   - `profi_polish.verify()` prüfte weder `publikations_vertrag.pruefe` noch `redaktions_standard.reserve_quality_findings` noch `/go/`-Affiliate-Links – und zerstörte am 12.10.2026 in `2026-10-12-energieausweis-...` die `**Faustregel:**` (RS3), die nummerierte Schrittfolge (RS4), den `/go/strom/`-Link und drückte Flesch auf `59,0`.
3. **Weitere Prompt↔Gate-Widersprüche in Heilern und Generatoren:**
   - `scripts/redaktions_standard.py` (`heal_article_ai`) wies die KI an, Zahlen mit „ca./rund/Spanne“ bzw. „ca. X–Y €“ einzuordnen, und prüfte nach der KI-Heilung nur den weichen Detektor `detect_rs5` statt `_reserve_numeric_claim_findings`.
   - `scripts/generate_drafts.py` forderte in der Einleitung noch eine „überraschende Zahl“.
   - `scripts/extend_articles.py` und `scripts/update_articles.py` verlangten „Zahlen und Beispiele“ bzw. „ca. 30–40 €“ ohne RS5-Modellanker und ohne `publikations_vertrag`.
4. **Titel-Verstümmelung durch `pinterest_seo_healer.ensure_colon_title()` und blinder Fleck in `check_titles.py` (R4):**
   - `ensure_colon_title()` setzte bei Titeln mit Komma oder Gedankenstrich blind einen zusätzlichen Doppelpunkt (`Kleine Energiespar‑Tricks,: die …`, `Wärmepumpe vs. Gasheizung 2026: – so …`) oder trennte zwischen flektiertem Adjektiv und Nomen (`geringeren: Monatskosten`).
   - `check_titles.py` erkannte `,:`, `;:` und `: –` in R4 nicht und heilte sie bei `--fix` nicht.
5. **Fehlende Heiler-Integration und fehlender Schritt-Rollback in `reserve_finisher.py`:**
   - `Reserve-Qualitäts-Gate` (`RS1`–`RS8`) fehlte in `scripts/reserve_blocker_klassen.py` (`GATE_BEFUNDE`).
   - `redaktions_standard.py` unterstützte weder `--include-drafts` noch `--file` und lief nicht in `reserve_finisher.HEALER_CHAIN`.
   - `reserve_finisher.run_chain()` besaß keinen Schritt-Vertrag, der Kandidaten bei neu eingeführten harten Defekten sofort auf den Zustand vor dem jeweiligen Heiler-Schritt zurückrollt.
6. **Quarantäne-Amnesie in `scripts/reserve_quarantine.py`:**
   - Durch die tägliche Umbenennung in `lift_to_today()` vor `reserve_quarantine.record()` ging der bisherige Zähler (`<alt-datum>-<stamm>`) verloren; `hits` fiel jeden Tag wieder auf `1` zurück.
7. **Fehlende Schluss-Verknüpfung in PR #718:**
   - PR #718 enthielt kein `Closes #710`, sodass `scripts/vorgangs_abschluss.py` das Issue #710 übersprang.

---

## 2. Vollständige Heilung des Reserve-Bestands (11/11 READY)

Alle 11 Kandidaten des Reserve-Pools bestehen das vollständige Produktions-Gate (`hugo --minify` + `publish_gate.py --strict` + `quality_score.py` inkl. `hunspell/de_DE`):

| Reserve-Kandidat | Status | Quality-Score | Flesch |
|---|---|---|---|
| `2026-10-07-urlaub-sparen-7-clevere-wege-deine-kasse-zu-fuellen` | ✅ READY | `0.984` | `61.1` |
| `2026-10-07-wie-smart-home-geraete-deine-stromrechnung-wirklich-druecken` | ✅ READY | `0.984` | `62.5` |
| `2026-10-09-balkonkraftwerk-foerderung-so-holst-du-dir-geld-zurueck` | ✅ READY | `0.950` | `61.0` |
| `2026-10-09-energiekosten-senken-smarte-helfer-fuer-den-haushalt` | ✅ READY | `0.910` | `60.0` |
| `2026-10-09-vpn-zuhause-schutzschild-oder-unnoetige-fixkosten-falle` | ✅ READY | `0.966` | `64.4` |
| `2026-10-12-dein-weg-zu-geringeren-monatskosten-schritt-fuer-schritt` | ✅ READY | `0.954` | `60.1` |
| `2026-10-12-haushaltskosten-reduzieren-so-gewinnst-du-die-kontrolle` | ✅ READY | `0.978` | `60.8` |
| `2026-10-12-energieausweis-was-das-dokument-fuer-deine-fixkosten` | ✅ READY | `0.984` | `66.7` |
| `2026-10-12-kleine-energiespar-tricks-die-deine-kosten-sofort-senken` | ✅ READY | `0.960` | `63.2` |
| `2026-10-12-stromkosten-senken-clevere-haushaltsgeraete-im-ueberblick` | ✅ READY | `0.970` | `71.5` |
| `2026-10-12-waermepumpe-vs-gasheizung-2026-so-entscheidest-du-richtig` | ✅ READY | `0.982` | `65.1` |

---

## 3. Systemische Dauerheilung (Code & Verträge)

1. **`scripts/profi_polish.py`:**
   - Datumsloser Cache-Schlüssel (`_cache_key`) verhindert wiederholtes Umschreiben nach `lift_to_today()`.
   - `_already_gate_clean()` überspringt Entwürfe, die Flesch ≥ `NEW_FLESCH_MIN`, 0 harte Textverständnis-Funde und 0 `reserve_quality_findings` bereits erfüllen.
   - `build_polish_prompt()` verlangt RS5-konforme Satz-Kennzeichnung (`Beispielrechnung`/`Modellrechnung`) und Bewahrung von `**Das Wichtigste in Kürze**`, `**Faustregel:**`, nummerierten Schrittfolgen, Frage-H2 und `/go/`-Links.
   - `verify()` prüft vor dem Schreiben `/go/`-Link-Erhalt, `publikations_vertrag.pruefe` (V1–V3 fail-closed) und `redaktions_standard.reserve_quality_findings` + `_reserve_numeric_claim_findings`.
   - Eigener `--selftest` ergänzt und in `selftest_runner.py` integriert.
2. **`scripts/redaktions_standard.py`:**
   - Unterstützt `--include-drafts` und `--file <pfad>`.
   - `fix_rs2_rs3_deterministic()` heilt fehlende Frage-H2 (RS2) und fehlende `**Faustregel:**` (RS3) deterministisch unter Schutz von `_vertrag_gruende`.
   - `heal_article_ai()` nutzt RS5-konforme Prompts und verwirft Antworten, die `_reserve_numeric_claim_findings` erhöhen.
3. **`scripts/generate_drafts.py`, `scripts/extend_articles.py`, `scripts/update_articles.py`, `scripts/tests/test_zahlen_prompt_vertrag.py`:**
   - Alle verbleibenden Hedge-Anweisungen („ca. X–Y €“, „ca. 30–40 €“, „überraschende Zahl“) beseitigt; `extend_articles.py` prüft vor dem Schreiben `publikations_vertrag.pruefe` und `redaktions_standard`.
   - `test_zahlen_prompt_vertrag.py` verriegelt alle fünf Schreib-/Heiler-Prompts gegen das RS5-Gate.
4. **`scripts/pinterest_seo_healer.py` & `scripts/check_titles.py`:**
   - `ensure_colon_title()` wandelt vorhandene Gedankenstriche (` – `) und Kommas sauber in `: ` um, vermeidet Schnitte nach flektierten Adjektiven/Funktionswörtern und bereinigt Doppel-Interpunktion.
   - `check_titles.py` erkennt und heilt `,:`, `;:` und `: –` deterministisch in R4 (alle 82 Bestandstitel: `0 Verstöße`).
5. **`scripts/reserve_blocker_klassen.py` & `scripts/reserve_finisher.py`:**
   - `Reserve-Qualitäts-Gate` in `GATE_BEFUNDE` als `HEILBAR` registriert.
   - `redaktions_standard.py` (`--fix --ai --include-drafts --file`) in `HEALER_CHAIN` verdrahtet.
   - `_kandidat_regressionen()` und `_step_guard_enforce()` rollen jeden Heiler-Schritt in `run_chain()` sofort zurück, falls er neue harte Defekte (Publikations-Vertrag V1/V2, RS1–RS8, Titel R1–R5) einführt.
6. **`scripts/reserve_quarantine.py`:**
   - Datumslose Stamm-Migration (`_stamm`) erhält Quarantäne-Zähler über `lift_to_today()`-Umbenennungen hinweg.
