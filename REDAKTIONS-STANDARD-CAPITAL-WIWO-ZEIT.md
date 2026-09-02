# 📰 REDAKTIONS-STANDARD: Capital · WirtschaftsWoche · DIE ZEIT

**Version 1.0 · Stand 02.09.2026 · Auftrag:** Die Blogautomatik von
[franksfinanzcheck.de](https://franksfinanzcheck.de) dauerhaft auf das
Qualitätsniveau der Online-Redaktionen von **Capital**, **WirtschaftsWoche**
und **DIE ZEIT (Verbraucher-/Geld-Teil)** anheben – für **bestehende und
zukünftige** Beiträge.

Dieses Dokument ist die Recherche-Grundlage (Quellen verlinkt) und die
Übersetzung der dort eingesetzten Methoden in **konkrete, automatisch
geprüfte Regeln**. Die technische Umsetzung liegt in
`scripts/redaktions_standard.py` (Regeln RS1–RS8) und ist verdrahtet in
Content-Engine v2 (neue Artikel), Blog-Doktor (tägliche Kette),
SEO-Weekly (Bestands-Retrofit) und die Generation-Prompts.

---

## 1. Was die drei Redaktionen machen (Recherche-Befunde)

### 1.1 CAPITAL (capital.de) – „Geld & Versicherungen"

**Selbstverständnis** (Verlagsprofil): „Glaubwürdigkeit, fundierte
Recherche, journalistische Exzellenz"; Dreiklang „Geld verdienen, Geld
vermehren, Geld ausgeben"; Ressorts „Welt der Wirtschaft · Investieren ·
Leben". Für Nutzwert-Themen (Vergleiche, Gütesiegel, Ratgeber) gilt
Capital als Goldstandard.

Befunde aus aktuellen Online-Artikeln (Sept. 2026):

| Methode | Beleg (Live-Beispiel) | Übertragung auf FranksFinanzcheck |
|---|---|---|
| **„Capital erklärt“-Fragenkatalog:** fette Fragen als Zwischenüberschriften, jede Antwort 3–5 Sätze, direkt und konkret | [Was Sie über die Altersvorsorge wissen sollten](https://capital.de/geld-versicherungen/was-sie-ueber-altersvorsorge-wissen-muessen) | **RS2:** Mindestens 2 Frage-Überschriften (H2 mit „?“) pro Artikel – Frage → direkte Antwort, kein Drumherum |
| **Konkrete Zahlen MIT benannter, verlinkter Quelle** (Bertelsmann-Studie, Statistisches Bundesamt) | ebd. + [Versicherungen-Ratgeber](https://www.capital.de/geld-versicherungen/ratgeber-dossiers/versicherungen--welche-sie-wirklich-brauchen-und-welche-unnoetig-sind-9362046.html) („2 700 Euro pro Kopf laut Statistischem Bundesamt") | **RS5 + RS6:** Zahlen nur mit Einordnung (ca./laut/Stand) und NIE mit erfundenen Quellen – ein Bot darf keine Phantom-Studien zitieren |
| **Faustregeln** („Mindestens zehn Prozent des Nettoeinkommens …") | ebd. | **RS3:** Jeder Artikel enthält mindestens eine klar markierte Faustregel |
| **Teaser/Standfirst:** 1–2 Sätze unter der Headline, die Nutzen versprechen („Eine Anleitung") | [100.000 Euro anlegen – Dossier](https://www.capital.de/geld-versicherungen/100-000-euro-anlegen--wie-am-besten--anleitung-fuer-die-richtige-geldanlage-32604232.html) | Description-Zeile + Haken-Einleitung (bereits R7-Öffnungen) |
| **Byline:** Autorin mit Profil-Link, Datum, Uhrzeit, **Lesezeit („9 Min.")** | ebd. | Autor + Datum vorhanden; **Lesezeit** aktiv (`ShowReadingTime`), plus „Stand“-Zeile (RS8-Baustein) |
| **Ratgeber-Dossiers:** mehrteilige Serien mit Nummerierung | ebd. | Pillar-Cluster + interne Verlinkung (bereits vorhanden); Serien-Logik über Themenpool |
| **Struktur-Disziplin:** Tabellen, Checklisten, „Mehr zum Thema“-Links, Bildunterschriften mit © | ebd. | Tabelle/Checkliste bereits Pflicht-Modul; Tabellen-System + Linker vorhanden |

### 1.2 WIRTSCHAFTSWOCHE (wiwo.de) – „Wie wir arbeiten"

Die WiWo beschreibt ihre eigenen Qualitätsmethoden öffentlich
([In eigener Sache: Über uns](https://www.wiwo.de/in-eigener-sache/in-eigener-sache-ueber-uns-das-bietet-die-wirtschaftswoche/100113417.html)):

1. **„Wir verifizieren und gegenprüfen Informationen, bevor wir sie
   veröffentlichen."** → Übertragung: kein unbelegter Fakten-Text
   aus der KI. Harte Zahlen dürfen nur mit Einordnung (Spanne/„ca.“/
   Rechenweg) erscheinen – **RS5**; Rechenbeispiele werden bereits von
   `math_guard.py` nachgerechnet.
2. **„Wir hören mehrere Quellen, bevor wir schreiben."** → Übertragung:
   ein Bot kann keine Quellen anrufen – also gilt die ehrliche Variante:
   **keine erfundenen Quellen/Studien/Experten-Zitate** (**RS6**).
   Was nicht belegbar ist, wird als allgemeines Wissen formuliert oder
   als Beispiel gekennzeichnet.
3. **„Wir korrigieren transparent Fehler."** → Übertragung: neue
   **Korrektur-Box** (Frontmatter `korrektur:`, sichtbar unter der
   Headline) + Korrektur-Log (**RS8**).
4. **Präzise Sprache, Pressekodex, Unabhängigkeit** → bereits abgedeckt
   durch Lektorat (L1–L15), Hardcases, Stil-Wache, Affiliate-Shield.
   Neu verstärkt: Weichmacher- und Unschärfe-Radar läuft jetzt gezielt
   auf Zahlen-Sätze (RS5).

### 1.3 DIE ZEIT (zeit.de) – Verbraucher-/Geld-Teil („Geld", „Die Geldverbesserer")

Das Ressort wurde 2023 gegründet, um „die Fragen [zu] beleuchten, die
aktuell für Ihre privaten Finanzen wichtig sind"
([Pressemitteilung ZEIT-Verlagsgruppe](https://www.zeit-verlagsgruppe.de/pressemitteilung/zeit-online-startet-das-ressort-geld/),
[Einführungstext](https://www.zeit.de/geld/2023-05/zeit-online-gruendet-geld-ressort)).

Befunde aus Live-Artikeln:

| Methode | Beleg | Übertragung |
|---|---|---|
| **„Artikelzusammenfassung“-Box** (Das Wichtigste in 3–5 Bullets) direkt unter der Headline | [ETF-Fallen (Geldverbesserer)](https://www.zeit.de/geld/2026-05/etf-fallen-investieren-fehler-finanztipps-geldverbesserer), [Haushaltsbuch-Kolumne](https://www.zeit.de/geld/2026-01/url-geld-sparen-haushaltsbuch-ausgaben-app-excel) | **RS1:** Pflicht-Modul „**Das Wichtigste in Kürze**" (3–4 Bullets) nach der Einleitung |
| **Selbstversuch & persönliche Erfahrung** („Ich habe ein Jahr Haushaltsbuch geführt") | ebd. | `erfahrung:`-Feld im Frontmatter (E-E-A-T) – **RS7** macht es zur Pflicht |
| **Nummerierte Fallen-/Tipp-Listen** („Falle Nummer eins wartet …") mit konkreten Zahlen | [ETF-Fallen](https://www.zeit.de/geld/2026-05/etf-fallen-investieren-fehler-finanztipps-geldverbesserer) | **RS4:** mindestens eine nummerierte Schrittfolge (3–6 Schritte) |
| **Klar benannte Autoren/Kolumnen** („Eine Kolumne von Laura Städtler und Thomas Kehl") | ebd. | Autor-Pflicht + `erfahrung:` (RS7); Byline mit Lesezeit |
| **Nüchterner, präziser Ton, ausgewogene Einordnung statt Verkaufssprache** | alle Beispiele | bestehende Stil-Gates; neue Zahlen-/Quellen-Regeln (RS5/RS6) |
| **Interne Verlinkung auf Themen-Seiten** (zeit.de/thema/etf) | ebd. | Pillar-Links + `internal_linker.py` (bereits vorhanden) |

---

## 2. Die Umsetzung: Regeln RS1–RS8 in `scripts/redaktions_standard.py`

| Regel | Quelle/Methode | Prüfung | Verhalten |
|---|---|---|---|
| **RS1** | ZEIT-Artikelzusammenfassung | Pflicht-Modul „**Das Wichtigste in Kürze**" mit ≥ 3 Bullets | hart bei neuen Artikeln (`--gate`); KI-Heilung (`--fix --ai`) fügt die Box nach der Einleitung ein |
| **RS2** | Capital erklärt | ≥ 2 H2-Überschriften als Frage („?") | hart bei neuen Artikeln; KI formuliert vage H2 um |
| **RS3** | Capital-Faustregeln | ≥ 1 markierte Faustregel („Faustregel: …") | hart bei neuen Artikeln; KI ergänzt |
| **RS4** | ZEIT-Tipplisten / Capital-Dossier | ≥ 1 nummerierte Liste mit ≥ 3 Schritten ODER ≥ 2 „Schritt“-Überschriften | hart bei neuen Artikeln; KI ergänzt |
| **RS5** | WiWo-Verifikation | Sätze mit harten Zahlen (€/%/3+-stellig) ohne Einordnung (ca./rund/laut/Stand/Spanne) | weich (Report); `--ai` formuliert ehrlich um |
| **RS6** | WiWo-Quellen-Regel / Pressekodex | Erfundene-Quellen-Muster („laut einer Studie“, „Experten sagen“, Phantom-Statistiken) | weich (Report); `--ai` ersetzt durch beleg-freie, ehrliche Formulierungen |
| **RS7** | ZEIT-/Capital-Byline, E-E-A-T | Frontmatter `author:` UND `erfahrung:` vorhanden | deterministische Selbstheilung (Standard-Erfahrungstext wird ergänzt) |
| **RS8** | WiWo-Korrektur-Transparenz | `korrektur:`-Feld im Frontmatter → sichtbare Korrektur-Box im Layout; Log in `data/korrekturen.yaml` | Layout + Log (dauerhaft aktiv) |

**Sabotage-Schutz:** eingefrorener Selbsttest (`--selftest`, Exit 2 = CI-Abbruch)
für alle Detektoren und die Heil-Verifikation (Links bleiben erhalten,
H2-Anzahl stabil, Länge ≥ 90 %, Frontmatter unangetastet, Idempotenz).
**Circuit-Breaker:** meldet der Gate-Modus mehr als 3 neue Artikel mit
harten Funden, wird NICHTS geparkt – dann gelten die Detektoren als
fehlerhaft (gleiche Schutzlogik wie beim Qualitäts-Score).

## 3. Verdrahtung (dauerhaft)

| Ort | Was passiert |
|---|---|
| `content-engine-v2.yml` Phase 2 | `redaktions_standard.py --fix --ai --new-only` (Heilung bei der Geburt) + `--gate --new-only` (harte Funde → Artikel bleibt Entwurf) |
| `scripts/blog_doctor.py` (täglich via Health + Engine) | Eintrag in der kanonischen Kette: `--fix` (deterministisch, kostenlos) |
| `seo-weekly.yml` (mittwochs) | **Bestands-Retrofit:** `--fix --ai --backlog 3` hebt wöchentlich die 3 Artikel mit den meisten Lücken auf Standard |
| `scripts/generate_drafts.py` (Prompts) | Die Pflicht-Module (Kürze-Box, Frage-H2, Faustregel, Schritte, Zahlen-/Quellen-Regeln) stehen jetzt DIREKT im Generierungs-Prompt – die meisten RS-Regeln werden also von der KI schon beim Schreiben erfüllt; die Wache prüft und heilt nur noch die Restfälle |

## 4. Bericht & Nachvollziehbarkeit

- **Report:** `REDAKTIONS-STANDARD-REPORT.md` (je Lauf: Flottenstand RS1–RS8, gehärtete Artikel, verbliebene Funde)
- **Historie:** `data/redaktions_standard_history.jsonl`
- **Korrekturen:** `data/korrekturen.yaml` + Korrektur-Box im Artikel-Layout
- **Regelwerk:** Abschnitt „Redaktions-Standard RS1–RS8" im `QUALITAETS-REGELWERK.md`

## 5. Quellen

1. Capital – „Capital erklärt: Was Sie über die Altersvorsorge wissen sollten":
   https://capital.de/geld-versicherungen/was-sie-ueber-altersvorsorge-wissen-muessen
2. Capital – „100.000 Euro anlegen" (Ratgeber-Dossier, Standfirst, Byline, Lesezeit):
   https://www.capital.de/geld-versicherungen/100-000-euro-anlegen--wie-am-besten--anleitung-fuer-die-richtige-geldanlage-32604232.html
3. Capital – „Versicherungen: Welche Sie wirklich brauchen" (Statistisches Bundesamt als benannte Quelle):
   https://www.capital.de/geld-versicherungen/ratgeber-dossiers/versicherungen--welche-sie-wirklich-brauchen-und-welche-unnoetig-sind-9362046.html
4. Capital – Markenprofil (Dreiklang, Nutzwert-Standard):
   https://pryntad.com/de/zeitschriften/capital
5. WirtschaftsWoche – „In eigener Sache: Über uns – wie wir arbeiten"
   (Verifizieren, mehrere Quellen, transparente Korrekturen, Pressekodex):
   https://www.wiwo.de/in-eigener-sache/in-eigener-sache-ueber-uns-das-bietet-die-wirtschaftswoche/100113417.html
6. ZEIT ONLINE – Start des Ressorts „Geld" (Pressemitteilung der ZEIT-Verlagsgruppe):
   https://www.zeit-verlagsgruppe.de/pressemitteilung/zeit-online-startet-das-ressort-geld/
7. ZEIT ONLINE – „In eigener Sache: Wir haben Geld":
   https://www.zeit.de/geld/2023-05/zeit-online-gruendet-geld-ressort
8. ZEIT ONLINE – „ETF-Fallen" (Artikelzusammenfassung, Autorenzeile, nummerierte Fallen):
   https://www.zeit.de/geld/2026-05/etf-fallen-investieren-fehler-finanztipps-geldverbesserer
9. ZEIT ONLINE – „Geld sparen: Ich habe ein Jahr Haushaltsbuch geführt" (Selbstversuch, Zusammenfassung):
   https://www.zeit.de/geld/2026-01/url-geld-sparen-haushaltsbuch-ausgaben-app-excel

> _Änderungen an den Regeln RS1–RS8 werden ausschließlich in
> `scripts/redaktions_standard.py` + diesem Dokument gepflegt.
> Das Regelwerk vergisst nie._
