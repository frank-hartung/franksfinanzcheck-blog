# Anleitung: Kapazität der Content-Engine

> Für den Fall, dass wieder ein Tag mit zu wenigen Artikeln endet.
> Hintergrund und Beweisführung: `CONTENT-ENGINE-KAPAZITAET-PREMIUM-2026-10-02.md`

---

## In einem Satz

Die Engine kann an einem Tag nur so viele Artikel veröffentlichen, wie sie
**freie Themen in der Automatik-Bahn** hat – und diese eine Zahl beantwortet:

```bash
python3 scripts/engine_capacity.py        # oder: npm run engine:kapazitaet
```

```
✅ Engine-Kapazität: 37 frei disponierbare AUTO-Themen – Tagesziel 2 ist gedeckt (Puffer-Bedarf 6).
   Themen 187 = AUTO 141 + FACHFREIGABE 46
   frei disponierbar: AUTO 37 · FACHFREIGABE 10
   Fachfreigabe-Bahn: GESCHLOSSEN (11/3 im Prüfstapel)
   nächste AUTO-Themen: Stromanbieter wechseln … · Strom sparen im Haushalt … · Photovoltaik …
```

Der Befehl ist **nebenwirkungsfrei**: kein KI-Aufruf, keine Kosten, keine
Schreibzugriffe. Er darf jederzeit laufen, auch während die Engine arbeitet.

---

## Die zwei Bahnen

Nicht jedes Thema darf automatisch live gehen. Das ist keine Einschränkung,
sondern der Kern der YMYL-Zusage („Your Money or Your Life“): Artikel über
Versicherungen, Rente oder Kredite tragen finanzielle Verantwortung und
brauchen eine menschliche Freigabe.

| Bahn | Was | Wer gibt frei | Beispiel |
|---|---|---|---|
| **AUTO** | Alltagsthemen | die Engine selbst | „Stromanbieter wechseln“ |
| **FACHFREIGABE** | YMYL / Hochrisiko | ein Mensch | „Riester-Rente 2026“ |

Die Einteilung trifft **nicht** dieses Modul, sondern
`editorial_review_gate.classify_text()` – dieselbe Klassifikation, die
später auch den Artikel prüft. Es gibt bewusst keine zweite Musterliste,
die auseinanderlaufen könnte.

**Nur die AUTO-Zahl beantwortet die Frage „schaffen wir heute das Tagesziel?“**
Ein YMYL-Thema zu produzieren ist sinnvolle Arbeit, aber es füllt nie einen
LIVE-Slot. Deshalb zählt es nicht mit.

### Warum die Fachfreigabe-Bahn zugehen kann

Die menschliche Prüfung ist der Engpass, nicht die Produktion. Liegen mehr
als `YMYL_WIP_LIMIT` (Standard: 3) Hochrisiko-Artikel ungeprüft herum,
schließt die Bahn: Es bringt niemandem etwas, einen vierzehnten Entwurf auf
einen Stapel von dreizehn zu legen. Die Bahn öffnet wieder, wenn der Stapel
schrumpft — über den Workflow „Redaktionelle YMYL-Prüfqueue“.

---

## Wenn die Kapazität knapp ist

### Schritt 1 – Phantom-Sperren lösen (fast immer die Ursache)

```bash
python3 scripts/reserve_topics.py --abgleich   # npm run engine:abgleich
```

Das Themen-Gedächtnis merkt sich jede Produktion mit
`produziert: <slug>` und sperrt das Thema 180 Tage. Stirbt der Artikel
danach an einem Gate oder wird er später entfernt, bleibt die Sperre
trotzdem stehen – das Thema ist dann für ein halbes Jahr blockiert,
**ohne dass es je einen Artikel dazu gab**.

Am 02.10.2026 betraf das **47 von 63** Einträgen. Die Engine fand nur noch
3 freie Themen von 187, nicht weil der Pool leer war, sondern weil er
falsch verriegelt war.

Der Abgleich ist gefahrlos: Er hebt nur den *Cooldown* auf, nie den
*Dubletten-Schutz*. Ob zu einem Thema schon ein Artikel existiert,
entscheidet weiterhin `thema_kollision()` gegen den echten Bestand.
Wiederholt sich der Fund für dasselbe Thema dreimal, ist es kein
Buchhaltungsfehler mehr, sondern ein Thema, dessen Artikel immer wieder
stirbt – dann greift die 30-Tage-Sperre.

Der Pre-Flight ruft den Abgleich bei jedem Lauf automatisch auf. Manuell
braucht man ihn nur bei einer Diagnose zwischendurch.

### Schritt 2 – Gedächtnis ansehen

```bash
python3 scripts/reserve_topics.py --bericht
```

Zeigt, welche Themen gesperrt sind und warum: `produziert` (Erfolg),
Content-Fehlschlag, `[infra]`-Fehler (Provider-Ausfall, nur 1 Tag Sperre)
oder Dauerfehler.

### Schritt 3 – Prüfstapel abbauen

Steht `Fachfreigabe-Bahn: GESCHLOSSEN`, liegt die Arbeit bei einem
Menschen, nicht bei der Automatik:

```bash
python3 scripts/editorial_review_gate.py --all --report
```

Das ist bewusst **nicht** automatisierbar (C15). Die Queue läuft über das
Issue „Redaktionelle YMYL-Prüfqueue“.

### Schritt 4 – Themen nachlegen

Erst wenn 1–3 nichts bringen, ist der Pool wirklich zu klein. Dann neue
Themen in `data/topics.yaml` ergänzen. **Beim Nachlegen auf die Bahn
achten:** Zehn neue Versicherungsthemen erhöhen die AUTO-Kapazität um
null.

Zum Prüfen, bevor committet wird:

```bash
python3 -c "
import sys; sys.path.insert(0,'scripts')
import engine_capacity as ec
print(ec.bahn_fuer_thema({'title': 'Dein neues Thema hier'}))"
```

---

## Stellschrauben (Umgebungsvariablen)

| Variable | Standard | Bedeutung |
|---|---:|---|
| `MIN_ARTIKEL_PRO_TAG` | 2 | Tagesziel, gegen das die Kapazität gemessen wird |
| `YMYL_WIP_LIMIT` | 3 | Wie viele ungeprüfte Hochrisiko-Artikel die Fachbahn offen lassen |

Beide werden bei unsinnigen Werten auf einen gültigen Bereich geklemmt und
melden das als Warnung – ein Tippfehler in einem Workflow soll die Messung
nicht still verfälschen.

Das **Reserve-Ziel** (Puffer-Bedarf) ist *keine* Stellschraube dieses
Moduls: Es hat genau einen Eigentümer, `scripts/reserve_economy.py`.

---

## Wo die Zahl sonst noch auftaucht

| Ort | Was dort passiert |
|---|---|
| `scripts/bot_preflight.py` (Phase 0) | misst die Lage, löst vorher Phantom-Sperren, schreibt `::warning::` ins Actions-Log – **bricht nie ab** |
| `scripts/engine_generate.py` | wählt Themen ausschließlich aus der AUTO-Bahn |
| `scripts/engine_issue.py` | **führt den Zustandskanal** `engine-deficit`: misst die Tagesquote, öffnet/belegt/schließt das Issue und hängt die Lage als Diagnose an |

Dass der Pre-Flight bei Engpass **nicht** abbricht, ist Absicht: Ein leerer
Themenpool heilt nicht dadurch, dass die Engine stillsteht. Re-Queue-
Beförderung und Reserve-Veröffentlichung bleiben auch dann die richtige
Arbeit – sie brauchen gar keine neuen Themen.

---

## Wenn die Slots gar nicht erst starten (Slot-Wache, #601)

Am 05.10.2026 war die Kapazität top (29 freie AUTO-Themen) – und der Tag
endete trotzdem mit 1/2 LIVE, weil GitHubs Scheduler 4 von 7 planmäßigen
Slots der Content-Linie **nie gestartet** hatte. Ein Lauf, der nie startet,
wird nie rot. Deshalb gibt es die Slot-Wache:

```bash
python3 scripts/slot_wache.py --pruefen --ohne-dispatch   # Trockenlauf (npm run engine:slots)
python3 scripts/slot_wache.py --pruefen                   # verpasste Slots nachholen (CI)
npm run test:engine:slots                                 # Selbsttest + 29 Unit-Tests
```

Sie kennt die Soll-Slots aus den Workflow-Dateien selbst (geparst, nie
abgetippt), erklärt einen Slot nach **Soll + 45 Minuten ohne einzigen
Laufversuch** für verpasst und holt ihn per Dispatch nach – aber nur an
Publikationstagen und nur, solange das Tagesziel offen ist. Das
Defizit-Issue trägt seit #601 zusätzlich das Slot-Protokoll des Tages
(`Soll-Slots / verpasst / LIVE`), damit der Alarm die Ursache nennt und
nicht nur das Symptom.

Details und Beweisführung: `TAGESDEFIZIT-ENGINE-601-DAUERHEILUNG-PREMIUM-2026-10-05.md`.

---

## Wenn der Tag unter dem Mindestziel bleibt (Zustandskanal, #601/#608)

Das Fach-Issue **`engine-deficit`** ist der einzige Kanal für „LIVE unter
Mindestziel“. Es ist **kein Arbeitsauftrag, sondern ein Zustand** – und ein
Zustand endet nicht mit einem Merge, sondern nur mit einer neuen Messung.
Das ist die Lehre aus dem 05./06.10.2026: Der Tag endete 1/2, das Issue
#601 wurde um 21:21 vom Reparatur-Merge #603 geschlossen („Closes #601“),
am Ruhetag übersprang der Melder den Tag – und der nachgelieferte
Montags-Slot meldete um 00:55 UTC ehrlich rot, während das zentrale
Fehler-Alerting fail-open ein generisches Wartungs-Issue mit
API-Key-Runbook anlegen musste (#608).

```bash
npm run engine:deficit            # Zustand in einem Blick (Trockenlauf, kein Schreibzugriff)
python3 scripts/engine_issue.py --deficit   # Kanal belegen (CI: Engine, Kadenz, Produktions-Wache)
npm run test:engine:deficit       # Selbsttest + 39 Unit-Tests
```

| Frage | Antwort |
|---|---|
| **Wer besitzt den Kanal?** | Die Messung selbst (`scripts/engine_issue.py`) – nicht der Vorschlag, der die Ursache heilt, und nicht die Hand. |
| **Wann wird gemessen?** | An **jedem** Tag. Gemessen wird immer der jüngste Publikationstag (SSOT `cadence_guard.letzter_publikationstag`); an Ruhetagen belegt die Produktions-Wache (20:00 UTC) den Kanal. |
| **Wann schließt er?** | Nur durch die eigene Messung: (1) Der gemessene Tag hat das Ziel noch erreicht, oder (2) der Fehltag ist vorbei – nicht nachholbar, weil Inhalte nie nachträglich datiert werden – und ein folgender Publikationstag erreicht das Ziel nachweislich. Der Schließvermerk sagt das ausdrücklich. |
| **Was, wenn ihn jemand rot schließt?** | Die nächste Messung öffnet ihn wieder – mit Begründung. Danach schließt er sich von selbst; es entsteht kein Dauerläufer. |
| **Warum hängt das Fehler-Alerting daran?** | Die Kadenz-Endkontrolle bleibt bei einem echten Quotendefizit ehrlich rot. Das zentrale Fehler-Alerting schweigt nur, wenn dieser rote Schritt durch einen **offenen, für denselben Lauf frisch belegten** Fachkanal gedeckt ist (#602-Regel) – sonst meldet es fail-open generisch. |

Zustände: `offen` (Publikationstag läuft, Slots können noch liefern) ·
`verbucht` (Tag vorbei, nicht nachholbar – Kanal bleibt offen) ·
`erfuellt` (Ziel erreicht, Kanal schließt sich). Die Zustandslogik steht
als reine Funktion in `engine_issue.quoten_lage()`/`urteil()` und ist im
Selbsttest mit dem echten 05./06.10. nachgestellt; Regel **C23** des
Governance-Vertrags friert Besitz, Kalender-SSOT, Ruhetag-Messung, Reopen
und die Marker-Identität ein. Vorgangsbericht:
`WF-1F8C-608-DAUERHEILUNG-PREMIUM-2026-10-07.md`.

---

## Tests

```bash
npm run test:engine:kapazitaet    # Selbsttest + 20 Unit-Tests
npm run test:prompt:echo          # R16-Prompt-Echo, 14 Unit-Tests
npm run test:engine:slots         # Slot-Wache: Selbsttest + 29 Unit-Tests
npm run test:engine:deficit       # Zustandskanal: Selbsttest + 39 Unit-Tests
```

