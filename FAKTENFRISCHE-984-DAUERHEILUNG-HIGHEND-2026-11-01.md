# Faktenfrische #984 – ein Schreibvorgang darf den Lauf nicht töten

Stand: 1. November 2026. Auftrag: „Bitte dauerhaft auf Highend-Level einer
Profi-Agentur beheben.“ Lokale Umsetzung auf dem Arbeitsbranch
`arena/7dfeec20-franksfinanzcheck-blog`, Freigabe über Pull Request.
Der Vorgang **schließt sich nicht über „Closes #984“**, sondern über den
ersten grünen Lauf von „Faktenfrische (Bestand)“ auf `main` – das ist der
Schließpfad, den `alert_resolve_gate.py` verlangt (Job `recherche` grün).
Ein Merge ist kein Beweis; ein grüner Lauf ist einer.

## Ausgangslage

Der Alarm vom 31.10.2026, 11:33 Uhr (Run
[41193270170](https://github.com/frank-hartung/franksfinanzcheck-blog/actions/runs/41193270170))
meldete:

> **Faktenfrische (Bestand) ist fehlgeschlagen**
> Fehlgeschlagene Schritte: Job „recherche“ – „Unvollständige Recherche melden“

Mehr stand nicht darin. Der letzte Schritt ist immer rot, wenn der
Recherche-Schritt rot war – er ist die Meldung, nicht die Ursache. Das echte
Job-Log liegt auf einem fremden Blob-Host und war zum Zeitpunkt der
Untersuchung nicht abrufbar (EOF beim Download). Die Ursache musste also aus
dem gebliebenen Zustand rekonstruiert werden. Sie ließ sich vollständig
beweisen – und sie war ein Programmierfehler, kein Leitungsproblem.

## Beweisführung ohne Log

| Beobachtung | Beleg |
|---|---|
| Der Job lief nur **28 Sekunden** (Schritt „Recherche + Fachprüfung“: 10 s). Ein gesunder Lauf braucht 95–105 s. | `actions/runs/41193270170/jobs` (Schrittzeiten) |
| Der Lauf hat **genau eine Seite** verarbeitet und committet: `2026-10-30-kostenloses-girokonto-ohne-gebuehren-finden`. | Commit `366582d9` „content(fakten): Belegkette aufgefrischt“ – eine `index.md` (+1), ein Dossier `.md` und `.json` |
| Queue, Historie und Report wurden **nicht** geschrieben. Beide stehen unverändert auf dem Stand des letzten guten Laufs (30.10.2026, 11:01 UTC). | `data/faktenfrische_queue.json`, `data/faktenfrische_history.jsonl` im Baum von `2bde46ef` = Stand 30.10. |
| Das Dossier der Seite belegt eine **vollständige** Fachprüfung: 1 Fundstelle, `geprüft (groq:openai/gpt-oss-120b)`, **5 Befunde**, gültiger `fassung_sha256`. | `data/research/artikel/2026-10-30-…-girokonto….json` |
| Die Seite bekam `faktencheck: 2026-10-31` – der Schreibvorgang war also erfolgreich. | Commit `366582d9`, `index.md` |
| Der Lauf brach **nach** diesem Schreibvorgang ab (keine zweite Seite, keine Bilanz). | Commit-Inhalt + fehlende Laufartefakte |

Der Zustand ist also eindeutig: **Schreiben erfolgreich, Bilanz tödlich.**
Damit blieb nur ein Fenster im Code – der Block, der seit dem 30.10.2026
(PR #968, Commit `0d3f6312`, 12:29 UTC) nach dem Schreiben die Fassung neu
liest:

```python
        if any(a.startswith("quellen:") or a.startswith("faktencheck:") for a in aenderungen):
            aktuelle_fassung = lade_artikel(art["pfad"])   # nur Datei-Wissen
            if aktuelle_fassung is None:
                return 2
            art = aktuelle_fassung                         # ← Buchhaltung weg
        laeufe.append({
            ...
            "grund": art["_faellig"]["grund"],             # ← KeyError
            "geo": art["_geo"]["prozent"],
```

`lade_artikel()` liefert ausschließlich, was in der Datei steht. `_faellig`,
`_geo` und `bereich` existieren nur im Lauf. Wer die frisch gelesene Fassung
an die Stelle von `art` setzt, verliert sie. Der Lauf starb mit
`KeyError: '_faellig'` – **vor** `report_schreiben()` und **vor** dem
atomaren Queue-Schreiben, also ohne jede Spur außer einem Traceback im Log.

Bestätigt ist der Auslöser durch die Zeitachse: Der letzte grüne Lauf
(30.10., 11:01 UTC) lief mit dem Code **vor** #968. Der erste Lauf mit dem
neuen Code war der rote vom 31.10. Die Reproduktion des Fehlers mit
Attrappen (kein Netz, keine Schlüssel) liefert exakt dieselbe Zeile:

```
File "scripts/faktenfrische.py", line 1461, in main
    "grund": art["_faellig"]["grund"],
KeyError: '_faellig'
QUEUE EXISTS False
```

Die Reproduktion liegt als Regression bei
(`test_schreiben_dann_neu_lesen_beendet_den_lauf_nicht`) und ist nach der
Heilung grün.

## Warum der Alarm nichts davon sagte

Zwei getrennte Mängel, beide behoben:

1. **Der Lauf kannte keinen Zwischenzustand.** Eine Ausnahme in der Schleife
   riss Queue, Report, Historie **und** Ledger mit. Übrig blieben Dossiers –
   Beweise ohne Leser.
2. **Die Meldung nannte nur den letzten Schritt.** Wer das Ticket liest, ohne
   fremde Blob-Logs laden zu können, konnte die Ursache nicht erfahren. Das
   Protokoll wurde nicht gesichert.

## Heilung (drei Schichten, keine davon „nochmal starten“)

### 1. Die Ursache: Datei-Wissen und Lauf-Wissen sind getrennt

- Neue, benannte Grenze: `fassung_nach_schreiben(art)` liest die
  hinterlassene Fassung und gibt sie **getrennt** zurück (`fassung`), statt
  `art` zu ersetzen. Die Lauf-Buchhaltung bleibt, wo sie hingehört.
- Neue, benannte Bilanz: `lauf_eintrag(art, fassung, …)` zieht Inhalt
  (`slug`, `titel`, Fassungs-Hash) aus der Fassung und Buchhaltung
  (`_faellig`, `_geo`, `bereich`) aus dem Lauf.
- Nicht lesbar heißt jetzt `ArtikelAbbruch` mit Pfad – kein stiller
  Ersatzwert, kein `return 2` mitten im Lauf.

### 2. Die Klasse: eine Seite ist eine Einheit, der Lauf überlebt sie

- Die Seitenbearbeitung ist als `verarbeite_seite()` gekapselt und gibt
  `(Lauf-Eintrag, bleibt_offen)` zurück.
- `main()` fängt jede Ausnahme einer Seite, schreibt den vollen Traceback
  ins Protokoll, führt die Seite unter **„Abgebrochene Seiten“** in Report
  und Queue und arbeitet weiter.
- Der Lauf endet dann mit **Exit 5** (neu dokumentiert). Kein stiller
  Teilerfolg: Die Beweise sind gesichert, der Ausfall bleibt rot.
- Die Klasse „keine Quelle erreichbar“ (Exit 3) gilt nur noch, wenn
  **alle** ausgewählten Seiten tatsächlich gelaufen sind. Vorher hätte
  `all()` über eine leere Liste die Klasse „Netz tot“ erfunden.

### 3. Die Meldung: Ursache statt Raten

- Der Workflow schreibt das Laufprotokoll nach `faktenfrische-lauf.log`
  (Artefakt + Step-Summary). `set -o pipefail` + `PIPESTATUS`-Muster halten
  den echten Exit-Code, obwohl der Schritt `continue-on-error` bleibt.
- Der rote Abschlussschritt übersetzt den Exit-Code in Klartext (2/3/4/5),
  zeigt die letzten 40 Logzeilen in der Step-Summary und schreibt dieselbe
  Einordnung als `::error::`. Das nächste Ticket dieser Klasse ist ohne
  Blob-Zugriff diagnostizierbar.
- Ausdrücke laufen über `env:` (kein `${{ }}` in `run:`) – die
  Template-Injection-Regel aus dem Tiefencheck #973 bleibt eingehalten.

### 4. Das Sicherheitsnetz: Nachlese

Ein Dossier entsteht **vor** der Bilanz. Bricht der Lauf danach ab, waren
die Befunde dieser Seite bis jetzt nur dort – unsichtbar für Redaktion,
Publish-Gate (F4) und Scorecard, während die Maschine „nichts gefunden“
meldete. Neu in `scripts/faktenfrische_befund_ledger.py`:

```bash
python3 scripts/faktenfrische_befund_ledger.py --nachlese           # Trockenlauf
python3 scripts/faktenfrische_befund_ledger.py --nachlese --apply   # ergänzen
```

- liest `data/research/artikel/*.json`, ergänzt nur fehlende Einträge,
- übernimmt nichts ohne echten 64-stelligen Fassungs-Hash (eine Entscheidung
  muss bindbar bleiben) und nennt Übersprungenes ausdrücklich,
- schließt **nie** einen Befund und ist idempotent,
- läuft im Workflow nach jedem Lauf (`if: always()`), sodass auch ein
  Abbruch seine Befunde ins Ledger bringt.

## Datenheilung: fünf Befunde waren verloren

Die Nachlese hat den Schaden des roten Laufs repariert:

| Seite | Befunde | Vorher im Ledger | Jetzt |
|---|---|---|---|
| Kostenloses Girokonto ohne Gebühren finden (Entwurf, `draft: true`) | 5 (`luecke`) | **0** – nur im Dossier | 5, offen zur redaktionellen Entscheidung |

`data/faktenfrische_queue.json` enthält jetzt `fachbefunde` mit **25** offenen
Einträgen: 20 aus dem Lauf vom 30.10.2026 (bereits offen über #964), 5
wiedergefunden. Die Altbestände aus `laeufe[].befunde` werden dabei – wie in
#912 vorgesehen – einmalig migriert; Seiten ohne echten Fassungs-Hash werden
nicht übernommen (sonst wäre keine Entscheidung bindbar) und im Ergebnis
ausgewiesen.

**Was das bedeutet:** F4 (offener Fachbefund) blockiert die betroffenen
Seiten bis zu einer dokumentierten menschlichen Entscheidung – das ist der
Vertrag aus #912, kein neuer Fehler. Die betroffene Girokonto-Seite ist ein
Entwurf und damit ohnehin nicht veröffentlicht. Es wurde **kein** Text
geändert und **kein** Befund geschlossen.

## Was ausdrücklich nicht angefasst wurde

- Intervalle, Fälligkeitsregel, Vorlauf, Budget und Cron: unverändert. Die
  Kadenz war nie das Problem (#912 ist davon getrennt).
- Allowlist, Kanalmatrix, KI-Routing und das Anti-Halluzinations-Gate:
  unverändert.
- Kein Artikeltext, kein `lastmod`, kein Prüfsiegel. Die Seite behält ihren
  wahrheitsgemäßen Stempel `faktencheck: 2026-10-31` – die Fachprüfung hat
  stattgefunden, nur ihre Bilanz fehlte.
- Keine kostenpflichtige Quelle, keine Browser-Brücke.

## Tests und Nachweise

| Prüfung | Ergebnis |
|---|---|
| `python3 scripts/faktenfrische.py --selftest` | 29/29 grün (neu: ST8 – Neuladen verliert die Buchhaltung nicht, Abbruch statt stiller Ersatzwert) |
| `python3 scripts/faktenfrische_befund_ledger.py --selftest` | grün (neu: Nachlese findet, ergänzt, ist idempotent, erfindet keine Fassung, schließt nichts) |
| `python3 -m unittest scripts.tests.test_faktenfrische_robustheit` | 16 Tests grün, davon 3 neue Regressionen zu #984 |
| `python3 -m unittest scripts.tests.test_faktenfrische_befund_ledger` | 16 Tests grün, davon 2 neue Nachlese-Regressionen |
| `npm run test:faktenfrische` | 65 Tests grün |
| `python3 scripts/selftest_runner.py --ohne-uhr-probe` | 258 Wachen, 0 Befunde zu dieser Änderung (einziger roter Punkt: `cover_render_check.py` ohne installiertes `pillow` – Umgebung, nicht dieser Vorgang) |
| `python3 -m unittest scripts.tests.test_unabhaengiger_tiefencheck` | grün (keine `${{ }}`-Interpolation in `run:`) |
| Workflow-YAML | parsebar; alle `run:`-Blöcke `bash -n`-sauber; Exit-Code→Klartext für 2/3/4/5/0/leer durchgespielt |

## Grenzen (ehrlich)

- Die Nachlese kann nur Seiten heilen, deren Dossier einen echten
  Fassungs-Hash trägt. Dossiers aus der Zeit vor #968 haben keinen; ihre
  Befunde stehen weiterhin über die Lauf-Migration in der Queue bzw. sind
  über #911/#964 entschieden. Sie werden **nicht** neu geöffnet.
- Ein Abbruch lässt die Seite in der Queue: Sie wird morgen erneut versucht.
  Das ist gewollt (kein stiller Datenverlust), kostet aber einen Slot, bis
  die Ursache behoben ist – der Report nennt sie beim Namen.
- Diese Heilung verhindert Programmierfehler in der Schleife; sie ersetzt
  nicht die Prüfung der Außenkanäle (Feeds, Schlüssel). Genau dafür nennt
  die Meldung künftig die Klasse, statt sie zu verschweigen.

## Abschluss

1. Review und Merge dieses Vorschlags auf `main`.
2. Der nächste Lauf von „Faktenfrische (Bestand)“ (täglich 04:40 UTC oder
   manuell) beweist die Heilung: **Exit 0**, Queue/Report/Ledger geschrieben,
   Nachlese ohne Ergänzung.
3. Dieses Ticket schließt sich damit selbst (`alert_resolve_gate.py`, Job
   `recherche`). Ein roter Lauf hält es offen und nennt ab jetzt die Ursache
   im Klartext.
4. Die fünf wiedergefundenen Befunde gehören in die redaktionelle
   Entscheidung (#964). Sie sind belegt, nicht behauptet – und sie
   verschwinden nicht mehr.
