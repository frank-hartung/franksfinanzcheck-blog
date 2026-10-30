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
| Takt | 2 Läufe/Woche × 3 = 0,86/Tag | 1 Lauf/Tag × 3 (elastisch bis 10) |
| Deckung | **33 %** | 155 % beim aktuellen Empfehlungsbudget 4 |
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
Rechnung mit. Governance **C45** prüft statisch, dass
`max_artikel_pro_lauf` (Sockel) × Läufe/Tag den Bedarf mit
`min_deckung_prozent` (110 %) deckt. Das harte Limit ist nur die Spitze und
zählt nicht als Plan. Reicht die Kapazität nicht, wird der **Bau** rot, bevor
der Bestand rot wird.

```bash
python3 scripts/faktenfrische_kapazitaet.py            # Bedarf, Angebot, Abbauplan
python3 scripts/faktenfrische_kapazitaet.py --wache    # Exit 1, wenn nicht abbaubar
python3 scripts/faktenfrische_kapazitaet.py --json     # maschinenlesbar
```

### Nachzug 30.10.2026: Kalender statt Wochenmittel (#912)

Ein Wochendurchschnitt kann keine tägliche Frist beweisen. Die Simulation läuft
daher über **120 echte Kalendertage**, arbeitet nur an cron-Tagen und darf
ein Tagesbudget nicht ansparen. Auswahl und Simulation verwenden denselben
EDF-Schlüssel. Nach jeder Prüfung entsteht aus dem tatsächlichen Prüftag die
nächste Frist; auch diese Folgetermine werden geprüft. Verspätung wird vor
der Arbeit des Tages gemessen, nicht erst danach weggeschrieben.

Die Wache und der Scorecard-Bericht prüfen bei `auto_skalierung: true` das
**empfohlene Budget**, das der Lauf auch verwendet. Der Sockel 3 bleibt als
statische Untergrenze sichtbar; aktuell ergibt die Kalendersimulation 4.
Das ist ein Plan, kein Nachweis erfolgreich ausgeführter CI-Läufe. Ausfälle
und nicht bestandene Prüfungen bleiben eigene, sichtbare Befunde.

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
Alt-Befunde aus `laeufe[].befunde` werden beim Lesen migriert. Fehlt dabei die
frühere Fassungsbindung, bleiben sie als `legacy-unbekannt` offen, bis eine
Neuprüfung eine echte Fassung zuordnet und die Redaktion entscheidet.

Die Fachprüfung erhält den **vollständigen Text** und die mitgeprüften
Aussageflächen im Frontmatter. Sie muss deren SHA-256 zurückgeben; eine
Antwort zu einer anderen Fassung wird verworfen. Der Hash umfasst Titel,
Beschreibung, Kurzantwort, Quellen und Text, nicht technische Datumsfelder.
Bei offenen Befunden wird keine neue Quellenkette neben den unentschiedenen
Text geschrieben.

### Befund redaktionell schließen

1. Text und Belege prüfen, Mängel korrigieren oder den Befund fachlich begründet
   zurückweisen. Keine automatische Textumschrift und keine Schein-Freigabe.
2. Die endgültige Fassung hashen:

   ```bash
   python3 scripts/faktenfrische_befund_ledger.py \
     --fassung content/posts/<slug>/index.md
   python3 scripts/faktenfrische_befund_ledger.py   # offene Befund-IDs
   ```

3. Einen Eintrag in `data/faktenfrische_entscheidungen.yaml` ergänzen:
   `slug`, `befund_id`, `fassung_sha256`, `entschieden_von`, `begruendung`.
   Die Entscheidung gilt nur für genau diese Fassung. Ungültige Signaturen,
   Duplikate und beschädigte Register sind Werkzeugfehler, niemals Grün.
4. Publish-Gate/Scorecard erneut messen. Erst wenn auch alle anderen Checks
   grün sind, darf der zugehörige Vorgang über den PR-Schließpfad enden.

Ein neues Prüfdatum allein schließt F4 nicht. Ebenso darf ein Mensch die
Entscheidung nicht stellvertretend durch eine Maschine erfinden lassen.

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
python3 scripts/faktenfrische.py --selftest      # 23 eingefrorene Fälle
npm run test:faktenfrische                       # Selbsttests + Offline-Regressionen
npm run faktenfrische                            # = Trockenlauf
```

Exit-Codes: `0` gelaufen · `1` offene Befunde (nur `--strict`) ·
`2` Selbsttest/Konfiguration rot · `3` keine Quelle erreichbar (CI warnt).

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
