# SEO- & GEO-Premium-Optimierung – Report 21.09.2026

**Ziel:** FranksFinanzcheck dauerhaft auf Profi-Agentur-Niveau heben –
Top-Rankings bei Google & Bing, maximale Zitierbarkeit in KI-Antworten
(ChatGPT Search, Perplexity, Google AI Overviews, Claude, Le Chat, Siri).

**Arbeitshypothese bestätigt:** Die technische Basis war bereits stark
(Schema-Validierung, IndexNow, Paginierungs-Hygiene, Kurzantwort-Boxen,
FAQ auf allen Live-Artikeln). Dieser Lauf schließt die verbleibenden
Premium-Lücken – darunter zwei echte Funde mit Ranking-Relevanz.

---

## 1. Kritische Funde (behoben)

### F1 – Sichtbare Frische-Inflation auf allen Artikeln ohne `lastmod` (KRITISCH)

`layouts/_default/single.html` nutzte Hugos `.Lastmod` für die sichtbare
„Stand: … · zuletzt aktualisiert“-Zeile. Ohne `lastmod`-Frontmatter fällt
Hugo auf die Datei-Mtime zurück – im CI der **Deploy-Zeitpunkt**. Folge:
Jeder Deploy stempelte alle betroffenen Artikel sichtbar auf „Stand: heute“.
Google liest sichtbare Datums-Signale – erfundene Frische ist ein
Vertrauensrisiko (Soft-Frische-Spam).

**Fix:** Stand-Zeile nutzt jetzt `article_dates.html` (identisch zu
JSON-LD + Sitemap): Nur belegte Überarbeitungen bekommen die Zeile.
Betroffen waren 10 Live-Artikel ohne explizites `lastmod`.

### F2 – Die 6 Themen-Ratgeber wirkten dauerhaft veraltet

`layouts/pillar/single.html` zeigte „📅 Stand: 8. August 2026“ (`.Date`),
obwohl alle Ratgeber am 31.08.2026 überarbeitet wurden (`lastmod`).
Die umsatzstärksten URLs der Site trugen damit das älteste Datum.

**Fix:** Pillar-Stand nutzt jetzt ebenfalls `article_dates.html`
→ „Stand: 31. August 2026“, künftig automatisch aktuell.

### F3 – Die 6 Money-Pillars wurden nie per IndexNow gemeldet

`submit_indexnow.py` meldete nur Posts + Startseite an Bing/Yandex/Naver/
Seznam. Pillar-Updates (z. B. 31.08.) erreichten Bing nur per Zufalls-Crawl.

**Fix:** Pillars + beide Hubs + neue Methodik-Seite werden mitgemeldet.
Beim nächsten Lauf gehen 10 URLs raus (1 neuer Artikel + 9 Nachmeldungen).

---

## 2. GEO-Paket – für KI-Sichtbarkeit (NEU)

| Maßnahme | Datei | Wirkung |
|---|---|---|
| `llms.txt` + Generator | `static/llms.txt`, `scripts/generate_llms_txt.py` | Kuratierte Maschinenlese-Datei: Identität, Zitierregeln, alle 37 Artikel + 6 Ratgeber. **Dauerhaft aktuell:** Regeneration bei jedem IndexNow-Lauf (wöchentlich + bei jedem neuen Artikel), Commit via bestehende Workflow-Schritte – keine Workflow-Änderung nötig |
| robots: Applebot, MistralAI-User, YouBot erlaubt | `layouts/robots.txt` ⚠️ Signatur nötig | Siri/Spotlight/Apple Intelligence, Le Chat (stark in DE/EU), You.com dürfen nutzerseitig abrufen. Trainings-Crawler bleiben gesperrt, `ai-train=no` unverändert |
| Speakable-Schema | `layouts/_partials/schema_article.html` | `SpeakableSpecification` auf Titel + Kurzantwort → Voice-/KI-Signal |
| WebSite-Entity komplett | `layouts/_partials/extend_head.html` | `inLanguage`, Autor-Referenz, vollständiges `sameAs`, Organisations-Beschreibung + redaktioneller Kontakt |
| Publisher-Vertrauen | `layouts/_partials/schema_article.html` | Organisations-Beschreibung + E-Mail im Article-Publisher (E-Mail steht bereits öffentlich im Impressum) |
| Methodik-Seite (E-E-A-T) | `content/methodik/` | Redaktionsstandards, Recherche-Quellen, Update-Rhythmus, KI-Transparenz, Finanzierung, Korrektur-Policy – verlinkt aus Footer (siteweit), jeder Artikel-Trust-Box und Über-Seite; in Sitemap + IndexNow aufgenommen |
| `security.txt` | `static/.well-known/security.txt` | RFC-9116-Hygiene + Policy-Verweis auf Methodik |

---

## 3. SEO-Technik (NEU)

| Maßnahme | Datei | Wirkung |
|---|---|---|
| hreflang-Selbstreferenz (`de` + `x-default`) | `extend_head.html` | Sprach-/Regions-Signal für Google & Bing auf jeder URL inkl. Paginierung (head.html ist KRITISCH-versiegelt, daher bewusst hier) |
| Google-Bild-Sitemap | `layouts/sitemap.xml` | `image:image`-Tags für alle 43 Cover (Artikel + Ratgeber) – zweiter Discovery-Pfad für Google Bilder/Discover/Pinterest. Bild-Tags stehen nach `priority` (S7-Regex bleibt grün) |
| Cockpit-Härtung | `scripts/seo_cockpit.py` + Unit-Test | Bild-URLs werden nicht als Seiten gewertet (sonst falsche P1-Befunde); neuer Regressionstest `test_sitemap_ignores_image_loc_entries` |
| S8-Wache erweitert | `scripts/schema_seo_gate.py` | Kennt die 3 neuen Antwortmaschinen (Sperre = Befund, Freigabe = INFO) |

---

## 4. Verifikation (ohne Hugo – Sandbox hat keinen Build)

- **Unit-Tests:** 423 Tests, nur 4 Vorab-Fehler (fehlendes `yaml`-Modul in der Sandbox, auf Pristine-HEAD identisch reproduziert) – **0 neue Fehler**, neuer Sitemap-Bild-Test grün.
- **Gate-Selbsttests:** `schema_seo_gate --selftest` grün, `integrity_guard`-Selbsttest grün.
- **S8-Echtprüfung:** Gate-Logik direkt gegen neue `robots.txt` → 0 Befunde, 10 Antwortmaschinen erkannt.
- **Template-Hygiene:** Alle 7 geänderten Hugo-Dateien: Delimiter-/Block-Bilanz exakt ausgeglichen; neue Konstrukte spiegeln bewährte Muster (`article_dates`, `absURL`, PREM-AUDIT-Escaping).
- **Content-Guards:** `textverstaendnis_guard` + `casing_guard` + `emoji_guard` grün für alle neuen/geänderten Inhalte (0 Befunde auf Methodik/Über).
- **Offen bis CI-Build:** E2E (`npm run test:e2e`) + `seo:check --strict` laufen auf dem PR – dort wird der Hugo-Build verifiziert.

---

## 5. ⚠️ Eine Entscheidung für Frank: robots.txt-Signatur (KRITISCH)

`layouts/robots.txt` ist integritätsversiegelt (Klasse KRITISCH):
Die Änderung liegt im Branch, das Integritäts-Gate bleibt rot, bis der
Betreiber signiert – so designed (Sabotage-Schutz).

**Nach PR-Prüfung ein Befehl auf dem Branch (oder nach dem Merge auf main):**

```bash
python3 scripts/integrity_guard.py --set-current
git commit -am "chore(integrity): robots.txt (GEO-Premium 21.09.) signiert"
```

`layouts/pillar/single.html` (Klasse FEST) heilt per `--heal` automatisch
mit – oder läuft in derselben `--set-current`-Signatur mit.

---

## 6. Empfohlene nächste Schritte (Roadmap, nicht in diesem Lauf)

1. **Kfz-Wechselsaison läuft (Stichtag 30.11.):** Live-Artikel
   `2026-08-26-kfz-versicherung-vergleich-bis-zu-800-euro-sparen` jetzt
   redaktionell auffrischen (Zahlen 2026 prüfen, `lastmod` setzen) und in
   Newsletter/Pinterest priorisieren – höchstes saisonales Potenzial.
2. **Affiliate-Lücken ohne Artikel:** Zahnzusatzversicherung,
   Unfallversicherung, Tierkrankenversicherung (Hund), Ratenkredit –
   alle 4 haben `/go/`-Ziele, aber weder Live-Artikel noch Entwurf.
   Je 1 Money-Artikel = direkt messbarer Funnel-Zuwachs.
3. **Search Console & Bing Webmaster:** IndexNow-Key-Abdeckung prüfen,
   neue Methodik-URL + Bild-Sitemap in beiden Tools verifizieren,
   Klick-/Impressions-Baseline für die 6 Pillars notieren.
4. **Reserve-Hygiene:** 3 Frugalismus-Entwürfe (09-11/09-14/09-16/09-20)
   behandeln dasselbe Thema – vor Publikation zu einem Kanon-Artikel
   mergen (sonst Keyword-Kannibalisierung).
5. **Pillar-Tiefe:** Ratgeber liegen bei 1.500–1.900 Wörtern – für
   „große Ratgeber“-Ambition je 1 Vertiefungs-Abschnitt + Fallbeispiel
   einplanen (Q4-Roadmap).

---

*Erstellt 21.09.2026 · Branch `arena/01a0c332-franksfinanzcheck-blog` ·
Umfang: 13 geänderte + 5 neue Dateien.*
