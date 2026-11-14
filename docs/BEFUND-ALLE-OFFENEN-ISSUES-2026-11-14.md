# Befundakte: alle offenen Issues — 14.11.2026

**Auftrag:** „Bitte dauerhaft vollständig auf Highend-Level einer Profi-Agentur beheben.“
**Maßstab:** Ursache statt Symptom. Kein Ticket wird stillgeschlossen, keine Wache
weichgespült, keine Prüfung abgeschaltet. Was ein Mensch entscheiden muss, steht
hier als solches — mit Namen, Grund und Schließweg.

**Stand:** alle 27 offenen Issues vom 14.11.2026 (GitHub), Arbeitszweig
`arena/514ca666-franksfinanzcheck-blog`, Grundlage `389d4c8` (main).

---

## 1. Ergebnis in Zahlen

| Messung | Vorher | Nachher (Beleg) |
| --- | --- | --- |
| Skriptaufrufe in Workflows mit Schaltern, die es nicht gibt | 13 Klassen (u. a. `--check` bei `ki_audio_markierung`, `--new-only` bei `keyword_optimizer`) | **820 Aufrufe / 101 Workflows / 0 Verstoß** (`workflow_aufruf_vertrag.py --check`) |
| Auslieferungs-Siegel (Deploy) | dauerhaft rot, weil der Prüfaufruf selbst mit Exit 2 starb | Siegel prüft jetzt den kanonischen Schalter `--gate`; 44/44 Tonspuren markiert |
| Veröffentlichte Artikel ohne Belegkette (`quellen`) | 11 Tickets in 5 Tagen (immer nach dem Livegang) | **133 Dateien, 0 Befunde** (`metadaten_wache.py`); Publish-Gate sperrt die Klasse künftig **vor** der Veröffentlichung |
| Nachlauf-Wache | 11 offene Tickets | **✅ grün** in allen fünf Klassen (`veroeffentlichungs_wache.py --wache`) |
| Schließakte (Faktenfrische-Ledger) | Scorecard-Lauf rot (Exit 2) | **325 Listeneinträge, keine doppelten Schlüssel** (`--struktur-pruefen`) |
| KI-Kennzeichnung maschinenlesbar (#1028) | 12 ungeklärte Registereinträge, Frist 02.12.2026 | **115/115 Seiten, 0 Funde** (`ki_provenienz_gate.py --gate`); offen bleibt allein die Betreiber-Attestierung |
| Wachen-Selbsttests | — | **287 Wachen, 574 Uhr-Proben, alle grün** (`selftest_runner.py`) |

---

## 2. Befundklasse A — Aufruf-Vertrag: der Schalter, den es nicht gibt

**Das Muster.** Ein Workflow ruft ein Skript mit einem Schalter auf, den das
Skript nie gekannt hat. `argparse` beendet so einen Aufruf mit **Exit 2** – und
zwar bevor irgendetwas geprüft wurde. Das Ergebnis ist die gefährlichste Sorte
Rot: Eine Prüfung, die aussieht wie eine Prüfung, aber nur ihren eigenen
AufrufFEHLER meldet.

**Warum das über Wochen niemandem auffiel.** Jeder Befund stand in genau einem
flüchtigen Job-Log auf einem fremden Blob-Host. Das Ticket nannte den Schritt,
nie die Ursache. Die Wachen selbst waren gesund — sie wurden nur nie gefragt.

**Die dauerhafte Heilung.** `scripts/workflow_aufruf_vertrag.py` liest **jeden**
Skriptaufruf in **jedem** Workflow, holt sich das `argparse` des gerufenen
Skripts und vergleicht Schalter für Schalter. Vier Befundarten:

| | Befund | Bedeutung |
| --- | --- | --- |
| A1 | Skript fehlt | der Workflow ruft eine Datei, die es nicht gibt |
| A2 | Schalter unbekannt | genau die Klasse oben (Exit 2 statt Prüfung) |
| A3 | nicht prüfbar | das Skript lässt sich nicht importieren → Vertrag nicht beweisbar |
| A4 | tote Weiterleitung | ein Alias/Schirm existiert, aber das Ziel kennt den Schalter nicht |

Der Vertrag läuft **zweimal**: als CI-Schritt in `skript-syntax.yml` (mit
Zusammenfassung im Step-Summary, fail-closed) und als `--check`/`--selftest`.
Dazu 13 Regressionstests — der letzte prüft den **echten Bestand**
(`geprueft > 100`, `verstoss == 0`), nicht nur einen Fixture-Ordner.

**Was im Einzelnen geheilt wurde**

| Fund | Heilung |
| --- | --- |
| `ki_audio_markierung.py --check` (Deploy-Siegel, Lauf 43618889770) | `--check` ist jetzt Alias von `--gate`; der Deploy ruft den kanonischen Schalter. Die 44 ausgelieferten Tonspuren waren die ganze Zeit gesund – rot war nur der Aufruf. |
| `keyword_optimizer.py --fix --new-only` | **echter Bug**, nicht nur ein Schalter: das Flag war dokumentiert und implementiert seine Wirkung nicht. Jetzt heilt der Lauf ausschließlich den heutigen Slug-Tag. |
| `autopilot --run`, `social_calendar --build`, `entity_marken_gate --source-only`, `pinterest_engine --auto`, `pinterest_ziele --check`, `set_lastmod --git-changed`, `measurement_chain --check`, `cadence_guard --check`, `fm_boundary_guard --check` | Schalter explizit implementiert; jeder mit **Widerspruchs-Veto** (Exit 2, kein Schreibvorgang), wenn zwei Angaben sich ausschließen. |
| `reserve_operations.py --run … --apply` | Detektor für verschachtelte Aufrufe (ein Wrapper ruft ein Skript mit eigenen Schaltern). |
| `hemingway_check.py --gate-bestand` | Weiterleitung auf `readability_check.py`, geführt in `data/workflow_aufruf_weiterleitung.yaml` (A4-geprüft). |

---

## 3. Befundklasse B — Belegkette: der Befund kam immer NACH dem Livegang

**Das Muster.** Elf Nachlauf-Tickets (#1146, #1150, #1155, #1156, #1158,
#1178, #1186, #1190, #1200, #1202, #1204) meldeten im Kern denselben Satz:

> `[metadaten] M4: Keine Quelle im Frontmatter (quellen)`

…und zwar an Artikeln, die **bereits veröffentlicht** waren. Die Metadaten-Wache
hat richtig gemeldet — sie meldet nur (C34). Das harte Pre-Publish-Gate hatte
für dieses Feld **keine Regel**. Die Kette hatte also ein Loch genau zwischen
„Wache sieht es“ und „Gate verhindert es“.

**Die dauerhafte Heilung.** `publish_gate.quellen_failures()` ist die fehlende
Vorbedingung: Jeder Kandidat mit `draft: false` braucht einen nicht-leeren
`quellen:`-Block. Fehlt er, wird der Kandidat zurückgestellt (der Text bleibt
erhalten, die Redaktion ergänzt die Belege) — genau das Verhalten, das bei der
Kurzantwort (#1110) schon gilt.

Vier Eigenschaften, die die Heilung dauerhaft machen:

1. **Kein Heiler erfindet Quellen.** In `reserve_healer_coverage.py` steht die
   Regel als *redaktionelle Ausnahme* mit Begründung — die Deckungswache
   (`deckung()`) prüft, dass jede ablehnende Gate-Regel entweder einen Heiler
   hat oder eine begründete Zuständigkeit. Ergebnis: `luecken: []`,
   `tote_ausnahmen: []`, 10 gedeckte Regeln. Ein Heiler, der Belege „ergänzt“,
   wäre auf einem Finanzblog Haftung, nicht Heilung (C15).
2. **Der Schreiber existiert und ist benannt:** `faktenfrische.py`
   (`fm_setze_quellen`) schreibt den Block aus dem Recherche-Dossier. Fehlt der
   Block, fehlt die Recherche — nicht die Darstellung.
3. **Der Befund kann nicht mehr still entstehen:** `quellen: []` und ein nacktes
   `quellen:` ohne Listeneintrag gelten als fehlend (sieht im Diff gefüllt aus,
   ist aber kein Beleg).
4. **Verdrahtet, nicht nur definiert:** ein Test liest `publish_gate.py` und
   prüft beides — die Collector-Funktion **und** ihre Auswertung in `main()`.
   Neun Tests in `scripts/tests/test_publish_gate_quellen.py`.

**Stand der Klasse:** `veroeffentlichungs_wache.py --wache` → ✅ grün
(Frontmatter, Metadaten, Register, Akte, Kanaltreue). `metadaten_wache.py` →
133 Dateien, 0 Befunde. Alle 84 veröffentlichten Artikel tragen `quellen`.

**#1110 (Kurzantwort fehlt am frischen Live-Artikel)** ist derselbe Fall und war
bereits über `kurzantwort_failures()` geschlossen; das Feld ist am genannten
Artikel wieder gesetzt (Ökostrom-Artikel, `draft: false`).

---

## 4. Befundklasse C — Zustand, der die Messung selbst blockiert (#1193, #1191)

Beide Tickets sind keine Inhaltsbefunde, sondern Werkzeugbefunde: Der Lauf
konnte nicht messen, weil der **Zustand** vor der Messung nicht prüfbar war.

| Issue | Fehlgeschlagener Schritt | Prüfung jetzt |
| --- | --- | --- |
| #1193 Release-Scorecard | „Schließakte strukturell heilen (Selbstheilung, fail-closed)“ – Exit 2 | `faktenfrische_befund_ledger.py --reparieren --apply` → ✅ nichts zu heilen · `--struktur-pruefen` → ✅ 325 Listeneinträge, keine doppelten Schlüssel · `--selftest` → ✅ |
| #1191 Faktenfrische (Bestand) | „Recherche + Fachprüfung“ – Exit 2 („Beweisstand oder Konfiguration ungültig, hat vorsorglich nichts geschrieben“) | `--selftest` 45/45 grün; Vorflug der Kette (Queue lesen → `zusammenfuehren` → `entscheidungen_laden`) im Einzelnen grün |

**Einordnung, ehrlich:** Der Lauf hat sich korrekt fail-closed verhalten — er hat
nichts geschrieben, statt auf einem unprüfbaren Stand weiterzuarbeiten. Die
Heilung ist der dokumentierte Schließweg („fehlgeschlagenen Schritt reparieren
und die Scorecard erneut laufen lassen“); der Stand ist repariert und
nachgewiesen. **Nicht belegbar geblieben ist die auslösende Ursache:** Das
Laufprotokoll liegt als Artefakt auf einem fremden Blob-Host, der aus dieser
Umgebung nicht erreichbar ist (`EOF` beim Download) — deshalb steht hier kein
geratener Grund. Die Klasse ist doppelt abgesichert: Reparatur **und** Prüfung
laufen in drei Workflows (`faktenfrische.yml`,
`befund-akte-nachziehen.yml`, `release-scorecard.yml`) *vor* jeder Messung.

---

## 5. Was offen bleibt — und warum das kein Repository-Problem ist

Diese Posten sind **keine** technischen Schulden. Jeder von ihnen braucht eine
Entscheidung, ein Konto oder ein Dashboard — Dinge, die per Definition nicht im
Repo liegen. Sie sind hier vollständig benannt, damit niemand sie suchen muss.

| Issue | Was fehlt | Wer / wo | Warum nicht automatisierbar |
| --- | --- | --- | --- |
| #448 | Pinterest: Domain-Sperre | Pinterest-Konto, Dashboard | Die Sperre liegt bei Pinterest; ein Repo-Commit kann sie nicht aufheben. |
| #1028 (Rest) | Herkunft von 12 Registereinträgen; Frist 02.12.2026 | Betreiber-Attestierung | Die maschinenlesbare Kennzeichnung ist **fertig** (115/115 Seiten, Meta + Schema + Bilddatei + Feed + sichtbarer Anker). Ob ein Artikel KI-erzeugt oder menschlich geprüft ist, kann nur der Betreiber belegen — die Repo-Historie ist an dieser Stelle zusammengeführt und gibt keine Herkunft her. Das Register verlangt ausdrücklich: erst nach belegter Entscheidung ändern. |
| #1072 | 155 offene Fachbefunde (F4) | Redaktion | Jeder Befund ist eine fachliche YMYL-Entscheidung mit Fassungs-Hash. Ein Automat, der sie „entscheidet“, wäre genau der Fehler, den die Akte verhindert. Arbeitsliste: `BEFUND-AKTE.md`. |
| #1152 | Web-Vitals-Feldmessung: „Urteil (Felddaten entscheiden)“ | CrUX/Google-API + echte Felddaten | Felddaten entstehen nur aus echtem Nutzungsverkehr; ohne sie ist das Urteil bewusst fail-closed. |
| #1194 | Werkbank: keine belegfähige Fundstelle | Runner-Infrastruktur (SearXNG/DuckDuckGo) | Die Ursachenliste im Ticket nennt Container-Start und Drosselung der Runner-IP — Netz und Drittdienst, nicht Repo. Ausdrücklich **kein** Produktionsausfall (P3). |
| #1196 | Sicherheits-Wache: F-01 Header **und** Worker-Zustand | Cloudflare-Dashboard + GitHub-Environment | Beides sind Dashboard-Aktionen (Transform Rule `FF Sicherheits-Header`, Environment-Policy mit Reviewer). Das Runbook `docs/SICHERHEIT-BETRIEB-RUNBOOK.md` nennt jeden Schritt; der Repo-Teil (Wächter, Diagnose, fail-closed) ist gebaut. |
| #1151 | Governance-Report (Sammelticket) | läuft weiter | Das ist die Tageszeitung der Redaktion, kein Vorgang. Alle technischen Punkte daraus sind unten einzeln zugeordnet und erledigt. |

---

## 6. Issue für Issue

| # | Titel (Kurz) | Befund | Erledigt durch / Stand |
| --- | --- | --- | --- |
| 448 | Pinterest geparkt | Domain-Sperre | **Mensch** (Pinterest) |
| 1028 | KI-VO Frist 02.12.2026 | maschinenlesbare Kennzeichnung | **Maschinenteil fertig** (`ki_provenienz_gate` 115/115, 0 Funde); Attestierung offen → Betreiber |
| 1072 | Offene Fachbefunde F4 | 155 offene Entscheidungen | **Redaktion** (Arbeitsliste vorhanden) |
| 1110 | Kurzantwort fehlt | M4 am Live-Artikel | **behoben** — `kurzantwort_failures` sperrt vor Veröffentlichung, Feld am Artikel gesetzt |
| 1146, 1150, 1155, 1156, 1158, 1178, 1186, 1190, 1200, 1202, 1204 | Nachlauf-Wache (11×) | M2/M4/M7, Register, Akte | **behoben** — Befunde reproduzieren nicht mehr (`--wache` ✅, `metadaten_wache` 0/133), Klasse durch `quellen_failures` vor dem Livegang geschlossen |
| 1151 | Governance-Report | Sammelbefund | Zuordnung siehe diese Akte; technische Punkte erledigt |
| 1152 | Web-Vitals-Feldmessung | Urteil ohne Felddaten | **extern** (CrUX) |
| 1153 | Design-Varianten | „Bewertung gegen die Budgets“ | **behoben/grün** — `design_variant_gate.py`: 3 Varianten, keine Befunde, BESTANDEN |
| 1179 | E2E (Playwright) | Schritt „Metadaten-Wache – Quelle“ | **behoben** — `metadaten_wache.py`: 133 Dateien, 0 Befunde (gleiche Klasse wie B) |
| 1181 | Deploy-Siegel | „Siegel auswerten“ | **behoben** — `ki_audio_markierung --check` → kanonisch `--gate`; Klasse durch Aufruf-Vertrag geschlossen |
| 1191 | Faktenfrische (Bestand) | Exit 2, nichts geschrieben | **Zustand repariert und nachgewiesen**; Ursache im Artefakt nicht abrufbar (Blob-Host) — ehrlich benannt |
| 1193 | Release-Scorecard rot | „Schließakte strukturell heilen“ | **Zustand repariert** (325 Einträge, keine Duplikate), Schließweg = erneuter Lauf |
| 1194 | Werkbank ohne Quelle | keine belegfähige Fundstelle | **Infrastruktur** (SearXNG/Drosselung), P3 |
| 1196 | Sicherheits-Wache | F-01 + Worker | **Mensch/Dashboard** (Cloudflare + Environment-Policy) |
| 1215 | Content-Engine v2 | „Do not report a quota deficit as success“ | Klassifikator meldet korrekt; Klasse = Engine-Kontingent/Tagesdefizit → Redaktion/Betrieb, kein stiller Fehler |
| 1216 | Blog-Gesundheits-Check | `konsolidierung.py --rollenpaare` | **behoben** — lokal Exit 0 („Rollentrennung belegt: 1 Paar(e)“) |
| 1146… | (siehe oben) | | |

---

## 7. Wie man das nachprüft (alles offline, ohne Netz)

```bash
export PATH=/tmp/gv/bin:$PATH          # Hugo extended + requirements-ci.txt

python3 scripts/workflow_aufruf_vertrag.py --check      # 820 / 101 / 0 Verstoß
python3 scripts/workflow_aufruf_vertrag.py --selftest
python3 scripts/veroeffentlichungs_wache.py --wache     # Nachlauf-Wache: grün
python3 scripts/metadaten_wache.py                      # 133 Dateien, 0 Befunde
python3 scripts/faktenfrische_befund_ledger.py --struktur-pruefen
python3 scripts/ki_provenienz_gate.py --gate            # 115/115, 0 Funde
python3 scripts/design_variant_gate.py                  # BESTANDEN
python3 scripts/selftest_runner.py                      # 287 Wachen, 574 Uhr-Proben
python3 -m unittest scripts.tests.test_publish_gate_quellen \
                   scripts.tests.test_workflow_aufruf_vertrag \
                   scripts.tests.test_ki_audio_cli \
                   scripts.tests.test_reserve_diagnose -v
```

---

## 8. Regeln, die ab jetzt gelten (und die es vorher nicht gab)

1. **Kein Workflow-Aufruf ohne geprüften Schalter.** Der Aufruf-Vertrag liest
   jeden Aufruf in jedem Workflow gegen das echte `argparse`. Erweiterung ist
   eine Zeile, Umgehung ist ein Befund.
2. **Keine Veröffentlichung ohne Belegkette.** `quellen_failures` ist die
   Vorbedingung; die Metadaten-Wache bleibt der Melder, nicht der Wächter.
3. **Ein Befund, der niemanden erreicht, ist kein Befund.** Diagnosezeilen
   nennen die Ursache im Ticket (Reserve-Ticket, Faktenfrische, Metadaten), nicht
   im flüchtigen Log.
4. **Was ein Mensch entscheiden muss, wird nicht simuliert.** Wo eine Heilung
   Inhalt erfinden müsste, steht eine begründete Ausnahme in der Deckungswache —
   geprüft, nicht behauptet.
