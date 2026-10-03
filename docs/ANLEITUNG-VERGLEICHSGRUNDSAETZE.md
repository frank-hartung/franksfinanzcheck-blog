# Anleitung: Vergleichsgrundsätze („So entstehen unsere Vergleiche")

> Rollout 03.10.2026 · Audit-Befund 8 („Monetarisierung und Vertrauen
> müssen sauberer austariert werden") · Wache:
> `scripts/vergleichsgrundsaetze_gate.py` · CI:
> `.github/workflows/vergleichsgrundsaetze-gate.yml` + finales
> Transparenz-Gate im Deploy.

## Was das System ist

Die öffentliche Seite [/so-entstehen-unsere-vergleiche/](https://franksfinanzcheck.de/so-entstehen-unsere-vergleiche/)
beantwortet die sieben Audit-Fragen zur Monetarisierung als
**Bewertungsraster**, nicht als Fließtext:

| Frage | Quelle der Antwort |
|---|---|
| V1 Welche Anbieter werden berücksichtigt? | Aufnahmekriterien (kuratiert) + Routen-Register aus `data/affiliate_ziele.yaml` (gebacken) |
| V2 Welche werden ausgeschlossen und warum? | `ausschluesse` in `data/vergleichsgrundsaetze.yaml`, je mit Pflicht-Begründung |
| V3 Wie entsteht die Reihenfolge? | Grundsatz (kuratiert) + Rangfolge je Bereich aus `data/beweise/vergleichsmethodik.yaml` |
| V4 Zählt Provision in der Bewertung? | Wörtlich „nein" – vertraglich eingefroren, siehe unten |
| V5 Gibt es Mindestkriterien? | Globale Grundsätze + K.-o.-Kriterien je Bereich aus der Methodik |
| V6 Wann wird ein Link deaktiviert? | Auslöser-/Reaktions-Paare (kuratiert, gespiegelt an `affiliate_health.py`/Intent-Wache) |
| V7 Fehlende/nicht vergleichbare Tarife? | `luecken`-Regeln (kuratiert) |

**SSOT-Prinzip:** Das Routen-Register und die K.-o.-/Rangfolge-Blöcke
werden beim Seitenbau aus denselben Dateien erzeugt, die auch Links und
Methodik speisen. Eine neue `/go/`-Route oder ein Methodik-Versionssprung
erscheint automatisch im Raster – nichts wird doppelt gepflegt.

## Dateien

| Datei | Rolle |
|---|---|
| `data/vergleichsgrundsaetze.yaml` | kuratierte Antworten (SemVer-Version + Changelog-Pflicht) |
| `layouts/shortcodes/vergleichsgrundsaetze.html` | Rendering je Abschnitt (`abschnitt="kopf"`, `"v1"` … `"v7"`); trägt die Detektor-Fingerabdrücke `data-ff-vg*` |
| `content/so-entstehen-unsere-vergleiche/index.md` | öffentliche Seite (Überschriften im Markdown → ToC) |
| `assets/css/extended/zz-vergleichsgrundsaetze.css` | `.ff-vg*`-Styles, Dark Mode über Marken-Tokens |
| `scripts/vergleichsgrundsaetze_gate.py` | Wache V1–V8, fail-closed, 13 Sabotage-Proben im `--selftest` |

## Die Verträge der Wache (V1–V8)

* **V1** Seite existiert, trägt Kopf + alle sieben Antwort-Abschnitte genau einmal.
* **V2** Routen-Register in beide Richtungen synchron zu `data/affiliate_ziele.yaml` (fehlende UND erfundene Routen blocken).
* **V3** Zieltyp-Ehrlichkeit: `abweichung`-Routen (Einzelangebot, Portalstartseite, Bündelprodukt) dürfen nie als „Marktvergleich" gerendert werden; der Erklärtext der Abweichung muss sichtbar sein.
* **V4** `provision.antwort` MUSS wörtlich `nein` sein, sichtbar als „Nein.", mit ≥ 3 benannten Durchsetzungs-Mechanismen. **Wer diese Antwort ändern will, muss zuerst die Wache ändern – öffentlich und mit Begründung im Änderungsprotokoll.**
* **V5** Jeder Methodik-Bereich erscheint zweimal (Rangfolge + Mindestkriterien) mit korrekter Versionsnummer.
* **V6** ≥ 4 Deaktivierungs-Auslöser kuratiert und vollzählig gerendert.
* **V7** Wegweiser-Kette: Footer (jede Seite), `/transparenz/` und `/methodik/` → Raster; Raster → zurück. **Ausbaustufe 2 (03.10.2026):** Zusätzlich muss JEDE Seite mit Partnerlinks das Raster **in ihrem aufklappbaren Offenlegungs-Baustein** verlinken (`layouts/_partials/ff_offenlegung.html`) – der Footer-Link außerhalb des Bausteins zählt dabei bewusst nicht. Die Antworten stehen damit genau dort, wo monetarisiert wird.
* **V8** Kuratierungs-Hygiene: SemVer, ISO-Stand, Changelog, Ausschlüsse nur mit Begründung, ≥ 3 Lücken-Regeln.

Fail-closed wie die Offenlegungs-Wache: fehlendes `public/`, fehlende
Seite oder entfernte `data-ff-vg`-Fingerabdrücke im Live-Template sind
WERKZEUGFEHLER (Exit 2), niemals „grün".

## Befehle

```bash
npm run test:vergleiche        # Selbsttest (offline, 13 Sabotage-Proben)
npm run vergleiche:check       # Selbsttest + Quellen + Build + HTML-Beweis
python3 scripts/vergleichsgrundsaetze_gate.py --source-only   # ohne Build
python3 scripts/vergleichsgrundsaetze_gate.py --public public # gegen Build
```

## Pflege-Regeln

1. **Inhaltliche Änderung am Raster** → `meta.version` erhöhen (SemVer),
   `changelog`-Eintrag ergänzen; größere Umbauten zusätzlich in
   `data/beweise/korrekturen.yaml` (öffentliches Änderungsprotokoll).
2. **Neue Partnerroute** → nichts zu tun: Register rendert sie
   automatisch. Hat sie eine `abweichung`, erscheint der Warn-Chip von
   selbst; V3 prüft die Ehrlichkeit.
3. **Neuer Themenbereich in der Methodik** → nichts zu tun: Rangfolge-
   und K.-o.-Blöcke entstehen automatisch; Bereiche ohne
   Anbieter-Ranking (z. B. Frugalismus) bekommen die ehrliche
   „kein Ranking"-Zeile.
4. **Aussagen müssen Mechanik haben:** In `deaktivierung` und
   `provision.durchsetzung` steht nur, was eine reale Wache
   (`affiliate_health.py`, `affiliate_intent_guard.py`,
   `offenlegung_gate.py`) tatsächlich erzwingt. Kein Versprechen ohne
   ausführbares Gegenstück.
