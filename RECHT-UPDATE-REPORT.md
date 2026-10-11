# Recht-Update-Report

**Zweck:** Abgleich-Historie der Rechtstexte und rechtlichen Einordnungen des Blogs
(FranksFinanzcheck). Jeder Eintrag ist datiert, nennt die zugehörige Frist-ID aus
`data/recht-fristen.yaml` und bleibt auch nach Erledigung stehen. Neue Einträge
stehen oben.

**Hinweis:** Dies ist eine dokumentierte Selbsteinschätzung des Betreibers, keine
Rechtsberatung. Bei Zweifeln oder einer Änderung der Geschäftsmodelle wird eine
fachanwaltliche Prüfung empfohlen (siehe Abschnitt „Nächste Schritte“).

---

## Eintrag 2026-10-11 · Tarifcheck-Anbieterkennzeichnung im Impressum

| | |
|---|---|
| **Frist-ID** | keine (Umsetzung einer Programm-Vorgabe, kein Fristen-Eintrag) |
| **Kategorie** | Anbieterkennzeichnung / Datenschutz |
| **Ergebnis** | iframe des Tarifcheck-Partnerprogramms im Impressum, Datenschutzhinweis ergänzt |

Das Partnerprogramm verlangt die Einbindung von
`a.partner-versicherung.de/filestore/ad/1166/` mit der Partner-ID 47086.
Das Snippet allein wäre 150 px hoch und mit `scrolling="no"` abgeschnitten.
Es liegt deshalb in `layouts/shortcodes/partner_impressum.html` (nicht im
Markdown, damit der Affiliate-Shield die URL nicht auf eine `/go/`-Route
umbiegt), mit Titel, ausreichender Höhe, Fallback-Link und Hinweis auf den
Datenabruf.

Die Datenschutzerklärung nennt den Abruf beim Seitenaufruf, die Rechtsgrundlage
Art. 6 Abs. 1 lit. f DSGVO und die offene Prüfung zu Cookies und § 25 TDDDG.
Eine Einwilligungs-Wand vor dem Dokument wurde nicht gesetzt: die Kennzeichnung
soll im Impressum sichtbar sein. Ob das Dokument Cookies setzt, ist an der
Live-Antwort noch nicht geprüft.

Dies ist eine dokumentierte Umsetzung, keine Rechtsberatung.

---

## Eintrag 2026-10-10 · BFSG-Scope-Bewertung

| | |
|---|---|
| **Frist-ID** | `bfsg-barrierefreiheit-bewertung` (Issue #689) |
| **Kategorie** | Barrierefreiheit |
| **Gewicht** | Empfehlung (einmalig) |
| **Fällig am** | 31.10.2026 |
| **Ergebnis** | Kein BFSG-Scope. Die Bewertung stützt sich auf zwei unabhängige Gründe. |

### Kurz-Bewertung

Das Barrierefreiheitsstärkungsgesetz (BFSG, in Kraft seit 28.06.2025) erfasst
Dienstleistungen im elektronischen Geschäftsverkehr, also digitale Dienste, die
auf individuelle Anfrage eines Verbrauchers im Hinblick auf den Abschluss eines
Verbrauchervertrags erbracht werden. FranksFinanzcheck schließt selbst keine
Verbraucherverträge ab. Die Werkzeuge rechnen im Browser, die Artikel informieren,
und die Partnerlinks führen zu Verträgen, die Dritte (CHECK24, Tarifcheck) mit den
Lesern schließen. Selbst wenn ein Teil davon als Dienstleistung im Sinne des BFSG
gälte, greift für Kleinstunternehmen die Ausnahme des § 3 Abs. 3 Satz 1 BFSG für
Dienstleistungen, sofern die Schwellen (weniger als zehn Beschäftigte, Jahresumsatz
oder Bilanzsumme jeweils höchstens 2 Mio. €) erfüllt sind. Diese Angaben sind vom
Betreiber noch zu bestätigen (siehe unten). Der Blog verkauft keine Produkte, auf
die die Ausnahme nicht anwendbar wäre.

### Prüfrahmen

- **Rechtsgrundlage:** BFSG (Fassung ab 28.06.2025), insbesondere
  - § 1 Abs. 3 Nr. 5: Dienstleistungen im elektronischen Geschäftsverkehr,
  - § 2 Nr. 26: Definition (digitale Dienste über Webseiten oder Apps, elektronisch
    und auf individuelle Anfrage eines Verbrauchers im Hinblick auf den Abschluss
    eines Verbrauchervertrags),
  - § 3 Abs. 3 Satz 1: Ausnahme für Kleinstunternehmen, die Dienstleistungen
    anbieten oder erbringen (gilt nicht für Produkte),
  - § 2 Nr. 17: Definition Kleinstunternehmen (weniger als zehn Personen und
    Jahresumsatz oder Jahresbilanzsumme jeweils höchstens 2 Mio. €).
- **Quellenstand:** Abgleich über Fachkommentierungen (u. a. IHK München, Stand
  2026; sitebrunch-Überblick). Vor einer Veröffentlichung ist der amtliche
  Gesetzestext zu prüfen. Die Paragrafen sind in dieser Fassung aus der
  Sekundärliteratur übernommen.

### Prüfung der Angebotsbestandteile

| Bestandteil | Vertragsabschluss durch den Betreiber? | Einordnung |
|---|---|---|
| Ratgeber-Artikel (`content/posts`, Pillar-Seiten) | nein | Kein BFSG-Scope |
| Werkzeuge (Rechner, Kündigungsfristen-Kalender, Tarifwechsel-Entscheidungsbaum, Budget) | nein, Berechnung im Browser | Kein BFSG-Scope |
| Fixkosten-Cockpit | nein, Speicherung lokal im Browser | Kein BFSG-Scope |
| Newsletter (kostenlose Anmeldung) | nein, kein Entgelt | Kein BFSG-Scope; Restrisiko gering |
| Affiliate-Links zu CHECK24 und Tarifcheck | nein, der Vertrag kommt bei Dritten zustande | Grauzone bei der Vermittlung; hier trägt die Kleinstunternehmen-Ausnahme |
| Verkauf von Produkten (Shop, E-Books, Merchandise) | nicht vorhanden | Ausnahme gilt nicht für Produkte, daher Neubewertung bei Einführung |

### Tragende Begründung

1. **Kein eigener Verbraucher-Vertragsabschluss.** Die Angebote informieren oder
   rechnen. Ein Vertrag entsteht immer bei einem Dritten.
2. **Kleinstunternehmen-Ausnahme (§ 3 Abs. 3 Satz 1 BFSG).** Der Betreiber tritt
   als natürliche Person auf (Impressum: Frank Hartung, ohne Firmenzusatz). Die
   Schwellen sind nachzuweisen (siehe „Zu bestätigen“).

### Zu bestätigen (Betreiber)

- [ ] Anzahl der Beschäftigten (einschließlich Inhaber) unter zehn.
- [ ] Jahresumsatz oder Jahresbilanzsumme jeweils höchstens 2 Mio. €
  (Nachweis: letzter Steuerbescheid bzw. Jahresabschluss oder EÜR).

Solange diese Punkte nicht bestätigt sind, gilt die Bewertung als vorläufig.

### Neubewertung auslösen, wenn …

- ein Shop oder Produktverkauf eingeführt wird (auch E-Books, Printprodukte, Merchandise),
- Terminbuchungen oder Vertragsabschlüsse direkt auf der Website angeboten werden,
- ein Vermittlungsangebot mit eigenem Abschluss im Haus entsteht (keine reinen
  Affiliate-Links),
- die Kleinstunternehmen-Schwellen überschritten werden,
- das BFSG oder die Auslegung durch die Marktüberwachung geändert wird.

### Goodwill-Nachweis: Stand Barrierefreiheit (Verweis)

Der Blog betreibt unabhängig von der Pflicht ein laufendes Barrierefreiheits-Audit:

- **Automatisches Audit:** `scripts/a11y_audit.py` prüft gebaute Seiten auf
  lang-Attribut, Seitentitel, genau eine H1, alt-Texte, Skip-Link, sichtbare
  Fokus-Styles, `prefers-reduced-motion` und Kontrast der Branding-Farben
  (WCAG-2.1-Teilmenge). Seit der Härtung vom 07.10.2026 läuft es über alle gebauten
  Seiten statt über eine Stichprobe von 20 Seiten.
- **Stand 08.10.2026:** 85 Seiten vollständig geprüft, 0 Befunde, 0 Kontrast-Fehler
  (Quelle: `A11Y-EINE-H1-DAUERHEILUNG-PREMIUM-2026-10-08.md`, Abschnitt „Nachweis“).
  Vorgängerbericht: `A11Y-EINE-H1-DAUERHEILUNG-PREMIUM-2026-10-07.md`.
- **Grenzen:** Ein automatisches Audit deckt nur einen Teil der WCAG ab. Der Blog
  veröffentlicht daher keine Konformitätsaussage und keine Barrierefreiheitserklärung,
  weil diese nur für in Scope befindliche Angebote verpflichtend und nur mit
  manueller Prüfung belastbar wären.

### Quellen im Repo

- `data/recht-fristen.yaml` (Frist `bfsg-barrierefreiheit-bewertung`)
- `docs/INFRASTRUKTUR.md` (Fristen-Übersicht, BFSG-Scope-Bewertung einmalig)
- `scripts/a11y_audit.py`, `scripts/h1_wache.py`
- `A11Y-EINE-H1-DAUERHEILUNG-PREMIUM-2026-10-07.md`, `A11Y-EINE-H1-DAUERHEILUNG-PREMIUM-2026-10-08.md`

### Nächste Schritte

1. Beschäftigten- und Umsatzschwellen bestätigen (Betreiber, bis 31.10.2026).
2. Bewertung bei jedem Neubewertungs-Auslöser erneut prüfen.
3. Die Bewertung im quartalsweisen Rechtslage-Screening mitführen.
4. Bei Zweifeln eine fachanwaltliche Prüfung (IT-/Medienrecht) einholen.

---

*Verantwortlich: Frank Hartung. Pflege gemäß Frist `bfsg-barrierefreiheit-bewertung`.*
