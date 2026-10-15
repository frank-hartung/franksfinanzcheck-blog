# WF-E813: Die Sicherheits-Wache log – „Seite nicht erreichbar“ wurde als „Header fehlen“ gemeldet

**Stand:** 15.10.2026 · **Meldung:** [#767](https://github.com/frank-hartung/franksfinanzcheck-blog/issues/767)
· **Klasse:** teils maschinell behebbar (`machine/auto`), teils menschlich (`human`) – getrennt nach Klasse, nicht nach Bauchgefühl
· **Vertrag:** **C34** (Auswertung statt Durchreichen)

> **„🔧 Wartung · Betriebspflege · Vorgang WF-E813“** – Der erste planmäßige
> Live-Lauf der Sicherheits-Wache wurde rot: Job *„Live-Messung (täglich und auf
> Zuruf)“*, Schritt *„Sicherheits-Header der echten Seite messen (F-01)“*.

## Das Urteil in einem Satz

Die Wache hat zwei verschiedene Dinge in einen einzigen Ausgang gepresst – „die
Seite ist nicht erreichbar“ und „die Seite liefert die falschen Header“ – und
der Melder hat daraus eine Ratliste gebaut, in der ein abgelaufener
API-Schlüssel an erster Stelle stand, obwohl diese Wache **keinen Schlüssel
kennt**. Seitdem unterscheidet die Wache vier Klassen, heilt transiente
Netzfehler selbst, nennt die Ursache statt des Symptoms, und der Workflow
**wertet den Exit-Code aus**, statt ihn an GitHub durchzureichen.

---

## 1. Zeitleiste (UTC, 14./15.10.2026)

| Zeit | Ereignis | Beleg |
|---|---|---|
| 14.10. 23:49:56 | Sicherheits-Wache, `pull_request` – **grün** (nur Quellseite, offline) | Run `38656449680` |
| 14.10. 23:58:23 | Sicherheits-Wache, `push` – **grün** (nur Quellseite, offline) | Run `38657279430`, Commit `36a5e137` |
| 15.10. 11:11:03 | **Erster planmäßiger Live-Lauf überhaupt** (`schedule`) – **rot** | Run `38725521166`, Commit `683da7fb`, Job `116390346576` |
| 15.10. 11:11:40 | Meldung **#767** entsteht (Vorgang WF-E813) | Issue #767 |
| 15.10. abends | Dauerheilung: Klassifikation, Selbstheilung, Auswertung, Triage, Tests | dieser Bericht |

**Der entscheidende Satz der Zeitleiste:** Die beiden grünen Läufe davor haben
**nie gemessen**. Der `live`-Job startet nur bei `schedule` oder
`workflow_dispatch` – Push und PR prüfen ausschließlich das Repository. Der
11:11-Lauf war also der erste Kontakt der Wache mit der echten Seite. Dass
ausgerechnet er rot wurde, ist keine Überraschung, sondern ein Konstruktions-
fehler im Umgang mit dem Ergebnis.

---

## 2. Was wir nicht wissen – und warum genau das der Befund ist

Das Log des Laufs ist abgelaufen (GitHub hält Run-Logs nur begrenzt vor; der
Abruf endet in `EOF`). Es lässt sich deshalb **nicht mehr belegen**, ob am
15.10. um 11:11 UTC

- **(a) ein echter Befund** vorlag – die Seite antwortete, aber ohne HSTS,
  `X-Frame-Options` und Konsorten, weil A1 im Cloudflare-Dashboard noch nicht
  aktiv ist (Stand des Runbooks: **offen, wichtigster Schritt**), oder
- **(b) eine Störung** – die Seite war aus dem Runner heraus nicht erreichbar
  (TLS-Abbruch, DNS, kurzer 5xx von der Kante).

**Dass wir das nicht mehr sagen können, ist der eigentliche Schaden.** Die Wache
hatte die Information im Moment der Messung in der Hand und hat sie in derselben
Sekunde weggeworfen: Beide Fälle landeten in *derselben* Liste
(`fehlend_gesamt`) und erzeugten *denselben* Satz:

> „❌ N Pflicht-Header fehlen oder sind falsch.“

Direkt daneben stand in der eigenen Codezeile, dass ohne Messung der Stand als
*ungeprüft* gilt. Ungeprüft ist nicht fehlend. Ein Melder, der diese zwei
Zustände gleich behandelt, nimmt dem Betrieb die einzige Information, für die
er überhaupt existiert: **was als Nächstes zu tun ist.**

Beide Fälle sind im Übrigen real und verschieden teuer:

| | (a) Befund | (b) Störung |
|---|---|---|
| Ursache | A1 im Dashboard nicht/abschnittsweise gesetzt | Netz zwischen Runner und Kante |
| Besitzer | `human` (nur Frank, im Dashboard) | `machine` (Wiederholung heilt) |
| Nächster Schritt | Runbook A1, Schritt 1 bzw. 3 | Erreichbarkeit prüfen, Lauf neu starten |
| Alte Meldung | „API-Key abgelaufen?“ | „API-Key abgelaufen?“ |

Die alte Meldung nannte in **beiden** Fällen denselben falschen Rat. Das ist
teurer als kein Alarm: Wer dreimal wegen nichts aufschreckt, überliest den
vierten, echten Alarm (Alarm-Müdigkeit, Governance-Vertrag C4).

---

## 3. Ursachen (U1–U4)

### U1 — Die Wache zählte jede Netzstörung als fehlenden Pflicht-Header

```python
except Exception as fehler:  # noqa: BLE001 – jede Netzstörung ist ein Befund
    fehlend_gesamt.append(f"`{ziel}` nicht erreichbar ({fehler}) — "
                          "ohne Messung gilt der Stand als ungeprüft.")
```

Der Kommentar sagt es selbst: „jede Netzstörung ist ein Befund“. Genau das ist
der Fehler. Das Ergebnis war ein Bericht, dessen Schlusszeile
„Pflicht-Header fehlen oder sind falsch“ lautete, obwohl im selben Bericht
„nicht erreichbar“ stand. Der Leser muss sich entscheiden, welchem Satz er
glaubt – und die automatische Meldung hat sich für den falschen entschieden.

### U2 — Keine Wiederholung, keine Selbstheilung

Ein einzelner Versuch, 20 s Zeitlimit, kein Zurücksetzen. Ein TLS-Reset – der
häufigste flüchtige Fehler überhaupt – machte damit die Sicherheits-Tagesschau
des ganzen Tages rot. Was eine Maschine in acht Sekunden selbst heilen kann,
wurde zu einem Ticket für einen Menschen.

### U3 — Ein Kanal für zwei Aussagen (Vertrag C34 verletzt)

```yaml
- name: Sicherheits-Header der echten Seite messen (F-01)
  run: python3 scripts/blog_header_gate.py
```

Der Exit-Code ging unevaluiert an GitHub. Der Schritt konnte nur „rot“ oder
„grün“ sagen – und „rot“ bedeutete für den Melder automatisch
„Sicherheitsproblem“. Genau diese Klasse hat #676 für die Release-Scorecard
bereits beseitigt (**Auswertung statt Durchreichen**); die Sicherheits-Wache
hatte die Lehre nicht mitbekommen.

### U4 — Der Melder riet, statt zu klassifizieren

Das zentrale Fehler-Alerting bot für alle Workflows ohne Sonderregel dieselbe
Liste an: *API-Key abgelaufen · GitHub-Ausfall · transienter Fehler*. Für eine
Wache, die ausschließlich HTTP-Kopfzeilen der eigenen Seite liest, trifft
**keiner** dieser drei Punkte zu. Ein Rat, der drei Ursachen anbietet, von denen
keine zutreffen kann, ist keine Diagnose – er ist Rauschen mit freundlichem Ton.

---

## 4. Die Heilung

### H1 — Vier Klassen statt „rot oder grün“ (`scripts/blog_header_gate.py`)

| Klasse | Exit | Bedeutung |
|---|---|---|
| `OK` | 0 | alle Ziele gemessen, kein Pflicht-Fehler |
| `TEILWEISE` | 0 | ein Ziel gemessen und sauber, ein Ziel nicht erreichbar |
| `BEFUND` | 1 | ein erreichbares Ziel verfehlt das Soll |
| `STOERUNG` | 2 | kein Ziel messbar – **ausdrücklich kein Header-Befund** |

`STOERUNG` erzeugt **keinen** Eintrag in `fehlend`. Das ist die Kernregression
und ist durch einen eigenen Testfall festgenagelt:

```python
def test_netzstoerung_wandert_nie_in_die_liste_fehlender_header(self):
    (_, _, daten), _ = _messen([ABBRUCH], ziele=[gate.ZIELE[0]])
    self.assertEqual(daten["fehlend"], [], ...)
```

Warum `TEILWEISE` grün ist (kein Freibrief, sondern eine Begründung): Die
Transform Rule aus A1 filtert auf `http.host`, gilt also je **Host**, nicht je
Pfad. Ein sauber gemessenes Ziel auf dem Host belegt die Regel für die Zone.
Das nicht erreichbare Ziel wird im Bericht ausdrücklich als **„nicht gemessen“**
geführt – nie als „in Ordnung“. Ein gemessener Befund sticht eine Störung
immer (`BEFUND` gewinnt gegen `nicht_gemessen`).

### H2 — Selbstheilung gegen transiente Netzfehler

Vier Versuche mit ansteigender Pause (2 s · 8 s · 30 s) und `GET`-Nachfrage,
wenn ein Proxy auf `HEAD` mit einem Fehlerstatus antwortet (manche Kanten
behandeln `HEAD` anders als `GET`). Erst was danach noch steht, erreicht den
Melder. Damit heilt genau der Fehlerklasse, die WF-E813 ausgelöst hat, im Lauf –
ohne Ticket, ohne Nachtarbeit.

### H3 — Diagnose statt Symptom

Der Bericht prüft, ob die Zone überhaupt hinter dem Proxy liegt
(`cf-ray`, `server: cloudflare`), und nennt danach den **einen** nächsten
Schritt:

- **Proxy fehlt** → „Die Transform Rule aus A1 kann gar nicht wirken.“
  → `docs/SICHERHEIT-BETRIEB-RUNBOOK.md`, A1 Schritt 1 (Wolke auf *Proxied*),
  Schritt 2 (SSL `Full`), dann Schritt 3.
- **Proxy aktiv** → „Regel unvollständig oder überschrieben.“
  → `cloudflare/edge-schutz.md`, Abschnitt A1, Regel `FF Sicherheits-Header`.

Zwei Befunde, zwei völlig verschiedene Handlungen – vorher wäre beides als
„Header fehlen“ gemeldet worden.

### H4 — Der Workflow wertet aus (C34)

```yaml
- name: Sicherheits-Header der echten Seite messen (F-01)
  id: header
  run: |                       # set -uo pipefail, kein set -e
    python3 scripts/blog_header_gate.py --json --report f01-live.md > f01-live.json
    echo "code=$?" >> "$GITHUB_OUTPUT"

- name: Sicherheits-Header auswerten (F-01) · Befund · Störung · grün
  run: |
    cat f01-live.md >> "$GITHUB_STEP_SUMMARY"
    case "…steps.header.outputs.code" in
      0) ::notice:: grün ;;
      1) ::error:: F-01 BEFUND …        ; exit 1 ;;
      2) ::error:: F-01 STOERUNG – KEIN Header-Befund … ; exit 1 ;;
      *) ::error:: F-01 WACHE-FEHLER …  ; exit 1 ;;
    esac
```

Drei Details, die den Unterschied machen:

- Der Mess-Schritt bleibt **neutral**. Er hält den Exit nur fest; der
  Auswerte-Schritt entscheidet, *was* gemeldet wird.
- Der Bericht geht in die **Lauf-Zusammenfassung** (`GITHUB_STEP_SUMMARY`),
  nicht nur ins Log (Lehre aus INCIDENT-2026-09-19).
- Der Auswerte-Schritt heißt weiterhin *„Sicherheits-Header …“* – genau die
  Zeichenkette, an der das Alarm-Routing den Kanal erkennt. Ein Test nagelt
  diese Kopplung fest; sonst fiele die Meldung bei einer Umbenennung still auf
  den Schlüssel-Rat zurück.
- Ein roter F-01 verdeckt nicht länger die Worker-Messung (`if: always()`):
  Ein Lauf, zwei Wahrheiten.

### H5 — Der Melder rät nicht mehr

`alert-on-failure.yml` bekommt für die Sicherheits-Wache eine eigene Triage. Sie
nennt zuerst die Einordnung („Diese Wache misst ausschließlich
HTTP-Kopfzeilen … ein abgelaufener GROQ- oder GEMINI-Schlüssel kann diesen
Schritt nicht auslösen“), dann die Klasse und den zugehörigen Schritt. Der
Schlüssel-Rat bleibt dort, wo er hingehört – bei Workflows, die Schlüssel
benutzen.

**Und sie hängt an der einen Quelle, die es dafür schon gab.** Während dieser
Heilung landete #769 (WF-9E5A / #761) auf `main` – mit genau derselben
Erkenntnis für das Offsite-Backup: Eine offene Meldung blieb wörtlich so
stehen, wie der erste rote Lauf sie geschrieben hatte, und riet weiter zu
GROQ/GEMINI-Schlüsseln, obwohl längst „Einrichtung unvollständig“ feststand.
Dort wurde der Mechanismus gebaut: Jeder Body trägt die Klasse seines Rats
(`<!-- alert-runbook: … -->`); ändert sie sich, schreibt der nächste rote Lauf
die Meldung neu.

Die Sicherheits-Wache bekommt deshalb **zwei eigene Klassennamen** in
derselben Kette (`sicherheit-header`, `sicherheit-wache`) statt eines
parallelen `if`. Wäre das nicht geschehen, hätte die Automatik beim Rebase
beides textlich gemischt – und der Nachführ-Mechanismus wäre für diesen Kanal
still wirkungslos geblieben, weil die Klasse immer `allgemein` geheißen hätte.
Ein eigenes Simulations-Szenario prüft genau das: Eine offene Meldung #767 mit
altem Rat wird beim Klassenwechsel neu geschrieben und trägt danach
`<!-- alert-runbook: sicherheit-header -->`.

---

## 5. Was sich für Frank ändert

| Vorher | Nachher |
|---|---|
| Roter Lauf, Rätselraten, Ratliste mit drei unpassenden Ursachen | Roter Lauf **mit Klasse**: BEFUND · STOERUNG · WACHE-FEHLER |
| „Nicht erreichbar“ las sich wie „Header fehlen“ | „**Kein Header-Befund** – ohne Messung ist keine Lücke belegt“ |
| Ursache im Log suchen | Zusammenfassung im Lauf nennt Diagnose **und** nächsten Schritt |
| Jeder Netz-Schluckauf wird ein Ticket | Vier Versuche heilen ihn im Lauf |
| Ein Rat (API-Key), der nie zutrifft | Ein Schritt (A1 Schritt 1 oder 3), der zutrifft |

**Und solange A1 nicht aktiv ist:** Der Lauf bleibt rot – das ist gewollt und
kein Code-Fehler. Der Unterschied ist, dass die Meldung jetzt sagt, *warum*
(„Proxy nicht aktiv“) und *was zu tun ist* (Runbook A1, Schritt 1), statt einen
API-Schlüssel zu verdächtigen. Sobald A1 steht, wird der Lauf grün und die
Meldung #767 schließt sich von selbst.

---

## 6. Nachweise

```
python3 scripts/blog_header_gate.py --selftest   19 Fälle grün  (vorher 10)
python3 -m unittest scripts.tests.test_blog_header_gate
                                                  24 Tests, 24 grün  (neu)
node scripts/tests/sim/alert_scoping_sim.mjs     38 Szenarien, 38 grün (vorher 28)
python3 -m unittest scripts.tests.test_alert_scoping
                                                  22 Tests, 22 grün
npm run test:sicherheit                          alle vier Wachen grün
```

Die neuen Selbsttest-Fälle 10–19 decken die Netz-Klassen ab, nicht nur die
Header-Regeln: Störung (kein Eintrag in `fehlend`), Selbstheilung nach
abgebrochenem Versuch, `GET`-Nachfrage bei `HEAD`-Fehlerstatus, `TEILWEISE`,
„Befund sticht Störung“, Proxy-Diagnose in beide Richtungen, Versuchsprotokoll.

**Gegenproben, die den Rückfall verhindern** (eine Wache ohne Gegenprobe ist ein
Wunsch, keine Wache):

- `test_netzstoerung_wandert_nie_in_die_liste_fehlender_header` – genau die
  Zeile, die WF-E813 erzeugt hat.
- `test_der_bericht_behauptet_keine_fehlenden_header` – der Report darf bei
  Störung den Satz „fehlen oder sind falsch“ nicht enthalten.
- `test_mess_schritt_reicht_seinen_exit_nicht_durch` – verhindert die
  Rückkehr zum nackten `run: python3 scripts/blog_header_gate.py`.
- `test_auswerte_schritt_bleibt_vom_alarm_routing_findbar` – verhindert, dass
  eine Umbenennung die Triage still abschaltet.
- `test_die_triage_haengt_an_der_runbook_klasse` – verhindert, dass die
  Sicherheits-Wache auf die allgemeine Klasse zurückfällt und damit der
  Nachführ-Mechanismus aus #761 für sie verstummt.
- Simulation *„WF-E813-Reproduktion“* – führt das echte Inline-Skript des
  Alertings aus und prüft, dass der Schlüssel-Rat **nicht** im Body steht.
- Simulation *„offene Meldung bekommt beim Klassenwechsel den neuen Rat“* –
  prüft die Integration mit #769 am konkreten Fall (Issue #767).

---

## 7. Was offen bleibt

**A1 ist und bleibt eine menschliche Aufgabe** im Cloudflare-Dashboard
(Runbook A1, Schritt 1–3, danach zwingend B7 für den Datenschutz-Text). Kein
Code in diesem Repository kann das abnehmen – und genau deshalb muss die Meldung
den Weg dorthin zeigen statt einer Ratliste.

Solange A1 offen ist, bleibt der tägliche Lauf rot. Das ist ehrlich: Es ist ein
offener Sicherheitsbefund, kein Messfehler. Der Dedupe des Alertings sorgt
dafür, dass daraus genau **ein** offenes Issue entsteht, und der Auto-Close
schließt es, sobald der Lauf auf `main` wieder grün wird.

---

## 8. Lehre

1. **Ein Messwert ohne Klasse ist keiner.** „Rot“ ist kein Befund. Wer misst,
   muss sagen, ob er etwas gefunden hat oder nichts messen konnte.
2. **Wiederholung vor Alarm.** Was eine Maschine in Sekunden selbst heilen kann,
   gehört nicht in den Briefkasten eines Menschen.
3. **Der Auswerte-Schritt gehört zum Mess-Schritt** (C34). Ein Exit-Code, der
   nur durchgereicht wird, erzwingt später eine Lüge.
4. **Ein Rat, der nie zutreffen kann, ist Rauschen.** Jeder Kanal mit eigenem
   Fehlerprofil braucht seine eigene Triage – die paar Zeilen im Alerting sind
   billiger als die Stunde, die ein falscher Rat kostet.
5. **Symptom und Ursache sind verschiedene Meldungen.** „Header fehlen“ und
   „die Regel kann nicht wirken, weil der Proxy fehlt“ führen zu völlig
   verschiedenen Handlungen.

---

## 9. Dateien

| Datei | Änderung |
|---|---|
| `scripts/blog_header_gate.py` | vier Klassen, Selbstheilung, `GET`-Fallback, Proxy-Diagnose, `--report`, JSON mit `klasse`/`proxy`/`naechster_schritt`, Selbsttest 10 → 19 Fälle |
| `scripts/tests/test_blog_header_gate.py` | **neu** – 23 Tests (Klassen, Verdrahtung, Alarm-Routing) |
| `.github/workflows/sicherheits-wache.yml` | Mess-Schritt neutral, Auswerte-Schritt mit Klassen, Zusammenfassung, Worker-Messung `always()` |
| `.github/workflows/alert-on-failure.yml` | eigene Triage für die Sicherheits-Wache (kein Schlüssel-Rat) |
| `scripts/tests/sim/alert_scoping_sim.mjs` | 4 Szenarien (WF-E813, Schwester-Schritt, Klassenwechsel, Gegenprobe) |
| `scripts/tests/test_alert_scoping.py` | Identität `Sicherheits-Wache` für die Simulation |
| `package.json` | `test:sicherheit` führt die neuen Unit-Tests mit; `header:check:live:json` |
| `docs/SICHERHEIT-BETRIEB-RUNBOOK.md` | A1: Klassen-Tabelle und Exit-Codes |
| `cloudflare/edge-schutz.md` | A1: Live-Messung mit Klassifikation, Proxy-Hinweis |
| `docs/SICHERHEITSNACHWEIS-2026-10-15.md` | Nachweiszahlen aktualisiert |
