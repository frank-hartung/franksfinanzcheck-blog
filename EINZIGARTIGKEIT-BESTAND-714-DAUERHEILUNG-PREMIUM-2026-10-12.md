# 🧬 Einzigartigkeits-Audit #714: Das Gate misst jetzt, was das Audit misst

**Datum:** 12.10.2026 · **Bezug:** Issue #714 „📋 Einzigartigkeits-Audit:
Bestandsüberlappungen gefunden" (Workflow-Lauf 38256360241, `blog-health-daily`)
· **Auftrag:** „Bitte dauerhaft auf Highend-Level einer Profi-Agentur heben."
· **Vorgänger:** `EINZIGARTIGKEIT-BESTAND-PREMIUM-2026-10-01.md` (#490)

---

## 1. Befund

```
🚨 TWIN am 2026-10-07: …dsl-anbieter-wechseln… ↔ …handyvertrag-kuendigen…
   ('DSL-Anbieter wechseln: Kosten und Fristen ri' ↔ 'Handyvertrag kündigen: Frist und Kosten rich')
🚨 KRITISCH …dsl-anbieter-wechseln… ↔ …handyvertrag-kuendigen…: 14 gleiche 7-Wort-Phrasen
   · darf hoechstens 24 monate dauern 56 tkg
   · dein vertrag nach der ersten festen zeit
   · frag den anbieter schriftlich heb die antwort
Ergebnis: Kritisch (live↔live): 1 | Same-Day-Twins: 1 (geheilt: 0)
```

Zwei Artikel aus derselben „Editorial revision"-Charge der Reserve (zertifiziert
08.10., live 12.10. um 06:02/06:03 UTC) teilten den Absatz zur Vertragslaufzeit
nach § 56 TKG fast wörtlich – nur „DSL-Vertrag" gegen „Handyvertrag" getauscht –
und trugen Titel nach derselben Schablone („…: Kosten und Fristen richtig
prüfen" / „…: Frist und Kosten richtig prüfen"). Im Handy-Artikel standen
zusätzlich zwei Dichte-Sätze des Keyword-Heilers („Darum geht es hier konkret:
Handyvertrag kündigen.", „Genau das ist der Hebel: Handyvertrag kündigen.").

## 2. Die eigentliche Schwäche: zwei Wahrheiten

Beide Artikel hatten `quality_score ≥ 0,85` **und** `publish_gate --strict`
bestanden. Das Gate war nicht zu lasch – **es kannte die Messung nicht:**

| Instanz | Was sie misst | Warum sie den Fall nicht sah |
|---|---|---|
| `duplikat_guard` D3/D4 (RD1, blockiert) | ganze Absätze, difflib-Ratio ≥ 0,85, ≥ 150 Zeichen | Ein Absatz mit getauschtem Produktwort und einem angehängten Satz liegt unter 0,85 |
| `quality_score` → `uniqueness` | Paare mit ≥ 5 gleichen 7-Grammen | Gewicht 0,1 × Abzug 0,1 = **−0,01** Gesamtpunkte; ein Artikel mit 0,97 bleibt bei 0,96 |
| `check_uniqueness.py` (Tagesaudit) | 7-Gramme, ≥ 5 = kritisch, plus Titel-Zwilling | **Lief nicht am Kandidaten.** Nur täglich über den Bestand – sieben Stunden nach dem Deploy |

Das ist dieselbe Bauart, die dieses Repo schon in #583 (Faktenfrische) und #674
(Duplikate) gekostet hat: ein grüner Publish-Pfad, ein roter Nachlauf, ein
offenes Ticket ohne Besitzer. Die strengere Messung kam erst nach der
Veröffentlichung zu Wort.

Zweiter, kleinerer Befund: Der Titel-Zwillings-Radar maß **Redaktionsvokabeln**
als Thema. „kosten richtig pruefen" genügte für Jaccard 0,30 zwischen einem DSL-
und einem Mobilfunk-Artikel, die verschiedene Suchanfragen bedienen.

## 3. Dauerheilung (Code)

### 3.1 Eine Messregel – `check_uniqueness.kandidaten_befunde()`

Neuer Collector in der Wache selbst, auf Kandidaten zugeschnitten:

- **U1-PHRASEN:** Kandidat teilt ≥ `KRITISCH_AB` (5) Sieben-Wort-Phrasen mit
  einem **auslieferbaren** Artikel oder einem Mit-Kandidaten. Beide Seiten
  werden benannt (inkl. Beispielphrase); einen Eintrag erhalten nur Kandidaten.
- **U2-ZWILLING:** Kandidat ist Titel-Zwilling eines auslieferbaren Artikels
  desselben Slug-Tags. Zwischen zwei Kandidaten trägt nur der **jüngere** den
  Befund – der ältere ist kanonisch (dieselbe Regel wie `heal_twin`).
- **Entwürfe sind keine Gegenseite:** `draft: true`/Zukunft/abgelaufen
  (Hugo-Semantik aus `post_utils.build_state`) kann nichts kannibalisieren.
  Sonst blockierte sich die Reserve selbst; der zweite Zwilling fällt genau
  dann, wenn der erste live ist.
- **Selbsttest mit eingefrorenem Mini-Korpus** (fünf Fälle, inkl. der
  § 56-Konstellation) läuft in `run_selftest()` – vor jedem Audit, in jedem
  Gate-Aufruf, im Selbsttest-Runner (191 Wachen, auch unter +97/+1461 Tage
  vorgestellter Uhr grün).

### 3.2 Publish-Gate: Prüfung 10 – `publish_gate.uniqueness_failures()`

Schmaler, schreibfreier Adapter (wie `duplicate_failures`): liest den Collector,
behandelt einen roten Selbsttest als **Werkzeugfehler → Gate stoppt fail-closed,
nichts wird verworfen**. Ein Fund am Kandidaten:

- neuer Artikel (Slug = heute) → verworfen (Betriebsregel 13.08.2026),
- Re-Queue/Reserve-Post → `park_state.hold` mit Grund
  `publish-gate: Einzigartigkeits-Gate U1–U2 nicht bestanden …` – Text bleibt
  erhalten, Entscheidung ist redaktionell.

Damit greift die Messung automatisch überall, wo das Gate läuft: Engine,
Kadenz-Backstop, Deploy-Refill, **Reserve-Zertifizierung** (`accept_candidate`
→ STRICT dry-run) und Release-Isolation.

### 3.3 Release-Scorecard: `RD2-einzigartigkeit` (blockiert, Entscheidung human)

`data/release_scorecard.yaml` deklariert den Check; `PUBLISH_GATE_HART_FAMILIEN`
führt ihn (C19-Spiegel, ST2); `sammle()` misst über **denselben Adapter** –
keine eigene Schleife (Verbot seit #674). Blustradius bleibt der Artikel
(C34/`release_isolation`), nicht die Site.

### 3.4 Kein Heiler, bewusst – `reserve_healer_coverage.AUSNAHMEN`

Welche Passage neu formuliert wird und ob die Rechtsangabe dabei stimmt, ist
Redaktionsarbeit mit Quellenpflicht. Ein Heiler müsste § 56-Sätze umschreiben,
ohne sie zu prüfen (C15). Die Ausnahme ist begründet und getestet (C29).

### 3.5 Zwillings-Radar: Themen statt Schablonen

`STOP` kennt jetzt Redaktionsvokabeln (`richtig pruefen pruefst prueft
wirklich lohnt jetzt tipps tricks schritt worauf ankommt achten clever`).
Zwei neue eingefrorene Selbsttest-Fälle: die #714-Titel sind **kein** Zwilling,
„Stromfresser im Haushalt richtig prüfen" ↔ „Stromfresser finden: So prüfst du
deinen Haushalt" bleibt einer. Der Gas-Fall vom 11.08.2026 bleibt der Maßstab.

## 4. Redaktionelle Reparatur (Inhalt)

| Artikel | Änderung |
|---|---|
| **DSL-Anbieter wechseln** | Titel → „DSL-Anbieter wechseln: Gesamtpreis, Router und Schalttermin". Abschnitt „Wann kannst du deinen DSL-Vertrag kündigen?" eigenständig neu gefasst – aus Sicht des Festnetzanschlusses (Schalttermin, Adresse, Umzug, Bandbreite); interne Dopplung der Monatsfrist entfernt; jede Zahl mit § 56-Beleg im Satz (RS5). Cover neu gerendert. |
| **Handyvertrag kündigen** | Titel → „Handyvertrag kündigen: Enddatum, Nachweis und Rufnummer". Abschnitt „Welche Kündigungsfrist gilt…?" neu gefasst – zwei Phasen, Gerät/Rate als Mobilfunk-Besonderheit. Beide Dichte-Sätze des Keyword-Heilers entfernt; Keyword zweimal natürlich eingebaut (Dichte 0,42 % > 0,30 %, kein Re-Insert). Cover neu gerendert. |

Nachgemessen nach der Reparatur (beide Artikel):
`check_uniqueness` **0 kritisch, 0 Twins** · Flesch 63,0 / 61,7 (≥ 60) ·
Lesbarkeit 100 · `reserve_quality_findings` (RS1–RS7) leer · Textverständnis,
Keyword, Titel-R5, YMYL-Review, D1–D6, U1–U2, Länge, Faktenfrische: leer ·
`seo_audit` ✅ · ZEIT-Rechtschreibung 0 Funde. `aenderungsgrund` in
`redaktionelle_pruefung` dokumentiert den Eingriff; Siegel/Status unangetastet.

## 5. Beweise

```
python3 scripts/check_uniqueness.py            # ✅ Audit bestanden – 0 kritisch, 0 Twins
python3 scripts/check_uniqueness.py --selftest # ✅ 8 Twin-Fälle + Collector-Korpus
python3 -m unittest scripts.tests.test_publish_gate_uniqueness   # 16 Tests OK
python3 scripts/release_scorecard.py --selftest                  # ✅ (ST2 inkl. RD2)
python3 scripts/reserve_healer_coverage.py                       # rc=0 (Deckung inkl. U1/U2)
python3 scripts/governance_contract.py                           # 🔒 34 Regeln erfüllt
python3 scripts/selftest_runner.py                               # 191 Wachen grün, Uhr-Proben grün
python3 -m unittest discover -s scripts/tests                    # 2862 Tests, 1 Fehler (vorbestehend, s. u.)
```

**Vorbestehend, nicht Teil dieses Vorgangs:**
`test_integrity_guard.RepoSealTests.test_ausgelieferter_baum_passt_zum_siegel`
ist auf `main` rot (Siegel-Drift `scripts/publikations_vertrag.py`,
`scripts/redaktions_standard.py` aus #713/#721; identisch ohne diese Änderungen).
Reparatur laut Wache: `python3 scripts/integrity_guard.py --set-current` im
eigenen Commit mit `data/integrity_lock.json`.

## 6. Dateien

- `scripts/check_uniqueness.py` – STOP-Erweiterung, `lade_bestand`,
  `kandidaten_befunde`, Collector-Selbsttest, 2 neue Twin-Fälle
- `scripts/publish_gate.py` – Prüfung 10 `uniqueness_failures`, Fail-closed-Stopp, Grund am Kandidaten
- `scripts/release_scorecard.py`, `data/release_scorecard.yaml` – `RD2-einzigartigkeit`
- `scripts/reserve_healer_coverage.py` – begründete Ausnahme `uniqueness_failures`
- `scripts/tests/test_publish_gate_uniqueness.py` – 16 Vertragstests
- `content/posts/2026-10-07-dsl-anbieter-wechseln-…/index.md`,
  `content/posts/2026-10-07-handyvertrag-kuendigen-…/index.md` + Cover-Varianten, `data/covers_manifest.json`
- `CLAUDE.md` (Dauervorgabe), `docs/ANLEITUNG-RELEASE-SCORECARD.md`

Der Vorgang #714 wird vom nächsten sauberen Produktionslauf automatisch
kommentiert und geschlossen (`uniqueness_issue_sync.py`); der Pull Request
trägt `Closes #714` für den Abschlussvermerk.
