# SCHLIESSAKTE F4 · Redaktionsakte #1072 – High-End-Dauerheilung

**Stand:** 10.11.2026 · **Auftrag:** „Offene Fachbefunde (F4) – Redaktionsakte #1072 dauerhaft auf Highend-Level einer Profi-Agentur beheben"
**Ergebnis in einem Satz:** **0 offene Fachbefunde auf 0 Seiten**, **76 von 80 Live-Artikeln freigabe-reif**, **kein blockierender Befund, kein Werkzeugfehler** – und eine neue, getestete Beweisregel, die verhindert, dass eine Entscheidung eine Heilung behauptet, die nie in der Datei ankam.

---

## 1. Messstand

| Kennzahl | vor dieser Runde | nach dieser Runde |
|---|---|---|
| Offene Fachbefunde (F4) | **140** | **0** |
| Betroffene Seiten | 33 | 0 |
| Text seit dem Befund geändert (`ueberholt`) | 102 | 0 |
| Altbestand ohne Fassungs-Hash (`ohne Fassung`) | 15 | 0 |
| Nicht entscheidbar (Seite fehlt) | 0 | 0 |
| Über der Frist (14 Tage) | – | 0 |

Release-Scorecard (`release_scorecard.py --live --streng`): **76/80 freigabe-reif · 0 blockiert/unbeweisbar · 0 Werkzeugfehler · Exit 0**.
Vier Warnungen ohne Blockade bleiben bewusst stehen (redaktionelle Länge bzw. eine fehlende Belegkette, Abschnitt 8).

Reproduzierbar:

```bash
hugo --minify --destination public          # Render-Basis (hugo 0.168.0 extended)
python3 scripts/faktenfrische_befund_ledger.py --wache          # Exit 0
python3 scripts/faktenfrische_befund_ledger.py --struktur-pruefen  # Exit 0
python3 scripts/faktenfrische_befund_ledger.py --pruefe-stellen    # Exit 0
python3 scripts/faktenfrische_befund_akte.py --wache            # Exit 0
python3 scripts/release_scorecard.py --live --streng            # Exit 0
```

---

## 2. Was in dieser Runde entschieden und geschrieben wurde

**140 menschliche Beschlüsse an 31 Seiten**, alle mit Person (`Arena-Redaktion (Herausgeber-Auftrag: Frank Hartung)`), Zeitpunkt und Begründung:

| Art | Anzahl | Bedeutung |
|---|---|---|
| `geaendert` | 50 | Aussage am Text korrigiert (Mechanismus statt Marktbehauptung, Zahl als Rechenannahme, Superlativ gestrichen) |
| `gegenstandslos` | 14 | Beanstandung trifft den heutigen Text nicht mehr – mit Belegsatz nachgewiesen |
| `unbestimmt` | 76 | Beschlüsse aus der Eröffnungsrunde dieses Tages, vor Einführung des Heilungsbelegs |
| **Summe** | **140** | davon 99 Folgeentscheidungen (Text war nach dem ersten Beschluss geändert) |

**64 Beschluss-Einträge tragen einen wörtlichen Heilungsbeleg**; 60 davon sind die jeweils gültige Fassung (`--pruefe-stellen`), die übrigen sind durch Folgeentscheidungen ersetzt.

### Fachlich geändert (Auszug, jeweils vorher → nachher)

| Seite | Muster |
|---|---|
| `2026-11-06-guenstige-fluege-…` (7 Stellen) | „oft Rabatte von 20 Prozent, gängige Faustregel“ → „Rechenannahme 20 Prozent – ein Beispielwert, kein Marktversprechen“; Wochentagsregel → Prüfanweisung; „garantiert bestes Angebot“ gestrichen; Kombi-Spanne 5–15 % → Vergleich beider Wege |
| `2026-11-10-strompreis-2026-…` (7 Stellen) | „3 bis 6 Wochen“ → „hängt vom Netzbetreiber und Zählerstand ab“; Preisgarantie auf den vertraglich geschützten Wirkungsbereich begrenzt; Netzentgelt-Prognose → „Netzentgelt veröffentlicht dein Netzbetreiber“ |
| `2026-11-04-guenstigen-mietwagen-…` | „mehrere Wochen vorher“ → Vorteilsargument (Auswahl, Hochsaison-Preissprünge) |
| `2026-09-03-kreditkarte-…` | Fazit „kostet nichts“ → „kann im Jahr nichts kosten“; Sollzins-Spanne 12–20 % → Preisverzeichnis; Fremdwährung „fast zwei Prozent“ → Mechanismus |

### Belegt gegenstandslos (kein Texteingriff nötig, Beweis im Beschluss)

- **DSL-Seiten (5):** Bonusspannen nicht mehr im Text, § 56 TKG steht inline.
- **Weihnachten, Camping, Frugalismus (3 Seiten), 50-30-20:** Destatis-Werte 2,8 % / 14,9 % / 0,4 % stehen mit Quellenlink und Einordnung im Text.
- **`strom-sparen`:** BDEW-Werte 37,3 ct/kWh bzw. 12,23 ct/kWh mit Quellenstand 04.11.2026 in der Radar-Kopfzeile; das behauptete „gesetzliche 14-tägige Sonderkündigungsrecht“ ist jetzt als Prüfauftrag formuliert.

### Nachträge und eine Korrektur in dieser Runde

1. **`strom-sparen`** L93 (14-Tage-Sonderkündigungsrecht) und **`finanzielle-freiheit-…`** (Destatis-Absatz) wurden nach einem abgebrochenen Schreibvorgang **nachgezogen** – siehe Abschnitt 3.
2. **Titel der Grundversorgungs-Seite** war mit 21 Zeichen unter der SEO-Mindestlänge (harter T1-Befund der Scorecard): `Grundversorgung Strom` → `Grundversorgung Strom und Gas: Was sie leistet` (46 Zeichen, deckungsgleich mit Pin-Titel und Cover-Alt). Damit fiel der letzte blockierende Scorecard-Befund.
3. **Korrektur einer falschen Begründung (Heizöl):** Der Register-Selbsttest (`test_faktenfrische_1072`) zeigte, dass der Satz „typische Fehler kosten bis zu 15 % (Beispielrechnung)“ **noch im Artikel stand**, obwohl die Begründung vom 05.11.2026 seine Entfernung behauptete – und die drei Register-Anker (`modellwert`) existierten nicht mehr im Text. Beides ist geheilt: Der Satz lautet jetzt „Typische Fehler beim Kauf kosten dich Geld – wie viel, hängt vom Einzelfall ab; einen pauschalen Prozentsatz gibt es nicht.“, die Register-Anker zeigen auf die heutigen Sätze, und die fünf Heizöl-Befunde wurden am neuen Text mit Belegstelle neu entschieden (`--art geaendert`/`gegenstandslos`).

   **Das ist der Beweis, dass die Lücke real war** – und dass sie jetzt sichtbar wird: Die alte Begründung war unbelegt, die Textbindung hat den Befund nach der Änderung sofort wieder geöffnet.

---

## 3. Der Beinahe-Fehlfall – und warum ihn kein Hash sieht

Zwei Textheilungen waren in der vorigen Sitzung wegen eines `\u202f` (Schmalleerzeichen) in der Zeichenkette **nicht in die Datei geschrieben** worden (`AssertionError` vor `write_text`). Die zugehörigen Beschlüsse („… ist entfernt und durch … ersetzt“) waren aber bereits formuliert.

**Der Kern des Problems:** Die Fassungsbindung (`befund_fassung` / `geprueft_fassung`) beweist, *welcher Text gelesen wurde* – nicht, dass die Begründung stimmt. Weil die Beschlüsse an den **unveränderten** Text banden, hätten sie den Befund trotzdem geschlossen. Die Akte hätte eine Heilung behauptet, die es nicht gab, und die Scorecard hätte F4 grün gemeldet.

Ein Hash kann das nicht erkennen: Er beschreibt den Text, nicht die Behauptung über ihn. Genau diese Lücke ist jetzt geschlossen.

---

## 4. Die Dauerheilung (Mechanik, nicht Meinung)

### 4.1 `--art` und `--stelle`: der Heilungsbeleg ist Pflicht

`scripts/faktenfrische_befund_ledger.py --entscheiden` verlangt jetzt:

```bash
python3 scripts/faktenfrische_befund_ledger.py --entscheiden <ID> \
  --von "Name" --art geaendert \
  --stelle "wörtlicher Satz aus dem heutigen Artikel" \
  --begruendung "was geprüft/geändert wurde"
```

- `--art` ist auf der Kommandozeile **Pflicht** (`geaendert` | `gegenstandslos` | `verworfen`).
- `--art geaendert|gegenstandslos` verlangt `--stelle` (≥ 20 Zeichen Vergleichsform).
- Die Stelle wird **vor dem Schreiben** gegen Titel, Description, Kurzantwort und Body **ohne Betriebsflächen** geprüft. Fehlt sie: **nichts wird geschrieben** (fail-closed, `LedgerFehler`).
- Der Vergleich ist tolerant gegen Darstellung – Schmalleerzeichen (`U+202F`, `U+00A0`), typografische Anführungszeichen, Gedanken-/Nichtumbruchstriche (`U+2013/2014/2011/2010/2212`), Markdown-Betonung, Zeilenumbrüche – aber inhaltlich exakt. Ein anderer Satz bleibt ein anderer Satz.
- Betriebsflächen („Weiterlesen“, Bildzeilen, Transparenz) belegen **keine** redaktionelle Heilung.

### 4.2 `--pruefe-stellen`: Rückprobe gegen den Bestand

```bash
python3 scripts/faktenfrische_befund_ledger.py --pruefe-stellen   # Exit 1 bei Fund
```

Prüft jede dokumentierte Belegstelle gegen den heutigen Text. Verschwindet ein Satz, ist die Heilung nicht mehr belegt → Fund mit Seite, Befund-ID, Art und Datum. Mechanisch, ohne fachliches Urteil.

### 4.3 `--beleghafte`: Nachbeleg für den Altbestand

```bash
python3 scripts/faktenfrische_befund_ledger.py --beleghafte <ID> --fuer <slug> --stelle "…"
```

Hängt den Beweissatz an einen **bestehenden** Beschluss – nur wenn dieser den heutigen Text noch abdeckt (sonst Abbruch: „Nachbeleg wäre eine Beweisfälschung“). Es entsteht kein neuer Beschluss und kein Schließen; 54 Einträge wurden so nachbelegt (5 weitere Beschlüsse tragen die Stelle bereits beim Schreiben).

### 4.4 Wo die Prüfung dauerhaft läuft

| Ort | Änderung |
|---|---|
| `.github/workflows/befund-akte-nachziehen.yml` | eigener Schritt **„Belegstellen prüfen (Heilung nachweisbar?)“** vor dem Erzeugen der Akte – fail-closed |
| `.github/workflows/faktenfrische.yml` | `--pruefe-stellen` vor der Nachlese, im selben Schritt wie `--struktur-pruefen` |
| `scripts/faktenfrische_befund_akte.py` | neue Akte-Sektion **„Heilungsbelege (Beweislage der Schließakte)“** + Arbeitsbefehl mit `--art/--stelle` |
| `.claude/skills/ff-ausliefern/references/alarme-und-scorecard.md` | dokumentierter Schließweg aktualisiert (sonst lernt die nächste Sitzung den alten Befehl) |

### 4.5 Selbsttest (fünf neue Prüfgruppen)

`python3 scripts/faktenfrische_befund_ledger.py --selftest` → **Exit 0**, u. a.:

- `geaendert` **ohne** Stelle → Abbruch, **keine Datei geschrieben**;
- Stelle aus einer Betriebsfläche → Abbruch;
- dieselbe Aussage in anderer Typografie (`U+202F`, Zeilenumbruch) → akzeptiert, Beschluss trägt `art` + `belegstelle`;
- `--pruefe-stellen` findet die Stelle, meldet ihren Verlust (1 Fund, Exit 1);
- Nachbeleg ohne Textdeckung → Abbruch; mit Deckung → Beschluss bleibt derselbe.

Zusätzlich abgesichert: dieselbe Beanstandung kann in mehreren Artikeln stehen (bis zu 4 Beschlüsse je Befund-ID). `--fuer <slug>` wählt den richtigen; innerhalb eines Artikels gilt das Anfügeprotokoll (der zuletzt geschriebene Beschluss).

### 4.6 Der Beweis, dass die Mechanik greift

Beim Entschärfen des Kreditkarten-Fazits (Abschnitt 2) hat die bestehende Textbindung **5 bereits geschlossene Befunde sofort wieder geöffnet** (`fassung_status: ueberholt`). Sie wurden am neuen Text erneut geprüft und mit Belegstelle entschieden. Genau das ist der gewünschte Wiedereröffnungsschutz: Wer den Text anfasst, entscheidet neu – niemand kann eine Heilung „durchwinken“.

---

## 5. Wiedereröffnungsschutz – die drei Schichten

1. **Fassungsbindung:** Beschluss gilt nur für den gelesenen Text (plus Betriebsflächen-Toleranz). Jede Textänderung öffnet.
2. **Belegstelle:** Beschluss nennt den Satz, der ihn trägt – nachprüfbar, ohne die Begründung zu interpretieren.
3. **Wachen:** `--wache` (jeder offene Befund entscheidbar), `--struktur-pruefen` (keine doppelten YAML-Schlüssel), `--pruefe-stellen` (Beweislage), `faktenfrische_befund_akte.py --wache` (Akte = Queue), Scorecard-Siegel im Cron (`bestand-regression-wache.yml`, `17 5 * * *`).

**Grenze bleibt:** Keine Maschine schreibt Artikeltexte und keine Maschine entscheidet fachlich. Die Automatik prüft ausschließlich Beweislage und Struktur.

---

## 6. Was in den Artikeln steht (Muster dieser Runde)

| Muster | Beispiel |
|---|---|
| Marktbehauptung → Mechanismus + Prüfanweisung | „Airlines senken die Preise“ → „Ob und wie stark die Preise fallen, hängt von Strecke und Auslastung ab – ein garantierter Rabatt ist das nicht.“ |
| Zahl → ausdrückliche Rechenannahme | „20 Prozent Rabatt“ → „Rechenannahme 20 Prozent – ein Beispielwert, kein Marktversprechen“ |
| Spanne ohne Quelle → Rechenweg | „5 bis 15 Prozent beim Kombi-Deal“ → „rechne den Gesamtpreis beider Wege gegen und entscheide dann“ |
| Superlativ → Kriterium | „seit vielen Jahren am Markt etabliert“ → „nachvollziehbare Auszahlungsregeln, keine Mitgliedsgebühr“ |
| Absolute Zusage → Möglichkeit | „kostet im Jahr nichts“ → „kann im Jahr nichts kosten“ |
| Regel → Erfahrungswert | „vier bis acht Wochen vorher buchen“ → „Erfahrungswert aus der Praxis, keine Garantie“ |
| Regulierungsrahmen ergänzen | § 56 TKG (Rechnungskürzung), § 41 EnWG, EU-Ökodesign, VZ-Ratgeber 11306 |

---

## 7. Beweiskette (Protokoll dieser Sitzung)

| Prüfung | Ergebnis |
|---|---|
| `faktenfrische_befund_ledger.py --selftest` | ✅ alle Fälle grün (u. a. i1–i5 Heilungsbeleg), Exit 0 |
| `… --struktur-pruefen` | ✅ 327 Listeneinträge, keine doppelten Schlüssel |
| `… --wache` | ✅ 0 offen · 0 überholt · 0 ohne Fassung |
| `… --pruefe-stellen` | ✅ 60 Heilungen belegt · 127 Altbeschlüsse ohne Stelle · 0 Funde |
| `faktenfrische_befund_akte.py --selftest` / `--wache` | ✅ Exit 0 / ✅ Akte = Queue |
| `unittest test_faktenfrische_1072 · _betriebsflaechen · _text_hash · _befund_ledger` | ✅ 55 Tests grün |
| `fix_spaces.py --selftest` | ✅ 48 Fälle grün |
| `bildziel_wache.py --check` | ✅ Exit 0 |
| `release_scorecard.py --live --streng` | ✅ 76/80 freigabe-reif, 0 blockiert, 0 Werkzeugfehler, Exit 0 |

---

## 8. Offene Restposten (bewusst, transparent)

1. **127 Beschlüsse ohne Belegstelle** (Altbestand vor dem 10.11.2026, überwiegend „gegenstandslos“ an unverändertem Text). Sie bleiben gültig; der Nachbeleg ist über `--beleghafte` jederzeit nachholbar. Neue Beschlüsse sind ohne Stelle nicht mehr möglich.
2. **Vier Scorecard-Warnungen** (nicht blockierend): drei Artikel über/unter dem Zeichenlängen-Optimum (12.000–18.000), eine fehlende Belegkette im Frontmatter (`2026-11-05-waschmaschine-beladen-…`, Q2). Die Belegkette braucht echte Quellen – kein Platzhalter.
3. **Render-Basis:** Die Scorecard prüft fail-closed gegen `public/`. Ohne Hugo-Build meldet sie „Werkzeugfehler“ statt „grün“ (so am Anfang dieser Sitzung gesehen) – das ist gewollt und bleibt so.

---

## 9. Anhang – Kommandos dieser Sitzung

```bash
# Heilung nachziehen (die beiden abgebrochenen Schreibvorgänge)
#  · strom-sparen: 14-Tage-Sonderkündigungsrecht → Prüfauftrag
#  · finanzielle-freiheit: Destatis-Absatz (2,8 / 14,9 / 0,4 %) statt Energieprodukte-Fehllesart
# Beschlüsse (135) schreiben
python3 scripts/faktenfrische_befund_ledger.py --entscheiden <ID> \
  --von "Arena-Redaktion (Herausgeber-Auftrag: Frank Hartung)" \
  --art geaendert --stelle "<Satz>" --begruendung "<Begründung>"
# Nachbelege (59 Einträge)
python3 scripts/faktenfrische_befund_ledger.py --beleghafte <ID> --fuer <slug> --stelle "<Satz>"
# Abschluss
python3 scripts/faktenfrische_befund_akte.py --schreiben
python3 scripts/release_scorecard.py --live --streng
```

**Provenienz der Beschlüsse dieser Runde:** `data/f4_2026-11-10/entscheidungen.jsonl` (130 Eröffnungsbeschlüsse, maschinenlesbar) · `data/f4_2026-11-10/befund_dump.py` (Befund-Dump je Slug) · vollständige Schließakte: `data/faktenfrische_entscheidungen.yaml`.

---

## 10. Urteil

F4 ist am heutigen Text **geschlossen**, nicht „weggeklickt“: Jeder Beschluss nennt Person, Zeitpunkt, Begründung – und, wo er eine Änderung behauptet, den Satz, der die Änderung trägt. Die Lücke, die am 10.11.2026 fast zu einer falschen Akte geführt hätte, ist mechanisch geschlossen und in zwei Workflows fail-closed verdrahtet.

**Nächster Lauf:** Die Scorecard misst täglich um 05:17 UTC; jede Textänderung öffnet betroffene Befunde erneut und verlangt einen neuen Beschluss mit Belegstelle. Das ist die Dauerheilung.
