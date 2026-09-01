# 🔗 DRAFT-LINK-REPORT (draft_link_healer.py)

**Stand:** 2026-09-01 20:17 UTC · Modus: FIX

## Gemeldet: Ziel gerade nicht im Build (1)

Kein Eingriff nötig – der Render-Guard `layouts/_default/_markup/render-link.html` gibt diese Links als Klartext aus (kein 404), und sie leben automatisch wieder auf, sobald das Ziel zurück im Build ist. Entlinken würde nur kuratierte Listen dauerhaft ausdünnen.

- `pillar/internet-dsl/index.md` → `2026-08-26-handytarif-vergleichen-2026-guenstige-tarife` (Draft (Kadenz-Re-Queue))

---
_Heiler: Ankertext bleibt 1:1 erhalten (kein Content-Verlust). Läuft in der Deploy-Gate-Kette vor dem Hugo-Build, in der Content-Engine vor jedem Slot und im Blog-Gesundheits-Check._