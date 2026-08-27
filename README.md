# FranksFinanzcheck – Hugo Affiliate-Blog (CHECK24)

Ein **kostenloser**, SEO-optimierter Blog mit **automatischer Content-Versorgung** – gebaut mit Hugo + PaperMod, hostbar kostenlos auf GitHub Pages oder Cloudflare Pages. Die Themen sind abgestimmt auf den **Pinterest-Masterplan** (FranksFinanzcheck, August 2026): Jeder Educational-Pin bekommt einen passenden Blog-Artikel, jeder Transactional-Pin eine eigene CHECK24-Kategorie.

> ⚠️ **Hinweis zur Automatisierung (Stand 26.08.2026):** Der Bot veröffentlicht Artikel automatisch, aber NUR wenn sie mehrere harte Qualitäts- und SEO-Gates bestehen (Profi-Qualitäts-Gate, `publish_gate.py`, `quality_score.py` ≥ 0,85) – siehe Abschnitt „Vollautomatik ohne manuelles Eingreifen" unten. Kein manueller Freigabe-Schritt mehr nötig; die Publikationsfrequenz ist fix auf Mo/Mi/Fr mit 2–3 Artikeln pro Tag begrenzt, um „Scaled Content Abuse"-Risiken bei einer jungen Domain zu vermeiden (DAUERVORGABE, siehe CADENCE-REPORT.md). **Seit 26.08.2026 wird die Routine HART erzwungen:** Vor jedem Publish (Deploy, Engine, manuell) prüft und heilt ein Gate-Komplex (`cadence_guard.py` + `publish_gate.py` + Titel-/Cover-Gates) Kadenz und Cover-Text-Komplettheit automatisch – Verstöße können nicht mehr live gehen, der Bestand heilt sich selbst (Details: `CADENCE-REPORT.md` Regel 5).

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
| **Deploy-Gate** (`deploy.yml`) | Vor jedem Hugo-Build: Kadenz-Selbsttest → `cadence_guard.py --fix` (Zurückstufung + Re-Queue bei Verstößen) → Titel-Gate → Cover-Gate → Build. Heilungen werden gepusht. |
| **Engine-Phase 0.5** | Vor JEDEM Slot: Kadenz-Gate stellt die Tageszahl auf den korrekten Stand (Selbstheilung) |
| **Engine-Publish-Gate** | 5 harte Prüfungen inkl. **Cover-Text-Komplettheit** (unvollständiger Titel → Verwurf bzw. Zurückstufung) |
| **Engine-Phase 6** | `engine_issue.py --deficit`: Tagesende unter Minimum → sichtbares, auto-schließendes Issue |
| **Blog-Health (täglich)** | Heilt auch ZWISCHEN den Publishing-Slots (Kadenz, Titel, Covers) |
| **`publish.py` (manuell)** | Gleiche Routine wie die Automation – Verstoß blockiert hart (Notfall: `--force-cadence`) |

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

**Einmalige Einrichtung (~10 Min.):** Siehe `ANLEITUNG-PINTEREST-API.md`
- Pinterest-Developer-App + Access-Token → Secret `PINTEREST_ACCESS_TOKEN`
- Board-ID (`python3 scripts/pinterest_engine.py --list-boards`) → Variable `PINTEREST_BOARD_ID`

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
