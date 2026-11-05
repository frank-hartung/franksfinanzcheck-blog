# Meta-Satzende #1069 – Dauerheilung auf Highend-Niveau (05.11.2026)

> Auftrag: Inhaber im Chat („Bitte dauerhaft auf Highend-Level einer Profi-Agentur
> beheben") sowie Herausgeber-Kommentar in #1069 vom 04.11.2026 („den Punkt an der
> Description ergänzen und neu siegeln"). Befund: ein Artikel, ein fehlendes
> Satzzeichen – und eine strukturelle Lücke, die genau diesen Befund dauerhaft
> gemacht hat. Beides ist geheilt: der Bestand über die dokumentierte
> YMYL-Freigabe, die Klasse an der Nahtstelle, an der sie entstand.

## 1. Befund

Das wöchentliche Meta-Qualitäts-Gate (`scripts/meta_report.py`) meldete seit dem
Lauf vom 04.11.2026 genau einen Artikel:

- **Wohngebäudeversicherung Vergleich: Worauf du achten musst**
  (`content/posts/2026-08-18-wohngebaeudeversicherung-vergleich-worauf-du-achten-musst/index.md`)
- Befund: `Description ohne Satzende (Punkt/!/?/… fehlt)` – Artikel-Score 85/100.
- Kennzahlen des Laufs: 76 Artikel · Ø Score 99,4/100 · Ø Titel 54,5 · Ø Description 142,4.

Der Ein-Zeichen-Fix aus PR #1071 wurde **zu Recht** von der YMYL-Siegelprüfung
blockiert: Der Artikel ist hochrisiko-versiegelt, und eine geänderte Description
ohne Neusiegelung bricht das Fachsiegel (E17). PR #1071 wurde geschlossen, #1069
blieb offen.

## 2. Ursache – warum ein Punkt zum Dauerbefund wurde

Die Git-Historie des Artikels zeigt die Kette lückenlos:

| Datum | Commit | Vorgang |
|---|---|---|
| 26.10.2026 | `6c614125` (#890) | SEO-Runde schreibt eine neue Description **ohne Satzende**. |
| 27.10.2026 | `bb4d3560` (#918) | Neusiegelung (`3d15a0a3…`) – die punktlose Fassung wird festgeschrieben. |
| 28.10.2026 | `d98624f7` | SEO-Heiler ergänzt den Punkt – ein **automatischer Schreibzugriff auf eine versiegelte Fassung**. |
| 29.10.2026 | `9bb3e86c` (#940) | YMYL-Restore stellt die geprüfte Fassung wieder her – der Punkt ist wieder weg. Korrekt so. |
| 04.11.2026 | – | Meta-Gate erzeugt #1069; PR #1071 versucht den Direkt-Fix und wird blockiert. |

Die strukturelle Lücke sitzt **zwischen zwei Wachen**:

- Das **Siegel-Gate** (`editorial_review_gate.py`) prüft fachliche Vollständigkeit
  (Quellen, Textanker, Zahlenprotokoll, Fristen, Hash) – aber nicht die
  Meta-Qualität der Description.
- Das **Meta-Gate** (`meta_optimizer.py` / `quality_score.py`) verlangt Satzende
  und Snippet-Fenster – aber sein Heiler überspringt versiegelte Artikel
  (`automatic_write_protected`), ebenfalls korrekt.

Ergebnis: Eine Fassung, die mit Meta-Befund versiegelt wird, ist für die Automatik
nicht mehr heilbar. Das Wochen-Gate meldet sie jede Woche und legt jede Woche ein
Issue nach – geheilt werden kann sie nur noch über eine neue redaktionelle
Freigabe. Genau das ist #1069.

## 3. Heilung des Bestands (dokumentierte YMYL-Freigabe)

Rein zeichensetzende Korrektur, keine fachliche Änderung:

- Description: ein Punkt am Ende. Maße danach **133 Zeichen / 857 px** – im
  Snippet-Fenster der SSOT (`serp_limits`: 100–155 Zeichen, ≤ 985 px).
- `aenderungsgrund` im Prüfprotokoll dokumentiert die Korrektur; Prüfer
  (`Redaktion FranksFinanzcheck`), Prüfertyp, Prüfdatum (05.10.2026) und nächster
  Review (19.11.2026) bleiben unverändert. Aussagen-, Zahlen- und Quellenprotokoll
  gelten unverändert – es wurde keine Aussage, Zahl oder Quelle angefasst.
- Neusiegelung über den dokumentierten Weg:
  `python3 scripts/editorial_review_gate.py --seal --file …/index.md`.
  Neues Siegel `210c16a84fefe83872ae42db27541fd2d6c626076caf18257262b8d1a0a95c1d`,
  append-only in `data/editorial_review_history.jsonl` protokolliert.
- `lastmod` bleibt 04.11.2026: ein Satzzeichen in der Description ist keine
  inhaltliche Änderung des Artikels (kein falsches Frische-Signal).

Damit ist das Meta-Gate grün: **76 Artikel · Ø Score 100/100 · Probleme: 0.**

## 4. Dauerheilung der Klasse (Siegel bindet Meta-Qualität)

Die Nahtstelle wird geschlossen, an der der Befund entstand – am Siegel selbst.
`editorial_review_gate.seal()` verweigert ab sofort eine Fassung, deren
Description das Meta-Qualitäts-Gate verletzt. Gemessen wird mit **denselben
Messstellen** wie im Publish-Score, ohne zweite Grenze und ohne Kopie:

- Satzende: `meta_optimizer.desc_has_sentence_end` (der dokumentierte Spiegel
  des Meta-Gates, genau die Funktion, die den #1069-Befund erzeugt).
- Snippet-Fenster: `serp_limits.befunde(desc, min_zeichen=0)` (Obergrenzen der
  SSOT; die Untergrenze ist Meldebestand der Wache, kein Publish-Hindernis –
  wie in `quality_score`).

Die Importe bleiben funktionslokal: Das Gate ist Modullast vieler Wachen und
zieht sich den SEO-Schreiber samt KI-Transportmodul nicht in den Importgraphen
jeder Wache. Das Siegel **prüft, es heilt nicht** – die Redaktion liefert die
saubere Fassung, das Siegel zieht sie erst dann fest. Ein verweigertes Siegel
lässt die Datei bytegleich unverändert und schreibt keinen History-Eintrag.

Warum genau diese Regel und nicht mehr: Titel, Keywords und Cover haben eigene
Gates bzw. eine eigene Pipeline (Cover wird nach dem Siegel erzeugt). Die
Description ist das SERP-Feld, dessen Satzende-Regel bisher **nur** das
Wochen-Gate kannte – sie war die ungeschützte Naht. Der Zeichensatz `.!?…` wird
nicht ein zweites Mal definiert, sondern über die vorhandene Messstelle gebunden.

## 5. Nachweis (alles lokal gefahren, reproduzierbar)

| Prüfung | Ergebnis |
|---|---|
| `meta_report.py` | 76 Artikel · Ø 100/100 · **Probleme: 0** (Exit 0) |
| `editorial_review_gate.py --selftest` | grün (inkl. neuer #1069-Proben) |
| `editorial_review_gate.py --published --strict` | 76 Artikel · 4 Hochrisiko · 4 freigegeben · **0 blockiert** |
| `ymyl_siegel_wache.py` | 108 Artikel · **0 Befunde** |
| `python3 -m unittest scripts.tests.test_editorial_review_gate` | **22 Tests OK** (4 neue) |
| YMYL-/Meta-/SERP-Suite (7 Module) | **110 Tests OK** |
| `metadaten_wache.py` | 115 Dateien · **0 Befunde** |
| `seo_cockpit.py --strict --fail-on description-length,description-breite,heading-order` | P1: 0 · P2: 0 (Exit 0) |
| `linktext_wache.py --public public` | crawlerlesbar, grün |
| `redos_guard.py` | 731 Python-Dateien · **0 Funde** |
| `skript_syntax_wache.py` | 647 Dateien kompilieren |
| `wachen_vertrag.py --selftest` · `skills_vertrag.py` | grün · 90 Skills, 0 Befunde |
| `governance_contract.py --quick` | **alle 45 Regeln erfüllt** |
| `hugo --minify` (Extended 0.168.0) | baut, 117 Seiten; Description mit Punkt im HTML |
| `belegketten_wache.py --selftest` | grün |

Neue Regressionen (in `scripts/tests/test_editorial_review_gate.py`, verdrahtet
über die YMYL-Siegelwache auf jedem PR nach `main`):

1. `test_siegel_verweigert_description_ohne_satzende` – Siegel verweigert, Datei
   unverändert, kein History-Eintrag.
2. `test_siegel_verweigert_description_ausserhalb_snippet_fenster` – zu lang/zu
   breit wird verweigert.
3. `test_siegel_akzeptiert_meta_sauberere_description` – saubere Fassung wird
   versiegelt, Hash stimmt, genau ein Audit-Eintrag.
4. `test_versiegelte_fassungen_sind_meta_sauber` – **Bestands-Invariante**: jede
   versiegelte Fassung besteht die Description-Regel. Hätte dieser Test am
   27.10. existiert, wäre die Neusiegelung der punktlosen Description im PR
   aufgefallen.

## 6. Grenzen und Ehrlichkeit

- **Belegketten im Netz:** Der Sandbox-Lauf meldet die externen Quellen als
  `unklar` (URLError – hier sind nur GitHub/PyPI/npm-Hosts erreichbar). Das
  blockiert nicht (`tot` schon, Exit 0). Der YMYL-Workflow auf dem GitHub-Runner
  (volles Netz) lief am 05.11.2026, 13:15 UTC, **grün** – die Belegkette ist dort
  live geprüft. Da keine Quelle oder Aussage geändert wurde, ist ihr Stand
  unverändert.
- **Fachfreigabe bleibt menschlich:** Die Neusiegelung erfolgt auf ausdrücklichen
  Auftrag des Herausgebers und ändert keine fachliche Substanz. Der neue
  Siegel-Vorlauf erfindet weder Prüfer noch Status – er verweigert nur schlechte
  Meta-Qualität, bevor sie festgeschrieben wird (D13 bleibt unangetastet).
- **Keine Workflow-Änderung:** Die Heilung liegt im Skript und im Bestand, nicht
  in `.github/workflows/**`. Das Wochen-Gate erzeugt künftig kein Issue mehr für
  diesen Befund, weil der Bestand grün ist; #1069 wird über `Closes #1069` im PR
  geschlossen, der Abschlussvermerk kommt vom Workflow (nicht von Hand).
- **Vorbestehender roter CI-Job (nicht durch diesen PR verursacht):** Der Job
  `regression` (Publication reliability) fährt die gesamte Suite
  (`unittest discover -s scripts/tests`, 5234 Tests). Drei Datenstands-Tests
  scheitern darin – `test_inhalts_register` (fachpruefung_register.yaml veraltet),
  `test_release_scorecard` und `test_faktenfrische_befund_akte` (je
  `nicht_entscheidbar: 5`). Nachweis der Vorbestehens: **identisch auf dem
  Basis-Commit `86c59a4` ohne diese Änderung UND auf dem aktuellen main-Kopf
  `dfca64a1`** ( jeweils in einem eigenen Worktree gefahren). Sie gehören zur
  Release-Scorecard-/YMYL-Fachbefund-Linie (#1074, #1024, #1026), nicht zu #1069,
  und verlangen fachliche Entscheidungen. Diese Änderung fügt vier grüne Tests
  hinzu und macht keinen bestehenden Test rot. Gemäß D11 („kein Merge vor dem
  grünen Abschluss DIESES Commits") bleibt der Merge die Entscheidung des
  Herausgebers, solange der vorbestehende Befund offen ist.

## 7. Geänderte Dateien

- `content/posts/2026-08-18-wohngebaeudeversicherung-vergleich-worauf-du-achten-musst/index.md`
  – Description-Satzende, `aenderungsgrund`, neues Siegel.
- `data/editorial_review_history.jsonl` – ein append-only Audit-Eintrag.
- `scripts/editorial_review_gate.py` – `meta_befunde_description()` + Siegel-Vorlauf,
  neue Selbsttest-Proben.
- `scripts/tests/test_editorial_review_gate.py` – vier Regressionen.

Wahrheitsorte: `docs/ANLEITUNG-REDAKTIONELLE-YMYL-PRUEFUNG.md` (Freigabe in fünf
Schritten), `scripts/serp_limits.py` (Snippet-SSOT), `scripts/meta_optimizer.py`
(Satzende-Heiler #295), `scripts/quality_score.py` (Publish-Meta-Regel).
