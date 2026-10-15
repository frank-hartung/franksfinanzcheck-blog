# 🧬 Einzigartigkeits-Audit #766: Der Heiler schreibt nie wieder einen Massensatz

**Datum:** 15.10.2026 · **Bezug:** Issue #766 „📋 Einzigartigkeits-Audit:
Bestandsüberlappungen gefunden" (Workflow-Lauf 38719422012, `blog-health-daily`)
· **Auftrag:** „Bitte dauerhaft auf Highend-Level einer Profi-Agentur beheben."
· **Vorgänger:** `EINZIGARTIGKEIT-BESTAND-714-DAUERHEILUNG-PREMIUM-2026-10-12.md`
(#714), `EINZIGARTIGKEIT-BESTAND-PREMIUM-2026-10-01.md` (#490)

---

## 1. Befund

```
Ergebnis: Pin-Konflikte: 0 | Interne Überlappungen: 453
          | Kritisch (live↔live): 435 | Nicht-Live-Paare: 7
          | Same-Day-Twins: 0 (geheilt: 0)                     → Exit 1
```

**435 = C(30,2).** Die Zahl war keine Häufung von Zufällen, sondern ein
vollständiger Graph: 30 Live-Artikel trugen **denselben** Satz, also war jedes
Paar ein Befund. Und der Satz war nicht von der Redaktion – er war **vom
Repository selbst geschrieben**: `fix_rs2_rs3_deterministic()` setzte in jeden
Artikel ohne RS3 den einen eingefrorenen Heiler-Satz

> `**Faustregel:** Prüfe vor jeder Entscheidung zuerst die Gesamtkosten über die
> volle Laufzeit und vergleiche mindestens zwei aktuelle Angebote, bevor du dich
> festlegst.`

Der Heiler hatte den Bestand von „zu wenige Faustregeln" auf „dreihundertfünf-
unddreißig Duplikate" geheilt. Die Regel war richtig, ihre **Umsetzung** war der
Fehler: ein Satz, der per Konstruktion in jedem Artikel passen muss, ist per
Konstruktion in jedem Artikel derselbe.

## 2. Die zweite Ursache: Format als Inhalt gemessen

Die sieben Nicht-Live-Paare hatten eine andere Ursache – **keine** Redaktions-
dopplung, sondern Haus-Format:

| Paar(e) | Geteilt | Was es war |
|---|---|---|
| 3 News-Entwürfe (`markt-update`, `energie-update`, `saison-update`) → 6 Paare | 11/12/17 gleiche 7-Gramme | `news_writer.STAND_INTRO` – die News-Dateline („Dieser News-Kompakt-Artikel ordnet eine aktuelle Entwicklung ein. Konditionen und Regeln können sich ändern …") |
| `2026-10-02-preiswert-surfen…` ↔ `2026-10-14-heizperiode…` | 6 gleiche 7-Gramme | identische Überschrift **und** identischer Tabellenkopf („\| Fehler \| Warum er kostet \| Wie du ihn vermeidest \|") |

`duplikat_guard` nimmt Haus-Templates seit #676 von der Messung aus
(`HAUS_TEXT_QUELLEN`); das Einzigartigkeits-Audit maß sie weiter als Text. Das
ist **exakt die Bauart, die #714 geheilt hat**: zwei Messungen, zwei Wahrheiten
– und die strengere fällt später auf. Der Frontmatter-gleiche Teil der
News-Entwürfe (Titel, Dateline) ist austauschbar, ihr Inhalt nicht.

## 3. Dauerheilung (Code)

### 3.1 Der Heiler WÄHLT, statt zu setzen – `redaktions_standard.py`

- **`FAUSTREGEL_POOL` (44 Sätze):** eigene, themenbezogene Faustregeln – alle
  ohne Zahlen (RS5), ohne Aussagen (RS6), Themen und Sätze eindeutig, und
  **paarweise unter der Audit-Schwelle** (`KRITISCH_AB`). Der Pool kann den
  Befund nicht selbst erzeugen, den er heilt.
- **`faustregel_kontext` / `waehle_faustregel`:** gewählt wird deterministisch
  nach vier Regeln – (1) weder im Bestand noch im laufenden Lauf vergeben,
  (2) der Satz schiebt kein Artikelpaar über die Audit-Schwelle (dieselbe
  7-Gramm-Messung wie das Audit, auf `check_uniqueness.clean_body`), (3) höchster
  Themenbezug, (4) stabiler Hash über (Slug, Satz) als Gleichstand.
- **`_kontext_aktualisieren`:** die Bestandsmessung wird **während** des Laufs
  nachgezogen – ein `--dry-run` ist damit die ehrliche Vorschau auf den echten
  Lauf (gleiche Reihenfolge, gleiche Messung), kein zweites Verhalten.
- **`ersetze_generische_faustregel`:** ersetzt den eingefrorenen Alt-Satz
  einmalig; tolerantes Muster (Wortfolge exakt, Typografie frei), idempotent,
  und **der Satzpunkt gehört zum Muster** (im ersten Echtlauf stand
  „… dann den Tarif.." – gesehen, eingefroren, behoben). Ist kein freier Satz
  übrig, bleibt der Text **unverändert** und die Meldung nennt den Grund –
  lieber eine offene Faustregel als ein neuer Massensatz.
- **Vorrats-Warnung:** `faustregel_vorrat()` + `FAUSTREGEL_VORRAT_WARNUNG = 5`;
  der echte Lauf meldet, wenn der Vorrat zur Neige geht – Stillstand wird
  sichtbar, bevor er eintritt.
- **`--nur-faustregel`:** der RS3-Bestand lässt sich heilen, ohne RS2/RS7
  anzufassen.

**Bestandsheilung (einmalig, nachvollziehbar in
`data/redaktions_standard_history.jsonl`):** 33 Schritte = **30** Ersetzungen
des Alt-Satzes + **3** Artikel, die vorher gar keine Faustregel hatten. Kein
Artikel bekam den Satz eines anderen.

### 3.2 Das Audit misst Haus-Formeln nicht mehr als Inhalt

`template_boilerplate.py` (SSOT für Template-Abzüge) entfernt jetzt die
registrierten Haus-Formeln – verkettet in `strip_template_boilerplate`, damit
**eine** Messung für Audit (`check_uniqueness.clean_body`), `quality_score`
(Gewicht 0,1) und `requeue_quality_holds` gilt. Die Quelle ist die **SSOT von
`duplikat_guard`** (`HAUS_TEXT_QUELLEN`), gelesen über den neuen öffentlichen
`duplikat_guard.ssot_konstante(modul, attribut)` (AST-Zugriff, kein Import der
Produzenten → keine PyYAML-Kette im Audit).

**Die Ausnahme ist absichtlich eng (Freibrief-Schutz):**

- Entfernt wird nur ein **literaler** Satz ab `HAUS_FORMEL_MIN_LAENGE = 40`
  Zeichen. Kurze Fragmente („Stand:", CTA-Fragmente) bleiben stehen – sonst
  wäre jedes Datum, jeder Schnipsel eine Lizenz zum Duplizieren.
- Platzhalter (`{today}`) werden zu **getrennten Teilen**, nicht zu beliebigem
  Text: „**Stand: 12.10.2026**" bleibt mit seinem Datum in der Messung.
- Zwischen den Wörtern ist nur **Typografie** frei (Leerzeichen, geschützte
  Leerzeichen, Binde-/Gedankenstriche, Satzzeichen). Eingeschobene eigene Wörter
  heben die Ausnahme auf – der Satz wird dann wieder gemessen.
- Alles, was der Artikel **selbst** um die Formel herum schreibt, bleibt im
  Vergleich (Selbsttest-Gegenprobe).
- **Fail-loud:** `haus_formel_luecken()` meldet eine nicht lesbare Quelle als
  Werkzeugbefund (der Audit-Selbsttest scheitert dann, fail-closed). Eine
  lesbare, aber zu kurze Quelle ist **Absicht**, keine Lücke; erst wenn **gar
  keine** Formel mehr auswertbar ist, wäre die Ausnahme blind – und das ist
  wieder ein Befund.

### 3.3 Redaktion: die Heizperioden-Schablone

Der Entwurf `2026-10-14-heizperiode-vorbereiten-im-spaetsommer` teilte
Überschrift und Tabellenkopf wörtlich mit dem DSL-Ratgeber vom 02.10. Das
Fehlerkapitel trägt jetzt eine eigene Überschrift und einen eigenen Tabellenkopf
(„Denkfehler / Was er dich kostet / So vermeidest du ihn"); die Änderung ist im
`aenderungsgrund` des Prüfprotokolls vermerkt.

**Entscheidung gegen die Allow-List:** Ein geteilter Tabellenkopf ist **kein**
Haus-Template (kein Generator schreibt ihn) – er ist Redaktionsgewohnheit. Eine
Allow-List hätte jeden künftigen Tabellenkopf blind gemacht; die Umformulierung
heilt die Ursache und lässt die Messung scharf.

## 4. Was bewusst NICHT passiert ist

- **Keine Schwellenänderung, kein Stummschalten.** `KRITISCH_AB = 5` und die
  7-Gramm-Messung sind unverändert; die 13 verbleibenden internen
  Überlappungen bleiben sichtbar, die kritischen sind weg.
- **RS3 bleibt Pflicht.** Die Capital-Regel („mindestens eine markierte
  Faustregel") wurde nicht abgeschwächt – sie bekommt nur 44 Wahrheiten statt
  einer.
- **Kein YMYL-Siegel beschädigt.** Von den 34 geänderten Artikeln trägt
  **keiner** `inhalt_sha256`; die Prüfprotokolle stehen auf `status:
  "ausstehend"`, `automatic_write_protected()` ist für alle 34 `False`. Der
  Schreibvertrag war nicht berührt – es war nichts zu versiegeln und nichts
  neu zu siegeln.
- **Keine Editor-Ausnahme für die News-Dateline.** Sie wird über dieselbe
  SSOT-Regel entfernt wie CTA und Disclaimer – nicht als Sonderfall für vier
  Entwürfe.

## 5. Beweise

```
# vorher (Reproduktion des Issue-Befunds)
python3 scripts/check_uniqueness.py
  → Kritisch (live↔live): 435 | Nicht-Live-Paare: 7          Exit 1

# nachher
python3 scripts/check_uniqueness.py
  → Pin-Konflikte: 0 | Interne Überlappungen: 13 | Kritisch: 0
    | Nicht-Live-Paare: 0 | Same-Day-Twins: 0 · ✅ Audit bestanden   Exit 0
python3 scripts/check_uniqueness.py --selftest     # ✅ 8 Twin-Fälle + Slug-/Gram-Pinne
python3 scripts/redaktions_standard.py --selftest  # ✅ 44 eingefrorene Fälle
python3 scripts/template_boilerplate.py            # ✅ 12 Fälle (Haus-Formeln inklusive)
python3 scripts/duplikat_guard.py --selftest       # ✅ 14 Fälle (SSOT ohne Import-Kette)
python3 -m unittest scripts.tests.test_redaktions_standard    # 14 Tests OK
python3 -m unittest scripts.tests.test_check_uniqueness       # 11 Tests OK
python3 scripts/governance_contract.py             # 🔒 alle 36 Regeln erfüllt
python3 scripts/selftest_runner.py                 # 207 Wachen grün, 414 Uhr-Proben
python3 scripts/reserve_healer_coverage.py         # rc=0
python3 -m unittest discover -s scripts/tests       # 3198 Tests, 1 Fehler = FEST-Drift (s. u.)
```

**Alt-Satz-Bilanz (mit dem echten Muster gezählt):** HEAD 30 Artikel → Arbeits-
baum 0. **Geänderte Dateien:** 34 Artikel (+ `data/redaktions_standard_history.jsonl`
mit 33 Einträgen).

**FEST-Drift, im zweiten Commit mitgeheilt:** `scripts/redaktions_standard.py`
steht auf der FEST-Liste; der PR-Check „Integritäts-Siegel" wird rot, bis
`python3 scripts/integrity_guard.py --heal` im eigenen Commit `chore(integrity)`
läuft (Herkunft in `data/integrity_lock.json` + `data/integrity_history.jsonl`)
– derselbe Weg wie in #714. KRITISCH bleibt HARD STOP.

## 6. Dateien

- `scripts/redaktions_standard.py` – `FAUSTREGEL_POOL` (44), Wähler mit
  Bestandsmessung, Legacy-Ersetzer, `--nur-faustregel`, Vorrats-Warnung,
  44 eingefrorene Selbsttest-Fälle
- `scripts/template_boilerplate.py` – Haus-Formel-Strip, `haus_formel_luecken()`,
  12 Selbsttest-Fälle (Freibrief-Schutz, idempotent, Gegenprobe)
- `scripts/duplikat_guard.py` – öffentlicher SSOT-Leser `ssot_konstante()`
- `scripts/check_uniqueness.py` – Haus-Formeln raus aus `clean_body()`
- `scripts/tests/test_redaktions_standard.py` – 6 neue Vertragstests (14 gesamt)
- 33 Bestandsartikel (`content/posts/**/index.md`),
  `content/posts/2026-10-14-heizperiode…/index.md` (Schablone),
  `data/redaktions_standard_history.jsonl`
- `CLAUDE.md` (Dauervorgabe), dieser Bericht

Der Vorgang #766 wird vom nächsten sauberen Produktionslauf automatisch
kommentiert und geschlossen (`uniqueness_issue_sync.py`); der Pull Request
trägt `Closes #766` für den Abschlussvermerk.
