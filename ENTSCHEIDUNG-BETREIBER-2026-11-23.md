# Betreiber-Entscheidungen – 23.11.2026

**Vorgang:** #1324 (F4-Vorlage ohne Prüfsummen) hat zwei Entscheidungen berührt, die
nicht in ein PR-Protokoll gehören, sondern dem Inhaber. Dieses Dokument fällt sie –
begründet, gemessen, mit Rücknahmeweg – so, wie eine Agentur sie einem Betreiber
vorlegt: **eine Empfehlung, kein Menü.**

**Stand:** `main` = `35c7f36` (23.11.2026, 03:03). Beide Maßnahmen sind dort bereits
technisch umgesetzt. Dieses Dokument entscheidet, ob sie **bleiben**.

---

## Entscheidung 1 – Prüf-Budget bleibt bei 21

**Entscheidung:** `budget.hartes_limit_pro_lauf` bleibt **21**.
(`data/agent_reach/faktenfrische.yaml`, gesetzt am 22.11.2026, vorher 19.)

### Was der Wert tut – und was nicht

Der Wert ist eine **Obergrenze für den Ausnahmefall**, kein Tagespensum. Der Lauf
wählt immer das **kleinste** Budget, das die Fristen hält (Sockel `max_artikel_pro_lauf: 10`).

| Lage | Seiten überfällig | Nötiges Budget | Wirkung des Limits |
|---|---|---|---|
| heute, 23.11.2026 | **0** | **10** (Sockel) | greift nicht |
| Stresstest, Vollrückstand | 139 | **19** | bei 19: **0** Reserveplätze, bei 21: **2** |

Gemessen mit `faktenfrische_kapazitaet.empfohlenes_budget` über 145 Artikel,
Nachholfrist 7 Tage, Mindestdeckung 110 %, Horizont 120 Tage.

### Warum 21 und nicht 19

Die Regel vom 10.11.2026 lautet: **gemessener Bedarf plus zwei Plätze Reserve**. Bei
19 Prüfungen Bedarf und Limit 19 bleibt kein einziger Platz – genau das meldet die
Deckungs-Wache (`test_vollrueckstand_nach_97_tagen_behaelt_reserve`, rot am 22.11.).
Ein Limit exakt auf Bedarf heißt: Der erste unerwartete Tag (Krankheit, Ausfall eines
Prüfers, ein Artikel mehr) reißt die Nachholfrist. Die zwei Plätze sind die
Versicherung, nicht der Luxus.

### Kosten – ehrlich beziffert

- Im Normalbetrieb: **0**. Das Limit greift nur im Rückstand.
- Im Rückstand: höchstens **+2 Artikel pro Lauf** gegenüber 19 (≈ +10 %), je Artikel
  `max_treffer_je_artikel: 6` und `web_max_zeichen: 1800` – also Rechenzeit und
  Prüfaufwand, **keine** Qualitätsminderung, keine Veröffentlichung ohne Gate.
- Kein Artikel wird dadurch schneller oder langsamer veröffentlicht; das Budget
  steuert nur, wie viele **Nachprüfungen** ein Lauf schafft.

### Rücknahme (falls du anders entscheidest)

```yaml
# data/agent_reach/faktenfrische.yaml
hartes_limit_pro_lauf: 19
```

Folge: `python3 -m unittest scripts.tests.test_faktenfrische_kapazitaet` wird rot
(Vollrückstand ohne Reserveplatz) – dann blockiert dieser Test wieder jeden PR, bis
entweder der Bestand wächst oder das Limit angehoben wird. Die Rücknahme ist also
möglich, aber sie kostet die CI-Fähigkeit. **Deshalb: nicht zurücknehmen.**

### Wann dieses Limit neu entschieden werden muss

Nicht nach Gefühl, sondern nach Messung. **Auslöser:** sobald im Stresstest
`Bedarf > Limit − 2` gilt (also heute: Bedarf > 19).

```bash
.venv/bin/python - <<'PY'
import sys, datetime as dt, copy; sys.path.insert(0,'scripts')
import faktenfrische_kapazitaet as kap, faktenfrische as ff, yaml
cfg = yaml.safe_load(open('data/agent_reach/faktenfrische.yaml'))
c = copy.deepcopy(cfg); c['budget']['hartes_limit_pro_lauf'] = 60   # Deckel wegnehmen
emp = kap.empfohlenes_budget(ff.alle_artikel("alle"), c, laeufe=1,
                             stichtag=dt.date(2027, 2, 22))
print('Bedarf', emp['budget'], '| überfällig', emp['plan']['ueberfaellig'],
      '| Abbau', emp['plan']['abbau_tage'], 'Tage')
PY
```

Dann gilt dieselbe Regel: **neues Limit = Bedarf + 2**, im YAML mit Datum und Messwert
kommentiert (so wie am 22.11. geschehen).

---

## Entscheidung 2 – Die Löschung des WLAN-Doppelentwurfs bleibt

**Entscheidung:** Der Entwurf
`2026-11-22-wlan-verbessern-lohnt-sich-mesh-oder-reicht-ein-repeater` bleibt gelöscht.
Er war **nie veröffentlicht** (keine URL, keine internen Links – der Janitor hat
0 Links und 0 `llms.txt`-Zeilen entfernen müssen).

### Warum das kein Verlust ist

Es waren drei Texte mit **derselben Suchabsicht** – „Mesh oder Repeater?":

| Artikel | Titel | Status |
|---|---|---|
| 09.11.2026 | „WLAN verbessern: Mesh-System oder Repeater im Check?" | Entwurf, **blockiert** (kein `quellen:`-Block, Kadenz-Demotion) |
| 13.11.2026 | „Mesh-WLAN nachrüsten: Wann lohnt sich die Investition?" | **live** |
| 22.11.2026 | „WLAN verbessern: Lohnt sich Mesh oder reicht ein Repeater?" | Entwurf, **gelöscht** |

Der Entwurf doppelte nicht nur das Thema, sondern **den Einstieg** des blockierten
09.11.-Entwurfs („Teste die Funkverbindung dort, wo ein Repeater stehen würde" gegen
„Miss die WLAN-Verbindung in den betroffenen Räumen") – und lag damit quer zu einem
Thema, das **schon zwei Live-Artikel** besetzen (27.09. „Verstärker vs. Mesh",
13.11. „Mesh-WLAN nachrüsten"). Ein dritter, vierter Text auf dieselbe Frage
kannibalisiert die bestehenden – der teuerste Fehler im Content-SEO, weil sich die
Seiten die Autorität teilen. Der Entwurf war zudem der **zweite blockierte** Text auf
genau diese Frage; einer davon musste weg, und der Janitor hat den richtigen genommen
(der verbliebene 09.11.-Entwurf ist kadenz-gedemotet und wird redaktionell behandelt).

### Warum ich ihn nicht „gerettet" habe

Der Blocker war das Quellen-Gate: kein `quellen:`-Block. Ihn zu füllen hätte
bedeutet, Belege für Aussagen zu erfinden, die kein Mensch geprüft hat. Genau das ist
im YMYL-Umfeld der eine Fehler, den man nicht macht. **Löschen war billiger als
lügen.** Der Themenplatz ist durch die bestehenden Live-Artikel besetzt; die
Suchintention ist bedient.

### Rücknahme (falls du anders entscheidest)

Der letzte Stand vor der Löschung liegt in `e5bcd4a3`:

```bash
git checkout e5bcd4a3 -- \
  "content/posts/2026-11-22-wlan-verbessern-lohnt-sich-mesh-oder-reicht-ein-repeater"
python3 scripts/generate_covers.py        # Cover in allen Varianten neu rendern
```

Danach bleibt der Entwurf **blockiert** (`draft: true`, `reserve_blocked: Quellen-Gate`)
und der Janitor greift ihn beim nächsten Lauf wieder auf – es sei denn, jemand
schreibt den Quellenblock mit echten Belegen. Rücknahme ist also möglich, aber
sinnlos ohne Quellenarbeit.

### Die eigentliche Folgearbeit (Empfehlung, nicht erledigt)

Die WLAN-Gruppe ist **unaufgeräumt**: Es gibt **vier Live-Artikel** zum Thema
WLAN/Mesh, aber `data/kannibalisierung_map.yaml` führt nur **2** davon (Rollen
„WLAN-Empfang" und „Gerätewahl"). Die beiden neueren (10.11. Router-Standort,
13.11. Mesh nachrüsten) stehen in keiner Rolle, dazu ein blockierter Entwurf
(09.11.). Solange das so ist, produziert die Content-Engine weiter Texte in eine
überfüllte Nische – der gelöschte Entwurf ist ein Symptom, nicht die Ursache.

**Empfehlung, Priorität mittel, Aufwand ~1–2 h Redaktion:**

1. In `data/kannibalisierung_map.yaml` im Cluster `internet-dsl` die zwei fehlenden
   Live-Artikel mit **eigener Rolle** eintragen („Router-Standort" für 10.11.,
   „Mesh nachrüsten" für 13.11.).
2. Den verbliebenen 09.11.-Entwurf entscheiden: echte Quellen und Freigabe – oder
   löschen. Beides ist besser als „liegt blockiert herum" (er ist der Zwilling des
   gelöschten Textes).
3. Prüfen, ob 13.11. und der 27.09. nach Zusammenführung verlangen
   (`python3 scripts/check_uniqueness.py` zeigt die Paare; Regel A in
   `data/weiterleitungen.yaml` für die Zusammenführung).
4. Erst danach neue WLAN-Themen zulassen – sonst entsteht der nächste Doppelentwurf.

---

## Was du als Betreiber jetzt tun musst

1. **Nichts** – wenn du dieser Entscheidung folgst. Beide Maßnahmen sind umgesetzt
   und ausgeliefert (`main` = `35c7f36`, Deploy mit Auslieferungs-Siegel grün am
   22.11.). Dieses Dokument ist die Bestätigung, nicht die Voraussetzung.
2. **Rücknahme** nur mit den oben genannten Befehlen – und dann bitte bewusst, weil
   beide Rücknahmen einen Preis haben (roter Guard-Test bzw. Quellenarbeit).
3. **Folgearbeit freigeben** (WLAN-Cluster kuratieren), wenn du willst, dass die
   Ursache und nicht nur das Symptom verschwindet.

## Grenze dieser Entscheidung

Beide Entscheidungen sind **rücknehmbar und dokumentiert**, beide sind gemessen, nicht
geschätzt. Was sie nicht leisten: Sie machen aus einem überfüllten Thema ein gutes.
Das bleibt Redaktion – und ist der nächste sinnvolle Schritt.

*Erstellt am 23.11.2026 im Auftrag von Frank Hartung; Zahlen aus dem Stand
`main` = `35c7f36`, gemessen mit den Werkzeugen des Repos
(`faktenfrische_kapazitaet`, `reserve_janitor`, `check_uniqueness`).*
