# 💶 Umsatz-Messung Premium – Quellen, Betriebsgrenzen, Beweis für jeden Tag

**Warum dieses Dokument?** Seit je gilt: *Ohne sichtbaren Trichter optimiert man
nach Gefühl – keine Agentur bekommt Budget, bevor der Funnel messbar ist.*
Die Messkette (19.09.2026) liefert ihn: **Affiliate-Klicks → Klick→Antrag →
Antrag→Abschluss → Stornoquote → Provision → EPC.** Dieses Dokument ist die
einzige Stelle, an der du ANLEGEN musst; alles andere erledigen die Workflows.

**Keine Besucherzahlen – mit Absicht.** Seit 11.10.2026 läuft auf dem Blog kein
Reichweiten-Tracking und kein Besucherzähler (Datenschutzentscheidung). Eine
Kennzahl ohne Quelle wäre für immer „unbekannt“, also Dekoration – darum gibt
es weder Besuche noch Outbound-CTR noch „Provision pro 100 Besuche“. Der
Trichter beginnt beim Klick. Eine Rückkehr der Fremdmessung verhindert
`scripts/fremdmessung_sperre.py` (Vertrag C40, Runbook:
`docs/ANLEITUNG-FREMDMESSUNG-SPERRE.md`).

Kurzform für die Eiligen: **Provisions-Tabelle pflegen (Abschnitt 5a) →
optional den eigenen Klickzähler einschalten (Abschnitt 2) → nichts mehr
tun.** Der Rest ist Eskalation, die von allein kommt.

---

## 1) Was gemessen wird und wo es liegt

| Kennzahl | Quelle | Datei/Report |
|---|---|---|
| Affiliate-Klicks (`affiliate_click`) | eigener, cookieloser Zähler am `/go/`-Beacon (Cloudflare D1) → `scripts/klick_import.py` | `data/klicks_eigen.json` + `data/klicks_eigen.meta.json` (leer, solange `aktiv: false`) |
| Abschlüsse/Stornos + Provision (Monatssummen) | Manuelle Provisions-Tabelle aus den Partnerabrechnungen | `data/provisionen/provisionen.csv` (gitignored) → `data/provisionen_aggregat.json` |
| Alles zusammen: Trichter + Ampel + Empfehlungen | Rechenlage | `REVENUE-FUNNEL-REPORT.md` (Lauf-Artefakt) + `data/revenue_funnel.json` + `data/revenue_funnel_history.jsonl` |
| Integrität der Kette (Template→Build→Gateway) | `scripts/click_chain_guard.py` | `CLICK-CHAIN-REPORT.md` |

**Hausregel der ganzen Pipeline:** eine Quelle, die nicht gemessen wurde, ist
**„unbekannt“** – niemals eine 0. Echte Nullen erscheinen erst, wenn der
Import nachweislich gelaufen ist (`data/klicks_eigen.meta.json` ⇒
`status: ok`). Der Governance-Gate unterscheidet genau deshalb zwischen
Betriebsgrenze (Info), Messlücke (AMBER) und Kaputt (ROT).

## 2) Betriebsmodi – was der Funnel in welchem Zustand sagt

Der Funnel (`scripts/revenue_funnel.py`, Funktion `lage()`) unterscheidet, ob
ein Weg **bewusst aus** ist oder **laufen soll und nicht liefert**:

| Zustand | Funnel zeigt | Ampel |
|---|---|---|
| Klickzähler aus (`aktiv: false` in `data/klickmessung.yaml`) | Klicks, Klick→Antrag, EPC „unbekannt“ + INFO `operating_boundary` | 🟢 GREEN |
| Provisions-Tabelle noch nie befüllt | Anträge, Abschlüsse, Provision … „unbekannt“ + INFO `operating_boundary` | 🟢 GREEN |
| Klickzähler an, Import frisch (auch mit 0 Klicks) | echte Zahlen, echte Null | 🟢 GREEN |
| Klickzähler an, Import fehlt / nicht konfiguriert / fehlgeschlagen / älter als 14 Tage | `funnel_gap` mit Behebungszeile | 🟠 AMBER → Governance-Issue |
| Provisions-Tabelle befüllt, aber der Import ist älter als 14 Tage | `funnel_gap` | 🟠 AMBER → Governance-Issue |

Ein **ausgeschalteter** Zähler zählt auch alte Zeilen nicht: ausgeschaltet heißt
nicht gemessen. Der Schalter ist derselbe wie für `click_chain_guard.py` und
den `/go/`-Generator – eine Wahrheit (Test:
`test_schalter_im_repo_deckt_sich_mit_den_beiden_anderen_lesern`).

### Klickzähler einschalten (optional, Einmal-Aufgabe von dir)

Einrichtung, Worker, Domain und die Datenschutz-Prüfung vor dem Einschalten
stehen in **`docs/ANLEITUNG-KLICKMESSUNG-OHNE-COOKIES.md`**. Erst danach
`aktiv: true` in `data/klickmessung.yaml` setzen. Ab dann erwartet der Funnel
tägliche Lieferung und meldet jede Lücke.

## 3) Der Eigen-Testklick (Pflicht, sobald der Klickzähler an ist)

Damit die Kette **bewiesen** ist, nicht nur „konfiguriert\":

1. Irgendeinen Live-Artikel mit `/go/`-Button öffnen (z. B. der letzte
   Gastbeitrag) → **genau einen** Affiliate-CTA klicken.
2. Beim Partner (CHECK24 bzw. Tarifcheck) darf **nichts abgeschlossen** werden –
   keine Anmeldung, kein Antrag, kein Kauf. **Kein Eigenabschluss – der
   wird storniert und kann den Programm-Status kosten.**
3. Nach dem nächsten Import (`python3 scripts/klick_import.py`) muss
   `data/klicks_eigen.json` eine Zeile mit dem Artikel-Slug und `count ≥ 1`
   tragen (SubID = Artikel-Slug ⇒ die Zuordnung zum Artikel funktioniert).

Komfort: `python3 scripts/click_chain_guard.py --test-page` zeigt die SOP
mit den konkreten Prüfkommandos.

## 4) Der Regelbetrieb – was läuft wann, ohne dass du etwas tust

| Takt | Workflow | Aufgabe |
|---|---|---|
| 2×/Tag (06:10 + 18:10 MESZ; war ~alle 6 h, Audit 30.09.) | `revenue-import.yml` | `scripts/offline_import.py` (Abrechnungs-Monatssummen → Aggregat, nur wenn eine Tabelle vorliegt) → Funnel neu berechnet in die Lauf-Zusammenfassung → Aggregate committen |
| Montag 07:15 | `premium-governance.yml` | Alles messen → GATE bewertet → Scorecard (zeigt Datenalter + Messlücken des Funnels) → bei Befund: EIN Issue mit Label `governance` |
| PR/push auf layouts/e2e | `e2e.yml` | Playwright `affiliate-guard`: jeder gebaute CTA trägt Event+Slug+SubID+Placement (der Layout-Vertrag) |

**Escalation – was dich wann packt:**
- Klickzähler an, aber kein Import → der Funnel meldet `funnel_gap` (AMBER) →
  das Wochen-Gate eröffnet/aktualisiert ein Governance-Issue mit der konkreten
  Behebungszeile. Es bleibt offen, bis es weg ist; bei GREEN schließt der Lauf
  es automatisch.
- Template baut CTA ohne Messattribute → `click_chain_guard` meldet
  `chain_gap` → wieder AMBER-Issue, plus e2e-Test rot auf dem PR, der es
  einführen wollte (Fehler sterben vor der Merge, nicht danach).
- Keine Abrechnungstabelle (noch nichts eingetragen) → Anträge, Provision und
  EPC stehen auf „unbekannt“ mit Benennung der Quelle; das ist eine Info,
  kein Alarm.

## 5) lokal prüfen (Werkbank, keine Secrets nötig)

```bash
python3 scripts/revenue_funnel.py --print      # Trichter auf stdout (schreibt keine Dateien)
npm run mess:status                            # Woher kommen die Zahlen gerade? (Tabelle, Zähler)
npm run mess:import                            # Provisions-Tabelle importieren + Trichter neu rechnen
python3 scripts/klick_import.py                # Klickzähler abrufen (ohne Zugang: „nicht konfiguriert“, Exit 0)
python3 scripts/click_chain_guard.py --public public/   # Kette am gebauten Stand (erst `hugo` bauen)
python3 scripts/revenue_funnel.py --selftest   # falls du an der Rechenlage änderst
npm run test:mess                              # Selbsttests + Regressionstests der Messkette
```

Jeder dieser Schritte hat denselben Code-Pfad wie der Workflow – was lokal
grün ist, ist es auch in CI (und umgekehrt).

## 5a) Die Provisions-Tabelle (manuelle Brücke)

**Warum es das gibt:** Die Provision steht nur in den Abrechnungen der Partner
– kein Automat holt sie. Ohne diesen Schritt meldet `data/revenue_funnel.json`
für Anträge, Abschlüsse, Provision und EPC `null`. Ein ausgelassener manueller
Schritt ist genau die stille Lücke, die Issue #514 dokumentiert hat. Also: ein
Befehl.

### Was du brauchst

| Daten | Woher | Felder |
|---|---|---|
| Provision, Abschlüsse, Stornos | Partner-Abrechnung (CHECK24/Tarifcheck/C24 Bank) → Monatssummen | `data/provisionen/provisionen.csv` (Schema: `docs/ANLEITUNG-PROVISIONEN.md`) |

### Ein Befehl, drei Schritte

```bash
npm run mess:vorlage     # 1) legt data/provisionen/provisionen.csv aus der Vorlage an (nur Kopfzeile)
# 2) Monatssummen eintragen (Schema und Prüfung: python3 scripts/provisionen_check.py)
python3 scripts/offline_import.py --dry-run   # 3) ansehen, was ankommt
npm run mess:import      # schreiben + Trichter neu rechnen
npm run mess:status      # Kontrolle: Stand, Monate, Summe, Zustand des Klickzählers
```

### Was die Brücke garantiert (und was nicht)

- **Eine Meta gehört dem, der sie schreibt:** der Import schreibt
  `data/offline_import.meta.json` (Stand, Zahl der Monate, letzter Monat); der
  Klickzähler hat seine eigene `data/klicks_eigen.meta.json`.
- **Provision ist eine Monatssicht:** die Abrechnungstabelle füllt
  `Provision`/`Abschlüsse`, **nie** einer einzelnen Seite, und die Raten
  (`Klick → Antrag`, EPC) werden im Report mit `*` + Fußnote als Zeitbezug-
  Mischung gekennzeichnet. Werfen sie einen Wochen-Vergleich aus, ist das
  ein Interpretationsfehler, kein Messfehler.
- **Bewusst offen ist kein Alarm:** eine noch nie befüllte Tabelle ist eine
  Betriebsgrenze (INFO, grün). Ist sie befüllt und der Import wird älter als
  14 Tage, ist es eine Messlücke (AMBER).
- **Datenschutz:** Die Roh-Tabelle bleibt lokal
  (`data/provisionen/provisionen.csv` ist per `.gitignore` ausgeschlossen),
  versioniert wird nur das Aggregat – ohne Abrechnungsnummern und Notizen.

### Im Regelbetrieb

`revenue-import.yml` (2×/Tag) führt den Import vor dem Funnel aus. Die
gitignored Tabelle existiert im Runner nur, wenn du sie committest (das
solltest du nicht) – der Schritt meldet dann „übersprungen“. Der Alltagsweg
bleibt: lokal ausführen, `data/offline_import.meta.json` +
`data/provisionen_aggregat.json` committen (beide enthalten nur Aggregate),
und der Funnel rechnet damit.

## 6) Was dieses Setup NICHT tut (bewusste Grenzen)

- **Keine Konversionen automatisieren:** der Testklick ist Verifikation,
  fertig. Eigenabschlüsse sind tabu.
- **Keine Besucher messen:** es gibt keinen Besucherzähler und keinen
  Reichweiten-Dienst. Wer einen einführen will, braucht eine eigene
  Entscheidung samt Datenschutz-Prüfung, Quelle, Meta-Datei und Test – und
  muss die Sperre (`docs/ANLEITUNG-FREMDMESSUNG-SPERRE.md`) bewusst ändern.
- **Kein Personenbezug:** gespeichert werden nur Aggregate (Pfad, Zähler,
  SubID-Slug). Keine IPs, keine Nutzendenprofile – die Reports sind damit
  auch als Nachweis gegenüber Sponsoring-Partnern vorlegbar.
- **Kein Fake-Grün:** ohne Messung steht „unbekannt\" da. Die Pipeline ist
  so gebaut, dass sie lieber laut eine Lücke meldet als still eine Null
  erfindet – ein offenes Issue ist billiger als eine falsche Entscheidung.

*Erste Installation: 19.09.2026 im Zuge der Forderung „vollständige
Umsatzmessung innerhalb einer Stunde\" – Skripte `revenue_funnel.py`,
`click_chain_guard.py`; verdrahtet in `premium-governance.yml`,
`revenue-import.yml`, Governance-Gate (`funnel_gap`/`chain_gap`),
Scorecard-Datenlage und e2e-CTA-Vertrag.*

*Stand 11.10.2026: Awin ist aus dem Blog entfernt (Abruf, Import und
Gate-Schritte). Provisionen laufen über die Abrechnungstabelle (Abschnitt 5a).*

*Stand 19.10.2026 (Governance-Report #806): Die Anbindung des früheren
Reichweiten-Dienstes ist restlos entfernt – Import-Skripte, Workflow-Schritte,
Zugangsdaten-Prüfung, Datenbestände, Dashboard-Export-Brücke. Mangels Quelle
entfallen die Besuchs-Kennzahlen; Klicks kommen aus dem eigenen Zähler.*
