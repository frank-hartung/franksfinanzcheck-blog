# Wartung · Inhaltsqualität · WF-D4E0 · #821 – Dauerheilung auf Highend-Agentur-Niveau

**Datum:** 25.10.2026
**Vorgang:** Issue **#821** (`auto-report`, Alert-Key `WF-D4E0`, Bereich *Inhaltsqualität*), Run
[40177233545](https://github.com/frank-hartung/franksfinanzcheck-blog/actions/runs/40177233545) · Schritt
**„Stock shortage must not look successful"** · Job `reserve`.
**Offen seit:** 20.10.2026 · **rot an:** 20., 21., 22., 23. (2×), 24. (2×), 25.10. – jeder Lauf mit
derselben Meldung.
**Stand vorher:** **1/6** gate-fertig (Pool 2), **0** frei disponierbare Themen in der AUTO-Bahn.
**Stand nachher:** **55** frei disponierbare AUTO-Themen = **27,5 Produktionstage** Vorlauf (Mindestvorlauf 14),
Diagnose nennt die Bahn, Wache verhindert das nächste stille Auslaufen.

---

## 1. Forensische Ursachenkette – warum sieben Nächte derselbe Schritt rot wurde

Der Lauf war nicht „zufällig schwach". Er war **planbar ergebnislos**: In der AUTO-Bahn gab es nichts
zu produzieren. Drei Befunde, jeder einzeln belegt, keiner im Ticket genannt.

### 1.1 Die AUTO-Bahn war leer – 154 von 202 Themen galten als „belegt"

```
$ python3 scripts/reserve_topics.py --status      (vor der Reparatur)
Themenpool: 202 Themen · 154 thematisch belegt · 47 im Cooldown
Frei disponierbar: 0 in der AUTO-Bahn (quotenfähig) von 21 über alle Bahnen

$ python3 scripts/engine_capacity.py
🛑 Engine-Kapazität: Kein frei disponierbares AUTO-Thema. …
   Themen 202 = AUTO 147 + FACHFREIGABE 55
   frei disponierbar: AUTO 0 · FACHFREIGABE 21
   Fachfreigabe-Bahn: offen (0/3 im Prüfstapel)
```

Die 21 „freien" Themen waren **ausschließlich** YMYL-Hochrisiko (Hausrat-, Risikolebens-,
Berufsunfähigkeits-, Rechtsschutz-, Reisekrankenversicherung, Ratenkredit, Riester, Baufi, Schufa).
`editorial_review_gate` ist für diese Klasse fail-closed – sie dürfen nie automatisch live gehen.
In der Bahn, aus der die Reserve produzieren darf, war die Zahl **null**.

### 1.2 Warum 154 Themen „belegt" waren: die Dublettenprüfung maß die falsche Menge

`reserve_topics.thema_kollision()` erklärt ein Thema für belegt, sobald **ein** „Leitbegriff" mit
einem bestehenden Artikel übereinstimmt. Die Füllwort-Liste kannte dabei „guenstig", aber **nicht die
gebeugten Formen**. Gemessen über alle 202 Themen, mit dem blockierenden Begriff je Thema:

| blockierender „Leitbegriff" | blockierte Themen | Bewertung |
|---|---|---|
| `guenstige` / `guenstigen` | 13 + 2 | **Füllwort** – Beugung von „günstig" (steht längst in der Liste) |
| `internet` | 8 | Produkt der Bahn, kein Thema |
| `kreditkarten` | 8 | Produkt der Bahn, kein Thema |
| `tarife` | 7 | **Füllwort** – „Tarif" ist die Verpackung, nicht der Inhalt |
| `versicherung(en)` | 10 | YMYL – gehört ohnehin in die Fachfreigabe-Bahn |
| `anbieter` | 4 | Füllwort (Rolle) |
| `wechsel` | 4 | Füllwort (Vorgang) |
| `welche`, `fehler`, `minute`, `herbst` … | 6 | Füllwörter / Jahreszeiten |

Der schwerste Einzelartikel blockierte **23** Themen („…günstige Tarife für 2026"), weil sein Titel
zufällig die Füllwörter „günstige" und „Tarife" enthält. Das ist keine Dublettenprüfung mehr – das ist
ein Leerlauf mit Ansage: **jeder neue Artikel sperrt weitere Themen derselben Wortfamilie**, die
Richtung ist monoton.

### 1.3 Der Befund nannte die falsche Baustelle

`reserve_gate.diagnose()` schrieb in jeden roten Lauf:

> • **THEMENMANGEL: Die Disposition findet kein freies Thema (alles thematisch belegt oder im
> Cooldown).** Nachschub in data/topics.yaml eintragen …

Am 25.10. war das nachweislich falsch: 21 Themen *waren* frei. Wer diesem Satz folgt, prüft
Cooldowns, Dubletten, Provider-Keys und die KI – also alles außer der Ursache. Dieselbe Klasse wie
C33 („ein Artefakt-Defekt sieht aus wie ein leerer Vorrat"): **ein Bahn-Problem sah aus wie ein
Themen-Problem.**

---

## 2. Dauerheilung – vier Eingriffe, jeder mit Gegenprobe

### 2.1 Die Deklinations-Lücke ist geschlossen (`scripts/reserve_topics.py`)

`FUELLWOERTER |= { … }` ergänzt **ausschließlich**, was im Titel nichts unterscheidet:

* Beugungen bereits gelisteter Wörter (`guenstige(n|s|m)`, `billig…`, `einfachen`, `kleinen`, `bester`),
* Rollen-/Vorgangs-Nomen (`tarif(e)`, `anbieter`, `wechsel`, `fehler`, `minute(n)`, `spartipp(s)`),
* Fragewörter (`welche/r/s/n/m`), Jahreszeiten (`fruehling`, `sommer`, `herbst`, `winter`, `spaetsommer`),
* generische Verben/Bewertungen (`rechnen`, `planst`, `erkennst`, `worauf`, `woran`, `sicher`, `online`, …)
  – aufgenommen nur, wenn sie über Bestand + Pool bei ≥ 3 Titeln standen.

**Nicht** aufgenommen: `mietwagen`, `kreditkarte`, `internet`, `stromfresser`, `fixkosten`, `gebuehren`,
`zinsen`, `urlaub`, `ausland`, `fallen`, `pflicht`, `wechselbonus`. Produkte und Sachthemen bleiben
Leitbegriffe – eine bequeme Füllwort-Liste würde die Dublettenprüfung entwerten. Ein Test verbietet
genau das (`test_produkte_bleiben_leitbegriffe`).

**Wirkung, gemessen (nicht geschätzt):** `154 → 127` belegte Themen · frei über alle Bahnen `21 → 45` ·
frei in der AUTO-Bahn **`0 → 19`**.

### 2.2 36 neue AUTO-Themen in `data/topics.yaml`

Jedes Thema ist maschinell geprüft: `engine_capacity.bahn_fuer_thema() == "auto"`, keine
Leitbegriff-Kollision gegen **Bestand (95 Artikel) und Pool (202 Themen)**, drei Keywords, ein zum
Thema passendes `/go/`-Ziel (strom/dsl/girokonto/kreditkarte/tagesgeld/mietwagen/reisen/allgemein) –
kein Versicherungs-, Kredit-, Renten- oder Baufi-Thema, denn die kosten einen Prüfplatz, keinen
Automatik-Slot.

| Pillar | neue Themen |
|---|---|
| `strom-sparen` | 10 (Kühlschrank, Grundlast, Fenster, Steckdosenleiste, Kaffeemaschine, Waschmaschine, Trockner, Spülmaschine, Wasserkosten, Mehrweg) |
| `frugalismus` | 11 (Vorrat, Essensplan, Lebensmittel retten, Secondhand, Möbel, Kleidertausch, Sparziel, Reparatur, Fitnessstudio, Taschengeld, Haustier, Balkon) |
| `internet-dsl` | 6 (Gäste-WLAN, Repeater/Powerline, Router-Position, Streaming-Bandbreite, Homeoffice-Leitung, Mesh) |
| `konto-karten` | 6 (Kontowechselservice, Gemeinschaftskonto, Geschenkkarten, Seniorenkonto, Kartenzahlung) |
| `mietwagen` | 3 (Ferienwohnung, Städtetrip, Carsharing) |

**Wirkung:** Pool `202 → 238` Themen · frei in der AUTO-Bahn `19 → 55` = **27,5 Produktionstage**.

### 2.3 Der Vorlauf ist jetzt eine Wache (`scripts/themen_nachschub_waechter.py`)

```
$ python3 scripts/themen_nachschub_waechter.py
✅ Themennachschub: 55 AUTO-Themen frei = 27.5 Produktionstage bei 2 Artikeln/Tag (Mindestvorlauf 14).
```

* **Stück ist keine Zeit:** Der Vorrat wird in **Produktionstagen** ausgedrückt (`vorlauf_tage()`),
  gemessen über `engine_capacity.lage()` → `reserve_topics.disponieren()` – also mit dem Maß des
  Disponenten. **Keine zweite Zählregel** (Lehre aus #521: „157 frei" vs. „3 frei").
* **Urteile:** `ok` (≥ Horizont) · `knapp` (< Horizont) · `erschoepft` (< Horizont/2 oder 0).
  Horizont über `THEMEN_HORIZON_TAGE` (Default 14), geklemmt und **nie still verschluckt**.
* **Befund nennt die Bahn:** „frei nur in der Fachfreigabe", „beide Bahnen leer", „Vorlauf knapp" –
  jeweils mit Zahl, Cooldowns und Handlungsort.
* **Fahrer:** eigener Schritt in `.github/workflows/content-reserve.yml` **vor** Runde 0, ohne
  `continue-on-error` (ein Befund an die Redaktion gehört in den Lauf), aber **keine** Stufe hängt an
  seinem Ergebnis – Bestandsheilung und Nachzertifizierung laufen weiter (C34: ein Datenbefund friert
  nichts ein).
* **Selbsttest** (C6, im vertraglichen Minimum): Vorlauf-Formel, Bahn-Trennung, Env-Klemmung,
  „grüner Lauf enthält keine Aufforderung" (kein Dauer-Alarm). Uhrfest gegen +97/+1461 Tage und
  schreibfrei geprüft (`selftest_clock.trap`, Arbeitsbaum unverändert).

### 2.4 Der End-Gate sagt jetzt, warum (`scripts/reserve_gate.py`)

`diagnose()` misst über `themen_nachschub_waechter.lage()` (fail-open: alte Messung, wenn das Modul
fehlt) und unterscheidet drei Befunde statt eines Sammelsatzes. Zusätzlich landet die Ursache in der
Gate-Meldung selbst – also dort, wo das Ticket sie liest:

> `::error::Content-Reserve nicht bestätigt (engpass): Aktuell gemessen; Zielbestand noch nicht
> erreicht. Ursache: Kein freies Thema der AUTO-Bahn. Die 21 freien Themen liegen ausschließlich in
> der FACHFREIGABE-Bahn (YMYL, menschliche Freigabe) – daraus kann die Automatik nichts produzieren.
> Das ist Themennachschub, keine KI-Störung und kein Provider-Ausfall.`

---

## 3. Beweis (gemessen, nicht behauptet)

| Prüfung | Ergebnis |
|---|---|
| `python3 scripts/reserve_topics.py --selftest` | ✅ grün |
| `python3 scripts/themen_nachschub_waechter.py --selftest` | ✅ grün |
| `python3 scripts/reserve_gate.py --selftest` | ✅ 8 Fälle |
| `python3 scripts/engine_capacity.py` | ✅ 55 frei, Tagesziel gedeckt |
| `python3 -m unittest scripts.tests.test_themen_nachschub` | ✅ 9 Tests |
| Reserve-Tests (`test_engine_capacity`, `test_reserve_pipeline`, `test_reserve_artifacts`, `test_reserve_vorratsschutz`, `test_themen_nachschub`) | ✅ **206 Tests, OK** |
| `python3 scripts/governance_contract.py --quick` | ✅ **42 Regeln** (neu: C44) |
| Uhr-Probe `selftest_clock.trap` (+97 / +1461 Tage) | ✅ beide grün, keine Schreibspur |
| `docs/GOVERNANCE-KONTRAKT.md` | neu erzeugt, **C44** dokumentiert |

Maschinelle Gegenprobe der 36 neuen Themen: `bahn == "auto"` für 36/36, `0` Kollisionen gegen
Bestand und Pool, `0` Themen ohne Keywords oder ohne `/go/`-Ziel.

Die Schutzrichtung ist mitgeprüft: `Stromfresser`, `Günstige Reiseversicherungen Winter/Sommer`,
`Kreditkarten mit Reiseversicherung` vs. `Kreditkarten für Reisen` und `Gasrechnung senken` kollidieren
**weiterhin** – die Füllwort-Ergänzung hat keine Sachgrenze verschoben.

---

## 4. Restrisiken (ehrlich benannt, nicht versteckt)

1. **RS5 ist der zweithäufigste Grund für Themen-Cooldowns.** Viele Themen scheitern dreimal am
   Profi-Gate „Zahlenbehauptung ohne Satzbeleg" (u. a. das aktuell blockierte Pool-Exemplar
   `2026-10-25-strategisch-sparen-…`, 9 Funde). Das Geburts-Gate misst korrekt; der Schreiber
   verletzt den Zahlen-Vertrag. **Nicht** aufgeweicht: Der Faktenbeleg ist ein Publish-Kriterium
   (C29). Der Retry erhält die Befunde als Korrektur-Auftrag; beobachtet wird das über die
   Diagnosezeile `PRODUKTIONS-FEHLschlag` im roten Lauf. Mit 55 freien Themen ist ein RS5-Ausfall
   jetzt ein Thema-Wechsel, kein Nachtausfall.
2. **Die Fachfreigabe-Bahn trägt 21 freie Themen und einen leeren Prüfstapel (0/3).** Sie kann
   produzieren, aber niemand prüft. Das ist bewusst **nicht** Teil dieses Vorgangs (Redaktionsprozess,
   Issue #826) – die Bahn bleibt fail-closed.
3. **Der Horizont ist eine Betriebsgröße, keine Garantie.** 27,5 Tage Vorlauf sind bei 2 Artikeln/Tag
   gerechnet. Wird die Kadenz erhöht, muss `THEMEN_HORIZON_TAGE` mitwachsen oder der Vorrat nach.
   Die Wache meldet beides, statt zu schweigen.

## 5. Bedienung

```bash
npm run engine:nachschub          # Vorlauf der AUTO-Bahn in Tagen
npm run engine:kapazitaet         # Tageslage (Bahn-getrennt)
npm run test:themen:nachschub     # Wache + Füllwort-Grenze + Diagnose-Tests
```

Nachschub anlegen: Titel (mit Doppelpunkt, wenn > 45 Zeichen), drei Keywords und ein thematisch
passendes `/go/`-Ziel. Danach `python3 scripts/engine_capacity.py` – erst wenn dort
`frei disponierbar: AUTO` steigt, ist der Nachschub angekommen.

**Vertrag:** C44 („Der Vorrat endet nicht, er läuft aus").

---

## 6. Nachtrag (25.10.2026, nach dem Merge von #861): der RS5-Befund log über sich selbst

Der verbliebene Pool-Blocker meldete:

> `RS5: 9 Zahlenbehauptung(en) ohne Satzbeleg oder klare Modellannahme`

Nachgemessen an derselben Datei waren es **5**. Vier der neun „Zahlen" waren
Artefakte des Detektors, keine Aussagen des Artikels:

| gemeldeter „Fund" | was er wirklich war |
|---|---|
| „…Pauschale Aussagen zu den Preisen im **Jahr 2026**…" | Kalenderjahr |
| „…kein Spartrend **für 2026**." | Kalenderjahr |
| „Oktober 2026**." | Satz-Fragment, das ein Fett-Marker zerschnitten hatte |
| „…zu **Issue #763**…" | repo-interne Vorgangsnummer |

Dieselbe Fehlerklasse wie in Abschnitt 1.3, nur eine Ebene tiefer: **nicht der
Lauf log, sondern der Zähler.** Ein Befund, der sich selbst zu hoch zählt,
schickt die Redaktion in die falsche Baustelle – und macht einen Artikel
schlechter, als er ist.

Geheilt in `scripts/redaktions_standard._reserve_numeric_claim_findings`:

* Fett-/Kursiv-Marker werden **vor** der Satztrennung entfernt (sie haben den
  Satz an „16." zerschnitten),
* `#<Zahl>` (Issue-/PR-Referenz) zählt nicht als Zahlenbehauptung,
* eine reine **Kalenderjahreszahl** (1900–2099) ist keine Zahlenbehauptung –
  erst wenn nach ihrem Entfernen eine Zahl mit Einheit übrig bleibt, wird der
  Satz bewertet („Für 2026 rechnet die Bank mit 250 € Jahresgebühr" bleibt ein
  Befund).

**Die Schutzrichtung ist unverändert hart.** Der Kandidat bleibt blockiert –
jetzt mit der Wahrheit (5 statt 9), und er bleibt es zu Recht: „Reichen 120 €
nicht, ändere den Plan." und „Drei Monate reichen zum Prüfen nicht." tragen
weiterhin unbelegte Zahlen und Fristen. Fünf neue Regressionstests in
`scripts/tests/test_zahlen_prompt_vertrag.py` verriegeln beide Richtungen
(Artefakt bleibt still, echte Zahl bleibt rot).
