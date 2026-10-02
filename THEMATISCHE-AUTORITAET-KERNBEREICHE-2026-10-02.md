# 🏛️ Thematische Autorität & Kernbereich-Dominanz (Profi-Agentur-Audit & Umsetzung)

**Datum:** 02.10.2026  
**Projekt:** FranksFinanzcheck (franksfinanzcheck.de)  
**Auftrag:** „4. Die thematische Breite verwässert die Autorität – dauerhaft auf Highend-Level einer Profi-Agentur beheben.“

---

## 1. Strategische Ausgangslage & Problemstellung

Die thematische Streuung über 62 Beiträge und sechs Themenwelten wies Überlappungen auf (mehrere Gas-/Heizkosten-, DSL-/WLAN-, Frugalismus-/Notgroschen- und Update-Artikel). Um FranksFinanzcheck im deutschsprachigen Raum als unverwechselbare Autoritätsmarke („Fixkosten-Cockpit für deutsche Haushalte“) zu etablieren, war nicht die Erstellung weiterer disparater Artikel der richtige Schritt, sondern die **vollständige Beherrschung und Dominanz von drei strategischen Kernbereichen**, während Randthemen gezielt als unterstützende Satelliteninhalte geführt werden.

---

## 2. Die 3 dominanten Kernbereiche vs. Unterstützende Randthemen

### Die 3 Kernbereiche (Flagship-Dominanz)
1. **Strom, Gas und Fixkosten** (`/pillar/strom-sparen/`):
   - Vollständige Beherrschung der Energiekosten (Strom, Gas, Wärmepumpenstrom § 14a EnWG, Standby-Lecks, dynamische Börsenstromtarife, Preisgarantien).
2. **Verträge und Wechselentscheidungen** (`/pillar/internet-dsl/`):
   - Vollständige Beherrschung aller Vertrags-, Kündigungs- und Wechselprozesse (DSL, Kabel, Glasfaser FTTH, Mobilfunk SIM-Only, 1-Monats-Kündigungsfrist nach BGB § 309 Nr. 9 & TKG § 56, Kündigungsbutton, Kündigung vs. Retention-Verhandlung).
3. **Haushaltsbudget und finanzielle Puffer** (`/pillar/frugalismus/`):
   - Vollständige Beherrschung von Budgetierung und Rücklagenbildung (50–30–20-Regel, 3-Stufen-Notgroschen-Architektur, 3-Konten-System, automatisierte Daueraufträge am Monatsersten, Dispo-Beseitigung).

### Unterstützende Satelliten-Themen (Supportive Modules)
- **Versicherungen & Vorsorge** (`/pillar/versicherungen/`): Fokussiert auf existenzielle Risiken (Haftpflicht, Wohngebäude, Kfz zum 30.11.).
- **Konto, Karten & Zinsen** (`/pillar/konto-karten/`): Gebührenfreies Banking und Tagesgeld-Infrastruktur als technischer Unterbau.
- **Mietwagen & Reisen** (`/pillar/mietwagen/`): Reine Kostenfallen-Vermeidung bei Reisen, klar untergeordnet.

---

## 3. Der 8-Punkte-Toolkit-Ausbau je Kernbereich

Jeder der drei Kernbereiche wurde mit dem vollständigen, von einer Profi-Agentur geforderten Instrumentarium ausgestattet:

| Element | 1. Strom, Gas & Fixkosten | 2. Verträge & Wechsel | 3. Budget & Puffer |
|---|---|---|---|
| **1. Pillar-Master-Ratgeber** | Tiefgehender, analytischer Leitfaden auf ZEIT/WiWo-Niveau (`strom-sparen`) | Leitfaden für 24M-Effektivpreise, TKG/BGB-Rechte & Wechsel ohne Ausfall (`internet-dsl`) | Leitfaden für 50–30–20, 3-Konten-System & Notgroschen-Staffelung (`frugalismus`) |
| **2. Interaktiver Rechner** | Strom- & Gas-Abschlagsrechner mit Nachzahlungs-Ampel | DSL- & Vertrags-Effektivpreis-Rechner über 24 Monate | 50–30–20-Budget- & Notgroschen-Ziel-Rechner |
| **3. Praxis-Checkliste** | 10-Punkte Energie- & Heizkosten-Audit (interaktiv/druckbar) | 8-Punkte Vertrags- & Kündigungs-Audit | 7-Punkte Haushaltsbudget- & Puffer-Checkliste |
| **4. Entscheidungstabelle** | Matrix: 12M-Festpreis vs. Dynamisch vs. Wärmepumpe vs. Grundversorgung | Matrix: Kündigen vs. Wechseln vs. Nachverhandeln vs. Sonderkündigung | Matrix: Notgroschen-Höhe nach Lebenslage & Berufsstatus |
| **5. Fallstudien** | Familie Peters (EFH Gas: 1.150 €/J) & Jonas (Single Altbau: 390 €/J) | Elena & David (Zusammenzug: 1.577 €/J) & Helga/Klaus (Kabel/DSL: 490 €/J) | Familie Becker (Dispo-Tilgung + 5.200 € Puffer) & Lea (3.380 € Puffer) |
| **6. Aktuelles Marktradar** | Q4 2026: Strom Ø 36,8 ct, Gas Ø 10,2 ct, CO₂-Preis 55–65 €/t, § 14a EnWG | Q4 2026: Breitbandspannen, § 312k Kündigungsbutton, BNetzA-Minderung | Q4 2026: Tagesgeld bis 3,45 %, Festgeld 3,30 %, Einlagensicherung 100k € |
| **7. Quellen- & Revisionslog** | BDEW, BNetzA, vzbv + Revisionshistorie v1.0 bis v2.2 | BNetzA, BMJ, BGB, TKG + Revisionshistorie v1.0 bis v2.2 | Bundesbank, Destatis, BaFin + Revisionshistorie v1.0 bis v2.2 |
| **8. Newsletter-Serie** | 4-Tage-Kurs: *Der Energie- & Fixkosten-Autopilot* | 4-Tage-Kurs: *Der Vertrags-Detox-Masterplan* | 4-Tage-Kurs: *Der 50-30-20 & Notgroschen-Bauplan* |

---

## 4. Technische Umsetzung & Invarianten

1. **Rechner-Engine (`static/premium/ff-rechner.js` & `tools/ff-rechner.test.cjs`):**
   - 100 % clientseitige Berechnung ohne Tracking, Cookies oder externe Netzanfragen.
   - Erweiterung um `budget-503020` und `gas-abschlag` mit vollem automatisierten Testlauf.
2. **Design-System (`assets/css/extended/zzz-agency-polish.css`):**
   - Neue Klassen `.ff-audit-checklist`, `.ff-decision-matrix`, `.ff-case-study-box`, `.ff-radar-card`, `.ff-course-series-box`, `.ff-changelog-card`, `.ff-pillar-core-badge`.
   - Volle Dark-Mode-Kompatibilität (`:root[data-theme="dark"]`), WCAG 2.1 AA Kontraste und Responsive Design (320px bis 1920px).
3. **Pillar-Hub & Hierarchie (`content/pillar/_index.md`, `layouts/pillar/list.html`, `layouts/pillar/single.html`):**
   - Die 3 Kernbereiche stehen an oberster Stelle und tragen optisch hervorgehobene Badges (`🌟 Kernbereich · Flagship`).
   - Die unterstützenden Themenwelten sind sauber als flankierende Module integriert.
4. **Verifikations-Pipeline:**
   - 1.214 Python-Unit-Tests bestanden (`python3 -m unittest discover -s scripts/tests`).
   - Node-Rechner-Tests 5/5 grün (`node --test tools/ff-rechner.test.cjs`).
   - Alle E2E-Playwright-Tests auf Desktop & Mobile bestanden (`npx playwright test`).
   - Alle Governance-Gates (`themenwelten_guard.py`, `offenlegung_gate.py`, `beweis_gate.py`, `index_hygiene_gate.py`, `layout_audit.py`) 100 % grün.

---

## 5. Fazit

Die thematische Verwässerung ist dauerhaft behoben. FranksFinanzcheck präsentiert sich jetzt mit glasklarem thematischen Profil, unangefochtener inhaltlicher und technischer Autorität in den drei Schlüsselbereichen und einer Architektur, die Vertrauen schafft, Rankings schützt und Leser nachvollziehbar zum nächsten Schritt führt.
