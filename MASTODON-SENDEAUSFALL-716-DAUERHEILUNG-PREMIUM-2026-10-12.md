# 🛰️ Sendeausfall #716: Warum Mastodon schwieg – und was jetzt nicht mehr schweigen kann

**Datum:** 12.10.2026 · **Bezug:** Issue #716 „Schaltwerk: Kanal Mastodon sendet
seit 48 h nicht" (Schaltwerk-Regel `stiller-kanal`) · **Auftrag:** „Bitte
dauerhaft auf Highend-Level einer Profi-Agentur heben." · **Vorgänger:**
`MASTODON-SENDEAUSFALL-PREMIUM-2026-10-04.md`, `SCHALTWERK-ZAPIER-NACHBAU-PREMIUM-2026-10-01.md`

---

## 1. Befund

Die Meldung selbst war korrekt: Der Kanal war eingerichtet, sendebereit und
hatte seit dem 10.10.2026, 18:15 Uhr nichts veröffentlicht. Der Wachhund hat
also getan, was er soll. Falsch war, **warum** der Kanal schwieg – und dass die
Meldung sieben Sekunden zu spät kam:

```
2026-10-10T18:15:58+02:00  letzter erfolgreicher Mastodon-Beitrag
2026-10-11T13:27:45        🛑 Gate blockiert: L9 Zahl ohne Beleg im Artikel: 503020
2026-10-11T20:09:39        🛑 dieselbe Blockade
2026-10-12T15:16:22        🛑 dieselbe Blockade
2026-10-12T21:17:05        ✅ Sofortheilung sendet (ref 117429543158372236)
2026-10-12T21:17:12        📨 Issue #716 wird angelegt  ← 7 s nach der Heilung
```

Sechs Einträge in `data/social/state.yaml → failures`, alle mit derselben
Begründung, alle zum selben Artikel
(`2026-09-11-50-30-20-regel-beherrsche-dein-budget-im-jahr-2026`). Fünf
verlorene Slots im Kalender (`data/social/kalender/mastodon.md`, 🚫 am 06.10.,
09.10., 11.10. zweimal, 12.10.).

## 2. Fünf Defekte, eine Kette

### 2.1 Ein Falschurteil der Fakten-Regel (Auslöser)

`social_gate.py` L9 prüfte den **rohen Text inklusive Hashtag-Block**. Der
Texter baut aus dem Keyword `50-30-20-Regel` das Hashtag `#503020Regel` – die
Ziffernfolge 503020 steht in keinem Artikel, wohl aber die drei Einzelzahlen
50 / 30 / 20. Ergebnis, für jeden der acht Winkel identisch:

```
nutzen    ok=False ['L9 Zahl ohne Beleg im Artikel: 503020']
zahl      ok=False ['L9 Zahl ohne Beleg im Artikel: 503020']
takeaway  ok=False ['L9 Zahl ohne Beleg im Artikel: 503020']
frage     ok=False ['L9 Zahl ohne Beleg im Artikel: 503020']
mythos    ok=False ['L9 Zahl ohne Beleg im Artikel: 503020']
zitat     ok=False ['L9 Zahl ohne Beleg im Artikel: 503020']
vergleich ok=False ['L9 Zahl ohne Beleg im Artikel: 503020']
thread    ok=False ['L2 kanonischer Artikel-Link fehlt', 'L4 zu wenige Hashtags: 0 < 2']
```

Ein Falschurteil in einer fail-closed-Wache ist kein Schönheitsfehler: Es
kostet Inhalt, blockiert Slots und lässt den Kanal verhungern – dieselbe
Bauart wie das L6-Falschnegativ aus PR #530, nur mit umgekehrtem Vorzeichen.

### 2.2 Verlorene Slots ohne Nachrücken

`social_studio.run_once()` markierte einen blockierten Posten als `blocked` und
ging zum nächsten über. **Niemand rückte nach.** Fünf blockierte Slots = fünf
verlorene Sendetermine = 48 Stunden Stille.

### 2.3 Ein Planer ohne Gedächtnis für Blockaden

`social_planner._candidates()` las `state["failures"]` überhaupt nicht. Ein
Artikel, der in keinem Winkel durch das Gate kam, wurde munter weiter
eingeplant – fünfmal im Bestand von `data/social/schedule.yaml`.

### 2.4 Eine Eskalation, die nicht weiß, ob sie gebraucht wird

`aktion_social_autopilot_lauf` wertete nur `sent` und `failed`. Ein Lauf mit
„0 gesendet, 0 fehlgeschlagen, 1 blockiert" galt als **Erfolg** – die
Sofortheilung meldete grün, ohne dass ein Beitrag rausgegangen war. Und
`github_issue` feuerte unbedingt: Deshalb entstand #716 sieben Sekunden,
nachdem der Kanal wieder beliefert war.

Zusätzlich trug der Dedupe-Schlüssel `stille:{kanal}` kein Datum. Marken
verfallen erst nach `STATE_KEEP_DAYS = 45` – ein zweiter Ausfall im November
wäre **nie** gemeldet worden.

### 2.5 Nebenbefund: vier weitere Kanäle waren strukturell stumm

Der Vollscan über Bestand × Playbook (44 Artikel × 10 Kanäle, alle Winkel)
zeigte vor der Reparatur:

| Kanal | in keinem Winkel sendbar | Ursache |
|---|---|---|
| LinkedIn | **44/44** | `link_position: first_comment` ließ den Hashtag-Block ersatzlos wegfallen → L4 |
| Pinterest | **44/44** | Playbook verlangte den Link im Text, die API trägt ihn als Ziel-Link → L2 |
| Instagram | 9/44 | Hashtag-Minimum 5 nicht erreichbar (7), CamelCase-Tags als „Geschrei" gemessen (2) |
| Facebook / Telegram / Reddit | je 1/44 | Pfeile aus dem Artikelbestand sprengten das Emoji-Budget → L5 |
| Mastodon | 1/44 | der Auslöser aus 2.1 |
| Bluesky / X / Threads | 0/44 | – |

LinkedIn und Pinterest wären mit hinterlegtem Token vom ersten Tag an stumm
gewesen – lautlos, denn Standby-Kanäle lösen keinen Alarm aus. Genau deshalb
gehört diese Prüfung in die Tests und nicht in den Vorfall.

## 3. Dauerheilung

### 3.1 Das Gate urteilt präziser (`scripts/social_gate.py`)

- **L9:** Der Fließtext wird ohne Hashtag-Block geprüft; jedes Hashtag einzeln.
  Eine Hashtag-Zahl gilt als belegt, wenn sie wörtlich im Material steht **oder**
  sich restlos aus belegten Zahlen zusammensetzt (`zahl_belegt()`:
  50 + 30 + 20 → 503020). Tausendertrenner zählen als Schreibweise
  (`2.800` belegt `2800`). Erfundene Zahlen blockieren weiterhin – im Text wie
  im Tag, mit eigener Meldung.
- **Threads:** Ein Thread wird als **ein** Beitrag bewertet. Link, Hashtags,
  Sprache und Fakten prüfen über alle Teile; Länge, Emoji-Budget und Teilezahl
  gelten jedem Teil, weil die Plattform jeden Teil als Post zählt. Der Winkel
  `thread` war auf Mastodon und Bluesky vorher dauerhaft unbenutzbar.
- **L7:** Die Geschrei-Kennzahl misst nur noch den Fließtext. CamelCase-Tags
  (`#DNSServerWechseln`) und Acronyme (`#WLAN`) sind Fachsprache, kein
  Geschrei – sie kippten technikstarke Ratgeber über die 12-%-Schwelle
  (17 % mit Tags, 3,7 % ohne).
- **L2:** `link_position: destination` ist neu und meint: Der Link reist als
  Ziel-Link des Beitrags (Pinterest-API), nicht durch die Beschreibung.

### 3.2 Das Textwerk hält die Kanalverträge ein (`scripts/social_copywriter.py`)

- LinkedIn: Der Hashtag-Block bleibt **immer** im Beitrag, nur der Link wandert
  in den ersten Kommentar (Reichweiten-Standard).
- `pick_hashtags()` erfüllt das Hashtag-**Minimum** des Kanals über einen
  kuratierten Schlusslicht-Pool. Die alte Zeile `add("Finanzen")` war toter
  Code – `add()` schließt genau dieses Token aus.
- `emoji_budget_halten()` baut Symbole auf das Kanalbudget zurück: Pfeile
  werden zu Gedankenstrichen, Übriges entfällt. Symbole aus dem Artikelbestand
  machen einen Beitrag nicht mehr unsendbar.
- `_compose_pin()` richtet sich nach `link_position`.

### 3.3 Der Plan plant nur Sendbares (`scripts/social_planner.py`)

- **Vorprüfung:** `build_plan(..., validator=...)` bekommt dieselbe Instanz, die
  später über den Versand entscheidet (`studio.gate_validator`). Vergeben wird
  nur ein (Kanal × Artikel × Winkel), der das Gate besteht. Abgelehnte Paare
  stehen als Befund im Plan (`gate_sperrungen`) – keine stille Auslassung.
- **Gate-Quarantäne:** Zwei Gate-Blockaden desselben Paares innerhalb von
  21 Tagen setzen es aus (`quarantiniert()`), auch aus bereits geplanten Slots.
  Sende-**fehler** der Plattform zählen bewusst nicht – die bleiben Sache der
  Versuchszähler.
- **Selbstaufhebung:** Besteht ein ausgesetztes Paar die Vorprüfung wieder
  (Artikel oder Regel repariert), hebt der Planer die Sperre im selben Lauf
  auf. Ohne diesen Schritt wäre der Ratgeber aus #716 nach der Reparatur noch
  bis zu 21 Tage gesperrt geblieben.

### 3.4 Der Versand rückt nach (`scripts/social_studio.py`)

`backfill_candidate()` + `register_backfill()`: Fällt ein fälliger Beitrag aus,
übernimmt im selben Lauf der nächstbeste **sendbare** Artikel den Termin –
innerhalb aller Betriebsgrenzen (Sperrfrist, Tageszähler, Quarantäne,
Vorprüfung). Der blockierte Posten bleibt mit Grund im Plan, der Ersatz kommt
als eigener Posten dazu; das Cockpit zählt `nachgerückt`.

Die Sofortheilung zieht nur noch einen Slot vor, der die Vorprüfung besteht –
eine Heilung, die am Gate scheitert, heilt nichts und darf nicht „versucht"
melden.

### 3.5 Das Schaltwerk meldet, was war (`schaltwerk*.py`, `data/automationen.yaml`)

- `social_autopilot_lauf` nennt alle vier Zähler und liefert `geheilt` –
  nur ein echter Versand zählt.
- Neu: **`wenn:`** pro Aktion (Zapiers „Only continue if"). Die Eskalation ist
  an `schritte.1.geheilt ist_falsch` geknüpft, der Erfolgsfall schreibt eine
  Protokollzeile. Fehlt das Feld, gilt es als falsch – die Eskalation läuft
  (Fail-safe Richtung).
- Der Trigger `kanal_stille` liefert Diagnose statt Bauchgefühl:
  `stille_stunden`, `ursache` (häufigste Gate-Blockade), `blockaden`,
  `quarantaene`, `geplant`, `datum`. Die Meldung benennt damit den Verursacher.
- `dedupe_key: stille:{kanal}:{datum}` – ein zweiter Ausfall wird wieder
  gemeldet.

## 4. Beweis

**Sendbarkeit** (Bestand × Playbook, alle Winkel, vor → nach):

```
vorher:  linkedin 44/44 · pinterest 44/44 · instagram 9/44 · facebook 1/44
         telegram 1/44 · reddit 1/44 · mastodon 1/44  (in keinem Winkel sendbar)
nachher: mastodon 0/44 · bluesky 0/44 · linkedin 0/44 · x 0/44 · threads 0/44
         facebook 0/44 · instagram 0/44 · pinterest 0/44 · telegram 0/44 · reddit 0/44
```

**Der Auslöserartikel** ist wieder in **8 von 8 Winkeln** sendbar (vorher 0 von 8):

```
vorher:  nutzen/zahl/takeaway/frage/mythos/zitat/vergleich → L9 503020 · thread → L2+L4
nachher: ['nutzen', 'zahl', 'takeaway', 'frage', 'mythos', 'zitat', 'vergleich', 'thread']
```

**Gegenproben** (ein Gate, das nur durchwinkt, wäre genauso kaputt):

```
erfundene Zahl im Text       → ok=False ['L9 Zahl ohne Beleg im Artikel: 9999']
erfundene Zahl im Hashtag    → ok=False ['L9 Zahl im Hashtag ohne Beleg: #1234EuroRegel (1234)']
"5031" bei Beleg {50,30,20}  → nicht belegt (Verkettung muss restlos aufgehen)
geschriener Fließtext        → L7 greift weiterhin
```

**Aktionskette** unter simulierter 51-Stunden-Stille (Probelauf, Stub-Adapter):

```
A · Plattform sendet:      Schritt 1 ok (geheilt=True) → Schritt 2 github_issue
                           uebersprungen „Bedingung nicht erfüllt" → Schritt 3 Protokoll
B · Plattform verweigert:  Schritt 1 fehler „Sofortheilung ohne Versand – 0 gesendet,
                           1 gescheitert" → Schritt 2 github_issue läuft → Schritt 3 uebersprungen
```

**Echter Lauf gegen den Bestand:**

```
✅ Gate-Quarantäne aufgehoben: 1 Paar/Paare bestehen die Vorprüfung wieder.
🗓️  Plan gerollt: 168 → 180 geplante Beiträge (Horizont 14 Tage).
```

**Tests:**

```
python3 -m unittest scripts.tests.test_social_autopilot \
                    scripts.tests.test_schaltwerk \
                    scripts.tests.test_social_gate_l9 \
                    scripts.tests.test_social_gate_l6 \
                    scripts.tests.test_social_perf_feedback
→ Ran 150 tests · OK

python3 -m unittest discover -s scripts/tests       → Ran 2969 tests · OK (skipped=11)
python3 scripts/selftest_clock.py --trap-modul …    → +97 Tage: alle drei Module grün
python3 scripts/selftest_ki.py --trap-workflows     → 114 Selbsttests ohne Modell/Netz
python3 scripts/social_studio.py --selftest         → grün
python3 scripts/schaltwerk.py --selftest            → grün (11 Regeln, 14 Trigger, 12 Aktionen)
```

Neu sind **42 Fälle**: `scripts/tests/test_social_gate_l9.py` (15),
`test_social_autopilot` 46 → 66, `test_schaltwerk` 36 → 43 – Kanaltreue über
den echten Bestand, Quarantäne inkl. Selbstaufhebung, Nachrücken, Ehrlichkeit
der Heilung, `wenn:`, Trigger-Diagnose.

## 5. Was sich im Betrieb ändert

- Ein Kanal kann nicht mehr wegen **eines** Artikels verstummen: Der Plan nimmt
  ihn nicht auf, und ein trotzdem blockierter Slot wird nachbesetzt.
- Ein Alarm kommt nur noch, wenn die Selbstheilung **nicht** gewirkt hat – und
  dann mit Ursache, Blockade-Zähler und Prüfpfad.
- `SOCIAL-AUTOPILOT-STATUS.md` zeigt neu „Gate-Quarantäne & Vorprüfung":
  was der Autopilot bewusst nicht einplant und warum.

## 6. Dateien

- `scripts/social_gate.py` – L9 (Hashtags, Verkettung, Trennzeichen), Thread-Bewertung, L7-Fließtext, L2 `destination`
- `scripts/social_copywriter.py` – LinkedIn-Hashtags, Minimums-Füllung, `emoji_budget_halten`, Pin-Link
- `scripts/social_planner.py` – `gate_blockaden`, `quarantiniert`, Vorprüfung in `build_plan`, Selbstaufhebung
- `scripts/social_studio.py` – `gate_validator`, `cover_source`, `backfill_candidate`, `register_backfill`, sendbare Sofortheilung, Cockpit-Abschnitt
- `scripts/schaltwerk.py` – bedingte Aktionen (`wenn:`), Zähler `aktionen_uebersprungen`
- `scripts/schaltwerk_actions.py` – ehrliches `geheilt` mit allen vier Zählern
- `scripts/schaltwerk_triggers.py` – Diagnose im `kanal_stille`-Ereignis
- `data/automationen.yaml` – Regel `stiller-kanal`: bedingte Eskalation, Datums-Dedupe, Befund-Meldung
- `data/social/channels.yaml` – Pinterest `link_position: destination`
- `scripts/tests/test_social_gate_l9.py` (neu), `scripts/tests/test_social_autopilot.py`, `scripts/tests/test_schaltwerk.py`
- `docs/ANLEITUNG-SOCIAL-AUTOPILOT.md`, `docs/ANLEITUNG-SCHALTWERK.md`

Der Vorgang #716 bekommt seinen Abschlussvermerk über den vorgesehenen Weg: Der
Pull Request trägt `Closes #716`, `vorgangs-abschluss.yml` kommentiert nach dem
Zusammenführen.
