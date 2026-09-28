# Klebe-Artefakte-Premium-Audit 28.09.2026 — Gesamter Blog

**Auftrag:** Sämtliche Klebe-Artefakte im gesamten Blog auf Premium-Level einer
Profi-Agentur beheben — nicht nur die bekannten Fundstellen, sondern alle
belegten Artefakt-Klassen über alle Textflächen, mit dauerhafter Wache gegen
Rückfall.

| | |
|---|---|
| **Umfang** | 69 Content-Dateien (`content/`), 27 Audio-Chunk-Dateien (`data/audio/`), Daten-Textfelder (`data/*.yaml`, `themenwelten.json`), sichtbare Layout-Texte (`layouts/`), Newsletter-Worker, `static/go/`-Redirects |
| **Artefakt-Klassen geprüft** | 11 (R9-Doppel-Initialen, CTA-Klebe, Wortdopplung adjazent, Wortdopplung mit Einschub, FM-Klebefuge, sichtbares `{rel=…}`, Camel-Klebe, Ziffern-Klebe, Strich-Space-Klebe „dein-zu Hause“, Satzzeichen-Klebe, Bold-Klebe) |
| **Echte Befunde** | **2** — beide Live, beide dieselbe Ursachenfamilie „Gasrechnung senken“ |
| **Geheilt** | 2 Artikel-Zeilen + 2 benachbarte C15-Kleinschreibungen in denselben Sätzen |
| **Durably verschlossen** | Neue harte Regel **R10-DOPPELWORT** in `textverstaendnis_guard.py` + Scan-Scope-Erweiterung auf alle Content-Flächen |
| **Verifikation** | Selbsttest R2–R10 grün (12 neue Sabotage-Fälle) · Verständnis-Audit: **R9/R10 = 0 Funde** (hart 2 = 2 R3-Terminologie-Bestandsbefunde, keine Klebe-Klasse, s. Abschnitt 3.4) · Casing-Guard 🎉 0 Befunde (corpusweit) · FM-Grenzen 69 Dateien sauber · Hardcases 0 · CTA-Hygiene-Selbsttest grün · **989 Unit-Tests OK** |

---

## 1. Warum dieser Audit anders läuft als ein Spellcheck

Klebe-Artefakte sind **maschinelle Text-Korruption** (Inserter-/Editier-/
Heiler-Kaskaden), keine Rechtschreibfehler: Jedes einzelne Wort ist korrekt
geschrieben — nur die Naht ist kaputt. Darum sieht Hunspell sie nicht, und
darum braucht jede Klasse einen eigenen Detektor. Belegte Familien in der
Repo-Historie:

| Familie | Beispiel | Erstmals | Wache |
|---|---|---|---|
| Doppel-Initialen (Inserter) | „HHerfindestdu“, „Ddeine6 Themenwelten" | 02.09. | R9-KLEBEWORT (hart) |
| CTA-Klebe | „Ddiebesten Tarife …" | 11.09. | `fix_cta_hygiene.py` |
| FM-Klebefuge | `---Warum zahlen …` | 18.09. | F6 (`fm_boundary_guard.py`, heilt selbst) |
| Sichtbares Prompt-Gerüst | `{rel="sponsored"}` im gerenderten Text | 25.09. | `fix_cta_hygiene.py`, 2. Klasse |
| Komposita-Fugen-Fehler | „Zweitwagenregelung", „dein-zu Hause" | Aug. | manuell geheilt |
| **Wortdopplung** | **„senken senken will"** | **28.09. (dieser Audit)** | **R10-DOPPELWORT (neu, hart)** |
| **Dopplung mit Einschub** | **„senken um bis zu 15 % senken"** | **28.09. (dieser Audit)** | **R10-DOPPELWORT (neu, hart)** |

## 2. Die zwei echten Befunde — und ihre Root Cause

### Befund 1 (Live, Artikel vom 20.09., veröffentlicht 25.09.)

> `content/posts/2026-09-20-gasrechnung-senken-so-bereitest-du-dich-im-spaetsommer-vor/index.md`, Intro:
> „Wer seine Gasrechnung **senken senken** will, sollte im Spätsommer handeln."

**Root Cause, per Git-Blame und Lektorats-Doku belegt:** Das Lektorat vom
25.09. (`docs/LEKTORAT-2026-09-25-gasrechnung-senken-deine-strategie-fuer-den-winter-2026.md`,
Abschnitt 2.2) fand und heilte exakt diesen Satz — **im damaligen Slug**
`…deine-strategie-fuer-den-winter-2026`. Beim Rework auf den heutigen Slug
(`…so-bereitest-du-dich-im-spaetsommer-vor`) überlebte die Dopplung: Die
Kleinschreibung („gasrechnung") war behoben, die Wortdopplung nicht. Die
Wache meldete damals wie heute „0 Befunde" — R2–R9 können sie strukturell
nicht sehen. Ein klassischer „verlorene Heilung"-Fall (gleiche Musterfamilie
wie die FM-Zeitbombe vom 18.09.).

### Befund 2 (Live, Artikel vom 14.08.)

> `content/posts/2026-08-14-gasrechnung-senken-fehler-im-spaetsommer-vermeiden/index.md`, Fazit-Vorzeile:
> „Mit dem richtigen Vorgehen lässt sich die gasrechnung **senken um bis zu 15 % senken**."

Einschub-Variante derselben Ursachenfamilie: Das Duplikat klammert einen
Quantor. Korrektes Deutsch stellt den Quantor vor das Verb. In demselben
Artikel saß zusätzlich die Kleinschreibung „deine gasrechnung senken"
(der einzige offene C15-Befund des Korpus).

### Heilungen (vorher → nachher)

| Datei | vorher | nachher |
|---|---|---|
| `…/2026-09-20-gasrechnung-senken-so-bereitest-du-dich…/index.md` | „Wer seine Gasrechnung senken **senken** will, …" | „Wer seine Gasrechnung senken will, …" |
| `…/2026-08-14-gasrechnung-senken-fehler…/index.md` (Zeile 264) | „… lässt sich die gasrechnung **senken um bis zu 15 % senken**." | „… lässt sich die Gasrechnung um bis zu 15 % senken." |
| `…/2026-08-14-gasrechnung-senken-fehler…/index.md` (Zeile 57, Nachbarschaftsheilung) | „Gerade wenn du deine gasrechnung senken willst, …" | „Gerade wenn du deine Gasrechnung senken willst, …" |

**Schutzzonen-Beweis:** Insgesamt 3 geänderte Zeilen in 2 Artikeln — keine
Links, keine Frontmatter-Schlüssel, keine Überschriften, keine Zahlen (der
Wert „15 %" bleibt byte-identisch, nur seine Stellung im Satz ist jetzt
grammatisch). `lastmod` bewusst nicht angefasst (Frische-Inflation-Vertrag).
Kein Artikel hat eine Audio-Tonspur mit dem Artefakt (2026-09-20: keine
Chunks vorhanden; 2026-08-14: Chunk-Text enthält die Sätze nicht) — nichts
nachzusynchronisieren.

## 3. Was sonst überall geprüft wurde — und sauber ist

| Fläche | Prüfung | Ergebnis |
|---|---|---|
| 69 Content-Dateien (Posts, Pillar-Hubs, Startseite, Datenschutz, Impressum, Methodik, Über, Newsletter-Seiten) | alle 11 Klassen, inkl. zeilenübergreifender Dopplungen (whitespace-normalisiert), Frontmatter-Textwerte (description, pin_description, erfahrung), Dopplungen über Markup-Grenzen (`**W** W`) | ✅ nur die 2 Befunde oben |
| 27 Audio-Chunk-Dateien (`data/audio/*.chunks.json`, Textfelder) | R9-Familien, Dopplungen, CTA-Klebe | ✅ sauber |
| Daten-Texte (`aktuelle_entwicklungen.yaml`-Hooks, `topics.yaml`, `themenwelten.json`, `saisons.yaml`, `terminologie.yaml`, `schreibstil.yaml`, `brand_brain.yaml`) | Dopplungen, Klebe-Muster in Textfeldern | ✅ sauber |
| Layouts (`layouts/**`), Newsletter-Worker, `static/go/**` | sichtbare Texte (ohne Template-/Code-Logik) | ✅ sauber |
| Frontmatter-Nähte | `fm_boundary_guard.py` (F6, 69 Dateien) | ✅ sauber |
| CTA-Zeilen | `fix_cta_hygiene.py` (beide Klassen, Selbsttest grün) | ✅ sauber |
| Hardcases (Duden-Blacklist) | `hardcases_guard.py` | ✅ 0 Fest-Fehler |
| „Duplikat mit Content-Wörtern dazwischen" (weites Fenster 1–6 Wörter, gefiltert auf Struktur-Wörter) | manuelle Durchsicht aller Kandidaten | ✅ nur legitime Muster („Schritt für Schritt", „Konto nicht gleich Konto", Parallelismen) |

**Bewusst geprüft und NICHT geändert (mit Begründung):**

1. **`id="ddeine6-themenwelten"`** in `layouts/_partials/themenwelten.html`:
   dokumentierter Legacy-Anker (`aria-hidden`, nie sichtbarer Text), damit
   alte geteilte Abschnitts-Links gültig bleiben. Entfernen würde Besucher-
   Links brechen — kein Artefakt, sondern Kompatibilitätsvertrag.
2. **Überschrift→Absatz-Wiederholungen** („### Kinder / Kinder haben …",
   „… gegen Impulskäufe / Impulskäufe sind …"): legitimes Journal-Muster,
   durch den Absatz-Scanner der Wache explizit ausgenommen (Selbsttest-Fall).
3. **Nomen-Verb-Homographen** („Konsum-Fallen fallen so auf"): korrektes
   Deutsch; R10 ist case-exakt, genau damit es hier nicht falsch anschlägt.
4. **R3-TERMINOLOGIE-Bestandsbefunde** (2×, DNS-/Tagesgeld-Artikel) und die
   62 weichen R4/R8-Funde: keine Klebe-Klasse — Redaktions-Review-Kandidaten
   im Report, außerhalb dieses Auftrags. (Hinweis: In Umgebungen ohne PyYAML
   bleiben sie unsichtbar, weil die Terminologie-Last dann entfällt.)
5. **Protokoll- und Journal-Dateien** (`data/newsletter_journal.jsonl` u. ä.):
   Historie wird nicht rückgeschrieben.

## 4. Dauerhafte Härtung — R10-DOPPELWORT (hart, blockierend)

**Design** (`scripts/textverstaendnis_guard.py`, guard-interner Nummernraum
R2–R10; die Ketten-R-Nummern des Qualitäts-Regelwerks sind ein eigener
Nummernraum und bleiben unangetastet):

- **Adjazente Dopplung:** `\b(Wort)(\s+)\1\b` — case-exakt, reine
  Leerraum-Trennung, nur Fließtext-Absätze (Überschriften/Listen/Tabellen/
  Zitate/Code ausgenommen), Fett-Markierung und Zeilenumbrüche innerhalb
  eines Absatzes mitgedacht.
- **Einschub-Variante:** Doplikat um einen reinen Quantor
  (`um (bis zu |rund |etwa …)? Zahl %|€|Prozent`) — die belegte
  Maschinen-Form, im Deutschen nie korrekt, darum ohne Ausnahme hart.
- **Eingefrorene Präzision** (12 neue Selbsttest-Fälle, Sabotage-Schutz):
  findet „senken senken", Dopplung über Hard-Wrap, Dopplung über
  `**Fett**`, Quantor-Einschub; schlägt NICHT an bei „Zugluft, die die
  Thermostate …", „kauft, kauft zweimal", „werden, werden", „voll-voll",
  „heißt das: Das …", „ist der, der …", „Konsum-Fallen fallen",
  „Sorgen sorgen", korrekter Quantor-Stellung und
  Überschrift→Absatz-Wiederholung.
- **Scan-Scope:** Die Klebe-Regeln (R9/R10, Nested-Links) laufen seit diesem
  Audit über **alle Content-Flächen** (52 Artikel + 17 Seiten: Startseite,
  Pillar-Hubs, Rechts-, Methodik-, Über- und Newsletter-Seiten). Neu
  angelegte Seiten rücken automatisch in den Scan — die Lücke „Wache kennt
  nur `content/posts`" ist geschlossen.
- **Verdrahtung:** harte Regel im `hard_rules`-Tupel (blockiert neue Artikel
  im Engine-Modus `--new-only`, wie R9); Report nennt Regelwerk und
  Seitenzahl; `data/verstaendnis_history.jsonl` unverändert im Schema.

## 5. Verifikations-Ergebnisse

| Messgröße | Ergebnis |
|---|---|
| `textverstaendnis_guard.py --selftest` | ✅ R2–R10 grün (inkl. 12 neuer R10-Sabotage-Fälle) |
| `textverstaendnis_guard.py` (Komplett-Audit) | ✅ **R9/R10: 0 Funde** (Klebe-Klassen sauber); hart 2 = 2 R3-Terminologie-**Bestands**befunde (DNS-/Tagesgeld-Artikel, keine Klebe-Klasse, Abschnitt 3.4 — nur in Umgebungen ohne PyYAML unsichtbar) · weich 62 (Bestand) |
| `casing_guard.py` | 🎉 **0 Befunde** — der letzte offene C15-Fund („deine gasrechnung") ist mitgeheilt |
| `fm_boundary_guard.py` | ✅ 69 Dateien sauber (F6) |
| `hardcases_guard.py` | ✅ 0 Fest-Fehler |
| `fix_cta_hygiene.py --selftest` | ✅ grün (Kanonik, Idempotenz, Draft-Filter) |
| `readability_check.py` (beide geheilte Artikel) | ✅ Flesch 68,1 / im Ziel |
| `profi_text_check.py` / `quality_score.py` / `check_length.py` | ✅ 100/100 · Verdict „publish" · Länge im Optimum |
| `python3 -m unittest discover -s scripts/tests` | ✅ **989 Tests OK** (22 umgebungsbedingt übersprungen; anfängliche Sandbox-Fehler waren ausschließlich das fehlende PyYAML, nachinstalliert) |
| `hugo`-Build / Playwright / Hunspell / LanguageTool | ⚠️ in dieser Sandbox nicht verfügbar (wie im Lektorat 25.09.) — CI-Workflows (`e2e.yml`, `content-engine-v2.yml`, `seo-weekly.yml`) holen das im Netzkontext nach; die Heilungen sind reine Fließtext-Ein-Zeilen-Änderungen ohne Layout-/Strukturberührung |

## 6. Verifikationskommandos

```bash
python3 scripts/textverstaendnis_guard.py --selftest   # R2–R10, Sabotage-Schutz
python3 scripts/textverstaendnis_guard.py              # Komplett-Audit, hart 0 erwartet
python3 scripts/casing_guard.py --dry-run              # 0 Befunde erwartet
python3 scripts/fm_boundary_guard.py                   # 69 Dateien sauber
python3 scripts/hardcases_guard.py                     # 0 Fest-Fehler
python3 scripts/fix_cta_hygiene.py --selftest
python3 -m unittest discover -s scripts/tests          # 989 Tests
grep -rn "senken senken" content/                      # leer erwartet
```

---

_Audit-Umfang: sämtliche Textflächen des Blogs. Methode: klassenweise
Detektoren (regex-basiert) + manuelle Durchsicht aller Kandidaten; jede
Heilung vor dem Schreiben verifiziert. Kein artefakt-zitierendes Dokument
(docs/, docs/archiv/) wurde „geheilt" — dort sind die Fundstellen Beweismittel._
