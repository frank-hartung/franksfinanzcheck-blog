# Figma ↔ Hugo Komponenten-Inventar

> Generiert aus `data/design/handoff.yaml` · Stand 2026-10-31.

| ID | Figma-Komponente | Hugo/CSS-Vertrag | Pflichtzustände | A11y-Abnahme |
|---|---|---|---|---|
| `button-primary` | `Action/Button/Primary` | `.ff-btn-primary` | `default`, `hover`, `focus-visible`, `disabled`, `dark` | 44 px Soll-Trefferfläche; sichtbarer 3-px-Fokusring; Gelb nur als Fläche |
| `button-secondary` | `Action/Button/Secondary` | `.ff-btn-secondary` | `default`, `hover`, `focus-visible`, `disabled`, `dark` | 44 px Soll-Trefferfläche; kein Gelb als Text auf heller Fläche |
| `button-outline` | `Action/Button/Outline` | `.ff-btn-outline` | `default`, `hover`, `focus-visible`, `dark` | Nur auf Smaragdflächen; Rand 2 px, Kontrast ≥ 3:1 zur Fläche |
| `article-card` | `Content/Article card` | `.post-entry` | `default`, `hover`, `focus-within`, `dark` | Überschrift bleibt semantisch; Bild immer mit Alt-Text und Maßen |
| `trust-pill` | `Trust/Proof pill` | `.ff-trust-pill` | `default`, `dark` | Aussage nicht nur über Farbe vermitteln |
| `callout` | `Content/Callout` | `.ff-callout` | `tip`, `warning`, `info`, `dark` | Typ und Überschrift als Text; Kontrast mindestens 4,5:1 |
| `kurzantwort` | `Content/Kurzantwort` | `.ff-kurzantwort` | `default`, `dark`, `print` | Antwort als echter Text; Signet rein dekorativ (aria-hidden) |
| `newsletter-form` | `Conversion/Newsletter form` | `.ff-nl__form` | `default`, `focus`, `error`, `success`, `disabled`, `dark` | Persistente Labels; verständliche Fehlertexte; Tastaturbedienung |
| `header` | `Navigation/Header` | `.header` | `desktop`, `mobile`, `keyboard`, `dark` | Skip-Link, Landmark und sichtbarer aktueller Navigationspunkt |
| `author-trust-box` | `Trust/Author box` | `.ff-trust-box` | `default`, `dark` | Autor und Prüfhinweis als echter Text |
| `kostenprofil` | `Brand/Kostenprofil` | `.ff-kostenprofil` | `default`, `article`, `dark` | 4K-Prüfpfad als geordnete Liste; Indexzahlen sind Inhalt, keine Deko |
| `spar-matrix` | `Data/Spar-Matrix` | `.ff-spar-matrix-table` | `default`, `hover`, `focus-visible`, `dark`, `mobile-gestapelt` | Unter 760 px wird jede Zeile zur Karte; Feldnamen aus data-label |
| `pill` | `Content/Chip` | `.ff-pc-chip` | `default`, `dark` | Pill nur als Zusatzinfo, nie als einziger Träger einer Aussage |
| `faq` | `Content/FAQ` | `.ff-faq-list` | `default`, `open`, `focus-visible`, `dark` | Native details/summary oder gleichwertige Tastaturbedienung |
| `pillar-box` | `Navigation/Pillar box` | `.ff-pillar-box` | `default`, `hover`, `focus-visible`, `dark` | Verlinkung mit echtem Linktext, kein 'hier klicken' |
| `pinterest-cta` | `Conversion/Pinterest CTA` | `.ff-pinterest-cta` | `default`, `hover`, `focus-visible`, `dark` | Fremdmarke Pinterest-Rot nur hier; Kontrast Weiß auf Rot ≥ 4,5:1 |
| `consent-banner` | `System/Consent banner` | `#ff-consent-banner` | `default`, `dark`, `keyboard` | Bedienelemente ≥ 24 px; Banner blockiert nie den Fokus |
| `skip-link` | `System/Skip link` | `.skip-link` | `default`, `focus-visible`, `dark` | Immer oberstes Element (z 1000001), 3-px-Fokusring |

## Benennungs- und Übergaberegel

Figma verwendet `Bereich/Komponente/Variante`; der Code-Vertrag bleibt die angegebene CSS-Klasse. Ein visueller Entwurf darf den semantischen HTML-Vertrag nicht ersetzen. Neue Komponenten brauchen vor dem Export einen Inventar-Eintrag mit Fokus-, Dark-Mode- und Fehlerzustand, sofern sie interaktiv sind.
