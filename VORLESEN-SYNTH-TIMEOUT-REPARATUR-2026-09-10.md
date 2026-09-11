# VORLESEN: Edge-Totalausfall behoben + Synthese gegen Hänger gehärtet (10.09.2026)

**Stand: 10.09.2026, Nachtrag 11.09.2026 (§ 6) · FranksFinanzcheck Lesehilfen · Timeout-Härtung + kritischer Beifund**

Auftrag (Frank): *Timeout-Deckel für `synth_edge()` nachziehen — ein hängender
Edge-Stream darf den Deploy nicht bis zur Job-Wanduhr (150 Min.) blockieren.*

Ergebnis: **Der Deckel ist drin — und dabei kam ein stiller Totalausfall ans
Licht: Edge war seit 3 Tagen zu 100 % tot (TypeError in jedem Aufruf), alle
Neuvertonungen fielen lautlos auf Piper zurück.** Beides ist repariert,
mit 8 neuen Gates gepinnt und blogweit verifiziert.

---

## 1 · Der Beifund: Edge war seit 07.09. still tot

**Befund:** `synthesize()` ruft seit Gen 4 (Commit `4519c391`, 07.09.2026 15:34)
`synth_edge(..., style=style)` auf — aber `synth_edge` hatte **keinen
`style`-Parameter**. Folge: **Jeder Edge-Versuch starb mit TypeError**
(verifiziert: Signatur hat 7 Parameter, Aufruf + Rumpf verwenden `style`).
3 Versuche × TypeError → Piper-Fallback (im Deploy installiert, lädt das
ONNX-Modell selbst). Alle Gates blieben grün, weil:

- die Parität nur **Texte** vergleicht (keine Stimmen-Identität),
- alle Tests `synth_edge` **fakten** (die Fakes akzeptieren `style`),
- Synthese-Fehler pro Artikel **nicht-fatal** sind (Deploy läuft weiter),
- der **Cache** alte Edge-Spuren weiter einband (Bruch nur bei Neuvertonung
  sichtbar).

**Schaden:** Die 12 Artikel ab 07.09. (5× 07.09., 1× 09.09., 6× 10.09.) plus
nachträglich geänderte ältere tragen **Piper-Spuren ohne Wortuhr** statt
Conrad/serious mit Wortuhr — hörbar, aber ohne Wort-Takt. Kein Datenverlust,
kein roter Deploy: Der Fallback hat exakt wie designed gegriffen, nur
die Ursache war ein Bug statt Netz.

**Repariert:** `style=None` in der Signatur ergänzt (1 Zeile). Edge spricht
ab dem nächsten Deploy wieder; betroffene Artikel heilen konvergent
(Fingerprint unverändert → Piper-Spur bleibt bis zur nächsten Änderung;
neue/geänderte Artikel bekommen sofort Edge + Wortuhr). **Kein
Rezept-Versionssprung:** kein Track-Churn, keine Sonderspur nötig.

## 2 · Die Härtung — drei Wände gegen Hänger

| Wand | Datei | Was jetzt gilt |
|---|---|---|
| **1 · Segment-Deckel** | `scripts/ff_voice_backends.py` | `synth_edge(..., timeout=EDGE_SEGMENT_TIMEOUT)` = **120 s je Stream-Versuch** (`asyncio.wait_for`). Segmente ≤ 220 Zeichen brauchen normal < 15 s. Worst case je Segment: 3 Versuche × 2 Stil-Stufen ≈ 12 Min., danach Engine-Fallback bzw. ehrlicher Fehlschlag. `timeout=None/≤0` = Diagnose-Notausgang. |
| **2 · Segment-Budget** | `scripts/ff_voice_audio.py` | `synth_article(..., deadline=...)`: Die `--max-seconds`-Deadline wird **vor jedem Segment** geprüft (früher nur zwischen Artikeln). Ablauf ⇒ `stats["aborted"]`, Aufrufer stellt zurück (`deferred`, kein Verwerfen, kein Strip) — identisch zum Artikel-Deckel. |
| **3 · Deploy-Wanduhr** | `.github/workflows/deploy.yml` | TTS-Schritt: `timeout-minutes: 120` + `continue-on-error: true`. 120 deckt Normal (20 + Überlauf) und Backfill (90 + Überlauf) mit Reserve; ein Rest-Hänger außerhalb der gedeckelten Synthese tötet den Deploy nicht mehr an der Job-Wanduhr (150), sondern läuft mit Cache-/Browser-Fallback weiter (Nachmessung `--heal` räumt Teilausgaben). |

Rechenweg Normal-Deploy: ≤ ~35 Min. Schritt-Laufzeit (Cache-Fetch +
Budget 20 + max. ein Segment-Überhang ~12) ≪ 120 ≪ 150. Ton darf den
Livegang verzögern, nie verhindern.

## 3 · Neue Gates (8) — die echte Funktion wird getestet

**`ff_voice_backends.py --selftest` (83 → 88):** ruft erstmals die **echte**
`synth_edge` auf (nur `edge_tts` ist eine Attrappe im `sys.modules`):

- Hängender Stream + Aufruf MIT `style="serious"` kehrt mit `(False, [])`
  zurück (fängt TypeError-Regression UND fehlenden Deckel),
- Rückkehr in Sekunden (`< 30 s`, real ~0,6 s),
- Signatur-Pin: `style`-Parameter mit Default `None`,
- `timeout=None` bleibt nutzbar (leerer Strom ⇒ `False`),
- Konstante maßvoll (`0 < 120 ≤ 300`).

**`ff_voice_audio.py --selftest` (114 → 117):**

- Abgelaufene Deadline ⇒ Abbruch mit `aborted`-Flag, `samples is None`,
- kein Segment mehr synthetisiert (Zähl-Attrappe),
- frische Deadline ⇒ normale Synthese (`ok > 0`, `failed == 0`).

## 4 · Verifikation (alle Suiten grün)

| Prüfung | Ergebnis |
|---|---|
| `ff_voice_backends.py --selftest` | **88/88** (5 neu) |
| `ff_voice_audio.py --selftest` | **117/117** (3 neu) |
| `ff_voice_parity_check.py` | **384/384** |
| `ff_voice_toolbar_check.py` | **118/118** |
| `ff_voice_functional_test.mjs` | **247/247** |
| `ff_voice_repair_test.mjs` | **56/56** |
| `ff_voice_tts_hardening_test.mjs` | **57/57** |
| `ff_voice_voice_test.js` | **69/69** |
| `ff_heading_glyph_guard_test.mjs` | **40/40** |
| `heading_anchor_guard.py` + `--selftest` | **36/36**, **4/4** |
| `deploy.yml` | YAML valide, `timeout-minutes=120`, `continue-on-error=True` |
| Negativkontrolle | Aufruf MIT `style` am alten Stand ⇒ TypeError (Bug bewiesen); am neuen Stand ⇒ `(False, [])` in < 1 s |

## 5 · Geänderte Dateien

| Datei | Änderung |
|---|---|
| `scripts/ff_voice_backends.py` | `style=None` ergänzt (Totalausfall-Fix) · `EDGE_SEGMENT_TIMEOUT` (120 s) + `timeout`-Parameter mit `asyncio.wait_for` · 5 neue Selftest-Checks (echte Funktion, Attrappen-Netz) |
| `scripts/ff_voice_audio.py` | `synth_article(..., deadline)` + Segment-Prüfung + `aborted`-Flag · Aufrufer: `deferred`-Pfad · 3 neue Selftest-Checks |
| `.github/workflows/deploy.yml` | TTS-Schritt: `timeout-minutes: 120`, `continue-on-error: true` + Wanduhr-Kommentar |
| `README.md` | Gate-Zahlen 83 → 88, 114 → 117 |
| `VORLESEN-SYNTH-TIMEOUT-REPARATUR-2026-09-10.md` | neu — dieser Report |

---

## 6 · Nachtrag 11.09.2026 — Aufruf-Budget, Piper-Parameter, Segment-Wanduhr

**Ausgangslage (verifiziert am Stand `826b8f7`):** Die drei Deckel aus § 2
griffen **zwischen** Segmenten, aber nicht **in** einem Segment. Ein
einzelnes Segment konnte die `--max-seconds`-Deadline des Laufs damit
weiter unbegrenzt überziehen — rechnerisch bis ~46 Minuten:

| Lücke am alten Stand | Nachweis (am alten Stand gemessen) |
|---|---|
| `synth_edge` deckelte nur den Einzelversuch — die zwei Stil-Stufen liefen additiv | hängender Strom, Versuchsdeckel 1,0 s ⇒ Rückkehr erst nach **2,00 s** |
| kein Budget je **Aufruf** | `EDGE_CALL_TIMEOUT` nicht vorhanden; `synth_edge(call_timeout=…)` ⇒ `TypeError` |
| Piper-Deckel **verdrahtet** | `synth_piper`-Parameter: `['text', 'voice', 'out_wav']` — `timeout=600` fest im `subprocess`-Aufruf |
| keine Wanduhr in `synthesize()` | `SYNTH_SEGMENT_BUDGET` nicht vorhanden; `synthesize(deadline=…)` ⇒ `TypeError`; `synth_article` reichte `deadline` **nicht** an `ttb.synthesize` durch |

### 6.1 · Was jetzt gilt

| Deckel | Datei | Verhalten |
|---|---|---|
| **Aufruf-Budget** | `ff_voice_backends.py` | `EDGE_CALL_TIMEOUT = 300 s` je `synth_edge`-Aufruf. Jeder Versuch läuft mit `min(EDGE_SEGMENT_TIMEOUT, Restbudget)`; ist das Restbudget weg, wird **keine weitere Stil-Stufe begonnen** — Rückgabe `(False, [])`. `call_timeout=None/≤ 0` = Diagnose-Notausgang. |
| **Piper als Parameter** | `ff_voice_backends.py` | `synth_piper(..., timeout=PIPER_TIMEOUT)` (Standard unverändert 600 s) statt Verdrahtung; `TimeoutExpired` räumt die halbe Datei weg (`_cleanup`) — keine Teiltonspur. |
| **Segment-Wanduhr** | `ff_voice_backends.py` | `synthesize(..., deadline=None)` + `SYNTH_SEGMENT_BUDGET = 900 s`. Gereichte Deadline (aus `--max-seconds`) und eigenes Budget — **die frühere Grenze gewinnt**. Prüfung vor jeder Engine und vor jedem Versuch; das Restbudget wird als Deckel an Edge (`call_timeout`) und Piper (`timeout`) durchgereicht. |
| **Durchreichung** | `ff_voice_audio.py` | `synth_article` reicht `deadline` jetzt **in** `ttb.synthesize(...)` — die Deadline greift damit mitten im Artikel, nicht nur davor. Ablauf ⇒ weiterhin `aborted` ⇒ `deferred` (kein Verwerfen, kein Strip). |

Rechenweg neu: Ein Segment kostet höchstens `min(900 s, Restbudget)` —
danach ehrlicher Fehlschlag und Engine-/Artikel-Rückzug. Die Kette
`edge → piper` läuft nie mehr über die Lauf-Deadline hinaus.

**Signatur-Kompatibilität (Lektion vom 07.09.2026):** Die neuen
Schlüsselwörter werden nur gereicht, wenn die Backend-Signatur sie kennt
(`_accepts_kw` über `inspect.signature`). Ein blind gereichtes
`style=` hatte Edge am 07.09. für drei Tage still gekillt — dasselbe
Muster darf sich mit `call_timeout=`/`timeout=` nicht wiederholen.
Ältere Attrappen und Backend-Module laufen unverändert.

### 6.2 · Neue Gates (16 + 2)

**`ff_voice_backends.py --selftest` (90 → 106):** Konstanten-Pinne
(`EDGE_CALL_TIMEOUT ≥ EDGE_SEGMENT_TIMEOUT`, `SYNTH_SEGMENT_BUDGET > 0`),
echte `synth_edge`-Aufrufe gegen Attrappen-Netze (riesiger Versuchsdeckel
wird vom Aufruf-Deckel geschlagen; erschöpftes Restbudget startet keine
zweite Stil-Stufe; `call_timeout=None` lässt beide Stil-Stufen laufen),
Piper-Deckel im `subprocess`-Mitschnitt (gereicht 12,5 s / Standard 600 s /
`timeout=0` schaltet ab), Segment-Wanduhr (abgelaufene Deadline ruft **kein**
Backend; Abbruch **mitten** in der Versuchsreihe; Restbudget kommt als
Deckel bei Edge und Piper an) und die Signatur-Kompatibilitäts-Pinne.

**`ff_voice_audio.py --selftest` (117 → 119):** Deadline wird an das
Backend durchgereicht (Mitschnitt in der Zähl-Attrappe) +
Signatur-Pin `deadline` in `ttb.synthesize`.

### 6.3 · Verifikation (alle Suiten grün, 11.09.2026)

| Prüfung | Ergebnis |
|---|---|
| `ff_voice_backends.py --selftest` | **106/106** (16 neu) |
| `ff_voice_audio.py --selftest` | **119/119** (2 neu) |
| `ff_voice_parity_check.py` | **384/384** |
| `ff_voice_toolbar_check.py` | **118/118** |
| `ff_voice_functional_test.mjs` | **247/247** |
| `ff_voice_repair_test.mjs` | **56/56** |
| `ff_voice_tts_hardening_test.mjs` | **57/57** |
| `ff_voice_voice_test.js` | **69/69** |
| `ff_heading_glyph_guard_test.mjs` | **40/40** |
| `heading_anchor_guard.py` + `--selftest` | **36/36**, grün |
| Negativkontrolle (alter Stand) | hängender Strom ⇒ **2,00 s** (beide Stil-Stufen); neuer Stand mit `call_timeout=0.45` ⇒ **0,45 s**. `call_timeout=`/`deadline=` am alten Stand ⇒ `TypeError` (Lücke bewiesen) |

### 6.4 · Geänderte Dateien (Nachtrag)

| Datei | Änderung |
|---|---|
| `scripts/ff_voice_backends.py` | `EDGE_CALL_TIMEOUT` (300 s) + `call_timeout`-Parameter mit Restbudget-Kappung je Versuch · `PIPER_TIMEOUT` + `synth_piper(timeout=…)` · `SYNTH_SEGMENT_BUDGET` (900 s) + `synthesize(deadline=…)` mit Durchreichung · `_accepts_kw` (Signatur-Kompatibilität) · 16 neue Selftest-Gates |
| `scripts/ff_voice_audio.py` | `synth_article` reicht `deadline` in `ttb.synthesize` durch · Attrappen mit `deadline=None` · 2 neue Selftest-Gates |
| `README.md` | Gate-Zahlen 90 → 106, 117 → 119 |
| `VORLESEN-SYNTH-TIMEOUT-REPARATUR-2026-09-10.md` | dieser Nachtrag (§ 6) |
