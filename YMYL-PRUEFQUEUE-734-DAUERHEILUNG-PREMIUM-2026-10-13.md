# Redaktionelle YMYL-Prüfqueue #734 – Dauerheilung auf Agentur-Niveau

**Stand:** 13.10.2026 · **Basis:** `main` @ `a20e526` (Analyse auf `ebbf39c`) · **Branch:** `arena/e6030eb1-franksfinanzcheck-blog`
**Queue nach Behebung:** 88 Artikel · 9 Hochrisiko · 9 freigegeben · **0 blockiert**

## 0. Kurzfassung

- **Befund:** Die Prüfqueue meldete einen einzigen offenen Fall: den KI-Entwurf
  „Versicherung-Update: Was sich jetzt für dich ändert“ vom 13.10.2026, Risiko
  hoch, **E03** (Hochrisiko-Thema ganz ohne `redaktionelle_pruefung`).
- **Redaktionsentscheidung:** **verworfen.** Der Text hat keinen Nachrichtenanlass,
  ist die Titel-Dublette eines Entwurfs vom 17.09., behauptet für Versicherungen
  einen Ranking-Mechanismus, den das Bundeskartellamt so nur für Hotelportale
  beschreibt, ignoriert geltendes Recht und enthält keine einzige Quelle. Eine
  freigabefähige Fassung wäre ein neuer Artikel (Abschnitt 3). Das Thema selbst
  ist gut – dafür liegt ein Brief für die Fachfreigabe-Bahn bei (Abschnitt 7).
- **Ursache:** Nicht das Gate, sondern die Produktion. Die Content-Engine hält
  sich seit #521 an zwei Bahnen (AUTO vs. FACHFREIGABE). Die drei Writer, die
  über `ki_shared` schreiben (KI-Redaktion Claude/News, Poppy-Werkbank), kannten
  diesen Vertrag nicht. Sie konnten jederzeit YMYL-Entwürfe ohne Prüfgerüst
  erzeugen. Gemeldet wurden solche Entwürfe erst von der Queue.
- **Dauerheilung:** Der Fachfreigabe-Vertrag sitzt jetzt an **einer** Stelle
  (`ki_shared`). Geprüft wird vor jeder Generierung und noch einmal an der
  Schreibgrenze. Dazu kommen ein Dubletten-Schutz über Titel **oder** Slug, eine
  Promote-Sperre und eine Vertragsprobe im fail-closed-Selbsttest des Workflows.
  39 neue Offline-Tests sichern das ab. Eine Sabotageprobe bestätigt, dass Tests
  und Selbsttest anschlagen, sobald der Vertrag fehlt.
- **Bewusst nicht getan:** Kein Prüfer erfunden, nichts versiegelt, keine
  Freigabe gesetzt, keine Workflow-Datei geändert, keine Gate-Regel aufgeweicht.

## 1. Befund

| Artikel | Status | Risiko | Freigabe | Befund |
|---|---|---|---|---|
| `2026-10-13-versicherung-update-was-sich-jetzt-fuer-dich-aendert` | Entwurf | hoch | offen | E03 – Hochrisiko-Thema ohne `redaktionelle_pruefung` (Freigabe fehlt) |

Lokal reproduziert auf `ebbf39c`: `editorial_review_gate.py --all` →
„89 Artikel · 10 Hochrisiko · 9 freigegeben · **1 blockiert**“. Die neun übrigen
Hochrisiko-Artikel waren gültig versiegelt. `--published --strict` war grün: Live
war nie etwas Ungeprüftes. Das Publish-Gate hätte den Entwurf fail-closed
gehalten.

## 2. Wurzelursache

**Tathergang**, belegt über die Actions-API und die Commit-Historie:

1. Die KI-Redaktion lief am Dienstag, 13.10.2026, planmäßig
   (`schedule`, Run 38395750905, Start 12:13:44 UTC). Dienstag bedeutet
   Rolle „news“, also `news_writer.py` ohne Flags.
2. `ki_shared.pick_news_hook()` gab den **ersten** unverbrauchten Aufhänger
   zurück: `versicherung-vergleichsportale-nicht-vollstaendig` (Kategorie
   „versicherung“). Eine Bahn- oder Risikoprüfung gab es nicht.
3. Der Titel entstand statisch aus der Kategorie: „Versicherung-Update: Was sich
   jetzt für dich ändert“. Genau diesen Titel trägt der Entwurf vom 17.09., der
   in #586 geprüft und versiegelt wurde. Der News-Writer prüfte Titel überhaupt
   nicht gegen den Bestand.
4. `ki_shared.build_frontmatter()` schrieb weder eine Risikoklasse noch das
   Prüfgerüst. Das Ergebnis war ein Hochrisiko-Entwurf ohne `redaktionelle_pruefung`.
   Der Content-Bot committete ihn um 12:14:06 UTC (`a17308b`, „neuer KI-Entwurf
   (draft, Rolle news)“).
5. Alle Schritte des Laufs meldeten **success**, auch der „Selbsttest
   (fail-closed)“. Der Vertrag kam in keinem Prüfpunkt vor. Erst die
   werktägliche Prüfqueue fand den Entwurf (E03) und öffnete #734.

**Systemische Ursache:** Mit #521 wurde die Engine bahnfest
(`engine_capacity.nur_auto`, WIP-Limit `YMYL_WIP_LIMIT`). Die zweite
Produktionslinie blieb blind:

| Lücke | Wirkung |
|---|---|
| `news_writer` wählte Aufhänger ohne Risikoprüfung | YMYL-Entwürfe bei jedem Versicherungs- oder Kredit-Aufhänger |
| `pick_topic` (claude_writer) ohne Bahnfilter | 55 von 202 Pool-Themen sind YMYL-Hochrisiko (Stand 13.10.2026) |
| `poppy_repurpose` ohne Prüfung, dazu ein `except Exception`-Ersatz-Frontmatter | jede Versicherungs-/Kredit-Karte wäre automatisch zum E03-Entwurf geworden |
| kein Prüfgerüst in `build_frontmatter` | E03 („niemand wusste davon“) statt E05 („wartet auf Prüfung“) |
| WIP-Limit nur in der Engine wirksam | die Fachbahn konnte von außen beliebig überlaufen |
| Dubletten-Schutz nur über den exakten Titel | SEO-verlängerte Titel täuschen ihn (Entwürfe vom 23.09. und 09.10. = Dubletten bereits veröffentlichter Artikel); der News-Writer prüfte gar nicht |
| `--promote` ohne YMYL-Prüfung | ein unfreigegebener Hochrisiko-Entwurf hätte in der Re-Queue einen Slot belegt |

Das ist dieselbe Fehlerklasse wie #521: Die Maschine erzeugt Arbeit, die sie
selbst nie ausliefern darf. Diesmal geschah es an einer zweiten
Produktionslinie, und dieselbe Linie hatte schon am 17.09. den Schwesterentwurf
geliefert (#586).

## 3. Redaktionsentscheidung: verworfen

Geprüft wurde die eingecheckte Fassung (`git show ebbf39c:content/posts/2026-10-13-versicherung-update-was-sich-jetzt-fuer-dich-aendert/index.md`).

| # | Prüfpunkt | Entwurf | Befund |
|---|---|---|---|
| 1 | Anlass | „**Stand: 13.10.2026.** Dieser News-Kompakt-Artikel ordnet eine aktuelle Entwicklung ein.“ | Es gibt kein Ereignis. Der Aufhänger ist eine zeitlose Beobachtung. Eine „News“ ohne Nachricht verspricht dem Leser etwas, das der Text nicht hält. |
| 2 | Dublette | Titel identisch mit `2026-09-17-versicherung-update-…` | Kannibalisiert den in #586 geprüften Entwurf. Zwei Seiten mit demselben Titel sind kein Angebot, sondern ein Fehler. |
| 3 | Kernmechanismus | „Algorithmen bevorzugen oft die Partner mit den höchsten Provisionen.“ / „Deshalb zeigen sie häufig die Anbieter mit den höchsten Provisionen zuerst.“ | Unbelegt und in dieser Pauschalität falsch. Laut Bundeskartellamt ist die Provision als Ranking-Faktor „insbesondere im Hotelbereich üblich“. Bei Versicherungen ist der Kernbefund eine vergleichsweise **geringe Marktabdeckung**, und Verbraucher erfahren oft nicht, welche Anbieter fehlen [Q1]. Die Verbraucherzentrale schreibt, Portale „können“ höhere Provisionen bevorzugen, nicht „oft“ [Q6]. |
| 4 | Rechtsrahmen | „Bis klare Regeln gelten …“, „Zukünftig könnten gesetzliche Vorgaben die Vollständigkeit … erhöhen.“ | Irreführend, denn es gibt Regeln. Ein Makler muss seinem Rat eine hinreichende Zahl von Verträgen und Versicherern zugrunde legen oder ausdrücklich auf eine eingeschränkte Auswahl hinweisen und diese benennen (§ 60 VVG) [Q2]. Wer eine Suche über Angebote verschiedener Anbieter anbietet, muss die Hauptparameter des Rankings offenlegen (§ 5b Abs. 2 UWG) [Q3]. Bezahltes Ranking ohne Offenlegung ist stets unzulässig (UWG Anhang Nr. 11a) [Q4]. Ein Portal muss offenlegen, wenn es nur zahlende Anbieter listet (BGH, 27.04.2017, I ZR 55/16) [Q5]. |
| 5 | Erfundenes | FAQ „Was kostet ein Versicherungswechsel? … Wechselgebühr“; „mehrere hundert Euro zu viel“; „Viele Unternehmen zahlen für bessere Platzierung in Suchmaschinen“ | Für eine „Wechselgebühr“ fehlt jeder Beleg. Der Betrag hat keine Grundlage. Suchmaschinenwerbung ist ein anderes Thema als das Portal-Ranking. |
| 6 | Interessenkonflikt | Erst „Portale zeigen die Anbieter mit den höchsten Provisionen zuerst“, dann der Schluss-CTA „Jetzt Fixkosten auf CHECK24 prüfen“ | Der Text widerspricht sich selbst und der eigenen Methodik: Partner sind nie Belegquelle, Redaktion und Provision sind getrennt (`content/methodik/index.md`). |
| 7 | Belege | kein `quellen`-Block | YMYL verlangt mindestens zwei erlaubte Quellen, davon mindestens eine aus Rang 1 oder 2 (E12). Hier gibt es keine einzige. |
| 8 | Form | Fast jede Zeile endet mit zwei Leerzeichen, also einem harten Umbruch; auf das Etikett „Faustregeln:“ folgt keine einzige Regel | Der Text rendert als Wand aus Einzelsätzen und erfüllt nicht den Redaktionsstandard des Hauses. |

**Urteil:** Eine Prüfung kann diesen Text nicht heilen. Jede freigabefähige
Fassung müsste Anlass, Titel, Kernthese, Rechtsrahmen, Belege und CTA ersetzen,
also ein neuer Artikel sein. Deshalb wird der Entwurf verworfen und der Ordner per
`git rm -r` entfernt. Die Fassung bleibt in der Git-Historie (`ebbf39c`, `a17308b`).
Der Aufhänger bleibt als verbraucht markiert. Das Thema gehört als Ratgeber in die
Fachfreigabe-Bahn, nicht als News in die Automatik (Brief: Abschnitt 7).

Der Schwesterentwurf vom 17.09. bleibt unberührt: versiegelt, Entwurf, nächster
Review am 19.11.2026.

### Belegkette (abgerufen am 13.10.2026)

- [Q1] Bundeskartellamt, Sektoruntersuchung Vergleichsportale, Abschlussbericht
  April 2019 – [Pressemitteilung](https://www.bundeskartellamt.de/SharedDocs/Meldung/DE/Pressemitteilungen/2019/11_04_2019_Vergleichsportale_Bericht.html),
  [Bericht (PDF)](https://www.bundeskartellamt.de/SharedDocs/Publikation/DE/Sektoruntersuchungen/Sektoruntersuchung_Vergleichsportale_Bericht.pdf?__blob=publicationFile&v=7).
  Belegt: vergleichsweise geringe Marktabdeckung u. a. bei Versicherungen.
  Ursachen sind Anbieter, die Portale meiden, und Portale, die nichtzahlende
  Anbieter ausschließen. Fehlende Anbieter werden oft nicht genannt. Die Provision
  als Ranking-Faktor ist „insbesondere im Hotelbereich üblich“. Die „Position 0“
  beruht bei Versicherungen überwiegend auf einer qualitativen Bewertung des Portals.
- [Q2] § 60 VVG – [gesetze-im-internet.de/vvg_2008/__60.html](https://www.gesetze-im-internet.de/vvg_2008/__60.html)
- [Q3] § 5b Abs. 2 UWG – [gesetze-im-internet.de/uwg_2004/__5b.html](https://www.gesetze-im-internet.de/uwg_2004/__5b.html)
- [Q4] UWG, Anhang (zu § 3 Abs. 3) Nr. 11a – [gesetze-im-internet.de/uwg_2004/anhang.html](https://www.gesetze-im-internet.de/uwg_2004/anhang.html)
- [Q5] BGH, Urteil vom 27.04.2017 – I ZR 55/16 („Bestattungspreisvergleich“)
- [Q6] Verbraucherzentrale, „Vergleichsportale richtig nutzen“ –
  [verbraucherzentrale.de/…-39545](https://www.verbraucherzentrale.de/wissen/digitale-welt/onlinehandel/vergleichsportale-richtig-nutzen-so-finden-sie-das-beste-angebot-39545)

## 4. Dauerheilung

### 4.1 Ein Vertrag an einer Stelle (`scripts/ki_shared.py`)

| Baustein | Aufgabe |
|---|---|
| `bahn_fuer()` / `risikoklasse()` | gibt wörtlich `engine_capacity.bahn_fuer_thema` bzw. `risikoklasse_fuer_thema` zurück, also `editorial_review_gate.classify_text` auf demselben Material, das das Gate am fertigen Artikel liest (Titel + erste zwei Keywords + Pillar). Keine kopierten Muster (Test-Pin). Ein Defekt heißt **fail-closed**. |
| `fachfreigabe_pruefen()` | AUTO ist frei. FACHFREIGABE braucht `--fachfreigabe` **und** eine offene Bahn (`engine_capacity.fachfreigabe_bahn`, WIP-Limit). Sonst gibt es `FachfreigabeErforderlich` mit einer Begründung im Klartext. |
| `build_frontmatter(..., fachfreigabe=)` | prüft an der letzten Schreibgrenze ein zweites Mal (Defense in Depth), **vor** der Tag-Kanonisierung. Jeder Entwurf trägt wie bei der Engine das Gerüst `redaktionelle_pruefung` (`pruefgeruest()`, status „ausstehend“, nie Prüfer, nie „freigegeben“). |
| `pick_topic(fachfreigabe=False)` | ohne Beauftragung nur AUTO-Themen, mit demselben Filter wie die Tagesquote der Engine (`engine_capacity.nur_auto`) |
| `news_hook_kandidaten()` | ersetzt `pick_news_hook`: Es gibt eine Liste statt „des nächsten“, und erst der Writer entscheidet, was er schreiben darf. Ein Test verbietet die Rückkehr der Einzelwahl. |
| `titel_vergeben()` | erkennt Dubletten über Titel **oder** normalisierten Slug (`reserve_topics._bestands_slugs`, ohne zweite Normalisierungsregel), sodass SEO-verlängerte Titel nicht mehr täuschen |
| `YMYL_ARBEITSAUFTRAG` | Leitplanken für beauftragte YMYL-Läufe wie im Hochrisiko-Block der Engine: keine simulierte Fachprüfung, keine unbelegten Zahlen oder Paragraphen, kein Kaufaufruf im Fachtext |

### 4.2 Die Writer

| Writer | Vorher | Nachher |
|---|---|---|
| `news_writer.py` | erster Aufhänger, statischer Titel, keine Prüfung | `waehle_aufhaenger()` prüft je Aufhänger zuerst Dublette, dann Bahn. Übersprungenes bleibt **unverbraucht** im Pool, der nächste erlaubte Aufhänger rückt nach. Eigener Titel über das neue Pool-Feld `titel:`. Neues Flag `--fachfreigabe`. |
| `claude_writer.py` | Pool ohne Filter, `--topic` ohne Prüfung | Der Pool liefert nur AUTO. Ein YMYL-`--topic` braucht `--fachfreigabe`. Geprüft wird **vor** dem Modellaufruf (kein verbranntes Gratis-Kontingent). |
| `poppy_repurpose.py` | jede Karte wurde ausgeschrieben; `except Exception` hätte jeden Fehler ins Ersatz-Frontmatter gelenkt | Frühprüfung vor der Generierung. `FachfreigabeErforderlich` wird nie geschluckt, und auch das Ersatz-Frontmatter trägt das Prüfgerüst. Eine YMYL-Karte bleibt „neu“, bis sie beauftragt wird (`--fachfreigabe`). |
| `ki_redaktion.py --promote` | legte jeden fertigen KI-Entwurf in die Re-Queue | verweigert Hochrisiko ohne gültige Freigabe und nennt die Codes und den Ablauf bis `--seal`. Gemessen wird mit `editorial_review_gate.evaluate_path`, also ohne zweite Regel (C19). Ein unlesbarer Entwurf führt fail-closed zur Ablehnung. |
| `ki_redaktion.py --selftest` | kannte den Vertrag nicht | prüft ihn funktional, offline und uhrfest: Vorfall-Material = FACHFREIGABE, ohne Auftrag keine Frontmatter, mit Auftrag das Gerüst hoch/ausstehend, volle Bahn heißt Sperre. Läuft im Workflow vor jeder Produktion mit Exit 2. |

### 4.3 Verhalten vorher → nachher

| Fall | Vorher | Nachher |
|---|---|---|
| Automatik trifft einen YMYL-Aufhänger | E03-Entwurf, Aufhänger verbraucht, Issue | übersprungen mit Begründung, bleibt im Pool, ein AUTO-Aufhänger rückt nach |
| Kategorie-Titel schon vergeben | Dublette | übersprungen, Hinweis auf das Pool-Feld `titel:` |
| Mensch beauftragt YMYL, Bahn offen | – | Entwurf mit Gerüst, in der Queue als **E05** (wartet auf Prüfung) statt E03 |
| Mensch beauftragt YMYL, Bahn voll | – | verweigert mit dem WIP-Grund |
| `--promote` auf Hochrisiko ohne Freigabe | Re-Queue (Publish-Gate hält fest) | verweigert, nennt den Ablauf bis `--seal` |
| Einstufung defekt | – | kein Entwurf (fail-closed) |

Asymmetrisch konservativ wie bei der Engine: Die Bahn ersetzt nie das Gate.
Wird ein als AUTO eingestufter Text doch YMYL, hält ihn weiterhin das
fail-closed `editorial_review_gate`.

## 5. Nachweis (lokal, ohne Netz und ohne API-Keys)

- **Neue Tests:** `scripts/tests/test_ki_redaktion_fachfreigabe.py`, 39 Tests
  (SSOT, Schreibgrenze, News-Auswahl, Dubletten-Identität, Läufe in Temp-Ordnern,
  Claude-Writer, Poppy inkl. Ersatz-Frontmatter, Promote-Sperre, Selbsttest).
  Uhrfest: Bestand und WIP-Lage werden festgenagelt, keine Schreibzugriffe auf
  `data/audit/`.
- **Sabotageprobe:** Ohne die Auftragsprüfung in `fachfreigabe_pruefen` scheitern
  8 der neuen Tests, und `ki_redaktion.py --selftest` endet mit
  „FEHLER ❌“ (Exit 2). Der Workflow-Lauf würde also vor der Produktion stoppen.
- **Gesamte Suite** (integrierter Stand): `python3 -m unittest discover -s scripts/tests`
  → 3013 Tests, davon 39 neu und alle grün, 11 übersprungen, **1 Fehlschlag**. Das ist
  der vorbestehende Reserve-Snapshot-Befund (Abschnitt 6). Er tritt auf `main` @ `a20e526`
  identisch auf (`reserve_artifacts.snapshot_findings`). Vor dem Rebase lief unverändertes
  `main` @ `ebbf39c` mit 2971 Tests und demselben einen Fehlschlag.
- **Uhr-Probe** (integrierter Stand): `selftest_clock.py --trap-discover scripts/tests --offset 97`
  → 3013 Tests, derselbe eine vorbestehende Fehlschlag, sonst grün. Die neuen Tests hängen
  nicht vom Datum ab.
- **Redaktions-Gate:** `--selftest` ✅ · `--all --strict --report` → 88 Artikel ·
  9 Hochrisiko · 9 freigegeben · 0 blockiert (Exit 0) · `--published --strict` → 56 Artikel · 0 Hochrisiko · 0 blockiert (Exit 0).
  Gemessen auf dem mit `main` @ `a20e526` integrierten Stand.
- **Selbsttests:** `ki_redaktion.py`, `poppy_repurpose.py`, `engine_capacity.py` ✅
- `automation_premium_audit.py --strict` → Exit 0 · `git diff --check` → sauber

## 6. Grenzen und offene Punkte

- **Keine Fachprüfung behauptet.** Dieser Auftrag hat weder geprüft noch
  versiegelt noch freigegeben. Die Belegkette in Abschnitt 3 begründet die
  Ablehnung, sie ist keine Freigabe.
- **Release-Scorecard:** `RELEASE-SCORECARD.md` führt den verworfenen Entwurf
  noch in der Frischetabelle. Die Datei wird vom Scorecard-Lauf (Deploy bzw.
  `release-scorecard.yml`) neu erzeugt und hier bewusst nicht von Hand bearbeitet.
- **Workflows unverändert.** Findet der News-Writer keinen erlaubten Aufhänger,
  endet er wie bisher bei leerem Pool mit Exit 1, und der Workflow meldet
  `::warning::`. Das Log nennt jetzt den Grund je Aufhänger.
- **Pool-Pflege:** Unverbraucht ist nur noch `saisonal-fruehjahrsputz-vertraege`
  (AUTO). Danach braucht die News-Rolle neue kuratierte Aufhänger, am besten mit
  eigenem `titel:`.
- **Vorbestehender, fremder Befund:** `test_reserve_artifacts …
  test_current_snapshot_is_whole_and_editorially_valid` schlägt schon auf `main`
  fehl (SHA-256 des Reserve-Snapshots für
  `2026-10-12-dein-weg-zu-geringeren-monatskosten-schritt-fuer-schritt`). Das hat
  mit #734 nichts zu tun und gehört zur Reserve-Zertifizierung.
  Derselbe Befund färbt seit dem Nachmittag des 13.10. die PR-Prüfung jeder
  offenen Änderung rot (Schritte „Reserve-Snapshot“, „Code-Regression“, „Uhr-Probe“).

## 7. Brief für die Fachfreigabe-Bahn

**Arbeitstitel:** „Vergleichsportale für Versicherungen: Was sie nicht zeigen“
(57 Zeichen) · **Pillar:** versicherungen · **Bahn:** FACHFREIGABE ·
**Format:** Evergreen-Ratgeber, keine News.

**Suchintention:** „Sind Vergleichsportale bei Versicherungen vollständig und
neutral – und wie nutze ich sie richtig?“

**Tragende Aussagen (belegt, siehe Abschnitt 3):**

1. Portale bilden bei Versicherungen oft nicht den ganzen Markt ab. Es fehlen
   Anbieter, die Portale meiden oder nicht zahlen, und Direktversicherer [Q1, Q6].
2. Arbeitet ein Portal als Makler, gilt § 60 VVG: Es braucht eine hinreichende
   Marktbasis, oder es muss die eingeschränkte Auswahl offenlegen und benennen [Q2].
3. Ranking-Kriterien sind offenzulegen (§ 5b Abs. 2 UWG). Bezahlte Platzierung
   ohne Kennzeichnung ist unzulässig (Anhang Nr. 11a) [Q3, Q4]. Ein Portal, das nur
   zahlende Anbieter listet, muss das sagen (BGH I ZR 55/16) [Q5].
4. Praxis: Anbieterliste bzw. Marktabdeckung des Portals lesen, Direktversicherer
   gesondert prüfen, Leistungen vor Preis vergleichen, mehrere Wege nutzen [Q6].

**Vor dem Schreiben zu klären (unbelegt, nicht verwenden ohne Primärquelle):**

- Wie weit § 5b Abs. 2 UWG bei Finanz- und Versicherungsvergleichen reicht
  (Hinweis aus Verbraucherschutzkreisen auf Ausnahmen, ungeprüft).
- Konkrete Abdeckungsquoten je Sparte. Sekundärquellen nennen Spannen. Vor jeder
  Zahl ist Kapitel E.5.4.4 des Kartellamtsberichts im Original zu prüfen.
- Erlaubnisstatus und Pflichtangaben von Portalen (Gewerbe- und
  Vermittlerregister) mit Primärquelle.

**Gate-Voraussetzungen:**

- Mindestens zwei erlaubte Quellen, davon mindestens eine aus Rang 1 oder 2
  (`gesetze-im-internet.de` Rang 1, `verbraucherzentrale.de` Rang 2).
  **`bundeskartellamt.de` steht nicht in `TRUSTED_SOURCE_RANK`.** Ob die Behörde
  (sinnvoll: Rang 1) aufgenommen wird, ist eine Redaktionsentscheidung im Gate.
  Bis dahin kann sie nicht als Belegquelle zählen.
- Partner (CHECK24, Tarifcheck) sind nie Beleg. Die eigene Partnerbeziehung wird
  offen benannt (Methodik). Ein CTA kommt erst nach mindestens 600 Wörtern und
  zwei H2 (E15).
- Ein benannter Prüfer, Aussagen- und Zahlenanker, Review-Termin, dann `--seal`.

**Beauftragung**, sobald die Bahn offen ist:

```bash
python3 scripts/claude_writer.py \
  --topic "Vergleichsportale für Versicherungen: Was sie nicht zeigen" \
  --pillar versicherungen --fachfreigabe
```

Der Writer kennt diesen Brief nicht. Sein Entwurf ist Rohmaterial mit Prüfgerüst.
Die tragenden Aussagen, die Belegkette und das Zahlenprotokoll setzt die Prüfung
ein, bevor irgendetwas versiegelt wird.
