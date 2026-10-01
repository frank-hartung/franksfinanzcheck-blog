# Anleitung: Das Beweissystem (Belege statt Behauptungen)

> Rollout 01.10.2026 · Report: `BEWEISSYSTEM-PREMIUM-2026-10-01.md`
> Vertrag: `data/beweise/schema.yaml` · Wache: `scripts/beweis_gate.py`
> CI: `.github/workflows/beweis-gate.yml`

## Warum es das gibt

Audit-Befund: Der Auftritt behauptete Erfahrung („selbst geprüft“,
„praxisgetestet“, „hunderte Tarifvergleiche“), zeigte aber kaum originäre
Belege. Highend-E-E-A-T entsteht durch **sichtbare Beweise**. Das Beweissystem
macht aus der Methodik-Seite ein prüfbares System mit vier Bausteinen:

| Baustein | SSOT | Öffentlich |
|---|---|---|
| Beweis-Register (Fallstudien, Wechselprotokolle, Messreihen, Modellrechnungen) | `data/beweise/register.yaml` | `/methodik/#beweis-register` + `{{</* beweis */>}}` in Artikeln |
| Vergleichsmethodik je Themenbereich, versioniert | `data/beweise/vergleichsmethodik.yaml` | `/methodik/#vergleichsmethodik-je-themenbereich` |
| Öffentliches Änderungsprotokoll | `data/beweise/korrekturen.yaml` | `/aenderungsprotokoll/` |
| Quelle direkt an der Zahl (Beleg-Chips A/M/E) | `data/kennzahlen_register.yaml` bzw. freie Parameter | `{{</* beleg */>}}` in Artikeln |

## Die drei Belegklassen (öffentliche Dreiteilung)

* **A – amtlich:** Behörden/Institutionen der Allowlist Rang 1–2. Immer mit URL + Stand.
* **M – markt:** eigene reproduzierbare Rechenwege und Tarif-Stichproben mit Abrufdatum.
* **E – erfahrung:** eigene Wechsel/Messungen/Tests – **nur** zitierfähig mit
  Protokoll im Register und intern archivierten Original-Belegen.

Die Erfahrungs-Box in Artikeln (`layouts/_partials/experience_box.html`) trägt
seit dem Rollout eine feste Einordnungszeile: persönliche Einschätzung ≠ Beweis.

## Tägliche Handgriffe

### Eine Zahl im Artikel belegen

```markdown
Der BDEW-Durchschnitt von 37,0 Cent pro kWh{{</* beleg kennzahl="bdew-haushaltsstrompreis" kurz="BDEW" */>}} …
```

Bevorzugt immer `kennzahl=` (ein Stand, überall synchron). Freie Belege:
`{{</* beleg url="https://…" name="Destatis" stand="2026-10-01" klasse="amtlich" */>}}`.

### Einen Beweis im Artikel einbetten

```markdown
{{</* beweis id="mr-tagesgeld-15000" */>}}
```

Nur Einträge mit Status `verifiziert` oder `modellfall` sind einbettbar –
alles andere bricht den Build ab (gewollt).

### Neuen Beweis anlegen

1. Eintrag in `data/beweise/register.yaml` nach `schema.yaml`:
   * unfertig → `status: geplant|in-erhebung` **mit** `dokumentationsplan` + `faellig`
     (erscheint öffentlich nur im Backlog),
   * fertig → `status: verifiziert` mit `stand`, `quellen`, `grenzen`, `changelog`
     und den typ-spezifischen Pflichtfeldern,
   * durchgerechnetes Beispiel ohne realen Fall → `status: modellfall`
     (Rendering erzwingt den Warnhinweis).
2. `python3 scripts/beweis_gate.py` lokal laufen lassen.
3. Bei Klasse E: Original-Belege (Rechnungen, Bestätigungen) intern archivieren,
   öffentlich nur anonymisierte Fassungen; Leser-Fallstudien nur mit schriftlicher
   Einwilligung und Vier-Augen-Prüfung der Anonymisierung.

### Korrektur/Änderung protokollieren

Jede inhaltliche Korrektur, jeder Quellenwechsel, jede Zahlen-Aktualisierung mit
neuem Stand und jeder Methodik-Versionssprung bekommt einen Eintrag **oben** in
`data/beweise/korrekturen.yaml` (datum, typ, titel, was, warum, quelle,
belegklasse, seiten). Kein Eintrag für rein technische Deployments.

### Methodik ändern

Formel/K.-o./Rangfolge in `data/beweise/vergleichsmethodik.yaml` ändern →
`version` erhöhen (SemVer), `changelog` ergänzen, zusätzlich Eintrag im
Änderungsprotokoll. Bewusst **keine Gewichtungs-Prozente** erfinden.

## Die Wache

```bash
python3 scripts/beweis_gate.py            # Prüfung (wie CI)
python3 scripts/beweis_gate.py --selftest # Sabotage-Proben
python3 scripts/beweis_gate.py --history  # + Journal data/beweis_history.jsonl
```

Hart (Build/CI rot): Pflichtfeld-Verstöße, doppelte IDs, tote Dataset-Refs,
unbekannte Kennzahl-/Beweis-Verweise im Content, Beweis-Einbettung unfertiger
Einträge, Protokoll-Sortierung, fehlende Quellen.
Weich (Warnung): B6-Inventar – Erfahrungs-Behauptungen in Artikeln ohne
Beweis-/Beleg-Verweis. Ziel ist, diese Liste über die Zeit auf null zu bringen:
entweder Beleg nachrüsten oder Formulierung zur Einordnung abschwächen.

## Grenzen & Ehrlichkeitsregeln

* Nichts erfinden: Ein Beweis ohne Protokoll ist kein Beweis, sondern ein
  Backlog-Eintrag mit Fälligkeit. Das Register zeigt beides öffentlich.
* Modellfälle sind immer als Modellfall gekennzeichnet – nicht abschaltbar.
* Affiliate-Partner sind als Beleg-Quelle verboten (gleiche Regel wie
  `data/agent_reach/faktenfrische.yaml`).
