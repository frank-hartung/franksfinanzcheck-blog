# Premium-Fix: „Zwingend 2–3 LIVE an Mo/Mi/Fr“ (Mi 02.09.2026: nur 1 Artikel)

**Stand:** 03.09.2026 · Branch `arena/01a0668b-franksfinanzcheck-blog` · Basis `b9e6ea4`

## Kernbefund (Mi 02.09.2026)

Am Mittwoch, 02.09.2026, ging nur **1** statt der geforderten **2–3** Artikel live.
Ursachenkette (drei Fehler, die zusammenwirkten):

1. **R8-URL-LEERZEICHEN:** Ein fertiger Artikel (`2026-08-26-handytarif-…`) scheiterte
   am Publish-Gate an einer internen Markdown-URL mit Leerzeichen
   (`…-zu Hause/` statt `…-zuhause/`) und wurde in den Zustand **hold** gestuft.
2. **Draft-inclusive Tageszählung:** Die Engine zählte gleichtägige Entwürfe als belegte
   Tages-Slots. Die Fallback-Slots (14:10/17:40 UTC) sahen den Tag dadurch als „voll (2/2)“
   und füllten das LIVE-Mindestziel nicht mehr auf.
3. **Kein Sicherheitsnetz:** Die Fehlerklasse R8-URL-LEERZEICHEN wurde von keiner Wache
   geheilt, und es gab keinen KI-unabhängigen Reserve-Pool für Ausfall-Tage.

## Vier-Baustein-Lösung (Premium-Agentur-Niveau, deterministisch, kein KI-Risiko)

### Baustein 1 – URL-Hygiene-Heiler (neue Datei `scripts/fix_url_hygiene.py`)
- Heilt Leerzeichen-URLs und `%20`-URLs gegen die **echten Post-Slugs** (eindeutige Auflösung,
  keine Rate-Rate-Rate).
- Entblockt ausschließlich dadurch gehaltene Posts (`hold` → Re-Queue) nachweisbar.
- Selbsttest (`--selftest`) als Sabotage-Schutz; eingebunden in:
  `deploy.yml` (vor Publish-Gate), `content-engine-v2.yml` (Phase 0.5 + beide
  Optimierungs-Phasen), `blog-health-daily.yml` (vor Kadenz-Heilung), `publish.py`,
  `publish_gate.py` und `engine_generate.py` (sofort nach jedem Speichern).
- **Bestand ist geheilt:** alle vier betroffenen Dateien zeigen auf den kanonischen Slug;
  Frontmatter-Ops-Kommentar mit Literal-Fehlerklasse entfernt.

### Baustein 2 – LIVE-only Tagesbilanz (`scripts/engine_generate.py`)
- `tages_bilanz()` zählt **nur** `draft: false` (live). Gate-Entwürfe belegen keine Slots mehr.
- `produktions_entscheidung()`: `STOP`/`DEADLOCK`/`WEITER` auf LIVE-Basis; STOP-Meldung
  nennt explizit „LIVE …“.
- Versuchs-Deckel (`2×max`) + „nur 1× Rescue-Entwurf pro Tag und nur bei 0 LIVE/0 Entwürfen“
  – kein „Vollparken“ mit Entwürfen.
- Dead Code `count_articles_today()` entfernt (ersetzt durch `cadence_guard.published_on`).
- `_reserve_topup()`: nach gesunden Produktionstagen wird der Reserve-Pool wieder gefüllt
  (`RESERVE_TARGET`, Default 2) – der Pool trocknet nie aus.
- **Selbsttest grün:** `✅ ENGINE-SELFTEST bestanden (LIVE-Bilanz: Gate-Entwurf blockiert keine
  Slots mehr, Refill, DEADLOCK- und STOP-Fälle).`

### Baustein 3 – Redaktions-Reserve-Pool (neue Datei `scripts/reserve_pool.py`)
- Fertige Premium-Evergreen-Artikel als `draft: true` + `reserve: true` (ohne `cadence_*`-Felder →
  park_state: „manual“, keine andere Automatik fasst sie an).
- `--publish-to-min`: veröffentlicht an Mo/Mi/Fr **nur bis zum LIVE-Mindestziel**
  (Guard identisch zu `cadence_guard.PUBLICATION_DAYS`), schreibt Audit-Zeile
  `reserve_published:`. `--status`, `--selftest`.
- **Pool aktuell gefüllt (2 Artikel):**
  - `2026-09-03-hausratversicherung-kosten-leistungen-vergleich` (~13,7k Zeichen)
  - `2026-09-03-kreditkarte-vergleichen-kostenlos-sicher-bezahlen` (~13,8k Zeichen)
  Beide im Premium-Korridor (12k–18k), interne Links auf live-Posts, CTA-Ziele in
  `check24_links.yaml` registriert (`hausrat`, `kreditkarte`, `reisekrankenversicherung`).

### Baustein 4 – Kadenz-Endkontrolle (neue Datei `.github/workflows/kadenz-endkontrolle.yml`)
- Cron Mo/Mi/Fr **21:05 UTC** (nach letztem Engine-Slot 17:40 und Produktions-Wache 20:00) +
  `workflow_dispatch`.
- Ablauf: heilen (URL-Hygiene + holds + Kadenz) → LIVE-Zahl zählen (nur `draft:false`) →
  bei Unterschreitung **Reserve-Pool veröffentlichen** → Qualitäts-Folgekette
  (Titel/Cover/URLs) → Commit+Push → **expliziter Deploy-Dispatch**
  (GITHUB_TOKEN-Commits triggern keine Workflows; deploy-catchup fängt zusätzlich ab) →
  `engine_issue.py --deficit` (öffnet/schließt das Defizit-Issue automatisch).
- Damit kann ein Mo/Mi/Fr **nie mehr still unter dem Mindestziel enden**.

## Validierung (lokal, alles grün)

```
py_compile …                       OK
check_titles.py                    34 Titel | Verstöße: 0
textverständnis (Hard-Rules)       beide Reserve-Drafts: 0 harte Funde
fix_url_hygiene.py --selftest      ✅ (Leerzeichen-URLs, %20, Rate-Verbot, hold-Heilung)
cadence_guard.py --selftest        ✅
reserve_pool.py --selftest         ✅
engine_generate.py --selftest      ✅
fix_url_hygiene.py --fix           „keine Leerzeichen-URLs im Bestand“
grep '](…zu Hause' content/        keine Treffer
```

## Nächster Publikationstag: Freitag, 04.09.2026

Slots 06:10/14:10/17:40 UTC + Endkontrolle 21:05 UTC. Bei vollem Engine-Erfolg liefern die
Slots; bei Teil-/Totalausfall fängt der Reserve-Pool (2 Artikel) das LIVE-Minimum von 2 ab.

## Hinweis: Push/PR wartet auf GitHub-Berechtigung

Die Commits liegen lokal auf `arena/01a0668b-franksfinanzcheck-blog` (4 Commits, Basis
`b9e6ea4`). Ein Push ist derzeit **nicht möglich**: GitHub verweigert GitHub-Apps das
Erzeugen/Aktualisieren von `.github/workflows/*` ohne `workflows`-Berechtigung
(„refusing to allow a GitHub App to create or update workflow … without `workflows`
permission“). → **GitHub-Verbindung in Arena neu verbinden mit `Workflows`-Berechtigung
(Read & write)**, danach Push + PR gegen `main` sofort möglich.
