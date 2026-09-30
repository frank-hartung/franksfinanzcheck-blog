# Lesbarkeit & Politur-Ruinen Premium 30.09.2026 — Issue #482

**Auftrag:** „Premium-Runde Lesbarkeit: sechs Entwürfe über die
Publish-Schwelle (#482) – bitte dauerhaft auf Premium-Level einer
Profi-Agentur beheben.“

PR #482 (Branch `arena/01a0f334`) trug die redaktionelle Arbeit, war aber
nach den Merges von #483 (Notgroschen-Dublette) und #484 (A11y-Kalender)
**konfliktbehaftet** und nicht mehr mergbar. Dieser Nachbau führt die
Arbeit auf aktuellem main konfliktfrei zusammen, heilt die dabei
sichtbar gewordenen Folgeschäden und verschließt die Ursachenklasse
dauerhaft.

| | |
|---|---|
| **Übernommen aus #482** | 6 redigierte Artikel (5 Entwürfe + Mietwagen-Live-Artikel), Doppel-Intro entfernt, alle vier Textdefekte geheilt |
| **Konfliktauflösung** | Notgroschen-Entwurf 30.09. auf main gelöscht (#483) → dessen Politur entfällt ersatzlos; 28.09.-Fassung ist live und über der Floor |
| **Neu geheilt (diese Runde)** | 1 Zwillings-Defekt („1 Januar“, Neujahrs-Entwurf) · 3 R5-hart-Absätze in den polierten Entwürfen · 6 R5-hart/R10-Bestandsbefunde · 3 Doppel-Passagen (R15-Klasse) · 1 Casing-Doppelfund |
| **Durably verschlossen** | **R11–R15** in `textverstaendnis_guard.py` + Muster-SSOT `sprachkern.POLITUR_RUINEN` + `write_verified`-Schreibsperre + Publish-Gate-Blocker |
| **Verifikation** | Selbsttest R2–R15 grün (14 neue Sabotage-Fälle) · Audit: **hart 0** über 61 Artikel · Publish-Gate-End-to-End-Sabotageprobe blockt R11–R15 einzeln · Bestands-Gate Ø Flesch 64,0, kein Entwurf unter Schwelle 60 · Struktur-Guard 0 Regressionen · Tabellen 0 · 937 Unit-Tests (alle neuen grün, Vorbefunde unverändert) |

---

## 1. Die sechs Entwürfe über die Publish-Schwelle (Übernahme aus #482)

Regelwerk R6 (Flesch ≥ 60, 11–14 Wörter/Satz, Aktiv statt Nominalstil,
keine Kanzleiwörter, max. 4 Sätze/Absatz). Die Politur aus #482 wurde
Datei für Datei identisch übernommen (byte-identisch zum PR-Zweig
verifiziert); der siebte Entwurf — Notgroschen 30.09. — ist auf main
bereits durch #483 **gelöscht** (Qualitätsentscheidung dort: Die
28.09.-Fassung ist in jeder Disziplin besser und jetzt live).

| Entwurf | vorher (main) | nachher | Score |
|---|---|---|---|
| `konto-karten-update` (29.09.) | 48,2 | **62,9** | 95 |
| `e-auto-ladekosten` (30.09.) | 50,4 | **70,9** | 95 |
| `oekostrom-anbieter-wechseln` (30.09.) | 50,4 | **67,1** | 95 |
| `weihnachten-budget-planen` (30.09.) | 56,9 | **69,8** | 95 |
| `e-bike-fahrradversicherung` (30.09.) | 57,1 | **70,2** | 95 |
| Mietwagen `september-roadtrip` (live) | 49,1* | **64,6** | 95 |

\* Flesch vor der Entzerrung aus #481; das Doppel-Intro entfernte #482.

**Damit liegt kein Entwurf mehr unter der Publish-Schwelle** (AMBER-Liste
des Bestands-Gates leer). Ø Flesch über alle 61 Artikel: 63,5 → **64,8**.

Die vier mitgereparierten Textdefekte aus dem Retrofit sind mit übernommen
und im Bestand nicht mehr auffindbar (Sonde, Abschnitt 3):
„Du bist der 0 am deutschen Strommarkt“ · „es ist der 2 Januar“ ·
„Nutze 20 26 gezielt Mindestbestellwerte“ ·
„SATZ: | **CHECK24-Vergleich** | – | | | | |“ (T1-Tabellenfund weg) ·
Doppel-Intro im Mietwagen-Artikel.

## 2. Was die neue Wache beim Aufbau gleich gefunden hat

Die Politur aus #482 verdichtete drei Absätze auf **7 Sätze** (R5-hart
blockiert das Publish-Gate — die Entwürfe wären über der Lesbarkeits-,
aber unter der Absatz-Schwelle hängen geblieben). Gesplittet:
`konto-karten` (Mechanismus-Absatz), `e-bike` (Teildiebstahl),
`oekostrom` (Kündigungsfrist/März-2022-Regeln).

Dazu **ein Zwillings-Defekt**, den #482 übersehen hatte — gefunden von
der neuen Regel R13 bei ihrer ersten Korpusfahrt:

> `neujahrsvorsaetze-geld` (30.09., Entwurf):
> „Jedes Jahr am **1 Januar** ist die Motivation riesig.“ → **1. Januar**

Und **sechs vorbestehende harte Bestandsbefunde**, alle aus derselben
Ursachenfamilie (automatisierte Politur-Runden), alle in dieser Runde
geheilt:

| Artikel (live) | Befund | Heilung |
|---|---|---|
| `energiediebe-stoppen` | 2 × R5-hart (18- und 16-Satz-Absatz) | in 4er-Blöcke gesplittet |
| `heizungs-check-im-spaetsommer` | R5-hart (19-Satz-Absatz) | in 4er-Blöcke gesplittet |
| `gasrechnung-so-bereitest` | R5-hart (7-Satz-Absatz) | gesplittet |
| `gasrechnung-fehler-im-spaetsommer` | R10-Dopplung „senken um bis zu 15 % senken“ (der eingefrorene Fall aus dem Klebe-Audit 28.09. — zurückgekehrt) | „senkst du … um bis zu 15 %“ |
| `gasrechnung-spaetsommer-check` | angehängte Doppel-Sätze („Wir lesen den Zähler ab …“ 2×) | Dublette entfernt |
| `mehr-freiheit-durch-verzicht` | **Doppel-Intro-Block** („Bedeutet Sparen für dich grauen Alltag? …“ 2×, von SEO-Healer-Runden angereichert) | Dublette entfernt — derselbe Schaden wie beim Mietwagen-Artikel |
| `finanzieller-puffer` | Fazit wiederholt Intro-Sätze wortgleich (10-Wort-Sequenz) | Fazit eigenständig formuliert |

**Ergebnis: Verständnis-Audit hart 0** — der gesamte Bestand ist erstmals
frei von harten R2–R15-Befunden (main: 9). Die 115 weichen Funde
(R4-Satzanfänge, R5-4-Sätze, R8-Anker-Kohärenz) sind bewusst
Review-Kandidaten und unverändert.

## 3. Dauerhaft: die Politur-Ruinen-Wache R11–R15

**Root Cause:** Alle vier Textdefekte aus #482 stammen aus
automatisierten Politur-Läufen (Sprachglatt/Grammatik/SEO-Heiler). Die
Schreib-Verifikation `sprachkern.write_verified` prüft nur Struktur
(Link-/Shortcode-/Überschriften-Zahl, Wortzahl ≥ 90 %) — nie den
Ergebnis-Text. Eine Ersetzung, die „2026“ in „20 26“ zerreißt, geht
durch jede Verifikation. Und das Doppel-Intro (Kapitel-Zusammenführung)
fand weder duplikat_guard D1/D2 (Ratio < 0,85, < 120 Zeichen) noch
irgendeine andere Wache.

**Zwei Einsatzstellen, eine Muster-SSOT:**

1. **`sprachkern.POLITUR_RUINEN`** (R11–R14) — deterministische Muster,
   am gesamten Content gegen False-Positive geprüft (0 Treffer auf
   61 Artikel + alle Seiten). `write_verified` **verweigert jede
   Schrift, die eine NEUE Ruine einführt** (Bestehende blockieren die
   Heilung nicht — keine Einfrierung). Damit kann keine Politur-Engine
   diese Klasse jemals wieder schreiben; erbt auch
   `zeit_rechtschreibung.py` automatisch.
2. **`textverstaendnis_guard.py` R11–R15** — meldet die Ruinen im
   täglichen Audit (`blog-health-daily.yml`) und blockiert die
   Veröffentlichung über `publish_gate.textverstaendnis_failures()`
   (hart). R15 (Phrasen-Dopplung ≥ 10 identische Wörter im Fließtext)
   lebt in der Wache, weil sie den Fließtext-Parser braucht.

| Regel | fingert (echte Fälle) | Grenzwert-Beweis |
|---|---|---|
| **R11-JAHRESZAHL-SPLIT** | „Nutze 20 26 gezielt …“ | Tausender-Gruppen sind Dreier-Blöcke („40 000“) — Zweier-Zweier mit 19/20-Anfang ist immer falsch |
| **R12-ZAHL-RUINE** | „Du bist der 0 am deutschen Strommarkt“ | Artikel + nackte Zahl (≤ 2-stellig) + Präposition ist nie korrektes Deutsch |
| **R13-DATUM-PUNKT** | „es ist der 2 Januar“ / „am 1 Januar“ | Zahl vor Monatsname trägt immer Ordinalpunkt; Lookbehind schließt „20. November“ aus |
| **R14-MARKER-RUINE** | „SATZ: \| **CHECK24-Vergleich** \| – \| \| \| \| \|“ | Debug-/Platzhalter-Marker am Zeilenanfang sind nie Inhalt (belt-and-braces zu table_guard T1) |
| **R15-PHRASEN-DOPPEL** | Mietwagen- & mehr-freiheit-Doppel-Intro (je 13-Wort-Sequenz identisch) | ≥ 10 Wörter: darunter legitime Titel-Echos und Kurzformeln („50 € bis 200 € mehr Spielraum im Monat“ = 9), darüber immer Redaktionsfehler; nur Fließtext — Überschriften/Listen/Tabellen/CTA-Boxen und fett geführte Transparenz-Zeilen bleiben außen vor; Rechtsseiten (Impressum-Adresse) bewusst ausgenommen |

**Sabotage-Schutz:** 14 neue eingefrorene Fälle im Selbsttest (alle vier
echten Schadensfälle + Zwillingsfund + Negativproben: „40 000 €“,
„seit 1998“, „1 100 € im Jahr“, „Der 3. Oktober“, korrekte Quantor-Stellung,
9-Wort-Titel-Echo, „Der Satz: kurze Hauptsätze“, „Tipp: Prüfe …“).
Publish-Gate-End-to-End-Sabotageprobe: ein Test-Entwurf mit je einem
Defekt pro Regel wird **einzeln in allen fünf Regeln geblockt**.

**Publish-Gate zusätzlich gehärtet:** R8-NESTED-LINK, R9-KLEBEWORT und
R10-DOPPELWORT blockieren jetzt ebenfalls die Veröffentlichung (die
Maschinen-Ruinen-Familie war bislang nur im Tages-Audit hart, nicht im
Publish-Pfad — die Mietwagen-Defekte sind genau so live gegangen).

## 4. Grün

- `textverstaendnis_guard --selftest`: R2–R15 grün · Audit: **hart 0**, 61 Artikel + 18 Seiten
- `readability_check --gate-bestand`: 45 Live-Artikel Ø 64,0, kein Live-Artikel unter Floor 55, **kein Entwurf unter Publish-Schwelle 60**
- `struktur_guard`: 61 Artikel · 0 Regressionen · Sperrklinke unangetastet
- `table_guard`: 0 Funde (E-Bike-T1 behoben) · `duplikat_guard`: D1–D3, D5, D6 = 0
- `zeit_rechtschreibung --selftest` (ST1–ST10), `grammar_check --selftest`, `sprachglatt --selftest`: grün (write_verified-Vertrag inklusive)
- `governance_contract --quick`: erfüllt (18 Regeln)
- Unit-Tests: 937 (3 neue zu `write_verified`: Ruinen-Sperre, Heilungs-Freiheit, Vier-Regeln-Sonde); Vorbefunde des Hauptstands unverändert (Worktree-Vergleich gegen main, gleiche 2+15)
- Casing-Guard: `energiediebe` sauber (C7/C10-Doppelfund „KWh“ am Satzanfang durch Umformulierung geheilt); 2 vorbestehende C7-Befunde in nicht berührten Artikeln bleiben der bestehenden Automatik überlassen

## 5. Offen (bewusst)

- Die 115 weichen Verständnis-Funde (R4/R5-weich/R8-Anker) sind
  Review-Kandidaten mit `owner=human` — keine Blocker, keine Ausweitung
  in dieser Runde.
- Hugo-Build + E2E laufen in CI (`link-check.yml` installiert Hugo
  0.164.0 extended; im Sandbox ist der Release-Download blockiert).
  Die Änderungen sind reine Fließtext-Edits: keine Frontmutter-, Link-,
  Shortcode- oder Layout-Änderungen.
- PR #482 wird von diesem Nachbau ersetzt und geschlossen (Branch der
  alten Session, Konflikt mit #483/#484, nicht aktualisierbar).
