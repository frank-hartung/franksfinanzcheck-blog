# Vorfall-Bericht: „Content-Engine v2" rot — der Integritäts-Lock stoppte die Produktion

**Datum:** 19.09.2026 · **Status:** behoben über [PR #317](https://github.com/frank-hartung/franksfinanzcheck-blog/pull/317)
(alle Checks grün) · **Schweregrad:** hoch
(Produktions-Slots fielen aus, **kein** Schaden an Artikeln, Links oder Builds)
**Vorgänger:** [Vorfall 18.09.2026 — Qualitäts-Gate als Zeitbombe](INCIDENT-2026-09-18-qualitaets-gate-zeitbombe.md)

## Kurzfassung

Zwei Läufe der Content-Engine starben am Abend des 18.09.2026 im **ersten
Schritt**, vor jeder Artikelarbeit: Der Integritäts-Lock stand auf HARD STOP.
Die Ursache war einen Tag alt und völlig unspektakulär — PR #315 (die
FM-Klebefugen-Heilung des Vorfalls vom selben Tag) hat sechs gesperrte Skripte
geändert und den Lock **nicht mit-signiert**. Der Sabotage-Schutz tat also
genau, was er soll, und traf den Falschen: nicht die Änderung, sondern den
Betrieb.

Der Fehler war strukturell, nicht individuell: Es gab **keinen Ort**, an dem
„gesperrte Datei geändert, aber nicht signiert" *vor* dem Merge auffällt — und
**keine Heilung** für den belegten Fall „committet, aber vergessen". Beides ist
jetzt da: ein PR-Gate (`integrity_guard.py --gate`, Workflow
`integrity-lock.yml`), eine belegte Selbst-Signatur für committeten FEST-Drift
(`--heal` als erster Engine-Schritt) und eine Herkunfts-Akte in jeder Signatur
(`--drift-audit`). KRITISCH-Drift und Laufzeit-Mutationen bleiben HARD STOP —
Sabotage bleibt eine menschliche Entscheidung.

## Was gemeldet wurde

| Lauf | Auslöser | Commit | Ergebnis |
|---|---|---|---|
| [35375644608](https://github.com/frank-hartung/franksfinanzcheck-blog/actions/runs/35375644608) | schedule 17:40 UTC | `aaac6c7d` | ❌ Schritt 3 „Integritäts-Lock prüfen (HARD STOP – Sabotage-Schutz)" |
| [35388673667](https://github.com/frank-hartung/franksfinanzcheck-blog/actions/runs/35388673667) | schedule 19:56 UTC | `e3f00f11` | ❌ derselbe Schritt |

Der Fehler-Alarm [Issue #316](https://github.com/frank-hartung/franksfinanzcheck-blog/issues/316)
wurde 17:39:59 UTC automatisch geöffnet. Das Alerting hat funktioniert — der
Befund war der richtige, die Zuordnung („API-Key abgelaufen? Transienter
Fehler?") war es nicht: Die Meldung riet, das Log hätte es gewusst.

Zwei Folgeschritte färbten in denselben Läufen ebenfalls rot und machten das
Bild unschärfer als nötig: „Persist final acceptance corrections" (committet
ohne Git-Identität, weil die Phasen davor übersprungen wurden) und „Do not
report a quota deficit as success" (`test … = success` — **absichtlich** rot,
damit ein Defizit nie als grüner Lauf durchgeht).

## Was tatsächlich passiert ist

| Zeit (UTC) | Ereignis |
|---|---|
| 18.09. 11:36 | `2be85f3a` — der Lock wird zum echten HARD STOP (Folge-Reparatur des Gate-Vorfalls, Ersatz für den `\|\| echo`-Pfad) |
| 18.09. 11:43 | `61e9b4c9` — **Neu-Signatur** nach dokumentierter Sichtung (42 Dateien, Lock-`signed_at` 11:41:17) |
| 18.09. 13:02 | `ff6232e3` — FM-Klebefugen-Heilung: 13 Content-Dateien + **sechs gesperrte Skripte** (`post_utils`-Naht-SSOT in 27 Schreiben, `fm_boundary_guard` F6) |
| 18.09. 13:10 | Merge von PR #315 — **ohne** Neu-Signatur des Locks |
| 18.09. 17:40 / 19:56 | Content-Engine v2 läuft in den HARD STOP (Exit 1, sechs FEST-Abweichungen); Issue #316 |

Der Lock war also 82 Minuten vor dem Merge frisch signiert und 3 Stunden später
veraltet — nicht durch Sabotage, sondern durch **vergessene Handarbeit** an
einer Stelle, die niemand prüft. Sechs FEST-Dateien, alle aus einem Commit
(`ff6232e3`): `affiliate_integrity_gate.py`, `fazit_schmiede.py`,
`generate_covers.py`, `hardcases_guard.py`, `plagiat_guard.py`,
`redaktions_standard.py`.

**Sichtung vor der Neu-Signatur (Betreiber-Entscheidung, hier dokumentiert).**
Die Abweichungen wurden mit `--drift-audit` auf ihre Herkunft zurückgeführt:
Arbeitsbaum = `HEAD`, keine ungestagten Änderungen, alle sechs Dateien zuletzt
angefasst von `ff6232e3` („fix(quality): FM-Klebefugen dauerhaft schließen –
Naht-SSOT, Wache F6, 13 Dateien geheilt (Folge-Befund 5)"). Das ist die
dokumentierte, mit eigenen Tests belegte Heilung des Vorfalls vom selben Tag
(13/13 Dateien, 292 Unittests, Governance C1–C17). Kein unerklärter Hunk,
keine Laufzeit-Mutation. Danach neu signiert — mit Akte (Commits, Klassen,
Urteile) im Lock.

**Warum das die zweite Runde derselben Klasse war:** Schon am 18.09., 11:41,
stand der Lock wegen vier Abweichungen aus regulär gemergten PRs (#308/#309)
auf HARD STOP — damals fiel es als Folge-Befund 1 auf, wurde gesichtet und neu
signiert. Zwei Vorfälle, zwei Mal dieselbe Wurzel, zwei Mal Handarbeit. Genau
deshalb ist die Reparatur hier keine dritte Signatur, sondern eine Grenze.

## Die Reparatur

**1 — Die Grenze vor den Merge (`--gate` + `integrity-lock.yml`).**
Jeder Pull Request auf `main` prüft jetzt, ob der signierte Kern zum Baum
passt. Passt er nicht, nennt der Lauf die Herkunft (welcher Commit welche
Datei angefasst hat) und die Reparaturzeile für **diesen** PR:
`--set-current`, Lock committen, fertig. Fail-closed, read-only, ohne Secrets
und Abhängigkeiten — der Lauf kostet Sekunden. Kein `push`-Trigger: Ein roter
Lauf, den niemand liest, ist Deko; auf `main` heilt die Engine selbst (siehe 2).

**2 — Belegte Selbst-Signatur statt Produktionsstopp (`--heal`).**
Der erste Engine-Schritt signiert Drift selbst — aber nur, wenn **jede**
Abweichung drei Bedingungen erfüllt:

| Bedingung | Warum |
|---|---|
| in Git versioniert | Nicht-Versioniertes hat keine Geschichte, die man prüfen könnte |
| Arbeitsbaum **bytegleich** zu `HEAD` | Laufzeit-Mutationen (ein Skript fasst den Kern an) werden **nie** automatisch geadelt — genau das ist die Sabotage-Klasse |
| Klasse **FEST** | KRITISCH (`hugo.toml`, Render-Hooks, `head.html`, `robots.txt` …) bleibt HARD STOP (Exit 3) und damit eine menschliche Entscheidung |

Ist etwas davon verletzt, stoppt der Lauf weiter hart und meldet den Grund.
Ist alles erfüllt, wird neu signiert, die Signatur mit ihrer Akte committet
und gepusht. Der Lauf bleibt grün, der Drift ist behoben, und niemand muss
nachts eine Unterschrift nachholen.

**3 — Die Akte in jeder Signatur (`--drift-audit`).**
`data/integrity_lock.json` trägt jetzt unter `audit`, wer wann mit welcher
Begründung signiert hat — samt Herkunft: Commits seit der Vor-Signatur, Klasse
und Urteil je Datei. Ist der Signatur-Stand nicht auflösbar (Rebase-Hash,
flacher Klon), zeigt die Akte die letzten Commits der Datei statt einer leeren
Zeile. Eine Unterschrift ohne Akte ist keine.

**4 — Nebenbei behoben:** Die Commit-Identität wird direkt nach dem Checkout
einmal gesetzt. Damit kann der `!cancelled()`-Schritt „Persist final acceptance
corrections" nicht mehr mit „Author identity unknown" scheitern, wenn frühe
Phasen abgebrochen sind (das war im Vorfall der zweite rote Schritt und hat den
Blick auf den echten Fehler verstellt).

## Nachweis

**Mutationstests am Guard (der Beweis muss beißen):**

| Mutation | Ergebnis |
|---|---|
| `--heal` behandelt KRITISCH-Drift wie FEST | 🔴 „KRITISCH-Drift gilt als selbst-signierbar (Fall5b)" |
| `--heal` signiert ungestagte Änderung (Arbeitsbaum ≠ HEAD) | 🔴 „ungestagte Laufzeit-Mutation gilt als signierbar (Fall4)" |
| HARD STOP signiert trotzdem | 🔴 „HARD STOP hat trotzdem signiert (Fall4c)" |
| Klassifikation liest Git-Herkunft nicht | 🔴 „Akte ohne Commit – Herkunft fehlt (Fall2b)" |
| Rückfall auf „letzte Commits" bei unbekanntem Signatur-Stand entfernt | 🔴 „Rückfall auf 'letzte Commits' fehlt (Fall2b3)" |
| Heilung ist nicht konvergent (zweiter Lauf ändert wieder) | 🔴 „Heilung ist nicht konvergent (Fall3c)" |
| Beweis-Lauf schreibt in den Baum (Lock/Report/Historie) | 🔴 „Selbsttest hat … verändert" |
| PR-Gate lässt FEST-Drift grün durch | 🔴 „auch FEST-Drift muss im PR-Gate rot sein" |

**Belege dieses Laufs:**

* `python3 scripts/integrity_guard.py --selftest` → Exit 0 (5 eingefrorene
  Fälle + Kern-Beweis an einem echten Mini-Repo: Klassifikation, Signatur-Regel,
  Konvergenz, Akte) — **ohne einen Schreibzugriff auf den Baum** (C15).
* `python3 -m unittest discover -s scripts/tests` → alle Tests grün, davon
  **18 neue** in `scripts/tests/test_integrity_guard.py`.
* `python3 scripts/integrity_guard.py --drift-audit` → sechs Abweichungen, alle
  `VERSIEGELBAR`, Herkunft `ff6232e3` (Sichtungs-Tabelle oben).
* Neu signiert + Verify **Exit 0** („Der Kern entspricht exakt dem letzten
  signierten Zustand").
* `integrity_guard.py` steht jetzt im `GUARDS`-Minimum
  (`governance_contract.GUARDS`, C6) — der Kern-Beweis läuft damit in jedem
  Gate-Durchgang mit, inklusive Uhr-Proben des Selbsttest-Runners.
* YAML aller geänderten Workflows parst, `bash -n` über die `run:`-Blöcke ohne
  Fehler.

## Selbst prüfen

```bash
python3 scripts/integrity_guard.py --selftest      # Kern-Beweis (schreibt nie)
python3 scripts/integrity_guard.py                 # Verify (Exit 0 = Siegel rein)
python3 scripts/integrity_guard.py --drift-audit   # Herkunft ansehen (read-only)
python3 scripts/integrity_guard.py --gate          # was das PR-Gate tut
python3 scripts/integrity_guard.py --heal --dry-run # was die Engine täte
python3 -m unittest discover -s scripts/tests      # Regression (inkl. 18 neue)
python3 scripts/selftest_runner.py                 # alle Wachen + Uhr-Proben
```

## Produktivbetrieb

* **PR-Gate:** greift ab dem nächsten Pull Request auf `main`; erster Beleg ist
  dieser PR selbst — alle Checks grün:

  | Check | Lauf | Ergebnis |
  |---|---|---|
  | **Integritäts-Lock (PR-Gate)** (neu) | [35433068144](https://github.com/frank-hartung/franksfinanzcheck-blog/actions/runs/35433068144) | ✅ success, **13 s** (Gate + Kern-Beweis) |
  | Publication reliability regression tests | [35433068121](https://github.com/frank-hartung/franksfinanzcheck-blog/actions/runs/35433068121) | ✅ success, 36 s |
  | Qualitäts-Gate (Build + interne Links) | [35433068093](https://github.com/frank-hartung/franksfinanzcheck-blog/actions/runs/35433068093) | ✅ success, 1 m 15 s (inkl. Selbsttest-Runner mit der neuen Wache) |
* **Engine:** Der nächste planmäßige Lauf (Mo/Mi/Fr; Haupt-Slot 06:10 UTC)
  startet mit frischem Siegel. Tritt wieder Drift auf, signiert er belegten
  FEST-Drift selbst, dokumentiert die Herkunft und **meldet es** (Report +
  Historie + Akte im Lock) — statt den Slot zu verlieren.
* **Issue #316** wird mit diesen Belegen geschlossen.

> **Was bewusst NICHT automatisiert ist:** eine KRITISCH-Abweichung. Sie kann
> weiterhin nur bewusst signiert werden (`--set-current`) oder zurückgenommen
> werden. Der PR-Gate-Satz „im selben PR signieren" macht daraus eine
> Sichtungs-Entscheidung **vor** dem Merge — der Ort, an dem sie hingehört.

## Nachtrag 19.09.2026 — der Pflicht-Check hieß `lock` und schützte nichts

**Befund (per API belegt, 09:14 UTC).** Der Gate-Job trug keinen Anzeigenamen
und meldete sich bei GitHub darum unter seiner Job-ID **`lock`**. Um 09:11 UTC
wurde er unter genau diesem Namen als Pflicht-Check in das Ruleset
„Integritäts-Lock (PR-Gate)“ (#23695872, *active*) eingetragen — das Ruleset
hatte aber **keinen Ziel-Zweig** (`conditions.ref_name.include: []`).
`GET /repos/…/rules/branches/main` antwortete `[]`, `main` stand auf
`protected: false`: ein aktives Häkchen, das nichts schützte. Dieselbe
Fehlerklasse wie der Vorfall selbst — still, grün, folgenlos — nur eine Ebene
höher: nicht im Gate, sondern im Vertrag *um* das Gate.

**Reparatur — der Name ist jetzt ein Vertrag (Governance-Regel C18).**

| Ort | Vorher | Nachher |
|---|---|---|
| `integrity-lock.yml` | Job ohne `name:` → Check `lock` | `name: Integritäts-Siegel` — sprechend, stabil, im Kopf der Datei als Vertrag erklärt |
| `governance_contract.py` | — | **C18 Pflicht-Check:** `PFLICHT_CHECK_NAME = "Integritäts-Siegel"` ist die Quelle; die Workflow-Datei muss ihn tragen, bei jedem PR auf `main` laufen, **ohne** `paths`-Filter (sonst „Expected“ für immer), **ohne** `if:` am Job und `continue-on-error` am Gate-Schritt (sonst Scheingrün), nur mit Leserechten |
| `pflichtcheck_guard.py` (neu, letzter Gate-Schritt) | — | **Wächter des Wächters:** liest den Check-Namen aus der Workflow-Datei, fragt `rules/branches/<Ziel-Zweig>` und urteilt `VERLANGT` / `FEHLT` / `FALSCHE_QUELLE` / `UNGESCHUETZT` — bei Rot mit Diagnose je Ruleset (Name, Zustand, Ziel-Zweige, verlangte Checks) und Reparatur in Klicks. API nicht erreichbar → `::warning::`, nicht rot |
| Doku | — | `docs/PFLICHT-CHECK-RUNBOOK.md` (Zustand prüfen, Ruleset reparieren, Reihenfolge beim Umbenennen) |

Die Wache gegen den Ist-Zustand vom 19.09.:

```
🛑 PFLICHT-CHECK-VERTRAG VERLETZT – Kein aktives Ruleset verlangt einen Status-Check auf dem
   Ziel-Zweig – `Integritäts-Siegel` entscheidet nichts, das Siegel ist Deko.
   Diagnose: Ruleset „Integritäts-Lock (PR-Gate)“ (#23695872, active): verlangt `lock`,
             zielt auf KEINEN Zweig (include: []).
   Fix (Admin, drei Klicks): … Include default branch … `lock` entfernen, `Integritäts-Siegel` hinzufügen
```

**Nachweis:** `governance_contract.py --selftest` (C1–C18, jede C18-Klausel mit
Kunst-Workflow in beide Richtungen), `pflichtcheck_guard.py --selftest` (9 Fälle,
kein Netz, schreibt nie; Fall 9 koppelt Workflow-Datei und Konstante),
`scripts/tests/test_pflichtcheck.py` (21 Tests am echten Workflow inkl.
Mutationen und Verdrahtung über den Runner-Mechanismus). `pflichtcheck_guard.py`
steht im `GUARDS`-Minimum.

**Was nur ein Mensch kann (Admin-Recht):** das Ruleset auf den Default-Branch
zielen lassen und `lock` gegen `Integritäts-Siegel` tauschen — Klickweg und
API-Einzeiler im Runbook. Bis dahin ist der letzte Gate-Schritt in jedem PR
**absichtlich rot** und sagt, warum.

## Nachtrag 20.09.2026 — Stand der Admin-Reparatur (unverändert offen)

**Befund:** Der Pflicht-Check-Vertrag ist weiter verletzt, und zwar ausschließlich
im Meta-Schritt. Der Hard-Stop selbst ist grün: `scripts/integrity_guard.py --gate`
antwortet „43 Kerndateien entsprechen exakt dem signierten Stand (HEAD `7556d54`)“,
und in den PR-Läufen `35517752331` / `35518477966` (20.09.) sind die Schritte 4 und 5
erfolgreich — rot ist nur Schritt 6, `pflichtcheck_guard.py`.

**Ursache (read-only nachgeprüft, 20.09.2026):** `GET /rules/branches/main` liefert
vier Einträge, je `deletion` + `non_fast_forward` aus den Rulesets **#23710849** und
**#23705980** — kein `required_status_checks`, keine `pull_request`-Regel. Das
ursprünglich beauftragte Ruleset **#23695872** antwortet weiter mit **HTTP 404**.
Der Arena-Zugang hat laut `GET /repos/…` keinerlei Repository-Rechte
(`admin/maintain/push/pull/triage: false`), also kein `administration:write`:
Die Reparatur (Check `Integritäts-Siegel` als Required Status Check, App **15368**,
Actions-Bypass `always`) kann nur ein Admin ausführen — Klickweg, exakter PUT-Body
und `gh`-Variante in [`PFLICHT-CHECK-RUNBOOK.md`](PFLICHT-CHECK-RUNBOOK.md).

**Korrektur zur Zeitachse.** Die Notiz „Zustand seit 19.09., ~20:42“ ist ungenau.
Belegt über die Jobs-API:

| Lauf (UTC) | Roter Schritt |
|---|---|
| 19.09. 20:42:36 · `35468218966` | Schritt 4 — `integrity_guard.py --gate` (HARD STOP), Schritte 5/6 übersprungen |
| 19.09. 20:44:43 · `35468323189` | keiner — alle sechs Schritte grün |
| 19.09. 23:09:30 · `35475323371` | Schritt 6 — `pflichtcheck_guard.py` (erster roter Pflicht-Check-Vertrag) |

Der Vertrag ist demnach seit **19.09. 23:09:30 UTC** rot, zeitlich passend zum
Ruleset-Wechsel 22:19/22:37 UTC (#23695872 → #23710849). Die Lauf-Logs selbst waren
in der Prüfumgebung nicht ladbar (`results-receiver.actions.githubusercontent.com`
→ `EOF`); die Einordnung beruht auf den Schritt-Abschlüssen der Jobs-API.

**Folgen:** kein Merge-Blocker (kein Ruleset verlangt den Check — das ist zugleich
die Lücke), aber jeder PR zeigt ein rotes Kreuz, das inhaltlich nichts mit dem PR
zu tun hat. Alarm-Routing: Besitzer **Mensch** (Frank, Admin-Klick), kein
Automations-Ticket, Schließpfad = Ruleset-Reparatur + Re-run des Gate-Jobs.
