# Alarme, Klassen und die Release-Scorecard

> Wörtlich aus `CLAUDE.md` übernommen am 01.11.2026 (Skill-Umbau). Kein Satz wurde umformuliert, gekürzt oder erfunden; die Überschriften sind eine Ebene tiefer gehängt. Änderungen hier sind Änderungen am Regelwerk – sie brauchen denselben Nachweis wie vorher: Selbsttest der betroffenen Wache, dann Commit.

### Alarm-Routing (seit #272, 12.09.2026)

**Nie wieder einen Befund ohne Besitzer melden.** Jeder neue Melde-Befund
braucht `owner` (`auto` = Maschine heilt, `human` = nur ein Mensch), `severity`
(P1–P3) und `channel` (Label, dem das Ticket gehört). Menschliche Befunde
öffnen **kein** Automations-Ticket und halten keins offen – sonst entsteht der
Dauer-Alarm ohne Schließpfad, der #272 erzeugt hat.

- SSOT: `scripts/alert_router.py` (Planung rein/testbar, `gh`-Aufrufe abgesichert)
- Anwender: `scripts/bot_watchdog.py --route`
- Vertrag: `governance_contract.py` **C14** (prüft Besitz-Trennung + Schließpfad)
- Betriebsmodell: `docs/ALARMROUTING-2026-09-12.md`

### Die Klasse geht dem Kanal vor (Auslieferungs-SLO, C28, seit #611, 07.10.2026)

Am 05.10.2026 endete der Montag bei **1/2 LIVE** (der 19:22 UTC nachgelieferte
Slot rettete genau einen Artikel). Am 06.10. lief der öffentliche Nachweis
(`Publication Delivery`) zweimal rot – um 01:17 und 14:10 UTC. Der Beleg sagte
die Ursache selbst:

```json
{"day": "2026-10-05", "source": ["…preiswert-surfen…"], "delivered": ["…preiswert-surfen…"],
 "errors": [], "ok": false, "minimum": 2, "maximum": 3}
```

`delivered == source`, keine Fehler: **Die Auslieferung war vollständig – der
Bestand trug den Tag nicht.** Weil der rote Sammel-Schritt („Missing public
delivery is a failed run“) keine Ursache nannte, legte das zentrale
Fehler-Alerting das generische Wartungs-Issue **#611** mit API-Key-/Transient-
Runbook an, obwohl der Fachkanal `engine-deficit` (C23) längst existierte –
dieselbe Doppelmeldung wie #602/#608, nur beim zweiten Melder derselben Sache.

`ok` ist die Summe zweier Wahrheiten mit zwei Besitzern; der Beleg trägt sie
jetzt getrennt (`publication_check.klasse()`):

| Klasse | Bedeutung | Besitzer |
|---|---|---|
| `ok` | Tag bestätigt (Mindestziel…Maximum öffentlich) | niemand – grün |
| `quelle_unter` | Bestand unter dem Mindestziel des gemessenen Tages | Fachkanal `engine-deficit` (Nachfüllung) |
| `quelle_ueber` | Bestand über dem Tagesmaximum | Kadenz-Gate (stuft im Deploy zurück) |
| `auslieferung` | Bestand im Zielband, öffentlich fehlt etwas | Deploy/CDN, P1-Kanal (#610) |
| `unbekannt` | kein lesbarer Beleg | fail-closed laut |

- **Die Klasse ist additiv.** `ok` behält seine Bedeutung; kein Aufrufer
  verliert ein Feld. Zusätzlich steht die Klasse in der versionierten Historie
  (`data/publication-delivery-history.jsonl`), damit ein roter Tag später
  seinem Besitzer zuordenbar bleibt.
- **Der Workflow antwortet der Klasse**, nicht dem Sammel-Boolean: eigener
  roter Schritt je Klasse. Nur `quelle_unter` ruft den Defizit-Fachkanal und
  belegt ihn **vor** dem roten Exit (`engine_issue.py --deficit`); sein
  Schrittname trägt beide Kennwörter („TAGESDEFIZIT“ + „engine-deficit“), an
  denen die Stummschaltung des Alertings hängt (#602-Regel). Überschuss und
  Auslieferungsdefizit bleiben laut mit ehrlichem Namen.
- **Ein bestätigter Tag hat keine Klasse nötig:** `ok` wird zuerst geprüft,
  ein unbekannter Beleg ist niemals still.
- **Vertrag:** Regel **C28** in `governance_contract.py` friert Klasse,
  Schritt-Namen, Reihenfolge (Beleg vor rotem Exit) und die beidseitige
  Alerting-Zuordnung ein; sechs Kunstbefunde werden im Kontrakt-Selbsttest rot.
- Bedienung: `npm run delivery:klasse` (Klasse des gültigen Belegs) ·
  `npm run test:delivery` (Regressionen) ·
  `python3 scripts/publication_check.py --selftest` (Logik-Beweis, uhrfest) ·
  `python3 scripts/publication_check.py --online` (voller Nachweis).
  Vorgangsbericht: `WF-7C1F-611-DAUERHEILUNG-PREMIUM-2026-10-07.md`.

### Meldetakt an den Ausfall (C35, seit #676 Teil 2, 10.10.2026)

C34 baute den Befund `deploy-blockade`. Gesehen hat ihn trotzdem niemand: Der
Watchdog lief **einmal täglich** um 08:30 UTC, zwischen Ausfall-Beginn und
Entdeckung lagen bis zu 23,5 Stunden. Der ganze Ausfall vom 09.10.2026
(19 h 38 min) fand zwischen zwei Läufen statt – und als das Ticket offen war,
rechnete die Eskalationsleiter in **Tagen** (0/3/7/14) mit 72 h Mindestabstand:
während der 19 Stunden kein einziger Kommentar. **Der Meldetakt war an den
Kalender gebunden, nicht an den Ausfall.**

- **Zwei Takte in einem Workflow.** `bot-watchdog.yml` läuft stündlich `5 * * * *`
  als **Ausfall-Takt** (`--triage`) und täglich `30 8 * * *` als **Voll-Lauf**.
  Der Takt-Umschalter (`id: takt`) liest `github.event.schedule`; per
  `workflow_dispatch` ist der Takt wählbar (`auto|triage|voll`).
- **Der Ausfall-Takt ist read-only.** Jeder teure und jeder schreibende Schritt
  prüft `steps.takt.outputs.modus == 'voll'`: Hugo, Reserve-Zertifikat,
  Pinterest-Report, Content-Reserve-Dispatch und der Commit des
  Routing-Zustands. Ein stündlicher Lauf kann damit per Konstruktion weder
  bauen noch produzieren noch nach main committen.
- **Eine nicht ausgeführte Messung ist kein Grün (C2).** Nicht gemessene Checks
  stehen als `ÜBERSPRUNGEN (Ausfall-Takt – Voll-Lauf 08:30 UTC)` in der Env –
  niemals als `OK`. Der Wortlaut ist Vertragsbestandteil.
- **Der Router meldet in Stunden, solange der Ausfall steht.** Befunde der
  Ausfall-Klasse tragen `akut=True` und folgen `AKUT_TAKT` (0/1/6/24 h, danach
  alle 24 h). Gerechnet wird ab dem **letzten Stand**, nicht ab der
  Stufen-Schwelle – sonst würde der stündliche Takt ab Stunde 48 jede Runde
  feuern (Taktfeuer statt Meldetakt). **Chronische Befunde behalten ihre
  72-h-Kadenz unverändert** (#272 bleibt gültig).
- **Voraussetzung:** Weil der Ausfall-Takt stündlich misst, ist das Ticket-Alter
  ein brauchbares Maß für die Ausfalldauer. Bei einem täglichen Lauf dürfte die
  Leiter gar nicht in Stunden rechnen.
- **Eine Blockade ist auch ohne 404 ein Befund.** `CHECK3B == blockiert`
  erzeugt `deploy-blockade` unabhängig vom HTTP-Status – sonst blieb die
  eingefrorene Auslieferung unsichtbar, bis der nächste Artikel 404 lief.
- **Ein Befund, zwei Beleg-Quellen.** `classify_deploy_jobs` (blockierender
  Schritt) und `deploy_ausfall_spur` (Fehlschlag-Serie, Run-Id) fließen in
  **einen** `live-site`-Befund. Zwei Befunde mit derselben id zeigten denselben
  Ausfall doppelt, einmal ohne Heilungsweg.
- Tests: `scripts/tests/test_bot_watchdog_meldetakt.py` (Takt, Nicht-Messung,
  Stunden-Leiter, Grenze zum Taktfeuer, C35-Sabotagen, Anker-Disziplin).
  Vorgangsbericht:
  `BOT-WATCHDOG-676-TEIL2-MELDETAKT-DAUERHEILUNG-PREMIUM-2026-10-10.md`.

Vertrag: **C35** in `governance_contract.py` (stündlicher Ausfall-Takt ·
Voll-Lauf bleibt · Takt-Umschalter · read-only-Takt · Nicht-Messung ist kein
Grün · Router nutzt den akuten Takt · Chronisch bleibt bei 72 h · Ausfall-Befund
ist akut · Regressionstest).

### Release-Scorecard: die Produktionswahrheit (seit 03.10.2026)

Das Repo hat viele Gates, Reports, Zustandsdateien und Wachen – stark, aber
ohne EINEN Wahrheitsort kann niemand auf einen Blick sagen, was
veröffentlicht, was blockiert, wer entscheidet und ob die live gegangene
Version wirklich die geprüfte war. Die Antwort ist die **Release-Scorecard**:

- **Eine Zeile pro Artikel, acht Dimensionen:** Technik · Quellen ·
  Faktenalter · Affiliate-Integrität · Redundanz · YMYL-Risiko · menschliche
  Freigabe · nächste Überprüfung. Sichtbar in `RELEASE-SCORECARD.md`,
  maschinenlesbar in `data/release_scorecard_state.json` (Siegel) und
  `data/release_scorecard_history.jsonl` (Verlauf).
- **SSOT ist deklarativ:** `data/release_scorecard.yaml` erklärt jeden Check
  mit `wirkung: blockiert|warnung` (Fragen 1+2), Besitz
  (`entscheidung: auto|human`), Eskalationsmatrix, Falsch-Positiv-Protokoll,
  Freigabeprozess und Siegel-Mechanik (Fragen 3–6). Die Datei ist menschlich
  kuratiert – die Maschine liest sie, schreibt sie nie.
- **Keine zweite Messregel (C19):** `scripts/release_scorecard.py` misst
  ausschließlich über die Collector-Funktionen des Publish-Gates und die
  Prüffunktionen der Fachwachen (`editorial_review_gate.evaluate_path`,
  `faktenfrische.faelligkeit`, `publish_gate.duplicate_failures`). Die Governance-Regel **C19**
  erzwingt Deckungsgleichheit – eine harte Gate-Familie, die nicht als
  blockierend deklariert ist, bricht den Build.
- **Beweislauf ohne Heilung (C15):** Die Scorecard setzt
  `publish_gate.DRY_RUN = True` und schreibt ausschließlich ihre eigenen
  Artefakte. Ein nicht führbarer Beweis heißt „nicht beweisbar“ – nie
  „bestanden“ (Exit 2).
- **Siegel (Frage 6):** Beim Deploy versiegelt sie jeden Live-Artikel
  (SHA-256 der Quelldatei + Dimensionen + Deploy-Commit); Drift nach der
  Versiegelung wird im nächsten Lauf sichtbar.
- **Ausnahmen sind befristet:** Falsch-Alarme über `ausnahmen` in der SSOT –
  Pflichtfelder, Ablaufdatum, Unterschrift; downgraden auf warnung, nie auf
  grün; `M2-siegel-bindung` und `T7-render-beweis` sind nie ausnehmbar.
- **Takt:** Deploy hart über die heutigen Kandidaten (`deploy.yml`, vor der
  Auslieferung) + täglich 07:07 MESZ über den Bestand
  (`release-scorecard.yml`, ein Ticket bei Rot, Schließen bei Grün – C4/C12/C14).
- Bedienung: `npm run release:scorecard` · `npm run release:bestand` ·
  `npm run release:artikel -- <slug>` · `npm run test:release`.
  Runbook mit den sechs Antworten: `docs/ANLEITUNG-RELEASE-SCORECARD.md`.

#### Ein Dauer-Alarm ist kein Alarm, sondern eine unbezahlte Rechnung (#912, 29.10.2026)

Vom 20. bis 28.10.2026 war die Scorecard siebenmal rot (12 von 20 Läufen) – immer mit derselben
Zeile „Faktenalter blockiert“, immer mit demselben offenen Ticket #912, das
sich nicht schließen ließ. Die Ursache war keine Inhaltskrise, sondern eine
Rechnung, die niemand angestellt hatte:

| Kennzahl | Wert |
|---|---|
| Bedarf (Σ 1/Intervall über 106 Seiten) | **2,58 Faktenprüfungen/Tag** (≈ 18/Woche) |
| Angebot (3 je Lauf × Di+Do) | **0,86/Tag** |
| Deckung | **33 %** – Rückstand +12 Seiten/Woche |

Die Intervalle waren richtig; **geliefert** wurde zu wenig. Damit war die
Scorecard strukturell nicht grün zu bekommen – ein Dauer-Alarm ohne
Schließpfad, den C14 in derselben Datei verbietet.

- **Die Heilung ist mehr Lieferung, nicht weniger Messung:** Bestands-Takt
  täglich statt Di+Do; Budget aus `planung`/`budget` der SSOT, elastisch per
  `budget.auto_skalierung` (Sockel 3, `hartes_limit_pro_lauf` 10). Die
  Intervalle (30/45/90) bleiben unangetastet.
- **Vorlauf statt Kante:** `planung.vorlauf_tage` (7) macht eine Seite
  *arbeitbar*, bevor sie fällig wird. Ein Rückstand ist binnen
  `planung.nachhol_frist_tage` (7) abzubauen, sonst ist der Lauf rot – das ist
  der Schließpfad.
- **EDF statt Klassenrang:** Die Auswahl sortiert nach Frist
  (earliest deadline first), nicht nach Risikoklasse. Vorher verhungerten
  Standard-Seiten (90 Tage) unbegrenzt hinter saisonalen (30 Tage).
- **Eine Regel, zwei Leser (C19):** `faktenfrische.faelligkeit` liefert seit
  dem 29.10. auch `frist` und `restlaufzeit`; die Scorecard *liest* sie,
  statt „faktencheck + Intervall“ ein zweites Mal zu rechnen.
- **Die Ursache steht im Ticket:** `scripts/faktenfrische_kapazitaet.py`
  rechnet Bedarf gegen Angebot (cron wird geparst, nie abgetippt), der Report
  zeigt sie als Abschnitt „Faktenfrische-Deckung“, das Siegel trägt sie unter
  `kapazitaet`.
- **Der Bau wird rot, bevor der Bestand rot wird:** Governance **C45** prüft
  statisch `max_artikel_pro_lauf (Sockel) × Läufe/Tag ≥ Bedarf ×
  min_deckung_prozent` (110 %). Das harte Limit ist nur die Spitze und zählt
  nicht als Plan – eine Kadenz, die erst im Dauer-Spitzenbetrieb aufgeht, baut
  keinen Rückstand ab. Wächst der Bestand über die Kapazität, ist das ein
  Bau-Befund mit Zahl, nicht ein Rätsel-Ticket Wochen später. Rückbauprobe:
  cron zurück auf Di+Do → C45 nennt „0,86/Tag gegen 2,84/Tag nötig“.
- Bedienung/Test: `npm run faktenfrische:deckung` ·
  `python3 scripts/faktenfrische_kapazitaet.py --wache` ·
  `npm run test:faktenfrische` (33 Unit-Tests + 36 Selbsttest-Fälle).
  Vorgang: `RELEASE-SCORECARD-912-DAUERHEILUNG-PREMIUM-2026-10-29.md`.
