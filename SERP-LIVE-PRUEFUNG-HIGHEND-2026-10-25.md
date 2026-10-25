# SERP-Live-Prüfung – FranksFinanzcheck (Highend-Agentur-Level)

> **Stand:** 25.10.2026 · **Methode:** Live-Google-SERP-Erhebung (hl=de, gl=de, pws=0, num=10), manuell, zweikontrolliert  
> **Vertrag:** Kein direktes google.com-Scraping (Nutzungsvertrag / YMYL / Rechenzentrums-CAPTCHA). Erhebung über die öffentliche SERP-Darstellung.  
> **Artefakt:** `data/serp/live-pruefung-2026-10-25.json` (maschinenlesbar)  
> **Dauerhafte Wache:** `scripts/serp_live_wache.py` (schlüssellose Kette, Offline-Selbsttest)

---

## 1. Kurzfazit

**franksfinanzcheck.de ist in keiner der 9 generischen Schlüsselbegriff-Anfragen in den Google Top 10 sichtbar.** Die Domain ist ca. zehn Wochen alt, hat laut Authority-Radar 0 redaktionelle Links und 0 Mediennennungen, und die Konkurrenz in den SERPs sind etablierte Player mit Domain-Autorität (Verivox, Check24, Finanztip, Verbraucherzentrale, Stiftung Warentest, Energieversorger, Sparkassen/ING).

Das ist kein technisches Problem (Canonical, Sitemap, robots.txt, JSON-LD sind sauber gelöst), sondern ein **Sichtbarkeits- und Autoritätsproblem**. Die technische Basis ist überdurchschnittlich; es fehlt an dem, was Google bei neuen YMYL-Domains vorrangig belohnt: einzigartige, belegte, nützliche Inhalte plus externe Verweise.

**Urteil: gelb** – die Grundlage steht, die organische Reichweite muss systematisch aufgebaut werden.

---

## 2. Erhebung je Suchbegriff (Google, de/de, entpersonalisiert)

| # | Suchbegriff | Eigener Rang | Eigener Titel | Top-3-Domänen in der SERP |
|---|-------------|--------------|---------------|---------------------------|
| 1 | Fixkosten senken | – | – | ing.de (1), lexware.de (2), verivox.de (3) |
| 2 | Gaskosten senken | – | – | viessmann.de (1), test.de (2), vattenfall.de (3) |
| 3 | Stromanbieter wechseln | – | – | verivox.de (1), check24.de (2), lekker.de (3) |
| 4 | DSL Anbieter Vergleich | – | – | check24.de (1), finanztip.de (2), freenet-internet.de (3) |
| 5 | Kontogebühren vermeiden | – | – | check24.de (1), verbraucherzentrale.de (2), finanztip.de (3) |
| 6 | Notgroschen aufbauen | – | – | finanzfluss.de (1), consorsfinanz.de (2), sparkasse.de (3) |
| 7 | Kündigungsfristen Strom | – | – | keine eigenen Treffer erhoben |
| 8 | Haushaltsbudget Rechner | – | – | zinsen-berechnen.de (1), baufi24.de (2), verbraucherzentrale.de (3) |
| 9 | Mietwagen günstig buchen | – | – | billiger-mietwagen.de (1), check24.de (2), kayak.de (3) |
| 10 | Versicherungen kündigen | – | – | verbraucherzentrale.de (1), brief-wechsel.de (2), versicherungsriese.de (3) |

**Ergebnis:** 0 von 9 generischen Anfragen mit eigener Präsenz in den Top 10.

---

## 3. Marken-Abfrage „FranksFinanzcheck“

Google korrigiert die Anfrage auf „Frank Finanzcheck“ und schlägt **FINANZCHECK.de** vor. Die eigene Marke ist nicht als eindeutige Rang-1-Entität etabliert – Google assoziiert den Begriff primär mit dem Kreditvergleichsportal (Smava). Das ist ein echtes Marken-Problem: Nutzer, die explizit nach der Domain suchen, landen nicht automatisch bei ihr.

**Empfehlung:** Eigene Domain konsistent in Titel/Description halten, Brand-Signale ausbauen (Backlinks auf Startseite, Presse, Gastbeiträge, Social Profile als `sameAs` im Schema – bereits vorhanden).

---

## 4. Indexlage (site:franksfinanzcheck.de)

- **ca. 108 Ergebnisse** unter `site:franksfinanzcheck.de`
- Indexiert: Startseite, `/ueber`, `/impressum`, `/datenschutz`, `/posts`, `/tags`, Pillar-Seiten, einige Artikel
- **Totes Asset:** `https://franksfinanzcheck.de/tags/sparmethoden/` liefert **Live-404** (erhoben 25.10.2026) – ist aber im Google-Index
- Tag-Archive sind indexiert, liefern aber 404 → **Index-Müll**, der Crawl-Budget und Qualitätssignal verschlechtert

**Empfehlung:** Tote Tag-Archive aus dem Index nehmen (noindex oder 404 beheben), `/tags/sparmethoden/` reparieren oder entfernen.

---

## 5. Google Search Console (Kontext)

- Zeitraum: 25.07.2026 – 22.10.2026 (33 Tage)
- **Klicks: 0**, Impressionen: 51 über 92 Beiträge (60 live)
- Einzelne Beiträge stehen auf Position 2–5, aber bei fast keiner Nachfrage
- Keine Conversions messbar (Umami entfernt, cookielose Messung offen)

---

## 6. Konkurrenz in den eigenen SERPs

Die Top-10 der eigenen Schlüsselbegriffe werden besetzt von:

| Spieler | Rolle | Präsenz |
|---------|-------|---------|
| verivox.de | Vergleichsportal | Fixkosten, Strom, DSL, Konto |
| check24.de / check24.net | Vergleichsportal | Fixkosten, Strom, DSL, Konto, Mietwagen |
| finanztip.de | Verbraucher-Ratgeber | DSL, Konto, Notgroschen |
| verbraucherzentrale.de | Verbraucherschutz | Konto, Versicherungen, Haushalt |
| test.de / Stiftung Warentest | Prüfinstitut | Gaskosten |
| viessmann.de / vattenfall.de / eprimo.de | Energieversorger | Gaskosten |
| finanzfluss.de / consorsfinanz.de | Finanz-Content | Notgroschen |
| sparkasse.de / ing.de / mlp.de | Banken | Notgroschen |
| kayak.de / idealo.de / adac.de | Reise-Vergleich | Mietwagen |

Das sind alles Domains mit hoher Domain-Autorität. FranksFinanzcheck konkurriert derzeit nicht auf Augenhöhe – die Lücke ist Autorität, nicht Technik.

---

## 7. Maßnahmenplan (abgeleitet aus der Live-Erhebung)

| # | Maßnahme | Aufwand | Wirkung | Status |
|---|----------|---------|---------|--------|
| 1 | Titel/Description aller Live-Artikel auf M1/M2 prüfen (≤60 Zeichen Titel, 100–160 Zeichen Description, kein hartes Ellipsis-Ende) | klein | mittel | ✅ erledigt (12 Descriptions repariert, metadaten_wache grün) |
| 2 | Marken-Präsenz stärken: Domain konsistent in Snippet, Backlinks auf Startseite (Authority-Radar), Presse/Gastbeiträge | groß | sehr hoch | 🔧 Entity-Fundament umgesetzt 25.10.2026 (`MARKEN-ENTITY-HIGHEND-2026-10-25.md`): kanonische Entity-Definition + Abgrenzung zu FINANZCHECK.de auf Startseite/Schema//ueber//Impressum/llms.txt, Person-sameAs repariert, rel=me im Footer, Startseiten-Kampagne im Backlink-CRM, Dauerwache `entity_marken_gate.py`. Offen bleiben Franks Handgriffe: Publisher-Center-Profil, LinkedIn/Xing-Profile, Outreach (Runbook `docs/ANLEITUNG-MARKEN-ENTITY.md`) |
| 3 | Tote Tag-Archive aus dem Index nehmen (`/tags/sparmethoden/` → 404) | klein | mittel | offen |
| 4 | Interne Verlinkung: jeder Beitrag verlinkt Rechner + Pillar (bereits 60/60 Live) | mittel | mittel | ✅ umgesetzt |
| 5 | Eigene Bilder/Rechenbeispiele in Top-20-Beiträgen (Bildersuche, Nutzerbindung) | mittel–groß | hoch | 8/20 umgesetzt |
| 6 | Konto-/Kreditkarten-Beiträge fachlich prüfen lassen (YMYL, nur 9/92 mit Prüfer) | mittel | hoch | offen (kein benannter Prüfer) |
| 7 | SERP-Live-Wache `scripts/serp_live_wache.py` regelmäßig laufen lassen (Snippet- & Marken-Überwachung) | klein | mittel | ✅ gebaut, Selbsttest grün |

---

## 8. SERP-Live-Wache (dauerhafte Überwachung)

`scripts/serp_live_wache.py` prüft über die schlüssellose Suchradar-Kette (searxng → DuckDuckGo → Mojeek → Wikipedia, **kein direktes google.com-Scraping**):

1. Erscheint `franksfinanzcheck.de` bei den eigenen Schlüsselbegriffen?
2. Stimmen Titel und Description der eigenen Treffer mit den Frontmatter-Werten überein? (Snippet-Kontrolle)
3. Steht die Marke „FranksFinanzcheck“ bei der Marken-Abfrage auf Rang 1?

- Offline-Selbsttest: ✅ bestanden (6 Prüfblöcke)
- Vertragskonform: kein direktes google.com-Scraping
- Ausgabe: `data/serp/live-pruefung-*.json` + Markdown-Bericht
- Exit: 0 = grün, 1 = Befunde

> Hinweis: Die schlüssellose Kette liefert in dieser Sandbox-Umgebung derzeit nicht zuverlässig (SearXNG-Instanzen tot, DuckDuckGo blockiert – exakt das, was das Suchradar am 25.10.2026 ebenfalls festgestellt hat). Die obige Erhebung basiert deshalb auf der direkten, manuellen Google-SERP-Erhebung. Der Betrieb der Wache über die Kette ist für den Produktionslauf vorgesehen.

---

## 9. Einordnung

Die technische SEO-Basis ist überdurchschnittlich gut (Note 8/10 im SEO-Audit 18.10.2026). Das Problem liegt bei **Autorität (Note 2/10: 0 redaktionelle Links, 0 Mediennennungen)** und **reale Sichtbarkeit (Note 1/10: 0 Klicks, 51 Impressionen)**. Mehr Technik bringt wenig; die Hebel sind Inhalt, Vertrauen (E-E-A-T/YMYL) und externe Verweise.

Kein Treffer aus diesem Bericht wird ungeprüft in einen Artikel übernommen. Das Radar misst; die Entscheidung trifft Frank.
