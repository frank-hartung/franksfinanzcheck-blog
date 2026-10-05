# Keyword-Grammatik & Entwurfs-Lesbarkeit – Premium-Instandsetzung vom 05.10.2026

Nachtrag zu Governance-Report **#585** („Redaktionelle & technische
Handlungsfelder"). Der erste Teil der Instandsetzung ist in
`LESBARKEIT-LIVE-KONSISTENZ-PREMIUM-2026-10-05.md` dokumentiert (Bestands-Gate,
Live/Draft-Konsistenz, R17-Erstfassung). Dieser Report beschreibt den zweiten
Teil: die **Ursache der Keyword-Ruinen** und die **Entwurfs-Pipeline**, damit
kein Artikel mehr unter der Publish-Schwelle in die Warteschlange rutscht.

---

## 1. Befund – maschinell zerstörte Keywords

Die Keyword-Heilung (`scripts/keyword_optimizer.py`) hat das Haupt-Keyword mit
`.lower()` in feste Satzschablonen gestanzt. Im Bestand standen daraus
entstandene Sätze – grammatisch falsch, aber von keiner Wache sichtbar, weil
Lesbarkeit nur Satz- und Wortlängen misst:

| Artikel (Datum) | Ruine im Live-Text |
|---|---|
| 2026-08-21 Mietwagen | „Du willst mietwagen buchen?" |
| 2026-08-24 Preisgarantie Gas | „Du willst [preisgarantie gas](…)?" |
| 2026-09-11 Standby-Kosten | „Du willst standby kosten?" |
| 2026-09-11 Heizungs-Check | „Du willst heizungs-check?" |
| 2026-09-20 Notgroschen | „Du willst finanzieller puffer?" |
| 2026-10-02 Weihnachtsbudget | „Du willst weihnachten budget planen?" |
| 2026-08-17 Privathaftpflicht | „Du willst privathaftpflicht?" |
| 2026-10-05 DNS (Entwurf) | „DNS server ändern", „FRITZ!Box dns", „dns anleitung handy" |

Das ist kein Tippfehler-Problem, sondern ein **Generator-Problem**: Die
Schablone erzeugt die Fehler reproduzierbar bei jedem neuen Artikel.

---

## 2. Strukturelle Heilung (Ursache)

**`scripts/keyword_optimizer.py` – `heal_first_paragraph()`**

* `.lower()` auf dem Keyword ist **entfernt**. Das Keyword wird wortgleich
  eingesetzt, in der Schreibweise des Frontmatters.
* Alle Themen-Sonderfälle (`gasrechnung`, `frugalismus`, `dsl/wlan/dns`) sind
  gestrichen. Sonderlocken pro Thema sind der Weg, auf dem solche Defekte
  zurückkommen.
* Es bleibt **eine** Form: `„{Keyword} im Check: {erster Absatz}"` – eine
  Apposition nach Doppelpunkt. Sie ist in jedem Kasus und mit jedem
  Keyword-Typ (Substantiv, Verbalphrase, Produktname) grammatisch korrekt.
* `DICHTE_SCHABLONEN` folgen derselben Regel: Doppelpunkt vor dem Keyword,
  Keyword am Satzende, keine Flexion.
* Der `--selftest` prüft die Schreibweise jetzt **wortgleich** für drei
  Keyword-Typen („Bankgebühren sparen", „Online-Konten", „Gasrechnung senken").

**`scripts/governance_contract.py` – C21** hält den Zustand fest: `.lower()` auf
dem Keyword ist vertraglich verboten, die Dichte-Schablone muss Doppelpunkt vor
`{kw}` haben und exakt auf `{kw}.` enden, beide R17-Codes müssen in Guard und
Publish-Gate verdrahtet sein.

---

## 3. Wache gegen Rückfall (R17)

`scripts/textverstaendnis_guard.py` kennt zwei Codes mit vier Beweiswegen. Alle
arbeiten **ohne Wörterbuch** und verlangen Beweis aus dem Artikel selbst:

| Weg | Code | Beweis |
|---|---|---|
| 1 | `R17-KEYWORD-KASUS` | kleingeschriebenes Wort nach Artikel/Possessiv/Präposition, das im selben Artikel ≥ 2× satzintern groß steht |
| 2 | `R17-KEYWORD-KASUS` | dasselbe, Beweis aus dem Frontmatter-Feld `keywords:` (dann genügt **ein** Vorkommen) |
| 3 | `R17-KEYWORD-KASUS` | die **vollständige** Keyword-Phrase steht klein im Text („mietwagen buchen" statt „Mietwagen buchen") |
| 4 | `R17-KEYWORD-KASUS` | CTA-Frage der alten Schablone: „Du willst/brauchst/suchst **heizungs-check**?" |
| 5 | `R17-KEYWORD-DOPPEL` | das Satz-Endwort wiederholt sich im selben Satz, endet auf `-en` und kommt im Artikel nie groß vor („… die gasrechnung senken um 15 % senken") |

Gegen Fehlalarme sind vier Negativ-Proben im `--selftest` verankert:

* **Adjektiv vor Substantiv** – „deine finanzielle Freiheit" bleibt frei
  (Keyword „Finanzielle Freiheit" ist nur Titel-Schreibweise).
* **Erstes Keyword-Wort** – „Sicher heizen", „Preiswert surfen" lösen nichts
  aus, solange der Text das Wort nicht selbst satzintern groß führt.
* **Adverb vor Infinitiv** – „Du willst sicher heizen?" ist korrektes Deutsch.
* **Wiederholtes Substantiv** – „20 Millisekunden statt 100 Millisekunden" ist
  kein Verb-Doppel.

Stand nach der Instandsetzung: **0 R17-Funde im gesamten Korpus.**

---

## 4. Korpus-Reparatur

Alle acht oben gelisteten Ruinen sind im Text behoben – nicht durch Löschen,
sondern durch eine tragfähige Formulierung („Standby Kosten im Check: …",
„Eine Preisgarantie beim Gas klingt beruhigend. …"). Die DNS-Schreibweisen sind
durchgängig auf `DNS Server ändern`, `FRITZ!Box DNS`, `DNS Anleitung Handy`
korrigiert – inklusive Titel, Description und Pin-Feldern.

---

## 5. Entwurfs-Lesbarkeit (Paket 1)

Neun Entwürfe lagen unter der Publish-Schwelle 60 und hätten den Bestandswert
beim Livegang sofort wieder gedrückt. Alle sind in einfaches Deutsch
umgeschrieben – Nominalstil zu Verben, 8–10 Wörter je Satz, höchstens drei
Sätze je Absatz, variierte Satzanfänge (R4), `kurzantwort` inklusive. Tabellen,
Listen, `/go/…`-CTAs, Affiliate- und Risikohinweise, NBSP vor `€`/`%` und
geschützte Bindestriche sind unangetastet.

| Entwurf | Flesch vorher | Flesch nachher |
|---|---:|---:|
| Digital Banking: Vorteile moderner Online-Konten | 48,3 | **71,6** |
| Dein Haus sicher schützen: Vorsorge-Update 2026 | 50,0 | **73,8** |
| Bankgebühren sparen: So halbierst du deine Kosten | 51,0 | **74,6** |
| Konto wechseln 2026 | 52,8 | **73,5** |
| E-Auto Ladekosten | 53,1 | **80,3** |
| Strom und Gas: teure Fehler beim Vergleichen | 54,4 | **72,7** |
| DNS Server ändern | 54,7 | **74,6** |
| Die 50-30-20-Regel einfach erklärt | 55,2 | **75,8** |
| Privathaftpflicht: warum so wichtig | 55,5 | **75,2** |

---

## 6. Nachweis (lokal, 05.10.2026)

```
python3 scripts/readability_check.py --gate-bestand
  ✅ 38 Live-Artikel, Ø Flesch 66.5, kein Live-Artikel unter Floor 55
python3 scripts/readability_check.py
  Ø Flesch 67.7 | unter Floor 55: 0 | kein Entwurf unter Publish-Schwelle 60
python3 scripts/readability_check.py --selftest     ✅
python3 scripts/textverstaendnis_guard.py --selftest ✅ R2–R17 grün
python3 scripts/textverstaendnis_guard.py --json     0 R17-Funde
python3 scripts/keyword_optimizer.py --selftest      ✅
python3 scripts/live_policy_guard.py                 L2/L3 konsistent
python3 scripts/governance_contract.py               C21 grün
python3 scripts/check_length.py                      38 Artikel, 0 zu kurz / 0 zu lang
```

Offene Punkte dieser Umgebung (nicht Teil des Befunds): `PyYAML`, `hugo` und
`pytest` sind im Sandbox-Container nicht installiert, daher melden C6/C19
Werkzeug-Fehler. In der CI laufen diese Prüfungen unverändert.

---

## 7. Warum das dauerhaft ist

1. **Die Fehlerquelle ist weg**, nicht übertüncht: keine Kleinschreibung, keine
   Themen-Sonderfälle, nur eine grammatisch neutrale Schablone.
2. **Der Vertrag hält sie weg**: C21 schlägt an, sobald jemand `.lower()` oder
   eine flektierende Schablone zurückbringt.
3. **Die Wache sieht den Rückfall**: R17 findet die Ruinen im Text, auch wenn
   sie aus einer ganz anderen Quelle stammen.
4. **Das Tor lässt sie nicht live**: `publish_gate` blockiert beide R17-Codes
   hart, zusätzlich zur Flesch-Untergrenze für neue Artikel.
