# 🚀 WOCHENPLAN 2026 – KW 36 (Mo 31.08. – So 06.09.)

**Auftraggeber:** FranksFinanzcheck · **Agentur-Sicht:** Wachstum / Pinterest / Affiliate
**Leitsatz der Woche:** *„Das Content-Maschinengewehr läuft – jetzt den Vertrieb einschalten: Pinterest live, Messung an, erste Backlinks setzen."*

---

## 1. Diagnose (Stand Montag, 31.08.2026)

| Bereich | Status | Kommentar |
|---|---|---|
| Content-Engine | 🟢 | 24 Artikel live, heute 3 veröffentlicht (Mo/Mi/Fr automatisch) |
| Qualität/SEO-Gates | 🟢 | Meta Ø 99/100, 0 SEO-Probleme, Einzigartigkeit ok |
| Affiliate-Kette | 🟢 | 19 CHECK24-Routen E2E gesund, /go/-Gateway + rel=sponsored |
| **Pinterest-Vertrieb** | 🔴 | **Komplettes System fertig (73-Pin-Plan, 6 Boards, 10 Pins in Queue, 18 Artikel warten) – aber OHNE Token läuft nichts. Aktuell erreicht dich null Pinterest-Traffic.** |
| **Messung** | 🔴 | Umami nicht aktiviert (`hugo.toml` → `websiteId` leer). Du steuerst blind. |
| Backlinks | 🟡 | Premium-Scout steht (7 Kanäle, Wochenpack à 5, CRM). 0 umgesetzt – diese Woche 3 Aktionen aus `BACKLINK-REPORT.md` |
| Social | 🟡 | Mastodon aktiv · LinkedIn nicht eingerichtet |

**Agentur-Fazit:** Dein Engpass ist nicht Content und nicht Technik – es ist **Distribution**. Die Woche gehört Pinterest, Messung und den ersten Backlinks.

---

## 2. Die 5 Hebel der Woche (nach Impact × Aufwand sortiert)

### 🔴 Hebel 1: Pinterest live schalten – HEUTE starten (Impact: ⭐⭐⭐⭐⭐ | Aufwand: 30 Min)

Die App-Freigabe bei Pinterest dauert **mehrere Tage (manuelle Prüfung!)** – deshalb muss der Antrag HEUTE raus, nicht Freitag:

1. **Developer-App beantragen** (10 Min): `developers.pinterest.com` → „Connect app" – Feld für Feld ausgefüllt in `ANLEITUNG-PINTEREST-API.md` Schritt 1b (Copy-Paste-fertig).
2. **Scopes ankreuzen:** `boards:read`, `boards:write`, `pins:read`, `pins:write`, `user_accounts:read`.
3. **Sobald freigegeben (E-Mail):** Token + `PINTEREST_TOKEN_KEY` als GitHub-Secrets anlegen (Schritt 2 der Anleitung). Danach postet `pinterest-ai.yml` die 10 vorbereiteten Pins aus `data/pin_queue.yaml` automatisch auf die richtigen Boards.

### 🟠 Hebel 2: Pinterest manuell vorbereiten – bis die App freigegeben ist (Impact: ⭐⭐⭐⭐⭐ | Aufwand: 45 Min, Di)

Warten auf die Freigabe? Nicht nötig – das Profil kannst du jetzt bauen (Checkliste steht in `PINTEREST-PROFIL-BEFUND.md` § 5):

1. **Business-Konto** aktivieren (Voraussetzung für Analytics & Website-Claim).
2. **Anzeigename + Bio** setzen (Copy-Paste-Block aus `PINTEREST-PROFILE-REPORT.md`).
3. **Website verifizieren:** `https://franksfinanzcheck.de/` eintragen – Claim-Datei `pinterest-e238f.html` liegt bereits im Repo, `<p:domain_verify>`-Tag ist eingebaut.
4. **6 Boards exakt nach** `data/pinterest_boards.yaml` anlegen (Namen = SEO-Suchbegriffe!) + Board-Cover hochladen (Zuordnung: `images/boards/cover-*.png`).
5. **Rich Pins** einmalig im Pinterest-URL-Debugger validieren.
6. **Übergangslösung bis Token fertig:** täglich 3–4 Pins manuell pinnen – Texte, Links (mit UTM) und Bilder stehen fertig in `data/pin_queue.yaml`. Beste Zeit laut Strategie: **18–21 Uhr** (deutsche Primetime), Reise-Pins sonntags nachmittags.

### 🟠 Hebel 3: Messung einschalten (Impact: ⭐⭐⭐⭐ | Aufwand: 20 Min, Di)

Ohne Zahlen kein Wachstums-Steuerung – aktuell weißt du nicht, ob ein Pin 0 oder 200 Klicks bringt:

1. **Umami:** kostenlosen Cloud-Account anlegen → Website-ID in `hugo.toml` bei `[params.umami] websiteId` eintragen → mit dem nächsten Deploy aktiv (cookieless, DSGVO-konform, kein Consent-Banner nötig).
2. **Google Search Console:** Verifizierung liegt bereits (`google8f0cd9537348f066.html` ist im Repo). Check: Sitemap `franksfinanzcheck.de/sitemap.xml` eingereicht? Bericht „Indexierung > Seiten" auf Crawl-Fehler prüfen.
3. **Bing Webmaster:** `BingSiteAuth.xml` liegt ebenfalls bereit – Account checken/anlegen.
4. **UTM-Disziplin:** Pinterest-Links tragen bereits `?utm_source=pinterest…` – in Umami/GSC siehst du dann sauber, welcher Kanal liefert.

### 🟡 Hebel 4: Backlink-Sprint Premium – 3 × 15 Minuten (Impact: ⭐⭐⭐⭐ langfristig | Aufwand: 45 Min, Mi/Do)

Junge Domain = Autorität fehlt. **Verdiente Editorial-Links**, keine Verzeichnisse (Google 2026 wertet Katalog-/Tausch-Links domain-level ab). Copy steht im Wochenpack von `BACKLINK-REPORT.md`, Doktrin in `BACKLINK-PREMIUM-STRATEGIE.md`:

| Tag | Aktion | Quelle |
|---|---|---|
| Mi | 2–3 **hilfreiche Antworten** in der Finanztip Community (Profil-Link in der Signatur, Link nur wenn die Frage eine Anleitung verlangt) | finanztip.de/community |
| Do | **1 Digital-PR-Pitch** mit 3 fertigen Zitaten (Kfz-Stichtag 30.11.) – z. B. Versicherungsbote oder t-online | Copy im Report |
| Do/Fr | **1 Gastbeitrag-Pitch** aus dem Wochenpack (aktuell Utopia.de – Frugalismus/Fixkosten; Alternative Sparkonto.org) – **kein** Republish | E-Mail-Vorlage im Report |

**Anti-Regel:** Kein Linkkauf, kein Linktausch, keine Blog-Verzeichnisse (Blogger.de/Sparwelt/Geld.de), kein Auto-Submit. Nach dem Senden: `python3 scripts/backlink_automation.py --mark <id>=kontaktiert`.

### 🟢 Hebel 5: Saisonhebel Kfz-Versicherung ausspielen (Impact: ⭐⭐⭐⭐ | Aufwand: 15 Min, Mi/Fr)

**Timing-Fenster:** Die Kündigungsfrist zum Stichtag 30.11. läuft am **30.09. ab** – die September-Suche nach „Kfz-Versicherung wechseln" explodiert ab jetzt:

1. Den Live-Artikel `2026-08-26-kfz-versicherung-vergleich-bis-zu-800-euro-sparen` diese Woche **2–3× pinnen** (TP-Pin mit `*Werbung`-Kennzeichnung ist vorbereitet) und auf Mastodon pushen.
2. Im Themenpool stehen 2 weitere Kfz-Themen bereit (`topics.yaml`: „Kfz-Versicherung vergleichen und sparen", „Kfz-Versicherung für Fahranfänger") – die Engine zieht sie sich je nach Plan; wenn du es erzwingen willst: `FORCE_TOPIC`-Nutzung bzw. Themenpool-Reihenfolge prüfen.
3. **CHECK24-Partnerportal:** einmal wöchentlich Klicks/Leads ansehen → welche Kategorie konvertiert, bekommt nächste Woche mehr Pins (EPC-Denken statt Traffic-Denken).

---

## 3. Tagesübersicht

| Tag | Fokus | Aufwand |
|---|---|---|
| **Mo 31.08.** | ✅ Engine lief (3 Artikel). Pinterest-App **jetzt beantragen** (Hebel 1) | 15 Min |
| **Di 01.09.** | Pinterest-Profil manuell aufbauen (Hebel 2) + Umami/GSC/Bing (Hebel 3) | 60 Min |
| **Mi 02.09.** | Publikationstag (Engine, automatisch). Backlink-Sprint Runde 1 + Kfz-Pin abends 18–21 Uhr (Hebel 4+5) | 30 Min |
| **Do 03.09.** | Gastartikel-Pitch + 3–4 manuelle Pins aus der Queue (18–21 Uhr) | 20 Min |
| **Fr 04.09.** | Publikationstag (Engine, automatisch). Token da? → Automatik prüfen: `PIN-STATUS.md` muss „aktiv" zeigen. Sonst: manuell weiterpinnen | 15 Min |
| **Sa/So 05.–06.09.** | 30 Min Pinterest-Community-Pflege (Repinnen, Kommentare) + Reise-Pin Sonntag Nachmittag + Wochenreview (KPIs unten) | 30 Min |

**Gesamtaufwand diese Woche: ~2,5–3 Stunden** – alles andere macht die Engine.

---

## 4. KPIs – so sieht „gute Woche" am Sonntag aus

| KPI | Ziel So Abend |
|---|---|
| Pinterest-App beantragt | ✅ erledigt |
| Profil: Business + Name + Bio + Website-Claim + 6 Boards + Cover | ✅ erledigt |
| Pins gepostet (manuell oder automatisch) | ≥ 10 (Queue leeren) |
| Umami `websiteId` eingetragen & live | ✅ erledigt |
| Backlinks/Community-Aktionen umgesetzt | ≥ 3 Quellen angefasst |
| GSC: Sitemap eingereicht, 0 Crawl-Fehler | ✅ erledigt |
| CHECK24-Partnerportal: Baseline notiert (Klicks/Leads) | ✅ notiert |

Ab KW 37 steuerst du dann erstmals **auf Zahlen**: welche Boards/Pins bringen Klicks → dort nachlegen.

---

## 5. Was die Agentur diese Woche bereits erledigt hat (31.08.)

- ✅ **A3-Fehler #1 behoben:** Im Handytarif-Artikel zeigten 2 Links auf einen **kaputten Pfad** (`…-dsl-tarif-fuer-dein-zu Hause/` mit Leerzeichen statt `zuhause`) → korrigiert; die Links funktionieren wieder UND zählen jetzt für die interne Verlinkung.
- ✅ **A3-Fehler #2 behoben:** Gas-Anbieter-Artikel – zwei Artikel-Links auf Gate-konforme Form `../../posts/…` umgestellt (gleiche Ziel-URL, zählt jetzt sauber).
- ✅ **Affiliate-Gate wieder komplett grün:** `affiliate_profi_check.py` → 0 Probleme (vorher 2). Der Deploy bringt die Fixes automatisch live.

---

## 6. Was du diese Woche bewusst NICHT tust

1. **Kadenz nicht erhöhen** – Mo/Mi/Fr mit 2–3 Artikeln ist genau richtig für eine junge Domain (Scaled-Content-Abuse-Risiko, siehe `CADENCE-REPORT.md`).
2. **Kein Massen-Pinnen** – max. 4–5 Pins/Tag, lieber Queue über die Woche verteilen.
3. **Keine neuen Kanäle aufmachen** (LinkedIn, TikTok…) – erst Pinterest messbar machen. Ein Kanal, der läuft, schlägt drei halbfertige.
4. **Keine Artikel-URLs ändern** – die Indexierung ist noch jung, ruhig halten.

---

*Erstellt am 31.08.2026 · Agentur-Wochenplan auf Basis von: PIN-STATUS, PINTEREST-PROFIL-BEFUND, PINTEREST-PREMIUM-STRATEGIE, BACKLINK-REPORT, ops-report.json, AFFILIATE-REPORT, Themenpool.*
