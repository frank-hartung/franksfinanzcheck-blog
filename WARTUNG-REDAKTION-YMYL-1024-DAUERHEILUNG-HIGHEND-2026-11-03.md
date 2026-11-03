# Dauerheilung #1024 – Redaktionelle YMYL-Prüfqueue (`belegketten_wache.py`)

- **Vorgang:** GitHub-Issue `#1024` (`Redaktionelle YMYL-Prüfqueue`, Label `redaktionelle-pruefung`)
- **Auslösender Lauf:** `41454120377` (`run_number: 21`, `2026-11-02T13:34:17Z`, Branch `main` @ `519a882c`)
- **Workflow / Jobs:** `.github/workflows/redaktionelle-ymyl-pruefung.yml` (`pruefung` + `belegketten`)
- **Datum der Dauerheilung:** `2026-11-03`

---

## 1. Forensischer Befund (Run `41454120377`)

Im Ticket `#1024` waren sämtliche **10/10 Hochrisiko-Artikel** fachlich freigegeben, gültig versiegelt (`inhalt_sha256`) und mit zukünftigen Review-Terminen (`2026-11-19` bis `2026-12-14`) versehen (`open_live = 0`, `open_drafts = 0`). Von 34 geprüften YMYL-Quellen waren alle 29 Nicht-GII-Quellen unverändert mit HTTP `200` erreichbar; offen blieben ausschließlich die **5 Bundesrechts-Zitate auf `www.gesetze-im-internet.de`** (`vvg_2008/__40.html` ×2, `vvg_2008/__96.html`, `bgb/__502.html`, `got_2022/`).

Die Ursachenkette lag in einer stillen Schnittstellen-Kollision zweier am `2026-10-30` kurz nacheinander zusammengeführter PRs (`#973` / `90e10d84` um `13:49 UTC` und `#976` / `bc2988f0` um `15:55 UTC`):

| # | Schicht | Befund vor der Heilung | Dauerhafte Lösung |
|---|---|---|---|
| 1 | `scripts/belegketten_wache.py` (`abruf_gii_spiegel_http`) | `net_safety.sicherer_abruf()` liefert ein **3-Tupel** `(status, antwort_kopf, roh)`, `abruf_gii_spiegel_http()` entpackte jedoch `status, nutzlast = sicherer_abruf(...)` (**2-Tupel**) → `ValueError: too many values to unpack (expected 2)` bei jedem Spiegel-Abruf. | Korrektes 3-Tupel-Unpacking `status, _antwort_kopf, nutzlast = sicherer_abruf(...)`. |
| 2 | `scripts/belegketten_wache.py` (`_pruefe_gii_spiegel` & `pruefe_quelle`) | Pauschales `except Exception:` fing auch Programmierfehler (`ValueError`, `TypeError`, `AttributeError`) ab und gab still `basis` (`❔ ... · nicht erreichbar (URLError)`) zurück – der echte `ValueError` blieb im Ticket unsichtbar. | Enge Ausnahmeklasse `NETZ_AUSNAHMEN = (URLError, TimeoutError, OSError, HTTPException, UnsicheresZielFehler)`: Transportstörungen bleiben `unklar`, Programmierfehler schlagen sofort hart fehl. |
| 3 | Spiegel-Redundanz (`Gesetze-fuer-KI/bundesrecht`) | Einziger Spiegelpfad war unauthentifiziertes `raw.githubusercontent.com` (anfällig für CDN-Drosselung / Firewall-Filter). | Zweistufiger Spiegelabruf: primär `raw.githubusercontent.com`, sekundär `api.github.com/repos/Gesetze-fuer-KI/bundesrecht/contents/...?ref=main` (`Accept: application/vnd.github.raw`, mit `GH_TOKEN` ausschließlich gegenüber `api.github.com` für 5.000 Req/h Kontingent). |
| 4 | Transiente Drittquellen-Wackler (`abruf_http`) | Einzelversuch ohne Backoff führte bei kurzen `429`/`5xx`/Netz-Wacklern unter `--require-complete` sofort zur Ticket-Öffnung. | Einmalige Wiederholung (`versuche=2`, `basis_pause=1.5s`, `Retry-After` bis `15s`) für Nicht-GII-Ziele bei transienten Codes; GII-Direktabruf bleibt bei 1 Versuch, damit der Spiegel ohne Zeitverlust übernimmt. |
| 5 | Test- & Governance-Abdeckung (`test_belegketten_wache.py`, `governance_contract.py`, `redaktionelle-ymyl-pruefung.yml`) | Alle Tests übergaben eine eigene 2-Tupel-Attrappe `spiegel_abruf=...` und testeten nie `abruf_gii_spiegel_http()` gegen `net_safety.sicherer_abruf()`; `belegketten_wache.py` fehlte in `governance_contract.GUARDS` (C6) und lief im Workflow ohne `--selftest` sowie mit `continue-on-error: true`. | Offline-End-to-End-Probe über `urllib.request.urlopen` im Selbsttest und in `test_belegketten_wache.py`, Aufnahme in `governance_contract.GUARDS` (C6), `--selftest` in beiden Workflow-Jobs, Ersatz von `continue-on-error` durch deterministisches `|| rc=$?` + eigener Schritt `Werkzeug-Integrität der Belegketten-Wache` (Exit `>= 2` schlägt hart fehl) + Status-Kopfzeile im Arbeits-Ticket. |

---

## 2. Live- & Offline-Nachweis

1. **Live-Gegenprobe aller 4 Bundesrechts-Quellen aus `#1024`** gegen den realen Spiegel (`Gesetze-fuer-KI/bundesrecht` via `api.github.com`, inkl. 1,76 MB `bg/bgb.md`):
   - `https://www.gesetze-im-internet.de/vvg_2008/__40.html` → `status: "ok"` (`§ 40 Kündigung bei Prämienerhöhung` aktiv)
   - `https://www.gesetze-im-internet.de/vvg_2008/__96.html` → `status: "ok"` (`§ 96 Kündigung nach Veräußerung` aktiv)
   - `https://www.gesetze-im-internet.de/bgb/__502.html` → `status: "ok"` (`§ 502 Vorfälligkeitsentschädigung` aktiv)
   - `https://www.gesetze-im-internet.de/got_2022/` → `status: "ok"` (`GOT 2022` aktiv)
2. **Fachfreigaben & Siegelbestand (`editorial_review_gate.py --all --strict`):**
   - `10/10` Hochrisiko-Artikel freigegeben, Siegel intakt, `open_live = 0`, `open_drafts = 0`.
3. **Vertragstests & Hauswachen:**
   - `npm run test:redaktion:ymyl` (`editorial_review_gate.py --selftest`, `belegketten_wache.py --selftest`, `test_editorial_review_gate`, `test_belegketten_wache` inkl. `bash -eo pipefail`-Ausführung der Workflow-Schritte) → grün
   - Uhr-Probe (`+97` Tage), KI-/Netz-Probe (`selftest_ki.py --trap scripts/belegketten_wache.py`), `ki_transportweg.py`, `governance_contract.py --quick`, `workflow_vertrag_wache.py --gate`, `automation_premium_audit.py --strict`, `trigger_wache.py --check`, `wachen_vertrag.py`, `skript_syntax_wache.py --check`, `report_hygiene.py --check` → sämtlich grün.
