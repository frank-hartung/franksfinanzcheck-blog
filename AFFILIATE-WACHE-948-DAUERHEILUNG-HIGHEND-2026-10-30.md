# Affiliate-Wachen #948 – „Beweis nicht möglich“: Dauerheilung auf Profi-Niveau

**Meldung:** [Issue #948](https://github.com/frank-hartung/franksfinanzcheck-blog/issues/948)
· **Datum:** 30.10.2026 · **Branch:** `arena/e755613b-franksfinanzcheck-blog`
**Betroffener Lauf:** [`40859063513`](https://github.com/frank-hartung/franksfinanzcheck-blog/actions/runs/40859063513)
(29.10.2026 10:37:45 UTC, `schedule`, Job `integritaet`: **failure**)

---

## 1. Was wirklich passiert ist (gemessen, nicht vermutet)

Das Issue sagte: „**Werkzeugfehler** – mindestens einer der Beweise konnte nicht
geführt werden. Exit fehlt (Integrität=?, Intent=?, Selftests=failure/skipped,
Hugo=skipped).“ Diese Beschreibung ist formal richtig und praktisch wertlos:
Sie nennt keinen Test, keinen Artikel, keinen Satz.

Die Job-API nennt die Schrittfolge des Laufs:

| Schritt | Ergebnis |
|---|---|
| Abhängigkeiten (PyYAML 6.0.3, Hugo-Action) | ✅ |
| **Detektor-Selbsttest (Wache muss sehen können)** | **❌** |
| Intent-Wache-Selbsttest | ⏭ skipped |
| Hugo-Build | ⏭ skipped |
| Affiliate-Integritäts-Gate | ⏭ skipped |
| Intent-Wache | ⏭ skipped |
| Issue-Pflege / Beweis-Lage | ✅ |
| Lauf bewerten | ❌ |

Der Schritt „Detektor-Selbsttest“ besteht aus **zwei** Verträgen:

```bash
python3 scripts/affiliate_integrity_gate.py --selftest          # Detektor-Fixtures
python3 -m unittest scripts.tests.test_affiliate_exemption \
                    scripts.tests.test_affiliate_link_check      # Live-Bestand
```

Der zweite war rot – reproduzierbar:

```text
FAIL: test_all_live_posts_and_pillars_pass_without_errors
  (scripts.tests.test_affiliate_link_check.IntentBeforePillarTests)
AssertionError: {'2026-10-24-heizoel-preise-2026-so-findest-du-den-optimalen-kaufzeitpu':
  ['Fehlt der passende Deep-Link: …deep=stromanbieter-wechseln&cat=1
    (erwartet: Stromtarif-Vergleich)']} != {}
```

**Der Befund:** Der Heizöl-Ratgeber vom 24.10.2026 trug in seinem Frontmatter

```yaml
affiliate_exempt: true
affiliate_exempt_reason: "… keine passende, registrierte Partnerroute …"
```

und **im Fließtext trotzdem einen Affiliate-CTA**
(`👉 Jetzt vergleichen und sparen: [→ Jetzt Fixkosten auf CHECK24 prüfen](/go/allgemein/)`)
samt Werbe-Offenlegung. Der Artikel steht im Pillar `strom-sparen`, dessen
erwartetes Angebot ein Stromtarif-Vergleich ist. Der Link-Checker verlangt
diesen Deep-Link – und meldete „Fehlt der passende Deep-Link“, obwohl die
Ursache eine ganz andere war: **Ausnahme und CTA widersprachen sich.**

Das ist eine halbe Angabe. Wer `affiliate_exempt` setzt, erklärt „für dieses
Thema gibt es kein passendes Angebot“; wer gleichzeitig einen CTA stehen
lässt, erklärt das Gegenteil. Beides zugleich ist keine Ausnahme, sondern ein
Widerspruch – und der Artikel behauptete zusätzlich „Der Artikel bleibt bis
zur Quellenprüfung Entwurf“, war aber mit `draft: false` live.

## 2. Warum fail-closed richtig war – und was daran trotzdem falsch war

Die Sperre war korrekt: Ein Beweis, den ein defekter oder widersprüchlicher
Vertrag nicht führen kann, darf nichts veröffentlichen. `publish_gate.py`
verhielt sich genau so, wie es soll.

Falsch war die **Form der Auskunft**. Vier Defekte, alle am selben Tag
belegt:

**U1 – Der Widerspruch war unsichtbar.** Der Vertrag aus #762 sagt: eine
Ausnahme hebt nur die *Mindestpflicht* auf. Das ist richtig und bleibt so.
Aber niemand sagte „hier steht ein CTA neben einer Ausnahme“; der einzige
sichtbare Satz war das *Symptom* (Deep-Link fehlt). Wer das liest, sucht den
Fehler in der Link-Konfiguration statt im Artikel.

**U2 – Der Selbsttest hatte kein Protokoll.** Der Schritt lief ohne `tee`,
ohne `pipefail`, ohne Ausgabe-Export. Ein roter Selbsttest kürte damit
Hugo-Build, Gate, Intent-Wache, Report und Artefakt gleichzeitig ab – und
hinterließ im Issue nur „failure/skipped“.

**U3 – Die Diagnose kannte den roten Vertrag nicht.** Selbst wenn jemand
„Diagnose“ nachgeschoben hätte: Kein Werkzeug prüfte im Fehlerfall den
Link-Checker, aus dem der Fund tatsächlich kam. Das Integritäts-Gate allein
war für diesen Artikel **grün** (0 Struktur-, 0 Render-Funde) – der Lauf wäre
also auch mit gelaufenem Gate grün gewesen, während der Vertrag rot blieb.

**U4 – Die zentrale Meldestelle war tot.** `alert-on-failure.yml` ließ sich
seit dem Merge von #935/#943 **nicht mehr parsen**: zwei `const
workerZugangFailed` im selben Block und eine `runbookKlasse`-Liste, in der
fünf Fassungen (18 Strings) ohne Komma nebeneinander standen. Ein
Syntaxfehler im `github-script`-Block heißt: dieses Alerting existiert nicht.
Ein fehlgeschlagener Alarm-Schritt erzeugt keinen Alarm – der Ausfall war
still. Aufgefallen ist er nur, weil `scripts/tests/test_workflow_yaml.py`
jedes eingebettete Skript mit `node --check` prüft; dieser Test war rot und
niemand hatte ihn im Blick.

## 3. Dauerheilung

### M1 – Inhalt: der Widerspruch ist aufgelöst (Ursache, nicht Symptom)

`content/posts/2026-10-24-heizoel-preise-2026-so-findest-du-den-optimalen-kaufzeitpu/index.md`

* Portal-CTA **und** die zugehörige Werbe-Offenlegung im Fließtext entfernt.
  Für Heizöl existiert keine registrierte Partnerroute (CHECK24 führt kein
  Heizöl); ein Strom- oder Gastarif-CTA wäre sachfremd – genau das sagt die
  Ausnahme, und genau das gilt jetzt auch im Text.
* Begründung der Ausnahme an die Wirklichkeit angepasst (der Satz „bleibt bis
  zur Quellenprüfung Entwurf“ war unwahr: der Artikel ist live).
* Nichts gelöscht, keine URL verändert, kein CTA per Text-Patch geflickt.

### M2 – Der Widerspruch wird benannt, bevor das Symptom kommt

`scripts/affiliate_link_check.py`, `scripts/affiliate_integrity_gate.py`

* Der Wochen-Checker gibt bei „Ausnahme **und** CTA“ einen expliziten
  **Hinweis** aus (`Ausnahme und CTA widersprechen sich … /go/allgemein/ …
  CTA entfernen oder Ausnahme zurücknehmen`), **vor** der Deep-Link-Prüfung.
  Nenne die `/go/`-Ziele, nicht die aufgelösten Partner-URLs – der Mensch
  sucht im Text.
* Der Tagesreport führt die Ausnahmen jetzt mit dem Vermerk
  „⚠️ **Halbe Angabe**“ samt Zielen.
* Der Vertrag aus #762 bleibt **unverändert**: die Ausnahme hebt weiterhin
  nur die Mindestpflicht auf, jeder vorhandene Link wird weiter vollständig
  geprüft. Es gibt keine automatische Heilung – „CTA entfernen oder Ausnahme
  zurücknehmen“ ist eine Redaktionsentscheidung.

### M3 – Ein roter Lauf nennt seinen Befund (fail-closed bleibt)

`.github/workflows/affiliate-integrity-daily.yml`

* **Selbsttest mit Protokoll:** `set -o pipefail` (sonst verdeckt ein grüner
  zweiter Befehl den roten ersten), `tee /tmp/selftest.log`, Exit-Export,
  `::error::`-Annotation mit dem ersten Befund, Protokoll in der
  Job-Zusammenfassung, eigener `exit $code`.
* **Neuer Schritt „Befund zur roten Selbstprüfung (nur lesend, keine
  Heilung)“**, nur bei roter Selbstprüfung: `affiliate_integrity_gate.py
  --json --dry-run --no-build` (keine Heilung, kein Build, kein
  Report-/Zustandsschreiben) **plus** der Link-Checker direkt über den
  Live-Bestand – also genau der Vertrag, der im Selbsttest lief.
* **Issue:** neue Sektion „🛑 Selbstprüfung rot – Befund“ mit Exit-Codes,
  Befundzeilen, lesender Diagnose und dem nächsten Schritt; das
  Selbsttest-Protokoll reist zusätzlich im Detail-Log-Block mit.
* **Artefakt:** `/tmp/selftest.log`, `/tmp/befund.json`, `/tmp/befund.err`,
  `/tmp/hugo-build.log` werden jetzt auch bei rotem Selbsttest hochgeladen.
* **Beweis-Lage:** neue Zeile „Detektor-Selbsttest | outcome (Exit)“, damit
  der Zustand auch an grünen Tagen sichtbar ist.
* Unverändert: Rot heißt rot. Hugo-Build, Gate, Intent-Wache und
  Veröffentlichung bleiben gesperrt.

### M4 – Die Meldestelle ist wieder erreichbar

`.github/workflows/alert-on-failure.yml`

* Doppelte `const workerZugangFailed`-Bindung entfernt (eine Bindung, ein
  Name).
* Die `worker-deploy-zugang`-Runbook-Liste auf **eine** Fassung
  zusammengeführt (vorher 18 Strings aus fünf Merge-Ständen ohne Komma).
* Beides mit Kommentar und Verweis auf die Wache (`npm run workflow:js`).
  `scripts/tests/test_workflow_yaml.py` prüft seither wieder alle
  eingebetteten Skripte: **7/7 grün** (vorher rot), die vier roten Fälle in
  `test_workflow_js_wache` sind ebenfalls grün – sie waren Folgeschäden
  desselben Syntaxfehlers.

### M5 – Dokumentation und Regressionstests

* `docs/ANLEITUNG-CHECK24-LINKS.md`: Abschnitt „Wenn das Issue sagt: Beweis
  nicht möglich“ (wo der Befund steht, was fail-closed bedeutet) und
  „Redaktionelle Ausnahme“ (Ausnahme + CTA = halbe Angabe).
* `scripts/tests/test_affiliate_exemption.py`: drei neue Fälle – Widerspruch
  wird benannt (vor dem Deep-Link-Fund), Report zeigt „Halbe Angabe“,
  Ausnahme ohne CTA bleibt ohne Widerspruch – und der Exit-Code bleibt
  unverändert grün, damit #762 nicht still aufgeweicht wird.
* `scripts/tests/test_affiliate_integrity_workflow_contract.py`: neue Klasse
  `SelftestBefundContractTests` friert Protokoll, Annotation, Diagnose
  (**lesend**: `--dry-run`, `--no-build`, kein `--heal`) und die
  Issue-Sektion ein.

## 4. Verifikation (lokal, mit den CI-Versionen)

| Prüfung | Ergebnis |
|---|---|
| `python3 scripts/affiliate_integrity_gate.py --selftest` | ✅ bestanden |
| `python3 -m unittest scripts.tests.test_affiliate_exemption scripts.tests.test_affiliate_link_check` | ✅ 59 Tests (vorher 1 Fehler: Heizöl) |
| `python3 -m unittest scripts.tests.test_affiliate_integrity_workflow_contract` | ✅ 7 Tests (4 neu) |
| `python3 -m unittest scripts.tests.test_workflow_yaml` | ✅ 7 Tests (vorher 1 Syntaxfehler in `alert-on-failure.yml`) |
| `python3 -m unittest scripts.tests.test_workflow_js_wache` | ✅ 16 Tests (vorher 4 rot, gleiche Ursache) |
| `python3 scripts/workflow_js_wache.py --check` | ✅ alle `github-script`-Blöcke kompilieren |
| `python3 scripts/affiliate_intent_guard.py` | ✅ Exit 0 |
| `python3 scripts/redos_guard.py` + `--selftest` | ✅ 1335 Dateien, 0 Funde |
| `python3 scripts/skript_syntax_wache.py` | ✅ 589 Dateien |
| **Hugo 0.168.0 extended Build** (aus PyPI, wie der CI-Fallback) | ✅ 113 Seiten |
| **`affiliate_integrity_gate.py` mit gebautem `public/`** | ✅ **Exit 0** – 72 Live-Artikel, 0 Struktur-/Render-Funde, 2 begründete Ausnahmen |
| Diagnose-Schritt im Fehlerfall (simuliert) | ✅ nennt `2026-10-24-heizoel-…: Fehlt der passende Deep-Link …` |
| `python3 -m unittest discover -s scripts/tests` | ✅ 4523 Tests, 19 Fehler/1 Error (vorher 4514 Tests, 24 Fehler/1 Error) – die fünf abgebauten roten Fälle sind genau die hier behobenen: Live-Vertrag, `alert-on-failure`-Syntax (2× JS-Wache, 1× YAML), `alert_scoping` |
| `python3 scripts/integrity_guard.py` | ✅ Kern-Drift nur `scripts/affiliate_integrity_gate.py`; mit `--set-current` neu signiert, `data/integrity_lock.json` liegt **im selben Commit** (Hausregel) |

Die verbleibenden roten Tests sind Bestandsbefunde aus der Umgebung dieses
Arbeitsstands (fehlende Bild-Manifeste, Social-Winkel für LinkedIn/Telegram,
Weiterleitungs-Snapshots, `package.json`-Doppelschlüssel). Sie sind **nicht**
durch diese Änderung entstanden – der Vergleich gegen den Ausgangsstand
(`git stash`-freier Baseline-Lauf vor der ersten Änderung) zeigt sie
unverändert.

Der gerenderte Beweis (AI4/AI5) ist damit **auf dem echten Bestand** geführt,
nicht nur behauptet – mit demselben Hugo-Build, den die Wache täglich fährt.

## 5. Offener Befund (bewusst nicht mitgeheilt)

Der Heizöl-Artikel trägt weiterhin

```yaml
redaktionelle_pruefung:
  risikoklasse: "erhoeht"
  status: "ausstehend"
  aenderungsgrund: "Zurückgestellt: … redaktionelle Prüfung vor erneuter
                    Veröffentlichung erforderlich."
```

und ist gleichzeitig `draft: false` (live). `editorial_review_gate.py` ist
fail-closed nur für die Risikoklasse `hoch`; für `erhoeht` ist „ausstehend“
kein Blocker. Ob dieser Text live bleiben soll, ist eine **redaktionelle**
Entscheidung (Quellenkette) und keine Affiliate-Frage – sie wird hier
deshalb gemeldet statt still vollzogen. Empfehlung: entweder Belegkette
nachziehen und `status`/`aenderungsgrund` fortschreiben, oder den Artikel
über den regulären Rückläufer-Pfad (`reserve_janitor`) zurückziehen.

## 6. Produktionsgrenze

Die Änderung liegt als Vorschlag auf dem Branch; sie ist **nicht** auf `main`
übernommen und nicht ausgerollt. Bis zum Zusammenführen gilt der bisherige
(rote) Stand. Nach der Übernahme muss der reguläre Tageslauf den Beweis
erneut führen – der Issue-Pfad schließt die Meldung selbst, sobald der Lauf
grün ist.
