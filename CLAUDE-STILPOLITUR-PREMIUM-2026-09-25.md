# ✍️ CLAUDE-STILPOLITUR PREMIUM – Claude 3.5 Sonnet, personalisiert (25.09.2026)

**Auftrag (Frank, 25.09.2026), wörtlich:**

> „Nutze für jeden bestehenden und zukünftigen Blogartikel nach der Offline-Optimierung zusätzlich automatisch täglich **Claude 3.5 Sonnet** mit einem personalisierten Prompt für meinen eigenen Schreibstil auf Premium-Level einer Profi-Agentur."

**Status:** ausgerollt · **Lane:** Paid (ANTHROPIC_API_KEY) · **Modell:** `claude-3-5-sonnet-latest` (ausdrücklich 3.5 Sonnet)

---

## Was gebaut wurde

| Baustein | Datei | Rolle |
|---|---|---|
| Stilprofil (SSOT) | `data/schreibstil.yaml` | Franks **eigener** Schreibstil: Haltung, Rhythmus, Tonfall, Wortwahl, Stil-Hebel, Qualitätsziele – live editierbar |
| Engine | `scripts/claude_stilpolitur.py` | Claude-3.5-Sonnet-Politur mit personalisiertem Prompt, Fingerprint-Rotation, harten Verifikationsverträgen, Selbsttest (13 Fälle) |
| Tages-Lauf | `.github/workflows/claude-stilpolitur.yml` | **Täglich** 04:50 UTC: Offline-Optimierung (LT+DW) über alle Artikel → **danach** Claude 3.5 Sonnet → Commit als Redaktions-Bot |
| Geburts-Hook | `.github/workflows/content-engine-v2.yml` Phase 2 | Jeder **zukünftige** Artikel wird direkt nach grammar_check + sprachglatt mitpoliert (`--fix --new-only`) |
| Konfiguration | `data/ki_redaktion.yaml → stilpolitur` | Modell-Bindung, Budget (12/Tag), Rotation (7 Tage) |
| Alerting | `.github/workflows/alert-on-failure.yml` | „Claude-Stilpolitur (täglich)“ im Watch-List – Ausfall wird nie still |
| Tests | `scripts/tests/test_claude_stilpolitur.py` | 16 Offline-Tests: Personalisierung, Modell-Bindung, Fakten-Schutz, Rotation |
| Runbook | `docs/ANLEITUNG-CLAUDE-STILPOLITUR.md` | Nutzung, Verträge, Modell-Pinning |

## Reihenfolge (Vertrag „nach der Offline-Optimierung“)

```
1. Offline-Optimierung (kostenlos, ohne API, 25.09.2026)
   grammar_check.py (LT1–LT4) + sprachglatt.py (DW1–DW9)
2. Claude 3.5 Sonnet (Paid, personalisiert – DIESE Lane)
   claude_stilpolitur.py → Premium-Level einer Profi-Agentur
   in Franks eigenem Schreibstil (data/schreibstil.yaml)
3. Commit als Redaktions-Bot (main = Produktion, wie redaktions-politur)
```

## Personalisierung („mein eigener Schreibstil“)

Der System-Prompt wird aus zwei Quellen gerendert:

- **`data/schreibstil.yaml`** – Franks Stimme: „Praktiker, kein Guru“, kurze/mittlere Sätze im Wechsel, Alltagsbilder statt Abstraktion, Lieblingswörter (ehrlich, handfest, Fixkosten …), Floskel-Ersatz („In diesem Ratgeber zeige ich dir“ → „Hier zeige ich dir“), Tabu-Liste, Stil-Hebel einer Profi-Agentur, messbare Ziele (Passiv < 28 %, LIX 35–50, Absätze 2–4 Sätze).
- **`data/brand_brain.yaml`** – Marken-SSOT: Ton, Leseniveau, Autor-Avatar, Verbotsphrasen.

Fein-Tuning = YAML editieren, der Prompt liest live mit. Kein Code-Touch nötig.

## Schutzverträge (warum nichts schiefgehen kann)

Vor **jedem** Schreiben (und vor jedem Lauf der Selbsttest, 13 eingefrorene Fälle, Exit 2 = kein Schreiben):

- Links **inkl. Ankertext**, Shortcodes, Code, URLs, HTML → byte-identisch
- Überschriften (Wortlaut + Reihenfolge) → unantastbar (Anker-Slugs, SEO)
- Zahlen/Prozente/Euro-Beträge → byte-identisch (Rechenbeispiele, Anti-Halluzination)
- Tabellen-Skelett & Trennlinien stabil, Wortzahl ≥ 90 %
- Frontmatter nie angefasst (title = Cover-Marken-Lock)
- Zweite Verifikation via `sprachkern.write_verified` vor dem Schreibvorgang

## Abdeckung & Taktung („jeden bestehenden und zukünftigen“, „täglich“)

- **Täglich** (04:50 UTC) prüft der Tages-Lauf **jeden** Artikel (43 live, Stand heute).
- Geschrieben wird nach Bedarf: `neu` · `geändert` · `auffrischen (älter als 7 Tage)` – Rotation sorgt dafür, dass **jeder** Artikel mindestens wöchentlich von Claude 3.5 Sonnet neu poliert wird, ohne dass die KI täglich dieselben Texte neu würfelt (Idempotenz-Vertrag des Repos).
- Budget 12 Artikel/Lauf (Cost-Guard, in `ki_redaktion.yaml` änderbar); `--force` / Workflow-Input `force` poliert sofort alles.
- **Zukünftige** Artikel holt die Content-Engine v2 im Geburtslauf mit (`--new-only`, direkt nach der Offline-Optimierung).

## Kosten-Einordnung (Abgrenzung zur Gratis-Regel)

Die Dauervorgabe „Kosten-Regel“ (08.09.2026) gilt weiterhin für die Artikel-**Generierung** (`anbieter_kette_lang/news: [groq, gemini]` – `ki_redaktion.py --selftest` bleibt grün). Die Stil-Politur ist ein **separater, ausdrücklich beauftragter Paid-Lane** mit eigenem Schlüssel (`ANTHROPIC_API_KEY`) und eigenem Budget – die Generierung bleibt gratis.

## Offene Baustelle (bewusst sichtbar)

- ⚠ **Repo-Secret `ANTHROPIC_API_KEY` muss gesetzt sein** (Settings → Secrets and variables → Actions). Ohne Key bricht der Tageslauf Exit 3 **laut** ab („der Alarm statt des stillen Ausfalls“, C14/Alerting).
- Modell-Pinning: Falls Anthropic `claude-3-5-sonnet-latest` einstellt, `STILPOLITUR_MODEL=claude-3-5-sonnet-20241022` setzen (siehe Runbook). Der Selbsttest verhindert versehentliche Upgrades auf 4.5.

---

_Dokumentation zum Auftrag vom 25.09.2026 · Ergänzt die Offline-Optimierung (docs/ANLEITUNG-SPRACHGLATT.md) um die beauftragte KI-Stil-Ebene · Details: docs/ANLEITUNG-CLAUDE-STILPOLITUR.md_
