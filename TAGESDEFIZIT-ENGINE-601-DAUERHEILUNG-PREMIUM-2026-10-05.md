# Content-Engine: Tagesdefizit 2026-10-05 (1/2 LIVE) — Dauerheilung auf Premium-Niveau

**Auftrag (Frank, Issue #601):** „Content-Engine: Tagesdefizit 2026-10-05
(1/2 LIVE) – Bitte dauerhaft auf Premium-Level einer Profi-Agentur beheben.“

**Vorgangskürzel:** WF-C601 · **Datum:** 05.10.2026 · **Issue:** #601

„Dauerhaft“ heißt hier – wie bei #521, #590 und #594 – nicht: den Lauf
wiederholen. Es heißt: den Konstruktionsfehler finden, die Fehlerklasse mit
einer Wache schließen und belegen, dass sie geschlossen bleibt.

---

## Kurzfassung

Der 05.10.2026 war ein Montag (Publikationstag) mit grüner Kapazität: 29
frei verfügbare AUTO-Themen, Tagesziel 2 gedeckt, Puffer-Bedarf erfüllt.
Trotzdem endete der Tag um 19:23 UTC mit **1/2 LIVE** – und mit einem
Defizit-Issue, das zur Themen-Kapazität riet, obwohl die Ursache woanders
lag: **GitHubs Scheduler hat an diesem Tag 4 von 7 planmäßigen Slots der
Content-Linie nie gestartet.**

| # | Fehler | Wirkung am 05.10. |
|---|---|---|
| **D1** | Die Content-Linie hatte **keine Slot-Wache**: Ein nie gestarteter cron-Lauf wird nie rot – kein Alerting, kein Issue, stille Tagesspitze | 4 Slots verloren: Engine 06:10 (Haupt-Slot!) + 17:40 (Fallback 2), Kadenz 10:35 + 16:35 (letzterer kam als EINZIGER – 2 h 47 min später, um 19:22). Selbst die Produktions-Wache (20:00 UTC) war um 20:35 noch nie angekommen |
| **D2** | Der einzige Engine-Lauf verlor seine Veröffentlichung an den **Synchronverlust** (PR #589 merge mitten im Lauf) | Phase 1 erreichte main (dns-server-Entwurf, 14:34), die Endabnahme-Commits nie – 0 LIVE aus der Engine. **Bereits heute geheilt:** #597 (18:06), Bestandsgewinn + Nachheilung |
| **D3** | Der Reserve-Pool war durch die **#594-Defekte** (Janitor löschte nach einem Befund, keine Übernahme aus dem Bestand) faktisch leer | Um 19:22 meldete das Zertifikat `ready: 0, pool_size: 1`; der Backstop konnte genau EINEN Artikel (DSL-Reserve) live schalten. **Bereits heute geheilt:** #594 (19:57), 5 gate-fertige Kandidaten |
| **D4** | Das Defizit-Issue **nennt seine Ursache nicht**: Diagnose zeigte Themen-Kapazität (grün!), nicht die Lauf-Realität des Tages | Der Alarm empfahl „Actions → Content-Engine v2 → Phase 1“ – dort stand aber nichts, weil der Lauf ja nie gestartet war |

Der sichtbare Symptomwert „1/2 LIVE“ ist das Produkt D1 × D2 × D3. D2 und D3
sind heute bereits durch #597 und #594 dauerhaft geschlossen (beide
Vorgangsberichte liegen im Repo). **Dieser Vorgang schließt D1 und D4** –
die einzige der vier Ursachen, die KEINEM der heutigen Reparaturen
unterlag, weil sie nicht in der Engine liegt, sondern eine Etage höher: in
der Annahme, ein geplanter cron-Lauf starte auch.

Das Repo kannte diese Fehlerklasse bereits namentlich. Die
Newsletter-Kadenz-Wache (23.09.2026) dokumentiert: „GitHub verwirft
schedule-Ereignisse unter Last“ — am 25.09. „lieferte GitHubs Scheduler an
diesem Tag jedes Ereignis 5–5,5 h zu spät oder gar nicht“. Deshalb hat der
Newsletter einen Worker-Taktgeber, eine Kadenz-Wache und ein drittes Netz.
**Die Content-Linie — das Herzstück des Repos — hatte keins davon.**

---

## Befund im Detail

### Die Beweiskette des Tages (alle Zeiten UTC)

| Zeit | Ereignis | Beleg |
|---|---|---|
| 06:10 | Engine-Haupt-Slot geplant — **startet nie** | Laufliste: kein einziger content-engine-v2-Lauf vor 14:32 |
| 10:35 | Kadenz-Endkontrolle Slot 1 geplant — **startet nie** | Laufliste |
| 10:41–11:00 | Content-Reserve (cron kam an): 8 Roh-Reserve-Entwürfe | Commit c029574b (11:00:20) |
| 14:10→14:32 | Engine-Fallback 1 kommt 22 min verspätet: Lauf 37325495772 | Laufliste |
| 14:34 | Phase-1-Commit 7cd2870b erreicht main: dns-server-Entwurf (`draft: true, reserve: true`) | Commit |
| 14:46 | PR #589 wird gemergt — mitten im Engine-Lauf | Commit 397c5808 |
| 14:53–14:55 | Phase 2/3-Commits scheitern am Rebase-Konflikt (SYNCHRONVERLUST), Lauf rot | Schritt „Persist final acceptance corrections“ |
| 16:35 | Kadenz-Slot 2 geplant — **startet nicht** | Laufliste |
| 17:19–17:35 | Reserve-Lauf (Dispatch): Janitor **löscht 9 Entwürfe**, darunter den Engine-Entwurf dns-server | Commit c56382b2 (Löschbeweis von #594, B2) |
| 17:40 | Engine-Fallback 2 geplant — **startet nie** (26 min bevor der #597-Fix gemergt wäre) | Laufliste |
| 19:22 | Kadenz-Slot (16:35) kommt 2 h 47 min später: Lauf 37362926801 | created_at 19:22:22 |
| 19:22–19:23 | Backstop: `ready: 0` im Zertifikat → genau EIN Reserve-Artikel live (DSL, `date: 19:22:11`); Büroausstattung am Gate geblockt (Audit 19:23:27) | data/audit/2026-10-05.jsonl |
| 19:23:46 | `engine_issue --deficit` eröffnet **#601 (1/2 LIVE)** | Issue |
| 20:00 | Produktions-Wache geplant — **um 20:35 immer noch nie angekommen** | Laufliste |

### D1 — Cron-Blindheit: das Netz, das nur vom selben Haken hing

Die Content-Linie hat sieben planmäßige Slots an jedem Publikationstag —
drei Engine-Slots (06:10 Haupt, 14:10/17:40 Fallback, „Selbstheilung“) und
vier Kadenz-Backstops. Das Design ist richtig gedacht: Jeder Slot ist ein
Fallback für den vorherigen. Aber alle sieben hängen am **selben**
Zustellkanal — GitHubs Scheduler — und dieser lieferte an diesem Tag:

```
Engine   06:10  ✗ nie gestartet        (Haupt-Slot = die Produktion des Morgens)
Kadenz   10:35  ✗ nie gestartet
Engine   14:10  ✓ 14:32 (22 min)       → rot (Synchronverlust D2, seit 18:06 geheilt)
Kadenz   16:35  ⚠ 19:22 (2 h 47 min)  → der EINZIGE Kadenz-Lauf des Tages
Engine   17:40  ✗ nie gestartet        (Fallback 2 = die letzte volle Engine-Chance)
Kadenz   19:35  ✗ nie gestartet
Kadenz   21:35  (ausstehend bei Redaktionsschluss)
```

Gemessen mit dem Trockenlauf der neuen Slot-Wache gegen die echten
Laufbücher (`python3 scripts/slot_wache.py --pruefen --ohne-dispatch
--md --repo …`, 20:29 UTC):

```
| Workflow              | Soll (UTC) | Zustand | Lauf                                    |
|-----------------------|-----------:|---------|-----------------------------------------|
| Content-Engine v2     |      06:10 | bedient | 37325495772 completed/failure um 14:32  |
| Kadenz-Endkontrolle   |      10:35 | bedient | 37362926801 completed/failure um 19:22  |
| Content-Engine v2     |      14:10 | bedient | 37325495772 completed/failure um 14:32  |
| Kadenz-Endkontrolle   |      16:35 | bedient | 37362926801 completed/failure um 19:22  |
| Content-Engine v2     |      17:40 | verpasst | – kein einziger Laufversuch seit Soll |
| Kadenz-Endkontrolle   |      19:35 | verpasst | – kein einziger Laufversuch seit Soll |
| Kadenz-Endkontrolle   |      21:35 | wartet  | Gnadenfrist läuft noch                  |

Tagesziel: 1/2 LIVE · Handlung: nachholen (Engine + Kadenz)
```

Die entscheidende Erkenntnis ist nicht, dass GitHub cron-Ereignisse
verliert — das weiß das Repo seit dem 23.09. und hat es am 25.09. sogar
quantiert. Die Erkenntnis ist: **Für die Content-Linie war das nie ein
Ticket wert.** Newsletter-Daily (2×/Woche) bekam Worker-Taktgeber +
Kadenz-Wache + drittes Netz; die Content-Linie (das Herzstück, 2–3
LIVE-Artikel an Mo/Mi/Fr) lieferte ihre gesamte Tagesquote an denselben
Scheduler aus, ohne jede Gegenprobe. Die Produktions-Wache, die „gar nicht
gelaufen“ erkennen soll, ist selbst ein einziger cron-Lauf um 20:00 UTC —
und kam an diesem Tag (bis Redaktionsschluss) ebenfalls nie an. Ein Wächter
am selben Haken ist kein Wächter.

### D4 — Der Alarm, der zur falschen Ursache riet

Das Defizit-Issue #601 zeigte:

> ✅ 29 frei disponierbare AUTO-Themen – Tagesziel 2 ist gedeckt
> … Runbook: Actions → Content-Engine v2 → Phase 1.

Alles wahr — und alles folgenlos. Die Kapazität war nie das Problem des
05.10. Wer dem Runbook folgte, fand einen einzigen, roten Engine-Lauf von
14:32, dessen Fehlerbild (Synchronverlust) um 18:06 bereits geheilt war.
Nirgendwo stand: „4 von 7 Slots nie gestartet, 2 davon nach heutigem
Merge-Nachholbar.“ Ein Alarm, der die Ursache verschweigt, erzeugt
Recherche-Arbeit statt Entscheidungen — exakt der Befund, für den
`engine_issue._diagnose()` in #521 erfunden wurde. Die Diagnose kannte
Themen, Bahnen und Fachfreigabe-Stapel — aber nicht die Läufe des Tages.

### Warum der Backstop nur EINEN Artikel rettete (D3, bereits #594)

Um 19:22 stand `data/reserve-readiness.json` auf `ready: 0, pool_size: 1`
(Stand 17:34:59): Die 8 Roh-Reserven vom Morgen fielen an den Gates (Audit:
14 Gate-Ablehnungen zwischen 16:13 und 17:36), der Janitor löschte sie samt
des Engine-Entwurfs (c56382b2 — der Löschbeweis steht wörtlich im
#594-Bericht), und die 14 reifen Entwürfe im Bestand waren vom Pool
abgeschnitten (B1). Der Backstop wählte aus dem, was blieb: die
DSL-Reserve (gate-fertig, zertifiziert) → LIVE. Büroausstattung (frisch,
Risikoklasse „erhöht“) → Gate-Ablehnung, korrekt. Damit war der Tag bei
1/2 — ehrlich, aber vermeidbar: #594 wurde um 19:57 gemergt, **35 Minuten
nach dem Backstop**. Der Pool steht seitdem bei 5 gate-fertigen Kandidaten.

---

## Die Dauerheilung

### 1. Slot-Wache (`scripts/slot_wache.py`, neu) — verpasste Slots werden nachgeholt, nicht beklagt

Vier Schichten, jede eine Lehre aus diesem Tag:

**a) Der Soll-Plan kommt aus den Workflow-Dateien selbst — geparsed, nie
abgetippt.** `slots_fuer_tag()` liest die cron-Zeilen aus
`content-engine-v2.yml` und `kadenz-endkontrolle.yml`. Wer den Plan
verschiebt, verschiebt die Wache mit. Nicht verstandene cron-Syntax
(Schritte, Bereiche, datumgebundene Ausnahmen) wird **abgelehnt und
gemeldet**, nie geraten — eine Wache, die einen Plan nur gibt zu verstehen,
wäre schlimmer als keine. Die cron-Wochentagszählung (Sonntag = 0) wird
korrekt auf Python (Montag = 0) gewandelt; ein Selbsttest friert die
Wandlung ein.

**b) Das Urteil folgt der Newsletter-Disziplin.** Ein Slot gilt nach
**Soll + 45 Minuten Gnadenfrist ohne einzigen Laufversuch** als verpasst.
Ein FEHLGESCHLAGENER Lauf bedient den Slot (er ist laut, Alerting kümmert
sich — automatische Wiederholung wäre Betreiber-Entscheid), ein LAUFENDER
ebenso. Die Gnadenfrist ist eine bewusste Entscheidung, kein Vorschlag:
`GNADENFRIST = 45 min` ist im Test eingefroren. Beobachtete Latenz an
diesem Tag: 22 min (normal, verschont) und 2 h 47 min (verpasst — und
hätte nachgeholt).

**c) Der Eingriff ist begrenzt und idempotent.** Nur an Publikationstagen
(SSOT `cadence_guard.PUBLICATION_DAYS`), nur solange LIVE < Mindestziel
(SSOT `cadence_guard.effective_limits()`), und **ein Nachhol-Dispatch je
Workflow und Wachen-Tick** — für den ältesten verpassten Slot. Der
dispatchte Lauf zählt selbst als „bedient“; eine Schleife ist
konstruktionell ausgeschlossen (der nächste Tick findet ihn im Laufbuch).
Kommt der verschobene cron doch noch, reiht die gemeinsame
concurrency-Gruppe `content-bot` ihn ein; das Kadenz-Gate deckelt 2–3 LIVE,
und `reserve_pool` wacht über die Mitternachtsgrenze. Der Dispatch trägt
keine Sonderfreigabe — er startet exakt denselben Workflow, den der cron
gestartet hätte.

**d) Die Notmeldung.** Nach dem letzten Slot + Gnadenfrist mit weiter
offener Quote meldet die Wache das Defizit selbst
(`engine_issue.py --deficit`) — aber nur, wenn noch kein offenes
Defizit-Issue existiert, und nur, wenn kein Nachhol-Lauf mehr laufen kann
(sonst klänge der Alarm, während die Heilung läuft). Damit geht der Alarm
auch an einem Tag raus, an dem **jeder** cron UND jeder Dispatch versagt —
die Lücke, durch die #601 heute fast 24 Stunden lang niemanden erreicht
hätte, hätte die Kadenz um 19:22 nicht doch noch angekommen.

**e) Eine blinde Wache handelt nicht.** Ist das Laufbuch eines Workflows
nicht lesbar (API-Ausfall), zeigt der Bericht für dessen Slots
**„unbekannt“** statt „verpasst“ — und es wird **nicht blind dispatcht**:
Ein vermeintlich verpasster Slot könnte längst laufen. Der Befund wird
laut (rc=1), nicht aktiv. Dasselbe gilt für das Slot-Protokoll im
Defizit-Issue: Scheitert eine Messung, entfällt das ganze Protokoll
(fail-open mit Hinweis) — eine Tabelle, die „verpasst“ zeigt, weil die
Messung blind war, würde die Ursache erfinden statt sie nennen.

### 2. Eigener Takt (`slot-wache.yml`, neu): häufige Ticks statt einem einzigen Haken

Die Wache tickt **alle 20 Minuten** (72 Läufe/Tag, an Ruhetagen ein
Sekunden-No-Op mit Exit 0). Ein Netz am selben Haken wie die Last ist kein
Netz (Vorfall 25.09.) — aber 72 Ticks verlieren selbst dann nicht ihre
Funktion, wenn die Hälfte aller Ticks verworfen wird: Es bleibt ein Tick
pro Stunde. Dazu drei weitere Zufahrten:

* `workflow_dispatch` — Menschen (und künftige Taktgeber) können erzwingen.
* `push` auf die eigenen Pfade — **die Wache beweist sich bei jedem Merge**
  (wie die Newsletter-Wache seit 25.09.: „Merge = Nachholen“).
* `failure`-Annotation + Eintrag in der Wacht-Liste des Fehler-Alertings —
  kann sie selbst nicht nachholen (fehlende Rechte, Netz), wird der
  Befund laut. Ein Wächter, der schweigt, wäre die alte Lücke neu.

### 3. Das Defizit-Issue nennt die Ursache (`scripts/engine_issue.py`)

`_diagnose()` hängt jetzt das **Slot-Protokoll des Tages** an den Alarm:
Soll-Slots, davon verpasst, LIVE-Zahl — plus eine Tabelle mit jedem Slot,
Soll-Zeit, Zustand und dem bedienenden Lauf. Fail-open: Eine kaputte
Diagnose darf den Alarm nie verschlucken (derselze Grundsatz wie in #521).
Das heutige Issue hätte dann gelesen:

```
### Slot-Protokoll des Tages
Soll-Slots heute: 7 · verpasst: 2 · LIVE: 1/2
| Content-Engine v2   | 17:40 | verpasst | – |
| Kadenz-Endkontrolle | 19:35 | verpasst | – |
```

— und niemand hätte in der Themen-Kapazität gegraben.

### 4. Vertrag statt Hoffnung

* `governance_contract.GUARDS` verlangt künftig den Selbsttest der
  Slot-Wache (C6) — eine Wache, die niemand verlangt, führt irgendwann
  niemand mehr aus (gleiche Begründung wie bei newsletter_cadence).
* Der Workflow-Vertrag ist eingefroren: Selbsttest VOR der Messung,
  `actions: write` + `issues: write`, 20-Minuten-Takt, und — die
  Voraussetzung des Heilens — `workflow_dispatch` in Engine und Kadenz
  bleibt bestehen (Test wird rot, wenn jemand es entfernt).
* Die Anleitung `docs/ANLEITUNG-ENGINE-KAPAZITAET.md` hat einen Abschnitt
  „Wenn die Slots gar nicht erst starten“, und `CLAUDE.md` dokumentiert
  die Dauervorgabe „Verpasste Slots werden nachgeholt, nicht beklagt“.

---

## Belege

### Der Vorfall, nachgestellt (ohne Netz)

`slot_wache.py --selftest`: **33 Fälle grün**, darunter der komplette
05.10. mit echten Laufzeiten (06:10/14:10 durch den 14:32-Lauf bedient,
17:40 verpasst, Kadenz 10:35/16:35 durch den 19:22-Lauf bedient, 19:35 in
der Gnadenfrist, Quote 1/2 → Nachhol-Dispatch Engine), die exakte
Gnadenfrist-Grenze (06:54 wartet / 06:56 verpasst), rote und laufende
Läufe als „bedient“, ein Dispatch je Workflow, das Defizit-Fenster, der
Ruhetag, Müll-Timestamps, die cron-Syntax-Kanone und die blinde Messung
(unbekannt statt verpasst, kein Dispatch).

### Trockenlauf gegen die echten Laufbücher (20:29 UTC)

`python3 scripts/slot_wache.py --pruefen --ohne-dispatch --md --repo …`
liefert das Slot-Protokoll aus dem Befund oben — gegen die ECHTEN
GitHub-Laufbücher, ohne einen einzigen Schreibzugriff. Das Werkzeug, das
in CI entscheidet, ist dasselbe, mit dem der Befund erhoben wurde.

### Tests

| Lauf | Ergebnis |
|---|---|
| `python3 scripts/slot_wache.py --selftest` | **33 Fälle grün** |
| `python3 -m unittest scripts.tests.test_slot_wache` | **29 Tests, OK** |
| `npm run test:engine:slots` | Selbsttest + Unit-Tests grün |
| Bestands-Suite (`python3 -m unittest discover -s scripts/tests`) | grün (keine Regression; engine_issue unverändert robust, fail-open geprüft) |

### Selbstsabotage-Proben

| Sabotage | Ergebnis |
|---|---|
| `GNADENFRIST` still verdoppelt | `test_sabotage_gnadenfrist_wird_rote_wache` rot — die Frist ist Vertrag |
| `workflow_dispatch` aus der Engine entfernt | `test_engine_und_kadenz_sind_dispatchfaehig` rot — ohne Dispatch keine Heilung |
| Slot-Wache aus der Alerting-Wacht-Liste gestrichen | `test_wache_steht_in_der_wacht_liste_des_alertings` rot — ein stummer Wächter wäre die alte Lücke |
| Slot-Wache aus `governance_contract.GUARDS` entfernt | `test_wache_im_governance_vertrag` rot — der Vertrag muss den Selbsttest verlangen |
| Slot-Protokoll aus `engine_issue._diagnose()` entfernt | `test_defizit_issue_nennt_slot_protokoll` rot — der Alarm muss die Ursache nennen |
| Laufbuch-Messung kippt auf „verpasst“ statt „unbekannt“ | `test_blinde_messung_handelt_nicht` rot — eine blinde Wache darf nicht handeln |

---

## Was bewusst **nicht** getan wurde

* **Der 05.10. wird nicht nachträglich grün gerechnet.** Der Tag endete mit
  1/2 LIVE, weil 4 Slots nie starteten und zwei weitere Fehler (D2, D3)
  erst am Abend geheilt wurden. Repariert ist die Ursache, nicht die
  Statistik. Ob der 21:35-Slot oder ein Nachhol-Dispatch den Tag doch noch
  auf 2/2 hebt, entscheidet die Maschine selbst — über die reguläre
  Kadenz-Endkontrolle und die neue Slot-Wache, nicht über eine
  Handveröffentlichung.
* **Kein zweites cron-Netz erfunden, das wieder nur an GitHub hängt.** Die
  Wache erhöht die Tick-Frequenz (20 min) und ist per `workflow_dispatch`
  auch extern anrufbar — der Cloudflare-Worker-Taktgeber der Newsletter-
  Linie ist das Vorbild für eine spätere fünfte Zufahrt, aber sie wurde
  nicht spekulativ mitgebaut.
* **Kein Auto-Retry für FEHLGESCHLAGENE Läufe.** Ein roter Lauf ist laut
  und gehört dem Alerting und dem Betreiber; die Wache holt nur nach, was
  NIE gestartet ist. Sonst würde sie jedem Gate-Fehler einen zweiten,
  dritten, vierten LLM-Lauf hinterherschicken.
* **Die Fachfreigabe-Bahn blieb zu.** 8 Hochrisiko-Artikel warten auf
  Frank (Limit 3) — per Beschluss C15 nicht automatisierbar. Auch an einem
  Defizittag verbrennt ein YMYL-Artikel keinen LIVE-Slot.
* **Keine zweite Kalender- oder Limit-Liste.** Publikationstage, Minimum
  und Maximum kommen aus `cadence_guard` (SSOT); die Soll-Slots aus den
  Workflow-Dateien (SSOT); das Defizit-Label und der Issue-Marker aus
  `engine_issue` (SSOT). Die Wache besitzt selbst keine einzige dieser
  Wahrheiten.

---

## Offen (kein Automatik-Thema)

* Der 21:35-Kadenz-Slot und die ersten Ticks der Slot-Wache entscheiden
  heute Nacht, ob der Tag noch auf 2/2 kommt. Danach schließt die
  Defizit-Wache das Issue automatisch, sobald ein Lauf `n ≥ 2` misst.
* Die 8 YMYL-Artikel in der Fachfreigabe bleiben redaktionelle Arbeit
  („Redaktionelle YMYL-Prüfqueue“, #586/#591).
* Als mögliche fünfte Zufahrt bleibt ein externer Taktgeber (Cloudflare-
  Worker-Cron, wie bei der Newsletter-Linie) notiert — der
  `workflow_dispatch`-Eingang der Wache ist dafür bereits vorbereitet.

---

## Bedienung

```bash
npm run engine:slots             # Slot-Lage in einem Blick (Trockenlauf)
python3 scripts/slot_wache.py --pruefen           # zählt + holt nach (CI)
python3 scripts/slot_wache.py --pruefen --ohne-dispatch --md   # Bericht
npm run test:engine:slots        # Selbsttest + 29 Unit-Tests
```

Anleitung für den Störfall: `docs/ANLEITUNG-ENGINE-KAPAZITAET.md`,
Abschnitt „Wenn die Slots gar nicht erst starten“.

---

## Geänderte Dateien

| Datei | Änderung |
|---|---|
| `scripts/slot_wache.py` | **neu** – Slot-Plan aus Workflow-Dateien, Urteil + Nachhol-Dispatch, Defizit-Notmeldung, Selbsttest (33 Fälle) |
| `.github/workflows/slot-wache.yml` | **neu** – 20-Minuten-Takt, Selbsttest vor Messung, Notfall-Annotation, Merge-Selbstbeweis |
| `scripts/engine_issue.py` | `_diagnose()` hängt das Slot-Protokoll des Tages an das Defizit-Issue (fail-open) |
| `scripts/tests/test_slot_wache.py` | **neu** – 28 Tests: Plan, Urteil, Grenzen, Workflow-Vertrag, Sabotage-Proben |
| `scripts/governance_contract.py` | Slot-Wache in `GUARDS` (C6 verlangt ihren Selbsttest) |
| `.github/workflows/alert-on-failure.yml` | Slot-Wache in die Wacht-Liste (kann sie nicht heilen, muss es laut werden) |
| `package.json` | `engine:slots` + `test:engine:slots` |
| `docs/ANLEITUNG-ENGINE-KAPAZITAET.md` | Abschnitt „Wenn die Slots gar nicht erst starten“ |
| `CLAUDE.md` | Dauervorgabe „Verpasste Slots werden nachgeholt, nicht beklagt“ |
