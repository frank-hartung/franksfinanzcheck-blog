# ✍️ CLAUDE-STILPOLITUR PREMIUM – Claude, kostenlos ohne API (25.09.2026)

**Auftrag (Frank, 25.09.2026), wörtlich:**

> „Nutze für jeden bestehenden und zukünftigen Blogartikel nach der Offline-Optimierung zusätzlich automatisch täglich **Claude** mit einem personalisierten Prompt für meinen eigenen Schreibstil auf Premium-Level einer Profi-Agentur."

**Nachtrag selben Tages (verbindlich):**

> „Claude sollte **nur ohne API** genutzt werden. Dafür sollte das **aktuell beste kostenlose Claude-Modell** gewählt werden."

**Status:** ausgerollt · **Zugang:** Puter.js (User-Pays, kostenlos, **ohne Anthropic-API**) · **Modell:** `claude-fable-5-1` (Claude Fable 5.1 – bestes kostenloses Claude-Modell, Stand 25.09.2026)

---

## Modellwahl (Auftrag: „aktuell beste kostenlose Claude-Modell“)

Recherche-Basis (25.09.2026): Der kostenlose Zugang echter Claude-Modelle läuft über Puter.js („Free, Unlimited Claude API“ – ohne Anthropic-Key, User-Pays-Gratis-Kontingent). Im dortigen Katalog steht **Claude Fable 5.1 (`claude-fable-5-1`) an der Spitze der Modellkarte** – vor Opus 5.5 und Sonnet 5. Damit ist Fable 5.1 das aktuell beste kostenlose Claude-Modell und Default der Lane.

| Stufe | Modell | Rolle |
|---|---|---|
| **Default** | `claude-fable-5-1` | bestes kostenloses Modell (Fable 5.1) |
| Fallback 1 | `claude-opus-5-5` | zweitstärkstes Gratis-Modell |
| Fallback 2 | `claude-sonnet-5` | Free-Tier-Workhorse (sparsamstes Kontingent) |

Selbsttest ST3 hält die Kette in der Frei-Liste; ST14 weist jeden Anthropic-API-Bezug in Lane + Workflows ab („nur ohne API“ ist damit maschinell verankert, nicht nur dokumentiert).

## Was gebaut wurde

| Baustein | Datei | Rolle |
|---|---|---|
| Stilprofil (SSOT) | `data/schreibstil.yaml` | Franks **eigener** Schreibstil: Haltung, Rhythmus, Tonfall, Wortwahl, Stil-Hebel – live editierbar |
| Engine | `scripts/claude_stilpolitur.py` | Personalisierter Prompt, Fingerprint-Rotation, harte Verifikationsverträge, Selbsttest (15 Fälle) |
| Puter-Brücke | `scripts/puter_chat.mjs` | Node (24+): `@heyputer/puter.js`, Streaming für volle Artikel-Länge, Modell-Fallback-Kette |
| Tages-Lauf | `.github/workflows/claude-stilpolitur.yml` | **Täglich** 04:50 UTC: Offline-Optimierung (LT+DW) → **danach** Claude → Commit als Redaktions-Bot |
| Geburts-Hook | `.github/workflows/content-engine-v2.yml` Phase 2 | Jeder **zukünftige** Artikel direkt nach grammar_check + sprachglatt (`--fix --new-only`) |
| Konfiguration | `data/ki_redaktion.yaml → stilpolitur` | Modell + Fallbacks, Budget (12/Tag), Rotation (7 Tage) |
| Alerting | `.github/workflows/alert-on-failure.yml` | „Claude-Stilpolitur (täglich)“ im Watch-List – Ausfall wird nie still |
| Tests | `scripts/tests/test_claude_stilpolitur.py` | 18 Offline-Tests: Personalisierung, Kostenlos-Vertrag, Fakten-Schutz, Rotation |
| Runbook | `docs/ANLEITUNG-CLAUDE-STILPOLITUR.md` | Nutzung, Verträge, Token-Einrichtung |

## Reihenfolge (Vertrag „nach der Offline-Optimierung“)

```
1. Offline-Optimierung (kostenlos, ohne API, 25.09.2026)
   grammar_check.py (LT1–LT4) + sprachglatt.py (DW1–DW9)
2. Claude (KOSTENLOS ohne API, personalisiert – DIESE Lane)
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

Vor **jedem** Schreiben (und vor jedem Lauf der Selbsttest, 15 eingefrorene Fälle, Exit 2 = kein Schreiben):

- Links **inkl. Ankertext**, Shortcodes, Code, URLs, HTML → byte-identisch
- Überschriften (Wortlaut + Reihenfolge) → unantastbar (Anker-Slugs, SEO)
- Zahlen/Prozente/Euro-Beträge → byte-identisch (Rechenbeispiele, Anti-Halluzination)
- Tabellen-Skelett & Trennlinien stabil, Wortzahl ≥ 90 %
- Frontmatter nie angefasst (title = Cover-Marken-Lock)
- Zweite Verifikation via `sprachkern.write_verified` vor dem Schreibvorgang

## Abdeckung & Taktung („jeden bestehenden und zukünftigen“, „täglich“)

- **Täglich** (04:50 UTC) prüft der Tages-Lauf **jeden** Artikel (43 live, Stand heute).
- Geschrieben wird nach Bedarf: `neu` · `geändert` · `auffrischen (älter als 7 Tage)` – Rotation sorgt dafür, dass **jeder** Artikel mindestens wöchentlich von Claude neu poliert wird, ohne dass die KI täglich dieselben Texte neu würfelt (Idempotenz-Vertrag des Repos).
- Budget 12 Artikel/Lauf (Cost-Guard, in `ki_redaktion.yaml` änderbar); `--force` / Workflow-Input `force` poliert sofort alles.
- **Zukünftige** Artikel holt die Content-Engine v2 im Geburtslauf mit (`--new-only`, direkt nach der Offline-Optimierung).

## Kosten-Einordnung (Auftrag „nur ohne API“)

- **Keine Anthropic-API, kein Anthropic-Account, keine Abrechnung** – Zugang ausschließlich über Puter.js (User-Pays: der eigene kostenlose Puter-Account trägt die Nutzung aus seinem monatlichen Gratis-Kontingent).
- Die Dauervorgabe „Kosten-Regel“ (08.09.2026) bleibt vollständig gewahrt: Artikel-**Generierung** gratis (`anbieter_kette_lang/news: [groq, gemini]`, `ki_redaktion.py --selftest` grün), Stil-Politur jetzt ebenfalls gratis.
- Budget-Guards (12 Artikel/Tag, 7-Tage-Rotation) schonen das Gratis-Kontingent; bei knappem Kontingent `stilpolitur.modell` auf `claude-sonnet-5` stellen (Runbook).

## Offene Baustelle (bewusst sichtbar)

- ⚠ **Repo-Secret `PUTER_AUTH_TOKEN` muss gesetzt sein** (kostenloser Puter-Account, ~2 Minuten – Anleitung im Runbook). Ohne Token bricht der Tageslauf Exit 3 **laut** ab und `alert-on-failure` meldet es – nie ein stiller Ausfall.
- Kontingent beobachten: Bei regelmäßiger Erschöpfung des Gratis-Kontingents Modell auf `claude-sonnet-5` wechseln oder Rotation strecken (`auffrischung_tage` erhöhen).

---

_Dokumentation zu Auftrag + Nachtrag vom 25.09.2026 · Ergänzt die Offline-Optimierung (docs/ANLEITUNG-SPRACHGLATT.md) um die beauftragte KI-Stil-Ebene · Details: docs/ANLEITUNG-CLAUDE-STILPOLITUR.md_
