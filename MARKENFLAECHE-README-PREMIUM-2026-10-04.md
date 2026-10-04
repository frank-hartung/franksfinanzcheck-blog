# 🏷️ Markenfläche README – dauerhafte Heilung (Vorgang WF-A4E0 · Meldung #552)

**Stand:** 04.10.2026 · **Auftrag (Frank):** „Wartung · Betriebspflege ·
Vorgang WF-A4E0 #552 – bitte dauerhaft auf Premium-Level einer Profi-Agentur
beheben."
**Ergebnis:** Markenfläche sauber (ROT=0), Betriebswissen an seinem richtigen
Ort, und die Grenze wird jetzt **vor dem Commit** gezogen statt nach dem Push.

---

## 1. Befund mit Belegen

| # | Beleg | Quelle |
|---|---|---|
| 1 | Lauf „Marken-Oberfläche (öffentliche Sichtbarkeit)" rot auf `main`, Commit `c1e7b30f`, 03.10.2026 20:39 | [Run 37145023336](https://github.com/frank-hartung/franksfinanzcheck-blog/actions/runs/37145023336), Job `markenflaeche`, Schritt „README als Markenfläche prüfen" |
| 2 | Vier ROT-Befunde auf der Markenfläche | `python3 scripts/brand_surface_guard.py --only readme --gate --offline` |
| 3 | `README.md:101` – „Blog**automatik** & 0 € Architektur" | Automatik-Sprache |
| 4 | `README.md:105` – „**Workflow**-Orchestrierung … `scripts/n8n_bridge.py`" | Workflow-Sprache **und** interner Dateipfad |
| 5 | `README.md:106` – „CI/CD Qualitäts-**Gates** auf Agentur-Niveau" | Gate-Sprache |
| 6 | Die Meldung selbst war öffentlich sichtbar (Issue #552, offenes Repo) | ein Betriebsalarm auf der Markenfläche ist der Fehler zweiter Ordnung |

Der Abschnitt kam mit der Whisper-/n8n-Integration vom 03.10.2026 ins README –
gut gemeint, als Schaufenster für einen sauber gebauten 0 €-Unterbau. Genau
dieses Schaufenster steht bei einer Markensuche („FranksFinanzcheck Frank
Hartung") neben dem Ratgeber: Wer die Marke prüft, liest dann „Blogautomatik"
statt „über zehn Jahre Praxis".

---

## 2. Ursache – und warum „Abschnitt löschen" zu wenig gewesen wäre

Die Wache hat **richtig** gemeldet. Falsch war der **Zeitpunkt der Frage**:

1. Gefragt wurde erst **nach dem Push** (`push`-Trigger auf `main`). Da war die
   Betriebssprache bereits öffentlich, der Lauf rot und die Fehlermeldung als
   Issue sichtbar.
2. Es gab **keine lokale Sperre**. Wer das README anfasst, bekam keinen
   Widerspruch, solange er nicht von sich aus an die Wache dachte.
3. Dieselbe Klasse war **drei Tage zuvor** schon aufgetreten (01.10.2026 – dafür
   wurde der `push`-Trigger überhaupt eingebaut). Ein Fehler, der sich in einer
   Woche wiederholt, ist kein Ausrutscher, sondern eine fehlende Leitplanke.
4. Das verschobene Wissen braucht ein **Zuhause**. Wird es nur gelöscht,
   schreibt es der Nächste wieder ins README – weil es sonst nirgends steht.

---

## 3. Was jetzt dauerhaft steht (mit Beweis)

| Maßnahme | Beweis |
|---|---|
| **README geheilt** – der technische Abschnitt ist raus, der Verweis auf die interne Doku bleibt | `npm run marke:check` → `Urteil: ROT=0 · GELB=0 · INFO=0` |
| **Wissen verschoben, nicht vernichtet** – „0 € Redaktionsarchitektur (Whisper · n8n · Pages)" steht jetzt in `docs/ENTWICKLER-WERKZEUGE.md`, inklusive Befehlen und Verweis auf Anleitung und Einbau-Protokoll | Regressionstest `WissenAmRichtigenOrt` prüft Whisper, n8n und `blogautomatik:status` in der Doku |
| **Commit-Sperre** `.githooks/pre-commit` – prüft den **gestageten** README-Stand offline in unter einer Sekunde, bevor der Commit entsteht | End-to-End-Test in einem Wegwerf-Repo: Betriebssprache → Commit scheitert mit Begründung, saubere Fassung → Commit läuft durch |
| **Wache kann fremde Fassungen prüfen** – neuer Schalter `--datei` (der Haken legt `git show :README.md` in eine temporäre Datei) | Selbsttest-Fallgruppe F17 a–d: sauber = 0, Betriebssprache = 1, fehlende Datei = 2 (keine stille Freigabe), `--datei` ohne `--only readme` = 2 |
| **Detektor bleibt beweisbar** – 16 → **17 Fallgruppen** im `--selftest` | `python3 scripts/brand_surface_guard.py --selftest` |
| **Regressionssperre im Testlauf** – `scripts/tests/test_markenflaeche_readme.py` (15 Tests) prüft den **echten** README-Stand, nicht nur ein Fixture | läuft automatisch in `unittest discover -s scripts/tests` (PR-Gate `publication-reliability-tests.yml`) |
| **Hausregel für Mensch und Agent** – „README ist Markenfläche" als DAUERVORGABE in `CLAUDE.md`, mit Ablageort, Prüfbefehl und Einschaltbefehl | `CLAUDE.md`, Abschnitt direkt vor „Redaktionelle Sprache" |
| **Sperre schaltet sich mit** – `npm install` setzt über `prepare` `core.hooksPath=.githooks`; manuell: `npm run hooks:install` | `package.json` |

### Vier Schichten statt einer

| Schicht | Wann sie greift | Wirkung |
|---|---|---|
| `.githooks/pre-commit` | beim Commit, lokal, offline | **verhindert** – nichts wird öffentlich |
| `brand-surface-guard.yml` (`markenflaeche`) | bei Push/PR auf README, Allowlist, Wache | **blockiert sichtbar** – roter Lauf mit Fundstelle |
| `unittest discover` (PR-Gate) | bei jeder Änderung unter `scripts/` | **hält den Bestand** – der echte README-Stand wird mitgeprüft |
| Tageslauf 04:20 UTC + Release-Trigger | täglich und bei jedem Release | **heilt** Releases/Tags, meldet Admin-Aufgaben als GELB |

---

## 4. Kontrolle in 30 Sekunden

```bash
npm run hooks:install        # Commit-Sperre einschalten (einmalig pro Arbeitskopie)
npm run marke:check          # Selbsttest (17 Fallgruppen) + README-Gate, offline
npm run test:marke           # 15 Regressionstests inkl. echtem Commit-Versuch
python3 scripts/brand_surface_guard.py --gate   # vollständiger Befund (mit Netz)
```

Erwartung: `✅ Selbsttest: 17 Fallgruppen bestanden` · `Urteil: ROT=0` ·
`OK (15 tests)`.

---

## 5. Was bewusst **nicht** getan wurde

- **Keine Allowlist-Ausnahme.** Ein Eintrag für „Blogautomatik" hätte den Befund
  stillgelegt statt ihn zu lösen – die Marke hätte weiter „Automatik" gesagt.
- **Keine Lockerung der Verbotsliste.** Sie ist Betriebs-, nicht Alltagssprache;
  die vier Treffer waren allesamt korrekt.
- **Kein Umbau des Alarmkanals.** Die Wache steht bewusst nicht in der
  Wacht-Liste von `alert-on-failure.yml`; dass diese Meldung trotzdem entstand,
  liegt am zentralen Fehler-Alerting und ist ein eigener Vorgang.
- **Kein Workflow-Eingriff.** Die Trigger waren richtig – falsch war nur, dass
  sie die einzige Instanz waren. Agenten-Tokens dürfen Workflow-Dateien ohnehin
  nicht anfassen (CLAUDE.md, Abschnitt CI).
- **Kein `--no-verify` in Skripten.** Der Notausgang bleibt eine bewusste
  Handbewegung eines Menschen; danach meldet der Push-Lauf weiterhin.

---

## 6. Restrisiko und Prüffrist

| Risiko | Gegenmittel | Rest |
|---|---|---|
| Arbeitskopie ohne `core.hooksPath` | `prepare` in `package.json` + Runbook-Zeile | greift erst nach einem `npm install`; Push-Gate fängt den Fall |
| Bewusstes `--no-verify` | Push-Lauf + Tageslauf | gewollt: ein Mensch darf entscheiden, muss es dann aber sehen |
| Betriebssprache in **anderen** Außenflächen (Repo-Beschreibung, Wiki, Issue-Titel) | O3/O4/O6 der Wache, `BRAND_ADMIN_TOKEN` | Admin-Aufgabe, siehe Runbook Abschnitt 3 |
| Neue Verbotsbegriffe (die Marke entwickelt sich) | `VERBOTEN`-Liste in der Wache, Selbsttest | **Prüffrist 31.12.2026**: Liste gegen den dann gültigen Markenauftritt lesen |

Hintergrund und Admin-Fahrplan: `docs/MARKEN-OBERFLAECHE-RUNBOOK.md` ·
Betriebswissen: `docs/ENTWICKLER-WERKZEUGE.md` ·
Hausregel: `CLAUDE.md`, „README ist Markenfläche (DAUERVORGABE)".
