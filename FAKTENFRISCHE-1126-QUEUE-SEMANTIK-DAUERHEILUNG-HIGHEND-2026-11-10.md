# Faktenfrische #1126 – `offen` führt nur noch Arbeit, der Vorlauf steht getrennt (Schema 2)

**Stand:** 10. November 2026 · **Befund:** `offen` der Faktenfrische-Queue führt
frisch geprüfte Artikel, `regression` repo-weit rot · **Entscheidung:** Lesart 1
des Befunds (der Erzeuger filtert), umgesetzt als Queue-Schema 2 · **Status:**
geheilt, mit Rückfall-Schutz und fail-closed-Schreiber.

> Auftrag (wörtlich): „Befund auf main: `offen` der Faktenfrische-Queue führt
> frisch geprüfte Artikel – `regression` repo-weit rot #1126. Bitte dauerhaft
> auf Highend-Level einer Profi-Agentur beheben.“

---

## 1. Befund

`data/faktenfrische_queue.json` führte am 10.11.2026 in `offen` **24** Einträge.
Jeder einzelne sagte im selben Atemzug:

```json
{ "slug": "2026-10-14-heizperiode-vorbereiten-im-spaetsommer",
  "grund": "frisch geprüft vor 26 Tagen (Intervall 30 Tage)",
  "faellig": false, "frist": "2026-11-14", "geo": 100 }
```

„Offen“ und „nicht fällig, Frist in vier Tagen“ sind zwei Aussagen, die sich
gegenseitig aufheben. Das Feld war kein Zustand, sondern eine Doppeldeutigkeit:

* Drei Aktentests (#763, #823, #911) lasen `queue['offen']` als *Befundliste*.
  Sobald eine geheilte Seite turnusgemäß wieder in den Vorlauf rutschte, wurden
  sie rot – am 07.11.2026 ohne einen einzigen Sachfehler.
* Der Schreibpfad machte das Problem am 07.11.2026 scheinbar heil, indem er
  `offen` zum **Alias** von `arbeitsvorrat` erklärte. Der Name war danach
  ehrlich, der Inhalt nicht: `offen == arbeitsvorrat` hielt den Widerspruch
  fest und dokumentierte ihn nur.
* Wer die Datei ohne Vorwissen las – Mensch, Workflow, neues Skript – musste
  wissen, dass „offen“ nicht „offen“ bedeutet. Genau daraus entstand der
  Repo-weite rote `regression`-Job (#1126).

**Nicht** die Ursache war ein Sachfehler in den beiden Artikeln: Heizperiode
und Reisekasse sind geheilt, ihre Befunde sind im Ledger geschlossen. Rot war
die **Messhöhe**, nicht der Inhalt.

## 2. Entscheidung

Der Befund ließ zwei Lesarten offen. Es gilt **Lesart 1**:

> `offen` führt nur, was Arbeit ist: **fällig**, **befundbehaftet** oder
> **abgebrochen**. Der turnusgemäße Vorlauf ist ein Termin, keine Arbeit.

Begründung – und warum Lesart 2 (nur die Wächter lockern) nicht genügt:

1. **Der Name ist ein Vertrag.** `offen` ist das Feld, das Menschen und
   nachgelagerte Werkzeuge zuerst lesen. Ein Feld, dessen Inhalt man nur mit
   einer Fußnote versteht, ist keine Messung, sondern eine Falle.
2. **Die Wächter waren nicht zu streng, sie maßen das falsche Feld.** Sie
   lesen jetzt das Ledger (`fachbefunde`), also genau die Quelle, aus der
   Ticket und Redaktion arbeiten (F4). `offen` bleibt für F1 (Fälligkeit)
   zuständig – und führt dort nur echte Arbeit.
3. **Kein Eintrag wird gelöscht.** Der Vorlauf bleibt vollständig erhalten –
   als `vorlauf`, mit Grund und Frist, und in `arbeitsvorrat` als Obermenge für
   Planung und Kapazität. Das ist die Beweis-Regel des Repos (H6): nichts
   verschwindet, es wird nur richtig benannt.
4. **Fail-closed statt Disziplin.** Der Schreiber kann den Widerspruch nicht
   mehr erzeugen: `queue_invariante` prüft die Zerlegung vor jedem Schreiben;
   ein widersprüchlicher Datensatz wird verweigert, der Lauf endet mit Exit 2.

## 3. Umsetzung – Queue-Schema 2

| Feld | Inhalt | Wer es liest |
|---|---|---|
| `offen` | **Arbeit**: `status: faellig` (Frist erreicht), `status: befund` (offener Fachbefund), `status: unvollstaendig` (Lauf abgebrochen) | Redaktion, Lauf, Wächter |
| `vorlauf` | **Termin**: Frist rückt näher, aber weder fällig noch befundbehaftet – Grund „frisch geprüft vor N Tagen“ | Planung, Report |
| `arbeitsvorrat` | Obermenge von `offen` und `vorlauf` | Kapazität, Deckungsrechnung |
| `fachbefunde` | Befunde mit `id`, `typ`, `text`, `fassung_sha256` – **nur hier** | Ledger, Publish-Gate, BEFUND-AKTE |

Jeder Eintrag trägt seinen `status`; `queue_status_von()` leitet ihn aus
`faellig`/`befund`/`unvollstaendig` ab – er wird nie von Hand gesetzt. Damit
gibt es keine zweite Wahrheit, die auseinanderlaufen kann.

**Schreiber** (`scripts/faktenfrische.py`):

* `queue_daten_bauen()` zerlegt den Arbeitsvorrat in `offen` und `vorlauf`,
  setzt den Status und prüft `queue_invariante`, **bevor** der Datensatz
  zurückgeht. Ein Verstoß ist ein lauter Abbruch (Exit 2), kein stiller
  Teilerfolg.
* Der Lauf markiert abgebrochene Seiten (`unvollstaendig: true`) und Seiten mit
  offenem Fachbefund (`befund: true`) an der Quelle; der Schreiber erfindet
  nichts.
* `--queue-normalisieren` hebt bestehende Dateien idempotent auf Schema 2 –
  ohne Netz, ohne Artikeländerung, ohne erfundene Frist. `--apply` schreibt,
  ohne `--apply` ist es ein Trockenlauf. Der `--apply`-Pfad führt vorher den
  Selbsttest aus (kein Schreibvorgang ohne grünen Selbsttest).

**Wächter** (`queue_invariante` + Tests):

1. `arbeitsvorrat` = `offen` ∪ `vorlauf`, disjunkt und lückenlos.
2. `offen` enthält **nie** einen Eintrag mit `status: vorlauf` – der Befund
   selbst (#1126) ist damit ein Strukturfehler, kein Grenzfall.
3. `vorlauf` enthält nie fällige, befundbehaftete oder abgebrochene Arbeit.
4. Kein Eintrag der Arbeitsliste trägt `id`/`text`; Befunde bleiben im Ledger.
5. Jeder Eintrag nennt `slug`, `faellig` (bool) und `frist` (auch `null`).

**Dokumentation:** `scripts/FAKTENFRISCHE.md` (Betrieb) und
`docs/ANLEITUNG-FAKTENFRISCHE.md` (Verfahren) beschreiben Schema 2 und den
Migrationsbefehl. Die Aktentests #763/#823/#911 prüfen jetzt drei Messhöhen
über `scripts/tests/faktenfrische_gleis.py`: Ledger, `offen`, `arbeitsvorrat`.

## 4. Beweis (lokal nachgefahren, 10.11.2026)

```
$ python3 scripts/faktenfrische.py --queue-normalisieren --apply
✅ Selbsttest Faktenfrische: 40/40 Fälle grün.
✅ Queue-Schema 2 · 24 Einträge · offen 0 (Befund 0, unvollständig 0) · Vorlauf 24

$ python3 -c "import json;q=json.load(open('data/faktenfrische_queue.json'));print(q['schema'],len(q['offen']),len(q['vorlauf']),len(q['arbeitsvorrat']))"
2 0 24 24

$ python3 -m unittest \
    scripts.tests.test_faktenfrische_763 \
    scripts.tests.test_faktenfrische_823 \
    scripts.tests.test_faktenfrische_911 \
    scripts.tests.test_faktenfrische_messhoehe
Ran 64 tests … OK (skipped=1)

$ python3 scripts/faktenfrische.py --selftest
✅ Selbsttest Faktenfrische: 40/40 Fälle grün.

$ python3 scripts/automation_premium_audit.py --strict
🟢 alle Actions gepinnt, alle Jobs mit Timeout/Permissions/Concurrency
```

Die beiden Tests aus dem Befund sind grün, **weil** die Daten stimmen – nicht,
weil die Prüfung abgeschaltet wurde. Die Sabotageproben in
`test_faktenfrische_messhoehe.py` beweisen die Gegenrichtung: Ein Vorlauf-
Eintrag in `offen`, eine aus `offen` entfernte Arbeit, eine fällige Seite im
`vorlauf` und Befunddaten im Vorrat machen die Wache rot.

## 5. Was ausdrücklich offen bleibt

* **Offene Fachbefunde außerhalb des Terminplans** stehen im Ledger und in
  `BEFUND-AKTE.md` (F4, Governance C46). Die Queue ist der Faktenfrische-Plan
  (F1) – sie ist kein zweites Befundregister. Wer einen Befund entscheiden
  will, arbeitet mit der Akte, nicht mit dieser Datei.
* **Die 140 offenen Fachbefunde** sind Bestand der Redaktion. Dieser Vorgang
  schließt keinen davon – ein grüner `regression`-Job ist kein fachlicher
  Freispruch.
* **Die Kadenz-/Deckungsfrage** aus #912/#1039 ist unberührt; Schema 2 ändert
  weder Budget noch Intervalle, nur die Benennung des Vorrats.

## 6. Rückfall-Schutz (was einen Rückfall rot macht)

| Wächter | Ort | Wirkung |
|---|---|---|
| `queue_invariante` | `scripts/faktenfrische.py` | verweigert das Schreiben eines widersprüchlichen Datensatzes (Exit 2) |
| ST9a–ST9k | `faktenfrische.py --selftest` | prüft Zerlegung, Status und drei Sabotagefälle; läuft vor jedem `--apply` |
| `QueueSchemaVertrag` | `scripts/tests/test_faktenfrische_messhoehe.py` | prüft Erzeuger, Artefakt, Invariante und vier Sabotagen |
| `MigrationUndIdempotenz` | dto. | Schema-1-Datei wird gehoben, kein Eintrag/Termin verloren, zweiter Lauf byte-gleich |
| `KeinRueckfallInsFalscheFeld` | dto. | AST-Wache: die drei Aktentests dürfen `offen` nicht wieder als Befundliste lesen |
| `FeldnameBleibtEhrlich` | dto. | `"offen": arbeitsvorrat` (Alias) ist verboten; Status muss abgeleitet werden |
| Aktentests #763/#823/#911 | `scripts/tests/` | prüfen Ledger **und** `offen` **und** Arbeitsvorrat |

Wer den Alias wieder einführt, `offen` wieder mit dem Vorlauf füllt oder die
Invariante abschaltet, macht den `regression`-Job rot – und zwar mit Namen
(`scripts/ci_tests.py` annotiert den roten Test seit #1137).

## 7. Rollback

Ein Rollback ist ein Daten-Rollback, kein Code-Rollback: Die Queue lässt sich
aus dem letzten Commit wiederherstellen (`git checkout <sha> --
data/faktenfrische_queue.json`), der Code bleibt Schema 2. Ein echter
Rückbau des Schemas wäre nur mit einem bewussten Vertragsbruch möglich – und
würde von `queue_invariante` und den Tests sofort rot gemeldet. Das ist
gewollt: Ein Zustand, den niemand mehr erklären kann, darf nicht wieder
entstehen.

## 8. Geänderte Dateien

* `scripts/faktenfrische.py` – Schema 2, `queue_status_von`,
  `queue_invariante`, fail-closed-Schreiber, `--queue-normalisieren`,
  Selbsttest ST9a–ST9k.
* `data/faktenfrische_queue.json` – auf Schema 2 migriert (24 Einträge,
  `offen: 0`, `vorlauf: 24`, `arbeitsvorrat: 24`); kein Eintrag verloren.
* `scripts/tests/faktenfrische_gleis.py` – drei Messhöhen statt einer.
* `scripts/tests/test_faktenfrische_763.py`, `…_823.py`, `…_911.py` –
  Aktentests prüfen zusätzlich, dass die Seiten nicht als Arbeit in `offen`
  stehen.
* `scripts/tests/test_faktenfrische_messhoehe.py` – Vertrag Schema 2 mit
  Sabotageproben, Migrationstest und AST-Rückfallwache.
* `scripts/FAKTENFRISCHE.md`, `docs/ANLEITUNG-FAKTENFRISCHE.md` – Betrieb und
  Verfahren.
* dieser Bericht.
