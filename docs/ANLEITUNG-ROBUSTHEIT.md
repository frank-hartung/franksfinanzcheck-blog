# Anleitung: Robustheit der Laufzeit (Vertrag C31, seit 07.10.2026)

**Kurzfassung:** Jeder interaktive Baustein der Seite hat ein Fangnetz, jeder
Netzaufruf ein Zeitlimit, jeder Speicherzugriff ein `try/catch`, der Service
Worker ist fail-open, und jeder gefangene Fehler wird sichtbar – im Befund
(`FFRobust.bericht()`) und, wo der Leser es braucht, als Satz auf der Seite.
Niemand pflegt das von Hand: `scripts/robustheits_gate.py` prüft R1–R13 an
jedem Push, jedem PR, jedem Deploy und jede Nacht.

---

## 1. Warum es das gibt

Dieser Blog hat zwei Fehlerklassen. Die **lauten** fangen die übrigen Wachen:
Der Build bricht ab, ein Gate wird rot, der Deploy bleibt liegen. Die
**stillen** sind teurer, weil sie niemand meldet – die Seite *baut*, also ist
aus Sicht der CI alles in Ordnung. Der Ausfall passiert erst im Browser, bei
einem Leser, auf einem Gerät, das hier niemand hat.

Vier stille Ausfälle waren am 07.10.2026 real im Bestand:

| # | Befund | Wirkung für den Leser |
|---|---|---|
| 1 | `initialisiere()` in `ff-rechner.js` lief ohne Fangnetz. Ein Rechner mit unerwartetem Markup warf mitten in der Schleife. | **Alle** Rechner derselben Seite verloren ihre Verdrahtung: Formular sichtbar, Absenden lädt die Seite neu, keine Rechnung. |
| 2 | Die Newsletter-Anmeldung wartete **unbegrenzt** auf den Worker (`fetch` ohne Zeitlimit, Knopf `disabled`). | Hing der Worker, stand „Wird übermittelt …" für immer; wiederholen ging nicht, abbrechen auch nicht. |
| 3 | Der Service Worker öffnete seinen Cache außerhalb jedes `try/catch`. Wirft das Cache-API (volle Quota, privater Modus), lehnte `respondWith` ab. | Ein Request, der ohne den SW problemlos durchgegangen wäre, kam nicht an: weiße Fläche für Wiederkehrer. |
| 4 | `navigator.clipboard.writeText()` im Kopier-Knopf lief ohne Fangnetz, die Erfolgsmeldung kam **vor** der Antwort. | „copied!" am Knopf, nichts in der Zwischenablage, ein nicht abgefangenes Promise in der Konsole. |

Keiner der vier Fälle ist in einem Build-Gate sichtbar. Alle vier kosten
Vertrauen – genau die Währung dieses Produkts.

**Grundsatz der Schicht:** Ein gefangener Fehler ist erst behoben, wenn der
Leser weiß, woran er ist. Ein Knopf, der nichts tut, ist schlechter als ein
Satz, der sagt, was geht und was nicht.

---

## 2. Zwei Stufen, eine Wahrheit

### Stufe 1 – Bootstrap im `<head>`

`layouts/_partials/extend_head.html`, **im vorhandenen** Consent-Skript (kein
zusätzliches Head-Kind: 58 Kinder sind die Lighthouse-Grenze, Artikel-Seiten
liegen bei 48–58 – `scripts/dom_audit.py`).

Warum im `<head>`: Fehler, die während des Parsens oder in den Inline-Skripten
des Body passieren (Consent, Kopier-Knopf, Lese-Fortschritt), sind weg, bevor
ein Skript am Fuß des Body seinen Horcher anmelden kann. Diese ~120 Zeilen sind
die einzige Stelle, die **jeden** Fehler der Seite sieht.

Was er stellt:

| Baustein | Verhalten |
|---|---|
| `FFRobust.melden(eintrag)` | Ringpuffer (25 Einträge), `ff:fehler`-Event, ab fünf Befunden `data-ff-robust="belastet"`. Sendet **nichts** nach außen. |
| `FFRobust.sicher(fn, rückfall, quelle)` | Einzelfunktion im Fangnetz. |
| `window.addEventListener('error', …, true)` | **Capture-Phase** – Ressourcen-Fehler (Bild, Skript, CSS) bubble'n nicht und wären sonst stumm. |
| `unhandledrejection` | Der häufigste stille Ausfall moderner Bausteine (Fetch ohne `.catch`). |
| `offline` / `online` | `data-ff-offline="1"` am Dokument – CSS und Bausteine können darauf reagieren. |
| `FFRobust.hole(url, opts)` | Fetch mit Zeitlimit, Wiederholung mit Zittern, **lehnt nie ab** (siehe §3). |

### Stufe 2 – Schicht am Fuß des Body

`static/premium/ff-robust.js`, geladen aus `layouts/_partials/deferred_scripts.html`
(über `asset_url.html`, also mit `?v=<SHA>`-Cache-Busting). Ergänzt, was Zeit hat:

| Baustein | Verhalten |
|---|---|
| `insel(name, init, opts)` | Fehlergrenze je interaktivem Baustein: Zustand (`ok`/`fehler`/`uebersprungen`), Befund, `data-ff-insel-fehler`, sichtbarer Satz in `opts.ziel`. |
| `hinweis(text, opts)` | `p.ff-robust-hinweis` mit `role="status"` (angekündigt, ohne Fokus zu stehlen). |
| `ablage` | Web Storage mit Fangnetz und Tab-Ersatz: `lesen/schreiben/loeschen/json/merke`, `verfuegbar()`, `ersatz()`. |
| `zwischenablage(text)` | Clipboard-API → `execCommand` → ehrliche Antwort `true`/`false`. |
| `bereit(cb, quelle)` | DOM-Freigabe im Fangnetz. |
| `bericht()` | Diagnose: Inseln, Befunde, Speicher, Service Worker, offline. Bleibt im Browser. |

Die Schicht ist **idempotent** (`R.boot`) und ergänzt die erste Stufe, statt sie
zu ersetzen. Fehlt Stufe 1 (alter Cache, fremde Einbindung), übernimmt Stufe 2
die Horcher – die Wache hängt nie von der Ladereihenfolge ab.

---

## 3. Der Fetch-Vertrag (`hole`)

`FFRobust.hole(url, optionen)` liefert **immer** ein Ergebnisobjekt und lehnt
nie ab:

```js
{ ok: true,  status: 200, versuche: 1, antwort: Response }      // Erfolg
{ ok: true,  unbekannt: true, status: 0, antwort: Response }    // opaque (no-cors)
{ ok: false, status: 503, fehler: 'http-503', antwort: … }      // Server-Fehler
{ ok: false, status: 0,  fehler: 'zeitlimit', versuche: 2 }     // Zeitlimit
{ ok: false, status: 0,  fehler: 'netz', versuche: 3 }          // Verbindung
```

Optionen: `zeitlimit` (ms, Vorgabe 12 000), `versuche` (1–3, Vorgabe 1),
`warte` (Basis der Wiederholung in ms, Vorgabe 400, exponentiell + Zittern),
`quelle` (Name für den Befund). Alles Übrige geht unverändert an `fetch`.

Zwei Entscheidungen, die nicht verhandelbar sind:

* **`opaque` ist kein Fehler.** Die Newsletter-Anmeldung sendet `no-cors`, weil
  das Ergebnis nicht lesbar ist (`test_kein_erfolgsversprechen` hält das fest).
  Eine opaque Antwort heißt „durchgekommen, Inhalt nicht lesbar". Sie als
  Misserfolg zu deuten hieße, ehrliche Anmeldungen als Fehler zu melden.
* **Wiederholen nur bei `netz`, nie bei `zeitlimit`.** Ein Request, der ins
  Zeitlimit läuft, hat den Dienst bereits beschäftigt; ihn blind zu
  wiederholen verdoppelt die Last genau dann, wenn der Dienst schon kämpft.

Bausteine, die `hole` nicht haben (weil sie vor Stufe 2 laufen), reichen es
durch und fallen sonst auf `window.fetch` zurück – dann gilt der alte Zustand,
nie ein schlechterer.

---

## 4. Die zwölf Regeln

| Regel | Was sie hält |
|---|---|
| **R1** Schicht | `ff-robust.js` existiert, trägt die API, hängt an `window.FFRobust`. |
| **R2** Bootstrap | Horcher sitzt im `<head>` – **im vorhandenen Skript**; Anzahl `<script>`-Tags eingefroren (DOM-Budget). |
| **R3** Idempotenz | Beide Stufen melden sich nur einmal an (`R.boot`), ein `unhandledrejection`-Horcher je Stufe. |
| **R4** Zeitlimit | Jeder `fetch`-Aufruf der Erstparteienskripte hat `hole`/`AbortController`/`zeitlimit` in Reichweite (±12 Zeilen). `prefetch(` ist kein Fetch. |
| **R5** Service Worker | fail-open (`fach()` im Fangnetz), Offline-Fangnetz (`404.html` in `PRECACHE`, Status 503), Range-Umgehung, `/sw.js` nie cache-first, `SKIP_WAITING`, `catch` in beiden Strategien. |
| **R6** Inseln | Jeder interaktive Baustein hat sein Fangnetz und einen Satz: Rechner, Kurzfassung-Netz, Kopier-Knopf, Anmeldung, Präferenzen, Feedback. |
| **R7** Markup | `innerHTML` nur mit statischem Literal oder statischer Konstante; nie `document.write`, `eval()`, `insertAdjacentHTML`, `outerHTML =`. |
| **R8** Speicher | Jeder `localStorage`/`sessionStorage`-Zugriff liegt in einem `try/catch`. |
| **R9** Hinweis | `.ff-robust-hinweis` ist gestylt, hat eine Dark-Variante, animiert keine Layout-Eigenschaft und ist `role="status"`. |
| **R10** Syntax | Jedes Erstparteienskript und der Service Worker sind parsebar (`node --check`). |
| **R11** First-Party | Schicht und Bootstrap nennen keine fremde Domain. |
| **R12** Einbindung | `ff-robust.js` wird genau einmal geladen, über `asset_url.html` (Cache-Busting). |
| **R13** Fristen | Jede Ausnahme nennt Entscheidungsdatum **und** Frist; die Spanne dazwischen liegt jenseits des CI-Uhr-Proben-Horizonts (≥ 97 Tage) und innerhalb der Obergrenze (≤ 730 Tage). Gemessen wird gegen die Daten, nie gegen die Wanduhr. |

Das Gate **heilt nie selbst**. Ein Fangnetz, das sich selbst wieder einhängt,
wäre keines.

---

## 5. Checkliste für einen neuen Baustein

Wer eine neue interaktive Insel baut (Rechner, Picker, Formular, Werkzeug),
erfüllt vier Punkte – sonst ist das Gate rot:

1. **Fangnetz um die Initialisierung**, je Instanz, nicht je Seite:
   `FFRobust.insel('name', init, { ziel: ergebnisFeld })` – oder ein eigenes
   `try/catch` pro Element, wenn die Schicht noch nicht geladen ist.
2. **Satz im Ausfall**: `role="status"`, Marke, keine Technik („Dieser Rechner
   konnte nicht gestartet werden. Der Ratgeber bleibt vollständig lesbar.").
3. **Zeitlimit an jedem Netzaufruf**: `FFRobust.hole(url, { zeitlimit: …,
   versuche: 2, quelle: '…' })` und ein Zustand, der den Knopf wieder freigibt.
4. **Speicher nur mit Fangnetz**: `FFRobust.ablage` oder `try/catch` – und die
   Seite bleibt ohne Speicher bedienbar.

Zusätzlich gilt der Bestand: kein `innerHTML` aus Text, keine fremde Domain,
keine Layout-Animation, Dark-Variante für jede Farbe.

---

## 6. Ausnahmen

`data/robustheit_ausnahmen.yaml`. Eine Ausnahme gehört dorthin, **nicht** in
die Prüflogik. Vertrag je Eintrag: `pfad`, `regel`, `grund`, `entscheidung`
(Mensch + Datum + Vorgang), `faellig` (JJJJ-MM-TT). Eine Ausnahme ohne
Fälligkeit ist eine stille Abschaffung.

**Zwei Regeln für die Frist, beide aus einem echten Befund gelernt (R13):**

1. Die Frist muss **jenseits des Uhr-Proben-Horizonts** liegen. Die CI lässt die
   ganze Suite mit einer um 97 Tage vorgestellten Uhr laufen
   (`publication-reliability-tests.yml`, Schritt „Uhr-Probe"; Grundlage
   `scripts/selftest_clock.py`). Eine Frist innerhalb dieses Horizonts färbt
   diesen Lauf rot – an einem Kalendertag, ohne eine Code-Änderung.
2. **Abgelaufen heißt sichtbar, nicht rot.** Eine Frist, die im echten Leben
   verstreicht, steht im Bericht (`⚠️ ÜBERFÄLLIG seit N Tagen`) und als
   `::warning` im Laufprotokoll. Den Exit-Code färbt sie nicht – sonst wäre die
   Wache eine Zeitbombe. Vorbild: `scripts/fristen_check.py` („Exit 0 = Lauf ok
   (auch bei überfälligen Fristen – die Eskalation läuft über eigene Issues,
   nicht über rote Runs)").

Gemessen wird deshalb immer gegen das **Entscheidungsdatum aus der Datei**, nie
gegen `date.today()`; `AusnahmenTests::test_dieser_test_liest_nicht_die_wanduhr`
verbietet den Uhr-Zugriff im Testmodul.

Das Gate nennt jede genutzte Ausnahme im Bericht, damit sie sichtbar bleibt.

Aktuell eine Ausnahme: `layouts/_partials/head.html` für **R8**. Die Datei ist
KRITISCH-versiegelt (`scripts/integrity_guard.py`), die vier nackten
`localStorage`-Zugriffe stammen aus dem PaperMod-Erbe und ihr Zweig ist durch
`disableThemeToggle = true` tot – er wird nicht gerendert. Sie zu ändern braucht
eine menschliche Signatur im selben Commit.

---

## 7. Prüfen

```bash
npm run robustheit          # Quelle (ohne Hugo, < 1 s)
npm run robustheit:check    # Selbsttest + Quelle + Build + gebaute Wahrheit
npm run robustheit:strict   # maschinenlesbar (JSON), node fehlt = Befund
npm run robustheit:ausnahmen# welche Ausnahme wird gerade genutzt?
npm run test:robustheit     # Selbsttest + Unit-Tests + 21 jsdom-Tests

python3 scripts/robustheits_gate.py --selftest           # 14 Sabotage-Proben, 4 Gegenproben
python3 scripts/selftest_clock.py --trap-modul \
        scripts.tests.test_robustheits_gate --offset 97   # Uhr-Probe: keine Zeitbombe
python3 scripts/robustheits_gate.py --public public      # gebaute Wahrheit
node --test tools/robust.test.mjs                        # Verhalten im Browser-DOM
```

CI-Verdrahtung:

* `.github/workflows/robustheit.yml` – Push/PR auf Laufzeit-Pfade, jede Nacht
  04:35 UTC, Selbsttest zuerst, danach Quelle, jsdom-Verhalten, Unit-Tests,
  Hugo-Build und die gebaute Wahrheit.
* `.github/workflows/deploy.yml` – vor dem Build, fail-closed: Ein fehlendes
  Fangnetz stoppt den Deploy, statt still auszuliefern.

Exit-Codes: `0` grün · `1` Verstoß · `2` Ausführungsfehler.

---

## 8. Diagnose im Feld

Ein Leser meldet „der Rechner geht nicht". Drei Handgriffe, ohne Tracking:

```js
FFRobust.bericht()          // Zustand: Inseln, Befunde, Speicher, SW, offline
copy(JSON.stringify(FFRobust.bericht(), null, 2))
document.documentElement.dataset   // ff-robust / ff-offline / ff-insel-fehler
```

`bericht()` sendet nichts. Es gibt kein Fehler-Backend und keins ist geplant:
Die Befunde gehören in die Konsole desjenigen, der sie sieht, und in ein Issue,
wenn sie sich häufen.

---

## 9. Bekannte Grenzen

* **`head.html` ist versiegelt.** Der tote Theme-Zweig mit nackten
  `localStorage`-Zugriffen bleibt, bis ein Mensch ihn signiert ändert
  (Ausnahme R8, fällig 2027-04-07).
* **Ohne `AbortController` kein Zeitlimit.** Alte Browser bekommen den
  schlichten Fetch – derselbe Zustand wie vorher, nie ein schlechterer.
* **Die gebaute Wahrheit braucht Hugo.** `--public` prüft nur, was gebaut
  wurde; ohne Build bleibt die Quellprüfung (`--source-only`) die Aussage.
* **Das Gate prüft Verträge, kein Verhalten im Feld.** Verhalten prüft
  `tools/robust.test.mjs` (jsdom) und – wo es um Darstellung geht – `e2e/`.

---

**Bezug:** `ROBUSTHEIT-PREMIUM-2026-10-07.md` (Befund, Heilung, Beweis) ·
`CLAUDE.md`, Abschnitt „Die Seite darf nie stumm sterben" ·
`PRODUCT.md` §6 (Qualitätsgrenzen) · `docs/ANLEITUNG-HUGO-BUILD.md`
