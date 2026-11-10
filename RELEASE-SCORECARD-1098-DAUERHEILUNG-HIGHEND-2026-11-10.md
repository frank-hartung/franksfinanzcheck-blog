# Release-Scorecard #1098 – Dauerheilung der Produktionswahrheit (10.11.2026)

**Auftrag:** „Bitte dauerhaft auf Highend-Level einer Profi-Agentur beheben.“
**Ausgangslage (Ticket-Kopf, Lauf 42824227898):** 46/80 freigabe-reif · **32 blockiert** ·
2 Warnungen. Blockierend: `T6-textverstaendnis` (20), `F4-fachbefund` (21),
`T1w-zeichenlaenge-optimum` (4, SSOT: Warnung) und `T2-seo-audit` (1).

---

## 1. Was wirklich rot war (Befund, nicht Vermutung)

### 1a. Der Erzeuger zerlegte Dateinamen – 20 Artikel

Alle 20 `T6`-Blocker hatten exakt denselben Fehler:

```
![Merkkarte: Kernaussagen zu …](abbildung-merkkarte. svg)   ← R8-URL-LEERZEICHEN
![Merkkarte: Kernaussagen zu …](abbildung-merkkarte.svg)    ← zweite, heile Zeile
```

Die Ursache ist nicht der Guard, sondern `scripts/fix_spaces.py` (Regel D:
„fehlendes Leerzeichen nach .!?“). Die Schutzzone der Regel deckte nur
`http(s)://`-URLs ab. Ein relatives Markdown-Ziel wie `abbildung-merkkarte.svg`
ist aber keine http-URL – Regel D setzte den Punkt in „Dateiname → Dateiname. “
um. Belegt über die Commit-Kette:

| Commit | Wirkung |
|---|---|
| `a5586fbe` (28.10.) | heil → kaputt (SEO-Lauf) |
| `3a3c59a3` (28.10., PR #931) | kaputt → heil (Reparatur) |
| `0019dbc5` (04.11.) | heil → kaputt |
| `c5ea4970` (05.11.) | kaputt → heil |
| `ef8085a7` (09.11.) | heil → kaputt |

Die Reparatur hielt jeweils genau bis zum nächsten Automatiklauf. **Ein Defekt,
der seine eigene Heilung auffrisst, ist kein Schönheitsfehler.**

### 1b. Der Heiler verdoppelte die Zeile

`scripts/abbildungen_ableiten.py` erkannte über `BILD_RE` nur die **heile**
Zeile. Die zerlegte Zeile galt damit als „Abbildung fehlt“; der Nachzug fügte
eine zweite, heile Zeile ein, statt die kaputte zu ersetzen. Aus einem
Schönheitsfehler wurden zwei – einer davon hart blockierend.

### 1c. Der Ledger band Entscheidungen an Leerzeilen – F4-Kreislauf

`F4` ist per SSOT menschlich. Die 77 offenen Live-Befunde sind aber zu **72**
bereits am 04./07.11.2026 vom Herausgeber entschieden worden. Sie standen wieder
offen, weil `text_hash` (Projektion `betrieb-v2`) die **Anzahl der Leerzeilen**
mitgehasht hat. Ein abgeleiteter Abbildungsblock belegt Leerzeilen; wurde er
nachgezogen oder entfernt, änderte sich der Hash – ohne einen geänderten Satz.
Genau derselbe Fehler wie bei den Betriebsflächen (#1072), eine Ebene tiefer.

---

## 2. Was dauerhaft geändert wurde

### 2a. `scripts/fix_spaces.py` – Schutzzonen statt Schönheitskorrektur

Vor **allen** Regeln werden jetzt tokenisiert:

* Markdown-Ziele `](…)` (Bilder, Links, `/go/`-Routen),
* HTML-Attribute `src`/`href`/`srcset`/`poster`,
* bare URLs,
* Dateinamen mit echter Endung (svg, png, pdf, md, json …).

Die Token (`§Z0§`) enthalten weder Punkt noch Leerzeichen; keine Leerzeichen-
Regel kann sie treffen. Prosa wird weiter geheilt (`Satz.Neuer` →
`Satz. Neuer`), Abkürzungen bleiben geschützt. Der Selbsttest wuchs von 40 auf
**62 eingefrorene Fälle**.

### 2b. `scripts/abbildungen_ableiten.py` – eine Zeile, kanonisch

* `BILD_ANY` erkennt **jede** Fassung des Ziels (Punkt mit beliebigem Leerraum,
  `%2e`) – geschrieben wird immer `![…](abbildung-merkkarte.svg)`.
* `_entferne_doppelte_bildzeilen()` lässt genau eine Zeile stehen und entfernt
  die zugehörige Unterschrift der Doppelzeile; der zweite Lauf ändert nichts.
* `--check` prüft jetzt **Anzahl** und **Kanonik** der Bildzeile sowie zerlegte
  URLs außerhalb der Bildzeile. Vorher genügte `name in body` – eine heile
  Zeile tarnte die kaputte.

### 2c. `scripts/fix_url_hygiene.py` – Datei-URLs heilbar

Der Heiler löste bisher nur Post-Slugs auf. `heal_asset_url()` heilt eine
relative Datei-URL (`abbildung-merkkarte. svg`) **nur dann**, wenn die Datei
ohne die Leerzeichen im selben Ordner nachweislich existiert. Kein Raten.

### 2d. `scripts/faktenfrische.py` – der Prüfer sieht die eigene Belegkette

Die KI-Fachprüfung bekam nur die frischen Recherche-Fundstellen. Eine Aussage,
die der Artikel selbst mit `laut BDEW` belegt und im Frontmatter führt, war für
den Prüfer „ohne Quellenangabe“. Jetzt:

* `eigene_belegkette()` liest `quellen` aus dem Frontmatter und übergibt sie als
  eigenen Prompt-Block mit der Regel: **eine dort gedeckte Aussage ist keine
  Beleglücke**.
* Jeder Befund muss in `stelle` den betroffenen Satz **wörtlich** aus dem
  Artikeltext nennen. `claude_antwort_pruefen()` vergleicht den Anker
  mechanisch (markdown-normalisiert, ≥ 12 Zeichen) und verwirft Befunde ohne
  Fundstelle; die Zahl der Verworfenen steht sichtbar im Prüfstatus.

Beleg aus dem Bestand: Der Artikel `2026-09-11-standby-kosten-reduzieren…`
führt die BDEW-Strompreisanalyse (37,3 ct/kWh) im Frontmatter und im Text; die
fünf „neuen“ Befunde behaupteten dennoch „ohne Quellenangabe“.

### 2e. `scripts/faktenfrische_befund_ledger.py` – Projektion `betrieb-v3`

Neue Projektion (Vorgabe für **neue** Entscheidungen): Leerzeilenfolgen werden
auf höchstens eine zusammengezogen. Eine abgeleitete Bildzeile oder ein
verschobener Block ändert damit keine Entscheidung mehr; ein echter Satz
öffnet sie weiterhin. Die älteren Projektionen (`betrieb-v2`, `betrieb-v1`,
`roh-rand`) bleiben unverändert als Rückwärtsanker erhalten, `text_v2` wird
zusätzlich geführt. **Keine dokumentierte Entscheidung wird entwertet.**

### 2f. Bestandsheilung

`abbildungen_ableiten.py --nachzug`: 20 Beiträge geheilt (kaputte Zeile
kanonisiert, Doppelzeile samt ihrer Unterschrift entfernt). Ergebnis:
`grep -rn "\. svg" content` → **0**, `--check` → **0 Befunde**.

### 2g. Titel `Grundversorgung Strom`

`T2-seo-audit`: „Titel zu kurz (21 Zeichen, min. 30)“. Neuer Titel:
„Grundversorgung Strom und Gas: Was sie leistet und kostet“ (58 Zeichen, mit
Doppelpunkt – `check_titles` R1). SEO-Audit danach: **0 score_issues**.

---

## 3. Nachweis (gemessen, nicht behauptet)

| Prüfung | Vorher | Nachher |
|---|---|---|
| `T6-textverstaendnis` (harte Regeln, 80 Live-Artikel) | 20 blockiert | **0** |
| `T2-seo-audit` (score_issues) | 1 | **0** |
| `check_titles` | – | **0 Verstöße / 126 Titel** |
| `abbildungen --check` | 20 Beiträge mit Doppelzeile | **0 Befunde** |
| Zerlegte Asset-URLs im Bestand | 40 | **0** |
| `F4-fachbefund` (live) | 21 Artikel / 87 Befunde | 19 Artikel / **77 Befunde** (nur noch menschlich) |

Zusätzlich grün über den gesamten Live-Bestand gemessen:
`T3` Titel, `T4` Keyword, `T5` Lesbarkeit, `RD1` Duplikate, `RD2`
Einzigartigkeit, `Y1/Y2` YMYL, `N1` Revision – **jeweils 0 Funde**.
`A1/A3` (Affiliate/Offenlegung) sind lokal ohne Hugo-Build nicht messbar; die
CI misst sie im gebauten `public/` (fail-closed, unverändert).

### Tests

* `scripts/tests/test_1098_produktionswahrheit.py` – **14 neue Regressionstests**
  (Schutzzonen, Doppelzeile/Idempotenz, Datei-URL, Bestandsscan, eigene
  Belegkette, Textanker, Leerzeilen-Projektion).
* Selbsttests: `fix_spaces` 62 Fälle · `abbildungen_ableiten` · `fix_url_hygiene`
  · `faktenfrische` 40/40 · `faktenfrische_befund_ledger` · Governance C1–C49.
* Bestehende Suiten: `test_faktenfrische_betriebsflaechen`,
  `test_faktenfrische_befund_akte`, `test_scorecard_ticket`,
  `test_abbildungen_ableiten`, `test_abbildungen_nachzug` – grün.

---

## 4. Was offen bleibt – und warum das richtig ist

**F4 ist per Vertrag menschlich** (`data/release_scorecard.yaml`:
`entscheidung: human`). Die verbleibenden 77 Live-Befunde stehen vollständig,
mit früherer Entscheidung, heutigem Zahlenabgleich und Datei-Hash in
`F4-ENTSCHEIDUNGSVORLAGE-1098-2026-11-10.md`. Die Maschine entscheidet sie
nicht – auch nicht durch ein neues Prüfdatum und nicht durch eine hübschere
Formulierung.

Schließweg (unverändert, eine Zeile je Befund):

```bash
python3 scripts/faktenfrische_befund_ledger.py --entscheiden <ID> \
  --von "Frank Hartung" --begruendung "<was am heutigen Text geprüft wurde>"
python3 scripts/faktenfrische_befund_akte.py --schreiben
python3 scripts/release_scorecard.py --live --streng
```

Mit der Projektion `betrieb-v3` bleibt eine so getroffene Entscheidung künftig
auch dann gültig, wenn der Abbildungs-Nachzug einen Block verschiebt. Genau
dieser Kreislauf ist damit beendet.
