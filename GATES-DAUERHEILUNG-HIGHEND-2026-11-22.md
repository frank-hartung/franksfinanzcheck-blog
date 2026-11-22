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
gemeinsamen Schreibweg die vierte. Darüber hinaus wurden zwei Defekte geheilt, die
die Übergabe nicht nannte, weil sie niemand sehen konnte:

- **Heilung C** – eine unerkannte Drift-Klasse in der Cover-Herkunft: 13
  Belege im Live-Bestand beschrieben die Bytes einer Vorfassung. Als messbare
  Regel (`beleg_veraltet`) im Prüfer verankert, damit sie nicht erneut still
  durchläuft.
- **Heilung D** – das Titel-Gate stand bei **Exit 1** (R1), weil der Heiler
  `ensure_colon_title()` Fragetitel ohne Anhang unverändert zurückgibt, während
  `deploy.yml` den Befund mit `|| echo` schluckt.

Ehrlich dazugesagt: Vier weitere Bestandstests sind rot – **bitgleich auch auf
`origin/main`** und von keinem Workflow aufgerufen (Abschnitt 8). Sie gehören in
die Redaktion, nicht in dieses PR; der Nachweis und die Reihenfolge stehen dort.

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

## 8. Nebenbefund – vier rote Bestandstests, die kein Workflow ruft

Für diesen Auftrag wurde **nicht** nur die Check-Matrix des PR nachgefahren,
sondern die volle Unittest-Fläche: alle **312** Module in `scripts/tests/`
(`python -m unittest` in 16 Batches; `discover` scheitert am fehlenden
`__init__.py`, und die CI ruft Module grundsätzlich namentlich auf).

Dabei fielen vier Tests auf, die **auf `origin/main` (`25f6f89`) exakt gleich rot
sind**. Der Nachweis wurde geführt, nicht vermutet: dieselben Module in einem
`git worktree` von `origin/main` gestartet – dieselben Assertionen, dieselben
Werte. Dieser Branch fügt also **keinen** neuen roten Test hinzu.

| Roter Test | Befund | Auf `main`? |
| --- | --- | --- |
| `test_einzigartigkeit_1027` · `test_gas_artikel_flesch_ueber_publish_schwelle` | `2026-08-12-preisgarantie-gas…`: Flesch **59.9** < Publish-Schwelle 60.0 (R6) | ✅ identisch rot |
| `test_einzigartigkeit_bestand` · `test_kein_kritisches_live_paar_im_bestand` | `2026-08-14-sparen-im-herbst…` ↔ `2026-08-26-kfz-versicherung…`: **5** gemeinsame 7-Wort-Phrasen | ✅ identisch rot |
| `test_faktenfrische_763` · `test_reisekasse_praezisierungen_und_recherche_bleiben_erhalten` | Rechtssatz „Das lässt sich nicht pauschal zusagen." fehlt im Artikel (0 != 1) | ✅ identisch rot |
| `test_inhalts_register` · `test_live_wache_ist_gruen` | FF3: drei Live-Artikel ohne Pillar-/Rechner-Link (`handytarif`, `kfz`, `tagesgeld`) | ✅ identisch rot |

**Warum sie kein Gate rot machen:** Alle vier Module haben **null** Aufrufe in
`.github/workflows/` und `package.json`. `scripts/ff_inhalts_wache.py` hat im
gesamten Repository **keinen einzigen Aufrufer** außer sich selbst und steht auch
nicht in der `selftest_runner`-Entdeckung (291 Wachen). Wer kein `run:` in einem
Workflow hat, läuft nie.

Das ist dieselbe Klasse wie Abschnitt 1, Lehre 3 – nur eine Stufe stiller: Dort
maß ein Gate zu selten, hier **hängt die Wache an gar keinem Gate**. Vier echte
Inhaltsbefunde (haarscharf verfehlte Lesbarkeits-Schwelle, kritische
Live-Überlappung der #1027-Familie, fehlender Rechtssatz, drei fehlende interne
Links) liegen deshalb unbemerkt auf `main`.

**Bewusst nicht in diesem PR geheilt – mit Begründung:**

1. Alle vier Befunde sind **redaktionell** (Satz ergänzen, Passage eigenständig
   formulieren, interne Links setzen, Lesbarkeit heben) und treffen **versiegelte
   Live-Artikel**: Jede Körperänderung bricht deren Freigabe und verlangt den
   vollen Siegelweg aus Abschnitt 2 – pro Artikel, nicht pauschal.
2. Die Wachen jetzt zu verdrahten, **ohne** die Befunde zu heilen, würde vier neue
   rote Gates erzeugen. Das ist das Gegenteil des Auftrags.
3. Empfohlene Reihenfolge: (a) Befunde redaktionell heilen und neu versiegeln,
   (b) Wachen neben das bestehende Diff-Tor in `link-check.yml:213` hängen
   (`bestand_einzigartigkeit_gate.py` läuft dort bereits), (c) `ff_inhalts_wache.py`
   in die `selftest_runner`-Entdeckung aufnehmen, damit sie nie wieder ohne
   Aufrufer altert.
4. Das Diff-Tor selbst ist grün: `bestand_einzigartigkeit_gate.py --basis <PR-Basis>`
   misst nur **neu** erzeugte Dopplungen – Altlasten zählen weder als Fund noch als
   Freispruch (V4-Messung). Dieser PR erzeugt keine.

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
3. **Vier rote Bestandstests ohne Aufrufer** – Abschnitt 8. Vorhanden auf `main`,
   redaktionell zu heilen, danach zu verdrahten. Nicht in diesem PR.
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
```

`selftest_runner.py` (Entdeckung aller Wachen, uhrfest, schreibfrei) lief zuvor
grün: **291 Wachen · 582 Proben · 444,3 s**.

**Basis – zwei Rebases, weil `main` während der Arbeit zweimal weiterlief.**
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

Was von Heilung A nach dem zweiten Rebase übrig ist und warum, steht in
Abschnitt 2 (Kasten). Alle übrigen Heilungen (B, C, D, E) sind von `main`
unberührt und stehen vollständig in diesem Branch.

**Unittest-Vollfläche:** 312 Module, 16 Batches – 13 Batches grün, 3 Batches mit
insgesamt **4** Fehlschlägen, alle vier auf `origin/main` bitgleich reproduziert
(Abschnitt 8). Kein neuer roter Test durch diesen Branch.

**Merge-Weg:** Dieses Repository verbietet Merge-Commits
(`allow_merge_commit: false`) – ein `gh pr merge --merge` wird von GitHub
abgelehnt. Der Weg ist **`gh pr merge <nr> --squash`**, nie `--merge`, nie
`--auto`. Ein squash-merged PR löst die Folge-Workflows normal aus
(Push-Ereignis mit echtem Autor); zusätzlich fängt `deploy-catchup.yml`
(cron `20 * * * *`) Drift ab, und `skript-syntax.yml` misst den Bestand seit
diesem Auftrag unabhängig vom Schreiber (Abschnitt 3).

---

## 11. Geänderte Dateien (Kern)

Stand **nach** dem zweiten Rebase (Delta gegen `origin/main` `c873f7b`), also ohne
die von `main` überstimmte Heilung A:

| Datei | Änderung |
| --- | --- |
| `content/posts/2026-11-12-wie-viel-streaming-bandbreite…/index.md` | Titel 47→52 Zeichen auf Hauskonvention (R1), `cover.alt`, `aenderungsgrund`-Nachtrag; unversiegelter Entwurf |
| 14 weitere Artikel-`index.md` | `cover.ki_pruefung` auf die Bytes der Datei erneuert (Beleg-Drift: 13 Altlasten + 1 nach R1-Render + 4 nach Stale-Render, teils dieselben Dateien) |
| `static/images/covers/**` (19 Dateien) | neu gerendert: Streaming-Slug (15) + 4 stale Cover |
| `data/covers_manifest.json`, `data/fcp_images.json` | Ableitung aus den Rendern |
| `static/llms.txt` | via `abgeleitete_register.py --fix` (1 Zeile: neuer Streaming-Titel) |
| `.github/workflows/skript-syntax.yml` | `schedule` (Backstop) + `workflow_dispatch` |
| `scripts/trigger_wache.py` | `relevante_workflows()`, `pruefe(root, bezug=…)`, `bericht(…, bezug=…)`, `--bezogen-auf`, Selbsttest-Block 6 |
| `scripts/git_sync.sh` | `trigger_notbremse()` + Einbau in staged- und push-Pfad + Kopf-Doku |
| `scripts/ki_cover_herkunft.py` | Klasse `beleg_veraltet`, `heilen()` mit `erneuert`, Selbsttest 2b/3b |
| `scripts/tests/test_trigger_wache.py` | Klasse `BezugTest` (6 Tests) |
| `scripts/tests/test_git_sync.py` | Seed kopiert `trigger_wache.py`; Klasse `TriggerNotbremseTests` (5 Tests) |
| `GATES-DAUERHEILUNG-HIGHEND-2026-11-22.md` | dieser Beleg |
