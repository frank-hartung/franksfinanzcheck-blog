# ✍️ ANLEITUNG – Claude-Stilpolitur (Claude 3.5 Sonnet, personalisiert)

**Stand:** 2026-09-25 · **Skripte:** `scripts/claude_stilpolitur.py`
**Stilprofil:** `data/schreibstil.yaml` (Franks eigener Schreibstil) + `data/brand_brain.yaml` (Marken-Stimme)
**Workflows:** `claude-stilpolitur.yml` (täglich 04:50 UTC), `content-engine-v2.yml` Phase 2 (bei jedem neuen Artikel)

---

## Auftrag

> „Nutze für jeden bestehenden und zukünftigen Blogartikel nach der Offline-Optimierung zusätzlich automatisch täglich **Claude 3.5 Sonnet** mit einem personalisierten Prompt für meinen eigenen Schreibstil auf Premium-Level einer Profi-Agentur."
> — Frank, 25.09.2026

**Reihenfolge ist Vertrag:** Erst die Offline-Optimierung (grammar_check + sprachglatt, kostenlos, ohne API), **danach** die Claude-Stil-Politur. Die Lane glänzt Sprachbild, Klang und Prägnanz – sie arbeitet nie an Fakten.

---

## Was macht die Lane?

`claude_stilpolitur.py` schickt jeden Artikel an **Claude 3.5 Sonnet** (`claude-3-5-sonnet-latest`, bewusst *nicht* der Sonnet-4.5-Default) mit einem **personalisierten System-Prompt**:

| Prompt-Baustein | Quelle | Inhalt |
|---|---|---|
| Franks Schreibstil | `data/schreibstil.yaml` | Haltung, Satzrhythmus, Tonfall, Wortwahl, Stil-Hebel, Qualitätsziele |
| Marken-Stimme | `data/brand_brain.yaml` | Ton, Leseniveau, Autor-Avatar, Verbotsphrasen |
| Premium-Auftrag | eingebaut | Verlagsniveau (Capital/WiWo/ZEIT), Profi-Agentur-Politur |
| Harte Regeln | eingebaut | Fakten/Schutzzonen/Überschriften byte-identisch, Tabu-Formulierungen |

**Fein-Tuning des Stils:** einfach `data/schreibstil.yaml` editieren (Lieblingswörter, Ersatzformulierungen, Hebel) – der Prompt liest live mit. Kein Neubau nötig.

---

## Sicherheitsverträge (Verifikation VOR dem Schreiben)

Eine KI-Antwort wird **nie** blind übernommen. Verworfen wird jede Antwort, die …

- **Link-Ziele ODER Ankertexte** verändert (byte-identischer Multiset-Vergleich)
- **Shortcodes, Code-Blöcke, URLs, HTML** anfasst (Schutzzonen wie `sprachkern.py`)
- **Überschriften** ändert (Wortlaut + Reihenfolge – Anker-Slugs & SEO)
- **Zahlen, Prozente, Euro-Beträge** ändert (Fakten & Rechenbeispiele, Anti-Halluzination)
- das **Tabellen-Skelett** oder die Trennlinien-Anzahl ändert
- unter **90 % Wortzahl** fällt
- **Frontmatter** mitliefert (title = Cover-Marken-Lock – wird nie geschrieben)

Zusätzlich greift die Repo-weite Zweite-Verifikation `sprachkern.write_verified` vor jedem Schreibvorgang, und der **Selbsttest (13 eingefrorene Fälle)** läuft vor jedem Lauf – Abweichung = Exit 2, kein Schreiben.

---

## Verbrauch & Rotation (Cost-Guard)

Jeder Lauf **prüft** jeden Artikel, **schreibt** aber nur bei Bedarf (Fingerprint in `data/claude_stil_state.json`):

| Grund | Wann |
|---|---|
| `neu` | Artikel noch nie poliert |
| `geändert` | Body hat sich seit dem letzten Lauf verändert |
| `auffrischen (Nd)` | letzter Claude-Lauf älter als `auffrischung_tage` (Default **7**) |
| `offen (verworfen)` | letzte Antwort fiel durch die Verifikation – nächster Lauf versucht es erneut |

Budget: `max_artikel_pro_tag` (Default **12**) – der Rest wartet auf die Rotation, jeder Artikel ist spätestens nach `auffrischung_tage` wieder dran. `--force` (oder Workflow-Input `force`) poliert alles unabhängig vom Fingerprint.

**Kostenhinweis:** Paid-Lane (ANTHROPIC_API_KEY). Ausdrückliche Dauervorgabe – die Gratis-Regel der Artikel-**Generierung** (`anbieter_kette_*` in `data/ki_redaktion.yaml`) bleibt unangetastet.

---

## Nutzung

```bash
# Report (welche Artikel wären dran? – offline, ohne API)
python3 scripts/claude_stilpolitur.py

# Polieren (braucht ANTHROPIC_API_KEY)
export ANTHROPIC_API_KEY=…
python3 scripts/claude_stilpolitur.py --fix              # Rotation + Budget
python3 scripts/claude_stilpolitur.py --fix --new-only   # nur heutige Artikel
python3 scripts/claude_stilpolitur.py --fix --force      # alles, egal Fingerprint
python3 scripts/claude_stilpolitur.py --fix --file content/posts/2026-09-25-…/index.md
python3 scripts/claude_stilpolitur.py --fix --dry-run    # Trockenlauf (prüft, schreibt nie)

# Sabotage-Schutz (offline)
python3 scripts/claude_stilpolitur.py --selftest         # 13 eingefrorene Fälle
```

**Ausgabe:**
- `CLAUDE-STILPOLITUR-REPORT.md` + `.claude_stilpolitur_report.json` (gitignored)
- `data/claude_stil_history.jsonl` (Verlauf, versioniert)
- `data/claude_stil_state.json` (Fingerprint-State, versioniert)

Exit-Codes: `0` = sauber/gelaufen · `1` = offene Kandidaten (nur `--strict`) · `2` = Selbsttest rot · `3` = `--fix` ohne `ANTHROPIC_API_KEY`.

---

## Automation

| Workflow | Wann | Was |
|---|---|---|
| `content-engine-v2.yml` Phase 2 | Bei jedem neuen Artikel | `--fix --new-only` direkt **nach** grammar_check + sprachglatt (Geburts-Politur) |
| `claude-stilpolitur.yml` | **Täglich** 04:50 UTC (06:50 MESZ) + manuell | Offline-Optimierung über alle Artikel, **danach** Claude 3.5 Sonnet (`--fix`), Commit als `Redaktions-Bot` |
| `claude-stilpolitur.yml` (Dispatch) | Nach Bedarf | Inputs `force` (alle neu) + `limit` (Budget) |

**Voraussetzung:** Repo-Secret `ANTHROPIC_API_KEY` (Settings → Secrets and variables → Actions). Fehlt der Key, bricht der Tageslauf **laut** ab (Exit 3) – `alert-on-failure.yml` meldet es als Issue („Claude-Stilpolitur (täglich)“ ist im Watch-List).

---

## Modell-Pinning (Claude 3.5 Sonnet)

Default: `claude-3-5-sonnet-latest` (SSOT: `data/ki_redaktion.yaml → stilpolitur.modell`). Falls Anthropic das `-latest`-Alias einstellt, fixe Datums-Version setzen – per Env `STILPOLITUR_MODEL=claude-3-5-sonnet-20241022` oder direkt in `stilpolitur.modell`. Der Selbsttest (ST3) hart auf „Modell-ID beginnt mit `claude-3-5-sonnet`“ – ein versehentliches Upgrade auf 4.5 wird dadurch verhindert.
