# SEO-Parität im Eigenbau: Linkvorschläge, Cornerstones, Fokus-Keywords, Social-Vorschau

Stand: 28.10.2026 · vier Werkzeuge, ein gemeinsamer Anspruch
Anlass: Anfrage „Yoast SEO Premium kostenlos nachbauen“. Warum es hier keinen
Nachbau gibt, sondern vier eigenständige Module, steht in
[SEO-PARITAET-EIGENBAU-2026-10-28.md](../SEO-PARITAET-EIGENBAU-2026-10-28.md).
Dieses Dokument ist die Bedienungsanleitung.

## Voraussetzungen

- Python ≥ 3.11
- PyYAML 6.0.3 – in `requirements-ci.in` gepinnt, nicht optional. Fehlt es,
  verweigern die Wachen den Dienst mit einer klaren Meldung statt mit einem
  stillen Grün (dasselbe Verhalten wie `scripts/metadaten_wache.py`).
- Hugo ist für diese vier Werkzeuge **nicht** nötig. Die Social-Vorschau liest
  das Frontmatter; `--quelle build` nutzt einen vorhandenen `public/`-Build,
  verlangt ihn aber nicht.
- Keine neuen Abhängigkeiten, keine externen Dienste, kein Netzwerkzugriff.

## Die vier Werkzeuge

### 1. Linkvorschläge als Liste (`scripts/link_vorschlaege.py`)

Liest denselben Korpus und dieselben Anker-Kandidaten wie
`scripts/internal_linker.py` – importiert, nicht kopiert – und **schreibt
nichts**. Ergebnis: CSV, Markdown und JSON in `.cache/link-vorschlaege/`, mit
dem fertigen Link zum Einfügen.

```bash
npm run links:vorschlaege            # alles vorschlagen
npm run links:vorschlaege:verwaist   # nur Ziele ohne eingehende Links
npm run links:vorschlaege:json       # maschinenlesbar
python3 scripts/link_vorschlaege.py --pro-artikel 3 --min-score 150
python3 scripts/link_vorschlaege.py --datei content/posts/<slug>/index.md
```

Bewertung (Reihenfolge für Menschen, kein Rankingfaktor):

| Baustein | Punkte |
|---|---|
| Grundscore des Ziels (Keyword-Abdeckung) | 50–80 |
| Themenüberlappung in `keywords`/`tags` | 100 je Treffer |
| Ziel hat keinen eingehenden Link | +25 |
| Ziel hat höchstens zwei eingehende Links | +10 |
| Ziel ist Cornerstone | +15 |
| Anker liegt im ersten Drittel | +5 |

Sperrzonen sind dieselben wie im Linker: Überschriften, Code, Shortcodes,
HTML-Attribute, bestehende Links, kanonische CTA- und Offenlegungsblöcke.
Ein Artikel am Deckel (9 interne Links) bekommt einen ausdrücklichen Hinweis
statt weiterer Vorschläge. Gelaufen in ~1,5 s über 76 Artikel.

**Grenze:** Der Vorschlag kennt keine Absicht. Ob der Satz den Link trägt,
entscheidet die Redaktion. Ein Link, der nur der Zahl dient, ist ein
schlechter Link.

### 2. Cornerstone-Inhalte (`scripts/cornerstone_wache.py`)

Das Frontmatter-Feld `cornerstone: true` markiert die Inhalte, die eine
Themenwelt tragen. Die Wache prüft, ob diese Inhalte auch so behandelt werden:

| Regel | Prüfung | Schwere |
|---|---|---|
| C1 | `cornerstone` ist ein Boolean (kein `"ja"`) | P2 |
| C2 | Cornerstone ist veröffentlicht | P1 |
| C3 | ≥ 5 eingehende interne Links aus anderen Artikeln | P1 |
| C4 | `lastmod`/`date` ≤ 180 Tage alt | P2 |
| C5 | `keywords_fokus`, `kurzantwort`, `quellen`, `cover.alt` vorhanden | P2 |
| C6 | Eingehende Links aus nur einer Themenwelt (Hinweis) | P3 |

```bash
npm run cornerstone:check        # Gate + Selbsttest
npm run cornerstone:kandidaten   # Vorschläge, paste-fertig
npm run cornerstone:bericht      # .cache/cornerstone/bericht.md
```

Gezählt werden alle drei im Bestand vorkommenden Linkformen
(`/posts/<slug>/`, `../../posts/<slug>/`, absolute Marken-URL), je Quelle
**einmal**; Selbstverweise zählen nicht. Die Zählung ist dieselbe, die auch
die Linkvorschläge und das SEO-Cockpit verwenden.

**Die Wache markiert nichts.** Kandidaten sind ein Vorschlag mit
`cornerstone: true`-Zeile zum Einfügen – die Entscheidung bleibt redaktionell.
Ein Skript, das sich selbst zu Cornerstones erklärt, hebt die Bedeutung des
Feldes auf.

### 3. Mehrere Fokus-Keywords (`scripts/fokus_keywords.py`)

Neues, geordnetes Feld:

```yaml
keywords_fokus: ["DSL-Wechselbonus sichern", "Internetvertrag wechseln"]
```

Der erste Eintrag ist die Hauptintention. Regeln:

| Regel | Prüfung |
|---|---|
| F1 | 1–5 Einträge, je 1–5 Wörter, ≤ 60 Zeichen, keine Dubletten |
| F2 | Primär-Keyword im Titel |
| F3 | Primär-Keyword im ersten Absatz |
| F4 | Primär-Keyword in mindestens einer H2 |
| F5 | Primär-Keyword in der Description |
| F6 | Jedes Sekundär-Keyword kommt im Fließtext vor |
| F7 | Dichte 0,4–2,5 % (zu hoch = P2, zu niedrig = P3) |
| F8 | Kannibalisierung: derselbe Primär-Keyword auf mehreren Seiten |
| F9 | Feld fehlt → Empfehlung, kein Gate |

```bash
npm run fokus:check       # Prüfung, Exit 1 bei P1/P2
npm run fokus:vorschlag   # Vorschläge aus den vorhandenen keywords
npm run fokus:bericht     # .cache/fokus-keywords/bericht.md
```

Verglichen wird casefold + umlautgefaltet (`ä→ae`, `ß→ss`), auf Wortgrenzen –
`konto` trifft nicht in `kontoführung`. Fehlt das Feld, ist das eine Empfehlung
(P3), damit 97 bestehende Artikel nicht nachträglich rot werden.

**Grenze:** Kein „SEO-Score“. Ein grüner Lauf heißt: die formalen Bedingungen
sind erfüllt – nicht, dass der Text gut ist oder rankt.

### 4. Social-Vorschau (`scripts/social_vorschau.py`)

Zeigt, was Leser bei X, Facebook, LinkedIn, WhatsApp, Slack und Pinterest
sehen – mit Kürzungsmarkierung und Befunden.

```bash
npm run social:vorschau         # .cache/social-vorschau/index.html
npm run social:vorschau:serve   # http://127.0.0.1:4175
python3 scripts/social_vorschau.py --quelle build   # gerenderte og:*-Tags
python3 scripts/social_vorschau.py --json
```

- **Grenzen und Bildmaße** stehen in `scripts/social_limits.py` (SSOT), nicht
  im JavaScript. Jeder Richtwert nennt seine Quelle.
- **Bildmaße** werden aus dem Dateikopf gelesen (PNG, JPEG, GIF, WebP) – ohne
  Pillow, ohne Schätzung. Unbekannte Formate werden als „nicht messbar“
  gemeldet, nicht geraten.
- **Quelle:** `frontmatter` (Standard ohne Build) bildet `og:title` nach der
  Regel aus `layouts/_partials/seo_title.html` nach – eine Annahme, die die
  Seite in der Kopfzeile benennt. `--quelle build` liest die tatsächlich
  gerenderten Tags aus `public/` und ist maßgeblich, wenn ein Build existiert.
- **Datenschutz:** Die Seite ist `noindex`, hat eine strenge CSP, macht keine
  Netzaufrufe und speichert nichts. Sie wird **nicht** mit dem Blog
  veröffentlicht.
- Ausgabe außerhalb von `public/`, `static/`, `content/`, `layouts/` und `.git`
  wird verweigert.

Befunde: fehlendes Bild (P1), zu klein/zu groß (P2), Seitenverhältnis (P3),
Titel/Beschreibung über dem Kanal-Richtwert (P3), fehlendes `og:image:alt` (P3).

**Grenze:** Kein Netzwerk dokumentiert verbindlich, ab welchem Zeichen es
kürzt. Die Zahlen sind gemessene Konventionen (Stand 10/2026). Ein Befund
heißt „prüfen“, nicht „falsch“.

## Zusammenspiel

```
content/*.md ──┬─► cornerstone_wache ──► Linkgraph (eingehende Links)
               │             │
               │             ├─► seo_cockpit.py      (Befunde im selben Bericht)
               │             └─► link_vorschlaege.py (Verwaist-/Cornerstone-Bonus)
               │
               ├─► fokus_keywords ──► Hauptintention (C5 liest dasselbe Feld)
               └─► social_vorschau ──► social_limits (Kanalgrenzen, Bildmaße)
```

Eine Zählung, eine Grenzwertquelle, kein zweiter Linker. Wo zwei Werkzeuge
dieselbe Frage beantworten, importiert eins das andere.

## Tests

```bash
npm run test:seo-paritaet
# = scripts.tests.test_fokus_keywords
#   scripts.tests.test_cornerstone_wache
#   scripts.tests.test_link_vorschlaege
#   scripts.tests.test_social_vorschau
#   + node --test tools/social-vorschau/app.test.cjs
```

Jedes Werkzeug hat zusätzlich `--selftest` (Sabotage-Proben). Die Unit-Tests
sind hermetisch: Temp-Verzeichnis, kein Hugo, kein Netz, keine echten Inhalte.
`test_link_vorschlaege` prüft ausdrücklich, dass ein Lauf über den echten
Bestand **keine** Datei in `content/` verändert.

Fehlt PyYAML im System-Python (z. B. auf einem frischen Rechner), brechen die
Tests mit „PyYAML fehlt – Wache nicht scharf" ab. Das ist Absicht
(fail-closed). Abhilfe:

```bash
python3 -m venv .venv && .venv/bin/pip install pyyaml==6.0.3
.venv/bin/python -m unittest scripts.tests.test_fokus_keywords \
  scripts.tests.test_cornerstone_wache scripts.tests.test_link_vorschlaege \
  scripts.tests.test_social_vorschau
```

## Einbindung in die CI (Entscheidung des Inhabers)

Die Workflows sind sicherheitsrelevante Dateien (siehe `CLAUDE.md`, Regel 3)
und wurden hier bewusst **nicht** angefasst. Vorschlag für einen eigenen
Schritt im PR-Gate:

```yaml
- name: SEO-Parität
  run: |
    python3 scripts/fokus_keywords.py --selftest
    python3 scripts/fokus_keywords.py
    python3 scripts/cornerstone_wache.py --selftest
    python3 scripts/cornerstone_wache.py
    python3 scripts/social_vorschau.py --selftest
    npm run test:seo-paritaet
```

`fokus_keywords` und `cornerstone_wache` sind Gates (Exit 1 bei P1/P2),
`link_vorschlaege` und `social_vorschau` sind Berichte (Exit 0).

## Was diese Werkzeuge nicht sind

- **Kein Yoast.** Kein WordPress, keine Lizenzfrage, kein fremder Code.
- **Keine Rankinggarantie.** Kein Werkzeug hier kennt Rankings, Suchvolumen
  oder Wettbewerber – dafür fehlt eine Datenquelle, nicht ein Feature.
- **Kein automatisches Schreiben.** Nur der bestehende `internal_linker`
  schreibt Links, und zwar auf ausdrückliche Anweisung.
- **Kein Admin-Backend.** Die Seiten sind lokal, `noindex`, ohne Anmeldung.
  Ein Arena-Vorschaufenster (`--bind 0.0.0.0`) ist keine Freigabe zum
  Veröffentlichen.
