# 🩺 Dauerheilung der roten Merge-Gates (22.11.2026) – eine Ursache, fünf rote Prüfungen

**Datum:** 22.11.2026 · **Auftrag:** „Bitte vollständig dauerhaft auf Highend-Level
einer Profi-Agentur beheben." · **Anlass:** Übergabe-Notiz „Beim Merge zu beachten":
Beim Squash-Merge waren auf dem PR die Prüfungen **Integritäts-Siegel**,
**Playwright-Suite**, **YMYL-Siegelprüfung**, **Entity-Marken-Gate**, **Gate** und
**Skript-Syntax** rot; die Rohlogs waren nicht abrufbar (EOF/Transportfehler), die
Befunde wurden deshalb zurückgestellt.

**Ergebnis vorweg:** Alle sechs Klassen sind auf dem liegenden Bestand grün
gemessen – nicht umgangen, sondern an der Ursache geheilt. Eine einzige
redaktionelle Zahl (Titel 64 Zeichen gegen die Grenze 60) war die gemeinsame
Ursache von **drei** der sechs roten Gates; eine Trigger-Vertrags-Drift im
gemeinsamen Schreibweg die vierte. Zusätzlich ist eine **unerkannte Drift-Klasse**
in der Cover-Herkunft aufgetaucht (13 Belege beschrieben nicht die Bytes der
Datei) und wurde als messbare Regel im Prüfer verankert, damit sie nicht erneut
still durchläuft.

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

**Drei Lehren aus dieser Tabelle**, die über den Einzelfall hinausgehen:

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

---

## 2. Heilung A – Titel, Siegel und die ganze Verdrahtung (M1)

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
| `data/social/kalender/mastodon.ics:417`, `static/kalender/mastodon.ics:417`, `data/social/kalender/video.md:27` | **kein maschineller Schreiber** – Handarbeit, offen | ⚠️ Abschnitt 6 |
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

## 5. Was bereits geheilt war – und warum das hier steht

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

## 6. Offen, bewusst – mit Begründung

1. **Kalender-Artefakte tragen noch den alten Kfz-Titel**
   (`data/social/kalender/mastodon.ics:417`, `static/kalender/mastodon.ics:417`,
   `data/social/kalender/video.md:27`). Es gibt **keinen maschinellen Schreiber**
   dafür; `social-autopilot.yml` ist der einzige `.ics`-Bezug. Eine Handänderung
   wäre ein Einzel-Fix ohne Wache – genau die Klasse, die dieser Auftrag abschafft.
   Empfehlung: Generator + Register-Eintrag in `abgeleitete_register.py`
   (dafür gibt es mit `generate_llms_txt.py` ein Vorbild). Nicht in diesem PR,
   weil ein neuer Generator eigener Vertrag, Selbsttest und Verdrahtung braucht.
2. **`check_titles.py` meldet 1 Verstoß (R1)** –
   `2026-11-12-wie-viel-streaming-bandbreite-du-wirklich-brauchst-dein`
   (47 Zeichen ohne Doppelpunkt). Nicht blockierend: `deploy.yml:559` ruft
   `--fix` auf, und der Bestand war bei `5e8233e` bereits rot, bevor dieser
   Auftrag begann. R1 ist eine Konventionsregel (Cover-Umbruch), kein M1-Blocker.
3. **Historische Protokoll-Doks** mit altem Titel bleiben unverändert
   (Begründung in Abschnitt 2): Ein Prüfbericht ist ein zeitgebundener Beleg.

---

## 7. Nachweis – alle Gates am liegenden Stand gemessen

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
```

`selftest_runner.py` (Entdeckung aller Wachen, uhrfest, schreibfrei) lief zuvor
grün: **291 Wachen · 582 Proben · 444,3 s**.

**Merge-Weg:** Dieses Repository verbietet Merge-Commits
(`allow_merge_commit: false`) – ein `gh pr merge --merge` wird von GitHub
abgelehnt. Der Weg ist **`gh pr merge <nr> --squash`**, nie `--merge`, nie
`--auto`. Ein squash-merged PR löst die Folge-Workflows normal aus
(Push-Ereignis mit echtem Autor); zusätzlich fängt `deploy-catchup.yml`
(cron `20 * * * *`) Drift ab, und `skript-syntax.yml` misst den Bestand seit
diesem Auftrag unabhängig vom Schreiber (Abschnitt 3).

---

## 8. Geänderte Dateien (Kern)

| Datei | Änderung |
| --- | --- |
| `content/posts/2026-08-26-kfz-versicherung…/index.md` | Titel 64→58 Zeichen, `aenderungsgrund`-Nachtrag, neues Siegel |
| `data/editorial_review_history.jsonl` | append-only Siegel-Eintrag |
| `e2e/archivredaktion.spec.mjs` | H1-Erwartung + Kommentar |
| `static/images/covers/**` (15), `data/covers_manifest.json`, `data/fcp_images.json` | deterministisch nachgerendert |
| `static/llms.txt`, `data/fachpruefung_register.yaml`, `BEFUND-AKTE.md` | via `abgeleitete_register.py --fix` |
| 12 weitere Artikel-`index.md` | `cover.ki_pruefung` auf die Bytes der Datei erneuert (Beleg-Drift) |
| `.github/workflows/skript-syntax.yml` | `schedule` (Backstop) + `workflow_dispatch` |
| `scripts/trigger_wache.py` | `relevante_workflows()`, `pruefe(root, bezug=…)`, `bericht(…, bezug=…)`, `--bezogen-auf`, Selbsttest-Block 6 |
| `scripts/git_sync.sh` | `trigger_notbremse()` + Einbau in staged- und push-Pfad + Kopf-Doku |
| `scripts/ki_cover_herkunft.py` | Klasse `beleg_veraltet`, `heilen()` mit `erneuert`, Selbsttest 2b/3b |
| `scripts/tests/test_trigger_wache.py` | Klasse `BezugTest` (6 Tests) |
| `scripts/tests/test_git_sync.py` | Seed kopiert `trigger_wache.py`; Klasse `TriggerNotbremseTests` (5 Tests) |
| `GATES-DAUERHEILUNG-HIGHEND-2026-11-22.md` | dieser Beleg |
