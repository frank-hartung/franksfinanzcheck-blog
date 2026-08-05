# 📋 Checkliste: Datenschutzerklärung per Generator erstellen

**Ziel:** Maximale Rechtssicherheit für den Blog „FranksFinanzcheck" (Affiliate-Links + Consent-Banner)
**Erstellt:** August 2026 | Für: Frank Hartung

---

## 1. Anbieter wählen (Vergleich)

| Kriterium | **IT-Recht Kanzlei** (empfohlen) | **eRecht24** |
|---|---|---|
| Preis | **ab 5,90 €/Monat** | ab 15 €/Monat (jährlich) / Free-Plan mit Quellenangabe |
| Automatische Updates bei Gesetzesänderungen | ✅ Ja | ✅ Ja |
| Spezialisiert auf Affiliate/Online-Marketing | ✅ Ja | ✅ Ja |
| Kündbar | Monatlich | Monatlich/jährlich |
| URL | https://www.it-recht-kanzlei.de/Datenschutzgenerator.html | https://www.e-recht24.de |

**Empfehlung:** IT-Recht Kanzlei – günstiger, monatlich kündbar, automatische Updates. Wenn du langfristig maximalen Service willst (Abmahnschutz, Rechtsberatung), nimm eRecht24 Business.

---

## 2. Diese Angaben brauchst du beim Generator (Antwortbogen)

### Persönliche Daten (Verantwortlicher)
- **Name:** Frank Hartung
- **Anschrift:** Karl-Marx-Str. 13, 19376 Ruhner Berge OT Marnitz, Deutschland
- **E-Mail:** frankhartung@web.de
- **Telefon:** (keine Angabe – optional)
- **Rechtsform:** Privatperson / Einzelperson (kein Gewerbe angemeldet → prüfen, ob du als „Privatperson" oder „Freiberufler" antwortest)

### Website
- **Domain:** franksfinanzcheck.de (geplant – kann im Generator später geändert werden)
- **Art:** Blog / Ratgeber-Website (Affiliate-Marketing)

### Tools & Dienste (wichtig – nur das ankreuzen, was wirklich genutzt wird!)

| Thema | Im Generator ankreuzen |
|---|---|
| **Affiliate-Partnerprogramm** | ✅ **Ja** – CHECK24-Partnerprogramm (via Awin) + Tarifcheck (Versicherungen) |
| **Consent-Management-Banner** | ✅ **Ja** – „Eigenes Consent-Tool" bzw. „Cookie-Consent-Tool" auswählen |
| **Hosting** | ✅ Ja – externer Host (GitHub Pages / Netlify / Cloudflare – nach Deployment konkret angeben) |
| Server-Logfiles | ✅ Ja (wird meist automatisch ergänzt) |
| Google Analytics / Statistik | ❌ **Nein** (noch nicht im Einsatz) |
| Google Ads / Facebook Pixel | ❌ **Nein** |
| Newsletter | ❌ **Nein** (kein Newsletter vorhanden) |
| Kommentarfunktion | ❌ **Nein** (Hugo hat keine) |
| Kontaktformular | ❌ **Nein** (nur E-Mail-Kontakt im Impressum) |
| Pinterest / Soziale Medien | ✅ **Ja** – Verlinkung auf externes Pinterest-Profil (als „Social Media Verlinkung" angeben) |
| SSL-Verschlüsselung | ✅ **Ja** (automatisch enthalten) |

### Affiliate-Details (für den Generator-Abschnitt)
- Partnerprogramm-Anbieter: **CHECK24 Vergleichsportal GmbH** (via **Awin AG**) + **Tarifcheck** (Versicherungen)
- Tracking-Mechanismus: **Tracking-Cookies / URL-Kennung** beim Klick auf Affiliate-Links
- Eigene Datenverarbeitung durch dich: **Keine** – nur statistische Abschluss-Daten ohne Personenbezug
- Verantwortung nach Klick: liegt beim Kooperationspartner (wird vom Generator automatisch formuliert)

### Consent-Banner-Details
- Dein Banner: eigener, selbstgebauter Consent-Banner („Alle akzeptieren" / „Nur notwendige")
- Cookie-Name: `ff_cookie_consent` (technisch notwendig, 12 Monate)
- Keine Cookie-Wall (Seite ohne Einwilligung nutzbar)

---

## 3. Nach der Generierung

1. **Fertigen Text kopieren** (der Generator liefert HTML/Text – am besten als Text exportieren)
2. **Mir schicken** (hier im Chat anhängen oder einfügen) – **ich baue ihn dann in den Blog ein:**
   - Konvertierung in Markdown (Format des Blogs)
   - Einbau in `content/datenschutz/index.md`
   - Verlinkung im Footer/Menü prüfen
   - Build + Commit + Vorschau
3. **Nach dem Deployment:** Hoster-Namen in § 2 (Hosting) ergänzen – Generator-Update abwarten oder mich informieren

---

## 4. Wichtig zu wissen

- Der Generator liefert die **rechtlich geprüfte Basis** – du musst die Angaben (Tools) ehrlich und vollständig machen, sonst stimmt das Ergebnis nicht
- **Automatische Updates** (bei beiden Diensten) halten die Erklärung bei Gesetzesänderungen aktuell – du musst sie nur ab und zu neu exportieren
- Auch mit Generator gilt: Eine **100%-Garantie** gibt es im Datenschutzrecht nie – aber mit IT-Recht Kanzlei/eRecht24 bist du auf dem Stand, den auch professionelle Affiliate-Blogs nutzen
- Der **eRecht24-Free-Plan** ist eine Option zum Testen (mit Quellenangabe) – für den dauerhaften Einsatz ist der bezahlte Tarif sauberer
