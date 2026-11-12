# 🏛️ WF-D4E0 (#1121) – Forensische Kausalanalyse & Dauerheilung auf Agentur-Niveau

**Vorgang:** `WF-D4E0` · Issue **#1121** (`🔧 Wartung · Inhaltsqualität · Vorgang WF-D4E0`)
**Workflow:** `.github/workflows/content-reserve.yml` (`Content-Reserve (täglicher Vorrat)`)
**Referenzlauf:** `43210335142` · Job `131155996163` · `2026-11-12 11:34:37Z`, `schedule`, Commit `1416a66b`
**Datum der Dauerheilung:** `2026-11-12` · Basis-HEAD `28b235b7`
**Alarmbild:** Selbsttests → Artefakt-Wächter → „Stock shortage must not look successful“ – drei rote Schritte, aber nicht drei unabhängige Vorratsfehler.

---

## 1. Was der Lauf tatsächlich meldete

Die Actions-API nennt genau drei fehlgeschlagene Schritte:

| # | Schritt | Einordnung |
|---|---|---|
| 8 | `Selbsttests aller Wachen (entdeckt, uhrfest, schreibfrei)` | **Primärfehler**: Reserve-Heiler-Deckung nicht vollständig |
| 23 | `Artefakt-Wächter (Maschinen-Artefakte strukturell heil)` | Separater Struktur-Befund in GSC-Artefakten |
| 26 | `Stock shortage must not look successful` | **Folge / korrekt fail-closed**: kein grüner Vorrat bei roter Wache bzw. 2/6 Nachweis |

Der Job hat aus gutem Grund keine Reserve-Schreibstufen ausgeführt, sobald der
Wachen-Selbsttest rot war. Das End-Gate darf eine solche Messung nicht als
Erfolg darstellen. „Stock shortage“ zu übergehen oder Schreibschutz trotz
roter Selbsttests einzuschalten wäre keine Heilung, sondern ein Sicherheitsleck.

---

## 2. Reproduktion am exakten Lauf-Commit

Der Commit `1416a66b` wurde in einem isolierten, temporären Worktree geprüft.
Der CI-Selbsttest-Runner lieferte denselben einzigen roten Wachen-Selbsttest:

```text
284 Wachen gelaufen · 566 Uhr-Proben
❌ scripts/reserve_finisher.py --selftest Exit 2:
   Gate-Regel ohne Heiler: [{'regel': 'kurzantwort_failures', 'art': 'keine-deckung'}]
```

**Ursache:** Mit #1110 wurde `kurzantwort_failures` zu einer ablehnenden
Publish-Gate-Regel. Der Lauf-Commit enthielt noch keine Deckungsentscheidung
für diese neue Regel. Deshalb stoppte `reserve_finisher.py` vor der ersten
Heilung; der zentrale Selbsttest-Runner tat genau das, wofür er da ist.

Im aktuellen Basisstand ist die Regel bereits als begründeter redaktioneller
Hold in `reserve_healer_coverage.AUSNAHMEN` eingetragen. Damit ist sie nicht
mehr „vergessen“ und der allgemeine Gate↔Kette-Vertrag kann wieder grün sein.

### Separater Artefakt-Befund

Der Artefakt-Wächter bestand auf dem Lauf-Commit seinen eigenen Selbsttest,
meldete bei der echten Bestandsprüfung aber vier GSC-Artefakt-Funde:

- `data/gsc/abdeckung/befund.json`: ungültiges JSON (A1, Zeile 472)
- `data/gsc/abdeckung/prioritaet.json`: doppelte Schlüssel (A2)
- `data/gsc/abdeckung/ursachen.json`: doppelter Schlüssel (A2)
- `data/gsc/abdeckung/verlinkungsheilung.json`: doppelte Schlüssel (A2)

Das ist eine andere Fehlerklasse als die Reserve-Heiler-Deckung. A2 ist nur
mit der belegten Regel „letzter JSON-Wert gewinnt“ heilbar; A1 wird nicht aus
einer alten Git-Fassung rekonstruiert. Im aktuellen Checkout ist die
Artefaktprüfung wieder sauber: **640 Artefakte, 0 Funde**. Es wurde keine
fremde GSC-Datei aus dem Verlauf blind zurückgeschrieben.

---

## 3. Dauerheilung: menschlichen Inhalt nicht als Maschinenformat tarnen

Die bestehende Ausnahme in `reserve_healer_coverage.py` zieht eine klare,
fachlich richtige Grenze: Eine Kurzantwort ist redaktioneller Inhalt. Sie darf
nicht allein aus Titel und Description als vermeintlich deterministische
Formatreparatur erzeugt werden. Ein Finanzsatz ohne belastbare Grundlage wäre
kein Qualitäts-Fix.

Bei der Reproduktion zeigte sich jedoch ein Widerspruch: `generate_kurzantworten.py`
war trotz dieser Ausnahme noch in `reserve_finisher.HEALER_CHAIN` eingetragen.
Damit konnte der Reserve-Finisher genau den KI-Schreiber ausführen, den seine
Deckungsregel als **nicht** geeigneten Reserve-Heiler klassifiziert.

Die Kette ist jetzt konsistent:

1. `generate_kurzantworten.py` ist aus der Reserve-Finisher-Kette entfernt;
   der Content-Engine-Aufruf bleibt bestehen. Wenn sein YMYL-Schreibvertrag eine
   Änderung ablehnt, zählt das Skript sie jetzt als übersprungen/fehlgeschlagen
   und meldet den Schreibschutz – nicht mehr fälschlich als erzeugte Antwort.
2. `kurzantwort_failures` bleibt ausdrücklich als redaktioneller Hold
   klassifiziert. Die Reserve erfindet keine Finanz-Antwort, um ein Zertifikat
   grün zu färben.
3. `reserve_finisher.py --selftest` prüft diesen Vertrag jetzt ausdrücklich:
   Die Kurzantwort-Regel muss eine begründete Ausnahme sein und der
   KI-Kurzantwortschreiber darf nicht in der Reserve-Heilerkette stehen.
   Wird die Ausnahme entfernt oder der Schreiber versehentlich wieder
   verdrahtet, wird genau dieser Selbsttest rot – bevor der Nachtlauf startet.
4. Alle anderen belegten, datei-bezirkelt laufenden Reserve-Heiler bleiben
   aktiv. Der Workflow darf sie nach grünen Wachen-Selbsttests automatisch
   ausführen; der Artefakt-Wächter darf weiterhin nur beweisbare A2-Dubletten
   heilen.

---

## 4. Ehrliche Bestandslage – kein künstliches Grün

Der vom Referenzlauf gespeicherte Nachweis steht bei **2/6**. Die Kandidaten
tragen unter anderem Hash-Drift, fehlende Kurzantwort, Textdopplungen,
Einzigartigkeitsbefunde, fehlende Faktenbelege und unbelegte Zahlenbehauptungen.
Der End-Gate muss rot bleiben, bis frische Produktions-Gates mindestens sechs
Kandidaten belegen.

Diese Reparatur macht die Ursache des Selbsttest-Ausfalls dauerhaft
klassifizierbar und lässt die *sicheren* Selbstheilungen wieder anlaufen. Sie
behauptet nicht, dass quellen- oder einzigartigkeitsbezogene Befunde, die
menschliche Redaktion erfordern, automatisch erledigt seien. Solche Inhalte
bleiben sichtbar und zurückgestellt,
statt mit erfundenen Belegen, Kurzantworten oder einem alten Zertifikat
überstimmt zu werden.

---

## 5. Verifikation

| Prüfung | Ergebnis |
|---|---|
| Exakter Lauf-Commit `1416a66b`, `selftest_runner.py` | 🛑 **1 reproduzierbarer Fehler**: fehlende Deckungsentscheidung für `kurzantwort_failures` |
| Exakter Lauf-Commit `1416a66b`, Artefakt-Wächter | 🛑 A1-JSON-Syntaxfehler + 3 A2-Doppel-Schlüssel-Funde; kein Wächter-Selbsttestfehler |
| `reserve_finisher.py --selftest` nach Reparatur | ✅ grün; Kurzantwort-Hold und Ausschluss des Generators explizit geprüft |
| `reserve_healer_coverage.py --selftest` | ✅ grün |
| `scripts.tests.test_ymyl_maintenance_writers` | ✅ **11 Tests**; YMYL-Schreibschutz wird als nicht erledigte Heilung gemeldet |
| `artefakt_waechter.py --selftest` | ✅ grün |
| `artefakt_waechter.py --json` auf aktuellem Checkout | ✅ **640 geprüft, 0 Funde** |
| `integrity_guard.py --gate` | ✅ 55 versiegelte Kerndateien unverändert |
| Vollständiger `selftest_runner.py` | ✅ **284 Wachen, 568 Uhr-Proben, 282,6 s**, alle grün; Hinweis `ki_provenienz.py` erwähnt `--selftest`, implementiert ihn aber nicht und wird deshalb korrekt nicht ausgeführt |

**Betriebsgrenze:** Der nächste grüne Lauf auf `main` muss den Vorrat frisch
messen und die sichere Heilerkette ausführen. Das Issue bleibt bis zu diesem
Nachweis offen; ein lokaler Code-Test ist kein Ersatz für einen produktiven
6/6-Nachweis.
