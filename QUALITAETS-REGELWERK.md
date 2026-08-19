# 📕 QUALITÄTS-REGELWERK – FranksFinanzcheck

**Version:** 1.0 · **Stand:** 10.08.2026 · **Geltungsbereich:** gesamtes Blog
(alles unter `content/`, die Startseite, die Skripte in `scripts/`, die
Workflows in `.github/workflows/`)

> **Zweck in einem Satz:** Jede Lektorats-Regel ist hier genau einmal
> dokumentiert – mit Entscheider, Schutzzonen und Selbstheilung. Kein
> Fehler darf sich jemals zweimal wiederholen.

---

## 🗺️ Die Qualitäts-Kette (Inkraft in Content-Engine v2, Phase 2)

Reihenfolge ist **absichtlich** so (erst Struktur, dann Sprache, dann Stil,
dann Länge – und Brand-Guard immer NACH Emoji-Guard, damit das Marken-Lock
das letzte Wort hat):

```
KI-Artikel (engine_generate.py)
   │
   ├─► profi_polish.py          KI-Feinschliff
   ├─► fix_linebreaks.py        Zeilenfluss (Markdown)
   ├─► fix_spaces.py            Leerzeichen-Hygiene
   ├─► spellcheck.py            Rechtschreibung (Hunspell, de-DE)
   ├─► grammar_check.py         Grammatik (LanguageTool)
   │
   ├─► 🔠 casing_guard.py       Akronym-/Marken-Schreibweise (C1–C3)
   ├─► 📏 dash_guard.py         Strich-Typografie (R1–R8) + KI-Stil (S1/S3)
   ├─► fix_dash_breaks.py       Umbruch NACH Gedankenstrich
   ├─► fix_heading_breaks.py    Teilüberschrift:<br>-Umbruch
   ├─► 🧩 compound_guard.py     Komposita („Preisgarantie Gas"-Falle)
   ├─► 😀 emoji_guard.py        Touchpoints & Text-Hygiene (E1–E5)
   ├─► 🔒 brand_guard.py        MARKEN-LOCK (unantastbar, siehe unten)
   ├─► 📏📝 length_guard.py     Längen-Korridore + KI-Selbstheilung
   │
   ├─► profi_text_check.py      Stil-Gate (Schwelle)
   ├─► readability_check.py     Lesbarkeits-Gate (> 75)
   ├─► check_titles.py          Titel-Gate
   ├─► generate_covers.py       Titelbilder (Manifest-selbstheilend*)
   ├─► check_uniqueness.py      Duplikat-Audit
   ├─► affiliate_link_check.py  Check24-/Tarifcheck-Link-Pflege
   ├─► check_covers.py --fix    *Cover-Stale-Erkennung über Manifest
   └─► generate_kurzantworten.py  💡-Box „Kurz & knapp"
```

Ausführung aller Regeln: **niemals blockierend** (`|| echo "nicht kritisch"`).
Fehler dürfen nie die Veröffentlichung stoppen, aber sie werden sichtbar gemacht.

---

## 🔠 Regeln im Detail

### casing_guard.py – Akronym-Orthografie (Duden, deterministisch)
| Regel | Inhalt | Beispiel |
|---|---|---|
| C1 | Kanonische Akronym-Form (auch Satzanfang) | `dsl` → `DSL`, `etfs` → `ETFs`, `cashback` → `Cashback` |
| C2 | Durchkopplung Akronym + Nomen | `DSL Tarif` → `DSL-Tarif` |
| C3 | Marken-Durchkopplung | `Check24 Gasvergleich` → `Check24-Gasvergleich` (Marken: Check24/CHECK24, Tarifcheck, Verivox, Idealo) |

### dash_guard.py – Strich-Typografie (Duden + Web)
| Regel | Inhalt |
|---|---|
| R1 | „ Wort - wort" (Minus als Gedankenstrich) → „ – " |
| R3 | US-Geviertstrich „—" → „ – " |
| R4 | „--"/„---" zwischen Wörtern → „ – " (Wort-Anker; schont Zeilenanfänge, Fences!, HR) |
| R5 | Zahlenbereiche → Halbgeviert ohne Leerzeichen: `10-20 Euro` → `10–20 Euro` (Kettenfest: `50-30-20` → `50–30–20`; Schutz: ISO-Daten, „5-jährig") |
| R6 | Asymmetrische Leerzeichen am Gedankenstrich |
| R7 | Satzende-Kollision: „. – Und" → „. Und"｜„. – dann" → „ – dann" |
| R8 | Imperativ am Satzanfang: „. Ließ das" → „. Lies das" (enge Negativ-Kontrollen) |
| S1/S3 | KI-Schiedsrichter (nur `--ai`): Doppelschub-Umformulierung, Strich-vs-Komma – mit 4-fach-Verifikation |

### compound_guard.py – Komposita (SEO-Keyword-Falle)
Regelwerk in `COMPOUND_RULES` oben im Skript. Aktuell: `Preisgarantie Gas|Strom|DSL`,
`Zinsen Tagesgeld|Festgeld`, `Sparplan ETF`, `Tarif DSL`, `Konto Giro`.
Kandidaten-Radar (Kopf-Nomen + Themen-Nomen) landet im Report; `--ai` urteilt selbst.

### emoji_guard.py – Touchpoints & Text-Hygiene
E1 Marken-Emoji an Startseite auto-ergänzen (Themen→Emoji-Mapping, Default 💰) ·
E2 Meta-Description bleibt Emojig-arm · E3 Anti-Overuse (max 2) · E4 Mojibake → Auto-Reparatur ·
E5 Zero-Width-Zeichen (U+200B…) → immer löschen.

## 🏛️ Hoheitskarte (wer regelt was — einmalig festgelegt 11.08.2026)

Bei zwei parallel gebauten Längen-Systemen gilt ab jetzt:

| Klasse | Hoheit | Korridor | Mechanik |
|---|---|---|---|
| **Posts** (normal) | `check_length.py` (Generierungs-System) | Floor **1.000** Wörter via `LENGTH_MIN_WORDS` (Repo-Variable, Default in Engine) – Optimum 800–1.400 | Heilung zur Generierungszeit |
| **Pillar-Seiten** | `length_guard.py --scope pillar` (dieses System) | **2.500–4.000 Wörter**, Heil < 1.800 | Engine + Wochen-Backlog (3/Wo.) |

Damit: Keine Doppel-KI-Kosten, keine Ping-Pong-Loops, getrennte Strenge.
Dash-Guards (dash_guard.py ≠ fix_dash_eol.py/fix_dash_und.py) koexistieren
bewusst – nachgewiesen disjunkte Muster.

---

### length_guard.py – Längen-Korridore (Affiliate-Profi)
| Typ | Ziel | Warnung | Selbstheilung unter … | **Zeichen-Empfehlung (Dauervorgabe)** |
|---|---|---|---|---|
| posts | 1.200–2.200 Wörter | < 1.000 | 900 | **6.000–10.000 Zeichen** Fließtext |
| pillar | 2.500–4.000 Wörter | < 1.800 | 1.800 | ≈ 17.500–28.000 Zeichen |

### 📌 DAUERVORGABEN Veröffentlichung (festgelegt 19.08.2026 – verbindlich)

- **Blog-Launch: 08.08.2026.** Kein Artikel darf je ein Datum vor dem 08.08.2026
  tragen. Der vor dem Launch datierte Alt-Bestand (36 Posts) wurde am 19.08.2026
  **dauerhaft gelöscht** (inkl. Covers, Manifest, Pins, Fingerprints, interner Links).
- **Veröffentlichungsintervall: nur Mo, Mi, Fr – 2–3 Artikel pro Publikationstag.**
  Haupt-Slot 08:10 MESZ (06:10 UTC), Fallback-Slots 16:10/19:40 MESZ.
  Umgesetzt in `.github/workflows/content-engine-v2.yml` (cron `10 6 * * 1,3,5`)
  plus hartem Wochentags-Guard in `scripts/engine_generate.py`
  (`PUBLICATION_DAYS = {0,2,4}` – gilt auch für manuelle Läufe;
  Notfall-Override `FORCE_PUBLISH_ANY_DAY=1`). Tagesmenge:
  `MIN_ARTIKEL_PRO_TAG` (Default 2) bis `MAX_ARTIKEL_PRO_TAG` (Default 3);
  die Engine erzwingt per Dauervorgabe-Floor mindestens 2 (der Workflow-
  Legacy-Fallback „1“ kann die Kadenz nicht drücken). Empfohlen:
  Repository-Variablen `MAX_ARTIKEL_PRO_TAG=3` / `MIN_ARTIKEL_PRO_TAG=2`.
  Definition siehe `CADENCE-REPORT.md`.
- **Bestands-Kadenz: Der Blog zeigt Artikel nur an Mo/Mi/Fr.** Am 19.08.2026
  wurden 38 Off-Kadenz-Posts vollständig gelöscht (08.08. Sa ×2, 08.09. So ×2,
  08.11. Di ×2 + 32 Evergreen-Posts vom 09.08. So) – inkl. Covers, Manifest,
  Pin-Queue, Fingerprints, Affiliate-Report, IndexNow-Log und interner Links.
  Verblieben: 6 Posts, je 2 an Mo 08.10., Mi 08.12. und Fr 08.14.
- **Empfohlene Zeichenlänge pro Blogartikel: 6.000–10.000 Zeichen** Fließtext
  (≈ 800–1.400 Wörter; empirisch: Median 9.124 Zeichen bei 6,96 Zeichen/Wort).
  Ausgewiesen und überwacht von `check_length.py` (Konstanten `OPT_CHARS_MIN/MAX`,
  Env `LENGTH_OPT_CHARS_MIN/MAX`); harte Gates bleiben wortbasiert (Hoheitskarte oben).

Heilung = KI ergänzt **Mehrwert-Module** (kein Fülltext!): Rechenbeispiel mit Jahr,
typische Fehler, Checkliste, +2 FAQ – eingefügt vor Fazit/Disclaimer, nach Gates.
Neue Artikel: Engine (`--new-only`). Rückstand: Wochen-Audit (`--backlog 3`, Pillars zuerst).

| D10 | CTA-Kasten (gelb) <-> /go/-Gateway-Kontrakt in custom.css | Auto-Heilung |
| D11 | Hover-Transparenz: /go/-Links tragen Tooltip (Ziel + Werbung) | Auto-Heilung (Hook-Re-Write) |

### design_guard.py + design_visual.py – 🎨 Verlagshaus-Design-QA (neu 11.08.)
| Regel/Modul | Inhalt | Lohn/Macht |
|---|---|---|
| Statisch (Guard) | D1 CLS-Bilder dims, D2 alt-Text, D3 Heading-Springe, D4 vage Links, D5 font-display, D6 externe Calls (KRITISCH – Privacy!), D7 doppelte IDs, D8 lang/viewport | Auto-Fix Alt-Text |
| Visuell (Visual) | pHash-Schnappschüsse (Desktop+Mobile) vs. Baseline; Regression -> Issue (Dedupe), Baseline heilt sich mit moderater Drift | Screenshots NIE im Repo (64-Bit-Hashes!) |

Echtes Verfahren wie bei Grossverlagen (Percy/Chromatic): nur deutlich leichter.

### math_guard.py – 🧮 Faktencheck-Schreibtisch (neu 11.08.)
| Regel | Inhalt | Automatik |
|---|---|---|
| M1 | Rate x Zeiteinheit x Dauer = Endbetrag **nachrechnen** („5–10 €/Tag x 14 Tage = 70–140 €") | Auto-Fix (Behauptung, letztes Zahlenpaar); weiche Formen (rund/ca.) nur melden |
| M2 | Prozentformeln („X % von Y") | pruefen |

Ausloeser: Artikel „Urlaub mit Kindern" (Beispielrechnung korrekt; dafuer
der Schutz fuer künftige KI-Halluzinationen, die erfahrungsgemaeß bei
Geldrechnungen eklatant sind).

### lektor_guard.py – ✒️ Verlags-Lektorat (Zeitungs-/Buchniveau, neu 11.08., Zielredaktion am Abend)
| Regel | Inhalt | Automatik |
|---|---|---|
| L1 | Wortduplikate („das das") | Auto-Fix (sichere Liste) + Komma-Lookbehind bei Artikeln |
| L1rel | Relativkaskaden „die die meisten" | NIE auto – korrektes Deutsch! (nur Report) |
| L2 | Füllphrasen (Bürokratie-Deutsch) mit Kanon-Ersatz | Auto |
| L3 | Personenkonsistenz Sie↔du | **Nur KI** (--ai) mit Grammatik-Gate (du+Verb-muss) |
| L4 | Ausrufezeichen-Inflation „!!" -> „!"; >3 pro Artikel = Werbeton-Radar | Auto + Report |
| L5 | Echo-Wörter (>4 Buchstaben 2× im Satz) | Report; KI-veredelt mit --ai + Gates |
| L6 | Stale-Jahre („Stand: 2023") | Report |
| L7 | Nominalstil-Radar (>4 Behörden-Nomen -ung/-heit/-keit je Absatz) | Report |
| L8 | Weichmacher-Dichte (>6 Konjunktive könnte/sollte/müsste je Artikel) | Report |
| L9 | Satzanfangs-Echo (gleiches Wort startet 3+ Sätze eines Absatzes) | Report |
| L10 | Zahlenschreibweise Duden (2–12 ausgeschrieben: „3 Tipps"→„drei Tipps"; NIE vor %, €, Euro) | Auto |
| L11 | Werbe-Intensivel („brutal günstig"→„besonders günstig", „sensationell"→„beachtlich"…) | Auto-Kanon |
| L12 | Longsatz-Alarm (>35 Wörter) | Report |

**🛡️ Sabotage-Schutz:** 12 eingefrorene Lektorats-Fälle (inkl. Negativ-Fallen wie
„Spare 3 Euro bleibt Ziffer") prüfen vor jedem Einsatz die Regelmaschine selbst –
Abweichung = Exit 2, keine Zeile wird geschrieben. **Verdrahtung:** Engine Phase 2
(`--fix --ai --new-only`, Lektorat bei der Geburt) + **wöchentliche Archiv-
Gesamtsichtung** im Weekly-Audit (auto-committet). Idempotent (Convergence getestet).

### brand_guard.py – 🔒 Marken-Lock (höchste Stufe)
Sperrt in `data/brand_lock.yaml` enthaltene hugo.toml-Bausteine: Willkommens-Titel/Tagline,
Meta-Description, Affiliate-Disclaimer. **Jede Abweichung wird zurückgerollt.**
Absichtliche Änderung: entweder `hugo.toml` + einmal `python3 scripts/brand_guard.py --set-current`,
oder einfach den Wert in `data/brand_lock.yaml` ändern und commiten – die Automatik folgt.

### affiliate_marketer.py – 🎯 CTA-Routing mit Selbsttest-Batterie (Sabotage-Schutz)
Steuert die 💡-Schnell-Tipp-Box thematisch korrekt (`route_for()` + `DEEP_HINTS`,
Reihenfolge = Spezifität; Register-Gate gegen 404) und retargetet jede falsch
geroutete Box automatisch auf die Ideale-Route. **Sabotage-Schutz:** `run_selftest()`
prüft vor JEDEM Lauf 18 kanonische Routing-Fälle (DSL→dsl, Elementar→hausrat (!),
Depot→tagesgeld, Gas→gas …). Schlägt auch nur einer fehl, bricht der Marketer mit
Exit 2 ab, bevor eine Datei angefasst wird – Mensch oder KI kann das Routing nicht
mehr „aus Versehen" verbiegen.

### affiliate_health.py – 🩺 E2E-Wächter mit Kontrakt + Selbstheilung (haerteste Fassung)
Prueft jede Route **end-to-end**: komplette Redirect-Kette bis zur finalen
Landeseite (nicht nur Tracker-Hop 1!), Endseite < 400, richtige Kategorie per
Keyword-Vertrag (`CONTRACT`, eingefroren), PID-Pins (`pid=80968&aid=18` /
`partner_id=47086&ad_id=15`), Gateway-Drift, CTA-Abdeckung. tarifcheck-WAF-403
(Datacenter-Bots) wird korrekt als erwartbar bewertet.
**Selbstheilung:** tote/falsch geroutete Ziele werden automatisch auf den
sicheren Homepage-Fallback (PID bleibt!) umgebaut, Gateways neu generiert,
Issue an Frank (Label `affiliate-health`). **Sabotage-Schutz:** 14 eingefrorene
Urteils-Faelle testen die `verdict()`-Logik selbst – Abbruch mit Exit 2 vor
jeder Schreibaktion.

---

## 🛡️ Schutzzonen (gelten über allen Guards)

1. **Front-Matter ist SEO-Safe-Zone** (Keywords bleiben; Titel-Semantik geschützt).
2. **URLs/Slugs sind sakrosankt.** Veröffentlichte URLs ändern sich NIE.
3. Code-Fences, Inline-Code, Markdown-Links, Bild-URLs, HTML-Kommentare: unantastbar.
4. Listen-/Zitat-Marker und Überschriften-Hashes bleiben (Inhalt hinter dem Marker wird geprüft).
5. Eigennamen-Whitelists (z. B. „Franks Finanzcheck").
6. Bekannter Blog-Eigenbau: geklebte Front-Matter-Fences (`---Text`) werden von allen
   Guards korrekt aufgedröselt (Fence bleibt, Text wird geregelt).

---

## 🩹 Selbstheilungs-Matrix

| Was schiefgehen kann | Wer heilt es |
|---|---|
| Schwache KI-Antwort → kein Artikel | Engine v2 (3-Ebenen-Fallback) |
| Artikel zu dünn | length_guard (KI-Module, Gate-verifiziert) |
| Titel geändert → Cover alt | check_covers Manifest-Abgleich (--fix) |
| Pinterest-Token läuft ab | pinterest_auth.py (Continuous Refresh, AES) |
| Push-Race zwischen Bots | Rebase-Guards + Concurrency in allen Write-Workflows |
| Bot komplett stumm | bot-watchdog → Issue |
| Website down | uptime-check → Issue (auto-schließend!) |
| Workflow-Fehler | alert-on-failure → Issue (Abdeckung: alle Kern-Workflows) |
| Text-Regelverstoß | die sechs Guards oben (korrigieren selbst) |
| Marken-Text verändert | brand_guard (Lock-Reset) |
| Actions veraltet | Dependabot + Auto-Merge (Patch/Minor auto) |

## 📁 Reports (werden bei Läufen kommittiert)

`LENGTH-REPORT.md` · `DASH-REPORT.md` · `COMPOUND-REPORT.md` · `EMOJI-REPORT.md` ·
`CASING-REPORT.md` · `BRAND-REPORT.md` · `SEO-REPORT.md` · `LAYOUT-REPORT.md` ·
`BOT-STATUS.md` · `ENGINE-STATUS.md` · `PIN-STATUS.md` · `SOCIAL-STATUS.md` ·
`AFFILIATE-REPORT.md` · `BACKLINK-REPORT.md` · `GRAMMATIK-REPORT.md` · `META-REPORT.md`

## 🛠️ Playbooks (typische Eingriffe)

| Situation | Vorgehen |
|---|---|
| **Neue Regel festnageln** (z. B. neue SEO-Falle) | In `compound_guard.py` / `casing_guard.py` im Regel-Block oben ergänzen. Fertig – ab nächstem Lauf aktiv. |
| Engine manuell anstoßen | Actions → „Content-Engine v2" → Run workflow |
| Selbstheilung pausieren | Workflow im Actions-Tab deaktivieren (Kill-Switch) |
| Guard-False-Positive | Ein melden via Issue; Regel im Skript weicher machen; `HISTORY`-Dateien in `data/` zeigen Verhalten |
| Max. Artikel/Tag ändern | Repo-Variable `MAX_ARTIKEL_PRO_TAG` |
| Wassertemperaturen | `BOT-STATUS.md` / `ENGINE-STATUS.md` jederzeit auf der Repo-Seite sichtbar |

## 🧾 Änderungsjournal (nur Qualitäts-Regelwerk)

- **11.08.2026 (15):** L14 Unidiom-Fangsatz (Frank-Fund „Jahresetag"):
  Holzrige KI-Komposita-Neubildungen bekommen einen Kanon (auto-fix,
  Fall-kontrolliert) – Pflege nur in L14_KANON (lektor_guard.py). Neu
  geborene Faelle meldet das Compound-Radar, Aufnahme hier durch
  Redaktion. Selbsttest nun 16 Faelle.
- **12.08.2026 (5):** Marken-Band statt Punktewand (Frank: „Die Punkte
  im Hintergrund stoeren"). Neues Footer-Design: tiefes Emerald-Band +
  goldene Fuehrungslinie + „FranksFinanz" weiss + „check" gold. 77 Covers
  neu. C2-Gate-Verifikation: Brand-Staerke jetzt 0.034 gold-Pixel-Anteil
  (vorher 0.0645 Chip-Rahmen) - beide Designs beat die Schwelle seit
  check_covers 2x sicher. Integritaets-Siegel inkl. generate_covers.py
  + check_covers.py neu gelockt (18 Dateien). Aenderungen am Marken-Look
  verlangen jetzt --set-current (siehe ANLEITUNG).
- **12.08.2026 (4):** Profi-Affiliate-Rundgang abgeschlossen (Frank):
      AM7 Mid-CTA eingefuehrt (In-Text-CTA nach Wort-Mitte, C24-rule inklusive),
      integrity_guard.py als SHA-256-Siegelschloss ueber 16 Kerndateien
      (Kritisch=fest stopft, Fest=meldet Sichtung), Deploy-Preflight gegen
      Merge-Marker erweitert (nie wieder roter Build wegen '<'), blog_doctor
      auf 13 Wachen inkl. Lock. ANMERKUNG: Umami bleibt deaktiviert bis die
      Website-ID eingetragen wird (Frank-Handlung, siehe ANLEITUNG-UMAMI).
- **12.08.2026 (4):** Brand-Chip auf Covern (Frank: „Markenname nicht
  scharf genug abgebildet"): gold-gerahmter Chip, weisser Text + goldener
  „check"-Ausweis (44 px Inter Bold), Punkte nie mehr in der Textzone.
  check_covers.py C2: Brand-Staerke pro Cover pixelbeweis-bar (0,0645 vs.
  0,002 bei leerem Band) + Selbstheilung per --slug --force-Regen. Alle 77
  Covers neu, Integritaets-Lock neu signiert.
- **12.08.2026 (3):** Der Merge-Marker-Vorfall (Deploy-Todestuetze): Die
  Engine-Kettenliessen ungelöste „<<<<<<< HEAD” in mehrere die Artikelfronts.
  W7 Marker-Jaeger in workspace_guard.py (findet + heilt mit material-
  Mehrheitswahl, dokumentiert). Deploy buildet wieder. Zusatz verteilt:
      spellcheck Whitelist +69 (Marke, Schufa, SEPA, Broker-Vokabeln),
      „begruendungslos"-Adverb Schutz, 5 Split-Link-Unfalle (internal-linker
      Wortspaltung) chirurgisch geheilt, oss-version Engine Skopus jetzt
      inkl. static/images/covers/ (baumitgezwungen Cover-Bote).
- **12.08.2026 (2):** Blog-Doktor installiert (Frank-Befehl „Selbstheilung
  auf Profi-Level fuer die GESAMTE Blogautomatik"): blog_doctor.py fuhrt
  ALLE 12 Wachen in kanonischer Ordnung mit --fix durch, bricht bei einem
  Exit 2 (Sabotage) sofort ab und dokumentiert jede Exit-Signatur
  (0 = sauber, 1 = Fund erlaubt, 2 = Stoppsirene). Ausserdem eigene
  Selbsttest-Phase (7 Faelle) mit Exit 2 vor JEDER Visite. Verankerung:
  eigene Wochenvisite Mi 08:45 MESZ + letzter Beweis in der Engine-Geburt.

- **12.08.2026 (1):** Mittwochs-Domino vorab eingefangen & verhindert:
  spellcheck hard-exitete (141 unbekannte Funde – u.a. der eigene Markenname!)
  und riss die gesamte seo-weekly-Kette (Stufen dahinter kamen nie).
  Reparatur-Wall: 67 Whitelist-Zuwaeche (Marke, Schufa, SEPA, ETF Welt),
  Rechtschreib-Schritt jetzt continue-on-error, Pinterest gaeltig gemacht als
  sauberer Skip bis zum App-Trial (kein Tages-Rot mehr). Plus: ‚vergessene
  Fitnessstud'io-Mitgliedschaft“-Zeile restauriert (Haesslicher interner Linker-
  Bug). workspace_guard bekam seinen Selbsttest (10 Faelle, Exit 2).
- **11.08.2026 (16):** L15 Gedankenstrich-Bruch (Frank „Zeilenumbruch prüfen",
  ETF-Kinder Schritt-5): Engine-Zeilenumbruch-Stil hinterließ Zeilenenden
  „… steuerfrei –  ⏎  der groesste …". jetzt LOT lokalisiert: 35 Bruche
  in 19 Dateien auto-fusioniert, Selbsttest 17, Body-only (FM/Code/Listen
  bleiben). Workflows brauchte es nicht einmal – Lektor laeuft ja ueberall.
- **11.08.2026 (15):** Nachts gehört die Tabellen dem Schlafwandler:
  Frank erwischte den abgerissenen Link-Mitten-In-Zelle-Bruch in der
  ETF-Kinder-Tabelle. Das Zahlenmodell werde jetzt auch wirklich bewiesen
  (50 €/Monat, 6 %, 19 Jahr -> exakt 19.400 €; Appeluft: „halbieren" ->
  „mehr als verdreifachen" bewiesen). Neuer table_guard.py (T1 Spalten-
  Kongruenz, T2 Bruchform-Heilung praezis bewiesen byte-gleich, T3
  Zell-Schutt, T4 absteigende Bereiche), 6 Faelle Selbsttest, verdrahtet
  in Engine + Weekly-Audit.
- **11.08.2026 (14):** Inter-Aera ausgerufen (Frank-Wahl nach Font-Palette):
  Ueberschriften UND Covertext = Inter Bold. Montserrat-Thin-Klone entfernt;
  Head-CSS referenziert nur noch Inter (Variable, 400..700) + Playfair-Akzent.
  76 Covers in Inter neu gebacken; Cover-Generator haengt hart an
  static/fonts/Inter-Bold.ttf (Exit 2 statt Stille). font_guard Vertrag auf
  Inter aktualisiert, Wiederverdrahtung in Engine + Wochenaudit.
  R796-Vorgespraech: zwei Vorab-Font-Commits wurden mit git revert sauber
  zurueckgenommen (kein Verlust, Regeln bewahrt).
- **11.08.2026 (13):** Link-Zivil-Katastrophe gefunden & komplett geheilt:
  Die Engine hatte Dutzende interne Links mit ABGEKNICKTEN Slugs gebaut
  (z. B. …/7-gewohnheiten-finanzielle-freih/) sowie Pillar-Links in die
  falsche Sektion gelegt (../../posts/frugalismus/ statt ../../pillar/).
  Neuer hartnäckiger Waechter link_guard.py (V1/Ziel-Register,
  V2/go-Register, 6-Faelle-Selbsttest, Sektions-Korrektur), ~86 Links
  geheilt inkl. 1 Handchirurgie (zersplitterte Markdown-Zeile). Tot seit:
  beiden Engine-Geburtskette (new-only) UND Weekly-Audit (Vollbestand).
- **11.08.2026 (12):** Archiv-Roundtrip abgeschlossen (alle deterministischen
  Auto-Regeln 0 Rest-Funde; Radar: 148 L8/166 L5 bewusst delegeiert) +
  neuer wochentlicher KI-Lauf „Redaktions-Politur" (Freitag 17:00 MESZ,
  --ai-budget=3 nach Fund-Dichte, Gates aktiv, Franks Quota-Regel).
- **11.08.2026 (11):** Betriebspruefung Frank: vier Massnahmen ausgefuehrt:
  13a. Lektor L13 Doppel-Anlauf-Detektor (KI-Verschleppungen „Ddiebesten" ->
  Report; Selbsttest-Faelle 14+15 inkl. Aachen-Negativfall);
  13b. seo-weekly bekommt die komplette Textbatterie als Anschluss-Stufe
  (Mittwoch-KI-Edits schleichen sich nicht mehr ein);
  13c. deploy.yml mit Pfad-Filter: Nur Nutzersichtbares baut die Seite
  (Report-/Bot-Commits ohne Rebuild);
  13d. FrankAutoOps-Report 08:00 → 07:35 MESZ (raus aus dem Push-Rennen).
- **11.08.2026 (10):** Grossstoerfall-Schlussbericht: Die Quality-Score-
  Inline-Zelle in der Engine bewertete ALLE Posts und parkte „human-review"-
  Faelle — die Kombination Schablonen-Blindheit (Schnell-Tipp/Disclaimer nicht
  ausgeklammert, uniqueness 0.0) + /go/-Blindheit (has_link false, Affiliate-Part 0.5)
  zwang 0.80 ueberall (CI = 42 offline). Fix: quality_score.py erkennt
  /go/-Links + streift Boilerplate vor n-Gramm; Workflow-Skopus auf „nur heute
  geboren" + CIRCUIT-BREAKER (>3 Park-Vorgaenge = verweigert + Alarm statt
  Ausloesung). 38 Artikel zurueckgeholt, 4 legitime Entwürfe bleiben.
- **11.08.2026 (9):** Masken-Kollaps gefunden & geheilt: gieriges Zitat-Regex in
  lektor_guard.mask() fraß Platzhalter verschachtelter Masken (md-Link zwischen
  zwei Zitaten → Link verloren, \x00-Leiche in der Datei). Fix: nicht-gierige
  Klasse + LIFO-unmask mit Fixpunkt; gleiche Panzerung in dash/casing/compound/
  unmask. Neuer Selbsttest-Fall 13 friert den Regressionsfall ein. Zwei seit
  Tagen korrumpierte Artikel (dns-server, balkonkraftwerk) chirurgisch geheilt.
- **11.08.2026 (8):** Cover-404-Fix: AVIF-<source>-Elemente in cover.html +
  extend_post_content.html werden nur noch emittiert, wenn die Datei echt
  existiert (os.FileExists-Gate). Grund: lokal ohne pillow-avif-plugin
  geborenes Cover referenzierte nie erzeugte AVIFs → 404 auf Karte/Artikel.
  check_covers.py (9-Varianten-Vertrag) bleibt Suspender; CI erzeugt AVIF
  vollständig (pillow-avif-plugin im Engine-Step vorhanden).
- **11.08.2026 (7):** Zielredaktions-Erweiterung Lektorat (Frank-Auftrag):
  L7 Nominalstil-Radar, L8 Weichmacher-Dichte, L9 Satzanfangs-Echo,
  L10 Duden-Zahlenschreibweise (Auto, 13 Funde im Archiv geheilt),
  L11 Werbe-Intensivel-Kanon, L12 Longsatz-Alarm + 12-Faelle-Selbsttest
  (Sabotage-Schutz) + woechentliche Archiv-Sichtung im Weekly-Audit.
- **11.08.2026 (6):** Route 19 `hunde` (Tarifcheck Hundekrankenversicherung,
  deep=hundekrankenversicherung) nach Frank-Entscheid aufgenommen — Fund via
  UNREGISTERED-deep-Report; Tier-Artikel oben+unten auf /go/hunde/ geroutet.
  Hinweis-Auto-Tune: Tierversicherung/Hundeversicherung/Katzenversicherung
  routen jetzt thematisch. Deep-First gilt per Auto-Deep im Shield dauerhaft.
- **11.08.2026 (5):** Frank-Bestaetigung aus dem Partnerprogramm eingefroren:
  fluege = offizieller Deep `pauschalreisen-vergleich&cat=9` (Homepage-Landung
  gilt jetzt als Sabotage-Falle im Kontrakt!); tagesgeld = `c24bank&cat=14`
  (es existiert kein eigener Tagesgeld-Link – C24 Bank ist die Heimat).
  C24-Nennungs-Regel ueberall: Tooltips (D11-Canonical + render-link),
  Gateway-Seiten-Text (GO_NAMES im Shield), kuenftige CTA-Anker (Marketer).
- **11.08.2026 (4):** Affiliate-Grossreparatur + E2E-Haertung. Zwei Deeps waren
  TOT (kreditvergleich, tagesgeldvergleich → 404 auf der Endseite; alter Waechter
  pruefte nur Hop 1!). Neu: kredit→kredit-vergleich, tagesgeld→c24bank (C24 =
  Geldanlage-Heimat), fluege→ehrlicher Homepage-Fallback (kein Flug-Deep am
  Tracker, TODO Dashboard). affiliate_health.py jetzt E2E mit Kategorie-Vertrag,
  Auto-Heilung auf sicheren Fallback und 17-Faelle-Selbsttest.
- **12.08.2026 (7):** INTERNAL-LINK-LECK ENTSCHAERFT (Root-Cause-Serie):
  Komplett-Messung zeigte o 1.1 interne Links/Artikel im HTML, obwohl
  im Markdown 5.6 standen. DREI Ursachen: (1) internal_linker.py kuerzte
  Slugs um 3 Zeichen (`tgt_fn[:-3]` – „wechseln"→„wechs" → 404), (2) die
  Inserts arbeiteten sequentiell mit Alt-Offsets → Verschiebe-Kaskade,
  Chaos-Texte wie „Zw[eitwagenre](…)gelung" entstanden – 21 Chaos-Zeilen
  in meiner eigenen heutigen Testrunde (rollbackt!), (3) der Render-Hook
  (render-link.html) gab relative Markdown-Links WORTWOERTLICH aus →
  Browser versuchte /posts/posts/xyz/ → 404 unsichtbar. FIXES:
  - Linker: nie kuerzen (tgt_fn ist sauberer Slug), Inserts geplant
    rueckwaerts einfuegen, anchor_ok-Qualitaetsfilter (keine „es sich"
    -Anker mehr), Deckel 9/Artikel (kein Link-Spam), used_targets prueft
    auch bestehende Datei-Links (kein Dup-Ping-Pong mehr).
  - render-link.html: relative Posts/Pillar-Links werden absolut-site-
    kanonisch (/posts/slug/) ergaenzt um doppelte-Slash-Saeuberung.
  - NEU: scripts/link_density_guard.py (C1 Korridor-Zaehlung 2-9,
    C2 Ziel-Duplikat-Heilung ab >3 Nennungen mit Anker-Dup-Regel, C3
    Header-Link-Relikt-Detektor, 5-Finger-Selbsttest) in blog_doctor-
    Kette eingefuegt (D-Ordnung). Erfolg: ø1.1 → ø5.5 interne Links.
  - 17 semantisch falsche „pro Monat"-Links (Preiseinheiten in Tabellen
    sollten keine Links tragen) entlinkt (Text blieb).
  - Repo-Repair-Beweisstuecke entfernt: 2 alt-kaputte Zeilen in
    frugalismus-im-alltag (Dauer-Klammer-Bruch + Ueberschrift mit
    Link-Rest) geheilt.
  Integrity-FEST: 26 → 28 Dateien (internal_linker, link_density_guard).
  BEKENNENDE LEKTION: Mein basename()-Bug (Trailing-Slash) loeste einen
  Phantom-Alarm aus → Version control ERST prüfen, dann handeln; außerdem
  zeigt das Desaster: Messmethoden-Dokumentation (wie „ø interne Links")
  muss in KLARTEXT definiert sein (HTML vs Markdown – wir zaehlen jetzt
  HTML nach Build, nicht mehr MD-Blindheit).
- **12.08.2026 (9):** PLAGIAT-KANZLEI + CONTENT-AUDIT (Frank: „weltbeste
  Plagiats-/Auditor-Automatik"). Zwei neue Wachen in blog_doctor-Kette:
  scripts/plagiat_guard.py (P1 Shingle-Jaccard 8-Wort-Fenster, P2 Duplikat-
  Saetze cross-artikel, P3 Boilerplate-Quote, P4 FINGERPRINT-REGISTRY mit
  SHA-256 + SimHash-64 + Zeitstempel = URHEBERSCHAFTS-Beweis, P5 Klon-
  Quarantaene bei Jaccard > 0.55: juengerer Artikel → draft:true
  (reversibel). Selbsttest 8 Faelle. Fund: 0 Klone, 0 Verdacht, 1
  legitimes Satz-Duplikat (versicherungstypisch). Boilerplate-Kanon
  erweitert um Disclaimer und Pillar-Kanal-Zeilen.
  scripts/content_audit.py (C1 Duenn-Alarm <750 Woerter, C2 Struktur-
  Vollstaendigkeit Fazit/FAQ, C3 Platzhalter-Kanon mit Auto-Fix [Name]
  → Frank Hartung, Beispiel.com→eigene Domain; TODO/lorem report-only,
  C4 Zahl ohne €/% fehlt, C5 Jahres-Drift, C6 Titel-Versprechen).
  Fund heute: 🚨 C2-Systemluecke: kein Artikel hat eine Fazit-Rubrik
  (echter Auditfund); Roadmap: redaktions-politur-Workflow ergaenzt.
  Integrity-FEST: 32 -> 35 Dateien (inkl. data/content_fingerprints.jsonl).
  Lektion: Audit-Messung sah zuerst 77/77 ohne Fazit – Messung korrekt:
  C2 deckt echte Strukturlücke auf; Auto-Plattencheck wirkt wie beworben.
- **12.08.2026 (8):** LEKTOR-ELITE (Frank: „weltbestes Pro-Lektorat“): Zwei Wachen
  ergaenzt: scripts/stil_guard.py (S1-S8 Stil-Messung: Satzanfangs-Echo ueber
  Absatzgrenzen, Passiv-Dichte > 28 %, Dass-Ketten, Weiche-Wolke, LIX
  Lesbarkeit-Median 49.1 Flotte, Absatz-Monster, Vokabular-Diversitaet TTR)
  und scripts/hardcases_guard.py (H1-H9 deterministische Fest-Fehler mit
  Auto-Heilung: einzigste→einzige, das selbe→dasselbe, darauf hin→daraufhin,
  seid/seit, wieder/wider, Pleonasmus-Kanon wie „weisser Schimmel", bißchen,
  pre-1996-Schreibung mit Schutz-Schleusen gegen Falsch-Positive).
  Beide in blog_doctor-Kette, Integrity-FEST 30 → 32 Dateien, Wohnplatte
  (Selbsttest vor jedem Schreiben). ERSTE RUNDE bewiesen: Selbsttest faengt
  3 echte Design-Bugs in meinen eigenen Regeln ab (Case-Erledigt, Inline-
  Code-Schutzfehl, m re.I bei Fall 6) – dieser Selbsttest ist die beste
  Investition heute.
- **12.08.2026 (6):** Marken-Relaunch Runde 2 (Frank: „Punkte stoeren, Marke nicht
  sauber genug + Logo fuer ganzen Blog"). BEKENNENDE LEKTION: Mein Punktmuster
  mit Alpha `fill=(255,255,255,18)` wurde von Pillow im RGB-Modus still
  verworfen → Dots renderten KNALLWEISS statt dezent. Konsequenz: Punkte
  KOMPLETT entfernt (nie wieder Alpha-Tricks auf RGB). NEU (Profi-Look):
  Kategorie-Badge (Gold-Pille) oben, Titel ruhig zentriert, Markenband unten
  mit goldenem Haeckchen-Signet + 68px-Wortmarke (weiss/gold). BLOG-LOGO:
  Selbes Lockup wird site-weite Marke — `scripts/bake_brand.py` backt
  logo.svg/logo-light.svg/favicon.svg/apple-touch-icon.png DETERMINISTISCH
  aus Inter-Bold.ttf (Pfade via fonttools = fontlos), Header-Override
  layouts/_partials/header.html (Rest 1:1 Theme), favicon.ico-Data-URI
  ersetzt durch Markenhaken. SCHUTZ: brand_guard wacht jetzt ueber SHA-256
  der 4 Artefakte + Lockup-Marker im Header (Lock data/brand_lock.yaml,
  Selbstheilung via bake_brand — getestet mit Farbdreher- & Loesch-Angriff:
  bytegleich zurueckgeheilt). C2-Wache in check_covers neu kalibriert
  (Brand-Band 0.82–0.97H + Signet-Quadrant C2b). Integrity-Lock: 18→26 Dateien
  (bake_brand, brand_guard, brand_lock, header.html, 4 Artefakte).
- **11.08.2026 (3):** affiliate_marketer.py: Schnell-Tipp-Routing-Korrektur (Fehlrouten
  Depot→girokonto, Elementar→handytarife u.a. geheilt), universelles Retarget +
  17-Fälle-Selbsttest als Sabotage-Schutz (Exit 2 vor jeder Datei-Berührung).
- **11.08.2026 (2):** Verlags-Lektorat `lektor_guard.py` (L1–L5) in die Kette eingebaut.
- **11.08.2026:** Hoheitskarte Längen-Systeme festgelegt (Posts vs. Pillar, Floor 1.000); R9 Fence-Normalisierung dauerhaft; 56 Alt-Fences geheilt.
- **10.08.2026:** Regelwerk 1.0. Neu: casing_guard, dash_guard (R1–R8),
  compound_guard, emoji_guard (E1–E5), length_guard, brand_guard,
  uplift der Workflow-Härtung (Audit-Fixes: Alerting-Blindspot,
  Push-Races, Zeit-Kollision Mo 17:30, Dependabot+Auto-Merge,
  uptime-check). Legacy-Verdrahtung der Umbruch-Skripte reaktiviert.

---

> _Dieses Dokument pflegen heißt: Wenn eine Regel hinzukommt oder sich ändert,
> hier in die Tabelle. Das Regelwerk lebt – aber es vergisst nie._
