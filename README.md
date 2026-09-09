# FranksFinanzcheck – Hugo Affiliate-Blog (CHECK24)

Ein **kostenloser**, SEO-optimierter Blog mit **automatischer Content-Versorgung** – gebaut mit Hugo + PaperMod, hostbar kostenlos auf GitHub Pages oder Cloudflare Pages. Die Themen sind abgestimmt auf den **Pinterest-Masterplan** (FranksFinanzcheck, August 2026): Jeder Educational-Pin bekommt einen passenden Blog-Artikel, jeder Transactional-Pin eine eigene CHECK24-Kategorie.

> ⚠️ **Hinweis zur Automatisierung (Stand 26.08.2026):** Der Bot veröffentlicht Artikel automatisch, aber NUR wenn sie mehrere harte Qualitäts- und SEO-Gates bestehen (Profi-Qualitäts-Gate, `publish_gate.py`, `quality_score.py` ≥ 0,85) – siehe Abschnitt „Vollautomatik ohne manuelles Eingreifen" unten. Kein manueller Freigabe-Schritt mehr nötig; die Publikationsfrequenz ist fix auf Mo/Mi/Fr mit 2–3 Artikeln pro Tag begrenzt, um „Scaled Content Abuse"-Risiken bei einer jungen Domain zu vermeiden (DAUERVORGABE, siehe CADENCE-REPORT.md). **Seit 26.08.2026 wird die Routine HART erzwungen:** Vor jedem Publish (Deploy, Engine, manuell) prüft und heilt ein Gate-Komplex (`cadence_guard.py` + `publish_gate.py` + Titel-/Cover-Gates) Kadenz und Cover-Text-Komplettheit automatisch – Verstöße können nicht mehr live gehen, der Bestand heilt sich selbst (Details: `CADENCE-REPORT.md` Regel 5).

> 🧠 **Neu: AGC-Autopilot (08.09.2026):** Die Blog-Automatik bildet jetzt den
> Funktionsumfang von AGC Studio nach – **Brand Brain** (`data/brand_brain.yaml`),
> **6 tägliche Research-Teams** mit Reports & Routing (`scripts/research_engine.py`),
> **Kampagnen-Management** (Promo/Researched, CTA-Override, `data/campaigns.yaml`)
> und ein **Redaktionskalender** (`data/editorial_calendar.yaml`). Der Autopilot
> recherchiert und plant – veröffentlicht wird weiterhin NUR über die
> Content-Engine v2 + ihre Gates. Vollständige Anleitung & Feature-Parität:
> **[`AGC-AUTOPILOT.md`](AGC-AUTOPILOT.md)** · Orchestrator: `python3 scripts/autopilot.py --run`.

---

## 📋 Was ist enthalten

| Baustein | Details |
|---|---|
| Hugo-Blog | Theme PaperMod (SEO-fertig: Meta-Tags, OpenGraph, JSON-LD, Sitemap, robots.txt, Canonical) |
| Pflichtseiten | Impressum (mit Platzhaltern), Datenschutz, Über – Werbekennzeichnung inklusive |
| Artikelbestand | 25+ veröffentlichte Ratgeber über alle 6 Pillars (Aktualisierung: 08/2026) |
| Themenpool | `data/topics.yaml` – 175 Themen über alle 6 Pillars (repariert & erweitert 13.08.2026; bei 2–3 Artikeln an Mo/Mi/Fr reicht der Pool über ein halbes Jahr), inkl. themenspezifischer CHECK24-Links |
| 🤖 Content-Bot | `scripts/generate_drafts.py` – erzeugt an Publikationstagen (Mo/Mi/Fr) frische, einzigartige Artikel-Entwürfe (Titel, Meta-Description, Keywords, strukturiertes Markdown, FAQ, Affiliate-CTA) |
| ⏰ Publikations-Job | `.github/workflows/content-engine-v2.yml` – Mo/Mi/Fr 08:10 MESZ (Fallback 16:10 / 19:40) |
| 🚀 Deployment | `.github/workflows/deploy.yml` – baut & veröffentlicht kostenlos auf GitHub Pages |
| 📤 Publish-Helfer | `scripts/publish.py` – Entwürfe mit einem Befehl veröffentlichen |

---

## ⚡ Vollautomatik (kein tägliches Pushen nötig)

Der Workflow **„Content-Engine v2“** veröffentlicht **nur montags, mittwochs und freitags – 2 bis 3 Artikel pro Publikationstag** (DAUERVORGABE, siehe `CADENCE-REPORT.md`):

| Uhrzeit (DE) | Was passiert |
|---|---|
| **08:10** | Haupt-Slot: Die Engine füllt das Tagesziel (2–3 Artikel) aus dem Pinterest-Plan bzw. Themenpool auf und VERÖFFENTLICHT sie automatisch |
| **16:10 / 19:40** | Fallback-Slots: greifen nur, wenn der Haupt-Slot gescheitert ist (Selbstheilung) |

**Wie es funktioniert:**
- Themen kommen **direkt aus deinem Pinterest-Plan** (`data/pinterest_plan.yaml`, 73 Pins)
- Artikel werden **automatisch veröffentlicht** (`draft: false`) – kein manueller Schritt
- Sind alle Pin-Themen abgedeckt, greift automatisch der erweiterte Themenpool (`topics.yaml`)
- Einzigartigkeits-Check + Anti-Copy-Prompt stellen sicher, dass kein Pin-Text 1:1 kopiert wird
- **Harter Wochentags-Guard:** auch manuelle Workflow-Starts veröffentlichen an Di/Do/Sa/So nichts (Notfall: `FORCE_PUBLISH_ANY_DAY=1` setzen)
- Tagesmenge steuerbar: `MIN_ARTIKEL_PRO_TAG` (Default 2) / `MAX_ARTIKEL_PRO_TAG` (Default 3)
- Die Engine erzwingt mindestens 2 Artikel pro Publikationstag (Dauervorgabe-Floor); empfohlen: Repository-Variablen `MAX_ARTIKEL_PRO_TAG=3` / `MIN_ARTIKEL_PRO_TAG=2` setzen

**🔒 Hartes Vor-Veröffentlichungs-Gate + Selbstheilung (26.08.2026):**
Die Routine wird nicht nur in der Engine eingehalten, sondern VOR JEDEM
Publish technisch erzwungen – egal welcher Pfad einen Artikel nach `main`
bringt (Deploy, Engine, manueller Commit, `publish.py`):

| Stage | Was passiert |
|---|---|
| **Deploy-Gate** (`deploy.yml`) | Vor jedem Hugo-Build: Kadenz-Selbsttest → `cadence_guard.py --fix` (Zurückstufung + Re-Queue bei Verstößen) → Titel-Gate → Cover-Gate → Build. Heilungen werden gepusht. Heading-Gate-Anbindung (27.08.) als fertiger Patch bereit: `patches/heading-gate-2026-08-27-workflows.patch`. |
| **Engine-Phase 0.5** | Vor JEDEM Slot: Kadenz-Gate stellt die Tageszahl auf den korrekten Stand (Selbstheilung) |
| **Engine-Publish-Gate** | 5 harte Prüfungen inkl. **Cover-Text-Komplettheit** (unvollständiger Titel → Verwurf bzw. Zurückstufung) |
| **Engine-Phase 6** | `engine_issue.py --deficit`: Tagesende unter Minimum → sichtbares, auto-schließendes Issue |
| **Blog-Health (täglich)** | Heilt auch ZWISCHEN den Publishing-Slots: Kadenz, Titel, Covers + Überschriften-Hygiene (`blog_health_gate.py` ruft seit 27.08. `heading_guard.py` anker-stabil auf – kein `<br>` in Überschriften, TOC-/Leerzeichen-Fehlerwurzel) |
| **Affiliate-Integritäts-Wache (täglich)** | Seit 02.09. Premium-Stufe: Detektor-**Selbsttest** vor jeder Prüfung, **Render-Beweis AI4** attribut-tolerant + schlüsselgenau, **Gateway-Beweis AI5** (`/go/<key>/` leitet auf die registrierte Partner-URL weiter), **fail-closed** bei Werkzeugfehlern (Exit 2 → `publish_gate.py` veröffentlicht nichts), EIN Issue pro Schadenslage (auto-schließend). Details: `AFFILIATE-INTEGRITY-GATE-REPORT.md` |
| **Casing-Bund (täglich + bei der Geburt)** | `casing_guard.py` entscheidet Groß-/Kleinschreibung nach Duden – 17 Textregeln (C1–C17) plus Tag/Kategorie-Regel T1, gemeinsames Lexikon `tag_casing.py`, Selbsttest vor JEDEM Schreibvorgang, `--gate` parkt Neugeburten mit hartem Befund, `--plan` heilt die Quelle der Pin-Texte mit. Details: `CASING-REPORT.md` |
| **Doktor-Kette / Engine** | `blog_doctor.py` (Phase A, erste Text-Wache) heilt jeden NEUEN Artikel bei der Geburt (`--new-only` via Content-Engine v2) und bei jeder Visite |
| **`publish.py` (manuell)** | Gleiche Routine wie die Automation – Verstoß blockiert hart (Notfall: `--force-cadence`) |

**✍️ Casing-Bund auf Premium-Stufe (09.09.2026):**

`scripts/casing_guard.py` ist keine Warnliste, sondern ein Entscheider: Es prüft
und heilt die gesamte Sprach-Oberfläche des Blogs in einem Lauf – Akronym-Kanon
(`dsl → DSL`, `W/kWh`), Marken-Schreibweise (`fritzbox → FRITZ!Box`,
`Check24 → CHECK24`, bewusst klein: `congstar`, `otelo`, `idealo`),
Durchkopplung (`DSL Vergleich → DSL-Vergleich`), Nominalisierung nach
Präposition (`zum sparen → zum Sparen`), substantivierte Adjektive
(`etwas neues → etwas Neues`), Satzanfang, Monats-/Wochentagsnamen,
Title-Case-Leaks aus der KI (`Den Stichtag Kennen und nutzen → kennen`),
Shouting-Betonung (`NICHT → nicht`) und die Tags/Kategorien selbst
(`dns hack → DNS Hack`, inklusive Slug-Dedup).

| Baustein | Beweis |
|---|---|
| 17 Regeln + T1, Zonenmodell (Fließtext / SEO-Feld / Pin-Feld / Tag / geschützte Register) | `python3 scripts/casing_guard.py --selftest` – 25 Fix- + 25 Schutz- + 16 Strukturfälle inkl. Idempotenz |
| Titel-Zone heilt mit | `C3` + `C17` in `TYPO_RULES`: Akronym- und Komposita-Kanon gelten auch in `title`/`description` (dort ist die Leerzeichenform der Fehler, im Fließtext kann sie Aufzählung sein) |
| Link-/SEO-Schutz | Sichtbare Linklabels folgen dem Textkanon; Linkziele, Bildpfade, URLs, Slugs, Code, Hashtags und `keywords` bleiben bytegleich – kein SEO- oder Routing-Risiko |
| Überschriften-Hygiene | `C16` entfernt redundantes `**Fettdruck**` aus Überschriften; `C17` koppelt Leerraum-Komposita im Titel (`Frugalismus Tipps → Frugalismus-Tipps`, `Heizung wartung → Heizungswartung`) |
| Kopf-Vollständigkeit als Trenn-Bremse | `HG_ENDHANG`: ein Kopf, der auf Artikel, Demonstrativpronomen oder Konjunktion endet („Welche Rolle spielt die | **Elementarschadenversicherung** bei einer Photovoltaik‑Anlage?“), wird nicht getrennt – die Sperre heilt einen Fall, den die erste Fassung der Trennung selbst gerissen hatte; 3 zusätzliche Selbsttestfälle (davon 2 mit verbotener Trennung: „… am einfachsten an?“, „Fair geht vor“) |
| Länge ist kein Fehler | Gemeldet wird nur die **nachgewiesene Satzfuge** (Satz endet mit Punkt innerhalb der Zeile / trennbarer Fettkörper), nie die Wortzahl – fünf saubere FAQ- und Doppelpunkt-Titel waren der alten Heuristik zum Opfer gefallen |
| Gleiche Entscheidung im Generator (Prävention) | `tag_casing.py` wird von `generate_drafts.normalize_tags()` und `engine_generate._casing_frontmatter()` genutzt |
| Struktur-Modus `--split-headglue` | trennt angeklebten Absatztext nur an drei beweisbaren Nahtstellen (Fettkörper / Folgesatz nach `?`/`!` / Listenkopf mit Satzanfang + Verbbeleg); 16 Positiv- und Schutzfälle belegen die Entscheidung, zweiter Lauf = 0. **Bewusst keine vierte Nahtstelle:** ein Satz, der mit einem Nomen beginnt, ist maschinell nicht von einem fortlaufenden Titel zu unterscheiden – geraten würde eine zerlegte Überschrift, also geht der Fall als Meldung an die Redaktion |
| Keine Klebefalle im Generator | `fazit_schmiede.py` schrieb `## Fazit: <kompletter H1> schlau nutzen` – CTA-Satz in der Überschrift, doppelter Doppelpunkt, duplizierter Titel. Seit 09.09.: Fazit-Überschrift ohne CTA, Unterüberschrift mit Gedankenstrich, Komposita über dasselbe Lexikon (`tc_join`) |
| Keine Kollision mit der Tipp-Kette | `fix_spaces.py` maskiert Marken mit Ausrufezeichen (FRITZ!Box) und ignoriert Wort-inneres `!`; Pin/SEO-Felder werden nie in der Betonung gefixt |
| extensionsfähig ohne Code-Change | `data/casing_whitelist.txt` (ein Wort pro Zeile = alle Regeln schweigen für diesen Begriff) |
| Nachvollziehbarkeit | `CASING-REPORT.md`, `data/casing_history.jsonl` (Dichte harter Befunde je 1.000 Wörter + Trend), Lampe in `EDITORIAL-SCORECARD.md` |

```bash
python3 scripts/casing_guard.py --selftest          # Detektor-Beweis (Exit 2 = Wache blind)
python3 scripts/casing_guard.py --dry-run           # Bestand prüfen, nichts schreiben
python3 scripts/casing_guard.py --fix --plan        # Inhalt + Pinterest-Plan heilen
python3 scripts/casing_guard.py --gate --new-only   # harter Restbefund → Artikel bleibt Entwurf
python3 scripts/casing_guard.py --split-headglue --dry-run  # angeklebte Überschriften anzeigen
python3 scripts/casing_guard.py --split-headglue            # eindeutige Fälle trennen (idempotent)
```

Dazu: zentrale Titel-Kürzung an Wortgrenzen (`post_utils.safe_title_cut()`,
nie mitten im Wort) und `check_covers.py` C4, die für jedes Cover
verifiziert, dass der komplette Titel im Textbereich rendert.
Report: `CADENCE-GATE-REPORT.md` · Regelwerk: `CADENCE-REPORT.md` Regel 5.

**Steuerung:**
- **Stoppen (Kill-Switch):** GitHub → Actions → „Content-Engine v2“ → Disable workflow
- **Manuell starten:** GitHub → Actions → „Run workflow“
- **Wieder auf Entwurfs-Modus:** Im Workflow `AUTO_PUBLISH: "0"` setzen (dann musst du wieder freigeben)

**🔗 Affiliate-Links ändern – so geht's (wichtig!):**

Alle Affiliate-Links liegen zentral in **`scripts/check24_links.yaml`**. Ändern sich deine Links (z. B. neue PID, neues Link-Format, neue Partnerprogramme):

1. **Neue Artikel (Bot):** Einfach die Links in `scripts/check24_links.yaml` aktualisieren – der Bot weist neuen Artikeln automatisch die passenden Links zu (Pin → Kategorie → Link). Die Zuordnung erfolgt über die Ziel-URL des Pins (z. B. `check24.de/strom/` → Strom-Link) bzw. die Pinwand.
2. **Bestehende Artikel:** `python3 scripts/affiliate_shield.py --fix` routet alle Affiliate-Links über das `/go/`-Gateway; `python3 scripts/affiliate_link_check.py --fix` prüft Kategorie und PID.
3. **Generischer Link (GitHub-Variable):** Falls nötig, in GitHub unter Settings → Secrets and variables → Actions die Variable `AFFILIATE_URL` aktualisieren.

**🛡️ Affiliate-Integritäts-Wache auf Premium-Stufe (02.09.2026):**

Die tägliche Wache (`affiliate-integrity-daily.yml`, 06:00 MESZ) beweist,
dass jeder Affiliate-Link **wirklich im Blog erscheint** – nicht nur, dass
er im Markdown steht:

| Prüfung | Was bewiesen wird |
|---|---|
| **AI1 Struktur** | Jede CTA-Zeile enthält einen vollständigen Markdown-Link (kein Dangling `[**Text**` ohne `](url)`) |
| **AI2 Registry** | Jedes `/go/<key>/` ist in `check24_links.yaml` registriert; **keine** rohen Partner-URLs im Content (Tracking-/Kennzeichnungsumgehung) |
| **AI3 Plausibilität** | Verstümmelter Text direkt an der CTA fällt auf (hunspell) |
| **AI4 Render-Beweis** | Jeder Markdown-Link steht **schlüsselgenau** als `<a href="/go/<key>/…">` im gebauten HTML – inkl. `rel="sponsored"` (Werbekennzeichnung) und Umami-Klick-Attribution |
| **AI5 Gateway-Beweis** | Jede `/go/<key>/`-Seite existiert, ist `noindex` und leitet exakt auf die registrierte Partner-URL weiter |

Selbstheilung: defekte CTA-Zeilen werden **nie geflickt**, sondern komplett
neu aus den geprüften Vorlagen (`affiliate_marketer.py`) generiert; fremde/
nicht registrierte Linkziele werden auf die thematisch korrekte Route
umgeroutet (`route_for()`); Bestandsartikel werden nie gelöscht.

Drei Sicherheitsnetze gegen „stille Blindheit" (Lehre aus dem Vorfall
01.09.2026, siehe `AFFILIATE-INTEGRITY-GATE-REPORT.md`):

```bash
python3 scripts/affiliate_integrity_gate.py --selftest   # Detektor-Beweis (Exit 2 = Wache blind)
python3 scripts/affiliate_integrity_gate.py              # prüfen + sofort heilen
python3 scripts/affiliate_integrity_gate.py --dry-run --json
```

- **Selbsttest mit eingefrorenen Fixtures** aus realer Hook-Ausgabe
  (aktuell, Legacy 14.08., unminifiziert) + **Drift-Wächter** gegen
  `render-link.html` – läuft im Workflow VOR jeder Prüfung.
- **Fail-closed:** kein `public/`, kaputter Hugo-Build oder veralteter
  Detektor = Werkzeugfehler (Exit 2). Dann wird nichts „geheilt", nichts
  verworfen und `publish_gate.py` veröffentlicht **gar nichts**.
- **Massen-Blindheit** (0 gerenderte Links in *allen* Artikeln) wird als
  Detektorfehler entlarvt, nicht als Inhaltsschaden.

Shortcode-CTAs (`tarifvergleich`, `einspartabelle`) laufen nicht durch die
Markdown-Pipeline und wurden deshalb vom Render-Hook nicht erfasst – sie
nutzen jetzt denselben Attribut-Vertrag über
`layouts/_partials/affiliate_anchor_attrs.html` (Fund vom 02.09.: Buttons
ohne `rel="sponsored"` und ohne Klick-Attribution).

Report und Zustand werden **konvergent** geschrieben (nur bei inhaltlicher
Änderung) – ruhige Tage erzeugen kein Git-Diff, keinen Commit, keinen
Deploy-Trigger und kein Issue.

Report: `AFFILIATE-INTEGRITY-REPORT.md` (täglich) ·
Zustand: `.affiliate_integrity_state.json` ·
Hintergrund/Dauerhaftigkeit: `AFFILIATE-INTEGRITY-GATE-REPORT.md`

> ⚠️ **Einmalig einspielen (Workflow):** Die Premium-Fassung von
> `.github/workflows/affiliate-integrity-daily.yml` liegt als fertiger Patch
> bei – Agenten dürfen keine Workflow-Dateien pushen (GitHub-App ohne
> `workflows`-Permission). Ohne Patch fehlt der Wache `actions: write`, der
> Deploy-Trigger läuft an Heilungs-Tagen in eine 403:
>
> ```bash
> git apply patches/affiliate-integrity-premium-2026-09-02-workflows.patch
> # alternativ: cp patches/affiliate-integrity-daily-2026-09-02-workflow-ready.yml \
> #                 .github/workflows/affiliate-integrity-daily.yml
> ```


**📌 Automatisches Pinnen bei Pinterest (RSS-Auto-Publish):**

Seit 20.08.2026 pinnpt **Pinterests eigener RSS-Auto-Publish** (Feed:
`https://franksfinanzcheck.de/index.xml`) neue Artikel automatisch – der
Feed ist dafür optimiert (Cover 1000×1500 als enclosure, Pin-Description,
`*Werbung`-Kennzeichnung, spam-geprüft durch `spam_guard.py` F1). Der
frühere Workflow „Wöchentliches Nach-Pinnen" wurde am 27.08.2026 entfernt
(Doppel-Struktur). Manuelle Pin-Läufe (z. B. Queue abarbeiten, Board-
Routing über 6 Boards) laufen über **Actions → „Pinterest-AI" → Run
workflow** (`pinterest_engine.py`); Rate-Limits und 30-Tage-Repeat-Schutz
setzt `spam_guard.py` durch.

**Einmalige Einrichtung (~5 Min.):** Siehe **`docs/PINTEREST-TOKEN-RUNBOOK.md`**
- Pinterest-Developer-App → Secrets `PINTEREST_APP_ID`, `PINTEREST_APP_SECRET`,
  `PINTEREST_TOKEN_KEY` (selbst gewählte Zufallszeichenkette)
- Autorisierung komplett in Actions: **„Pinterest-Token-Wache" → Run workflow**
  (`show_auth_url` → Link klicken → Erlauben → Code von `franksfinanzcheck.de/pinterest-oauth`
  kopieren → Code oder ganze Adresszeile in `auth_code`). Danach erneuert sich der Zugang
  **täglich selbst** (continuous refresh) – kein 30-Tage-Handbetrieb mehr.
  Härtung 08.09.2026 (#219): Live-Probe im Nachweis (`--verify`), nur die Wache rotiert
  proaktiv, Lagebild nur aus geprüften Läufen, echte v5-Scopes, Diagnose statt „Exit 1" –
  Regel **C13** im Governance-Vertrag. Details: `PINTEREST-TOKEN-219-REPARATUR-2026-09-08.md`
- Board-ID (`python3 scripts/pinterest_engine.py --list-boards`) → Variable `PINTEREST_BOARD_ID`
- Lagebild jederzeit: `python3 scripts/pinterest_token.py --status`
  (Quelle, Restlaufzeiten, nächster Schritt – ohne Token-Material)

**🔍 Automatische SEO-Optimierung (wöchentlich, kostenlos, Profi-Niveau):**

Der Workflow **„Wöchentliche SEO-Optimierung"** läuft jeden Mittwoch 07:00 Uhr (DE):

1. **SEO-Audit** (`python3 scripts/seo_audit.py`): prüft alle Artikel auf
   Titel-Länge (30-65 Zeichen), Meta-Description (70-165), Keywords, H2-Struktur,
   Alt-Texte, interne Links, Wortanzahl (min. 300) und Sitemap-Konsistenz.
   Bei Problemen → automatisches GitHub-Issue mit Details.
2. **IndexNow-Indexierung** (`python3 scripts/submit_indexnow.py`): reicht neue
   Artikel automatisch bei Bing, Seznam, Naver & Yandex ein (kostenloses
   Push-Protokoll, kein API-Key nötig – Key-Datei liegt im Repo). Bing speist
   auch DuckDuckGo und die ChatGPT-Suche.
3. **Google:** Sitemap bereits eingereicht; zusätzlich empfohlen: Google Search
   Console „Indexierung anfordern" nach Veröffentlichung (manuell, 30 Sekunden).

**🔑 Automatische Keyword-Optimierung (Profi-Niveau):**

1. **Neue Artikel:** Der Content-Bot erhält die Ziel-Keywords direkt im
   Generierungs-Prompt – das Haupt-Keyword muss in Titel, Description,
   erstem Absatz und einer H2 erscheinen (automatisch, keine Handarbeit).
2. **Bestehende Artikel:** `python3 scripts/keyword_optimizer.py` prüft alle
   Artikel auf Keyword-Platzierung (Titel, Description, erster Absatz,
   Überschriften, URL-Slug) und Keyword-Dichte (0,3–3 %). Läuft auch im
   wöchentlichen SEO-Workflow (mittwochs 07:00) – bei Problemen → GitHub-Issue.
3. **Optional KI-Vorschläge:** `python3 scripts/keyword_optimizer.py --ai`
   schlägt verwandte LSI-Keywords pro Artikel vor (nutzt deine Gratis-KI-Keys).

**📌 Pinterest- + Google-SEO-Healer (Agentur-Selbstheilung, Stand 24.08.2026):**

`python3 scripts/pinterest_seo_healer.py --fix` hält **alle** Beiträge
(bestehend + neu) dauerhaft auf Profi-Niveau:

| Feld | Google 2026 | Pinterest 2026 |
|---|---|---|
| Titel / Cover-Text | 30–60 Z., `Hauptkeyword: Untertitel` | Pin-Titel ≤100 (Feed ~40) |
| Meta-Description | 120–160 Z., Keyword + CTA | Pin-Text ≤500, `*Werbung \| …`, max. 3 ASCII-Hashtags |
| Cover | og:image 1000×1500, Alt = Titel | 2:3, Text-Overlay, Brand-Band |
| Keywords | ≥3 Phrasen in Titel/Desc/H2 | Hashtags aus Keywords |

Läuft automatisch in **Content-Engine v2** (Phase 3), **seo-weekly** und
**pinterest-watchdog** (vor dem Hugo-Build). Report: `PINTEREST-SEO-HEALER-REPORT.md`.
Neue Artikel bekommen Keywords + `pin_title`/`pin_description` bereits beim
Speichern (`engine_generate.py`).

**♿ Automatische Barrierefreiheit (WCAG 2.1, Top-Niveau):**

Der Blog ist barrierefrei umgesetzt und wird wöchentlich geprüft
(`python3 scripts/a11y_audit.py` – auch im SEO-Workflow):
- Skip-Link „Zum Inhalt springen" (Tastatur-Navigation)
- Sichtbare Fokus-Stile auf allen interaktiven Elementen
- `prefers-reduced-motion` (Animationen für empfindliche Nutzer aus)
- `aria-hidden` für alle dekorativen Emojis (Screenreader-freundlich)
- Consent-Banner: `role="region"`, Escape zum Schließen, Fokus-Management
- Alle Bilder mit Alt-Texten, genau 1 h1 pro Seite, `lang="de"`
- Farbkontraste geprüft gegen WCAG AA (alle ≥ 4.5:1, meist 7:1+)

**Automatisches Einzigartigkeits-Audit (Qualitäts-Gate):**
- **Nach jeder Bot-Veröffentlichung** läuft `scripts/check_uniqueness.py` automatisch mit:
  - Findet der Check kritische Duplikate (≥5 gleiche 7-Wort-Phrasen oder Pin-Konflikt),
    bricht der Workflow AB → der Artikel wird NICHT veröffentlicht. Das Log zeigt, was zu tun ist.
- **Bei jedem Bot-Lauf** (Mo/Mi/Fr) wird `check_uniqueness.py --sameday --fix` ausgeführt;
  der `seo-weekly`-Lauf prüft die Bestandsartikel im Rahmen des Qualitäts-Gates.
- **Manuell (jederzeit):** `python3 scripts/check_uniqueness.py` (oder `--strict`) –
  bei Verstößen wird im selben Zug ein normales GitHub-Issue angelegt.

> Hinweis: Im Winter (MEZ) verschiebt sich die UTC-Zeit automatisch – deutsche Uhrzeit (08:10/19:40) bleibt gleich.

---

## 🤖 KI-Redaktion (seit 08.09.2026: Claude/ChatGPT/Jasper-Schema, 0 €)

Die **KI-Redaktion** bildet das Dreier-Schema „Claude für lange Artikel +
ChatGPT für schnelle News + Jasper für SEO" mit gleichem Funktionsumfang ab –
ausschließlich über die vorhandenen **Gratis-Zugänge** (Groq/Gemini), es
entstehen **keinerlei Kosten** (Details und ehrliche Einordnung der
Abo-API-Lage: `KI-REDAKTION.md`).

| Slot | Rolle | Ergebnis |
|---|---|---|
| Mo/Mi/Fr 06:30 | „Claude" (`claude_writer.py`) + „Jasper"-SEO-Pass | Premium-Langentwurf + `KI-SEO-REPORT.md` |
| Di/Do/So 06:30 | „ChatGPT" (`news_writer.py`) + SEO-Pass | News-Kompakt-Entwurf |

Alles bleibt **Entwurf** (`draft: true`, ohne `cadence_wait`): Veröffentlicht
wird erst nach bewusster Freigabe über
`python3 scripts/ki_redaktion.py --promote <slug>` – dann wie gewohnt über
den `cadence_guard` (Mo/Mi/Fr, 2–3 Artikel/Tag, alle Gates).
Status: `python3 scripts/ki_redaktion.py --status`.

---

## 🧠 Verständnis-Qualität (seit 01.09.2026, Audit-Umsetzung)

Die Verständnis-Gates aus dem `TEXTVERSTAENDNIS-AUDIT-REPORT.md` sind als
lauffähige Skripte umgesetzt und in die Pipeline integriert:

| Skript | Was es prüft | Blockiert? |
|---|---|---|
| `scripts/duplikat_guard.py` (R1) | Exakte/Near-Duplikate, Doppel-Kapitel, Premium-Anhänge | `--new-only` → parkt neue Artikel |
| `scripts/textverstaendnis_guard.py` (R2–R5, R7, R8) | Keyword-Dumps, Terminologie-Mix, Satzanfangs-Echo, Absatz-Monster, Intro-Formeln, Ankertext-Kohärenz | `--new-only` → parkt neue Artikel |
| `scripts/readability_check.py` (R6, gehärtet) | Flesch ≥ 60, Ø Satzlänge ≤ 16, >25-Wort-Sätze < 10 %, Dumps, Satzlängen-SD | `--new-only` |
| `scripts/link_guard.py` (R8-URL) | Kaputte Slugs (auch Leerzeichen-Slugs), Ziele, UTM | `--fix` selbstheilend |
| `scripts/grammar_check.py` | LanguageTool-Grammatik – ehrlich bei API-Ausfall (Exit 2, kein falsch-grün) | bei API-down |
| `scripts/length_guard.py` (R9) | Längen-Korridore + Duplikatschutz der KI-Selbstheilung (Shingle-Overlap > 40 % → verworfen) | – |
| `scripts/quality_score.py` (R10) | Gesamt-Score mit Lesbarkeits-Gewicht 0,20 | publish/draft/human-review |
| `scripts/absorb_whitelist.py` | Senkt Rechtschreib-Rauschen: Komposita in ≥ 3 Artikeln → Whitelist | – |
| `scripts/r5_absatz_splitter.py` | Splittet Absätze > 4 Sätze an Satzgrenzen („eine Idee pro Absatz“) | – |

**Schnell-Checks:**

```bash
python3 scripts/duplikat_guard.py --selftest          # Selbsttests
python3 scripts/textverstaendnis_guard.py --selftest  # 8 Fälle
python3 scripts/textverstaendnis_guard.py             # Flotten-Audit (hart/weich)
python3 scripts/readability_check.py                  # Lesbarkeits-Audit
python3 scripts/duplikat_guard.py --fix               # Duplikate entfernen
python3 scripts/r5_absatz_splitter.py --apply         # Absätze splitten
```

Neue Artikel, die harte Regeln verletzen, werden in `content-engine-v2.yml`
automatisch auf `draft: true` geparkt („Entwurf statt Publikation“) – sie
erscheinen erst nach manueller Freigabe. Der wöchentliche Lauf
(`seo-weekly.yml`) auditert die gesamte Flotte.

---

## 📰 Redaktions-Standard (seit 02.09.2026, Capital · WirtschaftsWoche · DIE ZEIT)

Recherche der Online-Methoden von **Capital**, **WirtschaftsWoche** und dem
**Geld-Teil der ZEIT** (Quellen + Methoden-Übertragung:
`REDAKTIONS-STANDARD-CAPITAL-WIWO-ZEIT.md`) und dauerhafte Umsetzung in der
Wache `scripts/redaktions_standard.py` – gilt für **bestehende und
zukünftige** Beiträge:

| Regel | Vorbild | Automatik |
|---|---|---|
| RS1 | ZEIT-Artikelzusammenfassung | „Das Wichtigste in Kürze“-Box (≥ 3 Bullets) → Pflicht + KI-Heilung |
| RS2 | Capital-erklärt | ≥ 2 Frage-Überschriften → Pflicht + KI-Umformulierung |
| RS3 | Capital-Faustregeln | ≥ 1 markierte „Faustregel: …“ → Pflicht + KI-Ergänzung |
| RS4 | ZEIT-Tipplisten/Dossiers | ≥ 1 nummerierte Schrittfolge (3–6 Schritte) → Pflicht + KI-Ergänzung |
| RS5 | WiWo-Verifikation | Harte Zahlen nur mit Einordnung (ca./rund/Spanne/Rechenbeispiel) → Report + KI |
| RS6 | WiWo/Pressekodex | Keine Phantom-Quellen („laut einer Studie“) → Report + KI |
| RS7 | Byline/E-E-A-T | `author:` + `erfahrung:` im Frontmatter → deterministische Selbstheilung |
| RS8 | WiWo-Korrekturen | `korrektur:`-Feld → Korrektur-Box im Artikel + `data/korrekturen.yaml` |

**Verdrahtung:** Content-Engine v2 Phase 2 (Heilung + Gate bei der Geburt;
harte Funde → Entwurf), Blog-Doktor-Kette (täglich), SEO-Weekly
(Bestands-Retrofit, Backlog 3/Woche), Generation-Prompts (Pflicht-Module
stehen direkt im KI-Prompt). Report: `REDAKTIONS-STANDARD-REPORT.md`.

**Schnell-Checks:**

```bash
python3 scripts/redaktions_standard.py --selftest   # 22 Fälle (Sabotage-Schutz)
python3 scripts/redaktions_standard.py              # Flotten-Audit RS1–RS8
python3 scripts/redaktions_standard.py --fix --ai --backlog 3   # Bestand heben
python3 scripts/redaktions_standard.py --register-korrektur --file content/posts/<slug>/index.md --grund "Tippfehler korrigiert"
```

---

## 🔊 Lesehilfen: Vorlesen + Kurzfassung (FF Voice Studio, Generation 4 · 10.09.2026)

Das frühere Vorlese-Modell wurde **vollständig entfernt** und durch eine **robustere Hybrid-TTS** ersetzt (Generation 4: Nur-Deutsch-Sprechervertrag + wortgenaue Leseanzeige; Details im `VORLESEN-NURDEUTSCH-WORTTAKT-2026-09-10.md`). Jeder Artikel und jede Ratgeberseite bekommt zwei Lesehilfen:

1. **Vorlesen** – ein **männlicher, deutscher Nachrichtensprecher**, robust als Studio-/Browser-Hybrid; **Nur-Deutsch-Vertrag** (Befund 07.09.2026): die Vorlese-Funktion kennt keine zweite Sprache, keinen Sprach-Umschalter, kein Stimmen-Menü, keine Regler. Englische Fachbegriffe liest der Nachrichtensprecher, wie es im deutschen Hörfunk üblich ist.
2. **Kurzfassung** – Verlagshaus-Kurzfassung (Kapital/WirtschaftsWoche/Zeit als Maßstab) in einem barrierefreien Dialog.

### Zwei Tonpfade, eine Regie

| Stufe | Technik | Stimme |
|---|---|---|
| **Studio-Tonspur** (Vorzug) | `scripts/ff_voice_audio.py` im Deploy → MP3, 24 kHz Mono, −16 LUFS (EBU R128) | Profil „news“ (Standard): edge-tts `de-DE-ConradNeural` mit Style `serious`; „natural“: `de-DE-FlorianMultilingualNeural`; „narrator“: `de-DE-Thorsten`-Zone; sonst Piper: `de_DE-thorsten-high`. Englische Backends (Groq-Notnagel) sind mit dem Nur-Deutsch-Vertrag entfallen |
| **Browser-Engine** (Fallback) | `static/premium/ff-voice.js` (Web Speech API) | deterministisch männlich + deutsch gefiltert (Female-Veto, Deutsch-Pflicht, News-Vorrang Conrad > Killian > Florian > Thorsten, Google-Codes B/D/F), gleiche Regie |

Die Tonspur läuft im nativen HTML5-Player und klingt dadurch **identisch** auf iPhone, Mac, Tablet, Android, PC und in jedem Browser. Fehlt sie, übernimmt sofort die Browser-Engine – **nie stumm**.

### Was „High-End“ hier bedeutet

- **Aussprache-Regie** – Zahlen, Währungen, Daten, Zeiten, Prozente, Paragrafen, Abkürzungen, Einheiten und URLs werden vor dem Sprechen in gesprochene Sprache übersetzt — nach deutschem Regelwerk, für jeden Text.
- **Nur-Deutsch-Vertrag** – kein Satz- oder Wort-Routing in eine zweite Sprache mehr; das Paritäts-Gate verbietet EN-Stimmenketten und EN-Tabellen in beiden Implementierungen hart.
- **Studio-Prosodie** – jede Rolle (Überschrift, Fließtext, Tabellenzeile, Warnhinweis …) hat Tempo, Tonlage und Lautstärke; Informationsdichte bremst automatisch, Fragen steigen, Blockenden klingen aus.
- **Atemgruppen** – Sätze werden an Konnektoren und Nebensatzgrenzen geteilt; die harte Obergrenze bleibt unter der Chrome-Abbruchgrenze.
- **Vollständigkeit** – Überschriften aller Ebenen, Listen, Zitate, Fettdruck an seiner Stelle, Premium-Übersichten samt Titel und Fußnote. Tabellen und Übersichten werden vollständig mit Zeilen und Spalten erkannt und gesprochen: HTML- und ARIA-Tabellen (`role="table"/"grid"`, Zeilen über `role="row"`), colspan/rowspan als logisches Gitter, mehrzeilige Köpfe, Zeilentitel (`th scope="row"`), Gruppen- und Summenzeilen (auch im `<tbody>`), Werbelink-Zeilen als offengelegte Empfehlung, Titel aus `<caption>`, `aria-label`, Premium-Headline oder der Überschrift davor (Details: `VORLESEN-TABELLEN-HIGHEND-REPORT.md`).
- **Barrierefreiheit** – WCAG 2.2 / BITV: Live-Region, Fokus-Falle, Scroll-Sperre, Fokus-Rückkehr, Escape, Tastatursteuerung, `prefers-reduced-motion`, Media Session (Sperrbildschirm/Headset).
- **Profi-Fortschrittsanzeige** – gelber, sichtbarer Progress-Meter mit Prozentwert, Modus-Badge und zugänglichem `role="progressbar"`; er bleibt auch bei schwachen `onboundary`-Events durch Zeit-/Block-Interpolation plausibel in Bewegung. Die Zeile **„Gerade vorgelesen“** nennt den aktuell gesprochenen Satz samt Abschnittszähler und Wortzähler („Wort 214 von 1.286“). Der **Wort-Takt** hebt zusätzlich das gesprochene Wort im Artikeltext hell: millisekundengenau über die **Wortuhr** der Tonspur (`chunk.w`, vom Generator aus den Sprachsynthese-Grenzen gerechnet), bei der Browser-Engine über `onboundary`-Grenzen, und nur wo beides fehlt redlich gezeitt — die Quelle steht an der Leiste (`data-ff-wordsync="track|speech|none"`), geblendet wird nie ein Wort, das nicht klingt. Die Fläche ist dauerhaft reserviert (kein CLS), bleibt beim Pausieren stehen und wird beim Beenden vollständig zurückgebaut (Artikel-DOM unverändert). Tastatur: `Esc`, `←/→` Abschnitt, `Shift+←/→` Satz.

### Wächter (alle grün)

```bash
node scripts/ff_voice_functional_test.mjs   # 218 Gates: echte DOM, alle echten Artikel, Doppel-Lese-Schleuse, Wort-Takt (Gruppe 9b)
node scripts/ff_voice_voice_test.js         #  69 Gates: männlicher Nachrichtensprecher, Nur-Deutsch, Wortuhr-Sprechpfad, 8 Geräte-Kataloge
node scripts/ff_voice_repair_test.mjs       #  56 Gates: Reparatur-Pinne (Befund 06.09.2026)
node scripts/ff_voice_tts_hardening_test.mjs#  57 Gates: Ehrlichkeits-/Stumm-/Hänger-Wachen (Befund 07.09.2026)
python3 scripts/ff_voice_parity_check.py    # 337 Gates: Tonspur ≡ Browser-Engine, Wortuhr-Aligner-Parität, Nur-Deutsch-Verbote
python3 scripts/ff_voice_toolbar_check.py   # 118 Gates: Layout, Styling, Wortzähler-IDs, Workflow, Rückbau
python3 scripts/ff_voice_backends.py --selftest  #  71 Gates: Aussprache, Prosodie, Audio, Profile
python3 scripts/ff_voice_audio.py --selftest     # 105 Gates: Block-Parität, Tabellen, Injektion, Wortuhr
```

Die Suiten laufen im Workflow **„Lesehilfen-Gate (Vorlesen + Kurzfassung)“** – bei jedem Push/PR auf Lesehilfen oder Content sowie täglich um 08:20 MESZ.

Report: `LESEHILFEN-STUDIO-2026-09-05.md`.

---

## 🗞️ Premium-Governance (Chefredakteur-Cockpit · v2, gehärtet 07.09.2026)

Die Blogautomatik prüfte schon viel — jetzt **steuert** sie auch, und zwar ohne
Dauer-Alarm. Der Workflow **„Premium-Governance"** (Mo 07:15 MESZ) läuft in vier
Klar getrennten Phasen — **Messen → Sehen → Bewerten → Melden**:

| Phase | Skript | Was passiert |
|---|---|---|
| **0 · Preflight** | `scripts/governance_contract.py` (C1–C9) + `--selftest` aller Wachen | Kaputte Wachen liefern falsche Sicherheit → erst Selbsttest, dann Messung. Läuft auch bei **jedem** Push/PR im Qualitäts-Gate. |
| **1 · Messen** | `hugo --minify`, `scripts/decay_radar.py`, `scripts/cwv_guard.py --strict-build`, `scripts/secrets_age_guard.py --verify`, `scripts/pinterest_perf_feedback.py`, `scripts/umami_clicks.py`, `scripts/awin_provisions.py` | Alle Signale werden **frisch** erzeugt. Secret-Health = Live-Probe gegen die Kanal-API (Pinterest `/v5/users/me`, Mastodon `verify_credentials`, Groq/Gemini `/models`), nicht „steht im Env". |
| **2 · Sehen** | `scripts/editorial_scorecard.py` | Die Scorecard läuft direkt nach dem Messen (sie braucht die Werte *desselben* Laufs, nie die der Vorwoche) → `EDITORIAL-SCORECARD.md` + Trend `data/scorecard_history.jsonl`. |
| **3 · Bewerten** | `scripts/governance_gate.py` | Eine dokumentierte Policy entscheidet über **alle** Schritte (auch über die Sicht), was ein **Befund** ist (rot/gelb) und was nur **Datenlage** (ℹ️). Ledger: `data/governance_status.json`, Verlauf: `data/governance_history.jsonl`, Job-Summary inklusive. |
| **4 · Melden** | Gate + `gh issue` | **Ein** Issue pro Befundlage: offenes Issue wird aktualisiert (bei verändertem Fingerabdruck neuer Body, sonst nur Kommentar), bei Grün automatisch geschlossen. Kein Wochen-Duplikat mehr. |

```bash
python3 scripts/governance_gate.py --rehearse      # Was würde der Lauf heute entscheiden? (schreibt nichts)
python3 scripts/governance_contract.py             # Governance-Vertrag C1–C9 prüfen
python3 scripts/editorial_scorecard.py             # Scorecard aus dem Bestand
python3 scripts/cwv_guard.py --public public/ --strict-build   # Performance nach dem Build
python3 scripts/secrets_age_guard.py --verify      # Live-Probe gegen alle Kanäle
python3 scripts/umami_clicks.py --fetch            # Klick-Daten automatisch laden
```

### Was der Governance-Report #206 dauerhaft behoben hat

| Befund aus #206 | Ursache | Zustand jetzt |
|---|---|---|
| Scorecard „Core-Web-Vitals **AMBER**", Wächter meldet GREEN | Scorecard lief im Workflow **vor** der Messung und las das Manifest der Vorwoche | Messen → Sehen (Reihenfolge ist jetzt Regel **C1**), Scorecard-Zeile trägt Alter der Messung; „nicht gemessen" = ⚪ statt 🟡 |
| `PINTEREST_ACCESS_TOKEN` dauerhaft „UNBEKANNT" → jeder Lauf rot/gelb | Einziger Nachweis-Lieferant (`pinterest-ai.yml`) lief seit 20.08. nur noch manuell | Tägliche Live-Probe im Pinterest-Watchdog + wöchentliche `--verify`; Erfolg gilt nur bei HTTP 200, Ablehnung = **rot** |
| `PINTEREST_ACCESS_TOKEN` 401 – **jeden Monat aufs Neue** (Folge-Issues #153, #209) | Kein Lebenszyklus: 30-Tage-Token von Hand, sechs Skripte mit sechs Token-Reihenfolgen, Live-Probe gegen den v3-Pfad `/v5/users/me`, harter 401-Abbruch statt Queue-Modus | **Token-Broker** `scripts/pinterest_token.py` (eine Quelle, Failover, proaktive Erneuerung) + **tägliche Token-Wache** `pinterest-token.yml` (continuous refresh, verschlüsselt committet) + Vorwarnung `manual_token`/`refresh_rotation`, **bevor** der Kanal steht. Regeln **C10–C12** halten das fest. Details: `GOVERNANCE-206-BEHOBEN-2026-09-07.md` |
| `GROQ/GEMINI_API_KEY` „OK (6d)" | Der Governance-Lauf vermerkte Erfolg für Keys, die er nie benutzt (Selbst-Wäsche) | Regel **C5**: Nachweis nur mit `--proof-by <workflow>`, und nur dort, wo das Secret gerçekten gebraucht wird |
| Issue #145 + #206 = Duplikate im Wochenrhythmus | Issue an rohen Exit-Codes aufgehängt; „noch keine Daten" war ein Fehler | Policy im Gate: ℹ️-Datenlage ≠ Befund; ein Issue, aktualisiert statt neu created, close bei Grün |
| „Affiliate-Klicks 0 / Awin 0,00 €" ohne Ende | Manueller Dashboard-Export als einzige Datenquelle | `scripts/umami_clicks.py` holt die Klicks selbst (Secret `UMAMI_API_TOKEN`, Website-ID aus `hugo.toml`); ohne Token sauberes Skip + dokumentierter Grund statt Schein-Null |
| CWV könnte GREEN melden, ohne gebaut zu haben (`hugo … \|\| true`) | Messung auf leerem/altem `public/` | `--strict-build`: fehlender/leerer Build = Befund `build_missing`, Manifest-Feld `build_measured` (Regel **C2**) |
| Reports/Manifeste konnten bei Parallel-Läufen halbbeschrieben werden | `open(...,"w")` ohne Sperre/Atomicity | Alle State-Schreibungen atomar (`tmp` + `os.replace`) und bei der Secrets-Wache zusätzlich mit Dateisperre; kaputter State wird gesichert + neu begonnen statt abzustürzen |

**Neu im Set:** `scripts/governance_gate.py` (Bewertungs-Policy + Issue-Entscheidung),
`scripts/governance_contract.py` (Vertrag C1–C12, im Qualitäts-Gate bei jedem Push/PR),
`scripts/pinterest_token.py` (Token-Broker mit Failover + Lebenszyklus-Lagebild),
`scripts/umami_clicks.py` (Umsatz-Datenpipeline). Verlauf Artefakte:
`data/cwv_history.jsonl`, `data/scorecard_history.jsonl`,
`data/governance_status.json`, `data/governance_history.jsonl`,
`data/secrets_state.json` (jetzt mit Nachweis-Qualität `proven`/`declared`),
`data/umami_clicks.meta.json`. Details & Belege: `GOVERNANCE-HAERTUNG-2026-09-07.md`,
Regelwerk maschinenlesbar: `docs/GOVERNANCE-KONTRAKT.md`.

> **Datennachschub für die Monetarisierungs-Schleifen** (einmalig, 5 Min.):
> `UMAMI_API_TOKEN` als Repository-Secret anlegen (Umami → Avatar → *User Settings* →
> *API* → *Generate API Key*) — schon füllt der wöchentliche Governance-Lauf
> `data/umami_clicks.json` selbst, und Scorecard/Klick-Report rechnen mit echten
> Klicks. Awin bleibt CSV-basiert: Export nach `data/awin_transactions.csv` legen,
> `python3 scripts/awin_provisions.py` (bzw. `--gen-subid-map` für die SubID-Zuordnung)
> läuft im gleichen Workflow.

## 🚀 In 15 Minuten live

### 1. Repository anlegen & hochladen

1. Auf [github.com](https://github.com) → **New repository** → Name z. B. `sparratgeber24` (public oder private, beides ok)
2. Lokal im Projektordner:

```bash
cd check24-blog
git init
git add -A
git commit -m "Initial: Hugo-Blog mit Content-Automatisierung"
git branch -M main
git remote add origin https://github.com/DEIN-USERNAME/sparratgeber24.git
git push -u origin main
```

### 2. GitHub Pages aktivieren

GitHub → Repo → **Settings → Pages** → Source: **GitHub Actions** → Save.
Danach läuft der erste Build automatisch. Deine Seite ist live unter:
`https://DEIN-USERNAME.github.io/sparratgeber24/`

### 3. Eigene Domain (empfohlen, ~10–15 €/Jahr)

1. Domain kaufen (z. B. IONOS, Namecheap, Netlify Domains)
2. In `hugo.toml`: `baseURL = "https://www.deine-domain.de/"` eintragen
3. GitHub → Repo → **Settings → Pages → Custom domain** eintragen
4. Beim Domain-Anbieter DNS-Einträge setzen (Anleitung zeigt GitHub an)
5. Push → fertig. HTTPS stellt GitHub automatisch bereit.

**Alternative Cloudflare Pages** (empfohlen für EU + schnelleres CDN, ebenfalls kostenlos): Cloudflare Dashboard → Workers & Pages → Create → *Connect to Git* → Repo auswählen → Build command: `hugo --minify` → Output: `public`. Hugo-Version 0.164.0 einstellen. Kostenlos, unbegrenztes Datenvolumen.

### 4. Content-Bot aktivieren (kostenlos, 2 Minuten)

Der Bot braucht **einen** Gratis-KI-Key (ohne Zahlungsdaten):

| Anbieter | Key holen | Warum |
|---|---|---|
| **Groq** (empfohlen) | [console.groq.com](https://console.groq.com) → API Keys | sehr gut für deutschsprachige Artikel, großzügiges Gratis-Kontingent |
| **Gemini** (Google) | [aistudio.google.com](https://aistudio.google.com) → Get API key | ebenfalls kostenlos |

Dann im GitHub-Repo: **Settings → Secrets and variables → Actions → New repository secret**:

- Name: `GROQ_API_KEY` (oder `GEMINI_API_KEY`) – Wert: dein Key

**Optional (Repository variables):**
- `BLOG_AUTHOR` → Name, der unter den Artikeln steht (Standard: „Redaktion")
- `AFFILIATE_URL` → dein CHECK24-Partnerlink (Standard: Platzhalter)
- `MIN_ARTIKEL_PRO_TAG` / `MAX_ARTIKEL_PRO_TAG` → Artikel pro Publikationstag (Standard: 2–3, nur Mo/Mi/Fr – Dauervorgabe, siehe `CADENCE-REPORT.md`)
- `GROQ_MODEL` → Groq-Modell (Standard: `openai/gpt-oss-120b`; zentrales Modul `scripts/groq_config.py`. `llama-3.3-70b-versatile` ist seit 16.08.2026 abgeschaltet und wird automatisch gemappt.)

**Ab jetzt:** An Publikationstagen (Mo/Mi/Fr) um 08:10 Uhr (DE) erzeugt und veröffentlicht die **Content-Engine v2** automatisch 2–3 Artikel (Fallback-Slots 16:10/19:40, falls der Haupt-Slot an API-Limits scheitert). Nur Artikel, die das Profi-Qualitäts-Gate bestehen, gehen live – alles andere wird als Entwurf gesichert und per Issue gemeldet.

### 5. Entwürfe veröffentlichen

```bash
# Einen Artikel veröffentlichen (draft: true → false):
python3 scripts/publish.py content/posts/2026-08-05-mein-artikel.md

# Alle Entwürfe veröffentlichen:
python3 scripts/publish.py --all

# Danach pushen – GitHub Pages baut automatisch neu:
git add -A && git commit -m "Artikel veröffentlicht" && git push
```

Oder manuell: Datei öffnen → `draft: true` → `draft: false` → pushen.

---

## 🧠 Wie der Content-Bot funktioniert

1. Wählt zufällig ein Thema aus `data/topics.yaml` (12 Nischen, frei erweiterbar)
2. Rotiert durch 6 Schreibstile (Ratgeber, Vergleich, Fehler-Vermeidung, FAQ, Checkliste, Hintergrund) → jeder Artikel ist strukturell anders
3. Ruft die KI (Groq/Gemini) mit striktem Prompt auf: deutscher Titel, Meta-Description, 4–6 H2-Abschnitte, FAQ, 400–700 Wörter, keine erfundenen Preise
4. Schreibt den Entwurf mit SEO-Frontmatter (Titel, Description, Keywords, Tags) + Affiliate-CTA + Werbekennzeichnung
5. Duplikat-Schutz: bereits vorhandene Titel werden übersprungen

**Themen erweitern:** `data/topics.yaml` öffnen, neue Zeilen ergänzen – fertig.

**🛡️ Lösch-Schutz (verhindert Datenverlust):**

Der Bot unterscheidet strikt zwischen echten Artikeln und Demo-Dateien.
Nur Dateien mit dem Marker `demo-artikel` im Inhalt dürfen aufgeräumt
werden – echte Artikel (auch Bot-generierte) sind vor versehentlichem
Löschen geschützt (`demo_files()`-Check im Skript).

**Einzigartigkeits-Audit für bestehende Artikel:**
```bash
python3 scripts/check_uniqueness.py            # Standard-Check (7-Wort-Phrasen)
python3 scripts/check_uniqueness.py --strict   # strengerer Check (5-Wort-Phrasen)
```
Prüft alle Artikel gegen die Pinterest-Pin-Texte UND untereinander (interne Duplikate).
Template-Bausteine (Werbekennzeichnung, CTA, FAQ-Rahmen) werden automatisch
herausgefiltert – nur der echte Fließtext zählt. Unter 5 übereinstimmenden
7-Wort-Phrasen ist unkritisch (normale Standard-Formulierungen).

**Einzigartigkeit statt 1:1-Kopien:** Die Pinterest-Pins (in `data/pinterest_plan.yaml`)
dienen dem Bot NUR als Inspirationsquelle (Thema, Keywords, Pinwand). Der Prompt
verpflichtet die KI zu eigenem Wortlaut, eigener Struktur und eigenem Titel.
Zusätzlich prüft ein **Einzigartigkeits-Check** den fertigen Text gegen die
Pin-Beschreibung (7-Wort-Phrasen): Ist der Artikel zu ähnlich, wird er mit
anderem Stil und anderer Erzählperspektive automatisch neu generiert.
Im Frontmatter jedes Bot-Artikels steht `inspiration:` als Nachweis, dass nur
die Themen-Grundlage vom Pin stammt.

**Lokal testen (ohne Key):**

```bash
DEMO_MODE=1 python3 scripts/generate_drafts.py   # erzeugt Test-Entwurf
```

---

## ⚖️ Rechtliches – Pflicht für Affiliate-Seiten in DE

- [ ] **Impressum** ausfüllen (`content/impressum/index.md`) – Platzhalter ersetzen, § 5 DDG
- [ ] **Datenschutzerklärung** anpassen (Generator wie eRecht24/IT-Recht Kanzlei empfohlen)
- [ ] **Affiliate-Links kennzeichnen** – im Blog bereits eingebaut (Hinweis + Disclaimer in `hugo.toml`)
- [ ] **CHECK24-Partnerprogramm** – Anmeldung (z. B. über das Awin-Netzwerk), Voraussetzung: eigene Website
- [ ] **Persönliche Partnerlinks einsetzen** – zentral in `scripts/check24_links.yaml` pflegen und mit `python3 scripts/affiliate_shield.py --fix` + `python3 scripts/affiliate_link_check.py --fix` in Artikel/Gateway übernehmen (siehe `ANLEITUNG-CHECK24-LINKS.md`)
- [ ] **Steuer** – Provisionen sind Einkünfte (Steuererklärung!)
- [ ] **Marke:** keine Domain mit „check24" im Namen verwenden

**Rechtstexte-Status (30.08.2026):** Impressum + Datenschutz auf Generator-Niveau aktuell (Abgleich gegen eRecht24 Basis 1.50 – Diffs & Begründungen: `RECHT-UPDATE-REPORT.md`). Neu seit 30.08.: Drittlandtransfer USA über **EU-US Data Privacy Framework** (Art. 45 DSGVO) für GitHub Pages/Cloudflare, **KI-Transparenzhinweis** (Art. 50 EU-KI-VO, seit 02.08.2026) im Impressum.

**⏰ Fristen-Erinnerungssystem (kostenlos, eingebaut 30.08.2026):** `data/recht-fristen.yaml` + `scripts/fristen_check.py` + Workflow „Fristen-Check (Recht)" (täglich 07:55 MESZ) erinnern an Rechts-Fristen (Halbjahres-Rechtstexte-Abgleich, KI-VO-Kennzeichnung 02.12.2026, DPF-Zertifikats-Check, Partnerbedingungen, Rechtslage-Screening) und eskalieren über GitHub-Issues (`frist` → `frist-eskalation`, Stufen +0/+14/+30 Tage). Zusätzlich täglicher Veraltungs-Scan (TMG/TTDSG/OS-Plattform-Reste) + Stand-Alter-Prüfung der Rechtstexte. Aktueller Stand: `FRISTEN-REPORT.md`. Erledigen: Actions → „Fristen-Check (Recht)" → Run workflow → `erledigt=<frist-id>`.
**Workflow-Anbindung als Patch bereit** (Push durch Agent-Token ohne `workflows`-Scope blockiert, gleiche Situation wie Heading-Gate 27.08.): `patches/fristen-check-2026-08-30-workflows.patch` – einmalig einspielen mit `git apply patches/fristen-check-2026-08-30-workflows.patch && git add .github && git commit -m "ci: Fristen-Check-Workflow" && git push` (lokal oder mit vollwertigem Token). Bis dahin läuft der Check manuell: `python3 scripts/fristen_check.py` (Issue-Eskalation mit `GH_TOKEN` gesetzt).

---

## 🔍 SEO-Checkliste nach dem Launch

- [ ] `baseURL` in `hugo.toml` auf echte Domain gesetzt (sonst zeigen Sitemap/Canonical auf den Platzhalter!)
- [ ] Google Search Console einrichten → Sitemap `https://deine-domain.de/sitemap.xml` einreichen
- [ ] Bing Webmaster Tools (kostenlos, gleiche Sitemap)
- [ ] Blog-Name + Beschreibung in `hugo.toml` angepasst
- [ ] Eigenen CHECK24-Link überall ersetzen (Search & Replace nach `DEINE-AFFILIATE-ID-HIER-EINFUEGEN`)

---

## ❓ FAQ

**Kostet das wirklich nichts?** Ja. GitHub Pages, GitHub Actions und die KI-Keys (Groq/Gemini Gratis-Tarif) sind kostenlos. Optional: Domain ~10–15 €/Jahr.

**Warum Entwürfe statt automatischer Veröffentlichung?** Google bestraft massenhaft automatisch veröffentlichten KI-Content. Kurzes Prüfen + Freigeben schützt dein Ranking – und macht die Artikel besser (du ergänzt z. B. eigene Erfahrungen).

**Wie oft erscheint neuer Content?** Dauervorgabe: 2–3 Artikel an Publikationstagen (Mo/Mi/Fr), gesteuert über `MIN_ARTIKEL_PRO_TAG` / `MAX_ARTIKEL_PRO_TAG` und erzwungen durch `cadence_guard.py` (Details: `CADENCE-REPORT.md`).

**Kann ich den Bot stoppen?** GitHub → Actions → Workflow „Tägliche Content-Generierung" → Disable workflow.

**Was, wenn der Bot fehlschlägt?** Schau in die Workflow-Logs (Actions → Run → Logs). Häufigste Ursache: Key falsch gesetzt oder Kontingent erreicht – dann wechsle auf den anderen Anbieter oder warte bis zum nächsten Tag.

---

## 📌 Pinterest-Integration (Masterplan August 2026, Premium-Phase 2)

Der Themenpool `data/topics.yaml` ist 1:1 aus deinem Pinterest-Masterplan
(`data/pinterest_plan.yaml`, 73 Pins) abgeleitet.

**Premium-Regel (automatisch durchgesetzt):** `Pin → eigener Blogartikel → Affiliate-CTA`.
Nie direkt aufs Pinterest-Profil (Sackgasse) und nie nackt auf CHECK24 (Spam-Signal).

**So wird das verlinkt (alle Schichten automatisch, s. `PINTEREST-PREMIUM-STRATEGIE.md` § 12–14):**

| Schicht | Skript | Aufgabe |
|---|---|---|
| Zielseite | `scripts/pinterest_link_healer.py` | Weist jeden der 73 Pins per Scoring auf den bestmöglichen Artikel/Pillar-Seite (UTM inkl.) |
| Premium-Texte | `scripts/pinterest_pin_text_sync.py` | Überträgt die kuratierten Pin-Titel/-Beschreibungen + `pinwand` in die Artikel (1:1 + Board-Gate) |
| Zielseiten-Garantie | `scripts/pinterest_link_guard.py` | LOCAL: Slug-Existenz/Draft/Domain/UTM/URL-Form · LIVE (CI): HTTP 200 + Domain-Bleibepflicht + Rich-Pin-Meta |
| Posting | `scripts/pinterest_engine.py` | Pinnt neue Artikel per API v5 auf das **richtige der 6 Boards** (Routing per Pinwand/Pillar, Board-Auto-Creation), Drafts nie |
| Profil | `scripts/pinterest_profile_audit.py` | Live-Profil (Name/Bio/Boards) vs. Premium-Soll → Copy-Paste-Report |
| Rich Pins | Hugo-Templates + `layouts/_default/rss.xml` | og:image (sauber, 1000×1500), Pin-It-Button auf jedem Artikel, RSS-Auto-Publish mit Cover + Premium-Description |- **26.08.2026 (Spam-Schutz):** `spam_guard.py` neu – dauerhafter
  Spam-Schutz mit sofortiger Selbstheilung für alle vier Kanäle
  (Blog B1–B8, RSS-Feed F1–F6, CSV-Upload C1–C8, Pinterest-API A1–A4;
  Details: `SPAM-SCHUTZ.md`). Kern: Cross-Channel-Pin-Registry
  (`data/pin_history.jsonl`, Repeat-Fenster 30 Tage, Füllung auch aus
  den RSS-Live-Pins via `--sync-pins`), API-Rate-Limits 10/h + 40/Tag
  mit eskalierender Pause (1 h → 24 h → 7 Tage) bei Spam-/Rate-
  Antworten, `--gen-csv` (kanonisches Pinterest-Bulk-Format,
  Kadenz-verteiltes Scheduling) + CSV-Validator mit Live-Link-Check.
  Eingebunden: Deploy-Gate (vor Publish), Content-Engine v2 (neue
  Artikel), Pinterest-Watchdog (täglich + sync-pins), Blog-Health
  (täglich) – und UNBYPASSBAR in `pinterest_engine.py` /
  `generate_pins.py` (A1–A4 im Code). Erster Beleg-Lauf: 20 Posts
  geheilt (B8: `*Werbung`-Präfix in `pin_description` – ohne diesen
  Fix hätte die API Pin-Texte ohne Werbekennzeichnung erstellt),
  danach 0 harte Funde, 18 live / 7 draft (Kadenz unverändert).
  Selftest: 27 eingefrorene Fälle inkl. Regression „B2-warn +
  B8-hard → heilen, nie demoten“.


**Transactional-Pins (TP) → CHECK24:** Die TP-Pins (Strom, Gas, DSL, Girokonto, Kredit, Kfz, Reisen, Mietwagen, Flüge) sind im Pool – mit dem passenden CHECK24-Link pro Artikel (`affiliate_url` über `scripts/check24_links.yaml`). Manuelle TP-Pins immer über die eigene Gateway-URL `franksfinanzcheck.de/go/<kategorie>/` pinnen (nie nackten CHECK24-Link).

**Zielseiten-Zuordnung aller Pins im Blick:** `PINTEREST-LINK-REPORT.md` (Zuordnung + Scores + Content-Lücken) · `PINTEREST-LINK-GUARD-REPORT.md` (Reachability) · `PINTEREST-PROFILE-REPORT.md` (Profil-Soll-Abgleich).
