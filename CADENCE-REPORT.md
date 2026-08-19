# 📅 CADENCE-REPORT – Veröffentlichungs-Kadenz (DAUERVORGABE)

**Festgelegt:** 19.08.2026 · **Gültigkeit:** dauerhaft (keine dynamische Anpassung)
**Umsetzung:** `.github/workflows/content-engine-v2.yml` · Verbindlich auch in
`MASTER-SYSTEM-FRANKSFINANZCHECK.md` (Kapitel 4.0) und `QUALITAETS-REGELWERK.md`.

## Regelwerk

1. **Blog-Launch: 08.08.2026.** Kein Artikel trägt je ein Datum vor dem 08.08.2026.
   Der vor dem Launch datierte Alt-Bestand (36 Posts, ursprünglich 03.–07.08.2026)
   wurde am 19.08.2026 dauerhaft gelöscht – inkl. Cover-Varianten,
   Covers-Manifest, Pinterest-Pin-Queue, Content-Fingerprints und interner Links.
2. **Veröffentlichungsintervall: 3 Artikel pro Woche – montags, mittwochs, freitags.**
   - Haupt-Slot: **08:10 MESZ** (06:10 UTC)
   - Fallback-Slot 1: 16:10 MESZ · Fallback-Slot 2: 19:40 MESZ
   - Cron: `10 6 * * 1,3,5` (content-engine-v2.yml)
3. Die Frequenz ist **fix**. Der frühere, dynamische `cadence_manager.py`
   (Ramp-Logik) existiert nicht mehr – dieser Report ist die verbindliche
   Definition. Änderungen nur noch per ausdrücklichem Beschluss Franks
   (Dokumentation hier + Kapitel 4.0 im Master-System).

## Empfohlene Zeichenlänge pro Blogartikel (Dauervorgabe, same Tag festgelegt)

- **6.000–10.000 Zeichen Fließtext** (≈ 800–1.400 Wörter)
- Empirisch begründet: Bestands-Median 9.124 Zeichen bei 6,96 Zeichen/Wort
- Überwacht von `scripts/check_length.py` (`OPT_CHARS_MIN/MAX`, Env-übersteuerbar
  via `LENGTH_OPT_CHARS_MIN/MAX`); harte Gates bleiben wortbasiert

---
_Stand: 19.08.2026 · Bestand: 44 Posts (alle ≥ Launch-Datum) + 6 Pillar-Seiten_
