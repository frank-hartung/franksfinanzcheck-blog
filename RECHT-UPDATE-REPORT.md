# ⚖️ RECHT-UPDATE-REPORT – Rechtstexte-Abgleich August 2026

**Datum:** 30.08.2026 · **Referenz-Generator:** eRecht24 **Basis** (Datenschutz-Generator **Version 1.50 / 1.50.1**, Stand 17.02./01.04.2026) · **Zweitreferenz:** kostenloser Generator Dr. Schwenke (dr-schwenke.de) · **Rechtsstand:** 30.08.2026

> **Kurzfassung:** Beide Rechtstexte waren bereits auf DDG-/TDDDG-Niveau und in eRecht24-Struktur – kein Voll-Rewrite nötig. Der Abgleich gegen den aktuellen Generator-Stand ergab **3 echte Deltas**, alle übernommen: ① Drittlandtransfer USA jetzt auf **EU-US Data Privacy Framework (Art. 45 DSGVO)** gestützt (GitHub Pages + Cloudflare), ② **KI-Transparenzhinweis** (Art. 50 EU-KI-VO, seit 02.08.2026 anwendbar) ins Impressum, ③ Stand-Daten + Überarbeitungshistorie erneuert. Alles Weitere: geprüft und für aktuell befunden (Details unten). **Bonus eingebaut:** kostenloses Fristen-Erinnerungssystem mit Issue-Eskalation – siehe `FRISTEN-REPORT.md`.

---

## 1. Was geändert wurde (Deltas)

### 1.1 Datenschutzerklärung (`content/datenschutz/index.md`)

| # | Abschnitt | Vorher (Alt) | Nachher (Neu) | Grund / Quelle |
|---|---|---|---|---|
| 1 | § 2 Hosting (GitHub Pages) | USA-Transfer nur über „Auftragsverarbeitungsvereinbarung (Standardvertragsklauseln gemäß Art. 46 DSGVO)" | GitHub ist **DPF-zertifiziert** → Transfer gestützt auf **Angemessenheitsbeschluss v. 10.07.2023 (Art. 45 DSGVO)**, bestätigt durch EuG 03.09.2025 (T-553/23 „Latombe"); Status prüfbar auf dataprivacyframework.gov; **zusätzlich** AVV nach Art. 28 DSGVO | eRecht24-Generator weist seit 2023/2024 für US-Dienste das DPF aus (u. a. Cloudflare-Text); DPF rechtsgültig, Klage abgewiesen, Rechtsmittel C-703/25 P anhängig → Nachfrage via Fristen-Check |
| 2 | § 2 CDN (Cloudflare) | „Cloudflare bietet ein Datenverarbeitungsabkommen an …" | Cloudflare **DPF-zertifiziert** → USA-Transfer auf Art. 45 DSGVO (Angemessenheitsbeschluss) gestützt, Link zur Zertifizierungsliste | eRecht24-Muster für Cloudflare nennt DPF-Zertifizierung ausdrücklich als Zulässigkeitsvoraussetzung |
| 3 | § 15 Aktualität | „Stand: August 2026" | „Stand: **30. August 2026**" + Zeile „**Letzte Überarbeitung:** 30. August 2026 – …" | Nachvollziehbarkeit künftiger Abgleiche; der Fristen-Check prüft das Stand-Datum automatisch (max. 12 Monate) |

### 1.2 Impressum (`content/impressum/index.md`)

| # | Abschnitt | Vorher (Alt) | Nachher (Neu) | Grund / Quelle |
|---|---|---|---|---|
| 4 | **Neu:** „Hinweis zu KI-unterstützten Inhalten" | – (nicht vorhanden) | Transparente Ausweisung: Artikel/Grafiken/Cover entstehen **KI-gestützt**, werden vor Veröffentlichung **redaktionell geprüft**; **kein Chatbot** auf der Website (Art. 50 Abs. 1 KI-VO nicht einschlägig) | **Art. 50 EU-KI-VO seit 02.08.2026 anwendbar** (Transparenzpflichten); für redaktionell geprüfte Ratgebertexte besteht keine pauschale Einzeltext-Kennzeichnungspflicht, die freiwillige Gesamtausweisung ist Conservative-Best-Practice und Vertrauensvorschuss. Bewertung der maschinenlesbaren Kennzeichnung (Nachfrist für Bestandssysteme bis **02.12.2026**) läuft als Frist `ki-vo-kennzeichnung-bestand` |
| 5 | Stand-Fußnote | „Stand: August 2026" | „Stand: **30. August 2026**" | wie oben |

### 1.3 Über-Seite (`content/ueber/index.md`)

Geprüft, **keine Änderung nötig**: Werbekennzeichnung („Transparenz: Affiliate-Links"), Nichtberatungs-Disclaimer und Kontakt sind vollständig und aktuell.

---

## 2. Geprüft und unverändert übernommen (Generator-Stand 2026 = Status quo)

| Baustein | Befund |
|---|---|
| **Impressum § 5 DDG** (Anbieterkennzeichnung) | ✅ korrekt: Name, Anschrift, E-Mail; DDG-Referenzen statt TMG (seit 14.05.2024) – Telefonnummer seit DDG entbehrlich |
| **§ 18 Abs. 2 MStV** (Verantwortlicher) | ✅ vorhanden |
| **Haftung §§ 7–10 DDG** | ✅ auf DDG umgestellt (TMG-Privilegierungen sinngemäß übernommen) |
| **Urheberrecht, Haftung für Links** | ✅ Generator-Standard, aktuell |
| **§ 36 VSBG Universalschlichtungsstelle** | ✅ korrekt formuliert; **kein OS-Plattform-Hinweis enthalten** – Pflicht dazu ist seit **20.07.2025 entfallen** (EU-Plattform abgeschaltet, Weiterverwendung wäre irreführend). Veraltungs-Scan überwacht das künftig täglich |
| **Datenschutz: Verantwortliche Stelle, Betroffenenrechte (Art. 15–21, 77 DSGVO)** | ✅ vollständig inkl. Aufsichtsbehörde (LDA MV – korrekt für Standort) |
| **§ 25 TDDDG / Consent-Banner** | ✅ Opt-in-Logik, „Nur notwendige" gleichrangig (kein Cookie-Wall), Consent-Cookie `ff_cookie_consent` mit Zweck/Rechtsgrundlage (Art. 6 Abs. 1 lit. c i. V. m. § 25 Abs. 2 TDDDG)/Dauer/Inhalt dokumentiert, Widerruf über Footer-Link (Art. 7 Abs. 3 DSGVO) |
| **Affiliate-Abschnitt (CHECK24/Tarifcheck/Awin)** | ✅ Verantwortlichkeiten getrennt („nach dem Klick ist der Partner verantwortlich"), Partnerliste mit Links, § 5a UWG-/§ 18 MStV-gerechte Werbekennzeichnung im Impressum + auf Über-Seite |
| **Lokale Fonts (Inter, Playfair Display)** | ✅ kein Google-Fonts-Transfer – Generator-Anforderung („keine Verbindung zu fonts.googleapis.com") erfüllt und dokumentiert |
| **Umami (cookieless), Service Worker, Logfiles (7–14 Tage), Speicherdauern-Tabelle, SSL/TLS, Art. 22** | ✅ Generator-Niveau erreicht bzw. übertroffen (Dokumentationsdichte) |

---

## 3. Aktuell NICHT einschlägig – aber beobachtet (Fristen-System)

| Thema | Status für diesen Blog |
|---|---|
| **Widerrufsbutton-Pflicht** (EU-Richtlinie 2023/2673, seit **19.06.2026**) | Nicht einschlägig – gilt für Online-**Vertragsabschlüsse** eigener Leistungen; der Blog schließt selbst keine Verträge ab (Affiliate-Vertrag kommt beim Partner zustande). Re-Check über `rechtslage-screening` |
| **EmpCo-Richtlinie 2024/825: Garantie-/Gewährleistungs-Label** (ab **Sept. 2026**) | Nicht einschlägig – Handel mit Waren; kein eigener Verkauf. Re-Check über `rechtslage-screening` |
| **BFSG Barrierefreiheit** (seit 28.06.2025) | **Scope-Bewertung (dokumentiert):** Das BFSG adressiert u. a. „E-Commerce-Dienstleistungen" i. S. d. Art. 3 VRRL. FranksFinanzcheck bietet keine eigene Handels-/Vertragsdienstleistung an, sondern redaktionelle Inhalte + Werbung für Drittangebote (CHECK24/Tarifcheck). Nach herrschender Lesart besteht damit **keine unmittelbare BFSG-Pflicht**; die laufende accessibility-Arbeit (`scripts/a11y_audit.py`) dient als Goodwill-Nachweis. → Frist `bfsg-barrierefreiheit-bewertung` (31.10.2026) kann damit als erledigt markiert werden |
| **Digital-Omnibus-Paket (geplante DSGVO-Änderungen)** | In Verhandlung – keine Umsetzungspflichten vor Finalisierung. Beobachtet via `rechtslage-screening` (quartalsweise) |
| **KI-VO Hochrisiko-Pflichten** | Für Anhang-III-Systeme auf **02.12.2027** verschoben (VO (EU) 2026/1744); für diesen Blog ohnehin kein Hochrisiko-Einsatz. Es gelten nur die Transparenzpflichten (Art. 50) – siehe Delta #4 |
| **DPF-Stabilität (EuGH C-703/25 P)** | DPF derzeit gültig; Rechtsmittel anhängig. Quartalsweiser Zertifizierungs-Check als Frist `dpf-zertifizierung-pruefen`; bei Kippen: Rückfall auf AVV + SCC (Art. 46 DSGVO) – Anpassungsanleitung steht in der Frist-Checkliste |

---

## 4. Rechtsquellen (Stand 30.08.2026)

- eRecht24-Generator-Update 1.50/1.50.1 (17.02./01.04.2026): <https://www.e-recht24.de/news/datenschutz/13520-update-des-datenschutz-generators-auf-version-1-50.html>
- eRecht24 zum DDG (Impressum § 5 DDG, TDDDG-Umbenennung): <https://www.e-recht24.de/datenschutz/13328-digitale-dienste-gesetz-ddg.html>
- eRecht24-Cloudflare-Text (DPF-Zertifizierung als Voraussetzung): <https://www.e-recht24.de/dsg/12626-cloudflare.html>
- OS-Plattform abgeschaltet (20.07.2025), Hinweispflicht entfallen: <https://www.sor.de/blog/eu-streitschlichtung-aus-impressum-entfernen/>
- DPF-Status 2026 (EuG T-553/23, C-703/25 P, Zertifizierungsliste): <https://next-levels.de/wiki/eu-us-data-privacy-framework> · <https://www.dataprivacyframework.gov/>
- KI-VO Art. 50 ab 02.08.2026 (Texte öffentl. Interesse, Nachfrist 02.12.2026): <https://www.technovice.net/de/post/ki-kennzeichnungspflicht-eu-ai-act-2026> · <https://blog.academy.fraunhofer.de/blogbeitraege/transparenzpflicht/>
- Dr. Schwenke (Zweitreferenz-Generator, kostenlos): <https://www.dr-schwenke.de/>

---

## 5. Gegencheck-Anleitung: 5 Minuten im kostenlosen Generator (optional, empfohlen beim nächsten Halbjahres-Termin)

Die Texte hier sind eine **Eigenfassung auf Generator-Niveau** (Struktur + Rechtsstand des eRecht24-Basis-Generators 1.50, angereichert um die standortspezifischen Dienste GitHub Pages/Cloudflare/Umami/Consent-Banner). Es wurde **nichts 1:1 kopiert** – damit besteht auch keine eRecht24-Backlink-/Lizenzpflicht. Zum Gegenchecken (empfohlen beim Halbjahres-Termin, Frist `rechtstexte-halbjahrescheck`):

1. **eRecht24 Basis** (e-recht24.de → „Datenschutzerklärung kostenlos erstellen", Gratis-Konto): Profildaten = Frank Hartung, Karl-Marx-Str. 13, 19376 Ruhner Berge OT Marnitz, frankhartung@web.de; Dienste ankreuzen: externes Hosting (USA/DPF), CDN, **keine** Google Fonts, Cookie-Consent mit „technisch notwendige Cookies", Affiliate/Werbung, Statistik ohne Cookies.
2. **Dr. Schwenke** (dr-schwenke.de → kostenloser Datenschutz-Textgenerator): gleiche Angaben; dient als Zweitmeinung für Aufbau/Formulierungen.
3. Generierte Texte **nicht** blind übernehmen, sondern gegen diese Seiten diffen und **nur Deltas** einpflegen (die standortspezifischen Abschnitte – Fonts lokal, Service Worker, Umami, Consent-Cookie, CHECK24/Tarifcheck/Awin, Pinterest-Link – hat kein Generator und müssen bleiben).
4. Neue Deltas hier in Abschnitt 1 dokumentieren, Stand-Datum erneuern, deployen, Frist mit `erledigt=rechtstexte-halbjahrescheck` abschließen.

---

## 6. Das Erinnerungssystem (mit diesem Update eingebaut)

| Baustein | Datei | Funktion |
|---|---|---|
| Fristen-Kalender | `data/recht-fristen.yaml` | 6 Fristen: Rechtstexte-Halbjahrescheck, KI-VO-Kennzeichnung (02.12.2026), DPF-Check (quartalsweise), Affiliate-Partnerbedingungen (quartalsweise), Rechtslage-Screening (quartalsweise), BFSG-Bewertung (31.10.2026) |
| Prüfskript | `scripts/fristen_check.py` | Fristenbewertung (OK/Erinnerung/fällig/überfällig), Eskalations-Stufen 0/+14/+30 Tage, Veraltungs-Scan (TMG/TTDSG/OS-Plattform/Privacy-Shield-Reste), Stand-Alter-Prüfung, Report-Generator |
| Workflow | `.github/workflows/fristen-check.yml` | TÄGLICH 07:55 MESZ; Issues (`frist` → `frist-eskalation`), Commit von Report + State; manuelle Eingabe `erledigt=<frist-id>`. **Anbindung als Patch bereit** (`patches/fristen-check-2026-08-30-workflows.patch`, einmalig anwenden – Push durch Agent-Token ohne `workflows`-Scope blockiert); bis dahin: `python3 scripts/fristen_check.py` |
| Report | `FRISTEN-REPORT.md` | Aktueller Stand aller Fristen + Sofort-Prüfungen |
| Fehler-Alerting | `.github/workflows/alert-on-failure.yml` | „Fristen-Check (Recht)" in die zentrale Workflow-Überwachung aufgenommen |

*Erstellt am 30.08.2026 – Agentur-Update Rechtstexte + Compliance-Erinnerungssystem. Keine Rechtsberatung: Bei konkreten Abmahnungen oder Sonderfällen einen Fachanwalt konsultieren.*
