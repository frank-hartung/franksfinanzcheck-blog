# 🩺 DOKTOR-REPORT (Oberarzt, Gesamtprognose)

**Stand:** 2026-08-14 09:47 UTC · Modus: GEBURT
**Wachen behandelt:** 19 · **0-Exit:** 18 · Funde: 1 · Sabotage-Fehler: 0

| Wache (Phase) | Zweck | Exit |
|---|---|---|
| `integrity_guard.py` (0-LOCK) | Kern-Integritaet (Signatruehe nach Drift) | 0 |
| `casing_guard.py` (A-Text) | Akronyme/Marken (DSL, Check24) | 0 |
| `dash_guard.py` (A-Text) | Dash-Typografie R1-R9 | 0 |
| `unit_guard.py` (A-Text) | Euro/Prozent/NBSP | 0 |
| `emoji_guard.py` (A-Text) | Emoji-Zero-Width etc. | 0 |
| `lektor_guard.py` (A-Text) | Verlags-Lektorat L1-L15 | 0 |
| `hardcases_guard.py` (A-Text) | Deutsche Fest-Fehler H1-H9 (12.08. hinzu) | 0 |
| `stil_guard.py` (A-Text) | Stil-Qualitaet S1-S8 (12.08. hinzu) | 0 |
| `plagiat_guard.py` (B-Semantik) | Originalitaet P1-P5 + Fingerprint-Registry (12.08.) | 0 |
| `content_audit.py` (B-Semantik) | Content-Auditor C1-C6: Duenn, Struktur, Platzhalter (12.08.) | 0 |
| `compound_guard.py` (B-Semantik) | Komposita SEO-Falle | 0 |
| `math_guard.py` (B-Semantik) | Zahlenbeweis M1-M2 | 0 |
| `pillar_guard.py` (B-Semantik) | Tote Klartext-Artikelverweise auf Pillar-Seiten (13.08. hinzu, kein --fix: redaktionelle Entscheidung) | 0 |
| `affiliate_shield.py` (C-Money) | Auto-Deep + Gateways | 0 |
| `affiliate_marketer.py` (C-Money) | CTA-Routing + Retarget | 0 |
| `table_guard.py` (B-Semantik) | Tabellen T1-T4 | 0 |
| `link_guard.py` (C-Money) | Interne Links V1-V2 | 0 |
| `link_density_guard.py` (D-Ordnung) | Interne Link-Dichte & Duplikate (12.08. Pro-Link-Leck) | 1 |
| `workspace_guard.py` (D-Ordnung) | Junk/Waisen/Rotation/Billig | 0 |

## 🟡 Funde (nicht-fatal, dokumentiert)
- `link_density_guard.py`: Interne Link-Dichte & Duplikate (12.08. Pro-Link-Leck)

---
_Oberarzt bleibt bis zuletzt: Er loescht nur ueber die offiziellen Guards; Exit 2 einer Wache -> alles haelt._
