# Workflow-Vertrags-Wache – der stille Totalausfall

**Vorgang WF-SPRACHE · 31.10.2026**

Diese Anleitung beschreibt einen Fehlertyp, der kein Fehler *im Code* ist und
deshalb von jeder bestehenden Prüfung übersehen wurde: Eine Workflow-Datei,
die syntaktisch einwandfrei ist, formal gültiges YAML enthält, von PyYAML
sauber geparst wird – und die GitHub trotzdem als Ganzes verwirft.

---

## 1. Was passiert war

Die **Sprach-Qualitäts-Pipeline** stand monatelang in der Lauf-Liste der
Actions. Sie sah aus wie ein Workflow, der läuft und scheitert. Tatsächlich
hat sie **nie eine Zeile Code ausgeführt**.

| Kennzahl | Wert |
| --- | --- |
| Läufe insgesamt | 20 |
| davon `failure` | 20 |
| davon mit **Jobs** | **0** |
| Laufzeit je Lauf | unter 1 Sekunde (`created == updated`) |
| Check-Run am Commit | keiner |
| Beteiligte Branches | `main` und alle Arbeits-Branches |

Der entscheidende Hinweis war das Ereignis: Alle 20 Läufe trugen
`event: push` – obwohl die Datei nur `schedule` und `workflow_dispatch`
deklariert. GitHub legt bei **jedem Push** einen Fehl-Lauf für eine Datei an,
die es nicht validieren kann. Das ist die Signatur des Totalausfalls: ein
Lauf, der nicht deshalb rot ist, weil ein Schritt scheiterte, sondern weil
es keinen Schritt gab.

Die Fehlermeldung steht auf der Lauf-Seite, nicht in der API:

```
Invalid workflow file: .github/workflows/sprach-qualitaet-pipeline.yml#L1
(Line: 205, Col: 19): A sequence was not expected
```

## 2. Die Ursache

```yaml
      - name: Issue bei Qualitätsverstoß eröffnen (strict)
        uses: peter-evans/create-issue-from-file@959985ac0a2ee023b3cc256977ec1a093aa4a0bf
        with:
          title: "🚨 Sprach-Qualität: offene kritische Funde (Copy-Editing-Gate)"
          content-filepath: COPY-EDITING-REPORT.md
          labels: ["qualitaet", "sprach-qualitaet", "automatisiert"]   # ← hier
```

Die `action.yml` dieser Action sagt es ausdrücklich:

```yaml
  labels:
    description: 'A comma or newline-separated list of labels'
```

Ein **kommagetrennter Text**, keine Liste. GitHub prüft die Eingaben gegen
den Vertrag der Action, sobald sie die Datei einliest – und lehnt die
**gesamte Datei** ab, nicht nur den Schritt. Deshalb: 0 Jobs, kein
Check-Run, keine Meldung.

### Der zweite, unabhängige Defekt in derselben Datei

Beim Nachprüfen der Pins kam ein zweiter toter Punkt heraus:

| Pin in der Datei | Zustand |
| --- | --- |
| `peter-evans/create-issue-from-file@959985ac0a2ee023b3cc256977ec1a093aa4a0bf` | **existiert im Action-Repo nicht** (v4.0.1 ist `433e51abf769`) |
| `actions/upload-artifact@49538c08a0826eef0d640c58a59e7a5e2b50aaef` | **existiert nicht** (kanonisch im Repo: `cf430e030ddb`, 27×, v7.0.2) |

Beide hätten den Lauf beim Ziehen der Action sterben lassen – auch nach dem
Typfix. Es ist derselbe Entstehungsweg: Die Datei wurde geschrieben, aber nie
ausgeführt; ein falscher Pin fällt dann niemandem auf.

## 3. Warum keine bestehende Wache das gefunden hat

Das Repo hat 62 Dateien, die `.github/workflows` erwähnen. Alle prüfen
Eigenschaften, die PyYAML **sehen kann**:

| Wache | prüft | warum blind |
| --- | --- | --- |
| `yaml.safe_load` in Tests | Syntax | Der Block ist gültiges YAML. Ein Dict. Fertig. |
| `trigger_wache.py` | `on:` / `paths` | Liest nur den Trigger-Ausschnitt. |
| `actions_version_guard.py` | eine Version je Action | Regel A3 lässt SHA-Pins **absichtlich** unangetastet – ein toter Pin ist für sie unsichtbar. |
| `workflow_js_wache.py` | JavaScript in `script:` | Prüft Skripte, nicht `with:`-Verträge. |
| `integrity_guard.py` | Kerndateien, Siegel | Hashes, keine Semantik. |

Dazu eine Falle, die den Befund zusätzlich verdeckt: **`yaml.safe_load` löst
`on:` zu `True` auf** (YAML-1.1-Wahrheit). Ein Test, der `daten["on"]` liest,
stürzt ab oder überspringt – und meldet dann nichts.

## 4. Was jetzt anders ist

### 4.1 Die Reparatur

```yaml
        uses: peter-evans/create-issue-from-file@433e51abf769039ee20ba1293a088ca19d573b7f # v4.0.1
        with:
          # `labels`/`assignees` sind bei dieser Action kommagetrennte
          # ZEICHENKETTEN – keine YAML-Liste.
          labels: "qualitaet, sprach-qualitaet, automatisiert"
```

und der Artefakt-Upload auf den repo-kanonischen Pin.

### 4.2 Die Wache: `scripts/workflow_vertrag_wache.py`

Sechs Regeln, genau in der Schicht zwischen YAML und GitHub:

| Regel | Prüft | Findet |
| --- | --- | --- |
| **V1** | Jeder gepinnte 40-stellige `uses:`-SHA ist beim Anbieter auflösbar | tote Pins (beide Defekte oben) |
| **V2** | Jede `with:`-Eingabe ist in der `action.yml` deklariert **und** hat den richtigen YAML-Typ | `labels: [ … ]` statt `"a, b, c"` |
| **V3** | Nur bekannte Top-Level-Schlüssel, `on:`-Auslöser, `jobs:` | `job:` statt `jobs:` |
| **V4** | Nur bekannte Job- und Schritt-Schlüssel | `argument:` statt `with:` |
| **V5** | `${{` und `}}` sind blockweise ausgeglichen | fehlendes `}}` |
| **V6** | Jeder Schritt hat `run:` **oder** `uses:` | Schritte, die nichts tun und Erfolg melden |

Eigenschaften, die für den Dauerbetrieb wichtig sind:

* **Kein Fehlalarm bei fehlendem Netz.** `--online` löst Verträge über die
  GitHub-API auf. Ist der Anbieter nicht erreichbar, wird das als *nicht
  prüfbar* behandelt, nicht als Fehler. Eine Wache, die ohne Netz rot wird,
  wird abgeschaltet – und dann ist sie keine Wache mehr.
* **Ehrliche Grenze.** Sie ist ein Offline-Vertreter für GitHubs Parser,
  keine Kopie. Sie ersetzt keinen echten Dispatch. Der einzige vollständige
  Beweis bleibt ein Lauf mit Jobs.
* **Blockweise Ausdrucksprüfung.** `if: >-` mit einem dreizeiligen `${{ … }}`
  ist gültig und kommt im Repo vor (`alert-on-failure.yml`). Eine
  Zeilenprüfung hätte dort zwei Fehlalarme erzeugt; die erste Fassung dieser
  Wache tat genau das.
* **Unterordner-Actions.** `github/codeql-action/init` liegt in einem
  Unterordner; die `action.yml` des Repo-Kopfes zu lesen ergab sechs
  Falschmeldungen. Die Wache liest den richtigen Pfad.

### 4.3 Die Verankerung

Die Wache läuft im **PR-Gate** `Integritäts-Siegel`
(`.github/workflows/integrity-lock.yml`), direkt neben der
Actions-Versions-Wache – mit Selbsttest davor, damit ein kaputter Prüfer nicht
grün meldet.

### 4.4 Der Nachweis

`scripts/tests/test_workflow_vertrag_wache.py` – 9 Proben, darunter:

* der **echte Fall** wird erkannt (Liste → V2 mit der Originalmeldung),
* die **Zeichenkette** wird nicht beanstandet,
* die **toten Pins** kehren nicht zurück (namentliche Sperre),
* **alle 98 Workflows** sind offline befundfrei,
* **Sabotage-Probe**: eine kaputte Kopie der echten Datei muss auffallen –
  sonst wäre die Suite ein Grünsager.

## 5. Bedienung

```bash
# Bericht über alle Workflows (offline: V3–V6 vollständig)
python3 scripts/workflow_vertrag_wache.py

# Mit Anbieter-Auflösung (V1/V2) – braucht GITHUB_TOKEN
python3 scripts/workflow_vertrag_wache.py --online

# CI-Vertrag: Exit 1 bei Befund
python3 scripts/workflow_vertrag_wache.py --online --gate

# Selbsttest (Sabotage-Schutz, schreibt nie)
python3 scripts/workflow_vertrag_wache.py --selftest

# Verträge lokal zwischenspeichern (für Läufe ohne Netz)
python3 scripts/workflow_vertrag_wache.py --online --schreibe-vertraege
```

## 6. Was ein Redakteur daraus mitnehmen soll

**Ein grüner Lauf beweist nicht, dass ein Workflow funktioniert – er beweist
nur, dass er stattgefunden hat.** Und ein *roter* Lauf beweist nicht, dass
etwas kaputt ist; hier bewies er, dass der Workflow gar nicht existierte.

Die drei billigen Fragen bei jedem roten Actions-Lauf:

1. **Wie viele Jobs?** Null = GitHub konnte die Datei nicht laden. Nicht der
   Code ist schuld, die Datei.
2. **Wie lange?** Unter einer Sekunde = kein Runner, kein Skript, nichts.
3. **Welches Ereignis?** Ein `push`-Ereignis bei einem Workflow, der nur
   `schedule`/`workflow_dispatch` kennt, ist ein Validierungsfehler.

Alle drei stehen ohne Login in der API:

```bash
gh api repos/OWNER/REPO/actions/runs/<id>/jobs --jq '.total_count'
gh api repos/OWNER/REPO/actions/runs/<id> \
  --jq '"\(.event) \(.created_at) \(.updated_at)"'
```

Die Fehlermeldung selbst steht nur auf der HTML-Lauf-Seite (Annotations);
`--log` ist bei einem Lauf ohne Jobs leer.

## 7. Offene Grenze

Der Fix ist am 31.10.2026 in `main` gelandet. **Ob der Workflow danach
wirklich Jobs startet, ist zum Zeitpunkt dieses Textes nicht durch einen
eigenen Dispatch bestätigt** – die Integration, mit der hier gearbeitet wird,
darf keine `workflow_dispatch`-Läufe auslösen (HTTP 403, fehlendes
`actions:write`). Der Beweis kommt beim nächsten planmäßigen Lauf (04:30 UTC)
oder durch einen Push, der den Workflow berührt.

Die Wache ist davon unabhängig richtig: Sie hat die zwei toten Pins und den
Typbruch gefunden, **bevor** irgendein Lauf das bestätigen konnte.
