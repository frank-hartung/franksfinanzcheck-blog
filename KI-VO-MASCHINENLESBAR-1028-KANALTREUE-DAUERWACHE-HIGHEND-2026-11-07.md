# KI-VO: Kanaltreue, Verbreitungsweg und Dauerwache (#1028)

**Datum:** 07.11.2026 · **Frist-ID:** `ki-vo-kennzeichnung-bestand` (02.12.2026)
**Ebene:** Technik + Vertrag · keine Rechtsberatung
**Vorakte:** `KI-VO-MASCHINENLESBAR-1028-DAUERHEILUNG-HIGHEND-2026-11-05.md`

## Befund

Die Vorakte vom 05.11.2026 baute die maschinenlesbare Betreiberebene auf vier
Kanälen und ein Gate dazu. Am 07.11.2026 wurde **derselbe Baum gemessen statt
gelesen** – mit dem Ergebnis, dass das Gate grün war und der Bestand trotzdem
Lücken hatte. Vier Befunde, alle am gebauten Produkt belegt:

1. **Deckung.** Das Gate zählte `content/posts`: 78 Seiten. Ausgeliefert werden
   109 reguläre Seiten in 19 Abschnitten. Die sechs Ratgeber-Säulen unter
   `pillar/` tragen eine synthetische Stimme und waren von keiner Regel
   erfasst. Ein Gate, das einen Ausschnitt misst, meldet einen Ausschnitt.
2. **Kanaltreue.** Regel M4 verglich das maschinenlesbare Signal gegen **einen**
   Textanker (`data-ff-ki-label`, „Mit KI erstellt oder bearbeitet"). Gemessen:
   84 Seiten spielen eine Stimme ab; 66 zeigten einen Hinweis, der vom **Text**
   sprach; 18 zeigten sichtbar **nichts**. Ein Signal ohne passenden sichtbaren
   Hinweis ist ein halber Kanal – und genau der war grün.
3. **Verbreitungsweg.** `public/index.xml` lieferte 50 Items, 45 davon mit
   `ai_generated: true`, und **keine** Herkunftsangabe. Aus diesem Feed
   publiziert Pinterest automatisch weiter. Der Verhaltenskodex der Kommission
   vom 10.06.2026 verpflichtet nachgelagerte Akteure, Markierungen nicht zu
   entfernen; hier ging sie schon beim Betreiber selbst verloren.
4. **Robustheit.** Fiel PyYAML aus, starb das Gate mit `ModuleNotFoundError`
   und Exit **1** – dem Code für „Inhaltsbefund". Ein kaputtes Messwerkzeug sah
   damit aus wie ein roter Artikel (C33/C38 verletzt).
5. **Bild-Ableitungen.** `scripts/image_optimizer.py` kannte
   `cover.ai_generated` nicht. Aus einem deklarierten KI-Original wären
   öffentlich erreichbare AVIF/WebP/JPEG-Geschwister ohne Markierung geworden –
   Beweismittel gegen die eigene Kennzeichnung.

Dazu ein Wartbarkeitsbefund: Die Bedingung „welche Modalität ist deklariert"
lag **dreimal** im Bestand (Vorlage, Feed-Entwurf, Article-Schema). Drei
Abschriften derselben Wahrheit sind drei Orte, an denen sie auseinanderlaufen.

## Heilung

Sieben Kanäle, eine Quelle (`layouts/_partials/_funcs/ki_modalitaeten.html`),
kein zweiter Pflegeort:

| # | Kanal | Regel |
|---|---|---|
| 1 | `<meta name="ai-generated">` + `ai-generated-scope` + `rel="describedby"` → `/impressum/#ki-hinweis` | M1, M2 |
| 2 | schema.org `creditText` im Article-JSON-LD | M1, M2 |
| 3 | `data-ai-generated` + `data-digital-source-type` am `<img>` | M1, M2 |
| 4 | IPTC `DigitalSourceType` **in der Bilddatei** (ohne Neukodierung) | M3 |
| 5 | Sichtbare Angabe zur Tonspur: Chip `data-ff-ki-voice-label`, `aria-describedby`, SR-Satz, `aria-label` aus `I18N` (DE/EN) | M2, M4 |
| 6 | Feed: `xmlns:ffki`, `describedby` auf Kanal- **und** Item-Ebene, `ffki:ai-generated`, `ffki:ai-generated-scope`, `media:credit` | M5, M7 |
| 7 | Bild-Ableitungen: Optimizer kennt deklarierte KI-Originale und leitet nichts Unmarkiertes ab | M6 |

Neu gebaut:

* `scripts/ki_provenienz.py` – gemeinsamer Kern: Vokabular, Frontmatter-Leser
  (zeilenbasiert, keine ReDoS-Fläche), Abbildung des **ganzen** Baums
  (Inhalt → URL, an 109/109 Seiten verifiziert), Feed-Leser, Kanalvertrag mit
  13 Nadeln, Heilung mit Beleg.
* `scripts/ki_provenienz_gate.py` – Regeln M1–M7 plus **W0** (Blindheit),
  Betriebsarten `--gate`, `--source-only`, `--heilen`, `--wache`, `--selftest`,
  `--json`, `--trocken`. Exit **0** sauber, **1** Inhaltsbefund, **2**
  Werkzeugfehler über `scripts/werkzeugbefund.py`.
* `.github/workflows/ki-provenienz-wache.yml` – heilt bei jeder Änderung an
  Kennzeichnungs-Pfaden und täglich 06:22 MESZ, führt das Alter ungeklärter
  Angaben gegen die Frist.
* `layouts/rss.xml` + `layouts/_default/rss.xml` – Feed-Kanal, bytgleich
  gespiegelt (Hugo nimmt je nach Version die eine oder die andere Fassung).
* `scripts/image_optimizer.py` – `ki_originale()`, `ist_ki_original()`,
  `ki_ableitungen()`, Sprungmarke `KI_ORIGINAL_UEBERSPRUNGEN`, Befund
  `KI_ABLEITUNG_UNMARKIERT`; fail-closed (`SystemExit`), wenn der Kern nicht
  ladbar ist.

## Dauerhaft gesichert

**Selbstheilung** repariert nur, was mechanisch eindeutig ist, und belegt jeden
Eingriff in `data/ki_provenienz_history.jsonl`:

| Eingriff | Verifiziert am 07.11.2026 |
|---|---|
| Anker `{#ki-hinweis}` an der vorhandenen Überschrift | entfernt → Fund M2 → `--heilen` → **bytgleich** zur Ursprungsfassung, 0 Funde |
| Bytgleichheit der RSS-Spiegelung | einseitig gebrochen → Fund M7 → `--heilen` → `cmp` identisch, zweiter Lauf 0 Eingriffe |
| Unmarkierte Ableitung eines KI-Originals | angelegt → Fund M6 → `--heilen` entfernt sie mit Belegzeile |

**Eskaliert** statt erfunden wird, was nur ein Mensch entscheiden kann: die
Herkunft eines Bildes, die tatsächliche redaktionelle Verantwortung bei einem
`menschlich`-Eintrag, die Anbieteranfrage – und der Fall, dass **beide**
RSS-Vorlagen verschiedene Fassungen des Kanals tragen.

**Alter:** `data/ki_provenienz_state.json` führt das Erst-Datum jedes
ungeklärten Eintrags. Gespeichert wird nur der Dauerzustand; Alter und
Restfrist werden zur Laufzeit gerechnet. Sonst committet die Wache täglich die
Uhr statt des Befunds (Lehre aus der Befundakte, 06.11.2026). Verifiziert:
zweiter Lauf `state_geaendert: nein`.

**Verankert** an zwei Stellen: `deploy.yml` heilt **vor** dem Build
(`--heilen --source-only`, damit ein fehlendes Bauprodukt nicht jeden Deploy
stoppt) und misst **nach** dem Build (`--selftest`, `--gate`); geheilt wird über
den bestehenden Gate-Heilungscommit. Die Wache läuft zusätzlich eigenständig.

**Gegenproben** (jede mit Rücksicherung, alle am echten Baum):

| Sonde | Ergebnis |
|---|---|
| KI-Siegel der Lesehilfe entfernt | 1× M2 + **84× M4** = 85 Funde |
| RSS-Spiegel einseitig gebrochen | M7, Heilung bytgleich, idempotent |
| Impressum-Anker entfernt | M2, Heilung bytgleich |
| `ki_bild_markierung` nicht ladbar | **W0**, Exit **2**, kein M3-Doppelfund, C38-Meldung |
| PyYAML fehlt | **W0**, Exit **2**, Werkzeugbefund-Datei geschrieben |

**Regression:** `scripts/tests/test_ki_provenienz_gate.py` (31 Tests) pinnt
Deckung, Ein-Quellen-Vertrag, Erwartungsableitung, Spiegelungs-Entscheidung,
Belegzeilen, Uhr-Verbot und Exit-Codes; `scripts/tests/test_a11y_audit.py`
(+4) pinnt den Kontrast des Siegels **aus der CSS-Quelle aufgelöst**, nicht
abgeschrieben. Der Selbsttest des Gates umfasst 12 Szenarien inklusive
Sabotageproben.

## Prüfung (Hugo 0.168.0 extended, PyYAML + Pillow aus `requirements-hugo.txt`)

| Messung | Ergebnis |
|---|---|
| `ki_provenienz_gate.py --gate` | **109/109** gebaute Seiten, **19** Abschnitte, **50** Feed-Items, **0 Funde** |
| `--gate --source-only` (ohne Build) | 19 Abschnitte, 0 Funde, Exit 0 |
| `--selftest` | 12 Szenarien grün |
| `--wache` | 0 Eingriffe, 1 Eskalation (12 ungeklärte `menschlich`-Einträge, 25 Tage vor Frist), 0 Funde |
| `unittest … test_ki_provenienz_gate` | 31/31 |
| `a11y_audit.py` | 0 Probleme, 0 Kontrast-Fehler; Siegel **12.34:1** hell, **12.28:1** dunkel |
| `unittest … test_a11y_audit` | 22/22 |
| Vorlese-Suiten | Toolbar 118/118, funktional 265/265, Parität 387/387, Reparatur/TTS-Härtung/Selbstheilung grün |
| `spam_guard.py --public public` | F-OK: 50 Items, kadenzkonform, Cover vorhanden, keine Duplikate |
| `image_optimizer.py --check --json` | 164 Quellen, 0 Probleme, `kiOriginale 0`, Exit 0 |
| `ki_bild_markierung.py --gate` | 0 deklarierte KI-Cover, 0 Funde |
| `blustradius_register.py` | 81 Schritte des Auslieferungswegs erklärt (vorher 80) |
| `trigger_wache.py --check` | 101 Workflows, 0 Befunde |
| `workflow_vertrag_wache.py --gate` | 101 Workflows, V1–V6 erfüllt |
| `actions_version_guard.py --gate` | keine Drift |
| Hugo-Build | 119 Seiten, 406 Dateien, kein WARN/ERROR |

## Offen

Unverändert aus der Vorakte – nichts davon ist technisch heilbar, alles braucht
den Betreiber:

1. **Anbieter-Inventar und schriftliche Anfrage** (Art. 50 Abs. 2 ist eine
   Anbieterpflicht): welche Text-/Bild-/Audio-Systeme produktiv sind, Rolle,
   Datum des Inverkehrbringens, und wie der Anbieter markiert.
2. **Bildherkunft je Datei**: 0 Cover sind heute als KI deklariert; aus dem Repo
   allein ist Vollständigkeit nicht belegbar.
3. **12 `menschlich`-Einträge ohne Beleg** (`data/ki_kennzeichnung.yaml`,
   14.08.–03.09.2026). Die Wache führt ihr Alter und eskaliert; klären kann sie
   die Frage nicht.
4. **Live-Abnahme** nach Deployment gemäß `docs/KI-TRANSPARENZ-ABNAHME.md` §4 –
   jetzt einschließlich Tonspur (mit/ohne JavaScript, beide Themen) und Feed
   (`/index.xml`). Erst danach und nach Betreiberfreigabe den Workflow
   „Fristen-Check (Recht)" mit `erledigt=ki-vo-kennzeichnung-bestand` ausführen.

**Grenze dieser Akte:** Ein grünes Gate belegt, dass die Betreiberebene
vollständig, widerspruchsfrei und auf dem Verbreitungsweg erhalten ausgeliefert
wird. Es belegt **keinen** Herkunftsbeweis, kein Wasserzeichen, keine
C2PA-Signatur und keine Erfüllung der Anbieterpflicht.
