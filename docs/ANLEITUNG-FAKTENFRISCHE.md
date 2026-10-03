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
| **Bestand** | Fälligkeit nach Risikoklasse | `faktenfrische.py --apply` | `faktenfrische.yml`, Di + Do 06:40 MESZ |

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

Priorität 0 hat immer die **Erstrecherche**. Danach zählt das Alter der letzten
Prüfung. Pro Lauf werden `budget.max_artikel_pro_lauf` Artikel bearbeitet
(Default 3) – Rotation statt Rundumschlag, damit kein Lauf die Feeds
überrennt und jeder Commit überschaubar bleibt.

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
python3 scripts/faktenfrische.py --selftest      # 20 eingefrorene Fälle
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
