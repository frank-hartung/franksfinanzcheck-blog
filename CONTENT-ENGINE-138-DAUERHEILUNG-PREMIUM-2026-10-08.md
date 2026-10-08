# Content-Engine v2 · Lauf #138 — Dauerheilung auf Premium-Niveau

**Datum:** 08.10.2026 · **Workflow:** `.github/workflows/content-engine-v2.yml`
**Lauf:** #138, Run `37694986440`, Job `113044385963` (Slot „40 17 * * 1,3,5“,
von GitHub verzögert gestartet am 07.10.2026 22:15 UTC, Commit `55a927e`)
**Vorgänger:** WACHE-609 (#609/#619 – Lesbarkeits-Heiler, Schlüssel in Phase 0.5),
WF-A535 #529/#590 (Fehlerklassen der Endkontrolle), `selftest_clock.py` (Uhr-Zwang)

## Kurzfassung

#138 war **kein Tagesdefizit, kein API-Key-Problem und kein Endabnahme-Fehler** –
auch wenn die Annotation „Endabnahme ohne Exit-Code fehlgeschlagen“ das
nahelegte. Der Lauf starb in **Phase 0.5** mit Exit 2, also vor Phase 1: kein
Artikel, keine Endabnahme, kein Reserve-Refill.

> `requeue_quality_holds.py --selftest` rief den Lesbarkeits-Heiler mit
> `ki=True` **ohne Attrappe** auf. Seit WACHE-609 (07.10.2026) stehen in Phase
> 0.5 echte GROQ/GEMINI-Schlüssel. Das **Live-Modell** schrieb den absichtlich
> „schlechten“ Fixture-Text gut genug um (Flesch 2,9 → 86), der Heiler übernahm
> die Fassung korrekt – und der Selbsttest urteilte „Lesbarkeits-Hold unter der
> Schwelle wird freigegeben“ → Exit 2 → der ganze Lauf war tot.

Der Code war richtig, der **Test** war falsch: Sein Urteil hing an der
Tagesform eines Sprachmodells. #136 und #137 am selben Tag waren grün, weil das
Modell zufällig schwächer antwortete (oder die Antwort am Längenvertrag T4
scheiterte). Lokal und im PR-CI fehlt der Schlüssel → Stufe B fällt still aus →
grün. Das Risiko war deshalb nirgends sichtbar außer in der Produktion.

## Befund

### Was der Lauf zeigte

| Schritt | Ergebnis |
|---|---|
| Integritäts-Lock, Abhängigkeiten, Pre-Flight | ✅ |
| **Phase 0.5 – Kadenz-Gate (Selbsttest + Selbstheilung)** | ❌ `Process completed with exit code 2` |
| Phase 1 … Endabnahme (`final_release`) | ⏭ übersprungen |
| Reserve-Zertifikat, Persist, Nachheilung, Synchronstand, Phase 4 | ✅ (`!cancelled()`) |
| Endkontrolle | ❌ „Endabnahme ohne Exit-Code fehlgeschlagen“ – **falsche Fährte** |

Die Lauf-Logs selbst lagen hinter dem Blob-Speicher von GitHub und waren aus der
Werkbank nicht abrufbar; der Befund ist deshalb **nachgestellt und bewiesen**,
nicht aus dem Log abgeschrieben.

### Eingrenzung (Messung, nicht Vermutung)

1. Exit 2 ist in Phase 0.5 ausschließlich der Code „Selbsttest fehlgeschlagen“
   (alle sieben Werkzeuge: `return 2` / `sys.exit(2)` nur im `--selftest`-Zweig).
2. Alle 13 Befehle von Phase 0.5 am Commit `55a927e` grün – lokal, mit PyYAML,
   mit Attrappen-Schlüsseln **und** unter der Uhr des Laufs
   (`2026-10-07T22:16Z` = Donnerstag 00:16 Berlin, per `time-machine`).
   Kein Datums-, Inhalts- oder Abhängigkeitsproblem.
3. Einziger verbleibender Unterschied zur Produktion: **ein erreichbares Modell.**
   Nachstellung mit einer gelungenen, längentreuen Modellantwort:

   ```
   ['Lesbarkeits-Hold unter der Schwelle wird freigegeben: Flesch 2.9 → 86.2 (Stufe B, ≥ 60)']
   ```

   → exakt der Selbsttest-Fehler, der Exit 2 erzeugt.
4. Die neue KI-Probe zeigt den Aufrufort am alten Stand wörtlich:

   ```
   🛑 scripts/_alt_requeue_probe.py (12.2s) – NETZ
        ↳ create_connection → generativelanguage.googleapis.com:443 aus scripts/lesbarkeit_heiler.py:526 (_ki_chat)
        ↳ create_connection → api.groq.com:443 aus scripts/groq_config.py:115 (chat)
   ```

### Dieselbe Klasse noch dreimal im Repo (vor dem Ernstfall gefunden)

Die Probe über **alle 97** Selbsttests, die ein Workflow aufruft, fand drei
weitere latente Fälle:

| Selbsttest | Netzversuch | Risiko |
|---|---|---|
| `poppy_ingest.py` | Groq + Gemini (`llm_client`) | Kommentar „offline, da kein Key im Selbsttest“; mit Schlüssel entscheidet die Säulenwahl des Modells über Grün/Rot (nachgewiesen: rc 2) |
| `schaltwerk.py` (ST7) | `www.tagesschau.de` (RSS-Trigger) | „Offline-Selbsttest“ holt live einen Fremd-Feed |
| `blogautomatik_orchestrator.py` | dito (ruft ST7) | dito |

## Die Dauerheilung (fünf Teile)

### 1 · Ursache: `requeue_quality_holds.py` – Selbsttest hermetisch

Der Lesbarkeits-Teil läuft über `_KiAttrappe` (setzt
`lesbarkeit_heiler.KI_CALL`, zählt Aufrufe, stellt garantiert zurück). Statt
eines modellabhängigen Falls prüft er jetzt **alle vier** KI-Lagen
deterministisch:

| Fall | KI-Attrappe | Erwartung |
|---|---|---|
| L1 | stumm (Ausfall/kein Key) | Hold bleibt, Text unverändert, KI wurde gefragt |
| L2 | Vertragsbruch (zu kurz, T4) | Hold bleibt, nichts geschrieben |
| L3 | **gelungene Fassung** | Hold wird reif, NEUER Text, Beleg nennt Stufe B |
| L4 | — (Text schon ≥ 60) | reif ohne Schreiben, KI **nicht** gefragt |

L3 ist genau der Ernstfall von #138 – er ist jetzt der Beweis der gewollten
WACHE-609-Wirkung statt ihr Fehlalarm. Produktionslogik unverändert.

### 2 · Dieselbe Klasse: `poppy_lib.py`, `schaltwerk.py`

- Poppy: Modul-`chat` wird im Selbsttest ausgetauscht; geprüft werden
  Heuristik-Rückfall **und** Fail-closed gegen eine erfundene Säule (neu).
- Schaltwerk: `schaltwerk_triggers.NETZ_TRIGGER = {"rss"}` deklariert die
  Netz-Trigger; ST7 läuft gegen eine Attrappe, prüft die Deklaration gegen das
  Register und stellt die Provider im `finally` wieder her.

### 3 · Leitplanke: `scripts/selftest_ki.py` (KI-Probe)

Gegenstück zu `selftest_clock.py` für KI und Netz:

- `ki_sperre()` setzt jeden KI-Schlüssel der SSOT `data/ki_transportweg.yaml`
  auf eine Attrappe und sperrt jede Verbindung außer Loopback. **Jeder Versuch
  wird protokolliert, auch wenn der Aufrufer die Ausnahme schluckt** – genau das
  tut `_ki_chat`, deshalb fiel #138 vorher nie auf.
- `trap()` fährt einen `--selftest` in eigenem Prozess unter der Sperre;
  Befunde: `NETZ` (Datei:Zeile des Aufrufs), `ROT`, `ZEIT`.
- `entdecke()` liest **alle** Workflows – bewusst nicht nur Schritte mit
  Schlüssel, denn #138 entstand dadurch, dass ein Schritt Schlüssel *bekam*.
- Eigener Selbsttest mit sieben Sabotage-Proben (geschluckter Netzversuch,
  Schlüssel sichtbar, Loopback frei, Rot gemeldet, Aufräumen, Entdeckung des
  #138-Auslösers).
- Läuft in `publication-reliability-tests.yml` direkt nach der Uhr-Probe.

### 4 · Diagnose: Engine benennt den Frühabbruch

- Phase 0.5 hat eine ERR-Falle: Die Annotation nennt den **exakten Befehl** und
  Exit-Code statt eines nackten „exit code 2“.
- Die frühen Pflichtschritte tragen ids (`lock`, `preflight`, `kadenz`,
  `generate`, `taxonomie`, `phase1_commit`, `hugo`, `shortcode`).
- Die Endkontrolle kennt die vierte ehrlich rote Klasse **FRÜHABBRUCH**
  (`final_release` = `skipped`) und nennt den gestorbenen Schritt. Für #138
  hätte sie gemeldet: *„FRÜHABBRUCH (#138) – die Endabnahme lief nie;
  gescheitert ist: Phase 0.5 – Kadenz-Gate (Selbsttests + Selbstheilung). Kein
  Tagesdefizit, kein API-Key-Problem.“* (gerendert und ausgeführt, s. Beweise).

### 5 · Regel für alle künftigen Agenten

`CLAUDE.md`, Abschnitt „Ein Selbsttest urteilt über den Code, nicht über das
Modell“ – Regel, Muster, Leitplanke, Bedienung.

## Beweise (08.10.2026, offline – ohne Netz, ohne echten Schlüssel)

| Prüfung | Ergebnis |
|---|---|
| KI-Probe über alle Workflow-Selbsttests (minimale PR-Umgebung: nur pyyaml/pillow/cryptography) | ✅ **98/98** (vorher 94/97 + Auslöser) |
| Alter `requeue_quality_holds.py` unter KI-Probe | 🛑 NETZ – `lesbarkeit_heiler.py:526 (_ki_chat)` |
| `test_selftest_ki.py` (12 Tests) gegen **alte** Fassungen | ❌ 4 FAIL + 1 ERROR – inkl. wörtlicher #138-Meldung |
| `test_selftest_ki.py` gegen neue Fassungen | ✅ 12/12 |
| Gesamte Suite `unittest discover -s scripts/tests` | ✅ 2162 Tests (vorher 2150), 10 skipped |
| Uhr-Probe `selftest_clock.py --trap-discover scripts/tests --offset 97` | ✅ |
| `automation_premium_audit.py --strict`, `governance_contract.py` (29 Regeln) | ✅ |
| `integrity_guard.py --gate` (47 Kerndateien), `actions_version_guard.py --gate` | ✅ – keine signierte Datei berührt |
| KI-Transportweg-Vertrag (T1 Kostenwahrheit) | ✅ – Schlüsselliste aus der SSOT, kein Paid-Weg |
| Endkontrolle gerendert mit den Outcomes von #138 / Tagesdefizit / grün | FRÜHABBRUCH rc 1 · TAGESDEFIZIT rc 1 · rc 0 |
| ERR-Falle unter `bash -eo pipefail` (GitHub-Shell) | Annotation mit Befehl + Exit 2 |
| Nebenwirkung: Laufzeit der Selbsttests | requeue 12 s → 0,1 s · poppy 24 s → 0,2 s |

## Grenzen – ehrlich benannt

- Die Probe sperrt Netz **im Python-Prozess** des Selbsttests. Startet ein
  Selbsttest selbst `curl`/`gh` als Unterprozess, sieht sie das nicht. Heute tut
  das keiner der 98; Muster für den Fall: Unterprozess im Selbsttest attrappieren.
- Die Probe läuft im PR-Gate (`pull_request` auf `scripts/**`,
  `.github/workflows/**`). Direkte Bot-Pushes auf `main` ändern keine Skripte.
- Der verspätete Cron-Start (17:40 → 22:15 UTC, nach Mitternacht Berlin) ist
  GitHub-Verhalten und nicht Ursache von #138; Kadenz-Gate und Slot-Wache
  behandeln ihn bereits.

## Beobachtung (Abnahme)

- Nächste Engine-Läufe (Fr 09.10.2026, 06:10/14:10/17:40 UTC): Phase 0.5 grün;
  `requeue_quality_holds.py --selftest` meldet „✅ … bestanden“ in < 1 s.
- Neuer PR mit Skript-Änderung: Schritt „KI-Probe – kein Selbsttest darf am
  Modell oder am Netz hängen (#138)“ erscheint in *Publication reliability
  regression tests* und ist grün.

## Regressionen

`python3 -m unittest scripts.tests.test_selftest_ki` ·
`python3 scripts/selftest_ki.py --selftest` ·
`python3 scripts/selftest_ki.py --trap-workflows`
