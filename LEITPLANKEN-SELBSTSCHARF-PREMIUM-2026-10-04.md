# Leitplanken, die niemanden um etwas bitten – Premium-Heilung 04.10.2026

**Vorgang:** WF-A4E0 (Meldung #552), Folgearbeit zu PR #558
**Gegenstand:** die zwei Reste, die nach der README-Heilung offen blieben
**Kurz:** Eine Leitplanke, die an einer menschlichen Handlung oder am
Zugangsrecht einer einzelnen Person hängt, ist keine Leitplanke. Beides ist
jetzt Sache des Repositorys.

---

## 1. Ausgangslage

PR #558 hat den Rückfall vom 03.10.2026 an der Ursache geheilt: README als
Markenfläche gesäubert, Technik nach `docs/ENTWICKLER-WERKZEUGE.md` verschoben,
Commit-Sperre auf den gestageten Stand, Wache um `--datei` erweitert,
15 Regressionstests. Vier Schichten: Commit-Sperre → Push-Gate → Unit-Tests →
Tageslauf.

Im Abschluss blieben zwei Sätze stehen, die beide dasselbe Muster tragen wie
der ursprüngliche Befund („die Wache meldete richtig – nur zu spät"):

1. *„Einmal pro Arbeitskopie `npm run hooks:install` ausführen, sonst ist die
   Sperre lokal nicht aktiv."*
2. *„Mein Token darf keine Issue-Kommentare schreiben – #552 bleibt deshalb
   unkommentiert."*

Das sind keine Randnotizen. Satz 1 macht die erste Schicht **optional**;
Satz 2 macht den Abschluss eines Vorgangs **vom Recht einer einzelnen Person**
abhängig. Beides fällt erst auf, wenn es zu spät ist – nach dem Push, bzw. gar
nicht.

---

## 2. Befund A – die Sperre war eine Bitte

Git führt mitgelieferte Haken aus guten Sicherheitsgründen nie von selbst aus.
Ohne Einrichtung ist `.githooks/pre-commit` in einem frischen Klon schlicht
nicht vorhanden – **lautlos**. Der Betroffene merkt nichts; er merkt es am
roten Lauf, also genau dort, wo die Betriebssprache bereits öffentlich steht.

### Was jetzt gilt

`scripts/haken_wache.py` stellt die Sperre selbst scharf, an jedem Eingang,
den eine Arbeitskopie realistisch nimmt:

| Eingang | Wirkung |
|---|---|
| `npm install` | `prepare` ruft den Wächter (leise) |
| `npm run marke:check` | wer die Markenfläche prüft, bekommt die Sperre mit |
| `npm run hooks:install` | ausdrücklicher Befehl, idempotent |
| `npm run hooks:status` / `hooks:check` | Zustandsbericht bzw. Exit 1, wenn nicht scharf |

**Mit Nachprüfung:** Scharf gilt nur, was nach dem Schreiben zurückgelesen
wurde. **Offline, ohne Zugangsrecht, unter einer Sekunde.**

### Die Entscheidung, auf die es ankam

Der naheliegende Weg – `core.hooksPath=.githooks` – war der Weg von PR #558.
Er hat einen Fehler derselben Art wie der Vorfall selbst: Er legt **alle**
anderen Haken der Arbeitskopie still, lautlos. In dieser Werkstatt traf das
sofort einen echten Haken (`commit-msg`, der eine Mitautoren-Zeile anhängt);
in fremden Arbeitskopien träfe es Signatur-, Trailer- oder Lint-Haken.

Eingehängt wird deshalb als **Weiterleitung** in die Ablage, die git wirklich
benutzt (`git rev-parse --git-path hooks`):

- ein vorhandener `pre-commit` wird **bewahrt** (`pre-commit.lokal`) und läuft
  weiterhin – vor der Markenflächen-Sperre;
- Arbeitskopien mit dem alten `core.hooksPath` bleiben gültig und werden
  umgezogen, **sobald** die Einstellung echte Haken stilllegt – mit Begründung
  im Protokoll;
- ein fremdes Hakenwerkzeug (`.husky`) wird **nie** überschrieben, sondern mit
  zwei konkreten Wegen gemeldet;
- ohne Git-Arbeitsbaum (Export, Tarball) ist der Lauf grün und still –
  `npm install` scheitert daran nicht.

### Beweislage

- `python3 scripts/haken_wache.py --selftest` – **11 Fallgruppen** in echten
  Wegwerf-Repos, inklusive echter Commit-Versuche in beide Richtungen
  (Betriebssprache blockiert, saubere Markenfläche frei), bewahrter Fremdhaken
  läuft weiter, Altbestand zieht um, fremde Ablage unangetastet, fehlender
  Haken = defekt (nicht „scharf"), alter Stand ohne Sperre bleibt arbeitsfähig.
- `scripts/tests/test_haken_wache.py` – **19 Regressionstests**, davon ein
  Block ausdrücklich auf die Verdrahtung (`prepare`, `marke:check`,
  `hooks:*`): Fällt eine Zeile aus `package.json`, fällt es im Gate auf.
- Läuft im PR-Lauf der Marken-Wache (`brand-surface-guard.yml`) und in den
  Regressionstests mit; `.githooks/**` löst beide jetzt aus.

---

## 3. Befund B – der Abschluss hing an einer Person

Meldung #552 schloss sich über „Closes #552" beim Zusammenführen – stumm. Der
Versuch, den Vermerk von Hand nachzutragen, scheiterte mit **HTTP 403**:
Das persönliche Zugangsrecht darf keine Kommentare schreiben. Nachgestellt und
belegt am 04.10.2026 mit dem neuen Werkzeug im Schreibmodus.

### Was jetzt gilt

`.github/workflows/vorgangs-abschluss.yml` schreibt den Vermerk mit dem Recht,
das der Lauf ohnehin bekommt (`issues: write`) – **zwei Wege**, damit kein
Vermerk verloren geht:

1. **Sofort** beim Zusammenführen eines Änderungsvorschlags.
2. **Nachtrag** täglich 04:40 UTC über die zuletzt zusammengeführten
   Vorschläge – was fehlt, wird nachgetragen. Begründung: Ereignisse fallen
   belegbar aus (Vorfall 18.09.2026, ~35 % der `workflow_run`-Ereignisse kamen
   nie an), Läufe brechen ab, Rechte fehlen zeitweise.

Eigenschaften:

- **Wiederholbar** über einen unsichtbaren Marker
  (`<!-- vorgangs-abschluss: PR-N -->`) – zweimal laufen lassen schadet nie.
- **Nachprüfung:** geschrieben gilt nur, was zurückgelesen wurde.
- **Markenfläche:** Issue-Kommentare sind öffentlich und werden indexiert. Der
  Text läuft vor dem Absenden durch `scripts/brand_surface_guard.py`. Trägt der
  Titel des Vorschlags Betriebssprache, geht die **neutrale Kurzform** raus –
  lieber knapp als öffentliche Betriebsgeschichte.
- **Kein fremder Code:** `pull_request_target` checkt den Zielzweig aus; vom
  Vorschlag werden nur Nummer, Titel und Beschreibung gelesen.
- **Fehlendes Recht ist sichtbar**, nicht still: Der Lauf wird rot und benennt
  `issues: write`.

### Beweislage

- `python3 scripts/vorgangs_abschluss.py --selftest` – **12 Fallgruppen** mit
  nachgebauter API: Schlüsselwörter erkannt, Vermerk vollständig und markenrein,
  Betriebssprache abgefangen, Planmodus schreibfrei, zweiter Lauf still,
  fehlendes Schreibrecht benannt, unbelegter Vermerk = Fehler, Zeitfenster des
  Nachlaufs eingehalten, Vorschlag ohne Meldung erzeugt keinen Lärm.
- `scripts/tests/test_vorgangs_abschluss.py` – **15 Regressionstests**, davon
  fünf auf den Lauf selbst (Recht, beide Wege, Selbsttest, kein fremder Code).

### Meldung #552

Der Vermerk wird vom Repository gesetzt, sobald dieser Stand auf `main` ist –
entweder sofort (dieser Vorschlag trägt `Closes`-Bezug nicht auf #552, deshalb
greift) der tägliche Nachlauf, der #558 im Zeitfenster findet und den fehlenden
Vermerk an #552 nachträgt. Ohne Handarbeit, ohne persönliches Recht. Auslösen
von Hand (nach dem Zusammenführen, falls es schneller gehen soll):
`gh workflow run vorgangs-abschluss.yml -f pr=558`.

---

## 4. Was bewusst **nicht** getan wurde

- **Keine Lockerung der Verbotsliste**, keine Allowlist-Ausnahme, kein Eingriff
  in bestehende Abläufe.
- **Kein Überschreiben fremder Haken.** Lieber melden als heimlich gewinnen.
- **Keine Alarm-Meldung** für einen fehlenden Abschlussvermerk: Ein Alarm-Issue
  wäre selbst eine öffentliche Fläche. Sichtbar wird es am roten Lauf und in
  der Job-Zusammenfassung; der Nachlauf versucht es am nächsten Tag erneut.
- **Kein Zwang zur Einrichtung per CI-Prüfung.** Ob ein Haken lokal scharf ist,
  kann die CI nicht wissen; der Weg ist Selbstscharfstellung plus das Gate, das
  ohnehin blockiert.
- **README unberührt** – es ist Markenfläche; alles Technische steht in
  `docs/ENTWICKLER-WERKZEUGE.md`.

---

## 5. Restrisiken, ehrlich benannt

| Risiko | Einschätzung | Auffangnetz |
|---|---|---|
| Jemand klont, commitet sofort und nutzt nie npm | möglich | Push-Gate blockiert sichtbar; der nächste `marke:check` stellt scharf |
| `git commit --no-verify` | bewusster Notausgang | Push-Gate + Tageslauf |
| Dateisystem ohne Ausführungsrecht (Windows-Freigabe) | selten | Wächter meldet `defekt` mit konkretem Befehl statt stiller Freigabe |
| Fremdes Hakenwerkzeug im Arbeitsbaum | selten | Zustand `fremd` mit zwei Wegen – nichts wird überschrieben |
| `pull_request_target`-Ereignis fällt aus | belegt möglich | täglicher Nachlauf |
| Meldung ohne `Closes`-Bezug | möglich | `npm run vorgang:abschluss -- --pr N --issue M --apply` |

---

## 6. Kontrolle in 60 Sekunden

```bash
npm run hooks:status            # steht die Sperre in dieser Arbeitskopie?
npm run test:haken              # 11 Fallgruppen + 19 Regressionstests
npm run test:vorgang            # 12 Fallgruppen + 15 Regressionstests
npm run test:marke              # Wache + Wächter + Bestand
npm run vorgang:nachtrag -- --tage 14   # Plan: fehlt irgendwo ein Vermerk?
```

**Stand:** 04.10.2026 · Vorgang WF-A4E0 · Werkzeuge:
`scripts/haken_wache.py`, `scripts/vorgangs_abschluss.py` ·
Läufe: `brand-surface-guard.yml` (erweitert), `vorgangs-abschluss.yml` (neu) ·
Doku: `docs/ENTWICKLER-WERKZEUGE.md`, `docs/MARKEN-OBERFLAECHE-RUNBOOK.md`
Abschnitt 8.
