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

$ python3 -m unittest discover -s scripts/tests      # volle Suite, sauberer Baum
Ran 5787 tests in 689.616s
OK (skipped=6)

$ python3 scripts/selftest_clock.py --trap-modul scripts.tests.test_faktenfrische_messhoehe --offset 97
✅ scripts.tests.test_faktenfrische_messhoehe: bleibt unter einer um 97 Tage
   vorgestellten Uhr grün. (15 Tests, darunter alle Fristen 2026-11-13…23)

$ python3 scripts/blustradius_register.py --check
✅ Blustradius-Vertrag erfüllt: 86 Schritte des Auslieferungswegs erklären ihren Blustradius.
```

Und derselbe Job in der CI (Lauf 42890209624, Commit `4c82a37`, Job
`regression`, 40 min): **alle Schritte grün**, ausdrücklich

* `Code-Regression – Suite und Selbsttests` → success,
* `Uhr-Probe – die Suite muss an jedem Kalendertag grün sein` → success,
* `KI-Probe`, `Beweis-Ledger-Isolation`, `Beweis-Ledger unberührt` → success.

Das ist der Beweis am gemessenen Ort: Der Job, der den Befund trug, ist
grün – nicht nur ein lokaler Nachlauf.

Die beiden Tests aus dem Befund sind grün, **weil** die Daten stimmen – nicht,
weil die Prüfung abgeschaltet wurde. Die Sabotageproben in
`test_faktenfrische_messhoehe.py` beweisen die Gegenrichtung: Ein Vorlauf-
Eintrag in `offen`, eine aus `offen` entfernte Arbeit, eine fällige Seite im
`vorlauf` und Befunddaten im Vorrat machen die Wache rot.

## 5. Zusätzliche Rots im selben Job (beim Beweis gefunden und geheilt)

Der Befund nennt zwei Tests. Beim Nachfahren der vollen Suite wurden **weitere**
Rots sichtbar, die nicht aus #1126 stammen, aber denselben Job blockieren. Sie
sind mitgeheilt, jede mit derselben Regel: Vertrag erhalten, nicht Prüfung
abschalten.

| Rot | Ursache | Heilung |
|---|---|---|
| `test_suche_pagefind` (2), `test_manifest_guard` (1) | Dependabot-Bump pagefind 1.5.2 → 1.6.0 (#1140) war in `package.json` + Lockfile korrekt, aber drei Tests trugen die Version als Literal | Tests prüfen jetzt den VERTRAG: exakter Pin (kein `^`/`~`), gleiche Version in `package.json` und `package-lock.json`, pagefind als einzige Produktionsabhängigkeit. Der Vorfall-Nachbau im Manifest-Guard holt seine Version aus dem Bestand. |
| `test_local_verification` (2) | `requirements-hugo.txt` war durch den Python-Gruppen-Bump (#1142) auf 0.169.0 mit zehn Hashes gesprungen, während Action und 30 Workflows weiter 0.168.0 fahren | `requirements-hugo.txt` wieder auf den einen, im Aktions-Fallback verifizierten 0.168.0-Wheel-Hash gesetzt – lokale Prüfung und CI bauen dieselbe Version. |
| `test_gsc_abdeckung`, `test_gsc_artefakte`, `test_authority_engine`, `test_konsolidierung` (4) | `data/gsc/abdeckung/befund.json` war ein Spleiß aus zwei Läufen (fehlendes Komma, doppelte Fragmente); die Rohartefakte unter `data/gsc/` waren auf `main` bereits durch #1162 geheilt | Befund mit dem sanktionierten Erzeuger neu geschrieben (`gsc_abdeckung.py --audit --schreiben`). Das Ergebnis ist feldgleich mit dem letzten gültigen Git-Stand (11-10) – nichts erfunden, nur der Spleiß entfernt. |
| `test_blustradius_register` (3), `test_bot_watchdog_meldetakt` (1), `test_pflichtcheck` (1) | PR #1162 (10.11. 18:54) stellte den Schritt „GSC-Leistungsdaten – Artefaktprüfung (fail-closed)“ in den deploy-Job, ohne ihn im Blustradius-Register zu erklären – der Vertrag C38 meldet das sofort und zu Recht | Schritt im Register als `inhalt` erklärt: Die GSC-Daten sind die Rechengrundlage der Konsolidierungsregel F; ein gemischter Export würde eine Inhaltsentscheidung auf falscher Grundlage treffen. Kein `werkzeug`, weil hier das versionierte Artefakt geprüft wird, nicht die Website-Messung. |
| `test_offenlegung_gate` (1), `test_reserve_pipeline` (2) | #1170 (10.11. 19:01) fügte die harte Gate-Regel `kurzantwort_failures` hinzu, ohne Deckungszeile in `reserve_healer_coverage.py` – die Reserve hätte Nacht für Nacht an einer Regel geparkt, die kein Heiler kennt | Begründete AUSNAHME statt Heiler: Die Kurzantwort ist eine redaktionelle Aussage (M4); ein Generator würde sie erfinden (C15). Kandidat bleibt als Entwurf/Hold, die Redaktion ergänzt. |
| `test_faktenfrische_1072` (9 Sub-Fehler, nur im CI-Merge) | #1163 (WF-7B6B/#1148) hat den Waschmaschinen-Artikel am 10.11. neu belegt: acht Quellen, neue Modellrechnung, die fünf beanstandeten Aussagen entfernt. Die fünf #1072-Entscheidungen vom 05.11. hingen an Ankern der alten Fassung und an einer Beleg-URL, die der Bericht ausdrücklich als nicht tragfähig verworfen hat | Die fünf Einträge stehen jetzt als `status: ueberholt` mit `abgeloest_am`, Nachfolge-Dokument und Begründung da. Der Test prüft die Ablösung statt eines Ankers, den die neue Fassung zu Recht nicht mehr enthält – und verlangt, dass das Nachfolge-Dokument existiert und den Artikel nennt. `verboten_behauptend` bleibt für **alle** Einträge scharf; eine Sabotage-Probe belegt, dass „überholt“ kein Freispruch ist. Die F4-Befunde bleiben im Ledger offen – die neue Fassung muss redaktionell neu entschieden werden, nicht durch ein Etikett. |
| `Integritäts-Siegel` (CI-Job, bricht den PR ab) | Drei weitere GSC-Abdeckungsartefakte waren Text-Merges aus zwei Läufen: `verlinkungsheilung.json` und `ursachen.json` mit doppelten Schlüsseln, `prioritaet.json` mit fehlendem Komma (A1/A2 des Artefakt-Wächters) | `prioritaet.json` mit dem sanktionierten Erzeuger neu berechnet (dieselben 111 URLs, kein Verlust); in den beiden anderen der überholte 09.11.-Kopf entfernt, der 10.11.-Stand bleibt. `artefakt_waechter` → 627 Artefakte heil. |
| `test_publication_reliability` (1) | Derselbe #1170-Block: Der R5-Fixture-Post trug keine `kurzantwort`; der Test maß dadurch die neue Frontmatter-Regel statt der R5-Heilung | Fixture-Frontmatter um eine echte Kurzantwort ergänzt – der Test misst wieder, was sein Name sagt. |

Nicht durch Code heilbar und hier ehrlich benannt: Die Tests
`test_ki_cover_*`/`test_veroeffentlichungs_wache` brauchen Pillow, der
Feed-Test braucht einen echten Hugo-Build. Beides liefert die CI
(`requirements-ci.txt`, Hugo-Schritt vor der Suite); lokal wurden sie mit
installiertem Pillow und Hugo 0.168.0 zusätzlich nachgefahren.

## 6. Was ausdrücklich offen bleibt

* **Offene Fachbefunde außerhalb des Terminplans** stehen im Ledger und in
  `BEFUND-AKTE.md` (F4, Governance C46). Die Queue ist der Faktenfrische-Plan
  (F1) – sie ist kein zweites Befundregister. Wer einen Befund entscheiden
  will, arbeitet mit der Akte, nicht mit dieser Datei.
* **Die 140 offenen Fachbefunde** sind Bestand der Redaktion. Dieser Vorgang
  schließt keinen davon – ein grüner `regression`-Job ist kein fachlicher
  Freispruch.
* **Die Kadenz-/Deckungsfrage** aus #912/#1039 ist unberührt; Schema 2 ändert
  weder Budget noch Intervalle, nur die Benennung des Vorrats.

## 7. Rückfall-Schutz (was einen Rückfall rot macht)

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

## 8. Rollback

Ein Rollback ist ein Daten-Rollback, kein Code-Rollback: Die Queue lässt sich
aus dem letzten Commit wiederherstellen (`git checkout <sha> --
data/faktenfrische_queue.json`), der Code bleibt Schema 2. Ein echter
Rückbau des Schemas wäre nur mit einem bewussten Vertragsbruch möglich – und
würde von `queue_invariante` und den Tests sofort rot gemeldet. Das ist
gewollt: Ein Zustand, den niemand mehr erklären kann, darf nicht wieder
entstehen.

## 9. Geänderte Dateien

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
* `scripts/tests/test_suche_pagefind.py`, `scripts/tests/test_manifest_guard.py`,
  `requirements-hugo.txt`, `data/gsc/abdeckung/befund.json`/`.md` – die
  zusätzlichen Rots aus Abschnitt 5.
* `data/gsc/abdeckung/{prioritaet,ursachen,verlinkungsheilung}.json` –
  Merge-Spleiße entfernt bzw. mit dem Erzeuger neu berechnet.
* `data/blustradius-deploy.yml` – der neue GSC-Artefaktschritt erklärt
  (Klasse `inhalt`, Begründung im Register).
* `scripts/reserve_healer_coverage.py` – begründete Ausnahme für
  `kurzantwort_failures`.
* `scripts/tests/test_publication_reliability.py` – R5-Fixture trägt die
  seit #1170 geforderte Kurzantwort.
* `data/faktenfrische_befunde_1072.yaml` – fünf Einträge als `ueberholt`
  ausgewiesen (Fassungsbindung nach #1163).
* `scripts/tests/test_faktenfrische_1072.py` – Statusvertrag, Ablösungs-
  beweis und Sabotage-Probe.
* dieser Bericht.
