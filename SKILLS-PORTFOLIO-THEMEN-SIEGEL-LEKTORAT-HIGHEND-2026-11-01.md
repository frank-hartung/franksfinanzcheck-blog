# Welche Themen bedient der Blog? – Portfolio, Siegel, Lektorat im eigenen Haus (Highend, 01.11.2026)

> Status: umgesetzt, gemessen, geprüft. Fortsetzung von
> `SKILLS-BIBLIOTHEK-VOLLBESTAND-HIGHEND-2026-11-01.md` (Vollbestand + Rückbau).
> Betriebsanleitung: `docs/ANLEITUNG-SKILLS.md` (Vertrag K1–K10, Portfolio P1–P7).

## Die Frage, die keinen Ort hatte

Nach dem Rückbau um `sms`/`paywalls`/`aso` stand die richtige Frage im Raum:
**Welche Themen bedient der Blog überhaupt?** Sie war nicht zu beantworten,
weil niemand sie aufgeschrieben hatte. Man konnte nur raten – und Raten kostet
hier 200 Tokens pro Session und Skill.

Der Blog beantwortet sie selbst, wenn man ihn fragt. Gemessen am 01.11.2026:

| Befund | Wert |
|---|---|
| Artikel mit `pillar:` im Frontmatter | **105** (plus 6 Pillar-Kacheln, 140 Markdown-Dateien gesamt) |
| Themenwelten (`data/themenwelten.json`) | **6** – strom-sparen (33 Artikel), frugalismus (25), internet-dsl (18), konto-karten (10), mietwagen (9), versicherungen (8) |
| Kanäle mit Beleg im Baum | Newsletter (`newsletter-worker`), Pinterest (`scripts/pinterest_ziele.py`), Mastodon, Instagram (`scripts/social_video.py`), Suche (`scripts/gsc_abdeckung.py`), Presse (`content/presse`) |
| Werkzeuge | 10 Seiten unter `content/werkzeuge` |
| Fremd-Skills von `main` übernommen | `animate` (emilkowalski/skills, MIT) – beim Neuaufsetzen auf `origin/main` bewahrt und dem Kanal Werkzeuge zugeordnet |

Die Antwort hat damit zwei Hälften, und nur eine davon kauft Skills ein:
**sechs Inhaltswelten**, die die Content-Engine mit Artikeln füllt, und **sechs
Kanäle**, an denen Redaktion und Technik arbeiten.

## Der Ort: `data/skill_portfolio.yaml` + `scripts/skills_portfolio.py`

Das Portfolio ist die eine Zuordnung – jedes der 57 Fremd-Skills steht entweder
unter `produktion` (Thema, Rolle, belegter Kanal) oder unter `ausgeschlossen`
(Grund, Entscheidung, Frist). Der Lauf prüft P1–P7:

| Klasse | Frage | Fund heißt |
|---|---|---|
| P1 | Ist jedes installierte Fremd-Skill entschieden? | Dauerlast ohne Zweck |
| P2 | Hat jedes Thema und jeder Kanal einen existierenden Belegpfad? | Behauptung statt Betrieb |
| P3 | Bleibt der Themenbetrieb im Budget? | Wachstum ohne Entscheidung |
| P4 | Hat jedes Kanal-Thema ein Skill, jedes Skill eine `rolle` und belegte Kanäle? | Achse ohne Fahrer / Kanal, den es nicht gibt |
| P5 | Trägt jeder Ausschluss Grund, Entscheidung, Frist? | Stille Abschaffung |
| P6 | Steht kein Skill auf beiden Seiten? | Eine Entscheidung, zwei Antworten |
| P7 | Hat jedes Inhaltsthema Artikel (`pillar:`)? | Leere Kachel auf der Startseite |

Die Klasse `art: inhalt | kanal` ist dabei keine Formalie, sondern die
Antwort selbst: Ein **Inhaltsthema** ohne Marketing-Skill ist der Normalfall
(es wird von der Engine bedient) – ein **Kanal** ohne Skill ist ein Loch.
Genau diese Verwechslung hätte die erste Fassung der Wache fast produziert:
sie meldete sechs „Themen ohne Skill", die in Wahrheit sechs gut gefüllte
Themenwelten sind. Aufgefallen ist es beim ersten Lauf, nicht im Bericht.

## Was jetzt entschieden ist (gemessen, nicht geschätzt)

**29 Skills und 5.502 Tokens** dienen einem Thema:

| Thema | Skills | Tokens |
|---|---|---|
| suche-und-ki-sichtbarkeit | 7 | 1.332 |
| werkzeuge-und-oberflaeche | 9 | 1.309 |
| bestand-und-messung | 4 | 921 |
| verbreitung | 3 | 665 |
| wettbewerb | 3 | 657 |
| text-und-redaktion | 3 | 618 |

**31 Skills** sind ausgeschlossen, jeder mit Grund, Entscheidung und Frist
(2027-03-31, Plattformfälle 2027-06-30). Die Begründungen sind thematisch, nicht
geschmacklich – drei Beispiele:

* `ads`, `ad-creative`, `pricing`, `offers`, `paywalls` – der Blog verkauft kein
  Produkt; „Offerte" ist hier Rat, kein Warenkorb.
* `cold-email`, `prospecting`, `revops`, `sales-enablement` – es gibt kein
  Verkaufsteam; bei Kaltakquise kommt UWG §7 als rote Linie dazu.
* `community-marketing`, `events`, `influencer-marketing`, `referrals` – Kanäle,
  die im Baum keinen Beleg haben. Ein Skill für Discord ist keine Reserve,
  sondern eine Annahme.

Zwei Werkzeuge des Agenten (`agent-reach`, `skill-creator`) bleiben installiert
und sind bewusst **nicht** Teil des Themen-Budgets – sie dienen dem Betrieb,
nicht dem Marketing. Das steht als Ausnahme im Register, nicht als Lücke.

## Die zwei K8-Siegelfälle: geschlossen, nicht beschwichtigt

K8 hatte einen richtigen Befund und eine falsche Schlussfolgerung. Der Befund:
`scripts/skills_vertrag.py` und `data/skill_lizenzen.json` entscheiden, ob der
Kern sein Budget hält und ob fremder Code lizenziert ist – und standen weder in
`FEST`/`KRITISCH` noch im Siegel. Wer sie tauscht, tauscht den Bestand lautlos.
Die falsche Schlussfolgerung war „Zeichnen ist Betreiberakt, also später".

Warum es *nicht* bloß Betreiberwillkür war: `--add` ist seit dem 16.10.2026
fail-closed (WF-6F7F/#783) – ein Pfad, der nur per `--add` in die Map kommt,
verschwindet bei der nächsten Signatur wieder. Ein „schnelles --add" hätte ein
Siegel erzeugt, das aussieht wie Schutz und keiner ist. Genau diese Klasse hat
den Repo am 19.09.2026 (Issue #316) Produktion gekostet.

Deshalb in dieser Reihenfolge, in einem Zug:

1. **Quelle zuerst:** vier Pfade unter `FEST` in `scripts/integrity_guard.py` –
   `scripts/skills_vertrag.py`, `data/skill_lizenzen.json` und die beiden neuen
   (`scripts/skills_portfolio.py`, `data/skill_portfolio.yaml`).
2. **Dann zeichnen:** `--add` je Pfad (4 × „neu unter Siegel", Kette + Map-Prüfsumme).
3. **Dann der belegte Fremd-Drift:** `--heal` signierte `scripts/redaktions_standard.py`
   (seit `359e51d` auf `main`, Arbeitsbaum = HEAD, FEST, nicht KRITISCH, Herkunft
   in `audit` und `data/integrity_history.jsonl`).

Ergebnis: `--gate` **Exit 0**, `skills_vertrag.py` **0 Befunde, 0 Warnungen**
(vorher 2) — und das Siegel trägt jetzt auch die Datei, die darüber entscheidet,
welches Skill Dauerlast zahlen darf. Ein Siegel über einer ungezeichneten
Budget-Wache wäre Papier.

## Der `copy-editing`-Fall aus K10: Umzug statt Rettung

Die deutsche Lektorats-Ausgabe lag seit dem 21.09.2026 in **fremdem Haus**
(`.claude/skills/copy-editing/`). Sie war damit eine Löschung auf Zeit – und
genau das ist am 01.11.2026 passiert. Die erste Reaktion (aus Git
wiederherstellen) war Rettung, kein Betriebsmodell: derselbe Ordner wird beim
nächsten `update` erneut überschrieben.

Die Heilung ist der Umzug:

```
.claude/skills/copy-editing/SKILL_DE.md                  →  .claude/skills/ff-lektorat/SKILL.md
.claude/skills/copy-editing/references/ai-tells-de.md     →  …/ff-lektorat/references/ai-tells.md
.claude/skills/copy-editing/references/checkliste-de.md   →  …/ff-lektorat/references/checkliste.md
.claude/skills/copy-editing/references/werkzeugkette-de.md→  …/ff-lektorat/references/werkzeugkette.md
.claude/skills/copy-editing/references/ymyl-panel-de.md   →  …/ff-lektorat/references/ymyl-panel.md
.claude/skills/copy-editing/evals/evals-de.json           →  …/ff-lektorat/evals/evals.md
```

Im eigenen Haus gelten dann auch die eigenen Regeln – und drei davon waren
verletzt, was erst durch den Umzug sichtbar wurde:

1. **K2:** `name: copy-editing-de` passte nicht zum Ordner. Jetzt `ff-lektorat`,
   Router-Zeile im Kern, Eintrag in `data/skill_lizenzen.json` unter `eigene`.
2. **K1:** 242 Zeilen Einstieg, erlaubt sind 200. Die sieben Pässe, der
   AI-Tell-Check, das YMYL-Panel und der Quick-Pass sind **wörtlich** nach
   `references/seven-sweeps.md` gewandert (161 Zeilen); der Einstieg ist jetzt
   95 Zeilen und sagt in drei Sätzen, was die Pässe sind und wann sie laufen.
3. **Eine Datei, die log:** `evals-de.json` enthielt nie JSON, sondern Markdown
   mit Tabellen. Sie heißt jetzt `evals.md`. Eine Endung, die über den Inhalt
   lügt, ist dieselbe Klasse wie ein Report-Schritt ohne Erzeuger (#806) –
   deshalb steht der Befund im Register, nicht nur im Changelog.

K10 wurde dabei nicht abgeschafft, sondern **umgedreht**: statt „eigene Datei
im Fremd-Ordner gefunden" prüft sie jetzt drei Zustände aus
`data/skill_ergaenzungen.json` – **angekommen** (still), **zurückgefallen**
(Warnung), **verloren** (Befund). Der geschlossene Fall bleibt als Wächter
stehen: Wer die Datei wieder in den Fremd-Ordner legt, hört es sofort.

## Nachweis (alles in diesem Lauf ausgeführt)

```
python3 scripts/skills_vertrag.py               → 64 Skills, 0 Befunde, 0 Warnungen
python3 scripts/skills_vertrag.py --selftest    → OK, 21 Fälle (vorher 19)
python3 scripts/skills_portfolio.py             → 29 mit Thema, 31 ausgeschlossen, 0/0
python3 scripts/skills_portfolio.py --selftest  → OK, 15 Fälle
npm run test:skills                             → OK, 37 Tests (1 skipped)
npm run trigger:check                           → 98 Workflows, 0 Befunde
python3 scripts/skript_syntax_wache.py          → 624 Dateien grün
python3 scripts/governance_contract.py --quick  → 43 Regeln erfüllt
python3 scripts/integrity_guard.py --gate       → Exit 0
```

Verdrahtung: `skills_portfolio.py` steht in `GUARDS` (C6) und im Gate-Schritt
von `link-check.yml`; `npm run skills:portfolio` ist der Hausbefehl. Die vier
Schutzdateien sind unter `FEST` und gezeichnet.

## Grenzen, die dazugehören

1. **Das Portfolio ist eine Entscheidung, kein Naturgesetz.** Es sagt, was der
   Blog heute bedient – nicht, was er bedienen sollte. Wer eine siebte
   Themenwelt aufmacht, muss sie hier eintragen; das ist Absicht.
2. **Die Fristen sind Arbeit.** 31 Ausschlüsse laufen am 2027-03-31 ab. P5
   warnt dann, blockiert nicht – entschieden wird trotzdem von einem Menschen.
3. **Trefferqualität bleibt ungemessen.** 64 Skills mit teils überlappenden
   Beschreibungen (`copywriting` / `copy-editing` / `ff-lektorat`) können falsch
   auslösen. Das Portfolio ordnet Zweck und Kosten, nicht Trefferquote; dafür
   wäre die `skill-creator`-Auswertung der nächste Schritt.
4. **`redaktions_standard.py` ist mitgeheilt.** Der Drift stammte aus `main`
   (`359e51d`), nicht aus dieser Arbeit – die Signatur steht mit Herkunft in der
   Akte, damit sie nicht als Nebenwirkung dieses PR gelesen wird.
