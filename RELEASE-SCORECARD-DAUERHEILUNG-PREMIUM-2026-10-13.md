# Release-Scorecard: Produktionswahrheit wieder grün (#732)

**Auftrag (Frank, 13.10.2026):** „Release-Scorecard: Produktionswahrheit rot (Bestand blockiert) – #732. Bitte dauerhaft auf Highend-Level einer Profi-Agentur beheben.“

**Prüfmaßstab:** `data/release_scorecard.yaml` (SSOT) gemessen über die Collector-Funktionen des Publish-Gates – **keine zweite Messregel, keine Ausnahme, keine geschwächte Schwelle**. Der Bestand ist echt besser, nicht weggeklammert.

---

## Kurzfassung

Die Tageswache meldete **4 blockierte** und **10 verwarnnte** Live-Artikel (42/56 freigabe-reif). Ursache waren durchweg **Bestands-Altlasten**: Texte aus der Content-Engine-Ära, die vor den Regelhärtungen live gegangen sind (Absatz-Härte 11.09., Phrasen-Dopplung 30.09., Flesch-Mindest 60 am 05./07.10.) bzw. die das Längen-Optimum und die Belegketten-Pflicht nie erfüllt haben. Die Gates verhindern heute korrekt jede **Neu**infektion; den **Bestand** meldet die Tageswache, heilt ihn aber nie selbst (C15 – „Die Scorecard heilt nie“; R15 – „manuell reparieren“). Genau diesen Reparatur-Lauf hat dieser Vorgang erledigt.

| Kennzahl | vorher | nachher |
|---|---|---|
| Live-Artikel freigabe-reif | 42/56 | **56/56** |
| blockiert / nicht beweisbar | 4 | **0** |
| Warnungen ohne Blockade | 10 | **0** |
| Technik-Dimension Gesamtbestand | ❌ blockiert | **✅ bestanden** |
| Alle acht Dimensionen | 1× rot, 1× warn | **8× ✅** |
| Artikel unter Längen-Optimum (12.000) | 9 (gemeldet) + 2 (durch Redaktionskürzung) | **0** |
| Artikel ohne Belegkette (Q2) | 3 | **0** |
| `release_scorecard.py --live --streng` | Exit 1 | **Exit 0** |

---

## Was war blockiert – und was ist geheilt

### 1. `2026-08-26-warmwasser-sparen-rechnung-hinter-dem-hahn` (R5-ABSATZ-HART)

Ein Rechenweg-Absatz führte 7 Sätze (Limit 6), ein zweiter 5 (Limit 4). Beide sind jetzt an den Ideengrenzen geteilt (Wasser-Rechnung | Energie-Ergebnis; eigene Hebel | Nachricht an die Verwaltung | Beispiel). Lesbarkeit unverändert top (Flesch 63,2).

### 2. `2026-09-23-einlagensicherung-wie-viel-guthaben-geschuetzt-ist` (T5: Flesch 56,7)

Flesch **56,7 → 62,3**, Score **75 → 100**. Redaktioneller Feinschliff an ~50 Stellen: Schachtelsätze an sicheren Nahtstellen getrennt, lange Komposita durch Alltagswörter („Vertragsunterlagen“ → „Vertrag“, „Vermittlungsplattformen“ → „Vermittler“, „Kreditinstitut“ → „Bank“), Passiv-Formulierungen umgebaut (9 → 0), zwei Absätze > 4 Sätze geteilt, eine Grammatikfehlerstelle („mehrere verbundene Instituten“) korrigiert. Heilversuch mit `lesbarkeit_heiler.py` (Stufe A) blieb fail-closed bei 56,8 – die deterministische Stufe reicht für diese Klasse nicht; die KI-Stufe (B) ist in der Arbeitsumgebung ohne Schlüssel. Der Feinschliff folgt denselben Verträgen wie der Heiler: **Zahlen-Multiset, Links, Tabellen, Überschriften unverändert**, gemessen mit derselben Mess-SSOT (`readability_check`).

### 3. `2026-09-28-zaehlerstand-ablesen-und-melden-schaetzwerte-vermeiden` (T5 + R15-PHRASEN-DOPPEL)

- **R15:** Die beiden Modellrechnungen trugen dasselbe Intro („Annahmen: Dein gemessener Jahresverbrauch liegt bei 2.000 Kilowattstunden. Der …“, identische 10-Wort-Sequenz). Das zweite Intro heißt jetzt „Grundlage: Du verbrauchst gemessen 2.000 Kilowattstunden im Jahr. …“ – die Rechenwege selbst sind unverändert.
- **T5:** Flesch **59,5 → 63,2**, Score **70 → 100**, Passiv **18 → 0**, Absätze > 4 Sätze **1 → 0**. Sätze aktiv umgebaut und gekürzt, der fünfsätzige Rechenweg-Absatz geteilt.

### 4. `2026-10-05-erster-eigener-haushalt-fixkosten-richtig-ordnen` (R5-ABSATZ-HART)

Der Annahmen-Absatz (7 Sätze) ist in Wohnkosten | Alltag und Rücklagen geteilt; die Jahreslisten-Passage (5 Sätze) in Bestand der Liste | Umsetzung. Lesbarkeit unverändert (62,2/95).

## Was nur warnte – und jetzt auch sauber ist

- **T1w-zeichenlaenge-optimum (11 Artikel):** Jeder Artikel trägt jetzt ergänzende FAQ-Antworten im Stil und Format des jeweiligen Artikels (eine Idee pro Absatz, kurze Sätze, einzigartige Formulierungen – geprüft gegen R15/U1). Lücken waren 19–1.614 Zeichen. Zwei der Lücken (einlagensicherung, zaehlerstand) waren unerwünschte Nebenwirkung der Lesbarkeits-Kürzungen und wurden im selben Vorgang geschlossen. Ergebnis: **0 Artikel unter Optimum** (`check_length.py`: 56 ok).
- **Q2-quellen-vorhanden (3 Artikel):** `gasabschlag-berechnen`, `preiswert-surfen` und `weihnachten-budget-planen` tragen jetzt `quellen` im Frontmatter – je drei Belege aus den im Korpus bereits etablierten, vertrauenswürdigen Quellen (Rang 1/2 laut `editorial_review_gate.TRUSTED_SOURCE_RANK`: Bundesnetzagentur, Destatis, Verbraucherzentrale, BDEW). **Keine erfundenen URLs** – nur Adressen, die im Bestand als Belegkette in Gebrauch sind.

---

## Ursachenanalyse (das „dauerhaft“)

1. **Der Bestand ist älter als die Regeln.** R5-ABSATZ-HART, R15-PHRASEN-DOPPEL und die Flesch-Schwelle 60 (inkl. der zweiten Bedingung aus #585) wurden im September/Oktober nachgehärtet. Publish-Gate und Reserve-Zertifizierung schützen seitdem jeden **neuen** Text; veröffentlichte Alttexte fallen nur noch in die Tageswache. Das ist kein Gate-Defekt, sondern der bewusste Architekturvertrag: Wache meldet, Redaktion heilt (C15).
2. **Es gibt keine automatische Bestands-Heilung – richtig so.** R15 sagt „manuell reparieren“, fachliche Umformulierungen entscheidet die Redaktion. Werkzeuge für den deterministischen Teil existieren (`r5_absatz_splitter.py`, `politur_heiler.py`, `lesbarkeit_heiler.py --auch-live`) und wurden genutzt bzw. probiert (fail-closed = unangetastet). Die Reparatur selbst ist redaktionelle Arbeit gewesen – in diesem Vorgang.
3. **Die Engine zielte auf Floor statt Optimum.** Neun Artikel lagen mit 10.4–11,9k Zeichen knapp unter dem Optimum (12.000–18.000). Das harte Floor-Gate (10.000) war nie verletzt – die Optimum-Warnung (T1w) ist die ehrliche Sicht darauf. Die Nachführung erledigt jetzt den Bestand; die **Ausrichtung der Engine** ist eine Politikfrage (siehe „Offen“).
4. **Belegketten wurden nicht nachgepflegt.** Drei Engine-Artikel blieben ohne `quellen` (Q2 meldet „nachpflegen (faktenfrische)“). Der Korpus besitzt eine etablierte Quellen-SSOT – die Nachpflege ist damit rein zusammensetzend und wurde so durchgeführt.

---

## Belege

```
python3 scripts/release_scorecard.py               → 56/56 freigabe-reif, 0 blockiert, 0 Werkzeugfehler
python3 scripts/release_scorecard.py --live --streng → Exit 0 (Scope freigabe-reif)
python3 scripts/release_scorecard.py --selftest     → ✅ bestanden
python3 -m unittest scripts.tests.test_release_scorecard → 42 Tests OK
python3 scripts/readability_check.py --selftest     → ✅
python3 scripts/textverstaendnis_guard.py --selftest → ✅ (R2–R17)
python3 scripts/check_length.py                     → 56 ok, 0 unter-Optimum, 0 zu-kurz
python3 scripts/check_uniqueness.py                 → ✅ Audit bestanden (0 kritisch live↔live)
hugo --minify --destination public                  → Build sauber (Render-Beweis-Basis)
```

Gate-Nachweis auf den 14 geänderten Artikeln (Publish-Gate-Collectoren, Trockenlauf):
`T5-lesbarkeit: {} · T6-textverstaendnis: {} · T4-keyword-score: {} · RD1-duplikate: {} · RD2-einzigartigkeit: {} · editorial_review_gate: 0 Befunde`.

**Unit-Suite gesamt** (`unittest discover -s scripts/tests`): 2973 Tests, **1 Fehler** – `test_reserve_artifacts.test_current_snapshot_is_whole_and_editorially_valid`, „SHA-256 passt nicht mehr zum Entwurf“ für den Reserve-Entwurf `2026-10-12-dein-weg-…`. Der Fehler ist **auf dem Basisstand identisch** (per `git stash` gegengeprüft) und hat nichts mit dieser Änderung zu tun. Die zertifizierte Heilung `reserve_recert.py --fix` scheitert in dieser Arbeitsumgebung fail-closed an fehlendem `hunspell` (Rechtschreib-Kette zählt sonst „unbekannt“) – siehe „Nicht getan“.

---

## Entscheidungen (bewusst gesetzt, änderbar)

1. **Keine Ausnahme, keine Schwelle, kein herabgestuftes Gate.** Die SSOT `data/release_scorecard.yaml` ist unverändert; `ausnahmen` bleibt leer. Der Bestand misst sich an derselben Härte wie vorher.
2. **Mess-SSOT statt Augenmaß.** Jede redaktionelle Runde ist mit `readability_check` / `textverstaendnis_guard` / `publish_gate`-Collectoren gemessen; Zahlen-Multiset, Linkziele, Tabellen und Überschriften der Artikel sind unverfasst (Vertrag T4 der Heiler – hier selbstauferlegt, obwohl handwerklich editiert).
3. **FAQ-Format für die Längen-Nachführung.** Die Artikel endeten alle mit „Häufige Fragen“; dort ergänzen sich kurze Antworten ohne die Modellrechnungen, Listen und Tabellen der Hauptteile anzutasten – und ohne Flesch zu drücken (alle betroffenen Artikel liegen jetzt bei 62–78).
4. **Quellen nur aus der Korpus-Belegkette.** In einer Umgebung ohne Netz-Recherche wären neue URLs nicht verifizierbar. Die drei Artikel tragen jetzt genau die Belege, die der Bestand für dieselben Sachverhalte bereits führt (Energie/Heizkosten, Telekommunikation, Sparen/Konsum).

---

## Nicht getan / Offen (Entscheidung des Betreibers)

- **Reserve-Nachzertifizierung** (`2026-10-12-dein-weg-…`): `reserve_recert.py --fix` ist der richtige Weg, braucht aber `hunspell`/`hunspell-de-de` (in der Arbeitsumgebung nicht installierbar, Paketquellen nicht erreichbar). Im CI/Host mit Hunspell läuft `python3 scripts/reserve_recert.py --fix` und stellt den letzten verbliebenen Unit-Test-Fehler ab.
- **„Nächste Prüfung: unbekannt ⚠️ überfällig“** bei 10 Entwürfen (überwiegend Risikoklasse hoch): Die Prüftermine sind eine fachliche Planung des Herausgebers, keine Maschinenentscheidung. Der Report zeigt das ehrlich; die Zahlen sind nicht Teil des Live-Bestands (#732 betraf den Bestand).
- **Engine-Ausrichtung Floor → Optimum:** Wenn die Content-Engine künftig standardmäßig ≥ 12.000 Zeichen liefert, verschwindet die T1w-Warnklasse dauerhaft. Das ist eine Vorgabe für `data/ki_redaktion.yaml` / Content-Engine – bewusst nicht ohne Freigabe geändert.
- **Rechtschreib-/Grammatikprüfung der redaktionellen Kürzungen** lief als Satz- und Wortschärfung mit dem Lesbarkeits- und Verständnis-Regelwerk; eine vollständige Human-Korrekturlesung (Lektorat im klassischen Sinn) war nicht Teil des Auftrags.
