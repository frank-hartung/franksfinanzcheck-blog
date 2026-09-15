# Reparatur Issue #281 – Affiliate-Wache: „State 64 h alt" (Fehlalarm)

**Datum:** 15.09.2026 · **Status:** behoben · **Klasse:** Ursachenreparatur
(Überwachungs-Vertrag, nicht Content) · **Vertrag:** `docs/GOVERNANCE-KONTRAKT.md` C16

---

## 1. Kurzfassung für Frank

Die Affiliate-Links waren **nicht kaputt** – und die Wache war **nicht still**.
Sie ist jeden Tag fehlerfrei gelaufen. Gemeldet wurde ein **Fehlalarm**, den das
Zusammenspiel zweier Reparaturen zwangsläufig erzeugt hat:

* Das Gate schrieb seinen Zustand seit 02.09. **„konvergent"** – bei unverändertem
  Befund wurde keine Datei angefasst (Schutz vor täglichem Git-Diff und einem
  Deploy ohne Heilung).
* Der Watchdog prüft seit 12.09. **genau diesen Zeitstempel** als Lebenszeichen
  („State älter als 30 h = Wache schweigt", P1).

An ruhigen Tagen fror der Zeitstempel damit ein → der Watchdog **musste** Alarm
schlagen, und das Ticket konnte sich nie selbst schließen. Ein Befund-Zeitstempel
ist kein Lebenszeichen.

Reparatur: **Herzschlag und Befund werden getrennt.** Jeder Lauf erneuert den
Zeitstempel und pusht den Nachweis (der Lauf beweist, dass er in `origin/main`
angekommen ist); `verdict_changed` sagt, ob sich die *Lage* geändert hat. Der
Watchdog liest den Befund aus dem Zustand und belegt die Frische **per Herzschlag
oder per fehlerfreiem Lauf**. Beide Seiten sind als Selbsttest, Unit-Test und
Governance-Vertrag C16 eingefroren.

---

## 2. Beweislage

| Fakt | Wert |
|---|---|
| Ticket | [#281](https://github.com/frank-hartung/franksfinanzcheck-blog/issues/281) „Bot-Watchdog: Automatisierung braucht Eingriff" (14.09.2026, 15:09 UTC) |
| Befund | P1 · `affiliate-integritaet` · CHECK5B: „Integritäts-Wache schweigt: State 64 h alt (> 30 h, täglicher Lauf 06:00 MESZ)" |
| Zustand (Inhalt) | `generated_at: 2026-09-11 23:34:36 UTC` · exit 0 · 31 Artikel · 0 Funde |
| Zustand (Git) | letzter Commit `8ec9d8e` (12.09.2026, 00:25 UTC); davor `2e0e80c` (10.09.), `0651755` (08.09.), `20f74e6` (02.09.) |
| Wache-Läufe | täglich **success** (z. B. [34828017817](https://github.com/frank-hartung/franksfinanzcheck-blog/actions/runs/34828017817), 14.09., 14 Schritte grün, Deploy-Schritt korrekt übersprungen) |
| Reproduktion (lokal, 15.09.) | Lauf 1 → `generated_at 08:19:31` (Befund geändert: 31 → 32 Artikel) · **Lauf 2 mit identischem Befund → Zeitstempel blieb 08:19:31** (eingefroren) · Lauf 3 nach der Reparatur → `08:22:01`, `verdict_changed: false` |
| Umgebung des Nachweises | Hugo 0.164.0+extended (PyPI-Weg der CI-Action), Gate grün: 32 Live-Artikel, 0 Struktur-/Render-Funde, 19 Registry-Routen |

---

## 3. Ursachenkette

```
02.09.  Report + Zustand „konvergent"  (write_state: gleicher Befund -> kein Schreiben)
                  │
12.09.  Watchdog: „generated_at > 30 h  =  Wache schweigt"  (P1)
                  │
ruhiger Tag (Befund unverändert grün)
                  │
Zeitstempel friert ein  ──►  Wache committet nichts  ──►  Zustand bleibt alt
                  │
Watchdog meldet „Wache schweigt", obwohl sie lief  ──►  Ticket #281
                  │
Ticket kann sich nicht selbst schließen (der Fehlalarm entsteht täglich neu)
```

Der Widerspruch war **konstruktiv**, nicht zufällig: Die Frische-Anforderung
(12.09.) war mit dem Schreibverhalten (02.09.) nicht erfüllbar. Genau diese
Klasse – „Melder als Dauerläufer ohne Schließpfad" – war schon einmal der Kern
von #272 (Alarm-Routing).

---

## 4. Die Reparaturen

### R1 – Der Zustand trägt jetzt einen Herzschlag (`scripts/affiliate_integrity_gate.py`)

* `generated_at` wird bei **jedem** Lauf erneuert; Report und Zustand werden
  immer geschrieben. Der „Stand" ist damit ein echtes Lebenszeichen, versioniert
  und offline lesbar.
* Neues Feld `verdict_changed`: `true`, wenn sich die **Lage** (exit_code, geprüfte
  Artikel, Heilungen, Funde, Werkzeugfehler) gegenüber dem letzten Zustand geändert
  hat – verglichen wird ohne die flüchtigen Felder, das Feld selbst zählt nicht mit.
* `report_changed` trennt dasselbe für den Report (Menschen-Dashboard).
* Log-Zeile je Lauf: `💓 Herzschlag: … · Lage unverändert/GEÄNDERT`.
* Der Gate-Selbsttest friert den Vertrag ein (Fall 9): ein zweiter Lauf mit
  gleichem Befund **muss** den Zeitstempel erneuern und darf `verdict_changed=false`
  melden – in einem temporären Verzeichnis, der echte Zustand bleibt unberührt (C15).

### R2 – Der Lauf beweist seinen Nachweis (`.github/workflows/affiliate-integrity-daily.yml`)

* Der Beweis-Nachweis (Zustand + Report) wird **immer** committet und gepusht;
  die Commit-Botschaft unterscheidet Bedeutung:
  * Heilung → `fix(content): … automatisch geheilt (n Artikel)`
  * geänderte Lage → `chore(affiliate): Beweis-Lage aktualisiert`
  * ruhiger Tag → `chore(affiliate): Lebenszeichen … [skip ci]`
* **Frische-Nachweis:** Nach dem Push wird per `git fetch` + Blob-Vergleich geprüft,
  dass der Zustand wirklich in `origin/main` steht (`push_verified`). Genau dieses
  stille Verlieren hätte sonst denselben Fehlalarm wieder erzeugt.
* Der Deploy-Trigger verlangt `healed && pushed && push_verified` – ein Lebenszeichen
  löst **nie** eine Veröffentlichung aus.
* Die Zusammenfassung des Laufs zeigt nach jedem Lauf Herzschlag, Lage,
  Heilungen und `push_verified` (eine Wache, die nur bei Rot etwas zeigt, ist
  im Alltag unsichtbar).

### R3 – Der Watchdog prüft Befund und Frische getrennt (`scripts/bot_watchdog.py`)

| Lage | Bewertung |
|---|---|
| Zustand grün, Herzschlag ≤ 30 h | OK |
| Zustand mit Funden / exit ≠ 0 | FAIL (P1) – unabhängig vom Alter |
| Herzschlag alt, aber **fehlerfreier Lauf** im 30-h-Fenster | Hinweis (WARN): „Beweis über den Lauf geführt (Zustands-Push ausgeblieben?)" – **kein P1-Fehlalarm mehr** |
| Herzschlag > 54 h alt trotz fehlerfreier Läufe | FAIL: „Nachweis landet nicht im Repo" (eigener, präziser Befund) |
| kein Lauf / nur rote Läufe im Fenster | FAIL: „Wache schweigt" |
| gh nicht verfügbar (offline) | Hinweis (WARN) – Offline ist kein Ausfall |

Zusätzlich wertet **Check 5** jetzt nur noch **fehlerfreie** Läufe: eine Wache,
die täglich rot dreht, ist kein Grün (C2: „eine nicht ausgeführte Messung ist
kein Grün"). Die neue Lauf-Abfrage `workflow_run_evidence()` filtert das
30-h-Fenster im Python-Code statt per `gh --created` – das Flag fehlt in älteren
gh-Versionen (Debian 2.23) und machte die Abfrage dort zu einem Werkzeugfehler.

### R4 – Deploy-Negativliste: Verzeichnispfade waren wirkungslos (Nebenbefund)

Beim Absichern der Deploy-Neutralität des Herzschlags fiel auf: Die Einträge
`docs/`, `scripts/`, `.github/` … in der `STATE_ONLY`-Liste sind mit den Ankern
`^…$` **wirkungslos** – sie treffen nur eine Datei, die exakt so heißt. Jeder Push
unter diesen Verzeichnissen galt damit als deploy-relevant (voller Build +
Vertonung), obwohl Audit-Befund F1 vom 12.09. genau das Gegenteil beabsichtigt.
Jetzt `dir/.*`; der Zustand der Wache (`.affiliate_integrity_state.json`) steht
ausdrücklich in der Liste: **ein Lebenszeichen darf nie einen Livegang auslösen.**

### R5 – Verträge und Tests (dauerhaft, maschinengeprüft)

* `scripts/tests/test_affiliate_freshness.py` – 14 Tests: Herzschlag-Erneuerung,
  Lageerkennung, Report-Stand und alle Watchdog-Lagen (inkl. „#281 darf nie
  wieder ein P1 werden" und „schweigende Wache bleibt sichtbar").
* `scripts/tests/test_deploy_gate_paths.py` – 4 Tests, die die Deploy-Negativliste
  **in beide Richtungen** einfrieren (Lebenszeichen irrelevant, Site-Pfade immer
  relevant, Unbekanntes fail-safe relevant).
* `docs/GOVERNANCE-KONTRAKT.md` **C16 „Wache-Herzschlag"**: prüft maschinell, dass
  der Watchdog die Frische auch über Läufe belegen kann, eine Eskalationsgrenze
  kennt und der Lebenszeichen-Pfad deploy-neutral bleibt (und kein Site-Pfad
  still übersprungen wird). Der Gate-Selbsttest läuft zusätzlich in der
  Governance-Selbsttest-Runde (C6, `GUARDS`).
* Zeitanker in allen neuen Tests sind **relativ** (`now() - n h`) – die Lehre aus
  der Zeitbombe vom 14.09.2026.

---

## 5. Verifikation (15.09.2026)

| Prüfung | Ergebnis |
|---|---|
| `python3 scripts/affiliate_integrity_gate.py --selftest` | ✅ inkl. neuem Herzschlag-Fall |
| `python3 scripts/affiliate_integrity_gate.py` (echter Lauf, Hugo 0.164.0 extended) | ✅ 32 Artikel, 0 Funde, Herzschlag erneuert, `verdict_changed=false` im zweiten Lauf |
| `python3 scripts/bot_watchdog.py --selftest` | ✅ |
| `python3 -m unittest discover -s scripts/tests` | ✅ inkl. 18 neuer Tests |
| `python3 scripts/governance_contract.py --selftest` | ✅ C1–C16 (Kunstbefunde werden erkannt, sauberes Setup bleibt still) |
| `python3 scripts/governance_contract.py` | ✅ „alle sechzehn Regeln prüfen in beide Richtungen" |
| Watchdog-Lagen (9 simulierte Fälle) | ✅ genau die Tabelle aus R3 – der #281-Fall wird zum Hinweis, echte Stille bleibt FAIL |

---

## 6. Was bewusst NICHT geändert wurde

* **Heilungslogik der CTAs** (`affiliate_marketer.py`, `route_for()`) – unberührt;
  es gab nichts zu heilen.
* **Die Konvergenz-Idee selbst** – bleibt erhalten, nur getrennt: *inhaltliche*
  Konvergenz (kein Fund ohne Bedeutung) und *Lebenszeichen* (Herzschlag) sind
  jetzt zwei Dinge. Ein ruhiger Tag erzeugt genau **eine** Zeile Diff pro Datei.
* **`publish_gate.py`** – die harte Vor-Veröffentlichungsprüfung (AI1–AI4,
  fail-closed) bleibt unverändert. Der Herzschlag ist kein Freibrief.
* **Pinterest-Befunde (#279, #246)** – menschlicher Besitz, eigener Kanal, hier
  nicht angefasst.

---

## 7. Was nach dem Merge passiert

1. Der Zustand liegt mit frischem Herzschlag in `main`; die tägliche Wache hält
   ihn aktuell (06:00 MESZ) und beweist ihren Push.
2. Der Bot-Watchdog läuft täglich 10:30 MESZ. Findet er **keinen** maschinell
   behebbaren Befund mehr, schließt der Alarm-Router das Automations-Ticket
   selbst (Schließpfad aus #272) – #281 verschwindet ohne Handgriff.
3. Kommt ein echter Ausfall, bleibt er sichtbar: kein Lauf / rote Läufe →
   FAIL „Wache schweigt"; roter Befund → FAIL „offene Affiliate-Probleme";
   Nachweis landet nicht im Repo → FAIL „Nachweis landet nicht im Repo".
   Ein Fehlalarm „Wache schweigt, obwohl sie lief" ist durch C16 + Tests
   ausgeschlossen.
