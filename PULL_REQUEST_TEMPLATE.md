# Fix: Content-Engine darf bei 0 Artikeln keinen stillen Success-Lauf mehr durchgehen

**Behebt:** #519 (Produktions-Wache: Content-Engine liefert nicht), #518 (Wartung · Inhaltsqualität)

## Problem

Am 2026-10-02 (Freitag, Publikationstag) ist ein kritischer Fehler aufgetreten:
- Die Content-Engine lief durch alle Phasen ohne erkennbaren Fehler (grüner Lauf)
- **Ergebnis: 0 neue Artikel veröffentlicht** (Ziel: 2–3 LIVE pro Publikationstag)
- Der Workflow hat diesen Null-Lauf nicht als kritischen Fehler erkannt
- Statt einer harten Fehlermeldung wurde das als "nichts zu tun" behandelt

## Ursache

1. **Phase 1 (Generator):** Nach dem Artikel-Generierungs-Lauf wurde nur geprüft: `if git status --short content/ | grep -q .` 
   - Wenn diese Prüfung "nichts zu tun" meldete, endete der Lauf stillschweigend
   - Es gab keine Unterscheidung zwischen "bewusst nichts erzeugt" und "Engine-Fehler"

2. **Preflight:** Der `bot_preflight.py`-Check war zu permissiv
   - Ein leerer oder erschöpfter Themenpool wurde nicht als kritisch behandelt
   - Der Workflow startete die Engine trotzdem und lieferte 0 Artikel

## Lösung

### 1. Workflow-Validierung nach Phase 1 (hard fail)
```yaml
- name: Phase 1 – Ergebnis validieren (HARD FAIL bei 0 Artikeln)
  run: |
    if git status --short content/ data/ | grep -q .; then
      echo "ARTIKEL_ERSTELLT=true" >> "$GITHUB_ENV"
      echo "✅ Phase 1 validiert: neue Content-Dateien wurden erzeugt."
    else
      echo "::error::Content-Engine erzeugte nach dem Lauf keine neuen Artikel/Entwürfe. Publikationstag ist als Fehler zu markieren."
      exit 1
    fi
```

**Wirkung:** Jetzt wird der Generator-Nulllauf sofort erkannt und der Workflow bricht mit Exit-Code 1 ab.

### 2. Preflight-Härtung (kritische Themenpool-Prüfung)
```python
if not freie:  # 0 freie Themen
    ok = False
    print("   ❌ Keine freien Themen – Content-Engine darf nicht starten.")
```

**Wirkung:** Der Preflight-Check schlägt jetzt hart fehl, wenn der Themenpool leer oder völlig erschöpft ist.

## Auswirkungen

- **Produktion:** An Publikationstagen (Mo/Mi/Fr) darf der Workflow nicht mehr mit 0 Artikeln grün enden
- **Monitoring:** Fehler werden sofort sichtbar (rote Workflow-Lauf + klare Fehlermeldung)
- **Aufwachbarkeit:** Die Production-Watch (#519) kann nun auf echten Fehlern aufgebaut werden, statt auf stillen Nullläufen

## Testing

Der Patch wurde gegen folgende Szenarien validiert:
1. ✅ Generator arbeitet normal → 1+ Artikel erzeugt → Workflow grün
2. ✅ Generator erzeugt 0 Artikel → Workflow rot (exit 1) → Alerting aktiv
3. ✅ Themenpool leer → Preflight rot (exit 1) → Workflow stoppt sofort
4. ✅ API-Keys fehlen → Preflight rot → kein Workflow-Start

## Dateien

- `.github/workflows/content-engine-v2.yml` – Phase 1 Ergebnis-Validierung hinzugefügt
- `scripts/bot_preflight.py` – Themenpool-Härtung (0 freie Themen = kritisch)

---

**Labels:** `production-critical`, `automation`, `hardening`  
**Assignee:** @frank-hartung  
**Milestones:** Production Stability  
