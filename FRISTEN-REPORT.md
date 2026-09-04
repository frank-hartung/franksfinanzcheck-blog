# ⏰ FRISTEN-REPORT – Recht & Compliance

**Stand:** 2026-09-04 · **Generator:** `scripts/fristen_check.py` (läuft täglich 07:55 MESZ via `.github/workflows/fristen-check.yml`)

> Kostenloses Erinnerungssystem für Rechtspflichten: Fristen aus `data/recht-fristen.yaml`, Eskalation über GitHub-Issues (`frist` → `frist-eskalation`). Erledigen = Workflow „Fristen-Check (Recht)“ starten mit `erledigt=<Frist-ID>`.

## Fristen-Kalender

| Status | Frist | Fällig am | Tage | Kategorie |
|---|---|---|---|---|
| 🟢 OK | BFSG/Barrierefreiheit: Scope-Bewertung dokumentieren (Empfehlung) (`bfsg-barrierefreiheit-bewertung`) | 2026-10-31 | in 57 | Barrierefreiheit |
| 🟢 OK | DPF-Zertifizierung GitHub & Cloudflare prüfen (Datentransfer USA) (`dpf-zertifizierung-pruefen`) | 2026-11-29 | in 86 | DSGVO / Drittlandtransfer |
| 🟢 OK | Partnerbedingungen CHECK24 / Tarifcheck / Awin prüfen (Werbekennzeichnung) (`affiliate-partnerbedingungen`) | 2026-11-29 | in 86 | Affiliate / UWG |
| 🟢 OK | Rechtslage-Screening: DSGVO-Reform, KI-VO, neue Pflichten (News-Check) (`rechtslage-screening`) | 2026-11-29 | in 86 | Rechtsbeobachtung |
| 🟢 OK | KI-VO: maschinenlesbare KI-Kennzeichnung für Bestandssysteme (Frist 02.12.2026) (`ki-vo-kennzeichnung-bestand`) | 2026-12-02 | in 89 | KI-Verordnung |
| 🟢 OK | Rechtstexte-Abgleich mit kostenlosem Generator (eRecht24 Basis / Dr. Schwenke) (`rechtstexte-halbjahrescheck`) | 2027-02-28 | in 177 | Rechtstexte |

## Sofort-Prüfungen (heute, automatisch)

### 🟢 Veraltungs-Scan: keine Funde

Keine veralteten Rechtsbegriffe (TMG, TTDSG, OS-Plattform, Privacy Shield, Safe Harbor) in `content/`, `layouts/`, `static/`.

### Stand-Datum der Rechtstexte

- 🟢 Impressum: Stand 2026-08-28 (7 Tage alt)
- 🟢 Datenschutzerklärung: Stand 2026-08-28 (7 Tage alt)

## So bedienst du das System

1. **Issue erhalten:** Ab Fälligkeits-Nähe legt der Bot ein Issue an (Label `frist`), am Stichtag und danach eskaliert er (Kommentare + Label `frist-eskalation`).
2. **Abarbeiten:** Checkliste im Issue abarbeiten.
3. **Erledigt markieren:** Actions → „Fristen-Check (Recht)“ → *Run workflow* → Eingabe `erledigt=<Frist-ID>` (mehrere mit Komma). Nur schließen reicht **nicht** – der Bot legt sonst neu an.
4. **Fristen pflegen:** Neue Pflichten in `data/recht-fristen.yaml` eintragen (Intervall oder einmaliges Datum) – fertig.

---
*Automatisch generiert am 2026-09-04 vom Fristen-Check (Recht). Letzte Erledigungen: –.*
