# 🚀 Google Search Console einrichten – Schritt-für-Schritt

**Ziel:** Google findet und indexiert deinen Blog (frank-hartung.github.io/franksfinanzcheck-blog/)

**Vorab geprüft – alles bereit:**
- ✅ Sitemap erreichbar: 115 URLs (HTTP 200)
- ✅ robots.txt korrekt (mit Sitemap-Verweis)
- ✅ Startseite indexierbar (`index, follow`)

---

## Schritt 1: Search Console öffnen

1. Gehe auf **https://search.google.com/search-console**
2. Melde dich mit deinem **Google-Konto** an (das gleiche, mit dem du den Gemini-Key erstellt hast – oder ein beliebiges anderes)
3. Klicke auf **„Jetzt starten"**

## Schritt 2: Eigenschaft hinzufügen (URL-Präfix)

1. Wähle **„URL-Präfix"** (nicht „Domain" – das funktioniert nur mit eigener Domain)
2. Trage ein: **`https://frank-hartung.github.io/franksfinanzcheck-blog`**
   ⚠️ Wichtig: OHNE Schrägstrich am Ende
3. Klicke auf **„Weiter"**

## Schritt 3: Eigentum bestätigen (Verifikation)

Google bietet mehrere Methoden – **nutze die HTML-Datei-Methode** (funktioniert bei GitHub Pages am besten):

1. Wähle den Tab **„HTML-Datei"**
2. Google zeigt dir eine Datei zum Herunterladen: z. B. `google1234567890abcdef.html`
3. **Kopiere den Dateinamen** (die Zeichenfolge `google...html`)
4. **Schicke mir den Dateinamen hier im Chat** – ich lege die Datei in deinem Blog ab und pushe sie live (dauert 1 Minute)
5. Sobald deployed, klicke in Google auf **„Bestätigen"**

> **Alternativ (falls du es selbst machen willst):**
> Lege eine Datei mit diesem exakten Namen im Ordner `check24-blog/static/` an, mit dem Inhalt, den Google dir zeigt. Dann committen & pushen.

## Schritt 4: Sitemap einreichen

Nach erfolgreicher Verifikation:

1. Im GSC-Dashboard links auf **„Sitemaps"** klicken
2. Unter „Neue Sitemap hinzufügen" eingeben: **`sitemap.xml`**
3. **„Senden"** klicken
4. Status sollte „Erfolgreich" (oder „Wird verarbeitet") anzeigen

## Schritt 5: Erste Checks (optional, aber nützlich)

1. **„URL-Prüfung"** oben in der Suchleiste: `https://frank-hartung.github.io/franksfinanzcheck-blog/` eingeben → „Indexierung anfordern" klicken (beschleunigt das Finden der Startseite)
2. **„Seitenindexierung"** im Menü: Hier siehst du später, wie viele deiner 30+ Artikel Google indexiert hat
3. **„Leistung"** im Menü: Hier siehst du nach einigen Tagen Klicks, Impressionen und Suchbegriffe

---

## Was danach passiert

- Google crawlt den Blog (kann 1–7 Tage dauern, bis alles indexiert ist)
- Die 115 URLs aus der Sitemap werden nach und nach aufgenommen
- Der tägliche Bot veröffentlicht weiterhin 2 Artikel/Tag – die werden bei jedem neuen Push über die Sitemap automatisch mitgenommen

## Nützliche Zusatz-Tipps

- **Bing Webmaster Tools** (kostenlos, https://www.bing.com/webmasters): Gleiche Sitemap einreichen – Bing liefert auch Daten an ChatGPT/DuckDuckGo. Alternativ: „Import from Google Search Console" nutzen.
- **Keine eigene Domain nötig:** Die github.io-Adresse funktioniert für die GSC völlig normal. Solltest du später `franksfinanzcheck.de` kaufen, richtest du dort einfach eine zweite Property ein (oder wechselst um).

---

## Kurz-Zusammenfassung

1. search.google.com/search-console → URL-Präfix → deine Blog-URL
2. Verifikation: HTML-Datei → **Dateinamen mir schicken**, ich lege sie an
3. Sitemap `sitemap.xml` einreichen
4. Startseite „Indexierung anfordern"
5. Fertig – Google findet deinen Blog! 🎉
