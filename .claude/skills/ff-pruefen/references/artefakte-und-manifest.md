# Maschinen-Artefakte und Manifest – ganz oder gar nicht

> Wörtlich aus `CLAUDE.md` übernommen am 01.11.2026 (Skill-Umbau). Kein Satz wurde umformuliert, gekürzt oder erfunden; die Überschriften sind eine Ebene tiefer gehängt. Änderungen hier sind Änderungen am Regelwerk – sie brauchen denselben Nachweis wie vorher: Selbsttest der betroffenen Wache, dann Commit.

### Maschinen-Artefakte niemals mergen (seit 22.09.2026, Issue #346)

`data/integrity_lock.json` ist ein **Siegel**, kein Quelltext: SHA-256-Map,
verkettete Akte, eigene Prüfsummen. Es wird ausschließlich von
`scripts/integrity_guard.py` geschrieben.

- **Bei Merge-Konflikt: niemals beide Seiten zusammensetzen.** Eine Fassung
  wählen und neu signieren (`--set-current`) — oder das Siegel belegt heilen
  lassen: `python3 scripts/integrity_guard.py --repair-lock`.
- `.gitattributes` setzt `merge=binary`: Ein Text-Merge ist damit gar nicht
  mehr möglich (am 21.09.2026 hat genau so ein Zusammenschnitt die
  Content-Engine im ersten Schritt gestoppt, Issue #346).
- Zustand prüfen statt raten: `python3 scripts/integrity_guard.py --drift-audit`
  nennt Siegel-Zustand (gesund / Legacy / zerstört / Chimäre), Bruchstelle und
  Herkunft. Ein zerstörtes Siegel heißt **nicht** „6 Kerndateien ohne
  Signatur" — es heißt, dass keine Aussage möglich ist.
- Schreiben ist atomar + rückgelesen: Ein abgebrochener Lauf hinterlässt den
  vorigen Stand, nie ein halbes Siegel.
- **Die Lehre von #346 gilt für den ganzen `data/`-Baum, nicht nur für das
  Siegel** (08.10.2026, #653): Sechs Nächte hintereinander meldete der harte
  End-Gate „🛑 RESERVE-ENGPAß: nur 0/6 Kandidaten gate-fertig“ – bei vollem
  Vorrat. `data/reserve-readiness.json` und `data/reserve-quarantine.json`
  lagen nach einem Merge als ungültiges JSON in `main`; der End-Gate las
  daraus eine `0` und leitete eine komplette Ursachenliste ab („PRODUKTION: 6
  Kandidaten fehlen im Pool“). Der Schaden war nicht der rote Lauf, sondern
  die falsche Wegbeschreibung. Siehe
  `WF-D4E0-653-DAUERHEILUNG-PREMIUM-2026-10-08.md` und
  „Eine fehlgeschlagene Messung ist kein leerer Vorrat“ (C33) weiter unten.

### Ein Messartefakt ist eine ganze Messung, kein Text (seit 24.10.2026, #853)

Seit dem 21.10.2026 stand das `Integritäts-Siegel` für **jeden** Pull-Request
rot. Die Annotation sagte nur `.github#30 – Process completed with exit code 1`;
der Lauf-Log war über die API nicht lesbar (`results-receiver … EOF`). Die
Ursache stand im Repo, nicht im Netz: `artefakt_waechter.py` meldete drei
`A1-JSON-SYNTAX`-Funde in `data/gsc/` – alle drei Dateien waren aus **mehreren
Läufen** zusammengesetzt (`meta.json`: vier `stand`-Schlüssel in einem Objekt;
Top-Listen: zwei Läufe ohne Trennkomma hintereinander).

Der Import konnte das nicht sein (`write_text(json.dumps(...)` schreibt immer
vollständig). Entstanden ist es beim **Zusammenführen** der Bot-Branches:
PR #828 enthält zwei manuelle `Merge branch 'main'`-Commits, und Git hat die
drei JSON-Dateien als Text gemergt. Ein Text-Merge auf einem Messartefakt hat
keine Zeile, die zu beiden Läufen gehört.

Vier Regeln halten die Klasse jetzt:

- **Struktur:** `data/gsc/*.json merge=binary` in `.gitattributes` – wie beim
  Siegel (#346), den Reserve-Snapshots (#634) und den Quelltext-Wachen (#783).
  Der Tagesledger bleibt `merge=union`: Tage sind unabhängige Messungen.
- **Bedeutung:** `scripts/gsc_artefakte_guard.py` prüft vier Klassen – G1 Kopf,
  G2 Schema + Eindeutigkeit der Top-Listen, G3 Ledger streng aufsteigend, G4
  Kopf gegen gemessene Tage. G2–G4 fangen die Fälle, die **gültiges JSON**
  erzeugen und trotzdem falsch sind; der Selbsttest sabotiert 20 Fälle.
- **Herkunft:** `--heal` holt den letzten belegbar gültigen Git-Stand zurück
  (nie rekonstruieren, nie den Ledger zurückrollen, nie ein Teilstück
  schreiben); `--heal --rev <sha>` setzt alle Kopfdaten aus EINEM Lauf.
- **Verdrahtung:** die Wache läuft in `integrity-lock.yml` (jeder PR) und in
  `gsc-import.yml` **vor** jedem Commit; `data/gsc/**` löst jetzt `regression`
  aus, `scripts/tests/test_gsc_artefakte.py` prüft die echten Dateien; der
  Selbsttest steht im vertraglichen Minimum (C6).

Vertrag: **C6** (`GUARDS`) · Runbook `docs/ANLEITUNG-GSC-API-ZUGRIFF.md`,
Abschnitt „Wenn ein Artefakt kaputt ist“ · Bericht
`GSC-DATEN-INTEGRITAET-HIGHEND-2026-10-24.md`.

### Eine fehlgeschlagene Messung ist kein leerer Vorrat (C33, seit #653, 08.10.2026)

Sechs Nächte lang „0/6 gate-fertig“ bei vollem Vorrat – weil ein Merge zwei
Zertifikatsstände verschmolzen hatte und niemand die Artefakte gegenlas. Drei
Regeln halten die Klasse jetzt:

- **Artefakte werden gegengelesen.** `python3 scripts/artefakt_waechter.py`
  prüft alle versionierten Maschinen-Artefakte in sechs Klassen (A1 JSON-Syntax
  · A2 doppelte JSON-Schlüssel · A3 JSONL-Zeilen · A4 Konfliktmarker · A5 YAML ·
  A6 Frontmatter) – 386 Artefakte in 1,8 s, hart, ohne Fehlalarme. Geheilt wird
  **nur A2** und nur beweisbar (letzter Eintrag gewinnt == `json.loads`-Lesart,
  Gegenprobe auf Gleichheit, idempotent, Einzug wie gelesen). Alles andere
  bleibt Fund: Ein nicht mehr parsfähiges Artefakt zu rekonstruieren hieße,
  Inhalt zu erfinden.
- **Der End-Gate nennt die Klasse, nicht nur die Zahl.**
  `reserve_gate.py` unterscheidet `ok` · `engpass` · `artefakt` · `kette` ·
  `wachen`. Ohne Messung bleibt er rot (C2), aber er **erfindet keine
  Ursachen**: keine „URSACHEN DIESES ENGPASSES“-Liste aus einer Zahl, die
  dieser Lauf nicht gemessen hat. Ohne diese Unterscheidung weist die Diagnose
  die Reparatur in die falsche Richtung – sechs Nächte lang.
- **Messen läuft immer, heilen kommt vor urteilen.** Stufe 3
  (Zertifizierung) hängt an keinem anderen Schritt (`if: !cancelled()`): Wer
  das Artefakt schreibt, aus dem der End-Gate urteilt, darf nicht übersprungen
  werden. Der Artefakt-Wächter steht **hinter** ihr – ein Wächter am Lauf-Anfang
  würde die Stufe abschalten, die seinen eigenen Fund heilt.

Dazu: `scripts/reserve_readiness.py` schreibt Zertifikate atomar
(`os.replace`) und liest sie gegen, bevor es sie für gültig erklärt.

Vertrag: **C33** in `governance_contract.py` (Wache · Klassen · fail-closed ·
Verdrahtung in PR-Pfad und Reserve-Lauf in der richtigen Reihenfolge ·
Ursachenklassen · atomarer Schreiber · Siegel · Regressionstest).

### Das Manifest ist der Bau-Eingang (Manifest-Wache, seit WF-7B6B / #654, 08.10.2026)

Am 08.10.2026 brach `npm ci` in Sekunde 1 ab: Ein Merge (#647) hatte `package.json`
als **ungültiges JSON** auf `main` zurückgelassen (fehlendes Komma, `pagefind` doppelt).
Der E2E-Lauf und von 10:41 bis 12:50 UTC jeder Produktions-Deploy wurden rot. Die
automatische Meldung riet zu API-Keys – die Ursache stand in Zeile 181.

- **Vor jedem `npm ci` / `npm install` läuft `scripts/manifest_guard.py`** – Selbsttest
  zuerst, fail-closed. Geprüft werden JSON, Konfliktmarker, doppelte Schlüssel, Form
  und Lock ↔ Manifest (Wurzel-Sync, Vollständigkeit, exakte Pins). Befund = Datei +
  Zeile + Ursache, in GitHub als Annotation an der Zeile.
- **Verdrahtet** in `deploy.yml` (direkt nach dem Merge-Marker-Schutz), `e2e.yml`,
  `design-varianten.yml`, `lesehilfen-gate.yml`, `robustheit.yml`,
  `themenwelten-gate.yml`, `werkbank.yml`. Ein neuer Workflow mit `npm ci` ohne Wache
  fällt in `test_manifest_guard.VerdrahtungTests` rot.
- **Eine Quelle:** alle Manifeste des Repos (Wurzel, `tools/ff-voice-*`). Die einzige
  begründete Ausnahme (`OHNE_LOCKFILE_ERLAUBT`, `newsletter-worker`) gilt nur für ihren Pfad.
- **Die Wache ersetzt `npm ci` nicht.** Versions-Ranges entscheidet npm.
- **Der Alarm** nennt bei Install- und Manifest-Fehlern die Manifest-Diagnose statt des
  API-Key-Rats (`alert-on-failure.yml`, `installFailed`; Verhalten in
  `scripts/tests/sim/alert_scoping_sim.mjs`, Szenarien #654 und Deploy).
- Lock neu erzeugen: `npm install --package-lock-only --ignore-scripts`, dann Manifest
  und Lock **gemeinsam** committen. Den Lock nie von Hand auf einen Pin setzen.
- Bedienung: `npm run manifest:check` · `python3 scripts/manifest_guard.py --ref <sha>`
  (Vorfall nachspielen). Runbook: `docs/ANLEITUNG-MANIFEST-WACHE.md`.
  Vorgangsbericht: `WF-7B6B-654-DAUERHEILUNG-PREMIUM-2026-10-08.md`.
