# Beweis-Ledger-Bereinigung · C27 – dokumentierter Eigen-Commit

**Datum:** 07.10.2026
**Vorgänger:** `BEWEIS-LEDGER-ISOLATION-C27-DAUERHEILUNG-PREMIUM-2026-10-07.md`
(PR **#621**, Merge-Commit `0d5ebc0`) – dort wurde der Schreibpfad geschlossen.
**Dieser Commit:** entfernt die fünf Zeilen, die vorher bereits im Buch standen.

`history_guard.py` sagt zu einer bewussten Bereinigung selbst:

> „Bewusste Bereinigung (Union/chronologisch) gehört in einen dokumentierten,
> eigenen Commit."

Das ist dieser Commit. Er ist getrennt von der Heilung, weil beides
verschiedene Fragen beantwortet: PR #621 stoppt die **Zukunft**, dieser Commit
korrigiert die **Vergangenheit**. Beides in einem Commit hätte die
append-only-Verletzung mit der Reparatur vermischt, die sie verursacht hat.

## Was entfernt wurde – wörtlich

Fünf Zeilen, sonst nichts. `git diff --stat`: `2 files changed, 5 deletions(-)`.

`data/audit/2026-10-03.jsonl:136`
```json
{"ts": "2026-10-03T18:26:51Z", "module": "publish_gate", "action": "gate", "input": {"candidates": ["2026-09-07-r5-live"]}, "output": {"gated": ["2026-09-07-r5-live"], "demoted": ["2026-09-07-r5-live"], "editorial_holds": []}, "status": "gated", "critical": false, "commit": null}
```

`data/audit/2026-10-05.jsonl:2`
```json
{"ts": "2026-10-05T08:27:09Z", "module": "secrets_age_guard", "action": "record-success", "input": {"var": "GROQ_API_KEY", "proof_by": "content-engine-v2"}, "output": {"quality": "declared"}, "status": "ok", "critical": false, "commit": null}
```

`data/audit/2026-10-05.jsonl:162`
```json
{"ts": "2026-10-05T18:50:15Z", "module": "secrets_age_guard", "action": "record-success", "input": {"var": "GROQ_API_KEY", "proof_by": "content-engine-v2"}, "output": {"quality": "declared"}, "status": "ok", "critical": false, "commit": null}
```

`data/audit/2026-10-05.jsonl:185`
```json
{"ts": "2026-10-05T19:03:45Z", "module": "secrets_age_guard", "action": "record-success", "input": {"var": "GROQ_API_KEY", "proof_by": "content-engine-v2"}, "output": {"quality": "declared"}, "status": "ok", "critical": false, "commit": null}
```

`data/audit/2026-10-05.jsonl:187`
```json
{"ts": "2026-10-05T19:05:26Z", "module": "secrets_age_guard", "action": "record-success", "input": {"var": "GROQ_API_KEY", "proof_by": "content-engine-v2"}, "output": {"quality": "declared"}, "status": "ok", "critical": false, "commit": null}
```

Die Zeilen stehen hier vollständig, damit die Bereinigung nachvollziehbar
bleibt: Entfernt wird die **Behauptung** im Buch, nicht die Information darüber,
dass sie existiert hat und warum sie falsch war.

## Warum jede Zeile beweisbar fabriziert ist

### Zeile 1 – der gate-Entscheid für einen Artikel, den es nie gab

1. **Der Slug existierte nie.** `git log --all --diff-filter=A --
   'content/posts/2026-09-07-r5-live*'` liefert nichts. Im gesamten Repo kommt
   `2026-09-07-r5-live` nur in `scripts/tests/test_publication_reliability.py`
   vor (plus der Dokumentation ab PR #621).
2. **Kein Produktionslauf konnte ihn sehen.** Der Test legt die Fixture in
   einem `tempfile.TemporaryDirectory()` an und setzt `pg.POSTS_DIR` darauf.
   `todays_live_candidates()` liest `POSTS_DIR` – ein echter Lauf über das
   echte `content/posts/` hätte den Slug niemals aufgelistet.
3. **Der Zeitstempel passt zu keinem Taktgeber.** 2026-10-03 war ein Samstag,
   18:26:51 UTC. `publish_gate.py` wird aus `affiliate-integrity-daily.yml`
   (04:00 UTC), `redaktionelle-ymyl-pruefung.yml` (05:20 UTC, Mo–Fr),
   `seo-weekly.yml` (Mi 08:00 UTC) und `deploy.yml` (ereignisgesteuert)
   aufgerufen – keiner davon erklärt einen Samstagabend.
4. **Die Geschwister schweigen.** `r5-hold` und `r5-reserve`, die beiden
   anderen Fixtures derselben Klasse, kommen im Ledger **null** Mal vor. Nur
   die eine Fixture, deren Test `pg.main()` aufruft, hat eine Zeile
   hinterlassen. Genau das ist das erwartete Muster.
5. **Die Struktur bestätigt den Testpfad.** `demoted: ["…r5-live"]` ist der
   Re-Queue-Zweig (alter Ordner → `draft`, Inhalt erhalten). Ein am 07.09.
   datierter Slug, der am 03.10. als „bereits akzeptierter Bestand" behandelt
   wird, ist nur in der Fixture möglich.

### Zeilen 2–5 – eine Erfolgsbescheinigung, die niemand abgegeben hat

1. **Kein Workflow ruft das auf.** `--record-success` kommt in
   `.github/workflows/` genau zweimal vor: `pinterest-ai.yml` und
   `pinterest-token.yml`, beide für `PINTEREST_TOKEN_KEY`. Für
   `GROQ_API_KEY` ruft es niemand auf; `content-engine-v2.yml` ruft
   `--record-success` **überhaupt nicht** auf.
2. **Die Wache rechnet das jetzt selbst nach.**
   `record_success_aufrufe()` in `test_audit_ledger_isolation.py` liest die
   Workflows aus und ergibt genau `[('PINTEREST_TOKEN_KEY', 'pinterest-ai'),
   ('PINTEREST_TOKEN_KEY', 'pinterest-token')]`. Das Paar
   `('GROQ_API_KEY', 'content-engine-v2')` ist darin nicht erzeugbar.
3. **Erlaubt heißt nicht erfolgt.** `secrets_age_guard.CONFIG_ENV_VARS`
   gestattet `content-engine-v2` als `proof_by` für `GROQ_API_KEY` – deshalb
   tragen die Zeilen `quality: declared` und sehen echt aus. Genau das machte
   sie gefährlich: eine erlaubte, aber nie ausgeführte Kombination liest sich
   wie ein echter Nachweis. Ohne diese Erlaubnis hätte `_record_success` sie
   als `declared_foreign` abgewertet.
4. **Der Wortlaut stammt aus dem Test.** `proof_by="content-engine-v2"` steht
   wörtlich in `test_clear_text_logging_security.py`.
5. **Echte Nachweise hätten das Repo nie erreicht.** `pinterest-ai.yml` und
   `pinterest-token.yml` committen `data/audit/` **nicht** – ihre `git add`-
   Listen umfassen `data/pin_queue.yaml`, `content/posts/`,
   `data/secrets_state.json`, `data/pinterest_tokens.enc` und
   `data/pinterest_token_state.json`. `data/audit/` committet ausschließlich
   `frankautoops-report.yml` (Zeile 88: `git add data/audit/`), und dieser
   Workflow ruft kein `--record-success` auf. Konsistent damit: Es gibt
   **null** `PINTEREST_TOKEN_KEY`-Zeilen, obwohl zwei Workflows sie schreiben.
6. **Die Taktung passt zu keinem Scheduler.** `pinterest-token.yml` läuft
   `40 2 * * *` (02:40 UTC). Die vier Zeilen liegen bei 08:27:09, 18:50:15,
   19:03:45 und 19:05:26 UTC – drei davon innerhalb von 15 Minuten am Abend.
   Das ist die Signatur einer interaktiven Sitzung, nicht eines Cron-Laufs.

## Was bewusst NICHT entfernt wurde

**161 gate-Zeilen mit Slugs, die nicht in der Content-Historie stehen.** Der
erste, breite Scan („Slug nie in `content/posts/` angelegt") meldete 162
Treffer. 161 davon sind **echt**: `publish_gate.discard_article()` löscht
einen verworfenen neuen Artikel (`shutil.rmtree(bundle_dir)`, `os.remove(path)`),
bevor er je committet wird. Ein gate-Entscheid über einen Slug, den Git nicht
kennt, ist also der Normalfall und keine Fälschung. Das gültige Kriterium ist
die **Konjunktion**: Slug ist Test-Fixture *und* existiert nicht im Content.
Das ergibt genau eine Zeile.

Diese Selbstkorrektur steht hier, weil derselbe Fehlschluss naheliegt: Wer
„fehlt in der Historie" als Löschkriterium nimmt, vernichtet 161 echte
Beweise, um einen fabrizierten zu entfernen.

**`affiliate_profi_check`-Zeilen mit `action: check`.** Der Produktions-Gate
erzeugt über `publish_gate.affiliate_profi_failures()` →
`affiliate_profi_check.py --json` strukturell identische Zeilen. Ein
Testeintrag ist hier von einem echten Lauf nicht zu unterscheiden. Entfernt
wird nur, was beweisbar falsch ist – nicht, was möglicherweise falsch ist.
PR #621 stellt sicher, dass keine neuen dazukommen.

## Append-Only (H6) – der Nachweis

`history_guard.check_verlust()` vergleicht den Arbeitstree mit `git show HEAD:`.
Deshalb ist die Bereinigung in zwei Zuständen messbar:

**Vor dem Commit** (Arbeitstree kürzer als HEAD) – erwartungsgemäß rot:

```
$ python3 scripts/history_guard.py
  - 2026-10-03.jsonl: H6 Historie geschrumpft: 137 → 136 Records, nicht als
    W5-Rotation erklärbar (Kapazität 400) – Records fehlen oder Reihenfolge
    gedreht
  - 2026-10-05.jsonl: H6 Historie geschrumpft: 199 → 195 Records, …
🧾 78/80 Historien sauber · 2 harte Fehler · 0 Funde.
```

**Nach dem Commit** (HEAD ist die bereinigte Fassung, die Wache vergleicht
gegen sich selbst) – grün:

```
$ python3 scripts/history_guard.py
🧾 80/80 Historien sauber · 0 harte Fehler · 0 Funde.
```

In CI checkt `actions/checkout` bei einem Pull Request den Merge-Commit aus;
HEAD enthält die Bereinigung also bereits, und H6 bleibt grün. Der rote
Zwischenzustand ist kein Befund, sondern die Definition einer bewussten
Bereinigung: Sie ist nur als **eigener, dokumentierter Commit** gültig – nie
als stille Änderung am Rande.

Nicht berührt: `data/integrity_lock.json` sigelt 46 Dateien, **keine** davon
in `data/audit/`. `deploy_drift_guard.py` nennt `data/audit/2026-09-15.jsonl`
ausschließlich als Pfad-**Zeichenkette** in einem Selbsttest zur
Pfad-Klassifizierung, nicht als Inhalt. Keine Siegel-, Hash- oder
Zeilenketten-Abhängigkeit bricht.

## Wiederkehr ausgeschlossen

Neu in `scripts/tests/test_audit_ledger_isolation.py`, Klasse
`FabrizierteEintraege` – bewacht den **Ist-Zustand des Buches**, nicht nur den
Schreibpfad:

- `test_kein_fixture_slug_im_buch` – keine Ledger-Zeile nennt eine
  Test-Fixture (`r5-live`, `r5-hold`, `r5-reserve`).
- `test_record_success_nur_aus_echtem_workflow` – jede Erfolgsbescheinigung
  muss ein Paar `(VAR, proof_by)` tragen, das ein Workflow tatsächlich
  aufruft. **Selbstlernend** aus `.github/workflows/*.yml` gelesen: Kommt ein
  echter Aufruf dazu, passt sich die Regel an, ohne dass jemand eine Liste
  pflegt.
- `test_die_buchwache_ist_nicht_blind` – Schein-Sicherheits-Probe: Die Wache
  muss gegen die fünf Originalzeilen anschlagen; ein leeres Buch allein wäre
  kein Beweis.
- `test_echter_gate_entscheid_ist_kein_fund` – Gegenrichtung: Ein
  gate-Entscheid über einen echten Artikel bleibt stehen, auch wenn der Slug
  wegen `discard_article()` nicht in der Historie steht.

Beide Richtungen sind gemessen, nicht behauptet: **Vor** der Bereinigung
lieferte dieselbe Wache rot mit exakt diesen fünf Fundstellen
(`2026-10-03.jsonl:136`, `2026-10-05.jsonl:2,162,185,187`). **Nach** der
Bereinigung ist sie grün.

## Verfahren

Die Entfernung lief über ein streng inhaltsgeprüftes Skript (Planlauf zuerst,
`--apply` schreibt): Eine Zeile wurde nur entfernt, wenn sie die erwartete
Signatur trägt, und die erwartete Trefferzahl je Datei feststand
(`2026-10-03.jsonl`: 1, `2026-10-05.jsonl`: 4). Jede Abweichung bricht ab,
ohne zu schreiben. Zusätzlich geprüft: beide Dateien enden mit LF, keine
Leerzeile, jede Zeile parsebar – sonst Abbruch, weil sonst das Format der
Append-Only-Wache verletzt würde.
