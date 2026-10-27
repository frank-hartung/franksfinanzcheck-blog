# Optimierungsplan aus der Search Console

**Site:** `franksfinanzcheck.de` (Property `sc-domain:franksfinanzcheck.de`)
**Stand:** 27.10.2026
**Auftrag:** Bewertung des Blogs für die Google Search Console und umsetzbare
Optimierungstipps – ohne bezahltes Tool.
**Datenquellen:** Search-Console-API (nur lesen) für 20.09.–24.10.2026
(`data/gsc/tagesdaten.jsonl`, `top_seiten_28t.json`, `top_suchbegriffe_28t.json`);
Abdeckungs-Export vom 19.10.2026 (`data/gsc/abdeckung/export/2026-10-19/`);
Gegenprobe gegen den Repo-Bestand (`data/gsc/abdeckung/befund.json`, erzeugt
27.10.2026 10:31 UTC); `content/` mit 129 Seiten-Bundles (99 live, 30 Entwurf).

Dieser Plan ist ein **Maßnahmenplan**, kein zweiter Abdeckungsbericht. Die
Zahlenwahrheit der Indexierung steht in `GSC-ABDECKUNG-HIGHEND-2026-10-26.md`;
hier steht, in welcher Reihenfolge was zu tun ist und was es bringt.

---

## 0 · Das Urteil in fünf Sätzen

1. **Die Technik ist nicht das Problem.** Das Gate steht grün, es gibt keinen
   harten Fund. Von den beiden Hinweisen ist einer am 27.10.2026 geschlossen
   worden (die 4 toten Linkziele, Abschnitt 5); offen bleibt nur W5, die 18
   Index-Altlasten. `robots.txt`, `noindex`-Vertrag, 115 Weiterleitungen und
   die Sitemap sind dokumentiert und geprüft.
2. **Das Problem ist die Indexquote: 117 von 437 bekannten URLs (26,8 %).**
   Auf jede indexierbare Seite (99) kommen 3,2 Einträge, die nicht in den
   Index sollen. Diese 320 Posten sind zu 93 % Altlasten, nicht Content.
3. **Der größte Einzelposten ist selbst gemacht und aufschreibbar:** Aus dem
   Bestand lassen sich **136 Alt-URLs** ableiten (68 × `(1)`-Dublette, 68 ×
   URL ohne Datumspräfix). Das Muster ist belegt – 59 der 115 bereits
   dokumentierten Weiterleitungen sind genau solche datumslosen URLs.
4. **Der Sichtbarkeits-Hebel ist nicht die CTR, sondern die Menge.** 128
   Impressionen in 28 Tagen auf 25 Seiten, 49 Impressionen auf 19 Suchbegriffe,
   0 Klicks. Bei durchschnittlich Position ~20 sind ~1–2 Klicks statistisch zu
   erwarten – die Null ist kein Meta-Text-Problem, sondern eine Frage der
   Reichweite.
5. **Der billigste Gewinn liegt in sechs URLs, die es nicht mehr gibt:** Sie
   sammeln 17 der 128 Impressionen (13 %) – eine davon auf **Position 5,2** –
   und liefern Nutzern eine Meta-Refresh-Seite statt Inhalt.

---

## 1 · Bewertung in Zahlen (jede Zahl mit Quelle)

| Kennzahl | Wert | Quelle / Zeitraum |
|---|---|---|
| Bekannte URLs in der Property | **437** | Abdeckungs-Export, Sitemap „Alle bekannten Seiten" |
| davon indexiert | **117 (26,8 %)** | dasselbe, Datenstand 19.10.2026 |
| davon nicht indexiert | **320** | dasselbe |
| … Grund „Nicht gefunden (404)" | **223** | `uebersicht.csv` |
| … „Gefunden – zurzeit nicht indexiert" | **69** | `uebersicht.csv` |
| … „Durch robots.txt blockiert" | **18** | `uebersicht.csv` (Gateways `/go/…`) |
| … „Durch noindex ausgeschlossen" | **5** | `uebersicht.csv` (Vertrag, gewollt) |
| … „Gecrawlt – zurzeit nicht indexiert" | **4** | `uebersicht.csv` |
| … „Seite mit Weiterleitung" | **1** | `uebersicht.csv` |
| Indexierbare Seiten laut Repo | **99** von 258 Build-URLs | `befund.json` → `wahrheit` |
| Index-Puffer (Index-Einträge über Bestand) | **18** | `befund.json` → `kennzahlen` |
| Impressionen (28 Tage, Seiten) | **128** auf 25 Seiten | `top_seiten_28t.json` |
| Impressionen (28 Tage, Suchbegriffe) | **49** auf 19 Begriffe | `top_suchbegriffe_28t.json` |
| Klicks (28 Tage und 35 Tageszeilen) | **0** | beide Quellen |
| Impressionen je Tag | **2,07** (30-Tage-Export) · **3,7** (35 Tage API) | `kennzahlen` / `tagesdaten.jsonl` |
| Tage mit mindestens einer Impression | **29 von 35** | `tagesdaten.jsonl` |
| Bester Tag | 23.10.2026 mit **25 Impressionen** | `tagesdaten.jsonl` |
| Seiten in Position 3–25 („in Reichweite") | **12** | `prioritaet.json` |
| Suchbegriffe in Position ≤ 10 | **3** (davon 1 Marken-Variante, 2 Fragesätze) | `top_suchbegriffe_28t.json` |
| Tote interne Linkziele | **0** (vorher 4 Ziele / 14 Verlinkungen; geheilt am 27.10.2026) | `befund.json` → `tote_ziele` |
| Seiten ohne redaktionellen Auslink | **14** (inkl. aller 10 Werkzeuge) | `befund.json` → `verlinkung` |
| Median Auslinks je Seite | **6** (Summe 539) | dasselbe |
| Alt-URLs, aus dem Bestand ableitbar | **136** | eigene Rechnung, Abschnitt 3 |
| Kandidatenraum offen (nach Übernahme) | **26** – 24 Taxonomie, 2 ohne Ziel | `gsc_abdeckung --kandidaten`, Stand 27.10.2026 |
| Alarmanomalie | 17.10.2026: nicht indexiert 261 → **320**, indexiert 138 → **117** | `kennzahlen.anomalien` |

---

## 2 · Befund A — 93 % der „nicht indexiert"-Fälle sind Altlasten

Die 320 nicht indexierten Einträge sind **kein Qualitätsurteil über die
Texte**. Sie sind fast vollständig Aufräumarbeit:

- **223 × 404** – URLs, die es nicht mehr gibt. Der Repo-Bestand erklärt davon
  nachweislich 30 (23 abgeschaltete Taxonomie-Archive + 7 bewusst entfallene
  Alt-URLs, Regel D).
- **18 × robots.txt** – die 20 `/go/`-Gateways, gewollt gesperrt, im Vertrag
  dokumentiert.
- **5 × noindex** – Newsletter-Funnel und Suche, gewollt.
- **69 × „gefunden, nicht indexiert"** – die einzige Gruppe, die tatsächlich
  etwas über Inhalte aussagt (Abschnitt 6).
- **4 × „gecrawlt, nicht indexiert"** – davon 2 namentlich bekannt (Abschnitt 6).

**Konsequenz:** Solange die 404er nicht abgeräumt sind, misst die Indexquote
das Aufräumtempo, nicht die Inhaltsqualität. Jede Optimierung am Text wird von
dieser Zahl überlagert.

---

## 3 · Befund B — 136 Alt-URLs sind aus dem Bestand ableitbar

### 3.1 Wie gerechnet wurde

Der Kandidatenraum in `scripts/gsc_abdeckung.py` (`kandidatenraum()`) erzeugt
aus jeder live stehenden Seite genau zwei historische Formen:
`/posts/<slug>/` (ohne Datumspräfix) und `/posts/<slug>(1)/` (Zähler-Dublette).
Beide waren real, beide sind nicht live. Diese 162 Kandidaten ohne Entscheidung
habe ich gegen `content/` und die Weiterleitungskarte geprüft:

| Klasse | Anzahl | Behandlung |
|---|---|---|
| Genau **ein** Live-Ziel, Ziel ist `draft: false` | **136** | Weiterleitung Regel A (Anhang A) |
| Taxonomie-URLs (`/tags/…`, `/categories/…`) | **24** | bleiben 404 (Entscheidung „Index-Hygiene", Regel E) |
| ohne Ziel | **2** (`/posts/posts/`, `/posts/posts(1)/`) | 404 bleibt, kein Themenbezug |

Die 136 teilen sich exakt hälftig: **68 `(1)`-Dubletten** und **68 datumslose
URLs** – also im Schnitt **zwei Altformen je Live-Artikel**. Kein Ziel ist ein
Entwurf, keine Kette, keine Schleife (geprüft gegen `weiterleitungen.yaml` und
`url_entfallen.yaml`). Die vollständige Liste steht in **Anhang A**.

### 3.2 Warum das Muster belegt ist

Von den 115 bereits dokumentierten Weiterleitungen in
`data/weiterleitungen.yaml` sind **59 Quellen datumslos** (`/posts/<slug>/` →
`/posts/<datum>-<slug>/`). Die Umbenennung auf das Datumssystem hat also
nachweislich eine ganze Generation von URLs erzeugt – die 68 neuen Fälle sind
dieselbe Klasse. Ein Git-Beleg ist in dieser Arbeitskopie nicht möglich (flacher
Clone mit einem Commit); der Beleg kommt hier aus der Weiterleitungskarte
selbst.

### 3.3 Die ehrliche Einschränkung

Der Kandidatenraum ist laut eigener Dokumentation eine **Obergrenze, kein
Nachweis**: „Ob Google genau diese URL je gesehen hat, sagt nur die
Detail-Liste." Die 404-Detail-Liste fehlt
(`befund.kennzahlen.detail_fehlend`) – deshalb steht sie als Beweisfrage im
Repo und nicht als Behauptung.

**Was daraus folgt:** Der Anhang A ist ein *Vorschlag*, der erst nach dem
Export der 404-Liste zur Wahrheit wird:

```bash
# 1) In der Search Console: Indexierung → Seiten → „Nicht gefunden (404)" → Exportieren
# 2) einlesen und Zuordnungen prüfen (schreibt nichts):
python3 scripts/gsc_abdeckung.py --vorschlaege "details/Nicht gefunden (404).csv"
```

### 3.4 Was das bringt

- **Crawl-Budget:** Jede 404, die Google noch abruft, ist ein Abruf, den eine
  neue Seite nicht bekommt. Bei 2 Impressionen pro Tag ist der Crawl-Besuch
  der Engpass, nicht die Klickrate.
- **Signal:** 136 Weiterleitungen sind 136 ehrliche Antworten („die Seite ist
  hier") statt 136 Sackgassen.
- **Rechenbarkeit:** Danach ist die 404-Zahl eine Entscheidung, keine
  Hinterlassenschaft – und die Indexquote wird endlich vergleichbar.

---

## 4 · Befund C — Impressionen landen auf Seiten, die es nicht gibt

Sechs URLs stehen im Leistungsbericht, sind aber **nicht live**. Sie sammeln
**17 von 128 Impressionen (13 %)**:

| Impressions | Position | URL | Zustand |
|---:|---:|---|---|
| 7 | 19,4 | `/posts/kuehlschrank-strom-sparen-einstellung/` | Weiterleitung → `/posts/2026-08-19-energiediebe-stoppen-so-kannst-du-stromfresser-finden/` |
| 6 | **5,2** | `/posts/2026-08-07-frugalismus-fuer-den-erfolg/` | Weiterleitung → `/posts/2026-08-24-mehr-freiheit-durch-verzicht-clevere-frugalismus-tipps/` |
| 1 | 4,0 | `/posts/depot-umzug-steuerfrei-wechseln/` | Weiterleitung → `/pillar/konto-karten/` |
| 1 | 80,0 | `/posts/elementarschadenversicherung-hochwasser-starkregen/` | Weiterleitung → `/pillar/versicherungen/` |
| 1 | 6,0 | `/tags/haushaltsbuch/` | 404 (Regel E) |
| 1 | 10,0 | `/tags/reiser%C3%BCcktritt/` | 404 (Regel E) |

**Ursache:** GitHub Pages kann keine echten HTTP-301 setzen. Die 115
Weiterleitungen sind Meta-Refresh-Seiten mit `noindex,follow` – Google
akzeptiert sie, überträgt aber schwächer und **behält die alte URL eine Zeit
lang im Suchergebnis**. Genau das sieht man oben: Position 5,2 für eine Seite,
die nur weiterleitet.

**Maßnahme:** Cloudflare-Proxy prüfen und echte 301 scharf schalten.

```bash
python3 scripts/weiterleitungen.py --proxy-check   # braucht Internet
python3 scripts/weiterleitungen.py --cloudflare    # erzeugt cloudflare/redirects/bulk-redirects.csv
```

Parallel dazu: die vier Ziel-URLs aus den Artikeln heraus verlinken, damit die
Nachfrage beim Live-Ziel ankommt statt beim Stub.

---

## 5 · Befund D — Vier tote Verlinkungen, alle vier sind geparkte Entwürfe

> **Erledigt am 27.10.2026.** Alle 14 Verlinkungen sind bereinigt; `tote_ziele`
> steht auf 0, W11 ist aus dem Befund verschwunden. Was genau geändert wurde,
> steht in Abschnitt 13. Die Analyse darunter bleibt als Begründung stehen –
> und die Entscheidung „publizieren oder geparkt lassen" ist weiter offen.

`befund.widersprueche` (W11) meldete 4 Linkziele, die nicht gebaut werden – im
Rendering stand dort nur Text. **14 Verlinkungen** zeigten ins Leere, und alle
vier Ziele sind `draft: true`:

| Ziel (Entwurf) | Verlinkungen von | Weiterleitung vorhanden? |
|---|---:|---|
| `2026-08-17-privathaftpflicht-…` | 7 (u. a. `/pillar/versicherungen/`, Girokonto, Kreditkarte, Notgroschen) | **nein** |
| `2026-08-26-kfz-versicherung-vergleich-…` | 4 (u. a. `/pillar/versicherungen/`) | **nein** |
| `2026-08-12-dein-haus-sicher-schuetzen-…` | 2 | ja, Regel C → `/pillar/versicherungen/` |
| `2026-08-18-wohngebaeudeversicherung-vergleich-…` | 1 | **nein** |

Das trifft ausgerechnet die Themenwelt **Versicherungen**: Der Pillar zeigt auf
Artikel, die es nicht gibt – bei nur 2 redaktionellen Inlinks auf diesen Pillar
(die stärksten Pillars haben 17 und 24) und drei Impressions in 28 Tagen. Für
Nutzer ist das eine Sackgasse, für Google ein Hinweis auf unfertige Struktur.

**Zwei Wege, Entscheidung ist Redaktionssache:**

1. **Entlinken** (schnell, risikofrei): Die vier Stellen auf
   `/pillar/versicherungen/` oder auf einen Live-Artikel zeigen. Entspricht der
   bestehenden Regel C für geparkte Beiträge.
2. **Publizieren** (langsam, aber richtig): Für alle vier liegen Cover und
   Audio vor (`data/covers_manifest.json`, `data/audio/`), `lastmod`
   21.09.–14.10.2026. Sie sind aber nach dem Redaktions-Standard (RS1–RS3)
   geparkt – ob sie ihn erfüllen, entscheidet `npm run reserve:check`, nicht
   dieser Bericht. Wenn sie live gehen, verschwinden 4 tote Links und 4 der 30
   Entwürfe – und der Versicherungs-Pillar bekommt endlich Inhalt.

Bis zur Entscheidung gilt: **kein Live-Artikel verlinkt einen Entwurf.**

### 5.1 Das Werkzeug-Cluster ist eine Insel

14 Seiten haben keinen redaktionellen Auslink, darunter **alle 10
Werkzeug-Seiten**; `/werkzeuge/` hat umgekehrt **keinen redaktionellen
Inlink** (nur den Menüpunkt). Die Werkzeuge sind das Alleinstellungsmerkmal der
Seite und bekommen intern null Kontext. Ein Absatz plus Link aus den drei
stärksten Artikeln (Energiespar-Tricks, Fixkosten, Girokonto) wäre der
billigste Sichtbarkeitsgewinn nach den Weiterleitungen.

---

## 6 · Befund E — Die 69 „gefunden, zurzeit nicht indexiert"

Das ist die **einzige** Gruppe, bei der Google sagt: „Ich kenne die URL, ich
hole sie aber nicht." Bei 99 indexierbaren Seiten sind das 70 % des Bestands.
Typische Ursachen in dieser Größenordnung:

1. **Zu wenig interne Nachfrage** – Seiten, die nur aus Listen und Sitemap
   erreichbar sind, bekommen selten einen Crawl.
2. **Dünne Eigenständigkeit** – mehrere Artikel zur gleichen Suchabsicht
   (die `(1)`-Dubletten zeigen, dass es diese Doppelungen gab).
3. **Crawl-Budget** – solange 223 404er abgerufen werden, bleibt weniger für
   neue Seiten.

**Reihenfolge der Maßnahmen:**

```bash
npm run gsc:prioritaet     # Anfrage-Wellen (M2): welche Seiten zuerst
npm run gsc:verlinkung     # Verlinkungsauftrag: Quelle → Ziel
npm run gsc:indexieren     # Indexierung in Wellen anfragen (Kontingent beachten)
npm run gsc:abdeckung:gate # nach 14 Tagen: kein Rückschritt?
```

**Die 4 „gecrawlt, nicht indexiert"** sind namentlich teilweise bekannt
(`data/gsc/abdeckung/details/Gecrawlt – zurzeit nicht indexiert.csv`):

- `/posts/2026-08-21-haushaltsbuch-fuehren-app-excel-oder-papier/` – zuletzt
  gecrawlt 20.10.2026, Status „Ausstehend"
- `/posts/2026-10-12-dein-weg-zu-geringeren-monatskosten-schritt-fuer-schritt/`
  – zuletzt gecrawlt 20.10.2026, Status „Ausstehend"

„Ausstehend" heißt: Die Entscheidung ist noch offen, nicht endgültig negativ.
Der Hebel ist deshalb kein weiterer Indexierungsantrag, sondern ein
Relevanzsignal: **Inlinks aus starken Artikeln und eine klarere Suchabsicht im
Titel.**

---

## 7 · Befund F — Reichweite: 12 Seiten stehen in Position 3–25

| Impressions | Position | Inlinks | URL |
|---:|---:|---:|---|
| 12 | 8,4 | 17 | `/pillar/internet-dsl/` |
| 10 | 10,5 | 7 | `/impressum/` |
| 9 | 12,3 | 6 | `/datenschutz/` |
| 6 | 3,2 | 2 | `/pillar/` |
| 6 | 5,2 | – | `/posts/2026-08-07-frugalismus-fuer-den-erfolg/` *(Stub, siehe C)* |
| 4 | 7,2 | 3 | `/posts/2026-08-24-preisgarantie-gas-…/` |
| 4 | 18,2 | 15 | `/posts/2026-08-17-kostenloses-girokonto-…/` |
| 2 | 6,5 | 2 | `/posts/2026-08-14-sparen-im-herbst-…/` |
| 2 | 7,0 | 4 | `/posts/2026-08-14-internet-dsl-wechseln-…/` |
| 1 | 4,0 | 9 | `/posts/2026-08-14-wlan-verbessern-…/` |
| 1 | 4,0 | 4 | `/posts/2026-08-14-gasrechnung-senken-…/` |
| 1 | 7,0 | 3 | `/posts/2026-10-12-dein-weg-zu-geringeren-monatskosten-…/` |

**Auffällig:** Zwei der sichtbarsten Seiten sind **Pflichtseiten**
(Impressum Position 10,5, Datenschutz 12,3). Sie kosten keine Arbeit, zeigen
aber, wie klein die Datenbasis ist – bei 1–12 Impressionen ist keine
Position eine Messung, sondern ein Zufallswert.

### 7.1 Der einzige Begriff mit echter Nachfrage

| Impressions | Position | Suchbegriff |
|---:|---:|---|
| **18** | 42,8 | `energiekosten senken` |
| 5 | 7,4 | `frank dsl` (Marken-Variante) |
| 4 | 25,5 | `energieeinsparung` |
| 2 | 42,5 | `energiesparmaßnahme` |
| 2 | 23,5 | `energiespar lösungen` |
| 3 | **3,0** | `welche finanz-app bietet die besten spartipps basierend auf dem eigenen konsumverhalten?` |
| 2 | **5,5** | `wie kann ich kosten durch energieoptimierung senken?` |

**Der eigentliche Befund steht daneben:** Die Autorität und der Inhalt liegen
auf zwei verschiedenen Seiten. `/pillar/strom-sparen/` hat mit **24 Inlinks die
meisten eingehenden Links der ganzen Site** – und **0 Impressionen**.
`/pillar/frugalismus/` (17 Inlinks) ebenfalls 0. Der Artikel mit den 35
Impressionen hat dagegen nur 2 Inlinks. Google findet also Nachfrage bei einer
Seite ohne Autorität und Autorität bei Seiten ohne Nachfrage. Bevor neuer Text
entsteht, muss beides zusammen: Der Pillar übernimmt die Suchabsicht
„energiekosten senken" (Titel, Kurzantwort, Rechentabelle) und verlinkt die
Detailartikel; die Artikel verlinken zurück.

Daraus folgen zwei sehr unterschiedliche Aufgaben:

1. **`energiekosten senken` (18 Impressionen, Position 42,8):** Das ist der
   einzige Begriff mit Volumen. Die zugehörige Seite
   (`/posts/2026-10-12-kleine-energiespar-tricks-…/`, 35 Impressionen,
   Position 35,7) ist die sichtbarste Inhaltsseite der Site – und steht auf
   Seite 4. Hier lohnt **Tiefe statt neuer Artikel**: Rechenbeispiele in Euro,
   Geräte-Tabelle, Verbrauchswerte, Verlinkung aus `/pillar/strom-sparen/` und aus
   den Werkzeugen (Fixkosten-Scanner, Effektivpreis-Rechner).
2. **Fragesätze in Position 3,0 und 5,5:** Das sind
   Konversations-/KI-Suchanfragen. Sie kommen ohne Klick – genau dafür gibt es
   im Repo das GEO-Protokoll (`docs/ANLEITUNG-GEO-PROTOKOLL.md`). Antworten im
   ersten Absatz, Frage als H2, Kurzantwort-Block: das ist bereits Standard,
   aber die Seiten, die *diese* Fragen beantworten, sind nicht die
   Energiespar-Seite. Kurzantwort-Blöcke auf die Frageformulierung umschreiben.

---

## 8 · Befund G — CTR: heute kein Signal, also keine Meta-Bastelei

**128 Impressionen, 0 Klicks.** Gewichtete Durchschnittsposition der Seiten:
20,9 (Suchbegriffe: 37,8). Selbst mit optimistischen 1 % CTR wären ~1,3 Klicks
zu erwarten – Null liegt innerhalb dieser Schwankungsbreite. Wer jetzt Titel und Meta-Descriptions „optimiert", ändert Dinge,
deren Wirkung er nicht messen kann.

**Was stattdessen gilt:**

- Die Meta-Qualität ist im Repo bereits durch Gates abgesichert; hier ist kein
  blinder Fleck bekannt.
- Die **eine** belastbare CTR-Beobachtung: die Stub-URLs aus Befund C stehen
  auf Position 4–5 und bekommen keine Klicks – weil sie keine Inhalte sind.
  Das ist kein Snippet-Problem, sondern ein 301-Problem.
- CTR-Arbeit wird sinnvoll, sobald die Indexquote über ~60 % liegt. Vorher
  fehlt die Stichprobe.

---

## 9 · Maßnahmenplan

Reihenfolge nach Wirkung je Aufwand. „Beleg" ist die Zahl, die die Maßnahme
begründet – nicht die Zahl, die sie verspricht.

| ID | Prio | Maßnahme | Beleg | Aufwand | Wirkung | Messgröße nach 14 Tagen |
|---|---|---|---|---|---|---|
| **M1** | P1 | 404-Detail-Liste exportieren, `--vorschlaege` laufen lassen | 193 von 223 404ern ohne Erklärung | 30 min | macht M2 belegbar | 404er mit Zuordnung |
| ~~**M2**~~ | ✅ | Anhang A übernommen: 136 Einträge in `data/weiterleitungen.yaml`, `--check` → `--build` → `--verify` | 136 ableitbare Alt-URLs, 2 je Live-Artikel | erledigt | Kandidatenraum offen **162 → 26** | 404er gesamt |
| **M3** | P1 | Cloudflare-Proxy prüfen, echte 301 aktivieren | 13 % der Impressionen auf Nicht-Live-URLs | 30 min | Nachfrage kommt beim Ziel an | Impressionen auf Stubs |
| ~~**M4**~~ | ✅ | 4 tote Linkziele: entlinken oder publizieren — **erledigt 27.10.2026** (entlinkt bzw. auf den Pillar umgehängt) | 14 Verlinkungen auf 4 Entwürfe | erledigt | keine Sackgassen mehr | `tote_ziele` = **0** ✔ |
| **M5** | P2 | 69 „gefunden, nicht indexiert" in Wellen anfragen + Inlinks setzen | 70 % des Bestands nicht im Index | 2 h | Indexquote | `quote_indexiert` |
| **M6** | P2 | Werkzeug-Cluster redaktionell verlinken (3 Artikel → 10 Werkzeuge) | 10 Werkzeugseiten ohne Inlink, `/werkzeuge/` nur im Menü | 1 h | interne Autorität auf die USP-Seiten | Inlinks je Werkzeug |
| **M7** | P2 | `energiekosten senken`: Autorität und Inhalt zusammenführen (Pillar + Artikel), dann vertiefen | 18 Impressionen, Position 42,8 · Pillar `strom-sparen` hat 24 Inlinks, aber 0 Impressionen | 4 h | erste Seite-1-Position mit Volumen | Position des Begriffs |
| **M8** | P2 | 2 Titel-Zwillinge im Vorrat entscheiden (`5-einfache-frugalismus-tricks…`, `7-gewohnheiten…`) | je 1 live + 1 Entwurf, U2-Risiko beim Publizieren | 30 min | verhindert Kannibalisierung | `test_publish_gate_uniqueness` grün |
| **M9** | P3 | Taxonomie-Entscheidung (24 URLs bleiben 404) im Abschlussbericht festhalten | 24 von 162 Kandidaten sind Regel E | 15 min | Zahl ist Entscheidung, nicht Rest | dokumentiert |
| **M10** | P3 | Indexquote als Wochen-KPI + Cockpit-Zeile | 26,8 % bei einer Momentaufnahme | 15 min | Fortschritt wird sichtbar | Zeile in `COCKPIT.md` |

**Reihenfolge, wenn nur zwei Stunden Zeit sind:** M1 → M3. Die 404-Liste macht
den größten Posten rechenbar, die echten 301 holen die vorhandene Nachfrage
dort ab, wo Inhalt liegt.

---

## 10 · Wochenroutine (15 Minuten, freitags)

```bash
npm run gsc:daten            # Leistungsdaten holen (API, kostenlos)
npm run gsc:abdeckung        # Befund gegenrechnen (Export muss aktuell sein)
npm run gsc:abdeckung:gate   # Exit 1 bei Rückschritt
npm run gsc:abdeckung:md     # Befund als Markdown lesen
npm run gsc:prioritaet       # nächste Anfrage-Welle
```

Ein Export pro Woche, fünf Befehle, eine Zahl zum Beobachten:
`quote_indexiert`.

---

## 11 · Was noch fehlt (5 Exporte, exakte Klickwege)

Ohne diese Dateien bleibt die Zuordnung eine Obergrenze. Weg jeweils:
Search Console → **Indexierung → Seiten** → Grund anklicken → **Exportieren**.

1. `Nicht gefunden (404).csv` — **wichtigster Export**, macht Anhang A zur Wahrheit
2. `Gefunden – zurzeit nicht indexiert.csv` — welche 69 Seiten gemeint sind
3. `Seite mit Weiterleitung.csv` — ob die 115 Weiterleitungen ankommen
4. `Alternative Seite mit ordnungsgemäßem Canonical-Tag.csv`
5. `Durch robots.txt blockiert.csv` — Gegenprobe zu den 18 Gateways

Danach:

```bash
python3 scripts/gsc_abdeckung.py --import <verzeichnis-mit-den-csvs> --audit --md
```

---

## 12 · Grenzen dieser Bewertung

- **Datenmenge.** 128 Impressionen und 0 Klicks in 28 Tagen sind zu klein für
  Kausalaussagen. Jede Positionsangabe unter 10 Impressionen ist eine
  Stichprobe, kein Ranking.
- **Zeitfenster.** Die API liefert im Repo 35 Tageszeilen (20.09.–24.10.2026);
  die Search Console behält maximal 16 Monate. Ältere Vergleiche brauchen
  Exporte.
- **Zeilenlimit.** Die Oberfläche zeigt maximal 1.000 Zeilen je Bericht; für
  vollständige Auswertungen braucht es die API (vorhanden) oder den
  BigQuery-Bulk-Export (nicht eingerichtet).
- **Keine Wettbewerbsdaten.** Die Search Console zeigt nur eigene
  Suchanfragen. Für Wettbewerbsvergleiche ist ein kostenloses Fremdtool nötig
  (Ahrefs Free auf der eigenen Domain liefert Backlinks und Site-Audit, aber
  keine Wettbewerber).
- **Kein Git-Beleg in dieser Kopie.** Der Checkout ist flach (ein Commit);
  die Umbenennung auf das Datumssystem ist über die 59 datumslosen
  Weiterleitungsquellen belegt, nicht über die Historie.
- **Der Anhang ist ein Vorschlag.** Er schreibt nichts. Die Entscheidung
  bleibt bei der Redaktion, die Wache (`weiterleitungen.py --check`) prüft
  Ziele, Ketten und Schleifen.

---

## 13 · Umgesetzt am 27.10.2026 — die 4 toten Linkziele

**Entscheidung:** Die vier geparkten Versicherungs-Artikel werden *nicht*
publiziert (das ist eine Redaktionsentscheidung nach RS1–RS3, nicht Teil dieses
Auftrags). Also gilt die bestehende Regel C: Der Live-Artikel zeigt auf den
Pillar des Themas, oder die Verlinkung fällt weg. Aus einem Entwurf wird nichts
umgehängt, was selbst ein Entwurf ist.

| Datei | Änderung | Warum so |
|---|---|---|
| `content/pillar/versicherungen/index.md` | 2 Sätze ohne Link neu formuliert (Privathaftpflicht, Hausrat/Gebäude); „Cluster-Reihenfolge" als Text statt 4 Links | Ein Selbstlink auf den eigenen Pillar wäre falsch; die Absätze versprachen einen Artikel, den es nicht gibt |
| `posts/2026-08-14-sparen-im-herbst-…` | 4 Verlinkungen entlinkt (Fließtext, Tabelle) | Der Artikel verlinkt den Versicherungs-Pillar bereits in der „Weiterlesen"-Zeile – kein zweiter Link auf dasselbe Ziel |
| `posts/2026-09-03-kreditkarte-vergleichen-…` | 1 Link entlinkt (falsches Ziel: „Kreditkarten-Vergleich 2026" zeigte auf den Kfz-Artikel), 1 Link → `/pillar/versicherungen/` | Der erste war ein Zuordnungsfehler, kein Versicherungsthema |
| `posts/2026-08-17-kostenloses-girokonto-…` | „Weiterlesen"-Link „Privathaftpflicht im Check" → „Ratgeber Versicherungen" | Regel C, Ziel ist live |
| `posts/2026-09-20-finanzieller-puffer-…` | 1 Link → `/pillar/versicherungen/` | Regel C |

**Nachweise (alle am 27.10.2026 ausgeführt):**

| Prüfung | Ergebnis |
|---|---|
| `tote_ziele()` aus `gsc_abdeckung.py` | **0** (vorher 4 Ziele / 14 Quellen) |
| `gsc_abdeckung.py --audit --schreiben` | `befund.json`/`befund.md` neu geschrieben: W11 und „Links ins Leere" entfallen |
| `gsc_abdeckung.py --audit --gate` | **Exit 0** (grün, 0 harte Funde) |
| `url_wache.py` | **grün** (103 Live-URLs, 7 neue seit Snapshot, kein Befund) |
| `weiterleitungen.py --check` | **grün** (115 Weiterleitungen, 7 bewusst 404) |
| `link_density_guard.py` | 88 % im Goldkorridor (≥ 85 %); die vier Artikel bei 5 / 2 / 7 / 8 Post-Links (Korridor 2–9) |

**Bewusst nicht geändert:**

- **13 Verlinkungen in 8 Entwürfen** (Entwurf → Entwurf innerhalb des
  Versicherungs-Clusters). Sie werden nicht gebaut, sind also kein Befund – und
  sie werden *richtig*, sobald der Cluster veröffentlicht wird. Sie jetzt zu
  entlinken hieße, die Verlinkung zweimal zu bauen.
- **`lastmod` der fünf Seiten.** Es wurde kein Fakt geändert, nur eine
  Verlinkung. Ein neues Datum ohne Faktenbezug wäre ein falsches Frischesignal.

**Offen bleibt (Redaktionsentscheidung, nicht Teil dieses Auftrags):** die vier
Entwürfe veröffentlichen. Dann kommen vier Artikel in den Versicherungs-Pillar –
und die 13 Entwurfs-Verlinkungen werden mit einem Schlag gültig.

---

---

## 14 · Umgesetzt am 27.10.2026 — 136 Weiterleitungen + vier Veröffentlichungen

### 14.1 Die 136 Weiterleitungen aus Anhang A sind in der Quelle

| Schritt | Ergebnis |
|---|---|
| `data/weiterleitungen.yaml` | **+136** Einträge (Regel A), Kopfkommentar mit Herkunft, `stand: 2026-10-27` |
| Bestand danach | **251** Einträge (142 A · 73 B · 36 C), keine doppelte Quelle |
| `weiterleitungen.py --check` | **grün** (251 Weiterleitungen, 7 bewusst 404, 103 Live-URLs) |
| `weiterleitungen.py --build` | **136 Seiten geschrieben**, 0 veraltete entfernt |
| `weiterleitungen.py --verify` | **251 von 251** Seiten stimmen mit der Quelle überein |
| `url_wache.py` | **grün** |
| Kandidatenraum (`gsc_abdeckung --kandidaten`) | offen **162 → 26** · dokumentiert 122 → **257** |

Die 26 offenen Kandidaten sind abschließend erklärt: **24** Taxonomie-URLs
(`/tags/…`, `/categories/…` – Entscheidung „Index-Hygiene", Regel E) und **2**
ohne Ziel (`/posts/posts/`, `/posts/posts(1)/` – kein Themenbezug, 404 bleibt).

**Test angepasst, nicht umgangen:** `test_umfang` pinnt die Anzahl
(115 → 251 → 250, siehe 14.3) mit Begründung im Test. Neu dazugekommen ist
`test_weiterleitungsquelle_ist_nie_live`: keine Quelle darf gleichzeitig live
sein – genau der Fehler, den eine Veröffentlichung sonst hinterlässt.

### 14.2 Die vier Versicherungs-Artikel sind veröffentlichungsreif und in der Kadenz

Ausgangslage: **drei** der vier hatten offene harte Haus-Stil-Regeln, zwei davon
im Zustand `hold` (Redaktions-Standard), einer `manual`. Der einzige ohne Befund
war der Kfz-Artikel.

| Artikel | Befund vorher | Änderung | Befund jetzt |
|---|---|---|---|
| Haus sicher schützen | RS1, RS2, RS3 | Überschrift „Das Wichtigste in **Kurzform**" → „in **Kürze**" (die Box hatte bereits 6 Bullets); 1 H2 als Frage; 1 Faustregel | **0** |
| Privathaftpflicht | RS2, RS3 | 2 H2 als Frage; 1 Faustregel | **0** |
| Wohngebäudeversicherung | RS2, RS3 | 2 H2 als Frage; 1 Faustregel | **0** |
| Kfz-Versicherung | — (alle grün) | keine Textänderung | **0** |

Die Faustregeln kommen **nicht von mir**, sondern aus dem SSOT-Pool
(`redaktions_standard.faustregel_waehlen` gegen den Live-Bestand gemessen,
#766); dadurch ist jeder der drei Sätze im Bestand einmalig. Keine inhaltliche
Aussage, keine Zahl, kein Rechenweg und keine Quelle wurde geändert – bei allen
drei war RS4 (nummerierte Liste), RS6 (Belegpflicht) und RS7 (Autor) schon grün.

**YMYL-Siegel:** Für die drei geänderten Artikel war das Siegel an die alte
Fassung gebunden (E17). Nach der Änderung wurde neu versiegelt –
`aenderungsgrund` dokumentiert ausdrücklich, dass nur die Stil-Module ergänzt
wurden und Aussagen-/Zahlenprotokoll unverändert gelten. Stand jetzt:

| Prüfung | Ergebnis |
|---|---|
| `editorial_review_gate --file <je Artikel> --strict` | **4 × freigegeben, 0 blockiert** |
| `redaktions_standard --file <je Artikel> --include-drafts` | **4 × 0 harte Regeln** |
| `cadence_guard --check` | **grün** (Mo/Mi/Fr, kein Off-Day, kein Defizit) |
| `h1_wache` | bestanden |
| `duplikat_guard` | 0 Funde |
| `link_density_guard` | 88 % im Goldkorridor |

**Weg ins Live-Blog:** Alle vier stehen auf `queue`
(`draft: true` + `cadence_wait: true`), nicht auf `live`. Die Promotion macht
`cadence_guard` – am nächsten Publikationstag (**Mi 28.10.**, 2–3 Artikel/Tag,
danach der Rest am **Fr 30.10.**). Ich habe sie **nicht** von Hand live
geschaltet: laut `docs/ANLEITUNG-ENDREDAKTION.md` ist `cadence_guard` der
einzige Weg ins Blog, und ein Live-Artikel an einem Dienstag wäre ein
Kadenz-Verstoß (Wache → Zurückstufung).

### 14.3 Die Weiterleitung des Haus-Artikels musste weichen

`/posts/2026-08-12-dein-haus-sicher-schuetzen-das-neue-vorsorge-update-2026/`
war als Regel C auf den Versicherungs-Pillar weitergeleitet. Sobald der Artikel
wieder ausgeliefert wird, würde die Meta-Refresh-Seite die echte Seite
überschreiben (GitHub Pages kann keine Priorität auflösen).

Deshalb: Eintrag entfernt (**251 → 250**), `static/`-Seite gelöscht, Snapshot
der URL-Wache neu geschrieben (`--snapshot`, 103 URLs). Der Test, der diesen
einen Fall pinnte, ist durch die allgemeine Invariante ersetzt (14.1) – der
Zusammenhang „Regel C endet mit der Veröffentlichung" ist damit dauerhaft
geprüft und nicht nur an einem Beispiel.

**Bewusste Folge:** Bis zur Promotion am Mittwoch liefert diese eine URL 404.
Vorher war es eine Meta-Refresh-Seite. In den GSC-Leistungsdaten taucht die URL
nicht auf (keine Impressionen in 28 Tagen), der Verlust ist also messbar null –
und ab Mittwoch liefert sie Inhalt statt einer Weiterleitung.

### 14.4 Was nach der Promotion noch zu tun ist

1. **Pillar-Links zurückholen.** Der Versicherungs-Pillar verlinkt die vier
   Artikel derzeit nicht (die Links wurden entlinkt, weil die Ziele Entwürfe
   waren). Sobald sie live sind, gehören sie in die „Cluster-Reihenfolge" –
   dann sind es echte, wirksame Links statt Text. Vorher einzutragen würde die
   4 toten Linkziele sofort wieder erzeugen.
2. **13 Entwurfs-Verlinkungen** (Entwurf → Entwurf im Versicherungs-Cluster)
   werden mit der Veröffentlichung gültig, sobald auch die Quell-Entwürfe live
   gehen (u. a. Unfall-, Zahnzusatz-, Tierkrankenversicherung).
3. **`belegketten_wache.py --nur-hochrisiko --report`** vor dem nächsten
   Versiegeln: In dieser Umgebung ist kein Zugriff auf verbraucherzentrale.de /
   gdv.de möglich (nur npm/pypi/github). Die Wache prüft, ob die zitierten
   Adressen noch antworten – sie lief hier **nicht** und steht als offener
   Punkt.
4. **Bestandsbefund, nicht von heute:** `editorial_review_gate --all` meldet
   `2026-09-21-tierkrankenversicherung-hund-katze-kosten` mit E17 (Text nach
   Freigabe geändert). Der Entwurf ist nicht live und war schon vor dieser
   Sitzung offen.

---

---

## 15 · Die zwei offenen Punkte — was geprüft ist und was nicht

### 15.1 Belegketten: hier nicht prüfbar, in CI täglich geprüft

**Der Befund, ungeschminkt:** In dieser Umgebung ist kein Zugriff auf die
zitierten Verlags- und Behördensites möglich (erlaubt sind nur github.com,
npm- und pypi-Registry). Ein Verbindungstest antwortet für
`www.verbraucherzentrale.de`, `www.gdv.de` und `www.gesetze-im-internet.de`
mit HTTP `000` (DNS/Verbindung blockiert). Die Wache läuft trotzdem – und
meldet genau das, was ihre Doku vorsieht:

```
$ python3 scripts/belegketten_wache.py --nur-hochrisiko --json
geprueft: 33   ok: 0   umgeleitet: 0   tot: 0   unklar: 33
"befund": "nicht erreichbar (URLError)"
```

`unklar` blockiert bewusst nicht („eine Wache, die bei jedem Wackler rot wird,
wird abgeschaltet statt gelesen"). **Ein grünes Ergebnis wäre hier also
erschlichen** – es wäre die Abwesenheit von Netz, nicht die Anwesenheit von
Belegen. Deshalb steht der Punkt offen statt erledigt.

**Wo er tatsächlich läuft:** `.github/workflows/redaktionelle-ymyl-pruefung.yml`,
Job `belegketten`, **Mo–Fr 05:20** (cron `20 5 * * 1-5`) mit
`--strict --require-complete`; der Bericht landet als
`BELEGKETTEN-WACHE-REPORT.md` im Step-Summary und als Artefakt. Der nächste
Lauf ist **Mi 28.10. 05:20** – also vor der Promotion der vier Artikel.

**Was ich stattdessen offline prüfen konnte:** ob die vier Artikel eines der
Zitate tragen, die im Audit vom 24.10.2026 nachweislich defekt waren
(`YMYL-PRUEFQUEUE-826-DAUERHEILUNG-PREMIUM-2026-10-24.md`: 5 × 404 nach der
Verbraucherzentrale-Migration + 1 × BaFin-Umleitung):

| Artikel | Quellen | davon in der Todes-Liste | Abrufdatum |
|---|---:|---:|---|
| Haus sicher schützen | 3 | **0** | 2026-10-05 |
| Privathaftpflicht | 3 | **0** | 2026-10-05 |
| Wohngebäudeversicherung | 3 | **0** | 2026-10-05 |
| Kfz-Vergleich | 4 | **0** | 2026-10-24 |

Diese 13 Adressen waren Teil der 22, die am 24.10.2026 einzeln abgerufen und
inhaltlich gegen das Zitat gelesen wurden – sie waren nicht unter den fünf
toten. Der eine bekannte Fall **stiller Ersetzung** betraf den Kfz-Artikel
(GDV-Seite mit den Zahlen des Folgejahres); er zitiert inzwischen die
korrigierte Regionalklassen-Seite **2027** mit Abrufdatum 24.10.2026. Dass die
Seite heute noch dieselbe ist, kann nur der CI-Lauf bestätigen.

**Konsequenz:** An den drei neu versiegelten Fassungen hängt kein neues Risiko
aus diesem Grund – sie zitieren dieselben Adressen wie vorher, geändert wurden
nur die Stil-Module. Die Netzprüfung dieser Adressen passiert im nächsten
CI-Lauf.

### 15.2 Pillar-Links: Wiedervorlage, die sich selbst meldet

Die Links jetzt zurückzuholen wäre falsch (vier Ziele sind noch Entwurf → W11
sofort wieder da). Sie nach der Promotion zu vergessen wäre schlimmer. Also
gibt es statt eines Merkzettels eine Wache:

`scripts/tests/test_versicherungs_cluster_verlinkung.py` (neu, 6 Tests,
`npm run test:versicherungs-cluster`) prüft **beide** Richtungen:

| Regel | heute | nach der Promotion |
|---|---|---|
| Ist ein Cluster-Artikel **live**, muss der Pillar ihn verlinken | grün (alle vier sind Entwurf) | **rot, bis der Link steht** |
| Verlinkt der Pillar einen **Entwurf**, ist das ein Befund | grün | grün |

Dass die Wache wirklich anschlägt, ist nicht behauptet, sondern gezeigt: in
einem Promotions-Szenario (ein Artikel künstlich auf `draft: false` gesetzt,
Pillar unverändert) wird der Test rot mit
`['Kfz-Vergleich (2026-08-26-kfz-versicherung-vergleich-bis-zu-800-euro-sparen)']`.
Der Fall läuft in `publication-reliability-tests.yml` mit (vollständiges
`unittest discover`), ist also nicht auf einen Aufruf von Hand angewiesen.

Die Links selbst stehen als Copy-Paste-Block bereit: **Anhang B**.

---

## Anhang A · Weiterleitungs-Vorschlag (136 Einträge, Regel A)

> **Übernommen am 27.10.2026.** Alle 136 Zeilen stehen in
> `data/weiterleitungen.yaml` (Nachweise in Abschnitt 14.1). Eine davon ist
> wieder entfallen: der Hausvorsorge-Beitrag, weil er veröffentlicht wird
> (Abschnitt 14.3). Die Liste bleibt hier als Beleg stehen.

**So wird daraus Wirklichkeit:**

1. In der Search Console `Nicht gefunden (404).csv` exportieren und mit
   `python3 scripts/gsc_abdeckung.py --vorschlaege "…/Nicht gefunden (404).csv"`
   gegenprüfen. Nur bestätigte Quellen übernehmen.
2. Die bestätigten Zeilen in `data/weiterleitungen.yaml` unter
   `weiterleitungen:` einsortieren (alphabetisch wie der Bestand).
3. Prüfen und bauen:

```bash
python3 scripts/weiterleitungen.py --check     # Ziele live, keine Ketten/Schleifen
python3 scripts/weiterleitungen.py --build     # static/<von>/index.html erzeugen
python3 scripts/weiterleitungen.py --verify
python3 scripts/url_wache.py
```

Alle Ziele sind live (`draft: false`), es entsteht keine Kette und keine
Schleife (geprüft am 27.10.2026).

```yaml
  - {von: "/posts/5-einfache-frugalismus-tricks-fuer-den-alltag(1)/", nach: "/posts/2026-09-11-5-einfache-frugalismus-tricks-fuer-den-alltag/", regel: "A", grund: "Dublette mit Zähler „(1)“: identischer Titel, gleiche Suchabsicht – Regel A"}
  - {von: "/posts/5-einfache-frugalismus-tricks-fuer-den-alltag/", nach: "/posts/2026-09-11-5-einfache-frugalismus-tricks-fuer-den-alltag/", regel: "A", grund: "Alt-URL ohne Datumspräfix: Ordner nach Datumsystem umbenannt – Regel A"}
  - {von: "/posts/50-30-20-regel-beherrsche-dein-budget-im-jahr-2026(1)/", nach: "/posts/2026-09-11-50-30-20-regel-beherrsche-dein-budget-im-jahr-2026/", regel: "A", grund: "Dublette mit Zähler „(1)“: identischer Titel, gleiche Suchabsicht – Regel A"}
  - {von: "/posts/50-30-20-regel-beherrsche-dein-budget-im-jahr-2026/", nach: "/posts/2026-09-11-50-30-20-regel-beherrsche-dein-budget-im-jahr-2026/", regel: "A", grund: "Alt-URL ohne Datumspräfix: Ordner nach Datumsystem umbenannt – Regel A"}
  - {von: "/posts/7-gewohnheiten-fuer-finanzielle-freiheit(1)/", nach: "/posts/2026-10-07-7-gewohnheiten-fuer-finanzielle-freiheit/", regel: "A", grund: "Dublette mit Zähler „(1)“: identischer Titel, gleiche Suchabsicht – Regel A"}
  - {von: "/posts/7-gewohnheiten-fuer-finanzielle-freiheit/", nach: "/posts/2026-10-07-7-gewohnheiten-fuer-finanzielle-freiheit/", regel: "A", grund: "Alt-URL ohne Datumspräfix: Ordner nach Datumsystem umbenannt – Regel A"}
  - {von: "/posts/abos-und-vertraege-stiller-posten-haushaltsplan(1)/", nach: "/posts/2026-08-17-abos-und-vertraege-stiller-posten-haushaltsplan/", regel: "A", grund: "Dublette mit Zähler „(1)“: identischer Titel, gleiche Suchabsicht – Regel A"}
  - {von: "/posts/abos-und-vertraege-stiller-posten-haushaltsplan/", nach: "/posts/2026-08-17-abos-und-vertraege-stiller-posten-haushaltsplan/", regel: "A", grund: "Alt-URL ohne Datumspräfix: Ordner nach Datumsystem umbenannt – Regel A"}
  - {von: "/posts/balkonkraftwerk-foerderung-so-holst-du-dir-geld-zurueck(1)/", nach: "/posts/2026-10-09-balkonkraftwerk-foerderung-so-holst-du-dir-geld-zurueck/", regel: "A", grund: "Dublette mit Zähler „(1)“: identischer Titel, gleiche Suchabsicht – Regel A"}
  - {von: "/posts/balkonkraftwerk-foerderung-so-holst-du-dir-geld-zurueck/", nach: "/posts/2026-10-09-balkonkraftwerk-foerderung-so-holst-du-dir-geld-zurueck/", regel: "A", grund: "Alt-URL ohne Datumspräfix: Ordner nach Datumsystem umbenannt – Regel A"}
  - {von: "/posts/bankgebuehren-senken-7-schritte-zum-guenstigeren-konto(1)/", nach: "/posts/2026-10-24-bankgebuehren-senken-7-schritte-zum-guenstigeren-konto/", regel: "A", grund: "Dublette mit Zähler „(1)“: identischer Titel, gleiche Suchabsicht – Regel A"}
  - {von: "/posts/bankgebuehren-senken-7-schritte-zum-guenstigeren-konto/", nach: "/posts/2026-10-24-bankgebuehren-senken-7-schritte-zum-guenstigeren-konto/", regel: "A", grund: "Alt-URL ohne Datumspräfix: Ordner nach Datumsystem umbenannt – Regel A"}
  - {von: "/posts/bueroausstattung-steuerlich-clever-absetzen-so-vermeidest(1)/", nach: "/posts/2026-10-05-bueroausstattung-steuerlich-clever-absetzen-so-vermeidest/", regel: "A", grund: "Dublette mit Zähler „(1)“: identischer Titel, gleiche Suchabsicht – Regel A"}
  - {von: "/posts/bueroausstattung-steuerlich-clever-absetzen-so-vermeidest/", nach: "/posts/2026-10-05-bueroausstattung-steuerlich-clever-absetzen-so-vermeidest/", regel: "A", grund: "Alt-URL ohne Datumspräfix: Ordner nach Datumsystem umbenannt – Regel A"}
  - {von: "/posts/campingurlaub-2026-clever-sparen-ohne-komfortverlust(1)/", nach: "/posts/2026-10-07-campingurlaub-2026-clever-sparen-ohne-komfortverlust/", regel: "A", grund: "Dublette mit Zähler „(1)“: identischer Titel, gleiche Suchabsicht – Regel A"}
  - {von: "/posts/campingurlaub-2026-clever-sparen-ohne-komfortverlust/", nach: "/posts/2026-10-07-campingurlaub-2026-clever-sparen-ohne-komfortverlust/", regel: "A", grund: "Alt-URL ohne Datumspräfix: Ordner nach Datumsystem umbenannt – Regel A"}
  - {von: "/posts/dein-weg-zu-geringeren-monatskosten-schritt-fuer-schritt(1)/", nach: "/posts/2026-10-12-dein-weg-zu-geringeren-monatskosten-schritt-fuer-schritt/", regel: "A", grund: "Dublette mit Zähler „(1)“: identischer Titel, gleiche Suchabsicht – Regel A"}
  - {von: "/posts/dein-weg-zu-geringeren-monatskosten-schritt-fuer-schritt/", nach: "/posts/2026-10-12-dein-weg-zu-geringeren-monatskosten-schritt-fuer-schritt/", regel: "A", grund: "Alt-URL ohne Datumspräfix: Ordner nach Datumsystem umbenannt – Regel A"}
  - {von: "/posts/digitaler-turbo-warum-der-dns-hack-dein-netz-beschleunigt(1)/", nach: "/posts/2026-09-04-digitaler-turbo-warum-der-dns-hack-dein-netz-beschleunigt/", regel: "A", grund: "Dublette mit Zähler „(1)“: identischer Titel, gleiche Suchabsicht – Regel A"}
  - {von: "/posts/digitaler-turbo-warum-der-dns-hack-dein-netz-beschleunigt/", nach: "/posts/2026-09-04-digitaler-turbo-warum-der-dns-hack-dein-netz-beschleunigt/", regel: "A", grund: "Alt-URL ohne Datumspräfix: Ordner nach Datumsystem umbenannt – Regel A"}
  - {von: "/posts/dns-server-wechseln-schnelleres-sichereres-internet(1)/", nach: "/posts/2026-08-26-dns-server-wechseln-schnelleres-sichereres-internet/", regel: "A", grund: "Dublette mit Zähler „(1)“: identischer Titel, gleiche Suchabsicht – Regel A"}
  - {von: "/posts/dns-server-wechseln-schnelleres-sichereres-internet/", nach: "/posts/2026-08-26-dns-server-wechseln-schnelleres-sichereres-internet/", regel: "A", grund: "Alt-URL ohne Datumspräfix: Ordner nach Datumsystem umbenannt – Regel A"}
  - {von: "/posts/dsl-anbieter-wechseln-warum-treue-dich-bares-geld-kostet(1)/", nach: "/posts/2026-10-07-dsl-anbieter-wechseln-warum-treue-dich-bares-geld-kostet/", regel: "A", grund: "Dublette mit Zähler „(1)“: identischer Titel, gleiche Suchabsicht – Regel A"}
  - {von: "/posts/dsl-anbieter-wechseln-warum-treue-dich-bares-geld-kostet/", nach: "/posts/2026-10-07-dsl-anbieter-wechseln-warum-treue-dich-bares-geld-kostet/", regel: "A", grund: "Alt-URL ohne Datumspräfix: Ordner nach Datumsystem umbenannt – Regel A"}
  - {von: "/posts/dsl-vergleich-so-findest-du-guenstigeres-internet(1)/", nach: "/posts/2026-08-19-dsl-vergleich-so-findest-du-guenstigeres-internet/", regel: "A", grund: "Dublette mit Zähler „(1)“: identischer Titel, gleiche Suchabsicht – Regel A"}
  - {von: "/posts/dsl-vergleich-so-findest-du-guenstigeres-internet/", nach: "/posts/2026-08-19-dsl-vergleich-so-findest-du-guenstigeres-internet/", regel: "A", grund: "Alt-URL ohne Datumspräfix: Ordner nach Datumsystem umbenannt – Regel A"}
  - {von: "/posts/dsl-wechselbonus-sichern(1)/", nach: "/posts/2026-08-10-dsl-wechselbonus-sichern/", regel: "A", grund: "Dublette mit Zähler „(1)“: identischer Titel, gleiche Suchabsicht – Regel A"}
  - {von: "/posts/dsl-wechselbonus-sichern/", nach: "/posts/2026-08-10-dsl-wechselbonus-sichern/", regel: "A", grund: "Alt-URL ohne Datumspräfix: Ordner nach Datumsystem umbenannt – Regel A"}
  - {von: "/posts/einlagensicherung-wie-viel-guthaben-geschuetzt-ist(1)/", nach: "/posts/2026-09-23-einlagensicherung-wie-viel-guthaben-geschuetzt-ist/", regel: "A", grund: "Dublette mit Zähler „(1)“: identischer Titel, gleiche Suchabsicht – Regel A"}
  - {von: "/posts/einlagensicherung-wie-viel-guthaben-geschuetzt-ist/", nach: "/posts/2026-09-23-einlagensicherung-wie-viel-guthaben-geschuetzt-ist/", regel: "A", grund: "Alt-URL ohne Datumspräfix: Ordner nach Datumsystem umbenannt – Regel A"}
  - {von: "/posts/energiediebe-stoppen-so-kannst-du-stromfresser-finden(1)/", nach: "/posts/2026-08-19-energiediebe-stoppen-so-kannst-du-stromfresser-finden/", regel: "A", grund: "Dublette mit Zähler „(1)“: identischer Titel, gleiche Suchabsicht – Regel A"}
  - {von: "/posts/energiediebe-stoppen-so-kannst-du-stromfresser-finden/", nach: "/posts/2026-08-19-energiediebe-stoppen-so-kannst-du-stromfresser-finden/", regel: "A", grund: "Alt-URL ohne Datumspräfix: Ordner nach Datumsystem umbenannt – Regel A"}
  - {von: "/posts/energieeffizienz-im-haushalt-5-schnelle-spartricks(1)/", nach: "/posts/2026-10-24-energieeffizienz-im-haushalt-5-schnelle-spartricks/", regel: "A", grund: "Dublette mit Zähler „(1)“: identischer Titel, gleiche Suchabsicht – Regel A"}
  - {von: "/posts/energieeffizienz-im-haushalt-5-schnelle-spartricks/", nach: "/posts/2026-10-24-energieeffizienz-im-haushalt-5-schnelle-spartricks/", regel: "A", grund: "Alt-URL ohne Datumspräfix: Ordner nach Datumsystem umbenannt – Regel A"}
  - {von: "/posts/energiekosten-senken-smarte-helfer-fuer-den-haushalt(1)/", nach: "/posts/2026-10-09-energiekosten-senken-smarte-helfer-fuer-den-haushalt/", regel: "A", grund: "Dublette mit Zähler „(1)“: identischer Titel, gleiche Suchabsicht – Regel A"}
  - {von: "/posts/energiekosten-senken-smarte-helfer-fuer-den-haushalt/", nach: "/posts/2026-10-09-energiekosten-senken-smarte-helfer-fuer-den-haushalt/", regel: "A", grund: "Alt-URL ohne Datumspräfix: Ordner nach Datumsystem umbenannt – Regel A"}
  - {von: "/posts/erster-eigener-haushalt-fixkosten-richtig-ordnen(1)/", nach: "/posts/2026-10-05-erster-eigener-haushalt-fixkosten-richtig-ordnen/", regel: "A", grund: "Dublette mit Zähler „(1)“: identischer Titel, gleiche Suchabsicht – Regel A"}
  - {von: "/posts/erster-eigener-haushalt-fixkosten-richtig-ordnen/", nach: "/posts/2026-10-05-erster-eigener-haushalt-fixkosten-richtig-ordnen/", regel: "A", grund: "Alt-URL ohne Datumspräfix: Ordner nach Datumsystem umbenannt – Regel A"}
  - {von: "/posts/finanzielle-freiheit-erreichen-denke-dich-reich(1)/", nach: "/posts/2026-09-04-finanzielle-freiheit-erreichen-denke-dich-reich/", regel: "A", grund: "Dublette mit Zähler „(1)“: identischer Titel, gleiche Suchabsicht – Regel A"}
  - {von: "/posts/finanzielle-freiheit-erreichen-denke-dich-reich/", nach: "/posts/2026-09-04-finanzielle-freiheit-erreichen-denke-dich-reich/", regel: "A", grund: "Alt-URL ohne Datumspräfix: Ordner nach Datumsystem umbenannt – Regel A"}
  - {von: "/posts/finanzieller-puffer-wie-viel-notgroschen-ist-genug(1)/", nach: "/posts/2026-09-20-finanzieller-puffer-wie-viel-notgroschen-ist-genug/", regel: "A", grund: "Dublette mit Zähler „(1)“: identischer Titel, gleiche Suchabsicht – Regel A"}
  - {von: "/posts/finanzieller-puffer-wie-viel-notgroschen-ist-genug/", nach: "/posts/2026-09-20-finanzieller-puffer-wie-viel-notgroschen-ist-genug/", regel: "A", grund: "Alt-URL ohne Datumspräfix: Ordner nach Datumsystem umbenannt – Regel A"}
  - {von: "/posts/frugalismus-tipps-mehr-freiheit-durch-bewussten-konsum(1)/", nach: "/posts/2026-09-07-frugalismus-tipps-mehr-freiheit-durch-bewussten-konsum/", regel: "A", grund: "Dublette mit Zähler „(1)“: identischer Titel, gleiche Suchabsicht – Regel A"}
  - {von: "/posts/frugalismus-tipps-mehr-freiheit-durch-bewussten-konsum/", nach: "/posts/2026-09-07-frugalismus-tipps-mehr-freiheit-durch-bewussten-konsum/", regel: "A", grund: "Alt-URL ohne Datumspräfix: Ordner nach Datumsystem umbenannt – Regel A"}
  - {von: "/posts/frugalismus-tipps-so-vermeidest-du-teure-alltagsfehler(1)/", nach: "/posts/2026-09-07-frugalismus-tipps-so-vermeidest-du-teure-alltagsfehler/", regel: "A", grund: "Dublette mit Zähler „(1)“: identischer Titel, gleiche Suchabsicht – Regel A"}
  - {von: "/posts/frugalismus-tipps-so-vermeidest-du-teure-alltagsfehler/", nach: "/posts/2026-09-07-frugalismus-tipps-so-vermeidest-du-teure-alltagsfehler/", regel: "A", grund: "Alt-URL ohne Datumspräfix: Ordner nach Datumsystem umbenannt – Regel A"}
  - {von: "/posts/gasabschlag-berechnen-so-planst-du-die-heizsaison-richtig(1)/", nach: "/posts/2026-10-02-gasabschlag-berechnen-so-planst-du-die-heizsaison-richtig/", regel: "A", grund: "Dublette mit Zähler „(1)“: identischer Titel, gleiche Suchabsicht – Regel A"}
  - {von: "/posts/gasabschlag-berechnen-so-planst-du-die-heizsaison-richtig/", nach: "/posts/2026-10-02-gasabschlag-berechnen-so-planst-du-die-heizsaison-richtig/", regel: "A", grund: "Alt-URL ohne Datumspräfix: Ordner nach Datumsystem umbenannt – Regel A"}
  - {von: "/posts/gasrechnung-senken-fehler-im-spaetsommer-vermeiden(1)/", nach: "/posts/2026-08-14-gasrechnung-senken-fehler-im-spaetsommer-vermeiden/", regel: "A", grund: "Dublette mit Zähler „(1)“: identischer Titel, gleiche Suchabsicht – Regel A"}
  - {von: "/posts/gasrechnung-senken-fehler-im-spaetsommer-vermeiden/", nach: "/posts/2026-08-14-gasrechnung-senken-fehler-im-spaetsommer-vermeiden/", regel: "A", grund: "Alt-URL ohne Datumspräfix: Ordner nach Datumsystem umbenannt – Regel A"}
  - {von: "/posts/gasrechnung-senken-so-bereitest-du-dich-im-spaetsommer-vor(1)/", nach: "/posts/2026-09-20-gasrechnung-senken-so-bereitest-du-dich-im-spaetsommer-vor/", regel: "A", grund: "Dublette mit Zähler „(1)“: identischer Titel, gleiche Suchabsicht – Regel A"}
  - {von: "/posts/gasrechnung-senken-so-bereitest-du-dich-im-spaetsommer-vor/", nach: "/posts/2026-09-20-gasrechnung-senken-so-bereitest-du-dich-im-spaetsommer-vor/", regel: "A", grund: "Alt-URL ohne Datumspräfix: Ordner nach Datumsystem umbenannt – Regel A"}
  - {von: "/posts/gasrechnung-senken-spaetsommer-check-spart-hunderte-euro(1)/", nach: "/posts/2026-09-20-gasrechnung-senken-spaetsommer-check-spart-hunderte-euro/", regel: "A", grund: "Dublette mit Zähler „(1)“: identischer Titel, gleiche Suchabsicht – Regel A"}
  - {von: "/posts/gasrechnung-senken-spaetsommer-check-spart-hunderte-euro/", nach: "/posts/2026-09-20-gasrechnung-senken-spaetsommer-check-spart-hunderte-euro/", regel: "A", grund: "Alt-URL ohne Datumspräfix: Ordner nach Datumsystem umbenannt – Regel A"}
  - {von: "/posts/geld-abheben-im-ausland-gebuehren-vermeiden(1)/", nach: "/posts/2026-08-12-geld-abheben-im-ausland-gebuehren-vermeiden/", regel: "A", grund: "Dublette mit Zähler „(1)“: identischer Titel, gleiche Suchabsicht – Regel A"}
  - {von: "/posts/geld-abheben-im-ausland-gebuehren-vermeiden/", nach: "/posts/2026-08-12-geld-abheben-im-ausland-gebuehren-vermeiden/", regel: "A", grund: "Alt-URL ohne Datumspräfix: Ordner nach Datumsystem umbenannt – Regel A"}
  - {von: "/posts/grosseinkauf-und-vorrat-wann-bevorraten-sich-rechnet(1)/", nach: "/posts/2026-09-30-grosseinkauf-und-vorrat-wann-bevorraten-sich-rechnet/", regel: "A", grund: "Dublette mit Zähler „(1)“: identischer Titel, gleiche Suchabsicht – Regel A"}
  - {von: "/posts/grosseinkauf-und-vorrat-wann-bevorraten-sich-rechnet/", nach: "/posts/2026-09-30-grosseinkauf-und-vorrat-wann-bevorraten-sich-rechnet/", regel: "A", grund: "Alt-URL ohne Datumspräfix: Ordner nach Datumsystem umbenannt – Regel A"}
  - {von: "/posts/grundversorgung-strom-und-gas-was-sie-leistet(1)/", nach: "/posts/2026-09-21-grundversorgung-strom-und-gas-was-sie-leistet/", regel: "A", grund: "Dublette mit Zähler „(1)“: identischer Titel, gleiche Suchabsicht – Regel A"}
  - {von: "/posts/grundversorgung-strom-und-gas-was-sie-leistet/", nach: "/posts/2026-09-21-grundversorgung-strom-und-gas-was-sie-leistet/", regel: "A", grund: "Alt-URL ohne Datumspräfix: Ordner nach Datumsystem umbenannt – Regel A"}
  - {von: "/posts/guenstig-durch-den-winter-heizungs-check-im-spaetsommer(1)/", nach: "/posts/2026-09-11-guenstig-durch-den-winter-heizungs-check-im-spaetsommer/", regel: "A", grund: "Dublette mit Zähler „(1)“: identischer Titel, gleiche Suchabsicht – Regel A"}
  - {von: "/posts/guenstig-durch-den-winter-heizungs-check-im-spaetsommer/", nach: "/posts/2026-09-11-guenstig-durch-den-winter-heizungs-check-im-spaetsommer/", regel: "A", grund: "Alt-URL ohne Datumspräfix: Ordner nach Datumsystem umbenannt – Regel A"}
  - {von: "/posts/handytarif-vergleichen-2026-guenstige-tarife(1)/", nach: "/posts/2026-08-26-handytarif-vergleichen-2026-guenstige-tarife/", regel: "A", grund: "Dublette mit Zähler „(1)“: identischer Titel, gleiche Suchabsicht – Regel A"}
  - {von: "/posts/handytarif-vergleichen-2026-guenstige-tarife/", nach: "/posts/2026-08-26-handytarif-vergleichen-2026-guenstige-tarife/", regel: "A", grund: "Alt-URL ohne Datumspräfix: Ordner nach Datumsystem umbenannt – Regel A"}
  - {von: "/posts/handyvertrag-kuendigen-raus-aus-der-kostenfalle-verlaengerung(1)/", nach: "/posts/2026-10-07-handyvertrag-kuendigen-raus-aus-der-kostenfalle-verlaengerung/", regel: "A", grund: "Dublette mit Zähler „(1)“: identischer Titel, gleiche Suchabsicht – Regel A"}
  - {von: "/posts/handyvertrag-kuendigen-raus-aus-der-kostenfalle-verlaengerung/", nach: "/posts/2026-10-07-handyvertrag-kuendigen-raus-aus-der-kostenfalle-verlaengerung/", regel: "A", grund: "Alt-URL ohne Datumspräfix: Ordner nach Datumsystem umbenannt – Regel A"}
  - {von: "/posts/haushaltsbuch-fuehren-app-excel-oder-papier(1)/", nach: "/posts/2026-08-21-haushaltsbuch-fuehren-app-excel-oder-papier/", regel: "A", grund: "Dublette mit Zähler „(1)“: identischer Titel, gleiche Suchabsicht – Regel A"}
  - {von: "/posts/haushaltsbuch-fuehren-app-excel-oder-papier/", nach: "/posts/2026-08-21-haushaltsbuch-fuehren-app-excel-oder-papier/", regel: "A", grund: "Alt-URL ohne Datumspräfix: Ordner nach Datumsystem umbenannt – Regel A"}
  - {von: "/posts/haushaltskosten-reduzieren-so-gewinnst-du-die-kontrolle(1)/", nach: "/posts/2026-10-12-haushaltskosten-reduzieren-so-gewinnst-du-die-kontrolle/", regel: "A", grund: "Dublette mit Zähler „(1)“: identischer Titel, gleiche Suchabsicht – Regel A"}
  - {von: "/posts/haushaltskosten-reduzieren-so-gewinnst-du-die-kontrolle/", nach: "/posts/2026-10-12-haushaltskosten-reduzieren-so-gewinnst-du-die-kontrolle/", regel: "A", grund: "Alt-URL ohne Datumspräfix: Ordner nach Datumsystem umbenannt – Regel A"}
  - {von: "/posts/heizkosten-senken-mit-diesen-strategien-sparst-du-sofort(1)/", nach: "/posts/2026-09-07-heizkosten-senken-mit-diesen-strategien-sparst-du-sofort/", regel: "A", grund: "Dublette mit Zähler „(1)“: identischer Titel, gleiche Suchabsicht – Regel A"}
  - {von: "/posts/heizkosten-senken-mit-diesen-strategien-sparst-du-sofort/", nach: "/posts/2026-09-07-heizkosten-senken-mit-diesen-strategien-sparst-du-sofort/", regel: "A", grund: "Alt-URL ohne Datumspräfix: Ordner nach Datumsystem umbenannt – Regel A"}
  - {von: "/posts/internet-dsl-update-was-sich-jetzt-fuer-dich-aendert(1)/", nach: "/posts/2026-09-24-internet-dsl-update-was-sich-jetzt-fuer-dich-aendert/", regel: "A", grund: "Dublette mit Zähler „(1)“: identischer Titel, gleiche Suchabsicht – Regel A"}
  - {von: "/posts/internet-dsl-update-was-sich-jetzt-fuer-dich-aendert/", nach: "/posts/2026-09-24-internet-dsl-update-was-sich-jetzt-fuer-dich-aendert/", regel: "A", grund: "Alt-URL ohne Datumspräfix: Ordner nach Datumsystem umbenannt – Regel A"}
  - {von: "/posts/internet-dsl-wechseln-praxis-tipps-fuer-den-anbieterwechsel(1)/", nach: "/posts/2026-08-14-internet-dsl-wechseln-praxis-tipps-fuer-den-anbieterwechsel/", regel: "A", grund: "Dublette mit Zähler „(1)“: identischer Titel, gleiche Suchabsicht – Regel A"}
  - {von: "/posts/internet-dsl-wechseln-praxis-tipps-fuer-den-anbieterwechsel/", nach: "/posts/2026-08-14-internet-dsl-wechseln-praxis-tipps-fuer-den-anbieterwechsel/", regel: "A", grund: "Alt-URL ohne Datumspräfix: Ordner nach Datumsystem umbenannt – Regel A"}
  - {von: "/posts/kleine-energiespar-tricks-die-deine-kosten-sofort-senken(1)/", nach: "/posts/2026-10-12-kleine-energiespar-tricks-die-deine-kosten-sofort-senken/", regel: "A", grund: "Dublette mit Zähler „(1)“: identischer Titel, gleiche Suchabsicht – Regel A"}
  - {von: "/posts/kleine-energiespar-tricks-die-deine-kosten-sofort-senken/", nach: "/posts/2026-10-12-kleine-energiespar-tricks-die-deine-kosten-sofort-senken/", regel: "A", grund: "Alt-URL ohne Datumspräfix: Ordner nach Datumsystem umbenannt – Regel A"}
  - {von: "/posts/kostenloses-girokonto-so-findest-du-ein-konto-ohne-gebuehren(1)/", nach: "/posts/2026-08-17-kostenloses-girokonto-so-findest-du-ein-konto-ohne-gebuehren/", regel: "A", grund: "Dublette mit Zähler „(1)“: identischer Titel, gleiche Suchabsicht – Regel A"}
  - {von: "/posts/kostenloses-girokonto-so-findest-du-ein-konto-ohne-gebuehren/", nach: "/posts/2026-08-17-kostenloses-girokonto-so-findest-du-ein-konto-ohne-gebuehren/", regel: "A", grund: "Alt-URL ohne Datumspräfix: Ordner nach Datumsystem umbenannt – Regel A"}
  - {von: "/posts/kreditkarte-vergleichen-kostenlos-sicher-bezahlen(1)/", nach: "/posts/2026-09-03-kreditkarte-vergleichen-kostenlos-sicher-bezahlen/", regel: "A", grund: "Dublette mit Zähler „(1)“: identischer Titel, gleiche Suchabsicht – Regel A"}
  - {von: "/posts/kreditkarte-vergleichen-kostenlos-sicher-bezahlen/", nach: "/posts/2026-09-03-kreditkarte-vergleichen-kostenlos-sicher-bezahlen/", regel: "A", grund: "Alt-URL ohne Datumspräfix: Ordner nach Datumsystem umbenannt – Regel A"}
  - {von: "/posts/last-minute-urlaub-so-schnappst-du-dir-das-sommer-schnaepp(1)/", nach: "/posts/2026-09-30-last-minute-urlaub-so-schnappst-du-dir-das-sommer-schnaepp/", regel: "A", grund: "Dublette mit Zähler „(1)“: identischer Titel, gleiche Suchabsicht – Regel A"}
  - {von: "/posts/last-minute-urlaub-so-schnappst-du-dir-das-sommer-schnaepp/", nach: "/posts/2026-09-30-last-minute-urlaub-so-schnappst-du-dir-das-sommer-schnaepp/", regel: "A", grund: "Alt-URL ohne Datumspräfix: Ordner nach Datumsystem umbenannt – Regel A"}
  - {von: "/posts/lastschrift-und-dauerauftrag-abbuchungen-pruefen(1)/", nach: "/posts/2026-08-28-lastschrift-und-dauerauftrag-abbuchungen-pruefen/", regel: "A", grund: "Dublette mit Zähler „(1)“: identischer Titel, gleiche Suchabsicht – Regel A"}
  - {von: "/posts/lastschrift-und-dauerauftrag-abbuchungen-pruefen/", nach: "/posts/2026-08-28-lastschrift-und-dauerauftrag-abbuchungen-pruefen/", regel: "A", grund: "Alt-URL ohne Datumspräfix: Ordner nach Datumsystem umbenannt – Regel A"}
  - {von: "/posts/mehr-freiheit-durch-verzicht-clevere-frugalismus-tipps(1)/", nach: "/posts/2026-08-24-mehr-freiheit-durch-verzicht-clevere-frugalismus-tipps/", regel: "A", grund: "Dublette mit Zähler „(1)“: identischer Titel, gleiche Suchabsicht – Regel A"}
  - {von: "/posts/mehr-freiheit-durch-verzicht-clevere-frugalismus-tipps/", nach: "/posts/2026-08-24-mehr-freiheit-durch-verzicht-clevere-frugalismus-tipps/", regel: "A", grund: "Alt-URL ohne Datumspräfix: Ordner nach Datumsystem umbenannt – Regel A"}
  - {von: "/posts/mietwagen-buchen-ohne-kaution-fallen-urlaub(1)/", nach: "/posts/2026-08-21-mietwagen-buchen-ohne-kaution-fallen-urlaub/", regel: "A", grund: "Dublette mit Zähler „(1)“: identischer Titel, gleiche Suchabsicht – Regel A"}
  - {von: "/posts/mietwagen-buchen-ohne-kaution-fallen-urlaub/", nach: "/posts/2026-08-21-mietwagen-buchen-ohne-kaution-fallen-urlaub/", regel: "A", grund: "Alt-URL ohne Datumspräfix: Ordner nach Datumsystem umbenannt – Regel A"}
  - {von: "/posts/nachtstrom-tarife-wann-sich-ein-doppeltarifzaehler-noch-lohnt(1)/", nach: "/posts/2026-08-31-nachtstrom-tarife-wann-sich-ein-doppeltarifzaehler-noch-lohnt/", regel: "A", grund: "Dublette mit Zähler „(1)“: identischer Titel, gleiche Suchabsicht – Regel A"}
  - {von: "/posts/nachtstrom-tarife-wann-sich-ein-doppeltarifzaehler-noch-lohnt/", nach: "/posts/2026-08-31-nachtstrom-tarife-wann-sich-ein-doppeltarifzaehler-noch-lohnt/", regel: "A", grund: "Alt-URL ohne Datumspräfix: Ordner nach Datumsystem umbenannt – Regel A"}
  - {von: "/posts/notgroschen-die-wahrheit-ueber-das-finanzielle-polster(1)/", nach: "/posts/2026-09-09-notgroschen-die-wahrheit-ueber-das-finanzielle-polster/", regel: "A", grund: "Dublette mit Zähler „(1)“: identischer Titel, gleiche Suchabsicht – Regel A"}
  - {von: "/posts/notgroschen-die-wahrheit-ueber-das-finanzielle-polster/", nach: "/posts/2026-09-09-notgroschen-die-wahrheit-ueber-das-finanzielle-polster/", regel: "A", grund: "Alt-URL ohne Datumspräfix: Ordner nach Datumsystem umbenannt – Regel A"}
  - {von: "/posts/preisgarantie-gas-so-schuetzt-du-dich-vor-preisspruengen(1)/", nach: "/posts/2026-08-24-preisgarantie-gas-so-schuetzt-du-dich-vor-preisspruengen/", regel: "A", grund: "Dublette mit Zähler „(1)“: identischer Titel, gleiche Suchabsicht – Regel A"}
  - {von: "/posts/preisgarantie-gas-so-schuetzt-du-dich-vor-preisspruengen/", nach: "/posts/2026-08-24-preisgarantie-gas-so-schuetzt-du-dich-vor-preisspruengen/", regel: "A", grund: "Alt-URL ohne Datumspräfix: Ordner nach Datumsystem umbenannt – Regel A"}
  - {von: "/posts/preisgarantie-gas-so-sicherst-du-dir-guenstige-tarife-fuer-2026(1)/", nach: "/posts/2026-08-12-preisgarantie-gas-so-sicherst-du-dir-guenstige-tarife-fuer-2026/", regel: "A", grund: "Dublette mit Zähler „(1)“: identischer Titel, gleiche Suchabsicht – Regel A"}
  - {von: "/posts/preisgarantie-gas-so-sicherst-du-dir-guenstige-tarife-fuer-2026/", nach: "/posts/2026-08-12-preisgarantie-gas-so-sicherst-du-dir-guenstige-tarife-fuer-2026/", regel: "A", grund: "Alt-URL ohne Datumspräfix: Ordner nach Datumsystem umbenannt – Regel A"}
  - {von: "/posts/preiswert-surfen-so-findest-du-den-optimalen-dsl-anschluss(1)/", nach: "/posts/2026-10-02-preiswert-surfen-so-findest-du-den-optimalen-dsl-anschluss/", regel: "A", grund: "Dublette mit Zähler „(1)“: identischer Titel, gleiche Suchabsicht – Regel A"}
  - {von: "/posts/preiswert-surfen-so-findest-du-den-optimalen-dsl-anschluss/", nach: "/posts/2026-10-02-preiswert-surfen-so-findest-du-den-optimalen-dsl-anschluss/", regel: "A", grund: "Alt-URL ohne Datumspräfix: Ordner nach Datumsystem umbenannt – Regel A"}
  - {von: "/posts/september-roadtrip-clevere-wege-zum-mietwagen-schnaeppchen(1)/", nach: "/posts/2026-09-02-september-roadtrip-clevere-wege-zum-mietwagen-schnaeppchen/", regel: "A", grund: "Dublette mit Zähler „(1)“: identischer Titel, gleiche Suchabsicht – Regel A"}
  - {von: "/posts/september-roadtrip-clevere-wege-zum-mietwagen-schnaeppchen/", nach: "/posts/2026-09-02-september-roadtrip-clevere-wege-zum-mietwagen-schnaeppchen/", regel: "A", grund: "Alt-URL ohne Datumspräfix: Ordner nach Datumsystem umbenannt – Regel A"}
  - {von: "/posts/sicher-heizen-so-schuetzt-dich-eine-preisgarantie-gas(1)/", nach: "/posts/2026-08-10-sicher-heizen-so-schuetzt-dich-eine-preisgarantie-gas/", regel: "A", grund: "Dublette mit Zähler „(1)“: identischer Titel, gleiche Suchabsicht – Regel A"}
  - {von: "/posts/sicher-heizen-so-schuetzt-dich-eine-preisgarantie-gas/", nach: "/posts/2026-08-10-sicher-heizen-so-schuetzt-dich-eine-preisgarantie-gas/", regel: "A", grund: "Alt-URL ohne Datumspräfix: Ordner nach Datumsystem umbenannt – Regel A"}
  - {von: "/posts/so-findest-du-den-richtigen-dsl-tarif-fuer-dein-zuhause(1)/", nach: "/posts/2026-08-20-so-findest-du-den-richtigen-dsl-tarif-fuer-dein-zuhause/", regel: "A", grund: "Dublette mit Zähler „(1)“: identischer Titel, gleiche Suchabsicht – Regel A"}
  - {von: "/posts/so-findest-du-den-richtigen-dsl-tarif-fuer-dein-zuhause/", nach: "/posts/2026-08-20-so-findest-du-den-richtigen-dsl-tarif-fuer-dein-zuhause/", regel: "A", grund: "Alt-URL ohne Datumspräfix: Ordner nach Datumsystem umbenannt – Regel A"}
  - {von: "/posts/sparen-im-herbst-die-besten-spartipps-fuer-die-goldene-jahreszeit(1)/", nach: "/posts/2026-08-14-sparen-im-herbst-die-besten-spartipps-fuer-die-goldene-jahreszeit/", regel: "A", grund: "Dublette mit Zähler „(1)“: identischer Titel, gleiche Suchabsicht – Regel A"}
  - {von: "/posts/sparen-im-herbst-die-besten-spartipps-fuer-die-goldene-jahreszeit/", nach: "/posts/2026-08-14-sparen-im-herbst-die-besten-spartipps-fuer-die-goldene-jahreszeit/", regel: "A", grund: "Alt-URL ohne Datumspräfix: Ordner nach Datumsystem umbenannt – Regel A"}
  - {von: "/posts/standby-kosten-reduzieren-so-entlarvst-du-stromfresser(1)/", nach: "/posts/2026-09-11-standby-kosten-reduzieren-so-entlarvst-du-stromfresser/", regel: "A", grund: "Dublette mit Zähler „(1)“: identischer Titel, gleiche Suchabsicht – Regel A"}
  - {von: "/posts/standby-kosten-reduzieren-so-entlarvst-du-stromfresser/", nach: "/posts/2026-09-11-standby-kosten-reduzieren-so-entlarvst-du-stromfresser/", regel: "A", grund: "Alt-URL ohne Datumspräfix: Ordner nach Datumsystem umbenannt – Regel A"}
  - {von: "/posts/stoerung-beim-internetanbieter-so-sicherst-du-deine-rechte(1)/", nach: "/posts/2026-08-31-stoerung-beim-internetanbieter-so-sicherst-du-deine-rechte/", regel: "A", grund: "Dublette mit Zähler „(1)“: identischer Titel, gleiche Suchabsicht – Regel A"}
  - {von: "/posts/stoerung-beim-internetanbieter-so-sicherst-du-deine-rechte/", nach: "/posts/2026-08-31-stoerung-beim-internetanbieter-so-sicherst-du-deine-rechte/", regel: "A", grund: "Alt-URL ohne Datumspräfix: Ordner nach Datumsystem umbenannt – Regel A"}
  - {von: "/posts/stromkosten-senken-clevere-haushaltsgeraete-im-ueberblick(1)/", nach: "/posts/2026-10-23-stromkosten-senken-clevere-haushaltsgeraete-im-ueberblick/", regel: "A", grund: "Dublette mit Zähler „(1)“: identischer Titel, gleiche Suchabsicht – Regel A"}
  - {von: "/posts/stromkosten-senken-clevere-haushaltsgeraete-im-ueberblick/", nach: "/posts/2026-10-23-stromkosten-senken-clevere-haushaltsgeraete-im-ueberblick/", regel: "A", grund: "Alt-URL ohne Datumspräfix: Ordner nach Datumsystem umbenannt – Regel A"}
  - {von: "/posts/tagesgeld-zinsen-2026-die-besten-zinssaetze-im-vergleich(1)/", nach: "/posts/2026-08-26-tagesgeld-zinsen-2026-die-besten-zinssaetze-im-vergleich/", regel: "A", grund: "Dublette mit Zähler „(1)“: identischer Titel, gleiche Suchabsicht – Regel A"}
  - {von: "/posts/tagesgeld-zinsen-2026-die-besten-zinssaetze-im-vergleich/", nach: "/posts/2026-08-26-tagesgeld-zinsen-2026-die-besten-zinssaetze-im-vergleich/", regel: "A", grund: "Alt-URL ohne Datumspräfix: Ordner nach Datumsystem umbenannt – Regel A"}
  - {von: "/posts/umzug-mit-internet-anschluss-und-rufnummer-mitnehmen(1)/", nach: "/posts/2026-09-04-umzug-mit-internet-anschluss-und-rufnummer-mitnehmen/", regel: "A", grund: "Dublette mit Zähler „(1)“: identischer Titel, gleiche Suchabsicht – Regel A"}
  - {von: "/posts/umzug-mit-internet-anschluss-und-rufnummer-mitnehmen/", nach: "/posts/2026-09-04-umzug-mit-internet-anschluss-und-rufnummer-mitnehmen/", regel: "A", grund: "Alt-URL ohne Datumspräfix: Ordner nach Datumsystem umbenannt – Regel A"}
  - {von: "/posts/urlaub-sparen-7-clevere-wege-deine-kasse-zu-fuellen(1)/", nach: "/posts/2026-10-07-urlaub-sparen-7-clevere-wege-deine-kasse-zu-fuellen/", regel: "A", grund: "Dublette mit Zähler „(1)“: identischer Titel, gleiche Suchabsicht – Regel A"}
  - {von: "/posts/urlaub-sparen-7-clevere-wege-deine-kasse-zu-fuellen/", nach: "/posts/2026-10-07-urlaub-sparen-7-clevere-wege-deine-kasse-zu-fuellen/", regel: "A", grund: "Alt-URL ohne Datumspräfix: Ordner nach Datumsystem umbenannt – Regel A"}
  - {von: "/posts/vpn-zuhause-schutzschild-oder-unnoetige-fixkosten-falle(1)/", nach: "/posts/2026-10-09-vpn-zuhause-schutzschild-oder-unnoetige-fixkosten-falle/", regel: "A", grund: "Dublette mit Zähler „(1)“: identischer Titel, gleiche Suchabsicht – Regel A"}
  - {von: "/posts/vpn-zuhause-schutzschild-oder-unnoetige-fixkosten-falle/", nach: "/posts/2026-10-09-vpn-zuhause-schutzschild-oder-unnoetige-fixkosten-falle/", regel: "A", grund: "Alt-URL ohne Datumspräfix: Ordner nach Datumsystem umbenannt – Regel A"}
  - {von: "/posts/waermepumpe-vs-gasheizung-2026-so-entscheidest-du-richtig(1)/", nach: "/posts/2026-10-12-waermepumpe-vs-gasheizung-2026-so-entscheidest-du-richtig/", regel: "A", grund: "Dublette mit Zähler „(1)“: identischer Titel, gleiche Suchabsicht – Regel A"}
  - {von: "/posts/waermepumpe-vs-gasheizung-2026-so-entscheidest-du-richtig/", nach: "/posts/2026-10-12-waermepumpe-vs-gasheizung-2026-so-entscheidest-du-richtig/", regel: "A", grund: "Alt-URL ohne Datumspräfix: Ordner nach Datumsystem umbenannt – Regel A"}
  - {von: "/posts/warmwasser-sparen-rechnung-hinter-dem-hahn(1)/", nach: "/posts/2026-08-26-warmwasser-sparen-rechnung-hinter-dem-hahn/", regel: "A", grund: "Dublette mit Zähler „(1)“: identischer Titel, gleiche Suchabsicht – Regel A"}
  - {von: "/posts/warmwasser-sparen-rechnung-hinter-dem-hahn/", nach: "/posts/2026-08-26-warmwasser-sparen-rechnung-hinter-dem-hahn/", regel: "A", grund: "Alt-URL ohne Datumspräfix: Ordner nach Datumsystem umbenannt – Regel A"}
  - {von: "/posts/weihnachten-budget-planen-ohne-schulden-durch-die-feiertage(1)/", nach: "/posts/2026-10-02-weihnachten-budget-planen-ohne-schulden-durch-die-feiertage/", regel: "A", grund: "Dublette mit Zähler „(1)“: identischer Titel, gleiche Suchabsicht – Regel A"}
  - {von: "/posts/weihnachten-budget-planen-ohne-schulden-durch-die-feiertage/", nach: "/posts/2026-10-02-weihnachten-budget-planen-ohne-schulden-durch-die-feiertage/", regel: "A", grund: "Alt-URL ohne Datumspräfix: Ordner nach Datumsystem umbenannt – Regel A"}
  - {von: "/posts/wie-smart-home-geraete-deine-stromrechnung-wirklich-druecken(1)/", nach: "/posts/2026-10-07-wie-smart-home-geraete-deine-stromrechnung-wirklich-druecken/", regel: "A", grund: "Dublette mit Zähler „(1)“: identischer Titel, gleiche Suchabsicht – Regel A"}
  - {von: "/posts/wie-smart-home-geraete-deine-stromrechnung-wirklich-druecken/", nach: "/posts/2026-10-07-wie-smart-home-geraete-deine-stromrechnung-wirklich-druecken/", regel: "A", grund: "Alt-URL ohne Datumspräfix: Ordner nach Datumsystem umbenannt – Regel A"}
  - {von: "/posts/wlan-verbessern-so-bringst-du-speed-in-jede-ecke(1)/", nach: "/posts/2026-08-14-wlan-verbessern-so-bringst-du-speed-in-jede-ecke/", regel: "A", grund: "Dublette mit Zähler „(1)“: identischer Titel, gleiche Suchabsicht – Regel A"}
  - {von: "/posts/wlan-verbessern-so-bringst-du-speed-in-jede-ecke/", nach: "/posts/2026-08-14-wlan-verbessern-so-bringst-du-speed-in-jede-ecke/", regel: "A", grund: "Alt-URL ohne Datumspräfix: Ordner nach Datumsystem umbenannt – Regel A"}
  - {von: "/posts/wlan-verstaerker-vs-mesh-wlan-was-brauchst-du-wirklich(1)/", nach: "/posts/2026-09-27-wlan-verstaerker-vs-mesh-wlan-was-brauchst-du-wirklich/", regel: "A", grund: "Dublette mit Zähler „(1)“: identischer Titel, gleiche Suchabsicht – Regel A"}
  - {von: "/posts/wlan-verstaerker-vs-mesh-wlan-was-brauchst-du-wirklich/", nach: "/posts/2026-09-27-wlan-verstaerker-vs-mesh-wlan-was-brauchst-du-wirklich/", regel: "A", grund: "Alt-URL ohne Datumspräfix: Ordner nach Datumsystem umbenannt – Regel A"}
  - {von: "/posts/zaehlerstand-ablesen-und-melden-schaetzwerte-vermeiden(1)/", nach: "/posts/2026-09-28-zaehlerstand-ablesen-und-melden-schaetzwerte-vermeiden/", regel: "A", grund: "Dublette mit Zähler „(1)“: identischer Titel, gleiche Suchabsicht – Regel A"}
  - {von: "/posts/zaehlerstand-ablesen-und-melden-schaetzwerte-vermeiden/", nach: "/posts/2026-09-28-zaehlerstand-ablesen-und-melden-schaetzwerte-vermeiden/", regel: "A", grund: "Alt-URL ohne Datumspräfix: Ordner nach Datumsystem umbenannt – Regel A"}
```

---

*Erzeugt am 27.10.2026 aus `data/gsc/abdeckung/kandidaten.json`,
`data/weiterleitungen.yaml`, `data/url_entfallen.yaml` und `content/`.
Wiederholbar: der Kandidatenraum entsteht mit
`python3 scripts/gsc_abdeckung.py --kandidaten`.*

---

## Anhang B · Pillar-Links nach der Promotion (erst dann anwenden)

**Vorbedingung:** alle vier Artikel sind ausgeliefert (`draft: false`, von
`cadence_guard` promotet). Vorher eintragen erzeugt sofort wieder vier tote
Linkziele (W11) – genau das wurde am 27.10.2026 bereinigt.

**Datei:** `content/pillar/versicherungen/index.md`, Abschnitt
`## Cluster-Reihenfolge` (heute: ein Absatz ohne Links).

```markdown
## Cluster-Reihenfolge

1. [Privathaftpflicht: Warum sie so wichtig ist und was sie kostet](../../posts/2026-08-17-privathaftpflicht-warum-sie-so-wichtig-ist-und-was-sie-kostet/)
2. [Wohngebäudeversicherung Vergleich: Worauf du achten musst](../../posts/2026-08-18-wohngebaeudeversicherung-vergleich-worauf-du-achten-musst/)
3. [Dein Haus sicher schützen: Das neue Vorsorge-Update 2026](../../posts/2026-08-12-dein-haus-sicher-schuetzen-das-neue-vorsorge-update-2026/)
4. [Kfz-Versicherung Vergleich 2026: Bis zu 800 € sparen](../../posts/2026-08-26-kfz-versicherung-vergleich-bis-zu-800-euro-sparen/)

Kfz hat den Kalender (30.11.). Haftpflicht hat keinen – und genau deshalb bleibt
sie jahrelang unangetastet, obwohl 20 € und drei Klauseln fehlen.
```

Optional die zwei Absätze wieder auf die Detailartikel zeigen lassen (sie
tragen die Aussagen ausführlicher):

- Abschnitt `## Privathaftpflicht …`, letzter Satz →
  „Warum dieser Schutz unverzichtbar ist … erfährst du im Ratgeber
  [Privathaftpflicht: Warum sie so wichtig ist und was sie kostet](../../posts/2026-08-17-privathaftpflicht-warum-sie-so-wichtig-ist-und-was-sie-kostet/)."
- Abschnitt `## Hausrat- und Wohngebäudeversicherung …`, letzter Satz →
  „Einen umfassenden Überblick … findest du im Beitrag
  [Dein Haus sicher schützen: Das neue Vorsorge-Update 2026](../../posts/2026-08-12-dein-haus-sicher-schuetzen-das-neue-vorsorge-update-2026/)."

**Danach prüfen (in dieser Reihenfolge):**

```bash
npm run gsc:abdeckung:gate                  # tote_ziele muss 0 bleiben
npm run test:versicherungs-cluster          # die Wiedervorlage wird grün
python3 scripts/link_density_guard.py       # Pillar bleibt ausgenommen, Artikel im Korridor
```
