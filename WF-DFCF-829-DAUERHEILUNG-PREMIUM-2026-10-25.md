# WF-DFCF #829 – Dauerheilung: Wöchentliche SEO-Optimierung & Affiliate-Link-Check

**Datum:** 2026-10-25  
**Vorgang:** `WF-DFCF` ([Issue #829](https://github.com/frank-hartung/franksfinanzcheck-blog/issues/829))  
**Workflow:** `Wöchentliche SEO-Optimierung` (`.github/workflows/seo-weekly.yml`)  
**Fehlgeschlagener Lauf:** [`39609412316`](https://github.com/frank-hartung/franksfinanzcheck-blog/actions/runs/39609412316) (Job `119254013597`, Schritt 18: `Affiliate-Link-Check (Deep-Links – VOLLAUTOMATISCH)`)

---

## 1. Ursachenanalyse (Root Cause Analysis)

Im wöchentlichen Lauf `39609412316` am Mittwoch, 21.10.2026 brach Schritt 18 (`python3 scripts/affiliate_link_check.py --fix`) mit Exit-Code `1` ab, wodurch die Folgeschritte 19–37 übersprungen wurden.

Der konkrete Befund lautete:

```text
❌ 2026-10-07-urlaub-sparen-7-clevere-wege-deine-kasse-zu-fuellen: Fehlt der passende Deep-Link: https://a.check24.net/misc/click.php?pid=80968&aid=18&deep=mietwagen-preisvergleich&cat=10 (erwartet: Mietwagen-Vergleich)
```

### Warum der Artikel fachlich korrekt war, die Wache aber rot schlug

1. **Sammel-Pillar `mietwagen` („Mietwagen & Reisen“):**  
   Der am 16.10.2026 aus der Reserve veröffentlichte Artikel `content/posts/2026-10-07-urlaub-sparen-7-clevere-wege-deine-kasse-zu-fuellen/index.md` (*„Urlaub sparen: Budget, Buchung und Kosten im Blick“*) ist der datierte Nachfolger der früheren Slugs `urlaubskasse-aufbessern-spartipps` und `urlaub-mit-kindern-guenstig-spartricks` (vgl. `data/weiterleitungen.yaml`). Er liegt im Sammel-Pillar `mietwagen` (*„Mietwagen & Reisen“*) und verlinkt vertragskonform auf `/go/reisen/` (`deep=pauschalreisen-vergleich&cat=9`).
2. **Vertragsdrift zwischen `affiliate_link_check.py` und `affiliate_intent_contract.py`:**  
   - Während `affiliate_intent_guard.py` (IW0–IW9), `affiliate_profi_check.py` (A1–A8) und `affiliate_integrity_gate.py` (AI1–AI6) den Artikel bereits bei der Veröffentlichung zu 100 % grün prüften, kannte `affiliate_link_check.py` in `SLUG_DEEP` nur die alten undatierten Slugs (`urlaubskasse-aufbessern-spartipps`, `urlaub-mit-kindern-guenstig-spartricks`).
   - In `expected_target(post)` wurde der zentrale `affiliate_intent_contract` nach #742 lediglich für die Einzelroute `handytarife` abgefragt; alle übrigen eindeutigen Produktrouten (`EXPLICIT_PRODUCT_ROUTES`) sowie explizite Pauschalreise-/Urlaubsbudget-Ratgeber (`REISEN_EXPLICIT_RE`) fielen ungeprüft auf den groben Pillar-Default (`mietwagen-preisvergleich&cat=10`) zurück.
   - `PILLAR_DEEP_ALT` bildete bislang nur die Produktfamilie des Pillars `strom-sparen` (Strom + Gas) ab, nicht aber die Mehrprodukt-Pillars `mietwagen` (*Mietwagen & Reisen*) und `konto-karten` (*Girokonto/Tagesgeld, Kreditkarte, Ratenkredit*).
3. **Veraltete Vor-August-Deep-Links in `SLUG_DEEP`:**  
   Sechs historische Einträge in `SLUG_DEEP` verwiesen noch auf nicht mehr in `scripts/check24_links.yaml` registrierte Deep-Werte (`flugvergleich`, `kreditvergleich`, `tagesgeldvergleich`), die bereits am 11.08.2026 im zentralen Gateway-Register auf `pauschalreisen-vergleich&cat=9`, `kredit-vergleich` und `c24bank&cat=14` umgestellt worden waren.

---

## 2. Durchgeführte Dauerheilung

### 2.1 `scripts/affiliate_link_check.py`
- **Bestands- und Nachfolger-Mapping (`SLUG_DEEP`):**
  - `2026-10-07-urlaub-sparen-7-clevere-wege-deine-kasse-zu-fuellen` auf `("pauschalreisen-vergleich&cat=9", "Pauschalreisen-Vergleich")` aufgenommen.
  - Die 6 historischen Alt-Einträge (`guenstige-fluege-spaetsommer-finden`, `flug-buchen-9-tricks-guenstige-tickets`, `ratenkredit-bestszins-vergleichen`, `dispozinsen-verstehen-alternativen`, `tagesgeld-zinsen-sicher-anlegen`, `festgeld-oder-tagesgeld-2026`) mit den registrierten Routen aus `scripts/check24_links.yaml` synchronisiert.
- **Zentrale Intent-Auflösung vor Pillar-Fallback (`EXPLICIT_PRODUCT_ROUTES` & `REISEN_EXPLICIT_RE`):**
  - Eindeutige Einzelprodukt-Klassen (`handytarife`, `kreditkarte`, `kredit`, `fluege`, `kfz-versicherung`, `haftpflicht`, `hausrat`, `wohngebaeudeversicherung`, `unfallversicherung`, `reisekrankenversicherung`, `zahnzusatzversicherung`, `hunde`) werden aus `affiliate_intent_contract.route_fuer_text(slug, title)` direkt über `_target_from_registered_route(route)` aufgelöst.
  - Explizite Pauschalreise-/Urlaubsbudget-Ratgeber (`REISEN_EXPLICIT_RE`: `pauschal|all.inclusive|urlaubskasse|urlaub[- ]sparen`) lösen direkt auf `/go/reisen/` (`pauschalreisen-vergleich&cat=9`) auf, ohne dass Roadtrip-/Mietwagen-Artikel mit allgemeinem Urlaubsbezug im Titel fälschlich umgebogen werden.
- **Vollständige Pillar-Produktfamilien (`PILLAR_DEEP_ALT`) mit `STRICT_PRIMARY_ROUTES`-Schutz:**
  - `PILLAR_DEEP_ALT` umfasst nun alle drei Mehrprodukt-Pillars:
    - `strom-sparen`: `gasanbieter-wechseln&cat=3`
    - `mietwagen`: `pauschalreisen-vergleich&cat=9`
    - `konto-karten`: `kreditkarte`, `kredit-vergleich`
  - Schutz der `NIE_PAARE` aus `affiliate_intent_contract.py`: Trägt ein Artikel in Slug oder Titel bereits einen expliziten Primärprodukt-Intent (`STRICT_PRIMARY_ROUTES`: `strom`, `dsl`, `mietwagen`, `girokonto`, `tagesgeld`), darf er **nicht** über `PILLAR_DEEP_ALT` auf ein Nachbarprodukt ausweichen (z. B. reiner Mietwagen-Ratgeber mit `/go/reisen/` oder reiner Girokonto-Ratgeber mit `/go/kredit/` bleibt ein Fehler).
- **Selbsttest-Härtung (`--selftest`):**
  - Erweitert auf 8 eingefrorene Verträge inkl. Urlaubsbudget-Ratgeber unter `mietwagen`, `STRICT_PRIMARY_ROUTES`-Schutz und vollständigem Abgleich aller konfigurierten Deep-Links gegen `scripts/check24_links.yaml`.

### 2.2 `scripts/tests/test_affiliate_link_check.py` & Dokumentation
- Regressionstests für Issue #829 ergänzt:
  - Live-Artikel `2026-10-07-urlaub-sparen-7-clevere-wege-deine-kasse-zu-fuellen`
  - Neue Urlaubskasse-/Pauschalreise-Ratgeber im Pillar `mietwagen` (z. B. Reserve-Entwurf `2026-10-19-urlaubskasse-clever-aufbessern`)
  - `PILLAR_DEEP_ALT`-Familienlogik vs. `STRICT_PRIMARY_ROUTES`-Sperre für `mietwagen` und `konto-karten`
  - Spartenexakte Prüfung für `versicherungen`
  - Vollständiger Register-Abgleich aller Deep-Links gegen `scripts/check24_links.yaml`
  - Gesamter Live-Bestand (`checker.load_posts()`, 72 Seiten) fehlerfrei in der täglichen CI (`affiliate-integrity-daily.yml` + `seo-weekly.yml`)
- `docs/ANLEITUNG-CHECK24-LINKS.md` aktualisiert.

---

## 3. Verifikation

- `python3 scripts/affiliate_link_check.py --selftest` → **8 Verträge grün** (Exit 0)
- `python3 scripts/affiliate_link_check.py` → **72 Posts | Probleme: 0 | Korrigiert: 0** (Exit 0)
- `npm run test:affiliate-links` → **56 Unit-Tests + beide Gate-Selbsttests grün** (Exit 0)
- `python3 scripts/affiliate_intent_guard.py --selftest` & `--no-write` → **0 Befunde** (Exit 0)
- `python3 scripts/release_scorecard.py --selftest` & `python3 scripts/ff_inhalts_wache.py` → **grün, alle Siegel unverändert intakt**
