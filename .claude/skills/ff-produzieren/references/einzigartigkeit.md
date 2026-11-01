# Einzigartigkeit – Gate und Audit mit derselben Messung

> Wörtlich aus `CLAUDE.md` übernommen am 01.11.2026 (Skill-Umbau). Kein Satz wurde umformuliert, gekürzt oder erfunden; die Überschriften sind eine Ebene tiefer gehängt. Änderungen hier sind Änderungen am Regelwerk – sie brauchen denselben Nachweis wie vorher: Selbsttest der betroffenen Wache, dann Commit.

### Das Gate misst, was das Audit misst (Phrasen-Einzigartigkeit, seit #714, 12.10.2026)

Am 12.10.2026 gingen um 06:02 UTC zwei Reserve-Artikel live – „DSL-Anbieter
wechseln" und „Handyvertrag kündigen" –, beide durch `quality_score` und
`publish_gate --strict`. Um 13:35 UTC meldete das tägliche Einzigartigkeits-
Audit dasselbe Paar als **kritisch**: 14 gleiche Sieben-Wort-Phrasen aus einem
geteilten § 56-TKG-Absatz, dazu einen Titel-Zwilling („…: Kosten und Fristen
richtig prüfen" ↔ „…: Frist und Kosten richtig prüfen"). Das Gate war nicht
zu lasch – **es kannte die Messung nicht**: `duplikat_guard` (D3/D4) vergleicht
ganze Absätze mit Ratio ≥ 0,85, und ein Absatz, der „DSL-Vertrag" gegen
„Handyvertrag" tauscht, liegt darunter; `quality_score` gewichtet eine
kritische Überlappung mit −0,01. Bestandswache und Gate hatten zwei
Wahrheiten, und die strengere kam erst nach dem Deploy zu Wort – dieselbe
Bauart wie #583 (Faktenfrische) und #674 (Duplikate).

- **Eine Messregel.** `check_uniqueness.kandidaten_befunde()` ist der
  Collector für Publish-Gate (`uniqueness_failures`, U1 = ≥ 5 gleiche
  7-Wort-Phrasen mit einem auslieferbaren Artikel oder Mit-Kandidaten,
  U2 = Titel-Zwilling am selben Slug-Tag), Release-Scorecard
  (`RD2-einzigartigkeit`, `wirkung: blockiert`) und Tagesaudit. Ein
  Bestandsbefund kann damit nie erst nach einem grünen Gate auftauchen.
- **Entwürfe sind keine Gegenseite.** Ein `draft: true` im Vorrat kann nichts
  kannibalisieren; der zweite Zwilling fällt, sobald der erste live ist.
  Zwischen zwei Kandidaten trägt bei U2 nur der jüngere den Befund (der
  ältere ist kanonisch – dieselbe Regel wie `heal_twin`).
- **Kein Heiler, bewusst.** Welche Passage neu formuliert wird und ob die
  Rechtsangabe dabei stimmt, ist Redaktionsarbeit mit Quellenpflicht
  (`reserve_healer_coverage.AUSNAHMEN`). Der Kandidat bleibt als Hold erhalten.
- **Fail-closed.** Roter Selbsttest der Wache = Werkzeugfehler = Gate stoppt,
  nichts wird verworfen.
- **Redaktionsvokabeln sind keine Themenwörter.** „richtig prüfen", „worauf
  es ankommt", „Schritt für Schritt" stehen jetzt in `STOP`; der Zwillings-
  Radar vergleicht Themen, nicht Schablonen (Selbsttest-Fälle 7+8).
- Tests: `python3 -m unittest scripts.tests.test_publish_gate_uniqueness`
  (16) · Bericht: `EINZIGARTIGKEIT-BESTAND-714-DAUERHEILUNG-PREMIUM-2026-10-12.md`.

### Ein Heiler darf keinen Massensatz schreiben (Einzigartigkeit, seit #766, 15.10.2026)

Am 15.10.2026 meldete das tägliche Einzigartigkeits-Audit **435 kritische
live↔live-Paare** – C(30,2). Die Ursache war nicht die Redaktion, sondern der
eigene Heiler: `redaktions_standard.fix_rs2_rs3_deterministic()` hatte 30
Artikeln ohne Faustregel **denselben** eingefrorenen Satz eingesetzt. Ein Satz,
der per Konstruktion überall passt, ist per Konstruktion überall derselbe – die
Regel war richtig, ihre Umsetzung erzeugte den Befund, den die Wache meldete.

- **Der Heiler wählt, er setzt nicht.** `FAUSTREGEL_POOL` (44 eigene Sätze,
  ohne Zahlen und ohne Behauptungen, paarweise unter der Audit-Schwelle) und
  `waehle_faustregel()`: Bestand (`faustregel_kontext()` – Belegung plus
  7-Gramm-Index aus `check_uniqueness.clean_body`, DIESELBE Messung wie das
  Audit), Schwelle, Themenbezug, stabiler Hash. Kein freier Satz → **nichts
  schreiben** und den Grund melden (fail-loud statt Massensatz).
  `faustregel_vorrat()` + `FAUSTREGEL_VORRAT_WARNUNG = 5` warnen, bevor der
  Vorrat endet; `_kontext_aktualisieren()` hält die Messung im Lauf aktuell,
  damit `--dry-run` und Echtlauf dasselbe planen.
- **Ausgeliefertes wird nicht neu vergeben.** `FAUSTREGEL_LEGACY` ist
  eingefroren und kommt nie zurück; `ersetze_generische_faustregel()` ersetzt
  den Altbestand idempotent und toleriert nur Typografie (Wortfolge exakt,
  Satzpunkt gehört ins Muster).
- **Haus-Formeln sind Format, kein Inhalt – in EINER Messung.** Der
  Haus-Formel-Strip sitzt in `template_boilerplate` (Quelle ist die SSOT
  `duplikat_guard.HAUS_TEXT_QUELLEN`, gelesen über `ssot_konstante()` ohne
  Produzenten-Import) und gilt damit für Audit, Publish-Gate und Scorecard
  gleich.
- **Die Ausnahme ist eng und wehrhaft.** Nur literale Sätze ab
  `HAUS_FORMEL_MIN_LAENGE = 40` Zeichen; Platzhalter werden getrennt (Daten
  bleiben gemessen); eingeschobene eigene Wörter heben die Ausnahme auf;
  unlesbare Quelle = Werkzeugbefund (fail-closed), lesbare Kurzquelle =
  Absicht, gar keine auswertbare Formel = blinde Ausnahme = Befund.
- **Keine Allow-List für Redaktionsschablonen.** Ein geteilter Tabellenkopf
  (Heizperiode ↔ DSL) wurde umformuliert, nicht freigestellt – eine Liste
  hätte jeden künftigen Kopf blind gemacht.
- Tests: `python3 -m unittest scripts.tests.test_redaktions_standard` (14) ·
  Selbsttests `redaktions_standard.py` (44 Fälle) · `template_boilerplate.py`
  (12) · `duplikat_guard.py` (14) · Bericht:
  `EINZIGARTIGKEIT-BESTAND-766-DAUERHEILUNG-PREMIUM-2026-10-15.md`.
