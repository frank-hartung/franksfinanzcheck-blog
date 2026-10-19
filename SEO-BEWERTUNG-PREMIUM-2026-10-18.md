# SEO-Bewertung aus Profi-Sicht: Wie der Blog besser ranken kann

**Datum:** 18.10.2026 · **Auftrag:** „Bewerte meinen Blog als Profi-Webdesigner, um bestmögliches Ranking bei Google zu erhalten."
**Grundlage:** Quellcode und Inhalte dieses Repos (Stand `258fd51`), Live-Abruf von `franksfinanzcheck.de` über das Fetch-Werkzeug, Search-Console-Daten aus `data/gsc/` (Zeitraum 18.07.–15.10.2026).

> **Vorab:** Ein Ranking lässt sich nicht garantieren. Bewertet wird, was die Seite Google heute bietet und was ihr fehlt.

---

## 1. Kurzfazit

Die **technische Basis ist überdurchschnittlich gut**. Canonical, Sitemap, robots.txt, strukturierte Daten, Index-Hygiene und Ladeoptimierung sind sauber gelöst. Das Problem liegt woanders:

- **Die Seite ist kaum sichtbar.** In 26 Tagen gab es **51 Impressionen und 0 Klicks** über 92 Artikel.
- **Vertrauen und Autorität fehlen.** Die Domain ist etwa zehn Wochen alt, es gibt laut Authority-Radar **0 redaktionelle Links, 0 Mediennennungen**, und im Finanz-Bereich (YMYL) fehlt bei den meisten Beiträgen eine sichtbare Fachprüfung.
- **Die Inhalte wirken schematisch.** Sechs Artikel tragen dieselbe Titelformel („…-Update: Was sich jetzt für dich ändert"), mehrere Beiträge konkurrieren um dieselbe Suchanfrage, und 80 von 92 Beiträgen sind als KI-generiert markiert, ohne eigene Bilder oder Belege im Fließtext.

Das Tempo (34 neue Beiträge in den ersten 16 Tagen des Oktobers) verstärkt das Risiko. Google bewertet bei neuen Domains vor allem, ob Inhalte **einzigartig, belegt und nützlich** sind, und nicht die Menge.

---

## 2. Bewertung nach Bereichen

| Bereich | Note (1–10) | Befund |
|---|:---:|---|
| Technische SEO | **8** | Canonical selbstreferenziell, Sitemap ableitend, robots.txt mit Pinterest- und KI-Regeln, JSON-LD (Article, Person, Organization, Breadcrumb, FAQ), Index-Hygiene (Pager `noindex`, Tag-Archive aus), IndexNow, Bild-Preload für LCP. |
| On-Page (Titel, Descriptions, Struktur) | **7** | Median 54 Zeichen im Titel, 151 in der Description, keine doppelten Titel oder Descriptions. Jeder Beitrag hat 6–35 H2-Abschnitte; 85 von 92 haben zusätzlich einen Kurzantwort-Block. |
| Inhaltstiefe | **6** | Median 1.874 Wörter je Beitrag, sachlich, mit Rechenbeispielen. Aber: Formel-Titel, Themen-Überschneidungen und keinerlei eigene Bilder oder Screenshots im Fließtext. |
| E-E-A-T / Vertrauen (YMYL) | **4** | Autorenseite und Methodik sind gut. Aber nur **9 von 92** Beiträgen haben ein Prüfer-Feld, und Konto- und Kreditkarten-Beiträge sind ohne Prüfung. Erfahrungsaussagen im Text sind nicht belegt (Abschnitt 4). |
| Interne Verlinkung | **6** | Median 3 interne Links je Beitrag. Ein Beitrag hat keinen (`2026-09-04-digitaler-turbo-warum-der-dns-hack-…`). Kein einziger der 92 Beiträge verlinkt auf die acht Rechner, obwohl sie das Produktversprechen sind. |
| Autorität (externe Links) | **2** | 0 redaktionelle Links, 0 Mediennennungen, 0 Kooperationen (Stand Authority-Radar, 05.10.). Hier liegt der größte Hebel. |
| Reale Sichtbarkeit (GSC) | **1** | 51 Impressionen, 0 Klicks in 26 Tagen. Einzelne Beiträge stehen auf Position 2–5, aber mit fast keiner Nachfrage. |
| Performance | **7** | Lighthouse-LCP mobil 1.760 ms (Bestandsbefund 26.09.), Cover als AVIF mit Varianten, `defer` für Skripte. Repo-Gate „GREEN" (12.10.). Offen: ca. 495 KB JS insgesamt, 28 MB HTML über 115 Dateien (Build-Manifest). |
| Messbarkeit | **4** | Analytics ist bewusst aus (Umami entfernt 11.10.), `/go/`-Klickmessung ist inaktiv. Ohne eigene Messung ist Optimierung nur über Search Console möglich. |

**Gesamturteil: solide Technik, schwache Autorität und Sichtbarkeit.** Mit gezielten Eingriffen bei Inhalt, Vertrauen und Autorität lässt sich viel gewinnen. Mehr Technik bringt wenig.

---

## 3. Was bereits gut ist (nicht anfassen)

- **Canonical und Index-Steuerung** (`layouts/_partials/head.html`, `seo_indexierbar.html`): Pager und Archive sind `noindex, follow`, Canonical ist korrekt gesetzt.
- **Sitemap aus einer Quelle** (`layouts/sitemap.xml`, `seo_indexierbar.html`): Keine Namensliste mehr, die bei Wachstum veraltet.
- **Affiliate-Links** mit `rel="sponsored nofollow noopener"` (`render-link.html`). Das ist korrekt gekennzeichnet.
- **robots.txt** lässt Googlebot und Antwortmaschinen zu, sperrt Trainings-Crawler und `/go/`.
- **Autorenseite `/ueber/`** und **Methodik** erklären Verantwortung, Quellen und Finanzierung offen. Das ist für YMYL eine gute Grundlage.
- **Keine Keyword-Stuffing-Muster** und keine duplizierten Descriptions.

---

## 4. Die wichtigsten Befunde im Detail

### 4.1 Alt-URLs mit Nachfrage laufen ins Leere (Priorität: sofort)
Die Search Console listet URLs, die im Repo nicht mehr existieren:

- `/posts/kuehlschrank-strom-sparen-einstellung/`: 10 Impressionen, Position 21,6
- `/posts/elementarschadenversicherung-hochwasser-starkregen/`: Position 80
- `/posts/depot-umzug-steuerfrei-wechseln/`
- vier `/tags/…/`-URLs, obwohl Tag-Archive abgeschaltet sind

Ursache: `disableAliases = true` in `hugo.toml` schaltet Weiterleitungen global ab. Es gibt keine Redirect-Liste, und GitHub Pages kann keine 301 setzen. **Empfehlung:** Auf Cloudflare umziehen (Runbook-Punkt B.5 ist vorgesehen) und dort eine Redirect-Liste pflegen. Bis dahin gezielte Hugo-Aliase an den Nachfolge-Artikeln.

### 4.2 Keyword-Kannibalisierung und Formel-Titel (Priorität: hoch)
- „Gasrechnung senken": 3 Beiträge (08-14, 09-20 und „Gasrechnung prüfen").
- „Heizkosten senken": 3 Beiträge.
- „Frugalismus-Tipps": 2 Titel mit demselben Haupt-Suchbegriff.
- Preisgarantie Gas: 3 Beiträge, DSL-Wechsel: 5 Beiträge mit ähnlicher Suchabsicht.
- Titelformel „…-Update: Was sich jetzt für dich ändert" exakt 6-mal (Energie, Versicherung, Internet & DSL, Konto & Karten, Markt, Saison), dazu ein ähnlicher Vorsorge-Titel. Das widerspricht der eigenen Vorgabe in `CLAUDE.md` („Templates erzeugen Gleichförmigkeit").

**Empfehlung:** Je Suchabsicht einen Hauptartikel festlegen, verwandte Beiträge zusammenführen und per Redirect umleiten. Die „Update"-Titel durch konkrete Suchanfragen ersetzen, etwa „Gaspreise 2026: Was sich für Haushalte ändert".

### 4.3 Vertrauen im YMYL-Bereich (Priorität: hoch)
- **80 von 92** Beiträge sind mit `ai_generated: true` markiert. Das ist ehrlich und sollte so bleiben. Google bewertet KI-Text nicht pauschal negativ, wohl aber Texte ohne eigenen Nutzen oder Beleg.
- **Nur 9 von 92** haben ein Prüfer-Feld. Bei Versicherungen ist das gut gelöst. Bei Girokonto (08-17), Kreditkarte (09-03), Bankgebühren (10-06) und „Konto & Karten-Update" (09-29) fehlt es. Die eigene Policy nennt Kredite, Konten sind ein Grenzfall. Für Google zählt das Thema Geld insgesamt.
- **Erfahrungsaussagen ohne Beleg:** Der Beitrag zur Kfz-Versicherung sagt „Ich habe meine Autoversicherung in zehn Jahren fünfmal gewechselt." Die eigene Regel im Autorenbereich lautet aber „Keine Schein-Erfahrung: Persönliche Erfahrungen werden nur ausgewiesen, wenn ein dokumentierter Eigenbeleg referenziert ist." Diese Diskrepanz sollte geklärt werden.
- **Pauschale Angaben in der README:** „über zehn Jahre Praxis" und „Hunderte selbst durchgeführte Tarifvergleiche" sind nicht belegt. **Ihre Entscheidung:** belegen (Beweis-Register, Wechselprotokolle) oder neutral formulieren.

**Empfehlung:** Konto- und Kreditkarten-Beiträge prüfen lassen, die Erfahrungsaussagen belegen oder entfernen, und die Autorenseite mit echten Belegen (Fotos, Protokollen, Verweisen auf das Beweis-Register) stärken.

### 4.4 Keine eigenen Bilder im Fließtext (Priorität: mittel)
Alle 92 Beiträge enthalten nur das Cover-Bild. Im Fließtext gibt es **0 Bilder**. Eigene Screenshots (Vertragsseiten schwärzen), Rechenbeispiele als Grafik oder Tabellen sind für Bildersuche, Nutzerbindung und Vertrauen wirksam.

**Empfehlung:** Für die 20 Beiträge mit den meisten Impressionen je 2–3 eigene Abbildungen ergänzen (Alt-Text mit Suchbegriff, `width`/`height` setzen). Das ist der sichtbarste Einzelhebel auf der Seite.

### 4.5 Interne Verlinkung (Priorität: mittel)
- Median 3 interne Links je Beitrag, ein Beitrag ohne Link.
- Die acht Werkzeuge (Fixkosten-Scanner, Notgroschen-Rechner, Kündigungsfristen-Kalender usw.) sind eigenständige, verlinkbare Seiten. **Kein einziger der 92 Beiträge verlinkt auf `/werkzeuge/`.** Damit verschenkt der Blog genau den Traffic-Pfad, den das Produkt braucht.
- Die Pillar-Seiten sind gut gegliedert (sechs Themenwelten, je 5–18 Artikel, Versicherungen als Basis-Ratgeber).

**Empfehlung:** Jeder Beitrag verlinkt mindestens einen passenden Rechner, seine Pillar-Seite und zwei verwandte Beiträge (im Text, nicht nur in Kacheln). Den Beitrag ohne Link sofort reparieren.

### 4.6 Autorität aufbauen (Priorität: hoch, aber langfristig)
Das ist der größte Hebel, und er liegt außerhalb des Codes:

- **Linkwürdige Assets bekannt machen:** Der Fixkosten-Index 2026 Q4 und die Rechner eignen sich für Presse, Verbraucherportale und Fachkommentare.
- **Redaktionelle Erwähnungen** in Fachmedien und Verbraucherseiten anstreben. Das Authority-Radar hat dafür bereits ein Register, es ist aber leer.
- **Autor sichtbar machen:** Gastbeiträge, Interviews oder Auftritte im Presse-Bereich.

Ohne externe Links bleibt die Domain bei Finanzthemen schwer ranking-fähig, egal wie gut der Text ist.

### 4.7 Titel und Descriptions (Priorität: niedrig)
- 5 Titel über 60 Zeichen (Maximum 71), die bei Google abgeschnitten werden.
- 16 Descriptions über 160 Zeichen.

**Empfehlung:** Die 5 Titel kürzen, die 16 Descriptions auf 140–155 Zeichen bringen. Das lässt sich mit dem vorhandenen Gate `scripts/seo_cockpit.py` prüfen.

### 4.8 Messung (Priorität: mittel)
Ohne Messung lassen sich Ratschläge nicht gegenprüfen. Die Search Console liefert Suchdaten, aber keine Aufrufe, Verweildauer oder Conversions.

**Empfehlung:** Eine datenschutzfreundliche, cookielose Messung einführen (etwa Cloudflare Web Analytics oder selbst gehostetes Umami). Das passt zum Datenschutzversprechen des Blogs.

---

## 5. Maßnahmenplan

| # | Maßnahme | Aufwand | Wirkung | Wer |
|---|---|---|---|---|
| 1 | Alt-URLs mit Impressionen per 301 umleiten (Cloudflare oder Aliase) | klein | hoch | Technik |
| 2 | Den Live-Stand prüfen: Der Live-Abruf zeigt `/posts/` nur bis etwa 09.10., das Repo hat Beiträge bis 16.10. (Deploy-Rückstand oder Cache) | klein | mittel | Technik |
| 3 | Kannibalisierung auflösen: Gruppen zusammenführen, 6 „Update"-Titel neu benennen | mittel | hoch | Redaktion |
| 4 | Erfahrungsaussagen belegen oder streichen; README-Pauschalen prüfen | klein | hoch | Frank |
| 5 | Konto- und Kreditkarten-Beiträge fachlich prüfen lassen | mittel | hoch | Frank |
| 6 | Pro Top-20-Beitrag 2–3 eigene Abbildungen | mittel–groß | hoch | Redaktion |
| 7 | Interne Links: Rechner und Pillar in jeden Beitrag, Beitrag ohne Link reparieren | mittel | mittel | Redaktion |
| 8 | Publikationstempo auf etwa 2–3 gute Beiträge pro Woche senken, statt bis zu 2 pro Tag | klein | mittel | Frank |
| 9 | Autorität: Asset-Outreach, Presse, Kooperationen | groß | sehr hoch | Frank |
| 10 | Titel und Descriptions nachziehen | klein | niedrig | Technik |
| 11 | Cookielose Messung einführen | klein | mittel | Technik |

**Zum Tempo (Punkt 8):** Die Produktions-Wache verlangt aktuell mindestens 2 Beiträge pro Tag. Bei einer zehn Wochen alten Domain erzeugt das Volumen, aber kaum Vertrauen. Qualität vor Menge zu setzen, ist die Empfehlung. Die Entscheidung liegt bei Ihnen.

---

## 6. Was ich nicht bewerten konnte

- **Visuelles Design und Mobil-Darstellung:** Ich konnte keinen Browser starten (der Hugo-Build ist in dieser Umgebung nicht möglich, weil das Binary nicht geladen werden kann). Eine optische Prüfung fehlt daher.
- **Live-Werte für Core Web Vitals und Lighthouse:** Die Werte stammen aus Berichten im Repo, nicht aus einer frischen Messung.
- **Index-Abdeckung:** Die Zahl der indexierten Seiten steht nicht im Repo, nur die Anzahl der Einträge in der Sitemap.
- **Backlink-Profil:** Keine Abfrage externer Link-Daten möglich.

Empfehlung für den nächsten Schritt: einmal mit dem Build-Skript (`npm run seo:check`) und einer Lighthouse-Messung auf dem Live-Stand prüfen, dann die Maßnahmen 1–4 umsetzen.

---

## 7. Umsetzungsstand (19.10.2026)

**Korrektur zu den Zahlen oben:** Die Befunde in Abschnitt 4 nennen die Gesamtheit von 92 Beiträgen. Maßgeblich für Live-Wirkung sind **60 live** und **32 Entwürfe**. Die Zahlen oben bleiben als Gesamtbild stehen, die Live-Werte sind unten angegeben.

| # | Maßnahme | Stand | Was geändert wurde | Offen |
|---|---|---|---|---|
| 2 | Kannibalisierung und Formel-Titel | erledigt (Titel) | Live: 11 Titel geschärft (Gaspreis-Cluster 2×, Gasrechnung 2×, Heizungs-Check, Notgroschen, Frugalismus-Alltagsfehler, DSL-Treue, Sieben Geldgewohnheiten, DSL-Anschluss, Internet & DSL-Update). Entwürfe: 6 Update-Titel ersetzt. Keywords: „WLAN verbessern“ aus dem WLAN-Verstärker-Beitrag entfernt. | Duplikate ohne Redirect nicht gelöscht (Vorgabe). Merge-Kandidaten: 09-07 „Kleine Beträge“, 09-07 „Alltagsfehler“ und 09-11 „5 Tricks“ überschneiden sich stark; Notgroschen-Entwurf 10-07 „Notgroschen aufbauen“ überschneidet sich mit zwei Live-Beiträgen. Entscheidung nach Punkt 1 (Weiterleitungen). |
| 3 | Erfahrungsaussagen | erledigt (Live), Entwürfe mitgezogen | Haushaltsbuch: „Ich habe … getestet“, „Mein Erfahrungswert … 430 €“ als Modellrechnung gekennzeichnet; Handytarif: „Mein Sparbeispiel“ als Beispielrechnung. Frugalismus: „Fallstudie Max“ als fiktives Rechenbeispiel. Entwurf Kfz: Eigenes Spar-Beispiel als fiktiv gekennzeichnet, „fünfmal gewechselt“ gestrichen. Live-Beitrag Mietwagen (02.09.): „Meine Erfahrung“ durch Faustregel ersetzt. | README-Pauschalen („über zehn Jahre Praxis“, „Hunderte Tarifvergleiche“) nicht geändert: README ist Markenfläche und braucht Ihre Entscheidung. |
| 3 | Konto-/Kreditkarten-Fachprüfung | offen | keine | Kein benannter Prüfer. Ohne Prüfer keine Kennzeichnung „fachlich geprüft“. Entscheidung bei Ihnen. |
| 4 | 2–3 eigene Abbildungen je Top-20-Beitrag | teilweise | Für 8 Live-Beiträge mit Search-Console-Impressionen je 2 SVG (Merkkarte, Gliederung) aus dem eigenen Text. | Nur 8 von 20 Top-Beiträgen; 12 Plätze brauchen Ihre Auswahl. Die Gliederungsgrafik zeigt Zwischenüberschriften, keine Anleitung. Handgezeichnete Abbildungen wären stärker. |
| 5 | Rechner und Pillar pro Beitrag | erledigt (Live) | 60 von 60 Live-Beiträgen verlinken einen Rechner und eine Pillar-Seite (Block „Weiterrechnen und vertiefen“ vor dem Affiliate-Hinweis). Zuordnung nach Pillar und Titel. | Zuordnung ist heuristisch: einige Fälle (z. B. Bürobedarf → Haushaltsbudget, Einlagensicherung → Fixkosten-Scanner) bitte prüfen. |
| 6 | Autorität | Entwürfe und Recherche | Siehe `AUTORITAET-ENTWUERFE-2026-10-19.md`: Prioritäten, Recherche mit Quellen, Entwürfe A bis D. | Nichts versendet. Redaktionskontakte und Freigabe fehlen. |

**Live-Zahlen (60 Beiträge):** Werkzeug-Links vorher 0, jetzt 60. Pillar-Links vorher 58, jetzt 60. Formel-Titel live vorher 1, jetzt 0. Erfahrungsaussagen im Live-Text: entfernt oder als Modell gekennzeichnet.

**Nicht geprüft:** Ein Hugo-Build und ein Render-Test sind in dieser Umgebung nicht möglich (kein Hugo-Binary, kein GitHub-Zugriff). Die Frontmatter-Prüfung für alle 92 Beiträge ist erfolgreich (YAML gültig). Eine Sichtprüfung der Seiten nach dem Deploy steht aus.

### 7b. Nachtrag 19.10.2026: Entscheidungen auf Dauer gesichert

Die offenen Entscheidungen aus Punkt 2–6 sind jetzt als Repo-Artefakte festgehalten. Der Stand ist prüfbar, nicht nur behauptet.

| Artefakt | Zweck |
|---|---|
| `data/entscheidungen.yaml` | Entscheidungsregister E-01 bis E-15: Entscheidung, Begründung, Status, Verantwortlicher, Nachweis |
| `data/kannibalisierung_map.yaml` | Suchabsicht je Beitrag in den Clustern K1 bis K7; Regeln R1 bis R4 |
| `data/fachpruefung_register.yaml` | Prüfpaket für 17 Live-Beiträge mit erhöhtem Risiko oder Konto-/Karten-Pillar. Feld `pruefer` leer. Erzeugt durch `scripts/fachpruefung_register.py` |
| `data/top20_abbildungen.yaml` | Top-20-Auswahl und Regel (Dateikopf) |
| `scripts/ff_inhalts_wache.py` | Inhalts-Wache FF1–FF5 (Erfahrungsaussagen, Formel-Titel, Rechner-/Pillar-Links, Dubletten, Abbildungen) |
| `scripts/abbildungen_ableiten.py` | Erzeugt und prüft je 2 Abbildungen für die 20 Top-Beiträge |
| `scripts/tests/test_inhalts_register.py` | 16 Tests für Wache, Register und Map |

**Stand je Punkt**

| # | Punkt | Stand | Was offen bleibt (Entscheidung bei Ihnen) |
|---|---|---|---|
| 2 | Kannibalisierung, Formel-Titel | Titel umgesetzt, Map steht. Live-Formel-Titel: 0 (Wache FF2). | Drei Keyword-Bereinigungen (E-01). Entwürfe 09-23, 10-07 Notgroschen, 10-14, 10-16 nicht veröffentlichen; Verwerfen nur mit Ihrer Entscheidung (E-14). |
| 3 | Erfahrungsaussagen | Live bereinigt, Fallstudie als fiktiv gekennzeichnet, Wache FF1 grün. | README-Pauschalen „über zehn Jahre Praxis“ und „Hunderte … Tarifvergleiche“: nur Sie können sie belegen oder ersetzen (E-09). |
| 3 | Konto-/Kreditkarten-Fachprüfung | Prüfpaket erstellt, Status ausstehend, kein Prüfer. | Prüfer benennen (E-05). Empfohlene Reihenfolge im Register. |
| 4 | Abbildungen Top-20 | 20 von 20 Beiträgen mit je 2 eigenen SVG-Abbildungen, `--check` ohne Befund. | Die Abbildungen sind Schemata aus dem eigenen Text, keine Datengrafiken. Datengrafiken würden echte Zahlen brauchen (E-08). |
| 5 | Rechner und Pillar | 60 von 60 Live-Beiträge mit Rechner- und Pillar-Link. Drei Rechner-Zuordnungen korrigiert. | Stichprobe von 10 weiteren Beiträgen steht aus (E-10). |
| 6 | Autorität | Nur Entwürfe und Recherche, nichts versendet. | Redaktionskontakt (Digital-PR), Finanztip-Profil (nur durch Sie) (E-11, E-12). |
| – | Verbraucherkredit-Neuregelung 20.11.2026 | Kein Bestandsbeitrag betroffen. | Themenentwurf ja/nein (E-13). |

**Gate-Stand 19.10.:** Live-Blockaden 0. Veröffentlichte Beiträge (`--published --strict`): 60 Artikel, 0 Hochrisiko. Entwürfe: 10 Hochrisiko, davon 5 blockiert, bis ein benannter Prüfer freigibt.

**Gates, die in dieser Umgebung laufen:** `python3 -m unittest discover -s scripts/tests` mit dem Venv-Python (`/tmp/gv/bin/python`) ergibt 3359 Tests mit 1 Fehlschlag (`test_bot_watchdog_meldetakt`, Wirkungsprobe C25). Der gleiche Fehlschlag tritt im Ausgangsstand 258fd51 auf und wird nicht durch diese Arbeit verursacht. **Nicht ausführbar:** `layout_audit.py` braucht einen Hugo-Build; Hugo fehlt hier.

## 7c. Abschlussbericht 19.10.2026: Punkte 1–6

Dieser Abschnitt fasst den Stand nach dem Auftrag „auf Highend-Level einer Profi-Agentur, dauerhaft beheben“ zusammen. Die Befehle für jeden Punkt stehen im Register `data/entscheidungen.yaml` (E-01 bis E-21).

**Grundsatz:** Die Umsetzung liegt im Repo als Artefakt, nicht als Einzelmaßnahme. Nichts wurde veröffentlicht, versendet oder gelöscht. Entwürfe bleiben `draft: true`.

### Punkt 1 – 301-Weiterleitungen (E-16, E-17)

- **Befund:** 117 Alt-URLs waren veröffentlicht und sind heute nicht mehr erreichbar. Vier davon hatten im Zeitraum Nachfrage (GSC).
- **Umsetzung:** `data/weiterleitungen.yaml` ist die einzige Quelle: 114 Weiterleitungen, Regel A 6, B 73, C 35. 3 Alt-URLs stehen bewusst auf 404 (Regel D). Tag-Archive bleiben 404 (Regel E). Die Entscheidung „Index-Hygiene“ vom 29.09.2026 gilt weiter. Sie wird hier offengelegt, damit sie bestätigt werden kann.
- **Werkzeuge:** `scripts/weiterleitungen.py` (Check, Build, Verify, Cloudflare-CSV nur mit Flag), `scripts/url_wache.py` (Snapshot der 94 Live-URLs), Gate H9 in `scripts/index_hygiene_gate.py`, Anleitung `docs/ANLEITUNG-WEITERLEITUNGEN.md`.
- **Grenze:** GitHub Pages kann keine echten 301 setzen. Die Seiten sind Meta-Refresh (0 s, canonical, noindex,follow). Der echte 301 entsteht erst mit dem Cloudflare-Proxy.
- **Ehrlich zu den Zuordnungen:** Die Ziele beruhen auf Titel, Thema und Stichproben. Nicht jeder Text wurde einzeln gelesen. Die Regel-B-Einträge sollte die Redaktion gegenlesen.
- **Durchsetzung:** Gate H9 läuft im Deploy und stoppt bei harten Funden. Die Quellprüfung und der Test laufen nicht in der CI. Das wäre eine Workflow-Änderung und braucht einen Auftrag.
- **Offen für dich:** (a) Proxy-Status: `python3 scripts/weiterleitungen.py --proxy-check` auf deinem Rechner. `--cloudflare` erzeugt die CSV nur bei `aktiv` (eingebaut, 19.10.). Die Sandbox kann die Prüfung nicht ausführen. (b) Die CSV-Aktivierung im Cloudflare-Dashboard ist eine Außenwirkung und liegt bei dir. (c) Entscheidung, ob `--check` und der Test in `deploy.yml` aufgenommen werden.

### Punkt 2 – Kannibalisierung und Formel-Titel

- **Umsetzung:** 8 Live-Titel und 6 Entwurfs-Titel sind von Formeln befreit. Beispiel: „DSL-Anbieterwechsel: Ablauf, Ausfallzeiten und Effektivpreis“.
- **Entwürfe mit Dubletten** bleiben unveröffentlicht (E-14). Nichts wurde verworfen. Die Entscheidung über Überarbeitung oder Verwerfen liegt bei dir.

### Punkt 3 – Erfahrungsaussagen und Fachprüfung (E-03, E-05, E-09)

- **Umsetzung:** Unbelegte Ich-Aussagen im Live-Bestand sind entfernt oder als Modellrechnung gekennzeichnet. Die Fallstudie ist als fiktiv gekennzeichnet. Die Warnung der Beweis-Wache (Störungs-Beitrag) war ein Fehlalarm. Der Satz ist jetzt eindeutig.
- **Fachprüfung:** 17 Beiträge stehen im Register `data/fachpruefung_register.yaml`, alle ausstehend, kein Prüfer benannt. Eine Freigabe durch Automatik oder KI erfolgt nicht (E-05).
- **Offen bei dir:** Prüfer für Konto und Kreditkarte. README-Pauschalen („Über zehn Jahre Praxis“, „Hunderte selbst durchgeführte Tarifvergleiche“) sind deine persönlichen Angaben (E-09). Ich habe die README nicht verändert.

### Punkt 4 – Eigene Abbildungen

- **Umsetzung:** 20 Top-20-Beiträge haben je zwei eigene SVG-Abbildungen (Merkkarte und Ablaufgrafik). Erzeugt mit `scripts/abbildungen_ableiten.py`, Prüfung `--check` ohne Befund.

### Punkt 5 – Rechner und Pillar-Verlinkung (E-10, E-18)

- **Umsetzung:** 60 Live-Beiträge haben einen Rechner-Block und einen Pillar-Link. Drei Fehlzuordnungen sind korrigiert, dazu Campingurlaub: vom Effektivpreis-Rechner auf das Haushaltsbudget.
- **Stichprobe (11 Beiträge):** 6 passen. 4 haben keinen passenden Rechner: Balkonkraftwerk (Förderung und Amortisation), DNS-Server, WLAN-Verstärker vs. Mesh, Störung beim Internetanbieter. Ein fachlich falscher Rechner schadet mehr als ein fehlender. Die Entscheidung liegt bei dir (E-18): neues Werkzeug, Beibehalten oder Entfernen.

### Punkt 6 – Autorität (E-11, E-12, E-13, E-19, E-20)

- **Umsetzung:** Entwürfe und Recherche liegen in `AUTORITAET-ENTWUERFE-2026-10-19.md` (nicht versendet). Priorität 1: Digital-PR zum Fixkosten-Index. Priorität 2: Finanztip-Community (Profil nur durch dich).
- **Versand:** Kein Versand durch den Agenten. Redaktionskontakt, Community-Profil und Verbraucherkredit-Thema bleiben bei dir (E-11, E-12, E-13).
- **Methodik Fixkosten-Index:** Die BDEW-Werte sind geprüft: Strom 37,0 ct/kWh (BDEW-Strompreisanalyse 2026), Gas 11,93 ct/kWh (BDEW-Gaspreisanalyse August 2026). Die Rechnung stimmt. Der Strompreis bezieht sich laut BDEW auf 3.500 kWh inkl. anteiligem Grundpreis, das Modell rechnet mit 2.500 kWh. Das steht jetzt im Studientext. Die Zahlen bleiben unverändert (E-19, Änderungsprotokoll 19.10.2026).
- **Name (offen):** „Fixkosten-Index“ misst nur Strom und Gas. Vor dem Pitch entscheidest du, ob der Name bleibt oder ob die Seite umbenannt wird (E-20). Eine Umbenennung braucht eine Weiterleitung der alten URL, die Punkt 1 jetzt technisch ermöglicht.
- **Verbraucherkredit-Hinweis (20.11.2026):** Kein Bestandsbeitrag im Repo behandelt Verbraucherkredite. Ein Themenbeitrag wäre ein Entwurf und braucht deine Freigabe nach Fachprüfung (E-13).

### Offene Punkte und Befunde (Stand 19.10.2026)

- **Live-Aktualität geklärt (19.10.):** Der letzte Deploy auf `main` ist erfolgreich (19.10., 06:18 UTC). Die Seite `/posts/` zeigt den Beitrag vom 12.10. Die frühere Beobachtung „Stand 09.10. bzw. 25.09.“ war überholt.
- **Vorbestehender Testfehlschlag (E-21):** `test_bot_watchdog_meldetakt.test_rechter_baum_hat_keine_befunde`, Wirkungsprobe C25 (fail-closed). Identisch im Ausgangsstand 258fd51. Das Gate wurde nicht abgeschwächt.
- **Metadaten-Befund (E-15):** Privathaftpflicht, lastmod vor date. Ausgangsstand, unverändert.
- **Commit-Sperre:** Nicht scharf. `core.hooksPath` wird laut CLAUDE.md nicht gesetzt. Die README ist unverändert.
- **Sandbox-Grenze:** Hugo ist nicht installierbar. Die Gate-Prüfung H9 wurde gegen einen simulierten Build mit den echten 114 Zielen geprüft, nicht gegen einen echten Hugo-Build.
