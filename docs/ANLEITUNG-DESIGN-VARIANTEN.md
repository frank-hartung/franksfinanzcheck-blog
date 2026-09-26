# 🎛️ Design-Varianten-Werkbank – Runbook

**Stand:** 26.09.2026 · **Zweck:** Layoutvarianten entwerfen, messen und
freigeben, ohne dass jemals eine Maschine das Blogdesign austauscht.

---

## 1. Die Idee in fünf Sätzen

Eine KI ist gut darin, Layoutvarianten zu entwerfen und Messdaten
auszuwerten. Sie ist schlecht darin zu entscheiden, welches Design diese
Marke tragen soll. Also wird beides getrennt: Die Maschine baut Varianten
und misst sie gegen vorgegebene Budgets – Marke, Barrierefreiheit, SEO,
Performance, Conversion. Ein Mensch liest das Ergebnis und unterschreibt.
Ohne Unterschrift geht nichts live, und zwar nicht aus Höflichkeit,
sondern weil drei Wächter es technisch verhindern.

```
  Signal          Entwurf         Messung                Entscheidung
  ──────          ───────         ───────                ────────────
  Agent Reach  →  CSS-Variante →  Tier A  (HTML/DOM)  →  Mensch
  (nur lesend)    (nur Tokens)    Tier B  (Browser)      unterschreibt
                                  Lighthouse             im Register
                                       ↓                      ↓
                                  Gate bewertet    →    Produktionswache
                                  gegen Regelwerk        lässt es durch
```

---

## 2. Die Dateien

| Datei | Rolle |
|---|---|
| `data/design/regelwerk.yaml` | **Die Regeln.** Farben, Radien, Kontraste, Budgets, Conversion-Ziele, Freigabe-Bedingungen. Menschlich kuratiert. |
| `data/design/varianten.yaml` | **Das Register.** Jede Variante mit Hypothese, Herkunft, Status und Freigabe-Akte. Menschlich kuratiert. |
| `assets/css/varianten/<id>.css` | Das Varianten-Stylesheet. Liegt bewusst **nicht** in `extended/` (das wird immer ausgeliefert). |
| `layouts/_partials/design_variante.html` | Der Schalter. Ohne Parameter erzeugt er nichts. |
| `scripts/design_variant_gate.py` | Das Gate: Marke, Messvertrag, Freigabe, Produktionswache. |
| `scripts/design_variant_lab.py` | Die Werkbank: bauen + Tier A messen + Report. |
| `e2e/variant-metrics.mjs` | Tier B: Playwright (Kontrast/Tap/Fokus/CLS/LCP) + Lighthouse. |
| `scripts/design_reach_briefing.py` | Agent-Reach-Signale → Hypothesen-Vorschläge. |
| `lighthouserc.cjs` + `lighthouse/assertions.json` | LHCI; die Schwellen werden **aus dem Regelwerk erzeugt**. |

---

## 3. Der Ablauf – eine Variante von der Idee bis live

### Schritt 0 (optional): Signale holen

```bash
npm run design:briefing      # python3 scripts/design_reach_briefing.py
```

Schreibt `data/design/briefings/<datum>-design-hypothesen.md`: Signale aus
web.dev, Chrome Developers, Smashing, NN/g und GitHub, zugeordnet zu den
Themen aus `data/agent_reach/design_themenplan.yaml`. **Das ist ein
Vorschlag, keine Entscheidung** – Agent Reach läuft nur lesend und
schreibt weder CSS noch Register.

### Schritt 1: Eintrag im Register (von Hand)

```yaml
  - id: v-lesbarkeit-messweite
    titel: "Schmalere Messweite im Artikel"
    hypothese: >
      Was soll besser werden – und woran erkennt man es? Mit Messgröße
      und Abbruchkriterium. Unter 80 Zeichen meldet das Gate „zu dünn“.
    oberflaeche: ["artikel"]
    herkunft: "Figma-Entwurf / Relume-Muster / KI / Hand"
    status: entwurf
    css: "css/varianten/v-lesbarkeit-messweite.css"
    freigabe: { mensch: false, name: "", datum: "", kommentar: "" }
```

### Schritt 2: CSS schreiben

`assets/css/varianten/v-lesbarkeit-messweite.css` – Dateiname = ID.
Erlaubt ist nur, was `regelwerk.yaml → marke` zulässt: Token-Farben,
die Radius-Skala, die Schatten- und Easing-Skala. Verboten sind
`!important`, `@font-face`, externe URLs, `outline: none` und das
Animieren von Layout-Properties.

> **Warum kein `!important`?** Die Variante liegt ohnehin *nach* dem
> Basis-Stylesheet im `<head>` und gewinnt bei gleicher Spezifität.
> `!important` macht nur die Rückabwicklung unmöglich.

Sofort prüfen – das kostet zwei Sekunden und spart eine Messung:

```bash
python3 scripts/design_variant_gate.py --variante v-lesbarkeit-messweite
```

### Schritt 3: Bauen und messen

```bash
npm run design:lauf v-lesbarkeit-messweite     # Tier A (baut Basis + Variante)
npm run design:messen v-lesbarkeit-messweite   # Tier B (Browser + Lighthouse)
```

Tier A braucht nur Hugo (Sekunden). Tier B braucht Chromium:

```bash
npx playwright install chromium
npm i -D lighthouse        # nur nötig, wenn Lighthouse fehlt
```

Ergebnis: `.cache/design-varianten/<id>/messung.json` und der Vergleich
in `DESIGN-VARIANTEN-REPORT.md` (Lauf-Artefakt, gitignored).

### Schritt 4: Bewerten

```bash
npm run design:gate
```

Das Gate meldet je Befund `[Schwere/Besitzer]`:

* **P1** – blockiert (fehlende Freigabe, gekappte Messkette, SEO-Bruch)
* **P2** – blockiert (Budget gerissen, Markenverstoß)
* **P3** – sichtbar, blockiert nicht (Stilhinweise, **Bestandsbefunde**)

> **Bestand ≠ Regression.** Reißt schon die Basis ein Budget, wird das
> der Basis zugeschrieben (`bestand.*`, P3) und nicht der Variante. Ohne
> diese Trennung wandert ein alter Befund mit jeder neuen Variante mit
> und niemand behebt ihn je – die Fehlalarm-Klasse aus
> [Vorfall #343](INCIDENT-2026-09-21-layout-ai-fehlalarm-343.md).

### Schritt 5: Freigabe (nur Mensch)

Erst wenn Gate grün ist **und** alle drei Messebenen `ok` melden.
Zuerst die Messung als dauerhaften Beleg einfrieren:

```bash
python3 scripts/design_variant_lab.py --protokoll v-lesbarkeit-messweite
# → data/design/messungen/v-lesbarkeit-messweite-2026-10-04.json
```

Dann unterschreiben:

```yaml
    status: freigegeben
    freigabe:
      mensch: true
      name: "Frank Hartung"
      datum: "2026-10-04"
      messprotokoll: "design/messungen/v-lesbarkeit-messweite-2026-10-04.json"
      kommentar: "Messweite 68ch, Kontrast unverändert, LCP -40ms. Freigabe für 30 Tage."
```

Das Gate prüft: Name steht in `freigabe.berechtigte`, Datum ist gültig und
nicht in der Zukunft, alle drei Messungen liegen vor, die Freigabe ist
nicht älter als `gueltigkeit_tage` (30) – und das Protokoll existiert,
gehört zu dieser Variante und ist nicht jünger als die Unterschrift.

> **Warum ein Protokoll und nicht einfach der Cache?**
> Messungen entstehen in `.cache/design-varianten/` – gitignored und
> flüchtig. Läge der Beleg nur dort, wäre jede unterschriebene Variante
> nach dem nächsten frischen Checkout „freigegeben ohne Messung": ein P1
> in jedem CI-Lauf, den niemand verursacht hat und niemand beheben kann.
> Das Protokoll ist Teil des Repos und beantwortet die Frage „worauf
> gründet diese Freigabe?" mit Zahlen statt mit Erinnerung.

> **Warum verfällt eine Freigabe?** Weil der Blog weiterläuft. Eine
> Messung von vor acht Monaten beweist nichts über die Seite von heute.

### Schritt 6: Scharf schalten

Zwei Änderungen, die zusammenpassen müssen:

```yaml
# data/design/varianten.yaml
aktiv: "v-lesbarkeit-messweite"
# … und beim Eintrag:  status: live
```

```toml
# hugo.toml, [params]
designVariante = "v-lesbarkeit-messweite"
```

```bash
npm run design:wache     # muss BESTANDEN melden
```

Die Produktionswache läuft im Deploy vor dem Build. Sie verweigert:
eine Variante ohne Freigabe, eine unbekannte ID und jede Abweichung
zwischen `hugo.toml` und Register.

### Schritt 7: Zurückrollen

```toml
# hugo.toml
designVariante = ""
```

Register auf `aktiv: ""`, Status zurück auf `gemessen` oder `verworfen`.
Mehr ist nicht nötig – die Variante war additiv, die Basis lag immer
darunter.

---

## 4. Warum das Design so gebaut ist

**Der Schalter ist ein Parameter, kein Branch.**
Ein Design-Branch driftet nach zwei Wochen inhaltlich von `main` ab, und
man vergleicht Layouts, die unterschiedliche Artikel zeigen.
`HUGO_PARAMS_DESIGNVARIANTE=<id>` baut denselben Content zweimal.

**Das Varianten-CSS wird inline eingebettet, nicht per `<link>`.**
`head.html` bettet das Haupt-Stylesheet bewusst inline ein (CLS-Fix). Ein
nachgeladenes `<link>` käme nach dem ersten Paint an und würde genau den
Body-Shift erzeugen, den der Blog dort abgestellt hat – die Messung würde
dann die Ladeart bewerten statt das Layout. Kosten: exakt ein
zusätzliches `<head>`-Kind.

**Die Basis ist ein echter Register-Eintrag.**
Jede Messung braucht eine Kontrollgruppe aus demselben Lauf. `--lauf <id>`
baut deshalb immer auch `basis`.

**Zwei Messebenen, beide Pflicht.**
Tier A sieht das ausgelieferte HTML (DOM-Budget, SEO, Conversion-Bausteine,
Bytes) – schnell, überall lauffähig. Tier B sieht, was erst im Browser
entsteht (Kontrast, Tap-Ziele, Fokus, CLS/LCP, Lighthouse). Tier A allein
sieht keine Farbe; eine Freigabe darauf wäre Selbstbetrug.

**Fehlende Messung ist ein Zustand, kein Nichts.**
Ohne Chromium schreibt Tier B `status: "nicht_verfuegbar"` samt Grund.
Das Gate zählt die Ebene als fehlend und verweigert die Freigabe. Eine
Messung, die nicht sagt, dass sie nicht stattgefunden hat, ist schlimmer
als keine.

**Lighthouse-Schwellen werden erzeugt, nicht abgeschrieben.**
`lighthouse/assertions.json` entsteht aus dem Regelwerk
(`--lighthouse-export`). Das Gate meldet Drift. Zwei handgepflegte
Zahlensätze driften garantiert auseinander – unbemerkt, weil beide
„grün" melden.

**Conversion-Ziele schützen zuerst die Messkette.**
Ein `data-umami-event` weniger, und die Variante „gewinnt" jeden Test,
weil niemand mehr die Klicks sieht. Deshalb sind fehlende Umami-Events,
unvollständige Affiliate-`rel`-Attribute und verschwundene Pflicht-
Bausteine P1 – vor allen Geschmacksfragen.

---

## 5. Fallstricke (real passiert)

| Symptom | Ursache | Lösung |
|---|---|---|
| Varianten-Build hängt bei 0 % CPU, 300 s ohne Fortschritt | Zugriff auf `site.Data`/`hugo.Data` – Hugo parst den ganzen `data/`-Baum und stirbt an den `*.jsonl`-Protokollen | Register über `design_varianten_data.html` lesen (`os.ReadFile` + `transform.Unmarshal`) – wie `saisons_data.html` |
| Varianten-Build dauert 90 s statt 1,4 s | `partial` statt `partialCached` – der Registerabgleich lief auf jeder der 221 Seiten | `partialCached "design_variante.html" "design-variante"` |
| Gate klagt die Variante für einen Wert an, den die Basis auch hat | Budget ohne Basis-Vergleich | behoben: `_budget(..., basis_wert=…)`, Bestand → P3 auf `basis` |
| Briefing belegt eine A11y-Variante mit einem Token-Repository | Substring-Treffer: „aria" in „Vari**ables**" | behoben: Wortgrenzen in `_trifft()` |
| Gate meldet Verstöße, die nur im Kommentar stehen | CSS-Kommentare wurden mitgeprüft | behoben: `ohne_kommentare()` vor jeder Musterprüfung |
| `npx playwright install chromium` scheitert (ECONNRESET, `cdn.playwright.dev`) | Netz sperrt das Playwright-CDN | Repo-Fallback nutzen: `npm i --no-save @sparticuz/chromium lighthouse` – **beide in EINEM Befehl**, sonst räumt der zweite `--no-save`-Aufruf das Paket des ersten wieder weg |
| Basis-Budget gerissen, aber niemand meldet es | Die Variante wird (zu Recht) nicht angeklagt – und sonst prüfte niemand die Basis | behoben: `pruefe_bestand()` läuft über **alle drei** Messebenen, Befunde als P3 auf `basis` |
| Playwright meldet LCP 184 ms, Lighthouse 3110 ms | Ungedrosselt auf localhost vs. simulierte Drosselung – zwei verschiedene Messungen mit gleichem Namen | Die 2500-ms-Schwelle gilt nur für Lighthouse; der Playwright-Wert dient als Basis/Variante-Delta |
| Lighthouse misst mobil, obwohl `preset: 'desktop'` im Aufruf steht | Die Lighthouse-**Node-API** kennt `preset` nicht (CLI-Begriff) und ignoriert es stillschweigend | Echte Config-Objekte übergeben (`lighthouse/core/config/desktop-config.js`) und `formFactor` in die Messdatei schreiben |
| Lighthouse-LCP mobil weit über Budget, Bild aber optimal konfiguriert | `e2e/server.mjs` lieferte Text unkomprimiert, GitHub Pages liefert gzip/brotli – 190 KB statt 31 KB | behoben: Der Test-Server komprimiert jetzt wie Pages. LCP mobil 3179 → 1760 ms |

---

## 6. Befehle auf einen Blick

```bash
npm run design:liste        # Register + Messstand
npm run design:gate         # bewerten (Marke, Messung, Freigabe)
npm run design:wache        # Produktionswache (läuft im Deploy)
npm run design:lauf <id>    # bauen + Tier A messen
npm run design:messen <id>  # Tier B: Playwright + Lighthouse
python3 scripts/design_variant_lab.py --protokoll <id>   # Beleg für die Freigabe einfrieren
npm run design:briefing     # Agent-Reach-Signale → Hypothesen
npm run test:design         # 35 Regressionstests der Werkbank

python3 scripts/design_variant_gate.py --json            # maschinenlesbar
python3 scripts/design_variant_gate.py --lighthouse-export
python3 scripts/design_variant_gate.py --selftest
```

---

## 7. Grenzen – was diese Werkbank NICHT kann

* **Sie misst zwei Profile, und das ist Absicht.** Lighthouse läuft mobil
  (maßgeblich – Google bewertet Core Web Vitals überwiegend am mobilen
  Feld) und zusätzlich desktop. Der Unterschied ist bei diesem Blog nicht
  kosmetisch: LCP 1760 ms mobil gegen 573 ms desktop. Wer nur desktop
  misst, misst die Zahl, die ohnehin grün ist. Welches Profil eine Zahl
  erzeugt hat, steht in `messung.json` (`formFactor`, `cpu_faktor`,
  `netz_kbps`, `benchmark_index`) – eine Messung ohne Selbstauskunft ist
  deutbar und damit wertlos.
* **Sie misst keine echten Nutzer.** Tier B ist Labor. Ob die Hypothese
  stimmt, zeigt erst Umami über 14 Tage (`cta_click` je `slug`). Die
  Werkbank stellt nur sicher, dass eine Variante ausgeliefert werden
  *darf* – nicht, dass sie besser *ist*.
* **Sie ersetzt kein Auge.** Kontrast 4,6:1 kann messbar in Ordnung und
  trotzdem hässlich sein. Für die Gestaltungskritik gibt es
  `node e2e/design-shots.mjs` und die `impeccable`-Skill.
* **Sie kennt nur die Startseite im Detail.** CTA-Kette und
  Pflicht-Bausteine werden auf `/` geprüft, DOM/SEO über eine Stichprobe
  aus Startseite, Listen und drei Artikeln. Für eine Variante, die
  ausschließlich Artikel betrifft, gehört die Stichprobe in
  `design_variant_lab.stichprobe()` erweitert.

---

## 8. Verwandte Dokumente

* [`DESIGN.md`](../DESIGN.md) §9 – Varianten-Governance im Design-System
* [`docs/LAYOUT-AUTOMATISIERUNG.md`](LAYOUT-AUTOMATISIERUNG.md) – DOM-Budgets, dieselbe Quelle
* [`docs/ANLEITUNG-AGENT-REACH.md`](ANLEITUNG-AGENT-REACH.md) – Recherche-Kanäle und Leitplanken
* [`docs/ALARMROUTING-2026-09-12.md`](ALARMROUTING-2026-09-12.md) – Besitz/Schwere/Kanal je Befund (C14)
