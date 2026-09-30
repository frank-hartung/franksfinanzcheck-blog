# 🛡️ Claude-Stilpolitur dauerhaft ausfallsicher (Premium-Reparatur Issue #468)

**Datum:** 2026-09-30 · **Workflow:** `.github/workflows/claude-stilpolitur.yml` („Claude-Stilpolitur (Mo/Mi/Fr)")
**Auslöser:** Lauf [36704432305](https://github.com/frank-hartung/franksfinanzcheck-blog/actions/runs/36704432305) (30.09.2026, 04:50 UTC) – rot nach 13 s, Schritt „Voraussetzungen prüfen"
**Vorlauf:** identischer Ausfall [36414673455](https://github.com/frank-hartung/franksfinanzcheck-blog/actions/runs/36414673455) (28.09.2026)

---

## 1. Was wirklich kaputt war

Der Lauf starb im Preflight mit

> „Kostenloser Puter-Zugang ist nicht eingerichtet; es wird kein anderes Modell und kein API-Fallback verwendet."

Das Repository war **völlig in Ordnung**. Gefehlt hat ausschließlich ein **fremdes** Zugangs-Token
(`PUTER_AUTH_TOKEN`). Weil das Fehlen dieses Tokens als Repository-Defekt behandelt wurde, galt:

- kein Artikel wurde grammatikalisch oder sprachlich poliert – obwohl beide Engines **vollständig offline**
  und ohne jeden Fremdzugang arbeiten,
- nichts wurde committet, der Bestand blieb unverändert,
- jeder Mo/Mi/Fr-Lauf erzeugte einen roten Haken und ein Fehlalarm-Issue.

Eine Profi-Agentur stoppt nicht die eigene Redaktion, weil ein Zulieferer nicht ans Telefon geht.

## 2. Der dauerhafte Vertrag: zwei Lanes, getrennt bewertet

| Lane | Inhalt | Verhalten bei Störung |
|---|---|---|
| **intern** – eigener Code, *fail-closed* | Pflichtdateien, Selbsttests, `grammar_check --fix`, `sprachglatt --fix` | **rot**: Ein Defekt im eigenen Haus muss wehtun |
| **extern** – Puter/Claude, *best effort* | Token, npm-SDK, Claude-Aufruf | **grün mit gelber Warnung**: ehrliche Degradierung auf die Offline-Premium-Politur |

Diese Trennung ist keine Nachsicht, sondern Genauigkeit: Der Lauf sagt jetzt exakt, **wer** gestört hat.

## 3. Was konkret geändert wurde

| # | Änderung | Verhinderte Ausfallklasse |
|---|---|---|
| 1 | Fehlendes `PUTER_AUTH_TOKEN` → Warnung statt Abbruch, Offline-Lane läuft vollständig durch | roter Lauf ohne eigenen Defekt |
| 2 | `pip`-Installation mit 3 Versuchen + Backoff | PyPI-Transient |
| 3 | npm-SDK `@heyputer/puter.js@2.6.3` mit 3 Versuchen, danach **Degradierung** statt Abbruch (`steps.sdk.outputs.claude_ready`) | Registry-Transient, zurückgezogenes Release |
| 4 | Claude-Schritt wertet den Exit-Code **selbst** aus: 0 = ok · 2 = Sabotage-Schutz → **rot** · alles andere → gelbe Warnung | Puter-Ausfall, Netzfehler, leeres Gratis-Kontingent |
| 5 | **Wirksamkeits-Urteil** `scripts/claude_stilpolitur_wirkung.py`: Kandidaten vorhanden, aber 0 poliert und nur Fehlversuche → `wirkungslos` + Warnung „Token erneuern" | **Schein-Grün** bei abgelaufenem Token (das Skript fängt Fehlversuche selbst ab und endet mit 0) |
| 6 | Offline-Politur **nicht mehr maskiert** (`\|\| echo` entfernt, `set -Eeuo pipefail`), eigener Step-`id: offline` | stiller Absturz der eigenen Engines |
| 7 | Commit mit `!cancelled() && steps.offline.outcome == 'success'` | verworfene Offline-Arbeit, wenn die externe Lane später streikt |
| 8 | **Lauf-Bilanz** in der Job-Zusammenfassung: pro Lane eine nachprüfbare Statuszeile | „grüner Haken", der einen Claude-Lauf nur vortäuscht |

Unverändert bleibt das Mandat: **ausschließlich `claude-sonnet-5`**, **kostenlos ohne API**,
**kein Ersatzmodell**, **kein Anthropic-/Gemini-/Groq-Key**, Taktung **Mo/Mi/Fr 04:50 UTC**.

## 4. Beweis statt Behauptung

Der komplette Job wurde lokal Schritt für Schritt mit echter Ausführung durchgespielt
(Preflight → venv → SDK → Selbsttests → Offline-Politur → Claude → Commit → Bilanz):

| Szenario | Ergebnis |
|---|---|
| **Kein Token** | ✅ grün · 44 Artikel offline poliert · Commit erfolgt · Bilanz: „Claude übersprungen" |
| **Token vorhanden, Puter antwortet nicht** | ✅ grün · Offline-Politur committet · Warnung „Claude-Zusatz wirkungslos – Token erneuern" |
| **Offline-Engine stürzt ab** | 🛑 rot · **kein** Commit · Bilanz: „Offline-Engines abgestürzt" |
| **Selbsttest rot (Exit 2)** | 🛑 rot (Sabotage-Schutz, im Test eingefroren) |

## 5. Rückfall-Schutz (damit es dauerhaft bleibt)

- `scripts/tests/test_claude_stilpolitur_workflow.py` – 10 Vertragsprüfungen auf dem **geparsten** YAML:
  Degradierung, Token-Guards, Retry-Logik, Exit-2-bleibt-rot, unmaskierte Offline-Lane,
  Selbsttest-vor-Schreiben, Commit-Bedingung, Bilanz, Modell-Mandat, Mo/Mi/Fr-Cron.
- `scripts/tests/test_claude_stilpolitur_wirkung.py` – 7 Tests auf das Wirksamkeits-Urteil.
- `python3 scripts/claude_stilpolitur_wirkung.py --selftest` – 9 eingefrorene Fälle, läuft im Workflow mit.
- Gesamtsuite: `python3 -m unittest discover -s scripts/tests` → **1140 Tests grün**.

## 6. Einmalige Handarbeit (optional, 2 Minuten)

Der Claude-Zusatz läuft erst, wenn das **kostenlose** Token hinterlegt ist:

1. [puter.com](https://puter.com) → kostenloses Konto
2. Auth-Token erzeugen ([docs.puter.com](https://docs.puter.com))
3. GitHub → Settings → Secrets and variables → Actions → **`PUTER_AUTH_TOKEN`**

Bis dahin bleibt der Zeitplan grün und der Bestand auf Offline-Premium-Niveau –
ohne Kosten, ohne Ersatzmodell, ohne Fehlalarm.
