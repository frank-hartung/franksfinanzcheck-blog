# 🛡️ Bestand-Gate Premium-Fix (Issue #149) – V2 selbstständig

**Datum:** 2026-09-02 · **Status:** umgesetzt & verifiziert · **Betroffenes Issue:** [#149 – Bestand-Gate: bestehende Artikel brauchen Aufmerksamkeit](https://github.com/frank-hartung/franksfinanzcheck-blog/issues/149) (von Frank manuell geschlossen, 16:42 UTC)

---

## 1. Was war das Problem?

`bestand_gate.py` prüft den **gesamten Live-Bestand** gegen die aktuelle
Publish-Gate-Pflicht (Länge, SEO, Affiliate-Profi, Affiliate-Integrität)
und heilt Funde automatisch, ohne Bestandsartikel je zu löschen.

Die alte Rufkette hatte aber zwei dauerhafte Schwächen, die zusammen
Issue #149 erzeugt haben:

1. **Fehlersemantik war nicht eindeutig.** Der Render-Beweis AI4 hing früher
   an einer starren Attribut-Reihenfolge der HTML-Ausgabe. Nach der
   Render-Hook-Erweiterung (`?subid=`, Umami-Kontext) zählte die alte
   Auswertung in **24/24 Artikeln** exakt `0` gerenderte Affiliate-Links,
   obwohl alle Links korrekt im gebauten HTML standen. Ergebnis:
   `BESTAND-REPORT.md` meldete „Selbstheilung fehlgeschlagen“ bei jedem
   Artikel – ein Phantom-Fund, kein echter Content-Schaden.

2. **Issue-Pflege war nicht idempotent.** Der wöchentliche Workflow hat bei
   jedem roten Bestand-Gate-Lauf ein **neues** Issue eröffnet und bei Grün
   nie wieder geschlossen. Darum blieb #149 offen, obwohl der Bestand
   längst grün war (`BESTAND-REPORT.md`: 26 Live-Artikel, 0 auffällig;
   `AFFILIATE-INTEGRITY-REPORT.md`: alle Render-Beweise ✅).

Die eigentliche Detektor-Heilung (attribut-tolerantes Parsen, AI5,
Selbsttest, Drift-Wächter) war bereits vorhanden. Es fehlte die **dauerhafte
Betriebsabschottung**, damit so etwas nie wieder als offene, nicht
auflösbare Meldung liegen bleibt.

---

## 2. V2: Alles in einem Skript – kein Workflow-Patch, kein manueller Schritt

Die V1 (PR #154) hat den Workflow-Patch nachgeliefert, weil die
Issue-Pflege in `actions/github-script` lag und der Agent-Token keine
`workflows`-Permission hat. **V2 zieht die komplette Betriebslogik in
`scripts/bestand_gate.py`** – `.github/workflows/seo-weekly.yml` bleibt
unverändert und ruft das Skript wie bisher auf (`hugo --minify` +
`python3 scripts/bestand_gate.py`, das braucht nur `contents: write` +
`issues: write`, beides bereits vorhanden). Damit ist **kein Patch, kein
Terminal, kein zusätzlicher Token** nötig.

### 2.1 Detektor-Selbsttest als Vorbeweis

Vor jeder Bewertung läuft `scripts/affiliate_integrity_gate.py --selftest`:

- **Grün** → Bewertung wie gewohnt (Beweis vor Urteil).
- **Rot / Detektor-Drift** → **fail-closed**: keine Bewertung, **keine
  Heilung, kein Verwurf**, Exit `2`, Report „Bestand gilt als NICHT
  geprüft“ + Anleitung (Drift-Wächter gegen `render-link.html`).

`python3 scripts/bestand_gate.py --selftest` führt nur den Vorbeweis aus
(Exit `0`/`2`) – für lokale Diagnose und CI.

### 2.2 Eindeutige Exit-Codes

| Code | Bedeutung |
|---|---|
| `0` | grün – Bestand konform bzw. erfolgreich geheilt |
| `1` | Inhaltsschaden – nach Heilungsversuch bleibt etwas offen (echte Textarbeit) |
| `2` | Auswertungsfehler / Detektor-Drift – fail-closed, nichts geheilt/verworfen |

### 2.3 Idempotente Issue-Pflege direkt im Skript (GitHub-API)

`manage_issues()` nutzt `GITHUB_TOKEN` + `GITHUB_REPOSITORY` (stdlib
`urllib`, keine Extra-Dependency; lokal ohne Token wird sauber
übersprungen, `--dry-run` ist read-only):

- **Marker** `<!-- bestand-gate -->` in jedem gepflegten Issue.
- **EIN offenes Issue pro Schadenslage.** Bei Rot wird das vorhandene
  Issue **aktualisiert** (Titel + Body + Kommentar), nie dupliziert;
  weitere Duplikate werden geschlossen.
- **Bei Grün automatische Schließung** mit Erklärung – auch **Alt-Issues
  ohne Marker** wie **#149** (Erkennung über Legacy-Titel und feste
  Legacy-Nummern, Standard `149`, per Env
  `BESTAND_GATE_LEGACY_ISSUES` anpassbar).
- **Werkzeug- vs. Inhaltsschaden getrennt:** Exit `2` → Titel „Auswertung
  nicht möglich (Werkzeugfehler, fail-closed)“ mit Handlungsanleitung;
  Exit `1` → Titel „bestehende Artikel brauchen Aufmerksamkeit“.
- Der **alte JS-Schritt** in `seo-weekly.yml` (`Issue bei nicht
  automatisch heilbaren Bestandsartikeln`) ist damit überflüssig. Er
  kann beim *ersten* Rot-Lauf noch ein Duplikat ohne Marker erzeugen –
  das Skript erkennt es beim Folgelauf über den Legacy-Titel, schließt es
  als Duplikat bzw. bei Grün mit. (Der Workflow selbst bleibt bewusst
  unangetastet, token-bedingt und weil er nicht mehr gebraucht wird.)

### 2.4 Maschinenlesbarer Zustand & Konvergenz

`.bestand_gate_state.json` (Exit-Code, geprüft, geheilt, offen, Fehler)
wird **nur bei inhaltlicher Änderung** geschrieben; flüchtige Zeitstempel
sind vom Fingerprint ausgenommen → ruhige Tage erzeugen keinen Diff,
keinen Commit, keinen Deploy-Trigger (gleiches Prinzip wie
`.affiliate_integrity_state.json`).

### 2.5 Obsoleter Patch entfernt

`patches/bestand-gate-premium-2026-09-02-workflows.patch` wird mit V2
**gelöscht**: Der Workflow-Diff ist nicht mehr nötig und würde die
Selbstpflege nur doppeln (Selbsttest + Issue-Logik lägen dann zwei Mal vor).

---

## 3. Verifikation (V2)

| Prüfung | Ergebnis |
|---|---|
| `python3 -m py_compile scripts/bestand_gate.py` | ✅ OK |
| `python3 scripts/bestand_gate.py --selftest` | ✅ grün (Exit 0) |
| Drift-Simulation (Selbsttest Exit 7) | ✅ fail-closed: Exit 2, „NICHT geprüft“, keine Heilung |
| `--json` | ✅ reines JSON (selftest, exit_code, checked, errors) |
| Issue-Pflege Fall 1 (grün, Legacy #149 offen) | ✅ Kommentar + `state=closed` auf #149 |
| Fall 2 (rot, 1 vorhandenes Marker-Issue) | ✅ aktualisiert statt dupliziert (kein Create) |
| Fall 3 (rot, Marker + Legacy-Duplikat) | ✅ #42 aktualisiert, #149 als Duplikat geschlossen |
| Fall 4 (Exit 2, keins vorhanden) | ✅ Werkzeugfehler-Issue erstellt |
| Fall 5 (`--dry-run`) | ✅ ausschließlich Lesezugriffe (read-only) |
| Fall 6 (ohne `GITHUB_TOKEN`) | ✅ sauber übersprungen, Exit unverändert |
| Live-API (Read-only): `list_open_issues` + Matching | ✅ funktioniert (2 offene Issues erkannt; #149 war zu Testzeit bereits geschlossen) |
| Statischer Markdown-Check (AI1–AI3) über Live-Artikel | ✅ 0 Struktur-Funde (aus V1) |
| `AFFILIATE-INTEGRITY-REPORT.md` | ✅ alle Render-Beweise `Markdown → HTML` geprüft (aus V1) |

---

## 4. Warum es jetzt dauerhaft hält

1. **Werkzeugfehler können nicht mehr als „Content kaputt“ erscheinen.**
   Der Exit-Code unterscheidet `1` (Inhalt) von `2` (Detektor/Build).
   Der Detektor-Selbsttest läuft **vor** jeder Bewertung; Layout-/Hook-
   Änderungen führen zu „laut rot mit Anleitung“, nie wieder zu „still
   grün obwohl blind“.
2. **Ein Issue pro Schadenslage, mit Lebenszyklus.** Rot aktualisiert,
   Grün schließt – automatisch, inklusive Alt-Issue #149. Die Issue-Flut
   (#76/#78/#95/#99/#137/#146) und der Alt-Liegenbleiber #149 werden
   dauerhaft verhindert.
3. **Kein Workflow-Patch, kein manueller Schritt.** Die Betriebslogik
   lebt im Skript; der bestehende Wochenlauf trägt sie automatisch aus.
4. **Kein Commit-Churn.** Zustands- und Reportdateien werden nur bei
   inhaltlicher Änderung geschrieben. Ruhige Tage lösen weder Commit noch
   Deploy noch Issue aus.

---

_V2 erstellt im Rahmen der Arena-Session `arena/01a062f7-franksfinanzcheck-blog`
(Ersatz für die nicht wiederherstellbare lokale Version `d5dcce1` aus
`arena/01a062e3-franksfinanzcheck-blog`; V1 = gemergter PR #154)._
