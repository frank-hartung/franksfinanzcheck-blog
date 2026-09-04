# 🧱 HEADING-REPORT (heading_guard.py)

**Stand:** 2026-09-04 14:34 UTC · Modus: FIX

Regeln: **H1** `<br>` in Überschriften → Leerzeichen (nur bei anker-stabilem Beweis, Auto-Fix) · **H2** `<br>` am Ende → Wegfall (anker-stabil) · **H3** sonstiges Roh-HTML → nur Meldung.

🎉 Alle Überschriften frei von `<br>`/Roh-HTML – Anker stabil, TOC sauber, Profi-Niveau.

**Letzte Heilung (Audit-Spur):** 118 Überschrift(en) am 2026-09-02 12:23 UTC – Details: `data/heading_guard_history.jsonl`.

---
_Warum: `<br>` in Überschriften zerstört TOC-Texte („Fazit:\\ Ein“), fühlt sich für Leser wie ein fehlendes Leerzeichen an und ist ein SEO-/Barrierefreiheits-Risiko. Der Guard heilt anker-stabil – externe Links (Pinterest-Pins, Backlinks) brechen nie._
