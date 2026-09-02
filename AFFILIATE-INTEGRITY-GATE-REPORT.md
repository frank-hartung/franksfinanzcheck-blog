# 🛡️ AFFILIATE-INTEGRITY-GATE-REPORT – Premium-Dauerfix (02.09.2026)

**Auftrag (Frank):** *„Affiliate-Integritäts-Wache (täglich) #20 – bitte auf
Premium-Level dauerhaft beheben."*

**Dauerauftrag, unverändert gültig (14.08.2026):** *„Die Affiliate-Links
wurden beschädigt. Bitte dauerhaft beheben (Automatik und Selbstheilung),
indem die Veröffentlichung nur vorgenommen wird, wenn alle Links
funktionieren und tatsächlich im Blog erscheinen. Ansonsten soll sofort eine
Reparatur erfolgen."*

**Ergebnis:** 🟢 Die Wache ist grün, blindstelle-frei und fail-closed.
**25 Live-Artikel · 86 gerenderte Affiliate-Links · 86/86 mit
`rel="sponsored"` + Klick-Attribution + Awin-SubID · 0 rohe Partner-Links ·
0 nicht registrierte `/go/`-Keys · 0 offene Funde.**

---

## 1. Befund: Warum die Wache #20 rot war – zwei unabhängige Defekte

Die tägliche Wache lief seit Wochen rot (Runs `32933668966`, `33211717423`,
`33468544208`, `33589511441`; Alert-Issues #76, #78, #95, #99, #137, #146).
Es waren **zwei voneinander unabhängige** Ursachen – beide mussten weg, sonst
wäre nur die halbe Ruhe eingetreten:

### Defekt A – „stille Blindheit": der Render-Beweis zählte Phantom-Nullen

Am 01.09.2026 wurde der Render-Hook
`layouts/_default/_markup/render-link.html` fachlich korrekt erweitert
(Awin-SubID `?subid=<artikel-slug>`, Umami-Kontext-Attribute für
`click_attribution.py`). Seitdem meldete AI4 in **jedem** Artikel
`nur 0 statt mind. N Affiliate-Links im gebauten HTML gefunden` – 24 von 24.

Ursache: AI4 war ein einziges starres Regex auf die exakte
Attribut-Reihenfolge der Ausgabe von 14.08.:

```python
# ALT (blind seit 01.09.)
rendered = len(re.findall(r"<a href=/go/[\w-]+/[^>]*affiliate_click[^>]*>", html))
```

Der Hook liefert aber

```html
<a href="/go/kfz-versicherung/?subid=2026-08-26-kfz-…" rel="sponsored nofollow noopener"
   target=_blank data-umami-event=affiliate_click data-umami-event-slug=kfz-versicherung …>
```

– **quotiertes** href (Regex erwartete unquotiert), **`?subid=`** im Pfad
(bricht `[\w-]+/`), und **vier Attribute** zwischen `href` und
`data-umami-event`. Trefferzahl: 0. Die Links waren die ganze Zeit korrekt
im HTML; nur der Zähler war kaputt.

**Folgeschaden (real, nicht theoretisch):**

| Betroffen | Wirkung |
|---|---|
| `AFFILIATE-INTEGRITY-REPORT.md` | 24/24 „Render-Probleme" – täglich rot |
| `BESTAND-REPORT.md` | 24/24 „Selbstheilung fehlgeschlagen" (bestand_gate via publish_gate) |
| `publish_gate.py` | jeder Re-Queue-Kandidat wäre wegen Phantom-Fehler verworfen/zurückgestuft worden |
| **`2026-08-26-handytarif-vergleichen-2026-guenstige-tarife`** | **am 02.09. tatsächlich geparkt** (`cadence_grund: publish-gate: Affiliate-Link-Integrität nicht bestanden … nur 0 statt mind. 2 …`) – ein sauberer Artikel, den die Wache selbst ausgebremst hat |
| Alert-Issues | tägliche Duplikate statt eines gepflegten Issues |

### Defekt B – der Workflow selbst: 403 am Deploy-Trigger

Selbst als das Gate lief, scheiterte der Lauf am Schritt **„Deploy
anstoßen"**: `createWorkflowDispatch` verlangt die Permission
`actions: write` – dieser Workflow hatte nur `contents: write` und
`issues: write`. `deploy-catchup.yml` und `willkommenstext-refresh.yml`
hatten sie längst, die Affiliate-Wache nicht. Ergebnis: 403, Lauf rot,
Alert-Issue – jeden Tag.

Zusatzfund: die Deploy-Bedingung hing an `GEHEILT`, das `git_sync.sh` über
`sync_ok()` **auch bei „nichts zu pushen"** setzt. Der Deploy konnte also
ohne echte Reparatur anspringen (und umgekehrt eine echte Heilung ohne
sofortigen Deploy ins Repo gehen).

---

## 2. Dauerhafte Behebung (Premium-Level)

### 2.1 `scripts/affiliate_integrity_gate.py` – Version 2

| Neu | Wirkung |
|---|---|
| **Attribut-tolerante `<a>`-Auswertung** (`parse_anchors`) statt Positions-Regex | Reihenfolge, Quotes, Minifizierung, `?subid=` sind egal – der Beweis hält, solange das Hook-Attribut *existiert* |
| **Schlüssel-genauer Vergleich** (Markdown-Key ↔ HTML-Key) statt reiner Anzahl | Ein Link, der aufs falsche Ziel zeigt oder unterwegs verloren geht, fällt auf – nicht nur „zu wenige" |
| **`--selftest` mit eingefrorenen Fixtures** | Reale Hook-Ausgaben: aktuell (01.09., mit `?subid=`), Legacy (14.08., unquotiert), unminifiziert/mehrzeilig; plus die Schadensbilder von 14.08. (Dangling-Link, rohe Partner-URL, fremder Key), Deduplikation, AI5, Heilung, Build-Frische |
| **Drift-Wächter gegen das Live-Template** | Fehlt `render-link.html` der Fingerabdruck `/go/` + `affiliate_click`, meldet das Gate „Detektor veraltet" (Exit 2) statt grüner Nullen – genau der Fehlerklasse von Defekt A |
| **Fail-closed (Exit 2)** | Kein `public/`, kaputter Hugo-Build, veralteter Detektor = *Werkzeugfehler*. Es wird nichts „geheilt", nichts verworfen, und `publish_gate.py` veröffentlicht **nichts** |
| **Massen-Blindheits-Erkennung** | 0 gerenderte Links in *allen* Artikeln gleichzeitig = Detektorfehler, nicht Inhaltsschaden → Exit 2 statt 24 Phantom-Funde. Die Wache kann sich nicht mehr still selbst blenden |
| **Automatische Build-Frische** | `public/` fehlt oder ist älter als `content/`/`layouts/`/`static/`/`hugo.toml` → Hugo-Rebuild vor dem Beweis (sonst Beweis gegen veraltete Artefakte) |
| **AI5 Gateway-Beweis (neu)** | Jede referenzierte `/go/<key>/`-Seite muss existieren, `noindex` sein und **exakt auf die registrierte Partner-URL** weiterleiten (Meta-Refresh *oder* JS) |
| **`rel="sponsored"`-Prüfung (neu)** | Kennzeichnungspflicht/Google-Richtlinie wird am gebauten HTML bewiesen – hat Defekt C sofort gefunden |
| **Heilung: Umrouting statt nur Neugenerieren** | Nicht registrierte Keys und rohe Partner-URLs werden auf die *thematisch korrekte* Route umgeschrieben (`affiliate_marketer.route_for()`), CTA-Zeilen weiterhin komplett neu generiert (nie Text-Patch, nie Löschen) |
| **Maschinenlesbarer Zustand** `.affiliate_integrity_state.json` | Exit-Code, geheilte Slugs, offene Funde, Werkzeugfehler, Build-Info – die Workflows entscheiden daraus, nicht aus Log-Text |
| **Präziser Report** | Statuszeile, Build-Herkunft, Render-Beweis-Tabelle je Artikel (Markdown → HTML + Gateway-Ziele), Hinweise (Anti-Stuffing) getrennt von Funden |

Exit-Codes: `0` grün · `1` Inhaltsschaden offen · `2` Werkzeugfehler
(fail-closed). Haus-Konvention aller Wachen (Selbsttest → Exit 2) eingehalten.

### 2.2 Defekt C – echter Fund der reparierten Wache (sofort geheilt)

Kaum sah die Wache wieder scharf, fand sie einen **realen** Mangel, der
bislang durch alle Raster fiel:

Die Shortcodes `tarifvergleich` und `einspartabelle` rendern ihr HTML selbst
und laufen **nicht** durch die Markdown-Link-Pipeline – der Render-Hook
greift dort nicht. Ihre CTA-Buttons zeigten zwar korrekt auf `/go/<key>/`,
trugen aber **weder `rel="sponsored nofollow noopener"` noch das
Umami-Ereignis `affiliate_click` noch die Awin-SubID**.

Betroffen: **6 Buttons in 2 Artikeln**
(`2026-08-16-gas-anbieter-wechseln-praxis-tipps-fuer-guenstige-tarife`,
`2026-08-19-energiediebe-stoppen-so-kannst-du-stromfresser-finden`).
Konkret: Werbekennzeichnung unvollständig + diese Klicks waren in der
Umsatz-Messung unsichtbar.

**Fix:** neues zentrales Partial
`layouts/_partials/affiliate_anchor_attrs.html` – derselbe Vertrag wie der
Render-Hook, an einer Stelle, von beiden Shortcodes genutzt (Gateway-Link →
`rel=sponsored` + `target=_blank` + Umami-Event + SubID + Werbe-Tooltip;
internes Ziel → unverändert). Zwei Stolpersteine sind im Partial
dokumentiert, damit sie niemand erneut baut:

- Rückgabe als **Dict**, nicht als fertige Attribut-Zeichenkette – eine
  vorformatierte `HTMLAttr`-Kette wird von Go-Html-Template in fremdem
  Attribut-Kontext zu `zgotmplz` entschärft (toter Link).
- Kontext-Auflösung über **`.Page`** – ein Shortcode-Kontext
  (`ShortcodeWithPage`) hat kein `.File`; direkter Zugriff bricht den Build
  ab. Zudem wird der Shortcode-Kontext oben als `$ffSeite` festgehalten,
  weil `range`/`with` den Punkt verschieben.

### 2.3 `scripts/publish_gate.py` – Kandidaten-Bezug + fail-closed

1. **Fail-closed:** `exit_code 2`/`errors` der Wache blockieren jetzt **alle**
   Kandidaten mit Klartext-Grund. Vorher galt „kein JSON = keine Funde =
   live" – das verbot der Dauerauftrag ausdrücklich.
2. **Kandidaten-Filter:** Bestandsschäden (oder Phantom-Funde) reißen keine
   neuen Artikel mehr mit in den Verwurf. Bestand heilen
   `bestand_gate.py`/die tägliche Wache – nie das Publish-Gate.
3. `--no-build` im Prüfaufruf: das Gate greift nie in einen fremden
   Build-Zustand ein (deploy.yml baut bewusst direkt vorher selbst).

### 2.4 `scripts/bestand_gate.py` – fail-closed

Auswertungsfehler zählen jetzt als rot (`return 1 if still_affected or
errors`); vorher gingen Werkzeugfehler als „Bestand sauber" durch.

### 2.5 `.github/workflows/affiliate-integrity-daily.yml`

> ⚠️ **Diese Datei liegt als fertiger Patch bei** – der Agent-Token ist eine
> GitHub-App ohne `workflows`-Permission, GitHub lehnt Pushes auf
> `.github/workflows/` ab. Haus-Konvention (wie
> `patches/heading-gate-2026-08-27-workflows.patch`):
>
> ```bash
> git apply patches/affiliate-integrity-premium-2026-09-02-workflows.patch
> # alternativ 1:1 kopieren:
> cp patches/affiliate-integrity-daily-2026-09-02-workflow-ready.yml \
>    .github/workflows/affiliate-integrity-daily.yml
> ```
>
> Der Patch ist verifiziert (`git apply --check` grün, Ergebnis byte-identisch
> zur ready-Datei, YAML + alle JS-/Bash-Blöcke validiert).
> **Ohne ihn bleibt die Wache an Tagen mit echter Heilung rot (403).**

| Änderung | Wirkung |
|---|---|
| **`actions: write`** | Defekt B weg – Deploy-Dispatch läuft (403 bisher) |
| **Stage 1: Detektor-Selbsttest** vor jeder Prüfung | Bricht der Detektor, bricht der Lauf *hier* – statt 24 Phantom-Funde zu produzieren |
| **Deploy nur bei `healed=true` UND `pushed=true`** aus `.affiliate_integrity_state.json` | kein Deploy ohne echte Heilung, keine Heilung ohne Deploy |
| **Idempotente Issue-Pflege** (Marker `<!-- affiliate-integrity-daily -->`) | EIN offenes Issue pro Schadenslage: bei Rot aktualisieren, bei Grün **automatisch schließen**, Duplikate aufräumen – Schluss mit der Flut #76/#78/#95/#99/#137/#146 |
| **Issue unterscheidet Werkzeug- vs. Inhaltsschaden** | Bei Exit 2 steht die Handlungsanweisung (`--selftest`, Detektor an Hook anpassen) direkt im Issue |
| **Diagnose-Artefakt** bei Rot (Report + Zustand, 14 Tage) | Befund auch dann lesbar, wenn Log-Zip nicht erreichbar ist |
| Exit-Code als Step-Output (`0/1/2`) | Unterscheidbar im Log: grün / Inhaltsschaden / Werkzeugfehler |

### 2.6 Kollateralfund: dieselbe Fehlerklasse in `layout_audit.py`

Beim Aufräumen der Verify-Reports fiel auf, dass `layout_audit.py` an **zwei**
Stellen exakt denselben Fehler wie Defekt A hat – starre Zeichenketten gegen
minifiziertes HTML:

```python
re.finditer(r'href="([^"]+)"', text)      # sieht href=/go/gas/ NICHT
'<meta name="description"' not in text    # minifiziert: <meta name=description
```

`hugo --minify` gibt einfache Attributwerte ohne Quotes aus. Folge:

| Modus | interne Links geprüft | Befund |
|---|---|---|
| `hugo --quiet` (layout-ai.yml) | 1101 | grün |
| `hugo --minify` (deploy.yml!) | **108** | „Meta-Description fehlt auf 25 Seiten" – **false critical** |
| nach Härtung, beide Modi | **1236** | grün |

Das war kein Schönheitsfehler: die unsichtbaren 1128 Links sind überwiegend
genau die **unquotierten `/go/`-Affiliate-Links** – ein **false green** im
internen Link-Audit, dazu ein false critical, das bei jedem Lauf gegen einen
minifizierten Build ein rotes Issue provoziert hätte. Beide Muster sind jetzt
quote-tolerant; der Audit zählt in **beiden** Build-Modi identisch.

### 2.7 Konvergentes Schreiben – der tägliche Commit-Churn ist weg

Zweiter, unabhängig wirkender Hebel gegen die Dauer-Rot-Schleife: Der Report
trägt einen Zeitstempel und eine Build-Herkunftszeile (`public/ veraltet →
Hugo-Rebuild` vs. `public/ aktuell`). Beides ändert sich **jeden Lauf**, also
gab es täglich ein Git-Diff ohne inhaltliche Änderung → der Workflow
committet → `git_sync.sh` meldet Erfolg (`sync_ok()` greift auch bei „nichts
zu pushen") → `GEHEILT=true` → der Deploy-Trigger springt **ohne echte
Heilung** an und läuft in die 403.

Jetzt: Report und Zustand werden **nur bei inhaltlicher Änderung** geschrieben
(Vergleich ohne die flüchtigen Zeilen) – dasselbe „konvergent"-Prinzip, das
`deploy.yml` bereits dokumentiert. Gemessen:

| Lauf | Befund | Git-Diff |
|---|---|---|
| 1 | grün | Report neu geschrieben |
| 2 | grün | **keins** ✅ |
| 3 | grün (frischer Build, andere Build-Zeile) | **keins** ✅ |
| Schaden injiziert | 1 CTA defekt | geschrieben, **1 Artikel automatisch geheilt** |
| danach | grün | geschrieben (Heilung ausgewiesen) |
| danach ×2 | grün | **keins** ✅ |

Praktische Folge: **Die tägliche Wache läuft auch ohne den Workflow-Patch an
ruhigen Tagen grün** – kein Commit, kein Deploy-Trigger, keine 403, keine
Issue-Flut. Der Patch wird trotzdem gebraucht (Selftest-Stage, Issue-Hygiene,
`actions: write` für Heilungs-Tage).

### 2.8 `scripts/integrity_guard.py` – Signatur erweitert

Neu unter Siegel (FEST): `layouts/_partials/affiliate_anchor_attrs.html`,
`layouts/shortcodes/tarifvergleich.html`,
`layouts/shortcodes/einspartabelle.html`,
`scripts/affiliate_integrity_gate.py`. Begründung: Diese Dateien emittieren
bzw. beweisen die Affiliate-Links. Der Render-Hook (KRITISCH) deckt nur die
Markdown-Pipeline ab – die Shortcode-Pfade waren der blinde Fleck von
Defekt C. Lock neu signiert: **39 Dateien**, `INTEGRITY-REPORT.md` grün
(die vorher offene kritische Abweichung an `render-link.html` vom 01.09. ist
damit bewusst abgenommen und dokumentiert).

---

## 3. Beweise (lokal gegen echten Hugo-Build 0.164/0.165 extended)

**Selbsttest**

```
✅ AFFILIATE-INTEGRITY-SELFTEST bestanden (attribut-tolerante Anker-Erkennung
   inkl. ?subid=/Legacy/unminifiziert, rohe Partner-Links, AI1–AI3-Schadensbilder,
   Deduplikation, AI5-Gateway-Beweis, Selbstheilung, Build-Frische, Hook-Drift-Wächter).
```

**Bestand (echter Build, 25 Live-Artikel)**

```
🟢 Affiliate-Integrität bewiesen.
Geprüfte Live-Artikel: 25 · Struktur-Funde: 0 · Render-Funde: 0 · Registry-Routen: 19
Gerenderte Gateway-Links: 86 · rel=sponsored: 86 · affiliate_click: 86 · SubID: 86 · rohe Partner-Links: 0
```

**Schadens-Injektion + Selbstheilung (Kopie des Repos, 3 echte Schadensklassen)**

| Injiziert | Erkannt | Geheilt |
|---|---|---|
| Dangling-CTA (`[**Text**` ohne `](url)`, Vorfall 14.08.) | ✅ AI1 | CTA komplett neu generiert → `/go/dsl/` |
| nicht registrierter Key `/go/super-partner-xyz/` | ✅ AI2 (Markdown **und** HTML) | umgeroutet → `/go/haftpflicht/` (thematisch korrekt) |
| rohe Partner-URL `https://a.check24.net/…` im Fließtext | ✅ AI2 + AI4 (HTML) | umgeroutet → `/go/tagesgeld/` |

Danach: `exit 0`, Build automatisch erneuert, alle Beweise neu geführt.

**Fail-closed-Matrix**

| Szenario | Exit | Verhalten |
|---|---|---|
| Detektor simuliert blind (0 Anker trotz gültiger Markdown-Links) | **2** | „Detektor-Verdacht", 24 Phantom-Funde verworfen, **nichts** geheilt |
| `public/` veraltet + kein Hugo-Binary | **2** | „Render-Beweis nicht möglich" |
| `public/` veraltet + Hugo vorhanden | 0 | automatischer Rebuild, Beweis geführt |
| `public/` fehlt + `--no-build` | **2** | fail-closed |
| `publish_gate` ohne `public/` | – | **alle** Kandidaten blockiert, Klartext-Grund |
| `publish_gate`, nur 1 von 3 Kandidaten defekt | – | nur dieser eine blockiert (kein Sippenhaft-Verwurf) |

**Entparkung des zu Unrecht geblockten Artikels**

```
2026-08-26-handytarif-vergleichen-2026-guenstige-tarife
  vorher: state=hold, draft=true, cadence_grund="publish-gate: … nur 0 statt mind. 2 …"
  nachher: state=live, draft=false
  publish_gate.py --dry-run → 1 Kandidat, 0/1 scheitern ✅
```

---

## 4. Geänderte Dateien

| Datei | Änderung |
|---|---|
| `scripts/affiliate_integrity_gate.py` | **Version 2**: attribut-toleranter Beweis, AI5, `--selftest`, Drift-Wächter, fail-closed (Exit 2), Build-Frische, Umrouting-Heilung, Zustandsdatei, neuer Report |
| `layouts/_partials/affiliate_anchor_attrs.html` | **neu**: zentraler Attribut-Vertrag für Shortcode-CTAs (Defekt C) |
| `layouts/shortcodes/tarifvergleich.html` | CTA-Buttons (Tabelle + Karten) über das Partial → `rel=sponsored`, Umami, SubID |
| `layouts/shortcodes/einspartabelle.html` | dito (Tabellen-CTA + Summen-Karte) |
| `scripts/publish_gate.py` | fail-closed bei Werkzeugfehlern + Kandidaten-Filter + `--no-build` |
| `scripts/bestand_gate.py` | Auswertungsfehler = Exit 1 (vorher „sauber") |
| `patches/affiliate-integrity-premium-2026-09-02-workflows.patch`<br>`patches/affiliate-integrity-daily-2026-09-02-workflow-ready.yml` | **Workflow zum Einspielen** (`actions: write`, Selbsttest-Stage, präziser Deploy-Trigger, idempotente Issue-Pflege, Artefakt) – Agent-Token ohne `workflows`-Permission |
| `scripts/integrity_guard.py` + `data/integrity_lock.json` | Affiliate-emittierende Dateien unter Siegel, Lock neu signiert (39 Dateien) |
| `content/posts/2026-08-26-handytarif-vergleichen-2026-guenstige-tarife/index.md` | Phantom-Blockade aufgehoben (`park_state.release`) |
| `AFFILIATE-INTEGRITY-REPORT.md`, `BESTAND-REPORT.md`, `CADENCE-GATE-REPORT.md`, `INTEGRITY-REPORT.md` | auf echten (grünen) Stand gebracht |
| `scripts/layout_audit.py` | quote-tolerante `href`-/Meta-Description-Erkennung (Kollateralfund 2.6: false green + false critical bei minifiziertem Build) |
| `README.md`, `ANLEITUNG-CHECK24-LINKS.md`, `docs/PROFIBLOGGER-AFFILIATE-REPORT.md` | Doku: AI1–AI5, Selbsttest, fail-closed |

---

## 5. Warum das hält (nicht nur heute)

1. **Die Fehlerklasse ist abgestellt, nicht der Einzelfall.** Der Beweis
   hängt nicht mehr an Attribut-Reihenfolge/Quotes/Minifizierung. Neue
   Attribute am Hook (UTM, `data-*`, A/B-Tests) ändern am Beweis nichts.
2. **Wenn doch, sagt die Wache es selbst.** Selbsttest + Drift-Wächter +
   Massen-Blindheits-Erkennung verwandeln „still blind" in „laut rot mit
   Handlungsanweisung" – und zwar **bevor** geheilt/verworfen wird.
3. **Unbewiesen = unveröffentlicht.** Fail-closed auf allen drei Pfaden
   (tägliche Wache, `publish_gate`, `bestand_gate`).
4. **Ein Issue pro Schadenslage** – auto-schließend bei Grün. Kein
   Alarm-Müdigkeits-Effekt mehr, der echte Funde ertränkt.
5. **Beide Link-Pfade unter Vertrag und unter Siegel** (Markdown-Pipeline
   via Render-Hook, Shortcodes via Partial) – der blinde Fleck ist zu.
6. **Kein Commit-Churn mehr** (2.7): ruhige Tage produzieren kein Diff, also
   keinen Commit, keinen Deploy-Trigger und kein Issue. Die Wache meldet sich
   nur noch, wenn es wirklich etwas zu melden gibt.
7. **Die Lehre gilt repo-weit, nicht nur dieser Wache.** „Attribut-tolerant
   statt Zeichenketten-Vergleich" ist inzwischen auch in `layout_audit.py`
   umgesetzt (2.6). Faustregel für alle Gates: *geparste Attribut-Menge*
   prüfen, nie die *Zeichenreihenfolge* der Ausgabe – Minifizierung, Quotes
   und neue Attribute dürfen einen Beweis nicht kippen.

---

## 6. Betrieb

```bash
# täglich automatisch (06:00 MESZ) – Actions → „Affiliate-Integritäts-Wache (täglich)"
python3 scripts/affiliate_integrity_gate.py --selftest   # Detektor-Beweis
python3 scripts/affiliate_integrity_gate.py              # prüfen + sofort heilen
python3 scripts/affiliate_integrity_gate.py --dry-run --json
python3 scripts/affiliate_integrity_gate.py --slug <slug>  # Einzelartikel
```

**Nach jeder Änderung an `render-link.html`, an den CTA-Shortcodes oder am
Partial:** `--selftest` laufen lassen und (bei bewusster Änderung) den
Integrity-Lock neu signieren: `python3 scripts/integrity_guard.py --set-current`.

**Bei Exit 2 (Werkzeugfehler):** nicht am Content suchen – der Beweis konnte
nicht geführt werden. Reihenfolge: `--selftest` → Hugo-Build (`hugo
--minify`) → Drift-Wächter-Meldung im Report lesen.

_Täglicher Report: `AFFILIATE-INTEGRITY-REPORT.md` · Zustand:
`.affiliate_integrity_state.json` · Regelwerk: `QUALITAETS-REGELWERK.md` ·
Vertrag: `ANLEITUNG-CHECK24-LINKS.md`_

---

## 7. Was jetzt zu tun ist (einmalig, ~2 Minuten)

Die Skripte, das Partial, die Shortcodes, die Gates und der Integrity-Lock
sind **im Repo und wirksam**. Genau ein Punkt braucht deine Hand, weil GitHub
Agenten keine Workflow-Dateien schreiben lässt:

```bash
cd <repo>
git apply patches/affiliate-integrity-premium-2026-09-02-workflows.patch
git add .github/workflows/affiliate-integrity-daily.yml
git commit -m "ci(affiliate): Integritäts-Wache Premium (actions:write, Selftest, Issue-Pflege)"
git push
```

Danach einmal manuell prüfen: **Actions → „Affiliate-Integritäts-Wache
(täglich)" → Run workflow**. Erwartet: `Detektor-Selbsttest` ✅ →
`Hugo-Build` ✅ → Gate `🟢` (Exit 0) → „keine Änderungen" → **Lauf grün**.

Offene Alt-Issues dieser Wache (#76, #78, #95, #99, #137, #146) sind durch
diesen Fix gegenstandslos und können geschlossen werden; die neue
Issue-Pflege hält künftig pro Schadenslage genau ein Issue offen und
schließt es bei Grün selbst.
