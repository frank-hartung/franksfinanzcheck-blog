# Wartung · Veröffentlichung · Vorgang WF-829B (#922) — Bündel-Dauerheilung, 04.11.2026

**Vorgang:** WF-829B · **Issue:** [#922](https://github.com/frank-hartung/franksfinanzcheck-blog/issues/922)
**Auftrag:** [#1039](https://github.com/frank-hartung/franksfinanzcheck-blog/pull/1039) — „Bitte dauerhaft auf Highend-Level einer Profi-Agentur beheben."
**Stand der Messungen:** 04.11.2026, 14:05–15:20 UTC · alle Werte am echten Bestand und am echten Kalender gemessen
**Vorberichte:** `…-2026-10-29.md` · `…-2026-10-30.md` · `…-2026-11-01.md` · `…-2026-11-03.md` · `…-SIEGEL-DAUERHEILUNG-2026-11-04.md`

---

## 1. Kurzfassung

Der Vorgang war zweimal rot, und beide Male war die Ursache **nicht** der Bericht.

Der erste Befund (Siegellücke, PR #1061) ist am 04.11. geheilt und in `main`:
Der Lock war ein zeilenweiser Zusammenschnitt aus drei Fassungen, der nur
auffiel, weil ein Komma fehlte. Ohne dieses Komma wäre er gültiges JSON
gewesen — und das Gate hätte „ok" gesagt.

Der **zweite** Befund ist der eigentliche Gegenstand dieses Berichts, und er
ist unangenehmer: Die Deckungswache der Faktenfrische (C45) hat **einen**
Stichtag gemessen — „heute". Das ist der ruhigste Tag, nicht der härteste.
Die Prüftermine sind **Bündel**: 113 Seiten verteilen sich auf nur **34
Fristtage**, 29 davon mit demselben `faktencheck: 2026-10-13`. Die Wache war
am 04.11. grün — und ab dem **20.11.2026** kippt derselbe Bestand ohne eine
einzige Code-Änderung auf rot. Im Folgejahr sind **49 Kalendertage** rot.

Das ist die Definition einer Zeitbombe: nicht falsch heute, sondern falsch
ab einem Datum, das niemand im Blick hat.

| Nr. | Befund | Heilung | Stand 04.11. |
|---|---|---|---|
| **A** | C45 prüft nur den Stichtag. Der ist der ruhigste Tag — Bündel von bis zu 23 gleichtägigen Fristen bleiben unsichtbar | `spitzenlast_stichtage()` / `spitzenlast_stichtag()`: derselbe Plan, gemessen am Bündeltag — mit dem Kriterium „eine **heute frische** Seite darf später nicht zu spät kommen" | **geheilt**, mit Vorher/Nachher-Messung |
| **B** | Der Sockel 4 trägt diese Bündel nicht: an 3 von 53 geprüften Wochentagen käme eine heute frische Seite zu spät | Sockel `max_artikel_pro_lauf` **4 → 12** (Limit 16 und Nachholfrist 7 unverändert). Messung danach: **0 von 53** | **geheilt** |
| **C** | „Nicht gemessen" sah aus wie „grün": ohne Befund fehlte jede Spur der Prüfung | `spitze_geprueft` steht **immer** in den Zahlen; der Vertragstest verlangt es und verlangt `> 0` | **geheilt** |
| **D** | Ein Test hätte die neue Schicht nie bemerkt (er prüfte nur `urteil == []`) | 4 neue Verträge: Befund, Gegenprobe (kein Fehlalarm), Pflicht zur Messung, Messung im echten Baum | **geheilt** |
| **E** | Rest-Klasse: baut sich ein Alt-Rückstand über 100 Seiten auf (z. B. 31.12.2026), reicht auch Limit 16 nicht für 7 Tage | **nicht** durch einen Sockel heilbar — offener Eigentümer-Schritt (Abschnitt 6) | **offen, benannt** |
| **F** | #922 selbst: Environment `cloudflare-produktion` ohne Reviewer, ohne Branch-Regel, mit Admin-Bypass | Nicht im Repository heilbar — heute **erneut gemessen**: `--anwenden` → HTTP **403**, `--check` Exit 1, `--pruefen` 3 Ziele offen | **Inhaber** (Abschnitt 6) |

**Nichts wurde gelockert, um Grün zu erzeugen.** Der harte Stopp bleibt hart
(CLAUDE.md N-17), kein Befund wurde zur Warnung, keine Matrix geleert. Der
Sockel wurde **erhöht**, nicht gesenkt: Es wird mehr geprüft, nicht weniger.

---

## 2. Forensischer Befund — warum „heute" die falsche Frage ist

### 2.1 Die Messung, die den Fehler zeigte

Ein Kalendersweep über 400 Tage auf `main` (`59c328d9a`), mit dem Bestand vom
04.11.2026:

```
rote Tage (C45-Urteil != []): 49
erster roter Tag: 2026-11-20   (heute grün, 16 Tage später rot)
```

Die Verteilung der Fristen erklärt es:

| Kennzahl | Wert am 04.11.2026 |
|---|---|
| Seiten im Bestand | 113 (`content/posts` + `content/pillar`) |
| verschiedene Fristtage | **34** |
| größtes Bündel | **23 Seiten am 27.11.2026** |
| auffälligstes Einzelbündel | 29 Seiten mit `faktencheck: 2026-10-13` |

Ein Stichtag, der zufällig zwischen zwei Schüben liegt, sieht Reserve, wo eine
Woche später keine ist. Die Wache hat also nicht die Kadenz gemessen, sondern
die Tagesform des Kalenders.

### 2.2 Warum die vorhandene 97-Tage-Probe das nicht findet

Die CI-Uhr-Probe (`selftest_clock.py --trap-discover … --offset 97`) prüft
**einen** fremden Kalendertag. Sie fand am 04.11. tatsächlich einen Fehler —
aber nur den, der an *diesem* Tag auftrat. Ein Fix, der ausschließlich den
97-Tage-Punkt grün macht, ist eine Verabredung mit genau diesem Datum; er
sagt nichts über den 56., 57., 180. oder 365. Tag. Genau so war es: Nach dem
Merge von #1057 war +97 grün, während +56 und +57 weiterhin rot blieben.

### 2.3 Die zweite, unabhängige Fehlstelle

`test_bot_watchdog_meldetakt.AnkerDisziplinTestCase.test_rechter_baum_hat_keine_befunde`
fiel im Branch-Lauf mit aus. Ursache war **nicht** die Uhr, sondern ein
fehlender Commit: Der Branch stand einen Commit hinter `main`, ihm fehlte der
Fix aus #1057 (u. a. `scripts/governance_contract.py`). Auf `main` ist der
Test unter jeder verschobenen Uhr grün — belegt mit `--offset 0/30/97/180/365`.

Das ist die eigentliche Lehre aus dem roten PR: **Ein roter Lauf auf einem
Branch ist kein Beweis gegen `main`.** Erst der Vergleich Branch ↔ `main`
trennt „kaputt" von „veraltet".

---

## 3. Dauerhafte Heilung — vier Schichten

### Schicht 1 — Der Bündeltag wird mitgemessen (`scripts/faktenfrische_kapazitaet.py`)

`spitzenlast_stichtage()` liefert den Stichtag plus jeden Tag, an dem sich das
Bindungsbild ändern kann: jede Frist im Horizont und jeder Vorlauf-Beginn
(`frist − vorlauf_tage`). Nur dort kann ein Urteil kippen — alle anderen Tage
sind Wiederholungen.

`spitzenlast_stichtag()` prüft diese Kandidaten mit **derselben** Planrechnung
wie am Stichtag (keine zweite Formel, keine neue Schwelle) und sucht den Tag,
an dem eine **heute noch frische** Seite zu spät käme.

**Die Abgrenzung ist der Kern der Heilung.** Bewusst *nicht* gemeldet wird der
Tag, an dem längst alles überfällig ist. Dort misst man den Alt-Rückstand —
dafür gibt es `rueckstand_abgebaut` am Stichtag —, nicht die Kadenz. Hätte die
Wache dort angeschlagen, wäre **jeder** Bestand dauerhaft rot: eine Schwelle
durch die Hintertür, und die gehört in die SSOT, nicht in eine Wache.

### Schicht 2 — Das Urteil bleibt die eine Urteilsstelle (`scripts/governance_contract.py`)

`_c45_deckung()` misst beide Tage und übergibt den Spitzentag an
`c45_urteil()` — die bestehende, einzige Urteilsstelle (C19, Lektion #521).
Der Vertrag erfindet keine zweite Schwelle; er liefert nur den zweiten
Messpunkt. Der Befund nennt Datum, Zahl und Rechenweg:

> Spitzenlast reißt die Frist: am 2026-11-26 kämen 37 Seiten zu spät, die
> heute noch frisch sind. Das Budget von 4 je Lauf × 1,00 Läufe/Tag bedient
> den Zulauf nicht — die Bündelung der Prüftermine (`faktencheck` in den
> Seiten), der Takt oder das Limit in `data/agent_reach/faktenfrische.yaml`
> entscheidet. Nur den Stichtag zu messen heißt, den ruhigsten Tag des Jahres
> zu prüfen (#1039).

### Schicht 3 — „Nicht gemessen" ist nicht „grün" (`spitze_geprueft`)

Ein erster Entwurf schrieb den Spitzentag nur **bei Befund** in die Zahlen.
Dann wäre ein fehlender Schlüssel sowohl „alles in Ordnung" als auch „gar nicht
geprüft" — dieselbe Klasse wie C33. Jetzt steht `spitze_geprueft` (Anzahl
geprüfter Bündeltage) **immer** in den Zahlen, und ein eigener Test verlangt
sie und verlangt `> 0`.

### Schicht 4 — Der Sockel trägt die Bündel (`data/agent_reach/faktenfrische.yaml`)

Gemessen über 53 Wochentage (04.11.2026 – 03.11.2027), jeweils der Bündeltag:

| Sockel | Bündel-Befund |
|---|---|
| **4** (bis 04.11.2026) | **3 von 53** rot, u. a. „am 26.11. kämen 37 Seiten zu spät" |
| 6 / 8 / 10 / 11 | 3 von 53 (das Bündel ist zu groß für Feinschliff) |
| **12** (seit 04.11.2026) | **0 von 53** |

Der Sockel ist damit **erhöht** worden — 12 statt 4 Seiten je Lauf, Limit 16
und Nachholfrist 7 unverändert. Das ist keine Verschärfung der Intervalle und
keine Verlängerung des Takts; es wird so viel geprüft, wie der Zulauf verlangt.
Was das kostet, steht offen in Abschnitt 5.

---

## 4. Verifikation (04.11.2026, alles lokal ausgeführt)

| Prüfung | Ergebnis |
|---|---|
| `python3 -m unittest scripts.tests.test_faktenfrische_kapazitaet` | **47 Tests, OK** (vorher 43; 4 neue Verträge) |
| Uhr-Probe `--trap-modul …test_faktenfrische_kapazitaet` bei **0 / 30 / 97 / 180 / 365** Tagen | **OK** — vorher +56/+57 rot, jetzt grün |
| Uhr-Probe bei **+56 / +57** (Jahreswechsel) | rot — **und das ist richtig**: 103 Seiten bereits überfällig, Rückstands-Klasse (Befund E), kein Bündel-Problem |
| Volle Suite `python3 -m unittest discover -s scripts/tests` | **5182 Tests, OK** (29 skipped) |
| `python3 scripts/governance_contract.py --quick` | **45 Regeln erfüllt**, beide Richtungen |
| `python3 scripts/faktenfrische_kapazitaet.py --wache` | Exit **0** · 113 Seiten · Bedarf 2,77/Tag · Angebot 12,00/Tag · Deckung **434 %** · Rückstand in 0 Tagen abgebaut |
| `python3 scripts/artefakt_waechter.py` | 571 Artefakte heil, keine doppelten Schlüssel |
| `python3 scripts/wachen_vertrag.py` | 375 Skripte, 0 Funde |
| `python3 scripts/integrity_guard.py --gate` | **grün** (55 Kerndateien) — keine der geänderten Dateien ist Kerndatei, das Siegel musste **nicht** angefasst werden |

**Rückbauprobe (der eigentliche Beweis, dass die Wache wirkt):** Mit dem alten
Sockel 4 meldet dasselbe Urteil sofort

```
Spitzenlast reißt die Frist: am 2026-11-26 kämen 37 Seiten zu spät,
die heute noch frisch sind. (Budget 4 × 1,00 Läufe/Tag)
```

und mit Sockel 12 ist es still. Die Wache schlägt also an der Ursache an und
verstummt, wenn die Ursache weg ist — nicht, weil sie abgeschaltet wurde.

---

## 5. Grenzen dieser Heilung (bewusst benannt)

1. **Der Sockel 12 ist eine Betriebsentscheidung, keine Code-Eigenschaft.**
   Er bedeutet real: bis zu 12 Faktenprüfungen je Lauf statt 4 — mehr
   Modellaufrufe, mehr redaktionelle Last. Die Zahl ist gemessen (0 von 53),
   aber die Last ist eine Entscheidung des Inhabers. Wer sie senkt, bekommt
   den Bündel-Befund am 26.11./02.12./06.01. zurück — das ist dann korrekt
   gemeldet, nicht verschwiegen.
2. **Die 97-Tage-Probe bleibt ein Punkt, kein Kalender.** Sie ist jetzt durch
   die Bündel-Messung ergänzt, nicht ersetzt. Ein Restrisiko bleibt für
   Bündel, die erst nach dem Horizont (120 Tage) entstehen.
3. **Die Rückstands-Klasse ist nicht geheilt** (Befund E). Sie ist eine andere
   Ursache mit einem anderen Schließpfad und wird hier nicht mit einem
   größeren Limit zugedeckt.
4. **Kein Auth-Fix.** Befund F ist ein Rechtebefund (HTTP 403), kein Code.

---

## 6. Was offen bleibt

### 6.1 Inhaber-Aufgabe #922 (unverändert, heute erneut gemessen)

| Ziel | Stand 04.11.2026, 14:07 UTC | Weg |
|---|---|---|
| Required Reviewer | **fehlt** | `python3 scripts/worker_environment_einrichten.py --anwenden` → **HTTP 403** (Token ohne `Environments: write`) |
| Kein Administrator-Bypass | **aktiv** (`can_admins_bypass: true`) | nur Dashboard; keine API nimmt das Feld an (`additionalProperties: false`) |
| Branch-Regel exakt `main` | **fehlt** (`deployment_branch_policy: null`) | wie Required Reviewer — derselbe 403 |

Environment unverändert seit **2026-10-25T13:20:15Z**. `worker_environment_guard.py --check`
→ Exit 1. Die letzten drei `worker-deploy.yml`-Läufe: alle `failure`.

### 6.2 Rückstands-Klasse (Befund E) — braucht eine Entscheidung

Am 31.12.2026 stehen 103 Seiten gleichzeitig überfällig; auch Limit 16 baut
das nicht in 7 Tagen ab (`erreicht: False`, `puenktlich: False`). Drei
Schließpfade, alle außerhalb dieser Heilung:

- **Takt:** ein zweiter Lauf je Tag (cron), oder
- **Limit:** `hartes_limit_pro_lauf` über 16 — dann aber mit dem ehrlichen
  Dauer-Spitzenbetrieb-Befund, oder
- **Intervall/Bündelung:** die `faktencheck`-Daten entzerren, damit die
  Schübe nicht kollidieren.

Empfehlung: **Bündelung entzerren** (wirkt dauerhaft, kostet keinen
Dauer-Durchsatz) — aber das ist eine redaktionelle Entscheidung, keine
Code-Änderung, und deshalb hier nicht stillschweigend vorweggenommen.

---

## 7. Geänderte Dateien

| Datei | Änderung |
|---|---|
| `scripts/faktenfrische_kapazitaet.py` | `spitzenlast_stichtage()`, `spitzenlast_stichtag()`, Spitzenlast-Befund in `c45_urteil()` |
| `scripts/governance_contract.py` | `_c45_deckung()` misst den Bündeltag mit, belegt `spitze_geprueft` immer |
| `data/agent_reach/faktenfrische.yaml` | `max_artikel_pro_lauf: 4 → 12` (Limit 16, Nachholfrist 7 unverändert) |
| `scripts/tests/test_faktenfrische_kapazitaet.py` | 4 neue Verträge (43 → 47 Tests) |
| `docs/ANLEITUNG-FAKTENFRISCHE.md` | Nachzug „der Spitzentag wird mitgemessen", Sockel-Tabelle, offene Rückstands-Klasse |

---

*Geheilt, gemessen und dokumentiert am 04.11.2026. Der Bericht von gestern
bleibt gültig — er beschrieb das Siegel; dieser beschreibt, warum eine Wache,
die nur heute misst, den Fehler erst schreibt, wenn der Kalender ihn schreibt.*
