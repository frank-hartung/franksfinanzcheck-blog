# 📅 CADENCE-REPORT – Veröffentlichungs-Kadenz (DAUERVORGABE)

**Festgelegt:** 19.08.2026 · **Gültigkeit:** dauerhaft (keine dynamische Anpassung)
**Umsetzung:** `.github/workflows/content-engine-v2.yml` + harter Wochentags-Guard in
`scripts/engine_generate.py` · Verbindlich auch in
`docs/MASTER-SYSTEM-FRANKSFINANZCHECK.md` (Kapitel 4.0) und `QUALITAETS-REGELWERK.md`.

## Regelwerk

1. **Blog-Launch: 08.08.2026.** Kein Artikel trägt je ein Datum vor dem 08.08.2026.
   Der vor dem Launch datierte Alt-Bestand (36 Posts, ursprünglich 03.–07.08.2026)
   wurde am 19.08.2026 dauerhaft gelöscht – inkl. Cover-Varianten,
   Covers-Manifest, Pinterest-Pin-Queue, Content-Fingerprints und interner Links.
2. **Veröffentlichung nur montags, mittwochs und freitags – 2 bis 3 Artikel
   pro Publikationstag** (≈ 6–9 Artikel/Woche).
   - Haupt-Slot: **08:10 MESZ** (06:10 UTC) · Fallback-Slot 1: 16:10 MESZ ·
     Fallback-Slot 2: 19:40 MESZ
   - Cron: `10 6 * * 1,3,5` (content-engine-v2.yml)
   - Tagesmenge: `MIN_ARTIKEL_PRO_TAG` (Default 2) bis `MAX_ARTIKEL_PRO_TAG`
     (Default 3); die Engine füllt das Tageslimit selbstständig auf
     (Profi → Relaxed → Draft-Rettung pro Artikel).
   - **Dauervorgabe-Floor in der Engine:** Werte unter 2 werden auf 2
     angehoben – der Workflow-Legacy-Fallback „1“ kann die Kadenz nicht
     unter das Mindestziel drücken. Empfohlen (optional): Repository-
     Variablen `MAX_ARTIKEL_PRO_TAG=3` und `MIN_ARTIKEL_PRO_TAG=2` setzen
     (GitHub → Settings → Secrets and variables → Actions → Variables).
   - **Harter Wochentags-Guard** in `scripts/engine_generate.py`
     (`PUBLICATION_DAYS = {0, 2, 4}`): auch manuelle `workflow_dispatch`-Läufe
     veröffentlichen an Di/Do/Sa/So nichts. Notfall-Override:
     `FORCE_PUBLISH_ANY_DAY=1` (Env).
3. **Bestands-Bereinigung (19.08.2026, Frank: „Der Blog zeigt zu viele
   Artikel an – vollständig optimieren auf 2–3 Artikel an Mo/Mi/Fr“):**
   - Gelöscht (vollständig, inkl. Covers, Manifest, Pin-Queue, Fingerprints,
     Affiliate-Report, IndexNow-Log, Ops-Report und interner Links):
     **38 Posts** – 6 datierte Off-Kadenz-Posts (08.08. Sa ×2, 08.09. So ×2,
     08.11. Di ×2) + 32 Evergreen-Posts (alle datiert 08.09. So).
   - Verblieben: **6 Posts**, je 2 an Mo 08.10., Mi 08.12. und Fr 08.14. –
     exakt das Muster „2 Artikel pro Publikationstag“. Die Engine baut ab
     dem nächsten Publikationstag (Mi 19.08.) mit 2–3 Artikeln/Tag auf.
   - Zusätzlich repariert: `data/topics.yaml` (erneute Whitespace-Korruption
     durch Fazit-Schmiede-Lauf; aus Git-Historie auf 175 lesbare Themen
     zurückgerollt – Ursache des Engine-Ausfalls seit 17.08.2026) sowie
     2 im Frontmatter abgeschnittene Titel.
4. Die Frequenz ist **fix**. Der frühere, dynamische `cadence_manager.py`
   (Ramp-Logik) existiert nicht mehr – dieser Report ist die verbindliche
   Definition. Änderungen nur noch per ausdrücklichem Beschluss Franks
   (Dokumentation hier + Kapitel 4.0 im Master-System).
5. **Hartes Vor-Veröffentlichungs-Gate + Selbstheilung (26.08.2026,
   nach Fund von 7 Kadenz-Verstößen + 6 unvollständigen Titeln/Cover-Texten):**
   Die Kadenz ist nicht mehr nur „vorgeschrieben“, sondern wird VOR JEDEM
   Publish technisch erzwungen – ein Verstoß kann nicht mehr live gehen,
   egal welcher Pfad (manueller Commit, `publish.py`, Content-Engine,
   `workflow_dispatch`) ihn in `main` bringt:
   - **`scripts/cadence_guard.py` – die Kadenz-Wache (Single Source of
     Truth).** Prüft `Mo/Mi/Fr` + `2–3/Tag` gegen das FRONTMATTER-Datum
     (nicht den Ordner-Namen – bleibt bei Re-Queue stabil). Modus:
     `--check` (Bericht), `--fix` (Selbstheilung: Off-Day/Über-Max-Posts →
     `draft: true` + `cadence_wait: true`, d. h. Re-Queue in den nächsten
     Publikationstag – Content geht nie verloren), `--selftest` (Exit 2
     bricht jede CI-Stage ab, wenn das Gate selbst defekt ist).
     Report: `CADENCE-GATE-REPORT.md` (eingecommittet).
   - **Deploy-Gate** (`deploy.yml`): vor JEDEM Hugo-Build läuft
     Selbsttest → `cadence_guard --fix` → `check_titles --fix` →
     `check_covers --fix`; Heilungen werden konvergent gepusht (der
     Folge-Deploy findet einen sauberen Zustand). Erst danach Build.
   - **Publish-Gate** (`publish_gate.py`, Engine-Level): zählte bisher
     nur Ordner-Präfix-Posts des Tages; zählt jetzt auch Frontmatter-
     Datum = heute (Re-Queue-Promotions) und prüft **5. harte Prüfung:
     Cover-Text-Komplettheit** (`check_titles` R5 – Titel mit
     unvollständigem/hängendem Ende wird verworfen, wenn neu, bzw.
     als Re-Queue auf draft zurückgestuft).
   - **Content-Engine v2**: Phase 0.5 (Kadenz-Selbsttest + `--fix` vor
     JEDEM Slot) und Phase 6 (`engine_issue.py --deficit` – sichtbares
     GitHub-Issue, wenn am Tagesende unter Mindestziel liegt; schließt
     sich selbst, sobald das Minimum wieder erfüllt ist).
   - **Blog-Health (täglich 07:45 MESZ):** `cadence --selftest` + `--fix`
     + Titel-/Cover-Gate heilen auch ZWISCHEN den Publishing-Slots.
   - **`scripts/publish.py`:** manuelles Publizieren unterliegt der
     SELBEN Routine (Regel 2); Verstoß wird hart blockiert (Notfall:
     `--force-cadence`/`FORCE_PUBLISH_ANY_DAY=1`, sichtbar im Commit-Log).
     Veröffentlichen setzt das Frontmatter-Datum auf heute (Re-Dating).
   - **`safe_title_cut()` in `post_utils.py`:** zentrales Kürzen von
     Titeln an Wortgrenzen (nie mitten im Wort, nie mit hängendem
     Gedankenstrich) – ersetzt alle harten `title[:60]`-Slices in
     `meta_optimizer.py` und `engine_generate.py`. Die Ursache der
     unvollständigen Cover-Texte vom 26.08.
   - **`check_covers.py` C4:** verifiziert für JEDES Cover, dass der
     komplette Titel im Textbereich rendert (1:1-Nachbau des
     Render-Flows inkl. Zeilenbruch + Zeichen-Hard-Wrap); `--fix`
     rendert Verstöße neu. `generate_covers.py` selbst hat jetzt
     Zeichen-Hard-Wrap + Y-Start-Clamp als letzte Sicherheitslinie.
   - **Vorgang am 26.08.2026 (Beleg):** 7 Verstöße geheilt
     (5 Off-Day: 08.16. Sa ×2, 08.18. So ×2, 08.20. So; 2 Over-Cap:
     08.14. Fr, 08.26. Mi) → 18 live, jeder Tag exakt 2–3 · 6
     unvollständige Titel repariert (Wortbruch durch alte `[:60]`-
     Kürzung) + ihre Covers neu gerendert. Ergebnis: Bestand 100 %
     konform, alle Gates grün.
6. **Pagination-Fix (19.08.2026, nachgeschärft am selben Abend):** Mit nur
   6 Posts und `pagerSize = 8` existierten `/posts/page/2/` (und höhere)
   nicht mehr – bisher 404. `content/_index.md` aliasiert nur noch
   `/page/3/`–`/12/` → `/`, `content/posts/_index.md` nur noch
   `/posts/page/3/`–`/12/` → `/posts/`: Seit 10 Posts erzeugt Hugo
   `/page/2/` und `/posts/page/2/` wieder selbst – ein Alias auf dieselbe
   URL kann den Build (`hugo --minify`) hart abbrechen. Zusätzlich:
   `layouts/_partials/head.html` greift nicht mehr auf `.Paginator` zu
   (erster Zugriff sperrt die Seitenmenge und hat die Startseiten-Liste
   verfälscht).

## Empfohlene Zeichenlänge pro Blogartikel (Dauervorgabe, same Tag festgelegt)

- **6.000–10.000 Zeichen Fließtext** (≈ 800–1.400 Wörter)
- Empirisch begründet: Bestands-Median 9.124 Zeichen bei 6,96 Zeichen/Wort
- Überwacht von `scripts/check_length.py` (`OPT_CHARS_MIN/MAX`, Env-übersteuerbar
  via `LENGTH_OPT_CHARS_MIN/MAX`); harte Gates bleiben wortbasiert

---
_Stand: 26.08.2026 · Bestand: 18 live (2–3 an jedem Publikationstag 08.10.–08.26.) + 7 Re-Queue-Entwürfe (`cadence_wait`) + 6 Pillar-Seiten · Hartes Gate + Selbstheilung aktiv (Regel 5, Report: `CADENCE-GATE-REPORT.md`)_
