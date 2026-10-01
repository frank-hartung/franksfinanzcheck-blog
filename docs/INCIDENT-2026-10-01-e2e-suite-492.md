# Vorfall #492 – „E2E-Suite (Playwright) auf main rot – seit 30.09. ungemessen“

**Datum:** 01.10.2026 · **Ticket:** #492 (verwandt: #493)
**Befund im Ticket:** `.github/workflows/e2e.yml` scheitert reproduzierbar im Schritt
„E2E-Suite ausführen“; letzter grüner Lauf auf `main` stammte vom 30.09.
**Status:** bereits behoben (PR #494, 01.10.2026 10:04 UTC) · **dieser Report:**
unabhängige Reproduktion, Root-Cause-Bestätigung und Verifikation des
aktuellen `main`-Standes, da #492/#493 trotz `Closes #492`/`Closes #493` im
Merge-Commit offen geblieben waren.

---

## 1. Warum die Suite unbemerkt rot lief

Der Pfadfilter von `e2e.yml` triggert nur bei PRs, die `layouts/**`,
`assets/**`, `content/**`, `data/datasets/**`, `hugo.toml`, `e2e/**`,
`playwright.config.mjs`, `package.json` oder `package-lock.json` berühren.
Automatische Content-Commits landen aber per Push direkt auf `main` – ohne
PR, also ohne Trigger. Der einzige Schutzmechanismus war der wöchentliche
Cron-Lauf (Dienstag), der die Lücke tagelang offen ließ. PR #491 (neue
npm-Skripte in `package.json`) stieß die Suite zufällig wieder an und machte
einen seit dem 30.09. bestehenden roten Zustand sichtbar, den PR #491 selbst
nicht verursacht hatte (sein Diff berührt weder `layouts/`, `content/`,
`assets/` noch `hugo.toml`).

## 2. Reproduktion (unabhängig von #494 durchgeführt)

Da Job-Logs und der `playwright-report`-Artifact aus dieser Sandbox nicht
erreichbar sind (`productionresultssa8.blob.core.windows.net` liefert
`SSL_ERROR_SYSCALL`/EOF – dieselbe Einschränkung, die der ursprüngliche
Melder dokumentierte) und `workflow_dispatch` dem Agenten-Token verwehrt ist
(`403 Resource not accessible by integration`), wurde der exakte Fehlerstand
stattdessen lokal nachgebaut:

```
$ git worktree add /tmp/pr491 4caa341a     # Head von PR #491 vor dem Merge
$ hugo --quiet --destination public        # Build: grün
$ npx playwright test                      # 77 bestanden, 4 rot
```

Chromium kam dabei über den in `e2e/browser.mjs` dokumentierten
`@sparticuz/chromium`-Fallback, weil `cdn.playwright.dev` und
`release-assets.githubusercontent.com` aus dieser Sandbox ebenfalls blockiert
sind – exakt der Fall, für den der Fallback laut Kommentar im Modul gebaut
wurde.

### Gefundene Fehler (identisch zu den in #494 beschriebenen)

| Test | Fehler | Ursache |
|---|---|---|
| `article.spec.mjs` – „rendert Titel, H1, Meta und Breadcrumbs“ | `expect(h1.count()).toBe(1)` → erhalten `2` | Artikel `2026-09-30-last-minute-urlaub-…` begann den Fließtext mit `# Last-Minute-Urlaub: …` (Markdown-H1) statt `##`; PaperMod rendert den Frontmatter-Titel bereits als einziges `<h1>` |
| `visual-data.spec.mjs` ×2, `mobile.spec.mjs` „Datenvisualisierung mobil“ | `[data-ff-chart]` nicht gefunden (404 auf der Seite) | Artikel `2026-08-26-tagesgeld-zinsen-2026-…` stand auf `draft: true` – der Spam-Guard hatte die sachlich korrekte Formulierung „garantierter Zinssatz“ (Festgeld-Fachbegriff) fälschlich als harten Garantie-Claim gewertet und den Artikel vom Publish-Gate zurückgestuft |

77 der 81 Tests liefen bereits an diesem Stand grün – die Suite als Ganzes
war **nicht** strukturell kaputt, sondern durch zwei konkrete, unabhängige
Content-/Guard-Fehler kontaminiert.

## 3. Fix (bereits in `main`, PR #494, 01.10.2026 10:04 UTC – 33 Minuten nach #491)

* **Content:** `#` → `##` in `2026-09-30-last-minute-urlaub-…/index.md`;
  `draft: false` in `2026-08-26-tagesgeld-zinsen-…/index.md` wiederhergestellt,
  Datensatz/Methodik auf Version 1.1.0 synchronisiert.
* **`scripts/spam_guard.py`:** `CLAIMS_HARD`-Regex verengt – blockt weiterhin
  „garantierter Gewinn/Ertrag/…“, lässt „garantierter Zinssatz“ (Festgeld/
  Tagesgeld-Fachsprache) jetzt durch; zwei neue Selbsttest-Fälle frieren
  beide Richtungen ein.
* **`scripts/seo_audit.py`:** ein zusätzliches Markdown-H1 im Artikeltext ist
  jetzt ein harter Fund (`issues`, nicht nur gezählt) – genau der Defekt, den
  Playwright sah, wird jetzt schon vor der Veröffentlichung erkannt.
* **`scripts/publish_gate.py`:** Slug-Abgleich repariert (`seo_audit.py`
  lieferte `"<slug>.md"`, das Gate verglich nackte Slugs – dadurch griff die
  SEO-Prüfung nie durch).
* **`scripts/visual_data_gate.py`** (neu) + Tests: Chart-Datensätze zählen
  nur noch Referenzen in tatsächlich publizierbaren Inhalten (keine Drafts,
  keine zukünftigen/abgelaufenen Artikel) als erfüllte Produktionsabdeckung.
* **`.github/workflows/e2e.yml`:** Schedule von wöchentlich (Dienstag) auf
  **täglich** (`0 5 * * *`) erweitert – schließt die Lücke für
  Direkt-Pushes auf `main`, die keinen PR durchlaufen.
* **Regressionstests mit direktem Bezug auf #492:**
  `scripts/tests/test_seo_audit.py::test_markdown_h1_im_body_ist_harter_fund`,
  `::test_live_bestand_hat_keine_zusaetzlichen_body_h1`,
  `scripts/tests/test_visual_data_gate.py`,
  `scripts/tests/test_affiliate_integrity_workflow_contract.py` (für das
  begleitende Ticket #493).

## 4. Unabhängige Verifikation des aktuellen Standes (`main`, 76e5a6e8)

| Prüfung | Ergebnis |
|---|---|
| `hugo --quiet --destination public` | grün |
| `npx playwright test` (Desktop + Mobile, Fallback-Chromium) | **81/81 bestanden** |
| `python3 -m unittest discover -s scripts/tests` | **1178 Tests, OK** (14 übersprungen) |
| `python3 scripts/spam_guard.py --selftest` | 24/24 grün |
| `python3 scripts/affiliate_intent_guard.py --selftest` | grün, erwartete Funde erkannt |
| `python3 scripts/visual_data_gate.py` | 2 Datensätze, 2/2 Einbindungen in Produktion – BESTANDEN |
| `python3 scripts/seo_cockpit.py --strict` | 73 Seiten, 58 indexierbar, P1: 0, P2: 0 |
| `python3 scripts/tabellen_lesbarkeit_guard.py --selftest` + Lauf | grün, 0 Funde |

Ein Diff der beiden Stände zeigt exakt die oben beschriebenen Änderungen als
Ursache des Umschwungs von „4 rot“ auf „81/81 grün“ – keine weiteren
Abweichungen in den betroffenen Dateien.

`gh workflow run e2e.yml --ref main` wurde probiert, um wie im Ticket
vorgeschlagen einen offiziellen Actions-Lauf auf `main` zu erzwingen; das
Agenten-Token erhält dieselbe `403 Resource not accessible by integration`,
die der ursprüngliche Melder bereits dokumentiert hatte. Der nächste
planmäßige Lauf (täglich, 05:00 UTC) sowie jeder künftige PR, der
`layouts/`, `content/`, `assets/`, `hugo.toml` oder `e2e/` berührt, liefert
die offizielle Bestätigung automatisch.

## 5. Nachtrag zum Ticket-Status

PR #494 trägt `Closes #492` und `Closes #493` in der Beschreibung; beide
Issues blieben nach dem Merge dennoch `OPEN` – das automatische Schließen
griff in dieser Umgebung nicht (vermutlich fehlende Issue-Close-Berechtigung
des mergenden Bots). Mit diesem Report und den obigen Nachweisen wird #492
jetzt explizit geschlossen. #493 betrifft eine redaktionelle Tatsachenfrage
(„Marktvergleich“ vs. „Einzelangebot“ in `/go/tagesgeld/`) und bleibt zur
menschlichen Bestätigung offen, auch wenn der technische Teil (Eskalation in
der täglichen Affiliate-Wache) bereits mit PR #494 geliefert wurde.
