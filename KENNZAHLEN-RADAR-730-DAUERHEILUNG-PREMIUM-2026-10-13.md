# 📡 KENNZAHLEN-RADAR #730 – DAUERHEILUNG (PREMIUM-REPORT 2026-10-13)

**Vorgang:** Issue #730 (`Kennzahlen-Radar: 1 fällige Prüfungen (2026-10-13)`)  
**Stichtag:** 2026-10-13 (UTC)  
**Status:** ✅ Vollständig behoben (8/8 Kennzahlen `🟢 OK`, 0 P1/P2/P3, 0 tote Slugs, 0 hinterherhängende Artikel)

---

## 1. Ursachen-Diagnose (Root-Cause-Analyse)

Die Untersuchung des Befunds aus Issue #730 deckte sechs strukturelle und inhaltliche Ursachen auf:

1. **Überfällige Quartals-Kennzahl `bnetza-breitband` (P1) & drohende Fälligkeit `ezb-einlagenzins`:**
   - `bnetza-breitband` stand auf `stand: 2026-07-10` (`alter_tage: 95 > rhythmus_tage: 90`), und zehn `internet-dsl`-Ratgeber trugen im Frontmatter noch das alte BNetzA-Quellendatum `2026-07-10`.
   - `ezb-einlagenzins` stand auf `stand: 2026-09-01` (`alter_tage: 42 == rhythmus_tage: 42`) und wäre bereits am Folgetag (`2026-10-14`, 43 Tage) als nächster P2-Befund eskaliert.
2. **Fehlalarm-Verstärker in `scan_signale()` (`scripts/kennzahlen_radar.py`):**
   - `scan_signale()` durchsuchte den gesamten Rohtext einer Recherche-Datei (`f.read().lower()`). Dadurch matchte der Radar den eigenen Dossier-Kopf (`# Faktenfrische: …`, `- **Suchbegriffe:** …`, `### Suche: …`) sowie Diagnose-Sektionen (`## Offene GEO-Punkte`, `## Kanal-Störungen`) und gescrapte Navigationsmenü-Links (`> * [Breitbandversorgung](…)`) selbst dann, wenn das Dossier explizit `_Keine thematisch passende Fundstelle in diesem Lauf._` meldete.
3. **Falsche Datums-Auflösung in `_research_date()` für Artikel-Dossiers (`data/research/artikel/<slug>.md`):**
   - `_research_date()` prüfte zuerst das Datum im Dateinamen (`_ISO_IN_NAME`). Bei Artikel-Dossiers trägt der Dateiname jedoch das historische Slug-Datum des Artikels (z. B. `2026-08-12-…`) statt des tatsächlichen Erzeugungszeitstempels (`> Automatisch erzeugt von scripts/faktenfrische.py am 2026-10-13`).
4. **Drei verwaiste Slugs (`Slug nicht gefunden`) in `data/kennzahlen_register.yaml`:**
   - `2026-09-10-energie-update-was-sich-jetzt-fuer-dich-aendert` (`bdew-haushaltsstrompreis`)
   - `2026-09-22-konto-karten-update-was-sich-jetzt-fuer-dich-aendert` (`girokonto-kostenlos`)
   - `2026-09-27-rente-2026-so-baust-du-heute-deine-sichere-altersvorsorge` (`grundfreibetrag`, war im Report unsichtbar, da `OK`-Einträge nicht gerendert wurden).
5. **Hinterherhängende & inkonsistente Pillar-Seiten:**
   - `content/pillar/konto-karten/index.md` stand auf `lastmod: 2026-08-31` (< `2026-09-28` von `girokonto-kostenlos`).
   - `content/pillar/strom-sparen/index.md` zeigte nach dem Flagship-Umbau (v2.2) in den Marktradar-Karten und Quellentiteln wieder `36,8 ct/kWh` (Strom) und `10,2 ct/kWh` (Gas) statt der verifizierten Registerwerte `37,0 ct/kWh` (`bdew-haushaltsstrompreis`) und `11,93 ct/kWh` (`bdew-gaspreis-efh`).
6. **Unsichtbare `OK`-Kopplungswarnungen & fehlende Gate-Prüfung:**
   - `render_report()` gab nur `P1`, `P2` und `P3` aus; Kopplungsfehler (`Slug nicht gefunden`, `hinterher`) auf `OK`-Kennzahlen verschwanden unsichtbar aus `KENNZAHLEN-RADAR.md`.
   - `scripts/beweis_gate.py` prüfte zwar `{{< beleg kennzahl="…" >}}`-Verweise gegen das Register, validierte aber nicht umgekehrt, ob alle `betroffene_slugs` aus `data/kennzahlen_register.yaml` unter `content/` existieren.

---

## 2. Durchgeführte Dauerheilung

### A. Register, Belege & Content-Synchronisation
- **`data/kennzahlen_register.yaml`:**
  - `bnetza-breitband`, `ezb-einlagenzins` und `bnetza-energie-marktdaten` nach Prüfung und Artikel-Synchronisation auf `stand: 2026-10-13` aktualisiert.
  - Drei verwaiste Slugs durch die aktiven Live-Ratgeber ersetzt (`2026-08-31-nachtstrom-tarife-wann-sich-ein-doppeltarifzaehler-noch-lohnt`, `2026-08-12-geld-abheben-im-ausland-gebuehren-vermeiden`, `2026-10-05-bueroausstattung-steuerlich-clever-absetzen-so-vermeidest`).
  - Suchbegriffe präzisiert, damit generische Einzelwörter in Wochenbriefen keine Schein-Signale auslösen.
- **Pillar- und Ratgeber-Bestand (`content/`):**
  - `content/pillar/strom-sparen/index.md`: Marktradar-Karten und Quellentitel auf `37,0 ct/kWh` und `11,93 ct/kWh` synchronisiert (`lastmod: 2026-10-13`, `faktencheck: "2026-10-13"`).
  - `content/pillar/konto-karten/index.md`: Quellen- und Prüfstand auf `2026-10-13` aktualisiert (`hinterher`-Warnung aufgelöst).
  - `content/pillar/internet-dsl/index.md` sowie alle 10 gekoppelten `internet-dsl`-Ratgeber und 3 `ezb-einlagenzins`-Ratgeber auf aktuellen Quellen-/Prüfstand (`2026-10-13`) gebracht.
- **`data/beweise/korrekturen.yaml`:**
  - Öffentlichen Protokolleintrag zum Stichtag `2026-10-13` ergänzt.

### B. Härtung der Radar- & Gate-Logik
- **`scripts/kennzahlen_radar.py`:**
  - `_research_date()`: Liest zuerst den expliziten Generator-Zeitstempel (`Automatisch erzeugt … am/um YYYY-MM-DD`), bevor auf das Dateinamen-Datum zurückgefallen wird.
  - `_extrakt_signal_text()`: Filtert Dossier-Metadaten, eigene Such-Überschriften, Leer-Platzhalter (`_Keine …_`), Diagnose-Sektionen und gescrapte Navigationsmenü-Linklisten vor dem Keyword-Abgleich heraus.
  - `render_report()` & `write_queue()`: Rendert auch die Sektion `## 🟢 OK – im Rhythmus` (inkl. etwaiger Kopplungswarnungen) und exportiert `kopplungs_warnungen` in `data/kennzahlen_radar.json`.
  - `plan_issue_action()`: Deterministische Lifecycle-Logik (`create`, `edit`, `close`, `none`) für das GitHub-Issue.
- **`scripts/beweis_gate.py`:**
  - Neue Prüfung **B7 (`pruefe_kennzahlen_slugs`)**: Jeder in `data/kennzahlen_register.yaml` unter `betroffene_slugs` geführte Slug muss unter `content/` existieren (inkl. Sabotage-Probe 6 im `--selftest`).
- **Tests (`scripts/tests/test_kennzahlen_radar.py`):**
  - Auf 20 Unit-Tests erweitert (inkl. Produktiv-Register-Kopplungswache, Generator-Datums-Vorrang, Dossier-Fehlalarm-Schutz, OK-Report-Sektion und Issue-Lifecycle-Plan), verifiziert unter `selftest_clock.py` (+97d / +1461d).

---

## 3. Optionaler Workflow-Diff (`.github/workflows/kennzahlen-radar.yml`)

Falls der wöchentliche Workflow offene `kennzahlen-radar`-Tickets bei `0` fälligen Prüfungen künftig vollautomatisch schließen und bestehende Tickets aktualisieren soll (Agent-Token besitzt vereinbarungsgemäß keine `workflows`-Push-Permission):

```diff
--- a/.github/workflows/kennzahlen-radar.yml
+++ b/.github/workflows/kennzahlen-radar.yml
@@ -91,15 +91,26 @@ jobs:
           ANZAHL=$(python3 -c "import json;print(json.load(open('data/kennzahlen_radar.json'))['count'])" 2>/dev/null || echo 0)
           SCHWELLE=$(python3 -c "import yaml;print((yaml.safe_load(open('data/kennzahlen_register.yaml')).get('meta') or {}).get('melden',{}).get('issue_ab_faellig',1))" 2>/dev/null || echo 1)
+          OFFEN=$(gh issue list --repo "$GITHUB_REPOSITORY" --state open --label kennzahlen-radar --json number --jq '.[0].number // empty' 2>/dev/null || true)
           if [ "$ANZAHL" -ge "$SCHWELLE" ]; then
             TITEL="Kennzahlen-Radar: $ANZAHL fällige Prüfungen ($(date +%F))"
-            if ! gh issue list --repo "$GITHUB_REPOSITORY" --state open \
-                 --search "in:title \"Kennzahlen-Radar:\"" | grep -q .; then
+            if [ -z "$OFFEN" ]; then
               gh issue create --repo "$GITHUB_REPOSITORY" \
                 --title "$TITEL" --label kennzahlen-radar \
                 --body-file KENNZAHLEN-RADAR.md
             else
-              echo "Offenes Kennzahlen-Ticket existiert – kein Duplikat."
+              gh issue edit "$OFFEN" --repo "$GITHUB_REPOSITORY" \
+                --title "$TITEL" --body-file KENNZAHLEN-RADAR.md
             fi
           else
-            echo "$ANZAHL fällig (< $SCHWELLE) – kein Ticket."
+            if [ -n "$OFFEN" ]; then
+              gh issue close "$OFFEN" --repo "$GITHUB_REPOSITORY" \
+                --comment "✅ Alle registrierten Kennzahlen sind wieder im Prüf-Rhythmus (Stand $(date +%F))."
+            else
+              echo "$ANZAHL fällig (< $SCHWELLE) – kein Ticket."
+            fi
           fi
```
