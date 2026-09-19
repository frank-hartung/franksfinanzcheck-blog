# 💶 Umsatz-Messung Premium – Setup in zwei Minuten, Beweis für jeden Tag

**Warum dieses Dokument?** Seit je gilt: *Ohne sichtbaren Trichter optimiert man
nach Gefühl – keine Agentur bekommt Budget, bevor der Funnel messbar ist.*
Die Messkette (19.09.2026) liefert ihn: **Besuche je kaufnaher Seite →
Affiliate-Klicks → Outbound-CTR → Klick→Antrag → Antrag→Abschluss →
Stornoquote → Provision pro 100 Besuche → EPC.** Dieses Dokument ist die
einzige Stelle, an der du ANLEGEN musst; alles andere erledigen die Workflows.

Kurzform für die Eiligen: **zwei Secrets setzen → Testklick machen →
nichts mehr tun.** Der Rest ist Eskalation, die von allein kommt.

---

## 1) Was gemessen wird und wo es liegt

| Kennzahl | Quelle | Datei/Report |
|---|---|---|
| Besuche je Seite (kaufnah + gesamt) | Umami `/pages`, `/total` | `data/umami_views.json` |
| Affiliate-Klicks (`affiliate_click`) | Umami Event-API | `data/umami_clicks.json` |
| Start-/Pillar-CTA-Klicks (`cta_click`) | Umami Event-API | `data/umami_ctas.json` |
| Anträge/Abschlüsse/Stornos + Provision | Awin Publisher API | `data/awin_transactions.csv` (laufzeitlich, gitignored) → `data/awin_provisions.json` |
| Alles zusammen: Trichter + Ampel + Empfehlungen | Rechenlage | `REVENUE-FUNNEL-REPORT.md` (Lauf-Artefakt) + `data/revenue_funnel.json` + `data/revenue_funnel_history.jsonl` |
| Integrität der Kette (Template→Build→Umami→Gateway→Awin) | `scripts/click_chain_guard.py` | `CLICK-CHAIN-REPORT.md` |

**Hausregel der ganzen Pipeline:** eine Quelle, die nicht gemessen wurde, ist
**„unbekannt"** – niemals eine 0. Echte Nullen erscheinen erst, wenn der
Import nachweislich gelaufen ist (`data/*.meta.json` ⇒ `status: ok`). Der
Governance-Gate unterscheidet genau deshalb zwischen Messlücke (Info/AMBER)
und Kaputt (ROT).

## 2) Secrets anlegen (einmalig, ~2 Minuten)

GitHub → Repo → **Settings → Secrets and variables → Actions → Repository secrets**:

### a) `UMAMI_API_TOKEN` (liest Klicks UND Besuche)

1. https://cloud.umami.is → anmelden → **Avatar → User Settings → API →
   Generate API token** (Read reicht).
2. Secret `UMAMI_API_TOKEN` = dieser Token. **Fertig.**
3. Die Website-ID brauchst du hier nirgends – die Skripte lesen sie aus
   `hugo.toml` (`[params.umami] websiteId`). Selbst-gehostete Instanz?
   Dann zusätzlich Repository-**Variable** `UMAMI_API_BASE`
   (z. B. `https://umami.deinedomain.de/api`) setzen – kein Secret, keine
   Domain-Leckage im Repo.

Nach dem nächsten Importlauf (siehe 4) prüfst du mit:
`python3 scripts/umami_views.py --status` → muss `ok` melden.

### b) `AWIN_API_TOKEN` + `AWIN_PUBLISHER_ID` (liest Transaktionen)

1. Awin-Dashboard (app.awin.com) → **Settings → Users → „Manage your web
   services" (API credentials)** → API-Dienst anlegen/scopes auf *Lesen*
   (Transactions) → Token anzeigen lassen **und sofort kopieren**.
2. **Publisher-ID:** dein Account-Number aus dem Awin-Backend (steht in der
   URL bzw. unter Account-Details; reine Ziffernfolge).
3. Secrets anlegen: `AWIN_API_TOKEN` = Token, `AWIN_PUBLISHER_ID` = ID
   (die ID darf alternativ als Repository-**Variable** stehen – sie ist kein
   Geheimnis, macht aber 404-Fehler aussagekräftiger).
4. Token wird **nie** geloggt oder in Dateien geschrieben – die Skripte
   lesen ihn nur aus der Umgebung (und die Secrets-Wache prüft per
   Live-Probe `GET /publishers/{id}`, ob er noch lebt).

Hinweis aus der API-Doku: Abrufe max. 31 Tage pro Fenster (der Import
nutzt 62-Tage-Fenster über mehrere Slices), Zeitzonen-Referenz
`Europe/Berlin`, Beträge in Cent (automatisch umgerechnet).

## 3) Der Eigen-Testklick (Pflicht, exakt EIN Klick)

Damit die Kette **bewiesen** ist, nicht nur „konfiguriert":

1. Irgendeinen Live-Artikel mit `/go/`-Button öffnen (z. B. der letzte
   Gastbeitrag) → **genau einen** Affiliate-CTA klicken.
2. Beim Partner (Check24/Awin-Ziel) darf **nichts abgeschlossen** werden –
   keine Anmeldung, kein Antrag, kein Kauf. **Kein Eigenabschluss – der
   wird storniert und kann den Programm-Status kosten.**
3. Innerhalb von ~24 h muss der Klick im Awin-Dashboard sichtbar sein:
   **Reports → Click References** (dort steht deine Click-Reference mit dem
   SubID-Wert = Artikel-Slug ⇒ Attribution funktioniert).
4. Beim nächsten Importlauf muss derselbe Klick als `affiliate_click` in
   `data/umami_clicks.json` auftauchen ⇒ **beide Systeme sehen dasselbe**.

Komfort: `python3 scripts/click_chain_guard.py --test-page` zeigt die SOP
mit den konkreten Prüfkommandos. Wer es genau wissen will: Awinexport
„Click References" (CSV, enthält Click Reference + SubID) gegen
`data/umami_clicks.json` halten – mehr als ein Kreuzvergleich ist nicht nötig.

## 4) Der Regelbetrieb – was läuft wann, ohne dass du etwas tust

| Takt | Workflow | Aufgabe |
|---|---|---|
| ~alle 6 h | `revenue-import.yml` | Umami-Views + CTA-Klicks + Affiliate-Klicks + Awin-API → Daten committen; Funnel neu berechnet in die Lauf-Zusammenfassung |
| Montag 07:15 | `premium-governance.yml` | Alles messen → GATE bewertet → Scorecard (zeigt Datenalter + Messlücken des Funnels) → bei Befund: EIN Issue mit Label `governance` |
| PR/push auf layouts/e2e | `e2e.yml` | Playwright `affiliate-guard`: jeder gebaute CTA trägt Event+Slug+SubID+Placement (der Layout-Vertrag) |

**Escalation – was dich wann packt:**
- Secrets fehlen → der Funnel meldet `funnel_gap` (AMBER) → das Wochen-Gate
  eröffnet/aktualisiert ein Governance-Issue mit der konkreten
  Behebungszeile („UMAMI_API_TOKEN anlegen – Anleitung
  docs/UMSATZ-MESSUNG-PREMIUM.md"). Es bleibt offen, bis es weg ist; bei
  GREEN schließt der Lauf es automatisch.
- Token gesetzt, API aber kaputt → Import-Schritt wird **rot** (sichtbarer
  Run-Fehler + Mail) und die Secrets-Wache meldt toten Token beim
  Live-Probe-Namen.
- Template baut CTA ohne Messattribute → `click_chain_guard` meldet
  `chain_gap` → wieder AMBER-Issue, plus e2e-Test rot auf dem PR, der es
  einführen wollte (Fehler sterben vor der Merge, nicht danach).
- Awin-Zahlen bleiben aus (Partner liefert nicht) → Stornoquote/EPC stehen
  auf „unbekannt" mit Benennung der Quelle; das ist eine Info, kein Alarm.

## 5) lokal prüfen (Werkbank, keine Secrets nötig)

```bash
python3 scripts/umami_views.py --status        # Stand des Views-Imports
python3 scripts/umami_views.py --days 7        # jetzt, live importieren (braucht den Token im Env)
python3 scripts/awin_fetch.py --status         # Stand des Awin-Imports
python3 scripts/revenue_funnel.py --print      # Trichter auf stdout (schreibt nichts)
python3 scripts/click_chain_guard.py --public public/   # Kette am gebauten Stand (erst `hugo` bauen)
python3 scripts/revenue_funnel.py --selftest   # falls du an der Rechenlage änderst
```

Jeder dieser Schritte hat denselben Code-Pfad wie der Workflow – was lokal
grün ist, ist es auch in CI (und umgekehrt).

## 6) Was dieses Setup NICHT tut (bewusste Grenzen)

- **Keine Konversionen automatisieren:** der Testklick ist Verifikation,
  fertig. Eigenabschlüsse sind tabu.
- **Kein Personenbezug:** gespeichert werden nur Aggregate (Pfad, Zähler,
  SubID-Slug). Keine IPs, keine Nutzendenprofile – die Reports sind damit
  auch als Nachweis gegenüber Sponsoring-Partnern vorlegbar.
- **Kein Fake-Grün:** ohne Messung steht „unbekannt" da. Die Pipeline ist
  so gebaut, dass sie lieber laut lügt-los als still lügt – jede Lüge wäre
  teurer als ein offenes Issue.

*Erste Installation: 19.09.2026 im Zuge der Forderung „vollständige
Umsatzmessung innerhalb einer Stunde" – Skripte `umami_views.py`,
`umami_clicks.py`, `awin_fetch.py`, `awin_provisions.py`,
`revenue_funnel.py`, `click_chain_guard.py`; verdrahtet in
`premium-governance.yml`, `revenue-import.yml`, Governance-Gate
(`funnel_gap`/`chain_gap`), Scorecard-Datenlage und e2e-CTA-Vertrag.*
