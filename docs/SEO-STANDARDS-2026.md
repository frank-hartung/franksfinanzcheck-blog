# 📚 SEO-STANDARDS-2026.md – Aktueller Rechts-/Regelstand für Unique Content

> **Stand der Recherche: 14.08.2026.** Dieses Dokument ist die Wissensbasis
> hinter `scripts/web_uniqueness_guard.py` und `scripts/content_depth_guard.py`.
> SEO-Regeln ändern sich laufend (siehe die Update-Historie unten) – bei
> größeren Google-Core-/Spam-Updates oder spätestens alle 6 Monate sollte
> dieser Stand neu recherchiert werden (siehe „Frischhaltung" unten).

## 1. Duplicate Content: keine Straf-Schwelle, sondern Kanonisierung

Google bestraft doppelten Inhalt **nicht** anhand eines Prozentsatzes – die
verbreiteten „10 %"- oder „30 %"-Schwellen sind ein Mythos ohne offizielle
Quelle. Stattdessen **konsolidiert** Google mehrere Versionen derselben
Seite zu einer bevorzugten URL (Kanonisierung) und behält nur diese im
Index; Linkwert, Crawl-Häufigkeit etc. werden auf die kanonische Version
übertragen.

**Signal-Rangfolge für die Kanonisierung** (stärker zu schwächer):
1. 301-Redirect
2. `rel="canonical"`-Tag
3. Konsistente interne Verlinkung auf die gewünschte URL
4. Sitemap-Eintrag (schwaches Signal)
5. HTTPS wird gegenüber HTTP bevorzugt

**Praxis-Regeln (offizielle Google-Best-Practices):**
- Jede Seite bekommt einen **selbstreferenzierenden** `rel=canonical`.
- **Keine widersprüchlichen Signale** setzen (z. B. Sitemap zeigt auf URL A,
  `rel=canonical` auf URL B).
- `noindex` NICHT zur Kanonisierung innerhalb der eigenen Seite nutzen –
  dafür ist `rel=canonical` das richtige Werkzeug (noindex blockiert die
  Seite komplett aus der Suche).
- `robots.txt` NICHT zur Kanonisierung nutzen.
- Canonical-Fixes brauchen laut Google (Update 10.07.2026 an der
  Troubleshooting-Doku) **bis zu 2 Wochen**, bis die Neubewertung
  abgeschlossen ist – realistische Erwartungshaltung beim Reporting.

*Quellen: developers.google.com/search/docs/crawling-indexing/consolidate-duplicate-urls;
Google-Search-Central-Changelog vom 10.07.2026.*

## 2. Scaled Content Abuse – das eigentliche Risiko für KI-Content-Seiten

Für eine Seite wie franksfinanzcheck.de (vollautomatisiert KI-generiert)
ist NICHT die klassische Duplicate-Content-Frage das größte Risiko,
sondern Googles Spam-Richtlinie **„Scaled Content Abuse"**:

> „Generating many pages primarily to manipulate search rankings, with
> little or no value added for users." (Google Spam Policies)

**Wichtig:** Die Richtlinie verbietet **nicht** KI-Content an sich –
entscheidend ist der **Mehrwert pro Seite**, nicht die Erstellungsmethode.
Das März-2026-Core-Update hat das gezielt durchgesetzt (Sites mit
50-80 % Traffic-Verlust hatten typischerweise: keine Autoren-Angaben,
identische Struktur über viele Seiten hinweg, keine eigene Erfahrung/
Recherche). Seit 15.05.2026 gelten dieselben Spam-Richtlinien explizit
auch für Googles generative Antworten (AI Overviews/AI Mode).

**Was franksfinanzcheck.de bereits richtig macht (nicht anfassen):**
- Sichtbare Autorenschaft (Frank Hartung, Person-Schema)
- `erfahrung:`-Feld mit echtem Erstpersonen-Kontext pro Artikel (E-E-A-T)
- Transparente KI-Kennzeichnung (Mastodon-Bio, `ai_generated: true`)
- Konservative Publikationskadenz statt Massenproduktion (`cadence_manager.py`)

**Was die neuen Tools zusätzlich absichern:**
- `content_depth_guard.py`: verhindert identische, oberflächliche
  Artikelstruktur durch echte Themen-Tiefe pro Artikel.
- `web_uniqueness_guard.py`: stellt sicher, dass technische Signale
  (Titel/Description/Canonical) nicht versehentlich Duplicate-Cluster
  erzeugen.

*Quellen: Google Spam Policies (Stand Mai 2026); Search-Central-Changelog
15.05.2026 ("spam policies now cover generative AI responses"); Analyse
des März-2026-Core-Updates (mehrere unabhängige SEO-Publikationen,
Juli/August 2026).*

## 3. Themenautorität ("Topical Authority") als 2026-Standard für Content-Tiefe

Sowohl klassische Google-Suche als auch KI-Antwortsysteme bewerten 2026
zunehmend, ob eine Seite ein **Thema vollständig** behandelt statt nur ein
einzelnes Keyword zu bedienen:

- Folgefragen aktiv innerhalb desselben Artikels beantworten (nicht erst
  in einem separaten Artikel) – stärkt Featured-Snippet- und
  AI-Overview-Auswahl.
- Teilaspekte über H2/H3-Struktur abdecken statt nur in die Länge zu
  schreiben.
- Sonderfälle/Ausnahmen explizit benennen – das unterscheidet einen
  Profi-Ratgeber von einer oberflächlichen Zusammenfassung.
- Interne Verlinkung zwischen thematisch verwandten Artikeln stärkt das
  Themen-Cluster (bereits vorhanden: `internal_linker.py`).

*Quellen: mehrere unabhängige SEO-Fachpublikationen zu "Topical Authority"
und "On-Page SEO Factors 2026" (Stand Juni-Juli 2026).*

## 4. Bekannte Grenzen dieser Automatisierung

- **Keine echte Google-Index-Prüfung**: Weder `web_uniqueness_guard.py`
  noch ein anderes Tool in diesem Repo kann zuverlässig/regelkonform
  automatisiert abfragen, ob eine URL tatsächlich im Google-Index steht
  (Scraping von `site:`-Suchen verstößt gegen Googles Nutzungsbedingungen
  und ist unzuverlässig). Für echte Indexierungsdaten ist die **Google
  Search Console API** nötig (siehe `docs/ANLEITUNG-GOOGLE-SEARCH-CONSOLE.md`,
  noch nicht eingerichtet – wie schon bei `cadence_manager.py` erwähnt).
- **Web-Duplikat-Suche ist stichprobenartig**: `web_uniqueness_guard.py`
  prüft einzelne Textphrasen, keine vollständige Volltext-Gegenprüfung wie
  kommerzielle Tools (Copyscape etc.) – das ist der realistische
  kostenlose Kompromiss (Google Programmable Search Engine, 100
  Anfragen/Tag gratis).
- **Dieses Dokument ist ein Snapshot.** Es ersetzt keine laufende
  Beobachtung von Google Search Central / offiziellen Spam-Policy-Updates.

## 5. Frischhaltung dieses Dokuments

Eine vollautomatische, wirklich "live" Recherche ist aus einem GitHub-
Actions-Workflow heraus nicht sauber möglich (keine Web-Suche ohne
zusätzliche, meist kostenpflichtige API). Empfehlung:

- Bei jedem bekannten Google-Core-/Spam-Update (RSS/Twitter von
  „Google Search Central") kurz prüfen, ob sich etwas an den Kapiteln 1-3
  ändert.
- Spätestens alle 6 Monate: den Agenten bitten, diesen Stand neu zu
  recherchieren und zu aktualisieren (analog zu einer Bitte wie
  „Aktualisiere SEO-STANDARDS-2026.md auf den neuesten Stand").
- `scripts/content_depth_guard.py`/`web_uniqueness_guard.py` selbst
  brauchen bei einer inhaltlichen Änderung dieses Dokuments ggf. neue
  Schwellenwerte (z. B. `MIN_FAQ`, `MIN_H2`) – das ist eine bewusste
  redaktionelle Entscheidung, keine Automatik.
