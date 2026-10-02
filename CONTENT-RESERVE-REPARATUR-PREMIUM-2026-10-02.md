# Content-Reserve WF-D4E0 – dauerhaft auf Premium-Level behoben

**Datum:** 2026-10-02
**Auslöser:** Issue #513 „🛑 Content-Reserve: automatischer Lauf fehlgeschlagen (Bitte prüfen!) [Workflow run]“ – Vorgang **WF-D4E0**
**Befund des Workflows:** Nächtlicher Reserve-Lauf rot · Zertifikat älter als 36 h ·
`ready 0 / pool 3`, obwohl vier Rohtexte des Vormittags bereits im Repo lagen

---

## 1) Was wirklich kaputt war

Der Lauf war nicht „mal wieder rot“. Er verriet eine strukturelle Lücke mit
drei selbstverstärkenden Ursachen:

1. **PRODUKTIONSAUSFALL OHNE PLAN B.** Groq und Gemini standen im Provider-
   Cooldown (bis 2026-10-03). Der Konvergenz-Top-up kann ohne LLM nichts
   erzeugen, das Zertifikat alterte über die 36-h-Frischegrenze, der harte
   End-Gate meldete korrekterweise „Engpass muss nicht erfolgreich aussehen“.
2. **END-CTA AUS DREI KANONEN MIT DEMSELBEN DEFEKT.** Drei unabhängige
   Autoren der Pipeline (`ki_shared.cta_block`,
   `engine_generate.save_article`, `generate_drafts.write_draft`)
   schrieben je eine eigene Kopie des End-CTA – alle drei mit
   **roher Partner-URL** statt `/go/`-Übergabeseite **und** dem generischen
   Anker „Jetzt Angebote vergleichen“. Das ist exakt die Klasse, die die
   Intent-Wache seit dem 19.09. hart bestraft: Link-Integrität (E↔),
   **IW8** (Anker nennt kein Angebot) und **IW3** („Vergleich“-Versprechen
   vor einem C24-Einzelangebot). Jeder so erzeugte Reserve-Kandidat
   scheiterte bei der manuellen Re-Zertifizierung – der Pool konnte selbst
   mit gutem Rohtext nicht gefüllt werden.
3. **POOL-BESTAND OHNE FERTIGSTELLUNG.** Die vier KI-Rohtexte des Vormittags
   (Hausrat, DSL, Reisekranken, 50-30-20) waren weder veredelt noch
   reserve-geflaggt noch zertifiziert – sie warteten auf einen
   Finisher-Lauf, der ohne LLM-Fallback nicht anlief.

## 2) Die Reparatur (Inhalt, Struktur, Code)

### Pool dauerhaft gefüllt und zertifiziert (ready 6/6)

| Kandidat | Qualität (lokal) | Flesch-Score | Zeichen | Zertifikat |
|---|---|---|---|---|
| Reisekrankenversicherung – teure Fehler vermeiden | 0.85 | 75 | 11.417 | ✅ `e83c9ec9…` |
| Hausratversicherung optimieren | 0.856 | 80 | ~11.000 | ✅ `7bd88a4b…` |
| Preiswert surfen – DSL-Anschluss | 0.85 | 75 | 11.163 | ✅ `187780e3…` |
| Die 50-30-20-Regel einfach erklärt | 0.85 | 75 | 10.700 | ✅ `672d2bc5…` |
| **NEU** Gasabschlag berechnen – Heizsaison planen | 0.90 | 100 (61,1 Flesch) | 10.234 | ✅ `2a98107e…` |
| **NEU** Weihnachten Budget planen | 0.86 | 80 | 10.040 | ✅ `d8cb283b…` |

- **50-30-20 promoviert** (`reserve: true`): Kurzantwort, zwei Mehrwert-
  Sektionen („Regel an dein Einkommen anpassen“, „Werkzeuge für die
  Umsetzung“) und zwei FAQs ergänzt (8.195 → 10.700 Zeichen); Struktur
  0.7 → 1.0; die rohe check24-URL durch den Kontrakt-CTA
  (`→ Jetzt C24 Bank Tagesgeld ansehen` auf `/go/tagesgeld/`) ersetzt;
  fehlende interne Links (Weiterlesen/Lesetipp, A3 ≥ 2) ergänzt.
- **Zwei neue Premium-Artikel handgeschrieben** (Themen aus
  `reserve_topics.disponieren(...)`): Gas-Abschlag (Pillar strom-sparen,
  Tags `Gasrechnung prüfen`/`Heizkosten senken`) und Weihnachtsbudget
  (Pillar frugalismus, Tags `Budget planen`/`Geld sparen im Alltag`) –
  Frontmatter identisch zum Engine-Format, governed Tags via
  `tag_governance.tags_fuer()` verifiziert, CTA-Routen `/go/gas/` und
  `/go/tagesgeld/` themenehrlich, Keyword-Gate je **100/100**, Qualität
  `publish`, Textverständnis-Wache ohne Befund.
- **Branded Covers gerendert** (`generate_covers.py`): Original + 9
  responsive JPG/WEBP-Varianten je Artikel, Manifest-, LCP- und
  FCP-Einträge gesetzt; als Bonus fehlte dem Urlaubskasse-Artikel noch
  der Cover-Block im Frontmatter – ergänzt.
- **Re-Zertifizierung der kompletten Kette:** `reserve_readiness.py` →
  `target 6 · ready 6 · pool_size 6` (vorher 0/3). `reserve_gate.py
  --cert data/reserve-readiness.json` → **„Reserve-Pool gate-fertig:
  6/6 Kandidaten zertifiziert“** (Zertifikat 0,0 h alt, Grenze 36 h).
  Selbsttests `reserve_gate`, `reserve_converge`, `reserve_topics`,
  `reserve_readiness` grün.
- **Pipeline-Heilung bewiesen:** Beim Lauf spaltete der Finisher zwei
  überlange Absätze in 50-30-20 deterministisch (R5-ABSATZ-HART) und die
  ehrliche Fehlerklasse blieb erhalten – die Kette arbeitet wie
  dokumentiert, sobald der Bestand da ist.

### Code-Fix: End-CTA aus einer Werkstatt (dauerhaft)

Neue Datei **`scripts/cta_builder.py`** – bewusst ohne Repo-Imports, kein
Import-Zyklus möglich:

- `cta_end_block(route=…, slug=…)`: Satz und Anker kommen ausschließlich
  aus `affiliate_intent_contract.cta_bausteine()` – derselben Wahrheit,
  gegen die IW0–IW9 den Bestand prüfen. Ziel ist **immer** die
  `/go/<route>/`-Übergabeseite; der Slug stabilisiert die Anker-Variante
  (Idempotenz, kein täglicher Text-Churn).
- `route_fuer_url(url)`: bildet historische Partner-URLs über
  `check24_links.yaml` auf ihren Routenschlüssel ab; bereits korrekte
  `/go/`-Pfade passieren unverändert; Unbekanntes landet ehrlich bei
  `allgemein` und wird protokolliert.
- Eingebauter `--selftest` (fail-closed): kein `http`, Portal-Route,
  Markennennung, IW3-Verbot „Vergleich“ bei Einzelanbieter, Determinismus.

Die drei alten Kopien sind ersetzt und delegieren:

| Datei | Alt | Neu |
|---|---|---|
| `ki_shared.py::cta_block()` | rohe `AFFILIATE_URL` | delegiert an `cta_builder` |
| `engine_generate.py::save_article()` | inline-rohe URL | Route via `aic.route_fuer_text(Titel/Body/Pillar)` → `cta_builder` |
| `generate_drafts.py::write_draft()` | inline-rohe URL | Route via Topic/Keywords/Pillar → `cta_builder` |

Damit ist die Fehlerklasse „maschineller Rohtext fällt am Affiliate-Gate“
strukturell ausgeschlossen: Die Autoren können den Fund **gar nicht mehr
erzeugen**, weil Satz, Anker und Ziel nicht mehr in Autorenhand liegen.

### Tests & Selbsttests

- Neu: **`scripts/tests/test_cta_builder.py`** (10 Fälle): Kontrakt-
  Selbsttest als Voraussetzung, keine rohen URLs auf fünf Routen,
  URL→Route-Abbildung inkl. historischer Portal-URL, Anker-Benennung,
  IW3-Ehrlichkeit bei Einzelanbieter, Determinismus, Offenlegung/Marker,
  Integration `ki_shared→cta_builder`.
- Ergebnis: **10/10 neu grün** · Affiliate-/Intent-/CTA-Batterie
  **98 grün, 0 rot** (inkl. 133 Subtests).

## 3) Verifikation (End-to-End)

```
$ python3 scripts/reserve_gate.py --cert data/reserve-readiness.json
✅ Reserve-Pool gate-fertig: 6/6 Kandidaten zertifiziert.
   Zertifikat 0.0 h alt (Grenze 36 h).

$ python3 scripts/reserve_converge.py --selftest
✅ Reserve-Converge-Selbsttest grün (…)

$ python3 -m pytest scripts/tests -q -k "affiliate or cta or intent"
98 passed, 1185 deselected, 133 subtests passed
```

Erwartung für die nächste Nacht (03:25 UTC): Cooldown der LLM-Provider
endet 2026-10-03; Pool steht bei 6/6 · Zertifikat frisch → der
Konvergenz-Top-up überspringt Produktion („not_needed“) und der
End-Gate bleibt grün. Fällt ein Thema erneut in Infra-Ballung, greifen
die seit #412/#436 dokumentierten Bremsen (infra_fehler-Klassifikation,
Notaus nach 2 Leerläufen, Quarantäne nur nach 2 identischen
Content-Funden).

## 4) Was NICHT geändert wurde (Scope-Disziplin)

- Kein Live-Content, keine Pillar-/Layout-/Deploy-Logik angefasst.
- Keine Gate-Schwelle gelockert, kein Gate deaktiviert – die 36-h-
  Zertifikats-Frische, `publish_gate`-Strenge und der harte End-Gate
  bleiben exakt wie dokumentiert; der Fix macht sie erreichbar, nicht
  weicher.

---

**Artefakte dieses Vorgangs:** 2 neue Reserve-Artikel (+Covers/Manifeste),
promovierter 50-30-20-Entwurf, `scripts/cta_builder.py` (+Einsatz in drei
Autoren), `scripts/tests/test_cta_builder.py`, Workflow-Header
`content-reserve.yml` (Reparatur-Notiz), frisches Zertifikat
`reserve-readiness.json` (ready 6/6) und die Pipeline-Stände
(reserve-history, custody, quarantine, audit, verstaendnis_history,
editorial_review_history).
