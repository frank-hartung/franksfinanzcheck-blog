# Veröffentlichung WF-54C4 · #666 – Dauerheilung

**Datum:** 08.10.2026
**Auslöser:** Der Deploy-Lauf **37815234124** auf `main` (Commit `e894426` = `e8944266`,
„feat(ki-assistent): Free LLM Chat-Widget auf Premium-Level (#663)“) scheiterte im
Job **deploy** am Schritt **„Robustheit – Laufzeit-Fangnetze (fail-closed)“**. Der
Auto-Alert meldete das als Issue **#666** (`auto-report`, Alert-Key `WF-54C4`,
Bereich *Veröffentlichung*). Die Check-Run-Annotation nennt als Ursache
`Process completed with exit code 1`; die Log-Datei selbst war aus dieser
Umgebung nicht abrufbar. Der Befund wurde deshalb lokal reproduziert.

## Befund

### 1. Das Robustheits-Gate meldet zwei echte Verstöße im Widget

`python3 scripts/robustheits_gate.py --source-only --strict` (Vertrag C31):

| Regel | Stelle | Verstoß |
|---|---|---|
| **R4** Zeitlimit | `static/premium/ki-assistent.js:160` | `fetch()` ohne Zeitlimit – ein hängender Worker friert den Chat ein |
| **R7** Markup | `static/premium/ki-assistent.js:78` | `el.innerHTML = text` – Bot-Antworten gehen über `innerHTML` |

Der Code ist durch `escapeHtml` im Ergebnis zwar sicher, aber die Regel verlangt
die **strukturelle** Garantie (kein `innerHTML` mit berechnetem Inhalt). Das Gate
kann diese Unterscheidung nicht treffen und wertet den Schreibvorgang.

### 2. Der Selbsttest ist rot – aber nicht, weil das Gate kaputt ist

`--selftest` meldete „Fall0 sauberer Stand meldet Funde“ sowie zwei Gegenproben
(„statisches innerHTML-Literal wird zu Unrecht gemeldet“, „`</script >` erzeugt
Befunde“). Die Gegenproben prüfen „irgendein R7-Befund“ bzw. „irgendein Befund“
auf einer Kopie des **echten** Baums – der Verstoß aus Befund 1 löste sie also
aus. Nach der Heilung ist der Selbsttest grün, inklusive aller 14 Sabotage- und
4 Gegenproben. Das Gate war in Ordnung; die Datei war es nicht.

### 3. Hinter dem Gate: ein Build-Abbruch auf `/404`

Nach der Heilung von 1 bricht der **Build** (der im Deploy auf den Robustheits-
Schritt folgt) an einer zweiten Stelle ab:

    render of "/404" failed: … ki_assistent.html:12:18: executing … at <.File>:
    File is nil

`layouts/_partials/ki_assistent.html` läuft global über `baseof.html` – also auch
auf Seiten **ohne Quelldatei** (404, generierte Seiten). `.File.BaseFileName` ist
dort nil. Dieselbe Stelle wäre also nach jedem gelösten Gate als nächster
Deploy-Killer aufgetaucht.

### 4. Das Widget wäre ohne Endpoint auf jeder Seite kaputt gegangen

`hugo.toml` setzt `kiAssistentEndpoint` nicht (KA1-Warnung). Die Doku
(`docs/ANLEITUNG-KI-ASSISTENT.md` 4.3) sieht vor, den Endpoint **nach** dem
Worker-Deploy zu setzen. Bis dahin hätte das Widget auf jeder Seite einen Knopf
gezeigt, dessen Anfrage per `fetch("")` an die eigene Seite geht und immer
„nicht erreichbar“ meldet. Der Deploy ist seit diesem Commit rot, also ist dies
der erste Stand, den Leser sehen würden.

### 5. Das Zeitlimit muss die Worker-Kette abdecken

`cloudflare/ki-assistent/worker.js` probiert vier Provider **nacheinander** mit je
30 s Timeout (`AbortSignal.timeout(30_000)`). Ein Client-Limit unter 120 s würde
erfolgreiche Failover-Antworten abschneiden.

## Dauerhafte Reparatur

1. **Widget ohne Fangnetz-Verstoß (R4, R7).** `static/premium/ki-assistent.js`:
   - Bot-Antworten werden per DOM gebaut (`renderAnswer` / `inlineNodes`):
     Absätze, Zeilenumbrüche, Listen, **fett**, *kursiv*, `code` – jeder Teil als
     `textContent` bzw. eigenes Element. Kein `innerHTML`, `escapeHtml` und
     `formatAnswer` entfallen.
   - Der Typing-Indikator wird ohne `innerHTML` aufgebaut.
   - `fetch` läuft mit `AbortController` und Zeitlimit **130 s**
     (`ANTWORT_ZEITLIMIT_MS`, = 4 Provider × 30 s + Puffer), das in `finally`
     wieder gelöst wird. Bei Abbruch steht da: „Der Assistent hat zu lange
     gebraucht …“ – nicht die Verbindungs-Meldung.
2. **Build-Sicherheit auf allen Seiten.** `ki_assistent.html` liest `.File` nur
   noch innerhalb von `with .File` und fällt sonst auf „seite“ zurück.
3. **Kein Widget ohne Backend.** Die globale Partial rendert nur, wenn
   `kiAssistentEndpoint` (oder der Shortcode-Endpoint) gesetzt ist. Sobald der
   Endpoint in `hugo.toml` steht, erscheint das Widget ohne weitere Änderung.
   Geprüft: mit Override-Endpoint erscheint es auf 84 Seiten, ohne bleibt es aus.
4. **Regressions-Test gegen das Verhalten** – `tools/ki-assistent.test.mjs`
   (jsdom, 5 Tests):
   - Quelle: kein `innerHTML`-Schreiben, `fetch` mit Signal, Zeitlimit wird gelöst;
   - Markup in einer Antwort bleibt Text (`<img onerror>` wird nicht eingebaut);
   - normale Antworten werden als Absatz mit Zeilenumbruch gerendert;
   - Zeitlimit: Signal bricht den Request ab, klare Meldung, Senden wieder frei;
   - Netzfehler bleibt bei der Verbindungs-Meldung.
   Der Test ist in `robustheit.yml` (Schritt „Resilienzschicht … testen“) und in
   `package.json` (`test:robustheit`) eingebunden. Gegen die **alte** Datei
   schlagen 2 der 5 Tests fehl (Quelle und Zeitlimit) – er erkennt den Fehler.
5. **Doku.** `docs/ANLEITUNG-KI-ASSISTENT.md` (4.3): Verhalten ohne Endpoint,
   Zeitlimit und Kopplung an die Provider-Liste.

## Nachweis

Alles lokal in dieser Umgebung (Hugo 0.164.0 Extended, Node 22, Python 3.11):

* `robustheits_gate.py --selftest` → **grün** („14 Sabotage-Proben, 4 Gegenproben“).
* `robustheits_gate.py --source-only --strict` → **0 Funde** (13 Regeln).
* `hugo --minify --destination public` → **rc=0**, Build läuft durch (inkl. `/404`).
* `robustheits_gate.py --public public --strict` → **0 Funde**.
* `node --test tools/robust.test.mjs tools/ff-suche.test.mjs tools/ki-assistent.test.mjs`
  → **42/42 grün** (robust+suche 37, KI-Assistent 5).
* `python3 -m unittest scripts.tests.test_robustheits_gate scripts.tests.test_ki_assistent_gate`
  → **60 Tests OK**.
* `ki_assistent_gate.py` → **8 bereit, 1 Warnung (KA1: Endpoint), 0 defekt**
  (die Warnung ist die bewusste Betriebs-Vorgabe aus Befund 4).
* `integrity_guard.py --gate` → **grün** (`ki_assistent.html` und
  `ki-assistent.js` sind nicht versiegelt; `head.html` unverändert).
* `manifest_guard.py` → grün. `governance_contract.py --selftest` → bestanden.

**Simulation des Deploy-Jobs** (Kopie des Arbeitsbaums in `/tmp`, nicht im Repo;
Schritte aus `.github/workflows/deploy.yml`, je mit `bash -e`):

* Schritte **2–26** (Merge-Marker bis Taxonomie-Gate, inkl. Robustheit): **grün**.
* Build (Schritt 28, wie `hugo-build`): **grün**.
* Schritte **29–37** (H1, Index-Hygiene, Spam, Faktenfrische, Publish-Gate,
  Quote, YMYL): **grün**.
* Schritte **41–48** (finale Produkt-Gates, Anker-Wache, Release-Scorecard): **grün**.
* Schritte **50–52** (Vorlese-Selbsttests, TTS-Installation, Kostensperre): **grün**.
* Schritt **56** (Pagefind-Suchindex): **grün**.

**Nicht lokal prüfbar** (brauchen CI-Secrets, Netz zu TTS-Diensten oder Schreibrechte
auf `gh-pages`): Schritte 38/39/49 (Commits der Heilungen), 53–55 (Tonspuren, die
ohnehin mit `|| echo` nicht blockieren), 57–59 (Deploy auf gh-pages / Pages). Diese
sind im Workflow mit Fallbacks versehen bzw. laufen nur im echten Lauf.

**Ergebnis:** Die lokal reproduzierbaren Ursachen sind behoben: der R4/R7-Verstoß im
Widget, der Build-Abbruch auf `/404` und das Ausliefern eines Widgets ohne Backend.
Ob der nächste CI-Lauf grün wird, zeigt erst der echte Push – die Schritte ohne
lokale Entsprechung sind oben benannt. Der Test
schützt die Klasse (Markup-Sicherheit, Zeitlimit) gegen einen Rückfall; die
Wache läuft in `robustheit.yml` bei jeder Änderung an `static/premium/**`.

**Offen (außerhalb dieses Vorgangs, nicht verändert):** Die übrigen offenen
Issues im Repo (u. a. #665 Qualitätsprüfung, #661 Bot-Watchdog, #653 WF-D4E0) sind
eigene Vorgänge und wurden hier nicht bearbeitet. Ebenso wenig wurden die in
früheren Berichten genannten Altlasten (z. B. `reserve_readiness.py`,
Klartext-Wache) erneut gemessen oder verändert.
