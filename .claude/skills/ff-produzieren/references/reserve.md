# Content-Reserve – Messlatte, Übernahme, Heiler

> Wörtlich aus `CLAUDE.md` übernommen am 01.11.2026 (Skill-Umbau). Kein Satz wurde umformuliert, gekürzt oder erfunden; die Überschriften sind eine Ebene tiefer gehängt. Änderungen hier sind Änderungen am Regelwerk – sie brauchen denselben Nachweis wie vorher: Selbsttest der betroffenen Wache, dann Commit.

### Die Messlatte der Reserve gehört nicht dem Gemessenen (seit 26.09.2026, #393)

Zielbestand und Alarmschwelle der Content-Reserve haben **einen** Besitzer:
`scripts/reserve_economy.py`.

- `ziel()` kommt aus `RESERVE_TARGET` (Default 6), `alarmschwelle()` wird
  daraus **abgeleitet** (Ziel − Puffer, Default 2). Die Invariante
  `1 ≤ Alarm < Ziel` ist gerechnet, nicht konfiguriert – ohne diesen Abstand
  füllt die Linie exakt bis zur Alarmgrenze und das Ticket öffnet sich nach
  jeder Veröffentlichung neu (genau so entstand #393).
- **Nie wieder ein Ziel aus `data/reserve-readiness.json` lesen.** Das
  Zertifikat ist das geprüfte Artefakt; sein Feld `target` ist Protokoll
  („gegen diese Latte wurde gemessen“), nie Vorgabe. Vorher las der End-Gate
  es als Vorgabe – ein magerer Lauf schrieb `target: 4` und bekam dafür ein
  grünes „4/4“, die Konvergenz reichte die 4 an ihre Kindprozesse weiter und
  schrieb sie zurück: eine Ratsche, die das Produktionsziel aussperrte.
- Abweichung Zertifikat ↔ Produktionsziel ist ein benannter Befund
  (`MESSLATTE`), kein Schweigen.
- Keine zweite Kopie der Zahl anlegen – kein `minimum = 4` irgendwo.
  Verträge: `MesslattenBesitzTests` / `PufferInvarianteTests` in
  `scripts/tests/test_reserve_pipeline.py`.
- Vorfallbericht: `docs/INCIDENT-2026-09-26-bot-watchdog-393.md`.

### Die Reserve füllt sich aus dem Bestand, nicht nur aus Neuproduktion (DAUERVORGABE, seit #594, 05.10.2026)

Achter Vorfall der Klasse „Content-Reserve niedrig" (#251, #272, #281, #393,
#446, #462, #520, #594). Am 05.10. waren **14 Entwürfe reif** und **0** im
Pool: Die Reserve war nicht leer, sie war abgeschnitten. Wer den Vorrat nur
auffüllt, repariert den Melder – nicht die Linie. Deshalb gilt dauerhaft:

- **Übernahme ist ein Werkzeug, kein Handgriff.** `scripts/reserve_intake.py`
  entscheidet nach Triage-Reife, Risikoklasse, Themen-Dublette, Eigentum und
  Faktenfrische – und schreibt **jede** Entscheidung mit Grund nach
  `data/reserve-intake.json`. Auch jede Ablehnung. Eine Übernahme ohne
  Begründung ist ein Testfehler.
- **YMYL bleibt beim Menschen.** Risikoklasse `erhoeht` (Versicherung,
  Kredit, Steuer) wird nie automatisch in den Pool gezogen. Ein hoher Zähler
  ist kein Qualitätsnachweis.
- **Löschen braucht einen Beweis.** Unheilbare Klasse **und** zwei Läufe
  Beleg (`RESERVE_JANITOR_HITS`) **und** Karenz
  (`RESERVE_JANITOR_KARENZ_TAGE`). Trockenläufe zählen nicht, derselbe
  `run_key` zählt einmal. Geschontes erscheint im `--md`-Bericht mit
  Einzelbegründung – nichts verschwindet lautlos.
- **Keine Heilung ohne geprüfte Deckung.** `reserve_blocker_klassen.py` ist
  die einzige Stelle, die „heilbar" definiert; `reserve_healer_coverage.py`
  prüft sie gegen die Kette. Fehlt die Deckung: Aufräumer rc=0 mit
  `::error::` (der Nachtlauf darf daran nicht sterben), Finisher rc=1 ohne
  Schreibzugriff.
- **Identität schlägt Namensähnlichkeit.** Das Custody-Gedächtnis
  schlüsselt datumslos; zwei Entwürfe können denselben Stamm tragen.
  `--heal` setzt die Fahne nur auf dem **gemerkten** Slug, namensgleiche
  Geschwister werden berichtet, nie adoptiert.
- **CTA- und Offenlegungsblöcke sind für Heiler tabu.** Der interne Linker
  verlinkt Fließtext, nie Werbekennzeichnung (`cta_ranges()`).
- **Neue Wachen sind uhrfest.** Selbsttests laufen gegen feste Probetage und
  stempeln Dateialter absolut (`selftest_clock.stempel`) – nie „JETZT minus n
  Tage". Beide Wachen dieses Vorgangs fielen genau daran im PR-Gate auf.
- Verträge: `BestandsaufnahmeTests`, `LoeschRechtTests`,
  `LoeschDeckungsWacheTests`, `TriageFensterTests`, `CustodyIdentitaetTests`,
  `LinkerCtaSperrzoneTests`, `UhrZwangDerReserveWachenTests` in
  `scripts/tests/test_reserve_pipeline.py`.
- Vorgangsbericht: `BOT-WATCHDOG-RESERVE-594-DAUERHEILUNG-PREMIUM-2026-10-05.md`.

### Ein harter Blocker braucht einen Heiler (Content-Reserve, C29, seit #612, 07.10.2026)

Der harte End-Gate der Reserve („Stock shortage must not look successful“) war
rot, weil der Vorrat bei **Ziel 6 / bereit 2** stand – und er hatte recht: fünf
der letzten sechs Läufe endeten so. Die Zertifizierung hatte korrekt abgelehnt;
die Ursachen lagen davor:

- **Ein fertiger Kandidat hing an einem Politur-Rest.** R11/R13/R14
  (Politur-Ruinen) entscheiden seit #482 über die Veröffentlichung, aber keine
  Kette durfte sie heilen. `2026-10-07-wie-smart-home-…` scheiterte einzig an
  einem `SATZ: `-Präfix vor einer vollständig intakten Tabellenzeile
  (Zertifikat 0,95) und wurde als `reserve_blocked` aus dem Pool genommen.
  `scripts/politur_ruine_heiler.py` heilt die drei Klassen jetzt **beweisbar**
  (Tor T1–T4: keine Ruine bleibt, keine neue, Frontmatter/Links/Shortcodes
  stabil, Wortzahl ≥ 97 % − belegter Verlust) und **idempotent** – R12/R16
  werden nur gemeldet, Raten wäre eine Fälschung. Er läuft in Reserve- und
  Live-Kette, in der Deckung (`--wirkungsprobe`) und unter Siegel (FEST).
- **Die Geburt maß die Publish-Regel nicht.** `profi_quality_ok` prüfte alles
  außer der Lesbarkeit (Flesch ≥ 60 ist seit #585 hart): sieben Kandidaten
  wurden mit 53,1–59,9 geboren und fielen später geschlossen durch.
  `generate_drafts.lesbarkeits_befund` misst gegen die **importierte** SSOT
  `readability_check.NEW_FLESCH_MIN` – keine zweite Zahl.
- **Der Retry war blind.** Die Befunde des Vorversuchs gingen nie an den
  nächsten Versuch. `generate_article_text(…, hinweise=…)` baut daraus einen
  **KORREKTUR-AUFTRAG** im Prompt; `engine_generate.try_generate` reicht ihn
  weiter.
- **Der Trend-Beweis starb mit dem roten Lauf.** Die Chronik-Zeile entstand
  nach dem einzigen Commit-Schritt (letzter CI-Eintrag: 02.10.). Jetzt schreibt
  `reserve_gate.py --chronik` **vor** der Sicherung und ist je `lauf` idempotent;
  der End-Gate am Ende schreibt nichts doppelt.

- **Vertrag:** Regel **C29** in `governance_contract.py` friert alle vier
  Lektionen am echten Baum ein (Geburtsmessung, Retry-Gedächtnis,
  Chronik-Reihenfolge, Ruinen-Heiler in Kette/Deckung/Wirkungsprobe); sabotierte
  Fassungen werden im Kontrakt-Selbsttest rot. Klassen und Löschrechte stehen in
  `reserve_blocker_klassen.GATE_BEFUNDE` – R12/R16 bleiben bewusst „unbekannt“
  (fail-closed, nichts wird gelöscht, was niemand heilen kann).
- Bedienung: `python3 scripts/politur_ruine_heiler.py --selftest` ·
  `--wirkungsprobe` (Wirkung je Klasse + Idempotenz) ·
  `--file <pfad>` (Trockenlauf) bzw. `--fix`. Tests:
  `python3 -m unittest scripts.tests.test_reserve_pipeline`.
  Vorgangsbericht: `WF-D4E0-612-DAUERHEILUNG-PREMIUM-2026-10-07.md`.

### Die Endabnahme heilt Shortcode-Schaden und benennt Build-Crashs (WF-A535 #529, seit 02.10.2026)

Am 02.10.2026 ließ ein einziger Markdown-Link in einem
`rechner`-Shortcode-Parameter **alle** Hugo-Builds sterben; die
Content-Engine-Endabnahme (`publication_release.py`) endete in rohem
Traceback, der Reserve-Refill lief nie, und das Auto-Issue riet zu
API-Keys statt zur echten Ursache. Vertrag seither:

- `publication_release.py` führt am Anfang **jedes** Laufs
  `shortcode_guard.py --fix` aus (eine Quelle, alle Aufrufer: Engine,
  Kadenz-Backstop, Deploy-Refill) – best-effort, der Build bleibt hart.
- **Exit-Codes sind Vertrag:** 0 = ok · 1 = Tagesdefizit (ehrlich rot,
  aus `publication_check`) · 3 = Release-Crash (fail-closed, strukturiert
  diagnostiziert: echte Hugo-Fehlerzeile + Reparaturpfad + Audit-Event).
  Wer die Trennung einebnet, macht Crashs wieder ununterscheidbar von
  Defiziten – genau der Zustand, der #529 öffnete.
- Die Engine-Workflow führt die Shortcode-Wache **vor** der Endabnahme
  (Spiegel der Kadenz-Endkontrolle) und der Wächter-Schritt am Ende
  benennt die Klasse (`TAGESDEFIZIT` vs. `RELEASE-CRASH`) als Annotation.
- Verdrahtung ist gepinnt: `scripts/tests/test_publication_release_wache.py`.
  Runbook + Tathergang: `ENDABNAHME-WACHE-PREMIUM-2026-10-02.md`.
