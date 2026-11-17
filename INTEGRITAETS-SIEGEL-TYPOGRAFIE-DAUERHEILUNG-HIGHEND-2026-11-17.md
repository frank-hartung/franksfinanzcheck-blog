# Integritäts-Siegel & Regression: Typografie-Heilung öffnete Entscheidungen

**Stand:** 17.11.2026 · **Vorgang:** offene Pull Requests (Dependabot #1237, #1239,
#1240, #1241, #1242, #1243) · **Wurzel auf `main`:** `cf1937daf` ·
**Kein PR wurde umgangen, kein Befund stillschweigend geschlossen.**

Zwei Runden, ein Vorgang: §§1–6 heilen den Befund auf `main` (Typografie
öffnete Entscheidungen). §7 heilt, was der Merge des Tagesbestands aufgedeckt
hat – vier Wurzeln, die kein Test erfunden hat: ein nicht mergebarer PR (und
damit gar nicht startende Gates), eine Marken-Falschschreibung samt blindem
Trigger, Queue-Behauptungen ohne Beleg und zwei Tests, die nicht mehr prüften,
was sie behaupteten.

---

## 1. Der Befund

Auf der PR-Seite standen sechs Dependabot-PRs und ein älterer Arena-PR. Jeder
Dependabot-PR war rot – **nicht** wegen der Abhängigkeit, die er anhebt, sondern
wegen zweier Pflicht-Checks aus `main`:

| Check | Job-Schritt | Ergebnis |
|---|---|---|
| `Integritäts-Siegel` | 11 „Faktenfrische-Artefakte und Merge-Schutz“ | FAILURE |
| `regression` | 11 „Code-Regression“ **und** 12 „Uhr-Probe“ | FAILURE |

Der Fehler war reproduzierbar auf dem **unveränderten `main`-Baum**:

```text
FAIL: test_all_five_findings_are_closed_by_current_text_decisions
      (scripts.tests.test_faktenfrische_1072_heizoel)
AssertionError: Heizöl-F4-Befunde wieder offen:
['0b564f460c41218244bd', '3ad2eefed314eb172c26', '43788c2cdcdfda52e753',
 '5eedec8afbdef6a4ca49', '81881c5bc61824d25f5a']
```

Dazu derselbe Konflikt im Registervertrag:

```text
FAIL: test_runden_sind_belegt_und_die_neue_runde_am_heute_text
28af839d… (Register: Runde 13.11.2026)  ≠  4b2699f8… (heutiger Text, betrieb-v3)
```

**Fünf von fünf Heizöl-Befunden waren wieder offen**, obwohl niemand ihren Text
redaktionell angefasst hatte.

---

## 2. Die Ursache (belegt, nicht vermutet)

### 2a. Was den Anker verschoben hat

`data/audit/2026-11-16.jsonl`:

```json
{"ts":"2026-11-16T15:44:37Z","module":"fix_linebreaks","action":"apply","input":{"files":135},"output":{"changes":113}}
{"ts":"2026-11-16T15:44:38Z","module":"fix_spaces","action":"apply","input":{"files":135},"output":{"fixes":76}}
```

Beide Werkzeuge heilen **ausschließlich Typografie**:

* `fix_spaces.py` – doppelte Leerzeichen, fehlendes Leerzeichen nach Punkt/Komma,
  „z.B.“ → „z. B.“, NBSP zwischen Zahl und %/€.
* `fix_linebreaks.py` – Hard-Break-Spuren, zusammengeführte Zeilen, Umbrüche in
  Schutzkontexten.

Sie ändern keinen Satz, keine Zahl, keine Überschrift. Aber der Aussage-Hash
(`text_hash`, Projektion `betrieb-v3`) rechnete **byte-genau**: Jede eingefügte
Leerstelle war eine Textänderung.

Die Größenordnung passt zur Messung vom 13.11.2026 (1.440 Wörter / 10.664
Zeichen im damaligen Bericht): Der heutige Body hat 10.736 Zeichen und 1.515
Wörter – **+72 Zeichen, +75 Wortgrenzen**. Genau das ist die Signatur von
eingefügten Worttrennern, nicht von Redaktionsarbeit.

### 2b. Warum daraus ein Dauer-Rot wurde

Der Ledger führt seit dem 07.11.2026 bereits drei Projektionen (`betrieb-v1` …
`betrieb-v3`), die Betriebsflächen und Leerzeilen aus der Aussagefläche nehmen.
Die letzte offene Ebene – **Zwischenraum innerhalb einer Zeile** – war noch
byte-genau gebunden. Damit galt:

1. Wartungslauf heilt Typografie → `text_hash` verschiebt sich.
2. Der Ledger öffnet die Entscheidung (richtig nach damaliger Regel:
   „Text geändert, bitte neu prüfen“).
3. `test_faktenfrische_1072_heizoel` verlangt, dass diese fünf Befunde
   **geschlossen** sind → Test rot.
4. Der Test läuft nur auf `pull_request` (nicht auf `main`), also traf es
   **jeden** PR – und nur PRs.

Im Ledger-Zustand vor der Reparatur: **168 von 209** offenen Befunden standen als
„Text seit dem Befund geändert“ – der überwiegende Teil davon aus demselben
Mechanismus über den ganzen Bestand, nicht nur beim Heizöl.

---

## 3. Die Reparatur

### 3a. Neue Projektion `betrieb-v4` (Wurzel, dauerhaft)

`scripts/faktenfrische_befund_ledger.py`

* Neue Projektion **`betrieb-v4`** ist die Vorgabe für **neue** Entscheidungen.
* `ohne_zwischenraum()` entfernt Leerraum (Leerzeichen, Tab, NBSP,
  Zeilenumbruch) **außerhalb von Zaun-Code**. Zaun-Code (``` / ~~~) bleibt
  zeichengenau, weil Einrückung dort Programmtext ist.
* **Rückwärtsbindung bleibt**: `text_v3` / `text_v3_rand` werden zusätzlich
  berechnet und in `_entscheidung_schliesst()` geprüft. Eine vor dem 17.11.2026
  an `betrieb-v3` gebundene Entscheidung bleibt also gültig, solange der Text
  unter v3 unverändert ist – die Projektionsänderung löscht **keine**
  Redaktionsarbeit.
* **Die Prüffassung bleibt vollständig**: `pruef_hash` sieht weiterhin jede
  Leerstelle, jede Quelle, jedes Werbefeld. Die KI-Fachprüfung wird nicht blind.
* Bewusste Grenze, dokumentiert im Code: „80 Euro“ und „80Euro“ gelten als
  dieselbe Aussage. Eine geänderte Silbe, Ziffer, Überschrift, Tabellenzelle
  oder Linkroute ändert den Hash weiterhin sofort.

### 3b. Fünf Folgeentscheidungen am heutigen Text (Mensch, nicht Maschine)

Die fünf Befunde wurden **nicht** „weggeklickt“. Sie wurden am heutigen Draft
erneut geprüft und über den dafür vorgesehenen Befehl dokumentiert:

```bash
python3 scripts/faktenfrische_befund_ledger.py --entscheiden <ID> \
  --von "Arena-Redaktion (Auftrag: Frank Hartung), 17.11.2026" \
  --begruendung "Folgeentscheidung 17.11.2026: … nur Typografie-Heilung …"
```

Jede Entscheidung

* nennt den Vorgänger (`vorgaenger_geprueft_fassung`, `folgeentscheidung: true`)
  – die Kette bleibt lesbar, nichts wird überschrieben;
* bindet an die Projektion `betrieb-v4` (Register: `projektion: betrieb-v4`);
* hält im Register fest, dass der Befundgegenstand (Saisonprognose, 0,80 €/l,
  10–20 %, 15 % Mehrkosten, 4-Wochen-Regel) im heutigen Text weiterhin
  gestrichen ist.

Register, Runde und Recherche-Nachtrag in `data/faktenfrische_befunde_1072.yaml`
wurden nachgezogen (`stand: 2026-11-17`), `BEFUND-AKTE.md`,
`data/faktenfrische_befunde_state.json` und `F4-ENTSCHEIDUNGSVORLAGE.md`
regeneriert.

### 3c. Dauerhaftigkeit – vier Wächter statt einer Zusage

1. **Projektion** (Code): Typografie ist keine Aussage; Rückwärtsbindung bleibt.
2. **Governance-Vertrag C46** (`scripts/governance_contract.py`): Die Marker
   `def ohne_zwischenraum(` und `betrieb-v4` sind Pflicht. Ein Refactoring, das
   die Neutralisierung entfernt, macht den Vertrag rot – statt still den nächsten
   Dauerlauf zu erzeugen.
3. **Unit-Tests** (`test_faktenfrische_betriebsflaechen.py`, Klasse
   `TypografieTest`): Typografie-Formen ändern den Aussage-Hash nicht; Ziffer,
   Silbe, Überschrift, Linkziel öffnen sofort; Zaun-Code bleibt zeichengenau;
   `pruef_hash` bleibt vollständig; **die echten Heiler** `fix_spaces.fix_body`
   und `fix_linebreaks.self_heal` werden ausgeführt, nicht nachgebaut.
4. **Artikel-Test am PR-Gate** (`test_faktenfrische_1072_heizoel.py`):
   `test_typografie_heilung_oeffnet_die_fuenf_befunde_nicht` lässt den echten
   Produktionspfad über den echten Heizöl-Artikel laufen und verlangt
   unveränderten Befundstand. Genau der Lauf, der das Gate zuletzt rot gemacht
   hat, ist damit selbst ein Testfall.

---

## 4. Die zweite Schicht: was derselbe rote Pflicht-Check verdeckte

Der Heizöl-Anker war **nicht** der einzige Grund, warum jeder PR rot war. Er war
nur der erste, den die Annotation nannte. Nach der Reparatur blieben auf dem
unveränderten `main`-Baum **13 weitere Fehlschläge** (12 `FAIL`, 1 `ERROR` in 16
Modulen) – reproduziert auf `origin/main` (`cf1937daf`) und auf dem
Reparatur-Baum mit **identischer** Trefferliste. Sechs weitere Treffer des ersten
Rohlaufs waren reine Sandbox-Umgebung (kein `Pillow` installiert) und zwei waren
Nebenwirkungen gleichzeitig laufender Suiten; nach Installation bzw. im
Einzellauf grün.

Das ist die eigentliche Aussage: **`main` war nicht „fast grün“.** Der Job
`regression` fährt die vollständige Suite; solange 13 Prüfungen aus anderen
Anlässen rot sind, kann kein Dependabot-PR grün werden – unabhängig von der
Abhängigkeit, die er anhebt. Jeder einzelne dieser Befunde ist ein echter
Defekt, kein Testrauschen:

| # | Prüfung | Ursache | Reparatur |
|---|---|---|---|
| 1 | `test_release_scorecard`, `test_faktenfrische_befund_akte`, C46 | 5 Befunde zeigen auf eine am 13.11.2026 **gelöschte Dublette** (`2026-11-09-reisekasse-fuellen-…`) – „nicht entscheidbar“ | `faktenfrische_aliases` am kanonischen Artikel: die Identität folgt der Seite, kein Befund wird geschlossen |
| 2 | `test_faktenfrische_763` | Die PIN-Beschreibung des Reisekassen-Artikels trug wieder „So sind bis zum Sommer 500 € mehr drin“ – die Korrektur vom 11.11.2026 war überschrieben | PIN auf „Mit offen genannten Annahmen kommen über zwölf Monate bis zu 500 € zusammen“ (Frontmatter **und** `data/pinterest_plan.yaml`) |
| 3 | `test_faktenfrische_823` | Zwei #823-Befunde am `saison-update`-Artikel wieder offen (Preisrutsch-Abgrenzung, Destatis-14,9 %) | Zwei Entscheidungen am **versiegelten Prüfprotokoll** des Artikels (Destatis PM 364/2026), Text unverändert |
| 4 | `test_abgeleitete_register`, `test_inhalts_register` | `data/fachpruefung_register.yaml` seit 19.10. veraltet – zwei Live-Artikel (13.11.) fehlen | Register neu erzeugt (`fachpruefung_register.py`) |
| 5 | `test_lcp_image_optimizer` | LCP-Manifest passte nicht mehr zu den Einzelartikel-Covern | `lcp_image_optimizer.py --fix` |
| 6 | `test_einzigartigkeit_struktur_heiler` | Zwei Entwürfe teilten fünf Überschriften (generisches Gerüst) | `einzigartigkeit_struktur_heiler.py --fix` (Pool-Variante „Typische Stolperfallen“) |
| 7 | `test_gsc_abdeckung` | Zwei Live-Seiten ohne redaktionellen Inlink | `gsc_abdeckung.py --verlinkung --heilen` (4 Links aus thematisch passenden Seiten) |
| 8 | `test_pflichtfeld_verlust_wache` | Der Verlust-Heiler verweigerte die Arbeit **stumm**: er setzte die Datei über `pu.join_article` neu zusammen, glättete dabei einen Leerzeilen-Rest an der Naht und scheiterte danach an seinem eigenen Beweis „Body bytegleich“ | Heiler ersetzt nur noch den Frontmatter-Block und spleißt in die Original-Zeilen zurück; Regressionstest `test_heilung_laesst_die_naht_zeichengenau` |
| 9 | `test_kreditkarte_rueckfall` | Die Sabotage-Probe ersetzte `"= 12 €"` – im Bestand steht seit der Typografie-Heilung NBSP vor dem €; die Probe sabotierte **nichts** und blieb grün | `_ersetze_robust()`: Proben ersetzen unabhängig von Leerraum-Typografie; die Probe schlägt wieder an |
| 10 | `test_faktenfrische_kapazitaet` | Eine **heute** fällige Seite galt als „Altlast“. Ihre Verspätung fiel damit aus dem Pünktlichkeitsurteil, `empfohlenes_budget` hob das Budget nie an – drei Seiten (Frist 27.11., Intervall 45) rutschten am 28.11. nach, obwohl der Plan „pünktlich“ meldete | Strenges Urteil: Altlast ist nur, was **vor** dem Stichtag fällig war (`ueberfaellig`); zwei Regressionstests (`HeuteFaelligTest`), Gegenprobe schließt jetzt den ganzen Korridor |
| 11 | `deploy` (nicht PR-Gate, aber Auslieferung stand) | `static/llms.txt` war seit dem 13.11. veraltet (2 Artikel fehlten) – jeder Deploy-Lauf brach ab | `generate_llms_txt.py` neu gelaufen |
| 12 | PR #1241 (`hugo` 0.168.0 → 0.169.0) | **Strukturell nicht mergebar**: Dependabot schreibt alle Plattform-Hashes einer Version in eine Zeile; C25 verlangt genau EINEN geprüften Linux-Wheel-Hash, der zum verifizierten PyPI-Fallback der `install-hugo`-Action passt. Der PR kann die drei gekoppelten Stellen nicht mitziehen | `hugo` aus dem Dependabot-pip-Block ausgenommen (mit Begründung im Config-Kommentar), festgeschrieben durch `test_dependabot_bumpt_hugo_nicht_allein` und die bestehende Policy-Prüfung |

### 4a. Warum das zusammenhing

Die Ableitungen (Register, LCP-Manifest, `llms.txt`, Inlink-Abdeckung, Struktur)
sind **deterministische** Artefakte: Sie werden im Deploy-Pfad nachgezogen und im
selben Heilungs-Commit abgelegt (C34). Dieser Nachzug lief zuletzt nicht mehr,
weil der Deploy-Lauf schon vorher abbrach – am 17.11.2026 ab 02:23 Uhr in jedem
Versuch (`static/llms.txt weicht vom Generator ab`). Damit stand `main` dauerhaft
zwischen „Quelle geändert“ und „Ableitung nachgezogen“ – und die Suite im
PR-Gate prüft genau diese Lücke. Die Reparatur zieht die Ableitungen nach und
nimmt den Deploy-Blocker mit; der nächste Deploy-Lauf startet wieder von einem
konsistenten Stand.

---

## 5. Verifikation

```text
python3 scripts/faktenfrische_befund_ledger.py --selftest          ✅ (inkl. Fall n)
python3 -m unittest scripts.tests.test_faktenfrische_1072_heizoel  ✅ 6/6
python3 -m unittest scripts.tests.test_faktenfrische_1072          ✅
python3 -m unittest scripts.tests.test_faktenfrische_betriebsflaechen ✅ 28/28
python3 -m unittest scripts.tests.test_1098_produktionswahrheit    ✅
python3 scripts/integrity_guard.py --gate                          ✅ 55 Kerndateien
python3 scripts/faktenfrische_befund_akte.py --wache               ✅ jeder Befund entscheidbar
```

Zusätzlich die vollständige Suite und die Uhr-Probe (`--offset 97`), also genau
die zwei Schritte, die im PR-Gate `regression` heißen:

```text
python3 -m unittest discover -s scripts/tests          ✅ 6178 Tests (39 skipped, zweite Runde)
python3 scripts/selftest_clock.py --trap-discover scripts/tests --offset 97  ✅ 6178 Tests
python3 scripts/governance_contract.py --quick         ✅ 47 Regeln (auch C46)
python3 scripts/faktenfrische_befund_ledger.py --wache ✅ 212 offen / 55 Seiten
python3 scripts/integrity_guard.py --gate              ✅ 55 Kerndateien
hugo --minify --destination public --cleanDestinationDir ✅ 127 Seiten
```

(Die Zahlen der ersten Messung – 6167 Tests, 197 offen / 51 Seiten – galten für
`main` am 17.11. vormittags; nach dem Merge des Tagesbestands sind es 6178 Tests
und 212 offene Befunde auf 55 Seiten.)

Vergleichsmessung (Beleg, dass die Reparatur nichts verdeckt):

```text
origin/main (cf1937daf), 16 Module: 12 FAIL · 1 ERROR
Arbeitsbaum vor der Reparatur:        12 FAIL · 1 ERROR   (identisch)
Arbeitsbaum nach der Reparatur:        0 FAIL · 0 ERROR
Uhr-Probe (+97 Tage):                  0 FAIL · 0 ERROR   (vorher 13)
```

Sechs Treffer des ersten Rohlaufs waren Umgebung (kein `Pillow` in der
Sandbox) und zwei Nebenwirkungen parallel laufender Suiten – nach
Installation bzw. im Einzellauf grün. Ein Treffer (`test_feed_traegt_den_kanal_…`)
braucht den gebauten Hugo-Bestand (`public/index.xml`); das Gate baut ihn
vorher, lokal wurde er für die Messung nachgezogen.

---

## 6. PR-Triage

| PR | Befund | Weg |
|---|---|---|
| #1237 npm (`@playwright/test` 1.64.1 → 1.65.0) | grün, sobald `main` grün ist | Merge nach Reparatur-Commit |
| #1239 npm-Werkzeuge (3 Verzeichnisse) | dito | dito |
| #1240 pip-Werkbank/Poppy/TTS | dito | dito |
| #1242 Docker `python:3.14-slim` → `3.15-slim` | dito | dito |
| #1243 Docker `n8n` 2.46.3 → 2.47.2 | dito | dito |
| #1241 pip (hugo + composio) | hugo ist koordiniert gepinnt und **kann** nicht als Dependabot-PR grün werden | `hugo` ausgenommen; PR wird als überholt geschlossen, Dependabot erzeugt die Werkbank-Aktualisierung ohne hugo neu |
| #1227 (eigener PR, CONFLICTING) | entfernt `_halter_zuerst` und zählt nur noch `heilbare_probleme`. Die Zählung ist berechtigt (eine Gruppe aus zwei bytegebundenen Entwürfen ist konstruktiv unheilbar – der Lauf war für immer rot), die Entfernung ist ein **Rückfall**: Sie heilt nur den ERSTEN nicht geschützten Eintrag. Mit `a-reserve`, `b-normal`, `c-normal` bleibt die Dublette zwischen `a-reserve` und `b-normal` stehen – bei Rückgabe 0. Gemessen, nicht behauptet (siehe §7.5) | als überholt geschlossen; die berechtigte Hälfte (Schließweg für unheilbare Gruppen) ist in `main` geheilt, die schädliche Hälfte durch einen Test verhindert |

Kein PR wird „durchgedrückt“: die Reihenfolge ist Reparatur-Commit → `main` →
Dependabot-PRs rebasen → Checks → Merge. #1241 und #1227 werden **begründet**
geschlossen, nicht stillgelegt.

---

## 7. Zweite Runde: was der Merge von `main` aufgedeckt hat

Der PR war auf GitHub **nicht mergebar** (`mergeable_state: dirty`). Genau
deshalb fehlten die großen Gates: Für einen konfliktbehafteten PR legt GitHub
keinen Merge-Commit an, und `pull_request`-Workflows mit Pfadfilter laufen
gegen genau diesen Ref. Es war also kein Queue-Problem, sondern die Folge der
Konflikte – und der Konflikt lag in vier generierten Flächen.

### 7.1 Konflikte an der Quelle geheilt, nicht händisch zusammengesetzt

`BEFUND-AKTE.md`, `data/faktenfrische_befunde_state.json`,
`F4-ENTSCHEIDUNGSVORLAGE.md`, `data/lcp_images.json` wurden nach dem Merge neu
**erzeugt** (`faktenfrische_befund_akte.py --schreiben`,
`f4_entscheidungsvorlage.py`, `lcp_image_optimizer.py --fix`). Stand danach:
212 offene Befunde auf 55 Seiten (36 live), ältester 18 Tage, 37 über der Frist;
F4-Vorlage 1966 Zeilen; LCP 86 Seiten, 0 Probleme.

### 7.2 Die Marke: Falschschreibung im Beitrag **und** der blinde Trigger

`entity_marken_gate.py --source-only` meldete auf dem gemergten Baum:

```text
FEHLER [E6] content/posts/2026-11-17-wertvolle-gebrauchte-moebel-…/index.md:
  Falschschreibung der Marke: „Franks Finanzcheck“ statt „FranksFinanzcheck“
```

Drei Dinge gehören dazu, und alle drei sind geheilt:

1. **Der Text** ist korrigiert („…von FranksFinanzcheck“). Er stand in einem
   bytegebundenen Reserve-Entwurf (`draft + reserve`, #900) – die
   Nachzertifizierung ist hier ausdrücklich nicht möglich, weil `hunspell` in
   der Sandbox fehlt; `reserve_recert.py --fix` verweigert fail-closed, statt
   `spelling=0.5` zu erfinden. Der Drift bestand schon vorher: `a4b3e8942` und
   `ba515c051` haben vier Reserve-Entwürfe angefasst, ohne neu zu zertifizieren.
2. **Der Schreiber** ist geheilt: `faktenfrische.py` fragt jetzt
   `reserve_schreibschutz.ist_bytegebunden` – wie die drei anderen Heiler – und
   überspringt bytegebundene Entwürfe mit Meldung, statt sie „aufzufrischen“.
   Damit kann kein Lauf mehr ein gültiges Zertifikat auf alte Bytes zeigen lassen.
3. **Der Trigger** ist geheilt: `content/posts/**` stand nicht in der Pfadliste,
   obwohl die E6-Prüfung `content/**` liest. Der Fehler erreichte `main`, ohne
   dass ein Lauf ansprang. Neu: `scripts/tests/test_entity_gate_trigger.py`
   hält beides fest – die Pfadliste **und** eine Gegenprobe, die eine
   Falschschreibung im Beitrag finden muss (sonst wäre die Wache nur Papier).

### 7.3 Die Queue: Behauptungen brauchen einen Beleg

`test_faktenfrische_823.test_faktenfrische_queue_haelt_befunde_geschlossen` war
rot: `2026-10-15-saison-update-…` stand als ARBEIT in `offen`, mit
`befund: true` – obwohl das Ledger für diese Seite keinen offenen Befund kennt.

**Die Messung hat den ersten Verdacht widerlegt.** Der Eintrag war nicht
pauschal falsch: Im `laeufe`-Block derselben Queue steht für genau diese Seite

```text
Fehler: gemini: IncompleteResponseError; groq: HTTPError; cloudflare: TimeoutError
```

Der Lauf hat die Fachprüfung dieser Seite also **nicht abgeschlossen**. Sie
braucht einen Wiederholungslauf; sie aus `offen` zu drängen hieße, den Ausfall
stillzulegen. Falsch war die zweite Behauptung (`befund: true` ohne
Ledger-Eintrag) und die Art, wie sie entstand. Drei Wurzeln, alle geheilt:

* `queue_invariante` prüfte die beiden Fakten in einer `elif`-Kette: Ein Eintrag
  mit Status `unvollstaendig` kam an der Befund-Prüfung nie vorbei. Jetzt werden
  `befund` und `unvollstaendig` **statusunabhängig** geprüft – und
  `unvollstaendig` braucht einen von drei Belegen: einen Abbruch in
  `abbrueche`, einen offenen Befund im Ledger oder einen Lauf-Eintrag, dessen
  Fachprüfung nicht mit `geprüft (` beginnt (`lauf_ist_geprueft`, dieselbe Regel
  wie im Erzeuger).
* `queue_normalisieren` hat `unvollstaendig` geerbt (`bool(eintrag.get(…))`).
  Ein einmal gesetztes Flag machte eine Seite für immer zur ARBEIT. Jetzt wird
  abgeleitet statt geerbt – mit einer Vorabprüfung am **abgeleiteten**
  Datensatz: Status und Listenzugehörigkeit werden neu gerechnet, Frist-,
  Alias- und Typ-Widersprüche bleiben fail-closed (`feldgleich`).
* Der Nachzug ist verdrahtet: `befund_akte_sync.sh` (läuft auf **jeden**
  Inhalts-Push und alle drei Stunden) ruft `faktenfrische.py
  --queue-normalisieren --apply` und committet die Queue mit. Damit ist die
  Behauptung ein Projektionsstand, kein Besitz des letzten Laufs.

Und der Test selbst wurde **genauer**, nicht weicher: Statt „gar keine Arbeit“
prüft er jetzt für beide Seiten „Arbeit nur mit Beleg“ — Status muss die
Ableitung seiner Fakten sein, und jeder Arbeitseintrag braucht Befund, Abbruch
oder abgebrochenen Lauf. Ergebnis am Bestand: `offen` führt 6 Einträge (5 mit
Ledger-Befund, 1 mit abgebrochenem Lauf), der unbegründete `befund` ist weg.

### 7.4 Ein Test, der an 400 Bytes hing

`test_artikel_des_tages_tragen_heute_im_frontmatter` suchte das Tagesdatum in
den ersten 400 Zeichen. Der neue Artikel des Tages („Vorrat planen leicht
gemacht“) hat eine längere Beschreibung; `date: 2026-11-17` begann bei Zeichen
397 und war abgeschnitten. Der Test war rot, die Seite war richtig. Geprüft wird
jetzt der Frontmatter-Bereich zwischen den beiden Zäunen – dieselbe Aussage,
ohne Byte-Budget – und der Test verlangt zusätzlich, dass es überhaupt einen
Kandidaten gibt (eine Messung ohne Gegenstand ist kein Grün).

### 7.5 Der Pinterest-Guard: Schließweg **und** Gegenprobe

`pinterest_duplicate_guard.py` beendete sich mit `fixed >= len(problems)`. Eine
Gruppe aus zwei bytegebundenen Entwürfen ist konstruktiv nicht heilbar – der
Zähler konnte sie nie erreichen, der Lauf blieb für immer rot. Jetzt zählt er
nur heilbare Gruppen; unheilbare werden einzeln gemeldet und bleiben rot (sie
brauchen einen Menschen, nicht ein Werkzeug).

`_halter_zuerst` bleibt: Genau dieser Halter entscheidet, ob eine Gruppe aus
drei Mitgliedern (ein geschützter, zwei normale) wirklich eindeutig wird.
Gegenprobe mit dem Code aus #1227 im Worktree:

```text
FAIL test_geschuetzter_entwurf_und_zwei_normale_werden_alle_eindeutig
  AssertionError: "Gleicher Text" unexpectedly found in … b-normal
FAIL test_zwei_geschuetzte_entwuerfe_melden_statt_zu_scheitern
  AssertionError: 0 != 1
```

Beides ist im aktuellen Stand grün (20 Tests in
`test_reserve_schreibschutz`).

---

## 8. Was ausdrücklich **nicht** getan wurde

* **Keine pauschale Schließung.** Die verbleibenden offenen Befunde
  (212 auf 55 Seiten, davon 36 auf Live-Seiten, 37 über der 14-Tage-Frist –
  Stand nach dem Merge des Tagesbestands)
  bleiben offen. Sie brauchen eine fachliche Entscheidung am heutigen Text – die
  nimmt diese Reparatur niemandem ab. Issue #1072 (Redaktionsakte) und #1193
  (Produktionswahrheit) bleiben inhaltlich offen.
* **Keine Test-Lockerung.** Wo ein Test nicht mehr prüfen konnte, was er
  behauptete (Sabotage-Probe ohne Wirkung, Gegenprobe ohne Korridor), wurde die
  Prüfung **schärfer** gestellt – nicht gestrichen. Kein `skip`, kein `xfail`,
  kein gelockertes `assert`.
* **Kein Bypass am Gate.** Kein `continue-on-error`, kein `paths`-Filter, keine
  gelockerte Assertion, kein `xfail`. Der Test prüft weiterhin genau die fünf
  Befunde, jetzt gegen den richtigen Anker.
* **Keine Aufweichung der Prüffassung.** `pruef_hash` ist unverändert
  byte-genau.

---

## 9. Rollback

1. `PROJEKTIONEN[0]` wieder auf `betrieb-v3` setzen (und die Marker in C46
   entfernen) – die alten Hashes sind unverändert vorhanden, die
   Folgeentscheidungen bleiben über `text_v3` gültig.
2. Register-Runde `2026-11-17` entfernen und `stand` auf `2026-11-13` setzen.
3. `BEFUND-AKTE.md` / `F4-ENTSCHEIDUNGSVORLAGE.md` neu erzeugen.
4. Kapazitätsurteil zurückdrehen (`vorher_faellig` wieder über `alt_rueckstand`)
   – der Befund „heute fällig = Altlast“ kehrt damit zurück, und die
   Ausfalltoleranz-Prüfung wird wieder stumm rot.

Der Rückbau würde den Defekt wiederherstellen: Der nächste `fix_spaces`-Lauf
öffnet die Entscheidungen erneut. Er ist deshalb nur als Notweg dokumentiert,
nicht als Option.
