# Content-Engine Kapazität Premium – Reparatur-Report (02.10.2026)

**Auftrag (Frank, Issue #521):** „Content-Engine: Tagesdefizit 2026-10-02
(0/2 LIVE) – Bitte dauerhaft auf Premium-Level einer Profi-Agentur beheben.“

„Dauerhaft“ heißt hier nicht: den Lauf wiederholen. Es heißt: den
Konstruktionsfehler finden, die Fehlerklasse mit einer Wache schließen und
belegen, dass sie geschlossen bleibt.

---

## Kurzfassung

Der 02.10.2026 war **kein Ausfall der Produktion**. Die Engine lief, rief
die Modelle, schrieb vier Artikel – und veröffentlichte null. Drei
unabhängige Konstruktionsfehler trafen zusammen, von denen jeder für sich
unauffällig blieb, weil **jede beteiligte Wache grün meldete**.

| # | Fehler | Wirkung am 02.10. |
|---|---|---|
| **D1** | Die Themen-Disposition war risikoblind: Sie gab YMYL-Themen an die Automatik, deren Artikel per Vertrag nie ohne Menschen live gehen | 2 von 4 Produktionen konnten gar nicht live gehen – Slot und Thema (180 Tage) verbrannt |
| **D1b** | Das Themen-Gedächtnis sperrte Themen für „produziert“, ohne zu prüfen, ob es den Artikel gibt | **47 von 63** Einträgen sperrten Themen für einen Artikel, der nicht existiert |
| **D2** | Pre-Flight und Disponent maßen „freie Themen“ mit **zwei verschiedenen Regeln** | Pre-Flight meldete `157 frei` und ließ grün starten – der Disponent fand **3** |
| **D3** | `parse_article` erkannte den Prompt-Kopf nur positionsgebunden | Prompt-Marker landeten in Artikeltext, Meta-Description **und** Pinterest-Text |

Der sichtbare Symptomwert „0/2 LIVE“ ist das Produkt aus D1 und D2. D1b war
der Grund, warum der Pool trotz 187 Themen faktisch leer war. D3 wurde bei
der Obduktion gefunden und war nur durch Zufall nicht live.

---

## Befund im Detail

### D1 – Die Quoten-Verbrennungsschleife

Die Engine wählte Themen über `reserve_topics.disponieren()`. Diese Funktion
kannte Dubletten und Cooldowns, aber **kein Risiko**. Sie griff deshalb
genauso bereitwillig zu „Reisekrankenversicherung“ wie zu „Strom sparen“.

Was dann passierte, war in sich vollkommen konsistent:

```
Thema ziehen (YMYL, ungefiltert)
  → LLM-Aufruf, Artikel entsteht
  → editorial_review_gate: Risiko „hoch“ → status „ausstehend“  (korrekt!)
  → Entwurf bleibt liegen, kann nie automatisch live gehen      (korrekt!)
  → merke(ok=True, "produziert: <slug>")  → 180 Tage Sperre     ← HIER
```

Der letzte Schritt ist der Fehler. Die Engine verbuchte eine
**Produktion** als Erfolg, obwohl das Ergebnis per Vertrag unveröffentlichbar
war. Das Thema war für ein halbes Jahr weg, der Slot war weg, der LLM-Aufruf
war bezahlt – und der Zähler „LIVE heute“ stand unverändert.

**Größenordnung:** 46 der 187 Themen sind YMYL-`hoch`. Elf der 20 damals
liegenden Entwürfe waren YMYL-`hoch`/`ausstehend`, der älteste vom
12.08.2026. Dieselbe Mechanik erklärt die neun historischen 1/2-Tage.

Das Gate ist dabei **nicht** der Schuldige. Es tat exakt, was es soll. Der
Fehler lag eine Etage höher: Niemand hatte der Disposition gesagt, dass es
zwei Arten von Themen gibt.

### D1b – Erfolgsmeldungen für Artikel, die es nicht gibt

Beim Nachrechnen fiel ein Thema auf: „Urlaubskasse clever aufbessern:
7 Tipps für mehr Reisebudget“ – Ledger-Eintrag `produziert:
so-bringst-du-deine-urlaubskasse-in-schwung…`, gesperrt bis 31.03.2027.
Der Slug existiert im Repository nicht.

Die systematische Prüfung ergab: **47 von 63** Ledger-Einträgen behaupteten
eine Produktion, zu der es keinen Artikel gibt. Ursache ist dieselbe
Buchführung wie in D1 – `merke(ok=True)` wird beim *Schreiben* des Entwurfs
gesetzt, nicht beim Veröffentlichen. Stirbt der Entwurf danach an einem Gate
oder wird er später entfernt, bleibt die Sperre stehen.

**Das war der eigentliche Grund für die leere Themen-Lage.** Nicht ein
erschöpfter Pool, sondern ein falsch verriegelter:

```
vor dem Abgleich:   frei disponierbar: AUTO  3 · FACHFREIGABE  0
nach dem Abgleich:  frei disponierbar: AUTO 37 · FACHFREIGABE 10
```

### D2 – Zwei Wahrheiten über dasselbe Wort

Der Pre-Flight (Phase 0) beantwortete die Frage „genug Themen?“ mit
`generate_drafts.topic_already_covered` – einer laxen 60-%-Token-Regel.
Der Disponent, der das Thema wirklich zieht, benutzte
`reserve_topics.disponieren` – Leitbegriff-Kollision plus
Cooldown-Gedächtnis.

Am Morgen des 02.10.2026 um dieselbe Minute:

| Messung | Ergebnis |
|---|---|
| `bot_preflight.check_topics()` | `187 Themen, 157 frei` → **grün** |
| `reserve_topics.disponieren(limit=999)` | **3** Themen |

Ein Faktor **52**. Eine grüne Lampe, die an einem anderen Kabel hängt als
die Maschine, ist schlimmer als gar keine Lampe: Sie erzeugt Vertrauen,
wo Aufmerksamkeit nötig wäre.

### D3 – Der Generator spricht mit sich selbst

Die Prompts verlangen das Ausgabeformat `TITLE:` / `DESCRIPTION:` /
Fließtext. `parse_article()` erkannte diesen Kopf nur, wenn „TITLE:“ exakt
auf Zeile 0 **und** „DESCRIPTION:“ exakt auf Zeile 1 stand. Die zweite
Bedingung war zugleich die **einzige** Stelle, an der der Body überhaupt vom
Kopf getrennt wurde.

Setzte das Modell eine Leerzeile dazwischen – am 02.10. real geschehen –,
fiel alles auf einmal aus:

```yaml
description:     "TITLE: Preiswert surfen: So findest du den optimalen DSL‑Anschluss …"
pin_description: "*Werbung | TITLE: Preiswert surfen: …"
```

und der Artikeltext begann mit `TITLE:`. Das sind Google-Snippet und
Pinterest-Pin, also genau die zwei Flächen, die nach außen gehen. Gestoppt
wurde der Entwurf nur zufällig von der Zeichenlängen-Prüfung. **Keine der
15 Textregeln (R2–R15) kannte dieses Muster, und keine einzige Regel sah
überhaupt ins Frontmatter** – `split_body()` schneidet es vorher ab.

---

## Die Reparatur

### 1. Zwei Bahnen statt einer Warteschlange (`scripts/engine_capacity.py`, neu)

Themen werden in zwei Bahnen getrennt:

| Bahn | Inhalt | Freigabe |
|---|---|---|
| **AUTO** | Alltagsthemen (141) | die Engine |
| **FACHFREIGABE** | YMYL / Hochrisiko (46) | ein Mensch |

Nur die AUTO-Bahn beantwortet „schaffen wir heute das Tagesziel?“.

Entscheidend ist, **wer** klassifiziert: `editorial_review_gate.classify_text()`
– dieselbe Funktion, die später den Artikel beurteilt. Es gibt keine zweite
Musterliste. Ein Test (`test_klassifikation_stammt_vom_redaktions_gate`)
verbietet, dass jemand die Muster kopiert.

Die Vorhersage ist bewusst **asymmetrisch konservativ**: Ein als `hoch`
erkanntes Thema kommt nie in die Quote; ein als `auto` eingestuftes Thema,
dessen fertiger Artikel sich doch als YMYL erweist, läuft weiterhin in das
fail-closed Gate. **Die Bahn ersetzt nie ein Gate** – sie verhindert nur,
dass ein Slot für etwas ausgegeben wird, das ihn nicht nutzen kann.

YMYL-Themen sind nicht verbannt, nur umgeleitet – sie laufen über
`redaktionelle-ymyl-pruefung.yml`. Die Fachbahn hat einen WIP-Deckel
(`YMYL_WIP_LIMIT`, Standard 3): Liegen mehr ungeprüfte Hochrisiko-Artikel
herum, schließt sie. Am 02.10. standen dort **11 von 3** – die Bahn war zu.
Die YMYL-Themen hätten also auch dann nicht ausweichen können, wenn die
Engine sie korrekt umgeleitet hätte. Das sagt der Report jetzt laut.

### 2. Ein Maß für „frei“ (`engine_capacity.lage()`)

`lage()` zählt freie Themen **ausschließlich** über `rt.disponieren` – es
gibt keine zweite Zählregel, die wieder auseinanderlaufen könnte. Das ist
die strukturelle Antwort auf D2, nicht nur eine korrigierte Zahl.

`bot_preflight.py` misst jetzt damit:

```
✅ Themenpool lesbar: 187 Themen, 157 frei (grobe Zählung)
✅ Kapazität: 37 frei disponierbare AUTO-Themen – Tagesziel 2 ist gedeckt (Puffer-Bedarf 6).
   AUTO-Bahn frei: 37 · FACHFREIGABE-Bahn frei: 10 (von 141 + 46 Themen)
   ℹ️ Fachfreigabe-Bahn geschlossen: 11 Hochrisiko-Artikel warten auf eine Fachfreigabe (Limit 3)
```

Die lax gezählten `157` stehen weiterhin da – aber ausdrücklich als
„grobe Zählung“ der Lesbarkeit, nicht mehr als Kapazitätsaussage.

**Der Pre-Flight bricht bei Engpass nie ab.** Ein leerer Themenpool heilt
nicht dadurch, dass die Engine stillsteht: Re-Queue-Beförderung und
Reserve-Veröffentlichung brauchen gar keine neuen Themen. Statt Exit 1 gibt
es `::warning::` im Actions-Log. Ein Test hält das fest
(`test_preflight_bricht_bei_engpass_nicht_ab`).

### 3. Abgleich gegen den echten Bestand (`reserve_topics.abgleich()`)

Jede Erfolgsmeldung wird gegen das Dateisystem geprüft. Fehlt der Artikel,
fällt die 180-Tage-Sperre.

Zwei Eigenschaften machen das sicher:

* **Der Dubletten-Schutz bleibt unberührt.** Der Abgleich hebt nur den
  *Cooldown* auf. Ob ein Thema schon belegt ist, entscheidet weiterhin
  `thema_kollision()` gegen den echten Bestand. Ein Thema ohne Artikel ist
  per Definition nicht belegt.
* **Keine Endlosschleife.** Ein einzelner Phantom-Eintrag ist ein
  Buchhaltungsfehler und wird nicht bestraft. Wiederholt er sich dreimal,
  ist es ein Thema, dessen Artikel immer wieder stirbt – dann greift die
  30-Tage-Sperre.

> **Falle, die beim Bauen zuschnappte und nicht wieder zuschnappen darf:**
> Das Ledger speichert den Slug **ohne** Datumspräfix
> (`hausratversicherung-optimieren-…`), auf der Platte liegt aber
> `content/posts/2026-10-02-hausratversicherung-optimieren-…/index.md`,
> gelegentlich mit `-2`-Suffix bei Titel-Dubletten. Die naive Prüfung
> `(posts_dir / slug).exists()` meldete **51 von 63** Einträgen als Phantom
> – darunter nachweislich existierende Artikel – und hätte den halben Pool
> grundlos entsperrt. Normalisierung steckt jetzt in `_bestands_slugs()`.

### 4. R16-PROMPT-ECHO – zwei Ebenen gegen D3

**Ebene Entstehung:** `parse_article()` ist positionsunabhängig. Es sammelt
Marker in einem Kopffenster unabhängig von Reihenfolge, Leerzeilen,
Code-Fences und `---`, entfernt Rest-Marker aus dem gesamten Body und lässt
niemals einen Marker in Titel oder Beschreibung.

**Ebene Wache:** Zwei neue Regeln, die Muster genau einmal in
`sprachkern.POLITUR_RUINEN` (SSOT, geteilt mit `write_verified`):

| Regel | prüft |
|---|---|
| `R16-PROMPT-ECHO` | Prompt-Marker im Fließtext |
| `R16-PROMPT-ECHO-META` | Prompt-Marker in `description`, `pin_description`, `kurzantwort`, … |

Beide sind **hart** in `textverstaendnis_guard.py` *und* `publish_gate.py`.

Beide Ebenen sind nötig: Der Parser kann wieder brechen, und Artikel
entstehen nicht nur über diesen einen Pfad.

#### Nebenbefund: eine Wache, die eine Blockade nur versprach

Beim Eintragen von R16 fiel auf, dass der Kopf des Textverständnis-Reports
seit dem 30.09. „**Harte Regeln (… R11–R15)**“ behauptete, die
`hard_rules`-Liste desselben Moduls diese Regeln aber **nicht enthielt**.
Der Guard dokumentierte eine Blockade, die er nie vollzog. Beide Listen
sind jetzt deckungsgleich, und ein Test vergleicht sie dauerhaft gegen die
Liste in `publish_gate.py` – zwei Wachen mit verschiedenen Regelsätzen sind
Issue #521 in klein.

### 5. Das Defizit-Issue nennt seine Ursache

Das alte Issue meldete „0/2 LIVE“ und verwies aufs Runbook – es stand so
ratlos da wie der Leser. `engine_issue._diagnose()` hängt jetzt die Lage an:
Bahn-Tabelle, Zustand der Fachfreigabe, wartende Prüfungen, die nächsten
freien Themen und drei Befehle zum Nachsehen. Fail-open: Eine kaputte
Diagnose darf den Alarm nie verschlucken.

### 6. Der vergiftete Entwurf vom 02.10.

`2026-10-02-preiswert-surfen-…` wurde mit **genau dem Parser** repariert,
der den Fehler künftig verhindert – nicht von Hand. Die ursprünglich vom
Modell geschriebene Beschreibung war intakt und wurde wiederhergestellt:

```diff
- description: "TITLE: Preiswert surfen: So findest du den optimalen DSL‑Anschluss für dein Zuhause So sparst du …"
+ description: "Entdecke, wie ein preiswerter DSL‑Anschluss funktioniert, welche Tarife 2026 sinnvoll sind und wie du beim Wechsel Geld sparst."
```

Dasselbe für `pin_description`; Marker und der Trenner `---` sind aus dem
Fließtext verschwunden.

---

## Belege

### Wirkung, gemessen

```
vorher:  ⚠️ Nur 3 frei disponierbare AUTO-Themen für ein Tagesziel von 2 (Puffer-Bedarf 6).
            Themen 187 = AUTO 141 + FACHFREIGABE 46
            frei disponierbar: AUTO 3 · FACHFREIGABE 0

nachher: ✅ 37 frei disponierbare AUTO-Themen – Tagesziel 2 ist gedeckt (Puffer-Bedarf 6).
            frei disponierbar: AUTO 37 · FACHFREIGABE 10
```

### Tests

| Lauf | Ergebnis |
|---|---|
| `python3 -m unittest discover -s scripts/tests` | **1271 Tests, OK** (22 übersprungen) |
| `npm run test:engine:kapazitaet` | Selbsttest + **20 Unit-Tests** grün |
| `npm run test:prompt:echo` | Selbsttest + **14 Unit-Tests** grün |
| `scripts/reserve_topics.py --selftest` | grün (9 Abschnitte, inkl. Bahn-Filter und Abgleich) |
| `scripts/textverstaendnis_guard.py --selftest` | grün (R2–R16) |
| `npx playwright test` | **97 Tests, alle grün** (desktop + mobile) |

Der Playwright-Lauf lief über den in `CLAUDE.md` dokumentierten Fallback
`@sparticuz/chromium`, weil `cdn.playwright.dev` in dieser Umgebung
blockiert ist; Hugo 0.164.0 (dieselbe Version wie in CI) kam aus der
PyPI-Distribution, da die GitHub-Release-Assets ebenfalls blockiert sind.

### Falsch-Positive: gegen den gesamten Bestand geprüft

R16 wurde über alle 87 Content-Dateien und alle Frontmatter-Felder
laufen gelassen. Treffer: **genau eine Datei** – der echte Schadensfall.
Deutsche Prosa-Doppelpunkte („Tipp:“, „Beispiel:“, „Faustregel:“,
„Achtung:“, „Fazit:“, „Hinweis:“, „Wichtig:“) bleiben unberührt; das ist
als Test festgeschrieben, weil ein Falsch-Positiv hier teurer wäre als der
Fehler selbst – es würde jede Veröffentlichung blockieren.

Das Nachziehen von R11–R15 in die harte Liste kostete **null** zusätzliche
Funde im Bestand.

### Selbstsabotage-Probe

Repo-Konvention: Ein Selbsttest muss rot werden, wenn man die Reparatur
entfernt. Beide Wege geprüft:

| Sabotage | Ergebnis |
|---|---|
| R16 aus `hard_rules` entfernt | `🛑 R16-PROMPT-ECHO fehlt in hard_rules – die Regel würde nur gemeldet, nicht blockiert` → Exit 2 |
| Frontmatter-Prüfung lahmgelegt | `🛑 R16-META: Prompt-Marker in description/pin_description nicht erkannt` → Exit 2 |

---

## Was bewusst **nicht** getan wurde

* **Das YMYL-Gate wurde nicht aufgeweicht.** Es hat sich am 02.10. korrekt
  verhalten. Die Reparatur liegt ausschließlich oberhalb davon, in der
  Disposition. Ein Gate, das man lockert, wenn die Zahlen nicht stimmen,
  ist kein Gate.
* **Kein Workflow wurde angefasst.** Agent-Tokens haben keine
  `workflows`-Berechtigung – die Reparatur ist deshalb bewusst so
  geschnitten, dass sie ohne eine einzige Änderung an `.github/workflows/`
  auskommt. Phase 0 ruft `bot_preflight.py` bereits auf.
* **Keine zweite Zahl erfunden.** Das Reserve-Ziel bleibt alleiniges
  Eigentum von `reserve_economy.py`. `engine_capacity` liest es, besitzt es
  nicht.
* **Die 47 Themen wurden nicht einfach entsperrt.** Sie wurden gegen den
  Bestand geprüft; der Dubletten-Schutz bleibt in voller Schärfe aktiv.
* **Der 02.10. wurde nicht nachträglich grün gerechnet.** Der Tag bleibt
  0/2. Repariert ist die Ursache, nicht die Statistik.

---

## Offen (kein Automatik-Thema)

Die Fachfreigabe-Bahn ist mit **11 wartenden Hochrisiko-Artikeln bei Limit 3**
weiterhin geschlossen. Das ist kein Defekt, sondern angesammelte
redaktionelle Arbeit – sie läuft über „Redaktionelle YMYL-Prüfqueue“ und ist
per Beschluss (C15) nicht automatisierbar. Solange dieser Stapel steht,
produziert die Engine ausschließlich aus der AUTO-Bahn. Mit 37 freien
Themen trägt die den Tagesbedarf.

---

## Bedienung

```bash
npm run engine:kapazitaet         # Lage in einem Blick (ohne Nebenwirkungen)
npm run engine:abgleich           # Phantom-Sperren lösen
npm run test:engine:kapazitaet    # Selbsttest + Unit-Tests
npm run test:prompt:echo          # R16-Wache
```

Anleitung für den Störfall: `docs/ANLEITUNG-ENGINE-KAPAZITAET.md`

---

## Geänderte Dateien

| Datei | Änderung |
|---|---|
| `scripts/engine_capacity.py` | **neu** – Bahn-Trennung, ehrliche Kapazität, WIP-Deckel |
| `scripts/reserve_topics.py` | `bahn`-Parameter für `disponieren()`, `abgleich()`, Bericht, 2 Selbsttest-Abschnitte |
| `scripts/bot_preflight.py` | `check_capacity()` – misst mit dem Maß des Disponenten, warnt statt abzubrechen |
| `scripts/engine_generate.py` | Themenwahl nur noch aus der AUTO-Bahn |
| `scripts/generate_drafts.py` | `parse_article()` positionsunabhängig und marker-sicher |
| `scripts/sprachkern.py` | `R16-PROMPT-ECHO` + `prompt_echo_im_feld()` (Muster-SSOT) |
| `scripts/textverstaendnis_guard.py` | `check_meta_prompt_echo()`, R11–R16 hart, Selbsttest |
| `scripts/publish_gate.py` | R16 in den harten Regeln |
| `scripts/engine_issue.py` | `_diagnose()` – das Defizit-Issue nennt die Ursache |
| `scripts/tests/test_engine_capacity.py` | **neu** – 20 Tests |
| `scripts/tests/test_prompt_echo.py` | **neu** – 14 Tests |
| `scripts/tests/test_reserve_pipeline.py` | Bahn-Verträge, Kollisionstest entkoppelt |
| `content/posts/2026-10-02-preiswert-surfen-…/index.md` | Prompt-Ruine repariert |
| `data/reserve-topic-ledger.json` | 47 Phantom-Sperren aufgelöst |
| `package.json` | 4 neue Skripte |
| `docs/ANLEITUNG-ENGINE-KAPAZITAET.md` | **neu** – Störfall-Anleitung |
