# 🔗 DRAFT-LINK-REPORT (draft_link_healer.py)

**Stand:** 2026-09-05 09:01 UTC · Modus: FIX

## Gemeldet: Ziel gerade nicht im Build (11)

Kein Eingriff nötig – der Render-Guard `layouts/_default/_markup/render-link.html` gibt diese Links als Klartext aus (kein 404), und sie leben automatisch wieder auf, sobald das Ziel zurück im Build ist. Entlinken würde nur kuratierte Listen dauerhaft ausdünnen.

- `2026-08-10-dsl-wechselbonus-sichern` → `2026-09-04-finanzielle-freiheit-erreichen-denke-dich-reich` (Draft (Kadenz-Re-Queue))
- `2026-08-10-sicher-heizen-so-schuetzt-dich-eine-preisgarantie-gas` → `2026-09-04-finanzielle-freiheit-erreichen-denke-dich-reich` (Draft (Kadenz-Re-Queue))
- `2026-08-12-preisgarantie-gas-so-sicherst-du-dir-guenstige-tarife-fuer-2026` → `2026-09-04-finanzielle-freiheit-erreichen-denke-dich-reich` (Draft (Kadenz-Re-Queue))
- `2026-08-14-sparen-im-herbst-die-besten-spartipps-fuer-die-goldene-jahreszeit` → `2026-09-04-finanzielle-freiheit-erreichen-denke-dich-reich` (Draft (Kadenz-Re-Queue))
- `2026-08-16-strom-sparen-im-haushalt-die-besten-tipps-fuer-den-herbst` → `2026-09-04-finanzielle-freiheit-erreichen-denke-dich-reich` (Draft (Kadenz-Re-Queue))
- `2026-08-17-privathaftpflicht-warum-sie-so-wichtig-ist-und-was-sie-kostet` → `2026-09-04-finanzielle-freiheit-erreichen-denke-dich-reich` (Draft (Kadenz-Re-Queue))
- `2026-08-17-privathaftpflicht-warum-sie-so-wichtig-ist-und-was-sie-kostet` → `2026-09-04-finanzielle-freiheit-erreichen-denke-dich-reich` (Draft (Kadenz-Re-Queue))
- `2026-08-18-wohngebaeudeversicherung-vergleich-worauf-du-achten-musst` → `2026-09-04-finanzielle-freiheit-erreichen-denke-dich-reich` (Draft (Kadenz-Re-Queue))
- `2026-08-24-mehr-freiheit-durch-verzicht-clevere-frugalismus-tipps` → `2026-09-04-finanzielle-freiheit-erreichen-denke-dich-reich` (Draft (Kadenz-Re-Queue))
- `2026-08-24-mehr-freiheit-durch-verzicht-clevere-frugalismus-tipps` → `2026-09-04-finanzielle-freiheit-erreichen-denke-dich-reich` (Draft (Kadenz-Re-Queue))
- `2026-09-02-september-roadtrip-clevere-wege-zum-mietwagen-schnaeppchen` → `2026-09-04-finanzielle-freiheit-erreichen-denke-dich-reich` (Draft (Kadenz-Re-Queue))

---
_Heiler: Ankertext bleibt 1:1 erhalten (kein Content-Verlust). Läuft in der Deploy-Gate-Kette vor dem Hugo-Build, in der Content-Engine vor jedem Slot und im Blog-Gesundheits-Check._