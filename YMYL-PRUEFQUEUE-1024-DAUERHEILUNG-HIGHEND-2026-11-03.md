# Redaktionelle YMYL-Prüfqueue #1024 – Dauerheilung auf Agenturniveau

**Stand:** 2026-11-03 · **Zweig:** `arena/efd336eb-franksfinanzcheck-blog` · **Basis:** `b29c009`
**Ticket:** [#1024](https://github.com/frank-hartung/franksfinanzcheck-blog/issues/1024), offen seit 02.11.2026, 13:35 UTC
**Betroffene Prüfung:** `scripts/belegketten_wache.py` · `.github/workflows/redaktionelle-ymyl-pruefung.yml`

> **Kurzfassung:** Die Queue war redaktionell vollständig grün (10/10 Freigaben,
> 0 offene Reviews). Sie blieb ausschließlich wegen **fünf** Gesetzeszitaten
> offen, die auf GitHub-Runnern systematisch `unklar` wurden. Der am 30.10.2026
> eingebaute Ersatzweg über den Bundesrechts-Spiegel hat **seit seiner Einführung
> nie funktioniert**: Ein Adapter entpackte das 3-Tupel des gesicherten
> Transports als 2-Tupel und der daraus entstehende `ValueError` wurde still als
> „unklar“ geschluckt. Die Logiktests waren grün, weil sie genau diesen Adapter
> durch ein 2-Tupel-Attrappe ersetzten. Der Transport ist repariert, der Vertrag
> ist jetzt im Selbsttest, in 8 neuen Regressionstests, im CI-Schritt und im
> Bericht verankert. **Keine** fachliche Freigabe wurde neu erfunden, **kein**
> Gate abgeschwächt, **kein** Ticket von Hand geschlossen.

---

## 1. Ausgangslage: Was das Ticket wirklich meldet

Der Workflow-Lauf [41454120377](https://github.com/frank-hartung/franksfinanzcheck-blog/actions/runs/41454120377)
(02.11.2026, 13:34 UTC, `head 519a882`) schrieb den Ticketkörper:

| Ebene | Befund |
|---|---|
| `editorial_review_gate.py` | 10 Hochrisiko-Artikel, 10 freigegeben, `open_live = 0`, `open_drafts = 0` |
| `belegketten_wache.py` | 34 geprüfte Quellen, 29 `ok`, 0 `umgeleitet`, 0 `tot`, **5 `unklar`** |
| Betroffene Zitate | `vvg_2008/__40.html` (2×), `vvg_2008/__96.html`, `bgb/__502.html`, `got_2022/` |
| Folge | `--strict --require-complete` → Exit 1 → `steps.wache.outcome = failure` → Ticket bleibt offen |

Der Workflow ist bewusst fail-closed gebaut: `unklar` ist kein Freispruch und
hält das Ticket offen, bis die Abrufkette geklärt ist. Das ist richtig. Falsch
war die Annahme, der Ersatzweg aus Prüfqueue #826 (30.10.2026) würde diese
fünf Fälle klären.

---

## 2. Ursachenanalyse: Ein Vertragsbruch im Transport, nicht in der Logik

`scripts/net_safety.py` stellt zwei gesicherte Abrufwege bereit:

| Funktion | Rückgabe | Nutzung in der Wache |
|---|---|---|
| `sicherer_abruf_status()` | **2** Werte: `(status, end_url)` | `abruf_http()` – Direktabruf |
| `sicherer_abruf()` | **3** Werte: `(status, antwort_kopf, bytes)` | `abruf_gii_spiegel_http()` – Spiegel |

Sieben weitere Aufrufstellen im Repo (`agent_reach_research.py`,
`faktenfrische.py`, `schaltwerk_triggers.py`, `werkbank_adapters.py`) entpacken
korrekt drei Werte. Einzige Ausnahme war `belegketten_wache.py`:

```python
# Stand vor dem 03.11.2026
status, nutzlast = sicherer_abruf(...)   # ValueError: too many values to unpack
```

`_pruefe_gii_spiegel()` fing **alle** Ausnahmen und gab den ursprünglichen
`unklar`-Befund zurück – ohne Grund, ohne Spur im Bericht. Damit war der
gesamte Ersatzweg ein blindes Kabel:

1. Direktabruf von `www.gesetze-im-internet.de` scheitert auf dem Runner
   (`URLError` nach Timeout).
2. Der Spiegelabruf startet, wirft sofort `ValueError`, wird geschluckt.
3. Die Wache meldet wörtlich `nicht erreichbar (URLError)` – ein Grund, der
   den eigentlichen Fehler verdeckt.
4. `--require-complete` liefert Exit 1, das Ticket bleibt offen. Am nächsten
   Werktag dasselbe.

**Warum niemand es merkte:** `scripts/tests/test_belegketten_wache.py`
injizierte `spiegel_abruf` als 2-Tupel-Attrappe. Damit wurde die Normlogik
(Herkunftsprüfung, §-Schärfe, Wegfall, 404) korrekt geprüft – aber nie die
Verbindung zwischen `net_safety` und der Wache. Ein grüner Selbsttest war
kein Beweis für einen funktionierenden Ersatzweg. Genau diese Lücke hat der
vorliegende Auftrag geschlossen (vgl. D6/D23 in `CLAUDE.md`).

---

## 3. Messung: Vorher / Nachher mit den echten Spiegeldateien

Um den Produktionspfad zu messen, ohne die gesperrten Hosts zu berühren,
wurde eine **Offline-Simulation** gebaut: Der Direktabruf aller GII-Adressen
wirft wie auf dem Runner `URLError`, alle übrigen 29 Quellen antworten `200`.
Die drei realen Spiegeldateien wurden über `api.github.com` geladen (für
`bgb.md` über die Git-Blob-API, da die Contents-API ab 1 MiB keinen Inhalt
liefert) und als echtes 3-Tupel in `net_safety.sicherer_abruf` gespeist.
Es lief also der **echte** `abruf_gii_spiegel_http`, keine Attrappe.

| | Vorher | Nachher |
|---|---|---|
| Geprüfte Quellen | 34 | 34 |
| `ok` | 29 | **34** |
| `unklar` | **5** | **0** |
| `tot` / `umgeleitet` | 0 / 0 | 0 / 0 |
| Davon über Spiegel bestätigt | 0 | **5** |
| `--strict --require-complete` | **Exit 1** | **Exit 0** |

Die fünf Zitate gegen den realen Normbestand (Stand 03.11.2026):

| Zitat | Spiegeldatei | Größe | Gefundene aktive Überschrift |
|---|---|---:|---|
| `vvg_2008/__40.html` | `vv/vvg_2008.md` | 246.373 B | `##### § 40 Kündigung bei Prämienerhöhung` |
| `vvg_2008/__96.html` | `vv/vvg_2008.md` | 246.373 B | `##### § 96 Kündigung nach Veräußerung` |
| `bgb/__502.html` | `bg/bgb.md` | 1.761.876 B | `###### § 502 Vorfälligkeitsentschädigung` |
| `got_2022/` (Gesamtwerk) | `go/got_2022.md` | 93.568 B | `## § 2 …`, `## § 4 …` |

Alle drei Dateien weisen im YAML-Kopf exakt
`quelle: https://www.gesetze-im-internet.de/<slug>/` aus. Auch die übrigen im
Bestand zitierten Slugs (`estg`, `tkg_2021`, `ustg_1980`) liegen unter dem
8-MiB-Limit des Adapters; ein falsches `unklar` durch das Größenlimit ist
damit im gesamten Bestand ausgeschlossen.

**Grenze des Nachweises:** In dieser Umgebung sind sowohl
`www.gesetze-im-internet.de` als auch `raw.githubusercontent.com` netzseitig
gesperrt. Die Messung belegt den **Codepfad** und den **Inhalt** der
Spiegeldateien, nicht die Netzstrecke eines GitHub-Runners. Der reale
Wachenlauf nach der Übernahme bleibt das maßgebliche Signal; das Ticket wird
erst dann automatisch geschlossen.

---

## 4. Durchgeführte Dauerlösung

### 4.1 Transport reparieren und vertraglich absichern
- `abruf_gii_spiegel_http()` entpackt `(status, _koepfe, nutzlast)` und
  dokumentiert den Unterschied zu `sicherer_abruf_status()` im Docstring und
  im Modulkopf.
- `selftest()` prüft jetzt **zusätzlich den echten Adapter** gegen ein
  3-Tupel, verlangt `pruefpfad` und Spiegeldatei im Ergebnis und prüft die
  Gegenprobe: Fällt der Transport aus, muss `unklar` bleiben **und** den Grund
  nennen. Der Selbsttest ist fail-closed, läuft offline und berührt kein Netz.
- `scripts/tests/test_belegketten_wache.py`: 8 neue Fälle (15 → 23), u. a.
  eine Gegenprobe gegen `net_safety.sicherer_abruf` selbst (3 Werte), der
  echte Adapter gegen VVG- und BGB-Überschriftenebenen, direktes 404 darf
  nicht überstimmt werden, Spiegeloffline bleibt begründet `unklar`, der
  vollständige Produktionsweg ohne Injektion ist grün.

### 4.2 Ehrliche Befunde statt stiller Ausnahmen (D23)
- Jeder Ausgang trägt `pruefpfad` (`direkt` / `bundesrechts-spiegel` /
  `unklar`) als maschinenlesbare Wahrheit. `pruefe_alle()` entscheidet die
  Runner-Blockade-Erkennung jetzt über dieses Feld statt über einen
  Hinweistext.
- `_unklar_mit_grund()` und `_spiegel_tot()` liefern sichtbare Gründe und die
  geprüfte Spiegeldatei; ein `tot` aus dem Spiegel verlangt ausdrücklich die
  redaktionelle Verifizierung gegen die Primärquelle, bevor Text geändert wird.
- `spiegel_bestaetigt` ist ein eigenes Ergebnisfeld und erscheint im JSON,
  im Konsolenlauf und im Bericht.

### 4.3 Bericht, der keine Scheinsicherheit erzeugt
Früher hätte ein Lauf mit fünf Ersatzprüfungen „34 unverändert erreichbar“
gemeldet. Der Bericht rechnet jetzt auf:

```
- Geprüfte Quellen: **34**
- Ohne offenen Befund (`ok`): **34**
- Unverändert direkt erreichbar: **29**
- Über Bundesrechts-Spiegel bestätigt: **5**
- Nicht prüfbar (Netz/Timeout): **0**
```

Ein eigener Abschnitt „Ersatzprüfung über den Bundesrechts-Spiegel“ nennt zu
jedem Zitat Artikel, Quellen-ID, zitierte Adresse, Spiegeldatei und Grund –
mit dem ausdrücklichen Hinweis, dass dies **keine Inhaltsprüfung und keine
fachliche Freigabe** ist.

### 4.4 CI und Bedienweg auf dieselbe Wahrheit verpflichten
- `.github/workflows/redaktionelle-ymyl-pruefung.yml`: Der Schritt „Regelwerk
  selbst prüfen" ruft zusätzlich `belegketten_wache.py --selftest` auf; die
  bestehende Test-Suite deckt die neuen Regressionstests ab. Permissions,
  Action-Pins, Job-Reihenfolge und Fail-closed-Logik bleiben unverändert.
- Der automatische Schließvermerk sagt jetzt korrekt „direkt oder, bei
  blockiertem Direktabruf, über den täglichen Bundesrechts-Spiegel bestätigt"
  statt pauschal „erreichbar“.
- `npm run test:redaktion:ymyl` prüft **beide Hälften** der Queue: Gate und
  Wache, inklusive Transportvertrag (41 Tests grün).

### 4.5 Dokumentation und Korrektur der Historie
- `docs/ANLEITUNG-REDAKTIONELLE-YMYL-PRUEFUNG.md` beschreibt den Ersatzweg,
  seine Grenzen, den Transportvertrag und die scharfen Befehle.
- `YMYL-PRUEFQUEUE-826-DAUERHEILUNG-PREMIUM-2026-10-30.md` erhielt einen
  deutlich markierten **Nachtrag**: Die dort in Säule 1 behauptete Wirksamkeit
  der Spiegelprüfung war bis zum 03.11.2026 nicht gegeben. Der historische
  Bericht wurde nicht umgeschrieben.

---

## 5. Verifikation (lokal, 03.11.2026)

| Prüfung | Ergebnis |
|---|---|
| `belegketten_wache.py --selftest` | grün (Zustände, Sprachpfad, Normprüfung, **Transportvertrag**) |
| `editorial_review_gate.py --selftest` | grün |
| `editorial_review_gate.py --all --strict` | 106 Artikel · 10 Hochrisiko · 10 freigegeben · 0 blockiert · Exit 0 |
| `editorial_review_gate.py --published --strict` | 74 Artikel · 2 Hochrisiko · 2 freigegeben · 0 blockiert · Exit 0 |
| `ymyl_siegel_wache.py` | 106 Artikel · 0 Driftbefunde |
| Workflow-Sequenz „Regelwerk selbst prüfen“ (4 Discovery-Läufe) | 18 + 10 + 10 + 23 = **61 Tests**, alle grün |
| Verbundtests YMYL (6 Module) | **96 Tests**, alle grün |
| `npm run test:redaktion:ymyl` | **41 Tests**, grün |
| `skript_syntax_wache.py` | 628 Dateien kompilieren |
| `wachen_vertrag.py` | 372 Skripte, 0 Funde |
| `net_safety.py --selftest` / `url_host.py --selftest` | 21 Fälle / 42 Proben grün |
| `test_unabhaengiger_tiefencheck` | 13 Tests grün (u. a. Workflow-Permissions, keine `${{ }}` in `run:`) |
| `git diff --check` | sauber |
| Offline-Simulation mit echten Spiegelbytes | 34/34/0, 5 Ersatzprüfungen, Exit 0 |

**Sabotageprobe (Beweis, dass die Wache scharf ist):** Der alte 2er-Unpack
wurde kurzzeitig wieder eingesetzt. Ergebnis: Selbsttest **Exit 2** mit drei
benannten Fehlern („Adapter entpackt das 3-Tupel von net_safety
(ValueError …)"), Unit-Tests **4 Fehler + 1 Error**, darunter
`test_produktionsweg_ist_gruen_und_zaehlt_ersatzpruefungen`. Danach wurde die
reparierte Fassung wiederhergestellt und der Selbsttest erneut grün gefahren.
Die neuen Wachen erkennen also genau den Fehler, der #1024 verursacht hat.

---

## 6. Bewusst nicht getan

- **Kein** Artikel, Frontmatter, Siegel, Prüfprotokoll oder `quellen`-Feld
  geändert; keine neue Fachprüfung, kein Prüfer, kein Review-Termin erfunden.
- **Keine** der fünf GII-Adressen ausgetauscht – offizielle Leser-Links
  bleiben die zitierte Wahrheit.
- **Kein** Gate abgeschwächt: `--require-complete` verlangt weiterhin null
  Befunde; `unklar` bleibt ein offener Prüfauftrag; ein direktes 404 wird nie
  durch den Spiegel überstimmt.
- **Kein** Ticket von Hand geschlossen oder nachkommentiert (D2). Die
  Erledigung bleibt dem Workflow mit seinem eigenen Abschlussvermerk
  vorbehalten.
- **Keine** neuen Abhängigkeiten, keine Action-Pins, keine Rechte geändert.

---

## 7. Angrenzender Befund (außerhalb dieses Auftrags, nicht angefasst)

`data/integrity_lock.json` ist im vorliegenden Stand **kein gültiges JSON**
(ab Zeile 289 doppelte Schlüssel und fehlende Kommata – mehrere Fassungen
wurden textuell zusammengesetzt). `skills_vertrag.py` meldet das als
Warnung **K8**: „ein kaputtes Siegel meldet Scheinsicherheit, nie Sicherheit“.
Die Datei ist ein signiertes Maschinenartefakt und in `CLAUDE.md` als
sicherheitsrelevant eingestuft; eine Reparatur verlangt eine bewusste
Neu-Signatur durch den Inhaber
(`python3 scripts/integrity_guard.py --repair-lock --dry-run` als
Voransicht). Sie hat keinen Einfluss auf die YMYL-Queue und wurde daher
weder korrigiert noch neu signiert. Empfehlung: eigenes Ticket mit Owner.

---

## 8. Rollout und Abnahme

1. Pull Request aus `arena/efd336eb-franksfinanzcheck-blog` nach `main`
   übernehmen; der PR-Check **YMYL-Siegelprüfung** und die Syntax-/Wachen-
   Gates müssen grün sein.
2. Auf `main` den Workflow **Redaktionelle YMYL-Prüfung** per
   `workflow_dispatch` starten (nicht auf den nächsten Werktag warten).
3. Im Lauf prüfen: Schritt „Regelwerk selbst prüfen“ grün; Schritt
   „Belegketten der Hochrisiko-Artikel prüfen“ mit
   `34 Quellen · … · 0 unklar · 5 über Spiegel bestätigt`; der Bericht muss
   den Abschnitt „Ersatzprüfung über den Bundesrechts-Spiegel“ mit allen fünf
   Zuordnungen enthalten.
4. Erst wenn `GATE_OPEN = 0` **und** `steps.wache.outcome = success`, schließt
   der Workflow #1024 mit seinem eigenen Vermerk. Bleibt auch nur eine Quelle
   `unklar`, bleibt das Ticket offen – das ist der gewünschte Fail-closed-Zustand.
5. Danach einen Werktag lang beobachten: Die Queue darf nicht erneut
   aufspringen. Ein Wiederaufspringen wäre jetzt ein echter Quellenbefund oder
   eine Änderung am Spiegel, kein stummer Transportfehler mehr.

**Restrisiko, bewusst benannt:** Der Bundesrechts-Spiegel ist ein Drittanbieter,
nicht die amtliche Quelle. Er bestätigt den Normbestand, nicht die Richtigkeit
der Artikelaussage. Fällt er aus oder ändert seine Struktur, bleibt die Wache
`unklar` (bzw. meldet bei fehlender Datei `tot` mit ausdrücklichem
Verifizierungsauftrag) – in beiden Fällen entscheidet die Redaktion, nie die
Automatik.
