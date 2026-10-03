# Vergleichsgrundsätze auf Highend-Level – Rollout 03.10.2026

**Auftrag (Audit-Befund 8):** „Monetarisierung und Vertrauen müssen noch
sauberer austariert werden. […] Eine öffentliche Seite ‚So entstehen
unsere Vergleiche‘ mit einem konkreten Bewertungsraster wäre deutlich
stärker als ein allgemeiner Unabhängigkeitshinweis. Bitte dauerhaft auf
Highend-Level einer Profi-Agentur beheben."

## Befund vor dem Umbau

Die sieben Audit-Fragen waren nur teilweise und verstreut beantwortet:

| Audit-Frage | Zustand vorher |
|---|---|
| Welche Anbieter werden berücksichtigt? | Partnerliste auf /transparenz/ nannte Partner und Bereiche, aber keine Aufnahmekriterien – und nicht, welche Route ein echter Marktvergleich ist und welche ein Einzelangebot (C24 Bank) oder eine Portalstartseite |
| Welche werden ausgeschlossen und warum? | **Nirgends beantwortet** – die unsichtbare Hälfte jeder Auswahl fehlte komplett |
| Wie wird die Reihenfolge bestimmt? | Ein Satz auf /transparenz/ („nach Sachkriterien, nie nach Provision") ohne das konkrete Raster; die Rangfolgen existierten in der Methodik, waren aber nicht als Antwort auf die Monetarisierungs-Frage auffindbar |
| Wird Provision bei der Bewertung berücksichtigt? | Verbal verneint, aber nirgends als harter, maschinell bewachter Vertrag |
| Gibt es Mindestkriterien? | K.-o.-Kriterien je Bereich in der Methodik vorhanden, aber nicht als Mindestkriterien-Antwort gebündelt |
| Wann wird ein Link deaktiviert? | **Nirgends öffentlich** – obwohl die Mechanik (wöchentliche E2E-Prüfung, Selbstheilung, Intent-Wache) längst läuft |
| Umgang mit fehlenden/nicht vergleichbaren Tarifen? | Verstreute „Grenzen"-Hinweise, keine Regelsammlung |

## Umsetzung: Raster + SSOT + Wache (das „dauerhaft" ernst genommen)

Gleiches Muster wie bei der Offenlegungs-Wache vom 28.09.2026: Eine
Seite, die niemand gegen die Realität prüft, veraltet in die Unwahrheit.
Deshalb besteht die Lösung aus drei Schichten:

1. **Öffentliche Seite** `/so-entstehen-unsere-vergleiche/` – sieben
   Fragen, sieben Antworten, siteweit im Footer verlinkt, mit Hin- und
   Rückwegen zu /transparenz/ und /methodik/.
2. **Drei Quellen, keine Kopie:**
   * `data/vergleichsgrundsaetze.yaml` (neu, kuratiert, SemVer +
     Changelog-Pflicht): Aufnahmekriterien, Ausschlüsse mit
     Pflicht-Begründung, Reihenfolge-Grundsatz inkl. des ehrlichen
     Portal-Hinweises, Provisions-Antwort, Deaktivierungs-Auslöser,
     Lücken-Regeln.
   * `data/affiliate_ziele.yaml` (bestehend, gebacken): Das Raster
     rendert alle 20 Routen mit ehrlichem **Zieltyp** – Marktvergleich,
     Einzelangebot (C24 Girokonto/Tagesgeld), Portalstartseite,
     Bündelprodukt (Flüge) – samt Erklärtext der Abweichung.
   * `data/beweise/vergleichsmethodik.yaml` (bestehend, versioniert):
     Rangfolgen (V3) und K.-o.-Kriterien (V5) je Themenbereich werden
     gespiegelt, nie abgetippt; Versionsnummern sichtbar.
3. **Wache** `scripts/vergleichsgrundsaetze_gate.py` (V1–V8,
   fail-closed, attribut-tolerant via html.parser, Detektor-Frische-
   Prüfung nach der AI4-Lektion, 13 Sabotage-Proben im `--selftest`):
   * V2 Register-Sync in beide Richtungen – eine neue `/go/`-Route ohne
     öffentliche Nennung bricht den Deploy.
   * V3 Zieltyp-Ehrlichkeit – ein Einzelangebot, das als
     „Marktvergleich" gerendert wird, bricht den Deploy.
   * V4 Provisions-Vertrag – `provision.antwort` muss wörtlich „nein"
     sein; jede „Präzisierung" ist ein roter Lauf.
   * V7 Wegweiser-Kette – Footer, /transparenz/ und /methodik/ müssen
     das Raster verlinken, das Raster zurück.

## Verankerung

* **CI:** `.github/workflows/vergleichsgrundsaetze-gate.yml` (Selbsttest
  → Quellen → minifizierter Build → HTML-Beweis) bei jedem Push/PR, der
  Raster-Quellen, Seite, Shortcode, Footer oder Wache berührt.
* **Deploy:** Finales Transparenz-Gate in `deploy.yml` direkt neben den
  Produkt-Gates (Themenwelten, Cockpit, Werkzeuge) – kein `|| true`.
* **Governance:** `vergleichsgrundsaetze_gate.py` steht im
  GUARDS-Minimum von `scripts/governance_contract.py` (C6 erzwingt den
  Selbsttest dauerhaft).
* **npm:** `npm run vergleiche:check` / `npm run test:vergleiche`.
* **Öffentlich:** Eintrag im Änderungsprotokoll
  (`data/beweise/korrekturen.yaml`), Querverweise auf /transparenz/
  (Abschnitt 4.3 + Schluss) und /methodik/ (Finanzierungs-Abschnitt).
* **Runbook:** `docs/ANLEITUNG-VERGLEICHSGRUNDSAETZE.md`.

## Messung nach dem Umbau

* `vergleichsgrundsaetze_gate.py --selftest`: 13/13 Sabotage-Proben OK.
* Gate gegen unminifizierten UND minifizierten Build: 0 Fehler
  (20 Routen, 6 Methodik-Bereiche, 5 Ausschlüsse, 5 Auslöser).
* `beweis_gate.py`: 0 Fehler (Änderungsprotokoll-Eintrag valide).
* Bestehende Wachen (Offenlegung O1–O7, Index-Hygiene, Playwright-Suite)
  nach dem Umbau grün – Nachweis im PR-Lauf.

## Ausbaustufe 2 (03.10.2026, Nachschärfung desselben Befunds)

**Lücke:** Das Raster war im Footer, auf /transparenz/ und /methodik/
verlinkt – aber nicht an der Stelle, an der Leser der Monetarisierung
tatsächlich begegnen: im aufklappbaren Werbe-Offenlegungs-Baustein über
jedem Artikel.

**Umsetzung:**

* `layouts/_partials/ff_offenlegung.html`: Der „Was die Provision nicht
  beeinflusst"-Absatz verweist jetzt inhaltlich auf das Bewertungsraster
  (Aufnahme/Ausschluss, Sortierung, Link-Deaktivierung), und die
  Wege-Zeile führt „So entstehen unsere Vergleiche" als eigenen Link
  zwischen Finanzierung und Methodik.
* Wache V7, Ausbaustufe 2: JEDE gebaute Seite mit Partnerlinks
  (posts/, pillar/, Pillar-Zentrale) muss das Raster IM
  Offenlegungs-Baustein verlinken – der Footer-Link außerhalb zählt
  bewusst nicht (eigener Parser mit Baustein-Containment). Findet der
  Scan 0 Bausteine, ist das ein Werkzeugfehler (Exit 2), kein grüner
  Lauf; der `data-ff-offenlegung`-Fingerabdruck im Live-Partial gehört
  jetzt zur Detektor-Frische-Prüfung.
* Drei neue Sabotage-Proben (13 gesamt): Baustein mit Link sauber,
  Baustein ohne Link fällt durch (Footer zählt nicht), werbefreie
  Seiten bleiben außen vor.

**Messung:** Selbsttest 13/13 · Gate 0 Fehler, Artikel-Brücke auf allen
45 Offenlegungs-Bausteinen nachgewiesen · Offenlegungs-Wache O1–O7,
Layout- und Index-Hygiene-Gates grün · Playwright-Suite grün (Nachweis
im PR-Lauf).
