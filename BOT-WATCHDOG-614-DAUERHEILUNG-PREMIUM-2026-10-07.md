# Bot-Watchdog · Content-Reserve · Vorgang #614 — Dauerheilung auf Premium-Niveau

**Datum:** 07.10.2026 · **Issue:** #614 („⚠️ Bot-Watchdog: Automatisierung braucht Eingriff", Label `bot-watchdog`, offen seit 06.10.2026 15:23 UTC)
**Workflow:** `.github/workflows/content-reserve.yml` (letzter abgeschlossener Lauf `37607427999`, 07.10. 10:26 UTC; laufender Nachweislauf `37645894042`, 07.10. 15:40 UTC)
**Reparatur-Vorschlag:** PR **#626** („Closes #614") · **Vorgänger:** #585 (Lesbarkeits-Gate), #594 (Blocker-Klassen), #609 (Lesbarkeits-Heiler), #610 (Audit-Ledger)

## Kurzfassung

#614 war **kein Textproblem und kein Werkzeugausfall**. Der Befund hat zwei
Hälften – und die erste ist die Folge der zweiten:

> Von zehn geparkten Reserve-Kandidaten trugen **drei einen harten
> Textverständnis-Fund, für den es keinen Heiler gab** (R14-Marker-Ruine
> „SATZ:", R7-Intro-Formel, R15-PHrasen-Doppel). Das Zertifikat notierte dazu
> wörtlich „manuell reparieren". Zugleich verwirft das Tor **T2** des
> Lesbarkeits-Heilers jede Schrift, die danach noch einen harten Fund trägt.
> **Jede KI-Heilung dieser drei Artikel war damit von vornherein
> aussichtslos:** Der Heiler hatte eine Deckung, aber keine Wirkung – und der
> Vorrat blieb bei 2/6.

Die Dauerheilung schließt die Lücke **an der Wurzel**, in fünf Lagen: ein
Heiler für die Klasse, die richtige Stelle in der Kette, Vorbeugung an der
Quelle, ein Vertrag, der beides verlangt – und ein Lauf, der seinen
Blocker-Verlauf endlich im Repo hinterlässt, statt nur im Log.

## Befund

### Was das Ticket meldet (Zitat, gekürzt)

> **P2 · Content-Reserve niedrig** (Maschine) – Reserve unter Mindestbestand
> (2 gate-fertige Artikel (Ziel 6, Alarm unter 4), 12 Reserve-Entwürfe;
> Blocker: Lesbarkeits-Gate nicht bestanden: Flesch 57.9 …) →
> `data/reserve-readiness.json` auf konkrete Gate-Blocker prüfen; anschließend
> den letzten Lauf von `content-reserve.yml` kontrollieren und mindestens
> **4 zertifizierte Kandidaten** herstellen.

### Die Gate-Blocker (Zertifikat 07.10. 13:20 UTC, `data/reserve-readiness.json`)

| # | Kandidat (Slug, gekürzt) | Blocker im Zertifikat |
|---|---|---|
| 1 | `2026-10-05-bueroausstattung-steuerlich-clever-absetzen…` | ✅ **bereit** (Score 0,958) |
| 2 | `2026-10-07-handyvertrag-kuendigen-raus-aus-der-kostenfalle…` | ✅ **bereit** (Score 0,966) |
| 3 | `2026-10-07-dein-weg-zu-geringeren-monatskosten…` | Flesch 57,9 **+ R15-PHRASEN-DOPPEL** |
| 4 | `2026-10-07-dsl-anbieter-wechseln…` | Flesch 59,4 **+ R7-INTRO-FORMEL** |
| 5 | `2026-10-07-wie-smart-home-geraete-deine-stromrechnung-wirklich-druecken…` | **R14-MARKER-RUINE („SATZ:")** |
| 6 | `2026-10-07-haushaltskosten-reduzieren…` | Flesch 59,9 |
| 7 | `2026-10-07-heizoel-preise-2026…` | Zeichenlänge (`check_length.py`) |
| 8 | `2026-10-07-stromkosten-senken…` | Lesbarkeits-Score 70/100 (Flesch 52, 2 Absätze > 4 Sätze, 9 Passiv) |
| 9 | `2026-10-07-urlaub-sparen…` | Flesch 58,8 |
| 10 | `2026-10-07-vpn-zuhause…` | Flesch 55,8 |
| 11 | `2026-10-07-waermepumpe-vs-gasheizung…` | Flesch 53,1 |
| 12 | `2026-10-07-etf-sparplan-starten…` | quality-score 0,839 (structure 0,70) |

Ziel 6 · bereit **2** · Pool 12 · `recert` erneuert: `etf-sparplan`,
`heizoel`, `urlaub-sparen`.

### Der letzte Lauf von `content-reserve.yml` (Lauf 37607427999)

**Steps 1–16 grün** – Hugo Extended, hunspell, Selbsttests aller Wachen,
Janitor, Bestands-Wächter, Kandidaten-Erzeugung, Veredelungs-Kette,
Zertifizierung, Konvergenz (3 Runden / 45 min), Triage, Staging, Push.
**Rot war nur Step 17** („Stock shortage must not look successful",
`reserve_gate.py`); Steps 18/19 wurden deshalb übersprungen.

Der Befund ist damit präzise: **Die Kette lief. Das Ziel wurde verfehlt.**
Das harte End-Gate hat genau das gemeldet, wofür es gebaut ist – „ein
Engpass darf nicht wie Erfolg aussehen". Die Ursache lag nicht im Lauf,
sondern in einer Lücke der Kette, die sechs Tage lang unsichtbar war.

### Die eigentliche Ursache: eine Besitz-Lücke in der Kette

Drei Beobachtungen greifen ineinander:

1. **Das Zertifikat benennt den Fund als unheilbar.** Für die drei Kandidaten
   stand dort ein *harter* Fund der Regeln R7/R14/R15 – genau der Regeln, die
   `publish_gate.HARTE_REGELN` als ablehnend führt.
2. **Der Deckungsbericht führte die Klasse trotzdem als „gedeckt"**, weil für
   `textverstaendnis_failures` zwei Heiler eingetragen waren
   (`r5_absatz_splitter.py`, `fix_url_hygiene.py`) – beide kurieren ganz andere
   Defekte (Absatzlänge, URL-Hygiene) als einen Marker-Rest oder ein
   Phrasen-Doppel. **Ein Name in der Kette ist eine Behauptung; erst die
   Wirkungsprobe ist ein Beweis.**
3. **Das Tor T2 macht die Lücke tödlich.**
   `lesbarkeit_heiler.verifiziere()` verwirft jede Heilung, die danach noch
   einen harten Textverständnis-Fund trägt:

   ```python
   neue_funde = harte_funde(neu_raw, slug)
   for regel in sorted(neue_funde):
       gruende.append(f"T2 Textverständnis: harter Fund {regel} im Ergebnis")
   ```

   Für einen Artikel mit R14/R15-Rest heißt das: **Die Flesch-Heilung wird nie
   geschrieben.** Lokal reproduzierbar (Sandbox, ohne KI-Schlüssel):

   ```
   $ python3 scripts/lesbarkeit_heiler.py --file content/posts/…dein-weg…/index.md
   Stufe A hob intern auf Flesch 58.1 …
   🛑 T1 Lesbarkeit: Flesch 58.1 < Schwelle 60  →  verworfen
   ⚠ Stufe B (Versuch 1): keine KI-Antwort  →  fail-closed, Text unangetastet
   ```

   Zwei Tore, dieselbe Wirkung: Der Text bleibt stehen – nicht weil die
   Schwelle zu hoch wäre, sondern weil vorher niemand den Rest entfernt.

### Woher die Reste kommen (Quell-Prävention, nicht Kosmetik)

* **R14 „SATZ:"** – Die Prompt-Vorlage in `lektor_guard.l5_ai_rewrite()`
  beginnt mit `SATZ: {satz}`. Antwortet das Modell mit genau diesem Präfix,
  landete es unverändert im Fließtext (Realfall: smart-home-Artikel, Zeile
  mit Markdown-Tabelle). Dieselbe Vorlagen-Klasse in `dash_guard.py`.
* **R7/R15** – `keyword_optimizer.heal_intro()` stempelt die Intro-Formel und
  läuft in der Kette **zweimal** (`--fix --include-drafts`, an zwei Stellen).
  Ohne Idempotenz-Guard entstehen Doppel- und Dreifach-Präfixe
  („Dein Weg zu geringeren im Check: Dein Weg zu geringeren im Check: …").
* **R11/R13** – Zahlen-/Datums-Ruinen aus früheren Politur-Läufen
  („20 26", „2 Januar").

### Zweite Lücke: der Lauf hinterließ keinen Blocker-Verlauf

Beim Nachweis fiel auf, dass `data/reserve-history.jsonl` auf `main`
**keinen einzigen CI-Lauf** enthielt – nur „lokal"-Zeilen vom 02.10. Ursache:
Das End-Gate ist der **letzte** Schritt; seine Chronik-Zeile entstand erst
**nach** Commit und Push. Damit war „warum hebt Lauf N diesen Kandidaten
nicht?" nur aus einem Log zu beantworten, das niemand aufbewahrt.

## Dauerhafte Reparatur (fünf Lagen)

### 1. `scripts/politur_heiler.py` (neu) – der fehlende Heiler der Klasse

| Eigenschaft | Umsetzung |
|---|---|
| Regeln | R7, R11, R13, R14, R15, R16 (R12 bleibt liegen: Ersetzungs-Ruine, nicht automatisch entscheidbar) |
| SSOT | Muster aus `sprachkern.POLITUR_RUINEN`, Intro-Formeln aus `tv.INTRO_FORMELN`, Wiederholungs-Schwelle `tv.R15_N`, Zielregeln `pg.HARTE_REGELN`, Naht `post_utils.join_article` – alles **gelesen, nicht abgetippt** |
| Tor T1 | nur strikte Teilmenge der vorherigen Funde; kein neuer harter Fund |
| Tor T2 | Frontmatter bytegleich, Links, `/go/`-Anker, Überschriften, Shortcodes, Tabellenzellen, Zahlen; Wortzahl ≥ 90 % |
| Tor T3 | ohne Wirkung kein Schreiben (Text unverändert ⇒ niemals „geheilt") |
| Verhalten | idempotent; Markup wird nie zerschnitten; R15 behält das **letzte** Vorkommen (der fortsetzende Satzrest hängt daran) |
| CLI | `--file`, `--reserve`, `--blocked`, `--fix`, `--auch-live`, `--max`, `--json`, `--report`, `--wirkungsprobe`, `--selftest` |
| Exit-Code | 0 heißt in **jeder** Betriebsart „nichts mehr zu heilen": sauberer Text, geschriebene Heilung. Trockenlauf mit heilbarem Rest und verworfene Heilung sind **offene Punkte** (1) – ein Trockenlauf darf nie „Pool ist sauber" behaupten |

### 2. Ketten-Ordnung: Politur läuft **vor** dem Lesbarkeits-Heiler

```python
("politur_heiler.py", ["--fix"], "file"),
("lesbarkeit_heiler.py", ["--fix"], "file"),
```

Die Reihenfolge ist kein Geschmack, sondern die direkte Folge von T2: Läuft
der Lesbarkeits-Heiler zuerst, verwirft er seine eigene Heilung an einem Rest,
den niemand vorher entfernt hat.

### 3. Quell-Vorbeugung in `lektor_guard.py`

`_ohne_marker_echo()` entfernt ein Prompt-Präfix am Anfang der KI-Antwort,
**bevor** daraus eine Zeile im Artikel wird. Die Muster kommen aus derselben
SSOT, die sie sonst als Ruine melden (`sprachkern.POLITUR_RUINEN`, R14/R16);
bleibt nur der Marker übrig, ist das Ergebnis leer und die Aufrufer lehnen ab
(fail-closed). Ein normaler Satz bleibt unberührt – auch „Satz:" in
Kleinschreibung, das keine Ruine ist.

### 4. Vertrag: Deckung **und** Wirkung

* `reserve_healer_coverage.REGEL_HEILER["textverstaendnis_failures"]` führt
  jetzt `politur_heiler.py` – als **ersten** in der Liste.
* `WIRKUNGS_PROBEN["politur_heiler.py"] = ("--wirkungsprobe",)`, und
  `PROBEN_PFLICHT` verlangt die Probe für `textverstaendnis_failures`.
* `governance_contract.GUARDS` nimmt den Heiler ins vertragliche Minimum
  (C6) – sein Selbsttest läuft damit im Qualitäts-Gate, unter der Uhr-Probe
  (+97/+1461 Tage) und unter dem Schreibfreiheits-Check (C15).
* `scripts/tests/test_politur_heiler.py` (16 Tests) friert ein: Wirkung,
  Fail-closed-Verhalten (Trockenlauf, verworfene Heilung, Idempotenz),
  SSOT-Bindung, Quell-Vorbeugung für **jeden** Marker der SSOT und die
  Ketten-Ordnung – inklusive des *Grundes*: Nach der Politur darf kein
  harter Fund übrig bleiben, sonst verwirft T2 (und zwar messbar).

### 5. Nachweis und Gedächtnis

* `scripts/reserve_gate.py --chronik` schreibt genau **eine** Zeile pro Lauf
  (bereit, Ziel, Blocker-Slugs, Lauf-ID) – Pfad über `RESERVE_HISTORY`
  umlenkbar, damit Tests nicht ins echte Gedächtnis schreiben.
* `content-reserve.yml` ruft diese Bahn im Sicherungs-Schritt **vor** dem
  Staging auf. Der Blocker-Verlauf erreicht damit `main`, und die Frage
  „warum hebt Lauf N den Kandidaten nicht?" ist aus dem Repo beantwortbar.
* `.github/workflows/reserve-nachweis.yml` (neu, **nur** `workflow_dispatch`)
  fährt dieselben Stufen 2/3/4 auf einem beliebigen Ref, lässt das Löschrecht
  (Janitor) bewusst aus, sichert ausschließlich auf den eigenen Ref und prüft
  am Ende die Ticket-Akzeptanz (≥ 4 zertifizierte Kandidaten) als harten
  Schritt. Das ist der Weg, eine Reparatur **vor** dem Merge mit echten Gates
  zu beweisen – der Produktionslauf bleibt `content-reserve.yml` auf `main`.

## Nachweis

### Geheilte Kandidaten (Diff, vollständig)

```
 dein-weg…/index.md      | 2 +-
 dsl-anbieter…/index.md  | 2 +-
 wie-smart-home…/index.md| 2 +-
```

| Kandidat | vorher | nachher |
|---|---|---|
| `dein-weg…` | „Dein Weg zu geringeren im Check: Dein Weg zu geringeren im Check: Dein Weg zu geringeren im Check – stell dir vor…" | „Dein Weg zu geringeren im Check – stell dir vor…" |
| `dsl-anbieter…` | „**In diesem Artikel** erfährst du, wie du effektiv …" | „**Hier** erfährst du, wie du effektiv …" |
| `wie-smart-home…` | „`SATZ: | Thread | 2,4 GHz | …`" | „`| Thread | 2,4 GHz | …`" (Tabellenzeile intakt) |

### Messung nach der Heilung (lokale Korpus-Prüfung mit den echten Wachen)

| Kandidat | hart vorher | hart nachher | Flesch (lokale Messung) |
|---|---|---|---|
| `dein-weg…` | R15-PHRASEN-DOPPEL | **—** | 57,8 |
| `dsl-anbieter…` | R7-INTRO-FORMEL | **—** | 59,5 |
| `wie-smart-home…` | R14-MARKER-RUINE | **—** | 62,7 ✅ |
| alle übrigen 9 | — | — | 52,3–65,8 |

**Ergebnis: Kein Reserve-Entwurf trägt nach der Heilung noch einen harten
Textverständnis-Fund** (`tv.check_article(…) ∩ pg.HARTE_REGELN = ∅` für alle
12). Damit ist der strukturelle Block weg: Die verbleibenden Blocker sind
reine Flesch-/Score-/Längen-Fälle – genau die Klasse, für die die KI-Stufe der
Kette zuständig ist und die vorher an T2 scheiterte.

### Tests und Verträge (lokal, ohne Netz, ohne Hugo)

| Prüfung | Ergebnis |
|---|---|
| `python3 -m unittest scripts.tests.test_politur_heiler` | **16 Tests OK** |
| `python3 -m unittest scripts.tests.test_reserve_pipeline` | **113 Tests OK** (inkl. 2 neuen Chronik-Verträgen) |
| `python3 -m unittest …test_reserve_pipeline test_lesbarkeit_heiler test_politur_heiler test_bot_watchdog_routing` | **177 Tests OK** |
| `politur_heiler.py --selftest` / `--wirkungsprobe` / `--reserve` (Pool sauber) | Exit 0 |
| `selftest_clock.py --trap scripts/politur_heiler.py --offset 97 / 1461` | grün (uhrfest) |
| `governance_contract.py --selftest` | C1–C27 bestanden |
| `reserve_healer_coverage.py` | 12 Regeln · 10 gedeckt · 2 begründete Ausnahmen · **0 Lücken**; Wirkungsnachweise für `lesbarkeit_heiler.py` (Flesch 51,3 → 72,3) und `politur_heiler.py` (5 harte Funde behoben, T1–T3, idempotent) |
| Datenbestand | `git checkout`-geprüft: keine Sandbox-Läufe in `data/` (Zertifikat, Custody, Quarantäne, Historien unberührt) |

## Verifikation nach dem Merge (die letzten Zentimeter)

Das Zertifikat darf nur von den **echten** Produktions-Gates ausgestellt
werden (Hugo-Build, hunspell, Zeichenlängen-Politik, KI-Stufe). Deshalb gilt:

1. **Nach dem Merge** läuft `content-reserve.yml` (nächtlich 03:25 UTC oder
   per Watchdog-Dispatch) und schreibt ein neues
   `data/reserve-readiness.json`. Erwartung: **≥ 4 ready**, und die
   Flesch-Werte der bisher geparkten Kandidaten müssen sich **bewegen**
   (Beweis, dass die KI-Stufe greift und T2 sie nicht mehr verwirft).
2. **Sofortnachweis auf einem Ref:** `Reserve-Nachweis (Probe auf einem Ref)`
   per `workflow_dispatch` – schreibt den Nachweis nur auf den gestarteten
   Ref und prüft die Akzeptanz (≥ 4) als harten Schritt.
   *Hinweis:* GitHub registriert dispatchbare Workflows erst mit ihrer Datei
   auf dem Default-Branch; die Probe ist deshalb erst nach dem Merge
   startbar.
3. **Was offen bleibt** und im nächsten Zertifikat beantwortet wird:
   * ob die KI-Stufe (`gemini-3-flash-preview` → Groq-Fallback) im
     Produktionslauf tatsächlich Flesch ≥ 60 erreicht – die drei
     T2-blockierten Kandidaten sind ab jetzt beweisbar *heilbar*;
   * `etf-sparplan` (structure 0,70) – dafür gibt es bis heute keinen
     eigenen Heiler; die Chronik macht den Verlauf sichtbar.

## Geänderte Dateien

| Datei | Änderung |
|---|---|
| `scripts/politur_heiler.py` | **neu** – Heiler der Klasse (R7/R11/R13/R14/R15/R16), Tor T1–T3, Wirkungsprobe, Selbsttest |
| `scripts/tests/test_politur_heiler.py` | **neu** – 16 Regressionstests (Wirkung, Fail-closed, Quell-Vorbeugung, Verdrahtung) |
| `scripts/lektor_guard.py` | Quell-Vorbeugung `_ohne_marker_echo()` (R14/R16-Marker aus KI-Antworten) |
| `scripts/reserve_finisher.py` | Kette: Politur **vor** Lesbarkeit, mit Begründung |
| `scripts/reserve_healer_coverage.py` | Deckung + Wirkungsprobe + Probenpflicht für die Textverständnis-Klasse |
| `scripts/governance_contract.py` | Heiler ins vertragliche Minimum (C6) |
| `scripts/reserve_gate.py` | `--chronik` (eine Zeile pro Lauf, `RESERVE_HISTORY`-Seam) |
| `.github/workflows/content-reserve.yml` | Chronik **vor** dem Staging (Blocker-Verlauf erreicht `main`) |
| `.github/workflows/reserve-nachweis.yml` | **neu** – Probe auf einem Ref, nur `workflow_dispatch` |
| `scripts/tests/test_reserve_pipeline.py` | 2 Verträge: Chronik-Reihenfolge + genau eine Zeile |
| `content/posts/2026-10-07-{dein-weg…,dsl-anbieter…,wie-smart-home…}/index.md` | geheilt (3 × 1 Zeile) |

---

## Nachtrag 07.10.2026, ~16:45Z – der zweite Befund: der Vorrat blutete

### Befund (Belege, keine Vermutung)

* Lauf `37645894042` (07.10., fertig 16:15Z): Zertifikat **2/6**, **`pool_size` 2** – vorher 12.
* Die zehn verschwundenen Kandidaten tragen auf `main` im Frontmatter
  `reserve_blocked` + `reserve_blocked_at: 2026-10-07T16:07:55Z` – aber **keine**
  `reserve: true`-Fahne mehr (Kontrolle: die zwei verbliebenen Kandidaten tragen sie).
* `data/reserve-custody.json` (main): zehn Einträge `zustand: ausgemustert`,
  `zuletzt_im_pool: 2026-10-07`.
* `data/reserve-quarantine.json` (main): `{}` – die Quarantäne hatte **ihren eigenen
  Beleg schon gelöscht**: `record()` streicht Kandidaten aus dem Zähler, die nicht mehr
  im Pool sind. Genau deshalb war der Verlust im Repo unsichtbar (und nur über die
  vergossenen Frontmatter-Zeilen rekonstruierbar).
* `reserve_readiness.py` (Stufe 3) ruft `reserve_quarantine.record(rows)` auf;
  `record()` entschied **nur nach Laufzahl** (`hits >= RESERVE_QUARANTINE_HITS`), nie
  nach der **Klasse** – obwohl genau dieselben Befunde in der SSOT
  `reserve_blocker_klassen.GATE_BEFUNDE` als **heilbar** geführt werden
  (7× Lesbarkeit, 1× Zeichenlänge, 1× quality-score, 1× Textverständnis).
* Reihenfolge: Stufe 2 (Heiler-Kette) → Stufe 3 (Zertifikat + Ausmusterung). Der
  Bestands-Wächter der Folgeläufe (Stufe 0b) heilt nur **verlorene** Fahnen – nicht
  **ausgemusterte** (Ledger-Zustand `ausgemustert`). Damit war die Ausmusterung eine
  **Einbahnstraße**.

### Die Klasse (nicht der Einzelfall)

Eine Automatik, die Material für einen *heilbaren* Befund dauerhaft aussperrt, wird
genau dann kleiner, wenn die Heiler besser werden. Am 07.10. traf es zehn Kandidaten in
einem Lauf – 100 % der nicht zertifizierten Reserve. Der Watchdog konnte danach nur
noch „Vorrat niedrig" melden; die Ursache (eine Politik, kein Inhalt) stand nirgends
im Repo. Das ist die zweite Hälfte von „Deckung ohne Wirkung": erst heilte niemand die
Klasse (Politur-Heiler, erste Nachtschicht), dann **bestrafte** das System sie.

### Reparatur (vier Schichten)

1. **Klassen-Tor** in `reserve_quarantine.record()`: Ausmustern nur noch, wenn die
   SSOT den Befund als UNHEILBAR führt. Heilbar, Menschsache, Werkzeugfehler und
   Unbekanntes lassen die Fahne stehen (fail-closed); die Schonung wird mit Klasse,
   Heiler und Laufzahl begründet, im Zustand geführt und im Zertifikat als `geschont`
   ausgewiesen. Die Textverständnis-Klasse (R7/R11–R16) ist in der SSOT jetzt als
   heilbar geführt (Politur-Heiler + Absatz-Splitter).
2. **Rückholung mit Beweis** in `reserve_custody.py`: Ein ausgemusterter Kandidat kehrt
   zurück, wenn (a) seine Klasse heilbar ist, (b) ein Heiler der Klasse in der echten
   Kette läuft und (c) dieser Heiler einen **grünen Wirkungsnachweis** hat (C25).
   Setzt Fahne + Belegzeile `reserve_reaktiviert`, Inhalt unberührt, Quarantäne-Zähler
   zurück, idempotent, Trockenlauf schreibfrei. Ohne Beweis bleibt er ausgemustert –
   und wird mit Grund gemeldet. Nebenbei behoben: `RE_DRAFT_ZEILE` fraß mit `\s*$`
   über Zeilenenden (die Fahne konnte am Kopf-Ende landen).
3. **Satz-Heiler** `scripts/satz_heiler.py`: heilt die Lesbarkeits-Klasse satzweise
   mit der KI (die KI sieht nur Sätze ohne Zahlen/Markup, das Ganztext-Tor T1–T4
   entscheidet unverändert; R5-Absätze teilt die SSOT). Kettenglied **vor** dem
   Lesbarkeits-Heiler; Wirkungsprobe grün (Flesch 42 → 67 an der echten Formel);
   in `REGEL_HEILER`, `WIRKUNGS_PROBEN` und `governance_contract.GUARDS`.
4. **Maschinenbeweis** `reserve_healer_coverage.py --vorratsschutz` – läuft in jedem
   CI-Durchgang und prüft mit den **zehn Original-Befunden des Vorfalls**: kein
   Fahnenverlust für Heilbares · Ausmusterung nur für Unheilbares · Unbekanntes bleibt
   fail-closed · Rückholung nur mit Wirkungsnachweis.

### Nachweise (lokal ausgeführt)

| Prüfung | Ergebnis |
|---|---|
| `python3 -m unittest discover -s scripts/tests` | **2032 Tests · OK** (23 skipped) – nach Re-Signatur des Kerns |
| `integrity_guard --drift-audit` / `--gate` | Herkunft `700d903` dokumentiert, neu signiert, Gate **grün** |
| `reserve_healer_coverage --vorratsschutz` | 7 Original-Befunde ohne Fahnenverlust · 1 unheilbare Ausmusterung · 1 fail-closed · 1 Rückholung · 1 Verweigerung ohne Nachweis |
| `reserve_quarantine --selftest` / `reserve_custody --selftest` | grün (inkl. Klassen-Tor und Rückholung als Vertrag) |
| `governance_contract --selftest` | C1–C27 grün |
| `test_reserve_vorratsschutz.py` / `test_reserve_pipeline.py` | 20 / 114 Tests grün |

### Offene Punkte (bewusst benannt)

* **Klassen ohne Wirkungsnachweis**: `zeichenlänge` (check_length → extend_articles)
  und `quality-score` (profi_polish/spellcheck/check_length). Deshalb bleiben
  `heizoel-preise-2026-…` und `etf-sparplan-…` vorerst ausgemustert – ein
  Wirkungsnachweis für diese Klasse(n) gibt sie automatisch zurück.
* **CI-Evidenz**: GitHub hat für die letzten Pushes dieser Session **keine neuen
  `pull_request`-Läufe** ausgelöst; `workflow_dispatch` ist dem Token verweigert
  (HTTP 403). Die vollständige Testentdeckung ist deshalb lokal belegt, das
  Zertifikat (≥ 4) liefert der erste Produktionslauf nach dem Merge.

---

## Nachtrag 2, 07.10.2026 – der dritte Befund: der Stempel stempelt sich selbst

### Warum dieser Nachtrag nötig war

Der zweiten Nachtschicht fehlte noch die Antwort auf die Frage, die seit
Wochen im Zertifikat stand: **warum hebt die KI-Stufe die sieben
Lesbarkeits-Kandidaten nie über die Schwelle?** Die Suche danach hat einen
Fehler gefunden, der gar nichts mit der KI zu tun hat – und der dieselbe Ruine
jede Nacht neu erzeugt hätte, die der Politur-Heiler gerade geheilt hatte.

### Befund (reproduziert, nicht vermutet)

`keyword_optimizer.heal_first_paragraph` prüft, ob das Hauptkeyword schon
vorn steht – in den **ersten 350 Zeichen** – und stempelt sonst den **ersten
Fließabsatz**:

```python
if norm(main_kw) in norm(body[:350]):
    return body                      # Kopf-Wächter
...
paras[first_idx] = f"{main_kw} im Check: {first_para}"   # Stempel
```

In einem Reserve-Entwurf liegen die beiden Fenster auseinander. Am echten
Kandidaten `2026-10-07-dein-weg-…`:

* Divider, Schnell-Tipp-Kasten und Einleitungs-Überschrift stehen davor,
* der erste Fließabsatz beginnt bei **Zeichen 357**,
* der Kopf-Wächter sieht den Stempel also nie.

Ergebnis: Jeder Lauf meldet „Keyword fehlt", stempelt erneut, und der neue
Stempel liegt wieder außerhalb des Fensters. Mit der echten Datei gemessen:

| Aufruf | Stempel „… im Check" im Absatz |
|---|---|
| vorher (Bestand `main`) | 1 |
| 1. Heil-Lauf | **2** |
| 2. Heil-Lauf | **3** |
| 3. Heil-Lauf | **4** |

Die Kette ruft `keyword_optimizer.py --fix --include-drafts` **zweimal je
Nachtlauf** (`reserve_finisher.HEALER_CHAIN`), dazu kommen Konvergenz-Runden
und der Meldelauf – genau so entstand die R15-PHrasen-Doppel-Ruine, an der
der Kandidat aus der Zertifizierung fiel. Die Ruine war also **selbstgebaut**,
und der Politur-Heiler allein hätte sie jede Nacht neu heilen müssen.

### Reparatur (drei Teile, alle am selben Fenster)

1. `erster_para_index()` ist jetzt die **eine Quelle** für Prüfung und Stempel
   (kein Markup, keine Listen, ≥ 20 Zeichen – dieselben Regeln wie zuvor im
   Heiler, nur nicht mehr doppelt implementiert).
2. Der Heiler ist **am Ziel** idempotent: Trägt der erste Fließabsatz bereits
   „<Keyword> im Check:", ist er fertig – auch wenn der Kopf-Wächter ihn nicht
   sieht. Ein zweiter Stempel ist nie ein Qualitätsgewinn.
3. `check_article` zählt den ersten Fließabsatz mit. Vorher meldete die
   Prüfung dauerhaft „Keyword nicht in: Erster Absatz" (Fehlalarm), obwohl der
   Stempel stand – **dieser Fehlalarm hielt die Automatik in Gang.**

### Wachen und Tests (dreifach, nicht einfach)

* `keyword_gate --selftest` prüft die **reale Geometrie** (Stempelabsatz hinter
  Zeichen 350): kein zweiter Stempel, dritter Lauf = Fixpunkt. Ohne den Fix ist
  die Probe rot – nachgestellt und belegt.
* `test_fm_boundaries.StempelIdempotenzTests`: vier Regressionstests, **drei
  davon ohne den Fix rot** (Fixpunkt, Prüf-Sicht, Bestands-Wächter über alle
  73 Artikel).
* Klassen-Wächter über den ganzen Bestand: Für **jeden** Artikel im Repo ist
  `heal_first_paragraph` ein Fixpunkt. Diese Wache hätte den Befund in der
  Nacht seiner Entstehung gemeldet.

### Zusammenführung mit der Schwester-Reparatur (#612) aus `main`

`main` hatte am selben Tag die Geschwister-Ruine repariert
(`politur_ruine_heiler.py`, WF-D4E0) und dafür Klassen-Muster, Deckung und
Governance angepasst. Der Merge wurde **nicht** als Sieger-Entscheid
aufgelöst: der schmale, deterministische Ruinen-Heiler bleibt der **erste**
Schreiber je Ruinen-Muster, der breite Politur-Heiler folgt als Netz für die
restliche Familie (R7/R15/R16). Beide stehen in Kette, Deckung, Probenpflicht
und Governance-Minimum; der Klassen-Vertrag aus #612 („der spezifische Heiler
steht zuerst") ist im Test festgehalten und um die Prüfung erweitert, dass
**jeder** genannte Schreiber existiert und wirklich in der Kette läuft.

### Nachweise nach Reparatur und Merge

| Prüfung | Ergebnis |
|---|---|
| `python3 -m unittest discover -s scripts/tests` | **2058 Tests · OK** (23 skipped) |
| `reserve_healer_coverage --vorratsschutz` | rc=0 – 7 Original-Befunde ohne Fahnenverlust, 1 unheilbare Ausmusterung, 1 fail-closed, 1 Rückholung, 1 Verweigerung ohne Beweis |
| `keyword_gate --selftest` (mit Fix) | grün – mit der #614-Geometrie |
| `keyword_gate --selftest` (ohne Fix, nachgestellt) | rot: „Stempel-Automatik nicht idempotent (Stapel-Ruine #614)" |
| `StempelIdempotenzTests` (ohne Fix, nachgestellt) | 3 von 4 Tests rot |
| `integrity_guard --gate` | grün (47 Kerndateien, Herkunft im Lock) |
| Rückhol-Probe (`reserve_custody --heal`, lokal) | **13 Kandidaten zurück in den Pool**, 4 bleiben mit Grund (Klasse heilbar, aber kein Heiler mit grünem Wirkungsnachweis: `bankgebuehren`, `energieeffizienz`, `etf-sparplan`, `heizoel`) – die Probe wurde nicht committet, der Nachtlauf führt sie selbst aus |

### Offene Restverifikation

Das Zertifikat („≥ 4 zertifiziert") stellt nur der Produktionslauf aus
(Hugo-Bau, hunspell, KI-Stufen). Erwartung nach diesem PR: Die Rückholung
stellt 15 Kandidaten in den Pool, acht davon sind inhaltlich bereits geheilt
(3 politurfrei, 5 ohne harte Funde), und die Lesbarkeits-Klasse hat jetzt eine
Kette, die nicht mehr von unsichtbaren Stempeln blockiert wird. Der nächste
`content-reserve.yml`-Lauf muss das zeigen; der harte End-Gate hält die Zahl
fest.

---

## Nachtrag 3 (07.10.2026) – die Prüfung selbst war eine Zeitbombe

Beim Lesen der CI-Läufe zu diesem PR fiel eine **zweite, unabhängige** rote
Klasse auf – und diesmal lag es nicht an #614:

* `Publication reliability regression tests` war rot. Ursache:
  `test_social_perf_feedback` baute seine Fixtures von der echten Wanduhr
  (`planner.berlin_now() - 2 Tage`), plante aber für den **gepinnten**
  14.09.2026. Ab dem 01.10.2026 lag damit jeder Fixture-Artikel hinter allen
  Slots: kein Kandidat passt mehr, der Plan ist leer, der Test rot – ohne dass
  jemand eine Zeile Code angefasst hätte.
* Beweis, dass es nicht unsere Änderung war: derselbe Fehler reproduziert im
  frischen `origin/main`-Worktree (`5bcc31e`) – zwei rote Tests, exakt dieselben.
* Unsichtbar blieb sie, weil der Workflow **nur auf Pull Requests** läuft (main
  sah ihn nie) und `scripts/selftest_clock.py` bis heute nur Skripte mit
  `--selftest` unter fremde Uhren legen konnte – Testmodule kannte die Probe
  nicht.

### Reparatur (vier Teile, alles im selben PR)

1. **Wurzel**: Der Fixture-Bestand wird jetzt von der gepinnten Plan-Uhr aus
   datiert (`_pool(pn)`), plus ein Eigenschaftstest „der Plan hängt nicht an
   der echten Wanduhr" über drei Uhren (2026, 2027, Jahreswechsel 2030/31).
2. **Werkzeug**: `selftest_clock.trap_modul()` und die CLI-Wege
   `--trap-modul` / `--trap-discover` legen **Unit-Testmodule** unter eine
   vorgestellte Uhr (`0` grün · `1` Datumsbefund · `2` Probe nicht lauffähig –
   ein Importfehler ist kein Datumsbefund, sonst entsteht ein Fehlalarm). Der
   eigene Selbsttest deckt Bombe, festes Modul, Discover und den Alias-Fall ab.
   `uhr(module=…)` biegt jetzt **jeden** Namen um, der auf das echte (oder ein
   Shim-)`datetime`/`time` zeigt – `import datetime as dt` war zuvor eine
   Lücke; und `FFC_FREMD_UHR` macht die fremde Uhr für Tests sichtbar, die
   bewusst den echten Bestand am echten Tag prüfen (sie melden sich mit Grund
   ab, statt zu scheitern).
3. **Vier weitere Zeitbomben geheilt**: `test_social_autopilot` (dasselbe
   Fixture-Muster, 4 rote Tests unter fremder Uhr), `test_reserve_pipeline`
   (Karenz-Fixture wird absolut gestempelt), `test_pflichtcheck` und
   `test_publication_release_wache` (Uhr wird auf den Vertragszeitpunkt bzw.
   einen Publikationstag gepinnt – vorher wäre der erste Test am 01.01.2027 von
   selbst rot geworden, der zweite an jedem Wochenende).
4. **Wache in CI**: neuer Schritt „Uhr-Probe – die Suite muss an jedem
   Kalendertag grün sein" in `publication-reliability-tests.yml`. Er fährt die
   komplette Suite ein zweites Mal unter einer um 97 Tage vorgestellten Uhr.

**Nebenfund** (und der Beweis, dass die verschärfte Probe wirkt): Unter der
STRENGEN Uhr flog ein echter Uhr-Lesezugriff in `reserve_janitor._zaehle` auf.
Der Zähler-Stempel kommt jetzt aus dem Urteils-Tag (`today`, Mittag UTC) statt
aus der Wanduhr – damit ist der Zählerstand für denselben Tag reproduzierbar.

### Nachweis

| Prüfung | Ergebnis |
|---|---|
| `selftest_clock --trap-discover scripts/tests --offset 97` | **2065 Tests · OK** (6 skipped, jeweils begründet) |
| `selftest_clock --trap-modul … --offset 97/1461` (6 Module) | grün – vorher 11 rote Tests in 7 Modulen |
| `selftest_clock --selftest` | grün (Trap findet Bomben in Skripten UND Testmodulen) |
| `reserve_janitor --selftest` | grün, auch unter fremder Uhr |

---

## Nachtrag 4 (07.10.2026, 17:35Z) – CI-Beleg: die zwei roten Gates sind grün

Kopf `445ce8e` (Merge der zwischenzeitlichen main-Commits, u. a. C27):

| Check | Ergebnis |
|---|---|
| **Publication reliability regression tests** (Run 37659099315) | success – **alle Schritte grün**, inkl. des neuen Schritts „Uhr-Probe – die Suite muss an jedem Kalendertag grün sein" |
| **Qualitäts-Gate (Build + interne Links)** | success (169 Wachen · 338 Uhr-Proben, `reserve_blocker_klassen --selftest` unter +97/+1461 Tagen) |
| Integritäts-Lock (PR-Gate) | success – 47 Kerndateien, Herkunft im Lock |
| Beweis-Gate, CodeQL, Lesehilfen, Themenwelten, Daten-/Visualisierung, E2E | success |

Lokal auf demselben Baum: `unittest discover` **2065 Tests OK** (4 skipped),
`selftest_clock --trap-discover scripts/tests --offset 97` **2069 Tests OK**
(6 begründete Skips), `integrity_guard --gate` grün.

Damit ist der Weg frei: Der Produktionslauf auf `main` stellt das Zertifikat
aus – erwartet werden die zurückgeholten Kandidaten und ≥ 4 zertifizierte
Reserve-Artikel.

---

## Nachtrag 5 (07.10.2026) – der Satz-Heiler schrieb an der falschen Stelle

### Befund

Der Lauf **37666773476** blieb bei **3/6**. Der Satz-Heiler, der die
Lesbarkeits-Klasse übernehmen sollte, hatte keinen einzigen Ersatz in eine
Datei geschrieben. Die Ursache war ein Koordinatenfehler: `saetze_finden()`
lieferte Positionen relativ zu `teile[2]` (dem Body); gespleißt wurde aber mit
`aktuell[start:…]` im vollständigen Artikel. Beim DSL-Kandidaten lag der Kopf
rund 2.5k Zeichen vor diesem Koordinatensystem. `start = 140` traf deshalb
Frontmatter statt des Satzes. T4 erkannte die Änderung korrekt und verwarf
alles – fail-closed, aber ohne Fortschritt.

Die alte Wirkungsprobe hatte nur einen etwa 74 Zeichen langen Kopf. Dort traf
dieselbe falsche Position den Body und zerstückelte den Satzanfang
(„NotierWie …“); keine Prüfung bemerkte den Schaden. Eine grüne Probe bewies
also nicht, dass die Wirkung heil war.

### Reparatur auf Klassenebene

1. **Datei-Koordinaten:** `saetze_finden(..., base_offset=…)` hebt alle
   Zeiger in den Dateiraum. `_finde_satz()` sucht vor jedem Ersatz frisch im
   aktuellen Body und liefert `0` als ungültigen Sentinel; der Kopf wird nie
   durchsucht.
2. **Unabhängige Kopf-Wache:** Frontmatter und Trenner müssen vor jeder
   Freigabe byte-identisch sein. Das gilt zusätzlich zu T4 und unabhängig von
   der Positionsrechnung.
3. **Satzschutz:** `unversehrte_saetze()` baut den erwarteten Text aus dem
   Original und den vollständigen, freigegebenen Ersetzungen erneut auf. Ein
   beschädigter Satz oder eine Änderung außerhalb der Ersetzung wird
   fail-closed verworfen; R5 darf nur Absatz-Whitespace ergänzen.
4. **Ehrliche Wirkungsprobe:** Das Fixture hat nun einen Kopf von mindestens
   2.532 Zeichen. Die Gegenprobe erzwingt `_finde_satz → 0`; ein solcher Finder
   muss fail-closed gehen und der Selbsttest wird bei externer Sabotage rot.
5. **Teilfortschritt:** Unterhalb Flesch 60 darf ein sauberer Sprung von
   mindestens **+0,3 Punkten** geschrieben werden, wenn ausschließlich die
   T1-Schwelle offen ist. `--nur-ganz` und
   `FFC_SATZ_NUR_GANZ=1` stellen das bisherige Alles-oder-nichts wieder her.

### Nachweis in dieser Arbeitskopie

| Prüfung | Ergebnis |
|---|---|
| `satz_heiler.py --wirkungsprobe --json` | ✅ Flesch **42,0 → 73,6**; realistischer Kopf, Kopf-Tor und Satzschutz erfüllt |
| `satz_heiler.py --selftest` | ✅ Wirkung, Idempotenz und `_finde_satz → 0` fail-closed |
| `python -m unittest scripts.tests.test_satz_heiler -v` | ✅ **19 Regressionstests** |
| `selftest_clock --trap-modul scripts.tests.test_satz_heiler --offset 97` | ✅ 19 Tests unter vorgestellter Uhr |
| Vollständige Suite (`PyYAML 6.0.2`) | ✅ **2.108 Tests, 24 begründete Skips** |
| `reserve_healer_coverage.py --selftest` / `--vorratsschutz` | ✅ Deckung und Fahnen-Schutz grün |
| Read-only Reserve-Scan | ✅ **12 Kandidaten** unter Flesch 60; DSL 59,5, Haushaltskosten 59,9; keine Kandidatendatei geändert, keine Live-KI aufgerufen |

Der im vorherigen lokalen Lauf genannte mechanische Stub-Nachweis
(**0/12 → 5/12**, DSL 59,5 → 60,1, Haushaltskosten 59,9 → 60,0) ist
Übergabe-Evidenz; er wurde in dieser Arbeitskopie nicht erneut mit einem
Stub-Modell gefahren. Der zertifizierende Produktionslauf und der Dispatch
„Reserve-Nachweis #614“ bleiben ausstehend. Nach dem Push auf den freigegebenen
Ref muss der Nutzer den Dispatch auslösen; erst ein grünes Zertifikat belegt
≥ 4 Kandidaten und gehört anschließend ins Siegel.
