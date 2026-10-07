# Robustheit Premium – die Seite darf nie stumm sterben (Vertrag C31)

**Datum:** 07.10.2026
**Auftrag:** „Mache meinen gesamten Blog robuster gegen Fehleranfälligkeit auf
Premium-Level einer Profi-Agentur."
**Ergebnis:** Vier reale, stille Ausfälle geheilt, eine Resilienzschicht in zwei
Stufen eingezogen, der Service Worker fail-open gemacht und alles zusammen als
prüfbarer Vertrag R1–R13 hinterlegt – mit Wache, Selbsttest, 42 Unit-Tests und
21 Verhaltenstests im Browser-DOM.

---

## 1. Der Befund: zwei Fehlerklassen, nur eine war gedeckt

Dieser Blog hat ein ungewöhnlich dichtes Netz an Wachen: über 80 Workflows,
108 Unit-Test-Module, Gates für Kadenz, H1, Affiliate-Integrität, Index-Hygiene,
Design, Werkzeuge, Vergleichsgrundsätze. Alle prüfen dieselbe Frage: **Baut die
Seite richtig, und steht das Versprechen im ausgelieferten HTML?**

Die Gegenfrage war offen: **Was passiert, wenn ein Baustein im Browser stirbt?**
Diese Fehler sind unsichtbar für jedes Build-Gate, denn die Seite *baut*. Sie
passieren erst beim Leser – auf einem Gerät, in einem Modus, mit einer
Netzlage, die hier niemand nachstellt. Vier Fälle lagen am 07.10.2026 real im
Bestand.

### Befund 1 – Ein Rechner riss alle Rechner derselben Seite mit

`static/premium/ff-rechner.js`, Stand vor der Heilung:

```js
function initialisiere() {
  document.querySelectorAll('[data-ff-rechner]').forEach(function (container) {
    …
    var form = container.querySelector('form');
    if (!form) return;
    var rechnen = function () { rendere(typ, logik(werteLesen(container)), container); };
    form.addEventListener('submit', …);
    …
    rechnen();
  });
}
```

Kein `try`, kein `catch` – in der ganzen Datei nicht eines. Wirft ein einziger
Container (unerwartetes Markup, fremde Shortcode-Variante, ein geänderter
Ergebnis-Slot), bricht die Schleife ab: **alle folgenden Rechner derselben Seite
bleiben unverdrahtet.** Der Leser sieht ein Formular, drückt „Berechnen", die
Seite lädt neu (echter Submit statt `preventDefault`), keine Rechnung. Kein
Konsolenfehler, den jemand liest, kein Issue, kein Befund.

Zusatzbefund: `NodeList.forEach` ist nicht überall vorhanden; fehlte es, starb
der Baustein, bevor ein Horcher stand.

### Befund 2 – Die Anmeldung wartete unbegrenzt und schwieg

`static/premium/ff-newsletter.js`, `senden()`:

```js
if (button) button.disabled = true;
setzen('sendet', 'Wird übermittelt …');
window.fetch(ziel, { …, mode: 'no-cors', keepalive: true })
  .then(function () { …"Bestätigungsmail ausgelöst"… })
  .catch(function () { …"nicht durchgekommen"… });
```

`fetch` ohne Zeitlimit. Hängt der Worker (`abos.franksfinanzcheck.de`), kommt
weder `then` noch `catch`: Der Knopf bleibt `disabled`, die Zeile bleibt auf
„Wird übermittelt …" – **für immer**. Wiederholen unmöglich, abbrechen auch.
Der häufigste reale Ausfall eines Formulars ist nicht der Fehler, sondern das
Nicht-Antworten, und genau dafür gab es keinen Weg heraus.

Derselbe Befund in `ff-nl-praef.js` (zwei Worker-Aufrufe, beide ohne Limit) und
in `ff-feedback.js` (`keepalive`-Request ohne Begrenzung).

### Befund 3 – Der Service Worker konnte Requests verschlucken

`layouts/index.sw.js`, Stand vor der Heilung:

```js
async function cacheFirst(req) {
  const cache = await caches.open(CACHE);      // ← außerhalb jedes try/catch
  const hit = await cache.match(req);
  …
}
async function networkFirst(req) {
  const cache = await caches.open(CACHE);      // ← dasselbe
  …
  } catch (err) {
    const hit = await cache.match(req);
    if (hit) return hit;
    throw err;                                 // ← Offline-Seite des Browsers
  }
}
```

Der SW sitzt in **jedem** Request der Seite. Wirft das Cache-API – volle Quota,
privater Modus, abgeräumter Speicher, Firefox mit blockierter Storage-API –,
lehnt `respondWith` ab und der Request schlägt fehl, **obwohl er ohne den SW
problemlos durchgegangen wäre**. Ein Baustein, der die Seite beschleunigen soll,
wird so zur einzigen Komponente, die sie komplett ausfallen lassen kann – ohne
eine Zeile Protokoll.

Drei Lücken dazu: keine Offline-Antwort für Navigationen (der Leser sah die
Offline-Tafel des Browsers statt der Marke), keine Umgehung für
`Range`-Anfragen (das Cache-API bedient Teilantworten nicht zuverlässig – der
Grund, aus dem `.mp3` bewusst ungecacht bleibt, galt für den Rest nicht), und
`/sw.js` selbst lag im cache-first-Muster (`.js` ist in `ASSET_RE`): eine
zwischengespeicherte eigene Datei ist ein Update, das nicht mehr ankommt.

### Befund 4 – „copied!" vor der Antwort

`layouts/_partials/footer.html`, Kopier-Knopf:

```js
if ('clipboard' in navigator) {
  navigator.clipboard.writeText(codeblock.textContent);   // ← Promise, nicht abgewartet
  copyingDone();                                          // ← „copied!" sofort
  return;
}
…
copybutton.innerHTML = '{{- i18n "code_copy" }}';
…
} else if (codeblock.parentNode.parentNode.parentNode.parentNode.parentNode.nodeName == "TABLE") {
```

Drei Fehler in einem Baustein: Die Erfolgsmeldung kam **vor** der Antwort –
verweigert die Zwischenablage die Erlaubnis (Fokus verloren, unsicherer Kontext,
Safari ohne Nutzer-Geste), stand „copied!" am Knopf und ein nicht abgefangenes
Promise in der Konsole. Die fünfstufige Elternkette warf bei abweichendem
Markup einen `TypeError`, der die **ganze** Schleife beendete: EIN unerwarteter
Codeblock nahm ALLEN den Knopf. Und `innerHTML` für einen Übersetzungstext ist
dieselbe Technik, die das Anmelde-Skript zu Recht nicht benutzt
(`test_first_party_und_kein_tracking`).

### Befund 5 – Speicher ohne Fangnetz im Fuß

`layouts/_partials/footer.html`, Menü-Scroll:

```js
function restoreMenuScroll() {
  var scrollPosition = localStorage.getItem("menu-scroll-position");   // ← wirft
  …
requestAnimationFrame(function () {
  localStorage.setItem("menu-scroll-position", menu.scrollLeft);       // ← wirft je Frame
```

Safari privat, blockierte Cookies und volle Quota werfen bei **jedem** Zugriff.
Der erste Wurf beendete das Skript – und mit ihm alles, was darunter steht. Der
zweite kam bei jedem Scroll-Frame: ein Dauerfeuer in der Konsole und Frames, die
nie zu Ende liefen. Für eine Bequemlichkeit (Menü-Scroll-Position).

### Warum keine Wache das sehen konnte

| Wache | Was sie prüft | Warum sie hier blind ist |
|---|---|---|
| `h1_wache.py`, `offenlegung_gate.py`, `werkzeuge_gate.py` | gebautes HTML | Die Seite baut korrekt – der Ausfall ist zur Laufzeit |
| `dom_audit.py`, `layout_audit.py` | DOM-Budget, Links, Struktur | misst Markup, nicht Verhalten |
| `e2e/*.spec.mjs` | Verhalten im Browser | prüft den **Gutfall** auf Chromium mit Netz, Speicher und Erlaubnissen |
| `codeql.yml`, `integrity-lock.yml` | Sicherheit, Kern-Drift | finden kein fehlendes `catch` |

Genau deshalb ist die Heilung kein Patch an fünf Stellen, sondern ein Vertrag
mit eigener Wache: Ohne sie verschwindet jedes dieser Fangnetze beim nächsten
Umbau still – „unsichtbare Zusagen brauchen eine Wache" ist die Lehre, die
dieses Repo in `werkzeuge_gate.py` selbst aufschreibt.

---

## 2. Die Heilung: zwei Stufen, ein Vertrag

### Stufe 1 – Bootstrap im `<head>` (ohne neues Head-Kind)

`layouts/_partials/extend_head.html`, **im vorhandenen** Consent-Skript. Der
Ort ist nicht Geschmack, sondern Zwang:

* Fehler, die während des Parsens oder in den Inline-Skripten des Body
  passieren (Consent, Kopier-Knopf, Lese-Fortschritt), sind weg, bevor ein
  Skript am Fuß des Body horchen kann.
* Ein **eigenes** `<script>`-Tag wäre ein zusätzliches Head-Kind: 58 Kinder sind
  die Lighthouse-Messgrenze (`dom_audit.LIMIT.head_children`), Artikel-Seiten
  liegen bei 48–58. Repo-Regel: „Wer ein Tag ergänzt, nimmt ein anderes weg."
  Also teilt der Bootstrap sich das vorhandene Tag – und R2 friert die Zahl der
  `<script>`-Tags ein (8), damit niemand sie versehentlich erhöht.

Was er stellt: `melden()` (Ringpuffer 25, `ff:fehler`-Event, ab fünf Befunden
`data-ff-robust="belastet"`), `sicher()`, `error`-Horcher in der
**Capture-Phase** (Ressourcen-Fehler bubble'n nicht), `unhandledrejection`,
`offline`/`online`, und `hole()` – Fetch mit Zeitlimit, Wiederholung mit
Zittern, **der nie ablehnt**.

### Stufe 2 – Schicht am Fuß des Body

`static/premium/ff-robust.js`, geladen über `asset_url.html` (Cache-Busting
`?v=<SHA>`), ergänzt was Zeit hat: `insel()` (Fehlergrenze je Baustein),
`hinweis()` (`role="status"`), `ablage` (Web Storage mit Tab-Ersatz),
`zwischenablage()` (zwei Wege, ehrliche Antwort), `bereit()`, `bericht()`
(Diagnose, bleibt im Browser). Beide Stufen sind idempotent (`R.boot`), beide
first-party, keine sendet etwas nach außen.

### Die vier Vertragspunkte, die beim Bauen gelten

1. **Fangnetz je Instanz, nicht je Seite.** Ein kaputter Rechner darf die
   anderen sieben nicht mitreißen.
2. **Ein gefangener Fehler bekommt einen Satz.** `role="status"`, Marke, keine
   Technik: „Dieser Rechner konnte nicht gestartet werden. Der Ratgeber bleibt
   vollständig lesbar – die Rechnung steht als Formel im Text."
3. **Jeder Netzaufruf hat ein Zeitlimit** und gibt den Knopf wieder frei.
4. **`opaque` ist kein Fehler.** Die Anmeldung sendet bewusst `no-cors`
   (`test_kein_erfolgsversprechen` hält fest, dass sie deshalb nie einen Erfolg
   behauptet). Eine opaque Antwort heißt „durchgekommen, Inhalt nicht lesbar" –
   sie als Misserfolg zu deuten hieße, ehrliche Anmeldungen als Fehler zu
   melden. Wiederholt wird nur bei `netz`, nie bei `zeitlimit`: Ein Request, der
   ins Limit lief, hat den Dienst bereits beschäftigt.

---

## 3. Was sich geändert hat

| Datei | Heilung |
|---|---|
| `static/premium/ff-robust.js` **(neu)** | Resilienzschicht Stufe 2: Inseln, Speicher, Zwischenablage, Hinweis, Diagnose |
| `layouts/_partials/extend_head.html` | Bootstrap Stufe 1 im vorhandenen Head-Skript (Fehler-Horcher, `hole()`) |
| `layouts/_partials/deferred_scripts.html` | Einbindung der Schicht; SW-Registrierung meldet Fehlschläge und versucht **einmal** neu (Deploy-Fenster) |
| `layouts/index.sw.js` | fail-open (`fach()`), Offline-Fangnetz (`404.html`, Status 503), Range-Umgehung, `/sw.js` nie cache-first, `SKIP_WAITING`, Install/Aktivieren im Fangnetz |
| `static/premium/ff-rechner.js` | `verdrahten()` je Rechner im Fangnetz, Ausfall-Satz ins Ergebnisfeld, Rechnung selbst ebenfalls gefangen, `Array.prototype.forEach.call` |
| `static/premium/ff-newsletter.js` | Zeitlimit 15 s, ein Wiederholungsversuch, Doppelklick-Sperre, Knopf wird wieder freigegeben, `FormData`-Rückfall auf nativen POST |
| `static/premium/ff-nl-praef.js` | Zeitlimit 12/15 s und Wiederholung für beide Worker-Aufrufe |
| `static/premium/ff-feedback.js` | Zeitlimit 8 s, Doppelklick zählt einmal, `NodeList.forEach` ersetzt |
| `static/premium/ff-summary-safety.js` | `document.body`/`MutationObserver`-Prüfung, Fangnetz je Durchlauf, Leistungsschalter nach drei Fehlern |
| `layouts/_partials/footer.html` | Kopier-Knopf: Erfolg **nach** der Antwort, Rückfall `execCommand`, Fangnetz je Codeblock, `textContent`, `type="button"`; Menü-Scroll: Speicher im `try/catch` |
| `assets/css/extended/zz-robustheit.css` **(neu)** | `.ff-robust-hinweis` im Markenton, Dark-Variante, `overflow-wrap: anywhere`, keine Layout-Animation |
| `scripts/robustheits_gate.py` **(neu)** | Wache R1–R13, `--selftest` (14 Sabotage-Proben, 4 Gegenproben), `--source-only`, `--public`, `--json`, `--strict` |
| `scripts/tests/test_robustheits_gate.py` **(neu)** | 33 Regressionstests inkl. Aufruf-Vertrag und CI-Verdrahtung |
| `tools/robust.test.mjs` **(neu)** | 21 Verhaltenstests im jsdom (Fehler-Horcher, Zeitlimit, Wiederholung, Speicher, Inseln, Zwischenablage, offline) |
| `data/robustheit_ausnahmen.yaml` **(neu)** | Begründete Ausnahmen mit Entscheidung und **Fälligkeit** |
| `.github/workflows/robustheit.yml` **(neu)** | Push/PR auf Laufzeit-Pfade, jede Nacht 04:35 UTC, Build + gebaute Wahrheit + Uhr-Probe der Fristen |
| `.github/workflows/deploy.yml` | Robustheits-Prüfung **vor** dem Build, fail-closed |
| `package.json` | `robustheit`, `robustheit:check`, `robustheit:strict`, `robustheit:ausnahmen`, `test:robustheit` |
| `CLAUDE.md` | Abschnitt C31 + drei Zeilen in der Test-Pipeline |
| `docs/ANLEITUNG-ROBUSTHEIT.md` **(neu)** | Runbook: Stufen, Fetch-Vertrag, Regeln, Checkliste für neue Bausteine, Ausnahmen, Diagnose |

**Bewusst nicht angefasst:** `layouts/_partials/head.html` (KRITISCH-versiegelt)
und `layouts/_partials/extend_footer.html` (KRITISCH-versiegelt). Der nackte
`localStorage`-Zugriff in `head.html` stammt aus dem PaperMod-Erbe und sein
Zweig ist durch `disableThemeToggle = true` tot – er wird nicht gerendert. Er
steht als begründete Ausnahme (R8, fällig 2027-04-07) in
`data/robustheit_ausnahmen.yaml`, statt die Wache dauerhaft rot zu machen: Eine
Wache, die nur Fehlalarme liefert, wird abgeschaltet (Issue #338).

`layouts/index.sw.js` ist Klasse **FEST**: Die Änderung wird im selben Commit
mit dem Integritäts-Lock signiert (`integrity_guard.py --heal`).

---

## 4. Beweis

Ausgeführt am 07.10.2026 in der Arbeitskopie (Node 22.22.3, Python 3.11.2,
jsdom 30):

```
$ python3 scripts/robustheits_gate.py --selftest
✅ SELBSTTEST OK – 14 Sabotage-Proben erkannt, 4 Gegenproben freigegeben, echter Stand grün

$ python3 scripts/robustheits_gate.py --source-only --strict --no-report ; echo $?
0

$ python3 -m unittest scripts.tests.test_robustheits_gate
Ran 42 tests in 17.8s
OK

$ node --test tools/robust.test.mjs
# tests 21 · # pass 21 · # fail 0
```

**Der Selbsttest ist der Beweis, dass die Wache nicht nur grün ist.** 14
Sabotagen an den echten Dateien, jede muss ihre Regel auslösen: Cache-Öffnung
ohne Fangnetz (R5), Offline-Seite aus `PRECACHE` entfernt (R5), Range-Umgehung
gelöscht (R5), `SKIP_WAITING` umbenannt (R5), Bootstrap in ein eigenes
Head-Skript verschoben (R2), Capture-Phase entfernt (R2), Fetch ohne Zeitlimit
(R4), dynamisches `innerHTML` (R7), `document.write` (R7), Speicherzugriff ohne
`try/catch` (R8), Schicht nicht mehr eingebunden (R12), Dark-Variante des
Hinweises gelöscht (R9), Insel-Fangnetz entfernt (R6), API-Baustein umbenannt
(R1), Ausnahme-Frist innerhalb des Uhr-Proben-Horizonts (R13). Dazu vier
Gegenproben, die **nicht** anschlagen dürfen: statisches `innerHTML`-Literal,
ein Fetch mit Zeitlimit, End-Tags in gültigen aber ungebräuchlichen
Schreibweisen (`</script >`, `</script data-ff="1">`) und eine weite, aber
begrenzte Frist – sonst ist das Gate schärfer als der Vertrag (oder blind) und
wird abgeschaltet.

### Der Beweislauf fand einen Befund – in der Wache selbst, in zwei Runden

Der CodeQL-Lauf des Pull Requests (#633) meldete eine Security-Fundstelle. Sie
lag nicht im Blog, sondern im neuen Gate:

```
py/bad-tag-filter → scripts/robustheits_gate.py:187
This regular expression does not match script end tags like </script >.
```

Der Schnitt, der die `<script>`-Blöcke aus `extend_head.html` holt, endete auf
`</script>` und passte damit nicht auf `</script >`. Die Folge ist genau die
Fehlerklasse, die dieser Vorgang abschaffen soll: Trägt ein Template je ein
End-Tag in einer Schreibweise, die der Schnitt nicht kennt, sieht das Gate den
Block nicht, findet also weder Bootstrap noch Consent darin – und meldet
**grün, ohne geprüft zu haben**. Derselbe blinde Schnitt lag im Helfer von
`tools/robust.test.mjs`: Gate und Test wären zusammen blind gewesen.

**Runde 1** heilte mit `</script\s*>`. **CodeQL blieb rot – und hatte recht:**

```
py/bad-tag-filter → scripts/robustheits_gate.py:195
This regular expression does not match script end tags like </script\t\n bar>.
```

Ein End-Tag darf auch Attribute tragen (`</script data-ff="1">`); Parser
ignorieren sie, gültig ist die Schreibweise trotzdem. **Runde 2** heilt mit
`</script[^>]*>` – alles bis zur Klammer, im Gate *und* im Test-Helfer.

Der Beweis, dass die Heilung hält und nicht nur der Befund verschwindet:

* **Gegenprobe 3** im Selbsttest, je Schreibweise (`</script >`,
  `</script\n  data-ff="1">`, `</script\t>`) in zwei Hälften: Gültige End-Tags
  allein dürfen **keinen** Befund erzeugen – sonst ist das Gate schärfer als
  HTML und wird abgeschaltet. Und mit ihnen muss R2 **weiter anschlagen**, wenn
  der Bootstrap doch ein eigenes Head-Kind bekommt – sonst ist der Schnitt
  blind, während das Gate grün meldet.
* **Zähne zweifach nachgewiesen.** Mit dem blinden Muster `</script>` fällt der
  Selbsttest (`Gegenprobe 3a ('</script >')`), und mit der Halbheilung
  `</script\s*>` fällt er ebenfalls (`Gegenprobe 3a ('</script\n data-ff="1">')`).
  Eine Gegenprobe, die nie fehlschlägt, beweist nichts.
* 6 Unit-Tests (`SchnittTests`, darunter `</script foo="bar">` und die
  Dateninsel mit `type=`) und 1 jsdom-Test, der die Blockzahl am echten Bestand
  einfriert.

### Die Uhr-Probe fand eine Zeitbombe – in der Ausnahme dieses Vorgangs

Der zweite rote Lauf kam nicht von CodeQL, sondern von der Uhr-Probe der CI
(`publication-reliability-tests.yml` lässt die ganze Suite ein zweites Mal mit
einer um **97 Tage** vorgestellten Uhr laufen). Sie fand genau das, wovor
`scripts/selftest_clock.py` seit dem 18.09.2026 warnt – in meinem eigenen Test:

`test_ausnahmen_sind_begruendet_und_faellig` maß die Frist der
`head.html`-Ausnahme (`faellig: 2027-01-07`) gegen `date.today()`. Unter der
vorgestellten Uhr (12.01.2027) schlug `assertGreaterEqual(date(2027, 1, 7),
heute)` fehl. Die Suite wäre ab dem Stichtag **jeden Tag rot** geworden, ohne
eine einzige Code-Änderung. Ein Test, der die Wanduhr liest, ist keine Prüfung,
sondern eine Verabredung mit dem Kalender.

Heilung in vier Teilen:

1. **R13 FRISTEN** im Gate: Jede Ausnahme nennt Entscheidungsdatum und Frist,
   gemessen wird die **Spanne zwischen beiden** – nie gegen heute. Sie muss
   jenseits des Uhr-Proben-Horizonts liegen (≥ 97 Tage) und innerhalb der
   Obergrenze (≤ 730 Tage, denn ein Termin auf irgendwann ist keine Frist).
2. **Frist** der Ausnahme auf `2027-04-07` gesetzt (sechs Monate), mit dem
   Horizont als Begründung in `data/robustheit_ausnahmen.yaml` selbst.
3. **Abgelaufen heißt sichtbar, nicht rot.** Eine Frist, die im echten Leben
   verstreicht, steht im Bericht (`⚠️ ÜBERFÄLLIG seit N Tagen`) und als
   `::warning` im Laufprotokoll – den Exit-Code färbt sie nicht. Vorbild ist
   `fristen_check.py`: „Exit 0 = Lauf ok (auch bei überfälligen Fristen – die
   Eskalation läuft über eigene Issues, nicht über rote Runs."
4. **Die Uhr-Probe läuft jetzt auch im Robustheits-Lauf.** Eine Änderung an
   `data/robustheit_ausnahmen.yaml` löst die Regressionssuite nicht aus (sie
   wacht auf `content/`, `scripts/`, `.github/workflows/`), also hätte niemand
   die nächste kurze Frist gemerkt. Lokal bewiesen:
   `selftest_clock.py --trap-modul scripts.tests.test_robustheits_gate --offset 97`
   → 42 Tests grün unter fremder Uhr; das Gate-Selbsttest ebenso.

Dazu prüft sich der Test selbst: `test_dieser_test_liest_nicht_die_wanduhr`
verbietet Uhr-Zugriffe im Testmodul – die verbotenen Muster sind aus Einzelteilen
zusammengesetzt, damit der Test nicht sein eigenes Verbot in seinem eigenen
Quelltext findet.

Nebenbefund, ebenfalls im Berichtsweg: Der rote Bericht des Gates nannte statt
des Regel-Titels das Funktionsobjekt (`## ✗ R13 – <function pruefe_fristen …>`) –
`bericht()` entpackte das Regel-Tripel in der falschen Reihenfolge. Wer einen
roten Bericht liest, braucht den Titel der Regel, nicht ihre Speicheradresse.

**Bestand unverändert grün** (Regression gegen dieselben Wachen wie vorher):

```
$ node scripts/ff_heading_glyph_guard_test.mjs     48/48 Prüfungen bestanden
$ node scripts/ff_toc_beweglich_test.mjs           17/17 Prüfungen bestanden
$ python3 scripts/mini_toc_premium_guard.py --selftest   6/6 Sabotage-Proben erkannt
$ python3 scripts/h1_wache.py --source-only        ✅ jede Seite trägt genau eine H1
$ python3 -m unittest scripts.tests.test_newsletter_site   Ran 45 tests … OK
$ python3 -m unittest scripts.tests.test_workflow_yaml     Ran 7 tests … OK
$ python3 scripts/actions_version_guard.py --gate  ✅ Keine Drift
$ node --test tools/                               ff-rechner 5/5 · cockpit 5/5 · werkzeuge 55/55 · seo-cockpit 9/9
```

**Voller Unit-Test-Lauf, vorher/nachher** (108 Module, `python3 -m unittest
scripts.tests.<modul>` je Datei):

| | vorher | nachher |
|---|---|---|
| PASS | 93 | 94 |
| FAIL | 14 | 14 |

Die 14 Fehlschläge sind vorbestehend und umweltbedingt (fehlender Hugo-Build,
fehlende generierte Daten wie `data/newsletter_kadenz.json`, Netzwerkzugriffe im
Prüf-Container). Kein Modul, das vorher grün war, ist jetzt rot. Das neu
gekommene grüne Modul ist `test_robustheits_gate`. `test_integrity_guard`
meldete zwischenzeitlich den erwarteten FEST-Drift auf `layouts/index.sw.js`
und ist nach der Signatur im selben Commit wieder grün.

**Nicht ausgeführt (ehrlich benannt):** `hugo` steht im Prüf-Container nicht zur
Verfügung (Hugo Extended 0.164, Download außerhalb der erlaubten Quellen). Der
Modus `--public public` – Bootstrap im gebauten HTML, gehärteter `sw.js`, keine
Hugo-Platzhalter – läuft deshalb in `robustheit.yml` und im Deploy, nicht hier.
Die Playwright-Suiten (`npm run test:e2e`) brauchen Browser-Binaries und liefen
ebenfalls nicht; die geänderten Pfade sind verhaltensgleich im Gutfall
(dieselben Selektoren, dieselben Meldungstexte), neu ist nur der Ausfallweg.

---

## 5. Was die Wache dauerhaft hält

| Regel | Zusage |
|---|---|
| R1 | Die Schicht existiert, trägt die API (`insel`, `ablage`, `zwischenablage`, `bericht`, `melden`, `sicher`, `bereit`) – geprüft gegen den Code **ohne** Kommentare |
| R2 | Der Horcher sitzt im `<head>`, im vorhandenen Skript; die Zahl der `<script>`-Tags ist eingefroren |
| R3 | Beide Stufen sind idempotent (`R.boot`), ein `unhandledrejection`-Horcher je Stufe |
| R4 | Jeder Fetch der Erstparteienskripte hat `hole`/`AbortController`/`zeitlimit` in Reichweite; `prefetch(` ist kein Fetch |
| R5 | Service Worker: fail-open, Offline-Fangnetz, Range-Umgehung, Eigendatei-Ausnahme, `SKIP_WAITING`, `catch` in beiden Strategien |
| R6 | Sechs benannte Bausteine tragen ihr Fangnetz und einen angekündigten Satz |
| R7 | `innerHTML` nur aus statischem Literal oder statischer Konstante; nie `document.write`, `eval()`, `insertAdjacentHTML`, `outerHTML =` |
| R8 | Jeder Web-Storage-Zugriff liegt im `try/catch` |
| R9 | Der Hinweis ist gestylt, dunkeltauglich, ohne Layout-Animation, `role="status"` |
| R10 | Jedes Erstparteienskript und der SW sind parsebar (`node --check`) |
| R11 | Schicht und Bootstrap nennen keine fremde Domain |
| R12 | Die Schicht läuft genau einmal, mit Cache-Busting |
| R13 | Jede Ausnahme ist datiert, und ihre Frist liegt jenseits des Uhr-Proben-Horizonts (≥ 97 Tage) und innerhalb der Obergrenze (≤ 730 Tage) – gemessen gegen die Daten, nie gegen die Wanduhr |

Das Gate heilt nie selbst. Ein Fangnetz, das sich selbst wieder einhängt, wäre
keines.

---

## 6. Was offen bleibt

1. **`head.html` (KRITISCH).** Vier nackte `localStorage`-Zugriffe im toten
   Theme-Zweig. Heilung braucht eine menschliche Signatur
   (`integrity_guard.py --set-current`); Ausnahme R8 ist auf **2027-04-07**
   befristet, der Unit-Test meldet Überfälligkeit rot.
2. **Fehlertelemetrie ist bewusst keine eingebaut.** `bericht()` bleibt im
   Browser, es gibt kein Fehler-Backend. Für einen Betrieb mit mehreren
   Hundert Artikeln pro Quartal wäre ein eigener, first-party Sammler (z. B.
   auf dem vorhandenen Cloudflare Worker) der nächste Schritt – er braucht eine
   Datenschutz-Entscheidung und einen Eintrag in die Datenschutzerklärung, also
   einen Menschen.
3. **`e2e/robustheit.spec.mjs` fehlt.** Die Verhaltenstests laufen im jsdom.
   Ein Playwright-Spezifikationslauf mit abgeschaltetem Netz, blockiertem
   Storage und verweigerter Zwischenablage würde die Ausfallwege im echten
   Browser beweisen – das ist die natürliche nächste Ausbaustufe, sobald die
   Browser-Binaries im Lauf verfügbar sind.
4. **Alte Browser ohne `AbortController`** bekommen den schlichten Fetch: kein
   Zeitlimit, aber auch kein Absturz. Derselbe Zustand wie vorher, nie ein
   schlechterer.

---

**Runbook:** `docs/ANLEITUNG-ROBUSTHEIT.md`
**Leitfaden:** `CLAUDE.md`, Abschnitt „Die Seite darf nie stumm sterben (C31)"
**Wache:** `scripts/robustheits_gate.py` · **Lauf:** `.github/workflows/robustheit.yml`
