# Faktenfrische – Internet-Recherche für jeden Artikel (Agent Reach + Claude)

> Eingeführt am 27.09.2026. Betrifft **alle bestehenden und alle zukünftigen**
> Blogartikel sowie die Ratgeber-Silos unter `content/pillar/`.

## Warum es das gibt

Stil-Politur macht einen Text schön, nicht richtig. Ein Finanz-Ratgeber altert
über seine **Zahlen**: Strompreise, Netzentgelte, Kündigungsfristen,
Beitragsspannen, Stichtage. Für Google (E-E-A-T, YMYL) und noch stärker für
Antwortmaschinen (AI Overviews, ChatGPT Search, Perplexity) entscheidet die
**Belegkette**, ob eine Seite zitiert wird oder nur mitläuft.

Der Betrieb hatte bisher zwei Hälften: eine breite wöchentliche
Signalsammlung (`scripts/agent_reach_research.py`) und einen Verfallsmesser
(`scripts/decay_radar.py`). Was fehlte, war die Brücke – **artikelgenaue
Recherche, die zu einem prüfbaren Beleg im Artikel führt.** Das ist
`scripts/faktenfrische.py`.

## Die zwei Takte

| Takt | Auslöser | Befehl | Wo |
|---|---|---|---|
| **Erstellung** | jeder neue Artikel (kein `faktencheck` im Frontmatter) | `faktenfrische.py --neu --apply` | `content-engine-v2.yml`, Phase 3 |
| **Bestand** | Fälligkeit nach Risikoklasse | `faktenfrische.py --apply` | `faktenfrische.yml`, **täglich** 04:40 UTC (06:40 MESZ / 05:40 MEZ) |

Fälligkeit (SSOT `data/agent_reach/faktenfrische.yaml → intervalle`):

| Klasse | Erkennung | Intervall |
|---|---|---|
| saisonal | Heizung, Winter, Stichtag 30.11., Jahreswechsel … | 30 Tage |
| YMYL | Versicherung, Kredit, Zins, Tarif, Frist, Energie … | 45 Tage |
| standard | alles andere | 90 Tage |

**Bereiche:** `content/posts` (Blogartikel) und `content/pillar`
(Ratgeberseiten) laufen gemeinsam (`--scope alle`, Default). Bei gleicher
Dringlichkeit wird die Ratgeberseite zuerst bearbeitet – sie trägt die interne
Verlinkung ihrer ganzen Themenwelt.

Priorität 0 hat immer die **Erstrecherche**. Danach gilt **EDF – earliest
deadline first**: Wer die früheste Frist hat, kommt zuerst. (Bis 29.10.2026
sortierte der Lauf nach Risikoklasse; bei dauerhaftem Rückstand verhungerten
die Standard-Seiten mit 90-Tage-Intervall unbegrenzt hinter den saisonalen
Seiten, obwohl sie längst überfällig waren. Die Klasse war stärker als die
Frist – einer der Gründe für den Dauer-Alarm #912.)

## Deckung: der Takt muss zum Bestand passen (#912, 29.10.2026)

Ein Intervalldatum ist keine Messung, sondern eine Rechnung: Eine Seite mit
30-Tage-Intervall braucht 1/30 Prüfung je Tag. Über den Bestand summiert sich
das zu einem **Bedarf**; dem steht ein **Angebot** gegenüber (Budget je Lauf ×
Läufe je Tag aus dem cron). Solange das Angebot unter dem Bedarf liegt, wächst
der Rückstand jeden Tag – und die Release-Scorecard meldet „Faktenalter
blockiert“, obwohl kein Artikel falsch ist.

Am 27.10.2026 war genau das der Fall:

| Kennzahl | vor der Reparatur | nach der Reparatur |
|---|---|---|
| Bedarf | 2,58 Prüfungen/Tag (≈ 18/Woche) | unverändert |
| Takt | 2 Läufe/Woche × 3 = 0,86/Tag | 1 Lauf/Tag × 12 (Sockel; seit 04.11.2026 elastisch bis 16) |
| Deckung | **33 %** | 146 % beim Bestand vom 03.11.2026; seit dem Bündel-Nachzug (04.11.2026) prüft C45 zusätzlich den Spitzentag |
| Rückstand | +12 Seiten/Woche, nie abbaubar | im Kalenderplan in 3 Tagen abgebaut |

Die Intervalle wurden **nicht** angefasst. Weniger messen wäre keine Heilung.
Es wird mehr geliefert:

- **`planung.vorlauf_tage` (7):** Eine Seite wird *arbeitbar*, bevor sie
  fällig wird. Wer erst am Stichtag anfängt, arbeitet an einer roten Scorecard.
- **`budget.auto_skalierung`:** Der Lauf nimmt so viele Seiten, wie die
  Deckungsrechnung für einen fristgerechten Abbau braucht – nie unter
  `max_artikel_pro_lauf` (Sockel), nie über `hartes_limit_pro_lauf`.
- **`planung.nachhol_frist_tage` (7):** Ein Rückstand, der sich nicht binnen
  sieben Tagen abbauen lässt, macht den Lauf rot. Das ist ein Alarm **mit
  Schließpfad** (Governance C14) – grün, sobald der Plan konvergiert.

Die Rechnung selbst steht in `scripts/faktenfrische_kapazitaet.py`; sie liest
ausschließlich die eine Fälligkeitsregel (`faktenfrische.faelligkeit`) und den
echten cron der Workflow-Datei. Wer den Plan verschiebt, verschiebt die
Rechnung mit. Governance **C45** prüft den Plan, den der Lauf wirklich fährt:
Bei `auto_skalierung: true` ist das das **empfohlene Budget** (Sockel als
Untergrenze, hartes Limit als Obergrenze). Der Plan muss den Bedarf mit
`min_deckung_prozent` (110 %) decken und **unter** dem harten Limit bleiben –
sonst ist es ein Dauer-Spitzenbetrieb. Reicht die Kapazität nicht, wird der
**Bau** rot, bevor der Bestand rot wird.

```bash
python3 scripts/faktenfrische_kapazitaet.py            # Bedarf, Angebot, Abbauplan
python3 scripts/faktenfrische_kapazitaet.py --wache    # Exit 1, wenn nicht abbaubar
python3 scripts/faktenfrische_kapazitaet.py --json     # maschinenlesbar
```

### Nachzug 04.11.2026: der Spitzentag wird mitgemessen (#1039)

Die Wache hatte bis hierher **einen** Stichtag geprüft: „heute“. Das ist der
ruhigste Tag, nicht der härteste – die Prüftermine sind **Bündel**. Am
04.11.2026 verteilten sich 113 Seiten auf nur **34 Fristtage**, 29 davon mit
demselben `faktencheck: 2026-10-13`. Ergebnis: Die Wache war am 04.11. grün,
und ab dem 20.11. kippten 23 Seiten mit demselben Prüfdatum gemeinsam in die
Überfälligkeit – ohne dass Code oder Vertrag sich geändert hätten. Ein Lauf,
der am ruhigen Tag misst, meldet den Fehler erst, wenn der Kalender ihn
schreibt.

Seit dem 04.11. prüft C45 deshalb **zwei** Tage mit derselben Planrechnung:

1. den **Stichtag** (was heute zu tun ist: Deckung, Rückstand, Reserve), und
2. den **Spitzentag** (`spitzenlast_stichtag`): den Bündeltag im Horizont, an
   dem eine **heute noch frische** Seite zu spät geprüft würde.

Bewusst nicht geprüft wird der Tag, an dem längst alles überfällig ist: Dort
misst man den Alt-Rückstand (dafür gibt es `rueckstand_abgebaut`), nicht die
Kadenz – sonst wäre jeder Bestand „rot“, und das wäre eine Schwelle durch die
Hintertür.

**Gemessen, nicht geschätzt** (Wochentage 04.11.2026 – 03.11.2027):

| Sockel (`max_artikel_pro_lauf`) | Bündel-Befund |
|---|---|
| 4 (bis 04.11.2026) | 3 von 53 Wochentagen rot, u. a. „am 26.11. kämen 37 Seiten zu spät“ |
| 12 (seit 04.11.2026) | **0 von 53** |

Deshalb der Sockel 4 → 12. Er ist keine Verschärfung der Intervalle und keine
Verlängerung des Takts – es wird schlicht so viel geprüft, wie der Zulauf
verlangt. Limit (16) und Nachholfrist (7) bleiben unverändert.

**Offen bleibt eine andere Klasse:** Wenn sich ein Alt-Rückstand von über 100
Seiten aufbaut (z. B. am 31.12.2026), reicht auch das Limit 16 nicht, um ihn
binnen sieben Tagen abzubauen – dann melden die Wachen `erreicht: False`. Das
ist **kein** Bündel-Problem und wird von keinem Sockel geheilt; es ist die
Rückstands-Klasse aus #912 und gehört als eigene Entscheidung (Takt, Limit
oder Intervall) behandelt. Sie ist im Bericht vom 04.11.2026 als offener
Punkt geführt.

### Nachzug 30.10.2026: Kalender statt Wochenmittel (#912)

Ein Wochendurchschnitt kann keine tägliche Frist beweisen. Die Simulation läuft
daher über **120 echte Kalendertage**, arbeitet nur an cron-Tagen und darf
ein Tagesbudget nicht ansparen. Auswahl und Simulation verwenden denselben
EDF-Schlüssel. Nach jeder Prüfung entsteht aus dem tatsächlichen Prüftag die
nächste Frist; auch diese Folgetermine werden geprüft. Verspätung wird vor
der Arbeit des Tages gemessen, nicht erst danach weggeschrieben.

Die Wache und der Scorecard-Bericht prüfen bei `auto_skalierung: true` das
**empfohlene Budget**, das der Lauf auch verwendet. Der Sockel (12 seit
04.11.2026) bleibt als Untergrenze sichtbar; das harte Limit (16 seit
04.11.2026) ist die Obergrenze. Die Kalendersimulation bestimmt das Budget;
die Reserve zwischen Plan und Limit ist die Pufferfläche für
Nachfrage-Spitzen. Wächst der Bestand, wächst das empfohlene Budget mit – bis
zum harten Limit. Wird das Limit erreicht, wird C45 rot; dann müssen Takt,
Limit oder Intervall entschieden werden. Das ist der Schließpfad, kein
Dauerzustand. Das ist ein Plan, kein Nachweis erfolgreich ausgeführter
CI-Läufe. Ausfälle und nicht bestandene Prüfungen bleiben eigene, sichtbare
Befunde.

Die Uhrprobe am 04.11.2026 (+97 Tage) bündelte alle 112 Prüftermine in einem
Vollrückstand. Limit 10 konnte diesen nicht binnen der unveränderten
7-Tage-Nachholfrist abbauen. Die Kalenderrechnung benötigt dafür 14 Prüfungen
je Lauf; das Limit 16 lässt zwei Plätze Reserve. Bei etwa 30 Sekunden je Seite
sind das rund acht Minuten innerhalb des unveränderten 25-Minuten-Timeouts.
Eine feste Regression am 09.02.2027 prüft Abbaufrist, Folgefristen und Reserve.

## Prüfdatum ist keine inhaltliche Freigabe (#912)

`faktencheck` beantwortet nur: Wann wurde recherchiert? Es beantwortet nicht:
Sind alle gefundenen fachlichen Mängel entschieden? Deshalb gelten zwei
unabhängige Verträge:

- **F1 – Faktenalter:** Ist die Recherche innerhalb des Risikointervalls?
- **F4 – Fachbefund:** Gibt es noch einen offenen, nicht redaktionell
  entschiedenen Befund? F4 blockiert Publish-Gate und Release-Scorecard über
  denselben Collector `publish_gate.fakten_befund_failures()`.

Befunde liegen dauerhaft unter `fachbefunde` in
`data/faktenfrische_queue.json`. Ein späterer Lauf kann sie ergänzen, aber
nicht durch eine leere Antwort löschen. Die Queue wird atomar ersetzt.
Alt-Befunde aus `laeufe[].befunde` werden beim Lesen migriert; fehlt die
frühere Fassungsbindung, heißen sie `legacy-unbekannt` – sie bleiben offen,
sind aber am heutigen Text entscheidbar (siehe unten).

### Zwei Hashes: warum eine Heilung den Befund nicht mehr sperrt (03.11.2026)

Bis zum 02.11.2026 hing **alles** an `pruef_hash`: Titel, Beschreibung,
Kurzantwort, **Quellen** und Text. Das hatte zwei Folgen, die zusammen den
Bestand dauerhaft rot hielten (Ticket #912):

1. Die Maschine schreibt `quellen` selbst. Jede Quellenpflege änderte damit
   die „Fassung“ – und machte eine bereits dokumentierte Entscheidung
   ungültig. Der Schließpfad wurde durch die eigene Arbeit gelöscht.
2. Wurde ein Text zur Heilung eines Befunds geändert (genau der Zweck des
   Befunds!), passte der alte Hash nicht mehr. Eine Entscheidung über den
   neuen Text konnte den alten Befund **nie** schließen. Am 03.11.2026 standen
   so 21 von 57 Befunden an einem überholten Text, 20 weitere ohne Hash –
   unschließbar, per Konstruktion.

Seit dem 03.11.2026 gilt:

| Hash | Umfasst | Zweck |
|---|---|---|
| `pruef_hash` | Titel, Beschreibung, Kurzantwort, **Quellen**, Text | bindet die KI-Antwort an die vollständige Prüffassung |
| `text_hash` | Titel, Beschreibung, Kurzantwort, Text (ohne Quellen) | bindet den Befund und die menschliche Entscheidung an die Aussageflächen |

Eine Entscheidung nennt **beides**: `befund_fassung` (welcher Ledger-Eintrag
gemeint ist) und `geprueft_fassung` (welcher Text tatsächlich gelesen wurde).
Quellenpflege öffnet keine Entscheidung; eine Textänderung öffnet sie – dann
muss der Mensch die neue Aussage erneut anschauen. Die Maschine entscheidet
weiterhin nie fachlich.

### Befund redaktionell schließen (der Schließpfad)

Die Arbeitsliste ist **`BEFUND-AKTE.md`** – erzeugt aus Ledger und
Entscheidungen, mit Befund-ID, Typ, Alter, Fassungsstand, Beanstandung,
Beleg und dem fertigen Befehl. Sie wird vom Bestands-Takt täglich
aktualisiert und als GitHub-Ticket gespiegelt.

1. **Text und Beleg prüfen.** Mangel korrigieren (Zahl belegen oder entfernen,
   Aussage präzisieren) oder den Befund fachlich begründet zurückweisen.
   Keine automatische Textumschrift und keine Schein-Freigabe.
2. **Entscheidung dokumentieren** – eine Zeile, fassungsgebunden:

   ```bash
   python3 scripts/faktenfrische_befund_ledger.py \
     --entscheiden <BEFUND-ID> --von "Frank Hartung" \
     --begruendung "BDEW-Preis entfernt, 6-%-Wert an der Quelle verlinkt"
   ```

   Der Befehl prüft: der Befund ist offen, die ID ist eindeutig, die Seite
   ist lesbar, Person und Begründung (≥ 20 Zeichen) sind vorhanden. Er
   schreibt `data/faktenfrische_entscheidungen.yaml` atomar (Kommentarkopf
   bleibt), bindet an den heutigen `text_hash` und kontrolliert danach
   selbst, dass der Befund wirklich geschlossen ist. Ohne Person und
   Begründung schreibt er **nichts**.

   Übersicht und Stand:

   ```bash
   python3 scripts/faktenfrische_befund_akte.py --schreiben   # Akte + Zustand
   python3 scripts/faktenfrische_befund_ledger.py --wache     # Exit 1 ohne Schließweg
   python3 scripts/faktenfrische_befund_ledger.py --json      # offene Befunde
   ```

3. **Neu messen:** Die Akte neu erzeugen (`--schreiben`), dann
   Publish-Gate/Scorecard (`scripts/release_scorecard.py --live --streng`).
   Erst wenn alle anderen Checks grün sind, endet der Vorgang.

**Frist und Eskalation:** `befunde.frist_tage` (Standard 14) und
`befunde.eskalation_tage` (Standard 21) in `data/agent_reach/faktenfrische.yaml`.
Überschrittene Befunde stehen oben in der Akte und im Scorecard-Ticket als
Eskalation an den Herausgeber. Die Frist senkt keine Schwelle: Ein Befund
blockiert weiter, bis er entschieden ist – sie bestimmt nur, wer wann davon
erfährt.

Ein neues Prüfdatum allein schließt F4 nicht. Ebenso darf ein Mensch die
Entscheidung nicht stellvertretend durch eine Maschine erfinden lassen.
`data/faktenfrische_befunde_state.json` ist das Siegel der Akte (Zahlen für
Ticket und Bericht), `BEFUND-AKTE.md` die Sicht für Menschen – beide aus
derselben Regel.

## Was die Maschine schreiben darf – und was nicht

**Darf sie:** genau zwei Frontmatter-Felder.

```yaml
faktencheck: 2026-09-27
quellen:
  - titel: "BDEW-Strompreisanalyse: Haushaltsstrompreis 2026 bei 37,0 ct/kWh"
    url: "https://www.bdew.de/service/daten-und-grafiken/bdew-strompreisanalyse/"
    herausgeber: "BDEW Bundesverband der Energie- und Wasserwirtschaft"
    datum: "2026-08-21"
```

**Darf sie nicht:** den Artikeltext. Kein Satz, keine Zahl, keine Überschrift.
Fachliche Befunde („Wert X ist überholt“, „Aspekt Y fehlt“) landen in
`FAKTENFRISCHE-REPORT.md`, `data/faktenfrische_queue.json` und – ab
`melden.issue_ab_befunden` – in einem GitHub-Issue. Über Text entscheidet ein
Mensch (KI-Redaktions-Statut).

Ebenfalls tabu: `lastmod`. Ein Faktencheck ist keine inhaltliche
Überarbeitung; ihn als Frische auszuweisen wäre genau die Frische-Inflation,
die am 21.09.2026 abgeschaltet wurde.

## Anti-Halluzination: der doppelte Deckel

Claude bekommt den Artikel und das Dossier und antwortet in JSON. Bevor
irgendetwas geschrieben wird, gilt für **jede** URL:

1. Sie muss **wörtlich im Dossier** stehen (also wirklich abgerufen worden sein).
2. Ihre Domain muss auf der **Allowlist** in `faktenfrische.yaml` liegen
   (amtlich Rang 1, etablierte Instanz Rang 2, Wirtschaftsredaktion Rang 3).

Beides nicht erfüllt → die Quelle wird verworfen, der Befund bleibt ohne Beleg
stehen. Affiliate-Partner (CHECK24, Tarifcheck) sind bewusst **nicht**
belegfähig: Provisionsquelle ≠ Faktenquelle. `--selftest` friert genau diesen
Fall ein (ST3), inklusive einer erfundenen Beispiel-URL.

Die Fachprüfung läuft über den gemeinsamen LLM-Zugang des Blogs
(`scripts/llm_client.py`) mit den bereits etablierten Schlüsseln
`GROQ_API_KEY`, `NVIDIA_API_KEY`, `CLOUDFLARE_API_TOKEN` (+ `CLOUDFLARE_ACCOUNT_ID`)
oder `GEMINI_API_KEY` – alle kostenlos; kostenpflichtige Anbieter gibt es seit
dem 03.10.2026 nicht mehr. Der erste verfügbare Anbieter gewinnt, bei Ausfall rückt der
nächste nach. Ohne jeden Schlüssel läuft alles außer der Fachprüfung; die
Belegkette wird dann deterministisch aus den belegfähigen Fundstellen gebildet.

> **Korrektur 02.10.2026:** Die frühere Browser-Brücke über ein geteiltes
> Fremdkonto ist ersatzlos entfernt – sie wurde im Betrieb nie genutzt, die
> Fachprüfung war damit dauerhaft „übersprungen".
>
> **Seit 03.10.2026** hält das Transportweg-Gate diese Bauweise generell
> draußen: `scripts/ki_transportweg.py` Regel **T5** verbietet jede
> Browser-Brücke und jedes UI-Scraping (auch das von ChatGPT) in Skripten
> **und** Workflows, Regel **T9** verlangt, dass dieser Workflow mindestens
> zwei kostenlose Schlüssel durchreicht – damit ein leeres Tageskontingent
> die Fachprüfung nicht erneut still ausfallen lässt. Tests:
> `scripts/tests/test_ki_transportweg.py`, Runbook:
> `docs/ANLEITUNG-KI-TRANSPORTWEG.md`.

## Was der Leser sieht

`layouts/_partials/ff_quellen_box.html` rendert am Artikelende die Box
**„Quellen & Faktenstand“** – nummerierte Belege mit Herausgeber und Datum,
dazu der Prüfstempel „Fakten geprüft am …“. Dieselben Daten gehen als
`citation` in das Article-JSON-LD (`schema_article.html`), das Prüfdatum als
`sdDatePublished`. **Eine Quelle, zwei Ausspielwege** – Sichtbares und Schema
können nicht auseinanderlaufen.

Ohne `quellen:` rendert nichts. Kein leerer Kasten, kein Platzhalter.

## Befehle

```bash
python3 scripts/faktenfrische.py                 # Trockenlauf + Report
python3 scripts/faktenfrische.py --apply         # Belege schreiben
python3 scripts/faktenfrische.py --neu --apply   # nur neue Artikel
python3 scripts/faktenfrische.py --scope pillar --apply   # nur Ratgeberseiten
python3 scripts/faktenfrische.py --scope posts --apply    # nur Blogartikel
python3 scripts/faktenfrische.py --file content/posts/<slug>/index.md
python3 scripts/faktenfrische.py --offline       # ohne Netz: nur GEO-Reife
python3 scripts/faktenfrische.py --selftest      # 29 eingefrorene Fälle
npm run test:faktenfrische                       # Selbsttests + Offline-Regressionen
npm run faktenfrische                            # = Trockenlauf
```

Exit-Codes: `0` gelaufen · `1` offene Befunde (nur `--strict`) ·
`2` Selbsttest/Konfiguration rot (nichts geschrieben) · `3` keine Quelle
erreichbar · `4` KI-Fachprüfung unvollständig · `5` mindestens eine Seite
brach ab (Queue, Report und Ledger sind geschrieben).

## Wenn ein Lauf abbricht (#984, 01.11.2026)

Der Lauf vom 31.10.2026 schrieb eine Seite, verlor danach seine Buchhaltung
(`KeyError: _faellig`), und **Queue, Report und Ledger fielen mit ihm aus**.
Übrig blieben ein Dossier mit fünf belegten Befunden und ein Alarm, der nur
den letzten Schritt nannte. Drei Konsequenzen gelten dauerhaft:

1. **Seiten sind isoliert.** Eine Seite prüfen, schreiben und bilanzieren ist
   eine Einheit (`verarbeite_seite`). Wirft sie, steht sie mit Ursache unter
   „Abgebrochene Seiten“ in Report und Queue, der Lauf macht weiter und endet
   mit **Exit 5**. Kein stiller Teilerfolg: Der Ausfall bleibt rot.
2. **Neuladen löscht keine Buchhaltung.** `_faellig`, `_geo` und `bereich`
   sind Lauf-Wissen, nicht Datei-Wissen. Die geschriebene Fassung wird
   getrennt zurückgegeben (`fassung_nach_schreiben`) und ersetzt den
   Lauf-Datensatz nicht. Der Selbsttest friert den Fall ein (ST8).
3. **Die Meldung nennt die Ursache.** Der Workflow schreibt das Protokoll in
   `faktenfrische-lauf.log` (Artefakt + Step-Summary) und übersetzt den
   Exit-Code in der letzten Zeile in Klartext. Wer ein Ticket liest, muss
   nicht raten und kein fremdes Blob-Log laden.

**Nachlese.** Befunde, die nur im Dossier stehen, holt
`python3 scripts/faktenfrische_befund_ledger.py --nachlese --apply` ins
Ledger – idempotent, ohne erfundene Fassung und ohne je einen Befund zu
schließen. Der Bestands-Workflow fährt sie nach jedem Lauf, auch nach einem
Abbruch.

## GEO-Reife

Jeder Lauf bewertet nebenbei jeden Artikel auf sechs Merkmale, die
Antwortmaschinen brauchen: Kurzantwort, FAQ-Abschnitt, Belegkette, konkrete
Zahlen, Tabelle, Prüfdatum. Der Durchschnitt und die häufigsten Lücken stehen
im Report – das ist die Redaktions-Landkarte für den nächsten Ausbau.

## Pflege

- **Quartalsweise:** Feeds in `faktenfrische.yaml` prüfen (Kanal-Störungen
  stehen in jedem Dossier unter „Kanal-Störungen“).
- **Neue Themenwelt:** Block unter `themenwelten:` ergänzen – ohne Eintrag
  greift `standard:`.
- **Neue Belegquelle:** nur nach Prüfung in `quellen_allowlist` aufnehmen und
  den Rang begründen. Die Allowlist ist der einzige Schutz davor, dass eine
  Werbeseite zum „Beleg“ wird.
