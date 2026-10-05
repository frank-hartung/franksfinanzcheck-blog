# Wartung · Inhaltsqualität · Vorgang WF-A535 (#590) — Dauerhafte Behebung auf Premium-Niveau

**Datum:** 2026-10-05 · **Meldung:** #590 · **Vorgang:** WF-A535 ·
**Lauf:** [37325495772](https://github.com/frank-hartung/franksfinanzcheck-blog/actions/runs/37325495772)
**Betroffene Linie:** `Content-Engine v2` → Schritt „Persist final acceptance corrections"

> Auftrag: „Bitte dauerhaft auf Premium-Level einer Profi-Agentur beheben."
> Ergebnis: Die Meldung war **keine** API-Key- und **keine** Tagesdefizit-Klasse.
> Die Engine hat an diesem Tag drei fertige Commits erarbeitet und **keinen
> einzigen abgeliefert**. Die Ursache ist gefunden, belegt, geheilt und gegen
> Rückfall abgesichert — mit Opt-in statt Blast-Radius, 47 Testfällen und
> einer ehrlichen Fehlermeldung, die nie wieder zu API-Schlüsseln rät.

---

## 1. Was wirklich passiert ist (Beweiskette aus dem Lauf-Log)

Das Ticket nannte nur den Schritt, nicht die Ursache. Das Job-Log von Lauf
37325495772 nennt sie wörtlich:

| Uhrzeit (UTC) | Ereignis | Beleg |
|---|---|---|
| 14:32 | Engine startet auf `main`-Stand `30263d66` | Run-Kopf |
| 14:34 | Phase-1-Commit `7cd2870b` geht sauber nach main | Commit-Historie |
| **14:46** | Mensch führt **PR #585** zusammen: neun **Bestands**-Artikel redaktionell umgeschrieben (`397c5808`) | Commit-Historie |
| 14:47 | Deploy-Lauf heilt drei derselben Artikel (`a79a079c`) | Commit-Historie |
| **14:53** | **Phase-2-Push scheitert**: sieben Konflikte in `content/posts/*/index.md`, harter Stopp. Der Schritt toleriert Fehler → **der Lauf merkt es nicht** | Log 14:53:02 |
| 14:53–14:55 | Phase 3 und Endabnahme stapeln zwei weitere Commits auf einen Stand, der nie wieder pushbar ist | Log, `Rebasing (1/3)` |
| 14:55 | „Persist final acceptance corrections" (einziger Schritt ohne Fehlertoleranz) stirbt am selben Konflikt | Log 14:55:11 |

```
rebase: prüfe automatisch lösbare Bot-Artefakt-Konflikte:
  - content/posts/2026-08-14-gasrechnung-senken-fehler-im-spaetsommer-vermeiden/index.md
  - content/posts/2026-08-26-tagesgeld-zinsen-2026-die-besten-zinssaetze-im-vergleich/index.md
  - content/posts/2026-10-02-preiswert-surfen-so-findest-du-den-optimalen-dsl-anschluss/index.md
  - content/posts/2026-10-02-weihnachten-budget-planen-ohne-schulden-durch-die-feiertage/index.md
  - content/posts/2026-10-05-budget-app-2026-so-beherrschst-du-deine-ausgaben-ohne-auf/index.md
  - content/posts/2026-10-05-dns-server-aendern-schnelleres-internet-ohne-mehrkosten/index.md
  - content/posts/2026-10-05-oekostrom-anbieter-wechseln-clever-sparen-und-gruen-bleiben/index.md
rebase: enthält nicht automatisch lösbare Dateien – kein Blind-Merge.
```

**Verloren gingen:** die Qualitäts-Fixes (`53c7d5b`), die Sofort-Optimierung
(`48771a0`) und die finalen Veröffentlichungsgates samt neu gemessener
Reserve-Zertifikate (`1e03a1c`) — 23 Minuten Maschinenarbeit.

**Dieselbe Klasse, nicht zum ersten Mal:** Runs 37066812647 (03.10.),
37052950135 (03.10.) und 37007043195 (02.10.) sind rot aus demselben Grund.
Vier von fünf Läufen seit dem 02.10. — das ist kein Zufallsschaden, das ist
ein Konstruktionsfehler.

### Die beiden Fehler dahinter

1. **Die Entscheidung war zu grob.** `git_sync.sh` kennt für Content nur
   „Blind-Merge" (verboten, zu Recht) oder „alles wegwerfen". Dabei ist die
   Lage eindeutig: Unwiederbringlich ist der **fremde Text**; die maschinelle
   Heilung (Rechtschreibung, Keyword-Gate, Titel, URL-/CTA-Hygiene) ist
   **deterministisch** und auf dem neuen Text in unter einer Sekunde erneut
   herstellbar.
2. **Der Schaden war unsichtbar.** Der erste gescheiterte Push lief unter
   `continue-on-error` ins Leere. Der Lauf arbeitete 20 Minuten weiter — auf
   einem toten Stand. Ein Lauf, der produziert und nicht abliefert, sieht in
   jeder Statistik nach Erfolg aus.

---

## 2. Die Dauerheilung (vier Schichten)

### Schicht 1 — Bestands-Abgabe statt Totalverlust (`scripts/git_sync.sh`)

Neue, **ausdrücklich eingeschaltete** Konfliktklasse
(`GIT_SYNC_BESTAND_POLICY=bestand-gewinnt`):

* Kollidiert ein Bestands-Artikel, **gewinnt die fremde, neuere Fassung**
  (`--ours` = `origin/main`). Kein Zeichen fremder Redaktion wird je
  überschrieben.
* Der Pfad wandert in ein Protokoll (`.git_sync_nachheilung.txt`, gitignored).
* Der Rest des Laufs — neuer Artikel, Gates, Reserve-Zertifikat, Faktenstand —
  wird **gerettet statt verworfen**.
* Wird ein Bot-Commit dadurch gegenstandslos, wird er übersprungen
  (`git rebase --skip`) statt den Rebase steckenzulassen.

**Blast-Radius: null.** Ohne die Variable verhält sich der Sync-Kern exakt wie
vorher (harter Stopp). Die 29 bestehenden Regressionstests laufen unverändert
grün; nur die Content-Engine schaltet die Klasse ein.

**Vorrangregel bleibt bestehen:** Reserve-Kandidaten (#295) gehören weiterhin
der Maschine — dort gewinnt der frische Lauf, nicht der Bestand.

### Schicht 2 — Die Heilung kommt zurück (`scripts/nachheilung.py`, neu)

Das Protokoll ist kein Aktenvermerk, sondern ein Auftrag. Das neue Werkzeug
zieht die verlorene Heilung **im selben Lauf auf dem neuen Textstand** nach:

| Werkzeug | Aufruf | Zweck |
|---|---|---|
| `zeit_rechtschreibung.py` | `--fix --offline --file <artikel>` | Rechtschreibung (offline, keine Geldfläche) |
| `fix_cta_hygiene.py` | `--include-drafts --file <artikel>` | CTA-Hygiene |
| `repetition_guard.py` | `--fix` | Doppelwörter nach Keyword-Injektion |
| `keyword_gate.py` | `--fix` | Titel, Description, erster Absatz, Dichte |
| `check_titles.py` | `--fix` | Titel-Konvention |
| `fix_url_hygiene.py` | `--fix` | URL-Hygiene (R8) |
| `shortcode_guard.py` | `--fix` | Build-Killer-Fangnetz (#522) |

Verträge: nur echte Artikel unter `content/posts/<slug>/index.md` werden
geheilt (Pfad-Ausbruch, Skript- und Report-Pfade werden verworfen); Werkzeuge
laufen als Argumentvektor, **nie über eine Shell**; das Protokoll wird erst
nach vollständigem Erfolg geschlossen — scheitert ein Schritt, wiederholt ihn
der nächste Lauf. `--selftest` prüft ST1–ST8 offline, ohne ein einziges
Heil-Werkzeug zu starten. Gemessene Laufzeit der vollen Kette: **< 1 Sekunde**.

### Schicht 3 — Nichts bleibt unsichtbar (`content-engine-v2.yml`)

* `Persist final acceptance corrections` bekommt eine `id` und Fehlertoleranz,
  damit Nachheilung, Status- und Defizit-Wache noch laufen — der Lauf bleibt
  trotzdem **ehrlich rot**.
* Neuer Schritt **„Heilung nach Fremdänderung nachziehen"**: arbeitet das
  Protokoll ab und committet das Ergebnis.
* Neuer Schritt **„Synchronstand prüfen"**: meldet per `::warning::` jeden
  Commit, der main nicht erreicht hat — der Unterschied zwischen *getan* und
  *angekommen* steht ab jetzt im Lauf.

### Schicht 4 — Das Ticket sagt die Wahrheit

Der Abschluss-Schritt kennt jetzt drei ehrlich rote Klassen statt zwei:

```
::error::SYNCHRONVERLUST (WF-A535 #590) – die Endabnahme konnte ihren Stand
nicht nach main bringen. Ursache steht wörtlich im Schritt „Persist final
acceptance corrections" (git_sync.sh nennt Datei und Klasse:
konflikt/schutz/auth/netzwerk). Kein Tagesdefizit, kein API-Key-Problem.
```

Zusätzlich nennt die Konflikt-Annotation von `git_sync.sh` jetzt **die
betroffenen Dateien** — genau die Information, die im Log von #590 stand und
es nie ins Ticket geschafft hat.

---

## 3. Beweise

```
npm run test:sync
  → 47 Tests, OK   (29 Bestands-Verträge + 5 neue Sync-Klassen + 13 Nachheilung)

python3 -m unittest discover -s scripts/tests
  → Ran 1810 tests · OK (skipped=23)

python3 scripts/governance_contract.py
  → 🔒 GOVERNANCE-VERTRAG erfüllt – alle 21 Regeln
```

Die fünf neuen Sync-Tests bilden den Vorfall eins zu eins nach:

| Test | Zusicherung |
|---|---|
| `test_fremd_bearbeiteter_bestand_gewinnt_und_lauf_bleibt_gruen` | Menschentext bleibt live, der Rest des Laufs wird gerettet, Protokoll geschrieben |
| `test_gegenstandsloser_commit_wird_uebersprungen_statt_zu_blockieren` | kein „No changes"-Steckenbleiben, kein Halbzustand |
| `test_ohne_opt_in_bleibt_der_harte_stopp` | alle anderen Workflows erben nichts |
| `test_konfliktdiagnose_nennt_die_betroffenen_dateien` | die Annotation ist die Diagnose |
| `test_reserve_entwurf_bleibt_sache_der_maschine` | ältere Regel (#295) behält Vorrang |

---

## 4. Was bewusst **nicht** gemacht wurde

* **Kein Blind-Merge über Content.** Die Regel aus #295 steht — sie wird nur
  um einen Fall ergänzt, in dem eindeutig ist, wer gewinnen muss.
* **Kein globaler Richtungswechsel.** Die neue Klasse ist Opt-in; `deploy`,
  `blog-health-daily`, `content-reserve` & Co. bleiben unverändert hart.
* **Kein gemeinsamer Concurrency-Riegel für Engine und Deploy.** Das würde die
  Kollision zwar verhindern, aber Veröffentlichungen hinter Deploy-Läufen
  stauen und die Kadenzzusage (Mo/Mi/Fr) gefährden. Die Kollision ist
  betriebsnormal — der Umgang damit war der Fehler.
* **Kein Grünwaschen.** Ein nicht abgelieferter Tagesertrag bleibt rot. Neu
  ist nur, dass dabei nichts mehr verloren geht und die Meldung stimmt.

---

## 5. Betrieb

```bash
npm run nachheilung          # liegt ein Nachheil-Auftrag an? (Plan, schreibt nichts)
npm run nachheilung:fix      # Heilung auf dem neuen Textstand nachziehen
npm run test:sync            # Sync-Kern + Nachheilung: 47 Verträge
python3 scripts/nachheilung.py --selftest   # offline, ohne Werkzeugaufruf
```

**Wenn ein Lauf wieder rot wird:** Der Schritt „Persist final acceptance
corrections" nennt Klasse und Datei. `konflikt` auf einer Datei **außerhalb**
von `content/posts/*/index.md` heißt: ein Mensch muss angleichen. Alles andere
(`schutz`, `auth`, `netzwerk`) steht mit Reparaturweg in
`docs/PFLICHT-CHECK-RUNBOOK.md`.

---

*Erstellt am 05.10.2026 · Dateien: `scripts/git_sync.sh`,
`scripts/nachheilung.py`, `scripts/tests/test_git_sync.py`,
`scripts/tests/test_nachheilung.py`, `.github/workflows/content-engine-v2.yml`,
`.gitignore`, `package.json`, `CLAUDE.md`.*
