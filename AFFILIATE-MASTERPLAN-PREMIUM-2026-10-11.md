# Affiliate-Masterplan „bester Ratgeber-Affiliate-Blog Deutschlands“ – Ist-Analyse & Fahrplan

**Stand:** 11.10.2026 · **Branch:** `arena/3bd1f817-franksfinanzcheck-blog` · **Basis:** `main` @ `ed4dbc1`

**Ziel laut Auftrag:** Ein Affiliate-Ratgeber, der in Deutschland zur ersten Adresse für
Fixkosten-Entscheidungen wird – auf dem Niveau einer professionellen Redaktions- und
Vermarktungsagentur.

---

## 1. Kurzfassung

1. **Der Blog ist technisch und redaktionell solide, aber er ist „blind“.** Es gibt keine
   belastbare Zahl zu Klicks, Provisionen oder Umsatz pro Artikel. Ohne diese Zahl lässt sich
   „bester Affiliate-Blog“ nicht steuern und nicht belegen.
2. **Die Qualitätsgates halten.** Lesbarkeit, H1, Affiliate-Integrität, Werbe-Offenlegung und
   Layout sind im Live-Bestand grün (siehe Abschnitt 3).
3. **Ein wichtiger Fund: Zwei Artikel, die als „repariert und live“ gemeldet wurden, existieren auf
   `main` nicht.** Sie liegen als *unveröffentlichte Entwürfe* auf einem anderen Arbeits-Branch. Ihr
   Inhalt enthält ungeprüfte Zahlen. Ich habe sie **nicht** live geschaltet (Abschnitt 4).
4. **Das Konzentrationsrisiko ist hoch.** Fast alle Provisionsrouten laufen über CHECK24
   (11 Routen), Tarifcheck (7) und C24 Bank (2). Awin ist deaktiviert, obwohl README und
   PRODUCT.md es als Partner nennen.
5. **Die größten Hebel liegen in dieser Reihenfolge:** Messung → Vertrauen durch belegte Zahlen
   und sichtbare Expertise → Publikationstempo ohne Qualitätsverlust → Newsletter und Wiederkehr.
   Details und Entscheidungen für dich in Abschnitt 6 und 7.

---

## 2. Was geprüft wurde

Alle Angaben stammen aus Befehlen, die in dieser Sitzung gelaufen sind. Build: Hugo 0.164.0
Extended, `hugo --minify` ohne Fehler.

| Prüfung | Ergebnis |
|---|---|
| Hugo-Build (Extended 0.164) | ✅ fehlerfrei |
| `npm run h1:check` | ✅ jede Seite hat genau eine H1 |
| `readability_check.py --gate-bestand` | ✅ 42 Live-Artikel, Ø Flesch 67,7, keiner unter Boden 55 |
| `affiliate_integrity_gate.py` | ✅ alle Affiliate-Links intakt (laut Report-Lauf vom 11.10.) |
| `test:offenlegung` (Werbe-Offenlegung) | ✅ Selbsttest bestanden |
| `layout_audit.py` (DOM-Budget, Hreflang, Chunker) | ✅ im Budget |
| `provisionen:check` / `mess:status` | ❌ **keine Provisionsdaten** (`data/provisionen/provisionen.csv` fehlt) |
| Social-Plan `data/social/schedule.yaml` | ✅ alle 178 geplanten Posts zeigen auf existierende Artikel |

Nicht prüfbar aus der Sandbox: Live-Seite, Google Search Console, CHECK24-Partner-Dashboard,
Core Web Vitals im Feld, Rankings. Dafür fehlen Zugänge (siehe Abschnitt 7).

---

## 3. Ausgangslage in Zahlen (verifiziert)

| Kennzahl | Wert | Bewertung |
|---|---|---|
| Live-Artikel | 42 | ausbaufähig für „Marktführer“ |
| Entwürfe (`draft: true`) | 33 | Publikationsstau, siehe 4.3 |
| Median-Länge Live-Artikel | 1.865 Wörter (min. 1.459) | solide Tiefe |
| Ø Flesch (Live) | 67,7 | gut; Boden 55 eingehalten |
| Live-Artikel mit Description | 42 / 42 | ✅ |
| Live-Artikel mit `quellen`-Feld | 39 / 42 | 3 Artikel ohne Quellenfeld, trotz Zahlen im Text |
| Live-Artikel mit /go/-Link | 42 / 42 (Median 3) | ✅ |
| Live-Artikel mit `ai_generated: true` | 15 | Kennzeichnung vorhanden |
| Live-Artikel mit offener Redaktionsprüfung (`ausstehend`) | 6 | menschliche Freigabe fehlt dort |
| Pillar-Verteilung live | Frugalismus 12 · Internet-DSL 11 · Strom/Gas 11 · Konto 4 · Mietwagen 4 | Mietwagen/Konto dünn |
| Provisions-Datenlage | **keine** (CSV fehlt, Umami per Datenschutz-Entscheidung aus, Awin aus) | **kritisch** |
| Newsletter | noch kein echter Listenversand protokolliert, Warteschlange 5 Artikel, ältester 59 Tage | **kritisch** |
| Social | 1 von 10 Kanälen live (Mastodon); Pinterest-Kanal laut Issue #448 geparkt | schwach |
| Partner-Routen (`data/affiliate_ziele.yaml`) | 20: CHECK24 11 · Tarifcheck 7 · C24 Bank 2 | Konzentration |

---

## 4. Befunde nach Priorität

### 4.1 P1 – Messung fehlt (Umsatz ist eine Blackbox)

- Die Provisionsdatei fehlt. Der Import-Pfad existiert (`npm run mess:vorlage`), aber niemand hat
  bisher Daten eingespielt.
- Klick-Messung ist abgeschaltet: `data/monetization.yaml` setzt `umami_api_import_enabled: false`,
  und die Umami-`websiteId` in `hugo.toml` ist leer, aus Datenschutzgründen. Das ist eine bewusste
  Marken-Entscheidung und wird hier **nicht** geändert.
- Die Ampel „Affiliate & Umsatz: 🟢“ im Cockpit ist deshalb irreführend. Grün bedeutet nur „keine
  Fehler“, nicht „Umsatz vorhanden“.

**Lösungsweg ohne Tracking-Cookies:** Die /go/-Weiterleitungen laufen bereits über eigene Seiten. Sie
können Klicks je Artikel und Route serverseitig oder über Cloudflare-Logs zählen, ohne Cookies und
ohne Drittanbieter. Das wäre mit der Datenschutz-Linie vereinbar und sollte mit dir abgestimmt werden.

### 4.2 P1 – Vertrauen und Belegbarkeit

**Fund: die „verlorenen“ Artikel vom 05.10.2026.**

- `2026-10-05-oekostrom-anbieter-wechseln-clever-sparen-und-gruen-bleiben`
- `2026-10-05-budget-app-2026-so-beherrschst-du-deine-ausgaben-ohne-auf`

Auf `main` sind sie nicht mehr vorhanden. Die Historie zeigt: Commit `c029574b` (05.10., 10:46 UTC)
hat sie als `draft: true` auf `main` gebracht, `c56382b2` (05.10., 17:35 UTC, „content: unabhängige
Redaktionsreserve auffüllen“) hat sie wieder entfernt. Sie waren auf `main` also nie live
(`draft: false`). Der Live-Policy-Befund „HTTP 404“ passt dazu. Die Dateien existieren nur noch auf dem
Branch `arena/01a10c61-franksfinanzcheck-blog`. Dort sind sie `draft: true` mit dem Vermerk
*„Erstrecherche – noch nie faktengeprüft – keine Veröffentlichung ohne aktuellen Beleg“*.
Im Ökostrom-Text stehen unbelegte Zahlen wie „spart im Schnitt 7 Prozent“, „100 bis 300 € im
Jahr“ und „5 bis 10 Cent je kWh“. Ein Live-Schalten hätte Falschangaben in einem YMYL-Thema
veröffentlicht. Die Gates haben das richtig verhindert.

**Konsequenz:**

- Der Report `LESBARKEIT-LIVE-KONSISTENZ-PREMIUM-2026-10-05.md` meldet diese Artikel als
  „repariert, live“. Das stimmt nicht. Ich habe am Report einen Korrekturvermerk ergänzt.
- Die Social-Posts zu den beiden Artikeln stehen korrekt auf `blocked`.
- Empfehlung: Die Entwürfe nur dann neu aufsetzen, wenn Quellen und Zahlen aus dem Faktenfrische-
  Dossier stammen (siehe Abschnitt 6, Phase 1).

**Weitere Belegbarkeit:** 3 Live-Artikel enthalten Euro-Beträge oder Prozentangaben, haben aber
kein `quellen`-Feld. 6 Live-Artikel stehen auf `redaktionelle_pruefung.status: ausstehend`.

**Die „Faktencheck“-Felder sind nur Datumsstempel.** Auf allen 42 Live-Artikeln steht ein
`faktencheck: <Datum>`. Das ist keine Quelle und kein Beleg, und es sollte nicht als Vertrauens-
signal nach außen wirken.

### 4.3 P2 – Publikationstempo und Stau

- 42 live, 33 Entwürfe. Davon liegen 9 unter der Publish-Schwelle 60 (Flesch 38–58).
- Der Cockpit-Stand vom 10.10. meldet „Letzter Publikationstag: 2 Artikel“, aber danach keinen
  weiteren. Die Redaktionskette hat also Lücken.
- Die Zahl „Lesbarkeit 🔴“ im Cockpit ist veraltet. Der Live-Bestand ist grün, nur die Entwürfe
  sind es nicht.

### 4.4 P2 – Konzentrationsrisiko und widersprüchliche Angaben

- **Provisionen hängen fast nur an CHECK24.** 11 von 20 Routen, plus 7 Tarifcheck und 2 C24 Bank.
- **Widerspruch:** `PRODUCT.md` nennt „CHECK24, Awin“. `data/monetization.yaml` sagt „Awin bewusst
  deaktiviert“. `README.md` nennt CHECK24 und Tarifcheck. Das muss vereinheitlicht werden,
  sonst wirkt der Auftritt bei Partnern und Lesern inkonsistent.
- Bei Tarifcheck sind nur Versicherungsrouten aktiv. Mietwagen, Kreditkarte und Tagesgeld sind
  thematisch wichtig, haben aber keine eigene, dokumentierte Partnerbasis.

### 4.5 P2 – Newsletter und Wiederkehr

- Kein echter Listenversand protokolliert. Nur Tests und Bestätigungen.
- Das ist für einen Ratgeber mit Wiederkehr (Fixkosten-Kalender, Fristen) der größte ungenutzte
  Kanal.

### 4.6 P2 – Distribution

- Social: 1 von 10 Kanälen live. Pinterest ist laut Issue #448 durch eine Domain-Sperre geparkt, und
  der Token ist abgelehnt (Re-Auth nötig, siehe `COCKPIT.md`).
- Autorität: Der Authority-Radar meldet 0 redaktionelle Links, 0 Medienerwähnungen, 0 Interviews.
  Das ist ehrlich ausgewiesen und sollte der Ausgangspunkt für Outreach sein, nicht eine
  Behauptung.

### 4.7 P3 – Berichte und Selbstbild

Die Berichte im Root sind umfangreich, teils widersprüchlich und enthalten Aussagen wie „Premium-
Niveau“ oder „dauerhaft behoben“, die nicht überall belegt sind. Für ein Vertrauensprodukt
wirkt das nach außen nicht gut. Vorschlag: Berichte kürzen, ein Dokument pro Thema führen und
Behauptungen nur mit Messwert stehen lassen.

---

## 5. Was ich bewusst nicht getan habe

- **Keine Live-Schaltung der zwei Entwürfe.** Unbelegte Zahlen in YMYL-Inhalten werden nicht
  veröffentlicht.
- **Keine erfundenen Kennzahlen, Testimonials oder Auszeichnungen** in Texten oder Metadaten.
- **Keine Aktivierung von Umami oder Awin** ohne deine Freigabe. Das sind Datenschutz- bzw.
  Geschäftsentscheidungen.
- **Keine Layout-Änderungen an der Basis.** Nach `CLAUDE.md` gehören Umbauten in eine Variante
  (`assets/css/varianten/`) mit Messung und Freigabe.
- **Keine Änderung am Publish-Gate oder an Governance-Schwellen.** Die Gates haben richtig reagiert.

---

## 6. Fahrplan

### Phase 0 – diese Woche (Entscheidungen durch Frank)

1. **Provisionsdaten einspielen:** CHECK24-Partner-Dashboard exportieren, als
   `data/provisionen/provisionen.csv` (Vorlage: `data/provisionen/provisionen-vorlage.csv`) ablegen.
   Dann lässt sich Umsatz je Route und Monat sehen.
2. **Partnerstrategie festlegen:** Awin aktivieren oder den Eintrag in README/PRODUCT.md streichen.
   Ziel: eine Wahrheit im Repo.
3. **Die zwei Entwürfe entscheiden:** neu recherchieren und belegen oder endgültig verwerfen.
4. **Newsletter-Entscheidung:** Startet der Listenversand, und mit welchem Versanddienst?

### Phase 1 – 2 bis 4 Wochen (Vertrauen und Messung)

5. **Belegpflicht für Zahlen:** Jeder Artikel mit Euro- oder Prozentangaben braucht ein `quellen`-
   Feld mit geprüfter Quelle. Das Gate sollte bei fehlender Quelle blockieren. Die 3 betroffenen
   Live-Artikel werden zuerst nachgezogen.
6. **Redaktionsprüfung abschließen:** die 6 Artikel mit `ausstehend` durch einen Menschen freigeben.
7. **Klick-Messung ohne Cookies:** Entscheidung mit dir über serverseitige Zählung der /go/-Klicks.
8. **Die 9 Entwürfe unter Schwelle 60:** entweder überarbeiten oder endgültig aussortieren. Kein
   Durchwinken.
9. **Partner-Diversifizierung prüfen:** Für Mietwagen, Kreditkarte und Tagesgeld eine
   dokumentierte Partnerbasis suchen. Vor jeder Aufnahme eines Partners gilt die Ehrlichkeitsregel
   aus README und PRODUCT.md.

### Phase 2 – 1 bis 3 Monate (Autorität und Wachstum)

10. **Sichtbare Expertise:** Autorenseite mit Qualifikation und echten Praxisbelegen, zum Beispiel
    eigene Tarifwechsel mit Datum, Anbieter und Ergebnis. Nur, was Frank tatsächlich belegen kann.
11. **Eigene Datenstücke:** Der Authority-Radar listet bereits einen Fixkosten-Index und einen
    Kündigungsfristen-Kalender. Diese sollten live gehen, mit Methodik, Rohdaten und Quellen.
12. **Outreach:** Verbraucherportale, Lokalmedien, Fachblogs. Menschlich geführt, nicht automatisiert.
13. **Konkurrenz-Monitoring:** Finanztip, Verivox, Verbraucherzentrale und CHECK24-Ratgeber gezielt
    nach Keywords vergleichen. Die Analysen dazu liegen im Repo, sind aber nicht regelmäßig aktualisiert.

---

## 7. KPIs (Ziel, nicht Behauptung)

Aktuell **nicht messbar**, deshalb werden keine Ist-Werte genannt.

| KPI | Zielbild | Datenquelle |
|---|---|---|
| Provision je 1.000 Besuche (RPM) | Monat für Monat steigend | CHECK24-Export + Besuchszahlen |
| Klick-Rate der CTA-Boxen | messbar je Artikel | /go/-Zählung (Phase 1) |
| Anteil Artikel mit belegter Quelle | 100 % der Zahlen-Artikel | Repo-Gate |
| Live-Artikel mit abgeschlossener Redaktionsprüfung | 100 % | Frontmatter |
| Rankings für Kernbegriffe (Strom, Gas, DSL, Tagesgeld, Budget) | Top 3 je Begriff | Search Console |
| Newsletter-Abonnenten und Öffnungsrate | regelmäßiger Versand | Versanddienst |
| Redaktionelle Erwähnungen und Links | belegt im Evidenzregister | Authority-Radar |

„Bester Affiliate-Blog in Deutschland“ lässt sich nicht einseitig erklären. Er zeigt sich an Rang,
Umsatz und Vertrauen im Vergleich zu den Wettbewerbern. Dieser Vergleich sollte Quartal für
Quartal mit denselben Kennzahlen wiederholt werden.

---

## 8. Was ich von dir brauche

1. **Zugang oder Export:** CHECK24-Partner-Dashboard (Klicks und Provisionen) und Google Search
   Console. Ohne diese Daten bleibt die Strategie eine Hypothese.
2. **Entscheidung zu Awin** (aktivieren oder streichen) und zur Klick-Messung (Datenschutz-Linie).
3. **Entscheidung zu den zwei Entwürfen** (Abschnitt 4.2).
4. **Newsletter:** Versanddienst und Start-Termin.
5. **Eigene Expertise belegen:** Welche Praxiserfahrungen (Tarifwechsel, Kündigungen, Budgets) lassen
   sich mit Datum und Ergebnis dokumentieren? Nur diese dürfen als Erfahrung im Text stehen.

---

## 9. Hinweis zur Nachvollziehbarkeit

Dieser Bericht fasst Befunde aus der Repo-Sicht zusammen, nicht aus der Live-Sicht. Für die
Live-Seite, Rankings und Umsatz fehlt der Zugriff. Alle genannten Zahlen stammen aus den oben
aufgeführten Befehlen und Dateien. Bei Widersprüchen zu älteren Berichten gilt der Stand dieses
Dokuments.
