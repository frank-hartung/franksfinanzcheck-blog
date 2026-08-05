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
| Themenpool | `data/topics.yaml` – 29 Themen (19 aus dem Pinterest-Masterplan + 10 weitere Nischen), inkl. themenspezifischer CHECK24-Links |
| 🤖 Content-Bot | `scripts/generate_drafts.py` – erzeugt täglich frische, einzigartige Artikel-Entwürfe (Titel, Meta-Description, Keywords, strukturiertes Markdown, FAQ, Affiliate-CTA) |
| ⏰ Täglicher Job | `.github/workflows/daily-content.yml` – läuft automatisch um 07:00 Uhr (Sommerzeit) |
| 🚀 Deployment | `.github/workflows/deploy.yml` – baut & veröffentlicht kostenlos auf GitHub Pages |
| 📤 Publish-Helfer | `scripts/publish.py` – Entwürfe mit einem Befehl veröffentlichen |

---

## ⚡ Vollautomatik (kein tägliches Pushen nötig)

Der Workflow **„Automatische Content-Generierung"** läuft abgestimmt auf deine Pinterest-Zeiten:

| Uhrzeit (DE) | Was passiert |
|---|---|
| **08:00** | Deine Pinterest-Pins erscheinen |
| **08:10** | Der Bot generiert 1 einzigartigen Artikel aus einem freien Pin-Thema und VERÖFFENTLICHT ihn automatisch |
| **19:30** | Deine abendlichen Pinterest-Pins erscheinen |
| **19:40** | Der Bot generiert + veröffentlicht den 2. Artikel des Tages |

**Wie es funktioniert:**
- Themen kommen **direkt aus deinem Pinterest-Plan** (`data/pinterest_plan.yaml`, 62 Pins)
- Der Artikel wird **automatisch veröffentlicht** (`draft: false`) – kein manueller Schritt
- Sind alle Pin-Themen abgedeckt, greift automatisch der erweiterte Themenpool (`topics.yaml`)
- Einzigartigkeits-Check + Anti-Copy-Prompt stellen sicher, dass kein Pin-Text 1:1 kopiert wird
- Max. 2 Artikel/Tag (1 pro Lauf) – Google-konform, kein Content-Spam

**Steuerung:**
- **Stoppen (Kill-Switch):** GitHub → Actions → „Automatische Content-Generierung" → Disable workflow
- **Manuell starten:** GitHub → Actions → „Run workflow"
- **Wieder auf Entwurfs-Modus:** Im Workflow `AUTO_PUBLISH: "0"` setzen (dann musst du wieder freigeben)

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
