# 🩺 Dauerheilung der roten Merge-Gates (22.11.2026) – sechs gemeldete Prüfungen, eine siebte nachgetragen

**Datum:** 22.11.2026 · **Auftrag:** „Bitte vollständig dauerhaft auf Highend-Level
einer Profi-Agentur beheben." · **Anlass:** Übergabe-Notiz „Beim Merge zu beachten":
Beim Squash-Merge waren auf dem PR die Prüfungen **Integritäts-Siegel**,
**Playwright-Suite**, **YMYL-Siegelprüfung**, **Entity-Marken-Gate**, **Gate** und
**Skript-Syntax** rot; die Rohlogs waren nicht abrufbar (EOF/Transportfehler), die
Befunde wurden deshalb zurückgestellt.

**Ergebnis vorweg:** Alle sechs gemeldeten Klassen sind auf dem liegenden Bestand
grün gemessen – nicht umgangen, sondern an der Ursache geheilt. Eine einzige
redaktionelle Zahl (Titel 64 Zeichen gegen die Grenze 60) war die gemeinsame
Ursache von **drei** der sechs roten Gates; eine Trigger-Vertrags-Drift im
gemeinsamen Schreibweg die vierte.

**Eine siebte Prüfung kam während der Arbeit dazu.** Der Job `regression` war auf
**jedem** PR rot, nicht nur diesem, und die erste Fassung dieser Akte führte ihn
als Nebenbefund „außerhalb des Auftrags" – mit einer Begründung, die sich als
falsch erwies (Abschnitt 1, Lehre 4). Vier Bestandstests sind deshalb in
Abschnitt 8 als **Heilung G** nachgetragen. Darüber hinaus wurden zwei Defekte
geheilt, die die Übergabe nicht nannte, weil sie niemand sehen konnte:

- **Heilung C** – eine unerkannte Drift-Klasse in der Cover-Herkunft: 13
  Belege im Live-Bestand beschrieben die Bytes einer Vorfassung. Als messbare
  Regel (`beleg_veraltet`) im Prüfer verankert, damit sie nicht erneut still
  durchläuft.
- **Heilung D** – das Titel-Gate stand bei **Exit 1** (R1), weil der Heiler
  `ensure_colon_title()` Fragetitel ohne Anhang unverändert zurückgibt, während
  `deploy.yml` den Befund mit `|| echo` schluckt.

- **Heilung G** – der Job `regression` war rot, auf **jedem** PR: vier Bestandstests
  über `unittest discover -s scripts/tests`. Ein Parser-Bug in der Inhalts-Wache
  (las nur doppelt quotiertes Frontmatter), eine haarscharf verfehlte
  Lesbarkeits-Schwelle, eine wortgleiche Dopplung zweier Live-Artikel und ein
  Heiler-Artefakt, das einen Rechtssatz verdrängt hatte.

Ehrlich dazugesagt und **korrigiert**: Die erste Fassung dieser Akte führte die
vier Bestandstests als Nebenbefund, den kein Workflow rufe. Das war falsch –
`discover` erreicht jedes Modul, ob ein Workflow es beim Namen nennt oder nicht
(Abschnitt 1, Lehre 4). Die vier Befunde sind Teil des Auftrags und in
Abschnitt 8 geheilt; was danach offen bleibt, steht in Abschnitt 9.

---

## 1. Befund – was rot war und woran

Rohlogs waren aus dieser Umgebung nicht lesbar
(`gh run view --log-failed` → `EOF` auf `results-receiver.actions.githubusercontent.com`).
Der lesbare Weg sind die **Annotationen** der Check-Runs
(`gh api repos/…/check-runs/{job_id}/annotations`) und die Step-Conclusions
(`gh run view <id> --json jobs`). Damit ließ sich jeder rote Schritt benennen:

| Rote Prüfung | Roter Schritt | Befund im Klartext |
| --- | --- | --- |
| YMYL-Siegelprüfung (45012387630) | „Siegel- und Schreibschutz testen" | Bestandstest `test_bestand_einschliesslich_entwuerfe_erfuellt_metadatenvertrag` rot: **M1** Titel 64 Zeichen (max. 60) im Kfz-Artikel |
| Playwright-Suite (44913643184, 44921867790, 44927101639) | Schritt 19 „Metadaten-Wache – Quelle" | dieselbe **M1**-Zahl; Schritte 20–22 (SEO-Spider, E2E-Suite, Design-Audit) wurden deshalb **übersprungen** – die Suite kam nie bis zu einem Test |
| Deploy / Auslieferungs-Siegel (44995829205) | „Auslieferungs-Siegel" | Werkzeugbefund `metadaten-wache`, C34: Auslieferung läuft weiter, Befund bleibt offen |
| Skript-Syntax (44941227657) | Schritt 7 „Trigger-Wache" | **W1**: `code-selbstheilung.yml` ruft `scripts/git_sync.sh` auf, trägt die Datei aber in keinem `paths:`-Filter (push *und* pull_request) |
| Entity-Marken-Gate (44936582442) | „Site bauen" | Hugo: `2026-11-01-energieeffiziente-geraete…/index.md:23:3 mapping key "aenderungsgrund" already defined at [19:3]` |
| Integritäts-Siegel / Gate (44936582446, 44936582328) | „Artefakt-Wächter", „Governance-Vertrag C1–C49" | auf Commit `84f3bfcc` – derselbe Hugo-Duplikat-Bestand; bei `5e8233e` bereits geheilt |
| **Code-Regression** `regression` (45026488760, Job 137220544932) | Schritt 11 „Code-Regression – Suite und Selbsttests" | **vier Bestandstests** rot über `unittest discover -s scripts/tests` – Flesch 59.9 < 60.0, 5 gemeinsame 7-Wort-Phrasen, fehlender Rechtssatz, FF3 × 3. Rot auf **jedem** PR, nicht nur diesem. *Nachgetragen:* diese Zeile fehlte in der ersten Fassung der Akte, weil der Auftrag fälschlich auf die sechs namentlich gemeldeten Prüfungen verengt wurde – siehe Lehre 4 und Abschnitt 8 |

**Vier Lehren aus dieser Tabelle**, die über den Einzelfall hinausgehen:

1. **Eine Zahl, fünf Prüfungen.** M1 ist kein „SEO-Hinweis": Er steht im
   Bestandstest der YMYL-Siegelprüfung, im E2E-Vorlauf *vor* der Browser-Suite und
   im Auslieferungs-Siegel. Wer ihn offen lässt, verliert drei Gates gleichzeitig
   – und im E2E-Fall die gesamte Suite, weil sie nie startet.
2. **Rot vor der Messung ist teurer als rot in der Messung.** Die Playwright-Läufe
   starben in Schritt 19 von 22. Der teure Teil (Browser, Bau, 184 Tests) lief
   nicht – es gab also weder einen Befund aus der Suite noch einen Freispruch.
3. **Ein Gate, das nie wieder misst, ist ein stilles Gate.** `skript-syntax.yml`
   maß die Trigger-Drift am 21.11. 19:29 rot – und danach **nicht mehr**, weil der
   Automationslauf `5e8233e` (08:45) mit `GITHUB_TOKEN` committet und GitHub
   Folge-Workflows für solche Commits bewusst nicht auslöst. Der rote Stand blieb
   einfach liegen.
4. **„Kein `run:` mit diesem Namen" heißt nicht „läuft nie".** Die erste Fassung
   dieser Akte schloss aus `grep -rn <testname> .github/workflows/` → keine
   Treffer, dass vier rote Bestandstests kein Gate berühren, und empfahl sie als
   Nebenbefund in einen Folge-PR. Der Schluss war falsch: Der Job `regression`
   fährt `unittest discover -s scripts/tests` und erreicht damit **jedes** Modul,
   ob ein Workflow es beim Namen nennt oder nicht. Wer die Aufrufer einer Prüfung
   sucht, muss den **Entdeckungsmechanismus** suchen (`discover`, `glob`,
   `selftest_runner`-Entdeckung), nicht nur die namentliche Nennung. Die Folge
   war konkret: Das lauteste Tor des PR blieb rot, während die Akte es als
   „außerhalb des Auftrags" führte. Geheilt in Abschnitt 8.

---

## 2. Heilung A – Titel, Siegel und die ganze Verdrahtung (M1)

> **Stand nach dem Rebase (22.11.2026, 12:2x): Diese Heilung ist vom Bestand
> überstimmt und wurde zurückgenommen.** Während der Arbeit hat `main` denselben
> M1-Befund selbst geheilt – PR **#1315**, Commit `dccdf19` „M1-Heilung: kfz-Titel
> auf 59 Zeichen", Siegel `35ed9850…`. Hauspolitik ist „Bestand gewinnt"
> (`GIT_SYNC_BESTAND_POLICY`, #590), also steht jetzt **der Titel aus #1315** im
> Baum: `Kfz-Versicherung vergleichen: Was ändert sich beim Beitrag?` (59 Zeichen).
> Zurückgenommen wurden dafür: eigener Titel, eigenes Siegel, eigener Eintrag in
> `data/editorial_review_history.jsonl` (nur der **eigene**, überstimmte – die
> append-only-Kette des Bestands blieb bitgleich), eigene Cover-Bytes, eigene
> H1-Erwartung in `e2e/archivredaktion.spec.mjs`.
>
> **Zwei Dinge bleiben aus dieser Heilung, und sie sind der Punkt:**
> 1. #1315 hat die E2E-Assertion **robuster** gemacht als ich: Der Test prüft jetzt
>    `h1.count() === 1` und Substanz, nicht mehr den exakten Titeltext – mit
>    Begründung im Kommentar („macht aus einer Redaktionsentscheidung einen
>    Code-Test"). Meine Fassung hätte bei jeder zulässigen Titeländerung erneut
>    gebrochen. Der Bestand war hier besser; übernommen.
> 2. Die **Kette** (Titel → Siegelweg → Cover → Beleg → Register) ist dieselbe, die
>    #1315 gegangen ist – und genau sie hat die Beleg-Drift aus Abschnitt 4
>    erzeugt. Der Befund ist also nicht „mein Titel", sondern „jede Titelheilung
>    dieser Art lässt Belege altern". Das ist mit `beleg_veraltet` jetzt messbar.
>
> Der Rest dieses Abschnitts dokumentiert den **gegangenen Weg** und seine
> Messungen, wie sie zum Zeitpunkt der Ausführung waren – als Nachweis, dass die
> Klasse verstanden und nicht geraten ist.

**Ursache:** `content/posts/2026-08-26-kfz-versicherung-vergleich-bis-zu-800-euro-sparen/index.md`
trug in Zeile 3 den Titel
`Kfz-Versicherung vergleichen: Was ändert sich außer dem Beitrag?` – **64 Zeichen**
gegen die Grenze **60** (M1 der Metadaten-Wache). M1 ist bewusst **nicht** per
`--fix` heilbar: Wortwahl ist Redaktion, nicht Automatik.

**Heilung (redaktionell, minimal-invasiv):**

```
vorher (64): Kfz-Versicherung vergleichen: Was ändert sich außer dem Beitrag?
nachher (58): Kfz-Versicherung vergleichen: Was zählt außer dem Beitrag?
```

Hauptkeyword, Doppelpunkt-Konvention (R1), Kernaussagen, Zahlenprotokoll, Quellen
und Belegkette bleiben unverändert; gekürzt wurde ausschließlich das
Fragewort im Untertitel. Kollisionsprüfung vorab: im Bestand existiert genau ein
Kfz-Titel, keine Verwechslungsgefahr.

**Warum das nicht mit einem Edit erledigt ist** – der Freigabevertrag
(`docs/ANLEITUNG-REDAKTIONELLE-YMYL-PRUEFUNG.md`) bindet den Titel in den
Siegel-Fingerprint (`content_fingerprint()`, `editorial_review_gate.py:245`).
Eine Titeländerung **bricht** die Freigabe; automatisches Umversiegeln ist
verboten (`automatic_change_findings()`). Der sanktionierte Weg wurde vollständig
gegangen:

```bash
$P scripts/belegketten_wache.py --nur-hochrisiko --report
$P scripts/editorial_review_gate.py --seal --file content/posts/<slug>/index.md   # append-only History
$P scripts/editorial_review_gate.py --published --strict                          # hartes Deploy-Gate
```

Neues Siegel: `inhalt_sha256 c14b3f5e0492404632ca6282a014ee71080f33d167bd9b8dd43a6a3cee679077`,
Eintrag in `data/editorial_review_history.jsonl` (append-only, kein Umschreiben der
Vergangenheit), `aenderungsgrund` um den Nachtrag vom 22.11.2026 ergänzt,
`pruefdatum`/`naechste_pruefung` unverändert (19.11.2026 / 05.01.2027).

**Verdrahtung nachgezogen** (ein Titel hat in diesem Haus mehr als eine Stelle):

| Stelle | Weg | Stand |
| --- | --- | --- |
| `content/posts/…/index.md:3` | Hand (Redaktion) | ✅ |
| `e2e/archivredaktion.spec.mjs:5` | Hand + Kommentar, warum die H1-Erwartung am Titel hängt | ✅ |
| `static/images/covers/**` (15 Dateien) | `generate_covers.py --slug <slug>` (deterministisch, IPTC-Herkunft) | ✅ |
| `data/covers_manifest.json`, `data/fcp_images.json` | Generator | ✅ |
| `static/llms.txt:99` | `abgeleitete_register.py --fix` (**nie** von Hand) | ✅ |
| `data/fachpruefung_register.yaml`, `BEFUND-AKTE.md` | `abgeleitete_register.py --fix` | ✅ |
| `data/social/kalender/*.ics\|*.md`, `static/kalender/*` | `scripts/social_calendar.py --build` am Ende jedes Autopilot-Laufs – die Kalender ziehen den Titel **selbst** nach (Plan referenziert per Slug) | ✅ selbstheilend, Abschnitt 9 |
| `docs/kfz-artikelfassung-2026-11-19.md:3`, `docs/kfz-fachrevision-2026-11-19.md:11`, `FAKTENFRISCHE-1072-NACHPRUEFUNG-2026-11-20.md:199` | zeitgebundene Belege: bleiben **unverändert** (ein Prüfprotokoll vom 19.11. darf nicht den Titel vom 22.11. zitieren) | ✅ bewusst |

**Messung vorher / nachher:**

```
vorher:  ❌ [M1] … Titel 64 Zeichen (max. 60)      → 145 Dateien | Befunde: 1
         roter Test: test_bestand_einschliesslich_entwuerfe_erfuellt_metadatenvertrag
nachher: ✅ 145 Dateien | Befunde: 0
         ✅ ymyl_siegel_wache.py         → 138 Artikel · 0 Befunde
         ✅ editorial_review_gate.py --published --strict → 90 Artikel · 4 Hochrisiko · 4 freigegeben · 0 blockiert
         ✅ frontmatter_wache.py         → 174 | Blocker: 0 | Hinweise: 0
         ✅ H1 im Bau: genau eine, Text = neuer Titel
```

---

## 3. Heilung B – Trigger-Vertrag im gemeinsamen Schreibweg (W1)

**Ursache:** `code-selbstheilung.yml` ruft im Schritt „Geprüften Heilungs-PR
bereitstellen" `bash scripts/git_sync.sh` auf, führte die Datei aber in **keiner**
`paths:`-Liste. Folge: Eine Änderung am gemeinsamen Schreibweg (Notbremsen,
Nachzüge) löste den Lauf nie aus – der Prüfer, der `git_sync.sh` mitbewegt, lief
nicht mit.

**Heilung:** `scripts/git_sync.sh` in **beide** Listen (`push` und `pull_request`,
W3 verlangt Deckungsgleichheit), mit Begründungskommentar. Muster aus dem Haus
bestätigt: `abhaengigkeits-selbstheilung.yml:34/57`, `befund-akte-nachziehen.yml:43`.

```
vorher:  ❌ 2 Befund(e) (104 Workflows)   [W1 push + W1 pull_request]
nachher: ✅ Workflows geprüft: 104 · Befunde: 0
```

**Zeitlauf-Backstop (die eigentliche Dauerheilung):** Der Einzelfall war nach
einem Tag veraltet – die **Klasse** nicht. Ein Gate, das nur auf `push`/
`pull_request` hört, misst `GITHUB_TOKEN`-Commits niemals, und genau die machen
in diesem Haus einen erheblichen Teil der Schreibvorgänge aus
(Automationslauf „Schaltwerk", Selbstheilung, Catchup). Deshalb hat
`skript-syntax.yml` jetzt zusätzlich

```yaml
schedule:
  - cron: "23 */4 * * *"     # misst den liegenden Bestand unabhängig vom Schreiber
workflow_dispatch: {}        # Handlauf für die Nachmessung nach einer Heilung
```

Hausart und bewusst versetzt zu den übrigen Zeitläufen (`deploy-catchup` `20 * * * *`,
`befund-akte-nachziehen` `47 */3 * * *`, `code-selbstheilung` `38 6 * * *`,
`abhaengigkeits-selbstheilung` `18 6`), damit nicht alle Läufe zur selben Minute
auf denselben Runner drängen.

**Notbremse im Schreibweg (neu, 22.11.2026):** Der Zeitlauf misst *später*; er
verhindert nicht, dass Drift überhaupt committed wird. Deshalb prüft
`scripts/git_sync.sh` jetzt **vor** dem Commit/Push selbst:

```bash
trigger_notbremse <staged|push>   # scripts/git_sync.sh, nach syntax_notbremse (#864)
```

Sie wählt die Pfade des eigenen Vorgangs
(`git diff --cached --name-only --diff-filter=ACMRD` bzw.
`git diff --name-only --diff-filter=ACMRD "origin/$BRANCH...HEAD"`), filtert auf
`.github/workflows/* scripts/* tools/* e2e/*` und ruft
`scripts/trigger_wache.py --check --bezogen-auf <pfad>` auf. Bei Befund:
`::error::` mit **benannter** Heilung (W1: Datei in *beide* Listen; W2: Filtereintrag
entfernen oder Datei wiederherstellen) und Abbruch – im staged-Modus zusätzlich
`git reset -q`, damit nichts Halbes liegen bleibt. Fehlt die Wache im Baum, wird
still übersprungen; fehlt `python3`, wird **gewarnt statt blockiert** (Grenze wie
#864: eine Notbremse darf nicht ausfallen, weil ihr Werkzeug fehlt).

**Dafür bekam die Wache eine Bezugsauswahl** (`relevante_workflows(root, pfade)`):
Ein Schreibweg darf nicht am Bestand fremder Altlasten scheitern – sonst blockiert
ein unbeteiligter roter Workflow jeden Commit. Bezüge sind dreifach, und der dritte
ist der entscheidende:

1. die Workflow-Datei selbst liegt im Vorgang (Basename **oder** Repo-Pfad),
2. der Workflow ruft eine der Dateien auf (`aufrufe(text, root)`),
3. ein `paths`/`paths-ignore`-Eintrag **deckt** einen der Pfade (`gedeckt()`) –
   nötig für **W2**, weil `aufrufe()` nur *existierende* Dateien sieht, ein Commit
   eine aufgerufene Datei aber **löschen** kann.

`--bezogen-auf PFAD` ist wiederholbar; der Bericht trägt die Auswahl offen aus
(„der übrige Bestand ist in diesem Lauf NICHT gemessen"), und eine **leere**
Auswahl meldet ausdrücklich „Das ist KEIN Grün für den Gesamtbestand". Die
Bestandsmessung im Gate bleibt unverändert scharf.

**Schärfe nachgewiesen, nicht behauptet** – Sabotage-Gegenproben der Auswahl:

| Sabotage | Erwartung | Ergebnis |
| --- | --- | --- |
| Auswahl zu breit (`return workflow_dateien(root)` nach der Zielmengenbildung) | rote Proben | ✅ 4 Proben rot, Exit 2 |
| Auswahl zu schmal (Filter-Nennung ignoriert) | rote Proben | ✅ 3 Proben rot, Exit 2 |
| Selbsttest (`trigger_wache.py --selftest`, Block 6 „Bezugsauswahl", 8 Proben) | grün | ✅ Exit 0 |
| Unittests `scripts.tests.test_trigger_wache` (neu: Klasse `BezugTest`) | grün | ✅ 23 Tests, OK |
| Unittests `scripts.tests.test_git_sync` (neu: Klasse `TriggerNotbremseTests`) | grün | ✅ 65 Tests, OK |

Die `TriggerNotbremseTests` prüfen beide Modi und beide Richtungen: Vollmodus
lehnt eigene W1-Drift ab, ein gedeckter Filter geht durch, `--push-only` lehnt ab,
**fremde Altlast blockiert den eigenen Commit nicht**, und ein reiner Inhalts-Commit
läuft die Bremse gar nicht erst an (kein Zeitverlust).

---

## 4. Heilung C – Beleg-Drift: die unerkannte Klasse in der Cover-Herkunft

**Befund bei der Nachprüfung** (nicht Teil der Übergabe, aber derselben Familie):
`ki_cover_herkunft.py --attestieren --trocken` meldete `13 geplant, 133 aktuell`;
die Inline-Diagnose zeigte **131 aktuell, 2 ohne Beleg, 13 mit veralteter sha256** –
alle `geprueft_am 2026-11-21`, darunter der Kfz-Artikel und sieben Beiträge vom
21.11.

**Ursache (Struktur, nicht Tippfehler):** Eine Titeländerung zieht
`check_covers.py --fix` / `generate_covers.py` nach, die Cover werden neu
gerendert – **die Bytes ändern sich**, `cover.ki_pruefung.sha256` bleibt aber auf
der Vorfassung stehen. `--pruefen` verglich bisher nur **Pixel**, `--heilen` zog
nur die Klasse `ohne_beleg` nach. Ergebnis: 13 Herkunftserklärungen im
Live-Bestand, die eine Datei beschreiben, die es so nicht mehr gibt – und **kein**
Prüfer, der es merkt.

**Warum die Bytes sich überhaupt ändern – gemessen, nicht vermutet.** Das
Werkzeug nennt sich selbst „deterministisch" (`generate_covers.py:392`,
`_herkunft_markieren()`), und die **Pixel** sind es. Die **Bytes** sind es nicht:

```
sha256(static/images/covers/2026-11-12-…-streaming….jpg)
  Fassung im Commit:            7cf26fbea52c9e33…
  1. Neurender (gleicher Titel): 29f9a52bd4023317…
  2. Neurender (gleicher Titel): bcbb76058d0c25b3…
```

Drei Renders, drei Hashes – ohne dass sich Titel, Design oder Inhalt geändert
hätten. Ursache ist eine Zeile:

```python
# scripts/ki_bild_markierung.py:90
zeit = datum or dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
```

`generate_covers.py` ruft `paket_bauen(...)` **ohne** `datum` auf, also landet die
Render-Uhrzeit im XMP-Herkunftspaket der JPG. Jeder Lauf – ob `check_covers --fix`
im Deploy, `content-engine-v2 --heilen` oder eine manuelle Titelheilung – erzeugt
damit neue Bytes und lässt jeden `sha256`-Beleg altern. **Das ist der eigentliche
Motor der Drift-Klasse**, und er läuft unabhängig von Redaktion.

Bewusst **nicht** in diesem PR geändert: Die Zeile zu fixieren (z. B. `datum` =
Veröffentlichungsdatum des Beitrags statt Render-Uhrzeit) ändert die Semantik des
KI-Herkunftsnachweises für **alle** 144 Cover und berührt den Vertrag von
`ki_provenienz_gate.py` (M1–M4). Das ist ein eigener Auftrag mit eigener Abnahme –
hier steht stattdessen die Wache, die den Effekt sichtbar und heilbar macht.
Empfehlung für den Folgeauftrag: `datum` aus dem Beitrags-Frontmatter durchreichen
und `generate_covers.py --selftest` um eine Byte-Idempotenz-Probe erweitern
(zweimal rendern → gleicher Hash). Bis dahin gilt: nach jedem Render `--heilen`.

**Heilung als Regel im Prüfer** (`scripts/ki_cover_herkunft.py`, Klasse
`beleg_veraltet`):

- `messung()` prüft **nach** grüner Pixelmessung `belegt.strip().lower() != _sha256(ziel)`
  und meldet im Klartext: „Beleg nennt sha256 X…, die Datei trägt Y… – die
  Herkunftserklärung beschreibt nicht diese Bytes";
- `heilen()` zieht **beide** Klassen nach und zählt sie getrennt
  (`{geschrieben, erneuert, fehler, hart, geprueft, ausserhalb, trocken}`);
- eine echte **Pixelabweichung bleibt hart** (fail-closed) – die neue Klasse
  entschärft nichts, sie macht nur sichtbar, was vorher unsichtbar war;
- Selbsttest um die Proben **2b/3b** erweitert, Doku-Punkt 3 nachgezogen;
- fremde KI-Belege (`trainedAlgorithmicMedia`/composite) werden weiterhin **nie**
  überschrieben.

```
✅ ki_cover_herkunft.py --selftest → Exit 0
🔧 ki_cover_herkunft.py --heilen   → 13 Beleg(e) nachgezogen (davon 13 auf die Bytes der Datei erneuert)
                                     144 gemessen · 0 hart · 0 Schreibfehler
✅ ki_cover_herkunft.py --pruefen  → 144 Cover reproduziert, 2 außerhalb, 0 Befund(e)
✅ Kontrolle Kfz-Artikel: cover.ki_pruefung.sha256 = 03fe7bb2bb98… = sha256sum der jpg,
                          geprueft_am: 2026-11-22
✅ check_covers.py → 144 Covers | Probleme: 0 | Stale: 0 | Brand: 0 | Text: 0
✅ abgeleitete_register.py --fix → Fachprüfungs-Register (21 Beiträge), static/llms.txt,
                                   BEFUND-AKTE.md · --check → Exit 0
```

---

## 5. Heilung D – Titel-Gate R1: der Fixer versprach Heilung und lief ins Leere

**Befund am liegenden Stand** (identisch auf `main`): `check_titles.py` →
`144 Titel | Verstöße: 1`, **Exit 1**.

```
❌ [R1] 2026-11-12-wie-viel-streaming-bandbreite-du-wirklich-brauchst-dein:
   Titel 47 Zeichen ohne Doppelpunkt (Konvention „Hauptkeyword: Untertitel",
   Cover-Umbruch bricht sonst semantisch kaputt)
```

**Warum es niemand sah:** `deploy.yml:559` ruft `check_titles.py --fix` auf – mit
`|| echo "⚠ Titel-Gate – Funde im Log"`. Der Schritt bleibt grün, der Befund bleibt
liegen. Und `--fix` heilt R1 hier **nicht**, obwohl die Doku es verspricht
(`check_titles.py:377`: „R1 … wird über `pinterest_seo_healer.ensure_colon_title`
geheilt"):

```python
# ensure_colon_title(), Zweig „X? Y" → „Y: X?"
if "?" in t:
    head, tail = t.split("?", 1)   # tail ist LEER – das Fragezeichen steht am Ende
    ...
    if len(head) >= 12:
        return f"{head}?"          # ← gibt den Titel UNVERÄNDERT zurück
```

Ein reiner Fragetitel ohne Anhang hat kein „Y", das zum Kopf werden könnte: Die
Funktion gibt ihn unverändert zurück, `fix_title()` übernimmt das unverändert,
`check_title()` meldet R1 weiter – Runde für Runde, ohne dass etwas passiert.
Messbar gemacht statt behauptet:

```
fix_title('Wie viel Bandbreite brauchst du fürs Streaming?')
  → 'Wie viel Bandbreite brauchst du fürs Streaming?'   (47 Zeichen, kein Doppelpunkt)
```

**Heilung – redaktionell, nicht mechanisch.** Der Regex-Rückfall in `fix_title()`
hätte `„Wie viel Bandbreite: Brauchst du fürs Streaming?"` erzeugt: grammatisch
kaputt, keyword-schwach, und auf dem Cover umgebrochen schlechter als vorher. Der
Artikel trägt seine eigene Vorgabe bereits im Frontmatter
(`inspiration: "Streaming-Qualität: Wie viel Bandbreite du wirklich brauchst"`)
und in der ersten H2 (`„Wie viel Streaming‑Bandbreite brauchst du wirklich?"`):

```
vorher (47, ohne Doppelpunkt): Wie viel Bandbreite brauchst du fürs Streaming?
nachher (52, Hauskonvention):  Streaming-Bandbreite: Wie viel brauchst du wirklich?
```

Grenzen vor dem Schreiben geprüft: `TITLE_MIN/MAX = 30, 60`
(`pinterest_seo_healer.py:53`), M1 ≤ 60, R2 verlangt genau dieses
Bindestrich-Kompositum (`Streaming-Bandbreite`, nicht `Streaming Bandbreite`),
keine Titel-Kollision im Bestand, Hauptkeyword = `keywords[0]`.

**Governance:** Der Artikel ist **unversiegelt** –
`redaktionelle_pruefung.status: "ausstehend"`, `risikoklasse: "standard"`,
`engine_level: "draft"`, `automatic_write_protected()` → `False`. Es gab also keine
Freigabe zu brechen (anders als bei Heilung A); `--fix` hätte hier schreiben
dürfen, konnte aber nicht. Bewusst **nicht** angefasst:

- `pin_title` – eigenes Pinterest-Feld mit eigener Regel (H6: vorhanden und ≤ 100
  Zeichen; 47 passen). Es weicht in 37 von 138 Artikeln vom `title` ab – es ist
  keine Kopie, sondern Kanalkopie.
- `keywords` – die Frage ist ein realer Long-Tail-Suchbegriff und bleibt stehen.
- `description` – unverändert innerhalb 155 Zeichen / 985 px (`serp_limits.py`).

`cover.alt` wurde mitgezogen, weil das Cover den Titel rendert und der Alt-Text
das Bild beschreiben muss.

**Kette (dieselbe Bauart wie Heilung A):** Titel → `generate_covers.py --slug …`
(15 Bilddateien, `covers_manifest.json`, LCP-/FCP-Manifeste) →
`ki_cover_herkunft.py --heilen` → `abgeleitete_register.py --fix`
(`static/llms.txt`, Fachprüfungs-Register, Befund-Akte).

Dabei greift die neue Klasse aus Abschnitt 4 zum **ersten Mal im Ernstfall**:

```
🔧 Cover-Herkunft: 1 Beleg(e) nachgezogen (davon 1 auf die Bytes der Datei erneuert)
   – die Pixelmessung war für genau diese Cover bereits grün.
   144 Cover gemessen · 0 harte Befunde · 0 Schreibfehler
```

Ohne `beleg_veraltet` wäre genau hier wieder eine Herkunftserklärung auf der
Vorfassung stehen geblieben – dieselbe stille Drift, nur eine Datei kleiner.

```
vorher:  ❌ Titel-Check: 144 Titel | Verstöße: 1   (Exit 1)
nachher: ✅ Titel-Check: 144 Titel | Verstöße: 0   (Exit 0)
         ✅ Cover-Check: 144 Covers | Probleme: 0 | Stale: 0 | Brand: 0 | Text: 0
         ✅ Metadaten-Wache: 145 Dateien | Befunde: 0
         ✅ Frontmatter-Wache: 174 | Blocker: 0 | Hinweise: 0
         ✅ YMYL-Siegelwache: 138 Artikel · 0 Befunde
         ✅ editorial_review_gate --published --strict: 0 blockiert
```

**Was offen bleibt (Ehrlichkeit statt Grünmalerei):** Geheilt ist der Einzelfall,
nicht der Fixer. Ein nächster Fragetitel über 45 Zeichen ohne Anhang läuft wieder
ins Leere. Die dauerhafte Lösung ändert `ensure_colon_title()` für den gesamten
Bestand und braucht deshalb Idempotenz-Nachweis plus Sabotage-Selbsttest
(Hausart: `run_selftest()` in `check_titles.py:509` prüft bereits, dass die
R1-Heilung keine Artefakte erzeugt) – eigener Auftrag. Inhaltlich müsste der Kopf
dann aus `keywords[0]` oder der `inspiration`-Zeile kommen, nicht aus dem Titel
selbst, denn ein Fragetitel ohne Anhang trägt kein „Y" in sich.

---

## 6. Heilung E – vier stale Cover und die Reihenfolge im Deploy

**Befund, erst in der Endabnahme sichtbar geworden:** `check_covers.py` →
`144 Covers | Probleme: 0 | Stale: 4`, **Exit 1** – am liegenden Stand und
**bitgleich auf `origin/main`** (Nachweis im `git worktree` von `origin/main`,
dieselben vier Zeilen):

```
❌ STALE 2026-10-14-heizperiode…:  Cover zeigt 'Gasrechnung senken: Heizperiode vorbereiten im Spätsommer',
                                   Frontmatter 'Heizperiode vorbereiten im Spätsommer'
❌ STALE 2026-10-26-gastarife…:    Cover zeigt 'Gasvergleich: Kosten, Fristen und Verbrauch prüfen',
                                   Frontmatter 'Gastarife vergleichen: Kosten, Fristen und Verbrauch prüfen'
❌ STALE 2026-10-28-dsl…:          Cover zeigt 'DSL Vergleich: Was kostet der Anschluss',
                                   Frontmatter 'Internet-Flats vergleichen: Was kostet der Anschluss'
❌ STALE 2026-11-06-guenstige-fluege…: Cover zeigt 'Flugtickets günstig: Günstige Flüge für den Spätsommer',
                                   Frontmatter 'Günstige Flüge für den Spätsommer finden'
```

Das ist kein Schönheitsfehler: Auf dem Cover steht ein **anderer Titel** als auf
der Seite, die es bewirbt – sichtbar in Suchmaschine, Social-Kanal und LCP-Bild.

**Ursache ist eine Reihenfolge, nicht ein Renderer.** `deploy.yml` heilt in dieser
Order:

| Zeile | Schritt | Wirkung auf den Titel |
| --- | --- | --- |
| 556 | `cadence_guard.py --fix` | kann Titel fassen |
| 559 | `check_titles.py --fix` | kann Titel fassen (R2–R4) |
| **562** | **`check_covers.py --fix`** | **rendert Cover aus dem Titel von jetzt** |
| 567 | `keyword_optimizer.py --fix` | **schreibt Titel danach um** |
| 569 | `keyword_gate.py --fix` | **schreibt Titel danach um** |
| 610 | `metadaten_wache.py --fix` | schreibt Description/Zeitstempel danach |

Wer nach Zeile 562 einen Titel ändert, lässt das Cover altern – und im selben Lauf
rendert nichts mehr nach. Die vier Befunde tragen genau die Handschrift der
Keyword-Schreiber (Cover = keyword-optimierte Fassung, Frontmatter = spätere,
gekürzte Fassung). Ein Deckungsgleichheits-Test fehlt: Kein Prüfer vergleicht
„Titel-Schreiber" mit „Cover-Renderer" auf Reihenfolge.

**Heilung:** `check_covers.py --fix` (haus-sanktioniert, idempotent) →
4 Cover neu gerendert, danach `ki_cover_herkunft.py --heilen` → **4 Belege auf die
Bytes der Datei erneuert** (ohne die Klasse aus Abschnitt 4 wären hier vier neue
stille Driften entstanden), danach `abgeleitete_register.py --fix`.

Gegenprobe auf einer Kopie des Bestands (`/tmp`, nicht im Arbeitsbaum): `--fix`
heilt die vier Befunde **stabil** – Nachmessung `Stale: 0`, also kein
Heilungs-Kreislauf, sondern einmalige Altlast.

```
vorher:  ❌ Cover-Check: 144 Covers | Stale: 4   (Exit 1)
nachher: ✅ Cover-Check: 144 Covers | Probleme: 0 | Stale: 0 | Brand: 0 | Text: 0
         ✅ ki_cover_herkunft --healen: 144 gemessen · 4 erneuert · 0 hart · 0 Schreibfehler
         ✅ Metadaten-Wache 145 | 0 · Frontmatter 174 | 0 | 0 · YMYL 138 | 0
         ✅ abgeleitete_register --check: aktuell (3 geprüft)
```

**Nachweis am lebenden Bestand – dieselbe Drift, eine Stunde später, von `main`
selbst erzeugt.** Während dieses Auftrags lief auf `main` die Automatik
`9630dea fix(gate): Kadenz-/Titel-/Cover-Heilungen vor Veröffentlichung`: Sie
renderte genau diese vier Cover neu (der Bestand heilt also dieselbe Altlast),
**zog aber die Herkunftserklärungen nicht nach**. Gemessen gegen
`origin/main` (`628da3a`), Beleg aus dem Frontmatter kontra `sha256sum` der Datei:

```
2026-10-14-heizperiode…       ❌ DRIFT  Beleg d3b680d4c355c298…  ≠ Datei 48d123c31320ee52…
2026-10-26-gastarife…         ❌ DRIFT  Beleg aa541ca37624840b…  ≠ Datei 8490720471255c4b…
2026-10-28-dsl…               ❌ DRIFT  Beleg 1f8d2a2399961e32…  ≠ Datei 04fd4783ebca6833…
2026-11-06-guenstige-fluege…  ❌ DRIFT  Beleg 9d9c7ebd9010b412…  ≠ Datei 8ac2238f73764a10…
```

Vier neue stille Driften, erzeugt von einem **grünen** Lauf – und kein Prüfer im
Bestand hätte sie gemeldet, weil `--pruefen` vor dieser Änderung nur Pixel maß.
Genau dafür existiert die Klasse `beleg_veraltet` aus Abschnitt 4: Sie macht den
Effekt sichtbar, und `--heilen` zieht ihn in einem Zug nach (hier: 4 Belege
erneuert). Nach dem Rebase auf `628da3a` sind die Cover-Bytes die des Bestands und
die Belege darauf erneuert – kein eigener Render steht mehr gegen `main`.

**Offen (Folgeauftrag, bewusst nicht hier):** Die **Reihenfolge** in `deploy.yml`
ist nicht umgestellt. Ein `--fix`-Lauf heilt den Stand, aber derselbe Mechanismus
kann beim nächsten Keyword-Eingriff wieder vier Cover altern lassen. Dauerhaft wäre
entweder (a) das Cover-Gate **hinter** alle Titel-Schreiber zu ziehen, oder (b) in
`keyword_optimizer.py`/`keyword_gate.py` nach einer Titeländerung das Cover
nachzurendern – plus (c) einen Reihenfolge-Vertrag in `governance_contract.py`,
damit niemand die Order unbemerkt wieder umstellt. (a) ist die kleinste Änderung,
berührt aber den Deploy-Ablauf selbst und gehört deshalb in einen eigenen PR mit
eigenem Nachweis.

---

## 7. Was bereits geheilt war – und warum das hier steht

Ehrliche Bestandsaufnahme, damit niemand dieselbe Arbeit doppelt macht:

- **Entity-Marken-Gate / Integritäts-Siegel / Gate:** Der Hugo-Duplikat-Befund
  (`mapping key "aenderungsgrund" already defined`, Commit `84f3bfcc`) war bei
  `5e8233e` bereits aus dem Bestand verschwunden. Nachgemessen: Hugo-Bau grün
  (131 Seiten, 426 HTML-Dateien), `entity_marken_gate --source-only` **und**
  `--public public` grün, `integrity_guard --gate` grün (66 Tests OK),
  `governance_contract --quick` grün (47 Regeln).
- **W1 in `code-selbstheilung.yml`:** Während dieser Arbeit hat `main` dieselbe
  Heilung eigenständig eingespielt (`f405f49`, 11:00). Die eigene Fassung wurde
  deshalb **zurückgenommen** – zwei Kommentare für dieselbe Zeile wären ein
  Rebase-Konflikt ohne Nutzen. Der substancegleiche Eintrag steht; die
  Dauerheilung (Backstop + Notbremse, Abschnitt 3) ist der Teil, den `main`
  *nicht* hat.

**Nicht entschärft wurde nichts.** Keine Wache wurde abgeschaltet, kein `|| true`
eingebaut, keine Grenze verschoben, kein Siegel ohne Freigabeweg neu gesetzt.
Das wäre in diesem Haus auch gar nicht möglich, ohne dass
`automatic_change_findings()` bzw. `governance_contract.py` es melden.

---

## 8. Heilung G – vier rote Bestandstests: „kein Aufrufer" war eine falsche Folgerung

> ### ⚠ Vom Bestand überstimmt – PR #1318, gemeldet am 22.11.2026 gegen 16:20 UTC
>
> Während dieser Abschnitt geschrieben wurde, hat `main` **dieselben vier Befunde
> selbst geheilt**: `bc1e022` „Betriebsbereit 22.11.: Deploy-Siegel grün (via
> #1315) + **4 von 5 roten Regressionstests geheilt** (#1318)", dazu `5c5ee46`
> „fix(titel): Streaming-Bandbreite-Titel auf R1-Konvention (Doppelpunkt)
> (**#1320**)" für Heilung E.
>
> **Die Diagnose war deckungsgleich, nicht nur das Ergebnis.** `main`'s Fassung
> von `_field()` trägt denselben Befundkopf – „BEFUND 22.11.2026", derselbe
> Auslöser `pillar: versicherungen` ohne Anführungszeichen, dieselbe Folge
> („die Siegel-Ausnahme in `_has_template_links` fiel STILL aus"), derselbe
> Verweis auf `weiterrechnen_box.html`, dieselbe Schlussfolgerung („Ein Parser,
> der eine gültige Schreibweise nicht kennt, erfindet einen Befund"). Zwei
> unabhängige Läufe sind zur selben Ursache vorgedrungen. Die Umsetzungen
> unterscheiden sich: `main` nutzt **einen** Regex `^key:[ \t]*(.*)$` und
> schält die Quote danach manuell ab, dieser Branch nutzte drei Muster
> (doppelt/einfach/nackt) mit `(?:#.*)?$` für Inline-Kommentare.
>
> **Hauspolitik „Bestand gewinnt"** (`GIT_SYNC_BESTAND_POLICY`, #590) → `main`'s
> Fassung steht im Baum, alle fünf Inhaltsheilungen aus 8.1/8.3/8.4/8.5 und der
> eigene `_field()`-Entwurf sind zurückgenommen. Beim `handytarif`-Artikel war
> das keine Formalie: `main` hatte denselben Pillar-Link
> `../../pillar/internet-dsl/` bereits gesetzt, die eigene Fassung hätte ihn
> **zweimal** getragen (gemessen: 2 Treffer gegen 1 im Bestand).
>
> **Was von Heilung G bleibt**, und es ist nicht nichts:
> 1. **Lehre 4** (Abschnitt 1) – „kein `run:` mit diesem Namen" heißt nicht
>    „läuft nie". Ohne sie wäre `regression` weiter als „außerhalb des Auftrags"
>    geführt worden. #1318 bestätigt sie: Der Job war repo-weit rot, und geheilt
>    wurde er über die Suite, nicht über ein benanntes Gate.
> 2. **Abschnitt 8.6** – die Lesbarkeits-Diff-Wache, die einen gesetzten Link
>    als Text misst. Fünf Varianten, eine Tabelle, die Regel „ein Link ist Text".
> 3. **Abschnitt 8.7** – die Reihenfolge der Ableitungskette. Sie hat in diesem
>    Auftrag zweimal zugeschlagen und ist unabhängig davon gültig, wer die
>    Befunde heilt.
> 4. **Abschnitt 8.2** – der Schreibschutz-Fehlbefund über `except: return True`
>    auf einem umbenannten Pfad. Nicht geheilt, weiterhin offen (Abschnitt 9).
> 5. **Ein neuer, harter Nachweis für Heilung D** – siehe 8.9. `main` hat mit
>    `ae6fd3c`/`200a9e3` **14 frische Beleg-Driften** erzeugt, die `main`'s
>    eigener Prüfer mit **0 Befunden** durchwinkt.
> 6. **Neu und nicht überstimmt: die Sicherung von `main`'s eigenem Fix.**
>    `main`'s `_field()` ist richtig – gemessen gegen 10 Proben, alle grün,
>    darunter nackt/einfach/doppelt quotiert, Doppelpunkt im Wert, fehlendes
>    Feld, leeres Feld und Inline-Kommentar. Aber `main`'s `selftest()` prüft
>    **ausschließlich FF1**; für den Parser stand keine einzige Probe. Ein Fix
>    ohne Probe altert unbemerkt – dieselbe Klasse wie Lehre 3 („Ein Gate, das
>    nie wieder misst, ist ein stilles Gate"), nur eine Ebene tiefer: hier misst
>    der Selbsttest einer Wache seinen frisch reparierten Leser nicht.
>    Deshalb sind **9 Feld-Proben und 2 Vertrags-Proben** ergänzt, rein additiv,
>    ohne eine Zeile am Verhalten zu ändern: `selftest()` meldet jetzt
>    `18 Proben: FF1 + Feldleser + Siegel-Ausnahme scharf`.
>    **Sabotage-Gegenprobe geführt:** den Parser auf den Stand vor dem Fix
>    zurückgedreht (`^{key}: "(.*)"$`) → **6 Proben rot, Exit 2**, darunter
>    wörtlich „Fassungsgebundener Beitrag mit nacktem pillar-Feld verliert die
>    Template-Ausnahme – genau der Fehlbefund vom 22.11.2026". Zurückgesetzt →
>    grün. Die Proben sind in beide Richtungen scharf, denn ein fehlendes oder
>    leeres Feld **muss** leer bleiben: Sonst erfindet die Wache ein
>    `pillar`-Feld und gibt die Siegel-Ausnahme einem Beitrag, dessen Boxen
>    nichts zu verlinken hätten.
> 7. **Die Wurzel hinter dem Modellwert-Artefakt – der eine Befund, den #1318
>    nicht erreichte.** Abschnitt 8.5 zählte **192** verbliebene Stempel als
>    offenen Punkt, mit dem eigenen Auftrag, den **Injektor** zu finden statt 192
>    Symbole zu putzen. Er ist gefunden und geheilt: `scripts/sprachkern.py`,
>    `_marker_reparatur`. Der Ausdruck `_ZAHLBEHAUPTUNG` verknüpfte „Zahl mit
>    Einheit" (immer eine Behauptung) und „nackte Zahl ab drei Ziffern" (nur
>    manchmal eine) mit ODER – und der nackte Zweig fraß die `2016` der
>    Fundstelle `(Verordnung (EU) 2016/679)`. Ergebnis live: „Die DSGVO … regelt
>    die Verarbeitung personenbezogener Daten**; das ist ein Modellwert.**" Eine
>    Rechtsnorm ist kein Modellwert, sie ist geltendes Recht – faktisch falsch, in
>    einem YMYL-Satz. #1318 korrigierte den **Satz** von Hand; die Stelle, die ihn
>    schrieb, blieb im Baum. **Reichweite gemessen: 44 Zeilen** False Positives im
>    Bestand (1 Fundstelle, 40 Paragraphenverweise, 3 Link-Pfade mit Datum) – und
>    aktuell **0** Stempel an Rechtsnorm-Sätzen, also sauber, aber **nicht
>    geheilt**: sauber nur, weil diese Zeilen gerade keinen zerstückelten Marker
>    tragen. Geheilt mit getrennten Ausdrücken plus `_ist_rechtskontext()`, der
>    den Kontext um den **einzelnen** Treffer prüft – ein satzweiter Guard wäre
>    eine Scheinheilung in die Gegenrichtung, denn „Nach § 5 kostet das 460 € im
>    Monat" muss seine Kennzeichnungspflicht behalten. Nachweis: 19 Proben in
>    beide Richtungen, End-to-End ergibt die Heilung **wörtlich die Korrektur, die
>    #1318 von Hand machte**, Sabotage-Gegenprobe (Guard aus → 5 Proben rot, Exit
>    2, Original-Satz wörtlich reproduziert), `Ran 26 tests OK` statt 18,
>    `selftest_runner` **292** Wachen statt 291, und
>    `pflicht_marker_reparatur.py` meldet **„0 Reparatur(en) in 0 Datei(en)"** –
>    die Heilung schreibt den Bestand nicht um. Vollständig in **Abschnitt 8.10**.


Dieser Abschnitt stand in der ersten Fassung dieser Akte als **Nebenbefund** mit
der Empfehlung, ihn in einem Folge-PR zu heilen. Die Begründung war: Alle vier
Module hätten **null** Aufrufe in `.github/workflows/` und `package.json`, und
„wer kein `run:` in einem Workflow hat, läuft nie".

**Diese Folgerung war falsch, und die Korrektur ist der wichtigste Befund dieses
Abschnitts.** Sie galt nur für *namentliche* Aufrufe. Der Job `regression`
(`.github/workflows/publication-reliability-tests.yml`, Schritt 11 „Code-Regression
– Suite und Selbsttests") fährt:

```
python3 scripts/ci_tests.py --titel "Code-Regression" \
  --log /tmp/suite.log -- python3 -m unittest discover -s scripts/tests -v
```

`discover` erreicht **jedes** Modul in `scripts/tests/` – auch die vier, die kein
Workflow beim Namen nennt. Sie laufen also in CI, und sie machen `regression`
rot: auf **jedem** PR der letzten Stunden, nicht nur auf diesem. Belegt über die
Check-Runs-API dreier fremder Läufe (`45025681311`, `45015486469`, `45015442046`),
die exakt dieselben Testnamen als Annotation tragen:

```
test_kein_kritisches_live_paar_im_bestand
test_gas_artikel_flesch_ueber_publish_schwelle
test_reisekasse_praezisierungen_und_recherche_bleiben_erhalten
```

Damit sind die vier Befunde **kein** Nebenbefund, sondern Teil des Auftrags: Ein
PR, der „die roten Merge-Gates dauerhaft heilt" und dabei `regression` rot lässt,
heilt das lauteste Tor gar nicht. Alle vier sind hier geheilt.

Die erste Fassung notierte außerdem, `discover` scheitere lokal am fehlenden
`__init__.py`. Auch das war ungenau: `scripts/tests/` ist ein Package, und die
Batch-Messung über explizite Modulnamen war ein Umweg, der den CI-Weg **nicht**
abbildete. Gemessen wird jetzt auf dem CI-Weg selbst.

### 8.1 FF3 – ein Parser-Bug, kein Inhaltsmangel

`test_inhalts_register.test_live_wache_ist_gruen` meldete FF3 („kein Rechner-Link")
gegen drei Live-Artikel. Einer der drei war ein **Fehlbefund**, verursacht durch
die Wache selbst:

`scripts/ff_inhalts_wache.py` las Frontmatter-Felder ausschließlich mit

```python
m = re.search(rf'^{key}: "(.*)"$', front, re.M)
```

– also nur `key: "wert"` in doppelten Anführungszeichen. Der Kfz-Artikel trägt
`pillar: versicherungen` **unquotiert**: gültiges YAML, für diese Funktion aber
unsichtbar. `_field()` lieferte `""`, `_has_template_links()` sah kein `pillar`-Feld
und verweigerte dem Beitrag die Ausnahme, obwohl `weiterrechnen_box.html` und
`pillar_box.html` vorhanden sind und den Rechner- und Pillar-Link im gerenderten
HTML liefern. **136 von 137** Beiträgen quoten ihr `pillar`-Feld; der eine
Ausreißer reichte, weil die Wache Ausreißer nicht lesen konnte.

Eine Wache, die gültige Werte nicht liest, ist doppelt falsch: Sie meldet Befunde,
die keine sind, **und** sie übersieht dieselben Felder dort, wo sie wirklich
fehlen. Geheilt: `_field()` liest jetzt doppelt quotiert, einfach quotiert und
unquotiert, jeweils mit optionalem Inline-Kommentar. Der Selbsttest ist um acht
Feld-Proben und zwei Vertrags-Proben erweitert – in **beide** Richtungen scharf,
denn ein leerer Wert muss leer bleiben, sonst erfindet die Wache ein `pillar`-Feld
und gibt die Ausnahme einem Beitrag, dessen Boxen nichts zu verlinken hätten.

Die verbleibenden zwei Befunde waren echt und sind redaktionell geheilt:

| Artikel | Fehlender Link | Gesetzter Link |
| --- | --- | --- |
| `2026-08-26-handytarif-vergleichen-2026-guenstige-tarife` | Pillar-Link | `[Ratgeber Internet & DSL](../../pillar/internet-dsl/)` am Schlussabsatz – Netzqualität, Anschluss und Gesamtkosten gehören zusammen |
| `2026-08-26-tagesgeld-zinsen-2026-die-besten-zinssaetze-im-vergleich` | Rechner- **und** Pillar-Link | `[Notgroschen-Rechner: Zielbetrag, Dauer und drei Stufen](../../werkzeuge/notgroschen-rechner/)` direkt hinter dem Notgroschen-Absatz; `[Ratgeber Konto & Karten](../../pillar/konto-karten/)` hinter der Checkliste zur Kontoeröffnung |

Linktext und Zielpfad sind **nicht** erfunden, sondern aus dem Bestand übernommen:
`[Ratgeber Konto & Karten]` steht dort sechsmal, `[Ratgeber Internet & DSL]`
siebenmal, `[Notgroschen-Rechner: Zielbetrag, Dauer und drei Stufen]` dreimal.
Vorher: `Inhalts-Wache FF1–FF5: 4 Befund(e)` (einer davon falsch). Nachher:
`0 Befund(e)`.

### 8.2 Der Schreibschutz-Fehlbefund – und warum er gefährlich ist

Bei der Siegel-Prüfung meldete `editorial_review_gate.automatic_write_protected()`
den Reisekasse-Artikel als 🔒 **versiegelt**. Er ist es nicht: `status: "ausstehend"`,
kein `inhalt_sha256`. Der Schutz kam aus einer anderen Zeile – die Funktion endet mit

```python
except Exception:
    return True
```

Gemessen wurde der Pfad `content/posts/2026-10-24-strategisch-sparen-…`, den
`test_faktenfrische_763.py:40` hartkodiert trägt. Die Kadenz-Wache hat den Artikel
längst auf `2026-10-25-…` umdatiert. `load_article()` warf `FileNotFoundError`,
die Klausel fing ihn und meldete „geschützt".

**Fail-closed ist hier richtig** – ein unlesbarer Artikel darf nicht beschreibbar
sein. Aber der Fehlbefund hatte eine konkrete Folge: Er hätte dazu geführt, einen
freien Artikel über den vollen Siegelweg zu jagen und ein Siegel zu prägen, wo
keines hingehört. Der Test selbst ist gegen die Umbenennung immun, denn er löst
über `resolve()` auf (exakter Treffer gewinnt, sonst eindeutiger Fund über den
Namens-Kern) – nur die **Messung** daneben war es nicht. Geheilt ist hier deshalb
die Messung, nicht der Code: Die Siegel-Lage wird über den aufgelösten Pfad
ermittelt. Die `except`-Klausel bleibt stehen.

### 8.3 Flesch 59.9 – die längsten Sätze, nicht die kürzesten Wörter

`test_einzigartigkeit_1027.test_gas_artikel_flesch_ueber_publish_schwelle` fordert
für `GAS_12` und `GAS_24` `flesch ≥ 60.0` **und** `score ≥ 75`. `GAS_12`
(`2026-08-12-preisgarantie-gas…`) lag bei **59.9** – ein Zehntel unter der Schwelle.

`score` war 75 = 100 − 20 (Flesch unter `SCORE_MIN`) − 5 (zwei Absätze über
`ABSATZ_MAX_SENT`). Der 20er-Abzug ist also **derselbe** Hebel: Steigt Flesch über
die Schwelle, fällt er weg und der Score springt auf 95.

Gemessen: 1503 Wörter, 140 Sätze, `wps` 10.74, `spw` 1.870. Amstad-Deutsch ist
`flesch = 180 − wps − 58.5·spw`; `spw` zu drücken hieße, kürzere Wörter zu suchen –
Scheinheilung. Der ehrliche Hebel ist `wps`, und dort die Ausreißer. Die drei
längsten Sätze (31, 26, 26 Wörter) sind geteilt:

- **31 Wörter** → drei Sätze: BDEW-Mittelwerte je Hausart einzeln ausgewiesen
  (12,23 Cent/kWh Einfamilienhaus, 11,67 Cent/kWh Mehrfamilienhaus). Alle Zahlen
  und die Quelle bleiben stehen.
- **26 Wörter** → drei Sätze: Eurocent-/kWh-Verwechslung, grobe Schätzung und der
  Beispielwert getrennt. Der Hinweis auf den Beispielwert bleibt erhalten.
- **26 Wörter** → fünf Sätze: Die vier Prüfpunkte eines Preisschreibens sind jetzt
  vier Fragen statt einer Komma-Kette. Der `Kündigungsfrist`-Link bleibt im vierten.

Vorher: Flesch **59.9**, Score **75**, `nested_pct` 2.1. Nachher: Flesch **60.60**,
Score **95**, `nested_pct` **0.0**. `wps` 10.20. Kein Inhalt entfernt, keine Zahl
geändert, kein Link verloren.

### 8.4 Kritische Live-Überlappung – fünf Phrasen aus **einem** Satz

`test_einzigartigkeit_bestand.test_kein_kritisches_live_paar_im_bestand` maß
`sparen-im-herbst` ↔ `kfz-versicherung-vergleich` mit **5** gemeinsamen
7-Wort-Phrasen (`PHRASE_LEN=7`, `KRITISCH_AB=5`, `paar_klasse(n, False, False)`).

Die fünf Phrasen sind kein Zufallstreffer über zwei Artikel, sondern ein
**gleitendes Fenster über eine einzige Dopplung**:

```
bis zum 30 november beim versicherer eingehen
die ordentliche kuendigung bis zum 30 november
kuendigung bis zum 30 november beim versicherer
muss die ordentliche kuendigung bis zum 30
ordentliche kuendigung bis zum 30 november beim
```

Beide Artikel trugen wortgleich:

> Bei einem Vertragsende am 31. Dezember und einem Monat Kündigungsfrist muss die
> ordentliche Kündigung bis zum 30. November beim Versicherer eingehen.

Ein 16-Wort-Satz erzeugt bei Fenster 7 genau zehn Überlappungen; dass fünf davon
im jeweils anderen Artikel landen, ist die Messung, kein Befund an fünf Stellen.
Geheilt am **unversiegelten** Artikel (`sparen-im-herbst`), der versiegelte
Kfz-Beitrag bleibt unangetastet – derselbe Regelgehalt, eigenständig formuliert:

> Läuft dein Vertrag am 31. Dezember aus und gilt eine Frist von einem Monat, muss
> dein Schreiben spätestens am 30. November beim Versicherer vorliegen.

Vorher: **5** geteilte Phrasen. Nachher: **0**. Kein Test hält den Wortlaut fest
(geprüft über `scripts/tests/` und `e2e/`), und die drei anderen Erwähnungen des
Stichtags im selben Artikel (Kurzantwort, Aufzählung, FAQ) bleiben unverändert –
die Dopplung saß nur in diesem einen Satz.

### 8.5 Der fehlende Rechtssatz – ein Heiler-Artefakt in 72 Artikeln

`test_faktenfrische_763.test_reisekasse_praezisierungen_und_recherche_bleiben_erhalten`
fordert im Abschnitt `### Sind Cashback‑Apps sicher für meine Daten?` den Satz
`Das lässt sich nicht pauschal zusagen.` **exakt einmal**, dazu `DSGVO` und
`unter bestimmten Voraussetzungen`. Der Docstring des Tests nennt den Grund:
*„Die Lesbarkeitsreparatur darf keine rechtliche Pauschalaussage öffnen."*
Gemessen: **0** Vorkommen.

Die Fundstelle war nicht ein verlorener Satz, sondern ein ersetzter. Im Abschnitt
stand:

> Die DSGVO (Verordnung (EU) 2016/679) regelt die Verarbeitung personenbezogener
> Daten**; das ist ein Modellwert.** Du kannst Auskunft verlangen und Daten unter
> bestimmten Voraussetzungen berichtigen oder löschen lassen. …

`; das ist ein Modellwert.` ist ein mechanisch angehängter Stempel. Er steht
**193-mal in 72 Artikeln** – an Modellrechnungen ist er richtig, hier ist er
falsch: Die DSGVO ist eine Rechtsnorm, kein Modellwert. Der Stempel hatte den
Rechtssatz verdrängt, der die Frage des Abschnitts überhaupt erst beantwortet.

Der Originalsatz ist **nicht** erfunden, sondern aus der Historie geborgen:
`gh api …/contents/<pfad>?ref=77f9bef9` (25.10.2026, „fix(reserve): Dauerheilung
WF-D4E0 (#821) – RS5-Präzision") liefert den Abschnitt als

> Das lässt sich nicht pauschal zusagen. Sieh dir Anbieter, Berechtigungen und
> Datenschutzhinweise an. Frag auch: Wie lösche ich mein Konto und meine Daten?
> Rechtliche Pflichten ersetzen nicht deine eigene Entscheidung über die Zustimmung.

Wiederhergestellt ist die Kombination aus geborgenem Rechtssatz und den späteren
DSGVO-Präzisierungen, die der Test ebenfalls verlangt:

> **Das lässt sich nicht pauschal zusagen.** Die DSGVO (Verordnung (EU) 2016/679)
> regelt die Verarbeitung personenbezogener Daten. Du kannst Auskunft verlangen
> und Daten unter bestimmten Voraussetzungen berichtigen oder löschen lassen. …

Der Artikel war zum Messzeitpunkt auf `main` **selbst** zerstört – auch die Fassung
vom 20.11.2026 (`92e90965`) trägt das Artefakt. Der Befund lag also nicht an
diesem Branch. Geheilt: `21 tests … OK`.

Die übrigen 192 Artefakt-Vorkommen sind **bewusst nicht** angefasst (siehe
Abschnitt 9): Sie stehen an Modellrechnungen, wo der Stempel inhaltlich passt, und
ein Repo-weites `sed` über 72 Artikel wäre eine Massenänderung ohne redaktionelle
Prüfung jedes einzelnen Satzes – genau das, was die Siegel-Ordnung verhindern soll.

### 8.6 Das Diff-Gate, das `main` am selben Tag bekam – und das meine Heilung stoppte

Nach dem vierten Rebase auf `dba3f17` war ein Check rot, den es beim Start dieses
Auftrags **nicht gab**: `Geänderte Live-Artikel gegen Flesch-Boden`
(`.github/workflows/lesbarkeit-live-diff.yml`, Kopf-Doku „22.11.2026, Befund
#1247"). Er läuft auf `pull_request` mit `paths: content/posts/**` und fährt
`lesbarkeit_diff_wache.py --basis origin/$GITHUB_BASE_REF` – ein Diff-Tor, das
genau die Artikel misst, die der PR anfasst.

Der Befund war präzise und **zurecht**:

```
❌ 1 Live-Artikel würde unter dem Flesch-Boden 60 landen:
  - 2026-08-26-handytarif-vergleichen…: Flesch fällt von 53.8 auf 53.6
```

Der Artikel liegt seit langem **unter** dem Boden (53.8). Das Gate blockiert
Altbestand ausdrücklich nicht – „sonst würde jede Routinemeldung an alter Schuld
scheitern" – wohl aber eine **Verschlechterung**. Und genau die hatte Heilung G
verursacht: Der ergänzte Pillar-Link (8.1) war in einen Satz mit `Netzqualität`,
`Gesamtkosten` und `ordnet beide Seiten ein` verpackt. Zwei Zehntel unter dem
Altbestand, und der PR wäre rot geblieben.

**Das ist die Lehre in beide Richtungen.** Ein gesetzter interner Link ist noch
keine Heilung: Er ist Text, und Text wird gemessen. Wer einen Link ergänzt, um
eine Wache grün zu bekommen, und dabei die Lesbarkeit drückt, tauscht einen
Befund gegen einen anderen. Gemessen wurden fünf Formulierungen desselben Links
gegen denselben Anker – alle über dem Boden, die Spannweite 53.90 bis 54.20:

| Variante | Flesch | Puffer gegen 53.80 |
| --- | --- | --- |
| `Netzqualität, Anschluss und Gesamtkosten gehören zusammen – der […] ordnet beide Seiten ein.` | 53.60 | **−0.20 ❌** |
| `Kosten und Netz gehören zusammen. […] zeigt, warum.` | 53.90 | +0.10 |
| `Netz und Preis gehören zusammen. […] zeigt, warum.` | 53.90 | +0.10 |
| `Das Netz ist nicht alles. […] ordnet es ein.` | 54.10 | +0.30 |
| **`Zum Netz gehört mehr als der Preis. Das ordnet der […] ein.`** | **54.20** | **+0.40 ✅** |

Gewählt ist die Fassung mit dem größten Puffer **und** dem inhaltlich nächsten
Bezug: Der Artikel hat einen eigenen Abschnitt „Netz vor Preis prüfen" (Zeile 56),
der Satz führt ihn fort, statt ein neues Thema aufzumachen. Der Linktext bleibt
Hausart (`[Ratgeber Internet & DSL]`, siebenmal im Bestand). Nachher:
`✅ Keine neue Lesbarkeits-Regression unter Flesch 60` (Exit 0) und FF3
weiterhin `0 Befund(e)` – der Link steht ja noch.

**Abgrenzung, damit keine Verwechslung entsteht:** `readability_check.py --file`
meldet für denselben Artikel weiterhin `⚠️ 54.2 unter Ziel 62`. Das ist
**Altbestand** und kein PR-Gate: `readability_check` läuft ausschließlich in
Schedule-Workflows (`hemingway-check` Mo/Mi/Fr, `premium-governance` Montag,
`seo-weekly` Mittwoch, `sprach-qualitaet-pipeline` täglich, `endredaktion` Mo–Sa),
dort mit `--gate-bestand`. Auf `pull_request` läuft allein die Diff-Wache. Den
Artikel von 54.2 über 60 zu heben ist redaktionelle Arbeit an einem Live-Beitrag
und gehört nicht in einen Gate-PR – dasselbe Argument wie bei den 192
Modellwert-Stempeln in Abschnitt 9.

**Und ein Nachtrag in eigener Sache:** Dieses Gate ist der vierte Fall in diesem
Auftrag, in dem `main` während der Arbeit dieselbe Baustelle betrat – nach #1315
(Heilung A), `f405f49` (Heilung B) und `9630dea` (Heilung E/F). Hier kam es nicht
als Überstimmung, sondern als **neue Regel**, die den eigenen Entwurf prüfte. Wer
einen PR über Stunden fährt, muss die Check-Matrix nach jedem Rebase neu lesen,
statt sie vom Start zu kennen.

### 8.7 Reihenfolge – warum dieselbe Klasse zweimal zuschlug, und die Regel daraus

Die Projektkette aus 8.8 war **einmal** zu früh gelaufen, und das kostete einen
vollständigen CI-Durchlauf (`regression`: 56 Minuten, Schritt 11 und die Uhr-Probe
in Schritt 12 beide rot, Schritte 13–15 grün). Der Befund war exakt eine Zeile:

```
888c888
< - Datei-SHA256 (heute): `1f6a54c381989455f4b0882e194b69a67a471153bec215a1d97eebaa73db4b8a`
> - Datei-SHA256 (heute): `152f49578dff79c96084765f0439f25b713c2d92f6c4a343cfa436abf3161f85`
```

`sha256sum` über den Bestand bestätigte: `152f4957…` ist
`2026-08-26-handytarif-vergleichen-2026-guenstige-tarife/index.md` – genau der
Artikel, den die Lesbarkeits-Diff-Wache aus 8.6 **nach** dem Dossier-Lauf noch
einmal umformuliert hatte. Das Dossier trägt je Befund den Datei-SHA256 des
Artikels, weil es die „**heutige** Textlage" abbildet: stehen die beanstandeten
Werte noch im Artikel, und sind sie dort gekennzeichnet. Damit ist es keine
zählende, sondern eine **inhaltsensitive** Projektion – jeder Body-Eingriff an
einem Artikel mit offenen Befunden entwertet sie, auch wenn sich an der Zahl der
Befunde nichts ändert.

Es ist dieselbe Klasse wie in 8.6, nur eine Stufe feiner: Dort machte der
Akten-Nachzug das Dossier sichtbar veraltet (**Zählung** 304 → 306), hier machte
ein einziger umformulierter Satz es unsichtbar veraltet (**ein Hash**). Beides
ist derselbe Fehler: eine Ableitung wurde erzeugt, bevor die Quelle fertig war.

**Die Regel, die daraus folgt und die in diesem Auftrag zweimal verletzt wurde:**

> Ableitungen werden **zuletzt** erzeugt – nach *jedem* Eingriff in ihre Quelle,
> nicht nach dem ersten. Und „fertig" heißt: kein Satz wird danach noch
> umformuliert.

Konkret für dieses Repository, in dieser Reihenfolge und nicht anders:

```
1. alle redaktionellen Eingriffe (Titel, Body, Links, Sätze)     ← Quelle
2. generate_covers / check_covers --fix                          ← Pixel
3. ki_cover_herkunft --heilen && --pruefen                       ← Beleg
4. faktenfrische_befund_akte --schreiben                         ← Akte
5. abgeleitete_register --fix && --check                         ← Register
6. f4_entscheidungsvorlage && --check                            ← Dossier  ← ZULETZT
7. lesbarkeit_diff_wache --basis origin/<ziel>                   ← Diff-Tor
8. Suite auf dem CI-Weg                                          ← Beweis
```

Schritt 7 steht **nach** 6, weil die Diff-Wache ihrerseits Body-Änderungen
verlangen kann (8.6) – und jede solche Änderung wirft Schritt 6 zurück. Wer 6 und
7 vertauscht, bekommt genau den CI-Lauf, den dieser Auftrag bekommen hat. Der
Gegenbeweis ist billig und steht deshalb jetzt am Ende jeder Runde:
`f4_entscheidungsvorlage.py --check` und `abgeleitete_register.py --check` sind
beide Exit 0, und die Suite auf dem CI-Weg meldet **0 Annotationen**.

Ein ehrlicher Nachtrag zur eigenen Messdisziplin: Die Suite war vor dem vierten
Rebase einmal vollständig gelaufen (33 Minuten, 3 Annotationen). Nach dem Rebase
wurden nur die fünf Zielmodule einzeln gemessen – schnell, aber eben **nicht** die
Fläche. Der zweite Voll-Lauf am Stand `f4610fe` (36 Minuten) meldete genau
**eine** Annotation, dieselbe wie CI in Schritt 11 und 12. Der Befund war also
nicht neu auf der Basis `dba3f17`, sondern selbstgemacht. Nach einem Rebase gehört
die Vollfläche gemessen, nicht die Auswahl.

**Nachtrag 22.11.2026, spät – `main`'s #1324 bestätigt diese Diagnose wörtlich.**
`b3445bb` „F4-Vorlage bindet die Aussage statt der Datei-Bytes (Ende der
Byte-Alterung)" trägt im Commit-Text denselben Befund: „`test_dossier_ist_aktuell`
war im CI rot – in `Code-Regression` **UND** `Uhr-Probe` –, obwohl sich keine
einzige Aussage geändert hatte. Ursache: Die Vorlage trug je Artikel einen
SHA-256 über die ROHE Datei. **Der CI prüft den Merge-Stand (`refs/pull/N/merge`),
also Branch plus aktuelles `main`**; zwei redaktionell geänderte Artikel auf
`main` verschoben die Byte-Hashes und machten das Dossier ‚veraltet'."

Das ist genau die Mechanik, die hier dreimal gemessen wurde – einschließlich der
Feststellung, dass der CI den Merge-Stand prüft und nicht den Branch-Head. Die
Heilung ist strukturell und besser als jede Reihenfolge-Regel: Gebunden wird jetzt
an `ledger.text_hash()` in der Projektion `betrieb-v4` (Titel, Beschreibung,
Kurzantwort, Aussage-Body – ohne Quellen, Betriebsflächen und Zwischenraum);
`datei_hash()` entfällt. **Damit ist die Reihenfolge-Regel aus 8.7 für das Dossier
nicht mehr nötig**, weil Frontmatter-Betriebsflächen wie `cover.ki_pruefung` die
gebundene Aussage nicht mehr berühren. Messbar: Nach Rebase 8 ist
`F4-ENTSCHEIDUNGSVORLAGE.md` **bitgleich zu `main`** (2750 Zeilen) und fiel aus
dem Delta – der erste Rebase dieser Folge, nach dem das Dossier nicht neu
geschrieben werden musste, obwohl 13 Artikel Beleg-Zeilen tragen.

Die Regel bleibt für die **anderen** Ableitungen gültig (`BEFUND-AKTE.md`,
`abgeleitete_register`, Cover-Belege): #1324 hat das Dossier entkoppelt, nicht die
Kette.

### 8.8 Nachweis für Heilung G

Gemessen am liegenden Stand, `.venv/bin/python` (System-`python3` ist wertlos:
ohne PyYAML 21 F + 17 E):

| Prüfung | Vorher | Nachher |
| --- | --- | --- |
| `test_einzigartigkeit_1027` | ❌ `59.9 not >= 60.0` | ✅ `Ran 21 tests … OK` |
| `test_einzigartigkeit_bestand` | ❌ 5 gemeinsame Phrasen | ✅ `Ran 4 tests … OK` |
| `test_faktenfrische_763` | ❌ `0 != 1` (Rechtssatz) | ✅ `Ran 21 tests … OK` |
| `test_inhalts_register` | ❌ FF3 × 3 (eine falsch) | ✅ `OK` |
| `ff_inhalts_wache.py --selftest` | ✅ 7 Proben | ✅ 7 + 8 Feld- + 2 Vertrags-Proben |
| `ff_inhalts_wache.py` (Bestand) | ❌ 4 Befund(e) | ✅ `0 Befund(e)` |
| `readability_check` für `GAS_12` | Flesch 59.9 · Score 75 | **Flesch 60.60 · Score 95** |
| geteilte 7-Wort-Phrasen des Paares | 5 | **0** |
| `abgeleitete_register.py --check` | ❌ `BEFUND-AKTE.md` veraltet | ✅ `aktuell (3 geprüft)` |
| `f4_entscheidungsvorlage.py --check` | ❌ Dossier veraltet (2. Ableitungsebene) | ✅ `aktuell` · 2851 → 2877 Zeilen |
| `test_1098_produktionswahrheit` | ❌ 3 Annotationen (Dossier) | ✅ `Ran 22 tests … OK` |
| `ci_tests.py -- … discover -s scripts/tests -v` | ❌ 3 Annotationen, Exit 1 | ✅ Suite-Weg, siehe unten |
| `lesbarkeit_diff_wache --basis origin/main` | ❌ `handytarif` 53.8 → 53.6 (Diff-Gate neu auf `main`, 8.6) | ✅ `Keine neue Lesbarkeits-Regression` · 53.8 → **54.2** |
| `lesbarkeit_diff_wache --selbsttest` + `unittest test_lesbarkeit_diff_wache` | — | ✅ beide Exit 0 |
| `f4_entscheidungsvorlage.py --check` **nach** dem Lesbarkeits-Eingriff | ❌ veraltet durch **eine** Zeile (Datei-SHA256 des `handytarif`-Artikels, 8.7) | ✅ `aktuell` · 1 Zeile nachgezogen |
| Suite auf dem CI-Weg am Stand `f4610fe`, **vor** der Reihenfolge-Korrektur | ❌ 1 Annotation: `test_dossier_ist_aktuell` (CI Schritt 11 **und** Uhr-Probe Schritt 12, identisch) | — |
| Suite auf dem CI-Weg, **nach** der Reihenfolge-Korrektur (36 min) | — | ✅ **`SUITE_EXIT=0`, 0 Annotationen** (Gegenbeweis zu 8.7) |
| sechs Selbsttests aus Schritt 11 + `fm_boundary_guard --check` | — | ✅ alle 6 grün (174 Dateien) |
| Gate-Batterie am Endstand (34 Prüfungen) | — | ✅ `ERGEBNIS: alles grün` |
| **Suite nach der Wurzelheilung 8.10** (Stand `b5eb6f4`, 31 min) | — | ✅ **`Ran 6365 tests` → `OK (skipped=17)`**, `SUITE_EXIT=0`, **FAIL/ERROR-Zeilen: 0** |
| sieben Selbsttests aus Schritt 11, **inklusive dem neuen `sprachkern`** | — | ✅ `engine_generate`, `reserve_pool`, `cadence_guard`, `social_studio`, `fm_boundary --check`, `sprachkern` – alle grün |
| `selftest_runner` nach 8.10 | 291 Wachen | ✅ **292 Wachen**, 584 Uhr-Proben, 581 s – `sprachkern.py` trägt jetzt `--selftest` und wird entdeckt |
| **die 7 Test-Module, die `sprachkern` importieren** | — | ✅ **262 Tests, ROT=0** (`test_frontmatter_duplikate` 5, `test_grammatik_kongruenz` 32, `test_marker_ruinen_964` 26, `test_politur_heiler` 17, `test_prompt_echo` 17, `test_reserve_pipeline` 139, `test_sprach_politur` 26) |
| **CI-Fehlschlag Schritte 11+12 am Stand `6787112`** – Uhr-Probe | — | ❌→✅ **zwei Bestand-Befunde, beide von `main`/#1324 geheilt, Gegenprobe bitgleich:** `test_vollrueckstand_nach_97_tagen_behaelt_reserve` (`19 not less than 19`, 140 Seiten am 2027-02-22) und `test_echtes_repo_darf_heute_nichts_verlieren` (Janitor würde `wlan-verbessern…` löschen). Im Worktree von `origin/main` `954ee7c` **exakt dieselbe** AssertionError, dieselben 140 Seiten, `Ran 96 tests`, `FAILED (failures=1)` – also nicht dieser Branch. Nach Rebase 8: `LoeschRechtTests` `Ran 10 OK`, `test_faktenfrische_kapazitaet` unter +97 Tagen `Ran 96 OK`, Limit `19 → 21` |
| **CI-Fehlschlag Schritt 11 am Stand `b5eb6f4`** | lokal grün | ✅ **Ursache ist nicht der Code, sondern `main`**: 12 Commits liefen weiter (`c3ab0f2` Reserve, `9fbffaa` Akte, `fa3e8d0` #1323, `33dcbfe`+`e5bcd4a` Cover-Heilungen mit **44 neuen Cover-Bytes**). CI prüft den **Merge-Commit**, lokal lag die Basis `48cdd67`. Beweis: Rebase 7 → 14 Beleg-Driften, geheilt, Zielmodule danach `ROT=0`. |
| `check_covers.py` | — | ✅ `144 \| 0 \| 0 \| 0 \| 0` |

Keiner der fünf geänderten Artikel trägt ein Siegel (geprüft über
`grep inhalt_sha256`), der Siegelweg aus Abschnitt 2 war damit **nicht** fällig –
die erste Fassung dieses Abschnitts hatte ihn für alle vier Befunde vorausgesetzt,
weil sie von der 🔒-Fehlmessung aus 8.2 ausging.

`BEFUND-AKTE.md` war nach den Texteingriffen veraltet (304 → 306 Einträge,
`in_eskalation` 18 → 20). Geheilt auf dem dokumentierten Weg:
`faktenfrische_befund_akte.py --schreiben` + `abgeleitete_register.py --fix`.

**Und genau dabei passierte dasselbe noch einmal – eine Ableitungsebene tiefer.**
Der Suite-Lauf auf dem CI-Weg meldete **drei neue** Annotationen, alle aus
`test_1098_produktionswahrheit.Entscheidungsvorlage`:

```
test_dossier_ist_aktuell                     → F4-ENTSCHEIDUNGSVORLAGE.md ist veraltet
test_jeder_befund_hat_einen_schliessweg      → ['47f855cb…', '7f66ec82…'] != []
test_jeder_offene_live_befund_steht_im_dossier → dieselben zwei IDs
```

Die zwei IDs sind **dieselben** Befunde, die der Akten-Nachzug sichtbar gemacht
hatte – beide im `sparen-im-herbst`-Artikel, beide `alter_tage: 23`, also Bestand
und nicht Folge dieser Änderung. Die Kette: `main` trägt eine veraltete
`data/faktenfrische_befunde_state.json` (304 statt 306). Wer **eine** Ableitung
nachzieht, macht die nächste sichtbar. `F4-ENTSCHEIDUNGSVORLAGE.md` ist die
zweite – und ihre eigene Kopf-Doku beschreibt genau diesen Fall als ihren
Existenzgrund:

> In #1098 wurde genau dieses Dossier von Hand gebaut. Es war nach dem nächsten
> Automatik-Commit unvollständig (5 neue Befunde auf einem Artikel, den die
> Tageswache erst danach geprüft hatte) – ein Dossier, das der Wirklichkeit
> hinterherläuft, ist derselbe Fehler wie ein veraltetes Register.

Geheilt auf dem dokumentierten Weg: `f4_entscheidungsvorlage.py` (schreiben) →
2851 → **2877 Zeilen**, `--check` → aktuell, `Ran 22 tests … OK`. Das Dossier
schreibt in keinen Ledger und schließt keinen Befund – es projiziert nur, was zu
entscheiden ist. Die zwei Befunde bleiben **offen** und stehen jetzt dort, wo der
Herausgeber sie in einem Durchgang schließen kann; F4 ist laut
`data/release_scorecard.yaml` die einzige Prüfung mit `entscheidung: human`, die
keine Maschine schließen darf.

**Lehre daraus, und sie ist dieselbe wie Lehre 4:** Eine veraltete Ableitung ist
kein lokaler Fehler. Wer nur die Datei heilt, die ein Gate gerade anzeigt,
verschiebt den Befund eine Ebene weiter – hier von `BEFUND-AKTE.md` zum Dossier.
Der richtige Weg ist, die **Projektionskette** zu Ende zu fahren: State →
`faktenfrische_befund_akte.py` → `abgeleitete_register.py` → `f4_entscheidungsvorlage.py`,
und danach die Suite noch einmal auf dem CI-Weg zu messen statt nur das eine Gate.
`lastmod` war in allen fünf Artikeln auf `2026-11-22` gesetzt, weil
`test_metadaten_dauerhaft_korrekt` verlangt, dass `lastmod` den **tatsächlichen**
Texteingriff dokumentiert; `metadaten_wache` M3 (`lastmod ≥ date`) blieb grün.
Mit der Überstimmung durch #1318 sind diese fünf `lastmod`-Zeilen ebenso
zurückgenommen wie die Eingriffe selbst – der Bestand trägt jetzt seine eigene
Fassung und seine eigenen Stempel.

### 8.9 Vierzehn frische Beleg-Driften – und der Beweis, dass Heilung D nicht überstimmt ist

Der fünfte Rebase auf `ae6fd3c` brachte zwei weitere Automationsläufe mit
(`ae6fd3c`, `200a9e3`, beide „fix(gate): Kadenz-/Titel-/Cover-Heilungen vor
Veröffentlichung (automatisch)"). Danach maß `ki_cover_herkunft.py --heilen` im
eigenen Baum: **144 Cover gemessen, 0 Belege nachgezogen** – die Belege dieses
Branch passten zu den Bytes. Aber 14 Artikel wichen vom Bestand ab. Die Frage
war, wer hier falsch liegt.

Gegenprobe im `git worktree` von `origin/main` (`ae6fd3c`), zweimal gemessen,
einmal mit jedem Prüfer:

| Prüfer | Ergebnis am **selben** Bestand `ae6fd3c` | Exit |
| --- | --- | --- |
| `main`'s `ki_cover_herkunft.py` | `144 Cover reproduziert, 2 außerhalb, **0 Befund(e)**` | 0 |
| **dieser Branch** (`beleg_veraltet`) | `144 Cover reproduziert, 2 außerhalb, **14 Befund(e)**` | **1** |

Derselbe Baum, dieselben Bytes, dieselbe Pixelmessung – und zwei Antworten. Der
Unterschied ist genau die Klasse aus Abschnitt 4: `main`'s Prüfer vergleicht
**nur Pixel**, dieser Branch vergleicht zusätzlich den im Artikel hinterlegten
`sha256`-Beleg gegen die Datei (`belegt.strip().lower() != _sha256(ziel)`). Die
14 Belege nennen die Bytes einer Vorfassung, und weil die Pixel stimmen, läuft
der Befund in `main` **still** durch.

**Damit ist Heilung D der Teil von Abschnitt 8, den `main` nicht hat.** #1318 hat
die vier Inhaltstests geheilt; die Beleg-Drift-Klasse hat es nicht berührt, und
`ae6fd3c` hat im selben Zug 14 neue Driften erzeugt. Es ist das dritte Mal in
diesem Auftrag, dass ein **grüner** Automationslauf sie produziert: 13 Altlasten
zu Beginn, 4 nach `9630dea` (Abschnitt 6), jetzt 14 nach `ae6fd3c`/`200a9e3`.
Die Ursache ist jedes Mal dieselbe und weiterhin offen (Abschnitt 9): Der
Renderer ist nicht bytewert-deterministisch, und keiner der Cover-Heiler ruft
`--heilen` selbst auf.

Geheilt sind die 14 Belege in diesem Branch; sie sind der Grund, warum 14
Artikel-`index.md` im Delta stehen und sonst nichts an ihnen geändert ist
(je genau zwei Zeilen: `sha256`, `geprueft_am`). Nachweis am liegenden Stand:
`--heilen` → `0 Belege nachgezogen` (alle 14 sind es schon), `--pruefen` →
`0 Befund(e)`, `check_covers` → `144 | 0 | 0 | 0 | 0`.

**Auch das Dossier war auf `main` veraltet**, und wieder ist die Gegenprobe der
Beweis: `f4_entscheidungsvorlage.py --check` im reinen Bestands-Worktree →
Exit **1**. `main`'s `8ad6d41` „chore(faktenfrische): Akte, Stand und Queue
nachgezogen" hatte die Akte gezogen (sie ist grün: `301 offene Befunde,
Stichtag 2026-11-22`), das Dossier aber nicht. Geheilt auf dem dokumentierten
Weg: `2877 → 2803 Zeilen`, `--check` → aktuell, `test_1098_produktionswahrheit`
→ `OK`. Es ist dieselbe Regel wie in 8.7, nur dass diesmal `main` sie verletzt
hat: Ableitungen werden **alle** gezogen oder keine.

**Vierte Runde – `954ee7c`, und diesmal lief der Rebase konfliktfrei.** Nach
Rebase 7 (12 Commits auf `main`, darunter **zwei** Läufe „fix(gate):
Kadenz-/Titel-/Cover-Heilungen vor Veröffentlichung (automatisch)", `33dcbfe`
und `e5bcd4a`, die **44 Cover** neu schrieben) meldete dieselbe Gegenprobe:

| Prüfer am Bestand `bdb6939` | Ergebnis | Exit |
| --- | --- | --- |
| `main`'s `ki_cover_herkunft.py` (`beleg_veraltet`-Treffer: **0**) | `146 Cover reproduziert, 2 außerhalb, **0 Befund(e)**` | 0 |
| **dieser Branch** (`beleg_veraltet`-Treffer: **3**) | `146 Cover reproduziert, 2 außerhalb, **14 Befund(e)**` | **1** |

Wieder **14**, wieder von einem grünen Automationslauf erzeugt, wieder von
`main`'s eigenem Prüfer still durchgewinkt. Der Befundtext nennt die Bytes
beidseitig, zum Beispiel `2026-11-22-wlan-verbessern…: Beleg nennt sha256
791b75e1000a…, die Datei trägt fa262da5720c… – die Herkunftserklärung beschreibt
nicht diese Bytes (Pixelmessung grün: --heilen zieht den Beleg nach)`.

**Diesmal war der Rebase konfliktfrei – und genau das ist die Pointe.** Fünf
Dateien überlappten (`F4-ENTSCHEIDUNGSVORLAGE.md` und vier Artikel mit meinen
`cover.ki_pruefung`-Zeilen), aber Git konnte die **Textzeilen** sauber trennen.
Die **Bytes** unter den Belegen hatten sich trotzdem bewegt. Ein Rebase, der ohne
Konflikt durchläuft, ist also kein Nachweis, dass die Ableitungen noch stimmen –
nur die Messung danach ist einer. Ohne `beleg_veraltet` wäre dieser Stand mit
`0 Befund(e)` und Exit 0 durchgegangen und als Merge-Commit in `main` gelandet:
14 Herkunftserklärungen, die andere Bytes beschreiben als die, neben denen sie
stehen.

Geheilt auf dem dokumentierten Weg: `--heilen` → `14 Beleg(e) nachgezogen (14
erneuert), 0 harte(r) Befund(e)`, `--pruefen` → `146 reproduziert, **0
Befund(e)**`, `check_covers` → `146 | 0 | 0 | 0 | 0`, `check_titles` →
`146 | 0`, `abgeleitete_register --fix` + `--check` → `aktuell (3)`,
`f4_entscheidungsvorlage` **zuletzt** → `2803 Zeilen`, `--check` → aktuell,
`test_1098_produktionswahrheit` → `Ran 22 tests, OK`.

Die Zählung stieg von 144 auf **146**, weil `main`'s `c3ab0f2` „unabhängige
Redaktionsreserve auffüllen" zwei Artikel mit Cover brachte. Das Dossier fiel
dagegen aus dem Delta: `main` trägt inzwischen **bitgleich** dieselben 2803
Zeilen (`git diff --stat origin/main HEAD -- F4-ENTSCHEIDUNGSVORLAGE.md` → leer).

### 8.10 Die Wurzel hinter dem Modellwert-Artefakt – der eine Befund, den #1318 nicht erreichte

8.5 beschreibt das Artefakt und zählt **192** verbliebene Stempel als offenen
Punkt, mit dem eigenen Auftrag: „den **Injektor** finden und ihm beibringen,
Rechtsnormen von Modellwerten zu unterscheiden, statt 192 Symbole einzeln zu
putzen." Dieser Abschnitt löst ihn ein. Er ist **nicht** überstimmt, denn
#1318 hat den Satz geheilt, nicht die Stelle, die ihn schrieb.

**Der Injektor ist `scripts/sprachkern.py`, `_marker_reparatur`.** Der Satz stand
live im Reisekasse-Artikel, und `git show bc1e022` zeigt die Handkorrektur:

```
- Die DSGVO (Verordnung (EU) 2016/679) regelt die Verarbeitung personenbezogener
-   Daten; das ist ein Modellwert. Du kannst Auskunft verlangen …
+ Das lässt sich nicht pauschal zusagen. Die DSGVO (Verordnung (EU) 2016/679)
+   regelt die Verarbeitung personenbezogener Daten. Du kannst Auskunft verlangen …
```

**Eine Rechtsnorm ist kein Modellwert, sie ist geltendes Recht.** Der Stempel war
faktisch falsch, und zwar in einem YMYL-Satz über die DSGVO – die Klasse von Satz,
in der ein falsches Wort am teuersten ist.

**Die Ursache, bis auf den Ausdruck genau.** `_ZAHLBEHAUPTUNG` verknüpfte zwei
sehr unterschiedliche Fälle mit ODER:

```python
_ZAHLBEHAUPTUNG = re.compile(
    r"\d[\d.,]*\s*(?:€|EUR|Euro|%|Prozent|kWh|ct|Cent|Mbit/s|GB|MB|km|Watt|W)"   # 1
    r"|(?<![\w.,])\d{3,}(?:[.,]\d+)*(?![\w.])", re.I)                            # 2
```

Fall 1 – Zahl **mit** Einheit – ist immer eine Behauptung über die Welt. Fall 2 –
**nackte** Zahl ab drei Ziffern – ist es nur manchmal. Er matchte die `2016` der
Fundstellenangabe `(EU) 2016/679`, `_marker_reparatur` sah „der Satz trägt eine
Zahl" und hängte den Teilsatz an. Der Ausdruck war nie falsch *formuliert*; er
war zu grob *gemeint*.

**Reichweite gemessen, nicht geschätzt.** Der zweite Zweig liefert im Bestand
**44 Zeilen** False Positives:

| Klasse | Zeilen | Beispiel |
| --- | --- | --- |
| Fundstelle | 1 | `(EU) 2016/679` |
| Paragraphen-/Artikelverweis | 40 | `§ 5`, `§ 9`, `Art. 6` |
| Link-Pfad mit Datum | 3 | `](https://www.destatis.de/…/2026/10` |

Und die Kernfrage – hängt aktuell ein Stempel an einem Rechtsnorm-Satz? – ergibt
**0**. Der Bestand ist sauber, aber **nicht geheilt**: sauber nur, weil diese 44
Zeilen gerade keinen zerstückelten Marker tragen. Jede von ihnen hätte denselben
falschen Stempel bekommen. Das ist der Unterschied zwischen einem grünen Messwert
und einer Ursache, die nicht mehr schreiben kann.

**Die Heilung trennt die beiden Fälle** und gibt dem nackten einen Guard:
`_ZAHL_MIT_EINHEIT` (immer eine Behauptung), `_ZAHL_NACKT` plus
`_ist_rechtskontext()` für Fundstellen, Paragraphenverweise, Normklammern und
Link-Ziele, und `_zaahlbehauptung()` als einzige Entscheidungsstelle – eingesetzt
an genau den zwei Stellen, an denen `_marker_reparatur` entscheidet (Zeile 548
Fall b, 561 Fall c).

**Der Guard prüft den Kontext um den EINZELNEN Treffer, nicht den ganzen Satz.**
Das ist der Punkt, an dem eine naheliegende Heilung zur Scheinheilung würde: Ein
satzweiter Guard nimmt „Nach § 5 kostet das 460 € im Monat" die
Kennzeichnungspflicht, weil der Satz einen Paragraphen zitiert – und verstößt
damit still gegen genau das, was #964 durchgesetzt hat. Deshalb bleibt die
`460 €` eine Behauptung, während die `5` hinter dem `§` keine ist. **Beide
Richtungen sind geprüft**, sonst wäre die Heilung nur eine umgedrehte
Fehlmessung.

**Zwei Fundstellen-Hälften, nicht eine.** Der erste Anlauf deckte nur `2016` ab
(Slash folgt) und fiel durch: `679` hinter dem Slash matcht ebenfalls, und ihr
Kontext sieht für sich genommen harmlos aus – „/679) regelt die Verarbeitung…".
Erst `_FUNDTSTELLE_RUECK` (`\d\s*/\s*$`) schließt die Fundstelle ganz. Der
Messwert war der Beweis: 1 von 17 Proben rot, und es war genau die
DSGVO-Fundstelle.

**Nachweis:**

| Prüfung | Ergebnis |
| --- | --- |
| 17 Proben, beide Richtungen | ✅ 7 Rechtsnorm/Verweis → kein Stempel · 8 echte Modellrechnung → Stempel bleibt · 2 Mischfälle → Behauptung bleibt |
| End-to-End `pflicht_marker_heilen` auf dem Original-Befund | ✅ ergibt „…personenbezogener Daten. Du kannst Auskunft verlangen." – **wörtlich die Korrektur, die #1318 von Hand machte**, jetzt automatisch |
| **Sabotage-Gegenprobe:** Guard ausgeschaltet, alter Ausdruck zurück | ✅ **5 Proben rot, Exit 2** – und die Ausgabe reproduziert den Original-Satz wörtlich: „Die DSGVO (Verordnung (EU) 2016/679) … ; das ist ein Modellwert." |
| `test_marker_ruinen_964` | ✅ **Ran 26 tests, OK** (vorher 18 – 8 neue) |
| `test_duplikat_guard` / `test_pflichtcheck` / `test_pflichtcheck_frist` / `test_pflichtfeld_verlust_wache` | ✅ 27 / 39 / 23 / 28 tests, alle `OK` |
| **`pflicht_marker_reparatur.py` auf dem Bestand** | ✅ **„0 Reparatur(en) in 0 Datei(en)"** – die Heilung schreibt **nichts** um, sie verhindert nur zukünftige falsche Stempel. Keine Massenänderung, kein Siegelweg ausgelöst. |
| `selftest_runner` | ✅ **292 Wachen** (vorher 291), 584 Uhr-Proben, alle grün – `sprachkern.py` trägt jetzt `--selftest` und wird entdeckt, auch unter der um +97 und +1461 Tage vorgestellten Uhr |
| `skript_syntax_wache` / `konfliktmarker_wache` / `workflow_aufruf_vertrag` / `governance_contract --quick` | ✅ 736 · 6686 · 832/103 · 47 Regeln |
| `f4_entscheidungsvorlage --check` | ✅ aktuell – kein Content geändert, das Dossier bleibt stabil |

**Warum das hierher gehört und nicht in einen Folge-PR:** Die 192 Stempel waren
als offener Punkt mit genau diesem Auftrag dokumentiert. Ihn offen zu lassen,
nachdem der Injektor gefunden und die Reichweite gemessen ist, wäre dieselbe
Scheinheilung wie das Symptom-Putzen – nur mit besserer Begründung. Und der
Auftrag war klein genug, um ihn sauber zu erfüllen: zwei Entscheidungsstellen,
ein Guard, 19 Proben, null Bestandsumbau.

**Die 192 Stempel selbst bleiben, bewusst.** Sie stehen an Modellrechnungen, wo
der Stempel inhaltlich passt. Geheilt ist, dass keine Rechtsnorm mehr einen
bekommt. Ein `sed` über 72 Artikel wäre eine Massenänderung ohne redaktionelle
Prüfung jedes einzelnen Satzes und würde an versiegelten Beiträgen den Siegelweg
aus Abschnitt 2 auslösen – pro Artikel.

---

## 9. Offen, bewusst – mit Begründung

1. **Kalender-Artefakte – Korrektur einer eigenen Fehleinschätzung.** Die erste
   Messung dieses Auftrags notierte: `data/social/kalender/mastodon.ics:417`,
   `static/kalender/mastodon.ics:417` und `data/social/kalender/video.md:27`
   tragen noch den alten Kfz-Titel und hätten **keinen maschinellen Schreiber**.
   Das war falsch, und der Beweis steht hier: `scripts/social_calendar.py --build`
   erzeugt alle Kalender (`<kanal>.md`, `<kanal>.ics`, `UEBERSICHT.md`,
   `README.md`, `static/kalender/index.html`) aus `data/social/schedule.yaml` +
   `state.yaml` + `channels.yaml` und läuft laut eigener Kopf-Doku „automatisch am
   Ende jedes Autopilot-Laufs (`social-autopilot.yml`)". Der Plan referenziert
   Beiträge per **Slug**, nicht per Titel – die Artefakte ziehen den Titel also
   selbst nach. Nachweis: ein Probelauf von `--build` ließ den alten Titel in
   **allen** Kalenderdateien verschwinden (`grep -c` → keine Treffer).
   Der Probelauf wurde trotzdem **zurückgenommen**
   (`git checkout -- data/social/kalender static/kalender`): Die Kalender sind
   *rollierend* (Fenster relativ zum heutigen Tag), der Bau schrieb 35 Dateien mit
   3515 Einfügungen / 3179 Löschungen. Das wäre zeitabhängiger Ballast in einem PR
   gewesen, den der nächste Autopilot-Lauf ohnehin überschreibt. Regel daraus:
   Kalender-Artefakte nie von Hand pflegen – sie sind Ableitung, nicht Quelle.
2. **Titel-Gate R1** – in Abschnitt 5 geheilt (Einzelfall redaktionell,
   `check_titles.py` jetzt Exit 0). Offen bleibt der **Fixer**:
   `ensure_colon_title()` gibt Fragetitel ohne Anhang unverändert zurück, obwohl
   die Doku Heilung verspricht. Der nächste Titel dieser Klasse bleibt wieder
   liegen, bis der Heiler selbst lernt, den Kopf aus `keywords[0]`/`inspiration`
   zu nehmen – eigener Auftrag, weil er den Bestand berührt und einen
   Idempotenz-/Sabotage-Selbsttest verlangt.
3. **Vier rote Bestandstests** – in Abschnitt 8 **geheilt**; offen bleiben zwei
   Folgethemen, die dieser PR bewusst nicht anfasst:
   - **192 Modellwert-Stempel – die Zahl bleibt, der Injektor ist geheilt.**
     `; das ist ein Modellwert.` stand **193-mal in 72 Artikeln**. Nach `main`'s
     Heilung sind es **192 in 72** – also ist exakt **eines** verschwunden, das im
     Reisekasse-Artikel. Das ist kein Vorwurf an #1318: Genau dieses eine war
     falsch, weil es einen Rechtssatz verdrängt hatte, und genau deshalb war es
     über einen Test nachweisbar.
     **Hier standen zwei Dinge, die jetzt getrennt sind.** Der *Injektor*, der
     eine Rechtsnorm mit einem Modellwert-Stempel überschrieb, war die Wurzel –
     er ist in **Abschnitt 8.10** geheilt, mit Guard, 19 Proben in beide
     Richtungen, Sabotage-Gegenprobe und dem Nachweis, dass er den Bestand nicht
     umschreibt. Die *192 Stempel selbst* bleiben offen, und zwar bewusst: Sie
     stehen an Modellrechnungen, wo der Stempel inhaltlich passt. Ein Repo-weites
     `sed` über 72 Artikel wäre eine Massenänderung ohne redaktionelle Prüfung
     jedes einzelnen Satzes und würde an versiegelten Beiträgen den Siegelweg aus
     Abschnitt 2 auslösen – pro Artikel. Geheilt ist, dass keine Rechtsnorm mehr
     einen bekommt; das ist der Teil, der faktisch falsch war.
   - **`ff_inhalts_wache.py` hat keinen Aufrufer außer `discover` – und das
     Hindernis ist jetzt weg.** Die Wache läuft weiterhin nur, weil Schritt 11
     `discover` fährt, nicht weil ein Gate sie beim Namen ruft; in der
     `selftest_runner`-Entdeckung (291 Wachen) steht sie auch nicht. Sie gehört
     neben das bestehende Diff-Tor in `link-check.yml:213`, wo
     `bestand_einzigartigkeit_gate.py` bereits läuft. **Nicht in diesem PR** –
     aber die Begründung hat sich geändert: Ursprünglich hätte das Verdrahten
     vier neue rote Gates erzeugt, weil die Befunde noch offen waren. Seit #1318
     ist der Bestand grün (`FF1–FF5: 0 Befund(e)` am liegenden Stand, gemessen
     mit `main`'s Wache), die Reihenfolge „erst Befunde heilen, dann Gate scharf
     stellen" ist also **erfüllt** und der Weg frei. Was fehlt, ist ein eigener
     PR mit Workflow-Edit, `trigger_wache`-Bezug und Idempotenz-Nachweis – und
     der gehört nicht in einen Gate-PR, der selbst schon sechs Rebases hinter
     sich hat. Der Selbsttest ist inzwischen gesichert (Kasten in Abschnitt 8,
     Punkt 6), die Verdrahtung nicht.
   - **`automatic_write_protected()` meldet „geschützt" für unlesbare Pfade.**
     Fail-closed ist richtig und bleibt. Offen ist, dass die Klausel
     „Datei fehlt" und „Datei ist versiegelt" nicht unterscheidbar macht – beides
     ergibt `True`. Ein eigener Rückgabewert oder eine Logzeile für den
     Exception-Fall hätte die Fehlmessung aus 8.2 in einer Sekunde sichtbar
     gemacht statt über einen Umweg. Kleiner Auftrag, eigener PR, weil er die
     Signatur einer von vielen Heilern genutzten Funktion berührt.
4. **Historische Protokoll-Doks** mit altem Titel bleiben unverändert
   (Begründung in Abschnitt 2): Ein Prüfbericht ist ein zeitgebundener Beleg – wer
   ihn nachträglich auf den neuen Titel biegt, fälscht das Datum der Prüfung.

---

## 10. Nachweis – alle Gates am liegenden Stand gemessen

Vollständige Batterie, jede Prüfung einzeln mit Exit-Code (nicht „ein Skript lief
durch"):

```
== Skript-Syntax (liegender Stand) ==
  ✅ skript_syntax_wache --selftest / --check          ✅ workflow_js_wache --selftest / --check
  ✅ trigger_wache --selftest / --check                ✅ workflow_aufruf_vertrag --selftest / --check
  ✅ skript_syntax_heiler --selftest
== Integritäts-Siegel ==
  ✅ integrity_guard --gate / --selftest               ✅ unittest test_integrity_guard
== YMYL-Siegelprüfung ==
  ✅ unittest Siegel + Schreibschutz (4 Module)        ✅ ymyl_siegel_wache (Bestand)
== Qualitäts-Gate ==
  ✅ governance_contract --quick (47 Regeln)           ✅ unittest Gate-Verträge (7 Module)
  ✅ abgeleitete_register --selftest / --check
== Entity-Marken-Gate ==
  ✅ --selftest  ✅ --source-only  ✅ --public public (Bau)
== E2E / Playwright ==
  ✅ manifest_guard / frontmatter_wache / metadaten_wache / tabellen_lesbarkeit_guard
  ✅ unittest E2E-Verträge (14 Module, inkl. test_git_sync + test_trigger_wache)
  ✅ check_covers  ✅ Hugo-Bau (Extended 0.168.0)  ✅ h1_wache --public
  ✅ linktext_wache --public  ✅ interne Links  ✅ schema_seo_gate
  ✅ seo_cockpit --fail-on description-length,description-breite,heading-order
  ✅ newsletter_digest --check  ✅ newsletter_qa --build
  ✅ npx playwright test → 184 passed (9.7m)
== Deploy-Siegel-Pfad ==
  ✅ ki_cover_herkunft --selftest  ✅ ki_bild_markierung --selftest / --gate
  ✅ editorial_review_gate --published --strict
== Titel-/Cover-Gate (nach Heilung D) ==
  ✅ check_titles → 144 Titel | Verstöße: 0 (vorher 1, Exit 1)
  ✅ check_covers → 144 Covers | Probleme 0 | Stale 0 | Brand 0 | Text 0
  ✅ casing_guard  ✅ ki_cover_herkunft --heilen → 144 gemessen, 0 hart
== Code-Regression (nach Heilung G) – auf dem CI-Weg selbst gemessen ==
  ✅ ci_tests.py -- python -m unittest discover -s scripts/tests -v
     → die vier Befund-Module vorher rot, jetzt OK:
       test_einzigartigkeit_1027      (21 tests)  Flesch 59.9 → 60.60
       test_einzigartigkeit_bestand   ( 4 tests)  5 Phrasen → 0
       test_faktenfrische_763         (21 tests)  Rechtssatz 0 → 1
       test_inhalts_register                      FF3 4 → 0
  ✅ engine_generate / reserve_pool / cadence_guard --selftest
  ✅ fm_boundary_guard --selftest / --check   ✅ social_studio --selftest
== Inhalts-Wache (nach dem Parser-Fix aus 8.1) ==
  ✅ ff_inhalts_wache --selftest → 7 FF1- + 8 Feld- + 2 Vertrags-Proben
  ✅ ff_inhalts_wache (Bestand) → 0 Befund(e)   (vorher 4, einer davon falsch)
== Ableitungen nach den Texteingriffen (Projektionskette zu Ende gefahren) ==
  ✅ faktenfrische_befund_akte --schreiben → 306 Befunde / 83 Seiten
  ✅ abgeleitete_register --fix → 3 Register   ✅ --check → aktuell (3 geprüft)
  ✅ f4_entscheidungsvorlage → 2877 Zeilen     ✅ --check → aktuell
  ✅ unittest test_1098_produktionswahrheit → Ran 22 tests … OK
  ✅ engine_generate / reserve_pool / cadence_guard / fm_boundary_guard
     (--selftest + --check, 174 Dateien) / social_studio – alle 6 Selbsttests
     aus Schritt 11
```

`selftest_runner.py` (Entdeckung aller Wachen, uhrfest, schreibfrei) lief zuvor
grün: **291 Wachen · 582 Proben · 444,3 s**.

**Basis – acht Rebases, weil `main` während der Arbeit achtmal weiterlief.**
Gemessen wurde jeweils **nach** dem Angleichen, nicht davor:

1. **Rebase auf `25f6f89`** (PR #1307 gemergt, zwei Automationsläufe, neue
   Layout-/CSP-Skripte inkl. `scripts/tests/test_ymyl_siegel_wache.py`).
   Überlappung: genau eine Datei – `.github/workflows/code-selbstheilung.yml`,
   dort hatte `main` dieselbe W1-Heilung selbst eingespielt. Eigene Fassung
   zurückgenommen (Abschnitt 7). Dieser Rebase lief konfliktfrei.
2. **Rebase auf `c873f7b`** (218 Dateien neu auf `main`, darunter PR **#1315**
   „M1-Heilung: kfz-Titel auf 59 Zeichen" – dieselbe Heilung A, anderer Titel).
   **20 Konflikte**, alle nach Hauspolitik „Bestand gewinnt"
   (`GIT_SYNC_BESTAND_POLICY`, #590) auf `origin/main` aufgelöst: Kfz-Artikel,
   Kfz-Cover (15 Dateien), `e2e/archivredaktion.spec.mjs`, `covers_manifest.json`,
   `fcp_images.json`, `static/llms.txt`. Der eigene, dadurch überstimmte
   Siegel-Eintrag wurde aus `data/editorial_review_history.jsonl` zurückgenommen –
   **nur der eigene**: die append-only-Kette des Bestands blieb bitgleich
   (`diff` gegen `origin/main` leer). Abgleitete Artefakte danach neu erzeugt
   (`generate_covers --slug …`, `ki_cover_herkunft --heilen`,
   `abgeleitete_register --fix`), nicht von Hand geflickt.
3. **Rebase auf `628da3a`** – darunter `9630dea` „Kadenz-/Titel-/Cover-Heilungen
   vor Veröffentlichung (automatisch)": `main` hatte **dieselben vier stale Cover**
   selbst neu gerendert, die Abschnitt 6 misst. **6 Konflikte**
   (`covers_manifest.json`, `fcp_images.json`, 4 Cover-JPGs), alle erneut nach
   Hauspolitik auf `origin/main` aufgelöst. Danach `ki_cover_herkunft --heilen` →
   **4 Belege erneuert**, denn der Automationslauf renderte neu, **ohne** die
   Herkunft zu heilen – genau die Drift-Klasse aus Abschnitt 4, erzeugt von `main`
   selbst. Der Byte-Nachweis steht in Abschnitt 6: vier `sha256sum`-Werte gegen
   vier Beleg-Werte, alle vier ❌. Eigener Delta danach: 4 Artikel-`index.md`
   (ausschließlich `cover.ki_pruefung`) + diese Akte, **0** Cover-Dateien.
4. **Rebase auf `dba3f17`** – **konfliktfrei**, als einziger der fünf. Überlappung
   mit `main`'s 60 Dateien: **0**; `main` hatte keine der Befund-Dateien
   angefasst, weder die Artikel noch `ff_inhalts_wache.py`, `check_uniqueness.py`,
   `readability_check.py`, `ci_tests.py` oder den Workflow. Neu auf `main` war
   dafür eine **neue Regel**: `lesbarkeit-live-diff.yml` (Befund #1247, Kopf-Doku
   vom selben Tag), das Diff-Tor aus Abschnitt 8.6 – es prüfte den eigenen
   Entwurf und fand ihn zu lang.
5. **Rebase auf `ae6fd3c`** – darunter `bc1e022` „**4 von 5 roten
   Regressionstests geheilt** (#1318)" und `5c5ee46` „Streaming-Bandbreite-Titel
   auf R1-Konvention (#1320)". `main` hatte damit **Heilung E/F und Heilung G
   selbst** eingespielt. **13 Konflikte** in drei Runden (Streaming-Artikel,
   `covers_manifest.json`, Cover-JPG, dann `BEFUND-AKTE.md`,
   `F4-ENTSCHEIDUNGSVORLAGE.md`, `data/faktenfrische_befunde_state.json`,
   `data/covers_manifest.json`, `static/llms.txt`, 4 Cover-Dateien,
   `scripts/ff_inhalts_wache.py`), sämtlich auf `origin/main` aufgelöst. Der
   Delta schrumpfte von 48 auf **22 Dateien**; zurückgenommen wurden der eigene
   `_field()`-Entwurf, alle fünf Inhaltsheilungen aus 8.1/8.3/8.4/8.5 und ein
   Pillar-Link, der im Bestand sonst **doppelt** gestanden hätte. Der Nachweis,
   dass Heilung D davon nicht betroffen ist, steht in Abschnitt 8.9: derselbe
   Bestand, mit `main`'s Prüfer `0 Befund(e)`, mit diesem `14 Befund(e)`.
8. **Rebase auf `aa2e99d`** – ein `modify/delete`-Konflikt, dreimal derselbe:
   `main`'s **#1324** (`b3445bb`) hatte den Artikel
   `2026-11-22-wlan-verbessern-lohnt-sich-mesh-oder-reicht-ein-repeater`
   **gelöscht** (auf `ffb1ea7` noch vorhanden, auf `b3445bb` weg), während dieser
   Branch zwei Beleg-Zeilen in ihm erneuert hatte. Hauspolitik Bestand-gewinnt →
   `git rm`, der Artikel folgt dem Bestand. Delta danach **23 Dateien**, und die
   Zählung sank von 146 auf **145** Cover.
   Nach dem Rebase grün gemessen: `ki_cover_herkunft --pruefen` → `145 Cover
   reproduziert, 0 Befund(e)`, `check_covers` → `145 | 0 | 0 | 0 | 0`,
   `check_titles` → `145 | 0`, `abgeleitete_register --check` → aktuell,
   `faktenfrische_befund_akte --check` → `301 offene Befunde`,
   `ff_inhalts_wache` → `0 Befund(e)`, `f4_entscheidungsvorlage --check` →
   **aktuell**. Das Dossier fiel damit **aus dem Delta**: `main` trägt bitgleich
   dieselben 2750 Zeilen – der erste Rebase in dieser Folge, nach dem das Dossier
   nicht neu geschrieben werden musste. Der Grund steht im nächsten Punkt.
7. **Rebase auf `954ee7c`** – **konfliktfrei**, obwohl diesmal **5 Dateien
   überlappten** (`F4-ENTSCHEIDUNGSVORLAGE.md` und vier Artikel, deren
   `cover.ki_pruefung`-Zeilen ich erneuert hatte). `main` lief mit **12 Commits**
   weiter, darunter `c3ab0f2` „content: unabhängige Redaktionsreserve
   auffüllen", `9fbffaa` „chore(faktenfrische): Akte, Stand und Queue
   nachgezogen", `fa3e8d0` „fix(titel): Streaming-Bandbreite – H1/Keywords auf
   R1-Titelform (#1323)" und **zwei** Läufe „fix(gate): Kadenz-/Titel-/Cover-
   Heilungen vor Veröffentlichung (automatisch)" (`33dcbfe`, `e5bcd4a`), die
   **44 Cover** neu schrieben. Genau deshalb ist „konfliktfrei" hier kein
   Erfolgsmeldung: Git konnte die Textzeilen sauber trennen, aber die **Bytes**
   unter den Belegen hatten sich bewegt. Gemessen danach: **14 frische
   Beleg-Driften** – die vierte Runde derselben Klasse, Nachweis in 8.9.
   Das Delta sank auf **24 Dateien**, weil `main` das Dossier inzwischen selbst
   trägt (`F4-ENTSCHEIDUNGSVORLAGE.md` ist bitgleich, 2803 Zeilen) und den
   Streaming-Artikel über #1323 ebenfalls.
6. **Rebase auf `48cdd67`** – **konfliktfrei**, wie der vierte. Drei Commits neu
   auf `main` (`48cdd67` Watchdog-Routing, `9d2f8f5` Pinterest-Report, `c1d7fe5`
   Scorecard), 5 Dateien, Überlappung **0**; weder `content/posts` noch
   `ff_inhalts_wache.py` noch eine Faktenfrische-Quelle berührt. Trotzdem ist die
   Ableitungskette danach **vollständig neu gemessen** worden, nicht nur
   stichprobenartig – genau die Regel aus Abschnitt 8.7:
   `ff_inhalts_wache --selftest` (18 Proben) und Bestand (0 Befunde),
   `check_covers` (144|0|0|0|0), `check_titles` (144|0),
   `abgeleitete_register --check` (3 aktuell),
   `faktenfrische_befund_akte --check` (301 offene Befunde),
   `f4_entscheidungsvorlage --check` (aktuell),
   `ki_cover_herkunft --pruefen` (144 reproduziert, 0 Befunde),
   `lesbarkeit_diff_wache --basis origin/main` (keine Regression) und die vier
   Zielmodule (`test_inhalts_register`, `test_1098_produktionswahrheit`,
   `test_einzigartigkeit_bestand`, `test_lesbarkeit_diff_wache`) → **ROT = 0**.

Was nach dem zweiten Rebase von Heilung A übrig ist und warum, steht in
Abschnitt 2 (Kasten); was nach dem fünften von Heilung G übrig ist, steht im
Kasten am Kopf von Abschnitt 8. **Nicht von `main` berührt und vollständig in
diesem Branch stehen Heilung B, C und D** – Backstop und Trigger-Notbremse
(Abschnitt 3) und die Klasse `beleg_veraltet` (Abschnitt 4). Das ist die
Dauerheilung dieses PR; alles andere hat der Bestand inzwischen selbst.

**Unittest-Vollfläche:** 312 Module. Die erste Messung lief in 16 Batches über
explizite Modulnamen und zählte `Ran` = **6331** – 13 Batches grün, 3 mit
insgesamt **4** Fehlschlägen, alle vier auf `origin/main` bitgleich reproduziert.
Dieser Batch-Weg bildete den CI-Weg **nicht** ab (Abschnitt 8, Lehre 4): Gemessen
wird jetzt auf dem Weg, den `regression` selbst fährt –
`ci_tests.py -- python -m unittest discover -s scripts/tests -v`. **Alle vier
Fehlschläge sind geheilt** (Nachweis in Abschnitt 8.8); kein neuer roter Test
durch diesen Branch.

**Merge-Weg:** Dieses Repository verbietet Merge-Commits
(`allow_merge_commit: false`) – ein `gh pr merge --merge` wird von GitHub
abgelehnt. Der Weg ist **`gh pr merge <nr> --squash`**, nie `--merge`, nie
`--auto`. Ein squash-merged PR löst die Folge-Workflows normal aus
(Push-Ereignis mit echtem Autor); zusätzlich fängt `deploy-catchup.yml`
(cron `20 * * * *`) Drift ab, und `skript-syntax.yml` misst den Bestand seit
diesem Auftrag unabhängig vom Schreiber (Abschnitt 3).

---

## 11. Geänderte Dateien (Kern)

**Endstand nach dem achten Rebase**: Delta gegen `origin/main` `aa2e99d` =
**23 Dateien** – der `wlan-verbessern`-Artikel folgte dem Bestand, der ihn über
#1324 löschte, und `F4-ENTSCHEIDUNGSVORLAGE.md` ist bitgleich zu `main`.
Zwischenstände: 48 Dateien nach Rebase 4, 22 nach Rebase 5, 25 nach Rebase 6,
24 nach Rebase 7. Nach dem sechsten Rebase waren es 25; `F4-ENTSCHEIDUNGSVORLAGE.md`
fiel heraus, weil `main` das Dossier inzwischen **bitgleich selbst trägt**
(2803 Zeilen, `git diff --stat` leer) – dasselbe Muster wie beim
Streaming-Artikel, den #1323 übernahm. Von den 24 sind 22 die Heilungen B/C/D
plus die zwei der Wurzelheilung aus Abschnitt 8.10 (`scripts/sprachkern.py`,
`scripts/tests/test_marker_ruinen_964.py`). Alles, was `main` inzwischen selbst hat, ist herausgerebased und
steht **nicht** mehr hier – die Tabelle ist der Beweis, nicht die Absicht.

Die 23. Datei kam **nach** dem fünften Rebase dazu und ist kein Widerspruch zum
Kasten in Abschnitt 8: `ff_inhalts_wache.py` steht in **beiden** Tabellen, weil
dort zwei verschiedene Dinge passiert sind. Der eigene `_field()`-Entwurf ist
zurückgenommen – `main`'s Fassung aus #1318 steht im Baum und bleibt unangetastet.
Was hier steht, ist ausschließlich die **Sicherung** dieses Fixes durch
Selbsttest-Proben (Kasten in Abschnitt 8, Punkt 6). Die Datei erscheint also
unten bei „zurückgenommen" für den Parser und hier bei „geändert" für die Proben.

| Datei | Änderung | Heilung |
| --- | --- | --- |
| `.github/workflows/skript-syntax.yml` | `schedule: "23 */4 * * *"` (Backstop, weil `GITHUB_TOKEN`-Commits keine Folge-Workflows auslösen) + `workflow_dispatch` | B |
| `scripts/trigger_wache.py` | `relevante_workflows()` über drei Bezüge (Datei selbst, `run:`-Aufruf, `paths`-Deckung), `pruefe(root, bezug=…)`, `bericht(…, bezug=…)`, `--bezogen-auf`, Selbsttest-Block 6, offene Auswahl-Meldung | C |
| `scripts/git_sync.sh` | `trigger_notbremse(staged\|push)` vor Commit/Push, Abbruch mit benannter Heilung (`::error::`), ohne Halb-Zustand (`git reset -q` bei staged) + Kopf-Doku | C |
| `scripts/tests/test_trigger_wache.py` | Klasse `BezugTest` (6 Tests) | C |
| `scripts/tests/test_git_sync.py` | Seed kopiert `trigger_wache.py`; Klasse `TriggerNotbremseTests` (5 Tests) | C |
| `scripts/ki_cover_herkunft.py` | Klasse **`beleg_veraltet`** in `messung()` (`belegt.strip().lower() != _sha256(ziel)` nach grüner Pixelmessung), `heilen()` mit Zähler `erneuert`, Selbsttest 2b/3b. Pixelabweichung bleibt **hart**. | D |
| `scripts/sprachkern.py` | **Die Wurzel zum Modellwert-Artefakt (8.10).** `_ZAHLBEHAUPTUNG` in `_ZAHL_MIT_EINHEIT` + `_ZAHL_NACKT` getrennt; `_ist_rechtskontext()` maskiert Fundstellen (`2016/679`, **beide** Hälften), Paragraphen-/Artikel-/Ziffer-/Seitenverweise, Normklammern `(EU)`/`(EG)` und Link-Ziele – pro **einzelnen** Treffer, nicht pro Satz; `_zaahlbehauptung()` als einzige Entscheidungsstelle an den zwei Stellen von `_marker_reparatur`. Dazu `selbsttest()` mit 19 Proben in beide Richtungen plus Idempotenz und ein `__main__`-Zweig, den `selftest_runner` entdeckt (291 → **292** Wachen). Bestand: `0 Reparatur(en) in 0 Datei(en)` – schreibt nichts um. | 8.10 |
| `scripts/tests/test_marker_ruinen_964.py` | Klasse `RechtsnormStattModellwertTests` (8 Tests, `Ran 26` statt 18), darunter `test_bestand_traegt_keinen_stempel_an_einer_rechtsnorm` – die Prüfung, die am 22.11.2026 fehlte: #1318 sah den einen Satz, den ein anderer Test zufällig abdeckte; diese sieht die **Klasse**. | 8.10 |
| `scripts/ff_inhalts_wache.py` | **Nur `selftest()`**, rein additiv: 9 Feld-Proben für `_field()` (nackt/einfach/doppelt quotiert, Doppelpunkt im Wert, fehlendes Feld, leeres Feld, Inline-Kommentar) + 2 Vertrags-Proben für die Siegel-Ausnahme in `_has_template_links()`. Meldung `7 FF1-Proben` → `18 Proben`. **Keine Zeile am Verhalten geändert** – `_field()` selbst ist die Fassung aus #1318 und bleibt es. Sabotage-Gegenprobe: Parser zurückgedreht → 6 Proben rot, Exit 2. | G, Kasten Punkt 6 |
| 14 Artikel-`index.md` | je **genau zwei Zeilen**: `cover.ki_pruefung.sha256` + `.geprueft_am` auf die Bytes der Datei erneuert. 13 Altlasten zu Beginn, danach 4 neue nach `9630dea` (Abschnitt 6), danach **14 neue** nach `ae6fd3c`/`200a9e3` (Abschnitt 8.9). Sonst keine Änderung an diesen Artikeln. | D |
| ~~`F4-ENTSCHEIDUNGSVORLAGE.md`~~ | **Nicht mehr im Delta.** Dossier nachgezogen, `2877 → 2803 Zeilen` – und `main` trägt inzwischen dieselben 2803 Zeilen **bitgleich**, also fällt die Datei nach Rebase 7 heraus. Der Nachweis, dass sie auf `main` zuvor veraltet war, bleibt gültig: **Auf `main` ebenfalls veraltet** – Gegenprobe im Bestands-Worktree: `--check` → Exit **1**, während die Akte grün ist (`301 offene Befunde`). `main`'s `8ad6d41` hatte die Akte gezogen, das Dossier nicht. | 8.9 |
| `GATES-DAUERHEILUNG-HIGHEND-2026-11-22.md` | dieser Beleg | — |

**Zurückgenommen, weil der Bestand sie selbst hat** (Hauspolitik
`GIT_SYNC_BESTAND_POLICY`, #590 – „Bestand gewinnt"):

| Datei | Wer es jetzt trägt | Nachweis |
| --- | --- | --- |
| `scripts/ff_inhalts_wache.py` **(nur `_field()`)** | `main` via **#1318** – `_field()` liest ebenfalls alle drei YAML-Formen, andere Umsetzung (ein Regex `^key:[ \t]*(.*)$` + manuelles Abschälen der Quote statt drei Muster), **dieselbe Diagnose** im Befundkopf. Eigener Parser-Entwurf per `--ours` verworfen; `main`'s Fassung steht unverändert. **Zurückgenommen ist der Parser, nicht die Datei** – die 11 Selbsttest-Proben sind ein eigener, rein additiver Beitrag und stehen oben in der Endstand-Tabelle | Abschnitt 8, Kasten Punkte 5–6 |
| `content/posts/2026-08-12-preisgarantie-gas…` | `main` via #1318 – Flesch über der Publish-Schwelle | 8.3 |
| `content/posts/2026-08-14-sparen-im-herbst…` | `main` via #1318 – keine kritische Live-Überlappung mehr | 8.4 |
| `content/posts/2026-08-26-handytarif-vergleichen…` | `main` via #1318 – derselbe Pillar-Link `../../pillar/internet-dsl/` **war schon gesetzt**; die eigene Fassung hätte ihn doppelt getragen (2 Treffer gegen 1) | 8, Kasten |
| `content/posts/2026-08-26-tagesgeld-zinsen…` | `main` via #1318 – Rechner- und Pillar-Link gesetzt | 8.1 |
| `content/posts/2026-10-25-strategisch-sparen…reisekasse…` | `main` via #1318 – Rechtssatz steht, Modellwert-Artefakt ist raus | 8.5 |
| `content/posts/2026-11-12-wie-viel-streaming-bandbreite…` | `main` via **#1320** – R1-Titel auf Doppelpunkt-Konvention | Abschnitt 5 |
| `static/images/covers/**` (19), `data/covers_manifest.json`, `data/fcp_images.json`, `static/llms.txt` | `main` – Cover selbst gerendert (`9630dea`, `200a9e3`, `ae6fd3c`), Register selbst gezogen | 6, 10 |
| `BEFUND-AKTE.md`, `data/faktenfrische_befunde_state.json` | `main` via `8ad6d41`/`ad204bc` – Akte grün am Bestand (`301 offene Befunde, Stichtag 2026-11-22`) | 8.9 |

**Nie im Delta, obwohl Messläufe sie berührt haben:** `data/schema_seo_history.jsonl`,
`.casing_report.json`, `data/casing_history.jsonl` (STATE_ONLY_PATTERN aus
`deploy.yml:302` / `deploy-catchup.yml:162`) – nach jeder Runde mit
`git checkout origin/main -- <pfad>` zurückgenommen und vor jedem Push einzeln
geprüft.
