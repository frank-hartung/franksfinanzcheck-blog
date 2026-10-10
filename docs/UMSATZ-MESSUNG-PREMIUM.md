# 💶 Umsatz-Messung Premium – Setup in zwei Minuten, Beweis für jeden Tag

**Warum dieses Dokument?** Seit je gilt: *Ohne sichtbaren Trichter optimiert man
nach Gefühl – keine Agentur bekommt Budget, bevor der Funnel messbar ist.*
Die Messkette (19.09.2026) liefert ihn: **Besuche je kaufnaher Seite →
Affiliate-Klicks → Outbound-CTR → Klick→Antrag → Antrag→Abschluss →
Stornoquote → Provision pro 100 Besuche → EPC.** Dieses Dokument ist die
einzige Stelle, an der du ANLEGEN musst; alles andere erledigen die Workflows.

Kurzform für die Eiligen: **zwei Secrets setzen → Testklick machen →
nichts mehr tun.** Der Rest ist Eskalation, die von allein kommt.

**Kein API-Zugang (Umami Cloud Free) und keine Awin-Teilnahme?** Dann ist
Abschnitt **5a** dein Weg: eine Datei aus dem Dashboard legen, ein Befehl,
und der Trichter rechnet mit echten Zahlen statt `unbekannt`. Das ist kein
Provisorium, sondern die von der Repo-Hausregel vorgesehene
„manueller Export zählt auch“-Regel in `revenue_funnel.py` (`main`:
„gemessen = Import sagt ok ODER Bestand mit Datum“) – nur mit
einem Befehl statt Handarbeit an den JSON-Dateien.

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
**„unbekannt“** – niemals eine 0. Echte Nullen erscheinen erst, wenn der
Import nachweislich gelaufen ist (`data/*.meta.json` ⇒ `status: ok`). Der
Governance-Gate unterscheidet genau deshalb zwischen Messlücke (Info/AMBER)
und Kaputt (ROT).

## 2) Secrets anlegen & Betriebsmodi

### Betriebsmodus: Umami Free (Kostenfreie Betriebsgrenze – Standard)

> Umami Cloud im Free-Plan hat keinen API-Zugang. Die Brücke dafür ist
> Abschnitt **5a (Weg 3)** – manuelle Messstände per Datei.

Umami Cloud im kostenfreien Plan bietet keinen API-Zugang. Umami bleibt dennoch **im Frontend und Browser vollständig aktiv**:
- Seitenaufrufe und `affiliate_click`-Events laufen live im **Umami-Dashboard** auf.
- In `data/monetization.yaml` ist `umami_api_import_enabled: false` gesetzt.
- Die Import-Skripte fragen keine Umami-API ab und erwarten kein `UMAMI_API_TOKEN`.
- Die Secrets-Wache meldet `UMAMI_API_TOKEN | BEWUSST DEAKTIVIERT (Umami Free)`.
- Der Revenue-Funnel bleibt grün (**GREEN**, 0 Messlücken), die Kennzahlen werden ehrlich als „unbekannt / im Dashboard einsehbar“ geführt und erzeugen keinen Alarm.

### Optional: API-Import aktivieren (Umami Pro oder Self-Hosted)

Falls du später auf einen kostenpflichtigen Umami Pro Plan wechselst oder Umami selbst hostest (z. B. auf Vercel oder einem eigenen VPS):

GitHub → Repo → **Settings → Secrets and variables → Actions → Repository secrets**:

#### a) `UMAMI_API_TOKEN` (liest Klicks UND Besuche)

1. https://cloud.umami.is → anmelden → **Avatar → User Settings → API →
   Generate API token** (Read reicht).
2. Secret `UMAMI_API_TOKEN` = dieser Token.
3. In `data/monetization.yaml` den Schalter aktivieren:
   ```yaml
   umami_api_import_enabled: true
   ```
4. Die Website-ID brauchst du hier nirgends – die Skripte lesen sie aus
   `hugo.toml` (`[params.umami] websiteId`). Selbst-gehostete Instanz?
   Dann zusätzlich Repository-**Variable** `UMAMI_API_BASE`
   (z. B. `https://umami.deinedomain.de/api`) setzen – kein Secret, keine
   Domain-Leckage im Repo.

Nach dem nächsten Importlauf (siehe 4) prüfst du mit:
`python3 scripts/umami_views.py --status` → muss `ok` melden.

#### b) `AWIN_API_TOKEN` + `AWIN_PUBLISHER_ID` (liest Transaktionen)

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
„Click References“ (CSV, enthält Click Reference + SubID) gegen
`data/umami_clicks.json` halten – mehr als ein Kreuzvergleich ist nicht nötig.

## 4) Der Regelbetrieb – was läuft wann, ohne dass du etwas tust

| Takt | Workflow | Aufgabe |
|---|---|---|
| zuletzt, 2×/Tag | `revenue-import.yml` → **Weg 3** | `scripts/offline_import.py`: manuelle Messstände (Dashboard-Export) + Abrechnungs-Monatssummen → Aggregate → Trichter neu (Abschnitt 5a) |
| 2×/Tag (06:10 + 18:10 MESZ; war ~alle 6 h, Audit 30.09.) | `revenue-import.yml` | Umami-Views + CTA-Klicks + Affiliate-Klicks + Awin-API → Daten committen; Funnel neu berechnet in die Lauf-Zusammenfassung |
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
  auf „unbekannt“ mit Benennung der Quelle; das ist eine Info, kein Alarm.

## 5) lokal prüfen (Werkbank, keine Secrets nötig)

```bash
python3 scripts/umami_views.py --status        # Stand des Views-Imports
python3 scripts/umami_views.py --days 7        # jetzt, live importieren (braucht den Token im Env)
python3 scripts/awin_fetch.py --status         # Stand des Awin-Imports
python3 scripts/revenue_funnel.py --print      # Trichter auf stdout (schreibt nichts)
npm run mess:import                            # Weg 3: Manuell-Messstände + Abrechnung importieren
npm run mess:status                            # Woher kommen die Zahlen gerade? (API/manuell/keine)
python3 scripts/click_chain_guard.py --public public/   # Kette am gebauten Stand (erst `hugo` bauen)
python3 scripts/revenue_funnel.py --selftest   # falls du an der Rechenlage änderst
```

Jeder dieser Schritte hat denselben Code-Pfad wie der Workflow – was lokal
grün ist, ist es auch in CI (und umgekehrt).

## 5a) Weg 3: Messstände ohne API (manuelle Brücke)

**Warum es das gibt:** Der Import-Code behandelt einen manuellen Export
seit je als volle Messung („Bestand mit Datum – manueller Export zählt
auch"). Bis 10.10.2026 hieß das: die JSON-Dateien von Hand schreiben. Das
hat nie jemand getan – also meldete `data/revenue_funnel.json` wochenlang
`null`, während die Zahlen im Umami-Dashboard längst da waren. Ein
ausgelassener manueller Schritt ist genau die stille Lücke, die Issue #514
dokumentiert hat. Also: ein Befehl.

### Was du brauchst

| Daten | Woher | Felder |
|---|---|---|
| Besuche je Seite | Umami → **Analytics → Pages** (Zeitraum = Fenster) → Export/CSV | `url` (oder `pfad`), `pageViews`/`aufrufe`, `visits`/`besuche` |
| Affiliate-Klicks | Umami → **Events → `affiliate_click`** | `event`, `slug`, `article`, `pillar`, `zahl`/`count` |
| CTA-Klicks (Start/Pillar) | Umami → **Events → `cta_click`** | wie oben, `event: cta_click` |
| Provision | Partner-Abrechnung (CHECK24/Tarifcheck) → Monatssummen | `data/provisionen/provisionen.csv` (Schema: `docs/ANLEITUNG-PROVISIONEN.md`) |

### Ein Befehl, drei Schritte

```bash
python3 scripts/offline_import.py --template   # 1) data/offline/messstand.json anlegen
# 2) ausfüllen (JSON) ODER Dashboard-CSV daneben legen: seiten.csv / events.csv
python3 scripts/offline_import.py --dry-run     # 3) ansehen, was ankommt
python3 scripts/offline_import.py               # schreiben + Trichter neu rechnen
npm run mess:status                             # Kontrolle: Quelle, Stand, Zähler
```

`scripts/offline_import.py` akzeptiert das eigene Gerüst, den rohen
API-Export (`{"pages": [{"url": …, "pageViews": …}]}`) und CSV – die
Pfad-Normalisierung ist **dieselbe** wie bei `umami_views.py`
(UTM-Splitting wird zusammengeführt, Zeilen mit Mail/IP fallen raus).

### Was die Brücke garantiert (und was nicht)

- **Kein Überschreiben fremder Quellen:** läuft die API wirklich (Meta sagt
  `ok`), bleiben ihre Zeilen stehen – der manuelle Import ergänzt nur.
  `--merge` summiert zusätzlich den eigenen Bestand (Teilimporte).
- **Eine Meta gehört immer dem, der sie schreibt:** die API-Meta
  (`data/umami_*.meta.json`) bleibt unangetastet, die manuelle Brücke bekommt
  `data/offline_import.meta.json` (Stand, Modus, Dateiname, Zähler).
- **Provision ohne API ist eine Monats sicht:** die Abrechnungstabelle füllt
  `Provision`/`Abschlüsse`, **nie** einer einzelnen Seite, und die Raten
  (`Klick → Antrag`, EPC) werden im Report mit `*` + Fußnote als Zeitbezug-
  Mischung gekennzeichnet. Werfen sie einen Wochen-Vergleich aus, ist das
  ein Interpretationsfehler, kein Messfehler.
- **Laut statt still (neue Eskalation):** sobald KEINE Brücke misst – also
  API-Import deaktiviert (Umami Free) UND nie ein Manuell-Import gelaufen –
  meldet der Funnel `funnel_gap` (AMBER → Governance-Issue mit Behebungs-
  zeile auf diesen Abschnitt). Vorher galt das als „Betriebsgrenze“ und
  blieb grün bei durchgehend `unbekannt`. Belegt:
  `python3 scripts/revenue_funnel.py --selftest` (Fall „Umami Free ohne
  Manuell-Import“).

- **Datenschutz:** Roheingang bleibt lokal (`data/offline/` ist
  per `.gitignore` ausgeschlossen), versioniert werden nur Aggregate.

### Im Regelbetrieb

`revenue-import.yml` (2×/Tag) führt den Import als **letzten** Schritt vor
dem Commit aus – die gitignored Datei existiert im Runner also nur, wenn du
sie committest (das solltest du nicht). Der Alltagsweg bleibt: lokal
ausführen, `data/offline_import.meta.json` + `data/provisionen_aggregat.json`
commiten (beide enthalten nur Aggregate), und der Wochen-Funnel rechnet damit.

## 6) Was dieses Setup NICHT tut (bewusste Grenzen)

- **Keine Konversionen automatisieren:** der Testklick ist Verifikation,
  fertig. Eigenabschlüsse sind tabu.
- **Kein Personenbezug:** gespeichert werden nur Aggregate (Pfad, Zähler,
  SubID-Slug). Keine IPs, keine Nutzendenprofile – die Reports sind damit
  auch als Nachweis gegenüber Sponsoring-Partnern vorlegbar.
- **Kein Fake-Grün:** ohne Messung steht „unbekannt" da. Die Pipeline ist
  so gebaut, dass sie lieber laut eine Lücke meldet als still eine Null
  erfindet – ein offenes Issue ist billiger als eine falsche Entscheidung.

*Erste Installation: 19.09.2026 im Zuge der Forderung „vollständige
Umsatzmessung innerhalb einer Stunde" – Skripte `umami_views.py`,
`umami_clicks.py`, `awin_fetch.py`, `awin_provisions.py`,
`revenue_funnel.py`, `click_chain_guard.py`; verdrahtet in
`premium-governance.yml`, `revenue-import.yml`, Governance-Gate
(`funnel_gap`/`chain_gap`), Scorecard-Datenlage und e2e-CTA-Vertrag.*
