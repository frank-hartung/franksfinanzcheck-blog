# 📉 Content-Decay-Radar (Chefredakteur-View)
**Stand:** 2026-09-01 · **Auftrag:** Frische-Steuerung für YMYL-/Affiliate-Content

- 🔴 **STALE** (sofort aktualisieren): **0**
- 🟠 **DECAYING** (in den nächsten Wochen): **0**
- 🟡 **WATCH** (im Auge behalten): **0**
- 🟢 **FRESH** (ok): **24**

---

## 🔴 STALE – Refresh-Queue (priorisiert)
_Keine_


## 🟠 DECAYING – demnächst aktualisieren
_Keine_


## 🟡 WATCH
_Keine_


---

### Nächste Schritte (Chefredakteur)

1. **Stichtag-Artikel zuerst:** Kfz (30.11.), Gas/Strom (Preisgarantie, Heizsaison),
   DSL/Handy (Jahreswechsel) – hier veraltet Inhalt zuerst, und sie sind die
   größten Affiliate-Hebel.
2. **`lastmod` ehrlich setzen:** `scripts/set_lastmod.py --git-changed` nach jedem Update.
3. **Refresh vs. Neuschreiben:** Bei >30 % Textabdeckung (Duplikat-Gefahr) lieber den
   bestehenden Artikel aktualisieren als einen neuen bauen (Google bevorzugt gepflegte
   E-A-T-Quellen).
4. **Datenpflege:** `data/decay_queue.json` wird von Engine/Autoren als Prioritätsliste gelesen.

_Automatisch erzeugt von `scripts/decay_radar.py` am 2026-09-01._
