# Kurzantwort-Verlust #1110 – Dauerheilung auf Highend-Level

Stand: 7. November 2026. Auftrag: „Redaktion: Kurzantwort fehlt am frischen
Live-Artikel `2026-10-28-oekostrom-anbieter-wechseln-sicher-gruen-und-bezahlbar`
(M4, Content-Bot `0b55fca`) – bitte dauerhaft auf Highend-Level einer
Profi-Agentur beheben.“ Umsetzung auf dem Arbeitsbranch
`arena/3fce388a-franksfinanzcheck-blog`, Freigabe über Pull Request.

**Die wichtigste Auskunft zuerst:** Der Artikel ist **nicht** mehr kaputt – die
Kurzantwort steht im Bestand und M4 ist grün. Genau deshalb wäre „Kurzantwort
wieder einfügen“ hier **keine** Heilung gewesen, sondern eine Beruhigungspille:
Der Text war schon da, und der Weg, der ihn zweimal verschluckt hat, war noch
offen. Diese Arbeit schließt den **Weg**, nicht den einen Text.

---

## 1. Befund: reproduziert, nicht vermutet

### 1.1 Der Ist-Stand des Artikels

| Prüfung | Ergebnis |
|---|---|
| `kurzantwort` im Arbeitsbaum | **vorhanden** (Zeile 5, vollständiger Wortlaut) |
| `kurzantwort` in `HEAD` | **vorhanden** (`git show HEAD:… \| grep -c '^kurzantwort:'` → `1`) |
| Metadaten-Wache Bestand | `116 Dateien \| Befunde: 0 \| Geheilt: 0` |
| Nachlauf-Wache Bestand | `grün: Frontmatter, Metadaten, Register, Akte und Kanaltreue` |

Ein Nachfüllen des Feldes hätte also **nichts** geändert. Der Befund liegt
nicht im Text, sondern im Schreibweg.

### 1.2 Die Ursache hat zwei Hälften – beide nötig, keine hinreichend

**(a) Der Artikel war ungesiegelt und damit schreibfrei.**
`redaktionelle_pruefung.status` steht auf `"ausstehend"`, ein `inhalt_sha256`
fehlt. In `scripts/editorial_review_gate.py` entscheidet genau diese eine Zeile
über den Schreibschutz:

```python
protected = review.get("inhalt_sha256") or str(review.get("status") or "").strip().lower() in APPROVED_STATUSES
```

Ohne Siegel ist `protected` falsch, `automatic_change_findings` gibt `[]`
zurück – die Automatik darf an diesem Artikel **jedes** gebundene Feld ändern,
auch `kurzantwort`. Der YMYL-Schutz ist ein Siegel-Schutz, kein Feld-Schutz;
für frische, noch nicht fachgeprüfte Artikel greift er definitionsgemäß nicht.
Das ist **kein** Fehler des Siegels – es ist eine Lücke zwischen zwei
Verantwortlichkeiten.

**(b) Der Deploy-Lauf committet ohne Ausgangsprüfung.**
`.github/workflows/deploy.yml` heilt im `deploy`-Job über viele Schreiber
(Kadenz, Titel, Cover, Taxonomie, Spam, KI-Kennzeichnung, LCP) und persistiert
das Ergebnis anschließend als **Content-Bot**:

```yaml
- name: Gate-Heilungen committen (konvergent)
  run: |
    git config user.name "Content-Bot"
    git add -A
    git commit -m "fix(gate): Kadenz-/Titel-/Cover-Heilungen vor Veröffentlichung (automatisch)"
```

Genau dieser Schritt ist der Ursprung von `0b55fca`. Er committet mit
`GITHUB_TOKEN` direkt nach `main` – **kein PR-Gate prüft diesen Commit**. Bis
zu diesem Schritt gab es im ganzen Lauf **keine** Prüfung, ob ein Schreiber ein
Pflichtfeld *verloren* hat. C32 bewacht den **doppelten** Schlüssel, nicht den
**verlorenen**. Die Nachlauf-Wache (`veroeffentlichungs_wache.py`) kennt die
Klasse, steht aber nur in `content-reserve.yml` und
`bestand-regression-wache.yml` – **nicht** im Deploy-Pfad, und sie meldet
bewusst nur (§6 von `NACHLAUF-WACHE-AUTOMATIK-2026-11-06.md`: „Heilung braucht
einen Besitzer“). Zwischen Schreibverlust und Meldung liegt die Auslieferung.

### 1.3 Die Klasse ist bewiesen, der historische Einzeltäter nicht mehr greifbar

Alle heute im Deploy-Pfad laufenden Schreiber wurden einzeln geprüft
(`keyword_optimizer.fm_set`, `metadaten_wache`-Heiler, `check_titles`,
`check_covers`, `cadence_guard`, `park_state`, `tag_governance`,
`fm_boundary_guard`, `meta_optimizer`). **Keiner** davon reproduziert den
Verlust am heutigen Artikelstand. Der Verlust wurde stattdessen als **Klasse**
reproduziert – Entfernen der `kurzantwort`-Zeile:

```
M4 vorher: []
M4 nachher: [{'rule': 'M4', 'msg': 'Kurzantwort fehlt'}]
```

Der Befund ist also **messbar** – nur hat ihn im Deploy-Lauf niemand erhoben,
und nichts hat ihn aufgehalten. Deshalb ist die Heilung hier bewusst **nicht**
ein Patch an einem einzelnen Schreiber (das wäre Whack-a-mole beim nächsten
Schreiber oder Merge), sondern eine **Invariante am Ausgang des Schreibwegs**.

---

## 2. Die Heilung: eine Invariante vor dem Commit

Neu: `scripts/pflichtfeld_verlust_wache.py` (593 Zeilen). Ihr Vertrag in drei
Sätzen – jeder ist im Selbsttest bewiesen:

1. **Verlust ist messbar, nicht geraten.** Ein Pflichtfeld gilt als verloren,
   wenn `HEAD` es trug, der Arbeitsbaum es nicht mehr trägt **und** die
   Metadaten-Wache (M4) den Verlust bestätigt. Welche Felder Pflicht sind,
   entscheidet **M4 selbst** – importiert, nicht kopiert. Der Selbsttest pinnt
   die Liste gegen M4: jedes Feld muss einen M4-Befund auslösen, wenn es fehlt.
   Driftet M4, wird der Test rot, nicht die Wache blind.
2. **Heilen heißt zitieren, nicht erfinden.** Zurückgeholt wird **bytegenau aus
   `git show HEAD:<pfad>`** – der zuletzt redaktionell committe Stand, in
   derselben Schreibweise (Quotes, Einzug, Blockliste). Kein `yaml.dump`, kein
   KI-Text, keine erfundene Quelle. Der **Body bleibt bytegleich**. Stand das
   Feld auch in `HEAD` nicht, wird **nichts** erfunden: der Befund bleibt
   gemeldet und gehört Redaktion/Texter (`generate_kurzantworten.py`).
3. **Kein Befund nimmt einen Artikel offline (C34).** Die Wache heilt und
   meldet; sie blockiert die Auslieferung nicht. Der Restbefund geht über
   `werkzeugbefund.py --melden` an `release-seal` und färbt den Lauf **nach**
   der Veröffentlichung rot – der Meldeweg des Hauses (#676/#740), ohne eine
   einzige neue Berechtigung.

### 2.1 Warum die Position der entscheidende Teil ist

Die Wache steht als **letzter Schreiber** nach `lcp_image_optimizer.py --fix`
und **vor** `Gate-Heilungsdiff merken` / `Gate-Heilungen committen`:

```
… → YMYL-Bestand → LCP-Manifest → Pflichtfeld-Verlust-Selbsttest
  → Pflichtfeld-Verlust-Wache --fix → gate_diff → Content-Bot-Commit → Rebuild
```

In diesem Moment ist `HEAD` der auslösende Commit, also der Stand **vor** den
Heilungen. Der Verlust wird damit **im selben Lauf** gefangen und der schlechte
Commit entsteht gar nicht. Eine Wache erst im Folge-Lauf sähe ein bereits
schlechtes `HEAD` und könnte den Verlust nicht mehr von Absicht unterscheiden.
Genau das ist die Lehre aus dem Vorfall: *„Wache am Ausgang – und zwar im
selben Lauf.“*

### 2.2 Die vier Grenzen, die die Wache nicht überschreitet

| Grenze | Warum | Beweis |
|---|---|---|
| Kein Reset fremder Änderungen | Sie ist kein `git checkout`: Titel-/Cover-Heilungen bleiben stehen, nur das verlorene Feld kommt zurück. | `test_fremde_heilung_wird_nicht_zurueckgedreht` |
| Keine Wertänderung | Ein redaktionell **geänderter** Wert ist kein Verlust und wird nie auf `HEAD` zurückgesetzt. | `test_wertaenderung_ist_kein_verlust` |
| Kein Erfinden | Fehlt das Feld auch in `HEAD` (oder ist die Datei neu), wird nur gemeldet. | `test_nichts_erfinden_wenn_head_auch_fehlt`, `test_neue_datei_ohne_head_wird_nicht_angefasst` |
| Kein Doppelschlüssel (C32) | Ersetzt **an Ort und Stelle** statt anzuhängen – sonst überlebte bei `kurzantwort: ""` die leere Fassung, weil `doppel_freies_feld` die **erste** Zeile behält. | `test_leeres_feld_gilt_als_verlust_und_wird_ersetzt_nicht_verdoppelt` |

Die letzte Zeile ist ein Befund **aus dieser Arbeit**: Der erste Entwurf hat
gehängt statt ersetzt, und der eigene Test hat ihn verworfen. Lesen und
Ersetzen teilen sich jetzt **eine** Blockgrenzen-Funktion (`_block_grenzen`),
damit die beiden Scanner nicht auseinanderlaufen.

### 2.3 Fail-closed: zwei stille Ausfälle, die wie Grün aussahen

Ein Prüfer, der nicht messen kann, darf nicht grün sein (C2/C33). Zwei Ausfälle
waren zunächst genau so getarnt und sind jetzt geschlossen:

| Ausfall | Warum er wie Grün aussah | Jetzt |
|---|---|---|
| PyYAML fehlt | `metadaten_wache` importiert weiter (`yaml = None`), sein Leser gibt nur noch `None` – jede Datei sähe verlustfrei aus. | `_grundlage()` prüft den Parser **und** macht eine Wirksamkeitsprobe am Leser → Exit **2** |
| Git fehlt / kein `HEAD` | Jede Datei sähe wie eine **neue** Datei aus (keine Basis) – ebenfalls verlustfrei. | `git rev-parse --verify HEAD` muss tragen → Exit **2** |

Exit-Codes: `0` = kein offener Verlust (oder geheilt) · `1` = offener Verlust
(Redaktion/Texter) · `2` = Werkzeug/Grundlage ausgefallen. Der Selbsttest
beweist beide Ausfallpfade (S19–S23).

---

## 3. Der Beweis: der Vorfall, nachgespielt am echten Artikel

Wegwerf-Git-Repo, **echter** Artikel aus `HEAD`, echter Deploy-Ablauf inkl.
Content-Bot-Commit. Ausgabe des Laufs vom 07.11.2026:

```
1) Redaktionsstand committed · M4: grün
2) Nach dem Schreibverlust   · M4: ['Kurzantwort fehlt']
   Body unverändert: True
3) Wache --fix (Exit 0):
   ✅ 1 Pflichtfeld(er) aus HEAD zurückgeholt:
      · kurzantwort → content/posts/2026-10-28-oekostrom-…/index.md
4) Nach der Heilung          · M4: grün
   Kurzantwort wortgleich aus HEAD: True
   Body bytegleich zum Schreibstand: True
5) Content-Bot-Commit        · M4: grün
   kurzantwort im Commit: True
6) Folge-Lauf (Exit 0): ✅ kein Pflichtfeld gegenüber HEAD verloren
   keine Reständerung: True
```

Zeile 5 ist die Pointe: **Der Commit, der #1110 erzeugt hat, enthält die
Kurzantwort jetzt.** Zeile 6 beweist Konvergenz – kein Pendel-Commit, kein
Dauer-Diff.

---

## 4. Dauerhafte Absicherung: Governance-Vertrag C49

Eine Wache, die niemand verlangt, führt irgendwann niemand aus. Darum ist die
Verdrahtung selbst vertraglich gepinnt – **C49** in
`scripts/governance_contract.py`:

| Satz | Was C49 prüft |
|---|---|
| a | Die Wache importiert `metadaten_wache` (M4, keine zweite Pflichtliste) und `post_utils` (eine Naht); geheilt wird aus `git show HEAD:`. |
| b | `--selftest` existiert, die Grundlagenprobe existiert, und die Wache steht in `GUARDS` (vertragliches Minimum C6). |
| c | `deploy.yml` ruft `--fix` **vor** dem Diff-Tor und **vor** dem Content-Bot-Commit; der Selbsttest ist verdrahtet. |
| d | Lebende Wirkung: der Selbsttest der Wache läuft im Vertragslauf und ist grün. |

Der Vertrags-Selbsttest prüft C49 **in beide Richtungen** (Hausstil): sieben
Sabotagen müssen rot werden – fehlende Wache, kopierte Pflichtliste, fehlende
HEAD-Quelle, Deploy ohne Heilaufruf, Heilung **nach** dem Bot-Commit, Wache ohne
Selbsttest, Wache ohne Grundlagenprobe – und der echte Zustand muss still
bleiben.

**Namens-Nachzug:** Der Schritt in `link-check.yml` heißt jetzt
`Governance-Vertrag C1–C49 (… Diff-Tor, Pflichtfeld-Verlust)`. Die drei
lebenden Fundstellen sind konsistent nachgezogen (`link-check.yml`,
`scripts/tests/test_linkcheck_reporting.py`, Selbsttest-Ausgabe). Ältere
Berichte bleiben als historische Aussagen unangetastet.

**Blustradius (C38):** Beide neuen Schritte erklären ihren Blustradius in
`data/blustradius-deploy.yml` – der Selbsttest als `gate-selbsttest`
(darf blockieren), die Heilung als `werkzeug` (darf **nie** blockieren).
Der Register-Check meldet `82 Schritte`.

---

## 5. Nachweise

Alle Läufe am 07.11.2026, lokal, mit `PyYAML 6.0.3` / `Pillow 13.0.0`:

| Prüfung | Ergebnis |
|---|---|
| `pflichtfeld_verlust_wache.py --selftest` | ✅ **23 Gruppen** grün |
| `pflichtfeld_verlust_wache.py` (Bestand, lesend) | ✅ `115 Dateien`, kein Verlust, Exit 0 |
| `unittest scripts.tests.test_pflichtfeld_verlust_wache` | ✅ **Ran 27 tests … OK** |
| **Volle CI-Suite** (`unittest discover -s scripts/tests`) | ✅ **Ran 5446 tests … OK (skipped=22)**, Exit 0 |
| `governance_contract.py --selftest` | ✅ `C1–C49 mit Kunstbefunden` |
| `governance_contract.py --quick` | ✅ erfüllt, 47 Regeln, Exit 0 |
| `governance_contract.py` (voll, lebende Wirkung) | ✅ erfüllt, Exit 0 |
| `metadaten_wache.py --selftest` | ✅ 13 Proben + Heiler-Proben |
| `metadaten_wache.py` (Bestand) | ✅ `116 Dateien \| Befunde: 0` |
| `veroeffentlichungs_wache.py --selftest` | ✅ 8 Fälle |
| `veroeffentlichungs_wache.py --wache` | ✅ 5 Bereiche grün |
| `blustradius_register.py --check` | ✅ 82 Schritte |
| `fm_boundary_guard.py --selftest` | ✅ 18 Wert- + 4 Grenz-Fälle + F7 |
| YAML-Gültigkeit (`deploy.yml`, `link-check.yml`, `blustradius-deploy.yml`) | ✅ parses |
| `redos_guard.py --selftest` / Bestand | ✅ 12 Fälle · `751 Python-Dateien, 0 Funde` |
| `konfliktmarker_wache.py --all` | ✅ keine Merge-Marker in `6187 Dateien` |
| End-to-end-Beweis #1110 (Abschnitt 3) | ✅ schlechter Commit entsteht nicht |

Hinweis: `pillow-avif-plugin` fehlt in der Sandbox (AVIF-Varianten werden
übersprungen). Das ist ein bestehender, nicht blockierender Hinweis der
Metadaten-Wache und von dieser Änderung unabhängig.

---

## 6. Ehrliche Grenzen

1. **Der historische Einzeltäter ist nicht überführt.** Kein heutiger Schreiber
   reproduziert den Verlust (Abschnitt 1.3). Die Heilung schließt die
   **Klasse** am Ausgang, nicht einen benannten Sünder. Wer den konkreten
   `0b55fca`-Schreiber benennen will, braucht die CI-Logs jenes Laufs – die
   standen hier nicht zur Verfügung. Das wird nicht weggeraten.
2. **Die Wache schützt nur, was `HEAD` trug.** Ging ein Artikel schon im
   Reserve-Lauf **ohne** Kurzantwort live, ist `HEAD` selbst die schlechte
   Basis: Die Wache meldet (Exit 1 → Siegel), erfindet aber nichts. Dieser
   Fall gehört dem Texter (`generate_kurzantworten.py`, braucht einen
   AI-Provider) und der Redaktion.
3. **Teilweise Verluste in verschachtelten Feldern** (z. B. `cover` steht,
   `cover.alt` fehlt) sind Meldebestand von M4/Nachlauf, nicht dieser Wache.
   Sie holt **Top-Level-Blöcke** zurück; ein Eingriff in fremde Teilfelder
   wäre ein Reset durch die Hintertür.
4. **Der Artikel bleibt ungesiegelt** (`status: ausstehend`). Diese Arbeit
   setzt **keine** Fachfreigabe und kein `inhalt_sha256` – eine YMYL-Freigabe
   ist eine menschliche Entscheidung und wurde nicht vorgegeben. Die
   Invariante wirkt gerade **deshalb** auch ohne Siegel.
5. **Bewusst nicht in den Reserve-Pfad eingegriffen.** `content-reserve.yml`
   hat eine dreischichtige Isolierung (`reserve_stage_guard`,
   `reserve_frontmatter_gate`, Nachlauf-Wache). Der Deploy-Pfad ist der
   bewiesene Ursprung von `0b55fca` und läuft nach jedem Push – also auch nach
   jedem Reserve-Commit. Ein zusätzlicher Schreiber dort wäre ein Eingriff
   ohne eigenen Befund.
6. **Kein `--check`-Schritt im PR-Pfad.** Im PR-Checkout ist der Arbeitsbaum
   sauber, es gibt keinen uncommitted Schreibverlust zu messen; der Schritt
   wäre Prosa. Der PR wird über die Regressionstests und C49 abgesichert.
7. **Dieser Vorgang schließt Issue #1110 nicht automatisch** und enthält keine
   „Closes“-Klausel. Die Freigabe läuft über den Pull Request.

---

## 7. Geänderte Dateien

| Datei | Änderung |
|---|---|
| `scripts/pflichtfeld_verlust_wache.py` | **neu**, 593 Zeilen – Verlust-Wache (M4-SSOT, HEAD-Restore, Body-Beweis, fail-closed), `--fix/--json/--pfad/--selftest` |
| `scripts/tests/test_pflichtfeld_verlust_wache.py` | **neu**, 319 Zeilen – 27 Regressionstests, inkl. Vorfall-Nachspiel am echten Artikel und Verdrahtungs-Beweisen |
| `.github/workflows/deploy.yml` | Selbsttest (hart) + `--fix` (C34-toleriert, Meldeweg ans Siegel) als **letzter Schreiber vor** `gate_diff`/Content-Bot-Commit |
| `scripts/governance_contract.py` | **C49** (Funktion, `run_all`, `RULE_TEXT`, `LABEL`, `GUARDS`) + 7 Sabotage-Proben im Vertrags-Selbsttest; Ausgabe `C1–C49` |
| `data/blustradius-deploy.yml` | beide neuen Schritte erklärt (`gate-selbsttest` / `werkzeug`, C38) |
| `.github/workflows/link-check.yml` | Schrittname `C1–C49` + datierter Namens-Nachzug-Kommentar |
| `scripts/tests/test_linkcheck_reporting.py` | gepinnter Schrittname nachgezogen |

**Keine** Inhaltsdatei wurde geändert: Der Artikel war bereits geheilt, und
eine Heilung, die den Text anfasst, hätte den Befund nur zugedeckt.

---

## 8. Der Satz, der bleibt

> Ein Pflichtfeld, das der letzte Commit trug, überlebt den Lauf – gleichgültig,
> welcher Schreiber es fallen lässt. Und eine Wache, die nicht messen kann,
> ist rot, nicht grün.

Der Text war nie das Problem. Der Weg war es – und der Weg hat jetzt einen
Wächter, der im selben Lauf zuschlägt, in dem der Verlust entsteht.
