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
| `scripts/engine_issue.py` | hängt die Lage an das Tagesdefizit-Issue, damit der Alarm seine Ursache kennt |

Dass der Pre-Flight bei Engpass **nicht** abbricht, ist Absicht: Ein leerer
Themenpool heilt nicht dadurch, dass die Engine stillsteht. Re-Queue-
Beförderung und Reserve-Veröffentlichung bleiben auch dann die richtige
Arbeit – sie brauchen gar keine neuen Themen.

---

## Tests

```bash
npm run test:engine:kapazitaet    # Selbsttest + 20 Unit-Tests
npm run test:prompt:echo          # R16-Prompt-Echo, 14 Unit-Tests
```
