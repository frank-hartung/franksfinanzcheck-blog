# 🛡️ Bestand-Gate Premium-Fix (Issue #149)

**Datum:** 2026-09-02 · **Status:** umgesetzt & verifiziert · **Betroffenes Issue:** [#149 – Bestand-Gate: bestehende Artikel brauchen Aufmerksamkeit](https://github.com/frank-hartung/franksfinanzcheck-blog/issues/149)

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
   `BESTAND-REPORT.md` meldete „Selbstheilung fehlgeschlagen" bei jedem
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

## 2. Was ist jetzt umgesetzt?

### 2.1 `scripts/bestand_gate.py`

- **Eindeutige Exit-Semantik** (analog zur Affiliate-Integritäts-Wache):
  - `0` = grün (Bestand konform / erfolgreich geheilt)
  - `1` = Inhaltsschaden (nach Heilung weiter auffällig → echte Textarbeit)
  - `2` = **Auswertungsfehler / Detektor-Drift** (fail-closed, nichts geheilt)
- **Maschinenlesbarer Zustand** `.bestand_gate_state.json` mit `exit_code`,
  `checked`, `still_affected`, `errors`, `healing_attempted`.
- **Konvergenz-Schutz**: Der Zustand wird nur bei inhaltlicher Änderung
  geschrieben (flüchtiger Zeitstempel raus). Ruhige Tage erzeugen damit
  keinen Git-Diff, keinen Commit und keinen Deploy-Trigger – gleiches
  Prinzip wie `.affiliate_integrity_state.json`.

### 2.2 `.github/workflows/seo-weekly.yml`

- **Detektor-Selbsttest als Vorbeweis** im Bestand-Gate-Schritt: Die Wache
  muss erst *sehen* können, bevor sie urteilt. Bricht der Selbsttest, endet
  der Schritt mit Exit `2` und klarer Handlungsanweisung – statt wieder
  Phantom-„0 Links"-Funde zu produzieren.
- **Exit-Code als Step-Output** (`exit_code=0/1/2`) für die Folgeschritte.
- **Idempotente Issue-Pflege** (Marker `<!-- bestand-gate -->`):
  - EIN offenes Issue pro Schadenslage – kein wöchentliches Duplikat mehr.
  - Bei Rot: vorhandenes Issue wird **aktualisiert**, nicht neu erstellt;
    weitere Duplikate werden geschlossen.
  - Bei Grün: offene Bestand-Gate-Issues werden **automatisch geschlossen**
    – auch Alt-Issues ohne Marker wie **#149** (Erkennung über den
    Legacy-Titel).
  - **Werkzeug- vs. Inhaltsschaden** wird im Issue unterschieden: Exit `2`
    bzw. fehlender Exit-Code → Werkzeugfehler-Issue mit Anleitung
    (`--selftest`, Drift-Wächter gegen `render-link.html`).
  - Alt-Issues werden mit dem Label `auto-report` versehen, damit sie der
    bestehende Aufräum-Workflow (`issue-cleanup.yml`) nach der Schonfrist
    dauerhaft löschen darf.
- **Diagnose-Artefakt** bei Rot: `BESTAND-REPORT.md`, Zustandsdatei und
  Gate-Log als GitHub-Artifact (14 Tage), damit der Befund auch lesbar
  bleibt, wenn das Log-Zip nicht erreichbar ist.

### 2.3 Patch (falls der Workflow-Push abgelehnt wird)

`.github/workflows/`-Änderungen können je nach Token-Grant abgelehnt werden
(Haus-Konvention, siehe `AFFILIATE-INTEGRITY-GATE-REPORT.md`). Für diesen
Fall liegt der Workflow-Diff bei:

```bash
git apply patches/bestand-gate-premium-2026-09-02-workflows.patch
git add .github/workflows/seo-weekly.yml
git commit -m "fix(ci): Bestand-Gate idempotent (Issue #149)"
```

---

## 3. Verifikation

| Prüfung | Ergebnis |
|---|---|
| `python3 scripts/affiliate_integrity_gate.py --selftest` | ✅ grün (attribut-toleranter Anker-Parser inkl. `?subid=`, Legacy-, unminifiziertem Format, AI1–AI3, AI5, Heilung, Build-Frische, Drift-Wächter) |
| `python3 -m py_compile scripts/bestand_gate.py` | ✅ OK |
| `yaml.safe_load` für `.github/workflows/seo-weekly.yml` | ✅ valide |
| `node --check` für die Issue-Pflege-Skriptlogik | ✅ syntaktisch sauber |
| Statischer Markdown-Check (AI1–AI3) über 25 Live-Artikel | ✅ 0 Struktur-Funde |
| `BESTAND-REPORT.md` (aktueller Stand) | ✅ 26 geprüfte Live-Artikel · 0 weiterhin auffällig |
| `AFFILIATE-INTEGRITY-REPORT.md` | ✅ alle Render-Beweise `Markdown → HTML` geprüft |

---

## 4. Warum es jetzt dauerhaft hält

1. **Werkzeugfehler können nicht mehr als „Content kaputt" erscheinen.**
   Der Bestand-Gate-Exit-Code unterscheidet `1` (Inhalt) von `2`
   (Detektor/Build/pfad). Das Issue nennt die richtige Ursache inkl.
   Anleitung statt „24 Artikel suchen".
2. **Ein Issue pro Schadenslage, mit Lebenszyklus.** Grün schließt die
   Meldung automatisch; Aufräumen übernimmt der bestehende
   `issue-cleanup`-Workflow. Die Issue-Flut (#76/#78/#95/#99/#137/#146)
   und der Alt-Liegenbleiber #149 werden damit dauerhaft verhindert.
3. **Beweis vor Urteil.** Der Detektor-Selbsttest und die
   Massen-Blindheits-Erkennung laufen vor jeder Bewertung; Layout-/Hook-
   Änderungen führen zu „laut rot mit Anleitung", nie wieder zu „still grün
   obwohl blind".
4. **Kein Commit-Churn.** Zustands- und Reportdateien werden nur bei
   inhaltlicher Änderung geschrieben. Ruhige Tage lösen weder Commit noch
   Deploy noch Issue aus.

---

_Erstellt im Rahmen der Arena-Session `arena/01a062e3-franksfinanzcheck-blog`._
