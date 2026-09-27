# SEO-/GEO-Redaktion auf Premium-Level · 27.09.2026

## Auftrag

Den gesamten redaktionellen Bestand – bestehende und künftige Blogartikel,
Ratgeber-/Pillar-Seiten, redaktionelle Unterseiten und Newsletter-Landingpage –
mit Agent Reach und Claude dauerhaft pflegen; die „Im Artikel“-Navigation
zugänglich und hochwertig absichern.

## Umgesetzt

### 1. Ein verbindlicher redaktioneller Gesamt-Scope

`scripts/post_utils.py` ist jetzt die Single Source of Truth für vier Scopes:

- `posts`: Blogartikel
- `guides`: Pillar-/Ratgeberseiten
- `pages`: Startseite, Methodik, Newsletter-Landingpage, Über
- `editorial`: alle drei Gruppen

Rechtstexte sowie Bestätigungs-, Präferenz- und Abmeldeseiten sind bewusst nicht
Teil einer KI-Umschreibung. Das schützt juristische und prozessuale Worttreue.
Jeder Inhalt besitzt einen repo-relativen, kollisionsfreien State-Key.

### 2. Claude für den gesamten Redaktionsbestand

Die Claude-Stilpolitur läuft im Workflow mit
`--scope editorial --include-drafts` statt nur über veröffentlichte
`content/posts/`. So werden bestehende Live-Inhalte und künftige Entwürfe vor
der Veröffentlichung erfasst. Der Prompt kennt den Content-Typ: Newsletter-Conversion-Copy,
Methodik, Ratgeber und Blogartikel werden nicht mehr gleich behandelt.

Vor Claude laufen im Workflow auch Grammatik- und Sprachglättung über denselben
Gesamt-Scope. Bestehende Sicherheitsverträge bleiben unverändert: Überschriften,
Zahlen, Links/Ankertexte, Shortcodes, HTML und Tabellenstruktur werden vor jedem
Schreiben verifiziert. Leere Markdown-Landingpages verbrauchen kein Modellbudget.
Alte Post-States werden lesend akzeptiert und beim nächsten erfolgreichen Lauf
auf den kollisionsfreien Pfad-Key migriert.

### 3. Agent-Reach-Recherche bei Geburt und im sinnvollen Turnus

Neu: `scripts/agent_reach_editorial_research.py`.

- neue Inhalte: sofortiger Quellenlauf in Content-Engine Phase 1b
- Titel-/Description-/Keyword-/Gliederungsänderung: sofort wieder fällig
- Pillar-Ratgeber: alle 21 Tage
- Blogartikel: alle 30 Tage
- Newsletter-Landingpage/Startseite: alle 45 Tage
- Methodik/Über: alle 90 Tage
- Netzbudget: acht Seiten je Mo/Mi/Fr-Lauf; neue/geänderte und jüngste zuerst

Je Seite entsteht ein nachvollziehbares Dossier mit URL, Herausgeber, Datum und
Quellenklasse. Primär-/Verbraucherquellen und offene Marktsignale bleiben
sichtbar getrennt. Ein fehlgeschlagener Abruf setzt keinen falschen
„recherchiert“-Status. Das jüngste passende Dossier wird Claude als
Aktualitäts-/Intent-Kontext mitgegeben. Neue Behauptungen, Zahlen, Fristen oder
URLs daraus sind im Prompt verboten und würden zusätzlich am Byte-Gate scheitern.
Recherche ist automatisch; ungeprüfte Fakten werden nie automatisch publiziert.

Der Agent-Reach-Workflow läuft nun Montag, Mittwoch und Freitag. Die
Content-Engine recherchiert zusätzlich jeden neuen Inhalt direkt nach seiner
Erstellung.

### 4. SEO/GEO und Newsletter

Die Newsletter-Landingpage gehört zum redaktionellen Claude-/Agent-Reach-Scope:
Text, Nutzerintention und Aktualität werden wie bei Ratgeberseiten gepflegt. Ihr
bestehender Journey-Vertrag bleibt jedoch unangetastet: Anmeldung, Bestätigung,
Präferenzen und Abmeldung bleiben `noindex` und außerhalb der Sitemap. Damit
wird eine transaktionale E-Mail-Strecke nicht künstlich zur Such-Landingpage;
die SEO-/GEO-Sichtbarkeit entsteht weiterhin über indexierbare Artikel und
Ratgeber, die sauber auf die Anmeldung führen.

### 5. „Im Artikel“-Navigation

Die vollständige, bewegliche Desktop-Navigation behält Lesefortschritt,
Selbstnachführung, Drag/Tastatursteuerung und ihre kollisionsfreie Dock-Position.
Zusätzlich ist die Inhaltsstruktur jetzt ein echtes semantisches `ol/li` statt
einer unstrukturierten Link-Sammlung. Das verbessert Screenreader-Navigation.
Ein Klassenfehler bei nummerierten H3 wurde geschlossen: Unterabschnitt und
Nummernlayout bleiben nun gleichzeitig erhalten.

## Verifikation

- `python3 scripts/agent_reach_editorial_research.py --selftest` – grün
- `python3 scripts/grammar_check.py --selftest` – 11/11 grün
- `python3 scripts/sprachglatt.py --selftest` – 12/12 grün
- `python3 scripts/claude_stilpolitur.py --selftest` – 16/16 grün (mit PyYAML-Testumgebung)
- `python3 -m unittest scripts.tests.test_editorial_scope` – 4/4 grün
- `node scripts/ff_toc_beweglich_test.mjs` – 18/18 grün
- `node scripts/ff_heading_glyph_guard_test.mjs` – 48/48 grün
- vollständige Python-Regressionssuite – 967 Tests grün, 5 erwartete lokale Skips
- Hugo Extended 0.164.0 Produktions-Build – 205 Seiten, fehlerfrei
- Themenwelten-Browserprüfung – 309 Prüfungen grün
- `git diff --check` – sauber

Die eigentlichen Claude-Schreibläufe benötigen weiterhin das bereits vorgesehene
`PUTER_AUTH_TOKEN`; der Lauf verwendet keine Anthropic-API. Hugo Extended wurde
über die im Repository vorgesehene PyPI-Ausweichquelle installiert und der
Produktions-Build damit vollständig gegengeprüft.
