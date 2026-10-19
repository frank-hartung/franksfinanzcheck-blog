# Anleitung: Fremdmessung-Sperre – Umami ist entfernt und bleibt es

Stand: 19.10.2026 · Wache: `scripts/fremdmessung_sperre.py` · Tests:
`scripts/tests/test_fremdmessung_sperre.py` · Vertrag: C40 im
Governance-Vertrag · Anlass: Governance-Report #806

## Wozu

Am 11.10.2026 wurde Umami aus dem Frontend genommen (Tracking-Skript,
Einwilligungs-Banner). Die **Anbindung** lebte weiter: zwei Import-Skripte,
je zwei Workflow-Schritte in zwei Workflows, ein Secret samt Live-Probe,
vier Datenstände, ein Trichter, der behauptete „Klicks und Besuche werden im
Umami-Dashboard erfasst“ (falsch: nichts wurde erfasst) und zwei Info-Zeilen im
Governance-Issue. Nichts davon hat etwas gemessen. Alles hat Aufmerksamkeit
gekostet und eine Messung vorgetäuscht, die nicht stattfand.

Am 19.10.2026 ist das restlos entfernt. Die Sperre sorgt dafür, dass es dabei
bleibt – ob durch einen Menschen, einen Agenten oder einen Merge-Unfall.

## Was verboten ist (fünf Klassen, alle hart)

| Klasse | Heißt | Beispiel |
|---|---|---|
| **F1-DATEI** | Eine Datei oder ein Ordner trägt den Namen des Dienstes (Code, Daten, Doku – ein Foto nicht) | `scripts/<name>_clicks.py`, `data/<name>_views.json` |
| **F2-ANBINDUNG** | Ein Anbindungs-Merkmal steht im Text – **überall**, auch in `content/` und `data/`, denn diese Merkmale sind nie Prosa | Skript-Host, Ereignis-Attribut `data-…-event`, `data-website-id` (auch bei selbst gehosteter Instanz), `…track(`, Secret/Variable `…_API_TOKEN`, Konfig-Schlüssel `params.…`, Gate-Kennung `--emit …` |
| **F3-ERWAEHNUNG** | Der Name steht in einer **lebenden technischen Datei** (Workflow, Skript, Layout, Doku, `package.json` …) | ein Kommentar „wird bei uns gemessen“ |
| **F4-GEBAUT** | Der **gebaute** Baum trägt ein Anbindungs-Merkmal – oder, in Skripten und Stilen, die Besucher laden, den Namen | ein Kommentar in `static/premium/*.js` landet im Browser |
| **F5-AUSNAHME** | Eine Ausnahme ist unbegründet, unbekannt oder **veraltet** | eine Ausnahme, die keinen Fund mehr deckt |

**Redaktion ist erlaubt:** „Umami“ ist auch eine Geschmacksrichtung. Das bloße
Wort in `content/` und `data/` (und in gebautem Artikel-HTML) ist deshalb
**kein** Befund – ein Kochtipp im Sparratgeber legt das Qualitäts-Gate nicht
lahm. Nur die Anbindungs-Merkmale (F2/F4) bleiben dort verboten.

**Nicht gescannt (Historie):** datierte Berichte (`…-JJJJ-MM-TT.md`),
`docs/archiv/`, das Patch-Archiv der Awin-Entfernung und alle append-only
Ledger (`data/**/*.jsonl`). Eine Geschichte umzuschreiben wäre Fälschung, keine
Sauberkeit.

**Nicht gescannt (generierte Momentaufnahmen):** `COCKPIT.md`,
`data/cockpit_status.json`, `data/governance_status.json` schreibt ein Bot-Lauf
komplett neu (täglich bzw. wöchentlich). Sie hinken dem Code höchstens einen Lauf
hinterher; die *Ursache* einer Spur dort läge im Code, den die Wache prüft. Ein
Lauf-Rückstand soll `main` nicht rot färben (etwa nach einem Merge-Konflikt, bei
dem die ältere Bot-Fassung gewinnt).

## Bedienung

```bash
python3 scripts/fremdmessung_sperre.py                   # Quelltext prüfen (Exit 0/1)
python3 scripts/fremdmessung_sperre.py --public public/  # zusätzlich den gebauten Baum (erst `hugo --minify`)
python3 scripts/fremdmessung_sperre.py --json            # maschinenlesbar
python3 scripts/fremdmessung_sperre.py --selftest        # Logik-Beweis (schreibt nie)
npm run test:fremdmessung                                # Selbsttest + Quelltext + Regressionstests
```

Die Wache liest Dateien und führt nichts aus. Sie prüft die **versionierten und
neu angelegten, nicht ignorierten** Dateien – ein frisch angelegtes Skript fällt
also schon vor dem Commit auf.

## Wo sie läuft (ohne dass jemand daran denken muss)

| Ort | Wann | Was |
|---|---|---|
| **Governance-Vertrag C40** (`governance_contract.py --quick`) | jeder Push und jede PR (Qualitäts-Gate `link-check.yml`, ohne Pfadfilter), täglich 03:15, montags in der Governance | Wache vorhanden, im vertraglichen Minimum (C6), Regressionstest da, Gate ruft den Vertrag – und der **Live-Lauf über den echten Quelltext** ist still |
| **Regressionstest** (`test_fremdmessung_sperre.py`) | jede PR mit Änderungen an Layouts, Content, Assets, `hugo.toml`, Skripten, Workflows – **nach einem echten Hugo-Bau** | Quelltext **und** `public/` (F4) |
| **Selbsttest der Wache** | vertragliches Minimum (C6) | beweist, dass jede Klasse und jedes Merkmal wirklich anschlägt |

Kein Workflow musste dafür geändert werden: Die Sperre hängt an Verträgen und
Tests, die ohnehin laufen (Haus-Muster „kein Workflow-Patch“).

## Eine Ausnahme eintragen (selten, mit Grund)

Gehört der Name aus einem guten Grund in eine Datei – etwa eine **Sperrliste**
(die Newsletter-QA verbietet Tracker, statt sie zu benutzen) oder ein
**Absenz-Test** (er beweist, dass etwas fehlt) –, dann in
`scripts/fremdmessung_sperre.py` im Wörterbuch `ERLAUBT`:

```python
"pfad/zur/datei": "Grund, der vor einem Menschen besteht (mind. 20 Zeichen).",
```

Regeln: jede Datei einzeln (keine Wildcards), Grund Pflicht, und **die
Ausnahme muss einen Fund decken** – sonst meldet F5 sie als veraltet. Das ist
Absicht: Eine Ausnahme ohne Fund ist ein offenes Tor für eine spätere Rückkehr
genau in dieser Datei. **Eine Ausnahme ist nie die Lösung für eine Anbindung** –
die wird entfernt.

### Die zwei offenen Ausnahmen (einmalig aufzuräumen)

`layouts/_default/_markup/render-link.html` (zwei Kommentarzeilen) und
`scripts/check24_links.yaml` (eine Kommentarzeile) stammen aus der Zeit vor der
Entfernung. Beide Dateien sind **KRITISCH gesiegelt**; jede Änderung – auch an
einem Kommentar – verlangt die menschliche Neu-Signatur. Das ist bewusst keine
Agenten-Entscheidung. Beim nächsten Siegel-Termin:

1. In beiden Dateien die Kommentare ohne Namensnennung umformulieren
   (`render-link.html`: „Umami-Events“ → „Klick-Marken (`data-klick-*`)“, der
   Absatz „Umami-Event `affiliate_click` trägt jetzt ZUSÄTZLICH …“ →
   „Die Marke `data-klick="affiliate_click"` trägt …“; `check24_links.yaml`:
   „gemessen (Umami, siehe PINTEREST-PREMIUM-STRATEGIE.md §11)“ →
   „ausgewertet (Pinterest Analytics, siehe PINTEREST-PREMIUM-STRATEGIE.md §11)“).
2. `python3 scripts/integrity_guard.py --set-current`
3. Die beiden Einträge in `ERLAUBT` löschen – F5 meldet sie sonst als veraltet.

Bis dahin ist nichts offen: Die Zeilen sind Kommentare ohne Wirkung, der Bau
enthält sie nicht (Hugo-Kommentare werden nicht ausgeliefert).

## Wenn jemand wieder messen will

Das ist erlaubt – als **Entscheidung**, nicht als Unfall:

1. Datenschutz-Prüfung und Freigabe durch den Inhaber (der Datenschutzbericht
   vom 10.10.2026 beanstandete die Fremdmessung; ohne neue Prüfung kein
   Wiedereinbau).
2. Quelle, Meta-Datei, Betriebsschalter und Test – wie beim eigenen Klickzähler
   (`docs/ANLEITUNG-KLICKMESSUNG-OHNE-COOKIES.md`).
3. Die Sperre bewusst ändern (Muster oder Ausnahme) – im selben PR, mit Grund.
   Ein stiller Wiedereinbau scheitert an C40, bevor er gemergt ist.

## Was die Sperre NICHT tut

- Sie prüft nicht, ob **andere** Dienste eingebunden sind (Google Analytics,
  Matomo …). Das Partial `google_analytics.html` ist ein inaktiver Platzhalter
  (keine Dienst-ID konfiguriert). Weitere Dienste lassen sich in die Muster der
  Wache aufnehmen, wenn der Inhaber es will.
- Sie ersetzt keine Datenschutz-Prüfung und trifft keine rechtliche Aussage.
- Sie schreibt nichts um: Historie, Ledger und datierte Berichte bleiben, wie
  sie waren.
