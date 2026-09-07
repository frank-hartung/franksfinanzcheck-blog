# 🔒 Governance-Vertrag (automatisch geprüft)

**Stand:** 2026-09-07 · erzeugt von `scripts/governance_contract.py` · geprüft in `link-check.yml` (Qualitäts-Gate) und als Preflight in `premium-governance.yml`.

Dieser Vertrag hält die Regeln fest, die den Dauer-Alarm aus Governance-Report #206 ermöglicht haben. Jede Verletzung ist ein Build-Fehler.

## Regeln

- **C1 Reihenfolge** – Die Sicht (Chefredakteur-Scorecard) läuft nach allen Messungen – sonst zeigt sie Werte des Vorlaufs als aktuellen Befund (#206).
- **C2 Bau-Grundlage** – Der Hugo-Build darf keinen Fehler mit `|| true` verschlucken und meldet sein Ergebnis an das Gate – eine nicht ausgeführte Messung ist kein Grün.
- **C3 Messkette** – Jede Gate-Kennung wird aus einem Workflow befüllt – ein Schritt, den niemals jemand meldet, kann auch niemand reparieren.
- **C4 Issue-Policy** – Issues entstehen aus der Gate-Entscheidung (`--decide`), Duplikate sind verboten (aktualisieren statt neu öffnen), und eine meldungsfreie Lage schließt das Issue.
- **C5 Nachweis-Provenienz** – Secret-Nachweise tragen ihre Herkunft (`--proof-by`) und kommen aus dem Workflow, der das Secret benutzt; die Governance prüft live (`--verify`) statt sich selbst zu beglaubigen.
- **C6 Selbsttests** – Jede Wache hat einen `--selftest`, und alle bestehen – eine kaputte Wache liefert falsche Sicherheit.
- **C7 Datenkonsistenz** – Manifest, Report und Scorecard zeigen dieselbe Ampel (oder die Scorecard kennzeichnet STALE/nicht gemessen ausdrücklich).
- **C8 Commit-Hygiene** – `git add` im Workflow nennt nur versionierbare Pfade – ignorierte, unversionierte Dateien brechen den Lauf hart ab (#205).
- **C9 Secret-Leak-Schutz** – Reports und `data/*.json` enthalten kein Secret-Material (Pinterest/Groq/Gemini/GitHub/JWT-Muster).

## Befund

🟢 Alle Verträge erfüllt.
