# 📌 Pinterest-Check #729: Ein Befund hat jetzt einen Schließpfad

**Datum:** 13.10.2026 · **Bezug:** Issue #729 „Pinterest-Check: Probleme
gefunden" (Watchdog-Lauf 13.10.2026 11:58 UTC, Exit 1) · **Auftrag:** „Bitte
dauerhaft auf Highend-Level einer Profi-Agentur beheben." · **Neuer Vertrag:**
C37 (Governance-Kontrakt) · **Vorgänger:** #305 (Duplikate, C17), #390
(Report-Provenienz)

---

## 1. Befund

Der Pinterest-Watchdog meldete einen einzigen offenen Posten:

```
[P8] 2026-09-04-umzug-mit-internet-anschluss-und-rufnummer-mitnehmen:
     5 Hashtags (max. 3)
```

Der Artikel trug in seiner `pin_description` fünf Themen-Tags
(`#umzug #internet #rufnummer #dsl #wechsel`). Der Workflow öffnet dafür ein
Issue (Label `pinterest`) und schließt es **nur bei Exit 0**. Genau das konnte
nie passieren: Die Selbstheilung saniert P1, P4, P4b und P7 – für P8 gab es
keinen Heiler. P8 war zugleich der **einzige offene Posten** des Reports, also
blieb das Issue jeden Lauf erneut offen: täglich dieselbe Messung, täglich
dieselbe Meldung, ein Befund ohne Schließpfad. Dieselbe Bauart wie C29 („Ein harter Blocker braucht einen
Heiler"); die Lehre aus #390 („ein Report, der Befunde zeigt, die niemand
mehr hat") in neuer Form.

## 2. Die eigentliche Schwäche: Erkennen ohne Heilen – an zwei Stellen

| Instanz | Was sie sah | Warum nichts passierte |
|---|---|---|
| `pinterest_check.py` P8 | 5 Hashtags (max. 3) in der `pin_description` | P8 prüfte nur. Die Selbstheilung kannte P1, P3, P4, P4b, P7 – nicht P8 |
| `pinterest_seo_healer.py` H6 | dieselbe Klasse im eigenen Audit | `pin_desc_ok` prüfte nur Länge (220–500) und rohes `&`. Ein Text mit fünf Tags galt als „Premium-Text" und wurde **bewahrt** – Prüfer und Heiler widersprachen sich |

Beide Stellen hängen jetzt an derselben Quelle; P8 saniert die
`pin_description` an der **Quelle** (Frontmatter), bevor überhaupt ein Build
gemessen wird.

## 3. Die blinden Flecken derselben Prüfung

Die schärfere Regel hat sofort zwei weitere, bis dahin unsichtbare Defekte
gefunden – beide im Bestand, beide in Produktion ausgeliefert:

| Artikel | Alt | Neu | Warum unsichtbar |
|---|---|---|---|
| `2026-09-20-gasrechnung-senken-…-spaetsommer-vor` | `#zählerstand` | `#zaehlerstand` | `re.findall(r"#([a-z0-9]+)")` liest „#z" – der Rest fiel weg |
| `2026-10-05-erster-eigener-haushalt-…` | `#ersteWohnung` | `#erstewohnung` | Dasselbe Muster sieht „#erste"; die Umlaut-Prüfung daneben („Umlaut-Hashtag") war dadurch **toter Code** |

Pinterest kann beide Tags nicht als Themen-Tag lesen. Mit der SSOT-Regel
(Umlaut-Faltung, Kleinschreibung, `[a-z0-9]`) sind sie geordnet – und ein Text
mit fünf Tags kann gar nicht mehr entstehen: Die Regel hängt an jedem
Schreiber.

## 4. Die zweite Quelle: die API-Grenze

Zwei Skripte bauen die Pin-Beschreibung erst **beim Senden an Pinterest** –
und umgingen bis heute jede Prüfung im Frontmatter:

- `scripts/generate_pins.py` (Repin-Rotation) hängte blind
  `#GeldSparen #Spartipps #FranksFinanzcheck` **hinter** den kuratierten
  Block. Aus drei Quell-Tags wurden sechs Pin-Tags, zwei davon in CamelCase –
  die Heilung im Artikel wäre an der API wieder aufgehoben worden. Zusätzlich
  konnte `base[:478]` + Block das 500-Zeichen-Limit überschreiten.
- `scripts/pinterest_engine.py` (`pin_text`) sandte die `pin_description`
  unverändert und kappte blind bei 500 Zeichen – ein zu langer Text verlor so
  das Ende des Tag-Blocks.

Beide laufen jetzt durch die SSOT; `generate_pins.build_api_description()` ist
eine prüfbare Naht (ein Block, höchstens drei Tags, ≤ 500 Zeichen),
`pin_text` kürzt die **Prosa** und behält den Block.

## 5. Dauerheilung (Code)

### 5.1 Eine Quelle: `scripts/pinterest_hashtags.py` (neu)

Regel H1–H6, überall dieselbe:

| | Regel |
|---|---|
| H1 | höchstens **3** Hashtags pro Beschreibung |
| H2 | nur `[a-z0-9]` – ASCII, klein (keine Umlaute, keine Großbuchstaben) |
| H3 | 3–24 Zeichen je Tag |
| H4 | ein reines Zahlenschild (`#1`, `#2026`) ist **kein** Tag |
| H5 | kein Tag doppelt (gezählt nach Faltung) |
| H6 | die Hashtags stehen als **ein Block am Textende** |

Öffentliche API: `befunde` (messen), `heile` (deterministisch heilen, für
konforme Texte byte-identisch = idempotent), `tags_bauen` (Tags erzeugen),
`ist_konform`, `normalisiere`, `texte` (`--pruefe`/`--heile`). Die Heilung
**erfindet kein Thema**: gekappt wird hinten (die Reihenfolge im Text ist die
Priorität), und was sich nicht reparieren lässt, fällt weg. Das Modul steht im
vertraglichen Minimum (C6: `--selftest`) und trägt eine Wirkungsprobe
(`--wirkungsprobe`, 4 Fälle: #729-Fall, Umlaut, camelCase, Tag mitten im Satz).

### 5.2 Der Schließpfad: `pinterest_check.py --fix` heilt P8

- Neue Prüfung `_check_pin_descriptions()` läuft **vor** dem HTML-Vergleich und
  misst die Quelle (`pin_description` im Frontmatter). Bei `--fix` wird der
  Text deterministisch saniert, geschrieben und als `SOURCE_HEALED` belegt.
- Ein P8-Fund im **Build** ist kein offener Befund mehr, wenn die Quelle im
  selben Lauf geheilt wurde (der Watchdog baut vor dem Check): Er wird als FIX
  ausgewiesen – der nächste Build liefert den geheilten Stand aus. Weicht der
  Build dagegen von einer sauberen Quelle ab, bleibt es ein Befund
  („Build weicht von der Quelle ab").
- Fail-closed: Ändert die Heilung nichts, bleibt der Befund stehen.
- `_fm_set` ist gehärtet (Ersetzung per Funktion statt String – kein
  Backslash-Escape – und `post_utils.doppel_freies_feld` nach jedem Write).
- Der Report nennt nicht gemessene Prüfungen ausdrücklich (C2): Ohne
  Hugo-Build stehen P3/P6/P7/P10/P12 als „nicht gemessen" im Report statt als
  Grün.
- **Report-Schema 4:** Der Quellfingerabdruck enthält die neue Regeldatei –
  ein Schema-3-Report ist nicht mehr „aktuell" (bot_watchdog-Frische).

### 5.3 Eine Regel für alle Schreiber

| Datei | vorher | jetzt |
|---|---|---|
| `pinterest_seo_healer.py` | eigene Tag-Bau-Logik, `pin_desc_ok` ohne Hashtag-Regel | `ph.befunde` im Audit, `ph.tags_bauen` beim Bau, **minimale Heilung zuerst** im H6 (`ph.heile` – Premium-Prosa bleibt, nur der Block wird geordnet), `ph.ist_konform` in der Gültigkeit |
| `pinterest_duplicate_guard.py` | eigene `_build_hashtags` | `ph.tags_bauen` |
| `pinterest_pin_text_sync.py` | eigene Tag-Prüfung | `ph.heile` **vor** der Längen-Kappung, `pin_desc_valid` mit `ph.ist_konform`, neue Selbsttest-Fälle |
| `pinterest_engine.py` | Tag-Bau + blindes `[:500]` | `ph.tags_bauen`, `ph.heile` als letzte Instanz vor der API, Prosa-Kürzung mit erhaltenem Block |
| `generate_pins.py` | hängte 3 CamelCase-Tags an | `build_api_description()` – ein Block, ≤ 3 Tags |
| `engine_generate.py` | kuratierte Texte ungeprüft | `ph.heile` beim Gebären; ein Einzigartigkeits-Suffix landet nicht mehr hinter dem Tag-Block |
| `spam_guard.py` (B8) | schrieb `*Werbung \|`-Prefix ungeprüft | nach dem Write greift die SSOT-Hygiene |

### 5.4 Der Vertrag: C37

`scripts/governance_contract.py` prüft ab jetzt in sieben Sätzen (a–g), dass
(a) die Regel in **einer** Quelle lebt und als Wache läuft, (b) kein Schreiber
ein eigenes Maximum führt, (c) der Melder heilt, (d) der SEO-Heiler dieselbe
Gültigkeit fragt, (e) **der Bestand** hashtag-konform ist (ein neuer Artikel
mit fünf Tags macht den Vertrag rot, **bevor** ein Issue entsteht), (f) der
Quellfingerabdruck die Regel kennt und (g) Selbsttest/Wirkungsprobe **jetzt**
grün laufen. Sechs Sabotage-Fälle im Vertrags-Selbsttest beweisen, dass C37
rot wird, wenn man den Heiler, die SSOT-Bindung, die Bestandsprobe, die
Testdateien oder den Workflow-Aufruf entfernt. `docs/GOVERNANCE-KONTRAKT.md`
ist mit C37 neu erzeugt.

## 6. Beweise

Ausgeführt im Arbeitsbaum am 13.10.2026 (Exit-Codes in Klammern):

```
$ python3 scripts/pinterest_check.py --json
  {"problems": [], "fixed": []}                                  (0)
$ python3 scripts/pinterest_check.py --fix
  ✅ Pinterest-Selbsttest ok (Modus: FIX)                        (0)
$ python3 scripts/pinterest_hashtags.py --selftest
  ✅ Pinterest-Hashtag-Selbsttest ok (H1–H6, Idempotenz, #729)   (0)
$ python3 scripts/pinterest_hashtags.py --wirkungsprobe
  ✅ WIRKUNGSPROBE bestanden – erkennen, heilen, Fixpunkt (4)    (0)
$ python3 -m unittest scripts.tests.test_pinterest_hashtags scripts.tests.test_pinterest_check
  Ran 45 tests … OK
$ /tmp/blogvenv/bin/python scripts/pinterest_seo_healer.py --json
  89 Artikel · 0 Hashtag-Befunde · 5 offene Fremdbefunde (versicherung-update)
$ python3 scripts/pinterest_duplicate_guard.py
  ✅ Keine Pinterest-Duplikate                                    (0)
$ /tmp/blogvenv/bin/python scripts/pinterest_pin_text_sync.py --json
  89 Artikel · 0 Probleme                                         (0)
$ python3 scripts/spam_guard.py --selftest                       (0)
$ /tmp/blogvenv/bin/python scripts/engine_generate.py --selftest  (0)
$ /tmp/blogvenv/bin/python scripts/governance_contract.py
  🔒 GOVERNANCE-VERTRAG erfüllt – alle 35 Regeln …                (0)
$ python3 -c "import bot_watchdog; bot_watchdog.check_pinterest_report_freshness()"
  (True, 'Report aktuell zum Quellenstand')
$ /tmp/blogvenv/bin/python -m unittest discover -s scripts/tests
  Ran 3009 tests … FAILED (failures=2, skipped=25)
  # beide Roten sind VORBESTEHEND – auf dem Basis-Commit e632b72 in einem
  # frischen Worktree reproduziert:
  #   C25 YMYL-Schreibprüfung „ParseError" (Sandkasten-Interpreter ohne die
  #     Modul-Abhängigkeit, die der CI-Lauf hat) und
  #   2026-10-12-dein-weg-zu-geringeren-monatskosten (Reserve-Snapshot-SHA
  #     im Basis-Commit bereits veraltet); keiner der beiden Befunde liegt
  #     in einer Datei dieses PRs.
```

Die drei geheilten Beschreibungen (Diff, genau eine Zeile je Artikel):

```
2026-09-04-umzug-mit-internet-…:      … #umzug #internet #rufnummer #dsl #wechsel
                                   →  … #umzug #internet #rufnummer
2026-09-20-gasrechnung-senken-…:      … #gasrechnung #nachzahlung #zählerstand
                                   →  … #gasrechnung #nachzahlung #zaehlerstand
2026-10-05-erster-eigener-haushalt-…: … #ersteWohnung #fixkosten #budget
                                   →  … #erstewohnung #fixkosten #budget
```

`data/audit/2026-10-13.jsonl` belegt den Produktionsbefund (11:58:21Z,
`problems: 1, fixed: 0`) und die Heilung (14:44:22Z, `problems: 0, fixed: 3`).

## 7. Dateien

- neu: `scripts/pinterest_hashtags.py`, `scripts/tests/test_pinterest_hashtags.py`
- geändert: `scripts/pinterest_check.py`, `scripts/pinterest_seo_healer.py`,
  `scripts/pinterest_duplicate_guard.py`, `scripts/pinterest_pin_text_sync.py`,
  `scripts/pinterest_engine.py`, `scripts/generate_pins.py`,
  `scripts/engine_generate.py`, `scripts/spam_guard.py`,
  `scripts/governance_contract.py`, `scripts/tests/test_pinterest_check.py`,
  `CLAUDE.md`, `docs/PINTEREST-SPIELBUCH.md`, `docs/GOVERNANCE-KONTRAKT.md`,
  `PINTEREST-REPORT.md`, `data/audit/2026-10-13.jsonl` und die drei
  `content/posts/…/index.md`.

## 8. Rest-Risiken und ehrliche Grenzen

- **Kein Hugo im Sandkasten.** Die HTML-Prüfungen (P3/P6/P7/P10/P12) sind
  lokal **nicht gemessen**; der Report sagt das (C2). Der nächste
  Watchdog-Lauf in CI misst sie und schließt das Issue bei Exit 0.
- **Bereits gepinnte Pins.** Ein Pin, der vor dem 13.10.2026 mit dem alten
  Text gesendet wurde, behält ihn auf Pinterest. Ein `pin_id`-Ledger für
  nachträgliche Updates existiert im Repo nicht; der nächste Repin/Refresh
  zieht den geheilten Text über die API-Engines automatisch.
- **Fremdbefund, nicht Teil von #729:** `2026-10-13-versicherung-update-…`
  fehlen Cover, Keywords, `pin_title` und `pin_description` – das ist die
  Aufgabe des SEO-Heilers (H6) bzw. der Cover-Nachproduktion, wird aber hier
  ausdrücklich **nicht** als geheilt behauptet.
- **Doku-Leiche geschlossen:** `docs/PINTEREST-SPIELBUCH.md` §6 beschrieb ein
  `scripts/pinterest_trust_shield.py` samt Report, das es im Repo nie gab.
  Der Abschnitt nennt jetzt die Prüfliste und die **tatsächlichen** Orte der
  zwölf Signale statt eines erfundenen Skripts.

- **Test-Suite-Baseline:** Die volle Suite läuft mit 3009 Tests; die zwei
  Roten (`test_bot_watchdog_meldetakt` C25/YMYL-ParseError,
  `test_reserve_artifacts` Snapshot-SHA) sind im frischen Worktree des
  Basis-Commits `e632b72` identisch rot – sie gehören nicht zu diesem PR und
  werden hier **nicht** als geheilt behauptet.

*Dieser Bericht ist der Nachweis zu #729; er wird mit dem PR geschlossen.*
