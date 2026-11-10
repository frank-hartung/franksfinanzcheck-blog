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
| `F4-fachbefund` (live) | 21 Artikel / 87 Befunde | 20 Artikel / **82 Befunde** (nur noch menschlich; 5 davon aus einem main-Lauf nach dem Branch-Stand) |

`T1w-zeichenlaenge-optimum` ist per SSOT `wirkung: warnung` und deshalb
**kein Blocker** (der Exit-Code der Scorecard kennt nur „blockiert“ und
„nicht beweisbar“). Er ist trotzdem nicht weggeklammert – siehe Abschnitt 5.

Zusätzlich grün über den gesamten Live-Bestand gemessen:
`T3` Titel, `T4` Keyword, `T5` Lesbarkeit, `RD1` Duplikate, `RD2`
Einzigartigkeit, `Y1/Y2` YMYL, `N1` Revision – **jeweils 0 Funde**.
`A1/A3` (Affiliate/Offenlegung) sind lokal ohne Hugo-Build nicht messbar; die
CI misst sie im gebauten `public/` (fail-closed, unverändert).

### Tests

* `scripts/tests/test_1098_produktionswahrheit.py` – **20 Regressionstests**
  (Schutzzonen, Doppelzeile/Idempotenz, Datei-URL, Bestandsscan, eigene
  Belegkette, Textanker, Leerzeilen-Projektion, F4-Dossier vollständig/aktuell).
* Selbsttests: `fix_spaces` 62 Fälle · `abbildungen_ableiten` · `fix_url_hygiene`
  · `faktenfrische` 40/40 · `faktenfrische_befund_ledger` · `artefakt_waechter`
  (627 Artefakte heil) · Governance C1–C49 **vor** dem main-Merge grün; seit
  `7b93454` (PR #1162) sind **C6/C38 rot** – Fremdursache, s. Abschnitt 5c.
* Bestehende Suiten: `test_faktenfrische_betriebsflaechen`,
  `test_faktenfrische_befund_akte`, `test_scorecard_ticket`,
  `test_abbildungen_ableiten`, `test_abbildungen_nachzug` – grün.

**Vollsuite (`python3 -m unittest discover -s scripts/tests`): 5.761 Tests,
23 Fehlschläge, 8 Fehler.** Diese 31 sind **nicht** von diesem Branch: Ein
Export von `origin/main` (`963c044`) in ein separates Verzeichnis zeigt
exakt dieselben Testnamen (23/8, gleiche Module, gleiche Namen). Beweis statt
Beteuerung – 0 Abweichungen durch diesen Branch.

Einordnung der 31 (Fremdursachen, bereits auf `main` rot):

* 6 Fehler = fehlende CI-Pakete in dieser Umgebung (`pillow` u. a. aus
  `requirements-ci.in`) – fail-closed, kein Code-Defekt.
* 3 = `blustradius_register` (C38, Schritt `GSC-Leistungsdaten – …` ohne
  Registereintrag, s. Abschnitt 5b).
* 5 Subtest-Fehlschläge in `test_faktenfrische_1072` = die fünf Befunde, die
  der `main`-Faktenfrische-Lauf (`963c044`) auf dem Waschmaschinen-Artikel
  angelegt hat; sie nennen eine Fundstelle, die **nicht wörtlich** im Artikel
  steht. Genau diese Klasse verwirft die neue Ankerprüfung in
  `faktenfrische.py` – der Bestand aus der Zeit davor bleibt menschlich zu
  entscheiden (steht im Dossier).
* Rest (pagefind-Version im Manifest vs. Test, Hugo-Pin, Pflichtcheck,
  Reserve-/Offenlegungs-/Watchdog-Verdrahtung) = offene Roten auf `main`,
  unabhängig von #1098.

---

## 4. Was offen bleibt – und warum das richtig ist

**F4 ist per Vertrag menschlich** (`data/release_scorecard.yaml`:
`entscheidung: human`). Die verbleibenden Live-Befunde stehen vollständig,
mit früherer Entscheidung, heutigem Zahlenabgleich und Datei-Hash in
`F4-ENTSCHEIDUNGSVORLAGE.md`. Die Maschine entscheidet sie nicht – auch nicht
durch ein neues Prüfdatum und nicht durch eine hübschere Formulierung.

Das Dossier ist ab dieser Runde **keine Handarbeit mehr**, sondern eine
Projektion mit Prüfmodus:

```bash
python3 scripts/f4_entscheidungsvorlage.py            # schreibt die Vorlage
python3 scripts/f4_entscheidungsvorlage.py --check    # Exit 1 = veraltet
```

Grund: Die erste Fassung wurde von Hand gebaut und war nach dem nächsten
Automatik-Lauf unvollständig (fünf Befunde, die die Tageswache danach fand,
standen nicht darin). Ein Dossier, das der Wirklichkeit hinterherläuft, ist
derselbe Fehler wie ein veraltetes Register. `--check` und sechs Tests
(`test_1098_produktionswahrheit.Entscheidungsvorlage`) erzwingen jetzt:
jeder offene Live-Befund steht im Dokument, jeder hat eine fertige
Schließzeile, und das Dokument nennt für jeden beanstandeten Wert die heutige
Zeile – mit oder ohne Kennzeichnung.

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

---

## 5. Was dieser Stand bewusst NICHT anfasst (und warum)

Zwei Dinge bleiben offen – nicht aus Zeitmangel, sondern weil sie eine
Entscheidung oder eine andere Baustelle sind. Beides ist hier messbar
benannt, damit es niemand „übersehen“ kann.

### 5a. `T1w-zeichenlaenge-optimum` – 5 Beiträge, Hinweis, kein Blocker

Gemessen mit `check_length.py` (Optimum 12.000–18.000, Deckel 22.000):

| Artikel | Zeichen | Richtung |
|---|---|---|
| `2026-09-07-frugalismus-tipps-so-vermeidest-du-teure-alltagsfehler` | 19.890 | 1.890 über dem Optimum |
| `2026-08-14-sparen-im-herbst-…-goldene-jahreszeit` | 18.299 | 299 darüber |
| `2026-08-21-mietwagen-buchen-ohne-kaution-fallen-urlaub` | 18.296 | 296 darüber |
| `2026-09-30-last-minute-urlaub-…-sommer-schnaepp` | 18.112 | 112 darüber |
| `2026-10-24-etf-sparplan-starten-…` | 10.252 | 1.748 **unter** dem Optimum, über dem Floor |

Warum hier keine Textänderung passiert ist:

1. **SSOT:** `T1w` ist `wirkung: warnung`. Der Exit-Code der Scorecard kennt
   nur `blockiert`/`nicht beweisbar` – Warnungen schließen das Ticket nicht
   und öffnen es nicht. `docs/ANLEITUNG-RELEASE-SCORECARD.md` sagt dazu
   ausdrücklich: „T1w in Richtung `ueber-optimum` ist kein Kürzungsauftrag.“
2. **Fassungsbindung:** Jede Fließtextänderung ändert den Aussage-Hash. Beim
   `frugalismus`-Beitrag stehen **3 offene Live-Fachbefunde** – ein Eingriff
   würde die Redaktionsarbeit *vor* der F4-Entscheidung verändern und den
   menschlichen Prüfstand verschieben, statt ihn zu schließen. Genau das ist
   die Reihenfolge-Falle, die den F4-Kreislauf groß gemacht hat.
3. **Nachfüllen wäre Symptompflege:** Der Beitrag unter dem Optimum braucht
   Substanz (FAQ mit Aussagen), nicht Zeichen. Neue Aussagen sind neue
   Befundkandidaten – sinnvoll erst **nach** dem F4-Durchgang.

**Reihenfolge (Empfehlung an die Chefredaktion):** F4 entscheiden → danach
`T1w` redaktionell nachziehen (Rezept: `docs/ANLEITUNG-RELEASE-SCORECARD.md`,
Abschnitt „Längen-Nachführung“). Der Erzeuger dieser Drift ist dokumentiert:
KI-Politur (`profi_polish.py`) prüft nur die Untergrenze (≥ 85 % des
Originals), nicht den Optimums-Deckel. Ob die Engine künftig *ans Optimum*
statt an den Floor zielen soll, ist laut Anleitung eine Entscheidung der
Chefredaktion über `entscheidung: auto|human` in der SSOT – keine Reparatur
im Vorbeigehen.

### 5b. Zweite Fremdursache auf `main`, hier geheilt: kaputte GSC-Abdeckung

Der Automatik-Commit `e82c0eb` („Leistungsdaten 2026-11-09“) hat fünf
Abdeckungs-Artefakte als **Merge-Schnitt** nach `main` getragen:
`data/gsc/abdeckung/befund.json` und `prioritaet.json` waren ungültiges JSON
(doppelte Schlüssel, fehlende Objekttrenner), `ursachen.json` und
`verlinkungsheilung.json` hatten doppelte Objektschlüssel. Folge auf `main`:
`test_gsc_abdeckung` (Vertrag zu Code-Scanning-Alert Nr. 87) und der
Artefakt-Wächter im Integritäts-Siegel waren rot – **beide vor diesem
Branch**, beide denselben Fehler meldend.

Heilung ohne neue Messung: `befund.json`/`.md` und `prioritaet.json` aus dem
letzten gültigen Stand `6c9d473` zurückgeholt; die zwei A2-Artefakte mit dem
dafür gebauten Heiler (`scripts/artefakt_waechter.py --heal`, „letzter
Eintrag gewinnt“, Gegenprobe) bereinigt. Danach: **627 Artefakte strukturell
heil**, 118 Tests (`test_gsc_abdeckung` + `test_redos_security`) grün, im CI
**„ReDoS-Wache“ und „Integritäts-Siegel“ von rot auf grün**.

### 5c. Befund auf `main`, der nicht zu #1098 gehört: C38 (Blustradius)

`python3 scripts/governance_contract.py` meldet auf dem gemergten Stand
C6/C38: Der Schritt `GSC-Leistungsdaten – Artefaktprüfung (fail-closed)`
(deploy.yml, hinzugekommen mit `7b93454` / PR #1162) steht in **keinem**
Eintrag von `data/blustradius-deploy.yml`. Dieselbe Ursache färbt den
Lauf `42870913442` (Qualitäts-Gate, `main`, 18:01 UTC) rot – also **vor**
diesem Branch.

Das ist bewusst **nicht** hier geheilt: Wer einen Schritt in den
Auslieferungsweg stellt, entscheidet laut Register selbst, ob sein rotes
Ergebnis die Auslieferung anhalten darf (`infra`/`inhalt` = ja, `werkzeug` =
nein). Diese Entscheidung gehört dem Betreiber, nicht dem Reparatur-PR –
eine stillschweigend eingetragene Klasse wäre genau die Umgehung, gegen die
C38 gebaut wurde. Nachzutragen ist ein Eintrag in
`data/blustradius-deploy.yml` mit `name`, `klasse` und `grund`; die
Nachbar-Schritte (`Weiterleitungen – … (fail-closed)`: `infra`) sind die
nächstliegende Analogie.
