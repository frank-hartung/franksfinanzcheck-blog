# 📝 Grammatik-Kongruenz LT5/LT6 – Anleitung (Stand 30.10.2026)

**Auftrag (Frank, 30.10.2026):** „Rechtschreib- und Grammatikprüfung dauerhaft
auf Highend-Niveau einer Profi-Agentur nachschärfen und Fehler dauerhaft mit
Selbstheilung beheben.“ — Bezug: der Live-Artikel
`/posts/2026-10-24-etf-sparplan-starten-schritt-fuer-schritt-zum-monatlichen/`.

**Was hier steht, in einem Satz:** Diese Seite erklärt die zwei neuen
Prüf-Ebenen des `scripts/grammar_check.py` (LT5 Genus/Numerus, LT6 Kasus nach
Präposition), die Wissensquelle `data/genus_lexikon.txt`, wie die
Selbstheilung schreibt (und wann ausdrücklich **nicht**), wie man das Lexikon
pflegt – und welche Grenzen die Prüfung bewusst hat.

---

## 1. Der Befund, der die Ebene nötig machte

Der Artikel trug im Titel (und damit in H1, Cover, `og:title`, Pinterest):

```text
ETF-Sparplan starten: Dein Schritt-für-Schritt-Anleitung
```

Richtig ist „**Deine** …“, weil *Anleitung* feminin ist. Das ist kein Tippfehler –
es ist **Kongruenz**. Und genau die lag außerhalb des Radars:

| Wache | Warum sie es nicht sieht |
|---|---|
| `spellcheck.py` (Hunspell) | „Dein“ und „Anleitung“ sind beide korrekt geschrieben. Ein Wörterbuch kennt keine Nachbarschaft. |
| `casing_guard.py` | Prüft Groß-/Kleinschreibung, nicht Genus. |
| `grammar_check.py` LT1–LT4 | Prüft **Wendungen** („wo mit“ → „womit“, „im gegensatz“ → „im Gegensatz“). Eine Kongruenz ist keine Wendung. |
| `lektor_guard.py` | Prüft Stil (Füllphrasen, Doppelwörter, Nominalstil) – nicht Morphologie. |
| `textverstaendnis_guard.py` | Prüft Verständlichkeit (Satzlängen, Keyword-Dumps, Duplikate). |

Ergebnis: **0 Funde** über den ganzen Korpus, vier sichtbare Flächen mit
demselben Fehler. Das ist die Klasse, die LT5 schließt.

---

## 2. Beweisart: warum die Wache nicht rät

Die Prüfung benutzt **keine** Sprachstatistik und **kein** Modell. Sie rechnet:

1. Jedes Artikelwort („der/die/das/ein/kein/mein/dein/…/dieser/jeder/welcher“)
   hat eine **abzählbare Menge von Lesungen**: Genus × Numerus × Kasus.
   `die` = {f·nom, f·akk, pl·nom, pl·akk}, `dem` = {m·dat, n·dat}, `dein` =
   {m·nom, n·nom, n·akk} usw. — die Tabellen stehen im Quelltext
   (`EIN_ENDUNG`, `DIES_ENDUNG`, `BESTIMMT`).
2. Das folgende Nomen trägt sein Genus aus `data/genus_lexikon.txt`.
3. **Passt keine Lesung zum Genus, ist der Satz falsch** – unabhängig davon,
   welchen Kasus der Autor wollte. Diese Eigenschaft ist der Grund, warum die
   Prüfung ohne Semantik auskommt.

**Geschrieben wird nur, wenn genau ein Ziel übrig bleibt.** Beispiel
„Dein Anleitung“: `dein` liest sich als m·nom, n·nom oder n·akk; gesucht ist
eine Form, die zu f·sg passt → nur `deine`. Eindeutig, also Auto-Fix.
Gegenbeispiel „Dieser Konto“: zulässig sind `dieses` (n·nom/akk) **und**
`diesem` (n·dat) → **kein** Fix, sondern Report mit Vorschlagsliste.

---

## 3. Die zwei Ebenen

| ID | Was | Beispiel | Auslöser |
|---|---|---|---|
| **LT5** | Genus/Numerus-Kongruenz | „die Geld“ → „das Geld“, „Dein Anleitung“ → „Deine Anleitung“, „einen Konto“ → „ein Konto“ | jedes Artikelwort + Nomen aus dem Lexikon |
| **LT6** | Kasus **nach Präposition** | „mit dein Konto“ → „mit deinem Konto“, „um ein Grad“ → „um einen Grad“, „für der Kontrolle“ → „für die Kontrolle“ | Präposition mit **einem** Kasus (Dativ- und Akkusativliste im Quelltext) |

**Wechselpräpositionen sind absichtlich keine Auslöser.** „in, an, auf, über,
unter, vor, hinter, neben, zwischen“ regieren zwei Kasus („auf dein Konto“ /
„auf deinem Konto“ sind beide möglich, je nach Richtung). Ohne Semantik gibt
es dort keine Wahrheit – also keine Prüfung. Genitiv nach Präposition
(„dank des“, „laut des“) ist strittig und bleibt ebenfalls draußen.

---

## 4. Selbstheilung: was geschrieben wird, was nicht

| Zone | Verhalten |
|---|---|
| Fließtext | Auto-Fix bei eindeutigem Ziel, durch `sprachkern.write_verified` (Link-/Shortcode-/Überschriften-Zahl konstant, Wortzahl ≥ 90 %, keine neuen Politur-Ruinen) |
| `description` | wie Fließtext (SEO-Feld, inhaltlich identisch heilbar) |
| `title` | **Cover-Marken-Lock**: im Normallauf nur Report + Vorschlag; geschrieben **nur** mit `--fix-titel` und **nur** bei eindeutigem Beweis |
| `kurzantwort`, `pin_title`, `pin_description`, `cover.alt`, `cover.caption` | **geprüft, aber nie geschrieben**: Sie erscheinen auf Pinterest, im Cover und in der Suchvorschau – ein Pin-Text ist ein Markenvertrag, und `cover.alt` gehört zum gerenderten Bild. Der Report nennt Fund + Vorschlag, die Redaktion entscheidet |
| `keywords`, `tags` | unangetastet (Suchbegriffe sind keine Sätze) |
| Code, Links (inkl. Linktext), Shortcodes, URLs | unangetastet (Schutzzonen aus `sprachkern.protect_zones`) |
| YMYL-Artikel mit gültigem Siegel | unangetastet (`editorial_review_gate`, Schreibschutz im Kern) |

**Nach einer Titel-Heilung muss das Cover neu gerendert werden** – das Cover
trägt den Titel als Bild. Genau diese Reihenfolge erzwingt Governance-Regel
**C47** im täglichen Lauf: `grammar_check.py --fix` und `--fix-titel` laufen
**vor** `check_covers.py --fix`.

---

## 5. Falsch-Positiv-Sperren (eingefroren im Selbsttest)

Eine Grammatik-Wache, die korrektes Deutsch „heilt“, ist schlimmer als keine
Wache. Jede der folgenden Zeilen ist am Bestand vom 30.10.2026 belegt und
bleibt **unangetastet**:

| Sperre | Satz, der bleiben muss | Warum |
|---|---|---|
| Relativpronomen | „Personen, **die Geld** für Ziele brauchen“ | „die“ ist Bezugswort, kein Artikel |
| Demonstrativpronomen | „Sind **das Werte**, die gelten?“ | „das“ zeigt auf etwas |
| Schwache Adjektivdeklination | „Auf **dem einen Konto** laufen alle Abbuchungen“ | nach bestimmtem Artikel ist „einen“ Adjektiv |
| Kompositum mit Leerzeichen | „Kriterien für **den Girokonto Vergleich**“ | der Kopf des Kompositums ist „Vergleich“ |
| Fügung | „nicht Kontrolle **um der Kontrolle willen**“ | feste Genitivwendung |
| Gleichlautender Plural | „**Die Anbieter** senken den Preis“, „Öffne **die Fenster**“ | Singular und Plural sind formgleich → mehrdeutig |
| Plural-Dativ | „Bei **den Preise** fehlt ein Wert“ | das Nomen müsste „Preisen“ heißen → nie am Artikelwort allein heilen |
| Mehrdeutiges Nomen | „**dein** Nutzen“ (der/das Nutzen) | zwei Genera, kein Beweis |
| Wechselpräposition | „Leg es **auf dein Konto**“ | zwei Kasus möglich |

Zusätzlich: Nach einem Komma, Semikolon oder Gedankenstrich ist ein
Artikelwort im Deutschen ein Pronomen – dort prüft die Wache nicht.

---

## 6. Befehle

```bash
python3 scripts/grammar_check.py --selftest            # 20 Fälle (inkl. 9 Negativ-Proben)
python3 scripts/grammar_check.py --lexikon-pruefen     # Lexikon: Format, Tags, Duplikate
python3 scripts/grammar_check.py                       # Report über den Bestand
python3 scripts/grammar_check.py --fix                 # Heilung Fließtext + description
python3 scripts/grammar_check.py --fix-titel           # + Titel (nur eindeutige Fälle)
python3 scripts/grammar_check.py --file <pfad> --fix   # ein Artikel
python3 scripts/grammar_check.py --lexikon-vorschlag   # was als Nächstes ins Lexikon gehört
python3 -m unittest scripts.tests.test_grammatik_kongruenz
npm run grammatik          # = --strict (Exit 1 bei offenen Funden)
npm run test:grammatik     # Selbsttest + Lexikon-Prüfung + Unit-Tests
```

**Reports:** `GRAMMATIK-REPORT.md`, `.grammar_report.json` (beide gitignored).

---

## 7. Das Lexikon pflegen

`data/genus_lexikon.txt` ist die **einzige** Wissensquelle – kein Download,
kein Wörterbuch-Paket, kein Netz. Format:

```text
<oberflaeche><TAB><genus>        # m · f · n · pl · Mehrfach: m/pl, m/n
```

Zwei Regeln, die den Bestand sauber halten:

1. **Oberflächen, keine Lemmata.** `beitrags` (Genitiv) steht als eigene Zeile,
   weil die Wache genau die Form prüft, die im Text steht. Es wird nie ein
   Stamm geraten – deshalb ist die Prüfung falsch-positiv-frei.
2. **Nur eindeutige Genera.** Zweifelsfälle bekommen beide Tags
   (`gehalt m/n`, `nutzen m/n`, `artikel m/pl`) – damit ist automatisch klar,
   dass dort **nicht** geheilt wird.

Wartungspfad:

```bash
python3 scripts/grammar_check.py --lexikon-vorschlag   # Top-Formen ohne Eintrag
python3 scripts/grammar_check.py --lexikon-pruefen     # Format bleibt gültig
```

**Zwei automatische Wächter über dem Lexikon** (beide in `--lexikon-pruefen` bzw.
den Unit-Tests, beide am 30.10.2026 durch echte Fehler ausgelöst):

* **Suffix-Plausibilität** – `-ung/-heit/-keit/-schaft/-tion/-tät/-enz/-anz/-sion/
  -ive/-ik/-ie` sind feminin, `-lein` neutrum. Ausnahmen sind eine benannte Liste,
  keine stille Regel („Notgroschen“ ist maskulin, obwohl es auf `-chen` endet).
* **Anker-Genera** (`LexikonAnkerTests` in `scripts/tests/test_grammatik_kongruenz.py`)
  – 60 Kernwörter des Blogs mit geprüftem Duden-Genus. Grund: Ein falsches Genus
  ist teurer als ein fehlender Eintrag, weil es einen **falschen** Fix schreibt.
  Genau das passierte beim Aufbau („internet“, „unterschrift“ und „blatt“ standen
  mit falschem Genus in der Datei) – der Anker-Test hätte jeden dieser drei
  Fehler beim ersten Lauf gefangen.

Wer eine Zeile ergänzt, ergänzt **keine Regel** – die Prüfung ist generisch.
Aktueller Stand: 730 Oberflächen (f 281 · m 256 · n 126 · pl 112), Deckung
**67,4 %** aller Artikelwort+Nomen-Stellen des Bestands (11.661 von 17.293).

---

## 8. Grenzen (ehrlich benannt)

* **Kein Kasus ohne Präposition.** „Er hilft der Mann“ bleibt unentdeckt –
  der Dativ folgt hier aus dem Verb, nicht aus einer Präposition.
* **Keine Adjektiv-Kongruenz.** „ein großer Haus“ ist noch nicht abgedeckt;
  dafür bräuchte es Adjektiv-Paradigmen (nächster Ausbauschritt).
* **Kein Verbbezug.** Subjekt-Verb-Kongruenz („Die Preise steigt“) ist nicht
  Teil von LT5/LT6.
* **Lexikon-Abdeckung statt Vollständigkeit.** Was nicht im Lexikon steht,
  wird nicht geprüft – dafür ist jeder Fund ein Beweis. `--lexikon-vorschlag`
  macht die Lücke sichtbar und priorisierbar.
* **Keine Stil-Urteile.** Ob ein Satz gut klingt, entscheidet weiter das
  Lektorat (`lektor_guard.py`, `sprachglatt.py`).

---

## 9. Verdrahtung

| Ort | Was |
|---|---|
| `.github/workflows/blog-health-daily.yml` | täglich: Selbsttest → Lexikon-Prüfung → `--fix` → `--fix-titel` → **danach** Cover-Neubau |
| `.github/workflows/hemingway-check.yml` | Mo/Mi/Fr: `--fix` (Fließtext) + `--lexikon-pruefen` |
| `scripts/endredaktion.py` (E7) | nutzt `grammar_check.analyze` – damit automatisch inklusive LT5/LT6 |
| `.github/workflows/content-engine-v2.yml` | `--fix --new-only` je neuem Artikel (Geburt) |
| `governance_contract.py` | **C47** prüft Wache, Lexikon, Reihenfolge und Test in beide Richtungen |
| `scripts/selftest_runner.py` | `grammar_check.py` steht im vertraglichen Minimum (`GUARDS`, C6) |
