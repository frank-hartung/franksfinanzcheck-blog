# Werkbank – Premium-Rollout vom 03.10.2026

Crawl4AI, Playwright, Composio und eine **eigene, kostenlose Antwortmaschine**
sind als dauerhafte Schicht in franksfinanzcheck.de eingezogen. Kein
Einmal-Skript, sondern eine Werkbank mit eigenem Vertrag, eigenen Tests,
eigenem Workflow und eigenem Runbook – so, wie die übrigen Gewerke des Hauses
gebaut sind.

Der ursprüngliche Plan sah Perplexity für die Antwort-Recherche vor. Das ist
gestrichen. Statt eines Abonnements steht dort jetzt das **Antwortwerk**:
SearXNG sucht, Crawl4AI liest, die Allowlist entscheidet, Playwright
beweist. Abschnitt 2 begründet, warum das kein Sparzwang ist, sondern das
bessere Werkzeug für genau diesen Blog.

---

## 1. Was neu ist

| Datei | Rolle |
|---|---|
| `data/werkbank.yaml` | SSOT: Gewerke, Budgets, Freigaberegeln, Fragenplan |
| `scripts/werkbank_adapters.py` | Adapterschicht zu Suche, Leser, Browser, Konnektor |
| `scripts/antwortwerk.py` | Die Antwortmaschine selbst (Selbsttest ST1–ST15) |
| `scripts/werkbank_gate.py` | Vertrag B1–B9, fail-closed, mit `--selftest` |
| `scripts/tests/test_werkbank.py` | **55 Tests**, vollständig offline, ~0,7 s |
| `tools/werkbank/render.mjs` | Playwright-Brücke: Zitat im echten Browser prüfen |
| `docs/ANLEITUNG-WERKBANK.md` | Runbook, 13 Abschnitte |
| `.github/workflows/werkbank.yml` | Donnerstag 07:40 MESZ + Handstart |
| `requirements-werkbank.txt` | Abhängigkeiten, alle optional |

Dazu zehn npm-Skripte (`werkbank`, `werkbank:status`, `antwortwerk`,
`test:werkbank`, …) und ein Abschnitt in `CLAUDE.md`.

### Die vier Gewerke und ihre Rollen

- **Antwortwerk** – Faktenfrische und GEO-Sichtbarkeits-Check. Ersetzt die
  Perplexity-Rolle vollständig.
- **Crawl4AI** – sauberes Markdown aus Quellen und Wettbewerbsseiten. Löst den
  Jina Reader ab, der als Rückfallebene bleibt.
- **Playwright** – Browser-Beweis: steht die zitierte Zahl wirklich auf der
  gerenderten Seite? Zusätzlich Renderer unter Crawl4AI.
- **Composio** – Konnektor-Schicht für das Schaltwerk. Ausschließlich geplant,
  nie selbsttätig sendend.

---

## 2. Warum das gleichwertig oder besser ist als Perplexity

Die Anforderung war ausdrücklich nicht „billiger", sondern „gleichwertig oder
besser". Das ist sie, und zwar aus Gründen, die mit dem Preis nichts zu tun
haben. Die Vergleichstabelle steht ausführlich in
`docs/ANLEITUNG-WERKBANK.md`, Abschnitt 3. Die Kurzfassung:

**1. Volltext statt Snippet.** Perplexity synthetisiert überwiegend aus
Suchergebnis-Ausschnitten. Das Antwortwerk lädt jede Quelle vollständig und
entrümpelt sie mit Crawl4AI. Eine Zahl, die erst in Absatz 14 eines
Monitoringberichts steht, findet das Antwortwerk – ein Snippet-Synthesizer
nicht.

**2. Quellenauswahl nach Rang, nicht nach Anbieterrelevanz.** Die Allowlist aus
`data/agent_reach/faktenfrische.yaml` ordnet jede Domain einem Rang zu:
1 = amtlich, 2 = Verbraucher-Fachinstanz, 3 = Wirtschaftsredaktion. Gelesen
wird in dieser Reihenfolge. Perplexity gewichtet nach seinem eigenen
Relevanzmodell, das niemand einsehen kann. Für einen Finanzblog, der
Bundesnetzagentur über Vergleichsportal stellen muss, ist das der
entscheidende Unterschied.

**3. Affiliate- und Selbstzitate sind gesperrt.** Regel B9 leitet die
Sperrliste automatisch aus `scripts/check24_links.yaml` ab und setzt die
eigene Domain dazu. Eine Partnerseite kann sich nicht selbst als Beleg
unterschieben. Das ist nicht konfigurierbar, sondern Vertragsbedingung – das
Gate verweigert sonst den Start.

Diese Sperre hielt im Bau einem echten Angriff nicht stand und wurde gehärtet:
`domain_von()` behielt Port und Zugangsdaten, sodass `check24.de:443` oder
`test.de@check24.de` an der Liste vorbeiliefen. Behoben, mit zwei
Regressionstests eingefroren.

**4. Belegprüfung im echten Browser.** Perplexity liefert eine Linkliste. Das
Antwortwerk öffnet jeden Beleg in Chromium und prüft, ob die zitierten
Begriffe im gerenderten DOM wirklich vorkommen. Ergebnis: `belegt: true/false`
pro Quelle. Hier real nachgewiesen – Trefferfall und Negativfall:

```
$ node tools/werkbank/render.mjs --url … --suche "Strompreis" --suche "Kilowattstunde"
"treffer": [{"begriff":"Strompreis","gefunden":true},
            {"begriff":"Kilowattstunde","gefunden":true}],
"belegt": true

$ node tools/werkbank/render.mjs --url … --suche "Mietwagen"
belegt = False | treffer = [{'begriff': 'Mietwagen', 'gefunden': False}]
```

**5. Der extraktive Modus kann nicht halluzinieren.** Ohne `GROQ_API_KEY` und
ohne `GEMINI_API_KEY` schreibt das Antwortwerk keine freien Sätze, sondern
zitiert wörtliche Passagen mit `[1]`-Belegen. Kein Sprachmodell, keine
erfundene Zahl. Mit Schlüssel schaltet der Synthese-Pfad automatisch scharf –
die Belegpflicht bleibt.

**6. Abrufdatum ist Pflichtfeld.** B5 erzwingt es. Bei Strompreisen, Zinsen und
Steuersätzen entscheidet das Datum über die Gültigkeit einer Aussage.

**7. Keine Weitergabe der Suchanfragen.** Die Themen dieses Blogs –
Versicherungslücken, Schuldenfragen, Steuerthemen – laufen über die eigene
SearXNG-Instanz und nicht über einen Dritten, der sie protokolliert.

**8. 0 € statt rund 5 $ je 1.000 Abfragen,** bei wöchentlichem Lauf dauerhaft.

**Ehrliches Zugeständnis:** Perplexity formuliert runder und antwortet
schneller. Für fließende Prosa auf Knopfdruck ist es besser. Für *belegte*
Fakten in einem Blog, der für seine Zahlen haftet, ist das Antwortwerk das
schärfere Werkzeug – weil jeder Schritt zwischen Frage und Satz prüfbar und
abschaltbar ist.

Perplexity bleibt als Schnittstellen-Vorbild erhalten: Das Dossier-Format des
Antwortwerks folgt bewusst der Struktur der Perplexity-Agent-API
(`search_results` + `message`). Sollte der Anschluss später doch gewünscht
sein, ist er ein Adapter, kein Umbau.

---

## 3. Der Vertrag: B1 bis B9

`scripts/werkbank_gate.py` prüft fail-closed. Die Regeln heißen bewusst
`B…`, weil `W…` bereits von `werkzeuge_gate.py` belegt ist.

| Regel | Prüft |
|---|---|
| B1 | Kostenregel – kein Gewerk darf laufende Kosten verursachen |
| B2 | Schlüsselfreiheit – alles läuft auch ohne jedes Secret |
| B3 | Standby ist ein grüner Zustand, kein Fehler |
| B4 | Schreibrecht nur für den Konnektor, nur mit `freigabe.modus: mensch`, Trockenlaufpflicht und Positivliste erlaubter Aktionen |
| B5 | `abrufdatum_pflicht`, existierende `allowlist_quelle`, `max_belege_antwort >= 1` |
| B6 | Secret-Regex gegen die SSOT – kein Schlüssel im Klartext |
| B7 | `antwortwerk.selftest()` meldet nichts |
| B8 | Verdrahtung: Runbook, Workflow, Brücke, npm-Pflichtskripte vorhanden |
| B9 | Eigene Domain und alle Partnerdomains gesperrt, keine Listenkollision |

Exit-Codes: `0` Vertrag gehalten · `1` Vertragsbruch, defektes Gewerk oder
`--strict` bei Standby · `2` Gate selbst defekt.

Der Selbsttest prüft eine Positivprobe und **zehn Sabotage-Proben** – jede
manipuliert die SSOT auf eine Art, die das Gate erkennen muss. Erkennt es eine
nicht, schlägt der Selbsttest fehl.

---

## 4. Nachweis

Alles hermetisch, ohne Netz, reproduzierbar:

```
$ python3 -m unittest scripts.tests.test_werkbank
Ran 55 tests in 0.734s — OK

$ python3 scripts/werkbank_gate.py --selftest
✅ Werkbank-Gate-Selbsttest grün (Positivprobe + 10 Sabotage-Proben)

$ python3 scripts/werkbank_gate.py --no-cockpit
B1–B9 alle ✅
```

Die Kette wurde **vollständig durchgespielt**, gegen einen lokalen
Fixture-Server, der SearXNG und eine Quellseite spielt – mit echtem Chromium:

```
Suchanbieter : searxng
Belege       : 1
Verworfen    : ['https://www.check24.de/strom/']   ← Sperrliste greift
  Leseweg    : urllib | Browser-Beweis: True
Antwort      : - Der durchschnittliche Strompreis lag 2026 bei 41,8 Cent
                 je Kilowattstunde. [1]
```

Suche → Allowlist-Filter → Lesen → Passagenwahl → Browser-Beweis → Synthese
mit Beleg. Jeder Schritt nachweislich am Werk.

### Warum ein Fixture-Server und kein Live-Lauf

**Die Bausandbox hat kein ausgehendes TLS.** Jeder `urlopen` nach außen endet
mit `URLError: TLS/SSL connection has been closed (EOF)`. Ein Live-Lauf gegen
echte Quellen war hier technisch unmöglich. Statt den Beweis schuldig zu
bleiben, wurde er hermetisch geführt: ein lokaler HTTP-Server liefert
SearXNG-JSON und eine verrauschte HTML-Quellseite, die Kette läuft vollständig
darüber. Das ist der belastbarere Nachweis, weil er in CI jederzeit
wiederholbar ist.

Dieselbe Sperre betrifft den Chromium-Download. Playwright-Chromium ließ sich
nicht laden (`Download failure`), der hauseigene Rettungsweg
`npm i --no-save @sparticuz/chromium` griff und `resolveLaunchOptions()` aus
`e2e/browser.mjs` fand ihn – die Brücke lief damit real.

---

## 5. Drei Fehler, die der Bau selbst gefunden hat

Jeder im Betrieb aufgetreten, jeder behoben, jeder mit Regressionstest
eingefroren:

1. **Trockenlauf verlangte ein Secret.** `konnektor_ausfuehren()` prüfte den
   Schlüssel vor dem Trockenlauf. Ein Trockenlauf plant aber nur und sendet
   nie – er darf kein Secret brauchen. Reihenfolge getauscht.

2. **Der Themenpool war immer leer.** `suche_themenpool()` las eine
   Plan-Struktur (`themen[].quellen[]`), die es in
   `data/agent_reach/themenplan.yaml` gar nicht gibt – der Plan ist flach.
   Schlimmer: Der Feed-Parser kannte nur `<item>` und übersah damit die
   Atom-Feeds von tagesschau und heise, also zwei der drei Hausquellen. Beides
   lief **still** ins Leere. Jetzt werden RSS *und* Atom gelesen, CDATA
   entpackt.

3. **Die Sperrliste war umgehbar.** Siehe Abschnitt 2, Punkt 3.

Dazu eine Härtung beim Schreiben dieses Reports: Die unterste Leseebene
(rohes HTML, wenn Crawl4AI und Jina ausfallen) schleppte `<nav>`, `<footer>`
und `<title>` in die zitierte Passage – ein Beleg, der mit „Navigation
Impressum" beginnt, ist als Zitat wertlos. Das Beiwerk wird jetzt auf allen
drei Leseebenen entfernt.

---

## 6. Anschluss an den Bestand

Additiv, wie vereinbart. Bestehende Skripte behalten ihr Verhalten, wenn die
Werkbank aus ist:

- **`scripts/agent_reach_research.py`** – `sammle_web()` versucht jetzt zuerst
  Crawl4AI und fällt auf den Jina Reader zurück. Ohne installiertes Crawl4AI
  ist der Code-Pfad identisch zu vorher. Der Zweig kann den Recherche-Lauf
  nicht abbrechen; der Brief ist wichtiger als sein Komfort.
  `--selftest` weiterhin grün.
- **`scripts/faktenfrische.py`** – unberührt. Die Werkbank liefert Signale,
  die Faktenübernahme bleibt beim Bestandsskript.
- **`scripts/schaltwerk.py`** – unberührt. Composio steht als Konnektor
  bereit, schreibt aber nichts ohne menschliche Freigabe.

---

## 7. Standby – der grüne Normalzustand

Ohne jedes Secret läuft die Werkbank vollständig. Der heutige Status:

| Gewerk | Zustand |
|---|---|
| antwortwerk | ✅ aktiv (Suche über DuckDuckGo-Rückfall) |
| leser | ✅ aktiv (Crawl4AI nicht installiert, Rückfall greift) |
| browser | ✅ aktiv (Chromium-Beweis startbar, nach `npm ci`) |
| konnektor | ⏸ Standby (kein `COMPOSIO_API_KEY`) |

Ohne `npm ci` meldet der Browser ⏸ statt ✅ – ebenfalls kein Fehler.

⏸ ist **kein Fehler**. Das Gate quittiert Standby mit Exit 0. Nur
`--strict` – für CI gedacht – verlangt alle Gewerke aktiv.

Scharfschalten durch bloßes Hinterlegen eines Secrets, ohne Code-Änderung:

- `GROQ_API_KEY` oder `GEMINI_API_KEY` → Synthese statt extraktiver Zitate
- `COMPOSIO_API_KEY` → Konnektor plant Aktionen (sendet weiterhin nichts ohne
  Freigabe)
- `SEARXNG_URL` → eigene Metasuche statt DuckDuckGo-Rückfall

Für SearXNG genügt in `settings.yml`: `search.formats: [html, json]`,
`server.secret_key` setzen, `server.limiter: false`. Ohne JSON-Format
antwortet die Instanz mit 403 – der Adapter erkennt das und nennt die Ursache
im Klartext statt eines Stacktrace.

---

## 8. Offener Punkt: der Workflow

**`.github/workflows/werkbank.yml` ist geschrieben, lässt sich aber unter
Umständen nicht pushen.** Agenten-Tokens haben keine `workflows`-Permission.
Scheitert der Push mit `refusing to allow an OAuth App to create or update
workflow`, muss die Datei einmalig von Hand übernommen werden – ihr Inhalt ist
vollständig und unverändert einsatzbereit.

Eckdaten: Donnerstag 07:40 MESZ, `workflow_dispatch` (Modus plan/alle/gate/
dry-run, freie Frage), `repository_dispatch: [werkbank]`,
`concurrency: werkbank` ohne `cancel-in-progress`, `timeout-minutes: 30`.
Selbsttests laufen **vor** jedem Netzzugriff. Browser- und SearXNG-Schritt
sind `continue-on-error`. Ein Issue entsteht nur bei echtem Fehlschlag, Label
`werkbank` wird vorher per `gh label create --force` angelegt (Konvention C12).

---

## 9. Was die Werkbank nicht tut

- Sie veröffentlicht nichts. Dossiers landen in `data/werkbank/antworten/`.
- Sie ändert keine Artikel. Faktenübernahme bleibt bei `faktenfrische.py`.
- Sie sendet keine E-Mails, Posts oder Nachrichten ohne menschliche Freigabe.
- Sie erfindet keine Zahlen. Ohne Beleg gibt es keinen Satz, sondern Exit 3
  und eine Warnung.

---

## 10. Nächste Schritte

1. `.github/workflows/werkbank.yml` von Hand übernehmen, falls der Push
   scheitert (Abschnitt 8).
2. Eigene SearXNG-Instanz aufsetzen und `SEARXNG_URL` hinterlegen – der
   DuckDuckGo-Rückfall ist Best-Effort, keine tragende Säule.
3. `GROQ_API_KEY` hinterlegen (Gratis-Kontingent) und den Synthese-Pfad einen
   Lauf lang gegen den extraktiven Modus gegenlesen.
4. Einen Live-Lauf außerhalb der Sandbox fahren, sobald TLS verfügbar ist, und
   die Dossier-Qualität an einer bekannten Zahl prüfen.

Runbook: `docs/ANLEITUNG-WERKBANK.md` – Sofortstart, Störungstabelle,
Exit-Codes, Freigabeverfahren.
