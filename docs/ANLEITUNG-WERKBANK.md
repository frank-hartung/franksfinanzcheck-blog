# Anleitung: Die Werkbank

> Rollout 03.10.2026. SSOT `data/werkbank.yaml` · Wache `scripts/werkbank_gate.py`
> Cockpit `WERKBANK-STATUS.md` · Report `WERKBANK-PREMIUM-2026-10-03.md`

Die Werkbank bündelt vier Fremdwerkzeuge unter einem Vertrag. Sie beantwortet
Fragen mit belegten Quellen, liest Webseiten sauber, beweist Behauptungen im
echten Browser und kann – streng gedeckelt – in Fremd-Apps schreiben.

**Laufende Kosten: 0 €.** Das ist keine Sparmaßnahme, sondern eine
Architekturentscheidung: Was Geld pro Abfrage kostet, wird irgendwann
abgeschaltet oder heimlich gedrosselt. Was uns gehört, läuft weiter.

---

## 1. Die vier Gewerke

| Gewerk | Werkzeug | Rolle | Ohne Einrichtung? |
|---|---|---|---|
| `antwortwerk` | SearXNG + Crawl4AI + freie Synthese | Frage rein, belegte Antwort raus | ✅ ja (Rückfallkette) |
| `leser` | [Crawl4AI](https://crawl4ai.org) | Seite → sauberes Markdown | ✅ ja (Jina, dann urllib) |
| `browser` | [Playwright](https://playwright.dev) | Browser-Beweis für Zitate | ⏸ braucht Chromium |
| `konnektor` | [Composio](https://composio.dev) | Aktionen in Fremd-Apps | ⏸ braucht Schlüssel + Freigabe |

Das `antwortwerk` ist der **Ersatz für Perplexity**. Es ist kostenlos und in
den Punkten besser, auf die es in diesem Blog ankommt – siehe Abschnitt 3.

---

## 2. Sofort loslegen

```bash
# Lage aller Gewerke ansehen (macht keinen einzigen Netzaufruf)
npm run werkbank:status

# Vertrag B1–B9 prüfen und WERKBANK-STATUS.md schreiben
npm run werkbank

# Eine Frage beantworten lassen
python3 scripts/antwortwerk.py --frage "Wie hoch ist der durchschnittliche Strompreis 2026?"

# Fällige Fragen aus dem Fragenplan abarbeiten
npm run antwortwerk

# Alles testen (Selbsttests + 46 Unit-Tests, offline)
npm run test:werkbank
```

Ohne jede Einrichtung läuft das bereits: Suche über DuckDuckGo, Lektüre über
den Jina Reader, Synthese extraktiv. Die nächsten Abschnitte machen es gut.

---

## 3. Warum das besser ist als Perplexity

Perplexity liefert einen flüssigen Absatz mit einer Liste von Links darunter.
Für einen YMYL-Finanzblog ist genau das die schwächste Stelle: Niemand prüft,
ob der verlinkte Text die Behauptung trägt, und die Quellenauswahl kennt den
Unterschied zwischen Bundesnetzagentur und Vergleichsportal nicht.

| | Perplexity | Antwortwerk |
|---|---|---|
| Kosten | 5 $/1000 Abfragen aufwärts, Abo für die Oberfläche | **0 €** |
| Textgrundlage | Snippet aus dem Suchindex | **Volltext** der Seite (Crawl4AI) |
| Quellenauswahl | Relevanz des Anbieters | **Allowlist nach Rang**: amtlich vor Fachinstanz vor Redaktion |
| Affiliate-Quellen | werden zitiert | **gesperrt** – Provisionsquelle ≠ Faktenquelle |
| Selbstzitat | möglich | **gesperrt** (Zirkelschluss) |
| Beleg-Prüfung | nur Linkliste | **Playwright rendert die Seite und sucht die Begriffe** |
| Halluzination | möglich | im Standardmodus **ausgeschlossen** (wörtliche Zitate) |
| Abrufdatum | nicht garantiert | **Pflichtfeld** je Beleg |
| Datenabfluss | jede Frage geht an Perplexity | eigene Suche, eigene Infrastruktur |

Was Perplexity besser kann: Es formuliert runder und ist schneller. Deshalb
gibt es den LLM-Weg (Abschnitt 5) – aber angebunden an dasselbe geprüfte
Material, nicht an das Gedächtnis eines Modells.

### Der Ablauf einer Frage

```
Frage
  │
  ├─ 1. SUCHEN      SearXNG → DuckDuckGo → kuratierter Themenpool
  │                 (erster Anbieter, der liefert, gewinnt)
  │
  ├─ 2. FILTERN     Sperrliste schlägt Allowlist. Was nicht belegfähig
  │                 ist, wird gar nicht erst gelesen.
  │                 Amtliche Quellen (Rang 1) zuerst.
  │
  ├─ 3. LESEN       Crawl4AI holt den Volltext → Markdown
  │                 Rückfall: Jina Reader → rohes HTML
  │
  ├─ 4. PASSAGEN    Sätze nach Begriffsdeckung + Zahlendichte bewerten
  │                 (deterministisch und in zehn Sekunden nachvollziehbar)
  │
  ├─ 5. BEWEIS      Playwright rendert jede zitierte Seite und prüft,
  │                 ob die Suchbegriffe im sichtbaren Text vorkommen
  │
  └─ 6. SYNTHESE    extraktiv (Standard) oder Groq/Gemini, streng
                    an das Material gebunden
                              │
                              ▼
                    data/werkbank/antworten/<datum>-<slug>.md + .json
```

---

## 4. SearXNG einrichten (empfohlen, kostenlos)

SearXNG ist eine Metasuche, die Google, Bing, DuckDuckGo, Brave und weitere
in einer Abfrage bündelt. Sie läuft bei uns selbst – kein Schlüssel, keine
Abfragegebühr, kein Limit.

**Zwei Stolperfallen, die jeder einmal trifft:**
Die JSON-API ist ab Werk **aus**, und der Bot-Limiter blockiert Automaten.
Beides muss in der `settings.yml` stehen.

```bash
mkdir -p ~/searxng && cat > ~/searxng/settings.yml <<'EOF'
use_default_settings: true
server:
  secret_key: "$(openssl rand -hex 32)"
  limiter: false          # sonst 403 für jeden Skriptaufruf
  image_proxy: false
search:
  safe_search: 0
  default_lang: "de"
  formats:
    - html
    - json                # DIESE Zeile schaltet die API frei
EOF

docker run -d --name searxng -p 8080:8080 \
  -v ~/searxng/settings.yml:/etc/searxng/settings.yml:ro \
  -e SEARXNG_BASE_URL=http://localhost:8080/ \
  docker.io/searxng/searxng:latest

# Beweis statt Hoffnung:
curl -s -H 'X-Forwarded-For: 127.0.0.1' \
  "http://localhost:8080/search?q=strompreis&format=json" | head -c 200
```

Danach bekannt machen:

```bash
export SEARXNG_URL=http://localhost:8080
npm run werkbank:status     # searxng muss jetzt ✅ zeigen
```

In der CI startet `.github/workflows/werkbank.yml` den Container selbst und
setzt `SEARXNG_URL` für den Lauf. Dort ist nichts einzurichten.

> **Public Instances taugen nicht.** Fast alle öffentlichen SearXNG-Instanzen
> haben die JSON-API aus gutem Grund abgeschaltet. Wer eine fremde Instanz
> einträgt, bekommt 403 und wandert in die Rückfallkette.

---

## 5. Synthese: extraktiv oder LLM

| Weg | Schlüssel | Ergebnis |
|---|---|---|
| `extraktiv` | – | Wörtliche Passagen, nach Relevanz sortiert, je mit Belegnummer. **Standard.** Kann nicht halluzinieren. |
| `groq` | `GROQ_API_KEY` | Fließtext aus demselben Material. Gratis-Kontingent. |
| `gemini` | `GEMINI_API_KEY` | Zweiter Gratis-Weg, falls Groq drosselt. |

Beide Schlüssel existieren im Repo bereits für das Schaltwerk. Liegen sie
vor, schaltet sich der LLM-Weg von selbst scharf; das Dossier enthält dann
**beides** – den Fließtext und die extraktive Beleglage zum Nachprüfen.

Der Prompt ist eng geführt: kein Wissen aus dem Modellgedächtnis, Belegnummer
hinter jeder Aussage, keine Empfehlung, kein Anbietername. Steht etwas nicht
im Material, muss das Modell das schreiben, statt zu raten.

---

## 6. Crawl4AI nachrüsten

```bash
pip install -r requirements-werkbank.txt
python3 -m playwright install --with-deps chromium
npm run werkbank:status     # leser zeigt jetzt „crawl4ai"
```

Ohne Crawl4AI läuft das Gewerk über den Jina Reader und notfalls über rohes
HTML. Der Unterschied ist Qualität, nicht Funktion: Crawl4AI entfernt
Navigation, Werbung und Fußzeilen (`PruningContentFilter`) und liefert
Markdown statt Textsuppe. Das verbessert die Passagenauswahl spürbar.

---

## 7. Browser-Beweis (Playwright)

```bash
node tools/werkbank/render.mjs \
  --url https://www.bundesnetzagentur.de/ \
  --suche "Strompreis" --suche "2026"
```

Ausgabe ist JSON: `status`, `titel`, `text_laenge`, `auszug`, `treffer`,
`belegt`, `konsolenfehler`. Das Feld `belegt` ist der Kern – es sagt, ob die
gesuchten Begriffe auf der gerenderten Seite tatsächlich vorkommen.

Die Brücke nutzt denselben Browser-Resolver wie die E2E-Suite
(`e2e/browser.mjs`): zuerst `FF_BROWSER_PATH`/`CHROME_PATH`, dann einen
bereits installierten Playwright-Browser, zuletzt das im Root-Lockfile
gepinnte `@sparticuz/chromium`. Der Standardweg benötigt `cdn.playwright.dev`
nicht; Browser-Pin und JavaScript-Smoke-Test sind zentral dokumentiert in
`docs/ANLEITUNG-CHROMIUM.md`.

Fehlt Chromium, meldet das Gewerk **Standby**. Die Antwort entsteht trotzdem,
nur ohne Beweisspalte.

---

## 8. Konnektor (Composio) scharf schalten

Das ist das einzige Gewerk mit Schreibrecht nach außen. Es hat deshalb zwei
Schlösser, und beide muss ein Mensch öffnen.

```bash
# Schloss 1: Schlüssel hinterlegen (GitHub → Settings → Secrets)
export COMPOSIO_API_KEY=...

# Lesender Probeabruf – beweist den Zugang, ändert nichts
python3 -c "import sys; sys.path.insert(0,'scripts'); \
  import werkbank_adapters as w; \
  print(w.konnektor_toolkits(w.lade_ssot())[0][:5])"
```

```yaml
# Schloss 2: data/werkbank.yaml – Aktion ausdrücklich freigeben
konnektor:
  aktionen:
    - slug: GITHUB_CREATE_AN_ISSUE
      zweck: "Redaktionsbefund als Ticket"
      trockenlauf_zuerst: true

gewerke:
  - id: konnektor
    freigabe:
      modus: mensch
      erlaubte_aktionen:
        - GITHUB_CREATE_AN_ISSUE      # ← ohne diesen Eintrag: verweigert
      trockenlauf_pflicht: true
```

Eine Aktion, die nicht auf der Freigabeliste steht, wird verweigert – auch
wenn der Schlüssel vorliegt und der Aufrufer `trocken=False` setzt. Das ist
mit einer Sabotage-Probe im Selbsttest eingefroren (ST14).

**Vor jedem Scharfschalten:** `npm run test:werkbank`, danach ein
Trockenlauf. Der Trockenlauf sendet nie – er braucht nicht einmal einen
Schlüssel.

---

## 9. Der Vertrag B1–B9

`scripts/werkbank_gate.py` trennt zwei Dinge, die gern verwechselt werden:

* **Vertragsbruch** → rot, Exit 1. Jemand hat die Architektur beschädigt.
* **Standby** → gelb, Exit 0. Einem Gewerk fehlt eine Voraussetzung.

| Regel | Inhalt |
|---|---|
| B1 | Kostenregel – kein kostenpflichtiger Anbieter im Pflichtpfad |
| B2 | Schlüsselfreiheit – jedes Pflicht-Gewerk läuft ohne Secret |
| B3 | Standby ist ein Zustand, kein Fehler |
| B4 | Leseregel – nur der Konnektor schreibt, nur mit Freigabe |
| B5 | Belegpflicht – Quelle und Abrufdatum je Aussage |
| B6 | Keine Secrets in der SSOT |
| B7 | Selbsttest läuft offline und ist grün |
| B8 | Verdrahtung – Runbook, Workflow, Brücke, npm-Skripte |
| B9 | Domain-Disziplin – Sperrliste vor Allowlist |

Jede Regel hat eine **Sabotage-Probe**: Der Selbsttest beschädigt den Vertrag
absichtlich und verlangt, dass das Gate anschlägt. Ein Gate, das nur grün
sagen kann, ist Dekoration.

```bash
npm run werkbank                # Bericht + Cockpit
npm run werkbank:json           # maschinenlesbar
npm run werkbank:strict         # Freigabelauf: Standby zählt als Fehler
python3 scripts/werkbank_gate.py --selftest
```

---

## 10. Fragenplan pflegen

`data/werkbank.yaml` → `fragen:`. Kuratiert wie der Themenplan: Die Maschine
beantwortet, der Mensch entscheidet.

```yaml
fragen:
  - id: strompreis-entwicklung
    frage: "Wie haben sich die Strompreise für Haushalte zuletzt entwickelt?"
    themenwelt: strom-gas
    takt_tage: 30        # Mindestabstand bis zur nächsten Recherche
```

Der Zustand liegt in `data/werkbank/antwortwerk_state.json`. Eine Frage ist
fällig, wenn sie nie beantwortet wurde oder `takt_tage` überschritten sind.
Pro Lauf werden höchstens `budget.max_fragen_pro_lauf` abgearbeitet –
Rotation statt Rundumschlag.

---

## 11. Verhältnis zu den bestehenden Systemen

Die Werkbank ist **additiv**. Schaltet man sie ab, verhält sich der Blog wie
vorher.

| System | Verhältnis |
|---|---|
| `scripts/faktenfrische.py` | Bleibt der einzige Weg, auf dem eine Quelle in einen **Artikel** gelangt – samt Anti-Halluzinations-Vertrag. Die Werkbank liefert nur Dossiers. |
| `scripts/agent_reach_research.py` | Bleibt die breite Signalsammlung nach Themenplan. Das Antwortwerk ist die **frageweise** Schwester. |
| `scripts/schaltwerk.py` | Bleibt der Automations-Dirigent. Der Konnektor ist eine zusätzliche Aktionsart, kein Ersatz. |
| E2E-Suite | Teilt sich mit der Brücke den Browser-Resolver. Ein Pin, eine Wahrheit. |

**Wichtig:** Ein Dossier aus `data/werkbank/antworten/` ist eine
Signalsammlung, kein Freigabedokument. Faktenübernahme in Artikel läuft
ausschließlich über die Faktenfrische und ihre Allowlist.

---

## 12. Störungen

| Symptom | Ursache | Abhilfe |
|---|---|---|
| `searxng ⏸ SEARXNG_URL nicht gesetzt` | Instanz unbekannt | Abschnitt 4 |
| `SearXNG antwortet nicht in JSON` | `formats` ohne `json` | `settings.yml` ergänzen, Container neu starten |
| SearXNG liefert 403 | Bot-Limiter aktiv | `server.limiter: false` |
| SearXNG liefert 500 | kaputte Engine in den Defaults | `&engines=duckduckgo,bing` anhängen oder Engine entfernen |
| `DuckDuckGo lieferte keine auswertbaren Treffer` | Drosselung der IP | normal; SearXNG einrichten |
| `browser ⏸ playwright-core fehlt` | Root-Node-Abhängigkeiten fehlen | `npm ci && npm run browser:setup` |
| Chromium startet nicht / Browser-Beweis `defekt` | Paket nicht installiert, Linux-Laufzeit fehlt oder Systembrowserpfad ungültig | `npm run browser:setup` lesen; Standard-Fallback ist gelockt und benötigt kein Playwright-CDN. Alternativ `CHROME_PATH=/pfad/zu/chrome` setzen |
| Dossier ohne Belege | Treffer nicht auf der Allowlist | Abschnitt „Verworfen" im Dossier lesen; ggf. Allowlist in `data/agent_reach/faktenfrische.yaml` erweitern (**redaktionelle Entscheidung**) |
| `konnektor ⏸` trotz Schlüssel | keine Aktion freigegeben | Abschnitt 8, Schloss 2 |
| Gate rot bei B8 | Workflow/Runbook/npm-Skript entfernt | Verdrahtung wiederherstellen, nicht die Regel lockern |

### Exit-Codes

| Code | Bedeutung | CI-Verhalten |
|---|---|---|
| 0 | Antworten erzeugt oder nichts fällig | grün |
| 2 | Skript-/Vertragsfehler | rot |
| 3 | Keine Quelle lieferte belegfähiges Material | Warnung + Issue, kein Abbruch |

---

## 13. Was die Werkbank **nicht** tut

* Sie schreibt **keinen** Artikeltext und ändert **keine** Frontmatter.
* Sie postet **nichts** in soziale Netze.
* Sie übernimmt **keine** Fakten automatisch in den Bestand.
* Sie setzt **nie** `lastmod` (Frische-Inflation).
* Sie zitiert **nie** einen Affiliate-Partner als Faktenquelle.
* Sie führt **keine** Composio-Aktion aus, die nicht ein Mensch freigegeben hat.

Diese sechs Sätze sind keine Absichtserklärung, sondern Gate-Regeln mit
Sabotage-Proben. Wer sie aufweicht, muss zuerst den Selbsttest brechen – und
das fällt auf.
