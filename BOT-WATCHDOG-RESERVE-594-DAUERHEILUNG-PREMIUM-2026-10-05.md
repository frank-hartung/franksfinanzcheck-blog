# ⚠️→✅ Bot-Watchdog „Automatisierung braucht Eingriff" – Dauerheilung der Content-Reserve (#594)

**Stand:** 2026-10-05 · **Besitzer:** Content-Automatisierung (Maschine)
**Auslöser:** Issue #594 · **Niveau:** Profi-Agentur (Ursache, Prävention, Backstop, Test)
**Vorgangskürzel:** WF-B594

---

## 0. Ergebnis zuerst

| Messpunkt | vorher (05.10., 17:30 UTC) | nachher (05.10., 19:0x UTC) |
|---|---|---|
| `bot_watchdog.check_content_reserve()` | ❌ rot | ✅ `(True, 'Reserve ausreichend (5 gate-fertige Artikel (Ziel 6, Alarm unter 4), 5 Reserve-Entwürfe)')` |
| gate-fertige Kandidaten | **0** | **5** (Ziel 6, Alarm unter 4) |
| Reserve-Pool (Entwürfe mit Fahne) | 1 | 5 |
| Entwürfe im Bestand, die niemand sah | 14 reife Entwürfe lagen außerhalb des Pools | 0 unbeachtet – jeder trägt eine protokollierte Entscheidung |
| Regressionsnetz `test_reserve_pipeline.py` | 78 Tests | **108 Tests** (30 neu unter WF-B594) |
| Gesamtsuite | 1834 | **1842** Tests |

Das Zertifikat liegt in `data/reserve-readiness.json`, das Übernahmeprotokoll
in `data/reserve-intake.json`, der Beleg-Ledger des Aufräumers in
`data/reserve-janitor-state.json`.

---

## 1. Was das Ticket meldete – und was wirklich kaputt war

Das Ticket meldete „Content-Reserve niedrig, 0 von 6 gate-fertig". Das klingt
nach zu wenig Content. Der Bestand sagte etwas anderes: **14 Entwürfe waren
reif**, kein einziger davon gehörte dem Pool. Die Reserve war nicht leer, sie
war **abgeschnitten**.

Issue #594 ist der **achte** Vorfall dieser Klasse (#251, #272, #281, #393,
#446, #462, #520). Jede frühere Reparatur hat den Bestand aufgefüllt. Keine
hat den Weg repariert, auf dem fertige Arbeit in den Vorrat gelangt. Genau das
ist hier passiert.

Fünf getrennte Ursachen, alle mit derselben Handschrift – **die Automatik
entscheidet still über Material, das ihr nicht gehört**:

| # | Ursache | Wirkung im Nachtlauf |
|---|---|---|
| **B1** | Es gab keinen Weg, einen fertigen Entwurf in den Pool zu übernehmen. Der Pool füllte sich ausschließlich aus Neuproduktion. | 14 reife Entwürfe verhungerten neben einem leeren Vorrat. |
| **B2** | Der Aufräumer löschte Entwürfe nach **einem** Befund, sofort, ohne Karenz. | Material verschwand, bevor ein Heiler es zweimal gesehen hatte (Löschbeweis `c56382b`). |
| **B4** | Das Triage-Fenster zeigte nur Entwürfe der letzten Tage. | Wer länger lag, war für die Redaktion unsichtbar – und damit für jede Entscheidung. |
| **B5** | Der Linker konnte nur korpusweit arbeiten. | Der häufigste heilbare Blocker („interne Links < 2") hatte in der Reserve-Kette **keinen** Heiler. |
| **B6** | Die Lösch-Deckung war ungeprüft. | Eine Lücke zwischen „Blocker-Klasse" und „Heiler" konnte Material in die unheilbare Ecke schieben. |

Beim **scharfen Durchlauf** der reparierten Kette fielen zwei weitere Lecks
derselben Klasse auf – beide sind in diesem Vorgang mitrepariert:

| # | Ursache | Wirkung |
|---|---|---|
| **B7** | Das Gedächtnis des Bestands-Wächters schlüsselt **datumslos**. Zwei Entwürfe teilten sich den Stamm `konto-karten-update-…`. | `--heal` setzte die Reserve-Fahne am **falschen** Artikel: ein nie übernommener Entwurf wanderte still in den Pool, das Übernahmeprotokoll kannte ihn nicht, und der Ledger-Eintrag zeigte danach auf den falschen Slug. |
| **B8** | Der Linker kannte Shortcodes, Code, Links und Überschriften als Sperrzone – **nicht** die kanonischen CTA-Blöcke. | Mit dem neuen `--file`-Bezirk lief er erstmals über Entwürfe **mit** CTA und setzte zwei Links mitten in die Schnell-Tipp-Zeile, die `affiliate_integrity_gate` bytegenau prüft. |

---

## 2. Die Lösung in sieben Schichten

### Schicht 1 – Übernahme als eigenes Werkzeug (B1)
**Neu: `scripts/reserve_intake.py`**

* findet fertige Entwürfe außerhalb des Pools und prüft sie gegen **fünf**
  Regeln: Triage-Reife, Risikoklasse, Themen-Dublette zum Live-Bestand,
  Eigentum (KI-Redaktions-Angebote gehören einem Menschen) und Faktenfrische.
* schreibt **jede** Entscheidung mit Datum und Grund nach
  `data/reserve-intake.json` – auch jede Ablehnung. Eine Übernahme ohne
  Begründung ist in den Tests ein Fehler.
* YMYL-Material (Versicherungen, Kredit) wird **nicht** automatisch
  übernommen. Risikoklasse `erhoeht` bleibt eine Redaktionsentscheidung.
* `reserve_readiness.main()` ruft die Bestandsaufnahme **vor** dem Zählen auf:
  erst zurückgeben, was dem Pool gehört, dann messen.

### Schicht 2 – Löschen braucht einen Beweis (B2)
`scripts/reserve_janitor.py` löscht nur noch, wenn **drei** Bedingungen
zusammenkommen:

1. **Klasse** – der Blocker gehört zu einer nachweislich unheilbaren Klasse
   (`scripts/reserve_blocker_klassen.py`, siehe Schicht 4),
2. **Beleg** – derselbe Befund stand in `RESERVE_JANITOR_HITS` (Default 2)
   getrennten Läufen; Trockenläufe zählen nicht, derselbe `run_key` zählt
   einmal. Ledger: `data/reserve-janitor-state.json`,
3. **Karenz** – kein Entwurf wird in seinen ersten
   `RESERVE_JANITOR_KARENZ_TAGE` Tagen angefasst.

Geschontes verschwindet nicht lautlos: Der `--md`-Bericht führt es als
„🛟 Geschont (Material, N)" mit Einzelbegründung.

### Schicht 3 – Das Triage-Fenster zeigt den ganzen Bestand (B4)
`scripts/draft_triage.py` listet jeden Entwurf mit Zustand, Alter und
**konkretem** Hindernis. Was die Redaktion nicht sieht, kann sie nicht
freigeben – und was niemand freigibt, holt am Ende ein Ticket.

### Schicht 4 – Lösch-Deckung ist geprüft, nicht geglaubt (B6)
`scripts/reserve_blocker_klassen.py` ist die **eine** Stelle, die sagt, ob ein
Blocker heilbar ist. `scripts/reserve_healer_coverage.py` prüft gegen diese
Liste, dass jede heilbare Klasse einen Heiler in der Kette hat und kein
Eintrag ins Leere zeigt. Ohne Deckung:

* **Aufräumer**: löscht nichts, meldet `::error::`, berichtet als Trockenlauf,
  gibt **rc=0** zurück. Stufe 0a läuft ohne `continue-on-error` – die Sperre
  darf die Produktion nicht töten.
* **Finisher**: bricht **hart** ab (rc=1, `targets == []`, kein Schreibzugriff).
  Wer heilen will, ohne die Deckung zu kennen, heilt nicht.

### Schicht 5 – Der Linker heilt einzeln (B5)
`scripts/internal_linker.py --file <pfad>` arbeitet auf genau einem Artikel;
LIVE-Artikel bleiben Ziele, nie Quellen. Der Eintrag in `HEALER_CHAIN` nutzt
den `"file"`-Bezirk und wahrt damit die Live-Korpus-Isolation, an der die
naive Variante („Linker einfach anhängen") gescheitert wäre.

### Schicht 6 – Identität statt Namensähnlichkeit (B7)
`scripts/reserve_custody.py` heilt die Reserve-Fahne nur noch auf dem **exakt
gemerkten** Slug. Namensgleiche Geschwister werden als `namensgleich`
berichtet und nicht angefasst – Übernahme läuft ausschließlich über
`reserve_intake.py`. Alt-Einträge ohne gemerkten Slug bleiben über den Stamm
heilbar (Rückwärtskompatibilität).

### Schicht 7 – Werbeblöcke sind kein Fließtext (B8)
`internal_linker.cta_ranges()` sperrt Schnell-Tipp-, Spar-Tipp-,
Abschluss-CTA- und Offenlegungszeilen sowie jede Zeile mit `/go/`-Ziel. Der
Linker verlinkt im Fließtext – nicht in der Werbekennzeichnung.

---

## 3. Der Beweis

**Scharfe Kontrollläufe im echten Bestand (05.10.2026):**

```
reserve_janitor.purge(dry_run=True)        → deleted_slugs == []   (2 geschont, begründet)
reserve_janitor.py --purge --md            → 0 Löschungen, Ledger angelegt
reserve_healer_coverage.loeschdeckung()    → keine Lücken, keine toten Einträge
reserve_intake.run_selftest()              → rc 0
reserve_custody.py --selftest              → rc 0
internal_linker.py --selftest              → rc 0 (CTA-Sperrzone abgedeckt)
reserve_readiness.py                       → ready 5 / pool 5 / target 6
bot_watchdog.check_content_reserve()       → (True, 'Reserve ausreichend …')
```

**Der Pfad eines Artikels durch die reparierte Kette** – am Beispiel des
Entwurfs „Büroausstattung steuerlich clever absetzen":

1. **Triage** zeigt ihn als BLOCKIERT mit zwei konkreten Hindernissen
   (Länge, interne Links) statt als unsichtbaren Torso.
2. **Redaktion** schreibt ihn auf Premium-Niveau um: Kurzantwort, saubere
   H2/H3-Gliederung, zwei Tabellen, Modellrechnung, FAQ, drei `quellen` auf
   gesetze-im-internet.de (§ 6 Abs. 2, § 4 Abs. 5 S. 1 Nr. 6c, § 9 EStG),
   `faktencheck: 2026-10-05`, ausdrücklicher „ersetzt keine
   Steuerberatung"-Hinweis.
3. **Linker** (`--file`) setzt den fehlenden internen Link – im Fließtext,
   nicht in der CTA-Zeile (Schicht 7 im Einsatz).
4. **Gates** messen: Keyword 100/100, Flesch 68.5, Textverständnis ohne Fund.
5. **Zertifizierung**: Score 0.89, `ready: true` – Pool 5/6.

Der Fund bei Schritt 3 ist der eigentliche Wert dieses Vorgangs: Die Kette hat
ihr eigenes neues Leck in derselben Nacht sichtbar gemacht, in der sie gebaut
wurde – und zwar **vor** dem ersten Produktionslauf.

---

## 4. Regressionsnetz

`scripts/tests/test_reserve_pipeline.py` – **108 Tests**, davon 30 neu in
diesem Vorgang:

| Testklasse | nagelt fest |
|---|---|
| `TriageFensterTests` | Der Bestand ist vollständig sichtbar, jedes Hindernis benannt. |
| `LoeschRechtTests` | Klasse + Beleg + Karenz; Trockenlauf zählt nicht; derselbe Lauf zählt einmal. |
| `LoeschDeckungsWacheTests` | Ohne Deckung: Aufräumer rc=0 mit `::error::`, Finisher rc=1 ohne Schreibzugriff. |
| `BestandsaufnahmeTests` | Übernahme nur mit Grund; Zertifizierung nimmt auf, bevor sie zählt; KI-Angebote bleiben beim Menschen. |
| `CustodyIdentitaetTests` | Nur der gemerkte Slug bekommt die Fahne; namensgleiche Geschwister werden berichtet; Alt-Einträge bleiben heilbar. |
| `LinkerCtaSperrzoneTests` | CTA-, Spar-Tipp- und Offenlegungszeilen sind tabu; Fließtext bleibt verlinkbar. |

Gesamtsuite: **1842 Tests**. Abweichungen, die nicht zu diesem Vorgang
gehören: zwei Loader-Fehler (`test_automation_premium_audit`,
`test_check_covers` importieren `scripts.…` und brauchen das Repo-Root als
Laufverzeichnis – vorbestehend) sowie die Siegel-Prüfung, die grün wird,
sobald `data/integrity_lock.json` und die Skriptänderungen im **selben**
Commit liegen (genau so ausgeliefert).

---

## 5. Was bewusst NICHT getan wurde

* **Keine Massen-Adoption.** Acht YMYL-Versicherungsentwürfe und zwei
  Kredit-Updates blieben draußen. Mit ihnen stünde der Zähler auf 15 – und die
  Redaktion hätte zehn ungeprüfte Geldartikel im Auslieferungsweg. Ein Zähler
  ist kein Qualitätsnachweis.
* **Keine Dubletten.** `2026-09-23-5-einfache-frugalismus-tricks…`,
  `2026-09-29-konto-karten-update…` und `2026-10-05-die-50-30-20-regel…`
  bleiben liegen: Ihr Thema ist live. Eine Lücke ist ehrlicher als eine
  Dublette, die morgen wieder Entwurf ist.
* **Keine Absenkung der Messlatte.** Ziel 6 und Alarmschwelle 4 gehören
  weiterhin `reserve_economy.py` (#393). Es wäre ein Einzeiler gewesen, das
  Ticket durch eine kleinere Zahl zu schließen.
* **Keine Workflow-Änderung.** Alle Reparaturen sitzen in den Skripten, die
  die Workflows ohnehin aufrufen; die Dokumentation steht in den
  Skript-Köpfen.

---

## 6. Restrisiko und Beobachtung

Der Vorrat steht bei 5 von 6. Veröffentlicht die Linie morgen zwei Artikel aus
der Reserve und produziert keinen neuen, liegt der Stand bei 3 – unter der
Alarmschwelle. **Der Zählerstand ist nicht der Fix.** Der Fix ist die Kette:
sichtbarer Bestand → protokollierte Übernahme → geschontes Material →
gedeckte Heilung → belegtes Löschen. Sie füllt den Vorrat in jedem Nachtlauf
aus dem, was bereits fertig im Bestand liegt – statt ihn auf Neuproduktion
allein zu stellen.

Zu beobachten in den nächsten drei Nachtläufen:

1. `data/reserve-intake.json` – wächst das Protokoll, oder lehnt die Aufnahme
   dauerhaft alles ab? (Dann ist eine Regel zu streng.)
2. `data/reserve-janitor-state.json` – sammeln sich Belege auf Entwürfen, die
   eigentlich heilbar sind? (Dann fehlt ein Heiler, nicht ein Löschrecht.)
3. Der `namensgleich`-Hinweis des Bestands-Wächters – taucht er dauerhaft auf,
   gehört das Geschwister-Paar redaktionell aufgelöst.

---

## 7. Dateien dieses Vorgangs

**Neu**
`scripts/reserve_intake.py` · `scripts/reserve_blocker_klassen.py` ·
`data/reserve-intake.json` · `data/reserve-janitor-state.json`

**Geändert**
`scripts/reserve_janitor.py` · `scripts/reserve_healer_coverage.py` ·
`scripts/reserve_finisher.py` · `scripts/reserve_readiness.py` ·
`scripts/reserve_custody.py` · `scripts/internal_linker.py` ·
`scripts/draft_triage.py` · `scripts/ki_redaktion.py` ·
`scripts/tests/test_reserve_pipeline.py`

**Inhalt**
5 Entwürfe in den Pool übernommen (4 adoptiert, 1 redaktionell neu
geschrieben), Zertifikat `data/reserve-readiness.json` neu gezogen.

---

*Erstellt im Vorgang WF-B594 · Content-Automatisierung FranksFinanzcheck*
