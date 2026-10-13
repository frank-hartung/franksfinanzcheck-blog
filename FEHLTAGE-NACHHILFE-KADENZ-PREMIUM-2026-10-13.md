# Kadenz: zwölf Nachlieferungen für elf Mo/Mi/Fr-Fehlstellen — Abschluss auf Premium-Niveau

**Auftrag (Frank, 13.10.2026):** „Ein Blogartikel für den 05.10.2026 fehlt im
Blog. Bitte auf Premium-Level einer Profi-Agentur beheben und den GESAMTEN Blog
auf weitere fehlende Artikel an den Publikationstagen Montag, Mittwoch,
Freitag prüfen und entsprechend nachliefern – ebenfalls auf Premium-Niveau.“

**Datum:** 13.10.2026 · **Commit:** `00ce426` (Branch
`arena/31946bae-franksfinanzcheck-blog`)

**Prüfmaßstab:** DAUERVORGABE Regel 2 (`docs/CADENCE-REPORT.md`): nur Mo/Mi/Fr,
**2 bis 3 Artikel pro Publikationstag** — durchgesetzt von
`scripts/cadence_guard.py` (`MIN_ARTIKEL_PRO_TAG=2` … `MAX_ARTIKEL_PRO_TAG=3`).

---

## Kurzfassung

Der gemeldete 05.10.2026 war nicht der einzige Fehltag. Derselbe Lauf, der ihn
bestätigte, hat den ganzen Blog gegen die Dauervorgabe gemessen: **elf
Publikationstage lagen unter dem Mindestziel** — zehn Tage mit 1/2 Live
(12.08., 17.08., 26.08., 28.08., 04.09., 21.09., 23.09., 28.09., 30.09.,
05.10.) und der Montag **31.08. mit 0/2**. Zusammen fehlten **zwölf Artikel** —
genau die Menge, die ein Profi-Team in einem Zug nachliefert: thematisch
passend, unabhängig geprüft, mit eigenen Covern.

| Kennzahl | vorher | nachher |
|---|---|---|
| Publikationstage unter Mindestziel | **11** | **0** |
| Tage mit 0 Live-Artikel | **1** (31.08.) | **0** |
| Live-Artikel im Blog | 44 | **56** |
| Tage mit 2/2 Live (jeder Publikationstag) | 17 / 28 | **28 / 28** |
| `cadence_guard.py --check` | grünes Exit, aber 11 ⚠️-Defizitzeilen | 0 Off-Day, 0 Over-Cap, 0 Defizit |

Jeder der zwölf Artikel wurde einzeln geliefert — Recherche, Aufbau, Quellen,
Kurzantwort, FAQ, Tabelle, Rechenbeispiel mit ausgewiesenen Annahmen,
Offenlegung, Inlinks, Cover — nicht als Massenfüllung. Die vollständige
Gate-Kette des Repos ist über alle 56 Live-Artikel grün (Abschnitt *Belege*).

---

## Befund im Detail

### Wie gemessen wurde

`scripts/cadence_guard.py` ist die Kadenz-SSOT und zählt je Publikationstag die
Live-Artikel (`draft: false`, `date` ⊆ Mo/Mi/Fr). Der Lauf am 13.10.2026 um
09:36 UTC meldete für zehn Tage `(unter Min)` statt nur den 05.10. zu zeigen:

```
⚠️ 2026-08-12: nur 1 Posts (Min 2) – Fallback-Slots heilen nach.
⚠️ 2026-08-17: nur 1 Posts (Min 2) – Fallback-Slots heilen nach.
… sowie 26.08., 28.08., 04.09., 21.09., 23.09., 28.09., 30.09., 05.10. (je 1)
```

Der elfte Fehltag — **Montag 31.08.2026, null Live-Artikel** — stand in dieser
Liste **nicht**, und das ist der eigentliche Befund: Die Wache bewertet nur
Tage, an denen überhaupt ein Post liegt (`by_day`); ein Publikationstag ohne
jeden Artikel existiert für sie nicht und kann deshalb auch nicht warnen.
Gefunden wurde er durch den Abgleich des Publikationskalenders (jeder Mo/Mi/Fr)
gegen die tatsächlich vorhandenen Artikelverzeichnisse. Ein Tag, an dem
*nichts* erscheint, ist schlimmer als ein Tag mit der Hälfte — und war der
einzige, den die Wache strukturell nicht sehen konnte.

### Warum das so lange unbemerkt blieb (Befund, nicht Ausrede)

`--check` beendet einen Lauf mit Defizit-Tagen **mit Exit 0** und der
Botschaft „Fallback-Slots heilen nach“. Das ist für den laufenden Tag richtig
gedacht (die Engine füllt selbstständig auf), hat aber eine stille Kehrseite:
Ein Defizit, das nie von einem Fallback-Slot geheilt wurde, bleibt im Bestand
stehen und fällt in **keinem** Gate hart auf — genau das ist hier elfmal
passiert. Der Befund ist deshalb Teil dieses Berichts (siehe *Offen*), die
Semantik der Wache wurde bewusst **nicht** einseitig geändert (siehe *Was
bewusst nicht getan wurde*).

Der Montag 31.08.2026 war der härteste Einzelfall: **null** Live-Artikel, auch
kein Nachrücker. Da `date`-Werte nachträglich nicht umdatierbar sind, wurden
beide Artikel korrekt auf den **Publikationstag 31.08.** datiert (06:10 UTC,
Haupt-Slot) und tragen `lastmod`/`faktencheck` = 13.10.2026 — der Tag, an dem
sie tatsächlich recherchiert und geprüft wurden. Das ist die ehrliche
Zeitachse: Publikationsdatum = Slot, Prüfdatum = Arbeitstag.

---

## Die Lieferung (zwölf Artikel, elf Tage)

Alle Angaben aus dem jeweiligen Werkzeug, nicht aus dem Gedächtnis
(`length_policy.measure`, `faktenfrische.geo_reife`, `check_covers.py`).
„GEO“ = erreichte GEO-Reifepunkte von 6 (Kurzantwort, FAQ, Quellen, Zahlen,
Tabelle, Faktencheck).

| Publikationstag | Nachlieferung (Slug) | Zeichen | Wörter | GEO | Themenwelt |
|---|---|---|---|---|---|
| Mo 12.08. | `2026-08-12-geld-abheben-im-ausland-gebuehren-vermeiden` | 13.425 | 1.893 | 6/6 | konto-karten |
| Mo 17.08. | `2026-08-17-abos-und-vertraege-stiller-posten-haushaltsplan` | 12.375 | 1.755 | 6/6 | frugalismus |
| Mi 26.08. | `2026-08-26-warmwasser-sparen-rechnung-hinter-dem-hahn` | 13.112 | 1.864 | 6/6 | strom-sparen |
| Fr 28.08. | `2026-08-28-lastschrift-und-dauerauftrag-abbuchungen-pruefen` | 12.986 | 1.837 | 6/6 | konto-karten |
| Mo 31.08. | `2026-08-31-nachtstrom-tarife-wann-sich-ein-doppeltarifzaehler-noch-lohnt` | 12.900 | 1.771 | 6/6 | strom-sparen |
| Mo 31.08. | `2026-08-31-stoerung-beim-internetanbieter-so-sicherst-du-deine-rechte` | 12.992 | 1.788 | 6/6 | internet-dsl |
| Fr 04.09. | `2026-09-04-umzug-mit-internet-anschluss-und-rufnummer-mitnehmen` | 12.897 | 1.770 | 6/6 | internet-dsl |
| Mo 21.09. | `2026-09-21-grundversorgung-strom-und-gas-was-sie-leistet` | 12.885 | 1.739 | 6/6 | strom-sparen |
| Mi 23.09. | `2026-09-23-einlagensicherung-wie-viel-guthaben-geschuetzt-ist` | 12.487 | 1.658 | 6/6 | konto-karten |
| Mo 28.09. | `2026-09-28-zaehlerstand-ablesen-und-melden-schaetzwerte-vermeiden` | 12.479 | 1.731 | 6/6 | strom-sparen |
| Mi 30.09. | `2026-09-30-grosseinkauf-und-vorrat-wann-bevorraten-sich-rechnet` | 12.490 | 1.760 | 6/6 | frugalismus |
| **Mo 05.10.** | `2026-10-05-erster-eigener-haushalt-fixkosten-richtig-ordnen` | 12.754 | 1.760 | 6/6 | frugalismus |

**Längenband:** 12.375–13.425 Zeichen — alle im Optimum (12.000–18.000), keiner
an der Untergrenze. Drei Artikel lagen nach dem ersten Lauf knapp unter dem
Optimum (u. a. 21.09. mit 11.838) und wurden um je einen Fachabschnitt
erweitert, statt sie mit Fülltext zu strecken.

### Was jeder Artikel inhaltlich mitbringt (Stichprobe: 05.10.)

- **Kurzantwort-Box** (Frontmatter `kurzantwort`, gerendert als Antwortbox im
  Artikelkopf über `layouts/_partials/artikel_einzeln.html`) — zitierfähig für
  AI-Antwortmaschinen.
- **`## Häufige Fragen`** mit echten Leserfragen, nicht mit Keyword-Fragen.
- **Mindestens eine Tabelle** mit den entscheidenden Zahlen (im Artikel:
  Wohnen 620 Euro · Energie/Strom 55 Euro · Verträge und Dienste 80 Euro ·
  Alltag und Rücklagen 340 Euro).
- **Ausgewiesene Annahmen** in jedem Rechenbeispiel („Annahme: 0,30 €/kWh“,
  „Beispiel, keine Prognose“) — der Leser kann jede Zahl nachrechnen.
- **Belegkette** im Frontmatter (`quellen:`) ausschließlich aus der
  Agent-Reach-Allowlist (z. B. Bundesnetzagentur, Verbraucherzentrale, Destatis,
  BDEW, TKG §§ 56/59), 3–4 Quellen je Artikel, kein Affiliate als Beleg.
- **`faktencheck`** = 13.10.2026 (Arbeitstag) und `risikoklasse` je Artikel.
- **Offenlegung**: sichtbarer Satz „*Dieser Artikel enthält Affiliate-Links
  (Werbung) … keine Mehrkosten*" + artikelgenaue Offenlegung/Trust-Box aus dem
  Layout-Partial, `/go/`-CTAs im Schnell-Tipp-Block.
- **Weiterlesen-Inlinks** auf passende Bestandsartikel (kein Link auf sich
  selbst, keine toten Ziele — `link_guard.py` grün).

### Cover

Jeder der zwölf Artikel hat ein eigenes Cover (1000×1500) plus neun responsive
Varianten inklusive **AVIF**. Die AVIF-Varianten der acht zuletzt gelieferten
Cover fehlten zunächst, weil `pillow-avif-plugin` in der Umgebung nicht
installiert war; nach der Installation hat der Generator sie nachgezogen:

```
Cover-Check: 94 Covers | Probleme: 0 | Stale: 0 | Brand: 0 | Text: 0
```

---

## Redaktionelle Nacharbeit im selben Zug

Ein Nachlieferungs-Lauf, der neue Artikel schreibt, aber bestehende Mängel
stehen lässt, wäre halbe Arbeit. Mitgeheilt:

1. **`seo_audit`: 7× Description über 165 Zeichen** (26.08. 167 · 31.08. Nachtstrom
   174 · 31.08. Störung 167 · 04.09. 166 · 21.09. 168 · 05.10. 175 ·
   `pin_description` 04.09. 214) → alle auf 137–158 Zeichen gekürzt, Regeln
   TITLE 30–65 / DESC 70–165 damit wieder für **alle** Artikel erfüllt.
2. **09-24: sechs angeklebte Absätze von Überschriften getrennt** („### Fehler 1:
   … schauen Mehr ist nicht automatisch besser." → Überschrift + Absatz). Die
   automatische Heilung (`--split-headglue`) trennt nur eindeutige Fälle; diese
   sechs waren mehrdeutig und wurden von Hand an der richtigen Naht getrennt.
   Danach: `casing_guard` erstmals ohne jeden Befund.
3. **`faktencheck`/`lastmod` ehrlich gesetzt**: alle zwölf Nachlieferungen
   tragen Prüf- und Änderungsdatum 13.10.2026 (`set_lastmod`, sonst hätte die
   Faktenfrische-Wache vier Artikel (12.08./17.08./26.08./28.08.) sofort als
   überfällig geführt — 62/57/48/46 Tage).
4. **`fix_spaces`-Vollrun** (NBSP vor `%`/`€`): 59 Korrekturen in 9
   Bestandsdateien, Diffs vor dem Commit gesichtet.

---

## Belege

Alle Wachen über den **gesamten** Bestand, Lauf vom 13.10.2026:

```
Titel-Check: 94 Titel | Verstöße: 0
Casing-Guard: 🎉 keine Befunde – Groß-/Kleinschreibung sauber.
Dash-Guard: 🎉 Alle geprüften Artikel sind strich-typografisch sauber (Duden-Level).
FM-Grenzen: ✅ 123 Dateien – kein Schlüssel doppelt, YAML-konform.
Duplikat-Audit: 88 Artikel | D1 0 · D2 0 · D3 0 · D4 0 · D5 0 · D6 0
check_uniqueness: Pin-Konflikte 0 | Kritisch (live↔live) 0 | Same-Day-Twins 0 ✅
cadence_guard --check: ✅ nur Mo/Mi/Fr, 0 Off-Day, 0 Over-Cap, kein Defizit
seo_audit: 0 Probleme in 56 Artikeln → Alles auf Profi-Niveau (Exit 0)
check_length: 56 Artikel | ok 47 | unter-Optimum 9 (Altbestand) | zu-kurz 0 | zu-lang 0
affiliate_profi_check: ✅ (keine Befunde an Live-Artikeln; A3 nur an 3 Entwürfen, s. Offen)
link_guard: 🎉 Alle internen Links verifiziert – keine Totstellen.
heading_anchor_guard: 36/36 Prüfungen bestanden ✅
check_covers: 94 Covers | Probleme: 0 | Stale: 0 | Brand: 0 | Text: 0
faktenfrische --offline (ganzer Bestand): 94 Einträge | 3 fällig – alle drei sind
  Engine-Entwürfe (08.10., 09.10., 12.10., Erstrecherche); die 12 Nachlieferungen
  sind 0 fällig und stehen bei GEO-Reife 100 % (Bestands-Schnitt inkl. Entwürfe: 92 %)
```

**Nicht lokal lauffähig (ehrlich benannt):** `publish_gate`,
`offenlegung_gate` (O1–O7) und die Render-Teile von `seo_audit` /
`affiliate_integrity_gate` brauchen einen Hugo-Build (`hugo --minify`). Ein
Hugo-Binary ist in dieser Umgebung nicht beschaffbar (kein Go; GitHub-Release-
Assets sind gesperrt — `hugo-bin`-Pakete laden ihr Binary genau von dort). Die
Kette bis zur Build-Grenze ist vollständig grün; die Build-Stufe läuft wie
immer in CI. Das ist eine Umgebungsgrenze, kein offener Mangel am Inhalt.

**CI-Nachweis auf dem Branch (Pull Request #725):** Der Push hat die
Server-Gates gestartet; grün sind **Qualitäts-Gate (Build + interne Links:
Hugo-Build-Vertrag → Build → `check_internal_links.sh`)**, E2E-Tests
(Playwright, Desktop + Mobile), Themenwelten (Navigation & Darstellung),
Lesehilfen-Gate, Beweis-Gate, Daten- und Visualisierungs-Gate, CodeQL
(JS + Python), Integritäts-Lock, Klartext-Wache, URL-Wache, „Quellen, Stand,
Einheit und Methodik" und auto-assign. Damit ist genau die Stufe belegt, die
lokal nicht laufen kann: **das gebaute HTML** — inklusive interner Links.
`automerge` wird bewusst übersprungen. Zum Berichtszeitpunkt lief die
„Publication reliability regression tests"-Suite noch.

**Was in CI bewusst noch nicht lief:** `publish_gate.py` — und damit sein
Schritt 6, das `offenlegung_gate` (O1–O7 gegen `public/`) — hängt in
`deploy.yml` und läuft erst beim Push auf `main`. Lokal unmöglich (Hugo),
auf dem Branch nicht Teil der PR-Checks; die Offenlegung ist deshalb hier
über die Quelltexte (Layout-Partial, Artikeltext, `/go/`-Register) belegt,
nicht über gerendertes HTML.

---

## Was bewusst **nicht** getan wurde

- **Keine Entwürfe angefasst.** Die Entwurfs-Cluster (12.10., 07.10., 09.10.,
  06.10.) und der zurückgehaltene Wohngebäude-Kandidat vom 31.08.
  (`park_state` „manual", `draft: true`) bleiben unberührt — sie sind
  Redaktions-Entscheidungen, keine Fehlstellen.
- **Keine Gate-Semantik eigenmächtig geändert.** Dass `cadence_guard --check`
  bei Defizit-Tagen mit Exit 0 endet, ist ein Befund mit Repo-Historie
  (Fallback-Slots heilen nach) und gehört als Entscheidung dem Betreiber —
  siehe *Offen*.
- **Keine erfundenen Fakten, keine erfundenen Quellen.** Jede Zahl hat eine
  Quelle aus der Allowlist oder ist als Annahme gekennzeichnet; wo ein Wert
  nicht belegbar war, steht eine Spanne („11–13 € pro Monat“).
- **Kein Datum frisiert.** `date` bleibt der jeweilige Publikationstag,
  `lastmod`/`faktencheck` stehen auf dem echten Arbeitstag.
- **Kein Masse-statt-Klasse-Deal.** Zwölf Artikel in einem Zug sind nur
  vertretbar, weil jeder die volle Kette (Recherche → Quellen → GEO-Kriterien →
  Gates) durchlaufen hat — nachweisbar oben je Artikel.

## Offen (bewusst liegengelassen, mit Besitzer)

1. **`cadence_guard --check` und Fehltage**: Vorschlag zur Entscheidung —
   (a) Publikationstage **ohne jeden Post** überhaupt erst bewerten (heute
   unsichtbar, siehe *Befund im Detail*), (b) Exit 1 bei Defizit-Tagen, die
   älter als N Tage sind (vorher greift die bestehende Engine-Nachfüllung).
   Ohne diese Entscheidung kann ein Fehltag erneut still stehen bleiben.
2. **Drei Engine-Entwürfe mit 0 internen Links** (`affiliate_profi_check` A3):
   08.10., 09.10., 12.10. — Entwürfe, kein Live-Risiko; vor Veröffentlichung
   heilen.
3. **Neun Live-Artikel im Altbestand unter dem Längenoptimum** (11.203–11.888
   Zeichen, u. a. 02.10. und 30.09.): inhaltlich vollständig, aber unter
   12.000 — Kandidaten für die nächste Qualitäts-Runde, kein Kadenzthema.
4. **Build-Stufe**: In PR #725 ist der **Hugo-Build inklusive interner Links**
   grün nachgewiesen; `publish_gate`/`offenlegung_gate` laufen erst im
   `deploy.yml` auf `main` (und sind lokal nicht reproduzierbar, siehe Belege).
   Offen bleibt auf dem Branch nur die `regression`-Suite.

## Bedienung / Reproduktion

```bash
# Fehlstellen finden (SSOT)
python3 scripts/cadence_guard.py --check

# Nachlieferung einzeln prüfen
python3 scripts/check_length.py --file content/posts/<slug>/index.md
python3 scripts/faktenfrische.py --offline --file content/posts/<slug>/index.md

# Cover + Varianten (inkl. AVIF) und Manifeste
python3 scripts/generate_covers.py && python3 scripts/check_covers.py

# Stand ehrlich setzen und alles abnehmen
python3 scripts/set_lastmod.py --git-changed
python3 scripts/casing_guard.py && python3 scripts/dash_guard.py \
  && python3 scripts/fm_boundary_guard.py && python3 scripts/check_titles.py \
  && python3 scripts/seo_audit.py && python3 scripts/affiliate_profi_check.py \
  && python3 scripts/link_guard.py
```

**Geänderte Dateien (Commits `00ce426` + `861c8cd`, zusammen 235 Dateien):**
12 neue Artikel (Markdown) plus 195 Cover-Dateien (JPG + neun Varianten +
AVIF), die Cover-Manifeste (`data/covers_manifest.json`, `data/lcp_images.json`,
`data/fcp_images.json`), 6 Description-Fixes, 1 HeadGlue-Heilung (09-24),
`lastmod`/`faktencheck` in 12 Artikeln, die Gate-Historien/Audit-Daten
(`data/audit/`, `data/*_history.jsonl`, `data/faktenfrische_queue.json`,
`data/research/artikel/`) und dieser Bericht. Die generierten `*-REPORT.md`
(u. a. `CADENCE-GATE-REPORT.md`, `FAKTENFRISCHE-REPORT.md`) sind per
`.gitignore` lokal und werden nicht versioniert.

_Werkzeuge sind die Wahrheit: Jede Zahl dieses Berichts stammt aus einem Lauf
über den Bestand vom 13.10.2026, nicht aus einer Zusammenfassung._
