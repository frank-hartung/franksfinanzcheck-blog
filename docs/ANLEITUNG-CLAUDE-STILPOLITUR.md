# ✍️ ANLEITUNG – Claude-Stilpolitur (Claude, kostenlos ohne API, personalisiert)

**Stand:** 2026-09-25 · **Skripte:** `scripts/claude_stilpolitur.py` + `scripts/puter_chat.mjs`
**Stilprofil:** `data/schreibstil.yaml` (Franks eigener Schreibstil) + `data/brand_brain.yaml` (Marken-Stimme)
**Workflows:** `claude-stilpolitur.yml` (täglich 04:50 UTC), `content-engine-v2.yml` Phase 2 (bei jedem neuen Artikel)

---

## Auftrag

> „Nutze für jeden bestehenden und zukünftigen Blogartikel nach der Offline-Optimierung zusätzlich automatisch täglich **Claude** mit einem personalisierten Prompt für meinen eigenen Schreibstil auf Premium-Level einer Profi-Agentur."
> — Frank, 25.09.2026

**Nachtrag selben Tages (verbindlich):**

> „Claude sollte **nur ohne API** genutzt werden. Dafür sollte das **aktuell beste kostenlose Claude-Modell** gewählt werden."

**Reihenfolge ist Vertrag:** Erst die Offline-Optimierung (grammar_check + sprachglatt, kostenlos, ohne API), **danach** die Claude-Stil-Politur. Die Lane glänzt Sprachbild, Klang und Prägnanz – sie arbeitet nie an Fakten.

---

## Zugang: kostenlos, ohne API (Puter.js User-Pays)

Claude läuft **nicht** über die bezahlte Anthropic-API, sondern über **Puter.js** („Free, Unlimited Claude API“, User-Pays-Modell – offizieller Node/CI-Zugang):

| | |
|---|---|
| **Keine Anthropic-API** | kein Anthropic-Account, kein Modell-Key, keine Abrechnung – der Selbsttest ST14 weist jeden Anthropic-Bezug in Lane + Workflows ab |
| **Auth** | nur `PUTER_AUTH_TOKEN` – **kostenloser** Puter-Account mit monatlichem Gratis-Kontingent |
| **Brücke** | `scripts/puter_chat.mjs` (`@heyputer/puter.js`, Node.js 24+, transient installiert) |
| **Kosten-Regel des Repos** | voll erfüllt – die Lane ist so gratis wie die Offline-Optimierung davor |

> **Warum Puter und nicht duck.ai/Brave Leo/claude.ai-Scraping?** Die Chat-Wrapper von DuckDuckGo & Co. sind offiziell nicht freigegeben (Umgehung, jederzeit tot), modellmäßig nur Haiku-Klasse und für 15.000-Zeichen-Artikel ungeeignet. Puter ist der dokumentierte, offizielle Gratis-Weg an die echten Claude-Modelle – und erlaubt die Wahl des **besten** freien Modells.

**Einrichtung (einmalig, ~2 Minuten):**
1. [puter.com](https://puter.com) → kostenloses Konto anlegen
2. Auth-Token erzeugen (Anleitung: [docs.puter.com](https://docs.puter.com) → Node.js/Auth-Token)
3. GitHub → Settings → Secrets and variables → Actions → **`PUTER_AUTH_TOKEN`**

Ohne Token bricht der Tageslauf bewusst **laut** ab (Exit 3) – `alert-on-failure.yml` meldet es als Issue („Claude-Stilpolitur (täglich)“ ist im Watch-List). Nie ein stiller Ausfall.

---

## Modell: das aktuell beste kostenlose Claude-Modell

**Auswahl 25.09.2026 (Auftrag „aktuell beste kostenlose Claude-Modell“):**

| Stufe | Modell | Warum |
|---|---|---|
| **Default** | **`claude-fable-5-1`** (Claude Fable 5.1) | Spitze der kostenlosen Modellkarte (Puter-Katalog „Free, Unlimited Claude API“) |
| Fallback 1 | `claude-opus-5-5` | nächststärkeres Gratis-Modell |
| Fallback 2 | `claude-sonnet-5` | Free-Tier-Workhorse, sparsamstes Kontingent |

SSOT: `data/ki_redaktion.yaml → stilpolitur.modell` (+ `modell_fallback`). Override: `STILPOLITUR_MODEL`. Der Selbsttest (ST3) hält die Kette in der **Frei-Liste** des Puter-Katalogs – ein versehentlicher Griff in ein bezahltes Modell oder in die Anthropic-API wird damit abgewiesen.

> **Kontingent-Tipp:** Läuft das monatliche Gratis-Kontingent des Puter-Accounts regelmäßig leer, in `stilpolitur.modell` auf `claude-sonnet-5` wechseln (sparsamer, weiterhin Premium-tauglich).

---

## Was macht die Lane?

`claude_stilpolitur.py` schickt jeden Artikel an Claude mit einem **personalisierten System-Prompt**:

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

Zusätzlich greift die Repo-weite Zweite-Verifikation `sprachkern.write_verified` vor jedem Schreibvorgang, und der **Selbsttest (15 eingefrorene Fälle)** läuft vor jedem Lauf – Abweichung = Exit 2, kein Schreiben.

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

---

## Nutzung

```bash
# Report (welche Artikel wären dran? – offline, ohne API, ohne Token)
python3 scripts/claude_stilpolitur.py

# Polieren (braucht PUTER_AUTH_TOKEN – kostenlos, KEIN Anthropic-Key)
export PUTER_AUTH_TOKEN=…
npm install --no-save @heyputer/puter.js    # einmalig lokal (Node 24+)
python3 scripts/claude_stilpolitur.py --fix              # Rotation + Budget
python3 scripts/claude_stilpolitur.py --fix --new-only   # nur heutige Artikel
python3 scripts/claude_stilpolitur.py --fix --force      # alles, egal Fingerprint
python3 scripts/claude_stilpolitur.py --fix --file content/posts/2026-09-25-…/index.md
python3 scripts/claude_stilpolitur.py --fix --dry-run    # Trockenlauf (prüft, schreibt nie)

# Sabotage-Schutz (offline)
python3 scripts/claude_stilpolitur.py --selftest         # 15 eingefrorene Fälle
```

**Ausgabe:**
- `CLAUDE-STILPOLITUR-REPORT.md` + `.claude_stilpolitur_report.json` (gitignored)
- `data/claude_stil_history.jsonl` (Verlauf, versioniert)
- `data/claude_stil_state.json` (Fingerprint-State, versioniert)

Exit-Codes: `0` = sauber/gelaufen · `1` = offene Kandidaten (nur `--strict`) · `2` = Selbsttest rot · `3` = `--fix` ohne `PUTER_AUTH_TOKEN`.

---

## Automation

| Workflow | Wann | Was |
|---|---|---|
| `content-engine-v2.yml` Phase 2 | Bei jedem neuen Artikel | `--fix --new-only` direkt **nach** grammar_check + sprachglatt (Geburts-Politur) |
| `claude-stilpolitur.yml` | **Täglich** 04:50 UTC (06:50 MESZ) + manuell | Offline-Optimierung über alle Artikel, **danach** Claude (`--fix`), Commit als `Redaktions-Bot` |
| `claude-stilpolitur.yml` (Dispatch) | Nach Bedarf | Inputs `force` (alle neu) + `limit` (Budget) |

Beide Workflows stellen Node 24 (`actions/setup-node`) und `@heyputer/puter.js` (transient, `--no-save`) bereit.
