# VORLESEN — WORTLAUF-REPARATUR (05.09.2026)

**Projekt:** FranksFinanzcheck · FF Voice Studio · **Anlass:** Zwei Leser-Befunde an der Live-Funktion · **Ergebnis:** Beide behoben, mit 110 neuen Gates abgeschlossen · **Version:** `2026.09.05-c` (Reader und Tonspur-Rezept)

---

## 1 · Die beiden Befunde

### Befund A — Doppel-Lesen auf `/pillar/strom-sparen/#das-wichtigste-auf-einen-blick`

> „Hier wird der Text zunächst richtig vorgelesen, aber hinter **800 € pro Jahr** erfolgt erneut **Tarifwechsel als größter Hebel.**“

Der Übersichts-Listenpunkt

```markdown
* **Tarifwechsel als größter Hebel:** Ein Wechsel des Strom- oder Gasanbieters
  dauert online weniger als zehn Minuten und spart im Schnitt 300 € bis 800 € pro Jahr.
```

wurde korrekt gelesen — und **danach** erklang der Fettdruck-Lead-in ein zweites Mal. Reproduzierbar auf jeder Seite mit einem `**Lead-in:**` am Blockanfang (alle vier Punkte der Übersicht, die Schritt-für-Schritt-Checkliste, die Monatskarte „**Februar.** …“ u. v. m.).

### Befund B — Englisch im deutschen Satz klingt deutsch

> „Das TTS-Modell kann in einem überwiegend deutschsprechenden Text mit wenig Englisch offenbar nur deutschsprechenden Text anwenden.“

Das Sprach-Routing entschied **pro Satz** (`sniffSentenceLang`). Ein deutscher Satz mit englischen Fachbegriffen blieb damit vollständig bei der deutschen Stimme:

```
„Ein Robo Advisor nutzt Compound Interest und Cost Averaging.“  → ganzer Satz: de
```

Genau das beschwert der Befund: In einem überwiegend deutschen Text wird das wenig englische Vokabular deutsch verlesen („Robo Advisór“, „Compaund Interést“).

---

## 2 · Ursachen (Root Cause)

### A · `isStandaloneEmphasis()` — die Knotenzahl-Falle

```js
var siblings = parent.childNodes.length;
return text.length >= Math.max(12, parentText.length - 2) || siblings <= 2;
```

`childNodes` zählt **Textknoten mit**. `<li><strong>Label:</strong> Rest</li>` hat genau zwei Kindknoten (`<strong>` + Textknoten) — `siblings <= 2` war also immer wahr, obwohl dem `<li>`-Text nach der Fettdruck nur ein **Lead-in** ist. Ergebnis: Der Listenpunkt wurde als Block gesprochen **und** der Lead-in zusätzlich als eigener `emphasis`-Block (Dokumentordnung: erst richtig, dann die Wiederholung — exakt der Befund).

### B · Sprach-Routing nur auf Satz-/Blockebene

`collectBlocks()` riecht pro Block, `splitForSpeech()` pro Satz. Innerhalb eines Satzes gab es **kein** Modell — die deutsche Stimme sprach, was der Satz hergab. Ein Wortwechsel („bilingualer Hörfunk-Moderator“) existierte nicht.

---

## 3 · Reparatur

### 3.1 Doppel-Lese-Schleuse (A)

1. **`isStandaloneEmphasis()` (JS + Python wortgleich):** Die Knotenzahl-Regel `siblings <= 2` ist ersatzlos gestrichen. Maßgeblich ist allein der **Textanteil** am Elternelement: `text.length >= max(12, parentText.length - 2)`. Ein `**Lead-in:** Rest`-Block ist damit nie mehr „eigenständig“; ein echter Merksatz (`<p><strong>Merksatz …</strong></p>`) bleibt es.
2. **Zweite Schleuse — Vorfahren-Prüfung:** Bevor ein `strong/b` als `emphasis`-Block geschrieben wird, prüfen beide Implementierungen, ob derselbe Text bereits in einem **Vorfahren-Block** steht (Lead-in im Listenpunkt, CTA-Linktext im Absatz `👉 … [**→ Jetzt Stromtarife vergleichen**](…)`). Dort ist er schon gesprochen — der Zusatzblock entfällt. Blöcke liegen in Dokumentordnung, der Vorfahren-Block liegt also stets davor; der Rückwärtsscan bricht am jeweiligen Vorfahren ab.

**Wirkung auf der Pillar-Seite:** Vorher 98 Blöcke mit drei unerwünschten Zusatz-Blöcken; nachher werden alle Lead-ins und CTA-Linktexte **genau einmal** gesprochen, echte Merksätze bleiben unverändert an ihrer Stelle.

### 3.2 Wortlauf-Regie (B) — Sprachwechsel mitten im Satz

Neu in **beiden** Implementierungen (JS `languageRuns()` ↔ Python `language_runs()`, wortgleich gespiegelt, Parität geprüft): Jede Sprecheinheit wird in **maximale Sprachläufe** zerlegt. Die Segmente konkatenieren exakt zum Eingabetext (Vertrag ans Paritäts-Gate).

* **Belegwortschatz `EN_WORDS`** — Funktionswörter und Finanz-Fachbegriffe mit Scores (3 = trägt allein: *broker, cashflow, trading, robo, advisor, compounding, budgeting …*; 2 = trägt mit Partner: *money, savings, compound, interest, stock, fund, insurance …*).
* **Scheinfreunde `DE_EN_HOMOGRAPHS`** — *die, was, hat, will, fast, rat, gut, so, man …* zählen nie als Evidenz (in beiden Sprachen echte Wörter).
* **Deutscher Belegwortschatz `DE_EVIDENCE`** — ~130 häufige deutsche Wörter ohne Umlaut/Endungsmerkmal (*kommt, kostet, bringt, bleibt, richtig, wirklich …*). Er härtet die Satzmitte: „Der **Cashflow** kommt jeden Monat.“ bleibt nach dem Fachbegriff sofort wieder deutsch.
* **Etablierte Anglizismen** (App, Team, Meeting, Download, Training …) bleiben bewusst bei der deutschen Stimme — sie spricht sie korrekt.
* **Wechsel-Schwelle:** ein Fachbegriff (Score 3) trägt allein; sonst mindestens zwei belegte Wörter. Ein einsames Funktionswort („The“ in „The Big Short“) wechselt nicht — keine Stimm-Fetzen.
* **Innenräume:** beleglose Wörter zwischen Ankern derselben Sprache gehören in den Lauf („funds of funds“). Nachlaufende, unbelegte Wörter bleiben in der Artikelsprache („Cashflow **kommt**“ ist deutsch) — nur stiller Nachlauf (Komma, Punkt, Leerraum) hängt für den Atempunkt an den Wechsel.

**Tonpfad A — Studio-Tonspur:** `synth_article()` vertont jetzt **je Lauf** mit der passenden männlichen Stimme (`de-DE-Florian…` / `en-US-Andrew…` bzw. Profilstimmen); Tempo, Tonlage, Rolle bleiben der Atemgruppe treu. Fällt die EN-Vertonung eines Laufs aus, springt der Lauf auf die Artikelsprache — **nie verstummt ein Wort**. Die Block-Zeitachse `{b, t0, t1, lang}` bleibt unverändert (Live-Markierung stabil).

**Tonpfad B — Browser-Engine:** `speakUnit()` spricht die Läufe einer Einheit als **Kette** von Äußerungen — jede mit `u.lang`/männlicher Stimme ihres Laufs, gemeinsame Prosodie. Fortschritt (`onboundary` mit Lauf-Offset), Live-Markierung, Anti-Stall-Wache **je Lauf** (4 s), Retry der ganzen Einheit, Pause/Resume, Media Session: alles bleibt eine Einheit. Kein Umschalter, kein Menü — die Regie entscheidet satzteil-genau.

### 3.3 Rezept-Version

`RECIPE_VERSION → ff-voice-2026.09.05-c`, `VOICE_VERSION → 2026.09.05-c`. Der Inhalts-Fingerprint des Deploy-Generators ändert sich, damit **bestehende Tonspuren neu vertont werden** (das Doppel-Lesen steckte auch in den erzeugten MP3s).

---

## 4 · Qualitätssicherung — 805 Gates, alle grün

| Suite | Vorher | Nachher | Neu abgesichert |
|---|---:|---:|---|
| `ff_voice_functional_test.mjs` | 174 | **185** | Doppel-Lese-Schleuse am exakten Pillar-Befund (Lead-ins ×1, „Februar“ ×1, CTA ×1, Merksatz bleibt Block, keine Doppeltexte) |
| `ff_voice_voice_test.js` | 71 | **96** | Wortlauf-Regie: Segmentierung, Konkatenations-Vertrag, Scheinfreunde, Wiedergabe mit echtem Stimmwechsel (EN-Stimme spricht „Robo Advisor“, DE-Stimme „nutzt“), deutscher Einschub im EN-Artikel |
| `ff_voice_parity_check.py` | 269 | **332** | Wortlauf-Parität (14 Mustersätze, beide Verträge) + absolutes Pillar-Fixture (schlägt an, wenn BEIDE Seiten identisch falsch lesen) |
| `ff_voice_audio.py --selftest` | 48 | **65** | Generatorenanalogon der Schleuse + Wortlauf-Checks |
| `ff_voice_backends.py --selftest` | 44 | 44 | — |
| `ff_voice_toolbar_check.py` | 89 | 89 | — |
| **Gesamt** | **695** | **805** | **+110 Gates** |

Dazu der Beweis am echten Bestand: Der Pillar-Artikel `strom-sparen` (98 Blöcke, 178 Sprecheinheiten) trägt jeden Lead-in und jeden CTA-Linktext **genau einmal**; die Suiten laufen gegen `content/pillar` sowieso bei jedem Push (Workflow „Lesehilfen-Gate“) und täglich als Wache.

---

## 5 · Verhalten nach der Reparatur (Hörprobe)

| Satz | Vorher | Nachher |
|---|---|---|
| „Ein Robo Advisor nutzt Compound Interest und Cost Averaging.“ | ganz deutsch | `de: Ein ·` **`en: Robo Advisor`** `· de: nutzt ·` **`en: Compound Interest`** `· de: und ·` **`en: Cost Averaging.`** |
| „Der Cashflow kommt jeden Monat.“ | ganz deutsch | `de: Der ·` **`en: Cashflow`** `· de: kommt jeden Monat.` |
| „Mit Buy and Hold bleibst du flexibel.“ | ganz deutsch | `de: Mit ·` **`en: Buy and Hold`** `· de: bleibst du flexibel.` |
| „Was hat er damit gemeint?“ | deutsch | deutsch (Scheinfreund kippt nicht) |
| „Tarifwechsel als größter Hebel: … 800 € pro Jahr.“ | Text **+ Wiederholung** | genau einmal |

---

## 6 · Betroffene Dateien

| Datei | Änderung |
|---|---|
| `static/premium/ff-voice.js` | Wortlauf-Regie (`languageRuns`, `wordClassOf`, Belegwortschätze), Lauf-Kette in `speakUnit`, `isStandaloneEmphasis` repariert, Vorfahren-Schleuse, Version `2026.09.05-c` |
| `scripts/ff_voice_audio.py` | Spiegel all dessen (`language_runs`, `word_class_of`, `_is_standalone_emphasis`, Lauf-Vertonung in `synth_article`, Fallback auf Artikelsprache), Selbsttests |
| `scripts/ff_voice_backends.py` | Rezept-Version `ff-voice-2026.09.05-c` (Neuvertonung bestehender Tonspuren) |
| `scripts/ff_voice_probe.mjs` | Fühler liefert jetzt auch `languageRuns`-Ergebnisse |
| `scripts/ff_voice_parity_check.py` | Wortlauf-Parität + absolutes Pillar-Fixture (Abschnitt 4) |
| `scripts/ff_voice_functional_test.mjs` | Gruppe 2b (Doppel-Lese-Schleuse) |
| `scripts/ff_voice_voice_test.js` | Gruppen 8b/8c (Wortlauf-Regie + Wiedergabe) |
| `README.md` | Gate-Zähler aktualisiert |

Report-Ende. Nachträge zur Architektur: `LESEHILFEN-STUDIO-2026-09-05.md`, Tabellen: `VORLESEN-TABELLEN-HIGHEND-REPORT.md`.
