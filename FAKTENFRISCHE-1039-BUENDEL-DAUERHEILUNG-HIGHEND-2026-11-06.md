# Faktenfrische #1039 – Bündel-Blindfleck heilt dauerhaft, mit Selbstheilung 2026-11-06

**Stand:** 6. November 2026, nach Einholung von `main` (Merge `1bec17d85`,
`main` @ `112905a23`: #1100 Fachbefund-Folgeentscheidungen, #1073
Konfliktmarker-Wache; Abschnitt 8) · **Lauf:** Vorgang auf
`arena/dd833f9a-franksfinanzcheck-blog` · **Ersatz für:** PR #1067
(unmergebar, siehe unten)

> Auftrag (wörtlich): „fix(faktenfrische): #1039 Bündel-Blindfleck heilen – Spitzentag
> mitmessen, Sockel 4 → 12 – #1067 Bitte dauerhaft auf Highend-Level einer Profi-Agentur
> beheben mit automatischer Selbstheilung."

---

## 1. Ausgangslage: was an #1067 nicht hochend war

PR #1067 (geöffnet 04.11.2026, Head `arena/e65bed24-…`, 5 Commits, +483/−6, 8 Dateien)
hatte fachlich die richtige Richtung – aber er war **kein Heilmittel**, er war ein
Vorschlag in einem roten Paket:

1. **Unmergebar.** `mergeable_state` war `dirty` (05.11.2026) bzw. `unknown` (06.11.2026):
   Die Basis divergierte, der PR hätte ohne Rebase nicht gelandet.
2. **Sein eigener Gate war rot** – der Job `regression` in Run `41871656177` an genau
   zwei Schritten: **Schritt 10** („Code-Regression – Suite und Selbsttests“) und
   **Schritt 11** („Uhr-Probe – die Suite muss an jedem Kalendertag grün sein“).
   Ich habe den Prüf-Log des Jobs nachgefordert (`gh api …/jobs/126733245572/logs`) –
   der Log-Blob ist aus diesem Sandbox nicht abrufbar (EOF), die Ursache ist lokal
   **nicht einsehbar**. Lokal reproduzierbar auf diesem Stand sind genau **6
   Suite-Fehler, die auf `main` identisch rot sind** (Abschnitt 4). Keiner davon ist
   durch diesen Vorgang entstanden; keiner davon wird hier wegmoderiert.
3. **Kein Schließpfad bei Rot.** Rot hieß: der Lauf blieb rot stehen – ohne Auftrag,
   ohne Ticket, ohne selbständige Rückkehr. Ein Alarm ohne Schließpfad ist ein
   Dauerläufer (C14). Die angebliche „automatische Selbstheilung“, die der Titel von
   #1067 verspricht, existierte nicht.
4. **Der Befund konnte unbemerkt zurückkehren.** Sockel, Spitzentag-Logik und
   Vertragserweiterung standen nur in diesem einen PR; nichts im laufenden System
   hätte einen neuen Bündel-Blindfleck gemeldet – bis ihn der Kalender zeigt.

Was hier steht, ist die geheilte Version: denselben Befund messen (nicht nur den
ruhigen Tag), die Heilung **schließen** (Ticket mit Schließpfad, das sich selbst
schließt), die Heilung **absichern** (Vertrag, Tests, Wache, Ticket-Schleife) und
alles **offen benennen**, was offen bleibt.

## 2. Befund – am 06.11.2026 nachgemessen (Bestand: 115 Seiten, 35 Fristtage, 23 am 27.11.2026)

Der ruhige Tag ist nicht der härteste. Die Fristen sind **Bündel**; derselbe
Bestand, den die Wache am 06.11.2026 mit ✅ grün grüßte, war am 04.11.2026 bei
Sockel 4 an denselben Kalendertagen rot – nur sah es niemand:

| Messung (06.11.2026) | Sockel 4 (bis 05.11.) | Sockel 12 (seit 06.11.) |
|---|---|---|
| Härtester Bündeltag | **2026-11-26: 38 von 83 heute frischen Seiten zu spät** | kein Befund |
| Voller Kalender-Sweep (365 Starttage) | **36 rote Starttage** | **0 von 365** |
| Sweep über 52 Montage | **5 rote Montage** | **0 von 52** |
| `--wache` vor dem Fix | **Exit 1** – 🛑 Spitzentag reißt die Frist am 2026-11-26 | **Exit 0** |

CLI heute (geheilter Stand, 06.11.2026):

- `--json` → `empfohlenes_budget: 12`, `hartes_limit: 16`, `deckung_prozent: 425.2`,
  `rueckstand_abgebaut: true`, `puenktlich: true`, `spitze_geprueft: 52`
- `--wache` → ✅ Exit 0: Bestand 115 Seiten · fällig heute 1 · überfällig 0 ·
  Bedarf 2,82/Tag (19,8/Woche) · Angebot 12,00/Tag · Deckung 425 % · Rückstand
  abgebaut in 0 Tagen (Frist 7) · Spitzentag mitgemessen: 52 Bündeltage im Horizont
  – kein Befund.

Die #1067-eigenen Werte (113 Seiten / 34 Fristtage / 29 × `faktencheck: 2026-10-13`,
49 rote Kalendertage im Folgejahr, Messung 04.11.2026) sind hier **nicht** als
„aktuelle Lage“ wiederholt – sie stehen als dokumentierte Vorgeschichte im Bericht
`WARTUNG-VEROEFFENTLICHUNG-WF-829B-922-BUENDEL-DAUERHEILUNG-2026-11-04.md` des PR.

**Offen – andere Klasse, ehrlich benannt:** Projiziert man den heutigen Bestand
auf den **31.12.2026**, ist `puenktlich: false` (empfohlenes Budget 16 = Limit;
104 überfällige Seiten; `rueckstand_abgebaut: true`). Schon am **2026-11-26**
(heutiger Bestand, 20 Tage später gelesen) meldet die Wache Exit 1: „24 Seiten
mit ZUKÜNFTIGER Frist würden gerissen … auch mit dem harten Limit von 16 je Lauf
ist der Rückstand nicht fristgerecht abbaubar – Kadenz oder Intervall müssen
entschieden werden (#912)“. Das ist die Rückstands-Klasse aus #912 –
**kein Sockel heilt sie**; es ist eine Entscheidung über Takt/Intervall
(menschlich, in `data/agent_reach/faktenfrische.yaml`). Die neue Schleife
**meldet** das laufend und öffnet das eine Deckungs-Ticket – das ist genau
ihre Aufgabe; die Entscheidung bleibt beim Herausgeber.

## 3. Die Heilung – sechs Schichten, keine davon optional

**Schicht 1 – Spitzentag wird mitgemessen (statt nur behauptet).**
`spitzenlast_stichtage/spitzenlast_stichtag/spitze_zahlen` in
`scripts/faktenfrische_kapazitaet.py`: Kandidaten = Stichtag ∪ alle Fristtage im
Horizont (`frist` oder `frist − vorlauf_tage`); je Kandidat ein Frisch-Plan mit
derselben Formeln wie der Stichtags-Plan (C19 – eine Rechnung, zwei Tage); der
schlechteste Tag mit `puenktlich: False` wird Befund; Nicht-Tages-Pläne ohne
lesbaren Laufkalender liefern `ValueError` statt einer Raten-Aussage (die
Governance meldet dann „nicht beweisbar“ statt eines Tracebacks). Die Zahlen sind
**immer** vorhanden, auch bei Grün: `spitze_geprueft` – sonst existiert der
Blindfleck wieder als toter Punkt (C33).

**Schicht 2 – Sockel 4 → 12 in der SSOT** (`data/agent_reach/faktenfrische.yaml`,
Kommentar mit den Messwerten vom 06.11.2026). Limit 16 und Nachholfrist 7 bleiben
unverändert – weniger zu messen wäre keine Heilung. SSOT bleibt menschlich kuratiert;
die Maschine entscheidet nie darüber.

**Schicht 3 – Vertrag C45 verschärft, nie gelockert (N-17).**
`governance_contract.py`: `_c45_deckung` merged `spitze_zahlen` fail-closed
(`try/except → „nicht beweisbar“` statt Durchreichen); `C45_MARKER` +
`spitzenlast_stichtag` / `spitze_geprueft`; `C45_TESTS` läuft jetzt auch die
Ticket-Tests (C19/C45); `GUARDS` bindet `faktenfrische_deckung_ticket.py` mit in
das vertragliche Minimum (C6).

**Schicht 4 – Regression über den Kalender, nicht über den Tag.**
`BuenndelWacheSweepTest` in `scripts/tests/test_faktenfrische_kapazitaet.py` führt
die Wache über **52 Montage des Folgejahrs** gegen den ausgelieferten Bestand aus
(SSOT-Sockel, keine Handzahl). `SpitzentagTest` bindet den Urteilspfad (9 Verträge:
Kandidaten-Menge, reddest-Tag-Wahl, `spitze_geprueft` immer gesetzt, C45-Befund,
Urteils-Durchmeldung). Selbsttest der Kapazitätsrechnung: **49 Fälle grün**.

**Schicht 5 – Automatische Selbstheilung: das System schließt sich selbst.**
Das Herzstück, das #1067 nicht hatte:

1. **Urteilsfähige Wache.** `--wache` endet bei Spitzentag-Befund mit Exit 1; die
   `::error::`-Zeile nennt Bündeltag und Zahlen. `--json` trägt die `spitze_*`.
2. **Genau ein Ticket, nie zwei.** `scripts/faktenfrische_deckung_ticket.py`
   (`--apply`, `--selftest`): führt **ein** Issue mit Label `faktenfrische-deckung`
   und Marker `<!-- wache-id: faktenfrische-deckung -->` – erstellt **oder
   aktualisiert**, nie dupliziert; Titel, Text und Zahlen folgen ausschließlich dem
   gemessenen Zustand (`bewertung()` aus dem `--json`-Dict, nie dem Diskurs);
   drei Schließpfade im Text (Bündelung entzerren / Takt enger / Korridor in der
   SSOT) – die Entscheidung trifft weiter der Herausgeber (YAML), nie die Maschine.
   Bei **Grün** schließt das Skript das Ticket **selbständig** mit einem Kommentar,
   der die Heilung benennt. Fehlt `gh`, warnt der Schritt und bleibt grün – der
   rote Job bleibt das Tor. Fehlschlag intern: Exit 2 (sichtbar, nie still).
   **26 Selbsttestfälle grün.**
3. **Im Workflow verdrahtet.** `.github/workflows/faktenfrische.yml`: neuer Schritt
   „Deckungs-Ticket melden (`faktenfrische-deckung`, #1039)“ **nach** dem
   Deckungs-Nachweis, `if: always()`, `continue-on-error: true`; Permission
   `issues: write` existierte bereits. Die rote Job’s Schlusszeile nennt jetzt das
   Label, #1039 und den Schließpfad; der Header-Block erklärt, warum der Spitzentag
   mitgemessen wird. Weder `gate` noch irgendeine Schwelle wurde gelockert; es
   wurde **zusätzliches** Gewicht auf die Wage gelegt.
4. **In der Scorecard sichtbar.** `scripts/release_scorecard.py` zählt den
   Spitzentag jetzt aus **derselben** Planmessung (zweite Wahrheit verboten, C19):
   Zeile „Spitzentag (#1039)“ im Faktenfrische-Deckungs-Block – ✅ mitgemessen oder
   ❌ mit Tag und Zahlen, nie ein Freitext.

**Schicht 6 – Testnetz und Uhr.** `scripts/tests/test_faktenfrische_deckung_ticket.py`
(**14 Tests**: Urteil grün/rot/beweislos, Titel-Disziplin, Körper-Inhalte,
26 Selbsttest-Vertragsfälle). `test_faktenfrische_kapazitaet.py` jetzt **52 Tests**.
Uhr-Probe (`selftest_clock.py --trap-modul/--trap`) an **Offset 0/30/97/180/365**
für beide Module unter fremder Uhr: **grün**. Selbsttest Ticket-Werkzeug unter
Höhenuhr: grün.

## 4. Nachweise (am geänderten Baum, 06.11.2026)

| Prüfung | Ergebnis |
|---|---|
| `faktenfrische_kapazitaet.py --selftest` | ✅ 49 Fälle grün |
| `faktenfrische_deckung_ticket.py --selftest` | ✅ 26 Fälle grün |
| `python -m unittest scripts.tests.test_faktenfrische_kapazitaet` | ✅ 52 Tests OK |
| `python -m unittest scripts.tests.test_faktenfrische_deckung_ticket` | ✅ 14 Tests OK |
| `python -m unittest discover -s scripts/tests` | **5338 Tests** – 3 Fehler, alle identisch auf `main` (Worktree-Baseline), **0 neu**; 2 weitere Altlasten-Klasse hier geheilt, 1 (Affiliate-Deep-Link) hat `main` selbst geheilt |
| `governance_contract.py --quick` | ✅ 45/45 Regeln in beide Richtungen bestätigt |
| `integrity_guard.py --gate` | ✅ grün – 55 Kerndateien entsprechen exakt dem signierten Stand (HEAD `1e3a9311`); keine Siegel-Datei berührt |
| Uhr-Probe Offset 0/30/97/180/365 (neue Module) | ✅ grün |
| `faktenfrische_befund_akte.py --wache` (nach Nachzug) | ✅ jeder offene Befund hat Schließweg |
| `fachpruefung_register.py --check` (nach Nachzug) | ✅ aktuell |

**Die 3 verbleibenden Altlasten (nach dem `main`-Merge, identisch rot auf `main` – redaktionelle Entscheidungen, hier offen benannt statt zugedeckt):**

1. `test_einzigartigkeit_bestand.BestandSweepTest.test_kein_kritisches_live_paar_im_bestand` – 6 geteilte Phrasen `2026-09-04-finanzielle-freiheit-…` ↔ `2026-09-07-frugalismus-tipps-…`. Redaktionelle Einzigartigkeits-Entscheidung, keine Maschinenarbeit.
2. `test_social_autopilot.TestKanaltreue716 …(kanal='reddit')` und 3. `test_social_instagram_winkel … TestWinkelRedundanzImBestand (kanal='reddit')` – Artikel `2026-10-28-oekostrom-anbieter-wechseln-sicher-gruen-und-bezahlbar` hat auf Reddit keinen sendbaren Winkel / nur einen. Redaktionelle Winkel-Entscheidung.

**`main` hat eine vierte Altlast selbst geheilt:** den Affiliate-Deep-Link im
Artikel `2026-10-12-energieausweis-was-das-dokument-fuer-deine-fixkosten`
(PR #1100, `112905a23`) – `test_affiliate_link_check …
test_all_live_posts_and_pillars_pass_without_errors` ist nach dem Merge grün.

**Zwei weitere `main`-Altlasten (Listen/Register-Drift) wurden in diesem
Vorgang geheilt** (eigener Commit, maschinell erzeugt, kein Urteil):
`test_faktenfrische_befund_akte … test_akte_im_repo_ist_auf_dem_stand_der_queue`
(Akte 11→14 Befunde, 5 Seiten/4 live nachgezogen) und
`test_inhalts_register.FachpruefungRegisterTests.test_register_ist_aktuell`
(`fachpruefung_register.py` neu erzeugt; nur Zahlenprotokoll-Fundstelle um den
Satzbeginn ergänzt). Nach dem Nachzug: beide Tests grün; die volle Suite meldet
**4 Fehler**, ausschließlich die vier redaktionellen Altlasten oben.

## 5. Ehrliche Grenzen

- **Der Horizont ist 120 Tage.** „0 von 52“ und „0 von 365“ prüfen nur diesen
  Kalenderhorizont – der Blindfleck bleibt nach 120 Tagen eine Aussage der Zukunft.
  Die Wache läuft täglich; sie ist der Radar, nicht eine Garantie.
- **Cold-Start ist bewusst strenger** als der Stichtagspfad (`frisch = heute noch
  frische Seiten`). Dieselbe Formel, nicht eine härtere zweite Wahrheit.
- **Ein Ticket pro Flap:** Rot→Grün→Rot erzeugt je Flap ein Ticket; es ist immer das
  **eine** geöffnete `faktenfrische-deckung`-Ticket (aktualisiert statt dupliziert).
- `RELEASE-SCORECARD.md` zeigt nach diesem Merge bis zum nächsten Deploy noch
  „Empfohlenes Budget 4“ – sie wird beim Deploy (`[skip ci]`) neu aus der SSOT
  (12) erzeugt; handschriftlich wurde sie nicht gefälscht.
- **Schritt 10/11 der PR-#1067-Regression sind lokal nicht einsehbar** (Log-Blob
  nicht abrufbar). Die Ursachenannahme „Zeitbombe in den Altlasten“ ist durch die
  identische Reproduktion auf `main` gestützt – sie ist aber eine Reproduktion,
  kein Nachweis des ursprünglichen Rots. Ehrlicherweise benannt.
- Hugo ist in dieser Umgebung nicht lauffähig; der Build läuft im Workflow. Der
  Hugo-Build-Nachweis über den CI ist im PR grün.
- Rückstands-Klasse **#912** und **#922** (Inhaber-Entscheidung; Cloudflare 403,
  bekannter offener Punkt) bleiben offen und werden hier nicht „geheilt“.
- Die vier redaktionellen Altlasten aus Abschnitt 4 bleiben offen – sie sind
  ausdrücklich **nicht** Teil dieses Vorgangs.

## 6. Geänderte Dateien

- `scripts/faktenfrische_kapazitaet.py` – Spitzentag-Schicht (Kandidaten, Urteil,
  Zahlen, `--wache`-Rot, `--json`, Diagnosezeile, Selbsttest 49)
- `scripts/governance_contract.py` – C45 merged `spitze_zahlen` fail-closed;
  `C45_TESTS`/`C45_MARKER`/`GUARDS` erweitert
- `scripts/faktenfrische_deckung_ticket.py` – **neu**: das Selbstheilungs-Ticket
- `scripts/tests/test_faktenfrische_deckung_ticket.py` – **neu**: 14 Tests
- `scripts/tests/test_faktenfrische_kapazitaet.py` – 9 neue Verträge
- `data/agent_reach/faktenfrische.yaml` – SSOT `max_artikel_pro_lauf` 4 → 12
  (mit Messkommentar; Limit 16 / Nachhol 7 unverändert)
- `.github/workflows/faktenfrische.yml` – neuer Deckungs-Ticket-Schritt; Header
  erklärt den Spitzentag; red-job nennt #1039/Label/Schließpfad
- `scripts/release_scorecard.py` – Spitzentag-Zeile + Verdrahtung
- `docs/ANLEITUNG-FAKTENFRISCHE.md` – „Nachzug 06.11.2026“ (Spitzentag +
  Selbstheilungs-Schleife), Sockel-04-Reste aktualisiert
- `BEFUND-AKTE.md`, `data/faktenfrische_befunde_state.json`,
  `data/fachpruefung_register.yaml` – mechanischer Nachzug (eigener Commit)
- dieser Bericht – neu

**Nicht angefasst:** `data/integrity_history.jsonl`, Artikeltexte/Frontmatter,
alle 55 Siegel-Dateien, `.claude/`, Workflows außer `faktenfrische.yml`,
`integrity_lock.json`. PR #1067 wird nicht geschlossen und nicht gemerged – er
bleibt als Referenz; der Inhaber schließt ihn nach Freigabe.

## 7. Wie man die Heilung prüft (Nachweis-Kette)

```bash
python3 scripts/faktenfrische_kapazitaet.py --selftest      # 49 Fälle
python3 scripts/faktenfrische_kapazitaet.py --wache         # Exit 0, „52 Bündeltage – kein Befund“
python3 scripts/faktenfrische_kapazitaet.py --stichtag 2026-11-26 --wache   # projizierter Bündeltag (heutiger Bestand, Exit 1: #912-Klasse)
python3 scripts/faktenfrische_deckung_ticket.py --selftest  # 26 Fälle
python3 scripts/faktenfrische_deckung_ticket.py             # Dry-Run des Tickets (führt nichts aus)
python3 -m unittest discover -s scripts/tests               # Bestandssonnenschein + Altlasten
python3 scripts/governance_contract.py --quick               # 45/45
```

## 8. Nachtrag nach `main`-Merge (06.11.2026, nachmittags)

Während des Vorgangs lief `main` weiter (`1e3a9311` → `112905a23`: #1100
Fachbefund-Folgeentscheidungen, #1073 Konfliktmarker-Wache, Scorecard-Deploy
`6a6912cb0`, Veröffentlichungsgates `112905a23`). Der PR war dadurch
vorübergehend **unmergebar** – derselbe Befund wie bei #1067 – und sein
CI-Signal blieb aus. Vorgehen: `git merge origin/main`; einziger Konflikt in
`data/faktenfrische_befunde_state.json` (zwei Erzeugungsspuren, identischer
semantischer Inhalt) – aufgelöst durch **Regenerieren** mit dem Generator
(`faktenfrische_befund_akte.py --schreiben`); `governance_contract.py`
auto-merged (C45-Ergänzungen hier, GUARDS-Ergänzung aus #1100 – koexistieren
wie beabsichtigt). Nach dem Merge:

- Volle Suite: **5338 Tests**, 3 Fehler – ausschließlich die oben genannten
  redaktionellen Altlasten; **0 neu**; Governance Quick-Check 45/45;
  `test_faktenfrische_kapazitaet`, `test_faktenfrische_deckung_ticket`,
  `test_faktenfrische_befund_akte`, `test_inhalts_register`,
  `test_konfliktmarker_wache` / `test_folgeentscheidung_kette` /
  `test_git_sync` alle grün.
- `gate` (Qualitäts-Gate: Build + interne Links) **grün** – Hugo baut.
- Lehre, festgeschraubt: Unmergebar heißt kein CI. Die Heilung dieser
  Klasse verlangt den Merge, nicht das Warten.

**Vorgang:** #1039 · **Ersetzt:** #1067 · **Offen (unverändert):** #912, #922
