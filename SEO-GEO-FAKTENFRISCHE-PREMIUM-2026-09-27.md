# SEO/GEO, „Im Artikel“ und automatische Fachrecherche auf Premium-Level (27.09.2026)

**Auftrag (Frank, 27.09.2026):** Blogartikel, Unterseiten, Ratgeberseiten und
Newsletter SEO- und GEO-optimieren, Layout/Design auf Agentur-Niveau bringen,
die **„IM ARTIKEL“**-Box dauerhaft auf Premium-Level halten – und bestehende wie
zukünftige Artikel automatisch mit **Agent Reach und Claude** fachlich
optimieren: Recherche bei der Content-Erstellung und in sinnvollen Abständen.

---

## Befund zuerst: Was fehlte wirklich

Der Blog war beim Prüfen **nicht** SEO-schwach. Alle vorhandenen Gates liefen
grün:

| Gate | Ergebnis vor dieser Arbeit |
|---|---|
| `scripts/seo_audit.py` | 0 Probleme in 40 Artikeln |
| `scripts/seo_cockpit.py` | 213 Seiten, P1/P2/P3 = 0 |
| `scripts/schema_seo_gate.py` | 46 Money-Pages, 0 harte Funde |
| `scripts/layout_audit.py` | 2 411 interne Links, 0 kaputt |

Eine weitere Runde Meta-Kosmetik hätte also nichts bewegt. Die echte Lücke lag
woanders – und sie ist die teuerste im generativen Zeitalter:

> **Kein einziger Artikel nannte eine Quelle.**

Für Antwortmaschinen (AI Overviews, ChatGPT Search, Perplexity) ist eine
unbelegte Zahl eine Behauptung. Zitiert wird, wer nachweist. Und dieselbe
Lücke ist der Grund, warum „fachlich auf Premium-Level“ bisher nicht
automatisierbar war: Es gab Signale (Agent Reach), es gab eine Verfallsmessung
(Decay-Radar) – aber **keine Brücke von der Recherche zum Beleg im Artikel**.

Genau diese Brücke ist jetzt gebaut.

---

## 1. Faktenfrische: Agent Reach + Claude, artikelgenau und automatisch

**Neu:** `scripts/faktenfrische.py` · Vertrag: `data/agent_reach/faktenfrische.yaml`
· Runbook: `docs/ANLEITUNG-FAKTENFRISCHE.md`

### Zwei Takte – genau die beiden, die beauftragt waren

| Takt | Auslöser | Umsetzung |
|---|---|---|
| **bei Content-Erstellung** | neuer Artikel/neue Ratgeberseite ohne `faktencheck` (Priorität 0) | `content-engine-v2.yml`, Phase 3: `faktenfrische.py --neu --apply` |
| **in sinnvollen Abständen** | Fälligkeit nach Risikoklasse | `.github/workflows/faktenfrische.yml`, Di + Do 06:40 MESZ |

„Sinnvolle Abstände“ heißt nicht Gießkanne, sondern Halbwertszeit:
**saisonal 30 Tage** (Heizung, Stichtag 30.11., Jahreswechsel), **YMYL 45 Tage**
(Versicherung, Kredit, Zins, Tarif, Frist, Energie), **Standard 90 Tage**.
Budget: 3 Seiten je Lauf – Rotation statt Rundumschlag.

**Blogartikel und Ratgeberseiten gleichermaßen:** `content/posts` **und**
`content/pillar` sind im Bestand (`--scope alle`, Default; einzeln adressierbar
über `--scope posts` / `--scope pillar`). Bei gleicher Dringlichkeit läuft die
**Ratgeberseite zuerst** – ein Silo trägt die interne Verlinkung vieler
Artikel, ein veralteter Wert dort vergiftet die ganze Themenwelt.

### Der doppelte Deckel gegen Halluzination

Claude bekommt Artikel + Dossier und antwortet in JSON. Eine Quelle überlebt
den Weg in den Artikel nur, wenn **beides** stimmt:

1. Die URL steht **wörtlich im Dossier** (wurde also wirklich abgerufen).
2. Die Domain liegt auf der **Allowlist** (Rang 1 amtlich → Rang 3 Redaktion).

Affiliate-Partner sind bewusst nicht belegfähig: Provisionsquelle ≠
Faktenquelle. Der Selbsttest friert den Fall ein – eine erfundene URL und eine
echte gehen hinein, nur die echte kommt heraus (ST3).

### Eng begrenztes Schreibrecht

Die Maschine schreibt **zwei Frontmatter-Felder**: `faktencheck` und `quellen`.
Nicht den Artikeltext (fachliche Befunde gehen als Report/Queue/Issue an einen
Menschen), und **nie** `lastmod` – ein Faktencheck ist keine inhaltliche
Überarbeitung, und die Frische-Inflation vom 21.09.2026 bleibt abgeschaltet.
Vor jedem Schreibvorgang läuft der Selbsttest (Sabotage-Schutz), nach jedem
Schreibvorgang wird geprüft, dass der Body byte-identisch geblieben ist.

---

## 2. GEO: Belegkette wird sichtbar UND maschinenlesbar

**Neu:** `layouts/_partials/ff_quellen_box.html` (Posts + Ratgeber-Silos),
CSS-Block „Quellen & Faktenstand“ in `z-premium-blog.css`,
`citation` + `sdDatePublished` in `layouts/_partials/schema_article.html`.

- Für Leser: nummerierte Belege mit Herausgeber und Datum, Prüfstempel
  „Fakten geprüft am …“, Dokument-Anmutung statt Marketing-Kasten, Dark Mode
  und Druckfassung inklusive.
- Für Maschinen: dieselben Daten als `schema.org/citation` mit
  `publisher`/`datePublished`, das Prüfdatum als `sdDatePublished` (getrennt
  von `dateModified` – zwei verschiedene Aussagen).
- **Eine Quelle, zwei Ausspielwege.** Es gibt keinen zweiten Pflegeort, an dem
  Sichtbares und Schema auseinanderlaufen könnten.
- Ohne `quellen:` rendert nichts – kein leerer Kasten auf Altbeständen.

Jeder Lauf misst zusätzlich die **GEO-Reife** jedes Artikels an sechs
Merkmalen (Kurzantwort, FAQ, Belege, Zahlen, Tabelle, Prüfdatum) und schreibt
Durchschnitt und häufigste Lücken in `FAKTENFRISCHE-REPORT.md`.
Ausgangsstand des Bestands: **65 %** über 60 Seiten (54 Blogartikel +
6 Ratgeberseiten) – die größte Einzel-Lücke war die fehlende Belegkette
(60 von 60 Seiten ohne Quellenangabe). Nach den in dieser Runde belegten
Seiten: **70 %**; der Rest folgt über die Rotation der beiden Workflows.

**Belegt in dieser Runde (per Hand recherchiert und verifiziert):** neun
Seiten – der Ratgeber „Strom & Gas sparen“ und acht Energie-Artikel – mit
BDEW-Strompreisanalyse (37,0 ct/kWh, Stand 08/2026), BDEW-Gaspreisanalyse
(11,93 ct/kWh im Einfamilienhaus, Stand 08/2026), Verbraucherzentrale
(Anbieterwechsel; Grundversorgung mit 2-Wochen-Frist) und Bundesnetzagentur. Der Rest des Bestands läuft über die Rotation der beiden
Workflows – im CI sind die Feeds erreichbar, in der Sandbox dieser Session
waren sie es nicht (das Skript meldet das sauber mit Exit 3, statt still zu
schweigen).

---

## 3. „IM ARTIKEL“: Premium-Politur **und** eine Wache, die sie festhält

Die Box war am 26.09.2026 bereits zweimal repariert worden (Deckel bei 9
Einträgen; Überlappung des Newsletter-Kopfes). Beide Male hatte ein harmlos
aussehendes Refactoring den Premium-Zustand gekippt. Deshalb zwei Schritte:

**Politur** (`z-premium-blog.css`, Block „Im Artikel – Premium-Politur“):

| Detail | Wirkung |
|---|---|
| Zweistufiger Schatten + 1px-Innenlicht (`inset`) | Materialtiefe statt flacher Kasten – ohne zusätzliches DOM |
| Getönter Verlauf (2 % Akzent oben) | Die Box hebt sich auch auf weißem Grund ab, ohne Textkontrast zu kosten |
| Zähler als Ziffernpille, `tabular-nums` | „1 / 9“ und „12 / 24“ sind gleich breit – kein Zappeln beim Scrollen |
| Aktiver Eintrag: 3px-Akzentkante mit runder Kappe, Verlaufsfläche, 1px Versatz | Leseposition auf einen Blick, ohne Farbschrei |
| Fortschrittsbalken mit Verlauf | Der Lesefortschritt wirkt wie ein Instrument, nicht wie ein Balken |
| Eigener `:focus-visible`-Ring | Tastaturführung sichtbar (DESIGN.md-Pflicht, vorher nur geerbt) |
| Dark-Mode-Fassung für jede neue Fläche | `defaultTheme: auto` bleibt vollwertig |

**Wache** (`scripts/mini_toc_premium_guard.py`, in `npm run test:toc`):
14 Verträge (V1–V14) – Vollständigkeit ohne `slice`-Deckel, stehende Kopfzeile,
eigener Scrollbereich, Lesemarke, Geometrie an `--main-width`, Ruhzustand,
Breakpoint < 1280 px, Druck, Reduced Motion, Dark Mode, Materialtiefe,
Fokus-Ring, keine Inline-Farben im JS, kein Line-Clamp.

Der Selbsttest **sabotiert die Wache mit sechs Rückfällen** (u. a. genau dem
9er-Deckel und der Pixelzahl 1120 von damals) und verlangt, dass sie jeden
einzelnen bemerkt. Eine Wache, die nur „grün“ sagen kann, ist keine Wache.

---

## Verifikation

| Prüfung | Ergebnis |
|---|---|
| `hugo v0.164.0 --minify` | fehlerfrei, 205 Seiten |
| `python3 scripts/faktenfrische.py --selftest` | 20/20 Fälle grün |
| `python3 scripts/mini_toc_premium_guard.py --selftest` | Bestand grün, 6/6 Sabotage-Proben erkannt |
| `npm run test:toc` | 48/48 Prüfungen + Wache grün |
| `python3 scripts/layout_audit.py` | 2 411 Links, 0 kaputt; DOM im Budget |
| `python3 scripts/schema_seo_gate.py` | 0 harte Funde (jetzt inkl. `citation`) |
| `python3 scripts/seo_cockpit.py` | 213 Seiten, P1/P2/P3 = 0 |
| `python3 scripts/seo_audit.py` | 0 Probleme in 40 Artikeln |
| `python3 -m unittest discover -s scripts/tests` | 963 Tests grün (Siegel im selben Commit neu signiert) |

---

## Was bewusst NICHT passiert ist

- **Kein automatischer Eingriff in Artikeltexte.** Der Auftrag „fachlich
  optimieren“ wäre mit Auto-Rewriting schneller erledigt gewesen – und hätte
  die erste falsche Zahl unbemerkt live gestellt. Fachliche Befunde bekommen
  einen Menschen, die Belegkette bekommt die Maschine.
- **Keine Layout-Umbauten an anderen Flächen in der Basis.** CLAUDE.md verlangt
  dafür den Varianten-Weg (`assets/css/varianten/` + Messung + Freigabe). Die
  Arbeit hier betrifft eine Komponente (Artikel-Navigation) und eine neue
  Komponente (Quellenbox) – beides ohne Eingriff in bestehende Raster.
- **Keine neuen Meta-Texte „auf Verdacht“.** Die Gates waren grün; erfundene
  Verbesserung ist Drift, nicht Qualität.

## Nächste sinnvolle Schritte

1. `PUTER_AUTH_TOKEN` im Repo-Secret prüfen – ohne ihn läuft die Belegkette
   deterministisch, aber ohne Claudes Fachbefunde.
2. Nach den ersten CI-Läufen die GEO-Lücken-Liste im Report abarbeiten: FAQ-
   Abschnitte fehlen häufiger als Tabellen.
3. Newsletter-Ausgaben mit derselben Belegkette versehen (die Quellen liegen
   dann bereits im Frontmatter der verlinkten Artikel).
