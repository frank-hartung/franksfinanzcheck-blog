# GSC #1097: Das Kriterium heilt sich selbst

**Vorgang:** GSC-Leistungsdaten 2026-11-06 (#1097) · „Bitte dauerhaft auf
Highend-Level einer Profi-Agentur beheben mit automatischer Selbstheilung“
**Stand:** 06.11.2026 · Lauf `42221350309` (12:55 UTC) · Branch
`automation/gsc-tagesdaten-20261106` (PR #1097)
**Vorherige Wahrheit:** `GSC-FEHLERHEILUNG-HIGHEND-2026-11-01.md`,
`GSC-ABDECKUNG-HIGHEND-2026-10-26.md`

---

## 1 · Das Ergebnis in vier Sätzen

Der Tageslauf vom 06.11.2026 hat einen Befund gemeldet, den der Vortag noch
mit ✅ geführt hatte: **zwei Live-Artikel ohne einen einzigen redaktionellen
Inlink**. Die Ursache ist belegt – die Reserve-Automatik stellte die beiden
Artikel um **02:30/02:31 UTC** live, der Lauf um 12:55 UTC maß sie, und der
danach berechnete Verlinkungsauftrag wurde wie an jedem Tag **von niemandem
ausgeführt**: `--apply` war ein Handbefehl. Diese Sitzung heilt den Bestand
(4 Links, 2 Inseln → 0) **und** die Ursache: `--verlinkung --heilen` läuft
jetzt im Tageslauf **vor** der Messung, prüft vor jedem Eingriff drei harte
Sperren, belegt jeden Link und misst danach nach. Bleibt ein Befund offen,
sagt der Lauf das – statt ihn zu verschweigen oder zu erfinden.

| Kennzahl | vorher (PR #1097) | jetzt (dieser Branch) | Quelle |
|---|---|---|---|
| Inhaltsseiten ohne redaktionellen Inlink | **2** | **0** | `gsc_abdeckung.py --audit` |
| Abnahme-Kriterium „Seiten ohne redaktionellen Inlink“ | 🛑 2 Seiten | ✅ 0 Seiten | `--abnahme` |
| Eingefügte redaktionelle Links | 0 (Auftrag: 5 Paare) | 4 (1 Paar war schon erfüllt) | `data/verlinkung_history.jsonl` |
| Beleg je Eingriff | – | 4 Zeilen, append-only | dito |
| Selbstheilung im Tageslauf | nein (Handbefehl) | **ja, vor der Messung** | `.github/workflows/gsc-import.yml` |
| Selbsttest der Abdeckungs-Zentrale | 99 Fälle | **111 Fälle** | `--selftest` |
| Regressionstests | 85 | **104** (+19) | `scripts/tests/test_gsc_abdeckung.py` |

---

## 2 · Befund: was #1097 wirklich gemeldet hat

Der PR selbst ist unauffällig – ein Tag Daten (2026-11-03) und die
Top-Listen. Der Befund steckt in der **Abnahme**, die derselbe Lauf schreibt:

```
data/gsc/abdeckung/befund.md (Branch automation/gsc-tagesdaten-20261106)
| Seiten ohne redaktionellen Inlink | 30 Tage | 🛑 | 2 Seiten |
| 2 von 84 Inhaltsseiten ohne redaktionellen Inlink, … |
```

`main` (Lauf vom 05.11.2026) sagt für dieselbe Zeile:

```
| Seiten ohne redaktionellen Inlink | 30 Tage | ✅ | 0 Seiten |
| 0 von 82 Inhaltsseiten ohne redaktionellen Inlink, … |
```

Zwei Seiten mehr, zwei Inseln. Die betroffenen Artikel:

| Artikel | live seit | Frontmatter | Inlinks |
|---|---|---|---|
| `2026-10-12-energieausweis-was-das-dokument-fuer-deine-fixkosten/` | 2026-11-06 02:30:25 UTC | `draft: false`, `reserve_published: 2026-11-06`, `engine_level: draft` | 0 |
| `2026-10-28-oekostrom-anbieter-wechseln-sicher-gruen-und-bezahlbar/` | 2026-11-06 02:31:24 UTC | `draft: false`, `reserve_published: 2026-11-06`, `engine_level: draft` | 0 |

Beide tragen `redaktionelle_pruefung.status: "ausstehend"` – sie sind
automatisch veröffentlicht worden. Genau dafür gibt es den
Verlinkungsauftrag: `scripts/gsc_abdeckung.py --verlinkung` hatte für den
Lauf **5 Quelle-Ziel-Paare** berechnet und nach
`data/gsc/abdeckung/verlinkungsauftrag.json` geschrieben.

### 2.1 Die eigentliche Ursache

```
.github/workflows/gsc-import.yml (bis 06.11.2026)
  - name: Anfrage-Priorität und Verlinkungsauftrag berechnen
    run: python3 scripts/gsc_abdeckung.py --verlinkung   # ohne --apply
```

Der Auftrag wurde jeden Tag neu geschrieben, ausgeführt von niemandem.
`--apply` stand nur als `npm run gsc:verlinken` bereit – ein Handbefehl, den
niemand kannte. Die Abnahme verlangt seit dem 26.10.2026 „keine Inhaltsseite
ohne redaktionellen Inlink“; die Heilung dazu war vorhanden, aber **nicht
verdrahtet**. Ein Kriterium, das sich täglich neu rot misst und dessen
Heilung niemand anstößt, ist keine Wache, sondern eine Warteschlange.

Verschärfend: Die Veröffentlichung selbst kennt keine Inlink-Pflicht.
`reserve_pool.publish_one()` setzt `draft: false`, Datum und
`reserve_published` – und sonst nichts. Wer live geht, geht ohne Nachbar ins
Netz; der nächste Tageslauf sieht es 10 Stunden später.

---

## 3 · Heilung des Bestands (mit Beleg, ohne Erfindung)

`python3 scripts/gsc_abdeckung.py --verlinkung --heilen` – Auswahl aus dem
Auftrag, drei Sperren, Beleg, Nachmessung:

| Quelle (live) | Ziel | Vorher | Nachher | Beleg |
|---|---|---|---|---|
| `2026-09-21-grundversorgung-strom-und-gas-was-sie-leistet/` | Energieausweis | 0 Inlinks | 2 | `data/verlinkung_history.jsonl` |
| `2026-08-24-preisgarantie-gas-so-schuetzt-du-dich-vor-preisspruengen/` | Energieausweis | 0 | 2 | dito |
| `2026-08-31-nachtstrom-tarife-wann-sich-ein-doppeltarifzaehler-noch-lohnt/` | Ökostrom | 0 | 2 | dito |
| `2026-08-12-preisgarantie-gas-so-sicherst-du-dir-guenstige-tarife-fuer-2026/` | Ökostrom | 0 | 2 | dito |
| `2026-09-30-last-minute-urlaub-…/` | Flugvergleich | – | – | verweigert: „Ziel steht bereits im Artikel“ |

Der Eingriff ist **eine Zeile je Quelle**: die kuratierte
`**Weiterlesen:**`-Zeile, dort **vor** einem vorhandenen `**Lesetipp:**`.
Kein Fließtext, keine neue Aussage, keine Zahl. Nach der Heilung:

```
ohne_inlink 0   inhaltsseiten 84   median_auslink 6
```

Die Goldkorridor-Zählung (`link_density_guard.py`) bleibt bei 88 % im
Korridor; alle vier Quellen liegen danach bei 5–8 von maximal 9 internen
Post-Links.

---

## 4 · Dauerheilung: was jetzt automatisch passiert

### 4.1 Ein Modus, der heilt und nachmisst (`--verlinkung --heilen`)

Neu in `scripts/gsc_abdeckung.py`:

| Schritt | Was passiert | Warum |
|---|---|---|
| MESSEN | Inhaltsseiten mit 0 Inlinks, Zahl der Paare | Die Zahl kommt aus dem Bestand, nicht aus einer Liste |
| AUFTRAG | `verlinkungs_auftrag()`: gleicher Pillar → ähnlicher Slug → meiste Ausgänge | Nachvollziehbare Auswahl, keine Blackbox |
| PRÜFEN | YMYL-Siegel, Freigabe-Status, Quelldatei, Goldkorridor (≤ 9) | Eine Heilung darf nie mehr kaputt machen als der Befund |
| SCHREIBEN | nur `**Weiterlesen:**`, vor `**Lesetipp:**`; `--max` begrenzt | Stilkonform, im Diff prüfbar, kein Umbau |
| BELEGEN | `data/verlinkung_history.jsonl`, append-only | Jeder Eingriff hat Quelle, Ziel, Grund, Zeitstempel |
| NACHMESSEN | Befund wird neu erhoben; `offen` ist die Wahrheit | „4 eingefügt“ ist keine Wirkung – „0 offen“ ist eine |

Drei Ausgänge, drei Bedeutungen – und keiner lügt:

* **Exit 0** – Befund geschlossen (`status: geheilt`) oder nichts zu tun (`sauber`).
* **Exit 1** – es bleibt offen (`status: offen`/`teilweise`). Dann fehlt ein
  heilbarer Kandidat im Bestand, und die Redaktion entscheidet – nicht der Bot.
* **`--wache`** – derselbe Lauf als Trockenlauf: prüft und wählt aus,
  schreibt nichts, Exit 1, wenn der **Ist-Zustand** befallen ist.

### 4.2 Der Tageslauf heilt vor der Messung

In `.github/workflows/gsc-import.yml` steht die Heilung jetzt zwischen Build
und Abdeckungsprüfung. Damit gilt: **Der Bericht eines Laufs misst den
geheilten Zustand**, nicht den Zustand von vor drei Minuten. Der Schritt

* ist auf `--max 10` begrenzt (kein Umbau in einem Lauf),
* schreibt eine Tabelle (vorher · eingefügt · nachher · Status) in die
  Lauf-Zusammenfassung,
* macht einen Rest-Befund zur **Warnung**, nicht zum roten Lauf (der
  Datenimport hat Vorrang),
* nimmt `content/` und `data/verlinkung_history.jsonl` in den PR auf – sonst
  bliebe die Heilung im Runner liegen und der nächste Lauf meldete denselben
  Befund.

Der Wochenlauf (`gsc-abdeckung-woche.yml`) heilt bewusst **nicht** mit: kein
zweiter Schreiber auf `content/`. Er misst montags mit `--wache` und warnt,
wenn der Tageslauf es nicht geschafft hat.

### 4.3 Die Wache über den Bestand

`scripts/tests/test_gsc_abdeckung.py::BestandOhneInseln` prüft den **echten**
Bestand: keine Inhaltsseite ohne eingehenden, keine ohne ausgehenden
redaktionellen Link. Wer künftig eine Seite live stellt, ohne sie zu
verlinken, sieht sie dort rot – fail-closed, mit dem Heilbefehl in der
Meldung. Der Test schreibt nicht (Hausregel C15); geheilt wird im Tageslauf.

---

## 5 · Nebenbefund: die Kandidatenauswahl fragte die Gegenrichtung

Beim Bau der Tests fiel eine zweite Stelle auf, die den Heiler schwächte:

```python
# vorher (falsch)
if ziel in (info.get("quellen") or []):
    continue
```

`info["quellen"]` sind die **Inlinks** einer Seite. Die Zeile prüfte also
„verlinkt das *Ziel* die *Quelle*?“ – und warf damit genau die thematisch
nächsten Nachbarn weg, nämlich jede Quelle, die das Ziel selbst schon
verlinkt. Gefragt ist das Gegenteil:

```python
# jetzt
if quelle in (seiten.get(ziel, {}).get("quellen") or []):
    continue
```

Wirkung: Der Auftrag findet wieder Kandidaten, statt sie zu verwerfen; ein
doppelter Link wird weiterhin von `link_einfuegen()` verhindert (und der
Tageslauf heilt in Runden, bis der Befund leer ist). Eingefroren in
`test_heilung_konvergiert_ohne_doppelte_links`.

---

## 6 · Prüfungen, die dieser Branch bestanden hat

| Prüfung | Ergebnis |
|---|---|
| `python3 scripts/gsc_abdeckung.py --selftest` | ✅ 111 Fälle (12 neu: K86–K92) |
| `python3 -m unittest scripts.tests.test_gsc_abdeckung` | ✅ 104 Tests (19 neu) |
| `python3 scripts/gsc_abdeckung.py --verlinkung --wache` | ✅ Exit 0 (kein Befund mehr) |
| `python3 scripts/redos_guard.py` (Alert Nr. 87) | ✅ 737 Dateien, 0 Funde |
| `python3 -m unittest scripts.tests.test_redos_security` | ✅ 14 Tests |
| `python3 scripts/link_density_guard.py` | ✅ 88 % im Goldkorridor, keine neue Überladung |
| `python3 scripts/gsc_artefakte_guard.py --check` | ✅ vier Dateien gültig und passend |
| Workflow-YAML (`gsc-import.yml`, `gsc-abdeckung-woche.yml`) | ✅ parsebar, 21 bzw. unveränderte Schritte |
| `python3 scripts/linktext_wache.py --selftest` | ✅ L1/L2/L4 scharf |

Zwei Härtungen am Schreibweg gehören dazu: Ein Artikel, der nicht
verlustfrei als UTF-8 gelesen werden kann, wird **nicht** angefasst (ein
`errors="replace"` plus Zurückschreiben wäre stiller Datenverlust), und
geschrieben wird atomar über eine Nebendatei + `replace` – ein Abbruch mitten
im Schreiben hinterlässt nie einen halben Artikel. Beides ist eingefroren in
`SchreibenOhneDatenverlust`.

Der YMYL-Pfad ist **nicht** mitgelaufen: `editorial_review_gate.py` braucht
PyYAML, das in dieser Umgebung fehlt. Die Sperre ist deshalb doppelt gebaut –
`schreibgeschuetzt()` liest das Prüfprotokoll zeilenweise ohne YAML und ohne
mehrzeiliges Regex; ein Test friert Status/Siegel/leeren Hash ein. Der
CI-Lauf installiert die gepinnten Requirements und prüft zusätzlich
`ymyl_siegelwache`.

---

## 7 · Grenzen und der nächste offene Punkt

* **Die Sperre schützt nur, was sie kennt.** Ein Artikel mit
  `redaktionelle_pruefung.status: ausstehend` (wie die beiden neuen) gilt
  nicht als freigegeben und darf automatisch verlinkt werden. Das ist
  gewollt: Der Link ist eine Verknüpfung, keine Aussage.
* **Kein heilbarer Kandidat = roter Befund.** Wenn ausschließlich gesperrte
  Quellen in Frage kommen, bleibt die Insel stehen. Dann ist die
  Entscheidung der Redaktion – der Lauf sagt das mit Exit 1 und einer
  Warnung, statt einen Link zu erfinden.
* **Die Veröffentlichung selbst verlinkt weiterhin nicht.** Die Heilung
  greift im Tageslauf, also bis zu ~10 Stunden nach der Promotion. Der
  saubere Ort wäre `reserve_pool.publish_one()` – dort aber schreibt die
  Reserve-Strecke nur Pool-Pfade (`reserve_stage_guard.py`); ein Link in
  einen fremden Artikel würde beim Staging wieder herausgenommen. Dieser
  Schritt braucht einen eigenen Auftrag und einen eigenen Test.
* **Nebenbefund ohne Heilung (bewusst):** `data/gsc/meta.json` behauptet
  `zeitraum.von: 2026-08-05`, der Tagesledger beginnt am **2026-09-20** –
  46 Tage Differenz. `gsc_artefakte_guard.py` (G4) prüft nur das obere Ende
  („`bis` nicht hinter dem letzten Tag“). Wer aus dem Kopf eine Tagesrate
  rechnet, rechnet 46 Tage zu niedrig. Das ist eine eigene Entscheidung
  (Fenster vs. Abdeckung im Kopf), deshalb hier nur benannt: Messweg
  `python3 - <<'PY'`-Einzeiler im Bericht von #1097, Behebung im nächsten
  Datenintegritäts-Auftrag.
