# ANLEITUNG – Kennzahlen-Radar (Frühwarnsystem)

> **Seit:** 28.09.2026 · **Ursprung:** Quick Win H5 aus der
> Konkurrenz-Analyse Finanztip (`KONKURRENZ-ANALYSE-FINANZTIP-KI-TOOLS-2026-09-28.md`)
> **Teile:** `data/kennzahlen_register.yaml` (kuratiert) ·
> `scripts/kennzahlen_radar.py` (Maschine) ·
> `.github/workflows/kennzahlen-radar.yml` (Dienstag 06:20 MESZ)

---

## Warum gibt es das?

Finanztip baut laut Stellenanzeige („(Senior) Product Data & AI Automation
Manager“) eine **KI-gestützte Änderungserkennung** für Anbieter-, Produkt- und
Konditionsdaten: „Veränderungen früher erkennen, Daten effizienter verarbeiten
und Tests häufiger aktualisieren.“ Der Kennzahlen-Radar ist genau diese
Maschine für FranksFinanzcheck – ohne Personal und ohne Paid-API, weil er auf
zwei Dingen aufsetzt, die ohnehin existieren:

1. **Agent-Reach-Briefs** (`data/research/`, Montags 08:15 MESZ) als
   Ereignis-Quelle („irgendetwas hat sich bewegt“),
2. **das Kennzahlen-Register** (diese Datei, von Hand gepflegt) als
   Soll-Zustand („was muss in welchem Rhythmus stimmen“).

## Was der Radar tut (und was nicht)

| Prüfung | Bedeutung |
|---|---|
| **Fälligkeit** | `stand + rhythmus_tage < heute` → Kennzahl ist zur Prüfung fällig (P2). |
| **Brief-Signal** | Ein Recherche-Brief nennt ein Suchwort der Kennzahl UND ist neuer als der Prüfstand → Frühwarnung (P3, mit Fälligkeit zusammen P1). |
| **Artikel-Kopplung** | `lastmod` eines betroffenen Artikels liegt VOR dem Kennzahlenstand → Artikel spiegelt den neuesten Stand vermutlich nicht. |

**Vertrag (wie bei faktenfrische.py):**

- Die Maschine **schreibt nie das Register** – `ist_wert`/`stand` pflegt Frank
  von Hand, nachdem er die Quelle geprüft hat.
- Die Maschine **ändert nie Artikeltexte** – Befunde gehen als Report/Issue an
  einen Menschen (KI-Redaktions-Statut, CLAUDE.md).
- Jede `quelle.url` im Register muss auf der **Beleg-Allowlist** stehen
  (`data/agent_reach/faktenfrische.yaml`, Rang 1–3). Affiliate-Partner
  (CHECK24, Tarifcheck …) sind als Kennzahlenquelle verboten – der Radar
  validiert das und läuft gegen ein kaputtes Register gar nicht erst (Exit 2).

## Bedienung

```bash
# Report erzeugen (schreibt KENNZAHLEN-RADAR.md + data/kennzahlen_radar.json)
python3 scripts/kennzahlen_radar.py

# Zusätzlich Issue-Body auf stdout (für gh issue create --body-file -)
python3 scripts/kennzahlen_radar.py --issue

# Forecast: was ist am Stichtag-X fällig? (z. B. vor der Heizsaison)
python3 scripts/kennzahlen_radar.py --as-of 2026-10-15

# Sabotage-Schutz (läuft auch in CI vor jedem Radar-Lauf)
python3 scripts/kennzahlen_radar.py --selftest
```

**Exit-Codes:** `0` = alles im Rhythmus · `1` = fällige Kennzahlen gefunden
(normal, erzeugt Report/Issue) · `2` = Register ungültig oder Selftest fehlgeschlagen.

## Register pflegen (nur von Hand)

Neue Kennzahl anlegen – Vorlage:

```yaml
- id: bdew-haushaltsstrompreis          # eindeutig, klein-mit-bindestrich
  name: "BDEW-Strompreisanalyse: Haushaltsstrompreis"
  einheit: "ct/kWh"
  ist_wert: "37,0"                       # NUR belegte Werte, nie aus dem Gedächtnis
  stand: 2026-08-21                      # Datum der letzten Prüfung
  quelle:
    name: "BDEW-Strompreisanalyse"
    url: "https://www.bdew.de/…"         # Domain muss auf der Allowlist stehen
  rhythmus_tage: 30                      # Prüfintervall
  toleranz: null                         # null = jede Abweichung melden
  ymyl: true
  suchbegriffe: ["Strompreis", "BDEW"]   # Trigger für die Brief-Signale
  betroffene_slugs:                      # Posts als Slug, Ratgeber mit pillar/…
    - "2026-08-19-energiediebe-stoppen-so-kannst-du-stromfresser-finden"
    - "pillar/strom-sparen"
```

**Nach einer Prüfung** (Ablauf aus jedem Radar-Issue):

1. Quelle öffnen, neuen Wert prüfen.
2. `ist_wert` + `stand` im Register aktualisieren (von Hand).
3. Zahlen in betroffenen Artikeln aktualisieren, danach
   `scripts/set_lastmod.py --git-changed` laufen lassen.
4. Optional Recherche-Belege auffrischen:
   `python3 scripts/faktenfrische.py --apply --max 3`.

## CI-Einbindung

- **Dienstag 06:20 MESZ** (`.github/workflows/kennzahlen-radar.yml`), direkt
  nach den Montag-Briefs des Agent-Reach-Research-Workflows.
- Committet nur `KENNZAHLEN-RADAR.md` + `data/kennzahlen_radar.json`
  (Bot-Commit via `scripts/git_sync.sh --push-only`, wie Faktenfrische).
- Öffenen ein Issue mit Label `kennzahlen-radar`, sobald
  `meta.melden.issue_ab_faellig` erreicht ist (Default 1). Keine Duplikate –
  pro Zyklus maximal ein offenes Radar-Ticket.

## Bekannte Grenzen

- **Werte liest der Radar nicht selbst aus dem Netz.** Er priorisiert, was zu
  prüfen ist; die Wertprüfung bleibt beim Menschen (Anti-Halluzinations-
  Vertrag). Eine spätere Ausbaustufe kann die Faktenfrische-Pipeline die
  `ist_wert`-Pflege vorschlagen lassen.
- **Brief-Signale sind Stichwort-Treffer**, keine Bestätigung. Ein Brief, der
  „Strompreis“ in einem anderen Kontext nennt, erzeugt trotzdem ein P1/P3 –
  bewusst: Lieber einmal zu viel hingeschaut (YMYL).
- **Ein Agenten-Token kann Workflow-Dateien nicht ändern** (CLAUDE.md,
  Known Issue). Fehlt der Workflow auf `main`, muss ein Mensch ihn per
  PR/Commit mit vollwertigem Token landen – die Datei liegt dann bereit.

## Verwandte Dokumente

- `KONKURRENZ-ANALYSE-FINANZTIP-KI-TOOLS-2026-09-28.md` – Herleitung (H5)
- `docs/ANLEITUNG-AGENT-REACH.md` – Briefs/Signale (Montags-Lauf)
- `docs/ANLEITUNG-SEO-COCKPIT.md` – warum es keine Wettbewerber-Kennzahlen hier gibt
- `CLAUDE.md` – KI-Redaktions-Statut und Leitplanken
