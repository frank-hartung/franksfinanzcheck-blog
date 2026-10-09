# Bot-Watchdog #676: Ein einziger Format-Befund fror die ganze Auslieferung ein

**Stand:** 09.10.2026 · **Meldung:** [#676](https://github.com/frank-hartung/franksfinanzcheck-blog/issues/676)
· **Klasse:** maschinell behebbar, Besitzer `machine/auto`, Kanal `live-site`

> **„P1 · Neuester Artikel nicht live“** – `2026-10-07-campingurlaub-2026-clever-sparen-ohne-komfortverlust`
> lieferte HTTP **404**. Nächster Schritt im Ticket: *„Deploy prüfen, ggf. Deploy-Catchup
> triggern (Actions → Deploy auf GitHub Pages).“*

## Das Urteil in einem Satz

Der Artikel war gesund, `draft: false` und baufertig – er war nur **nie ausgeliefert
worden**, weil seit 02:12 UTC jeder Deploy im Schritt `Release-Scorecard` mit Exit 1
starb und damit auch `pages-deployment` ausfiel; ausgelöst hatte das ein **einziger
wortgleicher End-CTA in einem anderen Artikel**, den die Duplikat-Wache als Inhaltsklau
maß, obwohl derselbe Wortlaut von der CTA-Vertrags-SSOT vorgeschrieben ist.

Der Befund war echt. Falsch war seine **Wirkung**: Ein Format-Befund an einem Artikel
blockierte die Auslieferung aller 75 Artikel. Der Ratschlag im Ticket war zudem nicht
nur ungenau, er beschrieb eine Maßnahme, die den Ausfall nachweislich **verlängerte** –
der Deploy-Catchup lief längst stündlich und wiederholte 13-mal denselben Fehlschlag.

---

## 1. Zeitleiste (UTC, 08./09.10.2026)

| Zeit | Ereignis | Beleg |
|---|---|---|
| 08.10. 22:06:47 | Letzter **grüner** Deploy vor dem Fenster | Run `37851368576` (`workflow_dispatch`) |
| 09.10. 02:12 | Erster roter Deploy des Tages | `gh run list --workflow deploy.yml` |
| 09.10. 11:50:23 | Tägliche `release-scorecard.yml` rot – dieselbe Ursache | Run `37926200241` |
| 09.10. 14:34–17:10 | Deploy-Catchup und Push-Deploys rot, jeweils am selben Schritt | Runs `37945261056`, `37957830307`, `37963585911`, `37964399723` |
| 09.10. 15:27:43 | Bot-Watchdog misst `live-site` → HTTP 404 | Run `37951905455` |
| 09.10. 15:28:32 | Meldung **#676** angelegt, Ratschlag „Deploy-Catchup triggern“ | Issue #676 |
| 09.10. 17:45:33 | Deploy wieder **grün** (Vorgang WF-54C4/#674, PR #677) | Run `37968526680` |
| 09.10. 18:13:37 | `An GitHub Pages ausliefern` erfolgreich – Freeze beendet | Run `37968526680`, Job `pages-deployment` |

**13 aufeinanderfolgende Deploy-Fehlschläge** zwischen dem letzten grünen Lauf und
17:45 UTC. In diesem Fenster wurde nichts neu veröffentlicht – deshalb 404.

Harter Beleg für den Fehlschritt (Run `37963585911`, Job `deploy`, Job-ID `113932312815`):

```
failure: Process completed with exit code 1.
```
`gh api repos/:owner/:repo/check-runs/113932312815/annotations`
Fehlgeschlagener Schritt: `Release-Scorecard (Produktionswahrheit versiegeln, fail-closed)`.
Alles dahinter – Heal-Diff, Rebuild, Pagefind, `pages-deployment` – blieb `skipped`.

---

## 2. Ursachen (U1–U4)

### U1 · Die Ausnahme für Haus-Templates war eine Abschreibung, keine Ableitung

Die Duplikat-Wache kannte wiederkehrende Haussätze über `BOILERPLATE_RE` – eine
handgeschriebene Musterliste. Der End-CTA eines Artikels wird aber von
`cta_builder.cta_end_block()` aus `affiliate_intent_contract.ZIELE` erzeugt: **derselbe
Wortlaut ist dort Pflicht**, nicht Zufall. Zwei Artikel, die den Vertrag am treuesten
erfüllen, waren damit automatisch ein `D3-X`-Fund.

Verschärft durch Unicode: `affiliate_intent_contract` erzeugt Bindestriche als
U+2011 (nicht trennender Bindestrich). Die Wache normalisierte nur U+2010–U+2015
teilweise und sah zwei *verschiedene* Zeichenketten – die Musterliste traf also selbst
dann nicht, wenn sie den Satz kannte.

**Wirkung:** `RD1-duplikate` auf `7-gewohnheiten-fuer-finanzielle-freiheit` (Z. 216 ≡
`etf-sparplan…` Z. 164). In `data/release_scorecard.yaml` ist `RD1-duplikate` als
`wirkung: blockiert` / `entscheidung: auto` deklariert – aber Cross-Artikel-Funde (D3/D4)
werden bewusst **nie** automatisch geheilt (Redaktionsweg). Ein `auto`-Blocker ohne
Heilweg ist ein Dauerblocker.

### U2 · Der Blustradius war die ganze Seite

`deploy.yml` maß die Produktionswahrheit **nach** dem Build und **vor** der
Auslieferung, fail-closed. Korrekt als Prinzip – aber ein blockierter Kandidat stoppte
den Lauf vollständig. Es gab keinen Schritt, der einen blockierten Artikel aus der
Auslieferung nimmt und den Rest durchmisst. Ein Artikel mit Formatbefund ⇒ 75 Artikel
nicht live ⇒ Watchdog meldet P1.

### U3 · Der Catchup wiederholte den Fehlschlag, statt ihn zu benennen

`deploy-catchup.yml` stößt `deploy.yml` unverändert an. Ohne Diagnose im Ticket las sich
„Deploy-Catchup triggern“ wie eine offene Maßnahme – tatsächlich war sie die Ursache der
13 identischen Fehlschläge. Der Watchdog-Fund nannte HTTP-Status und URL, aber nicht
Workflow, Job, Schritt und Run-ID.

### U4 · Eine Messregel konnte abstürzen statt zu messen

`release_scorecard.bewerte_artikel()` benutzte `je_dimension` und `befundliste` in der
Schleife für **nicht deklarierte** Check-IDs, bevor beide Variablen initialisiert waren
(`NameError`). Folge: roher Traceback, Exit 2 (Werkzeugfehler) statt eines Befunds –
ebenfalls ein blockierter Deploy, nur ohne verwertbare Meldung.

### U5 · Nebenbefund dieses Vorgangs: dieselbe Klasse auf der Prüfebene

Bei der CI-Kontrolle dieses PRs zeigte sich derselbe Mechanismus an anderer Stelle.
`publication-reliability-tests.yml` ist der **einzige** Workflow, der die vollständige
Unit-Test-Suite fährt (`python3 -m unittest discover -s scripts/tests -v`). Sein erster
fachlicher Schritt prüft einen **Daten**-Zustand (`reserve_artifacts.py --check`), und
der war auf `main` rot – zwei alte SHA-256-Zertifikate.

Folge: Die Suite wurde `skipped`. Damit lief im gesamten Repo **kein** Regressionstest
mehr, auch die neuen aus #674 und diesem Vorgang nicht. Ein Befund über einen Zustand
fror die Prüfung des Codes ein – exakt die Blustradius-Klasse aus U2, nur eine Ebene
höher: Dort blockierte ein Artikel die Auslieferung aller Artikel, hier blockierte ein
Daten-Artefakt die Verifikation aller Code-Änderungen. Der Check war rot „aus einem
Grund, der mit dem geprüften Code nichts zu tun hatte", und niemand sah, was die Tests
dazu sagen.

**Heilung:** Die vier Prüf-Schritte (Suite + Selbsttests, Uhr-Probe, KI-Probe,
Ledger-Isolation) laufen jetzt mit `if: ${{ !cancelled() }}`. Der Job bleibt über den
Daten-Befund **rot** – fail-closed im Sinne von #634, kein `|| true`, kein
`continue-on-error` – aber er liefert wieder Signal. `!cancelled()` ist das Haus-Muster:
Der letzte Schritt desselben Workflows trägt es bereits, mit derselben Begründung
(„Der Schritt läuft auch nach einem fehlgeschlagenen Testlauf: Gerade dann ist die
Frage interessant, ob das Buch sauber geblieben ist").

Festgenagelt durch **C34 h)**: Fehlt der Bedingungsausdruck am Suite-Schritt, wird die
Regel rot. Sabotage-Probe (f) im Selbsttest entfernt ihn und verlangt den Befund.

---

## 3. Dauerhafte Änderungen

### (a) Haus-Templates werden aus der Quelle abgeleitet – und per AST gelesen

`scripts/duplikat_guard.py`: `_HAUS_CTA_REGISTER`, `haus_formeln()`, `haus_texte()`,
`haus_cta_register()`, `ist_haus_cta()`, `haus_template_grund()` als einzelner Einstieg.
Quellen (`HAUS_TEXT_QUELLEN`): `ki_shared.DISCLAIMER`, `cta_builder.END_DISCLOSURE`,
`cta_builder._END_SATZ_FALLBACK`, `news_writer.STAND_INTRO` (Formel mit `{today}`),
dazu das CTA-Register aus `affiliate_intent_contract.ZIELE`.

Zwei Entscheidungen, die tragen:

- **Normalisierung über `affiliate_intent_contract.norm()`** – dieselbe Vergleichsform
  wie die Intent-Wache. Damit ist U+2011 kein Unsichtbarkeitsgrund mehr, und beide
  Wachen sehen denselben Text (`_vergleichsform()`).
- **`_ssot_wert()` liest per `ast`, nicht per `import`.** `ki_shared`, `cta_builder` und
  `news_writer` ziehen PyYAML nach. Mit Import wäre die Ausnahme in jeder pyyaml-freien
  Umgebung (PR-Pfad, C6-Selbsttest, lokale Probe) **still** ausgefallen: Die Wache misst
  dann Haus-Format wieder als Plagiat, und #676 kehrt als Dauer-Fehlalarm zurück.
  Eine nicht lesbare Quelle ist darum ein Werkzeugfehler, kein Verzicht –
  `haus_template_luecken()` meldet sie, `main()` beendet mit **Exit 2** (fail-closed).

Kein Freibrief: `ist_haus_cta()` verlangt einen internen `/go/`-Link **und** vollständige
Deckung des Fließtextes durch registrierte Sätze/Anker. Ein einziger eigener
Redaktionssatz hebt die Ausnahme auf. Und jede Ausnahme ist **sichtbar** –
`haus_template_grund()` nennt die Quelle im Report (eine stille Ausnahme wäre
Scheingrün, Lektion #521 / C19).

Die Whitelist-Idee wurde bewusst verworfen: Sie hätte denselben Widerspruch beim
nächsten Partner neu erzeugt.

### (b) Blockiert heißt isoliert, nicht gestoppt

`scripts/release_isolation.py` (neu): nimmt blockierte Kandidaten aus der Auslieferung,
füllt die Quote nach, baut neu und misst nach – in begrenzten Runden.

- `park_state.hold()` – **nie** `park()`; Frontmatter-only, mit `cadence_grund`, der die
  Check-ID und #676 nennt. Der Grund steht damit im Artikel, nicht nur im Log.
- `publication_release.refill_until_min(finalize=False)` – Quote nachfüllen ohne
  Vorwegnahme der Entscheidung.
- `neu_bauen()` → `hugo --minify --destination public` (`FF_ISOLATION_OHNE_BUILD=1`
  überspringt den Bau für Proben).
- **Eine Messregel:** `verdict()` delegiert an `release_scorecard` und reicht dessen
  Exit-Code unverändert durch. Keine zweite Ampel (Lektion #521).
- Bei **Werkzeugfehler greift die Isolation bewusst nicht** – sie würde sonst auf einer
  Messung handeln, die nichts gemessen hat (C33).
- Grenzen: `--runden` (Default 3), `MAX_ISOLATIONEN_PRO_LAUF = 6`.
- Exit-Vertrag: `0` ausgeliefert · `1` weiterhin blockiert · `2` Werkzeugfehler.

Verdrahtung in `.github/workflows/deploy.yml` (Z. 667–680): Selbsttest zuerst, dann
`--commit-sha "$GITHUB_SHA" --runden 3`, Exit-Code wird durchgereicht. Der Schritt steht
**vor** Heal-Diff/Rebuild; die Scorecard bleibt bei Z. 787 der harte Endpunkt.
Kein `|| true`, kein `continue-on-error`.

### (c) Der Alarm nennt die Ursache

`scripts/bot_watchdog.py`: `DEPLOY_WORKFLOW` und `deploy_ausfall_spur()` ergänzen den
`live-site`-Fund um `laeufe_fehlend`, `job`, `schritt`, `lauf_id` – plus den Hinweis,
dass ein Catchup denselben Fehlschlag wiederholt. Offline-/`gh`-Fehler sind **kein**
Befund: Die Funktion liefert dann `None`, und der Aufrufer fällt auf die allgemeine
Formulierung zurück (kein erfundener Schuldiger, C2).

Live-Beweis am 09.10.2026, 17:03 UTC-Fenster:

```json
{"laeufe_fehlend": 13, "job": "deploy",
 "schritt": "Release-Scorecard (Produktionswahrheit versiegeln, fail-closed)",
 "lauf_id": 37963585911}
```

Gegenprobe nach der Entwarnung: `deploy.yml` → `None` (nichts zu melden), während
`release-scorecard.yml` weiterhin korrekt `{"laeufe_fehlend": 1, …}` liefert. Die Spur
schweigt also, wenn nichts fehlt, und rät nie.

### (d) Messregel repariert

`scripts/release_scorecard.py`: `je_dimension` / `befundliste` werden jetzt **vor** der
Schleife für nicht deklarierte Check-IDs initialisiert. Ein nicht deklarierter Check ist
damit ein Befund (`dimension: technik`, „Check `X` ist in der SSOT nicht deklariert“)
statt eines Tracebacks.

### (e) Inhalt geheilt, nicht ausgenommen

Der § 56 TKG-Absatz in
`content/posts/2026-10-07-dsl-anbieter-wechseln-warum-treue-dich-bares-geld-kostet/index.md`
war eine echte Near-Duplicate – er wurde **artikel-spezifisch umgeschrieben**
(hemingway ✅100, Flesch 63.0), nicht auf eine Ausnahmeliste gesetzt.

---

## 4. Zusammenspiel mit WF-54C4/#674 (PR #677)

Der Freeze selbst wurde am 09.10. um 17:45/18:13 UTC durch den parallelen Vorgang
**#674/#677** beendet (`fix(publication): gleiche Redundanz-Messung vor dem Deploy`,
Commit `b9a8b01`). Dieser Vorgang behauptet **nicht**, die Seite wieder live gebracht zu
haben – er schließt die **Klasse**, die den Freeze erzeugt hat.

Beide Änderungen greifen ineinander, statt sich zu überschneiden:

- `publish_gate.duplicate_failures()` (neu in #677) ruft `duplikat_guard.check_article`
  und `check_cross`. Die Haus-Template-Ausnahme aus (a) wirkt damit **durch den neuen
  Pfad hindurch** – Scorecard und Publish-Gate messen dieselbe Wahrheit, und die
  Fehlklassifikation verschwindet an der Quelle.
- #677 machte `root` in `check_article`/`load_blocks`/`check_cross` injizierbar. Genau
  diesen Parameter nutzen die neuen Regressionstests; das frühere `patch.object(dg,
  "ROOT", …)` wirkt seit #677 nicht mehr, weil `ROOT` als Default-Argument gebunden ist.
- Unterschiedlicher Fokus: #677 beseitigt die **zweite Messung** (ein Kandidat konnte
  das Gate passieren und nach dem Build an einer anderen Messung scheitern). Dieser
  Vorgang begrenzt den **Blustradius** (ein blockierter Kandidat darf nicht die
  Auslieferung aller anderen stoppen) und die **Fehlklassifikation** von Haus-Format.

Der Rebase auf `main` (`c167aac`) lief konfliktfrei; beide Schichten sind im Ergebnis
nachweislich vorhanden und gemeinsam grün (siehe §5).

---

## 5. Nachweise

| Prüfung | Befehl | Ergebnis |
|---|---|---|
| Duplikat-Audit, ganzer Bestand | `python3 scripts/duplikat_guard.py` | `75 Artikel · D1 0 · D2 0 · D3 0 · D4 0 · D5 0 · D6 0` – ✅ keine Duplikate |
| Messung vor/nach (a) | dito, Zwischenstände je Schicht | `D3 2 · D4 11` → `D3 0 · D4 2` → `D4 1` → **`D1–D6 = 0`** |
| Selbsttest Duplikat-Wache | `python3 scripts/duplikat_guard.py --selftest` | ✅ **14 Fälle** grün, Exit 0 |
| Selbsttest Isolation | `python3 scripts/release_isolation.py --selftest` | ✅ **ST1–ST9** grün, Exit 0 |
| Selbsttest Scorecard | `.venv/bin/python scripts/release_scorecard.py --selftest` | ✅ grün, Exit 0 |
| Regressionstests | `python3 -m unittest scripts.tests.test_duplikat_guard scripts.tests.test_release_isolation` | ✅ **44 Tests** (23 + 21) |
| Tests inkl. #674/#677 | `… test_publish_gate_duplicates test_release_scorecard` | ✅ **89 Tests** grün |
| Abhängigkeitsfreiheit | beide Selbsttests mit **System-`python3` ohne PyYAML** | ✅ Exit 0 (vor der AST-Lesart: Exit 2) |
| Governance-Selftest | `.venv/bin/python scripts/governance_contract.py --selftest` | ✅ **C1–C34** mit Kunstbefunden, Exit 0 |
| Governance-Vertrag (CI-Form) | `… --quick` | ✅ „alle 32 Regeln prüfen in beide Richtungen“, Exit 0 |
| Governance-Vertrag (voll, C6 führt jede Wache aus) | `scripts/governance_contract.py` | ✅ Exit 0 |
| Manifest-Wache | `.venv/bin/python scripts/manifest_guard.py` | ✅ GRÜN, Exit 0 |
| Ausfallspur live | `bot_watchdog.deploy_ausfall_spur()` | ✅ 13 Fehlschläge, Job/Schritt/Run-ID benannt |
| Siegel-Unversehrtheit | Abgleich `data/integrity_lock.json` | ✅ keine der 12 Dateien ist versiegelt |

**Der Dauertest gegen die Klasse #676:** `test_cta_vertrag_und_duplikatwache_einig` baut
für **jede** Route in `affiliate_intent_contract.ZIELE` × 3 Slugs den echten End-Block
über `cta_builder` und verlangt, dass jeder Absatz als Haus-Template erkannt wird.
`test_neue_route_waere_automatisch_erfasst` legt eine Route an, die es heute nicht gibt,
verwirft den Cache und verlangt dieselbe Erkennung – Beweis, dass die Ausnahme mit der
SSOT mitwächst und nicht nachgepflegt werden muss.
`VertragsCtaTests` liefert denselben Kernbeweis **ohne PyYAML**, damit er auch im
PR-Gate läuft; die `cta_builder`-Variante wird dort mit Grund übersprungen, nie still.

---

## 6. Neue Governance-Regel C34 „Blustradius eines Befunds“

`scripts/governance_contract.py` friert die Klasse in beide Richtungen (Fehler **und**
Schein-Sicherheit). Geprüft werden:

| # | Bedingung |
|---|---|
| a | Isolations-Bausteine vorhanden; `park_state.park(` in der Isolation **verboten** |
| b | Messung läuft über `release_scorecard` – keine zweite Ampel |
| c | `EXIT_WERKZEUGFEHLER` existiert (Unterscheidung Befund ≠ Messausfall) |
| d | `deploy.yml`: Isolation **vor** `Release-Scorecard (Produktionswahrheit versiegeln`, kein `|| true`/`continue-on-error` in der Zeile, `exit "$iso"` vorhanden |
| e | `bot_watchdog.py` enthält `deploy_ausfall_spur` **und** `DEPLOY_SCHRITT` |
| f | `duplikat_guard.py` enthält `affiliate_intent_contract`, `haus_template_grund`, `news_writer`; `news_writer.py` enthält `STAND_INTRO` |
| g | beide Wachen in `GUARDS`, `scripts/tests/test_<name>.py` vorhanden, Runbook vorhanden |
| h | `publication-reliability-tests.yml`: die vollständige Unit-Test-Suite läuft auch nach einem Fehlschlag davor (`!cancelled()`) – ein Daten-Befund schaltet die Code-Prüfung nicht aus (U5) |

Beide neuen Wachen (`release_isolation.py`, `duplikat_guard.py`) stehen jetzt in
`GUARDS` und werden von **C6** ausgeführt. Der Selbsttest sabotiert die Regel sechsmal
(`hold`→`park`, Isolation hinter den End-Gate verschoben, `|| true` angehängt,
SSOT-Ableitung→Whitelist, Ausfallspur umbenannt) und verlangt, dass jeder Sabotage-Akt
rot wird.

Regeltext und Label: `RULE_TEXT["C34"]`, `LABEL["C34"]`.

---

## 6b. Folge der Inhaltsheilung: Reserve-Zertifikat muss nachgezogen werden

Die Heilung aus (e) ändert den Entwurf von
`2026-10-07-dsl-anbieter-wechseln-…`. Damit passt der hinterlegte SHA-256 im
Reserve-Snapshot nicht mehr, und `scripts/reserve_artifacts.py --check` meldet
`Nachzertifizierung nötig`. Das ist **gewollt** und kein Fehler: Ein Zertifikat,
das über einen Text ausgestellt wurde, den es nicht mehr gibt, wäre ein
gefälschter Nachweis.

Nachzertifizieren darf nur die vollständige Messkette – `reserve_recert.gate_verfuegbar()`
verlangt `hugo` **und** `hunspell` (ohne hunspell wertet `quality_score` die
Rechtschreibung als „unbekannt" = 0.5 und drückt jeden Artikel um bis zu 0.10
unter die 0.85-Schwelle: ein Werkzeugmangel, der wie ein Qualitätsproblem
aussähe). Deshalb ist dieser Schritt lokal nicht ausführbar und läuft
ausschließlich über die sanktionierten Ketten:

| Kette | Auslöser | Schritt |
|---|---|---|
| `bot-watchdog.yml` | cron `30 8 * * *` + `workflow_dispatch` | „Reserve-Zertifikat nachziehen (#462)": `reserve_snapshot_heiler.py --fix` → `reserve_recert.py --fix` → `git_sync.sh` auf `data/reserve-*.json` |
| `content-reserve.yml` | cron `25 3 * * *` + `workflow_dispatch` | Stufe 3 Zertifizierung: `reserve_readiness.py` |
| `reserve-nachweis.yml` | `workflow_dispatch` | `reserve_readiness.py` |

**Vorbestehend, nicht aus diesem Vorgang:** Derselbe Check meldet auf `main`
(`c167aac`) bereits `2026-10-07-campingurlaub-2026-…: SHA-256 passt nicht mehr` –
nachgewiesen in einem sauberen Worktree von `origin/main`. Genau dieser Artikel
ist der 404-Auslöser aus #676; sein Zertifikat war schon vor diesem Vorgang
alt. Die PR-Prüfung `regression` ist deshalb auf der aktuellen Basis rot
(die letzten drei gemergten PRs #677, #680, #681 ebenfalls, je
`regression: FAILURE`); dieser Vorgang fügt ihr einen zweiten, nach dem Merge
automatisch heilenden Eintrag hinzu und behebt den ersten nicht.

---

## 7. Was bewusst NICHT geändert wurde

- **Kein `|| true`, kein `continue-on-error`** an Scorecard oder Isolation. Fail-closed
  bleibt fail-closed; geändert wurde nur, *was* ein Fehlschlag blockiert (ein Artikel
  statt der Seite).
- **D3/D4 bleiben report-only.** Zwei Artikel dürfen sich legitime Formulierungen
  teilen; der Heilweg läuft über die Redaktion. Die Ausnahme gilt ausschließlich für
  nachweisbare Haus-Templates.
- **`publish_gate.py`-Quarantänesemantik unverändert.** Die dort dokumentierte
  Betriebsregel (ein blockierter Artikel wird nicht auf `draft` zurückgesetzt) gilt
  weiter; die Isolation nutzt `hold()` mit `cadence_grund`, nicht `park()`.
- **Keine Ausnahmeliste für Gesetzestexte.** Der § 56 TKG-Absatz wurde umgeschrieben,
  nicht freigegeben – eine Zitier-Ausnahme wäre ein Freibrief für Copy-Paste.
- **Pinterest-Kanal untouched.** Domain-Sperre und toter Token sind `pinterest-parked`
  und gehören einem Menschen; sie stehen ausdrücklich nicht in diesem Ticket.
- **Kein Live-HTTP-Test aus dieser Umgebung.** `franksfinanzcheck.de` ist aus dem
  Arbeitskontext nicht erreichbar (Namensliste); der Beweis für das Ende des Freeze
  stammt aus den Actions-Läufen (`37968526680`, Job `pages-deployment` 18:13:37Z),
  nicht aus einem eigenen Request.

---

## 8. Betriebsabnahme

```bash
npm run release:isolation        # Trockenlauf: was würde isoliert?
npm run release:isolation:probe  # eine Runde, echt
npm run test:isolation           # Selbsttest + 21 Regressionstests
npm run duplikate:check          # Vollaudit über den Bestand
npm run test:duplikate           # Selbsttest + 23 Regressionstests
```

**Triage-Reihenfolge bei „neuester Artikel nicht live“** (Runbook
`docs/ANLEITUNG-AUSLIEFERUNGS-ISOLATION.md`):

1. `deploy.yml`-Lauf: welcher **Schritt** ist rot? (Nicht: ob rot.)
2. Steht im Fund ein `cadence_grund` mit Check-ID? → Der Artikel ist isoliert, die
   Seite ist live. Das ist der Soll-Zustand nach dieser Reparatur.
3. `RELEASE-SCORECARD.md` + `data/release_scorecard.yaml`: Ist der Check `blockiert`
   und `entscheidung: auto`, aber ohne Heilweg? Dann ist es ein Dauerblocker – Klasse
   #676.
4. Erst danach: Catchup. Ein Catchup ohne Schritt-Diagnose wiederholt den Fehlschlag.

---

## 9. Dateien

**Neu**

- `scripts/release_isolation.py` – Isolation blockierter Kandidaten, Exit 0/1/2
- `scripts/tests/test_release_isolation.py` – 21 Tests
- `scripts/tests/test_duplikat_guard.py` – 23 Tests (2 nur mit PyYAML)
- `docs/ANLEITUNG-AUSLIEFERUNGS-ISOLATION.md` – Runbook
- `BOT-WATCHDOG-676-DAUERHEILUNG-PREMIUM-2026-10-09.md` – dieser Bericht

**Geändert**

- `scripts/duplikat_guard.py` – Haus-Templates aus der SSOT, AST-Lesart,
  `haus_template_luecken()`, Exit 2 bei Lücke, Selbsttest 12 → 14 Fälle
- `scripts/release_scorecard.py` – `NameError` in `bewerte_artikel()` behoben
- `scripts/bot_watchdog.py` – `deploy_ausfall_spur()`, `DEPLOY_SCHRITT`, attribuiert
- `scripts/news_writer.py` – `STAND_INTRO` als benannte Haus-Formel-Quelle
- `.github/workflows/deploy.yml` – Isolations-Schritt (Z. 667–680), Scorecard-Schritt
  mit `set -uo pipefail`, `::error title=…`, `exit "$status"`
- `.github/workflows/publication-reliability-tests.yml` – vier Prüf-Schritte mit
  `if: ${{ !cancelled() }}`: ein Daten-Befund schaltet die einzige vollständige
  Unit-Test-Ausführung des Repos nicht mehr aus (U5)
- `scripts/governance_contract.py` – Regel **C34**, zwei neue `GUARDS`-Einträge,
  `LABEL`/`RULE_TEXT`, sechs Sabotage-Proben
- `CLAUDE.md` – Abschnitt „Ein Befund darf nicht die ganze Seite einfrieren (C34)“
- `package.json` – fünf npm-Skripte
- `content/posts/2026-10-07-dsl-anbieter-wechseln-…/index.md` – § 56 TKG-Absatz
  artikel-spezifisch umgeschrieben
