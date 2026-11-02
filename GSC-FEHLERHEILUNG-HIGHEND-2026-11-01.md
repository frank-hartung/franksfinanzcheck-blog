# GSC-Indexierung: sämtliche repo-seitigen Fehler geheilt

**Vorgang:** Alle Blogseiten in die Google-Search-Console-Indexierung bringen
und jeden Fehler auf Agentur-Niveau beheben
**Stand:** 01.11.2026 · Build: Hugo 0.168.0 Extended · Gegenprobe: `public/`
**Auftrag:** „Sorge dafür, dass alle Blogseiten bei der Google Search Console
indexiert werden und sämtliche Fehler behoben werden – auf Highend-Level einer
Profi-Agentur, um höher bei Google zu gerankt zu werden."
**Vorherige Wahrheit:** `GSC-OPTIMIERUNGSPLAN-2026-10-27.md` (Maßnahmen M1–M10)
und `data/gsc/abdeckung/befund.json` vom 31.10.2026.

---

## 1 · Das Ergebnis in vier Sätzen

Der Abdeckungs-Befund läuft nach dieser Sitzung mit **genau einem
Widerspruch** (W5, Index-Altlasten bei Google – keine Repo-Maßnahme) statt
dreien: **W10 und W11 sind geheilt**, nicht wegkonfiguriert. Jede der **79
Inhaltsseiten** hat jetzt mindestens einen redaktionellen Inlink (vorher 4
Seiten ohne), und **alle 104 Sitemap-URLs tragen ein `lastmod`** (vorher 9
ohne). Der Duplikat-Guard meldet zum ersten Mal **D1–D6 komplett null** –
inklusive zweier redaktioneller Dopplungen zwischen dem Strom- und dem
Gastarife-Artikel und einer Disclaimer-Abweichung vom Hausstandard. Die
Indexierungs-Anfrage selbst (`gsc_indexierung.py`, URL-Inspection-API,
Wellen 40/64 bei 200/Tag-Kontingent) läuft weiter automatisiert über
`gsc-import.yml` – sie braucht das Dienstkonto und kann aus dieser
Netzumgebung nicht angerufen werden.

| Kennzahl | vorher (31.10.) | jetzt (01.11.) | Quelle |
|---|---|---|---|
| Widersprüche im Abdeckungsbefund | W5, W10, W11 | **nur W5** | `--audit --schreiben` |
| Sitemap-URLs ohne `lastmod` (W10) | 9 | **0** | `public/sitemap.xml` |
| Links auf nicht gebaute Seiten (W11) | 2 Ziele / 3 Quellen | **0** | `tote_ziele()` |
| Inhaltsseiten ohne redaktionellen Inlink | 4 (von 79) | **0** | `--audit` |
| Duplikat-Befunde D1–D6 | D3: 1 · D4: 2 | **0 / 0 / 0 / 0 / 0 / 0** | `duplikat_guard.py` |
| YMYL-Disclaimer außerhalb des SSOT-Wortlauts | 2 Artikel | **0** | `ki_shared.py::DISCLAIMER` |
| Gate-Zustand (Verifikation, Hygiene, Schema, H1, Metadaten, Tags, URL-Wache, Weiterleitungen, Layout, SEO-Cockpit P1/P2) | grün | **grün** | Abschnitt 5 |

---

## 2 · Befund W10 – neun Sitemap-URLs ohne `lastmod`, mit Beleg geheilt

Google entscheidet bei fehlendem `lastmod` selbst über den Crawl-Zeitpunkt –
das Gegenteil von Crawl-Nachfrage. Betroffen waren die neun Rechts- und
Vertrauensseiten (Datenschutz, Impressum, Über, Presse, Transparenz,
Methodik, Änderungsprotokoll, Newsletter-Checkliste,
„So entstehen unsere Vergleiche").

**Der Weg durfte kein Datum erfinden.** `sitemap_lastmod.html` duldet nur
belegte Redaktionsdaten („Kein ‚heute' oder Datum fremder Artikel auf
Impressum/Datenschutz/Über"). Der flache Klon kennt keine Historie – also
stammt jedes Datum aus der **GitHub-Commits-API** (je Datei: letzter Commit,
der `content/<seite>/index.md` geändert hat):

| Seite | lastmod | Beleg (Commit) |
|---|---|---|
| aenderungsprotokoll, datenschutz, impressum, methodik, presse | 2026-10-27 | #916 bzw. #915 |
| newsletter-checkliste, ueber | 2026-10-25 | #875 |
| so-entstehen-unsere-vergleiche, transparenz | 2026-10-25 | #868 |

Neun Zeilen Frontmatter, kein Fakteninhalt geändert. Nach dem Build:
**104 von 104 Sitemap-URLs mit `lastmod`.**

## 3 · Befund W11 – Links auf Entwürfe, nach Regel C umgehängt

Zwei Live-Artikel verlinkten Seiten, die nicht gebaut werden (Rendering
zeigt Klartext, der Link ist wirkungslos):

| Quelle (live) | Fund | Heilung |
|---|---|---|
| `2026-08-26-kfz-versicherung-vergleich…` | „Weiterlesen" auf Privathaftpflicht- und Wohngebäude-**Entwurf** (beide `cadence_wait`, Promotion earliest Mo 03.11.) | Beide Links ersetzt durch Live-Ziele: „Abos und Verträge" + „Handyvertrag kündigen" (Thema Vertragskosten/Kündigung); Ratgeber Versicherungen bleibt verlinkt. Linkzahl im Goldkorridor unverändert (2 Post-Links). |
| `2026-09-30-last-minute-urlaub…` | Kontextfremder Link „worauf du achten musst" auf den Wohngebäude-**Entwurf** – ein Zuordnungsfehler des Content-Engine (Anker passte auf den Entwurfs-Titel, nicht aufs Thema) | Link auf „wie du fair vergleichst" umgehängt auf den **live**en Flugvergleich-Ratgeber (28.10.) – erfüllt damit exakt das Quelle-Ziel-Paar aus dem Verlinkungsauftrag, im Fließtext statt in der Weiterlesen-Zeile. |

Sobald die beiden Entwürfe über `cadence_guard` ausgeliefert werden, fordert
`test_versicherungs_cluster_verlinkung.py` die Pillar-Links zurück (grün
bestätigt). **Von Hand live geschaltet wurde nichts** – der Kadenz-Wache
gehört der Weg ins Blog.

## 4 · Interne Verlinkung: von „4 Inseln" auf null

Der Verlinkungsauftrag (`gsc_abdeckung --verlinkung`) wählte je Ziel die
inhaltlich nächste Quelle mit freier Goldkorridor-Kapazität. Angewandt:
**7 eingefügte Links + 1 im Fließtext vorab erfüllt** (siehe Abschnitt 3):

- ETF-Sparplan (24.10.) ← Grosseinkauf/Vorrat, Frugalismus-Familie
- Strategisch sparen – Reisekasse (25.10.) ← Flugvergleich, Campingurlaub
- Frugalismus Familie (27.10.) ← Büroausstattung, Erster eigener Haushalt
- Kfz-Versicherung (26.08.) ← DSL-Anbieterwechsel
- Flugvergleich (28.10.) ← Last-Minute-Urlaub (im Fließtext)

Alle fünf Ziele waren die Seiten ohne einzigen redaktionellen Inlink –
Crawl-Tiefe und Themenautorität kommen jetzt bei ihnen an statt nur im Menü.
Median der ausgehenden Links bleibt 6, Korridor-Anteil 89 % (Grenze 85 %).

## 5 · Duplikat-Heilung – zwei Energie-Artikel, drei Funde, eine Wurzel

Der Duplikat-Guard meldete D3-X (Absatz wortgleich) und zweimal D4-X
(Fast-Duplikate 0,87–0,95) zwischen dem Stromanbieter- (23.10.) und dem
Gastarife-Artikel (26.10.) – **beide Entwürfe in laufender Schlussprüfung**,
also innerhalb des Review-Zyklus heilbar (aenderungsgrund je erweitert):

1. **„Ein belastbarer Vergleich beginnt bei deiner Abrechnung …"** (D3,
   wortgleich): Im Gastarife-Artikel eigenständig formuliert – dieselben drei
   Fakten (Abrechnung → Vertrag → Kalender; Beispielwerte sind keine
   Marktpreise; Originalunterlagen prüfen), eigene Sprache.
2. **„Vorsicht bei Vorkasse …"** (D4, 0,95): Eigenständig formuliert, Beleg
   (Q1 Bundesnetzagentur) benannt, Tatsachen unverändert.
3. **„Als Haushaltskunde muss dich dein Anbieter …"** (D4, 0,87): Eigenständig
   formuliert (Sonderkündigungsrecht, Monatsfrist, Inhalte der Mitteilung).
4. **Wurzel des vierten Fundes:** Beide Artikel trugen einen YMYL-Disclaimer
   abseits des SSOT-Wortlauts (`scripts/ki_shared.py::DISCLAIMER`, 15 Artikel
   im Standard): „dient **der** allgemeinen Information und ersetzt keine
   Rechtsberatung" statt „dient **ausschließlich der** allgemeinen Information
   und stellt keine Anlage-, Rechts- oder Steuerberatung dar". Beide auf den
   Hausstandard zurückgeführt – damit greift auch die Boilerplate-Whitelist
   des Duplikat-Guards wieder, statt D4-X auf Pflichttext zu messen.

Kein Fakteninhalt, keine Zahl, keine Quelle wurde geändert; die
redaktionelle Schlussprüfung bleibt „ausstehend" und findet jetzt einen
duplikatfreien Bestand vor.

## 6 · Kandidatenraum: entschieden statt erfunden

Der Kandidatenraum meldet 38 URLs „ohne Entscheidung" (Obergrenze). 26 davon
sind die abschließend erklärten Fälle vom 27.10. (24 Taxonomie-URLs, Regel E;
`/posts/posts/` × 2 ohne Ziel). Die **12 neuen Varianten** stammen aus den
fünf seit dem 28.10. veröffentlichten Artikeln (KFZ, ETF-Sparplan,
Reisekasse, Frugalismus-Familie, Flugvergleich; je datumslose Form + `(1)`).

**Belegt per GitHub-Commits-API: Keine dieser Alt-Formen existierte je**
(`content/posts/<slug>/` bzw. `<slug>(1)/` – je 0 Commits). Die
Regel-A-Muster der 136er-Liste („Ordner nach Datumssystem umbenannt",
„Dublette mit Zähler (1)") treffen auf sie schlicht nicht zu. Eine
Weiterleitung hätte Historie behauptet, die es nicht gab – deshalb:
**keine erfundenen Einträge in `data/weiterleitungen.yaml`.** Der Raum wird
stattdessen hier als Entscheidung dokumentiert: *Variante nie existiert,
kein Handeln; der Kandidatenraum bleibt Obergrenze und Frühwarnung für
echte Engine-Dubletten.* Der 404-Posten (223) erklärt sich aus Historie vor
dem 27.10. – für die Zuordnung einzelner URLs braucht es den
Detail-Export (M1, Abschnitt 7).

## 7 · Was offen bleibt – und wo es läuft

| Punkt | Warum hier offen | Wo es passiert |
|---|---|---|
| M1: 404-Detail-Liste einlesen | Export nur aus der GSC-Oberfläche/API holbar; Netz hier auf GitHub/NPM/PyPI beschränkt | Search Console → Indexierung → Seiten → 404 → Exportieren, dann `gsc_abdeckung --vorschlaege` |
| M2: Indexierungs-Anfragen in Wellen (40/64, Kontingent 200/Tag) | braucht Dienstkonto (Secret) | `gsc-import.yml` täglich; `npm run gsc:indexieren` von Hand |
| M10: neuer Abdeckungs-Export (Stand 19.10., 13 Tage alt) | Export = manueller CSV-Download | Wochenroutine `npm run gsc:abdeckung` nach Import |
| M7: Sprung vom 17.10. erklären | Ursachenanalyse `--ursachen` ohne flache-Historie-Ersatz | CI mit `fetch --shallow-since` (Runbook im Wochenbericht) |
| W5: 13 Index-Altlasten bei Google | Nur Google entfernt alte URLs, mit 301-Stubs + Zeit | Cloudflare-301 (M3-Plan) beschleunigt das Abklingen |
| Link-Dichte: 10 Artikel < 2 Links, 1 Artikel > 9 | 8 der 10 sind Entwürfe (Publish-Gate greift bei Auslieferung); 2 Live-Fälle sind Redaktionsentscheidungen mit Historie im Report | `link_density_guard.py` je Satzung report-only |

## 8 · Nachweise (alle 01.11.2026, gleicher Build)

| Prüfung | Ergebnis |
|---|---|
| `hugo --minify --destination public` | ✅ 114 Seiten, 0 Fehler |
| `gsc_verifikations_guard.py` (V1–V12) | ✅ Besitznachweis, robots/Sitemap, 104 Sitemap-Einträge, 106 indexierbar, 0 unerklärte noindex |
| Sitemap-`lastmod` | ✅ 104/104 (vorher 95/104) |
| `gsc_abdeckung --audit --schreiben` | 🟢 GRÜN · Widersprüche: nur W5 (info) · W10/W11 entfallen |
| `index_hygiene_gate.py` | ✅ Verhältnis 0,45:1 (Budget 1,0), 0 Tag-Archive, 0 Aliase |
| `duplikat_guard.py` | ✅ D1–D6 alle 0 (vorher D3:1, D4:2) |
| `link_density_guard.py` | ✅ 89 % im Goldkorridor (≥ 85 %), Median 6 |
| `metadaten_wache.py` | ✅ 111 Dateien, 0 Befunde |
| `h1_wache.py` | ✅ Quelle + Build |
| `tag_governance.py --check` | ✅ Taxonomie sauber |
| `schema_seo_gate.py` | ✅ 405 Seiten, 79 Money-Pages, 0 harte Funde |
| `url_wache.py` | ✅ grün (108 Live-URLs) |
| `weiterleitungen.py --check/--verify` | ✅ 251/251 stimmen mit Quelle überein |
| `seo_cockpit.py --strict --fail-on …` | ✅ P1: 0, P2: 0 (10 P3 Cornerstone-Hinweise) |
| `layout_audit.py` | ✅ hreflang, DOM-Budget, Chunker-Vertrag im Budget |
| `editorial_review_gate` (beide geänderten Artikel) | ✅ 0 blockiert, Status „ausstehend" unverändert |
| `test_versicherungs_cluster_verlinkung` | ✅ 6/6 |
| `gsc_abdeckung --selftest` | ✅ 99 Fälle grün |

**Indexquote-Realität:** 117 von 437 bekannten URLs (26,8 %, Stand 19.10.)
sind zu 93 % Aufräumarbeit bei Google (223 × 404 Historie). Die repo-seitigen
Voraussetzungen für steigende Quote stehen jetzt vollständig: jede Seite
erreichbar und verlinkt, Sitemap vollständig datiert, keine Duplikate, keine
wirkungslosen Links. Den Zeitverlauf ablesen: `npm run gsc:abdeckung:md`
nach dem nächsten Import.
