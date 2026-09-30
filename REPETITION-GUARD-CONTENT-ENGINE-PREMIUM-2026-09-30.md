# 🔁 Repetition-Guard – Lücke in der Content-Engine geschlossen (Premium-Agentur-Befund)

**Datum:** 30.09.2026 · **Bezug:** Issue #456 „fix(content): prevent accidental
adjacent word repetitions" · **Auftrag:** „Bitte dauerhaft auf Premium-Level
einer Profi-Agentur beheben."

---

## 1. Ausgangslage

Issue #456 ist bereits gemergt: `scripts/repetition_guard.py` existiert
(deterministisch, idempotent, selbsttestend), heilt angrenzende Doppelwörter
wie „senken senken" außerhalb von Frontmatter/Codeblöcken, und ist verdrahtet
in:

- **Blog-Doctor** (`scripts/blog_doctor.py`, Kette Phase A-Text)
- **Blog-Health-Gate** (`scripts/blog_health_gate.py`, täglicher Bestandslauf)
- **Quality-Score** (`scripts/quality_score.py`, SSOT-Import für die
  Uniqueness-/Wiederholungs-Komponente)
- **Content-Engine v2, Phase 2** (expliziter Aufruf + Blog-Doctor `--new-only`)

Der aktuelle Content-Bestand ist sauber (`repetition_guard.py` ohne
`--fix`: 0 Funde, Exit 0) und alle im Issue genannten Validierungen laufen
grün:

```
python3 scripts/repetition_guard.py --selftest      # ✅ bestanden
python3 scripts/blog_health_gate.py --selftest       # ✅ bestanden
python3 scripts/blog_doctor.py --selftest            # ✅ bestanden (25 Wachen)
python3 -m unittest discover -s scripts/tests \
    -p "test_quality_score*.py"                      # ✅ 11 Tests, OK
git diff --check                                      # ✅ keine Whitespace-Fehler
```

## 2. Befund: die Heilung war nicht dauerhaft, weil sie nur die halbe Kette abdeckte

Der Repetition-Guard beschreibt seinen eigenen Auslöser so: *„Generated copy
occasionally contains `senken senken` after a keyword healing pass."* Genau
diese Keyword-Heilung läuft in der Content-Engine (`content-engine-v2.yml`)
**zweimal**:

1. **Phase 2 (Qualitäts-Kette)** – `keyword_optimizer.py --fix --new-only`,
   danach `repetition_guard.py --fix --new-only` **und** `blog_doctor.py
   --new-only` (der die Wache erneut enthält). ✅ abgesichert.
2. **Phase 3 (Sofort-Optimierung)** – `meta_optimizer.py --fix --ai`,
   `keyword_optimizer.py --fix --new-only` **ein zweites Mal**,
   `keyword_gate.py --fix --new-only`, `pinterest_seo_healer.py --fix`,
   `internal_linker.py --apply`, `affiliate_profi_check.py --fix`,
   `fix_cta_hygiene.py --include-drafts` — **sieben weitere
   textverändernde Heiler, ohne einen einzigen erneuten
   Repetition-Sweep**, bevor der Phase-3-Commit gepusht wird.

Das ist exakt die Fehlerklasse, die den ursprünglichen Vorfall ausgelöst
hat: eine Keyword-Injektion NACH dem letzten Repetition-Check. Bis zum
nächsten Lauf von `blog-health-daily.yml` (Bestandswache, ohne
`--new-only`) hätte ein so entstandenes Doppelwort **einen ganzen Tag lang
live** gestanden, statt vor dem eigenen Commit geheilt zu werden – kein
„dauerhaft behoben", sondern ein Netz mit einer offenen Masche genau an der
Stelle, die den Vorfall verursacht hat.

## 3. Maßnahme

`content-engine-v2.yml`, Phase 3, direkt nach der letzten
textverändernden Heilung (`fix_cta_hygiene.py --include-drafts`) und vor
dem Commit:

```yaml
echo "== Repetition-Wache nach allen Rewrite-Heilern (Issue #456) =="
python3 scripts/repetition_guard.py --selftest
python3 scripts/repetition_guard.py --fix --new-only || echo "⚠ Repetition-Guard – Funde im Log (selbstgeheilt)"
```

Damit folgt der Guard demselben, im Repo bereits etablierten Muster wie
`fix_url_hygiene.py` („URL-Hygiene nach Optimierung") und
`fix_cta_hygiene.py` („Finale CTA-Hygiene nach allen Rewrite-Heilern"):
**jeder Block textverändernder Heiler bekommt einen abschließenden,
deterministischen Sweep unmittelbar vor dem Commit**, statt sich auf den
nächsten Tageslauf zu verlassen.

## 4. Ergebnis

| Schutzebene | Vorher | Nachher |
|---|---|---|
| Neuer Artikel, Phase 2 (Geburt) | ✅ abgesichert | ✅ abgesichert |
| Neuer Artikel, Phase 3 (Meta/SEO/CTA-Nachbearbeitung) | ❌ ungeschützt bis zum nächsten Bestandslauf | ✅ Sweep vor dem Phase-3-Commit |
| Gesamter Bestand (tägliche Politur-Läufe) | ✅ `blog-health-daily.yml` | ✅ unverändert, bleibt globales Backstop-Netz |

Alle vier im Issue genannten Integrationspunkte (Content-Engine,
Blog-Health-Gate, Blog-Doctor, Quality-Score) decken jetzt lückenlos jeden
Schreibzugriff auf den Artikeltext ab – vor jedem Commit, nicht erst am
nächsten Tag.
