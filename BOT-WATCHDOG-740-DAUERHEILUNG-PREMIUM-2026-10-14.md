# Bot-Watchdog #740: Ein fehlendes Wörterbuch brach die Messkette – und fror die ganze Auslieferung ein

**Stand:** 14.10.2026 · **Meldung:** [#740](https://github.com/frank-hartung/franksfinanzcheck-blog/issues/740)
· **Klasse:** maschinell behebbar, Besitzer `machine/auto`, Kanal `live-site`

> **„P1 · Auslieferung blockiert (Live-Stand eingefroren)“** – Der letzte `deploy.yml`-Lauf
> endete, bevor das Pages-Artefakt hochgeladen war; blockierender Schritt:
> *„Quote-Nachfüllung nach Gate-Verlust (Re-Queue + Reserve → Min)“*. Solange das steht,
> geht kein einziger Artikel live, egal wie oft der Deploy-Catchup läuft.

## Das Urteil in einem Satz

Die öffentliche Auslieferung fror nicht an einem Inhalts-Befund ein, sondern an einer
**Messung**: An einem Publikationstag (Mi 14.10.) lag der Tag unter Minimum (0/2), die
Quote-Nachfüllung musste erstmals **Reserve-Kandidaten messen** – und der `deploy`-Job
hatte die Messkette unvollständig (kein `hunspell`), während ein doppelter
Modul-Import den Crash zusätzlich unheimlich machte: Der `ReleaseBuildCrash` kam aus
einer **zweiten Instanz** von `publication_release`, fiel durch den `except`-Haken in
`main()` und tötete den Schritt mit rohem Traceback (Exit 1) statt des Diagnose-Vertrags
(Exit 3). Der Schritt reichte seinen Exit-Code unevaluiert durch – und stellte damit die
gesamte öffentliche Auslieferung als Geisel eines kaputten Messwerkzeugs. Exakt die
Klasse, die #676 bereits für die Release-Scorecard endgültig beseitigt hatte (C34):
**erst liefern, dann siegeln.**

> **Nachtrag vom selben Tag (Teil 2, Vertrag C38):** Teil 1 hat den Schritt geheilt,
> der gebrannt hat. Die Prüfung danach zeigte, dass das nicht reicht: Von **64**
> Schritten des `deploy`-Jobs konnten **60** die öffentliche Auslieferung anhalten,
> ohne dass irgendwo stand, ob sie das dürfen. Teil 2 schließt deshalb die **Klasse**
> – Register, ein gemeinsamer Meldeweg, eine Messketten-Wache über alle Workflows –
> und hat dabei sofort einen zweiten, bis dahin unsichtbaren Fall gefunden
> (`frankautoops-report.yml` maß den gesamten Bestand täglich ohne `hunspell`).
> Details in **§8**.

---

## 1. Zeitleiste (UTC, 13./14.10.2026)

| Zeit | Ereignis | Beleg |
|---|---|---|
| 13.10. 23:18:58 | Letzter **grüner** Deploy vor dem Fenster | Run `38483490505` (`workflow_dispatch`) |
| 14.10. 01:58:53 | Erster roter Deploy des Tages, Schritt „Quote-Nachfüllung“ | Run `38498609876` (Schritt 1 s) |
| 14.10. 04:45 | Bot-Watchdog legt **#740** an (`deploy-blockade`, benannter Schritt) | Issue #740 |
| 14.10. 07:41–10:41 | Vier weitere Dispatch-Läufe rot, **derselbe Schritt** | Runs `38529938621`, `38540689253`, `38543758543`, `38544726702`, `38551364795` |
| 14.10. 11:49:46 | Einziger grüner Lauf des Tages: Quote-Nachfüllung ~1 s, **kein Kandidat gemessen** – beide 10-14-Slot-Artikel lagen im Checkout (`4769e801`) bereits `draft: true` | Run `38559331099`, Job `deploy` |
| 14.10. 11:50:39 | Der 11:49-Lauf stuft `2026-10-14-strategisch-sparen-…` selbst zurück (`cadence_grund: faktenfrische`) – Commit 11:53 | `6b2e1fde3c` |
| 14.10. 13:00–13:48 | Deploy-Catchup **und** Push-Deploys (#741, #743) wieder rot, derselbe Schritt | Runs `38568308314`, `38572586935`, `38574486376`, `38574904466` |

**10 aufeinanderfolgende Deploy-Fehlschläge** seit 01:58 UTC (einzelner grüner Lauf
11:49 ohne neue Inhalte). In diesem Fenster lieferte die öffentliche Site nichts Neues –
die letzten Live-Artikel tragen das Datum 12.10.2026.

Warum genau jetzt? An **Nicht-Publikationstagen** (So/Mo abends, Di, Sa) füllt die
Quote-Nachfüllung nichts nach und misst niemanden – die Läufe bleiben grün. Erst an einem
**Publikationstag (Mo/Mi/Fr) mit `live < Minimum`** muss sie Re-Queue- und
Reserve-Kandidaten durch die echte Qualitätsmessung jagen. Der letzte Publikationstag
davor (Mo 12.10.) stand mit 2/2 über Minimum → kein Refill → keine Messung → grün.
Mi 14.10. war der erste Tag, an dem die Messung im Deploy überhaupt anfiel – und sie
war unvollständig.

Inhalts-Zustand am Befundtag (kein Ausredendeckel, nur Vollständigkeit): Beide
Mi-Slot-Artikel lagen `draft: true` – einer mit `cadence_grund: faktenfrische`
(„Erstrecherche – noch nie faktengeprüft“), der andere ohne Rückstufung (YMYL-Prüfung
`ausstehend`). Das sind **legitime Inhalts-Gates** mit eigenem Fachkanal (Faktenfrische/
YMYL-Prüfqueue) – sie haben die Auslieferung **nicht** blockiert. Die Blockade erzeugte
ausschließlich der fehlgeschlagene Messschritt.

---

## 2. Ursachen (U1–U4)

### U1 · Die Messkette des `deploy`-Jobs war unvollständig: kein `hunspell`

`quality_score.score_article()` misst Rechtschreibung über `spellcheck`/`hunspell`.
Fehlt das Binary, trägt das Ergebnis `measurement_errors: {"spelling": "[Errno 2] No
such file or directory: 'hunspell'"}`. `accept_candidate()` behandelt eine ausgefallene
Messung strikt korrekt (C33): **keine Annahme ohne messbare Qualität** – es wirft
`ReleaseBuildCrash`.

Alle sechs Workflows, die dieselbe Messkette fahren, installieren das Paket:
`content-engine-v2.yml` (Z. 111/288), `content-reserve.yml` (Z. 251),
`kadenz-endkontrolle.yml` (Z. 42), `bot-watchdog.yml` (Z. 239),
`affiliate-integrity-daily.yml` (Z. 118), `reserve-nachweis-614.yml` (Z. 62) – jeweils
`sudo apt-get install -y -qq hunspell hunspell-de-de`. **Nur `deploy.yml`** hatte es nie.
Die Quote-Nachfüllung ist der erste Schritt im Deploy, der in einer Lage
(`Publikationstag + live < Minimum`) **jeden** Kandidaten misst – bis dahin war der
Mangel unsichtbar, weil die übrigen Deploy-Schritte keine pro-Kandidaten-Messung fahren.

### U2 · Doppelmodul-Bug: Der Crash kam aus einer zweiten `publication_release`-Instanz

Der Deploy startet das Skript als `python3 scripts/publication_release.py` → Modul
`__main__`. In `refill_to_min()` wurde `validator=None` durchgereicht, und
`reserve_pool.publish_to_min()` löste sie mit
`from publication_release import accept_candidate` auf – ein **by-name-Import**. Python
kannte in diesem Prozess `publication_release` noch nicht als Modul, also baute es eine
**zweite Instanz** des Skripts mit **eigener `ReleaseBuildCrash`-Klasse**. Der dort
geworfene Crash ist **keine Instanz** der Klasse, die `main()` im `except`-Haken erwartet
– er entkam ihm:

```
File "scripts/publication_release.py", line 263, in accept_candidate
    raise ReleaseBuildCrash(f"Qualitätsmessung ausgefallen: {result['measurement_errors']}")
publication_release.ReleaseBuildCrash: Qualitätsmessung ausgefallen:
    {'spelling': "[Errno 2] No such file or directory: 'hunspell'"}
```

Resultat: roher Traceback, **Exit 1** (nicht der Exit-3-Vertrag, keine benannte
Ursache), Schritt tot. `main()` hätte nach dem Vertrag (0 = ok · 1 = Defizit ·
3 = Release-Crash) eine strukturierte Diagnose mit Exit 3 liefern müssen.

Reproduziert 1:1 auf dem Befundstand (`ea26e0f`, identische Blobs in allen 10 roten
Läufen: `publication_release.py` = `d44aeb2`, `deploy.yml` = `bcfc90a`):
`python3 scripts/publication_release.py --refill-only` → derselbe Traceback, Exit 1.

### U3 · Der Schritt reichte Exit-Codes unevaluiert durch – Geiselhaltung (Klasse #676)

```yaml
- name: Quote-Nachfüllung nach Gate-Verlust (Re-Queue + Reserve → Min)
  run: |
    python3 scripts/publication_release.py --selftest
    python3 scripts/publication_release.py --refill-only
```

Jeder Fehlexit brach den Job **vor** `upload-pages-artifact` ab; `pages-deployment`
lief nie. Der Blustradius war damit dieselbe Größe wie beim Scorecard-Befund #676:
**ein kaputtes Messwerkzeug fror 42+ Live-Artikel ein.** Der Scorecard-Schritt trug
seit #676 die Exit-Auswertung (`0 → weiter · 1 → harter Stopp · 2 → Werkzeugfehler:
liefern, dann siegeln rot`) – der Quote-Schritt war nie nachgezogen worden, weil er
bisher praktisch nie gemessen hatte (U1 erst jetzt relevant).

### U4 · Nebenbefund: Diagnose gab es nur für den Build-Crash

Der `except ReleaseBuildCrash`-Haken in `main()` nahm an, `build_site()` hätte „bereits
strukturiert diagnostiziert“. Für den anderen Crash-Pfad (Qualitätsmessung, Gate-
Werkzeug) stand **nichts** im Log – ein Crash via Re-Queue-Pfad (dort wirft
`accept_candidate` aus `__main__` selbst und wird auch vor dem Doppelmodul-Bug
gefangen) endete **stumm** mit Exit 3. Ein roter Schritt, der die Ursache nicht nennt,
erzieht zum Wegsehen (WF-A535 #529, Lektion vom 02.10.2026).

---

## 3. Dauerhafte Änderungen

### (a) Die Messkette ist im `deploy`-Job vollständig

`.github/workflows/deploy.yml`, Schritt „Py-Abhängigkeiten für Gate-Chain“ (läuft vor
allen Gates): `sudo apt-get install -y -qq hunspell hunspell-de-de` – dieselbe Zeile,
dieselbe Reihenfolge wie in den sechs Schwester-Workflows. Fail-fast ohne `|| true`:
Ein nicht installierbares Paket ist ein lauter Werkzeugbefund, kein stiller
Messverzicht.

### (b) Ein Crash ist ein Crash, egal über welchen Pfad er kommt

`scripts/publication_release.py`:

- **`__main__`-Block registriert den Alias**
  `sys.modules['publication_release'] = sys.modules[__name__]` **vor** `main()`.
  Jeder by-name-Import (so macht ihn `reserve_pool`) liefert von jetzt an dieselbe
  Instanz – dieselbe `ReleaseBuildCrash`-Klasse, denselben `except`-Haken.
- **`refill_to_min()` löst den Validator explizit aus**
  `validator = validator or accept_candidate` – aus diesem Prozess. Der
  Import-Fallback in `reserve_pool` feuert auf dem Refill-Pfad nie mehr.
  (Zwei Schichten, eine Absicht: Die zweite schont Umgebungen, in denen der
  Alias aus einem anderen Grund fehlt.)
- **`main()` benennt die Ursache für JEDEN Crash-Pfad:**
  `Ursache: <Exception>` plus die Klassen-Trennung „KEIN Tagesdefizit (Exit 1)“ –
  die Build-Diagnose von `build_site()` bleibt, dazu kommt jetzt die lückenlose
  Schlusszeile (U4).

### (c) Der Schritt bewertet seinen Exit-Code – C34-Muster, kein `|| true`

`.github/workflows/deploy.yml`, Schritt „Quote-Nachfüllung nach Gate-Verlust“
(`id: quote_refill`), exakt die Auswertung des Scorecard-Schritts:

| Exit | Bedeutung | Reaktion |
|---|---|---|
| `0` | Quote gefüllt oder nichts zu tun | weiter; Defizite bleiben über `publication_check`/Endkontrolle rot (#287-Vertrag, unverändert) |
| `3` | Release-Crash (Mess-/Werkzeugfehler) | `::error::` + Job-Output `werkzeugfehler=true`, **Auslieferung läuft weiter**, Lauf wird **nach** der Veröffentlichung im Job `release-seal` rot |
| sonst | unerwartet | gleiche Behandlung: laut, nie Geisel |
| Selbsttest `≠0` | Refill-Vertrag rot | Refill wird übersprungen, Auslieferung läuft weiter, Siegel rot |

Kein `continue-on-error`, kein `|| true` – der Exit-Code wird **ausgewertet**, der
Befund bleibt `::error::`-Annotation und Job-Output.

### (d) Das Siegel kennt den Befund

`deploy`-Job-Output `refill_werkzeugfehler`; Job `release-seal` liest
`REFILL_WERKZEUGFEHLER`, trägt ihn in die Siegel-Tabelle und macht den Lauf rot –
**nach** der Veröffentlichung. `release-seal` bleibt bewusst kein `needs`-Vorlauf von
`pages-deployment` (C34: Das Siegel blockiert die Auslieferung nicht.)

### (e) Regressionstests: Die Klasse ist festgenagelt

- `scripts/publication_release.py --selftest`, neue Sektionen 4–6 (laufen in CI als
  erste Zeile des Schritts): **Modul-Identität** des by-name-Imports, **Crash-Vertrag
  über den Import-Pfad** (`main()` → Exit 3, nie roher Traceback) und
  **Validator-Wiring** (Sentinel beweist, dass der lokale Validator die Kandidaten
  prüft).
- `scripts/tests/test_publication_release_wache.py`:
  - `DoppelmodulRegressionTests` – Identität (Modul + Klasse), **Produktionsaufruf
    `python3 scripts/…` im Subprozess** (hält den `__main__`-Pfad als Ganzes),
    Crash-Diagnose mit benannter Ursache.
  - `DeployQuoteRefillVerdrahtungTests` – deploy.yml trägt die Messkette (hunspell),
    der Schritt wertet den Exit-Code aus, enthält **kein `exit 1`**, gibt den
    Befund nach außen, und `release-seal` wertet ihn rot.
- Verifiziert: Suite `python3 -m unittest discover -s scripts/tests` (3060 Tests – die
  3 verbliebenen Fehler sind Vorbestand auf `main`, nachgewiesen auf cleanem
  Worktree, siehe §5), Uhr-Probe `selftest_clock.py --trap-discover` (Offset 97 d)
  grün für die neuen Tests, `test_workflow_yaml` + `test_deploy_publication_priority`
  grün (YAML gültig, keine doppelten Schlüssel, #676-Vertrag intakt).

---

## 4. Nachweise

| Prüfung | Befehl | Ergebnis |
|---|---|---|
| Reproduktion des Befunds (vor der Heilung, Stand `ea26e0f`) | `python3 scripts/publication_release.py --refill-only` | 🔴 roher Traceback, **Exit 1** – identisch zum CI-Mechanismus (Blobs aller 10 roten Läufe verglichen: `publication_release.py` = `d44aeb2`, `deploy.yml` = `bcfc90a`) |
| Heilung, Crash-Pfad (ohne Messkette) | dito, nach der Heilung | ✅ **Exit 3** + `Ursache: Qualitätsmessung ausgefallen: {'spelling': "…'hunspell'"}` + „KEIN Tagesdefizit“ – kein Traceback |
| Selbsttest im Produktionsmodus | `python3 scripts/publication_release.py --selftest` | ✅ grün, Exit 0 (Sektionen 1–6 inkl. #740-Modul-Identität) |
| Schrittblock 1:1 (Crash-Zweig) | `deploy.yml`-`run`-Block verbatim mit `GITHUB_OUTPUT` | ✅ **Schritt-Exit 0** (Deploy fährt weiter), `werkzeugfehler=true` geschrieben, `::error::` benannt |
| Schrittblock 1:1 (Selbsttest-Zweig) | dito, simulierter Selbsttest-Abbruch | ✅ Schritt-Exit 0, `werkzeugfehler=true`, `::error::` benannt |
| Workflow-YAML (Haus-Wache) | `python3 -m unittest scripts.tests.test_workflow_yaml` | ✅ gültig, keine doppelten Schlüssel |
| #676-Vertrag intakt | `python3 -m unittest scripts.tests.test_deploy_publication_priority` | ✅ 17 Tests (Scorecard-Zweige, Artefakt-Position, Siegel-Job) |
| Neue Regressionstests | `python3 -m unittest scripts.tests.test_publication_release_wache` | ✅ **20 Tests** |
| Gesamtsuite | `python3 -m unittest discover -s scripts/tests` | 3060 Tests, **0 neue Fehler** (3 Vorbestand, §5) |
| Zeitbombe-Schutz (Uhr +97 d) | `scripts/selftest_clock.py --trap-discover scripts/tests --offset 97` | neue Tests grün (nur die 3 Vorbestands-Fehler, identisch) |

---

## 5. Was bewusst NICHT geändert wurde

- **Kein `|| true`, kein `continue-on-error`, keine Exit-Code-Verschiebung im
  Skript.** Der Vertrag `0 = ok · 1 = Defizit · 3 = Release-Crash` bleibt
  unverändert; neu ist nur, dass der Crash jetzt **zuverlässig** Exit 3 ist (U2) und
  der Workflow den Exit **auswertet** statt durchzureichen (U3) – dasselbe, was #676
  für die Scorecard beschlossen hat.
- **Inhalts-Gates bleiben hart.** Die Faktenfrische- und YMYL-Prüfung der
  10-14-Slot-Artikel ist ein legitimer Fachbefund mit eigenem Kanal
  (Faktenfrische-Wache, YMYL-Prüfqueue). Es wurde **kein** Artikel manuell auf
  `draft: false` geflippt und keine Gate-Schwelle bewegt. Wenn nach der Heilung
  weniger als 2/2 aus der Reserve gehen, ist das ein ehrliches Defizit – es bleibt
  über `publication_check`/Endkontrolle rot und läuft in seinen Fachkanal.
- **Der Bot-Watchdog ist unverändert.** Er hat gemessen, den Schritt benannt, den
  Meldetakt an den Ausfall gebunden und zum Catchup gerufen, der den Fehlschlag
  wiederholte (U3-Anteil von #676) – genau das korrekte Verhalten. Das Ticket
  schließt sich selbst, sobald die Nachmessung (stündlich :05) die
  Artefakt-/Pages-Auslieferung grün sieht.
- **`release-seal` blockiert nichts.** Neue Zeile im Siegel, aber derselbe Platz im
  Graph: nach `pages-deployment`, nie davor (C34).
- **Kein manuelles Triggern aus dieser Umgebung.** Der Beweis für das Ende der
  Blockade stammt aus den nächsten `deploy.yml`-Läufen (Push dieses PRs / nächster
  Catchup), nicht aus einer eigenen Anfrage.

**Vorbestand, nicht aus diesem Vorgang heilbar (nachgewiesen auf cleanem
`main`-Worktree, ohne jede Änderung dieses PRs rot – Stand nach Teil 2:
2 Fehler):**

| Test | Befund | Warum nicht hier geheilt |
|---|---|---|
| `test_reserve_artifacts` | `2026-10-07-wie-smart-home-geraete-…` und `2026-10-09-balkonkraftwerk-foerderung-…`: SHA-256 passt nicht mehr zum Entwurf | Nachzertifizierung läuft über `scripts/reserve_recert.py` – und die misst Rechtschreibung. In dieser Umgebung ist `hunspell` nicht installierbar; eine Zertifizierung ohne Messung wäre genau das Scheingrün, das dieser Vorgang abschafft. Gehört in `content-reserve.yml` (dort ist die Messkette vollständig). |
| `test_social_autopilot` | `2026-08-26-dns-server-wechseln-…` hat für Instagram keinen sendbaren Winkel | Inhaltsbefund der #716-Familie mit eigenem Fachkanal – kein Werkzeugfehler. |

Beide sind **Daten-**, keine Code-Befunde; kein Test wurde stummgeschaltet.

---

## 6. Betriebsabnahme

```bash
# Teil 1 – der geheilte Schritt
python3 scripts/publication_release.py --selftest          # Vertrag inkl. Sektionen 4–6
python3 -m unittest scripts.tests.test_publication_release_wache -v
python3 -m unittest scripts.tests.test_deploy_publication_priority scripts.tests.test_workflow_yaml -v

# Teil 2 – die geschlossene Klasse (C38)
python3 scripts/blustradius_register.py --check            # jeder Deploy-Schritt deklariert
python3 scripts/blustradius_register.py --tabelle          # Klassenübersicht zum Mitlesen
python3 scripts/blustradius_register.py --selftest
python3 scripts/werkzeugbefund.py --selftest
python3 scripts/measurement_chain.py --audit-workflows     # misst jemand ohne Werkzeug?
python3 scripts/measurement_chain.py --selftest
python3 -m unittest scripts.tests.test_blustradius_register \
                    scripts.tests.test_measurement_chain \
                    scripts.tests.test_werkzeugbefund -v
python3 scripts/governance_contract.py --selftest          # C1–C38 mit Kunstbefunden

# Gesamtlauf
python3 -m unittest discover -s scripts/tests              # Gesamtsuite (publication-reliability-tests.yml)
python3 scripts/selftest_clock.py --trap-discover scripts/tests --offset 97   # Uhr-Probe
```

**Triage-Reihenfolge bei „Auslieferung blockiert (Live-Stand eingefroren)“:**

1. `deploy.yml`-Lauf: welcher **Schritt** ist rot? (Der Watchdog benennt ihn seit
   #676 – hier: „Quote-Nachfüllung nach Gate-Verlust“.)
2. Steht im Schritt-Log `Ursache: …` (Release-Crash-Diagnose)? → Mess-/Werkzeugbefund:
   Die Auslieferung läuft weiter, das Siegel ist rot. **Nicht** in die Kette
   dispatchen, bis das Messwerkzeug steht.
3. Steht dort `Qualitätsmessung ausgefallen: {'spelling': …}`? → Messkette prüfen
   (`hunspell` in der „Py-Abhängigkeiten“-Zeile), nicht den Content.
4. Steht dort ein Gate-Befund mit `cadence_grund`/Check-ID? → Inhaltsbefund: harter
   Stopp ist korrekt, Fachkanal zuständig.
5. Erst danach Catchup – und nur in eine Kette, deren blockierender Schritt bekannt
   und geheilt ist (C34: ein Catchup in eine blockierte Kette wiederholt den
   Fehlschlag).

---

## 7. Dateien

**Neu**

- `BOT-WATCHDOG-740-DAUERHEILUNG-PREMIUM-2026-10-14.md` – dieser Bericht

**Geändert**

- `scripts/publication_release.py` – `__main__`-Alias (Doppelmodul-Schutz),
  explizite Validator-Auflösung in `refill_to_min()`, Ursache-Nennung für alle
  Crash-Pfade in `main()`, Selftest-Sektionen 4–6 (Modul-Identität,
  Import-Pfad-Crash, Validator-Wiring)
- `.github/workflows/deploy.yml` – `hunspell` in der Py-Abhängigkeits-Zeile,
  Quote-Nachfüllung-Schritt mit `id: quote_refill` und Exit-Auswertung
  (`werkzeugfehler`-Output, kein `exit 1`), Job-Output `refill_werkzeugfehler`,
  `release-seal` wertet den Befund rot (Tabelle + `::error::`)
- `scripts/tests/test_publication_release_wache.py` – `DoppelmodulRegressionTests`
  (3 Tests, inkl. Produktionsaufruf im Subprozess) +
  `DeployQuoteRefillVerdrahtungTests` (4 Tests)
- `CLAUDE.md` – Leitplanke „Eine Messkette gehört in jeden Lauf, der misst, und ein
  Crash ist ein Crash (Dauerheilung #740)“

---

## 8. Teil 2 – Die Klasse schließen (Vertrag C38)

### 8.1 Warum Teil 1 nicht reicht

Teil 1 hat den Schritt geheilt, der gebrannt hat: `hunspell` in den Job, Crash als
Crash, Exit-Code auswerten, Werkzeugbefund ans Siegel. Das war richtig – und zu
klein. Die Prüfung danach stellte eine unangenehme Frage:

> Wie viele andere Schritte im `deploy`-Job können dasselbe tun?

Die Antwort: **60 von 64**. Sie konnten die öffentliche Auslieferung anhalten, und
nirgendwo stand, ob sie das dürfen. Das ist exakt die Lage vom 09.10. (#676) und vom
14.10. (#740) – zweimal dieselbe Klasse, zweimal eine Einzelfallheilung. Wer so
heilt, baut eine Warteschlange: Der nächste Mess-Schritt, der an einem fehlenden
Paket stirbt, friert die Seite wieder ein, und der nächste Bericht beginnt wieder
mit „zehn rote Läufe".

Zwei Konstruktionsfehler erzeugen diese Klasse immer wieder:

1. **Die Erlaubnis zu blockieren war implizit.** Sie ergab sich daraus, ob jemand
   an `set +e` und eine `case`-Auswertung gedacht hatte – nicht aus einer
   Entscheidung. Eine Erlaubnis, die man vergessen kann, ist keine.
2. **Jeder Melder war handgemacht.** Nach #676 gab es `scorecard.werkzeugfehler`,
   nach Teil 1 zusätzlich `quote_refill.werkzeugfehler`. Beim dritten Schritt wäre
   ein drittes Output entstanden, beim vierten ein viertes – und irgendwann eines,
   das niemand ans Siegel verdrahtet. Copy-Paste ist hier nicht Stil, sondern die
   Fehlerquelle.

### 8.2 Jeder Schritt kennt seinen Blustradius (`data/blustradius-deploy.yml`)

Alle 64 Schritte des `deploy`-Jobs sind deklariert – mit Klasse und Begründung:

| Klasse | Anzahl | Darf die Auslieferung anhalten? | Bedeutung |
|---|---|---|---|
| `infra` | 13 | ja | Ohne ihn gibt es keinen Auslieferungsstand (Checkout, Abhängigkeiten, Build, Upload). |
| `inhalt` | 31 | ja | Fachliches Gate. Ein Stopp ist hier gewollt: Ungeprüftes geht nicht live. |
| `gate-selbsttest` | 12 | ja | Ein Inhalts-Gate ist nicht lauffähig – fail-closed bleibt (C2/C33). |
| `werkzeug` | 8 | **nein** | Mess-/Melde-Schritt ohne Inhaltsentscheid. Er meldet und liefert weiter. |

`scripts/blustradius_register.py --check` prüft das Register gegen den echten
Workflow – in sechs Gruppen: Deckung in beide Richtungen (kein Schritt ohne
Eintrag, kein Eintrag ohne Schritt), Reihenfolge, erlaubte Klassen, Begründungs-
pflicht, Exit-Auswertung bei `werkzeug`-Schritten und Meldepflicht an den
gemeinsamen Kanal. **Ein neuer Schritt ohne Eintrag ist ein Befund, kein Zufall.**

### 8.3 Ein Meldeweg statt acht (`scripts/werkzeugbefund.py`)

```
Schritt  →  werkzeugbefund.py --melden <schritt> <grund>   (Exit immer 0, #227)
         →  $RUNNER_TEMP/werkzeugbefunde.txt
Sammler  →  werkzeugbefund.py --sammeln
         →  Job-Outputs: werkzeugbefunde, werkzeugbefunde_anzahl
release-seal →  Tabellenzeile + ::error:: + Lauf rot – NACH der Veröffentlichung
```

Der Sammelschritt steht **vor** dem Artefakt-Upload (damit er Material hat) und
beendet sich immer mit 0 (damit er selbst nie blockiert). Die zwei Alt-Outputs aus
#676 und Teil 1 bleiben bestehen – sie sind vertraglich getestet – und werden vom
Sammler in denselben Kanal gefaltet, statt ein drittes Paar zu erzeugen.

### 8.4 Kein Messlauf ohne sein Werkzeug (`scripts/measurement_chain.py`)

Eine Quelle der Wahrheit für die Messkette (Binary, Wörterbuch, Installationszeile)
mit drei Wirkungen:

- **Laufzeit:** `status()` / `require(kontext)` – `refill_to_min()` fragt im
  **Vorflug**, bevor der erste Kandidat gemessen wird. Der Befund lautet dann
  „hunspell fehlt … `sudo apt-get install -y -qq hunspell hunspell-de-de`" (Exit 3)
  statt eines Tracebacks nach Vorheilung und Hugo-Build.
- **Statisch:** `--audit-workflows` liest **alle** Workflows und meldet jeden Job,
  der ein registriertes Mess-Skript aufruft, ohne die Kette vorher **im selben Job**
  zu installieren. Aufrufe mit `--selftest` zählen nicht: Selbsttests laufen im Haus
  mit Attrappen (dieselbe Regel, die die KI-Probe #138 für Modell und Netz
  durchsetzt).
- **Gegen Verrotten:** Ein Drift-Detektor meldet jedes Skript, das `spellcheck`/
  `quality_score` importiert oder eine Messfunktion aufruft, ohne in der Registry
  zu stehen – und jede Registry-Zeile, deren Datei es nicht mehr gibt.

**Der zweite Fund.** Das Audit war beim ersten Lauf rot – nicht wegen `deploy.yml`
(das war geheilt), sondern wegen `frankautoops-report.yml`:

> `ops_report.py` berechnet die Qualitätskennzahl des **gesamten Bestands** über
> `quality_score.score_article` → `spellcheck` → `hunspell`. Der Job installierte
> `hunspell` nie. Die Rechtschreibmessung fiel pro Artikel still auf „unbekannt"
> zurück, der Fehler landete in einem `try/except` als `{"error": …}` – und der
> tägliche Report zeigte trotzdem einen Durchschnitt.

Das ist dieselbe Klasse wie #740, nur ohne Knall: Eine tote Messung ist gefährlicher
als gar keine, denn sie liefert eine Zahl. Geheilt in derselben Änderung (Messkette
vor dem Report-Schritt, inklusive `measurement_chain.py --check` als Beleg).

Ein weiterer Riegel: Der Abschalter `MESSKETTE_VORFLUG=aus` ist für lokale
Teilprüfungen gedacht. Taucht er in einem **Workflow** auf, ist das ein Befund –
sonst wäre die Wache in CI still abgeschaltet.

### 8.5 Der Watchdog urteilt, statt zu fragen

`bot_watchdog.blockade_klasse()` schlägt den blockierenden Schritt im Register nach.
Das Ticket nennt seitdem die Klasse (`BLUSTRADIUS_KLASSE=…` als Beleg) und einen
konkreten nächsten Schritt:

| Klasse | Was im Ticket steht |
|---|---|
| `werkzeug` | „Darf die Auslieferung NIE blockieren … Exit-Code auswerten, Befund über `scripts/werkzeugbefund.py --melden` an `release-seal`, Schritt mit 0 beenden." Kein Catchup. |
| `inhalt` / `gate-selbsttest` | „Darf anhalten – der Befund ist fachlich gemeint und gehört in den Fachkanal des Gates." Kein Catchup. |
| `infra` | „Erst das Werkzeug wiederherstellen, dann Catchup." |
| unbekannt | „Schritt in `data/blustradius-deploy.yml` nachtragen (C38)." |

Jeder Zweig nennt zusätzlich den maschinellen Heiler und seine Grenze
(`watchdog_recovery.py --live-site` greift nur bei einer vorübergehenden Blockade
und scheitert bewusst mit Exit 3 in eine stehende Kette). Vorher stand im Ticket
die Rückfrage „Ist es ein Mess-Schritt, darf er nicht blockieren" – eine Frage, die
der Leser beantworten musste. Ein Ticket, das fragt, erzieht zum Wegsehen
(Lektion WF-A535 #529).

### 8.6 Nachweise Teil 2

| Prüfung | Befehl | Ergebnis |
|---|---|---|
| Register vollständig | `python3 scripts/blustradius_register.py --check` | ✅ 64 Schritte, 0 Befunde |
| Register-Wache gegen Sabotage | `python3 scripts/blustradius_register.py --selftest` | ✅ grün (Positivprobe, Klassifikation, Shell-Analyse, 13 Sabotageproben) |
| Meldeweg | `python3 scripts/werkzeugbefund.py --selftest` | ✅ grün |
| Messkette statisch | `python3 scripts/measurement_chain.py --audit-workflows` | ✅ grün (vor der Heilung: 1 Befund – `frankautoops-report.yml`) |
| Messketten-Wache | `python3 scripts/measurement_chain.py --selftest` | ✅ grün (7 Sabotageproben inkl. falscher Reihenfolge, fremdem Job, stillem Abschalter) |
| **Schrittblöcke 1:1 ausgeführt** | `scripts.tests.test_blustradius_register` | ✅ Isolation Exit 2 → Schritt 0 + Befund · Exit 1 → Schritt **1** (Inhalt stoppt) · Kostensperre rot → `gesperrt=true`, Auslieferung läuft · Sammler faltet Altkanäle (`anzahl=2`) |
| Messkette im Release | `scripts.tests.test_measurement_chain` | ✅ 24 Tests (Vorflug bricht **vor** der ersten Messung ab, Exit 3 nennt die Installationszeile, Artikel unangetastet) |
| Vertrag C38 | `python3 scripts/governance_contract.py --selftest` | ✅ „C1–C38 mit Kunstbefunden" (5 C38-Sabotagen erkannt) |
| Gesamtsuite | `python3 -m unittest discover -s scripts/tests` | **3110 Tests**, 2 Fehler – beides Vorbestand aus `main` (§5) |
| Uhr-Probe (+97 Tage) | `scripts/selftest_clock.py --trap-discover scripts/tests --offset 97` | identisch: nur dieselben 2 Vorbestands-Fehler |

### 8.7 Dateien Teil 2

**Neu**

- `data/blustradius-deploy.yml` – Register aller 64 Deploy-Schritte (Klasse + Grund)
- `scripts/blustradius_register.py` – Wache über das Register (`--check`,
  `--tabelle`, `--klasse`, `--selftest`)
- `scripts/werkzeugbefund.py` – der eine Meldeweg (`--melden`, `--sammeln`,
  `--liste`, `--selftest`)
- `scripts/measurement_chain.py` – SSOT + Vorflug + Workflow-Audit der Messkette
- `scripts/tests/test_blustradius_register.py` (19), `test_measurement_chain.py`
  (24), `test_werkzeugbefund.py` (7)

**Geändert**

- `.github/workflows/deploy.yml` – Isolation und Kostensperre werten ihren
  Exit-Code aus (Werkzeugzweig meldet, Inhaltszweig stoppt hart), bezahlte
  Vertonung hängt an `steps.kostensperre.outputs.gesperrt`, neuer Sammelschritt vor
  dem Artefakt-Upload, Job-Outputs `werkzeugbefunde`/`werkzeugbefunde_anzahl`,
  `release-seal` wertet sie rot
- `.github/workflows/frankautoops-report.yml` – Messkette vor dem Ops-Report
- `scripts/publication_release.py` – Messketten-Vorflug in `refill_to_min()`,
  Selbsttest läuft bewusst mit Attrappen
- `scripts/bot_watchdog.py` – `blockade_klasse()` + klassenscharfes Urteil im
  Blockade-Befund
- `scripts/governance_contract.py` – Vertrag **C38** (Prüfung, Regeltext, Label,
  fünf Sabotageproben im Kontrakt-Selbsttest), drei neue Wachen im vertraglichen
  Minimum (C6)
- `scripts/tests/test_bot_watchdog_meldetakt.py` – zwei Sabotage-Anker an die neue
  Struktur des Blockade-Bauplans nachgezogen (gleiche Aussage, heutige Stelle)
- `CLAUDE.md` – Leitplanke „Werkzeug blockiert nie die Auslieferung (C38)"

### 8.8 Was Teil 2 bewusst NICHT tut

- **Keine Gate-Schwelle bewegt, kein Inhalts-Gate entschärft.** Alle 43 Schritte der
  Klassen `inhalt`/`gate-selbsttest` stoppen weiterhin hart.
- **Kein `|| true`.** Werkzeugbefunde werden ausgewertet und gemeldet, nicht
  geschluckt; der Lauf wird rot – nur eben **nach** der Veröffentlichung.
- **Kein drittes `*_werkzeugfehler`-Output.** Die Altkanäle bleiben (sie sind
  getestet) und fließen in den gemeinsamen Kanal.
- **Keine Ausnahme ohne Begründung.** Die Ausnahmeliste der Messkette
  (`AUSNAHMEN`) ist leer; jede künftige Ausnahme braucht einen Satz, warum sie
  keine Lücke ist.
