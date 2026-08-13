# FranksFinanzcheck – Hugo Affiliate-Blog (CHECK24)

Ein **kostenloser**, SEO-optimierter Blog mit **automatischer Content-Versorgung** – gebaut mit Hugo + PaperMod, hostbar kostenlos auf GitHub Pages oder Cloudflare Pages. Die Themen sind abgestimmt auf den **Pinterest-Masterplan** (FranksFinanzcheck, August 2026): Jeder Educational-Pin bekommt einen passenden Blog-Artikel, jeder Transactional-Pin eine eigene CHECK24-Kategorie.

> ⚠️ **Wichtiger Hinweis zur Automatisierung:** Der Bot erzeugt täglich **Entwürfe** (`draft: true`), die du vor dem Veröffentlichen kurz prüfst. **Nicht** automatisch veröffentlichen lassen: Google wertet massenhaft automatisch publizierten KI-Content als Spam („Scaled Content Abuse") und kann die ganze Seite abwerten. Entwurf → prüfen → mit einem Klick veröffentlichen ist der google-sichere Weg.

---

## 📋 Was ist enthalten

| Baustein | Details |
|---|---|
| Hugo-Blog | Theme PaperMod (SEO-fertig: Meta-Tags, OpenGraph, JSON-LD, Sitemap, robots.txt, Canonical) |
| Pflichtseiten | Impressum (mit Platzhaltern), Datenschutz, Über – Werbekennzeichnung inklusive |
| 2 Beispiel-Artikel | Stromwechsel & Kfz-Versicherung (dienen als Vorlage/Struktur) |
| Themenpool | `data/topics.yaml` – 175 Themen über alle 6 Pillars (repariert & erweitert 13.08.2026, reicht bei 4 Artikeln/Woche über 1 Jahr), inkl. themenspezifischer CHECK24-Links |
| 🤖 Content-Bot | `scripts/generate_drafts.py` – erzeugt täglich frische, einzigartige Artikel-Entwürfe (Titel, Meta-Description, Keywords, strukturiertes Markdown, FAQ, Affiliate-CTA) |
| ⏰ Täglicher Job | `.github/workflows/daily-content.yml` – läuft automatisch um 07:00 Uhr (Sommerzeit) |
| 🚀 Deployment | `.github/workflows/deploy.yml` – baut & veröffentlicht kostenlos auf GitHub Pages |
| 📤 Publish-Helfer | `scripts/publish.py` – Entwürfe mit einem Befehl veröffentlichen |

---

## ⚡ Automatik mit manueller Freigabe (Stand 13.08.2026)

Zwei Workflows sichern an **4 Publikationstagen/Woche (Mo/Mi/Fr/Sa)** je
**1 fertigen, qualitätsgeprüften Artikel** (= max. 4/Woche statt vorher
2/Tag = 14/Woche): **„Content-Engine v2"** (`content-engine-v2.yml`,
mehrere Zeitfenster ab 08:10 MESZ, nur an Publikationstagen) und
**„Tagesziel 1 Post"** (`tagesziel-1-post.yml`, Nachlauf-Slots an
denselben Tagen), falls das Tagesziel sonst nicht erreicht würde. Die
ältere, in dieser Tabelle früher beschriebene „Automatische
Content-Generierung" (`daily-content.yml`) ist deaktiviert (nur manuell
startbar) – die Zeiten oben sind daher nicht mehr aktuell, siehe die
Cron-Zeilen direkt in `content-engine-v2.yml`.

**Warum die Frequenz-Reduktion (13.08.2026, von 2/Tag auf 1 Artikel an
4 Tagen/Woche)?** Tägliches Massen-Publizieren rein KI-generierter
Artikel ist genau das Muster, das Googles "Scaled Content Abuse"-
Klassifizierer erkennen soll – besonders riskant bei einer noch jungen
Domain. Bei einem Nischen-Finanzblog zählt zudem Tiefe/Vertrauen
(E-E-A-T) mehr als Frequenz: 4 wirklich hilfreiche Artikel/Woche schlagen
14 durchschnittliche langfristig fast immer. Ändern: Repo-Variable
`MAX_ARTIKEL_PRO_TAG` (max. 2, hartes Cap im Code) und die Cron-Tage in
beiden Workflow-Dateien.

**Betriebsregel seit 13.08.2026 – nur Profi-Qualität geht automatisch live:**
- Jeder generierte Artikel durchläuft die volle Qualitäts-Kette (Rechtschreibung,
  Grammatik, Cover, Meta, interne Links, Affiliate-Guards, …) genau wie zuvor
  und muss dabei das harte **Profi-Gate** bestehen (`engine_level: "profi"`
  im Frontmatter). Es gibt seit 13.08.2026 (Nachmittag) **keine abgeschwächte
  Relaxed-Zwischenstufe mehr** – die gab es zuvor als Kompromiss fürs
  Tagesziel, wurde aber ersatzlos gestrichen: Ein Artikel ist entweder
  Profi-Niveau oder er wird gar nicht erst automatisch veröffentlicht.
- **Nur Profi-Artikel werden automatisch veröffentlicht** (`draft: false`).
- **Jede Qualitäts-Rettung** (die KI erreicht auch nach 5 Versuchen kein
  Profi-Niveau) **bleibt als Entwurf** (`draft: true`) liegen
  (`engine_level: "draft"`) – dafür bekommst du ein Freigabe-Issue.
- **Hartes Publish-Gate (13.08.2026, `scripts/publish_gate.py`):** Selbst ein
  als "Profi" eingestufter Artikel geht erst NACH drei zusätzlichen,
  automatisierten Prüfungen wirklich live – direkt vor dem Deploy-Trigger:
  1. `check_length.py` – Zeichen-/Wortlänge (700–1800 Wörter)
  2. `seo_audit.py` – Title-/Description-Länge, Wortzahl, Alt-Texte, Sitemap
  3. `affiliate_profi_check.py` (A1–A8) – Offenlegung, E-E-A-T-Feld, interne
     Links, Schema.org, Affiliate-Dichte, Trust-Box, Autor, CTA
  Besteht ein Artikel eine dieser Prüfungen nicht (auch nach den
  Selbstheilungs-Läufen davor), wird er automatisch auf `draft: true`
  zurückgestuft statt live zu gehen – landet dann im normalen
  Freigabe-Issue. Kein Artikel geht mehr live, ohne dass diese drei
  Prüfungen tatsächlich bestanden wurden.
- Für wartende Entwürfe bekommst du automatisch ein **GitHub-Issue**
  ("📝 Content-Engine: Entwurf wartet auf Freigabe") – erscheint nur, wenn
  tatsächlich etwas zu prüfen ist, bleibt offen bis du es schließt (kein
  Spam bei mehreren Artikeln).
- **Freigeben:** Datei unter `content/posts/<datum-slug>/index.md` öffnen,
  `draft: true` → `draft: false` ändern, committen – der nächste Deploy
  veröffentlicht ihn. Oder lokal: `python3 scripts/publish.py <slug>`.
  Tipp fürs schnelle Freigeben mit wenig Aufwand: verbleibende Entwürfe
  1x/Woche gesammelt durchgehen, dabei jeweils einen eigenen Satz ins
  bereits vorhandene `erfahrung:`-Feld ergänzen (günstigster E-E-A-T-Hebel).
- Das 1-Artikel/Tag-Limit (an Publikationstagen) gilt weiterhin (zählt
  Artikel, die das Profi-Gate bestanden haben – unabhängig vom draft-Status),
  es werden also nie mehr Entwürfe angehäuft als geplant.
- **Modus wechseln:** Repo-Variable `AUTO_PUBLISH` – `profi` (Standard: nur
  Profi-Artikel automatisch, alles andere Entwurf), `0` (immer manuell,
  auch Profi-Artikel), `1` (Vollautomatik, alte Betriebsart – nicht empfohlen).

**Warum überhaupt Entwürfe statt automatischer Veröffentlichung?** Google
bestraft massenhaft automatisch veröffentlichten KI-Content ("Scaled
Content Abuse"). Kurzes Prüfen + Freigeben schützt dein Ranking – und
macht die Artikel besser (du ergänzst z. B. eigene Erfahrungen, bevor sie
live gehen).

**Steuerung:**
- **Stoppen (Kill-Switch):** GitHub → Actions → „Content-Engine v2" bzw.
  „Tagesziel 1 Post" → Disable workflow
- **Manuell starten:** GitHub → Actions → „Run workflow"
- **Zurück zur Vollautomatik (nicht empfohlen für YMYL/Google-Sichtbarkeit):**
  Repository-Variable `AUTO_PUBLISH` auf `1` setzen (GitHub → Settings →
  Secrets and variables → Actions → Variables). Dann werden auch
  Qualitäts-Rettungen (Ebene 2) sofort mit `draft: false` gespeichert.

**🔗 Affiliate-Links ändern – so geht's (wichtig!):**

Alle Affiliate-Links liegen zentral in **`scripts/check24_links.yaml`**. Ändern sich deine Links (z. B. neue PID, neues Link-Format, neue Partnerprogramme):

1. **Neue Artikel (Bot):** Einfach die Links in `scripts/check24_links.yaml` aktualisieren – der Bot weist neuen Artikeln automatisch die passenden Links zu (Pin → Kategorie → Link). Die Zuordnung erfolgt über die Ziel-URL des Pins (z. B. `check24.de/strom/` → Strom-Link) bzw. die Pinwand.
2. **Bestehende Artikel:** `python3 scripts/set_check24_links.py --topics` ausführen – ersetzt alle alten Links in allen Artikeln + Themenpool durch die neuen aus der YAML (sicherer Wortgrenzen-Check inklusive).
3. **Generischer Link (GitHub-Variable):** Falls nötig, in GitHub unter Settings → Secrets and variables → Actions die Variable `AFFILIATE_URL` aktualisieren.

**📌 Automatisches Nach-Pinnen bei Pinterest (montags 17:30 Uhr):**

Der Workflow **„Wöchentliches Nach-Pinnen"** erstellt jeden Montag um 17:30 Uhr (DE)
automatisch Pins für alle neuen Blog-Artikel (Cover-Bild, Beschreibung, Artikel-URL,
Hashtags) über die Pinterest API v5. Jeder Artikel wird nur einmal gepinnt
(`pinned: true`-Flag im Frontmatter).

**Einmalige Einrichtung (~10 Min.):** Siehe `ANLEITUNG-PINTEREST-API.md`
- Pinterest-Developer-App + Access-Token → Secret `PINTEREST_ACCESS_TOKEN`
- Board-ID (`python3 scripts/generate_pins.py --list-boards`) → Variable `PINTEREST_BOARD_ID`

**🔍 Automatische SEO-Optimierung (wöchentlich, kostenlos, Profi-Niveau):**

Der Workflow **„Wöchentliche SEO-Optimierung"** läuft jeden Mittwoch 07:00 Uhr (DE):

1. **SEO-Audit** (`python3 scripts/seo_audit.py`): prüft alle 30+ Artikel auf
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
- **Wöchentlich (montags 07:00 Uhr):** Der Workflow „Wöchentliches Einzigartigkeits-Audit"
  prüft alle Artikel und erstellt bei Problemen automatisch ein **GitHub-Issue** –
  du siehst es auf einen Blick im Repo (Tab „Issues").
- **Manuell:** `python3 scripts/check_uniqueness.py` (oder `--strict`)

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
- `MAX_ARTIKEL_PRO_LAUF` → Artikel pro Lauf (Standard: 1)

**Ab jetzt:** Jeden Morgen um 05:00 UTC (07:00 Uhr Sommerzeit in DE) erzeugt der Bot automatisch einen frischen Artikel-Entwurf im Repo. Du bekommst keine E-Mail – einfach mal in `content/posts/` reinschauen.

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
- [ ] **Persönliche Partnerlinks einsetzen** – siehe `ANLEITUNG-CHECK24-LINKS.md` (`python3 scripts/set_check24_links.py --topics`)
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

**Wie oft erscheint neuer Content?** Standard: 1 Entwurf pro Tag. Über `MAX_ARTIKEL_PRO_LAUF` (Variable) oder den Cron im Workflow anpassbar.

**Kann ich den Bot stoppen?** GitHub → Actions → Workflow „Tägliche Content-Generierung" → Disable workflow.

**Was, wenn der Bot fehlschlägt?** Schau in die Workflow-Logs (Actions → Run → Logs). Häufigste Ursache: Key falsch gesetzt oder Kontingent erreicht – dann wechsle auf den anderen Anbieter oder warte bis zum nächsten Tag.

---

## 📌 Pinterest-Integration (Masterplan August 2026)

Der Themenpool `data/topics.yaml` ist 1:1 aus deinem Pinterest-Masterplan abgeleitet:

**Educational-Pins (EP) → Blog-Artikel**
Die 10 wiederkehrenden EP-Themen (Frugalismus-Tricks, 50-30-20-Regel, Stromfresser, WLAN vs. Mesh, Urlaubskasse, finanzielle Freiheit, Notgroschen, Heizperiode, DNS-Server, Mietwagen-Fallen) sind als Themen im Pool. Tipp: Ändere die **DESTINATION URL** deiner EP-Pins von `pinterest.de/franksfinanzcheck/` auf den jeweiligen Blog-Artikel – so bekommen die Pins eine SEO-wertvolle Zielseite statt nur dein Profil.

**Transactional-Pins (TP) → CHECK24**
Die TP-Pins (Strom, Gas, DSL, Girokonto, Kredit, Kfz, Reisen, Mietwagen, Flüge) sind ebenfalls im Pool – mit dem passenden CHECK24-Link pro Artikel (`affiliate_url`). Die Blog-Artikel verlinken damit automatisch auf die richtige Vergleichs-Kategorie.

**Neue Artikel = neue Pin-Ideen:** Jeder vom Bot erzeugte Entwurf kann als Vorlage für einen neuen Pin dienen (Titel + Kernaussagen → Infografik).

**Fertiger Verlinkungsplan:** In `Pinterest-Blog-Verlinkungsplan.xlsx` findest du alle 62 Pins mit der jeweils passenden Blog-URL (nach Domain-Ersetzung einfach im Pinterest-Bulk-Editor eintragen).
