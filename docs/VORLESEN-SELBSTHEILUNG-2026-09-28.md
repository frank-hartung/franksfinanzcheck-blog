# Vorlesen · Selbstheilung und Laufzeit-Härtung

**Stand:** 28.09.2026 · **FF Voice Studio**

Die Vorlese-Funktion bleibt auf dem Premium-Pfad, solange die Tonspur bzw.
die Gerätestimme gesund läuft. Ein technischer Fehler darf aber weder eine
scheinbar aktive, stumme Leiste noch einen falschen Abschluss erzeugen.

## Was dauerhaft repariert wurde

### 1. Web-Speech-Hänger nach `onstart`

Einige Browser melden `onstart`, senden danach aber kein `onend` mehr. Die
bisherige Start-Wache konnte diesen Zustand nicht erkennen, weil sie nach dem
korrekten Start abgeschaltet wurde.

Die Engine besitzt jetzt eine zweite, einheitenbezogene Stall-Wache:

- sie wartet länger als die geschätzte Sprechdauer plus Reserve;
- ein transienter Hänger startet denselben Satz automatisch neu;
- nach einer begrenzten Zahl von Recovery-Versuchen stoppt der Reader ehrlich
  mit einer verständlichen Meldung, statt Text zu überspringen oder endlos zu
  blockieren;
- Pause, Sprung, Stopp, Tonspur-Fallback und Seitenwechsel räumen den Timer
  sicher auf.

### 2. Unerwartete Unterbrechung der Studiospur

Ein HTML5-Audio-Element kann wegen Codec-, Fokus- oder Netzproblemen pausieren,
ohne ein `error`-Event zu senden. Eine Pause durch die Nutzerbedienung wird
weiterhin normal behandelt. Eine unerwartete Pause wird dagegen automatisch
kurz wieder gestartet. Erst wenn auch die Wiederaufnahme scheitert, übernimmt
die Gerätestimme.

Damit gilt weiterhin: **Premium-Ton zuerst, aber niemals Stille als Erfolg.**

### 3. Strengere Kartenhygiene ohne Altspur-Bruch

Die Tonspur-Karte prüft jetzt vor dem Start zusätzlich:

- gültige Blockindizes,
- eindeutige Chunks,
- endliche und monotone Zeitfenster,
- echte Sprechdauer.

Ältere, zusammengefasste Blockkarten bleiben kompatibel. Fehlt dort ein
Block, wird nur die Wort-/Abschnittssynchronisation zurückgestuft; die hörbare
Spur wird nicht unnötig verworfen.

### 4. Kleine Stabilitätskorrekturen

- `splitForSpeech(text, lang)` reicht die erkannte Sprache jetzt korrekt in
  jede Sprecheinheit weiter. Die EN-Regie kann dadurch nicht versehentlich
  beim Chunking verloren gehen.
- Ein Tippfehler im Tabellen-Fallback (`TTTT`) ist beseitigt.
- Laufzeitdiagnose enthält Recovery-Zähler, letzte Recovery-Art und Zeitstempel.
  Die Werte bleiben im Tab und werden nicht übertragen.

## Dauerhafte Absicherung

Die neue Suite `scripts/ff_voice_self_heal_test.mjs` simuliert die drei kritischen
Fehlerbilder mit echter DOM und der unveränderten Produktions-Engine:

1. `onstart` ohne `onend` wird geheilt und der Satz bleibt bedienbar.
2. Eine unerwartete Pause der Studiospur wird automatisch wieder angesetzt;
   nach wiederholtem Fehlschlag übernimmt die Gerätestimme.
3. Ein dauerhafter Hänger wird begrenzt und ehrlich beendet.

Das Gate `Lesehilfen-Gate (Vorlesen + Kurzfassung)` führt die Suite bei Push,
Pull Request und täglich aus. Die Toolbar-Wache verlangt außerdem, dass die
Suite im Gate verankert bleibt.

## Verifikation

- Selbstheilungs-Suite: **13/13**
- Funktionstest Vorlesen + Kurzfassung: **252/252**
- Reparatur-Pinne: **56/56**
- TTS-Härtung: **57/57**
- Stimmen-Regie: **73/73**
- Paritäts-Gate: **386/386**
- Toolbar-/Infrastruktur-Wache: **119/119**

Die Echt-Browser-Suite bleibt zusätzlich aktiv. Wenn in einer Umgebung kein
Chromium vorhanden ist, überspringt sie sich wie bisher mit einem deutlichen
Hinweis; im CI wird Chromium installiert.
