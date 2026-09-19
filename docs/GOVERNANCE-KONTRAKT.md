# 🔒 Governance-Vertrag (automatisch geprüft)

**Stand:** 2026-09-19 · erzeugt von `scripts/governance_contract.py` · geprüft in `link-check.yml` (Qualitäts-Gate) und als Preflight in `premium-governance.yml`.

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
- **C10 Token-Broker** – Alle Pinterest-Skripte holen ihren Token über den Broker `scripts/pinterest_token.py` – eine Reihenfolge, ein Failover, und die Wache prüft denselben Token, mit dem der Bot arbeitet (#206).
- **C11 Token-Lebenszyklus** – Es gibt einen täglichen Erneuerungslauf (`pinterest-token.yml`), der den rotierten Refresh-Token sichert, sich selbst testet und sein Issue bei Heilung schließt – ein Handbetriebs-Secret stirbt sonst alle 30 Tage.
- **C12 Label-Garantie** – Jeder Workflow, der Issues mit Label erzeugt, legt das Label vorher an – sonst scheitert die Meldung mit HTTP 422 und der Melder wird selbst zum Zwischenfall (#209).
- **C13 Nachweis-Echtheit** – Ein Pinterest-Nachweis läuft immer mit Live-Probe (`--verify`), nur die Token-Wache rotiert den Refresh-Token proaktiv, und die Autorisierung fordert die echten v5-Scopes – sonst steht `unverified` im Cockpit, während niemand gemessen hat (#219).
- **C14 Alarm-Routing** – Jeder Alarm hat einen Besitzer (Maschine oder Mensch), einen Kanal und einen Schließpfad: menschliche Befunde öffnen kein Automations-Ticket und halten keins offen – sonst wird der Melder zum Dauerläufer (#272).
- **C15 Beweis-Trockenlauf** – Beweisen ist nicht Heilen: wer den Site-Bestand bei jedem Aufruf umschreibt, muss einen trockenen Beweispfad haben, und ein Kettenleiter darf `--fix` im eigenen Selbsttest nicht weitergeben – ein Prüflauf, der nebenbei heilt, verändert die Messgröße, die er prüfen will (15.09.2026).
- **C16 Wache-Herzschlag** – Ein Lebenszeichen ist kein Befund: die Affiliate-Integritäts-Wache erneuert ihren Zeitstempel bei jedem Lauf (Beweis im Gate-Selbsttest), ihre Frische wird per Herzschlag ODER fehlerfreiem Lauf belegt, und der Lebenszeichen-Pfad ist deploy-irrelevant – ein ruhiger Tag darf weder einen Fehlalarm noch eine Veröffentlichung auslösen (#281).
- **C17 Pinterest-Duplikate** – Pinterest-Duplikate (P4) sind Spam: pin_title und pin_description müssen über alle Artikel hinweg einzigartig sein – der Duplicate-Guard heilt deterministisch, läuft in Watchdog und Content-Engine und verhindert Repeat-Pin-Spam (#305).
- **C18 Pflicht-Check** – Der Pflicht-Check heißt, wie der Branch-Schutz ihn verlangt: Der Anzeigename des PR-Gates (`Integritäts-Siegel`) ist als Konstante eingefroren und muss Workflow und Ruleset gleichermaßen entsprechen; das Gate läuft bei jedem PR auf `main` ohne Pfadfilter, ohne `if:` am Job, ohne `continue-on-error` und nur mit Leserechten, und die Live-Wache `pflichtcheck_guard.py` prüft im Gate selbst, ob der Branch-Schutz den Check wirklich verlangt – ein umbenannter Job friert `main` ein, ein Ruleset ohne Ziel-Branch schützt nichts (19.09.2026).

## Befund

🟢 Alle Verträge erfüllt.
