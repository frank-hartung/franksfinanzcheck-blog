# Reparatur Issue #218 – „Deploy auf GitHub Pages (cancelled)“

**Datum:** 08.09.2026 · **Status:** behoben · **Klasse:** Ursachenreparatur (nicht Symptom)

---

## 1. Kurzfassung für Frank

Der Deploy war **nicht kaputt** – er war **zu langsam**, und die Fehlermeldung war **falsch**.

* Das Veröffentlichen der Website selbst dauert **90 Sekunden**.
* Das Erzeugen der Vorlese-Tonspuren dauerte im selben Lauf **63 bis 151 Minuten**.
* Dadurch stand ständig ein Deploy in der Warteschlange. GitHub lässt pro
  Warteschlange nur **einen** wartenden Lauf zu – jeder weitere Push wirft den
  Wartenden raus. Der bekommt dann den Stempel `cancelled`.
* Genau so ein rausgeworfener Lauf war Issue #218. **Er hat nie eine Zeile
  ausgeführt.** Es ging nichts verloren, es war nichts kaputt.
* Schlimmer: Solange dieses Phantom-Issue offen stand, hat die Dublettensperre
  des Alarm-Workflows **echte** Deploy-Fehler unterdrückt.

Drei Reparaturen: Tonspur bekommt ein Zeitbudget, der Job bekommt eine Notbremse,
das Alarmsystem lernt Phantome von echten Abbrüchen zu unterscheiden.

---

## 2. Beweislage

### 2.1 Wohin die Zeit verschwand

Schritt-Messung aus zwei echten, **erfolgreichen** Läufen:

| Schritt | Run 34129128450 | Run 34121113112 |
|---|---|---|
| Checkout + alle Gates + Hugo-Build | ~28 s | ~20 s |
| TTS-Backend installieren | 47 s | 31 s |
| **Vorlese-Tonspuren erzeugen** | **63 min 00 s** | **151 min 11 s** |
| Tonspuren nachmessen | 3 min 06 s | 2 min 59 s |
| Deploy auf gh-pages | 31 s | 31 s |
| **Gesamt** | **1 h 07 min** | **2 h 35 min** |

Die Vertonung stellte **97–99 %** der gesamten Deploy-Laufzeit.
Der eigentliche Livegang der Website: **rund 90 Sekunden.**

### 2.2 Warum „cancelled“ kein Fehler war

Abfrage der Job-Listen der gemeldeten Läufe:

| Run | Ausgang | Jobs | Bedeutung |
|---|---|---|---|
| **34148140778** (= Issue #218) | cancelled | **0** | nie gestartet – verdrängt |
| 34123667405 | cancelled | **0** | nie gestartet – verdrängt |
| 34217052055 | cancelled | **0** | nie gestartet – verdrängt |
| 34218421327 | cancelled | **0** | nie gestartet – verdrängt |
| 34140579736 | cancelled | 1 | **echter** Abbruch: 6 h 08 min → GitHub-Zeitlimit |

Vier von fünf gemeldeten „Fehlern“ hatten **null Jobs**. Sie sind nie gelaufen.

Der fünfte war ein echter Treffer – und zeigt die zweite Lücke: Ohne eigenes
`timeout-minutes` galt GitHubs Voreinstellung von **360 Minuten**. Dieser Lauf hat
sie voll ausgeschöpft und die Deploy-Warteschlange **sechs Stunden** blockiert.

### 2.3 Zustand während der Analyse (08.09.2026, 12:39 UTC)

Der Befund war live zu beobachten:

* Run `34213003459` hing seit 10:00:18 UTC – **2 h 39 min** – im Schritt
  „Vorlese-Tonspuren erzeugen“.
* Run `34222936579` wartete dahinter seit 11:51:57 UTC – **47 Minuten**.
* Der nächste Push hätte den Wartenden verdrängt → nächstes Phantom-Issue.

### 2.4 Schadensbild in Zahlen

Letzte 40 Deploy-Läufe: **23 erfolgreich, 11 abgebrochen, 4 fehlgeschlagen, 2 offen.**
Eine Abbruchquote von **27,5 %** – nahezu vollständig Phantome.

---

## 3. Ursachenkette

```
Vertonung läuft IM Deploy-Job  (63–151 min)
        └─> Deploy dauert Stunden statt Minuten
                └─> Warteschlange "pages-deploy" ist dauerbelegt
                        └─> GitHub verdrängt den wartenden Lauf -> "cancelled"
                                └─> Alerting wertet "cancelled" als Fehler
                                        └─> Phantom-Issue #218
                                                └─> Dublettensperre unterdrückt
                                                    ECHTE Deploy-Fehler
```

Zusätzlich, unabhängig: kein `timeout-minutes` → ein hängender Lauf blockiert
die Warteschlange bis zu 6 Stunden.

---

## 4. Die Reparaturen

### R1 – Zeitbudget für die Vertonung (`scripts/ff_voice_audio.py`)

Neue Option **`--max-seconds`**: eine Wanduhr-Grenze, die **ausschließlich die
teure Neusynthese** deckelt.

Warum die vorhandene Stückgrenze `--limit-new` nicht reichte: Sie zählt Artikel,
nicht Minuten. Die Dauer je Artikel schwankt stark (Länge, Netz, Backend-Retries) –
dieselben 25 Artikel brauchten einmal 63, einmal 151 Minuten.

### R2 – Warteschlangen-Treue: `break` → `continue` (gleiche Datei)

Beim Erreichen der Grenze verließ der alte Code die Schleife mit `break`.

Das war ein **stiller Audio-Verlust**: Alle nachfolgenden Artikel bekamen ihren
Tonspur-Block nicht mehr in die frisch gebaute Seite injiziert – **auch die, deren
fertige Spur längst im Cache lag.** Da `public/` bei jedem Lauf neu gebaut wird,
muss diese Injektion in *jedem* Lauf für *jeden* Artikel passieren.

Jetzt wird nur die teure Synthese übersprungen; die günstige Cache-Wiederverwendung
läuft über die **gesamte** Warteschlange weiter. Zurückgestellte Artikel werden
gezählt und im Log ausgewiesen statt verschwiegen.

### R3 – Notbremse für den Job (`.github/workflows/deploy.yml`)

`timeout-minutes: 150` statt der stillschweigenden 360. Liegt komfortabel über dem
größten geplanten Lauf (Backfill: 90 min Budget + Build + Deploy) und gibt die
Warteschlange im Störfall trotzdem schnell frei.

### R4 – Budget-Automatik (`.github/workflows/deploy.yml`)

| Auslöser | Budget |
|---|---|
| Push auf `main` (Normalfall) | **20 Minuten** |
| Manuell mit `audio_backfill = true` | **90 Minuten** |
| Manuell mit `audio_max_minutes = N` | **N Minuten** |

Erwartete Deploy-Dauer im Normalfall: **rund 25 Minuten statt 1–3 Stunden.**
Neue Eingabe `audio_max_minutes` (leer/0 = Automatik). Ungültige Eingaben fallen
sauber auf die Automatik zurück.

### R5 – Phantom-Filter im Alarmsystem (`.github/workflows/alert-on-failure.yml`)

Bei `cancelled` wird jetzt geprüft, ob der Lauf **überhaupt etwas ausgeführt hat**
(mindestens ein Schritt mit Ergebnis `success`).

* **Nichts ausgeführt** → verdrängter Wartelauf → **keine Meldung**.
* **Etwas ausgeführt** → echter Abbruch (z. B. Zeitlimit) → **Meldung wie bisher**.
* `failure` → **immer** Meldung, unverändert.
* API-Abfrage schlägt fehl → **im Zweifel melden**; eine echte Störung darf
  niemals verschluckt werden.

Dafür nötig: Workflow-Berechtigung `actions: read`.

---

## 5. Warum die Warteschlange *nicht* angefasst wurde

`cancel-in-progress: false` bleibt bewusst stehen.

Auf `true` umzustellen wäre der naheliegende, aber falsche Griff: Es würde laufende
Deploys mitten in der Vertonung abschießen – Rechenzeit verbrannt, keine Spur
erzeugt – und **echte** Abbrüche am laufenden Band produzieren.

Das Verdrängen wartender Läufe ist fachlich unkritisch: `main` ist linear, der
neuere Commit enthält den älteren bereits. Der verdrängende Lauf veröffentlicht
einen Superset-Stand. **Es geht nichts verloren.** Repariert werden musste die
Laufzeit, nicht die Warteschlange – damit sie gar nicht erst volläuft.

---

## 6. Absicherung gegen Rückfall

Neun neue Selbsttests in `scripts/ff_voice_audio.py` (hermetisch, ohne Netz und
ohne TTS-Backend):

* Drossel: Lauf bleibt erfolgreich
* Drossel: genau 1 Artikel neu vertont
* **Drossel: Warteschlange wird NICHT abgebrochen (Issue #218)**
* Drossel: Rest wird als wartend gemeldet, nicht verschwiegen
* Ohne Grenze: alle Artikel werden bearbeitet
* Ohne Grenze: nichts zurückgestellt
* Zeitbudget: Option wird angenommen
* Zeitbudget: Budget wird protokolliert
* Zeitbudget: großzügiges Budget drosselt nicht

Der dritte Test ist der eigentliche Wächter: Er schlägt an, sobald jemand das
`continue` wieder zu einem `break` macht.

**Testbilanz:**

| Prüfung | vorher | nachher |
|---|---|---|
| `ff_voice_audio.py --selftest` | 105/105 | **114/114** |
| `ff_voice_toolbar_check.py` | 118/118 | **118/118** |
| `ff_voice_backends.py --selftest` | 83/83 | **83/83** |

YAML beider Workflows validiert, das JavaScript des Alarm-Workflows
syntaxgeprüft, die Budget-Arithmetik gegen leere, negative und
Buchstaben-Eingaben getestet.

---

## 7. Erwartete Wirkung

| Kennzahl | vorher | nachher |
|---|---|---|
| Deploy-Dauer (Push) | 1–3 h | ~25 min |
| Blockade durch hängenden Lauf | bis 6 h | max. 2,5 h |
| Abbruchquote (letzte 40) | 27,5 % | ~0 % erwartet |
| Phantom-Fehlermeldungen | regelmäßig | keine |
| Audio-Verlust bei Drosselung | ja (still) | nein |
| Echte Fehler von Phantomen verdeckt | ja | nein |

**Nicht angetastet:** Vertonungsqualität, Nur-Deutsch-Vertrag, Stille-Wache,
Cache-Logik, `force_orphan`, alle Publikations-Gates. Die Tonspur-Warteschlange
arbeitet konvergent weiter – jeder Lauf setzt fort, wo der letzte aufhörte.
