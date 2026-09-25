# ✍️ CLAUDE-STILPOLITUR PREMIUM – NUR claude-sonnet-5, Auffrischung Mo/Mi/Fr (25.09.2026)

**Auftrag (Frank, 25.09.2026), wörtlich:**

> „Nutze für jeden bestehenden und zukünftigen Blogartikel nach der Offline-Optimierung zusätzlich automatisch täglich **Claude** mit einem personalisierten Prompt für meinen eigenen Schreibstil auf Premium-Level einer Profi-Agentur."

**Nachtrag selben Tages (verbindlich):**

> „Claude sollte **nur ohne API** genutzt werden. Dafür sollte das **aktuell beste kostenlose Claude-Modell** gewählt werden."

**Nachtrag 2 selben Tages (verbindlich, präzisiert das Modell):**

> „Bitte puter.com so einrichten, dass nur das Claude-Modell `claude-sonnet-5` verwendet wird und die `auffrischung_tage` nur Montag, Mittwoch und Freitag."

**Status:** ausgerollt · **Zugang:** Puter.js (User-Pays, kostenlos, **ohne Anthropic-API**) · **Modell:** **AUSCHLIESSLICH `claude-sonnet-5`** (kein Fallback, Stand 25.09.2026) · **Auffrischung:** **nur Mo/Mi/Fr**

---

## Modellwahl (verbindlich): AUSCHLIESSLICH `claude-sonnet-5`

Zugang: Puter.js („Free, Unlimited Claude API“ – ohne Anthropic-Key, User-Pays-Gratis-Kontingent). Modell-Mandat (Nachtrag 2, verbindlich): **nur `claude-sonnet-5`** – und nur dieses.

| | |
|---|---|
| **Modell** | **`claude-sonnet-5`** – fest verdrahtet in Config + Brücke |
| Fallback | **keiner** – `modell_fallback: []`, kein anderes Modell wird angesprochen |
| Verankerung | Selbsttest **ST3** pinnt die Kette exakt `["claude-sonnet-5"]` (fail-closed); bewusst **kein** Env-Override |
| Gratis-Regel | Weiterhin erfüllt: `claude-sonnet-5` liegt in der Puter-Frei-Liste, Kosten 0 € |

ST14 weist jeden Anthropic-API-Bezug in Lane + Workflows ab („nur ohne API“ ist maschinell verankert, nicht nur dokumentiert).

## Taktung (verbindlich): Auffrischung NUR Mo/Mi/Fr

| | |
|---|---|
| **Wochentage** | **`auffrischung_tage: [mo, mi, fr]`** – nur Montag, Mittwoch, Freitag |
| Rotation | `auffrischung_alter_tage: 7` – unveränderte Artikel ab 7 Tagen wieder dran |
| Doppel-Gate | Wochentag-Sperre zusätzlich im Skript (ST16): an anderen Tagen schreibt `--fix` nichts – `--force` hebt beides auf |

## Was gebaut wurde

| Baustein | Datei | Rolle |
|---|---|---|
| Stilprofil (SSOT) | `data/schreibstil.yaml` | Franks **eigener** Schreibstil: Haltung, Rhythmus, Tonfall, Wortwahl, Stil-Hebel – live editierbar |
| Engine | `scripts/claude_stilpolitur.py` | Personalisierter Prompt, Fingerprint-Rotation, harte Verifikationsverträge, Selbsttest (16 Fälle) |
| Puter-Brücke | `scripts/puter_chat.mjs` | Node (24+): `@heyputer/puter.js`, Streaming für volle Artikel-Länge, fest auf `claude-sonnet-5` |
| Tages-Lauf | `.github/workflows/claude-stilpolitur.yml` | **Mo/Mi/Fr** 04:50 UTC: Offline-Optimierung (LT+DW) → **danach** Claude → Commit als Redaktions-Bot |
| Geburts-Hook | `.github/workflows/content-engine-v2.yml` Phase 2 | Jeder **zukünftige** Artikel direkt nach grammar_check + sprachglatt (`--fix --new-only`) |
| Konfiguration | `data/ki_redaktion.yaml → stilpolitur` | `claude-sonnet-5` (ohne Fallback), `auffrischung_tage: [mo, mi, fr]`, Budget (12/Lauf), Rotation (7 Tage) |
| Alerting | `.github/workflows/alert-on-failure.yml` | „Claude-Stilpolitur (Mo/Mi/Fr)“ im Watch-List – Ausfall wird nie still |
| Tests | `scripts/tests/test_claude_stilpolitur.py` | 23 Offline-Tests: Personalisierung, Kostenlos-Vertrag, Fakten-Schutz, Rotation |
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

Vor **jedem** Schreiben (und vor jedem Lauf der Selbsttest, 16 eingefrorene Fälle, Exit 2 = kein Schreiben):

- Links **inkl. Ankertext**, Shortcodes, Code, URLs, HTML → byte-identisch
- Überschriften (Wortlaut + Reihenfolge) → unantastbar (Anker-Slugs, SEO)
- Zahlen/Prozente/Euro-Beträge → byte-identisch (Rechenbeispiele, Anti-Halluzination)
- Tabellen-Skelett & Trennlinien stabil, Wortzahl ≥ 90 %
- Frontmatter nie angefasst (title = Cover-Marken-Lock)
- Zweite Verifikation via `sprachkern.write_verified` vor dem Schreibvorgang

## Abdeckung & Taktung („jeden bestehenden und zukünftigen“, Auffrischung Mo/Mi/Fr)

- **Mo/Mi/Fr** (04:50 UTC) prüft der Tages-Lauf **jeden** Artikel (43 live, Stand heute); an anderen Tagen bleibt `--fix` lautlos stehen (Gate auch im Skript).
- Geschrieben wird nach Bedarf: `neu` · `geändert` · `auffrischen (älter als `auffrischung_alter_tage`)` – Rotation sorgt dafür, dass **jeder** Artikel mindestens alle 7 Tage wieder poliert wird, ohne dass die KI dieselben Texte neu würfelt (Idempotenz-Vertrag des Repos).
- Budget 12 Artikel/Lauf (Cost-Guard, in `ki_redaktion.yaml` änderbar); `--force` / Workflow-Input `force` poliert sofort alles – egal Fingerprint und Wochentag.
- **Zukünftige** Artikel holt die Content-Engine v2 im Geburtslauf mit (`--new-only`, direkt nach der Offline-Optimierung).

## Kosten-Einordnung (Auftrag „nur ohne API“)

- **Keine Anthropic-API, kein Anthropic-Account, keine Abrechnung** – Zugang ausschließlich über Puter.js (User-Pays: der eigene kostenlose Puter-Account trägt die Nutzung aus seinem monatlichen Gratis-Kontingent).
- Die Dauervorgabe „Kosten-Regel“ (08.09.2026) bleibt vollständig gewahrt: Artikel-**Generierung** gratis (`anbieter_kette_lang/news: [groq, gemini]`, `ki_redaktion.py --selftest` grün), Stil-Politur jetzt ebenfalls gratis.
- Budget-Guards (`max_artikel_pro_tag: 12`, `auffrischung_alter_tage: 7`, Auffrischung nur Mo/Mi/Fr) schonen das Gratis-Kontingent; bei Bedarf `auffrischung_alter_tage` strecken oder Budget senken (Runbook).

## Offene Baustelle (bewusst sichtbar)

- ⚠ **Repo-Secret `PUTER_AUTH_TOKEN` muss gesetzt sein** (kostenloser Puter-Account, ~2 Minuten – Anleitung im Runbook). Ohne Token bricht der Tageslauf Exit 3 **laut** ab und `alert-on-failure` meldet es – nie ein stiller Ausfall.
- Kontingent beobachten: Bei regelmäßiger Erschöpfung des Gratis-Kontingents Rotation strecken (`auffrischung_alter_tage` erhöhen) oder Budget senken (`max_artikel_pro_tag`).

---

_Dokumentation zu Auftrag + Nachträgen vom 25.09.2026 (Modell-Mandat `claude-sonnet-5`, Auffrischung Mo/Mi/Fr) · Ergänzt die Offline-Optimierung (docs/ANLEITUNG-SPRACHGLATT.md) um die beauftragte KI-Stil-Ebene · Details: docs/ANLEITUNG-CLAUDE-STILPOLITUR.md_
