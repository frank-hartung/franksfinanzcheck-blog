# Kostensperre – Schreibschutz vor Geldflächen

**Stand 03.10.2026 · SSOT `data/kostensperre.yaml` · Wache `scripts/kostensperre.py` · Vertrag T10**

## Worum es geht

Der KI-Transportweg ist seit dem 03.10.2026 strukturell kostenfrei: Dort
*existiert* kein kostenpflichtiger Pfad mehr (Regel T1). Zwei Flächen
daneben blieben erhalten, weil sie echte Qualität liefern:

| Fläche | Premium | Kostenloser Normalbetrieb |
|---|---|---|
| Vorlese-Stimme der Artikel | ElevenLabs | `edge → piper` |
| Rechtschreibung auf ZEIT-Niveau | Premium-Prüfdienst | Offline LT1–LT4 |

Beide kosteten 0 € – aber nur, weil kein Schlüssel gesetzt war. Das ist
keine Zusicherung, sondern ein Zufall. Ein Zustand, der nur hält, solange
niemand ein Secret setzt, kippt irgendwann still: Die Automatik läuft
nachts weiter, nichts meldet einen Fehler, und die Rechnung kommt mit
einem Monat Verspätung.

## Was der Schreibschutz tut

**Ein gesetztes Secret reicht nicht mehr aus, um Geld auszugeben.**

Beide Premium-Zweige fragen vor der ersten Ausgabe
`scripts/kostensperre.py`. Die Antwort ist *fail-closed*:

* SSOT fehlt oder ist kaputt → gesperrt
* Fläche unbekannt → gesperrt
* `freigegeben` fehlt oder ist nicht exakt `true` → gesperrt
* Freigabe ohne `grund` und `datum` → gesperrt

Der letzte Punkt ist Absicht: Eine Freigabe, die niemand begründet hat,
ist kein Beschluss, sondern ein Ausrutscher beim Editieren.

Bei Sperre passiert kein Abbruch. Die Kette fällt genau so zurück wie bei
einem fehlenden Schlüssel – eine Stufe weiter, mit einer Klartextzeile im
Protokoll. Stille Downgrades gibt es nicht.

## Was er **nicht** tut

Er löscht nichts. Beide Pfade bleiben vollständig im Code. Die
Vorlese-Stimme von ElevenLabs klingt hörbar besser als `edge` – diese
Entscheidung soll ein Mensch treffen, nicht ein vergessenes Secret.

## Entsichern (wenn du es wirklich willst)

In `data/kostensperre.yaml` bei der gewünschten Fläche:

```yaml
    freigegeben: true
    grund: "Hörprobe für die Startseite, Budget 5 €/Monat"
    datum: "2026-10-15"
```

Danach:

```bash
npm run kosten:pruefen     # muss grün sein
npm run ki:transportweg    # T10 meldet die Fläche jetzt als ENTSICHERT
```

Zwei Dinge sind dabei Absicht:

1. **Es braucht einen Commit.** Ein Secret allein genügt nicht – die
   Entscheidung ist im Diff sichtbar und reviewbar.
2. **T10 meldet die offene Fläche weiterhin**, mit Begründung und Datum.
   Entsichern ist erlaubt. Unbemerkt entsichern nicht.

Zurücksperren: `freigegeben: false`. Mehr nicht.

## Kommandos

```bash
npm run kosten:sperre      # Bericht: was ist verriegelt, was läuft
npm run kosten:pruefen     # Wache, Exit 1 bei Funden (läuft in CI)
npm run test:kosten        # Selbsttest + 18 Vertragstests
python3 scripts/kostensperre.py --json
```

## Wo der Schutz verdrahtet ist

| Ort | Rolle |
|---|---|
| `data/kostensperre.yaml` | SSOT: Flächen, Regeln, Freigaben |
| `scripts/kostensperre.py` | Riegel + Wache + 11 Sabotageproben |
| `scripts/ff_voice_backends.py` → `get_elevenlabs_api_key` | Engstelle Stimme |
| `scripts/zeit_rechtschreibung.py` → `zugang_ermitteln` | Engstelle Rechtschreibung |
| `scripts/ki_transportweg.py` → **T10** | Gegenprüfung aus dem Transportweg-Vertrag |
| `scripts/governance_contract.py` → `GUARDS` | macht die Wache zur Pflicht |
| `.github/workflows/deploy.yml` | belegt den Riegel **vor** der Vertonung |
| `.github/workflows/zeit-rechtschreibung.yml` | belegt den Riegel vor der Prüfung |

## Warum T10 *und* eine eigene Wache

Zwei Verträge, die voneinander nichts wissen, laufen auseinander – und
zwar immer in die teure Richtung. `kostensperre.py` prüft den Riegel von
innen, T10 fragt ihn aus dem Transportweg-Vertrag heraus noch einmal ab.
Fällt eine der beiden weg, meldet die andere es.
