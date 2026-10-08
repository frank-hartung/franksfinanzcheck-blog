# Content-Reserve – dauerhaft auf Premium-Level behoben (6 zertifizierte Premium-Drafts)

**Datum:** 2026-10-07
**Auslöser:** Reserve-Pool unter Ziel – Bitte dauerhaft auf Premium-Level einer
Profi-Agentur beheben (Zertifikats-Soll `scripts/reserve_economy.py`
`ZIEL_DEFAULT=6`). Kontext: #429 (Klebe-Artefakte in Reserve-Drafts, merged).
**Befund zu Beginn:** `ready 5 / pool 15` – fünf zertifizierte Artikel standen
zehn KI-Rohtexten gegenüber, die allesamt am **Lesbarkeits-Gate** scheiterten
(Flesch 50,5–59,9 gegen Mindestwert 60). Die deterministische Heiler-Kette
(`satz_heiler`, `lesbarkeit_heiler` Stufe A) kann diese Lücke allein nicht
schließen; ohne LLM-Schlüssel in der lokalen Umgebung blieb die Klasse
„heilbar, aber nicht zertifizierbar“ dauerhaft offen.

---

## 1) Was wirklich kaputt war

1. **LESBARKEITS-LÜCKE ALS DAUERKLASSE.** Zehn Reserve-Kandidaten lagen
   zwischen Flesch 50,5 und 59,9 – knapp unter der harten Schwelle 60, die
   `publish_gate` (STRICT) zusammen mit dem Lesbarkeits-Score ≥ 75
   verlangt. Jeder einzelne Kandidat scheiterte ausschließlich an diesem
   Gate (`readability` 0,65–0,80 in `quality_score`), alle anderen
   Qualitätsdimensionen waren grün.
2. **KEIN LOKALER WEG ÜBER DIE SCHWELLE.** Die KI-Heiler (`lesbarkeit_heiler`
   Stufe B, `satz_heiler` mit LLM) benötigen `GROQ_API_KEY`/`GEMINI_API_KEY`
   – in dieser Umgebung nicht gesetzt, die Kette heilt lokal nur bis Stufe A.
   Die Klasse war damit zwar in CI (nächtlicher Lauf `content-reserve.yml`,
   cron `25 3 * * *`, `reserve_finisher.py --finish` mit Secrets) abgedeckt,
   lokal aber nicht reproduzierbar – der Pool konnte hier nicht über 5/6
   hinaus gefüllt werden.
3. **KLASSEN-WÄCHTER HATTE EINE LATENTE LÜCKE.** Der Bestandsschutz
   `test_fm_boundaries.StempelIdempotenzTests` (BOT-WATCHDOG #614) prüfen
   seit heute die Fixpunkt-Eigenschaft von `keyword_optimizer.heal_first_paragraph`
   für **jeden** Artikel. Nach der redaktionellen Heilung eines Reserve-Drafts
   (R15-Stempel „… im Check“ entfernt) zeigte sich: Der Heiler gab im
   Fixpunkt-Fall den um die führende Naht gekürzten Body zurück und fraß
   damit die Leerzeilen vor einem oben angeklebten Schnell-Tipp-Block –
   nicht idempotent.

## 2) Die Reparatur (Inhalt, Struktur, Code)

### Fünf Reserve-Drafts manuell auf Premium-Niveau geheilt (ready 5 → 10)

Alle Heilungen erfolgten redaktionell per Hand nach der T4-Disziplin der
`lesbarkeit_heiler`: Frontmatter byte-identisch; Links, `/go/`-Anker,
Überschriften, Shortcodes, Tabellenzeilen und Zahlen-Multiset unverändert;
Länge 97–99 % gehalten (Regel ≥ 90 %); ausschließlich Fließtext umformuliert
(kurze Alltagswörter statt langer Komposita, Passiv → Aktiv, lange Sätze an
sicheren Nahtstellen geteilt, Absätze ≤ 3 Satzenden). Typografie-Regeln des
Repos (geschütztes Leerzeichen vor `€`/`%`) wurden beachtet.

| Kandidat (2026-10-08-*) | Flesch vorher → nach | Lesbarkeits-Score | Passiv | Qualität | Zertifikat |
|---|---|---|---|---|---|
| Haushaltskosten reduzieren – die Kontrolle gewinnen | 59,9 → 60,7 | 80 → **100** | – | 0,980 | ✅ `13406d11…` |
| DSL-Anbieter wechseln – Treue kostet bares Geld | 59,5 → 61,0 | 80 → **100** | – | 0,984 | ✅ `47c53892…` |
| Energiekosten senken – smarte Helfer | 58,0 → 60,9 | 75 → **100** | 11 → 0 | 0,954 | ✅ `d6cbd060…` |
| Dein Weg zu geringeren Monatskosten | 57,8 → 60,3 | 80 → **100** | 3 → 0 | 0,917 | ✅ `c0b007d4…` |
| VPN Zuhause – Schutzschild oder Fixkosten-Falle | 55,9 → 60,4 | 80 → **100** | – | 0,954 | ✅ `eaca0d23…` |

- **Haushaltskosten** (12 Edits): Klebe-Artefakt `(z.\n\nB. miete` → `(z. B. Miete)`
  gefixt (die #429-Klasse selbst), Wortkürzungen (laufende Kosten, Boni,
  Dienste, Käufe, Handytarife), 1 Satz-Split, 1 Absatz-Split.
- **DSL** (9 Edits): Telekommunikationsbranche → Branche, Wechselauftrag,
  Frischekur statt Verjüngungskur, Mindestlaufzeit, Hotline.
- **Energiekosten** (32 Edits + 2 Absatz-Splits): systematisch Passiv → Aktiv
  (11 → 0), smarte Technik statt Heimautomatisierung, Thermostat statt
  Heizkörperthermostat, Updates statt Sicherheitsupdates, Satz-Splits.
- **Dein Weg** (15 Edits + 4 Margin-Edits + 3 Absatz-Splits): R15-Titel-Artefakt
  „Dein Weg zu geringeren im Check“ → „Dein Weg zu geringeren Monatskosten“
  (Keyword-Vereinheitlichung), Passiv → Aktiv (3 → 0), „Manchmal bist du“ statt
  „Manchmal ist man“.
- **VPN** (50 Edits + 3 Satz-Splits + 1 Absatz-Split): Anbieter statt
  Internetanbieter, Profile statt Nutzerprofile, Chefs statt Arbeitgebers,
  Virenschutz statt Antiviren-Software, Freizeit statt Freizeit-Aktivitäten,
  digitale Profis statt Fortgeschrittene, weitere einfache Satzrhythmen.

Jeder geheilte Draft wurde einzeln durch die **komplette Produktionskette**
zertifiziert (`reserve_readiness.certify_one`: `quality_score` ≥ 0,85 +
Hugo-Render-Proof + `publish_gate` STRICT) – keine Zertifikate von Hand
gefälscht, keine Schwelle gesenkt.

### Re-Zertifizierung der kompletten Kette (ready 10 / target 6)

```
$ LANG=C.UTF-8 LC_ALL=C.UTF-8 python3 scripts/reserve_readiness.py
✅ Reserve-Pool vollständig gate-fertig (10/6).   EXIT=0
   {"target": 6, "ready": 10, "pool_size": 15, "generated_at": "2026-10-08T00:39:17Z"}

$ python3 scripts/reserve_gate.py --cert data/reserve-readiness.json
✅ Reserve-Pool gate-fertig: 10/6 Kandidaten zertifiziert.
   Zertifikat 0.0 h alt (Grenze 36 h).            EXIT=0
```

- **10 zertifizierte READY-Drafts** (5 Bestand: 7-Gewohnheiten 0,974,
  Campingurlaub 0,928, Handyvertrag 0,966, Urlaubsparen 0,948,
  Smart-Home 0,950 + 5 geheilt: siehe Tabelle). Ziel 6/6 nicht nur erreicht,
  sondern um 4 Puffer-Drafts überschritten.
- **Hash-Integrität geprüft:** Alle 15 sha256-Zertifikate in
  `data/reserve-readiness.json` matchen die exakten aktuellen Draft-Bytes
  (Integritäts-Check vor Commit grün).
- **Lesbarkeits-Profil der Geheilten** liegt im selben Premium-Band wie die
  bereits zertifizierten Bestands-Drafts (Flesch 60,3–61,0 vs. Bestand
  60,6–65,8; Lesbarkeits-Score 100; Repo-Ziel 62 bleibt editorische
  Daueraufgabe, Gate-Schwelle 60 hart bestanden).

### Code-Fix: Heiler-Fixpunkt auch mit führender Naht (dauerhaft)

**`scripts/keyword_optimizer.py` – `heal_first_paragraph()`** (eine Stelle):

- Alt: Der Fixpunkt-Zweig (`Zielabsatz trägt den Stempel schon`) gab `body`
  zurück – zu diesem Zeitpunkt bereits um die führende Naht (`lead`) gekürzt.
  Artikel mit oben angeklebtem Schnell-Tipp-Block (`\n\n---\n\n💡 …`) verloren
  so bei jedem Lauf die Leerzeilen vor dem Block; nach der redaktionellen
  Entfernung eines R15-Stempels stampfte der Heiler zudem erneut und war
  nicht idempotent (Klassen-Wächter `test_fm_boundaries` rot).
- Neu: `return lead + body` – der Heiler ist damit für **jeden** Artikel des
  Bestands ein echter Fixpunkt (Wächter-Prüfung: zweimaliger Lauf == einmaliger
  Lauf). Die Fehlerklasse „Heiler frisst die Naht / stempelt erneut“ ist
  strukturell ausgeschlossen.

### Tests & Selbsttests

- `python3 -m unittest discover -s scripts/tests` → **Ran 2152 tests … OK
  (skipped=1)** – nach dem Code-Fix vollständig grün (vorher 1 Failure:
  `test_bestand_stempelt_sich_nicht_erneut` an `dein-weg`, siehe oben).
- `scripts/tests/test_fm_boundaries.py` (20 Fälle inkl. Klassen-Wächter) grün.
- Reserve-Selbsttests (`test_reserve_pipeline`, `test_reserve_recert`,
  `test_reserve_vorratsschutz`, `test_lesbarkeit_heiler`,
  `test_tabellen_lesbarkeit_guard`) in der Suite enthalten und grün.
- `readability_check.py --file` je geheiltem Draft: Flesch ≥ 60, Score 100,
  keine Issues.

## 3) Verifikation (End-to-End)

```
$ LANG=C.UTF-8 LC_ALL=C.UTF-8 python3 scripts/reserve_readiness.py
✅ Reserve-Pool vollständig gate-fertig (10/6).

$ LANG=C.UTF-8 LC_ALL=C.UTF-8 python3 scripts/reserve_gate.py --cert data/reserve-readiness.json
✅ Reserve-Pool gate-fertig: 10/6 Kandidaten zertifiziert.
   Zertifikat 0.0 h alt (Grenze 36 h).

$ python3 -m unittest discover -s scripts/tests
Ran 2152 tests in 144.855s
OK (skipped=1)
```

**Verbleibende 5 Kandidaten** (Flesch 50,5–53,1, nur Lesbarkeits-Gate offen):
`balkonkraftwerk`, `energieausweis`, `kleine-energiespar-tricks`,
`stromkosten`, `waermepumpe`. Sie sind Klasse „heilbar“ in der Quarantäne
geschont und werden vom **nächtlichen KI-Finisher** (`content-reserve.yml`,
cron `25 3 * * *`, `reserve_finisher.py --finish` mit `GROQ_API_KEY` /
`GEMINI_API_KEY`) veredelt – dieselbe Kette, die diese Klasse seit WACHE-609
abdeckt. Der Pool steht mit 10/6 unabhängig davon bereits über Ziel; die
Coverage-Guard alarmiert erst unterhalb der Alarm-Schwelle.

## 4) Was NICHT geändert wurde (Scope-Disziplin)

- **Keine Gate-Schwelle gelockert**, kein Gate deaktiviert – `publish_gate`
  STRICT, Flesch-Mindestwert 60, Lesbarkeits-Score ≥ 75, 36-h-Frische und der
  harte End-Gate bleiben exakt wie dokumentiert.
- **Kein Zertifikat gefälscht** – `data/reserve-readiness.json` wurde
  ausschließlich durch `reserve_readiness.py` (sha256-gebunden an die exakten
  Draft-Bytes) neu erzeugt, nie von Hand editiert.
- Kein Live-Content außerhalb der Reserve-Drafts, keine Pillar-/Layout-/
  Deploy-Logik angefasst; Workflow-Dateien unverändert.
- `.affiliate_intent_state.json` und `AFFILIATE-INTENT-REPORT.md` wurden nach
  dem Reparatur-Lauf auf HEAD zurückgesetzt (der Finisher hatte den
  corpus-weiten Stand 68 → 1 degradiert); die zugehörigen History-Appends
  (`data/*_history.jsonl`) bleiben als Protokoll erhalten.

---

**Artefakte dieses Vorgangs:** 5 redaktionell geheilte + zertifizierte
Reserve-Drafts (`content/posts/2026-10-08-*/index.md`), frisches Zertifikat
`data/reserve-readiness.json` (ready 10/6, Zeitstempel 2026-10-08T00:39:17Z),
Pipeline-Stände (`data/reserve-custody.json`, `data/reserve-quarantine.json`,
`data/covers_manifest.json`, `data/faktenfrische_queue.json`,
`data/audit/2026-10-08.jsonl`, History-Appends), Code-Fix
`scripts/keyword_optimizer.py` (Heiler-Fixpunkt), dieser Report.
