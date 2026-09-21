# 🛡️ Governance-Heilung #335 – Redaktionelle & technische Handlungsfelder

**Stand:** 21.09.2026 · **Auftrag:** „Dauerhaft auf Premium-Level einer Profi-Agentur beheben" (Issue #335) ·
**Basis:** Premium-Governance-Lauf 21.09.2026 10:46, Ampel RED, Fingerabdruck `3a156412e360`

---

## Ergebnis je Handlungsfeld

| Feld | Vorher | Nachher | Wurzelursache & Heilung |
|---|---|---|---|
| Lesbarkeits-Wache (Bestand) | 🔴 3 Artikel unter Floor (50,8–51,8) | 🟢 Ø Flesch 63,1 ≥ 62, 0 unter Floor 55 | Fünf Bestandsartikel redaktionell gehoben (Satzrhythmus, Silbenlast, Absatzlängen) – inkl. zwei Nachrücker unter Floor und zwei knapp unter Ziel |
| Live-Konsistenz (Cloudflare/CDN) | 🔴 robots-Gruppen + Money-URL fehlen live | 🟢 Repo/Build vollständig, Tier-Artikel wieder freigegeben | Zwei Ursachen: (a) Deploy-/Cache-Hysterese (Repo-Seite war korrekt – Abgleich nach Deploy), (b) Tier-Post war 12:44 vom Kadenz-Gate geparkt worden (quality-score 0,745 < 0,85). Post geheilt (Score 0,99) und über den offiziellen Pfad `requeue_quality_holds.py --fix` → `cadence_guard.py --requeue` → `publish_gate.py` (0/3 Verstöße) wieder live gebracht |
| Secrets-/Token-Wache | 🔴 Pinterest-Token abgelaufen | 🟡 → One-Click-Rest (siehe unten) | Token-Broker + Runbook sind bereits selbsttragend („danach trägt sich der Kanal selbst"). Offen bleibt ausschließlich die **einmalige OAuth-Autorisierung mit Franks Pinterest-Konto** – ein Klick-Zweistarter, exakte Kommandos unten. `PINTEREST_TOKEN_KEY` = GitHub-Secret, nur im Org-Kontext setzbar |
| Klick-Messkette (CTA→Event→Gateway→SubID) | 🟠 1 Messlücke (`/go/strom/` ohne placement) | 🟢 GREEN, 0 Messlücken (68 Seiten) | Card-CTA in `layouts/shortcodes/einspartabelle.html` renderte ohne `data-umami-event-subid`/-`placement` (Tabellen-Variante war vollständig, Card-Variante nicht). Vertrag vervollständigt – eine Quelle der Wahrheit wie in `ff_affiliate_cta`/`render-link` |
| Umsatz-Funnel (Besuch→Klick→Antrag→Provision) | 🟠 3 Import-Lücken (Secrets fehlen) | 🟡 → One-Click-Rest (siehe unten) | Messkette technisch dicht (Selftest grün). Es fehlen nur die drei API-Credentials (`UMAMI_API_TOKEN`, `AWIN_API_TOKEN`, `AWIN_PUBLISHER_ID`) – Werte liegen nur in Franks Konten, Agenten-Token darf Repo-Secrets weder lesen (403) noch setzen |

## Redaktionelle Heilungen im Detail (Lesbarkeit)

| Artikel | Flesch vorher | Flesch nachher | Score |
|---|---|---|---|
| 2026-09-04 digitaler-turbo (DNS-Hack) | 51,5 | 67,8 | 100 |
| 2026-09-17 versicherung-update | 51,8 | 60,4 | 100 |
| 2026-09-20 gasrechnung-senken-clevere-herbst | 50,8 | 60,1 | 100 |
| 2026-09-21 7-gewohnheiten (Nachrücker unter Floor 48,5) | 48,5 | 60,9 | 95 |
| 2026-09-21 unfallversicherung-vergleich (Nachrücker unter Floor 51,3) | 51,3 | 60,4 | 95 |

Methode: Hebel-Analyse je Artikel (Satzlängen, Silben/Wort, Absatz-Sätze) entlang der exakten Messlogik von `readability_check.py` – geschachtelte Sätze getrennt, Amts- und Komposita-Ballast durch Klartext ersetzt (z. B. „Versicherungsunternehmen" → „Versicherer", „markiert einen Wendepunkt" → „ist ein Wendepunkt"), Duden-konforme Nominal-Formen („das 3,5-Fache"), echte Fehler bereinigt („Heitzt" → „Heizt", „rausbekommt" → „herausbekommt", Doppel-„senken" im Gas-Artikel). Inhalte, Zahlen, Links und Keywords blieben unangetastet – für „7-Gewohnheiten"/„Unfallversicherung" zusätzlich ≥ 60 Flesch (R6-Zielhorizont für neue Artikel), damit künftige Publish-Tage nicht erneut parken.

**Whitelist-Ergänzung** (`data/spellcheck_whitelist.txt`, Abschnitt „Fach-/Domänenvokabular 21.09.2026"): ~70 korrekte Fachkomposita/Kürzel/adjektivische Zahlformen (OP-Schutz, GOT-Satz, 3-/-4-fach-Formen, ED/HD, Gliedertaxe-Werte …), die Hunspell nicht kennt. Zusammen mit den Textkorrekturen hebt das `spelling` von 0,0 auf 1,0 – exakt die Issue-#251-Klasse („Wörterbuch-Lücken dürfen keine Artikel mehr sperren"). Ohne diese Heilung hätte der Tier-Artikel trotz inhaltlichem Facelift unter der Publish-Schwelle 0,85 geklemmt.

## Tierkrankenversicherung – der Live-Fall (L2/L3)

Zeitkette des Vorfalls: 09:59 erzeugt → 10:46 live gebaut (Funde L2/L3: Deploy-Hysterese) → 12:44 von `publication_release.hold_under_score_candidates` als **hold** geparkt („quality-score: 0.745 < 0.85; finale Freigabe fehlt") → URL in der Live-Sitemap ohne Ziel.

Heilung (vom Buch geplant, kein Hand-Patch):
1. Titel 61 → 53 Zeichen (Meta-Schwelle ≤ 60, Endwort R5-konform „versichern" statt des nicht gelisteten „absichern") – **Faustregel für die Engine: Titel-Endwörter gegen `check_titles.py` R5_END_WHITELIST prüfen, BEVOR der Titel in den Publish-Pfad geht.**
2. Rechtschreib-Whitelist + Textfehler → `quality_score` 0,745 → **0,99**.
3. `requeue_quality_holds.py --fix` (hold → queue, Score ≥ 0,80) → `cadence_guard.py --requeue` (Förderung bis Tageslimit, Montag = Publikationstag) → `publish_gate.py` **0/3 Verstöße**.
4. Build: Post + Sitemap-Eintrag + Klick-Kette (68 Seiten) grün.

**Warnung aus dem Vorfall (ins Runbook aufgenommen):** `publish_gate.py` verwirft Artikel des HEUTIGEN Ordner-Präfixes bei harten Fehlern **destruktiv** (Datei + Covers). Vor jedem harten Gate-Lauf auf Tages-Kandidaten ist der Stand zu committen oder zu sichern; Fehlschläge sind `git checkout`-wiederherstellbar. Ältere Re-Queue-Posts werden nur auf draft gesetzt – die Zwei-Klassen-Logik ist gewollt, aber nur sicher, wenn sie jeder kennt.

## Verifikationsstand (alles ausgeführt, alles grün)

```
hugo --destination public                          ✅ 197 Seiten
python3 scripts/publish_gate.py                    ✅ 0/3 scheitern
python3 scripts/click_chain_guard.py               ✅ GREEN, 0 Messlücken (68 Seiten)
python3 scripts/readability_check.py               ✅ Ø 63,1, kein Artikel < 55
python3 scripts/check_titles.py                    ✅ 58 Titel, 0 Verstöße
python3 scripts/affiliate_integrity_gate.py        ✅ (+ Selftest)
python3 scripts/governance_contract.py             ✅ 18/18 Regeln
python3 scripts/themenwelten_guard.py              ✅ sechs Themen sauber
Selftests: readability · click_chain · live_policy · affiliate_integrity · alert_router · revenue_funnel  ✅
quality_score (5 geheilte Artikel)                 ✅ 0,86–1,00 (alle „publish")
```

## Offene One-Click-Reste (Mensch mit Credentials – je 2 Minuten)

**A. Pinterest-Kanal wiederbeleben** (`docs/PINTEREST-TOKEN-RUNBOOK.md`, Schritte 1–4):
```bash
gh workflow run pinterest-token.yml -f show_auth_url=true    # Link aus Summary öffnen, „Erlauben"
gh workflow run pinterest-token.yml -f auth_code="<Code>"    # Code von /pinterest-oauth einfügen
```
Danach erneuert sich der Token täglich selbst; die Wache schließt ihr Issue automatisch.

**B. Umsatz-Funnel befüllen** (`docs/UMSATZ-MESSUNG-PREMIUM.md`, „zwei Secrets → Testklick"):
```bash
gh secret set UMAMI_API_TOKEN       # Umami-Dashboard → API-Token
gh secret set AWIN_API_TOKEN        # Awin → API Credentials
gh secret set AWIN_PUBLISHER_ID
# danach genügt ein Testklick auf einen /go/-Button (SOP: NIE Eigenabschluss!)
```
Der Import läuft dann regelmäßig (`revenue-import.yml`); `revenue_funnel.py --print` zeigt den vollen Trichter.

---
*Erstellt zur Schließung aller Handlungsfelder aus Issue #335 · Verifikation in `arena/01a0c45a-franksfinanzcheck-blog`.*
