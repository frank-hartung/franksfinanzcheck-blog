# 📅 CADENCE-REPORT – Veröffentlichungs-Kadenz (DAUERVORGABE)

**Festgelegt:** 19.08.2026 · **Gültigkeit:** dauerhaft (keine dynamische Anpassung)
**Umsetzung:** `.github/workflows/content-engine-v2.yml` + harter Wochentags-Guard in
`scripts/engine_generate.py` · Verbindlich auch in
`MASTER-SYSTEM-FRANKSFINANZCHECK.md` (Kapitel 4.0) und `QUALITAETS-REGELWERK.md`.

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

## Empfohlene Zeichenlänge pro Blogartikel (Dauervorgabe, same Tag festgelegt)

- **6.000–10.000 Zeichen Fließtext** (≈ 800–1.400 Wörter)
- Empirisch begründet: Bestands-Median 9.124 Zeichen bei 6,96 Zeichen/Wort
- Überwacht von `scripts/check_length.py` (`OPT_CHARS_MIN/MAX`, Env-übersteuerbar
  via `LENGTH_OPT_CHARS_MIN/MAX`); harte Gates bleiben wortbasiert

---
_Stand: 19.08.2026 · Bestand: 6 Posts (2× Mo 08.10., 2× Mi 08.12., 2× Fr 08.14.) + 6 Pillar-Seiten_
