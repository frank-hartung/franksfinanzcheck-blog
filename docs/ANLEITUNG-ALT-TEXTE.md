# Anleitung: KI-Vorschläge für Cover-Alt-Texte

Stand: 08.10.2026 · Skript: `scripts/alt_text_vorschlaege.py` · Tests: `scripts/tests/test_alt_text_vorschlaege.py`
Vorschläge: `data/alt_texte/vorschlaege.yaml` (versioniert)
Redaktionsstandard (verbindlich für Entscheidung und Prüfung): `docs/ALT-TEXT-REDAKTIONSSTANDARD.md`

## Befund

- 81 Seiten haben ein Titelbild. Alle haben einen `cover.alt`. Es fehlt also kein Alt-Text.
- **53 davon sind nur eine Kopie des Seitentitels.** Das hilft Screenreader-Nutzern nicht.
  Die Zählung kommt aus `--report` (Stand 08.10.2026).
- 28 Alt-Texte beschreiben bereits etwas. Die bleiben unberührt.

Ziel des Skripts: für die 53 Titel-Kopien beschreibende Vorschläge erzeugen,
die ein Mensch freigibt.

## Regeln (verbindlich)

- **Nur Vorschläge.** Kein Befehl schreibt Alt-Texte ohne Freigabe.
- **Freigabe braucht einen Namen.** `freigegeben: true` allein reicht nicht,
  `freigegeben_von` muss ausgefüllt sein.
- **Kein Überschreiben fremder Änderungen.** Stimmt der aktuelle Alt-Text nicht
  mehr mit dem Stand des Vorschlags überein, wird der Vorschlag als „veraltet“
  abgewiesen.
- **Kein automatisches Anwenden.** Einziger Actions-Aufruf ist der manuelle Workflow
  `.github/workflows/alt-text-gemini-probe.yml`: `workflow_dispatch`, genau
  `--vorschlagen --max 1`, schreibgeschützte Berechtigungen, kein Commit; das Ergebnis
  wird als Artifact abgelegt. Der Workflow muss zuerst in den Default-Branch gemergt
  werden, bevor GitHub ihn dispatchen kann. Ein Test prüft diese Grenzen.
- **Nur das Titelbild** wird an den Anbieter geschickt. Keine Personendaten.
- Anbieter: Google Gemini, Gratis-Tier, Modell `gemini-3-flash-preview`
  (wie in `data/ki_transportweg.yaml`). Kein kostenpflichtiger Weg.
- **Ein Transportweg:** Der Modellaufruf geht ausschließlich durch
  `scripts/llm_client.py` (T6 des KI-Transportwegs) – ein Ort für Schlüssel,
  Retries und Kosten. Das Gate `scripts/ki_transportweg.py` prüft das auch
  für dieses Skript; eine Nebenstrecke neben dem Client wird gemeldet.

## Ablauf

```bash
# 1. Stand prüfen
python3 scripts/alt_text_vorschlaege.py --report

# 2. Vorschläge holen (lokal, Schlüssel nur für diese Shell)
export GEMINI_API_KEY=…            # nie in Dateien, nie committen
python3 scripts/alt_text_vorschlaege.py --vorschlagen --max 10

# 3. Prüfen: data/alt_texte/vorschlaege.yaml öffnen.
#    Text bei Bedarf im Feld „vorschlag“ korrigieren. Dann setzen:
#      freigegeben: true
#      freigegeben_von: "Frank Hartung"

# 4. Trockenlauf, dann anwenden
python3 scripts/alt_text_vorschlaege.py --anwenden --trocken
python3 scripts/alt_text_vorschlaege.py --anwenden

# 5. Prüfen und committen: geänderte content/…/index.md und die YAML-Datei
python3 scripts/alt_text_vorschlaege.py --selftest
```

`--vorschlagen` verarbeitet höchstens `--max` Seiten pro Lauf (Standard 10) und
pausiert zwischen den Anfragen. Gratis-Kontingente sind knapp. Bereits erzeugte
Vorschläge bleiben erhalten, auch wenn sie noch nicht geprüft sind.

Ohne `GEMINI_API_KEY` meldet das Skript „übersprungen“, beendet sich mit Exit 0
und schreibt nichts.

## Manueller Gemini-Probelauf in GitHub Actions

Der Workflow `.github/workflows/alt-text-gemini-probe.yml` ist bewusst nur über
`workflow_dispatch` startbar. **Er muss zuerst in den Default-Branch gemergt
werden**, bevor GitHub ihn zur manuellen Ausführung anbietet. Der Workflow führt
exakt `python scripts/alt_text_vorschlaege.py --vorschlagen --max 1` aus und
lädt Protokoll, Vorschlagsdatei und Diff als Artifact hoch. Er hat nur
`contents: read`, persistiert keine Checkout-Credentials und committet oder pusht
keine Repository-Änderungen. Den Artifact anschließend im Actions-Lauf öffnen;
ein echter Gemini-Aufruf ist erst mit diesem Workflow validiert.

## Qualitätsregeln für den Text

Das Skript verwirft automatisch:

- mehr als 125 Zeichen,
- Einleitungen wie „Bild von“ oder „Foto:“,
- Mehrzeiler,
- eine wörtliche Wiederholung des Seitentitels.

Der Mensch prüft zusätzlich:

- Beschreibt der Text das sichtbare Motiv? Keine Dinge, die man nicht sieht.
- Steht Text im Bild (Logo, Schrift)? Dann muss der Alt-Text ihn wiedergeben.
- Keine Preise, Zinssätze oder Versprechen, die nicht im Bild stehen.

## Datenschutz und Recht

- Es werden nur Titelbilder der eigenen Seite gesendet. Das sind öffentlich zugängliche Dateien.
- Im Gratis-Tier gelten Googles Nutzungsbedingungen. Dort können Eingaben zur Verbesserung der Produkte
  genutzt werden. Deshalb nur öffentliche Bilder schicken, keine internen Entwürfe.
- Die Pflicht zur KI-Kennzeichnung nach EU AI Act Art. 50 betrifft generierte Inhalte für die
  Öffentlichkeit. Alt-Texte sind Barrierefreiheits-Metadaten und keine eigenen Inhalte. Das ist keine
  Rechtsberatung. Wer das abweichend sieht, meldet es.

## Grenzen

- Der Live-Aufruf ist im Entwicklungs-Sandkasten nicht getestet (der Gemini-Host war
  dort nicht freigegeben). Getestet sind der Weg durch `scripts/llm_client.py` (Bildteil,
  Payload) und die Verarbeitung mit einem Fake-Anbieter. Beim ersten echten Lauf also
  `--max 1` verwenden und das Ergebnis ansehen.
- Der Vergleich mit dem Bild findet nur über die Anfrage statt. Das Skript prüft nicht,
  ob der Text inhaltlich stimmt. Das bleibt die Aufgabe des Menschen.
