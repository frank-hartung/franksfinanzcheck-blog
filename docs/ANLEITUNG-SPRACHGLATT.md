# 🧴 ANLEITUNG – Sprachglatt & Grammatik (offline, ohne API)

**Stand:** 2026-09-25 · **Skripte:** `scripts/sprachkern.py`, `scripts/grammar_check.py`, `scripts/sprachglatt.py`
**Workflows:** `redaktions-politur.yml` (Mo 03:45 UTC), `content-engine-v2.yml` (bei jedem neuen Artikel), `seo-weekly.yml` (Bestand)

---

## Auftrag

> „Sämtliche Blogartikel dauerhaft automatisch mit DeepL Write (kostenlos ohne API nachbauen) oder LanguageTool glätten (kostenlos ohne API nachbauen) und auf Premium-Level einer Profi-Agentur beheben.“

**Klärung 25.09.2026:** DeepL Write und LanguageTool sind nur **Vorbilder für die zu emulierende Funktionalität**. Keine externen API-Aufrufe (`api.deepl.com`, `api.languagetool.org`), keine Keys, alles lokal/offline und kostenlos (DSGVO: null Datenabfluss).

---

## Was machen die beiden Engines?

### `grammar_check.py` – LanguageTool-Nachbau (Korrektur-Ebene, LT1–LT4)

| Regel | Beispiel Fehler → Fix | Schutz |
|---|---|---|
| **LT1 Partikel** | „wo mit“ → „womit“, „an Hand“ → „anhand“, „zu mindest“ → „zumindest“ | Negativ: „Ich bin da für dich“ bleibt |
| **LT2 Kollokation** | „im gegensatz“ → „im Gegensatz“, „zu hause“ → „zu Hause“, „von anfang an“ → „von Anfang an“ | Nur Fehler-Kleinschreibung wird gematcht, korrekte Form ist kein Fund |
| **LT3 Kontext** | „seid drei Jahren“ → „seit drei Jahren“, „wieder Erwarten“ → „wider Erwarten“, „vorallem“ → „vor allem“, „wahr nehmen“ → „wahrnehmen“ | Negativ-Fallen: „Ihr seid bereit“, „seid dem Kurs gefolgt“, Verb „wieder erwarten“ bleibt |
| **LT4 Typo-Kanon** | „ansonten“ → „ansonsten“, „übbrigens“ → „übrigens“, „bezeihungsweise“ → „beziehungsweise“ | Whitelist `data/grammar_whitelist.txt` schützt Marken/Fachbegriffe |

### `sprachglatt.py` – DeepL-Write-Nachbau (Glätt-Ebene, DW1–DW9 + V1)

| Regel | Beispiel Behördendeutsch → Premium | Typ |
|---|---|---|
| **DW1 Meinung** | „ist der Meinung, dass“ → „meint, dass“ | Auto-Fix |
| **DW2 Können-Hebel** | „bist in der Lage, Geld zu sparen“ → „kannst Geld sparen“ | Auto-Fix (Konjugations-Tabelle bin/bist/ist…) |
| **DW3 Möglichkeit** | „hast die Möglichkeit, zu sparen“ → „kannst sparen“ | Auto-Fix |
| **DW4 Anschluss** | „des Weiteren“ → „Außerdem“ | Auto-Fix |
| **DW5 Erwägen** | „in Betracht ziehen“ → „erwägen“ | Auto-Fix, Negativ: „in Betracht kommen“ bleibt |
| **DW6 Entscheidung** | „eine Entscheidung treffen“ → „entscheiden“ | Auto-Fix |
| **DW7 Nominalstil** | „eine Überprüfung vornehmen“ → „überprüfen“ | Auto-Fix (Kanon) |
| **DW8 Folge** | „, mit der Folge, dass“ → „, sodass“ | Auto-Fix |
| **DW9 Anwendung** | „findet Anwendung“ → „wird genutzt“ | Auto-Fix |
| **V1 Vorschläge** | „im Hinblick auf“, „hinsichtlich“, „eine Vielzahl von“ (Kasus-Falle!), „wegen dem“, „zur Verfügung stellen“, „von Bedeutung sein“, „Es ist möglich, zu“, „trotzdem + Subjekt“, „Es gilt zu beachten, dass“ | **Report-only** (nie Auto, Sinnrisiko) |

Bewusst **anderswo** (keine Doppel-Regeln, Regelwerk-Prinzip „jede Regel genau einmal“):
- Füllphrasen/Intensiv/Pleonasmus/Zahlen = `lektor_guard.py` (L2/L10/L11)
- Fest-Fehler `einzigste/daß/seid-Pronomen` = `hardcases_guard.py` (H1–H9)
- Stil-Messung (Passiv, LIX) = `stil_guard.py` (S1–S8)
- Stil-Politur auf Premium-Level (Claude 3.5 Sonnet, personalisiert, Paid-Lane 25.09.2026) = `claude_stilpolitur.py` – läuft NACH dieser Offline-Optimierung, Details in `docs/ANLEITUNG-CLAUDE-STILPOLITUR.md`

---

## Sicherheitsverträge (beide Engines)

- **Schutzzonen:** Code-Blöcke, Inline-Code, Markdown-Links/Bilder inkl. Linkziel, Hugo-Shortcodes, URLs, HTML-Tags/Kommentare werden maskiert und **nie verändert** (Link-Texte sind Marken-/Anker-Verträge).
- **Frontmatter:** `title` wird **nie geschrieben** (Cover-Marken-Lock, `check_covers`), `description` wird mitgeheilt, `tags/keywords` bleiben unangetastet.
- **Verifikation vor Schreiben:** Link-/Shortcode-/Überschriften-Zahl konstant, Wortzahl ≥ 90 % – sonst wird Datei **nicht** geschrieben.
- **Selbsttest vor jedem Schreibvorgang:** Abweichung = Exit 2, kein Schreiben (Sabotage-Schutz).
- **Identity-Falle:** Wenn `fix == found` (korrekter Text), zählt es nicht als Fund – Sicherheitsnetz gegen Regex mit `re.I`.
- **Idempotenz:** Zweiter Lauf ändert nichts mehr.

---

## Nutzung

```bash
# Prüfung (Report)
python3 scripts/grammar_check.py
python3 scripts/sprachglatt.py

# Heilen (sichere Fälle)
python3 scripts/grammar_check.py --fix
python3 scripts/sprachglatt.py --fix

# Nur heutige Artikel (Content-Engine)
python3 scripts/grammar_check.py --fix --new-only
python3 scripts/sprachglatt.py --fix --new-only

# Einzelner Artikel
python3 scripts/grammar_check.py --file content/posts/2026-09-02-.../index.md --fix

# Selbsttest (Sabotage-Schutz)
python3 scripts/grammar_check.py --selftest   # 11 Fälle
python3 scripts/sprachglatt.py --selftest     # 12 Fälle
```

**Ausgabe:**
- `GRAMMATIK-REPORT.md` + `.grammar_report.json`
- `SPRACHGLATT-REPORT.md` + `.sprachglatt_report.json`
- `data/sprachglatt_history.jsonl` (Verlauf, versioniert)

Exit-Codes: 0 = sauber/gelaufen, 1 = offene Funde (nur `--strict`), 2 = Selbsttest rot.

---

## Automation

| Workflow | Wann | Was |
|---|---|---|
| `content-engine-v2.yml` Phase 2 | Bei jedem neuen Artikel | `--selftest` implizit + `--fix --new-only` für beide Engines (nach Spellcheck, vor Casing) |
| `redaktions-politur.yml` | Mo 03:45 UTC + manuell | `--selftest` hart, dann `--fix` über **alle** Artikel, Commit als `Redaktions-Bot` via `git_sync.sh --push-only` |
| `seo-weekly.yml` | Mi 10:00 MESZ | Bestands-Audit + `--fix` für beide Engines (zusätzliche Absicherung) |

---

## Warum offline?

- **Kostenlos:** Keine DeepL-/LT-Abos, keine Token-Limits.
- **DSGVO:** Null Datenabfluss – Artikel verlassen nie den Runner.
- **Deterministisch:** Gleiche Eingabe → gleiche Ausgabe, kein KI-Halluzinieren, keine Sinnänderung.
- **Schnell:** Kein Netz-Roundtrip, keine Rate-Limits, < 2 s für 60 Artikel.

---

## Erweiterung

Neue Regel hinzufügen:
1. In `grammar_check.py` (LT) oder `sprachglatt.py` (DW) als `(ID, Regex, Fixer, Label)` eintragen.
2. **Einmaligkeit prüfen:** Steht sie schon in `lektor_guard.py`, `hardcases_guard.py`, `stil_guard.py`? Dann dort lassen!
3. Selbsttest-Fall hinzufügen (positiv + negativ) in `run_selftest()`.
4. In `scripts/tests/test_sprach_politur.py` Regressionstest ergänzen.
5. `docs/QUALITAETS-REGELWERK.md` aktualisieren.
6. `python3 scripts/... --selftest` muss grün sein, sonst Exit 2.

---

## Siehe auch

- `docs/QUALITAETS-REGELWERK.md` – Regel-Tabelle (LT1–LT4, DW1–DW9, V1)
- `scripts/sprachkern.py` – Gemeinsamer Kern (Schutzzonen, Verifikation)
- `scripts/tests/test_sprach_politur.py` – 23 Regressionstests (Offline-Vertrag, Idempotenz, Schutzmasken)
