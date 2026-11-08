# Schließakte: Struktur-Dauerheilung, Fail-closed-Guard und Selbstheilung

**Stand:** 08.11.2026 · **Vorgänge:** #1098 (Release-Scorecard: F4 nicht beweisbar),
#1126 (Regressionssuite repo-weit rot), #1120 (Akte nicht auf dem Stand der Queue),
#1072 (Befund-Ledger) · **Klasse:** Beweis-/Strukturfehler, kein Fachurteil

> **Kurzfassung.** Die menschliche Schließakte
> `data/faktenfrische_entscheidungen.yaml` war strukturell beschädigt: 20
> Folgeentscheidungen standen nicht als eigener Listenpunkt, sondern als
> zweiter Schlüsselblock **innerhalb** eines fremden Eintrags. YAML
> überschreibt doppelte Schlüssel still mit dem letzten Wert. Dadurch trug
> ein Eintrag eine `geprueft_fassung` und einen
> `vorgaenger_geprueft_fassung` aus **zwei verschiedenen Ketten** – die
> Scorecard brach als Werkzeugfehler ab („Ungültige Folgeentscheidung …
> Vorgänger fehlt oder stimmt nicht", #1098), die Akte konnte nicht
> nachziehen (#1120), und zwei Regressionstests lasen an der falschen Stelle
> (#1126). Behoben sind alle drei – mit einer Heilung, die sich selbst
> beweist und ab jetzt automatisch läuft.

---

## 1. Der Befund (gemessen, nicht vermutet)

```
$ python3 scripts/faktenfrische_befund_ledger.py --struktur-pruefen
❌ 11 Listeneintrag/-einträge tragen mehrere Entscheidungen untereinander:
   - Zeile 2383: 2 Entscheidungen in einem Listeneintrag …
   - Zeile 2419: 3 Entscheidungen in einem Listeneintrag …
   … (insgesamt 11 Einträge, 20 verlorene Entscheidungen)

$ python3 scripts/veroeffentlichungs_wache.py --wache
⚠ 1 Werkzeugfehler (kein Inhaltsbefund):
   · [akte] Wache nicht ausführbar: LedgerFehler: Ungültige Folgeentscheidung
     für ('2026-09-23-5-einfache-frugalismus-tricks-fuer-den-alltag',
     'f83f21c1f2e2012f672e'): Vorgänger fehlt oder stimmt nicht
```

**Warum das kein „Inhaltsproblem" war.** Jede betroffene Entscheidung war
belegt: Person, Datum, Begründung, Beanstandung, Befund-ID und Fassung waren
vorhanden – nur nicht an der Stelle, an der YAML sie liest. Ein pauschales
„rot ist rot, dann löschen wir die Einträge" wäre Schein-Grün auf
versioniertem Beweisbestand (history_guard H6) gewesen.

## 2. Ursache in drei Schichten

| Schicht | Defekt | Wirkung |
|---|---|---|
| Daten | Folgeentscheidungen wurden in bestehende Listeneinträge **eingehängt** (Writer-Fehler beim Anfügen) | 20 Entscheidungen unsichtbar; Eintrag widerspricht sich selbst |
| Leser | `yaml.safe_load` überschreibt doppelte Schlüssel **still** | Der Fehler wurde zur „Fachmeinung" umgedeutet statt als Strukturfehler zu scheitern |
| Tests | `test_faktenfrische_823` las `queue = ROOT / 'data' / …` und rief `.get()` auf einem `Path`; beide #763/#823-Tests trugen noch den alten `offen`-Vergleich samt drei Docstrings in einer Methode | `AttributeError` + Fehlalarm auf `main` – **jeder** PR rot (#1126) |

## 3. Was jetzt gilt (vier Schichten, eine Regel)

### 3.1 Fail-closed-Leser (`StrengerLoader`)

`entscheidungen_laden()` liest die Akte über einen Loader, der einen doppelten
Schlüssel **laut** ablehnt – mit Datei-Zeile und Heilbefehl. Ein solcher
Eintrag gilt nie mehr als „nichts gesehen"; er ist ein **Werkzeugbefund**.
Der stille Letzter-gewinnt-Leser existiert nur noch als `_laden_tolerant()`
für den Vorher/Nachher-Beweis im Heiler.

### 3.2 Beweisbarer Heiler (`--reparieren [--apply]`)

Der Heiler zerlegt jeden Listeneintrag an seinen doppelten Schlüsseln wieder
in eigenständige Entscheidungen. Er ist bewusst konservativ:

* **Kein Inhalt wird erfunden.** Beanstandung, Beleg, Person, Datum und
  Begründung bleiben zeichengenau.
* **Zuordnung nur mit Zeugen.** Ein herausgerissener Block hat keinen Slug und
  keine Befund-ID; er wird ausschließlich über seinen **Beanstandungstext**
  einem Ledger-Eintrag zugeordnet – und nur, wenn genau **ein** Eintrag passt.
  Sonst: `fail-closed`, kein Schreiben.
* **Nur verlorene Felder werden ergänzt** (Slug, Befund-ID, Befundfassung,
  geprüft-Fassung), und Kettenfelder nur, wenn sie fehlen
  (`kette_ergaenzt: true` dokumentiert das in der Akte).
* **Fragmente ohne Person/Begründung werden ausgewiesen und verworfen** –
  sie sind per Schema keine Entscheidung. Zusätzlich gilt: Ein verworfener
  Block darf **nie der jüngste Beleg** seines Befunds sein, sonst bricht der
  Heiler ab (Handprüfung statt Datenverlust).
* **Zwei Beweise vor dem Commit:** (1) jeder Block ist vorher/nachher
  feldgleich, (2) die Akte ist streng lesbar und alle Ketten stimmen. Schlägt
  eines fehl, werden die **Original-Bytes** zurückgeschrieben.

### 3.3 Kettenregel: Vorgänger muss existieren, nicht „der letzte" sein

Ein Anfügeprotokoll ist nicht streng chronologisch (zwei Personen bestätigen
denselben Text, ein Lauf zieht ältere Dokumentation nach). Verlangt wird
deshalb: Die `vorgaenger_geprueft_fassung` muss eine Fassung sein, die für
**diesen** Befund bereits dokumentiert wurde. Ein Vorgänger, den es in der
Kette nie gab, bleibt ein Strukturfehler.

### 3.4 Bildzeilen: Herkunft statt Wortlaut

`*Abbildung:`-Zeilen galten pauschal als abgeleitet. Damit fiel eine
**handgeschriebene** Unterschrift mit Prozentwert still aus dem Aussage-Hash –
die Entscheidung wäre blind geblieben. Jetzt zählt die Herkunft: Der Ableiter
schreibt „(eigene Darstellung …)" in die Zeile (bzw. das dokumentierte
Altformat „Gliederung zu … – N Stationen von … bis …"). Alles andere ist
Redaktion und bleibt gebunden. **Beweis, dass das nichts verschiebt:** Alle 40
Bildzeilen des Bestands tragen den Vermerk; die Zahl der offenen Befunde
bleibt bei 24 (vorher/nachher gemessen).

## 4. Automatische Selbstheilung (eingehängt, nicht nur dokumentiert)

| Lauf | Schritt | Wirkung |
|---|---|---|
| `release-scorecard.yml` | „Schließakte strukturell heilen (Selbstheilung, fail-closed)" **vor** jeder Messung: `--selftest` → `--reparieren --apply` → `--struktur-pruefen` | Die Scorecard misst nie mehr auf einer unlesbaren Akte; die Heilung wird mitcommittet |
| `befund-akte-nachziehen.yml` | gleicher Schritt **vor** dem Erzeugen der Akte, eigener Commit-Pfad für die Akte | Push auf `main` heilt die Struktur und zieht die Akte nach (#1120) |
| `faktenfrische.yml` | Heilung **vor** der Dossier-Nachlese, Akte im Commit-Pfad | Der Tageslauf kann keine neue Struktur-Korruption festschreiben |

Jeder dieser Läufe ist **idempotent**: ein zweiter Lauf ohne Defekt schreibt
nichts (`strukturfehler == 0`). Ein doppelter Schlüssel ist ab jetzt in jedem
Lauf Exit 1 – nie wieder „grün, weil unlesbar".

## 5. Verifikation (lokal nachgefahren)

```
$ python3 scripts/faktenfrische_befund_ledger.py --reparieren --apply
✅ 20 verlorene Folgeentscheidung(en) wieder als eigener Listeneintrag geführt
   (187 Entscheidungen gesamt).

$ python3 scripts/faktenfrische_befund_ledger.py --struktur-pruefen
✅ Schließakte strukturell sauber (187 Listeneinträge, keine doppelten Schlüssel).

$ python3 scripts/faktenfrische_befund_ledger.py --wache
Offene Fachbefunde: 24 auf 7 Seiten · überholte Fassung: 16 · ohne Fassung: 0
✅ Jeder offene Befund hat einen Schließweg (eine menschliche Entscheidung am
   heutigen Text).

$ python3 scripts/faktenfrische_befund_akte.py --schreiben
✅ BEFUND-AKTE.md geschrieben: 24 offene Befunde auf 7 Seiten (5 live),
   ältester 5 Tage, Frist 14 Tage, 0 über der Frist.

$ python3 scripts/veroeffentlichungs_wache.py --wache
✅ Nachlauf-Wache grün: Frontmatter, Metadaten, Register, Akte und Kanaltreue
   stimmen.
```

**Semantik-Beweis der Reparatur** (nicht nur „läuft durch"): Für alle 146
Befund-Schlüssel ist die jüngste Entscheidung dieselbe wie vor der Reparatur –
mit **zwei richtigen Ausnahmen**, und genau das war der Defekt:

| Befund | vor der Reparatur | nach der Reparatur | Beleg |
|---|---|---|---|
| `2026-10-07-campingurlaub…` · `3716cfd3` | `3b3904ec` (falsch: Fassung des Vorgängers) | `b2693d4a` | Beanstandung nennt Verbraucherzentrale/Buchungsangaben |
| `2026-09-23-5-einfache-frugalismus…` · `f83f21c1` | `b2693d4a` (fremde Fassung aus dem Camping-Artikel) | `16af0cf1` | eigene Beanstandung: Nahrungsmittel-Inflation |

**Tests:**

| Suite | Ergebnis |
|---|---|
| `scripts.tests.test_faktenfrische_befund_ledger` (20 Tests) | **OK** (vorher 1 Failure, 3 Errors) |
| `test_faktenfrische_763` + `…_823` | **OK** (29 Tests, 1 Skip) |
| `discover -p 'test_faktenfrische*.py'` | **256 Tests OK** |
| `faktenfrische_befund_ledger.py --selftest` | **OK** – inklusive neuer Proben: doppelter Schlüssel scheitert laut, Heiler trennt beweisbar, Fragment ohne Person wird ausgewiesen, zweiter Lauf ändert nichts |
| `governance_contract.py --selftest` (C1–C49) | **OK** |
| Alle 102 Workflows | YAML-valide |

## 6. Was ausdrücklich **nicht** maschinell entschieden wurde

* **#1107 Kadenz-Horizont** – der Takt/Intervall-Korridor bleibt
  Herausgeber-Entscheidung (`docs/ANLEITUNG-FAKTENFRISCHE.md`). Die Wache
  meldet, sie entscheidet nicht.
* **#1028 KI-VO** – das Gate heilt, was mechanisch heilbar ist (Anker,
  RSS-Spiegel, unmarkierte Ableitungen). Die 12 offenen `menschlich`-Einträge
  im Register (`data/ki_kennzeichnung.yaml`, Frist 02.12.2026) brauchen den
  Betreiber: Ob ein Mensch die redaktionelle Verantwortung übernommen hat,
  kann keine Maschine belegen.
* **#448 Pinterest** – Domain-Sperre, Kanal geparkt; Runbook
  `docs/PINTEREST-SPIELBUCH.md`.
* **#1137 Reserve-Zertifikat veraltet** – die Heilung ist der reguläre
  `content-reserve.yml`-Lauf (03:25 UTC) mit `reserve_readiness.py`; das
  Zertifikat wird erst nach vollständiger Messung neu versiegelt. Lokal ist
  die Messung ohne Hugo nicht beweisbar (`hugo fehlt im PATH`) – sie darf
  deshalb hier nicht „nachgestellt" werden.

## 7. Betriebsregeln für die Zukunft

1. **Ein Listeneintrag, eine Entscheidung.** Angehängt wird immer als neuer
   `- slug:`-Block, nie als Feldblock in einem bestehenden Eintrag.
2. **Doppelter Schlüssel = Werkzeugfehler**, nicht „letzter gewinnt".
3. **Kein Freibrief durch Reparatur:** Der Heiler ändert nur Struktur und
   fehlende Felder; er schließt und öffnet keinen Befund fachlich.
4. **Wer heilt, beweist:** Vorher/Nachher-Gleichheit aller Blöcke plus
   strenges Nachlesen – sonst Rollback auf die Original-Bytes.
