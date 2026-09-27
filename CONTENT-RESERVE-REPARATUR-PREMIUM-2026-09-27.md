# Content-Reserve (#27): Zweiter roter Lauf am 27.09. – dauerhaft behoben

**Auslöser (Frank):** „Content-Reserve (täglicher Vorrat) #27 Bitte dauerhaft
auf Premium-Level einer Profi-Agentur beheben.“

**Betroffen:** Workflow `content-reserve.yml`, Läufe 36324047187 (11:24 UTC)
und 36338925820 (17:58 UTC, beide rot, Auto-Issue #412). Endstand des Tages:
**1/6 Kandidaten zertifiziert** statt geforderter 6/6. Reserve ist ein VORRAT
– der Lauf hatte recht, rot zu werden; also wurden die Ursachen behoben, nicht
die Messlatte gesenkt (`RESERVE_TARGET` 6 bleibt, härteste Gates bleiben).

---

## 1 · Befundlage (vier Fehler, zwei davon strukturelle Dauerbrenner)

| # | Befund | Klasse |
|---|--------|--------|
| 1 | Altersvorsorge-Kandidat (`2026-09-27-rente-…`) scheiterte mit quality-score **0.838 < 0.85** – schwach: Rechtschreibung 0.52, Lesbarkeit 0.75, Typografie 0.84 | gestrandeter Kandidat |
| 2 | **23 korrekte Fachbegriffe** des Vorsorge-Clusters (Rürup-Rente, Umlageprinzip, Generationenkapital, Halbeinkünfteverfahren, Nachversteuerung …) sind dem CI-Wörterbuch unbekannt – je −0,02 bis −0,10 Hart-Abzug bei quality_score. `absorb_whitelist.py` greift erst ab 3 Artikeln – jeder erste Artikel eines neuen Themenfelds scheiterte damit **deterministisch** | Strukturfehler |
| 3 | Sechs Themen fielen durch („3 Versuche ohne Erfolg“) – die Meldung trug **keine Fehlerklasse**, das Gedächtnis sperrte sie 3 Tage wie Content-Verlierer, und die Notbremse beendete die Nacht nach 2 Leerrunden (bei 43 freien Themen) | Strukturfehler |
| 4 | Inhaltliche Schwächen am Kandidaten selbst: CTA-Themenroutung verkehrt (Rente-Artikel warb für `/go/strom/` – Stromtarife!), ASCII-Anführungszeichen, grammatische Fehler („Du funktionierst nach dem Umlageprinzip“, „die Halbeinkünfteverfahren“), Tag-Artefakt „Geld sparen 3“, Flesch 55 (< 60, hartes Neukandidaten-Gate) | Content-Qualität |

Der gestrandete Kandidat war der eigentliche „Hoster des roten Laufs“: Er saß
fest (nur 1 Fund-Tag von der Quarantäne entfernt, danach Janitor-Löschung),
und die Disposition fand an dem Tag keine Ersatzthemen mehr in dem Cluster –
exakt das Muster aus #295/#387, nur mit neuer Ursache (Vokabular-Deckel).

## 2 · Reparaturen – an der Wurzel, nicht am Zeiger

### 2.1 Der gestrandete Kandidat (komplettes Redaktions-Lektorat)

`content/posts/2026-09-27-rente-2026-so-baust-du-heute-deine-sichere-altersvorsorge/index.md`
wurde **inhaltlich vollständig neu lektoriert** (nicht „bis zum Gate gedrückt“):

- **CTA-Routing korrigiert:** alle drei Affiliate-Plätze zeigen jetzt auf
  `/go/tagesgeld/` (Vorsorge-Sparkontext; registrierte Route), das Disclosure
  bleibt beidseitig.
- **Typografie:** durchgehend deutsche Anführungszeichen, keine ASCII-Reste.
- **Grammatik/Redaktion:** „Du funktionierst …“ → „Sie funktioniert … „
  (Umlageprinzip-Apposition), „die Halbeinkünfteverfahren“ → „das
  Halbeinkünfteverfahren“, Passiv→Aktiv wo der Text gewinnt, Absatz-Splits für
  lesbare Einheiten; Text 2 167 Wörter, 6 H2, 5 Fragezeichen-H3,
  „Das Wichtigste in Kürze“ + „Faustregel“ verankert.
- **Lesbarkeit:** Flesch **61,2** (hartes Neukandidaten-Minimum: 60) –
  readability-Gate 100/100, keine Findings.
- **Metadaten:** Tag-Artefakt „Geld sparen 3“ entsorgt; Schlüsselwörter
  gepflegt; `reserve: true`/`draft: true` unverändert gelassen (der Kandidat
  bleibt Vorrat und wird heute Nacht nach dem Finisher-Lift neu gewertet).

### 2.2 Rechtschreib-Deckel für neue Themenfelder (Dauerbrenner)

`data/spellcheck_whitelist.txt`: **23 lektorierte Domänenbegriffe** des
Vorsorge-/Rentenclusters ergänzt (datierter Block 27.09.2026, mit Begründung
und Hinweis auf das Einstiegslohn-Problem der 3-Artikel-Absorptionsregel).
Der Rechtschreibteil von `quality_score` springt damit von 0.52 auf **1.0** –
für diesen und alle künftigen Kandidaten des Clusters (Einzahlung in die
Domain-Deckung statt Einzelfall-Hotfix).

### 2.3 Fehlerklasse im Produktions-Gedächtnis (Struktur)

- `scripts/engine_generate.py` – neue Funktion `versuch_bilanz()` +
  Umstellung von `try_generate`: jeder Fehlversuch trägt jetzt seine Klasse
  (**`[infra]`** = Provider-Ausnahme/leere Antwort/fehlender API-Key vs.
  **`[inhalt]`** = Dublette/Titel-Gate R2/Profi-Gate/Relaxed-Gate). Die
  Rückgabemeldung lautet „N Versuche ohne Erfolg [infra|inhalt] (Detail; …)“
  (max. 380 Zeichen, Konsolenzeilen unverändert) – **„[infra]“ nur, wenn JEDER
  Versuch ein Infra-Fund war** (ein einziger Content-Fund => harte Klasse).
- `scripts/reserve_topics.py` – `merke()` ist klassenscharf: `[infra]`-Nächte
  zählen **nicht** auf den Content-Fehlerzähler (kein Dauerfehler-Pfad nach 3
  Nächten) und sperren das Thema nur **1 Nacht** (statt 3–30 Tage); erst nach
  `INFRA_DAUER_AB = 3` Infra-Nächten in Serie greift die Budget-Notbremse
  (`SPERRE_INFRA_DAUER = 7`). Ein Erfolg räumt beide Zähler ab.
- `scripts/engine_generate.py` – `_reserve_topup/_reserve_topup_batch`: die
  Leerlauf-Bremse trennt die Klassen. **Reine** Infra-Leerrunde ⇒ sofortiger,
  Budget-schonender Stop; Content-Leerrunde ⇒ längere Leine
  (`RESERVE_LEERLAUF_INHALT_MAX = 3`) – einzelne Gate-Fehlschläge räumen die
  Nacht nicht mehr vorzeitig ab (27.09.: 43 freie Themen, 2 Leerrunden,
  Feierabend – so nicht mehr).
- `scripts/reserve_gate.py` – `diagnose()` druckt im roten Lauf die letzten
  bis zu 4 Produktions-Fehlschläge **mit Klasse, Datum und Cooldown**
  direkt ins Issue-Posting (Lauf-Logs verfallen; das Gedächtnis tut es nicht).

### 2.4 Quarantäne-Zähler: Reset mit Begründung

`data/reserve-quarantine.json`: Zähler für den Rente-Kandidaten auf 0,
`zurueckgesetzt_am: 2026-09-27` + Klartext-Begründung (neuer Inhalt, neuer
Hash, alter Fund inhaltlich erledigt). Damit ist der erste Fund des Abends
sauber gegengezeichnet statt still gelöscht – und ein Marginal-Fehlschlag in
der Zukunft kann den neuen Artikel nicht mehr auf Basis des ALTEN Urteils
ausmustern (Sperrsignatur bleibt dokumentiert).

## 3 · Verifikation (alle Gates, die lokal beweisbar sind)

| Anti-Korruption-Prüfung | Ergebnis |
|--------------------------|----------|
| `quality_score.score_article` | **1.0** (7 Teile à 1.0, „publish“) |
| `publish_gate.title_integrity_failures` (R5) | leer ✓ |
| `keyword_optimizer.check_article` | 100, keine Findings |
| `readability_check.analyze` | 100, Flesch 61,2, keine Findings |
| `affiliate_intent_guard` | exit 0 (Kontrakttabelle sauber) |
| `affiliate_integrity_gate` AI1–AI3 | keine CTA-Findings; Route `/go/tagesgeld/` im 20-Key-Register |
| Textverständnis-/Check-Length/SEO-Audit/Profi-Batterien | rente sauber (einzig Alt-Corpus-Funde anderer Slugs, unverändert) |
| `reserve_readiness`-Zertifikat-Hashwifi | wlan-Kandidat weiterhin gültig zertifiziert |
| **Sabotage-Wächter** `selftest_runner.py` | **109 Wachen grün**, inkl. +97/+1461-Tage-Uhr-Proben |
| reserve_topics/engine_generate/reserve_gate/reserve_finisher/reserve_janitor/reserve_custody/draft_triage/reserve_converge/reserve_economy Selftests | grün |
| `reserve_gate.py --selftest` + Live-Diagnose | grün; Diagnose nennt jetzt Klasse je Fehlschlag |
| `py_compile` aller geänderten Skripte | grün |

Nicht lokal beweisbar: der Hugo-Render-Beweis AI4 (kein Hugo-Binary in dieser
Umgebung) und die finale Re-Zertifizierung – beide laufen im heutigen
Nachtlauf 03:25 UTC in Stufe 3 wie immer. Der Kandidat trägt dafür alle
Bedingungen: Rechtschreibdeckung, Flesch ≥ 60, quality 1.0, INTENT/INTEGRITY
sauber, Quarantäne-Zähler zurückgesetzt.

## 4 · Was bewusst NICHT passiert ist

- `RESERVE_TARGET` bleibt 6; keine Gate-Schwelle wurde gesenkt, kein
  „grün stempeln“. Die beiden Leerrunden-Notbremsen bleiben hart und sind
  jetzt zusätzlich budgetscharf.
- Das Bestandszertifikat (`data/reserve-readiness.json`) wurde NICHT
  handaktualisiert – der Hash des lektorierten Artikels ist absichtlich
  noch „veraltet“, weil Stufe 3 die Zertifizierung ehrlich neu zieht.
- Anderen, vor-gefundenen Corpus-Funden (Frugalismus 07.09., Winter-Heizung
  11.09.) wurde nicht unbeauftragt in den Content gegriffen – sie stehen
  seit Langem im System und sind kein heutiges Ereignis.

## 5 · Erwartung für den Nachtlauf & Folgebeobachtung

1. Janitor/Custody: kein Befund (flags konsistent, Quarantäne sauber).
2. Finisher hebt beide Kandidaten auf 28.09.; Kette läuft (Whitelist deckt).
3. Stufe 3 zertifiziert rente (~1.0) und wlan neu; Pool-Zählung springt
   auf 2, Konvergenz produziert mindestens 4 weitere mit voller Leine
   (klassenscharfe Bremse greift nur bei echtem Provider-Ausfall).
4. End-Gate (liest weiterhin das Zertifikat, hart) → Ziel 6/6; das
   Triage-Posting schließt Issue #412 mit der neuen, klassenscharfen
   Diagnostik.
5. Die 6 am 27.09. gesperrten Themen sind ab 30.09. wieder wählbar; ihre
   Klasse ist im Gedächtnis dokumentiert (scheitern sie erneut an
   Content-Gates, greift der normale Dauerfehler-Pfad).

**Verantwortlich (Reparatur):** Arena-Agent, 27.09.2026 ·
**Nachweis-Grenzen** ehrlich: Hugo-Render und CI-Gesamtlauf nur im Workflow.
