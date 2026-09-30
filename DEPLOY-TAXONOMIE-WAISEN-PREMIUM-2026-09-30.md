# Deploy-Reparatur Premium — Taxonomie-Gate blockierte GitHub Pages (#1258)

**Datum:** 2026-09-30
**Betroffener Workflow:** `Deploy auf GitHub Pages` (`.github/workflows/deploy.yml`)
**Fehlerstelle:** Schritt „Taxonomie-Gate (Tags kanonisieren – selbstheilend, VOR dem Build)"
**Status:** dauerhaft behoben (fail-closed → self-healing), Selbsttests 17/17 grün

---

## 1. Befund (Symptom)

Jeder Deploy-Lauf brach mit Exit 1 ab, bevor Hugo überhaupt bauen durfte:

```
Taxonomie-Gate (Tags kanonisieren – selbstheilend, VOR dem Build)  ✗
✗ 4 harte Funde – Taxonomie nicht sauber.
Process completed with exit code 1
```

Damit blieb die öffentliche Auslieferung stehen — der klassische „ein einziger
long-tail-Artikel legt die ganze Pipeline lahm"-Fall.

## 2. Wurzelursache (Diagnose)

`scripts/tag_governance.py --apply` normalisiert Frontmatter gegen das
kuratierte Register `data/seo/tag_register.yaml`. Unbekannte Roh-Tags werden
bewusst **nicht geraten**, sondern entfernt. Bei vier Artikeln bestand das
`tags`-Feld **ausschließlich** aus Tags, die weder Name noch Synonym im Register
waren. Nach dem Entfernen blieb kein einziger gültiger Tag übrig → harter Fund
**T5** („Artikel ohne gültigen Tag") → Exit 1 → Deploy-Stopp:

| Artikel | Roh-Tags (alle unbekannt) |
|---|---|
| `2026-09-21-tierkrankenversicherung-hund-katze-kosten` | Tierkrankenversicherung Hund/Katze, Tierarztkosten absichern, Haustier Versicherung |
| `2026-09-30-neujahrsvorsaetze-geld-8-ziele-die-2027-wirklich-klappen` | Neujahrsvorsätze Geld, Finanzielle Ziele 2027, Sparziele erreichen, Gewohnheiten ändern |
| `2026-09-30-notgroschen-aufbauen-wie-viel-reicht-wirklich` | „Notgroschen aufbauen: Wie viel reicht wirklich?" (kopierter Titel) |
| `2026-09-30-weihnachten-budget-planen-entspannt-feiern-ohne-schulden` | Weihnachten Budget planen, Weihnachten sparen, Geschenkebudget, Weihnachten ohne Schulden |

Der Selbstheiler war also für Synonyme und Zeichen zuständig, deckte aber den
**Waisen-Fall** (0 gültige Tags übrig) nicht ab — genau dort lag das Leck.

## 3. Reparatur (zwei Schichten, Premium)

### Schicht 1 — Register-Kuratierung (präzise, redaktionell)
`data/seo/tag_register.yaml`: die vier realen Themen als **Synonyme unter
bestehende, bereits tragfähige Kanon-Tags** eingetragen — kein Thin-Archiv, kein
Verstoß gegen T4 (min. 2 Artikel/Tag):

- Tierkrankenversicherung → **Versicherungen vergleichen**
- Neujahrsvorsätze / finanzielle Ziele / Geschenkebudget → **Budget planen**
- Sparziele / Weihnachten sparen / ohne Schulden → **Geld sparen im Alltag**
- Gewohnheiten ändern → **Frugalismus**
- „Notgroschen aufbauen: …" (kopierter Titel) → **Notgroschen** (explizit)

### Schicht 2 — Selbstheiler-Härtung (dauerhaftes Netz)
`scripts/tag_governance.py`:

1. **Waisen-Netz:** Bleibt beim `--apply` kein gültiger Tag übrig, füllt der
   Heiler jetzt mit derselben Auffang-Logik wie die Generierung (`tags_fuer`):
   Keywords/Titel gegen das Register spiegeln, sonst die Tags des Pillars. Ein
   einzelner Artikel kann so **nie wieder** über T5 den Deploy blockieren.
   Erfunden wird weiterhin kein Tag (fehlt ein Pillar und trifft nichts, meldet
   T5 den Fall der Redaktion — fail-closed statt Falschzuordnung).
2. **Titel-Fallback entschärft:** Beim Titel-Abgleich greifen nur noch der
   kanonische Name und **mehrwortige** Synonyme, jeweils an Wortgrenzen. Damit
   kann ein Allerweltswort-Synonym keinen wildfremden Artikel mehr
   verschlagworten. (Konkret hätte das Alt-Synonym „Wirklich" den
   Notgroschen-Artikel fälschlich mit „Versicherungen vergleichen" getaggt.)
3. **Register-Hygiene:** totes/gefährliches Synonym „Wirklich" entfernt,
   redundantes Einzelwort „Finanzieller" entfernt (der Artikel trägt bereits
   „Finanzieller Puffer" + „Notgroschen").
4. **Regressionsschutz:** drei neue Selbsttests (Waisen-Netz, Keyword/Titel-
   Vorrang, Einzelwort-Synonym-Schutz) → **17/17 grün**.

## 4. Ergebnis (verifiziert)

```
python3 scripts/tag_governance.py --selftest   → 17 bestanden, 0 fehlgeschlagen
python3 scripts/tag_governance.py --apply      → Exit 0, 22 Dateien kanonisiert
python3 scripts/tag_governance.py --check      → ✓ Taxonomie sauber (Exit 0)
zweiter --apply                                → „Nichts zu ändern" (idempotent)
```

Geheilte Tags der vier Auslöser: `Versicherungen vergleichen` ·
`Budget planen, Geld sparen im Alltag, Frugalismus` · `Notgroschen` ·
`Budget planen, Geld sparen im Alltag`. Zusätzlich hat der Lauf 18 Altartikel
von long-tail-Roh-Tags auf den Kanon zurückgeführt — die Index-Hygiene, die im
Deploy-Commit sonst hängen blieb, ist damit vollständig realisiert.

## 5. Warum das dauerhaft hält

- Die Content-Engine (`engine_generate.py`, `generate_drafts.py`) erzeugt Tags
  bereits ausschließlich über `tags_fuer()` — keine Roh-Keyword-Tags mehr.
- Der Selbstheiler kann jetzt **jeden** Waisen deterministisch versorgen, ohne je
  einen Tag zu erfinden.
- Der Titel-Fallback ist gegen Falschzuordnung durch Einzelwort-Synonyme
  gepanzert und durch einen Selbsttest gesichert.
