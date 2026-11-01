# Aussteuerung: Slots und Zustandskanal

> Wörtlich aus `CLAUDE.md` übernommen am 01.11.2026 (Skill-Umbau). Kein Satz wurde umformuliert, gekürzt oder erfunden; die Überschriften sind eine Ebene tiefer gehängt. Änderungen hier sind Änderungen am Regelwerk – sie brauchen denselben Nachweis wie vorher: Selbsttest der betroffenen Wache, dann Commit.

### Verpasste Slots werden nachgeholt, nicht beklagt (Slot-Wache, seit #601, 05.10.2026)

Am 05.10.2026 endete ein Publikationstag mit 1/2 LIVE, obwohl die
Kapazität grün war – GitHubs Scheduler hatte 4 von 7 planmäßigen Slots der
Content-Linie nie gestartet (Engine 06:10 + 17:40, Kadenz 10:35 + 16:35;
der 16:35er kam erst 2 h 47 min später als einziger). Ein Lauf, der nie
startet, wird nie rot. Das Repo kannte die Klasse von der Newsletter-
Kadenz-Wache (23.09.) – nur die Content-Linie hatte keinen Schutz.

- **Soll-Plan geparsed, nie abgetippt:** `scripts/slot_wache.py` liest die
  cron-Zeilen aus `content-engine-v2.yml` und `kadenz-endkontrolle.yml` –
  wer den Plan verschiebt, verschiebt die Wache mit. Nicht verstandene
  cron-Syntax wird abgelehnt und gemeldet, nie geraten.
- **Urteil:** Slot + 45 min Gnadenfrist ohne einzigen Laufversuch =
  verpasst. Ein FEHLGESCHLAGENER oder LAUFENDER Lauf bedient den Slot
  (laut, kein Auto-Retry) – dieselbe Disziplin wie bei der Newsletter-
  Kadenz-Wache.
- **Eingriff begrenzt:** nur an Publikationstagen (SSOT
  `cadence_guard.PUBLICATION_DAYS`), nur solange LIVE < Mindestziel, ein
  Nachhol-Dispatch je Workflow und Tick (`gh workflow run`, dieselbe
  Freigabestufe wie der Cron). Der Doppel-Fall ist harmlos: concurrency-
  Gruppe `content-bot` reiht ein, das Kadenz-Gate deckelt 2–3 LIVE.
- **Notmeldung:** Nach dem letzten Slot + Gnadenfrist mit offener Quote
  meldet die Wache das Defizit selbst (`engine_issue.py --deficit`, nur
  wenn noch kein offenes existiert) – der Alarm geht auch raus, wenn jeder
  Cron UND jeder Dispatch versagte.
- **Das Defizit-Issue nennt die Ursache:** `engine_issue._diagnose()`
  hängt das Slot-Protokoll des Tages an (Soll-Slots / verpasst / LIVE).
- **Eigener Takt:** `slot-wache.yml` tickt alle 20 Minuten (häufige Ticks
  überleben Tick-Verluste am selben Haken), beweist sich bei jedem Merge
  (push auf die eigenen Pfade) und steht in der Wacht-Liste des Fehler-
  Alertings sowie in `governance_contract.GUARDS`.
- Bedienung: `npm run engine:slots` (Trockenlauf) ·
  `npm run test:engine:slots` (Selbsttest + 29 Unit-Tests).
  Vorgangsbericht: `TAGESDEFIZIT-ENGINE-601-DAUERHEILUNG-PREMIUM-2026-10-05.md`.

### Eine Quote ist ein Zustand, kein Arbeitsauftrag (Zustandskanal, seit #608, 07.10.2026)

Der 05.10.2026 endete mit 1/2 LIVE. Das Fach-Issue **#601** existierte
korrekt – wurde aber um 21:21 durch den Reparatur-Merge #603 geschlossen
(„Closes #601“), obwohl der gemessene Tag rot blieb. Am 06.10. (Dienstag)
übersprang `engine_issue.py` den Tag vollständig („Kein Publikationstag“),
also gab es keinen offenen, frischen Fachkanal. Der um 00:55 UTC
nachgelieferte Montags-Slot der Kadenz-Endkontrolle meldete daraufhin
ehrlich rot („TAGESDEFIZIT – Fachmeldung engine-deficit ist zuständig“) –
und das zentrale Fehler-Alerting musste **fail-open** melden: Es legte das
generische Wartungs-Issue **#608** mit API-Key-/GitHub-/Transient-Runbook
an. Doppelte Buchführung und eine falsche Handlungsanweisung.

Die Ursache war keine Alarmregel, sondern eine **Besitzfrage**: Ein
Arbeitsauftrag ist mit einem Merge erledigt – ein Zustand nur durch eine
neue Messung. Deshalb gilt für `engine_issue.py` (und seine Aufrufer):

- **Besitzer** des Kanals `engine-deficit` ist die Messung selbst – nicht
  der Vorschlag, der die Ursache heilt, und nicht die Hand.
- **Kadenz: jeder Tag.** Gemessen wird immer der jüngste Publikationstag
  (SSOT `cadence_guard.letzter_publikationstag`) – auch Di/Do/Sa/So belegt
  die Produktions-Wache den Kanal (`npm run engine:deficit` zeigt den
  Zustand). Ein Ruhetag vergisst keinen offenen Zustand.
- **Schließpfad: nur die eigene Messung**, in zwei ehrlichen Fällen – Ziel
  am Tag selbst noch erreicht, oder der Fehltag ist vorbei (nicht
  nachholbar, kein Nachtragen von Inhalten) und ein folgender
  Publikationstag erreicht das Ziel nachweislich. Der Vermerk sagt das
  ausdrücklich; repariert wird die Ursache, nicht die Statistik.
- **Reopen:** Wurde der Kanal geschlossen, während der gemessene Tag rot
  war (Merge, Hand, Missverständnis), öffnet die nächste Messung ihn
  wieder – mit Begründung. Danach schließt er sich von selbst, sobald ein
  Publikationstag das Ziel erreicht: kein Dauerläufer.
- **Das zentrale Alerting hängt daran:** Nur wenn der offene Fachkanal für
  denselben Lauf frisch belegt ist, schweigt die generische Meldung
  (#602-Regel). Wer den Kanal an einem Tag nicht belegt, erzeugt am
  nächsten roten Lauf wieder ein generisches Wartungs-Issue – genau #608.
- **Vertrag:** Regel **C23** in `governance_contract.py` friert Besitz,
  Kalender-SSOT, Ruhetag-Messung, Reopen und Marker/Label ein; sabotierte
  Fassungen werden im Kontrakt-Selbsttest rot.
- Bedienung: `npm run engine:deficit` (Zustand, Trockenlauf) ·
  `npm run test:engine:deficit` (Selbsttest + 39 Unit-Tests).
  Vorgangsbericht: `WF-1F8C-608-DAUERHEILUNG-PREMIUM-2026-10-07.md`.
