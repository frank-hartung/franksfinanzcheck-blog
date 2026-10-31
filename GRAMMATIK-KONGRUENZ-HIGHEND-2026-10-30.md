# Grammatik-Kongruenz auf Agentur-Niveau – LT5/LT6, Selbstheilung und Dauerwache

**Datum:** 30.10.2026 · **Auftrag (Frank):** „Rechtschreib- und Grammatikprüfung
(Automatik) dauerhaft auf Highend-Niveau einer Profi-Agentur nachschärfen und
Fehler dauerhaft mit Selbstheilung (Automatik) auf Highend-Niveau einer
Profi-Agentur beheben.“ · **Beispielartikel:**
`/posts/2026-10-24-etf-sparplan-starten-schritt-fuer-schritt-zum-monatlichen/`

---

## 1. Der Befund in einem Satz

Der Artikel stand seit dem 28.10.2026 mit **„Dein Schritt-für-Schritt-Anleitung“**
live – im Titel, in der H1, im Cover-Bild, in `og:title`, im Pinterest-Pin und in
sieben Social-Kalendern. Richtig ist „**Deine** …“. Alle vorhandenen Wachen
meldeten **0 Funde**, weil keine von ihnen die Nachbarschaft zweier Wörter
prüfen konnte: Rechtschreibprüfung kennt Wörter, nicht Grammatik.

---

## 2. Forensik: warum 250 Wachen das nicht sahen

| Wache | Prüft | Warum blind |
|---|---|---|
| `spellcheck.py` (Hunspell) | Wortexistenz | „Dein“ und „Anleitung“ sind beide korrekt geschrieben |
| `casing_guard.py` | Groß-/Kleinschreibung | kein Genus, kein Numerus |
| `grammar_check.py` LT1–LT4 | feste Wendungen | „Dein Anleitung“ ist keine Wendung, sondern eine Flexionsform |
| `lektor_guard.py` | Stil (Füllwörter, Doppelungen) | keine Morphologie |
| `stil_guard.py`, `sprachglatt.py` | Satzbau, Nominalstil | keine Kongruenz |
| `hardcases_guard.py` | harte Einzelfehler („daß“, „seid/seit“) | Regelwerk endlich, deckt keine Flexion |

**Erkenntnis:** Es fehlte keine Regel, es fehlte die **Fähigkeit**. Ein
Kongruenz-Fehler ist nur mit Wissen über das Genus des Nomens entscheidbar – und
dieses Wissen besaß keine einzige Stufe.

---

## 3. Was gebaut wurde

### 3.1 `data/genus_lexikon.txt` – die Wissensquelle (707 Oberflächen)

* Format: `<oberfläche>\t<tags>` (`m`, `f`, `n`, `pl`, mehrdeutig als `m/n`,
  `n/m`, `m/pl`, `n/pl`).
* **Oberflächen, keine Lemmata**: `beitrags`, `geräts`, `plänen` stehen als
  eigene Zeilen, weil die Wache prüft, was im Text steht.
* **Mehrdeutigkeit ist ein Merkmal, kein Fehler**: `gehalt m/n`,
  `nutzen m/n`, `teil m/n`, `thermostat n/m`, `artikel m/pl` – solche Einträge
  können **nie** automatisch geheilt werden.
* Verteilung: **f 271 · m 251 · n 120 · pl 138**.
* Kein Download, kein Netz, kein API-Call: Die Datei ist reviewbarer Quelltext.

### 3.2 LT5 – Genus/Numerus-Kongruenz

Das Artikelwort wird in **Lesungen** zerlegt (Genus × Numerus × Kasus). Passt
keine Lesung zum Genus des Nomens, ist der Satz falsch. Geschrieben wird nur,
wenn **genau ein** Ziel übrig bleibt:

| Fall | Lesungen | Ziel | Ergebnis |
|---|---|---|---|
| „Dein Anleitung“ | m·nom, n·nom, n·akk | f·sg → `deine` | eindeutig → **Fix** |
| „Dieser Konto“ | m·nom | `dieses` (nom/akk) **oder** `diesem` (dat) | mehrdeutig → **Report** |
| „den Preise“ | m·akk, pl·akk | Dativ Pl. bräuchte „Preisen“ | **nie Fix** (Nomen müsste mit) |

### 3.3 LT6 – Kasus nach Präposition

Nur Präpositionen mit **einem** Kasus lösen aus (Dativ: `mit nach aus von zu bei
seit gemäß …`, Akkusativ: `durch für gegen ohne um wider`). Wechselpräpositionen
(`in an auf über unter vor hinter neben zwischen`) und `bis` sind **keine**
Auslöser – dort ist der Kasus ohne Semantik nicht entscheidbar.

### 3.4 Die Sperren gegen Falsch-Heilungen (jede ist ein echter Bestandssatz)

Relativpronomen („Personen, **die Geld** …“), Demonstrativpronomen („Sind **das
Werte** …“), schwache Adjektivdeklination („auf **dem einen Konto**“),
Kompositum mit Leerzeichen („**den Girokonto Vergleich**“), Fügung („um **der
Kontrolle willen**“), gleichlautender Plural („**Die Anbieter** senken“),
Plural-Dativ, mehrdeutiges Nomen, Pronomen nach Satzzeichen, Schutzzonen
(Links, Shortcodes, Code, `keywords`, `tags`).

**Belegt im Selbsttest** (20 Fälle, davon 9 Negativ-Proben) und in **32
Unit-Tests** (`scripts/tests/test_grammatik_kongruenz.py`).

---

## 4. Selbstheilung: was geschrieben wird

| Zone | Verhalten |
|---|---|
| Fließtext | Auto-Fix bei genau einem Ziel, via `sprachkern.write_verified` (Link-/Shortcode-/H1-Zahl konstant, Wortzahl ≥ 90 %) |
| `description` | wie Fließtext |
| `title` | **Cover-Marken-Lock**: nur Report; geschrieben nur mit `--fix-titel` |
| `kurzantwort`, `pin_title`, `pin_description`, `cover.alt`, `cover.caption` | geprüft, **nie** automatisch geschrieben (Markenvertrag) |
| `keywords`, `tags` | unangetastet |
| YMYL-Artikel mit Siegel | Schreibschutz im Kern |

**Reihenfolge ist Vertrag:** `--fix` → `--fix-titel` → `check_covers.py --fix`.
Ohne diese Kette stünde der Satz im Text und der alte Satz weiter im Bild.

---

## 5. Was im Bestand geheilt wurde (9 Stellen, 7 Dateien)

| Datei | vorher → nachher | Weg |
|---|---|---|
| `2026-10-24-etf-sparplan-…` (Titel) | „**Dein** Schritt-für-Schritt-Anleitung“ → „**Deine** …“ | `--fix-titel` + Cover in 14 Varianten neu gerendert |
| `2026-10-24-etf-sparplan-…` (Text) | „Die Wahl des **ETF**“ → „des **ETFs**“ | Redaktion (Genitiv-s) |
| `2026-08-26-dns-server-…` | „kann **diese** Schritt verändern“ → „**diesen** Schritt“ | Redaktion (mehrdeutig → Report) |
| `2026-09-07-heizkosten-…` | „um **ein** Grad“ → „um **einen** Grad“ | LT6-Auto-Fix |
| `2026-10-02-gasabschlag-…` | „um **ein** Grad“ (2×) → „**einen**“ | LT6-Auto-Fix |
| `2026-10-27-frugalismus-…` | „gibt dir **das** Kraft“ → „**die** Kraft“ | LT5-Auto-Fix |
| `2026-10-12-kleine-energiespar-tricks-…` (`kurzantwort`) | „um **ein** Grad“ → „**einen**“ | Report → Redaktion |
| `2026-10-24-energieeffizienz-…` (`kurzantwort`) | „um **ein** Grad“ → „**einen**“ | Report → Redaktion |

**Nachher:** `--strict` über 72 Live-Artikel → **0 Funde**;
`--include-drafts` über 104 Artikel → **0 Funde**; Kongruenz-Prüfung über den
kompletten Bestand → **0 offene Befunde**.

**Folgeheilungen an den Ableitungen** (damit der alte Titel nicht weiterlebt):
`data/social/kalender/*` (künftige Posts neu erzeugt), `data/state.yaml`
(Archiv des gesendeten Mastodon-Posts bleibt als Historie unverändert),
`data/fachpruefung_register.yaml`, `data/reserve-custody.json`,
`data/covers_manifest.json`, `data/lcp_images.json`, `data/fcp_images.json`.

---

## 6. Dauerhaftigkeit: die Wache kann nicht still verschwinden

| Ebene | Was sie hält |
|---|---|
| Selbsttest | 20 Fälle vor jedem Schreibvorgang; Lexikon < 400 Einträge = **rot** |
| Unit-Tests | 32 Fälle inkl. Vorfall („Dein Schritt-für-Schritt-Anleitung“) und aller Sperren |
| **Governance C47** | prüft Wache, Lexikon (Format, Pflichtformen, Mindestgröße), Titel-Sperre, **Reihenfolge im Tageslauf** und Existenz der Tests – im Selbsttest mit fünf Kunstbefunden (Reihenfolge verdreht, Marker entfernt, Lexikon fehlt, negativ-Probe fehlt, Selbsttest-Aufruf fehlt) |
| Vertragliches Minimum | `governance_contract.GUARDS` enthält `grammar_check.py`; `selftest_runner` fährt **254 Wachen**, alle grün |
| Täglicher Lauf | `blog-health-daily.yml`: Selbsttest → Lexikon-Prüfung → `--fix` → `--fix-titel` → `check_covers.py --fix` |
| Mo/Mi/Fr | `hemingway-check.yml`: `--fix` + `--lexikon-pruefen` |
| Geburt neuer Artikel | `content-engine-v2.yml` (`--fix --new-only`), `endredaktion.py` E7 über `analyze()` |
| Social-Copy | `social_copywriter.load_article()` heilt Titel/`kurzantwort`/`description`/`pin_title` **an der Quelle** – ein gebrochener Titel erreicht keinen Kanal mehr |
| Wartungspfad | `--lexikon-vorschlag` (mit Genus-**Zeugnis** aus dem Bestand), `--lexikon-pruefen` |

**Zwei neue automatische Lexikon-Prüfungen** (beide durch echte Fehler beim
Aufbau ausgelöst):

1. **Suffix-Plausibilität** – `-ung/-heit/-keit/-schaft/-tion/-tät/-enz/-anz/
   -sion/-ive/-ik/-ie` feminin, `-lein` neutrum; Ausnahmen sind benannte Listen.
2. **Plural-Gleichheit** – Nomen auf `-er/-el/-en` mit nur einem Genus hätten
   zur Folge, dass „keine Kabel“ zu „kein Kabel“ „geheilt“ würde. Diese Klasse
   wird jetzt hart gemeldet (mit Liste der echten Umlaut-/pluralfreien
   Ausnahmen: `schaden`, `nummer`, `beispiel`, `backofen`, `wasser` …).
3. **Genus-Zeugnis** – `--lexikon-vorschlag` nennt neben jedem Kandidaten die
   eindeutigen Artikelwörter, die im Bestand davorstehen. Gemischtes Zeugnis →
   keine Aufnahme.

---

## 7. Nachweise (gemessen, nicht behauptet)

```text
python3 scripts/grammar_check.py --selftest
  → ✅ 20 Fälle grün (LT1–LT6, offline, ohne API)

python3 scripts/grammar_check.py --lexikon-pruefen
  → 📚 707 Oberflächen · f 271 · m 251 · n 120 · pl 138 → ✅ Format, Tags, Suffixe, Plural
python3 -m unittest scripts.tests.test_grammatik_kongruenz
  → Ran 32 tests … OK
python3 scripts/governance_contract.py --selftest
  → ✅ C1–C47 mit Kunstbefunden
python3 scripts/governance_contract.py
  → 🔒 GOVERNANCE-VERTRAG erfüllt – alle 43 Regeln
python3 scripts/selftest_runner.py
  → 254 Wachen · 508 Uhr-Proben · jeder Selbsttest grün
python3 scripts/check_covers.py
  → 109 Covers · Probleme 0 · Stale 0 · Brand 0 · Text 0
```

**Deckung:** 17.293 Artikelwort+Nomen-Stellen im Bestand, davon **11.953
(69,1 %)** mit Lexikon-Beweis geprüft (vorher 62,7 %). Die Restlücke ist
bewusst: Lieber ein ungeprüfter Satz als ein geratener Fix.

**Laufzeit:** 72 Live-Artikel in ~19 s, 104 Artikel inkl. Entwürfe in ~29 s –
alltagstauglich für den täglichen Lauf.

---

## 8. Grenzen (ehrlich, mit Ausbaupfad)

1. **Keine Adjektiv-Kongruenz** („ein großer Haus“) – braucht Adjektiv-Paradigmen.
2. **Keine Subjekt-Verb-Kongruenz** („Die Preise steigt“).
3. **Kein Kasus ohne Präposition** („Er hilft der Mann“) – Dativ aus dem Verb.
4. **Abdeckung statt Vollständigkeit** – 69,1 % der Stellen sind beweisbar.
   Nächste Runde: `--lexikon-vorschlag` abarbeiten (Zeugnis-gestützt).
5. **Keine Stil-Urteile** – Kürze, Rhythmus, Tonalität bleiben Lektorat.

---

## 9. Betrieb

```bash
python3 scripts/grammar_check.py --selftest            # Beweis zuerst
python3 scripts/grammar_check.py --lexikon-pruefen     # SSOT bleibt gültig
python3 scripts/grammar_check.py --fix                 # Fließtext + description
python3 scripts/grammar_check.py --fix-titel           # Titel (nur Beweis)
python3 scripts/check_covers.py --fix                  # NACH der Titel-Heilung
npm run grammatik                                      # = --strict (Exit 1 bei Funden)
npm run test:grammatik                                 # Selbsttest + Lexikon + Unit-Tests
```

Vollständige Betriebsanleitung: [`docs/ANLEITUNG-GRAMMATIK-KONGRUENZ.md`](docs/ANLEITUNG-GRAMMATIK-KONGRUENZ.md)
· Regelwerk: [`docs/QUALITAETS-REGELWERK.md`](docs/QUALITAETS-REGELWERK.md) (§ LT5/LT6)
· Vertrag: [`docs/GOVERNANCE-KONTRAKT.md`](docs/GOVERNANCE-KONTRAKT.md) (C47)

---

## 10. Nächste Ausbaustufen (nicht Teil dieses Auftrags, aber vorbereitet)

* **LT7 – Steigerungsstapel** („immer mehr besser“) und **LT8 – Weichmacher**
  („könnte eventuell vielleicht“) sind Stil-Regeln und gehören in
  `sprachglatt.py`/`lektor_guard.py`, nicht in die Kongruenz-Wache.
* **Füllfloskel-Ebene** („im Modellfall“, „als Beispielwert“ – ~395 Stellen im
  Bestand) berührt die Lesbarkeit, nicht die Grammatik; eigener Auftrag.
* **Adjektiv-Kongruenz** als LT9, sobald ein Paradigmen-Lexikon vorliegt.
