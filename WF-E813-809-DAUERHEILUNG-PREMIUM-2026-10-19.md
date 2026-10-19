# WF-E813: Die Wache hatte recht – das Pflege-System log. Fünf Tage „Behoben“ ohne je gemessen zu haben

**Stand:** 19.10.2026 · **Meldung:** [#809](https://github.com/frank-hartung/franksfinanzcheck-blog/issues/809)
· **Vorgang:** WF-E813 (Sicherheits-Wache, Bereich *Betriebspflege*) · Folge von
[#767](https://github.com/frank-hartung/franksfinanzcheck-blog/issues/767) ·
[#782](https://github.com/frank-hartung/franksfinanzcheck-blog/issues/782) ·
[#798](https://github.com/frank-hartung/franksfinanzcheck-blog/issues/798)
· **Klasse:** `machine/auto` (Pflege-System, Turnstile-Paar) + `human`
(Cloudflare-Proxy A1, Turnstile-Widget) – getrennt nach Klasse, nicht nach
Bauchgefühl
· **Vertrag:** **C34** durchgereicht bis zur Schließseite: *Auswertung statt
Durchreichen* gilt auch für „Behoben“.

> **„🔧 Wartung · Betriebspflege · Vorgang WF-E813“** – vierte Meldung
> desselben Vorgangs in fünf Tagen. Die Nachricht war jedes Mal dieselbe und
> jedes Mal richtig: zwei offene Befunde (Proxy nicht aktiv; Turnstile-Paar
> nicht vollständig). Falsch war das, was das Pflege-System **danach** tat.

## Das Urteil in einem Satz

Die Sicherheits-Wache hat seit dem 15.10.2026 täglich exakt gemessen und
klassegenau gemeldet – und der Auto-Close des Fehler-Alertings hat ihre
Meldungen geschlossen, sobald **irgendein** Lauf des Workflows grün war,
ohne dass der Job, der rot war, überhaupt gelaufen ist. Ein Push-Lauf ohne
Live-Messung schrieb „✅ Behoben: Der Vorgang läuft wieder fehlerfrei“ – die
nächste Messung meldete dieselbe Wahrheit von neuem. Dazu kam ein echter
Betriebsausfall im selben Lauf: Die Turnstile-Prüfung verlangte seit dem
15.10. ein Token, das das Formular ohne Site-Key gar nicht liefern konnte –
**jede Newsletter-Anmeldung scheiterte**, fünf Tage lang, täglich als BEFUND
gemeldet. Behoben ist beides jetzt im Code: Schließen nur noch mit Job-Beweis,
Turnstile nur noch als Paar, und A1 hat einen Befehl statt einer Klickstrecke.

---

## 1. Zeitleiste (UTC, 15.–19.10.2026)

| Zeit | Ereignis | Beleg |
|---|---|---|
| 15.10. 11:11 | Erster Live-Lauf der Sicherheits-Wache – rot | Run `38725521166`, Meldung **#767** |
| 15.10. abends | Dauerheilung WF-E813 (Teil 1): Klassen BEFUND/STOERUNG/WACHE-FEHLER, Selbstheilung, eigene Triage | `SICHERHEITS-WACHE-WF-E813-DAUERHEILUNG-PREMIUM-2026-10-15.md` |
| 16.10. 13:05 | Live-Lauf rot – Meldung **#782** | Run `38891475692` |
| 16.10. 15:25 | **#782 geschlossen** mit „läuft wieder fehlerfrei“ | Run `38923824627` – `push`, **Live-Messung: skipped** |
| 17.10. 12:25 | Live-Lauf rot – Meldung **#798** | Run `39024833276` |
| 18.10. 11:55 | **#798 geschlossen** mit „läuft wieder fehlerfrei“ | Run `39125154809` – `push`, **Live-Messung: skipped** |
| 19.10. 12:43 | Live-Lauf rot – Meldung **#809** (dieser Vorgang) | Run `39254264963`, Commit `c32ab5dc` |

**Der entscheidende Satz der Zeitleiste:** Die beiden Abschlussläufe sind
grün, weil sie die Messung **nicht ausführten**. Beide Male steht im Lauf
selbst `Live-Messung (täglich und auf Zuruf) → skipped`; der Workflow ist
per Konstruktion nur mit `Quellseite (offline)` grün. Wer „Behoben“ aus
einem Lauf liest, in dem der Patient nicht auf dem Tisch lag, hat nichts
festgestellt – er hat eine Behauptung geschrieben.

---

## 2. Was der rote Lauf vom 19.10. wirklich sagt

Die Log-Dateien des Laufs sind über die API nicht abrufbar (gleiche Lage wie
am 15.10. – `results-receiver` EOF). Die **Annotationen** des Laufs, die auf
der Actions-Seite stehen, tragen beide Klassen; mehr braucht es nicht:

1. **F-01 BEFUND** – „Pflicht-Header fehlen oder sind falsch“, Diagnose:
   **„Proxy nicht aktiv“** (kein `cf-ray`), nächster Schritt Runbook A1,
   Schritt 1–3. Das ist derselbe offene Befund wie seit dem 15.10.: Die Zone
   liegt nicht hinter dem Cloudflare-Proxy, also kann die Transform Rule
   `FF Sicherheits-Header` gar nicht wirken. Die Meldung nennt das korrekt –
   die Wache selbst ist seit der ersten Dauerheilung einwandfrei.
2. **Worker BEFUND** – „Betriebszustand verfehlt das Soll“. Der Exit-Code 1
   dieser Wache kann nur vier Ursachen haben (Skript gelesen, nicht geraten):
   KV-Ausfall, Tagesdeckel ≤ 0, fehlende Edge-Vorlage, Turnstile-Widerspruch.
   KV-Ausfall wäre Exit 2 (STOERUNG, `/healthz` antwortet 503), Deckel und
   Vorlage sind repo-seitig grün (Offline-Job derselben Sitzung grün). Bleibt
   der **Turnstile-Widerspruch** – und er passt bytegenau zum Bestand:
   `hugo.toml` trägt `turnstileSiteKey = ""`, `wrangler.toml` dokumentiert
   `TURNSTILE_SECRET` als „standardmäßig AKTIV seit 15.10.2026“. Der Worker
   also prüft, die Website liefert kein Widget: **Jede Anmeldung scheitert an
   der Sicherheitsprüfung.** Fünf Tage lang. Der BEFUND war in jeder Meldung
   sichtbar – er war nur ohne Dashboard-Handgriff nicht behebbar, und das
   Pflege-System tat so, als sei erledigt, was nicht erledigt war.

---

## 3. Ursachen

### U1 — Auto-Close auf Workflow-Ebene, Fehler passieren auf Job-Ebene

```yaml
if: github.event.workflow_run.conclusion == 'success' &&
    github.event.workflow_run.head_branch == … &&
    github.event.workflow_run.event != 'pull_request'
```

Drei Bedingungen, keine davon fragt: **Lief der Job, der rot war?** Für die
Sicherheits-Wache ist die Antwort in jedem Push-Lauf „nein“ – der Live-Job
ist `if: schedule || workflow_dispatch`. Genau die Push-Läufe der
Zwischenräume waren es, die #782 und #798 schlossen. Dieselbe Blindstelle
trifft jeden Workflow mit bedingten Jobs; die Sicherheits-Wache traf sie
zuerst, weil ihre Meldungen seit dem 15.10. im Wochentakt neu entstanden.

### U2 — Turnstile: fail-closed gegen Menschen ist kein Schutz, sondern ein Ausfall

Der Vertrag vom 15.10. lautete: „Sobald das Secret gesetzt ist, prüft der
Worker fail-closed – ohne Widget scheitert jede Anmeldung. Genau das meldet
die Wache täglich.“ Das ist exakt eingetroffen. Eine Regel, die fünf Tage
lang einen vollständigen Ausfall des Anmeldewegs in Kauf nimmt, um einen
Bot-Schutz zu erzwingen, dessen zweite Hälfte (das Widget) noch fehlt, hat
das Schutzziel verfehrt: Verfügbarkeit ist Teil der Sicherheit, und ein
Schutz, der nur noch den Angreifer bedient, weil kein Leser mehr
durchkommt, ist ein Angriff auf den eigenen Dienst. Die Wache konnte den
Zustand nur melden; der Code ließ keine dritte Antwort zu.

### U3 — A1 ist menschlich, aber der Weg dorthin war eine Klickstrecke

„Proxy nicht aktiv“ ist eine Dashboard-Entscheidung (plus B7-Datenschutztext
danach) – das bleibt so. Aber ein 20-Punkte-Handgriff im Dashboard ist kein
Betriebsstandard, sondern eine Einladung zu Drift: gemacht, halb gemacht,
nachgebaut, vergessen. Eine Profi-Agentur hält so einen Sollstand als
Werkzeug vor, das misst und – auf Zuruf – herstellt.

### U4 — Die Lehre vom 15.10. wurde nur auf die halbe Kette angewandt

„Ein Messwert ohne Klasse ist keiner“ – diese Lehre aus der ersten
Dauerheilung galt für die **Messseite** (BEFUND/STOERUNG). Die **Schließ-
seite** klassifizierte weiter nur „grün oder nicht grün“ und verlieh jedem
Grün die Behauptung „fehlerfrei“. Ein System, das nach misst und vor
beendet, ist nicht doppelt sicher – es ist an einer Stelle ehrlich.

---

## 4. Die Heilung

### H1 — „Behoben“ nur noch mit Job-Beweis (`scripts/alert_resolve_gate.py`)

Der Alarm trägt die fehlgeschlagenen Jobs jeder Meldung maschinenlesbar
(`<!-- alert-jobs: [...] -->`, `<`/`>` als JSON-Escapes – F-09-Kanalhygiene).
Der resolve-Job holt die Jobs **des auflösenden Laufs** und fragt eine
einzige Regel – eine Quelle der Wahrheit, offline prüfbar:

| Lage | Entscheidung |
|---|---|
| Jeder gemeldete Job im Lauf vorhanden und `success` | schließen – mit den Jobnamen im Grund |
| Ein gemeldeter Job **fehlt** im Lauf (typisch: bedingt ausgesetzt) | **offen**, Grund nennt den Job |
| Job vorhanden, aber `skipped`/`failure`/… | **offen** |
| Kein Job-Beweis im Lauf (API leer/unlesbar) | **offen** – kein „Behoben“ ohne Messung |
| Meldung ohne jede Job-Angabe (Altbestand) + Lauf mit Jobs | Altvertrag (schließen), Grund nennt den Fallback |

Die Altform ohne Marker wird aus den lesbaren Zeilen „- Job **„…“**“
geparst – der Bestand (#782/#798/#809) fällt unter dieselbe Regel wie der
Neubestand. Ein Werkzeugfehler des Gates lautet fail-safe: offen.

**Gegenproben, die den Rückfall verhindern** (eine Regel ohne Gegenprobe ist
ein Wunsch, keine Regel):

- `test_push_ohne_live_job_schliesst_live_meldung_nicht` – die exakte
  Wiederholung von #782/#798/#809, als Test.
- `test_live_job_gruen_schliesst` – die positive Form; ohne sie wäre die
  Regel „nie schließen“ auch „grün“.
- `test_skipped_ist_kein_beweis`, `test_nicht_gruener_job_schliesst_nicht`.
- `test_alle_gemeldeten_jobs_muessen_gruen_sein` – zwei Jobs, einer grün.
- `test_altform_ohne_marker_wird_gelernt` – Bestandsschutz.
- `test_kein_job_beweis_im_lauf_bleibt_offen`, `test_api_beide_shapes`.
- Struktur-Verdrahtung (`test_resolve_ruft_das_gate_auf`): das Gate sitzt
  **vor** `gh issue close`, der Alarm schreibt den Marker – ein Rückfall zum
  nackten `close` fällt sofort auf.

### H2 — Turnstile wird zum Paar (`newsletter-worker`, Wache, Tests)

Der Worker kennt drei Zustände – `aktiv` (Secret **und** Site-Key: geprüft,
fail-closed), `wartet` (nur Secret: Anmeldung läuft weiter, Prüfung steht
aus, `/healthz` meldet es laut) und `inaktiv` – und prüft Turnstile nur im
Zustand `aktiv`. Der Site-Key hat zwei Adressen, die zusammen deployt
werden: `hugo.toml` `params.turnstileSiteKey` (liefert das Widget) und
`newsletter-worker/wrangler.toml` `TURNSTILE_SITEKEY` (sagt es dem Worker).
Die Betriebs-Wache prüft den **Spiegel** beider Stellen (Abweichung =
Fehler) und bewertet die Matrix ausdrücklich:

| Worker | Widget | Urteil |
|---|---|---|
| `aktiv` | da | ✅ in Ordnung |
| `aktiv` | fehlt | ❌ jede Anmeldung scheitert |
| `wartet` | da | ❌ Fassade (Spiegel gebrochen) |
| `wartet` | fehlt | ⚠️ laut: Anmeldung ohne Bot-Prüfung, Paar vervollständigen |
| `inaktiv` | da | ❌ Fassade (wie bisher) |
| `inaktiv` | fehlt | ⚠️ wie bisher (Honeypot, Zeitfalle, Mengenklassen, Tagesbudget) |

Damit ist der Zustand, der seit dem 15.10. als Ausfall existierte, im Code
abstellbar: Beim nächsten Worker-Deploy läuft die Anmeldung wieder – und die
Wache schreit weiter, bis das Widget da ist („wartet“ ist ausdrücklich kein
„in Ordnung“). **Der Fußschuss ist konstruktiv unmöglich geworden:** Secret
und Site-Key wirken gemeinsam oder gar nicht, und der Spiegel wird jeden Tag
geprüft. 92 Worker-Tests (einschließlich der neuen Paar-Fälle) und 13
Selbsttest-Fälle der Betriebs-Wache nageln es fest.

### H3 — A1 in einem Griff (`scripts/cloudflare_edge_freigabe.py`)

`npm run edge:freigabe` misst DNS-Proxy (beide Hosts), SSL-Modus und die
Transform Rule `FF Sicherheits-Header` gegen die Cloudflare-API und
vergleicht sie mit dem Sollstand – der wird **aus der Tabelle in
`cloudflare/edge-schutz.md` gelesen** (eine Quelle; wer die Vorlage ändert,
ändert die Regel). `npm run edge:freigabe:apply` stellt den Sollstand
idempotent her (nur Abweichungen, andere Regeln der Phase unangetastet),
mit `CLOUDFLARE_API_TOKEN` (`Zone.DNS:Edit`, `Zone.Settings:Edit`,
`Zone.Transform Rules:Edit`). Exit 0 = im Soll, 1 = offen mit nächstem
Schritt, 2 = Werkzeugfehler. Der Selbsttest prüft ohne Netz, dass die
Vorlage vollständig ist (acht Kopfzeilen) und die Pläne korrekt sind.

### H4 — Doku

Runbook A1 nennt jetzt die Werkzeug-Variante neben dem Dashboard-Weg; A3 und
`cloudflare/edge-schutz.md` beschreiben den Paar-Vertrag samt „wartet“-
Zustand und Spiegel-Prüfung. Die Datenschutz-Pflicht B7 bleibt der
ausdrückliche Schritt nach dem Proxy – der Text steht fertig im Runbook.

---

## 5. Was sich für Frank ändert

| Vorher | Nachher |
|---|---|
| Jeder grüne Lauf schließt die Meldung – auch ohne je gemessen zu haben | Schließen nur, wenn **der Job, der rot war**, im Lauf grün ist |
| Fünf Tage „✅ Behoben“-Kommentare zu offenen Befunden | Ein ehrliches „bleibt offen: Job X lief in diesem Lauf nicht“ |
| WF-E813 meldet sich im Wochentakt neu | Eine Meldung, offen, bis die Live-Messung wirklich grün ist |
| Newsletter-Anmeldung seit 15.10. tot (Turnstile ohne Widget) | Anmeldung läuft sofort nach dem Worker-Deploy; Botschutz wird beim Paar-Vollausbau aktiv |
| A1 = drei Dashboard-Wege, 20 Handgriffe | `npm run edge:freigabe[:apply]` – messen, stellen, nachweisen |
| Wache meldet „jede Anmeldung scheitert“ ohne Abstellmöglichkeit | Zustand „wartet“ ist im Code behebbar und wird bis dahin täglich gemeldet |

---

## 6. Nachweise

```
python3 scripts/alert_resolve_gate.py --selftest          11 Fälle grün (neu)
python3 -m unittest scripts.tests.test_alert_resolve_gate 19 Tests, 19 grün (neu)
python3 -m unittest scripts.tests.test_alert_scoping      24 Tests, 24 grün
node scripts/tests/sim/alert_scoping_sim.mjs              44 Szenarien, 44 grün
python3 scripts/worker_betrieb_wache.py --selftest        13 Fälle grün (vorher 10)
python3 scripts/worker_betrieb_wache.py --offline         grün (Spiegel geprüft)
cd newsletter-worker && node --test                       92 Tests, 92 grün
npm run test:sicherheit                                   alle vier Wachen grün
python3 scripts/cloudflare_edge_freigabe.py --selftest    4 Fälle grün (neu)
npm run edge:check                                        grün
```

Belegt aus den Laufsachen (Actions-API, unveränderlich):

- Run `38923824627` (16.10., `push`) und `39125154809` (18.10., `push`):
  Job `Live-Messung (täglich und auf Zuruf) → skipped`, Lauf `success`,
  Abschlusskommentare auf #782/#798 „läuft wieder fehlerfrei“.
- Run `39254264963` (19.10., `schedule`): Annotationen
  „F-01 BEFUND … Proxy nicht aktiv“ und „Worker BEFUND“.

---

## 7. Was offen bleibt – und wer es schließt

1. **A1 (human):** Proxy auf *Proxied*, SSL `Full`, Regel A1 – jetzt ein
   Befehl (`npm run edge:freigabe:apply`) oder drei Handgriffe (Runbook A1).
   **Danach zwingend B7** (Datenschutz-Text, steht fertig im Runbook).
2. **Turnstile-Paar (human + deploy):** Widget anlegen, Site-Key in
   `hugo.toml` **und** `newsletter-worker/wrangler.toml`, deployen
   (Runbook A3, Schritt 1–2). Bis dahin: Anmeldung funktionsfähig,
   tägliche Warnung.

Beides ist bewusst `human`: Es berührt den Datenverkehr der Leser und die
Erklärungspflicht davor – das entscheidet kein Code. Sobald A1 steht, wird
der Live-Job grün, und **die Meldung schließt sich dann selbst** – diesmal
mit Job-Beweis, das heißt: erst wenn „Live-Messung (täglich und auf Zuruf)“
wirklich grün lief. Dieser Vorschlag schließt #809 deshalb bewusst **nicht**
vorab (dieselbe Zurückhaltung wie #786): Wer ein Ticket schließt, das
seinen Befund noch trägt, wiederholt die Lüge, die dieser Vorgang behebt.

---

## 8. Lehre

1. **„Grün“ ist eine Messung, keine Stimmung.** Ein Lauf, der den Job nicht
   ausgeführt hat, hat über diesen Job nichts gesagt. Wer „Behoben“
   schreibt, muss den rot gewesenen Job gesehen haben – im grün.
2. **Die Klasse muss durch die ganze Kette** (C34): Messen, Melden **und**
   Schließen. Die halbe Ehrlichkeit vom 15.10. erzeugte fünf Tage
   halber Wahrheit.
3. **Fail-closed ist kein Selbstzweck.** Ein Schutz, der in Abwesenheit
   seiner zweiten Hälfte die legitime Nutzung abwürgt, ist ein Ausfall mit
   guter Absicht – das Paar wird zusammen deployt oder gar nicht.
4. **Ein Befund, der nicht behebbar ist, wird wiederholt, nicht gelöst.**
   Deshalb gehört zu jedem „human“-Befund ein Werkzeug, das den
   Handgriff auf ein Maß bringt, das er verdient: einen Befehl.
5. **Der beste Alarm ist der, der nicht klingelt, weil er die Wahrheit
   schon gesagt hat.** Vier Meldungen in fünf Tagen waren kein
   Überschwang der Wache – sie war die Einzige, die noch ehrlich war.

---

## 9. Dateien

| Datei | Änderung |
|---|---|
| `scripts/alert_resolve_gate.py` | **neu** – Job-Beweis für Auto-Close (Marker + Altform, fail-safe, Selbsttest 11 Fälle) |
| `scripts/tests/test_alert_resolve_gate.py` | **neu** – 19 Regressionstests inkl. #809-Reproduktion |
| `.github/workflows/alert-on-failure.yml` | Alarm schreibt `<!-- alert-jobs: … -->`; resolve entscheidet über das Gate, loggt den Offen-Grund |
| `newsletter-worker/src/index.js` | Paar-Vertrag Turnstile (`aktiv`/`wartet`/`inaktiv`), `/healthz` meldet den Zustand |
| `newsletter-worker/wrangler.toml` | `TURNSTILE_SITEKEY` (Spiegel von `hugo.toml`), Vertragskommentare |
| `hugo.toml` | Kommentar: Paar-Vertrag statt „fail-open ohne Site-Key“ |
| `scripts/worker_betrieb_wache.py` | Bewertungsmatrix der drei Turnstile-Zustände, Spiegel-Prüfung, Selbsttest 10 → 13 Fälle |
| `newsletter-worker/test/index.test.js` | Paar-Fälle (92 Tests): beide Werte → geprüft, nur Secret → „wartet“, Anmeldung läuft |
| `scripts/cloudflare_edge_freigabe.py` | **neu** – A1 messen/herstellen (Sollstand aus `cloudflare/edge-schutz.md`) |
| `package.json` | `edge:check`, `edge:freigabe`, `edge:freigabe:apply` |
| `docs/SICHERHEIT-BETRIEB-RUNBOOK.md` | A1: Werkzeug-Variante · A3: Paar-Vertrag |
| `cloudflare/edge-schutz.md` | A1: Werkzeug-Variante · A3: Paar-Vertrag |
