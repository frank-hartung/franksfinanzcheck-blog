# Vorfall #387 – „Content-Reserve (täglicher Vorrat)" rot

**Datum:** 26.09.2026 · **Lauf:** 36230666076 (03:25 UTC) · **Status:** behoben
**Symptom im Ticket:** `Stock shortage must not look successful` → Exit 1,
`2/6 Kandidaten gate-fertig`.

---

## 1. Was wirklich passierte

Der Lauf war **nicht** an der KI, am Provider oder an einem Timeout
gescheitert. Der Vorrat war in 18 Stunden von **8 auf 3** Kandidaten
gefallen – und **zwei davon lagen unverändert im Repository**. Drei
unabhängige Lecks wirkten gleichzeitig; keines davon wurde im Lauf-Log
sichtbar, weil der End-Gate nur das Ergebnis meldete, nie die Ursache.

| # | Leck | Wirkung am 26.09. |
|---|------|-------------------|
| 1 | **Fahnen-Verlust** – Commit `b025322` schrieb das Frontmatter zweier zertifizierter Kandidaten neu und ließ `reserve: true` weg | −2 Kandidaten, lautlos |
| 2 | **Themen-Monokultur** – der Nachschub nahm immer `freie[0]`, also das erste Thema, das die 60-%-Titelregel passierte | 6× dasselbe Thema, danach Stillstand |
| 3 | **Titel-Falsch-Positiv** – Regel R5 hielt einen vollständigen Titel für abgeschnitten, ohne dass ein Heiler dafür existierte | −1 Kandidat, Quarantäne-Eintrag |
| — | Folgeschaden | Publikation am 20.09.: vier Gasrechnungs-Varianten am selben Tag live → drei später zu Entwürfen zurückgestuft („Rückläufer") |

Die Bilanz 25.09. → 26.09.: 8 Kandidaten → 3 (2 publiziert, **2
flag-verloren**, 1 Rückläufer), Nachschub 0, ready 2 < target 6.

---

## 2. Warum das kein Einzelfall war

Alle drei Lecks gehören derselben Fehlerklasse an: **ein Zustand, der nur
in einer Datei steht, aber niemandem gehört.**

* Die `reserve`-Fahne war Pool-Mitgliedschaft *und* Frontmatter-Feld –
  jeder Schreiber konnte sie mitnehmen, niemand vermisste sie.
* Die Themenwahl hatte kein Gedächtnis – dieselbe Nacht, dieselbe
  Entscheidung, dasselbe Ergebnis.
* Die Titelregel hatte einen Fund, aber keinen Heiler – die „Deckung"
  stand nur auf dem Papier (`R5_END_WHITELIST` als Pflaster).

---

## 3. Was jetzt anders ist

### 3.1 Bestands-Wächter (`scripts/reserve_custody.py`, neu)
Führt Buch über jeden Kandidaten, der je im Pool war
(`data/reserve-custody.json`). Fehlt einem Entwurf die Fahne, obwohl er
weder veröffentlicht noch ausgemustert noch von Hand zurückgezogen wurde,
**stellt der Wächter sie wieder her** – mit Datum und Begründung im
Gedächtnis. Läuft als **Stufe 0** vor jeder Produktion: erst den Bestand
sichern, dann Geld für KI ausgeben.

Grenzen, bewusst gesetzt:
* **Rückläufer** (veröffentlicht → wieder `draft`) werden **nur gemeldet**,
  nie automatisch zurückgeholt – meist hat ein Gate sie zu Recht
  zurückgestuft. Sie gehören der Redaktion.
* `reserve_retired: true` im Frontmatter ist ein **Veto des Menschen** und
  wird ausnahmslos respektiert.
* Der Schlüssel im Gedächtnis ist der Slug **ohne Datumspräfix** – die
  Veredelung datiert Kandidaten nächtlich um; ein Gedächtnis mit Datum im
  Schlüssel wäre nach einer Nacht wertlos.

### 3.2 Themen-Disposition (`scripts/reserve_topics.py`, neu)
Ersetzt `freie[0]`. Vergleicht **Leitbegriffe** (statt 60 % Wortgleichheit)
gegen den gesamten Bestand – live, Entwürfe und Pool –, rotiert über ein
Gedächtnis mit Cooldown (`data/reserve-topic-ledger.json`) und liefert eine
**Liste**: Scheitert die KI an einem Thema, läuft die Nacht mit dem
nächsten weiter, statt abzubrechen.

Messung im Bestand: 175 Themen, 121 thematisch belegt, **54 frei** – und
die Klumpen sind benannt (gasrechnung 7×, stromfresser 6×, energiediebe 5×,
frugalismus 5×, spätsommer 5×).

### 3.3 Fehlertoleranz im Nachschub (`scripts/engine_generate.py`)
Der Batch brach beim **ersten** Fehlschlag ab. Jetzt entscheidet ein
Stop-Signal, ob weitere Versuche überhaupt Sinn haben (Ziel erreicht,
Kapazität, In-Flight, keine freien Themen); ein reiner
Generierungs-Fehlschlag läuft mit dem nächsten Thema weiter – höchstens
`RESERVE_LEERLAUF_MAX = 2` Leerrunden hintereinander, damit kein API-Budget
verbrennt.

### 3.4 Titel-Integrität mit echtem Heiler (`scripts/check_titles.py`)
R5 unterscheidet jetzt zwischen **hängendem Satzzeichen / Auslassung /
Schluss-Tabu** und einem normalen Titelende. Neu ist `heal_r5()`: Es kürzt
nur **verlustfrei** (Rest ≥ Mindestlänge, ≥ 3 Wörter, danach R5-frei,
idempotent) und lässt echten Textverlust unangetastet – damit löst die
Regel ihre Zusage in `reserve_healer_coverage.py` ein, statt sie zu
behaupten. Bestand: **4 Funde → 1**, die drei Falsch-Positive sind weg, der
echte `&`-Abbruch ist geheilt.

### 3.5 Vielfalt beim Veröffentlichen (`scripts/reserve_pool.py`)
Die Reserve ist eine Notfall-Kasse, kein Kannibale: Ein Kandidat, dessen
Thema in den letzten **14 Tagen** live war, wird **zurückgestellt** (nicht
verbraucht). Bleibt die Lücke deshalb offen, sagt der Lauf das ehrlich –
eine echte Lücke ist besser als drei Dubletten, die morgen wieder
Entwürfe sind.

### 3.6 Diagnose statt Rätselraten (`scripts/reserve_gate.py`)
Der End-Gate bleibt hart, benennt aber jetzt die Ursachenklasse – **LECK /
RÜCKLÄUFER / BLOCKER / PRODUKTION / THEMENMANGEL** – mit konkretem nächsten
Befehl, im Log *und* in der Lauf-Zusammenfassung. Zusätzlich schreibt er
eine Zeile pro Lauf nach `data/reserve-history.jsonl`, damit ein Trend
sichtbar wird und nicht nur der schlechteste Tag.

Beispielausgabe auf dem Ist-Stand vor der Heilung:

```
🛑 RESERVE-ENGPAß: nur 2/6 Kandidaten gate-fertig.
   URSACHEN DIESES ENGPASSES:
   • LECK: 2 Entwürfe waren im Pool, haben aber die `reserve`-Fahne verloren …
   • RÜCKLÄUFER: 5 veröffentlichte Artikel stehen wieder auf `draft` …
   • BLOCKER: 1 Kandidat scheitert an einem Gate – „Cover-Text-Komplettheit …"
   • PRODUKTION: 3 Kandidaten fehlen, obwohl freie Themen bereitstehen …
```

### 3.7 Gedächtnisse überleben den Runner
`reserve_stage_guard.py` stagt die neuen Ledger, `git_sync.sh` löst
Rebase-Konflikte darauf **per Schlüssel-Vereinigung** (jüngerer Eintrag
gewinnt) statt „letzter Schreiber gewinnt" – ein Gedächtnis, von dem eine
Seite verworfen wird, verliert echtes Wissen.

---

## 4. Sofort-Wirkung (in diesem PR bereits ausgeführt)

| Maßnahme | Ergebnis |
|---|---|
| `reserve_custody.py --heal` | 2 Kandidaten zurück im Pool: **3 → 5** |
| `check_titles.py --fix` | letzter echter R5-Abbruch geheilt, **0 Verstöße** |
| Falsch-Positiv aus `data/reserve-quarantine.json` | entfernt (Quarantäne wieder leer) |

Damit steht der Pool bei **5 Entwürfen** statt 3; den Rest bis 6 liefert
die Produktion, sobald sie mit Schlüsseln läuft (lokal nicht prüfbar).

---

## 5. Nachweis

| Prüfung | Ergebnis |
|---|---|
| `scripts/selftest_runner.py` | 103 Wachen, 206 Uhr-Proben, alle grün |
| `python3 -m unittest discover -s scripts/tests` | 939 Tests, OK (22 übersprungen) |
| `scripts/tests/test_reserve_pipeline.py` | 55 Verträge (17 neu für #387) |
| `governance_contract.py --selftest` | C1–C18 grün, neue Wachen im Minimum |
| Trockenlauf `engine_generate.py --reserve-only` ohne Schlüssel | rotiert durch 6 verschiedene Themen, hält den ersten Fehlschlag aus, stoppt nach 2 Leerrunden ohne API-Kosten |

Neue Verträge (Auszug): verlorene Fahne wird zurückgeholt · fremder
Hand-Entwurf **nicht** · Re-Dating verliert das Gedächtnis nicht · der
Wächter hängt wirklich in der Linie · Ledger sind gestagt · belegtes Thema
wird nicht erneut vorgeschlagen · Batch gibt beim ersten Fehlschlag nicht
auf · Dublette wird zurückgestellt, fremdes Thema nicht · Sperre ist
fail-open · vollständiger Titel ist kein Abbruch · Heilung kürzt nur, dichtet
nie · Diagnose stürzt nie ab · Stufe 0 läuft **vor** der Produktion.

---

## 6. Was ein Mensch noch entscheiden muss

1. **5 Rückläufer** (`reserve_published` + `draft: true`), davon vier
   Gasrechnungs-Varianten: veröffentlichen, zusammenführen oder
   ausmustern (`reserve_retired: true`). Die Automatik fasst sie nicht an.
2. **Themen-Klumpen** in `data/topics.yaml`: 54 freie Themen reichen für
   gut zwei Wochen Nachschub – danach braucht die Reserve neue Themen.
3. Dauerbefund ohne Bezug zu #387: `secrets_age_guard` meldet
   `PINTEREST_ACCESS_TOKEN` als „dead" (critical).
